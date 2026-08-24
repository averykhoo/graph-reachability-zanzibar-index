"""
P5: reads (boolean spec §6, §11-P5).

  * untainted check is ONE edge-probe SQL statement (all ≤4 probe keys in a single
    row-value IN ... LIMIT 1) -- asserted with a cursor-level statement counter, and
    since R6-6 (2026-08-24d) ONE node-resolution statement in front of it, with each
    of the four probe keys pinned individually decisive (that block carries its own
    sabotage record);
  * derived check: edge probe + residue (intensional '*', ghost coverage, neg);
  * lookup/lookup_reverse extensions: derived edges arrive naturally, residues render
    as markers + excluded_node_ids, star-covered memberships join lookup();
  * full-grid check parity with the oracle on ALL FOUR boolean fixtures, after every
    accepted op of a randomized walk (the graph backend driven through the processor).
"""

import random
from contextlib import contextmanager

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from setengine import SetEngine, ALL_SETOPS
from zanzibar_utils_v1 import parse_openfga_schema
from tests.oracle import Oracle, OracleTuple
from tests.test_processor import build
from tests.test_matrix import _boolean_pool, _boolean_grid, _demorgan_pool
from tests.wildcard_helpers import make_wildcard_index


# ---------------------------------------------------------------------------
# Statement counting: the untainted single-round-trip guarantee
# ---------------------------------------------------------------------------

@contextmanager
def _count_statements(session):
    statements: list[str] = []
    engine = session.get_bind()

    def counter(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, 'before_cursor_execute', counter)
    try:
        yield statements
    finally:
        event.remove(engine, 'before_cursor_execute', counter)


def test_untainted_check_is_one_edge_statement(load_fga_schema):
    rs = parse_openfga_schema(load_fga_schema('wildcards.fga'))
    session, widx = make_wildcard_index(rs.schema_info)
    widx.add_tuple('...', 'user', '*', 'viewer', 'folder', 'root')
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'folder', 'root')
    session.commit()

    # One warm-up call so the counted ones are steady-state. It caches NOTHING:
    # w-node resolution is deliberately uncached across calls (W2,
    # `WildcardIndex._w_node`) and the N15 node cache is not installed outside a write
    # batch. (This line used to say "warm the w-id cache", which has not been true
    # since W2 -- R6-6/TK47, 2026-08-24d.)
    widx.check('...', 'user', 'alice', 'viewer', 'folder', 'root')

    for q, expected in [
        (('...', 'user', 'alice', 'viewer', 'folder', 'root'), True),
        (('...', 'user', 'ghost', 'viewer', 'folder', 'root'), True),   # star coverage
        (('...', 'user', 'ghost', 'viewer', 'folder', 'other'), False),
    ]:
        with _count_statements(session) as stmts:
            assert widx.check(*q) is expected, q
        edge_probes = [s for s in stmts if 'edge_v4' in s.lower()]
        assert len(edge_probes) <= 1, \
            f'{q}: expected at most one edge-probe statement, got {len(edge_probes)}:\n' \
            + '\n'.join(edge_probes)
        # positive checks must issue exactly one probe (a no-key miss may issue zero)
        if expected:
            assert len(edge_probes) == 1, q
    session.close()


