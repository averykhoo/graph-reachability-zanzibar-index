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

/-! ## The W3d-2 structural layer — bookkeeping, outbox/edge soundness, terminality

Mirrors of the W3d-1a layer (`Cascade.lean`) over the ROUTED pass: the routed guard
changes which branch of the fold fires, never which state fields a branch touches.

**Attack-first on `runCascade2_no_abort` (2026-07-12d, `#eval`, scratch deleted) —
the statement SURVIVED and its hypotheses are load-bearing.** On the 3-stratum
schema `a := b ∨ y, b := c ∨ x, c := x ∖ y` (all of `a`,`b`,`c` tainted), `hLU2`
evaluates FALSE and the reject genuinely FIRES: the round-2 pass at `b`'s R-node
emits a row that maps to key `(doc, a, 1)`, the leftover check fails, and
`runCascade2` returns the pre-state — so no-abort WITHOUT `hLU2` is refuted, the
condition is doing exactly the "two strata in disguise" rejection. On the
2-stratum truncation (drop `a`), `hLU2` is TRUE while W3d-1's `hLU` is FALSE (the
widening is contentful: `b` reads the derived `c`), the leftovers map to no keys
(accept), and fully-drained `check = sem` held over the query grid for one- and
three-write batches. -/

@[simp] theorem reconcileResidueKeyR_edges (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands).edges = σ.edges := rfl

@[simp] theorem reconcileResidueKeyR_nodes (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands).nodes = σ.nodes := rfl

@[simp] theorem reconcileResidueKeyR_outbox (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands).outbox = σ.outbox := rfl

@[simp] theorem reconcileResidueKeyR_watermark (σ : GraphState) (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands).watermark
      = σ.watermark := rfl

theorem reconcileKeyDR_outbox (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKeyDR T dt on R e cands).outbox = σ.outbox := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    rw [reconcileKeyDR_cons, ih]
    split
    · exact writeDirect_outbox σ _
    · rfl

theorem reconcileKeyDR_watermark (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKeyDR T dt on R e cands).watermark = σ.watermark := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    rw [reconcileKeyDR_cons, ih]
    split
    · exact writeDirect_watermark σ _
    · rfl

