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

/-! ## The W3b-complete state — a coverage-complete batch of edge + upos jobs

Faithful to `build_index`/`reconcile` (`processor.py:382-446`): the processor
reconciles every derived key over every object, settling **bare** candidates as
edges (step 4) and **userset** candidates as `upos` entries (step 2c) from the same
audit enumeration (incoming concretes ∪ leaf concretes ∪ old `upos` members). The
completeness clauses are properties of the *enumeration* — every `sem`-true subject
of the matching kind is fed to some job — not of the edge/`upos` conclusion. -/

/-- A W3b reconcile job: settle one derived key/object either over bare candidates
    (edges — exactly a W3a job) or over userset candidates (`upos`). -/
inductive W3bJob where
  | edge : W3aJob → W3bJob
  | upos : W3aJob → W3bJob
deriving Repr

/-- Apply one W3b job. -/
def W3bJob.apply (T : Store) (σ : GraphState) : W3bJob → GraphState
  | .edge j => σ.reconcileKey T j.dt j.on j.R j.e j.cands
  | .upos j => σ.reconcileUposKey T j.dt j.on j.R j.e j.cands

/-- Run a batch of W3b jobs left-to-right over a base state. -/
def reconcileJobsB (T : Store) (σ0 : GraphState) (jobs : List W3bJob) : GraphState :=
  jobs.foldl (W3bJob.apply T) σ0

/-- Job validity: an edge job is a valid W3a job (bare star-free candidates); a upos
    job targets a declared derived key with its compiled def over **userset**
    star-free candidates at a concrete object — a `ReachedByW3b.reconcileU` leg. -/
def W3bJobValid (S : Schema) : W3bJob → Prop
  | .edge j => W3aJobValid S j
  | .upos j => j.R ≠ BARE ∧ (∀ c ∈ j.cands, c.predicate ≠ BARE) ∧
      isDerived S (j.dt, j.R) = true ∧ S.lookup (j.dt, j.R) = some j.e ∧
      (∀ c ∈ j.cands, c.name ≠ STAR) ∧ j.on ≠ STAR

/-- Running valid W3b jobs keeps the state W3b-reached (each job is a leg). -/
theorem reconcileJobsB_pres {S : Schema} {T : Store} :
    ∀ (jobs : List W3bJob) (σ : GraphState), ReachedByW3b σ S T →
      (∀ j ∈ jobs, W3bJobValid S j) → ReachedByW3b (reconcileJobsB T σ jobs) S T := by
  intro jobs
  induction jobs with
  | nil => intro σ h _; exact h
  | cons j js ih =>
    intro σ h hv
    have hstep : ReachedByW3b (j.apply T σ) S T := by
      cases j with
      | edge ja =>
        obtain ⟨hRne, hcb, hder, hlke, hcStar, hon⟩ := hv (.edge ja) List.mem_cons_self
        exact ReachedByW3b.reconcile ja.dt ja.on ja.R ja.e ja.cands hRne hcb hder hlke hcStar hon h
      | upos ja =>
        obtain ⟨hRne, hcu, hder, hlke, hcStar, hon⟩ := hv (.upos ja) List.mem_cons_self
        exact ReachedByW3b.reconcileU ja.dt ja.on ja.R ja.e ja.cands hRne hcu hder hlke hcStar hon h
    have hfold : reconcileJobsB T σ (j :: js) = reconcileJobsB T (j.apply T σ) js := by
      unfold reconcileJobsB; rw [List.foldl_cons]
    rw [hfold]
    exact ih (j.apply T σ) hstep (fun j' hj' => hv j' (List.mem_cons_of_mem _ hj'))

