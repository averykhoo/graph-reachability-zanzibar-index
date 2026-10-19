import ZanzibarProofs.GraphIndex.SelfBridge
import ZanzibarProofs.GraphIndex.Exec
import ZanzibarProofs.SetEngine.SelfRelation

/-!
# The reflexive graph read and the headline theorems over `semR` (TK144)

**Model source:** `src/zanzibar/graphindex/wildcard.py::WildcardIndex._check_internal` (the
untainted branch's `seed_keys` probes) and `::WildcardIndex._check_derived` (the `reflexive`
branch, challenge C5: a concrete userset subject on a derived relation is answered by the
self hit or by the relation's plan evaluated at read time, `::_derived_read_eval`), behind
the public leaf-name fence `::WildcardIndex.check`.

* `GraphModel.checkRAux` / `checkR` -- the read. On a bare or star subject it IS the base
  read `GraphModel.check` (the self-relation never fires there). On a concrete userset
  subject:
  - **untainted relation:** the base read, OR the query node is a seed node of the subject's
    own object, OR the base read FROM a seed subject `T:o#r1` (`seedRels`) -- Python's probes
    from the seed nodes;
  - **derived relation:** the self hit, OR the relation's definition evaluated with every
    operand read reflexively (`checkRAux` one level down). The definition's `Direct` arms
    are evaluated over the EMPTY store: on the fragment they carry bare restrictions only
    (`W4Fragment.directArmsBare`), so for a userset subject they are false on every store
    (`directLeaf_bareArms_userset`) -- the model of Python's storage-leaf probe, which no
    userset edge reaches. A budget (`keys.length + 1`) bounds the derived recursion; the
    fragment's two strata need three levels (`checkRAux_derived_top`), which a second
    declared derived key guarantees (`graph_correctR`'s budget split).
* `graph_correctR` -- T2b for the spec: `checkR = semR` under exactly `graph_correct`'s
  hypotheses. Proved FROM `graph_correct` (the base read is the base spec at every subject,
  the seed subjects included) and `SelfBridge.lean::semR_untainted_userset`.
* `checkPublicR`, `graph_correct_publicR`, `backend_equivalenceR`, `exclusion_effectiveR`,
  `no_ghost_grantR` -- the fenced read and the T3 / T6 family over `semR`, mirroring
  `FullScope.lean`.

**Modelling gap, recorded (`CORRESPONDENCE.md` §7):** the Python seed probes gate a seed
SHAPE's `w_any` probe on the entity's witness (`_entity_has_witness`, the twin of the
oracle's `instances`), while `checkR`'s seed part reads the base read per seed subject,
whose `w_any` probe is unconditional. The two differ only on a userset-wildcard shape
`[T:*#r1]`, which `W4Fragment.wsBare` / `bareStar` exclude, so on every state the theorems
cover they agree.
-/

namespace Zanzibar

namespace GraphModel

/-- The reflexive graph read at derived-recursion budget `n` (TK144). -/
def checkRAux (σ : GraphState) : Nat → Query → Bool
  | 0, q => check σ q
  | n + 1, q =>
    if (q.subject.predicate != BARE && q.subject.name != STAR) = true then
      if isDerived σ.schema (q.object.type, q.relation) = true then
        if q.object.name = STAR then false
        else
          match σ.schema.lookup (q.object.type, q.relation) with
          | none => false
          | some e =>
              selfHit q.subject q.object.type q.object.name q.relation ||
              evalE (fun ot on r => checkRAux σ n ⟨q.subject, r, ⟨ot, on⟩⟩) q.subject [] q
                q.object.type q.object.name q.relation e
      else
        check σ q || (seedRels σ.schema q.subject).any (fun r1 =>
          (q.object.type == q.subject.type && q.object.name == q.subject.name
            && q.relation == r1)
          || check σ ⟨⟨q.subject.type, q.subject.name, r1⟩, q.relation, q.object⟩)
    else check σ q

/-- **The reflexive graph read** (TK144) -- `_check_internal` with the self-relation. -/
def checkR (σ : GraphState) (q : Query) : Bool :=
  checkRAux σ (σ.schema.keys.length + 1) q

/-- **The reflexive PUBLIC read** -- the leaf-name fence, then `checkR`
    (`WildcardIndex.check`). -/
def checkPublicR (σ : GraphState) (q : Query) : Bool :=
  if (publicOfLeaf σ.schema q.object.type q.relation).isSome then false
  else checkR σ q

end GraphModel

/-! ## Helpers -/

/-- A `Direct` arm with bare restrictions is false for a concrete userset subject, on any
    store: its grants all carry bare subjects. -/
theorem directLeaf_bareArms_userset {rec : Rec} {s : SubjectRef} {T : Store} {q : Query}
    {rs : List Restriction} {ot on rel : String} (hb : ∀ r ∈ rs, r.2.1 = BARE)
    (hs : s.name ≠ STAR) (hsp : s.predicate ≠ BARE) :
    directLeaf rec s T q rs ot on rel = false := by
  have hg := grantsOf_bare_subjects T rs ot on rel hb
  unfold directLeaf
  rw [if_neg (by simpa using hs), if_neg (by simpa using hsp),
    memberOfGranted_of_bareGrants rec T q _ hg, Bool.or_false]
  rw [List.any_eq_false]
  intro g hgm
  simp [hg g hgm]

/-- The derived-definition congruence for a concrete userset subject: on a
    `ComputedOrDirect` tree with bare `Direct` arms, the store and the recursion matter
    only at the computed references. -/
theorem evalE_cd_userset {rec1 rec2 : Rec} {s : SubjectRef} {T1 T2 : Store} {q1 q2 : Query}
    {dt on rel : String} (hs : s.name ≠ STAR) (hsp : s.predicate ≠ BARE) :
    ∀ e : Expr, ComputedOrDirect e → DirectArmsBare e →
      (∀ r' ∈ computedRefs e, rec1 dt on r' = rec2 dt on r') →
      evalE rec1 s T1 q1 dt on rel e = evalE rec2 s T2 q2 dt on rel e := by
  intro e
  induction e with
  | computed r' =>
      intro _ _ hag; simp only [evalE]; exact hag r' (List.mem_singleton.mpr rfl)
  | direct rs =>
      intro _ hb _
      simp only [evalE]
      rw [directLeaf_bareArms_userset hb hs hsp, directLeaf_bareArms_userset hb hs hsp]
  | ttu _ _ => intro hcd; exact hcd.elim
  | union a b iha ihb =>
      intro hcd hba hag; simp only [evalE]
      rw [iha hcd.1 hba.1 (fun r' hr' => hag r' (List.mem_append_left _ hr')),
        ihb hcd.2 hba.2 (fun r' hr' => hag r' (List.mem_append_right _ hr'))]
  | inter a b iha ihb =>
      intro hcd hba hag; simp only [evalE]
      rw [iha hcd.1 hba.1 (fun r' hr' => hag r' (List.mem_append_left _ hr')),
        ihb hcd.2 hba.2 (fun r' hr' => hag r' (List.mem_append_right _ hr'))]
  | excl a b iha ihb =>
      intro hcd hba hag; simp only [evalE]
      rw [iha hcd.1 hba.1 (fun r' hr' => hag r' (List.mem_append_left _ hr')),
        ihb hcd.2 hba.2 (fun r' hr' => hag r' (List.mem_append_right _ hr'))]

