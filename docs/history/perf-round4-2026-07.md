<!-- RETIRED 2026-07-16: round 4 (R4-BF, N15, N16, M2 + follow-up, N17, N10, N18, the index_v4 grab-bag micros, N12; N11 design-skipped) landed and pushed; this is the verbatim round-4 execution record, archived here. Living docs: open worklist → docs/perf-next-round.md; measured numbers → benchmarks/results/PERF_ANALYSIS.md "Applied"; gates → docs/gate-runbook.md. -->

# Perf optimization — round 4 record (archived 2026-07-16)

Round 4 was the **make-the-graph-index-testable/usable-at-scale** round plus the
wave-3 conditional leftovers from round 3. Date range **2026-07-15 → 2026-07-16**.
Two strategic threads:

1. **Bulk build/apply throughput** so a 10⁵–10⁶-tuple graph index could be built
   at all (R4-BF bulk boolean backfill, N15 per-batch node cache, N16 bulk-INSERT
   outbox rows, N18 bulk-build RAM ceiling), which unblocked —
2. **The M2 scale-bench verdict**: with the graph finally buildable at 200 k, the
   pareto question was answered in full (the graph has exactly one read-side niche:
   forward `lookup` on object-wildcard schemas; the set engine wins everywhere
   else), and the set-engine standalone `lookup` weakness on that same niche was
   closed (N17). N10 (lazy flow-graph off `rebuild()`) and N12 (compile-layer
   pattern cache) landed as below-model micros; N11 was design-skipped.

- **Measured numbers** (per-item mechanism/before-after):
  [`benchmarks/results/PERF_ANALYSIS.md`](../../benchmarks/results/PERF_ANALYSIS.md)
  "Applied".
- **Scale-bench results docs:**
  [`M2_FOLLOWUP_2026-07-15.md`](../../benchmarks/results/M2_FOLLOWUP_2026-07-15.md)
  (demorgans graph curves + both 200 k anchors; verdict final) and
  [`N18_FOLLOWUP_2026-07-16.md`](../../benchmarks/results/N18_FOLLOWUP_2026-07-16.md)
  (gdrive 200 k RSS re-measure after Phase-W/R streaming). Statement-count deltas:
  [`STMT_BASELINE_2026-07-14.md`](../../benchmarks/results/STMT_BASELINE_2026-07-14.md)
  addenda.
- **Git hash list (the audit trail):** R4-BF `b9c3931`, N15 `509baaf`, N16
  `8f439e8`, M2 follow-up bench `34e1f81`, N10 `422c5b9` (+ companion `859b677`),
  N17 `b7e9a75` (+ companion `702d38f`), N18 `bae7c2f`, grab-bag micros `31402bd`,
  N12 `7dd37c3`. N11 was design-skipped (no code change, no hash).
- Successor open worklist: [`docs/perf-next-round.md`](../perf-next-round.md);
  the round-3 record retired before this one:
  [`docs/history/perf-round3-2026-07.md`](perf-round3-2026-07.md).

Everything below is **verbatim** from the round-3-successor worklist as it stood at
round-4 close — history is not rewritten.

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
[`docs/r4bf-bulk-backfill-design.md`](../r4bf-bulk-backfill-design.md); numbers +
correctness story in [`benchmarks/results/PERF_ANALYSIS.md`](../../benchmarks/results/PERF_ANALYSIS.md)
"Applied"; Lean disposition (alternative constructor of the same modeled state)
in [`formal/CORRESPONDENCE.md §8.1`](../../formal/CORRESPONDENCE.md).

