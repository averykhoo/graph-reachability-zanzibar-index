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
      if foldAdmitsB σ (rewriteClosure S t) then
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
    right to construct them. -/
theorem graphRunOps_check_eq_sem {S : Schema} {ops : List GraphOp} {σ : GraphState}
    {T : Store} (hrun : graphRunOps S ops = some (σ, T)) (hdr : drainedB S σ = true)
    (hA : GraphAdmission S T) (hF : W4Fragment S T) (q : Query)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem S T q :=
  graph_correct q hA hF (graphRunOps_reached hrun) ((drainedB_iff S σ).mp hdr)
    hqs hqo

end Zanzibar
