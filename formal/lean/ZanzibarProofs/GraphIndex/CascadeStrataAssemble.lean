import ZanzibarProofs.GraphIndex.CascadeStrataEnum

/-!
# W3d-2 E-chain tail — the closure ASSEMBLY (ROADMAP W3d-2)

The last mile of the two-stratum enumerated chain: cursor-parameterized per-round
job lists (`enumJobs2R1`/`enumJobs2R2`), their validity/cover/scope/coverage
discharges, the fully-operational two-round scheduler closure `ReachedByW3d2E`,
and its projection onto the coverage chain (`reachedByW3d2E_toC`) — payoff
**`graph_correct_w3d2E`**, the two-stratum read theorem with NO chain-side
coverage hypotheses.

## The attack-shaped design (2026-07-12h, scratch deleted)

The ROADMAP's hoped-for discharge — "round-1 keys are stratum-1, so operand
settledness is vacuous" — is FALSE: a write to a DIRECT untainted leaf of a
stratum-2 def (`r2 := r1 \ b`, tuple at pred `b`) lands the stratum-2 key in
`cascadeKeysAbove` at the watermark, and when a leaf of its derived operand is
dirtied in the same window the state-derived enumeration at leg start is NOT
coverage-complete (`#eval`: `sem`-true subject with `cands.contains = false`).
Python survives because such a round-1 pass is provably stale-and-re-dirtied
(`round1_emission_dirties`) and round 2 re-enumerates against the settled operand.
Hence `ReachedByW3d2C` hypothesises coverage CONDITIONALLY (`W3dJobOpsSettled`),
and this file discharges exactly that conditional form from state — round 1 via
`w3dJobCoverage_enumJob2_state` at the leg start, round 2 via the routed leg
context at the MID state.
-/

namespace Zanzibar

open GraphModel

/-! ## Cascade-key facts at an arbitrary cursor -/

/-- Every cursor-round key names a declared derived key at a star-free object
    (the cursor only filters WHICH outbox rows are read — `mem_affectedKeys_props`
    is per-delta). -/
theorem mem_cascadeKeysAbove_props {S : Schema} {σ : GraphState} {n : Nat}
    {k : String × String × String} (hk : k ∈ cascadeKeysAbove S σ n) :
    isDerived S (k.1, k.2.1) = true ∧ (∃ e, S.lookup (k.1, k.2.1) = some e) ∧
      k.2.2 ≠ STAR := by
  unfold cascadeKeysAbove at hk
  obtain ⟨_, _, hkd⟩ := List.mem_flatMap.mp hk
  exact mem_affectedKeys_props hkd

/-! ## Star-free in-edge sources at derived R-nodes — W3d-2 chain + batch forms

Mirrors of `reachedByW3d_Rnode_source_name_ne_star` (`CascadeEnum.lean`) and
`reconcileJobsLR_source_bare` (`CascadeStrataSettle.lean`): cascade edges are
sourced at star-free candidates (`W3cJobValid`), write legs never land on a
derived R-node (model-level I5). -/

/-- Star-free in-edge sources at a FIXED derived R-node are batch-stable. -/
theorem reconcileJobsLR_source_name_ne_star {S : Schema} {T : Store}
    {jobs : List W3cJob} {σ : GraphState} {dt on R : String}
    (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (hbase : ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.name ≠ STAR) :
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T σ jobs).edges →
      x.name ≠ STAR := by
  intro x hx
  rcases reconcileJobsLR_edge_sound jobs σ x _ hx with hold | ⟨j, hj, c, hc, h1, _⟩
  · exact hbase x hold
  · obtain ⟨_, _, hcS, _⟩ := hjv j hj
    rw [h1, subjNode_plain (hcS c hc)]
    exact hcS c hc

/-- **Every in-edge source at a derived R-node is star-free** on a
    W3d-2 state (mirror of `reachedByW3d2_Rnode_source_bare`). -/
