"""Remove-sequence conformance: sem (final store) vs oracle vs the DRIVEN set engine.

The Lean operational chain is add-only (ARCHITECTURE.md §3.2 — remove legs are a
documented gap, FINAL_REVIEW §4), but the spec `sem` is a pure function of the
FINAL store. So removal conformance is testable today: drive the REAL Python
`SetEngine` through interleaved add_tuple/remove_tuple sequences (the remove
path: `_apply_remove`, interner `release` mask-scrub + id recycling,
`setengine/engine.py:111-131, 296-322`), land on a final store, and compare the
DRIVEN engine — not a rebuild — against the Lean spec and the oracle evaluated
on that final store. This pins Python's remove path against `sem` for the first
time. Two convergence pins ride along:

  * the driven engine must equal a fresh `rebuild()` (replay of the surviving
    `TupleV1` rows) BOTH pointwise over the grid AND at key-level state
    fingerprint (interner keys/refcounts/population masks, node_sets/member_of,
    flow-graph edge counts) — a freed id leaking residual state or a skipped
    mask scrub shows up here even when no grid query happens to read it;
  * the surviving `TupleV1` rows must be exactly the expected final multiset.

Sequences are derived from the existing corpora: each corpus's tuples plus
extras recombined from the corpus's OWN tuple space are added in random order
with interleaved removals, and some removed tuples are re-added (and possibly
re-removed) — interner release/recycle stress. An add the engine REJECTS
(graph-parity validation on a recombined extra, e.g. userset-cycle rejection)
poisons that tuple for the whole sequence; the comparison runs on the ACCEPTED
final store, so accept/reject parity stays pinned elsewhere (tests/test_matrix,
hypothesis), not here.

Scope: spec x oracle x set engine — the wider spec-scope corpus set (ALL of
`SCHEMAS`, exactly as test_conformance_random.py selects). The graph index is
deliberately OUT: its proved chain is add-only, and extending the harness there
is a separate work item (FINAL_REVIEW §4 remove legs).

Deterministic (seeded `random.Random`), no hypothesis dependency — the formal/
suite convention. Skips the `sem` comparisons if `zcli` is unbuilt (verify.sh
preflights the binary, so the gate never actually skips).
"""

from __future__ import annotations

import random
from collections import Counter

import pytest

from sqlmodel import select

from tests.oracle import Oracle, t as mk_tuple
from tests.wildcard_helpers import assert_wildcard_invariants
from setengine.models import TupleV1

from formal.conformance.corpus import SCHEMAS
from formal.conformance.encode import build_request
from formal.conformance.grid import (
    assert_grid_nonvacuous, queries_for, fmt_mismatches as _fmt)
from formal.conformance import runner
from formal.conformance.backends import (
    _fresh_session, GraphDriver, graphindex_drive_ops, bulk_build_drive)

SEEDS = list(range(5))

# Anti-vacuity (ZT-P4-4, 2026-07-26). Every differential in this file is
# `mism = [...]; assert not mism`, which is TRUE over an empty query list — and
# both the grid and the op streams are derived (from the corpus tuples, then from
# `_extras`, then from a seeded shuffle), so none of them is constant. Each test
# below therefore floors what it actually compared: the per-store grid (via the
# shared `assert_grid_nonvacuous`) and the running total of (query x store)
# comparisons across the seed sweep.
_MIN_SEQ_COMPARISONS = 6 * len(SEEDS)      # grid floor x seeds

# Sequence-shape knobs (all rng-driven, deterministic per seed).
_P_REMOVE_AFTER_ADD = 0.45   # chance to remove a present tuple after each add
_P_READD = 0.5               # chance a removed tuple is queued for re-add
_MAX_READDS = 2              # per-tuple re-add cap (bounds sequence length)
_P_FINAL_REMOVE = 0.3        # final wave: chance each survivor is removed


def _extras(rng, tuples):
    """Extra tuples drawn from the corpus's OWN tuple space: within each
    (subject_predicate, subject_type, relation, object_type) group, cross the
    observed subject names (+ two fresh same-type names when the group has a
    concrete, non-star subject) with the observed object names (+ one fresh
    object name — always filter-valid, the Filters are object-permissive).
    Star subjects stay star-only (a fresh name under a `[T:*]`-only restriction
    would just be filter-rejected); recombinations the engine still rejects
    (userset cycles) are handled by poisoning at drive time. Bounded to
    len(tuples)+2 extras so the grid stays inside the suite's runtime budget."""
    groups: dict[tuple, tuple[set, set]] = {}
    for t in tuples:
        k = (t.subject_predicate, t.subject_type, t.relation, t.object_type)
        g = groups.setdefault(k, (set(), set()))
        g[0].add(t.subject_name)
        g[1].add(t.object_name)
    existing = set(tuples)
    out = []
    for (sp, st, rel, ot), (snames, onames) in groups.items():
        cand_s = sorted(snames)
        if any(n != '*' for n in snames):
            cand_s += [f'x_{st}_1', f'x_{st}_2']
        for sn in cand_s:
            for on in sorted(onames) + [f'y_{ot}_1']:
                cand = mk_tuple(sp, st, sn, rel, ot, on)
                if cand not in existing:
                    out.append(cand)
    rng.shuffle(out)
    return out[:len(tuples) + 2]


def _sequence(rng, universe):
    """One interleaved add/remove op list over `universe`, landing on a strict
    subset (>= 1 net removal is forced). Every remove follows an add of the
    same tuple; removed tuples may be re-added and re-removed (recycle churn).
    Returns the op list `[('add'|'remove', tuple), ...]`."""
    pending = list(universe)
    rng.shuffle(pending)
    readds = dict.fromkeys(universe, 0)
    ops = []
    present: list = []
    while pending:
        tup = pending.pop()
        ops.append(('add', tup))
        present.append(tup)
        if len(present) > 1 and rng.random() < _P_REMOVE_AFTER_ADD:
            victim = present.pop(rng.randrange(len(present)))
            ops.append(('remove', victim))
            if readds[victim] < _MAX_READDS and rng.random() < _P_READD:
                readds[victim] += 1
                pending.insert(rng.randrange(len(pending) + 1), victim)
    for tup in list(present):
        if rng.random() < _P_FINAL_REMOVE:
            present.remove(tup)
            ops.append(('remove', tup))
    if len(present) == len(universe):   # no net removal happened: force one
        victim = present.pop(rng.randrange(len(present)))
        ops.append(('remove', victim))
    return ops


