import ZanzibarProofs.Spec.Semantics

/-!
# T0a supporting lemmas — the fuel-stability convergence argument

`SEMANTICS.md` §8 (T0a). The remaining `sorry` (`semAux_fuel_stable_step` in
`Spec/WellDef.lean`) asserts that above `fuelBound`, one more unit of fuel does not
change the answer. This file collects the reusable *ingredients* of the intended
proof. It is deliberately kept separate from `WellDef.lean` so each ingredient is
independently checkable.

**Why the naive pigeonhole fails (ROADMAP correction, confirmed).** `semAux` has no
visited-set: `semAux (n+1) = Φ(semAux n)` applies the immediate-consequence operator
`Φ` *uniformly* at every level. `Φ` is **non-monotone** (`.excl b s = b && !s`), so
`Φⁿ(⊥)` need not stabilize by any state-count bound — pure pigeonhole only gives
eventual periodicity at ~`2^{#atoms}`. Stability by `fuelBound` genuinely needs
`Stratifiable`.

**The convergence argument (structure).**
1. Taint propagates upward, so **untainted keys reference only untainted keys**, and
   their expressions are exclusion-free — a purely *positive/monotone* fragment.
   `evalE_mono` below is the monotonicity step for that fragment; it converges by
   the number of reachable untainted atoms (which is what makes `fuelBound`
   multiplicative — the `deep_grid` case).
2. `depEdges` includes **all** references among tainted keys, and `Stratifiable`
   (Kahn) makes them a **DAG**. So each tainted key's `Φ` depends only on
   strictly-lower-rank tainted atoms + untainted atoms; once those are stable, the
   tainted rank stabilizes one fuel-step later.

Remaining to build (next pass): the finite *reachable-atom* set with a confinement
lemma (`semAux` depends only on `rec` there), the per-rank stabilization induction,
and the arithmetic that the total level fits under `|keys|·(2|T|+4)`.

This file supplies **ingredient 1** (untainted monotonicity) in full.
-/

namespace Zanzibar

/-- An expression free of exclusion (the untainted/positive fragment: `∪`, `∩`,
    leaves). `evalE` is monotone in `rec` exactly on these. -/
def Expr.noExcl : Expr → Prop
  | .excl _ _ => False
  | .union a b => a.noExcl ∧ b.noExcl
  | .inter a b => a.noExcl ∧ b.noExcl
  | .direct _ => True
  | .computed _ => True
  | .ttu _ _ => True

/-- A `rec` refinement: `rec1 ≤ rec2` pointwise on Bool (`false ≤ true`). -/
def RecLe (rec1 rec2 : Rec) : Prop :=
  ∀ o n r, rec1 o n r = true → rec2 o n r = true

/-- `memberOfGranted` uses `rec` only positively, so it preserves truth under `≤`. -/
theorem memberOfGranted_mono {rec1 rec2 : Rec} (h : RecLe rec1 rec2)
    (T : Store) (q : Query) (grants : List Tuple)
    (hm : memberOfGranted rec1 T q grants = true) :
    memberOfGranted rec2 T q grants = true := by
  unfold memberOfGranted at hm ⊢
  rw [List.any_eq_true] at hm ⊢
  obtain ⟨g, hg, hgt⟩ := hm
  refine ⟨g, hg, ?_⟩
  by_cases hb : g.subject.predicate == BARE
  · simp [hb] at hgt
  · by_cases hs : g.subject.name != STAR
    · simp only [hb, hs, Bool.false_eq_true, if_false, if_true] at hgt ⊢
      exact h _ _ _ hgt
    · simp only [hb, hs, Bool.false_eq_true, if_false] at hgt ⊢
      rw [List.any_eq_true] at hgt ⊢
      obtain ⟨inst, hi, hit⟩ := hgt
      exact ⟨inst, hi, h _ _ _ hit⟩

/-- `directLeaf` = `(rec-free grants match) || memberOfGranted rec`, hence monotone. -/
theorem directLeaf_mono {rec1 rec2 : Rec} (h : RecLe rec1 rec2)
    (subject : SubjectRef) (T : Store) (q : Query) (rs : List Restriction)
    (otype oname rel : String)
    (hd : directLeaf rec1 subject T q rs otype oname rel = true) :
    directLeaf rec2 subject T q rs otype oname rel = true := by
  dsimp only [directLeaf] at hd ⊢
  by_cases h1 : (subject.name == STAR) = true
  · rw [if_pos h1] at hd ⊢; rw [Bool.or_eq_true] at hd ⊢
    exact hd.imp id (memberOfGranted_mono h T q _)
  · rw [if_neg h1] at hd ⊢
    by_cases h2 : (subject.predicate == BARE) = true
    · rw [if_pos h2] at hd ⊢; rw [Bool.or_eq_true] at hd ⊢
      exact hd.imp id (memberOfGranted_mono h T q _)
    · rw [if_neg h2] at hd ⊢; rw [Bool.or_eq_true] at hd ⊢
      exact hd.imp id (memberOfGranted_mono h T q _)

