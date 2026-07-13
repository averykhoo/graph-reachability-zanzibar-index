# Perf optimization handoff — ranked worklist (2026-07-14)

Master ranked list of performance-optimization opportunities across all three
layers (set engine · graph index · composition/schema). Supersedes the ad-hoc
"Optimization targets" list in
[`benchmarks/results/PERF_ANALYSIS.md`](../benchmarks/results/PERF_ANALYSIS.md)
as the *planning* doc; PERF_ANALYSIS stays the measured-baseline record. The
lookup reverse-walk item keeps its own full design in
[`docs/lookup-reverse-walk-plan.md`](lookup-reverse-walk-plan.md).

**How this was produced.** Two read-only survey agents (index_v4;
connectedstore+zanzibar_utils) plus direct cProfile of the set-engine write and
lookup paths (`simple` N=4000, `gdrive` N=500, `demorgans` N=300). "Measured"
items have profile/bench numbers; "hypothesized" items are code-read only and
need a measurement before/after.

**Reading the Lean column.** Per CLAUDE.md "Perf work & the Lean model": a
behavior-preserving micro-opt needs no Lean change (differential matrix +
hypothesis + conformance are the net). An optimization that *changes the modeled
algorithm* must update the corresponding Lean def and re-run `formal/verify.sh`,
or log the gap in `formal/CORRESPONDENCE.md §7`.

**The gate for every item:** `pytest -q` (~11 min, expect 794+ passed), plus the
targeted oracle gate for the surface touched (`tests/test_lookup_oracle.py` for
lookup/expand; `tests/test_matrix.py` for check/write parity). Never edit a
golden/oracle result to make an opt pass.

**Landed 2026-07-14** (commits `1d60d2b`, `bc20398`, `41fe499`, `75fa0d4`;
pushed on master, full suite 794 passed + verify.sh all-green): **P0, P2, P5,
P8**. Integration lesson recorded inline on each. Still open: P1 (has its own
plan doc), P3, P4, P6, P7, P9–P12.

---

## Tier 0 — do first: biggest win, lowest risk, fully independent

### P0. Set-engine writes: drop the per-write `_row` duplicate-check SELECT ✅ LANDED
> **Done** (`1d60d2b` + fix `75fa0d4`). Measured ~5.9× set-engine build speedup
> (35.8s→6.1s on 16k tuples). **Integration gotcha:** the removed `_row` SELECT
> was *implicitly autoflushing* pending ops per add; without it, an uncommitted
> add→remove→re-add of the same septuple leaves INSERT+DELETE pending on one
> unique key and SQLAlchemy orders INSERT-before-DELETE → `tuple_v1` UNIQUE
> violation. Caught by `formal/conformance/test_conformance_remove.py` in the
> **full** suite — NOT by the subagent's targeted `test_matrix`+hypothesis gate.
> Fixed with a `session.flush()` in `remove_tuple`. Lesson: run the full suite at
> integration; targeted gates miss uncommitted-churn interactions.
- **Where:** `setengine/engine.py:289` (`add_tuple`) → `:313` (`_row`), and the
  mirror in `remove_tuple` (`:307`).
- **What:** every `add_tuple` issues a 7-column equality `SELECT` against
  `TupleV1` purely to detect the idempotent duplicate. The in-memory state
  (`interner` + `node_sets`) is already authoritative and already answers "does
  this tuple exist" exactly: the tuple is present iff `subject_id` and
  `object_id` are interned **and** `subject_id ∈ node_sets[object_id].entities`
  (bare) / `.usersets` (userset). `node_sets` membership is populated *only* by
  real `_apply_add`s (never by the reverse-dependency candidate interning), so
  the test is precise, not an over-approximation.
- **Measured:** `_row` is **cumtime 25.4 s of 35.8 s (≈71%)** of set-engine build
  for `simple` N=4000, and 13.8 s of 20.1 s for `gdrive` N=500. The cost is not
  SQLite (`execute` ≈ 0.95 s) — it's SQLAlchemy *rebuilding the query* 16 000×
  (`_gen_cache_key`, `coercions.expect`, `_init_compiled`). Eliminating it should
  roughly **2–3× set-engine write throughput** (the remaining big chunk is ORM
  `TupleV1` construction in `session.add`, a separate item).
- **Fix:** replace the `_row(...) is not None` idempotency probe in `add_tuple`
  with the in-memory membership test; in `remove_tuple`, check in-memory
  existence first and only hit the DB `_row` fetch (still needed for
  `session.delete(row)`) when the tuple is present. Keep validation ordering
  (raise before any mutation) intact.
- **Lean:** none — write semantics are unchanged; the check is against the same
  authoritative state, just read from memory instead of the DB mirror.
