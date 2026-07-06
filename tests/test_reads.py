"""
P5: reads (boolean spec §6, §11-P5).

  * untainted check is ONE edge-probe SQL statement (all ≤4 probe keys in a single
    row-value IN ... LIMIT 1) -- asserted with a cursor-level statement counter;
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

    # warm the w-id cache (it is read-path state, invalidated by writes)
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
