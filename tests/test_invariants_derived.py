"""
P6 (boolean spec §8.2, §5.5): the derived-state invariants I4-I7/I10 catch seeded
corruption; backfill bootstraps a bulk-loaded store to the exact live-maintained
state and doubles as the residue recovery path.
"""

import json

import pytest
from sqlmodel import select

from index_v4 import EdgeV4
from index_v4.invariants import InvariantViolation, check_invariants, snapshot_rows
from index_v4.models import DeltaOutboxV1, ResidueV1
from index_v4.processor import DeltaProcessor
from zanzibar_utils_v1 import Entity, RelationalTriple, parse_openfga_schema
from tests.test_processor import build
from tests.wildcard_helpers import make_wildcard_index

_SCHEMA = '''
    type user
    type doc
      relations
        define public: [user:*]
        define blocked: [user]
        define editor: [user]
        define viewer: (public but not blocked) or editor
'''


def _populated():
    session, widx, proc, write = build(_SCHEMA)
    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
    write('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd1'))
    write('add', ('...', 'user', 'bob', 'editor', 'doc', 'd2'))
    return session, widx, proc, write


# ---------------------------------------------------------------------------
# Seeded corruption per invariant class
# ---------------------------------------------------------------------------

def test_i4_leaf_predicate_outside_namespace():
    session, widx, proc, write = _populated()
    # forge a node with a leaf-style predicate no schema declares
    widx.idx.node('shadow.7', 'doc', 'd1', create_if_missing=True)
    session.flush()
    with pytest.raises(InvariantViolation, match='I4'):
        check_invariants(session, 'test', widx.schema_info)
    session.rollback()
    session.close()


def test_i5_missing_derived_flag():
    session, widx, proc, write = _populated()
    flagged = [e for e in session.exec(select(EdgeV4)).all() if e.derived]
    assert flagged, 'populated store must hold a derived edge (bob->d2.viewer)'
    flagged[0].derived = False
    session.add(flagged[0])
    session.flush()
    with pytest.raises(InvariantViolation, match='I5'):
        check_invariants(session, 'test', widx.schema_info)
    session.rollback()
    session.close()


def test_i5_flag_on_ordinary_edge():
    session, widx, proc, write = _populated()
    plain = [e for e in session.exec(select(EdgeV4)).all()
             if not e.derived and e.direct_edge_count > 0]
    plain[0].derived = True
    session.add(plain[0])
    session.flush()
    with pytest.raises(InvariantViolation, match='I5'):
        check_invariants(session, 'test', widx.schema_info)
    session.rollback()
    session.close()


def test_i6_stars_outside_declared_shapes():
    session, widx, proc, write = _populated()
    row = session.exec(select(ResidueV1)).first()
    row.stars = json.dumps([['martian', '...']])
    session.add(row)
    session.flush()
    with pytest.raises(InvariantViolation, match='I6'):
        check_invariants(session, 'test', widx.schema_info)
    session.rollback()
    session.close()


def test_i6_neg_overlaps_edge_holders():
    session, widx, proc, write = _populated()
    # bob holds a derived edge on d2; force him into d2's neg as well
    bob = widx.idx.node('...', 'user', 'bob', create_if_missing=False)
    d2 = widx.idx.node('viewer', 'doc', 'd2', create_if_missing=False)
    session.add(ResidueV1(store_id='test', object_node_id=d2.id, relation='viewer',
                          stars=json.dumps([['user', '...']]),
                          neg=json.dumps([bob.id]), version=1))
    session.flush()
    with pytest.raises(InvariantViolation, match='I6'):
        check_invariants(session, 'test', widx.schema_info)
    session.rollback()
    session.close()


def test_i6_empty_residue_row():
    session, widx, proc, write = _populated()
    d2 = widx.idx.node('viewer', 'doc', 'd2', create_if_missing=False)
    session.add(ResidueV1(store_id='test', object_node_id=d2.id, relation='viewer',
                          stars='[]', neg='[]', version=1))
    session.flush()
    with pytest.raises(InvariantViolation, match='I6'):
        check_invariants(session, 'test', widx.schema_info)
    session.rollback()
    session.close()


def test_i7_version_regression():
    session, widx, proc, write = _populated()
    row = session.exec(select(ResidueV1)).first()
    # an in-place regression to a version > 1 (version 1 is the lineage-restart
    # allowance -- see test_i7_reused_rowid_recreate_is_not_flagged)
    row.version = 3
    session.add(row)
    session.flush()
    versions = {(row.id, row.object_node_id): 5}
    with pytest.raises(InvariantViolation, match='I7'):
        check_invariants(session, 'test', widx.schema_info, residue_versions=versions)
    session.rollback()
    session.close()


