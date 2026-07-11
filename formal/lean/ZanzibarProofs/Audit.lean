import ZanzibarProofs.Equiv
import ZanzibarProofs.SetEngine.Algebra
import ZanzibarProofs.SetEngine.Contains
import ZanzibarProofs.Spec.FuelStable
import ZanzibarProofs.Spec.Counterexample
import ZanzibarProofs.GraphIndex.Write
import ZanzibarProofs.GraphIndex.DirectCorrect
import ZanzibarProofs.GraphIndex.BareStarCorrect
import ZanzibarProofs.GraphIndex.ObjStarWrite
import ZanzibarProofs.GraphIndex.ObjStarCorrect
import ZanzibarProofs.GraphIndex.ObjStarClosure
import ZanzibarProofs.GraphIndex.UsStarWrite
import ZanzibarProofs.GraphIndex.UsStarCorrect
import ZanzibarProofs.GraphIndex.RulesWrite
import ZanzibarProofs.GraphIndex.RulesCorrect
import ZanzibarProofs.GraphIndex.RulesSound
import ZanzibarProofs.GraphIndex.RulesChain
import ZanzibarProofs.GraphIndex.RulesSaturate
import ZanzibarProofs.GraphIndex.RulesComplete
import ZanzibarProofs.GraphIndex.RulesBareStar
import ZanzibarProofs.GraphIndex.Reconcile
import ZanzibarProofs.GraphIndex.ReconcileWrite
import ZanzibarProofs.GraphIndex.ReconcileCorrect
import ZanzibarProofs.GraphIndex.RestrictBase
import ZanzibarProofs.GraphIndex.ReconcileComplete
import ZanzibarProofs.GraphIndex.ReconcileStars
import ZanzibarProofs.GraphIndex.ReconcileStarsComplete
import ZanzibarProofs.GraphIndex.Cascade
import ZanzibarProofs.GraphIndex.CascadeStable
import ZanzibarProofs.GraphIndex.CascadeInv
import ZanzibarProofs.GraphIndex.Correct

/-!
# Axiom audit (plan C4)

`#print axioms` on representative theorems documents the axiom surface. Fully proved
lemmas should depend only on `[propext, Classical.choice, Quot.sound]`; anything
routed through a `sorry` or an `opaque` model lists `sorryAx` / the opaque constant.

This file is DIAGNOSTIC — its output goes to the build log, it is not imported by the
library root. Build it on demand: `lake build ZanzibarProofs.Audit`. The final C4
gate (Phase 6) requires every T-theorem to show only the three standard axioms.
-/

namespace Zanzibar