theorem reachedByW3d2_Rnode_source_name_ne_star {σ : GraphState} {S : Schema}
    {T : Store} {dt on R : String} {e : Expr}
    (h : ReachedByW3d2 σ S T) :
    S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e →
    StoreValidRules S T →
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.name ≠ STAR := by
  induction h with
  | empty S =>
    intro _ _ _ _ x hx
    simp [emptyState] at hx
  | @write σp S T t hadm hprev ih =>
    intro hlk hder hco hSV x hx
    rw [writeLeg_derived_inedges_eq hSV hlk hder hco x] at hx
    exact ih hlk hder hco (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) x hx
  | @remove σp S T t _ _ hSVT _ _ _ _ ih =>
    intro hlk hder hco _ x hx
    exact ih hlk hder hco hSVT x (mem_removeLoggedRules_edges hx)
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro hlk hder hco hSV x hx
    unfold runCascade2 at hx
    split at hx
    · have hx' : (x, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T
          (reconcileJobsLR S T σp jobs1) jobs2).edges := hx
      rcases reconcileJobsLR_edge_sound jobs2 _ x _ hx' with hmid | ⟨j, hj, c, hc, h1, _⟩
      · rcases reconcileJobsLR_edge_sound jobs1 σp x _ hmid
          with hold | ⟨j, hj, c, hc, h1, _⟩
        · exact ih hlk hder hco hSV x hold
        · obtain ⟨_, _, hcS, _⟩ := hjv1 j hj
          rw [h1, subjNode_plain (hcS c hc)]
          exact hcS c hc
      · obtain ⟨_, _, hcS, _⟩ := hjv2 j hj
        rw [h1, subjNode_plain (hcS c hc)]
        exact hcS c hc
    · exact ih hlk hder hco hSV x hx

/-! ## Residue members are star-free — the W3d-2 structural residue invariant

`enumJob2` folds residue-named subjects into the candidate lists, so `W3cJobValid`'s
star-freeness clauses need: every persisted `neg`/`upos` member is star-free. True
structurally — the only residue writer is the routed wholesale recompute, whose
`neg`/`upos` are filters of the job's `negCands`/`uposCands`, star-free by
`W3cJobValid` (`processor.py:441-446` filters the audit-enumerated candidates, and
enumeration sources — leaf reach, persisted residue ids, R-node edges — are
star-free by I6/write admission). -/

/-- Every persisted residue member is a star-free subject. -/
def ResidueSubjectsStarFree (σ : GraphState) : Prop :=
  ∀ k r res, σ.residue k r = some res →
    (∀ n ∈ res.neg, n.name ≠ STAR) ∧ (∀ u ∈ res.upos, u.name ≠ STAR)

theorem residueSubjectsStarFree_empty (S : Schema) :
    ResidueSubjectsStarFree (emptyState S) := by
  intro k r res hres
  simp [emptyState] at hres

