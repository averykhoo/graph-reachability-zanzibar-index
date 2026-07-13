"""Shared benchmark plumbing for the two bench scripts.

Extracted so ``scale_bench.py`` (real-fixture scaling) and ``set_engine_bench.py``
(synthetic micro-schemas) share ONE implementation of the fiddly bits: the
process-RSS reader (Windows PSAPI / POSIX rusage), a fresh in-memory SQLite
session, a time-boxed timing loop, and the two backend builders (set-engine raw
load; graph closure materialisation + boolean backfill).

Nothing here is measured in CI -- these are scripts. Determinism is the callers'
responsibility (no RNG in measured paths); this module only times what it's given.
"""

from __future__ import annotations

import time
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from setengine import SetEngine
from setengine.setops import SetOps
from zanzibar_utils_v1 import parse_openfga_schema, Entity, RelationalTriple
from tests.wildcard_helpers import make_wildcard_index


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

def rss_mb(which: str = 'current') -> float | None:
    """Resident-set size in MB. ``which`` is 'current' or 'peak'.

    Windows: PSAPI GetProcessMemoryInfo (WorkingSetSize / PeakWorkingSetSize).
    POSIX: rusage.ru_maxrss (peak only; 'current' falls back to the same number).
    Returns None if neither path is available.
    """
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

        c = PMC(); c.cb = ctypes.sizeof(PMC)
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p     # HANDLE is 64-bit; avoid truncation
        psapi = ctypes.windll.psapi
        psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]
        if psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb):
            field = c.PeakWorkingSetSize if which == 'peak' else c.WorkingSetSize
            return field / (1024.0 * 1024.0)
    except Exception:
        pass
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

def timed(fn, iters: int, max_seconds: float | None = None) -> tuple[float, float, int]:
    """Call ``fn(i)`` up to ``iters`` times, stopping early if ``max_seconds``
    elapses. Returns (ops_per_sec, elapsed_s, iters_completed).

    The time box matters for the ``lookup`` surface: set-engine lookup is a
    full-store candidate sweep (O(stored tuples) per call), so at large N a
    single call can take seconds -- a fixed iteration count would hang the sweep.
    The elapsed clock is only sampled every 256 iters so the check is free for
    fast ops (``check`` runs at tens of thousands/s).
    """
    start = time.perf_counter()
    done = 0
    for i in range(iters):
        fn(i)
        done += 1
        if max_seconds is not None and (done & 0xFF) == 0 \
                and (time.perf_counter() - start) >= max_seconds:
            break
    elapsed = time.perf_counter() - start
    return (done / elapsed if elapsed else float('inf')), elapsed, done


# ---------------------------------------------------------------------------
# Sessions / backend builders
# ---------------------------------------------------------------------------

def fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def build_set(schema: str, shapes, ops: SetOps, tuples, store_id: str = 'sb') -> tuple[SetEngine, int]:
    """Load raw septuples into a SetEngine. Returns (engine, tuple_count)."""
    se = SetEngine(fresh_session(), store_id, schema, object_wildcard_shapes=shapes, ops=ops)
    n = 0
    for raw in tuples:
        se.add_tuple(*raw)
        n += 1
    se.session.commit()
    return se, n


def build_graph(schema: str, shapes, tuples, store_id: str = 'gb',
                paranoia: bool = False, commit_every: int = 0) -> tuple[object, int]:
    """Load raw septuples into the graph index (WildcardIndex), routing each
    write through ``RuleSet.apply`` and running a boolean ``backfill()`` when the
    schema compiles derived predicates. Returns (widx, tuple_count).

    paranoia defaults False: benchmarks measure index maintenance, not the
    invariant checker (per wildcard_helpers / CLAUDE.md -- paranoia runs the full
    I1-I13 sweep plus a per-pair outbox BFS around every commit). Pass
    paranoia=True to quantify that checker's overhead. (Paranoia is a graph-index
    feature; the set engine has no equivalent.)

    commit_every: 0 (default) batches all writes into one final commit -- fastest
    load, but paranoia then fires only once, understating its true per-commit cost.
    N>0 commits every N raw tuples (production-like), so paranoia is exercised the
    way it is paid in a real writer. Per-write commits are only valid on schemas
    with no derived cascade (simple / gdrive); on a boolean schema an intermediate
    commit would land in a state the cascade hasn't reconciled -> paranoia raises.
    """
    from index_v4.processor import DeltaProcessor
    ruleset = parse_openfga_schema(schema, object_wildcard_shapes=shapes)
    session, widx = make_wildcard_index(ruleset.schema_info, store_id=store_id, paranoia=paranoia)
    boolean = ruleset.compiled is not None and ruleset.compiled.plans
    if commit_every and boolean:
        raise ValueError('commit_every>0 is invalid on a boolean schema '
                         '(intermediate commit precedes cascade reconcile)')
    n = 0
    for raw in tuples:
        sp = Ellipsis if raw[0] == '...' else raw[0]
        tr = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        for d in ruleset.apply(tr):
            widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                           d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
        n += 1
        if commit_every and n % commit_every == 0:
            widx.idx.session.commit()
    if boolean:
        DeltaProcessor(widx, ruleset.compiled).backfill()   # offline bootstrap of derived state
    widx.idx.session.commit()
    return widx, n