def _build_engine(schema_text, obj_wild):
    from setengine import SetEngine
    session = _fresh_session()
    eng = SetEngine(session, 's1', schema_text,
                    object_wildcard_shapes=frozenset(obj_wild))
    return session, eng


def _drive(eng, ops):
    """Apply the op sequence to the real engine INCREMENTALLY (the point of the
    gate — never rebuild-from-final here). A rejected add (ValueError from the
    engine's graph-parity validation) poisons that tuple: all its later ops are
    skipped and it is excluded from the final store. Returns the accepted final
    tuple set."""
    poisoned: set = set()
    present: set = set()
    for kind, tup in ops:
        if tup in poisoned:
            continue
        if kind == 'add':
            try:
                added = eng.add_tuple(*tup)
            except ValueError:
                poisoned.add(tup)
                continue
            assert added, f'duplicate add generated for {tup}'
            present.add(tup)
        else:
            assert tup in present, f'remove of absent tuple generated: {tup}'
            eng.remove_tuple(*tup)
            present.discard(tup)
    return present


def _key(eng, i):
    """id -> surrogate key, mapping a stale (freed-but-not-scrubbed) id to a
    sentinel so it produces a fingerprint DIFF instead of a KeyError."""
    return eng.interner.key_of.get(i, ('<stale-id>', str(i), ''))


def _fingerprint(eng):
    """Key-level (id-free) snapshot of the engine's in-memory state. The
    driven engine and a fresh rebuild() assign different internal ids (the free
    list recycles), so state convergence is asserted on the stable surrogate
    keys: interner mappings + refcounts, the population masks, node_sets /
    member_of memberships, and the flow-graph (cycle-detection) edge counts.
    Empty masks/sets are dropped — replay never creates them."""
    # Flow graph is lazy since N10; materialize it before comparing so the
    # driven and rebuilt engines snapshot equivalent (built) state.
    eng._ensure_flow_graph()
    intr = eng.interner
    return {
        'keys': frozenset(intr.id_of),
        'refcount': {k: intr.refcount[i] for k, i in intr.id_of.items()},
        'ids_of_type': {ty: frozenset(_key(eng, i) for i in mask)
                        for ty, mask in intr.ids_of_type.items() if len(mask)},
        'ids_of_shape': {sh: frozenset(_key(eng, i) for i in mask)
                         for sh, mask in intr.ids_of_shape.items() if len(mask)},
        'node_sets': {_key(eng, oid): (frozenset(_key(eng, i) for i in ns.entities),
                                       frozenset(_key(eng, i) for i in ns.usersets))
                      for oid, ns in eng.node_sets.items()},
        'member_of': {_key(eng, sid): frozenset(_key(eng, i) for i in mo)
                      for sid, mo in eng.member_of.items() if len(mo)},
        'edge_count': dict(eng._edge_count),
        'flow_adj': {k: frozenset(v) for k, v in eng._flow_adj.items() if v},
    }


def _fp_diff(a, b):
    lines = []
    for part in sorted(set(a) | set(b)):
        if a.get(part) != b.get(part):
            lines.append(f'  {part}: driven={a.get(part)!r} rebuilt={b.get(part)!r}')
    return '\n'.join(lines)


def _rows(session):
    rows = session.exec(select(TupleV1).where(TupleV1.store_id == 's1')).all()
    return [(r.subject_predicate, r.subject_type, r.subject_name,
             r.relation, r.object_type, r.object_name) for r in rows]


@pytest.mark.parametrize('name', sorted(SCHEMAS))
def test_remove_sequences(name):
    """Seeded interleaved add/remove sequences per corpus: the DRIVEN engine ==
    rebuild() (grid + state fingerprint), == oracle(final store), and
    zcli spec(final store) == oracle(final store) — so all four corners agree
    on every store the remove path produced."""
    schema_text, corpus_tuples, obj_wild = SCHEMAS[name]
    have_zcli = True
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        have_zcli = False

    n_compared = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        universe = list(corpus_tuples) + _extras(rng, corpus_tuples)
        ops = _sequence(rng, universe)
        # grid over the FULL universe: removed/never-present names stay probed
        queries = queries_for(schema_text, universe)
        assert_grid_nonvacuous(f'{name} seed={seed}', queries)
        n_compared += len(queries)

        session, eng = _build_engine(schema_text, obj_wild)
        final = _drive(eng, ops)
        assert len(final) < len(universe), 'sequence must net-remove something'

        driven = [bool(eng.check(*q)) for q in queries]
        fp_driven = _fingerprint(eng)

        # The surviving rows ARE the expected final store (no dup/ghost rows).
        db = _rows(session)
        assert sorted(db) == sorted(tuple(t) for t in final), (
            f'[{name} seed={seed}] TupleV1 rows diverge from the expected '
            f'final store after the remove sequence')

        # Remove-path state convergence: driven == fresh replay of the rows.
        eng.rebuild()
        fp_rebuilt = _fingerprint(eng)
        assert fp_driven == fp_rebuilt, (
            f'[{name} seed={seed}] driven/rebuilt STATE divergence (remove-path '
            f'residue — freed-id scrub or mask hygiene):\n'
            f'{_fp_diff(fp_driven, fp_rebuilt)}')
        rebuilt = [bool(eng.check(*q)) for q in queries]
        mism = [(queries[i], driven[i], rebuilt[i]) for i in range(len(queries))
                if driven[i] != rebuilt[i]]
        assert not mism, (f'[{name} seed={seed}] driven/rebuilt disagreement:\n'
                          f'{_fmt(mism, "driven", "rebuilt")}')

        final_tuples = sorted(final)
        orc = Oracle(schema_text, final_tuples)
        oracle = [orc.check(*q) for q in queries]
        mism = [(queries[i], driven[i], oracle[i]) for i in range(len(queries))
                if driven[i] != oracle[i]]
        assert not mism, (
            f'[{name} seed={seed}] driven-set-engine/oracle disagreement on the '
            f'final store:\n{_fmt(mism, "driven", "oracle")}')

        if have_zcli:
            spec = runner.run_spec(
                build_request(schema_text, final_tuples, queries, obj_wild))
            mism = [(queries[i], spec[i], oracle[i]) for i in range(len(queries))
                    if spec[i] != oracle[i]]
            assert not mism, (
                f'[{name} seed={seed}] spec/oracle disagreement on the final '
                f'store (ADJUDICATION EVENT — plan §8.2):\n'
                f'{_fmt(mism, "spec", "oracle")}')
        session.close()

    # ANTI-VACUITY (ZT-P4-4): the seed sweep really compared something.
    assert n_compared >= _MIN_SEQ_COMPARISONS, (
        f'[{name}] ANTI-VACUITY: only {n_compared} (query x store) comparisons '
        f'across {len(SEEDS)} seeds, floor {_MIN_SEQ_COMPARISONS}')