/-- W3b jobs only add edges (a upos job leaves them untouched). -/
theorem reconcileJobsB_edges_mono {T : Store} :
    ∀ (jobs : List W3bJob) (σ : GraphState) (ab : NodeKey × NodeKey),
      ab ∈ σ.edges → ab ∈ (reconcileJobsB T σ jobs).edges := by
  intro jobs
  induction jobs with
  | nil => intro σ ab h; exact h
  | cons j js ih =>
    intro σ ab h
    have hfold : reconcileJobsB T σ (j :: js) = reconcileJobsB T (j.apply T σ) js := by
      unfold reconcileJobsB; rw [List.foldl_cons]
    rw [hfold]
    refine ih (j.apply T σ) ab ?_
    cases j with
    | edge ja => exact reconcileKey_edges_mono T ja.dt ja.on ja.R ja.e ja.cands ab h
    | upos ja =>
      show ab ∈ (σ.reconcileUposKey T ja.dt ja.on ja.R ja.e ja.cands).edges
      rw [reconcileUposKey_edges]
      exact h

/-! ### `upos` persistence — a `sem`-true entry survives every later job -/

/-- The bare-edge pass never moves any `upos` list. -/
theorem uposAt_reconcileKey (T : Store) (dt on R : String) (e : Expr)
    (cands : List SubjectRef) (σ : GraphState) (k : NodeKey) (r : String) :
    (σ.reconcileKey T dt on R e cands).uposAt k r = σ.uposAt k r := by
  unfold GraphState.uposAt
  rw [reconcileKey_residue]

/-- A upos pass moves only its own key's `upos` list. -/
theorem uposAt_reconcileUposKey_other {T : Store} {dt on R : String} {e : Expr}
    {k : NodeKey} {r : String} (h : ¬(k = objNode ⟨dt, on⟩ R ∧ r = R))
    (cands : List SubjectRef) (σ : GraphState) :
    (σ.reconcileUposKey T dt on R e cands).uposAt k r = σ.uposAt k r := by
  unfold GraphState.uposAt
  rw [reconcileUposKey_residue_other h cands σ]

/-- **`upos` persistence.** A `sem`-true userset entry, once present, survives any
    batch of valid W3b jobs: edge jobs don't touch residues, other-key upos jobs
    don't touch this key, and a same-key upos job re-evaluates its (fold-constant)
    guard — which is `sem = true` (`checkFn_eq_sem_w3b` at the W3b-reached job-start
    state) — so it *keeps* the entry (re-add, never remove). -/
theorem reconcileJobsB_upos_persist {S : Schema} {T : Store}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hs : s.name ≠ STAR) (hon : on ≠ STAR)
    (hsem : sem S T ⟨s, R, ⟨dt, on⟩⟩ = true) :
    ∀ (jobs : List W3bJob) (σ : GraphState), ReachedByW3b σ S T →
      (∀ j ∈ jobs, W3bJobValid S j) →
      s ∈ σ.uposAt (objNode ⟨dt, on⟩ R) R →
      s ∈ (reconcileJobsB T σ jobs).uposAt (objNode ⟨dt, on⟩ R) R := by
  intro jobs
  induction jobs with
  | nil => intro σ _ _ hmem; exact hmem
  | cons j js ih =>
    intro σ hσ hv hmem
    have hfold : reconcileJobsB T σ (j :: js) = reconcileJobsB T (j.apply T σ) js := by
      unfold reconcileJobsB; rw [List.foldl_cons]
    rw [hfold]
    -- the state after this job is W3b-reached
    have hstep : ReachedByW3b (j.apply T σ) S T := by
      cases j with
      | edge ja =>
        obtain ⟨hRne, hcb, hderj, hlke, hcStar, honj⟩ := hv (.edge ja) List.mem_cons_self
        exact ReachedByW3b.reconcile ja.dt ja.on ja.R ja.e ja.cands hRne hcb hderj hlke hcStar honj hσ
      | upos ja =>
        obtain ⟨hRne, hcu, hderj, hlke, hcStar, honj⟩ := hv (.upos ja) List.mem_cons_self
        exact ReachedByW3b.reconcileU ja.dt ja.on ja.R ja.e ja.cands hRne hcu hderj hlke hcStar honj hσ
    refine ih (j.apply T σ) hstep (fun j' hj' => hv j' (List.mem_cons_of_mem _ hj')) ?_
    -- membership survives this single job
    cases j with
    | edge ja =>
      show s ∈ (σ.reconcileKey T ja.dt ja.on ja.R ja.e ja.cands).uposAt (objNode ⟨dt, on⟩ R) R
      rw [uposAt_reconcileKey]
      exact hmem
    | upos ja =>
      show s ∈ (σ.reconcileUposKey T ja.dt ja.on ja.R ja.e ja.cands).uposAt (objNode ⟨dt, on⟩ R) R
      obtain ⟨_hRne, _hcu, _hderj, hlke, _hcStar, honj⟩ := hv (.upos ja) List.mem_cons_self
      by_cases hkey : objNode ⟨dt, on⟩ R = objNode ⟨ja.dt, ja.on⟩ ja.R ∧ R = ja.R
      · -- same key: the guard is `sem = true`, so the entry is kept (or re-added)
        obtain ⟨hdt, hon', hRR⟩ := objNode_inj_of_ne_star hon honj hkey.1
        subst hdt; subst hon'; subst hRR
        have hje : e = ja.e := Option.some.inj (hlk.symm.trans hlke)
        subst hje
        refine (reconcileUposKey_upos_mem s ja.cands σ).mpr ?_
        by_cases hc : s ∈ ja.cands
        · refine Or.inl ⟨hc, ?_⟩
          have := checkFn_eq_sem_w3b hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hσ
            hlk (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder) hs hon
          rw [this, hsem]
        · exact Or.inr ⟨hc, hmem⟩
      · rw [uposAt_reconcileUposKey_other hkey]
        exact hmem

