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

end Zanzibar
