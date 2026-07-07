"""
S7 (connected-store spec §5-S7): concurrency + stale-read hardening on file-backed
SQLite (mirrors tests/test_concurrency.py's idioms: busy_timeout + retry on
SQLITE_BUSY / IntegrityError; one Session per thread, never shared).

  * concurrent ConnectedStore writers on the SAME store converge to a consistent
    state equal to a single-writer twin over the union of their accepted writes;
  * a separate reader session ("the replica"): sees only consistent committed
    snapshots mid-stream (index answers ≡ its own set-engine evaluator after
    rebuild), never torn state;
  * async schedule under a lagging index: the reader's un-tokened answers are stale
    but internally consistent; after the worker catches up, they converge.
"""

import random
import threading
import time

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlmodel import Session, SQLModel, create_engine

from connectedstore import ConnectedStore
from index_v4.invariants import snapshot_rows
from tests.oracle import Oracle, OracleTuple
from tests.wildcard_helpers import assert_wildcard_invariants

_SCHEMA = '''
type user
type doc
  relations
    define public: [user:*]
    define blocked: [user]
    define editor: [user]
    define viewer: (public but not blocked) or editor
'''

_GRID = [('...', 'user', sn, rel, 'doc', on)
         for sn in ('u1', 'u2', 'u3', 'ghost', '*')
         for rel in ('viewer', 'editor', 'public', 'blocked')
         for on in ('d1', 'd2')]


def _file_engine(path):
    engine = create_engine(f'sqlite:///{path}',
                           connect_args={'check_same_thread': False, 'timeout': 60})

    @event.listens_for(engine, 'connect')
    def _busy_timeout(dbapi, _rec):
        cur = dbapi.cursor()
        cur.execute('PRAGMA busy_timeout=60000')
        # WAL: snapshot-isolated readers that never block the writer -- the honest
        # local simulation of "consistent reads from a secondary while the primary
        # writes" (rollback-journal readers would block writers instead).
        cur.execute('PRAGMA journal_mode=WAL')
        cur.close()
        # real transaction semantics (the SQLAlchemy-documented pysqlite workaround):
        # by default pysqlite runs SELECTs in autocommit, so a "snapshot" would tear
        # between statements. Let SQLAlchemy emit BEGIN itself instead.
        dbapi.isolation_level = None

    @event.listens_for(engine, 'begin')
    def _begin(conn):
        conn.exec_driver_sql('BEGIN')

    SQLModel.metadata.create_all(engine)
    return engine


def _write_retry(cs, op, raw, attempts=300):
    """SQLITE_BUSY and shared-node IntegrityErrors are safe to retry; a ValueError
    is a genuine rejection (validity), not contention."""
    fn = cs.add_tuple if op == 'add' else cs.remove_tuple
    for _ in range(attempts):
        try:
            fn(*raw)
            return True
        except ValueError:
            return False
        except (OperationalError, IntegrityError):
            # ConnectedStore already rolled back + rebuilt its evaluator
            time.sleep(0.005)
    raise RuntimeError(f'gave up committing {op} {raw}')


