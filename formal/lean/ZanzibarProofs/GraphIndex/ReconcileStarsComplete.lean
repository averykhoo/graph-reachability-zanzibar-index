import ZanzibarProofs.GraphIndex.ReconcileStars

/-!
# The W3c closure — the coverage-complete batch layer and `graph_correct_w3c` (ROADMAP W3c, read half)

`ReconcileStars.lean` closed the W3c **write half**: the `stars`/`neg`/`upos` residue model
(`reconcileStarsKey`), the W3a shadow, the master provenance (`reachedByW3c_master`: every
persisted row carries the CANONICAL star set of the chain's base, its `neg`/`upos`/edge members
canonically guard-checkable), and T2a `reachedByW3c_inv` with all four I6 clauses contentful.
`ReconcileComplete.lean` closed the star-relaxed base equation `checkFn_eq_sem_bs`
(over `BareStarStore` + `TtuStarFree`, subject-generic up to star-BARE subjects).

This file assembles the **read half**:

* **The shadow `checkFn` bridge** (`checkFn_eq_sem_w3c`): the compiled `check_fn` a reconcile
  pass evaluates equals `sem` at every W3c-reachable state — through the W3a-admitted shadow
  (`checkFn` reads only the core; `checkFn_eq_sem_bs` on the shadow).
* **The `W3cComplete` batch layer**: an admitted rule-routed base plus a batch of full-object
  `reconcileStarsKey` jobs (`processor.py:382-459` — one `reconcile` per derived key/object,
  audit-enumerating bare edge candidates, `neg` concretes, `upos` usersets). Coverage clauses
  are properties of the *enumeration*.
* **The assembly `graph_correct_w3c`**: `check = sem` through `probeDerived` on star-CARRYING
  stores — bare ⇒ edge ∨ (stars ∖ neg), star ⇒ stars, userset ⇒ upos ∨ (stars ∖ neg) — each
  branch glued by the master's canonicity, the `checkFn_eq_sem_bs` bridge, and completeness.

Fragment hypotheses on the store are `BareStarStore T` + `TtuStarFree S T` (replacing
`StarFreeStore`); the schema stays one `RootBoolean` derived stratum over untainted `computed`
operands (decision-15 scope: object wildcards and wildcard usersets over derived relations stay
rejected; `wildcardShapes` carries only bare-subject-star shapes).
-/

namespace Zanzibar

/-! ## The shadow `checkFn = sem` bridge on a W3c state -/

/-- **`checkFn` equals `sem` on any W3c state — star-relaxed.** Through the W3a-admitted shadow
    (`reachedByW3c_shadow`): `checkFn` reads only the core (`checkFn_congr`), and the shadow is
    W3a-admitted where `checkFn_eq_sem_bs` applies. Subject-generic up to star-BARE subjects — the
    exact form the `coveredFn` coverage correspondence consumes. -/
theorem checkFn_eq_sem_w3c {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3c σ S T)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  obtain ⟨σ', hσ', hcore⟩ := reachedByW3c_shadow h
  rw [← checkFn_congr hcore.edges hcore.nodes T s dt on R e]
  exact checkFn_eq_sem_bs hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hσ'
    hlk hco hleafUnt hs hon

/-! ## Whole-pass edge monotonicity -/

/-- The combined star pass only adds edges (the residue recompute is edge-inert; the edge fold is
    monotone through the collapse). -/