def test_i7_reused_rowid_recreate_is_not_flagged():
    """SQLite may hand a same-transaction recreate the just-deleted max rowid: the
    new row legitimately carries version=1 against a higher remembered lineage.
    That must NOT trip I7 (it would be a false-positive commit abort, not a masked
    regression)."""
    session, widx, proc, write = _populated()
    row = session.exec(select(ResidueV1)).first()
    row.version = 1                                 # a recreate always starts at 1
    session.add(row)
    session.flush()
    versions = {(row.id, row.object_node_id): 7}    # stale lineage from a dead row
    check_invariants(session, 'test', widx.schema_info, residue_versions=versions)
    assert versions[(row.id, row.object_node_id)] == 1   # lineage restarted
    session.rollback()
    session.close()


def test_i7_recreated_row_restarts_lineage():
    """Delete-then-recreate is legitimate (empty rows are deleted): a fresh row id
    restarts at version 1 without tripping I7."""
    session, widx, proc, write = _populated()
    row = session.exec(select(ResidueV1)).first()
    versions = {(row.id + 999, row.object_node_id): 7}   # a long-gone row's lineage
    check_invariants(session, 'test', widx.schema_info, residue_versions=versions)
    assert (row.id + 999, row.object_node_id) not in versions   # pruned
    assert versions[(row.id, row.object_node_id)] == row.version
    session.close()


def test_i10_malformed_outbox_action():
    session, widx, proc, write = _populated()
    session.add(DeltaOutboxV1(store_id='test', subject_node_id=1, object_node_id=2,
                              action='EXPLODED', subject_type='user', subject_name='x',
                              subject_predicate='...', object_type='doc', object_name='y',
                              object_predicate='viewer'))
    session.flush()
    with pytest.raises(InvariantViolation, match='I10'):
        check_invariants(session, 'test', widx.schema_info)
    session.rollback()
    session.close()


# ---------------------------------------------------------------------------
# Backfill: bulk-loaded ≡ live-maintained; recovery path
# ---------------------------------------------------------------------------

_OPS = [
    ('...', 'user', '*', 'public', 'doc', 'd1'),
    ('...', 'user', 'alice', 'blocked', 'doc', 'd1'),
    ('...', 'user', 'bob', 'editor', 'doc', 'd1'),
    ('...', 'user', 'carol', 'editor', 'doc', 'd2'),
    ('...', 'user', '*', 'public', 'doc', 'd2'),
]


def _residue_state(session, widx):
    out = {}
    for r in session.exec(select(ResidueV1)).all():
        node = widx._node_by_id(r.object_node_id)
        neg_names = frozenset(
            (n.predicate, n.type, n.name)
            for n in (widx._node_by_id(nid) for nid in json.loads(r.neg))
            if n is not None)
        out[(node.type, node.name, r.relation)] = (r.stars, neg_names)
    return out


def test_backfill_vs_live_equivalence(load_fga_schema):
    # live store: every op runs the cascade
    live_session, live_widx, live_proc, live_write = build(_SCHEMA)
    for raw in _OPS:
        live_write('add', raw)
    live_proc.audit_fixpoint()

    # bulk store: raw leaf writes only (no cascade), then one backfill
    rs = parse_openfga_schema(_SCHEMA, enable_boolean=True)
    bulk_session, bulk_widx = make_wildcard_index(rs.schema_info, store_id='test')
    for raw in _OPS:
        sp = Ellipsis if raw[0] == '...' else raw[0]
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        for d in rs.apply(triple):
            bulk_widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                                d.subject.type, d.subject.name,
                                d.relation, d.object.type, d.object.name)
    bulk_proc = DeltaProcessor(bulk_widx, rs.compiled)
    bulk_proc.backfill()
    bulk_session.commit()
    bulk_proc.audit_fixpoint()

    # identical logical state: row multisets (ids ignored) + residues by name
    assert snapshot_rows(live_session, 'test') == snapshot_rows(bulk_session, 'test')
    assert _residue_state(live_session, live_widx) == _residue_state(bulk_session, bulk_widx)

    # and identical reads
    for q in [('...', 'user', 'ghost', 'viewer', 'doc', 'd1'),
              ('...', 'user', 'alice', 'viewer', 'doc', 'd1'),
              ('...', 'user', 'bob', 'viewer', 'doc', 'd1'),
              ('...', 'user', '*', 'viewer', 'doc', 'd2')]:
        assert live_widx.check(*q) == bulk_widx.check(*q), q

    live_session.close()
    bulk_session.close()


def test_backfill_recovers_corrupted_residue():
    """I9 finds the inconsistency; backfill() repairs it (§5.5 recovery path)."""
    session, widx, proc, write = _populated()

    row = session.exec(select(ResidueV1)).first()
    good_stars = row.stars
    row.stars = '[]'
    row.neg = json.dumps([widx.idx.node('...', 'user', 'alice', create_if_missing=False).id])
    session.add(row)
    session.flush()

    with pytest.raises(InvariantViolation, match='I9'):
        proc.audit_fixpoint()

    proc.backfill()
    session.commit()
    proc.audit_fixpoint()                                  # clean again
    fixed = session.exec(select(ResidueV1)).first()
    assert fixed.stars == good_stars
    assert widx.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1') is True
    assert widx.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is False
    session.close()
