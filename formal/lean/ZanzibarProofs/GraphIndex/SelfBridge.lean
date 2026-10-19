import ZanzibarProofs.FullScope
import ZanzibarProofs.Spec.SelfRelation

/-!
# The self-relation bridge on the untainted side (TK144) -- `semR` from `sem`

The graph read correctness ladder (`graph_correct` and everything under it) is stated over
the NON-reflexive base `sem`. This file proves, at the SPEC level, how the reflexive spec
`semR` decomposes over `sem` on an UNTAINTED query with a concrete userset subject
`s = T:o#p` ("Claim A" of the TK144 build notes,
`docs/tk138-userset-self-relation-2026-10-14.md`, corrections 2026-10-17):

    semR q = sem q ∨ ∃ r1 ∈ seedRels S s, [q's node is (T, o, r1)] ∨ sem ⟨T:o#r1, q.relation, q.object⟩

where `seedRels S s` -- the "seed" relations -- are the declared untainted relations on `T`
whose node at `o` holds `s` by the self-relation through computed arms alone (computed
SEMANTICALLY: `semR` on the EMPTY store). The graph side then follows from `graph_correct`
applied to each seed subject `T:o#r1` (`GraphIndex/SelfRead.lean`), with no new graph-state
reasoning: the seed probes the Python read adds
(`src/zanzibar/graphindex/wildcard.py::WildcardIndex._check_internal`, the `seed_keys`) are
ordinary reads FROM the seed nodes.

Hypotheses are the spec-level store facts the W4 bundles supply: `StoreDeclared`,
`Stratifiable`, `NoUsersetStar` (a stored star subject is bare -- `W4Fragment.bareStar`), and
`NoStarParentsU` (no stored star subject feeds an untainted TTU tupleset -- from
`W4Fragment.ttuStarFree`), plus "no declared relation is named `BARE`" (from `WF`).
-/

namespace Zanzibar

/-! ## Query irrelevance and node-wise stability, reflexively -/

theorem semAuxR_qirrel (S : Schema) (subject : SubjectRef) (T : Store) (q1 q2 : Query) :
    ∀ (f : Nat) (ot on rel : String),
      semAuxR S subject T q1 f ot on rel = semAuxR S subject T q2 f ot on rel := by
  intro f
  induction f with
  | zero => intro ot on rel; rfl
  | succ f ih =>
    intro ot on rel
    have hfun : semAuxR S subject T q1 f = semAuxR S subject T q2 f := by
      funext ot' on' rel'; exact ih ot' on' rel'
    show stepR S subject T q1 (semAuxR S subject T q1 f) ot on rel
       = stepR S subject T q2 (semAuxR S subject T q2 f) ot on rel
    rw [hfun]
    unfold stepR
    cases S.lookup (ot, rel) with
    | none => rfl
    | some e =>
      exact congrArg (fun b => selfHit subject ot on rel || b)
        (evalE_qirrel _ subject T q1 q2 ot on rel e)

/-- Every node, not only the query's own, is fuel-stable above `fuelBound` (reflexively). -/
theorem semAuxR_stable_at (S : Schema) (T : Store) (hStrat : Stratifiable S)
    (hDecl : StoreDeclared S T) (s : SubjectRef) (q : Query) (t m r : String) :
    ∀ f, fuelBound S T ≤ f → semAuxR S s T q f t m r = semR S T ⟨s, r, ⟨t, m⟩⟩ := by
  intro f hf
  rw [semAuxR_qirrel S s T q ⟨s, r, ⟨t, m⟩⟩ f t m r]
  exact semR_fuel_stable S T ⟨s, r, ⟨t, m⟩⟩ hStrat hDecl f hf

/-- The same for the base `semAux`. -/
theorem semAux_stable_at (S : Schema) (T : Store) (hStrat : Stratifiable S)
    (hDecl : StoreDeclared S T) (s : SubjectRef) (q : Query) (t m r : String) :
    ∀ f, fuelBound S T ≤ f → semAux S s T q f t m r = sem S T ⟨s, r, ⟨t, m⟩⟩ := by
  intro f hf
  rw [semAux_qirrel S s T q ⟨s, r, ⟨t, m⟩⟩ f t m r]
  exact sem_fuel_stable S T ⟨s, r, ⟨t, m⟩⟩ hStrat hDecl f hf

/-! ## Store facts the bridge needs -/

/-- **No stored star subject feeds an UNTAINTED TTU tupleset** -- the spec-level form of
    `W4Fragment.ttuStarFree` (`GraphIndex/RulesBareStar.lean::TtuStarFree`), derived from it in
    `noStarParentsU_of_ttuStarFree`. It is what kills `ttuLeaf`'s star-parent branch. -/
def NoStarParentsU (S : Schema) (T : Store) : Prop :=
  ∀ tup ∈ T, tup.subject.name = STAR → ∀ k e, S.lookup k = some e → isDerived S k = false →
    ∀ tt ∈ exprTtus e, ¬(tup.relation = tt.2 ∧ tup.object.type = k.1)

theorem noStarParentsU_of_ttuStarFree {S : Schema} {T : Store} (hNK : NodupKeys S)
    (hTS : TtuStarFree S T) : NoStarParentsU S T := by
  intro tup htup hstar k e hlk hu tt htt
  have hd : (k, e) ∈ S.defs := mem_defs_of_lookup hlk
  have hcb : containsBool e = false := containsBool_of_mem_defs_untainted hNK hd hu
  have harm : (⟨k.1, tt.2, k.2, RuleKind.ttu tt.1⟩ : RRule) ∈ exprArms k.1 k.2 e :=
    mem_exprArms_of_mem_exprTtus hcb (by simpa using htt)
  have hrw := mem_schemaRewrites_of_mem_exprArms (d := (k, e)) hd hu harm
  exact hTS tup htup hstar _ hrw tt.1 rfl

theorem not_bare_of_mem_keys {S : Schema} (hWF : WF S) {k : Key} (hk : k ∈ S.keys) :
    k.2 ≠ BARE := by
  intro h
  have hok := relNameOK_of_mem_keys hWF hk
  rw [h] at hok
  exact hok (by simp [BARE, String.contains])

theorem untainted_of_isDerived_false {S : Schema} {k : Key} (h : isDerived S k = false) :
    k ∉ taintedKeys S := by
  unfold isDerived at h
  rw [List.contains_eq_mem] at h
  exact of_decide_eq_false h

theorem isDerived_false_of_untainted {S : Schema} {k : Key} (h : k ∉ taintedKeys S) :
    isDerived S k = false := by
  unfold isDerived
  rw [List.contains_eq_mem]
  exact decide_eq_false h

/-- An untainted declared key's definition is boolean-free, and its references are untainted. -/
theorem untainted_def {S : Schema} {k : Key} {e : Expr} (hlk : S.lookup k = some e)
    (hu : isDerived S k = false) :
    containsBool e = false ∧ ∀ b ∈ exprRefs S k.1 e, b ∉ taintedKeys S := by
  have hk : k ∈ S.keys := by
    by_contra hk; rw [lookup_eq_none S hk] at hlk; simp at hlk
  obtain ⟨hbt, hrefs⟩ := untainted_closed S hk (untainted_of_isDerived_false hu)
  refine ⟨?_, ?_⟩
  · unfold baseTaint at hbt; rw [hlk] at hbt; exact hbt
  · intro b hb; exact hrefs b (by unfold refsOf; rw [hlk]; exact hb)

/-! ## Union-only expressions (`containsBool e = false`)

An untainted definition is a union of `direct` / `computed` / `ttu` leaves. The two facts
below are what a "this computed arm holds" step needs in each direction. -/

theorem computedRefs_exprRefs {S : Schema} {t r' : String} :
    ∀ {e : Expr}, r' ∈ computedRefs e → (t, r') ∈ exprRefs S t e := by
  intro e
  induction e with
  | computed r => intro h; simp [computedRefs] at h; subst h; simp [exprRefs]
  | direct _ => intro h; simp [computedRefs] at h
  | ttu _ _ => intro h; simp [computedRefs] at h
  | union a b iha ihb =>
      intro h
      simp only [computedRefs, List.mem_append] at h
      simp only [exprRefs, List.mem_append]
      exact h.imp iha ihb
  | inter a b iha ihb =>
      intro h
      simp only [computedRefs, List.mem_append] at h
      simp only [exprRefs, List.mem_append]
      exact h.imp iha ihb
  | excl a b iha ihb =>
      intro h
      simp only [computedRefs, List.mem_append] at h
      simp only [exprRefs, List.mem_append]
      exact h.imp iha ihb

/-- A union-only expression holds as soon as one of its computed arms does. -/
theorem evalE_of_computed {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {t m R r' : String} (hr : rec t m r' = true) :
    ∀ {e : Expr}, containsBool e = false → r' ∈ computedRefs e →
      evalE rec s T q t m R e = true := by
  intro e
  induction e with
  | computed r =>
      intro _ h; simp [computedRefs] at h; subst h; simpa [evalE] using hr
  | direct _ => intro _ h; simp [computedRefs] at h
  | ttu _ _ => intro _ h; simp [computedRefs] at h
  | union a b iha ihb =>
      intro hcb h
      simp only [containsBool, Bool.or_eq_false_iff] at hcb
      simp only [computedRefs, List.mem_append] at h
      simp only [evalE, Bool.or_eq_true]
      exact h.imp (iha hcb.1) (ihb hcb.2)
  | inter _ _ _ _ => intro hcb _; simp [containsBool] at hcb
  | excl _ _ _ _ => intro hcb _; simp [containsBool] at hcb

/-- On the EMPTY store a union-only expression holds only through a computed arm. -/
theorem evalE_nil_computed {rec : Rec} {s : SubjectRef} {q : Query} {t m R : String} :
    ∀ {e : Expr}, containsBool e = false → evalE rec s [] q t m R e = true →
      ∃ r' ∈ computedRefs e, rec t m r' = true := by
  intro e
  induction e with
  | computed r => intro _ h; exact ⟨r, by simp [computedRefs], by simpa [evalE] using h⟩
  | direct rs =>
      intro _ h
      simp [evalE, directLeaf, grantsOf, memberOfGranted] at h
  | ttu tr ts => intro _ h; simp [evalE, ttuLeaf] at h
  | union a b iha ihb =>
      intro hcb h
      simp only [containsBool, Bool.or_eq_false_iff] at hcb
      simp only [evalE, Bool.or_eq_true] at h
      rcases h with h | h
      · obtain ⟨r', hr', hrec⟩ := iha hcb.1 h
        exact ⟨r', by simp [computedRefs, hr'], hrec⟩
      · obtain ⟨r', hr', hrec⟩ := ihb hcb.2 h
        exact ⟨r', by simp [computedRefs, hr'], hrec⟩
  | inter _ _ _ _ => intro hcb _; simp [containsBool] at hcb
  | excl _ _ _ _ => intro hcb _; simp [containsBool] at hcb

