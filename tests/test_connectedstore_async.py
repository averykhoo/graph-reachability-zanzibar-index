"""
S6 (connected-store spec §5-S6): the async schedule, end to end.

Same machinery as sync -- ``catch_up`` loops the identical ``advance_index`` apply
step the sync schedule inlines. Asserted here:

  * async-built state ≡ sync-built state after catch-up (rows, residues, reads);
  * freshness gating: while the index lags, un-tokened reads serve the (stale)
    index, token-carrying reads fall back to the always-fresh set engine; after
    catch-up both agree;
  * exactly-once batching: a mid-catch-up crash moves only committed batches;
    the retry completes without double-application;
  * invariants + I9 clean after catch-up.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from connectedstore import ConnectedStore
from index_v4.invariants import snapshot_rows
from tests.test_connectedstore_build import _SCHEMA, _OPS, _GRID, _residues_by_name
from tests.wildcard_helpers import assert_wildcard_invariants


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_async_equals_sync_after_catch_up(session):
    sync_store = ConnectedStore(session, 'sync', schema=_SCHEMA)
    async_store = ConnectedStore(session, 'async', schema=_SCHEMA, sync=False)

    for op, raw in _OPS:
        (sync_store.add_tuple if op == 'add' else sync_store.remove_tuple)(*raw)
        (async_store.add_tuple if op == 'add' else async_store.remove_tuple)(*raw)

    assert async_store.lag() == len(_OPS)
    applied = async_store.catch_up(batch=3)          # multiple batches
    assert applied == len(_OPS)
    assert async_store.lag() == 0

    assert snapshot_rows(session, 'sync') == snapshot_rows(session, 'async')
    assert _residues_by_name(session, sync_store.widx, 'sync') == \
        _residues_by_name(session, async_store.widx, 'async')
    for q in _GRID:
        assert async_store.check(*q) == sync_store.check(*q), q

    assert_wildcard_invariants(async_store.widx)
    if async_store.proc is not None:
        async_store.proc.audit_fixpoint()


def test_freshness_gating_while_lagging(session):
    cs = ConnectedStore(session, 's', schema=_SCHEMA, sync=False)
    token = cs.add_tuple('...', 'user', '*', 'public', 'doc', 'd1')
    assert cs.lag() > 0

    q = ('...', 'user', 'ghost', 'viewer', 'doc', 'd1')
    # un-tokened read: served by the (stale) index -- the write is not visible yet
    assert cs.check(*q) is False
    # token-carrying read: the index lags the token, so the set engine answers fresh
    assert cs.check(*q, at_least=token) is True

    cs.catch_up()
    assert cs.check(*q) is True                       # index caught up
    assert cs.check(*q, at_least=token) is True       # token now satisfied BY the index
    assert cs.cursor.applied_log_id >= token


def test_catch_up_is_exactly_once_across_crashes(session):
    cs = ConnectedStore(session, 's', schema=_SCHEMA, sync=False)
    for op, raw in _OPS:
        (cs.add_tuple if op == 'add' else cs.remove_tuple)(*raw)
    head = cs.watermark()

    # crash after the first committed batch: the second batch's cascade explodes
    calls = {'n': 0}
    original = cs.proc.run_cascade

    def flaky(wm):
        calls['n'] += 1
        if calls['n'] == 2:
            raise RuntimeError('injected worker crash')
        return original(wm)

    cs.proc.run_cascade = flaky
    with pytest.raises(RuntimeError, match='injected'):
        cs.catch_up(batch=3)
    cs.proc.run_cascade = original

    # only the committed batch moved the cursor
    assert 0 < cs.cursor.applied_log_id < head

    # the retry re-reads the failed batch and completes -- no double-application
    cs.catch_up(batch=3)
    assert cs.cursor.applied_log_id == head

    twin = ConnectedStore(session, 'twin', schema=_SCHEMA)
    for op, raw in _OPS:
        (twin.add_tuple if op == 'add' else twin.remove_tuple)(*raw)
    assert snapshot_rows(session, 's') == snapshot_rows(session, 'twin')
    if cs.proc is not None:
        cs.proc.audit_fixpoint()


def test_sync_store_is_the_inlined_special_case(session):
    """A sync store's catch_up is always a no-op: the inlined apply step already
    rode every write (same machinery, different schedule)."""
    cs = ConnectedStore(session, 's', schema=_SCHEMA)      # sync=True
    for op, raw in _OPS[:4]:
        (cs.add_tuple if op == 'add' else cs.remove_tuple)(*raw)
    assert cs.lag() == 0
    assert cs.catch_up() == 0