/-- One unlogged routed pass never touches the outbox. -/
theorem W3cJob.applyDR_outbox (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    (j.applyDR S T σ).outbox = σ.outbox := by
  unfold W3cJob.applyDR GraphState.reconcileStarsKeyDR
  rw [reconcileKeyDR_outbox, reconcileResidueKeyR_outbox]

/-- One unlogged routed pass never touches the watermark. -/
theorem W3cJob.applyDR_watermark (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) :
    (j.applyDR S T σ).watermark = σ.watermark := by
  unfold W3cJob.applyDR GraphState.reconcileStarsKeyDR
  rw [reconcileKeyDR_watermark, reconcileResidueKeyR_watermark]

/-- One unlogged routed pass keeps the fresh-id source fixed. -/
theorem W3cJob.applyDR_nextDeltaId (S : Schema) (T : Store) (σ : GraphState)
    (j : W3cJob) : (j.applyDR S T σ).nextDeltaId = σ.nextDeltaId := by
  unfold GraphState.nextDeltaId GraphState.maxOutboxId
  rw [W3cJob.applyDR_outbox, W3cJob.applyDR_watermark]

/-- The routed logged batch leaves the watermark untouched (the drain advance is
    `runCascade2`'s final act, not the passes'). -/
theorem reconcileJobsLR_watermark (S : Schema) (T : Store) :
    ∀ (jobs : List W3cJob) (σ : GraphState),
      (reconcileJobsLR S T σ jobs).watermark = σ.watermark := by
  intro jobs
  induction jobs with
  | nil => intro σ; rfl
  | cons j rest ih =>
    intro σ
    show (reconcileJobsLR S T (j.applyLoggedR S T σ) rest).watermark = σ.watermark
    rw [ih]
    unfold W3cJob.applyLoggedR
    rw [pushDelta_watermark, W3cJob.applyDR_watermark]

/-- **Outbox soundness of the routed logged batch**: every row is an original row or
    a pass-emitted row — at some job's derived key, with an id strictly above the
    pre-batch frontier `max maxOutboxId watermark` (mirror of
    `reconcileJobsL_outbox_sound`). -/
theorem reconcileJobsLR_outbox_sound (S : Schema) (T : Store) :
    ∀ (jobs : List W3cJob) (σ : GraphState), ∀ d ∈ (reconcileJobsLR S T σ jobs).outbox,
      d ∈ σ.outbox ∨
      ((∃ j ∈ jobs, d.node = objNode ⟨j.dt, j.on⟩ j.R ∧ d.relation = j.R) ∧
        max σ.maxOutboxId σ.watermark < d.id) := by
  intro jobs
  induction jobs with
  | nil => intro σ d hd; exact Or.inl hd
  | cons j rest ih =>
    intro σ d hd
    have hfold : reconcileJobsLR S T σ (j :: rest)
        = reconcileJobsLR S T (j.applyLoggedR S T σ) rest := by
      unfold reconcileJobsLR
      rw [List.foldl_cons]
    rw [hfold] at hd
    have hout1 : (j.applyLoggedR S T σ).outbox
        = ⟨σ.nextDeltaId, objNode ⟨j.dt, j.on⟩ j.R, j.R⟩ :: σ.outbox := by
      unfold W3cJob.applyLoggedR
      rw [pushDelta_outbox, W3cJob.applyDR_outbox]
      have := W3cJob.applyDR_nextDeltaId S T σ j
      rw [this]
    have hwm1 : (j.applyLoggedR S T σ).watermark = σ.watermark := by
      unfold W3cJob.applyLoggedR
      rw [pushDelta_watermark, W3cJob.applyDR_watermark]
    have hmax1 : (j.applyLoggedR S T σ).maxOutboxId = σ.nextDeltaId := by
      unfold W3cJob.applyLoggedR
      rw [pushDelta_maxOutboxId, W3cJob.applyDR_nextDeltaId]
    rcases ih (j.applyLoggedR S T σ) d hd with hin | ⟨⟨j', hj', hn, hr⟩, hgt⟩
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

/-! ## Edge soundness of the routed batch -/

/-- Routed diff-fold edge soundness: every edge of the result is an old edge or a
    candidate's derived edge onto the pass's own R-node (removal only shrinks). -/
theorem reconcileKeyDR_edge_sound (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState) (a b : NodeKey),
      (a, b) ∈ (σ.reconcileKeyDR T dt on R e cands).edges →
      (a, b) ∈ σ.edges ∨ ∃ c ∈ cands, a = subjNode c ∧ b = objNode ⟨dt, on⟩ R := by
  intro cands
  induction cands with
  | nil => intro σ a b h; exact Or.inl h
  | cons c rest ih =>
    intro σ a b h
    rw [reconcileKeyDR_cons] at h
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

/-- Whole routed pass edge soundness (the residue half is edge-inert). -/
theorem reconcileStarsKeyDR_edge_sound (T : Store) (dt on R : String) (e : Expr)
    (shapes : List Shape) (cands negCands uposCands : List SubjectRef)
    (σ : GraphState) (a b : NodeKey)
    (h : (a, b) ∈ (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands
      uposCands).edges) :
    (a, b) ∈ σ.edges ∨ ∃ c ∈ cands, a = subjNode c ∧ b = objNode ⟨dt, on⟩ R := by
  unfold GraphState.reconcileStarsKeyDR at h
  rcases reconcileKeyDR_edge_sound T dt on R e cands _ a b h with hold | hc
  · rw [reconcileResidueKeyR_edges] at hold
    exact Or.inl hold
  · exact Or.inr hc

/-- Routed logged-batch edge soundness (the emission rows are edge-inert). -/
theorem reconcileJobsLR_edge_sound {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState) (a b : NodeKey),
      (a, b) ∈ (reconcileJobsLR S T σ jobs).edges →
      (a, b) ∈ σ.edges ∨
        ∃ j ∈ jobs, ∃ c ∈ j.cands, a = subjNode c ∧ b = objNode ⟨j.dt, j.on⟩ j.R := by
  intro jobs
  induction jobs with
  | nil => intro σ a b h; exact Or.inl h
  | cons j rest ih =>
    intro σ a b h
    have hfold : reconcileJobsLR S T σ (j :: rest)
        = reconcileJobsLR S T (j.applyLoggedR S T σ) rest := by
      unfold reconcileJobsLR
      rw [List.foldl_cons]
    rw [hfold] at h
    rcases ih _ a b h with hin | ⟨j', hj', c, hc, h1, h2⟩
    · have hedges : (j.applyLoggedR S T σ).edges = (j.applyDR S T σ).edges := by
        unfold W3cJob.applyLoggedR
        rw [pushDelta_edges]
      rw [hedges] at hin
      unfold W3cJob.applyDR at hin
      rcases reconcileStarsKeyDR_edge_sound T j.dt j.on j.R j.e (wildcardShapes S)
        j.cands j.negCands j.uposCands σ a b hin with hold | ⟨c, hc, h1, h2⟩
      · exact Or.inl hold
      · exact Or.inr ⟨j, List.mem_cons_self, c, hc, h1, h2⟩
    · exact Or.inr ⟨j', List.mem_cons_of_mem _ hj', c, hc, h1, h2⟩

/-! ## The untainted occurrence-count stack (W3d remove-leg R3, LOW chain)

Relocated DOWN from `RemoveOccCount.lean` so the R3 occurrence-count characterisation is
available at the LOW `ReachedByW3d2` level (consumed by `reachedByW3d2_untOccCount` below and
by the R5b shadow-transport crux `untaintedShadow_removeLeg` in `CascadeStrataSettle.lean`).
Every lemma here is about the LOW `runCascade2`/reconcile/`writeLoggedRules`/`removeLoggedRules`
defs, all defined at/below this module. The TOP-level `reachedByW3d2E_untOccCount` (over
`ReachedByW3d2E`) still lives in `RemoveOccCount.lean` — it imports this module so these
relocated lemmas remain visible to it. -/

open scoped List

/-- The direct edge a tuple materializes: `subjNode subject → objNode object relation`
    (exactly the edge `writeDirect` adds, `Write.lean:77-82` / `writeDirect_edges`). -/
def edgeOfTuple (u : Tuple) : NodeKey × NodeKey :=
  (subjNode u.subject, objNode u.object u.relation)

/-- The model-internal occurrence count of edge `(a,b)` across the store's rewrite
    closures — `Σ_{t ∈ T}` (occurrences of `(a,b)` among `rewriteClosure S t`). The RHS of
    the R3 invariant. -/
def untOccCount (S : Schema) (T : Store) (a b : NodeKey) : Nat :=
  ((T.flatMap (rewriteClosure S)).map edgeOfTuple).count (a, b)

/-! ### The retraction's count-shrink law -/

/-- One logged retraction's effect on `count p`: it decrements by one iff `u`'s materialized
    edge IS `p` (Nat subtraction floors the absent case). The exact dual of `writeLoggedOne`'s
    `+1` (`count_foldl_writeDirect`'s per-step growth). -/
theorem count_removeLoggedOne (u : Tuple) (p : NodeKey × NodeKey) (σ : GraphState) :
    (σ.removeLoggedOne u).edges.count p
      = σ.edges.count p - (if edgeOfTuple u = p then 1 else 0) := by
  unfold GraphState.removeLoggedOne edgeOfTuple
  by_cases hmem : (subjNode u.subject, objNode u.object u.relation) ∈ σ.edges
  · rw [if_pos hmem, pushDelta_edges, removeEdgeOne_edges]
    by_cases hp : (subjNode u.subject, objNode u.object u.relation) = p
    · rw [if_pos hp]; subst hp; exact List.count_erase_self
    · rw [if_neg hp, Nat.sub_zero]
      exact List.count_erase_of_ne (fun h => hp h.symm)
  · rw [if_neg hmem]
    by_cases hp : (subjNode u.subject, objNode u.object u.relation) = p
    · rw [if_pos hp]; subst hp
      have hz : σ.edges.count (subjNode u.subject, objNode u.object u.relation) = 0 :=
        List.count_eq_zero.mpr hmem
      omega
    · rw [if_neg hp, Nat.sub_zero]

/-- The logged rule-routed retraction's count-shrink law: `count p` drops by the number of
    closure members whose materialized edge is `p` — the exact dual of R3's
    `count_writeLoggedRules`. UNCONDITIONAL (Nat subtraction). -/
theorem count_removeLoggedRules (p : NodeKey × NodeKey) (S : Schema) (t : Tuple) :
    ∀ (σ : GraphState),
      (σ.removeLoggedRules S t).edges.count p
        = σ.edges.count p - ((rewriteClosure S t).map edgeOfTuple).count p := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosure S t = us
  induction us with
  | nil => intro σ; simp
  | cons u rest ih =>
    intro σ
    simp only [List.foldl_cons]
    rw [ih (σ.removeLoggedOne u), count_removeLoggedOne u p σ, List.map_cons]
    by_cases hp : edgeOfTuple u = p
    · subst hp
      rw [if_pos rfl, List.count_cons_self]
      omega
    · rw [if_neg hp, List.count_cons_of_ne hp]
      omega

/-! ### The store-erase split of the occurrence count -/

/-- Erasing a stored tuple `t ∈ T` splits the occurrence count: the total over `T` is the
    total over `T.erase t` plus `t`'s own closure occurrences. `List.erase` drops the FIRST
    copy, and `List.count` is permutation-invariant, so this holds even if `t` recurs in `T`
    (a store multiset). The store-side identity R4's confluence needs to match the smaller
    rebuild. -/
theorem untOccCount_erase (S : Schema) (T : Store) (t : Tuple) (a b : NodeKey) (ht : t ∈ T) :
    untOccCount S T a b
      = untOccCount S (T.erase t) a b
        + ((rewriteClosure S t).map edgeOfTuple).count (a, b) := by
  unfold untOccCount
  have hperm : T ~ t :: T.erase t := List.perm_cons_erase ht
  have h1 := ((hperm.flatMap_right (rewriteClosure S)).map edgeOfTuple).count_eq (a, b)
  rw [h1, List.flatMap_cons, List.map_append, List.count_append]
  omega

/-- The retraction only SHRINKS the edge multiset: any surviving edge was already present.
    (Off the R4 count-shrink law `count_removeLoggedRules` — a present edge has positive
    count, which the retraction can only lower, so it was positive, hence present, in `σ`.) -/
theorem mem_removeLoggedRules_edges {σ : GraphState} {S : Schema} {t : Tuple}
    {e : NodeKey × NodeKey} (h : e ∈ (σ.removeLoggedRules S t).edges) : e ∈ σ.edges := by
  rw [← List.count_pos_iff] at h ⊢
  rw [count_removeLoggedRules e S t σ] at h
  omega

/-! ### Filter preserves the count of a kept element -/

/-- Filtering by a predicate `q` that HOLDS at `x` leaves `x`'s count unchanged (the
    kept-element case of `List.count`/`List.filter`). Used for the `removeEdgePair`
    (filter-all) arm of the diffing fold: a non-R-node edge is never the removed pair. -/
theorem count_filter_of_true {α : Type _} [BEq α] [LawfulBEq α] (q : α → Bool) (x : α)
    (hx : q x = true) : ∀ l : List α, (l.filter q).count x = l.count x := by
  intro l
  induction l with
  | nil => rfl
  | cons y rest ih =>
    rw [List.filter_cons]
    by_cases hy : q y = true
    · rw [if_pos hy, List.count_cons, List.count_cons, ih]
    · rw [if_neg hy, ih]
      have hyx : (y == x) = false := by
        rw [beq_eq_false_iff_ne]
        intro h; subst h; exact hy hx
      rw [List.count_cons, hyx]
      simp

/-! ### The write leg — an admitted `writeDirect` fold counts occurrences -/

/-- **The write-fold count-growth lemma.** When every write in the fold is ADMITTED
    (`FoldAdmits`, the write constructor's hypothesis — `RulesComplete.lean:54`), each
    `writeDirect` prepends its materialized edge, so `count (a,b)` grows by exactly the
    number of fold tuples whose materialized edge is `(a,b)` — a pure occurrence count.
    (No acyclicity argument needed: admission is the constructor's own hypothesis.) -/
theorem count_foldl_writeDirect (a b : NodeKey) :
    ∀ (us : List Tuple) {σ : GraphState}, FoldAdmits σ us →
      (us.foldl (fun acc u => acc.writeDirect u) σ).edges.count (a, b)
        = σ.edges.count (a, b) + (us.map edgeOfTuple).count (a, b) := by
  intro us
  induction us with
  | nil => intro σ _; simp
  | cons u rest ih =>
    intro σ hfa
    obtain ⟨hadm, hrest⟩ := hfa
    have hstep : (σ.writeDirect u).edges = edgeOfTuple u :: σ.edges := by
      rw [writeDirect_edges, if_pos hadm]; rfl
    simp only [List.foldl_cons]
    rw [ih hrest, hstep, List.count_cons, List.map_cons, List.count_cons]
    omega

/-- The logged rule-routed write's count-growth: the edge count grows by the closure's
    occurrence count of `(a,b)` (the logged core is the unlogged `writeRules`,
    `writeLoggedRules_evalEq`; then `count_foldl_writeDirect` under `FoldAdmits`). -/
theorem count_writeLoggedRules (a b : NodeKey) (σ : GraphState) (S : Schema) (t : Tuple)
    (hadm : FoldAdmits σ (rewriteClosure S t)) :
    (σ.writeLoggedRules S t).edges.count (a, b)
      = σ.edges.count (a, b) + ((rewriteClosure S t).map edgeOfTuple).count (a, b) := by
  rw [(writeLoggedRules_evalEq (EvalEq.refl σ) S t).edges]
  unfold GraphState.writeRules
  exact count_foldl_writeDirect a b (rewriteClosure S t) hadm

/-! ### The cascade leg — a routed diffing pass is untainted-count-inert

The diffing edge audit `reconcileKeyDR` touches ONLY edges into the job's own terminal R-node
`objNode ⟨dt,on⟩ R` — each fold step is either `writeDirect ⟨c,R,⟨dt,on⟩⟩` or
`removeEdgePair (subjNode c) (objNode ⟨dt,on⟩ R)`. So an edge `(a,b)` with
`b ≠ objNode ⟨dt,on⟩ R` keeps its exact count, and the whole two-round cascade is
untainted-count-inert. -/

/-- The routed diffing edge audit preserves `count (a,b)` when `b` is not the job's R-node. -/
theorem count_reconcileKeyDR_of_ne (T : Store) (dt on R : String) (e : Expr)
    {a b : NodeKey} (hb : b ≠ objNode ⟨dt, on⟩ R) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKeyDR T dt on R e cands).edges.count (a, b) = σ.edges.count (a, b) := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    rw [reconcileKeyDR_cons, ih]
    split
    · rw [writeDirect_edges]
      split
      · rw [List.count_cons]
        have hne : ((subjNode c, objNode ⟨dt, on⟩ R) == (a, b)) = false := by
          rw [beq_eq_false_iff_ne]
          intro h; exact hb (congrArg Prod.snd h).symm
        rw [hne]; simp
      · rfl
    · rw [removeEdgePair_edges]
      refine count_filter_of_true _ (a, b) ?_ σ.edges
      have hbne : (b == objNode ⟨dt, on⟩ R) = false := by
        rw [beq_eq_false_iff_ne]; exact hb
      simp [hbne]

/-- The routed full-object pass preserves `count (a,b)` off the job's R-node (the residue
    recompute `reconcileResidueKeyR` leaves edges untouched, then `reconcileKeyDR`). -/
theorem count_reconcileStarsKeyDR_of_ne (T : Store) (dt on R : String) (e : Expr)
    (shapes : List Shape) (cands negCands uposCands : List SubjectRef)
    {a b : NodeKey} (hb : b ≠ objNode ⟨dt, on⟩ R) (σ : GraphState) :
    (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands uposCands).edges.count (a, b)
      = σ.edges.count (a, b) := by
  unfold GraphState.reconcileStarsKeyDR
  rw [count_reconcileKeyDR_of_ne T dt on R e hb cands, reconcileResidueKeyR_edges]

/-- One routed logged job preserves `count (a,b)` off its R-node (the emission
    `pushDelta` leaves edges untouched). -/
theorem count_applyLoggedR_of_ne (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob)
    {a b : NodeKey} (hb : b ≠ objNode ⟨j.dt, j.on⟩ j.R) :
    (j.applyLoggedR S T σ).edges.count (a, b) = σ.edges.count (a, b) := by
  unfold W3cJob.applyLoggedR W3cJob.applyDR
  rw [pushDelta_edges]
  exact count_reconcileStarsKeyDR_of_ne T j.dt j.on j.R j.e (wildcardShapes S)
    j.cands j.negCands j.uposCands hb σ

/-- A routed logged batch preserves `count (a,b)` if `b` is off EVERY job's R-node. -/
theorem count_reconcileJobsLR_of_ne (S : Schema) (T : Store) {a b : NodeKey} :
    ∀ (jobs : List W3cJob), (∀ j ∈ jobs, b ≠ objNode ⟨j.dt, j.on⟩ j.R) →
      ∀ (σ : GraphState),
        (reconcileJobsLR S T σ jobs).edges.count (a, b) = σ.edges.count (a, b) := by
  intro jobs
  induction jobs with
  | nil => intro _ σ; rfl
  | cons j rest ih =>
    intro hjobs σ
    show (reconcileJobsLR S T (j.applyLoggedR S T σ) rest).edges.count (a, b)
      = σ.edges.count (a, b)
    rw [ih (fun j' hj' => hjobs j' (List.mem_cons_of_mem _ hj'))]
    exact count_applyLoggedR_of_ne S T σ j (hjobs j List.mem_cons_self)

