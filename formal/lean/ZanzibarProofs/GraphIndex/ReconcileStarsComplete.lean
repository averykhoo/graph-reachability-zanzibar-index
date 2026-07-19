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
`StarFreeStore`); the schema stays one `ComputedOnly` derived stratum over untainted `computed`
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
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
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
  exact checkFn_eq_sem_bs hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm hσ'
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

/-! ## The linchpin — no ghost star coverage

**`coveredFn σ0 sh = true → sh ∈ wildcardShapes S`**: a `sem`-true BARE-star subject has a
DECLARED wildcard shape. This is what collapses the space rule: the master theorem pins
`res.stars = (wildcardShapes S).filter (coveredFn σ0)`, so `res.stars.contains sh ↔
(sh ∈ wildcardShapes S ∧ coveredFn σ0 sh)` — and the read correspondence needs it
`↔ coveredFn σ0 sh` alone. Route: a true `coveredFn` has a true `computed` leaf (boolean
trees are false on all-false leaves), whose probe read leaves from the star subject's own
`wAny` node; the first edge out is a materialised closure tuple whose subject IS that node
(`reachedByRules_edge_sound`); a star closure member carries its stored seed's subject
(`rewriteClosure_star_subject`); and a stored star grant matched a wildcard-flagged
restriction (`StoreValidRules` + `restrictionMatches`), which is a `wildcardShapes` entry.

Attack-first (2026-07-11c PROOF_STATUS entry): confirmed TRUE against the `sem` defs and
NEEDED by all three `probeDerived` branches; `#eval` sanity re-run this session (scratch
deleted): `coveredFn` true exactly on the declared shape. -/

/-- A `ComputedOnly` boolean tree is true only if some `computed` leaf's `rec` is true
    (`union`/`inter`/`excl` are all false on all-false leaves). -/
theorem evalE_computedOnly_true_leaf {rec : Rec} {sub : SubjectRef} {T : Store} {q : Query}
    {dt on rel : String} :
    ∀ e : Expr, ComputedOnly e → evalE rec sub T q dt on rel e = true →
      ∃ r' ∈ computedRefs e, rec dt on r' = true := by
  intro e
  induction e with
  | computed r' =>
    intro _ h
    exact ⟨r', List.mem_singleton.mpr rfl, h⟩
  | union a b iha ihb =>
    intro hco h
    simp only [evalE, Bool.or_eq_true] at h
    rcases h with h | h
    · obtain ⟨r', hr', hrec⟩ := iha hco.1 h
      exact ⟨r', List.mem_append_left _ hr', hrec⟩
    · obtain ⟨r', hr', hrec⟩ := ihb hco.2 h
      exact ⟨r', List.mem_append_right _ hr', hrec⟩
  | inter a b iha ihb =>
    intro hco h
    simp only [evalE, Bool.and_eq_true] at h
    obtain ⟨r', hr', hrec⟩ := iha hco.1 h.1
    exact ⟨r', List.mem_append_left _ hr', hrec⟩
  | excl a b iha ihb =>
    intro hco h
    simp only [evalE, Bool.and_eq_true] at h
    obtain ⟨r', hr', hrec⟩ := iha hco.1 h.1
    exact ⟨r', List.mem_append_left _ hr', hrec⟩
  | direct rs => intro hco _; exact hco.elim
  | ttu tr ts => intro hco _; exact hco.elim

/-- A non-empty path has a first edge out of its source. -/
theorem nreaches_first_edge {edges : List (NodeKey × NodeKey)} {u v : NodeKey}
    (h : NReaches edges u v) : ∃ y, (u, y) ∈ edges := by
  cases h with
  | edge h => exact ⟨_, h⟩
  | head h _ => exact ⟨_, h⟩

/-- A restriction of a `Direct` storage arm occurs in the expression's restriction set. -/
theorem mem_exprRestrictions_of_directs {e : Expr} {rs : List Restriction} {r : Restriction}
    (hd : rs ∈ exprDirects e) (hr : r ∈ rs) : r ∈ exprRestrictions e := by
  induction e with
  | direct rs' =>
    simp only [exprDirects, List.mem_singleton] at hd
    subst hd
    exact hr
  | union a b iha ihb =>
    simp only [exprDirects, List.mem_append] at hd
    rcases hd with h | h
    · exact List.mem_append_left _ (iha h)
    · exact List.mem_append_right _ (ihb h)
  | computed _ => simp [exprDirects] at hd
  | ttu _ _ => simp [exprDirects] at hd
  | inter _ _ _ _ => simp [exprDirects] at hd
  | excl _ _ _ _ => simp [exprDirects] at hd

/-- **THE LINCHPIN (`coveredFn_declared`).** On an admitted rule-routed base, star coverage
    of a shape implies the shape is a declared subject-wildcard shape — no ghost star
    coverage. -/
