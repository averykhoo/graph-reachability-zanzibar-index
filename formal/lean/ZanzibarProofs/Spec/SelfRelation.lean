import ZanzibarProofs.Spec.WellDef

/-!
# The implicit userset self-relation — the spec `semR` (TK144, TK138 landing 2)

OpenFGA treats a concrete userset subject `T:o#r` as a member of its own node `(T, o, r)`
unconditionally, at every resolve node and OUTSIDE the rewrite (measured against OpenFGA
v1.22.0, `docs/tk138-userset-self-relation-2026-10-14.md` §1 and challenge C1):
`Members(o, r) = {o#r} ∪ Eval(rewrite(r))`. It propagates through computed usersets, TTU
and boolean arms, across objects, and it flips a `but not` from ALLOW to DENY (a userset
in its own subtrahend). Since TK144 the Python oracle (`tests/oracle.py::Oracle.check.sat`)
and both backends apply it; this file is the spec twin.

**`semR` is THE specification** (sub-decision D2: the disjunct form; the plan doc's §3.1
store/schema reduction is a proof device only, never the definition). The pre-TK144
`step` / `semAux` / `sem` (`Spec/Semantics.lean`) are kept, unchanged and with every
theorem about them, as the NON-reflexive base semantics: they still characterize the
residue the delta processor maintains (the reconcile evaluates non-reflexively, C5), and
the graph read-correctness ladder is stated over them. The headline theorems are restated
over `semR` (`GraphIndex/SelfRead.lean`, `SetEngine/SelfRelation.lean`).

* `selfHit` — the disjunct: the subject is a concrete userset (`predicate ≠ BARE`,
  `name ≠ STAR`; D1: a star subject takes no self-relation) equal to the node.
* `stepR` — `step` with the disjunct OUTSIDE the rewrite, inside `some e` only, so an
  undeclared relation stays `false` (lenient reads, unchanged).
* `semAuxR` / `semR` — the fuel recursion and the spec, exactly as `semAux` / `sem`.
* `semR_fuel_stable` — T0a for `semR` (C7: the disjunct consults no `rec`, so the
  consultation space, the atom count and the Kahn layering are all unchanged).
* `semR_eq_sem_of_not_userset` — on a bare or star subject `semR = sem`: the disjunct
  never fires (B1).
-/

namespace Zanzibar

/-- **The implicit userset self-relation** (TK144; the oracle's
    `subject[2] != '...' and subject[1] != '*' and subject == key`): a CONCRETE userset
    subject equal to the node `(otype, oname, rel)`. -/
def selfHit (subject : SubjectRef) (otype oname rel : String) : Bool :=
  subject.predicate != BARE && subject.name != STAR &&
  subject.type == otype && subject.name == oname && subject.predicate == rel

/-- `step` with OpenFGA's self-relation: at a DECLARED node the concrete userset subject
    equal to the node is a member, outside the rewrite (`tests/oracle.py::Oracle.check.sat`,
    `src/zanzibar/setengine/engine.py::SetEngine.check.sat`). An undeclared relation is
    `false`, exactly as in `step`. -/
def stepR (S : Schema) (subject : SubjectRef) (T : Store) (q : Query)
    (rec : Rec) (otype oname rel : String) : Bool :=
  match S.lookup (otype, rel) with
  | none => false
  | some e => selfHit subject otype oname rel || evalE rec subject T q otype oname rel e

/-- The fuel-bounded reflexive evaluator (`semAux` with `stepR`). -/
def semAuxR (S : Schema) (subject : SubjectRef) (T : Store) (q : Query) :
    Nat → String → String → String → Bool
  | 0, _, _, _ => false
  | fuel + 1, otype, oname, rel =>
      stepR S subject T q (semAuxR S subject T q fuel) otype oname rel

/-- **The specification** (TK144): `semAuxR` at `fuelBound`. -/
def semR (S : Schema) (T : Store) (q : Query) : Bool :=
  semAuxR S q.subject T q (fuelBound S T) q.object.type q.object.name q.relation

/-! ## Basic facts -/

