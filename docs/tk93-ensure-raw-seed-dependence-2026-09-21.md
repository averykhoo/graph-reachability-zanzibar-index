# `TK93` — the census `_ensure/raw` column, localised

**ACTIVE-PLAN, opened 2026-09-21 — the body is provenance, not a living status.** Live state
is `python scripts/task.py show TK93` and `python scripts/gate_status.py`, never this file.
Corrections append **dated at the top**, never edited into the body. Freeze it when `TK93`
closes.

**2026-10-06 (`TK120`):** the code moved into the `src/zanzibar/` package and lost its version suffixes after this doc was written; its paths and class names are the OLD ones. Key: `docs/architecture/overview.md` § "Renamed in TK120".

Provenance labels: **MEASURED** (this session ran it and read the literal output), **READ**
(first-hand from the named `file::symbol`), **REASONED**, **UNVERIFIED**. No subagent was
used; every number below was produced by a command this session ran.

Probe: `formal/probes/tk93_ensure_raw_bisect_2026-09-21.py`.

---

## 0. The verdict in four lines

1. `_ensure/raw` is **a deterministic function of `PYTHONHASHSEED`**, not a run-to-run
   drift. Twenty seeded runs, four seeds, **zero within-seed variation**.
2. It moves in exactly **two** of the module's `31` tests, entirely through
   `index_v4/wildcard.py::WildcardIndex.add_tuple`.
3. The mechanism is a **truncated rewrite fan-out**:
   `zanzibar_utils_v1.py::RuleSet.apply` yields out of a `set`, and
   `tests/parity.py::_GraphSide.apply` consumes it inside one `try` that rolls back on
   `ValueError`. When a fan-out member is refused, the raiser's POSITION in a set iteration
   order decides how many writes already completed.
4. Nothing observable moves — same decision, same rollback, same store, `31 passed` at every
   seed. Only the counter sees it.

`TK89`'s §5.3a conclusion ("the seed is not the mechanism") is **refuted**; that doc carries
a dated correction, and the census probe's trap (c) is rewritten.

---

## 1. The claim under test, and why the old one could not be right

`TK93` inherited this, from `formal/probes/tk77_crossable_census_2026-09-19.py` trap (c) as
it stood on 2026-09-20g:

> `PYTHONHASHSEED` unset : `6617`, `6589` · `PYTHONHASHSEED=0` : `6627`, `6627`, `6609`,
> `6627` … Hash randomisation is REFUTED as the cause.

**READ 2026-09-21** — the dependency set has not moved since those runs. `git diff
4af2c05..HEAD` is **empty** over `tests/test_generator_coverage.py`, `tests/genswarm.py`,
`tests/conftest.py`, `index_v4/`, `zanzibar_utils_v1.py`, `setengine/`, `connectedstore/`
and the census probe itself. So any measurement made today is comparable with those.

---

## 2. The instrument

`formal/probes/tk93_ensure_raw_bisect_2026-09-21.py`. The census books by MODULE
(`nodeid.split('::')[0]`), so its column names all `31` tests at once. This probe books by
**full nodeid**, by **caller**, and by **caller chain**, and runs the module N times in
separate subprocesses.

