---
id: TK89
title: the crossable census books two different numbers for one tree; its reproducibility is unpinned
brief: same tree, same command, parse_crossable 17 vs 18 -- the acceptance instrument is not reproducible
pri: NEXT
size: S
deps: []
related: [TK77, TK87, TK84]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-20
moved: 2026-09-20
updated: 2026-09-20
closed:
---

The acceptance instrument for `TK77` and `TK87` booked two different values for the same
column, on the same tree, from the same command, and nobody has explained the difference.

```
python formal/probes/tk77_crossable_census_2026-09-19.py --pytest \
    tests/test_generator_coverage.py -q -p no:cacheprovider -s
```

* `TK77` (2026-09-19e) recorded `parse_crossable` **17** for that module.
* `TK87` (2026-09-19f) booked **18** from the same command on the same tree, and
  recorded the disagreement **deliberately unreconciled** rather than averaging it
  ([`docs/tk87-swarm-churn-2026-09-19.md`](../docs/tk87-swarm-churn-2026-09-19.md) §1, §5).

Both are first-hand. The neighbouring columns in the same two runs match exactly
(`_ensure/EFF` **46**, `CTL` **110**), so this is not a wholesale instrument failure --
it is one column moving by one.

**Why this is an item and not a tidy.** That probe is the acceptance column both items
were closed on. `TK87`'s headline (`_sync/raw` **0 -> 44**, `_sync/EFF` **0 -> 20**) is far
too large to be explained by a +-1 drift and is not in question. What IS in question is the
instrument's reproducibility: if the census can move by one without a tree change, then any
FUTURE acceptance measured on it needs a stated tolerance, and a small delta read off it
means nothing. `CLAUDE.md` already forbids differencing against a recorded count; this is
the same failure one layer down, in the thing doing the measuring.

## Candidate mechanisms

**(1) The hypothesis example database -- REASONED, and the leading candidate.**
READ 2026-09-20: `tests/test_generator_coverage.py:685` and `:691` are `@given` tests
(`G.swarm_subset()`, `G.swarm_configs()`), and `.hypothesis/` exists in the working tree.
`-p no:cacheprovider` disables pytest's cache and does NOT touch hypothesis's. A replayed
example is an extra execution of the test body; every generated config gets parsed, so the
number of `parse_openfga_schema` calls seen is a function of DB state, not of the tree.
This predicts exactly the observed shape: a small integer column moving while the
structural ones hold still. UNVERIFIED: nobody has run it twice with the DB cleared
between runs.

**(2) Attribution by last-started test -- READ 2026-09-20, second candidate.**
`formal/probes/tk77_crossable_census_2026-09-19.py::pytest_runtest_logstart` sets `_CUR[0]`
from the nodeid, and `::_bump` attributes to whatever that holds. A parse during collection
or before the first test starts books to `<setup>`; a parse during teardown, or in a
lazily-built module-scoped fixture, books to whichever test last STARTED. So a parse can
change rows without changing the total. CHECK THIS FIRST -- it is nearly free: compare the
`<setup>` row and the TOTAL line between the two runs. If the TOTAL is stable and only the
module row moved, it is (2); if the TOTAL moved too, it is (1).

**(3) The re-export rebinding loop -- READ 2026-09-20, weakest.**
`::pytest_configure` rebinds `parse_openfga_schema` on every module already in
`sys.modules` that holds the original, and relies on later imports picking up the patched
attribute. A module that captured the re-export before the hook ran and is not reachable by
that sweep is invisible to the counter. REASONED: import order under a fixed pytest
invocation is deterministic, so this explains a constant bias, not a drift between two runs
of one command -- it is the explanation to reach for only if (1) and (2) are both excluded.

## Acceptance

Not "the number is 17" or "the number is 18" -- either is fine. The deliverable is that the
census states which it is and WHY it can be trusted:

* run the command twice back to back and say whether the column moves, with the `<setup>`
  row and the TOTAL quoted, not just the module row;
* if it moves, name the mechanism and either remove the drift (e.g. a
  `--hypothesis-seed` / derandomized profile for census runs) or write the tolerance into
  the probe's docstring so the next reader does not treat a +-1 as signal;
* append the finding, dated, to `docs/tk87-swarm-churn-2026-09-19.md` §1 where the
  discrepancy is flagged, and note it in the `TK77` census doc.

Note the instrument already carries its own dead-instrument control (`CTL`, printed with an
explicit `INSTRUMENT DEAD` banner when it never fires), and that control was ALIVE at
**110** in both runs. What it does not carry is a reproducibility control.

## Read first

- [`docs/tk87-swarm-churn-2026-09-19.md`](../docs/tk87-swarm-churn-2026-09-19.md) §1 --
  the flagged discrepancy, and §5 which leaves it open on purpose.
- `formal/probes/tk77_crossable_census_2026-09-19.py` -- traps (a) and (b) in its module
  docstring are the instrument's own known limits; this item is a third one.
- `docs/sabotage-procedure.md` § "Sweep the TEST MODULE with mutations" -- the standing
  requirement to control your instrument as well as your subject.

## Log
