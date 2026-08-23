---
id: TK48
title: perf audit banner says 'ten to land, five declined'; its own body says eleven and four
pri: LATER
size: S
deps: []
related: []
parent: R6
labels: [docs]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed:
---

The status banner of `docs/perf-round6-audit-2026-08.md` (`:3-5`) reads *"ALL EIGHTEEN are now MEASURED (2026-08-17) — ten recommended to land in a stated order, five declined on an upper bound, three unreachable by any benchmarked workload."* The document's own body says **eleven** ids in the recommended order and **four** declines (exactly four `NOT MOTIVATED` verdict rows). Both splits sum to 18, which is how it survived review.

This is a live `ZT-P3-5` — a stale figure in a durable place — in a `docs/` file that is the first thing a perf session reads, and it is the SOURCE the task corpus was generated from. The corpus correctly declined to inherit the banner's split and counted the children instead; the doc was never corrected.

## Traps

⚠ **Correct the banner from the BODY, not from any other row or task.** The body is the measurement; everything else is a restatement, and a restatement is what produced this. The safest form carries no number at all and points at the tables.

⚠ **`R6`'s parent-row prose quotes the wrong cell ON PURPOSE.** It records "9 to land, 5 declined" as the board cell it replaced, with the correction beside it. That is provenance; do not "fix" it into agreement and destroy the record of the discrepancy.

⚠ **This is a `docs/` edit and therefore reviewed and separate.** It is not a by-product of any perf item; file the correction on its own, with the derivation in the commit message.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md)`:3-5` — the banner; then the verdict tables and the recommended-order list that contradict it
- `.scratch/tasktool/PROOF2.md` §1 — the independent re-derivation (11 / 4 / 3, twice, from the audit alone)
- `python task.py show R6` — the parent row, whose body records the same discrepancy as provenance
- `python task.py list --parent R6` — the census, counted rather than restated

## Log

### 2026-08-21b

**Provenance.** Surfaced by this project's own work: PROOF2.md §1 re-derived the census from the audit body alone (11 ids in 10 steps, 4 NOT MOTIVATED rows, 3 unreachable = the audit's own "ALL EIGHTEEN") and found the banner contradicts it. Banner re-read this pass at docs/perf-round6-audit-2026-08.md:3-5.