/-- `ttuLeaf` uses `rec` only positively over stored parents, hence monotone. -/
theorem ttuLeaf_mono {rec1 rec2 : Rec} (h : RecLe rec1 rec2)
    (subject : SubjectRef) (T : Store) (q : Query)
    (tr ts otype oname : String)
    (ht : ttuLeaf rec1 subject T q tr ts otype oname = true) :
    ttuLeaf rec2 subject T q tr ts otype oname = true := by
  unfold ttuLeaf at ht ⊢
  rw [List.any_eq_true] at ht ⊢
  obtain ⟨tup, htup, htt⟩ := ht
  refine ⟨tup, htup, ?_⟩
  by_cases hcond : (tup.relation == ts && tup.object.type == otype &&
      (matchingObjects oname).contains tup.object.name)
  · by_cases hpn : tup.subject.name != STAR
    · simp only [hcond, hpn, if_true, Bool.or_eq_true] at htt ⊢
      rcases htt with htt | htt
      · exact Or.inl htt
      · exact Or.inr (h _ _ _ htt)
    · simp only [hcond, hpn, Bool.false_eq_true, if_false, if_true, Bool.or_eq_true] at htt ⊢
      rcases htt with htt | htt
      · exact Or.inl htt
      · rw [List.any_eq_true] at htt ⊢
        obtain ⟨inst, hi, hit⟩ := htt
        exact Or.inr ⟨inst, hi, h _ _ _ hit⟩
  · simp only [hcond, Bool.false_eq_true, if_false] at htt

/-- A schema whose every definition is exclusion-free (the fully-untainted /
    positive fragment — e.g. any pure-`direct` schema). On such a schema the whole
    evaluator is monotone in fuel (`semAux_mono` below). -/
def Schema.noExclAll (S : Schema) : Prop :=
  ∀ k e, S.lookup k = some e → e.noExcl

/-- **T0a ingredient 1 — untainted monotonicity.** On an exclusion-free expression,
    `evalE` preserves truth under a `rec` refinement: more derivable facts never
    retract a positive answer. This is the step of the T0a convergence argument that
    lets the untainted/positive fragment be treated as a monotone iteration. -/
theorem evalE_mono {rec1 rec2 : Rec} (h : RecLe rec1 rec2)
    (subject : SubjectRef) (T : Store) (q : Query) (otype oname rel : String) :
    ∀ e : Expr, e.noExcl →
      evalE rec1 subject T q otype oname rel e = true →
      evalE rec2 subject T q otype oname rel e = true := by
  intro e
  induction e with
  | union a b iha ihb =>
      intro hne he
      simp only [Expr.noExcl] at hne
      simp only [evalE, Bool.or_eq_true] at he ⊢
      rcases he with he | he
      · exact Or.inl (iha hne.1 he)
      · exact Or.inr (ihb hne.2 he)
  | inter a b iha ihb =>
      intro hne he
      simp only [Expr.noExcl] at hne
      simp only [evalE, Bool.and_eq_true] at he ⊢
      exact ⟨iha hne.1 he.1, ihb hne.2 he.2⟩
  | excl a b _ _ => intro hne _; simp only [Expr.noExcl] at hne
  | computed r => intro _ he; simp only [evalE] at he ⊢; exact h _ _ _ he
  | direct rs => intro _ he; exact directLeaf_mono h subject T q rs otype oname rel he
  | ttu tr ts => intro _ he; exact ttuLeaf_mono h subject T q tr ts otype oname he

/-! ## Fuel monotonicity of the evaluator on exclusion-free schemas

On a `Schema.noExclAll` schema every definition is a `noExcl` expression, so one
`step` is monotone in `rec` (`evalE_mono`), and hence `semAux` is monotone in fuel:
more fuel never retracts a positive answer. This is the evaluator-level form of
ingredient 1 — used by T2b's soundness direction (a membership chain found at its
own length's fuel persists to `fuelBound`) and by the eventual T0a untainted layer. -/

/-- One more unit of fuel never retracts a positive `semAux` answer (exclusion-free
    schema). -/
theorem semAux_le_succ (S : Schema) (hne : S.noExclAll) (subject : SubjectRef)
    (T : Store) (q : Query) :
    ∀ f, RecLe (semAux S subject T q f) (semAux S subject T q (f + 1)) := by
  intro f
  induction f with
  | zero => intro o n r h; simp [semAux] at h
  | succ f ih =>
    intro o n r h
    rw [semAux, step] at h ⊢
    cases hlk : S.lookup (o, r) with
    | none => rw [hlk] at h; simp at h
    | some e =>
      rw [hlk] at h
      exact evalE_mono ih subject T q o n r e (hne _ e hlk) h

/-- **Fuel monotonicity** (exclusion-free schema): a positive `semAux` answer at
    fuel `f` persists to any fuel `f' ≥ f`. -/
theorem semAux_mono (S : Schema) (hne : S.noExclAll) (subject : SubjectRef)
    (T : Store) (q : Query) {f f' : Nat} (hle : f ≤ f') :
    RecLe (semAux S subject T q f) (semAux S subject T q f') := by
  induction hle with
  | refl => exact fun _ _ _ h => h
  | step _ ih =>
    exact fun o n r h => semAux_le_succ S hne subject T q _ o n r (ih o n r h)

end Zanzibar
