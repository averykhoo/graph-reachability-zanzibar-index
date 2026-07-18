import ZanzibarProofs.GraphIndex.CascadeInv
import ZanzibarProofs.GraphIndex.CascadeStrataAssemble

/-!
# W4 T2a groundwork — `StructInv`, edge-free I6, and row declaredness over the
TWO-ROUND chain

`CascadeInv.lean` proved the full 8-clause `Inv` over the W3d-1 chain. W4 needs it
over the OPERATIONAL closure `ReachedBy := ReachedByW3d2E` (`FullScope.lean`). This
file ports the three fragment-free layers to the two-round chains
(`ReachedByW3d2` / `ReachedByW3d2C` / `ReachedByW3d2E`):

* **`StructInv`** through the ROUTED pass and `runCascade2` — the routed guard swap
  (`checkFnR` for `checkFn`) never changes which structural fields a fold branch
  touches (`writeDirect` / `removeEdgePair`, both preserving), so the proofs are
  the W3d-1 ones with routed rewrite lemmas.
* **`ResidueHygienic`** (the edge-free I6 clauses `negStarCovered` /
  `uposNegDisjoint`) — the routed residue write has the same filter structure
  (`reconcileResidueKeyR_residue_self`), so hygiene is guard-independent.
* **`ResidueDeclared`** (row-key declaredness) — over `ReachedByW3d2` from the
  chain's own `W3cJobValid`; over `ReachedByW3d2E` HYPOTHESIS-FREE, because the
  enumerated jobs' keys come from `cascadeKeysAbove` (`mem_cascadeKeysAbove_props`)
  with the def looked up by the enumeration itself (`enumJobs2At_keyFacts`).

The remaining W4 T2a piece — the two EDGE-referencing I6 clauses
(`negEdgeFree`/`uposEdgeFree`) over `ReachedByW3d2C` — mirrors
`reachedByW3dC_edgeHygienic` (targeted keys via `settledComplete_cascade2_targeted`,
untargeted via routed other-key fixedness, write legs via
`writeLeg_derived_inedges_eq` + the W3d2 reach collapse) and is tracked in ROADMAP
W4 item 4.
-/

namespace Zanzibar

/-! ## `StructInv` through the routed pass -/