# --- R6-6: the node resolution in FRONT of that probe is batched too -------------
#
# The probe above was always one statement; the up-to-4 identity resolutions feeding
# it were not (subject, object, w_any, w_all -- a `_db_node` point SELECT each,
# measured at 4.00 node_v4 statements per check on `profile_r6 --target graph-check`).
# They are now one row-value IN through `ReachabilityIndex.resolve_node_ids`.
#
# Batching a set of point lookups has exactly one interesting failure mode -- a key
# that silently stops participating -- and it fails OPEN or CLOSED depending on which
# key is dropped, while the statement count still looks perfect. So the count pin
# below is deliberately paired with `test_all_four_probe_keys_survive_the_batched_
# resolution`, which makes each of the four keys individually decisive. Neither test
# is redundant with the other: the first cannot see a dropped key, and the second
# cannot see a regression to four statements.
#
# ---------------------------------------------------------------------------------
# SABOTAGE (`docs/sabotage-procedure.md`; literal observed output, 2026-08-24d)
# ---------------------------------------------------------------------------------
#
# Eight sabotages, each the narrowest plausible weakening of ONE property of
# `ReachabilityIndex.resolve_node_ids`, applied by `-p` plugin monkeypatch (never by
# editing the source, so there is no restore step to get wrong). Baseline on the same
# tree with the fix in place:
#
#     $ python -m pytest tests/test_reads.py -q
#     25 passed in 42.50s
#
#   S1  keep the cache handling, lose the BATCH (one point SELECT per miss -- the
#       pre-R6-6 shape, and nothing else about the change):
#           2 failed, 23 passed in 52.67s
#           FAILED ...::test_untainted_check_resolves_its_node_ids_in_one_statement
#           FAILED ...::test_batched_resolution_serves_and_populates_the_n15_node_cache
#       The second is that test's own non-vacuity assertion (`cold cache should still
#       resolve once`) reading 4 instead of 1, not a second finding.
#
#   S2/S3/S2b/S3b  drop ONE key from the batch -- an off-by-one in the assembly.
#       Each reddens exactly the two probe cases whose surviving probe mentions that
#       key, which is the whole decisiveness claim, verified rather than asserted:
#           drop w_all -> [3 subj->w_all], [4 w_any->w_all]     2 failed, 23 passed
#           drop w_any -> [2 w_any->obj],  [4 w_any->w_all]     8 failed, 17 passed
#           drop obj   -> [1 subj->obj],   [2 w_any->obj]      18 failed,  7 passed
#           drop subj  -> [1 subj->obj],   [3 subj->w_all]     17 failed,  8 passed
#       ★ **drop-w_all is the one worth reading.** It is `2 failed, 23 passed` -- the
#       ONLY two reds in this module are the two new cases. Every other test here,
#       including all nine oracle grid-parity tests, stayed green while a real
#       under-grant was live. Widened to the headline nets it IS caught, so this is a
#       module-local blind spot and not a project-wide one:
#           $ SAB=s2 pytest tests/test_matrix.py tests/test_lookup_oracle.py \
#                 tests/test_wildcard_property.py -q -p sab_r66_plugin
#           4 failed, 56 passed in 106.82s      (baseline: 60 passed in 116.30s)
#           FAILED tests/test_matrix.py::test_matrix_4way_union_wildcard[0], [1]
#           FAILED tests/test_wildcard_property.py::test_wildcard_property_vs_oracle[0], [1]
#       `tests/test_lookup_oracle.py` -- **45** of those 60, from
#       `pytest tests/test_lookup_oracle.py -q --collect-only`, not from a run's tail
#       -- stayed fully green: the lookup surface never assembles a w_all probe key.
#       The other three drops are catastrophes rather than probes (7-17 collateral
#       reds), and per the procedure they are recorded but carry little attribution.
#
#   S4  map the returned rows back onto the requested keys BY POSITION (assuming a
#       row-value IN returns rows in IN-list order -- the fail-OPEN mistake a
#       dict-keyed batch cannot make):  14 failed, 11 passed in 24.20s.
#       Also a catastrophe; it does redden [1] and [2] plus the negative controls.
#
#   S5  read the N15 cache but never populate it ("caching is the write path's job"):
#           1 failed, 24 passed in 41.83s
#           FAILED ...::test_batched_resolution_serves_and_populates_the_n15_node_cache
#       Exactly one red, and it is the write-path regression this pin exists for.
#
#   S6  populate hits but not misses:  1 failed, 24 passed in 42.15s -- the same
#       single red.
#       ★ **A green finding, recorded rather than dropped** (`sabotage-procedure.md`:
#       a green sabotage is a finding): S6 leaves
#       `test_a_node_created_inside_the_scope_is_seen_by_the_next_resolution` GREEN,
#       because a negative entry that is never written cannot go stale. No narrow
#       sabotage of `resolve_node_ids` reddens that test alone -- it fires only under
#       the catastrophic key-drops. It is kept deliberately, as the net for a future
#       change to `node`'s creation-site invalidation, which is the thing that makes
#       writing negative entries here safe at all. It is a regression net, not
#       evidence for this change.

