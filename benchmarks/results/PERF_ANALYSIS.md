# Perf-curve analysis — 2026-07-14

Fitted scaling laws and a **PySets vs RoaringSets** comparison over the pre-perf
baseline (`scale_bench.jsonl`, 21 rows: `set:roaring` ×9, `set:py` ×9, `graph`
×3 — one session, `paranoia=False`, in-memory SQLite). Raw throughput/RSS tables
and reproduce commands live in [`BASELINE_2026-07-13.md`](BASELINE_2026-07-13.md);
this file is the *analysis*. Statements-per-operation baseline (composition-layer
sync writes, P12-M) lives in [`STMT_BASELINE_2026-07-14.md`](STMT_BASELINE_2026-07-14.md).

Regenerate:

```bash
PY="C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe"
"$PY" -m benchmarks.analyze       # dependency-free: fits + ratio tables (markdown)
"$PY" -m benchmarks.plot_curves   # needs matplotlib (benchmarks/requirements-analysis.txt)
```

![perf curves](perf_curves.png)

Log-log axes, so the slope *is* the exponent: a flat line is O(1), a −45° line is
O(N). Colour = workload, solid = RoaringSets, dashed = PySets, triangles = the
graph index (one scale each).

## Scaling laws (log-log least-squares fit)

Per-op **cost** exponent = −(throughput slope); **write** is fit on build-time vs
tuples (slope ≈ 1 ⇒ linear load). Fits are over 3 scale points/curve; R² shown.

| impl | workload | surface | slope | R² | law |
|---|---|---|--:|--:|---|
| set:roaring | simple    | write | +0.99 | 1.000 | **O(N)** linear |
| set:roaring | simple    | check | −0.03 | 0.49 | **O(1)** flat |
| set:roaring | simple    | lookup | −1.03 | 1.000 | **O(N)** |
| set:roaring | simple    | reverse | −0.03 | 0.48 | **O(1)** flat |
| set:roaring | gdrive    | lookup | −1.03 | 1.000 | **O(N)** |
| set:roaring | gdrive    | reverse | −0.06 | 0.999 | **O(1)** flat |
| set:roaring | demorgans | lookup | −0.77 | 0.989 | ~O(N^0.8) |
| set:roaring | demorgans | reverse | −0.01 | 0.25 | **O(1)** flat |
| set:py | simple    | check | −0.01 | 0.59 | **O(1)** flat |
| set:py | simple    | lookup | −1.02 | 0.999 | **O(N)** |
| set:py | simple    | **reverse** | **−0.69** | 0.885 | **~O(N^0.7)** ⚠ |
| set:py | gdrive    | lookup | −1.02 | 1.000 | **O(N)** |
| set:py | gdrive    | reverse | −0.18 | 0.884 | ~flat |
| set:py | demorgans | lookup | −0.83 | 0.974 | ~O(N^0.8) |
| set:py | demorgans | reverse | −0.12 | 0.982 | ~flat |

(write and check fit identically across workloads for both backends: write
+0.97…+1.01 @ R²=1.000; check −0.01…−0.08, i.e. flat. Full table:
`python -m benchmarks.analyze`.)

**What the exponents say.**

- **write — O(N), both backends.** Load time is linear in tuple count (≈780
  writes/s regardless of N); nothing super-linear in the set-engine write path.
- **check — O(1), flat.** Confirmed to 10⁵ tuples. A check walks only the query's
  neighborhood, never the store. (Low R² is just tiny noise around a flat line.)
- **lookup — O(N).** The clean slope −1.03 @ **R²=1.000** on simple/gdrive is a
  textbook confirmation that set-engine `lookup` is an O(stored-tuples) candidate
  sweep (`engine.py:821`). demorgans is ~O(N^0.8) — slightly shallower because its
  result set *also* grows with N (mean lookup result 245 → 3,560 ids), so the
  time-box caps completed iterations rather than the sweep alone setting the rate.
- **reverse — O(1) for RoaringSets; O(N^0.7) for PySets on `simple` ⚠.** This
  looks backend-specific but isn't: `direct_expand` copies the whole type
  population per call (`engine.py:768`), which is O(N) work for *both* backends —
  PySets surfaces it (Python set copy), RoaringSets hides it (fast C bitmap copy).
  A one-line fix removes the copy and flattens both. See PySets-vs-Roaring and
  optimization target #1.

## PySets vs RoaringSets

Ratio = roaring rate / py rate; **>1 ⇒ Roaring faster, <1 ⇒ PySets faster.**

| workload | tuples | write | check | lookup | reverse |
|---|--:|--:|--:|--:|--:|
| simple    | 1,000   | 1.04 | 0.91 | 0.93 | 0.68 |
| simple    | 10,000  | 1.00 | 0.82 | 1.03 | 1.32 |
| simple    | 100,000 | 1.08 | 0.85 | 0.90 | **13.97** |
| gdrive    | 4,200   | 1.11 | 0.91 | 0.93 | 0.64 |
| gdrive    | 16,800  | 0.98 | 1.11 | 0.91 | 0.65 |
| gdrive    | 67,200  | 0.98 | 0.77 | 0.91 | 0.89 |
| demorgans | 4,850   | 1.00 | 0.91 | 0.94 | 0.83 |
| demorgans | 54,250  | 1.01 | 0.88 | 0.95 | 1.07 |
| demorgans | 162,750 | 1.01 | 0.87 | 1.23 | 1.23 |
| **geomean** | | **1.02** | **0.89** | **0.97** | **1.20** |

- **write ≈ tie** (1.02×) — both just append tuples; the bitmap backend adds
  nothing at write time.
- **check: PySets ~12% faster** (0.89× geomean). These are tiny-set pointwise
  traversals; Python's native `set` beats the pyroaring FFI overhead. (Matches the
  micro-benchmark: roaring only pulls ahead on *bulk* `expand`, ~33× — see
  `BASELINE_2026-07-13.md`.)
