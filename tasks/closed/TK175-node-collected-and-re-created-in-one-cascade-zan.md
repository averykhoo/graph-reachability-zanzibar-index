---
id: TK175
title: node collected and re-created in one cascade: zanzibar_node UNIQUE violation on a self-parent tuple
brief: self-parent tuple: node collected then re-created in one cascade hit zanzibar_node UNIQUE; fixed in 0.1.1
pri: LATER
size: S
deps: []
related: [TK174]
parent:
labels: []
source: hand
source_hash:
created: 2026-10-30b
moved: 2026-10-30b
updated: 2026-10-30b
closed: 2026-10-30b
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-10-30b

Map: docs/tk175-self-parent-node-recreate-2026-10-30.md. Found by the gate (test_hypothesis add_then_remove, rare draw). Self-parent doc:d1 parent doc:d1 under r1 = r0 but not (r0 from parent), r2 = r1 from parent: _gc_public_node deletes the doc:d1#r1 node (pending), then r2 re-interns it via ReachabilityIndex.node; SQLAlchemy flushes INSERT before DELETE -> UNIQUE. 0.1.0 impact: sync add raised raw IntegrityError (rolled back, valid tuple unwritable); async stalled the index. No wrong answer. Fix: core.py::ReachabilityIndex.node flushes pending deletes before creating (bookkeeping, not a CORRESPONDENCE anchor). Pin tests/test_tk175_self_parent_node_recreate.py, 3 red with the guard removed. Ships in 0.1.1.
