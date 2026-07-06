"""
Concurrency tests for the v4 graph index.

Each thread gets its OWN Session + ReachabilityIndex (the correct SQLAlchemy pattern --
a Session is not thread-safe and must never be shared). Threads insert overlapping graphs
(private chains that all converge on a shared hub) against one shared store, then we assert
the closure is correct and cross-thread isolation holds.

What this proves and what it does not:
  * per-thread sessions do not corrupt one another, and reads are safe during writes;
  * on SQLite (default rollback-journal) write transactions are exclusive, so the
    ref-counted read-modify-write is atomic per transaction -- concurrent writers, with a
    busy-timeout and retry on SQLITE_BUSY / node-creation IntegrityError, produce the
    correct closure. This is the "SQLite serializes writers" half of the cost model.
  * it does NOT exercise the MVCC lost-update race (PostgreSQL/MySQL, READ COMMITTED)
    that ReachabilityIndex._lock_store's FOR UPDATE lock guards against -- FOR UPDATE is a
    no-op on SQLite. A Postgres-backed run (point DATABASE_URL at one) would cover that;
    here we validate the concurrent-session mechanics on the default backend.
"""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlmodel import Session, SQLModel, create_engine

from index_v4 import ReachabilityIndex, Store


def _file_engine(path):
    engine = create_engine(f'sqlite:///{path}',
                           connect_args={'check_same_thread': False, 'timeout': 60})

    @event.listens_for(engine, 'connect')
    def _busy_timeout(dbapi, _rec):              # let writers wait rather than fail instantly
        cur = dbapi.cursor()
        cur.execute('PRAGMA busy_timeout=60000')
        cur.close()

    SQLModel.metadata.create_all(engine)
    return engine


def _add_retry(idx, sess, *args, attempts=300):
    """Concurrent writers can hit SQLITE_BUSY, and concurrent find-or-create of a shared
    node can hit a unique-constraint IntegrityError; both are safe to retry."""
    for _ in range(attempts):
        try:
            idx.add_edge(*args)
            sess.commit()
            return
        except (OperationalError, IntegrityError):
            sess.rollback()
            time.sleep(0.005)
    raise RuntimeError(f'gave up committing {args}')


def test_concurrent_overlapping_writes(tmp_path):
    engine = _file_engine(tmp_path / 'conc.db')
    with Session(engine) as s:
        s.add(Store(id='c'))
        s.commit()

    THREADS, CHAIN = 6, 15

    def work(t):
        # own session per thread; connected chain t_0 -> ... -> t_CHAIN -> hub (predicate 'r'
        # throughout so consecutive edges share nodes). 'hub' is shared across all threads.
        with Session(engine) as sess:
            idx = ReachabilityIndex(sess, 'c')
            for i in range(CHAIN):
                _add_retry(idx, sess, 'r', 'n', f'{t}_{i}', 'r', 'n', f'{t}_{i + 1}')
            _add_retry(idx, sess, 'r', 'n', f'{t}_{CHAIN}', 'r', 'n', 'hub')
            # a read interleaved with other threads' writes must not error or corrupt
            assert idx.check_reachable('r', 'n', f'{t}_0', 'r', 'n', f'{t}_1')

    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        list(ex.map(work, range(THREADS)))

    with Session(engine) as sess:
        idx = ReachabilityIndex(sess, 'c')
        # every thread's chain head reaches the shared hub (no lost writes)
        for t in range(THREADS):
            assert idx.check_reachable('r', 'n', f'{t}_0', 'r', 'n', 'hub'), f'thread {t} head lost'
            assert idx.check_reachable('r', 'n', f'{t}_7', 'r', 'n', 'hub'), f'thread {t} mid lost'
        # cross-thread isolation: distinct chains never bleed into each other
        assert not idx.check_reachable('r', 'n', '0_5', 'r', 'n', '1_5')
    engine.dispose()


def test_concurrent_reads_are_consistent(tmp_path):
    """Many concurrent readers over a fixed graph all agree (reads take no locks)."""
    engine = _file_engine(tmp_path / 'reads.db')
    with Session(engine) as s:
        s.add(Store(id='r'))
        s.commit()
    with Session(engine) as sess:
        idx = ReachabilityIndex(sess, 'r')
        for i in range(20):
            idx.add_edge('r', 'n', f'a{i}', 'r', 'n', f'a{i + 1}')
        sess.commit()

    def reader(_):
        with Session(engine) as sess:
            idx = ReachabilityIndex(sess, 'r')
            return (idx.check_reachable('r', 'n', 'a0', 'r', 'n', 'a20'),
                    idx.check_reachable('r', 'n', 'a0', 'r', 'n', 'a5'),
                    idx.check_reachable('r', 'n', 'a10', 'r', 'n', 'a3'))

    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(reader, range(40)))
    assert all(r == (True, True, False) for r in results)
    engine.dispose()
