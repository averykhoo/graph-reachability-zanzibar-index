import ZanzibarProofs.FullScope
-- Added 2026-09-05 (round 5) for ONE reason: the E-chain occurrence-count theorem
-- `reachedByW3d2E_untOccCount` is not otherwise in this module's cone (round 4 measured
-- `unknownIdentifier` and had to put its bridge in `RemoveOccCount.lean`), and the round-5
-- repair-space section below needs it in scope to make the `#check` composition a real
-- obligation instead of a docstring claim. Acyclic: `RemoveOccCount` imports
-- `CascadeStrataInv`, and nothing in that cone imports `Exec` (only `Audit`, `Cli` and
-- `TtuStarWide` do). No definition changes.
import ZanzibarProofs.GraphIndex.RemoveOccCount

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
  Python write path: `connectedstore/apply.py::advance_index` →
  `index_v4/processor.py::DeltaProcessor.run_cascade` → `::DeltaProcessor._run_cascade`
  in the same transaction, `tests/test_matrix.py` `GraphBackend.apply`). **Only the
  INTERLEAVED schedule** — under `ConnectedStore(sync=False)` / `build_index`,
  `advance_index` applies the whole batch before one cascade (`ZT-P4-2c`).
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
  runCascade2 S T σ (enumJobs2R1 S T σ) (enumJobs2R2 S T σ)

/-- Fold the chain's own legs over the input writes: per tuple, one admitted
    logged write then one cascade leg (synchronous v1). `none` iff some write
    fails edge admission — the input is then outside the add-only chain and the
    CLI must error rather than answer. Accumulates the chain store (prepend
    order, as the `write` constructor does). -/
def graphRunAux (S : Schema) : List Tuple → GraphState → Store →
    Option (GraphState × Store)
  | [], σ, T => some (σ, T)
  | t :: ts, σ, T =>
      -- step 4c-ii: the runtime gate must decide the admission of the list the write leg
      -- ACTUALLY folds, which is now the leaf-routed one (`GraphState.writeLoggedRules`).
      if foldAdmitsB σ (rewriteClosureL S (rawWriteTuples S t)) then
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
    this is `graph_correct_public` applied to `graphRun_reached`, no analogy anywhere.

    ⚠ **"The printed verdict" is load-bearing, so this is stated over the PUBLIC read
    (2026-08-28c).** `Cli.lean::printAnswers` is fed `GraphModel.checkPublic σ q`, and
    this theorem must be about the same function or the sentence above is false. The two
    were migrated in ONE commit for that reason; if you re-point either, re-point both.
    Pre-4c-ii the two reads are extensionally equal on reachable states (no write mints
    a leaf node), so the conformance goldens are byte-identical across this change —
    which means **a green golden run is not evidence this migration is right**, the same
    vacuity shape `graph_correct_public`'s own docstring warns about. -/
theorem graphRun_check_eq_sem {S : Schema} {ts : List Tuple} {σ : GraphState}
    {T : Store} (hrun : graphRun S ts = some (σ, T)) (hdr : drainedB S σ = true)
    (hA : GraphAdmission S T) (hF : W4Fragment S T) (q : Query)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.checkPublic σ q = sem S T q :=
  graph_correct_public q hA hF (graphRun_reached hrun) ((drainedB_iff S σ).mp hdr)
    hqs hqo

/-- **The answer vector the CLI prints, as a NAMED definition.**
    `Cli.lean`'s graph mode is exactly `printAnswers (graphModeAnswers σ qs)`.

    ⚠ **This definition exists to be PINNED, and that is its whole job.** Its body is
    carried verbatim in `formal/headline_definitions.txt` (it is dragged into the closure
    by `graphModeAnswers_eq_sem` below, which is in `statement_pin.py::HEADLINE`), so
    re-pointing the driver's read from `checkPublic` back to the unfenced `check` changes
    pinned golden TEXT and turns `verify.sh lean` red.

    It was introduced 2026-08-28c because the migration's own sabotage proved the coupling
    was otherwise unpinned. **Sabotage 1** (the hole): with `Cli.lean` reverted to
    `GraphModel.check` and everything else migrated, the full conformance suite reported

        495 passed in 590.51s (0:09:50)

    — nothing anywhere caught a driver that no longer matched its capstone theorem. That
    is expected pre-4c-ii (both reads agree on every reachable state, so no corpus can
    distinguish them) and is why the pin has to be TEXTUAL rather than behavioural: no
    corpus-based test can do this job until 4c-ii mints leaf nodes.

    **Sabotage 2** (the instrument, run against this definition once it existed): revert
    the body below to `GraphModel.check` AND repair this file's proof to close via
    `graph_correct` instead — the realistic weakening, since a reverter who hits a build
    error just fixes the build. Result: `lake build` **succeeded (1089 jobs)**, and the
    pin caught it:

        FAIL: the DEFINITION of def:Zanzibar.graphModeAnswers changed:
            pinned: [def] def graphModeAnswers ... := qs.map (fun q => GraphModel.checkPublic σ q)
            source: [def] def graphModeAnswers ... := qs.map (fun q => GraphModel.check σ q)
          headline statement pin: 46/46 statements match

    ⚠ Read that last line. **The STATEMENT pin is blind to this** — `graphModeAnswers_eq_sem`'s
    text never mentions `check` or `checkPublic`, only `graphModeAnswers`, so it matches
    byte-for-byte while meaning something different. Only the DEFINITION pin fires. This is
    `2026-08-28b`'s lesson ("a guard-only pin cannot catch a fence removal; only a pin
    stated over a STATE can") recurring one layer up, and it is the reason
    `graphModeAnswers_eq_sem` is in `HEADLINE` at all: not for its own content, which is a
    one-line lift, but to drag this definition's BODY into the pinned closure. If you ever
    remove it from `HEADLINE`, this definition silently leaves the closure and the driver
    becomes re-pointable again with no red anywhere. -/
def graphModeAnswers (σ : GraphState) (qs : List Query) : List Bool :=
  qs.map (fun q => GraphModel.checkPublic σ q)

/-- **The printed answer VECTOR is `sem`, pointwise.** `graphRun_check_eq_sem` lifted
    over the query list, stated about the definition the driver actually calls. This is
    what drags `graphModeAnswers` into the pinned-definition closure. -/
