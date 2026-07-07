# The graph index (`index_v4/`)

Full design: `docs/specs/wildcard-materialization-spec.md` (cited as `spec §N` in
`index_v4/*`). This is the operational summary.

## Closure core (`core.py`)

`ReachabilityIndex` materialises the full transitive closure of a DAG as ref-counted
edge rows. Per `EdgeV4` row:

* `direct_edge_count` — how many direct (raw/bridge/derived) edges exist for the pair;
* `indirect_edge_count` — the **path count** (number of distinct paths). Invariant I1:
  `indirect >= direct` and `indirect > 0`; zero-reachability rows are deleted, never
  persisted.

Adding a direct edge `u -> v` multiplies path counts: every ancestor of `u` gains
`(paths to u) x (paths from v)` paths to every descendant of `v`. Removal subtracts the
same products — that is why removal is exact with no re-derivation. Consequences:

* **Cycles are impossible to tolerate** (infinite path multiplicity): every add runs a
  reverse-reachability pre-check and raises `ValueError('...cycle...')`.
* Reachability flips (0→positive = ADDED, →0 = REMOVED) are emitted as
  **outbox rows** (`DeltaOutboxV1`, `_emit`) inside the writing transaction. No write
  path returns delta lists; drain with `index_v4.outbox.drain_deltas(session, store,
  watermark)`. Outbox rows denormalize both endpoints (type/name/predicate) because
  implicit-node GC can delete a node row in the same transaction.

**Node identity** is `(store_id, predicate, type, name, wildcard)`; `wildcard ∈
{'', 'any', 'all'}` and `name == '*'` iff `wildcard != ''`. Implicit nodes are GC'd
when their `reference_count` (direct-edge endpoints) hits zero.

**Concurrency**: `_lock_store` takes `FOR UPDATE` on the store row — serializes the
whole logical write (cycle check + ref-count updates + cascade) per store on
PostgreSQL/MySQL; renders to nothing on SQLite (which serializes writers itself).
One `Session` per thread, never shared.

## Wildcards (`wildcard.py`)

`WildcardIndex` wraps the core with the **split wildcard node** model:

* `w_any(S)` = "some instance of shape S": concretes bridge INTO it
  (`concrete -> w_any`), grants depart out of it. Wildcard *subject* tuples grant from
  `w_any`.
* `w_all(S)` = "all instances of S": grants arrive into it, bridges depart OUT of it
  (`w_all -> concrete`). Wildcard *object* tuples grant into `w_all`.
* No `w_any -> w_all` edge ever — that would leak "being an instance" into "receiving
  what is distributed to instances".

Bridges are created idempotently per concrete of a *declared bridged shape*
(`SchemaInfo.bridged_in_shapes` = userset star shapes like `group:*#member`;
`bridged_out_shapes` = declared object-wildcard shapes) and GC'd when a concrete's
only remaining edges are its bridges. Bare `[user:*]` costs zero bridges.

**check()** on an untainted relation = up to 4 probe keys — `(s,o)`,
`(w_any(shape(s)), o)`, `(s, w_all(o.type,R))`, `(w_any, w_all)` — gated by
`SchemaInfo`, missing nodes drop their keys (ghosts keep star coverage), and all keys
go into **one SQL statement** (`tuple_(...).in_(keys) LIMIT 1`). Derived relations
take a different path (see `derived-predicates.md`). Reads never intern nodes (I11).

**Self-referential wildcard tuples** (`group:*#member member group:g`) are rejected by
the cycle pre-check — a counting-invariant necessity, re-raised with an explanatory
message; the set engine rejects identically. Conversely object-star self-containment
(`folder:X contains folder:*` ⇒ X contains itself) is representable and TRUE with no
cycle (subject-role and object-role are different nodes). Don't "fix" either.

## What lives where on a write

1. Raw tuple → `RuleSet.apply` (admission Filters, first-match; rewrite Rules,
   worklist fan-out; boolean relations: RewriteFilter fan-in onto leaf families).
2. Each derived triple → `WildcardIndex.add_tuple/remove_tuple` (validation, bridges,
   exclusivity assert, core edge op, outbox emission).
3. Boolean schemas only: `DeltaProcessor.run_cascade(watermark)` — same transaction.
4. `session.commit()` — paranoia mode (if installed) checks invariants pre- and
   post-commit.
