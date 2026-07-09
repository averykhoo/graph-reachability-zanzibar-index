import ZanzibarProofs.Equiv
import ZanzibarProofs.SetEngine.Algebra
import ZanzibarProofs.SetEngine.Contains
import ZanzibarProofs.Spec.FuelStable
import ZanzibarProofs.GraphIndex.Write
import ZanzibarProofs.GraphIndex.DirectCorrect
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
-- T5 — cascade convergence (GraphIndex/Correct.lean), closed off the concrete
-- `ReachedBy`; plus the concrete graph-model base-case lemmas. Expect only the
-- three standard axioms (no `sorryAx`):
#print axioms cascade_converges
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
#print axioms structInv_writeDirect
#print axioms inv_writeDirect
#print axioms residueEmpty_writeDirect
#print axioms writeDirect_writeStep
#print axioms reachedByDirect_inv
#print axioms reachedBy_of_direct
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
#print axioms graph_correct_direct

-- Proved modulo a documented sorry / opaque model — expect `sorryAx` and/or the
-- opaque model constants (these are the tracked debts, not final):
#print axioms sem_fuel_stable
#print axioms backend_equivalence

end Zanzibar
