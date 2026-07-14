# Perf optimization — next-round worklist (opened 2026-07-14)

The living list of **remaining** performance opportunities. Supersedes the retired
`perf-optimization-handoff.md` (2026-07-14) and `lookup-reverse-walk-plan.md`
(P1 landed) as the planning doc. Measured-baseline record stays
[`benchmarks/results/PERF_ANALYSIS.md`](../benchmarks/results/PERF_ANALYSIS.md);
cap-safe gate recipe stays [`docs/gate-runbook.md`](gate-runbook.md).

**Landed so far (git log is the audit trail):** P0, P1 (lookup reverse walk,
hybrid), P2, P3, P4, P5, P6, P7, P8, P9, P10, N3. See `PERF_ANALYSIS.md`
"Applied" for the per-item numbers/mechanism. **P11 struck** (2026-07-14): the
deployment reuses one `ConnectedStore` instance rather than opening one
per-request, so caching the compiled `RuleSet` across opens has no value — the
schema is static (a new schema means a new store) and compilation already happens
once per store. **N1/N2 measured and skipped** (2026-07-14): profiling showed
neither is hot — N1's evaluation-scoped memo target has 0 redundant `_object_ids`
calls (`sat`/`do` already memoize per key), and N2's restr bool test is <1% of the
lookup profile (the traversal machinery dominates). Left for a future round only if
the hot path shifts.

**Reading the Lean column.** Per CLAUDE.md "Perf work & the Lean model": a
behavior-preserving micro-opt needs no Lean change (differential matrix +
hypothesis + conformance are the net). An optimization that *changes the modeled
algorithm* must update the corresponding Lean def and re-run `formal/verify.sh`,
or log the gap in `formal/CORRESPONDENCE.md §7`. Everything landed this session
was behavior-preserving except P1 (forward `lookup` is an unmodeled surface —
recorded in `CORRESPONDENCE.md §8.1`), so no proof work has been needed.
**Fable is only warranted if a future item requires producing a genuine Lean
proof** (e.g. deliberately modeling forward `lookup` and proving the reverse
walk ≡ the sweep, or touching P12's serialization story); Opus subagents can
carry every item currently on this list end-to-end.

**The gate for every item:** `pytest tests/ -q` (~5.5 min, 531 passed) + the
targeted oracle gate for the surface touched (`tests/test_lookup_oracle.py` for
lookup/expand; `tests/test_matrix.py` for check/write parity), then
`formal/conformance/`. Never edit a golden/oracle result to make an opt pass.

---

## Deferred from this round (with reasons — not silently dropped)

### P6. Graph index: coalesce cascade outbox rows before per-row work — ✅ LANDED 2026-07-14
- **Where:** `index_v4/processor.py` `_map_deltas_to_keys` (~L715–789).
- **What:** P2's expansion emits O(A×D) outbox rows; the cascade then does a
  `self._node(...)` SELECT + dependent/tupleset/target fan-out **per row**, once
  per stratum round. Coalesce by `(object_node_id, subject_shape)` first (many
  rows collapse to the same derived key); memoize `_node` + fan-out.
- **Why deferred:** Medium risk (must preserve the full-object vs per-subject
  decision, ~L746–757), and it **overlaps the P2/P7 processor path** — wants its
  own focused agent + full matrix, not folded into an unrelated track.
- **Lean:** coalescing that preserves the final key set is behavior-preserving;
  changing fan-out semantics is not.

### P10. `memberset._starpop` star-path population copy — ✅ LANDED 2026-07-14
- **Where:** `setengine/memberset.py` `_starpop` (~L84–92).
- **What:** the twin of the already-fixed `direct_expand` copy (`78cfc2f`).
  `acc |= ops.new(pop(shape))` copies the whole O(population) mask per star shape.
- **Why deferred:** **needs a scale measurement first** — only bites star-heavy
  workloads (wide/demorgans reverse). Can't just drop `ops.new()`: the
  `Population` contract only promises an iterable (memberset tests pass bare
  tuples), so it's load-bearing as a normalizer (removing it broke
  `test_memberset_algebra_homomorphism`). The real fix is a `SetOps` bulk-union
  primitive that accepts an iterable without a full intermediate copy, **or** an
  engine-level guarantee that `pop` returns an ops set. Medium risk.
- **Lean:** none if behavior-preserving.

### P11. Composition: cache compiled `RuleSet` across store opens — ✂ STRUCK 2026-07-14 (store is reused, not per-request)
- **Where:** no memoization on `parse_openfga_schema` / `compile_ruleset`
  (`connectedstore/schema_io.py`, `store.py`). Every `ConnectedStore` reopen
  recompiles (`compute_taint` O(rel²), `_expand_object_wildcard_shapes` O(rules²)).
- **Why deferred:** **conditional** — only matters if the deployment opens a store
  per-request; confirm the open pattern before investing. `RuleSet` is
  mutable/stateful (lazy `_build_dispatch`, closures in `compiled.plans`), so
  caching the whole instance across sessions needs care; caching the
  AST/`SchemaInfo` is safer. Medium risk (shared mutable state across threads).
- **Lean:** none.

