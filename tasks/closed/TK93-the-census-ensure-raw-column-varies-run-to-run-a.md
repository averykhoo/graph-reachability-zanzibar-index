---
id: TK93
title: the census _ensure/raw column varies run-to-run at a FIXED hash seed; mechanism unidentified
brief: six runs one tree: 6589/6609/6617/6627; PYTHONHASHSEED refuted by its own fix failing sabotage
pri: NOW
size: S
deps: []
related: [TK89, TK77, TK87]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-20g
moved: 2026-09-21b
updated: 2026-09-21b
closed: 2026-09-21b
---

`formal/probes/tk77_crossable_census_2026-09-19.py`'s `_ensure/raw` column varies run to run
on an unchanged tree. **MEASURED 2026-09-20g**, six runs of the recorded `--pytest
tests/test_generator_coverage.py` invocation:

```
PYTHONHASHSEED unset : 6617, 6589
PYTHONHASHSEED=0     : 6627, 6627, 6609, 6627
```

Spread **38** (0.6%). Every other column held still in all six -- `parse_total` 1858,
`parse_crossable` 24, `_ensure/EFF` 78, `_sync/raw` 44, `_sync/EFF` 20, `CTL` 166 -- and the
crossable shape-set breakdown was byte-identical throughout.

**Severity is bounded and stated so nobody over-reads it.** By the census's own trap (a) a
raw count is NOT reach: both wrapped methods are called unconditionally and return at a
guard. No acceptance table has ever quoted this column, so `TK77` and `TK87` are undisturbed
and `TK89` closed on `parse_crossable`, which IS reproducible. This is an instrument defect,
not a correctness one.

## Ruled out already -- do not re-derive these

* **`PYTHONHASHSEED`** -- REFUTED 2026-09-20g, and by a fix that failed its own sabotage.
  A re-exec-seeded guard was added on the strength of two agreeing seeded runs, then the two
  re-exec'd runs booked `6609` and `6627`. The guard was removed.
  `docs/tk89-census-reproducibility-2026-09-20.md` sec 5.3a.
* **The hypothesis example database** -- REFUTED by READ: the only `@given` tests in the
  module carry `tests/test_generator_coverage.py::_SWARM_SETTINGS`, which sets
  `database=None` and `derandomize=True`. Same doc sec 2.
* **Attribution drift** (`::pytest_runtest_logstart` booking to the wrong row) -- REFUTED by
  measurement: there is no `<setup>` row at all, `TOTAL` equals the module row in every run.
  Same doc sec 5.2.

## Candidates NOT yet examined

1. **`id()`-keyed ordering.** `PYTHONHASHSEED` does not control the hash of an object
   without `__hash__` -- that is its `id()`, i.e. its memory address. A `set` of such objects
   iterates in an order that varies per run at ANY seed, which fits the observation exactly.
   REASONED, unverified; check this first, it is the only candidate that predicts variation
   at a fixed seed.
2. **Unseeded `random`** anywhere in the module's call graph. `tests/test_generator_coverage.py`
   uses `random.Random(0)` at `:1032`, but the graph reaches `tests/genswarm.py` and
   `index_v4/`; nobody has swept for a bare `random.` call.
3. **SQLAlchemy identity-map / GC-dependent work** on the `::_ensure_bridges` path, which is
   what drives the raw count.

## Read first

- [`docs/tk89-census-reproducibility-2026-09-20.md`](../docs/tk89-census-reproducibility-2026-09-20.md)
  sec 5.3a -- the refuted hash-seed diagnosis, and why its own fix is what refuted it.
- `formal/probes/tk77_crossable_census_2026-09-19.py` -- trap (c) in the module docstring,
  and traps (a)/(b) which bound how much this column ever mattered.
- `formal/probes/tk89_census_reproducibility_2026-09-20.py` -- the two-arm harness; reuse it
  rather than rewriting one, and note its table reader reports PARSE-FAIL rather than zeros.
- `docs/sabotage-procedure.md` sec "Sweep the TEST MODULE with mutations" -- a fix for a
  non-determinism has to be sabotaged ACROSS RUNS, which is the step that caught the wrong
  diagnosis here.