/-- `evalE` monotone in `rec` on the CONSULTED atoms only (the masking argument of
    `Spec/Stabilize.lean::semAux_mono_untainted`, stated once). -/
theorem evalE_mono_on {S : Schema} {T : Store} {q : Query} (hDecl : StoreDeclared S T)
    {rec1 rec2 : Rec} (s : SubjectRef) (t m R : String) (e : Expr) (hne : e.noExcl)
    (h : ∀ t' m' r', (t', r') ∈ exprRefs S t e → (m' = m ∨ m' ∈ storedNames T) →
        rec1 t' m' r' = true → rec2 t' m' r' = true)
    (he : evalE rec1 s T q t m R e = true) : evalE rec2 s T q t m R e = true := by
  set P : Rec := fun t' m' r' =>
    decide ((t', r') ∈ exprRefs S t e) && decide (m' = m ∨ m' ∈ storedNames T) with hP
  set A : Rec := fun t' m' r' => rec1 t' m' r' && P t' m' r' with hA
  set B : Rec := fun t' m' r' => rec2 t' m' r' && P t' m' r' with hB
  have hmask : ∀ (rec : Rec) t' m' r', (t', r') ∈ exprRefs S t e →
      (m' = m ∨ m' ∈ storedNames T) → (rec t' m' r' && P t' m' r') = rec t' m' r' := by
    intro rec t' m' r' hk' hm'
    rw [hP]
    simp only [decide_eq_true hk', decide_eq_true hm', Bool.and_true]
  have hAg : evalE A s T q t m R e = evalE rec1 s T q t m R e :=
    evalE_congr S T q hDecl s t m R e (fun t' m' r' hk' hm' => hmask _ t' m' r' hk' hm')
  have hBg : evalE B s T q t m R e = evalE rec2 s T q t m R e :=
    evalE_congr S T q hDecl s t m R e (fun t' m' r' hk' hm' => hmask _ t' m' r' hk' hm')
  have hle : RecLe A B := by
    intro t' m' r' hAt
    rw [hA] at hAt
    rw [hB]
    simp only [Bool.and_eq_true] at hAt ⊢
    obtain ⟨h1, hPt⟩ := hAt
    refine ⟨?_, hPt⟩
    rw [hP] at hPt
    simp only [Bool.and_eq_true, decide_eq_true_eq] at hPt
    exact h t' m' r' hPt.1 hPt.2 h1
  rw [← hBg]
  exact evalE_mono hle s T q t m R e hne (by rw [hAg]; exact he)

