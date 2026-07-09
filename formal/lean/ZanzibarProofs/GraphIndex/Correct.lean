import ZanzibarProofs.GraphIndex.State
import ZanzibarProofs.Spec.WellDef

/-!
# T2 / T5 — the graph index computes `sem`, and its cascade converges

`SEMANTICS.md` §8 (T2a, T2b, T5). Phase 4.

**Status (concretize + partial pass).** The graph model is now concrete
(`State.lean`): `GraphState`, `GraphModel.check`, `Inv`, `ReachedBy`, `Quiescent`,
`GraphAccepts` are real definitions, not `opaque` placeholders. Off the concrete
`ReachedBy` (which bakes the in-transaction cascade into each write, §7.8 / A1):

* **`cascade_converges` (T5) is CLOSED** — outbox-drain quiescence is a `WriteStep`
  postcondition, so it holds at every reachable state by induction.
* **`graph_reached_inv` (T2a)**: its `Quiescent` conjunct is closed the same way; the
  `Inv` conjunct stays a tracked `sorry` (it needs the full operational write path —
  edge/bridge/reconcile — to be realized, the deferred T2a content).
* **`graph_correct` (T2b)** stays a tracked `sorry` — the read = `sem` completeness
  argument (≤4-probe reachability decomposition + residue algebra), resting on T4
  (edges = path counts) and the T1 MemberSet lemmas.
-/

namespace Zanzibar

/-- **T5 (cascade convergence).** Every reachable state is cascade-quiescent: the
    in-transaction cascade drains the outbox on every write, so the drain frontier
    covers all deltas at any state reached from empty. Each `but not` operand settles
    before any consumer reads it (encoded by `Quiescent` + the stratum order). -/
theorem cascade_converges (S : Schema) (T : Store) (σ : GraphState)
    (_hStrat : Stratifiable S) (_hAcc : GraphAccepts S) (hReach : ReachedBy σ S T) :
    Quiescent σ := by
  induction hReach with
  | empty S => exact quiescent_empty S
  | step t _hprev hstep _ih => exact hstep.drained

/-- **T2a (invariant preservation).** Every reachable graph state satisfies the
    I-series invariant and is cascade-quiescent (materialization = recompute from
    scratch). The `Quiescent` conjunct is `cascade_converges`; the `Inv` conjunct
    still needs the concrete write path (edge/bridge/reconcile maintenance) that
    `WriteStep` abstracts — tracked `sorry`. -/
theorem graph_reached_inv (S : Schema) (T : Store) (σ : GraphState)
    (_hWF : WF S) (hStrat : Stratifiable S) (hAcc : GraphAccepts S)
    (hReach : ReachedBy σ S T) :
    Inv S σ ∧ Quiescent σ := by
  refine ⟨?_, cascade_converges S T σ hStrat hAcc hReach⟩
  sorry

/-- **T2b (read correctness).** On any invariant-satisfying reachable state the
    graph read answers exactly the specification. Tracked `sorry`: the completeness
    argument (every semantic path decomposes as leading-hop · materialized-closure ·
    trailing-hop for the ≤4 probes; the residue fold reproduces the star×boolean
    table) resting on T4 + the T1 MemberSet lemmas. -/
theorem graph_correct (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (_hWF : WF S) (_hStrat : Stratifiable S) (_hAcc : GraphAccepts S)
    (_hInv : Inv S σ) (_hReach : ReachedBy σ S T) :
    GraphModel.check σ q = sem S T q := by
  sorry

end Zanzibar