-- Fully proved — expect only [propext, Classical.choice, Quot.sound]:
#print axioms MemberSet.ext_normalize
#print axioms MemberSet.ext_union
#print axioms MemberSet.containsStar_subtract
#print axioms MemberSet.mem_ext_union
#print axioms restrictionMatches_type
#print axioms wildcard_scoping
#print axioms phat_boundary
#print axioms phat_recurrence
#print axioms pathsOfLength_card_vanish
#print axioms pathCount_addEdge
#print axioms pathCount_removeEdge
#print axioms stratify_none_iff_cycle
#print axioms stratify_topological
-- T1 corrected containsShape distribution (SetEngine/Contains.lean):
#print axioms MemberSet.containsShape_union_focus
#print axioms MemberSet.containsShape_intersect_focus
#print axioms MemberSet.containsShape_subtract_focus
-- T0a ingredient 1 — untainted monotonicity (Spec/FuelStable.lean):
#print axioms evalE_mono
-- T1 — set engine computes sem (SetEngine/Correct.lean), now fully proved:
#print axioms setEngine_correct
-- T5 — cascade convergence + T2a — invariant preservation (GraphIndex/Correct.lean),
-- restated 2026-07-10 over the OPERATIONAL closure `ReachedByDirect` (the abstract
-- `WriteStep`/`ReachedBy` layer was deleted as unsound-by-weakness); plus the
-- concrete graph-model base-case lemmas. Expect only the three standard axioms:
#print axioms cascade_converges
#print axioms graph_reached_inv
#print axioms inv_empty
#print axioms quiescent_empty
#print axioms reach_empty
-- T2a write-path groundwork (GraphIndex/State.lean) — fuel-free reachability,
-- cycle-rejection, primitive invariant preservation, reachB<->NReaches bridge.
-- All expect only the three standard axioms (no `sorryAx`):
#print axioms acyclic_addEdge
#print axioms structInv_addNode
#print axioms structInv_addEdge
#print axioms inv_putResidue
#print axioms reachB_sound
#print axioms nreaches_iff_reachB
#print axioms trail_compress
#print axioms reach_complete
#print axioms reach_iff_nreaches
-- T2a concrete write model, untainted direct fragment (GraphIndex/Write.lean).
-- All expect only the three standard axioms (no `sorryAx`):
-- (`writeDirect_writeStep` / `reachedBy_of_direct` were deleted with the abstract
-- `WriteStep`/`ReachedBy` layer, 2026-07-10 — removed from this list.)
#print axioms structInv_writeDirect
#print axioms inv_writeDirect
#print axioms residueEmpty_writeDirect
#print axioms reachedByDirect_inv
-- T2b groundwork (this session) — read-side relational bridge, edge/tuple
-- soundness, and the graph-reachability ⇒ membership-chain lemma, plus the T2b
-- base case (empty state). All expect only the three standard axioms (no `sorryAx`):
#print axioms GraphModel.probeNonDerived_iff
#print axioms writeDirect_edges
#print axioms reachedByDirect_edge_sound
#print axioms reachedByDirect_nreaches_chain
#print axioms sem_empty_store
#print axioms check_empty
#print axioms graph_correct_empty
-- Evaluator fuel monotonicity on exclusion-free schemas (Spec/FuelStable.lean).
-- Expect only the three standard axioms (no `sorryAx`):
#print axioms semAux_mono
-- **T2b on the star-free pure-direct fragment (GraphIndex/DirectCorrect.lean)** —
-- the semantic core (userset lifting, chain ⇔ sem) and the end-to-end fragment
-- read-correctness theorem. All expect only the three standard axioms (no `sorryAx`):
#print axioms semAux_lift
#print axioms semAux_of_chainN
#print axioms nreaches_of_semAux
#print axioms admitted_edge_complete
#print axioms isDerived_pureDirect
#print axioms stratifiable_pureDirect
#print axioms graph_correct_direct
-- **T2b stage W1a — bare star grants `[user:*]`, ZERO bridges
-- (GraphIndex/BareStarCorrect.lean)** — soundness over `Covers` (leading bare-star
-- hop), the probe-1∨probe-2 completeness disjunction, and the end-to-end widened
-- read-correctness theorem. All expect only the three standard axioms (no `sorryAx`):
#print axioms directLeaf_elim_bs
#print axioms semAux_lift_bs
#print axioms semAux_of_chainN_bs
#print axioms reach_of_semAux_bs
#print axioms admitted_edge_source_char
#print axioms graph_correct_bareStar
-- **T2b stage W1b — object wildcards, the bridge-materializing write model
-- (GraphIndex/ObjStarWrite.lean)** — attack-first established bridges are MANDATORY
-- (machine-checked, unlike the bridge-free W1a); the faithful `writeWild` model
-- (bridge-before-grant + cycle-rejected grant), structural preservation through the
-- `w_all → concrete` bridges, and the W1b write-closure `WildReached`. All expect
-- only the three standard axioms (no `sorryAx`):
#print axioms nodeEnc_wAllNode
#print axioms structInv_ensureBridges
#print axioms structInv_writeWild
#print axioms wildReached_structInv
-- **T2b stage W1c — the userset-star (in-bridge) write model
-- (GraphIndex/UsStarWrite.lean)** — `concrete → w_any` in-bridges for declared
-- subject-wildcard userset shapes, the faithful bridge-before-grant write
-- `writeUsStar` (out-bridges then in-bridges then cycle-rejected grant), structural
-- preservation through the in-bridges, and the W1c write-closure `UsStarReached`.
-- All expect only the three standard axioms (no `sorryAx`):
#print axioms nodeEnc_wAnyNode
#print axioms structInv_ensureInBridges
#print axioms structInv_writeUsStar
#print axioms usStarReached_structInv
-- W1c edge characterization (GraphIndex/UsStarCorrect.lean) — every edge of a
-- `UsStarReached` state is a stored grant, a `w_all → concrete` out-bridge, or a
-- `concrete → w_any` in-bridge (the new W1c machinery). Standard axioms only:
#print axioms bridgedInConcrete_elim
#print axioms ensureInBridges_edges_mem
#print axioms usStarReached_grant_or_bridge
-- W1c completeness semantic core (GraphIndex/UsStarCorrect.lean) — the userset-star
-- leaf eliminations (admitting the `instances`-branch / userset-star direct match),
-- `instances_ne_star`, and `reach_of_semAux_us` (`sem ⇒ probe 1 ∨ probe 2`, threading
-- the `concrete → w_any` in-bridge), parametrized by edge-completeness + in-bridge
-- completeness. Standard axioms only:
#print axioms instances_ne_star
#print axioms directLeaf_elim_us
#print axioms mog_elim_us
#print axioms reach_of_semAux_us
-- W1c soundness semantic core (GraphIndex/UsStarCorrect.lean) — the userset-star-aware
-- lift (`semAux_lift_us`, absorbing a userset-star intermediate via the outer subject's
-- `instances`-branch flow-through), the in-bridge-absorbing chain `UsStarReach`, and its
-- two directions: `UsStarReach ⇒ sem` (`semAux_of_usStarReach`, no `instances` needed —
-- an in-bridge maps to a direct shape-match) and `trail ⇒ UsStarReach`
-- (`usStarReach_of_trail`). Standard axioms only:
#print axioms mog_intro_star
#print axioms objectName_mem_instances
#print axioms directLeaf_grant_usStar
#print axioms semAux_lift_us
#print axioms semAux_one_covers_us
#print axioms semAux_of_usStarReach
#print axioms usStarReach_of_trail
-- W1c ASSEMBLY (GraphIndex/UsStarClosure.lean) — closes `graph_correct_usStar`
-- (`check = sem` on the userset-star fragment) end-to-end. Soundness discharges the
-- fuel obligation via T0a stability (`sem_of_usStar_probe`, no tight chain-length
-- bound — the W1b plain-node count fails since a userset-star grant's source is a
-- `w_any` node). Completeness discharges `reach_of_semAux_us`'s `hEC`/`hib` over the
-- admitted closure `UsStarReachedAdmitted` (`hib` = in-bridge completeness, via the
-- liveness invariant + `isSWU_of_storeValid`). Standard axioms only:
#print axioms storeDeclared_of_storeValid
#print axioms sem_of_usStar_probe
#print axioms isSWU_of_storeValid
#print axioms usStarReachedAdmitted_edge_complete
#print axioms usStarReachedAdmitted_inbridge_live
#print axioms usStarReachedAdmitted_hib
#print axioms graph_correct_usStar
-- **T2b stage W1b — the read-correspondence SOUNDNESS core
-- (GraphIndex/ObjStarCorrect.lean)** — the grant-or-bridge edge characterization,
-- the bridge-absorbing generalized grant chain `GrantReach`, and its two directions:
-- `GrantReach ⇒ sem` (via userset lifting, keyed through `matchingObjects`) and
-- `trail ⇒ GrantReach` (peeling grant / grant+bridge hops). All expect only the
-- three standard axioms (no `sorryAx`):
#print axioms wildReached_grant_or_bridge
#print axioms semAux_lift_os
#print axioms semAux_one_of_grant
#print axioms semAux_of_grantReach
#print axioms grantReach_of_trail
-- completeness semantic core (`sem ⇒ probe 1 ∨ probe 3`), parametrized by
-- edge-completeness + the bridge hypothesis (the admitted, bridge-complete
-- write-closure that discharges them is the deferred next increment):
#print axioms reach_of_semAux_os
-- **T2b stage W1b — the admitted, bridge-complete write-closure
-- (GraphIndex/ObjStarClosure.lean)** — the composed-system closure
-- `WildReachedAdmitted`, edge-completeness (`hEC`), Lemma A (a reachable `w_all`
-- node forces a declared object-wildcard shape), bridge-completeness, the `hbr`
-- discharge, and the operationally-closed completeness theorem (probe 1 ∨ probe 3).
-- All expect only the three standard axioms (no `sorryAx`):
#print axioms wildReachedAdmitted_edge_complete
#print axioms wall_reach_isObjectWildcard
#print axioms writeWild_subjBridge
#print axioms wildReachedAdmitted_bridge_complete
#print axioms wildReachedAdmitted_hbr
#print axioms graph_complete_objStar
-- **T2b stage W1b — SOUNDNESS assembly + full `check = sem`
-- (GraphIndex/ObjStarClosure.lean)** — the plain-node accounting (`≤ 2|T|`) that
-- bounds the `GrantReach` chain length under `fuelBound`, the dead `w_any` probes,
-- and the assembled `graph_correct_objStar` (probe 1 ∨ probe 3, both directions).
-- All expect only the three standard axioms (no `sorryAx`):
#print axioms wildReached_edge_source_ne_wAny
#print axioms ensureBridges_plainCount
#print axioms writeWild_plainCount_le
#print axioms wildReachedAdmitted_plainNodes
#print axioms graph_correct_objStar
-- T3 / T6a / T6b (Equiv.lean), restated 2026-07-10 over the operational closure
-- at fragment scope — now REAL proved theorems (were false over the deleted
-- abstract closure). Expect only the three standard axioms (no `sorryAx`):
#print axioms backend_equivalence
#print axioms exclusion_effective
#print axioms no_ghost_grant
-- T3 / T6a / T6b widened to the W1b object-wildcard fragment (Equiv.lean), one-line
-- corollaries of T1 ∘ graph_correct_objStar. Expect only the three standard axioms:
#print axioms backend_equivalence_objStar
#print axioms exclusion_effective_objStar
#print axioms no_ghost_grant_objStar
-- T3 / T6a / T6b widened to the W1c userset-star fragment (Equiv.lean), one-line
-- corollaries of T1 ∘ graph_correct_usStar. Expect only the three standard axioms:
#print axioms backend_equivalence_usStar
#print axioms exclusion_effective_usStar
#print axioms no_ghost_grant_usStar