/-! ## `ttuLeaf` / `directLeaf` intro helpers -/

theorem ttuLeaf_intro_self {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {tr ts ot on : String} {tup : Tuple} (htup : tup ∈ T)
    (hrel : tup.relation = ts) (hot : tup.object.type = ot)
    (hcon : (matchingObjects on).contains tup.object.name = true)
    (hpn : tup.subject.name ≠ STAR)
    (hself : s.type = tup.subject.type ∧ s.name = tup.subject.name ∧ s.predicate = tr) :
    ttuLeaf rec s T q tr ts ot on = true := by
  unfold ttuLeaf
  refine List.any_eq_true.mpr ⟨tup, htup, ?_⟩
  have hc : (tup.relation == ts && tup.object.type == ot &&
      (matchingObjects on).contains tup.object.name) = true := by
    rw [hrel, hot]; simpa using hcon
  have hp : (tup.subject.name != STAR) = true := by simpa using hpn
  rw [if_pos hc]
  simp only [hp, if_true, Bool.or_eq_true, Bool.and_eq_true, beq_iff_eq]
  exact Or.inl ⟨⟨hself.1, hself.2.1⟩, hself.2.2⟩

/-- The rec-free "match" part of `directLeaf` at a concrete userset subject. -/
theorem directLeaf_of_match {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String} (hs : s.name ≠ STAR) (hsp : s.predicate ≠ BARE)
    {g : Tuple} (hg : g ∈ grantsOf T rs ot on rel) (hgs : g.subject = s) :
    directLeaf rec s T q rs ot on rel = true := by
  unfold directLeaf
  rw [if_neg (by simpa using hs), if_neg (by simpa using hsp), Bool.or_eq_true]
  refine Or.inl (List.any_eq_true.mpr ⟨g, hg, ?_⟩)
  rw [hgs]
  simp [hs, hsp]

/-- The ttu-leaf parent's key is consulted (`exprRefs`), given `StoreDeclared`. -/
theorem ttu_parent_exprRefs {S : Schema} {T : Store} (hDecl : StoreDeclared S T)
    {tr ts t : String} {tup : Tuple} (htup : tup ∈ T) (hrel : tup.relation = ts)
    (hot : tup.object.type = t) :
    (tup.subject.type, tr) ∈ exprRefs S t (.ttu tr ts) := by
  obtain ⟨e', hlk, hpt⟩ := hDecl tup htup
  rw [hot, hrel] at hlk
  unfold exprRefs
  rw [hlk]
  exact List.mem_cons_of_mem _ (List.mem_map.mpr ⟨tup.subject.type, hpt, rfl⟩)

/-! ## A2 -- a seed subject's membership transfers to the reflexive subject -/

/-- **Subject switch, one level.** If `T:o#r1` is a member of a union-only node with recursion
    `rec1`, then `s = T:o#p` is a member with recursion `rec2`, provided `rec2` dominates
    `rec1` on the consulted atoms and `rec2` already holds at the seed node `(T, o, r1)` --
    an exact grant of `T:o#r1`, or a from-chain parent `T:o` with target `r1`, then reaches `s`
    through that node. -/
theorem evalE_switch {S : Schema} {T : Store} {q1 q2 : Query} {rec1 rec2 : Rec}
    (hDecl : StoreDeclared S T) (hNUS : NoUsersetStar T)
    {s : SubjectRef} {r1 : String} (hs : s.name ≠ STAR) (hr1 : r1 ≠ BARE)
    (hseed : rec2 s.type s.name r1 = true) (t m R : String) :
    ∀ e : Expr, containsBool e = false →
      (∀ tt ∈ exprTtus e, ∀ tup ∈ T, tup.subject.name = STAR →
          ¬(tup.relation = tt.2 ∧ tup.object.type = t)) →
      (∀ t' m' r', (t', r') ∈ exprRefs S t e → rec1 t' m' r' = true → rec2 t' m' r' = true) →
      evalE rec1 ⟨s.type, s.name, r1⟩ T q1 t m R e = true →
      evalE rec2 s T q2 t m R e = true := by
  intro e
  induction e with
  | computed r =>
      intro _ _ h he
      simp only [evalE] at he ⊢
      exact h t m r (by simp [exprRefs]) he
  | union a b iha ihb =>
      intro hcb hts h he
      simp only [containsBool, Bool.or_eq_false_iff] at hcb
      simp only [evalE, Bool.or_eq_true] at he ⊢
      rcases he with he | he
      · exact Or.inl (iha hcb.1 (fun tt htt => hts tt (by simp [exprTtus, htt]))
          (fun t' m' r' hk => h t' m' r' (by simp [exprRefs, hk])) he)
      · exact Or.inr (ihb hcb.2 (fun tt htt => hts tt (by simp [exprTtus, htt]))
          (fun t' m' r' hk => h t' m' r' (by simp [exprRefs, hk])) he)
  | inter _ _ _ _ => intro hcb; simp [containsBool] at hcb
  | excl _ _ _ _ => intro hcb; simp [containsBool] at hcb
  | direct rs =>
      intro _ _ h he
      simp only [evalE] at he ⊢
      apply directLeaf_of_mog
      unfold directLeaf at he
      rw [if_neg (by simpa using hs), if_neg (by simpa using hr1), Bool.or_eq_true] at he
      rcases he with he | he
      · obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp he
        have hgT := (grantsOf_elim hg).1
        simp only [Bool.or_eq_true, Bool.and_eq_true, bne_iff_ne, ne_eq, beq_iff_eq] at hgt
        rcases hgt with ⟨⟨⟨⟨hgn, hgp⟩, h1⟩, h2⟩, h3⟩ | ⟨⟨⟨hgn, hgp⟩, _⟩, _⟩
        · unfold memberOfGranted
          refine List.any_eq_true.mpr ⟨g, hg, ?_⟩
          rw [if_neg (by simpa using hgp), if_pos (by simpa using hgn), h1, h2, h3]
          exact hseed
        · exact absurd (hNUS g hgT hgn) hgp
      · unfold memberOfGranted at he ⊢
        obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp he
        refine List.any_eq_true.mpr ⟨g, hg, ?_⟩
        by_cases hb : (g.subject.predicate == BARE) = true
        · simp [hb] at hgt
        · have hbne : g.subject.predicate ≠ BARE := by simpa using hb
          by_cases hn : (g.subject.name != STAR) = true
          · rw [if_neg hb, if_pos hn] at hgt ⊢
            exact h _ _ _ (restrictionMatches_exprRefs (grantsOf_elim hg).2.2.2.2 hbne) hgt
          · exfalso
            have hstar : g.subject.name = STAR := by simpa using hn
            exact hbne (hNUS g (grantsOf_elim hg).1 hstar)
  | ttu tr ts =>
      intro _ hts h he
      simp only [evalE] at he ⊢
      have hnostar : ∀ tup ∈ T, tup.subject.name = STAR →
          ¬(tup.relation = ts ∧ tup.object.type = t) :=
        hts (tr, ts) (by simp [exprTtus])
      obtain ⟨tup, htup, hrel, hot, hcon, hpn, hcase⟩ := ttuLeaf_elim_nss hnostar he
      refine ttuLeaf_intro_rec htup hrel hot hcon hpn ?_
      rcases hcase with ⟨h1, h2, h3⟩ | hrec
      · simp only at h1 h2 h3
        rw [← h1, ← h2, ← h3]
        exact hseed
      · exact h _ _ _ (ttu_parent_exprRefs hDecl htup hrel hot) hrec

/-- **A2.** A seed subject `T:o#r1`'s base membership in an untainted node transfers to the
    reflexive subject `s`, at a fuel offset `D` from which the seed node holds. -/
theorem semAux_switch_untainted (S : Schema) (T : Store) (hDecl : StoreDeclared S T)
    (hNUS : NoUsersetStar T) (hNSP : NoStarParentsU S T)
    {s : SubjectRef} (hs : s.name ≠ STAR) {r1 : String} (hr1 : r1 ≠ BARE)
    (q1 q2 : Query) (D : Nat)
    (hseed : ∀ f, semAuxR S s T q2 (f + D) s.type s.name r1 = true) :
    ∀ f t m r, (t, r) ∈ S.keys → isDerived S (t, r) = false →
      semAux S ⟨s.type, s.name, r1⟩ T q1 f t m r = true →
      semAuxR S s T q2 (f + D) t m r = true := by
  intro f
  induction f with
  | zero => intro t m r _ _ h; simp [semAux] at h
  | succ f ih =>
      intro t m r hk hu h
      obtain ⟨e, hlk⟩ := lookup_some_of_mem S hk
      obtain ⟨hcb, hrefs⟩ := untainted_def hlk hu
      rw [semAux, step, hlk] at h
      have hts : ∀ tt ∈ exprTtus e, ∀ tup ∈ T, tup.subject.name = STAR →
          ¬(tup.relation = tt.2 ∧ tup.object.type = t) :=
        fun tt htt tup htup hstar => hNSP tup htup hstar (t, r) e hlk hu tt htt
      have hev : evalE (semAuxR S s T q2 (f + D)) s T q2 t m r e = true :=
        evalE_switch hDecl hNUS hs hr1 (hseed f) t m r e hcb hts (fun t' m' r' hk' h1 => by
          by_cases hdecl : (t', r') ∈ S.keys
          · exact ih t' m' r' hdecl (isDerived_false_of_untainted (hrefs _ hk')) h1
          · rw [semAux_undeclared S _ T q1 hdecl f m'] at h1; exact absurd h1 (by simp)) h
      have hfuel : f + 1 + D = (f + D) + 1 := by omega
      rw [hfuel, semAuxR, stepR, hlk]
      exact (Bool.or_eq_true _ _).mpr (Or.inr hev)

/-! ## A1 -- the base membership is a reflexive one (untainted) -/

theorem semAux_imp_semAuxR_untainted (S : Schema) (T : Store) (q : Query)
    (hDecl : StoreDeclared S T) (s : SubjectRef) :
    ∀ f t m r, (t, r) ∈ S.keys → isDerived S (t, r) = false →
      semAux S s T q f t m r = true → semAuxR S s T q f t m r = true := by
  intro f
  induction f with
  | zero => intro t m r _ _ h; simp [semAux] at h
  | succ f ih =>
      intro t m r hk hu h
      obtain ⟨e, hlk⟩ := lookup_some_of_mem S hk
      obtain ⟨hcb, hrefs⟩ := untainted_def hlk hu
      rw [semAux, step, hlk] at h
      rw [semAuxR, stepR, hlk]
      refine (Bool.or_eq_true _ _).mpr (Or.inr ?_)
      refine evalE_mono_on hDecl s t m r e (noExcl_of_containsBool_false e hcb) ?_ h
      intro t' m' r' hk' _ h1
      by_cases hdecl : (t', r') ∈ S.keys
      · exact ih t' m' r' hdecl (isDerived_false_of_untainted (hrefs _ hk')) h1
      · rw [semAux_undeclared S s T q hdecl f m'] at h1; exact absurd h1 (by simp)

/-! ## A3 -- a reflexive membership decomposes (untainted) -/

/-- **Decomposition, one level.** A reflexive membership of `s` in a union-only node, under
    recursion `rec`, is a base membership of `s` (`Rs`), or a computed arm landing on a seed
    node of `s`'s own object, or a base membership of a seed subject `T:o#r1` (`Ru r1`) -- given
    that `rec` decomposes the same way on the consulted atoms. -/
theorem evalE_decomp {S : Schema} {T : Store} {q : Query} {rec Rs : Rec} {Ru : String → Rec}
    (hDecl : StoreDeclared S T) (hNUS : NoUsersetStar T)
    {s : SubjectRef} (hs : s.name ≠ STAR) (hsp : s.predicate ≠ BARE)
    (seeds : List String) (hsb : ∀ r1 ∈ seeds, r1 ≠ BARE) (t m R : String) :
    ∀ e : Expr, containsBool e = false →
      (∀ tt ∈ exprTtus e, ∀ tup ∈ T, tup.subject.name = STAR →
          ¬(tup.relation = tt.2 ∧ tup.object.type = t)) →
      (∀ t' m' r', (t', r') ∈ exprRefs S t e → rec t' m' r' = true →
          Rs t' m' r' = true ∨ (∃ r1 ∈ seeds, t' = s.type ∧ m' = s.name ∧ r' = r1)
            ∨ (∃ r1 ∈ seeds, Ru r1 t' m' r' = true)) →
      evalE rec s T q t m R e = true →
      evalE Rs s T q t m R e = true
        ∨ (∃ r1 ∈ seeds, ∃ r' ∈ computedRefs e, t = s.type ∧ m = s.name ∧ r' = r1)
        ∨ (∃ r1 ∈ seeds, evalE (Ru r1) ⟨s.type, s.name, r1⟩ T q t m R e = true) := by
  intro e
  induction e with
  | computed r =>
      intro _ _ h he
      simp only [evalE] at he ⊢
      rcases h t m r (by simp [exprRefs]) he with h1 | ⟨r1, hr1, h2, h3, h4⟩ | ⟨r1, hr1, h5⟩
      · exact Or.inl h1
      · exact Or.inr (Or.inl ⟨r1, hr1, r, by simp [computedRefs], h2, h3, h4⟩)
      · exact Or.inr (Or.inr ⟨r1, hr1, h5⟩)
  | union a b iha ihb =>
      intro hcb hts h he
      simp only [containsBool, Bool.or_eq_false_iff] at hcb
      simp only [evalE, Bool.or_eq_true] at he ⊢
      have hA := fun hea => iha hcb.1 (fun tt htt => hts tt (by simp [exprTtus, htt]))
        (fun t' m' r' hk => h t' m' r' (by simp [exprRefs, hk])) hea
      have hB := fun heb => ihb hcb.2 (fun tt htt => hts tt (by simp [exprTtus, htt]))
        (fun t' m' r' hk => h t' m' r' (by simp [exprRefs, hk])) heb
      rcases he with he | he
      · rcases hA he with h1 | ⟨r1, hr1, r', hr', h2⟩ | ⟨r1, hr1, h3⟩
        · exact Or.inl (Or.inl h1)
        · exact Or.inr (Or.inl ⟨r1, hr1, r', by simp [computedRefs, hr'], h2⟩)
        · exact Or.inr (Or.inr ⟨r1, hr1, Or.inl h3⟩)
      · rcases hB he with h1 | ⟨r1, hr1, r', hr', h2⟩ | ⟨r1, hr1, h3⟩
        · exact Or.inl (Or.inr h1)
        · exact Or.inr (Or.inl ⟨r1, hr1, r', by simp [computedRefs, hr'], h2⟩)
        · exact Or.inr (Or.inr ⟨r1, hr1, Or.inr h3⟩)
  | inter _ _ _ _ => intro hcb; simp [containsBool] at hcb
  | excl _ _ _ _ => intro hcb; simp [containsBool] at hcb
  | direct rs =>
      intro _ _ h he
      simp only [evalE] at he ⊢
      have he' := he
      unfold directLeaf at he'
      rw [if_neg (by simpa using hs), if_neg (by simpa using hsp), Bool.or_eq_true] at he'
      rcases he' with he' | he'
      · -- the rec-free match part holds for `Rs` too
        left
        unfold directLeaf
        rw [if_neg (by simpa using hs), if_neg (by simpa using hsp), Bool.or_eq_true]
        exact Or.inl he'
      · unfold memberOfGranted at he'
        obtain ⟨g, hg, hgt⟩ := List.any_eq_true.mp he'
        by_cases hb : (g.subject.predicate == BARE) = true
        · simp [hb] at hgt
        · have hbne : g.subject.predicate ≠ BARE := by simpa using hb
          by_cases hn : (g.subject.name != STAR) = true
          · rw [if_neg hb, if_pos hn] at hgt
            have hgn : g.subject.name ≠ STAR := by simpa using hn
            rcases h _ _ _ (restrictionMatches_exprRefs (grantsOf_elim hg).2.2.2.2 hbne) hgt
              with h1 | ⟨r1, hr1, h2, h3, h4⟩ | ⟨r1, hr1, h5⟩
            · left
              apply directLeaf_of_mog
              unfold memberOfGranted
              refine List.any_eq_true.mpr ⟨g, hg, ?_⟩
              rw [if_neg hb, if_pos hn]
              exact h1
            · right; right
              refine ⟨r1, hr1, ?_⟩
              have hgs : g.subject = ⟨s.type, s.name, r1⟩ := by
                rcases g with ⟨⟨gt, gn, gp⟩, grel, gobj⟩
                simp only at h2 h3 h4 ⊢
                subst h2; subst h3; subst h4; rfl
              exact directLeaf_of_match hs (hsb r1 hr1) hg hgs
            · right; right
              refine ⟨r1, hr1, ?_⟩
              apply directLeaf_of_mog
              unfold memberOfGranted
              refine List.any_eq_true.mpr ⟨g, hg, ?_⟩
              rw [if_neg hb, if_pos hn]
              exact h5
          · exfalso
            have hstar : g.subject.name = STAR := by simpa using hn
            exact hbne (hNUS g (grantsOf_elim hg).1 hstar)
  | ttu tr ts =>
      intro _ hts h he
      simp only [evalE] at he ⊢
      have hnostar : ∀ tup ∈ T, tup.subject.name = STAR →
          ¬(tup.relation = ts ∧ tup.object.type = t) :=
        hts (tr, ts) (by simp [exprTtus])
      obtain ⟨tup, htup, hrel, hot, hcon, hpn, hcase⟩ := ttuLeaf_elim_nss hnostar he
      rcases hcase with hself | hrec
      · exact Or.inl (ttuLeaf_intro_self htup hrel hot hcon hpn hself)
      · rcases h _ _ _ (ttu_parent_exprRefs hDecl htup hrel hot) hrec
          with h1 | ⟨r1, hr1, h2, h3, h4⟩ | ⟨r1, hr1, h5⟩
        · exact Or.inl (ttuLeaf_intro_rec htup hrel hot hcon hpn h1)
        · right; right
          exact ⟨r1, hr1, ttuLeaf_intro_self htup hrel hot hcon hpn
            ⟨h2.symm, h3.symm, h4.symm⟩⟩
        · right; right
          exact ⟨r1, hr1, ttuLeaf_intro_rec htup hrel hot hcon hpn h5⟩