- **lookup ≈ tie** (0.97×) — both are dominated by the same O(N) `check` sweep, so
  the per-check backend difference washes out.
- **reverse: RoaringSets wins overall (1.20×), and *decisively at scale*** — at
  100k tuples on `simple`, PySets reverse is **14× slower** (2.0k vs 27k/s,
  reproduced). **Root-caused (not GC):** `direct_expand` at `engine.py:768` does
  `ops.new(ns.entities) & ops.new(pop((rtype,'...')))`, and `pop(...)` already
  returns the *persistent* type-population mask (`population()`, engine.py:270).
  The redundant `ops.new()` **copies the entire N-element population every call**,
  just to intersect it against ~4 entities — O(population) per expand, regardless
  of the tiny result. PySets pays it as a Python `set(100k)` copy (the cliff);
  RoaringSets pays it as a fast C `BitMap` copy (looks flat). Disabling GC does
  **not** help (1.79k → 1.85k), and a fixed-key expand craters identically —
  confirming allocation-copy, not GC. **Verified fix** — drop the redundant copy
  (`ops.new(ns.entities) & pop(...)`, `&` returns a new set so the mask is
  untouched): the intersection goes **flat** on both backends (py **1,614 →
  2.93M/s at 100k, 1817×**; roaring 2.8×). **Applied 2026-07-14** (see *Applied*):
  end-to-end simple reverse is now flat — PySets **1,944 → 57,136/s at 100k (29×)**,
  RoaringSets 27k → 35k. The baseline tables/plot above are the *pre-fix* snapshot.

**Verdict:** `RoaringSets` remains the right default (it is) — it never regresses
asymptotically and holds reverse flat at scale. `PySets` is a legitimate, slightly
faster choice for **check-dominated, small-store** workloads, but its reverse
scaling makes it a poor fit for reverse-heavy or large stores.

## Graph index (3 anchor points)

Only one scale/workload (build is 15–156 writes/s), so no slope — but the levels
confirm the design: graph reads are DB-round-trip-bound and flat
(check 388–682/s, reverse 99–530/s), and graph **lookup is flat and beats the set
engine once N is nontrivial** (simple: graph 534/s vs set 3.4/s at 100k) — the
materialized closure is the O(1) answer to the set engine's O(N) sweep.

## Applied

- ✅ **N12 — cache the frozen sub-patterns in `RelationalTriplePattern`
  (`zanzibar_utils_v1.py`), 2026-07-16, behavior-preserving.** The `.subject` /
  `.object` `@property`s rebuilt a fresh frozen `EntityPattern` on every
  `match()` / `replace()` call (the write-path fan-out, `RuleSet.apply`). Now built
  ONCE at construction into two `field(init=False, repr=False, compare=False)` cache
  slots populated in `__post_init__` via `object.__setattr__`; the properties return
  the cached instances. `init=False` preserves the `__init__` signature, `repr=False`
  preserves the compiled-RuleSet snapshot bytes (the snapshot gate is `repr()` over
  the declared fields), `compare=False` preserves `eq`/`order`. Patterns are
  compile-time artifacts, never rebuilt per write, so the build cost is paid once and
  amortized. **Micro (`RuleSet.apply`, gdrive fixture, 20 reps × 600 triples, best of
  7, stable across 3 runs): 155 → 73.5 ms (2.1×, −53%).** A `cProfile` attributed
  ~20% of `apply` tottime to the two properties in isolation, but gdrive's TTU/union
  `replace` fan-out multiplies the per-apply `EntityPattern` builds, so eliminating
  them roughly halves the wall. demorgans flat (~12.5 ms — its derived-family path
  builds fewer patterns per apply). **End-to-end** graph write loop
  (closure/SQL-dominated, ~500 writes): 9704 → 9336 ms — not a regression (apply is a
  tiny fraction end-to-end, as the worklist predicted; the win is the micro).
  Verified snapshot bytes, `eq`, and pickle round-trip unchanged. Gated: snapshot
  (13), `test_matrix.py` + `test_lookup_oracle.py` + `test_boolean_compile.py` +
  `test_compile_snapshot.py` (93), schema/parse/compile/utils selector (136),
  `test_hypothesis.py` (generated-schema round-trips). **Lean: none** (below model —
  construction-caching, identical results).

