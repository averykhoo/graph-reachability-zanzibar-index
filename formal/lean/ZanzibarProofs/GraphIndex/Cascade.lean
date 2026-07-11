import ZanzibarProofs.GraphIndex.ReconcileStarsComplete

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
   branches are out of fragment by `hterm`/`hRootB`). The subject-level cheap path is
   NOT modeled (the model always full-object reconciles — Python's general path; the
   cheap path is an optimization with its own §5.4 escalations to full).
5. **The loop** at one stratum: one round, then the leftover check as the
   accept/reject branch of `runCascade`.
6. **Add-only**: no removes; the remove-side hazards (operand-removal re-reconcile,
   `neg` pruning after node GC) are out of scope for W3d-1.

The W3c read-correspondence transfer (via `EvalEq` + the W3d analog of the coverage
clauses) is W3d-1b/1c — see ROADMAP.

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
    transaction; the autoincrement id is the cursor). -/
def GraphState.pushDelta (σ : GraphState) (k : NodeKey) (r : String) : GraphState :=
  { σ with outbox := ⟨σ.nextDeltaId, k, r⟩ :: σ.outbox }

@[simp] theorem pushDelta_schema (σ : GraphState) (k : NodeKey) (r : String) :
    (σ.pushDelta k r).schema = σ.schema := rfl
@[simp] theorem pushDelta_edges (σ : GraphState) (k : NodeKey) (r : String) :
    (σ.pushDelta k r).edges = σ.edges := rfl
@[simp] theorem pushDelta_nodes (σ : GraphState) (k : NodeKey) (r : String) :
    (σ.pushDelta k r).nodes = σ.nodes := rfl
@[simp] theorem pushDelta_residue (σ : GraphState) (k : NodeKey) (r : String) :
    (σ.pushDelta k r).residue = σ.residue := rfl
@[simp] theorem pushDelta_watermark (σ : GraphState) (k : NodeKey) (r : String) :
    (σ.pushDelta k r).watermark = σ.watermark := rfl
@[simp] theorem pushDelta_outbox (σ : GraphState) (k : NodeKey) (r : String) :
    (σ.pushDelta k r).outbox = ⟨σ.nextDeltaId, k, r⟩ :: σ.outbox := rfl

/-- Pushing a row moves `maxOutboxId` to exactly the fresh id. -/
theorem pushDelta_maxOutboxId (σ : GraphState) (k : NodeKey) (r : String) :
    (σ.pushDelta k r).maxOutboxId = σ.nextDeltaId := by
  show (⟨σ.nextDeltaId, k, r⟩ :: σ.outbox).foldl (fun m d => max m d.id) 0
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
  then (σ.writeDirect t).pushDelta (objNode t.object t.relation) t.relation
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

