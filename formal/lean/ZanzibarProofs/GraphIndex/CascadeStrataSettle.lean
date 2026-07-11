import ZanzibarProofs.GraphIndex.CascadeStrata

/-!
# W3d-2 item 3b — the stratum-staged shadow and the routed read bridge (ROADMAP W3d-2)

The two-round chain's structural layer (edge discipline, endpoint closure, the
untainted-core shadow at every `ReachedByW3d2` state) and the **stratum-staged read
bridge**: the ROUTED compiled guard of a derived def equals `sem` at any shadowed
state whose DERIVED operand keys are `SettledKey ∧ CompleteKey` — untainted operand
leaves read through the shadow (W2, as in `checkFn_eq_sem_w3d`), derived operand
leaves read `probeDerived` at a settled+complete key, which is exactly the `sem`
verdict (`probeDerived_eq_sem_settled`, factored out of `graph_correct_w3d`'s
derived branch). This is the guard form `reconcile` actually evaluates at a
stratum-2 key once round 1 has re-settled its stratum-1 operands
(`processor.py:43-70` routing; `:714-719` the per-round key loop).

**Attack-first (2026-07-12e, `#eval` against the real `writeLoggedRules` /
`runCascade2` / `check` / `checkFnR` / `sem`; scratch deleted).** On the 2-stratum
schema `c := x ∖ y`, `b := c ∨ z`:
* **The W3d-1-shaped invariant "dirty ∨ settled" is REFUTED at W3d-2 post-write
  states**: after `write y(alice)` (on a store where `x(alice)` made `b` true) the
  dirty set is exactly `[(doc, c, 1)]` — the stratum-2 key `b` is STALE
  (`check = true ≠ sem = false`) yet NOT dirty: a write row can never reach the
  stratum-1 R-node (its in-edge sources are bare, in-edge-free), so
  `_map_deltas_to_keys` maps only the operand key. The W3d-2 settledness invariant
  must carry a third disjunct — *some derived operand key is dirty* — the
  stratum-staged form the 12c mid-drain finding predicted.
* **The bridge SURVIVED and its settledness hypothesis is load-bearing**: at the
  post-round-1 mid state (operand `c` re-settled) `checkFnR = sem = false` while
  `b`'s STORED representation still reads stale (`check = true`); at the
  pre-round-1 state (operand unsettled) `checkFnR = true ≠ sem`.
* Fully drained, `check = sem` across the 5-relation grid, and round 1's emission
  at `c` re-dirties exactly `[(doc, b, 1)]` for round 2.
-/

namespace Zanzibar

/-! ## Routed-fold structural mirrors (nodes monotone, off-target edge preservation) -/

/-- The routed diffing fold only adds nodes. -/
theorem reconcileKeyDR_nodes_mono (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      ∀ k ∈ σ.nodes, k ∈ (σ.reconcileKeyDR T dt on R e cands).nodes := by
  intro cands
  induction cands with
  | nil => intro σ k hk; exact hk
  | cons c rest ih =>
    intro σ k hk
    rw [reconcileKeyDR_cons]
    split
    · exact ih _ k (writeDirect_monoNodes σ _ k hk)
    · exact ih _ k hk

/-- Edges whose target is not the pass's R-node survive the routed diffing fold. -/
theorem reconcileKeyDR_edge_pres_target (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState) (ab : NodeKey × NodeKey),
      ab.2 ≠ objNode ⟨dt, on⟩ R → ab ∈ σ.edges →
      ab ∈ (σ.reconcileKeyDR T dt on R e cands).edges := by
  intro cands
  induction cands with
  | nil => intro σ ab _ hab; exact hab
  | cons c rest ih =>
    intro σ ab hne hab
    rw [reconcileKeyDR_cons]
    split
    · exact ih _ ab hne (writeDirect_edges_mono σ _ ab hab)
    · refine ih _ ab hne ?_
      obtain ⟨a, b⟩ := ab
      exact mem_removeEdgePair_edges.mpr ⟨hab, fun h => hne h.2⟩

/-- The routed logged batch preserves edge endpoint-closure (residue writes and
    emissions are edge/node-inert). -/
theorem edgesClosed_reconcileJobsLR {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState),
      (∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) →
      ∀ ab ∈ (reconcileJobsLR S T σ jobs).edges,
        ab.1 ∈ (reconcileJobsLR S T σ jobs).nodes
          ∧ ab.2 ∈ (reconcileJobsLR S T σ jobs).nodes := by
  intro jobs
  induction jobs with
  | nil => intro σ hcl; exact hcl
  | cons j rest ih =>
    intro σ hcl
    have hfold : reconcileJobsLR S T σ (j :: rest)
        = reconcileJobsLR S T (j.applyLoggedR S T σ) rest := by
      unfold reconcileJobsLR
      rw [List.foldl_cons]
    rw [hfold]
    refine ih _ ?_
    intro ab hab
    unfold W3cJob.applyLoggedR at hab ⊢
    rw [pushDelta_edges] at hab
    rw [pushDelta_nodes]
    unfold W3cJob.applyDR GraphState.reconcileStarsKeyDR at hab ⊢
    refine edgesClosed_reconcileKeyDR T j.dt j.on j.R j.e j.cands _ ?_ ab hab
    intro ab' hab'
    rw [reconcileResidueKeyR_edges] at hab'
    rw [reconcileResidueKeyR_nodes]
    exact hcl ab' hab'

/-! ## The two-round chain's structural facts -/

/-- A two-round cascade run either accepts (the drained two-round batch) or rejects
    (identity) — mirror of `runCascade_cases`. -/
theorem runCascade2_cases (S : Schema) (T : Store) (σ : GraphState)
    (jobs1 jobs2 : List W3cJob) :
    runCascade2 S T σ jobs1 jobs2
        = { reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2 with
            watermark := (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1)
              jobs2).maxOutboxId }
      ∨ runCascade2 S T σ jobs1 jobs2 = σ := by
  unfold runCascade2
  split
  · exact Or.inl rfl
  · exact Or.inr rfl

