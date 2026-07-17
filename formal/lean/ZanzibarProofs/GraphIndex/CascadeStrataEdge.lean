import ZanzibarProofs.GraphIndex.CascadeStrataInv

/-!
# W4 T2a assembly — edge hygiene over the OPERATIONAL two-round chain

`CascadeStrataInv.lean` proved the three fragment-free `Inv` layers (`StructInv`,
edge-free I6, row declaredness) over `ReachedByW3d2E`, plus the pass-local I6 core
(`reconcileStarsKeyDR_row_edge_consistent`: the row a routed pass writes is
edge-consistent with its own audit, settled or STALE). This file assembles that
core into the two EDGE-referencing I6 clauses (`negEdgeFree`/`uposEdgeFree`) over
the operational closure, then the full 8-clause `Inv` (`reachedByW3d2E_inv`).

**Design (HANDOFF "The next task", the W3d-1 route deliberately NOT reused).**
`reachedByW3dC_edgeHygienic` (W3d-1) went through the coverage chain's SETTLED
verdicts. W3d-2 coverage is CONDITIONAL (12h): at a re-dirtied round-1 stratum-2
key there is no `SettledKey`. So we work at the EDGE-DIRECT level with an
invariant that never consumes settledness:

* `EdgeHyg1 σ` — no `neg`/`upos` member holds a direct in-edge at its key.
* Batch preservation (`edgeHyg1_reconcileJobsLR`) by induction carrying the
  prefix-state context: at a job's own key the pass-local core re-establishes
  consistency FRESH (whatever the guard said); at every other key
  `applyLoggedR_other_key_fixed` transports the prior state's hygiene. The
  candidate-discipline premise `negCands ⊆ cands` is the E-chain's
  `enumJob2_negCands_subset` — the reason this is provable at the 12h attack
  shape where the W3d-1 coverage route cannot go.
* `runCascade2` (two batches + watermark, reject = id) and the chain: write legs
  are residue-inert with derived in-edges fixed (`writeLeg_derived_inedges_eq`).
* `reachedByW3d2E_edgeHygienic` lifts the edge-direct form to the `Inv` clauses'
  `¬NReaches` form via the reach collapse (`reachedByW3d2_reach_collapse_root`).
-/

namespace Zanzibar

/-! ## The edge-direct hygiene predicate and the all-key R-node invariants -/

/-- **The edge-DIRECT form of the two edge-referencing I6 clauses.** No `neg`/`upos`
    member holds a direct in-edge at its key. Over a derived key the
    reach collapse turns this into the `Inv` clauses' `¬NReaches` form. -/
def EdgeHyg1 (σ : GraphState) : Prop :=
  ∀ k r res, σ.residue k r = some res →
    (∀ n ∈ res.neg, (subjNode n, k) ∉ σ.edges) ∧
    (∀ n ∈ res.upos, (subjNode n, k) ∉ σ.edges)

/-- The empty state has no residue rows. -/
theorem edgeHyg1_empty (S : Schema) : EdgeHyg1 (emptyState S) := by
  intro k r res hrow; simp [emptyState] at hrow

/-- R-node terminality across ALL non-bare derived keys — the pass-local core's
    `hRns` at every job key, carried through a batch prefix. -/
def RnodeTerminalAll (S : Schema) (σ : GraphState) : Prop :=
  ∀ dt on R, isDerived S (dt, R) = true → R ≠ BARE →
    ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges

/-- In-edge source bareness across ALL non-bare derived keys — the pass-local
    core's `hsb`, carried through a batch prefix. -/
def RnodeSourceBareAll (S : Schema) (σ : GraphState) : Prop :=
  ∀ dt on R, isDerived S (dt, R) = true → R ≠ BARE →
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE

/-- One routed logged pass preserves all-key R-node terminality (new edges are
    sourced at bare candidates — never an R-node — and removals only shrink). -/
