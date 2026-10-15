---
id: TK150
title: quantify ZANZIBAR_MAX_CLOSURE_FANOUT cost: index cost of one write at 10k/100k/1M/more closure rows
brief: user ask 2026-10-14: measure one write's index cost at 10k/100k/1M closure rows, so the cap is a table
pri: NEXT
size: M
deps: []
related: [TK112, TK123]
parent:
labels: [perf]
source: hand
source_hash:
created: 2026-10-14
moved: 2026-10-14
updated: 2026-10-14
closed:
---

User request, 2026-10-14 (verbatim): "we should probably run a test on ZANZIBAR_MAX_CLOSURE_FANOUT to see what the cost is for 10k, 100k, 1m, maybe higher if its reasonably fast, so we can quantify the cost to the index".

Goal: put a measured number on what the closure fan-out cap protects against. For one write whose closure fan-out is about 10k, 100k and 1M closure rows (higher if the 1M point is reasonably fast), measure the index cost of that single write: wall time, rows written to the closure (and residue, if any), database size growth, and peak memory, on SQLite at least. Compare the uncapped write (`ZANZIBAR_MAX_CLOSURE_FANOUT=0`) with the refusal at the default cap. The point is to let a user choose the cap from a table rather than a guess.

Deliverables (named by the coordinator 2026-10-14; the benchmark agent started the same day, so neither file exists at filing):
- plan / results doc: `docs/closure-fanout-cost-2026-10-14.md` (ACTIVE-PLAN shape, `docs/README.md` sec 3; every figure date-stamped and labelled PROBE / READ / REASONED, with machine and backend stated).
- script: `benchmarks/fanout_cost_bench.py` (re-runnable, so the numbers are regenerable rather than restated).

Context: the cap is a SYNC-ADMISSION bound only (`TK112`); removals are never capped, and `ConnectedStore.catch_up` / non-bulk `build_index` run with it suspended (`CLAUDE.md` "Operational knobs"). `TK123` item 16 makes the fan-out refusal message name the env var. `TK143` / the Diataxis docs row are where the resulting table should end up for users.

Done when: the doc holds the measured table for 10k / 100k / 1M (and any higher point, or the reason it was not run), the script reproduces it, and the row's close message names the default-cap recommendation (keep, or change with the measured reason).

## Log
