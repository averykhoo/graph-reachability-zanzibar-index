import ZanzibarProofs.GraphIndex.State

/-!
# The concrete write model — untainted direct fragment (Phase 4, T2a)

`SEMANTICS.md` §7.3–7.5. `State.lean` left `WriteStep` an abstract postcondition
spec (schema fixed, nodes monotone, outbox drained) — deliberately thin, because
the full edge/bridge/reconcile realization is the T2a operational content. **This
file begins that realization concretely**, for the *untainted direct fragment*:
schemas whose writes materialize as ordinary closure edges with no residues (no
`but not`/`and`, no derived relations). For that fragment a tuple write is one
guarded edge insertion, and the whole `Inv` is preserved by the `structInv_*`
lemmas (the residue clauses are vacuous — `ResidueEmpty`).

The derived/reconcile half (residue materialization, §7.6/§7.8) and the read
correspondence `check = sem` (§7.5, T2b) build on top of this; they remain the
tracked deferred content. What lands here is genuine, axiom-clean, reusable:

* `writeDirect` — the concrete guarded single-tuple edge write (cycle-rejection
  faithful to §7.3: a self-loop or back-path-forming write is rejected, leaving
  the state unchanged).
* `structInv_writeDirect` / `inv_writeDirect` — the write preserves the structural
  (and, on the residue-free fragment, the whole) invariant.
* `writeDirect_writeStep` — the concrete write realizes the abstract `WriteStep`
  spec, connecting the operational model to the `ReachedBy` closure.
-/

namespace Zanzibar

/-! ## Endpoint nodes are encoding-valid -/

/-- A subject-endpoint node always satisfies the node-encoding clause
    (`name == '*' ⟺ variant ≠ plain`). -/
theorem nodeEnc_subjNode (s : SubjectRef) :
    (subjNode s).name = STAR ↔ (subjNode s).variant ≠ Variant.plain := by
  unfold subjNode
  by_cases h : s.name = STAR
  · simp only [h, if_true]; decide
  · simp [h]

/-- An object-endpoint node always satisfies the node-encoding clause. -/
theorem nodeEnc_objNode (o : ObjectRef) (R : String) :
    (objNode o R).name = STAR ↔ (objNode o R).variant ≠ Variant.plain := by
  unfold objNode
  by_cases h : o.name = STAR
  · simp only [h, if_true]; decide
  · simp [h]

/-! ## The residue-free fragment -/

/-- `ResidueEmpty σ`: the state persists no residue. This holds along any write
    path that only touches untainted (closure-edge) relations — the fragment on
    which a direct edge write preserves the *whole* invariant, because every
    residue clause of `Inv` is then vacuous. -/
def ResidueEmpty (σ : GraphState) : Prop := ∀ k r, σ.residue k r = none

/-- The empty state is residue-free. -/
theorem residueEmpty_empty (S : Schema) : ResidueEmpty (emptyState S) := by
  intro k r; rfl

/-! ## The concrete guarded write -/

/-- Edge-admission (§7.3): the write is accepted unless it is a self-loop
    (`a = b`) or would close a cycle (a back-path `b →* a` already exists, detected
    by the executable reachability probe `p(b,a) > 0`). Fail-closed and exact
    (given endpoint-closure, `σ.reach = NReaches` — `reach_iff_nreaches`). -/
def GraphState.admitEdge (σ : GraphState) (a b : NodeKey) : Bool :=
  (a != b) && !σ.reach b a

/-- **Materialize one untainted direct tuple** `t = (s, R, o)` into the graph
    (§7.4–7.5): add both endpoint nodes and the direct edge `subjNode s → objNode
    o R`, guarded by cycle-rejection. A rejected (self / cycle-forming) write
    leaves the state unchanged (`_add_edge_locked` raises + rolls back, §7.3).
    Residues are untouched — this is the untainted fragment. -/
def GraphState.writeDirect (σ : GraphState) (t : Tuple) : GraphState :=
  let a := subjNode t.subject
  let b := objNode t.object t.relation
  if σ.admitEdge a b then
    (((σ.addNode a).addNode b).addEdge a b)
  else σ

/-- A rejected write is the identity. -/
theorem writeDirect_reject {σ : GraphState} {t : Tuple}
    (h : σ.admitEdge (subjNode t.subject) (objNode t.object t.relation) = false) :
    σ.writeDirect t = σ := by
  unfold GraphState.writeDirect
  simp [h]

