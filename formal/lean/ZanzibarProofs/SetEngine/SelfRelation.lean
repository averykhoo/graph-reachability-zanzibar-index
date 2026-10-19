import ZanzibarProofs.SetEngine.Correct
import ZanzibarProofs.Spec.SelfRelation

/-!
# T1 for the spec `semR` — the set-engine model with the self-relation (TK144)

`src/zanzibar/setengine/engine.py::SetEngine.check.sat` applies OpenFGA's implicit userset
self-relation since TK144 (the oracle's disjunct, statement for statement). The model twin
is `expandStepR`: at a DECLARED node `(otype, oname, rel)` with a concrete name and a
non-`BARE` relation, the expansion is the rewrite's `MemberSet` UNIONED with the node's
own token `⟨otype, oname, rel⟩` -- outside the rewrite, so an enclosing `subtract` removes
it exactly as `semR`'s `but not` does. Everything below the step (`expandE`, the leaves,
the boolean folds, `containsShape_expandE`) is reused unchanged from `Eval.lean` /
`Correct.lean`.

As before (`CORRESPONDENCE.md` §2, `ZT-P4-2a`), the pin to the Python is ANSWER-FOR-ANSWER
with `SetEngine.check`: the Python `expand` applies the self-relation as a top-level,
`check`-decided correction (`::SetEngine._self_relation_corrected`), because its ids are
interned handles and a self token may have none; the model's tokens are `SubjectRef`s.
-/

namespace Zanzibar

open MemberSet SetEngineModel

namespace SetEngineModel

/-- `expandStep` with the self-relation (TK144): the node's own token joins its
    expansion, outside the rewrite. A `STAR` node name or a `BARE` relation names no
    concrete userset, so no token is added there (D1). -/
def expandStepR (S : Schema) (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef)
    (otype oname rel : String) : MemberSet SubjectRef :=
  match S.lookup (otype, rel) with
  | none => MemberSet.empty
  | some e =>
      if (rel != BARE && oname != STAR) = true then
        MemberSet.union (popOf s) (MemberSet.singletonEntity ⟨otype, oname, rel⟩)
          (expandE S s T q rc otype oname rel e)
      else expandE S s T q rc otype oname rel e

/-- The fuel-bounded reflexive expander (mirrors `semAuxR`). -/
def expandAuxR (S : Schema) (s : SubjectRef) (T : Store) (q : Query) :
    Nat → String → String → String → MemberSet SubjectRef
  | 0, _, _, _ => MemberSet.empty
  | fuel + 1, otype, oname, rel =>
      expandStepR S s T q (expandAuxR S s T q fuel) otype oname rel

/-- The set-engine `check` with the self-relation (TK144): expand, then probe. -/
def checkR (S : Schema) (T : Store) (q : Query) : Bool :=
  containsShape
    (expandAuxR S q.subject T q (fuelBound S T) q.object.type q.object.name q.relation)
    q.subject q.subject.shape

end SetEngineModel

/-- The self token, probed at the query subject, is the spec's `selfHit` -- under the
    step's guard (a concrete name, a non-`BARE` relation). -/
theorem decide_eq_selfHit (s : SubjectRef) (otype oname rel : String)
    (hg : (rel != BARE && oname != STAR) = true) :
    decide (s = (⟨otype, oname, rel⟩ : SubjectRef)) = selfHit s otype oname rel := by
  simp only [Bool.and_eq_true, bne_iff_ne, ne_eq] at hg
  obtain ⟨hb, hs⟩ := hg
  unfold selfHit
  by_cases h : s = ⟨otype, oname, rel⟩
  · subst h
    simp [hb, hs]
  · rw [decide_eq_false h]
    symm
    simp only [Bool.and_eq_false_iff, bne_eq_false_iff_eq, beq_eq_false_iff_ne, ne_eq]
    rcases s with ⟨t', n', p'⟩
    simp only [SubjectRef.mk.injEq, not_and] at h
    by_cases h1 : t' = otype
    · by_cases h2 : n' = oname
      · exact Or.inr (fun h3 => h h1 h2 h3)
      · exact Or.inl (Or.inr h2)
    · exact Or.inl (Or.inl (Or.inr h1))

/-- Off the step's guard the spec's disjunct is `false` too. -/
theorem selfHit_false_of_guard (s : SubjectRef) (otype oname rel : String)
    (hg : ¬ (rel != BARE && oname != STAR) = true) :
    selfHit s otype oname rel = false := by
  simp only [Bool.and_eq_true, bne_iff_ne, ne_eq, not_and, Decidable.not_not] at hg
  unfold selfHit
  by_cases hb : rel = BARE
  · subst hb; cases h : (s.predicate == BARE) <;> simp_all
  · have hs := hg hb
    subst hs; cases h : (s.name == STAR) <;> simp_all

theorem wfp_expandAuxR (S : Schema) (s : SubjectRef) (T : Store) (q : Query)
    (fuel : Nat) (ot on rel : String) :
    WFp (popOf s) (SetEngineModel.expandAuxR S s T q fuel ot on rel) := by
  induction fuel generalizing ot on rel with
  | zero => simp only [SetEngineModel.expandAuxR]; exact wfp_empty _
  | succ n ih =>
      simp only [SetEngineModel.expandAuxR, SetEngineModel.expandStepR]
      cases S.lookup (ot, rel) with
      | none => exact wfp_empty _
      | some e =>
          dsimp only
          split
          · exact wfp_union _ _ _
          · exact wfp_expandE S s T q _ ih ot on rel e

/-- **T1 fuel step, reflexively.** At any fuel the reflexive expander probed at the query
    subject is `semAuxR`. -/
theorem containsShape_expandAuxR (S : Schema) (s : SubjectRef) (T : Store) (q : Query)
    (fuel : Nat) (ot on rel : String) :
    containsShape (SetEngineModel.expandAuxR S s T q fuel ot on rel) s s.shape
      = semAuxR S s T q fuel ot on rel := by
  induction fuel generalizing ot on rel with
  | zero => simp only [SetEngineModel.expandAuxR, semAuxR, containsShape_empty]
  | succ n ih =>
      simp only [SetEngineModel.expandAuxR, semAuxR, SetEngineModel.expandStepR, stepR]
      cases S.lookup (ot, rel) with
      | none => simp only [containsShape_empty]
      | some e =>
          have hbody := containsShape_expandE S s T q (SetEngineModel.expandAuxR S s T q n)
            (semAuxR S s T q n) ih (wfp_expandAuxR S s T q n) ot on rel e
          dsimp only
          split
          · rename_i hg
            rw [containsShape_union_focus (popFocus_popOf s) (wfp_singletonEntity _ _)
                  (wfp_expandE S s T q _ (wfp_expandAuxR S s T q n) ot on rel e),
                containsShape_singletonEntity, hbody, decide_eq_selfHit s ot on rel hg]
          · rename_i hg
            rw [hbody, selfHit_false_of_guard s ot on rel hg, Bool.false_or]

/-- **T1 for the spec (TK144).** The reflexive set-engine model answers exactly `semR`,
    unconditionally, like `setEngine_correct` for `sem`. -/
theorem setEngine_correctR (S : Schema) (T : Store) (q : Query) :
    SetEngineModel.checkR S T q = semR S T q := by
  unfold SetEngineModel.checkR semR
  exact containsShape_expandAuxR S q.subject T q (fuelBound S T)
    q.object.type q.object.name q.relation

end Zanzibar
