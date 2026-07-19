import ZanzibarProofs.GraphIndex.ReconcileDiff

/-!
# The cascade scheduling layer — logged writes, delta→key mapping, the drain loop (ROADMAP W3d-1a)

`index_v4/processor.py` `run_cascade` (`:694-740`), `_map_deltas_to_keys` (`:585-652`),
`_fan_out` (`:654-692`); `core.py:_emit` (`:31-44`); `outbox.py`;
`connectedstore/apply.py:79-87`; boolean spec §5.1–5.2. Design + faithfulness notes:
ROADMAP "W3d — the multi-stratum cascade".

W3a–W3c treated a reconcile pass as an externally-scheduled batch job. **W3d models the
scheduler**: writes emit outbox deltas inside the transaction, `run_cascade` maps the
frontier's deltas to affected derived keys, reconciles each, and advances the watermark
— with Python's final leftover check (`InvariantViolation` on non-quiescence,
`processor.py:729-739`) modeled as a REJECT branch, and T5 = the reject provably never
fires on the fragment (`runCascade_no_abort`) so the watermark advance is justified,
never asserted (`cascade_drains`).

Modeling decisions (ROADMAP W3d, decisions 1–6):
1. **One outbox row per accepted ROUTED edge** (not per raw write — a computed rewrite
   lands sibling-family tuples with no graph edge from the seed's object node, so the
   seed's reach cone would miss the sibling operand key). Python emits one row per
   materialized closure-pair flip; the row set's object ends `{y : b ⇝ y}` are
   recovered at cascade time as the reach cone of the routed edge's object node
   (add-only ⇒ superset ⇒ at worst extra idempotent reconciles).
2. **Fresh ids** `max maxOutboxId watermark + 1` — strictly above both existing rows
   and the drain frontier (never mint a born-drained row).
3. **Processor emission modeled**: one row per reconcile pass at its derived key — the
   coalescing of the pass's per-flip rows, which all share that object end by R-node
   terminality (re-proved over the interleaved closure:
   `reconcileJobsL_Rnode_not_source`).
4. **The key mapping** `affectedKeys` = `_map_deltas_to_keys`'s LeafFamily branch +
   `_fan_out`'s `via='computed'` branch, restricted to the fragment (`hLU`: operands
   are same-object untainted computed refs; the ttu/userset/tupleset-ttu dependent
   branches are out of fragment by `hterm`/`hCO`). The subject-level cheap path is
   NOT modeled (the model always full-object reconciles — Python's general path; the
   cheap path is an optimization with its own §5.4 escalations to full).
5. **The loop** at one stratum: one round, then the leftover check as the
   accept/reject branch of `runCascade`.
6. **Add-only STORE**: no store removes; the remove-side hazards (operand-removal
   re-reconcile, `neg` pruning after node GC, REMOVED deltas) are out of scope for
   W3d-1.
7. **The pass is the DIFFING audit** (`reconcileStarsKeyD`, 2026-07-11f): W3d's store
   grows between cascades, so a derived guard can flip DOWN (`excl` operand add) and
   the pass must RETRACT the stale derived edge — exactly Python's
   `reconcile_subject` removal branch (`processor.py:365-367`). The add-only pass
   model was refuted by `#eval` at a cascaded state (see `ReconcileDiff.lean` header);
   W3a–W3c keep the add-only pass, where fixed-store guard stability makes the
   removal branch provably dead.

The W3c read-correspondence transfer (via `EvalEq` + the W3d analog of the coverage
clauses) is W3d-1b/1c — see ROADMAP. NB the W3a SHADOW does not extend over diffing
passes (a removal is not a W3a reconcile leg), so W3d-1b re-derives its read bridge
over the interleaved closure directly.

**Attack-first (2026-07-11e, machine-checked `#eval` vs the real `check`/`sem`,
scratch deleted).** Corpus `viewer := member ∖ banned` (`member` admitting `user`,
`user:*`, `group#mem`), 5 logged writes: the frontier's 5 rows mapped to the viewer
key (via direct, star, userset and group-flow cones); `runCascade` with one covering
job took the ACCEPT branch (watermark 0→6), the state was `Quiescent`, and the full
18-query grid matched `sem` (bare incl. a ghost concrete-under-star, star, userset
subjects). **The cross-key hazard**: a post-cascade `banned` write re-mapped the
EXISTING viewer key through the `banned` operand cone — and until that second cascade
ran, the derived read was STALE (`check = true ≠ sem = false` for the newly-banned
subject), confirming the model claim scope: reads are correct at CASCADED states
(Python: `run_cascade` runs inside every writing transaction). The second cascade's
own pass row mapped to `[]` (the no-abort content) while the write's row mapped to
the key; an empty-frontier cascade was a no-op accept. No refutation. -/

namespace Zanzibar

/-! ## Outbox primitives -/

/-- The highest outbox id (0 if empty) — `outbox_watermark` (`outbox.py:13-21`). -/
def GraphState.maxOutboxId (σ : GraphState) : Nat :=
  σ.outbox.foldl (fun m d => max m d.id) 0

/-- Fold-max dominates its initial accumulator. -/
theorem foldl_max_init_le (l : List Delta) :
    ∀ a : Nat, a ≤ l.foldl (fun m d => max m d.id) a := by
  induction l with
  | nil => intro a; exact Nat.le_refl a
  | cons d rest ih =>
    intro a
    exact le_trans (Nat.le_max_left a d.id) (ih (max a d.id))

/-- Fold-max dominates every member's id. -/
theorem mem_le_foldl_max (l : List Delta) :
    ∀ (a : Nat), ∀ d ∈ l, d.id ≤ l.foldl (fun m d => max m d.id) a := by
  induction l with
  | nil => intro a d hd; cases hd
  | cons e rest ih =>
    intro a d hd
    rcases List.mem_cons.mp hd with rfl | hmem
    · exact le_trans (Nat.le_max_right a d.id) (foldl_max_init_le rest _)
    · exact ih _ d hmem

