"""
Named wildcard tests (spec §8.2), v4 backend only.

P3 covers the write path: bridge lifecycle, cycle rejection, GC parity, validation,
and the structural invariant checker after every op. P4 adds the read-path tests.
"""

import pytest
from sqlmodel import select

from index_v4 import NodeV4, EdgeV4
from zanzibar_utils_v1 import (
    Entity, RelationalTriple, parse_openfga_schema,
)
from tests.wildcard_helpers import make_wildcard_index, assert_wildcard_invariants, snapshot


def _ingest(widx, ruleset, triple):
    for d in ruleset.apply(triple):
        sp = '...' if d.subject_predicate is Ellipsis else d.subject_predicate
        widx.add_tuple(sp, d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)


def _remove_ingested(widx, ruleset, triple):
    for d in ruleset.apply(triple):
        sp = '...' if d.subject_predicate is Ellipsis else d.subject_predicate
        widx.remove_tuple(sp, d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

GROUP_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member]
type document
  relations
    define viewer: [user, user:*, group#member, group:*#member]
'''
GROUP_OBJ_WC = frozenset()   # no object wildcards here


CYCLE_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member, group:*#member]
'''


def _info(schema, object_wildcard_shapes=frozenset()):
    return parse_openfga_schema(schema, object_wildcard_shapes=object_wildcard_shapes).schema_info


def _direct_edges(widx):
    session, store_id = widx.idx.session, widx.idx.store_id
    return [e for e in session.exec(select(EdgeV4).where(EdgeV4.store_id == store_id)).all()
            if e.direct_edge_count > 0]


def _nodes(widx):
    session, store_id = widx.idx.session, widx.idx.store_id
    return list(session.exec(select(NodeV4).where(NodeV4.store_id == store_id)).all())


# ---------------------------------------------------------------------------
# Validation / reserved names (§3.5)
# ---------------------------------------------------------------------------

def test_undeclared_wildcard_rejected():
    session, widx = make_wildcard_index(_info(GROUP_SCHEMA))
    # (user, viewer) is not an object-wildcard shape -> object '*' rejected
    with pytest.raises(ValueError):
        widx.add_tuple('...', 'user', 'alice', 'viewer', 'document', '*')
    # bare (document,'...') is not a subject-wildcard shape -> subject '*' rejected
    with pytest.raises(ValueError):
        widx.add_tuple('...', 'document', '*', 'viewer', 'document', 'd')
    session.close()


def test_declared_wildcard_accepted():
    # subject wildcard [user:*] and object wildcard (document, viewer) both accepted.
    info = _info(GROUP_SCHEMA, object_wildcard_shapes={('document', 'viewer')})
    session, widx = make_wildcard_index(info)
    widx.add_tuple('...', 'user', '*', 'viewer', 'document', 'd')       # subject wildcard
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'document', '*')   # object wildcard
    session.commit()
    assert_wildcard_invariants(widx)
    session.close()


def test_reserved_star_name_rejected():
    # A concrete entity literally named '*' is rejected at the façade AND at node().
    session, widx = make_wildcard_index(_info(GROUP_SCHEMA))
    # façade: (user,'...') subject '*' IS declared, but object side here uses a concrete
    # relation; try a reserved '*' where no wildcard shape covers it -> ValueError.
    with pytest.raises(ValueError):
        widx.add_tuple('...', 'group', '*', 'member', 'group', 'g')   # (group,'...') not declared
    # core node(): name='*' without a wildcard variant is rejected outright.
    with pytest.raises(ValueError):
        widx.idx.node('...', 'user', '*', create_if_missing=True)
    session.close()


def test_wildcard_column_domain_rejected():
    # node() whitelists the wildcard column: only '', 'any', 'all' are allowed, so a
    # bogus value cannot slip past the name/wildcard biconditional (#4 hardening).
    session, widx = make_wildcard_index(_info(GROUP_SCHEMA))
    with pytest.raises(ValueError, match="wildcard must be"):
        widx.idx.node('...', 'user', '*', create_if_missing=True, wildcard='garbage')
    session.close()


# ---------------------------------------------------------------------------
# Cycle rejection (§3.5.4)
# ---------------------------------------------------------------------------

def test_wildcard_cycle_rejected():
    session, widx = make_wildcard_index(_info(CYCLE_SCHEMA))
    # group:*#member member group:g -> grant w_any(group,member)->g#member while the
    # bridge g#member->w_any(group,member) exists: a genuine cycle.
    with pytest.raises(ValueError, match="(?i)cycle|wildcard"):
        widx.add_tuple('member', 'group', '*', 'member', 'group', 'g')

    # Caller rolls back; store must be left clean (no orphan bridge).
    session.rollback()
    assert _direct_edges(widx) == []
    assert _nodes(widx) == []
    session.close()


