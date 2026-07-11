import ZanzibarProofs.FullScope

/-!
# The executable graph-model driver (Phase 6 — graph-state conformance)

`HANDOFF.md` Phase 6 item 1. The conformance CLI needs to RUN the operational
graph model — the very object `graph_correct` quantifies over — on a corpus of
writes and answer `check` queries, so the Python harness can diff the Lean model
against the real Python graph index (`index_v4`/`WildcardIndex`).

This file is the driver plus its **honesty theorems**: the driver is not a second
model, it is a fold of the CHAIN'S OWN constructors, and that is a theorem —

* `foldAdmitsB` — executable mirror of the `FoldAdmits` admission predicate;
  `foldAdmitsB_iff` pins them together, so the driver errors exactly where the
  chain has no `write` constructor (a cycle-rejected write: the composed system
  rolls back, decision 6 — the model is add-only, accepted-writes-only).
* `cascadeLeg` — one fully-operational cascade leg, verbatim the `cascade`
  constructor's target (`runCascade2` over the state-derived `enumJobs2R1`/`R2`).
* `graphRun` — write leg + cascade leg per input tuple (the synchronous v1
  Python write path: `advance_index` → `DeltaProcessor.run_cascade` in the same
  transaction, `tests/test_matrix.py` `GraphBackend.apply`).
* **`graphRun_reached`** — anything the driver outputs IS an operationally
  reached state: `graphRun S ts = some (σ, T) → ReachedBy σ S T`.
* `drainedB` / `drainedB_iff` — the executable fully-drained check the CLI
  gates its output on (mid-drain reads are honestly stale — the 12h attack).
* **`graphRun_check_eq_sem`** — the capstone: under the W4 bundles, every
  verdict the CLI's graph mode prints for an in-scope query IS `sem`. The CLI
  output is covered by `graph_correct` verbatim, not by analogy.
-/

namespace Zanzibar

/-! ## The executable admission check -/

/-- Executable mirror of `FoldAdmits` (`RulesComplete.lean:54`): every write in
    the `writeDirect` fold over `us` passes edge admission. -/
def foldAdmitsB : GraphState → List Tuple → Bool
  | _, [] => true
  | σ, u :: rest =>
      σ.admitEdge (subjNode u.subject) (objNode u.object u.relation)
      && foldAdmitsB (σ.writeDirect u) rest

/-- The mirror is exact: `foldAdmitsB` decides `FoldAdmits`. -/
theorem foldAdmitsB_iff (us : List Tuple) :
    ∀ σ : GraphState, foldAdmitsB σ us = true ↔ FoldAdmits σ us := by
  induction us with
  | nil => intro σ; simp [foldAdmitsB, FoldAdmits]
  | cons u rest ih =>
    intro σ
    simp [foldAdmitsB, FoldAdmits, Bool.and_eq_true, ih]

/-! ## The driver -/

/-- One fully-operational cascade leg — verbatim the `ReachedByW3d2E.cascade`
    constructor's target state. -/
def cascadeLeg (S : Schema) (T : Store) (σ : GraphState) : GraphState :=
  runCascade2 S T σ (enumJobs2R1 S σ) (enumJobs2R2 S T σ)

/-- Fold the chain's own legs over the input writes: per tuple, one admitted
    logged write then one cascade leg (synchronous v1). `none` iff some write
    fails edge admission — the input is then outside the add-only chain and the
    CLI must error rather than answer. Accumulates the chain store (prepend
    order, as the `write` constructor does). -/
def graphRunAux (S : Schema) : List Tuple → GraphState → Store →
    Option (GraphState × Store)
  | [], σ, T => some (σ, T)
  | t :: ts, σ, T =>
      if foldAdmitsB σ (rewriteClosure S t) then
        let σw := σ.writeLoggedRules S t
        graphRunAux S ts (cascadeLeg S (t :: T) σw) (t :: T)
      else none

/-- Run the operational graph model from the empty state over `ts` (in write
    order). -/