### N15. Per-batch node-resolution cache in the apply/cascade path — ✅ LANDED 2026-07-15
Per-batch `(pred,type,name,wildcard) → NodeV4|MISSING` cache on
`ReachabilityIndex`, `None` outside a batch, reentrant scope at
`advance_index` + standalone `run_cascade`; all five NodeV4 delete sites
evict, the `node()` creation choke point overwrites negatives; identity-tuple
keys sidestep the W2 id-cache hazards (within-txn, torn down before commit so
paranoia reads cache-blind). **Boolean node_v4 SELECTs 103.4 → 46.7/write
(−55%); boolean totals −26–29%; union ~flat** (its residue is id-based —
deliberately uncached: `_require_live_nodes` is a liveness check). Id-keyed
caching of the refcount tail/`_load_nodes` deferred (rowid-reuse-safe eviction
needed; small win). Mechanism + gate:
[`PERF_ANALYSIS.md`](../../benchmarks/results/PERF_ANALYSIS.md) "Applied"; stmt
deltas in `STMT_BASELINE_2026-07-14.md` addendum 2. Lean: none (below model).

### N16. Bulk-INSERT the emit/outbox rows — ✅ LANDED 2026-07-15 (edge rows descoped)
Outbox `_emit` rows now stage as dicts and bulk-insert in ONE
`insert(DeltaOutboxV1), [rows]` per `_add_direct_edge_unsafe` (the sole emit
driver; ids verified monotone in emission order). INSERTs/op: union add
20.4→13.0, union remove 9.2→2.2, boolean add 40.8→28.5, boolean remove
19.1→7.2; all other statement counts byte-identical. **Edge-row batching
descoped** (new EdgeV4 instances are identity-map read-modify-written and
deleted within the same op — Core inserts would force restaging the P2
ref-count batch; high risk, small marginal win). Mechanism + gate:
[`PERF_ANALYSIS.md`](../../benchmarks/results/PERF_ANALYSIS.md) "Applied";
stmt deltas in `STMT_BASELINE_2026-07-14.md` addendum. Lean: none (below
model).

### M2. Graph scale-bench: find the pareto crossover — ✅ CLOSED 2026-07-15 (follow-up run done; verdict final)
Results: [`benchmarks/results/ROUND3_COMPARISON_2026-07-15.md`](../../benchmarks/results/ROUND3_COMPARISON_2026-07-15.md)
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
**Follow-up run ✅ 2026-07-15 (post-R4-BF), results in
[`M2_FOLLOWUP_2026-07-15.md`](../../benchmarks/results/M2_FOLLOWUP_2026-07-15.md):**
demorgans graph curves at 4.8k–163k tuples + both 200k anchors, all built within
the cap. **Final verdict: the graph has NO second read-side win.** On boolean
(demorgans, wildcard-free) schemas the set engine beats the graph on every
surface at every scale (check ~26×, build 5×, RAM 1.5–2.6×); the graph's only
read-side niche remains forward `lookup` on object-wildcard schemas (~1,066× at
200k, widening with N). demorgans graph build is linear (O(N^1.03)) post-R4-BF.
Binding constraint at scale is now bulk-build RAM (gdrive 200k peaked 3.51 GB,
survived via swap) → N18 below. Original follow-ups: (b) N17 below stands;
(c) is now N18.

### N17. Set engine: sub-O(store) lookup for object-wildcard schemas — ✅ DONE 2026-07-15 (gate + scale bench green)
- **Why:** the M2 verdict — owc `lookup` at 0.27/s @100k is now the worst read
  surface in the system by orders of magnitude. Mitigations by deployment: the
  composed system already graph-serves lookup (flat); this item is for
  set-engine-standalone use.
- **What (shipped):** deleted the `_owc_needs_sweep` gate so the O(reachable)
  reverse walk runs on EVERY schema; the object-wildcard case is covered by inline
  **wildcard-bridge seeding** — on dequeuing a `(T,'*',·)` star node the walk
  enqueues the wildcard-covered concrete siblings (`ids_of_shape[(T,r')]` + a
  star-parent×TTU cross), every candidate `check`-confirmed. `_lookup_sweep`
  retained as the differential test reference. ALGORITHM CHANGE on candidate
  generation; gated by strict `test_lookup_oracle.py` (new `owc_star_ttu` corpus +
  8 handwritten regressions) + a `test_owc_bridge_walk_vs_sweep` differential
  (walk == sweep, both SetOps) + the hypothesis lookup machine. **Lean:** none
  (forward lookup unmodeled; `CORRESPONDENCE.md §8.1` N17 entry).
