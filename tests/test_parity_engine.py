"""
P1 verification foundation (boolean spec §8.1/§8.2/§8.4):

  * ParityEngine drives the handwritten scenarios and randomized walks -- every op
    fans out to oracle + set engine (both SetOps) + graph (when the schema compiles),
    with unanimous accept/reject, I12 rejection cleanliness, and full-grid check parity
    asserted per op *inside* the engine.
  * The invariant checker (index_v4.invariants) catches deliberately-corrupted stores:
    each seeded mutation class (I1 counts, I2 acyclicity, I3 bridge hygiene) must raise
    InvariantViolation -- proving the checker can actually see the bugs paranoia mode
    exists to catch.
  * Paranoia commit wiring: a corrupted pending state aborts its commit pre-commit.
"""

import random

import pytest
from sqlmodel import select

from index_v4 import EdgeV4
from index_v4.invariants import InvariantViolation, check_invariants
from zanzibar_utils_v1 import SchemaInfo, parse_openfga_schema
from tests.parity import ParityEngine
from tests.scenarios import SCENARIOS
from tests.test_wildcard_property import _candidate_raw_tuples, OBJECT_WC
from tests.wildcard_helpers import make_wildcard_index


# ---------------------------------------------------------------------------
# ParityEngine over the handwritten scenarios (the human anchor, spec §8.4)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('scn', SCENARIOS, ids=lambda s: s['name'])
def test_parity_engine_scenarios(scn):
    pe = ParityEngine(scn['schema'],
                      object_wildcard_shapes=frozenset(scn.get('object_wildcard_shapes', frozenset())))
    for op in scn['ops']:
        accepted = pe.add_tuple(*op)
        assert accepted, f'{scn["name"]}: scenario op unexpectedly rejected: {op}'
    for *query, expected in scn['expect']:
        got = pe.check(*tuple(query))
        assert got is expected, f'{scn["name"]}: {tuple(query)} -> {got}, expected {expected}'
    pe.close()


# ---------------------------------------------------------------------------
# ParityEngine random walks: 4-way on the wildcard fixture, 3-way on the boolean
# fixture until the P7 flip widens it automatically.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('seed', [0, 1])
def test_parity_engine_walk_union_wildcards(load_fga_schema, seed):
    schema = load_fga_schema('wildcards.fga')
    pe = ParityEngine(schema, object_wildcard_shapes=OBJECT_WC, seed=seed)
    assert pe.graph is not None, 'union+wildcard schema must include the graph backend'

    pool = _candidate_raw_tuples()
    rng = random.Random(seed)
    present = set()
    for _ in range(10):
        if not present or rng.random() < 0.65:
            cands = [r for r in pool if r not in present]
            op, raw = ('add', rng.choice(cands)) if cands else ('remove', rng.choice(sorted(present)))
        else:
            op, raw = 'remove', rng.choice(sorted(present))
        accepted = (pe.add_tuple if op == 'add' else pe.remove_tuple)(*raw)
        if accepted:
            (present.add if op == 'add' else present.discard)(raw)
    pe.close()


def test_parity_engine_boolean_runs_four_way_post_flip(load_fga_schema):
    """Post-P7: the boolean fixture compiles for the graph too -- the ParityEngine
    seam widens to 4-way automatically (graph + oracle + both set engines), with the
    processor cascade inside every graph write."""
    schema = load_fga_schema('boolean_wildcards.fga')
    pe = ParityEngine(schema)
    assert pe.graph is not None, 'graph backend must join boolean schemas post-flip'
    assert pe.graph.proc is not None, 'boolean graph backend needs the delta processor'

    pe.add_tuple('...', 'user', '*', 'public', 'doc', 'd1')
    pe.add_tuple('...', 'user', 'u1', 'blocked', 'doc', 'd1')
    pe.add_tuple('...', 'user', 'u2', 'editor', 'doc', 'd1')
    # viewer = (public but not blocked) or editor -- check() asserts 4-way unanimity
    assert pe.check('...', 'user', 'u2', 'viewer', 'doc', 'd1') is True    # editor arm
    assert pe.check('...', 'user', 'u1', 'viewer', 'doc', 'd1') is False   # blocked defeats star
    assert pe.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1') is True # star-covered ghost
    assert pe.check('...', 'user', '*', 'viewer', 'doc', 'd1') is True     # intensional
    pe.close()


def test_parity_engine_rejection_cleanliness_i12():
    """An op rejected by every backend must leave every backend's rows untouched."""
    schema = '''
        type user
        type doc
          relations
            define viewer: [user]
    '''
    pe = ParityEngine(schema)
    pe.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    # removing a never-added tuple: unanimous reject + I12 snapshots compare equal
    assert pe.remove_tuple('...', 'user', 'bob', 'viewer', 'doc', 'd1') is False
    # state is intact and still in lockstep
    assert pe.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True
    pe.close()


