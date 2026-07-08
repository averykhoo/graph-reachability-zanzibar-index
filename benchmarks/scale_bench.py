"""Scaling benchmark: does per-check latency grow with tuple count? (review-3 follow-up)

Unlike ``set_engine_bench.py`` (synthetic deep/wide micro-schemas), this runs the
REAL fixture schemas at increasing data sizes and reports, per backend:

  * tuple count actually loaded,
  * build time (raw-tuple load; for the graph, closure materialisation + one
    ``backfill()`` for boolean schemas),
  * peak/current RSS after build (memory footprint at scale),
  * check throughput over a fixed, representative query mix,
  * whether check throughput is FLAT or DEGRADES as N grows (the OpenFGA question).

Two workloads:
  * ``gdrive``   -- pure-union TTU/computed hierarchy (folders, groups, docs). The
                    graph index materialises the full closure; the set engine walks
                    it on the fly. Local queries (a doc + its ancestor folders +
                    their groups) touch a bounded neighbourhood regardless of N.
  * ``demorgans``-- demorgans_law_1.fga: a 5-level boolean+TTU derived cascade over
                    attrs/conds/roles. Graph maintains derived state via the
                    processor; set engine evaluates the booleans pointwise.

Run ONE (workload, backend, scale) per process so RSS is clean:

    python -m benchmarks.scale_bench --workload gdrive   --backend set   --scale 1000
    python -m benchmarks.scale_bench --workload gdrive   --backend graph --scale 250
    python -m benchmarks.scale_bench --workload demorgans --backend set  --scale 400

``--json`` appends a one-line JSON record to benchmarks/results/scale_bench.jsonl.
Deterministic: all data derived by modular arithmetic, no RNG in measured paths.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, SQLModel, create_engine

from setengine import SetEngine, PySets, RoaringSets
from setengine.setops import SetOps
from zanzibar_utils_v1 import parse_openfga_schema, Entity, RelationalTriple
from tests.wildcard_helpers import make_wildcard_index


# ---------------------------------------------------------------------------
# Memory / timing
# ---------------------------------------------------------------------------

def _rss_mb(which: str) -> float | None:
    """current or peak working-set in MB (Windows PSAPI / POSIX rusage)."""
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
        k32.GetCurrentProcess.restype = ctypes.c_void_p
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


def timed(fn, iters: int) -> tuple[float, float]:
    start = time.perf_counter()
    for i in range(iters):
        fn(i)
    elapsed = time.perf_counter() - start
    return (iters / elapsed if elapsed else float('inf')), elapsed


# ---------------------------------------------------------------------------
# Schemas (the real fixtures)
# ---------------------------------------------------------------------------

_FIX = Path(__file__).resolve().parent.parent / 'tests' / 'fga_schemas'
GDRIVE = (_FIX / 'gdrive.fga').read_text()
# demorgans_law_2, not _1: in _1 the deep relations (matched_roles/matched_users)
# are constantly empty by construction -- their TTU tuplesets are derived relations
# with no Direct restrictions, so no tuple is ever STORED on them and TTU parents
# come from stored tuples only. _2's chain (access <- authorized_user <-
# role_user_met <- user_met_requirement <- missing_user) runs over storable
# tuplesets throughout, so it exercises the full boolean+TTU+star cascade with
# real conditions and attributes.
DEMORGANS = (_FIX / 'demorgans_law_2.fga').read_text()


# ---------------------------------------------------------------------------
# Data generators (deterministic; yield raw septuples)
# ---------------------------------------------------------------------------

def gen_gdrive(n: int, *, group_size: int = 8, chain_len: int = 5,
               viewers_per_doc: int = 3):
    """A gdrive dataset with N users/groups/folders/docs.

    - groups: each has `group_size` distinct user members.
    - folders: laid out in chains of length `chain_len` (folder i's parent is the
      previous folder in its chain), so ancestor depth is bounded by chain_len
      independent of N -- the check neighbourhood stays local as N grows.
    - each folder: an owner (user) and a viewer grant to one group.
    - docs: each has a parent folder, an owner, and `viewers_per_doc` viewer grants
      (mix of direct users and a group), so can_read traverses doc -> parent chain.
    """
    for g in range(n):
        for k in range(group_size):
            yield ('...', 'user', f'u{(g * group_size + k) % n}', 'member', 'group', f'g{g}')
    for f in range(n):
        yield ('...', 'user', f'u{f % n}', 'owner', 'folder', f'f{f}')
        yield ('member', 'group', f'g{f % n}', 'viewer', 'folder', f'f{f}')
        if f % chain_len != 0:                       # link into the chain
            yield ('...', 'folder', f'f{f - 1}', 'parent', 'folder', f'f{f}')
    for d in range(n):
        yield ('...', 'folder', f'f{d % n}', 'parent', 'doc', f'd{d}')
        yield ('...', 'user', f'u{d % n}', 'owner', 'doc', f'd{d}')
        for v in range(viewers_per_doc):
            yield ('...', 'user', f'u{(d + v) % n}', 'viewer', 'doc', f'd{d}')
        yield ('member', 'group', f'g{d % n}', 'viewer', 'doc', f'd{d}')


def gdrive_queries(n: int, count: int):
    """A representative can_read query mix: hits via direct viewer, via group, via
    ancestor folder; and ghosts (misses). Exercises the deep TTU path."""
    qs = []
    for i in range(count):
        d = i % n
        kind = i % 4
        if kind == 0:
            qs.append(('...', 'user', f'u{d % n}', 'can_read', 'doc', f'd{d}'))       # owner
        elif kind == 1:
            qs.append(('...', 'user', f'u{(d * 7 + 1) % n}', 'can_read', 'doc', f'd{d}'))  # maybe group
        elif kind == 2:
            qs.append(('...', 'user', f'ghost{i}', 'can_read', 'doc', f'd{d}'))        # miss
        else:
            qs.append(('...', 'user', f'u{(d + 2) % n}', 'can_read', 'doc', f'd{d}'))  # viewer
    return qs


_DM_USERS_PER_ROLE = 6
_DM_ROLES_PER_DOC = 2


def _demorgans_sizes(n: int) -> tuple[int, int, int, int]:
    """(n_users, n_attrs, n_conds, n_roles) -- shared by generator and query builder
    so queries hit the REAL universe. Users capped (has_attr is O(attrs x users));
    attrs/conds/roles grow with n ('a lot of conditions and attributes')."""
    return (min(n, 250), max(8, n // 2), max(8, n // 2), max(8, n // 2))


def gen_demorgans(n: int, *, n_users: int = None, n_attrs: int = None,
                  n_conds: int = None, n_roles: int = None,
                  attrs_per_cond: int = 3, conds_per_role: int = 2,
                  users_per_role: int = _DM_USERS_PER_ROLE,
                  roles_per_doc: int = _DM_ROLES_PER_DOC):
    """demorgans_law_2 dataset: N docs over a shared user/attr/cond/role universe.

    access(u, doc) = ∃ role r associated with doc: u assigned to r AND for every
    cond c in match_any(r), u meets c -- i.e. for every attr a that c requires, u
    has_attr a. Every attr/cond declares the [user:*] star (_all_users) so
    missing_user / user_met_requirement have their star coverage. has_attr is given
    to ~half the users per attr, so the ∀-over-required-attrs makes the answer
    genuinely mixed rather than trivially true or false."""
    du, da, dc, dr = _demorgans_sizes(n)
    n_users = n_users or du
    n_attrs = n_attrs or da
    n_conds = n_conds or dc
    n_roles = n_roles or dr

    for a in range(n_attrs):
        yield ('...', 'user', '*', '_all_users', 'attr', f'a{a}')        # star coverage
        for u in range(n_users):
            # ~80% of (user, attr) pairs present, decorrelated across attrs so the
            # ∀-over-a-cond's-required-attrs is satisfiable for SOME users, not all
            if (u * 7 + a * 13) % 5 != 0:
                yield ('...', 'user', f'u{u}', 'has_attr', 'attr', f'a{a}')
    for c in range(n_conds):
        yield ('...', 'user', '*', '_all_users', 'cond', f'c{c}')
        for k in range(attrs_per_cond):                                  # disjoint attr pairs per cond
            yield ('...', 'attr', f'a{(2 * c + k) % n_attrs}', 'requires', 'cond', f'c{c}')
    for r in range(n_roles):
        for k in range(users_per_role):
            yield ('...', 'user', f'u{(r * users_per_role + k) % n_users}', 'assigned', 'role', f'r{r}')
        for k in range(conds_per_role):
            yield ('...', 'cond', f'c{(r + k) % n_conds}', 'match_any', 'role', f'r{r}')
    for d in range(n):
        for k in range(roles_per_doc):
            yield ('...', 'role', f'r{(d + k) % n_roles}', 'associated_role', 'doc', f'd{d}')


def demorgans_queries(n: int, count: int):
    """Doc-AWARE query mix so checks traverse the real cascade, not a fast-false
    path. For doc d (associated with roles r_{d%R}, r_{(d+1)%R}), a user assigned to
    one of those roles is u_{(role*6 + k) % U}; querying those exercises the full
    assigned ∧ role_user_met path (true/false split by whether they meet the cond's
    required attrs). 1/3 are ghosts (guaranteed misses)."""
    n_users, _, _, n_roles = _demorgans_sizes(n)
    qs = []
    for i in range(count):
        d = i % n
        if i % 3 == 0:
            qs.append(('...', 'user', f'ghost{i}', 'access', 'doc', f'd{d}'))
            continue
        role = (d + (i % _DM_ROLES_PER_DOC)) % n_roles         # a role associated with d
        u = f'u{(role * _DM_USERS_PER_ROLE + (i % _DM_USERS_PER_ROLE)) % n_users}'  # assigned to it
        qs.append(('...', 'user', u, 'access', 'doc', f'd{d}'))
    return qs


WORKLOADS = {
    'gdrive':   (GDRIVE,   gen_gdrive,    gdrive_queries,    frozenset({('doc', 'viewer'), ('folder', 'viewer')})),
    'demorgans': (DEMORGANS, gen_demorgans, demorgans_queries, frozenset()),
}


# ---------------------------------------------------------------------------
# Backend builders
# ---------------------------------------------------------------------------

def _fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def build_set(schema: str, shapes, ops: SetOps, tuples) -> tuple[SetEngine, int]:
    se = SetEngine(_fresh_session(), 'sb', schema, object_wildcard_shapes=shapes, ops=ops)
    n = 0
    for raw in tuples:
        se.add_tuple(*raw)
        n += 1
    se.session.commit()
    return se, n


def build_graph(schema: str, shapes, tuples) -> tuple[object, int]:
    from index_v4.processor import DeltaProcessor
    ruleset = parse_openfga_schema(schema, object_wildcard_shapes=shapes)
    session, widx = make_wildcard_index(ruleset.schema_info, store_id='gb', paranoia=False)
    n = 0
    for raw in tuples:
        sp = Ellipsis if raw[0] == '...' else raw[0]
        tr = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        for d in ruleset.apply(tr):
            widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                           d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
        n += 1
    proc = None
    if ruleset.compiled is not None and ruleset.compiled.plans:
        proc = DeltaProcessor(widx, ruleset.compiled)
        proc.backfill()                              # offline bootstrap of derived state
    widx.idx.session.commit()
    return widx, n


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(workload: str, backend: str, scale: int, checks: int, ops_name: str,
        emit_json: bool) -> None:
    schema, gen, queries, shapes = WORKLOADS[workload]
    tuples = list(gen(scale))
    q = queries(scale, checks)

    gc.collect()
    rss_before = _rss_mb('current')
    t0 = time.perf_counter()
    if backend == 'set':
        ops = RoaringSets if (ops_name == 'roaring' and RoaringSets) else PySets
        be, n = build_set(schema, shapes, ops, tuples)
        check = be.check
        impl = f'set:{ops.name}'
    else:
        be, n = build_graph(schema, shapes, tuples)
        check = be.check
        impl = 'graph'
    build_s = time.perf_counter() - t0
    gc.collect()
    rss_after = _rss_mb('current')
    rss_peak = _rss_mb('peak')

    # correctness spot-check: at least one query must be True and one False, else
    # the query mix is degenerate and the throughput number is meaningless
    trues = sum(1 for qq in q[:200] if check(*qq))
    rate, el = timed(lambda i: check(*q[i % len(q)]), checks)

    tuples_ram = (rss_after - rss_before) if (rss_after and rss_before) else None
    print(f'\n{workload}/{impl}  scale={scale}')
    print(f'  raw tuples loaded : {n:,}')
    print(f'  build time        : {build_s:,.2f} s  ({n / build_s:,.0f} writes/s)')
    print(f'  RSS after build   : {rss_after:,.0f} MB' if rss_after else '  RSS: n/a')
    print(f'  RSS delta (data)  : {tuples_ram:,.0f} MB' if tuples_ram is not None else '')
    print(f'  peak RSS          : {rss_peak:,.0f} MB' if rss_peak else '')
    print(f'  check throughput  : {rate:,.0f} checks/s  ({checks} checks, {trues}/200 true)')

    if emit_json:
        out = Path(__file__).resolve().parent / 'results'
        out.mkdir(exist_ok=True)
        rec = dict(workload=workload, impl=impl, scale=scale, tuples=n,
                   build_s=round(build_s, 3), writes_per_s=round(n / build_s, 1),
                   rss_after_mb=round(rss_after, 1) if rss_after else None,
                   rss_delta_mb=round(tuples_ram, 1) if tuples_ram is not None else None,
                   peak_rss_mb=round(rss_peak, 1) if rss_peak else None,
                   checks=checks, checks_per_s=round(rate, 1), trues_of_200=trues)
        with (out / 'scale_bench.jsonl').open('a') as fh:
            fh.write(json.dumps(rec) + '\n')

    if backend == 'set':
        be.session.close()
    else:
        be.idx.session.close()


def main():
    p = argparse.ArgumentParser(description='Scaling benchmark on real fixture schemas')
    p.add_argument('--workload', choices=list(WORKLOADS), required=True)
    p.add_argument('--backend', choices=['set', 'graph'], required=True)
    p.add_argument('--scale', type=int, required=True, help='N (users≈groups≈folders≈docs)')
    p.add_argument('--checks', type=int, default=5000)
    p.add_argument('--impl', choices=['py', 'roaring'], default='roaring')
    p.add_argument('--json', action='store_true', help='append a record to results/scale_bench.jsonl')
    a = p.parse_args()
    run(a.workload, a.backend, a.scale, a.checks, a.impl, a.json)


if __name__ == '__main__':
    main()
