# Perf optimization — open worklist (slim, opened 2026-07-15 after round 3)

The living list of **remaining, not-yet-landed** performance opportunities. Round 3
(P12-M, P12a/b, N4–N9, the P1 follow-up, P13) landed and pushed; its full worklist +
execution record is retired verbatim in
[`docs/history/perf-round3-2026-07.md`](history/perf-round3-2026-07.md).

- **Measured numbers** (all landed items, per-item mechanism/before-after):
  [`benchmarks/results/PERF_ANALYSIS.md`](../benchmarks/results/PERF_ANALYSIS.md)
  "Applied" — git log is the audit trail.
- **Gates** (cap-safe recipe, phased `verify.sh`, fuzz sweep): don't duplicate —
  [`docs/gate-runbook.md`](gate-runbook.md).
- **The Lean column.** Per CLAUDE.md "Perf work & the Lean model": a
  behavior-preserving micro-opt needs no Lean change (differential matrix +
  hypothesis + conformance are the net). An optimization that *changes the modeled
  algorithm* must update the corresponding Lean def and re-run `formal/verify.sh`
  (phased), or log the gap in `formal/CORRESPONDENCE.md §7`. Each item's Lean line
  below states which side it sits on.

Everything here is **conditional**: it needs a motivating measurement (from
`benchmarks/stmt_bench.py` / `scale_bench` / a fresh profile) or a design call before
it's worth landing. Nothing below is expected to need Lean work unless its line says
so. **Never edit a golden/oracle/snapshot result to make an opt pass. Never run two
heavy jobs (bench or pytest) concurrently** (CPU contention corrupts bench numbers).

---

## Wave 3 — conditional items (need measurement or a design call first)

### N10. Defer flow-graph construction on read-triggered `rebuild()`
`setengine/engine.py:290-298,:434-438`: rebuild replays every tuple through
`_ruleset.apply()` purely to populate `_flow_adj`/`_edge_count` — state that
only write-time cycle detection reads. `refresh_evaluator` fires on
rollback/tokened-read fallback and is often followed by reads only. Lazy-build
on first write instead. **Medium risk** (flow graph must be complete before
the first cycle check; lazy build must reconstruct from in-memory state).
Distinct from the fenced incremental-catch-up (no watermark contact). Boolean
schemas already skip (`:489`) — this is for union/TTU schemas. Gate:
`test_matrix.py` cycle-rejection parity, storage/eval tests,
`conf-heavy` (rebuild-after-remove), hypothesis restoration.

### N11. Duplicate-add: return the known watermark instead of `SELECT MAX(id)`
`connectedstore/source.py:88-91`. One round trip per duplicate write; bites
retry-heavy workloads only. **Semantic judgement required**: `log_watermark`
is the global store head, `evaluator_watermark` this session's — equal in the
single-session deployment, but confirm the token contract only needs "≥ enough
to see this (absent) write" before changing. Skip unless `stmt_bench` shows
duplicates matter.

### N12. Cache `EntityPattern`s in `RelationalTriplePattern`
`zanzibar_utils_v1.py:174-182`: `@property`s rebuild frozen sub-patterns per
`match()` call. Low risk, likely <1% (P0 dispatch already prunes candidates).
Must preserve compiled-RuleSet snapshot bytes (`tests/snapshots/`). Bundle
with any future compile-layer touch rather than standalone.

### N13. Graph `check`: batch node resolution (3–5 sequential point SELECTs → ~2) — DEPRIORITIZED
`index_v4/wildcard.py:331-388,:428-462`. check IS round-trip-bound (388–682/s
flat), so this is real — but **`stmt_bench` measured graph `check` at 2.7–3.1
stmts/op already (little headroom)**, so it's deprioritized: resolution
restructuring must preserve exact probe semantics (position rule,
missing-node-drops-key, `:349,:363-374`), and it's fiddly, for a small win.
Revisit only if a fresh statements-per-check profile shows more headroom;
medium risk. Behavior-preserving if done right. Gate: matrix 4-way + lookup
oracle + conformance.

### N14. Hoist `_keys_referencing` to one residue scan per `_map_deltas_to_keys` call
`index_v4/processor.py:316-332`, called per GC'd subject at `:836-839`. M
subject GCs = M full ResidueV1 scans + JSON decodes; hoist to one snapshot
scan building `subject_id → [Key]`. **Scope to the step-A loop only** (the
reconcile-step-5 calls mutate residues mid-flight). Only bites TTU/userset
schemas N3 doesn't already elide, on churn-heavy removes. Medium risk —
modeled delta→key territory (same class as P6): behavior-preserving only if
the key set is provably identical; full differential + hypothesis + paranoia
gate. Niche; needs a workload that shows it first.

---

## Round 4 candidates: make the graph index testable/usable at scale