Counters: `raw` (`_ensure_entity_middles` calls — the census's column), `bridges`
(`_ensure_bridges`), `apply` (`RuleSet.apply` invocations, i.e. raw tuples POSED),
`adds` (`WildcardIndex.add_tuple` calls, i.e. leaf writes ATTEMPTED), and `abort`
(the `(exception type, position-in-fan-out)` of every `add_tuple` that raised).

**Instrument controls, because a table is worth nothing before its instrument is.**

| control | what it rules out | result |
|---|---|---|
| CONSERVATION | attribution losing calls into an unbooked row | per-nodeid `raw` sums to the independently-kept TOTAL in every run |
| RESOLUTION (`--control <nodeid>`, `M0`-shaped) | an attribution that reports every test clean, which reads exactly like a clean module | available; not needed — the baseline diff already names movers, which is the same evidence |
| PARSE-FAIL, not zeros | a missing JSON read as a null result | `INSTRUMENT FAILURE` printed, run dropped |
| rc + summary per run | `CLAUDE.md`'s exit-code footgun | `passed=31` carried beside every number below |
| **cross-instrument** | the probe's own patching changing what it measures | the `tk77` census — a different patch set (it also wraps `parse_openfga_schema` and `_ensure_own_bridges`) — books **`6617`** at seed `0`, three runs, identical to this probe's |
| **instrument stability** | later counters perturbing the count | seed `0` books `6617` before AND after `add_tuple` / `RuleSet.apply` / abort wrappers were added |

---

## 3. MEASURED 2026-09-21 — the column is a function of the seed

Command, once per seed:

```
python formal/probes/tk93_ensure_raw_bisect_2026-09-21.py --seeds 0,1,2,3 --keep <dir>
```

| `PYTHONHASHSEED` | `_ensure/raw` | runs at this seed | within-seed variation |
|---|---|---|---|
| `0` | **`6617`** | `9` | none |
| `1` | **`6627`** | `5` | none |
| `2` | **`6609`** | `4` | none |
| `3` | **`6605`** | `2` | none |
| unset | `6627` | `1` | n/a — comparable with nothing |

The `9` at seed `0` are `3` through this probe, `3` through the `tk77` census itself, and
`3` more through later revisions of this probe. Every run: `rc=0`, `31 passed`.

**`TK89`'s four "one seed, four runs" values are four seeds.** `6609` is seed `2`, `6627` is
seed `1`, `6617` is seed `0` — the exact values its `hash-fixed` arm and its two re-exec'd
runs booked. Those runs were not at the seed they claimed.

### 3.1 WHICH tests

Between-seed diff, per nodeid (seeds `0/1/2/3`):

```
raw     spread 14  [4944, 4950, 4938, 4936]  ::test_dense_regime_finds_no_fail_open_divergence
raw     spread  8  [1593, 1597, 1591, 1589]  ::test_sparse_regime_finds_no_fail_closed_divergence
```

The other three tests that touch the machinery — `::test_churn_pass_never_sweeps_an_empty_store`
(`18`), `::test_churn_pass_reaches_the_i14_remove_path` (`18`),
`::test_removal_grid_still_probes_the_removed_entity` (`44`) — are byte-identical at every
seed, as are the remaining `26` tests (they book nothing).

### 3.2 WHERE in those tests

Caller-chain diff. Every moving call is on one path:

```
wildcard.py:600:_add_tuple_trusted <- wildcard.py:563:add_tuple    [2525, 2528, 2522, 2520]
wildcard.py:601:_add_tuple_trusted <- wildcard.py:563:add_tuple    [2525, 2528, 2522, 2520]
```

Not `wildcard.py:415` (`_sync_entity_middles`'s re-ensure) and not `wildcard.py:540` (the
migration's crossable-types walk): both are seed-invariant. So this is **write volume**, not
a different entity walk.

---

## 4. MEASURED 2026-09-21 — the mechanism

### 4.1 Same raw tuples posed, different number of leaf writes

| | seed `0` | seed `1` | seed `2` | seed `3` |
|---|---|---|---|---|
| `RuleSet.apply` calls (raw tuples POSED) | `7499` | `7499` | `7499` | `7499` |
| `add_tuple` calls (leaf writes ATTEMPTED) | `3364` | `3369` | `3360` | `3356` |

**READ** — `tests/parity.py::_GraphSide.apply`:

```python
try:
    wm = outbox_watermark(self.session, 'pg')
    for d in self.ruleset.apply(triple):
        fn(...)                       # widx.add_tuple, once per fanned-out leaf
    ...
    return True
except ValueError:
    self.session.rollback()
    return False
```

**READ** — `zanzibar_utils_v1.py::RuleSet.apply` builds `seeds` as a **set comprehension**
over the matching `RewriteFilter`s and then either `yield from seeds` (fast path) or drains
`unprocessed.pop()`. `RelationalTriple` is a frozen dataclass of strings, so its hash — and
therefore that set's iteration order — moves with `PYTHONHASHSEED`.

So when one member of a fan-out is refused, the loop dies there and **how many writes
already completed is the raiser's position in a set iteration order.**

### 4.2 The abort census — positions move, counts do not

`(exception, position-in-fan-out) -> occurrences`, seed `0` vs seed `1`:

```
::test_dense_regime...   AdmissionRejected pos=2   [ 3,  0]
::test_dense_regime...   AdmissionRejected pos=3   [ 8, 11]
::test_sparse_regime...  AdmissionRejected pos=2   [ 2,  0]
::test_sparse_regime...  AdmissionRejected pos=3   [ 8, 10]
```

The arithmetic closes exactly, which is what makes this an identification rather than a
correlation:

| | seed `0` | seed `1` | Δ |
|---|---|---|---|
| dense: aborts | `3 + 8 = 11` | `0 + 11 = 11` | `0` — invariant |
| dense: writes completed before the abort | `3·1 + 8·2 = 19` | `0 + 11·2 = 22` | `+3` |
| dense: `add_tuple` | `2525` | `2528` | `+3` ✔ |
| dense: `_ensure/raw` | `4944` | `4950` | `+6 = 2 ×` ✔ |
| sparse: aborts | `2 + 8 = 10` | `0 + 10 = 10` | `0` — invariant |
| sparse: writes completed before the abort | `2·1 + 8·2 = 18` | `0 + 10·2 = 20` | `+2` |
| sparse: `add_tuple` | `801` | `803` | `+2` ✔ |
| sparse: `_ensure/raw` | `1593` | `1597` | `+4 = 2 ×` ✔ |

The `2 ×` is `_ensure_bridges(subject)` + `_ensure_bridges(obj)` at `wildcard.py:600-601`.
**The number of refusals is invariant; only where they land in the fan-out moves.**

### 4.3 The decisive arm: sort the fan-out

`--sorted-fanout` makes `RuleSet.apply` yield the same multiset of writes in a
deterministic order and changes nothing else. (Materialising the generator is safe for this
claim: the raiser is the CONSUMER, `add_tuple`; `RuleSet.apply`'s own `AdmissionRejected`s
fire before the first yield, so they cannot be re-ordered into or out of existence.)

```
seed 0: raw=6627 bridges=6829 ruleset_apply=7499 add_tuple=3369  31 passed
seed 1: raw=6627 bridges=6829 ruleset_apply=7499 add_tuple=3369  31 passed
seed 2: raw=6627 bridges=6829 ruleset_apply=7499 add_tuple=3369  31 passed
seed 3: raw=6627 bridges=6829 ruleset_apply=7499 add_tuple=3369  31 passed
```

Every column, every nodeid, every caller cell: `0 MOVED`. **Fan-out order is the mechanism.**

---

## 5. Scope — what this is NOT

* **Not a correctness defect.** `31 passed` at every seed and under the sorted arm; the
  refusal, the rollback and the resulting store are the same. `TK89` already recorded that
  every other census column (`parse_total` `1858`, `parse_crossable` `24`, `_ensure/EFF`
  `78`, `_sync/raw` `44`, `_sync/EFF` `20`, `CTL` `166`) holds still, and that is
  reproduced here. **"Known live correctness bugs: 0" is undisturbed.**
* **Not a reason to change production.** Sorting the fan-out is a real (small) cost on the
  live write path (`connectedstore/apply.py::_apply_row` consumes the same generator) and
  buys nothing observable. It was used here as an instrument, not proposed as a fix.
* **Not the acceptance columns.** Trap (a) already says a raw call count is not reach, and
  no acceptance table has ever quoted this column. `TK77`, `TK87` and `TK89` are undisturbed.

**One thing IS left open, deliberately** (§7, filed as `TK95`): the outcome-equivalence of a truncated
fan-out is relied on and not pinned by any test.

---

## 6. What landed

| file | change |
|---|---|
| `formal/probes/tk93_ensure_raw_bisect_2026-09-21.py` | NEW — per-nodeid/per-caller attribution, the `--seeds` between-seed arm, the `--sorted-fanout` mechanism arm, the abort census, four instrument controls |
| `formal/probes/tk77_crossable_census_2026-09-19.py` | trap (c) rewritten (it asserted the opposite); the warning printed above every table rewritten; **the live seed welded onto the `_ensure/raw` column header** |
| `docs/tk89-census-reproducibility-2026-09-20.md` | dated correction at the top — §5.3a's headline is refuted, its three lessons survive, a fourth is added |
| `docs/tk93-ensure-raw-seed-dependence-2026-09-21.md` | this file |

**The mechanical remedy is the column header, not a doc warning.** A census number gets
transcribed far more often than its probe gets re-read — both `TK77`'s and `TK87`'s tables
were pasted from stdout — so the seed now travels *inside the column name*:
`_ensure/raw@seed=0`, or `_ensure/raw@UNSEEDED` when nobody set one. Two tables at different
seeds can no longer be silently differenced by a reader who never opened the probe.
Deliberately NOT done: a tolerance band on the column, which the row forbids and which would
now be actively wrong — within a seed the column is exact.

---

## 7. Owed, and why it is a separate item

**The outcome-equivalence of a TRUNCATED fan-out has no test.** MEASURED: `21` raw tuples
per run die mid-fan-out, **all `21` of them at position `≥ 2`** (there is not one abort at
position `1` at either seed) — so every single one leaves at least one leaf write already
applied inside the transaction. Correctness rests entirely on `_GraphSide.apply`'s
`rollback()` (and, in production, on `_apply_row`'s transaction) undoing exactly the
completed prefix — a prefix whose CONTENTS vary with the hash seed. Nothing asserts that the
post-rollback store is independent of that prefix. It evidently is (`31 passed` at four seeds, and the set engine
agrees, which is the equivalence referee), but that is a run-wide consequence, not a pin.

Filed as **`TK95`** rather than bolted on here: it needs a fixture whose fan-out has `≥ 2`
leaves with one refused, both orders driven, byte-identical snapshots asserted, and — per
`docs/sabotage-procedure.md` — a mutation sweep of the whole module, not one sabotage.
`TK93`'s acceptance is localisation, and that is done.