/-- The two-round drain loop preserves `count (a,b)` if `b` is off every job's R-node in
    BOTH rounds (accept: two batches, watermark bump is edge-inert; reject: identity). -/
theorem count_runCascade2_of_ne (S : Schema) (T : Store) (σ : GraphState)
    (jobs1 jobs2 : List W3cJob) {a b : NodeKey}
    (h1 : ∀ j ∈ jobs1, b ≠ objNode ⟨j.dt, j.on⟩ j.R)
    (h2 : ∀ j ∈ jobs2, b ≠ objNode ⟨j.dt, j.on⟩ j.R) :
    (runCascade2 S T σ jobs1 jobs2).edges.count (a, b) = σ.edges.count (a, b) := by
  unfold runCascade2
  split
  · show (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2).edges.count (a, b)
      = σ.edges.count (a, b)
    rw [count_reconcileJobsLR_of_ne S T jobs2 h2,
      count_reconcileJobsLR_of_ne S T jobs1 h1]
  · rfl

/-! ### The R3 invariant over the LOW two-round chain -/

/-- Every VALID cascade job (`W3cJobValid`) is at a DERIVED R-node, so an untainted edge's
    object endpoint differs from every job's R-node — the LOW-chain analog of
    `enumJobs2At_Rnode_ne` (which is stated over `enumJobs2At` and stays in
    `RemoveOccCount.lean`). -/
theorem w3cJobsValid_Rnode_ne {S : Schema} {b : NodeKey}
    (hb : isDerived S (b.type, b.pred) = false) :
    ∀ (jobs : List W3cJob), (∀ j ∈ jobs, W3cJobValid S j) →
      ∀ j ∈ jobs, b ≠ objNode ⟨j.dt, j.on⟩ j.R := by
  intro jobs hjv j hj heq
  obtain ⟨_, _, _, _, _, _, hder, _, _⟩ := hjv j hj
  have ht : (objNode ⟨j.dt, j.on⟩ j.R).type = j.dt := objNode_type _ _
  have hp : (objNode ⟨j.dt, j.on⟩ j.R).pred = j.R := objNode_pred _ _
  rw [heq, ht, hp, hder] at hb
  exact Bool.noConfusion hb

