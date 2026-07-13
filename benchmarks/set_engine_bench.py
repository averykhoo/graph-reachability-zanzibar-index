"""
Set-engine benchmark (spec §8). NOT part of CI -- a script that prints a table.

Axes: SetOps implementation (roaring / py) x workload.

Workloads:
  (a) deep/narrow  -- many small usersets, nesting depth ~8, check-heavy.
  (b) wide/flat    -- 3 relations, large entity populations, star + exclusion, expand-heavy.
  (c) mixed batch  -- 10^4 checks answered from a single reused expand memo.

Reports ops/sec and peak RSS. Workload (a) also runs against the graph backend (read
AND write) so the memoization-spectrum trade is concrete: the graph memoizes the whole
closure at write time (fast reads, heavy writes); the set engine memoizes nothing across
queries (cheap writes, work moved to read time).

Deterministic: fixed sizes via CLI flags, no RNG in the measured paths.

Usage:
    python -m benchmarks.set_engine_bench --scale 1
    python -m benchmarks.set_engine_bench --depth 8 --chains 200 --pop 100000 --checks 10000
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from setengine import SetEngine, PySets, RoaringSets
from setengine.setops import SetOps
from zanzibar_utils_v1 import parse_openfga_schema, Entity, RelationalTriple
from tests.wildcard_helpers import make_wildcard_index

# Shared plumbing (RSS reader, session, time-boxed timing) -- see benchmarks/_harness.py.
# peak_rss_mb / _fresh_session are thin adapters kept so the call sites below read
# unchanged; timed() is re-exported (its 3rd return value, iters-completed, is unused here).
from benchmarks._harness import rss_mb, timed, fresh_session as _fresh_session


def peak_rss_mb() -> float | None:
    return rss_mb('peak')


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

DEEP_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member]
'''

WIDE_SCHEMA = '''
type user
type doc
  relations
    define public: [user:*]
    define blocked: [user]
    define viewer: public but not blocked
'''


# ---------------------------------------------------------------------------
# Workload (a): deep/narrow, check-heavy
# ---------------------------------------------------------------------------

def build_deep_set(ops: SetOps, depth: int, chains: int) -> SetEngine:
    session = _fresh_session()
    se = SetEngine(session, 'deep', DEEP_SCHEMA, ops=ops)
    for c in range(chains):
        se.add_tuple('...', 'user', f'u{c}', 'member', 'group', f'g{c}_0')
        for d in range(depth):
            se.add_tuple('member', 'group', f'g{c}_{d}', 'member', 'group', f'g{c}_{d + 1}')
    session.commit()
    return se


def build_deep_graph(depth: int, chains: int):
    ruleset = parse_openfga_schema(DEEP_SCHEMA)
    # paranoia=False: benchmarks measure index maintenance, not the invariant
    # checker (wildcard_helpers/CLAUDE.md require this here -- paranoia runs the
    # full I1-I13 sweep plus the per-pair outbox BFS around every commit)
    session, widx = make_wildcard_index(ruleset.schema_info, store_id='deep',
                                        paranoia=False)

    def ingest(sp, st, sn, rel, ot, on):
        tr = RelationalTriple(Entity(st, sn), rel, Entity(ot, on), Ellipsis if sp == '...' else sp)
        for d in ruleset.apply(tr):
            widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                           d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)

    for c in range(chains):
        ingest('...', 'user', f'u{c}', 'member', 'group', f'g{c}_0')
        for d in range(depth):
            ingest('member', 'group', f'g{c}_{d}', 'member', 'group', f'g{c}_{d + 1}')
    session.commit()
    return session, widx


# ---------------------------------------------------------------------------
# Workload (b): wide/flat, expand-heavy
# ---------------------------------------------------------------------------

def build_wide(ops: SetOps, pop: int, blocked: int) -> SetEngine:
    session = _fresh_session()
    se = SetEngine(session, 'wide', WIDE_SCHEMA, ops=ops)
    se.add_tuple('...', 'user', '*', 'public', 'doc', 'd')     # everyone public
    for i in range(blocked):
        se.add_tuple('...', 'user', f'blk{i}', 'blocked', 'doc', 'd')
    # give the population concrete identity so materialisation has real ids to move
    for i in range(pop):
        se.add_tuple('...', 'user', f'u{i}', 'blocked', 'doc', 'other')
    session.commit()
    return se


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(ops_list: list[SetOps], depth: int, chains: int, pop: int, blocked: int, checks: int):
    print(f'\nset-engine benchmark  (depth={depth} chains={chains} pop={pop} '
          f'blocked={blocked} checks={checks})')
    print('=' * 78)
    header = f'{"workload":<22}{"impl":<10}{"ops/sec":>14}{"elapsed(s)":>14}{"peakRSS(MB)":>14}'

    # (a) deep/narrow check-heavy -- set engine
    print('\n(a) deep/narrow, check-heavy')
    print(header)
    for ops in ops_list:
        se = build_deep_set(ops, depth, chains)
        rate, el, _ = timed(lambda i: se.check('...', 'user', f'u{i % chains}', 'member',
                                               'group', f'g{i % chains}_{depth}'), checks)
        rss = peak_rss_mb()
        print(f'{"deep check":<22}{ops.name:<10}{rate:>14,.0f}{el:>14.3f}'
              f'{(f"{rss:.0f}" if rss else "n/a"):>14}')
        se.session.close()

    # (a') graph comparison -- read AND write
    session, widx = build_deep_graph(depth, chains)
    rate, el, _ = timed(lambda i: widx.check('...', 'user', f'u{i % chains}', 'member',
                                             'group', f'g{i % chains}_{depth}'), checks)
    rss = peak_rss_mb()
    print(f'{"deep check":<22}{"graph":<10}{rate:>14,.0f}{el:>14.3f}'
          f'{(f"{rss:.0f}" if rss else "n/a"):>14}')
    session.close()

    # write comparison for (a): closure (graph) vs raw (set engine)
    print('\n(a-write) build cost: closure materialisation vs raw tuples')
    print(header)
    for ops in ops_list:
        t0 = time.perf_counter()
        se = build_deep_set(ops, depth, chains)
        el = time.perf_counter() - t0
        writes = chains * (depth + 1)
        print(f'{"deep write":<22}{ops.name:<10}{writes / el:>14,.0f}{el:>14.3f}'
              f'{(f"{peak_rss_mb():.0f}" if peak_rss_mb() else "n/a"):>14}')
        se.session.close()
    t0 = time.perf_counter()
    session, widx = build_deep_graph(depth, chains)
    el = time.perf_counter() - t0
    writes = chains * (depth + 1)
    print(f'{"deep write":<22}{"graph":<10}{writes / el:>14,.0f}{el:>14.3f}'
          f'{(f"{peak_rss_mb():.0f}" if peak_rss_mb() else "n/a"):>14}')
    session.close()

    # (b) wide/flat expand-heavy -- set engine only: bulk expand is its native op
    # (post-P7 the graph ingests boolean schemas too, but its read surface here is
    # point probes / lookup, not a bulk MemberSet expand)
    print('\n(b) wide/flat, expand-heavy  (set engine only: bulk expand is its native op)')
    print(header)
    for ops in ops_list:
        se = build_wide(ops, pop, blocked)
        rate, el, _ = timed(lambda i: se.expand('viewer', 'doc', 'd'), max(1, checks // 100))
        rss = peak_rss_mb()
        print(f'{"wide expand":<22}{ops.name:<10}{rate:>14,.1f}{el:>14.3f}'
              f'{(f"{rss:.0f}" if rss else "n/a"):>14}')
        se.session.close()

    # (c) mixed batch -- 10^4 checks answered from one reused expand memo
    print('\n(c) mixed batch, 10^4 membership answers from a single reused expand memo')
    print(header)
    for ops in ops_list:
        se = build_wide(ops, pop, blocked)
        m = se.expand('viewer', 'doc', 'd')                    # one expand, reused
        rate, el, _ = timed(lambda i: m.contains_entity(i % max(1, pop), 'user'), checks)
        rss = peak_rss_mb()
        print(f'{"batch membership":<22}{ops.name:<10}{rate:>14,.0f}{el:>14.3f}'
              f'{(f"{rss:.0f}" if rss else "n/a"):>14}')
        se.session.close()
    print()


def main():
    p = argparse.ArgumentParser(description='Set-engine benchmark (spec §8)')
    p.add_argument('--scale', type=float, default=1.0, help='multiplier for default sizes')
    p.add_argument('--depth', type=int, default=None)
    p.add_argument('--chains', type=int, default=None)
    p.add_argument('--pop', type=int, default=None)
    p.add_argument('--blocked', type=int, default=None)
    p.add_argument('--checks', type=int, default=None)
    p.add_argument('--impl', choices=['both', 'py', 'roaring'], default='both')
    a = p.parse_args()

    s = a.scale
    depth = a.depth if a.depth is not None else 8
    chains = a.chains if a.chains is not None else int(200 * s)
    pop = a.pop if a.pop is not None else int(100_000 * s)
    blocked = a.blocked if a.blocked is not None else int(1_000 * s)
    checks = a.checks if a.checks is not None else int(10_000 * s)

    if a.impl == 'py':
        ops_list = [PySets]
    elif a.impl == 'roaring':
        ops_list = [RoaringSets] if RoaringSets else [PySets]
    else:
        ops_list = [PySets] + ([RoaringSets] if RoaringSets else [])

    run(ops_list, depth, chains, pop, blocked, checks)


if __name__ == '__main__':
    main()
