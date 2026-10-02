"""TK111 / TK112: a STALLED async apply step must not keep serving untokened reads.

An untokened ``ConnectedStore`` read is documented as bounded-stale: the index trails
the log by whatever the async worker has not applied yet. A log row the index can NEVER
apply breaks the bound. Two such rows are admitted today: a path-count overflow
(``TK111``) and a fan-out-capped row (``TK112``). ``catch_up`` then retries the row
forever, every later row -- revocations included -- waits behind it, and before this fix
an untokened ``check`` kept answering ALLOW for a revoked grant without bound.

Observed BEFORE the fix (P10 verify probe, first-hand, 2026-09-27d; the witness is the
first test below, SQLite, K=63, batch=1):
    catch_up attempt 0/1/2: OverflowError: Python int too large to convert to SQLite
    INTEGER | lag=2
    check(mallory viewer doc:secret): ConnectedStore.check(untokened)=True
    set_engine=False oracle=False

The fix (``docs/tk111-stall-aware-freshness-2026-10-02.md`` sec 2, D1-D5):
``catch_up`` persists a stall marker on the cursor row, and while it is live the
untokened ``check`` is served by the set engine and an untokened lookup refuses with
``IndexStalled``. These tests pin the fail-open closed for both poison sources, the
cross-instance case, and the transient case (a stall clears on the next good batch).
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

import connectedstore.store as store_mod
from connectedstore import ConnectedStore, IndexStalled
from tests import oracle as O
from zanzibar_utils_v1 import PathCountExceeded

DIAMOND = '''
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define viewer: [user, group#member]
'''

MALLORY = ('...', 'user', 'mallory', 'viewer', 'doc', 'secret')


def _diamond_writes(k):
    """``u`` in L0, then K diamond layers L_i -> {A_i, B_i} -> L_{i+1}: the path count
    from ``u`` to ``L_k`` is 2**k. That overflowed a 64-bit counter at k=63 (the raw
    SQLite error), and since TK111 S5 (2026-10-03b) it is refused at k=31, the int4
    ceiling ``index_v4.core.MAX_PATH_COUNT``, on the LAST write of the chain."""
    w = [('+', MALLORY), ('+', ('...', 'user', 'u', 'member', 'group', 'L0'))]
    for i in range(k):
        for mid in ('A', 'B'):
            w.append(('+', ('member', 'group', f'L{i}', 'member', 'group', f'{mid}{i}')))
            w.append(('+', ('member', 'group', f'{mid}{i}', 'member', 'group',
                            f'L{i + 1}')))
    return w


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _write_all(cs, writes):
    token = None
    for op, t in writes:
        token = cs.add_tuple(*t) if op == '+' else cs.remove_tuple(*t)
    return token


def test_overflow_poison_row_stalls_and_untokened_check_stops_serving_revoked_allow(
        session):
    """TK111 witness: the revocation of mallory is logged BEHIND the poison row.

    Was K=63 and a raw ``OverflowError`` until TK111 S5 (2026-10-03b); the poison row is
    now refused cleanly at K=31, and on the async schedule that is STILL a stall (the
    row is already logged), which is what this test pins."""
    writes = _diamond_writes(31) + [('-', MALLORY)]
    cs = ConnectedStore(session, 'st', schema=DIAMOND, sync=False)
    last = _write_all(cs, writes)

    with pytest.raises(PathCountExceeded):
        cs.catch_up(batch=1)
    # the poison row and the revocation behind it are the only rows left
    assert cs.lag() == 2
    assert cs.index_stalled
    assert 'PathCountExceeded' in cs.stall_error
    # a retry fails the same way and the stall stays live
    with pytest.raises(PathCountExceeded):
        cs.catch_up(batch=1)
    assert cs.index_stalled

    live = {O.t(*t) for op, t in writes if op == '+'} - {O.t(*MALLORY)}
    orc = O.Oracle(DIAMOND, sorted(live))
    assert orc.check(*MALLORY) is False
    # THE fail-open: was True (the stalled index still holds the revoked grant)
    assert cs.check(*MALLORY) is False
    # the fallback is the set engine, and it is right on a grant the index never saw
    deep = ('...', 'user', 'u', 'member', 'group', 'L31')
    assert orc.check(*deep) is True
    assert cs.check(*deep) is True
    # tokened reads were already correct and stay so
    assert cs.check(*MALLORY, at_least=last) is False
    # the enumeration surface has no fallback: an untokened lookup now refuses
    with pytest.raises(IndexStalled) as ei:
        cs.lookup('...', 'user', 'mallory')
    assert 'STALLED' in str(ei.value) and 'PathCountExceeded' in str(ei.value)
    with pytest.raises(IndexStalled):
        cs.lookup_reverse('viewer', 'doc', 'secret')


def test_fanout_over_cap_row_no_longer_stalls_the_async_apply(session, caplog):
    """TK112 C2, after the cap-policy decision (2026-10-03b): the cap is a SYNC-ADMISSION
    bound, so ``catch_up`` applies an over-cap row with a warning instead of stalling.

    Until then this test pinned the stall: the capped grant raised
    ``ClosureFanoutExceeded`` from ``catch_up`` with ``lag == 2``, and the stall marker
    kept the untokened check off the index. Now the REMOVE behind that row reaches the
    index, and the index itself answers correctly. Decision:
    ``docs/tk111-stall-aware-freshness-2026-10-02.md`` sec 7."""
    schema = DIAMOND
    cs = ConnectedStore(session, 'cs', schema=schema, sync=False)
    for i in range(30):
        cs.add_tuple('...', 'user', f'u{i}', 'member', 'group', 'big')
    old = ('...', 'user', 'u0', 'viewer', 'doc', 'old')
    cs.add_tuple(*old)
    cs.catch_up()
    assert cs.lag() == 0 and not cs.index_stalled
    assert cs.check(*old) is True

    cs.widx.idx.max_closure_fanout = 20       # an operator tightening the cap
    new = ('member', 'group', 'big', 'viewer', 'doc', 'new')
    cs.add_tuple(*new)                         # 30 closure rows: over the cap
    cs.remove_tuple(*old)
    with caplog.at_level('WARNING', logger='index_v4.core'):
        assert cs.catch_up() == 2
    assert cs.lag() == 0 and not cs.index_stalled and cs.stall_error is None
    assert any('materialised anyway' in r.getMessage() and 'limit of 20' in r.getMessage()
               for r in caplog.records)
    # answered BY THE INDEX (not stalled, so no fallback), and right
    assert cs.widx.check(*old) is False and cs.check(*old) is False
    assert cs.widx.check('...', 'user', 'u7', 'viewer', 'doc', 'new') is True
    assert cs.lookup('...', 'user', 'u0') is not None
    # the cap is still in force on this index outside catch_up: a direct write refuses
    from zanzibar_utils_v1 import ClosureFanoutExceeded
    with pytest.raises(ClosureFanoutExceeded):
        cs.widx.add_tuple('member', 'group', 'big', 'viewer', 'doc', 'newer')
    session.rollback()


def test_transient_failure_stalls_until_the_next_good_batch(session, monkeypatch):
    """D2: ANY catch_up failure records a stall, transient ones included. The cost of
    a false stall is a set-engine fallback until the next successful batch."""
    cs = ConnectedStore(session, 'st', schema=DIAMOND, sync=False)
    cs.add_tuple(*MALLORY)
    cs.catch_up()
    revoke = cs.remove_tuple(*MALLORY)

    real = store_mod.advance_index

    def flaky(*a, **kw):
        raise ConnectionError('simulated lost connection')

    monkeypatch.setattr(store_mod, 'advance_index', flaky)
    with pytest.raises(ConnectionError):
        cs.catch_up()
    assert cs.index_stalled and 'ConnectionError' in cs.stall_error
    assert cs.check(*MALLORY) is False            # not the index's stale True

    monkeypatch.setattr(store_mod, 'advance_index', real)
    assert cs.catch_up() == 1
    assert not cs.index_stalled
    assert cs.cursor.applied_log_id >= revoke
    assert cs.check(*MALLORY) is False            # now served by the caught-up index

    # The liveness RULE, pinned directly (sweep M8, 2026-10-02b: with advance_index
    # clearing the marker it is redundant, so no behavioural test could see it go). A
    # stall counts only while it sits AT the cursor: any advance invalidates it even
    # if nothing cleared it.
    cs.cursor.stalled_after = cs.cursor.applied_log_id - 1
    assert not cs.index_stalled and cs.stall_error is None
    cs.cursor.stalled_after = cs.cursor.applied_log_id
    assert cs.index_stalled
    session.rollback()


def test_replica_reader_sees_a_stall_recorded_by_another_instance(tmp_path):
    """D1 + D5: the stall is PERSISTED, so a reader instance whose own catch_up never
    runs stops trusting the index after its next refresh()."""
    engine = create_engine(f'sqlite:///{tmp_path / "st.db"}')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as ws, Session(engine) as rs:
        worker = ConnectedStore(ws, 'st', schema=DIAMOND, sync=False)
        _write_all(worker, _diamond_writes(31)[:2])
        worker.catch_up()
        reader = ConnectedStore(rs, 'st', schema=DIAMOND, sync=False)
        assert reader.check(*MALLORY) is True

        _write_all(worker, _diamond_writes(31)[2:] + [('-', MALLORY)])
        with pytest.raises(PathCountExceeded):
            worker.catch_up(batch=1)

        reader.refresh()
        assert reader.index_stalled
        assert reader.check(*MALLORY) is False    # was True: the replica's stale ALLOW
        with pytest.raises(IndexStalled):
            reader.lookup_reverse('viewer', 'doc', 'secret')
        rs.rollback()
        ws.rollback()
    engine.dispose()


def test_replica_polling_by_rollback_gets_a_caught_up_set_engine_answer(tmp_path):
    """D3: the fallback must catch the set engine up, not just switch to it. A reader
    that polls with a bare ``rollback()`` (the snapshot-advance step
    ``TupleSource.catch_up_evaluator``'s docstring prescribes) sees the stall on the
    reloaded cursor while its in-memory evaluator still predates the revocation.
    Without the catch-up the fallback answers from that stale evaluator: sweep M5,
    2026-10-02b, was INERT until this test existed."""
    engine = create_engine(f'sqlite:///{tmp_path / "st.db"}')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as ws, Session(engine) as rs:
        worker = ConnectedStore(ws, 'st', schema=DIAMOND, sync=False)
        _write_all(worker, _diamond_writes(31)[:2])
        worker.catch_up()
        reader = ConnectedStore(rs, 'st', schema=DIAMOND, sync=False)
        assert reader.check(*MALLORY) is True

        _write_all(worker, _diamond_writes(31)[2:] + [('-', MALLORY)])
        with pytest.raises(PathCountExceeded):
            worker.catch_up(batch=1)

        rs.rollback()                       # new snapshot; the evaluator is NOT rebuilt
        assert reader.index_stalled
        assert reader.source.evaluator_watermark < worker.watermark()
        assert reader.check(*MALLORY) is False
        rs.rollback()
        ws.rollback()
    engine.dispose()
