---
type: Decision
id: DEC-5
title: The connected store (round 3 — multi-instance / HA)
actor: unrecorded
decided: 2026-07-23
session: 2026-11-03a
decision_status: BUILT
attribution: unrecorded, the log names no one; the date of the commit that wrote the heading (git blame), 2026-07-23
imported_from: docs/evidence/decision-log-normalised-2026-11-03.md
body_sha: sha256:9550ec283ed1162a1e6e8552ede5858d1355ef55d8da151c0178cf61e93257a0
---

* **Multi-instance set engines via log tailing, not gossip.** Several
  `TupleSource`/`ConnectedStore` instances (one `Session` each) share a store; each
  set engine is instance-local in-memory, resynced by tailing `TupleLog`
  (`SetEngine.apply_logged` per committed row — the O(delta) analog of `rebuild()`,
  which is O(store)). The DB log is the *only* inter-instance channel — instance
  gossip was rejected as a second, redundant consistency surface. Consequence:
  every instance's state is the fold of an exact log *prefix* (prefix consistency —
  instances differ only in recency, never sideways); un-tokened replica reads are
  bounded-stale by tail cadence; read-your-writes/causal reads reuse the existing
  log-id token on `at_least` (now honored on `TupleSource.check`, not only
  `ConnectedStore.check`).
* **Log ids REMAIN the token** — no snowflake/ULID/lamport clock. Store-local
  autoincrement log ids already totally-order a store's history and are the cursor
  domain; a global clock buys nothing until *cross-store* tokens are in scope (they
  are not — X6). The round-1 brainstorm's timestamp menu is closed.
* **Source-lock write discipline** (`_lock_source`: `FOR UPDATE` on the `SchemaRecord`
  row) over lock-free admission: a write is a check-then-act against instance-local
  memory (duplicate / remove-existence / cycle parity), sound only if no other
  instance can commit between the catch-up and this write's commit. Taking the lock
  → `catch_up_evaluator` → validate → append in one transaction serializes writers
  at store granularity. **This also closes a latent pre-existing hazard**: the log
  append used to flush its autoincrement id *before* any lock, so concurrent writers
  on PostgreSQL could commit log ids out of order and a tailer (or `advance_index`'s
  cursor) could permanently skip a row. Ids now commit in id order per store.
  Lock-ordering invariant: source lock (`SchemaRecord`) before graph store lock
  (`Store`) — one global order, deadlock-free.
* **Correctness over per-write cost** in the degenerate single-writer case: the lock
  never contends and catch-up is one empty indexed SELECT, so the cost is one
  `FOR UPDATE` SELECT (no-op-rendered on SQLite) + one empty log SELECT per write —
  accepted deliberately rather than branching the write path on a deployment
  assumption.
