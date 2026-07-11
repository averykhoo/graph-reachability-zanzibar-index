import ZanzibarProofs.GraphIndex.ReconcileUpos

/-!
# The W3b closure — the shadow projection and `upos` soundness (ROADMAP W3b)

`ReconcileUpos.lean` landed the userset write model (`reconcileUposKey`), its
membership characterization, and the W3b read collapse. This file builds the W3b
**write-closure** `ReachedByW3b` — an admitted rule-routed base plus interleaved
bare-edge (`reconcileKey`) and userset-`upos` (`reconcileUposKey`) reconcile passes —
and its correspondence spine:

* **The shadow projection.** A upos pass never touches the edge/node structure, and
  the bare-edge pass never reads residues. So every W3b state has a **W3a-admitted
  shadow**: replay the same legs *minus* the upos passes and the core state (schema,
  edges, nodes, outbox, watermark) is identical (`reachedByW3b_shadow`). Every
  edge/reachability fact proved for the W3a closure — reach collapse, R-node
  terminality, edge soundness, `checkFn_eq_sem` — transfers through the shadow with
  zero new induction.
* **T2a at W3b.** `reachedByW3b_inv`: the full `Inv` (now with **contentful I6
  residue hygiene** — `uposEdgeFree` holds because a upos member is userset-shaped
  while every path onto a `RootBoolean` R-node is a single bare-sourced reconcile
  edge), `ResidueUposOnly`, and quiescence.
* **`upos` soundness.** A upos entry at a derived key witnesses `sem = true`: it was
  written by some upos pass whose (fold-constant) guard held at the pass start, and
  the pass-start state's `checkFn` equals `sem` (`checkFn_eq_sem_w3b`).
-/

namespace Zanzibar

/-! ## Core-state agreement and its congruences -/

/-- **`CoreEq σ' σ`** — the two states agree on everything except the residue table.
    The shadow relation: `σ'` is the residue-free (W3a) shadow of the W3b state `σ`. -/
