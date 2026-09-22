---
id: TK88
title: test_generator_coverage.py says it is RED; it has been green since 0838bcf
brief: three sites announce an expected-RED module that is 28 passed -- a genuine red would read as normal
pri: LATER
size: S
deps: []
related: [TK87]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-19f
moved: 2026-09-22c
updated: 2026-09-22c
closed: 2026-09-22c
---

`tests/test_generator_coverage.py` announces in three places that it is expected to be RED,
and it has been green for about five weeks.

MEASURED 2026-09-19f: the module is `28 passed` (103.8 s), and
`tests/test_ttu_tupleset_parent_types.py` -- the module the prose points at -- is
`12 passed`. READ: RC2 was closed at commit `0838bcf` ("RC2: represent the star TTU tupleset
parent -- the 2026-08-10 fail-open family is CLOSED"), and the sparse and dense driven sweeps
now find `FO=0 fc=0` over all 96 driven configs
(`formal/probes/tk87_churn_reach_2026-09-19.py regimes sparse`, 2026-09-19f).

The stale sites, as of 2026-09-19f (line numbers rot -- grep the text):

* `:15`  -- "THIS MODULE IS EXPECTED TO BE RED UNTIL RC1/RC2 ARE FIXED"
* `:126` -- the sabotage table row "RC1/RC2 (live, unfixed) -> RED (both sweeps)"
* `:761` -- "THE TWO TESTS BELOW ARE THE POSITIVE CONTROLS, AND THEY ARE RED TODAY"
* `::test_sparse_regime_finds_no_fail_closed_divergence` -- docstring opens "CURRENTLY RED"
* `::test_dense_regime_finds_no_fail_open_divergence` -- docstring opens "CURRENTLY RED"

Why it is worth an item rather than a tidy: a module that announces its own redness is a
module whose GENUINE red reads as normal, which is the house failure mode pointed the other
way. The fix is NOT to delete the history -- the 2026-08-10 measurements under those
docstrings were true on their date and are the provenance for the regime design. The shape
that fits `docs/README.md` is a dated correction line at each site saying the controls went
green at `0838bcf` and what they are controls FOR now.

## Read first

- [`docs/tk87-swarm-churn-2026-09-19.md`](../docs/tk87-swarm-churn-2026-09-19.md) sec 5 --
  where this was found and the numbers behind it.
- `git log --oneline -S"RC1" --all -- tests/test_ttu_tupleset_parent_types.py` -- the fix.

## Log

### 2026-09-22c

CLOSED 2026-09-22c. All five stale sites corrected in place, in the shape the row prescribed
(a dated correction line, history kept, nothing deleted):

* module docstring -- the "EXPECTED TO BE RED" paragraph is now indented under a
  "[2026-08-10, HISTORICAL]" marker, preceded by a correction saying the module is green
  since `0838bcf` and why the stale claim mattered (a module that announces its own redness
  is one whose GENUINE red reads as normal).
* the sabotage table row -- "RC1/RC2 (live, unfixed)" is now "(live, unfixed AS OF
  2026-08-10)" with the fix commit and the note that the row records what the controls DID
  detonate, not open work.
* the section-5 banner -- "THEY ARE RED TODAY" replaced, and it now says what the two tests
  are controls FOR now: anti-vacuity guards that each regime still drives enough pressure of
  its own kind to detonate an RC1/RC2-shaped divergence if one is reintroduced.
* both test docstrings -- "CURRENTLY RED (positive control)" -> "GREEN since `0838bcf`
  (positive control; RED on 2026-08-10, and this docstring said CURRENTLY RED until
  2026-09-22c)".

MEASURED 2026-09-22c: `pytest tests/test_generator_coverage.py -q --collect-only` collects
31, not the 28 the row recorded on 2026-09-19f -- the module grew between the two dates, so
the row's figure was a date-stamped reading and not a floor. Grep for the three stale
phrasings now returns only lines inside dated corrections or quoted history.

Found and fixed as the second of two "cheap honesty defects" in the 2026-09-22c goal census
(docs/goal-census-2026-09-22.md sec 5); the first was docs/perf-next-round.md still saying
round 6 had landed nothing.
