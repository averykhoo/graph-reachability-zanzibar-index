"""
External-review finding #2: the wildcard spec (§remove_tuple) mandates a façade
``remove_node`` that strips materialized bridges BEFORE the core removal --
`WildcardIndex` never implemented it. (The reviewer's claimed symptom -- dangling
edge rows tripping the core post-condition -- was empirically refuted: the count
math retires bridge edges fine. The real value of the ordering is refcount hygiene:
the core's node-removal shortcut doesn't decrement neighbour refcounts, so stripping
bridges through remove_edge_by_id lets an orphaned w node be implicit-GC'd instead
of lingering with a stale count.)
"""

import pytest
from sqlmodel import select

from index_v4 import NodeV4
from index_v4.invariants import check_invariants
from zanzibar_utils_v1 import parse_openfga_schema
from tests.wildcard_helpers import make_wildcard_index

_SCHEMA = '''
type user
type group
  relations
    define member: [user]
type doc
  relations
    define viewer: [user, group#member, group:*#member]
'''


def _store():
    rs = parse_openfga_schema(_SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info)
    return session, widx


def _w_nodes(session):
    return [n for n in session.exec(select(NodeV4)).all() if n.wildcard != '']


def test_remove_node_strips_bridges_and_gcs_orphan_w_node():
    session, widx = _store()
    # g1#member gets bridged (bridged-in shape) by this write
    widx.add_tuple('member', 'group', 'g1', 'viewer', 'doc', 'd1')
    widx.add_tuple('...', 'user', 'alice', 'member', 'group', 'g1')
    session.commit()
    assert len(_w_nodes(session)) == 1                     # w_any(group, member)

    widx.remove_node('member', 'group', 'g1')
    session.commit()

    check_invariants(session, 'test', widx.schema_info)
    # the bridge went through remove_edge_by_id, so the orphaned w node's refcount
    # hit zero honestly and implicit GC collected it
    assert _w_nodes(session) == []
    assert widx.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is False
    session.close()


def test_remove_node_unbridged_and_missing():
    session, widx = _store()
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    session.commit()

    widx.remove_node('...', 'user', 'alice')
    session.commit()
    check_invariants(session, 'test', widx.schema_info)
    assert widx.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is False

    with pytest.raises(ValueError, match='Non-existent'):
        widx.remove_node('...', 'user', 'ghost')
    session.close()


def test_remove_node_respects_derived_exclusivity():
    schema = '''
        type user
        type doc
          relations
            define banned: [user]
            define viewer: [user] but not banned
    '''
    rs = parse_openfga_schema(schema)
    session, widx = make_wildcard_index(rs.schema_info)
    widx.processor_writes = True
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    widx.processor_writes = False
    session.commit()

    with pytest.raises(ValueError, match='processor'):
        widx.remove_node('viewer', 'doc', 'd1')            # derived-public node
    session.close()
