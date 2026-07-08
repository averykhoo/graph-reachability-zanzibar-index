import ZanzibarProofs.SetEngine.Eval
import ZanzibarProofs.Spec.WellDef

/-!
# T1 — the set engine computes `sem`

`SEMANTICS.md` §8 (T1). Proved in Phase 3 by induction on strata then on the AST,
with the `MemberSet` algebra lemmas discharging each node type.
-/

namespace Zanzibar

/-- Every stored tuple is write-valid (`hValid`, §8). -/
def AllValid (T : Store) : Prop :=
  ∀ tup ∈ T, ValidIdent tup.subject.type ∧ ValidIdent tup.relation ∧ ValidIdent tup.object.type

/-- **T1.** The set-engine model answers exactly the specification. -/
theorem setEngine_correct (S : Schema) (T : Store) (q : Query)
    (_hWF : WF S) (_hStrat : Stratifiable S) (_hValid : AllValid T) :
    SetEngineModel.check S T q = sem S T q := by
  sorry

end Zanzibar