/-- **`W3bComplete S T σ`** — an admitted rule-routed base plus a coverage-complete
    batch of W3b jobs: every `sem`-true **bare** star-free subject at a derived key
    is enumerated by some *edge* job, and every `sem`-true **userset** star-free
    subject by some *upos* job. Faithful to the processor's audit enumeration
    (`processor.py:413-441`); the coverage clauses are enumeration properties. -/
def W3bComplete (S : Schema) (T : Store) (σ : GraphState) : Prop :=
  ∃ (σ0 : GraphState) (jobs : List W3bJob),
    ReachedByRulesAdmitted σ0 S T ∧ σ = reconcileJobsB T σ0 jobs ∧
    (∀ j ∈ jobs, W3bJobValid S j) ∧
    (∀ dt on R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ s : SubjectRef, s.predicate = BARE → s.name ≠ STAR → on ≠ STAR →
        sem S T ⟨s, R, ⟨dt, on⟩⟩ = true →
        ∃ ja, W3bJob.edge ja ∈ jobs ∧ ja.dt = dt ∧ ja.on = on ∧ ja.R = R ∧ s ∈ ja.cands) ∧
    (∀ dt on R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ s : SubjectRef, s.predicate ≠ BARE → s.name ≠ STAR → on ≠ STAR →
        sem S T ⟨s, R, ⟨dt, on⟩⟩ = true →
        ∃ ja, W3bJob.upos ja ∈ jobs ∧ ja.dt = dt ∧ ja.on = on ∧ ja.R = R ∧ s ∈ ja.cands)

/-- A W3b-complete state is W3b-reached. -/
theorem w3bComplete_reached {S : Schema} {T : Store} {σ : GraphState}
    (h : W3bComplete S T σ) : ReachedByW3b σ S T := by
  obtain ⟨σ0, jobs, h0, hσ, hv, _, _⟩ := h
  rw [hσ]
  exact reconcileJobsB_pres jobs σ0 (ReachedByW3b.base h0) hv

/-- **Bare completeness at W3b.** On a W3b-complete state, a `sem`-true bare
    star-free subject's derived edge is materialised — the W3a argument through the
    covering *edge* job, with the shadow supplying R-node terminality and the W3b
    legs supplying the guard (`checkFn_eq_sem_w3b`) at every prefix mid-state. -/
