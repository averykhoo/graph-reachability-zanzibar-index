"""
S1 (connected-store spec §2.1/§2.2/§5-S1): schemas live in the DB, write-once, and
stores are self-describing -- both backends open from (session, store_id) alone and
compile identically to explicit construction. Explicit schemas must MATCH a
persisted one (loud SchemaMismatch, never silent divergence).
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from connectedstore import (SchemaMismatch, SchemaV4, ensure_schema, load_schema,
                            open_graph_index, open_set_engine, save_schema)
from zanzibar_utils_v1 import parse_openfga_schema

_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define public: [user:*]
    define blocked: [user]
    define viewer: public but not blocked
'''

_OTHER = '''
type user
type doc
  relations
    define viewer: [user]
'''

_WC = frozenset({('doc', 'viewer')})


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_save_load_round_trip(session):
    # (group, member) and not e.g. (doc, blocked): blocked feeds the boolean
    # viewer's subtract leaf, and wildcard-object state cannot feed a derived
    # relation (decision-15 family) -- save_schema compiles first, so that shape
    # is now rejected before landing.
    save_schema(session, 's1', _SCHEMA, frozenset({('group', 'member')}))
    session.commit()
    text, shapes = load_schema(session, 's1')
    assert text == _SCHEMA
    assert shapes == frozenset({('group', 'member')})


def test_schema_is_write_once(session):
    save_schema(session, 's1', _SCHEMA)
    session.commit()
    with pytest.raises(ValueError, match='static'):
        save_schema(session, 's1', _OTHER)
    # even re-saving the identical text is a second write: use ensure_schema for that
    with pytest.raises(ValueError, match='static'):
        save_schema(session, 's1', _SCHEMA)


def test_invalid_schema_rejected_before_landing(session):
    with pytest.raises(ValueError):
        save_schema(session, 's1', 'type doc\n  relations\n    define a.b: [user]\n')
    assert session.get(SchemaV4, 's1') is None


def test_load_missing_schema_raises(session):
    with pytest.raises(KeyError, match='no persisted schema'):
        load_schema(session, 'ghost-store')


def test_ensure_schema_idempotent_and_mismatch(session):
    ensure_schema(session, 's1', _SCHEMA)
    session.commit()
    ensure_schema(session, 's1', _SCHEMA)          # idempotent: same text, no error
    with pytest.raises(SchemaMismatch):
        ensure_schema(session, 's1', _OTHER)       # different text
    with pytest.raises(SchemaMismatch):
        ensure_schema(session, 's1', _SCHEMA, frozenset({('doc', 'blocked')}))  # different shapes


def test_open_set_engine_self_describing(session):
    save_schema(session, 's1', _SCHEMA)
    session.commit()
    se = open_set_engine(session, 's1')
    explicit = parse_openfga_schema(_SCHEMA)
    assert se.schema_info.subject_wildcard_shapes == explicit.schema_info.subject_wildcard_shapes
    # behaves like a normal engine
    se.add_tuple('...', 'user', '*', 'public', 'doc', 'd1')
    se.add_tuple('...', 'user', 'alice', 'blocked', 'doc', 'd1')
    session.commit()
    assert se.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1') is True
    assert se.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is False


def test_open_graph_index_self_describing(session):
    save_schema(session, 's1', _SCHEMA)
    session.commit()
    widx, ruleset = open_graph_index(session, 's1')

    explicit = parse_openfga_schema(_SCHEMA)
    assert ruleset.rules_and_filters == explicit.rules_and_filters
    assert ruleset.schema_info == explicit.schema_info
    assert ruleset.compiled.tainted == explicit.compiled.tainted
    assert widx.schema_info is ruleset.schema_info

    # the store row was created; the index is usable
    from index_v4.processor import DeltaProcessor
    from index_v4.outbox import outbox_watermark
    from zanzibar_utils_v1 import Entity, RelationalTriple
    proc = DeltaProcessor(widx, ruleset.compiled)
    wm = outbox_watermark(session, 's1')
    triple = RelationalTriple(Entity('user', '*'), 'public', Entity('doc', 'd1'), Ellipsis)
    for d in ruleset.apply(triple):
        widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                       d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
    proc.run_cascade(wm)
    session.commit()
    assert widx.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1') is True


def test_object_wildcard_shapes_flow_through(session):
    save_schema(session, 's2', _OTHER, _WC)
    session.commit()
    widx, ruleset = open_graph_index(session, 's2')
    assert ruleset.schema_info.object_wildcard_shapes == _WC
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', '*')   # declared shape: accepted
    session.commit()
    assert widx.check('...', 'user', 'alice', 'viewer', 'doc', 'anydoc') is True
