# CORRESPONDENCE.md — the Lean-model ↔ Python-implementation map

Phase 6 item 2 (plan C2/C3; HANDOFF "The next task"). This is the auditable
backbone of the claim "the Python implementations are pinned to the Lean models
by the conformance harness": every load-bearing Lean definition, the Python
mechanism it models, and the harness gate that observes the two agreeing.

**What this table is NOT** (plan §7 honesty): a proof about the Python code.
The theorems are about the Lean models; the pin to Python is *empirical*
(`verify.sh` step 5). Line numbers are as of 2026-07-12; where a spec and the
code disagree on a name, the code wins.

**Scope note (six corners, 2026-07-12):** the verdict gates compare `check`
answers five ways (Lean `sem` · oracle · real `SetEngine` · Lean operational
graph model · real graph index); plan §7's sixth corner — state-level equality
of the materialized edge/residue state — is now gated by
`test_conformance_state.py` at the representation-neutral canonical form of
`formal/conformance/extractor.py`, under its six DOCUMENTED projections
(P1–P6: closure rows, bridges, multiplicity, empty residues, node GC,
leaf-family split). See `FINAL_REVIEW.md` §1 for the honest statement of what
that row earns.

Conformance gates (`formal/verify.sh` step 5, `formal/conformance/`):

| gate | compares | corpora |
|---|---|---|
| `test_conformance_spec.py` | Lean `sem` (zcli) vs `tests/oracle.py` vs real `SetEngine` | all 17 |
| `test_conformance_random.py` | same, randomized stores | random |
| `test_conformance_graph.py` | Lean **operational graph model** (zcli mode `"graph"`) vs real `WildcardIndex`+`DeltaProcessor`, and vs `sem` | the 15 `GRAPH_FRAGMENT` corpora |
| `test_conformance_state.py` | Lean graph model **FINAL STATE** (zcli mode `"graph-state"`: canonical direct-edge set + residues) vs the Python graph index's final SQL rows (`EdgeV4`/`ResidueV1` via `NodeV4`), projections per `extractor.py` | the 15 `GRAPH_FRAGMENT` corpora |
| `test_conformance_enum.py` | **exhaustive small-scope enumeration**: spec vs oracle vs set engine on ALL stores ≤ 3 tuples over 2 names/type (93 + 93 + 299 + 42 = 527 stores; counts asserted) | 4 fragment shapes |
| `test_cli_mode.py` | zcli mode dispatch fails closed: unknown / non-string `"mode"` → rc 4 (rc enumeration: 0 answers-or-state / 1 usage-parse / 2 admission / 3 not-drained / 4 unknown mode); absent mode defaults to spec | minimal |

All three answer-comparing suites share ONE query grid
(`formal/conformance/grid.py`): targets are the stored-tuple cross product PLUS
every schema-DECLARED `(type, relation)` paired type-aware with that type's
stored objects (so derived/boolean roots are queried on every corpus), and
subjects include userset-shaped `(relation, type, name)` over a bounded pool
(first 2 concrete names + a ghost per type). Star subjects stay bare-predicate;
the concrete-named userset queries sit inside the proved graph query scope
(`hqs` constrains only star-NAMED subjects).

---

## 1. The specification `sem` (Phase 0/2 — `Spec/`, `Core/`)

The spec is transcribed from the repository's INDEPENDENT oracle (which shares
no code with either backend), so the conformance triangle has three genuinely
independent corners.

