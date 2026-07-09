import ZanzibarProofs.SetEngine.Eval
import ZanzibarProofs.SetEngine.Contains
import ZanzibarProofs.Spec.WellDef

/-!
# T1 — the set engine computes `sem`

`SEMANTICS.md` §8 (T1). The concrete `SetEngineModel.check` (`Eval.lean`) expands the
query node into a `MemberSet` and probes it with `containsShape` at the query subject.
We prove that probe equals the pointwise specification `sem`, by induction on fuel and
then on the AST: boolean nodes collapse via the `containsShape_*_focus` distribution
laws (`Contains.lean`), leaves via the grant/parent correspondence with `sem`'s
`directLeaf`/`ttuLeaf`.

The query-focused population `popOf` makes the three modeling invariants
(`PopFocus`/`WFp`/`Grounded`) hold definitionally — see the `Eval.lean` header.
-/

namespace Zanzibar

open MemberSet SetEngineModel

variable {s : SubjectRef}

/-! ### The query-focused population satisfies the modeling invariants -/

theorem containsShape_empty (uid : SubjectRef) (shape : Shape) :
    containsShape (MemberSet.empty : MemberSet SubjectRef) uid shape = false := by
  simp [MemberSet.containsShape, MemberSet.empty]

/-- `popOf s` is focused at `(s, s.shape)`: the query is always at its own shape. -/
theorem popFocus_popOf (s : SubjectRef) : PopFocus (popOf s) s s.shape := by
  intro σ h
  unfold popOf at h
  by_cases hσ : σ = s.shape
  · exact hσ
  · simp [hσ] at h

/-- Every member set is `Grounded` at `(s, s.shape)` under `popOf s`, because
    `popOf s s.shape = {s}` contains `s` unconditionally. -/
theorem grounded_popOf (s : SubjectRef) (m : MemberSet SubjectRef) :
    Grounded (popOf s) s s.shape m := by
  intro _
  simp [popOf, Finset.mem_singleton]

/-! ### `WFp` for the leaves and the union fold -/

theorem wfp_empty (pop : Shape → Finset SubjectRef) :
    WFp pop (MemberSet.empty : MemberSet SubjectRef) := by
  unfold WFp MemberSet.empty; simp

theorem wfp_singletonEntity (pop : Shape → Finset SubjectRef) (uid : SubjectRef) :
    WFp pop (MemberSet.singletonEntity uid) := by
  unfold WFp MemberSet.singletonEntity MemberSet.starpop; simp

theorem wfp_star (pop : Shape → Finset SubjectRef) (shape : Shape) :
    WFp pop (MemberSet.star shape) := by
  unfold WFp MemberSet.star; simp

theorem wfp_unionFold (s : SubjectRef) (l : List (MemberSet SubjectRef)) :
    WFp (popOf s) (unionFold s l) := by
  induction l with
  | nil => exact wfp_empty _
  | cons x xs _ =>
      unfold unionFold
      rw [List.foldr_cons]
      exact wfp_union _ _ _

/-- Probing a `union`-fold at `(s, s.shape)` is the `any` of the probes, given the
    elements are `WFp` (the fold itself and each leaf are). -/
theorem containsShape_unionFold (s : SubjectRef) (l : List (MemberSet SubjectRef))
    (hw : ∀ m ∈ l, WFp (popOf s) m) :
    containsShape (unionFold s l) s s.shape = l.any (fun m => containsShape m s s.shape) := by
  induction l with
  | nil => simp [unionFold, containsShape_empty]
  | cons x xs ih =>
      have hx := hw x List.mem_cons_self
      have hrest := wfp_unionFold s xs
      have hxs : ∀ m ∈ xs, WFp (popOf s) m := fun m hm => hw m (List.mem_cons_of_mem _ hm)
      unfold unionFold
      rw [List.foldr_cons]
      rw [show xs.foldr (MemberSet.union (popOf s)) MemberSet.empty = unionFold s xs from rfl]
      rw [containsShape_union_focus (popFocus_popOf s) hx hrest]
      rw [ih hxs]
      simp [List.any_cons]