/-- **R3 at the LOW chain — the untainted occurrence-count invariant over `ReachedByW3d2`.**
    For every UNTAINTED direct edge `(a,b)` (`b.pred` not a derived relation of `b.type`), its
    ref-count in `σ.edges` is the total occurrence count of `(a,b)` across the stored writes'
    rewrite closures. A copy of `reachedByW3d2E_untOccCount` re-based on `ReachedByW3d2`'s own
    `empty`/`write`/`cascade` constructors; the `cascade` case reads the R-node-ne facts off
    each job's `W3cJobValid` (`w3cJobsValid_Rnode_ne`) rather than off `enumJobs2At`. -/
theorem reachedByW3d2_untOccCount {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    ∀ a b : NodeKey, isDerived S (b.type, b.pred) = false →
      σ.edges.count (a, b) = untOccCount S T a b := by
  induction h with
  | empty S =>
    intro a b _
    simp [untOccCount, emptyState]
  | @write σp S T t hadm hprev ih =>
    intro a b hb
    rw [count_writeLoggedRules a b σp S t hadm, ih a b hb]
    unfold untOccCount
    rw [List.flatMap_cons, List.map_append, List.count_append]
    omega
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro a b hb
    have h1 : ∀ j ∈ jobs1, b ≠ objNode ⟨j.dt, j.on⟩ j.R := w3cJobsValid_Rnode_ne hb jobs1 hjv1
    have h2 : ∀ j ∈ jobs2, b ≠ objNode ⟨j.dt, j.on⟩ j.R := w3cJobsValid_Rnode_ne hb jobs2 hjv2
    rw [count_runCascade2_of_ne S T σp jobs1 jobs2 h1 h2]
    exact ih a b hb

/-! ### The cascade leg — a routed diffing pass is NON-BARE-SOURCE-count-inert (R5b source leg)

The SOURCE-keyed mirror of the R-node target reasoning above. The diffing edge audit
`reconcileKeyDR` touches ONLY edges sourced at a candidate node `subjNode c` — each fold step is
`writeDirect ⟨c,R,⟨dt,on⟩⟩` (adds source `subjNode c`) or `removeEdgePair (subjNode c)
(objNode ⟨dt,on⟩ R)` (removes source `subjNode c`). A valid job's candidates are BARE-predicate
(`W3cJobValid`, `hcb`), so `subjNode c` has predicate `BARE`. Hence an edge `(a,b)` with
`a.pred ≠ BARE` keeps its exact count, and the whole two-round cascade is non-bare-source-count-
inert — attack-first CONFIRMED via the existing `reachedByW3d2_edge_source_ne_R` (cascade edge
sources are bare candidates, lines above). This is the SOURCE analog of the `*_of_ne` stack the
R5b remove-leg's source-keyed retraction fact needs. -/

/-- The routed diffing edge audit preserves `count (a,b)` when the source `a` is non-BARE and
    every candidate is BARE (so every touched edge is BARE-sourced, `a ≠ subjNode c`). -/
theorem count_reconcileKeyDR_of_src (T : Store) (dt on R : String) (e : Expr)
    {a b : NodeKey} (ha : a.pred ≠ BARE) :
    ∀ (cands : List SubjectRef), (∀ c ∈ cands, c.predicate = BARE) →
      ∀ (σ : GraphState),
        (σ.reconcileKeyDR T dt on R e cands).edges.count (a, b) = σ.edges.count (a, b) := by
  intro cands
  induction cands with
  | nil => intro _ σ; rfl
  | cons c rest ih =>
    intro hcb σ
    have hane : a ≠ subjNode c := by
      intro h; exact ha (by rw [h, subjNode_pred, hcb c List.mem_cons_self])
    rw [reconcileKeyDR_cons, ih (fun c' hc' => hcb c' (List.mem_cons_of_mem _ hc'))]
    split
    · rw [writeDirect_edges]
      split
      · rw [List.count_cons]
        have hne : ((subjNode c, objNode ⟨dt, on⟩ R) == (a, b)) = false := by
          rw [beq_eq_false_iff_ne]
          intro h; exact hane (congrArg Prod.fst h).symm
        rw [hne]; simp
      · rfl
    · rw [removeEdgePair_edges]
      refine count_filter_of_true _ (a, b) ?_ σ.edges
      have hane' : (a == subjNode c) = false := by
        rw [beq_eq_false_iff_ne]; exact hane
      simp [hane']

/-- The routed full-object pass preserves `count (a,b)` for a non-BARE source (the residue
    recompute `reconcileResidueKeyR` leaves edges untouched, then `reconcileKeyDR`). -/
theorem count_reconcileStarsKeyDR_of_src (T : Store) (dt on R : String) (e : Expr)
    (shapes : List Shape) (cands negCands uposCands : List SubjectRef)
    {a b : NodeKey} (ha : a.pred ≠ BARE) (hcb : ∀ c ∈ cands, c.predicate = BARE)
    (σ : GraphState) :
    (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands uposCands).edges.count (a, b)
      = σ.edges.count (a, b) := by
  unfold GraphState.reconcileStarsKeyDR
  rw [count_reconcileKeyDR_of_src T dt on R e ha cands hcb, reconcileResidueKeyR_edges]

/-- One routed logged job preserves `count (a,b)` for a non-BARE source (the emission
    `pushDelta` leaves edges untouched). -/
theorem count_applyLoggedR_of_src (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob)
    {a b : NodeKey} (ha : a.pred ≠ BARE) (hcb : ∀ c ∈ j.cands, c.predicate = BARE) :
    (j.applyLoggedR S T σ).edges.count (a, b) = σ.edges.count (a, b) := by
  unfold W3cJob.applyLoggedR W3cJob.applyDR
  rw [pushDelta_edges]
  exact count_reconcileStarsKeyDR_of_src T j.dt j.on j.R j.e (wildcardShapes S)
    j.cands j.negCands j.uposCands ha hcb σ

/-- A routed logged batch preserves `count (a,b)` for a non-BARE source if every job's
    candidates are BARE. -/
theorem count_reconcileJobsLR_of_src (S : Schema) (T : Store) {a b : NodeKey}
    (ha : a.pred ≠ BARE) :
    ∀ (jobs : List W3cJob), (∀ j ∈ jobs, ∀ c ∈ j.cands, c.predicate = BARE) →
      ∀ (σ : GraphState),
        (reconcileJobsLR S T σ jobs).edges.count (a, b) = σ.edges.count (a, b) := by
  intro jobs
  induction jobs with
  | nil => intro _ σ; rfl
  | cons j rest ih =>
    intro hjobs σ
    show (reconcileJobsLR S T (j.applyLoggedR S T σ) rest).edges.count (a, b)
      = σ.edges.count (a, b)
    rw [ih (fun j' hj' => hjobs j' (List.mem_cons_of_mem _ hj'))]
    exact count_applyLoggedR_of_src S T σ j ha (hjobs j List.mem_cons_self)

/-- The two-round drain loop preserves `count (a,b)` for a non-BARE source if every job's
    candidates are BARE in BOTH rounds (accept: two batches; reject: identity). -/
theorem count_runCascade2_of_src (S : Schema) (T : Store) (σ : GraphState)
    (jobs1 jobs2 : List W3cJob) {a b : NodeKey} (ha : a.pred ≠ BARE)
    (h1 : ∀ j ∈ jobs1, ∀ c ∈ j.cands, c.predicate = BARE)
    (h2 : ∀ j ∈ jobs2, ∀ c ∈ j.cands, c.predicate = BARE) :
    (runCascade2 S T σ jobs1 jobs2).edges.count (a, b) = σ.edges.count (a, b) := by
  unfold runCascade2
  split
  · show (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2).edges.count (a, b)
      = σ.edges.count (a, b)
    rw [count_reconcileJobsLR_of_src S T ha jobs2 h2,
      count_reconcileJobsLR_of_src S T ha jobs1 h1]
  · rfl

/-! ### The R3 SOURCE invariant over the LOW two-round chain -/

