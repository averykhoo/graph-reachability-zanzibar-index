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

`GraphState.edges : List (NodeKey × NodeKey)` is a MULTISET (`addEdge` prepends
unconditionally, `State.lean:742`), so `List.count (a,b)` IS the model's `direct_edge_count`
(the ref-count — `index_v4/core.py:686-704`). This theorem is the ref-count decision made
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
  edges: its diffing pass `reconcileKeyD` (`ReconcileDiff.lean:212`) writes on the guard
  `checkFn ∧ ¬covered` — it does NOT probe edge presence (`¬has_edge`) the way Python does
  (`processor.py:359-367`), so it STACKS duplicate derived copies across passes/rounds,
  compensated by making retraction a filter-ALL (`removeEdgePair`, `ReconcileDiff.lean:52`).
  This is the pre-existing, documented modeling decision (`ReconcileDiff.lean` header:
  "the model's `writeDirect` may stack duplicate copies across passes, so removal filters
  ALL copies"). So the faithful derived-side statement is NOT a count bound but a
  MEMBERSHIP property (filter-all zeroes the pair), which the model already carries via
  `removeEdgePair`'s design — there is nothing here to prove as `∈ {0,1}`, and asserting it
  would be a false statement. Only the UNTAINTED arm is landed.

* **Faithfulness nuance on the UNTAINTED arm (Python-vs-model ref-count VALUE).** The
  model's `rewriteClosure` does NOT deduplicate (`RulesWrite.lean:97-107`), while Python's
  `RuleSet.apply` DOES (worklist dedup). `#eval`-confirmed on a reconvergent (diamond)
  schema `a := b or c`, `b := d`, `c := d`, `d := [user]`, write `alice@d`: the model gives
  `count (alice → a:doc:1) = 2` (the closure lists the `a` edge twice), while Python's
  `ruleset.apply` fans out `(alice, a, doc:1)` exactly ONCE (`direct_edge_count = 1`). So
  this theorem faithfully characterizes the MODEL's ref-count in terms of the MODEL's
  `rewriteClosure` occurrences (the design's phrasing, "occurrences among rewriteClosure S t",
  names exactly this), but the model's ref-count VALUE exceeds Python's deduped
  `direct_edge_count` in reconvergent schemas. This over-count is READ-INVISIBLE (reads test
  membership, not multiplicity — `reachB`/`NReaches`) and REMOVE-CONSISTENT (`removeLoggedRules`
  folds the SAME `rewriteClosure`, so add-N/remove-N both zero the pair together), so it does
  not affect the membership-level confluence R4/R5 target. It DOES mean the exact ref-count
  value is not claimed Python-faithful where `rewriteClosure` is reconvergent — the exact
  scope of the pre-existing "duplicates are harmless — reachability, not counts" note
  (`RulesWrite.lean:100`), which R3 now confirms extends soundly to the remove path.
-/

namespace Zanzibar

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

/-! ## The retraction's count-shrink law -/

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

/-! ## The store-erase split of the occurrence count -/

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

/-! ## Filter preserves the count of a kept element -/

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

/-! ## The write leg — an admitted `writeDirect` fold counts occurrences -/

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

/-! ## The cascade leg — a routed diffing pass is untainted-count-inert

The diffing edge audit `reconcileKeyDR` (`CascadeStrata.lean:195`) touches ONLY edges into
the job's own terminal R-node `objNode ⟨dt,on⟩ R` — each fold step is either
`writeDirect ⟨c,R,⟨dt,on⟩⟩` (adds `(subjNode c, objNode ⟨dt,on⟩ R)`) or
`removeEdgePair (subjNode c) (objNode ⟨dt,on⟩ R)` (filters that same pair). So an edge
`(a,b)` with `b ≠ objNode ⟨dt,on⟩ R` keeps its exact count. Every cascade job is at a
DERIVED key (`enumJobs2At_keyFacts`), so an UNTAINTED `(a,b)` (`b.pred` not a derived
relation) differs from every R-node — the whole two-round cascade is untainted-count-inert. -/

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
    · -- add arm: writeDirect ⟨c, R, ⟨dt,on⟩⟩ prepends (subjNode c, objNode ⟨dt,on⟩ R)
      rw [writeDirect_edges]
      split
      · rw [List.count_cons]
        have hne : ((subjNode c, objNode ⟨dt, on⟩ R) == (a, b)) = false := by
          rw [beq_eq_false_iff_ne]
          intro h; exact hb (congrArg Prod.snd h).symm
        rw [hne]; simp
      · rfl
    · -- remove arm: removeEdgePair filters that pair, which (a,b) is not
      rw [removeEdgePair_edges]
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

/-- Every enumerated cascade job is at a DERIVED R-node, so an untainted edge's object
    endpoint differs from every job's R-node (`enumJobs2At_keyFacts` + `objNode` fields). -/
theorem enumJobs2At_Rnode_ne {S : Schema} {σe : GraphState}
    {keys : List (String × String × String)} {b : NodeKey}
    (hk : ∀ k ∈ keys, isDerived S (k.1, k.2.1) = true ∧ k.2.2 ≠ STAR)
    (hb : isDerived S (b.type, b.pred) = false) :
    ∀ j ∈ enumJobs2At S σe keys, b ≠ objNode ⟨j.dt, j.on⟩ j.R := by
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
  | @cascade σp S T hprev ih =>
    intro a b hb
    have hkfacts : ∀ (σe : GraphState) (n : Nat),
        ∀ k ∈ cascadeKeysAbove S σe n, isDerived S (k.1, k.2.1) = true ∧ k.2.2 ≠ STAR :=
      fun σe n k hk => ⟨(mem_cascadeKeysAbove_props hk).1, (mem_cascadeKeysAbove_props hk).2.2⟩
    have h1 : ∀ j ∈ enumJobs2R1 S σp, b ≠ objNode ⟨j.dt, j.on⟩ j.R :=
      enumJobs2At_Rnode_ne (hkfacts _ _) hb
    have h2 : ∀ j ∈ enumJobs2R2 S T σp, b ≠ objNode ⟨j.dt, j.on⟩ j.R :=
      enumJobs2At_Rnode_ne (hkfacts _ _) hb
    rw [count_runCascade2_of_ne S T σp (enumJobs2R1 S σp) (enumJobs2R2 S T σp) h1 h2]
    exact ih a b hb

end Zanzibar
