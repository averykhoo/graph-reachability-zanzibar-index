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

end Zanzibar
