# `TK87` — giving the swarm a removal pass (the last zero in `TK77`'s acceptance table)

**ACTIVE-PLAN, opened 2026-09-19f — the body is provenance, not a living status.** Every
figure below was measured first-hand on 2026-09-19f against the live tree, with the commands
in §6. Live state is the task row (`python scripts/task.py show TK87`) and
`python scripts/gate_status.py` — never this file. Corrections append **dated at the top**,
never edited into the body. Freeze it when `TK87` closes.

Provenance labels: **MEASURED** (first-hand run this session), **READ** (first-hand from the
named `file::symbol`), **REASONED** (derived from a READ, not separately observed). Nothing
here is agent-reported; no subagent was used.

⚠ **CORRECTION 2026-09-20g (`TK89`) — §1'S FLAGGED DISCREPANCY IS CLOSED, AND §1 WAS
RIGHT.** §1 recorded `parse_crossable` **18** against `TK77`'s **17** and refused to
reconcile them arithmetically. **MEASURED 2026-09-20g** in a `git worktree` at `399ea99`,
twice, `PYTHONHASHSEED=0`, byte-identical both times: **18**, alongside `parse_total`
**1661**, `_ensure/EFF` **46**, `CTL` **110** and `28 passed` — this section's transcript,
character for character. `TK77`'s `17` was taken mid-change against an uncommitted working
tree that no longer exists; the two numbers are not two measurements of one tree, and
"nobody has explained the difference" is now "the trees differed".

⚠ One column in that transcript does NOT reproduce: `_ensure/raw` **6521** here, **6547** at
seed 0 on the same commit, and `6589/6609/6617/6627` across six runs at HEAD — it varies at a
FIXED hash seed and the mechanism is unidentified (`TK93`, trap (c) in
`formal/probes/tk77_crossable_census_2026-09-19.py`). **§2's headline is untouched**:
`_sync/raw` `0 -> 44` and `_sync/EFF` `0 -> 20` are both reproducible columns.
Full write-up: [`tk89-census-reproducibility-2026-09-20.md`](tk89-census-reproducibility-2026-09-20.md).

---

## 1. The premise, re-measured before touching anything

`TK77` closed with one zero left in its acceptance table and attributed it to
`tests/genswarm.py::Diff` being add-only. **MEASURED 2026-09-19f**, the baseline, before any
edit — the same command and the same instrument `TK77` used:

```
python formal/probes/tk77_crossable_census_2026-09-19.py --pytest \
    tests/test_generator_coverage.py -q -p no:cacheprovider -s

module                            parse_total  parse_crossable  _ensure/raw  _ensure/EFF  _sync/raw  _sync/EFF   CTL
tests/test_generator_coverage.py         1661               18         6521           46          0          0   110
28 passed in 103.80s
```

Two things this run settles that the row could only assert:

* **`_sync/raw` is `0`, not merely `_sync/EFF`.** The module did not reach
  `index_v4/wildcard.py::_sync_entity_middles` and get turned away at its `crossable_shapes`
  guard — it never called it. **READ**: every caller of that method is a removal path
  (`::remove_edge`, `::remove_node`, and `index_v4/processor.py`'s reconcile-time GC), and
  `Diff` exposed `add` and `sweep` only. The zero is structural, exactly as the row said.
* **`CTL` is `110`**, so the instrument is alive: the zero is a real zero and not a dead
  patch (the census probe's trap (b)).

⚠ **One figure disagrees with the `TK77` row and is NOT reconciled here.** The row records
`parse_crossable` **17** for this module at 2026-09-19e; this run, on the same tree with the
same command, books **18**. Both are first-hand; nobody has explained the difference, and it
must not be reconciled arithmetically — it is a fifteen-minute question for whoever next
touches the census, not a number to average. The `_ensure/EFF` `46` and `CTL` `110` match the
row exactly.

## 2. What landed, and the one design decision worth defending

**The capability** (`tests/genswarm.py`):

| symbol | what it is |
| --- | --- |
| `Diff::remove` | the mirror of `::add` — unanimous accept/reject across graph + both set engines or `AdmissionDivergence`, `present` updated, `_names` deliberately not unwound |
| `Diff::restored` | side names whose row multiset differs from construction; meaningful only after every admitted write is removed |
| `grid_for(..., extra_names=)` | the grid keeps probing an entity after its last tuple is gone (§2.1) |
| `drive_config(..., churn=False)` | the removal pass, opt-in |
| `RunResult.removed` / `.remove_comparisons` / `.unrestored` | the removal half counted SEPARATELY from the add half |

**The pins** (`tests/test_generator_coverage.py` §6b):
`test_churn_pass_reaches_the_i14_remove_path`,
`test_removal_grid_still_probes_the_removed_entity`,
`test_churn_pass_never_sweeps_an_empty_store`.

**DECISION: churn is OFF by default and the two regimes do not use it.** The row's own
warning is that adding removes *changes what a regime IS* — `subsets_for`'s `SPARSE` /
`DENSE` / `FULL` each mean *which subset of the pool is applied*, and the two positive
controls plus the non-vacuity floors are calibrated against a monotone pool. The churn pass
does not touch `subsets_for`: it appends to each subset's drive, after that subset's sweep.
So the add half is unchanged, and it is unchanged in the strong sense —
**MEASURED** (§3.2): sparse comparisons `churn=False` **62 691**, `churn=True` **124 644**,
and the removal half alone is **61 953**; `124644 − 61953 = 62691` exactly. The add-phase
sweep is the same sweep, query for query.

### 2.1 Why the grid needed `extra_names` — the trap inside the trap

`grid_for` derives its query universe from the tuples that are PRESENT. Under a monotone
driver that is right. Under a removal pass it is a silent hole: the moment a tuple is
removed, the entity it named leaves the grid, and a stale-closure over-grant on a
just-revoked entity — the single most likely thing a removal sweep is for — has no query
left to catch it. `GHOST` is not a substitute: a name that was never written and a name that
was written and revoked take different paths through the index. `Diff` therefore passes
every name it has ever admitted. (**READ**: before `TK87`, `Diff._names` was written on every
add and read nowhere.)

## 3. What the churn pass reaches

### 3.1 Reach, per regime, over the 96 driven configs that compile at `K<=2`

**MEASURED 2026-09-19f**, `formal/probes/tk87_churn_reach_2026-09-19.py reach <regime>`:

```
regime   accepted  removed  removal-comparisons  _sync/raw  _sync/EFF  unrestored  divergences
sparse        470      467                61953       1717         10           0            0
dense        1967     1967                61659       5164         36           0            0
```

All of the `_sync/EFF` comes from the single crossable driven config `{owc, ts_wildcard}`
(sparse `10`, dense `36`) — which is the config
`test_driven_config_space_reaches_a_crossable_schema` exists to keep from silently becoming
zero. **`_sync/raw` 0 → 1717 is the headline**: the swarm now executes removals at all.

`unrestored 0` across all 96 configs, under both regimes, is a stronger result than the item
asked for: add-then-remove-everything returns every backend to a byte-identical row multiset
on every generated schema in the driven space, not just on the hand-built fixtures.

### 3.1b The acceptance column, measured with `TK77`'s own instrument

Same command as §1, after the change — the only comparison that settles the item:

```
module                            parse_total  parse_crossable  _ensure/raw  _ensure/EFF  _sync/raw  _sync/EFF   CTL
before (2026-09-19f baseline)            1661               18         6521           46          0          0   110
after  (2026-09-19f)                     1858               24         6609           78         44         20   166
                                   28 passed in 103.80s  ->  31 passed in 104.93s
```

`_sync/EFF` **0 → 20** is `TK77`'s acceptance target for this module, and `_sync/raw`
**0 → 44** is the structural fact underneath it. `CTL` rising with it (110 → 166) is the
ceiling control moving in the same direction, which is what distinguishes "reached more" from
"instrument counted more". The three new tests cost **1.1 s** of the module's 105 s.

### 3.2 Cost, if the regimes ever adopt churn

**MEASURED 2026-09-19f**, `... regimes <regime>`, same configs and same seed:

```
regime   churn=False          churn=True            detection sets
sparse   41.0 s   62691 cmp    74.2 s  124644 cmp     identical (both EMPTY)
dense    58.1 s   61659 cmp   117.3 s  123318 cmp     identical (both EMPTY)
```

Both rows carry the same arithmetic: `124644 - 61953 = 62691` and `123318 - 61659 = 61659`
— the add-phase comparison count with churn ON equals the whole comparison count with churn
OFF, exactly, on both regimes. Cost of adopting it inside the controls would be **+81%**
wall on sparse and **+102%** on dense.

⚠ **"Detection sets identical" is a WEAK statement today and must not be quoted as a strong
one.** Both arms detect nothing, because RC1/RC2 — the divergences the two regime tests were
written to detonate — have been fixed since `0838bcf` (§5). Two empty sets are equal for the
uninteresting reason. The load-bearing evidence that churn cannot disturb the controls is the
arithmetic in §2, not this row.

## 4. Sabotage: 9 mutations, 8 caught, and the INERT row that was MY bug

**MEASURED 2026-09-19f**, `formal/probes/tk87_churn_sweep_2026-09-19.py` (baseline green,
`7 passed`; every file restored from a byte copy; `git status` clean afterwards):

| id | mutation | verdict | attributed to |
| --- | --- | --- | --- |
| `M0` | HARNESS CONTROL — invert the reach pin's own final claim | CAUGHT | `test_churn_pass_reaches_the_i14_remove_path` |
| `M1` | drop `extra_names` from `Diff.grid` (the pre-`TK87` line) | CAUGHT *(INERT on run 1 — see below)* | `test_removal_grid_still_probes_the_removed_entity` |
| `M2` | `half = len(admitted)` — remove everything before the sweep | CAUGHT | the empty-store pin + the reach pin |
| `M3` | sweep ONLY at the end | CAUGHT | `test_churn_pass_never_sweeps_an_empty_store` |
| `M4` | `remove` stops updating `present` | CAUGHT | the reach pin + the grid pin |
| `M5` | PRODUCT: `_sync_entity_middles` made a no-op | CAUGHT | the reach pin, on `unrestored` |
| `M6` | PRODUCT: `remove_edge` stops syncing the OBJECT endpoint (`TK77`'s `N5`) | CAUGHT | the reach pin **and** `tests/test_wildcard_property.py::test_middle_sync_record_excludes_the_wildcard_entity` |
| `M7` | the removal half stops counting its own comparisons | CAUGHT | the empty-store pin + the reach pin |
| `M8` | drop the `admitted` dedupe | INERT *(predicted)* | — a count that no assertion claims |

★ **`M6` is the interesting row.** `TK77` recorded that mutation as caught by ONE test in the
whole suite, and explicitly NOT by `tests/test_i14_crossing_middles.py`, the module named
after the invariant, nor by its own 2026-09-19e remove pin. The churn pass reddens on it too,
`[('graph', 1)]` unrestored, from a GENERATED schema rather than a hand-written fixture. That
is the coverage this item bought, stated as a second independent catcher rather than as a
count.

⚠ **`M1` came back INERT on run 1, and the mutation was not the problem — my pin was.** The
first version of `test_removal_grid_still_probes_the_removed_entity` removed the last
admitted tuple and asserted on both of that tuple's names; a sibling tuple still named one of
them, so `present` still carried it and the grid never shrank. The pin CLAIMED a property it
did not measure, and it read exactly like a clean row. It was caught only because `M1` was
written to move the property the pin claimed, which is the whole argument for sweeping a
module rather than sabotaging one test. The test now removes every tuple naming its victim
and refuses outright if that stops being true. Literal outputs for `M1`, `M3`, `M5`, `M6` are
in the three docstrings.

## 5. What this did NOT do

* **The two regimes still drive monotonically.** Churn exists and is pinned; adopting it
  inside `test_sparse_regime_finds_no_fail_closed_divergence` /
  `..._dense_..._fail_open_...` would cost ~+81% wall on sparse (§3.2) and, per §3.1, has
  found nothing extra on the 96-config driven space (and +102% on dense). Worth revisiting
  only with a defect
  injected that a removal can expose — the synthetic-defect machinery
  (`genswarm::dropped_parent_defect` / `::detect_synthetic`) is the place to build it.
* **`TK88` (filed 2026-09-19f): `tests/test_generator_coverage.py` still says it is RED.**
  Line 15 — *"THIS MODULE IS EXPECTED TO BE RED UNTIL RC1/RC2 ARE FIXED"* — plus line 761 and
  the `★ CURRENTLY RED` openers on both regime test docstrings. **MEASURED 2026-09-19f**:
  the module is `28 passed`, `tests/test_ttu_tupleset_parent_types.py` is `12 passed`, and
  **READ**: RC2 was closed at commit `0838bcf` (*"the 2026-08-10 fail-open family is
  CLOSED"*). A module that announces it is expected to be red is a module whose genuine red
  reads as normal.
* **The `parse_crossable` 17-vs-18 discrepancy of §1 is open**, and deliberately not
  reconciled.

## 6. Reproducing

```
python formal/probes/tk87_churn_reach_2026-09-19.py reach   sparse   # section 3.1
python formal/probes/tk87_churn_reach_2026-09-19.py reach   dense
python formal/probes/tk87_churn_reach_2026-09-19.py regimes sparse   # section 3.2
python formal/probes/tk87_churn_sweep_2026-09-19.py                  # section 4
python formal/probes/tk77_crossable_census_2026-09-19.py --pytest \
    tests/test_generator_coverage.py -q -p no:cacheprovider -s       # section 1 + the acceptance column
```

⚠ The sweep **edits tracked files in place** and restores them from a byte copy; do not run
it on a dirty tree you care about, and check `git status` afterwards.