theorem reconcileStarsKey_edges_mono {σ : GraphState} (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (cands negCands uposCands : List SubjectRef) :
    ∀ ab ∈ σ.edges, ab ∈ (σ.reconcileStarsKey T dt on R e shapes cands negCands uposCands).edges := by
  intro ab hab
  unfold GraphState.reconcileStarsKey
  apply reconcileKeyC_edges_mono
  rw [reconcileResidueKey_edges]
  exact hab

/-! ## The W3c batch layer -/

/-- A W3c reconcile job: settle one derived key/object with a full `reconcileStarsKey` pass
    (residue recompute over `wildcardShapes S`/`negCands`/`uposCands`, then the covered-guarded
    edge audit over `cands`). Faithful to `reconcile` (`processor.py:382-459`). -/
structure W3cJob where
  dt : String
  on : String
  R : String
  e : Expr
  cands : List SubjectRef
  negCands : List SubjectRef
  uposCands : List SubjectRef
deriving Repr

/-- Apply one W3c job (shapes fixed to the schema's declared `wildcardShapes`). -/
def W3cJob.apply (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) : GraphState :=
  σ.reconcileStarsKey T j.dt j.on j.R j.e (wildcardShapes S) j.cands j.negCands j.uposCands

/-- Run a batch of W3c jobs left-to-right over a base state. -/
def reconcileJobsC (S : Schema) (T : Store) (σ0 : GraphState) (jobs : List W3cJob) : GraphState :=
  jobs.foldl (W3cJob.apply S T) σ0

/-- Job validity — exactly a `ReachedByW3c.reconcileS` leg's side conditions: a declared derived
    key with its compiled def, star-free bare edge candidates, star-free `neg` candidates, star-free
    userset `upos` candidates, at a concrete object. -/
def W3cJobValid (S : Schema) (j : W3cJob) : Prop :=
  j.R ≠ BARE ∧ (∀ c ∈ j.cands, c.predicate = BARE) ∧ (∀ c ∈ j.cands, c.name ≠ STAR) ∧
    (∀ c ∈ j.negCands, c.name ≠ STAR) ∧ (∀ c ∈ j.uposCands, c.predicate ≠ BARE) ∧
    (∀ c ∈ j.uposCands, c.name ≠ STAR) ∧
    isDerived S (j.dt, j.R) = true ∧ S.lookup (j.dt, j.R) = some j.e ∧ j.on ≠ STAR

/-- Running valid jobs keeps the state W3c-reached (each job is a `reconcileS` leg). -/
theorem reconcileJobsC_pres {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState), ReachedByW3c σ S T →
      (∀ j ∈ jobs, W3cJobValid S j) → ReachedByW3c (reconcileJobsC S T σ jobs) S T := by
  intro jobs
  induction jobs with
  | nil => intro σ h _; exact h
  | cons j js ih =>
    intro σ h hv
    obtain ⟨hRne, hcb, hcStar, hnegStar, huposP, huposStar, hder, hlke, hon⟩ :=
      hv j List.mem_cons_self
    have hstep : ReachedByW3c (j.apply S T σ) S T :=
      ReachedByW3c.reconcileS j.dt j.on j.R j.e j.cands j.negCands j.uposCands
        hRne hcb hcStar hnegStar huposP huposStar hder hlke hon h
    have hfold : reconcileJobsC S T σ (j :: js) = reconcileJobsC S T (j.apply S T σ) js := by
      unfold reconcileJobsC; rw [List.foldl_cons]
    rw [hfold]
    exact ih (j.apply S T σ) hstep (fun j' hj' => hv j' (List.mem_cons_of_mem _ hj'))

/-- Jobs only add edges: base edges survive the whole batch. -/
theorem reconcileJobsC_edges_mono {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState) (ab : NodeKey × NodeKey),
      ab ∈ σ.edges → ab ∈ (reconcileJobsC S T σ jobs).edges := by
  intro jobs
  induction jobs with
  | nil => intro σ ab h; exact h
  | cons j js ih =>
    intro σ ab h
    have hfold : reconcileJobsC S T σ (j :: js) = reconcileJobsC S T (j.apply S T σ) js := by
      unfold reconcileJobsC; rw [List.foldl_cons]
    rw [hfold]
    refine ih (j.apply S T σ) ab ?_
    exact reconcileStarsKey_edges_mono T j.dt j.on j.R j.e (wildcardShapes S)
      j.cands j.negCands j.uposCands ab h

end Zanzibar
