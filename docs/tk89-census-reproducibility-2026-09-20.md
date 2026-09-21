# `TK89` — is the crossable census reproducible?

**ACTIVE-PLAN, opened 2026-09-20g — the body is provenance, not a living status.** Live
state is `python scripts/task.py show TK89` and `python scripts/gate_status.py`, never this
file. Corrections append **dated at the top**, never edited into the body. Freeze it when
`TK89` closes.

Provenance labels: **MEASURED** (this session ran it and read the literal output), **READ**
(first-hand from the named `file::symbol`), **REASONED**, **UNVERIFIED**. No subagent was
used.

Probe: `formal/probes/tk89_census_reproducibility_2026-09-20.py`.

---

## ⚠ CORRECTION 2026-09-21 (`TK93`) — §5.3a's headline is REFUTED: the seed IS the mechanism

**§5.3a says "the seed is not the mechanism" and that `PYTHONHASHSEED` is refuted. That is
wrong, and the body below is deliberately left standing as the record of how.** `TK93`
measured, on a dependency set byte-identical to the one below (`git diff 4af2c05..HEAD` is
empty over `tests/test_generator_coverage.py`, `tests/genswarm.py`, `tests/conftest.py`,
`index_v4/`, `zanzibar_utils_v1.py`, `setengine/`, `connectedstore/` and the census probe):

| `PYTHONHASHSEED` | `_ensure/raw` | runs |
|---|---|---|
| `0` | **6617** | 9 |
| `1` | **6627** | 5 |
| `2` | **6609** | 4 |
| `3` | **6605** | 2 |

Zero within-seed variation. The set `{6589, 6609, 6617, 6627}` §5.3a treats as four runs at
one seed is four SEEDS. The mechanism is `zanzibar_utils_v1.py::RuleSet.apply` yielding its
fan-out out of a `set`, truncated mid-fan-out by an `AdmissionRejected` in
`tests/parity.py::_GraphSide.apply`; `docs/tk93-ensure-raw-seed-dependence-2026-09-21.md`
has the evidence, including the `sorted`-fan-out arm that removes the seed dependence
entirely.

**What actually went wrong here is worth more than the number.** The deleted re-exec guard
was aimed at the RIGHT mechanism. What refuted it was two nominally-seeded runs booking
`6609` and `6627` — which are exactly what seeds **2** and **1** book today, i.e. those two
runs were not at the seed they claimed, and the guard's own effect was never verified. So
§5.3a's three carried lessons survive intact (`n=2` cannot establish reproducibility; a fix
for a non-determinism must be sabotaged across runs; name what your control controls for) —
and they acquire a fourth, which is the one this correction exists for:

> **A sabotage that reddens has still told you nothing until you check that the instrument
> was in the state you think it was.** "Run it twice and the numbers differ" refutes
> reproducibility; it does not identify what varied. The missing control was one line: run
> at two DIFFERENT fixed seeds and check the value moves, which separates "the seed does
> nothing" from "the seed was not set".

---

## 1. The premise

`formal/probes/tk77_crossable_census_2026-09-19.py` is the acceptance instrument `TK77` and
`TK87` were both closed on. It booked two values for one column:

| source | date | `parse_crossable` for `tests/test_generator_coverage.py` |
|---|---|---|
| `docs/tk77-crossable-census-2026-09-19.md` §"acceptance columns" | 2026-09-19e | **17** |
| `docs/tk87-swarm-churn-2026-09-19.md` §1 | 2026-09-19f | **18** |

Both first-hand, same command, and the neighbouring columns match exactly (`_ensure/EFF`
**46**, `CTL` **110**). `TK87` recorded the disagreement **deliberately unreconciled** rather
than averaging it, which was the right call and is why this item exists.

**The deliverable is not the number.** Either value is fine. What is owed is that the census
states which it is and why it can be trusted — because `CLAUDE.md` already forbids
differencing against a recorded count, and an instrument that drifts by one silently makes
every future small delta read off it meaningless.

## 2. Candidate (1) — the hypothesis example database — is REFUTED

The task row named this the **leading** candidate: `tests/test_generator_coverage.py:685` and
`:691` are `@given` tests, `.hypothesis/` exists in the working tree, and
`-p no:cacheprovider` disables pytest's cache but not hypothesis's. A replayed example is an
extra execution of the test body, every generated config gets parsed, and that predicts
exactly the observed shape — a small integer column moving while the structural ones hold
still.