theorem directArmsBare_of_computedOnly : ∀ {e : Expr}, ComputedOnly e → DirectArmsBare e := by
  intro e
  induction e with
  | computed _ => intro _; trivial
  | direct _ => intro h; exact h.elim
  | ttu _ _ => intro h; exact h.elim
  | union a b iha ihb => intro h; exact ⟨iha h.1, ihb h.2⟩
  | inter a b iha ihb => intro h; exact ⟨iha h.1, ihb h.2⟩
  | excl a b iha ihb => intro h; exact ⟨iha h.1, ihb h.2⟩

/-- A computed reference never names a minted leaf (`GraphAdmission.computedRefsNotLeaf` +
    `keysNonempty`), so the fence never fires at it. -/
theorem publicOfLeaf_none_of_notLeafName {S : Schema}
    (hKN : S.keys.all (fun k => k.2 != "") = true) {ty r : String} (h : NotLeafName r) :
    publicOfLeaf S ty r = none := by
  rcases h with h | h
  · subst h
    apply publicOfLeaf_untainted
    rw [leafPublic_bare]
    cases hd : isDerived S (ty, "") with
    | false => rfl
    | true => exact absurd rfl (hne_of_keys_nonempty hKN ty "" hd)
  · exact publicOfLeaf_not_leaf h

