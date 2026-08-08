import ZanzibarProofs.GraphIndex.CascadeStrataInv

/-!
# The untainted occurrence-count invariant — the ref-count made concrete (W3d remove-leg R3)

**What this file proves.** Over every state reachable by the EXISTING add-only two-round
scheduler chain `ReachedByW3d2E` (`CascadeStrataAssemble.lean`), the multiplicity of an
UNTAINTED direct edge `(a,b)` in `σ.edges` is EXACTLY the number of times that edge is
materialized across the rewrite closures of the stored writes:

    reachedByW3d2E_untOccCount :
      ReachedByW3d2E σ S T → ∀ a b, isDerived S (b.type, b.pred) = false →
        σ.edges.count (a, b) = ((T.flatMap (rewriteClosure S)).map edgeOfTuple).count (a, b)

`GraphState.edges : List (NodeKey × NodeKey)` is a MULTISET
(`GraphIndex/State.lean::GraphState.addEdge` prepends
unconditionally), so `List.count (a,b)` IS the model's `direct_edge_count`
(the ref-count maintained by `index_v4/core.py::ReachabilityIndex._add_direct_edge_unsafe`
and decremented by `::ReachabilityIndex._remove_edge_locked`).

**★ That sentence was FALSE when it was written, and is TRUE as of 2026-08-08.** It
asserts Python's UNIT for a quantity the model did not compute: until the
`rewriteClosure` dedup landed, the model counted DERIVATION PATHS while Python counted
LIVE RAW TUPLES, so on any *reconvergent* schema the two disagreed (measured
`lean=2 python=1` on `a := b or c ; b := d ; c := d`, growing `1 → 2 → 4` with the
number of chained diamonds — i.e. with SCHEMA SHAPE, not store content). The
attack-first bullet below said so in as many words, so **this file contradicted itself
and R3/R4's faithfulness claim rested on the wrong half** (house rule 5). That is what
made the dedup a model-side fix rather than a projection narrowing: it is what makes
the sentence above true. `GraphIndex/RulesWrite.lean::rewriteClosure` now mirrors
`RuleSet.apply`'s `processed` worklist dedup, per stored tuple. Two corpora
(`reconvergent_diamond`, `reconvergent_derived`) pin it; nothing in this file's proofs
changed, because the count stack is list-generic
(`count_removeLoggedRules` opens `generalize rewriteClosure S t = us`).

This theorem is the ref-count decision made
concrete: an untainted edge's ref-count is a pure occurrence count over the store's
rewrite closures — exactly the quantity R4's confluence lemma will decrement with
`removeEdgeOne` (erase-one). It seeds the shared-derivation `rc ≥ 2` case (the R1 KILL:
`viewer := editor or manager`, alice granted both ⇒ `count (alice → viewer:doc) = 2`,
one occurrence per stored grant — removing one grant decrements to 1, the edge SURVIVES).

**This is ADDITIVE.** It inducts on the existing `ReachedByW3d2E`; it adds no constructor
and touches no existing def/theorem/inductive. Not in `Audit.lean` (R3 is infrastructure).

## Attack-first findings (house rule 2; machine-checked `#eval`, scratch deleted)

* **The rc=2 shared-derivation case HOLDS.** `viewer := editor or manager`, alice granted
  both: model `count (alice → viewer:doc:1) = 2` == `Σ = 2` (one occurrence in each grant's
  rewrite closure). This is precisely the R1 KILL scenario — the statement is TRUE there.