| Lean (`lean/ZanzibarProofs/`) | models | Python |
|---|---|---|
| `Core/Refs.lean` `SubjectRef`/`ObjectRef`/`Tuple` | tuple/query layout | `tests/oracle.py` `OracleTuple`; `zanzibar_utils_v1.RelationalTriple` |
| `Core/Schema.lean` `Expr`/`Schema` (binary `union`/`inter`) | the parsed DSL AST (n-ary ops left-folded) | `tests/oracle.py` AST (`ODirect`/…/`OExclusion`); `formal/conformance/encode.py` does the fold |
| `Core/Store.lean` `universeNames` | the query universe | `oracle.py:314-351` `_universe`/`instances` |
| `Spec/Semantics.lean` `restrictionMatches`/`grantsOf` | direct-grant matching | `oracle.py:393-411` `matching_objects`/`restriction_matches`/grants |
| `Spec/Semantics.lean` `memberOfGranted` | transitive userset membership | `oracle.py:450-462` `_member_of_granted` |
| `Spec/Semantics.lean` `directLeaf` | `Direct` leaf evaluation (star + userset branches) | `oracle.py:398-448` `direct_leaf` |
| `Spec/Semantics.lean` `ttuLeaf` | stored-parent TTU rule | `oracle.py:464-485` `ttu_leaf` |
| `Spec/Semantics.lean` `evalE`/`sem` (fuel `fuelBound`, multiplicative) | the oracle's recursive evaluation | `oracle.py:353-391` `sat`/`sat_expr` |
| `Spec/WellDef.lean` `sem_fuel_stable` (T0a), `stratify_*` (T0b) | fuel-independence; stratification = no derived cycle | `zanzibar_utils_v1.compile_boolean_schema` cycle `ValueError` |

## 2. The set-engine model (Phase 3, T1 — `SetEngine/`)

| Lean | models | Python |
|---|---|---|
| `SetEngine/MemberSet.lean` `MemberSet` (`pos`/`stars`/`neg`) | the star-closed member-set algebra | `setengine/memberset.py` (union/inter/sub: `:99-105` etc.) |
| `SetEngine/Eval.lean` `expandDirect` | direct expansion | `setengine/engine.py:675-705` `direct_expand` |
| `SetEngine/Eval.lean` `expandTtu` | tupleset walk | `engine.py:707-724` `ttu_expand` |
| `SetEngine/Eval.lean` `SetEngineModel.check` | `SetEngine.check` | `setengine/engine.py` `check` |
| `SetEngine/Correct.lean` **`setEngine_correct`** (T1) | — the theorem: model `check` = `sem` | pinned empirically by `test_conformance_spec.py` (`sem` vs real `SetEngine`) |

## 3. The graph-index state and reads (T2 — `GraphIndex/State.lean`)

| Lean | models | Python |
|---|---|---|
| `GraphState` (nodes/edges/residue/outbox/watermark) | materialized closure + residue + delta stream | `index_v4/models.py:30-46` (`NodeV4` identity/keying), `:57-77` (`EdgeV4`), `:80-107` (`ResidueV1` symbolic `(stars, neg)`), `outbox.py` (`DeltaOutboxV1`) |
| `GraphState.reach` (fuel = node count) | the O(1) closure probe | `index_v4/core.py` path counts (`p > 0`) |
| `GraphModel.probeNonDerived` (≤4 probes) | untainted read | `index_v4/wildcard.py:354-374` (probe assembly inside `check`, `:318-`) |
| `GraphModel.probeDerived` (edge probe → `stars`∖`neg`, `upos`; edge hit skips `neg` — I6) | derived read path | `wildcard.py:398-432` `_check_derived` |
| `GraphModel.check` (route by `isDerived`) | `WildcardIndex.check` | `wildcard.py:318` `check` (routes tainted relations to `_check_derived` `:398`) |
| `GraphAccepts` | decision-15 compile-scope rejection | `zanzibar_utils_v1.py` `UnsupportedByGraphIndex` scope checks (object wildcards on derived `:1029-1034`; wildcard usersets over derived `:1446-1451`) |
| `Inv` (8 clauses: I1–I3 structural + I6 residue hygiene ×4) | the invariant checker | `index_v4/invariants.py` (I1 `:89-101`, node encoding `:83-87`, …) |

## 4. The write path (T2 write half — `GraphIndex/Write.lean`, `RulesWrite.lean`, `Cascade.lean`)