-- **T2b stage W2 — the untainted RULE-ROUTING write model
-- (GraphIndex/RulesWrite.lean, 2026-07-10).** The rewrite-fanout write `writeRules`
-- (computed / union / ttu materialized as the rewrite-closure of a raw write, each
-- triple a guarded direct edge) and its full-`Inv`/residue-free/quiescence
-- preservation + the W2 write-closure `ReachedByRules`. Standard axioms only:
#print axioms structInv_writeRules
#print axioms inv_writeRules
#print axioms reachedByRules_inv
-- W2 read-routing (GraphIndex/RulesCorrect.lean): on the untainted fragment taint
-- collapses, so `check` routes to `probeNonDerived` (pure reachability). Standard axioms:
#print axioms taintedKeys_untainted
#print axioms check_eq_probeNonDerived
#print axioms reachedByRules_edge_sound
-- W2 storage-only tupleset fragment (GraphIndex/RulesCorrect.lean, 2026-07-10):
-- attack-first found `check ≠ sem` without the `_validate_ttu_tuplesets` condition
-- (a `computed` tupleset makes the rewrite-fanout fire a TTU on a rewrite-produced
-- triple while `ttuLeaf` reads stored tuplesets). `TtuTuplesetsDirect` + the
-- rewrite-closure structure lemmas: no rewrite outputs a tupleset relation, so a
-- closure tuple on a tupleset relation is the raw seed. Standard axioms only:
#print axioms exprArms_directsOnly
#print axioms no_rewrite_outputs_tupleset
#print axioms rewriteClosure_object
#print axioms rewriteClosure_seed
#print axioms closure_tupleset_is_seed

-- W2 SOUNDNESS core (GraphIndex/RulesSound.lean, 2026-07-10): the rewrite-closure
-- realises `evalE`'s computed/ttu/union recursion. `semAux_of_rewriteClosure` — every
-- rewrite-closure tuple of a stored tuple is a `sem` membership at some fuel (seed =
-- direct self-grant; computed = the predecessor's membership under the computed arm;
-- ttu = `ttuLeaf`'s stored-tupleset disjunct on the seed via `closure_tupleset_is_seed`).
-- `lookup_of_mem` needs `NodupKeys` (the Python schema is a dict). Standard axioms only:
#print axioms lookup_of_mem
#print axioms untainted_noExclAll
#print axioms storeDeclared_of_validRules
#print axioms semAux_seed
#print axioms semAux_step
#print axioms semAux_of_rewriteClosure

-- W2 SOUNDNESS direction end-to-end (GraphIndex/RulesChain.lean, 2026-07-10): the
-- userset lift generalised from PureDirect to UntaintedSchema (`semAux_lift_untainted`,
-- via `evalE_lift` — direct/computed/ttu/union), chain composition over the
-- rewrite-closure (`semAux_of_ruleChain`), and the top-level `sem_of_rules_reach` (graph
-- reachability ⇒ sem; fuel via the T0a-stability sidestep). Standard axioms only:
#print axioms ttuLeaf_elim
#print axioms semAux_lift_untainted
#print axioms rewriteClosure_subjectName
#print axioms rewriteClosure_rel_ne_bare
#print axioms semAux_of_ruleChain
#print axioms sem_of_rules_reach

-- W2 completeness groundwork (GraphIndex/RulesComplete.lean, 2026-07-10): the
-- admitted rule-routed write-closure + edge-completeness of every materialised
-- rewrite-closure tuple. Expect only the three standard axioms:
#print axioms foldl_writeDirect_edge_complete
#print axioms reachedByRulesAdmitted_edge_complete
#print axioms reachedByRulesAdmitted_seed_edge
#print axioms reachedByRules_of_admitted

-- W2 rewrite-closure saturation (GraphIndex/RulesSaturate.lean, 2026-07-10): under
-- rewrite-acyclicity (RewriteRanked) the |keys|+1-level closure is closed under one
-- more rewrite step — the depth-bound the completeness `computed` case consults.
-- Expect only the three standard axioms:
#print axioms rewriteClosure_saturated
#print axioms stepN_rank_ge
#print axioms rwKey_rank_lt

-- W2 completeness core + top-level (GraphIndex/RulesComplete.lean, 2026-07-10):
-- sem ⇒ reach (nreaches_of_semAux_rules, with the computed-case last-edge rewrite
-- nreaches_relation_rewrite) and the full check = sem assembly graph_correct_rules.
-- Expect only the three standard axioms:
#print axioms nreaches_relation_rewrite
#print axioms nreaches_of_semAux_rules
#print axioms graph_correct_rules

-- T3/T6 widened to the W2 rule-routing fragment (Equiv.lean, 2026-07-10), free
-- corollaries of T1 ∘ graph_correct_rules. Expect only the three standard axioms:
#print axioms backend_equivalence_rules
#print axioms exclusion_effective_rules
#print axioms no_ghost_grant_rules

-- T0a statement-level refutation (Spec/Counterexample.lean, 2026-07-10): the
-- pre-`StoreDeclared` statement is machine-checked FALSE. Expect only the
-- standard axioms (decide-based, no sorryAx, no ofReduceBool):
#print axioms T0aCounter.oscillates
#print axioms T0aCounter.fuel_stable_step_false
#print axioms T0aCounter.not_storeDeclared

-- **T0a — FULLY PROVED 2026-07-10** (sorry count 0): the confinement layer
-- (Spec/Confine.lean), the taint-fixpoint + untainted counting stabilization
-- (Spec/Stabilize.lean), the strict Kahn interface, and the rank-induction
-- assembly (Spec/WellDef.lean). Expect only the three standard axioms:
#print axioms evalE_congr
#print axioms step_congr
#print axioms untainted_closed
#print axioms semAux_mono_untainted
#print axioms untainted_stable
#print axioms kahn_topo_strict
#print axioms stratify_covers
#print axioms stratify_topo_strict
#print axioms layer_stable
#print axioms all_stable
#print axioms semAux_fuel_stable_step
#print axioms sem_fuel_stable

-- **ROADMAP W3a — the derived reconcile / residue path, read-side collapse
-- (GraphIndex/Reconcile.lean, 2026-07-10).** On the star-free bare-subject fragment
-- the processor stores no residue row, so the state stays `ResidueEmpty` and the
-- derived read `probeDerived` collapses to the bare edge probe (a derived relation
-- only adds edges — structurally an ordinary `writeDirect`). Standard axioms only:
#print axioms GraphModel.probeDerived_residueEmpty
#print axioms GraphModel.probeDerived_ResidueEmpty
#print axioms GraphModel.check_derived_ResidueEmpty

-- **ROADMAP W3a — the derived reconcile WRITE model (GraphIndex/ReconcileWrite.lean,
-- 2026-07-10).** `checkFn` (the compiled `check_fn`, modelled as `evalE` reading the
-- graph via `graphRec`), the guarded `reconcileKey` derived-edge fold (a derived edge
-- is structurally `writeDirect ⟨s,R,o⟩`), its full Inv/residue-free/quiescence
-- preservation, the W3a write-closure `ReachedByW3a`, and its T2a `Inv` conjunct
-- `reachedByW3a_inv` (residue-free ⇒ the read collapses to the edge probe). The
-- correspondence (checkFn = sem + candidate completeness) is the next increment.
-- Standard axioms only:
#print axioms structInv_reconcileKey
#print axioms inv_reconcileKey
#print axioms reachedByW3a_inv
#print axioms reachedByW3a_residueEmpty

-- **ROADMAP W3a — the `check_fn` ↔ `sem`-step reduction (GraphIndex/ReconcileCorrect.lean,
-- 2026-07-10).** The first spine of the W3a read correspondence: on the `ComputedOnly`
-- derived-def fragment (boolean tree over `computed` refs), `evalE`'s graph node-recursion
-- and `sem`'s fuel recursion agree (`evalE_computedOnly`), so `checkFn` equals one `sem`
-- immediate-consequence step of the derived key given per-relation graph↔`sem` agreement
-- on the operands (`checkFn_eq_semStep`) — isolating the remaining blocker to that
-- per-relation untainted fact. Standard axioms only:
#print axioms evalE_computedOnly
#print axioms checkFn_eq_semStep

-- **ROADMAP W3a — the reconcile edge characterization (GraphIndex/ReconcileCorrect.lean,
-- 2026-07-10).** The structural spine for the bare-subject reach-collapse: the reconcile
-- fold only adds edges (`reconcileKey_edges_mono`), every new edge is a candidate's derived
-- edge (`reconcileKey_edge_sound`), and every edge of a W3a state is either a materialised
-- rewrite-closure tuple (untainted base) or a reconcile derived edge
-- (`reachedByW3a_edge_sound`). Standard axioms only:
#print axioms reconcileKey_edges_mono
#print axioms reconcileKey_edge_sound
#print axioms reachedByW3a_edge_sound

-- **ROADMAP W3a — the bare-subject reach-collapse spine (GraphIndex/ReconcileCorrect.lean,
-- 2026-07-11).** A generic single-edge collapse (`nreaches_collapse_of_source_notarget`),
-- the structural fact that every W3a edge target has a non-`BARE` predicate — so a bare
-- candidate node is never an edge target (`reachedByW3a_edge_target_ne_bare` /
-- `reachedByW3a_bareNode_no_inedge`) — and their assembly: a bare-subject path to a derived
-- object node collapses to a single edge, given every R-node in-edge source is bare
-- (`reachedByW3a_reach_collapse`; the `NoRuleOutputs` gap is the next increment). Standard
-- axioms only:
#print axioms nreaches_collapse_of_source_notarget
#print axioms reachedByW3a_edge_target_ne_bare
#print axioms reachedByW3a_bareNode_no_inedge
#print axioms reachedByW3a_reach_collapse

-- **ROADMAP W3a — `hsrcbare` discharged via `NoRuleOutputs` (GraphIndex/ReconcileCorrect.lean,
-- 2026-07-11).** The reach-collapse's `hsrcbare` hypothesis (every R-node in-edge source is
-- bare) is discharged on the `RootBoolean` (inter/excl-rooted) derived-def fragment: such a
-- def emits no rewrite arms and no `Direct` storage arm, so no rewrite outputs `(dt,R)`
-- (`noRuleOutputs_of_root`) and no stored tuple sits on it — killing the base leg, leaving
-- every R-node in-edge a bare-sourced reconcile edge (`reachedByW3a_Rnode_source_bare`).
-- Hence the fully-discharged collapse `reachedByW3a_reach_collapse_root`. Standard axioms only:
#print axioms noRuleOutputs_of_root
#print axioms reachedByW3a_Rnode_source_bare
#print axioms reachedByW3a_reach_collapse_root