/-- Every VALID cascade job (`W3cJobValid`) has BARE-predicate candidates — the source-side
    fact the cascade case of `reachedByW3d2_srcOccCount` reads (the analog of
    `w3cJobsValid_Rnode_ne`, off the `hcb` clause rather than the derived-R-node clause). -/
theorem w3cJobsValid_cands_bare {S : Schema} :
    ∀ (jobs : List W3cJob), (∀ j ∈ jobs, W3cJobValid S j) →
      ∀ j ∈ jobs, ∀ c ∈ j.cands, c.predicate = BARE := by
  intro jobs hjv j hj c hc
  obtain ⟨_, hcb, _⟩ := hjv j hj
  exact hcb c hc

/-- **R3 SOURCE at the LOW chain — the non-bare-source occurrence-count invariant over
    `ReachedByW3d2`.** For every direct edge `(a,b)` whose SOURCE predicate `a.pred` is not
    `BARE`, its ref-count in `σ.edges` is the total occurrence count of `(a,b)` across the
    stored writes' rewrite closures — because such edges arise ONLY from stored-tuple closures
    (`write`), never from a cascade pass (cascade/reconcile edges are BARE-sourced candidate
    edges, so a non-bare source count is cascade-inert, `count_runCascade2_of_src`). The SOURCE
    mirror of `reachedByW3d2_untOccCount` (whose guard is on the edge TARGET, `b.pred` non-
    derived); the R5b remove-leg's source-keyed retraction discharge needs THIS form. -/
theorem reachedByW3d2_srcOccCount {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) :
    ∀ a b : NodeKey, a.pred ≠ BARE →
      σ.edges.count (a, b) = untOccCount S T a b := by
  induction h with
  | empty S =>
    intro a b _
    simp [untOccCount, emptyState]
  | @write σp S T t hadm hprev ih =>
    intro a b ha
    rw [count_writeLoggedRules a b σp S t hadm, ih a b ha]
    unfold untOccCount
    rw [List.flatMap_cons, List.map_append, List.count_append]
    omega
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    intro a b ha
    have h1 : ∀ j ∈ jobs1, ∀ c ∈ j.cands, c.predicate = BARE :=
      w3cJobsValid_cands_bare jobs1 hjv1
    have h2 : ∀ j ∈ jobs2, ∀ c ∈ j.cands, c.predicate = BARE :=
      w3cJobsValid_cands_bare jobs2 hjv2
    rw [count_runCascade2_of_src S T σp jobs1 jobs2 ha h1 h2]
    exact ih a b ha

/-! ## R-node terminality over the two-round closure -/

/-- **No W3d-2 edge is sourced at an `R`-userset node** (the two-round analog of
    `reachedByW3d_edge_source_ne_R`): a logged write's edge sources are rewrite-
    closure subjects, either round's cascade edge sources are bare candidates. -/
theorem reachedByW3d2_edge_source_ne_R {σ : GraphState} {S : Schema} {T : Store}
    {R : String} (hRne : R ≠ BARE) (h : ReachedByW3d2 σ S T) :
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
  | @cascade σp S T jobs1 jobs2 hjv1 hjv2 _ _ _ _ hprev ih =>
    intro hnt hns a b hab
    unfold runCascade2 at hab
    split at hab
    · have hab' : (a, b) ∈ (reconcileJobsLR S T (reconcileJobsLR S T σp jobs1)
          jobs2).edges := hab
      rcases reconcileJobsLR_edge_sound jobs2 _ a b hab' with hmid | ⟨j, hj, c, hc, h1, _⟩
      · rcases reconcileJobsLR_edge_sound jobs1 σp a b hmid
          with hold | ⟨j, hj, c, hc, h1, _⟩
        · exact ih hnt hns a b hold
        · rw [h1, subjNode_pred]
          obtain ⟨_, hcb, _⟩ := hjv1 j hj
          rw [hcb c hc]
          exact Ne.symm hRne
      · rw [h1, subjNode_pred]
        obtain ⟨_, hcb, _⟩ := hjv2 j hj
        rw [hcb c hc]
        exact Ne.symm hRne
    · exact ih hnt hns a b hab

/-- **The derived R-node is never an edge source on a W3d-2 state.** -/
theorem reachedByW3d2_Rnode_not_source {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hRne : R ≠ BARE) (hder : isDerived S (dt, R) = true) (h : ReachedByW3d2 σ S T) :
    ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges := by
  obtain ⟨hnt, hns⟩ := hterm dt R hder
  intro y hy
  exact reachedByW3d2_edge_source_ne_R hRne h hnt hns _ y hy (objNode_pred ⟨dt, on⟩ R)

/-- R-node terminality survives a routed logged batch, from any terminal base state
    (the batch-transported form — stackable round over round). -/
theorem reconcileJobsLR_Rnode_not_source {S : Schema} {T : Store} {jobs : List W3cJob}
    {dt on R : String} (hRne : R ≠ BARE) (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    {σ : GraphState} (hbase : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) :
    ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ (reconcileJobsLR S T σ jobs).edges := by
  intro y hy
  rcases reconcileJobsLR_edge_sound jobs σ _ y hy with hold | ⟨j, hj, c, hc, h1, _⟩
  · exact hbase y hold
  · obtain ⟨_, hcb, _⟩ := hjv j hj
    have hpred : (objNode ⟨dt, on⟩ R).pred = BARE := by
      rw [h1, subjNode_pred, hcb c hc]
    rw [objNode_pred] at hpred
    exact hRne hpred

/-! ## Frontier-cursor arithmetic -/

/-- The cursor advance dominates its start. -/
theorem GraphState.le_frontierMax (σ : GraphState) (n : Nat) : n ≤ σ.frontierMax n := by
  unfold GraphState.frontierMax
  exact foldl_max_init_le _ n

/-- **Every outbox row sits at or below the advanced cursor**: a row above `n` is in
    the round's frontier (hence folded into the max), a row at or below `n` is under
    the start. This is what makes a round's read exhaustive — nothing between the old
    cursor and the new one is skipped. -/
theorem GraphState.outbox_le_frontierMax (σ : GraphState) (n : Nat) :
    ∀ d ∈ σ.outbox, d.id ≤ σ.frontierMax n := by
  intro d hd
  by_cases hgt : n < d.id
  · unfold GraphState.frontierMax GraphState.frontierRowsAbove
    exact mem_le_foldl_max _ n d (List.mem_filter.mpr ⟨hd, decide_eq_true hgt⟩)
  · exact le_trans (Nat.le_of_not_lt hgt) (σ.le_frontierMax n)

/-! ## T5 over the two-round scheduler — the reject branch never fires

The fragment condition **`hLU2`** (the 2-strata condition without invoking
`stratify`): every `computed` operand of a derived def is untainted OR itself a
declared derived key whose own `computed` operands are ALL untainted. Faithful to
`len(strata) == 2` — `_stratify` (`zanzibar_utils_v1.py:1630`) layers the tainted
keys by Kahn; two layers means every derived-reading-derived chain stops after one
hop. Stated dependency-wise (as `hLU` was), not via `stratify`, so the W3d-1
condition is literally the special case (`hLU2_of_hLU`). -/

/-- W3d-1's single-stratum `hLU` implies the two-stratum `hLU2` (the widening is
    conservative — vacuously, no operand is derived). -/
theorem hLU2_of_hLU {S : Schema}
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false) :
    ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false := by
  intro dt R e hlk hder r' hr' hder' _ _ _ _
  cases (hLU dt R e hlk hder r' hr').symm.trans hder'

/-- **`runCascade2_no_abort` (T5 half a, two strata).** Under `hLU2` the final
    leftover check always passes. The round-2 rows above the round-2 cursor are
    jobs2 emissions at derived R-nodes (original and round-1 rows sit at or below
    the cursor by `outbox_le_frontierMax`); such a row's only candidate object is
    the R-node itself (terminality), whose predicate `j.R` is a derived pred that —
    by `hscope2` — was dirtied by a ROUND-1 emission, i.e. `j`'s def reads some
    round-1 job's derived pred as a computed operand. `hLU2` then forces ALL of
    `j`'s operands untainted — contradiction. So NO derived def reads `j.R`: the
    emission maps to no keys, and Python's `InvariantViolation`
    (`processor.py:736-739`) is dead code at two strata. -/