/-- **Every W3d-2 state is edge endpoint-closed.** -/
theorem reachedByW3d2_edgesClosed {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes := by
  induction h with
  | empty S =>
    intro ab hab
    simp [emptyState] at hab
  | @write σp S T t hadm hprev ih =>
    have hev := writeLoggedRules_evalEq (EvalEq.refl σp) S t
    intro ab hab
    rw [hev.edges] at hab
    rw [hev.nodes]
    exact edgesClosed_foldl_writeDirect (rewriteClosure S t) σp ih ab hab
  | @cascade σp S T jobs1 jobs2 _ _ _ _ _ _ _ ih =>
    intro ab hab
    rcases runCascade2_cases S T σp jobs1 jobs2 with hrc | hrc
    · rw [hrc] at hab ⊢
      exact edgesClosed_reconcileJobsLR jobs2 _
        (edgesClosed_reconcileJobsLR jobs1 σp ih) ab hab
    · rw [hrc] at hab ⊢
      exact ih ab hab

/-- **Every W3d-2 edge target has a non-`BARE` predicate** (mirror of
    `reachedByW3d_edge_target_ne_bare`; store hypotheses prefix-weakened). -/
theorem reachedByW3d2_edge_target_ne_bare {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    WF S → StoreValidRules S T → ∀ a b, (a, b) ∈ σ.edges → b.pred ≠ BARE := by
  induction h with
  | empty S =>
    intro _ _ a b hab
    simp [emptyState] at hab
  | @write σp S T t hadm hprev ih =>
    intro hWF hSV a b hab
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hab
    rcases foldl_writeDirect_edges_sound (rewriteClosure S t) hab with hold | ⟨u, hu, _, h2⟩
    · exact ih hWF (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) a b hold
    · rw [h2, objNode_pred]
      exact rewriteClosure_rel_ne_bare hWF hSV List.mem_cons_self hu
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro hWF hSV a b hab
    unfold runCascade2 at hab
    split at hab
    · have hab' : (a, b) ∈ (reconcileJobsLR S T (reconcileJobsLR S T σp jobs1)
          jobs2).edges := hab
      rcases reconcileJobsLR_edge_sound jobs2 _ a b hab' with hmid | ⟨j, hj, c, _, _, h2⟩
      · rcases reconcileJobsLR_edge_sound jobs1 σp a b hmid
          with hold | ⟨j, hj, c, _, _, h2⟩
        · exact ih hWF hSV a b hold
        · obtain ⟨hRne, _⟩ := hjv1 j hj
          rw [h2, objNode_pred]
          exact hRne
      · obtain ⟨hRne, _⟩ := hjv2 j hj
        rw [h2, objNode_pred]
        exact hRne
    · exact ih hWF hSV a b hab

/-- A `BARE`-predicate node is never an edge target on a W3d-2 state. -/
theorem reachedByW3d2_bareNode_no_inedge {σ : GraphState} {S : Schema} {T : Store}
    (hWF : WF S) (hSV : StoreValidRules S T) (h : ReachedByW3d2 σ S T)
    {k : NodeKey} (hk : k.pred = BARE) : ∀ x, (x, k) ∉ σ.edges := by
  intro x hxk
  exact reachedByW3d2_edge_target_ne_bare h hWF hSV x k hxk hk

/-- **Every W3d-2 edge target is plain** on `BareStarStore` stores (the fan-out
    fence, as in `reachedByW3d_edges_target_plain`). -/
theorem reachedByW3d2_edges_target_plain {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    BareStarStore T → ∀ ab ∈ σ.edges, ab.2.variant = Variant.plain := by
  induction h with
  | empty S =>
    intro _ ab hab
    simp [emptyState] at hab
  | @write σp S T t hadm hprev ih =>
    intro hBS ab hab
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hab
    obtain ⟨a, b⟩ := ab
    rcases foldl_writeDirect_edges_sound (rewriteClosure S t) hab with hold | ⟨w, hw, _, h2⟩
    · exact ih (fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')) (a, b) hold
    · show b.variant = Variant.plain
      have hwo : w.object.name ≠ STAR := by
        rw [rewriteClosure_object hw]
        exact (hBS t List.mem_cons_self).2
      rw [h2, objNode_plain hwo]
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro hBS ab hab
    unfold runCascade2 at hab
    split at hab
    · have hab' : ab ∈ (reconcileJobsLR S T (reconcileJobsLR S T σp jobs1)
          jobs2).edges := hab
      obtain ⟨a, b⟩ := ab
      rcases reconcileJobsLR_edge_sound jobs2 _ a b hab' with hmid | ⟨j, hj, c, _, _, h2⟩
      · rcases reconcileJobsLR_edge_sound jobs1 σp a b hmid
          with hold | ⟨j, hj, c, _, _, h2⟩
        · exact ih hBS (a, b) hold
        · obtain ⟨_, _, _, _, _, _, _, _, hon⟩ := hjv1 j hj
          show b.variant = Variant.plain
          rw [h2, objNode_plain hon]
      · obtain ⟨_, _, _, _, _, _, _, _, hon⟩ := hjv2 j hj
        show b.variant = Variant.plain
        rw [h2, objNode_plain hon]
    · exact ih hBS ab hab

/-- **Every in-edge source at a `RootBoolean` derived R-node is bare** on a W3d-2
    state (write legs never land there — model-level I5; cascade edges are sourced
    at bare candidates in BOTH rounds). -/
theorem reachedByW3d2_Rnode_source_bare {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {e : Expr}
    (h : ReachedByW3d2 σ S T) :
    NodupKeys S → S.lookup (dt, R) = some e → RootBoolean e → StoreValidRules S T →
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE := by
  induction h with
  | empty S =>
    intro _ _ _ _ x hx
    simp [emptyState] at hx
  | @write σp S T t hadm hprev ih =>
    intro hNK hlk hroot hSV x hx
    rw [writeLeg_derived_inedges_eq hNK hSV hlk hroot x] at hx
    exact ih hNK hlk hroot (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) x hx
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro hNK hlk hroot hSV x hx
    unfold runCascade2 at hx
    split at hx
    · have hx' : (x, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T
          (reconcileJobsLR S T σp jobs1) jobs2).edges := hx
      rcases reconcileJobsLR_edge_sound jobs2 _ x _ hx' with hmid | ⟨j, hj, c, hc, h1, _⟩
      · rcases reconcileJobsLR_edge_sound jobs1 σp x _ hmid
          with hold | ⟨j, hj, c, hc, h1, _⟩
        · exact ih hNK hlk hroot hSV x hold
        · obtain ⟨_, hcb, _⟩ := hjv1 j hj
          rw [h1, subjNode_pred]
          exact hcb c hc
      · obtain ⟨_, hcb, _⟩ := hjv2 j hj
        rw [h1, subjNode_pred]
        exact hcb c hc
    · exact ih hNK hlk hroot hSV x hx

/-- **The W3d-2 reach collapse at a `RootBoolean` derived R-node**: any path into
    the R-node is a single edge. -/
theorem reachedByW3d2_reach_collapse_root {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {e : Expr} {u : NodeKey}
    (hWF : WF S) (hSV : StoreValidRules S T) (hNK : NodupKeys S)
    (hlk : S.lookup (dt, R) = some e) (hroot : RootBoolean e)
    (h : ReachedByW3d2 σ S T)
    (hr : NReaches σ.edges u (objNode ⟨dt, on⟩ R)) :
    (u, objNode ⟨dt, on⟩ R) ∈ σ.edges := by
  refine nreaches_collapse_of_source_notarget ?_ hr
  intro x hxv
  exact reachedByW3d2_bareNode_no_inedge hWF hSV h
    (reachedByW3d2_Rnode_source_bare h hNK hlk hroot hSV x hxv)

/-! ## The untainted-core shadow over the two-round chain

The routed pass writes the same fields the unrouted one does — the guard swap never
changes which state components a fold branch touches — so the W3d-1b shadow
transport mirrors verbatim: pass edges are `DerNode`-targeted, removals never hit
shadow edges, sources stay bare. -/

/-- One routed LOGGED pass preserves the shadow (the emission row is
    edge/node-inert; mirror of `untaintedShadow_applyD`). -/
theorem untaintedShadow_applyLoggedR {S : Schema} {T : Store} {σ σ0 : GraphState}
    {j : W3cJob}
    (hsh : UntaintedShadow S σ σ0) (h0 : ReachedByRules σ0 S T)
    (hSV : StoreValidRules S T) (hNK : NodupKeys S)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hjv : W3cJobValid S j) :
    UntaintedShadow S (j.applyLoggedR S T σ) σ0 := by
  obtain ⟨hRne, hcb, _, _, _, _, hder, hlke, hon⟩ := hjv
  have hroot : RootBoolean j.e :=
    hRootB ⟨(j.dt, j.R), j.e⟩ (mem_defs_of_lookup hlke) hder
  have hnojob : ∀ ab ∈ σ0.edges, ab.2 ≠ objNode ⟨j.dt, j.on⟩ j.R := by
    intro ab hab heq
    have hno := reachedByRules_RootBoolean_no_inedge (on := j.on) hSV hNK hlke hroot h0 ab.1
    rw [← heq] at hno
    exact hno hab
  have hsound : ∀ a b, (a, b) ∈ (j.applyLoggedR S T σ).edges →
      (a, b) ∈ σ.edges ∨ ∃ c ∈ j.cands, a = subjNode c ∧ b = objNode ⟨j.dt, j.on⟩ j.R := by
    intro a b hab
    unfold W3cJob.applyLoggedR at hab
    rw [pushDelta_edges] at hab
    unfold W3cJob.applyDR at hab
    exact reconcileStarsKeyDR_edge_sound T j.dt j.on j.R j.e (wildcardShapes S)
      j.cands j.negCands j.uposCands σ a b hab
  have hEfix : (j.applyLoggedR S T σ).edges
      = ((σ.reconcileResidueKeyR T j.dt j.on j.R j.e (wildcardShapes S) j.negCands
          j.uposCands).reconcileKeyDR T j.dt j.on j.R j.e j.cands).edges := by
    unfold W3cJob.applyLoggedR
    rw [pushDelta_edges]
    rfl
  have hNfix : (j.applyLoggedR S T σ).nodes
      = ((σ.reconcileResidueKeyR T j.dt j.on j.R j.e (wildcardShapes S) j.negCands
          j.uposCands).reconcileKeyDR T j.dt j.on j.R j.e j.cands).nodes := by
    unfold W3cJob.applyLoggedR
    rw [pushDelta_nodes]
    rfl
  refine ⟨?_, ?_, ?_, ?_, hsh.closed0, ?_⟩
  · -- classify
    intro ab hab
    obtain ⟨a, b⟩ := ab
    rcases hsound a b hab with hold | ⟨c, _, _, h2⟩
    · exact hsh.classify (a, b) hold
    · exact Or.inr ⟨j.dt, j.on, j.R, hder, hRne, hon, h2⟩
  · -- sub
    intro ab hab
    rw [hEfix]
    refine reconcileKeyDR_edge_pres_target T j.dt j.on j.R j.e j.cands _ ab
      (hnojob ab hab) ?_
    rw [reconcileResidueKeyR_edges]
    exact hsh.sub ab hab
  · -- nodesSub
    intro k hk
    rw [hNfix]
    refine reconcileKeyDR_nodes_mono T j.dt j.on j.R j.e j.cands _ k ?_
    show k ∈ (σ.reconcileResidueKeyR T j.dt j.on j.R j.e (wildcardShapes S) j.negCands
      j.uposCands).nodes
    rw [reconcileResidueKeyR_nodes]
    exact hsh.nodesSub k hk
  · -- closed
    intro ab hab
    rw [hEfix] at hab
    rw [hNfix]
    refine edgesClosed_reconcileKeyDR T j.dt j.on j.R j.e j.cands _ ?_ ab hab
    intro ab' hab'
    rw [reconcileResidueKeyR_edges] at hab'
    rw [reconcileResidueKeyR_nodes]
    exact hsh.closed ab' hab'
  · -- term
    intro k hk y hy
    rcases hsound k y hy with hold | ⟨c, hc, h1, _⟩
    · exact hsh.term k hk y hold
    · obtain ⟨dt, on, R, _, hRne', _, hkey⟩ := hk
      have : R = c.predicate := by
        have hp := congrArg NodeKey.pred (hkey.symm.trans h1)
        simpa [objNode_pred, subjNode_pred] using hp
      rw [hcb c hc] at this
      exact hRne' this

/-- The routed logged batch preserves the shadow — every prefix state of either
    round's job loop is shadowed (the read bridge holds MID-ROUND). -/
theorem untaintedShadow_reconcileJobsLR {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ σ0 : GraphState), UntaintedShadow S σ σ0 →
      ReachedByRules σ0 S T → StoreValidRules S T → NodupKeys S →
      (∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2) →
      (∀ j ∈ jobs, W3cJobValid S j) →
      UntaintedShadow S (reconcileJobsLR S T σ jobs) σ0 := by
  intro jobs
  induction jobs with
  | nil => intro σ σ0 hsh _ _ _ _ _; exact hsh
  | cons j rest ih =>
    intro σ σ0 hsh h0 hSV hNK hRootB hjv
    have hfold : reconcileJobsLR S T σ (j :: rest)
        = reconcileJobsLR S T (j.applyLoggedR S T σ) rest := by
      unfold reconcileJobsLR
      rw [List.foldl_cons]
    rw [hfold]
    exact ih _ _ (untaintedShadow_applyLoggedR hsh h0 hSV hNK hRootB
        (hjv j List.mem_cons_self))
      h0 hSV hNK hRootB (fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj'))

/-- **A two-round cascade leg preserves the shadow** (σ0 fixed). -/
theorem untaintedShadow_cascade2 {S : Schema} {T : Store} {σ σ0 : GraphState}
    {jobs1 jobs2 : List W3cJob}
    (hsh : UntaintedShadow S σ σ0) (h0 : ReachedByRules σ0 S T)
    (hSV : StoreValidRules S T) (hNK : NodupKeys S)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hjv1 : ∀ j ∈ jobs1, W3cJobValid S j) (hjv2 : ∀ j ∈ jobs2, W3cJobValid S j) :
    UntaintedShadow S (runCascade2 S T σ jobs1 jobs2) σ0 := by
  unfold runCascade2
  split
  · have hD := untaintedShadow_reconcileJobsLR jobs2 _ σ0
      (untaintedShadow_reconcileJobsLR jobs1 σ σ0 hsh h0 hSV hNK hRootB hjv1)
      h0 hSV hNK hRootB hjv2
    exact ⟨hD.classify, hD.sub, hD.nodesSub, hD.closed, hD.closed0, hD.term⟩
  · exact hsh

/-- **`reachedByW3d2_shadow`** — every W3d-2 state has an untainted-core shadow:
    a rules-ADMITTED state on the CURRENT store agreeing on everything off the
    derived R-nodes. Mirror of `reachedByW3d_shadow` over the two-round legs. -/
theorem reachedByW3d2_shadow {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    NodupKeys S →
    (∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2) →
    StoreValidRules S T →
    (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) →
    ∃ σ0, ReachedByRulesAdmitted σ0 S T ∧ UntaintedShadow S σ σ0 := by
  induction h with
  | empty S =>
    intro _ _ _ _
    refine ⟨emptyState S, ReachedByRulesAdmitted.empty S, ?_, ?_, ?_, ?_, ?_, ?_⟩
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k hk; simp [emptyState] at hk
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k _ y hy; simp [emptyState] at hy
  | @write σp S T t hadm hprev ih =>
    intro hNK hRootB hSV hterm
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hRootB
      (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht'))
      (fun dt R hder => ⟨(hterm dt R hder).1,
        fun t' ht' => (hterm dt R hder).2 t' (List.mem_cons_of_mem _ ht')⟩)
    have hsubj : ∀ u ∈ rewriteClosure S t, ¬ DerNode S (subjNode u.subject) := by
      rintro u hu ⟨dt, on, R, hder, _hRne, _hon, heq⟩
      obtain ⟨hnt, hns⟩ := hterm dt R hder
      have hpne : u.subject.predicate ≠ R :=
        rewriteClosure_subject_pred_ne hnt (hns t List.mem_cons_self) hu
      apply hpne
      have hp := congrArg NodeKey.pred heq
      simpa [subjNode_pred, objNode_pred] using hp
    exact ⟨σ0.writeRules S t,
      ReachedByRulesAdmitted.step t h0
        (untaintedShadow_foldAdmits (rewriteClosure S t) σp σ0 hsh hsubj hadm),
      untaintedShadow_writeLeg (rewriteClosure S t) σp σ0 hsh hsubj⟩
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ hprev ih =>
    intro hNK hRootB hSV hterm
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hRootB hSV hterm
    exact ⟨σ0, h0,
      untaintedShadow_cascade2 hsh (reachedByRules_of_admitted h0) hSV hNK hRootB
        hjv1 hjv2⟩

/-! ## The settled-key derived read — `probeDerived = sem` at a settled+complete key

The `sem`-level content of `graph_correct_w3d`'s derived branch, factored into a
pure per-key lemma (no chain hypothesis): given the key's reach collapse and the
linchpin (`sem`-covered bare shapes are declared), a `SettledKey ∧ CompleteKey` key
reads at `sem` level for every in-scope subject. This is what a ROUTED derived
operand leaf consumes once its stratum-1 key is settled. -/

theorem probeDerived_eq_sem_settled {S : Schema} {T : Store} {σ : GraphState}
    {dt on R : String}
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (hcollapse : ∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ R) →
      (u, objNode ⟨dt, on⟩ R) ∈ σ.edges)
    (hsem_ws : ∀ sh : Shape, sh.2 = BARE →
      sem S T ⟨starSubj sh, R, ⟨dt, on⟩⟩ = true → sh ∈ wildcardShapes S)
    (hset : SettledKey S T σ dt on R) (hcomp : CompleteKey S T σ dt on R)
    {s : SubjectRef} (hqs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    GraphModel.probeDerived σ ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  obtain ⟨st, sn, sp⟩ := s
  replace hqs : sn = STAR → sp = BARE := hqs
  obtain ⟨hrowS, hedgeS⟩ := hset
  obtain ⟨hrowE, hedgeC, huposC, hnegC⟩ := hcomp
  rw [probeDerived_eq σ hon]
  -- reach ⇒ sem for star-free bare subjects: the collapse + the settled edges
  have hreach_sem : sn ≠ STAR → sp = BARE →
      σ.reach (subjNode ⟨st, sn, sp⟩) (objNode ⟨dt, on⟩ R) = true →
      sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ = true := by
    intro hsn hspb hr
    have hedge := hcollapse _ (reach_sound hr)
    exact hedgeS ⟨st, sn, sp⟩ hspb hsn hedge
  by_cases hstar : sn = STAR
  · -- ---- star subject: the `stars` read ----
    subst hstar
    have hsp : sp = BARE := hqs rfl
    subst hsp
    rw [if_pos rfl]
    cases hrow : σ.residue (objNode ⟨dt, on⟩ R) R with
    | none =>
      rw [Option.getD_none]
      cases hsm : sem S T ⟨⟨st, STAR, BARE⟩, R, ⟨dt, on⟩⟩
      · rfl
      · exfalso
        have hws := hsem_ws (st, BARE) rfl hsm
        have hsome := hrowE (st, BARE) hws hsm
        rw [hrow] at hsome
        exact absurd hsome (by decide)
    | some res =>
      rw [Option.getD_some]
      cases hc : res.stars.contains (st, BARE) <;>
        cases hsm : sem S T ⟨⟨st, STAR, BARE⟩, R, ⟨dt, on⟩⟩
      · rfl
      · exfalso
        have hws := hsem_ws (st, BARE) rfl hsm
        have := ((hrowS res hrow).1 (st, BARE)).mpr ⟨hws, hsm⟩
        rw [hc] at this
        exact absurd this (by decide)
      · exfalso
        obtain ⟨_, hs⟩ := ((hrowS res hrow).1 (st, BARE)).mp hc
        have hs' : sem S T ⟨⟨st, STAR, BARE⟩, R, ⟨dt, on⟩⟩ = true := hs
        rw [hsm] at hs'
        exact absurd hs' (by decide)
      · rfl
  · rw [if_neg hstar]
    by_cases hbare : sp = BARE
    · -- ---- bare subject: edge ∨ (stars ∖ neg) ----
      subst hbare
      rw [if_pos rfl]
      cases hrow : σ.residue (objNode ⟨dt, on⟩ R) R with
      | none =>
        rw [Option.getD_none]
        have hsimp : (Residue.empty.stars.contains (st, BARE) &&
            !Residue.empty.neg.contains ⟨st, sn, BARE⟩) = false := rfl
        rw [hsimp, Bool.or_false]
        cases hr : σ.reach (subjNode ⟨st, sn, BARE⟩) (objNode ⟨dt, on⟩ R) <;>
          cases hsm : sem S T ⟨⟨st, sn, BARE⟩, R, ⟨dt, on⟩⟩
        · rfl
        · exfalso
          by_cases hcov : (st, BARE) ∈ wildcardShapes S ∧
              sem S T ⟨starSubj (st, BARE), R, ⟨dt, on⟩⟩ = true
          · have hsome := hrowE (st, BARE) hcov.1 hcov.2
            rw [hrow] at hsome
            exact absurd hsome (by decide)
          · have hedge := hedgeC ⟨st, sn, BARE⟩ rfl hstar hsm hcov
            have hrc := reach_complete hcl (NReaches.edge hedge)
            rw [hr] at hrc
            exact absurd hrc (by decide)
        · exfalso
          have hsemT := hreach_sem hstar rfl hr
          rw [hsm] at hsemT
          exact absurd hsemT (by decide)
        · rfl
      | some res =>
        rw [Option.getD_some]
        obtain ⟨hstars_iff, hnegRow, _⟩ := hrowS res hrow
        have hfwd : (σ.reach (subjNode ⟨st, sn, BARE⟩) (objNode ⟨dt, on⟩ R)
            || (res.stars.contains (st, BARE) && !res.neg.contains ⟨st, sn, BARE⟩)) = true →
            sem S T ⟨⟨st, sn, BARE⟩, R, ⟨dt, on⟩⟩ = true := by
          intro hread
          rw [Bool.or_eq_true, Bool.and_eq_true] at hread
          rcases hread with hr | ⟨hcS, hnN⟩
          · exact hreach_sem hstar rfl hr
          · by_contra hsm
            rw [Bool.not_eq_true] at hsm
            obtain ⟨hws, hsemStar⟩ := (hstars_iff (st, BARE)).mp hcS
            obtain ⟨res', hres', hmem⟩ := hnegC ⟨st, sn, BARE⟩ hstar hws hsemStar hsm
            rw [hrow] at hres'
            obtain rfl := Option.some.inj hres'
            have hcont : res.neg.contains ⟨st, sn, BARE⟩ = true := by
              rw [List.contains_eq_mem]
              exact decide_eq_true hmem
            rw [hcont] at hnN
            exact absurd hnN (by decide)
        have hbwd : sem S T ⟨⟨st, sn, BARE⟩, R, ⟨dt, on⟩⟩ = true →
            (σ.reach (subjNode ⟨st, sn, BARE⟩) (objNode ⟨dt, on⟩ R)
              || (res.stars.contains (st, BARE) && !res.neg.contains ⟨st, sn, BARE⟩)) = true := by
          intro hsm
          rw [Bool.or_eq_true, Bool.and_eq_true]
          by_cases hcov : (st, BARE) ∈ wildcardShapes S ∧
              sem S T ⟨starSubj (st, BARE), R, ⟨dt, on⟩⟩ = true
          · refine Or.inr ⟨(hstars_iff (st, BARE)).mpr hcov, ?_⟩
            cases hcnt : res.neg.contains ⟨st, sn, BARE⟩
            · rfl
            · exfalso
              have hmem : (⟨st, sn, BARE⟩ : SubjectRef) ∈ res.neg := by
                rw [List.contains_eq_mem] at hcnt
                exact of_decide_eq_true hcnt
              obtain ⟨_, hsemF⟩ := hnegRow _ hmem
              rw [hsm] at hsemF
              exact absurd hsemF (by decide)
          · exact Or.inl (reach_complete hcl (NReaches.edge
              (hedgeC ⟨st, sn, BARE⟩ rfl hstar hsm hcov)))
        cases hread : (σ.reach (subjNode ⟨st, sn, BARE⟩) (objNode ⟨dt, on⟩ R)
            || (res.stars.contains (st, BARE) && !res.neg.contains ⟨st, sn, BARE⟩)) <;>
          cases hsm : sem S T ⟨⟨st, sn, BARE⟩, R, ⟨dt, on⟩⟩
        · rfl
        · exfalso
          have := hbwd hsm
          rw [hread] at this
          exact absurd this (by decide)
        · exfalso
          have := hfwd hread
          rw [hsm] at this
          exact absurd this (by decide)
        · rfl
    · -- ---- userset subject: the `upos` read ----
      rw [if_neg hbare]
      cases hrow : σ.residue (objNode ⟨dt, on⟩ R) R with
      | none =>
        rw [Option.getD_none]
        show false = sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
        cases hsm : sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
        · rfl
        · exfalso
          obtain ⟨res', hres', _⟩ := huposC ⟨st, sn, sp⟩ hbare hstar hsm
          rw [hrow] at hres'
          cases hres'
      | some res =>
        rw [Option.getD_some]
        obtain ⟨hstars_iff, _, huposRow⟩ := hrowS res hrow
        have hns : res.stars.contains (st, sp) = false := by
          by_contra hcx
          rw [Bool.not_eq_false] at hcx
          obtain ⟨hws, _⟩ := (hstars_iff (st, sp)).mp hcx
          exact hbare (hWSbare (st, sp) hws)
        rw [hns]
        show (if res.upos.contains ⟨st, sn, sp⟩ = true then true else false)
            = sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
        cases hu : res.upos.contains ⟨st, sn, sp⟩ <;>
          cases hsm : sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
        · rfl
        · exfalso
          obtain ⟨res', hres', hmem⟩ := huposC ⟨st, sn, sp⟩ hbare hstar hsm
          rw [hrow] at hres'
          obtain rfl := Option.some.inj hres'
          have hcontains : res.upos.contains ⟨st, sn, sp⟩ = true := by
            rw [List.contains_eq_mem]
            exact decide_eq_true hmem
          rw [hu] at hcontains
          exact absurd hcontains (by decide)
        · exfalso
          have hmem : (⟨st, sn, sp⟩ : SubjectRef) ∈ res.upos := by
            rw [List.contains_eq_mem] at hu
            exact of_decide_eq_true hu
          obtain ⟨_, _, hsemT⟩ := huposRow _ hmem
          rw [hsm] at hsemT
          exact absurd hsemT (by decide)
        · rfl

/-! ## The stratum-staged read bridge — `checkFnR = sem` at settled operands

The routed guard's leaves: an UNTAINTED operand reads through the shadow at the
rules base (`graphRec_base_eq_bs`, the W2 leg — exactly as `checkFn_eq_sem_w3d`);
a DERIVED operand reads `probeDerived` at its own key, which is the `sem` verdict
once that key is settled+complete (`probeDerived_eq_sem_settled`). `evalE` then
computes one `sem` step, and fuel stability closes the loop. This is the guard
`reconcile` evaluates at a stratum-2 key in round 2, after round 1 re-settled the
stratum-1 operands (`processor.py:43-70`, `:714-719`). -/

/-- The routed mirror of `checkFn_eq_semStep`: leaf agreement transports `evalE`. -/
theorem checkFnR_eq_semStep {S : Schema} {σ : GraphState} {T : Store} {q : Query}
    {s : SubjectRef} {dt on R : String} {e : Expr} {f : Nat}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hag : ∀ r' ∈ computedRefs e,
      GraphModel.graphRecR σ s dt on r' = semAux S s T q f dt on r') :
    σ.checkFnR T s dt on R e = semAux S s T q (f + 1) dt on R := by
  have hrhs : semAux S s T q (f + 1) dt on R
      = evalE (semAux S s T q f) s T q dt on R e := by
    simp only [semAux, step, hlk]
  rw [hrhs]
  unfold GraphState.checkFnR
  exact evalE_computedOnly e hco hag

/-- `checkFnR` ignores its store argument on `ComputedOnly` defs (the routed
    node-recursion reads only the graph state; the store feeds dead leaves). -/
theorem checkFnR_store_irrel {σ : GraphState} (T1 T2 : Store) (s : SubjectRef)
    (dt on R : String) {e : Expr} (hco : ComputedOnly e) :
    σ.checkFnR T1 s dt on R e = σ.checkFnR T2 s dt on R e := by
  unfold GraphState.checkFnR
  exact evalE_computedOnly e hco (fun _ _ => rfl)

/-- **The stratum-staged read bridge (`checkFnR_eq_sem_settled`)**: at any shadowed
    state whose DERIVED operand keys (same object) are settled+complete and
    reach-collapsed, the ROUTED compiled guard of a derived def equals `sem`.
    `hLU2` supplies the operands' own all-untainted defs (two strata); subjects
    star-BARE-scoped as everywhere on the fragment. -/
theorem checkFnR_eq_sem_settled {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (hσS : σ.schema = S)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hLU2 : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges))
    (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    σ.checkFnR T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hDecl : StoreDeclared S T := storeDeclared_of_validRules hSV
  have hag : ∀ r' ∈ computedRefs e,
      GraphModel.graphRecR σ s dt on r'
        = semAux S s T ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r' := by
    intro r' hr'
    have hstep : GraphModel.graphRecR σ s dt on r' = sem S T ⟨s, r', ⟨dt, on⟩⟩ := by
      cases hd' : isDerived S (dt, r') with
      | false =>
        -- untainted operand: routing + the shadow + the W2 base equation
        rw [GraphModel.graphRecR_eq_graphRec s on (by rw [hσS]; exact hd'),
          shadow_graphRec_agree hsh s on hd']
        exact graphRec_base_eq_bs hWF hTT hNK hR hSV hBS hTS hRootB hMatch h0
          hs hon r' hd'
      | true =>
        -- derived operand: routing + the settled-key read
        obtain ⟨hset', hcomp', hcollapse'⟩ := hops r' hr' hd'
        obtain ⟨e', hlk'⟩ := isDerived_declared hd'
        have hleafUnt' : ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false :=
          hLU2 r' hr' hd' e' hlk'
        have hco' : ComputedOnly e' := hCO dt r' e' hlk' hd'
        have hsem_ws' : ∀ sh : Shape, sh.2 = BARE →
            sem S T ⟨starSubj sh, r', ⟨dt, on⟩⟩ = true → sh ∈ wildcardShapes S := by
          intro sh hshb hsm
          refine coveredFn_declared hTT hSV hTS h0 hco'
            (dt := dt) (on := on) (R := r') ?_
          show σ0.checkFn T (starSubj sh) dt on r' e' = true
          rw [checkFn_eq_sem_bs hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm
            (ReachedByW3aAdmitted.base h0) hlk' hco' hleafUnt' (fun _ => hshb) hon]
          exact hsm
        show GraphModel.check σ ⟨s, r', ⟨dt, on⟩⟩ = sem S T ⟨s, r', ⟨dt, on⟩⟩
        rw [GraphModel.check_derived σ ⟨s, r', ⟨dt, on⟩⟩ (by rw [hσS]; exact hd')]
        exact probeDerived_eq_sem_settled hWSbare hsh.closed hcollapse' hsem_ws'
          hset' hcomp' hs hon
    rw [hstep]
    exact semAux_qirrel S s T ⟨s, r', ⟨dt, on⟩⟩ ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r'
  rw [checkFnR_eq_semStep hlk hco hag]
  exact sem_fuel_stable S T ⟨s, R, ⟨dt, on⟩⟩ hStrat hDecl (fuelBound S T + 1)
    (Nat.le_succ _)

end Zanzibar
