import ZanzibarProofs.GraphIndex.CascadeStrataSettle

/-!
# W3d-2 endgame — the two-round targeted re-settlement (ROADMAP W3d-2)

`index_v4/processor.py:382-459` (`reconcile`, now with ROUTED guards at stratum-2
keys), `:694-740` (`run_cascade` at two rounds). This file supplies the ROUTED
mirrors of the W3d-1b re-settle layer that the stratum-staged settledness induction
consumes:

* **The routed per-key edge characterisation** (`reconcileKeyDR_edge_char` /
  `reconcileStarsKeyDR_edge_char`): after one routed diffing pass, a subject's
  derived edge at the key is present iff it is a candidate whose ROUTED guard held
  at the pass-start state, or a non-candidate whose edge predates the pass. The
  W3d-1 char collapses routed guards via conservativity only on all-untainted
  defs; at a stratum-2 key the guard genuinely reads derived operands, so the char
  must be re-proved with `checkFnR`/`coveredFnR` guards. The new ingredient:
  guard fold-invariance now rests on `r' ≠ R` for every computed operand — under
  `hLU2` a derived def never reads ITSELF (a self-reference would make its own
  operands derived), so the pass's edge edits at its own R-node are invisible to
  every leaf the guard consults, whatever the leaf's stratum.
-/

namespace Zanzibar

/-! ## No self-reference under the two-stratum condition -/

/-- Under the per-def two-stratum condition a derived def never reads its own
    relation as a computed operand: `r' = R` would make `R` a derived operand of
    itself, forcing (by `hLU2`) all of `e`'s operands untainted — including `R`. -/
theorem computedRefs_ne_self {S : Schema} {dt R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hLU2e : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false) :
    ∀ r' ∈ computedRefs e, r' ≠ R := by
  intro r' hr' heq
  subst heq
  have hfalse := hLU2e r' hr' hder e hlk r' hr'
  cases hder.symm.trans hfalse

/-! ## Fold-level read inertness at other keys

The `reconcileKeyDR` fold edits edges only AT the pass's own R-node, so every read
anchored at any OTHER `(type, name, relation)` key is fold-constant — the fold-only
halves of `graphRec_reconcileStarsKeyDR_inert` / `probeDerived_reconcileStarsKeyDR_other`
(which state the same facts for the WHOLE pass, residue write included). -/

