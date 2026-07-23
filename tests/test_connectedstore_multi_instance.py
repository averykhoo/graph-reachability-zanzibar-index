"""
Multi-instance set-engine support: several TupleSource / ConnectedStore instances
(one Session each) share ONE store in ONE database; each instance's set engine is
in-memory-local, kept coherent via the TupleLogV1 log.

The honest local simulation of "read replicas over a shared primary" is file-backed
SQLite in WAL mode (snapshot-isolated readers that never block the writer) -- the
same fixture pattern as tests/test_connectedstore_concurrency.py. One Session per
instance, never shared.

Covers the just-landed APIs:
  * SetEngine.apply_logged / result_keys
  * TupleSource.catch_up_evaluator / evaluator_lag / check(at_least=)
  * the add/remove critical section (_lock_source -> catch_up_evaluator -> _append)
  * StaleRead re-export + the pinned-snapshot / bogus-token refusal
  * ConnectedStore.check tail fallback under concurrent multi-instance writers

The oracle (tests/oracle.py) is the independent ground truth -- it imports nothing
from either backend and parses the DSL itself.
"""

import threading
import time

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlmodel import Session, SQLModel, create_engine, select

from connectedstore import (ConnectedStore, StaleRead, TupleSource,
                            log_rows, log_watermark)
from setengine import SetEngine, TupleV1
from tests.oracle import Oracle, OracleTuple

# One schema for the whole file: a recursive-userset `group` (for the cross-instance
# cycle-rejection headline) plus a boolean `doc` (for the read grid).
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

# Small deterministic query grid (5 subjects x 4 relations x 2 objects).
GRID = [('...', 'user', sn, rel, 'doc', on)
        for sn in ('u1', 'u2', 'u3', 'ghost', '*')
        for rel in ('viewer', 'editor', 'public', 'blocked')
        for on in ('d1', 'd2')]


# --------------------------------------------------------------------------- #
# WAL file-backed engine (copied from tests/test_connectedstore_concurrency.py:45)
# --------------------------------------------------------------------------- #

def _file_engine(path):
    engine = create_engine(f'sqlite:///{path}',
                           connect_args={'check_same_thread': False, 'timeout': 60})

    @event.listens_for(engine, 'connect')
    def _busy_timeout(dbapi, _rec):
        cur = dbapi.cursor()
        cur.execute('PRAGMA busy_timeout=60000')
        # WAL: snapshot-isolated readers that never block the writer -- the honest
        # local simulation of a replica reading a store the primary writes.
        cur.execute('PRAGMA journal_mode=WAL')
        cur.close()
        # real transaction semantics (SQLAlchemy pysqlite workaround): let SQLAlchemy
        # emit BEGIN itself so a snapshot doesn't tear between statements.
        dbapi.isolation_level = None

    @event.listens_for(engine, 'begin')
    def _begin(conn):
        conn.exec_driver_sql('BEGIN')

    SQLModel.metadata.create_all(engine)
    return engine


def _bootstrap(path):
    """Bootstrap the store (schema + store + cursor rows) once via ConnectedStore,
    then return the shared WAL engine for per-instance sessions to open against."""
    engine = _file_engine(path)
    with Session(engine) as boot:
        ConnectedStore(boot, 's', schema=SCHEMA)   # commits its own bootstrap rows
        boot.commit()
    return engine


def _oracle(present):
    return Oracle(SCHEMA, [OracleTuple(*r) for r in present])


def _assert_grid(instance, oracle, other=None):
    for q in GRID:
        exp = oracle.check(*q)
        assert instance.check(*q) == exp, q
        if other is not None:
            assert other.check(*q) == exp, q


# --------------------------------------------------------------------------- #
# 1. Tail parity: B tails A's committed writes O(delta) and agrees everywhere.
# --------------------------------------------------------------------------- #

