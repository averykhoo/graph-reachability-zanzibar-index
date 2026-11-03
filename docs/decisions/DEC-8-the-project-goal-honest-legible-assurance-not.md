---
type: Decision
id: DEC-8
title: 'The project goal: honest, legible assurance, not wider (user decision, 2026-09-22c)'
actor: owner
decided: 2026-09-22
session: 2026-11-03a
decision_status: BUILT
attribution: owner, the heading says it records a user decision; the date in the heading, 2026-09-22
imported_from: docs/evidence/decision-log-normalised-2026-11-03.md
body_sha: sha256:c067c14d02518010a952115b519ee73acd5be1022f56508bfba3033a2cedd7da
---

* **The goal.** The user asked for a goal rather than a task ("not like what task to do,
  but what goal to achieve - correctness, perf, etc") and, after three read-only censuses
  (perf / equivalence / formal), chose: **make the assurance surface honest and legible,
  not wider.** The deciding measurement: ~12.5k lines of product code inside ~115k lines
  of tests and Lean (2026-09-22c), and neither assurance system could state which inputs
  it covers. Evidence: [`goal-census-2026-09-22.md`](../goal-census-2026-09-22.md) §6;
  the choice is recorded on `TK94` (closed, note 2026-09-22c) and in the session log's
  2026-09-22c entry. Recorded here 2026-10-07d, when the banner that had carried it was
  pruned (`TK130`); it had no live home of this kind before.
* **Corollary: stop widening the Lean fragment.** The census's move 2 under this goal:
  land the T2a chain (`P4` → `P5`, + `P14`; all three closed), declare it the formal
  milestone, and rank the rest (`P15`, `P16`, `P25` option 2, `DW-1`) as assurance work
  against product risk, not as "the rest of the proof".
* **Rejected: perf as the goal.** There is no performance target (an exhaustive grep,
  2026-09-22c), so a perf win cannot be shown to be worth anything outside the repo. Not
  abandoned: when perf reopens, its first move is `TK34` (the regression canary), not an
  `R6-N` row. Reasoning: `python scripts/task.py show R6`, note 2026-09-22c.
* **Rejected: a wider fragment.** More proven shapes would widen a surface that still
  could not say what it covers; legibility first.