| Lean | models | Python |
|---|---|---|
| `GraphState.admitEdge` (`a ≠ b` ∧ no back-path) | cycle rejection | `index_v4/core.py:319-342` `_add_edge_locked` raise+rollback |
| `GraphState.writeDirect` | one guarded closure-edge insert | `wildcard.py:222` `add_tuple` → `core.py:408` `add_edge` / `:344` `add_edge_by_id` |
| `RRule`/`exprArms`/`schemaRewrites` | compiled Computed/TTU rewrite rules | `zanzibar_utils_v1.py:834-853` `_rewrite_rule`, `:870-888` `_emit_expr` |
| `rewriteClosure` | the write fan-out worklist | `RuleSet.apply` |
| `GraphState.writeLoggedOne`/`writeLoggedRules` | routed write + delta row per accepted flip | `RuleSet.apply` + per-triple `add_tuple`, `core.py:31` `_emit` |
| `GraphState.nextDeltaId`/`pushDelta`/`maxOutboxId` | outbox append / autoincrement cursor | `index_v4/outbox.py` (`outbox_watermark` `:13-21`) |

## 5. The delta processor / cascade (T2 reconcile half + T5 — `ReconcileStars.lean`, `Cascade.lean`, `CascadeStrata.lean`)

| Lean | models | Python |
|---|---|---|
| `wildcardShapes` seeding | declared wildcard shapes → candidate stars | `processor.py:135` (`DeltaProcessor.__init__` `subject_shapes`), `:58-62` `leaf_stars` |
| `coveredFn` (star-subject guard) | star-coverage read | `processor.py:62` (`leaf_stars` passes `'*'` as subject name) |
| `reconcileResidueKey` (wholesale `stars`/`neg`/`upos` recompute) | `reconcile` steps (1)–(2c): stars fold, `neg`, `upos` | `processor.py:388-441` (`neg`: `:406-411`); current-state read `_residue_state` `:166-180` |
| `reconcileKeyC`/`reconcileStarsKey` (residue-THEN-edges) | `reconcile` (residue written before edge audit) | `processor.py:382-459` (upsert `:443-446`, edge audit `:448-455`) |
| `reconcileStarsKeyD` — the DIFFING pass (stale-edge retraction) | `reconcile_subject` want/have edge diff | `processor.py:321-380`: `want_edge = should ∧ ¬covered` `:359`, edge diff `:359-369` (removal branch `:367-369`) |
| `graphRecR`/`checkFnR`/`coveredFnR` — the ROUTED operand read | `_EvalContext` (untainted → `leaf_check`→`widx.check`; derived → residue read) | `processor.py:43-70`; `member_check` `:182-188`; `derived_stars` `:69-70` |
| `affectedKeys` | delta → dirty derived keys (concrete only, `:604-605`) | `processor.py:585-652` `_map_deltas_to_keys` |
| `frontierRowsAbove`/`frontierMax` | per-round outbox read + cursor | `processor.py:701-727` (`frontier_start = max id`, `:703`) |
| `runCascade2` (two rounds + quiescence check; reject branch) | `run_cascade` (`rounds = len(strata)`), leftover ⇒ `InvariantViolation` | `processor.py:694-740` (abort `:729-739`) |
| **T5** `runCascade2_no_abort`/`cascade2_drains` | — the abort is dead code at ≤2 strata | `processor.py:736-739` |

## 6. The operational closure and the driver (W4 + Phase 6 — `FullScope.lean`, `CascadeStrataAssemble.lean`, `Exec.lean`)

| Lean | models | Python |
|---|---|---|
| `ReachedByW3d2E` = **`ReachedBy`** | the synchronous v1 write path: admitted write + same-txn cascade, interleaved | `connectedstore.advance_index` → `DeltaProcessor.run_cascade`; `tests/test_matrix.py` `GraphBackend.apply` |
| `enumJobs2R1`/`enumJobs2R2` | per-round key enumeration off the state | `processor.py:701-727` per-round `_map_deltas_to_keys` |
| `Drained` | outbox fully drained at commit boundary | boolean spec §7.8 / I9 `audit_fixpoint` |
| `GraphAdmission` (wf/nodup/strat/ttuDirect/matchDecl/ranked/objWild/storeValid) | what compile+write admission guarantees | see field docs, `FullScope.lean:64-94` (e.g. `_validate_ttu_tuplesets` `zanzibar_utils_v1.py:898-935`) |
| `W4Fragment` (rootB/computedOnly/twoStrata/wsBare/bareStar/ttuStarFree/term) | — the HONEST carries: restrictions Python does NOT impose | `history/ROADMAP.md` "W4 — honest gaps" |
| `Exec.lean` `graphRun` + `graphRun_reached`/`graphRun_check_eq_sem` | the conformance driver IS the chain (theorem, not analogy) | driven against `WildcardIndex` by `test_conformance_graph.py` (verdicts) and `test_conformance_state.py` (final state, zcli mode `"graph-state"` — same fold, same gates; the dump code in `Cli.lean` is driver-level, its projections documented in the mode header + `extractor.py`) |

