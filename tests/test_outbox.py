"""
P3 tests (boolean spec §4, §8.3): the delta outbox replaces in-memory delta lists.

  * stream equivalence: the drained outbox range reproduces exactly the flips the
    legacy list API used to return, order included;
  * rollback discards the transaction's outbox rows (deltas are transactional);
  * EdgeV4.derived is set/cleared by processor writes only;
  * the delta-scoped verifier (§8.3) catches a seeded closure-maintenance bug at the
    moment and location it occurs.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from index_v4 import EdgeV4, ReachabilityIndex, Store
from index_v4.invariants import InvariantViolation, verify_outbox_deltas
from index_v4.models import DeltaOutboxV1
from index_v4.outbox import drain_deltas, outbox_rows, outbox_watermark
from zanzibar_utils_v1 import parse_openfga_schema
from tests.wildcard_helpers import make_wildcard_index


@pytest.fixture
def env():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Store(id='s'))
    session.commit()
    yield session, ReachabilityIndex(session, store_id='s')
    session.close()


def _names(session, idx, deltas):
    """Render node-id deltas as (subject, object, action) name triples."""
    out = []
    for d in deltas:
        s = session.get(type(idx.node('...', 'x', 'probe', create_if_missing=True)), d.subject_id)
        o = session.get(type(s), d.object_id)
        out.append(((s.type, s.name, s.predicate), (o.type, o.name, o.predicate), d.action))
    return out


def test_outbox_stream_matches_legacy_flips(env):
    """The canonical transitive scenario: alice->g1 then g1->doc1 emits exactly the
    legacy flips (g1->doc1 direct + alice->doc1 transitive), in emission order."""
    session, idx = env

    idx.add_edge(..., 'user', 'alice', 'member', 'group', 'g1')
    session.commit()
    wm = outbox_watermark(session, 's')

    idx.add_edge('member', 'group', 'g1', 'viewer', 'document', 'doc1')
    session.commit()

    deltas = drain_deltas(session, 's', wm)
    alice = idx.node(..., 'user', 'alice', create_if_missing=False).id
    g1 = idx.node('member', 'group', 'g1', create_if_missing=False).id
    doc = idx.node('viewer', 'document', 'doc1', create_if_missing=False).id

    assert [(d.subject_id, d.object_id, d.action) for d in deltas] == [
        (alice, doc, 'ADDED'),      # transitive expansion emits first (core order)
        (g1, doc, 'ADDED'),         # then the direct edge
    ]
    assert all(d.store_id == 's' for d in deltas)

    # symmetric removal retires both, reverse flips
    wm = outbox_watermark(session, 's')
    idx.remove_edge('member', 'group', 'g1', 'viewer', 'document', 'doc1')
    session.commit()
    deltas = drain_deltas(session, 's', wm)
    assert sorted((d.subject_id, d.object_id, d.action) for d in deltas) == sorted([
        (alice, doc, 'REMOVED'), (g1, doc, 'REMOVED')])


def test_outbox_rows_are_transactional(env):
    """A rolled-back write leaves no outbox rows (deltas are part of the transaction)."""
    session, idx = env
    idx.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
    session.rollback()
    assert outbox_rows(session, 's') == []
    idx.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
    session.commit()
    assert len(outbox_rows(session, 's')) == 1


def test_watermark_keyset_pagination(env):
    session, idx = env
    assert outbox_watermark(session, 's') == 0
    idx.add_edge(..., 'user', 'a', 'viewer', 'document', 'd1')
    session.commit()
    wm1 = outbox_watermark(session, 's')
    idx.add_edge(..., 'user', 'b', 'viewer', 'document', 'd1')
    session.commit()
    assert outbox_watermark(session, 's') > wm1
    assert len(drain_deltas(session, 's', 0)) == 2
    assert len(drain_deltas(session, 's', wm1)) == 1


def test_derived_flag_set_only_by_processor_writes():
    schema = '''
        type user
        type doc
          relations
            define banned: [user]
            define viewer: [user] but not banned
    '''
    rs = parse_openfga_schema(schema, enable_boolean=True)
    session, widx = make_wildcard_index(rs.schema_info)

    # ordinary (leaf) write: no derived flag anywhere
    widx.add_tuple('...', 'user', 'alice', 'viewer.0', 'doc', 'd1')
    session.commit()
    assert all(not e.derived for e in session.exec(select(EdgeV4)).all())

    # processor write into the derived-public family: direct edge flagged
    widx.processor_writes = True
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    widx.processor_writes = False
    session.commit()
    flagged = [e for e in session.exec(select(EdgeV4)).all() if e.derived]
    assert len(flagged) == 1 and flagged[0].direct_edge_count == 1

    # processor removal clears it (row deleted entirely here)
    widx.processor_writes = True
    widx.remove_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    widx.processor_writes = False
    session.commit()
    assert all(not e.derived for e in session.exec(select(EdgeV4)).all())
    session.close()


# ---------------------------------------------------------------------------
# Delta-scoped verification (§8.3): catches maintenance bugs at their moment
# ---------------------------------------------------------------------------

def test_delta_verifier_clean_on_real_ops(env):
    session, idx = env
    wm = outbox_watermark(session, 's')
    idx.add_edge(..., 'user', 'alice', 'member', 'group', 'g1')
    idx.add_edge('member', 'group', 'g1', 'viewer', 'document', 'doc1')
    session.flush()
    verify_outbox_deltas(session, 's', wm)      # no violation


def test_delta_verifier_catches_seeded_closure_bug(env):
    """Seed the classic maintenance bug: a direct edge row written WITHOUT its
    transitive closure rows. The emitted delta then disagrees with BFS-over-direct
    for the missing transitive pair -- exactly what §8.3 exists to catch."""
    session, idx = env
    idx.add_edge(..., 'user', 'alice', 'member', 'group', 'g1')
    session.commit()
    wm = outbox_watermark(session, 's')

    # bug simulation: add g1->doc1 direct row + its outbox flip, but "forget" the
    # transitive alice->doc1 closure row (bypassing _add_direct_edge_unsafe).
    g1 = idx.node('member', 'group', 'g1', create_if_missing=False)
    doc = idx.node('viewer', 'document', 'doc1', create_if_missing=True)
    alice = idx.node(..., 'user', 'alice', create_if_missing=False)
    session.add(EdgeV4(store_id='s', subject_id=g1.id, object_id=doc.id,
                       direct_edge_count=1, indirect_edge_count=1))
    session.add(DeltaOutboxV1(store_id='s', subject_node_id=g1.id,
                              object_node_id=doc.id, action='ADDED'))
    # the missing closure row means alice->doc is BFS-reachable but has no row; a
    # delta for that pair makes the verifier compare the two:
    session.add(DeltaOutboxV1(store_id='s', subject_node_id=alice.id,
                              object_node_id=doc.id, action='ADDED'))
    session.flush()

    with pytest.raises(InvariantViolation, match='delta-scoped'):
        verify_outbox_deltas(session, 's', wm)
    session.rollback()


def test_delta_verifier_catches_false_removal_claim(env):
    """An outbox row claiming REMOVED while the pair is still reachable must fail."""
    session, idx = env
    idx.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
    session.commit()
    wm = outbox_watermark(session, 's')

    alice = idx.node(..., 'user', 'alice', create_if_missing=False)
    doc = idx.node('viewer', 'document', 'doc1', create_if_missing=False)
    session.add(DeltaOutboxV1(store_id='s', subject_node_id=alice.id,
                              object_node_id=doc.id, action='REMOVED'))
    session.flush()

    with pytest.raises(InvariantViolation, match='delta-scoped'):
        verify_outbox_deltas(session, 's', wm)
    session.rollback()


def test_paranoia_runs_delta_verifier_per_commit():
    """make_wildcard_index wires §8.3 into every commit: a seeded bad delta aborts."""
    schema = '''
        type user
        type doc
          relations
            define viewer: [user]
    '''
    rs = parse_openfga_schema(schema)
    session, widx = make_wildcard_index(rs.schema_info)
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    session.commit()

    alice = widx.idx.node('...', 'user', 'alice', create_if_missing=False)
    d1 = widx.idx.node('viewer', 'doc', 'd1', create_if_missing=False)
    session.add(DeltaOutboxV1(store_id='test', subject_node_id=d1.id,
                              object_node_id=alice.id, action='ADDED'))
    with pytest.raises(InvariantViolation):
        session.commit()
    session.rollback()
    session.close()