def test_concurrent_writers_converge(tmp_path):
    engine = _file_engine(tmp_path / 'cs.db')
    with Session(engine) as boot:
        ConnectedStore(boot, 's', schema=_SCHEMA)      # bootstrap schema + store rows
        boot.commit()

    ops_a = [('add', ('...', 'user', '*', 'public', 'doc', 'd1')),
             ('add', ('...', 'user', 'u1', 'blocked', 'doc', 'd1')),
             ('add', ('...', 'user', 'u1', 'editor', 'doc', 'd2'))]
    ops_b = [('add', ('...', 'user', 'u2', 'editor', 'doc', 'd1')),
             ('add', ('...', 'user', 'u3', 'blocked', 'doc', 'd1')),
             ('add', ('...', 'user', '*', 'public', 'doc', 'd2'))]

    def worker(ops, errors):
        try:
            with Session(engine) as session:
                cs = ConnectedStore(session, 's')
                for op, raw in ops:
                    assert _write_retry(cs, op, raw)
        except Exception as e:                          # pragma: no cover
            errors.append(e)

    errors: list = []
    threads = [threading.Thread(target=worker, args=(ops, errors))
               for ops in (ops_a, ops_b)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors

    # a single-writer twin over the same accepted writes reaches the same state
    with Session(engine) as session:
        twin = ConnectedStore(session, 'twin', schema=_SCHEMA)
        for op, raw in ops_a + ops_b:
            _write_retry(twin, op, raw)

        cs = ConnectedStore(session, 's')
        assert_wildcard_invariants(cs.widx)
        if cs.proc is not None:
            cs.proc.audit_fixpoint()
        assert snapshot_rows(session, 's') == snapshot_rows(session, 'twin')

        present = ops_a + ops_b
        oracle = Oracle(_SCHEMA, [OracleTuple(*raw) for _, raw in present])
        for q in _GRID:
            assert cs.check(*q) == oracle.check(*q), q


def test_reader_session_sees_consistent_snapshots(tmp_path):
    """The replica pattern: a reader session polling a store another session writes
    to must see internally-consistent committed states, never torn ones."""
    engine = _file_engine(tmp_path / 'replica.db')
    with Session(engine) as boot:
        ConnectedStore(boot, 's', schema=_SCHEMA)
        boot.commit()

    stop = threading.Event()
    torn: list = []

    def reader():
        with Session(engine) as session:
            cs = ConnectedStore(session, 's')
            while not stop.is_set():
                cs.refresh()                           # fresh snapshot + caches per poll
                for q in _GRID[:12]:
                    if cs.check(*q) != cs.source.check(*q):
                        torn.append(q)                 # index vs truth disagree = torn
                        return
                time.sleep(0.001)

    t = threading.Thread(target=reader)
    t.start()
    try:
        with Session(engine) as session:
            cs = ConnectedStore(session, 's')
            rng = random.Random(0)
            pool = [('...', 'user', f'u{i}', rel, 'doc', d)
                    for i in (1, 2, 3) for rel in ('blocked', 'editor') for d in ('d1', 'd2')]
            pool += [('...', 'user', '*', 'public', 'doc', d) for d in ('d1', 'd2')]
            live = set()
            for _ in range(30):
                if live and rng.random() < 0.4:
                    raw = rng.choice(sorted(live))
                    if _write_retry(cs, 'remove', raw):
                        live.discard(raw)
                else:
                    raw = rng.choice(pool)
                    if raw not in live and _write_retry(cs, 'add', raw):
                        live.add(raw)
    finally:
        stop.set()
        t.join()

    assert not torn, f'reader observed torn state on {torn[0]}'


def test_replica_reads_under_async_lag(tmp_path):
    """Async schedule: a reader mid-lag serves stale-but-consistent answers from the
    index; token-carrying reads fall back fresh; after catch-up everything agrees."""
    engine = _file_engine(tmp_path / 'lag.db')
    with Session(engine) as boot:
        ConnectedStore(boot, 's', schema=_SCHEMA, sync=False)
        boot.commit()

    with Session(engine) as w_session, Session(engine) as r_session:
        writer = ConnectedStore(w_session, 's')
        writer.sync = False
        token = writer.add_tuple('...', 'user', '*', 'public', 'doc', 'd1')

        reader = ConnectedStore(r_session, 's')
        q = ('...', 'user', 'ghost', 'viewer', 'doc', 'd1')
        assert reader.check(*q) is False                       # stale index, consistent
        assert reader.check(*q, at_least=token) is True        # fresh fallback

        writer.catch_up()
        r_session.rollback()                                   # fresh snapshot
        assert reader.check(*q) is True                        # converged
        assert reader.check(*q, at_least=token) is True
