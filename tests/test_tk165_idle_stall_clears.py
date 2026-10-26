"""TK165: a stall recorded at lag 0 is cleared by the next successful catch_up(), even
one that applies nothing.

Before the fix (first-hand, ``docs/tk151-repros-2026-10-20/B3.py``, re-run 2026-10-26e):
a transient failure on an IDLE poll (the store lock is taken before the log is read)
recorded ``stalled_after == applied_log_id``; every later ``catch_up()`` returned 0 and
rolled back, so the stall never ended and untokened lookups raised ``IndexStalled``
until some unrelated write was applied::

    [after 3 successful zero-row catch_ups] lag=0 applied=1 stalled_after=1 index_stalled=True
    lookup -> IndexStalled: lookup() cannot be served: the index for store 'my-app' is
              STALLED at log id 1 (lag 0) ...

The fix lives in ``src/zanzibar/store/_store.py::Store._catch_up`` (zero-row branch).
A poison-row stall is NOT cleared by it: the failing row is still past the cursor, so
the batch is never zero-row (pinned below).

Sabotage (2026-10-26e, literal output in ``docs/tk165-idle-stall-clear-2026-10-26.md``):
  S1 delete the TK165 ``elif`` branch      -> both idle-stall tests FAIL
  S2 keep the branch, ``rollback()`` instead of ``commit()`` -> both idle-stall tests FAIL
  S3 (instrument control) ``_record_stall`` records nothing -> all 3 FAIL (poison test
     at its first ``index_stalled`` assert, so it does see a missing stall)
"""
import pytest
from sqlmodel import Session, SQLModel, create_engine

import zanzibar.store._store as store_mod
from zanzibar.store import IndexStalled, Store
from zanzibar.schema import PathCountExceeded
from tests.test_tk111_stall_aware_freshness import DIAMOND, MALLORY, _diamond_writes, _write_all


def _fail_once(monkeypatch):
    real = store_mod.advance_index
    calls = {'n': 0}

    def flaky(*a, **kw):
        calls['n'] += 1
        if calls['n'] == 1:
            raise ConnectionError('simulated lost connection on an idle poll')
        return real(*a, **kw)

    monkeypatch.setattr(store_mod, 'advance_index', flaky)


def _stall_idle_store(cs, monkeypatch):
    cs.add_tuple(*MALLORY)
    assert cs.catch_up() == 1
    assert cs.lag() == 0 and not cs.index_stalled
    _fail_once(monkeypatch)
    with pytest.raises(ConnectionError):
        cs.catch_up()
    assert cs.lag() == 0
    assert cs.index_stalled                       # the lag-0 stall the bug left behind
    assert cs.cursor.stalled_after == cs.cursor.applied_log_id
    with pytest.raises(IndexStalled):
        cs.lookup_reverse('viewer', 'doc', 'secret')


def test_zero_row_catch_up_clears_a_lag0_stall(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "st.db"}')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        cs = Store(s, 'st', schema=DIAMOND, sync=False)
        _stall_idle_store(cs, monkeypatch)

        assert cs.catch_up() == 0                 # healthy, nothing pending
        assert not cs.index_stalled
        assert cs.stall_error is None
        assert cs.cursor.stalled_after is None
        cs.lookup_reverse('viewer', 'doc', 'secret')   # served again, no IndexStalled
        assert cs.check(*MALLORY) is True
        s.rollback()
    engine.dispose()


def test_the_cleared_stall_is_committed_for_other_instances(tmp_path, monkeypatch):
    """The clear must be COMMITTED on the cursor row, not just set in this session:
    a replica reader that saw the stall stops seeing it after its next refresh()."""
    engine = create_engine(f'sqlite:///{tmp_path / "st.db"}')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as ws, Session(engine) as rs:
        worker = Store(ws, 'st', schema=DIAMOND, sync=False)
        _stall_idle_store(worker, monkeypatch)
        reader = Store(rs, 'st', schema=DIAMOND, sync=False)
        reader.refresh()
        assert reader.index_stalled
        rs.rollback()

        assert worker.catch_up() == 0
        reader.refresh()
        assert not reader.index_stalled
        assert reader.cursor.stalled_after is None
        reader.lookup_reverse('viewer', 'doc', 'secret')
        rs.rollback()
        ws.rollback()
    engine.dispose()


def test_a_poison_row_stall_is_not_cleared_by_later_catch_ups(tmp_path):
    """The negative pin: the zero-row clear must never end a stall whose failing row
    is still past the cursor (that would serve an unboundedly stale index)."""
    engine = create_engine(f'sqlite:///{tmp_path / "st.db"}')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        cs = Store(s, 'st', schema=DIAMOND, sync=False)
        _write_all(cs, _diamond_writes(31)[:2])
        cs.catch_up()
        _write_all(cs, _diamond_writes(31)[2:] + [('-', MALLORY)])
        with pytest.raises(PathCountExceeded):
            cs.catch_up()
        for _ in range(3):
            assert cs.index_stalled
            with pytest.raises(PathCountExceeded):
                cs.catch_up()
        assert cs.index_stalled and cs.lag() > 0
        with pytest.raises(IndexStalled):
            cs.lookup_reverse('viewer', 'doc', 'secret')
        assert cs.check(*MALLORY) is False        # set-engine fallback, not stale ALLOW
        s.rollback()
    engine.dispose()


