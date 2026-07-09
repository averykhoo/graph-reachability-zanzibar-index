import ZanzibarProofs.Spec.Semantics
import ZanzibarProofs.Spec.Stratify

/-!
# Consultation confinement — the store-validity hypothesis and the relevant-atom space

Supporting layer for T0a (`Spec/WellDef.lean`). The fuel-stability theorem is FALSE
over an arbitrary `Store` (see `Spec/Counterexample.lean`): `ttuLeaf` consults `rec`
at the subject type of *stored* tupleset tuples without any restriction check, so an
admission-invalid tuple creates a consultation edge that `exprRefs`/`depEdges` never
see — and such an edge can close an exclusion cycle that stratification misses,
making `semAux` oscillate forever.

The fix is the *documented* precondition (`SEMANTICS.md` §8: stores hold write-valid
tuples): the real system's admission gate (`setengine/engine.py:_validate` step (2),
shared with the graph backend) rejects any tuple that matches no declared type
restriction of its `(object.type, relation)`. `StoreDeclared` below is the piece of
that gate the confinement argument needs: every stored tuple's subject type is among
the declared `Direct`-restriction types of its (declared) relation. It is *implied
by* admission validity, so stating theorems over it keeps them applicable to every
store the composed system can actually hold.

With it, every `rec`-consultation of the evaluator is confined to
`exprRefs S · ×  relevantNames T q` — the finite atom space the T0a convergence
argument counts over.
-/

namespace Zanzibar

/-- Every name occurring in a subject or object position of the store. The
    evaluator only ever consults `rec` at stored names (grants' subject names,
    `instances` witnesses, TTU parents) or at the query object's own name. -/
def storedNames (T : Store) : List String :=
  T.flatMap (fun t => [t.subject.name, t.object.name])

/-- The names the evaluation of `q` over `T` can ever consult `rec` at:
    the query object's name (kept by `computed` steps) plus the stored names. -/
def relevantNames (T : Store) (q : Query) : List String :=
  q.object.name :: storedNames T

/-- **Store admission-validity (the type-restriction clause).** Every stored tuple's
    `(object.type, relation)` is a declared relation whose definition names the
    tuple's subject type in one of its `Direct` restrictions.

    This is implied by the Python admission gate (`engine.py:_validate` (2): a write
    matching no declared type restriction raises), so every store the composed
    system can hold satisfies it. It is exactly what confines `ttuLeaf`'s parent
    consultations to `exprRefs`: without it the consultation graph can leave the
    dependency graph and T0a is FALSE (`Spec/Counterexample.lean`). -/
def StoreDeclared (S : Schema) (T : Store) : Prop :=
  ∀ tup ∈ T, ∃ e, S.lookup (tup.object.type, tup.relation) = some e ∧
    tup.subject.type ∈ directTypes e

/-! ## Name confinement: everything `rec` is consulted at is a stored name or `oname` -/

theorem anyCongr {α} {l : List α} {f g : α → Bool}
    (h : ∀ x ∈ l, f x = g x) : l.any f = l.any g := by
  induction l with
  | nil => rfl
  | cons a t ih =>
      simp only [List.any_cons, h a (List.mem_cons_self ..),
        ih (fun x hx => h x (List.mem_cons_of_mem _ hx))]

theorem subjectName_mem_storedNames {T : Store} {g : Tuple} (hg : g ∈ T) :
    g.subject.name ∈ storedNames T :=
  List.mem_flatMap.mpr ⟨g, hg, by simp⟩

theorem objectName_mem_storedNames {T : Store} {g : Tuple} (hg : g ∈ T) :
    g.object.name ∈ storedNames T :=
  List.mem_flatMap.mpr ⟨g, hg, by simp⟩

/-- The `∃`-witness population consists of stored names only (`instances`
    excludes query endpoints by construction). -/
