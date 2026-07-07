# Spec: the connected store — source-of-truth tuples + materialized graph index

Round 2 of the build series (after `graph-boolean-ivm-spec.md`). Design conversation
conclusions frozen here; implementation record continues in `../spec-deviations.md`.

## §1 The split (Zanzibar / Leopard)

* The **tuple store** (`TupleV1` + the new tuple event log) is the **source of
  truth** — the Zanzibar half. Writes are validated and landed here first; the set
  engine is its online evaluator (always fresh).
* The **graph index** (`index_v4`) is a **materialized view** — the Leopard half:
  maximal materialization (full closure + boolean derived state) maintained *from*
  the tuple store. Tuples never live "in" the index; nothing is ever reconstructed
  from it.
* **`ConnectedStore`** composes the two. The synchronous coupling built this round is
  a **temporary schedule, not temporary machinery**: sync mode is the async apply
  step inlined into the write transaction (cursor pinned at the log head). The
  cutover to async changes *when* the apply step runs, never *what* it does.

## §2 Decisions (settled in design review; do not relitigate)

1. **Schema is static, everywhere.** One schema per store, stored in the DB
   (`SchemaV4`), write-once — a second schema write for the same store raises, for
   the set engine as much as the graph index. No versioning, no migration: a new
   schema means a new store/index. Rationale: schema changes can invalidate tuples
   anyway; a clean rebuild is more correct than a clever migration.
2. **Schema *source* is persisted; compiled artifacts are cache.** RuleSet/plans are
   a deterministic function of the source and are recompiled on open (the exact
   analogue of `SetEngine.rebuild()`). Persisting compiled Filter/Rule rows was
   rejected: the executable plans can't be persisted anyway (closures), and stored
   compiled state is a drift surface (same reasoning as the rejected `family`
   column, boolean spec decision 10).
3. **The tuple event log is permanent** (append-only, never cleared): it is the
   audit log, the volume is human-scale permission data, and permanence makes any
   index state derivable from `(log, schema)` alone. Log compaction is a documented
   hook, not a feature. Bootstrap-from-snapshot (§4) keeps new-index builds
   independent of log length.
4. **Validity at admission.** The source-of-truth write path enforces full validity
   parity up front — including graph-cycle parity via the set engine's flow graph —
   so the log contains only index-appliable ops. A rejection during index apply is
   therefore a **hard failure** (corruption signal), never an op rejection. This is
   what keeps the log replayable without a dead-letter mechanism.
5. **Freshness tokens (zookie-lite)** are log ids. A write returns the id of its log
   row; a read with `at_least=token` is served from the index iff the index cursor
   `>= token`, else answered by the set engine (fresh by construction). This is
   Leopard's `timestamp <= query_timestamp` merge simplified to a fallback.
6. **Exactly-once apply** comes from transactionality, not bookkeeping: log rows are
   applied and the cursor advanced in one transaction per batch. A failed batch
   moves nothing; retries re-read the same rows.
7. **No service layer this round.** Algorithms + a working setup only; HTTP wrapping
   is deliberately out of scope (the S6 worker being a plain callable is what makes
   that trivial later).

## §3 Data model (adapt names/layouts to repo conventions)

```python
class SchemaV4(SQLModel, table=True):
    store_id: str            # PK; one row per store, write-once
    schema_text: str         # the DSL source (or DSL rendered from OpenFGA JSON)
    object_wildcard_shapes: str   # JSON list of [type, relation]
    created_at: float

class TupleLogV1(SQLModel, table=True):
    id: int                  # PK autoincrement — the token and the cursor domain
    store_id: str
    op: str                  # 'ADD' | 'REMOVE'
    # the six tuple fields (subject predicate/type/name, relation, object type/name)
    created_at: float
    # INDEX(store_id, id)

class IndexCursorV1(SQLModel, table=True):
    index_store_id: str      # the graph index's store
    source_store_id: str     # the tuple store it materializes
    applied_log_id: int      # the index reflects the source through this log row
    # UNIQUE(index_store_id); INDEX(source_store_id)
```

Notes: `TupleLogV1` rows are written in the same transaction as the `TupleV1`
mutation. `TupleV1` remains the *current-state* table (rows deleted on remove); the
log is the history. The pair (snapshot table + append-only log) is deliberate — cheap
current-state reads, complete replayability.

## §4 Mechanisms

* **Write path** (`ConnectedStore.write`): validate (charset, restrictions,
  wildcard shapes, cycle parity) → mutate `TupleV1` + append `TupleLogV1` → [sync
  schedule only: apply to index + advance cursor] → commit. One transaction;
  rejection rolls back everything (I12 across both halves). Returns the log id.
* **Apply step** (`advance_index`): read log rows `> applied_log_id` for the source
  store (batched), route each through `RuleSet.apply` into the graph index, run the
  delta-processor cascade, advance the cursor; commit per batch. The ONLY moving
  part — sync mode inlines it, async mode loops it.
* **Bootstrap** (`build_index`): for an existing tuple store — capture the current
  log watermark, bulk-load the `TupleV1` snapshot through the ruleset,
  `DeltaProcessor.backfill()`, set cursor to the watermark. The offline builder from
  the Leopard paper; the worker then streams the tail. Distinct from the async seam.
* **Reads**: `check`/`lookup`/`lookup_reverse` from the graph index; with
  `at_least=token`, fall back to the set engine when the cursor lags the token.

## §5 Phases (each lands green; commit per phase; suite is the gate)

* **S0** Recon & spec freeze. *Accept: baseline green; this file committed.*
* **S1** `SchemaV4` + write-once + both backends open from `(session, store_id)`;
  explicit-schema constructors must match a stored schema (mismatch = loud error).
  *Accept: self-describing stores; immutability & mismatch tests.*
* **S2** `TupleLogV1` + the source-of-truth write path (full admission validity,
  tokens returned). *Accept: log ≡ applied writes; rejected writes leave no row.*
* **S3** `ConnectedStore`, sync schedule (documented temporary-schedule note).
  *Accept: parity vs oracle + set engine over fixture grids; atomic rollback across
  both halves.*
* **S4** `build_index` bootstrap. *Accept: built ≡ live-maintained (row multisets +
  residues, reads).*
* **S5** OpenFGA JSON model ingestion → same `SchemaAST`; unsupported features
  rejected loudly. *Accept: JSON twins of DSL fixtures parse to identical ASTs.*
* **S6** Async glue working end-to-end: `advance_index` as a test-driven callable,
  freshness-gated reads with set-engine fallback, lag → catch-up → convergence.
  *Accept: async-built state ≡ sync-built state after catch-up; stale reads gated.*
* **S7** Concurrency & stale-read hardening (file-backed SQLite, concurrent writers,
  reader-session-as-replica). *Accept: concurrency suite green.*
* **S8** Docs + matrix: `ConnectedStore` joins the validation matrix;
  `docs/architecture/system.md`. *Accept: suite green; docs cross-linked.*

## §6 Non-goals (hooks only)

HTTP/FastAPI service layer; a daemonized worker (the callable is the seam); log
compaction; cross-store tuple migration; schema versioning/migration of any kind;
Materialize-style per-permission change streaming (the outbox drain remains the
external seam); read-replica deployment (S7 simulates with sessions).