/-- Every outbox row's id is bounded by `maxOutboxId`. -/
theorem mem_outbox_le_maxOutboxId (σ : GraphState) :
    ∀ d ∈ σ.outbox, d.id ≤ σ.maxOutboxId :=
  mem_le_foldl_max σ.outbox 0

/-- Fold-max splits off its accumulator. -/
theorem foldl_max_comm (l : List Delta) :
    ∀ a : Nat, l.foldl (fun m d => max m d.id) a
      = max a (l.foldl (fun m d => max m d.id) 0) := by
  induction l with
  | nil => intro a; simp
  | cons d rest ih =>
    intro a
    simp only [List.foldl_cons]
    rw [ih (max a d.id), ih (max 0 d.id)]
    omega

/-- The next fresh delta id: strictly above both the existing rows and the drain
    watermark (decision 2 — a plain `maxId+1` could mint a born-drained row). -/
def GraphState.nextDeltaId (σ : GraphState) : Nat :=
  max σ.maxOutboxId σ.watermark + 1

/-- Append one delta row (`core.py:_emit` — a row inserted inside the writing
    transaction; the autoincrement id is the cursor). `leaf` records the row's
    provenance (Python LeafFamily vs DerivedFamily, see `Delta`): reconcile emissions
    default to `false`; raw leaf-routed writes/removes pass `true`. Only `affectedKeys`
    reads it, so every other observation is `leaf`-agnostic (the simp lemmas quantify
    over it). -/
def GraphState.pushDelta (σ : GraphState) (k : NodeKey) (r : String)
    (leaf : Bool := false) : GraphState :=
  { σ with outbox := ⟨σ.nextDeltaId, k, r, leaf⟩ :: σ.outbox }

@[simp] theorem pushDelta_schema (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).schema = σ.schema := rfl
@[simp] theorem pushDelta_edges (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).edges = σ.edges := rfl
@[simp] theorem pushDelta_nodes (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).nodes = σ.nodes := rfl
@[simp] theorem pushDelta_residue (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).residue = σ.residue := rfl
@[simp] theorem pushDelta_watermark (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).watermark = σ.watermark := rfl
@[simp] theorem pushDelta_outbox (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).outbox = ⟨σ.nextDeltaId, k, r, b⟩ :: σ.outbox := rfl

/-- Pushing a row moves `maxOutboxId` to exactly the fresh id. -/
theorem pushDelta_maxOutboxId (σ : GraphState) (k : NodeKey) (r : String) (b : Bool) :
    (σ.pushDelta k r b).maxOutboxId = σ.nextDeltaId := by
  show (⟨σ.nextDeltaId, k, r, b⟩ :: σ.outbox).foldl (fun m d => max m d.id) 0
    = σ.nextDeltaId
  rw [List.foldl_cons, foldl_max_comm]
  show max (max 0 σ.nextDeltaId) σ.maxOutboxId = σ.nextDeltaId
  have : σ.nextDeltaId = max σ.maxOutboxId σ.watermark + 1 := rfl
  omega

/-! ## Logged writes (decision 1) -/

/-- One logged routed-edge write: materialize the guarded edge and, iff it was
    admitted, emit its delta row (`_emit` fires on actual flips; a rejected write
    inserts nothing). -/
def GraphState.writeLoggedOne (σ : GraphState) (t : Tuple) : GraphState :=
  if σ.admitEdge (subjNode t.subject) (objNode t.object t.relation)
  then (σ.writeDirect t).pushDelta (objNode t.object t.relation) t.relation true
  else σ

/-- **The logged rule-routed write**: W2's `writeRules` fold with a delta row per
    accepted rewrite-closure member (`RuleSet.apply` + per-triple `add_tuple`, each
    `add_edge` emitting its flips). -/
def GraphState.writeLoggedRules (σ : GraphState) (S : Schema) (t : Tuple) : GraphState :=
  (rewriteClosure S t).foldl (fun acc u => acc.writeLoggedOne u) σ

/-! ## `EvalEq` — the read-relevant core, and the logged/unlogged correspondence -/

/-- **`EvalEq σ' σ`** — agreement on everything the READ consults: schema, edges,
    nodes, residue. The W3d projection relation (`CoreEq` is too strong once the
    outbox/watermark genuinely differ between the logged chain and its unlogged
    twin). -/