/-- The budget unfolding of the reflexive read on a concrete userset subject. -/
theorem checkRAux_succ_userset (σ : GraphState) (n : Nat) (q : Query)
    (hs : q.subject.name ≠ STAR) (hsp : q.subject.predicate ≠ BARE) :
    GraphModel.checkRAux σ (n + 1) q =
      if isDerived σ.schema (q.object.type, q.relation) = true then
        if q.object.name = STAR then false
        else
          match σ.schema.lookup (q.object.type, q.relation) with
          | none => false
          | some e =>
              selfHit q.subject q.object.type q.object.name q.relation ||
              evalE (fun ot on r => GraphModel.checkRAux σ n ⟨q.subject, r, ⟨ot, on⟩⟩)
                q.subject [] q q.object.type q.object.name q.relation e
      else
        GraphModel.check σ q || (seedRels σ.schema q.subject).any (fun r1 =>
          (q.object.type == q.subject.type && q.object.name == q.subject.name
            && q.relation == r1)
          || GraphModel.check σ ⟨⟨q.subject.type, q.subject.name, r1⟩, q.relation, q.object⟩) := by
  have hg : (q.subject.predicate != BARE && q.subject.name != STAR) = true := by simp [hs, hsp]
  rw [GraphModel.checkRAux, if_pos hg]

/-! ## The three levels of the reflexive read, at a reached drained state -/

section Levels

variable {S : Schema} {T : Store} {σ : GraphState}

/-- **Untainted level.** At any budget `≥ 1` the reflexive read of an untainted query with
    a concrete userset subject is `semR` -- `graph_correct` at the subject and at every seed
    subject, then Claim A. -/
theorem checkRAux_untainted (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ) (n : Nat) (q : Query)
    (hs : q.subject.name ≠ STAR) (hsp : q.subject.predicate ≠ BARE)
    (hqo : q.object.name ≠ STAR) (hql : publicOfLeaf S q.object.type q.relation = none)
    (hu : isDerived S (q.object.type, q.relation) = false) :
    GraphModel.checkRAux σ (n + 1) q = semR S T q := by
  have hsch : σ.schema = S := reachedByW3d2E_schema h
  rw [checkRAux_succ_userset σ n q hs hsp, hsch, if_neg (by rw [hu]; simp)]
  have hbase : ∀ (u : SubjectRef), u.name ≠ STAR →
      GraphModel.check σ ⟨u, q.relation, q.object⟩ = sem S T ⟨u, q.relation, q.object⟩ :=
    fun u hun => graph_correct ⟨u, q.relation, q.object⟩ hA hF h hq (fun h' => absurd h' hun)
      hqo hql
  have h0 : GraphModel.check σ q = sem S T q := hbase q.subject hs
  rw [h0, semR_untainted_userset S T q hA.wf hA.strat
    (storeDeclared_of_validRulesD hA.storeValid) hF.bareStar.noUsersetStar
    (noStarParentsU_of_ttuStarFree hA.nodup hF.ttuStarFree) hs hsp hu]
  unfold seedPart
  congr 1
  apply anyCongr
  intro r1 _
  rw [hbase ⟨q.subject.type, q.subject.name, r1⟩ hs]

/-- **Derived level.** At budget `n + 2`, the reflexive read of a derived query whose
    `ComputedOrDirect` / bare-arm definition has only operands the untainted level answers
    (`hops`), is `semR`. -/
