import ZanzibarProofs.GraphIndex.CascadeSettle

/-!
# The W3d invariant over the interleaved chain (ROADMAP W3d-1c, part 3)

The deferred T2a carry for W3d (`reachedByW3d_inv`, HANDOFF "The next task", point 3)
asks for `Inv S σ` at every state of the interleaved scheduler chain. This file
discharges the **structural half** — `StructInv` (schema fixity, node encoding, edge
endpoint-closure, and ACYCLICITY) — unconditionally, i.e. with none of the fragment
hypotheses (`ComputedOnly`/`hterm`/…) the residue-hygiene (I6) clauses need, then the
two edge-FREE I6 clauses (`ResidueHygienic`), and finally the two EDGE-referencing I6
clauses (`EdgeHygienic`) and the full assembly **`reachedByW3dC_inv`**.

**Attack-first (2026-07-11j, machine-checked `#eval` vs the real `writeLoggedRules`/
`runCascade`; scratch deleted): the full `Inv` is FALSE over the plain `ReachedByW3d`
chain** — the coverage clauses are load-bearing for `negEdgeFree`, not just for
`graph_correct_w3d`. On `viewer := member ∖ banned` (`member` carrying a wildcard
`user:*` restriction): `write member(alice) → cascade (cands = [alice], edge
materialised) → write member(user:*) → write banned(alice) → cascade with cands = []
(W3cJobValid but NOT coverage-valid), negCands = [alice]` reaches a fully-drained
(`cascadeKeys = []`) plain-chain state whose row has `neg = [alice]` while alice's
STALE edge survives the diff audit (a non-candidate is never audited) — `negEdgeFree`
violated. With the edge-holder coverage clause satisfied (`cands = [alice]`,
`W3dJobCoverage` clause 1 = Python's audit re-enumerating persisted incoming R-node
concretes, `processor.py:394-441`) the same chain retracts the edge. Hence the full
invariant is stated over the coverage chain: **`reachedByW3dC_inv`**.

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

/-- **Erase-one preserves the structural invariant** (W3d remove-leg R1). Same
    nodes/schema; endpoint closure via `edgesClosed_removeEdgeOne`; acyclicity because
    the erased edge set is a subset (`removeEdgeOne_edges_subset`) so `NReaches` can only
    shrink (`NReaches.mono_subset`). Identical shape to `structInv_removeEdgePair` — the
    subset-of-edges acyclicity argument does not care whether we drop one copy or all. -/