- **Risk:** Low. The one invariant to preserve: in-memory state mirrors the store
  (it does — `rebuild()` replays the table). Gate on the full matrix + hypothesis
  add/remove-restoration tests, which already assert exactly this mirror.
- **Independent:** yes — touches only `setengine/engine.py` write methods.

---

## Tier 1 — large structural wins (algorithm changes → Lean work)

### P1. Set-engine `lookup`: O(store) sweep → O(reachable) reverse walk
- **Where:** `setengine/engine.py:825` (`lookup`). Full design +
  implementation checklist already written:
  [`docs/lookup-reverse-walk-plan.md`](lookup-reverse-walk-plan.md).
- **What:** `lookup` calls `check` once per interned key — a full-store candidate
  sweep. Replace with an on-the-fly reverse BFS from the subject (dual of
  `expand`), reusing `member_of` + `_candidate_reverse_deps`. **NOT** a
  materialized per-subject index (that moves cost to writes, defeating the set
  engine).
- **Measured:** lookup slope **−1.03 @ R²=1.000** (O(N)); profile confirms lookup
  is ~100% the `check` sweep (160 040 `check` calls for 40 `simple` lookups ≈
  4001 checks/lookup at N=4000). `check`/`reverse` stay flat. This is the largest
  read-surface structural inefficiency.
- **Lean:** **required** — changes the modeled `lookup` algorithm. Update the Lean
  `lookup` def or log in `CORRESPONDENCE.md §7`.
- **Risk:** Medium — over-approximation must never *miss* a candidate (X1-class
  silent drop). `tests/test_lookup_oracle.py` is the gate.
- **Independent:** yes — self-contained in `setengine/engine.py` + the Lean
  `lookup` model. Can run concurrently with P0 (different methods, same file — mind
  the merge) and all graph-index items (different module).

### P2. Graph-index writes: batch the O(A×D) closure region SELECT/UPSERT ✅ LANDED
> **Done** (`41fe499`). Batched the indirect-closure region into one chunked
> row-value `IN` SELECT + in-memory increments + one flush (`_add_indirect_edges_batch_unsafe`);
> the direct edge stays a single-pair call to preserve subtract-first/add-last
> ordering. Lean: **logged observational equivalence** in `CORRESPONDENCE.md §8.1`
> (zero `.lean` files changed — the batch applies the identical per-pair
> arithmetic, so final edge state + per-pair outbox actions are unchanged).
> verify.sh green.
- **Where:** `index_v4/core.py:208-216` (expansion loops) → `:78-84`
  (`_add_db_edges_unsafe`, one point `SELECT` per pair).
- **What:** a single edge add grows the closure by ≈`(|ancestors|+1)×(|descendants|+1)`
  ref-counted rows, and **each pair is its own SELECT + INSERT/UPDATE round-trip**
  (classic N+1). This is the dominant reason graph writes are **15–156 writes/s** —
  the slowest surface in the whole system. Batch: gather all `(from,to,delta)`
  triples, one `SELECT … WHERE (subject_id,object_id) IN (:pairs)` to load the
  region, apply increments in memory, one bulk insert + one bulk update.
- **Lean:** **likely required** — changes the modeled closure-update procedure and
  delta-emission ordering. Must preserve subtraction-before / addition-after /
  direct-edge-last ordering and the *final* per-pair outbox action
  (`verify_outbox_deltas` + cascade key off it), and delete-when-both-zero.
- **Risk:** Medium. `tests/test_matrix.py` (4-way, I9-audited) + paranoia verifier
  are the gate.
- **Independent:** yes (graph-index only) — but **downstream items P6/P7 depend on
  its row-count**, so land P2 first if doing the graph write path as a unit.

---

## Tier 2 — behavior-preserving micro-opts (no Lean; safe, parallelizable)

### P3. Graph index: memoize `_residue_state` per reconcile
- **Where:** `index_v4/wildcard.py:381-396` (`_residue_state`), re-entered many
  times per `reconcile` (`processor.py` `stars_fn`, `derived_check`,
  `member_stars`, `_derived_leaf_neg_ids`, leaf callbacks).
- **What:** the same `(type, rel, name)` residue is re-fetched (node SELECT +
  residue SELECT) and re-`json.loads`'d (`stars`/`neg`/`upos`) on every access
  within one reconcile. Cache it on the `_EvalContext` (one context = one
  (store,object) per reconcile), invalidated when the reconcile writes its own
  residue at the end.