# ---------------------------------------------------------------------------
# Deliberately-broken mutations: the checker must catch each seeded corruption
# (P1 accept criterion)
# ---------------------------------------------------------------------------

_PLAIN = '''
    type user
    type doc
      relations
        define viewer: [user]
'''

_WILD = '''
    type user
    type group
      relations
        define member: [user]
    type doc
      relations
        define viewer: [user, group#member, group:*#member]
'''


def _plain_widx():
    rs = parse_openfga_schema(_PLAIN)
    # paranoia off: these tests corrupt state on purpose and invoke the checker by hand
    session, widx = make_wildcard_index(rs.schema_info, paranoia=False)
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    session.commit()
    return session, widx


def test_checker_catches_i1_zero_indirect():
    session, widx = _plain_widx()
    edge = session.exec(select(EdgeV4)).first()
    edge.indirect_edge_count = 0                     # stale zero-reachability row
    session.add(edge)
    session.flush()
    with pytest.raises(InvariantViolation, match='I1'):
        check_invariants(session, 'test', widx.schema_info)
    session.close()


def test_checker_catches_i1_indirect_below_direct():
    session, widx = _plain_widx()
    edge = session.exec(select(EdgeV4)).first()
    edge.direct_edge_count = edge.indirect_edge_count + 1
    session.add(edge)
    session.flush()
    with pytest.raises(InvariantViolation, match='I1'):
        check_invariants(session, 'test', widx.schema_info)
    session.close()


def test_checker_catches_i2_direct_cycle():
    session, widx = _plain_widx()
    idx = widx.idx
    a = idx.node('...', 'user', 'alice', create_if_missing=False)
    d = idx.node('viewer', 'doc', 'd1', create_if_missing=False)
    # close the loop behind the core's back: d1#viewer -> alice
    session.add(EdgeV4(store_id='test', subject_id=d.id, object_id=a.id,
                       direct_edge_count=1, indirect_edge_count=1))
    session.flush()
    with pytest.raises(InvariantViolation, match='I2'):
        check_invariants(session, 'test', widx.schema_info)
    session.close()


def test_checker_catches_i3_unjustified_bridge():
    """A concrete->w_any bridge for a shape the schema never declared bridged."""
    rs = parse_openfga_schema(_WILD)
    session, widx = make_wildcard_index(rs.schema_info, paranoia=False)
    widx.add_tuple('member', 'group', 'g1', 'viewer', 'doc', 'd1')  # creates (group,member) concrete
    session.commit()
    idx = widx.idx
    g1 = idx.node('member', 'group', 'g1', create_if_missing=False)
    # forge a w_any(doc, viewer) and bridge d1's viewer node into it -- never declared
    d1 = idx.node('viewer', 'doc', 'd1', create_if_missing=False)
    w = idx.node('viewer', 'doc', '*', create_if_missing=True, implicit=True, wildcard='any')
    session.add(EdgeV4(store_id='test', subject_id=d1.id, object_id=w.id,
                       direct_edge_count=1, indirect_edge_count=1))
    session.flush()
    with pytest.raises(InvariantViolation, match='I3'):
        check_invariants(session, 'test', widx.schema_info)
    assert g1 is not None
    session.close()


def test_checker_catches_i3_missing_bridge():
    """A concrete of a bridged shape whose bridge was deleted behind the façade's back."""
    rs = parse_openfga_schema(_WILD)
    assert ('group', 'member') in rs.schema_info.bridged_in_shapes
    session, widx = make_wildcard_index(rs.schema_info, paranoia=False)
    # (group, member) is a bridged-in shape, so this write bridges g1#member -> w_any
    widx.add_tuple('member', 'group', 'g1', 'viewer', 'doc', 'd1')
    session.commit()
    idx = widx.idx
    g1 = idx.node('member', 'group', 'g1', create_if_missing=False)
    w_any = idx.node('member', 'group', '*', create_if_missing=False, wildcard='any')
    bridge = session.exec(
        select(EdgeV4).where(EdgeV4.subject_id == g1.id).where(EdgeV4.object_id == w_any.id)
    ).first()
    assert bridge is not None
    session.delete(bridge)
    session.flush()
    with pytest.raises(InvariantViolation, match='I3'):
        check_invariants(session, 'test', widx.schema_info)
    session.close()


def test_paranoia_aborts_corrupted_commit():
    """Pre-commit checker inside the transaction: corruption never reaches disk."""
    rs = parse_openfga_schema(_PLAIN)
    session, widx = make_wildcard_index(rs.schema_info, paranoia=True)
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    session.commit()                                  # clean state commits fine

    edge = session.exec(select(EdgeV4)).first()
    edge.indirect_edge_count = 0
    session.add(edge)
    with pytest.raises(InvariantViolation):
        session.commit()                              # paranoia aborts the commit
    session.rollback()

    # the corruption never landed; the store is still consistent
    check_invariants(session, 'test', widx.schema_info)
    assert widx.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True
    session.close()