def graphRun (S : Schema) (ts : List Tuple) : Option (GraphState × Store) :=
  graphRunAux S ts (emptyState S) []

/-! ## Honesty: the driver's outputs are chain states -/

/-- Auxiliary invariant: from any reached state, the driver only produces
    reached states (each step is literally a `write` + `cascade` constructor
    pair). -/
theorem graphRunAux_reached {S : Schema} :
    ∀ (ts : List Tuple) {σ : GraphState} {T : Store} {σ' : GraphState} {T' : Store},
      ReachedBy σ S T → graphRunAux S ts σ T = some (σ', T') →
      ReachedBy σ' S T' := by
  intro ts
  induction ts with
  | nil =>
    intro σ T σ' T' h heq
    simp only [graphRunAux, Option.some.injEq, Prod.mk.injEq] at heq
    obtain ⟨rfl, rfl⟩ := heq
    exact h
  | cons t rest ih =>
    intro σ T σ' T' h heq
    rw [graphRunAux] at heq
    split at heq
    case isTrue hadm =>
      exact ih (ReachedByW3d2E.cascade
        (ReachedByW3d2E.write t ((foldAdmitsB_iff _ _).mp hadm) h)) heq
    case isFalse => cases heq

/-- **The driver is honest**: anything `graphRun` outputs is an operationally
    reached state of THE closure the final theorems quantify over. -/
theorem graphRun_reached {S : Schema} {ts : List Tuple} {σ : GraphState}
    {T : Store} (h : graphRun S ts = some (σ, T)) : ReachedBy σ S T :=
  graphRunAux_reached ts (ReachedByW3d2E.empty S) h

/-- The driver's chain store is exactly the input writes, newest first. -/
theorem graphRunAux_store {S : Schema} :
    ∀ (ts : List Tuple) {σ : GraphState} {T : Store} {σ' : GraphState} {T' : Store},
      graphRunAux S ts σ T = some (σ', T') → T' = ts.reverse ++ T := by
  intro ts
  induction ts with
  | nil =>
    intro σ T σ' T' heq
    simp only [graphRunAux, Option.some.injEq, Prod.mk.injEq] at heq
    obtain ⟨-, rfl⟩ := heq
    simp
  | cons t rest ih =>
    intro σ T σ' T' heq
    rw [graphRunAux] at heq
    split at heq
    · rw [ih heq]; simp
    · cases heq

/-- The driver's chain store is the reversed input list. -/
theorem graphRun_store {S : Schema} {ts : List Tuple} {σ : GraphState} {T : Store}
    (h : graphRun S ts = some (σ, T)) : T = ts.reverse := by
  have := graphRunAux_store ts h
  simpa using this

/-! ## The executable drained check -/

/-- Executable `Drained` (`FullScope.lean`): no dirty derived key above the
    watermark. -/
def drainedB (S : Schema) (σ : GraphState) : Bool := (cascadeKeys S σ).isEmpty

theorem drainedB_iff (S : Schema) (σ : GraphState) :
    drainedB S σ = true ↔ Drained S σ := by
  simp [drainedB, Drained, List.isEmpty_iff]

/-! ## The capstone: CLI graph-mode verdicts are `sem` -/

/-- **Under the W4 bundles, the CLI's graph-mode output IS the perfect model.**
    If the driver accepts the corpus and lands drained (both machine-checked at
    runtime), then for every in-scope query the printed verdict equals `sem` —
    this is `graph_correct` applied to `graphRun_reached`, no analogy anywhere. -/
theorem graphRun_check_eq_sem {S : Schema} {ts : List Tuple} {σ : GraphState}
    {T : Store} (hrun : graphRun S ts = some (σ, T)) (hdr : drainedB S σ = true)
    (hA : GraphAdmission S T) (hF : W4Fragment S T) (q : Query)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem S T q :=
  graph_correct q hA hF (graphRun_reached hrun) ((drainedB_iff S σ).mp hdr)
    hqs hqo

end Zanzibar
