# The connected store: the system view

Spec: `../specs/connected-store-spec.md`; implementation record in
`../spec-deviations.md` (connected-store round entries). This is how the pieces
compose into one Zanzibar-shaped system.

## The split (Zanzibar / Leopard)

```
            writes                                   reads
              │                                        │
              v                                        v
   ┌─────────────────────┐   log rows > cursor  ┌──────────────────┐
   │  TUPLE STORE        │ ───────────────────> │  GRAPH INDEX     │
   │  (source of truth)  │    advance_index     │  (materialized   │
   │  TupleV1 (snapshot) │    [the apply step]  │   view: closure  │
   │  TupleLogV1 (log)   │                      │   + booleans)    │
   │  SetEngine (online  │ <─── freshness ───── │  IndexCursorV1   │
   │   evaluator)        │      fallback        └──────────────────┘
   └─────────────────────┘
```

* **Tuple store = source of truth** (the Zanzibar half). `TupleV1` is the current
  snapshot; `TupleLogV1` is the permanent, append-only history (audit log + replay
  source + token domain — never cleared; compaction is a hook). The set engine is
  its always-fresh online evaluator.
* **Graph index = materialized view** (the Leopard half). Maximal materialization;
  nothing is ever reconstructed from it; a schema change means building a new one.
* **`IndexCursorV1`** is the entire index state bookkeeping: "index X reflects
  source Y through log row N."

## One apply step, two schedules

`advance_index(session, cursor, widx, ruleset, proc, batch=…)` — read log rows past
the cursor (under the index store's write lock; the cursor is re-read fresh), route
them through the rewrite fan-out, run the delta-processor cascade, advance the
cursor. Caller commits: applied rows + cursor land atomically ⇒ **exactly-once**;
a failed batch moves nothing and a retry re-reads the same rows.

* **Sync schedule** (`ConnectedStore(sync=True)`, default): the apply step is
  inlined into every write transaction — cursor rides the log head, reads are
  always fresh. *This coupling is a temporary schedule, not temporary machinery.*
* **Async schedule** (`sync=False`): writes land in the source of truth only;
  `catch_up(batch=…)` is the worker body (a daemon would just call it on a timer).

## Validity at admission (what keeps the log replayable)

The write path validates everything up front — charset, type restrictions, wildcard
gating, and the graph's cycle rejection reproduced by the set engine's flow graph —
so the log contains only index-appliable ops. An apply-time rejection is therefore a
**hard failure** (corruption signal), never an op rejection, and no dead-letter
mechanism is needed. Duplicate adds are idempotent set-semantics no-ops (raw tuples
are a set; the graph core stays ref-counted internally for rewritten fan-in).

## Freshness (zookie-lite)

A write returns its log id. `check(..., at_least=token)` is served by the index iff
`cursor >= token`, else answered by the set engine — Leopard's
`timestamp <= query_timestamp` merge simplified to a fallback. Sync mode satisfies
every token trivially; async mode is where it earns its keep.

Tokens are **store-local**: the domain is the store's own `TupleLogV1` id sequence
(a per-database autoincrement, not a global clock). A token minted against one store
means nothing to another; cross-store consistency needs an external ordering.

The fallback is **watermark-aware**: the set engine's in-memory state is only as
fresh as its last rebuild plus whatever it has since tailed
(`TupleSource.evaluator_watermark` tracks exactly that), so a tokened read whose
token exceeds the watermark catches up on demand — tailing the committed log delta
into the evaluator (`catch_up_evaluator` → `SetEngine.apply_logged` per row,
**O(delta)** not O(store)) — the honest per-read cost of demanding freshness from a
lagging index. This is honored on `TupleSource.check(at_least=…)` too, not only on
`ConnectedStore.check`. If the token is *still* not visible, the session's read
snapshot predates the write: the read raises `StaleRead` (call `refresh()` and
retry) rather than silently serving stale under an explicit freshness demand.

**Multi-instance (HA).** Several `TupleSource`/`ConnectedStore` instances (one
`Session` each) may share a store; each set engine is instance-local in-memory,
synced from `TupleLogV1`. Every instance's state is the fold of an exact *prefix* of
the store's log — **prefix consistency**: instances differ only in recency, never
sideways. Un-tokened replica reads are **bounded-stale** (only by the reader's tail
cadence via `refresh()`/`catch_up_evaluator`); read-your-writes / causal reads use
the existing log-id tokens (`at_least`). Multi-writer admission is correct because
each write runs a per-store **critical section**: `_lock_source` (a `FOR UPDATE`
lock on the store's `SchemaV4` row) → `catch_up_evaluator` → validate → append,
inside one transaction. Under the lock no new commit can appear, so duplicate
detection / remove-existence / cycle parity validate against current committed
state, and the log append lands inside the section — so **log ids commit in id
order per store** and `id > watermark` tailing (this tailer and `advance_index`'s
cursor alike) can never skip a row. **Lock ordering**: the source lock (`SchemaV4`
row) is always taken *before* the graph store lock (`StoreV4` row, taken inside
`advance_index`) — one global order, deadlock-free. A single-writer deployment
degrades to one no-op-rendered `FOR UPDATE` (SQLite) plus one empty indexed SELECT
per write: correctness-over-perf, deliberately.

## Bootstrap and schema changes

`build_index(session, source, index_id=None)` — the offline builder: capture the log
watermark, bulk-load the `TupleV1` snapshot through the rewrite fan-out,
`DeltaProcessor.backfill()`, set the cursor to the watermark. The worker then
streams the tail. Schemas are **static and write-once** (`SchemaV4`; compiled
artifacts are cache, recompiled on open): a new schema = a new store/index built
from the tuples, not a migration.

## Replicas (simulated; the real thing is a follower DB)

A reader session polling a store another session writes to sees consistent
committed snapshots; `ConnectedStore.refresh()` is the poll API (fresh transaction +
rebuilt evaluator + cleared w-id cache). Under async lag: un-tokened reads are
stale-but-consistent from the index, tokened reads fall back fresh. Local
simulation uses SQLite WAL + real BEGIN semantics (see the S7 deviations entry for
the pysqlite caveats).

## OpenFGA ingestion

`parse_openfga_json` (OpenFGA 1.1 authorization-model JSON) targets the same
`SchemaAST` as the DSL; `openfga_json_to_dsl` renders the persistable schema source.
One AST, two front-ends; conditions and unknown operators are rejected loudly.

## What the matrix pins

`ConnectedBackend` sits in the validation matrix alongside graph · oracle · set
engine (both `SetOps`) on the union+wildcard AND boolean fixtures: unanimous
accept/reject and identical full-grid checks after every op — the composition is
validated, not just the parts.