/-- One routed logged pass preserves residue star-freeness (the written row's
    `neg`/`upos` are filters of the job's star-free candidate lists). -/
theorem residueSubjectsStarFree_applyLoggedR {S : Schema} {T : Store}
    {σ : GraphState} {j : W3cJob} (hjv : W3cJobValid S j)
    (h : ResidueSubjectsStarFree σ) :
    ResidueSubjectsStarFree (j.applyLoggedR S T σ) := by
  obtain ⟨_, _, _, hnegS, _, huS, _, _, _⟩ := hjv
  intro k r res hres
  unfold W3cJob.applyLoggedR at hres
  rw [pushDelta_residue] at hres
  unfold W3cJob.applyDR GraphState.reconcileStarsKeyDR at hres
  rw [reconcileKeyDR_residue] at hres
  by_cases hk : k = objNode ⟨j.dt, j.on⟩ j.R ∧ r = j.R
  · obtain ⟨hk1, hk2⟩ := hk
    subst hk1; subst hk2
    unfold GraphState.reconcileResidueKeyR at hres
    rw [putResidue_residue, if_pos ⟨rfl, rfl⟩] at hres
    obtain rfl := Option.some.inj hres
    constructor
    · intro n hn
      exact hnegS n (List.mem_filter.mp hn).1
    · intro u hu
      exact huS u (List.mem_filter.mp hu).1
  · rw [reconcileResidueKeyR_residue_other hk] at hres
    exact h k r res hres

/-- The routed logged batch preserves residue star-freeness. -/
theorem residueSubjectsStarFree_reconcileJobsLR {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState), (∀ j ∈ jobs, W3cJobValid S j) →
      ResidueSubjectsStarFree σ →
      ResidueSubjectsStarFree (reconcileJobsLR S T σ jobs) := by
  intro jobs
  induction jobs with
  | nil => intro σ _ h; exact h
  | cons j rest ih =>
    intro σ hjv h
    show ResidueSubjectsStarFree (reconcileJobsLR S T (j.applyLoggedR S T σ) rest)
    exact ih _ (fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj'))
      (residueSubjectsStarFree_applyLoggedR (hjv j List.mem_cons_self) h)

/-- **Every W3d-2 state's residue members are star-free.** -/
theorem reachedByW3d2_residueStarFree {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) : ResidueSubjectsStarFree σ := by
  induction h with
  | empty S => exact residueSubjectsStarFree_empty S
  | @write σp S T t hadm hprev ih =>
    intro k r res hres
    rw [writeLoggedRules_residue] at hres
    exact ih k r res hres
  | @remove σp S T t _ _ _ _ _ _ _ ih =>
    intro k r res hres
    rw [removeLoggedRules_residue_eq] at hres
    exact ih k r res hres
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    rcases runCascade2_cases S T σp jobs1 jobs2 with hrc | hrc
    · rw [hrc]
      intro k r res hres
      exact residueSubjectsStarFree_reconcileJobsLR jobs2 _ hjv2
        (residueSubjectsStarFree_reconcileJobsLR jobs1 σp hjv1 ih) k r res hres
    · rw [hrc]; exact ih

/-! ## `enumJob2` is `W3cJobValid` -/

/-- Every `enum2Base` member is star-free: leaf concretes by construction,
    residue-named members by `ResidueSubjectsStarFree`. -/
theorem enum2Base_name_ne_star {σ : GraphState} {dt on : String} {e : Expr}
    {c : SubjectRef} (hres : ResidueSubjectsStarFree σ)
    (h : c ∈ enum2Base σ dt on e) : c.name ≠ STAR := by
  rw [enum2Base, List.mem_append] at h
  rcases h with hl | hr
  · exact leafConcretes_name_ne_star hl
  · obtain ⟨r', _, hc⟩ := List.mem_flatMap.mp hr
    rw [residueNamed, List.mem_append] at hc
    cases hrow : σ.residue (objNode ⟨dt, on⟩ r') r' with
    | none =>
      rw [hrow] at hc
      rcases hc with hcn | hcu
      · exact absurd hcn List.not_mem_nil
      · exact absurd hcu List.not_mem_nil
    | some res =>
      rw [hrow] at hc
      rcases hc with hcn | hcu
      · exact (hres _ _ _ hrow).1 c hcn
      · exact (hres _ _ _ hrow).2 c hcu

/-- **`enumJob2` is a valid W3c job**, from explicit per-key edge-source facts
    (bare + star-free in-edge sources at the R-node) and residue star-freeness —
    stated state-generically so the projection can instantiate it both at a chain
    state and at the MID state (via the batch transports). -/
theorem w3cJobValid_enumJob2 {S : Schema} {σ : GraphState}
    (hWF : WF S) {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hon : on ≠ STAR)
    (hsb : ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE)
    (hsns : ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.name ≠ STAR)
    (hres : ResidueSubjectsStarFree σ) :
    W3cJobValid S (enumJob2 σ dt on R e) := by
  unfold W3cJobValid
  refine ⟨lookup_rel_ne_bare hWF hlk, ?_, ?_, ?_, ?_, ?_, hder, hlk, hon⟩
  · -- cands are bare
    intro c hc
    simp only [enumJob2, List.mem_append] at hc
    rcases hc with hcl | hcr
    · rw [List.mem_filter] at hcl; exact eq_of_beq hcl.2
    · rw [edgeHolders, List.mem_map] at hcr
      obtain ⟨ed, hed, hce⟩ := hcr
      rw [List.mem_filter] at hed
      obtain ⟨hedm, hedeq⟩ := hed
      have hb : ed.2 = objNode ⟨dt, on⟩ R := eq_of_beq hedeq
      have hmem : (ed.1, objNode ⟨dt, on⟩ R) ∈ σ.edges := by rw [← hb]; exact hedm
      rw [← hce]
      exact hsb ed.1 hmem
  · -- cands are star-free
    intro c hc
    simp only [enumJob2, List.mem_append] at hc
    rcases hc with hcl | hcr
    · exact enum2Base_name_ne_star hres (List.mem_filter.mp hcl).1
    · rw [edgeHolders, List.mem_map] at hcr
      obtain ⟨ed, hed, hce⟩ := hcr
      rw [List.mem_filter] at hed
      obtain ⟨hedm, hedeq⟩ := hed
      have hb : ed.2 = objNode ⟨dt, on⟩ R := eq_of_beq hedeq
      have hmem : (ed.1, objNode ⟨dt, on⟩ R) ∈ σ.edges := by rw [← hb]; exact hedm
      rw [← hce]
      exact hsns ed.1 hmem
  · -- negCands are star-free
    intro c hc
    simp only [enumJob2] at hc
    exact enum2Base_name_ne_star hres (List.mem_filter.mp hc).1
  · -- uposCands are non-bare
    intro c hc
    simp only [enumJob2] at hc
    have hb := (List.mem_filter.mp hc).2
    intro heq; rw [heq] at hb; simp at hb
  · -- uposCands are star-free
    intro c hc
    simp only [enumJob2] at hc
    exact enum2Base_name_ne_star hres (List.mem_filter.mp hc).1

/-! ## The per-round enumerated job lists -/

/-- The enumerated job list for a key set (jobs enumerated at `σe` — round 1 the
    leg start, round 2 the MID state). -/
def enumJobs2At (S : Schema) (σe : GraphState)
    (keys : List (String × String × String)) : List W3cJob :=
  keys.filterMap (fun k =>
    (S.lookup (k.1, k.2.1)).map (fun e => enumJob2 σe k.1 k.2.2 k.2.1 e))

/-- Every declared key has an enumerated job (coverage by construction). -/
theorem enumJobs2At_cover {S : Schema} {σe : GraphState}
    {keys : List (String × String × String)}
    (hk : ∀ k ∈ keys, ∃ e, S.lookup (k.1, k.2.1) = some e) :
    ∀ k ∈ keys, ∃ j ∈ enumJobs2At S σe keys, j.key = k := by
  intro k hkm
  obtain ⟨e, hlk⟩ := hk k hkm
  refine ⟨enumJob2 σe k.1 k.2.2 k.2.1 e, ?_, rfl⟩
  refine List.mem_filterMap.mpr ⟨k, hkm, ?_⟩
  rw [hlk]; rfl

/-- Every enumerated job's key is in the key set (scope by construction). -/
theorem enumJobs2At_scope {S : Schema} {σe : GraphState}
    {keys : List (String × String × String)} :
    ∀ j ∈ enumJobs2At S σe keys, j.key ∈ keys := by
  intro j hj
  rw [enumJobs2At, List.mem_filterMap] at hj
  obtain ⟨k, hk, hfk⟩ := hj
  obtain ⟨e, _, hje⟩ := Option.map_eq_some_iff.mp hfk
  rw [← hje]
  exact hk

/-- Every enumerated job is `W3cJobValid`, from per-key edge-source facts at the
    enumeration state. -/
theorem enumJobs2At_valid {S : Schema} {σe : GraphState}
    {keys : List (String × String × String)} (hWF : WF S)
    (hprops : ∀ k ∈ keys, isDerived S (k.1, k.2.1) = true ∧ k.2.2 ≠ STAR)
    (hedge : ∀ k ∈ keys,
      (∀ x, (x, objNode ⟨k.1, k.2.2⟩ k.2.1) ∈ σe.edges → x.pred = BARE) ∧
      (∀ x, (x, objNode ⟨k.1, k.2.2⟩ k.2.1) ∈ σe.edges → x.name ≠ STAR))
    (hres : ResidueSubjectsStarFree σe) :
    ∀ j ∈ enumJobs2At S σe keys, W3cJobValid S j := by
  intro j hj
  rw [enumJobs2At, List.mem_filterMap] at hj
  obtain ⟨k, hk, hfk⟩ := hj
  obtain ⟨e, hlk, hje⟩ := Option.map_eq_some_iff.mp hfk
  obtain ⟨hder, hon⟩ := hprops k hk
  obtain ⟨hsb, hsns⟩ := hedge k hk
  rw [← hje]
  exact w3cJobValid_enumJob2 hWF hlk hder hon hsb hsns hres

/-- The ROUND-1 enumerated jobs: the frontier keys above the stored watermark,
    enumerated at the leg-start state (`run_cascade` round 1,
    `processor.py:701-727`). -/
def enumJobs2R1 (S : Schema) (σ : GraphState) : List W3cJob :=
  enumJobs2At S σ (cascadeKeysAbove S σ σ.watermark)

/-- The ROUND-2 enumerated jobs: the keys of the rows round 1 emitted, enumerated
    at the MID state (round 2 reads the graph as round 1 left it). -/
def enumJobs2R2 (S : Schema) (T : Store) (σ : GraphState) : List W3cJob :=
  enumJobs2At S (reconcileJobsLR S T σ (enumJobs2R1 S σ))
    (cascadeKeysAbove S (reconcileJobsLR S T σ (enumJobs2R1 S σ))
      (σ.frontierMax σ.watermark))

/-! ## The fully-operational two-round scheduler closure -/

/-- **`ReachedByW3d2E`** — the two-stratum interleaved scheduler closure with
    FULLY-OPERATIONAL cascade legs: each cascade runs the canonical per-round
    `enumJobs2R1`/`enumJobs2R2` lists read off the state. No `W3cJobValid` /
    cover / scope / coverage hypotheses — they are theorems of the enumeration. -/
inductive ReachedByW3d2E : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByW3d2E (emptyState S) S []
  | write {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hadm : FoldAdmits σ (rewriteClosure S t))
      (hprev : ReachedByW3d2E σ S T) :
      ReachedByW3d2E (σ.writeLoggedRules S t) S (t :: T)
  | remove {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hadm : RemoveAdmits σ T t) (hdrain : cascadeKeys S σ = [])
      (hSVT : StoreValidRules S T) (hBST : BareStarStore T) (hTST : TtuStarFree S T)
      (htermT : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
      (hprev : ReachedByW3d2E σ S T) :
      ReachedByW3d2E (σ.removeLoggedRules S t) S (T.erase t)
  -- hSVT/hBST/hTST/htermT: the pre-remove store T was validly built. FAITHFUL — Python's
  -- TupleSource.remove (connectedstore/source.py) only retracts admission-validated tuples
  -- (validate_write_identifiers + matching Direct arm = StoreValidRules); the star/ttu/term
  -- conditions are the W4Fragment carries graph_correct already assumes about the store.
  -- hdrain: Python drains the view between applied log rows (cascadeKeys non-monotone under
  -- retraction, so remove-from-undrained is unfaithful and would break reachedByW3d2C_settled).
  | cascade {σ : GraphState} {S : Schema} {T : Store}
      (hprev : ReachedByW3d2E σ S T) :
      ReachedByW3d2E (runCascade2 S T σ (enumJobs2R1 S σ) (enumJobs2R2 S T σ)) S T

/-- **The projection `ReachedByW3d2E ⇒ ReachedByW3d2C`.** Per cascade leg:
    validity/cover/scope structurally; round-1 CONDITIONAL coverage via
    `w3dJobCoverage_enumJob2_state` at the leg start (the `W3dJobOpsSettled`
    baseline is exactly its `hsettledOps`); round-2 conditional coverage via the
    routed leg context at the MID state (shadow, closedness, edge discipline, and
    the reach collapse all transported through the round-1 batch). Store
    hypotheses weaken along write prefixes. -/
theorem reachedByW3d2E_toC {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T) :
    WF S → TtuTuplesetsDirect S → NodupKeys S → RewriteRanked S →
    RewriteMatchDeclared S → Stratifiable S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e) →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false) →
    (∀ sh ∈ wildcardShapes S, sh.2 = BARE) →
    StoreValidRules S T → BareStarStore T → TtuStarFree S T →
    (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) →
    ReachedByW3d2C σ S T := by
  induction h with
  | empty S =>
    intro _ _ _ _ _ _ _ _ _ _ _ _ _
    exact ReachedByW3d2C.empty S
  | @write σp S T t hadm hprev ih =>
    intro hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare hSV hBS hTS hterm
    have hSVw : StoreValidRules S T := fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')
    have hBSw : BareStarStore T := fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')
    have hTSw : TtuStarFree S T := fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht')
    have htermw : ∀ dt R, isDerived S (dt, R) = true →
        NoTtuTarget S R ∧ NoStoreSubjectR T R :=
      fun dt R hd => ⟨(hterm dt R hd).1,
        fun t' ht' => (hterm dt R hd).2 t' (List.mem_cons_of_mem _ ht')⟩
    exact ReachedByW3d2C.write t hadm
      (ih hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare hSVw hBSw hTSw htermw)
  | @remove σp S T t hadm hdrain hSVT hBST hTST htermT hprev ih =>
    intro hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare _hSV _hBS _hTS _hterm
    exact ReachedByW3d2C.remove t hadm hdrain hSVT hBST hTST htermT
      (ih hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare hSVT hBST hTST htermT)
  | @cascade σp S T hprev ih =>
    intro hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare hSV hBS hTS hterm
    have hC : ReachedByW3d2C σp S T :=
      ih hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare hSV hBS hTS hterm
    have hW3d2 : ReachedByW3d2 σp S T := reachedByW3d2C_toW3d2 hC
    have hres_p : ResidueSubjectsStarFree σp := reachedByW3d2_residueStarFree hW3d2
    -- round-1 validity: per-key edge facts at the leg start
    have hjv1 : ∀ j ∈ enumJobs2R1 S σp, W3cJobValid S j := by
      refine enumJobs2At_valid hWF ?_ ?_ hres_p
      · intro k hk
        obtain ⟨hd, _, hon⟩ := mem_cascadeKeysAbove_props hk
        exact ⟨hd, hon⟩
      · intro k hk
        obtain ⟨hd, ⟨e', hlk'⟩, _⟩ := mem_cascadeKeysAbove_props hk
        have hco' : ComputedOnly e' := hCO k.1 k.2.1 e' hlk' hd
        exact ⟨reachedByW3d2_Rnode_source_bare hW3d2 hlk' hd hco' hSV,
          reachedByW3d2_Rnode_source_name_ne_star hW3d2 hlk' hd hco' hSV⟩
    -- MID-state facts, transported through the round-1 batch
    have hσS : σp.schema = S := reachedByW3d2_schema hW3d2
    have hσmidS : (reconcileJobsLR S T σp (enumJobs2R1 S σp)).schema = S := by
      rw [reconcileJobsLR_schema]; exact hσS
    have hres_mid : ResidueSubjectsStarFree (reconcileJobsLR S T σp (enumJobs2R1 S σp)) :=
      residueSubjectsStarFree_reconcileJobsLR _ σp hjv1 hres_p
    have hclmid : ∀ ab ∈ (reconcileJobsLR S T σp (enumJobs2R1 S σp)).edges,
        ab.1 ∈ (reconcileJobsLR S T σp (enumJobs2R1 S σp)).nodes ∧
        ab.2 ∈ (reconcileJobsLR S T σp (enumJobs2R1 S σp)).nodes :=
      edgesClosed_reconcileJobsLR _ σp (reachedByW3d2_edgesClosed hW3d2)
    have htb : ∀ a b, (a, b) ∈ σp.edges → b.pred ≠ BARE :=
      reachedByW3d2_edge_target_ne_bare hW3d2 hWF hSV
    obtain ⟨σ0, h0, hsh⟩ := reachedByW3d2_shadow hW3d2 hNK hCO hSV hterm
    have hshmid : UntaintedShadow S (reconcileJobsLR S T σp (enumJobs2R1 S σp)) σ0 :=
      untaintedShadow_reconcileJobsLR _ σp σ0 hsh (reachedByRules_of_admitted h0)
        hSV hNK hCO hjv1
    -- round-2 validity: per-key edge facts transported to MID
    have hjv2 : ∀ j ∈ enumJobs2R2 S T σp, W3cJobValid S j := by
      refine enumJobs2At_valid hWF ?_ ?_ hres_mid
      · intro k hk
        obtain ⟨hd, _, hon⟩ := mem_cascadeKeysAbove_props hk
        exact ⟨hd, hon⟩
      · intro k hk
        obtain ⟨hd, ⟨e', hlk'⟩, _⟩ := mem_cascadeKeysAbove_props hk
        have hco' : ComputedOnly e' := hCO k.1 k.2.1 e' hlk' hd
        exact ⟨reconcileJobsLR_source_bare hjv1
            (reachedByW3d2_Rnode_source_bare hW3d2 hlk' hd hco' hSV),
          reconcileJobsLR_source_name_ne_star hjv1
            (reachedByW3d2_Rnode_source_name_ne_star hW3d2 hlk' hd hco' hSV)⟩
    -- round-1 CONDITIONAL coverage: `w3dJobCoverage_enumJob2_state` at the leg start
    have hcovg1 : ∀ j ∈ enumJobs2R1 S σp, W3dJobOpsSettled S T σp j →
        W3dJobCoverage S T σp j := by
      intro j hj hops
      rw [enumJobs2R1, enumJobs2At, List.mem_filterMap] at hj
      obtain ⟨k, hk, hfk⟩ := hj
      obtain ⟨e, hlk, hje⟩ := Option.map_eq_some_iff.mp hfk
      obtain ⟨hder, _, hon⟩ := mem_cascadeKeysAbove_props hk
      rw [← hje] at hops ⊢
      exact w3dJobCoverage_enumJob2_state hWF hTT hNK hR hSV hBS hTS hMatch
        hStrat hterm hCO hWSbare hW3d2 hlk hder (hCO _ _ _ hlk hder) hon
        (hLU2 _ _ _ hlk hder) (fun r' hr' hd' => hops r' hr' hd')
    -- round-2 CONDITIONAL coverage: the routed leg context at the MID state
    have hcovg2 : ∀ j ∈ enumJobs2R2 S T σp,
        W3dJobOpsSettled S T (reconcileJobsLR S T σp (enumJobs2R1 S σp)) j →
        W3dJobCoverage S T (reconcileJobsLR S T σp (enumJobs2R1 S σp)) j := by
      intro j hj hops
      rw [enumJobs2R2, enumJobs2At, List.mem_filterMap] at hj
      obtain ⟨k, hk, hfk⟩ := hj
      obtain ⟨e, hlk, hje⟩ := Option.map_eq_some_iff.mp hfk
      obtain ⟨hder, _, hon⟩ := mem_cascadeKeysAbove_props hk
      rw [← hje] at hops ⊢
      have hco := hCO _ _ _ hlk hder
      have hLU2e := hLU2 _ _ _ hlk hder
      -- the operand baseline with the reach collapse at MID
      have hopsC : ∀ r' ∈ computedRefs e, isDerived S (k.1, r') = true →
          SettledKey S T (reconcileJobsLR S T σp (enumJobs2R1 S σp)) k.1 k.2.2 r' ∧
          CompleteKey S T (reconcileJobsLR S T σp (enumJobs2R1 S σp)) k.1 k.2.2 r' ∧
          (∀ u, NReaches (reconcileJobsLR S T σp (enumJobs2R1 S σp)).edges u
              (objNode ⟨k.1, k.2.2⟩ r') →
            (u, objNode ⟨k.1, k.2.2⟩ r')
              ∈ (reconcileJobsLR S T σp (enumJobs2R1 S σp)).edges) := by
        intro r' hr' hd'
        obtain ⟨hset, hcomp⟩ := hops r' hr' hd'
        obtain ⟨e', hlk'⟩ := isDerived_declared hd'
        have hco' : ComputedOnly e' := hCO k.1 r' e' hlk' hd'
        refine ⟨hset, hcomp, ?_⟩
        intro u hu
        exact reconcileJobsLR_reach_collapse hjv1 htb
          (reachedByW3d2_Rnode_source_bare hW3d2 hlk' hd' hco' hSV) hu
      obtain ⟨hbridge, hcovDecl⟩ := w3d2_leg_context hWF hTT hNK hR hSV hBS hTS
        hMatch hStrat hterm hCO hWSbare h0 hshmid hσmidS hlk hder hco hon hLU2e hopsC
      exact w3dJobCoverage_enumJob2 hco hclmid hon hbridge hcovDecl hWSbare
    exact ReachedByW3d2C.cascade (enumJobs2R1 S σp) (enumJobs2R2 S T σp)
      hjv1 hjv2
      (enumJobs2At_cover (fun k hk => (mem_cascadeKeysAbove_props hk).2.1))
      enumJobs2At_scope
      (enumJobs2At_cover (fun k hk => (mem_cascadeKeysAbove_props hk).2.1))
      enumJobs2At_scope
      hcovg1 hcovg2
      hC

/-- **T2b, W3d-2 fragment, UNCONDITIONAL (`graph_correct_w3d2E`) — `check = sem`
    at every fully-drained state of the FULLY-OPERATIONAL two-round scheduler
    chain.** Identical to `graph_correct_w3d2` but over `ReachedByW3d2E`, whose
    cascade legs carry NO validity/cover/scope/coverage hypotheses — all are
    discharged from state (with the attack-mandated conditional round-1 coverage
    discharged via the operand baseline). -/
theorem graph_correct_w3d2E {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2E σ S T) (hq : cascadeKeys S σ = [])
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem S T q :=
  graph_correct_w3d2 q hWF hTT hNK hR hSV hBS hTS hMatch hStrat hterm hCO hLU2
    hWSbare
    (reachedByW3d2E_toC h hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare hSV hBS
      hTS hterm)
    hq hqs hqo

end Zanzibar