/-- **A3.** A reflexive membership of `s` in an untainted node, at any fuel, is a base
    membership of `s`, or the node is a seed node of `s`'s own object, or a base membership of
    a seed subject -- given the seed list contains `s`'s own relation (when untainted) and is
    closed under untainted computed predecessors on `s`'s type. -/
theorem semAuxR_untainted_decomp (S : Schema) (T : Store) (q : Query)
    (hDecl : StoreDeclared S T) (hNUS : NoUsersetStar T) (hNSP : NoStarParentsU S T)
    {s : SubjectRef} (hs : s.name ≠ STAR) (hsp : s.predicate ≠ BARE)
    (seeds : List String) (hsb : ∀ r1 ∈ seeds, r1 ≠ BARE)
    (hown : (s.type, s.predicate) ∈ S.keys → isDerived S (s.type, s.predicate) = false →
      s.predicate ∈ seeds)
    (hclosed : ∀ R' e', S.lookup (s.type, R') = some e' → isDerived S (s.type, R') = false →
      ∀ r1 ∈ seeds, r1 ∈ computedRefs e' → R' ∈ seeds) :
    ∀ f t m r, (t, r) ∈ S.keys → isDerived S (t, r) = false →
      semAuxR S s T q f t m r = true →
      semAux S s T q f t m r = true ∨ (∃ r1 ∈ seeds, t = s.type ∧ m = s.name ∧ r = r1)
        ∨ (∃ r1 ∈ seeds, semAux S ⟨s.type, s.name, r1⟩ T q f t m r = true) := by
  intro f
  induction f with
  | zero => intro t m r _ _ h; simp [semAuxR] at h
  | succ f ih =>
      intro t m r hk hu h
      obtain ⟨e, hlk⟩ := lookup_some_of_mem S hk
      obtain ⟨hcb, hrefs⟩ := untainted_def hlk hu
      rw [semAuxR, stepR, hlk, Bool.or_eq_true] at h
      rcases h with hsh | hev
      · -- the self hit: the node is s's own, a seed
        unfold selfHit at hsh
        simp only [Bool.and_eq_true, bne_iff_ne, ne_eq, beq_iff_eq] at hsh
        obtain ⟨⟨⟨⟨_, _⟩, h1⟩, h2⟩, h3⟩ := hsh
        subst h1; subst h2; subst h3
        exact Or.inr (Or.inl ⟨s.predicate, hown hk hu, rfl, rfl, rfl⟩)
      · have hts : ∀ tt ∈ exprTtus e, ∀ tup ∈ T, tup.subject.name = STAR →
            ¬(tup.relation = tt.2 ∧ tup.object.type = t) :=
          fun tt htt tup htup hstar => hNSP tup htup hstar (t, r) e hlk hu tt htt
        rcases evalE_decomp (Rs := semAux S s T q f)
            (Ru := fun r1 => semAux S ⟨s.type, s.name, r1⟩ T q f)
            hDecl hNUS hs hsp seeds hsb t m r e hcb hts (fun t' m' r' hk' h1 => by
              by_cases hdecl : (t', r') ∈ S.keys
              · exact ih t' m' r' hdecl (isDerived_false_of_untainted (hrefs _ hk')) h1
              · rw [semAuxR_undeclared S s T q hdecl f m'] at h1
                exact absurd h1 (by simp)) hev
          with h1 | ⟨r1, hr1, r', hr', h2, h3, h4⟩ | ⟨r1, hr1, h5⟩
        · left; rw [semAux, step, hlk]; exact h1
        · right; left
          subst h2; subst h3; subst h4
          exact ⟨r, hclosed r e hlk hu r' hr1 hr', rfl, rfl, rfl⟩
        · right; right
          exact ⟨r1, hr1, by rw [semAux, step, hlk]; exact h5⟩

/-! ## The seed relations -/

/-- **The seed relations of a userset subject** (TK144): the declared untainted relations on
    the subject's type whose node at the subject's object holds the subject by the
    self-relation on the EMPTY store -- i.e. through computed arms alone. The Lean model of
    `src/zanzibar/schema/compiler.py::_self_seed_table` restricted to declared relations
    (Python's table also names compiled leaf predicates, which the model's derived read
    abstracts as reads of the public operands, exactly as `GraphState.checkFnR` does). -/
def seedRels (S : Schema) (s : SubjectRef) : List String :=
  (S.keys.filter (fun k => k.1 == s.type && !(isDerived S k) &&
    semR S [] ⟨s, k.2, ⟨s.type, s.name⟩⟩)).map Prod.snd

theorem mem_seedRels {S : Schema} {s : SubjectRef} {r1 : String} :
    r1 ∈ seedRels S s ↔ (s.type, r1) ∈ S.keys ∧ isDerived S (s.type, r1) = false ∧
      semR S [] ⟨s, r1, ⟨s.type, s.name⟩⟩ = true := by
  unfold seedRels
  simp only [List.mem_map, List.mem_filter, Bool.and_eq_true, beq_iff_eq, Bool.not_eq_true']
  constructor
  · rintro ⟨⟨kt, kr⟩, ⟨hk, ⟨h1, h2⟩, h3⟩, rfl⟩
    simp only at h1 h2 h3
    subst h1
    exact ⟨hk, h2, h3⟩
  · rintro ⟨hk, h2, h3⟩
    exact ⟨(s.type, r1), ⟨hk, ⟨rfl, h2⟩, h3⟩, rfl⟩

theorem storeDeclared_nil (S : Schema) : StoreDeclared S [] := by
  intro tup htup; simp at htup

/-- Store monotonicity from the EMPTY store, untainted. -/
theorem semAuxR_nil_imp (S : Schema) (T : Store) (s : SubjectRef) (q1 q2 : Query) :
    ∀ f t m r, (t, r) ∈ S.keys → isDerived S (t, r) = false →
      semAuxR S s [] q1 f t m r = true → semAuxR S s T q2 f t m r = true := by
  intro f
  induction f with
  | zero => intro t m r _ _ h; simp [semAuxR] at h
  | succ f ih =>
      intro t m r hk hu h
      obtain ⟨e, hlk⟩ := lookup_some_of_mem S hk
      obtain ⟨hcb, hrefs⟩ := untainted_def hlk hu
      rw [semAuxR, stepR, hlk, Bool.or_eq_true] at h
      rw [semAuxR, stepR, hlk, Bool.or_eq_true]
      rcases h with h | h
      · exact Or.inl h
      · right
        obtain ⟨r', hr', hrec⟩ := evalE_nil_computed hcb h
        have hk' : (t, r') ∈ S.keys := by
          by_contra hn
          rw [semAuxR_undeclared S s [] q1 hn f m] at hrec
          exact absurd hrec (by simp)
        have hu' : isDerived S (t, r') = false :=
          isDerived_false_of_untainted (hrefs _ (computedRefs_exprRefs hr'))
        exact evalE_of_computed (ih t m r' hk' hu' hrec) hcb hr'

theorem fuelBound_nil_le (S : Schema) (T : Store) : fuelBound S [] ≤ fuelBound S T := by
  unfold fuelBound
  exact Nat.mul_le_mul_left _ (by simp)

/-- **S1 (soundness).** A seed's node holds the subject on the real store. -/
theorem seedRels_sound (S : Schema) (T : Store) (hDecl : StoreDeclared S T)
    {s : SubjectRef} {r1 : String} (hr : r1 ∈ seedRels S s) :
    semR S T ⟨s, r1, ⟨s.type, s.name⟩⟩ = true := by
  obtain ⟨hk, hu, hsem⟩ := mem_seedRels.mp hr
  set q : Query := ⟨s, r1, ⟨s.type, s.name⟩⟩ with hq
  have h0 : semAuxR S s T q (fuelBound S []) s.type s.name r1 = true :=
    semAuxR_nil_imp S T s q q _ s.type s.name r1 hk hu hsem
  have hmono : ∀ d, semAuxR S s T q (fuelBound S [] + d) s.type s.name r1 = true := by
    intro d
    induction d with
    | zero => simpa using h0
    | succ d ihd =>
        have := semAuxR_mono_untainted S T q hDecl (fuelBound S [] + d) s.type r1 hk
          (untainted_of_isDerived_false hu) s.name (List.mem_cons_self ..) ihd
        simpa [Nat.add_assoc] using this
  have hfb := fuelBound_nil_le S T
  obtain ⟨d, hd⟩ : ∃ d, fuelBound S T = fuelBound S [] + d := ⟨_, (Nat.add_sub_cancel' hfb).symm⟩
  unfold semR
  rw [hd]
  exact hmono d

/-- **S3.** The subject's own (untainted, declared) relation is a seed. -/
theorem seedRels_own (S : Schema) {s : SubjectRef} (hs : s.name ≠ STAR) (hsp : s.predicate ≠ BARE)
    (hk : (s.type, s.predicate) ∈ S.keys) (hu : isDerived S (s.type, s.predicate) = false) :
    s.predicate ∈ seedRels S s := by
  refine mem_seedRels.mpr ⟨hk, hu, ?_⟩
  obtain ⟨e, hlk⟩ := lookup_some_of_mem S hk
  have hpos : 0 < fuelBound S [] := by
    unfold fuelBound
    have : 0 < S.keys.length := List.length_pos_of_mem hk
    exact Nat.mul_pos this (by decide)
  obtain ⟨f, hf⟩ : ∃ f, fuelBound S [] = f + 1 := ⟨_, (Nat.succ_pred_eq_of_pos hpos).symm⟩
  unfold semR
  simp only
  rw [hf, semAuxR, stepR, hlk]
  have : selfHit s s.type s.name s.predicate = true := by
    unfold selfHit; simp [hs, hsp]
  rw [this]; rfl

/-- **S2 (closure).** An untainted relation with a computed arm to a seed is a seed. -/
theorem seedRels_closed (S : Schema) (hStrat : Stratifiable S) {s : SubjectRef} {R' : String}
    {e' : Expr} (hlk : S.lookup (s.type, R') = some e') (hu : isDerived S (s.type, R') = false)
    {r1 : String} (hr1 : r1 ∈ seedRels S s) (hcr : r1 ∈ computedRefs e') :
    R' ∈ seedRels S s := by
  have hk : (s.type, R') ∈ S.keys := by
    by_contra hn; rw [lookup_eq_none S hn] at hlk; simp at hlk
  refine mem_seedRels.mpr ⟨hk, hu, ?_⟩
  obtain ⟨_, _, hsem⟩ := mem_seedRels.mp hr1
  have hcb := (untainted_def hlk hu).1
  set q' : Query := ⟨s, R', ⟨s.type, s.name⟩⟩ with hq'
  have hdecl0 := storeDeclared_nil S
  have hseed : semAuxR S s [] q' (fuelBound S []) s.type s.name r1 = true := by
    rw [semAuxR_stable_at S [] hStrat hdecl0 s q' s.type s.name r1 _ (le_refl _)]
    exact hsem
  have hstep : semAuxR S s [] q' (fuelBound S [] + 1) s.type s.name R' = true := by
    rw [semAuxR, stepR, hlk, Bool.or_eq_true]
    exact Or.inr (evalE_of_computed hseed hcb hcr)
  rw [← semR_fuel_stable S [] q' hStrat hdecl0 (fuelBound S [] + 1) (by omega)]
  exact hstep

theorem seedRels_bare (S : Schema) (hWF : WF S) {s : SubjectRef} {r1 : String}
    (hr : r1 ∈ seedRels S s) : r1 ≠ BARE :=
  not_bare_of_mem_keys hWF (mem_seedRels.mp hr).1

/-! ## Claim A -- `semR` over `sem` at an untainted query with a concrete userset subject -/

/-- The seed part of the untainted reflexive read: the query node is a seed node of the
    subject's own object, or a seed subject is a (base) member. -/
def seedPart (S : Schema) (T : Store) (q : Query) : Bool :=
  (seedRels S q.subject).any (fun r1 =>
    (q.object.type == q.subject.type && q.object.name == q.subject.name && q.relation == r1)
    || sem S T ⟨⟨q.subject.type, q.subject.name, r1⟩, q.relation, q.object⟩)

/-- **Claim A.** On an untainted query with a concrete userset subject, the reflexive spec is
    the base spec OR the seed part. -/
theorem semR_untainted_userset (S : Schema) (T : Store) (q : Query) (hWF : WF S)
    (hStrat : Stratifiable S) (hDecl : StoreDeclared S T) (hNUS : NoUsersetStar T)
    (hNSP : NoStarParentsU S T)
    (hs : q.subject.name ≠ STAR) (hsp : q.subject.predicate ≠ BARE)
    (hu : isDerived S (q.object.type, q.relation) = false) :
    semR S T q = (sem S T q || seedPart S T q) := by
  have hsb : ∀ r1 ∈ seedRels S q.subject, r1 ≠ BARE := fun r1 hr => seedRels_bare S hWF hr
  by_cases hk : (q.object.type, q.relation) ∈ S.keys
  swap
  · -- undeclared: every part is false
    have h1 : semR S T q = false := by
      unfold semR; exact semAuxR_undeclared S _ T q hk _ _
    have h2 : sem S T q = false := by
      unfold sem; exact semAux_undeclared S _ T q hk _ _
    have h3 : seedPart S T q = false := by
      unfold seedPart
      apply List.any_eq_false.mpr
      intro r1 hr1 hcontra
      have hk1 := (mem_seedRels.mp hr1).1
      rw [Bool.or_eq_true] at hcontra
      rcases hcontra with hc | hc
      · simp only [Bool.and_eq_true, beq_iff_eq] at hc
        obtain ⟨⟨h1, _⟩, h3⟩ := hc
        exact hk (by rw [h1, h3]; exact hk1)
      · have hsem : sem S T ⟨⟨q.subject.type, q.subject.name, r1⟩, q.relation, q.object⟩
            = false := by
          unfold sem; exact semAux_undeclared S _ T _ hk _ _
        rw [hsem] at hc
        exact Bool.false_ne_true hc
    rw [h1, h2, h3]; rfl
  apply Bool.eq_iff_iff.mpr
  rw [Bool.or_eq_true]
  constructor
  · -- (⟹) A3 at fuelBound
    intro hR
    have hdec := semAuxR_untainted_decomp S T q hDecl hNUS hNSP hs hsp
      (seedRels S q.subject) hsb
      (fun hk' hu' => seedRels_own S hs hsp hk' hu')
      (fun R' e' hlk' hu' r1 hr1 hcr => seedRels_closed S hStrat hlk' hu' hr1 hcr)
      (fuelBound S T) q.object.type q.object.name q.relation hk hu hR
    rcases hdec with h1 | ⟨r1, hr1, h2, h3, h4⟩ | ⟨r1, hr1, h5⟩
    · exact Or.inl h1
    · right
      unfold seedPart
      refine List.any_eq_true.mpr ⟨r1, hr1, ?_⟩
      simp [h2, h3, h4]
    · right
      unfold seedPart
      refine List.any_eq_true.mpr ⟨r1, hr1, ?_⟩
      rw [Bool.or_eq_true]
      right
      unfold sem
      rw [← semAux_qirrel S ⟨q.subject.type, q.subject.name, r1⟩ T q]
      exact h5
  · -- (⟸)
    rintro (h | h)
    · exact semAux_imp_semAuxR_untainted S T q hDecl q.subject _ _ _ _ hk hu h
    · unfold seedPart at h
      obtain ⟨r1, hr1, hor⟩ := List.any_eq_true.mp h
      rw [Bool.or_eq_true] at hor
      have hsound := seedRels_sound S T hDecl hr1
      rcases hor with hc | hm
      · simp only [Bool.and_eq_true, beq_iff_eq] at hc
        obtain ⟨⟨h1, h2⟩, h3⟩ := hc
        have hq : q = ⟨q.subject, r1, ⟨q.subject.type, q.subject.name⟩⟩ := by
          obtain ⟨qs, qr, ⟨qot, qon⟩⟩ := q
          simp only at h1 h2 h3 ⊢
          subst h1; subst h2; subst h3; rfl
        rw [hq]; exact hsound
      · -- A2 with offset fuelBound
        have hseed : ∀ f, semAuxR S q.subject T q (f + fuelBound S T)
            q.subject.type q.subject.name r1 = true := by
          intro f
          rw [semAuxR_stable_at S T hStrat hDecl q.subject q q.subject.type q.subject.name r1
            _ (by omega)]
          exact hsound
        have h2 := semAux_switch_untainted S T hDecl hNUS hNSP hs (hsb r1 hr1)
          ⟨⟨q.subject.type, q.subject.name, r1⟩, q.relation, q.object⟩ q (fuelBound S T) hseed
          (fuelBound S T) q.object.type q.object.name q.relation hk hu hm
        have hst := semR_fuel_stable S T q hStrat hDecl (fuelBound S T + fuelBound S T)
          (by omega)
        rw [← hst]
        exact h2

end Zanzibar
