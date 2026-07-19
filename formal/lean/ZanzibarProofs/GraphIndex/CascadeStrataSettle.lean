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
  | @remove σp S T t _ _ _ _ _ _ _ ih =>
    intro ab hab
    rw [removeLoggedRules_nodes]
    exact ih ab (mem_removeLoggedRules_edges hab)
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
  | @remove σp S T t _ _ hSVT _ _ _ _ ih =>
    intro hWF _ a b hab
    exact ih hWF hSVT a b (mem_removeLoggedRules_edges hab)
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
  | @remove σp S T t _ _ _ hBST _ _ _ ih =>
    intro _ ab hab
    exact ih hBST ab (mem_removeLoggedRules_edges hab)
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

/-- **Every in-edge source at a derived R-node is bare** on a W3d-2
    state (write legs never land there — model-level I5; cascade edges are sourced
    at bare candidates in BOTH rounds). -/
theorem reachedByW3d2_Rnode_source_bare {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {e : Expr}
    (h : ReachedByW3d2 σ S T) :
    S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e →
    StoreValidRules S T →
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE := by
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
        · obtain ⟨_, hcb, _⟩ := hjv1 j hj
          rw [h1, subjNode_pred]
          exact hcb c hc
      · obtain ⟨_, hcb, _⟩ := hjv2 j hj
        rw [h1, subjNode_pred]
        exact hcb c hc
    · exact ih hlk hder hco hSV x hx

/-- **The W3d-2 reach collapse at a derived R-node**: any path into
    the R-node is a single edge. -/
theorem reachedByW3d2_reach_collapse_root {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {e : Expr} {u : NodeKey}
    (hWF : WF S) (hSV : StoreValidRules S T)
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true) (hco : ComputedOnly e)
    (h : ReachedByW3d2 σ S T)
    (hr : NReaches σ.edges u (objNode ⟨dt, on⟩ R)) :
    (u, objNode ⟨dt, on⟩ R) ∈ σ.edges := by
  refine nreaches_collapse_of_source_notarget ?_ hr
  intro x hxv
  exact reachedByW3d2_bareNode_no_inedge hWF hSV h
    (reachedByW3d2_Rnode_source_bare h hlk hder hco hSV x hxv)

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
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hjv : W3cJobValid S j) :
    UntaintedShadow S (j.applyLoggedR S T σ) σ0 := by
  obtain ⟨hRne, hcb, _, _, _, _, hder, hlke, hon⟩ := hjv
  have hco : ComputedOnly j.e := hCO j.dt j.R j.e hlke hder
  have hnojob : ∀ ab ∈ σ0.edges, ab.2 ≠ objNode ⟨j.dt, j.on⟩ j.R := by
    intro ab hab heq
    have hno := reachedByRules_derived_no_inedge (on := j.on) hSV hlke hder hco h0 ab.1
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
      (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
      (∀ j ∈ jobs, W3cJobValid S j) →
      UntaintedShadow S (reconcileJobsLR S T σ jobs) σ0 := by
  intro jobs
  induction jobs with
  | nil => intro σ σ0 hsh _ _ _ _ _; exact hsh
  | cons j rest ih =>
    intro σ σ0 hsh h0 hSV hNK hCO hjv
    have hfold : reconcileJobsLR S T σ (j :: rest)
        = reconcileJobsLR S T (j.applyLoggedR S T σ) rest := by
      unfold reconcileJobsLR
      rw [List.foldl_cons]
    rw [hfold]
    exact ih _ _ (untaintedShadow_applyLoggedR hsh h0 hSV hNK hCO
        (hjv j List.mem_cons_self))
      h0 hSV hNK hCO (fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj'))

/-- **A two-round cascade leg preserves the shadow** (σ0 fixed). -/
theorem untaintedShadow_cascade2 {S : Schema} {T : Store} {σ σ0 : GraphState}
    {jobs1 jobs2 : List W3cJob}
    (hsh : UntaintedShadow S σ σ0) (h0 : ReachedByRules σ0 S T)
    (hSV : StoreValidRules S T) (hNK : NodupKeys S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hjv1 : ∀ j ∈ jobs1, W3cJobValid S j) (hjv2 : ∀ j ∈ jobs2, W3cJobValid S j) :
    UntaintedShadow S (runCascade2 S T σ jobs1 jobs2) σ0 := by
  unfold runCascade2
  split
  · have hD := untaintedShadow_reconcileJobsLR jobs2 _ σ0
      (untaintedShadow_reconcileJobsLR jobs1 σ σ0 hsh h0 hSV hNK hCO hjv1)
      h0 hSV hNK hCO hjv2
    exact ⟨hD.classify, hD.sub, hD.nodesSub, hD.closed, hD.closed0, hD.term⟩
  · exact hsh

/-! ## The remove-leg shadow transport — R5b-ii crux

A future `remove` constructor (R5b-iii) needs `reachedByW3d2_shadow`'s remove case to
transport the prior state's shadow across the logged retraction `removeLoggedRules S t`,
retargeting it at R5a's fresh rebuild `σ0'` over `T.erase t` (from `exists_admitted_erase`).
The heart is a COUNT argument: `removeLoggedRules` decrements each untainted edge's ref-count
by its occurrences in `t`'s rewrite closure (`count_removeLoggedRules`), R3 pins the pre-state
count to `untOccCount S T` (`reachedByW3d2_untOccCount`), and the store-erase split
(`untOccCount_erase`) lands it on `untOccCount S (T.erase t)` — exactly the count that
characterises the untainted edges of `σ0'` (the admitted-rebuild count bridge below). The
derived edges are untouched (`removeLoggedRules` only erases untainted edges) and stay
`DerNode`-classified from the prior shadow. -/

/-- **The admitted-rebuild count bridge.** On a rules-admitted state, an edge `(a,b)` is
    present iff its occurrence count over the store's rewrite closures is positive: forward by
    `reachedByRules_edge_sound` (the edge materialises a closure tuple), backward by
    `reachedByRulesAdmitted_edge_complete` (a materialised closure edge is present). This is the
    membership↔`untOccCount` characterisation for the fresh rebuild `σ0'`. -/
theorem mem_edges_iff_untOccCount_pos {σ0 : GraphState} {S : Schema} {T : Store}
    (h0 : ReachedByRulesAdmitted σ0 S T) (a b : NodeKey) :
    (a, b) ∈ σ0.edges ↔ 0 < untOccCount S T a b := by
  unfold untOccCount
  rw [List.count_pos_iff]
  constructor
  · intro hmem
    obtain ⟨t', ht', u, hu, hasub, hbobj⟩ :=
      reachedByRules_edge_sound (reachedByRules_of_admitted h0) a b hmem
    subst hasub; subst hbobj
    exact List.mem_map.mpr ⟨u, List.mem_flatMap.mpr ⟨t', ht', hu⟩, rfl⟩
  · intro hpos
    obtain ⟨u, humem, hueq⟩ := List.mem_map.mp hpos
    obtain ⟨t', ht', hu⟩ := List.mem_flatMap.mp humem
    have hc := reachedByRulesAdmitted_edge_complete h0 t' ht' u hu
    unfold edgeOfTuple at hueq
    rwa [hueq] at hc

/-- A bare Direct-arm restriction only matches a bare-predicate subject. -/
theorem restrictionMatches_bare {rs : List Restriction} {t : Tuple}
    (hbare : ∀ r ∈ rs, r.2.1 = BARE)
    (hmatch : restrictionMatches rs t = true) :
    t.subject.predicate = BARE := by
  unfold restrictionMatches at hmatch
  rw [List.any_eq_true] at hmatch
  obtain ⟨r, hr, hcond⟩ := hmatch
  rw [Bool.and_eq_true, Bool.and_eq_true] at hcond
  obtain ⟨⟨_htype, hpred⟩, _hstar⟩ := hcond
  rw [beq_iff_eq] at hpred
  rw [hpred]; exact hbare r hr

/-- `exprDirects e ⊆ exprDirectsAll e` (exprDirects only recurses through unions). -/
theorem exprDirects_subset_exprDirectsAll (e : Expr) :
    ∀ rs, rs ∈ exprDirects e → rs ∈ exprDirectsAll e := by
  induction e with
  | direct rs' => intro rs h; simpa [exprDirects, exprDirectsAll] using h
  | computed _ => intro rs h; simp [exprDirects] at h
  | ttu _ _ => intro rs h; simp [exprDirects] at h
  | union a b iha ihb =>
      intro rs h
      simp only [exprDirects, exprDirectsAll, List.mem_append] at h ⊢
      exact h.imp (iha rs) (ihb rs)
  | inter a b iha ihb => intro rs h; simp [exprDirects] at h
  | excl a b iha ihb => intro rs h; simp [exprDirects] at h

/-- Under `DirectArmsBare e`, every arm collected by `exprDirects` is all-BARE. -/
theorem directArmsBare_exprDirects {e : Expr} (hba : DirectArmsBare e) :
    ∀ rs ∈ exprDirects e, ∀ r ∈ rs, r.2.1 = BARE := by
  induction e with
  | direct rs' =>
      intro rs h r hr
      simp only [exprDirects, List.mem_singleton] at h; subst h
      simp only [DirectArmsBare] at hba; exact hba r hr
  | computed _ => intro rs h; simp [exprDirects] at h
  | ttu _ _ => intro rs h; simp [exprDirects] at h
  | union a b iha ihb =>
      simp only [DirectArmsBare] at hba
      intro rs h r hr
      simp only [exprDirects, List.mem_append] at h
      rcases h with h | h
      · exact iha hba.1 rs h r hr
      · exact ihb hba.2 rs h r hr
  | inter a b iha ihb => intro rs h; simp [exprDirects] at h
  | excl a b iha ihb => intro rs h; simp [exprDirects] at h

/-- `StoreValidRules` + all-derived-defs-`DirectArmsBare` ⇒ `StoreValidRulesD`. -/
theorem storeValidRulesD_of_storeValidRules_directArmsBare {S : Schema} {T : Store}
    (hSV : StoreValidRules S T)
    (hDAB : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → DirectArmsBare e) :
    StoreValidRulesD S T := by
  intro t ht
  obtain ⟨e, rs, hlk, hrs, hmatch⟩ := hSV t ht
  by_cases hder : isDerived S (t.object.type, t.relation) = true
  · have hbare := directArmsBare_exprDirects (hDAB _ _ e hlk hder) rs hrs
    exact Or.inr ⟨hder, restrictionMatches_bare hbare hmatch, e, rs, hlk,
      exprDirects_subset_exprDirectsAll e rs hrs, hmatch, hbare⟩
  · rw [Bool.not_eq_true] at hder
    exact Or.inl ⟨hder, e, rs, hlk, hrs, hmatch⟩

/-- **The load-bearing one.** A rules-admitted state over an UNTAINTED-ONLY store (no
    derived-key tuples) has NO derived-target edges — WITHOUT needing `hCO`/ComputedOnly.
    (Mirror of `reachedByRulesAdmitted_edge_target_untainted` just below, but the
    seed-tuple branch is killed by `hND` instead of by `exprDirects_computedOnly`.) -/
theorem reachedByRulesAdmitted_untStore_edge_untainted {σ0 : GraphState} {S : Schema} {T : Store}
    (hND : ∀ t ∈ T, isDerived S (t.object.type, t.relation) = false)
    (h0 : ReachedByRulesAdmitted σ0 S T) :
    ∀ a b, (a, b) ∈ σ0.edges → isDerived S (b.type, b.pred) = false := by
  intro a b hab
  by_contra hcon
  rw [Bool.not_eq_false] at hcon
  obtain ⟨t', ht', u, hu, hasub, hbobj⟩ :=
    reachedByRules_edge_sound (reachedByRules_of_admitted h0) a b hab
  have htype : b.type = u.object.type := by rw [hbobj, objNode_type]
  have hrel : b.pred = u.relation := by rw [hbobj, objNode_pred]
  rw [htype, hrel] at hcon
  rcases rewriteClosure_produced hu with heq | ⟨r, hr', hro, hrout⟩
  · subst heq
    rw [hND u ht'] at hcon
    exact absurd hcon (by simp)
  · exact noRuleOutputs_of_derived hcon r hr' ⟨hro, hrout⟩

/-- **Rules-admitted edges are untainted.** Every edge target on a rules-admitted state has a
    non-derived predicate: the edge materialises a closure tuple `u` on relation `u.relation`,
    which is never a derived key (`reachedByRules_derived_no_inedge`). -/
theorem reachedByRulesAdmitted_edge_target_untainted {σ0 : GraphState} {S : Schema} {T : Store}
    (hSV : StoreValidRules S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (h0 : ReachedByRulesAdmitted σ0 S T) :
    ∀ a b, (a, b) ∈ σ0.edges → isDerived S (b.type, b.pred) = false := by
  intro a b hab
  by_contra hcon
  rw [Bool.not_eq_false] at hcon
  obtain ⟨t', ht', u, hu, hasub, hbobj⟩ :=
    reachedByRules_edge_sound (reachedByRules_of_admitted h0) a b hab
  have htype : b.type = u.object.type := by rw [hbobj, objNode_type]
  have hrel : b.pred = u.relation := by rw [hbobj, objNode_pred]
  rw [htype, hrel] at hcon
  obtain ⟨e, hlk⟩ := isDerived_declared hcon
  have hco := hCO u.object.type u.relation e hlk hcon
  have hab2 : (a, objNode (⟨u.object.type, u.object.name⟩ : ObjectRef) u.relation) ∈ σ0.edges := by
    rw [hbobj] at hab; exact hab
  exact reachedByRules_derived_no_inedge hSV hlk hcon hco
    (reachedByRules_of_admitted h0) a hab2

/-- **Rules-admitted nodes are edge endpoints.** Every node of a rules-admitted state is an
    endpoint of some edge (the `empty` base has no nodes; `writeDirect` only ever adds a node
    together with the edge it participates in). Used to embed `σ0'.nodes` into `σp.nodes` via
    the prior shadow's `sub`/`closed`. -/
theorem foldl_writeDirect_nodesFromEdges (us : List Tuple) :
    ∀ (σ : GraphState),
      (∀ k ∈ σ.nodes, ∃ ab ∈ σ.edges, k = ab.1 ∨ k = ab.2) →
      ∀ k ∈ (us.foldl (fun acc u => acc.writeDirect u) σ).nodes,
        ∃ ab ∈ (us.foldl (fun acc u => acc.writeDirect u) σ).edges, k = ab.1 ∨ k = ab.2 := by
  induction us with
  | nil => intro σ h; exact h
  | cons u rest ih =>
    intro σ h
    refine ih (σ.writeDirect u) ?_
    intro k hk
    by_cases hadm : σ.admitEdge (subjNode u.subject) (objNode u.object u.relation) = true
    · rw [writeDirect_nodes, if_pos hadm] at hk
      rw [writeDirect_edges, if_pos hadm]
      rcases List.mem_cons.mp hk with rfl | hk1
      · exact ⟨_, List.mem_cons_self, Or.inr rfl⟩
      · rcases List.mem_cons.mp hk1 with rfl | hk2
        · exact ⟨_, List.mem_cons_self, Or.inl rfl⟩
        · obtain ⟨ab, hab, hor⟩ := h k hk2
          exact ⟨ab, List.mem_cons_of_mem _ hab, hor⟩
    · rw [Bool.not_eq_true] at hadm
      rw [writeDirect_reject hadm] at hk ⊢
      exact h k hk

theorem reachedByRulesAdmitted_nodesFromEdges {σ0 : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRulesAdmitted σ0 S T) :
    ∀ k ∈ σ0.nodes, ∃ ab ∈ σ0.edges, k = ab.1 ∨ k = ab.2 := by
  induction h with
  | empty S => intro k hk; simp [emptyState] at hk
  | @step σ S T t hprev hadm ih =>
    show ∀ k ∈ (σ.writeRules S t).nodes,
      ∃ ab ∈ (σ.writeRules S t).edges, k = ab.1 ∨ k = ab.2
    unfold GraphState.writeRules
    exact foldl_writeDirect_nodesFromEdges (rewriteClosure S t) σ ih

/-- **`untaintedShadow_removeLeg`** — the R5b-ii shadow-transport crux. Given a `ReachedByW3d2`
    state `σp` with prior untainted-core shadow `σ0` over `T`, and R5a's fresh admitted rebuild
    `σ0'` over `T.erase t` (edges ⊆ `σ0`'s, from `exists_admitted_erase`), the logged retraction
    `σp.removeLoggedRules S t` is shadowed by `σ0'`. The untainted edge SETS agree by the count
    argument (`count_removeLoggedRules` + `reachedByW3d2_untOccCount` + `untOccCount_erase` land
    both on `untOccCount S (T.erase t)`, bridged to membership on each side); the derived edges
    are untouched by the retraction (`mem_removeLoggedRules_edges`) and stay `DerNode`-classified
    from `σ0` via the prior shadow. -/
theorem untaintedShadow_removeLeg {σp σ0 σ0' : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hrb : ReachedByW3d2 σp S T)
    (hsh : UntaintedShadow S σp σ0)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    (hadm : RemoveAdmits σp T t)
    (h0' : ReachedByRulesAdmitted σ0' S (T.erase t))
    (hsub : ∀ e ∈ σ0'.edges, e ∈ σ0.edges)
    (hSV : StoreValidRules S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) :
    UntaintedShadow S (σp.removeLoggedRules S t) σ0' := by
  have ht : t ∈ T := hadm
  have hSV' : StoreValidRules S (T.erase t) :=
    fun t' ht' => hSV t' (List.mem_of_mem_erase ht')
  have hnodes : (σp.removeLoggedRules S t).nodes = σp.nodes := removeLoggedRules_nodes σp S t
  have hmem0' : ∀ a b, (a, b) ∈ σ0'.edges ↔ 0 < untOccCount S (T.erase t) a b :=
    mem_edges_iff_untOccCount_pos h0'
  have hσ0unt : ∀ a b, (a, b) ∈ σ0.edges → isDerived S (b.type, b.pred) = false :=
    reachedByRulesAdmitted_edge_target_untainted hSV hCO h0
  have hσ0'unt : ∀ a b, (a, b) ∈ σ0'.edges → isDerived S (b.type, b.pred) = false :=
    reachedByRulesAdmitted_edge_target_untainted hSV' hCO h0'
  -- the untainted count on the retracted state lands on `untOccCount S (T.erase t)`
  have hmemrem : ∀ a b, isDerived S (b.type, b.pred) = false →
      ((a, b) ∈ (σp.removeLoggedRules S t).edges ↔ 0 < untOccCount S (T.erase t) a b) := by
    intro a b hb
    have hcount : (σp.removeLoggedRules S t).edges.count (a, b)
        = untOccCount S (T.erase t) a b := by
      rw [count_removeLoggedRules (a, b) S t σp, reachedByW3d2_untOccCount hrb a b hb,
        untOccCount_erase S T t a b ht]
      omega
    rw [← hcount, List.count_pos_iff]
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩
  · -- classify
    intro ab hab
    obtain ⟨a, b⟩ := ab
    have habp : (a, b) ∈ σp.edges := mem_removeLoggedRules_edges hab
    rcases hsh.classify (a, b) habp with h0e | hD
    · have hbunt : isDerived S (b.type, b.pred) = false := hσ0unt a b h0e
      exact Or.inl ((hmem0' a b).mpr ((hmemrem a b hbunt).mp hab))
    · exact Or.inr hD
  · -- sub
    intro ab hab
    obtain ⟨a, b⟩ := ab
    have hbunt : isDerived S (b.type, b.pred) = false := hσ0'unt a b hab
    exact (hmemrem a b hbunt).mpr ((hmem0' a b).mp hab)
  · -- nodesSub
    intro k hk
    rw [hnodes]
    obtain ⟨ab, hab, hor⟩ := reachedByRulesAdmitted_nodesFromEdges h0' k hk
    have habp : ab ∈ σp.edges := hsh.sub ab (hsub ab hab)
    obtain ⟨h1, h2⟩ := hsh.closed ab habp
    rcases hor with rfl | rfl
    · exact h1
    · exact h2
  · -- closed
    intro ab hab
    rw [hnodes]
    exact hsh.closed ab (mem_removeLoggedRules_edges hab)
  · -- closed0
    exact (reachedByRules_inv (reachedByRules_of_admitted h0')).1.edgesClosed
  · -- term
    intro k hk y hy
    exact hsh.term k hk y (mem_removeLoggedRules_edges hy)

/-- **`reachedByW3d2_shadow`** — every W3d-2 state has an untainted-core shadow:
    a rules-ADMITTED state on the CURRENT store agreeing on everything off the
    derived R-nodes. Mirror of `reachedByW3d_shadow` over the two-round legs. -/
theorem reachedByW3d2_shadow {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    NodupKeys S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
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
    intro hNK hCO hSV hterm
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO
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
  | @remove σp S T t hadm _ hSVT _ _ htermT hprev ih =>
    intro hNK hCO _ _
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hSVT htermT
    obtain ⟨σ0', h0', hsub⟩ := exists_admitted_erase h0 t
    exact ⟨σ0', h0', untaintedShadow_removeLeg hprev hsh h0 hadm h0' hsub hSVT hCO⟩
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ hprev ih =>
    intro hNK hCO hSV hterm
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hSV hterm
    exact ⟨σ0, h0,
      untaintedShadow_cascade2 hsh (reachedByRules_of_admitted h0) hSV hNK hCO
        hjv1 hjv2⟩

/-! ## The FILTERED-σ0 shadow — the Direct-arm (W3d-2 `_d`) untainted-core rebuild

The naive full-store σ0 (`ReachedByRulesAdmitted σ0 S T`) is FALSE on the widened
`StoreValidRulesD` fragment (attack-refuted 2026-07-19: a stored Direct-arm subject that
is ALSO excluded — `approver := direct[user] ∖ computed banned`, store
`{(alice,approver,doc), (alice,banned,doc)}` — seeds the base edge
`subjNode alice → objNode(doc,approver)` into the full-store σ0, which the DRAINED σ
retracts, killing `UntaintedShadow.sub`). The faithful target rebuilds over the
UNTAINTED-FILTER store `T↾U := T.filter (!isDerived ∘ key)`: no derived-key seeds, so σ0
stays inside σ, and its edges are untainted-targeted WITHOUT any `ComputedOnly`
hypothesis (`reachedByRulesAdmitted_untStore_edge_untainted`).

The derived-key write/remove legs ride on the dead-end-seed collapse
(`rewriteClosure_derived_eq_seed_nk` below): under `NodupKeys` a derived-key tuple fires
NO rewrite rule — a firing rule's match key would BE the derived key, every match key of
a def the `schemaRewrites` taint filter kept is one of that def's `exprRefs`, and taint
fixpoint closedness (`taintedKeys_fixed`) would then taint the def.

**Attack-first (2026-07-20, `#eval` against the real `rewriteClosure` / `schemaRewrites`
/ `isDerived`; scratch deleted).**
* The seed collapse and all-derived-targets CONFIRMED on
  `approver := direct[user] ∖ computed banned` (+ the chained `super := computed
  approver`, + a `ttu` over a derived tupleset — taint propagates through the `exprRefs`
  ttu head `(t, ts)`, so the would-be fanout def is itself derived and filtered).
* **`NodupKeys` is load-bearing — the hNK-free claim is REFUTED**: on a duplicate key
  `(doc,x)` (first def `direct[user]`, second `computed approver`) the taint fixpoint
  reads only the FIRST def (`refsOf` goes through `lookup`), leaving `x` untainted,
  while `schemaRewrites` compiles arms of BOTH defs — emitting an `approver ↦ x` rule
  that fans a derived-key seed out to an untainted key
  (`(rewriteClosure S t).all (isDerived ∘ key) = false` observed). -/

/-- Every rewrite arm's match key is among its expression's references (`exprArms` and
    `exprRefs` walk the same union spine; `computed r ↦ (ot, r)`, `ttu tr ts ↦ (ot, ts)`). -/
theorem exprArms_matchKey_mem_exprRefs (S : Schema) (ot outRel : String) :
    ∀ (e : Expr), ∀ r ∈ exprArms ot outRel e,
      (r.objectType, r.matchRel) ∈ exprRefs S ot e := by
  intro e
  induction e with
  | direct rs => intro r hr; simp [exprArms] at hr
  | computed r' =>
      intro r hr
      simp only [exprArms, List.mem_singleton] at hr
      subst hr
      simp [exprRefs]
  | ttu tr ts =>
      intro r hr
      simp only [exprArms, List.mem_singleton] at hr
      subst hr
      simp [exprRefs]
  | union a b iha ihb =>
      intro r hr
      simp only [exprArms, List.mem_append] at hr
      simp only [exprRefs, List.mem_append]
      exact hr.imp (iha r) (ihb r)
  | inter a b iha ihb => intro r hr; simp [exprArms] at hr
  | excl a b iha ihb => intro r hr; simp [exprArms] at hr

/-- **No schema rewrite matches a DERIVED key** (under `NodupKeys`). A rule comes from a
    def the taint filter kept (`isDerived = false`); its match key is one of that def's
    references (`exprArms_matchKey_mem_exprRefs` through `lookup_of_mem`), so a tainted
    match key would taint the def by fixpoint closedness (`taintedKeys_fixed`).
    `NodupKeys` is load-bearing — attack-refuted without it (header). -/
theorem rewriteMatch_not_derived {S : Schema} (hNK : NodupKeys S) :
    ∀ r ∈ schemaRewrites S, isDerived S (r.objectType, r.matchRel) = false := by
  intro r hr
  by_contra hcon
  rw [Bool.not_eq_false] at hcon
  unfold schemaRewrites at hr
  rw [List.mem_flatMap] at hr
  obtain ⟨d, hd, hrarm⟩ := hr
  obtain ⟨hdmem, hfilt⟩ := List.mem_filter.mp hd
  have href : (r.objectType, r.matchRel) ∈ refsOf S d.1 := by
    unfold refsOf
    rw [lookup_of_mem hNK hdmem]
    exact exprArms_matchKey_mem_exprRefs S d.1.1 d.1.2 d.2 r hrarm
  have hkeys : d.1 ∈ S.keys := List.mem_map.mpr ⟨d, hdmem, rfl⟩
  have hstep : d.1 ∈ taintStep S (taintedKeys S) := by
    unfold taintStep
    refine List.mem_filter.mpr ⟨hkeys, ?_⟩
    have hany : ((refsOf S d.1).any fun k => (taintedKeys S).contains k) = true := by
      refine List.any_eq_true.mpr ⟨(r.objectType, r.matchRel), href, ?_⟩
      unfold isDerived at hcon
      exact hcon
    show (baseTaint S d.1 || (refsOf S d.1).any fun k => (taintedKeys S).contains k) = true
    rw [hany, Bool.or_true]
  have hder : d.1 ∈ taintedKeys S := (taintedKeys_fixed S d.1).mp hstep
  have hdT : isDerived S d.1 = true := by
    unfold isDerived
    rw [List.contains_eq_mem]
    exact decide_eq_true hder
  rw [hdT] at hfilt
  simp at hfilt

/-- **The dead-end-seed collapse, `NodupKeys` form** — a derived-key tuple's rewrite
    closure is the seed alone. `rewriteClosure_derived_eq_seed` (`RestrictBase.lean`)
    re-based off `rewriteMatch_not_derived` instead of `RewriteMatchDeclared`: here the
    would-be match key IS the derived key, which is declared, so no declaredness side
    condition is needed. -/
theorem rewriteClosure_derived_eq_seed_nk {S : Schema} (hNK : NodupKeys S)
    {t : Tuple} (hd : isDerived S (t.object.type, t.relation) = true) :
    rewriteClosure S t = [t] := by
  have hstep : rewriteStep S t = [] := by
    unfold rewriteStep
    rw [List.filterMap_eq_nil_iff]
    intro r hr
    unfold applyRRule
    rw [if_neg]
    rintro ⟨hrel, htype⟩
    have hu := rewriteMatch_not_derived hNK r hr
    rw [htype, hrel] at hd
    rw [hu] at hd
    exact Bool.noConfusion hd
  unfold rewriteClosure
  show rewriteClosureAux S (S.keys.length + 1) [t] = [t]
  rw [rewriteClosureAux]
  have hfm : List.flatMap (rewriteStep S) [t] = [] := by simp [hstep]
  rw [hfm, rewriteClosureAux_nil]
  rfl

/-- Splitting the store-closure occurrence count at a cons head. -/
theorem untOccCount_cons (S : Schema) (t : Tuple) (T : Store) (a b : NodeKey) :
    untOccCount S (t :: T) a b
      = ((rewriteClosure S t).map edgeOfTuple).count (a, b) + untOccCount S T a b := by
  unfold untOccCount
  rw [List.flatMap_cons, List.map_append, List.count_append]

/-- **Filter-invariance of the untainted occurrence count.** For an UNTAINTED target
    `b`, dropping the derived-key tuples changes no `(a,b)` occurrence: a derived-key
    tuple's closure is its seed alone (`rewriteClosure_derived_eq_seed_nk`), whose
    materialized edge targets the derived R-node — never the untainted `b`. -/
theorem untOccCount_untaintedFilter {S : Schema} (hNK : NodupKeys S) {b : NodeKey}
    (hb : isDerived S (b.type, b.pred) = false) (a : NodeKey) :
    ∀ T : Store,
      untOccCount S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) a b
        = untOccCount S T a b := by
  intro T
  induction T with
  | nil => rfl
  | cons t' T' ih =>
    rw [List.filter_cons]
    by_cases hd : isDerived S (t'.object.type, t'.relation) = true
    · have hzero : ((rewriteClosure S t').map edgeOfTuple).count (a, b) = 0 := by
        rw [rewriteClosure_derived_eq_seed_nk hNK hd]
        refine List.count_eq_zero.mpr ?_
        intro hmem
        rw [List.map_cons, List.map_nil, List.mem_singleton] at hmem
        have hbeq : b = objNode t'.object t'.relation := congrArg Prod.snd hmem
        rw [hbeq, objNode_type, objNode_pred, hd] at hb
        exact Bool.noConfusion hb
      rw [if_neg (by simp [hd]), untOccCount_cons, ih, hzero]
      omega
    · rw [Bool.not_eq_true] at hd
      rw [if_pos (by simp [hd]), untOccCount_cons, untOccCount_cons, ih]

/-- Filtering commutes with erasing a KEPT element (first-occurrence `erase` only ever
    meets copies the filter also keeps). -/
theorem filter_erase_pos {α : Type _} [DecidableEq α] {p : α → Bool} {t : α}
    (hp : p t = true) : ∀ l : List α, (l.erase t).filter p = (l.filter p).erase t := by
  intro l
  induction l with
  | nil => rfl
  | cons x xs ih =>
    by_cases hx : x = t
    · subst hx
      rw [List.erase_cons_head, List.filter_cons, if_pos hp, List.erase_cons_head]
    · have hbx : ((x == t) = true) → False := by
        intro hc; exact hx (by simpa using hc)
      rw [List.erase_cons, if_neg hbx, List.filter_cons]
      by_cases hpx : p x = true
      · rw [if_pos hpx, List.filter_cons, if_pos hpx, List.erase_cons, if_neg hbx, ih]
      · rw [if_neg hpx, List.filter_cons, if_neg hpx, ih]

/-- Erasing a DROPPED element is invisible to the filter. -/
theorem filter_erase_neg {α : Type _} [DecidableEq α] {p : α → Bool} {t : α}
    (hp : p t = false) : ∀ l : List α, (l.erase t).filter p = l.filter p := by
  intro l
  induction l with
  | nil => rfl
  | cons x xs ih =>
    by_cases hx : x = t
    · subst hx
      rw [List.erase_cons_head, List.filter_cons, if_neg (by simp [hp])]
    · have hbx : ((x == t) = true) → False := by
        intro hc; exact hx (by simpa using hc)
      rw [List.erase_cons, if_neg hbx, List.filter_cons, List.filter_cons]
      by_cases hpx : p x = true
      · rw [if_pos hpx, if_pos hpx, ih]
      · rw [if_neg hpx, if_neg hpx, ih]

/-- **The derived-key logged write step keeps the shadow with σ0 FIXED**: the one added
    edge targets a `DerNode` (`classify`'s right branch) and is sourced at a
    non-`DerNode` subject node (so `term` is safe); every other field is monotone.
    Mirror of `untaintedShadow_writeLoggedOne` (`CascadeStable.lean`) without the
    parallel σ0 step. -/
theorem untaintedShadow_writeLoggedOne_derived {S : Schema} {σ σ0 : GraphState}
    (hsh : UntaintedShadow S σ σ0) {u : Tuple}
    (hDer : DerNode S (objNode u.object u.relation))
    (hsubj : ¬ DerNode S (subjNode u.subject)) :
    UntaintedShadow S (σ.writeLoggedOne u) σ0 := by
  unfold GraphState.writeLoggedOne
  by_cases hb : σ.admitEdge (subjNode u.subject) (objNode u.object u.relation) = true
  · rw [if_pos hb]
    have hcl : ∀ ab ∈ (σ.writeDirect u).edges,
        ab.1 ∈ (σ.writeDirect u).nodes ∧ ab.2 ∈ (σ.writeDirect u).nodes :=
      edgesClosed_writeDirect hsh.closed u
    refine ⟨?_, ?_, ?_, ?_, hsh.closed0, ?_⟩
    · -- classify
      intro ab hab
      rw [pushDelta_edges, writeDirect_edges, if_pos hb] at hab
      rcases List.mem_cons.mp hab with heq | hmem
      · refine Or.inr ?_
        rw [heq]
        exact hDer
      · exact hsh.classify ab hmem
    · -- sub
      intro ab hab
      rw [pushDelta_edges, writeDirect_edges, if_pos hb]
      exact List.mem_cons_of_mem _ (hsh.sub ab hab)
    · -- nodesSub
      intro k hk
      rw [pushDelta_nodes, writeDirect_nodes, if_pos hb]
      exact List.mem_cons_of_mem _ (List.mem_cons_of_mem _ (hsh.nodesSub k hk))
    · -- closed
      intro ab hab
      rw [pushDelta_edges] at hab
      rw [pushDelta_nodes]
      exact hcl ab hab
    · -- term
      intro k hk y hy
      rw [pushDelta_edges, writeDirect_edges, if_pos hb] at hy
      rcases List.mem_cons.mp hy with heq | hmem
      · have h1 : k = subjNode u.subject := (Prod.ext_iff.mp heq).1
        rw [h1] at hk
        exact hsubj hk
      · exact hsh.term k hk y hmem
  · rw [if_neg hb]
    exact hsh

/-- **The derived-key write LEG keeps the shadow with σ0 FIXED** — the fold form
    (consumed at the singleton closure `[t]` of a derived-key write; stated over any
    all-`DerNode`-targeted batch). -/
theorem untaintedShadow_writeLeg_derived {S : Schema} :
    ∀ (us : List Tuple) (σ σ0 : GraphState), UntaintedShadow S σ σ0 →
      (∀ u ∈ us, DerNode S (objNode u.object u.relation)) →
      (∀ u ∈ us, ¬ DerNode S (subjNode u.subject)) →
      UntaintedShadow S (us.foldl (fun acc u => acc.writeLoggedOne u) σ) σ0 := by
  intro us
  induction us with
  | nil => intro σ σ0 hsh _ _; exact hsh
  | cons u rest ih =>
    intro σ σ0 hsh hD hs
    simp only [List.foldl_cons]
    exact ih _ _
      (untaintedShadow_writeLoggedOne_derived hsh (hD u List.mem_cons_self)
        (hs u List.mem_cons_self))
      (fun x hx => hD x (List.mem_cons_of_mem _ hx))
      (fun x hx => hs x (List.mem_cons_of_mem _ hx))

/-- One routed LOGGED pass preserves the shadow, `_d` form: instead of the full-store
    `hSV`/`hCO` route to "no σ0 edge targets the job's R-node"
    (`reachedByRules_derived_no_inedge`), take σ0's edge-target UNTAINTEDNESS directly —
    the filtered-σ0 rebuild supplies it via
    `reachedByRulesAdmitted_untStore_edge_untainted`, no `ComputedOnly` needed. -/
theorem untaintedShadow_applyLoggedR_d {S : Schema} {T : Store} {σ σ0 : GraphState}
    {j : W3cJob}
    (hsh : UntaintedShadow S σ σ0)
    (hunt : ∀ a b, (a, b) ∈ σ0.edges → isDerived S (b.type, b.pred) = false)
    (hjv : W3cJobValid S j) :
    UntaintedShadow S (j.applyLoggedR S T σ) σ0 := by
  obtain ⟨hRne, hcb, _, _, _, _, hder, _hlke, hon⟩ := hjv
  have hnojob : ∀ ab ∈ σ0.edges, ab.2 ≠ objNode ⟨j.dt, j.on⟩ j.R := by
    intro ab hab heq
    obtain ⟨a, b⟩ := ab
    have hbu := hunt a b hab
    have heq' : b = objNode ⟨j.dt, j.on⟩ j.R := heq
    rw [heq', objNode_type, objNode_pred, hder] at hbu
    exact Bool.noConfusion hbu
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
      have hcp : R = c.predicate := by
        have hp := congrArg NodeKey.pred (hkey.symm.trans h1)
        simpa [subjNode_pred, objNode_pred] using hp
      rw [hcb c hc] at hcp
      exact hRne' hcp

/-- The routed logged batch preserves the shadow, `_d` form. -/
theorem untaintedShadow_reconcileJobsLR_d {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ σ0 : GraphState), UntaintedShadow S σ σ0 →
      (∀ a b, (a, b) ∈ σ0.edges → isDerived S (b.type, b.pred) = false) →
      (∀ j ∈ jobs, W3cJobValid S j) →
      UntaintedShadow S (reconcileJobsLR S T σ jobs) σ0 := by
  intro jobs
  induction jobs with
  | nil => intro σ σ0 hsh _ _; exact hsh
  | cons j rest ih =>
    intro σ σ0 hsh hunt hjv
    have hfold : reconcileJobsLR S T σ (j :: rest)
        = reconcileJobsLR S T (j.applyLoggedR S T σ) rest := by
      unfold reconcileJobsLR
      rw [List.foldl_cons]
    rw [hfold]
    exact ih _ _ (untaintedShadow_applyLoggedR_d hsh hunt (hjv j List.mem_cons_self))
      hunt (fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj'))

/-- **A two-round cascade leg preserves the shadow, `_d` form** (σ0 fixed; edge-target
    untaintedness in place of `hSV`/`hCO`). -/
theorem untaintedShadow_cascade2_d {S : Schema} {T : Store} {σ σ0 : GraphState}
    {jobs1 jobs2 : List W3cJob}
    (hsh : UntaintedShadow S σ σ0)
    (hunt : ∀ a b, (a, b) ∈ σ0.edges → isDerived S (b.type, b.pred) = false)
    (hjv1 : ∀ j ∈ jobs1, W3cJobValid S j) (hjv2 : ∀ j ∈ jobs2, W3cJobValid S j) :
    UntaintedShadow S (runCascade2 S T σ jobs1 jobs2) σ0 := by
  unfold runCascade2
  split
  · have hD := untaintedShadow_reconcileJobsLR_d (T := T) jobs2 _ σ0
      (untaintedShadow_reconcileJobsLR_d (T := T) jobs1 σ σ0 hsh hunt hjv1)
      hunt hjv2
    exact ⟨hD.classify, hD.sub, hD.nodesSub, hD.closed, hD.closed0, hD.term⟩
  · exact hsh

/-- **`untaintedShadow_removeLeg`, filtered-σ0 form.** The count argument runs over the
    FULL store (`count_removeLoggedRules` + R3 `reachedByW3d2_untOccCount` +
    `untOccCount_erase`), then lands on the filtered store by count filter-invariance
    (`untOccCount_untaintedFilter` — derived-key closures contribute no untainted-target
    occurrences). Edge-target untaintedness of both rebuilds comes for free from the
    filtered store, so no `StoreValidRules`/`ComputedOnly` hypotheses survive. -/
theorem untaintedShadow_removeLeg_d {σp σ0 σ0' : GraphState} {S : Schema} {T : Store}
    {t : Tuple}
    (hNK : NodupKeys S)
    (hrb : ReachedByW3d2 σp S T)
    (hsh : UntaintedShadow S σp σ0)
    (h0 : ReachedByRulesAdmitted σ0 S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (ht : t ∈ T)
    (h0' : ReachedByRulesAdmitted σ0' S
      ((T.erase t).filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsub : ∀ e ∈ σ0'.edges, e ∈ σ0.edges) :
    UntaintedShadow S (σp.removeLoggedRules S t) σ0' := by
  have hND : ∀ t' ∈ T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)),
      isDerived S (t'.object.type, t'.relation) = false := by
    intro t' ht'
    simpa using (List.mem_filter.mp ht').2
  have hND' : ∀ t' ∈ (T.erase t).filter
        (fun tp => !isDerived S (tp.object.type, tp.relation)),
      isDerived S (t'.object.type, t'.relation) = false := by
    intro t' ht'
    simpa using (List.mem_filter.mp ht').2
  have hnodes : (σp.removeLoggedRules S t).nodes = σp.nodes := removeLoggedRules_nodes σp S t
  have hmem0' : ∀ a b, (a, b) ∈ σ0'.edges ↔
      0 < untOccCount S
        ((T.erase t).filter (fun tp => !isDerived S (tp.object.type, tp.relation))) a b :=
    mem_edges_iff_untOccCount_pos h0'
  have hσ0unt : ∀ a b, (a, b) ∈ σ0.edges → isDerived S (b.type, b.pred) = false :=
    reachedByRulesAdmitted_untStore_edge_untainted hND h0
  have hσ0'unt : ∀ a b, (a, b) ∈ σ0'.edges → isDerived S (b.type, b.pred) = false :=
    reachedByRulesAdmitted_untStore_edge_untainted hND' h0'
  have hmemrem : ∀ a b, isDerived S (b.type, b.pred) = false →
      ((a, b) ∈ (σp.removeLoggedRules S t).edges ↔
        0 < untOccCount S
          ((T.erase t).filter (fun tp => !isDerived S (tp.object.type, tp.relation))) a b) := by
    intro a b hb
    have hcount : (σp.removeLoggedRules S t).edges.count (a, b)
        = untOccCount S (T.erase t) a b := by
      rw [count_removeLoggedRules (a, b) S t σp, reachedByW3d2_untOccCount hrb a b hb,
        untOccCount_erase S T t a b ht]
      omega
    rw [untOccCount_untaintedFilter hNK hb a (T.erase t), ← hcount, List.count_pos_iff]
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩
  · -- classify
    intro ab hab
    obtain ⟨a, b⟩ := ab
    have habp : (a, b) ∈ σp.edges := mem_removeLoggedRules_edges hab
    rcases hsh.classify (a, b) habp with h0e | hD
    · have hbunt : isDerived S (b.type, b.pred) = false := hσ0unt a b h0e
      exact Or.inl ((hmem0' a b).mpr ((hmemrem a b hbunt).mp hab))
    · exact Or.inr hD
  · -- sub
    intro ab hab
    obtain ⟨a, b⟩ := ab
    have hbunt : isDerived S (b.type, b.pred) = false := hσ0'unt a b hab
    exact (hmemrem a b hbunt).mpr ((hmem0' a b).mp hab)
  · -- nodesSub
    intro k hk
    rw [hnodes]
    obtain ⟨ab, hab, hor⟩ := reachedByRulesAdmitted_nodesFromEdges h0' k hk
    have habp : ab ∈ σp.edges := hsh.sub ab (hsub ab hab)
    obtain ⟨h1, h2⟩ := hsh.closed ab habp
    rcases hor with rfl | rfl
    · exact h1
    · exact h2
  · -- closed
    intro ab hab
    rw [hnodes]
    exact hsh.closed ab (mem_removeLoggedRules_edges hab)
  · -- closed0
    exact (reachedByRules_inv (reachedByRules_of_admitted h0')).1.edgesClosed
  · -- term
    intro k hk y hy
    exact hsh.term k hk y (mem_removeLoggedRules_edges hy)

/-- **`reachedByW3d2_shadow_d`** — the FILTERED-σ0 shadow on the Direct-arm fragment:
    every W3d-2 state over a `StoreValidRulesD` store is shadowed by a rules-admitted
    rebuild of the UNTAINTED-FILTER store `T↾U`. The naive full-store σ0 is FALSE here
    (header: a stored Direct-arm subject that is also excluded breaks `sub`) — dropping
    the derived-key seeds is exactly what keeps σ0 inside the drained σ.

    ADDED HYPOTHESES vs `reachedByW3d2_shadow`: `WF S` (a declared — hence derived —
    relation is never `BARE`: `lookup_rel_ne_bare`, since `BARE = "..."` violates
    `relNameOK`) and `BareStarStore T` (stored objects are concrete). Together they pin
    the derived-key seed's target as a `DerNode` (`isDerived ∧ R ≠ BARE ∧ on ≠ STAR`).
    Both are established fragment disciplines: the `remove` constructor already carries
    `BareStarStore` for its pre-store, and every settled-chain consumer carries `WF`. -/
theorem reachedByW3d2_shadow_d {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    NodupKeys S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOrDirect e) →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → DirectArmsBare e) →
    StoreValidRulesD S T →
    (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) →
    WF S →
    BareStarStore T →
    ∃ σ0, ReachedByRulesAdmitted σ0 S
            (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
          ∧ UntaintedShadow S σ σ0 := by
  induction h with
  | empty S =>
    intro _ _ _ _ _ _ _
    refine ⟨emptyState S, ReachedByRulesAdmitted.empty S, ?_, ?_, ?_, ?_, ?_, ?_⟩
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k hk; simp [emptyState] at hk
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k _ y hy; simp [emptyState] at hy
  | @write σp S T t hadm _ ih =>
    intro hNK hCO hDAB hSV hterm hWF hBS
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hDAB
      (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht'))
      (fun dt R hder => ⟨(hterm dt R hder).1,
        fun t' ht' => (hterm dt R hder).2 t' (List.mem_cons_of_mem _ ht')⟩)
      hWF
      (fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht'))
    by_cases hd : isDerived S (t.object.type, t.relation) = true
    · -- derived-key write: the filter drops `t`, σ0 is UNCHANGED; the one logged edge
      -- (seed-only closure) targets a `DerNode`
      have hfe : (t :: T).filter (fun tp => !isDerived S (tp.object.type, tp.relation))
          = T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)) := by
        rw [List.filter_cons, if_neg (by simp [hd])]
      rw [hfe]
      have hcl : rewriteClosure S t = [t] := rewriteClosure_derived_eq_seed_nk hNK hd
      have hbare : t.subject.predicate = BARE := by
        rcases hSV t List.mem_cons_self with ⟨hfalse, _⟩ | ⟨_, hbare, _⟩
        · rw [hd] at hfalse
          exact Bool.noConfusion hfalse
        · exact hbare
      have hRne : t.relation ≠ BARE := by
        obtain ⟨e, hlk⟩ := isDerived_declared hd
        exact lookup_rel_ne_bare hWF hlk
      have honS : t.object.name ≠ STAR := (hBS t List.mem_cons_self).2
      have hDer : DerNode S (objNode t.object t.relation) :=
        ⟨t.object.type, t.object.name, t.relation, hd, hRne, honS, rfl⟩
      have hnsubj : ¬ DerNode S (subjNode t.subject) := by
        rintro ⟨dt, on, R, _, hRne', _, heq⟩
        have hp := congrArg NodeKey.pred heq
        rw [subjNode_pred, objNode_pred, hbare] at hp
        exact hRne' hp.symm
      refine ⟨σ0, h0, ?_⟩
      have hone : σp.writeLoggedRules S t = σp.writeLoggedOne t := by
        unfold GraphState.writeLoggedRules
        rw [hcl]
        simp only [List.foldl_cons, List.foldl_nil]
      rw [hone]
      exact untaintedShadow_writeLoggedOne_derived hsh hDer hnsubj
    · -- untainted write: the filter keeps `t`; fold it into σ0 (the original route)
      rw [Bool.not_eq_true] at hd
      have hfe : (t :: T).filter (fun tp => !isDerived S (tp.object.type, tp.relation))
          = t :: T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)) := by
        rw [List.filter_cons, if_pos (by simp [hd])]
      rw [hfe]
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
  | @remove σp S T t hadm _ hSVT hBST _ htermT hprev ih =>
    intro hNK hCO hDAB _ _ hWF _
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hDAB
      (storeValidRulesD_of_storeValidRules_directArmsBare hSVT hDAB)
      htermT hWF hBST
    by_cases hd : isDerived S (t.object.type, t.relation) = true
    · -- derived-key erase: the filter never kept `t` — σ0 carries over unchanged
      have hfe : (T.erase t).filter (fun tp => !isDerived S (tp.object.type, tp.relation))
          = T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)) :=
        filter_erase_neg (by simp [hd]) T
      rw [hfe]
      refine ⟨σ0, h0, ?_⟩
      have h0e : ReachedByRulesAdmitted σ0 S
          ((T.erase t).filter (fun tp => !isDerived S (tp.object.type, tp.relation))) := by
        rw [hfe]
        exact h0
      exact untaintedShadow_removeLeg_d hNK hprev hsh h0 hadm h0e (fun e he => he)
    · -- untainted erase: erase commutes with the filter; rebuild via `exists_admitted_erase`
      rw [Bool.not_eq_true] at hd
      have hfe : (T.erase t).filter (fun tp => !isDerived S (tp.object.type, tp.relation))
          = (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))).erase t :=
        filter_erase_pos (by simp [hd]) T
      obtain ⟨σ0', h0', hsub⟩ := exists_admitted_erase h0 t
      rw [hfe]
      refine ⟨σ0', h0', ?_⟩
      have h0e : ReachedByRulesAdmitted σ0' S
          ((T.erase t).filter (fun tp => !isDerived S (tp.object.type, tp.relation))) := by
        rw [hfe]
        exact h0'
      exact untaintedShadow_removeLeg_d hNK hprev hsh h0 hadm h0e hsub
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro hNK hCO hDAB hSV hterm hWF hBS
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hDAB hSV hterm hWF hBS
    have hND : ∀ t' ∈ T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)),
        isDerived S (t'.object.type, t'.relation) = false := by
      intro t' ht'
      simpa using (List.mem_filter.mp ht').2
    exact ⟨σ0, h0,
      untaintedShadow_cascade2_d hsh
        (reachedByRulesAdmitted_untStore_edge_untainted hND h0) hjv1 hjv2⟩

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

/-- **The routed `cd` step bridge (Direct-arm leg 5, sub-step 1 cont.)** — the
    `ComputedOrDirect` + `DirectArmsBare` analog of `checkFnR_eq_semStep`, via
    `evalE_computedOrDirect`: on a derived key whose def is a boolean tree of `computed`
    refs and BARE `Direct` arms, the routed compiled guard coincides with one `sem` step
    given operand agreement on the `computed` leaves (the `.direct` arm rides for free,
    `directLeaf_bare_indep`). The routed foundation the W3d2 settled read bridge migrates
    onto under `StoreValidRulesD`. -/
theorem checkFnR_eq_semStep_cd {S : Schema} {σ : GraphState} {T : Store} {q : Query}
    {s : SubjectRef} {dt on R : String} {e : Expr} {f : Nat}
    (hlk : S.lookup (dt, R) = some e) (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hag : ∀ r' ∈ computedRefs e,
      GraphModel.graphRecR σ s dt on r' = semAux S s T q f dt on r') :
    σ.checkFnR T s dt on R e = semAux S s T q (f + 1) dt on R := by
  have hrhs : semAux S s T q (f + 1) dt on R
      = evalE (semAux S s T q f) s T q dt on R e := by
    simp only [semAux, step, hlk]
  rw [hrhs]
  unfold GraphState.checkFnR
  exact evalE_computedOrDirect e hcd hba hag

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
        exact graphRec_base_eq_bs hWF hTT hNK hR hSV hBS hTS hCO hMatch h0
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
          rw [checkFn_eq_sem_bs hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm
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

/-- **The stratum-staged read bridge, Direct-arm-widened (`checkFnR_eq_sem_settled_d`).** The
    `StoreValidRulesD` + `ComputedOrDirect`/`DirectArmsBare` analog of `checkFnR_eq_sem_settled`:
    the CURRENT derived def `e` may carry BARE `Direct` arms (its operands stay `ComputedOnly`,
    lower stratum). The untainted operand read routes through the widened base equation
    (`graphRec_base_eq_bs_d`), the derived operand read reuses the settled `stars`-row read with
    the widened linchpin (`coveredFn_declared_d`/`checkFn_eq_sem_bs_d` at the `ComputedOnly`
    operand def), and the `Direct` arm of `e` rides `checkFnR_eq_semStep_cd`. -/
theorem checkFnR_eq_sem_settled_d {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRulesD S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (hσS : σ.schema = S)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hLU2 : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges))
    (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    σ.checkFnR T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hDecl : StoreDeclared S T := storeDeclared_of_validRulesD hSV
  have hag : ∀ r' ∈ computedRefs e,
      GraphModel.graphRecR σ s dt on r'
        = semAux S s T ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r' := by
    intro r' hr'
    have hstep : GraphModel.graphRecR σ s dt on r' = sem S T ⟨s, r', ⟨dt, on⟩⟩ := by
      cases hd' : isDerived S (dt, r') with
      | false =>
        rw [GraphModel.graphRecR_eq_graphRec s on (by rw [hσS]; exact hd'),
          shadow_graphRec_agree hsh s on hd']
        exact graphRec_base_eq_bs_d hWF hTT hNK hR hSV hBS hTS hMatch hterm h0 hs hon r' hd'
      | true =>
        obtain ⟨hset', hcomp', hcollapse'⟩ := hops r' hr' hd'
        obtain ⟨e', hlk'⟩ := isDerived_declared hd'
        have hleafUnt' : ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false :=
          hLU2 r' hr' hd' e' hlk'
        have hco' : ComputedOnly e' := hCO dt r' e' hlk' hd'
        have hsem_ws' : ∀ sh : Shape, sh.2 = BARE →
            sem S T ⟨starSubj sh, r', ⟨dt, on⟩⟩ = true → sh ∈ wildcardShapes S := by
          intro sh hshb hsm
          refine coveredFn_declared_d hTT hSV hTS h0 hlk'
            (computedOnly_computedOrDirect hco') (computedOnly_directArmsBare hco')
            (dt := dt) (on := on) (R := r') ?_
          show σ0.checkFn T (starSubj sh) dt on r' e' = true
          rw [checkFn_eq_sem_bs_d hWF hTT hNK hR hSV hBS hTS hMatch hStrat hterm
            (ReachedByW3aAdmitted.base h0) hlk' (computedOnly_computedOrDirect hco')
            (computedOnly_directArmsBare hco') hleafUnt' (fun _ => hshb) hon]
          exact hsm
        show GraphModel.check σ ⟨s, r', ⟨dt, on⟩⟩ = sem S T ⟨s, r', ⟨dt, on⟩⟩
        rw [GraphModel.check_derived σ ⟨s, r', ⟨dt, on⟩⟩ (by rw [hσS]; exact hd')]
        exact probeDerived_eq_sem_settled hWSbare hsh.closed hcollapse' hsem_ws'
          hset' hcomp' hs hon
    rw [hstep]
    exact semAux_qirrel S s T ⟨s, r', ⟨dt, on⟩⟩ ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r'
  rw [checkFnR_eq_semStep_cd hlk hcd hba hag]
  exact sem_fuel_stable S T ⟨s, R, ⟨dt, on⟩⟩ hStrat hDecl (fuelBound S T + 1)
    (Nat.le_succ _)

/-! ## The FILTERED-σ0 read bridge (Direct-arm leg 5d cont.)

`checkFnR_eq_sem_settled_d` takes a FULL-store base pair (`h0` over `T` + the shadow) —
jointly unsatisfiable on the widened fragment (the `reachedByW3d2_shadow_d` header's kill:
a stored-and-excluded Direct-arm seed is in the full-`T` σ0 but retracted from the drained
σ). The filtered shadow instead produces `h0 : ReachedByRulesAdmitted σ0 S (T↾U)` where
`T↾U := T.filter (fun tp => !isDerived S …)`. The `_filt` variants below consume exactly
that pair and conclude the SAME full-store `= sem S T`: untainted operand reads land at
`sem S (T↾U)` and bridge back on design lemma C (`sem_untaintedFilter`); the derived
operand's no-ghost star coverage routes the leg-5b/5c linchpins AT `T↾U` and converts the
full-store `sem` premise with the derived-key filter bridge `sem_untaintedFilter_co`.
Attack-first (2026-07-20, scratch deleted): (1) `coveredFn`'s store argument is fully
irrelevant on a `ComputedOnly` def (general proof via `checkFn_store_irrel` compiled) —
the `T↾U` phrasing loses nothing; (2) `sem_untaintedFilter_co`'s statement survived an
`#eval` grid over stored derived-key tuples (bare subject, userset subject, and the
exclusion kill shape) — stored derived-key tuples are `sem`-invisible through a
`ComputedOnly` def with untainted refs. -/

/-- **The derived-key `sem` filter bridge (`sem_untaintedFilter_co`).** `sem` at a DERIVED
    key whose def is `ComputedOnly` with UNTAINTED `computed` refs is invariant under the
    untainted store filter: the top step never reads the store (`evalE_computedOnly`), and
    each operand read is store-filter-invariant by design lemma C (`sem_untaintedFilter`).
    This is what lets a full-store `sem` fact at a derived OPERAND key be read over `T↾U`. -/
theorem sem_untaintedFilter_co {S : Schema} {T : Store}
    (hNK : NodupKeys S) (hDecl : StoreDeclared S T) (hNUS : NoUsersetStar T)
    (hTS : TtuStarFree S T) (hStrat : Stratifiable S)
    {s : SubjectRef} {dt on r' : String} {e' : Expr}
    (hlk' : S.lookup (dt, r') = some e') (hco' : ComputedOnly e')
    (hleafUnt' : ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false) :
    sem S T ⟨s, r', ⟨dt, on⟩⟩
      = sem S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
          ⟨s, r', ⟨dt, on⟩⟩ := by
  have hDeclU : StoreDeclared S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    fun t ht => hDecl t (List.mem_filter.mp ht).1
  have hag : ∀ r'' ∈ computedRefs e',
      semAux S s T ⟨s, r', ⟨dt, on⟩⟩ (fuelBound S T) dt on r''
        = semAux S s (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
            ⟨s, r', ⟨dt, on⟩⟩
            (fuelBound S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
            dt on r'' := by
    intro r'' hr''
    have h1 : semAux S s T ⟨s, r', ⟨dt, on⟩⟩ (fuelBound S T) dt on r''
        = sem S T ⟨s, r'', ⟨dt, on⟩⟩ :=
      semAux_qirrel S s T ⟨s, r', ⟨dt, on⟩⟩ ⟨s, r'', ⟨dt, on⟩⟩ (fuelBound S T) dt on r''
    have h2 : semAux S s (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
          ⟨s, r', ⟨dt, on⟩⟩
          (fuelBound S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
          dt on r''
        = sem S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
            ⟨s, r'', ⟨dt, on⟩⟩ :=
      semAux_qirrel S s _ ⟨s, r', ⟨dt, on⟩⟩ ⟨s, r'', ⟨dt, on⟩⟩ _ dt on r''
    rw [h1, h2]
    exact sem_untaintedFilter hNK hDecl hNUS hTS ⟨s, r'', ⟨dt, on⟩⟩ (hleafUnt' r'' hr'')
  calc sem S T ⟨s, r', ⟨dt, on⟩⟩
      = semAux S s T ⟨s, r', ⟨dt, on⟩⟩ (fuelBound S T + 1) dt on r' :=
        (sem_fuel_stable S T ⟨s, r', ⟨dt, on⟩⟩ hStrat hDecl (fuelBound S T + 1)
          (Nat.le_succ _)).symm
    _ = evalE (semAux S s T ⟨s, r', ⟨dt, on⟩⟩ (fuelBound S T)) s T ⟨s, r', ⟨dt, on⟩⟩
          dt on r' e' := by
        simp only [semAux, step, hlk']
    _ = evalE (semAux S s (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
            ⟨s, r', ⟨dt, on⟩⟩
            (fuelBound S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))))
          s (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
          ⟨s, r', ⟨dt, on⟩⟩ dt on r' e' :=
        evalE_computedOnly e' hco' hag
    _ = semAux S s (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
          ⟨s, r', ⟨dt, on⟩⟩
          (fuelBound S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) + 1)
          dt on r' := by
        simp only [semAux, step, hlk']
    _ = sem S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
          ⟨s, r', ⟨dt, on⟩⟩ :=
        sem_fuel_stable S _ ⟨s, r', ⟨dt, on⟩⟩ hStrat hDeclU _ (Nat.le_succ _)

/-- **The stratum-staged read bridge over the FILTERED shadow
    (`checkFnR_eq_sem_settled_d_filt`).** `checkFnR_eq_sem_settled_d` with the base witness
    σ0 admitted over `T↾U` — the pair `reachedByW3d2_shadow_d` actually produces. Same
    conclusion: the routed guard at the REAL drained state σ equals `sem` over the FULL
    store `T`. The audited full-store version stays in place, untouched.

    2026-07-20d: the operand-def `ComputedOnly` hypothesis is now PER-KEY
    (`hCOop`, exactly the uses in the body) — the former schema-wide `hCO` covered the
    ROOT def too and was thus unsatisfiable on any genuine Direct-arm schema. -/
theorem checkFnR_eq_sem_settled_d_filt {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRulesD S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h0 : ReachedByRulesAdmitted σ0 S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh : UntaintedShadow S σ σ0)
    (hσS : σ.schema = S)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hCOop : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' → ComputedOnly e')
    (hLU2 : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges))
    (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    σ.checkFnR T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hDecl : StoreDeclared S T := storeDeclared_of_validRulesD hSV
  -- the `T↾U` hypothesis pack
  have hSVU : StoreValidRules S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    storeValidRules_untaintedFilter hSV
  have hStoreUntU : ∀ t ∈ T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)),
      isDerived S (t.object.type, t.relation) = false := by
    intro t ht
    simpa using (List.mem_filter.mp ht).2
  have hSVU_D : StoreValidRulesD S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    fun t ht => Or.inl ⟨hStoreUntU t ht, hSVU t ht⟩
  have hBSU : BareStarStore (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    fun t ht => hBS t (List.mem_filter.mp ht).1
  have hTSU : TtuStarFree S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    fun t ht => hTS t (List.mem_filter.mp ht).1
  have htermU : ∀ dt' R', isDerived S (dt', R') = true → NoTtuTarget S R' ∧
      NoStoreSubjectR (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) R' :=
    fun dt' R' hd => ⟨(hterm dt' R' hd).1,
      fun t ht => (hterm dt' R' hd).2 t (List.mem_filter.mp ht).1⟩
  have hag : ∀ r' ∈ computedRefs e,
      GraphModel.graphRecR σ s dt on r'
        = semAux S s T ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r' := by
    intro r' hr'
    have hstep : GraphModel.graphRecR σ s dt on r' = sem S T ⟨s, r', ⟨dt, on⟩⟩ := by
      cases hd' : isDerived S (dt, r') with
      | false =>
        rw [GraphModel.graphRecR_eq_graphRec s on (by rw [hσS]; exact hd'),
          shadow_graphRec_agree hsh s on hd',
          graphRec_base_eq_bs_unt hWF hTT hNK hR hSVU hBSU hTSU hStoreUntU hMatch h0
            hs hon r' hd']
        exact (sem_untaintedFilter hNK hDecl hBS.noUsersetStar hTS ⟨s, r', ⟨dt, on⟩⟩ hd').symm
      | true =>
        obtain ⟨hset', hcomp', hcollapse'⟩ := hops r' hr' hd'
        obtain ⟨e', hlk'⟩ := isDerived_declared hd'
        have hleafUnt' : ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false :=
          hLU2 r' hr' hd' e' hlk'
        have hco' : ComputedOnly e' := hCOop r' hr' hd' e' hlk'
        have hsem_ws' : ∀ sh : Shape, sh.2 = BARE →
            sem S T ⟨starSubj sh, r', ⟨dt, on⟩⟩ = true → sh ∈ wildcardShapes S := by
          intro sh hshb hsm
          refine coveredFn_declared_d hTT hSVU_D hTSU h0 hlk'
            (computedOnly_computedOrDirect hco') (computedOnly_directArmsBare hco')
            (dt := dt) (on := on) (R := r') ?_
          show σ0.checkFn (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
            (starSubj sh) dt on r' e' = true
          rw [checkFn_eq_sem_bs_d hWF hTT hNK hR hSVU_D hBSU hTSU hMatch hStrat htermU
            (ReachedByW3aAdmitted.base h0) hlk' (computedOnly_computedOrDirect hco')
            (computedOnly_directArmsBare hco') hleafUnt' (fun _ => hshb) hon,
            ← sem_untaintedFilter_co hNK hDecl hBS.noUsersetStar hTS hStrat hlk' hco'
              hleafUnt']
          exact hsm
        show GraphModel.check σ ⟨s, r', ⟨dt, on⟩⟩ = sem S T ⟨s, r', ⟨dt, on⟩⟩
        rw [GraphModel.check_derived σ ⟨s, r', ⟨dt, on⟩⟩ (by rw [hσS]; exact hd')]
        exact probeDerived_eq_sem_settled hWSbare hsh.closed hcollapse' hsem_ws'
          hset' hcomp' hs hon
    rw [hstep]
    exact semAux_qirrel S s T ⟨s, r', ⟨dt, on⟩⟩ ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r'
  rw [checkFnR_eq_semStep_cd hlk hcd hba hag]
  exact sem_fuel_stable S T ⟨s, R, ⟨dt, on⟩⟩ hStrat hDecl (fuelBound S T + 1)
    (Nat.le_succ _)

/-! ## The routed transport layer — untargeted keys keep their representation

Mirrors of the W3d-1 `applyD_other_key_fixed` / `reconcileJobsD_other_key_fixed`
over the ROUTED LOGGED pass (the emission row is residue/edge-inert), plus the
batch-level `SettledKey`/`CompleteKey` transports the stratum-staged settledness
induction consumes PER ROUND (round 1 and round 2 are separate `reconcileJobsLR`
batches around a mid state). -/

/-- The concatenated two-round batch is one batch (`List.foldl_append`). -/
theorem reconcileJobsLR_append (S : Schema) (T : Store) (σ : GraphState)
    (jobs1 jobs2 : List W3cJob) :
    reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2
      = reconcileJobsLR S T σ (jobs1 ++ jobs2) := by
  unfold reconcileJobsLR
  rw [List.foldl_append]

/-- The advanced cursor never exceeds `max maxOutboxId n` — emissions land above it. -/
theorem GraphState.frontierMax_le (σ : GraphState) (n : Nat) :
    σ.frontierMax n ≤ max σ.maxOutboxId n := by
  unfold GraphState.frontierMax
  have H : ∀ (l : List Delta) (a : Nat), (∀ d ∈ l, d.id ≤ σ.maxOutboxId) →
      a ≤ max σ.maxOutboxId n →
      l.foldl (fun m d => max m d.id) a ≤ max σ.maxOutboxId n := by
    intro l
    induction l with
    | nil => intro a _ ha; exact ha
    | cons d rest ih =>
      intro a hmem ha
      refine ih (max a d.id) (fun d' hd' => hmem d' (List.mem_cons_of_mem _ hd')) ?_
      have hd := hmem d List.mem_cons_self
      omega
  refine H _ n ?_ (Nat.le_max_right _ _)
  intro d hd
  exact mem_outbox_le_maxOutboxId σ d
    (List.mem_filter.mp hd).1

/-- One routed logged pass touches no residue row and no in-edge at ANOTHER
    concrete key (mirror of `applyD_other_key_fixed`). -/
theorem applyLoggedR_other_key_fixed {S : Schema} {T : Store} {σ : GraphState}
    {j : W3cJob} (hjv : W3cJobValid S j) {dt on R : String} (hon : on ≠ STAR)
    (hnot : ¬ j.keyMatch dt on R) :
    (j.applyLoggedR S T σ).residue (objNode ⟨dt, on⟩ R) R
        = σ.residue (objNode ⟨dt, on⟩ R) R ∧
    ∀ u : NodeKey, ((u, objNode ⟨dt, on⟩ R) ∈ (j.applyLoggedR S T σ).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  obtain ⟨_, _, _, _, _, _, _, _, honj⟩ := hjv
  have hne_node : objNode ⟨dt, on⟩ R ≠ objNode ⟨j.dt, j.on⟩ j.R := by
    intro heq
    obtain ⟨h1, h2, h3⟩ := objNode_inj_of_ne_star hon honj heq
    exact hnot ⟨h1.symm, h2.symm, h3.symm⟩
  have hres : (j.applyLoggedR S T σ).residue = (j.applyDR S T σ).residue := by
    unfold W3cJob.applyLoggedR
    rw [pushDelta_residue]
  have hedges : (j.applyLoggedR S T σ).edges = (j.applyDR S T σ).edges := by
    unfold W3cJob.applyLoggedR
    rw [pushDelta_edges]
  constructor
  · rw [hres]
    show (σ.reconcileStarsKeyDR T j.dt j.on j.R j.e (wildcardShapes S) j.cands
      j.negCands j.uposCands).residue (objNode ⟨dt, on⟩ R) R = _
    exact reconcileStarsKeyDR_residue_other (fun h => hne_node h.1)
  · intro u
    rw [hedges]
    constructor
    · intro h
      unfold W3cJob.applyDR at h
      rcases reconcileStarsKeyDR_edge_sound T j.dt j.on j.R j.e (wildcardShapes S)
        j.cands j.negCands j.uposCands σ u _ h with hold | ⟨c, _, _, h2⟩
      · exact hold
      · exact absurd h2 hne_node
    · intro h
      unfold W3cJob.applyDR GraphState.reconcileStarsKeyDR
      refine reconcileKeyDR_edge_pres_target T j.dt j.on j.R j.e j.cands _
        (u, objNode ⟨dt, on⟩ R) hne_node ?_
      rw [reconcileResidueKeyR_edges]
      exact h

/-- A whole routed logged batch leaves an untargeted concrete key's row and
    in-edges untouched. -/
theorem reconcileJobsLR_other_key_fixed {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState) {dt on R : String}, on ≠ STAR →
      (∀ j ∈ jobs, W3cJobValid S j) → (∀ j ∈ jobs, ¬ j.keyMatch dt on R) →
      (reconcileJobsLR S T σ jobs).residue (objNode ⟨dt, on⟩ R) R
          = σ.residue (objNode ⟨dt, on⟩ R) R ∧
      ∀ u : NodeKey, ((u, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T σ jobs).edges
        ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  intro jobs
  induction jobs with
  | nil => intro σ dt on R _ _ _; exact ⟨rfl, fun u => Iff.rfl⟩
  | cons j rest ih =>
    intro σ dt on R hon hjv hnot
    have hfold : reconcileJobsLR S T σ (j :: rest)
        = reconcileJobsLR S T (j.applyLoggedR S T σ) rest := by
      unfold reconcileJobsLR
      rw [List.foldl_cons]
    rw [hfold]
    obtain ⟨hres1, hedge1⟩ := applyLoggedR_other_key_fixed (hjv j List.mem_cons_self)
      hon (hnot j List.mem_cons_self)
    obtain ⟨hres2, hedge2⟩ := ih (j.applyLoggedR S T σ) hon
      (fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj'))
      (fun j' hj' => hnot j' (List.mem_cons_of_mem _ hj'))
    exact ⟨hres2.trans hres1, fun u => (hedge2 u).trans (hedge1 u)⟩

/-- `SettledKey` is untouched by a routed batch at untargeted keys (store fixed —
    the per-ROUND transport). -/
theorem settledKey_jobsLR_untargeted {S : Schema} {T : Store} {σ : GraphState}
    {jobs : List W3cJob} {dt on R : String}
    (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (hnot : ∀ j ∈ jobs, ¬ j.keyMatch dt on R) (hon : on ≠ STAR)
    (hset : SettledKey S T σ dt on R) :
    SettledKey S T (reconcileJobsLR S T σ jobs) dt on R := by
  obtain ⟨hrow, hedge⟩ := hset
  obtain ⟨hres, hedges⟩ := reconcileJobsLR_other_key_fixed jobs σ hon hjv hnot
  constructor
  · intro res hresrow
    refine hrow res ?_
    rw [← hres]
    exact hresrow
  · intro s hb hstar hedge'
    refine hedge s hb hstar ?_
    rw [← hedges (subjNode s)]
    exact hedge'

/-- `CompleteKey` is untouched by a routed batch at untargeted keys (store fixed). -/
theorem completeKey_jobsLR_untargeted {S : Schema} {T : Store} {σ : GraphState}
    {jobs : List W3cJob} {dt on R : String}
    (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (hnot : ∀ j ∈ jobs, ¬ j.keyMatch dt on R) (hon : on ≠ STAR)
    (hcomp : CompleteKey S T σ dt on R) :
    CompleteKey S T (reconcileJobsLR S T σ jobs) dt on R := by
  obtain ⟨hrowE, hedgeC, huposC, hnegC⟩ := hcomp
  obtain ⟨hres, hedges⟩ := reconcileJobsLR_other_key_fixed jobs σ hon hjv hnot
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro sh hws hsm
    rw [hres]
    exact hrowE sh hws hsm
  · intro s hb hstar hsm hnc
    exact (hedges (subjNode s)).mpr (hedgeC s hb hstar hsm hnc)
  · intro s hu hstar hsm
    rw [hres]
    exact huposC s hu hstar hsm
  · intro s hstar hws hsemStar hsemF
    rw [hres]
    exact hnegC s hstar hws hsemStar hsemF

/-! ## Round-2 scope reads a derived operand — the stratum fence

The (A)-half of `runCascade2_no_abort`'s analysis, factored: a key in round-2 scope
was dirtied by a round-1 emission at a derived R-node, so its def READS a derived
pred as a computed operand. Consequences the settledness induction uses: a round-2
job never targets a stratum-1 key (whose def has no derived operand), so round 2 is
inert at every stratum-1 key settled by round 1. -/

/-- **A key in round-2 scope reads a derived operand.** The dirtying row is a
    round-1 emission at a valid job's terminal derived R-node (cursor arithmetic +
    outbox soundness); its only candidate object is that R-node (terminality), and
    the `affectedKeys` condition puts the emitter's derived pred among the reader's
    `computedRefs`. -/
theorem round2_key_reads_derived {σ : GraphState} {S : Schema} {T : Store}
    {jobs1 : List W3cJob} {dt' R' on' : String} {e' : Expr}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hjv1 : ∀ j ∈ jobs1, W3cJobValid S j)
    (h : ReachedByW3d2 σ S T)
    (hlk' : S.lookup (dt', R') = some e')
    (hjk : (dt', R', on') ∈ cascadeKeysAbove S (reconcileJobsLR S T σ jobs1)
      (σ.frontierMax σ.watermark)) :
    ∃ r', r' ∈ computedRefs e' ∧ isDerived S (dt', r') = true := by
  unfold cascadeKeysAbove at hjk
  obtain ⟨d', hd'raw, hjk'⟩ := List.mem_flatMap.mp hjk
  unfold GraphState.frontierRowsAbove at hd'raw
  obtain ⟨hd'mem, hd'gt'⟩ := List.mem_filter.mp hd'raw
  have hd'gt : σ.frontierMax σ.watermark < d'.id := of_decide_eq_true hd'gt'
  -- the dirtying row is a round-1 emission (original rows sit at or below the cursor)
  rcases reconcileJobsLR_outbox_sound S T jobs1 σ d' hd'mem
    with hin' | ⟨⟨j1, hj1, hnode1, _, hd'leaf⟩, _⟩
  · exfalso
    have := σ.outbox_le_frontierMax σ.watermark d' hin'
    omega
  obtain ⟨hRne1, _, _, _, _, _, hder1, _, _⟩ := hjv1 j1 hj1
  -- terminality collapses the row's candidate objects to its own R-node
  have hbase1 := reachedByW3d2_Rnode_not_source (on := j1.on) hterm hRne1 hder1 h
  have hmidT1 := reconcileJobsLR_Rnode_not_source (T := T) (jobs := jobs1)
    hRne1 hjv1 hbase1
  have hreach1 : ∀ v, (reconcileJobsLR S T σ jobs1).reach d'.node v = false := by
    intro v
    by_contra hne
    have htrue : (reconcileJobsLR S T σ jobs1).reach d'.node v = true := by
      revert hne
      cases (reconcileJobsLR S T σ jobs1).reach d'.node v <;> simp
    obtain ⟨y, hy⟩ := nreaches_first_edge (reach_sound htrue)
    rw [hnode1] at hy
    exact hmidT1 y hy
  have hobj1 : (reconcileJobsLR S T σ jobs1).affectedObjects d' = [d'.node] := by
    unfold GraphState.affectedObjects
    rw [List.filter_eq_nil_iff.mpr (fun v _ => by rw [hreach1 v]; exact Bool.false_ne_true)]
  unfold affectedKeys at hjk'
  rw [if_neg (by rw [hd'leaf]; simp), List.nil_append] at hjk'
  obtain ⟨v, hv, hvk⟩ := List.mem_flatMap.mp hjk'
  rw [hobj1] at hv
  have hveq : v = d'.node := List.mem_singleton.mp hv
  subst hveq
  by_cases hst1 : d'.node.name = STAR
  · rw [if_pos hst1] at hvk
    simp at hvk
  rw [if_neg hst1] at hvk
  obtain ⟨k', hk'mem, hopt'⟩ := List.mem_filterMap.mp hvk
  have hcond' : k'.1 = d'.node.type ∧ isDerived S k' = true ∧
      ((S.lookup k').map (fun e => (computedRefs e).contains d'.node.pred)).getD false
        = true := by
    by_contra hnc
    rw [if_neg hnc] at hopt'
    simp at hopt'
  rw [if_pos hcond'] at hopt'
  obtain ⟨hc1, _, hc3⟩ := hcond'
  have hkeq := Option.some.inj hopt'
  have h1' : k'.1 = dt' := congrArg (fun p => p.1) hkeq
  have h2' : k'.2 = R' := congrArg (fun p => p.2.1) hkeq
  have hk'eq : k' = (dt', R') := by rw [← h1', ← h2']
  have hpred1 : d'.node.pred = j1.R := by rw [hnode1, objNode_pred]
  have htype1 : d'.node.type = j1.dt := by rw [hnode1, objNode_type]
  rw [hk'eq, hlk'] at hc3
  simp only [Option.map_some, Option.getD_some] at hc3
  rw [List.contains_eq_mem] at hc3
  refine ⟨j1.R, of_decide_eq_true (by rw [← hpred1]; exact hc3), ?_⟩
  have hdt : dt' = j1.dt := by rw [← h1', hc1, htype1]
  rw [hdt]
  exact hder1

/-! ## The write-leg layer — unmapped keys keep meaning, at BOTH strata

A logged write leg cannot touch any derived key's representation (rows write-inert,
I5 in-edge exclusivity). The semantic complement now comes in two shapes:

* **stratum 1** (`writeLeg_sem_stable_sh`): the chain-agnostic restatement of
  W3d-1's `writeLeg_sem_stable` — shadows and structural facts as direct
  hypotheses, so the two-round chain (whose states are not `ReachedByW3d`) can
  instantiate it.
* **stratum 2** (`writeLeg_sem_stable2`): `sem` at a derived-reading key routes
  through the ROUTED guard — the stratum-staged bridge at both ends of the leg
  (operand keys' settledness transported across the leg by the stratum-1 half),
  the routed guard itself stable (`writeLeg_checkFnR_stable`: untainted leaves by
  fan-out completeness, derived leaves by the I5 in-edge fixity + the reach
  collapse on both sides), and store-irrelevance in the middle. -/

/-- The derived read at an operand key is stable across a write leg: the residue is
    write-inert, and reach into the R-node is single-edge on both sides (collapse)
    with the in-edge set fixed (I5). -/
theorem writeLeg_probeDerived_stable {σ : GraphState} {S : Schema} {T : Store}
    {t : Tuple}
    (hNK : NodupKeys S) (hSV : StoreValidRules S (t :: T))
    {dt on r' : String} {e' : Expr}
    (hlk' : S.lookup (dt, r') = some e') (hder' : isDerived S (dt, r') = true)
    (hco' : ComputedOnly e')
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (hclσ' : ∀ ab ∈ (σ.writeLoggedRules S t).edges,
      ab.1 ∈ (σ.writeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.writeLoggedRules S t).nodes)
    (hcol : ∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
      (u, objNode ⟨dt, on⟩ r') ∈ σ.edges)
    (hcol' : ∀ u, NReaches (σ.writeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
      (u, objNode ⟨dt, on⟩ r') ∈ (σ.writeLoggedRules S t).edges)
    {st sn sp : String} (hon : on ≠ STAR) :
    GraphModel.probeDerived (σ.writeLoggedRules S t) ⟨⟨st, sn, sp⟩, r', ⟨dt, on⟩⟩
      = GraphModel.probeDerived σ ⟨⟨st, sn, sp⟩, r', ⟨dt, on⟩⟩ := by
  have hres : (σ.writeLoggedRules S t).residue = σ.residue :=
    writeLoggedRules_residue σ S t
  have hreach : ∀ x : NodeKey, (σ.writeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
      = σ.reach x (objNode ⟨dt, on⟩ r') := by
    intro x
    cases h1 : (σ.writeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
      <;> cases h0 : σ.reach x (objNode ⟨dt, on⟩ r')
    · rfl
    · exfalso
      have hedge := hcol x (reach_sound h0)
      have hedge' := (writeLeg_derived_inedges_eq hSV hlk' hder' hco' x).mpr hedge
      have := reach_complete hclσ' (NReaches.edge hedge')
      rw [h1] at this
      cases this
    · exfalso
      have hedge' := hcol' x (reach_sound h1)
      have hedge := (writeLeg_derived_inedges_eq hSV hlk' hder' hco' x).mp hedge'
      have := reach_complete hclσ (NReaches.edge hedge)
      rw [h0] at this
      cases this
    · rfl
  rw [probeDerived_eq _ hon, probeDerived_eq σ hon, hres,
    hreach (subjNode ⟨st, sn, sp⟩)]

/-- **The routed guard is stable across an unmapped write leg** — untainted leaves
    by fan-out completeness (`writeLeg_graphRec_stable`), derived leaves by the
    write-inert derived read (`writeLeg_probeDerived_stable`). -/
theorem writeLeg_checkFnR_stable {σ : GraphState} {S : Schema} {T : Store}
    {t : Tuple} (T' : Store)
    (hNK : NodupKeys S) (hSV : StoreValidRules S (t :: T))
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hσS : σ.schema = S)
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant = Variant.plain)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hcolOps : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) ∧
      (∀ u, NReaches (σ.writeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.writeLoggedRules S t).edges))
    (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (s : SubjectRef) :
    (σ.writeLoggedRules S t).checkFnR T' s dt on R e = σ.checkFnR T' s dt on R e := by
  have hσ'S : (σ.writeLoggedRules S t).schema = S := by
    rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).schema, writeRules_schema, hσS]
  have hclσ' : ∀ ab ∈ (σ.writeLoggedRules S t).edges,
      ab.1 ∈ (σ.writeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.writeLoggedRules S t).nodes := by
    have hev := writeLoggedRules_evalEq (EvalEq.refl σ) S t
    intro ab hab
    rw [hev.edges] at hab
    rw [hev.nodes]
    exact edgesClosed_foldl_writeDirect (rewriteClosure S t) σ hclσ ab hab
  unfold GraphState.checkFnR
  refine evalE_computedOnly e hco ?_
  intro r' hr'
  cases hd' : isDerived S (dt, r') with
  | false =>
    rw [GraphModel.graphRecR_eq_graphRec s on (by rw [hσ'S]; exact hd'),
      GraphModel.graphRecR_eq_graphRec s on (by rw [hσS]; exact hd')]
    exact writeLeg_graphRec_stable hclσ htp' hlk hder hr' hon hunmapped s
  | true =>
    obtain ⟨e', hlk'⟩ := isDerived_declared hd'
    have hco' : ComputedOnly e' := hCO dt r' e' hlk' hd'
    obtain ⟨hcol, hcol'⟩ := hcolOps r' hr' hd'
    show GraphModel.check (σ.writeLoggedRules S t) ⟨s, r', ⟨dt, on⟩⟩
        = GraphModel.check σ ⟨s, r', ⟨dt, on⟩⟩
    rw [GraphModel.check_derived _ ⟨s, r', ⟨dt, on⟩⟩ (by rw [hσ'S]; exact hd'),
      GraphModel.check_derived σ ⟨s, r', ⟨dt, on⟩⟩ (by rw [hσS]; exact hd')]
    obtain ⟨st, sn, sp⟩ := s
    exact writeLeg_probeDerived_stable hNK hSV hlk' hd' hco' hclσ hclσ' hcol hcol' hon

/-- **Stratum-1 `sem` stability, chain-agnostic** (`writeLeg_sem_stable` with the
    shadows and structural facts as direct hypotheses — the two-round chain's
    states instantiate it through `reachedByW3d2_shadow` etc.). -/
theorem writeLeg_sem_stable_sh {σ σ0 σ0' : GraphState} {S : Schema} {T : Store}
    {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S (t :: T)) (hBS : BareStarStore (t :: T))
    (hTS : TtuStarFree S (t :: T))
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (t :: T) R)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (h0' : ReachedByRulesAdmitted σ0' S (t :: T))
    (hsh' : UntaintedShadow S (σ.writeLoggedRules S t) σ0')
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant = Variant.plain)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    {s : SubjectRef} (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hSVw : StoreValidRules S T := fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')
  have hBSw : BareStarStore T := fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')
  have hTSw : TtuStarFree S T := fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht')
  have htermw : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR T R :=
    fun dt R hd => ⟨(hterm dt R hd).1,
      fun t' ht' => (hterm dt R hd).2 t' (List.mem_cons_of_mem _ ht')⟩
  calc sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩
      = (σ.writeLoggedRules S t).checkFn (t :: T) s dt on R e :=
        (checkFn_eq_sem_w3d hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm
          h0' hsh' hlk hco hleafUnt hs hon).symm
    _ = σ.checkFn (t :: T) s dt on R e :=
        writeLeg_checkFn_stable (t :: T) hclσ htp' hlk hder hco hon hunmapped s
    _ = σ.checkFn T s dt on R e := checkFn_store_irrel _ _ s dt on R hco
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3d hWF hTT hNK hR hSVw hBSw hTSw hCO hMatch hStrat htermw
          h0 hsh hlk hco hleafUnt hs hon

/-- **`SettledKey` transports across a write leg given `sem` stability** — the
    representation is untouched (rows write-inert, derived in-edges fixed); the
    meaning hypothesis `hsem` is supplied per stratum. -/
theorem settledKey_writeLeg_sem {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hNK : NodupKeys S) (hSV : StoreValidRules S (t :: T))
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hsem : ∀ s : SubjectRef, (s.name = STAR → s.predicate = BARE) →
      sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩)
    (hset : SettledKey S T σ dt on R) :
    SettledKey S (t :: T) (σ.writeLoggedRules S t) dt on R := by
  obtain ⟨hrow, hedge⟩ := hset
  constructor
  · intro res hres
    rw [writeLoggedRules_residue] at hres
    obtain ⟨h1, h2, h3⟩ := hrow res hres
    refine ⟨?_, ?_, ?_⟩
    · intro sh
      rw [h1 sh]
      constructor
      · rintro ⟨hws, hsm⟩
        refine ⟨hws, ?_⟩
        rw [hsem (starSubj sh) (fun _ => hWSbare sh hws)]
        exact hsm
      · rintro ⟨hws, hsm⟩
        refine ⟨hws, ?_⟩
        rw [← hsem (starSubj sh) (fun _ => hWSbare sh hws)]
        exact hsm
    · intro n hn
      obtain ⟨hnstar, hsm⟩ := h2 n hn
      refine ⟨hnstar, ?_⟩
      rw [hsem n (fun hx => absurd hx hnstar)]
      exact hsm
    · intro n hn
      obtain ⟨hnp, hnstar, hsm⟩ := h3 n hn
      refine ⟨hnp, hnstar, ?_⟩
      rw [hsem n (fun hx => absurd hx hnstar)]
      exact hsm
  · intro s hb hstar hedge'
    rw [writeLeg_derived_inedges_eq hSV hlk hder (hCO dt R e hlk hder) (subjNode s)] at hedge'
    rw [hsem s (fun hx => absurd hx hstar)]
    exact hedge s hb hstar hedge'

/-- **`CompleteKey` transports across a write leg given `sem` stability.** -/
theorem completeKey_writeLeg_sem {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hNK : NodupKeys S) (hSV : StoreValidRules S (t :: T))
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hsem : ∀ s : SubjectRef, (s.name = STAR → s.predicate = BARE) →
      sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩)
    (hcomp : CompleteKey S T σ dt on R) :
    CompleteKey S (t :: T) (σ.writeLoggedRules S t) dt on R := by
  obtain ⟨hrowE, hedgeC, huposC, hnegC⟩ := hcomp
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro sh hws hsm
    rw [writeLoggedRules_residue]
    refine hrowE sh hws ?_
    rw [← hsem (starSubj sh) (fun _ => hWSbare sh hws)]
    exact hsm
  · intro s hb hstar hsm hnc
    rw [writeLeg_derived_inedges_eq hSV hlk hder (hCO dt R e hlk hder) (subjNode s)]
    refine hedgeC s hb hstar ?_ ?_
    · rw [← hsem s (fun hx => absurd hx hstar)]
      exact hsm
    · rintro ⟨hws, hsemstar⟩
      refine hnc ⟨hws, ?_⟩
      rw [hsem (starSubj s.shape) (fun _ => hWSbare _ hws)]
      exact hsemstar
  · intro s hu hstar hsm
    rw [writeLoggedRules_residue]
    refine huposC s hu hstar ?_
    rw [← hsem s (fun hx => absurd hx hstar)]
    exact hsm
  · intro s hstar hws hsemStar hsemF
    rw [writeLoggedRules_residue]
    refine hnegC s hstar hws ?_ ?_
    · rw [← hsem (starSubj s.shape) (fun _ => hWSbare _ hws)]
      exact hsemStar
    · rw [← hsem s (fun hx => absurd hx hstar)]
      exact hsemF

/-- **Stratum-2 `sem` stability (`writeLeg_sem_stable2`)**: at a derived-reading key
    that the write maps NEITHER directly NOR through any of its derived operand keys
    (the attack-confirmed third disjunct), `sem` is unchanged — the stratum-staged
    bridge at both ends of the leg (operand settledness transported by the
    stratum-1 half) with the routed guard stable in the middle. -/
theorem writeLeg_sem_stable2 {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S (t :: T)) (hBS : BareStarStore (t :: T))
    (hTS : TtuStarFree S (t :: T))
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (t :: T) R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2 σ S T) (hadm : FoldAdmits σ (rewriteClosure S t))
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (hopsUnmapped : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (dt, r', on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (hopsSettled : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r')
    {s : SubjectRef} (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  -- the weakened (pre-write) fragment pack
  have hSVw : StoreValidRules S T := fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')
  have hBSw : BareStarStore T := fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')
  have hTSw : TtuStarFree S T := fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht')
  have htermw : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR T R :=
    fun dt R hd => ⟨(hterm dt R hd).1,
      fun t' ht' => (hterm dt R hd).2 t' (List.mem_cons_of_mem _ ht')⟩
  have hco := hCO dt R e hlk hder
  have h' : ReachedByW3d2 (σ.writeLoggedRules S t) S (t :: T) :=
    ReachedByW3d2.write t hadm h
  have hσS : σ.schema = S := reachedByW3d2_schema h
  have hσ'S : (σ.writeLoggedRules S t).schema = S := reachedByW3d2_schema h'
  obtain ⟨σ0, h0, hsh⟩ := reachedByW3d2_shadow h hNK hCO hSVw htermw
  obtain ⟨σ0', h0', hsh'⟩ := reachedByW3d2_shadow h' hNK hCO hSV hterm
  have hclσ := reachedByW3d2_edgesClosed h
  have htp' := reachedByW3d2_edges_target_plain h' hBS
  -- collapse at each derived operand key, on both sides of the leg
  have hcolOps : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) ∧
      (∀ u, NReaches (σ.writeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.writeLoggedRules S t).edges) := by
    intro r' hr' hd'
    obtain ⟨e', hlk'⟩ := isDerived_declared hd'
    have hco' : ComputedOnly e' := hCO dt r' e' hlk' hd'
    exact ⟨fun u hu => reachedByW3d2_reach_collapse_root hWF hSVw hlk' hd' hco' h hu,
      fun u hu => reachedByW3d2_reach_collapse_root hWF hSV hlk' hd' hco' h' hu⟩
  -- operand settledness transports to the post state / post store (the stratum-1 half)
  have hops' : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S (t :: T) (σ.writeLoggedRules S t) dt on r' ∧
      CompleteKey S (t :: T) (σ.writeLoggedRules S t) dt on r' ∧
      (∀ u, NReaches (σ.writeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.writeLoggedRules S t).edges) := by
    intro r' hr' hd'
    obtain ⟨e', hlk'⟩ := isDerived_declared hd'
    have hco' := hCO dt r' e' hlk' hd'
    have hleafUnt' := hLU2 dt R e hlk hder r' hr' hd' e' hlk'
    have hsem_op : ∀ x : SubjectRef, (x.name = STAR → x.predicate = BARE) →
        sem S (t :: T) ⟨x, r', ⟨dt, on⟩⟩ = sem S T ⟨x, r', ⟨dt, on⟩⟩ :=
      fun x hx => writeLeg_sem_stable_sh hWF hTT hNK hR hSV hBS hTS hCO hMatch
        hStrat hterm h0 hsh h0' hsh' hclσ htp' hlk' hd' hco' hleafUnt'
        (hopsUnmapped r' hr' hd') hx hon
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨settledKey_writeLeg_sem hNK hSV hCO hWSbare hlk' hd' hsem_op hset,
      completeKey_writeLeg_sem hNK hSV hCO hWSbare hlk' hd' hsem_op hcomp,
      (hcolOps r' hr' hd').2⟩
  have hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) := by
    intro r' hr' hd'
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨hset, hcomp, (hcolOps r' hr' hd').1⟩
  have hLU2e : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false :=
    fun r' hr' hd' e' hlk' => hLU2 dt R e hlk hder r' hr' hd' e' hlk'
  calc sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩
      = (σ.writeLoggedRules S t).checkFnR (t :: T) s dt on R e :=
        (checkFnR_eq_sem_settled hWF hTT hNK hR hSV hBS hTS hMatch hStrat
          hterm hCO hWSbare h0' hsh' hσ'S hlk hder hco hLU2e hops' hs hon).symm
    _ = (σ.writeLoggedRules S t).checkFnR T s dt on R e :=
        checkFnR_store_irrel _ _ s dt on R hco
    _ = σ.checkFnR T s dt on R e :=
        writeLeg_checkFnR_stable T hNK hSV hCO hσS hclσ htp' hlk hder hco
          hcolOps hon hunmapped s
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFnR_eq_sem_settled hWF hTT hNK hR hSVw hBSw hTSw hMatch hStrat
          htermw hCO hWSbare h0 hsh hσS hlk hder hco hLU2e hops hs hon

/-! ## Batch groundwork for the stratum-staged invariant

The remaining pieces the `ReachedByW3d2C` settledness induction consumes at its
cascade legs: every job EMITS a persistent frontier row (`reconcileJobsLR_emits` —
so a round-1 pass at a stratum-1 key provably RE-DIRTIES its stratum-2 readers for
round 2, `round1_emission_dirties`), and the edge discipline is batch-stable
(targets stay non-`BARE`, R-node in-edge sources stay bare — so the reach collapse
holds at every MID-BATCH prefix state, where the re-settlement lemma reads its
guards). -/

/-- Rows persist through a routed logged batch (emissions only prepend). -/
theorem reconcileJobsLR_outbox_mono (S : Schema) (T : Store) :
    ∀ (jobs : List W3cJob) (σ : GraphState), ∀ d ∈ σ.outbox,
      d ∈ (reconcileJobsLR S T σ jobs).outbox := by
  intro jobs
  induction jobs with
  | nil => intro σ d hd; exact hd
  | cons j rest ih =>
    intro σ d hd
    have hfold : reconcileJobsLR S T σ (j :: rest)
        = reconcileJobsLR S T (j.applyLoggedR S T σ) rest := by
      unfold reconcileJobsLR
      rw [List.foldl_cons]
    rw [hfold]
    refine ih _ d ?_
    unfold W3cJob.applyLoggedR
    rw [pushDelta_outbox]
    refine List.mem_cons_of_mem _ ?_
    rw [W3cJob.applyDR_outbox]
    exact hd

/-- **Every job of a routed logged batch emits a row** at its own derived key, with
    an id strictly above the pre-batch frontier — the introduction form dual to
    `reconcileJobsLR_outbox_sound`. -/
theorem reconcileJobsLR_emits (S : Schema) (T : Store) :
    ∀ (jobs : List W3cJob) (σ : GraphState), ∀ j ∈ jobs,
      ∃ d ∈ (reconcileJobsLR S T σ jobs).outbox,
        d.node = objNode ⟨j.dt, j.on⟩ j.R ∧ d.relation = j.R ∧
        max σ.maxOutboxId σ.watermark < d.id := by
  intro jobs
  induction jobs with
  | nil => intro σ j hj; exact absurd hj List.not_mem_nil
  | cons j0 rest ih =>
    intro σ j hj
    have hfold : reconcileJobsLR S T σ (j0 :: rest)
        = reconcileJobsLR S T (j0.applyLoggedR S T σ) rest := by
      unfold reconcileJobsLR
      rw [List.foldl_cons]
    rw [hfold]
    have hout1 : (j0.applyLoggedR S T σ).outbox
        = ⟨σ.nextDeltaId, objNode ⟨j0.dt, j0.on⟩ j0.R, j0.R, false⟩ :: σ.outbox := by
      unfold W3cJob.applyLoggedR
      rw [pushDelta_outbox, W3cJob.applyDR_outbox, W3cJob.applyDR_nextDeltaId]
    have hwm1 : (j0.applyLoggedR S T σ).watermark = σ.watermark := by
      unfold W3cJob.applyLoggedR
      rw [pushDelta_watermark, W3cJob.applyDR_watermark]
    have hmax1 : (j0.applyLoggedR S T σ).maxOutboxId = σ.nextDeltaId := by
      unfold W3cJob.applyLoggedR
      rw [pushDelta_maxOutboxId, W3cJob.applyDR_nextDeltaId]
    have hnext : σ.nextDeltaId = max σ.maxOutboxId σ.watermark + 1 := rfl
    rcases List.mem_cons.mp hj with rfl | hjr
    · refine ⟨⟨σ.nextDeltaId, objNode ⟨j.dt, j.on⟩ j.R, j.R, false⟩, ?_, rfl, rfl, ?_⟩
      · refine reconcileJobsLR_outbox_mono S T rest _ _ ?_
        rw [hout1]
        exact List.mem_cons_self
      · show max σ.maxOutboxId σ.watermark < σ.nextDeltaId
        omega
    · obtain ⟨d, hd, hn, hr, hgt⟩ := ih (j0.applyLoggedR S T σ) j hjr
      refine ⟨d, hd, hn, hr, ?_⟩
      rw [hmax1, hwm1] at hgt
      omega

/-- **A round-1 pass at an operand key re-dirties its readers for round 2**: if some
    round-1 job targets `(dt, r', on)` and `(dt, R)`'s def reads `r'` as a computed
    operand, then `(dt, R, on)` is in round-2 scope — the model-level content of
    "the stratum-1 emission re-settles the stale stratum-2 key" (12c finding (b);
    `_map_deltas_to_keys` on the pass's own emission). -/
theorem round1_emission_dirties {σ : GraphState} {S : Schema} {T : Store}
    {jobs1 : List W3cJob} {j1 : W3cJob} (hj1 : j1 ∈ jobs1)
    {dt on R r' : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hr' : r' ∈ computedRefs e) (hon : on ≠ STAR)
    (hkey : j1.key = (dt, r', on)) :
    (dt, R, on) ∈ cascadeKeysAbove S (reconcileJobsLR S T σ jobs1)
      (σ.frontierMax σ.watermark) := by
  obtain ⟨d, hd, hnode, _, hgt⟩ := reconcileJobsLR_emits S T jobs1 σ j1 hj1
  have h1 : j1.dt = dt := congrArg Prod.fst hkey
  have h23 : (j1.R, j1.on) = (r', on) := congrArg Prod.snd hkey
  have h2 : j1.R = r' := congrArg Prod.fst h23
  have h3 : j1.on = on := congrArg Prod.snd h23
  have hnode' : d.node = objNode ⟨dt, on⟩ r' := by rw [hnode, h1, h2, h3]
  unfold cascadeKeysAbove
  refine List.mem_flatMap.mpr ⟨d, ?_, ?_⟩
  · unfold GraphState.frontierRowsAbove
    refine List.mem_filter.mpr ⟨hd, decide_eq_true ?_⟩
    have := σ.frontierMax_le σ.watermark
    omega
  · refine mem_affectedKeys hlk hder hr' hon ?_
    unfold GraphState.affectedObjects
    rw [← hnode']
    exact List.mem_cons_self

/-- Non-`BARE` edge targets are batch-stable (new edges land on job R-nodes). -/
theorem reconcileJobsLR_target_ne_bare {S : Schema} {T : Store}
    {jobs : List W3cJob} {σ : GraphState}
    (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (hbase : ∀ a b, (a, b) ∈ σ.edges → b.pred ≠ BARE) :
    ∀ a b, (a, b) ∈ (reconcileJobsLR S T σ jobs).edges → b.pred ≠ BARE := by
  intro a b hab
  rcases reconcileJobsLR_edge_sound jobs σ a b hab with hold | ⟨j, hj, c, _, _, h2⟩
  · exact hbase a b hold
  · obtain ⟨hRne, _⟩ := hjv j hj
    rw [h2, objNode_pred]
    exact hRne

/-- Bare in-edge sources at a FIXED derived R-node are batch-stable (new edges into
    any R-node are sourced at bare candidates). -/
theorem reconcileJobsLR_source_bare {S : Schema} {T : Store}
    {jobs : List W3cJob} {σ : GraphState} {dt on R : String}
    (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (hbase : ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE) :
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T σ jobs).edges →
      x.pred = BARE := by
  intro x hx
  rcases reconcileJobsLR_edge_sound jobs σ x _ hx with hold | ⟨j, hj, c, hc, h1, _⟩
  · exact hbase x hold
  · obtain ⟨_, hcb, _⟩ := hjv j hj
    rw [h1, subjNode_pred]
    exact hcb c hc

/-- **The reach collapse at MID-BATCH prefix states**: from a chain state's edge
    discipline (targets non-bare, sources at the R-node bare), any prefix of a
    routed logged batch keeps every path into the R-node a single edge — where the
    re-settlement lemma reads its guards. -/
theorem reconcileJobsLR_reach_collapse {S : Schema} {T : Store}
    {jobs : List W3cJob} {σ : GraphState} {dt on R : String}
    (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (htb : ∀ a b, (a, b) ∈ σ.edges → b.pred ≠ BARE)
    (hsb : ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE)
    {u : NodeKey}
    (hr : NReaches (reconcileJobsLR S T σ jobs).edges u (objNode ⟨dt, on⟩ R)) :
    (u, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T σ jobs).edges := by
  refine nreaches_collapse_of_source_notarget ?_ hr
  intro x hxv y hxy
  exact reconcileJobsLR_target_ne_bare hjv htb y x hxy
    (reconcileJobsLR_source_bare hjv hsb x hxv)

/-! ## `ReachedByW3d2C` — the two-round coverage chain

`ReachedByW3d2` plus per-round audit-enumeration coverage: round-1 jobs coverage-
complete relative to the LEG-START state, round-2 jobs relative to the MID state
(their passes re-enumerate against the graph as round 1 left it —
`processor.py:394-441` runs inside the round). Chain-side hypotheses as in W3d-1c;
the state-derived discharge is the W3d-2 E-chain tail (with the residue-named
candidates, 12c finding (c)).

**Coverage is CONDITIONAL on the job's operand baseline (attack-established
2026-07-12h, scratch deleted).** A round-1 key CAN be stratum-2 — a write to a
DIRECT untainted leaf of a stratum-2 def (`r2 := r1 \ b` dirtied via pred `b`)
lands the key in `cascadeKeysAbove` at the watermark — and when a leaf of its
derived operand is dirtied in the same window, the state-derived audit enumeration
at the leg start is NOT coverage-complete: the freshly-granted subject exists only
in the dirty operand's FUTURE residue, invisible to leaf reach, `res.neg`/`res.upos`,
and the R-node edges. Python survives this exactly because such a pass's output is
provably stale-and-re-dirtied (`round1_emission_dirties`) and the round-2 re-run
re-enumerates against the settled operand. So the chain hypothesises coverage only
GIVEN that the job's derived operand keys are settled at the round's baseline —
which is precisely what the re-settlement proof consumes (its Case B derives the
baseline before using round-1 coverage; its Case A uses round-1 coverage only at
stratum-1 operand keys, where the baseline is vacuous). -/

/-- The operand baseline of one job at a state: every DERIVED operand key of the
    job's def is settled+complete. Vacuous at stratum-1 keys. -/
def W3dJobOpsSettled (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) : Prop :=
  ∀ r' ∈ computedRefs j.e, isDerived S (j.dt, r') = true →
    SettledKey S T σ j.dt j.on r' ∧ CompleteKey S T σ j.dt j.on r'

inductive ReachedByW3d2C : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByW3d2C (emptyState S) S []
  | write {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hadm : FoldAdmits σ (rewriteClosure S t))
      (hprev : ReachedByW3d2C σ S T) :
      ReachedByW3d2C (σ.writeLoggedRules S t) S (t :: T)
  | remove {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hadm : RemoveAdmits σ T t) (hdrain : cascadeKeys S σ = [])
      (hSVT : StoreValidRules S T) (hBST : BareStarStore T) (hTST : TtuStarFree S T)
      (htermT : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
      (hprev : ReachedByW3d2C σ S T) :
      ReachedByW3d2C (σ.removeLoggedRules S t) S (T.erase t)
  -- hSVT/hBST/hTST/htermT: the pre-remove store T was validly built. FAITHFUL — Python's
  -- TupleSource.remove (connectedstore/source.py) only retracts admission-validated tuples
  -- (validate_write_identifiers + matching Direct arm = StoreValidRules); the star/ttu/term
  -- conditions are the W4Fragment carries graph_correct already assumes about the store.
  -- hdrain: Python drains the view between applied log rows (cascadeKeys non-monotone under
  -- retraction, so remove-from-undrained is unfaithful and would break reachedByW3d2C_settled).
  | cascade {σ : GraphState} {S : Schema} {T : Store} (jobs1 jobs2 : List W3cJob)
      (hjv1 : ∀ j ∈ jobs1, W3cJobValid S j)
      (hjv2 : ∀ j ∈ jobs2, W3cJobValid S j)
      (hcover1 : ∀ k ∈ cascadeKeysAbove S σ σ.watermark, ∃ j ∈ jobs1, j.key = k)
      (hscope1 : ∀ j ∈ jobs1, j.key ∈ cascadeKeysAbove S σ σ.watermark)
      (hcover2 : ∀ k ∈ cascadeKeysAbove S (reconcileJobsLR S T σ jobs1)
          (σ.frontierMax σ.watermark), ∃ j ∈ jobs2, j.key = k)
      (hscope2 : ∀ j ∈ jobs2, j.key ∈ cascadeKeysAbove S (reconcileJobsLR S T σ jobs1)
          (σ.frontierMax σ.watermark))
      (hcovg1 : ∀ j ∈ jobs1, W3dJobOpsSettled S T σ j → W3dJobCoverage S T σ j)
      (hcovg2 : ∀ j ∈ jobs2, W3dJobOpsSettled S T (reconcileJobsLR S T σ jobs1) j →
          W3dJobCoverage S T (reconcileJobsLR S T σ jobs1) j)
      (hprev : ReachedByW3d2C σ S T) :
      ReachedByW3d2C (runCascade2 S T σ jobs1 jobs2) S T

/-- Convert conditional batch coverage into keyMatch-restricted coverage at a key
    whose operand baseline holds: a job targeting `(dt, on, R)` has `j.e = e` (valid
    lookup) so its `W3dJobOpsSettled` is exactly the key's baseline. -/
theorem covg_of_opsSettled {S : Schema} {T : Store} {σ : GraphState}
    {jobs : List W3cJob} (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (hcovg : ∀ j ∈ jobs, W3dJobOpsSettled S T σ j → W3dJobCoverage S T σ j)
    {dt on R : String} {e : Expr} (hlk : S.lookup (dt, R) = some e)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r') :
    ∀ j ∈ jobs, j.keyMatch dt on R → W3dJobCoverage S T σ j := by
  intro j hj hkm
  refine hcovg j hj ?_
  obtain ⟨h1, h2, h3⟩ := hkm
  obtain ⟨_, _, _, _, _, _, _, hlke, _⟩ := hjv j hj
  have hje : j.e = e := by
    rw [h1, h3] at hlke
    exact Option.some.inj (hlke.symm.trans hlk)
  intro r' hr' hd'
  rw [hje] at hr'
  rw [h1] at hd'
  rw [h1, h2]
  exact hops r' hr' hd'

/-- The projection: every W3d-2 coverage-chain state is a plain W3d-2 state — the
    whole structural/shadow/T5 layer applies. -/
theorem reachedByW3d2C_toW3d2 {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2C σ S T) : ReachedByW3d2 σ S T := by
  induction h with
  | empty S => exact ReachedByW3d2.empty S
  | write t hadm _ ih => exact ReachedByW3d2.write t hadm ih
  | remove t hadm hdrain hSVT hBST hTST htermT _ ih =>
    exact ReachedByW3d2.remove t hadm hdrain hSVT hBST hTST htermT ih
  | cascade jobs1 jobs2 hjv1 hjv2 hcover1 hscope1 hcover2 hscope2 _ _ _ ih =>
    exact ReachedByW3d2.cascade jobs1 jobs2 hjv1 hjv2 hcover1 hscope1 hcover2
      hscope2 ih

/-! ## Retraction-leg duals (R5b-iii-a) — the settledness-dual stack, sem/settledness level

Retraction duals of the write-leg settledness-transport lemmas. Two placement/shape notes:

* These live in `CascadeStrataSettle` (not `CascadeStable`, where their write-leg templates
  `writeLeg_sem_stable`/`settledKey_writeLeg` sit) because the remove-leg SHADOW substrate —
  `untaintedShadow_removeLeg` (the R5b-ii shadow-transport crux) and `removeLoggedRules_residue`
  — is strictly downstream of `CascadeStable`. The write leg builds its post-state shadow
  in place via `reachedByW3d_shadow ∘ ReachedByW3d.write`; the retraction has NO `remove`
  constructor (that is the NEXT leg), so the post-state shadow can only come from
  `untaintedShadow_removeLeg`, which transports the PRE-state shadow across the erase given
  R5a's rebuild `σ0'` over `T.erase t`. Hence `removeLeg_sem_stable` / `settledKey_removeLeg`
  carry the rebuild triple `(σ0', h0', hsub)` as hypotheses (the shape the future `remove`
  constructor will supply) in place of the write leg's `ReachedByW3d.write`.

* The pre-state is `ReachedByW3d2` (two-round), matching `untaintedShadow_removeLeg`, where the
  write leg used the single-round `ReachedByW3d`. Plainness/closure fences land on the PRE-state
  `σ` (the bigger edge multiset) — the anti-monotone mirror. -/

/-- One logged retraction leaves the residue map untouched (local copy —
    `removeLoggedRules_residue` lives in the sibling `CascadeStrataInv`, off this import path). -/
theorem removeLoggedOne_residue_eq (σ : GraphState) (t : Tuple) :
    (σ.removeLoggedOne t).residue = σ.residue := by
  unfold GraphState.removeLoggedOne
  split
  · rw [pushDelta_residue, removeEdgeOne_residue]
  · rfl

/-- The logged retraction leaves the residue map untouched (a fold of
    `removeLoggedOne_residue_eq`; local copy of `removeLoggedRules_residue`). -/
theorem removeLoggedRules_residue_eq (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.removeLoggedRules S t).residue = σ.residue := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosure S t = ts
  induction ts generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih]; exact removeLoggedOne_residue_eq σ u

/-- **Retraction-leg `probeDerived` stability at a derived operand key** (dual of
    `writeLeg_probeDerived_stable`). Residue is inert (`removeLoggedRules_residue`) and the reach
    into the derived operand's R-node is fixed: it is a `DerNode`, whose in-edges the retraction
    never touches (`removeLeg_derived_inedges_eq`), and reach into it collapses to a direct edge
    (`hcol`/`hcol'`). No path surgery. -/
theorem removeLeg_probeDerived_stable {σ : GraphState} {S : Schema} {T : Store}
    {t : Tuple}
    (hNK : NodupKeys S) (hSV : StoreValidRules S T) (ht : t ∈ T)
    {dt on r' : String} {e' : Expr}
    (hlk' : S.lookup (dt, r') = some e') (hder' : isDerived S (dt, r') = true)
    (hco' : ComputedOnly e')
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (hclσ' : ∀ ab ∈ (σ.removeLoggedRules S t).edges,
      ab.1 ∈ (σ.removeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.removeLoggedRules S t).nodes)
    (hcol : ∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
      (u, objNode ⟨dt, on⟩ r') ∈ σ.edges)
    (hcol' : ∀ u, NReaches (σ.removeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
      (u, objNode ⟨dt, on⟩ r') ∈ (σ.removeLoggedRules S t).edges)
    {st sn sp : String} (hon : on ≠ STAR) :
    GraphModel.probeDerived (σ.removeLoggedRules S t) ⟨⟨st, sn, sp⟩, r', ⟨dt, on⟩⟩
      = GraphModel.probeDerived σ ⟨⟨st, sn, sp⟩, r', ⟨dt, on⟩⟩ := by
  have hres : (σ.removeLoggedRules S t).residue = σ.residue :=
    removeLoggedRules_residue_eq σ S t
  have hreach : ∀ x : NodeKey, (σ.removeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
      = σ.reach x (objNode ⟨dt, on⟩ r') := by
    intro x
    cases h1 : (σ.removeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
      <;> cases h0 : σ.reach x (objNode ⟨dt, on⟩ r')
    · rfl
    · exfalso
      have hedge := hcol x (reach_sound h0)
      have hedge' := (removeLeg_derived_inedges_eq hSV ht hlk' hder' hco' x).mpr hedge
      have := reach_complete hclσ' (NReaches.edge hedge')
      rw [h1] at this
      cases this
    · exfalso
      have hedge' := hcol' x (reach_sound h1)
      have hedge := (removeLeg_derived_inedges_eq hSV ht hlk' hder' hco' x).mp hedge'
      have := reach_complete hclσ (NReaches.edge hedge)
      rw [h0] at this
      cases this
    · rfl
  rw [probeDerived_eq _ hon, probeDerived_eq σ hon, hres,
    hreach (subjNode ⟨st, sn, sp⟩)]

/-- **Retraction-leg `checkFnR` stability off the mapped keys** (dual of
    `writeLeg_checkFnR_stable`): the routed guard is unchanged by a logged retraction that does
    not map the key — untainted leaves by `removeLeg_graphRec_stable`, derived leaves by
    `removeLeg_probeDerived_stable`. Plainness fence `htp` on the PRE-state. -/
theorem removeLeg_checkFnR_stable {σ : GraphState} {S : Schema} {T : Store}
    {t : Tuple} (T' : Store)
    (hNK : NodupKeys S) (hSV : StoreValidRules S T) (ht : t ∈ T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hσS : σ.schema = S)
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp : ∀ ab ∈ σ.edges, ab.2.variant = Variant.plain)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hcolOps : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) ∧
      (∀ u, NReaches (σ.removeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.removeLoggedRules S t).edges))
    (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (s : SubjectRef) :
    (σ.removeLoggedRules S t).checkFnR T' s dt on R e = σ.checkFnR T' s dt on R e := by
  have hσ'S : (σ.removeLoggedRules S t).schema = S := by
    rw [removeLoggedRules_schema, hσS]
  have hclσ' : ∀ ab ∈ (σ.removeLoggedRules S t).edges,
      ab.1 ∈ (σ.removeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.removeLoggedRules S t).nodes := by
    intro ab hab
    rw [removeLoggedRules_nodes]
    exact hclσ ab (removeLoggedRules_edges_subset σ S t ab hab)
  unfold GraphState.checkFnR
  refine evalE_computedOnly e hco ?_
  intro r' hr'
  cases hd' : isDerived S (dt, r') with
  | false =>
    rw [GraphModel.graphRecR_eq_graphRec s on (by rw [hσ'S]; exact hd'),
      GraphModel.graphRecR_eq_graphRec s on (by rw [hσS]; exact hd')]
    exact removeLeg_graphRec_stable hclσ htp hlk hder hr' hon hunmapped s
  | true =>
    obtain ⟨e', hlk'⟩ := isDerived_declared hd'
    have hco' : ComputedOnly e' := hCO dt r' e' hlk' hd'
    obtain ⟨hcol, hcol'⟩ := hcolOps r' hr' hd'
    show GraphModel.check (σ.removeLoggedRules S t) ⟨s, r', ⟨dt, on⟩⟩
        = GraphModel.check σ ⟨s, r', ⟨dt, on⟩⟩
    rw [GraphModel.check_derived _ ⟨s, r', ⟨dt, on⟩⟩ (by rw [hσ'S]; exact hd'),
      GraphModel.check_derived σ ⟨s, r', ⟨dt, on⟩⟩ (by rw [hσS]; exact hd')]
    obtain ⟨st, sn, sp⟩ := s
    exact removeLeg_probeDerived_stable hNK hSV ht hlk' hd' hco' hclσ hclσ' hcol hcol' hon

/-- **Stratum-1 `sem` stability across a retraction leg, chain-agnostic** (dual of
    `writeLeg_sem_stable_sh`): both shadows supplied directly. The store shifts from `T`
    (pre) to `T.erase t` (post); the guard is stable (`removeLeg_checkFn_stable`) and the
    W3d read bridge (`checkFn_eq_sem_w3d`) applies at both ends. -/
theorem removeLeg_sem_stable_sh {σ σ0 σ0' : GraphState} {S : Schema} {T : Store}
    {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (ht : t ∈ T)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (h0' : ReachedByRulesAdmitted σ0' S (T.erase t))
    (hsh' : UntaintedShadow S (σ.removeLoggedRules S t) σ0')
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp : ∀ ab ∈ σ.edges, ab.2.variant = Variant.plain)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    {s : SubjectRef} (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hSVe : StoreValidRules S (T.erase t) := fun t' ht' => hSV t' (List.mem_of_mem_erase ht')
  have hBSe : BareStarStore (T.erase t) := fun t' ht' => hBS t' (List.mem_of_mem_erase ht')
  have hTSe : TtuStarFree S (T.erase t) := fun t' ht' => hTS t' (List.mem_of_mem_erase ht')
  have hterme : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (T.erase t) R :=
    fun dt R hd => ⟨(hterm dt R hd).1,
      fun t' ht' => (hterm dt R hd).2 t' (List.mem_of_mem_erase ht')⟩
  calc sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩
      = (σ.removeLoggedRules S t).checkFn (T.erase t) s dt on R e :=
        (checkFn_eq_sem_w3d hWF hTT hNK hR hSVe hBSe hTSe hCO hMatch hStrat hterme
          h0' hsh' hlk hco hleafUnt hs hon).symm
    _ = σ.checkFn (T.erase t) s dt on R e :=
        removeLeg_checkFn_stable (T.erase t) hclσ htp hlk hder hco hon hunmapped s
    _ = σ.checkFn T s dt on R e := checkFn_store_irrel _ _ s dt on R hco
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3d hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm
          h0 hsh hlk hco hleafUnt hs hon

/-- **`SettledKey` transports across a retraction leg given `sem` stability** (dual of
    `settledKey_writeLeg_sem`): representation untouched (rows inert via
    `removeLoggedRules_residue`, derived in-edges fixed via `removeLeg_derived_inedges_eq`);
    meaning supplied as `hsem` at store `T.erase t` vs `T`. -/
theorem settledKey_removeLeg_sem {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hNK : NodupKeys S) (hSV : StoreValidRules S T) (ht : t ∈ T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hsem : ∀ s : SubjectRef, (s.name = STAR → s.predicate = BARE) →
      sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩)
    (hset : SettledKey S T σ dt on R) :
    SettledKey S (T.erase t) (σ.removeLoggedRules S t) dt on R := by
  obtain ⟨hrow, hedge⟩ := hset
  constructor
  · intro res hres
    rw [removeLoggedRules_residue_eq] at hres
    obtain ⟨h1, h2, h3⟩ := hrow res hres
    refine ⟨?_, ?_, ?_⟩
    · intro sh
      rw [h1 sh]
      constructor
      · rintro ⟨hws, hsm⟩
        refine ⟨hws, ?_⟩
        rw [hsem (starSubj sh) (fun _ => hWSbare sh hws)]
        exact hsm
      · rintro ⟨hws, hsm⟩
        refine ⟨hws, ?_⟩
        rw [← hsem (starSubj sh) (fun _ => hWSbare sh hws)]
        exact hsm
    · intro n hn
      obtain ⟨hnstar, hsm⟩ := h2 n hn
      refine ⟨hnstar, ?_⟩
      rw [hsem n (fun hx => absurd hx hnstar)]
      exact hsm
    · intro n hn
      obtain ⟨hnp, hnstar, hsm⟩ := h3 n hn
      refine ⟨hnp, hnstar, ?_⟩
      rw [hsem n (fun hx => absurd hx hnstar)]
      exact hsm
  · intro s hb hstar hedge'
    rw [removeLeg_derived_inedges_eq hSV ht hlk hder (hCO dt R e hlk hder) (subjNode s)] at hedge'
    rw [hsem s (fun hx => absurd hx hstar)]
    exact hedge s hb hstar hedge'

/-- **`CompleteKey` transports across a retraction leg given `sem` stability** (dual of
    `completeKey_writeLeg_sem`). -/
theorem completeKey_removeLeg_sem {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hNK : NodupKeys S) (hSV : StoreValidRules S T) (ht : t ∈ T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hsem : ∀ s : SubjectRef, (s.name = STAR → s.predicate = BARE) →
      sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩)
    (hcomp : CompleteKey S T σ dt on R) :
    CompleteKey S (T.erase t) (σ.removeLoggedRules S t) dt on R := by
  obtain ⟨hrowE, hedgeC, huposC, hnegC⟩ := hcomp
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro sh hws hsm
    rw [removeLoggedRules_residue_eq]
    refine hrowE sh hws ?_
    rw [← hsem (starSubj sh) (fun _ => hWSbare sh hws)]
    exact hsm
  · intro s hb hstar hsm hnc
    rw [removeLeg_derived_inedges_eq hSV ht hlk hder (hCO dt R e hlk hder) (subjNode s)]
    refine hedgeC s hb hstar ?_ ?_
    · rw [← hsem s (fun hx => absurd hx hstar)]
      exact hsm
    · rintro ⟨hws, hsemstar⟩
      refine hnc ⟨hws, ?_⟩
      rw [hsem (starSubj s.shape) (fun _ => hWSbare _ hws)]
      exact hsemstar
  · intro s hu hstar hsm
    rw [removeLoggedRules_residue_eq]
    refine huposC s hu hstar ?_
    rw [← hsem s (fun hx => absurd hx hstar)]
    exact hsm
  · intro s hstar hws hsemStar hsemF
    rw [removeLoggedRules_residue_eq]
    refine hnegC s hstar hws ?_ ?_
    · rw [← hsem (starSubj s.shape) (fun _ => hWSbare _ hws)]
      exact hsemStar
    · rw [← hsem s (fun hx => absurd hx hstar)]
      exact hsemF

/-- **Stratum-1 `sem` stability across a retraction leg** (dual of `writeLeg_sem_stable`):
    from a `ReachedByW3d2` pre-state and R5a's rebuild `σ0'` over `T.erase t`, the post-state
    shadow is transported by `untaintedShadow_removeLeg`; the rest is `removeLeg_sem_stable_sh`.
    The rebuild triple `(σ0', h0', hsub)` stands in for the write leg's `ReachedByW3d.write`. -/
theorem removeLeg_sem_stable {σ σ0 σ0' : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3d2 σ S T) (ht : t ∈ T)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (h0' : ReachedByRulesAdmitted σ0' S (T.erase t))
    (hsub : ∀ ed ∈ σ0'.edges, ed ∈ σ0.edges)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    {s : SubjectRef} (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hsh' : UntaintedShadow S (σ.removeLoggedRules S t) σ0' :=
    untaintedShadow_removeLeg h hsh h0 ht h0' hsub hSV hCO
  exact removeLeg_sem_stable_sh hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm ht
    h0 hsh h0' hsh' (reachedByW3d2_edgesClosed h)
    (reachedByW3d2_edges_target_plain h hBS) hlk hder hco hleafUnt hunmapped hs hon

/-- **Settledness transports across a retraction leg at an unmapped key** (dual of
    `settledKey_writeLeg`): representation untouched and the key's `sem` unchanged
    (`removeLeg_sem_stable`). Carries the R5a rebuild triple in place of `ReachedByW3d.write`. -/
theorem settledKey_removeLeg {σ σ0 σ0' : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2 σ S T) (ht : t ∈ T)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (h0' : ReachedByRulesAdmitted σ0' S (T.erase t))
    (hsub : ∀ ed ∈ σ0'.edges, ed ∈ σ0.edges)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (hon : on ≠ STAR)
    (hset : SettledKey S T σ dt on R) :
    SettledKey S (T.erase t) (σ.removeLoggedRules S t) dt on R := by
  have hsem : ∀ s : SubjectRef, (s.name = STAR → s.predicate = BARE) →
      sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
    fun s hs => removeLeg_sem_stable hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm
      h ht h0 hsh h0' hsub hlk hder hco hleafUnt hunmapped hs hon
  exact settledKey_removeLeg_sem hNK hSV ht hCO hWSbare hlk hder hsem hset

/-- **Stratum-2 `sem` stability across a retraction leg** (dual of `writeLeg_sem_stable2`): at a
    derived-reading key the retraction maps NEITHER directly NOR through any derived operand
    key, `sem` is unchanged. The post-state reach-collapse is derived from the pre-state
    collapse (`reachedByW3d2_reach_collapse_root`) plus edge-subset and the fixed derived
    in-edges (`removeLeg_derived_inedges_eq`) — no `remove` constructor needed. Operand
    settledness transports by the stratum-1 dual, the routed guard by `removeLeg_checkFnR_stable`. -/
theorem removeLeg_sem_stable2 {σ σ0 σ0' : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2 σ S T) (ht : t ∈ T)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (h0' : ReachedByRulesAdmitted σ0' S (T.erase t))
    (hsub : ∀ ed ∈ σ0'.edges, ed ∈ σ0.edges)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (hopsUnmapped : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (dt, r', on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (hopsSettled : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r')
    {s : SubjectRef} (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hSVe : StoreValidRules S (T.erase t) := fun t' ht' => hSV t' (List.mem_of_mem_erase ht')
  have hBSe : BareStarStore (T.erase t) := fun t' ht' => hBS t' (List.mem_of_mem_erase ht')
  have hTSe : TtuStarFree S (T.erase t) := fun t' ht' => hTS t' (List.mem_of_mem_erase ht')
  have hterme : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (T.erase t) R :=
    fun dt R hd => ⟨(hterm dt R hd).1,
      fun t' ht' => (hterm dt R hd).2 t' (List.mem_of_mem_erase ht')⟩
  have hco := hCO dt R e hlk hder
  have hσS : σ.schema = S := reachedByW3d2_schema h
  have hσ'S : (σ.removeLoggedRules S t).schema = S := by rw [removeLoggedRules_schema, hσS]
  have hsh' : UntaintedShadow S (σ.removeLoggedRules S t) σ0' :=
    untaintedShadow_removeLeg h hsh h0 ht h0' hsub hSV hCO
  have hclσ := reachedByW3d2_edgesClosed h
  have htp := reachedByW3d2_edges_target_plain h hBS
  -- collapse at each derived operand key, on σ (pre) and post
  have hcolOps : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) ∧
      (∀ u, NReaches (σ.removeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.removeLoggedRules S t).edges) := by
    intro r' hr' hd'
    obtain ⟨e', hlk'⟩ := isDerived_declared hd'
    have hco' : ComputedOnly e' := hCO dt r' e' hlk' hd'
    have hpre : ∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges :=
      fun u hu => reachedByW3d2_reach_collapse_root hWF hSV hlk' hd' hco' h hu
    refine ⟨hpre, ?_⟩
    intro u hu
    have hpreu : (u, objNode ⟨dt, on⟩ r') ∈ σ.edges :=
      hpre u (NReaches.mono_subset (removeLoggedRules_edges_subset σ S t) hu)
    exact (removeLeg_derived_inedges_eq hSV ht hlk' hd' hco' u).mpr hpreu
  -- operand settledness transported to post state / post store
  have hops' : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S (T.erase t) (σ.removeLoggedRules S t) dt on r' ∧
      CompleteKey S (T.erase t) (σ.removeLoggedRules S t) dt on r' ∧
      (∀ u, NReaches (σ.removeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.removeLoggedRules S t).edges) := by
    intro r' hr' hd'
    obtain ⟨e', hlk'⟩ := isDerived_declared hd'
    have hco' := hCO dt r' e' hlk' hd'
    have hleafUnt' := hLU2 dt R e hlk hder r' hr' hd' e' hlk'
    have hsem_op : ∀ x : SubjectRef, (x.name = STAR → x.predicate = BARE) →
        sem S (T.erase t) ⟨x, r', ⟨dt, on⟩⟩ = sem S T ⟨x, r', ⟨dt, on⟩⟩ :=
      fun x hx => removeLeg_sem_stable_sh hWF hTT hNK hR hSV hBS hTS hCO hMatch
        hStrat hterm ht h0 hsh h0' hsh' hclσ htp hlk' hd' hco' hleafUnt'
        (hopsUnmapped r' hr' hd') hx hon
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨settledKey_removeLeg_sem hNK hSV ht hCO hWSbare hlk' hd' hsem_op hset,
      completeKey_removeLeg_sem hNK hSV ht hCO hWSbare hlk' hd' hsem_op hcomp,
      (hcolOps r' hr' hd').2⟩
  have hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) := by
    intro r' hr' hd'
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨hset, hcomp, (hcolOps r' hr' hd').1⟩
  have hLU2e : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false :=
    fun r' hr' hd' e' hlk' => hLU2 dt R e hlk hder r' hr' hd' e' hlk'
  calc sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩
      = (σ.removeLoggedRules S t).checkFnR (T.erase t) s dt on R e :=
        (checkFnR_eq_sem_settled hWF hTT hNK hR hSVe hBSe hTSe hMatch hStrat
          hterme hCO hWSbare h0' hsh' hσ'S hlk hder hco hLU2e hops' hs hon).symm
    _ = (σ.removeLoggedRules S t).checkFnR T s dt on R e :=
        checkFnR_store_irrel _ _ s dt on R hco
    _ = σ.checkFnR T s dt on R e :=
        removeLeg_checkFnR_stable T hNK hSV ht hCO hσS hclσ htp hlk hder hco
          hcolOps hon hunmapped s
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFnR_eq_sem_settled hWF hTT hNK hR hSV hBS hTS hMatch hStrat
          hterm hCO hWSbare h0 hsh hσS hlk hder hco hLU2e hops hs hon

/-! ## Direct-arm settledness-transport groundwork (leg 5d, steps 2–3)

The `_d` clones of the settledness-transport family need four groundwork layers the
`ComputedOnly` originals never did:

1. **`sem` over the empty store is FALSE, unconditionally** (`sem_nil_false`) — the
   only truth sources in `sem` are stored tuples, so the `_d` induction's `empty`
   case needs none of the fragment machinery `sem_nil_derived_false2` threads.
2. **A raw write/remove on a derived key DIRTIES its own key**
   (`writeLeg_own_key_dirty` / `removeLeg_own_key_dirty`) — the 2026-07-20c
   `affectedKeys` LeafFamily own-key branch (`Delta.leaf`), made chain-usable. This
   is what lets an UNMAPPED key conclude the leg's tuple sits at a DIFFERENT
   derived node (`writeLeg_inedges_eq_of_unmapped`), replacing the `ComputedOnly`
   "no stored derived-key tuples" argument (`exprDirects_computedOnly`) that is
   FALSE under `StoreValidRulesD`.
3. **In-edge preservation from node inequality alone**
   (`rewriteClosure_notarget_of_ne` + the `_of_unmapped` wrappers) — fragment-free.
4. **Store-argument invariance of the ROUTED guard on `ComputedOrDirect` defs**
   (`evalE_cd_grants_agree`, `checkFnR_cons_irrel_cd`, `checkFnR_erase_irrel_cd`) —
   a `Direct` arm reads the store, so `checkFnR_store_irrel` is FALSE for CD defs;
   the honest replacement conditions on the changed tuple missing the key's grant
   window (`grantsOf_cons_of_ne` / `grantsOf_erase_of_ne`), discharged in context
   from own-key dirtiness. -/

/-- Every `evalE` truth source reads the store; with a constantly-false recursion and
    an EMPTY store every leaf — `direct` (no grants), `ttu` (no parents), `computed`
    (the recursion) — is false, hence so is every boolean combination. -/
theorem evalE_nil_false {rec : Rec} {sub : SubjectRef} {q : Query} {dt on rel : String}
    (hrec : ∀ ot onm r, rec ot onm r = false) :
    ∀ e : Expr, evalE rec sub ([] : Store) q dt on rel e = false := by
  intro e
  induction e with
  | computed r' => simp only [evalE]; exact hrec dt on r'
  | direct rs => simp [evalE, directLeaf, grantsOf, memberOfGranted]
  | ttu tr ts => simp [evalE, ttuLeaf]
  | union a b iha ihb => simp only [evalE]; rw [iha, ihb]; rfl
  | inter a b iha ihb => simp only [evalE]; rw [iha, ihb]; rfl
  | excl a b iha ihb => simp only [evalE]; rw [iha, ihb]; rfl

/-- `semAux` over the empty store is false at every fuel and node. -/
theorem semAux_nil_false (S : Schema) (sub : SubjectRef) (q : Query) :
    ∀ (n : Nat) (ot onm r : String), semAux S sub ([] : Store) q n ot onm r = false := by
  intro n
  induction n with
  | zero => intro ot onm r; rfl
  | succ n ih =>
    intro ot onm r
    show step S sub ([] : Store) q (semAux S sub ([] : Store) q n) ot onm r = false
    unfold step
    cases hlk : S.lookup (ot, r) with
    | none => rfl
    | some e => exact evalE_nil_false (fun ot' onm' r' => ih ot' onm' r') e

/-- **`sem` over the empty store is FALSE for every query** — hypothesis-free. -/
theorem sem_nil_false (S : Schema) (q : Query) : sem S ([] : Store) q = false :=
  semAux_nil_false S q.subject q (fuelBound S ([] : Store)) q.object.type
    q.object.name q.relation

/-- **A raw admitted write on a derived key dirties its OWN key** — the chain-level
    form of the `affectedKeys` LeafFamily own-key branch (`processor.py:991-1011`;
    the 2026-07-20c model fix): the seed delta carries `leaf = true` at the concrete
    object node of the derived relation, and its id lands above the watermark. -/
theorem writeLeg_own_key_dirty {σ : GraphState} {S : Schema} {t : Tuple}
    (hNK : NodupKeys S) (hadm : FoldAdmits σ (rewriteClosure S t))
    (hd : isDerived S (t.object.type, t.relation) = true)
    (honT : t.object.name ≠ STAR) :
    (t.object.type, t.relation, t.object.name)
      ∈ cascadeKeys S (σ.writeLoggedRules S t) := by
  have hcl : rewriteClosure S t = [t] := rewriteClosure_derived_eq_seed_nk hNK hd
  have hone : σ.writeLoggedRules S t = σ.writeLoggedOne t := by
    unfold GraphState.writeLoggedRules
    rw [hcl]
    simp only [List.foldl_cons, List.foldl_nil]
  rw [hcl] at hadm
  obtain ⟨hadm1, -⟩ := hadm
  have hpush : σ.writeLoggedOne t
      = (σ.writeDirect t).pushDelta (objNode t.object t.relation) t.relation true := by
    unfold GraphState.writeLoggedOne
    rw [if_pos hadm1]
  set d : Delta :=
    ⟨(σ.writeDirect t).nextDeltaId, objNode t.object t.relation, t.relation, true⟩
    with hd_def
  have hout : d ∈ (σ.writeLoggedOne t).outbox := by
    rw [hpush, pushDelta_outbox]
    exact List.mem_cons_self
  have hwm : (σ.writeLoggedOne t).watermark = σ.watermark := by
    rw [hpush, pushDelta_watermark, writeDirect_watermark]
  have hgt : (σ.writeLoggedOne t).watermark < d.id := by
    rw [hwm]
    have hnext : (σ.writeDirect t).nextDeltaId
        = max (σ.writeDirect t).maxOutboxId (σ.writeDirect t).watermark + 1 := rfl
    have hwmw : (σ.writeDirect t).watermark = σ.watermark := writeDirect_watermark σ t
    show σ.watermark < (σ.writeDirect t).nextDeltaId
    omega
  rw [hone]
  unfold cascadeKeys
  refine List.mem_flatMap.mpr ⟨d, ?_, ?_⟩
  · unfold GraphState.frontierRows
    exact List.mem_filter.mpr ⟨hout, decide_eq_true hgt⟩
  · unfold affectedKeys
    refine List.mem_append_left _ ?_
    have hnode : d.node = ⟨t.object.type, t.object.name, t.relation, Variant.plain⟩ := by
      show objNode t.object t.relation = _
      rw [objNode_plain honT]
    rw [if_pos ?_]
    · rw [hnode]
      exact List.mem_singleton.mpr rfl
    · refine ⟨rfl, ?_, ?_⟩
      · rw [hnode]; exact honT
      · rw [hnode]; exact hd

/-- **A raw remove on a derived key whose seed edge is PRESENT dirties its OWN key**
    (the retraction mirror: `removeLoggedOne` emits `leaf = true` on the actual
    edge-multiset flip). -/
theorem removeLeg_own_key_dirty {σ : GraphState} {S : Schema} {t : Tuple}
    (hNK : NodupKeys S)
    (hpres : (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges)
    (hd : isDerived S (t.object.type, t.relation) = true)
    (honT : t.object.name ≠ STAR) :
    (t.object.type, t.relation, t.object.name)
      ∈ cascadeKeys S (σ.removeLoggedRules S t) := by
  have hcl : rewriteClosure S t = [t] := rewriteClosure_derived_eq_seed_nk hNK hd
  have hone : σ.removeLoggedRules S t = σ.removeLoggedOne t := by
    unfold GraphState.removeLoggedRules
    rw [hcl]
    simp only [List.foldl_cons, List.foldl_nil]
  have hpush : σ.removeLoggedOne t
      = (σ.removeEdgeOne (subjNode t.subject) (objNode t.object t.relation)).pushDelta
          (objNode t.object t.relation) t.relation true := by
    unfold GraphState.removeLoggedOne
    rw [if_pos hpres]
  set σr := σ.removeEdgeOne (subjNode t.subject) (objNode t.object t.relation)
    with hσr_def
  set d : Delta := ⟨σr.nextDeltaId, objNode t.object t.relation, t.relation, true⟩
    with hd_def
  have hout : d ∈ (σ.removeLoggedOne t).outbox := by
    rw [hpush, pushDelta_outbox]
    exact List.mem_cons_self
  have hwm : (σ.removeLoggedOne t).watermark = σ.watermark := by
    rw [hpush, pushDelta_watermark, removeEdgeOne_watermark]
  have hgt : (σ.removeLoggedOne t).watermark < d.id := by
    rw [hwm]
    have hnext : σr.nextDeltaId = max σr.maxOutboxId σr.watermark + 1 := rfl
    have hwmw : σr.watermark = σ.watermark := by
      rw [hσr_def]; exact removeEdgeOne_watermark σ _ _
    show σ.watermark < σr.nextDeltaId
    omega
  rw [hone]
  unfold cascadeKeys
  refine List.mem_flatMap.mpr ⟨d, ?_, ?_⟩
  · unfold GraphState.frontierRows
    exact List.mem_filter.mpr ⟨hout, decide_eq_true hgt⟩
  · unfold affectedKeys
    refine List.mem_append_left _ ?_
    have hnode : d.node = ⟨t.object.type, t.object.name, t.relation, Variant.plain⟩ := by
      show objNode t.object t.relation = _
      rw [objNode_plain honT]
    rw [if_pos ?_]
    · rw [hnode]
      exact List.mem_singleton.mpr rfl
    · refine ⟨rfl, ?_, ?_⟩
      · rw [hnode]; exact honT
      · rw [hnode]; exact hd

/-- No rewrite-closure member of `t` targets the derived node `objNode ⟨dt,on⟩ R`,
    given `t`'s own seed node differs — fragment-free (rule outputs are killed by
    `noRuleOutputs_of_derived`, the seed by the hypothesis). -/
theorem rewriteClosure_notarget_of_ne {S : Schema} {t : Tuple} {dt on R : String}
    (hder : isDerived S (dt, R) = true)
    (hne : objNode t.object t.relation ≠ objNode ⟨dt, on⟩ R) :
    ∀ w ∈ rewriteClosure S t, objNode w.object w.relation ≠ objNode ⟨dt, on⟩ R := by
  intro w hw h2
  have htype : dt = w.object.type := by
    simpa [objNode_type] using (congrArg NodeKey.type h2).symm
  have hrel : R = w.relation := by
    simpa [objNode_pred] using (congrArg NodeKey.pred h2).symm
  rcases rewriteClosure_produced hw with heq | ⟨r, hr', hro, hrout⟩
  · rw [heq] at h2
    exact hne h2
  · exact noRuleOutputs_of_derived hder r hr' ⟨hro.trans htype.symm, hrout.trans hrel.symm⟩

/-- No rewrite-closure member of an UNTAINTED-key tuple targets a derived node —
    the seed's key disagrees on taint, rule outputs are untainted. -/
theorem rewriteClosure_notarget_of_untainted {S : Schema} {t : Tuple} {dt on R : String}
    (hd : isDerived S (t.object.type, t.relation) = false)
    (hder : isDerived S (dt, R) = true) :
    ∀ w ∈ rewriteClosure S t, objNode w.object w.relation ≠ objNode ⟨dt, on⟩ R := by
  refine rewriteClosure_notarget_of_ne hder ?_
  intro h2
  have htype : t.object.type = dt := by
    simpa [objNode_type] using congrArg NodeKey.type h2
  have hrel : t.relation = R := by
    simpa [objNode_pred] using congrArg NodeKey.pred h2
  rw [htype, hrel, hder] at hd
  exact Bool.noConfusion hd

/-- **Write-leg in-edge preservation at a derived node, from node inequality alone**
    (the `_d` replacement for `writeLeg_derived_inedges_eq`, whose `ComputedOnly`
    seed-branch argument is dead under `StoreValidRulesD`). -/
theorem writeLeg_derived_inedges_eq_d {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R : String}
    (hder : isDerived S (dt, R) = true)
    (hne : objNode t.object t.relation ≠ objNode ⟨dt, on⟩ R)
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.writeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  constructor
  · intro h
    rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).edges] at h
    rcases foldl_writeDirect_edges_sound (rewriteClosure S t) h with hold | ⟨w, hw, _h1, h2⟩
    · exact hold
    · exact absurd h2.symm (rewriteClosure_notarget_of_ne hder hne w hw)
  · exact fun h => writeLoggedRules_edges_mono σ S t _ h

/-- **Retraction-leg in-edge preservation at a derived node, from node inequality
    alone** (the `_d` replacement for `removeLeg_derived_inedges_eq`). -/
theorem removeLeg_derived_inedges_eq_d {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R : String}
    (hder : isDerived S (dt, R) = true)
    (hne : objNode t.object t.relation ≠ objNode ⟨dt, on⟩ R)
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.removeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  unfold GraphState.removeLoggedRules
  exact mem_foldl_removeLoggedOne_edges_iff_of_notarget (rewriteClosure S t)
    (rewriteClosure_notarget_of_ne hder hne) σ

/-- The seed node of an UNMAPPED derived key's write differs from the key's node:
    were they equal, the write would sit on the (derived) key itself and the
    own-key branch would have dirtied it. -/
theorem write_node_ne_of_unmapped {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R : String}
    (hNK : NodupKeys S) (hadm : FoldAdmits σ (rewriteClosure S t))
    (hder : isDerived S (dt, R) = true) (hon : on ≠ STAR)
    (honT : t.object.name ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t)) :
    objNode t.object t.relation ≠ objNode ⟨dt, on⟩ R := by
  intro heq
  have heq' : objNode ⟨t.object.type, t.object.name⟩ t.relation = objNode ⟨dt, on⟩ R := heq
  obtain ⟨h1, h2, h3⟩ := objNode_inj_of_ne_star honT hon heq'
  have hd : isDerived S (t.object.type, t.relation) = true := by
    rw [h1, h3]
    exact hder
  have := writeLeg_own_key_dirty hNK hadm hd honT
  rw [h1, h2, h3] at this
  exact hunmapped this

/-- **Write-leg in-edge preservation at an UNMAPPED derived key** — the packaged
    form the settledness transports consume: either the write's seed node differs
    (preservation from node inequality), or it coincides — but then the own-key
    branch dirties the key, contradicting unmappedness. -/
theorem writeLeg_inedges_eq_of_unmapped {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R : String}
    (hNK : NodupKeys S) (hadm : FoldAdmits σ (rewriteClosure S t))
    (hder : isDerived S (dt, R) = true) (hon : on ≠ STAR)
    (honT : t.object.name ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.writeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) :=
  writeLeg_derived_inedges_eq_d hder
    (write_node_ne_of_unmapped hNK hadm hder hon honT hunmapped) u

/-- **Retraction-leg in-edge preservation at an UNMAPPED derived key.** Node
    inequality gives preservation; node equality splits on the seed edge: present ⇒
    the retraction dirties the own key (contradiction), absent ⇒ the retraction is
    the identity (the singleton derived closure's `removeLoggedOne` guard fails). -/
theorem removeLeg_inedges_eq_of_unmapped {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R : String}
    (hNK : NodupKeys S)
    (hder : isDerived S (dt, R) = true) (hon : on ≠ STAR)
    (honT : t.object.name ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.removeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  by_cases hne : objNode t.object t.relation = objNode ⟨dt, on⟩ R
  · -- the tuple sits on the key itself
    have heq' : objNode ⟨t.object.type, t.object.name⟩ t.relation = objNode ⟨dt, on⟩ R := hne
    obtain ⟨h1, h2, h3⟩ := objNode_inj_of_ne_star honT hon heq'
    have hd : isDerived S (t.object.type, t.relation) = true := by
      rw [h1, h3]
      exact hder
    by_cases hpres : (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges
    · exfalso
      have := removeLeg_own_key_dirty hNK hpres hd honT
      rw [h1, h2, h3] at this
      exact hunmapped this
    · -- absent seed edge: the retraction is the identity on the state
      have hcl : rewriteClosure S t = [t] := rewriteClosure_derived_eq_seed_nk hNK hd
      have hone : σ.removeLoggedRules S t = σ := by
        unfold GraphState.removeLoggedRules
        rw [hcl]
        simp only [List.foldl_cons, List.foldl_nil]
        unfold GraphState.removeLoggedOne
        rw [if_neg hpres]
      rw [hone]
  · exact removeLeg_derived_inedges_eq_d hder hne u

/-! ### The two-round chain's structural facts under the widened admission -/

/-- **Every W3d-2 edge target has a non-`BARE` predicate under `StoreValidRulesD`**
    (`_d` mirror of `reachedByW3d2_edge_target_ne_bare`; the seed leg reads
    declaredness from `rewriteClosure_rel_ne_bare_d`). `hDAB` converts the `remove`
    constructor's plain pre-store validity to the widened form. -/
theorem reachedByW3d2_edge_target_ne_bare_d {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    WF S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → DirectArmsBare e) →
    StoreValidRulesD S T → ∀ a b, (a, b) ∈ σ.edges → b.pred ≠ BARE := by
  induction h with
  | empty S =>
    intro _ _ _ a b hab
    simp [emptyState] at hab
  | @write σp S T t hadm hprev ih =>
    intro hWF hDAB hSV a b hab
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hab
    rcases foldl_writeDirect_edges_sound (rewriteClosure S t) hab with hold | ⟨u, hu, _, h2⟩
    · exact ih hWF hDAB (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) a b hold
    · rw [h2, objNode_pred]
      exact rewriteClosure_rel_ne_bare_d hWF hSV List.mem_cons_self hu
  | @remove σp S T t _ _ hSVT _ _ _ _ ih =>
    intro hWF hDAB _ a b hab
    exact ih hWF hDAB (storeValidRulesD_of_storeValidRules_directArmsBare hSVT hDAB)
      a b (mem_removeLoggedRules_edges hab)
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro hWF hDAB hSV a b hab
    unfold runCascade2 at hab
    split at hab
    · have hab' : (a, b) ∈ (reconcileJobsLR S T (reconcileJobsLR S T σp jobs1)
          jobs2).edges := hab
      rcases reconcileJobsLR_edge_sound jobs2 _ a b hab' with hmid | ⟨j, hj, c, _, _, h2⟩
      · rcases reconcileJobsLR_edge_sound jobs1 σp a b hmid
          with hold | ⟨j, hj, c, _, _, h2⟩
        · exact ih hWF hDAB hSV a b hold
        · obtain ⟨hRne, _⟩ := hjv1 j hj
          rw [h2, objNode_pred]
          exact hRne
      · obtain ⟨hRne, _⟩ := hjv2 j hj
        rw [h2, objNode_pred]
        exact hRne
    · exact ih hWF hDAB hSV a b hab

/-- A `BARE`-predicate node is never an edge target on a W3d-2 state, widened
    admission. -/
theorem reachedByW3d2_bareNode_no_inedge_d {σ : GraphState} {S : Schema} {T : Store}
    (hWF : WF S)
    (hDAB : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      DirectArmsBare e)
    (hSV : StoreValidRulesD S T) (h : ReachedByW3d2 σ S T)
    {k : NodeKey} (hk : k.pred = BARE) : ∀ x, (x, k) ∉ σ.edges := by
  intro x hxk
  exact reachedByW3d2_edge_target_ne_bare_d h hWF hDAB hSV x k hxk hk

/-- **Every in-edge source at a derived R-node is bare, widened admission** (`_d`
    mirror of `reachedByW3d2_Rnode_source_bare` — no `ComputedOnly` at the key: the
    write leg's seed edge MAY land on the R-node, but the widened admission pins its
    stored subject BARE). -/
theorem reachedByW3d2_Rnode_source_bare_d {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String}
    (h : ReachedByW3d2 σ S T) :
    isDerived S (dt, R) = true →
    (∀ dt' R' e', S.lookup (dt', R') = some e' → isDerived S (dt', R') = true →
      DirectArmsBare e') →
    StoreValidRulesD S T →
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE := by
  induction h with
  | empty S =>
    intro _ _ _ x hx
    simp [emptyState] at hx
  | @write σp S T t hadm hprev ih =>
    intro hder hDAB hSV x hx
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hx
    rcases foldl_writeDirect_edges_sound (rewriteClosure S t) hx with hold | ⟨w, hw, h1, h2⟩
    · exact ih hder hDAB (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) x hold
    · -- a fresh closure edge into the R-node: the seed's stored subject is BARE by
      -- the widened admission; rule outputs never land on a derived key
      have htype : dt = w.object.type := by
        simpa [objNode_type] using congrArg NodeKey.type h2
      have hrel : R = w.relation := by
        simpa [objNode_pred] using congrArg NodeKey.pred h2
      rcases rewriteClosure_produced hw with heq | ⟨r, hr', hro, hrout⟩
      · rcases hSV t List.mem_cons_self with ⟨hf, _⟩ | ⟨_, hbare, _⟩
        · rw [← heq, ← htype, ← hrel, hder] at hf
          exact Bool.noConfusion hf
        · rw [h1, subjNode_pred, heq]
          exact hbare
      · exact absurd ⟨hro.trans htype.symm, hrout.trans hrel.symm⟩
          (noRuleOutputs_of_derived hder r hr')
  | @remove σp S T t _ _ hSVT _ _ _ _ ih =>
    intro hder hDAB _ x hx
    exact ih hder hDAB (storeValidRulesD_of_storeValidRules_directArmsBare hSVT hDAB)
      x (mem_removeLoggedRules_edges hx)
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro hder hDAB hSV x hx
    unfold runCascade2 at hx
    split at hx
    · have hx' : (x, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T
          (reconcileJobsLR S T σp jobs1) jobs2).edges := hx
      rcases reconcileJobsLR_edge_sound jobs2 _ x _ hx' with hmid | ⟨j, hj, c, hc, h1, _⟩
      · rcases reconcileJobsLR_edge_sound jobs1 σp x _ hmid
          with hold | ⟨j, hj, c, hc, h1, _⟩
        · exact ih hder hDAB hSV x hold
        · obtain ⟨_, hcb, _⟩ := hjv1 j hj
          rw [h1, subjNode_pred]
          exact hcb c hc
      · obtain ⟨_, hcb, _⟩ := hjv2 j hj
        rw [h1, subjNode_pred]
        exact hcb c hc
    · exact ih hder hDAB hSV x hx

/-- **The W3d-2 reach collapse at a derived R-node, widened admission**: any path
    into the R-node is a single edge (sources bare, bare nodes have no in-edges). -/
theorem reachedByW3d2_reach_collapse_root_d {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {u : NodeKey}
    (hWF : WF S)
    (hDAB : ∀ dt' R' e', S.lookup (dt', R') = some e' → isDerived S (dt', R') = true →
      DirectArmsBare e')
    (hSV : StoreValidRulesD S T)
    (hder : isDerived S (dt, R) = true)
    (h : ReachedByW3d2 σ S T)
    (hr : NReaches σ.edges u (objNode ⟨dt, on⟩ R)) :
    (u, objNode ⟨dt, on⟩ R) ∈ σ.edges := by
  refine nreaches_collapse_of_source_notarget ?_ hr
  intro x hxv
  exact reachedByW3d2_bareNode_no_inedge_d hWF hDAB hSV h
    (reachedByW3d2_Rnode_source_bare_d h hder hDAB hSV x hxv)

/-! ### Store-argument invariance of the routed guard on CD defs -/

/-- A cons'd tuple missing the key's grant window leaves `grantsOf` unchanged. -/
theorem grantsOf_cons_of_ne {T : Store} {t : Tuple} (rs : List Restriction)
    {dt on rel : String} (hon : on ≠ STAR)
    (hne : ¬ (t.relation = rel ∧ t.object.type = dt ∧
      (t.object.name = on ∨ t.object.name = STAR))) :
    grantsOf (t :: T) rs dt on rel = grantsOf T rs dt on rel := by
  unfold grantsOf
  rw [List.filter_cons, if_neg]
  intro hp
  rw [Bool.and_eq_true, Bool.and_eq_true, Bool.and_eq_true] at hp
  obtain ⟨⟨⟨hrel, htype⟩, hcont⟩, _⟩ := hp
  refine hne ⟨beq_iff_eq.mp hrel, beq_iff_eq.mp htype, ?_⟩
  have hmem : t.object.name ∈ matchingObjects on := by
    rw [List.contains_eq_mem] at hcont
    exact of_decide_eq_true hcont
  unfold matchingObjects at hmem
  rw [if_neg hon] at hmem
  rcases List.mem_cons.mp hmem with h | h
  · exact Or.inl h
  · exact Or.inr (List.mem_singleton.mp h)

/-- An erased tuple missing the key's grant window leaves `grantsOf` unchanged. -/
theorem grantsOf_erase_of_ne {T : Store} {t : Tuple} (rs : List Restriction)
    {dt on rel : String} (hon : on ≠ STAR)
    (hne : ¬ (t.relation = rel ∧ t.object.type = dt ∧
      (t.object.name = on ∨ t.object.name = STAR))) :
    grantsOf (T.erase t) rs dt on rel = grantsOf T rs dt on rel := by
  unfold grantsOf
  refine filter_erase_neg ?_ T
  by_contra hp
  rw [Bool.not_eq_false, Bool.and_eq_true, Bool.and_eq_true, Bool.and_eq_true] at hp
  obtain ⟨⟨⟨hrel, htype⟩, hcont⟩, _⟩ := hp
  refine hne ⟨beq_iff_eq.mp hrel, beq_iff_eq.mp htype, ?_⟩
  have hmem : t.object.name ∈ matchingObjects on := by
    rw [List.contains_eq_mem] at hcont
    exact of_decide_eq_true hcont
  unfold matchingObjects at hmem
  rw [if_neg hon] at hmem
  rcases List.mem_cons.mp hmem with h | h
  · exact Or.inl h
  · exact Or.inr (List.mem_singleton.mp h)

/-- A bare `Direct` leaf with EQUAL grants evaluates identically across recursions,
    stores and queries (the userset flow-through is dead on bare grants on both
    sides). -/
theorem directLeaf_bare_agree_of_grants_eq {rec1 rec2 : Rec} {sub : SubjectRef}
    {T1 T2 : Store} {q1 q2 : Query} {rs : List Restriction} {ot on rel : String}
    (hb : ∀ r ∈ rs, r.2.1 = BARE)
    (hg : grantsOf T1 rs ot on rel = grantsOf T2 rs ot on rel) :
    directLeaf rec1 sub T1 q1 rs ot on rel = directLeaf rec2 sub T2 q2 rs ot on rel := by
  have hmog1 : memberOfGranted rec1 T1 q1 (grantsOf T1 rs ot on rel) = false :=
    memberOfGranted_of_bareGrants rec1 T1 q1 _ (grantsOf_bare_subjects T1 rs ot on rel hb)
  have hmog2 : memberOfGranted rec2 T2 q2 (grantsOf T2 rs ot on rel) = false :=
    memberOfGranted_of_bareGrants rec2 T2 q2 _ (grantsOf_bare_subjects T2 rs ot on rel hb)
  unfold directLeaf
  rw [hg] at hmog1 ⊢
  simp only [hmog1, hmog2, Bool.or_false]

/-- **The CD-tree store congruence**: two evaluations of a `ComputedOrDirect` +
    `DirectArmsBare` tree agree when their recursions agree on the `computed` leaves
    and their stores agree on every `Direct` arm's grants at the key. -/
theorem evalE_cd_grants_agree {rec1 rec2 : Rec} {sub : SubjectRef}
    {T1 T2 : Store} {q1 q2 : Query} {dt on rel : String} :
    ∀ e : Expr, ComputedOrDirect e → DirectArmsBare e →
      (∀ r' ∈ computedRefs e, rec1 dt on r' = rec2 dt on r') →
      (∀ rs ∈ exprDirectsAll e, grantsOf T1 rs dt on rel = grantsOf T2 rs dt on rel) →
      evalE rec1 sub T1 q1 dt on rel e = evalE rec2 sub T2 q2 dt on rel e := by
  intro e
  induction e with
  | computed r' =>
    intro _ _ hag _
    simp only [evalE]
    exact hag r' (List.mem_singleton.mpr rfl)
  | direct rs =>
    intro _ hb _ hg
    simp only [evalE]
    exact directLeaf_bare_agree_of_grants_eq hb
      (hg rs (by simp [exprDirectsAll]))
  | union a b iha ihb =>
    intro hcd hba hag hg
    simp only [evalE]
    rw [iha hcd.1 hba.1 (fun r' hr' => hag r' (List.mem_append_left _ hr'))
        (fun rs hrs => hg rs (List.mem_append_left _ hrs)),
      ihb hcd.2 hba.2 (fun r' hr' => hag r' (List.mem_append_right _ hr'))
        (fun rs hrs => hg rs (List.mem_append_right _ hrs))]
  | inter a b iha ihb =>
    intro hcd hba hag hg
    simp only [evalE]
    rw [iha hcd.1 hba.1 (fun r' hr' => hag r' (List.mem_append_left _ hr'))
        (fun rs hrs => hg rs (List.mem_append_left _ hrs)),
      ihb hcd.2 hba.2 (fun r' hr' => hag r' (List.mem_append_right _ hr'))
        (fun rs hrs => hg rs (List.mem_append_right _ hrs))]
  | excl a b iha ihb =>
    intro hcd hba hag hg
    simp only [evalE]
    rw [iha hcd.1 hba.1 (fun r' hr' => hag r' (List.mem_append_left _ hr'))
        (fun rs hrs => hg rs (List.mem_append_left _ hrs)),
      ihb hcd.2 hba.2 (fun r' hr' => hag r' (List.mem_append_right _ hr'))
        (fun rs hrs => hg rs (List.mem_append_right _ hrs))]
  | ttu tr ts => intro hcd _ _ _; exact hcd.elim

/-- **Routed-guard store invariance across a cons, CD defs**: a written tuple that
    misses the key's grant window leaves `checkFnR` unchanged (the `_d` replacement
    for `checkFnR_store_irrel`'s cons instance). -/
theorem checkFnR_cons_irrel_cd {σ : GraphState} {T : Store} {t : Tuple}
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e) (hon : on ≠ STAR)
    (hne : ¬ (t.relation = R ∧ t.object.type = dt ∧
      (t.object.name = on ∨ t.object.name = STAR))) :
    σ.checkFnR (t :: T) s dt on R e = σ.checkFnR T s dt on R e := by
  unfold GraphState.checkFnR
  exact evalE_cd_grants_agree e hcd hba (fun _ _ => rfl)
    (fun rs _ => grantsOf_cons_of_ne rs hon hne)

/-- **Routed-guard store invariance across an erase, CD defs.** -/
theorem checkFnR_erase_irrel_cd {σ : GraphState} {T : Store} {t : Tuple}
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e) (hon : on ≠ STAR)
    (hne : ¬ (t.relation = R ∧ t.object.type = dt ∧
      (t.object.name = on ∨ t.object.name = STAR))) :
    σ.checkFnR (T.erase t) s dt on R e = σ.checkFnR T s dt on R e := by
  unfold GraphState.checkFnR
  exact evalE_cd_grants_agree e hcd hba (fun _ _ => rfl)
    (fun rs _ => grantsOf_erase_of_ne rs hon hne)

/-! ### Leg-level guard stability, widened admission

The `_d` clones of the write/remove-leg guard-stability layer. Two changes vs the
`ComputedOnly` originals: the tree congruence is `evalE_computedOrDirect` (a bare
`Direct` arm rides — same store both sides here), and the derived-operand
`probeDerived` stability derives its in-edge preservation from own-key dirtiness
(`*_inedges_eq_of_unmapped`) instead of the dead `ComputedOnly` store argument. -/

/-- Write-leg `probeDerived` stability at an UNMAPPED derived operand key, `_d`. -/
theorem writeLeg_probeDerived_stable_d {σ : GraphState} {S : Schema} {t : Tuple}
    (hNK : NodupKeys S) (hadm : FoldAdmits σ (rewriteClosure S t))
    {dt on r' : String}
    (hder' : isDerived S (dt, r') = true) (honT : t.object.name ≠ STAR)
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (hclσ' : ∀ ab ∈ (σ.writeLoggedRules S t).edges,
      ab.1 ∈ (σ.writeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.writeLoggedRules S t).nodes)
    (hcol : ∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
      (u, objNode ⟨dt, on⟩ r') ∈ σ.edges)
    (hcol' : ∀ u, NReaches (σ.writeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
      (u, objNode ⟨dt, on⟩ r') ∈ (σ.writeLoggedRules S t).edges)
    (hunm' : (dt, r', on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    {st sn sp : String} (hon : on ≠ STAR) :
    GraphModel.probeDerived (σ.writeLoggedRules S t) ⟨⟨st, sn, sp⟩, r', ⟨dt, on⟩⟩
      = GraphModel.probeDerived σ ⟨⟨st, sn, sp⟩, r', ⟨dt, on⟩⟩ := by
  have hres : (σ.writeLoggedRules S t).residue = σ.residue :=
    writeLoggedRules_residue σ S t
  have hreach : ∀ x : NodeKey, (σ.writeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
      = σ.reach x (objNode ⟨dt, on⟩ r') := by
    intro x
    cases h1 : (σ.writeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
      <;> cases h0 : σ.reach x (objNode ⟨dt, on⟩ r')
    · rfl
    · exfalso
      have hedge := hcol x (reach_sound h0)
      have hedge' := (writeLeg_inedges_eq_of_unmapped hNK hadm hder' hon honT hunm' x).mpr
        hedge
      have := reach_complete hclσ' (NReaches.edge hedge')
      rw [h1] at this
      cases this
    · exfalso
      have hedge' := hcol' x (reach_sound h1)
      have hedge := (writeLeg_inedges_eq_of_unmapped hNK hadm hder' hon honT hunm' x).mp
        hedge'
      have := reach_complete hclσ (NReaches.edge hedge)
      rw [h0] at this
      cases this
    · rfl
  rw [probeDerived_eq _ hon, probeDerived_eq σ hon, hres,
    hreach (subjNode ⟨st, sn, sp⟩)]

/-- **The routed guard is stable across an unmapped write leg, CD defs** (`_d` clone
    of `writeLeg_checkFnR_stable`): untainted leaves by fan-out completeness, derived
    leaves by the `_d` write-inert derived read, the `Direct` arm rides the CD tree
    congruence (same store both sides). -/
theorem writeLeg_checkFnR_stable_d {σ : GraphState} {S : Schema} {t : Tuple} (T' : Store)
    (hNK : NodupKeys S) (hadm : FoldAdmits σ (rewriteClosure S t))
    (honT : t.object.name ≠ STAR)
    (hσS : σ.schema = S)
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant = Variant.plain)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hcolOps : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) ∧
      (∀ u, NReaches (σ.writeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.writeLoggedRules S t).edges))
    (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (hopsUnmapped : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (dt, r', on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (s : SubjectRef) :
    (σ.writeLoggedRules S t).checkFnR T' s dt on R e = σ.checkFnR T' s dt on R e := by
  have hσ'S : (σ.writeLoggedRules S t).schema = S := by
    rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).schema, writeRules_schema, hσS]
  have hclσ' : ∀ ab ∈ (σ.writeLoggedRules S t).edges,
      ab.1 ∈ (σ.writeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.writeLoggedRules S t).nodes := by
    have hev := writeLoggedRules_evalEq (EvalEq.refl σ) S t
    intro ab hab
    rw [hev.edges] at hab
    rw [hev.nodes]
    exact edgesClosed_foldl_writeDirect (rewriteClosure S t) σ hclσ ab hab
  unfold GraphState.checkFnR
  refine evalE_computedOrDirect e hcd hba ?_
  intro r' hr'
  cases hd' : isDerived S (dt, r') with
  | false =>
    rw [GraphModel.graphRecR_eq_graphRec s on (by rw [hσ'S]; exact hd'),
      GraphModel.graphRecR_eq_graphRec s on (by rw [hσS]; exact hd')]
    exact writeLeg_graphRec_stable hclσ htp' hlk hder hr' hon hunmapped s
  | true =>
    obtain ⟨hcol, hcol'⟩ := hcolOps r' hr' hd'
    show GraphModel.check (σ.writeLoggedRules S t) ⟨s, r', ⟨dt, on⟩⟩
        = GraphModel.check σ ⟨s, r', ⟨dt, on⟩⟩
    rw [GraphModel.check_derived _ ⟨s, r', ⟨dt, on⟩⟩ (by rw [hσ'S]; exact hd'),
      GraphModel.check_derived σ ⟨s, r', ⟨dt, on⟩⟩ (by rw [hσS]; exact hd')]
    obtain ⟨st, sn, sp⟩ := s
    exact writeLeg_probeDerived_stable_d hNK hadm hd' honT hclσ hclσ' hcol hcol'
      (hopsUnmapped r' hr' hd') hon

/-- Retraction-leg `probeDerived` stability at an UNMAPPED derived operand key, `_d`. -/
theorem removeLeg_probeDerived_stable_d {σ : GraphState} {S : Schema} {t : Tuple}
    (hNK : NodupKeys S)
    {dt on r' : String}
    (hder' : isDerived S (dt, r') = true) (honT : t.object.name ≠ STAR)
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (hclσ' : ∀ ab ∈ (σ.removeLoggedRules S t).edges,
      ab.1 ∈ (σ.removeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.removeLoggedRules S t).nodes)
    (hcol : ∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
      (u, objNode ⟨dt, on⟩ r') ∈ σ.edges)
    (hcol' : ∀ u, NReaches (σ.removeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
      (u, objNode ⟨dt, on⟩ r') ∈ (σ.removeLoggedRules S t).edges)
    (hunm' : (dt, r', on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    {st sn sp : String} (hon : on ≠ STAR) :
    GraphModel.probeDerived (σ.removeLoggedRules S t) ⟨⟨st, sn, sp⟩, r', ⟨dt, on⟩⟩
      = GraphModel.probeDerived σ ⟨⟨st, sn, sp⟩, r', ⟨dt, on⟩⟩ := by
  have hres : (σ.removeLoggedRules S t).residue = σ.residue :=
    removeLoggedRules_residue_eq σ S t
  have hreach : ∀ x : NodeKey, (σ.removeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
      = σ.reach x (objNode ⟨dt, on⟩ r') := by
    intro x
    cases h1 : (σ.removeLoggedRules S t).reach x (objNode ⟨dt, on⟩ r')
      <;> cases h0 : σ.reach x (objNode ⟨dt, on⟩ r')
    · rfl
    · exfalso
      have hedge := hcol x (reach_sound h0)
      have hedge' := (removeLeg_inedges_eq_of_unmapped hNK hder' hon honT hunm' x).mpr
        hedge
      have := reach_complete hclσ' (NReaches.edge hedge')
      rw [h1] at this
      cases this
    · exfalso
      have hedge' := hcol' x (reach_sound h1)
      have hedge := (removeLeg_inedges_eq_of_unmapped hNK hder' hon honT hunm' x).mp
        hedge'
      have := reach_complete hclσ (NReaches.edge hedge)
      rw [h0] at this
      cases this
    · rfl
  rw [probeDerived_eq _ hon, probeDerived_eq σ hon, hres,
    hreach (subjNode ⟨st, sn, sp⟩)]

/-- **The routed guard is stable across an unmapped retraction leg, CD defs** (`_d`
    clone of `removeLeg_checkFnR_stable`). Plainness fence `htp` on the PRE-state. -/
theorem removeLeg_checkFnR_stable_d {σ : GraphState} {S : Schema} {t : Tuple} (T' : Store)
    (hNK : NodupKeys S) (honT : t.object.name ≠ STAR)
    (hσS : σ.schema = S)
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp : ∀ ab ∈ σ.edges, ab.2.variant = Variant.plain)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hcolOps : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) ∧
      (∀ u, NReaches (σ.removeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.removeLoggedRules S t).edges))
    (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (hopsUnmapped : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (dt, r', on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (s : SubjectRef) :
    (σ.removeLoggedRules S t).checkFnR T' s dt on R e = σ.checkFnR T' s dt on R e := by
  have hσ'S : (σ.removeLoggedRules S t).schema = S := by
    rw [removeLoggedRules_schema, hσS]
  have hclσ' : ∀ ab ∈ (σ.removeLoggedRules S t).edges,
      ab.1 ∈ (σ.removeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.removeLoggedRules S t).nodes := by
    intro ab hab
    rw [removeLoggedRules_nodes]
    exact hclσ ab (removeLoggedRules_edges_subset σ S t ab hab)
  unfold GraphState.checkFnR
  refine evalE_computedOrDirect e hcd hba ?_
  intro r' hr'
  cases hd' : isDerived S (dt, r') with
  | false =>
    rw [GraphModel.graphRecR_eq_graphRec s on (by rw [hσ'S]; exact hd'),
      GraphModel.graphRecR_eq_graphRec s on (by rw [hσS]; exact hd')]
    exact removeLeg_graphRec_stable hclσ htp hlk hder hr' hon hunmapped s
  | true =>
    obtain ⟨hcol, hcol'⟩ := hcolOps r' hr' hd'
    show GraphModel.check (σ.removeLoggedRules S t) ⟨s, r', ⟨dt, on⟩⟩
        = GraphModel.check σ ⟨s, r', ⟨dt, on⟩⟩
    rw [GraphModel.check_derived _ ⟨s, r', ⟨dt, on⟩⟩ (by rw [hσ'S]; exact hd'),
      GraphModel.check_derived σ ⟨s, r', ⟨dt, on⟩⟩ (by rw [hσS]; exact hd')]
    obtain ⟨st, sn, sp⟩ := s
    exact removeLeg_probeDerived_stable_d hNK hd' honT hclσ hclσ' hcol hcol'
      (hopsUnmapped r' hr' hd') hon

/-! ### The stratum-1 W3d read bridge over the FILTERED shadow -/

/-- **`checkFn = sem` at any shadowed state, filtered-σ0 form**
    (`checkFn_eq_sem_w3d_filt`): the untainted-core agreement lands the guard at the
    σ0 rebuild over `T↾U`, where the widened base bridge (`checkFn_eq_sem_bs_d`)
    reads it at `sem S (T↾U)`; the derived-key filter bridge
    (`sem_untaintedFilter_co`) lifts to the FULL store. The stratum-1 bridge every
    `_d` operand transport consumes in place of `checkFn_eq_sem_w3d`. -/
theorem checkFn_eq_sem_w3d_filt {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRulesD S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h0 : ReachedByRulesAdmitted σ0 S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh : UntaintedShadow S σ σ0)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hDecl : StoreDeclared S T := storeDeclared_of_validRulesD hSV
  have hSVU : StoreValidRules S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    storeValidRules_untaintedFilter hSV
  have hStoreUntU : ∀ t ∈ T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)),
      isDerived S (t.object.type, t.relation) = false := by
    intro t ht
    simpa using (List.mem_filter.mp ht).2
  have hSVU_D : StoreValidRulesD S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    fun t ht => Or.inl ⟨hStoreUntU t ht, hSVU t ht⟩
  have hBSU : BareStarStore (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    fun t ht => hBS t (List.mem_filter.mp ht).1
  have hTSU : TtuStarFree S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    fun t ht => hTS t (List.mem_filter.mp ht).1
  have htermU : ∀ dt' R', isDerived S (dt', R') = true → NoTtuTarget S R' ∧
      NoStoreSubjectR (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) R' :=
    fun dt' R' hd => ⟨(hterm dt' R' hd).1,
      fun t ht => (hterm dt' R' hd).2 t (List.mem_filter.mp ht).1⟩
  calc σ.checkFn T s dt on R e
      = σ0.checkFn T s dt on R e :=
        checkFn_agree_of_graphRec T s dt on R e hco hleafUnt
          (fun s' r' hr' => shadow_graphRec_agree hsh s' on hr')
    _ = σ0.checkFn (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
          s dt on R e :=
        checkFn_store_irrel _ _ s dt on R hco
    _ = sem S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
          ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_bs_d hWF hTT hNK hR hSVU_D hBSU hTSU hMatch hStrat htermU
          (ReachedByW3aAdmitted.base h0) hlk (computedOnly_computedOrDirect hco)
          (computedOnly_directArmsBare hco) hleafUnt hs hon
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        (sem_untaintedFilter_co hNK hDecl hBS.noUsersetStar hTS hStrat hlk hco
          hleafUnt).symm

/-- **Stratum-1 `sem` stability across a write leg, filtered-σ0 form** (`_d` clone of
    `writeLeg_sem_stable_sh`): the guard is stable and reads at `sem` through the
    filtered bridge at both ends of the leg. -/
theorem writeLeg_sem_stable_sh_d {σ σ0 σ0' : GraphState} {S : Schema} {T : Store}
    {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRulesD S (t :: T)) (hBS : BareStarStore (t :: T))
    (hTS : TtuStarFree S (t :: T))
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (t :: T) R)
    (h0 : ReachedByRulesAdmitted σ0 S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh : UntaintedShadow S σ σ0)
    (h0' : ReachedByRulesAdmitted σ0' S
      ((t :: T).filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh' : UntaintedShadow S (σ.writeLoggedRules S t) σ0')
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant = Variant.plain)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    {s : SubjectRef} (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hSVw : StoreValidRulesD S T := fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')
  have hBSw : BareStarStore T := fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')
  have hTSw : TtuStarFree S T := fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht')
  have htermw : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR T R :=
    fun dt R hd => ⟨(hterm dt R hd).1,
      fun t' ht' => (hterm dt R hd).2 t' (List.mem_cons_of_mem _ ht')⟩
  calc sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩
      = (σ.writeLoggedRules S t).checkFn (t :: T) s dt on R e :=
        (checkFn_eq_sem_w3d_filt hWF hTT hNK hR hSV hBS hTS hMatch hStrat hterm
          h0' hsh' hlk hco hleafUnt hs hon).symm
    _ = σ.checkFn (t :: T) s dt on R e :=
        writeLeg_checkFn_stable (t :: T) hclσ htp' hlk hder hco hon hunmapped s
    _ = σ.checkFn T s dt on R e := checkFn_store_irrel _ _ s dt on R hco
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3d_filt hWF hTT hNK hR hSVw hBSw hTSw hMatch hStrat htermw
          h0 hsh hlk hco hleafUnt hs hon

/-- **Stratum-1 `sem` stability across a retraction leg, filtered-σ0 form** (`_d`
    clone of `removeLeg_sem_stable_sh`). -/
theorem removeLeg_sem_stable_sh_d {σ σ0 σ0' : GraphState} {S : Schema} {T : Store}
    {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRulesD S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (ht : t ∈ T)
    (h0 : ReachedByRulesAdmitted σ0 S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh : UntaintedShadow S σ σ0)
    (h0' : ReachedByRulesAdmitted σ0' S
      ((T.erase t).filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh' : UntaintedShadow S (σ.removeLoggedRules S t) σ0')
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp : ∀ ab ∈ σ.edges, ab.2.variant = Variant.plain)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    {s : SubjectRef} (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hSVe : StoreValidRulesD S (T.erase t) :=
    fun t' ht' => hSV t' (List.mem_of_mem_erase ht')
  have hBSe : BareStarStore (T.erase t) := fun t' ht' => hBS t' (List.mem_of_mem_erase ht')
  have hTSe : TtuStarFree S (T.erase t) := fun t' ht' => hTS t' (List.mem_of_mem_erase ht')
  have hterme : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (T.erase t) R :=
    fun dt R hd => ⟨(hterm dt R hd).1,
      fun t' ht' => (hterm dt R hd).2 t' (List.mem_of_mem_erase ht')⟩
  calc sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩
      = (σ.removeLoggedRules S t).checkFn (T.erase t) s dt on R e :=
        (checkFn_eq_sem_w3d_filt hWF hTT hNK hR hSVe hBSe hTSe hMatch hStrat hterme
          h0' hsh' hlk hco hleafUnt hs hon).symm
    _ = σ.checkFn (T.erase t) s dt on R e :=
        removeLeg_checkFn_stable (T.erase t) hclσ htp hlk hder hco hon hunmapped s
    _ = σ.checkFn T s dt on R e := checkFn_store_irrel _ _ s dt on R hco
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3d_filt hWF hTT hNK hR hSV hBS hTS hMatch hStrat hterm
          h0 hsh hlk hco hleafUnt hs hon

/-! ### Per-key settledness transports, widened admission -/

/-- **`SettledKey` transports across a write leg given `sem` stability, `_d`** —
    representation untouched: rows write-inert, and the UNMAPPED key's derived
    in-edges fixed by own-key dirtiness (no `StoreValidRules`/`ComputedOnly`). -/
theorem settledKey_writeLeg_sem_d {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hNK : NodupKeys S) (hadm : FoldAdmits σ (rewriteClosure S t))
    (honT : t.object.name ≠ STAR)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {dt on R : String}
    (hder : isDerived S (dt, R) = true) (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (hsem : ∀ s : SubjectRef, (s.name = STAR → s.predicate = BARE) →
      sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩)
    (hset : SettledKey S T σ dt on R) :
    SettledKey S (t :: T) (σ.writeLoggedRules S t) dt on R := by
  obtain ⟨hrow, hedge⟩ := hset
  constructor
  · intro res hres
    rw [writeLoggedRules_residue] at hres
    obtain ⟨h1, h2, h3⟩ := hrow res hres
    refine ⟨?_, ?_, ?_⟩
    · intro sh
      rw [h1 sh]
      constructor
      · rintro ⟨hws, hsm⟩
        refine ⟨hws, ?_⟩
        rw [hsem (starSubj sh) (fun _ => hWSbare sh hws)]
        exact hsm
      · rintro ⟨hws, hsm⟩
        refine ⟨hws, ?_⟩
        rw [← hsem (starSubj sh) (fun _ => hWSbare sh hws)]
        exact hsm
    · intro n hn
      obtain ⟨hnstar, hsm⟩ := h2 n hn
      refine ⟨hnstar, ?_⟩
      rw [hsem n (fun hx => absurd hx hnstar)]
      exact hsm
    · intro n hn
      obtain ⟨hnp, hnstar, hsm⟩ := h3 n hn
      refine ⟨hnp, hnstar, ?_⟩
      rw [hsem n (fun hx => absurd hx hnstar)]
      exact hsm
  · intro s hb hstar hedge'
    rw [writeLeg_inedges_eq_of_unmapped hNK hadm hder hon honT hunmapped
      (subjNode s)] at hedge'
    rw [hsem s (fun hx => absurd hx hstar)]
    exact hedge s hb hstar hedge'

/-- **`CompleteKey` transports across a write leg given `sem` stability, `_d`.** -/
theorem completeKey_writeLeg_sem_d {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hNK : NodupKeys S) (hadm : FoldAdmits σ (rewriteClosure S t))
    (honT : t.object.name ≠ STAR)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {dt on R : String}
    (hder : isDerived S (dt, R) = true) (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (hsem : ∀ s : SubjectRef, (s.name = STAR → s.predicate = BARE) →
      sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩)
    (hcomp : CompleteKey S T σ dt on R) :
    CompleteKey S (t :: T) (σ.writeLoggedRules S t) dt on R := by
  obtain ⟨hrowE, hedgeC, huposC, hnegC⟩ := hcomp
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro sh hws hsm
    rw [writeLoggedRules_residue]
    refine hrowE sh hws ?_
    rw [← hsem (starSubj sh) (fun _ => hWSbare sh hws)]
    exact hsm
  · intro s hb hstar hsm hnc
    rw [writeLeg_inedges_eq_of_unmapped hNK hadm hder hon honT hunmapped (subjNode s)]
    refine hedgeC s hb hstar ?_ ?_
    · rw [← hsem s (fun hx => absurd hx hstar)]
      exact hsm
    · rintro ⟨hws, hsemstar⟩
      refine hnc ⟨hws, ?_⟩
      rw [hsem (starSubj s.shape) (fun _ => hWSbare _ hws)]
      exact hsemstar
  · intro s hu hstar hsm
    rw [writeLoggedRules_residue]
    refine huposC s hu hstar ?_
    rw [← hsem s (fun hx => absurd hx hstar)]
    exact hsm
  · intro s hstar hws hsemStar hsemF
    rw [writeLoggedRules_residue]
    refine hnegC s hstar hws ?_ ?_
    · rw [← hsem (starSubj s.shape) (fun _ => hWSbare _ hws)]
      exact hsemStar
    · rw [← hsem s (fun hx => absurd hx hstar)]
      exact hsemF

/-- **`SettledKey` transports across a retraction leg given `sem` stability, `_d`.** -/
theorem settledKey_removeLeg_sem_d {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hNK : NodupKeys S) (honT : t.object.name ≠ STAR)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {dt on R : String}
    (hder : isDerived S (dt, R) = true) (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (hsem : ∀ s : SubjectRef, (s.name = STAR → s.predicate = BARE) →
      sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩)
    (hset : SettledKey S T σ dt on R) :
    SettledKey S (T.erase t) (σ.removeLoggedRules S t) dt on R := by
  obtain ⟨hrow, hedge⟩ := hset
  constructor
  · intro res hres
    rw [removeLoggedRules_residue_eq] at hres
    obtain ⟨h1, h2, h3⟩ := hrow res hres
    refine ⟨?_, ?_, ?_⟩
    · intro sh
      rw [h1 sh]
      constructor
      · rintro ⟨hws, hsm⟩
        refine ⟨hws, ?_⟩
        rw [hsem (starSubj sh) (fun _ => hWSbare sh hws)]
        exact hsm
      · rintro ⟨hws, hsm⟩
        refine ⟨hws, ?_⟩
        rw [← hsem (starSubj sh) (fun _ => hWSbare sh hws)]
        exact hsm
    · intro n hn
      obtain ⟨hnstar, hsm⟩ := h2 n hn
      refine ⟨hnstar, ?_⟩
      rw [hsem n (fun hx => absurd hx hnstar)]
      exact hsm
    · intro n hn
      obtain ⟨hnp, hnstar, hsm⟩ := h3 n hn
      refine ⟨hnp, hnstar, ?_⟩
      rw [hsem n (fun hx => absurd hx hnstar)]
      exact hsm
  · intro s hb hstar hedge'
    rw [removeLeg_inedges_eq_of_unmapped hNK hder hon honT hunmapped
      (subjNode s)] at hedge'
    rw [hsem s (fun hx => absurd hx hstar)]
    exact hedge s hb hstar hedge'

/-- **`CompleteKey` transports across a retraction leg given `sem` stability, `_d`.** -/
theorem completeKey_removeLeg_sem_d {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hNK : NodupKeys S) (honT : t.object.name ≠ STAR)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {dt on R : String}
    (hder : isDerived S (dt, R) = true) (hon : on ≠ STAR)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (hsem : ∀ s : SubjectRef, (s.name = STAR → s.predicate = BARE) →
      sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩)
    (hcomp : CompleteKey S T σ dt on R) :
    CompleteKey S (T.erase t) (σ.removeLoggedRules S t) dt on R := by
  obtain ⟨hrowE, hedgeC, huposC, hnegC⟩ := hcomp
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro sh hws hsm
    rw [removeLoggedRules_residue_eq]
    refine hrowE sh hws ?_
    rw [← hsem (starSubj sh) (fun _ => hWSbare sh hws)]
    exact hsm
  · intro s hb hstar hsm hnc
    rw [removeLeg_inedges_eq_of_unmapped hNK hder hon honT hunmapped (subjNode s)]
    refine hedgeC s hb hstar ?_ ?_
    · rw [← hsem s (fun hx => absurd hx hstar)]
      exact hsm
    · rintro ⟨hws, hsemstar⟩
      refine hnc ⟨hws, ?_⟩
      rw [hsem (starSubj s.shape) (fun _ => hWSbare _ hws)]
      exact hsemstar
  · intro s hu hstar hsm
    rw [removeLoggedRules_residue_eq]
    refine huposC s hu hstar ?_
    rw [← hsem s (fun hx => absurd hx hstar)]
    exact hsm
  · intro s hstar hws hsemStar hsemF
    rw [removeLoggedRules_residue_eq]
    refine hnegC s hstar hws ?_ ?_
    · rw [← hsem (starSubj s.shape) (fun _ => hWSbare _ hws)]
      exact hsemStar
    · rw [← hsem s (fun hx => absurd hx hstar)]
      exact hsemF

/-! ### Stratum-2 `sem` stability, widened admission

The `_d` clones of `writeLeg_sem_stable2` / `removeLeg_sem_stable2`. Fragment pack:
schema-wide `ComputedOrDirect` + `DirectArmsBare` on derived defs, derived OPERAND
defs `ComputedOnly` (`hCOop` — the landed `_filt` machinery's scope), `hLU2` two
strata. The store steps go through the CD grant-window congruences, keyed off
own-key dirtiness; both read ends are the filtered-σ0 bridge with shadows derived
from the chain states (`reachedByW3d2_shadow_d`).

The RETRACTION clone additionally carries **`hNoUD`** (`exprDirects e = []` on
derived defs — every `Direct` arm sits under an `inter`/`excl`, the canonical
`but not` shape): the `remove` constructor guards its PRE store with the PLAIN
`StoreValidRules`, under which a derived-key tuple is storable exactly through a
union-reachable `Direct` arm; erasing such a tuple whose seed edge was retracted
(covered subject) changes the key's Direct-arm grants with NO own-key delta, and
proving `sem` stability there needs a star→concrete `sem` coverage monotonicity
lemma this leg does not build. `hNoUD` closes that door honestly: the pre store
then contains NO derived-key tuples at all. The motivating fragment
(`approver := excl(direct[user], computed banned)`) satisfies it; lifting it is
follow-up work, recorded in the session notes. -/

/-- **Stratum-2 `sem` stability across a write leg, widened admission**
    (`writeLeg_sem_stable2_d`). -/
theorem writeLeg_sem_stable2_d {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRulesD S (t :: T)) (hBS : BareStarStore (t :: T))
    (hTS : TtuStarFree S (t :: T))
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (t :: T) R)
    (hCD : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOrDirect e)
    (hDAB : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      DirectArmsBare e)
    (hCOop : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' → ComputedOnly e')
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2 σ S T) (hadm : FoldAdmits σ (rewriteClosure S t))
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (hopsUnmapped : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (dt, r', on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (hopsSettled : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r')
    {s : SubjectRef} (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  -- the weakened (pre-write) fragment pack
  have hSVw : StoreValidRulesD S T := fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')
  have hBSw : BareStarStore T := fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')
  have hTSw : TtuStarFree S T := fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht')
  have htermw : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR T R :=
    fun dt R hd => ⟨(hterm dt R hd).1,
      fun t' ht' => (hterm dt R hd).2 t' (List.mem_cons_of_mem _ ht')⟩
  have hcd := hCD dt R e hlk hder
  have hba := hDAB dt R e hlk hder
  have hCOop_e := hCOop dt R e hlk hder
  have honT : t.object.name ≠ STAR := (hBS t List.mem_cons_self).2
  have h' : ReachedByW3d2 (σ.writeLoggedRules S t) S (t :: T) :=
    ReachedByW3d2.write t hadm h
  have hσS : σ.schema = S := reachedByW3d2_schema h
  have hσ'S : (σ.writeLoggedRules S t).schema = S := reachedByW3d2_schema h'
  obtain ⟨σ0, h0, hsh⟩ := reachedByW3d2_shadow_d h hNK hCD hDAB hSVw htermw hWF hBSw
  obtain ⟨σ0', h0', hsh'⟩ := reachedByW3d2_shadow_d h' hNK hCD hDAB hSV hterm hWF hBS
  have hclσ := reachedByW3d2_edgesClosed h
  have htp' := reachedByW3d2_edges_target_plain h' hBS
  -- collapse at each derived operand key, on both sides of the leg
  have hcolOps : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) ∧
      (∀ u, NReaches (σ.writeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.writeLoggedRules S t).edges) := by
    intro r' hr' hd'
    exact ⟨fun u hu => reachedByW3d2_reach_collapse_root_d hWF hDAB hSVw hd' h hu,
      fun u hu => reachedByW3d2_reach_collapse_root_d hWF hDAB hSV hd' h' hu⟩
  -- operand settledness transports to the post state / post store (the stratum-1 half)
  have hops' : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S (t :: T) (σ.writeLoggedRules S t) dt on r' ∧
      CompleteKey S (t :: T) (σ.writeLoggedRules S t) dt on r' ∧
      (∀ u, NReaches (σ.writeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.writeLoggedRules S t).edges) := by
    intro r' hr' hd'
    obtain ⟨e', hlk'⟩ := isDerived_declared hd'
    have hco' : ComputedOnly e' := hCOop_e r' hr' hd' e' hlk'
    have hleafUnt' := hLU2 dt R e hlk hder r' hr' hd' e' hlk'
    have hsem_op : ∀ x : SubjectRef, (x.name = STAR → x.predicate = BARE) →
        sem S (t :: T) ⟨x, r', ⟨dt, on⟩⟩ = sem S T ⟨x, r', ⟨dt, on⟩⟩ :=
      fun x hx => writeLeg_sem_stable_sh_d hWF hTT hNK hR hSV hBS hTS hMatch
        hStrat hterm h0 hsh h0' hsh' hclσ htp' hlk' hd' hco' hleafUnt'
        (hopsUnmapped r' hr' hd') hx hon
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨settledKey_writeLeg_sem_d hNK hadm honT hWSbare hd' hon
        (hopsUnmapped r' hr' hd') hsem_op hset,
      completeKey_writeLeg_sem_d hNK hadm honT hWSbare hd' hon
        (hopsUnmapped r' hr' hd') hsem_op hcomp,
      (hcolOps r' hr' hd').2⟩
  have hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) := by
    intro r' hr' hd'
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨hset, hcomp, (hcolOps r' hr' hd').1⟩
  have hLU2e : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false :=
    fun r' hr' hd' e' hlk' => hLU2 dt R e hlk hder r' hr' hd' e' hlk'
  -- the written tuple misses the key's grant window (else the own-key branch fires)
  have hneKey : ¬ (t.relation = R ∧ t.object.type = dt ∧
      (t.object.name = on ∨ t.object.name = STAR)) := by
    rintro ⟨h1, h2, h3 | h3⟩
    · refine write_node_ne_of_unmapped hNK hadm hder hon honT hunmapped ?_
      show objNode t.object t.relation = objNode ⟨dt, on⟩ R
      rw [show t.object = (⟨t.object.type, t.object.name⟩ : ObjectRef) from rfl,
        h1, h2, h3]
    · exact honT h3
  calc sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩
      = (σ.writeLoggedRules S t).checkFnR (t :: T) s dt on R e :=
        (checkFnR_eq_sem_settled_d_filt hWF hTT hNK hR hSV hBS hTS hMatch hStrat
          hterm hWSbare h0' hsh' hσ'S hlk hder hcd hba hCOop_e hLU2e hops' hs hon).symm
    _ = (σ.writeLoggedRules S t).checkFnR T s dt on R e :=
        checkFnR_cons_irrel_cd hcd hba hon hneKey
    _ = σ.checkFnR T s dt on R e :=
        writeLeg_checkFnR_stable_d T hNK hadm honT hσS hclσ htp' hlk hder hcd hba
          hcolOps hon hunmapped hopsUnmapped s
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFnR_eq_sem_settled_d_filt hWF hTT hNK hR hSVw hBSw hTSw hMatch hStrat
          htermw hWSbare h0 hsh hσS hlk hder hcd hba hCOop_e hLU2e hops hs hon

/-- **Stratum-2 `sem` stability across a retraction leg, widened admission**
    (`removeLeg_sem_stable2_d`). Carries the `remove` constructor's own guards (the
    pre store is PLAIN-valid and drained) plus `hNoUD`, under which the pre store
    provably contains NO derived-key tuple — the erased tuple's key is untainted, so
    every derived key's grant window and in-edges are untouched. -/
theorem removeLeg_sem_stable2_d {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSVT : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCD : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOrDirect e)
    (hDAB : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      DirectArmsBare e)
    (hCOop : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' → ComputedOnly e')
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (hNoUD : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      exprDirects e = [])
    (h : ReachedByW3d2 σ S T) (hadm : RemoveAdmits σ T t)
    (hdrain : cascadeKeys S σ = [])
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (hopsUnmapped : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (dt, r', on) ∉ cascadeKeys S (σ.removeLoggedRules S t))
    (hopsSettled : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r')
    {s : SubjectRef} (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have ht : t ∈ T := hadm
  have honT : t.object.name ≠ STAR := (hBS t ht).2
  -- the erased tuple's key is UNTAINTED: a derived-key tuple would need a
  -- union-reachable Direct arm, dead under `hNoUD`
  have htu : isDerived S (t.object.type, t.relation) = false := by
    by_contra hcon
    rw [Bool.not_eq_false] at hcon
    obtain ⟨e', rs, hlk', hrs, _⟩ := hSVT t ht
    rw [hNoUD _ _ _ hlk' hcon] at hrs
    exact absurd hrs List.not_mem_nil
  have hSVD : StoreValidRulesD S T :=
    storeValidRulesD_of_storeValidRules_directArmsBare hSVT hDAB
  have hSVTe : StoreValidRules S (T.erase t) :=
    fun t' ht' => hSVT t' (List.mem_of_mem_erase ht')
  have hSVDe : StoreValidRulesD S (T.erase t) :=
    fun t' ht' => hSVD t' (List.mem_of_mem_erase ht')
  have hBSe : BareStarStore (T.erase t) := fun t' ht' => hBS t' (List.mem_of_mem_erase ht')
  have hTSe : TtuStarFree S (T.erase t) := fun t' ht' => hTS t' (List.mem_of_mem_erase ht')
  have hterme : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (T.erase t) R :=
    fun dt R hd => ⟨(hterm dt R hd).1,
      fun t' ht' => (hterm dt R hd).2 t' (List.mem_of_mem_erase ht')⟩
  have hcd := hCD dt R e hlk hder
  have hba := hDAB dt R e hlk hder
  have hCOop_e := hCOop dt R e hlk hder
  have h' : ReachedByW3d2 (σ.removeLoggedRules S t) S (T.erase t) :=
    ReachedByW3d2.remove t hadm hdrain hSVT hBS hTS hterm h
  have hσS : σ.schema = S := reachedByW3d2_schema h
  have hσ'S : (σ.removeLoggedRules S t).schema = S := by
    rw [removeLoggedRules_schema, hσS]
  obtain ⟨σ0, h0, hsh⟩ := reachedByW3d2_shadow_d h hNK hCD hDAB hSVD hterm hWF hBS
  obtain ⟨σ0', h0', hsh'⟩ := reachedByW3d2_shadow_d h' hNK hCD hDAB hSVDe hterme hWF hBSe
  have hclσ := reachedByW3d2_edgesClosed h
  have htp := reachedByW3d2_edges_target_plain h hBS
  -- no closure member of the untainted-key tuple targets any derived node
  have hneOp : ∀ r', isDerived S (dt, r') = true →
      objNode t.object t.relation ≠ objNode ⟨dt, on⟩ r' := by
    intro r' hd' heq
    have htype : t.object.type = dt := by
      simpa [objNode_type] using congrArg NodeKey.type heq
    have hrel : t.relation = r' := by
      simpa [objNode_pred] using congrArg NodeKey.pred heq
    rw [htype, hrel, hd'] at htu
    exact Bool.noConfusion htu
  -- collapse at each derived operand key, on both sides of the leg
  have hcolOps : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) ∧
      (∀ u, NReaches (σ.removeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.removeLoggedRules S t).edges) := by
    intro r' hr' hd'
    have hpre : ∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges :=
      fun u hu => reachedByW3d2_reach_collapse_root_d hWF hDAB hSVD hd' h hu
    refine ⟨hpre, ?_⟩
    intro u hu
    have hpreu : (u, objNode ⟨dt, on⟩ r') ∈ σ.edges :=
      hpre u (NReaches.mono_subset (removeLoggedRules_edges_subset σ S t) hu)
    exact (removeLeg_derived_inedges_eq_d hd' (hneOp r' hd') u).mpr hpreu
  -- operand settledness transports to the post state / post store
  have hops' : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S (T.erase t) (σ.removeLoggedRules S t) dt on r' ∧
      CompleteKey S (T.erase t) (σ.removeLoggedRules S t) dt on r' ∧
      (∀ u, NReaches (σ.removeLoggedRules S t).edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ (σ.removeLoggedRules S t).edges) := by
    intro r' hr' hd'
    obtain ⟨e', hlk'⟩ := isDerived_declared hd'
    have hco' : ComputedOnly e' := hCOop_e r' hr' hd' e' hlk'
    have hleafUnt' := hLU2 dt R e hlk hder r' hr' hd' e' hlk'
    have hsem_op : ∀ x : SubjectRef, (x.name = STAR → x.predicate = BARE) →
        sem S (T.erase t) ⟨x, r', ⟨dt, on⟩⟩ = sem S T ⟨x, r', ⟨dt, on⟩⟩ :=
      fun x hx => removeLeg_sem_stable_sh_d hWF hTT hNK hR hSVD hBS hTS hMatch
        hStrat hterm ht h0 hsh h0' hsh' hclσ htp hlk' hd' hco' hleafUnt'
        (hopsUnmapped r' hr' hd') hx hon
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨settledKey_removeLeg_sem_d hNK honT hWSbare hd' hon
        (hopsUnmapped r' hr' hd') hsem_op hset,
      completeKey_removeLeg_sem_d hNK honT hWSbare hd' hon
        (hopsUnmapped r' hr' hd') hsem_op hcomp,
      (hcolOps r' hr' hd').2⟩
  have hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) := by
    intro r' hr' hd'
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨hset, hcomp, (hcolOps r' hr' hd').1⟩
  have hLU2e : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false :=
    fun r' hr' hd' e' hlk' => hLU2 dt R e hlk hder r' hr' hd' e' hlk'
  -- the erased tuple misses the key's grant window (its key is untainted)
  have hneKey : ¬ (t.relation = R ∧ t.object.type = dt ∧
      (t.object.name = on ∨ t.object.name = STAR)) := by
    rintro ⟨h1, h2, -⟩
    rw [h2, h1, hder] at htu
    exact Bool.noConfusion htu
  calc sem S (T.erase t) ⟨s, R, ⟨dt, on⟩⟩
      = (σ.removeLoggedRules S t).checkFnR (T.erase t) s dt on R e :=
        (checkFnR_eq_sem_settled_d_filt hWF hTT hNK hR hSVDe hBSe hTSe hMatch hStrat
          hterme hWSbare h0' hsh' hσ'S hlk hder hcd hba hCOop_e hLU2e hops' hs hon).symm
    _ = (σ.removeLoggedRules S t).checkFnR T s dt on R e :=
        checkFnR_erase_irrel_cd hcd hba hon hneKey
    _ = σ.checkFnR T s dt on R e :=
        removeLeg_checkFnR_stable_d T hNK honT hσS hclσ htp hlk hder hcd hba
          hcolOps hon hunmapped hopsUnmapped s
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFnR_eq_sem_settled_d_filt hWF hTT hNK hR hSVD hBS hTS hMatch hStrat
          hterm hWSbare h0 hsh hσS hlk hder hcd hba hCOop_e hLU2e hops hs hon

end Zanzibar
