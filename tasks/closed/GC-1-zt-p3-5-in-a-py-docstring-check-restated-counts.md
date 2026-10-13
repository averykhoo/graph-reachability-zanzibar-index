---
id: GC-1
title: ZT-P3-5 in a .py docstring: check_restated_counts sees neither percentages nor .py files
brief: Four prose copies of one coverage figure, four values; all deleted -- the check that would catch it is still owed
pri: LATER
size: M
deps: []
related: []
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-09-10b
moved: 2026-10-13
updated: 2026-10-13
closed: 2026-10-13
---

## The rot that was found (TK44, 2026-09-10) and fixed (this row, same day)

One measurement — how much of the generator-coverage pair space stays unreached — was
stated in prose **four times, with four different values**:

| site | value |
|---|---|
| `tests/test_generator_coverage.py:68` (module docstring) | `~19%` |
| `tests/test_generator_coverage.py:428` (`test_every_alphabet_feature_is_hit_or_rejection_explained`) | `~28%` |
| `tests/test_generator_coverage.py:1152` (`test_report_cell_coverage`) | `~30%` |
| `docs/sabotage-procedure.md` | "roughly a quarter" |

The middle two used **identical wording** ("unreached even at `deep`") and contradicted
each other **inside one module**.

Live measurement, 2026-09-10, `ci` profile, K<=2, via
`pytest tests/test_generator_coverage.py::test_report_cell_coverage -q -s`:

```
[genswarm] alphabet 51 features -> 1275 pair cells
[genswarm] HIT        841  (66.0%)
[genswarm] +REJ       871  (68.3%)
[genswarm] UNKNOWN    404  (31.7%)   <- the honest remaining blind spot
```

The cause is ordinary and worth remembering: the four sentences measured **different
things** — HIT-only vs HIT+REJ, `ci` vs `deep`, this tree vs the frozen prototype design
(`docs/design/generator-coverage/README.md` §6 item 1: "Best measured union: 891/1275").
All four could be written in good faith and no two agree.

⚠ **The write-up of the drift added a FIFTH wrong value.** `docs/sabotage-procedure.md`
gained "roughly a quarter" in the same commit that documented the problem — a figure
obtained by pairing one instrument's floor (`_CELL_FLOOR_DEEP`, "measured 957", HIT-only)
with another's union framing. A note about a drifting number is still prose.

## Landed 2026-09-10

All four deleted and pointed at the single home,
`tests/test_generator_coverage.py::test_report_cell_coverage` (run with `-s`; take the
figure with the date you read it). The module docstring carries the ⚠ so the next reader
does not "helpfully" restore a number.

## STILL OPEN — the mechanism

`scripts/handoff_lint.py::check_restated_counts` cannot see this class, on **both** axes:

* **Scope.** `COUNT_DECLARED = ('CLAUDE.md', 'HANDOFF.md')` plus `*.md` under `docs/` and
  `tasks/`. A `.py` docstring is never walked.
* **Pattern.** `_COUNT_PATTERNS` is three CENSUS forms — `N checks`, `N open tasks`,
  `N tests`. A percentage matches none of them.

Widening it is not free, and its own contract constrains how:

* The check landed only after a census showed it arrived red on **6** real lines and no
  legitimate ones. A pattern that arrives red on dozens of good lines gets deleted.
  Measure before wiring, as `TK58` did.
* Its docstring requires that the commit adding a fourth pattern **name the rot that
  motivated it**. This row is that rot.
* `tests/test_handoff_lint_count_guard.py` carries a ten-mutation sweep in which the
  obvious widening of one pattern broke the check while the whole module stayed green.
  Read it before editing anything there.
* Extending the walk to `.py` docstrings is a much larger corpus than the markdown globs;
  a percentage pattern (`~NN%`, `NN %`, "roughly a <fraction>") over it needs its own
  census first. The escape vocabulary is structural by design (no baseline file) and
  should stay that way.

An alternative worth weighing before widening: this figure has a machine-readable home
that already prints it, so a check that refuses **any** `%`-of-the-pair-space claim
outside that one function may be both narrower and stronger than a general percentage
pattern.

## Log

### 2026-09-22

MECHANICAL: the `HANDOFF.md` `## Still owed` bullet that pointed here ("A percentage still has no mechanical guard -- now FILED as `GC-1`") was DELETED by the 2026-09-22 Still-owed disposition as a SECOND COPY. This row is the single home and its state is unchanged; `moved` deliberately holds. The bullet added nothing this row does not already carry, including why widening the check is not free. Context: `TK97` (lint check 15).

### 2026-10-13

CLOSED 2026-10-13 by executive decision (lane L7; the call was made by a separate judgement subagent under CLAUDE.md 'Who decides' and implemented here). No code, no new test, no lint widening. Facts below were READ first-hand 2026-10-13 unless labelled.

(1) The motivating instance is retired, and the quantity is no longer a free-floating number. The four prose figures stay deleted. The only percentages left in tests/test_generator_coverage.py are: the dated MEASURED 2026-08-10 table (:36-53), the GC-1 (!) paragraph quoting the rotten values AS HISTORY (:86-90), the floor-convention comments '~5% under' / '~10% under' (:598, :617, :633, :645, :968, :976), and the print lines of test_report_cell_coverage (:1802-1815). TK44 (d03156f) turned the residue into a DERIVED classification and pinned its interesting member to zero. `test_every_pair_of_hit_features_is_reached_together` (:722) asserts the gap is empty, with a recorded sabotage dated 2026-10-12c. `test_refused_only_features_are_tupleset_shapes` (:757) pins the refused-only class. No 'blind spot %' is left for anyone to copy. Stray '~30%' strings survive only in DATED snapshot docs: docs/goal-census-2026-09-22.md:123, docs/promote-next-triage-2026-10-03.md:85, and docs/tk44-generator-coverage-census-2026-10-12.md:137 (which quotes the row title). They are as-of-then, not drift.

(2) The general widening (a percentage pattern plus a walk of .py docstrings) fails `scripts/handoff_lint.py::check_restated_counts`'s own contract. In this ONE file a '%' pattern would go red on six legitimate floor-margin comments plus the GC-1 warning paragraph itself. That is more false reds than the whole retrospective control the check was landed on (6 true lines, 0 false). The row's own words: "a pattern that arrives red on dozens of good lines gets deleted."

(3) The narrow self-test ("refuse any %-of-pair-space claim outside test_report_cell_coverage") would need an allow-list: the (!) paragraph, six floor comments, the dated MEASURED table and the print lines. That is an ad-hoc baseline, which the row says the escape vocabulary must never become. A check with that many exemptions gets edited until it passes.

(4) The (!) at the exact site of the rot, naming the single machine-readable home, together with the pinned classification, is the most durable form available. On docs/sabotage-procedure.md's ladder, a mechanical check that cannot be made structural ranks below it, because it either fails by passing or gets deleted.

REOPEN TRIGGER: a THIRD drift of a percentage into live prose anywhere in tests/ or docs/ (dated snapshot docs do not count). Then run a TK58-style census FIRST, and add a fourth `_COUNT_PATTERNS` entry naming GC-1 as its rot, respecting the ten-mutation sweep in tests/test_handoff_lint_count_guard.py. Leave the 2026-08-10 MEASURED table alone: it is dated, so it is honest.