-- **ROADMAP W3a — reconcile-edge reachability inertness (GraphIndex/ReconcileCorrect.lean,
-- 2026-07-11).** Resolves the flagged R-node-source subtlety: on the single-stratum W3a
-- fragment the derived boolean `R` is terminal (`NoTtuTarget` + `NoStoreSubjectR`), so no
-- rewrite-closure subject predicate is `R` (`rewriteClosure_subject_pred_ne`) and no W3a edge
-- is sourced at an `R`-userset node (`reachedByW3a_edge_source_ne_R` /
-- `reachedByW3a_Rnode_not_source`) — the R-node has no out-edge. Hence a reconcile pass is
-- reachability-inert for any non-R-node read (`reconcileKey_reach_inert`, via the generic
-- `nreaches_cons_inert`). The per-pass inertness the multi-pass `hag` transfer folds over.
-- Standard axioms only (two axiom-free):
#print axioms nreaches_cons_inert
#print axioms rewriteClosure_subject_pred_ne
#print axioms reachedByW3a_edge_source_ne_R
#print axioms reachedByW3a_Rnode_not_source
#print axioms reconcileKey_reach_inert

-- **ROADMAP W3a — multi-pass reconcile inertness folded to the untainted base
-- (GraphIndex/ReconcileCorrect.lean, 2026-07-11).** Folds `reconcileKey_reach_inert` over the
-- whole W3a write path: for a W3a state there is an untainted base (`ReachedByRules`) with the
-- same reachability into every *untainted-key* node (`isDerived S (v.type,v.pred) = false`).
-- Each reconcile pass writes only into its derived R-node (`hder : isDerived (dt,R) = true`),
-- distinct from any untainted target since equal keys share `isDerived`; the R-node-not-a-source
-- premise comes from the pre-pass sub-derivation via the schema-level terminal hypothesis
-- `hterm`. The reachability half of the `hag` reduction (PROOF_STATUS point 2). Standard axioms:
#print axioms reachedByW3a_reach_inert

-- **ROADMAP W3a — the operand-read reduction to the untainted base
-- (GraphIndex/ReconcileCorrect.lean + State.lean, 2026-07-11).** Upgrades the inertness fold to
-- a biconditional (`reachedByW3a_reach_inert_iff`, backward via the general subset-monotonicity
-- `NReaches.mono_subset` + `σ0.edges ⊆ σ.edges`), then lifts it to the `probeNonDerived` read
-- `hag` consults: every W3a edge endpoint is plain on the star-free fragment
-- (`reachedByW3a_edges_plain`, using the new star-free constructor fields), so the read collapses
-- to probe 1 (`probeNonDerived_plainEdges`, strengthened to need only plain edges), and
-- `graphRec_reduce_base` equates the operand read on the full W3a state to the read on the
-- untainted base for every untainted operand relation. Reduces `hag` to a *base* per-relation W2
-- fact. Standard axioms only:
#print axioms NReaches.mono_subset
#print axioms reachedByW3a_reach_inert_iff
#print axioms reachedByW3a_edges_plain
#print axioms probeNonDerived_plainEdges
#print axioms graphRec_reduce_base

