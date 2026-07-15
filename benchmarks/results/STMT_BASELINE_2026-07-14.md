# Statements-per-operation baseline — 2026-07-14 (P12-M, wave 0)

Before-numbers for P12a/P12b/N5/N6: **SQL statements per operation** on a real
`connectedstore.ConnectedStore` (sync schedule), the composition path the
`build_set`/`build_graph` bench harness bypasses entirely. Counted via an
SQLAlchemy `before_cursor_execute` listener on the engine; wall-time is a weak
secondary signal (in-memory SQLite: a round-trip is ~µs, and `with_for_update()`
renders to nothing on SQLite).

**Reproduce:**

```bash
PY="C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe"
"$PY" -m benchmarks.stmt_bench
```

Deterministic (modular-arithmetic data, no RNG). Two schemas, each measured over a
200-tuple warm-up store then: 50 distinct `add_tuple`, 20 `remove_tuple` (of the
just-added), 50 `check`, 20 `lookup`, 20 `lookup_reverse`. Total wall time ~42 s.

**Mode:** `paranoia=off`, and **not reachable through `ConnectedStore`** — the
store opens the graph index via `schema_io.open_graph_index` →
`ReachabilityIndex(session, store_id)` directly, never calling `install_paranoia`,
and its constructor exposes no paranoia flag. So these numbers are the
production-realistic (checker-off) path; there is no knob to turn the checker on
via `ConnectedStore`.

**`FOR UPDATE` caveat:** on SQLite `with_for_update()` compiles to *nothing*, so the
literal-text `FOR UPDATE` counter is **0.0 everywhere**. The honest proxy for the
`_lock_store` lock round-trip is the count of `SELECT … FROM store_v4` statements:
`_lock_store` is the *only* code path that SELECTs `store_v4` on the write path
(grep-verified — no `.store` relationship lazy-loads in `core.py`/`wildcard.py`/
`processor.py`), so every `store_v4` SELECT is one lock re-take.

---

## (a) Pure-union schema (no boolean operators — `proc is None`, no cascade)

```
type user
type group
  relations
    define member: [user]
type doc
  relations
    define owner: [user]
    define editor: [user, group#member]
    define viewer: [user, group#member] or editor or owner
```

- construction statements: 9
- rewrite fan-out K over the 50 measured adds: **mean 1.66, min 1, max 2**
- read sanity: check hits 33/50, lookup non-empty, reverse non-empty

| op | stmts/op (mean) | min | max | kw/op (S/I/U/D) | FOR UPDATE/op | ops/s | store_v4 SELECT/op |
|---|--:|--:|--:|---|--:|--:|--:|
| add_tuple      | 50.6 | 22 | 90 | S25.2 I20.4 U5.0        | 0.0 | 27  | 4.3 |
| remove_tuple   | 43.0 | 23 | 69 | S26.1 I9.2 U4.0 D3.8    | 0.0 | 27  | 4.3 |
| check          |  2.7 |  2 |  3 | S2.7                   | 0.0 | 326 | –   |
| lookup         | 74.5 | 74 | 75 | S74.5                  | 0.0 | 17  | –   |
| lookup_reverse | 14.3 |  1 | 15 | S14.3                  | 0.0 | 78  | –   |

Per-`add_tuple` SELECT attribution (mean/op):

| table | SELECT/op | inventory item |
|---|--:|---|
| store_v4        |  4.32 | ②+③ `_lock_store` re-takes (predicted 1+K) |
| tuple_log_v1    |  1.00 | ⑤ `log_rows` (predicted 1) |
| delta_outbox_v1 |  0.00 | ⑥ `outbox_watermark` (boolean only — correctly absent) |
| index_cursor_v1 |  1.00 | ④ cursor refresh (predicted 1) |
| node_v4         | 11.62 | index node resolution |
| edge_v4         |  7.28 | index closure work |
| residue_v1      |  0.00 | derived residue (boolean only — correctly absent) |

**store_v4 SELECT/write = 4.32 vs predicted 1+K = 2.66 (K mean 1.66).**

## (b) Boolean schema (`and` / `but not` — derived `can_view`, cascade + outbox)

```
type user
type group
  relations
    define member: [user]
type doc
  relations
    define blocked: [user]
    define editor: [user, group#member]
    define viewer: [user, group#member] or editor
    define can_view: viewer but not blocked
```

- construction statements: 9
- rewrite fan-out K over the 50 measured adds: **mean 2.34, min 2, max 3**
- read sanity: check hits 33/50, lookup non-empty, reverse non-empty

