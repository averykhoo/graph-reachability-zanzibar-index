---
id: TK34
title: benchmarks/canary.py nightly perf tripwire: proposed, decision pending, never built
pri: LATER
size: M
deps: []
related: []
parent:
labels: [perf]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed:
---

`docs/gate-runbook.md:752-762` carries a concrete lightweight proposal: build one fixed store (e.g. `simple` N=8000), time a fixed op mix (K writes, K lookups, K checks), print rates, compare to a recorded baseline with a *generous* threshold (flag only a >2x regression). *"Runs in seconds"*. It sits between grepping test durations (free, noisy) and a full `scale_bench` sweep (accurate, minutes). The decision was left pending and `benchmarks/canary.py` still does not exist.

Filed `LATER` rather than `HOLD` because, unlike the appendix leads, this one is fully specified and the only open question is whether anyone wants it — and perf round 6 is about to land a series of changes with no regression tripwire behind them.

## Traps

⚠ **The runbook's own recommendation is DO NOT GATE ON IT.** Machine variance makes a hard threshold flaky; the proposal is a nightly alarm, not a gate phase. Wiring it into `formal/verify.sh` would make the gate flaky, which is worse than having no canary.

⚠ **A tripwire is an assurance step, so it can fail by passing.** A canary whose baseline is regenerated on every run alarms never. Sabotage it per [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md): plant a 2x slowdown and watch it fire, and record the literal output in the file's docstring.

## Read first

- [`docs/gate-runbook.md`](docs/gate-runbook.md)`:750-765` — the proposal and the recommendation not to gate on it
- `benchmarks/scale_bench.py` / `benchmarks/stmt_bench.py` — the existing instruments and the store builders to reuse
- [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) — mandatory before the tripwire is believed

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-19 (`GRB-H-1`, tier 3, sweep-h only); COVERAGE.md §C4 re-confirmed the file still does not exist. Proposal at docs/gate-runbook.md:752-762.
