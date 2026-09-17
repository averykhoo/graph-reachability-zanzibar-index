---
id: TK75
title: hunt the SECOND late-emission site (_sync_entity_middles) and the unreproduced second TK73 witness
brief: TK73 left two unpinned: the strip-AND-re-add call site on crossable schemas, and a reported witness never reproduced
pri: LATER
size: S
deps: []
related: [TK73]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-17
moved: 2026-09-17
updated: 2026-09-17
closed:
---

## What it is

`TK73` fixed the cascade's terminal check after reconcile-time node GC emitted outbox rows
inside the last budgeted round. Two things about that emission were left open, and both are
about **coverage of the emitting surface**, not about the fix:

1. **`_sync_entity_middles` is a SECOND late-emission site.** It is
   `index_v4/processor.py::DeltaProcessor._gc_subject_node`'s final act (READ), and
   `::_gc_public_node` carries the same call. Unlike `_maybe_remove_bridges` it both
   **strips AND re-adds** bridges, so on a schema with non-empty `crossable_shapes` it can
   emit in both directions. A `TK73` verifier built a crossable schema and could not make
   it fire; there is no witness in hand.
2. **A SECOND independent witness was reported and never reproduced** -- a randomised sweep
   trial with leftover `('folder','owner','z')` on a schema adding
   `editor: [user, user:*]` (UNVERIFIED).

The settle-and-assert fix covers both **by construction** (it asks the semantic question
regardless of which call site emitted), so this row is about PINNING the surface, not
about a live bug.

## (!) Traps

- **(!) This is NOT a reopening of `TK73`.** The fix is call-site-independent on purpose.
  If a witness here raises, the interesting question is which CLAIM it breaks -- do not
  reach for the round budget (`TK73` measured that `rounds+1` silently repairs genuine
  staleness, which is why it was rejected).
- **(!) An `INERT` result here is the expected outcome, and that is the trap.** If a hunt
  finds nothing, say what the probe was supposed to move and check it moved -- an
  un-fireable probe reads exactly like a clean surface.
- **(!) `crossable_shapes` is EMPTY on the `TK73` witness schema** (it has no object
  wildcards), so that schema cannot exercise `_sync_entity_middles`' re-add arm at all.
  A new fixture is required; reusing the witness would be a green that proves nothing.

## Read first

- [`docs/tk73-cascade-quiesce-gc-2026-09-17.md`](../docs/tk73-cascade-quiesce-gc-2026-09-17.md)
  sec 3 (the emission mechanism) and sec 7 (both open items, labelled by provenance).
- `index_v4/processor.py::DeltaProcessor._gc_subject_node` / `::_gc_public_node` -- the two
  callers of `_sync_entity_middles`.
- `tests/test_cascade_quiesce_gc.py` -- the existing pin; a new shape extends this module.

## Log
