# CORRESPONDENCE.md — the Lean-model ↔ Python-implementation map

Phase 6 item 2 (plan C2/C3; HANDOFF "The next task"). This is the auditable
backbone of the claim "the Python implementations are pinned to the Lean models
by the conformance harness": every load-bearing Lean definition, the Python
mechanism it models, and the harness gate that observes the two agreeing.

**What this table is NOT** (plan §7 honesty): a proof about the Python code.
The theorems are about the Lean models; the pin to Python is *empirical*
(`verify.sh` step 5). Line numbers are as of 2026-07-12; where a spec and the
code disagree on a name, the code wins.

**Scope note (five corners, not six):** the conformance gates below compare
`check` VERDICTS only — five corners (Lean `sem` · oracle · real `SetEngine` ·
Lean operational graph model · real graph index); plan §7's sixth corner,
state-level equality of materialized edge/residue state, is OPEN
(`FINAL_REVIEW.md` §1's ❌ row).

Conformance gates (`formal/verify.sh` step 5, `formal/conformance/`):

| gate | compares | corpora |
|---|---|---|
| `test_conformance_spec.py` | Lean `sem` (zcli) vs `tests/oracle.py` vs real `SetEngine` | all 17 |
| `test_conformance_random.py` | same, randomized stores | random |
| `test_conformance_graph.py` | Lean **operational graph model** (zcli mode `"graph"`) vs real `WildcardIndex`+`DeltaProcessor`, and vs `sem` | the 15 `GRAPH_FRAGMENT` corpora |

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
| `Spec/Semantics.lean` `matchesRestriction`/`granted` | direct-grant matching | `oracle.py:393-411` |
| `Spec/Semantics.lean` `memberOfGranted` | transitive userset membership | `oracle.py:450-462` `_member_of_granted` |
| `Spec/Semantics.lean` `directLeaf` | `Direct` leaf evaluation (star + userset branches) | `oracle.py:398-448` `direct_leaf` |
| `Spec/Semantics.lean` `ttuLeaf` | stored-parent TTU rule | `oracle.py:464-485` `ttu_leaf` |
| `Spec/Semantics.lean` `evalE`/`sem` (fuel `fuelBound`, multiplicative) | the oracle's recursive evaluation | `oracle.py:353-391` `sat`/`sat_expr` |
| `Spec/WellDef.lean` `sem_fuel_stable` (T0a), `stratify_*` (T0b) | fuel-independence; stratification = no derived cycle | `zanzibar_utils_v1.compile_boolean_schema` cycle `ValueError` |

## 2. The set-engine model (Phase 3, T1 — `SetEngine/`)

| Lean | models | Python |
|---|---|---|
| `SetEngine/MemberSet.lean` `MemberSet` (`pos`/`stars`/`neg`) | the star-closed member-set algebra | `setengine/memberset.py` (union/inter/sub: `:99-105` etc.) |
| `SetEngine/Eval.lean` `directExpand` | direct expansion | `setengine/engine.py:675-705` `direct_expand` |
| `SetEngine/Eval.lean` TTU expansion | tupleset walk | `engine.py:707-724` |
| `SetEngine/Eval.lean` `SetEngineModel.check` | `SetEngine.check` | `setengine/engine.py` |
| `SetEngine/Correct.lean` **`setEngine_correct`** (T1) | — the theorem: model `check` = `sem` | pinned empirically by `test_conformance_spec.py` (`sem` vs real `SetEngine`) |

## 3. The graph-index state and reads (T2 — `GraphIndex/State.lean`)

| Lean | models | Python |
|---|---|---|
| `GraphState` (nodes/edges/residue/outbox/watermark) | materialized closure + residue + delta stream | `index_v4/models.py:32-36` (`EdgeV4`), `:80-107` (`ResidueV1` symbolic `(stars, neg)`), `outbox.py` (`DeltaOutboxV1`) |
| `GraphState.reach` (fuel = node count) | the O(1) closure probe | `index_v4/core.py` path counts (`p > 0`) |
| `GraphModel.probeNonDerived` (≤4 probes) | untainted read | `index_v4/wildcard.py:354-374` |
| `GraphModel.probeDerived` (edge probe → `stars`∖`neg`, `upos`; edge hit skips `neg` — I6) | derived read path | `wildcard.py:398-432` |
| `GraphModel.check` (route by `isDerived`) | `WildcardIndex.check` | `wildcard.py` check routing |
| `GraphAccepts` | decision-15 compile-scope rejection | `zanzibar_utils_v1.py` `UnsupportedByGraphIndex` scope checks (object wildcards on derived `:1029-1034`; wildcard usersets over derived `:1446-1451`) |
| `Inv` (8 clauses: I1–I3 structural + I6 residue hygiene ×4) | the invariant checker | `index_v4/invariants.py` (I1 `:89-101`, node encoding `:83-87`, …) |

## 4. The write path (T2 write half — `GraphIndex/Write.lean`, `RulesWrite.lean`, `Cascade.lean`)

| Lean | models | Python |
|---|---|---|
| `GraphState.admitEdge` (`a ≠ b` ∧ no back-path) | cycle rejection | `index_v4/core.py` `_add_edge_locked` raise+rollback |
| `GraphState.writeDirect` | one guarded closure-edge insert | `core.py` `add_tuple`/`add_edge` |
| `RRule`/`exprArms`/`schemaRewrites` | compiled Computed/TTU rewrite rules | `zanzibar_utils_v1.py:834-852` `_rewrite_rule`/`_emit_expr` |
| `rewriteClosure` | the write fan-out worklist | `RuleSet.apply` |
| `GraphState.writeLoggedOne`/`writeLoggedRules` | routed write + delta row per accepted flip | `RuleSet.apply` + per-triple `add_tuple`, `core.py` `_emit` |
| `GraphState.nextDeltaId`/`pushDelta`/`maxOutboxId` | outbox append / autoincrement cursor | `index_v4/outbox.py` (`outbox_watermark` `:13-21`) |

## 5. The delta processor / cascade (T2 reconcile half + T5 — `ReconcileStars.lean`, `Cascade.lean`, `CascadeStrata.lean`)

| Lean | models | Python |
|---|---|---|
| `wildcardShapes`/`leafStars` seeding | declared wildcard shapes → candidate stars | `processor.py:135` (`DeltaProcessor.__init__`), `:58-62` `leaf_stars` |
| `coveredFn` (star-subject guard) | star-coverage read | `processor.py:62` (`'*'` as subject name) |
| `reconcileResidueKey` (wholesale `stars`/`neg`/`upos` recompute) | `_residue_state` | `processor.py:388-446` (`neg`: `:406-411`) |
| `reconcileKeyC`/`reconcileStarsKey` (residue-THEN-edges) | `reconcile` (residue written before edge audit) | `processor.py:382-459` (`:443-455`) |
| `reconcileStarsKeyD` — the DIFFING pass (stale-edge retraction) | `reconcile_subject` want/have diff | `processor.py:345-357`, `want_edge = should ∧ ¬covered` `:359`, removal branch `:359-367` |
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
| `W4Fragment` (rootB/computedOnly/twoStrata/wsBare/bareStar/ttuStarFree/term) | — the HONEST carries: restrictions Python does NOT impose | ROADMAP "W4 — honest gaps" |
| `Exec.lean` `graphRun` + `graphRun_reached`/`graphRun_check_eq_sem` | the conformance driver IS the chain (theorem, not analogy) | driven against `WildcardIndex` by `test_conformance_graph.py` |

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
  leaf families. On `ComputedOnly` defs there are no storage leaves, so the
  shapes coincide; schemas needing the split (`Direct`/TTU arms under a boolean)
  are outside `computedOnly`.
