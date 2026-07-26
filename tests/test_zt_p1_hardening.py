"""Zero-trust review 2026-07-26, P1 operational-envelope hardening: ZT-P1-4/5/6.

Three unrelated failure modes, one file (they are all "the envelope around a correct
evaluator"), each pinned in two directions -- the fix works, AND the failure it fixes is
actually detected:

* **ZT-P1-6 (read DoS)** -- a deep userset chain is accepted by the (iterative) write
  path and then made EVERY read on that subgraph raise ``RecursionError``, permanently;
  ``lookup`` worst of all since it sweeps every declared ``(type, relation)``.
  ``check``/``expand`` now run on a heap stack (``setengine.engine._drive``), so the
  answers are the ORACLE's at depths far past ``sys.getrecursionlimit()``. NOTE: no
  admission cap was added -- nothing that used to be accepted is now rejected.
* **ZT-P1-4 (no-op locks)** -- ``with_for_update()`` compiles to a plain SELECT on
  SQLite, so both documented per-store write locks were silent no-ops. They now take a
  real write lock, and a session configured so that no lock can hold is refused at
  ``ConnectedStore`` construction.
* **ZT-P1-5 (unguarded watermarks)** -- the evaluator watermark and the index cursor
  jumped to the newest id they had seen, assuming the preceding catch-up was complete.
  Under a pinned read snapshot it is not, and the skipped rows are lost FOREVER while
  ``at_least`` keeps certifying the stale answers. Both advances are now
  contiguity-checked and raise ``WatermarkGap``.

The oracle (``tests/oracle.py``) is the independent ground truth throughout.
"""

import sys
import threading

import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine, select

import connectedstore.apply as apply_mod
import connectedstore.source as source_mod
import index_v4.core as core_mod
from connectedstore import (ConnectedStore, SchemaV4, TupleSource,
                            UnsafeIsolationLevel, WatermarkGap, log_watermark)
from index_v4.core import WriteLockUnsafe, is_sqlite
from setengine import SetEngine
from tests.oracle import Oracle, OracleTuple

# --------------------------------------------------------------------------- #
# Shared fixtures/helpers
# --------------------------------------------------------------------------- #

