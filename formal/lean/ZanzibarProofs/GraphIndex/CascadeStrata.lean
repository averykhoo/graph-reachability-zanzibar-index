import ZanzibarProofs.GraphIndex.CascadeEnum

/-!
# W3d-2 opening — the ROUTED leaf dispatch + the two-round scheduler (ROADMAP W3d-2)

Two strata (derived-reading-derived). Model sources:

* **The routed read.** `processor.py:43-70` (`_EvalContext`): an UNTAINTED operand
  leaf dispatches to `leaf_check` = `widx.check` (the plain wildcard-aware closure
  read = `probeNonDerived` on an untainted key), while a DERIVED operand leaf
  dispatches to `derived_check` = `widx._check_derived` (edge probe + residue =
  `probeDerived`). `member_check` (`processor.py:182-188`) states the routing
  explicitly: tainted ⇒ derived read, else plain read. The single routed
  node-recursion `graphRecR` — every leaf reads the graph's own `GraphModel.check`,
  which routes on `isDerived σ.schema` — captures both dispatches at once.
  Star coverage: `derived_stars` (`processor.py:69-70`) returns the operand's stored
  residue `stars`; pointwise shape-membership is exactly `probeDerived` on the star
  subject, so `coveredFnR sh = checkFnR (starSubj sh)` mirrors the compiled
  `stars_fn` fold the same way W3c's `coveredFn` did (boolean spec §7), now routed.

* **The two-round drain.** `run_cascade` (`processor.py:694-740`) runs
  `rounds = len(strata)` rounds; each round reads the frontier rows above the
  running frontier cursor, advances the cursor to the max id read, maps rows to
  keys, and reconciles each key. With two strata a stratum-1 pass EMITS rows that
  map (via the `computed` fan-out) to dependent stratum-2 keys, which round 2
  re-settles. The final quiescence check reads the rows above the last cursor and
  raises on any leftover key (`:729-739`) — the reject branch.

* **Within-round order is NOT load-bearing.** Python sorts a round's keys lower
  stratum first (`:714-719` — "idempotent either way; ordering just avoids
  provably-stale recomputes"). Attack-confirmed (2026-07-12c `#eval`, both orders,
  sync + async batching, cross-stratum union / exclusion / stars / userset-upos):
  fully-drained `check = sem` either way — a stale round-1 recompute of a
  stratum-2 key is re-settled by round 2 because the stratum-1 pass's emission
  re-dirties it. The model therefore leaves batch order free.

