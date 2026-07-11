import ZanzibarProofs.GraphIndex.CascadeStrataResettle

/-!
# W3d-2 E-chain tail — piece 1: the derived-leaf concrete decomposition (ROADMAP W3d-2)

`index_v4/processor.py:394-441` (`reconcile`'s per-pass audit enumeration) at a
STRATUM-2 key reads DERIVED operand leaves — so, beyond the store-supported reach
concretes (`_leaf_concretes`, W3d-1's `leafConcretes`), it must also pull the operand
RESIDUES' `neg` ids (`_derived_leaf_neg_ids`, `processor.py:461-495`) and the persisted
`upos` ids (`:425-429`): a lower-stratum `neg`/`upos` member is EDGE-FREE (I6) so it is
invisible to the reach-probe enumeration, yet it reads differently from its shape-star
at the derived leaf. This file is the routed analog of `CascadeEnum.lean`'s
`probeNonDerived_concrete_decomp` spine — the DERIVED-leaf decomposition.

## The spine at a derived leaf

For a concrete (star-free) subject `s` and a star-free object name `on`, the derived
operand leaf read (`probeDerived`, `State.lean:552`) reads exactly like its shape-star

  `probeDerived σ ⟨s, r', ⟨dt,on⟩⟩ = res.stars.contains s.shape`   (= its star's read)

UNLESS `s` triggers one of the three concrete-specific terms: an incoming edge
(`σ.reach (subjNode s) oN`), a `res.neg` membership, or a `res.upos` membership — where
`res = (σ.residue oN r').getD ∅` and `oN = objNode ⟨dt,on⟩ r'`. Those three are exactly
the state-derived RESIDUE-NAMED candidates (`residueNamed`) plus the edge holders. So a
subject in NEITHER reads as its shape-star at the derived leaf — the routed congruence
(`evalE_computedOnly`) then transports the whole tree, exactly as W3d-1's untainted
spine did off the reach probes. -/

namespace Zanzibar

open GraphModel

/-- `graphRecR` at a DERIVED operand leaf is `probeDerived` (the routed recursion
    routes a derived key to the residue read; `processor.py:43-70, 182-188`). -/
theorem graphRecR_derived (σ : GraphState) (s : SubjectRef) {dt on r' : String}
    (h : isDerived σ.schema (dt, r') = true) :
    GraphModel.graphRecR σ s dt on r' = GraphModel.probeDerived σ ⟨s, r', ⟨dt, on⟩⟩ :=
  GraphModel.check_derived σ ⟨s, r', ⟨dt, on⟩⟩ h

/-- A star subject's derived-leaf read is exactly its shape's `stars` row. -/
theorem probeDerived_star (σ : GraphState) (sh : Shape) {dt on r' : String}
    (hon : on ≠ STAR) :
    GraphModel.probeDerived σ ⟨starSubj sh, r', ⟨dt, on⟩⟩ =
      ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).stars.contains sh := by
  obtain ⟨st, sp⟩ := sh
  rw [show starSubj (st, sp) = ⟨st, STAR, sp⟩ from rfl, probeDerived_eq σ hon, if_pos rfl]

/-- **The per-leaf DERIVED concrete decomposition.** A star-free subject that triggers
    none of the three concrete-specific terms (no incoming edge — here as `reach = false`;
    not in `res.neg`; not in `res.upos`) reads a derived leaf exactly as its shape's
    `stars` row — i.e. exactly as its shape-star would. Pure case analysis on the
    predicate over `probeDerived_eq`'s branches. -/
theorem probeDerived_concrete_off_named (σ : GraphState) {st sn sp dt on r' : String}
    (hon : on ≠ STAR) (hsn : sn ≠ STAR)
    (hnr : σ.reach (subjNode ⟨st, sn, sp⟩) (objNode ⟨dt, on⟩ r') = false)
    (hnn : ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).neg.contains
      ⟨st, sn, sp⟩ = false)
    (hnu : ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).upos.contains
      ⟨st, sn, sp⟩ = false) :
    GraphModel.probeDerived σ ⟨⟨st, sn, sp⟩, r', ⟨dt, on⟩⟩ =
      ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).stars.contains (st, sp) := by
  rw [probeDerived_eq σ hon, if_neg hsn]
  by_cases hbare : sp = BARE
  · rw [if_pos hbare, hnr, Bool.false_or, hnn, Bool.not_false, Bool.and_true]
  · rw [if_neg hbare]
    by_cases hu : ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).upos.contains
        ⟨st, sn, sp⟩ = true
    · rw [hu] at hnu; exact absurd hnu (by decide)
    · rw [Bool.not_eq_true] at hu
      rw [hu, if_neg (by decide)]
      by_cases hst : ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).stars.contains
          (st, sp) = true
      · rw [hst, if_neg (by decide), hnn, Bool.not_false]
      · rw [Bool.not_eq_true] at hst; rw [hst, if_pos (by decide)]

/-! ## The residue-named candidate enumeration (finding (c))

The state-derived enumeration Python adds at a derived-reading key: the operand
residue's `neg` and `upos` members. Edge holders reuse `CascadeEnum.edgeHolders`. -/

/-- The residue-named candidates at a derived leaf `r'` (object `⟨dt,on⟩`): the operand
    residue's `neg` ids (`_derived_leaf_neg_ids`) and `upos` ids. -/
def residueNamed (σ : GraphState) (dt on r' : String) : List SubjectRef :=
  ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).neg
    ++ ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).upos

/-- **`graphRecR` agrees with its shape-star at a derived leaf off the enumeration.**
    A star-free subject that is NOT an edge holder and NOT residue-named reads the
    derived leaf exactly as its shape-star (`probeDerived_concrete_off_named`), given
    the reach collapse (a reach into the derived R-node is a direct edge, so
    not-an-edge-holder ⇒ `reach = false`). -/
theorem graphRecR_derived_agree_off_named (σ : GraphState) {s : SubjectRef}
    {dt on r' : String} (hder : isDerived σ.schema (dt, r') = true) (hon : on ≠ STAR)
    (hsn : s.name ≠ STAR) (hne : s ∉ edgeHolders σ dt on r')
    (hnm : s ∉ residueNamed σ dt on r')
    (hcollapse : ∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
      (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) :
    GraphModel.graphRecR σ s dt on r' = GraphModel.graphRecR σ (starSubj s.shape) dt on r' := by
  obtain ⟨st, sn, sp⟩ := s
  have hsn' : sn ≠ STAR := hsn
  have hnr : σ.reach (subjNode ⟨st, sn, sp⟩) (objNode ⟨dt, on⟩ r') = false := by
    by_contra hc
    rw [Bool.not_eq_false] at hc
    exact hne (mem_edgeHolders (hcollapse _ (reach_sound hc)))
  have hnn : ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).neg.contains
      ⟨st, sn, sp⟩ = false := by
    rw [List.contains_eq_mem]
    exact decide_eq_false (fun h => hnm (List.mem_append_left _ h))
  have hnu : ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).upos.contains
      ⟨st, sn, sp⟩ = false := by
    rw [List.contains_eq_mem]
    exact decide_eq_false (fun h => hnm (List.mem_append_right _ h))
  rw [graphRecR_derived σ _ hder, graphRecR_derived σ _ hder,
    probeDerived_concrete_off_named σ hon hsn' hnr hnn hnu]
  exact (probeDerived_star σ (st, sp) hon).symm

/-- **Residue-named enumeration completeness.** A subject in `res.neg` is residue-named,
    a subject in `res.upos` is residue-named — the introduction rules the coverage
    discharge contraposes against. -/
theorem mem_residueNamed_of_neg {σ : GraphState} {dt on r' : String} {s : SubjectRef}
    (h : s ∈ ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).neg) :
    s ∈ residueNamed σ dt on r' := List.mem_append_left _ h

theorem mem_residueNamed_of_upos {σ : GraphState} {dt on r' : String} {s : SubjectRef}
    (h : s ∈ ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).upos) :
    s ∈ residueNamed σ dt on r' := List.mem_append_right _ h

end Zanzibar
