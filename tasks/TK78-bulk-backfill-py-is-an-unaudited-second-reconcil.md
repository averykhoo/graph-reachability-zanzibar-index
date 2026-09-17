---
id: TK78
title: bulk_backfill.py is an unaudited second reconcile implementation; backfill() discards _bumped
brief: no quiescence/settle/fixpoint check of any kind on the offline bootstrap path; processor.py:1726 drops the bump list
pri: LATER
size: M
deps: []
related: [TK74]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-18
moved: 2026-09-18
updated: 2026-09-18
closed:
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-09-18

REASONED / READ by the `TK74` fan-out completeness critic (2026-09-18), NOT re-verified first-hand here. Flagged, not claimed -- the first action is verification.

Two derived-state producers got zero attention in the whole `TK73`/`TK74`/`TK75` line of work:

* **`index_v4/bulk_backfill.py`** says at `:20` that it "mirrors `DeltaProcessor._reconcile` step for step", and `index_v4/bulk_build.py:29` claims the result is "byte-identical to running `DeltaProcessor.backfill()` per object". It emits no outbox rows and contains **no quiescence, settle, or fixpoint check of any kind** (the only two `InvariantViolation` raises, `:243` and `:255`, are unrelated). It is the offline bootstrap path behind `connectedstore.build_index`.
* **`index_v4/processor.py::DeltaProcessor.backfill`** (`:1714-1726`) ends with `self._bumped = []` -- **DISCARDING** the bump list that `::_run_cascade` fans out into its invalidation map (twice). Plausibly sound because backfill sweeps every object in topo order, but a bump landing on a LOWER stratum from a HIGHER stratum's reconcile would be dropped.

WHY IT MATTERS: if `TK74`'s answer is "a per-write staleness check should exist", these two paths silently get none -- and a second reconcile implementation that mirrors the first "step for step" is precisely the kind of claim that rots without a differential pin.

FIRST ACTION: verify the two readings above first-hand (they are a subagent's), then decide whether `bulk = replay` deserves a DIFFERENTIAL pin in Python rather than only the Lean statement `P24` proposes. Related: `P24` (Lean `bulkState = replay`), `TK74`.