def test_bridge_rollback_leaves_no_orphan():
    # Force a failure AFTER bridge creation and verify rollback removes the bridge too
    # (bridge insertion and grant must share the transaction, §6).
    session, widx = make_wildcard_index(_info(CYCLE_SCHEMA))
    with pytest.raises(ValueError):
        widx.add_tuple('member', 'group', '*', 'member', 'group', 'g')
    # Before rollback the bridge exists in the pending transaction...
    session.rollback()
    # ...and after rollback nothing persists.
    assert _nodes(widx) == []
    assert _direct_edges(widx) == []
    session.close()


# ---------------------------------------------------------------------------
# Bridge GC parity (§7.3 / §8.2)
# ---------------------------------------------------------------------------

def test_bridge_gc_restores_clean_state():
    info = _info(GROUP_SCHEMA)

    # Store A: scripted add/remove sequence ending at logical state Z.
    sess_a, a = make_wildcard_index(info, store_id='A')
    a.add_tuple('...', 'user', 'alice', 'member', 'group', 'g1')
    a.add_tuple('...', 'user', 'bob', 'member', 'group', 'g1')
    a.add_tuple('member', 'group', 'g1', 'viewer', 'document', 'doc1')
    a.remove_tuple('...', 'user', 'bob', 'member', 'group', 'g1')     # bob leaves
    sess_a.commit()
    assert_wildcard_invariants(a)

    # Store B: add state Z directly.
    sess_b, b = make_wildcard_index(info, store_id='B')
    b.add_tuple('...', 'user', 'alice', 'member', 'group', 'g1')
    b.add_tuple('member', 'group', 'g1', 'viewer', 'document', 'doc1')
    sess_b.commit()
    assert_wildcard_invariants(b)

    assert snapshot(a) == snapshot(b)
    sess_a.close(); sess_b.close()


def test_bridge_gc_full_teardown():
    # Removing every tuple must leave zero nodes and zero edges (no leaked bridges).
    info = _info(GROUP_SCHEMA)
    session, widx = make_wildcard_index(info)
    widx.add_tuple('...', 'user', 'alice', 'member', 'group', 'g1')
    widx.add_tuple('member', 'group', 'g1', 'viewer', 'document', 'doc1')
    session.flush()
    assert_wildcard_invariants(widx)

    widx.remove_tuple('member', 'group', 'g1', 'viewer', 'document', 'doc1')
    widx.remove_tuple('...', 'user', 'alice', 'member', 'group', 'g1')
    session.flush()
    assert _nodes(widx) == []
    assert _direct_edges(widx) == []
    session.close()


# ---------------------------------------------------------------------------
# No bridges for bare shapes (§8.2 test_user_created_after_grant, write side)
# ---------------------------------------------------------------------------

def test_no_bridge_edges_for_bare_shapes():
    # Plain [user:*] costs zero bridges: nothing points into w_any(user,'...').
    info = _info(GROUP_SCHEMA)
    session, widx = make_wildcard_index(info)
    widx.add_tuple('...', 'user', '*', 'viewer', 'document', 'doc1')   # public doc grant
    widx.add_tuple('...', 'user', 'alice', 'member', 'group', 'g1')    # unrelated new user
    session.flush()
    assert_wildcard_invariants(widx)

    # No concrete->w_any(user,'...') bridge rows exist.
    w_any_user = session.exec(
        select(NodeV4).where(NodeV4.type == 'user').where(NodeV4.predicate == '...')
        .where(NodeV4.wildcard == 'any')
    ).first()
    assert w_any_user is not None                       # created as the grant's source
    incoming = [e for e in _direct_edges(widx) if e.object_id == w_any_user.id]
    assert incoming == [], 'a bare-shape w_any must have no incoming bridge edges'
    session.close()


# ---------------------------------------------------------------------------
# Scripted invariant fuzz-lite: invariants hold after every op
# ---------------------------------------------------------------------------

def test_scripted_ops_preserve_invariants():
    info = _info(GROUP_SCHEMA, object_wildcard_shapes={('document', 'viewer')})
    session, widx = make_wildcard_index(info)

    ops = [
        ('add', ('...', 'user', 'alice', 'member', 'group', 'g1')),
        ('add', ('...', 'user', 'bob', 'member', 'group', 'g1')),
        ('add', ('member', 'group', '*', 'viewer', 'document', 'd1')),   # any-group members view d1
        ('add', ('...', 'user', 'carol', 'viewer', 'document', '*')),    # carol views all docs
        ('add', ('member', 'group', 'g1', 'viewer', 'document', 'd2')),
        ('remove', ('...', 'user', 'bob', 'member', 'group', 'g1')),
        ('remove', ('member', 'group', '*', 'viewer', 'document', 'd1')),
        ('remove', ('...', 'user', 'carol', 'viewer', 'document', '*')),
        ('remove', ('member', 'group', 'g1', 'viewer', 'document', 'd2')),
        ('remove', ('...', 'user', 'alice', 'member', 'group', 'g1')),
    ]
    for kind, args in ops:
        if kind == 'add':
            widx.add_tuple(*args)
        else:
            widx.remove_tuple(*args)
        session.flush()
        assert_wildcard_invariants(widx)

    # everything removed -> clean store
    assert _nodes(widx) == []
    assert _direct_edges(widx) == []
    session.close()


