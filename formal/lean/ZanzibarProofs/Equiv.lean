import ZanzibarProofs.SetEngine.Correct
import ZanzibarProofs.GraphIndex.Correct

/-!
# T3 / T6 — equivalence and the security corollaries

`SEMANTICS.md` §8 (T3, T6). T3 is the whole point of the shared-spec architecture:
prove each backend against `sem`, get backend-equivalence by transitivity in Lean.
T6 are the review's headline security properties, one-line consequences of T1/T2b.
-/

namespace Zanzibar

/-- **T3 (equivalence).** On states reached by writing exactly `T`, the two backends
    agree — by transitivity through `sem` (T1 ∘ T2b). Proved in Phase 5. -/
theorem backend_equivalence (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hStrat : Stratifiable S) (hAcc : GraphAccepts S)
    (hInv : Inv S σ) (hReach : ReachedBy σ S T) (hValid : AllValid T) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hWF hStrat hValid,
      graph_correct S T σ q hWF hStrat hAcc hInv hReach]

/-!
## T6 — security corollaries

Stated as named theorems because they are the review's headline properties. Each
is a one-line consequence of T1/T2b + a spec lemma. Proofs in Phase 5.
-/

/-- **T6a (exclusion-effectiveness).** If the spec places the subject in an
    exclusion's subtrahend so `sem` denies, both backends deny — a `but not banned`
    always removes a banned subject. Stated as: whenever `sem` is false, so are both
    model reads (the general soundness direction restricted to the exclusion case). -/
theorem exclusion_effective (S : Schema) (T : Store) (σ : GraphState) (q : Query)
    (hWF : WF S) (hStrat : Stratifiable S) (hAcc : GraphAccepts S)
    (hInv : Inv S σ) (hReach : ReachedBy σ S T) (hValid : AllValid T)
    (hDeny : sem S T q = false) :
    SetEngineModel.check S T q = false ∧ GraphModel.check σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correct S T q hWF hStrat hValid]; exact hDeny
  · rw [graph_correct S T σ q hWF hStrat hAcc hInv hReach]; exact hDeny

/-- **T6b (no-ghost-grant).** If removing a tuple makes the spec deny, both backends
    deny after the removal — no stale grant survives the loss of its last support.
    (`T'` is the post-removal store; `σ'` its reached state.) -/
theorem no_ghost_grant (S : Schema) (T' : Store) (σ' : GraphState) (q : Query)
    (hWF : WF S) (hStrat : Stratifiable S) (hAcc : GraphAccepts S)
    (hInv : Inv S σ') (hReach : ReachedBy σ' S T') (hValid : AllValid T')
    (hDeny : sem S T' q = false) :
    GraphModel.check σ' q = false := by
  rw [graph_correct S T' σ' q hWF hStrat hAcc hInv hReach]; exact hDeny

/-- **T6c (wildcard scoping).** A `Direct` restriction (in particular a `T:*` grant)
    matches a stored tuple only when the tuple's subject type is one of the
    restriction types — so a `T:*` grant can never leak to a subject of another type.
    Now a REAL proved theorem (was a placeholder), via `restrictionMatches_type`. Both
    backends inherit the property through T1/T2b + the shared leaf structure. -/
theorem wildcard_scoping (rs : List Restriction) (tup : Tuple)
    (h : restrictionMatches rs tup = true) : ∃ r ∈ rs, tup.subject.type = r.1 :=
  restrictionMatches_type rs tup h

end Zanzibar
