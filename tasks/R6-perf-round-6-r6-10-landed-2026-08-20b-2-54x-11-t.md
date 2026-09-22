---
id: R6
title: perf round 6 -- R6-10 (2.54x) and R6-6 landed; counts derived from the children, never typed here
brief: Batch THROUGH the N15 cache (R6-6 is the pattern); NOT parallel-safe with P6 on the cascade read path
pri: LATER
size: L
deps: []
related: []
parent:
labels: [perf]
source: board
source_hash: b895d453a044
created: 2026-08-21
moved: 2026-09-22c
updated: 2026-09-22c
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

**`R6` is a PARENT row: every `R6-N` sub-item is a task of its own**, so this row does not
carry them in prose. **There is deliberately no census here.** Get it from the tree:

    python scripts/task.py list --parent R6 --limit 0 --all

⚠ That query answers a WIDER question than it looks. `R6`'s children are no longer only the
`R6-N` items — the unverified perf leads (`TK17`–`TK32`) and `TK47`/`TK48` are parented here
too, so a raw total is not a count of round-6 candidates. Filter to the `R6-N` ids for that.

WHY NOTHING IS COUNTED HERE (`TK60`, 2026-09-07b). This paragraph used to carry
"10 `LATER`, 3 `HOLD`, 6 closed", asserted to be generated rather than typed, citing
`migrate.py::r6_census` as the thing that recomputed it. Two failures compounded. The
citation died: `migrate.py` lived in the deleted `.scratch/tasktool/`, so the sentence
claimed an enforcement that could not run. And the numbers were hand-maintained in fact —
the title's "11 to land" had already been corrected to "10 to land" by hand when `R6-6`
closed, and the scope caveat above had to be bolted on when the `TK` leads were parented
here. A count that must be re-typed whenever a child moves is a count that will be wrong;
the query is never wrong. The dispositions that are NOT derivable — which candidates were
declined and on what number — stay in the paragraphs above, because those are judgements,
not counts.

**Closing the last child is what reports that `R6` can close** — the round's archive sweep
is computed, not remembered.

**Restored to `NEXT` 2026-08-31b**: it was demoted on 2026-08-31 purely to seat `P20`, and
`P20` closed 2026-08-31b. Nothing about the work changed in between.

## Traps

⚠ **Batch *through* the N15 cache, not past it** — `R6-6` is the pattern, and every
read-path item in this round has a cascade caller behind it (`_EvalContext.leaf_check`)
where a fresh per-call query would replace warm N15 cache hits with SQL.

⚠ **Not parallel-safe with `P6` if it touches the cascade read path** (`P3` closed
2026-09-05b, so `P6` — now `NOW` — owns that cone). Check before opening a cone that `P6`
owns; the old `P3`/`P6` collision paragraph in `P6`'s file is the shape to expect.

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

### 2026-09-06b

Board row + block rewritten 2026-08-31b (restored to NEXT after P20 closed; N15-cache trap and the new 'not parallel-safe with P6 on the cascade read path' trap moved into the block; declines/unreachable reduced to a pointer at the audit). Task body reconciled 2026-09-06b: restoration paragraph added, both traps added to Traps, brief carries the P6 collision; children re-counted 10 LATER / 3 HOLD / 6 closed, title unchanged. Diff source: git 50af00e -> HEAD.

### 2026-09-15d

`NEXT` -> `LATER`, to make room for `P22`. Not a judgement on this row: the 2026-09-15d session was redirected by the user to edge cases and bugs, which produced a CONFIRMED equivalence break (`TK69`) and made `P22` actionable with a concrete candidate input. Correctness work outranks perf work under that instruction. Nothing here is stale, blocked or wrong -- the `R6-*` children are untouched and this row resumes as it stood.

(!) The standing note still holds and matters more now, not less: this row is NOT parallel-safe with `P6` on the cascade read path. `P6` is parked at `LATER` as of the same session, so that collision is dormant rather than resolved -- re-check it if `P6` restarts.

### 2026-09-22b