theorem rnodeTerminalAll_applyLoggedR {S : Schema} {T : Store} {σ : GraphState}
    {j : W3cJob} (hjv : W3cJobValid S j) (h : RnodeTerminalAll S σ) :
    RnodeTerminalAll S (j.applyLoggedR S T σ) := by
  intro dt on R hder hRne y hy
  exact reconcileJobsLR_Rnode_not_source (T := T) (jobs := [j]) hRne
    (by intro j' hj'; rcases List.mem_singleton.mp hj' with rfl; exact hjv)
    (h dt on R hder hRne) y hy

/-- One routed logged pass preserves all-key in-edge source bareness. -/
theorem rnodeSourceBareAll_applyLoggedR {S : Schema} {T : Store} {σ : GraphState}
    {j : W3cJob} (hjv : W3cJobValid S j) (h : RnodeSourceBareAll S σ) :
    RnodeSourceBareAll S (j.applyLoggedR S T σ) := by
  intro dt on R hder hRne x hx
  exact reconcileJobsLR_source_bare (T := T) (jobs := [j])
    (by intro j' hj'; rcases List.mem_singleton.mp hj' with rfl; exact hjv)
    (h dt on R hder hRne) x hx

/-! ## Single-pass edge-direct hygiene preservation -/

/-- **One routed logged pass preserves `EdgeHyg1`.** At the pass's OWN key the
    pass-local core establishes consistency fresh; at every other key the residue
    row and in-edges are verbatim (`applyLoggedR_other_key_fixed`), so the prior
    state's hygiene transports. No settledness is consumed. -/
theorem edgeHyg1_applyLoggedR {S : Schema} {T : Store} {σ : GraphState} {j : W3cJob}
    (hσS : σ.schema = S) (hStruct : StructInv S σ) (hRD : ResidueDeclared S σ)
    (hRns : RnodeTerminalAll S σ) (hsb : RnodeSourceBareAll S σ)
    (hjv : W3cJobValid S j) (hnc : ∀ c ∈ j.negCands, c ∈ j.cands)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hEH : EdgeHyg1 σ) :
    EdgeHyg1 (j.applyLoggedR S T σ) := by
  have hRne := hjv.1
  have hcb := hjv.2.1
  have hup := hjv.2.2.2.2.1
  have hder := hjv.2.2.2.2.2.2.1
  have hlk := hjv.2.2.2.2.2.2.2.1
  have hon := hjv.2.2.2.2.2.2.2.2
  have hco := hCO _ _ _ hlk hder
  have hrne := computedRefs_ne_self hlk hder (hLU2 _ _ _ hlk hder)
  have hres_eq : (j.applyLoggedR S T σ).residue = (j.applyDR S T σ).residue := by
    unfold W3cJob.applyLoggedR; rw [pushDelta_residue]
  have hedge_eq : (j.applyLoggedR S T σ).edges = (j.applyDR S T σ).edges := by
    unfold W3cJob.applyLoggedR; rw [pushDelta_edges]
  intro k r res hrow
  by_cases hkey : k = objNode ⟨j.dt, j.on⟩ j.R ∧ r = j.R
  · obtain ⟨hk, hr⟩ := hkey
    subst hk hr
    rw [hres_eq] at hrow
    have hpl := reconcileStarsKeyDR_row_edge_consistent (S := S) T j.dt j.on j.R j.e
      (wildcardShapes S) j.cands j.negCands j.uposCands hσS hRne hon hder hco hrne hcb
      hnc hup (hsb j.dt j.on j.R hder hRne) (hRns j.dt j.on j.R hder hRne)
      hStruct.edgesClosed res hrow
    rw [hedge_eq]
    exact hpl
  · have hres_other : (j.applyLoggedR S T σ).residue k r = σ.residue k r := by
      rw [hres_eq]
      exact reconcileStarsKeyDR_residue_other hkey
    rw [hres_other] at hrow
    obtain ⟨dt', on', R', e', hk', hr', hlk', hder', hon'⟩ := hRD k r res hrow
    subst hk' hr'
    have hnot : ¬ j.keyMatch dt' on' r := by
      intro hkm
      refine hkey ⟨?_, hkm.2.2.symm⟩
      rw [← hkm.1, ← hkm.2.1, ← hkm.2.2]
    obtain ⟨_, hedge_iff⟩ := applyLoggedR_other_key_fixed hjv hon' hnot
    exact ⟨fun n hn hedge => (hEH _ _ _ hrow).1 n hn ((hedge_iff (subjNode n)).mp hedge),
           fun n hn hedge => (hEH _ _ _ hrow).2 n hn ((hedge_iff (subjNode n)).mp hedge)⟩

/-! ## Batch and cascade preservation -/

/-- **A routed logged batch of enumerated jobs preserves `EdgeHyg1`.** Induction
    carrying the prefix-state context (`StructInv`/`ResidueDeclared`/the two all-key
    R-node invariants/schema), each re-established by the single-pass lemmas. -/
theorem edgeHyg1_reconcileJobsLR {S : Schema} {T : Store}
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false) :
    ∀ (jobs : List W3cJob) {σ : GraphState},
      σ.schema = S → StructInv S σ → ResidueDeclared S σ →
      RnodeTerminalAll S σ → RnodeSourceBareAll S σ →
      (∀ j ∈ jobs, W3cJobValid S j) →
      (∀ j ∈ jobs, ∀ c ∈ j.negCands, c ∈ j.cands) →
      EdgeHyg1 σ →
      EdgeHyg1 (reconcileJobsLR S T σ jobs) := by
  intro jobs
  induction jobs with
  | nil => intro σ _ _ _ _ _ _ _ hEH; exact hEH
  | cons j rest ih =>
    intro σ hσS hStruct hRD hRns hsb hjv hnc hEH
    have hfold : reconcileJobsLR S T σ (j :: rest)
        = reconcileJobsLR S T (j.applyLoggedR S T σ) rest := by
      unfold reconcileJobsLR; rw [List.foldl_cons]
    rw [hfold]
    have hjvj := hjv j List.mem_cons_self
    refine ih (σ := j.applyLoggedR S T σ) ?_ ?_ ?_ ?_ ?_ ?_ ?_ ?_
    · rw [W3cJob.applyLoggedR_schema, hσS]
    · exact structInv_applyLoggedR hStruct T j
    · exact residueDeclared_applyLoggedR T (w3cJobKeyFacts_of_valid hjvj) hRD
    · exact rnodeTerminalAll_applyLoggedR hjvj hRns
    · exact rnodeSourceBareAll_applyLoggedR hjvj hsb
    · exact fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj')
    · exact fun j' hj' => hnc j' (List.mem_cons_of_mem _ hj')
    · exact edgeHyg1_applyLoggedR hσS hStruct hRD hRns hsb hjvj
        (hnc j List.mem_cons_self) hCO hLU2 hEH

