---
id: TK78
title: bulk_backfill.py is an unaudited second reconcile implementation; backfill() discards _bumped
brief: no quiescence/settle/fixpoint check of any kind on the offline bootstrap path; processor.py:1726 drops the bump list
pri: NOW
size: M
deps: []
related: [TK74]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-18
moved: 2026-09-19f
updated: 2026-09-19f
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

### 2026-09-19f

PROMOTED to NOW 2026-09-19f by the session that closed TK77/TK87/TK72, with the reasoning
here rather than on the banner. No new work done on this row.

Why this one, of the fifty ready rows: it is the only open item whose FIRST ACTION is a
first-hand check of a possible EQUIVALENCE defect (`CLAUDE.md` sec  "Who decides": the
primary consideration is that the graph index gives the same answers as the set engine, and
`bulk_backfill.py` is a SECOND producer of derived state whose claim to match the first is
prose). Everything else near the top of `ready` is a coverage, perf or docs item.

(!) Its two readings are a subagent's (`TK74` fan-out, 2026-09-18) and are explicitly NOT
verified. Verify both first-hand before planning anything:
  1. `index_v4/bulk_backfill.py` has no quiescence/settle/fixpoint check -- grep the file,
     do not trust the summary;
  2. `index_v4/processor.py::DeltaProcessor.backfill` ends by discarding `self._bumped`, and
     whether a bump can land on a LOWER stratum during a topo-order sweep is the actual
     question -- construct it or show it cannot happen.

Two live precedents for why verification comes first: `TK72` (closed this session) was a
CONFIRMED-but-small item whose stale brief still said UNVERIFIED, and `TK67`, where a
subagent's "the symbol does not exist" nearly deleted a sound trap. A differential pin
(`bulk == replay` in Python, not only the Lean statement `P24` proposes) is the plausible
landing shape, but it is a DECISION for the verifying session, not a plan to inherit.