theorem coveredFn_declared {S : Schema} {T : Store} {σ0 : GraphState}
    (hTT : TtuTuplesetsDirect S) (hSV : StoreValidRules S T) (hTS : TtuStarFree S T)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    {dt on R : String} {e : Expr} (hco : ComputedOnly e) {sh : Shape}
    (hcov : σ0.coveredFn T dt on R e sh = true) :
    sh ∈ wildcardShapes S := by
  -- 1. some computed leaf's graph read is true
  unfold GraphState.coveredFn GraphState.checkFn at hcov
  obtain ⟨r', _hr', hleaf⟩ := evalE_computedOnly_true_leaf e hco hcov
  -- 2. the star subject's probes leave from its own node (probes 2/4 dead: name = STAR)
  have hstar : (starSubj sh).name = STAR := rfl
  have hreach : ∃ v, σ0.reach (subjNode (starSubj sh)) v = true := by
    unfold GraphModel.graphRec GraphModel.probeNonDerived at hleaf
    simp only [starSubj, bne_self_eq_false, Bool.false_and, Bool.or_false, Bool.false_or,
      Bool.or_eq_true, Bool.and_eq_true] at hleaf
    rcases hleaf with h | ⟨_, h⟩
    · exact ⟨_, h⟩
    · exact ⟨_, h⟩
  obtain ⟨v, hv⟩ := hreach
  -- 3. the first edge out is a materialised closure tuple sourced at the wAny node
  obtain ⟨y, hy⟩ := nreaches_first_edge (reach_sound hv)
  obtain ⟨t, ht, u, hu, hsubj, _hobj⟩ :=
    reachedByRules_edge_sound (reachedByRules_of_admitted h0) _ y hy
  -- 4. the closure tuple's subject IS the star subject
  have hustar : u.subject.name = STAR := by
    by_contra hne
    have hvar := congrArg NodeKey.variant hsubj
    rw [subjNode, if_pos hstar, subjNode, if_neg hne] at hvar
    have hvar' : Variant.wAny = Variant.plain := hvar
    cases hvar'
  have husubj : u.subject = starSubj sh := by
    have h1 : sh.1 = u.subject.type := by
      have := congrArg NodeKey.type hsubj
      rw [subjNode, if_pos hstar, subjNode, if_pos hustar] at this
      exact this
    have h2 : sh.2 = u.subject.predicate := by
      have := congrArg NodeKey.pred hsubj
      rw [subjNode, if_pos hstar, subjNode, if_pos hustar] at this
      exact this
    show u.subject = (⟨sh.1, STAR, sh.2⟩ : SubjectRef)
    have heta : u.subject = ⟨u.subject.type, u.subject.name, u.subject.predicate⟩ := rfl
    rw [heta, ← h1, ← h2, hustar]
  -- 5. a star closure member carries the stored seed's subject
  have hts : t.subject = starSubj sh :=
    (rewriteClosure_star_subject hTT hTS ht hu hustar).symm.trans husubj
  -- 6. the seed matched a wildcard-flagged restriction of its declared def
  obtain ⟨e', rs, hlk', hdirs, hrm⟩ := hSV t ht
  unfold restrictionMatches at hrm
  obtain ⟨r, hrmem, hrb⟩ := List.any_eq_true.mp hrm
  simp only [Bool.and_eq_true, beq_iff_eq] at hrb
  obtain ⟨⟨hty, hpred⟩, hwc⟩ := hrb
  have htstar : t.subject.name = STAR := by rw [hts]; rfl
  have hr22 : r.2.2 = true := by
    rw [htstar] at hwc
    simpa using hwc
  have hsh1 : sh.1 = r.1 := by rw [← hty, hts]; rfl
  have hsh2 : sh.2 = r.2.1 := by rw [← hpred, hts]; rfl
  -- 7. assemble the `wildcardShapes` membership
  unfold wildcardShapes
  refine List.mem_flatMap.mpr ⟨((t.object.type, t.relation), e'), mem_defs_of_lookup hlk', ?_⟩
  refine List.mem_filterMap.mpr ⟨r, mem_exprRestrictions_of_directs hdirs hrmem, ?_⟩
  rw [if_pos hr22, ← hsh1, ← hsh2]

/-! ## Direct-arm no-ghost-coverage (`coveredFn_declared_d`) — leg 5 sub-step 2 enum half

The linchpin `coveredFn_declared` widened to a `StoreValidRulesD` store carrying BARE
Direct-arm tuples on derived keys and a `ComputedOrDirect`/`DirectArmsBare` def. A true
star read of shape `sh` still certifies `sh ∈ wildcardShapes S`: a true COMPUTED leaf traces
its materialised closure edge to a wildcard-flagged restriction exactly as before (the seed
classification now takes the `StoreValidRulesD` DISJUNCTION — untainted `exprDirects` OR
derived `exprDirectsAll`); a true DIRECT leaf at the star subject is a stored bare-STAR grant
whose matching restriction (a STAR-name subject only matches a wildcard-flagged restriction)
IS a declared wildcard shape of the def `(dt,R)`. No ghost coverage on the Direct arm. -/

/-- A restriction of a `Direct` leaf reachable through ANY boolean nesting (`exprDirectsAll`,
    incl. `inter`/`excl`) occurs in the expression's restriction set — the `exprDirectsAll`
    analog of `mem_exprRestrictions_of_directs`. -/
theorem mem_exprRestrictions_of_directsAll {e : Expr} {rs : List Restriction}
    {r : Restriction} (hd : rs ∈ exprDirectsAll e) (hr : r ∈ rs) : r ∈ exprRestrictions e := by
  induction e with
  | direct rs' =>
    simp only [exprDirectsAll, List.mem_singleton] at hd; subst hd; exact hr
  | union a b iha ihb =>
    simp only [exprDirectsAll, List.mem_append] at hd
    rcases hd with h | h
    · exact List.mem_append_left _ (iha h)
    · exact List.mem_append_right _ (ihb h)
  | inter a b iha ihb =>
    simp only [exprDirectsAll, List.mem_append] at hd
    rcases hd with h | h
    · exact List.mem_append_left _ (iha h)
    · exact List.mem_append_right _ (ihb h)
  | excl a b iha ihb =>
    simp only [exprDirectsAll, List.mem_append] at hd
    rcases hd with h | h
    · exact List.mem_append_left _ (iha h)
    · exact List.mem_append_right _ (ihb h)
  | computed _ => simp [exprDirectsAll] at hd
  | ttu _ _ => simp [exprDirectsAll] at hd

/-- `DirectArmsBare` propagates to every arm reachable via `exprDirectsAll`: each such arm's
    restrictions are all BARE (`r.2.1 = BARE`). -/
theorem directArmsBare_mem : ∀ {e : Expr}, DirectArmsBare e →
    ∀ {rs : List Restriction}, rs ∈ exprDirectsAll e → ∀ r ∈ rs, r.2.1 = BARE := by
  intro e
  induction e with
  | direct rs' =>
    intro hb rs hrs; simp only [exprDirectsAll, List.mem_singleton] at hrs; subst hrs; exact hb
  | computed _ => intro _ rs hrs; simp [exprDirectsAll] at hrs
  | ttu _ _ => intro _ rs hrs; simp [exprDirectsAll] at hrs
  | union a b iha ihb =>
    intro hb rs hrs; simp only [exprDirectsAll, List.mem_append] at hrs
    rcases hrs with h | h
    · exact iha hb.1 h
    · exact ihb hb.2 h
  | inter a b iha ihb =>
    intro hb rs hrs; simp only [exprDirectsAll, List.mem_append] at hrs
    rcases hrs with h | h
    · exact iha hb.1 h
    · exact ihb hb.2 h
  | excl a b iha ihb =>
    intro hb rs hrs; simp only [exprDirectsAll, List.mem_append] at hrs
    rcases hrs with h | h
    · exact iha hb.1 h
    · exact ihb hb.2 h

/-- **The star-reach no-ghost-coverage core (`_d`).** A star subject whose graph read at an
    (arbitrary) leaf `(dt', on', r')` is true means the leaf's shape `sh` is a declared
    subject-wildcard shape — under the WIDENED store admission `StoreValidRulesD` (the seed
    classification takes the disjunction). Steps 2–7 of `coveredFn_declared`, disjunction-
    factored. The `StoreValidRulesD` analog of `graphRec_star_declared`. -/
theorem graphRec_star_declared_d {S : Schema} {T : Store} {σ0 : GraphState}
    (hTT : TtuTuplesetsDirect S) (hSV : StoreValidRulesD S T) (hTS : TtuStarFree S T)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    {sh : Shape} {dt' on' r' : String}
    (hleaf : GraphModel.graphRec σ0 (starSubj sh) dt' on' r' = true) :
    sh ∈ wildcardShapes S := by
  have hstar : (starSubj sh).name = STAR := rfl
  have hreach : ∃ v, σ0.reach (subjNode (starSubj sh)) v = true := by
    unfold GraphModel.graphRec GraphModel.probeNonDerived at hleaf
    simp only [starSubj, bne_self_eq_false, Bool.false_and, Bool.or_false, Bool.false_or,
      Bool.or_eq_true, Bool.and_eq_true] at hleaf
    rcases hleaf with h | ⟨_, h⟩
    · exact ⟨_, h⟩
    · exact ⟨_, h⟩
  obtain ⟨v, hv⟩ := hreach
  obtain ⟨y, hy⟩ := nreaches_first_edge (reach_sound hv)
  obtain ⟨t, ht, u, hu, hsubj, _hobj⟩ :=
    reachedByRules_edge_sound (reachedByRules_of_admitted h0) _ y hy
  have hustar : u.subject.name = STAR := by
    by_contra hne
    have hvar := congrArg NodeKey.variant hsubj
    rw [subjNode, if_pos hstar, subjNode, if_neg hne] at hvar
    have hvar' : Variant.wAny = Variant.plain := hvar
    cases hvar'
  have husubj : u.subject = starSubj sh := by
    have h1 : sh.1 = u.subject.type := by
      have := congrArg NodeKey.type hsubj
      rw [subjNode, if_pos hstar, subjNode, if_pos hustar] at this
      exact this
    have h2 : sh.2 = u.subject.predicate := by
      have := congrArg NodeKey.pred hsubj
      rw [subjNode, if_pos hstar, subjNode, if_pos hustar] at this
      exact this
    show u.subject = (⟨sh.1, STAR, sh.2⟩ : SubjectRef)
    have heta : u.subject = ⟨u.subject.type, u.subject.name, u.subject.predicate⟩ := rfl
    rw [heta, ← h1, ← h2, hustar]
  have hts : t.subject = starSubj sh :=
    (rewriteClosure_star_subject hTT hTS ht hu hustar).symm.trans husubj
  -- the seed matched a wildcard-flagged restriction of its declared def (disjunction-factored)
  obtain ⟨e', rs, hlk', hRinRestr, hrm⟩ :
      ∃ e' rs, S.lookup (t.object.type, t.relation) = some e' ∧
        (∀ r ∈ rs, r ∈ exprRestrictions e') ∧ restrictionMatches rs t = true := by
    rcases hSV t ht with ⟨_, e', rs, hlk', hdirs, hrm⟩ | ⟨_, _, e', rs, hlk', hdirs, hrm, _⟩
    · exact ⟨e', rs, hlk', fun r hr => mem_exprRestrictions_of_directs hdirs hr, hrm⟩
    · exact ⟨e', rs, hlk', fun r hr => mem_exprRestrictions_of_directsAll hdirs hr, hrm⟩
  unfold restrictionMatches at hrm
  obtain ⟨r, hrmem, hrb⟩ := List.any_eq_true.mp hrm
  simp only [Bool.and_eq_true, beq_iff_eq] at hrb
  obtain ⟨⟨hty, hpred⟩, hwc⟩ := hrb
  have htstar : t.subject.name = STAR := by rw [hts]; rfl
  have hr22 : r.2.2 = true := by rw [htstar] at hwc; simpa using hwc
  have hsh1 : sh.1 = r.1 := by rw [← hty, hts]; rfl
  have hsh2 : sh.2 = r.2.1 := by rw [← hpred, hts]; rfl
  unfold wildcardShapes
  refine List.mem_flatMap.mpr ⟨((t.object.type, t.relation), e'), mem_defs_of_lookup hlk', ?_⟩
  refine List.mem_filterMap.mpr ⟨r, hRinRestr r hrmem, ?_⟩
  rw [if_pos hr22, ← hsh1, ← hsh2]

/-- A `ComputedOrDirect` boolean tree is true only if some `computed` leaf's `rec` is true OR
    some `Direct` arm (reachable via `exprDirectsAll`) reads true — the `_cd` analog of
    `evalE_computedOnly_true_leaf`. -/
theorem evalE_computedOrDirect_true_leaf {rec : Rec} {sub : SubjectRef} {T : Store} {q : Query}
    {dt on rel : String} :
    ∀ e : Expr, ComputedOrDirect e → evalE rec sub T q dt on rel e = true →
      (∃ r' ∈ computedRefs e, rec dt on r' = true) ∨
      (∃ rs ∈ exprDirectsAll e, directLeaf rec sub T q rs dt on rel = true) := by
  intro e
  induction e with
  | computed r' =>
    intro _ h; exact Or.inl ⟨r', List.mem_singleton.mpr rfl, h⟩
  | direct rs =>
    intro _ h
    exact Or.inr ⟨rs, List.mem_singleton.mpr rfl, h⟩
  | union a b iha ihb =>
    intro hcd h
    simp only [evalE, Bool.or_eq_true] at h
    rcases h with h | h
    · rcases iha hcd.1 h with ⟨r', hr', hrec⟩ | ⟨rs, hrs, hdl⟩
      · exact Or.inl ⟨r', List.mem_append_left _ hr', hrec⟩
      · exact Or.inr ⟨rs, List.mem_append_left _ hrs, hdl⟩
    · rcases ihb hcd.2 h with ⟨r', hr', hrec⟩ | ⟨rs, hrs, hdl⟩
      · exact Or.inl ⟨r', List.mem_append_right _ hr', hrec⟩
      · exact Or.inr ⟨rs, List.mem_append_right _ hrs, hdl⟩
  | inter a b iha ihb =>
    intro hcd h
    simp only [evalE, Bool.and_eq_true] at h
    rcases iha hcd.1 h.1 with ⟨r', hr', hrec⟩ | ⟨rs, hrs, hdl⟩
    · exact Or.inl ⟨r', List.mem_append_left _ hr', hrec⟩
    · exact Or.inr ⟨rs, List.mem_append_left _ hrs, hdl⟩
  | excl a b iha ihb =>
    intro hcd h
    simp only [evalE, Bool.and_eq_true] at h
    rcases iha hcd.1 h.1 with ⟨r', hr', hrec⟩ | ⟨rs, hrs, hdl⟩
    · exact Or.inl ⟨r', List.mem_append_left _ hr', hrec⟩
    · exact Or.inr ⟨rs, List.mem_append_left _ hrs, hdl⟩
  | ttu tr ts => intro hcd _; exact hcd.elim

/-- **The Direct-arm no-ghost-coverage certification.** A true `Direct` leaf at the star
    subject `starSubj sh` on a BARE arm `rs` (reachable via `exprDirectsAll` of the def `e` of
    `(dt,R)`) means `sh` is a declared wildcard shape: `memberOfGranted` is dead on bare grants,
    so the star-match disjunct fires — a bare-STAR grant of shape `sh` — and a STAR-name subject
    only matches a WILDCARD-FLAGGED restriction, which lives in `exprRestrictions e`. -/
theorem directArm_star_declared {S : Schema} {T : Store} {rec : Rec} {q : Query}
    {dt on R : String} {e : Expr} {rs : List Restriction} {sh : Shape}
    (hlk : S.lookup (dt, R) = some e) (hba : DirectArmsBare e)
    (hrs : rs ∈ exprDirectsAll e)
    (hdl : directLeaf rec (starSubj sh) T q rs dt on R = true) :
    sh ∈ wildcardShapes S := by
  have hbr : ∀ r ∈ rs, r.2.1 = BARE := directArmsBare_mem hba hrs
  have hbareG : ∀ g ∈ grantsOf T rs dt on R, g.subject.predicate = BARE :=
    grantsOf_bare_subjects T rs dt on R hbr
  -- the star-match disjunct fires (memberOfGranted dead)
  unfold directLeaf at hdl
  simp only [starSubj, beq_self_eq_true, if_true,
    memberOfGranted_of_bareGrants rec T q _ hbareG, Bool.or_false] at hdl
  obtain ⟨g, hg, hgb⟩ := List.any_eq_true.mp hdl
  simp only [Bool.and_eq_true, beq_iff_eq] at hgb
  obtain ⟨⟨hgstar, hgty⟩, hgpred⟩ := hgb
  -- g matches rs (g ∈ grantsOf), and g's STAR name forces a wildcard-flagged restriction
  have hgmatch : restrictionMatches rs g = true := by
    unfold grantsOf at hg; rw [List.mem_filter] at hg
    simp only [Bool.and_eq_true] at hg
    exact hg.2.2
  unfold restrictionMatches at hgmatch
  obtain ⟨r, hrmem, hrb⟩ := List.any_eq_true.mp hgmatch
  simp only [Bool.and_eq_true, beq_iff_eq] at hrb
  obtain ⟨⟨hty, hpred⟩, hwc⟩ := hrb
  have hr22 : r.2.2 = true := by rw [hgstar] at hwc; simpa using hwc
  have hsh1 : sh.1 = r.1 := by rw [← hty, hgty]
  have hsh2 : sh.2 = r.2.1 := by rw [← hpred, hgpred]
  unfold wildcardShapes
  refine List.mem_flatMap.mpr ⟨((dt, R), e), mem_defs_of_lookup hlk, ?_⟩
  refine List.mem_filterMap.mpr ⟨r, mem_exprRestrictions_of_directsAll hrs hrmem, ?_⟩
  rw [if_pos hr22, ← hsh1, ← hsh2]

/-- **The linchpin `coveredFn_declared`, widened to Direct arms (`coveredFn_declared_d`).** On a
    `StoreValidRulesD` store with a `ComputedOrDirect`/`DirectArmsBare` def `e` of `(dt,R)`, star
    coverage of a shape `sh` implies `sh ∈ wildcardShapes S`. A true COMPUTED leaf rides
    `graphRec_star_declared_d`; a true DIRECT arm rides `directArm_star_declared`. -/
theorem coveredFn_declared_d {S : Schema} {T : Store} {σ0 : GraphState}
    (hTT : TtuTuplesetsDirect S) (hSV : StoreValidRulesD S T) (hTS : TtuStarFree S T)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    {dt on R : String} {e : Expr} (hlk : S.lookup (dt, R) = some e)
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e) {sh : Shape}
    (hcov : σ0.coveredFn T dt on R e sh = true) :
    sh ∈ wildcardShapes S := by
  unfold GraphState.coveredFn GraphState.checkFn at hcov
  rcases evalE_computedOrDirect_true_leaf e hcd hcov with ⟨r', _hr', hleaf⟩ | ⟨rs, hrs, hdl⟩
  · exact graphRec_star_declared_d hTT hSV hTS h0 hleaf
  · exact directArm_star_declared hlk hba hrs hdl

/-! ## Row characterisation — every persisted W3c row reads at `sem` level

Master (`reachedByW3c_master`) pins each row to the canonical base filters; the
star-relaxed bridge (`checkFn_eq_sem_bs` at the master base) converts every filter guard
to `sem`. `hWSbare` (decision-15 scope: only bare-subject wildcard shapes are declared —
wildcard usersets over derived relations are rejected, and userset-star coverage is
deferred with the W1c machinery) makes each declared shape's star subject BARE, which is
what the bridge's subject scope admits. -/

/-- **The `sem`-level row characterisation.** On a W3c state, any persisted row at a
    declared derived key satisfies: `stars` contains exactly the declared shapes whose
    star subject is `sem`-true; every `neg` member is star-free and `sem`-false; every
    `upos` member is a star-free userset and `sem`-true. -/
theorem w3c_row_char {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3c σ S T)
    {dt on R : String} {e : Expr} {res : Residue}
    (hlk : S.lookup (dt, R) = some e) (hon : on ≠ STAR)
    (hrow : σ.residue (objNode ⟨dt, on⟩ R) R = some res) :
    (∀ sh, res.stars.contains sh = true ↔
      (sh ∈ wildcardShapes S ∧ sem S T ⟨starSubj sh, R, ⟨dt, on⟩⟩ = true)) ∧
    (∀ n ∈ res.neg, n.name ≠ STAR ∧ sem S T ⟨n, R, ⟨dt, on⟩⟩ = false) ∧
    (∀ n ∈ res.upos, n.predicate ≠ BARE ∧ n.name ≠ STAR ∧
      sem S T ⟨n, R, ⟨dt, on⟩⟩ = true) := by
  obtain ⟨σ0, hσ0, _hag, hres, _hedge⟩ := reachedByW3c_master hterm hCO hLU h
  obtain ⟨dt', on', e', hk, hder', _hRne', hon', hlk', hstars, hnegm, huposm⟩ :=
    hres _ _ res hrow
  obtain ⟨hdt, honn, _⟩ := objNode_inj_of_ne_star hon hon' hk
  subst hdt
  subst honn
  have he' : e = e' := Option.some.inj (hlk.symm.trans hlk')
  subst he'
  have hbridge : ∀ (x : SubjectRef), (x.name = STAR → x.predicate = BARE) →
      σ0.checkFn T x dt on R e = sem S T ⟨x, R, ⟨dt, on⟩⟩ := fun x hx =>
    checkFn_eq_sem_bs hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm
      (ReachedByW3aAdmitted.base hσ0) hlk (hCO _ _ _ hlk hder') (hLU _ _ _ hlk hder') hx hon
  refine ⟨?_, ?_, ?_⟩
  · intro sh
    rw [hstars]
    constructor
    · intro hc
      rw [List.contains_eq_mem] at hc
      obtain ⟨hws, hcov⟩ := List.mem_filter.mp (of_decide_eq_true hc)
      refine ⟨hws, ?_⟩
      rw [← hbridge (starSubj sh) (fun _ => hWSbare sh hws)]
      exact hcov
    · rintro ⟨hws, hsem⟩
      have hcov : σ0.coveredFn T dt on R e sh = true := by
        show σ0.checkFn T (starSubj sh) dt on R e = true
        rw [hbridge (starSubj sh) (fun _ => hWSbare sh hws)]
        exact hsem
      rw [List.contains_eq_mem]
      exact decide_eq_true (List.mem_filter.mpr ⟨hws, hcov⟩)
  · intro n hn
    obtain ⟨_hcov, hnstar, hchk⟩ := hnegm n hn
    refine ⟨hnstar, ?_⟩
    rw [← hbridge n (fun hx => absurd hx hnstar)]
    exact hchk
  · intro n hn
    obtain ⟨_hunc, hnp, hnstar, hchk⟩ := huposm n hn
    exact ⟨hnp, hnstar, by rw [← hbridge n (fun hx => absurd hx hnstar)]; exact hchk⟩

/-! ## Per-key job coverage — row existence and `neg`/`upos` completeness

The residue is a WHOLESALE per-pass recompute (`reconcile` steps 1–3 replace the whole
row), so a `neg`/`upos` member survives the batch only if **every** job targeting its key
enumerates it — an attack-first `#eval` this session confirmed a second same-key pass
with an incomplete `negCands` DROPS the exclusion and breaks `check = sem` (necessity of
the ∀-jobs form; scratch deleted). Faithful to Python: every `reconcile` call re-derives
the full audit enumeration (`_leaf_concretes` ∪ persisted ids, `processor.py:394-441`),
so any store-supported subject is in every call's enumeration. -/

/-- Does a job target the derived key `(dt, R)` at object `on`? -/
def W3cJob.keyMatch (j : W3cJob) (dt on R : String) : Prop :=
  j.dt = dt ∧ j.on = on ∧ j.R = R

/-- **Row existence.** Once some job targets a key (or a row already exists), the final
    residue row at that key is present — jobs create their own row and never delete
    another's. -/
theorem reconcileJobsC_row_isSome {S : Schema} {T : Store} {dt on R : String} :
    ∀ (jobs : List W3cJob) (σ : GraphState),
      ((σ.residue (objNode ⟨dt, on⟩ R) R).isSome = true ∨
        ∃ j ∈ jobs, j.keyMatch dt on R) →
      ((reconcileJobsC S T σ jobs).residue (objNode ⟨dt, on⟩ R) R).isSome = true := by
  intro jobs
  induction jobs with
  | nil =>
    intro σ h
    rcases h with h | ⟨j, hj, _⟩
    · exact h
    · exact absurd hj List.not_mem_nil
  | cons j js ih =>
    intro σ h
    have hfold : reconcileJobsC S T σ (j :: js) = reconcileJobsC S T (j.apply S T σ) js := by
      unfold reconcileJobsC; rw [List.foldl_cons]
    rw [hfold]
    apply ih
    by_cases hkey : objNode ⟨dt, on⟩ R = objNode ⟨j.dt, j.on⟩ j.R ∧ R = j.R
    · refine Or.inl ?_
      show ((σ.reconcileStarsKey T j.dt j.on j.R j.e (wildcardShapes S) j.cands j.negCands
        j.uposCands).residue (objNode ⟨dt, on⟩ R) R).isSome = true
      rw [hkey.1, hkey.2, reconcileStarsKey_residue_self, reconcileResidueKey_residue_self]
      rfl
    · rcases h with hl | ⟨j', hj', hm⟩
      · refine Or.inl ?_
        show ((σ.reconcileStarsKey T j.dt j.on j.R j.e (wildcardShapes S) j.cands j.negCands
          j.uposCands).residue (objNode ⟨dt, on⟩ R) R).isSome = true
        rw [reconcileStarsKey_residue_other hkey]
        exact hl
      · rcases List.mem_cons.mp hj' with rfl | hj's
        · exact absurd ⟨by rw [hm.1, hm.2.1, hm.2.2], hm.2.2.symm⟩ hkey
        · exact Or.inr ⟨j', hj's, hm⟩

/-- **`neg` completeness.** A star-free subject with a declared, `sem`-covered shape that
    is `sem`-false at the derived key ends (and stays) in the key's `neg` — provided every
    job targeting the key enumerates it (the wholesale-recompute condition) and at least
    one such job runs (or a row already carries it). Each targeting pass re-derives the
    membership from its own guard, which the `checkFn = sem` bridge pins at every
    W3c-reached pass start. -/
theorem reconcileJobsC_neg_complete {S : Schema} {T : Store}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e)
    (hsstar : s.name ≠ STAR) (hon : on ≠ STAR)
    (hshWS : s.shape ∈ wildcardShapes S)
    (hsemStar : sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true)
    (hsemF : sem S T ⟨s, R, ⟨dt, on⟩⟩ = false) :
    ∀ (jobs : List W3cJob) (σ : GraphState), ReachedByW3c σ S T →
      (∀ j ∈ jobs, W3cJobValid S j) →
      (∀ j ∈ jobs, j.keyMatch dt on R → s ∈ j.negCands) →
      ((∃ res, σ.residue (objNode ⟨dt, on⟩ R) R = some res ∧ s ∈ res.neg) ∨
        ∃ j ∈ jobs, j.keyMatch dt on R) →
      ∃ res, (reconcileJobsC S T σ jobs).residue (objNode ⟨dt, on⟩ R) R = some res ∧
        s ∈ res.neg := by
  intro jobs
  induction jobs with
  | nil =>
    intro σ _ _ _ h
    rcases h with h | ⟨j, hj, _⟩
    · exact h
    · exact absurd hj List.not_mem_nil
  | cons j js ih =>
    intro σ hσ hv hcand h
    obtain ⟨jdt, jon, jR, je, jc, jn, ju⟩ := j
    obtain ⟨hRne, hcb, hcS, hnegS, huP, huS, hder, hlke, honj⟩ := hv _ List.mem_cons_self
    have hfold : reconcileJobsC S T σ (⟨jdt, jon, jR, je, jc, jn, ju⟩ :: js)
        = reconcileJobsC S T (W3cJob.apply S T σ ⟨jdt, jon, jR, je, jc, jn, ju⟩) js := by
      unfold reconcileJobsC; rw [List.foldl_cons]
    rw [hfold]
    have hstep : ReachedByW3c (W3cJob.apply S T σ ⟨jdt, jon, jR, je, jc, jn, ju⟩) S T :=
      ReachedByW3c.reconcileS jdt jon jR je jc jn ju hRne hcb hcS hnegS huP huS hder hlke honj hσ
    apply ih _ hstep (fun j' hj' => hv j' (List.mem_cons_of_mem _ hj'))
      (fun j' hj' => hcand j' (List.mem_cons_of_mem _ hj'))
    by_cases hkm : W3cJob.keyMatch ⟨jdt, jon, jR, je, jc, jn, ju⟩ dt on R
    · -- the job targets the key: it rewrites the row WITH s in `neg`
      obtain ⟨h1, h2, h3⟩ := hkm
      have h1' : dt = jdt := h1.symm
      have h2' : on = jon := h2.symm
      have h3' : R = jR := h3.symm
      subst h1'; subst h2'; subst h3'
      have hje : e = je := by
        simp only at hlke
        exact Option.some.inj (hlk.symm.trans hlke)
      subst hje
      simp only at hder
      refine Or.inl ?_
      have hrow := reconcileStarsKey_residue_self σ T dt on R e (wildcardShapes S) jc jn ju
      rw [reconcileResidueKey_residue_self] at hrow
      refine ⟨_, hrow, ?_⟩
      refine List.mem_filter.mpr ⟨hcand _ List.mem_cons_self ⟨rfl, rfl, rfl⟩, ?_⟩
      have hchkS : σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3c hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm hσ hlk
          (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder) (fun hx => absurd hx hsstar) hon
      have hcovS : σ.coveredFn T dt on R e s.shape = true := by
        show σ.checkFn T (starSubj s.shape) dt on R e = true
        rw [checkFn_eq_sem_w3c (s := starSubj s.shape) hWF hTT hNK hR hSV hBS hTS hCO
          hMatch hStrat hterm hσ hlk (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder)
          (fun _ => hWSbare s.shape hshWS) hon]
        exact hsemStar
      rw [Bool.and_eq_true]
      constructor
      · rw [List.contains_eq_mem]
        exact decide_eq_true (List.mem_filter.mpr ⟨hshWS, hcovS⟩)
      · rw [hchkS, hsemF]
        rfl
    · -- another key: the row at the query key is untouched
      have hne : ¬(objNode ⟨dt, on⟩ R = objNode ⟨jdt, jon⟩ jR ∧ R = jR) := by
        rintro ⟨hk, hRR⟩
        obtain ⟨e1, e2, _⟩ := objNode_inj_of_ne_star hon honj hk
        exact hkm ⟨e1.symm, e2.symm, hRR.symm⟩
      rcases h with ⟨res, hres, hmem⟩ | ⟨j', hj', hm⟩
      · refine Or.inl ⟨res, ?_, hmem⟩
        show (σ.reconcileStarsKey T jdt jon jR je (wildcardShapes S) jc jn ju).residue
          (objNode ⟨dt, on⟩ R) R = some res
        rw [reconcileStarsKey_residue_other hne]
        exact hres
      · rcases List.mem_cons.mp hj' with rfl | hj's
        · exact absurd hm hkm
        · exact Or.inr ⟨j', hj's, hm⟩

/-- **`upos` completeness.** A `sem`-true star-free USERSET subject at the derived key
    ends (and stays) in the key's `upos` — every targeting pass keeps it because its shape
    is never a declared (bare, `hWSbare`) wildcard shape, so it is never star-covered, and
    its guard is `sem`-true at every W3c-reached pass start. -/
theorem reconcileJobsC_upos_complete {S : Schema} {T : Store}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e)
    (hsu : s.predicate ≠ BARE) (hsstar : s.name ≠ STAR) (hon : on ≠ STAR)
    (hsemT : sem S T ⟨s, R, ⟨dt, on⟩⟩ = true) :
    ∀ (jobs : List W3cJob) (σ : GraphState), ReachedByW3c σ S T →
      (∀ j ∈ jobs, W3cJobValid S j) →
      (∀ j ∈ jobs, j.keyMatch dt on R → s ∈ j.uposCands) →
      ((∃ res, σ.residue (objNode ⟨dt, on⟩ R) R = some res ∧ s ∈ res.upos) ∨
        ∃ j ∈ jobs, j.keyMatch dt on R) →
      ∃ res, (reconcileJobsC S T σ jobs).residue (objNode ⟨dt, on⟩ R) R = some res ∧
        s ∈ res.upos := by
  intro jobs
  induction jobs with
  | nil =>
    intro σ _ _ _ h
    rcases h with h | ⟨j, hj, _⟩
    · exact h
    · exact absurd hj List.not_mem_nil
  | cons j js ih =>
    intro σ hσ hv hcand h
    obtain ⟨jdt, jon, jR, je, jc, jn, ju⟩ := j
    obtain ⟨hRne, hcb, hcS, hnegS, huP, huS, hder, hlke, honj⟩ := hv _ List.mem_cons_self
    have hfold : reconcileJobsC S T σ (⟨jdt, jon, jR, je, jc, jn, ju⟩ :: js)
        = reconcileJobsC S T (W3cJob.apply S T σ ⟨jdt, jon, jR, je, jc, jn, ju⟩) js := by
      unfold reconcileJobsC; rw [List.foldl_cons]
    rw [hfold]
    have hstep : ReachedByW3c (W3cJob.apply S T σ ⟨jdt, jon, jR, je, jc, jn, ju⟩) S T :=
      ReachedByW3c.reconcileS jdt jon jR je jc jn ju hRne hcb hcS hnegS huP huS hder hlke honj hσ
    apply ih _ hstep (fun j' hj' => hv j' (List.mem_cons_of_mem _ hj'))
      (fun j' hj' => hcand j' (List.mem_cons_of_mem _ hj'))
    by_cases hkm : W3cJob.keyMatch ⟨jdt, jon, jR, je, jc, jn, ju⟩ dt on R
    · obtain ⟨h1, h2, h3⟩ := hkm
      have h1' : dt = jdt := h1.symm
      have h2' : on = jon := h2.symm
      have h3' : R = jR := h3.symm
      subst h1'; subst h2'; subst h3'
      have hje : e = je := by
        simp only at hlke
        exact Option.some.inj (hlk.symm.trans hlke)
      subst hje
      simp only at hder
      refine Or.inl ?_
      have hrow := reconcileStarsKey_residue_self σ T dt on R e (wildcardShapes S) jc jn ju
      rw [reconcileResidueKey_residue_self] at hrow
      refine ⟨_, hrow, ?_⟩
      refine List.mem_filter.mpr ⟨hcand _ List.mem_cons_self ⟨rfl, rfl, rfl⟩, ?_⟩
      have hchkS : σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
        checkFn_eq_sem_w3c hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm hσ hlk
          (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder) (fun hx => absurd hx hsstar) hon
      have hnc : ((wildcardShapes S).filter
          (fun sh => σ.coveredFn T dt on R e sh)).contains s.shape = false := by
        by_contra hc
        rw [Bool.not_eq_false, List.contains_eq_mem] at hc
        have hws := List.mem_of_mem_filter (of_decide_eq_true hc)
        exact hsu (hWSbare s.shape hws)
      rw [Bool.and_eq_true, hnc]
      exact ⟨rfl, by rw [hchkS, hsemT]⟩
    · have hne : ¬(objNode ⟨dt, on⟩ R = objNode ⟨jdt, jon⟩ jR ∧ R = jR) := by
        rintro ⟨hk, hRR⟩
        obtain ⟨e1, e2, _⟩ := objNode_inj_of_ne_star hon honj hk
        exact hkm ⟨e1.symm, e2.symm, hRR.symm⟩
      rcases h with ⟨res, hres, hmem⟩ | ⟨j', hj', hm⟩
      · refine Or.inl ⟨res, ?_, hmem⟩
        show (σ.reconcileStarsKey T jdt jon jR je (wildcardShapes S) jc jn ju).residue
          (objNode ⟨dt, on⟩ R) R = some res
        rw [reconcileStarsKey_residue_other hne]
        exact hres
      · rcases List.mem_cons.mp hj' with rfl | hj's
        · exact absurd hm hkm
        · exact Or.inr ⟨j', hj's, hm⟩

