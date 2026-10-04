---
id: TK121
title: async poison row (path-count bound) has no documented recovery; pin rebuild-from-snapshot
brief: async PathCountExceeded row stalls forever; reads correct; recovery = fresh index from snapshot, untested
pri: NOW
size: S
deps: []
related: [TK111, TK112]
parent:
labels: []
source: docs/tk111-stall-aware-freshness-2026-10-02.md
source_hash:
created: 2026-10-03b
moved: 2026-10-04f
updated: 2026-10-04f
closed: 2026-10-04f
---

Filed 2026-10-03b when TK111 closed. What TK111 left, by design: a logged row the index can
NEVER apply still stalls the async apply step permanently. The fan-out cap no longer does
this (TK112: `catch_up` is uncapped). But the path-count bound
(`index_v4/core.py::MAX_PATH_COUNT`, `PathCountExceeded`) is a storage-width fact, it is
never suspended, and `TupleSource` admission cannot see the closure, so it cannot refuse the
row before it is logged. Reads are correct while stalled (the TK111 stall marker: untokened
`check` falls back to the set engine, lookups refuse with `IndexStalled`). But the index is
unavailable for that store, and there is NO documented or tested way back:
- the poison row is BEFORE any corrective REMOVE in the log, so `catch_up` never reaches
  that REMOVE;
- `connectedstore/build.py::build_index` refuses a store that already has a cursor
  ("build_index is for fresh builds");
- so recovery today is, UNVERIFIED: remove the offending tuple at the source, then build a
  FRESH index under a new index store id from the current snapshot, then repoint readers.

Scope of the item: write the recovery down as an operator procedure, and pin it with a test
that runs the TK111 K=31 diamond async, stalls, recovers, and ends with graph == set engine
== oracle and no stall. Optional: decide whether a "rebuild in place" entry point (drop the
index store's rows, then `build_index`) is worth adding. Unreachable without a K>=31 diamond
of parallel paths, hence LATER.

## Log

### 2026-10-04f

CLOSED: recovery is connectedstore.rebuild_index (in place), pinned in tests/test_tk121_stall_recovery.py (9 tests, the real K=31 diamond, both constructors). The row assumed "fresh index under a new store id, then repoint readers"; READ first-hand, ConnectedStore hard-wires the index to its own store id, so nothing can be repointed. Hence in place: one transaction under the store lock that deletes Edge/ResidueRef/Residue/Node rows, runs the shared build body (_materialise, also used by build_index), reuses the cursor row and clears the stall. The outbox is kept so ids stay monotone. On any failure nothing changes, so the old index and its stall survive. Premise pinned: after the source REMOVE, catch_up is STILL stalled. Rebuilt state == a fresh build of the same snapshot on _BOOLEAN with junk planted in all four tables. Sweep: 16 mutations plus M0, 15 RED, M10 (no _lock_store) INERT on SQLite by construction, PG-only. IndexStalled text no longer says "raise the fan-out cap" (dead since TK112). MIN_TESTS_ALL ratcheted 1575 -> 1744 (+9 new, +160 drift). Map: docs/tk121-stall-recovery-2026-10-04.md. Operator procedure: docs/architecture/system.md, Bootstrap section.