- ✅ **Grab-bag micros (index_v4 minor notes), 2026-07-16, behavior-preserving.**
  Three independent small edits, each measured before landing:
  - **`_require_live_nodes` 2 point SELECTs → 1 `IN` (`index_v4/core.py`).** The
    liveness re-check on every `add_edge_by_id` / `remove_edge_by_id` SELECTed each
    endpoint separately; now one `select(NodeV4.id).where(id.in_(...))` covers both,
    unchanged error semantics (first missing id in call order raises), still
    **cache-blind by contract** (never the N15 node cache — it is a liveness probe).
    **`stmt_bench` (real ConnectedStore, sync, paranoia-off): union add node_v4
    SELECT 10.96 → 9.30, total 38.2 → 36.6; union remove 31.2 → 29.6; boolean add
    node_v4 46.66 → 39.90, total 137.7 → 130.9; boolean remove 119.8 → 113.6.** All
    I/U/D and other SELECT-table attributions byte-identical.
  - **`remove_node` neighbour-debit tail N+1 → 1 `IN` (`index_v4/core.py`).** The
    Blind-audit C1 tail applied per-neighbour refcount debits with one point SELECT
    per neighbour; now `_load_nodes(neighbours + [subject])` hoists them in one IN
    query, debits applied in Python (they differ per neighbour, so no single UPDATE)
    with the identical implicit-GC rule and N15 eviction. **When** debits apply is
    unchanged (still the tail, after the expansion loops emit their REMOVED deltas).
    Cold path (node GC), absent from `stmt_bench`'s op mix — verified with a
    `before_cursor_execute` scratch driving `remove_node` on an N-neighbour star:
    **node_v4 SELECTs during remove_node N+3 → flat 3; total statements 34 / 114 /
    414 / 814 (N = 10/50/200/400) → flat 14.**
  - **`_collect_residue_memberships` set/frozenset elimination + lazy `upos`
    (`index_v4/wildcard.py`).** The per-residue-row scan built a `frozenset` for a
    single `shape in …` test and wrapped `neg`/`upos` in `set()` for point
    membership; now the decoded JSON lists are probed directly (`want in
    json.loads(stars)`, `id in json.loads(neg)`), so `upos` decodes only on the
    branch that needs it. CPU-only (no statement change). **Isolated inner-loop A/B
    (800 synthetic rows, identical decisions asserted equal): steady-state 14.6 →
    11.2 ms/scan (−23%); diluted to ~2.5% end-to-end behind the SQL fetch + graph
    walk.**
  Gated: `test_matrix.py` (12), the index_v4 selector (wildcard/index/invariant/
  processor/bulk/connectedstore/matrix/lookup_oracle/blind_audit/remove_node/reads/
  self_referential, 287, paranoia inside), `test_hypothesis.py` (12) — all green.
  Stmt deltas in `STMT_BASELINE_2026-07-14.md` addendum 3. **Lean: none** (below
  model — SQL-shape / CPU micro-opts, no modeled-algorithm change).

- ✅ **N18 — stream the bulk builder's Phase-W writes + Phase-R snapshot read
  (`index_v4/bulk_build.py`), 2026-07-16, RAM ceiling, behavior-preserving
  (byte-identical rows in identical order).** RESHAPED from the original
  "chunk/stream the DP" plan by a 2026-07-16 tracemalloc probe: the Phase-P DP
  (`pvec`) holds only ~210 MB at gdrive/201.6k (closure linear: 100,548 /
  402,948 / 1,209,348 pairs at 16.8k / 67.2k / 201.6k tuples; 91% of vectors
  simultaneously live, so a release-when-consumed schedule reclaims ~9%) —
  phases R/B/C/P left logically untouched. The actual hogs were SQLAlchemy row
  staging: Phase W's `edge_rows` + `outbox_rows` per-row-dict lists (~3× the DP,
  ~700 MB at 200k) fed to single giant `session.execute(insert(...), rows)`
  calls; the Phase-R `.all()` snapshot holding ~200k ORM `TupleV1` objects for
  the whole build; and ~165k flushed `NodeV4` instances parked in the identity
  map. Now: Phase W builds + executes + frees edge/residue/outbox row dicts in
  bounded 50k-row chunks (slices of the sorted `edge_pairs` / `residues.items()`
  — same rows, same order, auto-increment ids assigned exactly as before);
  Phase R streams via `.execution_options(yield_per=10_000)` selecting only the
  six routed columns (no ORM entities); the `NodeV4` objects are expunged after
  the flush + `node_id` capture (the caller re-reads via fresh queries).
  **gdrive graph 201.6k tuples (`n18_followup_2026-07-16.jsonl`, M2 §6 Phase-B
  flags, ~2.87 GB free at start): peak RSS 3,512 → 1,117 MB (−68%, 3.14×);
  build 390.5 → 314.2 s under the cap (cross-session wall not comparable — the
  M2 baseline ran under heavier pressure; peak RSS is the headline, and the
  build no longer swaps). 67.2k sanity: peak 405 MB (round-3 curve: 925 MB
  @50.4k / 1,788 MB @100.8k). `answers_sig` byte-identical to the M2 follow-up
  gdrive value at both scales.** Gated: `tests/test_bulk_build.py` (6, the
  build-vs-incremental identity gate) + connectedstore suite + `test_matrix.py`
  (60 green). **Lean: none** (alternative constructor of the same modeled
  state, same rows — `CORRESPONDENCE.md §8.1` N18 entry).

- ✅ **N10 — defer flow-graph construction off read-triggered `rebuild()`
  (`setengine/engine.py`), 2026-07-16, lazy first-touch build, behavior-preserving.**
  `rebuild()` (and the constructor's replay) replayed every `TupleV1` row through
  `_apply_add` → `_derived_pairs` (the full `RuleSet.apply` rewrite fan-out) purely to
  populate `_flow_adj` / `_edge_count` — write-only cycle-detection state that reads
  NEVER consult; `refresh_evaluator` (rollback / tokened-read fallback) fires this and
  is often followed by reads only. Now `_flow_built` gates all flow work: replay skips
  the entire `_derived_pairs` fan-out, and a single `_ensure_flow_graph()` guard on the
  flow touch points (`_flow_reaches` reads + `_flow_add_edge` / `_flow_remove_edge`
  mutations) builds the complete graph on demand exactly once, before the first write's
  cycle check. Reconstructed from the engine's in-memory `node_sets` (which holds
  EXACTLY the stored septuples — the same completeness `_tuple_present` relies on to
  answer SELECT-free), so the lazy build needs no DB read; the edge multiset is
  byte-identical to the old per-row replay (`_flow_add_edge` is count-based /
  order-independent). Incremental `_apply_add` / `_apply_remove` maintenance is
  unchanged once built. **gdrive scale 4000 (67,200 tuples, set:roaring): `rebuild()`
  4.99 s → 1.26 s (~4.0×); the flow-graph fan-out was 74.8% of the eager rebuild
  wall.** A read-only reopen (constructor + 50 checks + 10 lookups + 10 reverses)
  never builds the flow graph (`_flow_built` stays False). Accept/reject parity
  (including the N17 §1.5 routed-star check, `test_reg9`) is unchanged — the graph is
  identical the moment any cycle check reads it. Gated: `test_matrix.py` (12),
  setengine/storage/engine/lookup_oracle (94), `test_hypothesis.py` (12). **Companion
  (integration, orchestrator-owned `formal/`):** the `test_conformance_remove.py`
  white-box `_fingerprint` reads `_edge_count` / `_flow_adj` directly and asserts a
  bare `rebuild()` reproduces them — a one-line adaptation (`eng._ensure_flow_graph()`
  before snapshotting, on both driven + rebuilt engines) keeps the exact same
  flow-graph-convergence assertion under lazy materialization. **Lean: none** (below
  model — write-only auxiliary state, no modeled-algorithm change).