theorem checkRAux_derived (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ) (n : Nat) (q : Query)
    (hs : q.subject.name ≠ STAR) (hsp : q.subject.predicate ≠ BARE)
    (hqo : q.object.name ≠ STAR)
    (hd : isDerived S (q.object.type, q.relation) = true) {e : Expr}
    (hlk : S.lookup (q.object.type, q.relation) = some e)
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hops : ∀ r' ∈ computedRefs e,
      GraphModel.checkRAux σ (n + 1) ⟨q.subject, r', ⟨q.object.type, q.object.name⟩⟩
        = semR S T ⟨q.subject, r', ⟨q.object.type, q.object.name⟩⟩) :
    GraphModel.checkRAux σ (n + 2) q = semR S T q := by
  have hsch : σ.schema = S := reachedByW3d2E_schema h
  have hDecl := storeDeclared_of_validRulesD hA.storeValid
  rw [checkRAux_succ_userset σ (n + 1) q hs hsp, hsch, if_pos hd, if_neg hqo, hlk]
  -- the spec side, one step above `fuelBound`
  have hst := semR_fuel_stable S T q hA.strat hDecl (fuelBound S T + 1) (by omega)
  rw [← hst, semAuxR, stepR, hlk]
  dsimp only
  congr 1
  refine evalE_cd_userset hs hsp e hcd hba (fun r' hr' => ?_)
  rw [hops r' hr', semAuxR_stable_at S T hA.strat hDecl q.subject q q.object.type
    q.object.name r' _ (le_refl _)]

/-- The untainted level, in the operand shape the derived level consumes. -/
theorem checkRAux_operand_untainted (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ) (n : Nat) (q : Query)
    (hs : q.subject.name ≠ STAR) (hsp : q.subject.predicate ≠ BARE)
    (hqo : q.object.name ≠ STAR) {e : Expr}
    (hlk : S.lookup (q.object.type, q.relation) = some e) {r' : String}
    (hr' : r' ∈ computedRefs e) (hu : isDerived S (q.object.type, r') = false) :
    GraphModel.checkRAux σ (n + 1) ⟨q.subject, r', ⟨q.object.type, q.object.name⟩⟩
      = semR S T ⟨q.subject, r', ⟨q.object.type, q.object.name⟩⟩ :=
  checkRAux_untainted hA hF h hq n _ hs hsp hqo
    (publicOfLeaf_none_of_notLeafName hA.keysNonempty
      (notLeafName_of_computedRef hA.computedRefsNotLeaf hlk hr')) hu

/-- **The two-strata read.** At budget `n + 3`, any derived query of the fragment. -/
theorem checkRAux_derived_top (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ) (n : Nat) (q : Query)
    (hs : q.subject.name ≠ STAR) (hsp : q.subject.predicate ≠ BARE)
    (hqo : q.object.name ≠ STAR)
    (hd : isDerived S (q.object.type, q.relation) = true) :
    GraphModel.checkRAux σ (n + 3) q = semR S T q := by
  obtain ⟨e, hlk⟩ := isDerived_declared hd
  refine checkRAux_derived hA hF h hq (n + 1) q hs hsp hqo hd hlk
    (hF.computedOrDirect _ _ e hlk hd) (hF.directArmsBare _ _ e hlk hd) (fun r' hr' => ?_)
  cases hdr : isDerived S (q.object.type, r') with
  | false => exact checkRAux_operand_untainted hA hF h hq (n + 1) q hs hsp hqo hlk hr' hdr
  | true =>
      -- a derived operand: computed-only, over untainted relations (two strata)
      obtain ⟨e', hlk'⟩ := isDerived_declared hdr
      have hco := hF.computedOnlyOperands _ _ e hlk hd r' hr' hdr e' hlk'
      refine checkRAux_derived hA hF h hq n _ hs hsp hqo hdr hlk'
        (computedOnly_computedOrDirect hco) (directArmsBare_of_computedOnly hco)
        (fun r'' hr'' => ?_)
      exact checkRAux_operand_untainted hA hF h hq n
        ⟨q.subject, r', ⟨q.object.type, q.object.name⟩⟩ hs hsp hqo hlk' hr''
        (hF.twoStrata _ _ e hlk hd r' hr' hdr e' hlk' r'' hr'')

/-- At budget `n + 2`, a derived query whose definition has NO derived operand. -/
theorem checkRAux_derived_flat (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ) (n : Nat) (q : Query)
    (hs : q.subject.name ≠ STAR) (hsp : q.subject.predicate ≠ BARE)
    (hqo : q.object.name ≠ STAR)
    (hd : isDerived S (q.object.type, q.relation) = true) {e : Expr}
    (hlk : S.lookup (q.object.type, q.relation) = some e)
    (hflat : ∀ r' ∈ computedRefs e, isDerived S (q.object.type, r') = false) :
    GraphModel.checkRAux σ (n + 2) q = semR S T q :=
  checkRAux_derived hA hF h hq n q hs hsp hqo hd hlk (hF.computedOrDirect _ _ e hlk hd)
    (hF.directArmsBare _ _ e hlk hd)
    (fun r' hr' => checkRAux_operand_untainted hA hF h hq n q hs hsp hqo hlk hr' (hflat r' hr'))

end Levels

/-! ## T2b over `semR` -/

/-- **T2b for the spec (`graph_correctR`, TK144).** At every fully-drained state of the
    operational closure, the reflexive graph read computes `semR` -- under exactly
    `graph_correct`'s hypotheses, query scope included (star subjects bare, objects
    concrete, not a leaf name). -/
theorem graph_correctR {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR)
    (hql : publicOfLeaf S q.object.type q.relation = none) :
    GraphModel.checkR σ q = semR S T q := by
  have hsch : σ.schema = S := reachedByW3d2E_schema h
  unfold GraphModel.checkR
  rw [hsch]
  by_cases hus : q.subject.predicate = BARE ∨ q.subject.name = STAR
  · -- bare or star subject: the base read, the base spec (B1)
    have hng : ¬ (q.subject.predicate != BARE && q.subject.name != STAR) = true := by
      rcases hus with hb | hst
      · simp [hb]
      · simp [hst]
    rw [GraphModel.checkRAux, if_neg hng, semR_eq_sem_of_not_userset S T q hus]
    exact graph_correct q hA hF h hq hqs hqo hql
  · have hsp : q.subject.predicate ≠ BARE := fun hb => hus (Or.inl hb)
    have hs : q.subject.name ≠ STAR := fun hst => hus (Or.inr hst)
    cases hd : isDerived S (q.object.type, q.relation) with
    | false => exact checkRAux_untainted hA hF h hq _ q hs hsp hqo hql hd
    | true =>
        obtain ⟨e, hlk⟩ := isDerived_declared hd
        have hk : (q.object.type, q.relation) ∈ S.keys := by
          by_contra hn; rw [lookup_eq_none S hn] at hlk; simp at hlk
        by_cases hflat : ∀ r' ∈ computedRefs e, isDerived S (q.object.type, r') = false
        · obtain ⟨m, hm⟩ : ∃ m, S.keys.length = m + 1 :=
            ⟨S.keys.length - 1, by have := List.length_pos_of_mem hk; omega⟩
          rw [hm]
          exact checkRAux_derived_flat hA hF h hq m q hs hsp hqo hd hlk hflat
        · -- a derived operand exists: it is a SECOND declared key, so the budget is ≥ 3
          push Not at hflat
          obtain ⟨r', hr', hdr⟩ := hflat
          have hdr' : isDerived S (q.object.type, r') = true := by simpa using hdr
          obtain ⟨e', hlk'⟩ := isDerived_declared hdr'
          have hk' : (q.object.type, r') ∈ S.keys := by
            by_contra hn; rw [lookup_eq_none S hn] at hlk'; simp at hlk'
          have hne : r' ≠ q.relation := by
            intro heq
            subst heq
            have he : e' = e := by rw [hlk] at hlk'; exact (Option.some.inj hlk').symm
            subst he
            have := hF.twoStrata _ _ e' hlk hd _ hr' hdr' e' hlk _ hr'
            rw [hd] at this
            exact Bool.noConfusion this
          have h2 : 2 ≤ S.keys.length := by
            have hsub : [(q.object.type, q.relation), (q.object.type, r')] ⊆ S.keys := by
              intro x hx
              simp only [List.mem_cons, List.not_mem_nil, or_false] at hx
              rcases hx with rfl | rfl
              · exact hk
              · exact hk'
            have hnd : [(q.object.type, q.relation), (q.object.type, r')].Nodup := by
              simp only [List.nodup_cons, List.mem_cons, List.not_mem_nil, or_false,
                not_false_eq_true, List.nodup_nil, and_true]
              intro heq
              exact hne (Prod.mk.inj heq).2.symm
            have := List.Subperm.length_le (List.subperm_of_subset hnd hsub)
            simpa using this
          obtain ⟨m, hm⟩ : ∃ m, S.keys.length = m + 2 := ⟨S.keys.length - 2, by omega⟩
          rw [hm]
          exact checkRAux_derived_top hA hF h hq m q hs hsp hqo hd

/-- **T2b-public over `semR`** -- the fenced reflexive read equals the spec, unguarded. -/
theorem graph_correct_publicR {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.checkPublicR σ q = semR S T q := by
  have hsch : σ.schema = S := reachedByW3d2E_schema h
  unfold GraphModel.checkPublicR
  split
  · rename_i hsome
    rw [hsch] at hsome
    exact (semAuxR_undeclared S q.subject T q
      (not_mem_keys_of_publicOfLeaf_isSome hA.wf hsome) _ _).symm
  · rename_i hnone
    rw [hsch] at hnone
    have hql : publicOfLeaf S q.object.type q.relation = none := by
      cases hpl : publicOfLeaf S q.object.type q.relation with
      | none => rfl
      | some v => rw [hpl] at hnone; exact absurd rfl hnone
    exact graph_correctR q hA hF h hq hqs hqo hql

/-- **T3 over `semR`** -- the reflexive set-engine model and the reflexive public graph read
    agree (through `semR`). -/
theorem backend_equivalenceR {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    SetEngineModel.checkR S T q = GraphModel.checkPublicR σ q := by
  rw [setEngine_correctR S T q, graph_correct_publicR q hA hF h hq hqs hqo]

/-- **T6a over `semR`** -- whenever the spec denies, both reflexive backends deny. -/
theorem exclusion_effectiveR {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR)
    (hDeny : semR S T q = false) :
    SetEngineModel.checkR S T q = false ∧ GraphModel.checkPublicR σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correctR S T q]; exact hDeny
  · rw [graph_correct_publicR q hA hF h hq hqs hqo]; exact hDeny

/-- **T6b over `semR`** -- no ghost grant survives the drain. -/
theorem no_ghost_grantR {S : Schema} {T' : Store} {σ' : GraphState} (q : Query)
    (hA : GraphAdmission S T') (hF : W4Fragment S T')
    (h : ReachedBy σ' S T') (hq : Drained S σ')
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR)
    (hDeny : semR S T' q = false) :
    GraphModel.checkPublicR σ' q = false := by
  rw [graph_correct_publicR q hA hF h hq hqs hqo]; exact hDeny

/-! ## The executable driver over `semR` (zcli graph mode) -/

/-- **The answer vector the CLI prints** (TK144): the reflexive PUBLIC read. Pinned, like
    `graphModeAnswers`, so re-pointing the driver changes golden text. -/
def graphModeAnswersR (σ : GraphState) (qs : List Query) : List Bool :=
  qs.map (fun q => GraphModel.checkPublicR σ q)

theorem graphRun_check_eq_semR {S : Schema} {ts : List Tuple} {σ : GraphState}
    {T : Store} (hrun : graphRun S ts = some (σ, T)) (hdr : drainedB S σ = true)
    (hA : GraphAdmission S T) (hF : W4Fragment S T) (q : Query)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.checkPublicR σ q = semR S T q :=
  graph_correct_publicR q hA hF (graphRun_reached hrun) ((drainedB_iff S σ).mp hdr) hqs hqo

theorem graphModeAnswersR_eq_semR {S : Schema} {ts : List Tuple} {σ : GraphState}
    {T : Store} {qs : List Query}
    (hrun : graphRun S ts = some (σ, T)) (hdr : drainedB S σ = true)
    (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (hqs : ∀ q ∈ qs, q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : ∀ q ∈ qs, q.object.name ≠ STAR) :
    graphModeAnswersR σ qs = qs.map (fun q => semR S T q) := by
  unfold graphModeAnswersR
  refine List.map_congr_left ?_
  intro q hq
  exact graphRun_check_eq_semR hrun hdr hA hF q (hqs q hq) (hqo q hq)

theorem graphRunOps_check_eq_semR {S : Schema} {ops : List GraphOp} {σ : GraphState}
    {T : Store} (hrun : graphRunOps S ops = some (σ, T)) (hdr : drainedB S σ = true)
    (hA : GraphAdmission S T) (hF : W4Fragment S T) (q : Query)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.checkPublicR σ q = semR S T q :=
  graph_correct_publicR q hA hF (graphRunOps_reached hrun) ((drainedB_iff S σ).mp hdr) hqs hqo

end Zanzibar
