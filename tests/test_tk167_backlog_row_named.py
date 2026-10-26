"""TK167: a sync write refused because of SOMEONE ELSE'S unappliable backlog row says so.

The sync apply step replays the whole pending backlog inside the caller's write
transaction, so one row a ``sync=False`` writer logged and the index cannot apply refuses
every ``sync=True`` write on that store id -- removals of the very tuple included. That
is correct (both backends stay equal: the write is rolled back everywhere); what was
wrong was the message. Before the fix (first-hand, ``docs/tk151-repros-2026-10-20/B6.py``,
re-run 2026-10-26e), every such write said only::

    sync add unrelated tuple: PathCountExceeded: path count bound exceeded: this edge
      would give closure row user:alice -> group:a32#member 2147483648 distinct ...
    sync remove of the poison tuple itself: PathCountExceeded: path count bound exceeded: ...

which names the backlog row's closure row, not the caller's tuple. After::

    sync add unrelated tuple: PathCountExceeded: this write (log row 255) was rolled back
      because the index backlog of store 'my-app' holds an earlier log row it cannot
      apply: row 254 (ADD group:b31#member member group:a32) ...

The fix: ``src/zanzibar/store/_store.py::_name_blocking_backlog_row``, called from the
``IndexResourceLimit`` arm of ``Store._write``. Same instance, same type, so an
``except PathCountExceeded`` keeps matching; ``failing_log_row`` is untouched.

Sabotage (2026-10-26e, literal output in ``docs/tk167-backlog-row-message-2026-10-26.md``):
  S1 ``_name_blocking_backlog_row`` returns at once -> 3 failed, 2 passed:
     FAILED test_unrelated_sync_add_names_the_backlog_row,
     test_sync_remove_of_the_poison_tuple_names_it_too, test_fanout_cap_type_is_covered_too
  S2 the guard inverted to ``row[0] != token``    -> 4 failed, 1 passed: the three above
     plus test_own_row_refusal_message_is_unchanged (the recovery test is the survivor;
     it pins behaviour, not the message)
  S3 (review) ``if isinstance(exc, ClosureFanoutExceeded):`` -> ``if False:`` -> 1 failed,
     4 passed: test_fanout_cap_type_is_covered_too
  Repair round 1 (2026-10-26e): the guard compared the failing row with the returned
  TOKEN, which on a duplicate add is the log head, i.e. the poison row itself. It now
  compares with the id of the row the call appended (``own_row_id``, None on a
  duplicate). S4 (the call passes ``token`` again) -> 2 failed, 5 passed:
     FAILED test_sync_duplicate_add_names_the_backlog_row[unrelated-duplicate] and
     [poison-duplicate]; restored by cp, cmp-identical, 7 passed.
"""
import pytest
from sqlmodel import Session, SQLModel, create_engine

import zanzibar.graphindex.core as core
from zanzibar import ClosureFanoutExceeded, PathCountExceeded, Store
from zanzibar.store import rebuild_index

SCHEMA = '''
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
'''
POISON = ('group:B1#member', 'member', 'group:L2')


def _diamond(st):
    """u in L0, two diamond layers: 4 paths u -> L2, refused under MAX_PATH_COUNT=3 on
    the LAST write (``POISON``)."""
    st.add_tuple('user:u', 'member', 'group:L0')
    for i in range(2):
        for mid in ('A', 'B'):
            st.add_tuple(f'group:L{i}#member', 'member', f'group:{mid}{i}')
            st.add_tuple(f'group:{mid}{i}#member', 'member', f'group:L{i + 1}')


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f'sqlite:///{tmp_path}/tk167.db')
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def poisoned(engine, monkeypatch):
    """A ``sync=False`` writer logs the poison row; a ``sync=True`` instance on the same
    store id is returned, with the poison row in its backlog."""
    monkeypatch.setattr(core, 'MAX_PATH_COUNT', 3)
    a = Store(Session(engine), 'my-app', schema=SCHEMA, sync=False)
    _diamond(a)
    with pytest.raises(PathCountExceeded) as ei:
        a.catch_up()
    assert a.index_stalled
    poison_id = ei.value.failing_log_row[0]
    assert 'ADD group:B1#member member group:L2' in ei.value.failing_log_row[1]
    s = Store(Session(engine), 'my-app')
    return a, s, poison_id