### P12. Composition (do NOT casually touch): sync round-trips; rebuild-from-truth
- `connectedstore/apply.py` — sync writes pay ~4–6 DB round-trips each
  (`_lock_store` FOR UPDATE, `refresh`, `log_rows`, `outbox_watermark`). Largest
  raw composition win, but entangled with the exactly-once/serialization story the
  Lean model encodes; any change must be **gated on `sync=True`** and preserve
  serialization. **Algorithm/coupling change → Lean (fable territory).**
- `connectedstore/source.py` / `setengine/engine.py` `rebuild()` — full O(N)
  tuple-log replay on every write-failure/rollback and tokened-read fallback.
  Incremental catch-up would touch the evaluator-freshness watermark contract
  (Lean). Deliberate correctness backstop — **document the cost, don't casually
  change.**

### P1 follow-up: tighter object-wildcard `lookup` fallback
- **Where:** `setengine/engine.py` `lookup` / `_lookup_sweep`.
- **What:** object-wildcard schemas currently fall back to the exact O(store)
  sweep for *any* wildcard shape. A tighter condition — fall back **only when an
  object-wildcard type is actually a TTU parent** (the one case the reverse walk
  can't bridge, per `CORRESPONDENCE.md §8.1`) — would extend the O(reachable)
  walk to more object-wildcard schemas (e.g. wildcards used only as direct grants).
- **Lean:** none new (forward `lookup` stays unmodeled; §8.1 already covers it).
  **Gate:** `test_lookup_oracle.py` + a hypothesis-deep sweep (this is the surface
  that shipped the object-wildcard×TTU bug — see gate-runbook).

---

## New scopes surfaced 2026-07-14 (found while landing P3/P7/P9)

### N1. Set engine: share the per-leaf `nodes` list / `_object_ids` interning
- **Where:** `setengine/engine.py` `direct_leaf` / `direct_expand`.
- **What:** both recompute `nodes = [self.node_sets[i] for i in
  self._object_ids(ot, on, rel) if i in self.node_sets]` per call. When a leaf is
  invoked repeatedly for the same `(ot, on, rel)` within one evaluation, the
  `_object_ids` interning + list rebuild is repeated work that could be
  shared/short-circuited (evaluation-scoped memo, like the `restr` cache but keyed
  on `(ot, on, rel)`). Measure it's hot first. **Lean:** none. Low risk.

### N2. Set engine: pre-partition `restr` into wildcard / non-wildcard frozensets
- **Where:** `setengine/engine.py`, alongside the P9 `_restr_cache`.
- **What:** the hot path re-tests the `wildcard` bool on every `(t, p, w) in restr`
  membership check. Pre-partition each Direct node's restrictions into two
  frozensets (wildcard vs concrete) once (cache them the same way P9 caches the
  combined set) to drop the bool test on the hot loop. **Lean:** none. Low risk.
  Small constant-factor; pairs with N1 and P9.

### N3. Graph index: schema-level elision of the full-store residue scan — ✅ LANDED 2026-07-14
- **Where:** `index_v4/processor.py` `_gc_public_node`, `_gc_subject_node`,
  `_map_deltas_to_keys` (~L761) — all run `_residue_references` / a full
  `ResidueV1` scan + JSON decode.
- **What:** when the compiled schema has **no cross-object-recording leaf kinds**
  (no `derived-ttu` / `derived-tupleset-ttu` / `derived-userset` / userset-storage
  recordings), that scan is provably always empty and could be skipped entirely.
  Real win on non-TTU/non-userset boolean schemas.
- **Why not done now:** needs a **carefully-proven leaf-kind predicate** (getting
  it wrong corrupts GC) + the full differential matrix. Deliberately deferred on
  correctness grounds. **Lean:** none (the guard is behavior-preserving), but the
  predicate proof burden is real. Medium risk.
- **Do NOT chase:** an rc pre-guard on `_gc_subject_node` (the way P7a guards
  `_gc_public_node`) is **unsafe** — bridge-stripping can drop rc to 0 *after* the
  scan point, so the scan there is genuinely load-bearing. Confirmed dead end.

---

## Parallelization / hygiene notes (carried forward)

- **`setengine/` and `index_v4/` do not cross-import** (verified 2026-07-14) — a
  set-engine track and a graph-index track can implement + self-test concurrently
  over disjoint files without interference. This is how P9 ‖ (P3+P7) ran.
- **Run the full suite at integration**, not just the subagents' targeted gates
  — the P0 lesson: targeted gates miss uncommitted-churn / cross-cutting
  interactions (and the paranoia-mode invariant checker only runs in the full
  index_v4 suite).
- **Algorithm changes need the fuzz gate before pushing** (gate-runbook §3) — the
  P1 lesson. Behavior-preserving micro-opts ride on the `ci`-profile fuzz inside
  the suite.
- **Measurement hygiene:** never run two bench/pytest processes at once
  (CPU-contention corrupts measurement); the baseline `scale_bench.jsonl` +
  `perf_curves.png` are the pre-optimization snapshot — record after-numbers in
  `PERF_ANALYSIS.md`, don't overwrite the jsonl.