/-- The write never drops a residue (untainted fragment: residues are untouched). -/
theorem residueEmpty_writeDirect {σ : GraphState} (t : Tuple) (h : ResidueEmpty σ) :
    ResidueEmpty (σ.writeDirect t) := by
  intro k r
  unfold GraphState.writeDirect
  by_cases hadmit : σ.admitEdge (subjNode t.subject) (objNode t.object t.relation) = true
  · simp only [hadmit, if_true]
    -- addEdge/addNode leave `residue` definitionally equal to `σ.residue`
    show σ.residue k r = none
    exact h k r
  · simp only [Bool.not_eq_true] at hadmit
    simp only [hadmit]
    exact h k r

/-! ## Invariant preservation -/

/-- **Structural preservation.** A `writeDirect` preserves `StructInv`: on the
    reject branch the state is unchanged; on the accept branch the two endpoint
    nodes are encoding-valid (`nodeEnc_subjNode`/`nodeEnc_objNode`) and the edge is
    admitted by cycle-rejection, so `structInv_addNode`/`structInv_addEdge` apply.
    The back-path premise comes from the admission probe via `reach_complete`
    (endpoint-closure supplied by `StructInv.edgesClosed`). -/
theorem structInv_writeDirect {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (t : Tuple) : StructInv S (σ.writeDirect t) := by
  unfold GraphState.writeDirect
  set a := subjNode t.subject with ha_def
  set b := objNode t.object t.relation with hb_def
  by_cases hadmit : σ.admitEdge a b = true
  · simp only [hadmit, if_true]
    -- unpack the admission Bool
    unfold GraphState.admitEdge at hadmit
    simp only [Bool.and_eq_true, bne_iff_ne, ne_eq, Bool.not_eq_true'] at hadmit
    obtain ⟨hne, hreach⟩ := hadmit
    -- add the two endpoint nodes
    have h1 : StructInv S (σ.addNode a) :=
      structInv_addNode h (by rw [ha_def]; exact nodeEnc_subjNode t.subject)
    have h2 : StructInv S ((σ.addNode a).addNode b) :=
      structInv_addNode h1 (by rw [hb_def]; exact nodeEnc_objNode t.object t.relation)
    -- the edge is admitted: no back-path b →* a in σ.edges
    have hback : ¬ NReaches σ.edges b a := by
      intro hr
      have := reach_complete h.edgesClosed hr
      rw [this] at hreach; exact Bool.noConfusion hreach
    -- transport ¬back-path to the extended (same-edge) state
    have hback' : ¬ NReaches ((σ.addNode a).addNode b).edges b a := by
      simpa using hback
    refine structInv_addEdge h2 ?_ ?_ hback' hne
    · exact List.mem_cons_of_mem _ List.mem_cons_self
    · exact List.mem_cons_self
  · simp only [Bool.not_eq_true] at hadmit
    simp only [hadmit]
    exact h

/-- **Full-invariant preservation on the residue-free fragment.** With no persisted
    residues, every residue clause of `Inv` is vacuous, so `writeDirect` preserves
    the *whole* invariant: the structural clauses via `structInv_writeDirect`, the
    residue clauses because `σ'` is again `ResidueEmpty` (`residueEmpty_writeDirect`).
    This is T2a's `Inv` conjunct *for the untainted fragment* — the derived case
    (edge changes reachability-affecting an existing residue) is the deferred half. -/
theorem inv_writeDirect {S : Schema} {σ : GraphState} (h : Inv S σ)
    (hre : ResidueEmpty σ) (t : Tuple) : Inv S (σ.writeDirect t) := by
  have hstruct := structInv_writeDirect h.toStruct t
  have hre' := residueEmpty_writeDirect t hre
  exact
    { schemaEq := hstruct.schemaEq
      nodeEnc := hstruct.nodeEnc
      edgesClosed := hstruct.edgesClosed
      acyclic := hstruct.acyclic
      negStarCovered := by
        intro k r res hr _ _; exact absurd (hr.symm.trans (hre' k r)) (Option.some_ne_none res)
      negEdgeFree := by
        intro k r res hr _ _; exact absurd (hr.symm.trans (hre' k r)) (Option.some_ne_none res)
      uposEdgeFree := by
        intro k r res hr _ _; exact absurd (hr.symm.trans (hre' k r)) (Option.some_ne_none res)
      uposNegDisjoint := by
        intro k r res hr _ _; exact absurd (hr.symm.trans (hre' k r)) (Option.some_ne_none res) }

/-! ## Realizing the abstract `WriteStep` -/

/-- The write leaves the outbox untouched (untainted fragment produces no deltas). -/
theorem writeDirect_outbox (σ : GraphState) (t : Tuple) :
    (σ.writeDirect t).outbox = σ.outbox := by
  unfold GraphState.writeDirect; dsimp only; split <;> rfl

/-- The write leaves the drain watermark untouched. -/
theorem writeDirect_watermark (σ : GraphState) (t : Tuple) :
    (σ.writeDirect t).watermark = σ.watermark := by
  unfold GraphState.writeDirect; dsimp only; split <;> rfl

/-- The schema is fixed by the write. -/
theorem writeDirect_schema (σ : GraphState) (t : Tuple) :
    (σ.writeDirect t).schema = σ.schema := by
  unfold GraphState.writeDirect; dsimp only; split <;> rfl

/-- Existing nodes persist across the write (nodes are only ever added). -/
theorem writeDirect_monoNodes (σ : GraphState) (t : Tuple) :
    ∀ k ∈ σ.nodes, k ∈ (σ.writeDirect t).nodes := by
  intro k hk
  unfold GraphState.writeDirect
  dsimp only
  split
  · exact List.mem_cons_of_mem _ (List.mem_cons_of_mem _ hk)
  · exact hk

/-- **The concrete write realizes the abstract `WriteStep` spec.** Schema fixed,
    nodes monotone, outbox drained (a `Quiescent` state stays quiescent because the
    untainted write touches neither outbox nor watermark). This connects the
    concrete operation to the `ReachedBy` write-closure the T2 theorems quantify
    over. -/
theorem writeDirect_writeStep {S : Schema} {σ : GraphState} (hq : Quiescent σ)
    (t : Tuple) : WriteStep S σ (σ.writeDirect t) t where
  schemaEq := writeDirect_schema σ t
  monoNodes := writeDirect_monoNodes σ t
  drained := by
    intro d hd
    rw [writeDirect_outbox] at hd
    rw [writeDirect_watermark]
    exact hq d hd

/-- Quiescence is preserved by the write (outbox/watermark untouched). -/
theorem quiescent_writeDirect {σ : GraphState} (hq : Quiescent σ) (t : Tuple) :
    Quiescent (σ.writeDirect t) := by
  intro d hd
  rw [writeDirect_outbox] at hd
  rw [writeDirect_watermark]
  exact hq d hd

/-! ## The untainted write-closure and its invariant -/

/-- **`ReachedByDirect σ S T`** — `σ` is reached from the empty state by applying
    `T`'s writes as untainted direct-edge writes (`writeDirect`). The concrete
    counterpart of `ReachedBy` for the residue-free fragment. -/
inductive ReachedByDirect : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByDirect (emptyState S) S []
  | step {σ : GraphState} {S : Schema} {T : Store} (t : Tuple) :
      ReachedByDirect σ S T → ReachedByDirect (σ.writeDirect t) S (t :: T)

/-- **T2a's `Inv` conjunct for the untainted fragment.** Every state reached by
    untainted direct writes satisfies the full I-series invariant, stays
    residue-free, and is cascade-quiescent — proved honestly by induction over the
    concrete write path (`inv_writeDirect`), not postulated as a `WriteStep`
    postcondition. -/
theorem reachedByDirect_inv {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByDirect σ S T) : Inv S σ ∧ ResidueEmpty σ ∧ Quiescent σ := by
  induction h with
  | empty S => exact ⟨inv_empty S, residueEmpty_empty S, quiescent_empty S⟩
  | step t _ ih =>
    obtain ⟨hInv, hRe, hQ⟩ := ih
    exact ⟨inv_writeDirect hInv hRe t, residueEmpty_writeDirect t hRe,
      quiescent_writeDirect hQ t⟩

/-- The untainted write-closure embeds in the abstract `ReachedBy` closure: each
    concrete `writeDirect` realizes a `WriteStep` (quiescence supplied by the
    running invariant). So the concrete fragment is a genuine sub-model of the
    states the T2 theorems quantify over. -/
theorem reachedBy_of_direct {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByDirect σ S T) : ReachedBy σ S T := by
  induction h with
  | empty S => exact ReachedBy.empty S
  | step t hd ih =>
    exact ReachedBy.step t ih (writeDirect_writeStep (reachedByDirect_inv hd).2.2 t)

end Zanzibar
