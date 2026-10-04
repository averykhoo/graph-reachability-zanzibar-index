---
id: TK79
title: the late-GC rows' design justification (a drain_deltas replica must see them) is pinned by nothing
brief: processor.py:1611 states it; no test asserts it; there is no in-tree outbox consumer at all
pri: NEXT
size: S
deps: []
related: [TK73, TK74]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-18
moved: 2026-10-04g
updated: 2026-10-04g
closed:
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-09-18

READ by the `TK74` fan-out completeness critic (2026-09-18); the grep half re-checkable in seconds.

`index_v4/processor.py:1611` carries the justification for NOT suppressing the late reconcile-time-GC outbox rows: they are "honest, balanced retractions (an external `drain_deltas` replica must see them)". That sentence is the reason the `TK73` fix asks a SEMANTIC question instead of simply dropping the rows -- i.e. **it is load-bearing for the shipped design**.

**Nothing in the tree asserts it.** `index_v4/outbox.py::drain_deltas` is called only from `tests/test_outbox.py`, `tests/test_index_v4.py:41` and `tests/test_boolean_compile.py:434` -- none of them about GC emission. `tests/test_cascade_quiesce_gc.py` never inspects outbox contents at all (grepped: no `outbox` in any assertion, 213 lines). And `connectedstore/source.py::catch_up_evaluator` tails the TUPLE LOG, not the outbox, so **there is no in-tree outbox consumer whatsoever**.

So the claim "a replica must see these rows" is untested in both directions: nothing shows a replica needs them, and nothing shows a replica fed them arrives at the right state.

FIRST ACTION: write the missing consumer-side property -- drain the outbox across a cascade that includes a reconcile-time GC strip, apply the deltas to an independent replica, and assert the replica's membership equals the primary's (and the oracle's). That is a real differential test of a claim the design rests on, and `tests/test_i14_crossing_middles.py::test_middles_retire_with_their_entity` is already a witness that produces such rows (`TK75` log, 2026-09-18), so the fixture exists.

### 2026-10-04g

PROMOTED LATER -> NEXT 2026-10-04g (user: NEXT raised to 5, ranked by correctness certainty). Why (READ 2026-10-04g): drain_deltas is called only from index_v4/outbox.py, index_v4/processor.py and three test modules (test_outbox, test_index_v4, test_boolean_compile); no consumer replays the drained stream, so the design premise that late-GC rows must reach a replica is unpinned. Cheap shape: replay the drained rows into a replica and compare it with the primary AND the oracle. Independent of TK120 ordering.
