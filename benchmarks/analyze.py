"""Fit perf curves from benchmarks/results/scale_bench.jsonl and print markdown.

Two analyses:
  1. Scaling exponents -- for each (impl, workload, surface) with >=3 scale points,
     a log-log least-squares fit. Throughput surfaces (check/lookup/reverse) are fit
     as rate vs tuples; the per-op COST exponent is -slope (rate ~ N^slope <=>
     cost ~ N^-slope). Write is fit as build_time vs tuples (slope ~1 => linear load).
  2. PySets vs RoaringSets -- per-scale rate ratios (roaring / py) and a geometric
     mean per surface, over the set-engine rows.

Pure Python (no numpy in this env). Deterministic; reads the jsonl only.

    python -m benchmarks.analyze [path/to/scale_bench.jsonl]

With no argument it reads the committed baseline (``results/scale_bench.jsonl``);
pass a path (or a bare filename resolved under ``results/``) to fit a different
run, e.g. ``benchmarks/analyze.py scale_bench_2026-07-15.jsonl``.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

_RESULTS = Path(__file__).resolve().parent / 'results'
JSONL = _RESULTS / 'scale_bench.jsonl'


def _resolve(arg: str) -> Path:
    p = Path(arg)
    return p if p.is_absolute() or p.exists() else (_RESULTS / arg)

# (surface label, jsonl rate field, is_throughput). Write is fit on build_s (time).
THROUGHPUT = [('check', 'checks_per_s'), ('lookup', 'lookups_per_s'),
              ('reverse', 'reverses_per_s')]


def linfit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Least squares y = a + b*x. Returns (slope b, intercept a, R^2)."""
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if denom == 0:
        return float('nan'), float('nan'), float('nan')
    b = (n * sxy - sx * sy) / denom
    a = (sy - b * sx) / n
    ybar = sy / n
    ss_tot = sum((y - ybar) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot else float('nan')
    return b, a, r2


def cost_law(cost_exp: float) -> str:
    """Human label for a per-op cost exponent (cost ~ N^cost_exp)."""
    if abs(cost_exp) < 0.15:
        return 'O(1)  flat'
    if abs(cost_exp - 1.0) < 0.15:
        return 'O(N)  linear'
    if abs(cost_exp - 0.5) < 0.15:
        return 'O(sqrt N)'
    return f'~O(N^{cost_exp:.2f})'


def load(path: Path = JSONL) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def scaling_section(rows: list[dict]) -> None:
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        groups.setdefault((r['impl'], r['workload']), []).append(r)

    print('## Scaling exponents (log-log fit)\n')
    print('Per-op cost exponent = -(throughput slope); write is time-vs-tuples.\n')
    print('| impl | workload | surface | pts | slope | R2 | law |')
    print('|---|---|---|--:|--:|--:|---|')
    for (impl, wl), rs in sorted(groups.items()):
        rs = sorted(rs, key=lambda r: r['tuples'])
        xs = [math.log10(r['tuples']) for r in rs]
        if len(rs) < 3:
            print(f'| {impl} | {wl} | (all) | {len(rs)} | - | - | single/low N, no fit |')
            continue
        # write: time vs tuples (build_s on scale_bench/graph rows; the bulk bench's
        # set rows carry rebuild_s instead and would TypeError on log10(None))
        pts = [(x, math.log10(t)) for x, r in zip(xs, rs)
               if (t := (r.get('build_s') or r.get('rebuild_s')))]
        if len(pts) >= 3:
            b, _, r2 = linfit([p[0] for p in pts], [p[1] for p in pts])
            print(f'| {impl} | {wl} | write(time) | {len(pts)} | {b:+.2f} | {r2:.3f} | {cost_law(b)} |')
        # throughput surfaces: rate vs tuples; cost exponent = -slope
        for label, field in THROUGHPUT:
            pts = [(x, math.log10(r[field])) for x, r in zip(xs, rs) if r.get(field)]
            if len(pts) < 3:
                continue
            b, _, r2 = linfit([p[0] for p in pts], [p[1] for p in pts])
            print(f'| {impl} | {wl} | {label} | {len(pts)} | {b:+.2f} | {r2:.3f} | {cost_law(-b)} |')
    print()


def pyroaring_section(rows: list[dict]) -> None:
    # index set rows by (workload, scale) -> {impl: row}
    idx: dict[tuple[str, int], dict[str, dict]] = {}
    for r in rows:
        if not r['impl'].startswith('set:'):
            continue
        idx.setdefault((r['workload'], r['scale']), {})[r['impl']] = r

    print('## PySets vs RoaringSets (rate ratio = roaring / py)\n')
    print('>1 means RoaringSets is faster; <1 means PySets is faster.\n')
    print('| workload | tuples | write | check | lookup | reverse |')
    print('|---|--:|--:|--:|--:|--:|')
    geo: dict[str, list[float]] = {s: [] for s in ['writes_per_s', 'checks_per_s',
                                                   'lookups_per_s', 'reverses_per_s']}
    for (wl, scale), impls in sorted(idx.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        rr, py = impls.get('set:roaring'), impls.get('set:py')
        if not (rr and py):
            continue
        cells = []
        for field in ['writes_per_s', 'checks_per_s', 'lookups_per_s', 'reverses_per_s']:
            if py.get(field):
                ratio = rr[field] / py[field]
                geo[field].append(ratio)
                cells.append(f'{ratio:.2f}x')
            else:
                cells.append('-')
        print(f'| {wl} | {rr["tuples"]:,} | ' + ' | '.join(cells) + ' |')

    def gm(v: list[float]) -> str:
        if not v:
            return '-'
        return f'{math.exp(sum(math.log(x) for x in v) / len(v)):.2f}x'
    print(f'| **geomean** | | {gm(geo["writes_per_s"])} | {gm(geo["checks_per_s"])} '
          f'| {gm(geo["lookups_per_s"])} | {gm(geo["reverses_per_s"])} |')
    print()


def main() -> None:
    path = _resolve(sys.argv[1]) if len(sys.argv) > 1 else JSONL
    rows = load(path)
    print(f'<!-- generated by benchmarks/analyze.py over {len(rows)} rows '
          f'from {path.name} -->\n')
    scaling_section(rows)
    pyroaring_section(rows)


if __name__ == '__main__':
    main()