- **Scale bench (`n17_scale_2026-07-15.jsonl`, gdrive set:roaring): the owc
  lookup curve is now FLAT — 222 / 221 / 224 / 207 lookups/s at scale
  250/1k/4k/10k = 4.2k → 168k raw tuples — vs the old sweep's O(store) collapse
  (7.4 → 1.8 → 0.44/s over 4.2k → 67k tuples, `scale_bench_2026-07-15.jsonl`
  baselines): ~25× at 4.2k tuples growing to ~1,000×+ at 168k, widening with N.**
  `simple` control unchanged (13.2k/14.0k /s at 16k/64k vs the 10.1k–16.6k
  baseline band); checks unchanged. Gate: split suite 543+24 green, verify.sh
  lean/conf-heavy/conf-rest green, 6-seed hypothesis sweep green.
- **Discovered + fixed THREE pre-existing set-engine bugs** (full record:
  `docs/spec-deviations.md` 2026-07-15), all on star-tupleset (`[T, T:*]`) × TTU
  states no prior corpus built: (1) the walk's H3 folded only the concrete bare
  parent, dropping downstream objects behind a STAR bare parent (design-review
  find, oracle-confirmed); (2) the walk seed was empty for uninterned from-chain
  star-identity userset subjects (walk≡sweep differential find, first run); (3)
  an ACCEPT/REJECT divergence — the set engine accepted a same-type star parent
  (`folder:* parent folder:f2`) that the graph rejects as a routed same-shape
  wildcard self-reference cycle (seed-7 hypothesis find; `_would_cycle` now runs
  the §1.5 check over derived pairs; `test_reg9` pins parity both ways).