@pytest.mark.parametrize('name', sorted(SCHEMAS))
def test_full_churn_restores(name):
    """Add every corpus tuple, remove ALL of them (different order — the
    interner must drain to empty: every id released, every mask scrubbed),
    then re-add them all (freed ids recycled). The churned engine must equal a
    fresh replay at state level and match spec/oracle on the corpus store."""
    schema_text, corpus_tuples, obj_wild = SCHEMAS[name]
    have_zcli = True
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        have_zcli = False

    rng = random.Random(0xC0FFEE)
    queries = queries_for(schema_text, corpus_tuples)
    assert_grid_nonvacuous(name, queries)

    session, eng = _build_engine(schema_text, obj_wild)
    for tup in corpus_tuples:
        eng.add_tuple(*tup)
    removal_order = list(corpus_tuples)
    rng.shuffle(removal_order)
    for tup in removal_order:
        eng.remove_tuple(*tup)

    # Fully drained: no interned ids, no memberships, no rows, no flow edges.
    assert not eng.interner.id_of and not eng.interner.refcount, (
        f'[{name}] interner not empty after removing every tuple')
    assert not eng.node_sets and not eng.member_of and not eng._edge_count, (
        f'[{name}] evaluator state not empty after removing every tuple')
    assert all(len(m) == 0 for m in eng.interner.ids_of_type.values()), (
        f'[{name}] a type population mask survived full removal')
    assert all(len(m) == 0 for m in eng.interner.ids_of_shape.values()), (
        f'[{name}] a shape population mask survived full removal')
    assert not _rows(session), f'[{name}] TupleV1 rows survived full removal'

    readd_order = list(corpus_tuples)
    rng.shuffle(readd_order)
    for tup in readd_order:
        eng.add_tuple(*tup)

    churned = [bool(eng.check(*q)) for q in queries]
    fp_churned = _fingerprint(eng)
    eng.rebuild()
    assert fp_churned == _fingerprint(eng), (
        f'[{name}] churned/rebuilt STATE divergence after full add-remove-readd '
        f'cycle:\n{_fp_diff(fp_churned, _fingerprint(eng))}')

    orc = Oracle(schema_text, list(corpus_tuples))
    oracle = [orc.check(*q) for q in queries]
    mism = [(queries[i], churned[i], oracle[i]) for i in range(len(queries))
            if churned[i] != oracle[i]]
    assert not mism, (f'[{name}] churned-engine/oracle disagreement:\n'
                      f'{_fmt(mism, "churned", "oracle")}')

    if have_zcli:
        spec = runner.run_spec(
            build_request(schema_text, corpus_tuples, queries, obj_wild))
        mism = [(queries[i], spec[i], churned[i]) for i in range(len(queries))
                if spec[i] != churned[i]]
        assert not mism, (
            f'[{name}] spec/churned-engine disagreement (ADJUDICATION EVENT — '
            f'plan §8.2):\n{_fmt(mism, "spec", "churned")}')
    session.close()


# ---------------------------------------------------------------------------
# Graph backend (index_v4) — the SAME remove sequences, driven through the
# synchronous v1 write path (rule routing + same-transaction cascade, I5).
#
# Scope note. zcli `sem` parity is NOT re-run here for the graph: the sibling
# `test_remove_sequences` already pins `sem(final) == oracle(final)` on these
# exact corpora/seeds, so pinning `graph == oracle` below pins `graph == sem`
# transitively. And the Lean OPERATIONAL graph model is add-only
# (ARCHITECTURE.md §3.2 / FINAL_REVIEW §4 remove legs), so it is out of scope as
# a post-remove reference — item (d)'s Lean half stays deferred; the Python graph
# remove path is what these tests pin for the first time.
# ---------------------------------------------------------------------------

def _residues_by_name(session, widx):
    """Symbolic residues keyed by (object_type, object_name, relation) with the
    neg set carried as id-free (predicate, type, name) triples — the id-stable
    idiom from tests/test_hypothesis.py, so a driven index and a fresh add-only
    build (which assign different node ids) compare equal."""
    import json
    from sqlmodel import select
    from index_v4.models import ResidueV1
    out = {}
    for r in session.exec(select(ResidueV1)).all():
        node = widx._node_by_id(r.object_node_id)
        neg = frozenset((n.predicate, n.type, n.name)
                        for n in (widx._node_by_id(i) for i in json.loads(r.neg))
                        if n is not None)
        out[(node.type, node.name, r.relation)] = (r.stars, neg)
    return out


def _graph_state(session, widx):
    """Id-free graph fingerprint: (snapshot_rows, residues_by_name).

    Uses `snapshot_rows` (I11/I12 multiset), NOT `extract_sql_state` — the
    latter's P2 projection would hide a stale bridge that a remove-path residue
    leak leaves behind, which is exactly what this gate must catch (P6 retired
    2026-09-05; leaf edges are compared now)."""
    from index_v4.invariants import snapshot_rows
    return snapshot_rows(session, widx.idx.store_id), _residues_by_name(session, widx)