_R66_SCHEMA = '''
type user
type doc
  relations
    define viewer: [user, user:*]
'''
#: `('doc','viewer')` as an OBJECT wildcard shape (no DSL syntax -- spec §1.3, passed
#: to the parser) makes this the DOUBLY-declared shape: `w_any(user,'...')` from
#: `user:*` in the DSL and `w_all(doc,viewer)` from here. That is the only
#: configuration in which `check` assembles all four probe keys, i.e. the only one
#: that measures what R6-6 is about.
_R66_OWC = frozenset({('doc', 'viewer')})


def _r66_index(store_id='r66'):
    rs = parse_openfga_schema(_R66_SCHEMA, object_wildcard_shapes=_R66_OWC)
    return make_wildcard_index(rs.schema_info, store_id=store_id)


def _node_statements(stmts):
    return [s for s in stmts if 'node_v4' in s.lower() and 'edge_v4' not in s.lower()]


def test_untainted_check_resolves_its_node_ids_in_one_statement():
    """R6-6: ONE node_v4 statement per untainted check, not one per identity.

    The floor is derived, not tuned: `check` needs up to four node ids and they are
    independent, so one row-value IN over `node_v4_unique_constraint` answers all of
    them (`ReachabilityIndex.resolve_node_ids`). Asserting `== 1` rather than `<= 4`
    is the point -- the pre-R6-6 code passed `<= 4`.

    ⚠ `== 1` and not `<= 1`: zero node statements would mean the resolution stopped
    happening at all (or the counter stopped seeing it), which must not read as an
    even better result. Same reason the edge-probe test above asserts `== 1` on the
    positive cases.
    """
    session, widx = _r66_index()
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    session.commit()
    widx.check('...', 'user', 'alice', 'viewer', 'doc', 'd1')     # steady state

    for q, expected in [
        (('...', 'user', 'alice', 'viewer', 'doc', 'd1'), True),
        (('...', 'user', 'ghost', 'viewer', 'doc', 'd1'), False),   # missing subject
        (('...', 'user', 'alice', 'viewer', 'doc', 'd9'), False),   # missing object
        (('...', 'user', '*', 'viewer', 'doc', 'd1'), False),       # star endpoint
    ]:
        with _count_statements(session) as stmts:
            assert widx.check(*q) is expected, q
        nodes = _node_statements(stmts)
        assert len(nodes) == 1, (
            f'{q}: expected exactly ONE batched node-resolution statement, got '
            f'{len(nodes)}:\n' + '\n'.join(nodes))
    session.close()


#: (label, grant, query) -- one row per probe. The QUERY is what isolates the probe,
#: and it is what the first draft of this test got wrong (see the docstring).
_R66_PROBES = [
    ('1 subj->obj',
     ('...', 'user', 'alice', 'viewer', 'doc', 'd1'),
     ('...', 'user', 'alice', 'viewer', 'doc', 'd1')),
    ('2 w_any->obj',
     ('...', 'user', '*', 'viewer', 'doc', 'd1'),
     ('...', 'user', 'ghost', 'viewer', 'doc', 'd1')),
    ('3 subj->w_all',
     ('...', 'user', 'alice', 'viewer', 'doc', '*'),
     ('...', 'user', 'alice', 'viewer', 'doc', 'dghost')),
    ('4 w_any->w_all',
     ('...', 'user', '*', 'viewer', 'doc', '*'),
     ('...', 'user', 'ghost', 'viewer', 'doc', 'dghost')),
]