* **Mid-drain staleness is REAL** (same `#eval`): after round 1 only, a stratum-2
  key read can disagree with `sem` (`viewer` stale after `editor`'s retraction).
  The W3d-2 read theorem stays scoped to fully-drained states, exactly like
  W3d-1's, and the settledness invariant must become stratum-staged.

**Conservativity (this file's theorems):** on defs whose `computed` operands are all
untainted (the W3d-1 `hLU` fragment), the routed read IS the W3d read —
`checkFnR = checkFn` (`checkFnR_eq_checkFn`), and the routed diffing pass / logged
batch collapse to their W3d counterparts (`reconcileStarsKeyDR_eq`,
`reconcileJobsLR_eq`). W3d-2 is a strict extension of W3d-1: everything proved over
the unrouted scheduler is the single-stratum image of this one.

**Candidate enumeration note (for the W3d-2 E-chain tail):** Python's per-pass audit
at a derived-reading key pulls, besides the leaf concretes and edge holders, the
operand residues' `neg` ids (`_derived_leaf_neg_ids`, `processor.py:461-495` —
"exclusions recorded in lower-strata residues must surface as candidates") and the
old `upos` ids (`:425-429`). A W3d-2 `enumJobs` must extend `leafConcretes`
accordingly: a lower-stratum `neg`/`upos` member is edge-free (I6) and invisible to
reach-probe enumeration.
-/

namespace Zanzibar

namespace GraphModel

/-- **Routing, made pointwise.** `check` on an untainted key IS the plain ≤4-probe
    read (`wildcard.py` check routing; `member_check`, `processor.py:186-188`). -/
theorem check_untainted (σ : GraphState) (q : Query)
    (h : isDerived σ.schema (q.object.type, q.relation) = false) :
    check σ q = probeNonDerived σ q := by
  unfold check
  rw [h]
  simp

/-- `check` on a derived key is the derived read path (edge probe + residue). -/
theorem check_derived (σ : GraphState) (q : Query)
    (h : isDerived σ.schema (q.object.type, q.relation) = true) :
    check σ q = probeDerived σ q := by
  unfold check
  rw [h]
  simp

/-- **The ROUTED node-recursion for `check_fn`** (the W3d-2 model extension):
    every operand leaf reads the graph's own `check`, which routes an untainted
    key to `probeNonDerived` (= `leaf_check` → `widx.check`, `processor.py:54-56`)
    and a derived key to `probeDerived` (= `derived_check` → `widx._check_derived`,
    `processor.py:66-67, 173-180`). -/
def graphRecR (σ : GraphState) (s : SubjectRef) : Rec :=
  fun ot on' r' => check σ ⟨s, r', ⟨ot, on'⟩⟩

/-- On an untainted operand key the routed recursion is W3a's `graphRec`. -/
theorem graphRecR_eq_graphRec {σ : GraphState} (s : SubjectRef) {dt : String}
    (on : String) {r' : String} (h : isDerived σ.schema (dt, r') = false) :
    graphRecR σ s dt on r' = graphRec σ s dt on r' :=
  check_untainted σ ⟨s, r', ⟨dt, on⟩⟩ h

end GraphModel

/-- **The routed compiled `check_fn`.** `evalE` with the routed node-recursion —
    faithful to `reconcile`'s per-subject boolean evaluation once derived operands
    are allowed (`plan.check_fn` dispatching through `_EvalContext`). -/
def GraphState.checkFnR (σ : GraphState) (T : Store) (s : SubjectRef)
    (dt on R : String) (e : Expr) : Bool :=
  evalE (GraphModel.graphRecR σ s) s T ⟨s, R, ⟨dt, on⟩⟩ dt on R e

/-- **Conservativity of the routed read**: on a computed-only def whose operands
    are all UNTAINTED (the W3d-1 `hLU` fragment), `checkFnR = checkFn` — the leaf
    reads agree pointwise (`graphRecR_eq_graphRec`), and `evalE_computedOnly`
    transports the whole tree. -/
theorem checkFnR_eq_checkFn (σ : GraphState) (T : Store) (s : SubjectRef)
    (dt on R : String) (e : Expr) (hco : ComputedOnly e)
    (hLU : ∀ r' ∈ computedRefs e, isDerived σ.schema (dt, r') = false) :
    σ.checkFnR T s dt on R e = σ.checkFn T s dt on R e :=
  evalE_computedOnly e hco
    (fun r' hr' => GraphModel.graphRecR_eq_graphRec s on (hLU r' hr'))

/-- Routed star coverage of one shape — the pointwise `stars_fn` with routed leaves
    (`leaf_stars` on untainted leaves, `derived_stars` = the operand residue's
    stored `stars` on derived leaves — `processor.py:58-62, 69-70`). -/
