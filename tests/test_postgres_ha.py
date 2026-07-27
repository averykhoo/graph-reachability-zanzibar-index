"""The HA/concurrency scenarios SQLite provably cannot express.

Everything here needs a REAL server (``ZANZIBAR_TEST_DSN``); on SQLite these skip,
and under ``ZANZIBAR_PG_REQUIRED=1`` a missing DSN is a hard error rather than a
silent green. The reason each of these lives in its own module rather than in
``tests/test_connectedstore_multi_instance.py`` is that the mechanism under test
does not EXIST on SQLite:

  * ``take_row_write_lock``'s ``FOR UPDATE`` arm (pysqlite renders it to nothing, so
    the SQLite leg exercises a different mechanism -- a no-op UPDATE taking the
    RESERVED lock);
  * lock ORDERING between two row locks (there is only one lock on SQLite: the
    database);
  * ``assert_read_isolation`` (returns immediately on SQLite by design, and until
    now had only ever met a hand-written fake session);
  * real MVCC, where a LOWER log id can commit AFTER a higher one -- the precise
    hazard ``log_gap`` / ``WatermarkGap`` exist to catch, and the one SQLite's
    single-writer model cannot produce.

NO XFAILS REMAIN (2026-07-27). This module was written with strict, ``raises=``-typed
xfails for properties the production code CLAIMED and PostgreSQL falsified -- each
reproduced before it was written down. The last of them,
``test_open_instance_races_a_concurrent_commit``, became a plain pin when
``TupleSource._consistent_rebuild`` landed; an xfail is itself a failure that passes,
so it is a state to leave, not to keep. If a future finding needs one, keep the
``raises=``: a bare strict xfail also "passes" when the database is unreachable, which
is the exact silent-green failure this module exists to eliminate.
"""

from __future__ import annotations

import threading
import time
from unittest import mock

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

import connectedstore.apply as apply_mod
import connectedstore.source as source_mod
from connectedstore import (ConnectedStore, StaleRead, TupleSource, UnsafeIsolationLevel,
                            WatermarkGap, advance_index, assert_read_isolation, log_gap,
                            log_rows, log_watermark)
from connectedstore.models import SchemaV4, TupleLogV1
from index_v4.invariants import snapshot_rows
from index_v4.models import StoreV4
from setengine import TupleV1
from tests.dbengine import requires_rdbms, server_engine, shared_engine
from tests.oracle import Oracle, OracleTuple