@pytest.mark.parametrize('label,grant,query', _R66_PROBES,
                         ids=[p[0] for p in _R66_PROBES])
def test_all_four_probe_keys_survive_the_batched_resolution(label, grant, query):
    """R6-6: each of the four probe keys is INDIVIDUALLY decisive after batching.

    Batching a set of point lookups has one interesting failure mode -- a key that
    silently stops participating -- and a statement count cannot see it. So each case
    grants exactly one shape and asks a query only THAT probe's key can answer.

    ⚠ **The query, not the grant, is what isolates the probe, and the first draft of
    this test got that wrong.** It asked `check(alice, d1)` in all four cases and was
    GREEN under a sabotage that dropped the `w_all` key entirely (2026-08-24d;
    `docs/sabotage-procedure.md`: a green pin under a sabotage that should break it is
    a verdict on the pin). The closure is fully materialized, so with `doc:d1` interned
    the bridge `alice -> w_all -> d1` is a real EDGE and probe 1 answers on its own;
    probes 3 and 4 exist precisely for the case where the endpoint node does NOT exist,
    and only a GHOST endpoint reaches them. Hence `dghost` / `ghost` above: a missing
    node contributes no id, which drops every probe key that mentions it and leaves
    exactly one standing.

    Verified by construction: dropping key *k* from the batch reddens exactly the two
    cases whose surviving probe mentions it (`subj`->1,3; `obj`->1,2; `w_any`->2,4;
    `w_all`->3,4). The literal runs are in `docs/perf-round6-audit-2026-08.md`'s R6-6
    landing note.
    """
    session, widx = _r66_index()
    widx.add_tuple(*grant)
    session.commit()
    assert widx.check(*query) is True, \
        f'probe {label}: grant {grant} no longer answers {query} -- key lost in the batch'
    session.close()


@pytest.mark.parametrize('label,grant,query', _R66_PROBES,
                         ids=[p[0] for p in _R66_PROBES])
def test_all_four_probe_keys_negative_control(label, grant, query):
    """The control: with NO grant at all, every one of those queries is False.

    Without it the case above could be passing on something ambient in the fixture
    (an implicitly interned node, a bridge built for another reason) rather than on
    the grant, and the parametrization would be decoration. It is also the pin that a
    dropped key cannot make green: a fail-OPEN mis-mapping shows up here.
    """
    session, widx = _r66_index()
    widx.add_tuple('...', 'user', 'bob', 'viewer', 'doc', 'other')   # unrelated traffic
    session.commit()
    assert widx.check(*query) is False, f'probe {label}: {query} granted by nothing'
    session.close()


def test_batched_resolution_serves_and_populates_the_n15_node_cache():
    """R6-6 must not regress the WRITE path, where `_check_internal` is also reached
    (`processor.py::_EvalContext.leaf_check`) and the N15 batch cache IS installed.

    `resolve_node_ids` reads and writes that cache exactly as `node` does, so a repeat
    resolution inside one scope costs ZERO statements -- a fresh batched SELECT per
    call would have been strictly worse than the four cached point lookups it replaced.
    Both halves are asserted: the first call still pays one (non-vacuity -- a cache
    that was never consulted would also report zero on the second), the second pays
    none.
    """
    session, widx = _r66_index()
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    session.commit()
    q = ('...', 'user', 'alice', 'viewer', 'doc', 'd1')

    with widx.idx._node_cache_scope():
        with _count_statements(session) as first:
            assert widx.check(*q) is True
        assert len(_node_statements(first)) == 1, 'cold cache should still resolve once'
        with _count_statements(session) as second:
            assert widx.check(*q) is True
        assert len(_node_statements(second)) == 0, \
            'the batched resolution bypassed the N15 cache -- write-path regression'
    session.close()