theorem semAuxR_undeclared (S : Schema) (subject : SubjectRef) (T : Store) (q : Query)
    {t r : String} (hk : (t, r) ∉ S.keys) :
    ∀ f m, semAuxR S subject T q f t m r = false
  | 0, _ => rfl
  | f + 1, m => by rw [semAuxR, stepR, lookup_eq_none S hk]

/-- `stepR` congruence (the `step_congr` twin): the disjunct reads no `rec`. -/
theorem stepR_congr {rec1 rec2 : Rec} (S : Schema) (T : Store) (q : Query)
    (hDecl : StoreDeclared S T) (subject : SubjectRef) (otype oname rel : String)
    (h : ∀ t' m r', (t', r') ∈ refsOf S (otype, rel) →
        (m = oname ∨ m ∈ storedNames T) → rec1 t' m r' = rec2 t' m r') :
    stepR S subject T q rec1 otype oname rel
      = stepR S subject T q rec2 otype oname rel := by
  unfold stepR
  cases hlk : S.lookup (otype, rel) with
  | none => rfl
  | some e =>
      have hc := evalE_congr S T q hDecl subject otype oname rel e (by
        unfold refsOf at h
        rw [hlk] at h
        exact h)
      exact congrArg (fun b => selfHit subject otype oname rel || b) hc

/-- On a subject that is NOT a concrete userset the disjunct is `false`. -/
theorem selfHit_false_of_not_userset {subject : SubjectRef}
    (h : subject.predicate = BARE ∨ subject.name = STAR) (otype oname rel : String) :
    selfHit subject otype oname rel = false := by
  unfold selfHit
  rcases h with h | h <;> simp [h]

/-- **B1.** On a bare or star subject the reflexive evaluator IS the base one, at every
    fuel and node. -/
theorem semAuxR_eq_semAux_of_not_userset (S : Schema) {subject : SubjectRef} (T : Store)
    (q : Query) (h : subject.predicate = BARE ∨ subject.name = STAR) :
    ∀ f t m r, semAuxR S subject T q f t m r = semAux S subject T q f t m r := by
  intro f
  induction f with
  | zero => intro t m r; rfl
  | succ f ih =>
      intro t m r
      have hrec : semAuxR S subject T q f = semAux S subject T q f := by
        funext t' m' r'; exact ih t' m' r'
      rw [semAuxR, semAux, stepR, step, hrec, selfHit_false_of_not_userset h]
      cases S.lookup (t, r) <;> simp

/-- **B1 (query form).** `semR = sem` on a bare or star subject. -/
theorem semR_eq_sem_of_not_userset (S : Schema) (T : Store) (q : Query)
    (h : q.subject.predicate = BARE ∨ q.subject.name = STAR) :
    semR S T q = sem S T q := by
  unfold semR sem
  exact semAuxR_eq_semAux_of_not_userset S T q h _ _ _ _

/-! ## T0a for `semR` — the untainted (monotone) phase

The `Spec/Stabilize.lean` argument verbatim, with `stepR` for `step`. The disjunct is a
constant in `rec`, so the masked monotonicity, the true-set chain and the counting bound
go through unchanged (C7). -/