* **★ KILL of the design's DERIVED arm (`count ∈ {0,1}`).** The design proposed a second
  arm: derived (I5 processor-owned) edges have `count ∈ {0,1}`. This is **FALSE for the
  model as written.** `#eval` on `viewer := a but not b` (write `alice@a`, cascade, write
  `bob@a`, cascade) gives `count (alice → viewer:doc:1) = 1` after the first cascade but
  **`= 4`** after the second. The model DELIBERATELY does NOT maintain `rc ≡ 1` on derived
  edges: its diffing pass `GraphIndex/ReconcileDiff.lean::GraphState.reconcileKeyD` writes
  on the guard
  `checkFn ∧ ¬covered` — it does NOT probe edge presence (`¬has_edge`) the way Python does
  (`index_v4/processor.py::DeltaProcessor._reconcile_subject`'s bare-entity tail, whose
  `has_edge` probe is `index_v4/core.py::ReachabilityIndex.direct_edge_exists_by_id`),
  so it STACKS duplicate derived copies across passes/rounds,
  compensated by making retraction a filter-ALL
  (`GraphIndex/ReconcileDiff.lean::GraphState.removeEdgePair`).
  This is the pre-existing, documented modeling decision (`ReconcileDiff.lean` header:
  "the model's `writeDirect` may stack duplicate copies across passes, so removal filters
  ALL copies"). So the faithful derived-side statement is NOT a count bound but a
  MEMBERSHIP property (filter-all zeroes the pair), which the model already carries via
  `removeEdgePair`'s design — there is nothing here to prove as `∈ {0,1}`, and asserting it
  would be a false statement. Only the UNTAINTED arm is landed.

* **[RESOLVED 2026-08-08 — kept because it is the finding that got the model fixed.]
  Faithfulness nuance on the UNTAINTED arm (Python-vs-model ref-count VALUE).** As
  originally recorded: the model's `rewriteClosure` did NOT deduplicate, while Python's
  `RuleSet.apply` DOES (worklist dedup). `#eval`-confirmed on a reconvergent (diamond)
  schema `a := b or c`, `b := d`, `c := d`, `d := [user]`, write `alice@d`: the model gave
  `count (alice → a:doc:1) = 2` (the closure listed the `a` edge twice), while Python's
  `ruleset.apply` fans out `(alice, a, doc:1)` exactly ONCE (`direct_edge_count = 1`).
  The note then argued the gap was tolerable because it is READ-INVISIBLE (reads test
  membership, not multiplicity — `reachB`/`NReaches`) and REMOVE-CONSISTENT
  (`removeLoggedRules` folds the SAME `rewriteClosure`, so add-N/remove-N both zero the
  pair together).
  **Both halves of that argument were correct and the conclusion was still wrong**, which
  is the transferable part. "It does not affect the R4/R5 membership target" is a reason
  the divergence is not URGENT; it is not a reason it is not a DEFECT. What settled it was
  house rule 5: the header above asserts Python's unit, so tolerating the gap meant
  shipping a file that contradicted itself. `rewriteClosure` now dedupes per stored tuple
  and this bullet's `count = 2` is `count = 1`.
  **Why not fix Python instead:** its `processed` worklist dedup is the TERMINATION
  mechanism, not an optimisation — `a: [user] or b ; b: a` compiles (only *derived* cycles
  raise) and loops forever without it.
  **Why not narrow projection P3 a second time** (the move that was right for the derived
  arm on 2026-07-29): that was right *because* no honest model edit made the derived arm
  agree. Here `.dedup` matches Python element-for-element, and narrowing would force
  `formal/conformance/extractor.py` to compute a path-weighted expectation — i.e.
  re-implement `rewriteClosure` in Python, destroying the harness's independence.
-/

namespace Zanzibar

open scoped List

/-! ## The occurrence-count stack now lives in `CascadeStrata.lean`

The `untOccCount` def and the count stack (`count_removeLoggedOne`, `count_removeLoggedRules`,
`untOccCount_erase`, `mem_removeLoggedRules_edges`, `count_filter_of_true`,
`count_foldl_writeDirect`, `count_writeLoggedRules`, `count_reconcileKeyDR_of_ne`,
`count_reconcileStarsKeyDR_of_ne`, `count_applyLoggedR_of_ne`, `count_reconcileJobsLR_of_ne`,
`count_runCascade2_of_ne`) were RELOCATED DOWN into `CascadeStrata.lean` (W3d remove-leg R5b-ii)
so they are available at the LOW `ReachedByW3d2` level for the R5b shadow-transport crux. They
are all about the LOW `runCascade2`/reconcile/`writeLoggedRules`/`removeLoggedRules` defs, so
they relocated cleanly. `CascadeStrata` is imported transitively here (via `CascadeStrataInv`),
so they remain visible to `reachedByW3d2E_untOccCount` below. Only `enumJobs2At_Rnode_ne` (which
cites `enumJobs2At_keyFacts` from `CascadeStrataInv`, ABOVE `CascadeStrata`) stays here. -/

/-- Every enumerated cascade job is at a DERIVED R-node, so an untainted edge's object
    endpoint differs from every job's R-node (`enumJobs2At_keyFacts` + `objNode` fields). -/
theorem enumJobs2At_Rnode_ne {S : Schema} {T : Store} {σe : GraphState}
    {keys : List (String × String × String)} {b : NodeKey}
    (hk : ∀ k ∈ keys, isDerived S (k.1, k.2.1) = true ∧ k.2.2 ≠ STAR)
    (hb : isDerived S (b.type, b.pred) = false) :
    ∀ j ∈ enumJobs2At S T σe keys, b ≠ objNode ⟨j.dt, j.on⟩ j.R := by
  intro j hj heq
  obtain ⟨_, hder, _⟩ := enumJobs2At_keyFacts hk j hj
  have ht : (objNode ⟨j.dt, j.on⟩ j.R).type = j.dt := objNode_type _ _
  have hp : (objNode ⟨j.dt, j.on⟩ j.R).pred = j.R := objNode_pred _ _
  rw [heq, ht, hp, hder] at hb
  exact Bool.noConfusion hb

/-! ## The R3 invariant over the add-only chain -/

/-- **R3 — the untainted occurrence-count invariant.** For every UNTAINTED direct edge
    `(a,b)` (`b.pred` not a derived relation of `b.type`), its ref-count in `σ.edges` is the
    total occurrence count of `(a,b)` across the stored writes' rewrite closures. By
    induction on the add-only two-round scheduler chain `ReachedByW3d2E`:
    * `empty` — no edges, empty store: both sides `0`.
    * `write t` — `count_writeLoggedRules` grows the edge count by `t`'s closure occurrences
      (`FoldAdmits` from the constructor); the store gains `t` at the front, so the Σ gains
      exactly `t`'s term (`List.flatMap_cons`/`map_append`/`count_append`).
    * `cascade` — the two-round diffing cascade touches only DERIVED R-nodes
      (`count_runCascade2_of_ne` + `enumJobs2At_Rnode_ne`), so the untainted count is
      unchanged; the store is unchanged, so the Σ is unchanged. -/
theorem reachedByW3d2E_untOccCount {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T) :
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
  | @remove σp S T t hadm _ _ _ _ _ hprev ih =>
    intro a b hb
    rw [count_removeLoggedRules (a, b) S t σp, ih a b hb, untOccCount_erase S T t a b hadm]
    omega
  | @cascade σp S T hprev ih =>
    intro a b hb
    have hkfacts : ∀ (σe : GraphState) (n : Nat),
        ∀ k ∈ cascadeKeysAbove S σe n, isDerived S (k.1, k.2.1) = true ∧ k.2.2 ≠ STAR :=
      fun σe n k hk => ⟨(mem_cascadeKeysAbove_props hk).1, (mem_cascadeKeysAbove_props hk).2.2⟩
    have h1 : ∀ j ∈ enumJobs2R1 S T σp, b ≠ objNode ⟨j.dt, j.on⟩ j.R :=
      enumJobs2At_Rnode_ne (hkfacts _ _) hb
    have h2 : ∀ j ∈ enumJobs2R2 S T σp, b ≠ objNode ⟨j.dt, j.on⟩ j.R :=
      enumJobs2At_Rnode_ne (hkfacts _ _) hb
    rw [count_runCascade2_of_ne S T σp (enumJobs2R1 S T σp) (enumJobs2R2 S T σp) h1 h2]
    exact ih a b hb

end Zanzibar