structure EvalEq (σ' σ : GraphState) : Prop where
  schema : σ'.schema = σ.schema
  edges : σ'.edges = σ.edges
  nodes : σ'.nodes = σ.nodes
  residue : σ'.residue = σ.residue

theorem EvalEq.refl (σ : GraphState) : EvalEq σ σ := ⟨rfl, rfl, rfl, rfl⟩

theorem EvalEq.trans {σ₁ σ₂ σ₃ : GraphState} (h₁ : EvalEq σ₁ σ₂) (h₂ : EvalEq σ₂ σ₃) :
    EvalEq σ₁ σ₃ :=
  ⟨h₁.schema.trans h₂.schema, h₁.edges.trans h₂.edges, h₁.nodes.trans h₂.nodes,
   h₁.residue.trans h₂.residue⟩

/-- `admitEdge` is `EvalEq`-congruent (it probes reachability over edges with
    node-count fuel). -/
theorem admitEdge_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (a b : NodeKey) :
    σ'.admitEdge a b = σ.admitEdge a b := by
  unfold GraphState.admitEdge GraphState.reach
  rw [h.edges, h.nodes]

/-- `writeDirect` is `EvalEq`-congruent (it reads and writes only edges/nodes). -/
theorem writeDirect_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (t : Tuple) :
    EvalEq (σ'.writeDirect t) (σ.writeDirect t) := by
  unfold GraphState.writeDirect
  dsimp only
  rw [admitEdge_evalEq h]
  by_cases hb : σ.admitEdge (subjNode t.subject) (objNode t.object t.relation) = true
  · rw [if_pos hb, if_pos hb]
    exact ⟨h.schema, by simp [h.edges], by simp [h.nodes], by simp [h.residue]⟩
  · rw [if_neg hb, if_neg hb]
    exact h

/-- One logged write step is `EvalEq` to the unlogged step. -/
theorem writeLoggedOne_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (t : Tuple) :
    EvalEq (σ'.writeLoggedOne t) (σ.writeDirect t) := by
  unfold GraphState.writeLoggedOne
  rw [admitEdge_evalEq h]
  by_cases hb : σ.admitEdge (subjNode t.subject) (objNode t.object t.relation) = true
  · rw [if_pos hb]
    have hw := writeDirect_evalEq h t
    exact ⟨hw.schema, hw.edges, hw.nodes, hw.residue⟩
  · rw [if_neg hb]
    rw [writeDirect_reject (Bool.eq_false_iff.mpr hb)]
    exact h

/-- **The logged routed write's core is the unlogged `writeRules`.** All W2 edge/node
    facts about `writeRules` transfer to `writeLoggedRules` through this. -/
theorem writeLoggedRules_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (S : Schema)
    (t : Tuple) : EvalEq (σ'.writeLoggedRules S t) (σ.writeRules S t) := by
  unfold GraphState.writeLoggedRules GraphState.writeRules
  generalize rewriteClosure S t = ts
  induction ts generalizing σ' σ with
  | nil => exact h
  | cons u rest ih =>
    simp only [List.foldl_cons]
    exact ih (writeLoggedOne_evalEq h u)

/-- The logged write leaves the watermark untouched. -/
theorem writeLoggedRules_watermark (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.writeLoggedRules S t).watermark = σ.watermark := by
  unfold GraphState.writeLoggedRules
  generalize rewriteClosure S t = ts
  induction ts generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih]
    unfold GraphState.writeLoggedOne
    split
    · rw [pushDelta_watermark, writeDirect_watermark]
    · rfl

/-! ## Logged retractions (W3d remove-leg R2 substrate — the retract mirror of the
    logged writes above)

`_apply_row` (`connectedstore/apply.py:48-68`) routes BOTH an ADD and a REMOVE log row
through the IDENTICAL `ruleset.apply(triple)` rewrite fan-out (`apply.py:61`), then applies
`_add_tuple_trusted` (ADD) or `_remove_tuple_trusted` (REMOVE) per rewrite-closure member.
So the retraction of a raw tuple is the fold of a per-member edge decrement over the SAME
`rewriteClosure S t` the write path folds `writeLoggedOne` over — modelled below as
`removeLoggedRules`, the exact retract mirror of `writeLoggedRules`. The per-member step
uses `removeEdgeOne` (erase ONE copy — the ref-counted `-1`, NOT the filter-all
`removeEdgePair`; see the `ReconcileDiff.lean` R1 KILL note) and emits its retraction
delta the way `writeLoggedOne` emits its write delta. These are STANDALONE additive defs:
the `remove` constructor on `ReachedByW3d2E` (which consumes them) is a LATER leg (R5),
armed with the R4 confluence — added last so every increment stays green. -/

/-- One logged routed-edge retraction: erase ONE copy of the guarded direct edge and,
    iff a copy was actually present to remove, emit its retraction delta row. The exact
    retract mirror of `writeLoggedOne`: where the write emits iff the edge was ADMITTED
    (the direct-edge multiset GREW), the retraction emits iff the edge was PRESENT (the
    multiset SHRANK) — same "emit on an actual flip of the direct-edge multiset" rule, one
    delta at the object node with the tuple's relation. Mirror of Python
    `_remove_tuple_trusted` → `remove_edge_by_id` → `_remove_edge_locked`
    (`index_v4/core.py:686-704`): the ref-counted `-1` update
    (`_add_direct_edge_unsafe(subject_id, object_id, -1)`, `core.py:704`) is the sole
    driver of `_emit(subject_id, object_id, "REMOVED")` on the reachability flip
    (`core.py:278`, denormalised over the closure; the model reconstructs that cone at
    cascade time via `affectedObjects`, decision 1). The presence guard mirrors the
    `direct_edge_count == 0 ⇒ ValueError` reject (`core.py:700-702`) / the
    non-existent-endpoint `ValueError` (`index_v4/wildcard.py:320-323`); store consistency
    makes the else-branch dead at every admitted removal (an R3 fact), so it is present
    only for totality. -/
def GraphState.removeLoggedOne (σ : GraphState) (t : Tuple) : GraphState :=
  if (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges
  then (σ.removeEdgeOne (subjNode t.subject) (objNode t.object t.relation)).pushDelta
    (objNode t.object t.relation) t.relation true
  else σ

/-- **The logged rule-routed retraction**: the retract mirror of `writeLoggedRules` — fold
    `removeLoggedOne` over the SAME `rewriteClosure S t` the write path folds
    `writeLoggedOne` over (`RuleSet.apply t` as a list, `RulesWrite.lean:106`). Mirrors
    `_apply_row`'s REMOVE branch: `ruleset.apply(triple)` fan-out
    (`connectedstore/apply.py:61`) with `_remove_tuple_trusted` per member. -/
def GraphState.removeLoggedRules (σ : GraphState) (S : Schema) (t : Tuple) : GraphState :=
  (rewriteClosure S t).foldl (fun acc u => acc.removeLoggedOne u) σ

/-- **The chain-level retraction admission guard** — the retract mirror of the write leg's
    `FoldAdmits`. A raw tuple may be retracted only if it is IN the store: `t ∈ T`. Mirror
    of `TupleSource.remove` (`connectedstore/source.py:104-112`), whose `engine.remove_tuple`
    raises `ValueError` and logs nothing on an absent tuple. `σ` is carried for constructor
    symmetry with the write leg's `hadm : FoldAdmits σ …` (the guard itself is store-only). -/
def RemoveAdmits (_σ : GraphState) (T : Store) (t : Tuple) : Prop := t ∈ T

/-- One logged retraction leaves the schema fixed. -/
@[simp] theorem removeLoggedOne_schema (σ : GraphState) (t : Tuple) :
    (σ.removeLoggedOne t).schema = σ.schema := by
  unfold GraphState.removeLoggedOne
  split
  · rw [pushDelta_schema, removeEdgeOne_schema]
  · rfl

/-- One logged retraction leaves the nodes fixed (node GC is modeled away, cf.
    `removeEdgeOne`). -/
@[simp] theorem removeLoggedOne_nodes (σ : GraphState) (t : Tuple) :
    (σ.removeLoggedOne t).nodes = σ.nodes := by
  unfold GraphState.removeLoggedOne
  split
  · rw [pushDelta_nodes, removeEdgeOne_nodes]
  · rfl

/-- One logged retraction leaves the watermark untouched (it only decrements an edge and
    appends a frontier row — the drain watermark advances in the cascade, not here). -/
@[simp] theorem removeLoggedOne_watermark (σ : GraphState) (t : Tuple) :
    (σ.removeLoggedOne t).watermark = σ.watermark := by
  unfold GraphState.removeLoggedOne
  split
  · rw [pushDelta_watermark, removeEdgeOne_watermark]
  · rfl

/-- The logged retraction keeps the schema fixed (a fold of `removeLoggedOne_schema`). -/
theorem removeLoggedRules_schema (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.removeLoggedRules S t).schema = σ.schema := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosure S t = ts
  induction ts generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih]; exact removeLoggedOne_schema σ u

/-- The logged retraction keeps the nodes fixed (a fold of `removeLoggedOne_nodes`). -/
theorem removeLoggedRules_nodes (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.removeLoggedRules S t).nodes = σ.nodes := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosure S t = ts
  induction ts generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih]; exact removeLoggedOne_nodes σ u

/-- The logged retraction leaves the watermark untouched (mirror of
    `writeLoggedRules_watermark`; a fold of `removeLoggedOne_watermark`). -/
theorem removeLoggedRules_watermark (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.removeLoggedRules S t).watermark = σ.watermark := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosure S t = ts
  induction ts generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih]; exact removeLoggedOne_watermark σ u

