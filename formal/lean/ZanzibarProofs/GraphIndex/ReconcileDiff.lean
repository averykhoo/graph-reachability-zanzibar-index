import ZanzibarProofs.GraphIndex.ReconcileStarsComplete

/-!
# The diffing edge audit — stale-edge REMOVAL (ROADMAP W3d, decision 7)

**Attack-first finding (2026-07-11f, machine-checked `#eval` vs the real `check`/`sem`,
scratch deleted).** The naive W3d-1b read-correctness statement — `check = sem` at every
cascaded `ReachedByW3d` state — is **FALSE over the add-only pass model** (`reconcileKeyC`):
on `viewer := member ∖ banned` (bare `user` restrictions, NO star grants), the chain
`write member(alice) → cascade → write banned(alice) → cascade` reaches a fully-drained
state where the first cascade's derived edge `alice → (doc,1,viewer)` is STALE —
`check = true ≠ sem = false`. The second cascade DID re-reconcile the key (the cross-key
fan-out worked), but an add-only fold cannot retract an edge whose guard has flipped down.

**Python retracts it.** `reconcile_subject` (`processor.py:321-380`) diffs the desired
representation against the materialized one: `want_edge = should ∧ ¬covered` (`:359`), and
`elif not want_edge and has_edge: self._write_derived(s, ..., add=False)` (`:365-367`) —
`remove_tuple` on the derived pair, driven through the ref-counted closure. W3a–W3c never
saw this branch fire because their chains hold the store FIXED: `checkFn = sem` at every
pass start (the bridge), so a guard true at edge-write time stays true at every later pass
— the removal branch is provably dead there. W3d's store GROWS between cascades, and an
`excl` operand ADD flips a derived guard down: the removal branch is now load-bearing.

**The model** (`reconcileKeyD` — D for diff): per candidate, materialize the derived edge
when `want` holds, else remove every copy of the pair. Faithfulness notes:
* Python removes only when `has_edge`; removal of an absent edge is a filter no-op —
  same state, no case split needed.
* Python adds only when `¬has_edge` (the pair is ref-counted at 1 on derived families —
  the processor is the only writer, I5); the model's `writeDirect` may stack duplicate
  copies across passes, so removal filters ALL copies — "the ref-count reaches zero".
* Python's `_gc_public_node` may garbage-collect an implicit node after its last edge is
  removed; the model keeps nodes (monotone). Extra nodes are read-inert: reads probe
  reachability over EDGES; `affectedObjects` at worst maps extra keys to idempotent
  reconciles; `reach` fuel only grows. Recorded as a model/Python divergence, read-safe.
* The removal, like the additions, touches only edges INTO the pass's own terminal
  R-node — the pass stays operand-read-inert (both directions now: additions are
  trailing hops, removals are trailing hops).

`reconcileStarsKeyD` is the faithful atomic unit for W3d: residue recompute (steps 1–3)
then the DIFFING edge audit (step 4). The W3c layer (`reconcileKeyC`, add-only) remains
valid as the fixed-store batch model — on a fixed store the removal branch never fires.
-/

namespace Zanzibar

/-! ## Edge removal -/

/-- Remove every copy of the direct edge `(a, b)` — `remove_tuple` on the derived pair
    (`_write_derived(..., add=False)`, `processor.py:290-314`): the processor's diff
    drives the ref-count to zero and the closure pair disappears. Nodes/residue/outbox
    are untouched (node GC is a modeled-away optimization, see header). -/
def GraphState.removeEdgePair (σ : GraphState) (a b : NodeKey) : GraphState :=
  { σ with edges := σ.edges.filter (fun ed => !(ed.1 == a && ed.2 == b)) }

@[simp] theorem removeEdgePair_schema (σ : GraphState) (a b : NodeKey) :
    (σ.removeEdgePair a b).schema = σ.schema := rfl
@[simp] theorem removeEdgePair_nodes (σ : GraphState) (a b : NodeKey) :
    (σ.removeEdgePair a b).nodes = σ.nodes := rfl
@[simp] theorem removeEdgePair_residue (σ : GraphState) (a b : NodeKey) :
    (σ.removeEdgePair a b).residue = σ.residue := rfl
@[simp] theorem removeEdgePair_outbox (σ : GraphState) (a b : NodeKey) :
    (σ.removeEdgePair a b).outbox = σ.outbox := rfl
@[simp] theorem removeEdgePair_watermark (σ : GraphState) (a b : NodeKey) :
    (σ.removeEdgePair a b).watermark = σ.watermark := rfl
@[simp] theorem removeEdgePair_edges (σ : GraphState) (a b : NodeKey) :
    (σ.removeEdgePair a b).edges
      = σ.edges.filter (fun ed => !(ed.1 == a && ed.2 == b)) := rfl

/-- Removal only shrinks the edge set. -/
theorem removeEdgePair_edges_subset (σ : GraphState) (a b : NodeKey) :
    ∀ ed ∈ (σ.removeEdgePair a b).edges, ed ∈ σ.edges := by
  intro ed hed
  exact List.mem_of_mem_filter hed

