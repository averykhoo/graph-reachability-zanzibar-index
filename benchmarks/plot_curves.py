"""Render log-log perf curves from scale_bench.jsonl -> results/perf_curves.png.

One panel per surface (write-time / check / lookup / reverse). Within a panel:
colour = workload, line style = set backend (solid roaring, dashed py); the graph
index is drawn as isolated markers (one scale each). Log-log axes make the scaling
slope visible directly -- a flat line is O(1), a -45deg line is O(N).

Optional analysis dep (matplotlib) -- see benchmarks/requirements-analysis.txt.
The dependency-free number-cruncher is benchmarks/analyze.py.

    python -m benchmarks.plot_curves
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RESULTS = Path(__file__).resolve().parent / 'results'
JSONL = RESULTS / 'scale_bench.jsonl'
OUT = RESULTS / 'perf_curves.png'

WL_COLOR = {'simple': '#4C78A8', 'gdrive': '#F58518', 'demorgans': '#54A24B'}
PANELS = [('write (build time, s)', 'build_s', True),
          ('check (ops/s)', 'checks_per_s', False),
          ('lookup (ops/s)', 'lookups_per_s', False),
          ('reverse (ops/s)', 'reverses_per_s', False)]


def load() -> list[dict]:
    return [json.loads(l) for l in JSONL.read_text().splitlines() if l.strip()]


def main() -> None:
    rows = load()
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    for ax, (title, field, _is_time) in zip(axes.flat, PANELS):
        # set-engine lines (roaring solid, py dashed), one per (impl, workload)
        for impl, style in [('set:roaring', '-'), ('set:py', '--')]:
            for wl, color in WL_COLOR.items():
                pts = sorted([(r['tuples'], r[field]) for r in rows
                              if r['impl'] == impl and r['workload'] == wl and r.get(field)])
                if len(pts) >= 2:
                    xs, ys = zip(*pts)
                    ax.plot(xs, ys, style, color=color, marker='o', ms=4,
                            label=f'{impl.split(":")[1]} {wl}')
        # graph index: isolated markers
        for wl, color in WL_COLOR.items():
            pts = [(r['tuples'], r[field]) for r in rows
                   if r['impl'] == 'graph' and r['workload'] == wl and r.get(field)]
            if pts:
                xs, ys = zip(*pts)
                ax.plot(xs, ys, '^', color=color, ms=9, mec='black', mew=0.6,
                        label=f'graph {wl}')
        ax.set_xscale('log'); ax.set_yscale('log')
        ax.set_title(title); ax.set_xlabel('raw tuples')
        ax.grid(True, which='both', ls=':', alpha=0.4)
        ax.legend(fontsize=6, ncol=2)
    fig.suptitle('Zanzibar index perf curves (log-log; paranoia=False, in-memory SQLite)',
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(OUT, dpi=120)
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