def test_tail_parity(tmp_path):
    engine = _bootstrap(tmp_path / 'tail.db')
    with Session(engine) as sa, Session(engine) as sb:
        a = TupleSource(sa, 's')
        b = TupleSource(sb, 's')            # opened BEFORE A's writes: watermark 0

        present = [('...', 'user', '*', 'public', 'doc', 'd1'),
                   ('...', 'user', 'u1', 'blocked', 'doc', 'd1'),
                   ('...', 'user', 'u1', 'editor', 'doc', 'd2'),
                   ('...', 'user', 'u2', 'editor', 'doc', 'd1')]
        for raw in present:
            a.add(*raw)
            sa.commit()

        sb.rollback()                        # advance B's WAL read snapshot
        applied = b.catch_up_evaluator()     # tail the delta into B's evaluator
        assert applied == len(present)
        assert b.evaluator_lag() == 0

        _assert_grid(b, _oracle(present), other=a)


# --------------------------------------------------------------------------- #
# 2. Cross-instance read-your-writes: a tokened read on a stale evaluator catches
#    up on demand (no manual catch-up) and answers fresh.
# --------------------------------------------------------------------------- #

def test_cross_instance_token_read(tmp_path):
    engine = _bootstrap(tmp_path / 'token.db')
    with Session(engine) as sa, Session(engine) as sb:
        a = TupleSource(sa, 's')
        b = TupleSource(sb, 's')            # opened before the write

        token = a.add('...', 'user', 'u1', 'editor', 'doc', 'd1')
        sa.commit()

        # release B's stale construction snapshot (NOT refresh_evaluator: the
        # in-memory evaluator stays behind) -- the tokened read itself must catch up.
        sb.rollback()
        assert b.evaluator_watermark < token
        q = ('...', 'user', 'u1', 'viewer', 'doc', 'd1')
        assert b.check(*q, at_least=token) is True
        assert b.evaluator_watermark >= token


# --------------------------------------------------------------------------- #
# 3. StaleRead: a pinned snapshot predating the write refuses loudly; a bogus
#    future token refuses without hanging.
# --------------------------------------------------------------------------- #

def test_stale_read_pinned_snapshot(tmp_path):
    engine = _bootstrap(tmp_path / 'pinned.db')
    with Session(engine) as sa, Session(engine) as sb:
        a = TupleSource(sa, 's')
        b = TupleSource(sb, 's')

        q = ('...', 'user', 'u1', 'viewer', 'doc', 'd1')
        b.check(*q)                          # pin B's WAL snapshot NOW (pre-write)

        token = a.add('...', 'user', 'u1', 'editor', 'doc', 'd1')
        sa.commit()

        # B's snapshot predates the commit: catch-up can find nothing -> refuse.
        with pytest.raises(StaleRead):
            b.check(*q, at_least=token)

        sb.rollback()                        # fresh snapshot; same call now succeeds
        assert b.check(*q, at_least=token) is True


def test_stale_read_bogus_future_token(tmp_path):
    engine = _bootstrap(tmp_path / 'bogus.db')
    with Session(engine) as sa, Session(engine) as sb:
        a = TupleSource(sa, 's')
        a.add('...', 'user', 'u1', 'editor', 'doc', 'd1')
        sa.commit()

        b = TupleSource(sb, 's')             # fully caught up at construction
        head = log_watermark(sb, 's')
        # a token 1000 past the head is never visible: refuse, don't loop forever.
        with pytest.raises(StaleRead):
            b.check('...', 'user', 'u1', 'viewer', 'doc', 'd1', at_least=head + 1000)


# --------------------------------------------------------------------------- #
# 4. Cross-instance cycle rejection: the headline admission fix. The write's
#    internal catch-up (under the lock) sees the other instance's committed row,
#    so the flow-graph cycle check fires -- the store cannot be corrupted.
# --------------------------------------------------------------------------- #

