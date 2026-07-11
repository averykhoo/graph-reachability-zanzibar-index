import ZanzibarProofs.GraphIndex.CascadeInv

/-!
# W3d-1c piece B — the audit enumeration + discharging `W3dJobCoverage` (ROADMAP W3d-1c)

`index_v4/processor.py:394-441` (`reconcile`'s per-pass audit enumeration): every pass
re-derives the store-supported concretes of every operand leaf (`_leaf_concretes`), the
persisted incoming R-node concretes (the edge holders), and the persisted `neg`/`upos`
members, then wholesale-rewrites the row + diff-audits the edges. `W3dJobCoverage`
(`CascadeSettle.lean`) is the `sem`-level content of that enumeration; here it was
carried as a chain-side hypothesis on each cascade leg. This file discharges it as a
THEOREM of a state-derived enumeration — making `graph_correct_w3d` / `reachedByW3dC_inv`
unconditional.

## The spine: `checkFn` = `coveredFn` off the concrete-specific probes

For a concrete (star-free) subject `s`, each operand leaf read decomposes POINTWISE:

  `probeNonDerived σ ⟨s, r', ⟨dt,on⟩⟩`
    `= probeNonDerived σ ⟨starSubj s.shape, r', ⟨dt,on⟩⟩`   (probes 2/4: `wAny`-sourced)
      `∨ σ.reach (subjNode s) (objNode ⟨dt,on⟩ r')`          (probe 1: concrete-specific)
      `∨ σ.reach (subjNode s) (wAllNode dt r')`              (probe 3: concrete-specific)

because `subjNode (starSubj sh) = wAnyNode sh` and the star subject's probes 2/4 are
dead (`name = STAR`). So a subject `s` triggering NEITHER concrete-specific probe at ANY
leaf of a `ComputedOnly` `e` reads exactly like its shape's star — `evalE` congruence,
no monotonicity, exclusion-safe (`checkFn_eq_coveredFn_of_no_extra`). -/

namespace Zanzibar

open GraphModel

/-- **The per-leaf concrete decomposition.** For a star-free subject `s` and a star-free
    object name `on`, the leaf read is its shape-star's read OR one of the two
    concrete-specific reach probes (into the object node or the `w_all` node). Pure
    boolean algebra over `probeNonDerived`'s four disjuncts: the concrete subject's
    probes 2/4 (`wAny`-sourced) are exactly the star subject's own probes 1/3
    (`subjNode (starSubj sh) = wAnyNode sh`). -/
theorem probeNonDerived_concrete_decomp (σ : GraphState) (s : SubjectRef)
    (dt on r' : String) (hsn : s.name ≠ STAR) (hon : on ≠ STAR) :
    probeNonDerived σ ⟨s, r', ⟨dt, on⟩⟩
      = (probeNonDerived σ ⟨starSubj s.shape, r', ⟨dt, on⟩⟩
         || σ.reach (subjNode s) (objNode ⟨dt, on⟩ r')
         || σ.reach (subjNode s) (wAllNode dt r')) := by
  unfold probeNonDerived
  have hstar : (starSubj s.shape).name = STAR := rfl
  have hsub : subjNode (starSubj s.shape) = wAnyNode s.shape := by
    unfold subjNode starSubj wAnyNode; simp
  have hsn' : (s.name == STAR) = false := beq_eq_false_iff_ne.mpr hsn
  have hon' : (on == STAR) = false := beq_eq_false_iff_ne.mpr hon
  simp only [hstar, hsub, starSubj_shape, bne, hsn', hon', beq_self_eq_true,
    Bool.not_false, Bool.not_true, Bool.true_and, Bool.false_and,
    Bool.and_true, Bool.or_false]
  -- now a pure boolean identity in the ≤4 reach atoms
  cases σ.reach (subjNode s) (objNode ⟨dt, on⟩ r') <;>
    cases σ.reach (wAnyNode s.shape) (objNode ⟨dt, on⟩ r') <;>
    cases σ.reach (subjNode s) (wAllNode dt r') <;>
    cases σ.reach (wAnyNode s.shape) (wAllNode dt r') <;> rfl

/-- **The key lemma: `checkFn` = `coveredFn` off the concrete-specific probes.** If a
    star-free subject `s` triggers NEITHER concrete-specific reach probe (into the
    object node or the `w_all` node) at ANY `computed` leaf of a `ComputedOnly` `e`,
    then its `checkFn` equals its shape-star's coverage — the leaf reads all collapse
    onto the star's reads (`probeNonDerived_concrete_decomp`), so `evalE` congruence
    (`evalE_computedOnly`) transports the whole tree. No monotonicity, exclusion-safe. -/
theorem checkFn_eq_coveredFn_of_no_extra {σ : GraphState} {T : Store} {s : SubjectRef}
    {dt on R : String} {e : Expr} (hco : ComputedOnly e)
    (hsn : s.name ≠ STAR) (hon : on ≠ STAR)
    (hno : ∀ r' ∈ computedRefs e,
      σ.reach (subjNode s) (objNode ⟨dt, on⟩ r') = false ∧
      σ.reach (subjNode s) (wAllNode dt r') = false) :
    σ.checkFn T s dt on R e = σ.coveredFn T dt on R e s.shape := by
  unfold GraphState.coveredFn GraphState.checkFn
  refine evalE_computedOnly e hco ?_
  intro r' hr'
  show GraphModel.graphRec σ s dt on r' = GraphModel.graphRec σ (starSubj s.shape) dt on r'
  unfold GraphModel.graphRec
  rw [probeNonDerived_concrete_decomp σ s dt on r' hsn hon]
  obtain ⟨h1, h3⟩ := hno r' hr'
  rw [h1, h3, Bool.or_false, Bool.or_false]

/-! ## The state-derived leaf enumeration `leafConcretes`

`processor.py:394-441` (`_leaf_concretes`): the pass enumerates the store-supported
concrete subjects of every operand leaf — those reaching the leaf's object node or its
`w_all` node. The model reads them straight off the state: every plain star-free node
that reaches a `computed`-leaf target. `nodeSubj` decodes a node back to a subject
(left-inverse of `subjNode` on plain star-free nodes). -/

/-- Decode a node to a subject reference (drop the variant). Left-inverse of `subjNode`
    on a plain star-free node. -/
def nodeSubj (u : NodeKey) : SubjectRef := ⟨u.type, u.name, u.pred⟩

@[simp] theorem nodeSubj_subjNode {s : SubjectRef} (hsn : s.name ≠ STAR) :
    nodeSubj (subjNode s) = s := by
  unfold nodeSubj subjNode; rw [if_neg hsn]

/-- Does node `u` reach some `computed`-leaf target of `e` — the object node
    `⟨dt,on⟩` under a leaf relation `r'`, or that relation's `w_all` node? -/
def hitsLeaf (σ : GraphState) (u : NodeKey) (dt on : String) (e : Expr) : Bool :=
  (computedRefs e).any (fun r' =>
    σ.reach u (objNode ⟨dt, on⟩ r') || σ.reach u (wAllNode dt r'))

/-- **The leaf concretes** — the state-derived audit enumeration: every plain
    star-free node that hits a leaf target, decoded to a subject. -/
def leafConcretes (σ : GraphState) (dt on : String) (e : Expr) : List SubjectRef :=
  (σ.nodes.filter (fun u => u.variant == Variant.plain && u.name != STAR
    && hitsLeaf σ u dt on e)).map nodeSubj

/-- The source of any reach is a node (edges-closed): a true `σ.reach u v` starts at
    an edge out of `u`, whose source is in `σ.nodes`. -/
theorem reach_source_mem_nodes {σ : GraphState}
    (hcl : ∀ e ∈ σ.edges, e.1 ∈ σ.nodes ∧ e.2 ∈ σ.nodes) {u v : NodeKey}
    (h : σ.reach u v = true) : u ∈ σ.nodes := by
  have hn := reach_sound h
  cases hn with
  | edge he => exact (hcl _ he).1
  | head he _ => exact (hcl _ he).1

/-- **Enumeration completeness for the leaf concretes.** A star-free subject `s`
    whose graph node hits a `computed` leaf of `e` is enumerated. -/
theorem mem_leafConcretes_of_hit {σ : GraphState} {s : SubjectRef} {dt on : String}
    {e : Expr} (hcl : ∀ e ∈ σ.edges, e.1 ∈ σ.nodes ∧ e.2 ∈ σ.nodes)
    (hsn : s.name ≠ STAR) {r' : String} (hr' : r' ∈ computedRefs e)
    (hhit : σ.reach (subjNode s) (objNode ⟨dt, on⟩ r') = true ∨
            σ.reach (subjNode s) (wAllNode dt r') = true) :
    s ∈ leafConcretes σ dt on e := by
  have hmem : subjNode s ∈ σ.nodes := by
    rcases hhit with h | h <;> exact reach_source_mem_nodes hcl h
  have hplain : (subjNode s).variant = Variant.plain := by
    unfold subjNode; rw [if_neg hsn]
  have hnameNe : (subjNode s).name ≠ STAR := by
    unfold subjNode; rw [if_neg hsn]; exact hsn
  have hhitb : hitsLeaf σ (subjNode s) dt on e = true := by
    unfold hitsLeaf
    rw [List.any_eq_true]
    exact ⟨r', hr', by rcases hhit with h | h <;> rw [h] <;> simp⟩
  rw [leafConcretes, List.mem_map]
  refine ⟨subjNode s, ?_, nodeSubj_subjNode hsn⟩
  rw [List.mem_filter]
  refine ⟨hmem, ?_⟩
  simp only [hplain, beq_self_eq_true, bne_iff_ne, ne_eq, hnameNe, not_false_eq_true,
    Bool.true_and, hhitb, Bool.and_true]

/-- **The bridge to the key lemma's hypothesis.** A star-free subject NOT among the
    leaf concretes triggers NEITHER concrete-specific probe at any leaf (contrapositive
    of `mem_leafConcretes_of_hit`), so `checkFn_eq_coveredFn_of_no_extra` applies. -/
theorem no_extra_of_not_mem {σ : GraphState} {s : SubjectRef} {dt on : String}
    {e : Expr} (hcl : ∀ e ∈ σ.edges, e.1 ∈ σ.nodes ∧ e.2 ∈ σ.nodes)
    (hsn : s.name ≠ STAR) (hnm : s ∉ leafConcretes σ dt on e) :
    ∀ r' ∈ computedRefs e,
      σ.reach (subjNode s) (objNode ⟨dt, on⟩ r') = false ∧
      σ.reach (subjNode s) (wAllNode dt r') = false := by
  intro r' hr'
  refine ⟨?_, ?_⟩
  · by_contra h
    exact hnm (mem_leafConcretes_of_hit hcl hsn hr' (Or.inl (by
      simpa using h)))
  · by_contra h
    exact hnm (mem_leafConcretes_of_hit hcl hsn hr' (Or.inr (by
      simpa using h)))

/-- **Combined: a non-enumerated star-free subject reads as its coverage.** The key
    lemma fed by the enumeration bridge — the exact shape the completeness clauses
    contrapose against. -/
theorem checkFn_eq_coveredFn_of_not_mem {σ : GraphState} {T : Store} {s : SubjectRef}
    {dt on R : String} {e : Expr} (hco : ComputedOnly e)
    (hcl : ∀ e ∈ σ.edges, e.1 ∈ σ.nodes ∧ e.2 ∈ σ.nodes)
    (hsn : s.name ≠ STAR) (hon : on ≠ STAR) (hnm : s ∉ leafConcretes σ dt on e) :
    σ.checkFn T s dt on R e = σ.coveredFn T dt on R e s.shape :=
  checkFn_eq_coveredFn_of_no_extra hco hsn hon (no_extra_of_not_mem hcl hsn hnm)

end Zanzibar
