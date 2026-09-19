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
moved: 2026-09-19f
updated: 2026-09-19f
closed:
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