def _assert_names_backlog(exc, poison_id):
    msg = str(exc)
    assert exc.failing_log_row[0] == poison_id
    assert f'holds an earlier log row it cannot apply: row {poison_id} ' in msg, msg
    assert 'ADD group:B1#member member group:L2' in msg, msg
    assert 'sync=False' in msg and 'rebuild_index' in msg, msg
    assert 'removals included' in msg, msg
    assert 'path count bound exceeded' in msg, msg      # the original reason survives


def test_unrelated_sync_add_names_the_backlog_row(poisoned):
    _, s, poison_id = poisoned
    with pytest.raises(PathCountExceeded) as ei:
        s.add_tuple('user:bob', 'member', 'group:zz')
    _assert_names_backlog(ei.value, poison_id)
    assert f'this write (log row {poison_id + 1}) was rolled back' in str(ei.value)
    # equivalence: the refused write is absent from BOTH backends
    assert s.check('user:bob', 'member', 'group:zz') is False
    assert s.source.check('user:bob', 'member', 'group:zz') is False


def test_sync_remove_of_the_poison_tuple_names_it_too(poisoned):
    _, s, poison_id = poisoned
    with pytest.raises(PathCountExceeded) as ei:
        s.remove_tuple(*POISON)
    _assert_names_backlog(ei.value, poison_id)



@pytest.mark.parametrize('dup', [('user:u', 'member', 'group:L0'), POISON],
                         ids=['unrelated-duplicate', 'poison-duplicate'])
def test_sync_duplicate_add_names_the_backlog_row(poisoned, engine, dup):
    """Repair round 1: a duplicate add appends NO log row and returns the log head as its
    token. With the poison row at the head (as here, and in B6) that token equals the
    poison id, so an "own row == token" guard read the backlog row as the caller's own
    and the bare message came back. Before the fix (first-hand review, 2026-10-26e)::

        PathCountExceeded: path count bound exceeded: this edge would give closure row
          user:alice -> group:a32#member ...    (failing_log_row (254, ...), head = 254)
    """
    from zanzibar.store.source import log_watermark
    _, s, poison_id = poisoned
    with Session(engine) as probe:
        assert log_watermark(probe, 'my-app') == poison_id     # the poison row IS the head
    with pytest.raises(PathCountExceeded) as ei:
        s.add_tuple(*dup)
    _assert_names_backlog(ei.value, poison_id)
    assert 'this write (a duplicate add, which appends no log row)' in str(ei.value)

def test_documented_recovery_unblocks_sync_writes(poisoned, engine):
    a, s, _ = poisoned
    a.remove_tuple(*POISON)
    with Session(engine) as ops:
        rebuild_index(ops, 'my-app')
    s.refresh()
    s.add_tuple('user:bob', 'member', 'group:zz')
    assert s.check('user:bob', 'member', 'group:zz') is True
    assert s.source.check('user:bob', 'member', 'group:zz') is True


def test_own_row_refusal_message_is_unchanged(engine, monkeypatch):
    """Control: on a store with no backlog the failing row IS the caller's, and the
    message stays the bare limit message."""
    monkeypatch.setattr(core, 'MAX_PATH_COUNT', 3)
    s = Store(Session(engine), 'clean', schema=SCHEMA)
    with pytest.raises(PathCountExceeded) as ei:
        _diamond(s)
    assert str(ei.value).startswith('path count bound exceeded'), str(ei.value)
    assert 'backlog' not in str(ei.value)


def test_fanout_cap_type_is_covered_too():
    """The helper runs in the ``IndexResourceLimit`` arm, so ``ClosureFanoutExceeded``
    (an unapplied over-cap backlog row met by a sync writer) gets the same message."""
    from zanzibar.store._store import _name_blocking_backlog_row
    e = ClosureFanoutExceeded('closure fan-out cap exceeded')
    e.failing_log_row = (7, 'ADD group:g#member member group:h')
    _name_blocking_backlog_row(e, 9, 'x')
    assert isinstance(e, ClosureFanoutExceeded)
    assert 'row 7 (ADD group:g#member member group:h)' in str(e)
    assert str(e).endswith('closure fan-out cap exceeded')
    assert 'run Store.catch_up()' in str(e) and 'rebuild_index' not in str(e)