**READ 2026-09-20g, and it does not survive.** Those two `@given` functions are the *only*
`@given` in the module (enumerated first-hand over the whole file), and both are decorated
with `::_SWARM_SETTINGS` (`tests/test_generator_coverage.py:594`):

```python
_SWARM_SETTINGS = settings(max_examples=SWARM_DRAWS, deadline=None, database=None,
                           derandomize=True,
                           suppress_health_check=list(HealthCheck),
                           phases=(Phase.generate,))
```

`database=None` means the example database is **not consulted at all** for these tests, so
`.hypothesis/` state cannot add a replayed execution here; `derandomize=True` fixes the
draws; `phases=(Phase.generate,)` removes the reuse phase outright. The comment above that
line says so in as many words — the module is the *yardstick*, and "a yardstick has to be
the same length twice."

⚠ Recorded at this length because the row ranks it first. A future reader should not spend
the same fifteen minutes re-deriving it. What the row got right is that it labelled the
candidate **REASONED / UNVERIFIED** rather than stating it.

## 3. Candidate (2) — attribution by last-started test — is WEAK for this invocation

**READ 2026-09-20g.** `::pytest_runtest_logstart` sets `_CUR[0] = nodeid.split('::')[0]` —
the **module** path, not the test. The recorded command runs exactly one module
(`tests/test_generator_coverage.py`), so every test in the session sets `_CUR[0]` to the same
string. The only other row reachable is `<setup>`, which holds until the first test starts.

So within this invocation the mechanism can only move a parse between **two** rows —
`<setup>` and the single module — and the boundary is "did this parse happen before the
first test started", which is fixed by import/collection order. That is deterministic under
a fixed pytest invocation.

**It is not eliminated**, because it predicts a signature this probe can see directly: if
`parse_crossable` moves while the **TOTAL** holds still, a parse changed rows. That is the
cheap discriminator the task row asked to run first, and it is the reason §5's table quotes
`<setup>` and `TOTAL` and not just the module row.

## 4. A fourth candidate the row does not list: the two runs were not the same tree

**REASONED from a first-hand `git log` read, 2026-09-20g.** The row and both docs assert
"the same tree", but `TK77`'s **17** was measured *during* the `TK77` session — it appears
in that document as the `after` half of a before/after acceptance table (`3 -> 17`), i.e.
against the working tree as the change was being made. `TK87`'s **18** was measured the next
session, described as "the baseline, before any edit", i.e. against the *committed* tree.

Exactly two commits touch the census's inputs on that day:

```
a0c7b31 2026-09-19 test(TK87): the swarm can remove now, ...
399ea99 2026-09-19 test(TK77): the generator half, and both census premises were wrong when measured
```

If a late edit inside `399ea99` added one crossable parse after the `17` was written down,
both numbers are honest, the instrument is reproducible, and there is nothing to fix but the
provenance. **This is a hypothesis, not a finding**, and §5's stability result is what makes
it worth stating: an instrument that is stable across back-to-back runs today cannot be the
thing that produced a ±1 yesterday.

## 5. The measurement at HEAD — MEASURED 2026-09-20g

Four runs of the recorded command, two per arm, each a fresh subprocess.

| arm | run | `parse_total` | `parse_crossable` | `_ensure/raw` | `_ensure/EFF` | `_sync/raw` | `_sync/EFF` | `CTL` | summary |
|---|---|---|---|---|---|---|---|---|---|
| `hash-random` | 0 | 1858 | **24** | **6617** | 78 | 44 | 20 | 166 | `31 passed in 102.53s` |
| `hash-random` | 1 | 1858 | **24** | **6589** | 78 | 44 | 20 | 166 | `31 passed in 105.80s` |
| `hash-fixed` (`PYTHONHASHSEED=0`) | 0 | 1858 | **24** | **6627** | 78 | 44 | 20 | 166 | `31 passed in 103.81s` |
| `hash-fixed` | 1 | 1858 | **24** | **6627** | 78 | 44 | 20 | 166 | `31 passed in 105.49s` |

`CTL` is **166** in every run, so the instrument is alive in all four and the stable columns
are real nulls rather than a dead patch.

**Three findings, in order of importance.**

### 5.1 `parse_crossable` does NOT drift today — it is 24, four times

The column `TK89` was filed about is **stable across four runs and both arms**, as are
`parse_total`, `_ensure/EFF`, `_sync/raw`, `_sync/EFF` and `CTL`. The crossable shape-set
breakdown is byte-identical in all four runs too: `[('doc','r1')] x21` and
`[('doc','r2')] x3`.