/-- **A whole two-round cascade run preserves `EdgeHyg1`.** Accept branch = two
    enumerated batches with the intermediate context transported, then a watermark
    bump (residue/edge-inert); reject branch = identity. -/
theorem edgeHyg1_runCascade2 {S : Schema} {T : Store} {σ : GraphState}
    {jobs1 jobs2 : List W3cJob}
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hσS : σ.schema = S) (hStruct : StructInv S σ) (hRD : ResidueDeclared S σ)
    (hRns : RnodeTerminalAll S σ) (hsb : RnodeSourceBareAll S σ)
    (hjv1 : ∀ j ∈ jobs1, W3cJobValid S j) (hjv2 : ∀ j ∈ jobs2, W3cJobValid S j)
    (hnc1 : ∀ j ∈ jobs1, ∀ c ∈ j.negCands, c ∈ j.cands)
    (hnc2 : ∀ j ∈ jobs2, ∀ c ∈ j.negCands, c ∈ j.cands)
    (hEH : EdgeHyg1 σ) :
    EdgeHyg1 (runCascade2 S T σ jobs1 jobs2) := by
  rcases runCascade2_cases S T σ jobs1 jobs2 with hrc | hrc
  · rw [hrc]
    have hbatch1 : EdgeHyg1 (reconcileJobsLR S T σ jobs1) :=
      edgeHyg1_reconcileJobsLR hCO hLU2 jobs1 hσS hStruct hRD hRns hsb hjv1 hnc1 hEH
    have hσSmid : (reconcileJobsLR S T σ jobs1).schema = S := by
      rw [reconcileJobsLR_schema]; exact hσS
    have hStrmid := structInv_reconcileJobsLR T jobs1 hStruct
    have hRDmid := residueDeclared_reconcileJobsLR T jobs1
      (fun j hj => w3cJobKeyFacts_of_valid (hjv1 j hj)) hRD
    have hRnsmid : RnodeTerminalAll S (reconcileJobsLR S T σ jobs1) := by
      intro dt on R hder hRne y hy
      exact reconcileJobsLR_Rnode_not_source hRne hjv1 (hRns dt on R hder hRne) y hy
    have hsbmid : RnodeSourceBareAll S (reconcileJobsLR S T σ jobs1) := by
      intro dt on R hder hRne x hx
      exact reconcileJobsLR_source_bare hjv1 (hsb dt on R hder hRne) x hx
    have hbatch2 : EdgeHyg1 (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2) :=
      edgeHyg1_reconcileJobsLR hCO hLU2 jobs2 hσSmid hStrmid hRDmid hRnsmid hsbmid
        hjv2 hnc2 hbatch1
    intro k r res hrow
    exact hbatch2 k r res hrow
  · rw [hrc]; exact hEH