## 7. Known intentional divergences (model ≠ code, by design)

* **Add-only.** The chain has no remove legs (decision 6); Python supports
  `remove_tuple`. Removal is outside every graph-side theorem.
* **Fixed two rounds.** `runCascade2` always runs 2 rounds; Python runs
  `len(strata)`. Same drained fixpoint at ≤2 strata (T5); ≥3 strata are outside
  the fragment (`hLU2` attack-confirmed load-bearing).
* **Fragment surplus.** Python accepts more than `W4Fragment` (union-rooted
  taint, object-wildcard tuples, wildcard usersets over untainted relations,
  arbitrary strata). The Phase 6 attack probe (2026-07-12k) found NO behavioral
  divergence on union-rooted / object-wildcard corpora — the exclusions are
  proof-scope, not observed disagreement (`corpus.py` note).
* **No leaf-family split.** The model reads raw boolean defs (`ComputedOnly`
  leaves); Python's compiler splits derived storage onto `<relation>.<index>`
  leaf families. **State-gate correction (2026-07-12):** the earlier note here
  claimed "on ComputedOnly defs there are no storage leaves, so the shapes
  coincide" — that holds only for `storage=True` leaves. Even on ComputedOnly
  defs the compiler creates `storage=False` CLOSURE leaves and `RuleSet.apply`
  routes copies of the untainted operand writes onto them (e.g. an `editor`
  write also lands on `viewer.0`), so the SQL edge state carries `<rel>.<i>`
  rows the model never has. The read shapes still coincide (the model reads the
  raw operand relations; the plans read the leaf copies — same content), and
  the state gate projects the class out explicitly (`extractor.py` P6, keyed on
  the reserved `'.'` in the target predicate) with the pin argument recorded
  there. Schemas needing genuine storage leaves (`Direct`/TTU arms under a
  boolean) remain outside `computedOnly`.

## 8. Keeping the model in sync when optimizing the Python (READ THIS before perf work)

The theorems are about the **Lean models**, which are *algorithm-twins* of the
Python (this whole table). A proof only means something if the Lean definition
still describes the algorithm the Python actually runs. So, when optimizing:

* A **behavior-preserving micro-optimization** (same algorithm, faster) needs no
  Lean change — the differential matrix / hypothesis / conformance gates are the
  net that it didn't change observable answers.
* An optimization that **changes the modeled algorithm** (a new candidate-pruning
  rule, a different cascade order, a restructured closure/residue update, a new
  fast path with its own logic) means the Lean definition it maps to (see the
  rows above) now describes *dead code*. **Update the corresponding Lean model to
  match, and re-run `formal/verify.sh`** (phased — `lean` → `conf-heavy` →
  `conf-rest` — per [`docs/gate-runbook.md`](../docs/gate-runbook.md) §2; the
  one-shot blows the agent command cap) — otherwise the proof silently verifies
  an algorithm you no longer ship. If the new algorithm is hard to model, that is
  a signal to keep the old one behind the model, or to widen the model
  deliberately (a real formal task, not a silent drift). Either way: never let
  the code and the model diverge unrecorded — if you must ship ahead of the
  model, log it in §7 as an intentional divergence with the reason.

### 8.1 Logged behavior-preserving perf optimizations (no Lean change)