- **Lean:** none (pure read caching). **Risk:** Low-Medium (must not serve stale
  residue across the reconcile's own write). **Independent:** yes.

### P4. Graph index: batch the N+1 `session.get(NodeV4, id)` loops
- **Where:** `index_v4/processor.py:237-241` (`stored_userset_subjects`),
  `:252-257` (`tupleset_parents`), `:344-348`
  (`_stored_parent_objects_of_entity`), `:468`/`:519` (reconcile passes),
  `:315-328` (`_ttu_target_upos_nodes`).
- **What:** each enumerates edges, then fetches endpoints one id at a time.
  Replace with a single `WHERE id IN (:ids)` batch — `_incoming_concretes`
  (`processor.py:211-220`) already shows the pattern.
- **Lean:** none. **Risk:** Low (preserve per-row filter predicates).
  **Independent:** yes.

### P5. Shared `RuleSet.apply`: fast-path the trivial single-match fan-out ✅ LANDED
> **Done** (`bc20398`). Fast-path yields `seeds` directly when the seed relation
> has no rule candidates; drains in place otherwise. Snapshot byte-identity gate
> (`test_compile_snapshot.py`) green.
- **Where:** `zanzibar_utils_v1.py:322-371`.
- **What:** called ≥1× per raw write in **both** backends (`engine.py:418`
  `_derived_pairs`; `connectedstore/apply.py`). On the dominant case (a `[user]`
  direct restriction, one filter match, no further rewrite) it still allocates
  `seeds`, `unprocessed = set(seeds)`, `processed = set()` and runs a worklist for
  a one-element result. Reuse `seeds` directly; short-circuit when the seed
  relation has no rule candidates.
- **Lean:** none (output identical). **Risk:** Low — but `apply` feeds both
  backends + oracle, so run the parity matrix. **Independent:** yes (schema
  layer; touches neither backend's state).

### P6. Graph index: coalesce cascade outbox rows before per-row work
- **Where:** `index_v4/processor.py:715-789` (`_map_deltas_to_keys`).
- **What:** P2's expansion emits O(A×D) outbox rows; the cascade then does a
  `self._node(...)` SELECT + dependent/tupleset/target fan-out **per row**, once
  per stratum round. Coalesce by `(object_node_id, subject_shape)` first (many
  rows collapse to the same derived key); memoize `_node` + fan-out. Downstream
  of P2 — shrinking emitted rows at the source (P2) also shrinks this.
- **Lean:** coalescing that preserves the final key set is behavior-preserving;
  changing fan-out semantics is not. **Risk:** Medium (preserve full-object vs
  per-subject decision, `:746-757`). **Independent:** overlaps P2/processor.

### P7. Graph index: guard the GC full-residue scan; `_emit` node fetches
- **Where:** `index_v4/processor.py:284-291` (`_keys_referencing` — full
  ResidueV1 scan + JSON decode on every changing reconcile, via `_gc_public_node`)
  and `index_v4/core.py:36-37` (`_emit` fetches both endpoint nodes per emitted
  delta, O(A×D)× per write).
- **What:** short-circuit the residue scan before loading rows when the node isn't
  actually empty; hoist a `{id: node}` map for the A∪D∪{subj,obj} region once and
  pass names into `_emit` instead of re-`get`-ting.
- **Lean:** none (the guard/hoist are behavior-preserving). A real fix for the GC
  scan (normalize `neg`/`upos` into an indexed child table) is a schema change and
  *would* touch Lean — separate, larger item. **Risk:** Low for the guard/hoist.

### P8. Composition: kill the redundant bootstrap double-parse; guard union `outbox_watermark` ✅ LANDED
> **Done** (`bc20398`). Bootstrap now compiles once (`save_schema`/`ensure_schema`
> return the compiled `RuleSet`, threaded into `open_graph_index` via `ruleset=`);
> union stores skip the unused per-batch `outbox_watermark` SELECT.
- **Where:** `connectedstore/schema_io.py:43` (throwaway `parse_openfga_schema`
  whose result is discarded, then `:95` re-parses the same text) and
  `connectedstore/apply.py:96` (`outbox_watermark` read unconditionally even when
  `proc is None`, i.e. pure-union schemas that never use it).
- **What:** first-time bootstrap compiles the schema twice; union stores pay an
  extra SELECT per apply batch for an unused value. Reuse/skip the throwaway
  parse; guard the watermark read behind `if proc is not None:`.
- **Lean:** none. **Risk:** Very low. **Independent:** yes.

---

## Tier 3 — smaller / conditional / needs-a-measurement-first

### P9. Set-engine hot leaf: precompute static `restr` frozensets
- **Where:** `setengine/engine.py:595` (`direct_leaf`) and `:754`
  (`direct_expand`) both rebuild `restr = {(r.type, r.predicate, r.wildcard) …}`
  on every leaf evaluation. It's static per `Direct` AST node.
- **What:** compute once (cache on the AST node / a side dict keyed by node id) and
  reuse. Hot: `direct_leaf` is 0.77 s tottime / 199 k calls in the demorgans
  lookup profile. **Lean:** none. **Risk:** Low. Small constant-factor win;
  pairs naturally with P1 (same file). Measure before/after.

### P10. `memberset._starpop` star-path population copy
- **Where:** `setengine/memberset.py:84-92` (`_starpop`), the twin of the already-
  fixed `direct_expand` copy (commit `78cfc2f`).
- **What:** `acc |= ops.new(pop(shape))` copies the whole O(population) mask per
  star shape. Can't just drop `ops.new()` — the `Population` contract only
  promises an iterable (memberset tests pass bare tuples), so it's load-bearing as
  a normalizer. Needs a `SetOps` bulk-union primitive that accepts an iterable
  without a full intermediate copy, **or** an engine-level guarantee that `pop`
  returns an ops set. **Lean:** none if behavior-preserving. **Risk:** Medium
  (the `test_memberset_algebra_homomorphism` contract). Only bites star-heavy
  workloads (wide/demorgans reverse) — measure it's real at scale first.

### P11. Composition: cache compiled `RuleSet` across store opens
- **Where:** no memoization on `parse_openfga_schema` / `compile_ruleset`
  (`connectedstore/schema_io.py:95`, `store.py:66`). Every `ConnectedStore` reopen
  recompiles from scratch (`compute_taint` O(rel²), `_expand_object_wildcard_shapes`
  O(rules²) fixpoints). Only matters **if the deployment opens a store
  per-request** — otherwise once-per-open is fine. `RuleSet` is mutable/stateful
  (lazy `_build_dispatch`, closures in `compiled.plans`), so caching the whole
  instance across sessions needs care; caching the AST/`SchemaInfo` is safer.
  **Lean:** none. **Risk:** Medium (shared mutable state across sessions/threads).
  **Conditional** — confirm the open pattern before investing.

### P12. Composition (do NOT casually touch): sync per-write DB round-trips; rebuild-from-truth
- `connectedstore/apply.py:90-100` — sync writes pay ~4-6 DB round-trips each
  (`_lock_store` FOR UPDATE, `refresh(cursor)`, `log_rows`, `outbox_watermark`).
  Largest raw composition win, but entangled with the exactly-once/serialization
  story the Lean model encodes; any change must be **gated on `sync=True`** and
  preserve serialization. **Algorithm/coupling change → Lean.**
- `connectedstore/source.py:124` / `setengine/engine.py:256` — `rebuild()` is a
  full O(N) tuple-log replay on every write-failure/rollback and tokened-read
  fallback. Incremental catch-up would touch the evaluator-freshness watermark
  contract (Lean). It's a deliberate correctness backstop — **document the cost,
  don't casually change.**

### Ruled out by measurement
- **`_instances_of_type` O(store) scan** (`engine.py:529`) — hypothesized as a
  demorgans lookup bottleneck; **not confirmed**: it does not appear in the
  demorgans lookup profile top-18 (the star `∀⇒∃` path is hit far less than
  expected at these scales). Lookup cost there is the same O(store) `check` sweep
  P1 fixes. Leave it; revisit only if a star-∀-heavy schema surfaces it.

---

## Suggested parallelization (for the opus-subagent plan)

Fully independent, safe to run concurrently (distinct files/modules, no shared
state, each self-gates on the suite):

| Track | Items | Files | Lean? |
|---|---|---|---|
| **A — set engine** | P0, then P1, P9 | `setengine/engine.py` (+ Lean `lookup` for P1) | P1 only |
| **B — graph write** | P2 → P6/P7 | `index_v4/core.py`, `processor.py` | P2 (likely) |
| **C — graph reconcile reads** | P3, P4 | `index_v4/wildcard.py`, `processor.py` | none |
| **D — schema/composition** | P5, P8 | `zanzibar_utils_v1.py`, `connectedstore/*` | none |

Caveats for the fan-out:
- **A is serial internally** (P0/P1/P9 all touch `engine.py`) — one agent, not three.
- **B and C both touch `processor.py`** (P4/P6/P7 vs P3) — run B and C as **one
  graph-index agent** or accept a merge, don't fan them into conflicting worktrees.
- **D is genuinely independent** of A/B/C.
- Recommended first parallel batch: **A (just P0)** ‖ **B (P2)** ‖ **D (P5+P8)** —
  three non-conflicting tracks, the three biggest measured/structural wins, P0 and
  D behavior-preserving, P2 the graph headline. Then reconvene before the Lean-
  touching P1/P2 model updates.
- **Measurement hygiene (from the prior session):** never run two bench/pytest
  processes at once (CPU-contention corruption); the baseline `scale_bench.jsonl`
  + `perf_curves.png` are the pre-optimization snapshot — record after-numbers in
  PERF_ANALYSIS.md, don't overwrite the jsonl.