theorem semAuxR_mono_untainted (S : Schema) (T : Store) (q : Query)
    (hDecl : StoreDeclared S T) :
    ∀ f (t r : String), (t, r) ∈ S.keys → (t, r) ∉ taintedKeys S →
      ∀ m, m ∈ relevantNames T q →
      semAuxR S q.subject T q f t m r = true →
      semAuxR S q.subject T q (f + 1) t m r = true := by
  intro f
  induction f with
  | zero => intro t r _ _ m _ h; simp [semAuxR] at h
  | succ f ih =>
      intro t r hk hu m hm h
      obtain ⟨e, hlk⟩ := lookup_some_of_mem S hk
      obtain ⟨hbt, hrefs⟩ := untainted_closed S hk hu
      have hne : e.noExcl := by
        refine noExcl_of_not_containsBool e ?_
        unfold baseTaint at hbt
        rw [hlk] at hbt
        exact hbt
      set P : Rec := fun t' m' r' =>
        decide ((t', r') ∈ exprRefs S t e) && decide (m' = m ∨ m' ∈ storedNames T)
        with hP
      set A : Rec := fun t' m' r' => semAuxR S q.subject T q f t' m' r' && P t' m' r'
        with hA
      set B : Rec := fun t' m' r' =>
        semAuxR S q.subject T q (f + 1) t' m' r' && P t' m' r' with hB
      have hmask : ∀ (rec : Rec) t' m' r', (t', r') ∈ exprRefs S t e →
          (m' = m ∨ m' ∈ storedNames T) →
          (rec t' m' r' && P t' m' r') = rec t' m' r' := by
        intro rec t' m' r' hk' hm'
        rw [hP]
        simp only [decide_eq_true hk', decide_eq_true hm', Bool.and_true]
      have hAgree1 : evalE A q.subject T q t m r e
          = evalE (semAuxR S q.subject T q f) q.subject T q t m r e :=
        evalE_congr S T q hDecl q.subject t m r e
          (fun t' m' r' hk' hm' => hmask _ t' m' r' hk' hm')
      have hAgree2 : evalE B q.subject T q t m r e
          = evalE (semAuxR S q.subject T q (f + 1)) q.subject T q t m r e :=
        evalE_congr S T q hDecl q.subject t m r e
          (fun t' m' r' hk' hm' => hmask _ t' m' r' hk' hm')
      have hle : RecLe A B := by
        intro t' m' r' hAt
        rw [hA, hB] at *
        simp only [Bool.and_eq_true] at hAt ⊢
        obtain ⟨hsem, hPt⟩ := hAt
        refine ⟨?_, hPt⟩
        have hPt' := hPt
        rw [hP] at hPt'
        simp only [Bool.and_eq_true, decide_eq_true_eq] at hPt'
        obtain ⟨hkey, hname⟩ := hPt'
        by_cases hdecl' : (t', r') ∈ S.keys
        · have hu' : (t', r') ∉ taintedKeys S := by
            refine hrefs (t', r') ?_
            show (t', r') ∈ refsOf S (t, r)
            unfold refsOf
            rw [hlk]
            exact hkey
          have hm'' : m' ∈ relevantNames T q := by
            rcases hname with rfl | hs
            · exact hm
            · exact List.mem_cons_of_mem _ hs
          exact ih t' r' hdecl' hu' m' hm'' hsem
        · rw [semAuxR_undeclared S q.subject T q hdecl' f m'] at hsem
          exact absurd hsem (by simp)
      have hs1 : semAuxR S q.subject T q (f + 1) t m r
          = (selfHit q.subject t m r || evalE (semAuxR S q.subject T q f) q.subject T q t m r e) := by
        rw [semAuxR, stepR, hlk]
      have hs2 : semAuxR S q.subject T q (f + 1 + 1) t m r
          = (selfHit q.subject t m r
              || evalE (semAuxR S q.subject T q (f + 1)) q.subject T q t m r e) := by
        rw [semAuxR, stepR, hlk]
      rw [hs1, Bool.or_eq_true] at h
      rw [hs2, Bool.or_eq_true]
      rcases h with h | h
      · exact Or.inl h
      · right
        have h1 : evalE A q.subject T q t m r e = true := by rw [hAgree1]; exact h
        have h2 := evalE_mono hle q.subject T q t m r e hne h1
        rwa [hAgree2] at h2

/-- The untainted relevant atoms true at fuel `f`, reflexively. -/
def trueSetR (S : Schema) (T : Store) (q : Query) (f : Nat) : Finset (Key × String) :=
  (atomsU S T q).filter (fun a => semAuxR S q.subject T q f a.1.1 a.2 a.1.2 = true)

private theorem bool_eq_of_true_iffR {a b : Bool} (h : a = true ↔ b = true) : a = b := by
  cases a <;> cases b <;> simp_all

