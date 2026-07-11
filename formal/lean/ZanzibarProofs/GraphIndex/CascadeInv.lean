import ZanzibarProofs.GraphIndex.CascadeSettle

/-!
# The structural invariant over the interleaved W3d chain (ROADMAP W3d-1c, part 3a)

The deferred T2a carry for W3d (`reachedByW3d_inv`, HANDOFF "The next task", point 3)
asks for `Inv S σ` at every state of the interleaved scheduler chain. This file
discharges the **structural half** — `StructInv` (schema fixity, node encoding, edge
endpoint-closure, and ACYCLICITY) — unconditionally, i.e. with none of the fragment
hypotheses (`RootBoolean`/`hterm`/…) the residue-hygiene (I6) clauses need.

The key observation is that acyclicity is *free* on the W3d chain: every edge added by
the model is a `writeDirect`, which **cycle-rejects internally** (`admitEdge` probes for
a back-path via `reach_complete`, `Write.lean`), and every edge removed by the diffing
audit is a `removeEdgePair`, which only *shrinks* the edge set — so `NReaches` can only
shrink (`NReaches.mono_subset`). No terminality argument is needed here; the R-node
terminality the residue clauses lean on is a separate concern.

Faithfulness: this mirrors the graph index's structural invariants I1–I3 (node/edge
well-formedness) and the acyclicity the closure maintains by construction
(`ReachabilityIndex` refuses a self-reaching edge). The diffing audit's removals are
`processor.py:359-367` (`_write_derived(add=False)`); the model's `removeEdgePair`.
-/

namespace Zanzibar

/-! ## `StructInv` preservation for the residue/edge primitives -/

/-- **Edge removal preserves the structural invariant.** Same nodes/schema; endpoint
    closure via `edgesClosed_removeEdgePair`; acyclicity because the removed edge set is
    a subset (`removeEdgePair_edges_subset`) so `NReaches` can only shrink. -/
