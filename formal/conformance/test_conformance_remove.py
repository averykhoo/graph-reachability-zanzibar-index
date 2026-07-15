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
from formal.conformance.grid import queries_for, fmt_mismatches as _fmt
from formal.conformance import runner
from formal.conformance.backends import (
    _fresh_session, GraphDriver, graphindex_drive_ops)

SEEDS = list(range(5))

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

    for seed in SEEDS:
        rng = random.Random(seed)
        universe = list(corpus_tuples) + _extras(rng, corpus_tuples)
        ops = _sequence(rng, universe)
        # grid over the FULL universe: removed/never-present names stay probed
        queries = queries_for(schema_text, universe)

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
    latter's P2/P6 projections would hide a stale bridge or leaf edge that a
    remove-path residue leak leaves behind, which is exactly what this gate must
    catch."""
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

    for seed in SEEDS:
        rng = random.Random(seed)
        universe = list(corpus_tuples) + _extras(rng, corpus_tuples)
        ops = _sequence(rng, universe)
        # grid over the FULL universe: removed/never-present names stay probed
        queries = queries_for(schema_text, universe)

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
