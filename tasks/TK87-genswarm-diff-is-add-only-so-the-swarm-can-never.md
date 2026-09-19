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
moved: 2026-09-19e
updated: 2026-09-19e
closed:
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