theorem structInv_removeEdgeOne {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (a b : NodeKey) : StructInv S (σ.removeEdgeOne a b) where
  schemaEq := by rw [removeEdgeOne_schema]; exact h.schemaEq
  nodeEnc := by rw [removeEdgeOne_nodes]; exact h.nodeEnc
  edgesClosed := edgesClosed_removeEdgeOne h.edgesClosed a b
  acyclic := fun v hv =>
    h.acyclic v (NReaches.mono_subset (removeEdgeOne_edges_subset σ a b) hv)

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
    (k : NodeKey) (r : String) (b : Bool := false) : StructInv S (σ.pushDelta k r b) where
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
  · exact structInv_pushDelta (structInv_writeDirect h t) _ _ true
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

/-- A single logged routed-edge retraction preserves `StructInv` (present branch =
    `removeEdgeOne` then `pushDelta`; absent branch = identity). Retract mirror of
    `structInv_writeLoggedOne`; the erase-one leg is `structInv_removeEdgeOne`. -/
theorem structInv_removeLoggedOne {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (t : Tuple) : StructInv S (σ.removeLoggedOne t) := by
  unfold GraphState.removeLoggedOne
  split
  · exact structInv_pushDelta (structInv_removeEdgeOne h _ _) _ _ true
  · exact h

/-- The logged rule-routed retraction preserves `StructInv` (a fold of
    `structInv_removeLoggedOne` — the retract mirror of `structInv_writeLoggedRules`).
    Same nodes/schema throughout; acyclicity is free because every step only ERASES an
    edge (`removeEdgeOne_edges_subset`), so `NReaches` can only shrink. -/
theorem structInv_removeLoggedRules {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (t : Tuple) : StructInv S (σ.removeLoggedRules S t) := by
  unfold GraphState.removeLoggedRules
  have hgen : ∀ (us : List Tuple) {σ : GraphState}, StructInv S σ →
      StructInv S (us.foldl (fun acc u => acc.removeLoggedOne u) σ) := by
    intro us
    induction us with
    | nil => intro σ h; exact h
    | cons u rest ih =>
      intro σ h
      rw [List.foldl_cons]
      exact ih (structInv_removeLoggedOne h u)
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
    residue-hygiene clauses (which DO need the `ComputedOnly`/terminality fragment) are a
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

/-! ## Residue rows live only at declared derived keys

Every residue row is written by some pass's `reconcileResidueKey` at ITS key
`(objNode ⟨dt, on⟩ R, R)`, and the chain only runs `W3cJobValid` jobs — so a persisted
row always names a DECLARED derived key at a concrete object (`processor.py` only
reconciles keys produced by the schema-driven fan-out). This is what lets the edge
clauses fetch the key's `Expr` and `ComputedOnly`ness. -/

/-- Every residue row sits at `(objNode ⟨dt, on⟩ R, R)` for a declared derived
    `(dt, R)` and a concrete object. -/
def ResidueDeclared (S : Schema) (σ : GraphState) : Prop :=
  ∀ k r res, σ.residue k r = some res →
    ∃ dt on R e, k = objNode ⟨dt, on⟩ R ∧ r = R ∧ S.lookup (dt, R) = some e ∧
      isDerived S (dt, R) = true ∧ on ≠ STAR

/-- The diffing batch preserves row-key declaredness: each pass writes only its own
    (valid) key's row. -/
theorem residueDeclared_reconcileJobsD {S : Schema} (T : Store) :
    ∀ (jobs : List W3cJob), (∀ j ∈ jobs, W3cJobValid S j) → ∀ {σ : GraphState},
      ResidueDeclared S σ → ResidueDeclared S (reconcileJobsD S T σ jobs) := by
  intro jobs
  induction jobs with
  | nil => intro _ σ h; exact h
  | cons j rest ih =>
    intro hjv σ h
    have hfold : reconcileJobsD S T σ (j :: rest)
        = reconcileJobsD S T (j.applyD S T σ) rest := by
      unfold reconcileJobsD
      rw [List.foldl_cons]
    rw [hfold]
    refine ih (fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj')) ?_
    intro k r res hrow
    unfold W3cJob.applyD at hrow
    by_cases hkey : k = objNode ⟨j.dt, j.on⟩ j.R ∧ r = j.R
    · obtain ⟨_, _, _, _, _, _, hder, hlk, hon⟩ := hjv j List.mem_cons_self
      exact ⟨j.dt, j.on, j.R, j.e, hkey.1, hkey.2, hlk, hder, hon⟩
    · rw [reconcileStarsKeyD_residue_other hkey] at hrow
      exact h k r res hrow

/-- **Row-key declaredness at every W3d state** — no fragment hypotheses (the chain's
    own `W3cJobValid` is enough). -/
theorem reachedByW3d_residueDeclared {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d σ S T) : ResidueDeclared S σ := by
  induction h with
  | empty S =>
    intro k r res hrow
    simp [emptyState] at hrow
  | write t hadm hprev ih =>
    intro k r res hrow
    rw [writeLoggedRules_residue] at hrow
    exact ih k r res hrow
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    rcases runCascade_cases S T σp jobs with hrc | hrc
    · intro k r res hrow
      rw [hrc] at hrow
      have hupd : ({ reconcileJobsL S T σp jobs with
          watermark := (reconcileJobsL S T σp jobs).maxOutboxId }).residue
            = (reconcileJobsL S T σp jobs).residue := rfl
      rw [hupd, (reconcileJobsL_evalEq (EvalEq.refl σp) S T jobs).residue] at hrow
      exact residueDeclared_reconcileJobsD T jobs hjv ih k r res hrow
    · rw [hrc]
      exact ih

/-! ## The edge-referencing I6 clauses over the COVERAGE chain

`negEdgeFree` / `uposEdgeFree`: a persisted `neg`/`upos` member has no reach into its
key's R-node. Attack-first (header): FALSE over the plain chain — a stale
non-candidate edge survives the diff audit while a later pass writes its holder into
`neg`. Over `ReachedByW3dC` the edge-holder coverage clause forces every pre-leg
holder into `cands`, so the last targeting pass audits it against the fresh
(`checkFn = sem`) guard: targeted keys land `SettledKey` (whose row verdicts and edge
verdicts CONTRADICT — a `neg` member is `sem`-false, an edge holder `sem`-true; a
`upos` member is userset-shaped, an edge source bare); untargeted keys keep row and
in-edges verbatim, and write legs never touch derived in-edges (model-level I5,
`writeLeg_derived_inedges_eq`) — with the W3d reach collapse turning any path into
the R-node into a single edge on both legs. -/

/-- The two edge-referencing I6 clauses: no `neg`/`upos` member reaches its key. -/
def EdgeHygienic (σ : GraphState) : Prop :=
  ∀ k r res, σ.residue k r = some res →
    (∀ n ∈ res.neg, ¬ NReaches σ.edges (subjNode n) k) ∧
    (∀ n ∈ res.upos, ¬ NReaches σ.edges (subjNode n) k)

/-- **The edge-referencing I6 clauses hold at every COVERAGE-chain state** (fragment
    hypotheses as in `reachedByW3dC_settled`; the plain chain refutes this, see the
    file header). -/
theorem reachedByW3dC_edgeHygienic {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3dC σ S T) :
    WF S → TtuTuplesetsDirect S → NodupKeys S → RewriteRanked S →
    RewriteMatchDeclared S → Stratifiable S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false) →
    (∀ sh ∈ wildcardShapes S, sh.2 = BARE) →
    StoreValidRules S T → BareStarStore T → TtuStarFree S T →
    (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) →
    EdgeHygienic σ := by
  induction h with
  | empty S =>
    intro _ _ _ _ _ _ _ _ _ _ _ _ _ k r res hrow
    simp [emptyState] at hrow
  | @write σp S T t hadm hprev ih =>
    intro hWF hTT hNK hR hMatch hStrat hCO hLU hWSbare hSV hBS hTS hterm
      k r res hrow
    -- weaken the store-indexed hypotheses back to `T` for the IH
    have hSVw : StoreValidRules S T := fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')
    have hBSw : BareStarStore T := fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')
    have hTSw : TtuStarFree S T := fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht')
    have htermw : ∀ dt R, isDerived S (dt, R) = true →
        NoTtuTarget S R ∧ NoStoreSubjectR T R :=
      fun dt R hd => ⟨(hterm dt R hd).1,
        fun t' ht' => (hterm dt R hd).2 t' (List.mem_cons_of_mem _ ht')⟩
    have hW3dpost : ReachedByW3d (σp.writeLoggedRules S t) S (t :: T) :=
      ReachedByW3d.write t hadm (reachedByW3dC_toW3d hprev)
    have hEHp : EdgeHygienic σp :=
      ih hWF hTT hNK hR hMatch hStrat hCO hLU hWSbare hSVw hBSw hTSw htermw
    -- the row is the pre-write row, at a declared derived key
    rw [writeLoggedRules_residue] at hrow
    obtain ⟨dt, on, R, e, hk, hr, hlk, hder, hon⟩ :=
      reachedByW3d_residueDeclared (reachedByW3dC_toW3d hprev) k r res hrow
    subst hk
    have hco : ComputedOnly e := hCO dt R e hlk hder
    constructor
    · intro n hn hre
      have hedge := reachedByW3d_reach_collapse_root hWF hSV hlk hder hco hW3dpost hre
      rw [writeLeg_derived_inedges_eq hSV hlk hder hco (subjNode n)] at hedge
      exact (hEHp _ _ _ hrow).1 n hn (NReaches.edge hedge)
    · intro n hn hre
      have hedge := reachedByW3d_reach_collapse_root hWF hSV hlk hder hco hW3dpost hre
      rw [writeLeg_derived_inedges_eq hSV hlk hder hco (subjNode n)] at hedge
      exact (hEHp _ _ _ hrow).2 n hn (NReaches.edge hedge)
  | @cascade σp S T jobs hjv hcover hscope hcovg hprev ih =>
    intro hWF hTT hNK hR hMatch hStrat hCO hLU hWSbare hSV hBS hTS hterm
      k r res hrow
    have hW3dpost : ReachedByW3d (runCascade S T σp jobs) S T :=
      ReachedByW3d.cascade jobs hjv hcover hscope (reachedByW3dC_toW3d hprev)
    obtain ⟨dt, on, R, e, hk, hr, hlk, hder, hon⟩ :=
      reachedByW3d_residueDeclared hW3dpost k r res hrow
    subst hk
    rw [hr] at hrow
    have hco : ComputedOnly e := hCO dt R e hlk hder
    by_cases htgt : ∃ j ∈ jobs, j.keyMatch dt on R
    · -- targeted key: SettledKey verdicts vs the bare-sourced single edge
      obtain ⟨⟨hrowS, hedgeS⟩, _⟩ :=
        settledComplete_cascade_targeted hWF hTT hNK hR hSV hBS hTS hMatch
          hStrat hterm hCO hLU hWSbare (reachedByW3dC_toW3d hprev) hjv hcovg hlk hder
          hon htgt
      obtain ⟨_, h2, h3⟩ := hrowS res hrow
      constructor
      · intro n hn hre
        have hedge :=
          reachedByW3d_reach_collapse_root hWF hSV hlk hder hco hW3dpost hre
        have hpred : n.predicate = BARE := by
          have := reachedByW3d_Rnode_source_bare hW3dpost hlk hder hco hSV
            (subjNode n) hedge
          rwa [subjNode_pred] at this
        have hsemT := hedgeS n hpred (h2 n hn).1 hedge
        rw [(h2 n hn).2] at hsemT
        exact absurd hsemT (by decide)
      · intro n hn hre
        have hedge :=
          reachedByW3d_reach_collapse_root hWF hSV hlk hder hco hW3dpost hre
        have hpred : n.predicate = BARE := by
          have := reachedByW3d_Rnode_source_bare hW3dpost hlk hder hco hSV
            (subjNode n) hedge
          rwa [subjNode_pred] at this
        exact absurd hpred (h3 n hn).1
    · -- untargeted key: row and in-edges verbatim from the pre-leg state
      have hnot : ∀ j ∈ jobs, ¬ j.keyMatch dt on R := fun j hj hkm => htgt ⟨j, hj, hkm⟩
      have hEHp : EdgeHygienic σp :=
        ih hWF hTT hNK hR hMatch hStrat hCO hLU hWSbare hSV hBS hTS hterm
      rcases runCascade_cases S T σp jobs with hrc | hrc
      · have hev := reconcileJobsL_evalEq (EvalEq.refl σp) S T jobs
        have hupd_res : ({ reconcileJobsL S T σp jobs with
            watermark := (reconcileJobsL S T σp jobs).maxOutboxId }).residue
              = (reconcileJobsL S T σp jobs).residue := rfl
        have hupd_edge : ({ reconcileJobsL S T σp jobs with
            watermark := (reconcileJobsL S T σp jobs).maxOutboxId }).edges
              = (reconcileJobsL S T σp jobs).edges := rfl
        have hres_post : (runCascade S T σp jobs).residue
            = (reconcileJobsD S T σp jobs).residue := by
          rw [hrc, hupd_res, hev.residue]
        have hedges_post : (runCascade S T σp jobs).edges
            = (reconcileJobsD S T σp jobs).edges := by
          rw [hrc, hupd_edge, hev.edges]
        obtain ⟨hresD, hedgesD⟩ := reconcileJobsD_other_key_fixed jobs σp hon hjv hnot
        have hrowp : σp.residue (objNode ⟨dt, on⟩ R) R = some res := by
          rw [← hresD, ← hres_post]
          exact hrow
        constructor
        · intro n hn hre
          have hedge :=
            reachedByW3d_reach_collapse_root hWF hSV hlk hder hco hW3dpost hre
          rw [hedges_post] at hedge
          exact (hEHp _ _ _ hrowp).1 n hn
            (NReaches.edge ((hedgesD (subjNode n)).mp hedge))
        · intro n hn hre
          have hedge :=
            reachedByW3d_reach_collapse_root hWF hSV hlk hder hco hW3dpost hre
          rw [hedges_post] at hedge
          exact (hEHp _ _ _ hrowp).2 n hn
            (NReaches.edge ((hedgesD (subjNode n)).mp hedge))
      · rw [hrc] at hrow ⊢
        exact hEHp _ _ _ hrow

/-! ## The full W3d T2a -/

/-- **T2a, W3d fragment (`reachedByW3dC_inv`) — the full 8-clause `Inv` at every state
    of the coverage chain**, dirty keys and mid-drain states included. Structural half
    and the edge-free I6 clauses need no fragment hypotheses
    (`reachedByW3d_structInv` / `reachedByW3d_residueHygienic`); the edge-referencing
    I6 clauses (`reachedByW3dC_edgeHygienic`) carry the W3d fragment and genuinely
    need the coverage clauses (the plain chain refutes them — file header). -/
theorem reachedByW3dC_inv {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3dC σ S T)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR T R) :
    Inv S σ := by
  have hst := reachedByW3dC_structInv h
  have hhy := reachedByW3d_residueHygienic (reachedByW3dC_toW3d h)
  have heh := reachedByW3dC_edgeHygienic h hWF hTT hNK hR hMatch hStrat hCO hLU
    hWSbare hSV hBS hTS hterm
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
