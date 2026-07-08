import ZanzibarProofs.GraphIndex.State
import ZanzibarProofs.Spec.WellDef

/-!
# T2 / T5 — the graph index computes `sem`, and its cascade converges

`SEMANTICS.md` §8 (T2a, T2b, T5). Proved in Phase 4.
-/

namespace Zanzibar

/-- **T2a (invariant preservation).** Every reachable graph state satisfies the
    I-series invariant and is cascade-quiescent (materialization = recompute from
    scratch). -/
theorem graph_reached_inv (S : Schema) (T : Store) (σ : GraphState)
    (_hWF : WF S) (_hStrat : Stratifiable S) (_hAcc : GraphAccepts S)
    (_hReach : ReachedBy σ S T) :
    Inv S σ ∧ Quiescent σ := by
  sorry

/-- **T2b (read correctness).** On any invariant-satisfying reachable state the
    graph read answers exactly the specification. -/
theorem graph_correct (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (_hWF : WF S) (_hStrat : Stratifiable S) (_hAcc : GraphAccepts S)
    (_hInv : Inv S σ) (_hReach : ReachedBy σ S T) :
    GraphModel.check σ q = sem S T q := by
  sorry

/-- **T5 (cascade convergence).** The in-transaction cascade lands on the
    stratified fixpoint — reachable states are quiescent (subsumed by T2a; stated
    separately as the headline IVM property). Each `but not` operand settles before
    any consumer reads it (encoded by `Quiescent` + stratum order). -/
theorem cascade_converges (S : Schema) (T : Store) (σ : GraphState)
    (_hStrat : Stratifiable S) (_hAcc : GraphAccepts S) (_hReach : ReachedBy σ S T) :
    Quiescent σ := by
  sorry

end Zanzibar
