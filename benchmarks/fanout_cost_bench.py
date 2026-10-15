"""TK150: what does ONE admitted write that creates N closure rows cost the graph index?

Quantifies the blast radius that ``ZANZIBAR_MAX_CLOSURE_FANOUT``
(``zanzibar.graphindex.core.DEFAULT_MAX_CLOSURE_FANOUT``) bounds. Results and
conclusions: ``docs/closure-fanout-cost-2026-10-14.md``.

Every point runs in its OWN process (the ``sweep`` driver spawns ``point``), so the
peak-memory figure is not polluted by an earlier point, and the cap env var is read
fresh (the cap is resolved once, at ``ReachabilityIndex`` construction).

Shapes (``fanout = |ancestors(subject)| x |descendants(object)| + |A| + |D|``):

* ``userset`` -- ``group:g`` has N members; the measured write is
  ``group:g#member viewer doc:d``  (|A| = N, |D| = 0  ->  N closure rows).
* ``object``  -- N docs have ``parent folder:f`` (TTU ``viewer from parent``); the
  measured write is ``user:u viewer folder:f``  (|A| = 0, |D| = N).
* ``product`` -- ``group:g`` has a members, ``folder:f`` has d docs (a = d =
  round(sqrt(N))); the measured write is ``group:g#member viewer folder:f``
  (a*d + a + d closure rows from only a + d stored tuples).

The precondition is NOT measured and NOT built through per-write admission: the raw
tuples are bulk-inserted as ``RelationTuple`` rows PLUS matching ``TupleLog`` ADD rows
(so the TK140 adoption check sees a fully-logged store), then the index is built with
``build_index(..., bulk=True)`` (the P13 offline constructor, never capped), and only
then is the store opened through the user-facing ``ConnectedStore`` (sync schedule).
The one measured write goes through ``ConnectedStore.add_tuple`` exactly as a user's
would, and the removal through ``remove_tuple``.

Usage (from the repo root, with the repo's conda env)::

    python -m benchmarks.fanout_cost_bench point --shape userset --n 10000 --out x.jsonl
    python -m benchmarks.fanout_cost_bench sweep --plan sqlite-small --out x.jsonl

``--mode admit`` sets ``ZANZIBAR_MAX_CLOSURE_FANOUT=0`` (cap off, the write is
admitted); ``--mode refuse`` unsets it (default cap) to time the refusal instead.
``--dsn`` (or ``ZANZIBAR_TEST_DSN``) runs on PostgreSQL; the point DROPS and recreates
every zanzibar table in that database, so point it at a throwaway server only
(``scripts/pg_local.sh``).
"""

from __future__ import annotations

import argparse
import ctypes
import gc
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / 'src'))   # this checkout's code, never an installed copy

from sqlalchemy import event, func, insert, text  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine, select  # noqa: E402

from zanzibar.connectedstore import build_index, save_schema  # noqa: E402
from zanzibar.connectedstore.models import TupleLog  # noqa: E402
from zanzibar.graphindex.core import ReachabilityIndex  # noqa: E402
from zanzibar.graphindex.models import DeltaOutbox, Edge, Node  # noqa: E402
from zanzibar.setengine.models import RelationTuple  # noqa: E402

# The user-facing store class may be renamed (TK123); import defensively.
try:
    from zanzibar.connectedstore import ConnectedStore as _StoreClass  # noqa: E402
except ImportError:  # pragma: no cover - post-rename
    from zanzibar.connectedstore import Store as _StoreClass  # type: ignore  # noqa: E402
try:
    from zanzibar.schema import ClosureFanoutExceeded  # noqa: E402
except ImportError:  # pragma: no cover
    from zanzibar import ClosureFanoutExceeded  # type: ignore  # noqa: E402
import zanzibar.connectedstore.store as _store_mod  # noqa: E402

from benchmarks._harness import rss_mb  # noqa: E402

CAP_ENV = 'ZANZIBAR_MAX_CLOSURE_FANOUT'
STORE = 'fan'

SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user]
type folder
  relations
    define viewer: [user, group#member]
type doc
  relations
    define parent: [folder]
    define viewer: [user, group#member] or viewer from parent
"""


# --------------------------------------------------------------------------- #
# Machine-load and memory probes (Windows; degrade to None elsewhere)
# --------------------------------------------------------------------------- #

def _system_times():
    try:
        ft = ctypes.c_ulonglong
        idle, kern, user = ft(), ft(), ft()
        if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern),
                                                 ctypes.byref(user)):
            return idle.value, kern.value, user.value
    except Exception:
        pass
    return None


def _busy_pct(t0, t1):
    if not t0 or not t1:
        return None
    di, dk, du = (b - a for a, b in zip(t0, t1))
    total = dk + du        # kernel time includes idle time
    return round(100.0 * (1 - di / total), 1) if total else None


def machine_load() -> dict:
    """Competing processes at this instant (other agents share the laptop)."""
    out = {}
    try:
        res = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True,
                             text=True, timeout=30)
        names = [ln.split('","')[0].strip('"').lower() for ln in res.stdout.splitlines() if ln]
        for img in ('python.exe', 'lean.exe', 'lake.exe', 'postgres.exe'):
            out[img.split('.')[0]] = names.count(img)
    except Exception as e:  # pragma: no cover
        out['error'] = repr(e)
    t0 = _system_times()
    time.sleep(0.5)
    out['cpu_busy_pct_0.5s'] = _busy_pct(t0, _system_times())
    return out


def avail_phys_mb() -> float | None:
    """System-wide available physical memory (GlobalMemoryStatusEx), MB."""
    try:
        class MS(ctypes.Structure):
            _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            return m.ullAvailPhys / (1024.0 * 1024.0)
    except Exception:
        pass
    return None


#: Set by ``run_point``: called (from the sampler thread) when the machine runs short
#: of physical memory, to record a partial result and exit before the laptop -- shared
#: with other sessions -- starts paging.
_ON_MEMORY_ABORT = None
MIN_AVAIL_MB = float(os.environ.get('FANOUT_BENCH_MIN_AVAIL_MB', '1500'))


class PeakSampler:
    """Polls the process working set every ``period`` s on a daemon thread; ``peak``
    is the largest sample inside the window (the write-attributable peak, unlike the
    process-lifetime PeakWorkingSetSize, which setup already raised). Also the memory
    watchdog: below ``MIN_AVAIL_MB`` system-available memory it aborts the point."""

    def __init__(self, period: float = 0.02):
        self.period = period
        self.peak = 0.0
        self.t0 = time.perf_counter()
        self.min_avail = None
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        k = 0
        while not self._stop.is_set():
            v = rss_mb('current') or 0.0
            if v > self.peak:
                self.peak = v
            k += 1
            if k % 25 == 0:          # every ~0.5 s
                av = avail_phys_mb()
                if av is not None:
                    self.min_avail = av if self.min_avail is None else min(self.min_avail, av)
                    if av < MIN_AVAIL_MB and _ON_MEMORY_ABORT is not None:
                        _ON_MEMORY_ABORT(self, av)
            self._stop.wait(self.period)

    def __enter__(self):
        self.peak = rss_mb('current') or 0.0
        self.t0 = time.perf_counter()
        self._t.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join()
        v = rss_mb('current') or 0.0
        self.peak = max(self.peak, v)


# --------------------------------------------------------------------------- #
# Phase timers: wrap the hot methods for the measured window only
# --------------------------------------------------------------------------- #

class Phases:
    def __init__(self):
        self.t: dict[str, float] = {}
        self.n: dict[str, int] = {}

    def add(self, k, dt):
        self.t[k] = self.t.get(k, 0.0) + dt
        self.n[k] = self.n.get(k, 0) + 1

    def wrap(self, owner, name, label):
        orig = getattr(owner, name)

        def w(*a, **kw):
            t0 = time.perf_counter()
            try:
                return orig(*a, **kw)
            finally:
                self.add(label, time.perf_counter() - t0)
        setattr(owner, name, w)
        return lambda: setattr(owner, name, orig)


def instrument(cs, session: Session, ph: Phases):
    undo = []
    # store layer (instance attributes: _write reads them through self)
    undo.append(ph.wrap(cs.source, 'add', 'admit_s'))
    undo.append(ph.wrap(cs.source, 'remove', 'admit_s'))
    undo.append(ph.wrap(cs.source, 'refresh_evaluator', 'refresh_evaluator_s'))
    undo.append(ph.wrap(session, 'commit', 'commit_s'))
    undo.append(ph.wrap(session, 'exec', 'sql_exec_s'))
    undo.append(ph.wrap(_store_mod, 'advance_index', 'apply_s'))
    # index layer (class attributes)
    undo.append(ph.wrap(ReachabilityIndex, '_add_direct_edge_unsafe_impl', 'expand_s'))
    undo.append(ph.wrap(ReachabilityIndex, '_add_indirect_edges_batch_unsafe', 'batch_s'))
    undo.append(ph.wrap(ReachabilityIndex, '_flush_outbox', 'outbox_insert_s'))
    # ORM flush (the INSERT/DELETE of the closure rows) via session events
    st = {}

    def bf(sess, ctx, inst):
        st['t'] = time.perf_counter()

    def af(sess, ctx):
        if 't' in st:
            ph.add('orm_flush_s', time.perf_counter() - st.pop('t'))
    event.listen(session, 'before_flush', bf)
    event.listen(session, 'after_flush_postexec', af)
    undo.append(lambda: event.remove(session, 'before_flush', bf))
    undo.append(lambda: event.remove(session, 'after_flush_postexec', af))
    return lambda: [u() for u in reversed(undo)]


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

def shape_plan(shape: str, n: int):
    """-> (precondition raw tuples generator, n_tuples, write tuple, check probe,
    expected closure rows by the cap's own formula)."""
    if shape == 'userset':
        def gen():
            for i in range(n):
                yield ('...', 'user', f'u{i}', 'member', 'group', 'g')
        write = ('member', 'group', 'g', 'viewer', 'doc', 'd')
        probe = ('...', 'user', 'u0', 'viewer', 'doc', 'd')
        return gen, n, write, probe, n          # |A| = n, |D| = 0
    if shape == 'object':
        def gen():
            for i in range(n):
                yield ('...', 'folder', 'f', 'parent', 'doc', f'd{i}')
        write = ('...', 'user', 'u', 'viewer', 'folder', 'f')
        probe = ('...', 'user', 'u', 'viewer', 'doc', 'd0')
        return gen, n, write, probe, n          # |A| = 0, |D| = n (expected; verified)
    if shape == 'product':
        a = d = max(1, round(n ** 0.5))

        def gen():
            for i in range(a):
                yield ('...', 'user', f'u{i}', 'member', 'group', 'g')
            for j in range(d):
                yield ('...', 'folder', 'f', 'parent', 'doc', f'd{j}')
        write = ('member', 'group', 'g', 'viewer', 'folder', 'f')
        probe = ('...', 'user', 'u0', 'viewer', 'doc', 'd0')
        return gen, a + d, write, probe, a * d + a + d
    raise ValueError(shape)


def seed(session: Session, gen, chunk: int = 20000) -> None:
    """Bulk-insert the precondition as RelationTuple + TupleLog ADD rows (log ids in
    tuple order), bypassing per-write admission: the data is acyclic and
    admission-valid by construction, and this setup is not what is measured."""
    rt, lg = RelationTuple.__table__, TupleLog.__table__
    now = time.time()
    buf = []
    for (sp, st, sn, rel, ot, on) in gen():
        buf.append(dict(store_id=STORE, subject_predicate=sp, subject_type=st,
                        subject_name=sn, relation=rel, object_type=ot,
                        object_name=on, created_at=now))
        if len(buf) >= chunk:
            session.execute(insert(rt), buf)
            session.execute(insert(lg), [dict(r, op='ADD') for r in buf])
            buf = []
    if buf:
        session.execute(insert(rt), buf)
        session.execute(insert(lg), [dict(r, op='ADD') for r in buf])
    session.commit()


def _workdir(args) -> Path:
    return Path(args.workdir or Path(tempfile.gettempdir()) / 'zanzibar-fanout-bench')


def _sweep_leftovers(work: Path) -> list[str]:
    """Delete bench DB files a hard-exited point (memory watchdog) could not."""
    gone = []
    if work.is_dir():
        for p in work.glob('fan_*.db*'):
            p.unlink()
            gone.append(p.name)
    return gone


def count(session, model) -> int:
    return int(session.exec(select(func.count()).select_from(model)
                            .where(model.store_id == STORE)).one())


def db_bytes(session, db_path: Path | None) -> int:
    if db_path is not None:
        return sum(p.stat().st_size for p in
                   (db_path, Path(str(db_path) + '-wal'), Path(str(db_path) + '-journal'))
                   if p.exists())
    return int(session.exec(text('select pg_database_size(current_database())')).one()[0])


def check_us(cs, probe, reps: int = 300) -> tuple[float, bool]:
    ans = cs.check(*probe)
    xs = []
    for _ in range(reps):
        t0 = time.perf_counter_ns()
        cs.check(*probe)
        xs.append(time.perf_counter_ns() - t0)
    return round(statistics.median(xs) / 1000.0, 1), ans


# --------------------------------------------------------------------------- #
# One point
# --------------------------------------------------------------------------- #

def run_point(args) -> dict:
    rec: dict = dict(shape=args.shape, n=args.n, mode=args.mode, paranoia=args.paranoia,
                     rep=args.rep, date=time.strftime('%Y-%m-%d %H:%M:%S'),
                     python=platform.python_version(), host=platform.node())
    rec['load_before'] = machine_load()
    dsn = args.dsn or None
    db_path = None
    if dsn:
        rec['backend'] = 'postgresql'
        engine = create_engine(dsn)
        SQLModel.metadata.drop_all(engine)
    else:
        rec['backend'] = 'sqlite-file'
        work = _workdir(args)
        work.mkdir(parents=True, exist_ok=True)
        db_path = work / f'fan_{args.shape}_{args.n}_{args.mode}_{args.paranoia}_{os.getpid()}.db'
        engine = create_engine(f'sqlite:///{db_path}')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    def _abort(sampler, avail):
        # Runs on the sampler thread: record what we know, drop the DB file, hard-exit
        # (a clean unwind would first finish the very allocation we are escaping).
        rec['aborted'] = (f'system available memory {avail:.0f} MB < {MIN_AVAIL_MB:.0f} MB '
                          f'after {time.perf_counter() - sampler.t0:.1f} s in the window')
        rec['aborted_ws_mb'] = round(rss_mb('current') or 0, 1)
        rec['aborted_window_peak_mb'] = round(sampler.peak, 1)
        if args.out:
            with open(args.out, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec, sort_keys=True, default=str) + '\n')
        print('ABORTED', rec['aborted'], flush=True)
        if db_path is not None and not args.keep_db:
            try:
                engine.dispose()
                for p in (db_path, Path(str(db_path) + '-wal'), Path(str(db_path) + '-journal')):
                    if p.exists():
                        p.unlink()
            except Exception as e:      # an open handle on Windows: say so, do not hide it
                print(f'ABORT could not delete {db_path}: {e!r}', flush=True)
        os._exit(3)

    global _ON_MEMORY_ABORT
    _ON_MEMORY_ABORT = _abort
    rec['avail_mb_at_start'] = round(avail_phys_mb() or 0)
    # Whole-point watchdog (setup included: the bulk build of a 1M-tuple precondition
    # is itself large); the per-window samplers below measure the write's own peak.
    whole = PeakSampler(period=0.02)
    whole.__enter__()
    try:
        gen, n_tuples, write, probe, expect_rows = shape_plan(args.shape, args.n)
        rec['precondition_tuples'] = n_tuples
        rec['expected_closure_rows'] = expect_rows
        t0 = time.perf_counter()
        save_schema(session, STORE, SCHEMA)
        session.commit()
        seed(session, gen)
        rec['setup_seed_s'] = round(time.perf_counter() - t0, 2)
        t0 = time.perf_counter()
        rep = build_index(session, STORE, bulk=True)
        rec['setup_bulk_build_s'] = round(time.perf_counter() - t0, 2)
        rec['setup_constructor'] = getattr(rep, 'constructor', None)

        if args.mode == 'admit':
            os.environ[CAP_ENV] = '0'
        else:
            os.environ.pop(CAP_ENV, None)
        t0 = time.perf_counter()
        cs = _StoreClass(session, STORE, paranoia=args.paranoia)
        rec['setup_open_s'] = round(time.perf_counter() - t0, 2)
        rec['cap'] = cs.widx.idx.max_closure_fanout

        edges0, out0, nodes0 = count(session, Edge), count(session, DeltaOutbox), count(session, Node)
        bytes0 = db_bytes(session, db_path)
        rec['edges_before'], rec['nodes_before'], rec['bytes_before'] = edges0, nodes0, bytes0
        rec['check_before_us'], ans0 = check_us(cs, probe)
        if ans0:
            raise AssertionError(f'probe {probe} already allowed before the write')

        # ---- the measured write ------------------------------------------------
        gc.collect()
        ph = Phases()
        undo = instrument(cs, session, ph)
        sys_t0 = _system_times()
        refused = None
        with PeakSampler() as ps:
            ws0 = rss_mb('current')
            t0 = time.perf_counter()
            try:
                cs.add_tuple(*write)
            except ClosureFanoutExceeded as e:
                refused = str(e)[:200]
            rec['write_s'] = round(time.perf_counter() - t0, 3)
        undo()
        rec['write_cpu_busy_pct'] = _busy_pct(sys_t0, _system_times())
        rec['write_phases'] = {k: round(v, 3) for k, v in sorted(ph.t.items())}
        rec['write_ws_before_mb'] = round(ws0 or 0, 1)
        rec['write_peak_ws_mb'] = round(ps.peak, 1)
        rec['write_peak_delta_mb'] = round(ps.peak - (ws0 or 0), 1)
        rec['write_min_avail_mb'] = round(ps.min_avail) if ps.min_avail is not None else None
        rec['refused'] = refused

        edges1, out1 = count(session, Edge), count(session, DeltaOutbox)
        bytes1 = db_bytes(session, db_path)
        rec['edge_rows_added'] = edges1 - edges0
        rec['outbox_rows_added'] = out1 - out0
        rec['bytes_added'] = bytes1 - bytes0
        rec['check_after_us'], ans1 = check_us(cs, probe)
        if refused is None and not ans1:
            raise AssertionError('admitted write did not grant the probe')
        if refused is not None and ans1:
            raise AssertionError('refused write granted the probe')

        if refused is None:
            gc.collect()
            ph = Phases()
            undo = instrument(cs, session, ph)
            sys_t0 = _system_times()
            with PeakSampler() as ps:
                ws0 = rss_mb('current')
                t0 = time.perf_counter()
                cs.remove_tuple(*write)
                rec['remove_s'] = round(time.perf_counter() - t0, 3)
            undo()
            rec['remove_cpu_busy_pct'] = _busy_pct(sys_t0, _system_times())
            rec['remove_phases'] = {k: round(v, 3) for k, v in sorted(ph.t.items())}
            rec['remove_peak_delta_mb'] = round(ps.peak - (ws0 or 0), 1)
            rec['edge_rows_after_remove'] = count(session, Edge) - edges0
            rec['bytes_after_remove'] = db_bytes(session, db_path) - bytes0
            rec['check_after_remove_us'], ans2 = check_us(cs, probe)
            if ans2:
                raise AssertionError('removal did not revoke the probe')
        rec['process_peak_ws_mb'] = round(rss_mb('peak') or 0, 1)
        rec['load_after'] = machine_load()
    finally:
        whole.__exit__(None, None, None)
        rec['point_min_avail_mb'] = round(whole.min_avail) if whole.min_avail is not None else None
        session.close()
        if dsn:
            SQLModel.metadata.drop_all(engine)
        engine.dispose()
        if db_path is not None and not args.keep_db:
            for p in (db_path, Path(str(db_path) + '-wal'), Path(str(db_path) + '-journal')):
                if p.exists():
                    p.unlink()
    return rec


# --------------------------------------------------------------------------- #
# Sweep driver: one subprocess per point
# --------------------------------------------------------------------------- #

_SHAPES = ('userset', 'object', 'product')
PLANS = {
    # (shape, n, mode, paranoia, reps)
    'sqlite-small': (
        [(s, n, 'admit', 'off', 3) for n in (10_000, 100_000) for s in _SHAPES]
        + [('userset', n, 'admit', p, 3) for n in (10_000, 100_000) for p in ('residue', 'full')]
    ),
    'sqlite-large': [(s, n, 'admit', 'off', 1) for n in (300_000, 1_000_000) for s in _SHAPES],
    'refuse': [(s, n, 'refuse', 'off', 1) for n in (100_001, 1_000_000)
               for s in ('userset', 'product')],
    'pg': [(s, n, 'admit', 'off', 1) for n in (10_000, 100_000, 1_000_000)
           for s in ('userset', 'product')],
}


def sweep(args) -> None:
    plan = PLANS[args.plan]
    if args.only_n:
        plan = [p for p in plan if p[1] in args.only_n]
    if args.only_shape:
        plan = [p for p in plan if p[0] in args.only_shape]
    for shape, n, mode, par, reps in plan:
        for r in range(reps):
            cmd = [sys.executable, '-m', 'benchmarks.fanout_cost_bench', 'point',
                   '--shape', shape, '--n', str(n), '--mode', mode, '--paranoia', par,
                   '--rep', str(r), '--out', args.out]
            if args.dsn:
                cmd += ['--dsn', args.dsn]
            if args.workdir:
                cmd += ['--workdir', args.workdir]
            print('>>', ' '.join(cmd[3:]), flush=True)
            res = subprocess.run(cmd, cwd=str(_ROOT), timeout=args.timeout)
            if res.returncode != 0:
                print(f'!! point failed rc={res.returncode}', flush=True)
            if not args.dsn:
                left = _sweep_leftovers(_workdir(args))
                if left:
                    print(f'!! deleted leftover DB files {left}', flush=True)


def report(args) -> None:
    """Markdown table from a results JSONL: one row per (backend, shape, N, mode,
    paranoia), median over reps (the rep count is shown), so the doc's table is
    regenerated from data rather than retyped."""
    groups: dict = {}
    for ln in open(args.inp, encoding='utf-8'):
        r = json.loads(ln)
        if r.get('aborted'):
            continue
        k = (r['backend'], r['shape'], r['n'], r['mode'], r['paranoia'])
        groups.setdefault(k, []).append(r)

    def med(rs, key, sub=None):
        xs = [(r.get(sub) or {}).get(key) if sub else r.get(key) for r in rs]
        xs = [x for x in xs if x is not None]
        return statistics.median(xs) if xs else None

    def f(x, nd=1):
        if isinstance(x, float) and x.is_integer() and nd == 1 and abs(x) >= 1000:
            x = int(x)       # a median of whole counts over an even rep count
        return '-' if x is None else (f'{x:,.{nd}f}' if isinstance(x, float) else f'{x:,}')

    print('| backend | shape | N | mode | paranoia | reps | write s | expand s | ORM flush s '
          '| closure rows | outbox rows | MB added | us/row | peak delta MB | KB/row RAM '
          '| remove s | check us before/after | load: py procs, CPU% |')
    print('|' + '---|' * 18)
    order = {'userset': 0, 'object': 1, 'product': 2}
    for k in sorted(groups, key=lambda k: (k[0], k[3], k[4] != 'off', k[4], k[2], order.get(k[1], 9))):
        rs = groups[k]
        rows = med(rs, 'edge_rows_added')
        w = med(rs, 'write_s')
        mb = med(rs, 'bytes_added')
        pk = med(rs, 'write_peak_delta_mb')
        py = sorted({r['load_before'].get('python') for r in rs})
        cpu = med(rs, 'write_cpu_busy_pct')
        print(f"| {k[0]} | {k[1]} | {k[2]:,} | {k[3]} | {k[4]} | {len(rs)} | {f(w, 2)} "
              f"| {f(med(rs, 'expand_s', 'write_phases'), 2)} "
              f"| {f(med(rs, 'orm_flush_s', 'write_phases'), 2)} "
              f"| {f(rows)} | {f(med(rs, 'outbox_rows_added'))} "
              f"| {f(mb / 1e6 if mb is not None else None)} "
              f"| {f(1e6 * w / rows if w and rows else None)} | {f(pk, 0)} "
              f"| {f(1024 * pk / rows if pk and rows else None, 2)} "
              f"| {f(med(rs, 'remove_s'), 2)} "
              f"| {f(med(rs, 'check_before_us'), 0)} / {f(med(rs, 'check_after_us'), 0)} "
              f"| {','.join(str(p) for p in py)}, {f(cpu, 0)} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    rp = sub.add_parser('report')
    rp.add_argument('inp')
    p = sub.add_parser('point')
    p.add_argument('--shape', choices=('userset', 'object', 'product'), required=True)
    p.add_argument('--n', type=int, required=True)
    p.add_argument('--mode', choices=('admit', 'refuse'), default='admit')
    p.add_argument('--paranoia', default='off')
    p.add_argument('--rep', type=int, default=0)
    p.add_argument('--dsn', default=os.environ.get('ZANZIBAR_TEST_DSN'))
    p.add_argument('--workdir')
    p.add_argument('--keep-db', action='store_true')
    p.add_argument('--out', help='append one JSON line here')
    s = sub.add_parser('sweep')
    s.add_argument('--plan', choices=sorted(PLANS), required=True)
    s.add_argument('--only-n', type=int, nargs='*')
    s.add_argument('--only-shape', nargs='*')
    s.add_argument('--dsn', default=None)
    s.add_argument('--workdir')
    s.add_argument('--timeout', type=float, default=1800)
    s.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.cmd == 'report':
        report(a)
        return
    if a.cmd == 'sweep':
        sweep(a)
        return
    rec = run_point(a)
    line = json.dumps(rec, sort_keys=True)
    print(line, flush=True)
    if a.out:
        with open(a.out, 'a', encoding='utf-8') as f:
            f.write(line + '\n')


if __name__ == '__main__':
    main()