@pytest.mark.parametrize('name', sorted(SCHEMAS))
def test_graph_remove_sequences(name):
    """Seeded interleaved add/remove sequences per corpus, driven through the
    REAL graph index (index_v4) — the first end-to-end pin of the graph remove
    path. Identical universe/ops to `test_remove_sequences` (same generators,
    same seeds). Asserts, on the driven final state: (a) I1-I8 invariants and, on
    boolean schemas, the I9 fixpoint audit; (b) driven grid `check` ==
    oracle(accepted_final) — the primary correctness pin; (c) driven graph state
    == a fresh add-only build's state (remove-path residue: stale bridge / leaf
    edge / residue leak shows up here); (d) driven grid == fresh-build grid.

    (Scope: sem/Lean deferred — see the module-level note above.)"""
    schema_text, corpus_tuples, obj_wild = SCHEMAS[name]

    n_compared = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        universe = list(corpus_tuples) + _extras(rng, corpus_tuples)
        ops = _sequence(rng, universe)
        # grid over the FULL universe: removed/never-present names stay probed
        queries = queries_for(schema_text, universe)
        assert_grid_nonvacuous(f'{name} seed={seed}', queries)
        n_compared += len(queries)

        session, widx, proc, _store_id, final = graphindex_drive_ops(
            schema_text, ops, obj_wild)
        assert len(final) < len(universe), 'sequence must net-remove something'

        # (a) invariants + fixpoint audit on the driven final state
        assert_wildcard_invariants(widx)
        if proc is not None:
            proc.audit_fixpoint()                       # I9, all keys

        driven = [bool(widx.check(*q)) for q in queries]

        # (b) primary pin: driven graph == oracle on the accepted final store.
        final_tuples = sorted(final)
        orc = Oracle(schema_text, final_tuples)
        oracle = [orc.check(*q) for q in queries]
        mism = [(queries[i], driven[i], oracle[i]) for i in range(len(queries))
                if driven[i] != oracle[i]]
        assert not mism, (
            f'[{name} seed={seed}] driven-graph/oracle disagreement on the '
            f'final store:\n{_fmt(mism, "driven", "oracle")}')

        # (c)+(d)+(e) convergence: the driven state must equal a FRESH add-only
        # build over accepted_final, both at id-free state level (no ghost/dup
        # edges, no stale bridge/residue — the graph analog of the set-engine
        # row-multiset check) and pointwise over the grid.
        fsession, fwidx, _fproc, _fstore, _ffinal = graphindex_drive_ops(
            schema_text, [('add', t) for t in final_tuples], obj_wild)
        driven_state = _graph_state(session, widx)
        fresh_state = _graph_state(fsession, fwidx)
        assert driven_state == fresh_state, (
            f'[{name} seed={seed}] driven/fresh-build STATE divergence '
            f'(remove-path residue — stale bridge/leaf edge or residue leak):\n'
            f'  driven nodes={driven_state[0][0]}\n  fresh  nodes={fresh_state[0][0]}\n'
            f'  driven edges={driven_state[0][1]}\n  fresh  edges={fresh_state[0][1]}\n'
            f'  driven residues={driven_state[1]}\n  fresh  residues={fresh_state[1]}')
        fresh = [bool(fwidx.check(*q)) for q in queries]
        mism = [(queries[i], driven[i], fresh[i]) for i in range(len(queries))
                if driven[i] != fresh[i]]
        assert not mism, (
            f'[{name} seed={seed}] driven/fresh-build grid disagreement:\n'
            f'{_fmt(mism, "driven", "fresh")}')

        fsession.close()
        session.close()

    # ANTI-VACUITY (ZT-P4-4): the seed sweep really compared something.
    assert n_compared >= _MIN_SEQ_COMPARISONS, (
        f'[{name}] ANTI-VACUITY: only {n_compared} (query x store) comparisons '
        f'across {len(SEEDS)} seeds, floor {_MIN_SEQ_COMPARISONS}')


@pytest.mark.parametrize('name', sorted(SCHEMAS))
def test_graph_full_churn_restores(name):
    """Add every corpus tuple to the graph index, remove ALL of them (shuffled),
    assert the graph SQL state is FULLY DRAINED (no NodeV4/EdgeV4/ResidueV1 rows —
    empirically the drain equals a fresh-EMPTY index; permanent scaffolding like
    the store row is not a graph row and legitimately remains), then re-add all
    and assert the churned state + grid match a fresh add-only build and the
    oracle. Between the drain and the re-add, a repeat remove of a corpus tuple
    must raise `ValueError('Non-existent edge ...')` AND leave state unchanged
    (I12: a rejected remove must not mutate).

    (Scope: sem/Lean deferred — see the module-level note above.)"""
    schema_text, corpus_tuples, obj_wild = SCHEMAS[name]
    rng = random.Random(0xC0FFEE)
    queries = queries_for(schema_text, corpus_tuples)
    assert_grid_nonvacuous(name, queries)

    # Fresh-empty reference: what "fully drained" must equal.
    empty = GraphDriver(schema_text, obj_wild)
    empty_state = _graph_state(empty.session, empty.widx)
    empty.close()

    drv = GraphDriver(schema_text, obj_wild)
    for tup in corpus_tuples:
        assert drv.apply(tup, 'add'), f'[{name}] corpus add rejected: {tup}'
    removal_order = list(corpus_tuples)
    rng.shuffle(removal_order)
    for tup in removal_order:
        assert drv.apply(tup, 'remove'), f'[{name}] corpus remove rejected: {tup}'

    # Fully drained: no closure edges, no nodes, no residues — == fresh-empty.
    drained_state = _graph_state(drv.session, drv.widx)
    assert drained_state == empty_state, (
        f'[{name}] graph state not fully drained after removing every tuple:\n'
        f'  drained nodes={drained_state[0][0]} edges={drained_state[0][1]} '
        f'residues={drained_state[1]}')
    assert drained_state[0] == (Counter(), Counter()) and not drained_state[1], (
        f'[{name}] residual graph rows survived full removal: {drained_state}')
    assert_wildcard_invariants(drv.widx)
    if drv.proc is not None:
        drv.proc.audit_fixpoint()

    # I12: a repeat remove of a now-absent edge must raise AND not mutate.
    before = _graph_state(drv.session, drv.widx)
    with pytest.raises(ValueError, match='Non-existent edge'):
        drv._route(corpus_tuples[0], 'remove')
    drv.session.rollback()
    assert _graph_state(drv.session, drv.widx) == before, (
        f'[{name}] a rejected remove mutated graph state (I12 violation)')

    # Re-add all (freed node ids recycled), then converge to a fresh build.
    readd_order = list(corpus_tuples)
    rng.shuffle(readd_order)
    for tup in readd_order:
        assert drv.apply(tup, 'add'), f'[{name}] corpus re-add rejected: {tup}'

    fsession, fwidx, _fproc, _fstore, _ffinal = graphindex_drive_ops(
        schema_text, [('add', t) for t in corpus_tuples], obj_wild)
    churned_state = _graph_state(drv.session, drv.widx)
    fresh_state = _graph_state(fsession, fwidx)
    assert churned_state == fresh_state, (
        f'[{name}] churned/fresh-build STATE divergence after full '
        f'add-remove-readd cycle:\n'
        f'  churned nodes={churned_state[0][0]}\n  fresh   nodes={fresh_state[0][0]}\n'
        f'  churned edges={churned_state[0][1]}\n  fresh   edges={fresh_state[0][1]}\n'
        f'  churned residues={churned_state[1]}\n  fresh   residues={fresh_state[1]}')

    churned = [bool(drv.widx.check(*q)) for q in queries]
    fresh = [bool(fwidx.check(*q)) for q in queries]
    mism = [(queries[i], churned[i], fresh[i]) for i in range(len(queries))
            if churned[i] != fresh[i]]
    assert not mism, (f'[{name}] churned/fresh-build grid disagreement:\n'
                      f'{_fmt(mism, "churned", "fresh")}')

    orc = Oracle(schema_text, list(corpus_tuples))
    oracle = [orc.check(*q) for q in queries]
    mism = [(queries[i], churned[i], oracle[i]) for i in range(len(queries))
            if churned[i] != oracle[i]]
    assert not mism, (f'[{name}] churned-graph/oracle disagreement:\n'
                      f'{_fmt(mism, "churned", "oracle")}')

    fsession.close()
    drv.close()