/-! ## The W3c-complete state and the assembly `graph_correct_w3c` -/

/-- The full derived read (`probeDerived`, `wildcard.py:398-432`), unfolded on explicit
    components at a concrete object: star ⇒ `stars`; bare ⇒ edge ∨ (`stars` ∖ `neg`);
    userset ⇒ `upos` ∨ (`stars` ∖ `neg`) (with the `stars` gate). -/
theorem probeDerived_eq (σ : GraphState) {st sn sp R dt on : String} (hon : on ≠ STAR) :
    GraphModel.probeDerived σ ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ =
      (if sn = STAR then
        ((σ.residue (objNode ⟨dt, on⟩ R) R).getD Residue.empty).stars.contains (st, sp)
      else if sp = BARE then
        σ.reach (subjNode ⟨st, sn, sp⟩) (objNode ⟨dt, on⟩ R)
          || (((σ.residue (objNode ⟨dt, on⟩ R) R).getD Residue.empty).stars.contains (st, sp)
              && !((σ.residue (objNode ⟨dt, on⟩ R) R).getD Residue.empty).neg.contains
                    ⟨st, sn, sp⟩)
      else if ((σ.residue (objNode ⟨dt, on⟩ R) R).getD Residue.empty).upos.contains
          ⟨st, sn, sp⟩ then true
      else if !((σ.residue (objNode ⟨dt, on⟩ R) R).getD Residue.empty).stars.contains
          (st, sp) then false
      else !((σ.residue (objNode ⟨dt, on⟩ R) R).getD Residue.empty).neg.contains
        ⟨st, sn, sp⟩) := by
  unfold GraphModel.probeDerived
  by_cases h1 : sn = STAR
  · simp [hon, h1, SubjectRef.shape]
  · by_cases h2 : sp = BARE <;> simp [hon, h1, h2, SubjectRef.shape]