/-! ## The enumerated jobs audit their own residue candidates -/

/-- Every enumerated job satisfies the candidate-discipline premise
    (`negCands ⊆ cands`) — the E-chain discharge of the pass-local `hnc`. -/
theorem enumJobs2At_negCands_subset {S : Schema} {σe : GraphState}
    {keys : List (String × String × String)} :
    ∀ j ∈ enumJobs2At S σe keys, ∀ c ∈ j.negCands, c ∈ j.cands := by
  intro j hj
  rw [enumJobs2At, List.mem_filterMap] at hj
  obtain ⟨k, _, hfk⟩ := hj
  obtain ⟨e, _, hje⟩ := Option.map_eq_some_iff.mp hfk
  rw [← hje]
  exact enumJob2_negCands_subset σe k.1 k.2.2 k.2.1 e

/-! ## `EdgeHyg1` over the operational chain -/

/-- **The edge-direct hygiene holds at every operational (`ReachedByW3d2E`) state.**
    Empty vacuous; write legs transport it (`writeLoggedRules_residue` +
    `writeLeg_derived_inedges_eq` at the declared derived key); cascade
    legs re-establish it via `edgeHyg1_runCascade2`, whose per-round enumerated jobs
    are valid and candidate-audited from state. Fragment threaded as in
    `reachedByW3d2E_toC`. -/
theorem reachedByW3d2E_edgeHyg1 {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T) :
    WF S → TtuTuplesetsDirect S → NodupKeys S → RewriteRanked S →
    RewriteMatchDeclared S → Stratifiable S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false) →
    (∀ sh ∈ wildcardShapes S, sh.2 = BARE) →
    StoreValidRules S T → BareStarStore T → TtuStarFree S T →
    (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) →
    EdgeHyg1 σ := by
  induction h with
  | empty S =>
    intro _ _ _ _ _ _ _ _ _ _ _ _ _
    exact edgeHyg1_empty S
  | @write σp S T t hadm hprev ih =>
    intro hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare hSV hBS hTS hterm
    have hSVw : StoreValidRules S T := fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')
    have hBSw : BareStarStore T := fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')
    have hTSw : TtuStarFree S T := fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht')
    have htermw : ∀ dt R, isDerived S (dt, R) = true →
        NoTtuTarget S R ∧ NoStoreSubjectR T R :=
      fun dt R hd => ⟨(hterm dt R hd).1,
        fun t' ht' => (hterm dt R hd).2 t' (List.mem_cons_of_mem _ ht')⟩
    have hEHp : EdgeHyg1 σp :=
      ih hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare hSVw hBSw hTSw htermw
    intro k r res hrow
    rw [writeLoggedRules_residue] at hrow
    obtain ⟨dt, on, R, e, hk, hr, hlk, hder, hon⟩ :=
      reachedByW3d2E_residueDeclared hprev k r res hrow
    subst hk
    have hco : ComputedOnly e := hCO dt R e hlk hder
    refine ⟨fun n hn hedge => ?_, fun n hn hedge => ?_⟩
    · rw [writeLeg_derived_inedges_eq hSV hlk hder hco (subjNode n)] at hedge
      exact (hEHp _ _ _ hrow).1 n hn hedge
    · rw [writeLeg_derived_inedges_eq hSV hlk hder hco (subjNode n)] at hedge
      exact (hEHp _ _ _ hrow).2 n hn hedge
  | @cascade σp S T hprev ih =>
    intro hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare hSV hBS hTS hterm
    have hEHp : EdgeHyg1 σp :=
      ih hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare hSV hBS hTS hterm
    have hW3d2 : ReachedByW3d2 σp S T :=
      reachedByW3d2C_toW3d2 (reachedByW3d2E_toC hprev hWF hTT hNK hR hMatch
        hStrat hCO hLU2 hWSbare hSV hBS hTS hterm)
    -- σp facts
    have hσS : σp.schema = S := reachedByW3d2_schema hW3d2
    have hStruct : StructInv S σp := reachedByW3d2E_structInv hprev
    have hRD : ResidueDeclared S σp := reachedByW3d2E_residueDeclared hprev
    have hRns : RnodeTerminalAll S σp := by
      intro dt on R hder hRne y hy
      exact reachedByW3d2_Rnode_not_source hterm hRne hder hW3d2 y hy
    have hsb : RnodeSourceBareAll S σp := by
      intro dt on R hder hRne x hx
      obtain ⟨e', hlk'⟩ := isDerived_declared hder
      have hco' : ComputedOnly e' := hCO dt R e' hlk' hder
      exact reachedByW3d2_Rnode_source_bare hW3d2 hlk' hder hco' hSV x hx
    have hres_p : ResidueSubjectsStarFree σp := reachedByW3d2_residueStarFree hW3d2
    -- round-1 validity (copy of `reachedByW3d2E_toC`)
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
    -- MID-state facts transported through round 1
    have hres_mid : ResidueSubjectsStarFree (reconcileJobsLR S T σp (enumJobs2R1 S σp)) :=
      residueSubjectsStarFree_reconcileJobsLR _ σp hjv1 hres_p
    -- round-2 validity
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
    exact edgeHyg1_runCascade2 hCO hLU2 hσS hStruct hRD hRns hsb hjv1 hjv2
      (enumJobs2At_negCands_subset) (enumJobs2At_negCands_subset) hEHp