theorem w3bComplete_derived_edge {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : W3bComplete S T σ)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hsb : s.predicate = BARE) (hs : s.name ≠ STAR) (hon : on ≠ STAR)
    (hsem : sem S T ⟨s, R, ⟨dt, on⟩⟩ = true) :
    (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges := by
  obtain ⟨σ0, jobs, h0, hσ, hv, hcovE, _hcovU⟩ := h
  obtain ⟨ja, hj, hjdt, hjon, hjR, hjs⟩ := hcovE dt on R e hlk hder s hsb hs hon hsem
  obtain ⟨hjRne, hjcb, hjder, hjlke, hjcStar, hjon'⟩ := hv (.edge ja) hj
  subst hjdt; subst hjon; subst hjR
  have hje : e = ja.e := Option.some.inj (hlk.symm.trans hjlke)
  subst hje
  obtain ⟨pre, post, hsplit⟩ := List.append_of_mem hj
  have hσpre : ReachedByW3b (reconcileJobsB T σ0 pre) S T := by
    refine reconcileJobsB_pres pre σ0 (ReachedByW3b.base h0) ?_
    intro j' hj'; exact hv j' (hsplit ▸ List.mem_append_left _ hj')
  set σpre := reconcileJobsB T σ0 pre with hσpre_def
  -- R-node terminality transfers from the shadow
  obtain ⟨hnt, hns⟩ := hterm ja.dt ja.R hjder
  obtain ⟨σsh, hσsh, hcoresh⟩ := reachedByW3b_shadow hσpre
  have hRns' := reachedByW3a_Rnode_not_source hnt hns hjRne
    (reachedByW3aAdmitted_toW3a hσsh) (objNode_pred ⟨ja.dt, ja.on⟩ ja.R)
  have hRns : ∀ y, (objNode ⟨ja.dt, ja.on⟩ ja.R, y) ∉ σpre.edges := by
    intro y hy
    exact hRns' y (by rw [hcoresh.edges]; exact hy)
  -- guard: checkFn = sem = true at every prefix mid-state (a W3b leg each)
  have hguard : ∀ pre', pre' <+: ja.cands →
      (σpre.reconcileKey T ja.dt ja.on ja.R ja.e pre').checkFn T s ja.dt ja.on ja.R ja.e
        = true := by
    intro pre' hpre'
    have hmid : ReachedByW3b (σpre.reconcileKey T ja.dt ja.on ja.R ja.e pre') S T :=
      ReachedByW3b.reconcile ja.dt ja.on ja.R ja.e pre' hjRne
        (fun c hc => hjcb c (hpre'.subset hc)) hjder hjlke
        (fun c hc => hjcStar c (hpre'.subset hc)) hjon' hσpre
    have := checkFn_eq_sem_w3b hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hmid
      hlk (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder) hs hon
    rw [this, hsem]
  -- the covering job materialises the edge; it persists through `post`
  have hedge_j : (subjNode s, objNode ⟨ja.dt, ja.on⟩ ja.R)
      ∈ ((W3bJob.edge ja).apply T σpre).edges := by
    show (subjNode s, objNode ⟨ja.dt, ja.on⟩ ja.R)
        ∈ (σpre.reconcileKey T ja.dt ja.on ja.R ja.e ja.cands).edges
    exact reconcileKey_edge_present hjRne ja.cands σpre hjcb hjs hRns hguard
  have hσeq : σ = reconcileJobsB T ((W3bJob.edge ja).apply T σpre) post := by
    rw [hσ, hsplit, hσpre_def]
    unfold reconcileJobsB
    rw [List.foldl_append, List.foldl_cons]
  rw [hσeq]
  exact reconcileJobsB_edges_mono post _ _ hedge_j

/-- **Userset completeness at W3b.** On a W3b-complete state, a `sem`-true userset
    star-free subject is in the derived key's `upos`: the covering *upos* job
    enumerates it, its pass-start guard is `sem = true` (`checkFn_eq_sem_w3b`), and
    the entry persists through the remaining jobs (`reconcileJobsB_upos_persist`). -/
theorem w3bComplete_derived_upos {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : W3bComplete S T σ)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hsu : s.predicate ≠ BARE) (hs : s.name ≠ STAR) (hon : on ≠ STAR)
    (hsem : sem S T ⟨s, R, ⟨dt, on⟩⟩ = true) :
    s ∈ σ.uposAt (objNode ⟨dt, on⟩ R) R := by
  obtain ⟨σ0, jobs, h0, hσ, hv, _hcovE, hcovU⟩ := h
  obtain ⟨ja, hj, hjdt, hjon, hjR, hjs⟩ := hcovU dt on R e hlk hder s hsu hs hon hsem
  obtain ⟨hjRne, hjcu, hjder, hjlke, hjcStar, hjon'⟩ := hv (.upos ja) hj
  subst hjdt; subst hjon; subst hjR
  have hje : e = ja.e := Option.some.inj (hlk.symm.trans hjlke)
  subst hje
  obtain ⟨pre, post, hsplit⟩ := List.append_of_mem hj
  have hσpre : ReachedByW3b (reconcileJobsB T σ0 pre) S T := by
    refine reconcileJobsB_pres pre σ0 (ReachedByW3b.base h0) ?_
    intro j' hj'; exact hv j' (hsplit ▸ List.mem_append_left _ hj')
  set σpre := reconcileJobsB T σ0 pre with hσpre_def
  -- the covering job writes the entry: its pass-start guard is sem = true
  have hchk : σpre.checkFn T s ja.dt ja.on ja.R ja.e = true := by
    have := checkFn_eq_sem_w3b hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hσpre
      hlk (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder) hs hon
    rw [this, hsem]
  have hmem_j : s ∈ ((W3bJob.upos ja).apply T σpre).uposAt (objNode ⟨ja.dt, ja.on⟩ ja.R) ja.R := by
    show s ∈ (σpre.reconcileUposKey T ja.dt ja.on ja.R ja.e ja.cands).uposAt
      (objNode ⟨ja.dt, ja.on⟩ ja.R) ja.R
    exact (reconcileUposKey_upos_mem s ja.cands σpre).mpr (Or.inl ⟨hjs, hchk⟩)
  -- the entry persists through `post`
  have hstep : ReachedByW3b ((W3bJob.upos ja).apply T σpre) S T :=
    ReachedByW3b.reconcileU ja.dt ja.on ja.R ja.e ja.cands hjRne hjcu hjder hjlke
      hjcStar hjon' hσpre
  have hσeq : σ = reconcileJobsB T ((W3bJob.upos ja).apply T σpre) post := by
    rw [hσ, hsplit, hσpre_def]
    unfold reconcileJobsB
    rw [List.foldl_append, List.foldl_cons]
  rw [hσeq]
  exact reconcileJobsB_upos_persist hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm hCO hLU
    hlk hder hs hon hsem post _ hstep
    (fun j' hj' => hv j' (hsplit ▸ List.mem_append_right _ (List.mem_cons_of_mem _ hj')))
    hmem_j

/-! ## The W3b assembly — `check = sem` on ALL star-free queries

The W3a statement's `hqbare` hypothesis is GONE: userset subjects on derived keys
are now answered by the `upos` residue. Scope: star-free subject and object names;
the schema fragment is unchanged from W3a (one `RootBoolean` derived stratum over
untainted `computed` operands). -/

/-- **T2b, W3b fragment (`graph_correct_w3b`) — `check = sem` on star-free queries,
    bare AND userset subjects.**

    * **Untainted query:** the read reduces through the shadow to the admitted base,
      whose read is `sem` (`graphRec_reduce_base_adm` + `graphRec_base_eq`).
    * **Derived query, bare subject:** the upos-only read is the edge probe; `reach
      ↔ sem` by the shadow-transferred collapse/soundness and bare completeness.
    * **Derived query, userset subject:** the upos-only read is `upos` membership;
      `upos ↔ sem` by `reachedByW3b_upos_sound` and `w3bComplete_derived_upos`. -/
theorem graph_correct_w3b {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : W3bComplete S T σ)
    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem S T q := by
  have hadm := w3bComplete_reached h
  obtain ⟨hInv, hru, _hQ⟩ := reachedByW3b_inv hWF hNK hSV hRootB hadm
  have hcl := hInv.edgesClosed
  obtain ⟨σ', hσ', hcore⟩ := reachedByW3b_shadow hadm
  by_cases hder : isDerived S (q.object.type, q.relation) = true
  · -- derived query: the upos-only read
    have hderσ : isDerived σ.schema (q.object.type, q.relation) = true := by
      rw [hInv.schemaEq]; exact hder
    rw [GraphModel.check_derived_uposOnly hru q hderσ, if_neg hqo, if_neg hqs]
    obtain ⟨e, hlk⟩ := isDerived_declared hder
    have hroot : RootBoolean e :=
      hRootB ⟨(q.object.type, q.relation), e⟩ (mem_defs_of_lookup hlk) hder
    by_cases hqb : q.subject.predicate = BARE
    · -- bare subject: the edge probe
      rw [if_pos hqb]
      have hfwd : σ.reach (subjNode q.subject) (objNode q.object q.relation) = true →
          sem S T q = true := by
        intro hr
        have hN : NReaches σ'.edges (subjNode q.subject) (objNode q.object q.relation) := by
          rw [hcore.edges]; exact reach_sound hr
        have hedge := reachedByW3a_reach_collapse_root hWF hSV hNK hlk hroot
          (reachedByW3aAdmitted_toW3a hσ') hN
        exact reachedByW3aAdmitted_derived_edge_sound hWF hTT hNK hR hSV hSF hRootB hMatch
          hStrat hterm hCO hLU hσ' hlk hder hqs hqo hedge
      have hbwd : sem S T q = true →
          σ.reach (subjNode q.subject) (objNode q.object q.relation) = true := by
        intro hsemq
        have hedge := w3bComplete_derived_edge hWF hTT hNK hR hSV hSF hRootB hMatch hStrat
          hterm hCO hLU h hlk hder hqb hqs hqo hsemq
        exact reach_complete hcl (NReaches.edge hedge)
      cases hr : σ.reach (subjNode q.subject) (objNode q.object q.relation) <;>
        cases hsm : sem S T q <;> simp_all
    · -- userset subject: the upos membership read
      rw [if_neg hqb]
      have hfwd : (σ.uposAt (objNode q.object q.relation) q.relation).contains q.subject = true →
          sem S T q = true := by
        intro hc
        have hmem : q.subject ∈ σ.uposAt (objNode q.object q.relation) q.relation := by
          rw [List.contains_eq_mem] at hc; exact of_decide_eq_true hc
        exact reachedByW3b_upos_sound hWF hTT hNK hR hSV hSF hRootB hMatch hStrat hterm
          hCO hLU hadm hlk hder hqs hqo hmem
      have hbwd : sem S T q = true →
          (σ.uposAt (objNode q.object q.relation) q.relation).contains q.subject = true := by
        intro hsemq
        have hmem := w3bComplete_derived_upos hWF hTT hNK hR hSV hSF hRootB hMatch hStrat
          hterm hCO hLU h hlk hder hqb hqs hqo hsemq
        rw [List.contains_eq_mem]
        exact decide_eq_true hmem
      cases hc : (σ.uposAt (objNode q.object q.relation) q.relation).contains q.subject <;>
        cases hsm : sem S T q <;> simp_all
  · -- untainted query: reduce through the shadow to the admitted base
    have hd : isDerived S (q.object.type, q.relation) = false := by
      simpa using hder
    have hroute : GraphModel.check σ q = GraphModel.probeNonDerived σ q := by
      unfold GraphModel.check; rw [hInv.schemaEq, hd]; simp
    rw [hroute]
    obtain ⟨σ0, hσ0adm, hredx⟩ :=
      graphRec_reduce_base_adm hSF hterm hσ' (s := q.subject)
        (dt := q.object.type) (on := q.object.name)
    have h2 := hredx q.relation hd
    have h3 := graphRec_base_eq hWF hTT hNK hR hSV hSF hRootB hMatch hσ0adm hqs hqo q.relation hd
    show GraphModel.probeNonDerived σ q = sem S T q
    calc GraphModel.probeNonDerived σ q
        = GraphModel.probeNonDerived σ' q := (probeNonDerived_congr hcore.edges hcore.nodes q).symm
      _ = GraphModel.graphRec σ' q.subject q.object.type q.object.name q.relation := rfl
      _ = GraphModel.graphRec σ0 q.subject q.object.type q.object.name q.relation := h2
      _ = sem S T ⟨q.subject, q.relation, ⟨q.object.type, q.object.name⟩⟩ := h3
      _ = sem S T q := rfl

end Zanzibar
