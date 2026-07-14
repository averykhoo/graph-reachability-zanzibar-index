"""Micro-bench for MemberSet algebra (N4: _ext/_normalize copy elision).

Times union/intersect/subtract on star-heavy MemberSets with large populations,
under both SetOps. Runs in <30s total. Numbers are INDICATIVE ONLY — other
agents may be running tests concurrently; treat as order-of-magnitude signal.

Run: python -m benchmarks.microbench_memberset
"""

from __future__ import annotations

import time

from setengine import memberset as ms
from setengine.memberset import MemberSet
from setengine.setops import ALL_SETOPS

# Large populations across several shapes -> star-heavy, big ext() sets.
# Sized so the whole sweep stays well under 30s on both backends.
N = 6000
SHAPES = [('user', '...'), ('group', 'member'), ('org', 'admin'), ('team', 'lead')]
POP = {sh: tuple(range(i * N, i * N + N)) for i, sh in enumerate(SHAPES)}


def _pop(shape):
    return POP.get(shape, ())


def _build(ops):
    # a: covers first three shapes as stars, with a scattered pos/neg
    a = MemberSet(
        ops.freeze(range(5, 5 + 500)),
        frozenset(SHAPES[:3]),
        ops.freeze(range(100, 100 + 500)),
    )
    # b: covers last three shapes as stars, different pos/neg
    b = MemberSet(
        ops.freeze(range(N, N + 500)),
        frozenset(SHAPES[1:]),
        ops.freeze(range(N + 200, N + 700)),
    )
    return a, b


def bench(ops, iters=400):
    a, b = _build(ops)
    ops_ = ops
    results = {}
    for name, fn in (('union', ms.union), ('intersect', ms.intersect), ('subtract', ms.subtract)):
        t0 = time.perf_counter()
        for _ in range(iters):
            fn(a, b, ops_, _pop)
        results[name] = (time.perf_counter() - t0) / iters * 1e6  # us/op
    return results


def main():
    print(f'MemberSet algebra micro-bench (N={N} per shape, star-heavy). '
          f'INDICATIVE ONLY (concurrent activity).')
    for ops in ALL_SETOPS:
        r = bench(ops)
        print(f'  [{ops.name:8}] '
              + '  '.join(f'{k}={v:8.2f}us' for k, v in r.items()))


if __name__ == '__main__':
    main()
