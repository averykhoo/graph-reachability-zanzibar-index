---
id: TK87
title: genswarm Diff is add-only, so the swarm can never reach the I14 remove path
brief: the last zero in TK77 acceptance: _sync/EFF 0 because Diff has no remove op; changes what a regime IS
pri: LATER
size: M
deps: []
related: [TK77]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-19e
moved: 2026-09-19f
updated: 2026-09-19f
closed: 2026-09-19f
---

`tests/genswarm.py::Diff` exposes `add` and `sweep` only. `drive_config` therefore drives
every config as a monotone sequence of ADDS, and no swarm config of any shape can reach
`index_v4/wildcard.py::_sync_entity_middles` -- whose every caller is a removal path
(`::remove_edge`, `::remove_node`, and `index_v4/processor.py`'s reconcile-time GC). That is
the last zero in `TK77`'s acceptance table: after the 2026-09-19e generator change
`tests/test_generator_coverage.py` books `_ensure/EFF` 46 and CTL 110, and `_sync/EFF` **0**.

MEASURED 2026-09-19e (`formal/probes/tk77_crossable_census_2026-09-19.py --pytest`), and the
zero is structural, not a fixture or a weighting -- which is why `TK77` closed its own scope
without closing this.

Why it is not a one-liner. The swarm exists to fuzz ADMISSION SEQUENCES (`RC1`/`RC2` came
through order-dependent bridge cycles that only surface when writes interleave), and
`subsets_for`'s two regimes are tuned against a monotone pool: `SPARSE`/`FULL`/`DENSE` all
mean "which SUBSET of the pool is applied", with the comparison counts and the fail-open /
fail-closed controls (`test_sparse_regime_finds_no_fail_closed_divergence`,
`test_dense_regime_finds_no_fail_open_divergence`) calibrated on that. Adding removes changes
what a regime IS, so the two positive controls and the non-vacuity floors have to be re-read
rather than assumed. The cheap version -- append a remove pass after each subset's adds --
also has a real trap: an add-then-remove-everything sequence restores the row multiset, so a
sweep that only compares at the END would compare an EMPTY store and report success (that is
`::test_a_sweep_with_an_empty_pool_would_have_reported_success`, already in the module,
pointing at the same failure mode from the other side).

## Read first

- [`docs/tk77-crossable-census-2026-09-19.md`](../docs/tk77-crossable-census-2026-09-19.md)
  -- the 2026-09-19e dated append: the acceptance table, and the paragraph naming this gap.
- `tests/genswarm.py::Diff` / `::drive_config` / `::subsets_for` -- the driver contract that
  would change.
- `tests/test_generator_coverage.py::DRIVE_K` and the two regime tests -- what has to be
  re-read if a regime gains removes.

## Log

### 2026-09-19f

EXECUTED, with one decision recorded rather than taken. Map (ACTIVE-PLAN, freeze it with
this row): docs/tk87-swarm-churn-2026-09-19.md. Probes
formal/probes/tk87_churn_reach_2026-09-19.py (modes `reach`, `regimes`) and
formal/probes/tk87_churn_sweep_2026-09-19.py.

PREMISE RE-MEASURED FIRST (2026-09-19f, before any edit, TK77's own instrument):
tests/test_generator_coverage.py booked `_sync/raw` **0**, not merely `_sync/EFF` 0 -- the
module never called `_sync_entity_middles` at all, with `CTL` 110 proving the instrument was
alive. So the row's structural diagnosis was right.

LANDED (tests/genswarm.py): `Diff::remove` (unanimity or AdmissionDivergence, symmetric to
`::add`), `Diff::restored` (per-side row multiset vs construction), `grid_for(...,
extra_names=)`, `drive_config(..., churn=False)`, and `RunResult.removed` /
`.remove_comparisons` / `.unrestored` counted SEPARATELY from the add half. Three pins in
tests/test_generator_coverage.py section 6b:
`::test_churn_pass_reaches_the_i14_remove_path`,
`::test_removal_grid_still_probes_the_removed_entity`,
`::test_churn_pass_never_sweeps_an_empty_store`.

DECISION -- CHURN IS OFF BY DEFAULT AND THE TWO REGIMES DO NOT USE IT. The row's warning
("changes what a regime IS") is answered by not changing one: the churn pass does not touch
`subsets_for`, it appends after each subset's sweep. MEASURED, and this is the load-bearing
evidence rather than a claim: sparse comparisons churn=False 62691, churn=True 124644, removal
half 61953, and 124644-61953 = 62691 exactly; dense 61659 / 123318 / 61659, same identity. The
add-phase sweep is the same sweep, query for query, so both positive controls and the
non-vacuity floors keep measuring what they were calibrated on. Cost if ever adopted: +81%
wall on sparse, +102% on dense, for nothing found on the 96-config driven space. Revisit only
with an injected defect a REMOVAL can expose (`genswarm::dropped_parent_defect` /
`::detect_synthetic` is where that would be built).

REACH (MEASURED 2026-09-19f, all 96 driven configs that compile at K<=2): sparse 470 accepted
/ 467 removed / 61953 removal comparisons / `_sync/raw` 0 -> 1717 / `_sync/EFF` 0 -> 10; dense
1967 removed / `_sync/EFF` 36. Zero unrestored and zero divergences under both -- i.e.
add-then-remove-everything restores every backend byte-identically on every generated schema
in the driven space, which is stronger than the item asked for.

SABOTAGE: 9 mutations, 8 CAUGHT, `M0` control attributed, `M8` legitimately INERT (a count no
assertion claims). (!) `M1` came back INERT on run 1 and THE PIN WAS THE BUG, not the
mutation: the grid test removed one tuple and asserted on both its names, but a sibling tuple
still named one of them, so `present` never lost it. A pin that claims a property it does not
measure reads exactly like a clean row -- it was caught only because the mutation was written
to move the property the pin claimed. (!) `M6` is TK77's `N5`, the drop of `remove_edge`'s
OBJECT-endpoint `_sync_entity_middles` that `tests/test_i14_crossing_middles.py` stays GREEN
on and that TK77 recorded as caught by exactly one test in the suite: the churn pass reddens
on it too, from a GENERATED schema. That is the coverage this item bought.

FILED: TK88 -- tests/test_generator_coverage.py announces in five places that it is expected
to be RED; it is 28 passed, and RC1/RC2 were closed at 0838bcf about five weeks ago. Left
open, deliberately unreconciled: the census's `parse_crossable` 17 (TK77 row) vs 18 (this
session), same command and same tree.

ACCEPTANCE (MEASURED 2026-09-19f, TK77's instrument, whole module before and after):
`parse_crossable` 18 -> 24, `_ensure/EFF` 46 -> 78, `_sync/raw` **0 -> 44**, `_sync/EFF`
**0 -> 20**, `CTL` 110 -> 166, `28 passed` -> `31 passed` (the three new tests cost 1.1 s of
105 s). CTL moving with the EFF columns is what separates "reached more" from "the instrument
counted more".