theorem runCascade2_no_abort {σ : GraphState} {S : Schema} {T : Store}
    {jobs1 jobs2 : List W3cJob}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hjv1 : ∀ j ∈ jobs1, W3cJobValid S j)
    (hjv2 : ∀ j ∈ jobs2, W3cJobValid S j)
    (hscope2 : ∀ j ∈ jobs2, j.key ∈ cascadeKeysAbove S (reconcileJobsLR S T σ jobs1)
        (σ.frontierMax σ.watermark))
    (h : ReachedByW3d2 σ S T) :
    runCascade2 S T σ jobs1 jobs2
      = { reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2 with
          watermark := (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1)
            jobs2).maxOutboxId } := by
  unfold runCascade2
  refine if_pos ?_
  rw [List.all_eq_true]
  intro d hd
  unfold GraphState.frontierRowsAbove at hd
  obtain ⟨hdmem, hdgt'⟩ := List.mem_filter.mp hd
  have hdgt : (reconcileJobsLR S T σ jobs1).frontierMax (σ.frontierMax σ.watermark)
      < d.id := of_decide_eq_true hdgt'
  -- the row is a jobs2 emission: mid-state rows sit at or below the round-2 cursor
  rcases reconcileJobsLR_outbox_sound S T jobs2 (reconcileJobsLR S T σ jobs1) d hdmem
    with hin | ⟨⟨j, hj, hnode, _⟩, _⟩
  · exfalso
    have := (reconcileJobsLR S T σ jobs1).outbox_le_frontierMax
      (σ.frontierMax σ.watermark) d hin
    omega
  obtain ⟨hRne2, _, _, _, _, _, hder2, hlke2, _⟩ := hjv2 j hj
  -- (A) unfold `hscope2`: j's def reads a ROUND-1 job's derived pred as an operand
  have hjk := hscope2 j hj
  unfold cascadeKeysAbove at hjk
  obtain ⟨d', hd'raw, hjk'⟩ := List.mem_flatMap.mp hjk
  unfold GraphState.frontierRowsAbove at hd'raw
  obtain ⟨hd'mem, hd'gt'⟩ := List.mem_filter.mp hd'raw
  have hd'gt : σ.frontierMax σ.watermark < d'.id := of_decide_eq_true hd'gt'
  -- the dirtying row is itself a round-1 emission: original rows sit at or below
  -- the round-1 cursor
  rcases reconcileJobsLR_outbox_sound S T jobs1 σ d' hd'mem
    with hin' | ⟨⟨j1, hj1, hnode1, _⟩, _⟩
  · exfalso
    have := σ.outbox_le_frontierMax σ.watermark d' hin'
    omega
  obtain ⟨hRne1, _, _, _, _, _, hder1, _, _⟩ := hjv1 j1 hj1
  -- j1's R-node is terminal at the mid state → the row's only candidate object is
  -- the R-node itself
  have hbase1 := reachedByW3d2_Rnode_not_source (on := j1.on) hterm hRne1 hder1 h
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
  have h1' : k'.1 = j.dt := congrArg (fun p => p.1) hkeq
  have h2' : k'.2 = j.R := congrArg (fun p => p.2.1) hkeq
  have hk'eq : k' = (j.dt, j.R) := by rw [← h1', ← h2']
  have htype1 : d'.node.type = j1.dt := by rw [hnode1, objNode_type]
  have hpred1 : d'.node.pred = j1.R := by rw [hnode1, objNode_pred]
  rw [hk'eq, hlke2] at hc3
  simp only [Option.map_some, Option.getD_some] at hc3
  rw [hpred1, List.contains_eq_mem] at hc3
  have hmemj1R : j1.R ∈ computedRefs j.e := of_decide_eq_true hc3
  have hjdt : j.dt = j1.dt := by rw [← h1', hc1, htype1]
  -- (B) j's own R-node is terminal at the final state → the emission's only
  -- candidate object is itself, and no derived def may read j.R (hLU2)
  have hbase2 := reachedByW3d2_Rnode_not_source (on := j.on) hterm hRne2 hder2 h
  have hmidT2 := reconcileJobsLR_Rnode_not_source (T := T) (jobs := jobs1)
    hRne2 hjv1 hbase2
  have hfinT2 := reconcileJobsLR_Rnode_not_source (T := T) (jobs := jobs2)
    hRne2 hjv2 hmidT2
  have hreach2 : ∀ w, (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2).reach
      d.node w = false := by
    intro w
    by_contra hne
    have htrue : (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2).reach
        d.node w = true := by
      revert hne
      cases (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2).reach d.node w
        <;> simp
    obtain ⟨y, hy⟩ := nreaches_first_edge (reach_sound htrue)
    rw [hnode] at hy
    exact hfinT2 y hy
  have hobj2 : (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1)
      jobs2).affectedObjects d = [d.node] := by
    unfold GraphState.affectedObjects
    rw [List.filter_eq_nil_iff.mpr (fun w _ => by rw [hreach2 w]; exact Bool.false_ne_true)]
  have htype : d.node.type = j.dt := by rw [hnode, objNode_type]
  have hpredR : d.node.pred = j.R := by rw [hnode, objNode_pred]
  have hkeys : affectedKeys S (reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2)
      d = [] := by
    unfold affectedKeys
    rw [hobj2]
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
        | some e'' =>
          rw [hlk] at hkref
          simp only [Option.map_some, Option.getD_some] at hkref
          have hmem : d.node.pred ∈ computedRefs e'' := by
            rw [List.contains_eq_mem] at hkref
            exact of_decide_eq_true hkref
          have hlkj : S.lookup (k.1, d.node.pred) = some j.e := by
            rw [hk1, htype, hpredR]
            exact hlke2
          have hderj : isDerived S (k.1, d.node.pred) = true := by
            rw [hk1, htype, hpredR]
            exact hder2
          have hallU := hLU2 k.1 k.2 e'' hlk hkder d.node.pred hmem hderj j.e hlkj
          have hfalse := hallU j1.R hmemj1R
          have hkdt : k.1 = j1.dt := by rw [hk1, htype, hjdt]
          rw [hkdt] at hfalse
          cases hder1.symm.trans hfalse
      rw [if_neg hcond]
  rw [hkeys]
  rfl

/-- **`cascade2_drains` (T5 half b, two strata).** After a two-round cascade on the
    fragment the state is `Quiescent`: the watermark advance past BOTH rounds'
    emissions is JUSTIFIED by `runCascade2_no_abort` (the skipped rows provably map
    to no keys), never asserted. -/
theorem cascade2_drains {σ : GraphState} {S : Schema} {T : Store}
    {jobs1 jobs2 : List W3cJob}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hjv1 : ∀ j ∈ jobs1, W3cJobValid S j)
    (hjv2 : ∀ j ∈ jobs2, W3cJobValid S j)
    (hscope2 : ∀ j ∈ jobs2, j.key ∈ cascadeKeysAbove S (reconcileJobsLR S T σ jobs1)
        (σ.frontierMax σ.watermark))
    (h : ReachedByW3d2 σ S T) :
    Quiescent (runCascade2 S T σ jobs1 jobs2) := by
  rw [runCascade2_no_abort hterm hLU2 hjv1 hjv2 hscope2 h]
  intro d hd
  exact mem_outbox_le_maxOutboxId _ d hd

/-! ## Per-stratum operand-read inertness — the routed pass off its own key

A routed pass at key `(dt, R, on)` writes the residue only at its own R-node under
`R`, and touches edges only AT that (terminal) R-node — so every read anchored at
any OTHER key is constant across the pass: the untainted ≤4-probe read (`graphRec`),
the derived edge+residue read (`probeDerived`), hence the routed leaf read (`check`)
and the routed compiled guard (`checkFnR`) of every other key, WHATEVER its stratum.
This is the model-level reason a round may settle its keys in any order (the
2026-07-12c attack finding) and the base fact the stratum-staged settledness
transport consumes: a stratum-2 guard is undisturbed by its own round's other
passes, and a stratum-1 pass perturbs a stratum-2 guard only through the reconciled
key itself. Mirrors of the `ReconcileDiff.lean` W3d-1b layer with routed guards —
the guard swap never changes which fields a fold branch touches. -/