### N18. Bulk-build RAM ceiling — ✅ LANDED 2026-07-16 (RESHAPED by the tracemalloc probe: Phase-W/R streaming, DP untouched)
- **Why:** the M2 follow-up's binding constraint — gdrive/200k peaked **3.51 GB**
  working set (vs the set engine's 0.92 GB) and built only by swapping; RAM, not
  the cap, gated >100k object-wildcard graph builds, exactly the niche (owc
  forward lookup) where the graph is worth building at all.
- **RESHAPED (2026-07-16 tracemalloc probe): the DP is NOT the hog.** The closure
  grows linearly on gdrive (100,548 / 402,948 / 1,209,348 pairs at 16.8k / 67.2k
  / 201.6k tuples) and the Phase-P `pvec` holds only ~210 MB at 201.6k; a
  release-vectors-when-consumed schedule would reclaim only ~9% (91% of vectors
  simultaneously live). The original chunk/stream/spill-the-DP plan was dropped —
  **phases R/B/C/P are logically untouched**. The real hogs were: Phase W's
  `edge_rows` + `outbox_rows` (two full per-row-dict lists, ~3× the DP, ~700 MB
  at 200k, handed to single giant `session.execute(insert(...), rows)` calls
  that reprocess them inside SQLAlchemy); the Phase-R `.all()` snapshot (~200k
  ORM `TupleV1` objects referenced for the whole build); and ~165k `NodeV4` ORM
  instances parked in the session identity map after the flush.
- **What (shipped, all in `index_v4/bulk_build.py`):** (a) Phase W generates +
  executes + frees the edge/residue/outbox row dicts in bounded 50k-row chunks
  (slices of the sorted `edge_pairs` / `residues.items()`) — same rows, same
  order, so per-table auto-increment ids assign exactly as the old single
  INSERTs; (b) Phase R streams the snapshot via
  `.execution_options(yield_per=10_000)` selecting only the six routed columns
  (no ORM entities enter the identity map), same `order_by(TupleV1.id)`; (c) the
  flushed `NodeV4` instances are expunged after `node_id` capture (nothing
  downstream needs them — `connectedstore/build.py`'s `ensure_cursor`/commit
  path re-reads via fresh queries). `bulk=False` reference path and
  `bulk_backfill.py` untouched.
- **Measured (gdrive graph, `n18_followup_2026-07-16.jsonl`, the M2 §6 Phase-B
  flags, ~2.87 GB free of 15.8 GB at run start): 201.6k tuples peak RSS 3,512 →
  1,117 MB (−68%, 3.14×); build 390.5 → 314.2 s, comfortably under the cap
  (cross-session wall not comparable — RSS is the headline; peak now fits in
  free RAM, no swap). 67.2k sanity point: peak 405 MB, vs round-3's 925 MB
  @50.4k / 1,788 MB @100.8k curve. `answers_sig` byte-identical to the M2
  follow-up gdrive value (`d9ddd99d…9999`) at both scales.** Remaining peak is
  the in-memory graph state itself (`m`/`succ`/`pvec`/`edge_pairs`) — linear in
  closure, no longer SQLAlchemy row staging.
- **Gate:** `tests/test_bulk_build.py` (6 — the build-vs-incremental identity
  gate) + the connectedstore suite + `test_matrix.py`, 60 green total. **Lean:**
  none — same rows, same modeled state, alternative constructor unchanged in
  effect; logged in `formal/CORRESPONDENCE.md §8.1` alongside P13/R4-BF.
  Mechanism + numbers in [`PERF_ANALYSIS.md`](../../benchmarks/results/PERF_ANALYSIS.md)
  "Applied"; results note `benchmarks/results/N18_FOLLOWUP_2026-07-16.md`.

### Minor notes (grab-bag) — landed bullet
- ✅ **LANDED 2026-07-16** (grab-bag micros; `PERF_ANALYSIS.md` "Applied",
  `STMT_BASELINE` addendum 3): `remove_node` neighbour-debit tail N+1 → 1 `IN`
  query (cold node-GC path — node_v4 SELECTs during `remove_node` on an
  N-neighbour star N+3 → flat 3); `_require_live_nodes` 2 point SELECTs → 1
  `IN` (still cache-blind — union add node_v4 10.96→9.30, boolean 46.66→39.90);
  `_collect_residue_memberships` set/frozenset elimination + lazy `upos` decode
  (CPU-only, ~23% on the isolated residue-scan inner loop).

---

## Wave 3 — conditional items (landed / disposed this round)

### N10. Defer flow-graph construction on read-triggered `rebuild()` — ✅ LANDED 2026-07-16 (targeted gate green; `formal/` companion landed, see note)
Rebuild replayed every tuple through `_ruleset.apply()` (the full `_derived_pairs`
rewrite fan-out) purely to populate `_flow_adj`/`_edge_count` — write-only
cycle-detection state reads never consult. Now `_flow_built` gates all flow work:
`rebuild()` / constructor replay skip the fan-out entirely, and a single
`_ensure_flow_graph()` guard on every flow touch point (`_flow_reaches` read +
`_flow_add_edge`/`_flow_remove_edge` mutations) builds the complete graph on demand,
exactly once, before the first write's cycle check. Reconstructed from the in-memory
`node_sets` (the complete stored-septuple collection `_tuple_present` answers from —
no DB read), byte-identical edge multiset to the old per-row replay. Incremental
maintenance unchanged once built; boolean schemas still build nothing. **gdrive scale
4000 (67,200 tuples, set:roaring): `rebuild()` 4.99 s → 1.26 s (~4.0×); flow fan-out
was 74.8% of the eager wall.** Read-only reopen never builds the graph. Accept/reject
parity (incl. the N17 §1.5 routed-star check, `test_reg9`) unchanged. Gate:
`test_matrix.py` (12), setengine/storage/engine/lookup_oracle (94),
`test_hypothesis.py` (12) — all green. **`formal/` companion (integration,
orchestrator-owned):** `formal/conformance/test_conformance_remove.py`'s white-box
`_fingerprint` (`:189-190`) reads `_edge_count`/`_flow_adj` directly and asserts a
bare `rebuild()` reproduces them eagerly — which lazy rebuild deliberately no longer
does. One-line, assertion-preserving adaptation: call `eng._ensure_flow_graph()`
before snapshotting the two flow-graph keys in `_fingerprint`, so both driven and
rebuilt engines materialize before the (unchanged) convergence comparison. Outside
the setengine track's file scope; companion landed 859b677.
Numbers + mechanism in [`PERF_ANALYSIS.md`](../../benchmarks/results/PERF_ANALYSIS.md)
"Applied". Lean: none (below model — write-only auxiliary state).

### N11. Duplicate-add: return the known watermark instead of `SELECT MAX(id)` — ❌ DESIGN-SKIP 2026-07-16 (token contract forbids the only cheap substitute)
`connectedstore/source.py:89-99`. **Semantic judgement (done): the substitution
is unsafe.** The only session-local watermark we could return without the
`SELECT MAX(id)` is `evaluator_watermark`, and it can *lag the engine's actual
contents*: `refresh_evaluator` reads the watermark BEFORE the rebuild query, so a
row committed by another session in that gap is included in the rebuilt engine but
NOT claimed by the watermark (the documented "conservative" rebuild,
`source.py:144-152`). A duplicate `add` is reached precisely when the tuple is
already in the engine — including such an ahead-of-watermark tuple `T@k` with
`k > evaluator_watermark`. The freshness-token contract (spec §2.5) is "a read at
cursor ≥ token reflects this write"; for a duplicate the observable effect is "T is
present", so the returned token must be ≥ `k`. Returning `evaluator_watermark < k`
would let a later `check(at_least=token)` be served by a graph index whose cursor
sits at that lower value and has NOT yet applied `T` → a stale "absent" answer under
an explicit freshness demand. The current global-head `SELECT MAX(id)` is the only
cheaply-computable value guaranteed ≥ `k` (the tuple's true log id is unknown without
a query). Existing gate `tests/test_connectedstore_source.py::test_duplicate_add_is_idempotent_no_log_row`
(`t2 == t1`) only pins the single-session case where head == `k`; it does not
cover the multi-session race, so it would not have caught the bug. Cost is one
SELECT per *duplicate* write only (retry-heavy workloads); not worth a
freshness-correctness hazard. No code change.

### N12. Cache `EntityPattern`s in `RelationalTriplePattern` — ✅ LANDED 2026-07-16 (micro 2.1× on gdrive `apply`; snapshot bytes preserved)
`zanzibar_utils_v1.py`: the `.subject`/`.object` `@property`s rebuilt a fresh
frozen `EntityPattern` on every `match()`/`replace()` call. Now built ONCE at
construction (compile time) into two `field(init=False, repr=False, compare=False)`
cache slots populated in `__post_init__` via `object.__setattr__` (frozen bypass);
the properties return the cached instances. `init=False` keeps the `__init__`
signature, `repr=False` keeps the compiled-RuleSet snapshot bytes byte-identical
(the snapshot gate is `repr()` of the dataclass fields), `compare=False` keeps
`eq`/`order` over the declared fields only. Patterns are compile-time artifacts —
never rebuilt per write — so the cost is paid once and amortized over all writes.
**Micro (`RuleSet.apply`, gdrive fixture, 20 reps × 600 triples, best of 7,
stable over 3 runs): 155 → 73.5 ms (2.1×, −53%)** — the profile attributed ~20% of
`apply` tottime to the two properties, but gdrive's TTU/union `replace` fan-out
multiplies the builds, so eliminating them halves the wall. demorgans flat (~12.5 ms;
its derived-family path builds fewer patterns per `apply`). End-to-end write loop
(closure/SQL-dominated, ~500 graph writes) 9704 → 9336 ms — not a regression (apply
is a tiny fraction there, as the worklist predicted). Snapshot gate + matrix +
lookup_oracle + boolean_compile + schema/parse/compile/utils + hypothesis all green.
Numbers in [`PERF_ANALYSIS.md`](../../benchmarks/results/PERF_ANALYSIS.md) "Applied".
Lean: none (below model — construction-caching, identical results).
