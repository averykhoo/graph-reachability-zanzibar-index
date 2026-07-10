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

end Zanzibar