def GraphState.coveredFnR (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (sh : Shape) : Bool :=
  σ.checkFnR T (starSubj sh) dt on R e

/-- Routed coverage collapses to W3c's `coveredFn` on untainted-operand defs. -/
theorem coveredFnR_eq_coveredFn (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (sh : Shape) (hco : ComputedOnly e)
    (hLU : ∀ r' ∈ computedRefs e, isDerived σ.schema (dt, r') = false) :
    σ.coveredFnR T dt on R e sh = σ.coveredFn T dt on R e sh :=
  checkFnR_eq_checkFn σ T (starSubj sh) dt on R e hco hLU

/-! ## Congruence — the routed read consults exactly the `EvalEq` core

`checkFn` needed only edges/nodes (`checkFn_congr`); the ROUTED read additionally
consults the schema (the dispatch) and the residue (`probeDerived`) — i.e. exactly
the four `EvalEq` components. -/

/-- The derived read agrees across edge/node/residue-equal states. -/
theorem probeDerived_congr {σ σ' : GraphState} (he : σ'.edges = σ.edges)
    (hn : σ'.nodes = σ.nodes) (hres : σ'.residue = σ.residue) (q : Query) :
    GraphModel.probeDerived σ' q = GraphModel.probeDerived σ q := by
  unfold GraphModel.probeDerived
  simp only [reach_congr he hn, hres]

/-- The routed `check` agrees across `EvalEq` states. -/
theorem check_evalEq {σ σ' : GraphState} (h : EvalEq σ' σ) (q : Query) :
    GraphModel.check σ' q = GraphModel.check σ q := by
  unfold GraphModel.check
  rw [h.schema]
  split
  · exact probeDerived_congr h.edges h.nodes h.residue q
  · exact probeNonDerived_congr h.edges h.nodes q

/-- The routed node-recursion agrees across `EvalEq` states. -/
theorem graphRecR_evalEq {σ σ' : GraphState} (h : EvalEq σ' σ) (s : SubjectRef) :
    GraphModel.graphRecR σ' s = GraphModel.graphRecR σ s := by
  funext ot on' r'
  exact check_evalEq h _

/-- **`checkFnR` agrees across `EvalEq` states** — the routed compiled boolean reads
    the state only through `graphRecR`. -/
theorem checkFnR_evalEq {σ σ' : GraphState} (h : EvalEq σ' σ) (T : Store)
    (s : SubjectRef) (dt on R : String) (e : Expr) :
    σ'.checkFnR T s dt on R e = σ.checkFnR T s dt on R e := by
  unfold GraphState.checkFnR
  rw [graphRecR_evalEq h s]

/-! ## The routed reconcile pass (wholesale residue recompute + diffing edge audit) -/

/-- The routed wholesale residue recompute — `reconcile` steps 1–3
    (`processor.py:388-446`) with routed guards. Mirrors
    `GraphState.reconcileResidueKey` exactly, `checkFn`/`coveredFn` → routed. -/
def GraphState.reconcileResidueKeyR (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) : GraphState :=
  let stars := shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)
  let neg := negCands.filter (fun c => stars.contains c.shape && !(σ.checkFnR T c dt on R e))
  let upos := uposCands.filter (fun c => !(stars.contains c.shape) && σ.checkFnR T c dt on R e)
  σ.putResidue (objNode ⟨dt, on⟩ R) R ⟨stars, neg, upos⟩

/-- On untainted-operand defs the routed residue recompute IS the W3c one. -/
theorem reconcileResidueKeyR_eq (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef)
    (hco : ComputedOnly e)
    (hLU : ∀ r' ∈ computedRefs e, isDerived σ.schema (dt, r') = false) :
    σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands
      = σ.reconcileResidueKey T dt on R e shapes negCands uposCands := by
  have hcf : ∀ c : SubjectRef, σ.checkFnR T c dt on R e = σ.checkFn T c dt on R e :=
    fun c => checkFnR_eq_checkFn σ T c dt on R e hco hLU
  unfold GraphState.reconcileResidueKeyR GraphState.reconcileResidueKey
  simp only [GraphState.coveredFnR, GraphState.coveredFn, hcf]

@[simp] theorem reconcileResidueKeyR_schema (σ : GraphState) (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands).schema = σ.schema := rfl

/-- The routed diffing edge audit — `reconcile` step 4 → `reconcile_subject`
    (`want = should ∧ ¬covered`; add on want, retract on ¬want,
    `processor.py:359-367`) with the routed guard. -/