theorem trueSetR_mono (S : Schema) (T : Store) (q : Query) (hDecl : StoreDeclared S T)
    (f : Nat) : trueSetR S T q f ⊆ trueSetR S T q (f + 1) := by
  intro a ha
  rw [trueSetR, Finset.mem_filter] at ha ⊢
  obtain ⟨haU, hsem⟩ := ha
  obtain ⟨⟨hk, hu⟩, hm⟩ := mem_atomsU haU
  exact ⟨haU, semAuxR_mono_untainted S T q hDecl f a.1.1 a.1.2 hk hu a.2 hm hsem⟩

theorem trueSetR_det (S : Schema) (T : Store) (q : Query) (hDecl : StoreDeclared S T)
    (f : Nat) (heq : trueSetR S T q f = trueSetR S T q (f + 1)) :
    trueSetR S T q (f + 1) = trueSetR S T q (f + 2) := by
  have hstable : ∀ a ∈ atomsU S T q,
      semAuxR S q.subject T q f a.1.1 a.2 a.1.2
        = semAuxR S q.subject T q (f + 1) a.1.1 a.2 a.1.2 := by
    intro a ha
    refine bool_eq_of_true_iffR ?_
    constructor
    · intro ht
      have : a ∈ trueSetR S T q f := by
        rw [trueSetR, Finset.mem_filter]; exact ⟨ha, ht⟩
      rw [heq, trueSetR, Finset.mem_filter] at this
      exact this.2
    · intro ht
      have : a ∈ trueSetR S T q (f + 1) := by
        rw [trueSetR, Finset.mem_filter]; exact ⟨ha, ht⟩
      rw [← heq, trueSetR, Finset.mem_filter] at this
      exact this.2
  unfold trueSetR
  refine Finset.filter_congr (fun a ha => ?_)
  obtain ⟨⟨hk, hu⟩, hm⟩ := mem_atomsU ha
  have hrefs := (untainted_closed S hk hu).2
  have hstep : semAuxR S q.subject T q (f + 1) a.1.1 a.2 a.1.2
      = semAuxR S q.subject T q (f + 2) a.1.1 a.2 a.1.2 := by
    show stepR S q.subject T q (semAuxR S q.subject T q f) a.1.1 a.2 a.1.2
      = stepR S q.subject T q (semAuxR S q.subject T q (f + 1)) a.1.1 a.2 a.1.2
    refine stepR_congr S T q hDecl q.subject a.1.1 a.2 a.1.2 (fun t' m' r' hk' hm' => ?_)
    by_cases hdecl' : (t', r') ∈ S.keys
    · have hu' : (t', r') ∉ taintedKeys S := hrefs (t', r') hk'
      have hm'' : m' ∈ relevantNames T q := by
        rcases hm' with rfl | hs
        · exact hm
        · exact List.mem_cons_of_mem _ hs
      exact hstable ((t', r'), m') (by
        unfold atomsU untaintedKeysF
        rw [Finset.mem_product, Finset.mem_sdiff, List.mem_toFinset, List.mem_toFinset,
          List.mem_toFinset]
        exact ⟨⟨hdecl', hu'⟩, hm''⟩)
    · rw [semAuxR_undeclared S q.subject T q hdecl' f m',
        semAuxR_undeclared S q.subject T q hdecl' (f + 1) m']
  rw [hstep]

/-- Untainted stabilization, reflexively: from fuel `|atomsU|` on. -/
theorem untainted_stableR (S : Schema) (T : Store) (q : Query)
    (hDecl : StoreDeclared S T) :
    ∀ f, (atomsU S T q).card ≤ f →
      ∀ t r, (t, r) ∈ S.keys → (t, r) ∉ taintedKeys S →
      ∀ m ∈ relevantNames T q,
      semAuxR S q.subject T q f t m r = semAuxR S q.subject T q (f + 1) t m r := by
  have hstab := chain_stabilizes (trueSetR S T q) (atomsU S T q).card
    (trueSetR_mono S T q hDecl) (trueSetR_det S T q hDecl) (by
      unfold trueSetR
      refine Finset.filter_false_of_mem (fun a _ => ?_)
      simp [semAuxR])
    (fun i => Finset.card_le_card (Finset.filter_subset _ _))
  intro f hf t r hk hu m hm
  have hpers := chain_persists (trueSetR S T q) (trueSetR_det S T q hDecl) hstab f hf
  have ha : ((t, r), m) ∈ atomsU S T q := by
    unfold atomsU untaintedKeysF
    rw [Finset.mem_product, Finset.mem_sdiff, List.mem_toFinset, List.mem_toFinset,
      List.mem_toFinset]
    exact ⟨⟨hk, hu⟩, hm⟩
  refine bool_eq_of_true_iffR ?_
  constructor
  · intro ht
    have : ((t, r), m) ∈ trueSetR S T q f := by
      rw [trueSetR, Finset.mem_filter]; exact ⟨ha, ht⟩
    rw [hpers, trueSetR, Finset.mem_filter] at this
    exact this.2
  · intro ht
    have : ((t, r), m) ∈ trueSetR S T q (f + 1) := by
      rw [trueSetR, Finset.mem_filter]; exact ⟨ha, ht⟩
    rw [← hpers, trueSetR, Finset.mem_filter] at this
    exact this.2

/-! ## T0a for `semR` — the tainted (Kahn) phase and the assembly -/

theorem layer_stableR (S : Schema) (T : Store) (q : Query) (hDecl : StoreDeclared S T)
    {L : List (List Key)} (hL : stratify S = some L) :
    ∀ i, ∀ k ∈ L.getD i [], ∀ m ∈ relevantNames T q,
      ∀ f, (atomsU S T q).card + 1 + i ≤ f →
      semAuxR S q.subject T q f k.1 m k.2
        = semAuxR S q.subject T q (f + 1) k.1 m k.2 := by
  intro i
  induction i using Nat.strong_induction_on with
  | _ i ih =>
    intro k hk m hm f hf
    obtain ⟨f', rfl⟩ : ∃ f', f = f' + 1 := ⟨f - 1, by omega⟩
    show stepR S q.subject T q (semAuxR S q.subject T q f') k.1 m k.2
      = stepR S q.subject T q (semAuxR S q.subject T q (f' + 1)) k.1 m k.2
    refine stepR_congr S T q hDecl q.subject k.1 m k.2 (fun t' m' r' hk' hm' => ?_)
    have hm'' : m' ∈ relevantNames T q := by
      rcases hm' with rfl | hs
      · exact hm
      · exact List.mem_cons_of_mem _ hs
    by_cases hdecl' : (t', r') ∈ S.keys
    · by_cases htaint : (t', r') ∈ taintedKeys S
      · have hktaint : k ∈ taintedKeys S := stratify_layers_tainted S hL i k hk
        have hedge : (k, (t', r')) ∈ depEdges S := by
          unfold depEdges
          refine List.mem_flatMap.mpr ⟨k, hktaint, ?_⟩
          refine List.mem_filterMap.mpr ⟨(t', r'), hk', ?_⟩
          have hc : ((taintedKeys S).contains (t', r')) = true := by
            rw [List.contains_eq_mem, decide_eq_true_eq]
            exact htaint
          rw [if_pos hc]
        obtain ⟨j, _, hbj⟩ := stratify_covers S hL (t', r') htaint
        have hji : j < i := stratify_topo_strict S hL k (t', r') i j hedge hk hbj
        exact ih j hji (t', r') hbj m' hm'' f' (by omega)
      · exact untainted_stableR S T q hDecl f' (by omega) t' r' hdecl' htaint m' hm''
    · rw [semAuxR_undeclared S q.subject T q hdecl' f' m',
        semAuxR_undeclared S q.subject T q hdecl' (f' + 1) m']

theorem all_stableR (S : Schema) (T : Store) (q : Query) (hDecl : StoreDeclared S T)
    {L : List (List Key)} (hL : stratify S = some L) :
    ∀ f, (atomsU S T q).card + 1 + L.length ≤ f →
      ∀ t r m, m ∈ relevantNames T q →
      semAuxR S q.subject T q f t m r = semAuxR S q.subject T q (f + 1) t m r := by
  intro f hf t r m hm
  by_cases hdecl : (t, r) ∈ S.keys
  · by_cases htaint : (t, r) ∈ taintedKeys S
    · obtain ⟨i, hi, hbi⟩ := stratify_covers S hL (t, r) htaint
      exact layer_stableR S T q hDecl hL i (t, r) hbi m hm f (by omega)
    · exact untainted_stableR S T q hDecl f (by omega) t r hdecl htaint m hm
  · rw [semAuxR_undeclared S q.subject T q hdecl f m,
      semAuxR_undeclared S q.subject T q hdecl (f + 1) m]

/-- The `fuelBound` arithmetic of `semAux_fuel_stable_step`, factored for reuse. -/
theorem atomsU_card_add_le_fuelBound (S : Schema) (T : Store) (q : Query)
    (hK : S.keys ≠ []) {L : List (List Key)} (hL : stratify S = some L) :
    (atomsU S T q).card + 1 + L.length ≤ fuelBound S T := by
  have hN : (atomsU S T q).card ≤ S.keys.length * (T.length * 2 + 1) := by
    unfold atomsU
    rw [Finset.card_product]
    refine Nat.mul_le_mul ?_ ?_
    · exact le_trans (Finset.card_le_card Finset.sdiff_subset)
        (List.toFinset_card_le S.keys)
    · have h1 := List.toFinset_card_le (relevantNames T q)
      have h2 : (relevantNames T q).length = T.length * 2 + 1 := by
        unfold relevantNames
        rw [List.length_cons, storedNames_length]
        omega
      omega
  have hLlen : L.length ≤ S.keys.length :=
    le_trans (stratify_length S hL) (taintedKeys_length_le S)
  have hK1 : 1 ≤ S.keys.length := by
    cases hKs : S.keys with
    | nil => exact absurd hKs hK
    | cons a t => simp
  have hmul : S.keys.length * (T.length * 2 + 1) + S.keys.length * 3
      = S.keys.length * (T.length * 2 + 4) := by
    rw [← Nat.mul_add]
  unfold fuelBound
  omega

/-- **The stabilization core, reflexively** (the `semAux_fuel_stable_step` twin; the
    `StoreDeclared` premise is needed for the same reason, `Spec/Counterexample.lean`). -/
theorem semAuxR_fuel_stable_step (S : Schema) (T : Store) (q : Query)
    (hStrat : Stratifiable S) (hDecl : StoreDeclared S T) :
    ∀ f, fuelBound S T ≤ f →
      semAuxR S q.subject T q f q.object.type q.object.name q.relation
        = semAuxR S q.subject T q (f + 1) q.object.type q.object.name q.relation := by
  intro f hf
  by_cases hK : S.keys = []
  · have hout : (q.object.type, q.relation) ∉ S.keys := by rw [hK]; simp
    rw [semAuxR_undeclared S q.subject T q hout f q.object.name,
        semAuxR_undeclared S q.subject T q hout (f + 1) q.object.name]
  · obtain ⟨L, hL⟩ := Option.isSome_iff_exists.mp hStrat
    exact all_stableR S T q hDecl hL f
      (le_trans (atomsU_card_add_le_fuelBound S T q hK hL) hf) _ _ _ (List.mem_cons_self ..)

/-- **T0a for the spec `semR`** (TK144). Fuel above `fuelBound` does not change the
    answer. C7 (the plan doc's open check): the bound is the same `fuelBound` — the
    disjunct consults no `rec`, so a subject whose object is reached only through a
    stored tuple (model C's `group:3`) is a stored name and inside the atom space. -/
theorem semR_fuel_stable (S : Schema) (T : Store) (q : Query)
    (hStrat : Stratifiable S) (hDecl : StoreDeclared S T) :
    ∀ f, fuelBound S T ≤ f →
      semAuxR S q.subject T q f q.object.type q.object.name q.relation = semR S T q := by
  intro f hf
  induction f, hf using Nat.le_induction with
  | base => rfl
  | succ n hn ih =>
      rw [← semAuxR_fuel_stable_step S T q hStrat hDecl n hn]; exact ih

end Zanzibar