* **P2 — batched closure-region access (`index_v4/core.py`, 2026-07-14).**
  `_add_direct_edge_unsafe`'s three expansion loops previously called
  `_add_db_edges_unsafe` once per closure pair, each a point `SELECT` + write
  (N+1). They now gather the whole `(from, to, indirect_delta)` region and apply
  it via `_add_indirect_edges_batch_unsafe`: one chunked row-value `IN` `SELECT`,
  in-memory increments, one flush. **This is below the model's abstraction level
  and needs no Lean change.** The T4 model (`Closure.lean` `pathCount_addEdge` /
  `pathCount_removeEdge`, §3 `GraphState.reach`) states the closed-form *final*
  path counts per pair; the batched code applies the identical per-pair
  arithmetic (`phat a u · phat v b` products), so the final `EdgeV4` state is
  unchanged — `DirectGraph` is a pure `V → V → Nat`, with no notion of a DB
  round-trip to restructure. The outbox model (§4 `pushDelta` /
  `writeLoggedRules`) is likewise preserved: the loops enumerate **distinct**
  pairs (subject ∉ ancestors, object ∉ descendants, no self-edges), so each pair
  already flipped at most once, and the batch emits the same action per pair in
  the same loop order — the *final* per-pair outbox action `verify_outbox_deltas`
  and the cascade key off is byte-identical. Observational equivalence (same
  final edge state + same per-pair delta stream) is what the differential matrix,
  the outbox/processor tests, the remove-path and hypothesis add/remove-
  restoration gates, and `verify.sh`'s state-level graph conformance
  (`test_conformance_state.py`) net empirically.

* **P1 — set-engine forward `lookup`: O(store) sweep → O(reachable) reverse walk
  (`setengine/engine.py`, 2026-07-14).** The forward `lookup` surface is **not
  modeled in Lean.** §2 models the set-engine *semantics* (`MemberSet`,
  `expandDirect`/`expandTtu`, `check`, and the T1 `setEngine_correct` theorem =
  model `check` ≡ `sem`); `lookup_reverse` is `expand` rendered and rides on the
  `expand` model — **both unchanged by P1.** `lookup` itself was a Python-only
  composition: `check` over *every interned key* (O(stored tuples)). P1 replaces
  the candidate sweep with a reverse BFS (`_reverse_neighbors`: `member_of`
  fan-in + wildcard-sentinel coverage + `_object_deps` (Computed/TTU-tupleset) +
  `_ttu_map` (TTU from-chain) — the reverse mirror of `check`'s
  direct-userset / Computed / TTU recursion), **verifying every surfaced
  candidate with the unchanged `check`** and keeping the intensional marker loop.
  **Hybrid:** object-wildcard schemas (`object_wildcard_shapes` non-empty) keep
  the exact O(store) sweep (`_lookup_sweep`) — a subject granted `T:*` reaches
  every object whose stored tupleset parent is a concrete `T`, which the walk
  reaches only as the `(T,'*',rel)` node, not the wildcard-covered concrete
  parents that feed the TTU (a hypothesis-deep finding). The O(reachable) walk
  runs for every wildcard-free schema (the default). Either way the observable
  output is identical (same `node_ids` + `markers`), and no
  modeled Lean definition describes `lookup`'s candidate generation — nothing
  becomes dead code. Pinned **exact two-sided** by
  `tests/test_lookup_oracle.py` (S4) against the independent brute-force oracle
  over the full candidate grid — a differential net stronger here than a Lean
  twin would be — plus the hypothesis lookup coverage and the validation matrix.
  **Superseded by N17 (below):** the `_lookup_sweep` hybrid/fallback is removed;
  `lookup` now walks on every schema.

