# TK121 -- recovering an async index stalled on a path-count poison row (2026-10-04f)

**FROZEN 2026-10-04f, at `TK121`'s close -- provenance, not a living document.** Status
lines below are as-of-then. Corrections are appended dated at the top, never edited into
the body. Row: `python scripts/task.py show TK121`. Filed from
`docs/tk111-stall-aware-freshness-2026-10-02.md` when `TK111` closed.

## 1. What the row assumed, and what the tree says (READ first-hand 2026-10-04f)

The row's UNVERIFIED recovery was: remove the offending tuple at the source, build a FRESH
index under a NEW index store id from the current snapshot, then "repoint readers".

**The last step does not exist for a `ConnectedStore` user.** `ConnectedStore.__init__`
hard-wires the index to the source's own store id: `open_graph_index(session, store_id)` and
`ensure_cursor(session, store_id, store_id)` (`connectedstore/store.py::ConnectedStore.__init__`).
There is no parameter that opens a `ConnectedStore` over a separately-built index, so a
separate-id `build_index` produces an index nothing in the composed system can read or tail.

The other two facts the row relied on hold:

- `connectedstore/build.py::build_index` refuses an index store that has a cursor
  (`"build_index is for fresh builds"`) or any `NodeV4` row.
- `build_index` applies the same bound: both constructors refuse a snapshot that exceeds
  `index_v4/core.py::MAX_PATH_COUNT` with `PathCountExceeded`
  (`tests/test_tk111_path_count_bound.py::test_both_build_index_constructors_apply_the_same_bound`).
  So the source-side REMOVE is a precondition, not an option: a snapshot that still holds the
  poison tuple cannot be materialised at all.

So the only recovery that leaves a working `ConnectedStore` is **in place**: delete the index
store's graph state and rebuild it from the snapshot under the same id. By hand that is
deletes across four index tables plus a cursor reset, and getting it wrong is dangerous:
leaving `ResidueRefV1` / `ResidueV1` rows behind gives residues that name node ids the
rebuild then hands to different nodes -- the `ZT-P0-1` escalation class.

## 2. The decision (REASONED, the session's call under `CLAUDE.md` "Who decides")

Add `connectedstore.build.rebuild_index(session, source_store_id, index_store_id=None, *,
bulk=True)`. One transaction:

1. clean-session guard (same as `build_index`); refuse when the index has NO cursor (that is
   a fresh build: use `build_index`);
2. take the graph store lock (`ReachabilityIndex._lock_store`), so a concurrent `catch_up`
   cannot interleave;
3. delete this index store's `EdgeV4`, `ResidueRefV1`, `ResidueV1`, `NodeV4` rows (FK order);
4. run the SAME build body as `build_index` (refactored into one shared function, so the two
   cannot drift);
5. reset the EXISTING cursor row to the watermark and clear the stall marker. Reused, not
   deleted: other instances hold that row in their sessions, and `refresh()` must find it.

What it deliberately does NOT touch:

- `DeltaOutboxV1`. Its ids are a consumer cursor domain; emptying it restarts ids at 1 on
  SQLite (the reason `index_v4/outbox.py::prune_outbox` keeps the head row). The old rows are
  drained history -- every in-tree consumer reads only `id >` a watermark captured inside its
  own transaction, and `DeltaProcessor.backfill` does not read the outbox at all. The rebuild
  appends its own ADDED rows above them, exactly as a fresh build would.
- `StoreV4`, `SchemaV4`, `TupleV1`, `TupleLogV1`: the source of truth and the store row.

On ANY failure the transaction rolls back, so the old index AND its stall marker survive
intact. That is the property that makes the entry point safe to try: a rebuild against a
snapshot that still overflows (step 1 skipped) leaves reads exactly as correct as before
(untokened `check` -> set engine, lookups refuse with `IndexStalled`).

Rejected: a separate-id build plus a "repoint" parameter on `ConnectedStore`. It is a new
public surface (which cursor, which `StoreV4` row, what happens to the old index) to solve a
problem an in-place rebuild solves with no new reader-side concept.

## 3. The operator procedure

1. Read `ConnectedStore.stall_error`: it names the refused write and its closure row.
2. Remove (or otherwise break) that tuple at the SOURCE: `cs.remove_tuple(...)` works on the
   async schedule while stalled -- it only appends to the log.
3. Stop the async worker for that store (a concurrent writer makes `rebuild_index` refuse with
   "concurrent writes"; nothing is lost, retry when quiescent).