- ✅ **N17 — set-engine `lookup`: O(store) sweep fully removed; O(reachable) walk on
  EVERY schema via wildcard-bridge seeding (`setengine/engine.py`), 2026-07-15,
  ALGORITHM CHANGE on candidate generation, oracle+fuzz-gated.** P1 left
  object-wildcard schemas on the exact O(store) `_lookup_sweep` (the M2 verdict's
  worst read surface: gdrive owc lookup 0.27/s @100k). N17 deletes the
  `_owc_needs_sweep` gate so the reverse walk runs everywhere, seeding the
  wildcard-covered concrete siblings the walk cannot reach on its own: on dequeuing
  a `(T,'*',·)` star node it enqueues `ids_of_shape[(T,r')]` + a star-parent×TTU
  cross (`member_of` of the star bare `T:*` crossed with `_ttu_map`), all
  `check`-confirmed. `_lookup_sweep` is kept only as the differential test
  reference. **Quick sanity (30-s inline timing, owc `[user,user:*]` schema, subject
  reaching 5 objects): walk stays flat while the old sweep collapses —
  N=2k 8,549/s vs 37.9/s (225×); N=10k 7,399/s vs 5.2/s (1,435×), the gap widening
  with N (O(reachable) vs O(store)).** Owc-free `simple` lookup unchanged (~5.4k/s
  flat at 2k/10k; it always walked — the added H3 star-bare fold is ~2 dict probes
  per visited node). **Scale bench (post-gate, `n17_scale_2026-07-15.jsonl`,
  gdrive set:roaring): lookup 222 / 221 / 224 / 207 /s at scale 250/1k/4k/10k
  (4.2k → 168k raw tuples) — FLAT, vs the sweep baselines 7.4 → 1.8 → 0.44/s over
  4.2k → 67k tuples (`scale_bench_2026-07-15.jsonl`): ~25× at 4.2k tuples,
  ~500× at 67k, ~1,000×+ extrapolated at 168k. `simple` control 13.2k/14.0k /s at
  16k/64k (baseline band 10.1k–16.6k); checks unchanged.** Also fixes THREE
  pre-existing set-engine bugs, all on star-tupleset (`[T, T:*]`) × TTU states no
  prior corpus built (full record `docs/spec-deviations.md` 2026-07-15):
  `_reverse_neighbors`'s H3 folded only the concrete bare parent, dropping the
  STAR bare parent (`T:*` tupleset parent → every instance is a parent, ttu_leaf
  ∀⇒∃; Commit-1); the walk seed skipped uninterned userset
  from-chain-star-identity subjects; and an accept/reject parity divergence — the
  set engine accepted same-type star parents the graph rejects as routed
  same-shape wildcard self-reference cycles (`_would_cycle` now runs the §1.5
  check over derived pairs; found by the seed-7 hypothesis sweep). Gated:
  `test_lookup_oracle.py` (new `owc_star_ttu` 4-backend corpus + 8 handwritten
  regressions, exact two-sided vs oracle), a new `test_owc_bridge_walk_vs_sweep`
  differential (walk covered-set == sweep covered-set, both `SetOps`, 4 seeds ×
  30-step walks), + `test_lookup_hypothesis.py` machine over the widened corpus set,
  + matrix/wildcard-property/blind-audit. **Lean: none** (forward `lookup` unmodeled;
  `CORRESPONDENCE.md §8.1` N17 entry).

- ✅ **`direct_expand` population copy (`engine.py:768`) — FIXED 2026-07-14.**
  Dropped the redundant `ops.new()` around the persistent population mask
  (`ops.new(ns.entities) & pop((rtype,'...'))`). Turned the reverse/expand direct
  path from O(population) to O(result). **End-to-end (simple reverse): PySets
  1,944 → 57,136/s at 100k — now flat across 1k–100k (29×); RoaringSets 27k →
  35k.** Behavior-preserving, so no Lean change (CLAUDE.md); gated by the full
  suite (**794 passed**).
  - **Not** dropped in the sibling `memberset._starpop` (star path): the
    `Population` callable there may return a bare iterable (the memberset tests
    pass plain tuples), so `ops.new()` is load-bearing as a normalizer, not just a
    copy. Removing it broke `test_memberset_algebra_homomorphism`. See target #1.