def test_cross_instance_cycle_rejection(tmp_path):
    engine = _bootstrap(tmp_path / 'cycle.db')
    with Session(engine) as sa, Session(engine) as sb:
        a = TupleSource(sa, 's')
        b = TupleSource(sb, 's')            # in-memory evaluator predates A's write

        a.add('member', 'group', 'a', 'member', 'group', 'b')
        sa.commit()

        # Mirror a between-ops session: release B's stale construction snapshot so
        # the next write takes a fresh snapshot (the SQLite stand-in for the
        # Postgres FOR-UPDATE + read-committed catch-up). Crucially NOT
        # refresh_evaluator: B's evaluator is still empty -- only the catch-up
        # INSIDE add() can see a#member->b and reject the closing edge.
        sb.rollback()
        assert b.evaluator_watermark == 0
        with pytest.raises(ValueError):
            b.add('member', 'group', 'b', 'member', 'group', 'a')
        sb.rollback()

        # Exactly one row landed (A's), no corruption from a blind second write.
        assert len(log_rows(sa, 's')) == 1


# --------------------------------------------------------------------------- #
# 5. Cross-instance duplicate add: idempotent no-op (no log row, no IntegrityError).
# --------------------------------------------------------------------------- #

def test_cross_instance_duplicate_add(tmp_path):
    engine = _bootstrap(tmp_path / 'dup.db')
    with Session(engine) as sa, Session(engine) as sb:
        a = TupleSource(sa, 's')
        b = TupleSource(sb, 's')

        t = ('...', 'user', 'u1', 'editor', 'doc', 'd1')
        token = a.add(*t)
        sa.commit()
        before = len(log_rows(sa, 's'))

        sb.rollback()                        # fresh snapshot for B's catch-up
        dup_token = b.add(*t)                # catch-up makes it present -> no-op
        sb.commit()

        assert dup_token == token            # current watermark, not a new token
        assert len(log_rows(sa, 's')) == before   # no log row appended


# --------------------------------------------------------------------------- #
# 6. Cross-instance remove of a tuple this instance never saw: catch-up makes it
#    present, so the remove succeeds.
# --------------------------------------------------------------------------- #

def test_cross_instance_remove_unseen(tmp_path):
    engine = _bootstrap(tmp_path / 'rmunseen.db')
    with Session(engine) as sa, Session(engine) as sb:
        a = TupleSource(sa, 's')
        b = TupleSource(sb, 's')

        t = ('...', 'user', 'u1', 'editor', 'doc', 'd1')
        a.add(*t)
        sa.commit()

        sb.rollback()
        b.remove(*t)                         # catch-up applies A's add, then removes
        sb.commit()

        # the tuple is retired end to end: B's evaluator and a fresh reader agree
        # with an empty-store oracle.
        _assert_grid(b, _oracle([]))
        sa.rollback()
        remaining = {(r.subject_predicate, r.subject_type, r.subject_name,
                      r.relation, r.object_type, r.object_name)
                     for r in sa.exec(select(TupleV1)
                                      .where(TupleV1.store_id == 's')).all()}
        assert t not in remaining


# --------------------------------------------------------------------------- #
# 7. Rejection leaves the caught-up evaluator truthful: the catch-up rows applied
#    under the (rejected) write were committed by A, so a plain rollback (the
#    ConnectedStore rejection path -- no refresh_evaluator) discards nothing they
#    depend on.
# --------------------------------------------------------------------------- #

def test_rejection_leaves_evaluator_truthful(tmp_path):
    engine = _bootstrap(tmp_path / 'reject.db')
    with Session(engine) as sa, Session(engine) as sb:
        a = TupleSource(sa, 's')
        b = TupleSource(sb, 's')

        present = [('...', 'user', 'u1', 'editor', 'doc', 'd1'),
                   ('...', 'user', 'u2', 'blocked', 'doc', 'd2'),
                   ('...', 'user', '*', 'public', 'doc', 'd2')]
        for raw in present:
            a.add(*raw)
            sa.commit()

        sb.rollback()                        # fresh snapshot for B's catch-up
        # invalid write: relation matches no declared type restriction -> ValueError,
        # AFTER the internal catch-up has already applied A's committed rows in memory.
        with pytest.raises(ValueError):
            b.add('...', 'martian', 'zork', 'viewer', 'doc', 'd1')
        sb.rollback()                        # ConnectedStore's rejection path

        _assert_grid(b, _oracle(present))


