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

end Zanzibar