| op | stmts/op (mean) | min | max | kw/op (S/I/U/D) | FOR UPDATE/op | ops/s | store_v4 SELECT/op |
|---|--:|--:|--:|---|--:|--:|--:|
| add_tuple      | 221.2 | 41 | 535 | S164.9 I40.8 U15.2 D0.3  | 0.0 | 5   | 14.5 |
| remove_tuple   | 187.2 | 51 | 417 | S145.2 I19.1 U12.4 D10.5 | 0.0 | 5   | 13.4 |
| check          |   3.1 |  3 |   4 | S3.1                    | 0.0 | 251 | –    |
| lookup         | 134.8 | 133| 137 | S134.8                  | 0.0 | 8   | –    |
| lookup_reverse |  14.4 |  2 |  16 | S14.4                   | 0.0 | 74  | –    |

Per-`add_tuple` SELECT attribution (mean/op):

| table | SELECT/op | inventory item |
|---|--:|---|
| store_v4        |  14.52 | ②+③ `_lock_store` re-takes (predicted 1+K) |
| tuple_log_v1    |   1.00 | ⑤ `log_rows` (predicted 1) |
| delta_outbox_v1 |   3.00 | ⑥ `outbox_watermark` + cascade drain (predicted 1) |
| index_cursor_v1 |   1.00 | ④ cursor refresh (predicted 1) |
| node_v4         | 103.42 | index node resolution + cascade |
| edge_v4         |  37.24 | index closure work + cascade |
| residue_v1      |   4.76 | derived residue reconcile |

**store_v4 SELECT/write = 14.52 vs predicted 1+K = 3.34 (K mean 2.34).**

---

## Interpretation

### The `SELECT … FOR UPDATE` (`_lock_store`) count per sync write

The P12a prediction was **1 + K**, K = number of routed `widx.add_tuple` calls.
**The measurement shows the prediction UNDERCOUNTS** — materially:

| schema | K (mean) | predicted 1+K | measured store_v4 SELECT/write | ratio |
|---|--:|--:|--:|--:|
| pure-union | 1.66 |  2.66 |  4.32 | 1.6× |
| boolean    | 2.34 |  3.34 | 14.52 | 4.3× |

Why: the inventory modeled "one `_lock_store` per routed `widx.add_tuple`", but a
*single* `widx.add_tuple` locks **more than once** — the façade locks
(`wildcard.py:252`) and then each `ReachabilityIndex.add_edge` it drives locks again
(`core.py:503/529`), plus bridge-node and remove-node fixups each re-lock
(`core.py:559/570/581`). So the true multiplier is *edge/node mutations*, not
routed calls. On the boolean schema the delta-processor **cascade** (`run_cascade`)
performs its own derived-family façade writes, each with its own `_lock_store` — so
a boolean write's lock count (14.5) is dominated by cascade lock re-takes, far above
the fan-out K. **This strengthens the P12a case**: a transaction-scoped `_lock_store`
memo collapses *all* of these (4.3→1 union, 14.5→1 boolean) to a single lock per
transaction, a bigger win than the 1+K framing implied — and the largest single
constant on the boolean write path in absolute terms.

### ⑤ `log_rows` and ⑥ `outbox_watermark` visibility

Both are visible exactly as the inventory predicted:

- **⑤ `log_rows` (tuple_log_v1 SELECT):** **1.00 per write** on both schemas — the
  single re-read of the row this transaction just flushed. This is P12b's target;
  the count confirms one redundant SELECT per sync write.
- **⑥ `outbox_watermark` (delta_outbox_v1 SELECT):** **0.00 on the pure-union
  schema** (correct — `proc is None`, the SELECT is skipped entirely, `apply.py:100`)
  and **3.00 on the boolean schema**. Only 1 of those 3 is the capture-before-apply
  watermark (⑥ proper); the other ~2 are the cascade's keyset **drain** reads
  (`outbox_rows`, one per stratum round) — a related but distinct read that P12c
  fences (⑥ the watermark) does *not* cover. So ⑥-the-watermark is present as
  predicted; attribution of the extra outbox SELECTs is the cascade drain, not the
  watermark.
- **④ cursor refresh (index_cursor_v1 SELECT):** 1.00 per write, as predicted; the
  cursor UPDATE is folded into the `U` keyword tally (union U5.0 = 1 cursor + ~4
  refcount updates; boolean U15.2 similarly).

### Composition overhead vs the "K+5-ish" prediction

The inventory predicted "K+5-ish statements of pure composition overhead per sync
write". Reading composition overhead as the **non-index** statements (log INSERT +
store_v4 locks + cursor refresh/update + log_rows + outbox), pure-union comes to
≈ 4.3 (store_v4) + 1 (log INSERT) + 1 (cursor SELECT) + 1 (cursor UPDATE) + 1
(log_rows) ≈ **~8.3**, against a fan-out K of 1.66 — broadly the "K+5-ish" shape once
the lock undercount is corrected. The remaining ~38 statements/write (union) and
~205/write (boolean) are **index work** (`node_v4` + `edge_v4` + `residue_v1`) —
already optimized under P2/P4/P6/P7 and NOT what P12a/P12b target.

