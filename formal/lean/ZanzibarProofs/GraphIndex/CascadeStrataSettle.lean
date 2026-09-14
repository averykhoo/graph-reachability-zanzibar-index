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
derived branch). This is the guard form
`index_v4/processor.py::DeltaProcessor._reconcile` actually evaluates at a
stratum-2 key once round 1 has re-settled its stratum-1 operands
(`index_v4/processor.py::_EvalContext` routing;
`::DeltaProcessor._run_cascade`'s per-round key loop).

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
    exact edgesClosed_foldl_writeBridgedOne (rewriteClosureL S (rawWriteTuples S t)) σp ih ab hab
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
    rcases foldl_writeBridgedOne_edges_sound (rewriteClosureL S (rawWriteTuples S t)) hab
      with hold | ⟨u, hu, _, h2⟩ | ⟨hbr, h2⟩
    · exact ih hWF (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) a b hold
    · rw [h2, objNode_pred]
      -- OBLIGATION (F), W3d-2 twin: the L lemma is a drop-in at the same premises.
      exact rewriteClosureL_rel_ne_bare hWF hSV List.mem_cons_self hu
    · -- ★ `P6` step 3b: a bridge target inherits its source's predicate, which
      -- `isSubjectWildcardUserset`'s OUTER guard keeps off `BARE`.
      rw [h2]
      show (wAnyNode (a.type, a.pred)).pred ≠ BARE
      exact (bridgedInConcrete_elim hbr).2.2.1
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

/-- **No W3d-2 edge target is a `wAll` node** on `BareStarStore` stores (the fan-out
    fence, as in `reachedByW3d_edges_target_plain`).

    ★★ **RESTATED by `P6` step 3b (2026-09-14) — the W3d-2 twin of
    `CascadeStable.lean::reachedByW3d_edges_target_plain`, and it goes hard-FALSE for the
    same reason**: a bridge target is `wAnyNode …`, hence not `plain`. The name is NOT
    audited here (unlike the W3d one), so only the statement moved. `≠ wAll` is what all six
    consumers actually feed to `DirectCorrect.lean::nreaches_target_variant_ne`. -/
theorem reachedByW3d2_edges_target_plain {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    BareStarStore T → ∀ ab ∈ σ.edges, ab.2.variant ≠ Variant.wAll := by
  induction h with
  | empty S =>
    intro _ ab hab
    simp [emptyState] at hab
  | @write σp S T t hadm hprev ih =>
    intro hBS ab hab
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hab
    obtain ⟨a, b⟩ := ab
    rcases foldl_writeBridgedOne_edges_sound (rewriteClosureL S (rawWriteTuples S t)) hab
      with hold | ⟨w, hw, _, h2⟩ | ⟨_, h2⟩
    · exact ih (fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')) (a, b) hold
    · show b.variant ≠ Variant.wAll
      have hwo : w.object.name ≠ STAR := by
        rw [rewriteClosureL_object hw]
        exact (hBS t List.mem_cons_self).2
      rw [h2, objNode_plain hwo]
      exact Variant.noConfusion
    · -- ★ `P6` step 3b: a bridge target is `wAny`, which is not `wAll`.
      show b.variant ≠ Variant.wAll
      rw [h2]
      exact Variant.noConfusion
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
          show b.variant ≠ Variant.wAll
          rw [h2, objNode_plain hon]
          exact Variant.noConfusion
      · obtain ⟨_, _, _, _, _, _, _, _, hon⟩ := hjv2 j hj
        show b.variant ≠ Variant.wAll
        rw [h2, objNode_plain hon]
        exact Variant.noConfusion
    · exact ih hBS ab hab

/-- **Every in-edge source at a derived R-node is bare** on a W3d-2
    state (write legs never land there — model-level I5; cascade edges are sourced
    at bare candidates in BOTH rounds). -/
theorem reachedByW3d2_Rnode_source_bare {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {e : Expr}
    (h : ReachedByW3d2 σ S T) :
    WF S →
    S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e →
    StoreValidRules S T →
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE := by
  -- `WF S` is new (step 4c-ii): `writeLeg_derived_inedges_eq` needs it post-flip.
  induction h with
  | empty S =>
    intro _ _ _ _ _ x hx
    simp [emptyState] at hx
  | @write σp S T t hadm hprev ih =>
    intro hWF hlk hder hco hSV x hx
    rw [writeLeg_derived_inedges_eq hWF hSV hlk hder hco x] at hx
    exact ih hWF hlk hder hco (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) x hx
  | @remove σp S T t _ _ hSVT _ _ _ _ ih =>
    intro hWF hlk hder hco _ x hx
    exact ih hWF hlk hder hco hSVT x (mem_removeLoggedRules_edges hx)
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro hWF hlk hder hco hSV x hx
    unfold runCascade2 at hx
    split at hx
    · have hx' : (x, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T
          (reconcileJobsLR S T σp jobs1) jobs2).edges := hx
      rcases reconcileJobsLR_edge_sound jobs2 _ x _ hx' with hmid | ⟨j, hj, c, hc, h1, _⟩
      · rcases reconcileJobsLR_edge_sound jobs1 σp x _ hmid
          with hold | ⟨j, hj, c, hc, h1, _⟩
        · exact ih hWF hlk hder hco hSV x hold
        · obtain ⟨_, hcb, _⟩ := hjv1 j hj
          rw [h1, subjNode_pred]
          exact hcb c hc
      · obtain ⟨_, hcb, _⟩ := hjv2 j hj
        rw [h1, subjNode_pred]
        exact hcb c hc
    · exact ih hWF hlk hder hco hSV x hx

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
    (reachedByW3d2_Rnode_source_bare h hWF hlk hder hco hSV x hxv)

/-! ## The untainted-core shadow over the two-round chain

The routed pass writes the same fields the unrouted one does — the guard swap never
changes which state components a fold branch touches — so the W3d-1b shadow
transport mirrors verbatim: pass edges are `DerNode`-targeted, removals never hit
shadow edges, sources stay bare. -/

/-- One routed LOGGED pass preserves the shadow (the emission row is
    edge/node-inert; mirror of `untaintedShadow_applyD`).

    **PRE-WIDENED (4c-ii step 8, 2026-09-01e), and this declaration is why the step's
    first-wave error count was a LOWER bound.** Lean does not build dependents of a
    failed module, so the 2026-09-01d flip probe — which stopped at
    `CascadeStable.lean` — never compiled this file at all and could not see it. It was
    measured this session by stubbing the four unowned obligations with `sorry` so the
    build reached here. Two errors in this declaration and two in
    `::untaintedShadow_applyLoggedR_d` — the same `Invalid ⟨…⟩` (build the extras
    witness) / `unsolved goals` (destructure it) pair as `untaintedShadow_applyD`, one
    at each of the two steps repaired below. (The probe's line numbers are recorded in
    the session entry and are NOT the landed ones — this edit moved them.)

    Repaired the same way and for the same reason — step 5's
    `first | <post-flip form> | <today's form>` idiom, no new declaration, no signature
    change, no call-site churn. ⚠ Unlike `untaintedShadow_applyD` this name carries **no**
    `Audit.lean` `#print axioms` row, so a rename here would be silently unpinned rather
    than caught by the gate; do not rename it.

    ⚠ The post-flip alternative is dead code today and no weakening can reach it (scope
    doc §11.13 trap (k)). Its control is the flip probe, whose 2026-09-01e run took this
    file from 8 errors in 4 declarations to 4 in 2 — the two remaining being the `hsubj`
    sites, which are blocked, not free. -/
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
  -- **PRE-WIDENED (4c-ii step 8).** The subject-side obligation at the POST-FLIP extras
  -- predicate, with zero new premises: `hcb` (a `W3cJobValid` conjunct) makes every
  -- candidate's predicate `BARE`, which `Leaf.lean::bare_subjNode_not_leafNode` refutes
  -- `LeafNode` from outright. Mirror of `CascadeStable.lean::untaintedShadow_applyD`.
  -- ★ `P6` step 3b step 8 (2026-09-14): the `BridgeNode` disjunct, free from the SAME
  -- `hcb` -- a cascade candidate's subject node has predicate `BARE`, and a bridge node's
  -- does not (`bridgeNode_elim`, off `isSubjectWildcardUserset`'s outer guard).
  have hoffW : ∀ c ∈ j.cands,
      ¬ (DerNode S (subjNode c) ∨ LeafNode S (subjNode c)
        ∨ BridgeNode S (subjNode c)) := by
    rintro c hc (⟨dt, on, R, _, hRne', _, hkey⟩ | hleaf | hbr)
    · have hp : R = c.predicate := by
        have := congrArg NodeKey.pred hkey.symm
        simpa [objNode_pred, subjNode_pred] using this
      rw [hcb c hc] at hp
      exact hRne' hp
    · exact bare_subjNode_not_leafNode (hcb c hc) hleaf
    · refine (bridgeNode_elim hbr).2.2.1 ?_
      rw [subjNode_pred]
      exact hcb c hc
  refine ⟨?_, ?_, ?_, ?_, hsh.closed0, ?_⟩
  · -- classify
    intro ab hab
    obtain ⟨a, b⟩ := ab
    rcases hsound a b hab with hold | ⟨c, _, _, h2⟩
    · exact hsh.classify (a, b) hold
    · first
      | exact Or.inr (Or.inl ⟨j.dt, j.on, j.R, hder, hRne, hon, h2⟩)
      | exact Or.inr ⟨j.dt, j.on, j.R, hder, hRne, hon, h2⟩
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
    · subst h1
      exact hoffW c hc hk

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

/-- **The store-summed plain/leaf-routed bridge.** `count_edgeOfTuple_closureL_of_notLeaf`
    (`CascadeStrata.lean:1419`) at ONE tuple, summed over the store: away from a minted leaf
    name and away from a public derived name, `untOccCount` (post-R5 the LEAF-ROUTED sum)
    equals the PLAIN-closure sum.

    ⚠ **Why this exists, and why it is not a guard-weakening.** R5 moved `untOccCount` onto
    the leaf-routed closure because that is what BOTH legs now fold; the shadow rebuild
    `σ0` (`ReachedByRulesAdmitted` / `GraphState.writeRules`) is deliberately NOT re-pointed,
    so its edge multiset is still the plain sum. The two therefore differ at leaf-named
    targets, and the honest way across is this bridge — not re-pointing `σ0` (which would
    break the `RulesComplete`/`RulesWrite` development) and not forking `untOccCount` per
    leg. The guards here describe the SHADOW's own edge shape (a `σ0` edge target is never
    leaf-named: store relations are declared, hence dot-free, and plain rule outputs are
    non-leaf), so they are not fencing out a counterexample to an invariant. -/
theorem untOccCount_eq_plainOcc_of_notLeaf {S : Schema}
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hnd : ∀ r ∈ schemaRewrites S, isDerived S (r.objectType, r.matchRel) = false)
    (a b : NodeKey)
    (hlp : isLeafPred b.pred = false)
    (hbd : isDerived S (b.type, b.pred) = false) :
    ∀ T : Store,
      untOccCount S T a b = ((T.flatMap (rewriteClosure S)).map edgeOfTuple).count (a, b) := by
  intro T
  induction T with
  | nil => rfl
  | cons t T' ih =>
    unfold untOccCount at ih ⊢
    simp only [List.flatMap_cons, List.map_append, List.count_append]
    rw [ih, count_edgeOfTuple_closureL_of_notLeaf hmd hnd t a b hlp hbd]

/-- **The admitted-rebuild count bridge.** On a rules-admitted state, an edge `(a,b)` is
    present iff its occurrence count over the store's rewrite closures is positive: forward by
    `reachedByRules_edge_sound` (the edge materialises a closure tuple), backward by
    `reachedByRulesAdmitted_edge_complete` (a materialised closure edge is present). This is the
    membership↔`untOccCount` characterisation for the fresh rebuild `σ0'`.

    **R5 cost, paid honestly.** `σ0` folds the PLAIN closure (envelope (viii) leaves
    `ReachedByRulesAdmitted` un-re-pointed) while `untOccCount` now sums the leaf-routed one,
    so the two guards `hlp`/`hbd` and the threaded `hmd`/`hnd` are what carry the statement
    across `untOccCount_eq_plainOcc_of_notLeaf`. `hmd` is `LeafScope.matchNotLeaf` and `hnd`
    is `RewriteMatchDeclared`'s second component — both already reach every call site through
    `GraphAdmission.leafScope`/`.matchDecl`, so no headline gains a fresh binder. -/
theorem mem_edges_iff_untOccCount_pos {σ0 : GraphState} {S : Schema} {T : Store}
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hnd : ∀ r ∈ schemaRewrites S, isDerived S (r.objectType, r.matchRel) = false)
    (h0 : ReachedByRulesAdmitted σ0 S T) (a b : NodeKey)
    (hlp : isLeafPred b.pred = false)
    (hbd : isDerived S (b.type, b.pred) = false) :
    (a, b) ∈ σ0.edges ↔ 0 < untOccCount S T a b := by
  rw [untOccCount_eq_plainOcc_of_notLeaf hmd hnd a b hlp hbd T]
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

/-- A DECLARED relation name is dot-free (`WF.relNames`), hence never a minted leaf name.
    The store-shape half of the R5 shadow bridge, and the Lean image of Python's
    `zanzibar_utils_v1.py::_validate_ast_references::check_name`, which raises iff
    `'.' in name and name != '...'`. -/
theorem isLeafPred_relation_false_of_lookup {S : Schema} (hWF : WF S) {t : Tuple} {e : Expr}
    (hlk : S.lookup (t.object.type, t.relation) = some e) : isLeafPred t.relation = false := by
  have hk : (t.object.type, t.relation) ∈ S.keys := by
    by_contra hno
    rw [lookup_eq_none S hno] at hlk
    simp at hlk
  exact isLeafPred_eq_false_of_relNameOK (relNameOK_of_mem_keys hWF hk)

/-- **A rules-admitted shadow edge never TARGETS a minted leaf name.** The plain-closure
    rebuild `σ0` materialises exactly two kinds of tuple, and neither carries a dotted
    relation: a STORE tuple (`hSN`), or a PLAIN rule output, which
    `not_isLeafPred_outRel_of_mem_schemaRewrites` pins non-leaf.

    **Added by R5**, and it is what makes the `untOccCount` guards on
    `mem_edges_iff_untOccCount_pos` discharge-able rather than assumed: the shadow's own
    edge shape supplies them. Note this is a statement about the PLAIN rebuild only — the
    leaf-routed legs DO mint leaf targets, which is the whole point of the flip. -/
theorem reachedByRulesAdmitted_untStore_edge_notLeaf {σ0 : GraphState} {S : Schema}
    {T : Store} (hWF : WF S) (hSN : ∀ t' ∈ T, isLeafPred t'.relation = false)
    (h0 : ReachedByRulesAdmitted σ0 S T) :
    ∀ a b, (a, b) ∈ σ0.edges → isLeafPred b.pred = false := by
  intro a b hab
  obtain ⟨t', ht', u, hu, _hasub, hbobj⟩ :=
    reachedByRules_edge_sound (reachedByRules_of_admitted h0) a b hab
  have hrel : b.pred = u.relation := by rw [hbobj, objNode_pred]
  rw [hrel]
  rcases rewriteClosure_produced hu with heq | ⟨r, hr, _hro, hrout⟩
  · -- the member is the STORE tuple itself
    rw [heq]; exact hSN t' ht'
  · -- the member is a PLAIN rule output: never a minted leaf name
    rw [← hrout]
    exact not_isLeafPred_outRel_of_mem_schemaRewrites hWF hr

/-- The `StoreValidRules` corollary: a store tuple's relation is a DECLARED key
    (`StoreValidRules` hands back a `lookup`), and a declared relation name is dot-free by
    `WF.relNames`, hence not a minted leaf name. -/
theorem reachedByRulesAdmitted_edge_target_notLeaf {σ0 : GraphState} {S : Schema} {T : Store}
    (hWF : WF S) (hSV : StoreValidRules S T)
    (h0 : ReachedByRulesAdmitted σ0 S T) :
    ∀ a b, (a, b) ∈ σ0.edges → isLeafPred b.pred = false :=
  reachedByRulesAdmitted_untStore_edge_notLeaf hWF
    (fun t' ht' => by
      obtain ⟨e, _rs, hlk, _, _⟩ := hSV t' ht'
      exact isLeafPred_relation_false_of_lookup hWF hlk) h0

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

/-- ★ **No edge of the PLAIN admitted rebuild targets a `wAny` node.** ★ ADDITIVE, `P6` step
    3b (2026-09-14).

    `ReachedByRulesAdmitted` folds `RulesWrite.lean::GraphState.writeRules`, which is
    deliberately left UNBRIDGED — so every one of its edges is some closure member's
    `edgeOfTuple`, whose target is an `objNode` (`State.lean::objNode_ne_wAny`). That is the
    whole proof, and it is what lets the remove-leg shadow transport keep using the R3 count
    law after that law gained a `b.variant ≠ Variant.wAny` scope: on the σ0 SIDE the scope is
    free, because σ0 is the side that does not bridge. **The asymmetry the design chose is
    what pays for it here.** -/
theorem reachedByRulesAdmitted_edge_target_ne_wAny {σ0 : GraphState} {S : Schema} {T : Store}
    (h : ReachedByRulesAdmitted σ0 S T) :
    ∀ a b, (a, b) ∈ σ0.edges → b.variant ≠ Variant.wAny := by
  induction h with
  | empty S => intro a b hab; simp [emptyState] at hab
  | @step σ S T t hprev hadm ih =>
    intro a b hab
    have hab' : (a, b) ∈ ((rewriteClosure S t).foldl
        (fun acc (u : Tuple) => GraphState.writeDirect acc u) σ).edges := hab
    rcases foldl_writeDirect_edges_sound (rewriteClosure S t) hab' with hold | ⟨u, _, _, h2⟩
    · exact ih a b hold
    · rw [h2]; exact objNode_ne_wAny u.object u.relation

/-- **`untaintedShadow_removeLeg`** — the R5b-ii shadow-transport crux. Given a `ReachedByW3d2`
    state `σp` with prior untainted-core shadow `σ0` over `T`, and R5a's fresh admitted rebuild
    `σ0'` over `T.erase t` (edges ⊆ `σ0`'s, from `exists_admitted_erase`), the logged retraction
    `σp.removeLoggedRules S t` is shadowed by `σ0'`. The untainted edge SETS agree by the count
    argument (`count_removeLoggedRules` + `reachedByW3d2_untOccCount` + `untOccCount_erase` land
    both on `untOccCount S (T.erase t)`, bridged to membership on each side); the derived edges
    are untouched by the retraction (`mem_removeLoggedRules_edges`) and stay `DerNode`-classified
    from `σ0` via the prior shadow. -/
theorem untaintedShadow_removeLeg {σp σ0 σ0' : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hLS : LeafScope S) (hMatch : RewriteMatchDeclared S)
    (hrb : ReachedByW3d2 σp S T)
    (hsh : UntaintedShadow S σp σ0)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    (hadm : RemoveAdmits σp T t)
    (h0' : ReachedByRulesAdmitted σ0' S (T.erase t))
    (hsub : ∀ e ∈ σ0'.edges, e ∈ σ0.edges)
    (hSV : StoreValidRules S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) :
    UntaintedShadow S (σp.removeLoggedRules S t) σ0' := by
  -- **R5**: `hLS`/`hMatch` are the two components `mem_edges_iff_untOccCount_pos` needs to
  -- cross from the PLAIN shadow rebuild to the leaf-routed `untOccCount`. They are threaded
  -- (`GraphAdmission.leafScope` / `.matchDecl`), not assumed fresh.
  have hWF : WF S := hLS.wf
  have hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false := hLS.matchNotLeaf
  have hnd : ∀ r ∈ schemaRewrites S, isDerived S (r.objectType, r.matchRel) = false :=
    fun r hr => (hMatch r hr).2
  have ht : t ∈ T := hadm
  have hSV' : StoreValidRules S (T.erase t) :=
    fun t' ht' => hSV t' (List.mem_of_mem_erase ht')
  have hnodes : (σp.removeLoggedRules S t).nodes = σp.nodes := removeLoggedRules_nodes σp S t
  have hmem0' : ∀ a b, isLeafPred b.pred = false → isDerived S (b.type, b.pred) = false →
      ((a, b) ∈ σ0'.edges ↔ 0 < untOccCount S (T.erase t) a b) :=
    fun a b hlp hbd => mem_edges_iff_untOccCount_pos hmd hnd h0' a b hlp hbd
  have hσ0unt : ∀ a b, (a, b) ∈ σ0.edges → isDerived S (b.type, b.pred) = false :=
    reachedByRulesAdmitted_edge_target_untainted hSV hCO h0
  have hσ0'unt : ∀ a b, (a, b) ∈ σ0'.edges → isDerived S (b.type, b.pred) = false :=
    reachedByRulesAdmitted_edge_target_untainted hSV' hCO h0'
  have hσ0nl : ∀ a b, (a, b) ∈ σ0.edges → isLeafPred b.pred = false :=
    reachedByRulesAdmitted_edge_target_notLeaf hWF hSV h0
  have hσ0'nl : ∀ a b, (a, b) ∈ σ0'.edges → isLeafPred b.pred = false :=
    reachedByRulesAdmitted_edge_target_notLeaf hWF hSV' h0'
  -- the untainted count on the retracted state lands on `untOccCount S (T.erase t)`
  -- ★ `P6` step 3b (2026-09-14): the R3 count law is now scoped off the `wAny` targets, so
  -- this local equivalence carries the same guard. It costs NOTHING at either consumer
  -- below, because both approach it from the σ0 side, where
  -- `reachedByRulesAdmitted_edge_target_ne_wAny` supplies it for free.
  have hmemrem : ∀ a b, isDerived S (b.type, b.pred) = false → b.variant ≠ Variant.wAny →
      ((a, b) ∈ (σp.removeLoggedRules S t).edges ↔ 0 < untOccCount S (T.erase t) a b) := by
    intro a b hb hbv
    have hcount : (σp.removeLoggedRules S t).edges.count (a, b)
        = untOccCount S (T.erase t) a b := by
      rw [count_removeLoggedRules (a, b) hbv S t σp,
        reachedByW3d2_untOccCount hrb a b hb hbv,
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
      have hbv : b.variant ≠ Variant.wAny :=
        reachedByRulesAdmitted_edge_target_ne_wAny h0 a b h0e
      exact Or.inl ((hmem0' a b (hσ0nl a b h0e) hbunt).mpr ((hmemrem a b hbunt hbv).mp hab))
    · exact Or.inr hD
  · -- sub
    intro ab hab
    obtain ⟨a, b⟩ := ab
    have hbunt : isDerived S (b.type, b.pred) = false := hσ0'unt a b hab
    have hbv : b.variant ≠ Variant.wAny :=
      reachedByRulesAdmitted_edge_target_ne_wAny h0' a b hab
    exact (hmemrem a b hbunt hbv).mpr ((hmem0' a b (hσ0'nl a b hab) hbunt).mp hab)
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
    derived R-nodes. Mirror of `reachedByW3d_shadow` over the two-round legs.

    ADDED BY THE FLIP: `LeafScope S` and `BareStarStore T`, exactly as at
    `CascadeStable.lean::reachedByW3d_shadow` — see there for what each discharges. The
    `remove` constructor supplies the store premise for its own recursive call (`hBST`), so
    the store-level addition costs one binder rename and no new hypothesis on the chain.
    ⚠ `TtuTargetsSat S NotLeafName` is now DEAD here too; same note as at that site. -/
theorem reachedByW3d2_shadow {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    NodupKeys S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
    StoreValidRules S T →
    (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) →
    TtuTargetsSat S NotLeafName →
    DirectRestrictionsNotLeaf S →
    LeafScope S →
    -- **R5**: the remove case's shadow transport crosses the PLAIN rebuild to the
    -- leaf-routed `untOccCount`, which needs `RewriteMatchDeclared`'s untaintedness
    -- component (threaded from `GraphAdmission.matchDecl`; not a fresh assumption).
    RewriteMatchDeclared S →
    BareStarStore T →
    -- ★ `P6` step 3b step 8, W3d-2 twin (2026-09-14): the three carries the widened extras
    -- predicate costs. `NoBridgedDerived` is `T1`; `TtuTuplesetsDirect` + `TtuStarFree` are
    -- `T3`'s two binders, both already bound at every call site.
    NoBridgedDerived S →
    TtuTuplesetsDirect S →
    TtuStarFree S T →
    ∃ σ0, ReachedByRulesAdmitted σ0 S T ∧ UntaintedShadow S σ σ0 := by
  induction h with
  | empty S =>
    intro _ _ _ _ _ _ _ _ _ _ _ _
    refine ⟨emptyState S, ReachedByRulesAdmitted.empty S, ?_, ?_, ?_, ?_, ?_, ?_⟩
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k hk; simp [emptyState] at hk
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k _ y hy; simp [emptyState] at hy
  | @write σp S T t hadm hprev ih =>
    intro hNK hCO hSV hterm hQ hDR hLS hMatch hBS hNBD hTT hTS
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO
      (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht'))
      (fun dt R hder => ⟨(hterm dt R hder).1,
        fun t' ht' => (hterm dt R hder).2 t' (List.mem_cons_of_mem _ ht')⟩)
      hQ hDR hLS hMatch (fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht'))
      hNBD hTT (fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht'))
    -- ══ THE FLIP (step 4c-ii), W3d-2 twin of `CascadeStable.lean::reachedByW3d_shadow`'s
    -- write leg. Identical structure and identical discharges; see there for the reasoning
    -- behind each of the three (the plain-list `hsubjW` is likewise deleted, not kept).
    have hunt : isDerived S (t.object.type, t.relation) = false := by
      obtain ⟨e, rs, hlk, hrs, _⟩ := hSV t List.mem_cons_self
      by_contra hcon
      rw [Bool.not_eq_false] at hcon
      rw [exprDirects_computedOnly (hCO _ _ _ hlk hcon)] at hrs
      simp at hrs
    have hsubL : ∀ u ∈ rewriteClosure S t, u ∈ rewriteClosureL S (rawWriteTuples S t) :=
      fun _ hu => rewriteClosure_subset_rewriteClosureL (mem_rawWriteTuples_self hunt) hu
    -- OBLIGATION (D) — DISCHARGED from `hLS.noLeafSubjects`.
    have hsubjWL0 : ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
        ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject)) :=
      writeLegSubjectsWide_L hLS.noLeafSubjects hterm
        (noLeafStoreSubjects_of_storeValidRules hDR hSV t List.mem_cons_self)
    -- ★ `T3`, W3d-2 twin: no closure member's subject is a bridge node.
    have hsubjWL : ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
        ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject)
          ∨ BridgeNode S (subjNode u.subject)) := by
      intro u hu hc
      rcases hc with hc | hc | hc
      · exact hsubjWL0 u hu (Or.inl hc)
      · exact hsubjWL0 u hu (Or.inr hc)
      · exact not_bridgeNode_of_star_bare hNK hCO hLS.matchNotLeaf hTT hTS hBS
          (t := t) List.mem_cons_self hu hc
    have hTshadow : ∀ ty p, S.isSubjectWildcardUserset ty p = true →
        (DerNode S (wAnyNode (ty, p)) ∨ LeafNode S (wAnyNode (ty, p))
          ∨ BridgeNode S (wAnyNode (ty, p))) :=
      fun ty p hx => Or.inr (Or.inr (bridgeNode_wAnyNode hx))
    have hSshadow : ∀ k : NodeKey, k.variant = Variant.plain →
        S.isSubjectWildcardUserset k.type k.pred = true →
        ¬ (DerNode S k ∨ LeafNode S k ∨ BridgeNode S k) := by
      intro k hkv hksw hc
      rcases hc with ⟨dt, on, R, hder', _, hon', rfl⟩ | hleaf | hbr
      · rw [objNode_type, objNode_pred] at hksw
        rw [hNBD dt R hder'] at hksw
        exact Bool.noConfusion hksw
      · have hnl : ¬ NotLeafName k.pred := fun hx => not_leafNode_of_notLeafName hx hleaf
        rw [isSubjectWildcardUserset_false_of_notLeafName hNK hCO hQ hDR hnl] at hksw
        exact Bool.noConfusion hksw
      · exact Variant.noConfusion (hkv ▸ (bridgeNode_elim hbr).1)
    -- OBLIGATION (E), object half — DISCHARGED.
    have hextraL := writeLegExtrasWide_L (t := t) hLS (hBS t List.mem_cons_self).2
    -- OBLIGATION (E), admission half — DISCHARGED (transfer on the L list, restrict at σ0).
    have hadmVL : FoldAdmits σ0 (rewriteClosureL S (rawWriteTuples S t)) :=
      untaintedShadow_foldAdmits hTshadow hSshadow (rewriteClosureL S (rawWriteTuples S t))
        σp σ0 hsh (reachedByW3d2_schema hprev) hsubjWL hadm
    have hadmV : FoldAdmits σ0 (rewriteClosure S t) :=
      foldAdmits_plain_of_L h0 hadmVL hsubL
    exact ⟨σ0.writeRules S t,
      ReachedByRulesAdmitted.step t h0 hadmV,
      untaintedShadow_writeLegL hTshadow hSshadow (rewriteClosureL S (rawWriteTuples S t))
        (rewriteClosure S t) σp σ0 hsh (reachedByW3d2_schema hprev)
        hsubjWL hextraL hsubL hadm hadmV⟩
  | @remove σp S T t hadm _ hSVT hBST hTST htermT hprev ih =>
    intro hNK hCO _ _ hQ hDR hLS hMatch _ hNBD hTT _
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hSVT htermT hQ hDR hLS hMatch hBST hNBD hTT hTST
    obtain ⟨σ0', h0', hsub⟩ := exists_admitted_erase h0 t
    exact ⟨σ0', h0',
      untaintedShadow_removeLeg hLS hMatch hprev hsh h0 hadm h0' hsub hSVT hCO⟩
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ hprev ih =>
    intro hNK hCO hSV hterm hQ hDR hLS hMatch hBS hNBD hTT hTS
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hSV hterm hQ hDR hLS hMatch hBS hNBD hTT hTS
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
  have hraw : rewriteClosureRaw S t = [t] := by
    unfold rewriteClosureRaw
    show rewriteClosureAux S (S.keys.length + 1) [t] = [t]
    rw [rewriteClosureAux]
    have hfm : List.flatMap (rewriteStep S) [t] = [] := by simp [hstep]
    rw [hfm, rewriteClosureAux_nil]
    rfl
  unfold rewriteClosure
  rw [hraw]
  simp

/-- Splitting the store-closure occurrence count at a cons head. -/
theorem untOccCount_cons (S : Schema) (t : Tuple) (T : Store) (a b : NodeKey) :
    untOccCount S (t :: T) a b
      = ((rewriteClosureL S (rawWriteTuples S t)).map edgeOfTuple).count (a, b)
          + untOccCount S T a b := by
  unfold untOccCount
  rw [List.flatMap_cons, List.map_append, List.count_append]

/-- **Filter-invariance of the untainted occurrence count.** For an UNTAINTED, NON-LEAF
    target `b`, dropping the derived-key tuples changes no `(a,b)` occurrence: a derived-key
    tuple's PLAIN closure is its seed alone (`rewriteClosure_derived_eq_seed_nk`), whose
    materialized edge targets the derived R-node — never the untainted `b`.

    **R5 cost, paid honestly.** Post-R5 `untOccCount` sums the LEAF-ROUTED closure, and a
    derived-key tuple no longer contributes NOTHING there — it contributes its minted LEAF
    edges, and a leaf name passes the derived guard `hb` (a minted name is not a declared
    key). So the `hzero` step now goes through `count_edgeOfTuple_closureL_of_notLeaf`
    first, which is exactly why `hlp : isLeafPred b.pred = false` and the threaded
    `hmd`/`hnd` are new hypotheses here.

    ⚠ **Why this is a legitimate strengthening and not the house failure mode.** The
    dropped instances (leaf-named `b`) are precisely the ones the retraction now ALSO
    handles, because both legs fold the same list — they are covered by the unguarded R3
    (`reachedByW3d2_untOccCount`) itself, which R5 made true. The guard here describes the
    PLAIN shadow's own edge shape, not a fence around a live counterexample. -/
theorem untOccCount_untaintedFilter {S : Schema} (hNK : NodupKeys S)
    (hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false)
    (hnd : ∀ r ∈ schemaRewrites S, isDerived S (r.objectType, r.matchRel) = false)
    {b : NodeKey}
    (hb : isDerived S (b.type, b.pred) = false)
    (hlp : isLeafPred b.pred = false) (a : NodeKey) :
    ∀ T : Store,
      untOccCount S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) a b
        = untOccCount S T a b := by
  intro T
  induction T with
  | nil => rfl
  | cons t' T' ih =>
    rw [List.filter_cons]
    by_cases hd : isDerived S (t'.object.type, t'.relation) = true
    · have hzero : ((rewriteClosureL S (rawWriteTuples S t')).map edgeOfTuple).count (a, b)
          = 0 := by
        rw [count_edgeOfTuple_closureL_of_notLeaf hmd hnd t' a b hlp hb,
          rewriteClosure_derived_eq_seed_nk hNK hd]
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
    parallel σ0 step.

    **PRE-WIDENED (4c-ii step 5).** `hsubj` is stated at the WIDE extras predicate
    `DerNode ∨ LeafNode` even though `UntaintedShadow` is still `ShadowOver (DerNode S)`:
    the `term` field's obligation at the added edge's source is `¬ Extra`, so it grows
    with the extras when `CascadeStable.lean::UntaintedShadow` is re-pointed. Proving the
    stronger premise now is what makes that re-point a no-op here. The only call site
    (`reachedByW3d2_shadow_d`'s derived-write branch) discharges the new half for free from
    `StoreValidRulesD`'s bare-subject conjunct via `Leaf.lean::bare_subjNode_not_leafNode`.

    `hDer` stays NARROW on purpose — it is a positive producer feeding `classify`'s right
    branch, so it takes the LEFT injection into the widened extras, and widening the
    hypothesis instead would weaken the lemma for nothing. The two extras-dependent steps
    below are written `first | exact … | exact Or.inl …`: today the `Or.inl` alternative
    fires, after the re-point the bare one does, and **the lines do not change**. -/
theorem untaintedShadow_writeLoggedOne_derived {S : Schema} {Sc : Schema}
    {σ σ0 : GraphState}
    (hsh : UntaintedShadow S σ σ0) (hsc : σ.schema = Sc) {u : Tuple}
    (hDer : DerNode S (objNode u.object u.relation))
    (hsubj : ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject)
      ∨ BridgeNode S (subjNode u.subject)))
    (hT : ∀ ty p, Sc.isSubjectWildcardUserset ty p = true →
      (DerNode S (wAnyNode (ty, p)) ∨ LeafNode S (wAnyNode (ty, p))
        ∨ BridgeNode S (wAnyNode (ty, p))))
    (hS : ∀ k : NodeKey, k.variant = Variant.plain →
      Sc.isSubjectWildcardUserset k.type k.pred = true →
      ¬ (DerNode S k ∨ LeafNode S k ∨ BridgeNode S k)) :
    UntaintedShadow S (σ.writeLoggedOne u) σ0 := by
  -- ★ `P6` step 3b step 8 (2026-09-14): same repair as the general
  -- `CascadeStable.lean::untaintedShadow_writeLoggedOne` -- the admission probe moved to
  -- the BRIDGED pre-state, so the shadow has to be established there first.
  have hpre : UntaintedShadow S (σ.bridgePreLogged u) σ0 :=
    untaintedShadow_bridgePreLogged hsh hsc u hT hS
  unfold GraphState.writeLoggedOne
  by_cases hb : (σ.bridgePreLogged u).admitEdge (subjNode u.subject)
      (objNode u.object u.relation) = true
  · rw [if_pos hb]
    have hsubjMem : subjNode u.subject ∈ (σ.bridgePreLogged u).nodes := by
      unfold GraphState.bridgePreLogged
      rw [ensureInBridgesLogged_nodes]
      refine ensureInBridges_mono ?_
      rw [ensureInBridgesLogged_nodes]
      refine ensureInBridges_mono ?_
      rw [addNode_nodes]
      exact List.mem_cons_of_mem _ (by rw [addNode_nodes]; exact List.mem_cons_self)
    have hobjMem : objNode u.object u.relation ∈ (σ.bridgePreLogged u).nodes := by
      unfold GraphState.bridgePreLogged
      rw [ensureInBridgesLogged_nodes]
      refine ensureInBridges_mono ?_
      rw [ensureInBridgesLogged_nodes]
      refine ensureInBridges_mono ?_
      rw [addNode_nodes]
      exact List.mem_cons_self
    refine ⟨?_, ?_, ?_, ?_, hsh.closed0, ?_⟩
    · -- classify
      intro ab hab
      rw [pushDelta_edges, addEdge_edges] at hab
      rcases List.mem_cons.mp hab with heq | hmem
      · refine Or.inr ?_
        rw [heq]
        exact Or.inl hDer
      · exact hpre.classify ab hmem
    · -- sub
      intro ab hab
      rw [pushDelta_edges, addEdge_edges]
      exact List.mem_cons_of_mem _ (hpre.sub ab hab)
    · -- nodesSub
      intro k hk
      rw [pushDelta_nodes, addEdge_nodes]
      exact hpre.nodesSub k hk
    · -- closed
      intro ab hab
      rw [pushDelta_edges, addEdge_edges] at hab
      rw [pushDelta_nodes, addEdge_nodes]
      rcases List.mem_cons.mp hab with heq | hmem
      · exact heq ▸ ⟨hsubjMem, hobjMem⟩
      · exact hpre.closed ab hmem
    · -- term
      intro k hk y hy
      rw [pushDelta_edges, addEdge_edges] at hy
      rcases List.mem_cons.mp hy with heq | hmem
      · have h1 : k = subjNode u.subject := (Prod.ext_iff.mp heq).1
        rw [h1] at hk
        exact hsubj hk
      · exact hpre.term k hk y hmem
  · rw [if_neg hb]
    exact hsh

/-- **The derived-key write LEG keeps the shadow with σ0 FIXED** — the fold form
    (consumed at the singleton closure `[t]` of a derived-key write; stated over any
    all-`DerNode`-targeted batch).

    **PRE-WIDENED (4c-ii step 5)** in lockstep with
    `untaintedShadow_writeLoggedOne_derived`, whose premises it threads verbatim: the
    subject premise is at the wide `DerNode ∨ LeafNode`, the positive target premise stays
    narrow. -/
theorem untaintedShadow_writeLeg_derived {S : Schema} {Sc : Schema}
    (hT : ∀ ty p, Sc.isSubjectWildcardUserset ty p = true →
      (DerNode S (wAnyNode (ty, p)) ∨ LeafNode S (wAnyNode (ty, p))
        ∨ BridgeNode S (wAnyNode (ty, p))))
    (hS : ∀ k : NodeKey, k.variant = Variant.plain →
      Sc.isSubjectWildcardUserset k.type k.pred = true →
      ¬ (DerNode S k ∨ LeafNode S k ∨ BridgeNode S k)) :
    ∀ (us : List Tuple) (σ σ0 : GraphState), UntaintedShadow S σ σ0 → σ.schema = Sc →
      (∀ u ∈ us, DerNode S (objNode u.object u.relation)) →
      (∀ u ∈ us, ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject)
        ∨ BridgeNode S (subjNode u.subject))) →
      UntaintedShadow S (us.foldl (fun acc u => acc.writeLoggedOne u) σ) σ0 := by
  intro us
  induction us with
  | nil => intro σ σ0 hsh _ _ _; exact hsh
  | cons u rest ih =>
    intro σ σ0 hsh hsc hD hs
    simp only [List.foldl_cons]
    exact ih _ _
      (untaintedShadow_writeLoggedOne_derived hsh hsc (hD u List.mem_cons_self)
        (hs u List.mem_cons_self) hT hS)
      (by rw [writeLoggedOne_schema]; exact hsc)
      (fun x hx => hD x (List.mem_cons_of_mem _ hx))
      (fun x hx => hs x (List.mem_cons_of_mem _ hx))

/-- One routed LOGGED pass preserves the shadow, `_d` form: instead of the full-store
    `hSV`/`hCO` route to "no σ0 edge targets the job's R-node"
    (`reachedByRules_derived_no_inedge`), take σ0's edge-target UNTAINTEDNESS directly —
    the filtered-σ0 rebuild supplies it via
    `reachedByRulesAdmitted_untStore_edge_untainted`, no `ComputedOnly` needed.

    **PRE-WIDENED (4c-ii step 8, 2026-09-01e)** — see `untaintedShadow_applyLoggedR`
    above for the measurement and the idiom. Its `hunt` route to `hnojob` is
    extras-independent, so the two repaired steps are exactly the same two. -/
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
  -- **PRE-WIDENED (4c-ii step 8).** The subject-side obligation at the POST-FLIP extras
  -- predicate, with zero new premises: `hcb` (a `W3cJobValid` conjunct) makes every
  -- candidate's predicate `BARE`, which `Leaf.lean::bare_subjNode_not_leafNode` refutes
  -- `LeafNode` from outright. Mirror of `CascadeStable.lean::untaintedShadow_applyD`.
  -- ★ `P6` step 3b step 8 (2026-09-14): the `BridgeNode` disjunct, free from the SAME
  -- `hcb` -- a cascade candidate's subject node has predicate `BARE`, and a bridge node's
  -- does not (`bridgeNode_elim`, off `isSubjectWildcardUserset`'s outer guard).
  have hoffW : ∀ c ∈ j.cands,
      ¬ (DerNode S (subjNode c) ∨ LeafNode S (subjNode c)
        ∨ BridgeNode S (subjNode c)) := by
    rintro c hc (⟨dt, on, R, _, hRne', _, hkey⟩ | hleaf | hbr)
    · have hp : R = c.predicate := by
        have := congrArg NodeKey.pred hkey.symm
        simpa [objNode_pred, subjNode_pred] using this
      rw [hcb c hc] at hp
      exact hRne' hp
    · exact bare_subjNode_not_leafNode (hcb c hc) hleaf
    · refine (bridgeNode_elim hbr).2.2.1 ?_
      rw [subjNode_pred]
      exact hcb c hc
  refine ⟨?_, ?_, ?_, ?_, hsh.closed0, ?_⟩
  · -- classify
    intro ab hab
    obtain ⟨a, b⟩ := ab
    rcases hsound a b hab with hold | ⟨c, _, _, h2⟩
    · exact hsh.classify (a, b) hold
    · first
      | exact Or.inr (Or.inl ⟨j.dt, j.on, j.R, hder, hRne, hon, h2⟩)
      | exact Or.inr ⟨j.dt, j.on, j.R, hder, hRne, hon, h2⟩
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
    · subst h1
      exact hoffW c hc hk

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
    occurrences). Edge-target UNTAINTEDNESS of both rebuilds comes for free from the
    filtered store, so no `ComputedOnly` hypothesis survives.

    ⚠ **R5 CORRECTION to this docstring, which used to say "no `StoreValidRules` … survive".**
    That is no longer true and the reason is worth stating: post-R5 `untOccCount` sums the
    LEAF-ROUTED closure, so both `mem_edges_iff_untOccCount_pos` and
    `untOccCount_untaintedFilter` need `isLeafPred b.pred = false` at the shadow's edge
    targets, and the filter premise `hND` (`isDerived … = false`) does NOT give it: a store
    tuple whose relation is literally `viewer.0` satisfies `hND` (it is not a declared key)
    while its seed edge IS leaf-targeted. So a genuine store-shape premise is required, and
    it is `hSN` below — every store relation is dot-free. That is Python-enforced, not
    assumed: `zanzibar_utils_v1.py::_validate_ast_references`'s `check_name` raises iff
    `'.' in name and name != '...'`, and `TupleSource` admission runs it. `hLS`/`hMatch`
    supply `WF` and the two rewrite-layer components the bridge consumes. -/
theorem untaintedShadow_removeLeg_d {σp σ0 σ0' : GraphState} {S : Schema} {T : Store}
    {t : Tuple}
    (hLS : LeafScope S) (hMatch : RewriteMatchDeclared S)
    (hSN : ∀ t' ∈ T, isLeafPred t'.relation = false)
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
  have hWF : WF S := hLS.wf
  have hmd : ∀ r ∈ schemaRewrites S, isLeafPred r.matchRel = false := hLS.matchNotLeaf
  have hnd : ∀ r ∈ schemaRewrites S, isDerived S (r.objectType, r.matchRel) = false :=
    fun r hr => (hMatch r hr).2
  have hSNf : ∀ t' ∈ T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)),
      isLeafPred t'.relation = false :=
    fun t' ht' => hSN t' (List.mem_of_mem_filter ht')
  have hSNf' : ∀ t' ∈ (T.erase t).filter
        (fun tp => !isDerived S (tp.object.type, tp.relation)),
      isLeafPred t'.relation = false :=
    fun t' ht' => hSN t' (List.mem_of_mem_erase (List.mem_of_mem_filter ht'))
  have hmem0' : ∀ a b, isLeafPred b.pred = false → isDerived S (b.type, b.pred) = false →
      ((a, b) ∈ σ0'.edges ↔
        0 < untOccCount S
          ((T.erase t).filter (fun tp => !isDerived S (tp.object.type, tp.relation))) a b) :=
    fun a b hlp hbd => mem_edges_iff_untOccCount_pos hmd hnd h0' a b hlp hbd
  have hσ0unt : ∀ a b, (a, b) ∈ σ0.edges → isDerived S (b.type, b.pred) = false :=
    reachedByRulesAdmitted_untStore_edge_untainted hND h0
  have hσ0'unt : ∀ a b, (a, b) ∈ σ0'.edges → isDerived S (b.type, b.pred) = false :=
    reachedByRulesAdmitted_untStore_edge_untainted hND' h0'
  have hσ0nl : ∀ a b, (a, b) ∈ σ0.edges → isLeafPred b.pred = false :=
    reachedByRulesAdmitted_untStore_edge_notLeaf hWF hSNf h0
  have hσ0'nl : ∀ a b, (a, b) ∈ σ0'.edges → isLeafPred b.pred = false :=
    reachedByRulesAdmitted_untStore_edge_notLeaf hWF hSNf' h0'
  have hmemrem : ∀ a b, isDerived S (b.type, b.pred) = false → isLeafPred b.pred = false →
      b.variant ≠ Variant.wAny →
      ((a, b) ∈ (σp.removeLoggedRules S t).edges ↔
        0 < untOccCount S
          ((T.erase t).filter (fun tp => !isDerived S (tp.object.type, tp.relation))) a b) := by
    intro a b hb hlp hbv
    have hcount : (σp.removeLoggedRules S t).edges.count (a, b)
        = untOccCount S (T.erase t) a b := by
      rw [count_removeLoggedRules (a, b) hbv S t σp,
        reachedByW3d2_untOccCount hrb a b hb hbv,
        untOccCount_erase S T t a b ht]
      omega
    rw [untOccCount_untaintedFilter hNK hmd hnd hb hlp a (T.erase t), ← hcount,
      List.count_pos_iff]
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩
  · -- classify
    intro ab hab
    obtain ⟨a, b⟩ := ab
    have habp : (a, b) ∈ σp.edges := mem_removeLoggedRules_edges hab
    rcases hsh.classify (a, b) habp with h0e | hD
    · have hbunt : isDerived S (b.type, b.pred) = false := hσ0unt a b h0e
      have hblp : isLeafPred b.pred = false := hσ0nl a b h0e
      have hbv : b.variant ≠ Variant.wAny :=
        reachedByRulesAdmitted_edge_target_ne_wAny h0 a b h0e
      exact Or.inl ((hmem0' a b hblp hbunt).mpr ((hmemrem a b hbunt hblp hbv).mp hab))
    · exact Or.inr hD
  · -- sub
    intro ab hab
    obtain ⟨a, b⟩ := ab
    have hbunt : isDerived S (b.type, b.pred) = false := hσ0'unt a b hab
    have hblp : isLeafPred b.pred = false := hσ0'nl a b hab
    have hbv : b.variant ≠ Variant.wAny :=
      reachedByRulesAdmitted_edge_target_ne_wAny h0' a b hab
    exact (hmemrem a b hbunt hblp hbv).mpr ((hmem0' a b hblp hbunt).mp hab)
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
    `BareStarStore` for its pre-store, and every settled-chain consumer carries `WF`.

    ADDED BY THE FLIP: `LeafScope S`, appended LAST (this theorem's premise order already
    diverges from the plain twin's, and appending keeps the four `_d` call sites a
    one-token edit). `hWF`/`hBS` were already here, which is why the `_d` form needed only
    one new binder where the plain form needed two.
    ⚠ `TtuTargetsSat S NotLeafName` is DEAD in the UNTAINTED-seed branch for the same reason
    as at `CascadeStable.lean::reachedByW3d_shadow`; the DERIVED-seed branch never used it. -/
theorem reachedByW3d2_shadow_d {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    NodupKeys S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOrDirect e) →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → DirectArmsBare e) →
    StoreValidRulesD S T →
    (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) →
    WF S →
    BareStarStore T →
    TtuTargetsSat S NotLeafName →
    DirectRestrictionsNotLeaf S →
    LeafScope S →
    -- **R5**: see `reachedByW3d2_shadow`'s note — the remove case's transport needs it.
    RewriteMatchDeclared S →
    -- ★ `P6` step 3b step 8 (2026-09-14): the three carries, as at the non-`_d` twin.
    NoBridgedDerived S →
    TtuTuplesetsDirect S →
    TtuStarFree S T →
    ∃ σ0, ReachedByRulesAdmitted σ0 S
            (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
          ∧ UntaintedShadow S σ σ0 := by
  induction h with
  | empty S =>
    intro _ _ _ _ _ _ _ _ _ _ _ _ _ _
    refine ⟨emptyState S, ReachedByRulesAdmitted.empty S, ?_, ?_, ?_, ?_, ?_, ?_⟩
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k hk; simp [emptyState] at hk
    · intro ab hab; simp [emptyState] at hab
    · intro ab hab; simp [emptyState] at hab
    · intro k _ y hy; simp [emptyState] at hy
  | @write σp S T t hadm hprev ih =>
    intro hNK hCO hDAB hSV hterm hWF hBS hQ hDR hLS hMatch hNBD hTT hTS
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hDAB
      (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht'))
      (fun dt R hder => ⟨(hterm dt R hder).1,
        fun t' ht' => (hterm dt R hder).2 t' (List.mem_cons_of_mem _ ht')⟩)
      hWF
      (fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht'))
      hQ hDR hLS hMatch hNBD hTT (fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht'))
    -- ★ `P6` step 3b step 8 (2026-09-14). ⚠ `hCO` here is `ComputedOrDirect`, not
    -- `ComputedOnly` -- which is the whole point of the `_d` chain. The `T2` bridge was
    -- GENERALISED rather than forked: it only ever needed "a derived def has no TTU
    -- node", and `ComputedOrDirect` forbids `.ttu` just as `ComputedOnly` does
    -- (`ReconcileCorrect.lean::exprTtus_computedOrDirect`), so
    -- `isSubjectWildcardUserset_false_of_ttuFree` serves both chains.
    have hTF : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
        exprTtus e = [] :=
      fun dt R e hlk hder => exprTtus_computedOrDirect (hCO dt R e hlk hder)
    have hTshadow : ∀ ty p, S.isSubjectWildcardUserset ty p = true →
        (DerNode S (wAnyNode (ty, p)) ∨ LeafNode S (wAnyNode (ty, p))
          ∨ BridgeNode S (wAnyNode (ty, p))) :=
      fun ty p hx => Or.inr (Or.inr (bridgeNode_wAnyNode hx))
    have hSshadow : ∀ k : NodeKey, k.variant = Variant.plain →
        S.isSubjectWildcardUserset k.type k.pred = true →
        ¬ (DerNode S k ∨ LeafNode S k ∨ BridgeNode S k) := by
      intro k hkv hksw hc
      rcases hc with ⟨dt, on, R, hder', _, hon', rfl⟩ | hleaf | hbr
      · rw [objNode_type, objNode_pred] at hksw
        rw [hNBD dt R hder'] at hksw
        exact Bool.noConfusion hksw
      · have hnl : ¬ NotLeafName k.pred := fun hx => not_leafNode_of_notLeafName hx hleaf
        rw [isSubjectWildcardUserset_false_of_ttuFree hNK hTF hQ hDR hnl] at hksw
        exact Bool.noConfusion hksw
      · exact Variant.noConfusion (hkv ▸ (bridgeNode_elim hbr).1)
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
      -- PRE-WIDENED (4c-ii step 5): the `LeafNode` half is free at a BARE subject.
      have hnsubj : ¬ (DerNode S (subjNode t.subject) ∨ LeafNode S (subjNode t.subject)) := by
        rintro (⟨dt, on, R, _, hRne', _, heq⟩ | hleaf)
        · have hp := congrArg NodeKey.pred heq
          rw [subjNode_pred, objNode_pred, hbare] at hp
          exact hRne' hp.symm
        · exact bare_subjNode_not_leafNode hbare hleaf
      refine ⟨σ0, h0, ?_⟩
      -- ══ THE FLIP (step 4c-ii), DERIVED-seed shadow leg. Pre-flip this was the single
      -- step `σp.writeLoggedOne t` (`hcl : rewriteClosure S t = [t]`); post-flip the write
      -- fans out over `rawWriteTuples S t`, whose members are the LEAF copies of `t`
      -- (`Leaf.lean::mem_rawWriteRels_derived`) — so `hone` is FALSE and the leg is the
      -- two-list lemma at `vs = []` (the shadow σ0 does not move for a derived write).
      -- `hDer`/`hnsubj` above are the pre-flip single-step facts, kept because they are
      -- exactly what the two obligations below have to be re-derived from.
      -- OBLIGATION (D), derived form — DISCHARGED. `hnsubj` was only the SEED's instance of
      -- it; the whole-list fact is `writeLegSubjectsWide_L` at `hbase = Or.inl hbare`
      -- (a BARE subject predicate is `NotLeafName` by its left disjunct).
      have hsubjWD : ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
          ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject)) :=
        writeLegSubjectsWide_L hLS.noLeafSubjects hterm (Or.inl hbare)
      -- OBLIGATION (E), derived form — DISCHARGED. `writeLegExtrasWide_L` splits into
      -- "already in the PLAIN closure" (which `hcl` collapses to the seed `t`, whose target
      -- is the `DerNode` of `hDer`) and "leaf-targeted". So every member of a DERIVED raw
      -- write's leaf-routed closure is Der-or-Leaf targeted, which is what lets the shadow
      -- stand still (`vs = []`) across a derived write.
      have hextraD : ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
          u ∈ ([] : List Tuple) ∨
            (DerNode S (objNode u.object u.relation) ∨
              LeafNode S (objNode u.object u.relation)) := by
        intro u hu
        refine Or.inr ?_
        rcases writeLegExtrasWide_L (t := t) hLS honS u hu with hmem | hE
        · rw [hcl, List.mem_singleton] at hmem
          subst hmem
          exact Or.inl hDer
        · exact hE.imp id (fun hx => hx.elim id (fun hb => absurd hb (by
            rintro ⟨ty, pp, _, hnode⟩
            exact objNode_ne_wAny u.object u.relation (congrArg NodeKey.variant hnode)))) 
      have hsubjWD3 : ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
          ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject)
            ∨ BridgeNode S (subjNode u.subject)) := by
        intro u hu hc
        rcases hc with hc | hc | hc
        · exact hsubjWD u hu (Or.inl hc)
        · exact hsubjWD u hu (Or.inr hc)
        · exact not_bridgeNode_of_star_bare_of_leafKinds hLS.matchNotLeaf
            (fun r hr => kind_computed_of_mem_leafRewrites_computedOrDirect hNK hCO hr)
            hTT hTS hBS (t := t) List.mem_cons_self hu hc
      have hextraD3 : ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
          u ∈ ([] : List Tuple) ∨
            (DerNode S (objNode u.object u.relation) ∨
              LeafNode S (objNode u.object u.relation) ∨
              BridgeNode S (objNode u.object u.relation)) :=
        fun u hu => (hextraD u hu).imp id (fun hx => hx.imp id Or.inl)
      exact untaintedShadow_writeLegL hTshadow hSshadow
        (rewriteClosureL S (rawWriteTuples S t))
        ([] : List Tuple) σp σ0 hsh (reachedByW3d2_schema hprev) hsubjWD3 hextraD3
        (by intro u hu; simp at hu) hadm trivial
    · -- untainted write: the filter keeps `t`; fold it into σ0 (the original route)
      rw [Bool.not_eq_true] at hd
      have hfe : (t :: T).filter (fun tp => !isDerived S (tp.object.type, tp.relation))
          = t :: T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)) := by
        rw [List.filter_cons, if_pos (by simp [hd])]
      rw [hfe]
      -- ══ THE FLIP (step 4c-ii), UNTAINTED-seed branch — identical to
      -- `CascadeStable.lean::reachedByW3d_shadow`'s write leg (`hd` gives `hunt` directly).
      -- The plain-list `hsubjW` that used to sit here (built through the WIDENED seed
      -- discharge `noLeafStoreSubjects_of_storeValidRulesD`) is DELETED, for the reason
      -- given at that site: its only consumer folded the plain list on σp, and that step is
      -- now the L-list transfer plus a restriction at σ0.
      have hsubL : ∀ u ∈ rewriteClosure S t, u ∈ rewriteClosureL S (rawWriteTuples S t) :=
        fun _ hu => rewriteClosure_subset_rewriteClosureL (mem_rawWriteTuples_self hd) hu
      -- OBLIGATION (D) — DISCHARGED; the seed fact is the WIDENED (`StoreValidRulesD`) one.
      have hsubjWL : ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
          ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject)) :=
        writeLegSubjectsWide_L hLS.noLeafSubjects hterm
          (noLeafStoreSubjects_of_storeValidRulesD hDR hSV t List.mem_cons_self)
      -- OBLIGATION (E), object half — DISCHARGED.
      have hextraL := writeLegExtrasWide_L (t := t) hLS (hBS t List.mem_cons_self).2
      -- ★ `P6` step 3b step 8 (2026-09-14): the T3 widening, `_d` untainted branch.
      have hsubjWL3 : ∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
          ¬ (DerNode S (subjNode u.subject) ∨ LeafNode S (subjNode u.subject)
            ∨ BridgeNode S (subjNode u.subject)) := by
        intro u hu hc
        rcases hc with hc | hc | hc
        · exact hsubjWL u hu (Or.inl hc)
        · exact hsubjWL u hu (Or.inr hc)
        · exact not_bridgeNode_of_star_bare_of_leafKinds hLS.matchNotLeaf
            (fun r hr => kind_computed_of_mem_leafRewrites_computedOrDirect hNK hCO hr)
            hTT hTS hBS (t := t) List.mem_cons_self hu hc
      have hextraL3 := hextraL
      -- OBLIGATION (E), admission half — DISCHARGED.
      have hadmVL : FoldAdmits σ0 (rewriteClosureL S (rawWriteTuples S t)) :=
        untaintedShadow_foldAdmits hTshadow hSshadow
          (rewriteClosureL S (rawWriteTuples S t)) σp σ0 hsh
          (reachedByW3d2_schema hprev) hsubjWL3 hadm
      have hadmV : FoldAdmits σ0 (rewriteClosure S t) :=
        foldAdmits_plain_of_L h0 hadmVL hsubL
      exact ⟨σ0.writeRules S t,
        ReachedByRulesAdmitted.step t h0 hadmV,
        untaintedShadow_writeLegL hTshadow hSshadow (rewriteClosureL S (rawWriteTuples S t))
          (rewriteClosure S t) σp σ0 hsh (reachedByW3d2_schema hprev)
          hsubjWL3 hextraL3 hsubL hadm hadmV⟩
  | @remove σp S T t hadm _ hSVT hBST hTST htermT hprev ih =>
    intro hNK hCO hDAB _ _ hWF _ hQ hDR hLS hMatch hNBD hTT _
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hDAB
      (storeValidRulesD_of_storeValidRules_directArmsBare hSVT hDAB)
      htermT hWF hBST hQ hDR hLS hMatch hNBD hTT hTST
    -- **R5**: the shadow transport's store-shape premise, discharged (never assumed) from
    -- `StoreValidRules`' own `lookup` plus `WF.relNames` — a declared relation is dot-free.
    have hSN : ∀ t' ∈ T, isLeafPred t'.relation = false := fun t' ht' => by
      obtain ⟨e, _rs, hlk, _, _⟩ := hSVT t' ht'
      exact isLeafPred_relation_false_of_lookup hWF hlk
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
      exact untaintedShadow_removeLeg_d hLS hMatch hSN hNK hprev hsh h0 hadm h0e (fun e he => he)
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
      exact untaintedShadow_removeLeg_d hLS hMatch hSN hNK hprev hsh h0 hadm h0e hsub
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro hNK hCO hDAB hSV hterm hWF hBS hQ hDR hLS hMatch hNBD hTT hTS
    obtain ⟨σ0, h0, hsh⟩ := ih hNK hCO hDAB hSV hterm hWF hBS hQ hDR hLS hMatch hNBD hTT hTS
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
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (hcollapse : ∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ R) →
      (u, objNode ⟨dt, on⟩ R) ∈ σ.edges)
    (hsem_ws : ∀ sh : Shape, sh.2 = BARE →
      sem S T ⟨starSubj sh, R, ⟨dt, on⟩⟩ = true → sh ∈ declaredWildcardShapes S)
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
          by_cases hcov : (st, BARE) ∈ declaredWildcardShapes S ∧
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
          by_cases hcov : (st, BARE) ∈ declaredWildcardShapes S ∧
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
`index_v4/processor.py::DeltaProcessor._reconcile` evaluates at a stratum-2 key in
round 2, after round 1 re-settled the stratum-1 operands
(`::_EvalContext` routing; `::DeltaProcessor._run_cascade`'s per-round key loop). -/

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
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
    (hcr : ComputedRefsNotLeaf S)
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
        -- untainted operand: routing + the shadow + the W2 base equation.
        -- The `have` is TYPED on purpose: the `rw` below elaborates with no expected
        -- type, and `notLeafNode_of_computedRef`'s `{dt on}` are fixed by nothing in
        -- its explicit arguments (`hlk` pins only the lookup key).
        have hnl : ¬ LeafNode S (objNode ⟨dt, on⟩ r') :=
          notLeafNode_of_computedRef hcr hlk hr'
        rw [GraphModel.graphRecR_eq_graphRec s on (by rw [hσS]; exact hd'),
          shadow_graphRec_agree hsh s on hnl hd']
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
            sem S T ⟨starSubj sh, r', ⟨dt, on⟩⟩ = true → sh ∈ declaredWildcardShapes S := by
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
    (hcr : ComputedRefsNotLeaf S)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
        have hnl : ¬ LeafNode S (objNode ⟨dt, on⟩ r') :=
          notLeafNode_of_computedRef hcr hlk hr'
        rw [GraphModel.graphRecR_eq_graphRec s on (by rw [hσS]; exact hd'),
          shadow_graphRec_agree hsh s on hnl hd']
        exact graphRec_base_eq_bs_d hWF hTT hNK hR hSV hBS hTS hMatch hterm h0 hs hon r' hd'
      | true =>
        obtain ⟨hset', hcomp', hcollapse'⟩ := hops r' hr' hd'
        obtain ⟨e', hlk'⟩ := isDerived_declared hd'
        have hleafUnt' : ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false :=
          hLU2 r' hr' hd' e' hlk'
        have hco' : ComputedOnly e' := hCO dt r' e' hlk' hd'
        have hsem_ws' : ∀ sh : Shape, sh.2 = BARE →
            sem S T ⟨starSubj sh, r', ⟨dt, on⟩⟩ = true → sh ∈ declaredWildcardShapes S := by
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
    (hcr : ComputedRefsNotLeaf S)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
        have hnl : ¬ LeafNode S (objNode ⟨dt, on⟩ r') :=
          notLeafNode_of_computedRef hcr hlk hr'
        rw [GraphModel.graphRecR_eq_graphRec s on (by rw [hσS]; exact hd'),
          shadow_graphRec_agree hsh s on hnl hd',
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
            sem S T ⟨starSubj sh, r', ⟨dt, on⟩⟩ = true → sh ∈ declaredWildcardShapes S := by
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
    (hNBD : NoBridgedDerived S)
    (hjv1 : ∀ j ∈ jobs1, W3cJobValid S j)
    (h : ReachedByW3d2 σ S T)
    (hlk' : S.lookup (dt', R') = some e')
    (hjk : (dt', R', on') ∈ cascadeKeysAbove S (reconcileJobsLR S T σ jobs1)
      (σ.frontierMax σ.watermark)) :
    ∃ r', r' ∈ computedRefs e' ∧ isDerived S (dt', r') = true := by
  unfold cascadeKeysAbove at hjk
  rw [List.mem_eraseDups] at hjk
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
  have hbase1 := reachedByW3d2_Rnode_not_source (on := j1.on) hterm hRne1 hNBD hder1 h
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
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S (t :: T))
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
      have hedge' := (writeLeg_derived_inedges_eq hWF hSV hlk' hder' hco' x).mpr hedge
      have := reach_complete hclσ' (NReaches.edge hedge')
      rw [h1] at this
      cases this
    · exfalso
      have hedge' := hcol' x (reach_sound h1)
      have hedge := (writeLeg_derived_inedges_eq hWF hSV hlk' hder' hco' x).mp hedge'
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
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S (t :: T))
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hσS : σ.schema = S)
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant ≠ Variant.wAll)
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
    rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).schema, writeRulesRaw_schema, hσS]
  have hclσ' : ∀ ab ∈ (σ.writeLoggedRules S t).edges,
      ab.1 ∈ (σ.writeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.writeLoggedRules S t).nodes := by
    have hev := writeLoggedRules_evalEq (EvalEq.refl σ) S t
    intro ab hab
    rw [hev.edges] at hab
    rw [hev.nodes]
    exact edgesClosed_foldl_writeBridgedOne (rewriteClosureL S (rawWriteTuples S t)) σ hclσ ab hab
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
    exact writeLeg_probeDerived_stable hWF hNK hSV hlk' hd' hco' hclσ hclσ' hcol hcol' hon

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
    (hcr : ComputedRefsNotLeaf S)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (h0' : ReachedByRulesAdmitted σ0' S (t :: T))
    (hsh' : UntaintedShadow S (σ.writeLoggedRules S t) σ0')
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant ≠ Variant.wAll)
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
        (checkFn_eq_sem_w3d hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm hcr
          h0' hsh' hlk hco hleafUnt hs hon).symm
    _ = σ.checkFn (t :: T) s dt on R e :=
        writeLeg_checkFn_stable (t :: T) hclσ htp' hlk hder hco hon hunmapped s
    _ = σ.checkFn T s dt on R e := checkFn_store_irrel _ _ s dt on R hco
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3d hWF hTT hNK hR hSVw hBSw hTSw hCO hMatch hStrat htermw hcr
          h0 hsh hlk hco hleafUnt hs hon

/-- **`SettledKey` transports across a write leg given `sem` stability** — the
    representation is untouched (rows write-inert, derived in-edges fixed); the
    meaning hypothesis `hsem` is supplied per stratum. -/
theorem settledKey_writeLeg_sem {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S (t :: T))
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
    rw [writeLeg_derived_inedges_eq hWF hSV hlk hder (hCO dt R e hlk hder) (subjNode s)] at hedge'
    rw [hsem s (fun hx => absurd hx hstar)]
    exact hedge s hb hstar hedge'

/-- **`CompleteKey` transports across a write leg given `sem` stability.** -/
theorem completeKey_writeLeg_sem {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S (t :: T))
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
    rw [writeLeg_derived_inedges_eq hWF hSV hlk hder (hCO dt R e hlk hder) (subjNode s)]
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
    (hQ : TtuTargetsSat S NotLeafName) (hDR : DirectRestrictionsNotLeaf S)
    (hLS : LeafScope S)
    (hcr : ComputedRefsNotLeaf S)
    (hNBD : NoBridgedDerived S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (t :: T) R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2 σ S T) (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
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
  obtain ⟨σ0, h0, hsh⟩ :=
    reachedByW3d2_shadow h hNK hCO hSVw htermw hQ hDR hLS hMatch hBSw hNBD hTT hTSw
  obtain ⟨σ0', h0', hsh'⟩ :=
    reachedByW3d2_shadow h' hNK hCO hSV hterm hQ hDR hLS hMatch hBS hNBD hTT hTS
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
        hStrat hterm hcr h0 hsh h0' hsh' hclσ htp' hlk' hd' hco' hleafUnt'
        (hopsUnmapped r' hr' hd') hx hon
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨settledKey_writeLeg_sem hWF hNK hSV hCO hWSbare hlk' hd' hsem_op hset,
      completeKey_writeLeg_sem hWF hNK hSV hCO hWSbare hlk' hd' hsem_op hcomp,
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
          hterm hCO hWSbare hcr h0' hsh' hσ'S hlk hder hco hLU2e hops' hs hon).symm
    _ = (σ.writeLoggedRules S t).checkFnR T s dt on R e :=
        checkFnR_store_irrel _ _ s dt on R hco
    _ = σ.checkFnR T s dt on R e :=
        writeLeg_checkFnR_stable T hWF hNK hSV hCO hσS hclσ htp' hlk hder hco
          hcolOps hon hunmapped s
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFnR_eq_sem_settled hWF hTT hNK hR hSVw hBSw hTSw hMatch hStrat
          htermw hCO hWSbare hcr h0 hsh hσS hlk hder hco hLU2e hops hs hon

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
  rw [List.mem_eraseDups]
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
`index_v4/processor.py::DeltaProcessor._reconcile`'s step-(2)/(2b) enumeration runs
inside the round). Chain-side hypotheses as in W3d-1c;
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
      (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
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
  · rw [releasePostLogged_residue, pushDelta_residue, removeEdgeOne_residue]
  · rfl

/-- The logged retraction leaves the residue map untouched (a fold of
    `removeLoggedOne_residue_eq`; local copy of `removeLoggedRules_residue`). -/
theorem removeLoggedRules_residue_eq (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.removeLoggedRules S t).residue = σ.residue := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosureL S (rawWriteTuples S t) = ts
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
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S T) (ht : t ∈ T)
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
      have hedge' := (removeLeg_derived_inedges_eq hWF hSV ht hlk' hder' hco' x).mpr hedge
      have := reach_complete hclσ' (NReaches.edge hedge')
      rw [h1] at this
      cases this
    · exfalso
      have hedge' := hcol' x (reach_sound h1)
      have hedge := (removeLeg_derived_inedges_eq hWF hSV ht hlk' hder' hco' x).mp hedge'
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
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S T) (ht : t ∈ T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hσS : σ.schema = S)
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp : ∀ ab ∈ σ.edges, ab.2.variant ≠ Variant.wAll)
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
    exact removeLeg_probeDerived_stable hWF hNK hSV ht hlk' hd' hco' hclσ hclσ' hcol hcol' hon

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
    (hcr : ComputedRefsNotLeaf S)
    (ht : t ∈ T)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (h0' : ReachedByRulesAdmitted σ0' S (T.erase t))
    (hsh' : UntaintedShadow S (σ.removeLoggedRules S t) σ0')
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp : ∀ ab ∈ σ.edges, ab.2.variant ≠ Variant.wAll)
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
        (checkFn_eq_sem_w3d hWF hTT hNK hR hSVe hBSe hTSe hCO hMatch hStrat hterme hcr
          h0' hsh' hlk hco hleafUnt hs hon).symm
    _ = σ.checkFn (T.erase t) s dt on R e :=
        removeLeg_checkFn_stable (T.erase t) hclσ htp hlk hder hco hon hunmapped s
    _ = σ.checkFn T s dt on R e := checkFn_store_irrel _ _ s dt on R hco
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3d hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm hcr
          h0 hsh hlk hco hleafUnt hs hon

/-- **`SettledKey` transports across a retraction leg given `sem` stability** (dual of
    `settledKey_writeLeg_sem`): representation untouched (rows inert via
    `removeLoggedRules_residue`, derived in-edges fixed via `removeLeg_derived_inedges_eq`);
    meaning supplied as `hsem` at store `T.erase t` vs `T`. -/
theorem settledKey_removeLeg_sem {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S T) (ht : t ∈ T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
    rw [removeLeg_derived_inedges_eq hWF hSV ht hlk hder (hCO dt R e hlk hder)
      (subjNode s)] at hedge'
    rw [hsem s (fun hx => absurd hx hstar)]
    exact hedge s hb hstar hedge'

/-- **`CompleteKey` transports across a retraction leg given `sem` stability** (dual of
    `completeKey_writeLeg_sem`). -/
theorem completeKey_removeLeg_sem {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S T) (ht : t ∈ T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
    rw [removeLeg_derived_inedges_eq hWF hSV ht hlk hder (hCO dt R e hlk hder) (subjNode s)]
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
    (hLS : LeafScope S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hcr : ComputedRefsNotLeaf S)
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
    untaintedShadow_removeLeg hLS hMatch h hsh h0 ht h0' hsub hSV hCO
  exact removeLeg_sem_stable_sh hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm hcr ht
    h0 hsh h0' hsh' (reachedByW3d2_edgesClosed h)
    (reachedByW3d2_edges_target_plain h hBS) hlk hder hco hleafUnt hunmapped hs hon

/-- **Settledness transports across a retraction leg at an unmapped key** (dual of
    `settledKey_writeLeg`): representation untouched and the key's `sem` unchanged
    (`removeLeg_sem_stable`). Carries the R5a rebuild triple in place of `ReachedByW3d.write`. -/
theorem settledKey_removeLeg {σ σ0 σ0' : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hLS : LeafScope S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hcr : ComputedRefsNotLeaf S)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
    fun s hs => removeLeg_sem_stable hWF hTT hNK hR hLS hSV hBS hTS hCO hMatch hStrat hterm hcr
      h ht h0 hsh h0' hsub hlk hder hco hleafUnt hunmapped hs hon
  exact settledKey_removeLeg_sem hWF hNK hSV ht hCO hWSbare hlk hder hsem hset

/-- **Stratum-2 `sem` stability across a retraction leg** (dual of `writeLeg_sem_stable2`): at a
    derived-reading key the retraction maps NEITHER directly NOR through any derived operand
    key, `sem` is unchanged. The post-state reach-collapse is derived from the pre-state
    collapse (`reachedByW3d2_reach_collapse_root`) plus edge-subset and the fixed derived
    in-edges (`removeLeg_derived_inedges_eq`) — no `remove` constructor needed. Operand
    settledness transports by the stratum-1 dual, the routed guard by `removeLeg_checkFnR_stable`. -/
theorem removeLeg_sem_stable2 {σ σ0 σ0' : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hLS : LeafScope S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hcr : ComputedRefsNotLeaf S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
    untaintedShadow_removeLeg hLS hMatch h hsh h0 ht h0' hsub hSV hCO
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
    exact (removeLeg_derived_inedges_eq hWF hSV ht hlk' hd' hco' u).mpr hpreu
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
        hStrat hterm hcr ht h0 hsh h0' hsh' hclσ htp hlk' hd' hco' hleafUnt'
        (hopsUnmapped r' hr' hd') hx hon
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨settledKey_removeLeg_sem hWF hNK hSV ht hCO hWSbare hlk' hd' hsem_op hset,
      completeKey_removeLeg_sem hWF hNK hSV ht hCO hWSbare hlk' hd' hsem_op hcomp,
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
          hterme hCO hWSbare hcr h0' hsh' hσ'S hlk hder hco hLU2e hops' hs hon).symm
    _ = (σ.removeLoggedRules S t).checkFnR T s dt on R e :=
        checkFnR_store_irrel _ _ s dt on R hco
    _ = σ.checkFnR T s dt on R e :=
        removeLeg_checkFnR_stable T hWF hNK hSV ht hCO hσS hclσ htp hlk hder hco
          hcolOps hon hunmapped s
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFnR_eq_sem_settled hWF hTT hNK hR hSV hBS hTS hMatch hStrat
          hterm hCO hWSbare hcr h0 hsh hσS hlk hder hco hLU2e hops hs hon

/-! ## Direct-arm settledness-transport groundwork (leg 5d, steps 2–3)

The `_d` clones of the settledness-transport family need four groundwork layers the
`ComputedOnly` originals never did:

1. **`sem` over the empty store is FALSE, unconditionally** (`sem_nil_false`) — the
   only truth sources in `sem` are stored tuples, so the `_d` induction's `empty`
   case needs none of the fragment machinery `sem_nil_derived_false2` threads.
2. **A raw write on a derived key DIRTIES its own key** (`writeLeg_own_key_dirty`) — the
   `affectedKeys` LeafFamily own-key branch (`Delta.leaf`), made chain-usable.
   ⚠ **UPDATED after R5 + (alpha):** its remove twin `removeLeg_own_key_dirty` is DELETED
   (the retraction no longer collapses to one `removeLoggedOne`), and this layer is no
   longer what lets an UNMAPPED key conclude the leg's tuple sits at a different derived
   node — BOTH `writeLeg_inedges_eq_of_unmapped` and `removeLeg_inedges_eq_of_unmapped` are
   now UNCONDITIONAL, off `rewriteClosureL_notarget_of_ne`'s conditional `hne`. The ONLY
   surviving consumer of own-key dirtiness is `writeLeg_sem_stable2_d`'s `hneKey` step.
   ⚠ **LANDED sorry-free 2026-09-05 round 2**, on the post-(alpha) mechanism (the delta sits
   at the MINTED LEAF node and `publicOfLeaf` recovers the public relation) plus the routing
   premise `hroute : rawWriteRels S t ≠ []`, which the `hneKey` step discharges from
   `StoreValidRulesD` through `rawWriteRels_ne_nil_of_exprDirectsAll` — a theorem about the
   compiled plan tree, NOT a `GraphAdmission` carry. Necessity control:
   `tvDer_own_key_not_dirty`.
3. **In-edge preservation from node inequality alone**
   (`rewriteClosureL_notarget_of_ne` + the `_of_unmapped` wrappers) — fragment-free.
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

/-! ### The routing obligation — a `Direct` arm that admits the subject really routes

`rawWriteRels` filters the ALLOCATION (`Leaf.lean::persistedLeaves`) for storage-bearing
leaves whose restrictions admit `t`'s subject; `StoreValidRulesD` admits a derived-key
tuple on the strength of a `Direct` arm of the def (`ReconcileCorrect.lean::exprDirectsAll`)
that admits the same subject. The two are different walks over the same tree, and nothing
in the tree connected them — which is why `writeLeg_own_key_dirty` was a staged `sorry`
through 2026-09-05 round 1: without this bridge the routing premise it needs cannot be
discharged at its consumer.

⚠ **This is a THEOREM about the compiled plan tree and must stay one.** The tempting
shortcut is a third `GraphAdmission` field ("every admitted derived write routes to at
least one leaf"); that would let the model assume the very routing it exists to model, and
is refused here by name.

Sited in this module (not `Leaf.lean`, where the design plan proposed it) for a measured
reason: `exprDirectsAll` lives in `ReconcileCorrect.lean`, which is in neither `Leaf.lean`'s
nor `LeafRules.lean`'s import cone. `Cascade.lean`'s cone is the first that contains both.
-/

/-- Proof-local: does a persisted leaf take the raw write of `t`? Exactly the two
    storage-bearing arms `rawWriteRels`' `filterMap` keeps (`.closure` leaves are
    rule-fed and take no raw write). -/
private def PLeafTakes (t : Tuple) : PLeaf → Bool
  | .storage rs => restrictionMatches rs t
  | .userset r  => restrictionMatches [r] t
  | .closure _  => false

private theorem restrictionMatches_iff {rs : List Restriction} {t : Tuple} :
    restrictionMatches rs t = true ↔ ∃ r ∈ rs,
      (t.subject.type == r.1 && t.subject.predicate == r.2.1 &&
        ((t.subject.name == STAR) == r.2.2)) = true := by
  unfold restrictionMatches; simp [List.any_eq_true]

/-- Inside a PURE subtree `splitPure` collects EVERY `Direct` arm's restrictions into one
    block — `isPure` rules out `inter`/`excl`, which are the only nodes `exprDirectsAll`
    descends into and `splitPure` does not. -/
private theorem mem_splitPure_of_isPure {S : Schema} {ty : String} :
    ∀ (e : Expr), isPure S ty e = true → ∀ rs ∈ exprDirectsAll e, ∀ r ∈ rs,
      r ∈ (splitPure e).1 := by
  intro e
  induction e with
  | direct rs0 =>
      intro _ rs hrs r hr
      simp only [exprDirectsAll, List.mem_singleton] at hrs
      subst hrs; simpa [splitPure] using hr
  | computed _ => intro _ rs hrs; simp [exprDirectsAll] at hrs
  | ttu _ _ => intro _ rs hrs; simp [exprDirectsAll] at hrs
  | union a b iha ihb =>
      intro hp rs hrs r hr
      rw [isPure] at hp
      obtain ⟨hpa, hpb⟩ := Bool.and_eq_true .. |>.mp hp
      simp only [exprDirectsAll, List.mem_append] at hrs
      simp only [splitPure, List.mem_append]
      rcases hrs with h | h
      · exact Or.inl (iha hpa rs h r hr)
      · exact Or.inr (ihb hpb rs h r hr)
  | inter a b _ _ => intro hp; simp [isPure] at hp
  | excl a b _ _ => intro hp; simp [isPure] at hp

/-- A matching restriction inside the merged pure block gives a matching `.storage` leaf. -/
private theorem pureLeaves_takes {t : Tuple} {e : Expr} {r : Restriction}
    (hr : r ∈ (splitPure e).1)
    (hm : (t.subject.type == r.1 && t.subject.predicate == r.2.1 &&
        ((t.subject.name == STAR) == r.2.2)) = true) :
    ∃ pl ∈ pureLeaves e, PLeafTakes t pl = true := by
  have hne : ¬ (splitPure e).1.isEmpty = true := by
    cases hsp : (splitPure e).1 with
    | nil => rw [hsp] at hr; simp at hr
    | cons a l => simp
  refine ⟨.storage (splitPure e).1, ?_, ?_⟩
  · unfold pureLeaves
    simp only [List.mem_append]
    exact Or.inl (by rw [if_neg hne]; simp)
  · exact restrictionMatches_iff.mpr ⟨r, hr, hm⟩

/-- A `Direct` arm that admits `t` allocates a leaf that takes `t`'s raw write: the merged
    `.storage` block on the pure route, and on the impure route either the non-tainted
    filtered block or the tainted restriction's own `.userset` leaf. -/
private theorem atomLeaves_direct_takes {S : Schema} {ty : String} {t : Tuple}
    {rs0 : List Restriction} (h : restrictionMatches rs0 t = true) :
    ∃ pl ∈ atomLeaves S ty (.direct rs0), PLeafTakes t pl = true := by
  obtain ⟨r, hr, hm⟩ := restrictionMatches_iff.mp h
  rw [show atomLeaves S ty (.direct rs0)
      = (if isPure S ty (.direct rs0) then pureLeaves (.direct rs0)
         else ((if (rs0.filter (fun r => !isTaintedUserset S r)).isEmpty then []
                else [PLeaf.storage (rs0.filter (fun r => !isTaintedUserset S r))])
               ++ (rs0.filter (isTaintedUserset S)).map PLeaf.userset)) from rfl]
  by_cases hp : isPure S ty (.direct rs0) = true
  · rw [if_pos hp]
    exact pureLeaves_takes (e := .direct rs0) (by simpa [splitPure] using hr) hm
  · rw [if_neg hp]
    by_cases ht : isTaintedUserset S r = true
    · refine ⟨.userset r, ?_, ?_⟩
      · simp only [List.mem_append]
        exact Or.inr (List.mem_map.mpr ⟨r, List.mem_filter.mpr ⟨hr, by simpa using ht⟩, rfl⟩)
      · exact restrictionMatches_iff.mpr ⟨r, List.mem_singleton.mpr rfl, hm⟩
    · have ht' : isTaintedUserset S r = false := by
        cases hx : isTaintedUserset S r with
        | true => exact absurd hx ht
        | false => rfl
      have hmemp : r ∈ rs0.filter (fun r => !isTaintedUserset S r) :=
        List.mem_filter.mpr ⟨hr, by simp [ht']⟩
      have hne : ¬ (rs0.filter (fun r => !isTaintedUserset S r)).isEmpty = true := by
        cases hsp : rs0.filter (fun r => !isTaintedUserset S r) with
        | nil => rw [hsp] at hmemp; simp at hmemp
        | cons a l => simp
      refine ⟨.storage (rs0.filter (fun r => !isTaintedUserset S r)), ?_, ?_⟩
      · simp only [List.mem_append]
        exact Or.inl (by rw [if_neg hne]; simp)
      · exact restrictionMatches_iff.mpr ⟨r, hmemp, hm⟩

/-- **The allocation walk meets the admission walk.** Proved for `persistedLeaves` and
    `unionSpineLeaves` simultaneously, because the impure-`union` arm of the first calls the
    second (`Leaf.lean::unionSpineLeaves`' 2026-08-16b correction: Python never merges a
    sub-union of an impure n-ary node). Every case is `exprDirectsAll`'s own recursion arm
    for arm; the only content is the PURE-union case, where `mem_splitPure_of_isPure`
    relocates the matching restriction into the merged block. -/
private theorem persistedLeaves_takes {S : Schema} {ty : String} {t : Tuple} :
    ∀ (e : Expr), ∀ rs ∈ exprDirectsAll e, restrictionMatches rs t = true →
      (∃ pl ∈ persistedLeaves S ty e, PLeafTakes t pl = true) ∧
      (∃ pl ∈ unionSpineLeaves S ty e, PLeafTakes t pl = true) := by
  intro e
  induction e with
  | direct rs0 =>
      intro rs hrs hm
      simp only [exprDirectsAll, List.mem_singleton] at hrs
      subst hrs
      exact ⟨atomLeaves_direct_takes hm, atomLeaves_direct_takes hm⟩
  | computed _ => intro rs hrs; simp [exprDirectsAll] at hrs
  | ttu _ _ => intro rs hrs; simp [exprDirectsAll] at hrs
  | union a b iha ihb =>
      intro rs hrs hm
      simp only [exprDirectsAll, List.mem_append] at hrs
      have hspine : ∃ pl ∈ unionSpineLeaves S ty a ++ unionSpineLeaves S ty b,
          PLeafTakes t pl = true := by
        rcases hrs with h | h
        · obtain ⟨pl, hpl, hlm⟩ := (iha rs h hm).2
          exact ⟨pl, List.mem_append_left _ hpl, hlm⟩
        · obtain ⟨pl, hpl, hlm⟩ := (ihb rs h hm).2
          exact ⟨pl, List.mem_append_right _ hpl, hlm⟩
      refine ⟨?_, hspine⟩
      rw [show persistedLeaves S ty (.union a b)
          = (if isPure S ty (.union a b) then pureLeaves (.union a b)
             else unionSpineLeaves S ty a ++ unionSpineLeaves S ty b) from rfl]
      by_cases hp : isPure S ty (.union a b) = true
      · rw [if_pos hp]
        obtain ⟨r, hr, hmr⟩ := restrictionMatches_iff.mp hm
        have hrs' : rs ∈ exprDirectsAll (Expr.union a b) := by
          simp only [exprDirectsAll, List.mem_append]; exact hrs
        exact pureLeaves_takes (mem_splitPure_of_isPure _ hp rs hrs' r hr) hmr
      · rw [if_neg hp]; exact hspine
  | inter a b iha ihb =>
      intro rs hrs hm
      simp only [exprDirectsAll, List.mem_append] at hrs
      have hb : ∃ pl ∈ persistedLeaves S ty a ++ persistedLeaves S ty b,
          PLeafTakes t pl = true := by
        rcases hrs with h | h
        · obtain ⟨pl, hpl, hlm⟩ := (iha rs h hm).1
          exact ⟨pl, List.mem_append_left _ hpl, hlm⟩
        · obtain ⟨pl, hpl, hlm⟩ := (ihb rs h hm).1
          exact ⟨pl, List.mem_append_right _ hpl, hlm⟩
      exact ⟨hb, hb⟩
  | excl a b iha ihb =>
      intro rs hrs hm
      simp only [exprDirectsAll, List.mem_append] at hrs
      have hb : ∃ pl ∈ persistedLeaves S ty a ++ persistedLeaves S ty b,
          PLeafTakes t pl = true := by
        rcases hrs with h | h
        · obtain ⟨pl, hpl, hlm⟩ := (iha rs h hm).1
          exact ⟨pl, List.mem_append_left _ hpl, hlm⟩
        · obtain ⟨pl, hpl, hlm⟩ := (ihb rs h hm).1
          exact ⟨pl, List.mem_append_right _ hpl, hlm⟩
      exact ⟨hb, hb⟩

/-- `rawWriteRels`' `filterMap` over the indexed allocation keeps at least one entry as
    soon as one leaf takes the write. List-generic in the index accumulator so no
    `zipIdx`-membership lemma is needed. -/
private theorem filterMap_zipIdx_ne_nil {t : Tuple} {R : String} :
    ∀ (l : List PLeaf) (n : Nat), (∃ pl ∈ l, PLeafTakes t pl = true) →
      (l.zipIdx n).filterMap (fun pi =>
        match pi.1 with
        | .storage rs => if restrictionMatches rs t then some (leafPred R pi.2) else none
        | .userset r => if restrictionMatches [r] t then some (leafPred R pi.2) else none
        | .closure _ => none) ≠ [] := by
  intro l
  induction l with
  | nil => intro n h; obtain ⟨pl, hpl, _⟩ := h; simp at hpl
  | cons a rest ih =>
      intro n h
      simp only [List.zipIdx_cons, List.filterMap_cons]
      have hrest : PLeafTakes t a = false → ∃ pl ∈ rest, PLeafTakes t pl = true := by
        intro ha
        obtain ⟨pl, hpl, hlm⟩ := h
        rcases List.mem_cons.mp hpl with rfl | hpl'
        · rw [ha] at hlm; exact absurd hlm (by simp)
        · exact ⟨pl, hpl', hlm⟩
      cases a with
      | storage rs =>
          by_cases hc : restrictionMatches rs t = true
          · simp [hc]
          · have ha : PLeafTakes t (PLeaf.storage rs) = false := by
              show restrictionMatches rs t = false
              cases hx : restrictionMatches rs t with
              | true => exact absurd hx hc
              | false => rfl
            simp only [hc]
            simpa using ih (n + 1) (hrest ha)
      | userset r =>
          by_cases hc : restrictionMatches [r] t = true
          · simp [hc]
          · have ha : PLeafTakes t (PLeaf.userset r) = false := by
              show restrictionMatches [r] t = false
              cases hx : restrictionMatches [r] t with
              | true => exact absurd hx hc
              | false => rfl
            simp only [hc]
            simpa using ih (n + 1) (hrest ha)
      | closure e =>
          have ha : PLeafTakes t (PLeaf.closure e) = false := rfl
          simpa using ih (n + 1) (hrest ha)

/-- **THE ROUTING OBLIGATION.** A derived-key write that `StoreValidRulesD` admits — i.e.
    one matching a `Direct` arm reachable through any boolean nesting — routes to at least
    one storage leaf. This is what discharges `writeLeg_own_key_dirty`'s `hroute` premise at
    its consumer (`writeLeg_sem_stable2_d`'s `hneKey`) from the store admission, so no
    `GraphAdmission` field is added and the premise is a consequence rather than a carry.

    Non-vacuity / necessity control: `tvDer_own_key_not_dirty` below (a derived write whose
    def has NO `Direct` arm routes to `[]` and dirties nothing) — drop `hroute` and the
    theorem it guards is FALSE. -/
theorem rawWriteRels_ne_nil_of_exprDirectsAll {S : Schema} {t : Tuple} {e : Expr}
    (hd : isDerived S (t.object.type, t.relation) = true)
    (hlk : S.lookup (t.object.type, t.relation) = some e)
    {rs : List Restriction} (hrs : rs ∈ exprDirectsAll e)
    (hrm : restrictionMatches rs t = true) :
    rawWriteRels S t ≠ [] := by
  unfold rawWriteRels
  rw [if_pos hd, hlk]
  exact filterMap_zipIdx_ne_nil _ 0 (persistedLeaves_takes e rs hrs hrm).1

/-- **NECESSITY CONTROL — `hrm` (the subject-match premise) is load-bearing**, per
    `docs/sabotage-procedure.md`: the narrowest plausible weakening of the lemma above is
    "a derived def with ANY `Direct` arm routes somewhere", and it is FALSE. At
    `Leaf.lean::LeafWitness.SwF` (`approver := [user] or ([user, employee] but not banned)`)
    the def has TWO `Direct` arms, yet a `group:g1` subject matches neither restriction, so
    `rawWriteRels` filter-maps to `[]`. Same fixture as `Leaf.lean::swF_second_only`, whose
    sabotage S4 (drop the match guard) is the mirror image of this one.

    Stated as a conjunction of `decide`-able positives rather than as a `¬ ∀`, following
    `LeafRules.lean::lrV_localisation_needs_notLeaf` / `::lrV_localisation_needs_notDerived`. -/
theorem swF_unmatched_subject_routes_nowhere :
    isDerived LeafWitness.SwF ("doc", "approver") = true
      ∧ ((LeafWitness.SwF.lookup ("doc", "approver")).map
          (fun e => (exprDirectsAll e).length)) = some 2
      ∧ rawWriteRels LeafWitness.SwF ⟨⟨"group", "g1", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩
          = [] := by
  decide

/-- The write leg's outbox carries a `leaf = true` frontier row at EVERY closure member's
    object node. `FoldAdmits` fires `writeLoggedOne`'s `if` at each step, `pushDelta` mints
    an id strictly above the (fold-invariant) watermark, and
    `foldl_writeLoggedOne_outbox_mono` carries the row to the end of the fold. -/
private theorem mem_outbox_foldl_writeLoggedOne :
    ∀ (us : List Tuple) (σ : GraphState), FoldAdmitsBridged σ us → ∀ u ∈ us,
      ∃ d ∈ (us.foldl (fun acc x => acc.writeLoggedOne x) σ).outbox,
        d.node = objNode u.object u.relation ∧ d.leaf = true ∧ σ.watermark < d.id := by
  intro us
  induction us with
  | nil => intro σ _ u hu; simp at hu
  | cons a rest ih =>
      intro σ hfa u hu
      obtain ⟨h1, h2⟩ := hfa
      have h1' : (σ.bridgePreLogged a).admitEdge (subjNode a.subject)
          (objNode a.object a.relation) = true := by
        rw [admitEdge_evalEq (bridgePreLogged_evalEq (EvalEq.refl σ) a)]
        exact h1
      have hstep : σ.writeLoggedOne a
          = ((σ.bridgePreLogged a).addEdge (subjNode a.subject)
              (objNode a.object a.relation)).pushDelta
              (objNode a.object a.relation) a.relation true := by
        unfold GraphState.writeLoggedOne; rw [if_pos h1']
      have hwm : (σ.writeLoggedOne a).watermark = σ.watermark := writeLoggedOne_watermark σ a
      have hfa' : FoldAdmitsBridged (σ.writeLoggedOne a) rest :=
        foldAdmitsBridged_evalEq (writeLoggedOne_evalEq (EvalEq.refl σ) a) rest h2
      simp only [List.foldl_cons]
      rcases List.mem_cons.mp hu with rfl | hu'
      · refine ⟨⟨((σ.bridgePreLogged u).addEdge (subjNode u.subject)
            (objNode u.object u.relation)).nextDeltaId,
            objNode u.object u.relation, u.relation, true⟩,
          ?_, rfl, rfl, ?_⟩
        · refine foldl_writeLoggedOne_outbox_mono rest (σ.writeLoggedOne u) _ ?_
          rw [hstep, pushDelta_outbox]
          exact List.mem_cons_self ..
        · show σ.watermark < max ((σ.bridgePreLogged u).addEdge (subjNode u.subject)
            (objNode u.object u.relation)).maxOutboxId
            ((σ.bridgePreLogged u).addEdge (subjNode u.subject)
              (objNode u.object u.relation)).watermark + 1
          have hw : ((σ.bridgePreLogged u).addEdge (subjNode u.subject)
              (objNode u.object u.relation)).watermark = σ.watermark :=
            bridgePreLogged_watermark σ u
          omega
      · obtain ⟨d, hd, hn, hl, hid⟩ := ih (σ.writeLoggedOne a) hfa' u hu'
        exact ⟨d, hd, hn, hl, by rw [hwm] at hid; exact hid⟩

/-- The seed list sits inside its own leaf-routed closure (fuel is `|keys| + 1 ≥ 1`, and
    `rewriteClosureAuxL`'s successor arm is `cur ++ …`). -/
private theorem mem_rewriteClosureL_of_mem_seeds {S : Schema} {seeds : List Tuple}
    {u : Tuple} (h : u ∈ seeds) : u ∈ rewriteClosureL S seeds := by
  rw [mem_rewriteClosureL_iff]
  show u ∈ rewriteClosureAuxL S (S.keys.length + 1) seeds
  show u ∈ seeds ++ rewriteClosureAuxL S S.keys.length (seeds.flatMap (rewriteStepL S))
  exact List.mem_append_left _ h

/-- **A raw admitted, ROUTED write on a derived key dirties its OWN PUBLIC key** — the
    chain-level form of the `affectedKeys` LeafFamily own-key branch (the
    `isinstance(fam, LeafFamily)` arm of
    `index_v4/processor.py::DeltaProcessor._map_deltas_to_keys`, `processor.py:1411-1422`).

    **Post-(alpha) mechanism, which is NOT the pre-flip one.** The write no longer emits a
    delta at the public node: it fans out over `rawWriteTuples S t`, whose members carry
    MINTED LEAF relations, so every emitted row sits at a leaf node
    (`mem_outbox_foldl_writeLoggedOne`). The own-key branch recovers the public relation
    from that leaf name through `Leaf.lean::publicOfLeaf`, and
    `Leaf.lean::publicOfLeaf_rawWriteRels` is the round trip at EVERY minted index — which
    is why `hNK` was replaced by `hWF` (the closure no longer collapses to `[t]`, and
    dot-freeness of the declared relation is what the round trip needs).

    ⚠ **`hroute` is MANDATORY and is not a guard-narrowing.** A derived def with no `Direct`
    arm at all (`CascadeStrata.lean::tvDer`, `viewer := editor but not banned`) routes to
    `[]`, so the write leg is the IDENTITY, the outbox stays empty and `cascadeKeys` is `[]`
    under ANY `affectedKeys` whatsoever — `tvDer_own_key_not_dirty` below is that control,
    in the kernel. Python refuses such a write at `TupleSource` admission, which the model
    calls `StoreValidRulesD`; the premise is discharged there, not assumed, by
    `rawWriteRels_ne_nil_of_exprDirectsAll`. It is NOT discharged by a `GraphAdmission`
    field: the routing fact is a theorem about the compiled plan tree. -/
theorem writeLeg_own_key_dirty {σ : GraphState} {S : Schema} {t : Tuple}
    (hWF : WF S) (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
    (hd : isDerived S (t.object.type, t.relation) = true)
    (honT : t.object.name ≠ STAR)
    (hroute : rawWriteRels S t ≠ []) :
    (t.object.type, t.relation, t.object.name)
      ∈ cascadeKeys S (σ.writeLoggedRules S t) := by
  obtain ⟨r, hr⟩ : ∃ r, r ∈ rawWriteRels S t := by
    cases hl : rawWriteRels S t with
    | nil => exact absurd hl hroute
    | cons r rs => exact ⟨r, List.mem_cons_self ..⟩
  have hu : ({ t with relation := r } : Tuple) ∈ rawWriteTuples S t :=
    List.mem_map.mpr ⟨r, hr, rfl⟩
  have hucl : ({ t with relation := r } : Tuple) ∈ rewriteClosureL S (rawWriteTuples S t) :=
    mem_rewriteClosureL_of_mem_seeds hu
  obtain ⟨d, hdmem, hnode, hleaf, hid⟩ :=
    mem_outbox_foldl_writeLoggedOne (rewriteClosureL S (rawWriteTuples S t)) σ hadm _ hucl
  have hnode' : d.node = ⟨t.object.type, t.object.name, r, Variant.plain⟩ := by
    rw [hnode]
    show objNode t.object r = _
    rw [objNode, if_neg honT]
  have hwm : (σ.writeLoggedRules S t).watermark = σ.watermark :=
    writeLoggedRules_watermark σ S t
  have hdmem' : d ∈ (σ.writeLoggedRules S t).outbox := hdmem
  have hfr : d ∈ (σ.writeLoggedRules S t).frontierRows := by
    unfold GraphState.frontierRows
    exact List.mem_filter.mpr ⟨hdmem', by rw [hwm]; simpa using hid⟩
  refine List.mem_flatMap.mpr ⟨d, hfr, ?_⟩
  unfold affectedKeys
  refine List.mem_append_left _ ?_
  rw [if_pos ⟨hleaf, by rw [hnode']; exact honT⟩]
  rw [show publicOfLeaf S d.node.type d.node.pred = some t.relation by
    rw [hnode']; exact publicOfLeaf_rawWriteRels hWF hd hr]
  rw [hnode']
  exact List.mem_singleton.mpr rfl

/-! ### ★ THE OWN-KEY FINDING, MECHANIZED

House rule (`docs/sabotage-procedure.md`): a mechanical refusal beats a doc warning. The
witness is deliberately IN-FRAGMENT: `LeafWitness.Sw` is
`approver := ([user] or viewer) but not banned`, whose derived key carries a `Direct` storage
arm, so `LeafWitness.tw = doc:d1#approver@user:bob` is a write the admission bundle accepts.
Post-flip it re-addresses onto the storage leaf `approver.0` and the single emitted delta
sits at `doc:d1#approver.0`, where `affectedKeys`' own-key branch tests
`isDerived S ("doc", "approver.0")` — false, because a minted leaf name is not a declared
key. The cascade therefore does NOT fire for the very write that needs it. -/

/-- The leaf-routed closure of the derived `approver` write: exactly its storage-leaf copy.
    (No rule matches an `approver.0` relation — `LeafRules.lean::LeafRuleWitness.lrSw_rules`
    shows the two rule leaves match `viewer` and `banned` — so the closure stops there.) -/
theorem swTw_closureL_eq :
    rewriteClosureL LeafWitness.Sw (rawWriteTuples LeafWitness.Sw LeafWitness.tw)
      = [⟨⟨"user", "bob", BARE⟩, leafPred "approver" 0, ⟨"doc", "d1"⟩⟩] := by
  decide

theorem swTw_foldAdmits :
    FoldAdmits (emptyState LeafWitness.Sw)
      (rewriteClosureL LeafWitness.Sw (rawWriteTuples LeafWitness.Sw LeafWitness.tw)) := by
  rw [swTw_closureL_eq]
  exact ⟨by decide, trivial⟩

/-- The whole write leg collapses to ONE logged step at the LEAF node — the shape the
    own-key branch no longer recognises. Pinned as an equation so the `decide` below runs on
    a concrete state instead of re-reducing the closure. -/
theorem swTw_writeLeg_eq :
    (emptyState LeafWitness.Sw).writeLoggedRules LeafWitness.Sw LeafWitness.tw
      = (emptyState LeafWitness.Sw).writeLoggedOne
          ⟨⟨"user", "bob", BARE⟩, leafPred "approver" 0, ⟨"doc", "d1"⟩⟩ := by
  unfold GraphState.writeLoggedRules
  rw [swTw_closureL_eq]
  rfl

/-- **(alpha), PINNED.** The derived `approver` write DOES dirty its own PUBLIC key, at the
    very witness where it did not before. The single emitted delta sits at the minted leaf
    node `doc:d1#approver.0`; `affectedKeys`' own-key branch now looks that name up through
    `publicOfLeaf` and recovers `approver`, exactly as Python's
    `key = (o_type, fam.owner_relation, o_name)` does.

    ⚠ **This `decide` is the cheapest permanent guard that (alpha) is really wired.** It was
    `swTw_own_key_not_dirty` (a `∉`) until (alpha) landed and went red on the first build
    after the `affectedKeys` re-point — that red is how the change was confirmed to bite.
    Revert the branch and it goes red again.

    ⚠ **LESSON CARRIED FORWARD from the deleted `Exec.lean::writeLeg_own_key_dirty_refuted_under_admission`
    block, because it outlives that particular refutation:** a `#check <refutation> <bridge>`
    line prints `… : False` whether or not the bridge type-checks — a mis-aimed composition
    prints the same thing as a correct one, and only the ERROR line carries the assurance.
    So never read a `#check … : False` as evidence on its own; read the build's exit code
    and the absence of an error at that line. -/
theorem swTw_own_key_dirty :
    ("doc", "approver", "d1") ∈
      cascadeKeys LeafWitness.Sw
        ((emptyState LeafWitness.Sw).writeLoggedRules LeafWitness.Sw LeafWitness.tw) := by
  rw [swTw_writeLeg_eq]
  decide

/-- The `tvDer` write leg is the IDENTITY: `rawWriteRels SlV tvDer = []` (the
    `excl (computed …) (computed …)` body has no `Direct` arm, hence no storage-bearing
    leaf), so the fold runs over the empty list. -/
theorem tvDer_writeLeg_eq :
    (emptyState LeafRuleWitness.SlV).writeLoggedRules LeafRuleWitness.SlV tvDer
      = emptyState LeafRuleWitness.SlV := by
  unfold GraphState.writeLoggedRules
  rw [tvDer_closureL_nil]
  rfl

/-- The routing itself, pinned: a derived def with NO `Direct` arm allocates no
    storage-bearing leaf, so `rawWriteRels` is empty. -/
theorem tvDer_rawWriteRels_nil : rawWriteRels LeafRuleWitness.SlV tvDer = [] := by decide

/-- **NECESSITY CONTROL for `writeLeg_own_key_dirty`'s `hroute` premise** — the sabotage,
    as a permanent theorem rather than a docstring. Drop `hroute` and the theorem it guards
    is FALSE, at this witness and with a mechanism (alpha) does not touch: `tvDer` is
    `doc:d1#viewer@group:g1#member` on `LeafRuleWitness.SlV`, whose `viewer` body is
    `excl (computed …) (computed …)` and therefore has no `Direct` arm; the write routes to
    `[]` (`tvDer_rawWriteRels_nil`), the fold is the identity (`tvDer_writeLeg_eq`), the
    outbox stays empty and `cascadeKeys` is `[]` under ANY `affectedKeys` whatsoever.

    ⚠ **The premise is a fenced-out counterexample only in the sense Python already fences
    it out.** `TupleSource` admission refuses a write with no matching `Direct` arm — the
    model's `StoreValidRulesD` — and `CascadeStrata.lean::tvDer_not_storeValidD` proves this
    very witness is outside it. So `hroute` narrows nothing that the modelled system admits,
    and it is DISCHARGED at the consumer from `StoreValidRulesD` by
    `rawWriteRels_ne_nil_of_exprDirectsAll`, never assumed.

    This replaces the deleted `writeLeg_own_key_dirty_refuted`: the statement it refuted is
    now a landed theorem, but the counterexample it exhibited is still the reason the
    premise exists, so it is kept as a positive `∉` pin instead of being thrown away
    (`docs/sabotage-procedure.md`'s durability ranking — a mechanical refusal beats a
    comment). -/
theorem tvDer_own_key_not_dirty :
    ("doc", "viewer", "d1") ∉
      cascadeKeys LeafRuleWitness.SlV
        ((emptyState LeafRuleWitness.SlV).writeLoggedRules LeafRuleWitness.SlV tvDer) := by
  rw [tvDer_writeLeg_eq]
  decide


/-! ⚠ **`removeLeg_own_key_dirty` was DELETED by step R5.** It said "a raw remove on a
derived key whose seed edge is PRESENT dirties its OWN key", and its proof rested on
`rewriteClosure_derived_eq_seed_nk` collapsing `removeLoggedRules` to a single
`removeLoggedOne` on `[t]`. Post-R5 the retraction folds
`rewriteClosureL S (rawWriteTuples S t)`, so that collapse is false, and the emitted delta
sits at a MINTED LEAF node rather than at the public derived node the statement names. Its
sole consumer (`removeLeg_inedges_eq_of_unmapped`) became UNCONDITIONAL and no longer needs
it. It is not restated: the remove leg would need the same routing premise the write leg's
own-key theorem carries PLUS a presence hypothesis on the leaf edge instead of the seed
edge, and nothing consumes the result. -/

/-- **The leaf-routed twin of `rewriteClosure_notarget_of_ne`** (step 4c-ii). Both new
    cases are refuted by NAME: a derived raw write's re-addressed seeds carry minted
    `leafPred` relations, and so do the `leafRewrites` outputs, while `R` is a derived key's
    own — dot-free — relation. Hence the new `hWF`.

    ⚠ **`hne` is CONDITIONAL, and that is a strengthening, not a weakening.** The seed
    branch only needs a node inequality when the raw write is UNTAINTED-addressed; when it
    is derived-addressed the branch is killed by the leaf NAME instead, with `hne` unused.
    Handing the hypothesis back on the derived arm is what lets
    `removeLeg_inedges_eq_of_unmapped` / `writeLeg_inedges_eq_of_unmapped` shed their
    own-key detour entirely: the conclusion holds for MORE `t`, so every consumer supplies
    less, never more. -/
theorem rewriteClosureL_notarget_of_ne {S : Schema} (hWF : WF S) {t : Tuple}
    {dt on R : String}
    (hder : isDerived S (dt, R) = true)
    (hne : isDerived S (t.object.type, t.relation) = false →
      objNode t.object t.relation ≠ objNode ⟨dt, on⟩ R) :
    ∀ w ∈ rewriteClosureL S (rawWriteTuples S t),
      objNode w.object w.relation ≠ objNode ⟨dt, on⟩ R := by
  intro w hw h2
  have hRok : relNameOK R := relNameOK_of_isDerived hWF (k := (dt, R)) hder
  have htype : dt = w.object.type := by
    simpa [objNode_type] using (congrArg NodeKey.type h2).symm
  have hrel : R = w.relation := by
    simpa [objNode_pred] using (congrArg NodeKey.pred h2).symm
  rcases rewriteClosureL_produced hw with hseed | ⟨r, hr', hro, hrout⟩
  · by_cases hd : isDerived S (t.object.type, t.relation) = true
    · obtain ⟨r0, hr0, hw0⟩ := List.mem_map.mp hseed
      obtain ⟨i, hi⟩ := mem_rawWriteRels_derived hd hr0
      have hwr : w.relation = r0 := by rw [← hw0]
      exact leafPred_ne_relName hRok t.relation i (by rw [← hi, ← hwr, ← hrel])
    · rw [rawWriteTuples_untainted (by simpa using hd)] at hseed
      rw [List.mem_singleton.mp hseed] at h2
      exact hne (by simpa using hd) h2
  · exact noRuleOutputsL_of_derived hWF hder r hr'
      ⟨hro.trans htype.symm, hrout.trans hrel.symm⟩

/-- **The leaf-routed twin of `ReconcileCorrect.lean::rewriteClosure_rel_ne_bare_d`** —
    the widened-admission form of obligation (F). It is the two-line corollary of
    `LeafRules.lean::rewriteClosureL_rel_ne_bare_of_rel`, whose premise is exactly the
    consequence `storeValidRulesD_declared` + `lookup_rel_ne_bare` extract from the store. -/
theorem rewriteClosureL_rel_ne_bare_d {S : Schema} {T : Store} (hWF : WF S)
    (hSV : StoreValidRulesD S T) {t : Tuple} (ht : t ∈ T) {u : Tuple}
    (hu : u ∈ rewriteClosureL S (rawWriteTuples S t)) : u.relation ≠ BARE := by
  obtain ⟨e, hlk⟩ := storeValidRulesD_declared hSV t ht
  exact rewriteClosureL_rel_ne_bare_of_rel hWF (lookup_rel_ne_bare hWF hlk) hu

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
    {dt on R : String} (hWF : WF S)
    (hder : isDerived S (dt, R) = true)
    (hne : isDerived S (t.object.type, t.relation) = false →
      objNode t.object t.relation ≠ objNode ⟨dt, on⟩ R)
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.writeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  constructor
  · intro h
    rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).edges] at h
    rcases foldl_writeBridgedOne_edges_sound (rewriteClosureL S (rawWriteTuples S t)) h
      with hold | ⟨w, hw, _h1, h2⟩ | ⟨_, h2⟩
    · exact hold
    · exact absurd h2.symm (rewriteClosureL_notarget_of_ne hWF hder hne w hw)
    · -- ★ `P6` step 3b: the bridge disjunct dies by variant, as at the W3d twin.
      exact absurd (congrArg NodeKey.variant h2) (objNode_ne_wAny ⟨dt, on⟩ R)
  · exact fun h => writeLoggedRules_edges_mono σ S t _ h

/-- **Retraction-leg in-edge preservation at a derived node, from node inequality
    alone** (the `_d` replacement for `removeLeg_derived_inedges_eq`).

    **RE-POINTED by step R5**, onto `rewriteClosureL S (rawWriteTuples S t)` and the L twin
    `rewriteClosureL_notarget_of_ne` — hence the new `hWF` and the CONDITIONAL `hne`. -/
theorem removeLeg_derived_inedges_eq_d {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R : String}
    (hWF : WF S)
    (hder : isDerived S (dt, R) = true)
    (hne : isDerived S (t.object.type, t.relation) = false →
      objNode t.object t.relation ≠ objNode ⟨dt, on⟩ R)
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.removeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) := by
  unfold GraphState.removeLoggedRules
  exact mem_foldl_removeLoggedOne_edges_iff_of_notarget
    (rewriteClosureL S (rawWriteTuples S t))
    (rewriteClosureL_notarget_of_ne hWF hder hne) (objNode_ne_wAny ⟨dt, on⟩ R) σ

/-- The seed node of an UNMAPPED derived key's write differs from the key's node:
    were they equal, the write would sit on the (derived) key itself and the
    own-key branch would have dirtied it.

    Carries `writeLeg_own_key_dirty`'s two new binders verbatim — `hWF` (which replaced
    `hNK`) and the routing premise `hroute` — and forwards them. Its single consumer,
    `writeLeg_sem_stable2_d`'s `hneKey` step, discharges `hroute` from
    `StoreValidRulesD S (t :: T)` via `rawWriteRels_ne_nil_of_exprDirectsAll`. -/
theorem write_node_ne_of_unmapped {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R : String}
    (hWF : WF S) (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
    (hder : isDerived S (dt, R) = true) (hon : on ≠ STAR)
    (honT : t.object.name ≠ STAR)
    (hroute : rawWriteRels S t ≠ [])
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t)) :
    objNode t.object t.relation ≠ objNode ⟨dt, on⟩ R := by
  intro heq
  have heq' : objNode ⟨t.object.type, t.object.name⟩ t.relation = objNode ⟨dt, on⟩ R := heq
  obtain ⟨h1, h2, h3⟩ := objNode_inj_of_ne_star honT hon heq'
  have hd : isDerived S (t.object.type, t.relation) = true := by
    rw [h1, h3]
    exact hder
  have := writeLeg_own_key_dirty hWF hadm hd honT hroute
  rw [h1, h2, h3] at this
  exact hunmapped this

/-- **Write-leg in-edge preservation at a derived key — UNCONDITIONAL post-R5**, the exact
    mirror of `removeLeg_inedges_eq_of_unmapped`.

    ⚠ **It used to need `hunmapped` and the own-key route.** The old proof split on whether
    the raw write sat ON the key: node inequality gave preservation; node EQUALITY was
    pushed through `writeLeg_own_key_dirty` (the write dirties its own key, contradicting
    unmappedness). Under `WF S` that split is unnecessary — no member of
    `rewriteClosureL S (rawWriteTuples S t)` targets a PUBLIC derived node at all (seeds are
    minted leaf names when `t` is derived-addressed; rule outputs are killed by
    `noRuleOutputsL_of_derived`) — so the equality case never arises. `hNK`, `hadm` and
    `hunmapped` all drop out, and the ONLY remaining consumer of `writeLeg_own_key_dirty` is
    `writeLeg_sem_stable2_d`'s `hneKey` step, which is the one site that genuinely needs
    own-key dirtiness. Consumers pass FEWER arguments, never more. -/
theorem writeLeg_inedges_eq_of_unmapped {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R : String}
    (hWF : WF S)
    (hder : isDerived S (dt, R) = true) (hon : on ≠ STAR)
    (honT : t.object.name ≠ STAR)
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.writeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) :=
  writeLeg_derived_inedges_eq_d hWF hder
    (fun hUT heq => by
      have heq' : objNode ⟨t.object.type, t.object.name⟩ t.relation = objNode ⟨dt, on⟩ R := heq
      obtain ⟨h1, _h2, h3⟩ := objNode_inj_of_ne_star honT hon heq'
      have hcon : isDerived S (dt, R) = false := by rw [← h1, ← h3]; exact hUT
      rw [hcon] at hder
      exact Bool.noConfusion hder) u

/-- **Retraction-leg in-edge preservation at a derived key — UNCONDITIONAL post-R5.**

    ⚠ **This used to need `hunmapped` and an own-key detour, and no longer does.** The old
    proof split on whether the raw write sat ON the key: node inequality gave preservation,
    node EQUALITY was pushed through `removeLeg_own_key_dirty` (present seed edge ⇒ the
    retraction dirties the own key ⇒ contradiction with unmappedness) or through the
    singleton-closure identity (absent seed edge). Both halves rested on
    `rewriteClosure_derived_eq_seed_nk` collapsing the retraction fold to ONE
    `removeLoggedOne` — which R5 makes false, since the fold now runs over the leaf-routed
    closure. `removeLeg_own_key_dirty` is deleted with them.

    The replacement is strictly better: under `WF S`, NO member of
    `rewriteClosureL S (rawWriteTuples S t)` targets a PUBLIC derived node at all — seeds
    are minted leaf names when `t` is derived-addressed, and rule outputs are killed by
    `noRuleOutputsL_of_derived` — so the equality case never arises and the whole
    hypothesis `hunmapped` drops out. Consumers pass FEWER arguments, never more. -/
theorem removeLeg_inedges_eq_of_unmapped {σ : GraphState} {S : Schema} {t : Tuple}
    {dt on R : String}
    (hWF : WF S)
    (hder : isDerived S (dt, R) = true) (hon : on ≠ STAR)
    (honT : t.object.name ≠ STAR)
    (u : NodeKey) :
    ((u, objNode ⟨dt, on⟩ R) ∈ (σ.removeLoggedRules S t).edges
      ↔ (u, objNode ⟨dt, on⟩ R) ∈ σ.edges) :=
  removeLeg_derived_inedges_eq_d hWF hder
    (fun hUT heq => by
      have heq' : objNode ⟨t.object.type, t.object.name⟩ t.relation = objNode ⟨dt, on⟩ R := heq
      obtain ⟨h1, _h2, h3⟩ := objNode_inj_of_ne_star honT hon heq'
      have hcon : isDerived S (dt, R) = false := by rw [← h1, ← h3]; exact hUT
      rw [hcon] at hder
      exact Bool.noConfusion hder) u

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
    rcases foldl_writeBridgedOne_edges_sound (rewriteClosureL S (rawWriteTuples S t)) hab
      with hold | ⟨u, hu, _, h2⟩ | ⟨hbr, h2⟩
    · exact ih hWF hDAB (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) a b hold
    · rw [h2, objNode_pred]
      exact rewriteClosureL_rel_ne_bare_d hWF hSV List.mem_cons_self hu
    · rw [h2]
      show (wAnyNode (a.type, a.pred)).pred ≠ BARE
      exact (bridgedInConcrete_elim hbr).2.2.1
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
    WF S →
    isDerived S (dt, R) = true →
    (∀ dt' R' e', S.lookup (dt', R') = some e' → isDerived S (dt', R') = true →
      DirectArmsBare e') →
    StoreValidRulesD S T →
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE := by
  -- `WF S` is new (step 4c-ii): the write case's rule branch now ranges over
  -- `schemaRewritesL`, whose leaf half is refuted by name (`noRuleOutputsL_of_derived`).
  induction h with
  | empty S =>
    intro _ _ _ _ x hx
    simp [emptyState] at hx
  | @write σp S T t hadm hprev ih =>
    intro hWF hder hDAB hSV x hx
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hx
    rcases foldl_writeBridgedOne_edges_sound (rewriteClosureL S (rawWriteTuples S t)) hx
      with hold | ⟨w, hw, h1, h2⟩ | ⟨_, h2⟩
    · exact ih hWF hder hDAB (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) x hold
    · -- a fresh closure edge into the R-node: the seed's stored subject is BARE by
      -- the widened admission; rule outputs never land on a derived key
      have htype : dt = w.object.type := by
        simpa [objNode_type] using congrArg NodeKey.type h2
      have hrel : R = w.relation := by
        simpa [objNode_pred] using congrArg NodeKey.pred h2
      rcases rewriteClosureL_produced hw with hseed | ⟨r, hr', hro, hrout⟩
      · -- a re-addressed SEED. `rawWriteTuples` rewrites the RELATION only, so the widened
        -- admission's BARE-subject clause still applies verbatim; the untainted disjunct is
        -- refuted because there `rawWriteTuples S t = [t]` and the target IS the seed's node.
        obtain ⟨r0, hr0, hw0⟩ := List.mem_map.mp hseed
        have hsubj : w.subject = t.subject := by rw [← hw0]
        rcases hSV t List.mem_cons_self with ⟨hf, _⟩ | ⟨_, hbare, _⟩
        · exfalso
          rw [rawWriteTuples_untainted hf] at hseed
          have hwt : w = t := List.mem_singleton.mp hseed
          rw [hwt] at htype hrel
          rw [← htype, ← hrel, hder] at hf
          exact Bool.noConfusion hf
        · rw [h1, subjNode_pred, hsubj]
          exact hbare
      · exact absurd ⟨hro.trans htype.symm, hrout.trans hrel.symm⟩
          (noRuleOutputsL_of_derived hWF hder r hr')
    · -- ★ `P6` step 3b: a bridge target is `wAny`; the goal's target is an `objNode`.
      exact absurd (congrArg NodeKey.variant h2) (objNode_ne_wAny ⟨dt, on⟩ R)
  | @remove σp S T t _ _ hSVT _ _ _ _ ih =>
    intro hWF hder hDAB _ x hx
    exact ih hWF hder hDAB (storeValidRulesD_of_storeValidRules_directArmsBare hSVT hDAB)
      x (mem_removeLoggedRules_edges hx)
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro hWF hder hDAB hSV x hx
    unfold runCascade2 at hx
    split at hx
    · have hx' : (x, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T
          (reconcileJobsLR S T σp jobs1) jobs2).edges := hx
      rcases reconcileJobsLR_edge_sound jobs2 _ x _ hx' with hmid | ⟨j, hj, c, hc, h1, _⟩
      · rcases reconcileJobsLR_edge_sound jobs1 σp x _ hmid
          with hold | ⟨j, hj, c, hc, h1, _⟩
        · exact ih hWF hder hDAB hSV x hold
        · obtain ⟨_, hcb, _⟩ := hjv1 j hj
          rw [h1, subjNode_pred]
          exact hcb c hc
      · obtain ⟨_, hcb, _⟩ := hjv2 j hj
        rw [h1, subjNode_pred]
        exact hcb c hc
    · exact ih hWF hder hDAB hSV x hx

/-- **Every in-edge source at a derived R-node is STAR-free, widened admission** (`_d`
    mirror of `CascadeStrataAssemble.lean::reachedByW3d2_Rnode_source_name_ne_star`, whose
    write case is `ComputedOnly`-powered — it rewrites with `writeLeg_derived_inedges_eq`,
    i.e. "a write leg never changes a derived key's in-edges", which is exactly what
    `StoreValidRulesD` makes false). Here the write leg's seed edge MAY land on the R-node;
    what pins it star-free is `DirectArmsConcrete` + the widened admission
    (`storeValidRulesD_derived_subject_ne_star`). Rule outputs never land on a derived key
    (`noRuleOutputs_of_derived`), and cascade edges are sourced at `W3cJobValid`'s star-free
    candidates. Structurally the true `pred = BARE` analogue of
    `reachedByW3d2_Rnode_source_bare_d` above.

    This is the prerequisite the E-chain Direct-arm widening needs for
    `w3cJobValid_enumJob2D`'s star-free-candidate clauses (`edgeHolders` half); the
    `storedDirectSubjects` half is `storedDirectSubjects_name_ne_star`. -/
theorem reachedByW3d2_Rnode_source_name_ne_star_d {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String}
    (h : ReachedByW3d2 σ S T) :
    WF S →
    isDerived S (dt, R) = true →
    (∀ dt' R' e', S.lookup (dt', R') = some e' → isDerived S (dt', R') = true →
      DirectArmsBare e') →
    DirectArmsConcrete S →
    StoreValidRulesD S T →
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.name ≠ STAR := by
  -- `WF S` is new (step 4c-ii), as in `reachedByW3d2_Rnode_source_bare_d`.
  induction h with
  | empty S =>
    intro _ _ _ _ _ x hx
    simp [emptyState] at hx
  | @write σp S T t hadm hprev ih =>
    intro hWF hder hDAB hDAC hSV x hx
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hx
    rcases foldl_writeBridgedOne_edges_sound (rewriteClosureL S (rawWriteTuples S t)) hx
      with hold | ⟨w, hw, h1, h2⟩ | ⟨_, h2⟩
    · exact ih hWF hder hDAB hDAC (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) x hold
    · -- a fresh closure edge into the R-node: it is a re-addressed SEED (rule outputs never
      -- land on a derived key, `noRuleOutputsL_of_derived`), and `rawWriteTuples` rewrites
      -- the RELATION only, so the seed's stored subject is star-free by the widened admission
      have htype : dt = w.object.type := by
        simpa [objNode_type] using congrArg NodeKey.type h2
      have hrel : R = w.relation := by
        simpa [objNode_pred] using congrArg NodeKey.pred h2
      rcases rewriteClosureL_produced hw with hseed | ⟨r, hr', hro, hrout⟩
      · obtain ⟨r0, hr0, hw0⟩ := List.mem_map.mp hseed
        have hsubj : w.subject = t.subject := by rw [← hw0]
        have hderT : isDerived S (t.object.type, t.relation) = true := by
          by_contra hcon
          rw [rawWriteTuples_untainted (by simpa using hcon)] at hseed
          have hwt : w = t := List.mem_singleton.mp hseed
          rw [hwt] at htype hrel
          rw [← htype, ← hrel] at hcon
          exact hcon hder
        have hne : t.subject.name ≠ STAR :=
          storeValidRulesD_derived_subject_ne_star hDAC hSV List.mem_cons_self hderT
        have hnm : (subjNode t.subject).name = t.subject.name := by
          unfold subjNode; split
          · next hs => exact hs.symm
          · rfl
        rw [h1, hsubj, hnm]
        exact hne
      · exact absurd ⟨hro.trans htype.symm, hrout.trans hrel.symm⟩
          (noRuleOutputsL_of_derived hWF hder r hr')
    · -- ★ `P6` step 3b: a bridge target is `wAny`; the goal's target is an `objNode`.
      exact absurd (congrArg NodeKey.variant h2) (objNode_ne_wAny ⟨dt, on⟩ R)
  | @remove σp S T t _ _ hSVT _ _ _ _ ih =>
    intro hWF hder hDAB hDAC _ x hx
    exact ih hWF hder hDAB hDAC (storeValidRulesD_of_storeValidRules_directArmsBare hSVT hDAB)
      x (mem_removeLoggedRules_edges hx)
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro hWF hder hDAB hDAC hSV x hx
    unfold runCascade2 at hx
    split at hx
    · have hx' : (x, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T
          (reconcileJobsLR S T σp jobs1) jobs2).edges := hx
      rcases reconcileJobsLR_edge_sound jobs2 _ x _ hx' with hmid | ⟨j, hj, c, hc, h1, _⟩
      · rcases reconcileJobsLR_edge_sound jobs1 σp x _ hmid
          with hold | ⟨j, hj, c, hc, h1, _⟩
        · exact ih hWF hder hDAB hDAC hSV x hold
        · obtain ⟨_, _, hcS, _⟩ := hjv1 j hj
          rw [h1, subjNode_plain (hcS c hc)]
          exact hcS c hc
      · obtain ⟨_, _, hcS, _⟩ := hjv2 j hj
        rw [h1, subjNode_plain (hcS c hc)]
        exact hcS c hc
    · exact ih hWF hder hDAB hDAC hSV x hx

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
    (reachedByW3d2_Rnode_source_bare_d h hWF hder hDAB hSV x hxv)

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
    (hWF : WF S) (hNK : NodupKeys S) (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
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
      have hedge' := (writeLeg_inedges_eq_of_unmapped hWF hder' hon honT x).mpr
        hedge
      have := reach_complete hclσ' (NReaches.edge hedge')
      rw [h1] at this
      cases this
    · exfalso
      have hedge' := hcol' x (reach_sound h1)
      have hedge := (writeLeg_inedges_eq_of_unmapped hWF hder' hon honT x).mp
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
    (hWF : WF S) (hNK : NodupKeys S) (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
    (honT : t.object.name ≠ STAR)
    (hσS : σ.schema = S)
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant ≠ Variant.wAll)
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
    rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).schema, writeRulesRaw_schema, hσS]
  have hclσ' : ∀ ab ∈ (σ.writeLoggedRules S t).edges,
      ab.1 ∈ (σ.writeLoggedRules S t).nodes ∧ ab.2 ∈ (σ.writeLoggedRules S t).nodes := by
    have hev := writeLoggedRules_evalEq (EvalEq.refl σ) S t
    intro ab hab
    rw [hev.edges] at hab
    rw [hev.nodes]
    exact edgesClosed_foldl_writeBridgedOne (rewriteClosureL S (rawWriteTuples S t)) σ hclσ ab hab
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
    exact writeLeg_probeDerived_stable_d hWF hNK hadm hd' honT hclσ hclσ' hcol hcol'
      (hopsUnmapped r' hr' hd') hon

/-- Retraction-leg `probeDerived` stability at an UNMAPPED derived operand key, `_d`. -/
theorem removeLeg_probeDerived_stable_d {σ : GraphState} {S : Schema} {t : Tuple}
    (hWF : WF S) (hNK : NodupKeys S)
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
      have hedge' := (removeLeg_inedges_eq_of_unmapped hWF hder' hon honT x).mpr
        hedge
      have := reach_complete hclσ' (NReaches.edge hedge')
      rw [h1] at this
      cases this
    · exfalso
      have hedge' := hcol' x (reach_sound h1)
      have hedge := (removeLeg_inedges_eq_of_unmapped hWF hder' hon honT x).mp
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
    (hWF : WF S) (hNK : NodupKeys S) (honT : t.object.name ≠ STAR)
    (hσS : σ.schema = S)
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp : ∀ ab ∈ σ.edges, ab.2.variant ≠ Variant.wAll)
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
    exact removeLeg_probeDerived_stable_d hWF hNK hd' honT hclσ hclσ' hcol hcol'
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
    (hcr : ComputedRefsNotLeaf S)
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
        checkFn_agree_of_graphRec_notLeafNode T s dt on R e hco hcr hlk hleafUnt
          (fun s' r' hnl hr' => shadow_graphRec_agree hsh s' on hnl hr')
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
    (hcr : ComputedRefsNotLeaf S)
    (h0 : ReachedByRulesAdmitted σ0 S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh : UntaintedShadow S σ σ0)
    (h0' : ReachedByRulesAdmitted σ0' S
      ((t :: T).filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh' : UntaintedShadow S (σ.writeLoggedRules S t) σ0')
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp' : ∀ ab ∈ (σ.writeLoggedRules S t).edges, ab.2.variant ≠ Variant.wAll)
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
        (checkFn_eq_sem_w3d_filt hWF hTT hNK hR hSV hBS hTS hMatch hStrat hcr hterm
          h0' hsh' hlk hco hleafUnt hs hon).symm
    _ = σ.checkFn (t :: T) s dt on R e :=
        writeLeg_checkFn_stable (t :: T) hclσ htp' hlk hder hco hon hunmapped s
    _ = σ.checkFn T s dt on R e := checkFn_store_irrel _ _ s dt on R hco
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3d_filt hWF hTT hNK hR hSVw hBSw hTSw hMatch hStrat hcr htermw
          h0 hsh hlk hco hleafUnt hs hon

/-- **Stratum-1 `sem` stability across a retraction leg, filtered-σ0 form** (`_d`
    clone of `removeLeg_sem_stable_sh`). -/
theorem removeLeg_sem_stable_sh_d {σ σ0 σ0' : GraphState} {S : Schema} {T : Store}
    {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRulesD S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hcr : ComputedRefsNotLeaf S)
    (ht : t ∈ T)
    (h0 : ReachedByRulesAdmitted σ0 S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh : UntaintedShadow S σ σ0)
    (h0' : ReachedByRulesAdmitted σ0' S
      ((T.erase t).filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh' : UntaintedShadow S (σ.removeLoggedRules S t) σ0')
    (hclσ : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (htp : ∀ ab ∈ σ.edges, ab.2.variant ≠ Variant.wAll)
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
        (checkFn_eq_sem_w3d_filt hWF hTT hNK hR hSVe hBSe hTSe hMatch hStrat hcr hterme
          h0' hsh' hlk hco hleafUnt hs hon).symm
    _ = σ.checkFn (T.erase t) s dt on R e :=
        removeLeg_checkFn_stable (T.erase t) hclσ htp hlk hder hco hon hunmapped s
    _ = σ.checkFn T s dt on R e := checkFn_store_irrel _ _ s dt on R hco
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3d_filt hWF hTT hNK hR hSV hBS hTS hMatch hStrat hcr hterm
          h0 hsh hlk hco hleafUnt hs hon

/-! ### Per-key settledness transports, widened admission -/

/-- **`SettledKey` transports across a write leg given `sem` stability, `_d`** —
    representation untouched: rows write-inert, and the UNMAPPED key's derived
    in-edges fixed by own-key dirtiness (no `StoreValidRules`/`ComputedOnly`). -/
theorem settledKey_writeLeg_sem_d {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hNK : NodupKeys S) (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
    (honT : t.object.name ≠ STAR)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
    rw [writeLeg_inedges_eq_of_unmapped hWF hder hon honT
      (subjNode s)] at hedge'
    rw [hsem s (fun hx => absurd hx hstar)]
    exact hedge s hb hstar hedge'

/-- **`CompleteKey` transports across a write leg given `sem` stability, `_d`.** -/
theorem completeKey_writeLeg_sem_d {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hNK : NodupKeys S) (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
    (honT : t.object.name ≠ STAR)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
    rw [writeLeg_inedges_eq_of_unmapped hWF hder hon honT (subjNode s)]
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
    (hWF : WF S) (hNK : NodupKeys S) (honT : t.object.name ≠ STAR)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
    rw [removeLeg_inedges_eq_of_unmapped hWF hder hon honT
      (subjNode s)] at hedge'
    rw [hsem s (fun hx => absurd hx hstar)]
    exact hedge s hb hstar hedge'

/-- **`CompleteKey` transports across a retraction leg given `sem` stability, `_d`.** -/
theorem completeKey_removeLeg_sem_d {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hNK : NodupKeys S) (honT : t.object.name ≠ STAR)
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
    rw [removeLeg_inedges_eq_of_unmapped hWF hder hon honT (subjNode s)]
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
    (hQ : TtuTargetsSat S NotLeafName) (hDR : DirectRestrictionsNotLeaf S)
    (hLS : LeafScope S)
    (hcr : ComputedRefsNotLeaf S)
    (hNBD : NoBridgedDerived S)
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
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2 σ S T) (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t)))
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
  obtain ⟨σ0, h0, hsh⟩ :=
    reachedByW3d2_shadow_d h hNK hCD hDAB hSVw htermw hWF hBSw hQ hDR hLS hMatch
      hNBD hTT hTSw
  obtain ⟨σ0', h0', hsh'⟩ :=
    reachedByW3d2_shadow_d h' hNK hCD hDAB hSV hterm hWF hBS hQ hDR hLS hMatch
      hNBD hTT hTS
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
        hStrat hterm hcr h0 hsh h0' hsh' hclσ htp' hlk' hd' hco' hleafUnt'
        (hopsUnmapped r' hr' hd') hx hon
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨settledKey_writeLeg_sem_d hWF hNK hadm honT hWSbare hd' hon
        (hopsUnmapped r' hr' hd') hsem_op hset,
      completeKey_writeLeg_sem_d hWF hNK hadm honT hWSbare hd' hon
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
    · -- the routing obligation, discharged from the WIDENED store admission rather than
      -- carried: on this branch `t` sits on the derived key `(dt, R)`, so `StoreValidRulesD`
      -- must take its derived disjunct and hands back a `Direct` arm of `e` that admits
      -- `t`'s subject — which `rawWriteRels_ne_nil_of_exprDirectsAll` turns into a leaf.
      have hdt : isDerived S (t.object.type, t.relation) = true := by rw [h1, h2]; exact hder
      have hroute : rawWriteRels S t ≠ [] := by
        rcases hSV t List.mem_cons_self with ⟨hun, _⟩ | ⟨_, _, e', rs', hlk', hrs', hrm', _⟩
        · rw [hdt] at hun; exact Bool.noConfusion hun
        · exact rawWriteRels_ne_nil_of_exprDirectsAll hdt hlk' hrs' hrm'
      refine write_node_ne_of_unmapped hWF hadm hder hon honT hroute hunmapped ?_
      show objNode t.object t.relation = objNode ⟨dt, on⟩ R
      rw [show t.object = (⟨t.object.type, t.object.name⟩ : ObjectRef) from rfl,
        h1, h2, h3]
    · exact honT h3
  calc sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩
      = (σ.writeLoggedRules S t).checkFnR (t :: T) s dt on R e :=
        (checkFnR_eq_sem_settled_d_filt hWF hTT hNK hR hSV hBS hTS hMatch hStrat
          hterm hcr hWSbare h0' hsh' hσ'S hlk hder hcd hba hCOop_e hLU2e hops' hs hon).symm
    _ = (σ.writeLoggedRules S t).checkFnR T s dt on R e :=
        checkFnR_cons_irrel_cd hcd hba hon hneKey
    _ = σ.checkFnR T s dt on R e :=
        writeLeg_checkFnR_stable_d T hWF hNK hadm honT hσS hclσ htp' hlk hder hcd hba
          hcolOps hon hunmapped hopsUnmapped s
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFnR_eq_sem_settled_d_filt hWF hTT hNK hR hSVw hBSw hTSw hMatch hStrat
          htermw hcr hWSbare h0 hsh hσS hlk hder hcd hba hCOop_e hLU2e hops hs hon

/-- **Stratum-2 `sem` stability across a retraction leg, widened admission**
    (`removeLeg_sem_stable2_d`). Carries the `remove` constructor's own guards (the
    pre store is PLAIN-valid and drained) plus `hNoUD`, under which the pre store
    provably contains NO derived-key tuple — the erased tuple's key is untainted, so
    every derived key's grant window and in-edges are untouched. -/
theorem removeLeg_sem_stable2_d {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSVT : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hQ : TtuTargetsSat S NotLeafName) (hDR : DirectRestrictionsNotLeaf S)
    (hLS : LeafScope S)
    (hcr : ComputedRefsNotLeaf S)
    (hNBD : NoBridgedDerived S)
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
    (hWSbare : ∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE)
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
  obtain ⟨σ0, h0, hsh⟩ :=
    reachedByW3d2_shadow_d h hNK hCD hDAB hSVD hterm hWF hBS hQ hDR hLS hMatch hNBD hTT hTS
  obtain ⟨σ0', h0', hsh'⟩ :=
    reachedByW3d2_shadow_d h' hNK hCD hDAB hSVDe hterme hWF hBSe hQ hDR hLS hMatch
      hNBD hTT hTSe
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
    exact (removeLeg_derived_inedges_eq_d hWF hd' (fun _ => hneOp r' hd') u).mpr hpreu
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
        hStrat hterm hcr ht h0 hsh h0' hsh' hclσ htp hlk' hd' hco' hleafUnt'
        (hopsUnmapped r' hr' hd') hx hon
    obtain ⟨hset, hcomp⟩ := hopsSettled r' hr' hd'
    exact ⟨settledKey_removeLeg_sem_d hWF hNK honT hWSbare hd' hon
        (hopsUnmapped r' hr' hd') hsem_op hset,
      completeKey_removeLeg_sem_d hWF hNK honT hWSbare hd' hon
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
          hterme hcr hWSbare h0' hsh' hσ'S hlk hder hcd hba hCOop_e hLU2e hops' hs hon).symm
    _ = (σ.removeLoggedRules S t).checkFnR T s dt on R e :=
        checkFnR_erase_irrel_cd hcd hba hon hneKey
    _ = σ.checkFnR T s dt on R e :=
        removeLeg_checkFnR_stable_d T hWF hNK honT hσS hclσ htp hlk hder hcd hba
          hcolOps hon hunmapped hopsUnmapped s
    _ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFnR_eq_sem_settled_d_filt hWF hTT hNK hR hSVD hBS hTS hMatch hStrat
          hterm hcr hWSbare h0 hsh hσS hlk hder hcd hba hCOop_e hLU2e hops hs hon

/-- **Routed no-ghost-star-coverage (`hcovDecl`).** A `checkFnR`-true star read at a
    derived key with settled derived operands means the shape is declared. Factored from
    `graph_correct_w3d2` (`CascadeStrataResettle.lean:1458-1485`). -/
theorem checkFnR_star_declared {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hTT : TtuTuplesetsDirect S) (hSV : StoreValidRules S T) (hTS : TtuStarFree S T)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (hschema : σ.schema = S) {dt on R : String} {e : Expr}
    (hcr : ComputedRefsNotLeaf S) (hlk : S.lookup (dt, R) = some e)
    (hco : ComputedOnly e) (hqo : on ≠ STAR)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') → (u, objNode ⟨dt, on⟩ r') ∈ σ.edges))
    {sh : Shape} (hchk : σ.checkFnR T (starSubj sh) dt on R e = true) :
    sh ∈ declaredWildcardShapes S := by
  unfold GraphState.checkFnR at hchk
  obtain ⟨r', hr', hleaf⟩ := evalE_computedOnly_true_leaf e hco hchk
  unfold GraphModel.graphRecR at hleaf
  cases hd' : isDerived S (dt, r') with
  | false =>
    rw [GraphModel.check_untainted _ _ (by rw [hschema]; exact hd')] at hleaf
    have hnl : ¬ LeafNode S (objNode ⟨dt, on⟩ r') :=
      notLeafNode_of_computedRef hcr hlk hr'
    have hleaf0 : GraphModel.graphRec σ0 (starSubj sh) dt on r' = true := by
      rw [← shadow_graphRec_agree hsh (starSubj sh) on hnl hd']
      exact hleaf
    exact graphRec_star_declared hTT hSV hTS h0 hleaf0
  | true =>
    rw [GraphModel.check_derived _ _ (by rw [hschema]; exact hd')] at hleaf
    rw [probeDerived_eq _ hqo, if_pos (show (starSubj sh).name = STAR from rfl)] at hleaf
    obtain ⟨hset', _, _⟩ := hops r' hr' hd'
    cases hrow : σ.residue (objNode ⟨dt, on⟩ r') r' with
    | none => rw [hrow, Option.getD_none] at hleaf; exact absurd hleaf Bool.false_ne_true
    | some res =>
      rw [hrow, Option.getD_some] at hleaf
      obtain ⟨hstars_iff, _, _⟩ := hset'.1 res hrow
      exact ((hstars_iff sh).mp hleaf).1

/-- **Routed no-ghost-star-coverage, Direct-arm-widened (`checkFnR_star_declared_d`).** The
    `StoreValidRulesD` + `ComputedOrDirect`/`DirectArmsBare` analog of `checkFnR_star_declared`.
    A true routed star read of shape `sh` at a Direct-arm derived def certifies `sh` declared:
    a true COMPUTED leaf rides the shadow (`graphRec_star_declared_d`, untainted) or the settled
    `stars` row (derived); a true `Direct` arm rides `directArm_star_declared` (a stored bare-STAR
    grant of shape `sh` is a wildcard-flagged restriction of the def). -/
theorem checkFnR_star_declared_d {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hTT : TtuTuplesetsDirect S) (hSV : StoreValidRulesD S T) (hTS : TtuStarFree S T)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (hschema : σ.schema = S) {dt on R : String} {e : Expr}
    (hcr : ComputedRefsNotLeaf S)
    (_hNBD : NoBridgedDerived S)
    (hlk : S.lookup (dt, R) = some e) (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hqo : on ≠ STAR)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') → (u, objNode ⟨dt, on⟩ r') ∈ σ.edges))
    {sh : Shape} (hchk : σ.checkFnR T (starSubj sh) dt on R e = true) :
    sh ∈ declaredWildcardShapes S := by
  unfold GraphState.checkFnR at hchk
  rcases evalE_computedOrDirect_true_leaf e hcd hchk with ⟨r', hr', hleaf⟩ | ⟨rs, hrs, hdl⟩
  · unfold GraphModel.graphRecR at hleaf
    cases hd' : isDerived S (dt, r') with
    | false =>
      rw [GraphModel.check_untainted _ _ (by rw [hschema]; exact hd')] at hleaf
      have hnl : ¬ LeafNode S (objNode ⟨dt, on⟩ r') :=
        notLeafNode_of_computedRef hcr hlk hr'
      have hleaf0 : GraphModel.graphRec σ0 (starSubj sh) dt on r' = true := by
        rw [← shadow_graphRec_agree hsh (starSubj sh) on hnl hd']
        exact hleaf
      exact graphRec_star_declared_d hTT hSV hTS h0 hleaf0
    | true =>
      rw [GraphModel.check_derived _ _ (by rw [hschema]; exact hd')] at hleaf
      rw [probeDerived_eq _ hqo, if_pos (show (starSubj sh).name = STAR from rfl)] at hleaf
      obtain ⟨hset', _, _⟩ := hops r' hr' hd'
      cases hrow : σ.residue (objNode ⟨dt, on⟩ r') r' with
      | none => rw [hrow, Option.getD_none] at hleaf; exact absurd hleaf Bool.false_ne_true
      | some res =>
        rw [hrow, Option.getD_some] at hleaf
        obtain ⟨hstars_iff, _, _⟩ := hset'.1 res hrow
        exact ((hstars_iff sh).mp hleaf).1
  · exact directArm_star_declared hlk hba hrs hdl

/-- **Routed no-ghost-star-coverage over the FILTERED shadow
    (`checkFnR_star_declared_d_filt`).** `checkFnR_star_declared_d` with the base witness
    σ0 admitted over `T↾U` — the pair the filtered shadow (`reachedByW3d2_shadow_d`)
    produces. Only the untainted COMPUTED branch touches σ0: `graphRec_star_declared_d`
    instantiates at `T↾U` (its `hSV`/`h0` stores are coupled; the conclusion is
    store-free). The derived branch reads the settled `stars` row and the `Direct` arm
    reads the FULL store — both unchanged. -/
theorem checkFnR_star_declared_d_filt {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hTT : TtuTuplesetsDirect S) (hSV : StoreValidRulesD S T) (hTS : TtuStarFree S T)
    (h0 : ReachedByRulesAdmitted σ0 S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh : UntaintedShadow S σ σ0)
    (hschema : σ.schema = S) {dt on R : String} {e : Expr}
    (hcr : ComputedRefsNotLeaf S)
    (_hNBD : NoBridgedDerived S)
    (hlk : S.lookup (dt, R) = some e) (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hqo : on ≠ STAR)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') → (u, objNode ⟨dt, on⟩ r') ∈ σ.edges))
    {sh : Shape} (hchk : σ.checkFnR T (starSubj sh) dt on R e = true) :
    sh ∈ declaredWildcardShapes S := by
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
  have hTSU : TtuStarFree S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    fun t ht => hTS t (List.mem_filter.mp ht).1
  unfold GraphState.checkFnR at hchk
  rcases evalE_computedOrDirect_true_leaf e hcd hchk with ⟨r', hr', hleaf⟩ | ⟨rs, hrs, hdl⟩
  · unfold GraphModel.graphRecR at hleaf
    cases hd' : isDerived S (dt, r') with
    | false =>
      rw [GraphModel.check_untainted _ _ (by rw [hschema]; exact hd')] at hleaf
      have hnl : ¬ LeafNode S (objNode ⟨dt, on⟩ r') :=
        notLeafNode_of_computedRef hcr hlk hr'
      have hleaf0 : GraphModel.graphRec σ0 (starSubj sh) dt on r' = true := by
        rw [← shadow_graphRec_agree hsh (starSubj sh) on hnl hd']
        exact hleaf
      exact graphRec_star_declared_d hTT hSVU_D hTSU h0 hleaf0
    | true =>
      rw [GraphModel.check_derived _ _ (by rw [hschema]; exact hd')] at hleaf
      rw [probeDerived_eq _ hqo, if_pos (show (starSubj sh).name = STAR from rfl)] at hleaf
      obtain ⟨hset', _, _⟩ := hops r' hr' hd'
      cases hrow : σ.residue (objNode ⟨dt, on⟩ r') r' with
      | none => rw [hrow, Option.getD_none] at hleaf; exact absurd hleaf Bool.false_ne_true
      | some res =>
        rw [hrow, Option.getD_some] at hleaf
        obtain ⟨hstars_iff, _, _⟩ := hset'.1 res hrow
        exact ((hstars_iff sh).mp hleaf).1
  · exact directArm_star_declared hlk hba hrs hdl

end Zanzibar
