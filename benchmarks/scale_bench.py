"""Scaling benchmark: do the read surfaces (check / lookup / reverse) and the
write path grow with tuple count? (review-3 follow-up, extended for lookup.)

Unlike ``set_engine_bench.py`` (synthetic deep/wide micro-schemas), this runs the
REAL fixture schemas at increasing data sizes and reports, per backend:

  * tuple count actually loaded,
  * build time (raw-tuple load; for the graph, closure materialisation + one
    ``backfill()`` for boolean schemas) -- the WRITE surface,
  * peak/current RSS after build (memory footprint at scale),
  * throughput of the three read surfaces over fixed, representative query mixes:
      - ``check``          -- one (subject, relation, object) point query,
      - ``lookup``         -- everything a subject can reach,
      - ``lookup_reverse`` -- everything that can reach an object,
  * whether each stays FLAT or DEGRADES as N grows (the OpenFGA question).

Three schema-complexity tiers:
  * ``simple``   -- a direct-only ``define viewer: [user]`` floor: no hierarchy,
                    no booleans. Isolates the per-op constant cost from traversal.
  * ``gdrive``   -- pure-union TTU/computed hierarchy (folders, groups, docs). The
                    graph index materialises the full closure; the set engine walks
                    it on the fly. Local checks touch a bounded neighbourhood
                    regardless of N.
  * ``demorgans``-- demorgans_law_2.fga: a 5-level boolean+TTU derived cascade over
                    attrs/conds/roles. Graph maintains derived state via the
                    processor; set engine evaluates the booleans pointwise.

Note on ``lookup``: the set engine's ``lookup`` is a full-store candidate sweep
(one ``check`` per interned key -- O(stored tuples) per call), so it is EXPECTED to
degrade with N, unlike ``check``. The graph walks the materialised closure, so its
lookup is bounded by the reachable set. That asymmetry is the headline this bench
now captures. Timing is time-boxed (``--time-box``) so a slow lookup at large N
can't hang the sweep.

Run ONE (workload, backend, scale) per process so RSS is clean:

    python -m benchmarks.scale_bench --workload gdrive    --backend set   --scale 1000
    python -m benchmarks.scale_bench --workload gdrive    --backend graph --scale 250
    python -m benchmarks.scale_bench --workload demorgans --backend set   --scale 400
    python -m benchmarks.scale_bench --workload simple    --backend set   --scale 10000

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

from setengine import PySets, RoaringSets

from benchmarks._harness import rss_mb, timed, build_set, build_graph


# ---------------------------------------------------------------------------
# Schemas (the real fixtures + a direct-only floor)
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

# The complexity floor: one direct relation, no hierarchy, no booleans, no stars.
# Every read surface here measures raw per-op overhead with a trivial neighbourhood.
SIMPLE = '''
type user
type doc
  relations
    define viewer: [user]
'''


# ---------------------------------------------------------------------------
# Data + query generators (deterministic; tuples are raw septuples)
# ---------------------------------------------------------------------------

# --- simple (direct-only floor) --------------------------------------------

_SIMPLE_VIEWERS = 4


def gen_simple(n: int):
    """N docs over a user pool of N; each doc has _SIMPLE_VIEWERS direct viewers."""
    for d in range(n):
        for v in range(_SIMPLE_VIEWERS):
            yield ('...', 'user', f'u{(d + v) % n}', 'viewer', 'doc', f'd{d}')


def simple_checks(n: int, count: int):
    qs = []
    for i in range(count):
        d = i % n
        if i % 3 == 2:
            qs.append(('...', 'user', f'ghost{i}', 'viewer', 'doc', f'd{d}'))     # miss
        else:
            qs.append(('...', 'user', f'u{(d + (i % _SIMPLE_VIEWERS)) % n}', 'viewer', 'doc', f'd{d}'))  # hit
    return qs


def simple_lookups(n: int, count: int):
    """Subjects to expand. Reals reach ~_SIMPLE_VIEWERS docs; ghosts reach nothing."""
    return [('...', 'user', f'ghost{i}') if i % 4 == 2 else ('...', 'user', f'u{i % n}')
            for i in range(count)]


def simple_reverses(n: int, count: int):
    return [('viewer', 'doc', f'ghost{i}') if i % 4 == 2 else ('viewer', 'doc', f'd{i % n}')
            for i in range(count)]


# --- gdrive (pure-union hierarchy) -----------------------------------------

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


def gdrive_lookups(n: int, count: int):
    """Subjects to expand: a user reaches its groups, owned folders/docs, and
    viewer-granted docs. Ghosts reach nothing."""
    return [('...', 'user', f'ghost{i}') if i % 4 == 2 else ('...', 'user', f'u{i % n}')
            for i in range(count)]


def gdrive_reverses(n: int, count: int):
    """Reverse targets: who can_read a doc (deep TTU fan-in), who is viewer of a
    folder (group + direct), and ghost objects (empty)."""
    qs = []
    for i in range(count):
        kind = i % 3
        if kind == 0:
            qs.append(('can_read', 'doc', f'd{i % n}'))
        elif kind == 1:
            qs.append(('viewer', 'folder', f'f{i % n}'))
        else:
            qs.append(('can_read', 'doc', f'ghost{i}'))     # miss
    return qs


# --- demorgans (boolean + TTU cascade) -------------------------------------

_DM_USERS_PER_ROLE = 6
_DM_ROLES_PER_DOC = 2
_DM_ATTRS_PER_COND = 3
_DM_CONDS_PER_ROLE = 2


def _demorgans_sizes(n: int) -> tuple[int, int, int, int]:
    """(n_users, n_attrs, n_conds, n_roles) -- shared by generator and query builder
    so queries hit the REAL universe. Users capped (has_attr is O(attrs x users));
    attrs/conds/roles grow with n ('a lot of conditions and attributes')."""
    return (min(n, 250), max(8, n // 2), max(8, n // 2), max(8, n // 2))


def gen_demorgans(n: int):
    """demorgans_law_2 dataset: N docs over a shared user/attr/cond/role universe.

    access(u, doc) = ∃ role r associated with doc: u assigned to r AND for every
    cond c in match_any(r), u meets c -- i.e. for every attr a that c requires, u
    has_attr a. Every attr/cond declares the [user:*] star (_all_users) so
    missing_user / user_met_requirement have their star coverage. has_attr is given
    to ~half the users per attr, so the ∀-over-required-attrs makes the answer
    genuinely mixed rather than trivially true or false.

    Sizes and fan-outs come ONLY from _demorgans_sizes and the _DM_* module
    constants — demorgans_queries assumes exactly this shape, so the generator
    deliberately takes no overrides."""
    n_users, n_attrs, n_conds, n_roles = _demorgans_sizes(n)

    for a in range(n_attrs):
        yield ('...', 'user', '*', '_all_users', 'attr', f'a{a}')        # star coverage
        for u in range(n_users):
            # ~80% of (user, attr) pairs present, decorrelated across attrs so the
            # ∀-over-a-cond's-required-attrs is satisfiable for SOME users, not all
            if (u * 7 + a * 13) % 5 != 0:
                yield ('...', 'user', f'u{u}', 'has_attr', 'attr', f'a{a}')
    for c in range(n_conds):
        yield ('...', 'user', '*', '_all_users', 'cond', f'c{c}')
        for k in range(_DM_ATTRS_PER_COND):                              # disjoint attr pairs per cond
            yield ('...', 'attr', f'a{(2 * c + k) % n_attrs}', 'requires', 'cond', f'c{c}')
    for r in range(n_roles):
        for k in range(_DM_USERS_PER_ROLE):
            yield ('...', 'user', f'u{(r * _DM_USERS_PER_ROLE + k) % n_users}', 'assigned', 'role', f'r{r}')
        for k in range(_DM_CONDS_PER_ROLE):
            yield ('...', 'cond', f'c{(r + k) % n_conds}', 'match_any', 'role', f'r{r}')
    for d in range(n):
        for k in range(_DM_ROLES_PER_DOC):
            yield ('...', 'role', f'r{(d + k) % n_roles}', 'associated_role', 'doc', f'd{d}')


def demorgans_queries(n: int, count: int):
    """Doc-AWARE query mix so checks traverse the real cascade, not a fast-false
    path. For doc d (associated with roles r_{d%R}, r_{(d+1)%R}), a user assigned to
    one of those roles is u_{(role*6 + k) % U}; querying those exercises the full
    assigned ∧ role_user_met path (true/false split by whether they meet the cond's
    required attrs). 1/3 are ghosts (guaranteed misses).

    Role-slot and user-slot come from a multiplicative hash of i, NOT from linear
    i-arithmetic: any linear stride (i % 2, i % 3, a non-ghost counter, ...)
    aliases against d = i % n at some scale — e.g. i % 2 parity-locks every even
    n to even role indices only — silently shrinking the queried role universe.
    Hashing is still fully deterministic (no RNG)."""
    n_users, _, _, n_roles = _demorgans_sizes(n)
    qs = []
    for i in range(count):
        d = i % n
        if i % 3 == 0:
            qs.append(('...', 'user', f'ghost{i}', 'access', 'doc', f'd{d}'))
            continue
        h = (i * 0x9E3779B1) & 0xFFFFFFFF                      # Fibonacci hash of i
        role = (d + ((h >> 7) % _DM_ROLES_PER_DOC)) % n_roles  # a role associated with d
        u = f'u{(role * _DM_USERS_PER_ROLE + ((h >> 13) % _DM_USERS_PER_ROLE)) % n_users}'  # assigned to it
        qs.append(('...', 'user', u, 'access', 'doc', f'd{d}'))
    return qs


def demorgans_lookups(n: int, count: int):
    """Subjects to expand: a real user reaches its attrs (has_attr) and roles
    (assigned); ghosts reach nothing."""
    n_users, _, _, _ = _demorgans_sizes(n)
    return [('...', 'user', f'ghost{i}') if i % 4 == 2 else ('...', 'user', f'u{i % n_users}')
            for i in range(count)]


def demorgans_reverses(n: int, count: int):
    """Reverse targets: who has ``access`` to a doc (the boolean cascade + star
    markers), and ghost docs (empty)."""
    return [('access', 'doc', f'ghost{i}') if i % 3 == 2 else ('access', 'doc', f'd{i % n}')
            for i in range(count)]


WORKLOADS = {
    'simple': dict(schema=SIMPLE, shapes=frozenset(), gen=gen_simple,
                   checks=simple_checks, lookups=simple_lookups, reverses=simple_reverses),
    'gdrive': dict(schema=GDRIVE, shapes=frozenset({('doc', 'viewer'), ('folder', 'viewer')}),
                   gen=gen_gdrive, checks=gdrive_queries, lookups=gdrive_lookups,
                   reverses=gdrive_reverses),
    'demorgans': dict(schema=DEMORGANS, shapes=frozenset(), gen=gen_demorgans,
                      checks=demorgans_queries, lookups=demorgans_lookups,
                      reverses=demorgans_reverses),
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _rsz(result) -> int:
    """Result magnitude: concrete ids + symbolic markers (both backends)."""
    return len(result.node_ids) + len(result.markers)


def run(workload: str, backend: str, scale: int, checks: int, lookups: int,
        time_box: float, ops_name: str, emit_json: bool) -> None:
    spec = WORKLOADS[workload]
    schema, shapes = spec['schema'], spec['shapes']
    tuples = list(spec['gen'](scale))
    cq = spec['checks'](scale, checks)
    lq = spec['lookups'](scale, lookups)
    rq = spec['reverses'](scale, lookups)

    gc.collect()
    rss_before = rss_mb('current')
    t0 = time.perf_counter()
    if backend == 'set':
        ops = RoaringSets if (ops_name == 'roaring' and RoaringSets) else PySets
        be, n = build_set(schema, shapes, ops, tuples)
        impl = f'set:{ops.name}'
    else:
        be, n = build_graph(schema, shapes, tuples)
        impl = 'graph'
    build_s = time.perf_counter() - t0
    gc.collect()
    rss_after = rss_mb('current')
    rss_peak = rss_mb('peak')

    check, lookup, reverse = be.check, be.lookup, be.lookup_reverse

    # check correctness spot-check: at least one True and one False over the sample,
    # else the query mix is degenerate and the throughput number is meaningless.
    sample = [bool(check(*qq)) for qq in cq[:200]]
    trues = sum(sample)
    assert 0 < trues < len(sample), (
        f'degenerate check mix ({trues}/{len(sample)} true): throughput would be meaningless')
    # Per-query answer signature over the sample: equal sigs for two backends at the
    # same (workload, scale) prove per-query agreement on these 200 queries.
    answers_sig = f'{int("".join("01"[b] for b in sample), 2):x}'

    # lookup / reverse non-degeneracy: a small pre-sample (kept tiny because set
    # lookup is O(stored tuples) per call) must produce at least one non-empty
    # result, else we'd be timing an all-empty fast path. Also captures mean size.
    l_sizes = [_rsz(lookup(*qq)) for qq in lq[:5]]
    r_sizes = [_rsz(reverse(*qq)) for qq in rq[:5]]
    assert any(s > 0 for s in l_sizes), 'degenerate lookup mix (all empty)'
    assert any(s > 0 for s in r_sizes), 'degenerate reverse mix (all empty)'

    check_rate, _, check_done = timed(lambda i: check(*cq[i % len(cq)]), checks, time_box)
    lookup_rate, _, lookup_done = timed(lambda i: lookup(*lq[i % len(lq)]), lookups, time_box)
    reverse_rate, _, reverse_done = timed(lambda i: reverse(*rq[i % len(rq)]), lookups, time_box)

    tuples_ram = (rss_after - rss_before) if (rss_after and rss_before) else None
    print(f'\n{workload}/{impl}  scale={scale}')
    print(f'  raw tuples loaded : {n:,}')
    print(f'  build (write)     : {build_s:,.2f} s  ({n / build_s:,.0f} writes/s)')
    print(f'  RSS after build   : {rss_after:,.0f} MB' if rss_after else '  RSS: n/a')
    print(f'  RSS delta (data)  : {tuples_ram:,.0f} MB' if tuples_ram is not None else '')
    print(f'  peak RSS          : {rss_peak:,.0f} MB' if rss_peak else '')
    print(f'  check             : {check_rate:>12,.1f} /s  ({check_done} done, {trues}/200 true)')
    print(f'  lookup            : {lookup_rate:>12,.1f} /s  ({lookup_done} done, ~{max(l_sizes)} max result)')
    print(f'  lookup_reverse    : {reverse_rate:>12,.1f} /s  ({reverse_done} done, ~{max(r_sizes)} max result)')
    print(f'  answers signature : {answers_sig}')

    if emit_json:
        out = Path(__file__).resolve().parent / 'results'
        out.mkdir(exist_ok=True)
        rec = dict(workload=workload, impl=impl, scale=scale, tuples=n,
                   build_s=round(build_s, 3), writes_per_s=round(n / build_s, 1),
                   rss_after_mb=round(rss_after, 1) if rss_after else None,
                   rss_delta_mb=round(tuples_ram, 1) if tuples_ram is not None else None,
                   peak_rss_mb=round(rss_peak, 1) if rss_peak else None,
                   checks=check_done, checks_per_s=round(check_rate, 1),
                   lookups=lookup_done, lookups_per_s=round(lookup_rate, 2),
                   reverses=reverse_done, reverses_per_s=round(reverse_rate, 2),
                   mean_lookup_size=round(sum(l_sizes) / len(l_sizes), 1),
                   mean_reverse_size=round(sum(r_sizes) / len(r_sizes), 1),
                   trues_of_200=trues, answers_sig=answers_sig)
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
    p.add_argument('--lookups', type=int, default=500,
                   help='iteration cap for lookup / lookup_reverse (also time-boxed)')
    p.add_argument('--time-box', type=float, default=20.0, dest='time_box',
                   help='per-surface wall-clock cap (s); a slow lookup at large N stops here')
    p.add_argument('--impl', choices=['py', 'roaring'], default='roaring')
    p.add_argument('--json', action='store_true', help='append a record to results/scale_bench.jsonl')
    a = p.parse_args()
    run(a.workload, a.backend, a.scale, a.checks, a.lookups, a.time_box, a.impl, a.json)


if __name__ == '__main__':
    main()