2026-09-22b: A CORRECTNESS/EXPECTATIONS + LEAN AUDIT OF EVERY OPEN CHILD LANDED, at user
request ("look into the correctness and expectations for each r6 option ... and audit whether it
breaks the lean model and by how much, or whether it could allow simplifying the lean model").
Map: docs/r6-sizing-census-2026-09-22.md (ACTIVE-PLAN). Corrections are logged on each child's
own row under session 2026-09-22b; this entry is the index.

THE HEADLINE: four rows described a surface or a number the code does not have. R6-9's
instrument is mis-keyed, so the fix cannot move its own headline figure. R6-16 names one emit
site and has six. R6-19 calls its cheapest sub-step argument-free when the code mutates and
stores back between iterations. R6-11's owed CORRESPONDENCE edit was already landed by R6-10.

MEASURED: R6-5's 32.7% is not R6-5's. One profile run serves both R6-4 and R6-5 (the
`target_graph_lookup` banner is literally "[R6-4, R6-5]") and the 32.7% is SQLAlchemy's generic
`_instance` line. Per-class attribution gives 6,000 ResidueV1 (26.8%, R6-4's scan) vs 16,410
NodeV4+EdgeV4 (73.2%). The two headline numbers OVERLAP BY ~8.8 POINTS AND CANNOT BE ADDED.
R6-4 is the better true win of the pair. Probe `.scratch/r6-decomp/probe_instance_by_class.py`;
its deduped total reconciles EXACTLY to the profile's recorded 22,410, which is the instrument
control -- its first run said 38,820 and the disagreement is what exposed a double-registered
listener.

LEAN, by mechanical anchor census: zero cost for R6-8 (0 anchors), R6-9 (0), R6-19 (0);
no def edit but a sec 7 log for R6-7 (scopes a modelled PREDICATE) and R6-1; representation-only
for R6-18; unmodelled sec 7.3 surface for R6-5; genuinely modelled for R6-4 and R6-16.

STAR THE ONE THING WORTH TRYING FIRST: R6-16 may SIMPLIFY the Lean model rather than complicate
it. `GraphIndex/LeafRules.lean::writeRulesRaw_untaintedSchema` is already stated at hypothesis
`forall d in S.defs, isDerived S d.1 = false` -- exactly R6-16's "schema boolean-ness" gate --
and proves a write path collapses under it. If emission is gated the same way, the
logged/unlogged distinction should collapse for pure-union stores, retiring a branch of
reasoning instead of adding one. REASONED, not attempted in Lean. See the R6-16 row.

STRUCTURAL: R6-16 + R6-7 + R6-8 are ONE unit (~16 symbols, three modules), not three rows. A
session picking "two small ones" off the tail picks R6-7 and R6-8 and unknowingly takes on
R6-16. Breaking the triple needs an explicit recorded decision.

BUDGET, measured from `.gate-runs/ledger.tsv`: the ten-phase gate is 1779 s across ten commands
and must run after the write-back, so it is one full gate per session. R6-6 was declared size S
and consumed a whole session. One id end-to-end per sitting, or two only if R6-11 + R6-9.

### 2026-09-22c

2026-09-22c -- **PERF IS DEPRIORITIZED BY A GOAL DECISION, WITH A REASON. This is not an
abandonment and not a judgement on the work, which is unusually well instrumented.** The user
asked for a goal rather than a task and chose "make the assurance surface honest and legible,
not wider" over perf; the evidence is docs/goal-census-2026-09-22.md, the perf leg is sec 4.

The one fact that decided it, measured first-hand 2026-09-22c: **there is no performance
target.** An exhaustive grep for SLA / p99 / p95 / latency target / throughput target /
production deployment / customer over docs/, tasks/, benchmarks/ and README.md returns zero
substantive hits (the only p99 hits are a sabotage fixture id). The two profiling workloads are
synthetic fixtures under in-memory SQLite and cProfile, and R6_PROFILE_2026-08-17.md itself
says both invalidate the seconds column. So a win here cannot currently be shown to be worth
anything to anyone outside the repo -- which is a statement about the MISSING TARGET, not about
the measurements.

Two consequences worth carrying into whenever this reopens:

1. **The honest first move is TK34 (the nightly canary), not an R6-N row.** The round has landed
   two real multiples and has no regression tripwire behind them. TK34 is fully specified at
   docs/gate-runbook.md:752-762 and has never been built. A tripwire is also the cheapest thing
   that would give perf work an external referent.
2. **docs/perf-next-round.md was corrected this session and had been wrong for five weeks** --
   it said round 6 "landed nothing" and still listed R6-10 and R6-6 as the first two items to
   land, both closed in August. A session starting from the living perf doc would have re-opened
   two closed items. The landing order there is now struck and captioned, and the 2026-09-22b
   corrections (the R6-5 / R6-4 overlap, R6-9's mis-keyed instrument, the R6-16+R6-7+R6-8 unit)
   are linked from it.

Standing state if it reopens: the two unimpeached large measured wins are R6-4 and R6-18. Four
of the ten open children had their prose corrected 2026-09-22b for describing a surface the code
does not have, and three more had headline figures downgraded, overlapped or reclassified as
ceilings -- that, rather than the percentages, is the diminishing-return signal.