SCHEMA = '''
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

GRID = [('...', 'user', sn, rel, 'doc', on)
        for sn in ('u1', 'u2', 'ghost', '*')
        for rel in ('viewer', 'editor', 'public', 'blocked')
        for on in ('d1', 'd2')]

#: How long a probe waits before we call it "blocked". Long enough that a machine
#: hiccup does not read as a lock, short enough that a genuinely-unblocked probe
#: does not sit here.
BLOCK_MS = 1500
#: A probe that must NOT block has to come back well inside BLOCK_MS for the
#: distinction to mean anything.
FAST_S = 0.6


def _bootstrap(tmp_path, *store_ids):
    """One clean database + a bootstrapped ConnectedStore per id. Skips (or hard-fails
    under ZANZIBAR_PG_REQUIRED=1) when no server DSN is configured."""
    requires_rdbms()
    engine = shared_engine(tmp_path, 'unused-on-postgres.db')
    with Session(engine) as boot:
        for sid in store_ids:
            ConnectedStore(boot, sid, schema=SCHEMA)
        boot.commit()
    return engine


def _statement_timeout(session, ms=BLOCK_MS):
    """Turn "blocks forever" into a bounded, catchable error. This is what makes
    blocking OBSERVABLE: without it a test that proves a lock works is
    indistinguishable from a test that hangs."""
    session.connection().exec_driver_sql(f'SET LOCAL statement_timeout = {int(ms)}')


def _await_blocked_backend(engine, deadline_s=20.0) -> bool:
    """Wait until some backend is queued on a lock. Returns whether it happened, so
    the caller can assert on it instead of walking into a vacuous check.

    Takes the ENGINE, not a caller's session: polling ``pg_locks`` needs a fresh
    snapshot each time (i.e. a rollback), and doing that on a session that is HOLDING
    the lock under test would release it."""
    end = time.monotonic() + deadline_s
    while time.monotonic() < end:
        with engine.connect() as conn:
            n = conn.execute(
                text('SELECT count(*) FROM pg_locks WHERE NOT granted')).scalar()
        if n:
            return True
        time.sleep(0.02)
    return False


def _raw_log_row(session, name):
    """Append a TupleLogV1 row DIRECTLY, bypassing TupleSource -- i.e. bypassing the
    per-store critical section. That is the point: the hazard log_gap guards is
    "two writers whose log ids commit out of order", and the lock discipline makes
    that unreachable through the supported write path (proved positively by
    ``test_lock_discipline_keeps_log_commits_in_id_order``). To test the GUARD we
    have to construct the state the guard exists for."""
    row = TupleLogV1(store_id='s', op='ADD', subject_predicate='...',
                     subject_type='user', subject_name=name, relation='editor',
                     object_type='doc', object_name='d1')
    session.add(row)
    session.flush()
    assert row.id is not None
    return row.id


# =========================================================================== #
# (a) FOR UPDATE really blocks, on the row we think it does, in the order we
#     documented.
# =========================================================================== #

def test_for_update_source_lock_really_blocks_a_second_writer(tmp_path):
    """``TupleSource._lock_source``'s FOR UPDATE arm has never executed in this
    repo's history. Prove three things about it at once: it BLOCKS (not "passes
    through"), it blocks on the ``SchemaV4`` row of THIS store only, and it releases
    on commit."""
    engine = _bootstrap(tmp_path, 's', 'other')
    with Session(engine) as sa, Session(engine) as sb, Session(engine) as sc:
        a = TupleSource(sa, 's')
        a.add('...', 'user', 'u1', 'editor', 'doc', 'd1')   # holds the lock, uncommitted

        b = TupleSource(sb, 's')
        _statement_timeout(sb)
        t0 = time.monotonic()
        with pytest.raises(OperationalError) as exc:
            b._lock_source()
        waited = time.monotonic() - t0
        # The distinction that matters: a no-op lock returns instantly. This one sat
        # in the lock queue until the server cancelled it.
        assert type(exc.value.orig).__name__ == 'QueryCanceled', exc.value.orig
        assert waited >= BLOCK_MS / 1000 * 0.8, f'returned too fast to have blocked: {waited}s'
        sb.rollback()

        # Granularity: the lock is the store's SchemaV4 ROW, so another store's row is
        # free. Without this the test would also pass if we locked the whole table.
        _statement_timeout(sc)
        t1 = time.monotonic()
        other = sc.exec(select(SchemaV4).where(SchemaV4.store_id == 'other')
                        .with_for_update()).first()
        assert other is not None and other.store_id == 'other'
        assert time.monotonic() - t1 < FAST_S, 'a different store blocked -> not row-level'
        sc.rollback()

        sa.commit()                                        # release

    with Session(engine) as sb2:
        b2 = TupleSource(sb2, 's')
        _statement_timeout(sb2)
        b2._lock_source()                                  # no raise: lock is free
        sb2.rollback()


def test_lock_ordering_source_lock_is_held_before_the_store_lock(tmp_path):
    """The documented LOCK ORDERING invariant (``source.py:_lock_source`` docstring:
    source lock BEFORE the graph store lock) is what makes the two-lock protocol
    deadlock-free, and it has never been observed. Observe it: hold the graph
    ``StoreV4`` row, let a writer run, and show that while the writer is queued on
    THAT lock it is already holding the ``SchemaV4`` one."""
    engine = _bootstrap(tmp_path, 's')
    done: list = []
    errors: list = []

    with Session(engine) as holder:
        holder.exec(select(StoreV4).where(StoreV4.id == 's').with_for_update()).first()

        def writer():
            try:
                with Session(engine) as sw:
                    cs = ConnectedStore(sw, 's')
                    cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
                    done.append(True)
            except Exception as e:                          # pragma: no cover
                errors.append(e)

        t = threading.Thread(target=writer)
        t.start()
        try:
            assert _await_blocked_backend(engine), 'the writer never queued on the store lock'
            with Session(engine) as probe:
                _statement_timeout(probe)
                t0 = time.monotonic()
                with pytest.raises(OperationalError) as exc:
                    probe.exec(select(SchemaV4).where(SchemaV4.store_id == 's')
                               .with_for_update()).first()
                # The writer is stuck on the SECOND lock while still holding the FIRST:
                # that IS the ordering claim, observed rather than reasoned.
                assert type(exc.value.orig).__name__ == 'QueryCanceled'
                assert time.monotonic() - t0 >= BLOCK_MS / 1000 * 0.8
                probe.rollback()
        finally:
            holder.rollback()                               # release the store lock
            t.join(timeout=60)
    assert not errors
    assert done == [True], 'the writer never completed after the store lock was released'

    with Session(engine) as s:
        assert TupleSource(s, 's').check('...', 'user', 'u1', 'editor', 'doc', 'd1')


# =========================================================================== #
# (b) Concurrent multi-writer admission against a real lock
# =========================================================================== #

def test_concurrent_writers_log_integrity_and_index_equals_replay(tmp_path):
    """N real writer instances, one store. Every accepted write appears in the log
    exactly once, the log ids are CONTIGUOUS (the property the whole
    ``id > watermark`` tailing design rests on), and the resulting graph index is
    byte-identical to a single-writer replay of that log -- with the independent
    oracle as ground truth for the answers."""
    engine = _bootstrap(tmp_path, 's', 'twin')
    THREADS, PER = 4, 6
    plans = {t: [('...', 'user', f't{t}u{i}', 'editor', 'doc', 'd1' if i % 2 else 'd2')
                 for i in range(PER)]
             for t in range(THREADS)}
    accepted: list = []
    errors: list = []
    lock = threading.Lock()

    # Instances are opened HERE, before any write, deliberately: opening one
    # CONCURRENTLY with a commit is a separate, real defect on this dialect
    # (test_open_instance_races_a_concurrent_commit below). Mixing the two would
    # make this test flaky and would stop it testing the lock discipline.
    sessions = [Session(engine) for _ in range(THREADS)]
    stores = [ConnectedStore(s, 's') for s in sessions]

    def worker(t):
        try:
            for raw in plans[t]:
                stores[t].add_tuple(*raw)                   # blocks, never spins
                with lock:
                    accepted.append(raw)
        except Exception as e:                              # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(THREADS)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=120)
    for s in sessions:
        s.close()
    assert not errors
    assert len(accepted) == THREADS * PER == 24             # count what we did

    with Session(engine) as session:
        rows = log_rows(session, 's', 0)
        ids = [r.id for r in rows]
        assert len(rows) == len(accepted)
        # Exactly once, and contiguous. A gap here would mean a burned/absent id,
        # which is precisely what makes a tailer skip a row forever.
        assert ids == list(range(ids[0], ids[0] + len(ids)))
        logged = [(r.subject_predicate, r.subject_type, r.subject_name,
                   r.relation, r.object_type, r.object_name) for r in rows]
        assert sorted(logged) == sorted(accepted)
        assert all(r.op == 'ADD' for r in rows)

        # The materialized index must equal a single-writer replay of the log in id
        # order (the log IS the serialization the lock discipline produces).
        twin = ConnectedStore(session, 'twin')
        for raw in logged:
            twin.add_tuple(*raw)
        assert snapshot_rows(session, 's') == snapshot_rows(session, 'twin')

        # ...and both agree with the independent oracle over the whole grid.
        oracle = Oracle(SCHEMA, [OracleTuple(*raw) for raw in logged])
        cs = ConnectedStore(session, 's')
        checked = 0
        for q in GRID:
            exp = oracle.check(*q)
            assert cs.check(*q) == exp, q
            assert twin.check(*q) == exp, q
            checked += 1
        assert checked == len(GRID) > 0

        # And the source of truth holds exactly the accepted set, no duplicates.
        tuples = session.exec(select(TupleV1).where(TupleV1.store_id == 's')).all()
        assert len(tuples) == len(accepted)


# =========================================================================== #
# (c) assert_read_isolation meets a real dialect for the first time
# =========================================================================== #

@pytest.mark.parametrize('level,safe', [('READ COMMITTED', True),
                                        ('SERIALIZABLE', False),
                                        ('REPEATABLE READ', False)])
def test_assert_read_isolation_against_a_real_server(level, safe):
    """Until now this function had only ever been shown a fake session reporting a
    string. Show it a real PostgreSQL connection at each level and check both that
    the server round-trips the level and that the verdict matches
    ``SAFE_ISOLATION_LEVELS``.

    SERIALIZABLE was in that set until 2026-07-27 and moved to the REFUSED side once
    this file demonstrated it reproduces the ZT-P1-5 fail-open -- see
    ``test_serializable_bind_is_refused``."""
    dsn = requires_rdbms()
    engine = server_engine(dsn, isolation_level=level)
    with Session(engine) as s:
        assert s.connection().get_isolation_level() == level
        if safe:
            assert_read_isolation(s)                        # no raise
        else:
            with pytest.raises(UnsafeIsolationLevel) as exc:
                assert_read_isolation(s)
            assert 'READ COMMITTED' in str(exc.value)
        s.rollback()


def test_connected_store_refuses_a_repeatable_read_bind(tmp_path):
    """End to end: the refusal happens at construction, before anything touches the
    store -- so an operator cannot accidentally run the whole system at a level where
    log tailing silently stops short."""
    _bootstrap(tmp_path, 's')   # a real, openable store -- so the refusal below can
                                # only be about the isolation level, nothing else
    rr = server_engine(requires_rdbms(), isolation_level='REPEATABLE READ')
    with Session(rr) as s:
        with pytest.raises(UnsafeIsolationLevel):
            ConnectedStore(s, 's')
        s.rollback()


# =========================================================================== #
# (d) WatermarkGap / log_gap against real MVCC
# =========================================================================== #

def test_log_gap_finds_a_row_committed_out_of_id_order(tmp_path):
    """The hazard, constructed for real: PostgreSQL hands out log ids at INSERT time
    but visibility at COMMIT time, so a lower id can become visible after a higher
    one. A reader that tailed while the lower id was uncommitted holds a
    non-contiguous view -- exactly the state that would make it skip a row forever."""
    engine = _bootstrap(tmp_path, 's')
    with Session(engine) as sx, Session(engine) as sy, Session(engine) as sr:
        base = log_watermark(sr, 's')
        sr.rollback()
        x_id = _raw_log_row(sx, 'x')
        y_id = _raw_log_row(sy, 'y')
        assert x_id < y_id                                  # id order is INSERT order
        sy.commit()                                         # ...commit order is not

        visible = [r.id for r in log_rows(sr, 's', base)]
        # Non-vacuous: the whole test is worthless unless the reader really does see
        # a hole here.
        assert visible == [y_id], f'expected only the higher id to be visible, got {visible}'

        sx.commit()                                         # the lower id lands late
        assert log_gap(sr, 's', base, y_id, visible) == x_id
        # ...and a contiguous view is correctly reported as no gap (the fast path).
        assert log_gap(sr, 's', base, y_id, [x_id, y_id]) is None
        sr.rollback()


def test_advance_index_raises_watermark_gap_on_a_real_out_of_order_commit(tmp_path,
                                                                          monkeypatch):
    """``advance_index`` must REFUSE the advance rather than bury the row.

    The interleaving (the lower id commits after ``log_rows`` returned but before the
    contiguity re-read) is a real window on a real server; the hook below only makes
    it deterministic instead of a race. Everything else -- the ids, the visibility,
    the commit -- is genuine PostgreSQL MVCC."""
    engine = _bootstrap(tmp_path, 's')
    with Session(engine) as sr, Session(engine) as sx, Session(engine) as sy:
        cs = ConnectedStore(sr, 's')
        base = cs.cursor.applied_log_id
        x_id = _raw_log_row(sx, 'x')
        y_id = _raw_log_row(sy, 'y')
        sy.commit()

        real_log_rows = apply_mod.log_rows
        fired = []

        def hooked(*a, **k):
            rows = real_log_rows(*a, **k)
            if not fired:
                fired.append(True)
                sx.commit()                                 # the late lower id
            return rows

        monkeypatch.setattr(apply_mod, 'log_rows', hooked)
        with pytest.raises(WatermarkGap) as exc:
            advance_index(sr, cs.cursor, cs.widx, cs.ruleset, cs.proc)
        assert fired == [True], 'the interleave never happened -> the test proved nothing'
        assert str(x_id) in str(exc.value)
        sr.rollback()

    # Nothing was committed, and a fresh pass applies BOTH rows contiguously.
    with Session(engine) as s2:
        cs2 = ConnectedStore(s2, 's')
        assert cs2.cursor.applied_log_id == base
        assert cs2.catch_up() == 2
        assert cs2.cursor.applied_log_id == y_id
        assert cs2.check('...', 'user', 'x', 'editor', 'doc', 'd1') is True
        assert cs2.check('...', 'user', 'y', 'editor', 'doc', 'd1') is True


def test_lock_discipline_keeps_log_commits_in_id_order(tmp_path):
    """The positive half, and the more important one: through the SUPPORTED write
    path the hazard above is UNREACHABLE, because every write appends inside the
    per-store critical section. A concurrent observer therefore never sees a hole.

    This is a proof, not a smoke test: the observer counts its samples and the test
    fails if it never actually raced (or if any single sample was non-contiguous)."""
    engine = _bootstrap(tmp_path, 's')
    stop = threading.Event()
    samples: list = []
    holes: list = []
    errors: list = []

    def observer():
        try:
            with Session(engine) as so:
                while not stop.is_set():
                    so.rollback()                           # fresh snapshot each sample
                    ids = [r.id for r in log_rows(so, 's', 0)]
                    samples.append(len(ids))
                    if ids and ids != list(range(ids[0], ids[0] + len(ids))):
                        holes.append(ids)
                        return
        except Exception as e:                              # pragma: no cover
            errors.append(e)

    # Same reason as the previous test: open every instance before the first commit,
    # so the constructor race pinned by test_open_instance_races_a_concurrent_commit
    # cannot contaminate the property under test here.
    sessions = [Session(engine) for _ in range(3)]
    sources = [TupleSource(s, 's') for s in sessions]

    def writer(t):
        try:
            for i in range(8):
                sources[t].add('...', 'user', f'w{t}n{i}', 'editor', 'doc', 'd1')
                sessions[t].commit()
        except Exception as e:                              # pragma: no cover
            errors.append(e)

    obs = threading.Thread(target=observer)
    obs.start()
    ws = [threading.Thread(target=writer, args=(t,)) for t in range(3)]
    for w in ws:
        w.start()
    for w in ws:
        w.join(timeout=120)
    stop.set()
    obs.join(timeout=30)
    for s in sessions:
        s.close()

    assert not errors
    assert not holes, f'a lower log id committed after a higher one: {holes[0]}'
    # Non-vacuous, three ways: the observer sampled repeatedly, it saw the log GROW,
    # and at least one sample caught it PART-BUILT (i.e. it really raced the writers
    # rather than only seeing empty-then-final).
    assert len(samples) >= 5, f'observer only sampled {len(samples)} times'
    assert min(samples) < max(samples), 'observer never saw the log grow'
    assert any(0 < n < 24 for n in samples), f'observer never raced a writer: {samples}'

    with Session(engine) as s:
        ids = [r.id for r in log_rows(s, 's', 0)]
        assert len(ids) == 24
        assert ids == list(range(ids[0], ids[0] + 24))


def test_log_gap_is_snapshot_served_under_a_pinned_snapshot(tmp_path):
    """``log_gap`` is blind under a pinned snapshot -- which is WHY only READ COMMITTED
    may ever be admitted.

    ``log_gap`` used to justify itself with "A LOCKING read, not a snapshot read ...
    InnoDB serves locking reads from the LATEST committed version, so FOR SHARE
    surfaces the hidden row." That is an InnoDB property, and this project does not
    support MySQL. On PostgreSQL, ``SELECT ... FOR SHARE`` under REPEATABLE READ or
    SERIALIZABLE is served from the TRANSACTION snapshot like any other read, so the
    row it exists to find stays invisible and it returns ``None``.

    Measured here rather than argued, and pinned in the direction that matters: this
    test asserts the BLINDNESS. If someone re-admits a snapshot-pinning level to
    ``SAFE_ISOLATION_LEVELS``, the gap check is silently disarmed and the ZT-P1-5
    fail-open comes back -- see ``test_serializable_bind_is_refused``. The lock hint is
    not what makes the gap check sound; the isolation gate is."""
    engine = _bootstrap(tmp_path, 's')
    rr = server_engine(requires_rdbms(), isolation_level='REPEATABLE READ')
    with Session(rr) as sr:
        base = log_watermark(sr, 's')                       # pins the snapshot
        with Session(engine) as sw:
            token = TupleSource(sw, 's').add('...', 'user', 'u1', 'editor', 'doc', 'd1')
            sw.commit()
        assert token > base                                 # the row IS committed
        # ...and the reader's pinned snapshot cannot see it -- neither by a plain read
        # nor through log_gap's FOR SHARE.
        assert [r.id for r in log_rows(sr, 's', base)] == []
        assert log_gap(sr, 's', base, token, ()) is None
        sr.rollback()

    # The contrast that makes the gate meaningful: at READ COMMITTED -- the only level
    # the guard admits -- the same probe finds the row.
    rc = server_engine(requires_rdbms(), isolation_level='READ COMMITTED')
    with Session(rc) as src_s:
        base2 = 0
        head = log_watermark(src_s, 's')
        assert head >= token
        assert log_gap(src_s, 's', base2, head, ()) == 1
        src_s.rollback()


def test_serializable_bind_is_refused(tmp_path):
    """SERIALIZABLE must be REFUSED, and the reason is a reproduced fail-open.

    Until 2026-07-27 ``SAFE_ISOLATION_LEVELS`` accepted it, on the stated grounds that
    "PostgreSQL aborts the transaction with a serialization failure rather than letting
    it act on a stale view". Measured against a real server: it does not. A
    ``SELECT ... FOR UPDATE`` against a row another transaction only LOCK-modified
    raises no conflict, and a plain log read is not a dangerous SSI structure on its
    own. So a SERIALIZABLE ``TupleSource`` used to pin its snapshot at open, miss a
    concurrently committed REVOCATION, jump its watermark straight past it (``log_gap``
    being blind for the reason pinned in
    ``test_log_gap_is_snapshot_served_under_a_pinned_snapshot``), and then answer
    ``check(at_least=<revocation token>)`` with **True** -- the freshness mechanism
    certifying a state that never existed. That is precisely the ZT-P1-5 scenario the
    guard was written to close, reproduced at an ACCEPTED level.

    The escalation sequence is replayed below against the now-refusing guard, so this
    test fails if the level is ever re-admitted -- it does not merely assert a set
    membership."""
    engine = _bootstrap(tmp_path, 's')
    with Session(engine) as s:
        ConnectedStore(s, 's').add_tuple('...', 'user', 'victim', 'editor', 'doc', 'd1')

    ser = server_engine(requires_rdbms(), isolation_level='SERIALIZABLE')
    with Session(ser) as ss:
        with pytest.raises(UnsafeIsolationLevel) as exc:
            TupleSource(ss, 's')
        assert 'READ COMMITTED' in str(exc.value)
        ss.rollback()

    # The refusal is the whole defence, so prove the thing it defends against is real:
    # drive the identical sequence with the guard bypassed and watch the revoked grant
    # come back ALLOWED under an explicit freshness demand.
    with Session(ser) as ss:
        with mock.patch.object(source_mod, 'assert_read_isolation', lambda _s: None):
            src = TupleSource(ss, 's')                      # open pins the snapshot
            assert src.check('...', 'user', 'victim', 'editor', 'doc', 'd1') is True

            with Session(engine) as sw:                     # another instance revokes
                revoked = TupleSource(sw, 's').remove(
                    '...', 'user', 'victim', 'editor', 'doc', 'd1')
                sw.commit()

            src.add('...', 'user', 'other', 'editor', 'doc', 'd1')
            ss.commit()
            escalated = src.check('...', 'user', 'victim', 'editor', 'doc', 'd1',
                                  at_least=revoked)
        ss.rollback()
    assert escalated is True, (
        'the SERIALIZABLE escalation no longer reproduces even with the isolation '
        'guard bypassed. That is good news, but it means this test is no longer '
        'evidence for the refusal above -- re-derive why SERIALIZABLE is refused '
        'before relaxing anything.')


def test_open_instance_races_a_concurrent_commit(tmp_path, monkeypatch):
    """Opening an instance while another instance commits must yield a usable
    instance -- and a self-CONSISTENT one, whose watermark is true of the state it
    just rebuilt.

    WAS A STRICT XFAIL until 2026-07-27; the bug is real and was reproduced here
    before it was fixed. ``TupleSource.__init__`` read ``log_watermark(...)`` and THEN
    rebuilt the evaluator from ``TupleV1`` -- two statements. Under SQLite-WAL both run
    in one pinned snapshot, so the pair is atomic by accident; at PostgreSQL READ
    COMMITTED (the only level ``assert_read_isolation`` admits, precisely BECAUSE every
    statement re-snapshots) a write committed between them lands in the rebuild but not
    in the watermark. The instance was then born with its evaluator AHEAD of its
    watermark, and the next ``catch_up_evaluator()`` replayed that row into
    ``apply_logged``'s strict guard: ``RuntimeError(... watermark corruption)``,
    permanently, since ``add``/``remove`` catch up first. Reading the watermark AFTER
    the rebuild would have turned that loud failure into a silent skip, so the pair was
    made genuinely atomic instead (``TupleSource._consistent_rebuild``: optimistic
    wm/rebuild/wm loop, then the shared source lock).

    The hook does not CREATE the window, it makes the real one deterministic: it
    commits from a genuinely separate session at the exact point the constructor is
    between its two reads. The assertions below therefore check BOTH that the
    interleaving happened AND that the constructor noticed it -- a fix that merely
    stopped the race being constructible would fail here, not pass quietly."""
    engine = _bootstrap(tmp_path, 's')
    real_open = source_mod.open_set_engine
    fired: list = []

    def hooked(session, store_id, **kw):
        # Claim the slot BEFORE doing anything: the writer below opens its own
        # TupleSource, which re-enters this very hook.
        if not fired:
            fired.append(0)
            with Session(engine) as sw:
                fired[0] = TupleSource(sw, 's').add(
                    '...', 'user', 'u1', 'editor', 'doc', 'd1')
                sw.commit()
        return real_open(session, store_id, **kw)

    monkeypatch.setattr(source_mod, 'open_set_engine', hooked)
    with Session(engine) as sb:
        b = TupleSource(sb, 's')
        # (1) the race was really run: a foreign session committed inside the ctor.
        assert fired and fired[0] > 0, 'the interleave never happened'
        # (2) ...and the constructor SAW it. One attempt would mean the commit landed
        # outside the window after all, i.e. this test stopped testing anything.
        assert b.snapshot_attempts >= 2, (
            f'the constructor never detected the concurrent commit '
            f'(snapshot_attempts={b.snapshot_attempts}) -- the race is no longer being '
            f'constructed, so this test is no longer evidence for the fix')
        # (3) the instance is self-consistent: the evaluator answers the raced write
        # AND its watermark claims it. Those two used to disagree.
        assert b.check('...', 'user', 'u1', 'editor', 'doc', 'd1') is True
        assert b.evaluator_watermark >= fired[0]
        assert b.evaluator_lag() == 0
        assert b.catch_up_evaluator() == 0                   # <-- RuntimeError before
        # (4) and it is not bricked: the next write on it works, end to end.
        token = b.add('...', 'user', 'u2', 'editor', 'doc', 'd1')
        sb.commit()
        assert token > fired[0]
        assert b.check('...', 'user', 'u2', 'editor', 'doc', 'd1', at_least=token) is True
        assert b.evaluator_lag() == 0
        sb.rollback()

    # The store really holds both writes -- the raced one was not lost in a rebuild.
    with Session(engine) as s:
        assert [r.subject_name for r in log_rows(s, 's', 0)] == ['u1', 'u2']


def test_refresh_evaluator_races_a_concurrent_commit(tmp_path, monkeypatch):
    """The same window on the OTHER opener, which is the more dangerous one:
    ``refresh_evaluator`` sits on ``ConnectedStore._write``'s error path, so an
    ordinary rejected write could enter it -- and its old comment claimed reading the
    watermark first was "conservative", when that ordering IS the window.

    Hook point differs (the constructor is already past), so the commit is driven from
    inside ``SetEngine.rebuild`` instead."""
    engine = _bootstrap(tmp_path, 's')
    fired: list = []

    with Session(engine) as sb:
        b = TupleSource(sb, 's')
        real_rebuild = b.engine.rebuild

        def hooked_rebuild():
            if not fired:
                fired.append(0)
                with Session(engine) as sw:
                    fired[0] = TupleSource(sw, 's').add(
                        '...', 'user', 'u1', 'editor', 'doc', 'd1')
                    sw.commit()
            real_rebuild()

        monkeypatch.setattr(b.engine, 'rebuild', hooked_rebuild)
        b.refresh_evaluator()

        assert fired and fired[0] > 0, 'the interleave never happened'
        assert b.snapshot_attempts >= 2, (
            f'refresh_evaluator never detected the concurrent commit '
            f'(snapshot_attempts={b.snapshot_attempts})')
        assert b.check('...', 'user', 'u1', 'editor', 'doc', 'd1') is True
        assert b.evaluator_watermark >= fired[0]
        assert b.evaluator_lag() == 0
        assert b.catch_up_evaluator() == 0                   # <-- RuntimeError before
        sb.rollback()


# =========================================================================== #
# (e) Read-your-writes / at_least / StaleRead across two instances
# =========================================================================== #

def test_read_your_writes_across_two_instances(tmp_path):
    """The zookie-lite contract on a real server: B's evaluator predates A's write, a
    tokened read tails the delta on demand, and B then answers exactly what the
    independent oracle says -- across the whole grid, not just the one query."""
    engine = _bootstrap(tmp_path, 's')
    with Session(engine) as sa, Session(engine) as sb:
        a = TupleSource(sa, 's')
        b = TupleSource(sb, 's')                            # opened BEFORE the writes
        assert b.evaluator_watermark == 0

        present = [('...', 'user', '*', 'public', 'doc', 'd1'),
                   ('...', 'user', 'u1', 'blocked', 'doc', 'd1'),
                   ('...', 'user', 'u1', 'editor', 'doc', 'd2')]
        token = 0
        for raw in present:
            token = a.add(*raw)
            sa.commit()
        assert token > 0

        # No rollback on B: on PostgreSQL READ COMMITTED the catch-up's next statement
        # sees the committed head, which is precisely why READ COMMITTED is mandatory.
        assert b.evaluator_watermark < token
        q = ('...', 'user', 'u1', 'viewer', 'doc', 'd2')
        assert b.check(*q, at_least=token) is True
        assert b.evaluator_watermark == token
        assert b.evaluator_lag() == 0

        oracle = Oracle(SCHEMA, [OracleTuple(*r) for r in present])
        checked = 0
        for g in GRID:
            exp = oracle.check(*g)
            assert b.check(*g) == exp, g
            assert a.check(*g) == exp, g
            checked += 1
        assert checked == len(GRID) > 0


def test_stale_read_on_an_unreachable_token(tmp_path):
    """A token past the log head can never become visible: refuse, do not loop.

    This is the ONLY StaleRead path reachable on PostgreSQL READ COMMITTED -- the
    pinned-snapshot path that ``tests/test_connectedstore_multi_instance.py`` pins on
    SQLite cannot occur here, because every statement re-snapshots. That is a
    property difference, not a bug: see
    ``test_read_committed_gives_a_reader_no_stable_snapshot``."""
    engine = _bootstrap(tmp_path, 's')
    with Session(engine) as sa, Session(engine) as sb:
        a = TupleSource(sa, 's')
        a.add('...', 'user', 'u1', 'editor', 'doc', 'd1')
        sa.commit()

        b = TupleSource(sb, 's')
        head = log_watermark(sb, 's')
        assert head > 0
        with pytest.raises(StaleRead):
            b.check('...', 'user', 'u1', 'viewer', 'doc', 'd1', at_least=head + 1000)
        # ...and the reachable token still works from the same session.
        assert b.check('...', 'user', 'u1', 'viewer', 'doc', 'd1', at_least=head) is True


def test_read_committed_gives_a_reader_no_stable_snapshot(tmp_path):
    """WHY ``test_reader_session_sees_consistent_snapshots`` (concurrency module) is
    SQLite-only.

    On SQLite-WAL a transaction pins one snapshot, so a reader's rebuilt evaluator
    and its later index probes describe the same committed state. PostgreSQL READ
    COMMITTED -- the level ``assert_read_isolation`` REQUIRES -- re-snapshots per
    STATEMENT, so a multi-statement read straddles concurrent commits. Demonstrated
    deterministically here rather than left as a flaky assertion elsewhere."""
    engine = _bootstrap(tmp_path, 's')
    with Session(engine) as sr:
        before = len(sr.exec(select(TupleLogV1).where(TupleLogV1.store_id == 's')).all())
        with Session(engine) as sw:
            ConnectedStore(sw, 's').add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
        after = len(sr.exec(select(TupleLogV1).where(TupleLogV1.store_id == 's')).all())
        # SAME transaction, two statements, different answers.
        assert (before, after) == (0, 1)
        assert sr.in_transaction()
        sr.rollback()