/-! ## From edge-direct hygiene to the `Inv` clauses -/

/-- **The edge-referencing I6 clauses over the operational chain.** The reach
    collapse at a derived R-node turns `EdgeHyg1`'s direct-edge form
    into the `Inv` clauses' `¬NReaches` form. -/
theorem reachedByW3d2E_edgeHygienic {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR T R) :
    EdgeHygienic σ := by
  have hW3d2 : ReachedByW3d2 σ S T :=
    reachedByW3d2C_toW3d2 (reachedByW3d2E_toC h hWF hTT hNK hR hMatch hStrat
      hCO hLU2 hWSbare hSV hBS hTS hterm)
  have hEH : EdgeHyg1 σ :=
    reachedByW3d2E_edgeHyg1 h hWF hTT hNK hR hMatch hStrat hCO hLU2 hWSbare
      hSV hBS hTS hterm
  have hRD : ResidueDeclared S σ := reachedByW3d2E_residueDeclared h
  intro k r res hrow
  obtain ⟨dt, on, R, e, hk, hr, hlk, hder, hon⟩ := hRD k r res hrow
  subst hk
  rw [hr] at hrow
  have hco : ComputedOnly e := hCO dt R e hlk hder
  refine ⟨fun n hn hre => ?_, fun n hn hre => ?_⟩
  · exact (hEH _ _ _ hrow).1 n hn
      (reachedByW3d2_reach_collapse_root hWF hSV hlk hder hco hW3d2 hre)
  · exact (hEH _ _ _ hrow).2 n hn
      (reachedByW3d2_reach_collapse_root hWF hSV hlk hder hco hW3d2 hre)

/-! ## The full W4 T2a invariant -/

/-- **T2a, W4 scope (`reachedByW3d2E_inv`) — the full 8-clause `Inv` at every state
    of the operational two-round chain**, dirty keys and mid-drain states included.
    The structural half (`reachedByW3d2E_structInv`) and the edge-free I6 clauses
    (`reachedByW3d2E_residueHygienic`) need no fragment hypotheses; the two
    edge-referencing I6 clauses carry the W4 fragment via
    `reachedByW3d2E_edgeHygienic`. -/
theorem reachedByW3d2E_inv {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR T R) :
    Inv S σ := by
  have hst := reachedByW3d2E_structInv h
  have hhy := reachedByW3d2E_residueHygienic h
  have heh := reachedByW3d2E_edgeHygienic h hWF hTT hNK hR hMatch hStrat hCO
    hLU2 hWSbare hSV hBS hTS hterm
  exact
    { schemaEq := hst.schemaEq
      nodeEnc := hst.nodeEnc
      edgesClosed := hst.edgesClosed
      acyclic := hst.acyclic
      negStarCovered := hhy.1
      negEdgeFree := fun k r res hrow n hn => (heh k r res hrow).1 n hn
      uposEdgeFree := fun k r res hrow n hn => (heh k r res hrow).2 n hn
      uposNegDisjoint := hhy.2 }

end Zanzibar
