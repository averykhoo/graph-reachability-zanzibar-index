---
id: R6
title: perf round 6 -- R6-10 (2.54x) and R6-6 landed; 10 to land, 4 declined, 3 unreachable
brief: Batch THROUGH the N15 cache, not past it (R6-6 is the pattern). Order: R6-11, R6-5, R6-4, R6-9, R6-18
pri: LATER
size: L
deps: []
related: []
parent:
labels: [perf]
source: board
source_hash: 77474b3d6848
created: 2026-08-21
moved: 2026-08-31
updated: 2026-08-31
closed:
---

**`R6-10` landed 2026-08-20b** (both steps): `−60.7%` incremental boolean write wall,
**2.54×**, SQL statements/cycle `1929 → 822`. **`R6-6` landed 2026-08-24d** at its
predicted `4.75 → 1.75` statements per `check`. Remaining order:
`R6-11` → `R6-5` (**32.7%** ORM construction for 3–4 columns) →
`R6-4` → `R6-9` → `R6-18` (**53.1%** off the biggest table; owes a hand PG migration) →
`R6-16` → `R6-7`+`R6-8` → `R6-1`.

**Declined on an upper bound; do not reopen without new numbers:** `R6-15` (**0.9%**),
`R6-12` (**1.00×**), `R6-14` (**5.0%**), `R6-2`. **Unreachable by any benchmarked workload**
(`R6-3` = `R6-17`, bulk twin `R6-13` — 0 calls each): they need a `T:*#P` workload first.
`R6-19` owns the last unowned number (**cum 25.4%, self 2.0%** — a call-site fan-out; corrected here 2026-08-21: the board cell paired the 2026-08-17 pass’s *undecomposed* **25.3%** with the 2026-08-18 filing re-run’s self time, and no source states that pair. The audit’s `### R6-19` decomposition reads `145,560 calls tottime 0.382 s (2.0%) cum 4.80 s (25.4%)`).

**`R6` is a PARENT row: all 19 `R6-N` sub-items are now tasks of their own** (`task.py list --parent R6`), so this row no longer has to carry them in prose. **Every count in the title and in this paragraph is COUNTED from those children at generation time** (`migrate.py::r6_census`), not restated from the board cell above — a restated count is the defect this whole migration exists to delete, and the board cell is the proof: it says "9 to land, 5 declined". Re-counted 2026-08-29: **10 `LATER`** (unlanded — the audit’s ten-item land order less `R6-6`, plus `R6-19`, filed 2026-08-18 outside the audit and therefore not in that order), **3 `HOLD`** (measured 0 calls — they need a `T:*#P` workload before they need a patch), **6 under `closed/`** (`R6-10` and `R6-6` landed; `R6-2`/`R6-12`/`R6-14`/`R6-15` declined on an upper bound). The declined count is the audit’s own: exactly four `NOT MOTIVATED` verdict rows, so the board cell’s fifth decline does not exist. **Closing the last child is what reports that `R6` can close** — the round’s archive sweep is computed, not remembered. Re-count any time with `task.py list --parent R6`; do not re-type these numbers here.

## Traps