structure CoreEq (σ' σ : GraphState) : Prop where
  schema : σ'.schema = σ.schema
  edges : σ'.edges = σ.edges
  nodes : σ'.nodes = σ.nodes
  outbox : σ'.outbox = σ.outbox
  watermark : σ'.watermark = σ.watermark

/-- `CoreEq` is reflexive. -/
theorem CoreEq.refl (σ : GraphState) : CoreEq σ σ := ⟨rfl, rfl, rfl, rfl, rfl⟩

/-- The node-list equation of the write (companion to `writeDirect_edges`). -/
theorem writeDirect_nodes (σ : GraphState) (t : Tuple) :
    (σ.writeDirect t).nodes =
      (if σ.admitEdge (subjNode t.subject) (objNode t.object t.relation)
       then objNode t.object t.relation :: subjNode t.subject :: σ.nodes
       else σ.nodes) := by
  unfold GraphState.writeDirect
  dsimp only
  split <;> simp only [addEdge_nodes, addNode_nodes]

/-- `writeDirect` preserves core agreement: the admission guard reads only the core
    (`reach` congruence), and both branches mutate only core fields. -/
theorem writeDirect_coreEq {σ' σ : GraphState} (h : CoreEq σ' σ) (t : Tuple) :
    CoreEq (σ'.writeDirect t) (σ.writeDirect t) := by
  have hadm : σ'.admitEdge (subjNode t.subject) (objNode t.object t.relation)
      = σ.admitEdge (subjNode t.subject) (objNode t.object t.relation) := by
    unfold GraphState.admitEdge
    rw [reach_congr h.edges h.nodes]
  refine ⟨?_, ?_, ?_, ?_, ?_⟩
  · rw [writeDirect_schema, writeDirect_schema]; exact h.schema
  · rw [writeDirect_edges, writeDirect_edges, hadm, h.edges]
  · rw [writeDirect_nodes, writeDirect_nodes, hadm, h.nodes]
  · rw [writeDirect_outbox, writeDirect_outbox]; exact h.outbox
  · rw [writeDirect_watermark, writeDirect_watermark]; exact h.watermark

/-- The bare-edge reconcile pass preserves core agreement: its guard (`checkFn`) and
    its writes (`writeDirect`) read/mutate only the core. -/
theorem reconcileKey_coreEq {T : Store} {dt on R : String} {e : Expr} :
    ∀ (cands : List SubjectRef) {σ' σ : GraphState}, CoreEq σ' σ →
      CoreEq (σ'.reconcileKey T dt on R e cands) (σ.reconcileKey T dt on R e cands) := by
  intro cands
  induction cands with
  | nil => intro σ' σ h; exact h
  | cons c rest ih =>
    intro σ' σ h
    have hfold : ∀ (τ : GraphState), τ.reconcileKey T dt on R e (c :: rest)
        = (if τ.checkFn T c dt on R e then τ.writeDirect ⟨c, R, ⟨dt, on⟩⟩
           else τ).reconcileKey T dt on R e rest := by
      intro τ; unfold GraphState.reconcileKey; rw [List.foldl_cons]
    rw [hfold σ', hfold σ]
    have hg : σ'.checkFn T c dt on R e = σ.checkFn T c dt on R e :=
      checkFn_congr h.edges h.nodes T c dt on R e
    rw [hg]
    by_cases hc : σ.checkFn T c dt on R e = true
    · rw [if_pos hc, if_pos hc]
      exact ih (writeDirect_coreEq h _)
    · rw [if_neg hc, if_neg hc]
      exact ih h

/-- A upos pass leaves the core untouched, so the *unchanged* shadow stays
    core-equal to it. -/
theorem reconcileUposKey_coreEq {σ' σ : GraphState} (h : CoreEq σ' σ)
    (T : Store) (dt on R : String) (e : Expr) (cands : List SubjectRef) :
    CoreEq σ' (σ.reconcileUposKey T dt on R e cands) :=
  ⟨h.schema.trans (reconcileUposKey_schema T dt on R e cands σ).symm,
   h.edges.trans (reconcileUposKey_edges T dt on R e cands σ).symm,
   h.nodes.trans (reconcileUposKey_nodes T dt on R e cands σ).symm,
   h.outbox.trans (reconcileUposKey_outbox T dt on R e cands σ).symm,
   h.watermark.trans (reconcileUposKey_watermark T dt on R e cands σ).symm⟩

/-! ## The W3b write-closure -/

/-- **`ReachedByW3b σ S T`** — an admitted rule-routed base plus interleaved
    bare-edge reconcile passes (`reconcile`, exactly W3a's leg) and userset-`upos`
    reconcile passes (`reconcileU`). The `reconcileU` side conditions are faithful to
    the processor's userset branch (`reconcile_subject`, `processor.py:345-357`;
    `reconcile` step 2c, `:431-441`): candidates are **userset-shaped** concrete
    subjects (`hcands : predicate ≠ BARE` — the branch guard `sp != '...'`;
    `hcStar : name ≠ STAR` — candidates are concrete nodes, and wildcard usersets
    over derived relations are rejected at compile, decision-15), the key is a
    declared derived relation with its compiled def, and the object is concrete. -/
inductive ReachedByW3b : GraphState → Schema → Store → Prop where
  | base {σ : GraphState} {S : Schema} {T : Store} :
      ReachedByRulesAdmitted σ S T → ReachedByW3b σ S T
  | reconcile {σ : GraphState} {S : Schema} {T : Store}
      (dt on R : String) (e : Expr) (cands : List SubjectRef) (hRne : R ≠ BARE)
      (hcands : ∀ c ∈ cands, c.predicate = BARE)
      (hder : isDerived S (dt, R) = true) (hlke : S.lookup (dt, R) = some e)
      (hcStar : ∀ c ∈ cands, c.name ≠ STAR) (honStar : on ≠ STAR) :
      ReachedByW3b σ S T → ReachedByW3b (σ.reconcileKey T dt on R e cands) S T
  | reconcileU {σ : GraphState} {S : Schema} {T : Store}
      (dt on R : String) (e : Expr) (cands : List SubjectRef) (hRne : R ≠ BARE)
      (hcands : ∀ c ∈ cands, c.predicate ≠ BARE)
      (hder : isDerived S (dt, R) = true) (hlke : S.lookup (dt, R) = some e)
      (hcStar : ∀ c ∈ cands, c.name ≠ STAR) (honStar : on ≠ STAR) :
      ReachedByW3b σ S T → ReachedByW3b (σ.reconcileUposKey T dt on R e cands) S T

/-- Every W3a-admitted state is a W3b state (leg-for-leg re-tagging). -/
theorem reachedByW3aAdmitted_toW3b {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3aAdmitted σ S T) : ReachedByW3b σ S T := by
  induction h with
  | base hr => exact ReachedByW3b.base hr
  | reconcile dt on R e cands hRne hcands hder hlke hcStar honStar _ ih =>
    exact ReachedByW3b.reconcile dt on R e cands hRne hcands hder hlke hcStar honStar ih

/-- **The shadow projection.** Every W3b state has a W3a-admitted shadow with an
    identical core: replay the same legs minus the upos passes. The bare legs stay
    in lockstep (`reconcileKey_coreEq` — guards agree because `checkFn` reads only
    the core), and a upos leg moves only the W3b side (`reconcileUposKey_coreEq`).
    All W3a edge/reach facts transfer to W3b states through this. -/
theorem reachedByW3b_shadow {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3b σ S T) :
    ∃ σ', ReachedByW3aAdmitted σ' S T ∧ CoreEq σ' σ := by
  induction h with
  | base hr => exact ⟨_, ReachedByW3aAdmitted.base hr, CoreEq.refl _⟩
  | reconcile dt on R e cands hRne hcands hder hlke hcStar honStar _ ih =>
    obtain ⟨σ', hσ', hcore⟩ := ih
    exact ⟨_,
      ReachedByW3aAdmitted.reconcile dt on R e cands hRne hcands hder hlke hcStar honStar hσ',
      reconcileKey_coreEq cands hcore⟩
  | reconcileU dt on R e cands _hRne _hcands _hder _hlke _hcStar _honStar _ ih =>
    obtain ⟨σ', hσ', hcore⟩ := ih
    exact ⟨σ', hσ', reconcileUposKey_coreEq hcore _ dt on R e cands⟩

/-! ## Residue facts along the W3b closure -/

/-- Reading `uposAt` through a known residue row. -/
theorem uposAt_of_residue {σf : GraphState} {k : NodeKey} {r : String} {res : Residue}
    (h : σf.residue k r = some res) : σf.uposAt k r = res.upos := by
  unfold GraphState.uposAt
  rw [h]
  rfl

/-- A `uposAt` member comes from an actual residue row. -/
theorem residue_of_uposAt_mem {σf : GraphState} {k : NodeKey} {r : String} {x : SubjectRef}
    (h : x ∈ σf.uposAt k r) : ∃ res, σf.residue k r = some res ∧ x ∈ res.upos := by
  unfold GraphState.uposAt at h
  cases hres : σf.residue k r with
  | none => rw [hres] at h; exact absurd h List.not_mem_nil
  | some res => rw [hres] at h; exact ⟨res, rfl, h⟩

/-- The W3b closure keeps the residue table `upos`-only — the read collapse
    (`probeDerived_uposOnly`) applies to every W3b state. -/
theorem reachedByW3b_residueUposOnly {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3b σ S T) : ResidueUposOnly σ := by
  induction h with
  | base hr =>
    exact residueUposOnly_of_empty
      (reachedByRules_inv (reachedByRules_of_admitted hr)).2.1
  | reconcile dt on R e cands _ _ _ _ _ _ _ ih =>
    exact residueUposOnly_reconcileKey _ dt on R e cands ih
  | reconcileU dt on R e cands _ _ _ _ _ _ _ ih =>
    exact residueUposOnly_reconcileUposKey _ dt on R e cands ih

/-- **Residue provenance.** Every persisted residue row of a W3b state sits at a
    derived R-node key `(objNode ⟨dt,on⟩ r, r)` (concrete object, `r ≠ BARE`), and
    every `upos` member is a concrete userset (`predicate ≠ BARE`, `name ≠ STAR`) —
    the facts I6's `uposEdgeFree` needs. By induction: the base persists nothing, a
    bare pass touches nothing, and a upos leg writes only its own (side-condition-
    carrying) key with members drawn from `{candidates} ∪ {previous members}`. -/
theorem reachedByW3b_residue_provenance {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3b σ S T) :
    ∀ k r res, σ.residue k r = some res →
      (∃ dt on, k = objNode ⟨dt, on⟩ r ∧ isDerived S (dt, r) = true ∧ r ≠ BARE ∧ on ≠ STAR) ∧
      (∀ n ∈ res.upos, n.predicate ≠ BARE ∧ n.name ≠ STAR) := by
  induction h with
  | base hr =>
    intro k r res hres
    rw [(reachedByRules_inv (reachedByRules_of_admitted hr)).2.1 k r] at hres
    cases hres
  | reconcile dt on R e cands _ _ _ _ _ _ _ ih =>
    intro k r res hres
    rw [reconcileKey_residue] at hres
    exact ih k r res hres
  | reconcileU dt on R e cands hRne hcands hder _hlke hcStar honStar hprev ih =>
    intro k r res hres
    by_cases hkey : k = objNode ⟨dt, on⟩ R ∧ r = R
    · obtain ⟨rfl, rfl⟩ := hkey
      refine ⟨⟨dt, on, rfl, hder, hRne, honStar⟩, ?_⟩
      intro n hn
      -- n is in the fold's upos at its own key: a candidate or a previous member
      rcases (reconcileUposKey_upos_mem n cands _).mp
          (by rw [uposAt_of_residue hres]; exact hn) with ⟨hc, _⟩ | ⟨_, hold⟩
      · exact ⟨hcands n hc, hcStar n hc⟩
      · -- previous member: read the pre-state's residue row
        obtain ⟨res', hpres, hold'⟩ := residue_of_uposAt_mem hold
        exact (ih _ _ res' hpres).2 n hold'
    · rw [reconcileUposKey_residue_other hkey] at hres
      exact ih k r res hres

/-! ## T2a at W3b — the full invariant, with contentful I6 -/

/-- **T2a for the W3b fragment.** Every W3b state satisfies the full I-series
    invariant — including, for the first time, **contentful residue hygiene**: the
    `neg` clauses hold because `neg` is empty (`ResidueUposOnly`), `uposNegDisjoint`
    likewise, and `uposEdgeFree` holds *for real*: a `upos` member is userset-shaped
    (provenance), any path from it onto the residue's `RootBoolean` R-node collapses
    to a single edge (shadow + `reachedByW3a_reach_collapse_root`), and every such
    edge has a bare source (`reachedByW3a_Rnode_source_bare`) — contradiction. -/
theorem reachedByW3b_inv {σ : GraphState} {S : Schema} {T : Store}
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (h : ReachedByW3b σ S T) :
    Inv S σ ∧ ResidueUposOnly σ ∧ Quiescent σ := by
  obtain ⟨σ', hσ', hcore⟩ := reachedByW3b_shadow h
  have hW3a := reachedByW3aAdmitted_toW3a hσ'
  obtain ⟨hInv', _hre', hQ'⟩ := reachedByW3a_inv hW3a
  have hru := reachedByW3b_residueUposOnly h
  have hprov := reachedByW3b_residue_provenance h
  refine ⟨?_, hru, ?_⟩
  · refine ⟨hcore.schema.symm.trans hInv'.schemaEq,
      by rw [← hcore.nodes]; exact hInv'.nodeEnc,
      by rw [← hcore.edges, ← hcore.nodes]; exact hInv'.edgesClosed,
      by rw [← hcore.edges]; exact hInv'.acyclic,
      ?_, ?_, ?_, ?_⟩
    · -- negStarCovered: neg is empty
      intro k r res hres n hn
      rw [(hru k r res hres).2] at hn
      exact absurd hn (List.not_mem_nil)
    · -- negEdgeFree: neg is empty
      intro k r res hres n hn
      rw [(hru k r res hres).2] at hn
      exact absurd hn (List.not_mem_nil)
    · -- uposEdgeFree: the contentful I6 clause
      intro k r res hres n hn hreach
      obtain ⟨⟨dt, on, rfl, hder, _hRne, honStar⟩, hmemb⟩ := hprov k r res hres
      obtain ⟨e, hlk⟩ := isDerived_declared hder
      have hroot : RootBoolean e :=
        hRootB ⟨(dt, r), e⟩ (mem_defs_of_lookup hlk) hder
      -- transfer the path to the shadow and collapse it to a single edge
      have hreach' : NReaches σ'.edges (subjNode n) (objNode ⟨dt, on⟩ r) := by
        rw [hcore.edges]; exact hreach
      have hedge := reachedByW3a_reach_collapse_root hWF hSV hNK hlk hroot hW3a hreach'
      have hbare := reachedByW3a_Rnode_source_bare hSV hNK hlk hroot hW3a
        (subjNode n) hedge
      rw [subjNode_pred] at hbare
      exact (hmemb n hn).1 hbare
    · -- uposNegDisjoint: neg is empty
      intro k r res hres n _hn
      rw [(hru k r res hres).2]
      rfl
  · -- quiescence transfers across the core agreement
    intro d hd
    rw [← hcore.outbox] at hd
    rw [← hcore.watermark]
    exact hQ' d hd

/-! ## `checkFn = sem` on a W3b state, and `upos` soundness -/

/-- **`checkFn` equals `sem` on any W3b state** — the guard the upos (and bare)
    passes evaluate is the specification, at every W3b-reachable pass-start state.
    Through the shadow: `checkFn` reads only the core (`checkFn_congr`), and the
    shadow is W3a-admitted where `checkFn_eq_sem` applies. Subject-generic: `s` may
    be bare or userset (only star-free). -/
theorem checkFn_eq_sem_w3b {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3b σ S T)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hs : s.name ≠ STAR) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  obtain ⟨σ', hσ', hcore⟩ := reachedByW3b_shadow h
  rw [← checkFn_congr hcore.edges hcore.nodes T s dt on R e]
  exact checkFn_eq_sem hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hσ'
    hlk hco hleafUnt hs hon

/-- **`upos` soundness.** On a W3b state, a `upos` entry `s` at the derived key
    `(dt, R)` / object `on` witnesses `sem S T ⟨s, R, ⟨dt,on⟩⟩ = true`. By induction
    over the write path: the base persists no residue; a bare pass changes none; a
    upos pass either wrote `s` — its (fold-constant) guard held at the pass start,
    which is itself a W3b state, so `checkFn_eq_sem_w3b` turns the guard into `sem` —
    or `s` survived from the predecessor (IH). -/
theorem reachedByW3b_upos_sound {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : ReachedByW3b σ S T) :
    ∀ {s : SubjectRef} {dt on R : String} {e : Expr},
      S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      s.name ≠ STAR → on ≠ STAR →
      s ∈ σ.uposAt (objNode ⟨dt, on⟩ R) R → sem S T ⟨s, R, ⟨dt, on⟩⟩ = true := by
  induction h with
  | base hr =>
    intro s dt on R e _hlk _hder _hs _hon hmem
    have hre := (reachedByRules_inv (reachedByRules_of_admitted hr)).2.1
    unfold GraphState.uposAt at hmem
    rw [hre (objNode ⟨dt, on⟩ R) R] at hmem
    exact absurd hmem (List.not_mem_nil)
  | reconcile dt' on' R' e' cands _ _ _ _ _ _ _ ih =>
    intro s dt on R e hlk hder hs hon hmem
    obtain ⟨res, hres, hmem'⟩ := residue_of_uposAt_mem hmem
    rw [reconcileKey_residue] at hres
    exact ih hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hCO hLU hlk hder hs hon
      (by rw [uposAt_of_residue hres]; exact hmem')
  | reconcileU dt' on' R' e' cands hRne' hcands' hder' hlke' hcStar' honStar' hprev ih =>
    intro s dt on R e hlk hder hs hon hmem
    by_cases hkey : objNode ⟨dt, on⟩ R = objNode ⟨dt', on'⟩ R' ∧ R = R'
    · -- the pass's own key: candidate write or survival
      obtain ⟨hdt, hon', hRR⟩ := objNode_inj_of_ne_star hon honStar' hkey.1
      subst hdt; subst hon'; subst hRR
      have he : e = e' := Option.some.inj (hlk.symm.trans hlke')
      subst he
      rcases (reconcileUposKey_upos_mem s cands _).mp hmem with ⟨_hc, hchk⟩ | ⟨_hc, hold⟩
      · have := checkFn_eq_sem_w3b hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hprev
          hlk (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder) hs hon
        rw [hchk] at this
        exact this.symm
      · exact ih hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hCO hLU hlk hder hs hon hold
    · -- a different key: the pass left it untouched
      obtain ⟨res, hres, hmem'⟩ := residue_of_uposAt_mem hmem
      rw [reconcileUposKey_residue_other hkey] at hres
      exact ih hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hCO hLU hlk hder hs hon
        (by rw [uposAt_of_residue hres]; exact hmem')

end Zanzibar