/-- Membership after removal, characterized. -/
theorem mem_removeEdgePair_edges {σ : GraphState} {a b : NodeKey}
    {ed : NodeKey × NodeKey} :
    ed ∈ (σ.removeEdgePair a b).edges ↔ ed ∈ σ.edges ∧ ¬(ed.1 = a ∧ ed.2 = b) := by
  rw [removeEdgePair_edges, List.mem_filter]
  constructor
  · rintro ⟨hmem, hne⟩
    refine ⟨hmem, ?_⟩
    rintro ⟨h1, h2⟩
    rw [h1, h2] at hne
    simp at hne
  · rintro ⟨hmem, hne⟩
    refine ⟨hmem, ?_⟩
    simp only [Bool.not_eq_eq_eq_not, Bool.not_true, Bool.and_eq_false_iff, beq_eq_false_iff_ne]
    by_cases h1 : ed.1 = a
    · exact Or.inr (fun h2 => hne ⟨h1, h2⟩)
    · exact Or.inl h1

/-- **Removal of an in-edge of a non-source node is path-inert for other targets.**
    If `r` is never an edge *source*, an edge into `r` can only be a path's LAST hop —
    so removing `(a, r)` breaks no path to any `v ≠ r`. The removal-side counterpart of
    `nreaches_cons_inert`. -/
theorem nreaches_remove_terminal {edges : List (NodeKey × NodeKey)} {a r u v : NodeKey}
    (hterm : ∀ y, (r, y) ∉ edges) (hv : v ≠ r) (h : NReaches edges u v) :
    NReaches (edges.filter (fun ed => !(ed.1 == a && ed.2 == r))) u v := by
  induction h with
  | @edge u v huv =>
    refine NReaches.edge (List.mem_filter.mpr ⟨huv, ?_⟩)
    simp only [Bool.not_eq_eq_eq_not, Bool.not_true, Bool.and_eq_false_iff,
      beq_eq_false_iff_ne]
    by_cases h1 : u = a
    · exact Or.inr hv
    · exact Or.inl h1
  | @head u w v huw hrest ih =>
    by_cases hw : w = r
    · -- the path continues out of `r` — impossible, `r` is not a source
      exfalso
      subst hw
      cases hrest with
      | edge hrv => exact hterm _ hrv
      | head hry _ => exact hterm _ hry
    · refine NReaches.head (List.mem_filter.mpr ⟨huw, ?_⟩) (ih hv)
      simp only [Bool.not_eq_eq_eq_not, Bool.not_true, Bool.and_eq_false_iff,
        beq_eq_false_iff_ne]
      by_cases h1 : u = a
      · exact Or.inr hw
      · exact Or.inl h1

/-! ## The diffing edge audit -/

/-- **The diffing edge audit** (`reconcile` step 4 → `reconcile_subject`,
    `processor.py:359-367`): per candidate, `want = should ∧ ¬covered`; materialize the
    derived edge when `want`, REMOVE the pair when `¬want` (the stale-edge retraction —
    see header). `covered` reads the persisted row, which the fold never writes. -/
