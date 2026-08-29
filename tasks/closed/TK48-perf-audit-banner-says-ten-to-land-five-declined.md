---
id: TK48
title: perf audit banner says 'ten to land, five declined'; its own body says eleven and four
brief:
pri: LATER
size: S
deps: []
related: []
parent: R6
labels: [docs]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
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

### 2026-08-24d

SECOND DEFECT IN THE SAME BANNER, found while closing TK47 (2026-08-24d): docs/perf-round6-audit-2026-08.md:3 also says 'Nothing here is landed', and that is now false twice over -- R6-10 landed 2026-08-20b (2.54x) and R6-6 landed 2026-08-24d (4.75 -> 1.75 statements/check). Both clauses of that banner are stale, so fix them in ONE reviewed edit rather than two. This row's own trap still binds: correct from the BODY (the verdict tables and the recommended-order list), and the safest form of the count clause carries no number at all. The landed items now carry a LANDED marker in the R6-6 verdict row and entry, so the body can be counted for that too.

### 2026-08-29b

Banner corrected in one edit (docs/perf-round6-audit-2026-08.md:3-14). Verified first-hand from the BODY per the finding's own trap: eleven MOTIVATED verdict rows (R6-6,5,4,1,10,11,9,16,18,7,8) and four NOT MOTIVATED (R6-2,14,12,15) -- 11+4+3 unreachable = the banner's own ALL EIGHTEEN. Instrument control: grep -c 'NOT MOTIVATED' returns 5 and is WRONG, line :90 is prose not a verdict row. Second clause 'Nothing here is landed' was false twice over (R6-10 2026-08-20b, R6-6 2026-08-24d) and is deleted. Per the trap the new banner carries NO count and points at the tables.