-- **ROADMAP W3a Step A — schema restriction to the untainted fragment
-- (GraphIndex/RestrictBase.lean, 2026-07-11).** The `hag` base reduction: restrict `S` to
-- `S↾U := restrictUntainted S` (drop every tainted-key def), which is untainted
-- (`untaintedSchema_restrict`, under `NodupKeys`), and transfer `sem` between `S` and `S↾U` on
-- untainted keys (`semAux_restrict`) — untaintedness is hereditary (the taint fixpoint confines
-- an untainted def's references to untainted keys, `untainted_closed`), so evaluating an untainted
-- relation never consults a dropped derived def. `restrictUntainted_lookup`: the schemas agree at
-- every untainted key. This lets `graph_correct_rules` (proved over whole-schema `UntaintedSchema`)
-- discharge the mixed-schema `hag` as a black box. Standard axioms only:
#print axioms untaintedSchema_restrict
#print axioms restrictUntainted_lookup
#print axioms semAux_restrict
-- The rewrite fan-out is preserved by the restriction (tainted defs emit no arms), the
-- state-transfer groundwork: schemaRewrites unchanged, hence rewriteStep and the bounded
-- closure (at any fixed fuel) unchanged. Standard axioms only:
#print axioms schemaRewrites_restrict
#print axioms rewriteClosureAux_restrict
-- **The fuel bridge, closed (2026-07-11).** The two canonical closures — `rewriteClosure S t`
-- (fuel `|S.keys|+1`) and `rewriteClosure (S↾U) t` (smaller fuel `|S↾U.keys|+1`) — have identical
-- membership. `⊇` is unconditional fuel monotonicity (`rewriteClosureAux_mono` via the `stepN`
-- layer algebra); `⊆` is saturation of the `S↾U`-closure, whose `RewriteRanked (S↾U)` is built
-- from `RewriteRanked S` by rank COMPRESSION (`rewriteRanked_restrict`, counting `S↾U`-keys ranked
-- below `k`), given the faithful side condition `RewriteMatchDeclared` (every rewrite's match key
-- is a declared untainted relation, confining each step to the kept cone). Standard axioms only:
#print axioms rewriteRanked_restrict
#print axioms rewriteClosure_restrict_mem_iff

-- **The state transfer (2026-07-11).** From an admitted rule-routed state `σ0` over the MIXED
-- schema `S`, `exists_admitted_restrict` builds a canonical `ReachedByRulesAdmitted σ' (S↾U) T`
-- with identical edge membership. Both edge sets are exactly the materialised rewrite closures
-- (`reachedByRules_edge_sound` / `reachedByRulesAdmitted_edge_complete`), which agree by the fuel
-- bridge; the admissions transfer because they depend only on the acyclicity of the shared target
-- relation `σ0.edges` (`foldAdmits_of_acyclic` — a `writeDirect` fold admits when every
-- materialised edge lands in an acyclic relation containing the running edges). Standard axioms:
#print axioms foldAdmits_of_acyclic
#print axioms exists_admitted_restrict

-- **The base `hag` equation (2026-07-11) — Step A closed.** `graphRec_base_eq`: on an admitted
-- rule-routed state `σ0` over the MIXED schema `S`, the operand read `graphRec σ0 s dt on r'`
-- (for an untainted operand `r'`) equals `sem S T ⟨s, r', ⟨dt,on⟩⟩`. Composes the state transfer
-- with `graph_correct_rules` over `S↾U`: `graphRec σ0 = probeNonDerived σ0 = probeNonDerived σ'`
-- (edge agreement) `= check σ' = sem (S↾U) T q'` `= sem S T q'` (`semAux_restrict` at `fuelBound S`
-- + fuel stability over the untainted `S↾U`). Fragment premises: `RootBoolean`-derived defs (⇒
-- stored relations untainted, ⇒ the W2 restriction hypotheses transfer), `RewriteMatchDeclared`,
-- and the W2 conditions on the base. This discharges the W3a correspondence blocker `hag` on an
-- admitted base. Standard axioms only:
#print axioms graphRec_base_eq

-- **The `check_fn` ↔ `sem` bridge (2026-07-11) — Step B increment 1.** `checkFn_eq_sem`: on a
-- W3a-*admitted* state `σ`, the compiled `check_fn` for a bare subject `s` at a `ComputedOnly`
-- derived key `(dt, R)` (untainted computed leaves) equals `sem S T ⟨s, R, ⟨dt,on⟩⟩`. Composes
-- `graphRec_reduce_base_adm` (operand reads reduce to the admitted base — the admitted analog of
-- `graphRec_reduce_base`), `graphRec_base_eq` (base read = `sem`), `semAux_qirrel` (`sem` never
-- reads the query except through `instances`, which discards it — so the operand `sem` at query
-- `⟨s,r',o⟩` feeds `checkFn_eq_semStep`'s enclosing query `⟨s,R,o⟩`), and T0a fuel stability.
-- Standard axioms only:
#print axioms semAux_qirrel
#print axioms graphRec_reduce_base_adm
#print axioms checkFn_eq_sem

-- **Derived-edge soundness (2026-07-11) — Step B forward half.** `reachedByW3aAdmitted_derived_edge_
-- sound`: on a W3a-admitted state a materialised derived edge `subjNode s → objNode ⟨dt,on⟩ R`
-- (bare star-free `s`) witnesses `sem S T ⟨s,R,⟨dt,on⟩⟩ = true`. The base leg cannot feed the
-- `RootBoolean` R-node (`reachedByRules_RootBoolean_no_inedge`); a reconcile leg either inherits the
-- edge (IH) or wrote it, and the guard at a W3a-admitted prefix mid-state (`reconcileKey_edge_guard`)
-- becomes `sem` via `checkFn_eq_sem`. Standard axioms only:
#print axioms reconcileKey_edge_guard
#print axioms reachedByW3aAdmitted_derived_edge_sound

-- **Candidate completeness + the W3a assembly (2026-07-11) — Step B closed.** `w3aComplete_derived_
-- edge`: on a coverage-complete W3a state a `sem`-true bare subject's derived edge is materialised
-- (the covering job enumerates it; guard = sem via `checkFn_eq_sem`; admitted terminal write;
-- persists — `reconcileKey_edge_present` + `reconcileJobs_edges_mono`). `graph_correct_w3a`: on a
-- W3a-complete state `check = sem` for every BARE-subject star-free query — untainted via the base
-- reduction, derived via the residue-empty edge probe glued by soundness/completeness. Scope is
-- bare-subject (attack-first: a userset on a derived key can be sem-true while the residue-empty
-- read is false — W3b's `upos`). Standard axioms only:
#print axioms w3aComplete_derived_edge
#print axioms graph_correct_w3a

-- **T3/T6 at W3a scope (2026-07-11) — Step C.** The backend-equivalence / deny-propagation /
-- no-ghost-grant corollaries at the star-free bare-subject derived-boolean fragment (T1 ∘
-- `graph_correct_w3a`); T6a carries the first real exclusion content. Standard axioms only:
#print axioms backend_equivalence_w3a
#print axioms exclusion_effective_w3a
#print axioms no_ghost_grant_w3a

-- **ROADMAP W3b — the userset `upos` residue (GraphIndex/ReconcileUpos.lean, 2026-07-11).**
-- The write model `reconcileUposKey` (per-candidate insert/remove on the `upos` list, faithful to
-- `reconcile_subject`'s userset branch — edge-free, blind-audit P4), the congruence spine (`checkFn`
-- reads only the edge/node core, hence is constant across the upos fold), the whole-fold membership
-- characterization, and the W3b read collapse (`probeDerived` on a `upos`-only residue table:
-- star ⇒ false, userset ⇒ `upos` membership, bare ⇒ the W3a edge probe). Standard axioms only:
#print axioms checkFn_congr
#print axioms reconcileUposKey_upos_mem
#print axioms GraphModel.probeDerived_uposOnly
#print axioms GraphModel.check_derived_uposOnly

-- **W3b closure + shadow projection + T2a (GraphIndex/ReconcileUposComplete.lean, 2026-07-11).**
-- `ReachedByW3b` (admitted base + interleaved bare-edge and userset-upos passes); the SHADOW
-- PROJECTION `reachedByW3b_shadow` (every W3b state has a W3a-admitted shadow with identical core,
-- so all W3a edge/reach facts transfer); residue provenance; `reachedByW3b_inv` — the full `Inv`
-- with CONTENTFUL I6 (`uposEdgeFree` proved for real: a upos member is userset-shaped while every
-- path onto the `RootBoolean` R-node is a single bare-sourced edge). Standard axioms only:
#print axioms reachedByW3b_shadow
#print axioms reachedByW3b_residue_provenance
#print axioms reachedByW3b_inv

-- **W3b correspondence + assembly (2026-07-11).** `checkFn_eq_sem_w3b` (subject-generic, via the
-- shadow); `upos` soundness (an entry witnesses `sem`, the fold-constant guard at the W3b pass-start
-- state); `upos` persistence + userset completeness (`w3bComplete_derived_upos`: the covering upos
-- job writes the entry, later jobs keep it — a same-key re-reconcile re-evaluates the guard, which
-- is `sem = true`); bare completeness through the covering edge job; and the W3b assembly
-- `graph_correct_w3b`: `check = sem` on EVERY star-free query — the W3a bare-subject scope
-- restriction is lifted, userset subjects on derived keys are answered by `upos`. Standard axioms
-- only:
#print axioms checkFn_eq_sem_w3b
#print axioms reachedByW3b_upos_sound
#print axioms reconcileJobsB_upos_persist
#print axioms w3bComplete_derived_edge
#print axioms w3bComplete_derived_upos
#print axioms graph_correct_w3b

-- **T3/T6 at W3b scope (2026-07-11).** The backend-equivalence / deny-propagation / no-ghost-grant
-- corollaries with the bare-subject hypothesis GONE — T6a now covers a userset subject excluded by
-- a derived `but not` (the P4 non-leak, both directions). Standard axioms only:
#print axioms backend_equivalence_w3b
#print axioms exclusion_effective_w3b
#print axioms no_ghost_grant_w3b

-- **ROADMAP W3c — star coverage and the `stars`/`neg` residue, write half + T2a
-- (GraphIndex/ReconcileStars.lean, 2026-07-11).** The wholesale residue recompute
-- `reconcileResidueKey` (stars = the star-subject `checkFn` filter — the pointwise form of the
-- compiled star fold `plan.stars_fn`; `neg` = covered ∧ expr-false; `upos` gains its ¬covered
-- guard) and the covered-guarded edge fold (`want_edge = should ∧ ¬covered`). Three structural
-- devices: the COVERED-FILTER COLLAPSE `reconcileKeyC_eq_filter` (the covered guard is
-- fold-constant, so the W3c edge fold IS a W3a `reconcileKey` on the filtered candidates — all
-- W3a fold lemmas transfer); the shadow projection `reachedByW3c_shadow`; and STAR-GENERAL
-- operand-read inertness `graphRec_reconcileKey_inert` (NO `StarFreeStore` — all four probe
-- targets of an untainted-key read differ from the terminal R-node), which pins every persisted
-- `stars` row to the canonical star set of the chain base (`reachedByW3c_master`) — and, via
-- `reconcileKey_edge_guard` + prefix-mid-state inertness, pins GUARD CANONICITY: every `neg`
-- member is canonically expr-false, every `upos` member canonically expr-true, every reconcile
-- edge source canonically expr-true and uncovered (the graph-internal half of the W3c read
-- correspondence; composing with a star-relaxed base equation `checkFn = sem` is what remains). T2a
-- `reachedByW3c_inv`: the full `Inv` with ALL FOUR I6 clauses contentful for the first time —
-- `negStarCovered` (write-time filter), `uposNegDisjoint` (covered vs ¬covered, same row),
-- `uposEdgeFree` (userset member vs bare-sourced single edge), and `negEdgeFree` (the space rule
-- cross-pass: a `neg` member is canonically covered, every reconcile edge source canonically
-- uncovered) — with no `StarFreeStore` hypothesis anywhere. Standard axioms only:
#print axioms reconcileKeyC_eq_filter
#print axioms reachedByW3c_shadow
#print axioms graphRec_reconcileKey_inert
#print axioms reachedByW3c_master
#print axioms reachedByW3c_inv

-- **ROADMAP W3c read half, step 1 — the untainted correspondence over BARE-STAR stores
-- (GraphIndex/RulesBareStar.lean, 2026-07-11).** `graph_correct_rulesBS`: W2's `check = sem`
-- re-proved with `StarFreeStore` weakened to `BareStarStore` + `TtuStarFree` (no wildcard TTU
-- parents — attack-CONFIRMED necessary: a star tupleset tuple needs the W1c in-bridges the
-- rule-routed write model does not materialise), and the query scope widened to STAR-BARE
-- subjects (probe 1 at the `wAny` source) — the star-subject instance the W3c `stars ↔ sem`
-- correspondence consumes. Machinery: closure star-characterisation
-- (`rewriteClosure_star_subject`: no ttu arm ever fires on a star-subject closure member, so it
-- carries the seed's full subject — bare), subject-generic per-hop soundness
-- (`semAux_of_rewriteClosure_bs`) + userset lift (`semAux_lift_untainted_bs`) + chain composition
-- (`semAux_of_ruleChain_bs`, via global `subjNode` injectivity), the star→concrete coverage
-- transfer `semAux_star_to_bare` (probe-2 glue: a `wAny`-source chain IS a star-subject chain),
-- and completeness `nreaches_of_semAux_rulesBS` (probe-1 ∨ probe-2 disjunction). Standard axioms
-- only:
#print axioms rewriteClosure_star_subject
#print axioms semAux_of_rewriteClosure_bs
#print axioms semAux_lift_untainted_bs
#print axioms semAux_of_ruleChain_bs
#print axioms semAux_star_to_bare
#print axioms nreaches_of_semAux_rulesBS
#print axioms rulesAdmitted_edge_endpoints_bs
#print axioms graph_correct_rulesBS

-- **ROADMAP W3c read half, step 1 CLOSED — the star-relaxed base equation
-- (RestrictBase.lean + ReconcileComplete.lean, 2026-07-11).** `graphRec_base_eq_bs`: the
-- admitted mixed-schema base's operand read = `sem` over `BareStarStore` + `TtuStarFree`
-- stores, subject-generic up to star-BARE subjects (the schema-restriction route with
-- `graph_correct_rulesBS` as the untainted black box; `TtuStarFree` transfers to `S↾U`
-- because the restriction preserves `schemaRewrites`). `graphRec_reduce_base_adm_bs`: the
-- W3a-admitted state's operand read reduces to the base with NO `StarFreeStore` — the
-- plain-edges probe-killing shortcut is replaced by transferring ALL FOUR probes (both
-- probe targets carry the untainted key `(dt, r')`, so the reach-inertness applies to each
-- verbatim). `checkFn_eq_sem_bs`: the composed star-relaxed `checkFn ↔ sem` bridge — the
-- form the W3c `coveredFn`/`stars ↔ sem` correspondence consumes. Standard axioms only:
#print axioms graphRec_base_eq_bs
#print axioms graphRec_reduce_base_adm_bs
#print axioms checkFn_eq_sem_of_base_bs
#print axioms checkFn_eq_sem_bs

-- **ROADMAP W3c read half CLOSED — the linchpin + the assembly
-- (GraphIndex/ReconcileStarsComplete.lean + Equiv.lean, 2026-07-11).**
-- `checkFn_eq_sem_w3c`: the star-relaxed `checkFn = sem` on ANY W3c state (through the
-- W3a-admitted shadow). `coveredFn_declared` — THE LINCHPIN, no ghost star coverage: a
-- `sem`-covered shape is DECLARED (true computed leaf → wAny-sourced probe → first edge →
-- materialised closure tuple → the star seed carries its subject → `restrictionMatches`'
-- wildcard flag names a `wildcardShapes` entry). `w3c_row_char`: every persisted row reads
-- at `sem` level (master provenance + the star-relaxed bridge). Batch completeness for the
-- WHOLESALE residue recompute: `reconcileJobsC_row_isSome` (row existence),
-- `reconcileJobsC_neg_complete` / `reconcileJobsC_upos_complete` (an attack-first `#eval`
-- confirmed the ∀-targeting-jobs enumeration form is NECESSARY — a second same-key pass
-- with an incomplete `negCands` drops the exclusion), `w3cComplete_derived_edge` (the
-- covered-filter survival + prefix-mid-state inertness + terminal admitted write).
-- **T2b `graph_correct_w3c`**: `check = sem` on star-CARRYING stores (`BareStarStore` +
-- `TtuStarFree`; `hWSbare` = decision-15 bare-only declared shapes) for bare, star-BARE,
-- and userset subjects — all three `probeDerived` branches: star ⇒ `stars`, bare ⇒ edge ∨
-- (`stars` ∖ `neg`), userset ⇒ `upos`. T3/T6 `*_w3c`: `backend_equivalence_w3c`,
-- `exclusion_effective_w3c` (a concrete subject excluded from UNDER a `T:*` grant — the
-- space rule's `neg` actually excludes), `no_ghost_grant_w3c`. Standard axioms only:
#print axioms checkFn_eq_sem_w3c
#print axioms coveredFn_declared
#print axioms w3c_row_char
#print axioms reconcileJobsC_neg_complete
#print axioms reconcileJobsC_upos_complete
#print axioms w3cComplete_derived_edge
#print axioms graph_correct_w3c
#print axioms backend_equivalence_w3c
#print axioms exclusion_effective_w3c
#print axioms no_ghost_grant_w3c

-- **ROADMAP W3d-1a — the cascade scheduling layer (GraphIndex/Cascade.lean,
-- 2026-07-11e).** The scheduler is now IN the model: logged writes emit one outbox
-- row per accepted routed edge (`writeLoggedRules`), `affectedKeys` maps a frontier
-- row to the derived keys reading its reach cone (`_map_deltas_to_keys` + `_fan_out`
-- `via='computed'`, fragment-restricted), and `runCascade` reconciles the mapped keys
-- then models Python's final quiescence check (`InvariantViolation`,
-- `processor.py:729-739`) as a reject branch. The interleaved closure `ReachedByW3d`
-- admits writes AFTER cascades (the W3a–W3c chains could not). **T5, contentful and
-- justified**: `runCascade_no_abort` — the reject branch never fires at one stratum
-- (every pass-emitted row sits at a terminal derived R-node whose predicate no
-- derived def reads as an operand, so it maps to no keys); `cascade_drains` — the
-- post-cascade state is `Quiescent`, with the watermark advance EARNED by no-abort,
-- never asserted (the fix for the deleted vacuous `cascade_converges` shape).
-- R-node terminality re-proved over the interleaved closure
-- (`reachedByW3d_edge_source_ne_R`). Standard axioms only:
#print axioms writeLoggedRules_evalEq
#print axioms reconcileJobsL_evalEq
#print axioms reconcileJobsL_outbox_sound
#print axioms reachedByW3d_edge_source_ne_R
#print axioms reachedByW3d_Rnode_not_source
#print axioms runCascade_no_abort
#print axioms cascade_drains

-- **ROADMAP W3d decision 7 — the DIFFING edge audit (GraphIndex/ReconcileDiff.lean,
-- 2026-07-11f).** Attack-first `#eval` REFUTED the naive W3d-1b read statement over
-- the add-only pass: on `viewer := member ∖ banned` (no star grants), a post-cascade
-- `banned` add flips the derived guard down and the second cascade cannot retract the
-- stale derived edge — `check = true ≠ sem = false` at a fully-drained state. Python
-- retracts it (`reconcile_subject`, `processor.py:365-367`). The W3d pass is now the
-- diffing audit `reconcileStarsKeyD` (add when `want`, remove ALL copies of the pair
-- when `¬want`); T5 above is re-earned over it. Removal is path-inert off the pass's
-- terminal R-node (`nreaches_remove_terminal`), giving BOTH inertness directions —
-- the foundation for W3d-1b settledness. Standard axioms only:
#print axioms nreaches_remove_terminal
#print axioms reconcileKeyD_edge_sound
#print axioms reconcileKeyD_Rnode_terminal
#print axioms reconcileKeyD_reach_inert
#print axioms reconcileKeyD_reach_pres

-- **W3d-1b groundwork — per-key edge EXACTNESS of the diffing pass.** The guard
-- `wantEdge = checkFn ∧ ¬covered` is fold-invariant (operand-read inertness), so one
-- full-object diffing pass makes the key's derived edge set EXACTLY the wanted
-- candidates plus untouched non-candidates — candidate history is erased
-- (`reconcileStarsKeyD_edge_char`, the cascade-leg heart of settledness):
#print axioms graphRec_reconcileKeyD_inert
#print axioms wantEdge_reconcileKeyD_inert
#print axioms reconcileKeyD_edge_char
#print axioms reconcileStarsKeyD_edge_char

-- **W3d-1b — FAN-OUT COMPLETENESS (GraphIndex/CascadeStable.lean, 2026-07-11g).**
-- The cross-key re-reconcile hazard as a theorem, contrapositive form: a derived key
-- NOT in `cascadeKeys` after a logged write leg has its operand `graphRec` — hence
-- the pass guard `checkFn`/`coveredFn` — unchanged by the leg. Route: a changed
-- probe's new path factors through a routed edge (`nreaches_factor`) whose emitted
-- frontier row (`writeLoggedRules_edge_delta`) has the operand node in its reach
-- cone, putting the key in `affectedKeys` (`mem_affectedKeys`). Probes 3–4 stay dead
-- on plain edge targets (`reachedByW3d_edges_target_plain` — the fence the attack
-- found load-bearing: an OUT-of-fragment object-star write flips probe 3 at every
-- object while mapping no keys, `processor.py:604-605`). Plus `cascadeKeys` write-leg
-- monotonicity (dirty keys stay dirty until a cascade) and endpoint closure over the
-- whole interleaved chain. Standard axioms only:
#print axioms nreaches_factor
#print axioms writeLoggedRules_edge_delta
#print axioms reachedByW3d_edgesClosed
#print axioms reachedByW3d_edges_target_plain
#print axioms mem_affectedKeys
#print axioms writeLeg_reach_stable
#print axioms writeLeg_graphRec_stable
#print axioms writeLeg_checkFn_stable
#print axioms cascadeKeys_writeLeg_mono

-- **W3d-1b — the UNTAINTED-CORE SHADOW and the W3d read bridge
-- (GraphIndex/CascadeStable.lean, 2026-07-11g).** The W3a shadow does not extend
-- over diffing passes, so W3d gets a weaker projection: every W3d state differs
-- from a rules-ADMITTED state on the CURRENT store only in edges into terminal
-- derived R-nodes (`UntaintedShadow`), which no untainted probe traverses
-- (`shadow_reach_agree`). New content vs the W3c `CoreEq` shadow: the write-leg
-- ADMISSION transfer (`shadow_admitEdge_agree` — the cycle probe's back-reach
-- target is a closure subject node, never a `DerNode` on the fragment), so the
-- logged fold and the shadow's `writeRules` fold accept the same edges. Corollary:
-- **`checkFn_eq_sem_w3d`** — the pass guard equals `sem` at EVERY W3d state,
-- cascaded or not (attack `#eval`: guard = sem across a 6-write chain with three
-- deliberately uncascaded mid-transaction states; the DERIVED read is what goes
-- stale, not the guard). Standard axioms only:
#print axioms shadow_reach_agree
#print axioms shadow_admitEdge_agree
#print axioms untaintedShadow_foldAdmits
#print axioms untaintedShadow_applyD
#print axioms untaintedShadow_reconcileJobsD
#print axioms untaintedShadow_cascade
#print axioms reachedByW3d_shadow
#print axioms shadow_graphRec_agree
#print axioms checkFn_eq_sem_w3d

-- **W3d-1b — SETTLEDNESS TRANSPORT (GraphIndex/CascadeStable.lean, 2026-07-11g).**
-- Write legs cannot touch ANY derived key's representation: rows are write-inert
-- (`writeLoggedRules_residue`) and no rule-routed edge lands on a `RootBoolean`
-- R-node (`writeLeg_derived_inedges_eq` — model-level I5 exclusivity). The semantic
-- complement `writeLeg_sem_stable`: at an UNMAPPED key the write does not change
-- `sem` either — guard = `sem` on BOTH sides of the leg (the read bridge at both
-- stores) and the guard is stable (fan-out completeness) — the cross-key hazard's
-- absence, semantically. `SettledKey` (the soundness-side per-key predicate: row
-- members carry their `sem` verdicts, derived edges witness `sem`-true subjects)
-- transports across write legs at unmapped keys (`settledKey_writeLeg`) and across
-- cascades at untargeted keys (`settledKey_cascade_untargeted` — passes touch only
-- their own keys' rows/in-edges, store unchanged). Standard axioms only:
#print axioms writeLoggedRules_residue
#print axioms writeLeg_derived_inedges_eq
#print axioms writeLeg_sem_stable
#print axioms settledKey_writeLeg
#print axioms reconcileJobsD_other_key_fixed
#print axioms settledKey_cascade_untargeted

-- **W3d-1b CLOSED — TARGETED RE-SETTLEMENT, THE INVARIANT, `graph_correct_w3d`
-- (GraphIndex/CascadeSettle.lean, 2026-07-11h).** The coverage chain `ReachedByW3dC`
-- carries, per cascade job, the audit-enumeration coverage clauses (`W3dJobCoverage`
-- — `processor.py:394-441`; the edge-holder clause is attack-confirmed load-bearing:
-- a pre-leg STALE edge holder missing from `cands` survives the diff audit and
-- breaks `check = sem` at a fully-drained state). `settledComplete_cascade_targeted`:
-- a cascade leg RE-SETTLES every targeted key — the last targeting job wholesale-
-- rewrites the row and diff-audits the edges, guards read at mid-batch states where
-- `checkFn = sem`. `reachedByW3dC_settled`: at EVERY chain state, every declared
-- derived key is dirty (`∈ cascadeKeys`) or `SettledKey ∧ CompleteKey`. At a
-- fully-drained state (`cascadeKeys = []` — what every accepted cascade produces,
-- `cascade_drains` + `cascadeKeys_nil_of_quiescent`) all keys are settled, giving
-- **`graph_correct_w3d`**: `check = sem` for bare/star-BARE/userset subjects at any
-- state of the interleaved scheduler chain — writes, outbox fan-out, cascades, and
-- stale-edge retraction all inside the verified perimeter. T3/T6 corollaries
-- restated at W3d scope. Standard axioms only:
#print axioms reachedByW3d_schema
#print axioms reachedByW3d_reach_collapse_root
#print axioms reachedByW3dC_toW3d
#print axioms completeKey_writeLeg
#print axioms completeKey_cascade_untargeted
#print axioms reconcileJobsD_key_edge_sem
#print axioms settledComplete_cascade_targeted
#print axioms sem_nil_derived_false
#print axioms reachedByW3dC_settled
#print axioms cascadeKeys_nil_of_quiescent
#print axioms graph_correct_w3d
#print axioms backend_equivalence_w3d
#print axioms exclusion_effective_w3d
#print axioms no_ghost_grant_w3d

-- **W3d-1c (part 3a) — the STRUCTURAL invariant over the interleaved chain
-- (GraphIndex/CascadeInv.lean).** The structural half of the deferred T2a carry
-- `reachedByW3d_inv`: every W3d state satisfies `StructInv` (schema fixity, node
-- encoding, edge endpoint-closure, ACYCLICITY) with NO fragment hypotheses.
-- Acyclicity is free on the chain — every added edge is a cycle-rejecting `writeDirect`,
-- every removed edge only shrinks reach (`removeEdgePair`/`NReaches.mono_subset`). The
-- four I6 residue-hygiene clauses (which need the `RootBoolean`/terminality fragment)
-- remain the open half of `reachedByW3d_inv`. Standard axioms only:
#print axioms structInv_reconcileStarsKeyD
#print axioms structInv_runCascade
#print axioms reachedByW3d_structInv
#print axioms reachedByW3dC_structInv

end Zanzibar
