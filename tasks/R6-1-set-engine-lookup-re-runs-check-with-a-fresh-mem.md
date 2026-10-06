---
id: R6-1
title: set-engine lookup re-runs check with a fresh memo per candidate (91.4% of lookup)
brief:
pri: LATER
size: L
deps: []
related: []
parent: R6
labels: [perf]
source: docs/perf-round6-audit-2026-08.md
source_hash:
created: 2026-08-15
moved: 2026-09-22b
updated: 2026-09-22b
closed:
---

`src/zanzibar/setengine/engine.py::SetEngine.lookup`

**Measured (2026-08-17 motivating-measurement pass):** **74.1 `check` calls per `lookup`** and **91.4%** of lookup wall time; `lookup` degrades **2.5×** from scale 400→1600 while `check` stays flat. The biggest read ceiling in the round — and it is last in the land order anyway, on purpose.

**Verdict: MOTIVATED — still to land.** Position **10 of 10** in the audit’s recommended order (`R6-6 → R6-11 → R6-5 → R6-4 → R6-9 → R6-18 → R6-16 → R6-7 → R6-8 → R6-1`). That order is a RECOMMENDATION and is deliberately NOT encoded as `deps`; neither is `R6-16`’s co-design requirement, which is simultaneity rather than precedence and lives in the traps of `R6-16`/`R6-7`/`R6-8`. **No row in this round has `deps`.**

## Traps

⚠ **Read your id’s entry in [`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) — INCLUDING its verifier corrections — and that file’s §"Traps the numbers do not carry", before taking this id.** The audit’s own rule: *do not implement from titles alone*. Eighteen findings survived adversarial verification with **0 refuted**, but several impacts were downgraded, several fix sketches were corrected, and one fix was refuted outright while its finding stood.

⚠ **`R6-1` has the biggest read ceiling in round 6 and must NOT be landed from it.** The profile proves `check` *dominates*; it does not prove sharing *eliminates* — the redundant fraction is **unmeasured**. The naive shared memo is a **correctness bug by this audit’s own counterexample**: the finding stood, the proposed fix was REFUTED. Prototype the two-tier design in the verdict behind a measurement; do not land off the percentage.

⚠ Owes a `CORRESPONDENCE.md` §7 log entry even though forward `lookup` is unmodeled.

⚠ **Decompose every cumulative share before quoting it as a target.** `R6-10`’s headline 59.8% was CUMULATIVE; decomposed it was `_direct_incoming` 28.4% + `_nodes_by_ids` 30.7%, and the realised win came from the two SELECTs, not the headline. `R6-19` is the same trap caught earlier.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §`### R6-1` — the entry, **including its verifier corrections**
- the same file, §"Traps the numbers do not carry" — the round-wide traps. Read the section; it is short, and it is the only home for how many there are. (This line used to say "the five", attributed to the tree generator recounting them at generation time. That generator was deleted with `.scratch/tasktool/` on 2026-09-07, so the attribution named a mechanism that could not run — `TK61`, reworded 2026-09-07b. A bare "five" with no attribution would have been worse: that is an unsourced restated count.)
- [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md) — verdicts, method, and the two honest limits (in-memory SQLite understates statement-count wins; cProfile depresses throughput)
- `src/zanzibar/setengine/engine.py::SetEngine.lookup` — the code
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the fence and the reopening rule
- `python scripts/task.py show R6` — the parent: round-wide order, traps and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21

**Migrated by `migrate.py`, and this row is a CORRECTION.** The first migration pass classified every id whose disposition string was not literally `closed` as retired, which wrote this live item into `retired-ids.txt` — an irreversible sink, since `task.py` refuses to re-mint a retired id. Its true disposition (`MOTIVATED, unlanded`) is taken from `docs/perf-round6-audit-2026-08.md`, the audit that owns these ids, not from the `R6` board row’s summary prose (which undercounts the land list by one and overcounts the declines by one). `parent: R6` makes the round a rollup: closing the last child is what reports that `R6` itself can close. **`created` (`2026-08-15`) is RECORDED, not approximated** — it is the date the audit doc that minted these ids states for itself; `moved` is the `R6` board row’s value.

### 2026-09-22b

2026-09-22b LEAN VERDICT + the standing refusal, restated because the percentage keeps
attracting sessions.

LEAN: no def change IF standalone `check` answers are preserved, but a sec 7 entry is owed
regardless. `CORRESPONDENCE.md` sec 2 pins `SetEngine/Eval.lean::SetEngineModel.check`
answer-for-answer against `SetEngine.check` and states it is explicitly NOT an algorithm twin;
it anchors the closures `::SetEngine.check.sat`, `.sat_expr`, `.direct_leaf`,
`.member_via_usersets`, `.ttu_leaf` -- RENAMING ANY OF THEM FAILS `verify.sh lean`, and the
two-tier promotion logic lands inside `.sat`. Forward `lookup` is unmodelled (sec 7 P1/N17);
`_instances_of_type` has zero anchors.

DO NOT LAND THIS FROM THE 91.4%. That figure proves `check` DOMINATES; it does not prove sharing
ELIMINATES, and the redundant fraction is UNMEASURED. The naive shared memo is a correctness bug
by the audit's own counterexample (`x: [user] but not y` / `y: [user] but not x`): the lowlink
guard is `if my_low >= depth:`, so it memoizes a frame that is the root of its own cycle -- a
root-context cycle-broken answer, not a root-independent truth. This is the only fix in the
round that was REFUTED OUTRIGHT while the finding stood.

SO THE FIRST DELIVERABLE IS A MEASUREMENT SESSION, not a change session: instrument the
redundant fraction, then prototype the two-tier design behind it. Realistically two sittings
minimum, three likely. The hard part is proving the clean-sharing promotion rule sound against
non-monotone Exclusion on a schema class (`CyclicDerivedDependency`, ruleset-less) the engine
deliberately admits; `tests/test_lookup_oracle.py` is what would go red.

UNVERIFIED, for the next session to re-grep before sizing: a subagent census this session
reported THREE `self.check(...)` sites in `src/zanzibar/setengine/engine.py` (`:1544`/`:1599`/`:1624`) where
this row's evidence block names two. Not re-verified first-hand.

Full audit: docs/r6-sizing-census-2026-09-22.md
