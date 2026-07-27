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

Set ``ZANZIBAR_TEST_DSN`` and the multi-writer tests re-run against a real server
(``tests/dbengine.shared_engine``) -- the only place ``_lock_source`` /
``_lock_store`` actually emit ``FOR UPDATE``. Two tests stay SQLite-only, for two
DIFFERENT reasons, and the distinction matters:

  * ``test_token_not_visible_in_pinned_snapshot_raises`` -- MECHANISM. A pinned read
    snapshot is what makes StaleRead observable; PostgreSQL READ COMMITTED (which
    ``assert_read_isolation`` requires) has none, so the path is unreachable there.
  * ``test_reader_session_sees_consistent_snapshots`` -- GUARANTEE. The property is
    genuinely FALSE on PostgreSQL, verified. Read its docstring; it is the more
    interesting of the two.
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
from tests.dbengine import rdbms_dsn, shared_engine
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


#: The WAL file-backed engine this module used to build inline now lives in
#: ``tests/dbengine`` (byte-identical), so ``ZANZIBAR_TEST_DSN`` can swap in a real
#: server without changing SQLite behaviour at all.
_file_engine = shared_engine

#: Tests whose SUBJECT is a pinned read snapshot -- see the identical note in
#: tests/test_connectedstore_multi_instance.py. SQLite WAL pins a reader's snapshot
#: for the whole transaction; PostgreSQL READ COMMITTED (which
#: ``assert_read_isolation`` REQUIRES) re-snapshots per statement, so a committed row
#: is never hidden from a catch-up and the StaleRead refusal cannot fire. The
#: property under test does not exist on that bind -- this is not a divergence.
sqlite_only_pinned_snapshot = pytest.mark.skipif(
    rdbms_dsn() is not None,
    reason='pins SQLite-WAL pinned-snapshot semantics; PostgreSQL READ COMMITTED '
           're-snapshots per statement so the StaleRead path is unreachable there')


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
    engine = _file_engine(tmp_path, 'cs.db')
    with Session(engine) as boot:
        ConnectedStore(boot, 's', schema=_SCHEMA)      # bootstrap schema + store rows
        boot.commit()

    ops_a = [('add', ('...', 'user', '*', 'public', 'doc', 'd1')),
             ('add', ('...', 'user', 'u1', 'blocked', 'doc', 'd1')),
             ('add', ('...', 'user', 'u1', 'editor', 'doc', 'd2'))]
    ops_b = [('add', ('...', 'user', 'u2', 'editor', 'doc', 'd1')),
             ('add', ('...', 'user', 'u3', 'blocked', 'doc', 'd1')),
             ('add', ('...', 'user', '*', 'public', 'doc', 'd2'))]

    # Instances are opened HERE, before the first write, rather than inside each
    # worker. Opening one CONCURRENTLY with another writer's commit is a genuine
    # PostgreSQL defect -- ``TupleSource.__init__`` reads its watermark and then
    # rebuilds its evaluator in two statements, which READ COMMITTED does not make
    # atomic, so the instance is born with an evaluator ahead of its watermark and the
    # next catch-up raises. That is pinned on its own by
    # ``tests/test_postgres_ha.py::test_open_instance_races_a_concurrent_commit``;
    # leaving the open inside the thread only made THIS test intermittently red for a
    # reason unrelated to what it asserts (observed ~1 run in 20 on the server leg).
    # No behaviour change on SQLite, where the constructor's two reads share one
    # pinned snapshot and the race cannot occur.
    sessions = [Session(engine) for _ in range(2)]
    stores = [ConnectedStore(s, 's') for s in sessions]

    def worker(cs, ops, errors):
        try:
            for op, raw in ops:
                assert _write_retry(cs, op, raw)
        except Exception as e:                          # pragma: no cover
            errors.append(e)

    errors: list = []
    threads = [threading.Thread(target=worker, args=(cs, ops, errors))
               for cs, ops in zip(stores, (ops_a, ops_b))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for s in sessions:
        s.close()
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


@pytest.mark.skipif(
    rdbms_dsn() is not None,
    reason='the guarantee under test is SQLite-WAL-specific and is FALSE on '
           'PostgreSQL READ COMMITTED (verified: this test fails there). It is not '
           'a mechanism difference like sqlite_only_pinned_snapshot -- it is a '
           'GUARANTEE the repo silently inherits from SQLite. See '
           'tests/test_postgres_ha.py::test_read_committed_gives_a_reader_no_stable_'
           'snapshot for the deterministic demonstration, and the note in this '
           'test\'s docstring.')
def test_reader_session_sees_consistent_snapshots(tmp_path):
    """The replica pattern: a reader session polling a store another session writes
    to must see internally-consistent committed states, never torn ones.

    HOW this holds, and where it stops holding. ``cs.refresh()`` rebuilds the
    in-memory evaluator from ``TupleV1`` and then the loop compares it against the
    graph index, which is read by SEPARATE statements. The two agree only if both
    observe the same committed state -- which is true on SQLite-WAL, where a
    transaction pins one snapshot from its first statement, and FALSE on PostgreSQL
    READ COMMITTED, where every statement re-snapshots. Run against a real server
    this test fails within a few polls (observed: a ``viewer`` query where the
    evaluator predates a commit the index has already applied). The system does not
    lose an invariant -- a concurrent structural sweep of the index found no
    violation in 42 passes -- but "a replica reader never observes torn state" is
    a guarantee this repo has been getting for free from SQLite, and does not have
    on its target dialect."""
    engine = _file_engine(tmp_path, 'replica.db')
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
    engine = _file_engine(tmp_path, 'lag.db')
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


def test_token_fallback_rebuilds_stale_evaluator(tmp_path):
    """The cross-session token contract: a write committed AFTER the reader opened
    must still be honored by a token-carrying read -- the reader's in-memory
    evaluator rebuilds on demand instead of serving its stale cache."""
    from connectedstore import StaleRead

    engine = _file_engine(tmp_path, 'token.db')
    with Session(engine) as boot:
        ConnectedStore(boot, 's', schema=_SCHEMA, sync=False)
        boot.commit()

    with Session(engine) as w_session, Session(engine) as r_session:
        writer = ConnectedStore(w_session, 's')
        writer.sync = False
        reader = ConnectedStore(r_session, 's')        # opens BEFORE the write

        token = writer.add_tuple('...', 'user', '*', 'public', 'doc', 'd1')

        # release the reader's snapshot only -- deliberately NOT refresh(): the
        # in-memory evaluator stays stale, and the tokened read itself must detect
        # that (evaluator watermark < token), rebuild, and answer fresh. This is
        # the case a trusted-stale cache used to get wrong.
        r_session.rollback()
        q = ('...', 'user', 'ghost', 'viewer', 'doc', 'd1')
        assert reader.source.evaluator_watermark < token
        assert reader.check(*q, at_least=token) is True
        # and the un-tokened read still serves the (lagging) index consistently
        assert reader.check(*q) is False


@sqlite_only_pinned_snapshot
def test_token_not_visible_in_pinned_snapshot_raises(tmp_path):
    """If the reader is pinned in a snapshot that predates the write, a tokened read
    must refuse loudly (StaleRead), never silently serve stale under an explicit
    freshness demand; refresh() + retry succeeds."""
    from connectedstore import StaleRead

    engine = _file_engine(tmp_path, 'pinned.db')
    with Session(engine) as boot:
        ConnectedStore(boot, 's', schema=_SCHEMA, sync=False)
        boot.commit()

    with Session(engine) as w_session, Session(engine) as r_session:
        writer = ConnectedStore(w_session, 's')
        writer.sync = False
        reader = ConnectedStore(r_session, 's')
        q = ('...', 'user', 'ghost', 'viewer', 'doc', 'd1')
        reader.check(*q)                    # pin a WAL read snapshot NOW

        token = writer.add_tuple('...', 'user', '*', 'public', 'doc', 'd1')

        with pytest.raises(StaleRead, match='refresh'):
            reader.check(*q, at_least=token)

        reader.refresh()                    # fresh snapshot + caches
        assert reader.check(*q, at_least=token) is True