def _poison_stall(cs):
    _write_all(cs, _diamond_writes(31)[:2])
    cs.catch_up()
    _write_all(cs, _diamond_writes(31)[2:] + [('-', MALLORY)])
    with pytest.raises(PathCountExceeded):
        cs.catch_up()
    assert cs.index_stalled and cs.lag() > 0
    return cs.cursor.applied_log_id, cs.cursor.stalled_after, cs.stall_error


def _assert_still_poison_stalled(cs, before):
    cs.refresh()
    assert (cs.cursor.applied_log_id, cs.cursor.stalled_after, cs.stall_error) == before
    assert cs.index_stalled and cs.lag() > 0
    with pytest.raises(IndexStalled):
        cs.lookup_reverse('viewer', 'doc', 'secret')
    assert cs.check(*MALLORY) is False        # set-engine fallback, not stale ALLOW


@pytest.mark.parametrize('bad, exc', [(0, ValueError), (-1, ValueError),
                                      (True, TypeError), (1.5, TypeError),
                                      ('1', TypeError)])
def test_catch_up_refuses_a_batch_below_one_and_the_poison_stall_survives(
        tmp_path, bad, exc):
    """TK165 repair round 1 (review blocking item). Before the repair, ``catch_up
    (batch=0)`` read ``log_rows(limit=0) == []`` with the poison row still pending,
    took the zero-row branch and CLEARED the stall (first-hand probe
    ``.scratch/wf-rel010/rev165/batch0.py``, 2026-10-26e)::

        before: stalled True lag 125
        catch_up(batch=0) -> 0
        after: stalled False lag 125 stall_error None
        lookup SERVED (stale)
        check MALLORY -> True (set engine truth: False)

    Now ``batch`` must be ``None`` or an ``int >= 1``, refused before the log is read.
    Sabotage S4 (2026-10-26e): make the ``batch < 1`` check in ``Store.catch_up`` a
    no-op -> 2 failed, 8 passed: ``[0-ValueError]`` with ``Failed: DID NOT RAISE
    ValueError`` (the head probe still keeps the stall, see the next test), and
    ``[-1-ValueError]`` with ``PathCountExceeded`` raised instead (SQLite reads
    ``LIMIT -1`` as no limit). The 3 TypeError params are guarded by the type check,
    not by S4. Literal output: ``docs/tk165-idle-stall-clear-2026-10-26.md``."""
    engine = create_engine(f'sqlite:///{tmp_path / "st.db"}')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        cs = Store(s, 'st', schema=DIAMOND, sync=False)
        before = _poison_stall(cs)
        with pytest.raises(exc, match='batch must be None or an int >= 1'):
            cs.catch_up(batch=bad)
        _assert_still_poison_stalled(cs, before)
        # batch=1 applies the good rows ahead of the failing one, then fails on it:
        # the cursor moves up to (not past) the poison row, and the stall stays.
        with pytest.raises(PathCountExceeded):
            cs.catch_up(batch=1)
        cs.refresh()
        assert cs.cursor.stalled_after == cs.cursor.applied_log_id > before[0]
        _assert_still_poison_stalled(cs, (cs.cursor.applied_log_id,
                                          cs.cursor.stalled_after, cs.stall_error))
        with pytest.raises(PathCountExceeded):      # at the failing row: still red
            cs.catch_up(batch=1)
        _assert_still_poison_stalled(cs, (cs.cursor.applied_log_id,
                                          cs.cursor.stalled_after, cs.stall_error))
        s.rollback()
    engine.dispose()


@pytest.mark.parametrize('how', ['inner_batch0', 'zero_rows_for_any_reason'])
def test_a_zero_row_batch_with_a_poison_row_pending_does_not_clear(
        tmp_path, monkeypatch, how):
    """The clear is guarded by a HEAD PROBE, not by "zero rows applied": drive the
    zero-row branch while the poison row is still past the cursor -- via the internal
    ``_catch_up(0)`` (bypassing the public validation), or by an ``advance_index`` that
    returns 0 for some other reason -- and the stall must survive.
    Sabotage S5 (2026-10-26e): drop the ``not log_rows(..., limit=1)`` probe from the
    ``elif`` -> 2 failed, 8 passed: both params of this test, nothing else
    (literal output in the TK165 doc)."""
    engine = create_engine(f'sqlite:///{tmp_path / "st.db"}')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        cs = Store(s, 'st', schema=DIAMOND, sync=False)
        before = _poison_stall(cs)
        if how == 'inner_batch0':
            with cs.widx.idx.fanout_cap_suspended():
                assert cs._catch_up(0) == 0
        else:
            monkeypatch.setattr(store_mod, 'advance_index', lambda *a, **kw: 0)
            assert cs.catch_up() == 0
            monkeypatch.undo()
        _assert_still_poison_stalled(cs, before)
        s.rollback()
    engine.dispose()