theorem reconcileKeyDR_residue (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (σ.reconcileKeyDR T dt on R e cands).residue = σ.residue := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    rw [reconcileKeyDR_cons, ih]
    split
    · exact writeDirect_residue σ _
    · rfl

/-- The routed residue recompute leaves every other `(key, relation)` untouched. -/
theorem reconcileResidueKeyR_residue_other {σ : GraphState} {T : Store}
    {dt on R : String} {e : Expr} {shapes : List Shape}
    {negCands uposCands : List SubjectRef} {k' : NodeKey} {r' : String}
    (h : ¬(k' = objNode ⟨dt, on⟩ R ∧ r' = R)) :
    (σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands).residue k' r'
      = σ.residue k' r' := by
  unfold GraphState.reconcileResidueKeyR
  rw [putResidue_residue, if_neg h]

/-- The whole routed pass leaves every other `(key, relation)` residue untouched. -/
theorem reconcileStarsKeyDR_residue_other {σ : GraphState} {T : Store}
    {dt on R : String} {e : Expr} {shapes : List Shape}
    {cands negCands uposCands : List SubjectRef} {k' : NodeKey} {r' : String}
    (h : ¬(k' = objNode ⟨dt, on⟩ R ∧ r' = R)) :
    (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands uposCands).residue k' r'
      = σ.residue k' r' := by
  unfold GraphState.reconcileStarsKeyDR
  rw [reconcileKeyDR_residue, reconcileResidueKeyR_residue_other h]

/-- The routed fold maintains "the pass's R-node is never a source" step by step. -/
theorem reconcileKeyDR_Rnode_terminal (T : Store) (dt on R : String) (e : Expr)
    (hRne : R ≠ BARE) :
    ∀ (cands : List SubjectRef), (∀ c ∈ cands, c.predicate = BARE) →
      ∀ (σ : GraphState), (∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) →
      ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ (σ.reconcileKeyDR T dt on R e cands).edges := by
  intro cands hcb σ hRns y hy
  rcases reconcileKeyDR_edge_sound T dt on R e cands σ _ y hy with hold | ⟨c, hc, hac, _⟩
  · exact hRns y hold
  · have : (objNode ⟨dt, on⟩ R).pred = c.predicate := by rw [hac, subjNode_pred]
    rw [objNode_pred, hcb c hc] at this
    exact hRne this

/-- Routed diff-fold reach inertness (post ⇒ pre) for `v ≠` the pass's R-node. -/
theorem reconcileKeyDR_reach_inert {σ0 : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands0 : List SubjectRef) (hRne : R ≠ BARE)
    {u v : NodeKey} (hv : v ≠ objNode ⟨dt, on⟩ R)
    (hcb0 : ∀ c ∈ cands0, c.predicate = BARE)
    (hRns0 : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ0.edges)
    (h0 : NReaches (σ0.reconcileKeyDR T dt on R e cands0).edges u v) :
    NReaches σ0.edges u v := by
  suffices H : ∀ (cs : List SubjectRef) (σ : GraphState),
      (∀ c ∈ cs, c.predicate = BARE) →
      (∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) →
      NReaches (σ.reconcileKeyDR T dt on R e cs).edges u v →
      NReaches σ.edges u v from H cands0 σ0 hcb0 hRns0 h0
  intro cs
  induction cs with
  | nil =>
    intro σ _ _ h
    exact h
  | cons c rest ih =>
    intro σ hcb hRns h
    rw [reconcileKeyDR_cons] at h
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

/-- Routed diff-fold reach preservation (pre ⇒ post) for `v ≠` the pass's R-node. -/
theorem reconcileKeyDR_reach_pres {σ0 : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands0 : List SubjectRef) (hRne : R ≠ BARE)
    {u v : NodeKey} (hv : v ≠ objNode ⟨dt, on⟩ R)
    (hcb0 : ∀ c ∈ cands0, c.predicate = BARE)
    (hRns0 : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ0.edges)
    (h0 : NReaches σ0.edges u v) :
    NReaches (σ0.reconcileKeyDR T dt on R e cands0).edges u v := by
  suffices H : ∀ (cs : List SubjectRef) (σ : GraphState),
      (∀ c ∈ cs, c.predicate = BARE) →
      (∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) →
      NReaches σ.edges u v →
      NReaches (σ.reconcileKeyDR T dt on R e cs).edges u v from H cands0 σ0 hcb0 hRns0 h0
  intro cs
  induction cs with
  | nil =>
    intro σ _ _ h
    exact h
  | cons c rest ih =>
    intro σ hcb hRns h
    rw [reconcileKeyDR_cons]
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

/-- The routed diffing fold preserves edge endpoint-closure. -/
theorem edgesClosed_reconcileKeyDR (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      (∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) →
      ∀ ab ∈ (σ.reconcileKeyDR T dt on R e cands).edges,
        ab.1 ∈ (σ.reconcileKeyDR T dt on R e cands).nodes
          ∧ ab.2 ∈ (σ.reconcileKeyDR T dt on R e cands).nodes := by
  intro cands
  induction cands with
  | nil => intro σ hcl; exact hcl
  | cons c rest ih =>
    intro σ hcl
    rw [reconcileKeyDR_cons]
    split
    · exact ih _ (edgesClosed_writeDirect hcl _)
    · exact ih _ (edgesClosed_removeEdgePair hcl _ _)

/-- **The routed pass leaves the UNTAINTED read of every subject unchanged** (the
    routed-pass analog of `graphRec_reconcileKeyD_inert`; the untainted key's probe
    targets are never the pass's derived R-node). -/
theorem graphRec_reconcileStarsKeyDR_inert {σ : GraphState} {S : Schema} (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef) (hRne : R ≠ BARE)
    (hcands : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (s : SubjectRef) (dt' on' r' : String) (hunt : isDerived S (dt', r') = false) :
    GraphModel.graphRec
        (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands uposCands) s dt' on' r'
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
  -- the residue half is edge/node-inert: transport the pass-start facts
  unfold GraphState.reconcileStarsKeyDR
  set σr := σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands with hσr
  have hE : σr.edges = σ.edges := by rw [hσr]; rfl
  have hN : σr.nodes = σ.nodes := by rw [hσr]; rfl
  have hRnsr : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σr.edges := by
    intro y
    rw [hE]
    exact hRns y
  have hclr : ∀ ab ∈ σr.edges, ab.1 ∈ σr.nodes ∧ ab.2 ∈ σr.nodes := by
    intro ab hab
    rw [hE] at hab
    rw [hN]
    exact hcl ab hab
  have hcl2 := edgesClosed_reconcileKeyDR T dt on R e cands σr hclr
  have hiff2 := GraphModel.probeNonDerived_iff hcl2 (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  have hiffr := GraphModel.probeNonDerived_iff hclr (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  have hpres1 : ∀ {u : NodeKey},
      NReaches σr.edges u (objNode ⟨dt', on'⟩ r') →
      NReaches (σr.reconcileKeyDR T dt on R e cands).edges u (objNode ⟨dt', on'⟩ r') :=
    fun hn => reconcileKeyDR_reach_pres T dt on R e cands hRne hvne1 hcands hRnsr hn
  have hpres3 : ∀ {u : NodeKey},
      NReaches σr.edges u (wAllNode dt' r') →
      NReaches (σr.reconcileKeyDR T dt on R e cands).edges u (wAllNode dt' r') :=
    fun hn => reconcileKeyDR_reach_pres T dt on R e cands hRne hvne3 hcands hRnsr hn
  have hinert1 : ∀ {u : NodeKey},
      NReaches (σr.reconcileKeyDR T dt on R e cands).edges u (objNode ⟨dt', on'⟩ r') →
      NReaches σr.edges u (objNode ⟨dt', on'⟩ r') :=
    fun hn => reconcileKeyDR_reach_inert T dt on R e cands hRne hvne1 hcands hRnsr hn
  have hinert3 : ∀ {u : NodeKey},
      NReaches (σr.reconcileKeyDR T dt on R e cands).edges u (wAllNode dt' r') →
      NReaches σr.edges u (wAllNode dt' r') :=
    fun hn => reconcileKeyDR_reach_inert T dt on R e cands hRne hvne3 hcands hRnsr hn
  -- the residue half itself is read-inert (edges/nodes untouched)
  have hbase : GraphModel.probeNonDerived σr (⟨s, r', ⟨dt', on'⟩⟩ : Query)
      = GraphModel.probeNonDerived σ (⟨s, r', ⟨dt', on'⟩⟩ : Query) :=
    probeNonDerived_congr hE hN _
  show GraphModel.probeNonDerived (σr.reconcileKeyDR T dt on R e cands)
      (⟨s, r', ⟨dt', on'⟩⟩ : Query) = GraphModel.probeNonDerived σ (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  rw [← hbase]
  cases hb2 : GraphModel.probeNonDerived (σr.reconcileKeyDR T dt on R e cands)
      (⟨s, r', ⟨dt', on'⟩⟩ : Query)
    <;> cases hb1 : GraphModel.probeNonDerived σr (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  · rfl
  · exfalso
    have hd := hiffr.mp hb1
    have : GraphModel.probeNonDerived (σr.reconcileKeyDR T dt on R e cands)
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
    have : GraphModel.probeNonDerived σr (⟨s, r', ⟨dt', on'⟩⟩ : Query) = true := by
      apply hiffr.mpr
      rcases hd with h1 | ⟨hs, h2⟩ | ⟨ho, h3⟩ | ⟨hs, ho, h4⟩
      · exact Or.inl (hinert1 h1)
      · exact Or.inr (Or.inl ⟨hs, hinert1 h2⟩)
      · exact Or.inr (Or.inr (Or.inl ⟨ho, hinert3 h3⟩))
      · exact Or.inr (Or.inr (Or.inr ⟨hs, ho, hinert3 h4⟩))
    rw [hb1] at this
    cases this
  · rfl

/-- **The routed pass leaves the DERIVED read at every OTHER key unchanged**: the
    residue write and every edge touch live at the pass's own R-node, and a
    different `(type, name, relation)` key owns a different node. -/
theorem probeDerived_reconcileStarsKeyDR_other {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef) (hRne : R ≠ BARE)
    (hcands : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) (honStar : on ≠ STAR)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (q : Query) (hne : ¬(q.object.type = dt ∧ q.object.name = on ∧ q.relation = R)) :
    GraphModel.probeDerived
        (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands uposCands) q
      = GraphModel.probeDerived σ q := by
  -- the queried object node is not the pass's R-node
  have hvne : objNode q.object q.relation ≠ objNode ⟨dt, on⟩ R := by
    intro heq
    by_cases hoStar : q.object.name = STAR
    · have hv := congrArg NodeKey.variant heq
      unfold objNode at hv
      rw [if_pos hoStar, if_neg honStar] at hv
      simp at hv
    · exact hne (objNode_inj_of_ne_star hoStar honStar heq)
  -- residue at the queried key is untouched
  have hres : (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands
        uposCands).residue (objNode q.object q.relation) q.relation
      = σ.residue (objNode q.object q.relation) q.relation :=
    reconcileStarsKeyDR_residue_other (fun hand => hvne hand.1)
  -- the bare-subject edge probe at the queried node is untouched (both directions)
  have hreach : (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands
        uposCands).reach (subjNode q.subject) (objNode q.object q.relation)
      = σ.reach (subjNode q.subject) (objNode q.object q.relation) := by
    unfold GraphState.reconcileStarsKeyDR
    set σr := σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands with hσr
    have hE : σr.edges = σ.edges := by rw [hσr]; rfl
    have hN : σr.nodes = σ.nodes := by rw [hσr]; rfl
    have hRnsr : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σr.edges := by
      intro y
      rw [hE]
      exact hRns y
    have hclr : ∀ ab ∈ σr.edges, ab.1 ∈ σr.nodes ∧ ab.2 ∈ σr.nodes := by
      intro ab hab
      rw [hE] at hab
      rw [hN]
      exact hcl ab hab
    have hcl2 := edgesClosed_reconcileKeyDR T dt on R e cands σr hclr
    have hbase : σr.reach (subjNode q.subject) (objNode q.object q.relation)
        = σ.reach (subjNode q.subject) (objNode q.object q.relation) := by
      unfold GraphState.reach
      rw [hE, hN]
    rw [← hbase]
    cases hb2 : (σr.reconcileKeyDR T dt on R e cands).reach (subjNode q.subject)
        (objNode q.object q.relation)
      <;> cases hb1 : σr.reach (subjNode q.subject) (objNode q.object q.relation)
    · rfl
    · exfalso
      have hn := reconcileKeyDR_reach_pres T dt on R e cands hRne hvne hcands hRnsr
        (reach_sound hb1)
      rw [reach_complete hcl2 hn] at hb2
      cases hb2
    · exfalso
      have hn := reconcileKeyDR_reach_inert T dt on R e cands hRne hvne hcands hRnsr
        (reach_sound hb2)
      rw [reach_complete hclr hn] at hb1
      cases hb1
    · rfl
  unfold GraphModel.probeDerived
  simp only [hres, hreach]

/-- **The routed leaf read is pass-inert off the pass's key** — `check` at any query
    whose `(type, name, relation)` key differs from the reconciled key is unchanged
    by a routed pass, whatever the queried key's stratum. The W3d-2 per-stratum
    inertness core. -/
theorem check_reconcileStarsKeyDR_other {σ : GraphState} {S : Schema} (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef)
    (hσS : σ.schema = S) (hRne : R ≠ BARE)
    (hcands : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (q : Query) (hne : ¬(q.object.type = dt ∧ q.object.name = on ∧ q.relation = R)) :
    GraphModel.check (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands
        uposCands) q
      = GraphModel.check σ q := by
  have hschema : (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands
      uposCands).schema = σ.schema := reconcileStarsKeyDR_schema σ T dt on R e shapes
    cands negCands uposCands
  cases hd : isDerived S (q.object.type, q.relation) with
  | false =>
    rw [GraphModel.check_untainted _ q (by rw [hschema, hσS]; exact hd),
      GraphModel.check_untainted σ q (by rw [hσS]; exact hd)]
    exact graphRec_reconcileStarsKeyDR_inert (S := S) T dt on R e shapes cands negCands
      uposCands hRne hcands hRns honStar hder hcl q.subject q.object.type q.object.name
      q.relation hd
  | true =>
    rw [GraphModel.check_derived _ q (by rw [hschema, hσS]; exact hd),
      GraphModel.check_derived σ q (by rw [hσS]; exact hd)]
    exact probeDerived_reconcileStarsKeyDR_other T dt on R e shapes cands negCands
      uposCands hRne hcands hRns honStar hcl q hne

/-- **Per-stratum guard stability**: the routed compiled guard of any def whose
    computed leaves all differ from the pass's key is constant across the pass —
    whatever the leaves' strata. (The W3d-2 analog of the `wantEdge` check half; a
    stratum-2 guard is perturbed only through the reconciled key itself.) -/
theorem checkFnR_reconcileStarsKeyDR_other {σ : GraphState} {S : Schema} (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef)
    (hσS : σ.schema = S) (hRne : R ≠ BARE)
    (hcands : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (s : SubjectRef) (dt' on' R' : String) (e' : Expr) (hco : ComputedOnly e')
    (hother : ∀ r' ∈ computedRefs e', ¬(dt' = dt ∧ on' = on ∧ r' = R)) :
    (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands uposCands).checkFnR
        T s dt' on' R' e'
      = σ.checkFnR T s dt' on' R' e' :=
  evalE_computedOnly e' hco (fun r' hr' =>
    check_reconcileStarsKeyDR_other T dt on R e shapes cands negCands uposCands hσS
      hRne hcands hRns honStar hder hcl ⟨s, r', ⟨dt', on'⟩⟩ (hother r' hr'))

end Zanzibar