def GraphState.reconcileKeyDR (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (cands : List SubjectRef) : GraphState :=
  cands.foldl (fun acc c =>
    if acc.checkFnR T c dt on R e && !(acc.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)
    then acc.writeDirect ⟨c, R, ⟨dt, on⟩⟩
    else acc.removeEdgePair (subjNode c) (objNode ⟨dt, on⟩ R)) σ

/-- One-step unfolding of the routed diffing fold. -/
theorem reconcileKeyDR_cons (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (c : SubjectRef) (rest : List SubjectRef) :
    σ.reconcileKeyDR T dt on R e (c :: rest)
      = (if σ.checkFnR T c dt on R e && !(σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)
         then σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩
         else σ.removeEdgePair (subjNode c) (objNode ⟨dt, on⟩ R)).reconcileKeyDR
          T dt on R e rest := by
  unfold GraphState.reconcileKeyDR
  rw [List.foldl_cons]

theorem reconcileKeyDR_schema (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKeyDR T dt on R e cands).schema = σ.schema := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    rw [reconcileKeyDR_cons, ih]
    split
    · exact writeDirect_schema σ _
    · exact removeEdgePair_schema σ _ _

/-- On untainted-operand defs the routed diffing audit IS the W3d one (the guards
    agree at every fold state — the fold never moves the schema). -/
theorem reconcileKeyDR_eq {S : Schema} (T : Store) (dt on R : String) (e : Expr)
    (hco : ComputedOnly e)
    (hLU : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false) :
    ∀ (cands : List SubjectRef) (σ : GraphState), σ.schema = S →
      σ.reconcileKeyDR T dt on R e cands = σ.reconcileKeyD T dt on R e cands := by
  intro cands
  induction cands with
  | nil => intro σ _; rfl
  | cons c rest ih =>
    intro σ hs
    rw [reconcileKeyDR_cons, reconcileKeyD_cons,
      checkFnR_eq_checkFn σ T c dt on R e hco (fun r' hr' => by rw [hs]; exact hLU r' hr')]
    split
    · exact ih _ (by rw [writeDirect_schema, hs])
    · exact ih _ (by rw [removeEdgePair_schema, hs])

/-- The routed full-object pass: residue recompute THEN diffing edge audit
    (Python stores the row at `:446` before auditing edges at `:450-455`). -/
def GraphState.reconcileStarsKeyDR (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (cands negCands uposCands : List SubjectRef) :
    GraphState :=
  (σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands).reconcileKeyDR
    T dt on R e cands

@[simp] theorem reconcileStarsKeyDR_schema (σ : GraphState) (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef) :
    (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands uposCands).schema
      = σ.schema := by
  unfold GraphState.reconcileStarsKeyDR
  rw [reconcileKeyDR_schema, reconcileResidueKeyR_schema]

/-- On untainted-operand defs the routed pass IS the W3d pass. -/
theorem reconcileStarsKeyDR_eq (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (cands negCands uposCands : List SubjectRef)
    (hco : ComputedOnly e)
    (hLU : ∀ r' ∈ computedRefs e, isDerived σ.schema (dt, r') = false) :
    σ.reconcileStarsKeyDR T dt on R e shapes cands negCands uposCands
      = σ.reconcileStarsKeyD T dt on R e shapes cands negCands uposCands := by
  unfold GraphState.reconcileStarsKeyDR GraphState.reconcileStarsKeyD
  rw [reconcileResidueKeyR_eq σ T dt on R e shapes negCands uposCands hco hLU,
    reconcileKeyDR_eq T dt on R e hco hLU cands _ (by simp)]

/-! ## The routed logged job batch -/

/-- Apply one routed W3d job (shapes fixed to the schema's `wildcardShapes`). -/
def W3cJob.applyDR (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) : GraphState :=
  σ.reconcileStarsKeyDR T j.dt j.on j.R j.e (wildcardShapes S) j.cands j.negCands
    j.uposCands

/-- One routed pass plus its coalesced processor emission (a single row at the
    derived key — as in W3d-1a, decision 3). -/
def W3cJob.applyLoggedR (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    GraphState :=
  (j.applyDR S T σ).pushDelta (objNode ⟨j.dt, j.on⟩ j.R) j.R

@[simp] theorem W3cJob.applyLoggedR_schema (S : Schema) (T : Store) (σ : GraphState)
    (j : W3cJob) : (j.applyLoggedR S T σ).schema = σ.schema := by
  unfold W3cJob.applyLoggedR W3cJob.applyDR
  rw [pushDelta_schema, reconcileStarsKeyDR_schema]

/-- Run a batch of routed logged jobs left-to-right (`run_cascade`'s per-round key
    loop; batch order left free — attack-confirmed not load-bearing). -/
def reconcileJobsLR (S : Schema) (T : Store) (σ : GraphState) (jobs : List W3cJob) :
    GraphState :=
  jobs.foldl (W3cJob.applyLoggedR S T) σ

theorem reconcileJobsLR_schema (S : Schema) (T : Store) :
    ∀ (jobs : List W3cJob) (σ : GraphState),
      (reconcileJobsLR S T σ jobs).schema = σ.schema := by
  intro jobs
  induction jobs with
  | nil => intro σ; rfl
  | cons j rest ih =>
    intro σ
    show (reconcileJobsLR S T (j.applyLoggedR S T σ) rest).schema = σ.schema
    rw [ih, W3cJob.applyLoggedR_schema]

/-- **Batch conservativity**: under the W3d-1 schema-level `hCO`/`hLU` (every
    derived def computed-only with untainted operands), a routed logged batch of
    VALID jobs is the W3d logged batch — the whole W3d-1 development is the
    single-stratum image of the routed scheduler. -/
theorem reconcileJobsLR_eq {S : Schema} (T : Store)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false) :
    ∀ (jobs : List W3cJob) (σ : GraphState), σ.schema = S →
      (∀ j ∈ jobs, W3cJobValid S j) →
      reconcileJobsLR S T σ jobs = reconcileJobsL S T σ jobs := by
  intro jobs
  induction jobs with
  | nil => intro σ _ _; rfl
  | cons j rest ih =>
    intro σ hs hjv
    obtain ⟨_, _, _, _, _, _, hder, hlke, _⟩ := hjv j List.mem_cons_self
    have hstep : j.applyLoggedR S T σ = j.applyLogged S T σ := by
      unfold W3cJob.applyLoggedR W3cJob.applyDR W3cJob.applyLogged W3cJob.applyD
      rw [reconcileStarsKeyDR_eq σ T j.dt j.on j.R j.e (wildcardShapes S) j.cands
        j.negCands j.uposCands (hCO j.dt j.R j.e hlke hder)
        (fun r' hr' => by rw [hs]; exact hLU j.dt j.R j.e hlke hder r' hr')]
    show reconcileJobsLR S T (j.applyLoggedR S T σ) rest
        = reconcileJobsL S T (j.applyLogged S T σ) rest
    rw [hstep]
    exact ih _ (by rw [← hstep, W3cJob.applyLoggedR_schema, hs])
      (fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj'))

/-! ## The two-round drain loop -/

/-- The rows above an explicit frontier cursor (`outbox_rows(session, store, n)` —
    the per-round read; the stored watermark moves only at accept). -/
def GraphState.frontierRowsAbove (σ : GraphState) (n : Nat) : List Delta :=
  σ.outbox.filter (fun d => n < d.id)

/-- The invalidation key set of a round at cursor `n`. -/
def cascadeKeysAbove (S : Schema) (σ : GraphState) (n : Nat) :
    List (String × String × String) :=
  (σ.frontierRowsAbove n).flatMap (affectedKeys S σ)

/-- W3d-1's `cascadeKeys` is the round at the stored watermark. -/
theorem cascadeKeys_eq_above (S : Schema) (σ : GraphState) :
    cascadeKeys S σ = cascadeKeysAbove S σ σ.watermark := rfl

/-- Advance the frontier cursor past a round's read (`frontier_start = max id`,
    `processor.py:703`). -/
def GraphState.frontierMax (σ : GraphState) (n : Nat) : Nat :=
  (σ.frontierRowsAbove n).foldl (fun m d => max m d.id) n

/-- **`runCascade2`** (`run_cascade`, `rounds = len(strata) = 2`): round 1 on the
    frontier above the stored watermark, round 2 on the rows round 1 emitted, then
    the quiescence check — the rows above the round-2 cursor must map to NO keys,
    else the transaction aborts (reject: state unchanged). On accept the watermark
    advances past everything. -/
def runCascade2 (S : Schema) (T : Store) (σ : GraphState) (jobs1 jobs2 : List W3cJob) :
    GraphState :=
  if ((reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2).frontierRowsAbove
        ((reconcileJobsLR S T σ jobs1).frontierMax (σ.frontierMax σ.watermark))).all
      (fun d =>
        (affectedKeys S (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2) d).isEmpty)
  then { reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2 with
         watermark := (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2).maxOutboxId }
  else σ

/-! ## The W3d-2 closure — interleaved logged writes and two-round cascades -/

/-- **`ReachedByW3d2 σ S T`** — the two-stratum interleaved scheduler closure:
    admitted logged rule-routed writes and TWO-ROUND cascade runs, in any order.
    Each cascade leg's round-1 jobs must cover exactly the frontier's affected keys
    at the pre-state, and its round-2 jobs the keys of the rows round 1 emitted,
    read at the mid-state (`_map_deltas_to_keys` per round). Job batches are
    C-style data (validity + two-sided coverage as hypotheses); the state-derived
    enumeration discharge is the W3d-2 tail, as in W3d-1c. -/
inductive ReachedByW3d2 : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByW3d2 (emptyState S) S []
  | write {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hadm : FoldAdmits σ (rewriteClosure S t))
      (hprev : ReachedByW3d2 σ S T) :
      ReachedByW3d2 (σ.writeLoggedRules S t) S (t :: T)
  | cascade {σ : GraphState} {S : Schema} {T : Store} (jobs1 jobs2 : List W3cJob)
      (hjv1 : ∀ j ∈ jobs1, W3cJobValid S j)
      (hjv2 : ∀ j ∈ jobs2, W3cJobValid S j)
      (hcover1 : ∀ k ∈ cascadeKeysAbove S σ σ.watermark, ∃ j ∈ jobs1, j.key = k)
      (hscope1 : ∀ j ∈ jobs1, j.key ∈ cascadeKeysAbove S σ σ.watermark)
      (hcover2 : ∀ k ∈ cascadeKeysAbove S (reconcileJobsLR S T σ jobs1)
          (σ.frontierMax σ.watermark), ∃ j ∈ jobs2, j.key = k)
      (hscope2 : ∀ j ∈ jobs2, j.key ∈ cascadeKeysAbove S (reconcileJobsLR S T σ jobs1)
          (σ.frontierMax σ.watermark))
      (hprev : ReachedByW3d2 σ S T) :
      ReachedByW3d2 (runCascade2 S T σ jobs1 jobs2) S T

/-- Every W3d-2 state carries its schema (the anchor for the routed dispatch). -/
theorem reachedByW3d2_schema {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) : σ.schema = S := by
  induction h with
  | empty S => rfl
  | @write σp S T t _ _ ih =>
    show (σp.writeLoggedRules S t).schema = S
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).schema, writeRules_schema, ih]
  | @cascade σp S T jobs1 jobs2 _ _ _ _ _ _ _ ih =>
    show (runCascade2 S T σp jobs1 jobs2).schema = S
    unfold runCascade2
    split
    · show (reconcileJobsLR S T (reconcileJobsLR S T σp jobs1) jobs2).schema = S
      rw [reconcileJobsLR_schema, reconcileJobsLR_schema, ih]
    · exact ih

end Zanzibar