/-- The covered-guarded edge fold is `EvalEq`-congruent. -/
theorem reconcileKeyC_evalEq (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) {σ' σ : GraphState}, EvalEq σ' σ →
      EvalEq (σ'.reconcileKeyC T dt on R e cands) (σ.reconcileKeyC T dt on R e cands) := by
  intro cands
  induction cands with
  | nil => intro σ' σ h; exact h
  | cons c rest ih =>
    intro σ' σ h
    have hstep' : σ'.reconcileKeyC T dt on R e (c :: rest)
        = (if σ'.checkFn T c dt on R e
              && !(σ'.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)
           then σ'.writeDirect ⟨c, R, ⟨dt, on⟩⟩ else σ').reconcileKeyC T dt on R e rest := by
      unfold GraphState.reconcileKeyC
      rw [List.foldl_cons]
    have hstep : σ.reconcileKeyC T dt on R e (c :: rest)
        = (if σ.checkFn T c dt on R e
              && !(σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)
           then σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩ else σ).reconcileKeyC T dt on R e rest := by
      unfold GraphState.reconcileKeyC
      rw [List.foldl_cons]
    rw [hstep', hstep, checkFn_congr h.edges h.nodes T c dt on R e,
      coveredAt_congr h.residue]
    split
    · exact ih (writeDirect_evalEq h ⟨c, R, ⟨dt, on⟩⟩)
    · exact ih h

/-- **The combined star pass is `EvalEq`-congruent.** -/
theorem reconcileStarsKey_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef) :
    EvalEq (σ'.reconcileStarsKey T dt on R e shapes cands negCands uposCands)
      (σ.reconcileStarsKey T dt on R e shapes cands negCands uposCands) := by
  unfold GraphState.reconcileStarsKey
  exact reconcileKeyC_evalEq T dt on R e cands
    (reconcileResidueKey_evalEq h T dt on R e shapes negCands uposCands)

/-! ## The delta → key mapping (decision 4) -/

/-- Candidate object nodes of one delta: the row's own object node plus its
    cascade-time reach cone — the model-level reconstruction of the per-flip rows'
    denormalized object ends (`{y : b ⇝ y}`, decision 1). -/
def GraphState.affectedObjects (σ : GraphState) (d : Delta) : List NodeKey :=
  d.node :: σ.nodes.filter (fun v => σ.reach d.node v)

/-- **The delta → derived-key mapping** (`_map_deltas_to_keys` LeafFamily branch +
    `_fan_out` `via='computed'`, fragment-restricted): a candidate object node `v`
    (concrete — derived keys are never star-named, `processor.py:604-605`) dirties
    every declared derived key `(v.type, R)` whose def reads `v.pred` as a computed
    operand, at object `v.name`. Keys are `(dt, R, on)` triples. -/
def affectedKeys (S : Schema) (σ : GraphState) (d : Delta) :
    List (String × String × String) :=
  (σ.affectedObjects d).flatMap (fun v =>
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

/-- One reconcile pass plus its coalesced processor emission: a single row at the
    derived key (all the pass's per-flip rows share that object end — the R-node is
    terminal on the fragment). -/
def W3cJob.applyLogged (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    GraphState :=
  (j.apply S T σ).pushDelta (objNode ⟨j.dt, j.on⟩ j.R) j.R

/-- Run a batch of logged reconcile jobs left-to-right (`run_cascade`'s per-round
    key loop; one-stratum, so ordering is irrelevant — operand reads are
    pass-inert). -/
def reconcileJobsL (S : Schema) (T : Store) (σ : GraphState) (jobs : List W3cJob) :
    GraphState :=
  jobs.foldl (W3cJob.applyLogged S T) σ

/-- A logged job batch's core is the unlogged `reconcileJobsC` batch — all W3c
    per-pass facts transfer. -/
theorem reconcileJobsL_evalEq {σ' σ : GraphState} (h : EvalEq σ' σ) (S : Schema)
    (T : Store) (jobs : List W3cJob) :
    EvalEq (reconcileJobsL S T σ' jobs) (reconcileJobsC S T σ jobs) := by
  unfold reconcileJobsL reconcileJobsC
  induction jobs generalizing σ' σ with
  | nil => exact h
  | cons j rest ih =>
    simp only [List.foldl_cons]
    refine ih ?_
    have happ : EvalEq (j.apply S T σ') (j.apply S T σ) :=
      reconcileStarsKey_evalEq h T j.dt j.on j.R j.e (wildcardShapes S)
        j.cands j.negCands j.uposCands
    exact ⟨happ.schema, happ.edges, happ.nodes, happ.residue⟩

/-! ### Outbox/watermark bookkeeping of the logged batch -/

/-- The covered-guarded edge fold never touches the outbox. -/
theorem reconcileKeyC_outbox (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKeyC T dt on R e cands).outbox = σ.outbox := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    have hstep : σ.reconcileKeyC T dt on R e (c :: rest)
        = (if σ.checkFn T c dt on R e
              && !(σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)
           then σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩ else σ).reconcileKeyC T dt on R e rest := by
      unfold GraphState.reconcileKeyC
      rw [List.foldl_cons]
    rw [hstep, ih]
    split
    · exact writeDirect_outbox σ _
    · rfl

/-- The covered-guarded edge fold never touches the watermark. -/
theorem reconcileKeyC_watermark (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKeyC T dt on R e cands).watermark = σ.watermark := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    have hstep : σ.reconcileKeyC T dt on R e (c :: rest)
        = (if σ.checkFn T c dt on R e
              && !(σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)
           then σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩ else σ).reconcileKeyC T dt on R e rest := by
      unfold GraphState.reconcileKeyC
      rw [List.foldl_cons]
    rw [hstep, ih]
    split
    · exact writeDirect_watermark σ _
    · rfl

/-- One unlogged pass never touches the outbox. -/
theorem W3cJob.apply_outbox (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    (j.apply S T σ).outbox = σ.outbox := by
  unfold W3cJob.apply GraphState.reconcileStarsKey
  rw [reconcileKeyC_outbox, reconcileResidueKey_outbox]

/-- One unlogged pass never touches the watermark. -/
theorem W3cJob.apply_watermark (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    (j.apply S T σ).watermark = σ.watermark := by
  unfold W3cJob.apply GraphState.reconcileStarsKey
  rw [reconcileKeyC_watermark, reconcileResidueKey_watermark]

/-- One unlogged pass keeps the fresh-id source fixed. -/
theorem W3cJob.apply_nextDeltaId (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    (j.apply S T σ).nextDeltaId = σ.nextDeltaId := by
  unfold GraphState.nextDeltaId GraphState.maxOutboxId
  rw [W3cJob.apply_outbox, W3cJob.apply_watermark]

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
    rw [pushDelta_watermark, W3cJob.apply_watermark]

/-- **Outbox soundness of the logged batch**: every row is an original row or a
    pass-emitted row — at some job's derived key, with an id strictly above the
    pre-batch frontier `max maxOutboxId watermark`. -/
theorem reconcileJobsL_outbox_sound (S : Schema) (T : Store) :
    ∀ (jobs : List W3cJob) (σ : GraphState), ∀ d ∈ (reconcileJobsL S T σ jobs).outbox,
      d ∈ σ.outbox ∨
      ((∃ j ∈ jobs, d.node = objNode ⟨j.dt, j.on⟩ j.R ∧ d.relation = j.R) ∧
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
        = ⟨σ.nextDeltaId, objNode ⟨j.dt, j.on⟩ j.R, j.R⟩ :: σ.outbox := by
      unfold W3cJob.applyLogged
      rw [pushDelta_outbox, W3cJob.apply_outbox]
      have := W3cJob.apply_nextDeltaId S T σ j
      rw [this]
    have hwm1 : (j.applyLogged S T σ).watermark = σ.watermark := by
      unfold W3cJob.applyLogged
      rw [pushDelta_watermark, W3cJob.apply_watermark]
    have hmax1 : (j.applyLogged S T σ).maxOutboxId = σ.nextDeltaId := by
      unfold W3cJob.applyLogged
      rw [pushDelta_maxOutboxId, W3cJob.apply_nextDeltaId]
    rcases ih (j.applyLogged S T σ) d hd with hin | ⟨⟨j', hj', hn, hr⟩, hgt⟩
    · rw [hout1] at hin
      rcases List.mem_cons.mp hin with rfl | hmem
      · refine Or.inr ⟨⟨j, List.mem_cons_self, rfl, rfl⟩, ?_⟩
        show max σ.maxOutboxId σ.watermark < σ.nextDeltaId
        have : σ.nextDeltaId = max σ.maxOutboxId σ.watermark + 1 := rfl
        omega
      · exact Or.inl hmem
    · refine Or.inr ⟨⟨j', List.mem_cons_of_mem _ hj', hn, hr⟩, ?_⟩
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

/-- Every edge added by an unlogged job batch is a candidate's derived edge onto the
    job's own R-node. -/
theorem reconcileJobsC_edge_sound {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState) (a b : NodeKey),
      (a, b) ∈ (reconcileJobsC S T σ jobs).edges →
      (a, b) ∈ σ.edges ∨
        ∃ j ∈ jobs, ∃ c ∈ j.cands, a = subjNode c ∧ b = objNode ⟨j.dt, j.on⟩ j.R := by
  intro jobs
  induction jobs with
  | nil => intro σ a b h; exact Or.inl h
  | cons j rest ih =>
    intro σ a b h
    have hfold : reconcileJobsC S T σ (j :: rest)
        = reconcileJobsC S T (j.apply S T σ) rest := by
      unfold reconcileJobsC
      rw [List.foldl_cons]
    rw [hfold] at h
    rcases ih _ a b h with hin | ⟨j', hj', c, hc, h1, h2⟩
    · unfold W3cJob.apply GraphState.reconcileStarsKey at hin
      rcases reconcileKeyC_edge_sound T j.dt j.on j.R j.e j.cands a b hin
        with hold | ⟨c, hc, h1, h2, _⟩
      · rw [reconcileResidueKey_edges] at hold
        exact Or.inl hold
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
      rcases reconcileJobsC_edge_sound jobs σp a b hab' with hold | ⟨j, hj, c, hc, h1, _⟩
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
  rcases reconcileJobsC_edge_sound jobs σ _ y hy with hold | ⟨j, hj, c, hc, h1, _⟩
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
    with hold | ⟨⟨j, hj, hnode, hrel⟩, _⟩
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