⚠ **Five traps the numbers do not carry** live in
[`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §"Traps the numbers do
not carry", demoted there 2026-08-20b. **Read that section before taking an id.** Both
2026-08-20b corrections were fully applied 2026-08-21: `R6-11`'s "8×" is **~4×** in all four
places *and* the halving now lives in the instrument
(`benchmarks/profile_r6.py::_ctxmgr_entries`, which refuses an odd ncalls), re-confirmed at
`184 scopes / 40 reconciles = 4.6×` — verdict still `MOTIVATED`, only the size moved;
`R6-4(a)`'s unsound `(id, version)` memo is now flagged **in its own entry**, because the
fix sketch is a verbatim block that calls the key "sound".

## Read first

- board pointer: [profile](benchmarks/results/R6_PROFILE_2026-08-17.md)

[`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md)
(verdicts, method, the two limits — in-memory SQLite understates statement-count wins,
cProfile depresses throughput — and its three instrument corrections, whose transferable
rule is [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) §"A MEASUREMENT is an
assurance step too" and binds any re-run), then your id's entry in
[`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) **including its
verifier corrections**, then [`docs/perf-next-round.md`](docs/perf-next-round.md) for the
fence and the reopening rule. Re-run with `python -m benchmarks.profile_r6 [_write]
--target <t>` — never beside another bench or pytest run.

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-21`), which is an upper bound on the real creation date, not a measurement. Summary, traps and read-first come from the `### R6` item block verbatim; the board pointer is the first line of Read first. `R6-1`..`R6-19` were split out of this row into child tasks; the earlier pass wrote fourteen of them into `retired-ids.txt`, which would have made ten funded items unmintable forever. **The title’s count clause is REBUILT** from the children (`11 to land, 4 declined, 3 unreachable`) — the board cell’s "9 to land, 5 declined" was wrong against the audit’s own verdict tables and the old file said so in its last paragraph, which left the retraction below the fold while `board`, `list` and `ready` went on printing the wrong line. The landed clause before the semicolon is the board’s, verbatim. **One figure inside the ported cell was corrected in place and dated**: `R6-19` read "25.3% cumulative, self 2.0%", which pairs the 2026-08-17 undecomposed share with the 2026-08-18 re-run’s self time; the audit states cum 25.4% / self 2.0%.

### 2026-08-24b

Digest drift only; CONTENT AGREES and the tree is ahead. The board cell was corrected on 2026-08-24 (25.3% -> 25.4%, and 11/4/3) to match what this task body had already carried since 2026-08-21, so the stored source_hash pointed at the pre-correction board text. Re-stamped. NOTE the trees still disagree on moved: board says 2026-08-24, this file says 2026-08-21 -- left as-is deliberately, see the 2026-08-24b ledger entry.

### 2026-08-29

Stale figures repaired, and the staleness itself is the trial evidence. The title said '11 to land' and the body's 'As built' census said 11 LATER / 5 closed, both generated 2026-08-21 by migrate.py::r6_census and never re-counted after R6-6 closed 2026-08-24d. HANDOFF.md:50 was CORRECT ('10 to land') the whole time -- the board was re-counted from the children, the tree was not. Re-counted live this session with task.py list --parent R6 --limit 0, R6-N children only: 10 LATER, 3 HOLD, 6 closed. This is the summary-row-contradicting-its-own-child defect (trial finding P4, then HS-5/TK49) recurring a third time, inside the tree, on the row whose self-recounting was cited as the tree's win. Recorded in docs/tasktool-trial-protocol.md section 6, append 2026-08-29 (A6), BEFORE this repair.

Board row rewritten 2026-08-24d (R6-6 landed, '11 to land' -> '10 to land'); the task body was NOT re-counted at the time, so this ack follows an actual content repair this session, not a no-op re-stamp. See the 2026-08-29 Log entry.

Re-stamp: the R6 board row was itself edited this session (moved 2026-08-24d -> 2026-08-29, and the cell now records that the tree carried the stale 11 for five days). Content already reconciled earlier this session; this ack only re-digests the rewritten row.

### 2026-08-29b

Board block edited 2026-08-29b: the decline/unreachable split was replaced by a pointer at the audit's verdict tables, and the five-traps paragraph was reduced to a pointer that says to count the bullets. Both were restatements of docs/perf-round6-audit-2026-08.md, whose banner was corrected the same session (TK48) to carry no count -- restating a split on the board is the defect TK48 was filed for, one file over. No figure changed and no child moved; R6-19's number is unchanged. Task body content remains current.

Block edited again in 2026-08-29c: the Read-first now names the audit's new 2026-08-29b appendix cross-links section alongside the verifier corrections, since ten of them are corrections to the appendix leads a perf session would otherwise read uncorrected. Reflowed for the line ceiling; no figure changed.