/-- The routed residue recompute is residue-only, so it preserves `StructInv`. -/
theorem structInv_reconcileResidueKeyR {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (T : Store) (dt on R : String) (e : Expr) (shapes : List Shape)
    (negCands uposCands : List SubjectRef) :
    StructInv S (σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands) where
  schemaEq := by rw [reconcileResidueKeyR_schema]; exact h.schemaEq
  nodeEnc := by rw [reconcileResidueKeyR_nodes]; exact h.nodeEnc
  edgesClosed := by
    rw [reconcileResidueKeyR_edges, reconcileResidueKeyR_nodes]; exact h.edgesClosed
  acyclic := by rw [reconcileResidueKeyR_edges]; exact h.acyclic

/-- The routed diffing edge audit preserves the structural invariant — each fold
    step is a `writeDirect` or a `removeEdgePair`, whatever the guard says. -/
theorem structInv_reconcileKeyDR {S : Schema} (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) {σ : GraphState}, StructInv S σ →
      StructInv S (σ.reconcileKeyDR T dt on R e cands) := by
  intro cands
  induction cands with
  | nil => intro σ h; exact h
  | cons c rest ih =>
    intro σ h
    rw [reconcileKeyDR_cons]
    split
    · exact ih (structInv_writeDirect h _)
    · exact ih (structInv_removeEdgePair h _ _)

/-- One full-object ROUTED reconcile preserves `StructInv`. -/
theorem structInv_reconcileStarsKeyDR {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (T : Store) (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef) :
    StructInv S (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands uposCands) := by
  unfold GraphState.reconcileStarsKeyDR
  exact structInv_reconcileKeyDR T dt on R e cands
    (structInv_reconcileResidueKeyR h T dt on R e shapes negCands uposCands)

/-- One logged routed reconcile job preserves `StructInv`. -/
theorem structInv_applyLoggedR {S : Schema} {σ : GraphState} (h : StructInv S σ)
    (T : Store) (j : W3cJob) : StructInv S (j.applyLoggedR S T σ) := by
  unfold W3cJob.applyLoggedR W3cJob.applyDR
  exact structInv_pushDelta
    (structInv_reconcileStarsKeyDR h T j.dt j.on j.R j.e (wildcardShapes S)
      j.cands j.negCands j.uposCands) _ _

/-- A batch of logged routed jobs preserves `StructInv`. -/
theorem structInv_reconcileJobsLR {S : Schema} (T : Store) :
    ∀ (jobs : List W3cJob) {σ : GraphState}, StructInv S σ →
      StructInv S (reconcileJobsLR S T σ jobs) := by
  intro jobs
  induction jobs with
  | nil => intro σ h; exact h
  | cons j rest ih =>
    intro σ h
    unfold reconcileJobsLR
    rw [List.foldl_cons]
    exact ih (structInv_applyLoggedR h T j)

/-- **A whole two-round cascade run preserves `StructInv`** — accept branch = two
    routed batches + a watermark bump; reject branch = identity. -/
theorem structInv_runCascade2 {S : Schema} {T : Store} {σ : GraphState}
    (h : StructInv S σ) (jobs1 jobs2 : List W3cJob) :
    StructInv S (runCascade2 S T σ jobs1 jobs2) := by
  unfold runCascade2
  split
  · exact structInv_setWatermark
      (structInv_reconcileJobsLR T jobs2 (structInv_reconcileJobsLR T jobs1 h)) _
  · exact h

/-! ## The retraction is residue-inert — the T2a Group-A remove-case substrate (R5 pre-discharge)

The logged rule-routed retraction `removeLoggedRules` touches ONLY the edge multiset (via
`removeEdgeOne`) and the outbox (via `pushDelta`); it never writes a `residue` row. So the
STRUCTURAL invariant clauses that read only `residue` (`ResidueHygienic`, `ResidueDeclared`)
transport verbatim across a retraction. -/

/-- One logged retraction leaves the residue map untouched (`removeEdgeOne`/`pushDelta` are
    both residue-inert). -/
@[simp] theorem removeLoggedOne_residue (σ : GraphState) (t : Tuple) :
    (σ.removeLoggedOne t).residue = σ.residue := by
  unfold GraphState.removeLoggedOne
  by_cases hmem : (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges
  · rw [if_pos hmem, pushDelta_residue, removeEdgeOne_residue]
  · rw [if_neg hmem]

/-- The logged rule-routed retraction leaves the residue map untouched (fold of the above). -/
theorem removeLoggedRules_residue (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.removeLoggedRules S t).residue = σ.residue := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosure S t = us
  induction us generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih (σ.removeLoggedOne u), removeLoggedOne_residue]

/-- **`ResidueHygienic` survives a retraction** (both clauses read only `residue`, which is
    inert). The R5 `reachedByW3d2E_residueHygienic` remove-case discharge. -/
theorem residueHygienic_removeLoggedRules {σ : GraphState} (S : Schema) (t : Tuple)
    (h : ResidueHygienic σ) : ResidueHygienic (σ.removeLoggedRules S t) := by
  obtain ⟨h1, h2⟩ := h
  refine ⟨fun k r res hrow n hn => ?_, fun k r res hrow n hn => ?_⟩
  · rw [removeLoggedRules_residue] at hrow; exact h1 k r res hrow n hn
  · rw [removeLoggedRules_residue] at hrow; exact h2 k r res hrow n hn

/-- **`ResidueDeclared` survives a retraction** (reads only `residue`). The R5
    `reachedByW3d2E_residueDeclared` remove-case discharge. -/
theorem residueDeclared_removeLoggedRules {σ : GraphState} (S : Schema) (t : Tuple)
    (h : ResidueDeclared S σ) : ResidueDeclared S (σ.removeLoggedRules S t) := by
  intro k r res hrow
  rw [removeLoggedRules_residue] at hrow
  exact h k r res hrow

/-- **T2a structural half over the two-round chain** — schema fixity, node
    encoding, edge endpoint-closure, acyclicity at EVERY `ReachedByW3d2` state,
    with NO fragment hypotheses. -/
theorem reachedByW3d2_structInv {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) : StructInv S σ := by
  induction h with
  | empty S => exact structInv_empty S
  | write t hadm hprev ih => exact structInv_writeLoggedRules ih t
  | remove t _ _ _ _ _ _ _ ih => exact structInv_removeLoggedRules ih t
  | cascade jobs1 jobs2 _ _ _ _ _ _ _ ih => exact structInv_runCascade2 ih jobs1 jobs2

/-- The two-round coverage chain inherits the structural invariant. -/
theorem reachedByW3d2C_structInv {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2C σ S T) : StructInv S σ :=
  reachedByW3d2_structInv (reachedByW3d2C_toW3d2 h)

/-- **The structural invariant over the OPERATIONAL closure** (`ReachedByW3d2E` =
    W4's `ReachedBy`), hypothesis-free — by direct induction (the preservation
    lemmas are jobs-generic, so the enumerated legs need no validity facts). -/
theorem reachedByW3d2E_structInv {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T) : StructInv S σ := by
  induction h with
  | empty S => exact structInv_empty S
  | write t hadm hprev ih => exact structInv_writeLoggedRules ih t
  | remove t _ _ _ _ _ _ _ ih => exact structInv_removeLoggedRules ih t
  | cascade hprev ih => exact structInv_runCascade2 ih _ _

/-! ## The edge-free I6 clauses through the routed pass -/

/-- **The ROUTED residue recompute writes a hygienic row** — same filter structure
    as the W3d-1 pass (`neg` demands star coverage, `upos` its negation), so the
    two edge-free clauses are guard-independent. -/
theorem residueHygienic_reconcileStarsKeyDR {σ : GraphState} (h : ResidueHygienic σ)
    (T : Store) (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef) :
    ResidueHygienic (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands uposCands) := by
  obtain ⟨hns, hun⟩ := h
  constructor
  · intro k r res hrow n hn
    by_cases hkey : k = objNode ⟨dt, on⟩ R ∧ r = R
    · obtain ⟨hk, hr⟩ := hkey
      unfold GraphState.reconcileStarsKeyDR at hrow
      rw [hk, hr, reconcileKeyDR_residue, reconcileResidueKeyR_residue_self] at hrow
      obtain rfl := Option.some.inj hrow
      have hcond := (List.mem_filter.mp hn).2
      simp only [Bool.and_eq_true] at hcond
      exact hcond.1
    · rw [reconcileStarsKeyDR_residue_other hkey] at hrow
      exact hns k r res hrow n hn
  · intro k r res hrow n hn
    by_cases hkey : k = objNode ⟨dt, on⟩ R ∧ r = R
    · obtain ⟨hk, hr⟩ := hkey
      unfold GraphState.reconcileStarsKeyDR at hrow
      rw [hk, hr, reconcileKeyDR_residue, reconcileResidueKeyR_residue_self] at hrow
      set stars := shapes.filter (fun sh => σ.coveredFnR T dt on R e sh) with hstdef
      set neg := negCands.filter
        (fun c => stars.contains c.shape && !(σ.checkFnR T c dt on R e)) with hnegdef
      obtain rfl := Option.some.inj hrow
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
    · rw [reconcileStarsKeyDR_residue_other hkey] at hrow
      exact hun k r res hrow n hn

/-- One logged routed job preserves residue hygiene. -/
theorem residueHygienic_applyLoggedR {S : Schema} {σ : GraphState} (h : ResidueHygienic σ)
    (T : Store) (j : W3cJob) : ResidueHygienic (j.applyLoggedR S T σ) := by
  unfold W3cJob.applyLoggedR W3cJob.applyDR
  exact residueHygienic_pushDelta
    (residueHygienic_reconcileStarsKeyDR h T j.dt j.on j.R j.e (wildcardShapes S)
      j.cands j.negCands j.uposCands) _ _

/-- A batch of logged routed jobs preserves residue hygiene. -/
theorem residueHygienic_reconcileJobsLR {S : Schema} (T : Store) :
    ∀ (jobs : List W3cJob) {σ : GraphState}, ResidueHygienic σ →
      ResidueHygienic (reconcileJobsLR S T σ jobs) := by
  intro jobs
  induction jobs with
  | nil => intro σ h; exact h
  | cons j rest ih =>
    intro σ h
    unfold reconcileJobsLR
    rw [List.foldl_cons]
    exact ih (residueHygienic_applyLoggedR h T j)

/-- A whole two-round cascade run preserves residue hygiene. -/
theorem residueHygienic_runCascade2 {S : Schema} {T : Store} {σ : GraphState}
    (h : ResidueHygienic σ) (jobs1 jobs2 : List W3cJob) :
    ResidueHygienic (runCascade2 S T σ jobs1 jobs2) := by
  unfold runCascade2
  split
  · exact residueHygienic_setWatermark
      (residueHygienic_reconcileJobsLR T jobs2 (residueHygienic_reconcileJobsLR T jobs1 h)) _
  · exact h

/-- **The edge-free I6 clauses at every two-round chain state**, fragment-free. -/
theorem reachedByW3d2_residueHygienic {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) : ResidueHygienic σ := by
  induction h with
  | empty S => exact residueHygienic_empty S
  | write t hadm hprev ih => exact residueHygienic_writeLoggedRules ih t
  | @remove σp S T t _ _ _ _ _ _ _ ih => exact residueHygienic_removeLoggedRules S t ih
  | cascade jobs1 jobs2 _ _ _ _ _ _ _ ih => exact residueHygienic_runCascade2 ih jobs1 jobs2

/-- The two-round coverage chain inherits residue hygiene. -/
theorem reachedByW3d2C_residueHygienic {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2C σ S T) : ResidueHygienic σ :=
  reachedByW3d2_residueHygienic (reachedByW3d2C_toW3d2 h)

/-- **Residue hygiene over the OPERATIONAL closure**, hypothesis-free (direct
    induction; the preservation lemmas are jobs-generic). -/
theorem reachedByW3d2E_residueHygienic {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T) : ResidueHygienic σ := by
  induction h with
  | empty S => exact residueHygienic_empty S
  | write t hadm hprev ih => exact residueHygienic_writeLoggedRules ih t
  | @remove σp S T t _ _ _ _ _ _ _ ih => exact residueHygienic_removeLoggedRules S t ih
  | cascade hprev ih => exact residueHygienic_runCascade2 ih _ _

/-! ## Row-key declaredness over the two-round chains -/

/-- The key facts `ResidueDeclared` needs of a job: its def is looked up, derived,
    and its object concrete — the last three conjuncts of `W3cJobValid`. -/
def W3cJobKeyFacts (S : Schema) (j : W3cJob) : Prop :=
  S.lookup (j.dt, j.R) = some j.e ∧ isDerived S (j.dt, j.R) = true ∧ j.on ≠ STAR

theorem w3cJobKeyFacts_of_valid {S : Schema} {j : W3cJob} (h : W3cJobValid S j) :
    W3cJobKeyFacts S j := by
  obtain ⟨_, _, _, _, _, _, hder, hlk, hon⟩ := h
  exact ⟨hlk, hder, hon⟩

/-- One logged routed job preserves row-key declaredness: it writes only its own
    (declared, derived, concrete) key's row. -/
theorem residueDeclared_applyLoggedR {S : Schema} {σ : GraphState} (T : Store)
    {j : W3cJob} (hj : W3cJobKeyFacts S j) (h : ResidueDeclared S σ) :
    ResidueDeclared S (j.applyLoggedR S T σ) := by
  intro k r res hrow
  unfold W3cJob.applyLoggedR W3cJob.applyDR at hrow
  rw [pushDelta_residue] at hrow
  by_cases hkey : k = objNode ⟨j.dt, j.on⟩ j.R ∧ r = j.R
  · exact ⟨j.dt, j.on, j.R, j.e, hkey.1, hkey.2, hj.1, hj.2.1, hj.2.2⟩
  · rw [reconcileStarsKeyDR_residue_other hkey] at hrow
    exact h k r res hrow

/-- A batch of key-fact jobs preserves row-key declaredness. -/
theorem residueDeclared_reconcileJobsLR {S : Schema} (T : Store) :
    ∀ (jobs : List W3cJob), (∀ j ∈ jobs, W3cJobKeyFacts S j) → ∀ {σ : GraphState},
      ResidueDeclared S σ → ResidueDeclared S (reconcileJobsLR S T σ jobs) := by
  intro jobs
  induction jobs with
  | nil => intro _ σ h; exact h
  | cons j rest ih =>
    intro hjf σ h
    unfold reconcileJobsLR
    rw [List.foldl_cons]
    exact ih (fun j' hj' => hjf j' (List.mem_cons_of_mem _ hj'))
      (residueDeclared_applyLoggedR T (hjf j List.mem_cons_self) h)

/-- A two-round cascade of key-fact jobs preserves row-key declaredness. -/
theorem residueDeclared_runCascade2 {S : Schema} {T : Store} {σ : GraphState}
    {jobs1 jobs2 : List W3cJob} (hjf1 : ∀ j ∈ jobs1, W3cJobKeyFacts S j)
    (hjf2 : ∀ j ∈ jobs2, W3cJobKeyFacts S j) (h : ResidueDeclared S σ) :
    ResidueDeclared S (runCascade2 S T σ jobs1 jobs2) := by
  rcases runCascade2_cases S T σ jobs1 jobs2 with hrc | hrc
  · rw [hrc]
    intro k r res hrow
    exact residueDeclared_reconcileJobsLR T jobs2 hjf2
      (residueDeclared_reconcileJobsLR T jobs1 hjf1 h) k r res hrow
  · rw [hrc]; exact h

/-- **Row-key declaredness at every two-round chain state** — the chain's own
    `W3cJobValid` supplies the key facts. -/
theorem reachedByW3d2_residueDeclared {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2 σ S T) : ResidueDeclared S σ := by
  induction h with
  | empty S =>
    intro k r res hrow
    simp [emptyState] at hrow
  | write t hadm hprev ih =>
    intro k r res hrow
    rw [writeLoggedRules_residue] at hrow
    exact ih k r res hrow
  | @remove σp S T t _ _ _ _ _ _ _ ih => exact residueDeclared_removeLoggedRules S t ih
  | cascade jobs1 jobs2 hjv1 hjv2 _ _ _ _ _ ih =>
    exact residueDeclared_runCascade2
      (fun j hj => w3cJobKeyFacts_of_valid (hjv1 j hj))
      (fun j hj => w3cJobKeyFacts_of_valid (hjv2 j hj)) ih

/-- The two-round coverage chain inherits row-key declaredness. -/
theorem reachedByW3d2C_residueDeclared {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2C σ S T) : ResidueDeclared S σ :=
  reachedByW3d2_residueDeclared (reachedByW3d2C_toW3d2 h)

/-- The enumerated jobs carry their key facts BY CONSTRUCTION: the key list is
    `cascadeKeysAbove` (derived + declared + concrete, `mem_cascadeKeysAbove_props`)
    and the enumeration looks the def up itself. -/
theorem enumJobs2At_keyFacts {S : Schema} {σe : GraphState}
    {keys : List (String × String × String)}
    (hk : ∀ k ∈ keys, isDerived S (k.1, k.2.1) = true ∧ k.2.2 ≠ STAR) :
    ∀ j ∈ enumJobs2At S σe keys, W3cJobKeyFacts S j := by
  intro j hj
  unfold enumJobs2At at hj
  obtain ⟨k, hkmem, hjk⟩ := List.mem_filterMap.mp hj
  cases hlk : S.lookup (k.1, k.2.1) with
  | none => rw [hlk] at hjk; cases hjk
  | some e =>
    rw [hlk] at hjk
    obtain rfl := Option.some.inj hjk
    obtain ⟨hder, hne⟩ := hk k hkmem
    exact ⟨hlk, hder, hne⟩

/-- **Row-key declaredness over the OPERATIONAL closure, hypothesis-free** — the
    enumerated rounds' key facts come from the state, not from chain-side validity. -/
theorem reachedByW3d2E_residueDeclared {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T) : ResidueDeclared S σ := by
  induction h with
  | empty S =>
    intro k r res hrow
    simp [emptyState] at hrow
  | write t hadm hprev ih =>
    intro k r res hrow
    rw [writeLoggedRules_residue] at hrow
    exact ih k r res hrow
  | @remove σp S T t _ _ _ _ _ _ _ ih => exact residueDeclared_removeLoggedRules S t ih
  | @cascade σp S T hprev ih =>
    exact residueDeclared_runCascade2
      (enumJobs2At_keyFacts (fun k hk =>
        ⟨(mem_cascadeKeysAbove_props hk).1, (mem_cascadeKeysAbove_props hk).2.2⟩))
      (enumJobs2At_keyFacts (fun k hk =>
        ⟨(mem_cascadeKeysAbove_props hk).1, (mem_cascadeKeysAbove_props hk).2.2⟩)) ih

/-! ## Pass-local I6 — the routed pass writes an EDGE-CONSISTENT row

The core of the remaining W4 T2a piece (the edge-referencing clauses
`negEdgeFree`/`uposEdgeFree`). KEY DESIGN SHIFT vs the W3d-1 proof
(`reachedByW3dC_edgeHygienic`): that proof went through the coverage chain's
settled verdicts, because over `ReachedByW3dC`'s ARBITRARY covered jobs a `neg`
candidate need not be audited by the edge fold. Over the OPERATIONAL closure the
enumerated jobs audit their own residue candidates BY CONSTRUCTION
(`enumJob2.negCands ⊆ enumJob2.cands`, below) — so the row and the edges written
by ONE pass are mutually consistent whatever the guard said, settled or STALE.
This is what makes the E-chain edge hygiene provable at re-dirtied round-1 keys
(the 12h attack shape), where `SettledKey` is simply unavailable:

* a `neg` member failed the guard at pass-start, and — being a candidate — had
  its edge audited against THAT guard (`reconcileStarsKeyDR_edge_char`), so no
  edge survives;
* a `upos` member is userset-shaped (`W3cJobValid`), while candidates and
  pre-pass in-edge sources at the R-node are bare — so it can hold no edge.

The batch/chain assembly (prefix-state transports of `hRns`/`hcl`/`hsb`, the
other-key fixedness walk, and the write legs) is the next-session item. -/

/-- **Pass-local I6.** The row a routed pass writes at its own key is
    edge-consistent with the pass's own edge audit — at the POST-pass state, no
    `neg`/`upos` member holds an edge into the key. Hypotheses are the
    `reconcileStarsKeyDR_edge_char` context plus the two candidate-discipline
    facts (`hnc` : residue candidates are audited; `hup` : upos candidates are
    userset-shaped) and pre-pass source-bareness (`hsb`). -/
theorem reconcileStarsKeyDR_row_edge_consistent {S : Schema} {σ : GraphState}
    (T : Store) (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef)
    (hσS : σ.schema = S) (hRne : R ≠ BARE) (honStar : on ≠ STAR)
    (hder : isDerived S (dt, R) = true) (hco : ComputedOnly e)
    (hrne : ∀ r' ∈ computedRefs e, r' ≠ R)
    (hcb : ∀ c ∈ cands, c.predicate = BARE)
    (hnc : ∀ c ∈ negCands, c ∈ cands)
    (hup : ∀ c ∈ uposCands, c.predicate ≠ BARE)
    (hsb : ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) :
    ∀ res, (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands
        uposCands).residue (objNode ⟨dt, on⟩ R) R = some res →
      (∀ n ∈ res.neg, (subjNode n, objNode ⟨dt, on⟩ R)
          ∉ (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands
              uposCands).edges) ∧
      (∀ n ∈ res.upos, (subjNode n, objNode ⟨dt, on⟩ R)
          ∉ (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands
              uposCands).edges) := by
  intro res hrow
  have hrow' : res = ⟨shapes.filter (fun sh => σ.coveredFnR T dt on R e sh),
      negCands.filter (fun c =>
        (shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)).contains c.shape
          && !(σ.checkFnR T c dt on R e)),
      uposCands.filter (fun c =>
        !((shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)).contains c.shape)
          && σ.checkFnR T c dt on R e)⟩ := by
    unfold GraphState.reconcileStarsKeyDR at hrow
    rw [reconcileKeyDR_residue, reconcileResidueKeyR_residue_self] at hrow
    exact (Option.some.inj hrow).symm
  subst hrow'
  constructor
  · intro n hn hedge
    obtain ⟨hnmem, hncond⟩ := List.mem_filter.mp hn
    simp only [Bool.and_eq_true] at hncond
    have hguardF : σ.checkFnR T n dt on R e = false := by
      have := hncond.2
      cases hc : σ.checkFnR T n dt on R e with
      | false => rfl
      | true => rw [hc] at this; exact absurd this (by decide)
    rcases (reconcileStarsKeyDR_edge_char T dt on R e shapes cands negCands
        uposCands hσS hRne honStar hder hco hrne hcb hRns hcl n).mp hedge with
      ⟨_, hg⟩ | ⟨hnotc, _⟩
    · rw [hguardF] at hg
      simp at hg
    · exact hnotc (hnc n hnmem)
  · intro n hn hedge
    obtain ⟨hnmem, _⟩ := List.mem_filter.mp hn
    rcases (reconcileStarsKeyDR_edge_char T dt on R e shapes cands negCands
        uposCands hσS hRne honStar hder hco hrne hcb hRns hcl n).mp hedge with
      ⟨hc, _⟩ | ⟨_, hold⟩
    · exact hup n hnmem (hcb n hc)
    · have := hsb (subjNode n) hold
      rw [subjNode_pred] at this
      exact hup n hnmem this

/-- The enumerated job audits its own residue candidates: `negCands ⊆ cands` (the
    bare base list is the left summand of `cands`) — the E-chain discharge of
    `hnc` above. -/
theorem enumJob2_negCands_subset (σ : GraphState) (dt on R : String) (e : Expr) :
    ∀ c ∈ (enumJob2 σ dt on R e).negCands, c ∈ (enumJob2 σ dt on R e).cands := by
  intro c hc
  show c ∈ (enum2Base σ dt on e).filter (fun u => u.predicate == BARE)
    ++ edgeHolders σ dt on R
  exact List.mem_append_left _ hc

end Zanzibar