# --------------------------------------------------------------------------- #
# 8. Crash recovery: a brand-new instance on a fresh Session rebuilds from
#    TupleV1 -- watermark at the log head, lag 0, grid parity with the oracle.
# --------------------------------------------------------------------------- #

def test_crash_recovery_rebuild(tmp_path):
    engine = _bootstrap(tmp_path / 'crash.db')
    live = set()
    with Session(engine) as sa:
        a = TupleSource(sa, 's')
        history = [
            ('add', ('...', 'user', '*', 'public', 'doc', 'd1')),
            ('add', ('...', 'user', 'u1', 'blocked', 'doc', 'd1')),
            ('add', ('...', 'user', 'u1', 'editor', 'doc', 'd2')),
            ('add', ('...', 'user', 'u2', 'editor', 'doc', 'd1')),
            ('remove', ('...', 'user', 'u1', 'blocked', 'doc', 'd1')),
            ('add', ('...', 'user', 'u3', 'editor', 'doc', 'd2')),
            ('remove', ('...', 'user', 'u2', 'editor', 'doc', 'd1')),
        ]
        for op, raw in history:
            (a.add if op == 'add' else a.remove)(*raw)
            sa.commit()
            live.add(raw) if op == 'add' else live.discard(raw)

    # simulated restart: brand-new Session, brand-new instance
    with Session(engine) as sc:
        c = TupleSource(sc, 's')
        assert c.evaluator_watermark == log_watermark(sc, 's')
        assert c.evaluator_lag() == 0
        _assert_grid(c, _oracle(sorted(live)))


# --------------------------------------------------------------------------- #
# 9. apply_logged corruption guards (direct unit; in-memory SQLite is fine).
# --------------------------------------------------------------------------- #

def test_apply_logged_corruption_guards():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        eng = SetEngine(session, 's', SCHEMA)
        eng.add_tuple('...', 'user', 'u1', 'blocked', 'doc', 'd1')

        # ADD of an already-present tuple: watermark corruption -> hard failure
        with pytest.raises(RuntimeError):
            eng.apply_logged('ADD', '...', 'user', 'u1', 'blocked', 'doc', 'd1')
        # REMOVE of an absent tuple
        with pytest.raises(RuntimeError):
            eng.apply_logged('REMOVE', '...', 'user', 'ghost', 'blocked', 'doc', 'd1')
        # unknown op (the log carries only ADD/REMOVE)
        with pytest.raises(RuntimeError):
            eng.apply_logged('MUTATE', '...', 'user', 'u1', 'blocked', 'doc', 'd1')


# --------------------------------------------------------------------------- #
# 10. result_keys portability: instance-local recycled interner ids differ, but
#     the portable surrogate keys agree across a rebuilt instance.
# --------------------------------------------------------------------------- #

def test_result_keys_portability():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        a = SetEngine(session, 's', SCHEMA)
        # churn so the interner recycles ids: add several, remove some, add more.
        a.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
        a.add_tuple('...', 'user', 'u2', 'editor', 'doc', 'd1')
        a.add_tuple('...', 'user', 'u3', 'editor', 'doc', 'd2')
        a.remove_tuple('...', 'user', 'u2', 'editor', 'doc', 'd1')   # frees ids
        a.add_tuple('member', 'group', 'g1', 'member', 'group', 'g2')
        a.remove_tuple('member', 'group', 'g1', 'member', 'group', 'g2')
        a.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd2')
        a.add_tuple('...', 'user', 'u1', 'blocked', 'doc', 'd1')
        a.add_tuple('...', 'user', 'u1', 'member', 'group', 'g1')
        session.flush()

        # fresh instance rebuilds from the final TupleV1 -> different id assignment
        b = SetEngine(session, 's', SCHEMA)

        a_res = a.lookup('...', 'user', 'u1')
        b_res = b.lookup('...', 'user', 'u1')
        assert a_res.node_ids                       # non-empty (u1 reaches things)
        assert a.result_keys(a_res) == b.result_keys(b_res)
        assert a_res.markers == b_res.markers


