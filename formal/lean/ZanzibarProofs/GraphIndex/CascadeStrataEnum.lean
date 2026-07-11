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

/-- **The routed leg context** — both helpers `w3dJobCoverage_enumJob2` consumes, at a
    shadowed W3d-2 state with settled derived operand keys. `hbridge` is
    `checkFnR_eq_sem_settled`, `hcovDecl` is `checkFnR_star_declared`. -/
theorem w3d2_leg_context {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
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
  ⟨fun s' hs' => checkFnR_eq_sem_settled hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat
      hterm hCO hWSbare h0 hsh hschema hlk hder hco hLU2 hops hs' hqo,
   fun _ hchk => checkFnR_star_declared hTT hSV hTS h0 hsh hschema hco hqo hops hchk⟩

end Zanzibar
