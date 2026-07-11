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
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
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
    checkFn_eq_sem_bs hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm
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
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
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
        checkFn_eq_sem_w3c hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hσ hlk
          (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder) (fun hx => absurd hx hsstar) hon
      have hcovS : σ.coveredFn T dt on R e s.shape = true := by
        show σ.checkFn T (starSubj s.shape) dt on R e = true
        rw [checkFn_eq_sem_w3c (s := starSubj s.shape) hWF hTT hNK hR hSV hBS hTS hRootB
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
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
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
        checkFn_eq_sem_w3c hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm hσ hlk
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

end Zanzibar
