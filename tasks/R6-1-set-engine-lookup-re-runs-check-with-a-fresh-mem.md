---
id: R6-1
title: set-engine lookup re-runs check with a fresh memo per candidate (91.4% of lookup)
pri: LATER
size: L
deps: []
related: []
parent: R6
labels: [perf]
source: docs/perf-round6-audit-2026-08.md
source_hash:
created: 2026-08-15
moved: 2026-08-21
updated: 2026-08-21
closed:
---

`setengine/engine.py::SetEngine.lookup`

**Measured (2026-08-17 motivating-measurement pass):** **74.1 `check` calls per `lookup`** and **91.4%** of lookup wall time; `lookup` degrades **2.5×** from scale 400→1600 while `check` stays flat. The biggest read ceiling in the round — and it is last in the land order anyway, on purpose.

**Verdict: MOTIVATED — still to land.** Position **10 of 10** in the audit’s recommended order (`R6-6 → R6-11 → R6-5 → R6-4 → R6-9 → R6-18 → R6-16 → R6-7 → R6-8 → R6-1`). That order is a RECOMMENDATION and is deliberately NOT encoded as `deps`; neither is `R6-16`’s co-design requirement, which is simultaneity rather than precedence and lives in the traps of `R6-16`/`R6-7`/`R6-8`. **No row in this round has `deps`.**

## Traps

⚠ **Read your id’s entry in [`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) — INCLUDING its verifier corrections — and that file’s §"Traps the numbers do not carry", before taking this id.** The audit’s own rule: *do not implement from titles alone*. Eighteen findings survived adversarial verification with **0 refuted**, but several impacts were downgraded, several fix sketches were corrected, and one fix was refuted outright while its finding stood.

⚠ **`R6-1` has the biggest read ceiling in round 6 and must NOT be landed from it.** The profile proves `check` *dominates*; it does not prove sharing *eliminates* — the redundant fraction is **unmeasured**. The naive shared memo is a **correctness bug by this audit’s own counterexample**: the finding stood, the proposed fix was REFUTED. Prototype the two-tier design in the verdict behind a measurement; do not land off the percentage.

⚠ Owes a `CORRESPONDENCE.md` §7 log entry even though forward `lookup` is unmodeled.

⚠ **Decompose every cumulative share before quoting it as a target.** `R6-10`’s headline 59.8% was CUMULATIVE; decomposed it was `_direct_incoming` 28.4% + `_nodes_by_ids` 30.7%, and the realised win came from the two SELECTs, not the headline. `R6-19` is the same trap caught earlier.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §`### R6-1` — the entry, **including its verifier corrections**
- the same file, §"Traps the numbers do not carry" — the five round-wide traps (counted from that section at generation time, not restated: `migrate.py` refuses to build if the bullet count moves)
- [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md) — verdicts, method, and the two honest limits (in-memory SQLite understates statement-count wins; cProfile depresses throughput)
- `setengine/engine.py::SetEngine.lookup` — the code
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the fence and the reopening rule
- `python task.py show R6` — the parent: round-wide order, traps and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21

**Migrated by `migrate.py`, and this row is a CORRECTION.** The first migration pass classified every id whose disposition string was not literally `closed` as retired, which wrote this live item into `retired-ids.txt` — an irreversible sink, since `task.py` refuses to re-mint a retired id. Its true disposition (`MOTIVATED, unlanded`) is taken from `docs/perf-round6-audit-2026-08.md`, the audit that owns these ids, not from the `R6` board row’s summary prose (which undercounts the land list by one and overcounts the declines by one). `parent: R6` makes the round a rollup: closing the last child is what reports that `R6` itself can close. **`created` (`2026-08-15`) is RECORDED, not approximated** — it is the date the audit doc that minted these ids states for itself; `moved` is the `R6` board row’s value.