theorem graphModeAnswers_eq_sem {S : Schema} {ts : List Tuple} {σ : GraphState}
    {T : Store} {qs : List Query}
    (hrun : graphRun S ts = some (σ, T)) (hdr : drainedB S σ = true)
    (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (hqs : ∀ q ∈ qs, q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : ∀ q ∈ qs, q.object.name ≠ STAR) :
    graphModeAnswers σ qs = qs.map (fun q => sem S T q) := by
  unfold graphModeAnswers
  refine List.map_congr_left ?_
  intro q hq
  exact graphRun_check_eq_sem hrun hdr hA hF q (hqs q hq) (hqo q hq)

/-! ## The op-stream driver — add AND remove (Exec-driver remove hardening)

`graphRun` above is add-only: it folds `write`+`cascade` per input tuple, so the
chain PROVES remove-correctness (the `remove` constructor on `ReachedByW3d2E`) but
the driver never EXERCISES it. This layer widens the driver to a stream of
`GraphOp`s (add / remove), each op stepping the SAME chain — an add is a `write`
then a `cascade` leg (as before), a remove is a `remove` then a `cascade` leg
(Python's retract-then-drain, `TupleSource.remove` + the same-transaction
cascade). The `remove` constructor's guard is DECIDED at runtime by `removeGateB`
(the honesty-by-runtime-gate discipline, mirroring `foldAdmitsB`/`drainedB`); an
op failing its gate FAILS CLOSED (`none`, driver rejects), exactly as an
admission-failing write does on the add side. Purely additive: `graphRun` and its
honesty theorems are untouched, so the add-only zcli path is byte-identical. -/

/-- A driver op: grant (`add`) or retract (`remove`) one tuple. -/
inductive GraphOp where
  | add (t : Tuple)
  | remove (t : Tuple)
deriving Repr, Inhabited, DecidableEq

/-! ### Bool deciders for the `remove` constructor's store-discipline guard

Each mirrors one `Prop` the `ReachedByW3d2E.remove` constructor carries about the
PRE-remove store `T` (`CascadeStrataAssemble.lean`); the paired `…_iff` lemma
lets the honesty theorem feed the runtime-decided fact straight into the
constructor. Same pattern as `foldAdmitsB_iff`/`drainedB_iff`. -/

/-- Executable `StoreValidRules` (`RulesSound.lean`): every stored tuple lands on a
    declared relation with a matching `Direct` arm. -/
def storeValidRulesB (S : Schema) (T : Store) : Bool :=
  T.all fun t =>
    match S.lookup (t.object.type, t.relation) with
    | some e => (exprDirects e).any (fun rs => restrictionMatches rs t)
    | none => false

theorem storeValidRulesB_iff (S : Schema) (T : Store) :
    storeValidRulesB S T = true ↔ StoreValidRules S T := by
  unfold storeValidRulesB StoreValidRules
  rw [List.all_eq_true]
  refine ⟨fun h t ht => ?_, fun h t ht => ?_⟩
  · have hh := h t ht
    revert hh
    cases hl : S.lookup (t.object.type, t.relation) with
    | none => simp
    | some e =>
      intro hany
      rw [List.any_eq_true] at hany
      obtain ⟨rs, hrs, hm⟩ := hany
      exact ⟨e, rs, rfl, hrs, hm⟩
  · obtain ⟨e, rs, hl, hrs, hm⟩ := h t ht
    rw [hl, List.any_eq_true]
    exact ⟨rs, hrs, hm⟩

/-- Executable `BareStarStore` (`BareStarCorrect.lean`): star subjects are bare,
    objects are star-free. -/
def bareStarStoreB (T : Store) : Bool :=
  T.all fun t =>
    (!(t.subject.name == STAR) || t.subject.predicate == BARE)
      && !(t.object.name == STAR)

theorem bareStarStoreB_iff (T : Store) :
    bareStarStoreB T = true ↔ BareStarStore T := by
  unfold bareStarStoreB BareStarStore
  rw [List.all_eq_true]
  refine ⟨fun h t ht => ?_, fun h t ht => ?_⟩
  · have hh := h t ht
    simp only [Bool.and_eq_true, Bool.or_eq_true, Bool.not_eq_true', beq_iff_eq,
      beq_eq_false_iff_ne, ne_eq] at hh
    exact ⟨fun hstar => hh.1.resolve_left (by simp [hstar]), hh.2⟩
  · have hh := h t ht
    simp only [Bool.and_eq_true, Bool.or_eq_true, Bool.not_eq_true', beq_iff_eq,
      beq_eq_false_iff_ne, ne_eq]
    refine ⟨?_, hh.2⟩
    by_cases hstar : t.subject.name = STAR
    · exact Or.inr (hh.1 hstar)
    · exact Or.inl hstar

/-- Executable `TtuStarFree` (`RulesBareStar.lean`): no TTU rewrite arm matches a
    stored star-subject tuple. -/
def ttuStarFreeB (S : Schema) (T : Store) : Bool :=
  T.all fun t =>
    !(t.subject.name == STAR) ||
      (schemaRewrites S).all (fun a =>
        match a.kind with
        | RuleKind.ttu _ =>
            !((t.relation == a.matchRel) && (t.object.type == a.objectType))
        | RuleKind.computed => true)

theorem ttuStarFreeB_iff (S : Schema) (T : Store) :
    ttuStarFreeB S T = true ↔ TtuStarFree S T := by
  unfold ttuStarFreeB TtuStarFree
  rw [List.all_eq_true]
  refine ⟨fun h t ht hstar a ha tr hkind => ?_, fun h t ht => ?_⟩
  · have hh := h t ht
    simp only [Bool.or_eq_true, Bool.not_eq_true', beq_eq_false_iff_ne, ne_eq] at hh
    have hall := hh.resolve_left (by simp [hstar])
    rw [List.all_eq_true] at hall
    have ha' := hall a ha
    rw [hkind] at ha'
    simp only [Bool.not_eq_true', Bool.and_eq_false_iff, beq_eq_false_iff_ne,
      ne_eq] at ha'
    rintro ⟨hrel, hobj⟩
    rcases ha' with hr | ho
    · exact hr hrel
    · exact ho hobj
  · simp only [Bool.or_eq_true, Bool.not_eq_true', beq_eq_false_iff_ne, ne_eq]
    by_cases hstar : t.subject.name = STAR
    · refine Or.inr ?_
      rw [List.all_eq_true]
      intro a ha
      cases hkind : a.kind with
      | computed => rfl
      | ttu tr =>
        simp only [Bool.not_eq_true', Bool.and_eq_false_iff, beq_eq_false_iff_ne,
          ne_eq]
        by_cases hrel : t.relation = a.matchRel
        · by_cases hobj : t.object.type = a.objectType
          · exact absurd ⟨hrel, hobj⟩ (h t ht hstar a ha tr hkind)
          · exact Or.inr hobj
        · exact Or.inl hrel
    · exact Or.inl hstar

/-- Executable `NoStoreSubjectR` (`ReconcileCorrect.lean`). -/
def noStoreSubjectRB (T : Store) (R : String) : Bool :=
  T.all fun t => !(t.subject.predicate == R)

theorem noStoreSubjectRB_iff (T : Store) (R : String) :
    noStoreSubjectRB T R = true ↔ NoStoreSubjectR T R := by
  unfold noStoreSubjectRB NoStoreSubjectR
  rw [List.all_eq_true]
  simp only [Bool.not_eq_true', beq_eq_false_iff_ne, ne_eq]

/-- Executable `NoTtuTarget` (`ReconcileCorrect.lean`). -/
def noTtuTargetB (S : Schema) (R : String) : Bool :=
  (schemaRewrites S).all fun r =>
    match r.kind with
    | RuleKind.ttu tr => !(tr == R)
    | RuleKind.computed => true

theorem noTtuTargetB_iff (S : Schema) (R : String) :
    noTtuTargetB S R = true ↔ NoTtuTarget S R := by
  unfold noTtuTargetB NoTtuTarget
  rw [List.all_eq_true]
  refine ⟨fun h r hr tr hkind => ?_, fun h r hr => ?_⟩
  · have hh := h r hr
    rw [hkind] at hh
    simp only [Bool.not_eq_true', beq_eq_false_iff_ne, ne_eq] at hh
    exact hh
  · cases hkind : r.kind with
    | computed => rfl
    | ttu tr =>
      simp only [Bool.not_eq_true', beq_eq_false_iff_ne, ne_eq]
      exact h r hr tr hkind

/-- Executable mirror of the `remove` constructor's `htermT` guard: every derived
    relation `R` is TTU-terminal and carries no stored `R`-userset subject.
    Quantifying over `taintedKeys S` is exact — `isDerived S (dt, R)` is exactly
    membership in `taintedKeys S`. -/
def htermB (S : Schema) (T : Store) : Bool :=
  (taintedKeys S).all fun k => noTtuTargetB S k.2 && noStoreSubjectRB T k.2

theorem htermB_iff (S : Schema) (T : Store) :
    htermB S T = true ↔
      ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R := by
  unfold htermB isDerived
  rw [List.all_eq_true]
  refine ⟨fun h dt R hd => ?_, fun h k hk => ?_⟩
  · have hmem : (dt, R) ∈ taintedKeys S := by
      simpa [List.contains_iff_mem] using hd
    have hh := h (dt, R) hmem
    simp only [Bool.and_eq_true] at hh
    exact ⟨(noTtuTargetB_iff S R).mp hh.1, (noStoreSubjectRB_iff T R).mp hh.2⟩
  · have hh := h k.1 k.2 (by simpa [List.contains_iff_mem] using hk)
    simp only [Bool.and_eq_true]
    exact ⟨(noTtuTargetB_iff S k.2).mpr hh.1, (noStoreSubjectRB_iff T k.2).mpr hh.2⟩

/-! ### The runtime remove gate -/

/-- The runtime gate for a remove op: decides the whole `ReachedByW3d2E.remove`
    guard (`RemoveAdmits` ∧ drained-prior ∧ the four store disciplines). -/
def removeGateB (S : Schema) (σ : GraphState) (T : Store) (t : Tuple) : Bool :=
  decide (t ∈ T) && drainedB S σ && storeValidRulesB S T
    && bareStarStoreB T && ttuStarFreeB S T && htermB S T

/-- The gate decides the constructor guard: a passing gate supplies every
    `remove` hypothesis. -/
theorem removeGateB_gate {S : Schema} {σ : GraphState} {T : Store} {t : Tuple}
    (hg : removeGateB S σ T t = true) :
    RemoveAdmits σ T t ∧ cascadeKeys S σ = [] ∧ StoreValidRules S T ∧
      BareStarStore T ∧ TtuStarFree S T ∧
      (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) := by
  unfold removeGateB at hg
  simp only [Bool.and_eq_true, decide_eq_true_eq] at hg
  obtain ⟨⟨⟨⟨⟨hmem, hdr⟩, hsv⟩, hbs⟩, hts⟩, hterm⟩ := hg
  exact ⟨hmem, (drainedB_iff S σ).mp hdr, (storeValidRulesB_iff S T).mp hsv,
    (bareStarStoreB_iff T).mp hbs, (ttuStarFreeB_iff S T).mp hts,
    (htermB_iff S T).mp hterm⟩

/-! ### The op-stream driver -/

/-- The accepted-store fold: an add prepends, a remove erases one occurrence —
    exactly the store the chain constructors accumulate. -/
def applyOpsStore : List GraphOp → Store → Store
  | [], T => T
  | GraphOp.add t :: ops, T => applyOpsStore ops (t :: T)
  | GraphOp.remove t :: ops, T => applyOpsStore ops (T.erase t)

/-- Fold the chain's own legs over the op stream: per op, one leg (`write` for
    add / `remove` for remove — the latter gated at runtime) then one cascade
    leg. `none` iff some op fails its gate (outside the operational chain). -/
def graphRunOpsAux (S : Schema) : List GraphOp → GraphState → Store →
    Option (GraphState × Store)
  | [], σ, T => some (σ, T)
  | GraphOp.add t :: ops, σ, T =>
      -- step 4c-ii: same re-point as `graphRunAux`.
      if foldAdmitsB σ (rewriteClosureL S (rawWriteTuples S t)) then
        graphRunOpsAux S ops (cascadeLeg S (t :: T) (σ.writeLoggedRules S t)) (t :: T)
      else none
  | GraphOp.remove t :: ops, σ, T =>
      if removeGateB S σ T t then
        graphRunOpsAux S ops (cascadeLeg S (T.erase t) (σ.removeLoggedRules S t))
          (T.erase t)
      else none

/-- Run the op-stream driver from the empty state. -/
def graphRunOps (S : Schema) (ops : List GraphOp) : Option (GraphState × Store) :=
  graphRunOpsAux S ops (emptyState S) []

/-! ### Honesty: op-driver outputs are chain states, remove included -/

/-- From any reached state the op-driver only produces reached states — each step
    is a `write`/`remove` constructor followed by a `cascade` constructor. The
    remove step's hypotheses are all supplied by `removeGateB_gate`. -/
theorem graphRunOpsAux_reached {S : Schema} :
    ∀ (ops : List GraphOp) {σ : GraphState} {T : Store} {σ' : GraphState}
      {T' : Store},
      ReachedBy σ S T → graphRunOpsAux S ops σ T = some (σ', T') →
      ReachedBy σ' S T' := by
  intro ops
  induction ops with
  | nil =>
    intro σ T σ' T' h heq
    simp only [graphRunOpsAux, Option.some.injEq, Prod.mk.injEq] at heq
    obtain ⟨rfl, rfl⟩ := heq
    exact h
  | cons op rest ih =>
    intro σ T σ' T' h heq
    cases op with
    | add t =>
      rw [graphRunOpsAux] at heq
      split at heq
      case isTrue hadm =>
        exact ih (ReachedByW3d2E.cascade
          (ReachedByW3d2E.write t ((foldAdmitsB_iff _ _).mp hadm) h)) heq
      case isFalse => cases heq
    | remove t =>
      rw [graphRunOpsAux] at heq
      split at heq
      case isTrue hg =>
        obtain ⟨hadm, hdrain, hSVT, hBST, hTST, hterm⟩ := removeGateB_gate hg
        exact ih (ReachedByW3d2E.cascade
          (ReachedByW3d2E.remove t hadm hdrain hSVT hBST hTST hterm h)) heq
      case isFalse => cases heq

/-- **The op-driver is honest**: any `graphRunOps` output is an operationally
    reached state of THE closure the final theorems quantify over — now covering
    remove ops. -/
theorem graphRunOps_reached {S : Schema} {ops : List GraphOp} {σ : GraphState}
    {T : Store} (h : graphRunOps S ops = some (σ, T)) : ReachedBy σ S T :=
  graphRunOpsAux_reached ops (ReachedByW3d2E.empty S) h

/-- The op-driver's chain store is the accepted-store fold of the op stream. -/
theorem graphRunOpsAux_store {S : Schema} :
    ∀ (ops : List GraphOp) {σ : GraphState} {T : Store} {σ' : GraphState}
      {T' : Store},
      graphRunOpsAux S ops σ T = some (σ', T') → T' = applyOpsStore ops T := by
  intro ops
  induction ops with
  | nil =>
    intro σ T σ' T' heq
    simp only [graphRunOpsAux, Option.some.injEq, Prod.mk.injEq] at heq
    obtain ⟨-, rfl⟩ := heq
    rfl
  | cons op rest ih =>
    intro σ T σ' T' heq
    cases op with
    | add t =>
      rw [graphRunOpsAux] at heq
      split at heq
      · rw [ih heq]; rfl
      · cases heq
    | remove t =>
      rw [graphRunOpsAux] at heq
      split at heq
      · rw [ih heq]; rfl
      · cases heq

/-- The op-driver's chain store is the op stream's accepted-store fold from empty. -/
theorem graphRunOps_store {S : Schema} {ops : List GraphOp} {σ : GraphState}
    {T : Store} (h : graphRunOps S ops = some (σ, T)) : T = applyOpsStore ops [] :=
  graphRunOpsAux_store ops h

/-! ### The capstone: op-driver graph-mode verdicts are `sem`, remove included -/

/-- **Under the W4 bundles, the op-driver's graph-mode output IS the perfect
    model — for op streams with removes.** If the driver accepts the stream and
    lands drained (both machine-checked at runtime), then for every in-scope query
    the printed verdict equals `sem` of the accepted final store — `graph_correct`
    applied to `graphRunOps_reached`, no analogy anywhere. The `remove`
    constructor's correctness (the completed Lean remove leg) is what makes this
    hold over retraction states, and `removeGateB` is what earns the driver the
    right to construct them.

    Over the PUBLIC read, for the same reason as `graphRun_check_eq_sem` above. -/
theorem graphRunOps_check_eq_sem {S : Schema} {ops : List GraphOp} {σ : GraphState}
    {T : Store} (hrun : graphRunOps S ops = some (σ, T)) (hdr : drainedB S σ = true)
    (hA : GraphAdmission S T) (hF : W4Fragment S T) (q : Query)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.checkPublic σ q = sem S T q :=
  graph_correct_public q hA hF (graphRunOps_reached hrun) ((drainedB_iff S σ).mp hdr)
    hqs hqo

/-! ## ★ THE EDGE LEAK IS CLOSED, ON THE REACHABLE DRIVER TRACE (step R5)

⚠ **HISTORY — what this section said, and why it is inverted rather than deleted.** Between
the write-path flip and R5 this block held six kernel `decide`s establishing a genuine
defect of the half-landed flip: `graphRunOps_writeRemove_leaks_leaf_edge` (add then remove
the same tuple through the op-driver, which drains after every op; the store returns to `[]`
and the index still holds `doc:d1#viewer.0@user:alice`), `…_leak_accumulates` (two round
trips leave TWO leaked edges, so the residue grew without bound), `…_leak_read_inert` (the
PUBLIC entry still denied), and `graphRunOps_leak_unfenced_grants` /
`graphRunOps_leak_internal_ghost_grant` — which measured the sharper half: BELOW the
`checkPublic` leaf fence, `GraphModel.check` (Python's
`index_v4/wildcard.py::WildcardIndex._check_internal`) GRANTED at the leaked leaf name
against an EMPTY store on a DRAINED, `ReachedBy`-certified state, where `sem` denies by
`sem_nil_false`. The single load-bearing barrier was the fence.

R5 removes the mechanism: `Cascade.lean::GraphState.removeLoggedRules` folds
`rewriteClosureL S (rawWriteTuples S t)`, the same list the write leg folds, so the
retraction retracts exactly what the write minted. Every one of those six `decide`s is now
FALSE, and that is how this landing was detected — they went red on the first whole-tree
build after the re-point, before any of them was touched. Per
`docs/sabotage-procedure.md`'s durability ranking a fix whose only trace is a deleted
refutation is a doc warning, so the same ops streams stay and the claims are INVERTED
below. Revert `removeLoggedRules` and `graphRunOps_writeRemove_edge_neutral` goes red on
the exact trace that used to leak.

⚠ **What has NOT changed:** the WRITE leg still mints leaf edges, which exist between the
write and the drain. `writeLeg_extra_leafName` / `writeLeg_extra_unreadable` /
`writeLeg_extra_leaf_terminal` below are about those TRANSIENT extras and are kept
unchanged — they say the extras are leaf-addressed, invisible at the public entry on EVERY
`LeafScope` schema, and never a SOURCE of any edge. What R5 changed is that they no longer
SURVIVE the matching retraction.

**Python fidelity, re-verified 2026-09-05:** `connectedstore/apply.py::_apply_row` (`:62-66`)
selects `widx._add_tuple_trusted` / `::_remove_tuple_trusted` by `row.op` and then routes
ONE `ruleset.apply(triple)` fan-out, and the conformance driver
`formal/conformance/backends.py::GraphDriver._fan` has the same symmetric shape. The leak
was therefore a MODEL artefact of the half-landed flip throughout, never shipped behaviour;
R5 is the model catching up. -/

/-- **THE LEAK, CLOSED, ON A REACHABLE TRACE.** Add `doc:d1#editor@user:alice`, then retract
    the very same tuple. The driver accepts both ops and drains the cascade after each, the
    store returns to EMPTY — and so does the index. This is the literal inversion of the
    deleted `graphRunOps_writeRemove_leaks_leaf_edge`, whose right-hand side was
    `some ([(user:alice, doc:d1#viewer.0)], [])`. -/
theorem graphRunOps_writeRemove_edge_neutral :
    ((graphRunOps LeafRuleWitness.SlV
        [GraphOp.add LeafRuleWitness.tlEditor,
         GraphOp.remove LeafRuleWitness.tlEditor]).map (fun p => (p.1.edges, p.2)))
      = some ([], []) := by
  decide

/-! ⚠ **The deleted `…_leak_accumulates` has NO four-op replacement here, deliberately.**
It decided `some (2, [])` on the two-round-trip stream — the residue growing once per round
trip, which is what made the leak a `NOW`-shaped problem. The natural inversion (`some (0,
[])` on the same stream) was tried and does not FIT: after (alpha) each op runs a real
cascade rather than quiescing immediately, and the four-op `decide` exhausts the
elaborator's recursion budget (`maximum recursion depth has been reached`, measured
2026-09-05). It is NOT stated with `set_option maxRecDepth` raised: a `decide` that needs
its budget nudged is one line away from a `decide` that needs it raised to hide a failure,
and this repo's rule is to keep that distance.

The content is not lost — it is carried by a THEOREM rather than a fixture, which is the
better half of the durability ranking anyway:
`CascadeStrata.lean::writeThenRemove_edge_count_zero` says the write/remove round trip
returns EVERY edge count to zero for an ARBITRARY `p`, off `count_writeLoggedRules` +
`count_removeLoggedRules`, so no residue can accumulate at any edge over any number of
round trips. `graphRunOps_writeRemove_edge_neutral` above is its driver-level instance. -/

/-- The leaf query that used to be a ghost grant: `alice` at the storage leaf
    `doc:d1#viewer.0`. Kept — the pins below are stated at it. (Was `writeExtraLeafQuery`; renamed
    when R5 closed the leak, because a name asserting a defect that no longer exists is the
    kind of citation this repo keeps having to correct.) -/
def writeExtraLeafQuery : Query :=
  ⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩

/-- **THE GHOST GRANT IS GONE, BELOW THE FENCE AS WELL AS AT IT.** Same round trip, same
    four components decided in ONE statement so a `check` from one state cannot be paired
    with a store from another: the store is `[]`, the state is DRAINED, and the UNFENCED
    internal read (`GraphModel.check` = `WildcardIndex._check_internal`, the layer beneath
    the `BL-2` fence) now DENIES — where the deleted `graphRunOps_leak_unfenced_grants`
    decided `some ([], true, true, false)`, i.e. granted.

    ⚠ This is the assurance that matters most in the block, because the internal surface is
    the one the leak was actually visible on: `graphRunOps_writeRemove_edge_neutral` says
    the edges are gone, and this says the READ agrees. The public column stays `false`
    throughout, so the `checkPublic` leaf fence is no longer the single load-bearing
    barrier — it is now a redundant one. -/
theorem graphRunOps_writeRemove_no_ghost_grant :
    ((graphRunOps LeafRuleWitness.SlV
        [GraphOp.add LeafRuleWitness.tlEditor,
         GraphOp.remove LeafRuleWitness.tlEditor]).map (fun p =>
          (p.2, drainedB LeafRuleWitness.SlV p.1,
           GraphModel.check p.1 writeExtraLeafQuery,
           GraphModel.checkPublic p.1 writeExtraLeafQuery)))
      = some ([], true, false, false) := by
  decide

/-- …and the same fact on a certified CHAIN state, with the spec's answer alongside. The
    state is `ReachedBy`-reachable (`graphRunOps_reached`) and `Drained` (`drainedB_iff`),
    the store is `[]`, and the spec denies by `sem_nil_false` — hypothesis-free and
    schema-generic, so that half cannot be a fixture artefact. The INTERNAL read agrees with
    the spec, which is exactly what the deleted `graphRunOps_leak_internal_ghost_grant`
    denied. -/
theorem graphRunOps_writeRemove_internal_agrees :
    ∃ σ : GraphState,
      graphRunOps LeafRuleWitness.SlV
          [GraphOp.add LeafRuleWitness.tlEditor,
           GraphOp.remove LeafRuleWitness.tlEditor] = some (σ, ([] : Store))
        ∧ ReachedBy σ LeafRuleWitness.SlV ([] : Store)
        ∧ Drained LeafRuleWitness.SlV σ
        ∧ GraphModel.check σ writeExtraLeafQuery = false
        ∧ GraphModel.checkPublic σ writeExtraLeafQuery = false
        ∧ sem LeafRuleWitness.SlV ([] : Store) writeExtraLeafQuery = false := by
  have hd := graphRunOps_writeRemove_no_ghost_grant
  cases hopt : graphRunOps LeafRuleWitness.SlV
      [GraphOp.add LeafRuleWitness.tlEditor,
       GraphOp.remove LeafRuleWitness.tlEditor] with
  | none => rw [hopt] at hd; simp at hd
  | some p =>
      obtain ⟨σ0, T0⟩ := p
      rw [hopt] at hd
      simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at hd
      obtain ⟨hT, hdr, hchk, hpub⟩ := hd
      subst hT
      exact ⟨σ0, rfl, graphRunOps_reached hopt, (drainedB_iff _ _).mp hdr, hchk, hpub,
        sem_nil_false _ _⟩

/-- **The fence is CORRECT at a leaf name, not merely conservative** — on every state and
    every store. The public read denies by construction, and the spec denies because a
    leaf-family name is not a declared key. Extracted from `graph_correct_public`'s own
    fenced branch so the general severity bound below need not re-derive it, and stated
    without any admission/reachability hypothesis so it applies to the post-flip states too. -/
theorem checkPublic_eq_sem_of_leafName {S : Schema} {σ : GraphState} {T : Store}
    (hWF : WF S) (hsch : σ.schema = S) {q : Query}
    (hleaf : (publicOfLeaf S q.object.type q.relation).isSome = true) :
    GraphModel.checkPublic σ q = false ∧ sem S T q = false := by
  refine ⟨?_, ?_⟩
  · unfold GraphModel.checkPublic
    rw [hsch, if_pos hleaf]
  · exact semAux_undeclared S q.subject T q
      (not_mem_keys_of_publicOfLeaf_isSome hWF hleaf) _ _

/-- **Every extra the flipped write leg materialises is addressed at a LEAF name** — the
    object half of the residue's shape, at any `LeafScope` schema. This is
    `LeafRules.lean::rewriteClosureL_extras_leafNode` with its `LeafNode` existential
    projected down to the one component the fence reads. -/
theorem writeLeg_extra_leafName {S : Schema} (hLS : LeafScope S)
    {t : Tuple} (hon : t.object.name ≠ STAR)
    {u : Tuple} (hu : u ∈ rewriteClosureL S (rawWriteTuples S t))
    (hnot : u ∉ rewriteClosure S t) :
    (publicOfLeaf S u.object.type u.relation).isSome = true := by
  rcases rewriteClosureL_extras_leafNode hLS.wf hLS.matchNotLeaf
      hLS.derivedNameNonempty hon u hu with h | h
  · exact absurd h hnot
  · obtain ⟨ty, on, p, hsome, _, _, heq⟩ := h
    have ht : u.object.type = ty := by
      have h2 := congrArg NodeKey.type heq
      rwa [objNode_type, objNode_type] at h2
    have hp : u.relation = p := by
      have h2 := congrArg NodeKey.pred heq
      rwa [objNode_pred, objNode_pred] at h2
    rw [ht, hp]; exact hsome

/-- **THE GENERAL BOUND — the write leg's TRANSIENT extras are unreadable through the PUBLIC
    entry, on every schema.** At any query naming a node the leaf-routed write leg minted
    beyond the plain closure, `checkPublic` and `sem` agree (both `false`) whatever the index
    holds — at any schema in `LeafScope`, any subject, any state whose schema is `S`.

    ⚠ **Scope, restated post-R5.** The extras still EXIST between a write and its matching
    retraction; what R5 changed is that they no longer SURVIVE it
    (`graphRunOps_writeRemove_edge_neutral`,
    `CascadeStrata.lean::writeThenRemove_edge_count_zero`). While they exist they are fenced
    above and — post-R5 — absent below: `graphRunOps_writeRemove_no_ghost_grant` decides that
    the UNFENCED `GraphModel.check` denies at the leaf name on the round-tripped state, where
    the deleted `graphRunOps_leak_unfenced_grants` had it granting. This theorem bounds the
    DIRECT probe only, and it is unchanged by either landing: it was true before and is true
    now, which is why it survives while the leak fixtures did not. -/
theorem writeLeg_extra_unreadable {S : Schema} {σ : GraphState} {T : Store}
    (hLS : LeafScope S) (hsch : σ.schema = S)
    {t : Tuple} (hon : t.object.name ≠ STAR)
    {u : Tuple} (hu : u ∈ rewriteClosureL S (rawWriteTuples S t))
    (hnot : u ∉ rewriteClosure S t) (s : SubjectRef) :
    GraphModel.checkPublic σ ⟨s, u.relation, u.object⟩
      = sem S T ⟨s, u.relation, u.object⟩ := by
  obtain ⟨h1, h2⟩ := checkPublic_eq_sem_of_leafName (S := S) (σ := σ) (T := T) hLS.wf hsch
    (q := ⟨s, u.relation, u.object⟩) (writeLeg_extra_leafName hLS hon hu hnot)
  rw [h1, h2]

/-- **The residue is TERMINAL as well as fenced**: every extra points INTO a leaf node and
    none is sourced AT one. The subject half is `LeafRules.lean::
    rewriteClosureL_subject_not_leafNode`, whose premise is the `noLeafSubjects` field the
    4c-ii re-point added to `GraphAdmission` — so this is the (D) obligation's threading
    paying for itself outside the settledness cone. Together the two halves say a leaked
    edge cannot lie on a path from any queryable node to any other. -/
theorem writeLeg_extra_leaf_terminal {S : Schema} (hLS : LeafScope S)
    {t : Tuple} (hon : t.object.name ≠ STAR)
    (hsb : NotLeafName t.subject.predicate)
    {u : Tuple} (hu : u ∈ rewriteClosureL S (rawWriteTuples S t))
    (hnot : u ∉ rewriteClosure S t) :
    (publicOfLeaf S u.object.type u.relation).isSome = true
      ∧ ¬ LeafNode S (subjNode u.subject) :=
  ⟨writeLeg_extra_leafName hLS hon hu hnot,
   rewriteClosureL_subject_not_leafNode hLS.noLeafSubjects hsb u hu⟩

/-! ### The non-vacuity instrument for the three theorems above

House rule: a theorem whose premises cannot be met passes by being empty, which is this
project's named failure mode. `writeLeg_extra_unreadable` quantifies over a `u` that IS in
the leaf-routed closure and is NOT in the plain one, so if no such `u` ever existed the
general severity bound would be worth nothing. The two pins below say the premise set is
inhabited at a schema that already lives in the tree.

⚠ **One premise IS discharged vacuously at `SlV`, and saying so is the point.**
`LeafRules.lean::LeafRuleWitness.lrV_untainted_layer_silent` proves `schemaRewrites SlV = []`,
so `LeafScope.matchNotLeaf` (a `∀ r ∈ schemaRewrites S` binder) holds at `SlV` by EMPTINESS,
exactly as `LeafRules.lean:1927` and `:2300` warn. What is NOT vacuous here is the pair that
carries the content — `slV_extra_exists` exhibits a concrete tuple the flipped leg
materialises and the plain leg does not — and that is the premise the bound is about. A
witness whose untainted rule layer is non-empty (`LeafRuleWitness.SnlBoth`) would tighten
`matchNotLeaf` too; it is not needed for the bound's content and is not claimed here. -/

/-- `LeafScope SlV`, assembled from the existing `LeafRules.lean::LeafRuleWitness.slV_wf`
    plus three decidable fields. -/
theorem leafScope_SlV : LeafScope LeafRuleWitness.SlV :=
  ⟨LeafRuleWitness.slV_wf, by decide, by decide, by decide⟩

/-- **The residue premise is inhabited**: the leaf copy `doc:d1#viewer.0@user:alice` IS in
    the flipped write leg's closure of `tlEditor` and is NOT in the plain closure. This is
    the `hu`/`hnot` pair of `writeLeg_extra_leafName` / `writeLeg_extra_unreadable` /
    `writeLeg_extra_leaf_terminal`, satisfied at a concrete schema. -/
theorem slV_extra_exists :
    (⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩ : Tuple)
        ∈ rewriteClosureL LeafRuleWitness.SlV
            (rawWriteTuples LeafRuleWitness.SlV LeafRuleWitness.tlEditor)
      ∧ (⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩ : Tuple)
        ∉ rewriteClosure LeafRuleWitness.SlV LeafRuleWitness.tlEditor := by
  decide

/-- The general bound, INSTANTIATED — every hypothesis discharged from the two pins above,
    so the reader can see it fire rather than take the binders on trust. At any state whose
    schema is `SlV` and any subject, the public read of the leaked leaf key equals the spec. -/
theorem writeLeg_extra_unreadable_SlV (σ : GraphState) (T : Store)
    (hsch : σ.schema = LeafRuleWitness.SlV) (s : SubjectRef) :
    GraphModel.checkPublic σ ⟨s, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩
      = sem LeafRuleWitness.SlV T ⟨s, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩ :=
  writeLeg_extra_unreadable leafScope_SlV hsch (t := LeafRuleWitness.tlEditor) (by decide)
    slV_extra_exists.1 slV_extra_exists.2 s

/-! ## ★★ THE HEADLINE IS TRUE AGAIN AT THE WITNESS THAT REFUTED IT (step (alpha))

⚠ **HISTORY — this section was headed "STOP — `graph_correct_public` IS FALSE AFTER THE
FLIP", and it held `graph_correct_public_refuted` and `graph_correct_refuted`, both
`sorryAx`-free.** The mechanism: `CascadeStrataSettle.lean::writeLeg_own_key_dirty` was
refuted post-flip, because a write to a derived relation's Direct storage arm re-addresses
onto the leaf name (`approver.0`) and `affectedKeys`' own-key branch tested
`isDerived S (node.type, node.pred)` — FALSE at a minted leaf name. The write never dirtied
its OWN key, the cascade never fired for the very write that needed it, the public
`approver` edge was never materialised, and the state then reported itself DRAINED. The
break was FAIL-CLOSED (`sem` granted, the index denied), which is the safer direction but
was still a hard divergence inside the supported fragment.

It was refuted at the project's OWN certified in-fragment witness, not at a schema built to
break it — `W4WitnessDirect.Sd`/`Td`, whose `GraphAdmission` (`::admission`) and
`W4Fragment` (`::w4fragment`) were proved by an earlier leg for an unrelated purpose.

**(alpha) closes it**: `affectedKeys`' own-key branch now maps the leaf delta back to its
PUBLIC key through `Leaf.lean::publicOfLeaf`, exactly as
`index_v4/processor.py::DeltaProcessor._map_deltas_to_keys` does. The refutations are
DELETED because their statements are false, and the same fixtures are kept and INVERTED into
`decide` pins — `graphRunOps_directArm_agrees`, `::_agrees_check`, `::_agrees_corpus`,
`::graphRunOps_directArm_check_eq_sem`. Revert the branch and every one of them reddens at
the exact query that used to refute the headline.

**The headline is PROVED as of 2026-09-05 round 2.** The last staged sorry
(`CascadeStrataSettle.lean::writeLeg_own_key_dirty`) is discharged: the routing premise
`rawWriteRels S t ≠ []` is now a CONSEQUENCE of the store admission through
`CascadeStrataSettle.lean::rawWriteRels_ne_nil_of_exprDirectsAll`, not a carry, so
`graph_correct` no longer depends on `sorryAx`. The `decide` pins below stay: they are what
reddens if `affectedKeys`' own-key branch is reverted. -/

/-- The in-fragment query: `alice`'s grant through the Direct arm of the derived `approver`
    def of `W4WitnessDirect.Sd` (`approver := [user] but not banned`). -/
def sdDirectArmQuery : Query := ⟨⟨"user", "alice", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩

/-- The one-op stream whose accepted store is exactly `W4WitnessDirect.Td`. -/
def sdDirectArmOps : List GraphOp :=
  [GraphOp.add ⟨⟨"user", "alice", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩]

/-- **THE HEADLINE AGREES AGAIN, MEASURED — ★ the single most valuable pin of this
    landing.** The driver accepts the write, the accepted store is exactly
    `W4WitnessDirect.Td`, the state reports itself DRAINED — and the public read now answers
    `true`, matching `sem_directArm_grants` below.

    ⚠ **This `decide` was `= some (W4WitnessDirect.Td, false, true)` until (alpha) landed,
    and that `false` was a refutation of the pinned headline `graph_correct_public` at the
    project's OWN certified in-fragment witness.** The mechanism, for the record: the write
    to `approver`'s Direct storage arm re-addresses onto the leaf name `approver.0`;
    `affectedKeys`' own-key branch tested `isDerived S (node.type, node.pred)` — FALSE at a
    minted leaf name — so the write never dirtied its own key, the cascade never fired, the
    public `approver` edge was never materialised, and the state then reported itself
    DRAINED. (alpha) routes that branch through `Leaf.lean::publicOfLeaf`, the write dirties
    `("doc","approver","d1")`, and the cascade job reconciles it FROM THE STORE
    (`reconcileKeyDR`'s `checkFnR` reads `grantsOf T …`; it never consults the leaf edges),
    so the public edge is materialised.

    Revert the `affectedKeys` branch and this goes red at the exact query that refuted the
    headline. That is why it is a `decide` pin and not a deleted refutation. -/
theorem graphRunOps_directArm_agrees :
    ((graphRunOps W4WitnessDirect.Sd sdDirectArmOps).map
        (fun p => (p.2, GraphModel.checkPublic p.1 sdDirectArmQuery,
                   drainedB W4WitnessDirect.Sd p.1)))
      = some (W4WitnessDirect.Td, true, true) := by
  decide

/-- …and the reference semantics GRANTS it. Decided independently of the index side, so
    neither is inferred from the other — which is what makes the pair an AGREEMENT rather
    than a restatement. -/
theorem sem_directArm_grants :
    sem W4WitnessDirect.Sd W4WitnessDirect.Td sdDirectArmQuery = true := by
  decide

/-- The same agreement on the RAW read `GraphModel.check` (the public fence is not what is
    doing the work here: `approver` is a declared key, so `publicOfLeaf` returns `none` and
    `checkPublic` reduces to `check`). This is the surface `graph_correct` itself is stated
    over. -/
theorem graphRunOps_directArm_agrees_check :
    ((graphRunOps W4WitnessDirect.Sd sdDirectArmOps).map
        (fun p => (p.2, GraphModel.check p.1 sdDirectArmQuery,
                   drainedB W4WitnessDirect.Sd p.1)))
      = some (W4WitnessDirect.Td, true, true) := by
  decide

/-- `graph_correct`'s extra leaf-fence hypothesis is SATISFIED at the witness query, so the
    fence is not what makes the agreement above hold. -/
theorem sdDirectArm_not_leaf :
    publicOfLeaf W4WitnessDirect.Sd "doc" "approver" = none := by
  decide

/-- **`graph_correct`'s conclusion, INSTANTIATED at the witness that used to refute it.**
    Every hypothesis discharged from a pre-existing declaration — `GraphAdmission` /
    `W4Fragment` from `W4WitnessDirect.admission` / `::w4fragment`, `ReachedBy` from
    `graphRunOps_reached` (a genuine chain state, not a driver artefact), `Drained` from
    `drainedB_iff`, the query-scope side conditions by `decide`, the leaf fence from
    `sdDirectArm_not_leaf` — and the conclusion HOLDS: both sides are `true`.

    ⚠ Stated as a standalone equation rather than as `graph_correct` applied, deliberately.
    It was written while `graph_correct` still inherited `sorryAx` through a staged sorry, so
    applying the headline would have proved nothing; it composes two independent `decide`s
    instead (`graphRunOps_directArm_agrees_check` and `sem_directArm_grants`). That sorry is
    discharged (2026-09-05 round 2) and the headline is now `sorryAx`-free, but the
    standalone form is KEPT: it is an EXECUTABLE check of the driver at the witness that once
    refuted the headline, which `graph_correct` applied would not be. -/
theorem graphRunOps_directArm_check_eq_sem :
    ∃ σ : GraphState,
      graphRunOps W4WitnessDirect.Sd sdDirectArmOps = some (σ, W4WitnessDirect.Td)
        ∧ ReachedBy σ W4WitnessDirect.Sd W4WitnessDirect.Td
        ∧ Drained W4WitnessDirect.Sd σ
        ∧ GraphModel.check σ sdDirectArmQuery
            = sem W4WitnessDirect.Sd W4WitnessDirect.Td sdDirectArmQuery := by
  have hd := graphRunOps_directArm_agrees_check
  cases hopt : graphRunOps W4WitnessDirect.Sd sdDirectArmOps with
  | none => rw [hopt] at hd; simp at hd
  | some p =>
      obtain ⟨σ0, T0⟩ := p
      rw [hopt] at hd
      simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at hd
      obtain ⟨hT, hchk, hdr⟩ := hd
      subst hT
      exact ⟨σ0, rfl, graphRunOps_reached hopt,
        (drainedB_iff W4WitnessDirect.Sd σ0).mp hdr,
        by rw [hchk, sem_directArm_grants]⟩

/-- **★ The headline `backend_equivalence` (T3) at a DRIVER-BUILT state — the first
    concrete instance of the project's namesake theorem (2026-09-06).**

    `graphRunOps_directArm_check_eq_sem` above hands over a genuine chain state `σ`
    (produced by `graphRunOps`, with `ReachedBy` and `Drained` discharged from the run
    itself); this theorem applies `backend_equivalence` to it, so the SET-ENGINE model's
    answer equals the GRAPH index's public answer at that state — and the last conjunct
    pins that the agreed answer is a GRANT (`true`), not a vacuous double-deny.

    Why it is new: until 2026-09-06 T3 carried `(hValid : AllValid T)` over an `opaque`
    predicate, so it could not be applied at any non-empty concrete store; every
    executable witness in this file stopped at T2b. Companion (universally quantified
    over the reached state): `FullScope.lean::W4WitnessDirect.equivalence_applies`. -/
theorem graphRunOps_directArm_backend_equivalence :
    ∃ σ : GraphState,
      graphRunOps W4WitnessDirect.Sd sdDirectArmOps = some (σ, W4WitnessDirect.Td)
        ∧ ReachedBy σ W4WitnessDirect.Sd W4WitnessDirect.Td
        ∧ Drained W4WitnessDirect.Sd σ
        ∧ SetEngineModel.check W4WitnessDirect.Sd W4WitnessDirect.Td sdDirectArmQuery
            = GraphModel.checkPublic σ sdDirectArmQuery
        ∧ SetEngineModel.check W4WitnessDirect.Sd W4WitnessDirect.Td sdDirectArmQuery
            = true := by
  obtain ⟨σ, hrun, h, hq, _⟩ := graphRunOps_directArm_check_eq_sem
  refine ⟨σ, hrun, h, hq, ?_, ?_⟩
  · exact backend_equivalence sdDirectArmQuery W4WitnessDirect.admission
      W4WitnessDirect.w4fragment h hq (by decide) (by decide)
  · rw [setEngine_correct]; exact sem_directArm_grants

set_option maxHeartbeats 4000000 in
/-- **The agreement is not an artefact of the one-tuple store.** It reproduces at
    `W4WitnessDirect.Td4`, the four-tuple CORPUS store that `::admission4` / `::w4fragment4`
    certify — the store the driver-vs-Python conformance leg actually runs. Alice's grant is
    granted by the index and by `sem`; the state still reports itself drained. Was
    `some (W4WitnessDirect.Td4, false, true)` before (alpha).
    (`Td4` is reversed into an op stream because `graphRunOpsAux` conses each accepted tuple
    onto the store, so replaying it in reverse lands the store back at `Td4` exactly.) -/
theorem graphRunOps_directArm_agrees_corpus :
    ((graphRunOps W4WitnessDirect.Sd (W4WitnessDirect.Td4.reverse.map GraphOp.add)).map
        (fun p => (p.2, GraphModel.checkPublic p.1 sdDirectArmQuery,
                   drainedB W4WitnessDirect.Sd p.1)))
      = some (W4WitnessDirect.Td4, true, true) := by
  decide

/-! ## ⚠ HISTORY — "THE STALENESS TRAP" AND ALL FOUR `_explicit` BRIDGES ARE GONE

**What was here (rounds 4–5, and round 1 of 2026-09-05).** Four staged `sorry`s, each with a
kernel refutation of the statement it stood for, plus an `*_explicit` bridge per pair and a
`#check <refuted> <explicit> : False` composing them. The bridges existed because a
refutation is stated in a `¬ ∀` form restated BY HAND, and a later round could narrow the
named theorem until its `sorry` vanished while the hand-copied lookalike next to it still
compiled and still read "FALSE" — nothing going red. Each bridge was the named theorem
eta-expanded into the refutation's binder shape, so drift broke the bridge.

**Why they are all deleted (2026-09-05 rounds 1–2).** All four statements are now THEOREMS:
R5 (both legs fold `rewriteClosureL S (rawWriteTuples S t)`, and `untOccCount` sums it)
discharged the three OccCount ones; (alpha) plus the routing obligation
(`CascadeStrataSettle.lean::rawWriteRels_ne_nil_of_exprDirectsAll`) discharged
`writeLeg_own_key_dirty`. A bridge to a theorem that is no longer refuted is dead weight,
and a `#check … : False` that no longer has a `False` to print is worse than dead.

**Two lessons kept, because they outlive the particular refutations.**
* A `#check <refutation> <bridge>` line prints `… : False` whether or not the bridge
  type-checks; only the ERROR line carries the assurance. Never read the printed line as
  evidence. (Carried in `CascadeStrataSettle.lean::swTw_own_key_dirty`'s docstring too.)
* The narrowest plausible weakening of R3 — its guard gaining `NotLeafName b.pred` — was
  named and REFUSED (`CascadeStrata.lean`'s section note); the fix was the state function,
  not the guard. R5 is what made that possible.

**What replaced them, at the same fixtures**, so a revert reddens rather than passing
silently: `graphRunOps_directArm_agrees` / `::_agrees_check` / `::_agrees_corpus` /
`::graphRunOps_directArm_check_eq_sem` here; `CascadeStrata.lean::lrV_untOccCount_leaf_one`,
`::tlUsEditor_srcOccCount_agrees`, `::tvDer_srcOccCount_agrees`,
`::writeThenRemove_no_leaf_edge`; `RemoveOccCount.lean::reachedByW3d2E_untOccCount_leaf_pinned`;
`CascadeStrataSettle.lean::swTw_own_key_dirty` and `::tvDer_own_key_not_dirty` (the
necessity control for the routing premise). -/

/-! ## ★ THE REPAIR SPACE, CLOSED BY LANDING THE FLIP RATHER THAN BY A COUNTEREXAMPLE

⚠ **HISTORY.** Before R5 + (alpha) there were FOUR staged `sorry`s, each with a kernel
refutation of the statement it stood for (`writeLeg_own_key_dirty_refuted`,
`reachedByW3d2_untOccCount_refuted`, `reachedByW3d2_srcOccCount_refuted`,
`reachedByW3d2E_untOccCount_refuted`), plus `*_explicit` bridges so each refutation provably
targeted the NAMED theorem rather than a hand-copied lookalike. ALL FOUR statements are now
theorems, and every refutation and bridge is deleted: R5 discharged the three OccCount ones,
and (alpha) plus the routing obligation
(`CascadeStrataSettle.lean::rawWriteRels_ne_nil_of_exprDirectsAll`) discharged
`writeLeg_own_key_dirty`.

**What that still leaves open, and what this section closes.** A `_refuted` kills exactly ONE
sentence. It does not say the *repair space* is empty — and the repairs are what a later round
will actually reach for. Three are obvious enough that they will be tried:

1. **Redefine (or fork) `untOccCount`.** The write leg now materialises the leaf-routed
   closure, so "make `untOccCount` count that instead" looks like a one-line fix.
2. **Add the admission bundle.** The oldest move in this tree: if a statement is false, assume
   `GraphAdmission` and hope the witness falls outside it.
3. **Restrict to drained states.** `graph_correct` already carries `Drained`, so adding it to
   the ref-count invariant looks free.

⚠ **HOW R5 ANSWERED THAT, and why it is not repair (1) in disguise.** The impossibility
theorem quantified over the REPAIR (`∃ f : Schema → Store → NodeKey → NodeKey → Nat`), so
repair (1) — "redefine `untOccCount`" — really was closed while the flip sat on the write
leg alone. Its proof needed TWO reachable drained states over the SAME store disagreeing on
one edge count, and it got them from the LEAK. R5 does not redefine the invariant to dodge
the counterexample; it changes a STATE FUNCTION (`removeLoggedRules`) so the two states
COINCIDE, which the deleted docstring itself named as "the only escape". Repair (2) (assume
`GraphAdmission`) and repair (3) (assume `Drained`) were never taken, and are not taken now:
`reachedByW3d2_untOccCount` and `reachedByW3d2E_untOccCount` carry neither.

The impossibility block (`leakState_reached_drained`,
`reachedBy_edgeCount_not_store_indexed`, `reachedByW3d2E_untOccCount_admitted_drained_explicit`,
`reachedByW3d2E_untOccCount_refuted_of_general` and its `#check`) is DELETED because its
statements are now false, and replaced by the positive pins below. -/

/-- The `SlV` witness schema admits the EMPTY store under the FULL `GraphAdmission` bundle,
    including the two fields the flip added (`noLeafSubjects`, `keysNonempty`). Discharged
    field-by-field rather than by one `decide` because `WF` / `Stratifiable` /
    `TtuTuplesetsDirect` / `RewriteMatchDeclared` / `StoreValidRulesD` carry no `Decidable`
    instance (measured 2026-09-05: `failed to synthesize Decidable (WF LeafRuleWitness.SlV)`).
    `ttuNotLeaf` arrives through
    `CascadeStable.lean::ttuTargetsSat_notLeafName_of_noLeafSubjects` — i.e. off the new
    admission field, the same route obligation (D) threads. -/
theorem slV_admission_nil : GraphAdmission LeafRuleWitness.SlV ([] : Store) := by
  refine ⟨LeafRuleWitness.slV_wf, by unfold NodupKeys; decide, by unfold Stratifiable; decide,
    by unfold TtuTuplesetsDirect; decide, by unfold RewriteMatchDeclared; decide,
    ⟨fun _ => 0, by decide, fun _ => Nat.zero_le _⟩, by decide, by decide, ?_,
    ttuTargetsSat_notLeafName_of_noLeafSubjects (by decide), by decide, by decide,
    by decide, by decide⟩
  intro t ht
  simp at ht

/-- **THE IMPOSSIBILITY ARGUMENT'S TWO WITNESSES ARE NOW THE SAME COUNT** — the positive
    replacement for the deleted `leakState_reached_drained` / `emptyState_reached_drained` /
    `reachedBy_edgeCount_not_store_indexed` block.

    The deleted impossibility theorem said: NO function of `(S, T)` is the untainted edge
    count on the operational chain — proved from TWO `ReachedBy`, `Drained`, `GraphAdmission`
    states over the SAME empty store disagreeing on ONE edge count (the round-tripped state
    had 1, the initial state 0). It got that pair from the LEAK. R5 destroys the pair: with
    symmetric legs the round trip returns the edge multiset to its start, so both states
    count 0 and there is nothing to disagree about. `untOccCount`-over-L IS such a function
    (`RemoveOccCount.lean::reachedByW3d2E_untOccCount`), which is the constructive form of
    the same fact.

    ⚠ The deleted theorem was NOT wrong when it was written and is not being suppressed: its
    hypothesis "the flip is landed on the write leg only" is what R5 removed. This pin is
    what a regression would trip — restore the asymmetry and the round-tripped state's count
    goes back to 1. -/
theorem roundTripState_reached_drained_count_zero :
    ∃ σ : GraphState,
      ReachedBy σ LeafRuleWitness.SlV ([] : Store)
        ∧ Drained LeafRuleWitness.SlV σ
        ∧ σ.edges.count
            (subjNode ⟨"user", "alice", BARE⟩,
             objNode ⟨"doc", "d1"⟩ (leafPred "viewer" 0)) = 0 := by
  obtain ⟨σ0, hopt, hre, hdr, -, -, -⟩ := graphRunOps_writeRemove_internal_agrees
  refine ⟨σ0, hre, hdr, ?_⟩
  have hneu := graphRunOps_writeRemove_edge_neutral
  rw [hopt] at hneu
  simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at hneu
  rw [hneu.1]
  decide

/-- The initial state over the same schema and the same (empty) store, which is reachable and
    drained for free. Post-R5 it agrees with the round-tripped state above at 0 — the two
    states the impossibility argument used to separate. -/
theorem emptyState_reached_drained :
    ReachedBy (emptyState LeafRuleWitness.SlV) LeafRuleWitness.SlV ([] : Store)
      ∧ Drained LeafRuleWitness.SlV (emptyState LeafRuleWitness.SlV)
      ∧ (emptyState LeafRuleWitness.SlV).edges.count
          (subjNode ⟨"user", "alice", BARE⟩,
           objNode ⟨"doc", "d1"⟩ (leafPred "viewer" 0)) = 0 :=
  ⟨ReachedByW3d2E.empty _, (drainedB_iff _ _).mp (by decide), by decide⟩

/-- **The scope marker, kept.** The deleted refutations all fired at a MINTED LEAF target.
    Recorded as a positive fact because it is still the reason the `isLeafPred`-guarded
    variants were strictly weaker (and hence redundant once the unguarded forms became
    true), and the reason `count_edgeOfTuple_closureL_of_notLeaf` needs its guard.
    (Was `leak_target_is_leaf_named`; renamed with `writeExtraLeafQuery` for the same
    reason — the leak is closed, the leaf-named write extra is not.) -/
theorem writeExtra_target_is_leaf_named :
    ¬ NotLeafName (objNode ⟨"doc", "d1"⟩ (leafPred "viewer" 0)).pred := by
  decide

/-- The `SlV` write leg collapses to TWO logged steps — the write itself and its `viewer.0`
    leaf copy — pinned as an equation so the `decide` below runs on a concrete state instead
    of re-reducing the leaf-routed closure (the heartbeat trap `lrV_chain`'s docstring
    records). Same device as `CascadeStrataSettle.lean::swTw_writeLeg_eq`. -/
theorem lrV_writeLeg_eq :
    (emptyState LeafRuleWitness.SlV).writeLoggedRules LeafRuleWitness.SlV
        LeafRuleWitness.tlEditor
      = ((emptyState LeafRuleWitness.SlV).writeLoggedOne LeafRuleWitness.tlEditor).writeLoggedOne
          ⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩ := by
  unfold GraphState.writeLoggedRules
  rw [lrV_closureL_eq]
  rfl

/-- **The LOW-chain scope boundary, promoted from a docstring measurement to a kernel fact.**
    The post-write `SlV` state is NOT drained. Two consequences, and they pull in opposite
    directions, so quoting either alone misreports the round:

    * It is why a write/remove round trip is unavailable INSIDE `ReachedByW3d2`
      (`.remove` carries `hdrain : cascadeKeys S σ = []`), so any statement about one has to
      be made over the op-driver's `ReachedBy` chain, where `graphRunOpsAux` supplies the
      drain. That was asserted in prose by an earlier round — "measured 2026-09-05: `decide`
      refutes `cascadeKeys SlV … = []`" — and a measurement recorded only in a docstring is
      the thing `docs/sabotage-procedure.md` says not to rely on; this is it as a theorem.
    * It stays TRUE under (alpha) and becomes MORE informative: with the own-key branch
      wired, a post-write state has a genuinely non-empty key set, so it is not drained for
      a substantive reason rather than an incidental one. That is the fact justifying the
      driver's drain after every op, and it is why `removeGateB`'s `drainedB` conjunct is
      now a real precondition on a remove rather than a formality. -/
theorem lrV_writeLeg_not_drained :
    ¬ Drained LeafRuleWitness.SlV
        ((emptyState LeafRuleWitness.SlV).writeLoggedRules LeafRuleWitness.SlV
          LeafRuleWitness.tlEditor) := by
  rw [lrV_writeLeg_eq]
  decide

/-! ### ⚠ THE PROJECTION TRAP — a green `¬ ∃ f` on the LOW chain that is NOT evidence

Recorded because this round walked into it and stopped one `#print axioms` short of shipping
it, and the next round will reach for the same handle.

⚠ **The specific trap below is HISTORICAL — the theorem it was about
(`reachedBy_edgeCount_not_store_indexed`) is deleted, R5 having made an `(S,T)`-indexed edge
count exist. The LESSON is not historical and is why the section stays: after any landing
that leaves a staged `sorry`, a green proof that routes through a contaminated lemma is not
evidence, and `#print axioms` is the only thing that tells them apart.**

The obvious way to lift the (now deleted) `reachedBy_edgeCount_not_store_indexed` from the
operational chain to the LOW `ReachedByW3d2` chain was the existing projection
`CascadeStrataSettle.lean::reachedByW3d2C_toW3d2 ∘ CascadeStrataAssemble.lean::reachedByW3d2E_toC`:
the leaked state is `ReachedBy`-reachable, so project it and re-run the same two-state
argument. **It works, in the sense that it compiles.** Measured 2026-09-05: the whole
seventeen-premise bundle of `reachedByW3d2E_toC` IS dischargeable at `SlV` with the empty
store — `WF` from `LeafRuleWitness.slV_wf`, `LeafScope` from `leafScope_SlV`, the two
`ComputedOnly`-shaped carries by enumerating `SlV.keys` through
`LeafRules.lean::mem_keys_of_isDerived` (only `("doc","viewer")` is derived, and its
`excl (computed …) (computed …)` body is `ComputedOnly` with both `computedRefs` untainted, so
the nested carry is vacuous), the three store carries vacuously at `[]`, and terminality from
`LeafRuleWitness.lrV_untainted_layer_silent` (`schemaRewrites SlV = []`). The resulting
`¬ ∃ f` over `ReachedByW3d2` elaborates green.

**It is worthless as evidence, and that is why it is not in this file.** `#print axioms` on
the projection reports `[propext, sorryAx, Classical.choice, Quot.sound]`: `reachedByW3d2E_toC`
is itself one of the forty `sorryAx`-contaminated entries of `formal/audited_theorems.txt`
after the flip (re-measured this round: **40 of 584**, `#print axioms` over every audited
name). A `¬ ∃ f` whose proof already assumes a `sorry` proves nothing at all — it is the house
failure mode wearing the costume of the fix for the house failure mode.

Consequences, stated so nobody re-derives them:
* The LOW-chain sites (`CascadeStrata.lean::reachedByW3d2_untOccCount` and
  `::reachedByW3d2_srcOccCount`) are now THEOREMS, so nothing there needs a repair at all.
  The contamination count was **40 of 584** audited names with four staged sorries, **17 of
  584** with one, and **0** once the last one landed (2026-09-05 round 2). Those are dated
  measurements, not a standing claim — re-measure with `#print axioms`, do not quote them.
* **While ANY staged `sorry` remains, every route through a contaminated lemma yields green
  theorems that are not evidence.** The mechanical guard already exists and is the one to
  use: the axiom audit (`Audit.lean` + `formal/audited_theorems.txt`, gated by `verify.sh`'s
  `lean` phase). Run `#print axioms` on any new refutation before believing it. -/

/-- The `LeafWitness.Sw` fixture admits its OWN one-tuple store under the full
    `GraphAdmission` bundle — so the derived `approver` write really is inside the admitted
    fragment, not a degenerate schema the bundle would have thrown out. Same field-by-field
    discharge as `slV_admission_nil`; `storeValid` takes the `Or.inr` (derived) arm, whose
    `Direct` storage arm under the `excl` is what makes the write legal. -/
theorem swTw_admission : GraphAdmission LeafWitness.Sw [LeafWitness.tw] := by
  refine ⟨LeafWitness.wf, by unfold NodupKeys; decide, by unfold Stratifiable; decide,
    by unfold TtuTuplesetsDirect; decide, by unfold RewriteMatchDeclared; decide,
    ⟨fun _ => 0, by decide, fun _ => Nat.zero_le _⟩, by decide, by decide, ?_,
    ttuTargetsSat_notLeafName_of_noLeafSubjects (by decide), by decide, by decide,
    by decide, by decide⟩
  intro t ht
  simp only [List.mem_singleton] at ht
  subst ht
  exact Or.inr ⟨by decide, rfl,
    .excl (.union (.direct [("user", BARE, false)]) (.computed "viewer")) (.computed "banned"),
    [("user", BARE, false)], rfl, by decide, by decide, by decide⟩

/-! ⚠ **`writeLeg_own_key_dirty_admitted_explicit`, `::_refuted_under_admission` and their
`#check` were DELETED by step (alpha).** They were the "repair (2)" trap: the witness was a
reachable pre-state whose POST-write store `[LeafWitness.tw]` satisfied the WHOLE admission
bundle (`swTw_admission`) and whose own key was still not dirtied, proving that assuming
`GraphAdmission` did not rescue the theorem — the gap really was the branch-(α) hole in
`Cascade.lean::affectedKeys`' own-key arm. (alpha) closed that hole, so this witness now
DIRTIES the key (`CascadeStrataSettle.lean::swTw_own_key_dirty`) and the refutation is false.
The second counterexample — `CascadeStrata.lean::tvDer`, whose mechanism is routing rather
than admission — survives only as a NECESSITY CONTROL
(`CascadeStrataSettle.lean::tvDer_own_key_not_dirty`), because
`::tvDer_not_storeValidD` shows it is OUTSIDE `StoreValidRulesD`: admission really does
exclude it, which is exactly why the theorem's extra premise is the ROUTING obligation
`rawWriteRels S t ≠ []` — DISCHARGED from `StoreValidRulesD` by
`CascadeStrataSettle.lean::rawWriteRels_ne_nil_of_exprDirectsAll` — and not a new
`GraphAdmission` field. Assuming the routing would have been the model assuming the very
thing it exists to model.

⚠ **THE LESSON THIS BLOCK CARRIED, KEPT — it outlives the refutation.** Its instrument
control (2026-09-05) pointed the `#check` at a bridge whose statement was NOT the refuted
one (`GraphAdmission S T` in place of `GraphAdmission S (t :: T)`, a difference a reader
skims straight past). The composition failed with an `Application type mismatch` — AND the
`#check` line still printed `writeLeg_own_key_dirty_refuted_under_admission sorry : False`.
So reading a build log for `: False` is NOT enough: the error line is what carries the
assurance. That lesson is also recorded on `swTw_own_key_dirty`, which is where a future
reader is more likely to look. -/

/-! ## ★ THE EDGE COUNT IS STORE-INDEXED — UNGUARDED, post-R5

⚠ **HISTORY.** This section used to package the `_notLeaf` REPAIR: the impossibility
theorem said no function of `(S, T)` is the untainted edge count, and the answer was to
fence out the one class the R3 guard `isDerived S (b.type,b.pred) = false` does not exclude
— a MINTED LEAF NAME, which is not a declared key. `reachedByW3d2E_edgeCount_store_indexed_offLeaf`
and `reachedByW3d2E_untOccCount_notLeaf_of_admission` were that packaging.

R5 removes the need for the guard entirely, so the guarded twin is strictly weaker and both
it and its packaging are deleted. The `∃ f` below is the same statement with the
`isLeafPred b.pred = false` premise REMOVED — a strengthening — and its witness is still
`untOccCount`, now summing the leaf-routed closure both legs fold. `hmd`/`hnd` also drop
out: the unguarded `reachedByW3d2E_untOccCount` needs neither. -/

/-- **The edge count IS store-indexed, with no leaf guard.** Strictly stronger than the
    deleted `reachedByW3d2E_edgeCount_store_indexed_offLeaf` (which additionally required
    `isLeafPred b.pred = false` and the two threaded rewrite-set premises), and the
    constructive contradictory of the deleted `reachedBy_edgeCount_not_store_indexed`.
    Doubles as a staleness trap on `RemoveOccCount.lean::reachedByW3d2E_untOccCount`: the
    statement is hand-copied, so any drift in that theorem's binders breaks this
    declaration. `sorryAx`-free. -/
theorem reachedByW3d2E_edgeCount_store_indexed :
    ∃ f : Schema → Store → NodeKey → NodeKey → Nat,
      ∀ (σ : GraphState) (S : Schema) (T : Store),
        ReachedByW3d2E σ S T →
          ∀ a b : NodeKey, isDerived S (b.type, b.pred) = false →
              σ.edges.count (a, b) = f S T a b :=
  ⟨untOccCount, fun _ _ _ h => reachedByW3d2E_untOccCount h⟩

/-- `SlV` admits the ONE-ELEMENT store `[tlEditor]` under the full 13-field bundle. Round 5
    landed `slV_admission_nil` at the EMPTY store, which cannot exercise `storeValid`; this
    one differs from it in exactly that field, taking `StoreValidRulesD`'s untainted arm
    (`editor := direct [user]`, so `exprDirects` has the matching restriction). All twelve
    schema-only fields are `slV_admission_nil`'s, verbatim — including `ttuNotLeaf` through
    `ttuTargetsSat_notLeafName_of_noLeafSubjects`, i.e. off the flip's new field. -/
theorem slV_admission_tlEditor :
    GraphAdmission LeafRuleWitness.SlV [LeafRuleWitness.tlEditor] := by
  refine ⟨LeafRuleWitness.slV_wf, by unfold NodupKeys; decide, by unfold Stratifiable; decide,
    by unfold TtuTuplesetsDirect; decide, by unfold RewriteMatchDeclared; decide,
    ⟨fun _ => 0, by decide, fun _ => Nat.zero_le _⟩, by decide, by decide, ?_,
    ttuTargetsSat_notLeafName_of_noLeafSubjects (by decide), by decide, by decide,
    by decide, by decide⟩
  intro t ht
  simp only [List.mem_singleton] at ht
  subst ht
  exact Or.inl ⟨by decide, .direct [("user", BARE, false)], [("user", BARE, false)],
    by decide, by decide, by decide⟩

/-- **R3 is CONTENTFUL at an ADMITTED, reachable, post-write state.** Not "the guards are
    satisfiable somewhere" but "the invariant computes a NONZERO edge count at the fixture
    whose LEAF target used to refute it". A `= 1` conclusion rules out the degenerate
    reading of a count invariant: one that only ever said `0 = 0` would be equally "true"
    and would tell a reader nothing.

    ⚠ Post-R5 the interesting instance moved. It used to be stated at `doc:d1#editor`, the
    ordinary untainted target, because the LEAF target `doc:d1#viewer.0` was exactly where
    the unrepaired invariant was refuted. Now the invariant holds at BOTH, so this is stated
    at the LEAF one — the harder instance, and the one that goes red if either leg is
    re-pointed back at the plain closure. The `editor` instance is kept as
    `RemoveOccCount.lean::reachedByW3d2E_untOccCount_nonleaf_pinned`. -/
theorem reachedByW3d2E_untOccCount_admitted_nonvacuous :
    ((emptyState LeafRuleWitness.SlV).writeLoggedRules LeafRuleWitness.SlV
        LeafRuleWitness.tlEditor).edges.count
        (subjNode ⟨"user", "alice", BARE⟩,
         objNode ⟨"doc", "d1"⟩ (leafPred "viewer" 0)) = 1 :=
  reachedByW3d2E_untOccCount_leaf_pinned

end Zanzibar