/-- **`W3cComplete S T σ`** — an admitted rule-routed base plus a coverage-complete batch
    of full-object star reconcile jobs. Faithful to `build_index`/`reconcile`
    (`processor.py:382-459`): the processor reconciles every derived key over every
    object, re-deriving the full audit enumeration each pass. Coverage clauses are
    properties of the *enumeration*:

    * every `sem`-true bare star-free subject is in some covering job's edge `cands`;
    * every `sem`-true userset star-free subject is in EVERY targeting job's `uposCands`
      (and some job targets its key) — the wholesale-recompute condition;
    * every star-free subject with a declared `sem`-covered shape that is `sem`-false is
      in EVERY targeting job's `negCands`;
    * every key with a declared `sem`-covered shape is targeted by some job (row
      existence for the star read). -/
def W3cComplete (S : Schema) (T : Store) (σ : GraphState) : Prop :=
  ∃ (σ0 : GraphState) (jobs : List W3cJob),
    ReachedByRulesAdmitted σ0 S T ∧ σ = reconcileJobsC S T σ0 jobs ∧
    (∀ j ∈ jobs, W3cJobValid S j) ∧
    (∀ dt on R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ s : SubjectRef, s.predicate = BARE → s.name ≠ STAR → on ≠ STAR →
        sem S T ⟨s, R, ⟨dt, on⟩⟩ = true →
        ∃ j ∈ jobs, j.keyMatch dt on R ∧ s ∈ j.cands) ∧
    (∀ dt on R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ s : SubjectRef, s.predicate ≠ BARE → s.name ≠ STAR → on ≠ STAR →
        sem S T ⟨s, R, ⟨dt, on⟩⟩ = true →
        (∃ j ∈ jobs, j.keyMatch dt on R) ∧
        (∀ j ∈ jobs, j.keyMatch dt on R → s ∈ j.uposCands)) ∧
    (∀ dt on R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ s : SubjectRef, s.name ≠ STAR → on ≠ STAR →
        s.shape ∈ wildcardShapes S → sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true →
        sem S T ⟨s, R, ⟨dt, on⟩⟩ = false →
        ∀ j ∈ jobs, j.keyMatch dt on R → s ∈ j.negCands) ∧
    (∀ dt on R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ sh ∈ wildcardShapes S, on ≠ STAR →
        sem S T ⟨starSubj sh, R, ⟨dt, on⟩⟩ = true →
        ∃ j ∈ jobs, j.keyMatch dt on R)

