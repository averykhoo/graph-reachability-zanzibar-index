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
    for EVERY subject: `subjNode` only ever rewrites the variant, so dropping it recovers
    the subject (a `'*'` subject already IS its own `wAny` node's decode). -/
def nodeSubj (u : NodeKey) : SubjectRef := ⟨u.type, u.name, u.pred⟩

@[simp] theorem nodeSubj_subjNode (s : SubjectRef) : nodeSubj (subjNode s) = s := by
  unfold nodeSubj subjNode
  split
  · rename_i h; rw [← h]
  · rfl

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
  refine ⟨subjNode s, ?_, nodeSubj_subjNode s⟩
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

/-! ## Discharging the `W3dJobCoverage` completeness clauses

Each clause is a contrapositive of the leg-state bridge `checkFn = sem`
(`checkFn_eq_sem_w3d`, supplied here as `hbridge`) fed through
`checkFn_eq_coveredFn_of_not_mem`: a subject NOT in the enumerated candidate list is
not among the leaf concretes, so it reads exactly as its shape-star — but the
hypotheses force its `sem` and its star's `sem` apart, a contradiction. The
"`sem`-covered ⇒ declared" helper (`hdeclB`, the `coveredFn_declared` linchpin lifted
to the leg, cf. `graph_correct_w3d`'s `hsem_ws`) discharges clause (2). -/

/-- **Clause (2) discharge** — the uncovered `sem`-true bare candidate is enumerated.
    An uncovered (`hunc`) bare star-free subject that is `sem`-true but NOT in `cands`
    would not be among the leaf concretes, so `checkFn s = checkFn (starSubj s.shape)`;
    both bridge to `sem`, giving `sem s = sem (starSubj s.shape)`, so the star is
    `sem`-true — and `sem`-covered-of-a-bare-shape is declared (`hdeclB`), contradicting
    `hunc`. -/
theorem cands_complete_uncovered {S : Schema} {T : Store} {σ : GraphState}
    {dt on R : String} {e : Expr} (hco : ComputedOnly e)
    (hcl : ∀ ed ∈ σ.edges, ed.1 ∈ σ.nodes ∧ ed.2 ∈ σ.nodes) (hon : on ≠ STAR)
    (hbridge : ∀ s' : SubjectRef, (s'.name = STAR → s'.predicate = BARE) →
      σ.checkFn T s' dt on R e = sem S T ⟨s', R, ⟨dt, on⟩⟩)
    (hcovDecl : ∀ sh : Shape, σ.checkFn T (starSubj sh) dt on R e = true →
      sh ∈ wildcardShapes S)
    {cands : List SubjectRef}
    (hsub : ∀ u ∈ leafConcretes σ dt on e, u.predicate = BARE → u ∈ cands)
    {s : SubjectRef} (hsb : s.predicate = BARE) (hsn : s.name ≠ STAR)
    (hsem : sem S T ⟨s, R, ⟨dt, on⟩⟩ = true)
    (hunc : ¬(s.shape ∈ wildcardShapes S ∧
      sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true)) :
    s ∈ cands := by
  by_contra hnm
  have hnl : s ∉ leafConcretes σ dt on e := fun h => hnm (hsub s h hsb)
  have hkey : σ.checkFn T s dt on R e = σ.checkFn T (starSubj s.shape) dt on R e := by
    rw [checkFn_eq_coveredFn_of_not_mem hco hcl hsn hon hnl]; rfl
  have hbs : σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
    hbridge s (fun h => absurd h hsn)
  have hshapeB : (starSubj s.shape).name = STAR → (starSubj s.shape).predicate = BARE :=
    fun _ => hsb
  have hbstar : σ.checkFn T (starSubj s.shape) dt on R e
      = sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ := hbridge (starSubj s.shape) hshapeB
  have hchkStar : σ.checkFn T (starSubj s.shape) dt on R e = true := by
    rw [← hkey, hbs, hsem]
  have hstarTrue : sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true := by
    rw [← hbstar]; exact hchkStar
  exact hunc ⟨hcovDecl s.shape hchkStar, hstarTrue⟩

/-- **Clause (3) discharge** — the covered `sem`-false candidate is in `negCands`.
    A star-free subject whose shape is covered (∈ `wildcardShapes`, hence bare under
    `hWSb`) with the star `sem`-true but the subject `sem`-false: were it NOT enumerated
    it would read as its star (`checkFn s = checkFn (starSubj s.shape)`), bridging to
    `sem s = false` vs `sem (starSubj) = true`, a contradiction. -/
theorem negCands_complete {S : Schema} {T : Store} {σ : GraphState}
    {dt on R : String} {e : Expr} (hco : ComputedOnly e)
    (hcl : ∀ ed ∈ σ.edges, ed.1 ∈ σ.nodes ∧ ed.2 ∈ σ.nodes) (hon : on ≠ STAR)
    (hbridge : ∀ s' : SubjectRef, (s'.name = STAR → s'.predicate = BARE) →
      σ.checkFn T s' dt on R e = sem S T ⟨s', R, ⟨dt, on⟩⟩)
    (hWSb : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {negCands : List SubjectRef}
    (hsub : ∀ u ∈ leafConcretes σ dt on e, u.predicate = BARE → u ∈ negCands)
    {s : SubjectRef} (hsn : s.name ≠ STAR) (hcov : s.shape ∈ wildcardShapes S)
    (hstar : sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true)
    (hsemF : sem S T ⟨s, R, ⟨dt, on⟩⟩ = false) :
    s ∈ negCands := by
  have hsb : s.predicate = BARE := hWSb s.shape hcov
  by_contra hnm
  have hnl : s ∉ leafConcretes σ dt on e := fun h => hnm (hsub s h hsb)
  have hkey : σ.checkFn T s dt on R e = σ.checkFn T (starSubj s.shape) dt on R e := by
    rw [checkFn_eq_coveredFn_of_not_mem hco hcl hsn hon hnl]; rfl
  have hbs : σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
    hbridge s (fun h => absurd h hsn)
  have hshapeB : (starSubj s.shape).name = STAR → (starSubj s.shape).predicate = BARE :=
    fun _ => hsb
  have hbstar : σ.checkFn T (starSubj s.shape) dt on R e
      = sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ := hbridge (starSubj s.shape) hshapeB
  rw [hbs, hbstar, hsemF, hstar] at hkey
  exact absurd hkey (by decide)

/-- **Clause (4) discharge** — the `sem`-true userset candidate is in `uposCands`.
    A userset (`hsu`) star-free subject that is `sem`-true but NOT enumerated would read
    as its shape-star; the subject bridges to `sem = true`, but the star's shape is
    userset, hence undeclared (all wildcard shapes are bare, `hWSb`), so its coverage is
    `false` by the contrapositive of `hcovDecl` — a contradiction. -/
theorem uposCands_complete {S : Schema} {T : Store} {σ : GraphState}
    {dt on R : String} {e : Expr} (hco : ComputedOnly e)
    (hcl : ∀ ed ∈ σ.edges, ed.1 ∈ σ.nodes ∧ ed.2 ∈ σ.nodes) (hon : on ≠ STAR)
    (hbridge : ∀ s' : SubjectRef, (s'.name = STAR → s'.predicate = BARE) →
      σ.checkFn T s' dt on R e = sem S T ⟨s', R, ⟨dt, on⟩⟩)
    (hcovDecl : ∀ sh : Shape, σ.checkFn T (starSubj sh) dt on R e = true →
      sh ∈ wildcardShapes S)
    (hWSb : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {uposCands : List SubjectRef}
    (hsub : ∀ u ∈ leafConcretes σ dt on e, u.predicate ≠ BARE → u ∈ uposCands)
    {s : SubjectRef} (hsu : s.predicate ≠ BARE) (hsn : s.name ≠ STAR)
    (hsem : sem S T ⟨s, R, ⟨dt, on⟩⟩ = true) :
    s ∈ uposCands := by
  by_contra hnm
  have hnl : s ∉ leafConcretes σ dt on e := fun h => hnm (hsub s h hsu)
  have hkey : σ.checkFn T s dt on R e = σ.checkFn T (starSubj s.shape) dt on R e := by
    rw [checkFn_eq_coveredFn_of_not_mem hco hcl hsn hon hnl]; rfl
  have hbs : σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
    hbridge s (fun h => absurd h hsn)
  -- the userset star's shape is undeclared, so its coverage is false
  have hcovF : σ.checkFn T (starSubj s.shape) dt on R e = false := by
    by_contra hc
    rw [Bool.not_eq_false] at hc
    exact hsu (hWSb s.shape (hcovDecl s.shape hc))
  rw [hbs, hcovF, hsem] at hkey
  exact absurd hkey (by decide)

/-! ## The edge-holder enumeration (clause (1), by construction)

`processor.py:394-441` also re-enumerates the persisted incoming R-node concretes — the
attack-confirmed stale-holder clause. The model reads them straight off the edges: every
source of an edge into the R-node, decoded. Clause (1) is then immediate — `nodeSubj`
recovers the subject from its (variant-only-altered) source node. -/

/-- The subjects whose graph node has an edge into the derived R-node `objNode ⟨dt,on⟩ R`
    — the persisted edge holders, decoded. -/
def edgeHolders (σ : GraphState) (dt on R : String) : List SubjectRef :=
  (σ.edges.filter (fun ed => ed.2 == objNode ⟨dt, on⟩ R)).map (fun ed => nodeSubj ed.1)

/-- **Clause (1) discharge** — every pre-leg edge holder at the key is enumerated. -/
theorem mem_edgeHolders {σ : GraphState} {s : SubjectRef} {dt on R : String}
    (h : (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges) : s ∈ edgeHolders σ dt on R := by
  rw [edgeHolders, List.mem_map]
  refine ⟨(subjNode s, objNode ⟨dt, on⟩ R), ?_, nodeSubj_subjNode s⟩
  rw [List.mem_filter]
  exact ⟨h, by simp⟩

/-! ## The leg context — `hbridge` and `hcovDecl` at any W3d state

The two leg-level helpers the clause discharges consume are reconstructed at every W3d
state through the untainted-core shadow (`reachedByW3d_shadow`): `hbridge` is the W3d
read bridge (`checkFn_eq_sem_w3d`); `hcovDecl` is the `coveredFn_declared` linchpin
lifted across the shadow (`checkFn` of a star subject reads only untainted operands, so
it agrees with the rules-admitted shadow, where a `true` coverage is declared). -/

/-- **The leg context.** At any W3d state, for a declared derived key `(dt,R)` with
    untainted computed leaves and a star-free object, the read bridge (`checkFn = sem`,
    subject-generic up to star-BARE) and the coverage-declaredness helper both hold. -/
theorem w3d_leg_context {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3d σ S T) {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false) (hon : on ≠ STAR) :
    (∀ s' : SubjectRef, (s'.name = STAR → s'.predicate = BARE) →
      σ.checkFn T s' dt on R e = sem S T ⟨s', R, ⟨dt, on⟩⟩) ∧
    (∀ sh : Shape, σ.checkFn T (starSubj sh) dt on R e = true → sh ∈ wildcardShapes S) := by
  obtain ⟨σ0, h0, hsh⟩ := reachedByW3d_shadow h hNK hRootB hSV hterm
  refine ⟨fun s' hs' => ?_, fun sh hcov => ?_⟩
  · exact checkFn_eq_sem_w3d hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm h0 hsh
      hlk hco hleafUnt hs' hon
  · have hagree : σ.checkFn T (starSubj sh) dt on R e = σ0.checkFn T (starSubj sh) dt on R e :=
      checkFn_agree_of_graphRec T (starSubj sh) dt on R e hco hleafUnt
        (fun s' r' hr' => shadow_graphRec_agree hsh s' on hr')
    have hcov0 : σ0.coveredFn T dt on R e sh = true := by
      show σ0.checkFn T (starSubj sh) dt on R e = true
      rw [← hagree]; exact hcov
    exact coveredFn_declared hTT hSV hTS h0 hco hcov0

/-! ## The enumerated job — `W3dJobCoverage` discharged from state

`enumJob` bundles the state-derived enumeration for one key: bare leaf concretes ∪ edge
holders as `cands`, bare leaf concretes as `negCands`, userset leaf concretes as
`uposCands` (the persisted `neg`/`upos` the proofs don't need are dropped). Its
`W3dJobCoverage` is exactly the four discharges above fed the leg context — no longer a
hypothesis. -/

/-- The state-derived enumerated job for one derived key `(dt,R)` at object `on`. -/
def enumJob (σ : GraphState) (dt on R : String) (e : Expr) : W3cJob :=
  { dt := dt, on := on, R := R, e := e,
    cands := (leafConcretes σ dt on e).filter (fun u => u.predicate == BARE)
             ++ edgeHolders σ dt on R,
    negCands := (leafConcretes σ dt on e).filter (fun u => u.predicate == BARE),
    uposCands := (leafConcretes σ dt on e).filter (fun u => u.predicate != BARE) }

/-- **`W3dJobCoverage` as a theorem of the enumeration.** At any W3d state, the
    enumerated job for a declared derived key satisfies all four coverage clauses —
    discharging the chain-side hypothesis of `ReachedByW3dC.cascade`. -/
theorem w3dJobCoverage_enumJob {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3d σ S T) {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false) (hon : on ≠ STAR)
    (hWSb : ∀ sh ∈ wildcardShapes S, sh.2 = BARE) :
    W3dJobCoverage S T σ (enumJob σ dt on R e) := by
  obtain ⟨hbridge, hcovDecl⟩ := w3d_leg_context hWF hTT hNK hR hSV hBS hTS hRootB hMatch
    hStrat hterm h hlk hco hleafUnt hon
  have hcl := reachedByW3d_edgesClosed h
  have hbareSub : ∀ u ∈ leafConcretes σ dt on e, u.predicate = BARE →
      u ∈ (leafConcretes σ dt on e).filter (fun u => u.predicate == BARE) :=
    fun u hu hub => List.mem_filter.mpr ⟨hu, by simp [hub]⟩
  refine ⟨fun s hs => ?_, fun s hsb hsn hsem hunc => ?_,
    fun s hsn hcov hstar hsemF => ?_, fun s hsu hsn hsem => ?_⟩
  · -- clause (1): edge holders
    exact List.mem_append_right _ (mem_edgeHolders hs)
  · -- clause (2): uncovered sem-true bare
    exact List.mem_append_left _
      (cands_complete_uncovered hco hcl hon hbridge hcovDecl hbareSub hsb hsn hsem hunc)
  · -- clause (3): covered sem-false → negCands
    exact negCands_complete hco hcl hon hbridge hWSb hbareSub hsn hcov hstar hsemF
  · -- clause (4): sem-true userset → uposCands
    refine uposCands_complete hco hcl hon hbridge hcovDecl hWSb ?_ hsu hsn hsem
    exact fun u hu huu => List.mem_filter.mpr ⟨hu, by simp [huu]⟩

/-! ## W3d-1c piece B TAIL — the enumerated-cascade restatement

`w3dJobCoverage_enumJob` discharges `W3dJobCoverage` for the state-derived `enumJob`.
The last mile: assemble a fully-operational scheduler closure whose cascade legs are
BUILT from `enumJobs` (the per-key `enumJob` list), so `graph_correct_w3d` /
`reachedByW3dC_inv` no longer carry `W3dJobCoverage` (or `hcover`/`hscope`/`hjv`) as
constructor hypotheses — they are discharged from the state. -/

/-- Every leaf-concrete subject is star-free (`leafConcretes` filters `name != STAR`;
    `nodeSubj` keeps the name). -/
theorem leafConcretes_name_ne_star {σ : GraphState} {dt on : String} {e : Expr}
    {c : SubjectRef} (h : c ∈ leafConcretes σ dt on e) : c.name ≠ STAR := by
  rw [leafConcretes, List.mem_map] at h
  obtain ⟨u, hu, hc⟩ := h
  rw [List.mem_filter] at hu
  obtain ⟨_, hcond⟩ := hu
  rw [Bool.and_eq_true, Bool.and_eq_true] at hcond
  obtain ⟨⟨_, hns⟩, _⟩ := hcond
  rw [← hc]
  show u.name ≠ STAR
  intro heq; rw [heq] at hns; simp at hns

/-- **The star-free analog of `reachedByW3d_Rnode_source_bare`.** Every in-edge source
    at a `RootBoolean` derived R-node is star-free on a W3d state: write legs never
    land there (model-level I5, `writeLeg_derived_inedges_eq`), cascade edges are
    sourced at star-free candidates (`W3cJobValid`'s `cands` non-star clause). Same
    induction as `_source_bare`. -/
theorem reachedByW3d_Rnode_source_name_ne_star {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {e : Expr}
    (h : ReachedByW3d σ S T) :
    NodupKeys S → S.lookup (dt, R) = some e → RootBoolean e → StoreValidRules S T →
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.name ≠ STAR := by
  induction h with
  | empty S =>
    intro _ _ _ _ x hx
    simp [emptyState] at hx
  | @write σp S T t hadm hprev ih =>
    intro hNK hlk hroot hSV x hx
    rw [writeLeg_derived_inedges_eq hNK hSV hlk hroot x] at hx
    exact ih hNK hlk hroot (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) x hx
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    intro hNK hlk hroot hSV x hx
    rcases runCascade_cases S T σp jobs with hrc | hrc
    · rw [hrc] at hx
      have hx' : (x, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsL S T σp jobs).edges := hx
      rw [(reconcileJobsL_evalEq (EvalEq.refl σp) S T jobs).edges] at hx'
      rcases reconcileJobsD_edge_sound jobs σp x _ hx' with hold | ⟨j, hj, c, hc, h1, _⟩
      · exact ih hNK hlk hroot hSV x hold
      · obtain ⟨_, _, hcStar, _⟩ := hjv j hj
        rw [h1, subjNode_plain (hcStar c hc)]
        exact hcStar c hc
    · rw [hrc] at hx
      exact ih hNK hlk hroot hSV x hx

/-! ### Cascade-key structural facts

Every cascade key `(dt, R, on)` is a declared derived key at a star-free object — read
straight off `affectedKeys`' `_map_deltas_to_keys` branch (`isDerived`, `S.lookup`,
`v.name ≠ STAR`). -/

/-- Every `affectedKeys` triple names a declared derived key at a star-free object. -/
theorem mem_affectedKeys_props {S : Schema} {σ : GraphState} {d : Delta}
    {k : String × String × String} (hk : k ∈ affectedKeys S σ d) :
    isDerived S (k.1, k.2.1) = true ∧ (∃ e, S.lookup (k.1, k.2.1) = some e) ∧
      k.2.2 ≠ STAR := by
  unfold affectedKeys at hk
  obtain ⟨v, _, hkv⟩ := List.mem_flatMap.mp hk
  by_cases hvs : v.name = STAR
  · rw [if_pos hvs] at hkv; exact absurd hkv (List.not_mem_nil)
  · rw [if_neg hvs] at hkv
    obtain ⟨k', _, hfk⟩ := List.mem_filterMap.mp hkv
    by_cases hc : k'.1 = v.type ∧ isDerived S k' = true ∧
        ((S.lookup k').map (fun e => (computedRefs e).contains v.pred)).getD false = true
    · rw [if_pos hc] at hfk
      obtain rfl := (Option.some.inj hfk).symm
      obtain ⟨_, hcder, hclk⟩ := hc
      have hlksome : ∃ e, S.lookup k' = some e := by
        cases hl : S.lookup k' with
        | none => rw [hl] at hclk; simp at hclk
        | some e => exact ⟨e, rfl⟩
      exact ⟨hcder, hlksome, hvs⟩
    · rw [if_neg hc] at hfk; exact absurd hfk (by simp)

/-- Every cascade key names a declared derived key at a star-free object. -/
theorem mem_cascadeKeys_props {S : Schema} {σ : GraphState}
    {k : String × String × String} (hk : k ∈ cascadeKeys S σ) :
    isDerived S (k.1, k.2.1) = true ∧ (∃ e, S.lookup (k.1, k.2.1) = some e) ∧
      k.2.2 ≠ STAR := by
  unfold cascadeKeys at hk
  obtain ⟨_, _, hkd⟩ := List.mem_flatMap.mp hk
  exact mem_affectedKeys_props hkd

/-! ### `enumJob` is `W3cJobValid` -/

/-- **`enumJob` is a valid W3c job.** The bare-filtered leaf concretes and the edge
    holders give bare, star-free candidates (`reachedByW3d_Rnode_source_bare` /
    `_source_name_ne_star` for the holders); the leaf concretes are star-free
    (`leafConcretes_name_ne_star`); the userset candidates are non-bare by the filter;
    the declared-derived key data comes from the enumeration hypotheses. -/
theorem w3cJobValid_enumJob {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (h : ReachedByW3d σ S T) {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hon : on ≠ STAR) :
    W3cJobValid S (enumJob σ dt on R e) := by
  have hroot : RootBoolean e := hRootB ⟨(dt, R), e⟩ (mem_defs_of_lookup hlk) hder
  unfold W3cJobValid
  refine ⟨lookup_rel_ne_bare hWF hlk, ?_, ?_, ?_, ?_, ?_, hder, hlk, hon⟩
  · -- cands are bare
    intro c hc
    simp only [enumJob, List.mem_append] at hc
    rcases hc with hcl | hcr
    · rw [List.mem_filter] at hcl; exact eq_of_beq hcl.2
    · rw [edgeHolders, List.mem_map] at hcr
      obtain ⟨ed, hed, hce⟩ := hcr
      rw [List.mem_filter] at hed
      obtain ⟨hedm, hedeq⟩ := hed
      have hb : ed.2 = objNode ⟨dt, on⟩ R := eq_of_beq hedeq
      have hmem : (ed.1, objNode ⟨dt, on⟩ R) ∈ σ.edges := by rw [← hb]; exact hedm
      rw [← hce]
      exact reachedByW3d_Rnode_source_bare h hNK hlk hroot hSV ed.1 hmem
  · -- cands are star-free
    intro c hc
    simp only [enumJob, List.mem_append] at hc
    rcases hc with hcl | hcr
    · exact leafConcretes_name_ne_star (List.mem_filter.mp hcl).1
    · rw [edgeHolders, List.mem_map] at hcr
      obtain ⟨ed, hed, hce⟩ := hcr
      rw [List.mem_filter] at hed
      obtain ⟨hedm, hedeq⟩ := hed
      have hb : ed.2 = objNode ⟨dt, on⟩ R := eq_of_beq hedeq
      have hmem : (ed.1, objNode ⟨dt, on⟩ R) ∈ σ.edges := by rw [← hb]; exact hedm
      rw [← hce]
      exact reachedByW3d_Rnode_source_name_ne_star h hNK hlk hroot hSV ed.1 hmem
  · -- negCands are star-free
    intro c hc
    simp only [enumJob] at hc
    exact leafConcretes_name_ne_star (List.mem_filter.mp hc).1
  · -- uposCands are non-bare
    intro c hc
    simp only [enumJob] at hc
    have hb := (List.mem_filter.mp hc).2
    intro heq; rw [heq] at hb; simp at hb
  · -- uposCands are star-free
    intro c hc
    simp only [enumJob] at hc
    exact leafConcretes_name_ne_star (List.mem_filter.mp hc).1

/-! ### `enumJobs` — the per-key enumerated cascade -/

/-- The canonical cascade job list read off the state: one `enumJob` per cascade key
    (with the key's declared def fetched from the schema). -/
def enumJobs (S : Schema) (σ : GraphState) : List W3cJob :=
  (cascadeKeys S σ).filterMap (fun k =>
    (S.lookup (k.1, k.2.1)).map (fun e => enumJob σ k.1 k.2.2 k.2.1 e))

/-- Every cascade key has an enumerated job (coverage by construction). -/
theorem enumJobs_cover {S : Schema} {σ : GraphState} :
    ∀ k ∈ cascadeKeys S σ, ∃ j ∈ enumJobs S σ, j.key = k := by
  intro k hk
  obtain ⟨_, ⟨e, hlk⟩, _⟩ := mem_cascadeKeys_props hk
  refine ⟨enumJob σ k.1 k.2.2 k.2.1 e, ?_, rfl⟩
  refine List.mem_filterMap.mpr ⟨k, hk, ?_⟩
  rw [hlk]; rfl

/-- Every enumerated job's key is a cascade key (scope by construction). -/
theorem enumJobs_scope {S : Schema} {σ : GraphState} :
    ∀ j ∈ enumJobs S σ, j.key ∈ cascadeKeys S σ := by
  intro j hj
  rw [enumJobs, List.mem_filterMap] at hj
  obtain ⟨k, hk, hfk⟩ := hj
  obtain ⟨e, _, hje⟩ := Option.map_eq_some_iff.mp hfk
  rw [← hje]
  exact hk

/-- Every enumerated job is `W3cJobValid`. -/
theorem enumJobs_valid {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (h : ReachedByW3d σ S T) :
    ∀ j ∈ enumJobs S σ, W3cJobValid S j := by
  intro j hj
  rw [enumJobs, List.mem_filterMap] at hj
  obtain ⟨k, hk, hfk⟩ := hj
  obtain ⟨e, hlk, hje⟩ := Option.map_eq_some_iff.mp hfk
  obtain ⟨hder, _, hon⟩ := mem_cascadeKeys_props hk
  rw [← hje]
  exact w3cJobValid_enumJob hWF hNK hSV hRootB h hlk hder hon

/-- Every enumerated job satisfies `W3dJobCoverage` (the discharge from state). -/
theorem enumJobs_covg {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d σ S T) :
    ∀ j ∈ enumJobs S σ, W3dJobCoverage S T σ j := by
  intro j hj
  rw [enumJobs, List.mem_filterMap] at hj
  obtain ⟨k, hk, hfk⟩ := hj
  obtain ⟨e, hlk, hje⟩ := Option.map_eq_some_iff.mp hfk
  obtain ⟨hder, _, hon⟩ := mem_cascadeKeys_props hk
  rw [← hje]
  exact w3dJobCoverage_enumJob hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm h
    hlk (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder) hon hWSbare

/-! ### The fully-operational scheduler closure and the unconditional restatements -/

/-- **`ReachedByW3dE`** — the interleaved scheduler closure with FULLY-OPERATIONAL
    cascade legs: each cascade runs the canonical `enumJobs` list read off the state.
    No `W3cJobValid` / `hcover` / `hscope` / `W3dJobCoverage` hypotheses — they are
    theorems of the enumeration (`enumJobs_valid`/`_cover`/`_scope`/`_covg`). -/
inductive ReachedByW3dE : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByW3dE (emptyState S) S []
  | write {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hadm : FoldAdmits σ (rewriteClosure S t))
      (hprev : ReachedByW3dE σ S T) :
      ReachedByW3dE (σ.writeLoggedRules S t) S (t :: T)
  | cascade {σ : GraphState} {S : Schema} {T : Store}
      (hprev : ReachedByW3dE σ S T) :
      ReachedByW3dE (runCascade S T σ (enumJobs S σ)) S T

/-- **The projection `ReachedByW3dE ⇒ ReachedByW3dC`.** Each fully-operational cascade
    leg's four coverage hypotheses are discharged from state by `enumJobs_*`; store
    hypotheses weaken along write prefixes. All fragment hypotheses are threaded as
    premises (the schema/store are inductive indices). -/
theorem reachedByW3dE_toC {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3dE σ S T) :
    WF S → TtuTuplesetsDirect S → NodupKeys S → RewriteRanked S →
    (∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2) →
    RewriteMatchDeclared S → Stratifiable S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false) →
    (∀ sh ∈ wildcardShapes S, sh.2 = BARE) →
    StoreValidRules S T → BareStarStore T → TtuStarFree S T →
    (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) →
    ReachedByW3dC σ S T := by
  induction h with
  | empty S =>
    intro _ _ _ _ _ _ _ _ _ _ _ _ _ _
    exact ReachedByW3dC.empty S
  | @write σp S T t hadm hprev ih =>
    intro hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare hSV hBS hTS hterm
    have hSVw : StoreValidRules S T := fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')
    have hBSw : BareStarStore T := fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')
    have hTSw : TtuStarFree S T := fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht')
    have htermw : ∀ dt R, isDerived S (dt, R) = true →
        NoTtuTarget S R ∧ NoStoreSubjectR T R :=
      fun dt R hd => ⟨(hterm dt R hd).1,
        fun t' ht' => (hterm dt R hd).2 t' (List.mem_cons_of_mem _ ht')⟩
    exact ReachedByW3dC.write t hadm
      (ih hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare hSVw hBSw hTSw htermw)
  | @cascade σp S T hprev ih =>
    intro hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare hSV hBS hTS hterm
    have hC : ReachedByW3dC σp S T :=
      ih hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare hSV hBS hTS hterm
    have hW3d : ReachedByW3d σp S T := reachedByW3dC_toW3d hC
    exact ReachedByW3dC.cascade (enumJobs S σp)
      (enumJobs_valid hWF hNK hSV hRootB hW3d)
      enumJobs_cover enumJobs_scope
      (enumJobs_covg hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hCO hLU
        hWSbare hW3d)
      hC

/-- **T2b, W3d fragment, UNCONDITIONAL (`graph_correct_w3dE`) — `check = sem` at every
    fully-drained state of the FULLY-OPERATIONAL scheduler chain.** Identical to
    `graph_correct_w3d` but over `ReachedByW3dE`, whose cascade legs carry NO
    `W3dJobCoverage` hypothesis — coverage is discharged from state. -/
theorem graph_correct_w3dE {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3dE σ S T) (hq : cascadeKeys S σ = [])
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem S T q :=
  graph_correct_w3d q hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hCO hLU
    hWSbare
    (reachedByW3dE_toC h hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare hSV hBS hTS
      hterm)
    hq hqs hqo

/-- **T2a, W3d fragment, UNCONDITIONAL (`reachedByW3dE_inv`) — the full 8-clause `Inv`
    at every state of the FULLY-OPERATIONAL scheduler chain.** Identical to
    `reachedByW3dC_inv` but over `ReachedByW3dE`. -/
theorem reachedByW3dE_inv {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3dE σ S T)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR T R) :
    Inv S σ :=
  reachedByW3dC_inv
    (reachedByW3dE_toC h hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare hSV hBS hTS
      hterm)
    hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare hSV hBS hTS hterm

end Zanzibar
