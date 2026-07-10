import ZanzibarProofs.GraphIndex.Reconcile
import ZanzibarProofs.GraphIndex.RulesWrite

/-!
# The derived reconcile — the WRITE model (ROADMAP W3a, write half)

`SEMANTICS.md` §7.6, §7.8; `index_v4/processor.py` (`reconcile` / `reconcile_subject`
/ `_EvalContext`). This is the write half of W3a (star-free, bare-subject derived
booleans), mirroring how W1b/W1c/W2 each landed a "write model DONE" increment before
the read correspondence.

## The processor's `check_fn` (`processor.py:43-56`, `410`)

`reconcile` computes, per candidate bare subject `s`, `should := check_fn(ctx, s)` and
maintains a derived edge `subjNode s → objNode ⟨dt,on⟩ R` iff `should ∧ ¬covered` (on
star-free data `covered` is always `false`, so `should` alone decides — §7.6, P4). The
compiled `check_fn` evaluates the boolean tree of the derived def; on the W3a fragment
(operands are `computed` references to **untainted** relations — a single stratum)
*every* leaf dispatches to `_EvalContext.leaf_check` = `widx.check` = the graph's
≤4-probe reachability read (`probeNonDerived`). So `check_fn` is exactly `evalE` with
the node-recursion `rec` reading the graph instead of the fuel recursion — see
`checkFn` below.

A derived edge is *structurally* an ordinary `writeDirect ⟨s, R, o⟩` (guarded,
cycle-rejecting, residue-untouched), so W3a reuses ALL of W2's `writeDirect` fold
machinery (`inv_foldl_writeDirect` etc.). The whole write model here is therefore a
guarded fold; its structural/`Inv`/residue-free/quiescence preservation is immediate.

**Deferred to the correspondence increment:** `checkFn σ s = sem`-membership of `s`
(via W1/W2 for the untainted operands + `evalE_congr`), and candidate-completeness
(every `sem`-member is enumerated) — together giving `probeDerived = sem` through the
W3a read collapse (`Reconcile.lean:probeDerived_residueEmpty`).
-/

namespace Zanzibar

namespace GraphModel