# ===========================================================================
# P4 read-path tests (§8.2)
# ===========================================================================

PUBLIC_SCHEMA = '''
type user
type document
  relations
    define owner: [user]
    define writer: [user, user:*] or owner
    define viewer: [user, user:*] or writer
'''

CANON_SCHEMA = '''
type user
type folder
  relations
    define parent_folder: [folder, folder:*]
    define viewer: [user:*, user, folder:*#viewer] or viewer from parent_folder
type document
  relations
    define parent_folder: [folder, folder:*]
    define viewer: [user:*, user, folder:*#viewer] or viewer from parent_folder
'''

GROUP_ANY_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member]
type document
  relations
    define viewer: [group#member, group:*#member]
'''

OBJ_HIER_SCHEMA = '''
type user
type folder
  relations
    define parent: [folder]
    define viewer: [user] or viewer from parent
type document
  relations
    define parent: [folder]
    define viewer: [user] or viewer from parent
'''


def test_public_doc_ghost_user():
    rs = parse_openfga_schema(PUBLIC_SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info)
    _ingest(widx, rs, RelationalTriple(Entity('user', '*'), 'viewer', Entity('document', 'd'), Ellipsis))
    session.flush()
    assert widx.check('...', 'user', 'nobody_ever_seen', 'viewer', 'document', 'd') is True
    assert widx.check('...', 'user', 'nobody_ever_seen', 'viewer', 'document', 'other') is False
    assert_wildcard_invariants(widx)
    session.close()


def test_user_created_after_grant():
    rs = parse_openfga_schema(PUBLIC_SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info)
    _ingest(widx, rs, RelationalTriple(Entity('user', '*'), 'viewer', Entity('document', 'd'), Ellipsis))
    # A brand-new user appears in an unrelated tuple after the grant.
    _ingest(widx, rs, RelationalTriple(Entity('user', 'late'), 'owner', Entity('document', 'other'), Ellipsis))
    session.flush()
    assert widx.check('...', 'user', 'late', 'viewer', 'document', 'd') is True
    session.close()


def test_wildcard_through_computed_userset():
    # define viewer: ... or writer, with writer: [user:*] -> user:* writer implies viewer.
    rs = parse_openfga_schema(PUBLIC_SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info)
    _ingest(widx, rs, RelationalTriple(Entity('user', '*'), 'writer', Entity('document', 'd'), Ellipsis))
    session.flush()
    assert widx.check('...', 'user', 'ghost', 'writer', 'document', 'd') is True
    assert widx.check('...', 'user', 'ghost', 'viewer', 'document', 'd') is True    # computed
    session.close()


def test_wildcard_through_from_chain():
    # No object-wildcard on viewer: this test exercises only user:* (subject wildcard)
    # + from-chain propagation, never a folder:* OBJECT on viewer. Declaring
    # {('folder','viewer')} here would make CANON_SCHEMA doubly-bridged (folder:*#viewer
    # userset + object-wildcard on the same shape) -- now compile-rejected as F1/F2
    # (docs/spec-deviations.md 2026-07-17). The OWC was superfluous; dropping it keeps
    # the feature under test intact.
    rs = parse_openfga_schema(CANON_SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info)
    _ingest(widx, rs, RelationalTriple(Entity('user', '*'), 'viewer', Entity('folder', 'root'), Ellipsis))
    _ingest(widx, rs, RelationalTriple(Entity('folder', 'root'), 'parent_folder', Entity('document', 'child'), Ellipsis))
    session.flush()
    # user:* views root; root is parent of child -> everyone views child via from-chain.
    assert widx.check('...', 'user', 'ghost', 'viewer', 'document', 'child') is True
    assert_wildcard_invariants(widx)
    session.close()


def test_group_any_member_grant():
    rs = parse_openfga_schema(GROUP_ANY_SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info)
    # any group's members can view d
    _ingest(widx, rs, RelationalTriple(Entity('group', '*'), 'viewer', Entity('document', 'd'), 'member'))
    # nested membership: alice in g_inner, g_inner in g_outer
    _ingest(widx, rs, RelationalTriple(Entity('user', 'alice'), 'member', Entity('group', 'g_inner'), Ellipsis))
    _ingest(widx, rs, RelationalTriple(Entity('group', 'g_inner'), 'member', Entity('group', 'g_outer'), 'member'))
    session.flush()

    assert widx.check('...', 'user', 'alice', 'viewer', 'document', 'd') is True     # member of a group
    # ghost group's #member userset matches the marker by shape (probe parity)
    assert widx.check('member', 'group', 'ghost_group', 'viewer', 'document', 'd') is True
    assert_wildcard_invariants(widx)
    session.close()


def test_all_folders_grant_reaches_child_docs():
    rs = parse_openfga_schema(OBJ_HIER_SCHEMA,
                              object_wildcard_shapes={('folder', 'viewer'), ('document', 'viewer')})
    session, widx = make_wildcard_index(rs.schema_info)
    _ingest(widx, rs, RelationalTriple(Entity('user', 'alice'), 'viewer', Entity('folder', '*'), Ellipsis))
    _ingest(widx, rs, RelationalTriple(Entity('folder', 'f1'), 'parent', Entity('document', 'd'), Ellipsis))
    session.flush()

    assert widx.check('...', 'user', 'alice', 'viewer', 'document', 'd') is True     # via all-folders
    # ghost folder direct check (probe 3)
    assert widx.check('...', 'user', 'alice', 'viewer', 'folder', 'never_made') is True
    assert widx.check('...', 'user', 'bob', 'viewer', 'document', 'd') is False
    assert_wildcard_invariants(widx)
    session.close()


def test_two_hop_user_star_folder_star():
    # The canonical §3.2 regression, end-to-end. Uses only SUBJECT wildcards
    # (user:* viewer, folder:* parent_folder) -- no folder:* OBJECT on viewer -- so the
    # object-wildcard on viewer is unneeded. Declaring it would make CANON_SCHEMA
    # doubly-bridged (now compile-rejected as F1/F2; docs/spec-deviations.md 2026-07-17).
    rs = parse_openfga_schema(CANON_SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info)
    _ingest(widx, rs, RelationalTriple(Entity('user', '*'), 'viewer', Entity('folder', 'xyz'), Ellipsis))
    _ingest(widx, rs, RelationalTriple(Entity('folder', '*'), 'parent_folder', Entity('document', '1'), Ellipsis))
    session.flush()
    assert widx.check('...', 'user', 'alice', 'viewer', 'document', '1') is True
    assert widx.check('...', 'user', 'ghost', 'viewer', 'document', '1') is True
    assert_wildcard_invariants(widx)
    session.close()


def test_forall_implies_exists_strict():
    # group:*#member viewer d; strict forall=>exists: 0 groups => False, 1 => True, remove => False.
    rs = parse_openfga_schema(GROUP_ANY_SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info)
    _ingest(widx, rs, RelationalTriple(Entity('group', '*'), 'viewer', Entity('document', 'd'), 'member'))
    session.flush()
    assert widx.check('...', 'user', 'alice', 'viewer', 'document', 'd') is False     # no groups exist

    membership = RelationalTriple(Entity('user', 'alice'), 'member', Entity('group', 'g1'), Ellipsis)
    _ingest(widx, rs, membership)
    session.flush()
    assert widx.check('...', 'user', 'alice', 'viewer', 'document', 'd') is True       # a group now exists

    _remove_ingested(widx, rs, membership)
    session.flush()
    assert widx.check('...', 'user', 'alice', 'viewer', 'document', 'd') is False       # back to none
    assert_wildcard_invariants(widx)
    session.close()


def test_no_instance_leak():
    rs = parse_openfga_schema(PUBLIC_SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info)
    # bob granted directly (no wildcard); alice must NOT acquire it.
    _ingest(widx, rs, RelationalTriple(Entity('user', 'bob'), 'viewer', Entity('document', 'd'), Ellipsis))
    session.flush()
    assert widx.check('...', 'user', 'bob', 'viewer', 'document', 'd') is True
    assert widx.check('...', 'user', 'alice', 'viewer', 'document', 'd') is False
    session.close()


def test_revoke_wildcard_grant_revokes_all():
    rs = parse_openfga_schema(PUBLIC_SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info)
    grant = RelationalTriple(Entity('user', '*'), 'viewer', Entity('document', 'd'), Ellipsis)
    _ingest(widx, rs, grant)
    session.flush()
    assert widx.check('...', 'user', 'alice', 'viewer', 'document', 'd') is True
    assert widx.check('...', 'user', 'bob', 'viewer', 'document', 'd') is True

    _remove_ingested(widx, rs, grant)
    session.flush()
    assert widx.check('...', 'user', 'alice', 'viewer', 'document', 'd') is False
    assert widx.check('...', 'user', 'bob', 'viewer', 'document', 'd') is False
    assert _nodes(widx) == []       # nothing left
    session.close()