# ---------------------------------------------------------------------------
# BULK arm (TK91) — the OFFLINE bootstrap replayed over a POST-REMOVAL
# survivor set.
#
# `test_graph_remove_sequences` above compares the driven index against a fresh
# ADD-ONLY write-by-write build of the survivors. That fresh build is the same
# constructor, run again: `graphindex_drive_ops`, routing + same-transaction
# cascade. The PRODUCTION bootstrap is a different constructor —
# `connectedstore.build_index(bulk=True)` -> `index_v4/bulk_build.py` (one
# in-memory pass, closed-form path counts, `bulk_backfill.py`'s in-memory
# boolean Phase-D backfill, bulk INSERTs) — and until this arm nothing anywhere
# bulk-built from a POST-REMOVAL survivor set. `test_conformance_bulk_state.py`
# runs the bulk constructor only over whole, add-only corpora (its "Remove
# histories" bullet says so); the survivor sets this file produces are sparse
# and holey in a way no add-only corpus is.
# ---------------------------------------------------------------------------

# Anti-vacuity floors for the bulk arm. `_MIN_SEQ_COMPARISONS` (:69) floors GRID
# QUERIES, which does NOT cover this arm: `_graph_state` on two EMPTY indexes
# compares equal, and `bulk_build.py` returns early on an empty node set, so an
# empty survivor set would pass having compared no STATE at all. These floor the
# state instead. Both are set AT the live minimum (no headroom): adding state is
# free, losing it is loud.
#
# FLOOR PROVENANCE, measured 2026-09-20 over all 26 `SCHEMAS` x 5 `SEEDS` = 130
# cells (sweep script `.scratch/tk91-tk80/measure_arm.py`, mirroring this test
# exactly; totals `740` survivors, `3757` state rows, `72` residues, `157`
# derived edges, `44245` grid comparisons, 0 mismatches):
#   * per-corpus state rows over the 5-seed sweep, MINIMUM = 12
#     (`wildcard_public`; next thinnest `object_wildcard` at 32, median 148).
#   * exactly ONE of the 130 cells compares two EMPTY indexes —
#     `wildcard_public` seed 4, 0 survivors / 0 state rows — and 7 of 130 have
#     <= 1 survivor or <= 3 state rows. That cell is NOT skipped: it still pins
#     that the driven remove path drained completely and that the bulk build
#     wrote nothing extra. It is exactly why the floor is on the SWEEP and not
#     per cell.
#   * derived-arm state (processor-stamped `derived` edges + symbolic residues)
#     over the sweep, MINIMUM over the 17 boolean corpora = 1
#     (`nary_intersection`: 1 derived edge, 0 residues). Measured 2026-09-20, when
#     13 of the 26 corpora THEN in `SCHEMAS` carried a derived edge at all and 5
#     carried residues. `SCHEMAS` has grown since (TK94), and the floor is on the
#     SWEEP rather than per cell, so those figures are provenance, not a live count.
_MIN_BULK_STATE_ROWS = 12
_MIN_BULK_DERIVED_STATE = 1


def _derived_edge_flags(session, store_id):
    """Per-edge `EdgeV4.derived` stamp (I5), keyed id-free like `snapshot_rows`.

    `invariants.py::snapshot_rows` captures `direct_edge_count` /
    `indirect_edge_count` but NOT `derived`, so `_graph_state` cannot see a
    constructor that materializes the right closure with the wrong I5
    provenance stamp. This is the one field added on top of it here; measured
    2026-09-20 to redden under the bulk-backfill control in the test docstring
    below (12 of 130 cells) while staying green on the clean tree (0 of 130).
    """
    from index_v4.models import EdgeV4, NodeV4
    nodes = session.exec(select(NodeV4).where(NodeV4.store_id == store_id)).all()
    by_id = {n.id: (n.predicate, n.type, n.name, n.wildcard) for n in nodes}
    edges = session.exec(select(EdgeV4).where(EdgeV4.store_id == store_id)).all()
    return Counter((by_id[e.subject_id], by_id[e.object_id], e.derived)
                   for e in edges)


def _flag_diff(driven: Counter, bulk: Counter) -> str:
    lines = []
    for k in sorted(set(driven) | set(bulk), key=repr):
        if driven[k] != bulk[k]:
            lines.append(f'  {k[0]} -> {k[1]} derived={k[2]}: '
                         f'driven={driven[k]} bulk={bulk[k]}')
    return '\n'.join(lines)


def _incremental_constructor_label(schema_text, tuples, object_wildcards):
    """CONTROL for leg (e): build the SAME snapshot with ``bulk=False`` and
    report which constructor ``build_index`` says it ran.

    Leg (e) is a refusal in `backends.bulk_build_drive`: it raises unless
    `build_index` reports `constructor == 'bulk'`. That refusal is worth
    nothing if the label can only ever say `'bulk'` — the classic assertion
    that cannot fail. This runs the OTHER branch of the same function over the
    same survivors and requires the OTHER label, so a
    `BuildReport.constructor` that silently became a constant reddens here
    instead of quietly disarming the pin.

    Cheap by construction: the survivor sets are small (740 tuples over all
    130 cells, measured 2026-09-20) and this runs once per corpus, not once
    per seed. It asserts nothing about STATE — `tests/test_bulk_build.py` owns
    the bulk/incremental identity differential.
    """
    from connectedstore import TupleSource, build_index, save_schema

    session = _fresh_session()
    try:
        save_schema(session, 'ctl', schema_text, frozenset(object_wildcards))
        src = TupleSource(session, 'ctl')
        for tup in tuples:
            src.add(tup.subject_predicate, tup.subject_type, tup.subject_name,
                    tup.relation, tup.object_type, tup.object_name)
        session.commit()
        return build_index(session, 'ctl', bulk=False).constructor
    finally:
        session.close()