theorem instances_subset_storedNames (T : Store) (q : Query) (t : String) :
    ∀ x ∈ instances T q t, x ∈ storedNames T := by
  intro x hx
  unfold instances universeOf at hx
  simp only [if_neg (Bool.false_ne_true), List.append_nil, List.mem_dedup] at hx
  induction T with
  | nil => simpa using hx
  | cons tup rest ih =>
      simp only [List.foldr_cons] at hx
      have hsplit : ∀ {y : String} {acc : List String},
          y ∈ (if tup.object.type = t ∧ tup.object.name ≠ STAR
                then tup.object.name :: acc else acc) →
          y = tup.object.name ∨ y ∈ acc := by
        intro y acc hy
        split at hy
        · rcases List.mem_cons.mp hy with h | h
          · exact Or.inl h
          · exact Or.inr h
        · exact Or.inr hy
      rcases hsplit hx with rfl | hx1
      · exact objectName_mem_storedNames (List.mem_cons_self ..)
      · have hsplit2 : x = tup.subject.name ∨
            x ∈ rest.foldr (fun tup acc =>
              let acc := if tup.subject.type = t ∧ tup.subject.name ≠ STAR
                         then tup.subject.name :: acc else acc
              if tup.object.type = t ∧ tup.object.name ≠ STAR
              then tup.object.name :: acc else acc) [] := by
          split at hx1
          · rcases List.mem_cons.mp hx1 with h | h
            · exact Or.inl h
            · exact Or.inr h
          · exact Or.inr hx1
        rcases hsplit2 with rfl | hx2
        · exact subjectName_mem_storedNames (List.mem_cons_self ..)
        · have hrest := ih hx2
          unfold storedNames at hrest ⊢
          rw [List.flatMap_cons]
          exact List.mem_append_right _ hrest

/-! ## Undeclared keys are constantly `false` -/

theorem lookup_eq_none (S : Schema) {k : String × String} (hk : k ∉ S.keys) :
    S.lookup k = none := by
  unfold Schema.lookup
  cases hf : S.defs.find? (fun p => p.1 = k) with
  | none => rfl
  | some p =>
      have hpk : p.1 = k := by simpa using List.find?_some hf
      have hmem : p ∈ S.defs := List.mem_of_find?_eq_some hf
      exact absurd (hpk ▸ List.mem_map.mpr ⟨p, hmem, rfl⟩) hk

theorem semAux_undeclared (S : Schema) (subject : SubjectRef) (T : Store) (q : Query)
    {t r : String} (hk : (t, r) ∉ S.keys) :
    ∀ f m, semAux S subject T q f t m r = false
  | 0, _ => rfl
  | f + 1, m => by rw [semAux, step, lookup_eq_none S hk]

/-! ## Key confinement certificates for the leaves -/

theorem grantsOf_mem {T : Store} {rs : List Restriction} {otype oname rel : String}
    {g : Tuple} (hg : g ∈ grantsOf T rs otype oname rel) :
    g ∈ T ∧ restrictionMatches rs g = true := by
  unfold grantsOf at hg
  have := List.mem_filter.mp hg
  refine ⟨this.1, ?_⟩
  have hp := this.2
  simp only [Bool.and_eq_true] at hp
  exact hp.2

/-- A restriction-matched grant with a userset subject is consulted at a key the
    `Direct` leaf's `exprRefs` predicts. -/
theorem restrictionMatches_exprRefs {S : Schema} {t : String} {rs : List Restriction}
    {g : Tuple} (hm : restrictionMatches rs g = true)
    (hbne : g.subject.predicate ≠ BARE) :
    (g.subject.type, g.subject.predicate) ∈ exprRefs S t (.direct rs) := by
  unfold restrictionMatches at hm
  obtain ⟨r, hr, hp⟩ := List.any_eq_true.mp hm
  simp only [Bool.and_eq_true, beq_iff_eq] at hp
  refine List.mem_filterMap.mpr ⟨r, hr, ?_⟩
  rw [if_neg (by rw [← hp.1.2]; exact hbne)]
  rw [hp.1.1, hp.1.2]

/-! ## The congruence lemmas — `rec1`/`rec2` agreeing on consulted atoms evaluate equal -/

/-- `memberOfGranted` congruence, hypothesis per grant: agreement at the grant's
    userset key, at the grant's own name or any stored name. -/
