---
id: TK121
title: async poison row (path-count bound) has no documented recovery; pin rebuild-from-snapshot
brief: async PathCountExceeded row stalls forever; reads correct; recovery = fresh index from snapshot, untested
pri: LATER
size: S
deps: []
related: [TK111, TK112]
parent:
labels: []
source: docs/tk111-stall-aware-freshness-2026-10-02.md
source_hash:
created: 2026-10-03b
moved: 2026-10-03b
updated: 2026-10-03b
closed:
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
