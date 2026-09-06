---
id: P24
title: Lean bulkState = replay -- build_index(bulk=True) under the headline, not the scope statement
brief: ReadEq: bulk constructor = replay through ReachedBy; GraphState has no multiplicity fields, say what it cannot cover
pri: SOMEDAY
size: M
deps: []
related: [P22]
parent:
labels: [formal]
source: board
source_hash: fb043667c009
created: 2026-09-06b
moved: 2026-09-06b
updated: 2026-09-06b
closed:
---

Filed 2026-09-06b as the deferred half of `P17` (user decision: option (c) now, Lean shape
SOMEDAY). A `ReadEq`-style theorem that the offline constructor (`index_v4/bulk_build.py`
+ `bulk_backfill.py`) reaches the same `GraphState` as replaying the same tuples through
`ReachedBy` would put `build_index(bulk=True)` under the headline theorems instead of
under the scope statement in `formal/FINAL_REVIEW.md` section 3.1 item 6 / 4(h).

(!) `GraphState` (`formal/lean/ZanzibarProofs/GraphIndex/State.lean:105-111`) carries no
refcount / path-count / `implicit` / `derived` / version fields. The theorem can only speak
to the projection the extractor compares; the edge MULTIPLICITIES that
`test_conformance_bulk_state.py` pins (sabotage: `incremental=3 bulk=1`) stay Python-only
either way. Say so in the statement's docstring rather than letting the name overclaim.

## Log

### 2026-09-06b

first reconciliation: filed from the board row this session; body carries the GraphState-fields caveat the row states