theorem memberOfGranted_congr {rec1 rec2 : Rec} (T : Store) (q : Query)
    (grants : List Tuple)
    (h : ∀ g ∈ grants, g.subject.predicate ≠ BARE → ∀ m,
        (m = g.subject.name ∨ m ∈ storedNames T) →
        rec1 g.subject.type m g.subject.predicate
          = rec2 g.subject.type m g.subject.predicate) :
    memberOfGranted rec1 T q grants = memberOfGranted rec2 T q grants := by
  unfold memberOfGranted
  refine anyCongr (fun g hg => ?_)
  by_cases hb : (g.subject.predicate == BARE) = true
  · simp [hb]
  · have hbne : g.subject.predicate ≠ BARE := by
      simpa [beq_iff_eq] using hb
    by_cases hs : (g.subject.name != STAR) = true
    · simp only [hb, hs, Bool.false_eq_true, if_false, if_true]
      exact h g hg hbne _ (Or.inl rfl)
    · simp only [hb, hs, Bool.false_eq_true, if_false]
      refine anyCongr (fun inst hi => ?_)
      exact h g hg hbne inst (Or.inr (instances_subset_storedNames T q _ inst hi))

/-- `directLeaf` congruence: agreement on the leaf's `exprRefs` × (own name ∪
    stored names). Needs no store hypothesis — `grantsOf` restriction-filters. -/
theorem directLeaf_congr {rec1 rec2 : Rec} (S : Schema) (subject : SubjectRef)
    (T : Store) (q : Query) (rs : List Restriction) (otype oname rel : String)
    (h : ∀ t' m r', (t', r') ∈ exprRefs S otype (.direct rs) →
        (m = oname ∨ m ∈ storedNames T) → rec1 t' m r' = rec2 t' m r') :
    directLeaf rec1 subject T q rs otype oname rel
      = directLeaf rec2 subject T q rs otype oname rel := by
  have hmog : memberOfGranted rec1 T q (grantsOf T rs otype oname rel)
      = memberOfGranted rec2 T q (grantsOf T rs otype oname rel) := by
    refine memberOfGranted_congr T q _ (fun g hg hbne m hm => ?_)
    obtain ⟨hgT, hmatch⟩ := grantsOf_mem hg
    refine h _ _ _ (restrictionMatches_exprRefs hmatch hbne) (Or.inr ?_)
    rcases hm with rfl | hm
    · exact subjectName_mem_storedNames hgT
    · exact hm
  simp only [directLeaf, hmog]

/-- `ttuLeaf` congruence: THE case needing `StoreDeclared` — parents come from
    stored tuples, and only admission validity places their types in `exprRefs`. -/
theorem ttuLeaf_congr {rec1 rec2 : Rec} (S : Schema) (T : Store) (q : Query)
    (hDecl : StoreDeclared S T) (subject : SubjectRef) (tr ts otype oname : String)
    (h : ∀ t' m r', (t', r') ∈ exprRefs S otype (.ttu tr ts) →
        (m = oname ∨ m ∈ storedNames T) → rec1 t' m r' = rec2 t' m r') :
    ttuLeaf rec1 subject T q tr ts otype oname
      = ttuLeaf rec2 subject T q tr ts otype oname := by
  unfold ttuLeaf
  refine anyCongr (fun tup htup => ?_)
  by_cases hc : (tup.relation == ts && tup.object.type == otype
      && (matchingObjects oname).contains tup.object.name) = true
  · obtain ⟨e', hlk, hpt⟩ := hDecl tup htup
    have hts : tup.relation = ts := by
      simp only [Bool.and_eq_true, beq_iff_eq] at hc; exact hc.1.1
    have hot : tup.object.type = otype := by
      simp only [Bool.and_eq_true, beq_iff_eq] at hc; exact hc.1.2
    rw [hot, hts] at hlk
    have hkey : (tup.subject.type, tr) ∈ exprRefs S otype (.ttu tr ts) := by
      unfold exprRefs
      rw [hlk]
      exact List.mem_cons_of_mem _ (List.mem_map.mpr ⟨tup.subject.type, hpt, rfl⟩)
    simp only [hc, if_true]
    by_cases hpn : (tup.subject.name != STAR) = true
    · simp only [hpn, if_true]
      rw [h _ _ _ hkey (Or.inr (subjectName_mem_storedNames htup))]
    · simp only [hpn, Bool.false_eq_true, if_false]
      have hinst : (instances T q tup.subject.type).any
            (fun inst => rec1 tup.subject.type inst tr)
          = (instances T q tup.subject.type).any
            (fun inst => rec2 tup.subject.type inst tr) :=
        anyCongr (fun inst hi =>
          h _ _ _ hkey (Or.inr (instances_subset_storedNames T q _ inst hi)))
      rw [hinst]
  · simp only [hc, Bool.false_eq_true, if_false]