def test_a_node_created_inside_the_scope_is_seen_by_the_next_resolution():
    """The negative-cache half of the same coherence contract.

    A miss recorded by `resolve_node_ids` is stored as `_MISSING`, so it must be
    overwritten when that identity is created later in the SAME batch -- otherwise a
    read that ran before the write answers from a stale absence. `node` is the sole
    creation choke point and overwrites the entry (N15); this pins that the entry
    `resolve_node_ids` writes is subject to the same rule.
    """
    session, widx = _r66_index()
    with widx.idx._node_cache_scope():
        assert widx.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is False
        widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
        assert widx.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True, \
            'a negative cache entry survived creation of the node it denied'
    session.commit()
    session.close()


def test_read_purity_i11(load_fga_schema):
    """Reads never intern or create nodes (I11: row counts unchanged)."""
    from index_v4.invariants import snapshot_rows
    session, widx, proc, write = build('''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define viewer: public but not blocked
    ''')
    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
    write('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd1'))
    before = snapshot_rows(session, 'test')

    widx.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1')
    widx.check('...', 'user', '*', 'viewer', 'doc', 'd1')
    widx.check('...', 'user', 'alice', 'viewer', 'doc', 'd9')      # untouched object
    widx.lookup('...', 'user', 'ghost')
    widx.lookup_reverse('viewer', 'doc', 'd1')

    assert snapshot_rows(session, 'test') == before
    session.close()


# ---------------------------------------------------------------------------
# Derived check via the public read path
# ---------------------------------------------------------------------------

def test_derived_check_via_facade():
    session, widx, proc, write = build('''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define editor: [user]
            define viewer: (public but not blocked) or editor
    ''')
    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
    write('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd1'))
    write('add', ('...', 'user', 'bob', 'editor', 'doc', 'd1'))

    assert widx.check('...', 'user', 'bob', 'viewer', 'doc', 'd1') is True     # edge
    assert widx.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1') is True   # stars
    assert widx.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is False  # neg
    assert widx.check('...', 'user', '*', 'viewer', 'doc', 'd1') is True       # intensional
    assert widx.check('...', 'user', 'ghost', 'viewer', 'doc', 'nope') is False
    session.close()


def test_derived_lookup_reverse_markers_and_exclusions():
    session, widx, proc, write = build('''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define editor: [user]
            define viewer: (public but not blocked) or editor
    ''')
    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
    write('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd1'))
    write('add', ('...', 'user', 'bob', 'editor', 'doc', 'd1'))

    res = widx.lookup_reverse('viewer', 'doc', 'd1')
    alice = widx.idx.node('...', 'user', 'alice', create_if_missing=False)

    # canonical representation: star coverage owns every user-shaped member (bob
    # included -- covered members hold no edge), minus the excluded set
    assert ('user', '...', 'any') in res.markers
    assert res.excluded_node_ids == {alice.id}          # "everyone except alice"
    assert res.node_ids == set()                        # no concrete derived edges

    # a subject OUTSIDE the starred shape keeps its concrete edge
    session2, widx2, proc2, write2 = build('''
        type user
        type group
          relations
            define member: [user]
        type doc
          relations
            define blocked: [user]
            define editor: [user, group#member]
            define viewer: editor but not blocked
    ''')
    write2('add', ('...', 'user', 'bob', 'editor', 'doc', 'd1'))
    res2 = widx2.lookup_reverse('viewer', 'doc', 'd1')
    bob2 = widx2.idx.node('...', 'user', 'bob', create_if_missing=False)
    assert bob2.id in res2.node_ids                     # concrete derived edge
    assert res2.markers == set() and res2.excluded_node_ids == set()
    session2.close()
    session.close()