def GraphState.reconcileKeyD (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (cands : List SubjectRef) : GraphState :=
  cands.foldl (fun acc c =>
    if acc.checkFn T c dt on R e && !(acc.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)
    then acc.writeDirect ⟨c, R, ⟨dt, on⟩⟩
    else acc.removeEdgePair (subjNode c) (objNode ⟨dt, on⟩ R)) σ

/-- **One full-object W3d reconcile**: the wholesale residue recompute (steps 1–3),
    then the DIFFING edge audit (step 4). Python stores the residue at `:446` before
    auditing edges at `:450-455`. -/
def GraphState.reconcileStarsKeyD (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (cands negCands uposCands : List SubjectRef) :
    GraphState :=
  (σ.reconcileResidueKey T dt on R e shapes negCands uposCands).reconcileKeyD
    T dt on R e cands

/-- One-step unfolding of the diffing fold. -/
theorem reconcileKeyD_cons (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (c : SubjectRef) (rest : List SubjectRef) :
    σ.reconcileKeyD T dt on R e (c :: rest)
      = (if σ.checkFn T c dt on R e && !(σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)
         then σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩
         else σ.removeEdgePair (subjNode c) (objNode ⟨dt, on⟩ R)).reconcileKeyD
          T dt on R e rest := by
  unfold GraphState.reconcileKeyD
  rw [List.foldl_cons]

/-! ## Structural facts — the diffing fold touches only edges/nodes -/

theorem reconcileKeyD_residue (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKeyD T dt on R e cands).residue = σ.residue := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    rw [reconcileKeyD_cons, ih]
    split
    · exact writeDirect_residue σ _
    · rfl

theorem reconcileKeyD_schema (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKeyD T dt on R e cands).schema = σ.schema := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    rw [reconcileKeyD_cons, ih]
    split
    · exact writeDirect_schema σ _
    · rfl

theorem reconcileKeyD_outbox (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKeyD T dt on R e cands).outbox = σ.outbox := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    rw [reconcileKeyD_cons, ih]
    split
    · exact writeDirect_outbox σ _
    · rfl

theorem reconcileKeyD_watermark (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKeyD T dt on R e cands).watermark = σ.watermark := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    rw [reconcileKeyD_cons, ih]
    split
    · exact writeDirect_watermark σ _
    · rfl

/-- Existing nodes persist (additions add nodes, removal keeps them). -/
theorem reconcileKeyD_nodes_mono (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      ∀ k ∈ σ.nodes, k ∈ (σ.reconcileKeyD T dt on R e cands).nodes := by
  intro cands
  induction cands with
  | nil => intro σ k hk; exact hk
  | cons c rest ih =>
    intro σ k hk
    rw [reconcileKeyD_cons]
    split
    · exact ih _ k (writeDirect_monoNodes σ _ k hk)
    · exact ih _ k hk

/-! ## Edge soundness — every surviving edge is old or a candidate's derived edge -/

/-- **Diff-fold edge soundness.** Removal only shrinks, addition only adds candidate
    edges onto the pass's own R-node — so every edge of the result is an old edge or
    `subjNode c → objNode ⟨dt,on⟩ R` for some `c ∈ cands`. (The converse — old edges
    SURVIVING — is deliberately false now: that is the stale-edge retraction.) -/
theorem reconcileKeyD_edge_sound (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState) (a b : NodeKey),
      (a, b) ∈ (σ.reconcileKeyD T dt on R e cands).edges →
      (a, b) ∈ σ.edges ∨ ∃ c ∈ cands, a = subjNode c ∧ b = objNode ⟨dt, on⟩ R := by
  intro cands
  induction cands with
  | nil => intro σ a b h; exact Or.inl h
  | cons c rest ih =>
    intro σ a b h
    rw [reconcileKeyD_cons] at h
    split at h
    · rcases ih _ a b h with hprev | ⟨c', hc', hac, hbc⟩
      · rw [writeDirect_edges] at hprev
        split at hprev
        · rcases List.mem_cons.mp hprev with heq | hmem
          · obtain ⟨h1, h2⟩ := Prod.ext_iff.mp heq
            exact Or.inr ⟨c, List.mem_cons_self, h1, h2⟩
          · exact Or.inl hmem
        · exact Or.inl hprev
      · exact Or.inr ⟨c', List.mem_cons_of_mem _ hc', hac, hbc⟩
    · rcases ih _ a b h with hprev | ⟨c', hc', hac, hbc⟩
      · exact Or.inl (removeEdgePair_edges_subset σ _ _ _ hprev)
      · exact Or.inr ⟨c', List.mem_cons_of_mem _ hc', hac, hbc⟩

/-- Whole-pass edge soundness (residue half is edge-inert). -/
theorem reconcileStarsKeyD_edge_sound (T : Store) (dt on R : String) (e : Expr)
    (shapes : List Shape) (cands negCands uposCands : List SubjectRef)
    (σ : GraphState) (a b : NodeKey)
    (h : (a, b) ∈ (σ.reconcileStarsKeyD T dt on R e shapes cands negCands
      uposCands).edges) :
    (a, b) ∈ σ.edges ∨ ∃ c ∈ cands, a = subjNode c ∧ b = objNode ⟨dt, on⟩ R := by
  unfold GraphState.reconcileStarsKeyD at h
  rcases reconcileKeyD_edge_sound T dt on R e cands _ a b h with hold | hc
  · rw [reconcileResidueKey_edges] at hold
    exact Or.inl hold
  · exact Or.inr hc

/-! ## Residue effect of the combined pass -/

theorem reconcileStarsKeyD_residue_other {σ : GraphState} {T : Store} {dt on R : String}
    {e : Expr} {shapes : List Shape} {cands negCands uposCands : List SubjectRef}
    {k' : NodeKey} {r' : String} (h : ¬(k' = objNode ⟨dt, on⟩ R ∧ r' = R)) :
    (σ.reconcileStarsKeyD T dt on R e shapes cands negCands uposCands).residue k' r'
      = σ.residue k' r' := by
  unfold GraphState.reconcileStarsKeyD
  rw [reconcileKeyD_residue, reconcileResidueKey_residue_other h]

theorem reconcileStarsKeyD_residue_self (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (cands negCands uposCands : List SubjectRef) :
    (σ.reconcileStarsKeyD T dt on R e shapes cands negCands uposCands).residue
        (objNode ⟨dt, on⟩ R) R =
      (σ.reconcileResidueKey T dt on R e shapes negCands uposCands).residue
        (objNode ⟨dt, on⟩ R) R := by
  unfold GraphState.reconcileStarsKeyD
  rw [reconcileKeyD_residue]

/-! ## Reach inertness — both directions, for targets other than the pass's R-node

The add-only fold was reach-MONOTONE everywhere and inert (post ⇒ pre) off the R-node.
The diffing fold is inert in BOTH directions off the R-node: additions are trailing
hops onto it (`nreaches_cons_inert`), removals are in-edges of it
(`nreaches_remove_terminal`) — provided the R-node is terminal at the pass start,
which the fold maintains (added sources are BARE candidates, `R ≠ BARE`). -/

/-- The fold maintains "the pass's R-node is never a source" step by step. -/
theorem reconcileKeyD_Rnode_terminal (T : Store) (dt on R : String) (e : Expr)
    (hRne : R ≠ BARE) :
    ∀ (cands : List SubjectRef), (∀ c ∈ cands, c.predicate = BARE) →
      ∀ (σ : GraphState), (∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) →
      ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ (σ.reconcileKeyD T dt on R e cands).edges := by
  intro cands hcb σ hRns y hy
  rcases reconcileKeyD_edge_sound T dt on R e cands σ _ y hy with hold | ⟨c, hc, hac, _⟩
  · exact hRns y hold
  · have : (objNode ⟨dt, on⟩ R).pred = c.predicate := by rw [hac, subjNode_pred]
    rw [objNode_pred, hcb c hc] at this
    exact hRne this

/-- **Diff-pass reach inertness (post ⇒ pre)** for `v ≠` the pass's R-node: a
    post-pass path came from a pre-pass path (additions are trailing hops onto the
    terminal R-node; removals only shrink). -/
theorem reconcileKeyD_reach_inert {σ0 : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands0 : List SubjectRef) (hRne : R ≠ BARE)
    {u v : NodeKey} (hv : v ≠ objNode ⟨dt, on⟩ R)
    (hcb0 : ∀ c ∈ cands0, c.predicate = BARE)
    (hRns0 : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ0.edges)
    (h0 : NReaches (σ0.reconcileKeyD T dt on R e cands0).edges u v) :
    NReaches σ0.edges u v := by
  suffices H : ∀ (cs : List SubjectRef) (σ : GraphState),
      (∀ c ∈ cs, c.predicate = BARE) →
      (∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) →
      NReaches (σ.reconcileKeyD T dt on R e cs).edges u v →
      NReaches σ.edges u v from H cands0 σ0 hcb0 hRns0 h0
  intro cs
  induction cs with
  | nil =>
    intro σ _ _ h
    exact h
  | cons c rest ih =>
    intro σ hcb hRns h
    rw [reconcileKeyD_cons] at h
    split at h
    · -- addition: peel with `nreaches_cons_inert`
      have hRns' : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ (σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩).edges := by
        intro y hy
        rw [writeDirect_edges] at hy
        split at hy
        · rcases List.mem_cons.mp hy with heq | hmem
          · have h1 := (Prod.ext_iff.mp heq).1
            have h2 : R = c.predicate := by
              have hp := congrArg NodeKey.pred h1
              simpa [objNode_pred, subjNode_pred] using hp
            rw [hcb c List.mem_cons_self] at h2
            exact hRne h2
          · exact hRns y hmem
        · exact hRns y hy
      have hstep := ih (σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩)
        (fun x hx => hcb x (List.mem_cons_of_mem _ hx)) hRns' h
      rw [writeDirect_edges] at hstep
      split at hstep
      · exact nreaches_cons_inert hRns hv hstep
      · exact hstep
    · -- removal: shrinking is trivially inert (subset)
      have hRns' : ∀ y, (objNode ⟨dt, on⟩ R, y)
          ∉ (σ.removeEdgePair (subjNode c) (objNode ⟨dt, on⟩ R)).edges := by
        intro y hy
        exact hRns y (removeEdgePair_edges_subset σ _ _ _ hy)
      have hstep := ih (σ.removeEdgePair (subjNode c) (objNode ⟨dt, on⟩ R))
        (fun x hx => hcb x (List.mem_cons_of_mem _ hx)) hRns' h
      exact NReaches.mono_subset (removeEdgePair_edges_subset σ _ _) hstep

/-- **Diff-pass reach preservation (pre ⇒ post)** for `v ≠` the pass's R-node: a
    pre-pass path survives the pass (additions never break paths; removals are
    in-edges of the terminal R-node, path-inert off it). NB unlike the add-only
    fold this genuinely NEEDS `v ≠ R-node` — retracting a stale edge is the point. -/
theorem reconcileKeyD_reach_pres {σ0 : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands0 : List SubjectRef) (hRne : R ≠ BARE)
    {u v : NodeKey} (hv : v ≠ objNode ⟨dt, on⟩ R)
    (hcb0 : ∀ c ∈ cands0, c.predicate = BARE)
    (hRns0 : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ0.edges)
    (h0 : NReaches σ0.edges u v) :
    NReaches (σ0.reconcileKeyD T dt on R e cands0).edges u v := by
  suffices H : ∀ (cs : List SubjectRef) (σ : GraphState),
      (∀ c ∈ cs, c.predicate = BARE) →
      (∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) →
      NReaches σ.edges u v →
      NReaches (σ.reconcileKeyD T dt on R e cs).edges u v from H cands0 σ0 hcb0 hRns0 h0
  intro cs
  induction cs with
  | nil =>
    intro σ _ _ h
    exact h
  | cons c rest ih =>
    intro σ hcb hRns h
    rw [reconcileKeyD_cons]
    split
    · -- addition: the path persists by monotonicity
      have hRns' : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ (σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩).edges := by
        intro y hy
        rw [writeDirect_edges] at hy
        split at hy
        · rcases List.mem_cons.mp hy with heq | hmem
          · have h1 := (Prod.ext_iff.mp heq).1
            have h2 : R = c.predicate := by
              have hp := congrArg NodeKey.pred h1
              simpa [objNode_pred, subjNode_pred] using hp
            rw [hcb c List.mem_cons_self] at h2
            exact hRne h2
          · exact hRns y hmem
        · exact hRns y hy
      refine ih (σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩)
        (fun x hx => hcb x (List.mem_cons_of_mem _ hx)) hRns' ?_
      exact NReaches.mono_subset (fun ed hed => writeDirect_edges_mono σ _ ed hed) h
    · -- removal: path-inert off the terminal R-node
      have hRns' : ∀ y, (objNode ⟨dt, on⟩ R, y)
          ∉ (σ.removeEdgePair (subjNode c) (objNode ⟨dt, on⟩ R)).edges := by
        intro y hy
        exact hRns y (removeEdgePair_edges_subset σ _ _ _ hy)
      refine ih (σ.removeEdgePair (subjNode c) (objNode ⟨dt, on⟩ R))
        (fun x hx => hcb x (List.mem_cons_of_mem _ hx)) hRns' ?_
      exact nreaches_remove_terminal hRns hv h

/-! ## Endpoint closure survives the diffing fold -/

/-- `writeDirect` preserves edge endpoint-closure (accepted endpoints become nodes). -/
theorem edgesClosed_writeDirect {σ : GraphState}
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) (t : Tuple) :
    ∀ ab ∈ (σ.writeDirect t).edges,
      ab.1 ∈ (σ.writeDirect t).nodes ∧ ab.2 ∈ (σ.writeDirect t).nodes := by
  intro ab hab
  rw [writeDirect_edges] at hab
  rw [writeDirect_nodes]
  by_cases hadm : σ.admitEdge (subjNode t.subject) (objNode t.object t.relation) = true
  · rw [if_pos hadm] at hab ⊢
    rcases List.mem_cons.mp hab with heq | hmem
    · obtain ⟨h1, h2⟩ := Prod.ext_iff.mp heq
      rw [h1, h2]
      exact ⟨List.mem_cons_of_mem _ List.mem_cons_self, List.mem_cons_self⟩
    · obtain ⟨ha, hb⟩ := hcl ab hmem
      exact ⟨List.mem_cons_of_mem _ (List.mem_cons_of_mem _ ha),
        List.mem_cons_of_mem _ (List.mem_cons_of_mem _ hb)⟩
  · rw [if_neg hadm] at hab ⊢
    exact hcl ab hab

/-- Removal preserves endpoint-closure (fewer edges, same nodes). -/
theorem edgesClosed_removeEdgePair {σ : GraphState}
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) (a b : NodeKey) :
    ∀ ab ∈ (σ.removeEdgePair a b).edges,
      ab.1 ∈ (σ.removeEdgePair a b).nodes ∧ ab.2 ∈ (σ.removeEdgePair a b).nodes := by
  intro ab hab
  rw [removeEdgePair_nodes]
  exact hcl ab (removeEdgePair_edges_subset σ a b ab hab)

/-- The diffing fold preserves endpoint-closure. -/
theorem edgesClosed_reconcileKeyD (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) →
      ∀ ab ∈ (σ.reconcileKeyD T dt on R e cands).edges,
        ab.1 ∈ (σ.reconcileKeyD T dt on R e cands).nodes
          ∧ ab.2 ∈ (σ.reconcileKeyD T dt on R e cands).nodes := by
  intro cands
  induction cands with
  | nil => intro σ hcl; exact hcl
  | cons c rest ih =>
    intro σ hcl
    rw [reconcileKeyD_cons]
    split
    · exact ih _ (edgesClosed_writeDirect hcl _)
    · exact ih _ (edgesClosed_removeEdgePair hcl _ _)

/-! ## Guard fold-invariance — the diffing pass is operand-read-inert

Both halves of a diffing step touch only edges at the pass's own terminal R-node, so
every untainted operand read — hence the compiled guard `checkFn` itself — is constant
along the fold. This is what makes the per-key edge characterisation below well-posed:
each candidate's `want` is decided once, at pass start. -/

/-- The diffing fold leaves the operand read of every untainted key unchanged, for
    EVERY subject (the D analog of `graphRec_reconcileKey_inert`; endpoint closure at
    the fold result is derived, not hypothesised). -/
theorem graphRec_reconcileKeyD_inert {σ : GraphState} {S : Schema} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) (hRne : R ≠ BARE)
    (hcands : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (s : SubjectRef) (dt' on' r' : String) (hunt : isDerived S (dt', r') = false) :
    GraphModel.graphRec (σ.reconcileKeyD T dt on R e cands) s dt' on' r'
      = GraphModel.graphRec σ s dt' on' r' := by
  -- probe targets of the untainted read differ from the reconciled R-node
  have hvne1 : objNode ⟨dt', on'⟩ r' ≠ objNode ⟨dt, on⟩ R := by
    intro heq
    have htype : dt' = dt := by
      have := congrArg NodeKey.type heq
      simpa [objNode_type] using this
    have hpred : r' = R := by
      have := congrArg NodeKey.pred heq
      simpa [objNode_pred] using this
    rw [htype, hpred, hder] at hunt
    cases hunt
  have hvne3 : wAllNode dt' r' ≠ objNode ⟨dt, on⟩ R := by
    unfold wAllNode objNode
    rw [if_neg honStar]
    intro heq
    have := congrArg NodeKey.variant heq
    simp at this
  have hcl2 := edgesClosed_reconcileKeyD T dt on R e cands σ hcl
  have hiff2 := GraphModel.probeNonDerived_iff hcl2 (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  have hiff1 := GraphModel.probeNonDerived_iff hcl (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  have hpres1 : ∀ {u : NodeKey},
      NReaches σ.edges u (objNode ⟨dt', on'⟩ r') →
      NReaches (σ.reconcileKeyD T dt on R e cands).edges u (objNode ⟨dt', on'⟩ r') :=
    fun hn => reconcileKeyD_reach_pres T dt on R e cands hRne hvne1 hcands hRns hn
  have hpres3 : ∀ {u : NodeKey},
      NReaches σ.edges u (wAllNode dt' r') →
      NReaches (σ.reconcileKeyD T dt on R e cands).edges u (wAllNode dt' r') :=
    fun hn => reconcileKeyD_reach_pres T dt on R e cands hRne hvne3 hcands hRns hn
  have hinert1 : ∀ {u : NodeKey},
      NReaches (σ.reconcileKeyD T dt on R e cands).edges u (objNode ⟨dt', on'⟩ r') →
      NReaches σ.edges u (objNode ⟨dt', on'⟩ r') :=
    fun hn => reconcileKeyD_reach_inert T dt on R e cands hRne hvne1 hcands hRns hn
  have hinert3 : ∀ {u : NodeKey},
      NReaches (σ.reconcileKeyD T dt on R e cands).edges u (wAllNode dt' r') →
      NReaches σ.edges u (wAllNode dt' r') :=
    fun hn => reconcileKeyD_reach_inert T dt on R e cands hRne hvne3 hcands hRns hn
  unfold GraphModel.graphRec
  cases hb2 : GraphModel.probeNonDerived (σ.reconcileKeyD T dt on R e cands)
      (⟨s, r', ⟨dt', on'⟩⟩ : Query)
    <;> cases hb1 : GraphModel.probeNonDerived σ (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  · rfl
  · exfalso
    have hd := hiff1.mp hb1
    have : GraphModel.probeNonDerived (σ.reconcileKeyD T dt on R e cands)
        (⟨s, r', ⟨dt', on'⟩⟩ : Query) = true := by
      apply hiff2.mpr
      rcases hd with h1 | ⟨hs, h2⟩ | ⟨ho, h3⟩ | ⟨hs, ho, h4⟩
      · exact Or.inl (hpres1 h1)
      · exact Or.inr (Or.inl ⟨hs, hpres1 h2⟩)
      · exact Or.inr (Or.inr (Or.inl ⟨ho, hpres3 h3⟩))
      · exact Or.inr (Or.inr (Or.inr ⟨hs, ho, hpres3 h4⟩))
    rw [hb2] at this
    cases this
  · exfalso
    have hd := hiff2.mp hb2
    have : GraphModel.probeNonDerived σ (⟨s, r', ⟨dt', on'⟩⟩ : Query) = true := by
      apply hiff1.mpr
      rcases hd with h1 | ⟨hs, h2⟩ | ⟨ho, h3⟩ | ⟨hs, ho, h4⟩
      · exact Or.inl (hinert1 h1)
      · exact Or.inr (Or.inl ⟨hs, hinert1 h2⟩)
      · exact Or.inr (Or.inr (Or.inl ⟨ho, hinert3 h3⟩))
      · exact Or.inr (Or.inr (Or.inr ⟨hs, ho, hinert3 h4⟩))
    rw [hb1] at this
    cases this
  · rfl

/-! ## Per-key edge exactness — the settledness core (ROADMAP W3d-1b)

After ONE diffing pass, the derived edge set at the pass's key is EXACTLY
`{c ∈ cands : want c at pass start}` plus the untouched edges of non-candidates —
presence for candidates no longer depends on history. This is the cascade-leg heart
of the W3d settledness invariant: a re-reconcile genuinely RE-SETTLES its key. -/

/-- The per-candidate edge guard `want = should ∧ ¬covered`
    (`reconcile_subject`, `processor.py:359`). -/
def GraphState.wantEdge (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (c : SubjectRef) : Bool :=
  σ.checkFn T c dt on R e && !(σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)

/-- A one-candidate fold is a single diff step, guard spelled via `wantEdge`. -/
theorem reconcileKeyD_singleton (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (c : SubjectRef) :
    σ.reconcileKeyD T dt on R e [c]
      = if σ.wantEdge T dt on R e c then σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩
        else σ.removeEdgePair (subjNode c) (objNode ⟨dt, on⟩ R) := rfl

/-- The guard is fold-invariant: `wantEdge` after the fold equals `wantEdge` at the
    start (operand-read inertness + the fold never writes residues). -/
theorem wantEdge_reconcileKeyD_inert {σ : GraphState} {S : Schema} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) (hRne : R ≠ BARE)
    (hcands : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hlu : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) (x : SubjectRef) :
    (σ.reconcileKeyD T dt on R e cands).wantEdge T dt on R e x
      = σ.wantEdge T dt on R e x := by
  unfold GraphState.wantEdge
  have hchk : (σ.reconcileKeyD T dt on R e cands).checkFn T x dt on R e
      = σ.checkFn T x dt on R e :=
    checkFn_agree_of_graphRec (S := S) T x dt on R e hco hlu
      (fun s' r' hr' => graphRec_reconcileKeyD_inert T dt on R e cands hRne hcands hRns
        honStar hder hcl s' dt on r' hr')
  have hcov : (σ.reconcileKeyD T dt on R e cands).coveredAt (objNode ⟨dt, on⟩ R) R x.shape
      = σ.coveredAt (objNode ⟨dt, on⟩ R) R x.shape := by
    unfold GraphState.coveredAt
    rw [reconcileKeyD_residue]
  rw [hchk, hcov]

/-- The accepted derived edge: writing an uncovered wanted candidate at a terminal
    R-node is always admitted (no self-loop — the preds differ; no back-path — the
    R-node has no out-edges). -/
theorem writeDirect_pair_present {σ : GraphState} {c : SubjectRef} {dt on R : String}
    (hcb : c.predicate = BARE) (hRne : R ≠ BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) :
    (subjNode c, objNode ⟨dt, on⟩ R) ∈ (σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩).edges := by
  have hadm : σ.admitEdge (subjNode c) (objNode ⟨dt, on⟩ R) = true := by
    unfold GraphState.admitEdge
    rw [Bool.and_eq_true]
    constructor
    · rw [bne_iff_ne]
      intro heq
      have hpred := congrArg NodeKey.pred heq
      rw [subjNode_pred, objNode_pred, hcb] at hpred
      exact hRne hpred.symm
    · cases hr : σ.reach (objNode ⟨dt, on⟩ R) (subjNode c)
      · rfl
      · exfalso
        obtain ⟨y, hy⟩ := nreaches_first_edge (reach_sound hr)
        exact hRns y hy
  rw [writeDirect_edges, if_pos hadm]
  exact List.mem_cons_self

/-- **The per-key edge characterisation** (guards abstracted to a fold-invariant `g`):
    after the diffing fold, the derived pair of a subject `s` is present iff `s` is a
    candidate with `g s` true, or a non-candidate whose pair was already present.
    History for candidates is fully erased — the re-settle. -/
theorem reconcileKeyD_edge_char {S : Schema} (T : Store) (dt on R : String) (e : Expr)
    (hRne : R ≠ BARE) (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hlu : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (g : SubjectRef → Bool) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (∀ c ∈ cands, c.predicate = BARE) →
      (∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) →
      (∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) →
      (∀ c ∈ cands, σ.wantEdge T dt on R e c = g c) →
      ∀ s : SubjectRef,
        ((subjNode s, objNode ⟨dt, on⟩ R) ∈ (σ.reconcileKeyD T dt on R e cands).edges
          ↔ ((s ∈ cands ∧ g s = true) ∨
             (s ∉ cands ∧ (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges))) := by
  intro cands
  induction cands with
  | nil =>
    intro σ _ _ _ _ s
    show (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges ↔ _
    simp
  | cons c rest ih =>
    intro σ hcb hRns hcl hg s
    have hcb1 : ∀ x ∈ [c], x.predicate = BARE := by
      intro x hx
      rw [List.mem_singleton.mp hx]
      exact hcb c List.mem_cons_self
    -- the step state is the singleton fold
    have hstep : σ.reconcileKeyD T dt on R e (c :: rest)
        = (σ.reconcileKeyD T dt on R e [c]).reconcileKeyD T dt on R e rest := rfl
    set σc := σ.reconcileKeyD T dt on R e [c] with hσc
    -- step-state facts
    have hRns1 : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σc.edges :=
      reconcileKeyD_Rnode_terminal T dt on R e hRne [c] hcb1 σ hRns
    have hcl1 : ∀ ab ∈ σc.edges, ab.1 ∈ σc.nodes ∧ ab.2 ∈ σc.nodes :=
      edgesClosed_reconcileKeyD T dt on R e [c] σ hcl
    have hg1 : ∀ x ∈ rest, σc.wantEdge T dt on R e x = g x := by
      intro x hx
      rw [hσc, wantEdge_reconcileKeyD_inert (S := S) T dt on R e [c] hRne hcb1 hRns
        honStar hder hco hlu hcl x]
      exact hg x (List.mem_cons_of_mem _ hx)
    have hgc : σ.wantEdge T dt on R e c = g c := hg c List.mem_cons_self
    -- the step-state pair membership, characterized
    have hpairc : ∀ s : SubjectRef,
        ((subjNode s, objNode ⟨dt, on⟩ R) ∈ σc.edges
          ↔ ((s = c ∧ g c = true) ∨
             (s ≠ c ∧ (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges))) := by
      intro s
      rw [hσc, reconcileKeyD_singleton, hgc]
      cases hgcv : g c
      · -- removal step
        rw [if_neg (by simp), mem_removeEdgePair_edges]
        constructor
        · rintro ⟨hmem, hne⟩
          refine Or.inr ⟨?_, hmem⟩
          intro heq
          exact hne ⟨by rw [heq], rfl⟩
        · rintro (⟨_, hfalse⟩ | ⟨hne, hmem⟩)
          · exact absurd hfalse (by simp)
          · refine ⟨hmem, ?_⟩
            rintro ⟨h1, _⟩
            exact hne (subjNode_inj_total h1)
      · -- write step
        rw [if_pos rfl, writeDirect_edges]
        have hadm : σ.admitEdge (subjNode c) (objNode ⟨dt, on⟩ R) = true := by
          unfold GraphState.admitEdge
          rw [Bool.and_eq_true]
          constructor
          · rw [bne_iff_ne]
            intro heq
            have hpred := congrArg NodeKey.pred heq
            rw [subjNode_pred, objNode_pred, hcb c List.mem_cons_self] at hpred
            exact hRne hpred.symm
          · cases hr : σ.reach (objNode ⟨dt, on⟩ R) (subjNode c)
            · rfl
            · exfalso
              obtain ⟨y, hy⟩ := nreaches_first_edge (reach_sound hr)
              exact hRns y hy
        rw [if_pos hadm]
        constructor
        · intro hmem
          rcases List.mem_cons.mp hmem with heq | hold
          · have h1 := (Prod.ext_iff.mp heq).1
            exact Or.inl ⟨subjNode_inj_total h1, rfl⟩
          · by_cases hsc : s = c
            · exact Or.inl ⟨hsc, rfl⟩
            · exact Or.inr ⟨hsc, hold⟩
        · rintro (⟨hsc, _⟩ | ⟨_, hold⟩)
          · rw [hsc]
            exact List.mem_cons_self
          · exact List.mem_cons_of_mem _ hold
    -- assemble via the IH at the step state
    rw [hstep]
    rw [ih σc (fun x hx => hcb x (List.mem_cons_of_mem _ hx)) hRns1 hcl1 hg1 s]
    rw [hpairc s]
    constructor
    · rintro (⟨hsr, hgs⟩ | ⟨hsr, (⟨hsc, hgc'⟩ | ⟨hsc, hold⟩)⟩)
      · exact Or.inl ⟨List.mem_cons_of_mem _ hsr, hgs⟩
      · exact Or.inl ⟨by rw [hsc]; exact List.mem_cons_self, by rw [hsc]; exact hgc'⟩
      · refine Or.inr ⟨?_, hold⟩
        intro hmem
        rcases List.mem_cons.mp hmem with heq | hr
        · exact hsc heq
        · exact hsr hr
    · rintro (⟨hmem, hgs⟩ | ⟨hmem, hold⟩)
      · rcases List.mem_cons.mp hmem with heq | hr
        · by_cases hsr : s ∈ rest
          · exact Or.inl ⟨hsr, hgs⟩
          · exact Or.inr ⟨hsr, Or.inl ⟨heq, by rw [← heq]; exact hgs⟩⟩
        · exact Or.inl ⟨hr, hgs⟩
      · have hsc : s ≠ c := fun heq => hmem (by rw [heq]; exact List.mem_cons_self)
        have hsr : s ∉ rest := fun hr => hmem (List.mem_cons_of_mem _ hr)
        exact Or.inr ⟨hsr, Or.inr ⟨hsc, hold⟩⟩

/-- **Pass-level edge exactness** (`reconcileStarsKeyD_edge_char`): after one
    full-object diffing pass, a subject's derived edge at the key is present iff it is
    a candidate whose guard holds at the PASS-START state — `checkFn` true and its
    shape not in the freshly-recomputed `stars` row — or a non-candidate whose edge
    predates the pass. The wholesale re-settle, as a theorem. -/
theorem reconcileStarsKeyD_edge_char {S : Schema} {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef)
    (hRne : R ≠ BARE) (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hlu : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hcb : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (s : SubjectRef) :
    ((subjNode s, objNode ⟨dt, on⟩ R)
        ∈ (σ.reconcileStarsKeyD T dt on R e shapes cands negCands uposCands).edges
      ↔ ((s ∈ cands ∧ (σ.checkFn T s dt on R e
            && !((shapes.filter (fun sh => σ.coveredFn T dt on R e sh)).contains
                  s.shape)) = true) ∨
         (s ∉ cands ∧ (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges))) := by
  unfold GraphState.reconcileStarsKeyD
  set σr := σ.reconcileResidueKey T dt on R e shapes negCands uposCands with hσr
  have hedges : σr.edges = σ.edges := by rw [hσr]; rfl
  have hnodes : σr.nodes = σ.nodes := by rw [hσr]; rfl
  have hRnsr : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σr.edges := by
    intro y
    rw [hedges]
    exact hRns y
  have hclr : ∀ ab ∈ σr.edges, ab.1 ∈ σr.nodes ∧ ab.2 ∈ σr.nodes := by
    intro ab hab
    rw [hedges] at hab
    rw [hnodes]
    exact hcl ab hab
  -- the fold-invariant guard, evaluated at the ORIGINAL σ
  have hg : ∀ c ∈ cands, σr.wantEdge T dt on R e c
      = (σ.checkFn T c dt on R e
          && !((shapes.filter (fun sh => σ.coveredFn T dt on R e sh)).contains c.shape)) := by
    intro c _
    unfold GraphState.wantEdge
    rw [checkFn_congr hedges hnodes T c dt on R e]
    unfold GraphState.coveredAt
    rw [hσr, reconcileResidueKey_residue_self]
    rfl
  have hchar := reconcileKeyD_edge_char (S := S) T dt on R e hRne honStar hder hco hlu
    (fun c => σ.checkFn T c dt on R e
      && !((shapes.filter (fun sh => σ.coveredFn T dt on R e sh)).contains c.shape))
    cands σr hcb hRnsr hclr hg s
  rw [hchar, hedges]

end Zanzibar