The strategic driver: the graph index's value proposition (O(1) durable
DB-served reads, no per-process RAM ∝ store, many replicas, structural
freshness tokens) only materializes at scales the bench has never reached —
graph curves have 3 small anchor points because **build throughput** made a
10⁵–10⁶-tuple index impractical to construct. P13 (the bulk closure builder)
landed 44–49× on pure-union builds, but **boolean *total* build only 1.44×**
because the shared `backfill()` pass P13 leaves untouched now dominates the
boolean build — so the next bulk-phase win is the backfill. These items attack
build/apply throughput, in ROI order. Note the asymmetry: steady-state
*incremental* write cost is largely the algorithm itself (closure maintenance
is O(ancestors×descendants) per write — the memoization you're buying); the
big recoverable waste is in **bulk construction** and per-batch SQL overhead.

### R4-BF. Bulk the boolean `backfill()` phase — ✅ LANDED 2026-07-15
In-memory Phase D mirror of `DeltaProcessor.backfill()` on the bulk build path
(`index_v4/bulk_backfill.py` + extended `index_v4/bulk_build.py`;
`connectedstore/build.py`'s bulk branch skips `proc.backfill()`). Boolean
*total* build ~201× on demorgans / ~60× on boolean_wildcards; `backfill()`
itself unchanged (repair path + `bulk=False` reference side). Design:
[`docs/r4bf-bulk-backfill-design.md`](r4bf-bulk-backfill-design.md); numbers +
correctness story in [`benchmarks/results/PERF_ANALYSIS.md`](../benchmarks/results/PERF_ANALYSIS.md)
"Applied"; Lean disposition (alternative constructor of the same modeled state)
in [`formal/CORRESPONDENCE.md §8.1`](../formal/CORRESPONDENCE.md).

### N15. Per-batch node-resolution cache in the apply/cascade path
- **What:** node_v4 SELECTs are 11.6/write (union) and 103/write (boolean) —
  25–50% of all write statements; the same subject/object/bridge/leaf nodes
  are re-resolved per row within one `advance_index` batch / cascade run.
  Cache `(pred, type, name, wildcard) → NodeV4` for the duration of a batch,
  invalidating on node creation/GC-deletion (the hard part — GC deletes node
  rows mid-cascade; a stale hit would resurrect a dead id, so the cache must
  be invalidated by the GC paths or keyed to check liveness).
- **Risk:** medium (GC invalidation). **Lean:** none (resolution is below the
  model). **Gate:** full suite incl. paranoia + conformance; stmt_bench delta.

### N16. Bulk-INSERT the emit/outbox and edge rows
- **What:** INSERTs are ~40% of union write statements (20.4/write). Outbox
  `_emit` rows are plain value inserts — batchable via `executemany`/
  `session.execute(insert(...), [rows])` at flush points; edge inserts ride
  the P2 batch already but flush row-at-a-time. Constant-factor; biggest on
  networked DBs (per-statement latency), visible in stmt counts everywhere.
- **Risk:** low-medium (ordering: outbox ids must stay monotone within the
  txn — verify autoincrement behavior under executemany on SQLite/Postgres).
  **Lean:** none. **Gate:** full suite + conformance (outbox order is
  load-bearing for the cascade) + stmt_bench.

### M2. Graph scale-bench: find the pareto crossover — ✅ RUN 2026-07-15 (to 100k; 200k+ blocked on R4-BF)
Results: [`benchmarks/results/ROUND3_COMPARISON_2026-07-15.md`](../benchmarks/results/ROUND3_COMPARISON_2026-07-15.md)
(new curves in `graph_scale_2026-07-15.jsonl`; run under memory pressure —
~1.6× systematic offset, de-trended against the unchanged `check` control).
**The verdict flipped the round-4 rationale:**
- **P1 flattened set-engine lookup, so the graph index no longer wins ANY read
  surface on wildcard-free schemas** (set beats it ~30–130× on reads, builds
  19× faster, at every measured scale to 100k).
- **The graph's remaining read-side win is forward `lookup` on object-wildcard
  schemas** — set-engine gdrive lookup collapses to 0.27/s at 100k (the
  by-design O(store) sweep) while graph holds flat ~150/s (54× at 10k, ~570×
  at 100k). This is also exactly the surface `ConnectedStore.lookup` already
  serves from the graph — the composed system routes around the weakness.
- Graph bulk build is super-linear in wall/RAM (simple O(N^1.66); gdrive
  peaked 1.79 GB at 100k — the DP holds the whole closure in memory), and the
  graph's architectural wins (durability, multi-replica, no per-process
  rebuild, freshness tokens) remain unmeasured by a single-process bench.
**Follow-ups this creates:** (a) R4-BF is now ALSO what blocks 200k+/demorgans
curves (backfill-bound builds blow the command cap) — **R4-BF landed 2026-07-15,
so the 200k+/demorgans scale-bench rerun is now unblocked** (a fresh M2
follow-up run is future work, not yet done); (b) a NEW candidate below
(N17); (c) chunk/stream the bulk-build DP if >100k builds matter (RAM).

### N17. Set engine: sub-O(store) lookup for object-wildcard schemas (NEW 2026-07-15)
- **Why:** the M2 verdict — owc `lookup` at 0.27/s @100k is now the worst read
  surface in the system by orders of magnitude. Mitigations by deployment: the
  composed system already graph-serves lookup (flat); this item is for
  set-engine-standalone use.
- **What:** replace the full O(store) sweep with the O(reachable) walk PLUS an
  explicit wildcard-bridge enumeration: when the walk reaches a `(T,'*',rel)`
  star node, additionally enumerate the concrete `T` objects stored as TTU
  tupleset parents (the exact case CORRESPONDENCE §8.1 documents the walk
  missing) instead of falling back wholesale. ALGORITHM CHANGE on the surface
  that shipped the owc×TTU bug — strict `test_lookup_oracle.py` + multi-seed
  fuzz gate mandatory; over-include when in doubt. **Lean:** none (forward
  lookup unmodeled). Design review before implementation.

### Minor notes (grab-bag, land opportunistically with adjacent work)
- `core.py:377-403` remove_node neighbour-debit tail N+1 (batchable `IN`; cold
  path). `core.py:454-464` `_require_live_nodes` 2 SELECTs → 1.
- `wildcard.py:502-508` `_collect_residue_memberships` builds sets for
  single-membership tests and decodes `upos` unconditionally.
- `invariants.py:322-368` paranoia delta verifier is O(pairs × edges) per
  commit — production-paranoia cost, out of scope for bench numbers; noted so
  nobody profiles paranoia-on and panics.
- Dead ends already confirmed, do NOT chase: rc pre-guard on `_gc_subject_node`
  (bridge-stripping drops rc post-scan — load-bearing scan); removing
  `ops.new()` in `_starpop` without the `update` primitive (Population
  contract); N1/N2 (measured cold); P11 (struck).

---

## P12c — FENCED: do not touch without a design round + Lean plan

A standing do-not-touch list (from the round-3 P12 decomposition). These are the
composition-write round-trips that would change the modeled algorithm; leave them.

- **`session.refresh(cursor)`:** the double-apply guard under the lock and
  the input to P12b's guard. Stays.
- **`outbox_watermark` capture-before-apply:** the cascade replay
  boundary; frontier machinery is modeled (`frontierRowsAbove`/`frontierMax`,
  `CORRESPONDENCE.md §5`). Other sessions legitimately raise the watermark
  between transactions; a stale-low cache replays foreign deltas. One SELECT
  per boolean write is the price. Stays.
- **Transaction coupling / exactly-once (log INSERT flush / cursor UPDATE
  flush / COMMIT):** moving the cascade out of the write transaction, batching
  commits, async-first — genuine spec + Lean work (`ReachedByW3d2E` changes).
  Out of scope.
- **`rebuild()` / incremental evaluator catch-up** (`source.py:124-132`,
  `setengine/engine.py rebuild`): the failure-path rebuild is what makes
  rollback correct — the in-memory engine holds phantom state that can't be
  incrementally undone without an undo journal, and *that* is a new algorithm
  on the evaluator-freshness watermark contract. Cold path anyway (ordinary
  rejections take the cheap branch, `store.py:100-106`). Cost documented;
  not changing. (N10 above defers *write-only auxiliary* state off the
  rebuild — a different, narrower thing.)

---

## Standing hygiene / gate notes

- `setengine/` and `index_v4/` do not cross-import (verified 2026-07-14); keep
  parallel tracks file-disjoint — a track that discovers it needs a file
  outside its list stops and reports.
- **Full suite + phased verify.sh at every wave integration**, not just
  per-track targeted gates (the P0 lesson; the paranoia checker only runs in
  the full index_v4 suite). Cap-safe recipe: [`docs/gate-runbook.md`](gate-runbook.md).
- **Algorithm changes fuzz before push** (gate-runbook §3) — any item whose
  Lean line says it touches modeled territory (N14 pending; R4-BF landed
  2026-07-15 with its multi-seed sweep) ends with the multi-seed fuzz sweep.
- **Measurement hygiene:** never two bench/pytest processes at once. New
  statement-count results go in `STMT_BASELINE_2026-07-14.md` +
  `PERF_ANALYSIS.md` "Applied" entries; never overwrite `scale_bench.jsonl`.
- Model policy (the loop that landed rounds 1–3): Fable orchestrates and
  reviews (trust contracts, wave gates, any Lean touch); Opus subagents
  implement below-the-model items. Scope drift toward a modeled algorithm
  stops the track and escalates.