/-- The untainted ≤4-probe read is fold-inert (the probe targets are never the
    pass's derived R-node). -/
theorem graphRec_reconcileKeyDR_other {σ : GraphState} {S : Schema} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) (hRne : R ≠ BARE)
    (hcands : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (s : SubjectRef) (dt' on' r' : String) (hunt : isDerived S (dt', r') = false) :
    GraphModel.graphRec (σ.reconcileKeyDR T dt on R e cands) s dt' on' r'
      = GraphModel.graphRec σ s dt' on' r' := by
  have hvne1 : objNode ⟨dt', on'⟩ r' ≠ objNode ⟨dt, on⟩ R := by
    intro heq
    have htype : dt' = dt := by
      have := congrArg NodeKey.type heq
      simpa [objNode_type] using this
    have hpred : r' = R := by
      have := congrArg NodeKey.pred heq
      simpa [objNode_pred] using this
    rw [htype, hpred, hder] at hunt
    cases hunt
  have hvne3 : wAllNode dt' r' ≠ objNode ⟨dt, on⟩ R := by
    unfold wAllNode objNode
    rw [if_neg honStar]
    intro heq
    have := congrArg NodeKey.variant heq
    simp at this
  have hcl2 := edgesClosed_reconcileKeyDR T dt on R e cands σ hcl
  have hiff2 := GraphModel.probeNonDerived_iff hcl2 (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  have hiffσ := GraphModel.probeNonDerived_iff hcl (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  have hpres1 : ∀ {u : NodeKey},
      NReaches σ.edges u (objNode ⟨dt', on'⟩ r') →
      NReaches (σ.reconcileKeyDR T dt on R e cands).edges u (objNode ⟨dt', on'⟩ r') :=
    fun hn => reconcileKeyDR_reach_pres T dt on R e cands hRne hvne1 hcands hRns hn
  have hpres3 : ∀ {u : NodeKey},
      NReaches σ.edges u (wAllNode dt' r') →
      NReaches (σ.reconcileKeyDR T dt on R e cands).edges u (wAllNode dt' r') :=
    fun hn => reconcileKeyDR_reach_pres T dt on R e cands hRne hvne3 hcands hRns hn
  have hinert1 : ∀ {u : NodeKey},
      NReaches (σ.reconcileKeyDR T dt on R e cands).edges u (objNode ⟨dt', on'⟩ r') →
      NReaches σ.edges u (objNode ⟨dt', on'⟩ r') :=
    fun hn => reconcileKeyDR_reach_inert T dt on R e cands hRne hvne1 hcands hRns hn
  have hinert3 : ∀ {u : NodeKey},
      NReaches (σ.reconcileKeyDR T dt on R e cands).edges u (wAllNode dt' r') →
      NReaches σ.edges u (wAllNode dt' r') :=
    fun hn => reconcileKeyDR_reach_inert T dt on R e cands hRne hvne3 hcands hRns hn
  show GraphModel.probeNonDerived (σ.reconcileKeyDR T dt on R e cands)
      (⟨s, r', ⟨dt', on'⟩⟩ : Query) = GraphModel.probeNonDerived σ (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  cases hb2 : GraphModel.probeNonDerived (σ.reconcileKeyDR T dt on R e cands)
      (⟨s, r', ⟨dt', on'⟩⟩ : Query)
    <;> cases hb1 : GraphModel.probeNonDerived σ (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  · rfl
  · exfalso
    have hd := hiffσ.mp hb1
    have : GraphModel.probeNonDerived (σ.reconcileKeyDR T dt on R e cands)
        (⟨s, r', ⟨dt', on'⟩⟩ : Query) = true := by
      apply hiff2.mpr
      rcases hd with h1 | ⟨hs, h2⟩ | ⟨ho, h3⟩ | ⟨hs, ho, h4⟩
      · exact Or.inl (hpres1 h1)
      · exact Or.inr (Or.inl ⟨hs, hpres1 h2⟩)
      · exact Or.inr (Or.inr (Or.inl ⟨ho, hpres3 h3⟩))
      · exact Or.inr (Or.inr (Or.inr ⟨hs, ho, hpres3 h4⟩))
    rw [hb2] at this
    cases this
  · exfalso
    have hd := hiff2.mp hb2
    have : GraphModel.probeNonDerived σ (⟨s, r', ⟨dt', on'⟩⟩ : Query) = true := by
      apply hiffσ.mpr
      rcases hd with h1 | ⟨hs, h2⟩ | ⟨ho, h3⟩ | ⟨hs, ho, h4⟩
      · exact Or.inl (hinert1 h1)
      · exact Or.inr (Or.inl ⟨hs, hinert1 h2⟩)
      · exact Or.inr (Or.inr (Or.inl ⟨ho, hinert3 h3⟩))
      · exact Or.inr (Or.inr (Or.inr ⟨hs, ho, hinert3 h4⟩))
    rw [hb1] at this
    cases this
  · rfl

/-- The derived edge+residue read at any OTHER key is fold-inert (the fold is
    residue-inert and its edge edits live at its own R-node). -/
theorem probeDerived_reconcileKeyDR_other {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) (hRne : R ≠ BARE)
    (hcands : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) (honStar : on ≠ STAR)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (q : Query) (hne : ¬(q.object.type = dt ∧ q.object.name = on ∧ q.relation = R)) :
    GraphModel.probeDerived (σ.reconcileKeyDR T dt on R e cands) q
      = GraphModel.probeDerived σ q := by
  have hvne : objNode q.object q.relation ≠ objNode ⟨dt, on⟩ R := by
    intro heq
    by_cases hoStar : q.object.name = STAR
    · have hv := congrArg NodeKey.variant heq
      unfold objNode at hv
      rw [if_pos hoStar, if_neg honStar] at hv
      simp at hv
    · exact hne (objNode_inj_of_ne_star hoStar honStar heq)
  have hres : (σ.reconcileKeyDR T dt on R e cands).residue (objNode q.object q.relation)
      q.relation = σ.residue (objNode q.object q.relation) q.relation := by
    rw [reconcileKeyDR_residue]
  have hcl2 := edgesClosed_reconcileKeyDR T dt on R e cands σ hcl
  have hreach : (σ.reconcileKeyDR T dt on R e cands).reach (subjNode q.subject)
      (objNode q.object q.relation) = σ.reach (subjNode q.subject)
        (objNode q.object q.relation) := by
    cases hb2 : (σ.reconcileKeyDR T dt on R e cands).reach (subjNode q.subject)
        (objNode q.object q.relation)
      <;> cases hb1 : σ.reach (subjNode q.subject) (objNode q.object q.relation)
    · rfl
    · exfalso
      have hn := reconcileKeyDR_reach_pres T dt on R e cands hRne hvne hcands hRns
        (reach_sound hb1)
      rw [reach_complete hcl2 hn] at hb2
      cases hb2
    · exfalso
      have hn := reconcileKeyDR_reach_inert T dt on R e cands hRne hvne hcands hRns
        (reach_sound hb2)
      rw [reach_complete hcl hn] at hb1
      cases hb1
    · rfl
  unfold GraphModel.probeDerived
  simp only [hres, hreach]

/-- **The routed leaf read is fold-inert off the pass's key** — whatever the queried
    key's stratum (the fold-only half of `check_reconcileStarsKeyDR_other`). -/
theorem check_reconcileKeyDR_other {σ : GraphState} {S : Schema} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef)
    (hσS : σ.schema = S) (hRne : R ≠ BARE)
    (hcands : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (q : Query) (hne : ¬(q.object.type = dt ∧ q.object.name = on ∧ q.relation = R)) :
    GraphModel.check (σ.reconcileKeyDR T dt on R e cands) q = GraphModel.check σ q := by
  have hschema : (σ.reconcileKeyDR T dt on R e cands).schema = σ.schema :=
    reconcileKeyDR_schema T dt on R e cands σ
  cases hd : isDerived S (q.object.type, q.relation) with
  | false =>
    rw [GraphModel.check_untainted _ q (by rw [hschema, hσS]; exact hd),
      GraphModel.check_untainted σ q (by rw [hσS]; exact hd)]
    exact graphRec_reconcileKeyDR_other (S := S) T dt on R e cands hRne hcands hRns
      honStar hder hcl q.subject q.object.type q.object.name q.relation hd
  | true =>
    rw [GraphModel.check_derived _ q (by rw [hschema, hσS]; exact hd),
      GraphModel.check_derived σ q (by rw [hσS]; exact hd)]
    exact probeDerived_reconcileKeyDR_other T dt on R e cands hRne hcands hRns honStar
      hcl q hne

/-! ## The routed per-candidate guard and its fold-invariance -/

/-- The routed per-candidate edge guard `want = should ∧ ¬covered`
    (`reconcile_subject`, `processor.py:359`, with the ROUTED `should`). -/
def GraphState.wantEdgeR (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (c : SubjectRef) : Bool :=
  σ.checkFnR T c dt on R e && !(σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)

/-- A one-candidate routed fold is a single diff step, guard spelled via `wantEdgeR`. -/
theorem reconcileKeyDR_singleton (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (c : SubjectRef) :
    σ.reconcileKeyDR T dt on R e [c]
      = if σ.wantEdgeR T dt on R e c then σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩
        else σ.removeEdgePair (subjNode c) (objNode ⟨dt, on⟩ R) := rfl

/-- The routed guard is fold-invariant: every leaf the guard consults sits at a key
    `(dt, on, r')` with `r' ≠ R` (no self-reference), where the fold is read-inert;
    the covered gate reads the residue, which the fold never writes. -/
theorem wantEdgeR_reconcileKeyDR_inert {σ : GraphState} {S : Schema} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) (hRne : R ≠ BARE)
    (hσS : σ.schema = S)
    (hcands : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e) (hrne : ∀ r' ∈ computedRefs e, r' ≠ R)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) (x : SubjectRef) :
    (σ.reconcileKeyDR T dt on R e cands).wantEdgeR T dt on R e x
      = σ.wantEdgeR T dt on R e x := by
  unfold GraphState.wantEdgeR
  have hchk : (σ.reconcileKeyDR T dt on R e cands).checkFnR T x dt on R e
      = σ.checkFnR T x dt on R e := by
    unfold GraphState.checkFnR
    refine evalE_computedOnly e hco ?_
    intro r' hr'
    show GraphModel.graphRecR _ x dt on r' = GraphModel.graphRecR σ x dt on r'
    unfold GraphModel.graphRecR
    exact check_reconcileKeyDR_other T dt on R e cands hσS hRne hcands hRns honStar
      hder hcl ⟨x, r', ⟨dt, on⟩⟩ (fun h => hrne r' hr' h.2.2)
  have hcov : (σ.reconcileKeyDR T dt on R e cands).coveredAt (objNode ⟨dt, on⟩ R) R
      x.shape = σ.coveredAt (objNode ⟨dt, on⟩ R) R x.shape := by
    unfold GraphState.coveredAt
    rw [reconcileKeyDR_residue]
  rw [hchk, hcov]

/-! ## The routed per-key edge characterisation -/

/-- **The routed per-key edge characterisation** (guards abstracted to a
    fold-invariant `g`) — mirror of `reconcileKeyD_edge_char` with the routed guard;
    history for candidates is fully erased. -/
theorem reconcileKeyDR_edge_char {S : Schema} (T : Store) (dt on R : String) (e : Expr)
    (hRne : R ≠ BARE) (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e) (hrne : ∀ r' ∈ computedRefs e, r' ≠ R)
    (g : SubjectRef → Bool) :
    ∀ (cands : List SubjectRef) (σ : GraphState), σ.schema = S →
      (∀ c ∈ cands, c.predicate = BARE) →
      (∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) →
      (∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) →
      (∀ c ∈ cands, σ.wantEdgeR T dt on R e c = g c) →
      ∀ s : SubjectRef,
        ((subjNode s, objNode ⟨dt, on⟩ R) ∈ (σ.reconcileKeyDR T dt on R e cands).edges
          ↔ ((s ∈ cands ∧ g s = true) ∨
             (s ∉ cands ∧ (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges))) := by
  intro cands
  induction cands with
  | nil =>
    intro σ _ _ _ _ _ s
    show (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges ↔ _
    simp
  | cons c rest ih =>
    intro σ hσS hcb hRns hcl hg s
    have hcb1 : ∀ x ∈ [c], x.predicate = BARE := by
      intro x hx
      rw [List.mem_singleton.mp hx]
      exact hcb c List.mem_cons_self
    have hstep : σ.reconcileKeyDR T dt on R e (c :: rest)
        = (σ.reconcileKeyDR T dt on R e [c]).reconcileKeyDR T dt on R e rest := rfl
    set σc := σ.reconcileKeyDR T dt on R e [c] with hσc
    have hσcS : σc.schema = S := by
      rw [hσc, reconcileKeyDR_schema]
      exact hσS
    have hRns1 : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σc.edges :=
      reconcileKeyDR_Rnode_terminal T dt on R e hRne [c] hcb1 σ hRns
    have hcl1 : ∀ ab ∈ σc.edges, ab.1 ∈ σc.nodes ∧ ab.2 ∈ σc.nodes :=
      edgesClosed_reconcileKeyDR T dt on R e [c] σ hcl
    have hg1 : ∀ x ∈ rest, σc.wantEdgeR T dt on R e x = g x := by
      intro x hx
      rw [hσc, wantEdgeR_reconcileKeyDR_inert (S := S) T dt on R e [c] hRne hσS hcb1
        hRns honStar hder hco hrne hcl x]
      exact hg x (List.mem_cons_of_mem _ hx)
    have hgc : σ.wantEdgeR T dt on R e c = g c := hg c List.mem_cons_self
    have hpairc : ∀ s : SubjectRef,
        ((subjNode s, objNode ⟨dt, on⟩ R) ∈ σc.edges
          ↔ ((s = c ∧ g c = true) ∨
             (s ≠ c ∧ (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges))) := by
      intro s
      rw [hσc, reconcileKeyDR_singleton, hgc]
      cases hgcv : g c
      · rw [if_neg (by simp), mem_removeEdgePair_edges]
        constructor
        · rintro ⟨hmem, hne⟩
          refine Or.inr ⟨?_, hmem⟩
          intro heq
          exact hne ⟨by rw [heq], rfl⟩
        · rintro (⟨_, hfalse⟩ | ⟨hne, hmem⟩)
          · exact absurd hfalse (by simp)
          · refine ⟨hmem, ?_⟩
            rintro ⟨h1, _⟩
            exact hne (subjNode_inj_total h1)
      · rw [if_pos rfl, writeDirect_edges]
        have hadm : σ.admitEdge (subjNode c) (objNode ⟨dt, on⟩ R) = true := by
          unfold GraphState.admitEdge
          rw [Bool.and_eq_true]
          constructor
          · rw [bne_iff_ne]
            intro heq
            have hpred := congrArg NodeKey.pred heq
            rw [subjNode_pred, objNode_pred, hcb c List.mem_cons_self] at hpred
            exact hRne hpred.symm
          · cases hr : σ.reach (objNode ⟨dt, on⟩ R) (subjNode c)
            · rfl
            · exfalso
              obtain ⟨y, hy⟩ := nreaches_first_edge (reach_sound hr)
              exact hRns y hy
        rw [if_pos hadm]
        constructor
        · intro hmem
          rcases List.mem_cons.mp hmem with heq | hold
          · have h1 := (Prod.ext_iff.mp heq).1
            exact Or.inl ⟨subjNode_inj_total h1, rfl⟩
          · by_cases hsc : s = c
            · exact Or.inl ⟨hsc, rfl⟩
            · exact Or.inr ⟨hsc, hold⟩
        · rintro (⟨hsc, _⟩ | ⟨_, hold⟩)
          · rw [hsc]
            exact List.mem_cons_self
          · exact List.mem_cons_of_mem _ hold
    rw [hstep]
    rw [ih σc hσcS (fun x hx => hcb x (List.mem_cons_of_mem _ hx)) hRns1 hcl1 hg1 s]
    rw [hpairc s]
    constructor
    · rintro (⟨hsr, hgs⟩ | ⟨hsr, (⟨hsc, hgc'⟩ | ⟨hsc, hold⟩)⟩)
      · exact Or.inl ⟨List.mem_cons_of_mem _ hsr, hgs⟩
      · exact Or.inl ⟨by rw [hsc]; exact List.mem_cons_self, by rw [hsc]; exact hgc'⟩
      · refine Or.inr ⟨?_, hold⟩
        intro hmem
        rcases List.mem_cons.mp hmem with heq | hr
        · exact hsc heq
        · exact hsr hr
    · rintro (⟨hmem, hgs⟩ | ⟨hmem, hold⟩)
      · rcases List.mem_cons.mp hmem with heq | hr
        · by_cases hsr : s ∈ rest
          · exact Or.inl ⟨hsr, hgs⟩
          · exact Or.inr ⟨hsr, Or.inl ⟨heq, by rw [← heq]; exact hgs⟩⟩
        · exact Or.inl ⟨hr, hgs⟩
      · have hsc : s ≠ c := fun heq => hmem (by rw [heq]; exact List.mem_cons_self)
        have hsr : s ∉ rest := fun hr => hmem (List.mem_cons_of_mem _ hr)
        exact Or.inr ⟨hsr, Or.inr ⟨hsc, hold⟩⟩

/-! ## The routed residue write is read-inert at other keys -/

/-- The row the ROUTED residue recompute writes at its own key — the three routed
    filters, evaluated at the pass-start state. -/
theorem reconcileResidueKeyR_residue_self (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands).residue
        (objNode ⟨dt, on⟩ R) R =
      some ⟨shapes.filter (fun sh => σ.coveredFnR T dt on R e sh),
            negCands.filter (fun c =>
              (shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)).contains c.shape
                && !(σ.checkFnR T c dt on R e)),
            uposCands.filter (fun c =>
              !((shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)).contains c.shape)
                && σ.checkFnR T c dt on R e)⟩ := by
  unfold GraphState.reconcileResidueKeyR
  rw [putResidue_residue, if_pos ⟨rfl, rfl⟩]

/-- The routed leaf read at a key the residue write does NOT own is unchanged: the
    write is edge/node-inert and every consulted residue row sits at another
    `(node, relation)` pair. -/
theorem check_reconcileResidueKeyR_other {σ : GraphState} {S : Schema} (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (negCands uposCands : List SubjectRef) (hσS : σ.schema = S)
    (q : Query)
    (hne : ¬(objNode q.object q.relation = objNode ⟨dt, on⟩ R ∧ q.relation = R)) :
    GraphModel.check (σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands) q
      = GraphModel.check σ q := by
  set σr := σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands with hσr
  have hE : σr.edges = σ.edges := by rw [hσr]; rfl
  have hN : σr.nodes = σ.nodes := by rw [hσr]; rfl
  have hSc : σr.schema = σ.schema := by rw [hσr]; rfl
  cases hd : isDerived S (q.object.type, q.relation) with
  | false =>
    rw [GraphModel.check_untainted σr q (by rw [hSc, hσS]; exact hd),
      GraphModel.check_untainted σ q (by rw [hσS]; exact hd)]
    exact probeNonDerived_congr hE hN q
  | true =>
    rw [GraphModel.check_derived σr q (by rw [hSc, hσS]; exact hd),
      GraphModel.check_derived σ q (by rw [hσS]; exact hd)]
    have hres : σr.residue (objNode q.object q.relation) q.relation
        = σ.residue (objNode q.object q.relation) q.relation := by
      rw [hσr]
      exact reconcileResidueKeyR_residue_other hne
    have hreach : σr.reach (subjNode q.subject) (objNode q.object q.relation)
        = σ.reach (subjNode q.subject) (objNode q.object q.relation) := by
      unfold GraphState.reach
      rw [hE, hN]
    unfold GraphModel.probeDerived
    simp only [hres, hreach]

/-! ## Pass-level routed edge exactness -/

/-- **Pass-level routed edge exactness** (`reconcileStarsKeyDR_edge_char`): after one
    full-object ROUTED diffing pass, a subject's derived edge at the key is present
    iff it is a candidate whose ROUTED guard holds at the PASS-START state —
    `checkFnR` true and its shape not in the freshly-recomputed routed `stars` row —
    or a non-candidate whose edge predates the pass. The stratum-2 wholesale
    re-settle, as a theorem. -/
theorem reconcileStarsKeyDR_edge_char {S : Schema} {σ : GraphState} (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (cands negCands uposCands : List SubjectRef)
    (hσS : σ.schema = S) (hRne : R ≠ BARE) (honStar : on ≠ STAR)
    (hder : isDerived S (dt, R) = true) (hco : ComputedOnly e)
    (hrne : ∀ r' ∈ computedRefs e, r' ≠ R)
    (hcb : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (s : SubjectRef) :
    ((subjNode s, objNode ⟨dt, on⟩ R)
        ∈ (σ.reconcileStarsKeyDR T dt on R e shapes cands negCands uposCands).edges
      ↔ ((s ∈ cands ∧ (σ.checkFnR T s dt on R e
            && !((shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)).contains
                  s.shape)) = true) ∨
         (s ∉ cands ∧ (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges))) := by
  unfold GraphState.reconcileStarsKeyDR
  set σr := σ.reconcileResidueKeyR T dt on R e shapes negCands uposCands with hσr
  have hedges : σr.edges = σ.edges := by rw [hσr]; rfl
  have hnodes : σr.nodes = σ.nodes := by rw [hσr]; rfl
  have hσrS : σr.schema = S := by
    rw [hσr]
    show σ.schema = S
    exact hσS
  have hRnsr : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σr.edges := by
    intro y
    rw [hedges]
    exact hRns y
  have hclr : ∀ ab ∈ σr.edges, ab.1 ∈ σr.nodes ∧ ab.2 ∈ σr.nodes := by
    intro ab hab
    rw [hedges] at hab
    rw [hnodes]
    exact hcl ab hab
  -- the fold-invariant routed guard, evaluated at the ORIGINAL σ
  have hg : ∀ c ∈ cands, σr.wantEdgeR T dt on R e c
      = (σ.checkFnR T c dt on R e
          && !((shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)).contains
                c.shape)) := by
    intro c _
    unfold GraphState.wantEdgeR
    have hchkr : σr.checkFnR T c dt on R e = σ.checkFnR T c dt on R e := by
      unfold GraphState.checkFnR
      refine evalE_computedOnly e hco ?_
      intro r' hr'
      show GraphModel.graphRecR σr c dt on r' = GraphModel.graphRecR σ c dt on r'
      unfold GraphModel.graphRecR
      rw [hσr]
      exact check_reconcileResidueKeyR_other T dt on R e shapes negCands uposCands hσS
        ⟨c, r', ⟨dt, on⟩⟩ (fun h => hrne r' hr' h.2)
    have hcovr : σr.coveredAt (objNode ⟨dt, on⟩ R) R c.shape
        = (shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)).contains c.shape := by
      unfold GraphState.coveredAt
      rw [hσr, reconcileResidueKeyR_residue_self]
      rfl
    rw [hchkr, hcovr]
  have hchar := reconcileKeyDR_edge_char (S := S) T dt on R e hRne honStar hder hco hrne
    (fun c => σ.checkFnR T c dt on R e
      && !((shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)).contains c.shape))
    cands σr hσrS hcb hRnsr hclr hg s
  rw [hchar, hedges]

/-! ## The routed batch edge origin at a fixed derived key

The routed mirror of `reconcileJobsD_key_edge_sem`, with the STRATUM-STAGED bridge
at each prefix state: an edge of a routed logged batch at the key carries a
`sem`-true subject or predates the batch. The bridge (`checkFnR_eq_sem_settled`)
needs the key's derived operand keys settled+complete at each prefix state — so the
walk threads their settledness (transported stepwise: no batch job targets an
operand key) together with the edge discipline that yields their reach collapse. -/

theorem reconcileJobsLR_key_edge_sem {S : Schema} {T : Store} {σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hRne : R ≠ BARE) (hon : on ≠ STAR)
    (hLU2e : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false) :
    ∀ (js : List W3cJob) (σ : GraphState),
      σ.schema = S →
      (∀ j ∈ js, W3cJobValid S j) →
      UntaintedShadow S σ σ0 →
      (∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) →
      (∀ a b, (a, b) ∈ σ.edges → b.pred ≠ BARE) →
      (∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ x, (x, objNode ⟨dt, on⟩ r') ∈ σ.edges → x.pred = BARE) →
      (∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r') →
      (∀ j ∈ js, ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ¬ j.keyMatch dt on r') →
      ∀ s : SubjectRef,
        (subjNode s, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T σ js).edges →
        sem S T ⟨s, R, ⟨dt, on⟩⟩ = true ∨ (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges := by
  have hco := hCO _ _ _ hlk hder
  have hrne := computedRefs_ne_self hlk hder hLU2e
  intro js
  induction js with
  | nil =>
    intro σ _ _ _ _ _ _ _ _ s hs
    exact Or.inr hs
  | cons j rest ih =>
    intro σ hσS hjv hsh hRns htb hsbOps hopsS hjsOps s hs
    have hjv1 := hjv j List.mem_cons_self
    have hfold : reconcileJobsLR S T σ (j :: rest)
        = reconcileJobsLR S T (j.applyLoggedR S T σ) rest := by
      unfold reconcileJobsLR
      rw [List.foldl_cons]
    rw [hfold] at hs
    have hjvs : ∀ j' ∈ [j], W3cJobValid S j' := by
      intro j' hj'
      rw [List.mem_singleton.mp hj']
      exact hjv1
    -- step transports (the singleton batch IS the one logged pass)
    have hσS' : (j.applyLoggedR S T σ).schema = S := by
      rw [W3cJob.applyLoggedR_schema, hσS]
    have hsh' : UntaintedShadow S (j.applyLoggedR S T σ) σ0 :=
      untaintedShadow_applyLoggedR hsh (reachedByRules_of_admitted h0) hSV hNK hRootB hjv1
    have hRns' : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ (j.applyLoggedR S T σ).edges :=
      reconcileJobsLR_Rnode_not_source (jobs := [j]) hRne hjvs hRns
    have htb' : ∀ a b, (a, b) ∈ (j.applyLoggedR S T σ).edges → b.pred ≠ BARE :=
      reconcileJobsLR_target_ne_bare (jobs := [j]) hjvs htb
    have hsbOps' : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ x, (x, objNode ⟨dt, on⟩ r') ∈ (j.applyLoggedR S T σ).edges → x.pred = BARE :=
      fun r' hr' hd' =>
        reconcileJobsLR_source_bare (jobs := [j]) hjvs (hsbOps r' hr' hd')
    have hopsS' : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        SettledKey S T (j.applyLoggedR S T σ) dt on r' ∧
        CompleteKey S T (j.applyLoggedR S T σ) dt on r' := by
      intro r' hr' hd'
      obtain ⟨hset, hcomp⟩ := hopsS r' hr' hd'
      have hnot : ∀ j' ∈ [j], ¬ j'.keyMatch dt on r' := by
        intro j' hj'
        rw [List.mem_singleton.mp hj']
        exact hjsOps j List.mem_cons_self r' hr' hd'
      exact ⟨settledKey_jobsLR_untargeted (jobs := [j]) hjvs hnot hon hset,
        completeKey_jobsLR_untargeted (jobs := [j]) hjvs hnot hon hcomp⟩
    rcases ih (j.applyLoggedR S T σ) hσS'
        (fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj')) hsh' hRns' htb' hsbOps'
        hopsS' (fun j' hj' => hjsOps j' (List.mem_cons_of_mem _ hj')) s hs
      with hsem | hmem
    · exact Or.inl hsem
    · by_cases hkm : j.keyMatch dt on R
      · -- the pass targets the key: the routed char at pass start + the bridge
        obtain ⟨jdt, jon, jR, je, jc, jn, ju⟩ := j
        obtain ⟨hRneJ, hcb, hcS, hnegS, huP, huS, hderJ, hlke, honj⟩ := hjv1
        obtain ⟨h1, h2, h3⟩ := hkm
        have h1' : dt = jdt := h1.symm
        have h2' : on = jon := h2.symm
        have h3' : R = jR := h3.symm
        subst h1'; subst h2'; subst h3'
        simp only at hlke hcb hcS
        have hje : e = je := Option.some.inj (hlk.symm.trans hlke)
        subst hje
        have happlyedges : ((⟨dt, on, R, e, jc, jn, ju⟩ : W3cJob).applyLoggedR S T σ).edges
            = (σ.reconcileStarsKeyDR T dt on R e (wildcardShapes S) jc jn ju).edges := by
          unfold W3cJob.applyLoggedR
          rw [pushDelta_edges]
          rfl
        rw [happlyedges] at hmem
        have hchar := reconcileStarsKeyDR_edge_char (S := S) T dt on R e (wildcardShapes S)
          jc jn ju hσS hRne hon hder hco hrne hcb hRns hsh.closed s
        rcases hchar.mp hmem with ⟨hcands, hguard⟩ | ⟨_, hold⟩
        · rw [Bool.and_eq_true] at hguard
          have hchk := hguard.1
          have hsstar : s.name ≠ STAR := hcS s hcands
          have hopsB : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
              SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' ∧
              (∀ u, NReaches σ.edges u (objNode ⟨dt, on⟩ r') →
                (u, objNode ⟨dt, on⟩ r') ∈ σ.edges) := by
            intro r' hr' hd'
            obtain ⟨hset, hcomp⟩ := hopsS r' hr' hd'
            refine ⟨hset, hcomp, ?_⟩
            intro u hu
            refine nreaches_collapse_of_source_notarget ?_ hu
            intro x hxv y hxy
            exact htb y x hxy (hsbOps r' hr' hd' x hxv)
          rw [checkFnR_eq_sem_settled hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat
            hterm hCO hWSbare h0 hsh hσS hlk hder hco hLU2e hopsB
            (fun hx => absurd hx hsstar) hon] at hchk
          exact Or.inl hchk
        · exact Or.inr hold
      · obtain ⟨_, hedges⟩ := applyLoggedR_other_key_fixed hjv1 hon hkm
        exact Or.inr ((hedges (subjNode s)).mp hmem)

/-! ## Batch-level targeted re-settlement

The routed mirror of `settledComplete_cascade_targeted`, stated at the BATCH level
(one `reconcileJobsLR` round, structural facts as explicit hypotheses) so the
two-round leg can instantiate it per round: round 1 with coverage baseline σ,
round 2 with coverage baseline MID. The key's derived operand keys must be
settled+complete at the batch start and untargeted THROUGHOUT the batch (round 1:
the shape-analysis derives it; round 2: the stratum fence). -/

theorem settledComplete_jobsLR_targeted {S : Schema} {T : Store} {σ σ0 : GraphState}
    {jobs : List W3cJob}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsh : UntaintedShadow S σ σ0)
    (hσS : σ.schema = S)
    (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (hcovg : ∀ j ∈ jobs, W3dJobCoverage S T σ j)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hon : on ≠ STAR)
    (hLU2e : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (htb : ∀ a b, (a, b) ∈ σ.edges → b.pred ≠ BARE)
    (hsbOps : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ x, (x, objNode ⟨dt, on⟩ r') ∈ σ.edges → x.pred = BARE)
    (hopsS : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r')
    (hjsOps : ∀ j ∈ jobs, ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ¬ j.keyMatch dt on r')
    (htgt : ∃ j ∈ jobs, j.keyMatch dt on R) :
    SettledKey S T (reconcileJobsLR S T σ jobs) dt on R ∧
    CompleteKey S T (reconcileJobsLR S T σ jobs) dt on R := by
  have hco := hCO _ _ _ hlk hder
  have hrne := computedRefs_ne_self hlk hder hLU2e
  -- split at the LAST targeting job
  obtain ⟨pre, j, post, hsplit, hkm, hpostn⟩ := exists_last_targeting jobs htgt
  have hjmem : j ∈ jobs := hsplit ▸ List.mem_append_right _ List.mem_cons_self
  have hjvpre : ∀ j' ∈ pre, W3cJobValid S j' :=
    fun j' hj' => hjv j' (hsplit ▸ List.mem_append_left _ hj')
  have hjvpost : ∀ j' ∈ post, W3cJobValid S j' :=
    fun j' hj' => hjv j' (hsplit ▸ List.mem_append_right _ (List.mem_cons_of_mem _ hj'))
  have hjsOpsPre : ∀ j' ∈ pre, ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ¬ j'.keyMatch dt on r' :=
    fun j' hj' => hjsOps j' (hsplit ▸ List.mem_append_left _ hj')
  obtain ⟨hcovE, hcovC, hcovN, hcovU⟩ := hcovg j hjmem
  have hjvj := hjv j hjmem
  obtain ⟨jdt, jon, jR, je, jc, jn, ju⟩ := j
  obtain ⟨hRneJ, hcb, hcS, hnegS, huP, huS, hderJ, hlke, honj⟩ := hjvj
  obtain ⟨h1, h2, h3⟩ := hkm
  have h1' : dt = jdt := h1.symm
  have h2' : on = jon := h2.symm
  have h3' : R = jR := h3.symm
  subst h1'; subst h2'; subst h3'
  simp only at hlke hcb hcS hnegS huP huS hRneJ hcovE hcovC hcovN hcovU
  have hje : e = je := Option.some.inj (hlk.symm.trans hlke)
  subst hje
  have hRne : R ≠ BARE := hRneJ
  -- the prefix state and its facts
  set σpre := reconcileJobsLR S T σ pre with hσpre_def
  have hshpre : UntaintedShadow S σpre σ0 :=
    untaintedShadow_reconcileJobsLR pre σ σ0 hsh (reachedByRules_of_admitted h0)
      hSV hNK hRootB hjvpre
  have hσpreS : σpre.schema = S := by
    rw [hσpre_def, reconcileJobsLR_schema]
    exact hσS
  have hRnspre : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σpre.edges :=
    reconcileJobsLR_Rnode_not_source hRne hjvpre hRns
  have htbpre : ∀ a b, (a, b) ∈ σpre.edges → b.pred ≠ BARE :=
    reconcileJobsLR_target_ne_bare hjvpre htb
  have hsbOpspre : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ x, (x, objNode ⟨dt, on⟩ r') ∈ σpre.edges → x.pred = BARE :=
    fun r' hr' hd' => reconcileJobsLR_source_bare hjvpre (hsbOps r' hr' hd')
  have hopsB : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      SettledKey S T σpre dt on r' ∧ CompleteKey S T σpre dt on r' ∧
      (∀ u, NReaches σpre.edges u (objNode ⟨dt, on⟩ r') →
        (u, objNode ⟨dt, on⟩ r') ∈ σpre.edges) := by
    intro r' hr' hd'
    obtain ⟨hset, hcomp⟩ := hopsS r' hr' hd'
    have hnot : ∀ j' ∈ pre, ¬ j'.keyMatch dt on r' :=
      fun j' hj' => hjsOpsPre j' hj' r' hr' hd'
    refine ⟨settledKey_jobsLR_untargeted hjvpre hnot hon hset,
      completeKey_jobsLR_untargeted hjvpre hnot hon hcomp, ?_⟩
    intro u hu
    refine nreaches_collapse_of_source_notarget ?_ hu
    intro x hxv y hxy
    exact htbpre y x hxy (hsbOpspre r' hr' hd' x hxv)
  -- the mid-batch STRATUM-STAGED bridge at the last targeting job's pass start
  have hbridge : ∀ (x : SubjectRef), (x.name = STAR → x.predicate = BARE) →
      σpre.checkFnR T x dt on R e = sem S T ⟨x, R, ⟨dt, on⟩⟩ :=
    fun x hx => checkFnR_eq_sem_settled hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat
      hterm hCO hWSbare h0 hshpre hσpreS hlk hder hco hLU2e hopsB hx hon
  have hcovsem : ∀ sh ∈ wildcardShapes S,
      σpre.coveredFnR T dt on R e sh = sem S T ⟨starSubj sh, R, ⟨dt, on⟩⟩ :=
    fun sh hws => hbridge (starSubj sh) (fun _ => hWSbare sh hws)
  -- the batch factors through the last targeting job
  have hfold : reconcileJobsLR S T σ jobs
      = reconcileJobsLR S T
          ((⟨dt, on, R, e, jc, jn, ju⟩ : W3cJob).applyLoggedR S T σpre) post := by
    rw [hsplit, hσpre_def]
    unfold reconcileJobsLR
    rw [List.foldl_append, List.foldl_cons]
  obtain ⟨hpostres, hpostedges⟩ :=
    reconcileJobsLR_other_key_fixed post
      ((⟨dt, on, R, e, jc, jn, ju⟩ : W3cJob).applyLoggedR S T σpre) hon hjvpost hpostn
  -- the final row is the last targeting pass's ROUTED wholesale recompute at σpre
  have hrowfinal : (reconcileJobsLR S T σ jobs).residue (objNode ⟨dt, on⟩ R) R
      = some ⟨(wildcardShapes S).filter (fun sh => σpre.coveredFnR T dt on R e sh),
              jn.filter (fun c =>
                ((wildcardShapes S).filter
                  (fun sh => σpre.coveredFnR T dt on R e sh)).contains c.shape
                    && !(σpre.checkFnR T c dt on R e)),
              ju.filter (fun c =>
                !(((wildcardShapes S).filter
                  (fun sh => σpre.coveredFnR T dt on R e sh)).contains c.shape)
                    && σpre.checkFnR T c dt on R e)⟩ := by
    rw [hfold, hpostres]
    have happlyres : ((⟨dt, on, R, e, jc, jn, ju⟩ : W3cJob).applyLoggedR S T σpre).residue
        = ((⟨dt, on, R, e, jc, jn, ju⟩ : W3cJob).applyDR S T σpre).residue := by
      unfold W3cJob.applyLoggedR
      rw [pushDelta_residue]
    rw [happlyres]
    show (σpre.reconcileStarsKeyDR T dt on R e (wildcardShapes S) jc jn ju).residue
      (objNode ⟨dt, on⟩ R) R = _
    unfold GraphState.reconcileStarsKeyDR
    rw [reconcileKeyDR_residue, reconcileResidueKeyR_residue_self]
  -- the final edge membership at the key, characterised at σpre
  have happlyedges : ((⟨dt, on, R, e, jc, jn, ju⟩ : W3cJob).applyLoggedR S T σpre).edges
      = (σpre.reconcileStarsKeyDR T dt on R e (wildcardShapes S) jc jn ju).edges := by
    unfold W3cJob.applyLoggedR
    rw [pushDelta_edges]
    rfl
  have hchar := reconcileStarsKeyDR_edge_char (S := S) T dt on R e (wildcardShapes S)
    jc jn ju hσpreS hRne hon hder hco hrne hcb hRnspre hshpre.closed
  have hedgefinal : ∀ s : SubjectRef,
      ((subjNode s, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsLR S T σ jobs).edges
        ↔ (subjNode s, objNode ⟨dt, on⟩ R)
            ∈ (σpre.reconcileStarsKeyDR T dt on R e (wildcardShapes S) jc jn ju).edges) := by
    intro s
    rw [hfold, ← happlyedges]
    exact hpostedges (subjNode s)
  -- the stars row reads at `sem` level
  have hstars_iff : ∀ sh : Shape,
      ((wildcardShapes S).filter (fun sh => σpre.coveredFnR T dt on R e sh)).contains sh
          = true
        ↔ (sh ∈ wildcardShapes S ∧ sem S T ⟨starSubj sh, R, ⟨dt, on⟩⟩ = true) := by
    intro sh
    rw [List.contains_eq_mem]
    constructor
    · intro hc
      obtain ⟨hws, hcov⟩ := List.mem_filter.mp (of_decide_eq_true hc)
      refine ⟨hws, ?_⟩
      rw [← hcovsem sh hws]
      exact hcov
    · rintro ⟨hws, hsm⟩
      refine decide_eq_true (List.mem_filter.mpr ⟨hws, ?_⟩)
      rw [hcovsem sh hws]
      exact hsm
  constructor
  · -- === the settled half ===
    constructor
    · -- row members carry their `sem` verdicts
      intro res hres
      rw [hrowfinal] at hres
      obtain rfl := Option.some.inj hres
      refine ⟨hstars_iff, ?_, ?_⟩
      · intro n hn
        obtain ⟨hnmem, hg⟩ := List.mem_filter.mp hn
        rw [Bool.and_eq_true] at hg
        have hnstar : n.name ≠ STAR := hnegS n hnmem
        refine ⟨hnstar, ?_⟩
        have hchkF : σpre.checkFnR T n dt on R e = false := by
          have := hg.2
          rw [Bool.not_eq_eq_eq_not, Bool.not_true] at this
          exact this
        rw [← hbridge n (fun hx => absurd hx hnstar)]
        exact hchkF
      · intro n hn
        obtain ⟨hnmem, hg⟩ := List.mem_filter.mp hn
        rw [Bool.and_eq_true] at hg
        refine ⟨huP n hnmem, huS n hnmem, ?_⟩
        rw [← hbridge n (fun hx => absurd hx (huS n hnmem))]
        exact hg.2
    · -- every derived edge witnesses a `sem`-true subject
      intro s _ _ hedge
      rw [hedgefinal s] at hedge
      rcases (hchar s).mp hedge with ⟨hcands, hguard⟩ | ⟨hncand, holdpre⟩
      · rw [Bool.and_eq_true] at hguard
        have hchk := hguard.1
        rw [hbridge s (fun hx => absurd hx (hcS s hcands))] at hchk
        exact hchk
      · rcases reconcileJobsLR_key_edge_sem hWF hTT hNK hR hSV hBS hTS hRootB hMatch
            hStrat hterm hCO hWSbare h0 hlk hder hRne hon hLU2e pre σ hσS hjvpre hsh
            hRns htb hsbOps hopsS hjsOpsPre s holdpre
          with hsem | hpreleg
        · exact hsem
        · exact absurd (hcovE s hpreleg) hncand
  · -- === the completeness half ===
    refine ⟨?_, ?_, ?_, ?_⟩
    · -- row existence: the targeting pass always writes the row
      intro _ _ _
      rw [hrowfinal]
      rfl
    · -- an uncovered `sem`-true bare subject's edge is materialised
      intro s hb hstar hsm hnc
      rw [hedgefinal s]
      have hcmem : s ∈ jc := hcovC s hb hstar hsm hnc
      have hncov : ((wildcardShapes S).filter
          (fun sh => σpre.coveredFnR T dt on R e sh)).contains s.shape = false := by
        by_contra hc
        rw [Bool.not_eq_false] at hc
        exact hnc ((hstars_iff s.shape).mp hc)
      refine (hchar s).mpr (Or.inl ⟨hcmem, ?_⟩)
      rw [Bool.and_eq_true, hncov]
      constructor
      · rw [hbridge s (fun hx => absurd hx hstar)]
        exact hsm
      · rfl
    · -- a `sem`-true userset is in `upos`
      intro s hu hstar hsm
      refine ⟨_, hrowfinal, ?_⟩
      refine List.mem_filter.mpr ⟨hcovU s hu hstar hsm, ?_⟩
      have hncov : ((wildcardShapes S).filter
          (fun sh => σpre.coveredFnR T dt on R e sh)).contains s.shape = false := by
        by_contra hc
        rw [Bool.not_eq_false] at hc
        obtain ⟨hws, _⟩ := (hstars_iff s.shape).mp hc
        exact hu (hWSbare s.shape hws)
      rw [Bool.and_eq_true, hncov]
      constructor
      · rfl
      · rw [hbridge s (fun hx => absurd hx hstar)]
        exact hsm
    · -- a covered-but-`sem`-false subject is in `neg`
      intro s hstar hws hsemStar hsemF
      refine ⟨_, hrowfinal, ?_⟩
      refine List.mem_filter.mpr ⟨hcovN s hstar hws hsemStar hsemF, ?_⟩
      rw [Bool.and_eq_true]
      constructor
      · exact (hstars_iff s.shape).mpr ⟨hws, hsemStar⟩
      · rw [Bool.not_eq_eq_eq_not, Bool.not_true]
        rw [hbridge s (fun hx => absurd hx hstar)]
        exact hsemF

/-! ## The two-round targeted re-settlement

The leg-level assembly (the 12e design-note case analysis, reorganized around
"targeted by round 2 or not"):

* **Case A** (some round-2 job targets the key): the key's last targeting job is in
  round 2 — settle over `jobs2` from the MID state (coverage baseline MID, exactly
  `hcovg2`). Its stratum-1 operand keys are settled AT MID: an operand targeted in
  round 1 is re-settled by the batch lemma at σ (its own operands untainted, hops
  vacuous); an untargeted one was clean at leg start (`hcover1` would otherwise
  target it) hence settled at σ (`hopsBase`) and transported. Round 2 never touches
  a stratum-1 key (the stratum fence via `round2_key_reads_derived` + `hLU2`).
* **Case B** (no round-2 job targets the key): the last targeting job is in round 1.
  No round-1 job targets any derived operand key either — such a pass's emission
  would put the key in round-2 scope (`round1_emission_dirties`) and `hcover2`
  would then produce a round-2 targeting job, contradicting Case B. So the operands
  are settled at σ throughout, the batch lemma settles the key at MID, and round 2
  leaves it untouched. -/

theorem settledComplete_cascade2_targeted {σ : GraphState} {S : Schema} {T : Store}
    {jobs1 jobs2 : List W3cJob}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d2 σ S T)
    (hjv1 : ∀ j ∈ jobs1, W3cJobValid S j) (hjv2 : ∀ j ∈ jobs2, W3cJobValid S j)
    (hcover1 : ∀ k ∈ cascadeKeysAbove S σ σ.watermark, ∃ j ∈ jobs1, j.key = k)
    (hcover2 : ∀ k ∈ cascadeKeysAbove S (reconcileJobsLR S T σ jobs1)
        (σ.frontierMax σ.watermark), ∃ j ∈ jobs2, j.key = k)
    (hscope2 : ∀ j ∈ jobs2, j.key ∈ cascadeKeysAbove S (reconcileJobsLR S T σ jobs1)
        (σ.frontierMax σ.watermark))
    (hcovg1 : ∀ j ∈ jobs1, W3dJobCoverage S T σ j)
    (hcovg2 : ∀ j ∈ jobs2, W3dJobCoverage S T (reconcileJobsLR S T σ jobs1) j)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hon : on ≠ STAR)
    (hopsBase : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      (dt, r', on) ∈ cascadeKeys S σ ∨
      (SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r'))
    (htgt : ∃ j ∈ jobs1 ++ jobs2, j.keyMatch dt on R) :
    SettledKey S T (runCascade2 S T σ jobs1 jobs2) dt on R ∧
    CompleteKey S T (runCascade2 S T σ jobs1 jobs2) dt on R := by
  have hLU2e := hLU2 dt R e hlk hder
  have hRne : R ≠ BARE := by
    obtain ⟨j, hj, hkm⟩ := htgt
    rw [← hkm.2.2]
    rcases List.mem_append.mp hj with hj1 | hj2
    · exact (hjv1 j hj1).1
    · exact (hjv2 j hj2).1
  -- chain facts at the leg-start state
  obtain ⟨σ0, h0, hsh⟩ := reachedByW3d2_shadow h hNK hRootB hSV hterm
  have hσS : σ.schema = S := reachedByW3d2_schema h
  have htb : ∀ a b, (a, b) ∈ σ.edges → b.pred ≠ BARE :=
    reachedByW3d2_edge_target_ne_bare h hWF hSV
  have hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges :=
    reachedByW3d2_Rnode_not_source hterm hRne hder h
  have hsbOps : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ x, (x, objNode ⟨dt, on⟩ r') ∈ σ.edges → x.pred = BARE := by
    intro r' hr' hd' x hx
    obtain ⟨e', hlk'⟩ := isDerived_declared hd'
    have hroot' : RootBoolean e' :=
      hRootB ⟨(dt, r'), e'⟩ (mem_defs_of_lookup hlk') hd'
    exact reachedByW3d2_Rnode_source_bare h hNK hlk' hroot' hSV x hx
  -- the accept form (the reject branch is dead at two strata)
  have hacc := runCascade2_no_abort hterm hLU2 hjv1 hjv2 hscope2 h
  set mid := reconcileJobsLR S T σ jobs1 with hmid_def
  -- the stratum fence: round 2 never targets a derived operand key (its def is
  -- all-untainted, but a round-2 scope key must read a derived operand)
  have hfence : ∀ j2 ∈ jobs2, ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ¬ j2.keyMatch dt on r' := by
    intro j2 hj2 r' hr' hd' hkm
    obtain ⟨e', hlk'⟩ := isDerived_declared hd'
    have hkey2 : j2.key = (dt, r', on) := by
      obtain ⟨ha, hb, hc⟩ := hkm
      show (j2.dt, j2.R, j2.on) = (dt, r', on)
      rw [ha, hb, hc]
    have hjk := hscope2 j2 hj2
    rw [hkey2] at hjk
    obtain ⟨r'', hr''mem, hd''⟩ := round2_key_reads_derived hterm hjv1 h hlk' hjk
    cases (hLU2e r' hr' hd' e' hlk' r'' hr''mem).symm.trans hd''
  by_cases hA : ∃ j ∈ jobs2, j.keyMatch dt on R
  · -- ==== Case A: settle over round 2 from the MID state ====
    have hshmid : UntaintedShadow S mid σ0 :=
      untaintedShadow_reconcileJobsLR jobs1 σ σ0 hsh (reachedByRules_of_admitted h0)
        hSV hNK hRootB hjv1
    have hσmidS : mid.schema = S := by
      rw [hmid_def, reconcileJobsLR_schema]
      exact hσS
    have hRnsmid : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ mid.edges :=
      reconcileJobsLR_Rnode_not_source hRne hjv1 hRns
    have htbmid : ∀ a b, (a, b) ∈ mid.edges → b.pred ≠ BARE :=
      reconcileJobsLR_target_ne_bare hjv1 htb
    have hsbOpsmid : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ x, (x, objNode ⟨dt, on⟩ r') ∈ mid.edges → x.pred = BARE :=
      fun r' hr' hd' => reconcileJobsLR_source_bare hjv1 (hsbOps r' hr' hd')
    -- every derived operand key is settled+complete AT MID
    have hopsMid : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        SettledKey S T mid dt on r' ∧ CompleteKey S T mid dt on r' := by
      intro r' hr' hd'
      obtain ⟨e', hlk'⟩ := isDerived_declared hd'
      have hLUe' : ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false :=
        hLU2e r' hr' hd' e' hlk'
      by_cases htgt1 : ∃ j1 ∈ jobs1, j1.keyMatch dt on r'
      · -- targeted in round 1 ⇒ re-settled by the batch lemma at σ (hops vacuous)
        obtain ⟨j1, hj1, hkm1⟩ := htgt1
        have hRne' : r' ≠ BARE := by
          rw [← hkm1.2.2]
          exact (hjv1 j1 hj1).1
        have hRns' : ∀ y, (objNode ⟨dt, on⟩ r', y) ∉ σ.edges :=
          reachedByW3d2_Rnode_not_source hterm hRne' hd' h
        have hLU2e' : ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = true →
            ∀ e'', S.lookup (dt, r'') = some e'' →
              ∀ r''' ∈ computedRefs e'', isDerived S (dt, r''') = false := by
          intro r'' hr'' hd'' _ _ _ _
          cases (hLUe' r'' hr'').symm.trans hd''
        refine settledComplete_jobsLR_targeted hWF hTT hNK hR hSV hBS hTS hRootB hMatch
          hStrat hterm hCO hWSbare h0 hsh hσS hjv1 hcovg1 hlk' hd' hon hLU2e' hRns' htb
          ?_ ?_ ?_ ⟨j1, hj1, hkm1⟩
        · intro r'' hr'' hd''
          cases (hLUe' r'' hr'').symm.trans hd''
        · intro r'' hr'' hd''
          cases (hLUe' r'' hr'').symm.trans hd''
        · intro j' _ r'' hr'' hd''
          cases (hLUe' r'' hr'').symm.trans hd''
      · -- untargeted in round 1 ⇒ clean at leg start, settled at σ, transported
        rcases hopsBase r' hr' hd' with hdirty | ⟨hset, hcomp⟩
        · exfalso
          obtain ⟨j1, hj1, hkey1⟩ := hcover1 _ hdirty
          have h1 : j1.dt = dt := congrArg Prod.fst hkey1
          have h23 : (j1.R, j1.on) = (r', on) := congrArg Prod.snd hkey1
          have h2 : j1.R = r' := congrArg Prod.fst h23
          have h3 : j1.on = on := congrArg Prod.snd h23
          exact htgt1 ⟨j1, hj1, h1, h3, h2⟩
        · have hnot1 : ∀ j' ∈ jobs1, ¬ j'.keyMatch dt on r' :=
            fun j' hj' hkm' => htgt1 ⟨j', hj', hkm'⟩
          exact ⟨settledKey_jobsLR_untargeted hjv1 hnot1 hon hset,
            completeKey_jobsLR_untargeted hjv1 hnot1 hon hcomp⟩
    have hsettled := settledComplete_jobsLR_targeted hWF hTT hNK hR hSV hBS hTS hRootB
      hMatch hStrat hterm hCO hWSbare h0 hshmid hσmidS hjv2 hcovg2 hlk hder hon hLU2e
      hRnsmid htbmid hsbOpsmid hopsMid hfence hA
    rw [hacc]
    exact ⟨settledKey_congr rfl rfl hsettled.1, completeKey_congr rfl rfl hsettled.2⟩
  · -- ==== Case B: the last targeting job is in round 1; round 2 is inert here ====
    have htgtB : ∃ j ∈ jobs1, j.keyMatch dt on R := by
      obtain ⟨j, hj, hkm⟩ := htgt
      rcases List.mem_append.mp hj with hj1 | hj2
      · exact ⟨j, hj1, hkm⟩
      · exact absurd ⟨j, hj2, hkm⟩ hA
    -- no round-1 job targets a derived operand key: its emission would re-dirty
    -- the key for round 2, and `hcover2` would produce a round-2 targeting job
    have hopsNoTgt : ∀ j1 ∈ jobs1, ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ¬ j1.keyMatch dt on r' := by
      intro j1 hj1 r' hr' hd' hkm1
      have hkey1 : j1.key = (dt, r', on) := by
        obtain ⟨ha, hb, hc⟩ := hkm1
        show (j1.dt, j1.R, j1.on) = (dt, r', on)
        rw [ha, hb, hc]
      have hscope := round1_emission_dirties (σ := σ) (T := T) hj1 hlk hder hr' hon hkey1
      obtain ⟨j2, hj2, hkey2⟩ := hcover2 _ hscope
      have h1 : j2.dt = dt := congrArg Prod.fst hkey2
      have h23 : (j2.R, j2.on) = (R, on) := congrArg Prod.snd hkey2
      have h2 : j2.R = R := congrArg Prod.fst h23
      have h3 : j2.on = on := congrArg Prod.snd h23
      exact hA ⟨j2, hj2, h1, h3, h2⟩
    -- hence every derived operand key is settled at the leg start
    have hopsS : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        SettledKey S T σ dt on r' ∧ CompleteKey S T σ dt on r' := by
      intro r' hr' hd'
      rcases hopsBase r' hr' hd' with hdirty | hsc
      · exfalso
        obtain ⟨j1, hj1, hkey1⟩ := hcover1 _ hdirty
        have h1 : j1.dt = dt := congrArg Prod.fst hkey1
        have h23 : (j1.R, j1.on) = (r', on) := congrArg Prod.snd hkey1
        have h2 : j1.R = r' := congrArg Prod.fst h23
        have h3 : j1.on = on := congrArg Prod.snd h23
        exact hopsNoTgt j1 hj1 r' hr' hd' ⟨h1, h3, h2⟩
      · exact hsc
    have hsettled1 := settledComplete_jobsLR_targeted hWF hTT hNK hR hSV hBS hTS hRootB
      hMatch hStrat hterm hCO hWSbare h0 hsh hσS hjv1 hcovg1 hlk hder hon hLU2e hRns
      htb hsbOps hopsS hopsNoTgt htgtB
    have hnot2 : ∀ j ∈ jobs2, ¬ j.keyMatch dt on R :=
      fun j hj hkm => hA ⟨j, hj, hkm⟩
    rw [hacc]
    exact ⟨settledKey_congr rfl rfl
        (settledKey_jobsLR_untargeted hjv2 hnot2 hon hsettled1.1),
      completeKey_congr rfl rfl
        (completeKey_jobsLR_untargeted hjv2 hnot2 hon hsettled1.2)⟩

end Zanzibar