def test_derived_lookup_includes_star_covered_objects():
    session, widx, proc, write = build('''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define editor: [user]
            define viewer: (public but not blocked) or editor
    ''')
    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
    write('add', ('...', 'user', '*', 'public', 'doc', 'd2'))
    write('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd2'))
    write('add', ('...', 'user', 'alice', 'editor', 'doc', 'd3'))

    def viewer_objects(name):
        res = widx.lookup('...', 'user', name)
        out = set()
        for nid in res.node_ids:
            n = widx._node_by_id(nid)
            if n is not None and (n.type, n.predicate) == ('doc', 'viewer'):
                out.add(n.name)
        return out

    # alice: d1 via star, d3 via concrete edge; d2 excluded by neg
    assert viewer_objects('alice') == {'d1', 'd3'}
    # ghost: star coverage only
    assert viewer_objects('ghost') == {'d1', 'd2'}
    session.close()


# ---------------------------------------------------------------------------
# The P5 acceptance: full-grid check parity with the oracle on boolean fixtures
# ---------------------------------------------------------------------------

def _fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _walk_and_compare(schema, pool, grid, seed, steps=14):
    """Drive a randomized walk on the graph backend (processor-wired); mirror every
    graph-accepted op onto both set engines; compare the FULL grid on graph, both set
    engines, and the oracle after every op."""
    g_session, widx, proc, write = build(schema)
    sets = []
    for ops in ALL_SETOPS:
        s = _fresh_session()
        sets.append((SetEngine(s, 'w', schema, ops=ops), s))

    rng = random.Random(seed)
    present, history = set(), []
    for _ in range(steps):
        if not present or rng.random() < 0.6:
            cands = [r for r in pool if r not in present]
            op, raw = ('add', rng.choice(cands)) if cands else ('remove', rng.choice(sorted(present)))
        else:
            op, raw = 'remove', rng.choice(sorted(present))

        try:
            write(op, raw)
        except ValueError:
            g_session.rollback()
            continue        # graph rejected (e.g. userset cycle): keep all backends in sync by skipping
        for se, s in sets:
            (se.add_tuple if op == 'add' else se.remove_tuple)(*raw)
            s.commit()
        (present.add if op == 'add' else present.discard)(raw)
        history.append((op, raw))

        oracle = Oracle(schema, [OracleTuple(*r) for r in present])
        for q in grid:
            expected = oracle.check(*q)
            got_g = widx.check(*q)
            if got_g != expected:
                pytest.fail(f'graph/oracle mismatch seed={seed} q={q} graph={got_g} '
                            f'oracle={expected}\n' + '\n'.join(f'  {o} {r}' for o, r in history))
            for se, _ in sets:
                got_s = se.check(*q)
                if got_s != expected:
                    pytest.fail(f'set/oracle mismatch seed={seed} q={q} set={got_s} '
                                f'oracle={expected}')

    proc.audit_fixpoint()
    g_session.close()
    for _, s in sets:
        s.close()


@pytest.mark.parametrize('seed', [0, 1, 2])
def test_grid_parity_boolean_wildcards(load_fga_schema, seed):
    schema = load_fga_schema('boolean_wildcards.fga')
    _walk_and_compare(schema, _boolean_pool(), _boolean_grid(), seed)


@pytest.mark.parametrize('fixture', ['demorgans_law_1.fga', 'demorgans_law_2.fga',
                                     'demorgans_reverse.fga'])
@pytest.mark.parametrize('seed', [0, 1])
def test_grid_parity_demorgans(load_fga_schema, fixture, seed):
    from zanzibar_utils_v1 import parse_schema_ast
    schema = load_fga_schema(fixture)
    pool = _demorgan_pool(schema)
    ast = parse_schema_ast(schema)

    subjects = [('...', 'user', 'a'), ('...', 'user', 'ghost'), ('...', 'user', '*'),
                ('...', 'doc', 'dc1'), ('...', 'doc', '*'),
                ('...', 'cond', 'c1'), ('...', 'attr', 'at1'), ('...', 'role', 'r1')]
    grid = [(sp, st, sn, rel, ot, on)
            for (ot, rel) in sorted(ast)
            for (sp, st, sn) in subjects
            for on in ['dc1', 'r1', 'c1', 'at1', 'g1', 'ghost']]

    _walk_and_compare(schema, pool, grid, seed, steps=10)
