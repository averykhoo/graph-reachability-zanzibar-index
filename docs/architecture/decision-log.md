# Decision log

Load-bearing decisions with their rejected alternatives, compressed from the three
specs (`docs/specs/`). Dated *implementation* divergences live in
`docs/spec-deviations.md`; this file is the "why is it like this at all" record.
Do not re-walk these without new evidence — the alternatives were considered.

## Graph index

* **Path-counted closure rows** over interval/2-hop/PLL labelings and per-object
  bitmaps: labelings have non-constant queries and degrade under deletion; bitmap
  bits can't be ref-counted for exact removal. Under OMv-style lower bounds nothing
  gets both fast updates and fast queries — the query-optimal corner is chosen
  deliberately; multiplicative path counting is what makes removal exact.
* **Cycle rejection is a counting necessity**, not a policy: a cycle means infinite
  path multiplicity. Hence also: self-referential wildcard tuples rejected (the
  bridge+grant pair closes a loop), while object-star self-containment is fine
  (subject-role and object-role are different nodes; entity nodes have in-degree 0).
* **Split wildcard nodes** (`w_any`/`w_all`, never bridged to each other) over a
  single `*` node: prevents the instance leak (being an instance ≠ receiving what is
  distributed to instances). Interior wildcard hops are materialised as bridges so
  check stays ≤4 probes; only query-endpoint hops stay virtual.
* **Store-granularity writer lock** (`_lock_store`) over per-edge locking: the
  affected closure region is discovered while walking, so piecemeal locking in graph
  order invites deadlocks; one logical write already touches many rows.

## Set engine

* **Raw tuples (`TupleV1`) are the ground truth**; all set state is in-memory,
  rebuilt by replay on open. Bitmap snapshot persistence rejected (opaque, duplicates
  state).
* **Reference-counted interner with recycled int32 ids**: `(type, name, predicate)`
  is the stable surrogate; memory tracks live entities, not lifetime. Never
  `isinstance`-check the underlying set type — everything goes through the `SetOps`
  seam (roaring/pyset must be indistinguishable; the matrix runs both).
* **`MemberSet (pos, stars, neg)`** carries the pinned star×boolean table:
  stars fold ∪=`|`, ∩=`&`, ∖=`-`; `pos` wins over `neg`; concrete-only exclusions
  never defeat star queries.

## Boolean relations in the graph index (the IVM build)

* **Materialisation as ordinary edges in the SAME closure** over check-time
  expression evaluation: check-time eval can't support anything *downstream* of a
  boolean (TTU over a boolean viewer, userset restrictions, nested booleans).
  Materialised derived edges re-enter the closure and emit their own deltas, which
  drive the next stratum. Strata are logical, never physical — one store, one
  transaction.
* **Taint propagates** (a pure union over a boolean relation is derived): star-covered
  members have no edges, so compiling it normally would silently drop them.
* **Symbolic state is a per-object residue row** (`stars`, `neg`) — not derived
  w-edges (splits one relation's symbolic state across two writers + bridge-GC
  interactions), not extensional star expansion (unbounded, ghost-wrong, and
  cycle-creating for self-including universals).
* **Deltas are invalidation signals, never state transfers**; reconciliation is
  recompute-from-committed-state, idempotent. The §5.4 rule is load-bearing: a
  symbolic delta must reconcile the concrete edge-holders on that object, not just
  the residue (blocked:`[user:*]` arriving produces no concrete delta for bob, yet
  must revoke his edge).
* **Canonical representation**: star-covered members hold no edges (residue answers);
  uncovered members hold an edge iff true. Required for permutation invariance and
  the "star-only members: zero edges" space rule.
* **Synchronous v1, in-transaction outbox cascade**; no SAVEPOINTs (a failed
  reconcile must abort the whole write; SAVEPOINT-per-delta is the future async
  worker's tool, noted with the pysqlite transaction-boundary caveat).
* **Stratification is mandatory**; recursion through a boolean relation is a compile
  error. Termination of the cascade follows from idempotent reconciliation; the
  quiescence assert enforces it.
* **Namespacing lives in the predicate name** (`<relation>.<index>`, `.` reserved in
  declarations); classification is the compiled namespace map keyed
  `(object_type, predicate)` — no `family` column (a drift surface duplicating
  name-derivable information).
* **TTU parents = stored tupleset tuples** (oracle-pinned Zanzibar semantics).
  Storage leaves are split from rule-routed leaves so "stored tuples of a derived
  relation" is a well-defined edge set. This is also why decision 15's rejection of
  derived-tupleset TTUs could be lifted (the frozen acceptance event required it):
  parents are data-bounded stored tuples, not an object-star-shaped computed set.
* **Raw-tuple set semantics at the API boundary** (duplicate add = no-op) while the
  core stays ref-counted: two *different* raw tuples may rewrite to the same derived
  edge, so counts are load-bearing internally — but Zanzibar raw tuples are a set.
* **Scope hooks, not features**: object wildcards on derived relations and wildcard
  usersets over derived relations both need symbolic composition through residues
  (a symmetric subject-keyed residue) — loud compile errors until someone builds it.

## The connected store (round 2)

* **Source-of-truth / materialized-view split** (Zanzibar/Leopard): tuples live in
  `TupleV1` + a permanent log; the graph index is downstream and owns nothing.
  "Reconstruct tuples from the index" was rejected — likely possible in principle
  (topo-order peeling with path-count subtraction) but it's the whole forward engine
  reimplemented in reverse, kept bug-for-bug in sync forever, to recover data one
  table keeps losslessly.
* **Schemas are static, write-once, stored as SOURCE** (`SchemaV4`); compiled
  artifacts are cache (closures can't be persisted; stored compiled state is a
  drift surface — the `family`-column argument again). A new schema = a new
  store/index built from the tuples; no versioning, no migration.
* **The tuple log is permanent** (audit + replay + token domain; human-scale
  volume); bootstrap-from-snapshot keeps builds independent of log length, so
  compaction stays a hook.
* **One apply step, two schedules**: sync = the async worker inlined into the write
  transaction. The coupling is a temporary *schedule*, not temporary machinery.
* **Validity at admission** keeps the log replayable: the write path enforces full
  parity (incl. graph-cycle rejection via the set engine's flow graph), so an
  apply-time rejection is a corruption signal — no dead-letter mechanism.
* **Exactly-once by transactionality**: applied rows + cursor advance commit
  together; the applier locks the index store before reading the cursor
  (lost-update prevention).
* **Freshness tokens are log ids** (zookie-lite): index serves iff cursor ≥ token,
  else the set engine answers fresh — Leopard's timestamp merge simplified to a
  fallback.

## Non-goals (documented hooks only)

Async outbox workers; exposing derived-relation deltas to external consumers;
cross-query caching / zookies; automatic outbox pruning; residue GC beyond empty-row
deletion; lenient ∀⇒∃; a `family` metadata column; Rete-style general incremental
matching; 64-bit id space; query-time node interning.
