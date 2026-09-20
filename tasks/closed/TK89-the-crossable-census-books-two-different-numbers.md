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
moved: 2026-09-20g
updated: 2026-09-20g
closed: 2026-09-20g
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

### 2026-09-20g

CLOSED. The census IS reproducible on every column an acceptance table has ever quoted, the
historical 17-vs-18 is ANSWERED, and a different column turned out not to be reproducible at
all -- filed as `TK93`.

Map: `docs/tk89-census-reproducibility-2026-09-20.md` (ACTIVE-PLAN, freeze it now).
Probe: `formal/probes/tk89_census_reproducibility_2026-09-20.py` (two arms, a table reader
that reports PARSE-FAIL rather than zeros).

THE ANSWER TO 17 vs 18: THE TREES DIFFERED. MEASURED 2026-09-20g in a throwaway `git
worktree` at `399ea99` (`TK77`'s own commit, the tree `TK87` described itself as measuring),
twice, byte-identical: `parse_total` **1661**, `parse_crossable` **18**, `_ensure/EFF` **46**,
`CTL` **110**, `28 passed`. That is `TK87`'s sec 1 transcript character for character.
`TK77`'s **17** appears in its doc as the `after` half of a before/after table written WHILE
the change was being made -- an uncommitted tree that no longer exists. Which late edit added
the eighteenth crossable parse is unanswerable and is left unanswered rather than guessed.
`TK87` was right not to average them.

AT HEAD: `parse_crossable` is **24**, six runs, stable, both hash arms; shape-set breakdown
byte-identical throughout. (24 not 17/18 because HEAD carries `TK87`'s churn pass --
`_sync/raw` 44, `_sync/EFF` 20, `31 passed` vs `28`. HEAD cannot reproduce the discrepancy by
construction, which is why the worktree was needed.)

THE ROW'S TWO CANDIDATES ARE BOTH REFUTED, first-hand.
* (1) the hypothesis example DB -- the row's LEADING candidate -- dies on a READ: the only
  `@given` tests in the module carry `::_SWARM_SETTINGS` (`:594`), which sets
  `database=None` AND `derandomize=True`. `.hypothesis/` is never consulted there.
* (2) attribution by last-started test -- dies on a MEASUREMENT: there is no `<setup>` row at
  all in any run, `TOTAL` equals the module row every time, so there is only one bucket.
  (`_CUR[0]` holds the MODULE, not the test, and the command runs one module.)

(!) A COLUMN IS NON-REPRODUCIBLE AND IT IS NOT THE ONE ANYONE WAS LOOKING AT. `_ensure/raw`
varies by up to 38 (0.6%) on one unchanged tree: unseeded {6617, 6589}, `PYTHONHASHSEED=0`
{6627, 6627, 6609, 6627}. Bounded severity -- by the probe's own trap (a) a raw count is not
reach, and no acceptance table quotes it -- but real. Now trap (c) in the probe, and the
warning is PRINTED INTO EVERY CENSUS TABLE, not just the docstring: a number gets transcribed
into a doc far more often than a probe gets re-read, and both historical tables were pasted
from stdout.

(!) THE DIAGNOSIS I NEARLY SHIPPED WAS WRONG, AND ITS OWN FIX IS WHAT CAUGHT IT. The seeded
arm agreed at 6627 twice, `PYTHONHASHSEED` is unset repo-wide, and set-iteration order
plausibly reaches a call count -- so it was written up as hash randomisation and a re-exec
guard was added. Sabotaging THAT guard the only way a cross-run non-determinism can be
sabotaged -- run it twice -- gave **6609** and **6627** from two identically-seeded runs.
The guard was removed rather than kept as decoration. Two durable lessons, both in the doc
sec 5.3a and worth promoting if they recur:
  - `n=2` cannot establish reproducibility, only refute it. Two agreeing runs are evidence of
    nothing; two differing runs are proof.
  - A fix for a NON-DETERMINISM must be sabotaged ACROSS RUNS. This guard passed every
    construction test -- it re-exec'd, printed the seed, honoured the opt-out -- and was
    still wrong about what it fixed. "An assurance step that fails by passing" includes a
    fix that succeeds at the wrong thing.

ACCEPTANCE, item by item: ran twice (six times) with `<setup>` and TOTAL quoted, not just the
module row -- done, and the `<setup>` row's ABSENCE is itself the discriminator the row asked
for; named the mechanism where one is known and refused to name one where it is not; wrote
the tolerance into the probe (and one better, into its output); appended dated corrections to
`docs/tk87-swarm-churn-2026-09-19.md` sec 1 and to the `TK77` census doc.