/-! ### Leaf probes and list helpers -/

theorem containsShape_star (shape' : Shape) (uid : SubjectRef) (shape : Shape) :
    containsShape (MemberSet.star shape') uid shape = decide (shape = shape') := by
  simp [MemberSet.containsShape, MemberSet.star]

theorem containsShape_singletonEntity (uid0 uid : SubjectRef) (shape : Shape) :
    containsShape (MemberSet.singletonEntity uid0) uid shape = decide (uid = uid0) := by
  simp [MemberSet.containsShape, MemberSet.singletonEntity]

/-- `any` distributes over a pointwise `||`. -/
theorem any_or_distrib {α} (l : List α) (p q : α → Bool) :
    l.any (fun x => p x || q x) = (l.any p || l.any q) := by
  induction l with
  | nil => rfl
  | cons x xs ih =>
      simp only [List.any_cons, ih]
      cases p x <;> cases q x <;> cases xs.any p <;> cases xs.any q <;> rfl

theorem wfp_grantMS (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef) (g : Tuple) :
    WFp (popOf s) (grantMS s T q rc g) := by
  unfold grantMS
  dsimp only
  split_ifs
  · exact wfp_star _ _
  · exact wfp_union _ _ _
  · exact wfp_singletonEntity _ _
  · exact wfp_union _ _ _

theorem wfp_parentMS (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef) (targetRel : String) (tup : Tuple) :
    WFp (popOf s) (parentMS s T q rc targetRel tup) := by
  unfold parentMS
  dsimp only
  split_ifs
  · exact wfp_union _ _ _
  · exact wfp_union _ _ _

/-! ### The direct-leaf correspondence -/

/-- The probe of one grant's member set equals its match part `||` its flow part. -/
theorem containsShape_grantMS (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef) (rec : Rec)
    (HR : ∀ ot on rel, containsShape (rc ot on rel) s s.shape = rec ot on rel)
    (HW : ∀ ot on rel, WFp (popOf s) (rc ot on rel)) (g : Tuple) :
    containsShape (grantMS s T q rc g) s s.shape = (grantMatch s g || grantFlow rec T q g) := by
  unfold grantMS
  dsimp only
  split_ifs with h1 h2 h2
  · -- wildcard bare
    rw [containsShape_star]
    unfold grantMatch grantFlow; simp_all
  · -- wildcard userset
    rw [containsShape_union_focus (popFocus_popOf s) (wfp_star _ _) (wfp_unionFold s _),
        containsShape_star,
        containsShape_unionFold s _
          (fun m hm => by rw [List.mem_map] at hm; obtain ⟨i, _, rfl⟩ := hm; exact HW _ _ _),
        List.any_map]
    unfold grantMatch grantFlow; simp_all [Function.comp_def, HR]
  · -- concrete bare
    rw [containsShape_singletonEntity]
    unfold grantMatch grantFlow; simp_all
  · -- concrete userset
    rw [containsShape_union_focus (popFocus_popOf s) (wfp_singletonEntity _ _) (HW _ _ _),
        containsShape_singletonEntity, HR]
    unfold grantMatch grantFlow; simp_all

/-- `memberOfGranted` is exactly the `any` of the per-grant flow parts. -/
theorem memberOfGranted_eq (rec : Rec) (T : Store) (q : Query) (grants : List Tuple) :
    memberOfGranted rec T q grants = grants.any (fun g => grantFlow rec T q g) := rfl

/-- Pointwise congruence for `List.any`. -/
theorem any_ext {α} (l : List α) (f g : α → Bool) (h : ∀ x, f x = g x) :
    l.any f = l.any g := by rw [funext h]

/-- Prove a `Bool` equation from the equivalence of its truth. -/
theorem bool_eq_of_iff {a b : Bool} (h : a = true ↔ b = true) : a = b := by
  cases a <;> cases b <;> simp_all

/-- Componentwise equality for subject refs (no auto-generated `ext_iff`). -/
theorem SubjectRef.eq_iff (a b : SubjectRef) :
    a = b ↔ a.type = b.type ∧ a.name = b.name ∧ a.predicate = b.predicate := by
  constructor
  · rintro rfl; exact ⟨rfl, rfl, rfl⟩
  · obtain ⟨_, _, _⟩ := a; obtain ⟨_, _, _⟩ := b; rintro ⟨rfl, rfl, rfl⟩; rfl

set_option maxRecDepth 8000 in
/-- **T1 direct leaf.** The set-engine expansion of a `Direct` leaf, probed at the
    query subject, equals `sem`'s `directLeaf`. -/
theorem containsShape_expandDirect (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef) (rec : Rec)
    (HR : ∀ ot on rel, containsShape (rc ot on rel) s s.shape = rec ot on rel)
    (HW : ∀ ot on rel, WFp (popOf s) (rc ot on rel))
    (rs : List Restriction) (ot on rel : String) :
    containsShape (expandDirect s T q rc rs ot on rel) s s.shape
      = directLeaf rec s T q rs ot on rel := by
  unfold expandDirect
  rw [containsShape_unionFold s _
        (fun m hm => by rw [List.mem_map] at hm; obtain ⟨g, _, rfl⟩ := hm; exact wfp_grantMS s T q rc g),
      List.any_map]
  simp only [Function.comp_def, containsShape_grantMS s T q rc rec HR HW]
  unfold directLeaf
  simp only [memberOfGranted_eq]
  split_ifs with hs hb
  · -- star subject
    rw [← any_or_distrib]
    apply any_ext; intro g
    have hs' : s.name = STAR := by simpa using hs
    congr 1
    unfold grantMatch
    simp only [SubjectRef.shape]
    split_ifs with hn hp hp <;>
      apply bool_eq_of_iff <;>
      simp_all only [beq_iff_eq, bne_iff_ne, ne_eq, Bool.and_eq_true, Bool.or_eq_true,
        Bool.not_eq_true, decide_eq_true_eq, SubjectRef.eq_iff, Prod.mk.injEq] <;>
      first | tauto | aesop
  · -- bare concrete subject
    rw [← any_or_distrib]
    apply any_ext; intro g
    have hs' : ¬ s.name = STAR := by simpa using hs
    have hb' : s.predicate = BARE := by simpa using hb
    congr 1
    unfold grantMatch
    simp only [SubjectRef.shape]
    split_ifs with hn hp hp <;>
      apply bool_eq_of_iff <;>
      simp_all only [beq_iff_eq, bne_iff_ne, ne_eq, Bool.and_eq_true, Bool.or_eq_true,
        Bool.not_eq_true, decide_eq_true_eq, SubjectRef.eq_iff, Prod.mk.injEq] <;>
      first | tauto | aesop
  · -- userset subject
    rw [← any_or_distrib]
    apply any_ext; intro g
    have hs' : ¬ s.name = STAR := by simpa using hs
    have hb' : ¬ s.predicate = BARE := by simpa using hb
    congr 1
    unfold grantMatch
    simp only [SubjectRef.shape]
    split_ifs with hn hp hp <;>
      apply bool_eq_of_iff <;>
      simp_all only [beq_iff_eq, bne_iff_ne, ne_eq, Bool.and_eq_true, Bool.or_eq_true,
        Bool.not_eq_true, decide_eq_true_eq, SubjectRef.eq_iff, Prod.mk.injEq] <;>
      first | tauto | aesop

/-! ### The TTU-leaf correspondence -/

/-- `any` over a guarded body equals `any` of the body over the filtered list. -/
theorem any_filter_guard {α} (l : List α) (p b : α → Bool) :
    l.any (fun x => if p x then b x else false) = (l.filter p).any b := by
  induction l with
  | nil => rfl
  | cons x xs ih =>
      simp only [List.any_cons, List.filter_cons]
      by_cases h : p x = true <;> simp [h, List.any_cons, ih]

/-- **T1 TTU leaf.** The set-engine expansion of a TTU leaf, probed at the query
    subject, equals `sem`'s `ttuLeaf`. -/
theorem containsShape_expandTtu (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef) (rec : Rec)
    (HR : ∀ ot on rel, containsShape (rc ot on rel) s s.shape = rec ot on rel)
    (HW : ∀ ot on rel, WFp (popOf s) (rc ot on rel))
    (tr ts ot on : String) :
    containsShape (expandTtu s T q rc tr ts ot on) s s.shape = ttuLeaf rec s T q tr ts ot on := by
  unfold expandTtu
  rw [containsShape_unionFold s _
        (fun m hm => by rw [List.mem_map] at hm; obtain ⟨tup, _, rfl⟩ := hm; exact wfp_parentMS s T q rc tr tup),
      List.any_map]
  unfold ttuLeaf ttuParents
  dsimp only
  rw [any_filter_guard]
  apply any_ext; intro tup
  simp only [Function.comp_def]
  by_cases hstar : (tup.subject.name == STAR) = true
  · -- wildcard parent
    unfold parentMS; dsimp only; rw [if_pos hstar]
    rw [containsShape_union_focus (popFocus_popOf s) (wfp_star _ _) (wfp_unionFold s _),
        containsShape_star,
        containsShape_unionFold s _
          (fun m hm => by rw [List.mem_map] at hm; obtain ⟨i, _, rfl⟩ := hm; exact HW _ _ _),
        List.any_map]
    simp_all [Function.comp_def, HR, SubjectRef.shape, bne, beq_eq_decide]
  · -- concrete parent
    unfold parentMS; dsimp only; rw [if_neg hstar]
    rw [containsShape_union_focus (popFocus_popOf s) (wfp_singletonEntity _ _) (HW _ _ _),
        containsShape_singletonEntity, HR]
    apply bool_eq_of_iff
    simp only [bne, hstar, beq_eq_false_iff_ne, ne_eq, not_false_eq_true, if_true, decide_not]
    simp_all [beq_iff_eq, SubjectRef.eq_iff, Prod.mk.injEq, and_assoc]

/-! ### The structural and fuel inductions -/

/-- Every expansion output is `WFp` under `popOf s` (leaves and boolean folds all
    produce `normalize`d sets), given the recursive expander is. -/
theorem wfp_expandE (S : Schema) (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef)
    (HW : ∀ ot on rel, WFp (popOf s) (rc ot on rel)) (ot on rel : String) (e : Expr) :
    WFp (popOf s) (expandE S s T q rc ot on rel e) := by
  cases e with
  | union a b => exact wfp_union _ _ _
  | inter a b => exact wfp_intersect _ _ _
  | excl b sub => exact wfp_subtract _ _ _
  | computed r => exact HW ot on r
  | direct rs => exact wfp_unionFold s _
  | ttu tr ts => exact wfp_unionFold s _

/-- **T1 structural step.** For a fixed recursive expander `rc` matching `rec`
    pointwise (`HR`), the expansion of any `Expr`, probed at the query subject, equals
    `sem`'s `evalE`. Boolean nodes use the `containsShape_*_focus` distribution laws;
    leaves the direct/TTU correspondences; `computed` is `HR`. -/
theorem containsShape_expandE (S : Schema) (s : SubjectRef) (T : Store) (q : Query)
    (rc : String → String → String → MemberSet SubjectRef) (rec : Rec)
    (HR : ∀ ot on rel, containsShape (rc ot on rel) s s.shape = rec ot on rel)
    (HW : ∀ ot on rel, WFp (popOf s) (rc ot on rel))
    (ot on rel : String) (e : Expr) :
    containsShape (expandE S s T q rc ot on rel e) s s.shape = evalE rec s T q ot on rel e := by
  induction e with
  | union a b iha ihb =>
      simp only [expandE, evalE]
      rw [containsShape_union_focus (popFocus_popOf s)
            (wfp_expandE S s T q rc HW ot on rel a) (wfp_expandE S s T q rc HW ot on rel b),
          iha, ihb]
  | inter a b iha ihb =>
      simp only [expandE, evalE]
      rw [containsShape_intersect_focus (popFocus_popOf s)
            (wfp_expandE S s T q rc HW ot on rel a) (wfp_expandE S s T q rc HW ot on rel b)
            (grounded_popOf s _) (grounded_popOf s _),
          iha, ihb]
  | excl b sub ihb ihsub =>
      simp only [expandE, evalE]
      rw [containsShape_subtract_focus (popFocus_popOf s)
            (wfp_expandE S s T q rc HW ot on rel b) (wfp_expandE S s T q rc HW ot on rel sub)
            (grounded_popOf s _) (grounded_popOf s _),
          ihb, ihsub]
  | computed r => simp only [expandE, evalE]; exact HR ot on r
  | direct rs => exact containsShape_expandDirect s T q rc rec HR HW rs ot on rel
  | ttu tr ts => exact containsShape_expandTtu s T q rc rec HR HW tr ts ot on

/-- Every fuel-bounded expansion output is `WFp` under `popOf s`. -/
theorem wfp_expandAux (S : Schema) (s : SubjectRef) (T : Store) (q : Query)
    (fuel : Nat) (ot on rel : String) :
    WFp (popOf s) (expandAux S s T q fuel ot on rel) := by
  induction fuel generalizing ot on rel with
  | zero => simp only [expandAux]; exact wfp_empty _
  | succ n ih =>
      simp only [expandAux, expandStep]
      cases S.lookup (ot, rel) with
      | none => exact wfp_empty _
      | some e => exact wfp_expandE S s T q _ ih ot on rel e

/-- **T1 fuel step.** At any fuel, the expander probed at the query subject equals
    `semAux` — by induction on fuel (`expandStep`/`step` share the `lookup` split, the
    body is `containsShape_expandE` with the fuel-`IH` as `HR`). -/
theorem containsShape_expandAux (S : Schema) (s : SubjectRef) (T : Store) (q : Query)
    (fuel : Nat) (ot on rel : String) :
    containsShape (expandAux S s T q fuel ot on rel) s s.shape = semAux S s T q fuel ot on rel := by
  induction fuel generalizing ot on rel with
  | zero => simp only [expandAux, semAux, containsShape_empty]
  | succ n ih =>
      simp only [expandAux, semAux, expandStep, step]
      cases S.lookup (ot, rel) with
      | none => simp only [containsShape_empty]
      | some e =>
          exact containsShape_expandE S s T q (expandAux S s T q n) (semAux S s T q n)
            ih (wfp_expandAux S s T q n) ot on rel e

/-- Every stored tuple is write-valid (`hValid`, §8). -/
def AllValid (T : Store) : Prop :=
  ∀ tup ∈ T, ValidIdent tup.subject.type ∧ ValidIdent tup.relation ∧ ValidIdent tup.object.type

/-- **T1.** The set-engine model answers exactly the specification.

    Note the well-formedness / stratifiability / validity hypotheses are *not needed*:
    the concrete expansion computes `semAux` at every fuel, and the two run at the same
    `fuelBound`, so equality is unconditional. They are retained (underscored) to match
    the theorem statement `backend_equivalence` routes through. -/
theorem setEngine_correct (S : Schema) (T : Store) (q : Query)
    (_hWF : WF S) (_hStrat : Stratifiable S) (_hValid : AllValid T) :
    SetEngineModel.check S T q = sem S T q := by
  unfold SetEngineModel.check sem
  exact containsShape_expandAux S q.subject T q (fuelBound S T)
    q.object.type q.object.name q.relation

end Zanzibar
