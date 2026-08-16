# Bulk-merge write path — SKETCH, unbuilt

> **SKETCH, unbuilt — the fuller 2026-07-19 design is still owed.** This is *not* a
> landed design record like [`p13-bulk-build-design.md`](./p13-bulk-build-design.md) or
> [`r4bf-bulk-backfill-design.md`](./r4bf-bulk-backfill-design.md); no code implements
> it and no test covers it. A fuller design sketch was produced 2026-07-19 in a
> read-only session and **was never written down** — a repo-wide search on 2026-08-16
> found no trace of it, so it must be re-derived, not recovered. Write the full design
> up in the style of `p13-bulk-build-design.md` **before implementing**. Tracked as
> board row `SD-4` in [`HANDOFF.md`](../../HANDOFF.md) (SOMEDAY — revisit only on a
> concrete large-batch ingest need). Migrated out of `HANDOFF.md` on 2026-08-16.

## What it is

A batch closure update **seeded from EXISTING state**: the one high-value UNBUILT write
optimization. It was never filed in the perf arc because it crosses the Lean/identity
bar — it is not a micro-optimization.

It sits between the two shipped paths:

| path | cost | restriction |
|---|---|---|
| incremental `advance_index` | per-edge `O(anc×desc)`, writes only the delta | none |
| from-empty `bulk_build` / `bulk_backfill` | one topo+DP pass, 30–200× faster | **REFUSES a non-empty store** |

**Goal:** apply a large batch to an already-populated index by loading the affected
region, recomputing the merged closure delta in memory (the bulk-builder DP seeded with
existing boundary path-counts), and writing back ONLY changed rows.

**When it wins:** the batch touches more than roughly 2–3% of the closure (incremental's
summed regions get expensive) but far less than the whole graph (a full rebuild
wastefully rewrites the untouched majority).

## The crux — why this is hard

⚠ **A merge must reproduce, against PRE-EXISTING rows, every coupled invariant the
from-empty builders are add-only exempt from.** That exemption is the entire reason the
shipped bulk paths are simple, and it does not survive seeding from existing state:

* `EdgeV4` direct/indirect counts, including boundary composition
* the I5 `derived` flag
* `ResidueV1` stars/neg/upos + version
* from-chain nodes
* node `reference_count` / implicit GC — **order-sensitive**
* sticky explicit promotion

…plus the remove/GC/diff cases (`_gc_*` deletes) that the from-empty mirrors never hit.

## Reuse

`bulk_build.py` Phases R/C/P/W, plus a `_BulkBackfill` recompute **scoped to affected
derived keys**.

## Gates it must pass

It changes a modeled algorithm, so:

* a **differential identity gate** mirroring `tests/test_bulk_build.py`: bulk-merge ==
  incremental `advance_index`, byte-identical modulo row ids;
* the hypothesis campaign, especially removes;
* a **Lean twin + `formal/CORRESPONDENCE.md` §7/§8 entry** — it is an "alternative
  constructor" in the same sense as P13 / R4-BF;
* the full phased `verify.sh` plus a fuzz sweep.

## Phasing

1. **Bench first.** No large-batch-on-large-index bench exists — build one, and confirm
   whether the cascade or the closure DP dominates. (Per
   [`../perf-next-round.md`](../perf-next-round.md)'s reopening rule, the motivating
   measurement comes before the work, not after.)
2. Add-only merge behind a **distinct entry point**.
3. Removes.

⚠ Watch the P12c fence (outbox / watermark / cascade coupling).