/-- A W3c-complete state is W3c-reached. -/
theorem w3cComplete_reached {S : Schema} {T : Store} {σ : GraphState}
    (h : W3cComplete S T σ) : ReachedByW3c σ S T := by
  obtain ⟨σ0, jobs, h0, hσ, hv, _, _, _, _⟩ := h
  rw [hσ]
  exact reconcileJobsC_pres jobs σ0 (ReachedByW3c.base h0) hv

/-- **Edge completeness at W3c.** A `sem`-true, canonically-UNCOVERED bare star-free
    subject's derived edge is materialised: it survives the covering job's covered
    filter (its pass-start `stars` row is the canonical one), its guard is `sem`-true
    at every prefix mid-state (star-general inertness + the W3c bridge), the write is
    admitted at the terminal R-node, and edges persist through the batch. -/
theorem w3cComplete_derived_edge {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : W3cComplete S T σ)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hsb : s.predicate = BARE) (hss : s.name ≠ STAR) (hon : on ≠ STAR)
    (hnotcov : ¬(s.shape ∈ wildcardShapes S ∧
      sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true))
    (hsem : sem S T ⟨s, R, ⟨dt, on⟩⟩ = true) :
    (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges := by
  obtain ⟨σ0, jobs, h0, hσeq, hv, hcovE, _hcovU, _hcovN, _hrowEx⟩ := h
  obtain ⟨j, hj, hkm, hjs⟩ := hcovE dt on R e hlk hder s hsb hss hon hsem
  obtain ⟨jdt, jon, jR, je, jc, jn, ju⟩ := j
  obtain ⟨hRne, hjcb, hjcS, _hjnS, _hjuP, _hjuS, hjder, hjlke, hjon⟩ := hv _ hj
  obtain ⟨h1, h2, h3⟩ := hkm
  have h1' : dt = jdt := h1.symm
  have h2' : on = jon := h2.symm
  have h3' : R = jR := h3.symm
  subst h1'; subst h2'; subst h3'
  have hje : e = je := by
    simp only at hjlke
    exact Option.some.inj (hlk.symm.trans hjlke)
  subst hje
  simp only at hjs hjcb hjcS hjder
  -- split the batch at the covering job
  obtain ⟨pre, post, hsplit⟩ := List.append_of_mem hj
  have hσpre : ReachedByW3c (reconcileJobsC S T σ0 pre) S T := by
    refine reconcileJobsC_pres pre σ0 (ReachedByW3c.base h0) ?_
    intro j' hj'
    exact hv j' (hsplit ▸ List.mem_append_left _ hj')
  set σpre := reconcileJobsC S T σ0 pre with hσpre_def
  -- the residue half, then the covered-filter collapse
  set σ1 := σpre.reconcileResidueKey T dt on R e (wildcardShapes S) jn ju with hσ1
  have hσ1e : σ1.edges = σpre.edges := by rw [hσ1]; rfl
  have hσ1n : σ1.nodes = σpre.nodes := by rw [hσ1]; rfl
  have hcoll : W3cJob.apply S T σpre ⟨dt, on, R, e, jc, jn, ju⟩
      = σ1.reconcileKey T dt on R e
          (jc.filter (fun c => !(σ1.coveredAt (objNode ⟨dt, on⟩ R) R c.shape))) := by
    show σpre.reconcileStarsKey T dt on R e (wildcardShapes S) jc jn ju = _
    unfold GraphState.reconcileStarsKey
    rw [reconcileKeyC_eq_filter]
  -- R-node terminality at the pass start
  have hRns1 : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ1.edges := by
    have hns := reachedByW3c_Rnode_not_source hterm hRne hjder hσpre (on := on)
    intro y hy
    rw [hσ1e] at hy
    exact hns y hy
  have hcl1 : ∀ ab ∈ σ1.edges, ab.1 ∈ σ1.nodes ∧ ab.2 ∈ σ1.nodes := by
    have hec := reachedByW3c_edgesClosed hσpre
    intro ab hab
    rw [hσ1e] at hab
    rw [hσ1n]
    exact hec ab hab
  -- s is canonically uncovered, so it survives the covered filter
  have hcovAt : σ1.coveredAt (objNode ⟨dt, on⟩ R) R s.shape = false := by
    unfold GraphState.coveredAt
    rw [hσ1, reconcileResidueKey_residue_self]
    simp only [Option.getD_some]
    by_contra hc
    rw [Bool.not_eq_false, List.contains_eq_mem] at hc
    obtain ⟨hws, hcov⟩ := List.mem_filter.mp (of_decide_eq_true hc)
    refine hnotcov ⟨hws, ?_⟩
    rw [← checkFn_eq_sem_w3c (s := starSubj s.shape) hWF hTT hNK hR hSV hBS hTS hCO hMatch
      hStrat hterm hσpre hlk (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder)
      (fun _ => hWSbare s.shape hws) hon]
    exact hcov
  have hsfil : s ∈ jc.filter (fun c => !(σ1.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)) := by
    refine List.mem_filter.mpr ⟨hjs, ?_⟩
    rw [hcovAt]
    rfl
  have hfilbare : ∀ c ∈ jc.filter (fun c => !(σ1.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)),
      c.predicate = BARE := fun c hc => hjcb c (List.mem_of_mem_filter hc)
  -- guard: checkFn = sem = true at every prefix mid-state of the filtered fold
  have hguard : ∀ pre',
      pre' <+: jc.filter (fun c => !(σ1.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)) →
      (σ1.reconcileKey T dt on R e pre').checkFn T s dt on R e = true := by
    intro pre' hpre'
    have hpre_bare : ∀ x ∈ pre', x.predicate = BARE := fun x hx => hfilbare x (hpre'.subset hx)
    have hpre_star : ∀ x ∈ pre', x.name ≠ STAR := fun x hx =>
      hjcS x (List.mem_of_mem_filter (hpre'.subset hx))
    obtain ⟨σ', hσ', hcore⟩ := reachedByW3c_shadow hσpre
    have hcore1 : CoreEq σ' σ1 := by
      rw [hσ1]
      exact reconcileResidueKey_coreEq hcore T dt on R e (wildcardShapes S) jn ju
    have hmidAdm : ReachedByW3aAdmitted (σ'.reconcileKey T dt on R e pre') S T :=
      ReachedByW3aAdmitted.reconcile dt on R e pre' hRne hpre_bare hjder hlk hpre_star hjon hσ'
    have hcoremid : CoreEq (σ'.reconcileKey T dt on R e pre')
        (σ1.reconcileKey T dt on R e pre') := reconcileKey_coreEq pre' hcore1
    have hclmid : ∀ ab ∈ (σ1.reconcileKey T dt on R e pre').edges,
        ab.1 ∈ (σ1.reconcileKey T dt on R e pre').nodes
          ∧ ab.2 ∈ (σ1.reconcileKey T dt on R e pre').nodes := by
      have hInvm := (reachedByW3a_inv (reachedByW3aAdmitted_toW3a hmidAdm)).1
      intro ab hab
      rw [← hcoremid.edges] at hab
      rw [← hcoremid.nodes]
      exact hInvm.edgesClosed ab hab
    have hmidag : ∀ (x : SubjectRef) (r' : String), isDerived S (dt, r') = false →
        GraphModel.graphRec (σ1.reconcileKey T dt on R e pre') x dt on r'
          = GraphModel.graphRec σ1 x dt on r' :=
      fun x r' hunt => graphRec_reconcileKey_inert T dt on R e pre' hRne hpre_bare hRns1
        hjon hjder hcl1 hclmid x dt on r' hunt
    have hstep1 : (σ1.reconcileKey T dt on R e pre').checkFn T s dt on R e
        = σ1.checkFn T s dt on R e :=
      checkFn_agree_of_graphRec T s dt on R e (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder)
        (fun x' r' hr' => hmidag x' r' hr')
    have hstep2 : σ1.checkFn T s dt on R e = σpre.checkFn T s dt on R e :=
      checkFn_congr hσ1e hσ1n T s dt on R e
    have hstep3 : σpre.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
      checkFn_eq_sem_w3c hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat hterm hσpre hlk
        (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder) (fun hx => absurd hx hss) hon
    rw [hstep1, hstep2, hstep3]
    exact hsem
  -- the covering job materialises the edge; it persists through the tail
  have hedge_j : (subjNode s, objNode ⟨dt, on⟩ R)
      ∈ (W3cJob.apply S T σpre ⟨dt, on, R, e, jc, jn, ju⟩).edges := by
    rw [hcoll]
    exact reconcileKey_edge_present hRne _ σ1 hfilbare hsfil hRns1 hguard
  have hσeq2 : σ = reconcileJobsC S T (W3cJob.apply S T σpre ⟨dt, on, R, e, jc, jn, ju⟩) post := by
    rw [hσeq, hsplit, hσpre_def]
    unfold reconcileJobsC
    rw [List.foldl_append, List.foldl_cons]
  rw [hσeq2]
  exact reconcileJobsC_edges_mono post _ _ hedge_j

/-- **T2b, W3c fragment (`graph_correct_w3c`) — `check = sem` on star-CARRYING stores.**
    The query subject may be bare, star-BARE, or a userset; the store may hold bare
    `T:*` grants (`BareStarStore` + `TtuStarFree` replace `StarFreeStore`); the schema
    is the one-derived-stratum (`ComputedOnly`) fragment with bare-only declared wildcard shapes
    (`hWSbare`, decision-15).

    * **Untainted query:** shadow → admitted base → `graphRec_base_eq_bs`.
    * **Derived, star subject:** the `stars` read = declared ∧ `sem`-covered (row char);
      backward, the LINCHPIN turns `sem`-coverage into declaredness and the row-existence
      clause materialises the row.
    * **Derived, bare subject:** edge ∨ (`stars` ∖ `neg`): reach ⇒ single canonical edge ⇒
      `sem` (master + bridge); covered fallback sound by `neg` completeness; backward, a
      covered subject reads from the row (`neg` members are `sem`-false) and an uncovered
      one gets its edge (`w3cComplete_derived_edge`).
    * **Derived, userset subject:** its shape is never declared (`hWSbare`), so the read
      is exactly `upos` — sound by the row char, complete by `upos` completeness. -/
theorem graph_correct_w3c {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : W3cComplete S T σ)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem S T q := by
  have hadm := w3cComplete_reached h
  obtain ⟨hInv, _hQ⟩ := reachedByW3c_inv hWF hNK hSV hterm hCO hLU hadm
  have hcl := hInv.edgesClosed
  obtain ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ := q
  replace hqs : sn = STAR → sp = BARE := hqs
  replace hqo : on ≠ STAR := hqo
  by_cases hder : isDerived S (dt, R) = true
  · -- ===== derived query: the residue read =====
    obtain ⟨e, hlk⟩ := isDerived_declared hder
    have hco := hCO _ _ _ hlk hder
    have hleafUnt := hLU _ _ _ hlk hder
    have hroute : GraphModel.check σ ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
        = GraphModel.probeDerived σ ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ := by
      unfold GraphModel.check
      rw [hInv.schemaEq]
      simp [hder]
    rw [hroute, probeDerived_eq σ hqo]
    -- reach ⇒ sem for star-free subjects (row-independent: master's canonical edge)
    have hreach_sem : sn ≠ STAR →
        σ.reach (subjNode ⟨st, sn, sp⟩) (objNode ⟨dt, on⟩ R) = true →
        sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ = true := by
      intro hsn hr
      obtain ⟨σsh, hσsh, hcore⟩ := reachedByW3c_shadow hadm
      have hN : NReaches σsh.edges (subjNode ⟨st, sn, sp⟩) (objNode ⟨dt, on⟩ R) := by
        rw [hcore.edges]
        exact reach_sound hr
      have hedge1 := reachedByW3a_reach_collapse_root hWF hSV hlk hder hco
        (reachedByW3aAdmitted_toW3a hσsh) hN
      rw [hcore.edges] at hedge1
      obtain ⟨σ0, hσ0, _hag2, _hres2, hedge⟩ := reachedByW3c_master hterm hCO hLU hadm
      rcases hedge dt on R e hder hlk hqo _ hedge1 with hbase | ⟨c, huc, _hcb, hcS, _hunc, hchk⟩
      · exact absurd hbase (reachedByRules_derived_no_inedge hSV hlk hder hco
          (reachedByRules_of_admitted hσ0) _)
      · have hcs : (⟨st, sn, sp⟩ : SubjectRef) = c := subjNode_inj_of_ne_star hsn hcS huc
        rw [← checkFn_eq_sem_bs (s := (⟨st, sn, sp⟩ : SubjectRef)) hWF hTT hNK hR hSV hBS hTS
          hCO hMatch hStrat hterm (ReachedByW3aAdmitted.base hσ0) hlk hco hleafUnt
          (fun hx => absurd hx hsn) hqo]
        rw [hcs]
        exact hchk
    -- W3cComplete pieces (keep `h` intact for the edge-completeness call)
    have hW := h
    obtain ⟨σ0B, jobs, h0B, hσB, hvjobs, _hcovE, hcovU, hcovN, hrowEx⟩ := hW
    by_cases hstar : sn = STAR
    · -- ---- star subject: the `stars` read ----
      subst hstar
      have hsp : sp = BARE := hqs rfl
      subst hsp
      rw [if_pos rfl]
      have hsem_ws : sem S T ⟨⟨st, STAR, BARE⟩, R, ⟨dt, on⟩⟩ = true →
          (st, BARE) ∈ wildcardShapes S := by
        intro hsm
        refine coveredFn_declared hTT hSV hTS h0B hco (dt := dt) (on := on) (R := R) ?_
        show σ0B.checkFn T (starSubj (st, BARE)) dt on R e = true
        rw [checkFn_eq_sem_bs (s := starSubj (st, BARE)) hWF hTT hNK hR hSV hBS hTS hCO
          hMatch hStrat hterm (ReachedByW3aAdmitted.base h0B) hlk hco hleafUnt
          (fun _ => rfl) hqo]
        exact hsm
      cases hrow : σ.residue (objNode ⟨dt, on⟩ R) R with
      | none =>
        rw [Option.getD_none]
        cases hsm : sem S T ⟨⟨st, STAR, BARE⟩, R, ⟨dt, on⟩⟩
        · rfl
        · exfalso
          obtain ⟨j, hj, hkm⟩ := hrowEx dt on R e hlk hder (st, BARE) (hsem_ws hsm) hqo hsm
          have hsome := reconcileJobsC_row_isSome (S := S) (T := T) jobs σ0B
            (Or.inr ⟨j, hj, hkm⟩)
          rw [← hσB, hrow] at hsome
          exact absurd hsome (by decide)
      | some res =>
        rw [Option.getD_some]
        have hchar := w3c_row_char hWF hTT hNK hR hSV hBS hTS hMatch hStrat hterm
          hCO hLU hWSbare hadm hlk hqo hrow
        cases hc : res.stars.contains (st, BARE) <;>
          cases hsm : sem S T ⟨⟨st, STAR, BARE⟩, R, ⟨dt, on⟩⟩
        · rfl
        · exfalso
          have hcontains := (hchar.1 (st, BARE)).mpr ⟨hsem_ws hsm, hsm⟩
          rw [hc] at hcontains
          exact absurd hcontains (by decide)
        · exfalso
          obtain ⟨_, hs⟩ := (hchar.1 (st, BARE)).mp hc
          have hs' : sem S T ⟨⟨st, STAR, BARE⟩, R, ⟨dt, on⟩⟩ = true := hs
          rw [hsm] at hs'
          exact absurd hs' (by decide)
        · rfl
    · -- star-free subject
      rw [if_neg hstar]
      by_cases hbare : sp = BARE
      · -- ---- bare subject: edge ∨ (stars ∖ neg) ----
        subst hbare
        rw [if_pos rfl]
        cases hrow : σ.residue (objNode ⟨dt, on⟩ R) R with
        | none =>
          rw [Option.getD_none]
          have hsimp : (Residue.empty.stars.contains (st, BARE) &&
              !Residue.empty.neg.contains ⟨st, sn, BARE⟩) = false := rfl
          rw [hsimp, Bool.or_false]
          cases hr : σ.reach (subjNode ⟨st, sn, BARE⟩) (objNode ⟨dt, on⟩ R) <;>
            cases hsm : sem S T ⟨⟨st, sn, BARE⟩, R, ⟨dt, on⟩⟩
          · rfl
          · exfalso
            by_cases hcov : (st, BARE) ∈ wildcardShapes S ∧
                sem S T ⟨starSubj (st, BARE), R, ⟨dt, on⟩⟩ = true
            · obtain ⟨j, hj, hkm⟩ := hrowEx dt on R e hlk hder (st, BARE) hcov.1 hqo hcov.2
              have hsome := reconcileJobsC_row_isSome (S := S) (T := T) jobs σ0B
                (Or.inr ⟨j, hj, hkm⟩)
              rw [← hσB, hrow] at hsome
              exact absurd hsome (by decide)
            · have hedge := w3cComplete_derived_edge (s := ⟨st, sn, BARE⟩) hWF hTT hNK hR hSV
                hBS hTS hMatch hStrat hterm hCO hLU hWSbare h hlk hder rfl hstar hqo
                hcov hsm
              have hrc := reach_complete hcl (NReaches.edge hedge)
              rw [hr] at hrc
              exact absurd hrc (by decide)
          · exfalso
            have hsemT := hreach_sem hstar hr
            rw [hsm] at hsemT
            exact absurd hsemT (by decide)
          · rfl
        | some res =>
          rw [Option.getD_some]
          have hchar := w3c_row_char hWF hTT hNK hR hSV hBS hTS hMatch hStrat hterm
            hCO hLU hWSbare hadm hlk hqo hrow
          have hfwd : (σ.reach (subjNode ⟨st, sn, BARE⟩) (objNode ⟨dt, on⟩ R)
              || (res.stars.contains (st, BARE) && !res.neg.contains ⟨st, sn, BARE⟩)) = true →
              sem S T ⟨⟨st, sn, BARE⟩, R, ⟨dt, on⟩⟩ = true := by
            intro hread
            rw [Bool.or_eq_true, Bool.and_eq_true] at hread
            rcases hread with hr | ⟨hcS, hnN⟩
            · exact hreach_sem hstar hr
            · by_contra hsm
              rw [Bool.not_eq_true] at hsm
              obtain ⟨hws, hsemStar⟩ := (hchar.1 (st, BARE)).mp hcS
              have hall := hcovN dt on R e hlk hder ⟨st, sn, BARE⟩ hstar hqo hws hsemStar hsm
              obtain ⟨j, hj, hkm⟩ := hrowEx dt on R e hlk hder (st, BARE) hws hqo hsemStar
              obtain ⟨res', hres', hmem⟩ := reconcileJobsC_neg_complete
                (s := ⟨st, sn, BARE⟩) hWF hTT hNK hR hSV hBS
                hTS hMatch hStrat hterm hCO hLU hWSbare hlk hstar hqo hws hsemStar hsm
                jobs σ0B (ReachedByW3c.base h0B) hvjobs hall (Or.inr ⟨j, hj, hkm⟩)
              rw [← hσB, hrow] at hres'
              obtain rfl := Option.some.inj hres'
              have hcont : res.neg.contains ⟨st, sn, BARE⟩ = true := by
                rw [List.contains_eq_mem]
                exact decide_eq_true hmem
              rw [hcont] at hnN
              exact absurd hnN (by decide)
          have hbwd : sem S T ⟨⟨st, sn, BARE⟩, R, ⟨dt, on⟩⟩ = true →
              (σ.reach (subjNode ⟨st, sn, BARE⟩) (objNode ⟨dt, on⟩ R)
                || (res.stars.contains (st, BARE) && !res.neg.contains ⟨st, sn, BARE⟩)) = true := by
            intro hsm
            rw [Bool.or_eq_true, Bool.and_eq_true]
            by_cases hcov : (st, BARE) ∈ wildcardShapes S ∧
                sem S T ⟨starSubj (st, BARE), R, ⟨dt, on⟩⟩ = true
            · refine Or.inr ⟨(hchar.1 (st, BARE)).mpr hcov, ?_⟩
              cases hcnt : res.neg.contains ⟨st, sn, BARE⟩
              · rfl
              · exfalso
                have hmem : (⟨st, sn, BARE⟩ : SubjectRef) ∈ res.neg := by
                  rw [List.contains_eq_mem] at hcnt
                  exact of_decide_eq_true hcnt
                obtain ⟨_, hsemF⟩ := hchar.2.1 _ hmem
                rw [hsm] at hsemF
                exact absurd hsemF (by decide)
            · exact Or.inl (reach_complete hcl (NReaches.edge
                (w3cComplete_derived_edge (s := ⟨st, sn, BARE⟩) hWF hTT hNK hR hSV hBS hTS
                  hMatch hStrat hterm hCO hLU hWSbare h hlk hder rfl hstar hqo hcov
                  hsm)))
          cases hread : (σ.reach (subjNode ⟨st, sn, BARE⟩) (objNode ⟨dt, on⟩ R)
              || (res.stars.contains (st, BARE) && !res.neg.contains ⟨st, sn, BARE⟩)) <;>
            cases hsm : sem S T ⟨⟨st, sn, BARE⟩, R, ⟨dt, on⟩⟩
          · rfl
          · exfalso
            have := hbwd hsm
            rw [hread] at this
            exact absurd this (by decide)
          · exfalso
            have := hfwd hread
            rw [hsm] at this
            exact absurd this (by decide)
          · rfl
      · -- ---- userset subject: the `upos` read (its shape is never declared) ----
        rw [if_neg hbare]
        cases hrow : σ.residue (objNode ⟨dt, on⟩ R) R with
        | none =>
          rw [Option.getD_none]
          show false = sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
          cases hsm : sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
          · rfl
          · exfalso
            obtain ⟨⟨j, hj, hkm⟩, hall⟩ := hcovU dt on R e hlk hder ⟨st, sn, sp⟩ hbare hstar
              hqo hsm
            obtain ⟨res', hres', _⟩ := reconcileJobsC_upos_complete hWF hTT hNK hR hSV hBS hTS
              hMatch hStrat hterm hCO hLU hWSbare hlk hbare hstar hqo hsm jobs σ0B
              (ReachedByW3c.base h0B) hvjobs hall (Or.inr ⟨j, hj, hkm⟩)
            rw [← hσB, hrow] at hres'
            cases hres'
        | some res =>
          rw [Option.getD_some]
          have hchar := w3c_row_char hWF hTT hNK hR hSV hBS hTS hMatch hStrat hterm
            hCO hLU hWSbare hadm hlk hqo hrow
          have hns : res.stars.contains (st, sp) = false := by
            by_contra hcx
            rw [Bool.not_eq_false] at hcx
            obtain ⟨hws, _⟩ := (hchar.1 (st, sp)).mp hcx
            exact hbare (hWSbare (st, sp) hws)
          rw [hns]
          show (if res.upos.contains ⟨st, sn, sp⟩ = true then true else false)
              = sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
          cases hu : res.upos.contains ⟨st, sn, sp⟩ <;>
            cases hsm : sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
          · rfl
          · exfalso
            obtain ⟨⟨j, hj, hkm⟩, hall⟩ := hcovU dt on R e hlk hder ⟨st, sn, sp⟩ hbare hstar
              hqo hsm
            obtain ⟨res', hres', hmem⟩ := reconcileJobsC_upos_complete hWF hTT hNK hR hSV hBS
              hTS hMatch hStrat hterm hCO hLU hWSbare hlk hbare hstar hqo hsm jobs σ0B
              (ReachedByW3c.base h0B) hvjobs hall (Or.inr ⟨j, hj, hkm⟩)
            rw [← hσB, hrow] at hres'
            obtain rfl := Option.some.inj hres'
            have hcontains : res.upos.contains ⟨st, sn, sp⟩ = true := by
              rw [List.contains_eq_mem]
              exact decide_eq_true hmem
            rw [hu] at hcontains
            exact absurd hcontains (by decide)
          · exfalso
            have hmem : (⟨st, sn, sp⟩ : SubjectRef) ∈ res.upos := by
              rw [List.contains_eq_mem] at hu
              exact of_decide_eq_true hu
            obtain ⟨_, _, hsemT⟩ := hchar.2.2 _ hmem
            rw [hsm] at hsemT
            exact absurd hsemT (by decide)
          · rfl
  · -- ===== untainted query: shadow → admitted base → star-relaxed base equation =====
    have hd : isDerived S (dt, R) = false := by simpa using hder
    have hroute : GraphModel.check σ ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
        = GraphModel.probeNonDerived σ ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ := by
      unfold GraphModel.check
      rw [hInv.schemaEq]
      simp [hd]
    rw [hroute]
    obtain ⟨σsh, hσsh, hcore⟩ := reachedByW3c_shadow hadm
    obtain ⟨σ0, hσ0adm, hredx⟩ := graphRec_reduce_base_adm_bs hterm hσsh
      (s := ⟨st, sn, sp⟩) (dt := dt) (on := on)
    have h2 := hredx R hd
    have h3 := graphRec_base_eq_bs hWF hTT hNK hR hSV hBS hTS hCO hMatch hσ0adm
      (s := ⟨st, sn, sp⟩) (dt := dt) (on := on) hqs hqo R hd
    calc GraphModel.probeNonDerived σ ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
        = GraphModel.probeNonDerived σsh ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ :=
          (probeNonDerived_congr hcore.edges hcore.nodes _).symm
      _ = GraphModel.graphRec σsh ⟨st, sn, sp⟩ dt on R := rfl
      _ = GraphModel.graphRec σ0 ⟨st, sn, sp⟩ dt on R := h2
      _ = sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ := h3

end Zanzibar