⚠ **24, not 17 and not 18 — because HEAD is not the tree either number was measured on.**
`_sync/raw` is **44** and `_sync/EFF` is **20** here, which is `TK87`'s own headline
(`0 -> 44`, `0 -> 20`) and its landed churn pass; the module also collects `31 passed` where
both historical runs collected `28`. So HEAD cannot reproduce the discrepancy by
construction, and §6 goes to the commit that can.

### 5.2 Candidate (2) is refuted by measurement, not just by reading

**There is no `<setup>` row at all** in any of the four runs — `BY_MOD['<setup>']` is never
created, so `TOTAL` equals the module row exactly, in every run. No parse happens before the
first test starts, so the attribution mechanism has only one bucket to put anything in and
cannot move a count between rows. Combined with §3's READ (`_CUR[0]` holds the *module*, not
the test), candidate (2) is closed for this invocation.

### 5.3 ⚠ A column IS non-reproducible, and it is not the one anyone was looking at

`_ensure/raw` moves **6617 → 6589** between two back-to-back `hash-random` runs (Δ **28**),
while every other column holds still. It is a real reproducibility hole in the instrument —
the same class of defect this item was filed about, one column over.

**It is the least load-bearing column**, by the census's own trap (a): a raw count is *not*
reach, both wrapped methods are called unconditionally and return at a guard. Every column
the acceptance tables actually quote (`parse_crossable`, `_ensure/EFF`, `_sync/EFF`, `CTL`)
held still. So this does not retroactively weaken `TK77` or `TK87`. But a future session
diffing `_ensure/raw` by a few dozen would be reading noise as signal.

### ⚠ 5.3a — the first diagnosis was WRONG, and its own fix is what caught it

> **This subsection is here rather than edited away on purpose.** What was nearly shipped is
> the finding.

The `hash-fixed` arm above returned **6627 twice**, against `hash-random`'s 6589/6617. That
is exactly what seed-dependence looks like, `PYTHONHASHSEED` is unset repo-wide (READ
2026-09-20g: no `pytest.ini`, no `pyproject` setting), and `set`/`frozenset` iteration order
plausibly reaches a call count. The diagnosis was written up, and a mechanical fix was
added: the probe re-exec'd itself under `PYTHONHASHSEED=0` whenever the variable was unset.

Then the fix was sabotaged the only way a *cross-run* non-determinism can be — **run it
twice** — and the two re-exec'd, identically-seeded runs booked:

```
6609   31 passed in 104.37s
6627   31 passed in 105.06s
```

**The seed is not the mechanism.** The full set at `PYTHONHASHSEED=0` is now
`{6627, 6627, 6609, 6627}` and unseeded is `{6617, 6589}` — the seeded arm varies too, and
the earlier agreement at `n=2` was luck. The re-exec was **removed** rather than kept as
decoration, because machinery that does not do the thing its comment claims is worse than
no machinery: the next reader trusts it.

Three things this is worth carrying:

* **`n=2` cannot establish reproducibility**, only refute it. Two runs that agree are
  evidence of nothing; two that differ are proof. The `hash-fixed` arm was read in the
  direction the evidence does not support, and §5.3's first draft said so in bold.
