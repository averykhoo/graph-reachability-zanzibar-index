"""
S4 (connected-store spec §5-S4): build_index, the offline bootstrap builder.

A tuple store that lived index-less gets an index equal -- row multisets, residues,
reads -- to one that was live-maintained through the same history (removes
included). Separate-id indexes work; double-builds are refused; the built index
continues under the sync schedule seamlessly.
"""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from connectedstore import ConnectedStore, TupleSource, build_index, save_schema
from index_v4.invariants import snapshot_rows
from index_v4.models import ResidueV1

_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define parent: [doc]
    define public: [user:*]
    define blocked: [user]
    define editor: [user, group#member]
    define viewer: (public but not blocked) or editor
    define inherited: viewer from parent
'''

_OPS = [
    ('add', ('...', 'user', '*', 'public', 'doc', 'd1')),
    ('add', ('...', 'user', 'u1', 'blocked', 'doc', 'd1')),
    ('add', ('...', 'user', 'u2', 'editor', 'doc', 'd1')),
    ('add', ('...', 'user', 'u1', 'member', 'group', 'g1')),
    ('add', ('member', 'group', 'g1', 'editor', 'doc', 'd1')),
    ('add', ('...', 'doc', 'd1', 'parent', 'doc', 'd2')),
    ('remove', ('...', 'user', 'u2', 'editor', 'doc', 'd1')),
    ('add', ('...', 'user', 'u2', 'editor', 'doc', 'd2')),
]

_GRID = [('...', 'user', sn, rel, 'doc', on)
         for sn in ('u1', 'u2', 'ghost', '*')
         for rel in ('viewer', 'inherited', 'editor', 'public')
         for on in ('d1', 'd2')]


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _residues_by_name(session, widx, store_id):
    out = {}
    for r in session.exec(select(ResidueV1).where(ResidueV1.store_id == store_id)).all():
        node = widx._node_by_id(r.object_node_id)
        neg = frozenset((n.predicate, n.type, n.name)
                        for n in (widx._node_by_id(i) for i in json.loads(r.neg))
                        if n is not None)
        out[(node.type, node.name, r.relation)] = (r.stars, neg)
    return out


def test_built_index_equals_live_maintained(session, load_fga_schema):
    # live twin: every write maintains the index synchronously
    live = ConnectedStore(session, 'live', schema=_SCHEMA)
    # index-less twin: source-of-truth writes only
    save_schema(session, 'bulk', _SCHEMA)
    src = TupleSource(session, 'bulk')
    for op, raw in _OPS:
        (live.add_tuple if op == 'add' else live.remove_tuple)(*raw)
        (src.add if op == 'add' else src.remove)(*raw)
    session.commit()

    cursor, widx, ruleset = build_index(session, 'bulk')

    assert cursor.applied_log_id == src.watermark()          # cursor at the watermark
    assert snapshot_rows(session, 'live') == snapshot_rows(session, 'bulk')
    assert _residues_by_name(session, live.widx, 'live') == \
        _residues_by_name(session, widx, 'bulk')
    for q in _GRID:
        assert widx.check(*q) == live.check(*q), q


def test_built_index_continues_under_sync_schedule(session):
    save_schema(session, 's', _SCHEMA)
    src = TupleSource(session, 's')
    src.add('...', 'user', '*', 'public', 'doc', 'd1')
    session.commit()
    build_index(session, 's')

    # reopening as a ConnectedStore picks up the cursor and keeps maintaining
    cs = ConnectedStore(session, 's')
    assert cs.cursor.applied_log_id == cs.watermark()
    cs.add_tuple('...', 'user', 'u1', 'blocked', 'doc', 'd1')
    assert cs.check('...', 'user', 'u1', 'viewer', 'doc', 'd1') is False
    assert cs.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1') is True
    if cs.proc is not None:
        cs.proc.audit_fixpoint()


def test_separate_index_store(session):
    save_schema(session, 'src', _SCHEMA)
    src = TupleSource(session, 'src')
    src.add('...', 'user', '*', 'public', 'doc', 'd1')
    src.add('...', 'user', 'u1', 'blocked', 'doc', 'd1')
    session.commit()

    cursor, widx, ruleset = build_index(session, 'src', 'idx')
    assert cursor.source_store_id == 'src' and cursor.index_store_id == 'idx'
    assert widx.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1') is True
    assert widx.check('...', 'user', 'u1', 'viewer', 'doc', 'd1') is False
    # source store carries no graph rows of its own
    assert snapshot_rows(session, 'src')[1] == snapshot_rows(session, 'nonexistent')[1]


def test_double_build_refused(session):
    save_schema(session, 's', _SCHEMA)
    TupleSource(session, 's').add('...', 'user', 'u2', 'editor', 'doc', 'd1')
    session.commit()
    build_index(session, 's')
    with pytest.raises(ValueError, match='fresh builds'):
        build_index(session, 's')


def test_build_on_store_with_graph_state_refused(session):
    cs = ConnectedStore(session, 's', schema=_SCHEMA)
    cs.add_tuple('...', 'user', 'u2', 'editor', 'doc', 'd1')
    # simulate a state-but-no-cursor situation
    session.exec(select(type(cs.cursor))).first()
    session.delete(cs.cursor)
    session.commit()
    with pytest.raises(ValueError, match='graph state'):
        build_index(session, 's')
