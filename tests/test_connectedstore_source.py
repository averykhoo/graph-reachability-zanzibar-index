"""
S2 (connected-store spec §2.3-§2.6, §5-S2): the source-of-truth write path.

  * log ≡ applied writes (op + fields, cursor order), and replaying the log into a
    fresh engine reproduces the state;
  * rejected writes leave NO row anywhere (tuple, log) -- validity at admission;
  * duplicate adds are idempotent (set semantics): no log row, watermark token;
  * rollback discards tuple + log together (same transaction);
  * tokens are monotonic log ids.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from connectedstore import TupleSource, TupleLogV1, log_rows, log_watermark, save_schema
from setengine import SetEngine, TupleV1

_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define public: [user:*]
    define blocked: [user]
    define editor: [user, group#member]
    define viewer: (public but not blocked) or editor
'''


@pytest.fixture
def env():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        save_schema(session, 's', _SCHEMA)
        session.commit()
        yield session, TupleSource(session, 's')


def _tuples(session, store_id):
    rows = session.exec(select(TupleV1).where(TupleV1.store_id == store_id)).all()
    return {(r.subject_predicate, r.subject_type, r.subject_name,
             r.relation, r.object_type, r.object_name) for r in rows}


def test_log_matches_applied_writes(env):
    session, src = env
    t1 = src.add('...', 'user', '*', 'public', 'doc', 'd1')
    t2 = src.add('...', 'user', 'alice', 'blocked', 'doc', 'd1')
    t3 = src.remove('...', 'user', 'alice', 'blocked', 'doc', 'd1')
    session.commit()

    assert t1 < t2 < t3                                     # monotonic tokens
    rows = log_rows(session, 's')
    assert [(r.op, r.subject_name, r.relation) for r in rows] == [
        ('ADD', '*', 'public'), ('ADD', 'alice', 'blocked'), ('REMOVE', 'alice', 'blocked')]
    assert log_watermark(session, 's') == t3
    assert _tuples(session, 's') == {('...', 'user', '*', 'public', 'doc', 'd1')}


def test_replaying_log_reproduces_state(env):
    session, src = env
    ops = [
        ('add', ('...', 'user', '*', 'public', 'doc', 'd1')),
        ('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd1')),
        ('add', ('...', 'user', 'bob', 'editor', 'doc', 'd2')),
        ('remove', ('...', 'user', 'alice', 'blocked', 'doc', 'd1')),
        ('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd2')),
    ]
    for op, raw in ops:
        (src.add if op == 'add' else src.remove)(*raw)
    session.commit()

    # fresh store, replay the log verbatim
    save_schema(session, 'replay', _SCHEMA)
    replayed = SetEngine(session, 'replay', _SCHEMA)
    for r in log_rows(session, 's'):
        fn = replayed.add_tuple if r.op == 'ADD' else replayed.remove_tuple
        fn(r.subject_predicate, r.subject_type, r.subject_name,
           r.relation, r.object_type, r.object_name)
    session.commit()

    assert _tuples(session, 'replay') == _tuples(session, 's')
    for q in [('...', 'user', 'ghost', 'viewer', 'doc', 'd1'),
              ('...', 'user', 'alice', 'viewer', 'doc', 'd2'),
              ('...', 'user', 'bob', 'viewer', 'doc', 'd2')]:
        assert replayed.check(*q) == src.check(*q), q


def test_rejected_writes_leave_no_row(env):
    session, src = env

    with pytest.raises(ValueError):                     # no matching restriction
        src.add('...', 'martian', 'zork', 'viewer', 'doc', 'd1')
    with pytest.raises(ValueError):                     # invalid charset
        src.add('...', 'user', 'a b', 'blocked', 'doc', 'd1')
    with pytest.raises(ValueError):                     # remove of absent tuple
        src.remove('...', 'user', 'nobody', 'blocked', 'doc', 'd1')
    # userset cycle: g1 in g2, then g2 in g1 (cycle parity at admission, spec §2.4)
    src.add('member', 'group', 'g1', 'member', 'group', 'g2')
    with pytest.raises(ValueError):
        src.add('member', 'group', 'g2', 'member', 'group', 'g1')
    session.commit()

    assert [r.op for r in log_rows(session, 's')] == ['ADD']    # only the g1->g2 add
    assert _tuples(session, 's') == {('member', 'group', 'g1', 'member', 'group', 'g2')}


def test_duplicate_add_is_idempotent_no_log_row(env):
    session, src = env
    t1 = src.add('...', 'user', 'bob', 'editor', 'doc', 'd1')
    t2 = src.add('...', 'user', 'bob', 'editor', 'doc', 'd1')   # duplicate
    session.commit()

    assert t2 == t1                                     # watermark, not a new token
    assert len(log_rows(session, 's')) == 1
    # and remove-once fully retires it (set semantics end to end)
    src.remove('...', 'user', 'bob', 'editor', 'doc', 'd1')
    session.commit()
    assert _tuples(session, 's') == set()
    assert src.check('...', 'user', 'bob', 'viewer', 'doc', 'd1') is False


def test_rollback_discards_tuple_and_log_together(env):
    session, src = env
    src.add('...', 'user', 'bob', 'editor', 'doc', 'd1')
    session.rollback()

    assert log_rows(session, 's') == []
    assert _tuples(session, 's') == set()
    # in-memory engine state is rebuilt from ground truth on open
    fresh = TupleSource(session, 's')
    assert fresh.check('...', 'user', 'bob', 'viewer', 'doc', 'd1') is False


def test_log_is_append_only_audit(env):
    session, src = env
    src.add('...', 'user', 'bob', 'editor', 'doc', 'd1')
    src.remove('...', 'user', 'bob', 'editor', 'doc', 'd1')
    session.commit()
    # history survives even though the current-state table is empty
    assert _tuples(session, 's') == set()
    assert [r.op for r in log_rows(session, 's')] == ['ADD', 'REMOVE']