theorem structInv_removeEdgePair {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (a b : NodeKey) : StructInv S (σ.removeEdgePair a b) where
  schemaEq := by rw [removeEdgePair_schema]; exact h.schemaEq
  nodeEnc := by rw [removeEdgePair_nodes]; exact h.nodeEnc
  edgesClosed := edgesClosed_removeEdgePair h.edgesClosed a b
  acyclic := fun v hv =>
    h.acyclic v (NReaches.mono_subset (removeEdgePair_edges_subset σ a b) hv)

/-- The residue recompute is residue-only, so it preserves `StructInv` verbatim. -/
theorem structInv_reconcileResidueKey {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (T : Store) (dt on R : String) (e : Expr) (shapes : List Shape)
    (negCands uposCands : List SubjectRef) :
    StructInv S (σ.reconcileResidueKey T dt on R e shapes negCands uposCands) where
  schemaEq := by rw [reconcileResidueKey_schema]; exact h.schemaEq
  nodeEnc := by rw [reconcileResidueKey_nodes]; exact h.nodeEnc
  edgesClosed := by
    rw [reconcileResidueKey_edges, reconcileResidueKey_nodes]; exact h.edgesClosed
  acyclic := by rw [reconcileResidueKey_edges]; exact h.acyclic

/-- **The diffing edge audit preserves the structural invariant.** Each fold step is a
    `writeDirect` (cycle-rejecting, `structInv_writeDirect`) or a `removeEdgePair`
    (subset, `structInv_removeEdgePair`). -/
theorem structInv_reconcileKeyD {S : Schema} (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) {σ : GraphState}, StructInv S σ →
      StructInv S (σ.reconcileKeyD T dt on R e cands) := by
  intro cands
  induction cands with
  | nil => intro σ h; exact h
  | cons c rest ih =>
    intro σ h
    rw [reconcileKeyD_cons]
    split
    · exact ih (structInv_writeDirect h _)
    · exact ih (structInv_removeEdgePair h _ _)

/-- One full-object W3d reconcile (residue recompute then diffing edge audit) preserves
    `StructInv`. -/
theorem structInv_reconcileStarsKeyD {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (T : Store) (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef) :
    StructInv S (σ.reconcileStarsKeyD T dt on R e shapes cands negCands uposCands) := by
  unfold GraphState.reconcileStarsKeyD
  exact structInv_reconcileKeyD T dt on R e cands
    (structInv_reconcileResidueKey h T dt on R e shapes negCands uposCands)

/-! ## `StructInv` preservation for the scheduling primitives -/

/-- Pushing a delta row is outbox-only, so it preserves `StructInv`. -/
theorem structInv_pushDelta {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (k : NodeKey) (r : String) : StructInv S (σ.pushDelta k r) where
  schemaEq := by rw [pushDelta_schema]; exact h.schemaEq
  nodeEnc := by rw [pushDelta_nodes]; exact h.nodeEnc
  edgesClosed := by rw [pushDelta_edges, pushDelta_nodes]; exact h.edgesClosed
  acyclic := by rw [pushDelta_edges]; exact h.acyclic

/-- Overwriting the watermark is a structural no-op (schema/nodes/edges are unchanged). -/
theorem structInv_setWatermark {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (w : Nat) : StructInv S { σ with watermark := w } where
  schemaEq := h.schemaEq
  nodeEnc := h.nodeEnc
  edgesClosed := h.edgesClosed
  acyclic := h.acyclic

/-- A single logged routed-edge write preserves `StructInv` (accept branch =
    `writeDirect` then `pushDelta`; reject branch = identity). -/
theorem structInv_writeLoggedOne {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (t : Tuple) : StructInv S (σ.writeLoggedOne t) := by
  unfold GraphState.writeLoggedOne
  split
  · exact structInv_pushDelta (structInv_writeDirect h t) _ _
  · exact h

/-- The logged rule-routed write preserves `StructInv` (a fold of `writeLoggedOne`). -/
theorem structInv_writeLoggedRules {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (t : Tuple) : StructInv S (σ.writeLoggedRules S t) := by
  unfold GraphState.writeLoggedRules
  have hgen : ∀ (us : List Tuple) {σ : GraphState}, StructInv S σ →
      StructInv S (us.foldl (fun acc u => acc.writeLoggedOne u) σ) := by
    intro us
    induction us with
    | nil => intro σ h; exact h
    | cons u rest ih =>
      intro σ h
      rw [List.foldl_cons]
      exact ih (structInv_writeLoggedOne h u)
  exact hgen (rewriteClosure S t) h

/-- One W3d logged reconcile job (diffing pass then the coalesced processor emission)
    preserves `StructInv`. -/
theorem structInv_applyLogged {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (T : Store) (j : W3cJob) : StructInv S (j.applyLogged S T σ) := by
  unfold W3cJob.applyLogged W3cJob.applyD
  exact structInv_pushDelta
    (structInv_reconcileStarsKeyD h T j.dt j.on j.R j.e (wildcardShapes S)
      j.cands j.negCands j.uposCands) _ _

/-- A batch of logged reconcile jobs preserves `StructInv`. -/
theorem structInv_reconcileJobsL {S : Schema} (T : Store) :
    ∀ (jobs : List W3cJob) {σ : GraphState}, StructInv S σ →
      StructInv S (reconcileJobsL S T σ jobs) := by
  intro jobs
  induction jobs with
  | nil => intro σ h; exact h
  | cons j rest ih =>
    intro σ h
    unfold reconcileJobsL
    rw [List.foldl_cons]
    exact ih (structInv_applyLogged h T j)

/-- **A whole cascade run preserves `StructInv`.** Accept branch = the logged job batch
    with the watermark advanced (both structural no-ops off the edge/node core); reject
    branch = identity. -/
theorem structInv_runCascade {S : Schema} {T : Store} {σ : GraphState}
    (h : StructInv S σ) (jobs : List W3cJob) :
    StructInv S (runCascade S T σ jobs) := by
  unfold runCascade
  split
  · exact structInv_setWatermark (structInv_reconcileJobsL T jobs h) _
  · exact h

/-! ## The structural invariant over the interleaved chain -/

/-- **T2a structural half for W3d (`reachedByW3d_structInv`).** Every state of the
    interleaved scheduler chain satisfies `StructInv` — schema fixity, node encoding,
    edge endpoint-closure, and acyclicity — with NO fragment hypotheses. The write legs
    go through `structInv_writeLoggedRules`, the cascade legs through
    `structInv_runCascade`; the empty seed is `structInv_empty`.

    This is the structural core of the deferred `reachedByW3d_inv`; the four I6
    residue-hygiene clauses (which DO need the `RootBoolean`/terminality fragment) are a
    separate obligation, tracked in the ROADMAP W3d-1c line. -/
theorem reachedByW3d_structInv {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d σ S T) : StructInv S σ := by
  induction h with
  | empty S => exact structInv_empty S
  | write t hadm hprev ih => exact structInv_writeLoggedRules ih t
  | cascade jobs hjv hcover hscope hprev ih => exact structInv_runCascade ih jobs

/-- The coverage chain inherits the structural invariant through the projection. -/
theorem reachedByW3dC_structInv {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3dC σ S T) : StructInv S σ :=
  reachedByW3d_structInv (reachedByW3dC_toW3d h)

/-! ## The edge-free I6 residue-hygiene clauses over the interleaved chain

`negStarCovered` (`neg ⊆ stars-covered`) and `uposNegDisjoint` (`upos ∩ neg = ∅`) are
the two `Inv` clauses that read ONLY the residue row, not the edges — so they hold over
the whole interleaved chain with NO fragment hypotheses, exactly because
`reconcileResidueKey` writes `neg = negCands.filter (stars.contains ∧ ¬checkFn)` and
`upos = uposCands.filter (¬stars.contains ∧ checkFn)` (`processor.py:406-441`): every
`neg` member's shape is star-covered by construction, and no member is in both sets
(one demands coverage, the other its negation). The two EDGE-referencing clauses
(`negEdgeFree`/`uposEdgeFree`) need the R-node terminality fragment and remain open. -/

/-- The two edge-free I6 clauses: `neg` is star-covered and disjoint from `upos`. -/
def ResidueHygienic (σ : GraphState) : Prop :=
  (∀ k r res, σ.residue k r = some res → ∀ n ∈ res.neg, res.stars.contains n.shape = true) ∧
  (∀ k r res, σ.residue k r = some res → ∀ n ∈ res.upos, res.neg.contains n = false)

/-- The empty state has no residue rows, so both clauses are vacuous. -/
theorem residueHygienic_empty (S : Schema) : ResidueHygienic (emptyState S) :=
  ⟨by intro k r res h; simp [emptyState] at h,
   by intro k r res h; simp [emptyState] at h⟩

/-- **The residue recompute writes a hygienic row.** Any state whose residue is a
    hygienic table stays hygienic after `reconcileStarsKeyD`: the self-key row is the
    filtered `⟨stars, neg, upos⟩` (`reconcileResidueKey_residue_self`), whose filters
    give both clauses directly; every other key is untouched (IH). -/
theorem residueHygienic_reconcileStarsKeyD {σ : GraphState} (h : ResidueHygienic σ)
    (T : Store) (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef) :
    ResidueHygienic (σ.reconcileStarsKeyD T dt on R e shapes cands negCands uposCands) := by
  obtain ⟨hns, hun⟩ := h
  constructor
  · intro k r res hrow n hn
    by_cases hkey : k = objNode ⟨dt, on⟩ R ∧ r = R
    · obtain ⟨hk, hr⟩ := hkey
      rw [hk, hr, reconcileStarsKeyD_residue_self, reconcileResidueKey_residue_self] at hrow
      set stars := shapes.filter (fun sh => σ.coveredFn T dt on R e sh) with hstdef
      obtain rfl := Option.some.inj hrow
      -- n ∈ negCands.filter (fun c => stars.contains c.shape && !checkFn)
      have hcond := (List.mem_filter.mp hn).2
      simp only [Bool.and_eq_true] at hcond
      exact hcond.1
    · rw [reconcileStarsKeyD_residue_other hkey] at hrow
      exact hns k r res hrow n hn
  · intro k r res hrow n hn
    by_cases hkey : k = objNode ⟨dt, on⟩ R ∧ r = R
    · obtain ⟨hk, hr⟩ := hkey
      rw [hk, hr, reconcileStarsKeyD_residue_self, reconcileResidueKey_residue_self] at hrow
      set stars := shapes.filter (fun sh => σ.coveredFn T dt on R e sh) with hstdef
      set neg := negCands.filter
        (fun c => stars.contains c.shape && !(σ.checkFn T c dt on R e)) with hnegdef
      obtain rfl := Option.some.inj hrow
      -- n ∈ upos ⇒ ¬covered; a neg member is covered ⇒ n ∉ neg
      have hcond := (List.mem_filter.mp hn).2
      simp only [Bool.and_eq_true] at hcond
      have hstarF : stars.contains n.shape = false := by simpa using hcond.1
      cases hc : neg.contains n with
      | false => rfl
      | true =>
        exfalso
        rw [List.contains_eq_mem] at hc
        have hmem : n ∈ neg := of_decide_eq_true hc
        rw [hnegdef] at hmem
        have hcond2 := (List.mem_filter.mp hmem).2
        simp only [Bool.and_eq_true] at hcond2
        rw [hstarF] at hcond2
        exact absurd hcond2.1 (by decide)
    · rw [reconcileStarsKeyD_residue_other hkey] at hrow
      exact hun k r res hrow n hn

/-- Pushing a delta row is residue-inert. -/
theorem residueHygienic_pushDelta {σ : GraphState} (h : ResidueHygienic σ)
    (k : NodeKey) (r : String) : ResidueHygienic (σ.pushDelta k r) := by
  obtain ⟨hns, hun⟩ := h
  exact ⟨by intro k' r' res hrow; rw [pushDelta_residue] at hrow; exact hns k' r' res hrow,
         by intro k' r' res hrow; rw [pushDelta_residue] at hrow; exact hun k' r' res hrow⟩

/-- Overwriting the watermark is residue-inert. -/
theorem residueHygienic_setWatermark {σ : GraphState} (h : ResidueHygienic σ) (w : Nat) :
    ResidueHygienic { σ with watermark := w } := h

/-- One logged reconcile job preserves residue hygiene. -/
theorem residueHygienic_applyLogged {S : Schema} {σ : GraphState} (h : ResidueHygienic σ)
    (T : Store) (j : W3cJob) : ResidueHygienic (j.applyLogged S T σ) := by
  unfold W3cJob.applyLogged W3cJob.applyD
  exact residueHygienic_pushDelta
    (residueHygienic_reconcileStarsKeyD h T j.dt j.on j.R j.e (wildcardShapes S)
      j.cands j.negCands j.uposCands) _ _

/-- A batch of logged reconcile jobs preserves residue hygiene. -/
theorem residueHygienic_reconcileJobsL {S : Schema} (T : Store) :
    ∀ (jobs : List W3cJob) {σ : GraphState}, ResidueHygienic σ →
      ResidueHygienic (reconcileJobsL S T σ jobs) := by
  intro jobs
  induction jobs with
  | nil => intro σ h; exact h
  | cons j rest ih =>
    intro σ h
    unfold reconcileJobsL
    rw [List.foldl_cons]
    exact ih (residueHygienic_applyLogged h T j)

/-- A whole cascade run preserves residue hygiene. -/
theorem residueHygienic_runCascade {S : Schema} {T : Store} {σ : GraphState}
    (h : ResidueHygienic σ) (jobs : List W3cJob) :
    ResidueHygienic (runCascade S T σ jobs) := by
  unfold runCascade
  split
  · exact residueHygienic_setWatermark (residueHygienic_reconcileJobsL T jobs h) _
  · exact h

/-- A logged rule-routed write is residue-inert, so it preserves residue hygiene. -/
theorem residueHygienic_writeLoggedRules {S : Schema} {σ : GraphState}
    (h : ResidueHygienic σ) (t : Tuple) : ResidueHygienic (σ.writeLoggedRules S t) := by
  obtain ⟨hns, hun⟩ := h
  exact ⟨by intro k r res hrow; rw [writeLoggedRules_residue] at hrow; exact hns k r res hrow,
         by intro k r res hrow; rw [writeLoggedRules_residue] at hrow; exact hun k r res hrow⟩

/-- **The edge-free I6 residue-hygiene clauses hold at every W3d state**
    (`negStarCovered` + `uposNegDisjoint`), with NO fragment hypotheses — the residue
    rows are always the filtered output of `reconcileResidueKey`. This reduces the
    open half of `reachedByW3d_inv` to the two EDGE-referencing clauses
    (`negEdgeFree`/`uposEdgeFree`), which need R-node terminality. -/
theorem reachedByW3d_residueHygienic {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d σ S T) : ResidueHygienic σ := by
  induction h with
  | empty S => exact residueHygienic_empty S
  | write t hadm hprev ih => exact residueHygienic_writeLoggedRules ih t
  | cascade jobs hjv hcover hscope hprev ih => exact residueHygienic_runCascade ih jobs

end Zanzibar