# --------------------------------------------------------------------------- #
# 11. Write-path discipline pin: lock -> catch_up -> append, in that order.
# --------------------------------------------------------------------------- #

def test_write_path_ordering(tmp_path, monkeypatch):
    engine = _bootstrap(tmp_path / 'order.db')
    with Session(engine) as sa:
        src = TupleSource(sa, 's')
        calls: list[str] = []
        orig_lock = src._lock_source
        orig_catch = src.catch_up_evaluator
        orig_append = src._append

        def spy_lock():
            calls.append('lock')
            return orig_lock()

        def spy_catch(batch=None):
            calls.append('catch_up')
            return orig_catch(batch)

        def spy_append(*a, **k):
            calls.append('append')
            return orig_append(*a, **k)

        monkeypatch.setattr(src, '_lock_source', spy_lock)
        monkeypatch.setattr(src, 'catch_up_evaluator', spy_catch)
        monkeypatch.setattr(src, '_append', spy_append)

        src.add('...', 'user', 'u1', 'blocked', 'doc', 'd1')
        sa.commit()
        # the critical-section ordering: append lands strictly inside lock+catch-up
        assert calls == ['lock', 'catch_up', 'append']


# --------------------------------------------------------------------------- #
# 12. Concurrent multi-instance writers converge (threads). ConnectedStore
#     handles the SQLITE_BUSY / shared-node retry internally; afterwards every
#     fresh instance catches up and agrees with the single-writer twin + oracle.
# --------------------------------------------------------------------------- #

def _write_retry(cs, op, raw, attempts=300):
    """SQLITE_BUSY and shared-node IntegrityErrors are safe to retry; a ValueError
    is a genuine rejection. ConnectedStore already rolls back + rebuilds its
    evaluator on the retryable errors (see ConnectedStore._write)."""
    fn = cs.add_tuple if op == 'add' else cs.remove_tuple
    for _ in range(attempts):
        try:
            fn(*raw)
            return True
        except ValueError:
            return False
        except (OperationalError, IntegrityError):
            time.sleep(0.005)
    raise RuntimeError(f'gave up committing {op} {raw}')


def test_concurrent_multi_instance_writers_converge(tmp_path):
    engine = _bootstrap(tmp_path / 'converge.db')

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
        except Exception as e:                       # pragma: no cover
            errors.append(e)

    errors: list = []
    threads = [threading.Thread(target=worker, args=(ops, errors))
               for ops in (ops_a, ops_b)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors

    present = [raw for _, raw in ops_a + ops_b]
    oracle = _oracle(present)

    with Session(engine) as session:
        # a single-writer twin over the same accepted writes reaches the same answers
        twin = ConnectedStore(session, 'twin', schema=SCHEMA)
        for op, raw in ops_a + ops_b:
            _write_retry(twin, op, raw)
        cs = ConnectedStore(session, 's')
        for q in GRID:
            exp = oracle.check(*q)
            assert cs.check(*q) == exp, q
            assert twin.check(*q) == exp, q

    # every fresh multi-instance evaluator catches up and agrees with the oracle
    for db in ('mi1.db', 'mi2.db'):
        with Session(engine) as si:
            inst = TupleSource(si, 's')
            assert inst.evaluator_lag() == 0
            _assert_grid(inst, oracle)