/-- **The graph's node-recursion oracle for `check_fn`.** `rec ot on' r'` = "is the
    fixed subject `s` a member of `(ot, on', r')` in the graph", read by the
    non-derived ≤4-probe (`probeNonDerived`). On the W3a fragment the boolean
    operands are `computed` references to untainted relations, whose graph read is
    exactly this probe (= `sem` by W1/W2, the correspondence increment's lemma). -/
def graphRec (σ : GraphState) (s : SubjectRef) : Rec :=
  fun ot on' r' => probeNonDerived σ ⟨s, r', ⟨ot, on'⟩⟩

end GraphModel

/-- **The compiled `check_fn`, modelled.** Evaluate the derived def `e` on the fixed
    bare subject `s` at object `(dt, on)` under relation `R`, with node-recursion
    reading the graph (`graphRec`). Faithful to `reconcile`'s per-subject boolean
    evaluation on the W3a fragment (`processor.py:410`, `check_fn(ctx, (pred,type,
    name))`). The store `T`/query are threaded only for `evalE`'s `direct`/`ttu`
    leaves, which do not occur on the fragment. -/
def GraphState.checkFn (σ : GraphState) (T : Store) (s : SubjectRef)
    (dt on R : String) (e : Expr) : Bool :=
  evalE (GraphModel.graphRec σ s) s T ⟨s, R, ⟨dt, on⟩⟩ dt on R e

/-- **Reconcile one derived key `(dt, R)` at object name `on`.** For each candidate
    bare subject in `cands`, materialise the derived edge `subjNode s → objNode
    ⟨dt,on⟩ R` **iff** `check_fn` holds — the canonical `reconcile_subject` rule
    (`want_edge = should ∧ ¬covered`, `covered = false` on star-free data). Residues
    stay untouched (empty on W3a). Faithful mechanism: a guarded `writeDirect` fold. -/
def GraphState.reconcileKey (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (cands : List SubjectRef) : GraphState :=
  cands.foldl
    (fun acc s => if acc.checkFn T s dt on R e then acc.writeDirect ⟨s, R, ⟨dt, on⟩⟩ else acc)
    σ

/-! ## Preservation — the guarded fold preserves everything `writeDirect` does -/

/-- The guarded reconcile fold preserves `StructInv` (each step is `writeDirect` or
    the identity). -/
theorem structInv_reconcileKey {S : Schema} {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) (h : StructInv S σ) :
    StructInv S (σ.reconcileKey T dt on R e cands) := by
  unfold GraphState.reconcileKey
  induction cands generalizing σ with
  | nil => exact h
  | cons s rest ih =>
    simp only [List.foldl_cons]
    by_cases hc : σ.checkFn T s dt on R e = true
    · rw [if_pos hc]; exact ih (structInv_writeDirect h _)
    · rw [if_neg hc]; exact ih h

/-- The guarded reconcile fold preserves residue-freeness. -/
theorem residueEmpty_reconcileKey {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) (h : ResidueEmpty σ) :
    ResidueEmpty (σ.reconcileKey T dt on R e cands) := by
  unfold GraphState.reconcileKey
  induction cands generalizing σ with
  | nil => exact h
  | cons s rest ih =>
    simp only [List.foldl_cons]
    by_cases hc : σ.checkFn T s dt on R e = true
    · rw [if_pos hc]; exact ih (residueEmpty_writeDirect _ h)
    · rw [if_neg hc]; exact ih h

/-- The guarded reconcile fold preserves the full `Inv` on the residue-free
    fragment — W3a's T2a `Inv` conjunct, proved by folding `inv_writeDirect`. -/
theorem inv_reconcileKey {S : Schema} {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef)
    (h : Inv S σ) (hre : ResidueEmpty σ) :
    Inv S (σ.reconcileKey T dt on R e cands) := by
  unfold GraphState.reconcileKey
  induction cands generalizing σ with
  | nil => exact h
  | cons s rest ih =>
    simp only [List.foldl_cons]
    by_cases hc : σ.checkFn T s dt on R e = true
    · rw [if_pos hc]
      exact ih (inv_writeDirect h hre _) (residueEmpty_writeDirect _ hre)
    · rw [if_neg hc]; exact ih h hre

/-- The guarded reconcile fold preserves cascade-quiescence. -/
theorem quiescent_reconcileKey {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) (h : Quiescent σ) :
    Quiescent (σ.reconcileKey T dt on R e cands) := by
  unfold GraphState.reconcileKey
  induction cands generalizing σ with
  | nil => exact h
  | cons s rest ih =>
    simp only [List.foldl_cons]
    by_cases hc : σ.checkFn T s dt on R e = true
    · rw [if_pos hc]; exact ih (quiescent_writeDirect h _)
    · rw [if_neg hc]; exact ih h

/-! ## The W3a operational write-closure -/

/-- **`ReachedByW3a σ S T`** — `σ` is reached by first materialising `T`'s untainted
    structure (W2's `ReachedByRules`) and then any number of derived-key reconcile
    passes (`reconcileKey`). The star-free bare-subject derived-boolean closure; it
    stays residue-free (derived relations only add edges on W3a), so `probeDerived`
    collapses to the edge probe (`Reconcile.lean`). The base leg pins the untainted
    edges to the store; each reconcile leg adds `check_fn`-selected derived edges.

    The reconcile leg carries `hder : isDerived S (dt, R) = true` — faithful, reconcile
    only ever runs on a declared *derived* relation. It is the fact that separates a
    reconciled derived key from an untainted operand key of the same object type (equal
    keys share `isDerived`), so a reconcile edge is reachability-inert for the untainted
    operand reads the correspondence's `hag` consults (`reachedByW3a_reach_inert`).

    The star-freeness side conditions `hcStar` (each candidate subject star-free) and
    `honStar` (the reconciled object name star-free) are faithful to the W3a star-free
    fragment: reconcile candidates are the `_leaf_concretes` (concrete bare subjects) and it
    runs per concrete object. They keep every reconcile edge's endpoints *plain*
    (`reachedByW3a_edges_plain`), so the wildcard probes 2–4 stay dead on the operand read. -/
inductive ReachedByW3a : GraphState → Schema → Store → Prop where
  | base {σ : GraphState} {S : Schema} {T : Store} :
      ReachedByRules σ S T → ReachedByW3a σ S T
  | reconcile {σ : GraphState} {S : Schema} {T : Store}
      (dt on R : String) (e : Expr) (cands : List SubjectRef) (hRne : R ≠ BARE)
      (hcands : ∀ c ∈ cands, c.predicate = BARE)
      (hder : isDerived S (dt, R) = true)
      (hcStar : ∀ c ∈ cands, c.name ≠ STAR) (honStar : on ≠ STAR) :
      ReachedByW3a σ S T → ReachedByW3a (σ.reconcileKey T dt on R e cands) S T

/-- **T2a for the W3a fragment.** Every state reached by W3a writes satisfies the
    full I-series invariant, stays residue-free, and is cascade-quiescent — by
    induction over the concrete write path (untainted rule routing + reconcile
    passes), never postulated. The residue-free conjunct is what makes the derived
    read collapse to the edge probe (`probeDerived_ResidueEmpty`). -/
theorem reachedByW3a_inv {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3a σ S T) : Inv S σ ∧ ResidueEmpty σ ∧ Quiescent σ := by
  induction h with
  | base hr => exact reachedByRules_inv hr
  | reconcile dt on R e cands _hRne _hcands _hder _hcStar _honStar _ ih =>
    obtain ⟨hInv, hRe, hQ⟩ := ih
    exact ⟨inv_reconcileKey _ dt on R e cands hInv hRe,
      residueEmpty_reconcileKey _ dt on R e cands hRe,
      quiescent_reconcileKey _ dt on R e cands hQ⟩

/-- The W3a closure is residue-free — so `check` on any derived relation collapses to
    the bare edge probe (`check_derived_ResidueEmpty`). The load-bearing consequence
    of `reachedByW3a_inv` for the read side. -/
theorem reachedByW3a_residueEmpty {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3a σ S T) : ResidueEmpty σ :=
  (reachedByW3a_inv h).2.1

end Zanzibar