4. `rebuild_index(session, store_id)` on a clean session.
5. Every other instance calls `refresh()`; the stall is gone and the index serves again.

## 4. Pins and the mutation sweep (PROBED first-hand 2026-10-04f)

`tests/test_tk121_stall_recovery.py`, 9 tests (`pytest --collect-only`):

- `test_k31_poison_row_recovers_by_source_remove_then_rebuild[bulk]`: the real `TK111`
  K=31 diamond, async. It pins the PREMISE (after the source REMOVE, `catch_up` is still
  stalled, lag 3) and then the recovery. After the rebuild there is no stall, lag is 0 and
  the cursor row is the same object. Graph == set engine == oracle over the K=31 grid plus
  mallory, read from the index directly. Lookups are served, and a later async write
  catches up normally.
- `test_rebuild_that_cannot_succeed_changes_nothing[bulk]`: skips the source REMOVE. The
  rebuild raises `PathCountExceeded`, and every row count, the edge projection, the stall
  marker and the fallback reads stay the same. The `IndexStalled` message now names the
  recovery.
- `test_rebuild_refuses_concurrent_writes_and_changes_nothing`: the watermark re-check is
  shared with `build_index` and is atomic.
- `test_rebuilt_state_equals_a_fresh_build_on_a_boolean_schema[bulk]`: `_BOOLEAN` with
  churn, so residues and refs exist. Junk is planted in all four cleared tables first. The
  rebuilt state must equal a fresh `build_index` of the same snapshot exactly (natural
  keys, from `tests/test_bulk_build.py`'s projections). The outbox is kept, and new ids
  land above the old ones.
- `test_rebuild_requires_an_existing_index_and_a_clean_session`: the guards, plus a
  separate-id index.
- `test_replica_reader_sees_the_recovery_after_refresh`: file DB, two sessions, K=3 under a
  monkeypatched bound of 7.

Sweep (`.scratch/tk121/sweep.py`, gitignored, so the result is recorded here): 16
mutations of `connectedstore/build.py::rebuild_index` plus an `M0` control. **15 RED, 1
INERT.**

```
BASELINE 9 passed
M0  test claim lag()==0 -> 1        RED  k31 recovery (attribution correct)
M1  keep EdgeV4                     RED  k31, concurrent, guards, fresh-build
M2  keep ResidueV1                  RED  fresh-build
M3  keep ResidueRefV1               RED  fresh-build
M4  keep NodeV4                     RED  k31, concurrent, guards, cannot-succeed, fresh-build
M5  also wipe DeltaOutboxV1         RED  fresh-build (outbox monotone)
M6  stall marker not cleared        RED  k31
M7  cursor not moved to watermark   RED  k31, replica
M8  no quiescence re-check          RED  concurrent
M9  cursor row deleted + recreated  RED  k31 (identity pin only)
M10 no _lock_store()                INERT
M11 no rollback on failure          RED  concurrent, cannot-succeed
M12 no clean-session guard          RED  guards
M13 no existence guard              RED  guards
M14 no source-mismatch guard        RED  guards
M15 bulk flag ignored               RED  k31 (constructor label)
M16 watermark off by one            RED  k31, guards, fresh-build, replica
```

Explained (REASONED):

- **M10 is INERT on SQLite by construction.** The rebuild's own DELETEs take SQLite's
  database write lock anyway, so no SQLite test can tell whether `_lock_store` ran. Only a
  PostgreSQL concurrency test (a `catch_up` blocked on the `StoreV4` row) could, and none
  is written. Recorded, not faked.
- **M9 is caught by one pin only.** The replica test stayed green because SQLite gives the
  recreated cursor row the deleted row's rowid, so the reader reloads it by primary key.
  On PostgreSQL the id would differ. The `report[0] is cs.cursor` identity pin is what
  catches it.
- M16 was labelled "watermark read before the lock". What it actually does is shift the
  watermark by one, so it pins the cursor value, not lock ordering.

Also fixed: the `IndexStalled` docstring and refusal message said "raise the fan-out cap".
That stopped being a remedy at `TK112`, when `catch_up` began running uncapped. Both now
name the source REMOVE plus `rebuild_index`. Sabotaging the message back to the old text
turns `test_rebuild_that_cannot_succeed_changes_nothing` red (2 failed, observed).

## 5. Status

Landed 2026-10-04f: `connectedstore/build.py::rebuild_index` (exported from
`connectedstore`), the shared `_materialise` / `_require_quiescent` /
`_require_clean_session` helpers, the operator procedure in
`docs/architecture/system.md` § "Bootstrap and schema changes", and the pins above.