/-- **Consultation confinement (congruence form).** Two `rec`s agreeing at every
    atom in `exprRefs S otype e × ({oname} ∪ storedNames T)` evaluate any
    expression identically on `(otype, oname)`, provided the store is
    admission-valid (`ttu` parents). This is what makes the T0a atom space
    finite. -/
theorem evalE_congr {rec1 rec2 : Rec} (S : Schema) (T : Store) (q : Query)
    (hDecl : StoreDeclared S T) (subject : SubjectRef) (otype oname rel : String) :
    ∀ e : Expr,
      (∀ t' m r', (t', r') ∈ exprRefs S otype e →
        (m = oname ∨ m ∈ storedNames T) → rec1 t' m r' = rec2 t' m r') →
      evalE rec1 subject T q otype oname rel e
        = evalE rec2 subject T q otype oname rel e := by
  intro e
  induction e with
  | union a b iha ihb =>
      intro h
      simp only [evalE]
      rw [iha (fun t' m r' hk => h t' m r'
            (by unfold exprRefs; exact List.mem_append_left _ hk)),
          ihb (fun t' m r' hk => h t' m r'
            (by unfold exprRefs; exact List.mem_append_right _ hk))]
  | inter a b iha ihb =>
      intro h
      simp only [evalE]
      rw [iha (fun t' m r' hk => h t' m r'
            (by unfold exprRefs; exact List.mem_append_left _ hk)),
          ihb (fun t' m r' hk => h t' m r'
            (by unfold exprRefs; exact List.mem_append_right _ hk))]
  | excl a b iha ihb =>
      intro h
      simp only [evalE]
      rw [iha (fun t' m r' hk => h t' m r'
            (by unfold exprRefs; exact List.mem_append_left _ hk)),
          ihb (fun t' m r' hk => h t' m r'
            (by unfold exprRefs; exact List.mem_append_right _ hk))]
  | computed r =>
      intro h
      simp only [evalE]
      exact h otype oname r (by unfold exprRefs; exact List.mem_singleton.mpr rfl)
        (Or.inl rfl)
  | direct rs =>
      intro h
      exact directLeaf_congr S subject T q rs otype oname rel h
  | ttu tr' ts' =>
      intro h
      exact ttuLeaf_congr S T q hDecl subject tr' ts' otype oname h

/-- `step` congruence: agreement on `refsOf (otype, rel) × ({oname} ∪ storedNames)`
    determines the next level's answer at `(otype, oname, rel)` — for ANY key
    (an undeclared key answers `false` under both). -/
theorem step_congr {rec1 rec2 : Rec} (S : Schema) (T : Store) (q : Query)
    (hDecl : StoreDeclared S T) (subject : SubjectRef) (otype oname rel : String)
    (h : ∀ t' m r', (t', r') ∈ refsOf S (otype, rel) →
        (m = oname ∨ m ∈ storedNames T) → rec1 t' m r' = rec2 t' m r') :
    step S subject T q rec1 otype oname rel
      = step S subject T q rec2 otype oname rel := by
  unfold step
  cases hlk : S.lookup (otype, rel) with
  | none => rfl
  | some e =>
      refine evalE_congr S T q hDecl subject otype oname rel e ?_
      unfold refsOf at h
      rw [hlk] at h
      exact h

end Zanzibar