### Attribution caveats (honest)

- **`FOR UPDATE` literal count is 0.0** because SQLite drops the clause; the
  `store_v4` SELECT count is the proxy and is exact here (only `_lock_store` selects
  `store_v4` on the write path). On PostgreSQL/MySQL these same statements carry the
  real `FOR UPDATE` and the real contention cost — where the SQLite wall-time
  understates them entirely. That asymmetry is the whole reason statement-count, not
  wall-time, is the primary metric.
- The `remove_tuple` fan-out is not separately reported as a K (the removes replay
  the same fan-out as their matching adds); its store_v4 counts (4.3 / 13.4) track
  the adds as expected.
- Per-op `max` values are large (union add 90, boolean add 535) because a write that
  creates a new group-userset bridge or triggers a wide cascade touches many more
  closure rows than one that lands on existing structure — the mean is the load-
  bearing number, the spread is real workload variance, not noise.
- Wall-time `ops/s` (union add 27/s, boolean add 5/s) is a SQLite-only artifact of
  the statement counts and should not be read as a production throughput figure.

---

## Addendum 2026-07-15 — N16 landed (outbox emit rows bulk-inserted)

N16 (`index_v4/core.py`: `_emit` stages dicts; `_flush_outbox()` drains one
`insert(DeltaOutboxV1), [rows]` per `_add_direct_edge_unsafe`) changes ONLY the
INSERT counts above; every other statement class and all SELECT-table
attributions re-measured byte-identical (S/U/D, `delta_outbox_v1` reads still
3.00/op boolean, all read ops unchanged).

| op | INSERT/op before | after | Δ | total/op before → after |
|---|--:|--:|--:|---|
| union add_tuple | 20.4 | **13.0** | −36% | 46.2 → 38.9 |
| union remove_tuple | 9.2 | **2.2** | −76% | — |
| boolean add_tuple | 40.8 | **28.5** | −30% | — |
| boolean remove_tuple | 19.1 | **7.2** | −62% | — |

Edge-row INSERTs are untouched (descoped: identity-map read-modify-write within
the op — see `PERF_ANALYSIS.md` Applied/N16). The remaining INSERT floor is edge
rows + log row + node interning.

## Addendum 2026-07-15 (2) — N15 landed (per-batch node-resolution cache)

N15 (`index_v4/core.py` + `processor.py` + `connectedstore/apply.py`: per-batch
`(pred,type,name,wildcard)→NodeV4|MISSING` cache with delete-site eviction and
creation-site overwrite) changes ONLY node_v4 SELECT counts; I/U/D and all other
SELECT-table attributions byte-identical.

| op | node_v4 SELECT/write | total stmts/op |
|---|---|---|
| union add_tuple | 11.62 → **10.96** | 38.9 → 38.2 |
| union remove_tuple | — | 31.9 → 31.2 |
| boolean add_tuple | 103.42 → **46.66** (−55%) | 194.4 → 137.7 |
| boolean remove_tuple | — | 161.9 → 119.8 |

Union's residual node redundancy is id-based (`_require_live_nodes` — a
deliberate liveness check, never cached — plus the refcount tail and
`_load_nodes`, which ride the identity map); id-keyed caching was evaluated and
deferred (needs rowid-reuse-safe eviction for a small marginal win).

## Addendum 2026-07-16 (3) — grab-bag micros (`_require_live_nodes` 2 SELECTs → 1 IN)

`_require_live_nodes` (`index_v4/core.py`) now checks both edge endpoints with a
single `select(NodeV4.id).where(id.in_(...))` instead of one point SELECT per id
(still cache-blind — a liveness probe, never the N15 node cache). Changes ONLY
node_v4 SELECT counts; I/U/D and every other SELECT-table attribution byte-identical.

| op | node_v4 SELECT/write | total stmts/op |
|---|---|---|
| union add_tuple | 10.96 → **9.30** | 38.2 → 36.6 |
| union remove_tuple | — | 31.2 → 29.6 |
| boolean add_tuple | 46.66 → **39.90** | 137.7 → 130.9 |
| boolean remove_tuple | — | 119.8 → 113.6 |

The same batch landed two more micros invisible to this bench's op mix: the
`remove_node` neighbour-debit tail (N+1 → 1 IN query; cold node-GC path, verified
separately — node_v4 SELECTs during `remove_node` on an N-neighbour star go N+3 →
flat 3, total 34/114/414/814 at N=10/50/200/400 → flat 14) and a CPU-only
`_collect_residue_memberships` scan cleanup (set/frozenset elimination, ~23% on the
isolated inner loop). Full record: `PERF_ANALYSIS.md` "Applied" (grab-bag entry).
