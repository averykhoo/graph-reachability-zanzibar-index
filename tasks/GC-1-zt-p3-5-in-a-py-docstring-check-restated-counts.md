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
moved: 2026-09-10b
updated: 2026-09-10b
closed:
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