- ✅ **set-engine `lookup` — O(store) sweep → O(reachable) reverse walk (P1),
  2026-07-14** (was target #2), **HYBRID**. Reverse BFS (dual of `expand`):
  `_reverse_neighbors` propagates `member_of` fan-in + wildcard-sentinel coverage
  + `_object_deps` (Computed/TTU-tupleset) + `_ttu_map` (TTU from-chain), each
  candidate confirmed by the unchanged `check`. **Wildcard-free schemas get the
  flat O(reachable) walk: `simple` ~20,000/s at 64k tuples, flat (was ~3.4/s at
  100k — the −1.03 O(N) slope).** **Object-wildcard schemas keep the exact O(store)
  sweep** (`_lookup_sweep`): a subject granted `T:*` reaches every object whose
  stored tupleset parent is a concrete `T`, which the walk reaches only as the
  `(T,'*',rel)` node — a **hypothesis-deep completeness finding** (the initial
  walk-only version dropped it). So `gdrive`/`wildcards` (both declare object
  wildcards) are unchanged from baseline (still O(store)); no schema regresses.
  Gated by `test_lookup_oracle.py` (exact two-sided vs the oracle) + a 6-seed
  hypothesis sweep + full suite. Lean: forward `lookup` is an unmodeled surface —
  recorded in `CORRESPONDENCE.md §8.1`. A tighter fallback condition (only when an
  object-wildcard type is a TTU parent) would extend the walk to more schemas —
  landed as the P1 follow-up (see Applied below; round-3 record in
  `docs/history/perf-round3-2026-07.md`).

- ✅ **P9 — set-engine `restr` frozenset cache (`setengine/engine.py`),
  2026-07-14.** `direct_leaf` / `direct_expand` rebuilt `{(r.type, r.predicate,
  r.wildcard) for r in direct.restrictions}` on every call — 0.77s tottime /
  199k calls in the demorgans lookup profile. Now computed once per (frozen,
  lifetime-stable) `Direct` node, keyed by `id(direct)`, reused across both
  leaves; `rebuild()` never reparses the AST so no reset. Behavior-preserving
  (identical set content) — no Lean. Gated by the full suite (531 passed).

- ✅ **P3 — graph-index `_residue_state` per-reconcile memo (`index_v4/
  wildcard.py`, `processor.py`), 2026-07-14.** The same `(type, rel, name)`
  residue was re-fetched (node SELECT + residue SELECT + `json.loads`) many times
  within one reconcile (via `stars_fn`/`derived_check`/`member_stars`/leaf
  callbacks). A per-reconcile read cache on `WildcardIndex` (None outside a
  reconcile ⇒ read path unchanged) memoizes it; `_store_residue` invalidates the
  key it writes, so a post-write read of the object's own residue never sees the
  pre-write snapshot. Cache holds immutable snapshots; every read returns fresh
  mutable `neg`/`upos` sets. Behavior-preserving — no Lean. Gated by 531 passed
  **incl. the paranoia-mode invariant checker + delta-scoped verifier** (the real
  net for a residue-caching change).

- ✅ **P7 — graph-index `_emit` region-snapshot hoist (`index_v4/core.py`),
  2026-07-14.** `_emit` did two `session.get` calls per delta to denormalize
  endpoint identity — O(A×D) round trips per write over the closure region. Now a
  `{id: NodeV4}` snapshot of A∪D∪{subject,object} is loaded once (chunked `IN`)
  and threaded through `_add_indirect_edges_batch_unsafe` → `_emit`; a map miss
  falls back to `session.get`, endpoint identity fields are never mutated by
  edge/refcount updates, and the batch deletes no nodes, so emitted rows are
  byte-identical. (P7's GC-scan short-circuit was already present in
  `_gc_public_node` — no change needed there.) Behavior-preserving — no Lean.
  Gated by 531 passed.

- ✅ **P10 — `memberset._starpop` population copy (`setengine/memberset.py`,
  `setops.py`), 2026-07-14.** Added a copy-free `SetOps.update(acc, it)` primitive
  (in-place union accepting any iterable — `set.update` / `BitMap.update` both
  normalise bare tuples, generators, and peer sets) and rewrote `_starpop` from
  `acc |= ops.new(pop(shape))` to `ops.update(acc, pop(shape))`, dropping the
  redundant full-population copy per star shape. **Constant-factor, not asymptotic**
  (unlike its `direct_expand` twin): `_starpop` over a covered shape is inherently
  O(population). Isolated micro-bench (100k-id population, single shape): PySets
  6,518 → 3,467 µs/call (**1.88×**), RoaringSets 5.9 → 3.2 µs/call (**1.85×**);
  full `_ext` (tiny result / huge neg) 1.2–1.3×. Invisible on `scale_bench`
  demorgans-reverse (users capped at 250 ⇒ bounded star population — measured flat
  602 → 565/s from 17.7k to 86.8k tuples), so the uncapped micro-bench is the
  justification. Behavior-preserving (`ext` identical old==new) — no Lean. Gated by
  the full suite (531 + 263).

- ✅ **P6 — graph-index cascade outbox coalescing (`index_v4/processor.py`),
  2026-07-14.** P2's closure expansion emits O(ancestors×descendants) outbox rows;
  `_map_deltas_to_keys` redid the per-row work (a `subject_node` SELECT, a residue
  scan for GC'd subjects, and the whole dependent/tupleset/target fan-out) once per
  row. Rewrote it to run the object-level fan-out exactly **once per distinct
  `(o_type, o_name, o_pred)`** (that fan-out never depends on the subject) and to
  dedupe the `session.get(subject_node_id)` / `_node(subject)` lookups via per-call
  memos; only the leaf's own-key full/subject decision stays per-row. The function
  mutates no node/residue state (memo is exact) and `full`/`subject` merge
  order-independently and idempotently, so the coalesced key set is identical.
  Behavior-preserving (no modeled-algorithm change) — no Lean. Gated by 531 passed
  **incl. paranoia-mode invariant checker + delta verifier** + 263 conformance + a
  3-seed cascade/stateful-parity hypothesis sweep.

- ✅ **P13 — bulk closure builder for `build_index`
  (`index_v4/bulk_build.py`, `connectedstore/build.py`, 2026-07-15).**
  `build_index(..., bulk=True)` (default) constructs the pre-backfill state
  directly: route snapshot → natural-key direct multigraph → topo sort →
  sparse integer path-count DP (T4's closed form) → bulk INSERT of
  nodes/edges/outbox. Incremental loop retained as `bulk=False` (the identity
  gate's reference side; the online write path is untouched). **Measured:
  pure-union `build_index` 81.1 s → 1.67 s at 3.3k tuples and 407.8 s → 9.3 s
  at 16.9k (43.9–48.6×); boolean load phase isolated 127.9 s → 3.8 s at 3.0k
  (33.6×); boolean *total* build only 1.44× because the unchanged shared
  `backfill()` dominates it (next candidate).** Correctness: the differential
  identity gate (`tests/test_bulk_build.py`) builds the same snapshot both
  ways over 4 corpora — union+wildcards (both bridge directions), boolean
  (residues, version counts), De Morgan TTU, and a **multigraph fan-in corpus
  (direct multiplicity ≥ 2 + pure-indirect counts multiplied through an m=2
  edge — the dimension the first three corpora never reach)** — and asserts
  exact equality of the four id-independent canonical projections
  (nodes/edges/residues/outbox), plus I1–I13 invariant checker green and an
  oracle read-parity grid on the bulk stores. Lean: unchanged (alternative
  constructor of the same modeled state; logged in `CORRESPONDENCE.md §8.1`).
  Design doc: `docs/p13-bulk-build-design.md`.

- ✅ **R4-BF — bulk boolean backfill for `build_index`
  (`index_v4/bulk_backfill.py`, `index_v4/bulk_build.py`,
  `connectedstore/build.py`, 2026-07-15).** P13 bulk-built the pre-backfill
  closure but left the per-object `DeltaProcessor.backfill()` on the boolean
  build path, where it dominated the total (P13 boolean total was 1.44×). R4-BF
  computes the final derived state **in memory** during the same bulk build: a
  new Phase D mirrors `DeltaProcessor.backfill()`'s exact iteration (strata in
  order, relations in stratum order, `_live_keys_of` names sorted), **reusing
  the compiled plan closures** (`plan.check_fn`/`plan.stars_fn`) via a mirrored
  `_BulkEvalContext` implementing the same callback protocol as
  `processor._EvalContext` — the boolean expression logic is shared, only state
  access is mirrored. Within-stratum immediate visibility (bridge-on-intern) is
  reproduced by maintaining **reachability incrementally on every edge add**; a
  single final DP over the final direct multigraph recovers the path counts;
  the extended Phase W writes nodes/edges/residues/outbox in one pass.
  `connectedstore/build.py`'s bulk branch no longer calls `proc.backfill()`
  (the `bulk=False` branch keeps it, unchanged). **Measured (single-run,
  in-memory SQLite, `build_index(bulk=True)` total wall; before = pre-R4-BF
  HEAD where `backfill()` was 98.7–99.8% of the total): demorgans (5-level
  boolean+TTU cascade) 9.38 → 0.11 s at 188 tuples, 22.38 → 0.17 s at 330,
  75.22 → 0.41 s at 980, 163.36 → 0.81 s at 1950 (~201×) — the before-curve was
  strongly superlinear (~3.4× per scale-doubling), the after tracks the load
  phase ~linearly; boolean_wildcards (userset+TTU+exclusion) 8.04 → 0.14 s at
  390 tuples, 31.82 → 0.40 s at 1455, 70.69 → 1.18 s at 3051 (~60×).**
  Correctness: the differential identity gate (`tests/test_bulk_build.py`)
  extended from 4 to **6 corpora** — a new `derived_member` corpus
  (derived-userset leaf + sticky implicit→explicit public-node promotion under
  a raw userset subject over a derived relation), a new `demorgan1`
  (`demorgans_law_1`) corpus (derived-tupleset-ttu leaf + ≥3 boolean strata +
  edge-free explicit rc=0 residue-anchored node), and X4b upos-lift assertions
  on the existing `demorgan` corpus — each with anti-vacuity assertions that
  the design §5 features (a–e) are actually reached; both build paths still
  compared on the four id-independent canonical projections
  (nodes/edges/residues/outbox) + I1–I13 checker + oracle read-parity grid.
  Full gate green (split suite 513+24=537 passed; `verify.sh`
  lean/conf-heavy 68/conf-rest 195 all PASSED) + multi-seed fuzz sweep
  (`test_hypothesis.py`, `test_lookup_hypothesis.py`, seeds 7/19/31/53/71/97).
  `DeltaProcessor.backfill()` itself is unchanged (repair path + `bulk=False`
  reference side). Lean: unchanged (alternative constructor of the same modeled
  state; logged in `CORRESPONDENCE.md §8.1`). Design doc:
  `docs/r4bf-bulk-backfill-design.md`.

- ✅ **Wave 2 (round 3) — N6 + N7 + N9 + P1-follow-up, 2026-07-15.** Two parallel
  subagent tracks; integration gate green (531 passed split cap-safe 507+24 +
  `verify.sh lean`/`conf-heavy` 68/`conf-rest` 195). Statement counts vs the
  post-wave-1 run:
  - **N6 — graph lookup classify batch (`index_v4/wildcard.py`).** The K-result
    classify N+1 now batch-loads via `_load_nodes` (chunked `IN`, `_node_by_id`
    fallback on a map miss). **lookup 74.5 → 3.0 stmts/op (union), 134.8 → 5.0
    (boolean); lookup_reverse 14.3 → 2.9 / 14.4 → 4.8; ops/s 13 → 134 and
    9 → 78.** Behavior-preserving; forward lookup unmodeled (§8.1).
  - **N9 — trusted apply-path write (`wildcard.py` + `connectedstore/apply.py`).**
    `_apply_row` now uses `_add/_remove_tuple_trusted` (skips only
    `validate_write_identifiers`; provably always-passing there — admission
    validated the raw tuple, `RuleSet.apply` copies identifiers verbatim and
    rewrites only the relation to a charset-valid leaf predicate). Public API
    validates unchanged; sole external trusted caller is `_apply_row`
    (grep-verified). CPU constant, no stmt change.
  - **N7 — `_instances_of_type` per-eval memo (`setengine/engine.py`).** One
    O(interner) scan per type per evaluation (was per call); dead `query_names`
    param + unused var in `check` deleted (all call sites passed empty).
  - **P1 follow-up — tighter object-wildcard lookup fallback
    (`setengine/engine.py`), ALGORITHM CHANGE, fuzz-swept.** `_owc_needs_sweep`
    precomputed once: sweep only if some wildcard shape can bridge into a TTU
    **target** or a non-wildcard userset restriction over its Computed
    reverse-closure (the 2026-07-14 spec had the TTU end inverted and missed
    the userset bridge — corrected + recorded in
    `docs/history/perf-round3-2026-07.md`).
    Over-inclusive by design. Walk arm oracle-exact over ~1600 random states;
    strict `test_lookup_oracle.py` + 6-seed `test_lookup_hypothesis.py` sweep
    all green. github/boolean/demorgans now walk; wildcards/gdrive still sweep.

- ✅ **Wave 1 (round 3) — P12a + P12b + N4 + N5 + N8, 2026-07-14.** Landed as three
  parallel subagent tracks over disjoint files; full integration gate green (531
  passed + `verify.sh lean`/`conf-heavy`/`conf-rest` = 68+195 conformance).
  Statement-count after-numbers (re-run of `stmt_bench`, vs
  `STMT_BASELINE_2026-07-14.md`): pure-union add **50.6 → 46.2 stmts/write**,
  boolean add **221.2 → 206.7**; removes 43.0 → 38.8 / 187.2 → 173.8.
  - **P12a — transaction-scoped `_lock_store` memo (`index_v4/core.py`).**
    `SELECT…FOR UPDATE` re-takes per sync write: **4.32 → 1.00** (union),
    **14.52 → 1.00** (boolean). Memo keyed on the live `SessionTransaction`
    object's identity (fresh object per txn ⇒ structurally rollback-safe; repo
    has no savepoints). Behavior-preserving — no Lean.
  - **P12b — sync-gated log-row handoff (`connectedstore/`).** `log_rows`
    SELECT per sync write: **1.00 → 0.00**. The just-flushed `TupleLogV1` row is
    threaded to `advance_index(rows_hint=…)`, used only under the guard
    `cursor.applied_log_id == hint[0].id − 1` (+ contiguity), else exact
    fallback to `log_rows`. Single-slot pending buffer (bounded for direct
    `TupleSource` users). Below the model (row *source*, not content) — logged
    in `CORRESPONDENCE.md §8.1`.
  - **N4 + N8 — memberset `_ext`/`_normalize` copy elimination + read micros
    (`setengine/`).** Dropped ~6 defensive O(set) copies per algebra op (pos/neg
    are always `freeze()` outputs — verified at every construction site; both
    backends accept frozen operands in `-=`/`|=`/`&`). Micro-bench (indicative):
    union/intersect/subtract **−13…−29%** across both SetOps
    (`benchmarks/microbench_memberset.py`). Plus `itertools.chain` in the TTU
    walks and the small `ns.entities` copy drop in `direct_expand`.
  - **N5 — DB index audit (3 models files).** Dropped 13 write-only/redundant
    secondary indexes (TupleV1 ×6, NodeV4 ×4, EdgeV4 store_id+subject_id,
    ResidueV1 relation, IndexCursorV1 dup) — all grep-audited as covered by
    composite-unique prefixes/PK; added composite keyset indexes
    `edge_v4(store_id,object_id)`, `delta_outbox_v1(store_id,id)`,
    `tuple_log_v1(store_id,id)`. Biggest payoff on PostgreSQL/MySQL (SQLite
    understates index maintenance); InnoDB FK caveat documented on EdgeV4.

- ✅ **N3 — graph-index residue-scan elision (`index_v4/processor.py`),
  2026-07-14.** `_keys_referencing` / `_residue_references` scanned the whole
  `ResidueV1` table + JSON-decoded every row's neg/upos on every GC call in the
  cascade — but that scan is load-bearing ONLY for cross-object subject recordings
  (from-chain usersets X4a, lifted userset memberships X4), which arise solely from
  `derived-ttu` / `derived-tupleset-ttu` / `derived-userset` leaf kinds. A schema
  whose every leaf is `closure` or `derived-computed` records only edge-justified,
  same-object ids (already covered by the `reference_count` guards in the GC paths
  and the fully-deleted-subject precondition on the delta-map scan), so the scan is
  provably empty. Precompute a one-shot flag from `compiled.plans` (WHITELIST of the
  two safe kinds — any unrecognized/future kind auto-disables the elision, so GC
  correctness never rests on enumerating dangerous kinds) and short-circuit to `[]`.
  Real win on pure-boolean (and/but-not over direct+computed) schemas; TTU/userset
  schemas (e.g. demorgans) keep the scan. Behavior-preserving — no Lean. Gated as P6.

- ✅ **N16 — graph-index bulk-INSERT of outbox emit rows (`index_v4/core.py`),
  2026-07-15.** `_emit` `session.add`-ed one `DeltaOutboxV1` per reachability flip
  and the ORM unit-of-work flushed them **one INSERT statement per row** (verified
  by echo probe, SQLAlchemy 2.0.51). Now `_emit` stages a plain dict (endpoint-
  identity capture unchanged — still eager, while the nodes are alive) and
  `_flush_outbox()` drains the buffer in ONE `session.execute(insert(DeltaOutboxV1),
  rows)` at the end of `_add_direct_edge_unsafe` — the sole emit driver, during
  which nothing reads the outbox, so every reader (cascade frontier drain,
  `outbox_watermark`, paranoia §8.3 verifier) still sees a fully materialized
  stream and ids stay monotone in emission order (empirically verified on SQLite;
  Postgres: single insertmanyvalues statement, ids ascend in list order; no
  RETURNING consumed — same pattern as `bulk_build.py`). A `finally` leak guard
  drops the buffer on error paths (the caller's contract is rollback, matching the
  old pending-`add` semantics). **stmt_bench INSERTs/op: union add 20.4 → 13.0
  (−36%), union remove 9.2 → 2.2 (−76%), boolean add 40.8 → 28.5 (−30%), boolean
  remove 19.1 → 7.2 (−62%); union add total 46.2 → 38.9/op.** All other statement
  counts byte-identical. Edge-row batching DESCOPED: new `EdgeV4` ORM instances are
  read-modify-written and deleted through the identity map within the same op, so
  Core-inserting them would require restaging the P2 ref-count batch — high risk,
  small marginal win. Behavior-preserving — no Lean. Gated: full `tests/` (537
  passed incl. paranoia) + conf-heavy (68) + conf-rest (195).

- ✅ **N15 — per-batch node-resolution cache (`index_v4/core.py`, `processor.py`,
  `connectedstore/apply.py`), 2026-07-15.** The same subject/object/bridge/leaf
  nodes were re-resolved by point SELECT dozens of times within one
  `advance_index` batch / cascade (probe attribution: boolean 103.4 node_v4
  SELECTs/write — `check`→`_get_concrete` 19.0, processor `_node` ~18.7,
  `_resolve`→`node()` 12.8, plus residue/`_write_derived` probes). Now a
  per-batch `(predicate, type, name, wildcard) → NodeV4 | MISSING` cache on
  `ReachabilityIndex`, `None` outside a batch (uninstalled ⇒ byte-identical
  pre-N15 behavior), installed by a REENTRANT scope at two seams:
  `advance_index` (apply loop + cascade) and `run_cascade` (standalone — the
  test-matrix GraphBackend path, so paranoia/I9 exercise the cache). All
  resolution funnels through `node()` / `cached_concrete_node()` (the wildcard
  façade's `_resolve`/`_w_node`/`_get_concrete` all delegate to `node()`).
  **Negative caching included** — honest because the FIVE NodeV4 delete sites
  evict (→MISSING) and the sole creation choke point (`node()`) overwrites.
  Identity-tuple keys (not ids) — the blind-audit W2 hazards (cross-session
  staleness, rowid reuse) don't apply to a within-txn cache torn down before
  commit; the paranoia checker (`before_commit`) always reads cache-blind
  state. `_require_live_nodes` and `invariants.py` deliberately uncached.
  **stmt_bench node_v4 SELECTs/write: boolean add 103.4 → 46.7 (−55%), boolean
  totals 194.4 → 137.7/op (−29%), remove 161.9 → 119.8 (−26%); union add
  11.6 → 11.0** (union's residual redundancy is id-based — refcount tail,
  `_load_nodes` — deliberately not cached). I/U/D counts byte-identical.
  Behavior-preserving — no Lean. Gated: full `tests/` (537 passed incl.
  paranoia + delta verifier) + conf-heavy (68) + conf-rest (195).

## Optimization targets (ranked)

*(Rounds 1–3 landed — see Applied above; the retired round-3 worklist/execution
record is `docs/history/perf-round3-2026-07.md`. The living **open** worklist
(wave-3 conditionals, round-4 candidates, the P12c fence) is
[`docs/perf-next-round.md`](../../docs/perf-next-round.md).)*

1. **`memberset._starpop` population copy (`memberset.py:87`).** Same O(population)
   copy, but on the *star* path (star-heavy workloads: wide/demorgans). Can't just
   drop `ops.new()` (contract: `pop` may yield a bare iterable). Needs a `SetOps`
   bulk-union primitive that accepts an iterable without a full intermediate copy,
   or an engine-level guarantee that `pop` returns an ops set. Medium risk. (P10.)
2. **graph write path** (closure materialization + boolean `backfill()`), 15–156
   writes/s — the only thing blocking graph numbers at scale. *(P2 landed the
   closure-region batching, P7 hoisted the per-emit node fetches, both 2026-07-14;
   the boolean cascade coalescing — P6 — remains.)*
3. check and reverse (roaring) are already O(1) and fast — low leverage.

## Notes

- Single session, `paranoia=False`, in-memory SQLite. Run-to-run variance ≈ ±10%
  (set) / ±15% (low-throughput graph reads); the 14× reverse gap and the O(N)
  lookup slope are far outside that band, i.e. real.
- `analyze.py` is dependency-free (reproducible anywhere); `plot_curves.py` needs
  matplotlib (`benchmarks/requirements-analysis.txt`). numpy was **not** required —
  the fits are hand-rolled log-log least squares.

---

> **Round-3 after-numbers + graph-at-scale crossover (2026-07-15):**
> [`ROUND3_COMPARISON_2026-07-15.md`](ROUND3_COMPARISON_2026-07-15.md). Re-runs this
> baseline (→ `scale_bench_2026-07-15.jsonl`) and adds the P13-bulk graph curves at
> 10⁴–10⁵ tuples vs the set engine (→ `graph_scale_2026-07-15.jsonl`). Headline: set
> `lookup` O(N)→O(1) on wildcard-free schemas (up to ~3000×), PySets `reverse`
> O(N^0.7)→O(1) (16× at 100 k), write ~1.6× (N5). Crossover: after P1 the graph index's
> only read-side win is forward `lookup` on **object-wildcard** schemas at scale
> (gdrive 100 k: graph flat ~150/s vs set 0.27/s); the set engine dominates everywhere
> else. (Re-run captured under memory pressure — read its session caveat first.)