* **`at_least` is check-only — lookup/reverse-lookup/expand deliberately excluded**
  (not "can't", "didn't": the token mechanics are the same five lines). Three costs
  `check` doesn't have, plus a structural point:

  > **REVISED 2026-07-27 (`ZT-P1-8b`).** "Excluded" was the wrong shape of answer.
  > Taking no token at all meant a revoked principal stayed ENUMERABLE with no API to
  > demand otherwise — and list-objects / list-users is precisely what a revocation UI
  > reads, so the surface that most needs freshness was the one that could not ask for
  > it. `lookup` / `lookup_reverse` now ACCEPT `at_least`, run the same first two rungs
  > as `check` (in-memory cursor, then a cursor refresh), and raise `LookupNotFresh`
  > when the index still lags. What stays excluded is the third rung, the set-engine
  > FALLBACK, and reason 1 below is why — with one addition the original entry missed:
  > in the stale-index case the graph `Node` rows for the un-applied tuples do not
  > exist yet, so even a key-translation bridge is impossible in principle, not merely
  > expensive. `excluded_node_ids` (the derived `neg` channel) has no set-engine
  > counterpart either. The prerequisite in reason 1 is unchanged and still unbuilt.
  > *(2026-10-13, TK139: that `neg` clause was wrong -- the set engine's `expand.neg`
  > is the counterpart, and `SetEngine.lookup_reverse` now fills `excluded_node_ids`
  > from it; it is still in the set engine's own id domain, so reason 1 stands.)*
  > Untokened calls are byte-identical to before. **Refusing a demand you cannot meet
  > is not the same as not offering one.**
  1. *Result domain.* `check` returns a bool, so the freshness fallback (graph when
     fresh, set engine when lagging) is invisible. The lookup surfaces return ids —
     graph node ids (DB rows) vs set-engine interner ids (instance-local, recycled)
     — so a fallback silently switches the id domain of the same call depending on
     index lag. Prerequisite: redefine the public lookup contract in the portable
     `(type, name, predicate)` key + marker domain for BOTH backends
     (`SetEngine.result_keys` is that form; the graph side needs the twin), a
     breaking/versioned API change in its own right.
  2. *Perf cliff.* Graph lookup is probes over the materialized closure — the point
     of that backend; the set engine's is a check-verified reverse walk (correct,
     oracle-pinned, expensive). A tokened `check` fallback costs one pointwise
     evaluation; a tokened lookup fallback silently turns a hot enumeration into a
     full reverse walk whenever the worker lags. That degradation should be a
     visible, chosen behavior, not an implicit one.
  3. *Test surface.* `tests/test_lookup_oracle.py` is the strictest gate in the
     repo (the X1–X4 history); a lagging-index fallback leg doubles its matrix
     (fresh vs lagging × backends × token boundaries) — a deliberate follow-up
     arc, not a rider.
  Structurally: a lagging reader cannot make the index fresh itself
  (`advance_index` is the writer/worker's job — store lock, closure mutation), so
  the set-engine fallback is the only non-blocking option, which is exactly where
  costs 1–2 bite. **Shape of the future work**: unify the lookup result contract on
  keys/markers → add the same `at_least` plumbing as `check` → extend the lookup
  oracle gate with a lagging-index leg (mostly test-writing).
  ⚠ **None of that arc is built, and the id that filed it is CLOSED** — `ZT-P1-8b`
  closed 2026-07-29 having landed the accept-and-raise half only. So the ledger
  answers *"is `at_least` done?"* wrongly: the closed record covers less than its
  filed scope, and this bullet's arrow-chain is the part still outstanding. Read the
  chain above, not the id's status.
* **Out of scope** (this round): snapshot / "at exactly" reads (only `at_least`
  lower-bounding); cross-store tokens (X6 — store-local); instance gossip (the DB
  log is the channel); schema-version skew (schemas are write-once — a new schema
  is a new store). **Sharing tuples or state ACROSS stores** is out too, and stays
  out until a design says what it means for three per-store things: `TupleLog`
  (`store_id`-scoped, and every read filters on it), the watermark/cursor domain
  (`source.py::log_watermark` is per store; `IndexCursor` is unique per index
  store), and `_lock_store`'s store-granularity serialization. ⚠ Log **ids are
  globally monotonic across stores** even though scoping is per-store, which is why
  `lag()` counts rows instead of subtracting ids — a sharing design that assumes
  per-store id density breaks on exactly that.
* **One write path per store id (TK140, 2026-10-13d).** The `SchemaRecord` row is the
  governance marker: a `SetEngine` on an id that has one is log-governed (its direct
  writes raise `UnloggedWriteRefused`; reads stay legal), probed at construction and once
  per transaction before a standalone write. It was not made a construction-time refusal,
  because reads through a second engine are legitimate. And a `ConnectedStore` will not be
  born (create its cursor) over `RelationTuple` rows the log does not account for
  (`UnloggedTuplesPresent`); the adoption path is `save_schema` + `build_index`. The
  concurrent case (a standalone write racing an uncommitted bootstrap under READ
  COMMITTED) is a documented residual. A standalone engine has no lock surface, and
  giving it one was not worth it for two write paths misused on one id.
  `docs/tk140-one-write-path-per-store-2026-10-13.md`.