CHAIN_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define viewer: [user, group#member]
'''

BOOL_SCHEMA = '''
type user
type doc
  relations
    define public: [user:*]
    define blocked: [user]
    define editor: [user]
    define viewer: (public but not blocked) or editor
'''


def _mem_engine():
    engine = create_engine('sqlite://')       # pysqlite DEFAULT config (isolation_level='')
    SQLModel.metadata.create_all(engine)
    return engine


def _file_engine(path, *, recipe=True):
    """File-backed WAL engine. ``recipe=True`` applies the documented pysqlite
    transaction recipe (isolation_level=None + an explicit BEGIN); ``False`` leaves
    pysqlite's default in place. Both are SAFE configurations."""
    engine = create_engine(f'sqlite:///{path}',
                           connect_args={'check_same_thread': False, 'timeout': 60})

    @event.listens_for(engine, 'connect')
    def _pragmas(dbapi, _rec):
        cur = dbapi.cursor()
        cur.execute('PRAGMA busy_timeout=60000')
        cur.execute('PRAGMA journal_mode=WAL')
        cur.close()
        if recipe:
            dbapi.isolation_level = None

    if recipe:
        @event.listens_for(engine, 'begin')
        def _begin(conn):
            conn.exec_driver_sql('BEGIN')

    SQLModel.metadata.create_all(engine)
    return engine


def _deep_chain_tuples(n):
    """``user:deep`` -> ``group:g{n-1}#member`` -> ... -> ``group:g0#member`` ->
    ``doc:d1#viewer``: one raw tuple per link, ``n`` links of userset recursion."""
    out = [('member', 'group', f'g{i + 1}', 'member', 'group', f'g{i}')
           for i in range(n - 1)]
    out.append(('...', 'user', 'deep', 'member', 'group', f'g{n - 1}'))
    out.append(('member', 'group', 'g0', 'viewer', 'doc', 'd1'))
    return out


def _oracle_answers(tuples, queries, depth_budget=200_000):
    """Reference answers from the independent oracle.

    The oracle is itself a plain recursion (``tests/oracle.py`` sat), so at these
    depths IT needs a raised recursion limit and a fat stack -- which is precisely the
    point of this test: the set engine no longer does. Run in a throwaway thread so the
    process-wide limit and the big stack die with it."""
    oracle = Oracle(CHAIN_SCHEMA, [OracleTuple(*t) for t in tuples])
    out, err = {}, []
    old_limit = sys.getrecursionlimit()

    def run():
        try:
            sys.setrecursionlimit(depth_budget)
            for q in queries:
                out[q] = oracle.check(*q)
        except BaseException as exc:                        # pragma: no cover
            err.append(exc)

    old_stack = threading.stack_size(128 * 1024 * 1024)
    try:
        t = threading.Thread(target=run)
        t.start()
        t.join()
    finally:
        threading.stack_size(old_stack)
        sys.setrecursionlimit(old_limit)
    if err:                                                 # pragma: no cover
        raise err[0]
    return out


# =========================================================================== #
# ZT-P1-6 -- the permanent read DoS on a deep userset chain
# =========================================================================== #

def test_deep_chain_check_expand_lookup_match_oracle():
    """2,000 links of ``group#member``: check / expand / lookup_reverse all answer, and
    answer what the ORACLE says. Before the heap-stack conversion every one of these
    raised ``RecursionError`` -- forever, for every reader of the subgraph."""
    n = 2000
    tuples = _deep_chain_tuples(n)
    assert n > sys.getrecursionlimit(), 'the chain must out-depth the recursion limit'

    with Session(_mem_engine()) as s:
        eng = SetEngine(s, 'deep', schema=CHAIN_SCHEMA)
        for t in tuples:
            assert eng.add_tuple(*t)                # the write path accepts it (no cap)

        queries = [('...', 'user', 'deep', 'viewer', 'doc', 'd1'),      # True via 2000 hops
                   ('...', 'user', 'ghost', 'viewer', 'doc', 'd1'),     # False
                   ('member', 'group', f'g{n - 1}', 'viewer', 'doc', 'd1'),
                   ('member', 'group', 'g0', 'viewer', 'doc', 'd1')]
        expected = _oracle_answers(tuples, queries)
        assert expected[queries[0]] is True and expected[queries[1]] is False
        for q in queries:
            assert eng.check(*q) == expected[q], q

        # expand: every link's userset node plus the deep entity are members of viewer
        members = eng.result_keys(eng.lookup_reverse('viewer', 'doc', 'd1'))
        assert ('user', 'deep', '...') in members
        assert ('group', f'g{n - 1}', 'member') in members
        assert len(members) == n + 1                # n userset nodes + the bare user

        # and the subject's own view of the world (deep chain up the OTHER direction)
        assert eng.check('...', 'user', 'deep', 'member', 'group', 'g0') is True


def test_deep_chain_lookup_matches_oracle():
    """``lookup`` -- the review's worst case (it sweeps every declared shape and
    confirms every candidate with ``check``) -- on a chain deeper than the recursion
    limit. Kept shorter than 2,000 because the walk is inherently O(chain^2) confirmed
    checks; still ~4x the recursion limit."""
    n = 400
    tuples = _deep_chain_tuples(n)
    # 400 links is already past the limit in FRAMES: each link costs several nested
    # evaluator frames (sat -> sat_expr -> direct_leaf -> member_via_usersets -> sat),
    # which is why the oracle below needs a raised limit at this depth.
    with Session(_mem_engine()) as s:
        eng = SetEngine(s, 'deep2', schema=CHAIN_SCHEMA)
        for t in tuples:
            eng.add_tuple(*t)
        got = eng.result_keys(eng.lookup('...', 'user', 'deep'))
        # reference: every (type, name, relation) reachable up the chain
        want = {('doc', 'd1', 'viewer')} | {('group', f'g{i}', 'member') for i in range(n)}
        assert got == want
        # pin the reference against the independent oracle at both extremes, and pin a
        # non-member (the oracle needs a fat stack for this; the engine does not)
        spot = [('...', 'user', 'deep', 'viewer', 'doc', 'd1'),
                ('...', 'user', 'deep', 'member', 'group', 'g0'),
                ('...', 'user', 'ghost', 'member', 'group', 'g0')]
        expected = _oracle_answers(tuples, spot)
        assert list(expected.values()) == [True, True, False]
        for q in spot:
            assert eng.check(*q) == expected[q], q


def test_evaluator_is_depth_independent_not_limit_dependent():
    """The mechanism, isolated: with the interpreter's recursion limit CRUSHED to 60,
    the evaluator still answers over a 300-link chain -- so the depth budget is heap,
    not stack. The control proves the limit is genuinely in force (a plain recursion of
    the same depth dies), i.e. the pre-fix evaluator would have died here too."""
    n = 300
    tuples = _deep_chain_tuples(n)
    with Session(_mem_engine()) as s:
        eng = SetEngine(s, 'deep3', schema=CHAIN_SCHEMA)
        for t in tuples:
            eng.add_tuple(*t)

        def control(k):                 # the shape the evaluator used to have
            return 0 if k == 0 else 1 + control(k - 1)

        old = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(60)
            with pytest.raises(RecursionError):
                control(n)              # the limit really is in force
            assert eng.check('...', 'user', 'deep', 'viewer', 'doc', 'd1') is True
            assert eng.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1') is False
            assert len(eng.lookup_reverse('viewer', 'doc', 'd1').node_ids) == n + 1
        finally:
            sys.setrecursionlimit(old)


CYCLE_SCHEMA = '''
type user
type folder
  relations
    define parent: [folder]
    define blocked: [user]
    define own: [user]
    define viewer: (own but not blocked) or viewer from parent
'''


def test_deep_object_cycle_check_and_expand_match_oracle():
    """DEEP **and** CYCLIC: a 400-long ``parent`` ring (admission allows object-level
    TTU cycles -- the flow graph tracks userset edges, not concrete parent chains). This
    needs the heap stack AND the ``key in stack`` provisional-False cycle answer AND the
    lowlink memo guard to all still work together; a wrong memo here would either hang,
    or memoize a provisional answer and diverge from the oracle."""
    n = 400
    ring = [('...', 'folder', f'f{i}', 'parent', 'folder', f'f{(i + 1) % n}')
            for i in range(n)]
    tuples = ring + [('...', 'user', 'u1', 'own', 'folder', f'f{n // 2}'),
                     ('...', 'user', 'u2', 'own', 'folder', f'f{n // 2}'),
                     ('...', 'user', 'u2', 'blocked', 'folder', f'f{n // 2}')]
    with Session(_mem_engine()) as s:
        eng = SetEngine(s, 'ring', schema=CYCLE_SCHEMA)
        for t in tuples:
            assert eng.add_tuple(*t)                    # the ring IS admitted

        queries = [('...', 'user', 'u1', 'viewer', 'folder', 'f0'),      # via the ring
                   ('...', 'user', 'u2', 'viewer', 'folder', 'f0'),      # own but blocked
                   ('...', 'user', 'u1', 'viewer', 'folder', f'f{n // 2}'),
                   ('...', 'user', 'ghost', 'viewer', 'folder', 'f0')]
        oracle = Oracle(CYCLE_SCHEMA, [OracleTuple(*t) for t in tuples])
        out, err = {}, []

        def run():                                      # the oracle needs the fat stack
            try:
                sys.setrecursionlimit(200_000)
                for q in queries:
                    out[q] = oracle.check(*q)
            except BaseException as exc:                # pragma: no cover
                err.append(exc)

        old_limit, old_stack = sys.getrecursionlimit(), threading.stack_size(128 * 1024 * 1024)
        try:
            t = threading.Thread(target=run)
            t.start()
            t.join()
        finally:
            threading.stack_size(old_stack)
            sys.setrecursionlimit(old_limit)
        if err:                                         # pragma: no cover
            raise err[0]

        assert [out[q] for q in queries] == [True, False, True, False]
        for q in queries:
            assert eng.check(*q) == out[q], q
        # and the bulk surface terminates on the ring too
        assert len(eng.expand('viewer', 'folder', 'f0').pos) == n + 1


def test_deep_chain_cycle_and_memo_semantics_preserved():
    """The delicate part of the conversion: the Tarjan-lowlink memo guard and the
    provisional-False cycle answer. A self-referential relation (the engine admits
    ``define member: [user, group#member]`` cycles only through TTU/computed shapes, so
    use a computed self-reference) plus a chain that re-enters an in-progress key must
    still terminate with the oracle's answer rather than looping or memoizing a
    provisional result."""
    schema = '''
type user
type group
  relations
    define direct: [user, group#member]
    define member: direct
type doc
  relations
    define parent: [doc]
    define viewer: [user, group#member] or viewer from parent
'''
    tuples = [('...', 'user', 'u1', 'direct', 'group', 'g1'),
              ('member', 'group', 'g1', 'direct', 'group', 'g2'),
              ('member', 'group', 'g2', 'viewer', 'doc', 'd2'),
              ('...', 'doc', 'd2', 'parent', 'doc', 'd1'),
              ('...', 'doc', 'd1', 'parent', 'doc', 'd0')]
    oracle = Oracle(schema, [OracleTuple(*t) for t in tuples])
    with Session(_mem_engine()) as s:
        eng = SetEngine(s, 'cyc', schema=schema)
        for t in tuples:
            eng.add_tuple(*t)
        grid = [(sp, st, sn, rel, ot, on)
                for (sp, st, sn) in (('...', 'user', 'u1'), ('...', 'user', 'u2'),
                                     ('member', 'group', 'g1'), ('member', 'group', 'g2'))
                for (ot, rel) in (('doc', 'viewer'), ('group', 'member'), ('group', 'direct'))
                for on in ('d0', 'd1', 'd2', 'g1', 'g2')]
        for q in grid:
            assert eng.check(*q) == oracle.check(*q), q


# =========================================================================== #
# ZT-P1-4 -- the SQLite locks were silent no-ops
# =========================================================================== #

def test_source_lock_is_a_real_write_lock_on_sqlite(tmp_path, monkeypatch):
    """A held ``_lock_source`` blocks a second writer -- and the OLD statement
    (``SELECT ... FOR UPDATE``) does not, which is the no-op that was fixed."""
    # fail fast instead of waiting out the (production-sensible) busy timeout
    monkeypatch.setattr(core_mod, 'SQLITE_BUSY_TIMEOUT_MS', 50)
    monkeypatch.setattr(core_mod, 'SQLITE_BUSY_RETRIES', 1)
    engine = _file_engine(tmp_path / 'lock.db')
    with Session(engine) as boot:
        ConnectedStore(boot, 's', schema=BOOL_SCHEMA)
        boot.commit()

    with Session(engine) as sa, Session(engine) as sb:
        a = TupleSource(sa, 's')
        b = TupleSource(sb, 's')
        a._lock_source()                       # A holds the store's write lock

        # CONTROL: the pre-fix statement completes happily -- it locks nothing.
        assert sb.exec(select(SchemaV4).where(SchemaV4.store_id == 's')
                       .with_for_update()).first() is not None
        sb.rollback()

        # THE FIX: the real lock refuses to be taken twice.
        with pytest.raises(OperationalError):
            b._lock_source()
        sb.rollback()
        sa.rollback()


def test_write_lock_leaves_the_connection_in_a_transaction(tmp_path):
    """Both locks promote the connection into a real transaction, which is what makes a
    write's check-then-act (validate, then INSERT) atomic. Checked for pysqlite's
    DEFAULT config -- the one the library ships against -- where SELECTs alone run in
    autocommit."""
    engine = _file_engine(tmp_path / 'txn.db', recipe=False)
    with Session(engine) as s:
        cs = ConnectedStore(s, 's', schema=BOOL_SCHEMA)
        assert is_sqlite(s)
        raw = s.connection().connection.dbapi_connection
        assert raw.isolation_level == ''                    # pysqlite default
        cs.source._lock_source()
        assert raw.in_transaction
        s.rollback()
        cs.widx.idx._lock_store()
        assert raw.in_transaction
        s.rollback()


@pytest.mark.parametrize('kwargs', [
    dict(isolation_level='AUTOCOMMIT'),          # SQLAlchemy-level autocommit
])
def test_construction_refuses_autocommit_sqlite(tmp_path, kwargs):
    """The configurations that now RAISE: anything where the write lock cannot hold.
    The error names the fix."""
    path = tmp_path / 'auto.db'
    with Session(_file_engine(path)) as boot:                # bootstrap normally
        ConnectedStore(boot, 's', schema=BOOL_SCHEMA)
        boot.commit()
    engine = create_engine(f'sqlite:///{path}', **kwargs)
    with Session(engine) as s:
        with pytest.raises(WriteLockUnsafe) as exc:
            ConnectedStore(s, 's')
    assert 'autocommit' in str(exc.value)
    assert 'isolation_level' in str(exc.value)


@pytest.mark.parametrize('mode', ['isolation_level_none', 'autocommit_attr'])
def test_construction_refuses_driver_autocommit_without_begin(tmp_path, mode):
    """The other genuinely-unsafe shapes, both at the DRIVER level: pysqlite
    ``isolation_level=None`` with nothing emitting ``BEGIN`` (half of the documented
    recipe -- the multi-instance harness has the other half), and Python 3.12+'s
    ``sqlite3`` ``autocommit=True``."""
    path = tmp_path / f'nobegin_{mode}.db'
    with Session(_file_engine(path)) as boot:
        ConnectedStore(boot, 's', schema=BOOL_SCHEMA)
        boot.commit()

    engine = create_engine(f'sqlite:///{path}')

    @event.listens_for(engine, 'connect')
    def _no_begin(dbapi, _rec):
        if mode == 'isolation_level_none':
            dbapi.isolation_level = None        # autocommit, and NO begin listener
        else:
            dbapi.autocommit = True             # sqlite3's own autocommit mode

    with Session(engine) as s:
        with pytest.raises(WriteLockUnsafe):
            ConnectedStore(s, 's')


@pytest.mark.parametrize('recipe', [True, False])
def test_construction_accepts_both_safe_configurations(tmp_path, recipe):
    """Not over-tightened: pysqlite's DEFAULT (``isolation_level=''``) and the
    documented recipe (``isolation_level=None`` + a BEGIN listener) both open, write and
    read normally."""
    engine = _file_engine(tmp_path / f'ok{int(recipe)}.db', recipe=recipe)
    with Session(engine) as s:
        cs = ConnectedStore(s, 's', schema=BOOL_SCHEMA)
        token = cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
        assert cs.check('...', 'user', 'u1', 'viewer', 'doc', 'd1', at_least=token)


def test_in_memory_default_session_still_opens():
    """The whole existing suite's shape: a default in-memory SQLite session."""
    with Session(_mem_engine()) as s:
        cs = ConnectedStore(s, 's', schema=BOOL_SCHEMA)
        cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
        assert cs.check('...', 'user', 'u1', 'viewer', 'doc', 'd1')


# =========================================================================== #
# ZT-P1-5 -- watermark advances must be contiguous
# =========================================================================== #

def test_evaluator_watermark_gap_raises(tmp_path, monkeypatch):
    """A commit that this instance's read snapshot cannot see (simulated by hiding it
    from ``log_rows``, exactly what MySQL/InnoDB REPEATABLE READ does for real) used to
    be jumped over by ``max(watermark, token)`` and lost forever. Now it raises."""
    engine = _file_engine(tmp_path / 'gap.db')
    with Session(engine) as boot:
        ConnectedStore(boot, 's', schema=BOOL_SCHEMA)
        boot.commit()

    with Session(engine) as sa, Session(engine) as sb:
        a, b = TupleSource(sa, 's'), TupleSource(sb, 's')
        t1 = a.add('...', 'user', 'u1', 'editor', 'doc', 'd1')
        sa.commit()
        sb.rollback()                           # fresh snapshot (B was opened earlier)
        b.catch_up_evaluator()                  # B is caught up through t1
        assert b.evaluator_watermark == t1
        sb.rollback()

        hidden = a.add('...', 'user', 'u2', 'editor', 'doc', 'd1')   # invisible to B
        sa.commit()

        real_log_rows = source_mod.log_rows
        monkeypatch.setattr(source_mod, 'log_rows', lambda s, sid, after=0, limit=None: [
            r for r in real_log_rows(s, sid, after, limit) if r.id != hidden])

        with pytest.raises(WatermarkGap) as exc:
            b.add('...', 'user', 'u3', 'editor', 'doc', 'd1')
        assert str(hidden) in str(exc.value)
        assert 'retry' in str(exc.value)
        # and the watermark did NOT move past the gap
        assert b.evaluator_watermark == t1
        sb.rollback()


def test_index_cursor_gap_raises(tmp_path, monkeypatch):
    """The same guard on the apply step: ``cursor.applied_log_id = rows[-1].id`` with a
    row of the batch invisible would strand that row permanently (and ``at_least`` would
    still certify the resulting stale answer)."""
    engine = _file_engine(tmp_path / 'cgap.db')
    with Session(engine) as boot:
        ConnectedStore(boot, 's', schema=BOOL_SCHEMA)
        boot.commit()

    with Session(engine) as sw:                        # the writer fills the log
        w = ConnectedStore(sw, 's')
        ids = [w.add_tuple('...', 'user', f'u{i}', 'editor', 'doc', 'd1')
               for i in range(1, 4)]

    with Session(engine) as sr:                        # a lagging async index
        r = ConnectedStore(sr, 's', sync=False)
        r.cursor.applied_log_id = 0
        sr.commit()
        real = apply_mod.log_rows
        monkeypatch.setattr(apply_mod, 'log_rows', lambda s, sid, after=0, limit=None: [
            row for row in real(s, sid, after, limit) if row.id != ids[1]])
        with pytest.raises(WatermarkGap) as exc:
            r.catch_up()
        assert str(ids[1]) in str(exc.value)
        sr.rollback()
        sr.refresh(r.cursor)
        assert r.cursor.applied_log_id == 0            # nothing committed


def test_contiguous_path_unaffected_and_read_your_writes_holds(tmp_path):
    """The normal path: every write advances both watermarks by exactly its own token
    (assignment, not max), ``lag()`` returns to 0, and the ``at_least`` read-your-writes
    contract still holds on the sync AND async schedules."""
    engine = _file_engine(tmp_path / 'ok.db')
    with Session(engine) as s:
        cs = ConnectedStore(s, 's', schema=BOOL_SCHEMA)
        tokens = []
        for i in range(6):
            tokens.append(cs.add_tuple('...', 'user', f'u{i}', 'editor', 'doc', 'd1'))
            assert cs.source.evaluator_watermark == tokens[-1]
            assert cs.cursor.applied_log_id == tokens[-1]
            assert cs.lag() == 0
            assert cs.check('...', 'user', f'u{i}', 'viewer', 'doc', 'd1',
                            at_least=tokens[-1])
        assert tokens == sorted(set(tokens))
        # removes advance it too, and idempotent adds do not regress it
        tok = cs.remove_tuple('...', 'user', 'u0', 'editor', 'doc', 'd1')
        assert cs.source.evaluator_watermark == tok
        dup = cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')   # duplicate
        assert dup == log_watermark(s, 's') == tok
        assert cs.source.evaluator_watermark == tok

    with Session(engine) as s2:                        # async schedule
        cs2 = ConnectedStore(s2, 's', sync=False)
        t = cs2.add_tuple('...', 'user', 'zz', 'editor', 'doc', 'd1')
        assert cs2.lag() == 1
        # tokened read while the index lags: served by the fresh set engine
        assert cs2.check('...', 'user', 'zz', 'viewer', 'doc', 'd1', at_least=t)
        assert cs2.catch_up() == 1
        assert cs2.lag() == 0
        assert cs2.check('...', 'user', 'zz', 'viewer', 'doc', 'd1', at_least=t)


def test_no_false_gap_when_log_ids_interleave_across_stores(tmp_path):
    """No false alarm: ``TupleLogV1.id`` is a GLOBAL autoincrement, so two stores in one
    database produce per-store id sequences full of holes. Every write must still be
    accepted (this is the case the cheap contiguity fast path cannot take, so it
    exercises the real gap query)."""
    engine = _file_engine(tmp_path / 'two.db')
    with Session(engine) as sa, Session(engine) as sb:
        a = ConnectedStore(sa, 'A', schema=BOOL_SCHEMA)
        b = ConnectedStore(sb, 'B', schema=BOOL_SCHEMA)
        for i in range(5):
            ta = a.add_tuple('...', 'user', f'u{i}', 'editor', 'doc', 'd1')
            tb = b.add_tuple('...', 'user', f'u{i}', 'editor', 'doc', 'd1')
            assert ta < tb                                  # ids interleave
            assert a.source.evaluator_watermark == ta
            assert b.source.evaluator_watermark == tb
        assert a.lag() == 0 and b.lag() == 0
        for i in range(5):
            assert a.check('...', 'user', f'u{i}', 'viewer', 'doc', 'd1')
            assert b.check('...', 'user', f'u{i}', 'viewer', 'doc', 'd1')
        # a burned id (a rolled-back write) is not a gap either
        with pytest.raises(ValueError):
            a.add_tuple('...', 'user', 'u0', 'nosuchrelation', 'doc', 'd1')
        assert a.add_tuple('...', 'user', 'after', 'editor', 'doc', 'd1')


def test_rolled_back_own_write_still_needs_refresh_not_a_gap(tmp_path):
    """The documented pre-existing contract (rollback of your OWN write requires
    ``refresh_evaluator``) is unchanged by the assignment/contiguity rewrite."""
    engine = _file_engine(tmp_path / 'rb.db')
    with Session(engine) as s:
        ConnectedStore(s, 's', schema=BOOL_SCHEMA)
        src = TupleSource(s, 's')
        tok = src.add('...', 'user', 'u1', 'editor', 'doc', 'd1')
        assert src.evaluator_watermark == tok
        s.rollback()
        src.refresh_evaluator()
        assert src.evaluator_watermark == 0
        assert src.check('...', 'user', 'u1', 'editor', 'doc', 'd1') is False
        again = src.add('...', 'user', 'u1', 'editor', 'doc', 'd1')
        assert src.evaluator_watermark == again


# --------------------------------------------------------------------------- #
# ZT-P1-5, second half: the isolation-level assertion
# --------------------------------------------------------------------------- #

class _FakeConn:
    def __init__(self, level):
        self._level = level

    def get_isolation_level(self):
        return self._level


class _FakeSession:
    """Minimal stand-in for a non-SQLite bind (the check is dialect-aware, and MySQL --
    where REPEATABLE READ is the DEFAULT -- is the dialect that matters)."""

    def __init__(self, dialect, level):
        self._dialect, self._level = dialect, level

    def get_bind(self):
        class _B:
            dialect = type('D', (), {'name': self._dialect})
        return _B()

    def connection(self):
        return _FakeConn(self._level)


@pytest.mark.parametrize('level', ['REPEATABLE READ', 'READ UNCOMMITTED'])
def test_unsafe_isolation_level_rejected(level):
    with pytest.raises(UnsafeIsolationLevel) as exc:
        source_mod.assert_read_isolation(_FakeSession('mysql', level))
    assert 'READ COMMITTED' in str(exc.value)


@pytest.mark.parametrize('level', ['READ COMMITTED', 'SERIALIZABLE'])
def test_safe_isolation_levels_accepted(level):
    source_mod.assert_read_isolation(_FakeSession('postgresql', level))


def test_sqlite_isolation_check_is_not_a_false_alarm():
    """pysqlite reports SERIALIZABLE whatever the configuration, and SQLite cannot hide
    a committed row from a writer (it fails the write loudly instead), so the check must
    not fire there -- it would flag every session in this repo."""
    with Session(_mem_engine()) as s:
        source_mod.assert_read_isolation(s)                 # no raise
        assert is_sqlite(s)