## Acceptance

Localise it, or prove it unlocalisable and say what that costs. The useful next step is
cheap and is a BISECTION, not a code read: run the census twice at a fixed seed over
subsets of the module (`-k`) until one test's raw count is the one that moves. Attribution
is by module today, so that bisection is the only way to get per-test resolution without
changing the instrument.

(!) Whatever the answer, do not "fix" it by widening trap (c) into a tolerance band on the
column. A band is a number nobody re-measures.

## Log

### 2026-09-21b

LOCALISED, and the row's premise was wrong: this is not a run-to-run drift, it is a
deterministic FUNCTION OF `PYTHONHASHSEED`. MEASURED 2026-09-21b, 20 seeded runs on a
dependency set byte-identical to TK89's (`git diff 4af2c05..HEAD` empty over the census's
whole import surface): seed 0 -> `6617` (x9), seed 1 -> `6627` (x5), seed 2 -> `6609` (x4),
seed 3 -> `6605` (x2), ZERO within-seed variation. TK89's `{6589,6609,6617,6627}` is four
SEEDS, not four runs -- `6609` and `6627` are exactly what seeds 2 and 1 book today, so the
two "identically-seeded" runs that refuted the hash-seed diagnosis were not at the seed they
claimed. The deleted re-exec guard was aimed at the right mechanism; its EVIDENCE failed,
not its target.

The row's candidate (1) (`id()`-keyed ordering, "the only candidate that predicts variation
at a fixed seed") is refuted with it: there is no variation at a fixed seed to predict.
Candidates (2) unseeded `random` and (3) SQLAlchemy/GC were never examined and no longer
need to be.

WHERE: two tests of the 31 (`::test_dense_regime_finds_no_fail_open_divergence`,
`::test_sparse_regime_finds_no_fail_closed_divergence`), entirely through
`wildcard.py:600/601:_add_tuple_trusted <- :563:add_tuple`. Not `:415`, not `:540`.

WHY: `zanzibar_utils_v1.py::RuleSet.apply` yields its rewrite fan-out out of a `set`;
`tests/parity.py::_GraphSide.apply` consumes it in ONE `try` that rolls back on ValueError.
Raw tuples POSED is `7499` at every seed and the abort count is invariant at `21` -- only
the raiser's POSITION in the fan-out moves, and 2x the completed-prefix delta accounts for
the column exactly (dense +3 writes -> +6 raw; sparse +2 -> +4). The decisive arm:
`--sorted-fanout` gives `6627` at all four seeds with `0 MOVED` in every cell.

REMEDY, and it is not the tolerance band the row forbids: within a seed the column is EXACT,
so the fix is provenance, made mechanical -- the live seed is now welded onto the column
NAME (`_ensure/raw@seed=0`, or `@UNSEEDED`), so a pasted table cannot be silently differenced
against one taken at another seed. Trap (c) is rewritten (it asserted the opposite) and
TK89's doc carries a dated correction at the top; its three lessons survive and gain a
fourth: a sabotage that reddens has still told you nothing until you check the instrument
was in the state you think it was -- "run it twice and the numbers differ" refutes
reproducibility without identifying what varied, and the missing control was one line (run
at two DIFFERENT fixed seeds and watch the value move).

SCOPE: nothing observable moves -- `31 passed` at four seeds and under the sorted arm, same
decision, same rollback, every other census column seed-invariant. No production code
changed; sorting the fan-out is an instrument here, NOT proposed as a fix. "Known live
correctness bugs: 0" is undisturbed, and TK77/TK87/TK89's acceptance columns are untouched.

SPLIT OUT as `TK95` (NEXT, S): all `21` aborts land at fan-out position >= 2, so every one
leaves a completed prefix whose CONTENTS move with the seed, and no test drives one fan-out
in two orders to pin that the post-rollback store is identical. It is evidently fine and
that is a run-wide consequence, not a pin.

Map: `docs/tk93-ensure-raw-seed-dependence-2026-09-21.md`. Probe (with a RAN verdict block):
`formal/probes/tk93_ensure_raw_bisect_2026-09-21.py`.