@pytest.mark.parametrize('name', sorted(SCHEMAS))
def test_graph_remove_bulk_build_survivors(name):
    """The OFFLINE bulk bootstrap, run over the survivor set of a remove
    sequence, lands on exactly the state the driven graph index is in.

    Same universe/ops/grid/seeds as `test_graph_remove_sequences` (identical
    generators, so all three graph arms traverse identical op streams). Per
    corpus x seed: drive adds/removes through the synchronous v1 path
    (`graphindex_drive_ops`), snapshot the accepted survivors, then build a
    SECOND index from that snapshot through `connectedstore.build_index(
    bulk=True)` (`backends.bulk_build_drive`) and assert

      (a) the bulk-built index satisfies I1-I8 on its own, and on a boolean
          schema passes the I9 fixpoint audit (absolute, not differential —
          a defect both constructors shared would still fail here);
      (b) driven state == bulk state, id-free, via `_graph_state`
          (`snapshot_rows` node/edge multisets + symbolic residues);
      (c) driven per-edge `derived` flags == bulk's (`_derived_edge_flags`) —
          the I5 stamp `snapshot_rows` does not carry;
      (d) driven grid `check` == bulk grid `check` over the full universe;
      (e) the BULK constructor is the one that actually RAN. `bulk_build_drive`
          refuses unless `build_index` reports `constructor == 'bulk'`
          (`connectedstore/build.py::BuildReport`), and this arm carries the
          CONTROL that keeps that refusal from being an assertion that cannot
          fail: once per corpus `_incremental_constructor_label` rebuilds the
          last seed's survivors with `bulk=False` and requires the OTHER label.
          Legs (a)-(d) are blind here BY DESIGN — P13's correctness bar is that
          the two constructors produce identical state — so nothing about the
          RESULT can distinguish them. Measured 2026-09-20, before leg (e)
          existed: a byte edit of `connectedstore/build.py` turning `if bulk:`
          into `if False:` left this arm at `26 passed, 104 deselected` rc=0
          while `index_v4.bulk_build.bulk_build` was called 0 times instead of
          130 — the arm's whole stated subject silently replaced by the
          constructor it was written to differ from.

    WHAT THIS COVERS THAT NOTHING ELSE DID. `bulk_build.py` /
    `bulk_backfill.py` were pinned only over whole, add-only tuple lists:
    `test_conformance_bulk_state.py` (25 `GRAPH_FRAGMENT` corpora, add-only),
    `tests/test_bulk_build.py` (its own `_CORPORA`, add-only), and
    `tests/test_connectedstore_build.py::test_built_index_equals_live_maintained`
    (ONE history with ONE remove). A post-removal survivor set is a different
    input class — sparse and holey, with families partly drained and
    recombined `_extras` names left dangling — and nothing bulk-built from one.
    Two secondary widenings, both measured 2026-09-20:
      * the comparison is `snapshot_rows`, which carries
        `indirect_edge_count`, so Phase P's closed-form path counts ARE
        compared here; `test_conformance_bulk_state.py`'s canonical form
        (`extract_sql_state`, P1) drops them and says so.
      * this module parametrizes over every `SCHEMAS` entry, and as measured
        2026-09-20 `object_wildcard` was the ONLY corpus in either set with a
        non-empty `bridged_in_shapes` / `bridged_out_shapes`
        (`bridged_out = [('folder', 'viewer')]`). `SCHEMAS` minus
        `GRAPH_FRAGMENT` is no longer that one corpus alone — TK94 added
        `derived_userset_subject` on 2026-09-22, deliberately outside the
        fragment — but it declares no wildcard shape, so the bridge-row claim
        below is unchanged. Do not restate the set size here; it rots. Its
        bulk-built survivor indexes carry `2` BRIDGE rows across the 5 seeds
        (a row whose target is a `w_any` node or whose source is a `w_all`
        node), and `snapshot_rows` filters nothing, so they are compared here.
        `extract_sql_state`'s P2 drops exactly those rows, which is why
        `test_conformance_bulk_state.py` records its Phase-B coverage as nil.
        Do not read more into this than the number: 2 rows on 1 corpus, and
        `crossable_shapes` was EMPTY, measured 2026-09-16 over all 26 corpora THEN
        in `SCHEMAS`, so `bulk_build.py`'s
        I14 crossable-middle loop is still reached by nothing in this file
        (it is pinned by `tests/test_bulk_build.py::_assert_r4bf_features`
        clause (g), per `P22`).

    WHAT THIS DOES *NOT* COVER, said plainly:

      * **The mutation TK91 was opened for.** Deleting the leading `rel` from
        `index_v4/processor.py::_live_keys_of`'s `preds` list leaves this arm
        GREEN, and that is not fixable by strengthening the comparison. Two
        measured reasons (2026-09-20): the bulk path never calls that function
        (`bulk_backfill.py::_live_keys_of` is its own mirror; the processor's
        was called 0 times on the bulk arm across all 26 corpora), AND on a
        CONSISTENT store the edit is a semantic no-op — clean vs mutated dumps
        of every answer it returns are byte-identical (536 enumerated names,
        same sha, `diff` exit 0). Only a corrupt-then-repair shape
        (uncascaded leaf retraction + `DeltaProcessor.backfill()`)
        discriminates it; that is a `tests/` unit, not a conformance remove
        arm. Literal output of the mutated run is in the evidence block below.
      * **The bulk side's LOG never contains a remove.** The survivors are
        re-written fresh through a `TupleSource`, so `build_index` reads an
        add-only snapshot. What is pinned is the bulk constructor over a
        survivor SET; a bulk build over a store whose own log interleaves
        removes is still pinned only by
        `tests/test_connectedstore_build.py::test_built_index_equals_live_maintained`.
      * **The outbox**, which neither `_graph_state` nor the grid reads: the
        bulk path writes one `ADDED` row per final closure pair by design
        while the driven path holds a per-write delta history, so they are not
        comparable here. `tests/test_bulk_build.py` compares them against
        `bulk=False`.
      * **`sem` / the Lean model.** Out of scope for the whole graph section of
        this module — the Lean operational chain is add-only (see the section
        note above `test_graph_remove_sequences`). The reference here is the
        driven Python index, which the sibling test has already pinned to the
        oracle on these exact corpora and seeds.
      * **Accept/reject parity at the two admission surfaces.**
        `bulk_build_drive` writes through `TupleSource` (set-engine admission)
        while `graphindex_drive_ops` validates through the graph index. If they
        disagreed on a survivor, `bulk_build_drive` raises its landed-count
        refusal instead of reporting a mismatch. Measured 2026-09-20: it never
        fires over the 130 cells (`landedfail=0`). If it ever does, that is a
        Python bug to fix, not an arm to relax (`CLAUDE.md` "Who decides").
        MEASURED AND DELIBERATELY NOT PINNED (sweep M15, 2026-09-20): because
        every cell satisfies `landed == len(tuples)`, neutering that refusal to
        `if False:` is GREEN. It guards a future divergence, not a live
        property, and was not contorted into one.
      * **Six paths the bulk constructor never takes on this input class.**
        Each proven dead by an instrumented counter over all 130 cells —
        MEASURED, not inferred: the hit counters were never taken — and each
        MEASURED AND DELIBERATELY NOT PINNED (2026-09-20). Subject-side
        bridging in `bulk_build.py` Phase B; the `_ensure_bridges` call in
        `bulk_backfill.py::_write_derived_add`; Phase P's multiplicity weight
        (`mult` is never != 1); `ResidueV1.version` != 1 on a fresh bulk build;
        `bulk_backfill.py::_store_residue`'s re-store branch; and the step-4
        neg-maintenance `_store_residue`. Weakening any of them leaves this arm
        green because nothing here reaches them. Detail:
        `docs/tk91-tk80-removal-coverage-2026-09-20.md`.

    ★ SABOTAGE EVIDENCE (2026-09-20, `docs/sabotage-procedure.md`), literal
    observed output. Every run below is
    ``pytest formal/conformance/test_conformance_remove.py
    -k test_graph_remove_bulk_build_survivors -q`` against this module as
    landed. The weakenings were applied as RUNTIME monkeypatches loaded with
    `-p` from `.scratch/` rather than as edits to `index_v4/`, because sibling
    agents were running pytest against this same working tree in the same
    session; each replacement body is a byte-for-byte copy of the shipped one
    with only the named line changed.

      * CLEAN: ``26 passed, 104 deselected in 279.57s (0:04:39)``.

      * ★ **The control that shows the arm is not vacuous.** Drop the
        `derived-computed` recursion from
        `index_v4/bulk_backfill.py::_BulkBackfill._live_keys_of`
        (`names |= self._live_keys_of(o_type, spec.predicate)` -> `pass`) —
        the narrowest plausible weakening of the bulk mirror's enumeration::

            E   index_v4.invariants.InvariantViolation: I9: reconcile of (doc, approver, d1) was not a fixpoint -- derived state was stale
            FAILED ...::test_graph_remove_bulk_build_survivors[cross_stratum_resettle]
            FAILED ...[nary_union_derived4]
            FAILED ...[residue_rich]
            FAILED ...[star_two_strata_churn]
            FAILED ...[taint_computed_root_over_boolean]
            FAILED ...[taint_union_over_boolean]
            FAILED ...[taint_union_userset_arm]
            FAILED ...[two_stratum_cascade]
            8 failed, 18 passed, 104 deselected in 197.72s (0:03:17)

      * ★ **Controlling the INSTRUMENT.** Every red above is leg (a)'s I9
        audit, which runs first — so that run alone does NOT show the
        DIFFERENTIAL sees anything. Re-run with the same control PLUS
        `DeltaProcessor.audit_fixpoint` monkeypatched to a no-op: the SAME 8
        corpora redden, now on leg (b)::

            E   AssertionError: [cross_stratum_resettle seed=0] driven/BULK-BUILT STATE divergence on the post-removal survivor set (the offline bootstrap does not reproduce the state the logged write path is in):
            E       driven nodes=Counter({... ('a', 'doc', 'y_doc_1', '', False, 1): 1, ('...', 'user', 'alice', '', True, 4): 1, ('a', 'doc', 'd1', '', False, 1): 1})
            E       bulk   nodes=Counter({('...', 'user', 'alice', '', True, 3): 1, ... ('v.0', 'doc', 'y_doc_1', '', True, 2): 1})
            8 failed, 18 passed, 104 deselected in 157.46s (0:02:37)

        Reading the two Counters (interpretation, not observed text): the
        bulk build is missing the whole public `a` family — both
        `('a', 'doc', d)` nodes and the two grant edges into them — because
        the dropped recursion never enumerated the objects that only the
        derived-computed arm reaches.

      * **INERT, recorded as such rather than worked around.** The mutation
        TK91 was opened for —
        `index_v4/processor.py::DeltaProcessor._live_keys_of`'s
        `preds = [rel] + [...]` -> `preds = [] + [...]` — leaves this arm
        GREEN: ``26 passed, 104 deselected in 243.89s (0:04:03)``. The two
        measured reasons are in the "does NOT cover" list above. It is pinned
        in `tests/`, not here, and the arm was deliberately NOT contorted to
        chase it.

      * **Phase P — the closed-form path counts — IS pinned here**, which
        `test_conformance_bulk_state.py` records as impossible for itself
        (its canonical form never reads `indirect_edge_count`; `snapshot_rows`
        does). `bulk_build.py` Phase W `'indirect_edge_count': pvec[a][b]`
        -> `min(1, pvec[a][b])`, clamped at the `executemany` boundary
        (`1751` `EdgeV4` rows touched)::

            E   index_v4.invariants.InvariantViolation: I1: indirect < direct on edge id=3 subject_id=1 direct_edge_count=2 derived=False store_id='conf' object_id=7 indirect_edge_count=1
            E   AssertionError: [deep_grid seed=1] driven/BULK-BUILT STATE divergence on the post-removal survivor set (the offline bootstrap does not reproduce the state the logged write path is in):
            E   AssertionError: [group_userset seed=2] driven/BULK-BUILT STATE divergence on the post-removal survivor set (the offline bootstrap does not reproduce the state the logged write path is in):
            FAILED ...[deep_grid]
            FAILED ...[group_userset]
            FAILED ...[nary_union]
            3 failed, 23 passed, 104 deselected in 135.00s (0:02:15)

        Two of the three reds are the DIFFERENTIAL (leg b) and one is leg
        (a)'s I1; re-run with leg (a) neutered the same three are red on leg
        (b) alone, ``3 failed, 23 passed, 104 deselected in 131.79s
        (0:02:11)``.

      * ★ **Leg (e), the constructor pin -- PROVEN BOTH WAYS, 2026-09-20.**
        Both runs are BYTE EDITS of `connectedstore/build.py` (pristine bytes
        restored and `cmp`-verified afterwards), on the 3-param subset
        ``-k "test_graph_remove_bulk_build_survivors and (object_wildcard or
        residue_rich or wildcard_public)"`` -- chosen for the bridge corpus,
        the residue-carrying boolean corpus, and the one whose last seed
        leaves ZERO survivors, so the control is exercised on an empty
        snapshot too. Subset, not the full 26: the arm costs ~170-280s for all
        of them and this pin is per-cell, not per-corpus.

          * M14, the mutation that used to be GREEN (`if bulk:` ->
            `if False:`), i.e. the whole arm silently downgraded to the
            incremental constructor::

                E   AssertionError: bulk_build_drive: build_index ran its 'incremental' constructor, not 'bulk' -- index_v4/bulk_build.py never executed. ...
                3 failed, 127 deselected in 1.49s     rc=1

          * CONTROLLING THE INSTRUMENT -- the refusal above is only worth
            something if `BuildReport.constructor` can ever say anything but
            `'bulk'`. Make the label a constant instead (the else branch's
            ``constructor = 'incremental'`` -> ``constructor = 'bulk'``): the
            refusal goes quiet, as it must, and leg (e)'s control catches it::

                E   AssertionError: [object_wildcard] CONTROL: build_index(bulk=False) reported constructor 'bulk', so `BuildReport.constructor` does not discriminate the two branches and leg (e) -- bulk_build_drive's refusal -- is an assertion that cannot fail.
                3 failed, 127 deselected in 11.87s    rc=1

          * Same subset, unmutated: ``3 passed, 127 deselected in 11.48s``
            rc=0. Whole arm with leg (e) in place, unmutated:
            ``26 passed, 104 deselected in 169.65s (0:02:49)`` rc=0.
    """
    from index_v4.processor import DeltaProcessor
    from zanzibar_utils_v1 import parse_openfga_schema

    schema_text, corpus_tuples, obj_wild = SCHEMAS[name]
    ruleset = parse_openfga_schema(
        schema_text, object_wildcard_shapes=frozenset(obj_wild))
    boolean = ruleset.compiled is not None and bool(ruleset.compiled.plans)

    n_compared = 0
    n_state_rows = 0
    n_derived_state = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        universe = list(corpus_tuples) + _extras(rng, corpus_tuples)
        ops = _sequence(rng, universe)
        # grid over the FULL universe: removed/never-present names stay probed
        queries = queries_for(schema_text, universe)
        assert_grid_nonvacuous(f'{name} seed={seed}', queries)
        n_compared += len(queries)

        session, widx, _proc, store_id, final = graphindex_drive_ops(
            schema_text, ops, obj_wild)
        assert len(final) < len(universe), 'sequence must net-remove something'
        driven_state = _graph_state(session, widx)
        driven_flags = _derived_edge_flags(session, store_id)
        driven = [bool(widx.check(*q)) for q in queries]

        # The OFFLINE bootstrap over the same survivors — a different
        # constructor, not a replay of the same one.
        final_tuples = sorted(final)
        bsession, bwidx, bstore = bulk_build_drive(
            schema_text, final_tuples, obj_wild)

        # (a) the bulk-built index is internally sound on its own terms.
        assert_wildcard_invariants(bwidx)
        if boolean:
            DeltaProcessor(bwidx, ruleset.compiled).audit_fixpoint()   # I9

        bulk_state = _graph_state(bsession, bwidx)
        bulk_flags = _derived_edge_flags(bsession, bstore)
        bulk = [bool(bwidx.check(*q)) for q in queries]

        (d_nodes, d_edges), d_res = driven_state
        n_state_rows += sum(d_nodes.values()) + sum(d_edges.values())
        n_derived_state += sum(c for k, c in driven_flags.items() if k[2])
        n_derived_state += len(d_res)

        # (b) state convergence of the two CONSTRUCTORS.
        assert driven_state == bulk_state, (
            f'[{name} seed={seed}] driven/BULK-BUILT STATE divergence on the '
            f'post-removal survivor set (the offline bootstrap does not '
            f'reproduce the state the logged write path is in):\n'
            f'  driven nodes={driven_state[0][0]}\n  bulk   nodes={bulk_state[0][0]}\n'
            f'  driven edges={driven_state[0][1]}\n  bulk   edges={bulk_state[0][1]}\n'
            f'  driven residues={driven_state[1]}\n  bulk   residues={bulk_state[1]}')

        # (c) the I5 `derived` stamp, which `snapshot_rows` does not carry.
        assert driven_flags == bulk_flags, (
            f'[{name} seed={seed}] driven/BULK-BUILT per-edge `derived` flag '
            f'divergence (I5 provenance stamp):\n'
            f'{_flag_diff(driven_flags, bulk_flags)}')

        # (d) pointwise over the grid.
        mism = [(queries[i], driven[i], bulk[i]) for i in range(len(queries))
                if driven[i] != bulk[i]]
        assert not mism, (
            f'[{name} seed={seed}] driven/bulk-built grid disagreement:\n'
            f'{_fmt(mism, "driven", "bulk")}')

        bsession.close()
        session.close()

    # (e) CONTROL — see the docstring. `bulk_build_drive` has already refused
    # above if `build_index` did not report the 'bulk' constructor; this is the
    # proof that the label can ever say anything else, on the same survivors.
    ctl = _incremental_constructor_label(schema_text, final_tuples, obj_wild)
    assert ctl == 'incremental', (
        f'[{name}] CONTROL: build_index(bulk=False) reported constructor '
        f'{ctl!r}, so `BuildReport.constructor` does not discriminate the two '
        f"branches and leg (e) -- bulk_build_drive's refusal -- is an "
        f'assertion that cannot fail.')

    # ANTI-VACUITY. The grid floor is the shared one; the STATE floors are this
    # arm's own (see `_MIN_BULK_STATE_ROWS` above for why the grid floor does
    # not cover it, and for where these numbers come from).
    assert n_compared >= _MIN_SEQ_COMPARISONS, (
        f'[{name}] ANTI-VACUITY: only {n_compared} (query x store) comparisons '
        f'across {len(SEEDS)} seeds, floor {_MIN_SEQ_COMPARISONS}')
    assert n_state_rows >= _MIN_BULK_STATE_ROWS, (
        f'[{name}] ANTI-VACUITY: the bulk arm compared only {n_state_rows} '
        f'graph state row(s) across {len(SEEDS)} seeds, floor '
        f'{_MIN_BULK_STATE_ROWS}. Two EMPTY indexes compare equal and '
        f'`bulk_build` returns early on an empty node set, so the state '
        f'assertions above can pass having compared nothing.')
    if boolean:
        assert n_derived_state >= _MIN_BULK_DERIVED_STATE, (
            f'[{name}] ANTI-VACUITY: a BOOLEAN corpus whose sweep produced '
            f'{n_derived_state} derived-arm state row(s) (processor-stamped '
            f'edges + residues), floor {_MIN_BULK_DERIVED_STATE} — '
            f'`bulk_backfill.py` is the half of the bulk constructor this arm '
            f'exists to reach, and it wrote nothing to compare.')
