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

/-! ## The routed reads-as-star lemma (off the unified W3d-2 enumeration)

The routed analog of `CascadeEnum.checkFn_eq_coveredFn_of_not_mem`. A star-free
subject that is NOT among the leaf concretes (untainted leaves, reach-based) AND NOT
residue-named at any derived leaf reads every operand leaf exactly as its shape-star,
so the routed compiled guard `checkFnR` reads it exactly as its shape-star's. Crucially
NO reach-collapse / settledness is needed here: a reach into any leaf's object node
already makes the subject a leaf concrete (`mem_leafConcretes_of_hit`), so
`∉ leafConcretes` gives `reach = false` directly. -/

/-- **The per-leaf agreement, both leaf kinds.** Off the enumeration, `graphRecR` at
    each operand leaf reads a star-free subject exactly as its shape-star: an untainted
    leaf via `probeNonDerived_concrete_decomp` (the W3d-1 spine), a derived leaf via
    `probeDerived_concrete_off_named` (piece 1). -/
theorem graphRecR_leaf_agree {σ : GraphState} {s : SubjectRef} {dt on r' : String}
    {e : Expr} (hcl : ∀ ed ∈ σ.edges, ed.1 ∈ σ.nodes ∧ ed.2 ∈ σ.nodes)
    (hsn : s.name ≠ STAR) (hon : on ≠ STAR) (hr' : r' ∈ computedRefs e)
    (hnl : s ∉ leafConcretes σ dt on e)
    (hnm : isDerived σ.schema (dt, r') = true → s ∉ residueNamed σ dt on r') :
    GraphModel.graphRecR σ s dt on r' = GraphModel.graphRecR σ (starSubj s.shape) dt on r' := by
  by_cases hd : isDerived σ.schema (dt, r') = true
  · have hnr : σ.reach (subjNode s) (objNode ⟨dt, on⟩ r') = false := by
      by_contra hc; rw [Bool.not_eq_false] at hc
      exact hnl (mem_leafConcretes_of_hit hcl hsn hr' (Or.inl hc))
    have hnres := hnm hd
    obtain ⟨st, sn, sp⟩ := s
    have hnn : ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).neg.contains
        ⟨st, sn, sp⟩ = false := by
      rw [List.contains_eq_mem]
      exact decide_eq_false (fun h => hnres (mem_residueNamed_of_neg h))
    have hnu : ((σ.residue (objNode ⟨dt, on⟩ r') r').getD Residue.empty).upos.contains
        ⟨st, sn, sp⟩ = false := by
      rw [List.contains_eq_mem]
      exact decide_eq_false (fun h => hnres (mem_residueNamed_of_upos h))
    rw [graphRecR_derived σ _ hd, graphRecR_derived σ _ hd,
      probeDerived_concrete_off_named σ hon hsn hnr hnn hnu]
    exact (probeDerived_star σ (st, sp) hon).symm
  · rw [Bool.not_eq_true] at hd
    rw [graphRecR_eq_graphRec s on hd, graphRecR_eq_graphRec (starSubj s.shape) on hd]
    obtain ⟨h1, h3⟩ := no_extra_of_not_mem hcl hsn hnl r' hr'
    show GraphModel.graphRec σ s dt on r' = GraphModel.graphRec σ (starSubj s.shape) dt on r'
    unfold GraphModel.graphRec
    rw [probeNonDerived_concrete_decomp σ s dt on r' hsn hon, h1, h3, Bool.or_false, Bool.or_false]

/-- **The routed `checkFnR` reads a non-enumerated subject as its shape-star.** `evalE`
    congruence (`evalE_computedOnly`) over the per-leaf agreement — the routed analog of
    `checkFn_eq_coveredFn_of_not_mem`, the exact shape the W3d-2 coverage clauses
    contrapose against. -/
theorem checkFnR_eq_star_of_not_enum {σ : GraphState} {T : Store}
    {s : SubjectRef} {dt on R : String} {e : Expr} (hco : ComputedOnly e)
    (hcl : ∀ ed ∈ σ.edges, ed.1 ∈ σ.nodes ∧ ed.2 ∈ σ.nodes)
    (hsn : s.name ≠ STAR) (hon : on ≠ STAR) (hnl : s ∉ leafConcretes σ dt on e)
    (hnm : ∀ r' ∈ computedRefs e, isDerived σ.schema (dt, r') = true →
      s ∉ residueNamed σ dt on r') :
    σ.checkFnR T s dt on R e = σ.checkFnR T (starSubj s.shape) dt on R e := by
  unfold GraphState.checkFnR
  exact evalE_computedOnly e hco (fun r' hr' =>
    graphRecR_leaf_agree hcl hsn hon hr' hnl (hnm r' hr'))

/-- **The routed Direct-arm star/concrete split (`checkFnR_eq_star_of_not_enum_cd`).** The
    `ComputedOrDirect` + `DirectArmsBare` analog of `checkFnR_eq_star_of_not_enum`, gated on the
    attack-mandated `NoConcDirect` (`ReconcileStars.lean`): computed leaves ride
    `graphRecR_leaf_agree` (unchanged), bare `Direct` arms ride `directLeaf_star_of_noConc`, so
    `evalE_star_of_noConc` transports the routed read. The routed foundation the W3d-2 coverage
    clauses contrapose against for a Direct-arm operand (the concrete-grant subjects are
    enumerated separately, sub-step 2's second half). -/
theorem checkFnR_eq_star_of_not_enum_cd {σ : GraphState} {T : Store}
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hcl : ∀ ed ∈ σ.edges, ed.1 ∈ σ.nodes ∧ ed.2 ∈ σ.nodes)
    (hsn : s.name ≠ STAR) (hsp : s.predicate = BARE) (hon : on ≠ STAR)
    (hnc : NoConcDirect T s dt on R e)
    (hnl : s ∉ leafConcretes σ dt on e)
    (hnm : ∀ r' ∈ computedRefs e, isDerived σ.schema (dt, r') = true →
      s ∉ residueNamed σ dt on r') :
    σ.checkFnR T s dt on R e = σ.checkFnR T (starSubj s.shape) dt on R e := by
  unfold GraphState.checkFnR
  exact evalE_star_of_noConc hsn hsp e hcd hba hnc (fun r' hr' =>
    graphRecR_leaf_agree hcl hsn hon hr' hnl (hnm r' hr'))

/-! ## The W3d-2 enumerated job and its coverage

`enumJob2` folds the residue-named candidates into W3d-1's `enumJob`: the per-key base
list is the leaf concretes (untainted-leaf reach) UNION the residue-named subjects of
every derived leaf. The four `W3dJobCoverage` clauses are then discharged exactly as in
W3d-1 (`w3dJobCoverage_enumJob`), with the ROUTED leg context (`hbridge`/`hcovDecl`
over `checkFnR`) in place of the unrouted one and `checkFnR_eq_star_of_not_enum` in
place of `checkFn_eq_coveredFn_of_not_mem`. The leg context itself is discharged at
actual W3d-2 states in a later increment (the routed bridge holds once the derived
operand keys are settled). -/

/-- The per-key base candidate list: leaf concretes ∪ every derived leaf's
    residue-named subjects (`neg`+`upos`). -/
def enum2Base (σ : GraphState) (dt on : String) (e : Expr) : List SubjectRef :=
  leafConcretes σ dt on e ++ (computedRefs e).flatMap (fun r' => residueNamed σ dt on r')

/-- The state-derived W3d-2 enumerated job for one derived key `(dt,R)` at object `on`:
    bare base ∪ edge holders as `cands`, bare base as `negCands`, userset base as
    `uposCands` (the residue-named `neg`/`upos` now included via `enum2Base`). -/
def enumJob2 (σ : GraphState) (dt on R : String) (e : Expr) : W3cJob :=
  { dt := dt, on := on, R := R, e := e,
    cands := (enum2Base σ dt on e).filter (fun u => u.predicate == BARE)
             ++ edgeHolders σ dt on R,
    negCands := (enum2Base σ dt on e).filter (fun u => u.predicate == BARE),
    uposCands := (enum2Base σ dt on e).filter (fun u => u.predicate != BARE) }

/-- Off the base list, `checkFnR` reads a star-free subject as its shape-star. The
    bridge to `checkFnR_eq_star_of_not_enum`: `∉ enum2Base` splits into `∉ leafConcretes`
    (left) and `∉ residueNamed` at each leaf (right, via `flatMap`). -/
theorem checkFnR_eq_star_of_not_base {σ : GraphState} {T : Store} {s : SubjectRef}
    {dt on R : String} {e : Expr} (hco : ComputedOnly e)
    (hcl : ∀ ed ∈ σ.edges, ed.1 ∈ σ.nodes ∧ ed.2 ∈ σ.nodes)
    (hsn : s.name ≠ STAR) (hon : on ≠ STAR) (hnb : s ∉ enum2Base σ dt on e) :
    σ.checkFnR T s dt on R e = σ.checkFnR T (starSubj s.shape) dt on R e := by
  refine checkFnR_eq_star_of_not_enum hco hcl hsn hon
    (fun h => hnb (List.mem_append_left _ h)) ?_
  intro r' hr' _ h
  exact hnb (List.mem_append_right _ (List.mem_flatMap.mpr ⟨r', hr', h⟩))

/-- **`W3dJobCoverage` for `enumJob2` from the ROUTED leg context.** Given the routed
    read bridge (`checkFnR = sem`, subject-generic up to star-BARE) and the routed
    coverage-declaredness helper — both of which hold at a W3d-2 state whose derived
    operand keys are settled — the four coverage clauses hold for the state-derived
    `enumJob2`. Same contrapositive skeleton as `w3dJobCoverage_enumJob`. -/
theorem w3dJobCoverage_enumJob2 {S : Schema} {T : Store} {σ : GraphState}
    {dt on R : String} {e : Expr} (hco : ComputedOnly e)
    (hcl : ∀ ed ∈ σ.edges, ed.1 ∈ σ.nodes ∧ ed.2 ∈ σ.nodes) (hon : on ≠ STAR)
    (hbridge : ∀ s' : SubjectRef, (s'.name = STAR → s'.predicate = BARE) →
      σ.checkFnR T s' dt on R e = sem S T ⟨s', R, ⟨dt, on⟩⟩)
    (hcovDecl : ∀ sh : Shape, σ.checkFnR T (starSubj sh) dt on R e = true →
      sh ∈ wildcardShapes S)
    (hWSb : ∀ sh ∈ wildcardShapes S, sh.2 = BARE) :
    W3dJobCoverage S T σ (enumJob2 σ dt on R e) := by
  -- a bare base member lands in the bare filter (the `cands`/`negCands` source)
  have hbareSub : ∀ u ∈ enum2Base σ dt on e, u.predicate = BARE →
      u ∈ (enum2Base σ dt on e).filter (fun u => u.predicate == BARE) :=
    fun u hu hub => List.mem_filter.mpr ⟨hu, by simp [hub]⟩
  refine ⟨fun s hs => ?_, fun s hsb hsn hsem hunc => ?_,
    fun s hsn hcov hstar hsemF => ?_, fun s hsu hsn hsem => ?_⟩
  · -- clause (1): edge holders ⊆ cands
    exact List.mem_append_right _ (mem_edgeHolders hs)
  · -- clause (2): uncovered sem-true bare ∈ cands
    refine List.mem_append_left _ ?_
    by_contra hnm
    have hnb : s ∉ enum2Base σ dt on e := fun h => hnm (hbareSub s h hsb)
    have hkey : σ.checkFnR T s dt on R e = σ.checkFnR T (starSubj s.shape) dt on R e :=
      checkFnR_eq_star_of_not_base hco hcl hsn hon hnb
    have hbs : σ.checkFnR T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
      hbridge s (fun h => absurd h hsn)
    have hshapeB : (starSubj s.shape).name = STAR → (starSubj s.shape).predicate = BARE :=
      fun _ => hsb
    have hbstar : σ.checkFnR T (starSubj s.shape) dt on R e
        = sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ := hbridge (starSubj s.shape) hshapeB
    have hchkStar : σ.checkFnR T (starSubj s.shape) dt on R e = true := by
      rw [← hkey, hbs]; exact hsem
    have hstarTrue : sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true := by
      rw [← hbstar]; exact hchkStar
    exact hunc ⟨hcovDecl s.shape hchkStar, hstarTrue⟩
  · -- clause (3): covered sem-false → negCands
    have hsb : s.predicate = BARE := hWSb s.shape hcov
    by_contra hnm
    have hnb : s ∉ enum2Base σ dt on e := fun h => hnm (hbareSub s h hsb)
    have hkey : σ.checkFnR T s dt on R e = σ.checkFnR T (starSubj s.shape) dt on R e :=
      checkFnR_eq_star_of_not_base hco hcl hsn hon hnb
    have hbs : σ.checkFnR T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
      hbridge s (fun h => absurd h hsn)
    have hshapeB : (starSubj s.shape).name = STAR → (starSubj s.shape).predicate = BARE :=
      fun _ => hsb
    have hbstar : σ.checkFnR T (starSubj s.shape) dt on R e
        = sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ := hbridge (starSubj s.shape) hshapeB
    have e1 : sem S T ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ := by
      rw [← hbs, hkey, hbstar]
    have hsemF' : sem S T ⟨s, R, ⟨dt, on⟩⟩ = false := hsemF
    have hstar' : sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true := hstar
    rw [hsemF', hstar'] at e1
    exact absurd e1 (by decide)
  · -- clause (4): sem-true userset → uposCands
    refine List.mem_filter.mpr ⟨?_, by simp [hsu]⟩
    by_contra hnm
    have hnb : s ∉ enum2Base σ dt on e := fun h => hnm h
    have hkey : σ.checkFnR T s dt on R e = σ.checkFnR T (starSubj s.shape) dt on R e :=
      checkFnR_eq_star_of_not_base hco hcl hsn hon hnb
    have hbs : σ.checkFnR T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
      hbridge s (fun h => absurd h hsn)
    have hcovF : σ.checkFnR T (starSubj s.shape) dt on R e = false := by
      by_contra hc
      rw [Bool.not_eq_false] at hc
      exact hsu (hWSb s.shape (hcovDecl s.shape hc))
    have hstarT : σ.checkFnR T (starSubj s.shape) dt on R e = true := by
      rw [← hkey, hbs]; exact hsem
    rw [hstarT] at hcovF
    exact absurd hcovF (by decide)

/-! ## The routed leg context — `hbridge` and `hcovDecl` at a settled W3d-2 state

The two helpers `w3dJobCoverage_enumJob2` consumes, reconstructed at a W3d-2 state whose
derived operand keys are settled (`hops`). `hbridge` is the stratum-staged read bridge
(`checkFnR_eq_sem_settled`); `hcovDecl` is the routed no-ghost-star-coverage —
factored verbatim from `graph_correct_w3d2`'s `hsem_ws` block: a true routed star read
has a true leaf, an UNTAINTED leaf transfers through the shadow to `graphRec_star_declared`,
a DERIVED leaf is the settled operand's `stars`-row read (declared by `SettledKey`). -/

/-- **Routed no-ghost-star-coverage (`hcovDecl`).** A `checkFnR`-true star read at a
    derived key with settled derived operands means the shape is declared. Factored from
    `graph_correct_w3d2` (`CascadeStrataResettle.lean:1458-1485`). -/
theorem checkFnR_star_declared {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hTT : TtuTuplesetsDirect S) (hSV : StoreValidRules S T) (hTS : TtuStarFree S T)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (hschema : σ.schema = S) {dt on R : String} {e : Expr}
    (hco : ComputedOnly e) (hqo : on ≠ STAR)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') → (u, objNode ⟨dt, on⟩ r') ∈ σ.edges))
    {sh : Shape} (hchk : σ.checkFnR T (starSubj sh) dt on R e = true) :
    sh ∈ wildcardShapes S := by
  unfold GraphState.checkFnR at hchk
  obtain ⟨r', hr', hleaf⟩ := evalE_computedOnly_true_leaf e hco hchk
  unfold GraphModel.graphRecR at hleaf
  cases hd' : isDerived S (dt, r') with
  | false =>
    rw [GraphModel.check_untainted _ _ (by rw [hschema]; exact hd')] at hleaf
    have hleaf0 : GraphModel.graphRec σ0 (starSubj sh) dt on r' = true := by
      rw [← shadow_graphRec_agree hsh (starSubj sh) on hd']
      exact hleaf
    exact graphRec_star_declared hTT hSV hTS h0 hleaf0
  | true =>
    rw [GraphModel.check_derived _ _ (by rw [hschema]; exact hd')] at hleaf
    rw [probeDerived_eq _ hqo, if_pos (show (starSubj sh).name = STAR from rfl)] at hleaf
    obtain ⟨hset', _, _⟩ := hops r' hr' hd'
    cases hrow : σ.residue (objNode ⟨dt, on⟩ r') r' with
    | none => rw [hrow, Option.getD_none] at hleaf; exact absurd hleaf Bool.false_ne_true
    | some res =>
      rw [hrow, Option.getD_some] at hleaf
      obtain ⟨hstars_iff, _, _⟩ := hset'.1 res hrow
      exact ((hstars_iff sh).mp hleaf).1

/-- **Routed no-ghost-star-coverage, Direct-arm-widened (`checkFnR_star_declared_d`).** The
    `StoreValidRulesD` + `ComputedOrDirect`/`DirectArmsBare` analog of `checkFnR_star_declared`.
    A true routed star read of shape `sh` at a Direct-arm derived def certifies `sh` declared:
    a true COMPUTED leaf rides the shadow (`graphRec_star_declared_d`, untainted) or the settled
    `stars` row (derived); a true `Direct` arm rides `directArm_star_declared` (a stored bare-STAR
    grant of shape `sh` is a wildcard-flagged restriction of the def). -/
theorem checkFnR_star_declared_d {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hTT : TtuTuplesetsDirect S) (hSV : StoreValidRulesD S T) (hTS : TtuStarFree S T)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (hschema : σ.schema = S) {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hqo : on ≠ STAR)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') → (u, objNode ⟨dt, on⟩ r') ∈ σ.edges))
    {sh : Shape} (hchk : σ.checkFnR T (starSubj sh) dt on R e = true) :
    sh ∈ wildcardShapes S := by
  unfold GraphState.checkFnR at hchk
  rcases evalE_computedOrDirect_true_leaf e hcd hchk with ⟨r', hr', hleaf⟩ | ⟨rs, hrs, hdl⟩
  · unfold GraphModel.graphRecR at hleaf
    cases hd' : isDerived S (dt, r') with
    | false =>
      rw [GraphModel.check_untainted _ _ (by rw [hschema]; exact hd')] at hleaf
      have hleaf0 : GraphModel.graphRec σ0 (starSubj sh) dt on r' = true := by
        rw [← shadow_graphRec_agree hsh (starSubj sh) on hd']
        exact hleaf
      exact graphRec_star_declared_d hTT hSV hTS h0 hleaf0
    | true =>
      rw [GraphModel.check_derived _ _ (by rw [hschema]; exact hd')] at hleaf
      rw [probeDerived_eq _ hqo, if_pos (show (starSubj sh).name = STAR from rfl)] at hleaf
      obtain ⟨hset', _, _⟩ := hops r' hr' hd'
      cases hrow : σ.residue (objNode ⟨dt, on⟩ r') r' with
      | none => rw [hrow, Option.getD_none] at hleaf; exact absurd hleaf Bool.false_ne_true
      | some res =>
        rw [hrow, Option.getD_some] at hleaf
        obtain ⟨hstars_iff, _, _⟩ := hset'.1 res hrow
        exact ((hstars_iff sh).mp hleaf).1
  · exact directArm_star_declared hlk hba hrs hdl

/-- **Routed no-ghost-star-coverage over the FILTERED shadow
    (`checkFnR_star_declared_d_filt`).** `checkFnR_star_declared_d` with the base witness
    σ0 admitted over `T↾U` — the pair the filtered shadow (`reachedByW3d2_shadow_d`)
    produces. Only the untainted COMPUTED branch touches σ0: `graphRec_star_declared_d`
    instantiates at `T↾U` (its `hSV`/`h0` stores are coupled; the conclusion is
    store-free). The derived branch reads the settled `stars` row and the `Direct` arm
    reads the FULL store — both unchanged. -/
theorem checkFnR_star_declared_d_filt {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hTT : TtuTuplesetsDirect S) (hSV : StoreValidRulesD S T) (hTS : TtuStarFree S T)
    (h0 : ReachedByRulesAdmitted σ0 S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh : UntaintedShadow S σ σ0)
    (hschema : σ.schema = S) {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hqo : on ≠ STAR)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') → (u, objNode ⟨dt, on⟩ r') ∈ σ.edges))
    {sh : Shape} (hchk : σ.checkFnR T (starSubj sh) dt on R e = true) :
    sh ∈ wildcardShapes S := by
  have hSVU : StoreValidRules S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    storeValidRules_untaintedFilter hSV
  have hStoreUntU : ∀ t ∈ T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)),
      isDerived S (t.object.type, t.relation) = false := by
    intro t ht
    simpa using (List.mem_filter.mp ht).2
  have hSVU_D : StoreValidRulesD S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    fun t ht => Or.inl ⟨hStoreUntU t ht, hSVU t ht⟩
  have hTSU : TtuStarFree S (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))) :=
    fun t ht => hTS t (List.mem_filter.mp ht).1
  unfold GraphState.checkFnR at hchk
  rcases evalE_computedOrDirect_true_leaf e hcd hchk with ⟨r', hr', hleaf⟩ | ⟨rs, hrs, hdl⟩
  · unfold GraphModel.graphRecR at hleaf
    cases hd' : isDerived S (dt, r') with
    | false =>
      rw [GraphModel.check_untainted _ _ (by rw [hschema]; exact hd')] at hleaf
      have hleaf0 : GraphModel.graphRec σ0 (starSubj sh) dt on r' = true := by
        rw [← shadow_graphRec_agree hsh (starSubj sh) on hd']
        exact hleaf
      exact graphRec_star_declared_d hTT hSVU_D hTSU h0 hleaf0
    | true =>
      rw [GraphModel.check_derived _ _ (by rw [hschema]; exact hd')] at hleaf
      rw [probeDerived_eq _ hqo, if_pos (show (starSubj sh).name = STAR from rfl)] at hleaf
      obtain ⟨hset', _, _⟩ := hops r' hr' hd'
      cases hrow : σ.residue (objNode ⟨dt, on⟩ r') r' with
      | none => rw [hrow, Option.getD_none] at hleaf; exact absurd hleaf Bool.false_ne_true
      | some res =>
        rw [hrow, Option.getD_some] at hleaf
        obtain ⟨hstars_iff, _, _⟩ := hset'.1 res hrow
        exact ((hstars_iff sh).mp hleaf).1
  · exact directArm_star_declared hlk hba hrs hdl

/-- **The routed leg context** — both helpers `w3dJobCoverage_enumJob2` consumes, at a
    shadowed W3d-2 state with settled derived operand keys. `hbridge` is
    `checkFnR_eq_sem_settled`, `hcovDecl` is `checkFnR_star_declared`. -/
theorem w3d2_leg_context {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (hschema : σ.schema = S) {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e) (hqo : on ≠ STAR)
    (hLU2 : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') → (u, objNode ⟨dt, on⟩ r') ∈ σ.edges)) :
    (∀ s' : SubjectRef, (s'.name = STAR → s'.predicate = BARE) →
      σ.checkFnR T s' dt on R e = sem S T ⟨s', R, ⟨dt, on⟩⟩) ∧
    (∀ sh : Shape, σ.checkFnR T (starSubj sh) dt on R e = true → sh ∈ wildcardShapes S) :=
  ⟨fun s' hs' => checkFnR_eq_sem_settled hWF hTT hNK hR hSV hBS hTS hMatch hStrat
      hterm hCO hWSbare h0 hsh hschema hlk hder hco hLU2 hops hs' hqo,
   fun _ hchk => checkFnR_star_declared hTT hSV hTS h0 hsh hschema hco hqo hops hchk⟩

/-! ## `W3dJobCoverage` for `enumJob2` at a W3d-2 state

The state-level combining lemma: over any `ReachedByW3d2` state, given only that the
derived operand keys are settled+complete (`hsettledOps` — the single remaining
obligation the closure assembly discharges per round: vacuous at stratum-1/round-1
keys, from round-1 re-settlement at stratum-2/round-2 keys), `enumJob2`'s coverage
holds. The shadow (`reachedByW3d2_shadow`), edges-closedness
(`reachedByW3d2_edgesClosed`), the schema anchor, and the per-operand reach collapse
(`reachedByW3d2_reach_collapse_root`) are all read off the state. -/
theorem w3dJobCoverage_enumJob2_state {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2 σ S T) {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e) (hqo : on ≠ STAR)
    (hLU2 : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hsettledOps : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r') :
    W3dJobCoverage S T σ (enumJob2 σ dt on R e) := by
  have hcl := reachedByW3d2_edgesClosed h
  obtain ⟨σ0, h0, hsh⟩ := reachedByW3d2_shadow h hNK hCO hSV hterm
  have hschema : σ.schema = S := reachedByW3d2_schema h
  have hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') → (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) := by
    intro r' hr' hd'
    obtain ⟨e', hlk'⟩ := isDerived_declared hd'
    have hco' : ComputedOnly e' := hCO dt r' e' hlk' hd'
    obtain ⟨hset', hcomp'⟩ := hsettledOps r' hr' hd'
    exact ⟨hset', hcomp',
      fun u hu => reachedByW3d2_reach_collapse_root hWF hSV hlk' hd' hco' h hu⟩
  obtain ⟨hbridge, hcovDecl⟩ := w3d2_leg_context hWF hTT hNK hR hSV hBS hTS hMatch
    hStrat hterm hCO hWSbare h0 hsh hschema hlk hder hco hqo hLU2 hops
  exact w3dJobCoverage_enumJob2 hco hcl hqo hbridge hcovDecl hWSbare

/-! ## The Direct-arm-widened enumerated job (`enumJob2D`) and its coverage — leg 5 sub-step 2

`enum2Base` (leaf concretes ∪ residue-named) MISSES the subjects that read a `Direct` arm
differently from their shape-star — exactly the `NoConcDirect`-FAILING subjects, i.e. the
subjects of the stored BARE Direct-arm grants (`grantsOf T rs dt on R` over `exprDirectsAll e`).
Those live in the FIXED store `T`, NOT in any mutating operand residue, so — unlike the 12h
kill (a fresh grant appearing only in a dirty operand's future residue) — a stored Direct-arm
tuple is enumerable at EVERY state directly from `T`. `enum2BaseD` adds them; the coverage
discharge `w3dJobCoverage_enumJob2D` then contraposes `checkFnR_eq_star_of_not_baseD` (a subject
off the widened base reads as its star) for the `NoConcDirect` subjects and covers the
concrete-grant subjects directly. -/

/-- The userset (`predicate ≠ BARE`) analog of `directLeaf_star_of_noConc`: on a BARE arm, a
    userset subject and its (userset) shape-star BOTH read the arm as `false` — bare grants
    never match a userset subject or a userset star. NO `NoConcDirect` gate needed. -/
theorem directLeaf_star_userset_bare {rec1 rec2 : Rec} {T : Store} {q1 q2 : Query}
    {s : SubjectRef} {rs : List Restriction} {ot on rel : String}
    (hb : ∀ r ∈ rs, r.2.1 = BARE) (hsn : s.name ≠ STAR) (hsp : s.predicate ≠ BARE) :
    directLeaf rec1 s T q1 rs ot on rel
      = directLeaf rec2 (starSubj s.shape) T q2 rs ot on rel := by
  have hbareG : ∀ g ∈ grantsOf T rs ot on rel, g.subject.predicate = BARE :=
    grantsOf_bare_subjects T rs ot on rel hb
  have hmog : ∀ (rec : Rec) (q : Query),
      memberOfGranted rec T q (grantsOf T rs ot on rel) = false :=
    fun rec q => memberOfGranted_of_bareGrants rec T q _ hbareG
  have hlhs : directLeaf rec1 s T q1 rs ot on rel = false := by
    unfold directLeaf
    have hsnL : (s.name == STAR) = false := beq_eq_false_iff_ne.mpr hsn
    have hspL : (s.predicate == BARE) = false := beq_eq_false_iff_ne.mpr hsp
    simp only [hsnL, hspL, hmog, Bool.or_false]
    rw [if_neg Bool.false_ne_true, if_neg Bool.false_ne_true, List.any_eq_false]
    intro g hg
    have hgb : g.subject.predicate = BARE := hbareG g hg
    rw [Bool.not_eq_true]
    simp only [hgb, bne_self_eq_false, Bool.and_false, Bool.false_and, Bool.or_false]
  have hrhs : directLeaf rec2 (starSubj s.shape) T q2 rs ot on rel = false := by
    unfold directLeaf
    have hstarN : ((starSubj s.shape).name == STAR) = true := by show (STAR == STAR) = true; simp
    simp only [hstarN, if_true, hmog, Bool.or_false]
    rw [List.any_eq_false]
    intro g hg
    have hgb : g.subject.predicate = BARE := hbareG g hg
    have hpne : (g.subject.predicate == (starSubj s.shape).predicate) = false := by
      rw [hgb]; exact beq_eq_false_iff_ne.mpr (fun h => hsp h.symm)
    rw [Bool.not_eq_true]
    simp only [starSubj, SubjectRef.shape] at hpne ⊢
    simp only [hpne, Bool.and_false]
  rw [hlhs, hrhs]

/-- **The star transport over a `ComputedOrDirect`/`DirectArmsBare` tree, both subject kinds.**
    A star-free subject `s` reads `e` exactly as its shape-star, given operand agreement on the
    `computed` leaves and — ONLY in the bare-subject case — `NoConcDirect` (conditional on
    `s.predicate = BARE`). Bare `Direct` arms ride `directLeaf_star_of_noConc` (bare) or
    `directLeaf_star_userset_bare` (userset); generic in `rec1`/`rec2` (serves routed + unrouted).-/
theorem evalE_star_bareArms {rec1 rec2 : Rec} {T : Store} {q1 q2 : Query} {s : SubjectRef}
    {dt on rel : String} (hsn : s.name ≠ STAR) :
    ∀ e : Expr, ComputedOrDirect e → DirectArmsBare e →
      (s.predicate = BARE → NoConcDirect T s dt on rel e) →
      (∀ r' ∈ computedRefs e, rec1 dt on r' = rec2 dt on r') →
      evalE rec1 s T q1 dt on rel e = evalE rec2 (starSubj s.shape) T q2 dt on rel e := by
  intro e
  induction e with
  | computed r' => intro _ _ _ hag; simp only [evalE]; exact hag r' (List.mem_singleton.mpr rfl)
  | direct rs =>
    intro _ hb hnc _; simp only [evalE]
    by_cases hsp : s.predicate = BARE
    · exact directLeaf_star_of_noConc hb hsn hsp (hnc hsp)
    · exact directLeaf_star_userset_bare hb hsn hsp
  | union a b iha ihb =>
    intro hcd hba hnc hag; simp only [evalE]
    rw [iha hcd.1 hba.1 (fun hp => (hnc hp).1) (fun r' hr' => hag r' (List.mem_append_left _ hr')),
        ihb hcd.2 hba.2 (fun hp => (hnc hp).2) (fun r' hr' => hag r' (List.mem_append_right _ hr'))]
  | inter a b iha ihb =>
    intro hcd hba hnc hag; simp only [evalE]
    rw [iha hcd.1 hba.1 (fun hp => (hnc hp).1) (fun r' hr' => hag r' (List.mem_append_left _ hr')),
        ihb hcd.2 hba.2 (fun hp => (hnc hp).2) (fun r' hr' => hag r' (List.mem_append_right _ hr'))]
  | excl a b iha ihb =>
    intro hcd hba hnc hag; simp only [evalE]
    rw [iha hcd.1 hba.1 (fun hp => (hnc hp).1) (fun r' hr' => hag r' (List.mem_append_left _ hr')),
        ihb hcd.2 hba.2 (fun hp => (hnc hp).2) (fun r' hr' => hag r' (List.mem_append_right _ hr'))]
  | ttu tr ts => intro hcd _ _ _; exact hcd.elim

/-- The stored BARE Direct-arm subjects at key `(dt,R)` object `on`: the subjects of the grants
    of every `Direct` arm reachable via `exprDirectsAll e`, read from the FIXED store `T`. These
    are exactly the `NoConcDirect`-failing candidates the coverage enumeration must add. -/
def storedDirectSubjects (T : Store) (dt on R : String) (e : Expr) : List SubjectRef :=
  (exprDirectsAll e).flatMap (fun rs => (grantsOf T rs dt on R).map (·.subject))

/-- A subject NOT among the stored Direct-arm subjects (and `s.predicate = BARE`) has
    `NoConcDirect`: a concrete grant would put `s` (= the grant's own subject) in the set. -/
theorem noConcDirect_of_not_mem {T : Store} {dt on R : String} {s : SubjectRef}
    (hsp : s.predicate = BARE) :
    ∀ e : Expr, s ∉ storedDirectSubjects T dt on R e → NoConcDirect T s dt on R e := by
  intro e
  induction e with
  | computed _ => intro _; trivial
  | ttu _ _ => intro _; trivial
  | direct rs =>
    intro hns
    show (grantsOf T rs dt on R).any (concMatch s) = false
    rw [List.any_eq_false]
    intro g hg hcm
    apply hns
    simp only [concMatch, Bool.and_eq_true, bne_iff_ne, beq_iff_eq] at hcm
    obtain ⟨⟨⟨_, hgp⟩, hgt⟩, hgn⟩ := hcm
    have hseq : g.subject = s := by
      obtain ⟨st, sn, sp⟩ := s
      simp only at hgt hgn hsp
      show g.subject = ⟨st, sn, sp⟩
      have hη : g.subject = ⟨g.subject.type, g.subject.name, g.subject.predicate⟩ := rfl
      rw [hη, hgt, hgn, hgp, hsp]
    show s ∈ storedDirectSubjects T dt on R (.direct rs)
    unfold storedDirectSubjects
    simp only [exprDirectsAll, List.flatMap_cons, List.flatMap_nil, List.append_nil]
    exact hseq ▸ List.mem_map.mpr ⟨g, hg, rfl⟩
  | union a b iha ihb =>
    intro hns
    have hsplit : storedDirectSubjects T dt on R (.union a b)
        = storedDirectSubjects T dt on R a ++ storedDirectSubjects T dt on R b := by
      unfold storedDirectSubjects; simp only [exprDirectsAll, List.flatMap_append]
    rw [hsplit] at hns
    exact ⟨iha (fun h => hns (List.mem_append_left _ h)),
           ihb (fun h => hns (List.mem_append_right _ h))⟩
  | inter a b iha ihb =>
    intro hns
    have hsplit : storedDirectSubjects T dt on R (.inter a b)
        = storedDirectSubjects T dt on R a ++ storedDirectSubjects T dt on R b := by
      unfold storedDirectSubjects; simp only [exprDirectsAll, List.flatMap_append]
    rw [hsplit] at hns
    exact ⟨iha (fun h => hns (List.mem_append_left _ h)),
           ihb (fun h => hns (List.mem_append_right _ h))⟩
  | excl a b iha ihb =>
    intro hns
    have hsplit : storedDirectSubjects T dt on R (.excl a b)
        = storedDirectSubjects T dt on R a ++ storedDirectSubjects T dt on R b := by
      unfold storedDirectSubjects; simp only [exprDirectsAll, List.flatMap_append]
    rw [hsplit] at hns
    exact ⟨iha (fun h => hns (List.mem_append_left _ h)),
           ihb (fun h => hns (List.mem_append_right _ h))⟩

/-- The Direct-arm-widened per-key base list: `enum2Base` ∪ the stored Direct-arm subjects. -/
def enum2BaseD (σ : GraphState) (T : Store) (dt on R : String) (e : Expr) : List SubjectRef :=
  enum2Base σ dt on e ++ storedDirectSubjects T dt on R e

/-- The Direct-arm-widened state-derived W3d-2 enumerated job for one derived key `(dt,R)`. -/
def enumJob2D (σ : GraphState) (T : Store) (dt on R : String) (e : Expr) : W3cJob :=
  { dt := dt, on := on, R := R, e := e,
    cands := (enum2BaseD σ T dt on R e).filter (fun u => u.predicate == BARE)
             ++ edgeHolders σ dt on R,
    negCands := (enum2BaseD σ T dt on R e).filter (fun u => u.predicate == BARE),
    uposCands := (enum2BaseD σ T dt on R e).filter (fun u => u.predicate != BARE) }

/-- Off the widened base list, `checkFnR` reads a star-free subject as its shape-star. `∉
    enum2BaseD` splits into `∉ enum2Base` (leaf concretes + residue-named, via
    `graphRecR_leaf_agree`) and `∉ storedDirectSubjects` (⇒ `NoConcDirect`, for the Direct
    arm), transported by `evalE_star_bareArms` over BOTH subject kinds. -/
theorem checkFnR_eq_star_of_not_baseD {σ : GraphState} {T : Store} {s : SubjectRef}
    {dt on R : String} {e : Expr} (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hcl : ∀ ed ∈ σ.edges, ed.1 ∈ σ.nodes ∧ ed.2 ∈ σ.nodes)
    (hsn : s.name ≠ STAR) (hon : on ≠ STAR) (hnb : s ∉ enum2BaseD σ T dt on R e) :
    σ.checkFnR T s dt on R e = σ.checkFnR T (starSubj s.shape) dt on R e := by
  have hnbBase : s ∉ enum2Base σ dt on e := fun h => hnb (List.mem_append_left _ h)
  have hnbSD : s ∉ storedDirectSubjects T dt on R e := fun h => hnb (List.mem_append_right _ h)
  unfold GraphState.checkFnR
  refine evalE_star_bareArms hsn e hcd hba (fun hp => noConcDirect_of_not_mem hp e hnbSD) ?_
  intro r' hr'
  exact graphRecR_leaf_agree hcl hsn hon hr'
    (fun h => hnbBase (List.mem_append_left _ h))
    (fun _ h => hnbBase (List.mem_append_right _ (List.mem_flatMap.mpr ⟨r', hr', h⟩)))

/-- **`W3dJobCoverage` for `enumJob2D` from the ROUTED leg context (Direct-arm-widened).** Same
    contrapositive skeleton as `w3dJobCoverage_enumJob2`, with `enum2BaseD` (adding the stored
    Direct-arm subjects) as the base and `checkFnR_eq_star_of_not_baseD` in place of
    `checkFnR_eq_star_of_not_base`. -/
theorem w3dJobCoverage_enumJob2D {S : Schema} {T : Store} {σ : GraphState}
    {dt on R : String} {e : Expr} (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hcl : ∀ ed ∈ σ.edges, ed.1 ∈ σ.nodes ∧ ed.2 ∈ σ.nodes) (hon : on ≠ STAR)
    (hbridge : ∀ s' : SubjectRef, (s'.name = STAR → s'.predicate = BARE) →
      σ.checkFnR T s' dt on R e = sem S T ⟨s', R, ⟨dt, on⟩⟩)
    (hcovDecl : ∀ sh : Shape, σ.checkFnR T (starSubj sh) dt on R e = true →
      sh ∈ wildcardShapes S)
    (hWSb : ∀ sh ∈ wildcardShapes S, sh.2 = BARE) :
    W3dJobCoverage S T σ (enumJob2D σ T dt on R e) := by
  have hbareSub : ∀ u ∈ enum2BaseD σ T dt on R e, u.predicate = BARE →
      u ∈ (enum2BaseD σ T dt on R e).filter (fun u => u.predicate == BARE) :=
    fun u hu hub => List.mem_filter.mpr ⟨hu, by simp [hub]⟩
  refine ⟨fun s hs => ?_, fun s hsb hsn hsem hunc => ?_,
    fun s hsn hcov hstar hsemF => ?_, fun s hsu hsn hsem => ?_⟩
  · exact List.mem_append_right _ (mem_edgeHolders hs)
  · refine List.mem_append_left _ ?_
    by_contra hnm
    have hnb : s ∉ enum2BaseD σ T dt on R e := fun h => hnm (hbareSub s h hsb)
    have hkey : σ.checkFnR T s dt on R e = σ.checkFnR T (starSubj s.shape) dt on R e :=
      checkFnR_eq_star_of_not_baseD hcd hba hcl hsn hon hnb
    have hbs : σ.checkFnR T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
      hbridge s (fun h => absurd h hsn)
    have hbstar : σ.checkFnR T (starSubj s.shape) dt on R e
        = sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ := hbridge (starSubj s.shape) (fun _ => hsb)
    have hchkStar : σ.checkFnR T (starSubj s.shape) dt on R e = true := by
      rw [← hkey, hbs]; exact hsem
    have hstarTrue : sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true := by
      rw [← hbstar]; exact hchkStar
    exact hunc ⟨hcovDecl s.shape hchkStar, hstarTrue⟩
  · have hsb : s.predicate = BARE := hWSb s.shape hcov
    by_contra hnm
    have hnb : s ∉ enum2BaseD σ T dt on R e := fun h => hnm (hbareSub s h hsb)
    have hkey : σ.checkFnR T s dt on R e = σ.checkFnR T (starSubj s.shape) dt on R e :=
      checkFnR_eq_star_of_not_baseD hcd hba hcl hsn hon hnb
    have hbs : σ.checkFnR T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
      hbridge s (fun h => absurd h hsn)
    have hbstar : σ.checkFnR T (starSubj s.shape) dt on R e
        = sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ := hbridge (starSubj s.shape) (fun _ => hsb)
    have e1 : sem S T ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ := by
      rw [← hbs, hkey, hbstar]
    have hsemF' : sem S T ⟨s, R, ⟨dt, on⟩⟩ = false := hsemF
    have hstar' : sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true := hstar
    rw [hsemF', hstar'] at e1
    exact absurd e1 (by decide)
  · refine List.mem_filter.mpr ⟨?_, by simp [hsu]⟩
    by_contra hnm
    have hnb : s ∉ enum2BaseD σ T dt on R e := fun h => hnm h
    have hkey : σ.checkFnR T s dt on R e = σ.checkFnR T (starSubj s.shape) dt on R e :=
      checkFnR_eq_star_of_not_baseD hcd hba hcl hsn hon hnb
    have hbs : σ.checkFnR T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
      hbridge s (fun h => absurd h hsn)
    have hcovF : σ.checkFnR T (starSubj s.shape) dt on R e = false := by
      by_contra hc
      rw [Bool.not_eq_false] at hc
      exact hsu (hWSb s.shape (hcovDecl s.shape hc))
    have hstarT : σ.checkFnR T (starSubj s.shape) dt on R e = true := by
      rw [← hkey, hbs]; exact hsem
    rw [hstarT] at hcovF
    exact absurd hcovF (by decide)

/-- **The routed leg context, Direct-arm-widened (`w3d2_leg_context_d`)** — both helpers
    `w3dJobCoverage_enumJob2D` consumes, at a shadowed W3d-2 state with settled derived operand
    keys. `hbridge` is `checkFnR_eq_sem_settled_d`, `hcovDecl` is `checkFnR_star_declared_d`. -/
theorem w3d2_leg_context_d {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRulesD S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (hschema : σ.schema = S) {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e) (hqo : on ≠ STAR)
    (hLU2 : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') → (u, objNode ⟨dt, on⟩ r') ∈ σ.edges)) :
    (∀ s' : SubjectRef, (s'.name = STAR → s'.predicate = BARE) →
      σ.checkFnR T s' dt on R e = sem S T ⟨s', R, ⟨dt, on⟩⟩) ∧
    (∀ sh : Shape, σ.checkFnR T (starSubj sh) dt on R e = true → sh ∈ wildcardShapes S) :=
  ⟨fun s' hs' => checkFnR_eq_sem_settled_d hWF hTT hNK hR hSV hBS hTS hMatch hStrat
      hterm hCO hWSbare h0 hsh hschema hlk hder hcd hba hLU2 hops hs' hqo,
   fun _ hchk => checkFnR_star_declared_d hTT hSV hTS h0 hsh hschema hlk hcd hba hqo hops hchk⟩

/-- **The routed leg context over the FILTERED shadow (`w3d2_leg_context_d_filt`)** —
    `w3d2_leg_context_d` with the base witness σ0 admitted over `T↾U`, the pair the
    filtered shadow (`reachedByW3d2_shadow_d`) actually produces (the full-store pair is
    jointly unsatisfiable on the Direct-arm fragment). Same conclusions over the FULL
    store: `hbridge` is `checkFnR_eq_sem_settled_d_filt`, `hcovDecl` is
    `checkFnR_star_declared_d_filt`. -/
theorem w3d2_leg_context_d_filt {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRulesD S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h0 : ReachedByRulesAdmitted σ0 S
      (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))))
    (hsh : UntaintedShadow S σ σ0)
    (hschema : σ.schema = S) {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e) (hqo : on ≠ STAR)
    (hLU2 : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hops : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
      (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') → (u, objNode ⟨dt, on⟩ r') ∈ σ.edges)) :
    (∀ s' : SubjectRef, (s'.name = STAR → s'.predicate = BARE) →
      σ.checkFnR T s' dt on R e = sem S T ⟨s', R, ⟨dt, on⟩⟩) ∧
    (∀ sh : Shape, σ.checkFnR T (starSubj sh) dt on R e = true → sh ∈ wildcardShapes S) :=
  ⟨fun s' hs' => checkFnR_eq_sem_settled_d_filt hWF hTT hNK hR hSV hBS hTS hMatch hStrat
      hterm hCO hWSbare h0 hsh hschema hlk hder hcd hba hLU2 hops hs' hqo,
   fun _ hchk => checkFnR_star_declared_d_filt hTT hSV hTS h0 hsh hschema hlk hcd hba hqo
      hops hchk⟩

end Zanzibar