* **A fix for a non-determinism must be sabotaged ACROSS RUNS.** The usual sabotage —
  break the thing and watch it redden — cannot see this class at all. The guard here passed
  its own construction test (it re-exec'd, the seed printed, the opt-out worked) and was
  still wrong about what it fixed. `CLAUDE.md`'s house rule generalises: *an assurance step
  that fails by passing* includes a fix that succeeds at the wrong thing.
* **The mechanism is UNIDENTIFIED and is filed as `TK93`**, not guessed at here. What
  is ruled out: `PYTHONHASHSEED` (above), the hypothesis example database (§2,
  `database=None`), and attribution drift (§5.2, no `<setup>` row exists).

The honest state of the column: it varies by up to **38** (0.6%) on one unchanged tree with
no known input moving. `TK89`'s acceptance allows *either* removing the drift *or* writing
the tolerance into the probe — the tolerance is written, and it is printed into the census
table itself (§7) rather than left in a docstring.

## 6. The historical 17 vs 18 — ANSWERED at the commit that can answer it

HEAD cannot settle this (§5.1: the tree moved). `399ea99` — `TK77`'s own commit, the tree
`TK87` described itself as measuring "before any edit" — can. **MEASURED 2026-09-20g** in a
throwaway `git worktree` at that commit, twice, `PYTHONHASHSEED=0`, and the two runs are
**byte-identical on every column**:

```
module                            parse_total  parse_crossable  _ensure/raw  _ensure/EFF  _sync/raw  _sync/EFF   CTL
tests/test_generator_coverage.py         1661               18         6547           46          0          0   110
TOTAL                                    1661               18         6547           46          0          0   110
  crossable shape-sets seen at parse, by module:
    tests/test_generator_coverage.py         [('doc', 'r1')] x15
    tests/test_generator_coverage.py         [('doc', 'r2')] x3
28 passed in 101.35s (0:01:41)
```

**`18` reproduces exactly, and so does everything around it.** `parse_total` **1661**,
`_ensure/EFF` **46**, `CTL` **110** and `28 passed` all match `TK87`'s §1 transcript
character for character. The only column that differs from `TK87`'s run is `_ensure/raw`
(**6547** here at seed 0 versus **6521** in their unseeded run) — which is §5.3's column,
and an independent confirmation of it on a second tree.

### The verdict

**The census is reproducible. `17` and `18` are not two measurements of one tree.**

`TK87`'s **18** is what that commit reproducibly books. `TK77`'s **17** appears in
`docs/tk77-crossable-census-2026-09-19.md` as the `after` half of a before/after acceptance
table (`3 -> 17`) written *while* the change was being made — i.e. against an uncommitted
working tree, not against `399ea99`. That working tree no longer exists and cannot be
recovered, so **which** late edit added the eighteenth crossable parse is unanswerable and
is deliberately left unanswered rather than guessed.

What this closes: the instrument was never the problem, and no future acceptance measured on
`parse_crossable` needs a tolerance. What it leaves: a provenance lesson, not a numeric one —
**a figure measured mid-change is a figure about a tree nobody can check.** `CLAUDE.md`
already says to date every measured number; this adds that a number is only as citable as
the tree it was taken on, and that "the same tree" is an assumption worth stating rather
than asserting. `TK87` was right not to average them.

## 7. What landed — the tolerance, and where it is written

`TK89`'s acceptance allowed *either* removing the drift *or* writing the tolerance into the
probe so the next reader does not treat a ±1 as signal. §5.3a is why it is the second: the
drift's mechanism is not known, so there is nothing to remove yet, and shipping a fix aimed
at a refuted mechanism would have been worse than shipping nothing.

**The tolerance is printed into the census table, not only into the docstring.**
`formal/probes/tk77_crossable_census_2026-09-19.py::pytest_sessionfinish` emits, above every
table it prints:

```
  PYTHONHASHSEED='0'   (!) `_ensure/raw` is NOT reproducible run-to-run and pinning this
  seed does NOT fix it -- observed 6589/6609/6617/6627 on one unchanged tree
  (TK89, 2026-09-20g). Do not difference that column. Every other column held.
```

That placement is the point. A census number gets transcribed into a document far more often
than the probe that produced it gets re-read, and both `TK77`'s and `TK87`'s tables were
pasted from stdout. The warning now travels with the data.

Trap **(c)** is added to the probe's module docstring beside (a) and (b), carrying the six
observations, the refutation of the hash-seed diagnosis, and a pointer here.

| file | change |
|---|---|
| `formal/probes/tk77_crossable_census_2026-09-19.py` | trap (c); the live seed + non-reproducibility warning printed into every table |
| `formal/probes/tk89_census_reproducibility_2026-09-20.py` | NEW — the two-arm reproducibility harness, with a table reader that reports `PARSE-FAIL` rather than zeros |
| `docs/tk77-crossable-census-2026-09-19.md` | dated correction at the top — the `17` is resolved |
| `docs/tk87-swarm-churn-2026-09-19.md` | dated correction at the top — §1's flagged discrepancy is closed |

### 7.1 What is NOT closed

The mechanism behind `_ensure/raw`'s variation is unidentified and is filed as `TK93`.
Ruled out so far, each first-hand: `PYTHONHASHSEED` (§5.3a), the hypothesis example database
(§2), and attribution drift (§5.2). Not yet examined: unseeded `random` use anywhere in the
module's call graph, `id()`-keyed ordering (which `PYTHONHASHSEED` does **not** control), and
SQLAlchemy identity-map / GC-dependent bridge work on the `_ensure_bridges` path.