* **N17 — set-engine forward `lookup`: O(store) sweep fully removed; walk on every
  schema via wildcard-bridge seeding (`setengine/engine.py`, 2026-07-15).** Same
  disposition as P1: forward `lookup` is **not modeled in Lean** (§2 models the
  set-engine semantics + `expand`; `lookup` is a Python-only `check`-verified
  candidate composition), so no modeled definition describes its candidate
  generation and nothing becomes dead code. N17 deletes P1's object-wildcard
  `_lookup_sweep` fallback (`_owc_needs_sweep` / `_owc_lookup_needs_sweep` gone) so
  the O(reachable) reverse walk runs for **every** schema, including object-wildcard
  ones (which P1 kept on the O(store) sweep). Candidate generation is **widened**,
  the observable output unchanged: (a) an inline *wildcard-bridge seeding* step — on
  dequeuing a star node of an object-wildcard type, enqueue the wildcard-covered
  concrete siblings (interned `ids_of_shape` members + a star-parent × TTU cross)
  the reverse walk cannot reach on its own; and (b) an H3 *star-bare fold* in
  `_reverse_neighbors` plus a subject-shape walk seed (the Commit-1 bug fix, below).
  `_lookup_sweep` is retained only as the **differential test reference**. Every
  surfaced candidate is still confirmed by the unchanged `check`, and the observable
  output (`node_ids` + `markers`) is identical to the removed sweep — pinned
  **exact two-sided** by `tests/test_lookup_oracle.py` (S4, incl. the new
  `owc_star_ttu` corpus + 8 handwritten star-parent/bridge regressions) and a new
  **walk == sweep** differential property test (`test_owc_bridge_walk_vs_sweep`,
  both `SetOps`), plus the hypothesis lookup machine over the widened corpus set.
  **Commit-1 completeness bug (no Lean impact):** the pre-existing candidate
  generation was *incomplete*, not the modeled semantics — `_reverse_neighbors`'s H3
  TTU from-chain folded only the concrete bare parent, dropping the STAR bare parent
  (`T:*` as a tupleset parent, ttu_leaf's ∀⇒∃ star branch); and the walk seed
  skipped uninterned userset subjects whose reachability is a from-chain star
  identity. Both are candidate-generation completeness fixes on an unmodeled surface
  — no Lean definition changes.

* **P12a/P12b — composition write-path round-trip elision
  (`index_v4/core.py` `_lock_store`, `connectedstore/`, 2026-07-14).** Both
  below the model's abstraction; no Lean def describes them. `ReachedByW3d2E`
  (§6) models the sync write path as *admitted write + same-transaction
  cascade* — WHAT is applied and THAT it is one transaction. P12a memoizes the
  `SELECT…FOR UPDATE` store-lock re-take per transaction (locking/concurrency
  is unmodeled; the lock is still taken, once, before the cursor read). P12b
  hands `advance_index` the just-flushed `TupleLogV1` row instead of
  re-SELECTing it, guarded by `cursor.applied_log_id == hint[0].id − 1` (+
  strict contiguity) with an exact `log_rows` fallback — the same rows in the
  same order reach the same apply loop, so the modeled chain (routed writes →
  outbox → cascade) is byte-identical; only the row *source* changed (the P2
  precedent: DB round-trips are below `DirectGraph`/the chain's abstraction).
  Exactly-once/commit structure untouched. Netted by the full differential
  suite + `test_connectedstore_*` (exactly-once, rollback, StaleRead) + graph
  conformance (verdict + state).

* **P13 — bulk closure builder for `build_index`
  (`index_v4/bulk_build.py`, `connectedstore/build.py`, 2026-07-15).** The
  offline bootstrap can now construct the pre-backfill graph state directly:
  route the tuple snapshot to a natural-key direct multigraph, topo-sort,
  compute per-pair path counts by sparse integer DP (`P(a,b) = m(a,b) +
  Σ_v m(a,v)·P(v,b)` — **T4's closed form computed directly**), and bulk-write
  nodes/edges/outbox. The modeled algorithm (incremental `pathCount_addEdge`
  maintenance) is unchanged and remains the default for every online write
  (`advance_index`/`add_tuple`); the bulk path is an **alternative constructor
  of the same state**, kept behind `build_index(..., bulk=True)` with the
  incremental loop retained as `bulk=False`. **The net is the differential
  identity gate** (`tests/test_bulk_build.py`): same snapshot built both ways
  across four corpora (union+wildcards both bridge directions, boolean+residues,
  De Morgan TTU, and a multigraph fan-in corpus with direct multiplicity ≥ 2
  and pure-indirect counts multiplied through an m≥2 edge), compared on
  id-independent canonical projections — nodes `(implicit, reference_count)`,
  edges `(direct, indirect, derived)`, residues, outbox multiset — all exactly
  equal, plus the I1–I13 invariant checker and an oracle read-parity grid on
  the bulk-built stores. No modeled definition describes dead code; nothing to
  widen.

* **R4-BF — bulk boolean backfill for `build_index`
  (`index_v4/bulk_backfill.py`, `index_v4/bulk_build.py`,
  `connectedstore/build.py`, 2026-07-15).** Same disposition as P13, one layer
  out. The **incremental backfill/cascade is the modeled algorithm** — the
  per-flip reconcile + per-stratum cascade over the outbox (§4/§5) still runs
  for every online write, and `DeltaProcessor.backfill()` itself is unchanged
  (it survives as the repair path and the `bulk=False` reference side). The
  bulk backfill is an **alternative constructor of the same modeled state**: on
  a fresh build (empty derived state, add-only) it computes the final derived
  edges / residues / from-chain nodes and their closure/refcount/outbox effects
  directly in a new in-memory Phase D that mirrors `backfill()`'s exact
  iteration and **reuses the compiled plan closures** (`plan.check_fn` /
  `plan.stars_fn` via a `_BulkEvalContext` matching the `processor._EvalContext`
  callback protocol — boolean logic shared, only state access mirrored), then
  writes everything in one extended Phase W. **The net is the extended
  differential identity gate** (`tests/test_bulk_build.py`, now **6 corpora**:
  the P13 four plus `derived_member` — derived-userset leaf + sticky
  implicit→explicit promotion under a raw userset subject over a derived
  relation — and `demorgan1`/`demorgans_law_1` — derived-tupleset-ttu leaf + ≥3
  boolean strata + an edge-free explicit rc=0 residue-anchored node — with X4b
  upos-lift assertions added on the existing `demorgan` corpus, each guarded by
  anti-vacuity assertions): the same snapshot built both ways, compared on the
  four id-independent canonical projections (nodes/edges/residues/outbox), plus
  the I1–I13 invariant checker and an oracle read-parity grid on the bulk
  stores. No Lean definition becomes dead code (the incremental processor runs
  for every online write; `backfill()` remains the repair path and the
  reference side); nothing to widen.

* **N18 — stream the bulk builder's Phase-W writes + Phase-R snapshot read
  (`index_v4/bulk_build.py`, 2026-07-16).** A pure RAM-ceiling optimization on
  the same alternative constructor P13/R4-BF introduced; **no rows, no state, and
  no modeled algorithm change**. The Phase-P DP itself is untouched (a 2026-07-16
  tracemalloc probe showed the DP holds only ~210 MB at 201.6k tuples — 91% of its
  vectors are simultaneously live, so it is not the hog and is left exactly as
  modeled). What changed is *how the already-computed rows reach the DB*: (a) Phase
  W builds + executes + frees the edge / residue / outbox row dicts in bounded
  `_WRITE_CHUNK`-row chunks (slices of the sorted `edge_pairs` / `residues.items()`)
  instead of materializing three full per-row-dict lists, so peak RSS is bounded by
  a chunk, not the whole closure — the chunks run in the identical order, so
  per-table auto-increment ids are assigned exactly as the old single INSERT; (b)
  Phase R streams the snapshot with `yield_per`, selecting only the six routed
  columns (no ORM `TupleV1` entities enter the identity map) in the same
  `order_by(TupleV1.id)` order; (c) the flushed `NodeV4` instances are expunged
  after `node_id` capture (the caller re-reads via fresh queries). The written
  nodes/edges/residues/outbox multiset is byte-identical — pinned by the same
  differential identity gate (`tests/test_bulk_build.py`, six corpora) that pins
  P13/R4-BF. As with those, no modeled definition describes DB round-trips or
  buffering (`DirectGraph` is a pure `V → V → Nat`), so nothing becomes dead code.