/-! ## The reconcile pass is `EvalEq`-congruent -/

/-- Persisted coverage is residue-determined. -/
theorem coveredAt_congr {σ' σ : GraphState} (h : σ'.residue = σ.residue) (k : NodeKey)
    (R : String) (sh : Shape) : σ'.coveredAt k R sh = σ.coveredAt k R sh := by
  unfold GraphState.coveredAt
  rw [h]

/-- The wholesale residue recompute is `EvalEq`-congruent (its three filters read
    `checkFn`/`coveredFn`, which consult only edges/nodes). -/
theorem reconcileResidueKey_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (negCands uposCands : List SubjectRef) :
    EvalEq (σ'.reconcileResidueKey T dt on R e shapes negCands uposCands)
      (σ.reconcileResidueKey T dt on R e shapes negCands uposCands) := by
  have hcov : ∀ sh : Shape, σ'.coveredFn T dt on R e sh = σ.coveredFn T dt on R e sh := by
    intro sh
    unfold GraphState.coveredFn
    exact checkFn_congr h.edges h.nodes T _ dt on R e
  have hchk : ∀ c : SubjectRef, σ'.checkFn T c dt on R e = σ.checkFn T c dt on R e :=
    fun c => checkFn_congr h.edges h.nodes T c dt on R e
  refine ⟨?_, ?_, ?_, ?_⟩
  · rw [reconcileResidueKey_schema, reconcileResidueKey_schema]; exact h.schema
  · rw [reconcileResidueKey_edges, reconcileResidueKey_edges]; exact h.edges
  · rw [reconcileResidueKey_nodes, reconcileResidueKey_nodes]; exact h.nodes
  · funext k' r'
    by_cases hk : k' = objNode ⟨dt, on⟩ R ∧ r' = R
    · obtain ⟨hk1, hk2⟩ := hk
      subst hk1; subst hk2
      rw [reconcileResidueKey_residue_self, reconcileResidueKey_residue_self]
      simp only [hcov, hchk]
    · rw [reconcileResidueKey_residue_other hk, reconcileResidueKey_residue_other hk]
      rw [h.residue]

/-- Edge removal is `EvalEq`-congruent. -/
theorem removeEdgePair_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (a b : NodeKey) :
    EvalEq (σ'.removeEdgePair a b) (σ.removeEdgePair a b) :=
  ⟨h.schema, by rw [removeEdgePair_edges, removeEdgePair_edges, h.edges],
   by rw [removeEdgePair_nodes, removeEdgePair_nodes, h.nodes],
   by rw [removeEdgePair_residue, removeEdgePair_residue, h.residue]⟩

/-- The diffing edge audit is `EvalEq`-congruent. -/
theorem reconcileKeyD_evalEq (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) {σ' σ : GraphState}, EvalEq σ' σ →
      EvalEq (σ'.reconcileKeyD T dt on R e cands) (σ.reconcileKeyD T dt on R e cands) := by
  intro cands
  induction cands with
  | nil => intro σ' σ h; exact h
  | cons c rest ih =>
    intro σ' σ h
    rw [reconcileKeyD_cons, reconcileKeyD_cons, checkFn_congr h.edges h.nodes T c dt on R e,
      coveredAt_congr h.residue]
    split
    · exact ih (writeDirect_evalEq h ⟨c, R, ⟨dt, on⟩⟩)
    · exact ih (removeEdgePair_evalEq h _ _)

/-- **The combined diffing pass is `EvalEq`-congruent.** -/
theorem reconcileStarsKeyD_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef) :
    EvalEq (σ'.reconcileStarsKeyD T dt on R e shapes cands negCands uposCands)
      (σ.reconcileStarsKeyD T dt on R e shapes cands negCands uposCands) := by
  unfold GraphState.reconcileStarsKeyD
  exact reconcileKeyD_evalEq T dt on R e cands
    (reconcileResidueKey_evalEq h T dt on R e shapes negCands uposCands)

/-! ## The delta → key mapping (decision 4) -/

/-- Candidate object nodes of one delta: the row's own object node plus its
    cascade-time reach cone — the model-level reconstruction of the per-flip rows'
    denormalized object ends (`{y : b ⇝ y}`, decision 1). -/
def GraphState.affectedObjects (σ : GraphState) (d : Delta) : List NodeKey :=
  d.node :: σ.nodes.filter (fun v => σ.reach d.node v)

/-- **The delta → derived-key mapping** (`_map_deltas_to_keys`, `processor.py:989-1027`).

    Two branches, matching Python's LeafFamily/DerivedFamily split on the delta row:

    * **LeafFamily own-key branch** (`processor.py:991-1011`): a RAW leaf-routed
      write/remove (`d.leaf = true`) on a DERIVED relation dirties its OWN derived key
      `(d.node.type, d.node.pred, d.node.name)` (Python routes the write onto the
      storage leaf `<R>.<i>` and dirties `key = (o_type, fam.owner_relation, o_name)`).
      Guarded `d.node.name ≠ STAR` (`processor.py:993`: a wildcard-object delta on a
      derived key is a leaked decision-15 shape) and `isDerived` (untainted leaves have
      no derived own-key; and reconcile emissions carry `leaf = false`, so this branch is
      empty for them — the fence that lets the cascade quiesce, since `_fan_out` never
      re-dirties its own key).
    * **DerivedFamily fan-out** (`_fan_out via='computed'`, fragment-restricted): a
      candidate object node `v` (concrete — derived keys are never star-named,
      `processor.py:604-605`) dirties every declared derived key `(v.type, R)` whose def
      reads `v.pred` as a computed operand, at object `v.name`.

    Keys are `(dt, R, on)` triples. -/
def affectedKeys (S : Schema) (σ : GraphState) (d : Delta) :
    List (String × String × String) :=
  (if d.leaf = true ∧ d.node.name ≠ STAR ∧ isDerived S (d.node.type, d.node.pred) = true
   then [(d.node.type, d.node.pred, d.node.name)] else [])
  ++ (σ.affectedObjects d).flatMap (fun v =>
    if v.name = STAR then []
    else S.keys.filterMap (fun k =>
      if k.1 = v.type ∧ isDerived S k = true ∧
          ((S.lookup k).map (fun e => (computedRefs e).contains v.pred)).getD false = true
      then some (k.1, k.2, v.name) else none))

/-- The rows above the drain watermark — this transaction's frontier
    (`outbox_rows(session, store, after_id=watermark)`). -/
def GraphState.frontierRows (σ : GraphState) : List Delta :=
  σ.outbox.filter (fun d => σ.watermark < d.id)

/-- The invalidation key set of the round: every frontier row's affected keys
    (coalescing/dedup is irrelevant — reconciles are idempotent). -/
def cascadeKeys (S : Schema) (σ : GraphState) : List (String × String × String) :=
  σ.frontierRows.flatMap (affectedKeys S σ)

/-! ## The logged reconcile pass (decision 3) -/

/-- The `(dt, R, on)` key a job settles. -/
def W3cJob.key (j : W3cJob) : String × String × String := (j.dt, j.R, j.on)

/-- Apply one W3d job — the DIFFING pass (decision 7; shapes fixed to the schema's
    declared `wildcardShapes`). -/
def W3cJob.applyD (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) : GraphState :=
  σ.reconcileStarsKeyD T j.dt j.on j.R j.e (wildcardShapes S) j.cands j.negCands
    j.uposCands

/-- Run a batch of unlogged diffing jobs left-to-right. -/
def reconcileJobsD (S : Schema) (T : Store) (σ0 : GraphState) (jobs : List W3cJob) :
    GraphState :=
  jobs.foldl (W3cJob.applyD S T) σ0

/-- One diffing reconcile pass plus its coalesced processor emission: a single row at
    the derived key (all the pass's per-flip rows — adds AND removes — share that
    object end; the R-node is terminal on the fragment). -/
def W3cJob.applyLogged (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    GraphState :=
  (j.applyD S T σ).pushDelta (objNode ⟨j.dt, j.on⟩ j.R) j.R

/-- Run a batch of logged reconcile jobs left-to-right (`run_cascade`'s per-round
    key loop; one-stratum, so ordering is irrelevant — operand reads are
    pass-inert). -/
def reconcileJobsL (S : Schema) (T : Store) (σ : GraphState) (jobs : List W3cJob) :
    GraphState :=
  jobs.foldl (W3cJob.applyLogged S T) σ

/-- A logged job batch's core is the unlogged `reconcileJobsD` batch — all per-pass
    facts about the diffing batch transfer. -/
theorem reconcileJobsL_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (S : Schema)
    (T : Store) (jobs : List W3cJob) :
    EvalEq (reconcileJobsL S T σ' jobs) (reconcileJobsD S T σ jobs) := by
  unfold reconcileJobsL reconcileJobsD
  induction jobs generalizing σ' σ with
  | nil => exact h
  | cons j rest ih =>
    simp only [List.foldl_cons]
    refine ih ?_
    have happ : EvalEq (j.applyD S T σ') (j.applyD S T σ) :=
      reconcileStarsKeyD_evalEq h T j.dt j.on j.R j.e (wildcardShapes S)
        j.cands j.negCands j.uposCands
    exact ⟨happ.schema, happ.edges, happ.nodes, happ.residue⟩

/-! ### Outbox/watermark bookkeeping of the logged batch -/

/-- One unlogged diffing pass never touches the outbox. -/
theorem W3cJob.applyD_outbox (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    (j.applyD S T σ).outbox = σ.outbox := by
  unfold W3cJob.applyD GraphState.reconcileStarsKeyD
  rw [reconcileKeyD_outbox, reconcileResidueKey_outbox]

/-- One unlogged diffing pass never touches the watermark. -/
theorem W3cJob.applyD_watermark (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    (j.applyD S T σ).watermark = σ.watermark := by
  unfold W3cJob.applyD GraphState.reconcileStarsKeyD
  rw [reconcileKeyD_watermark, reconcileResidueKey_watermark]

/-- One unlogged diffing pass keeps the fresh-id source fixed. -/
theorem W3cJob.applyD_nextDeltaId (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    (j.applyD S T σ).nextDeltaId = σ.nextDeltaId := by
  unfold GraphState.nextDeltaId GraphState.maxOutboxId
  rw [W3cJob.applyD_outbox, W3cJob.applyD_watermark]

/-- The logged batch leaves the watermark untouched (the drain advance is
    `runCascade`'s final act, not the passes'). -/
theorem reconcileJobsL_watermark (S : Schema) (T : Store) :
    ∀ (jobs : List W3cJob) (σ : GraphState),
      (reconcileJobsL S T σ jobs).watermark = σ.watermark := by
  intro jobs
  induction jobs with
  | nil => intro σ; rfl
  | cons j rest ih =>
    intro σ
    have hfold : reconcileJobsL S T σ (j :: rest)
        = reconcileJobsL S T (j.applyLogged S T σ) rest := by
      unfold reconcileJobsL
      rw [List.foldl_cons]
    rw [hfold, ih]
    unfold W3cJob.applyLogged
    rw [pushDelta_watermark, W3cJob.applyD_watermark]

/-- **Outbox soundness of the logged batch**: every row is an original row or a
    pass-emitted row — at some job's derived key, with an id strictly above the
    pre-batch frontier `max maxOutboxId watermark`. -/
theorem reconcileJobsL_outbox_sound (S : Schema) (T : Store) :
    ∀ (jobs : List W3cJob) (σ : GraphState), ∀ d ∈ (reconcileJobsL S T σ jobs).outbox,
      d ∈ σ.outbox ∨
      ((∃ j ∈ jobs, d.node = objNode ⟨j.dt, j.on⟩ j.R ∧ d.relation = j.R ∧ d.leaf = false) ∧
        max σ.maxOutboxId σ.watermark < d.id) := by
  intro jobs
  induction jobs with
  | nil => intro σ d hd; exact Or.inl hd
  | cons j rest ih =>
    intro σ d hd
    have hfold : reconcileJobsL S T σ (j :: rest)
        = reconcileJobsL S T (j.applyLogged S T σ) rest := by
      unfold reconcileJobsL
      rw [List.foldl_cons]
    rw [hfold] at hd
    have hout1 : (j.applyLogged S T σ).outbox
        = ⟨σ.nextDeltaId, objNode ⟨j.dt, j.on⟩ j.R, j.R, false⟩ :: σ.outbox := by
      unfold W3cJob.applyLogged
      rw [pushDelta_outbox, W3cJob.applyD_outbox]
      have := W3cJob.applyD_nextDeltaId S T σ j
      rw [this]
    have hwm1 : (j.applyLogged S T σ).watermark = σ.watermark := by
      unfold W3cJob.applyLogged
      rw [pushDelta_watermark, W3cJob.applyD_watermark]
    have hmax1 : (j.applyLogged S T σ).maxOutboxId = σ.nextDeltaId := by
      unfold W3cJob.applyLogged
      rw [pushDelta_maxOutboxId, W3cJob.applyD_nextDeltaId]
    rcases ih (j.applyLogged S T σ) d hd with hin | ⟨⟨j', hj', hn, hr, hl⟩, hgt⟩
    · rw [hout1] at hin
      rcases List.mem_cons.mp hin with rfl | hmem
      · refine Or.inr ⟨⟨j, List.mem_cons_self, rfl, rfl, rfl⟩, ?_⟩
        show max σ.maxOutboxId σ.watermark < σ.nextDeltaId
        have : σ.nextDeltaId = max σ.maxOutboxId σ.watermark + 1 := rfl
        omega
      · exact Or.inl hmem
    · refine Or.inr ⟨⟨j', List.mem_cons_of_mem _ hj', hn, hr, hl⟩, ?_⟩
      rw [hmax1, hwm1] at hgt
      have : σ.nextDeltaId = max σ.maxOutboxId σ.watermark + 1 := rfl
      omega

/-! ## The drain loop (decision 5) -/

/-- **`runCascade`** (`run_cascade`, `processor.py:694-740`, one-stratum): reconcile
    the batch, then Python's final quiescence check — the rows above the round
    frontier must map to NO keys, else `InvariantViolation` aborts the transaction.
    The abort is modeled as the reject branch (state unchanged); on accept the
    watermark advances past everything, which the next transaction's frontier read
    (`advance_index` re-reads `outbox_watermark`) makes faithful. -/
def runCascade (S : Schema) (T : Store) (σ : GraphState) (jobs : List W3cJob) :
    GraphState :=
  if ((reconcileJobsL S T σ jobs).outbox.filter
        (fun d => max σ.maxOutboxId σ.watermark < d.id)).all
      (fun d => (affectedKeys S (reconcileJobsL S T σ jobs) d).isEmpty)
  then { reconcileJobsL S T σ jobs with watermark := (reconcileJobsL S T σ jobs).maxOutboxId }
  else σ

/-! ## The W3d closure — interleaved logged writes and cascades -/

/-- **`ReachedByW3d σ S T`** — the interleaved scheduler closure: admitted logged
    rule-routed writes and cascade runs, in ANY order (Python: each write
    transaction runs its own in-transaction cascade; `build_index` batches many
    writes before one backfill). The jobs of a cascade leg must cover exactly the
    frontier's affected keys (`_map_deltas_to_keys` + the per-key reconcile loop):
    every cascade key has a job, every job settles a cascade key. -/
inductive ReachedByW3d : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByW3d (emptyState S) S []
  | write {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hadm : FoldAdmits σ (rewriteClosure S t))
      (hprev : ReachedByW3d σ S T) :
      ReachedByW3d (σ.writeLoggedRules S t) S (t :: T)
  | cascade {σ : GraphState} {S : Schema} {T : Store} (jobs : List W3cJob)
      (hjv : ∀ j ∈ jobs, W3cJobValid S j)
      (hcover : ∀ k ∈ cascadeKeys S σ, ∃ j ∈ jobs, j.key = k)
      (hscope : ∀ j ∈ jobs, j.key ∈ cascadeKeys S σ)
      (hprev : ReachedByW3d σ S T) :
      ReachedByW3d (runCascade S T σ jobs) S T

/-! ## Edge soundness and R-node terminality over the interleaved closure -/

/-- Every edge of an unlogged diffing batch is an old edge or a candidate's derived
    edge onto the job's own R-node (removal only shrinks; NB old edges need NOT
    survive — the stale-edge retraction). -/
theorem reconcileJobsD_edge_sound {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState) (a b : NodeKey),
      (a, b) ∈ (reconcileJobsD S T σ jobs).edges →
      (a, b) ∈ σ.edges ∨
        ∃ j ∈ jobs, ∃ c ∈ j.cands, a = subjNode c ∧ b = objNode ⟨j.dt, j.on⟩ j.R := by
  intro jobs
  induction jobs with
  | nil => intro σ a b h; exact Or.inl h
  | cons j rest ih =>
    intro σ a b h
    have hfold : reconcileJobsD S T σ (j :: rest)
        = reconcileJobsD S T (j.applyD S T σ) rest := by
      unfold reconcileJobsD
      rw [List.foldl_cons]
    rw [hfold] at h
    rcases ih _ a b h with hin | ⟨j', hj', c, hc, h1, h2⟩
    · unfold W3cJob.applyD at hin
      rcases reconcileStarsKeyD_edge_sound T j.dt j.on j.R j.e (wildcardShapes S)
        j.cands j.negCands j.uposCands σ a b hin with hold | ⟨c, hc, h1, h2⟩
      · exact Or.inl hold
      · exact Or.inr ⟨j, List.mem_cons_self, c, hc, h1, h2⟩
    · exact Or.inr ⟨j', List.mem_cons_of_mem _ hj', c, hc, h1, h2⟩

/-- **No W3d edge is sourced at an `R`-userset node** (the interleaved analog of
    `reachedByW3a_edge_source_ne_R`): a logged write's edge sources are rewrite-
    closure subjects (predicate ≠ `R` by `NoTtuTarget` + `NoStoreSubjectR`), a
    cascade's edge sources are bare candidates (`BARE ≠ R`). The store hypothesis is
    taken at the chain's own store and weakens along the prefix. -/
theorem reachedByW3d_edge_source_ne_R {σ : GraphState} {S : Schema} {T : Store}
    {R : String} (hRne : R ≠ BARE) (h : ReachedByW3d σ S T) :
    NoTtuTarget S R → NoStoreSubjectR T R → ∀ a b, (a, b) ∈ σ.edges → a.pred ≠ R := by
  induction h with
  | empty S =>
    intro _ _ a b hab
    simp [emptyState] at hab
  | @write σp S T t hadm hprev ih =>
    intro hnt hns a b hab
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hab
    unfold GraphState.writeRules at hab
    rcases foldl_writeDirect_edges_sound (rewriteClosure S t) hab with hin | ⟨u, hu, h1, _⟩
    · exact ih hnt (fun t' ht' => hns t' (List.mem_cons_of_mem _ ht')) a b hin
    · rw [h1, subjNode_pred]
      exact rewriteClosure_subject_pred_ne hnt (hns t List.mem_cons_self) hu
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    intro hnt hns a b hab
    unfold runCascade at hab
    split at hab
    · have hab' : (a, b) ∈ (reconcileJobsL S T σp jobs).edges := hab
      rw [(reconcileJobsL_evalEq (EvalEq.refl σp) S T jobs).edges] at hab'
      rcases reconcileJobsD_edge_sound jobs σp a b hab' with hold | ⟨j, hj, c, hc, h1, _⟩
      · exact ih hnt hns a b hold
      · rw [h1, subjNode_pred]
        obtain ⟨_, hcb, _⟩ := hjv j hj
        rw [hcb c hc]
        exact Ne.symm hRne
    · exact ih hnt hns a b hab

/-- **The derived R-node is never an edge source on a W3d state.** -/
theorem reachedByW3d_Rnode_not_source {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hRne : R ≠ BARE) (hder : isDerived S (dt, R) = true) (h : ReachedByW3d σ S T) :
    ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges := by
  obtain ⟨hnt, hns⟩ := hterm dt R hder
  intro y hy
  exact reachedByW3d_edge_source_ne_R hRne h hnt hns _ y hy (objNode_pred ⟨dt, on⟩ R)

/-- R-node terminality survives the batch itself (the mid-cascade state the leftover
    check reads): a batch edge's source is a bare candidate, never an R-node. -/
theorem reconcileJobsL_Rnode_not_source {σ : GraphState} {S : Schema} {T : Store}
    {jobs : List W3cJob} {dt on R : String}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hRne : R ≠ BARE) (hder : isDerived S (dt, R) = true) (h : ReachedByW3d σ S T)
    (hjv : ∀ j ∈ jobs, W3cJobValid S j) :
    ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ (reconcileJobsL S T σ jobs).edges := by
  intro y hy
  rw [(reconcileJobsL_evalEq (EvalEq.refl σ) S T jobs).edges] at hy
  rcases reconcileJobsD_edge_sound jobs σ _ y hy with hold | ⟨j, hj, c, hc, h1, _⟩
  · exact reachedByW3d_Rnode_not_source hterm hRne hder h y hold
  · obtain ⟨_, hcb, _⟩ := hjv j hj
    have hpred : (objNode ⟨dt, on⟩ R).pred = BARE := by
      rw [h1, subjNode_pred, hcb c hc]
    rw [objNode_pred] at hpred
    exact hRne hpred

/-! ## T5 — the reject branch never fires; the drain is justified -/

/-- **`runCascade_no_abort` (T5 half a).** On the fragment the leftover check always
    passes: every row above the round frontier is a pass-emitted row at a derived
    R-node, whose reach cone is empty (terminality) and whose own predicate is
    derived — hence not a computed operand of any derived def (`hLU`) — so it maps
    to no keys. Python's `InvariantViolation` (`processor.py:736-739`) is dead code
    at one stratum. -/
theorem runCascade_no_abort {σ : GraphState} {S : Schema} {T : Store}
    {jobs : List W3cJob}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hjv : ∀ j ∈ jobs, W3cJobValid S j) (h : ReachedByW3d σ S T) :
    runCascade S T σ jobs
      = { reconcileJobsL S T σ jobs with
          watermark := (reconcileJobsL S T σ jobs).maxOutboxId } := by
  unfold runCascade
  refine if_pos ?_
  rw [List.all_eq_true]
  intro d hd
  obtain ⟨hdmem, hdgt⟩ := List.mem_filter.mp hd
  have hdgt' : max σ.maxOutboxId σ.watermark < d.id := of_decide_eq_true hdgt
  rcases reconcileJobsL_outbox_sound S T jobs σ d hdmem
    with hold | ⟨⟨j, hj, hnode, hrel, hleaf⟩, _⟩
  · -- an original row sits at or below the frontier — it cannot be in the filter
    exfalso
    have := mem_outbox_le_maxOutboxId σ d hold
    omega
  · -- a pass-emitted row: maps to no keys
    obtain ⟨hRne, _hcb, _hcS, _hnS, _huP, _huS, hder, _hlke, hon⟩ := hjv j hj
    -- the reach cone of the R-node is empty
    have hRns := reconcileJobsL_Rnode_not_source (on := j.on) hterm hRne hder h hjv
    have hreach : ∀ v, (reconcileJobsL S T σ jobs).reach d.node v = false := by
      intro v
      by_contra hne
      have htrue : (reconcileJobsL S T σ jobs).reach d.node v = true := by
        revert hne
        cases (reconcileJobsL S T σ jobs).reach d.node v <;> simp
      obtain ⟨y, hy⟩ := nreaches_first_edge (reach_sound htrue)
      rw [hnode] at hy
      exact hRns y hy
    have hobj : (reconcileJobsL S T σ jobs).affectedObjects d = [d.node] := by
      unfold GraphState.affectedObjects
      rw [List.filter_eq_nil_iff.mpr (fun v _ => by rw [hreach v]; exact Bool.false_ne_true)]
    -- the single candidate object is the derived R-node: no derived def reads a
    -- derived predicate as a computed operand (`hLU`), so no key is emitted
    have htype : d.node.type = j.dt := by rw [hnode, objNode_type]
    have hpred : d.node.pred = j.R := by rw [hnode, objNode_pred]
    have hkeys : affectedKeys S (reconcileJobsL S T σ jobs) d = [] := by
      unfold affectedKeys
      rw [hobj]
      have hleaf_ne : ¬(d.leaf = true ∧ d.node.name ≠ STAR ∧
          isDerived S (d.node.type, d.node.pred) = true) := by rw [hleaf]; simp
      rw [if_neg hleaf_ne, List.nil_append]
      simp only [List.flatMap_cons, List.flatMap_nil, List.append_nil]
      by_cases hst : d.node.name = STAR
      · rw [if_pos hst]
      · rw [if_neg hst]
        rw [List.filterMap_eq_nil_iff]
        intro k hk
        have hcond : ¬(k.1 = d.node.type ∧ isDerived S k = true ∧
            ((S.lookup k).map
              (fun e => (computedRefs e).contains d.node.pred)).getD false = true) := by
          rintro ⟨hk1, hkder, hkref⟩
          cases hlk : S.lookup k with
          | none => rw [hlk] at hkref; simp at hkref
          | some e =>
            rw [hlk] at hkref
            simp only [Option.map_some, Option.getD_some] at hkref
            have hmem : d.node.pred ∈ computedRefs e := by
              rw [List.contains_eq_mem] at hkref
              exact of_decide_eq_true hkref
            have hfalse := hLU k.1 k.2 e hlk hkder _ hmem
            rw [hk1, htype, hpred] at hfalse
            cases hder.symm.trans hfalse
        rw [if_neg hcond]
    rw [hkeys]
    rfl

/-- **`cascade_drains` (T5 half b).** After a cascade run on the fragment the state
    is `Quiescent` — every outbox row sits at or below the advanced watermark.
    Contentful: a non-empty pre-cascade frontier (un-drained user-write rows) IS
    drained, and the watermark advance is JUSTIFIED by `runCascade_no_abort` (the
    skipped rows provably map to no keys), never asserted — the fix for the old
    vacuous `cascade_converges` shape. -/
theorem cascade_drains {σ : GraphState} {S : Schema} {T : Store} {jobs : List W3cJob}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hjv : ∀ j ∈ jobs, W3cJobValid S j) (h : ReachedByW3d σ S T) :
    Quiescent (runCascade S T σ jobs) := by
  rw [runCascade_no_abort hterm hLU hjv h]
  intro d hd
  exact mem_outbox_le_maxOutboxId _ d hd

end Zanzibar
