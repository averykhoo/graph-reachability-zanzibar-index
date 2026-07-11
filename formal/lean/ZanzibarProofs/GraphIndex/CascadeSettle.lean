import ZanzibarProofs.GraphIndex.CascadeStable

/-!
# Targeted-key re-settlement, the settledness invariant, and `graph_correct_w3d` (ROADMAP W3d-1b, final leg)

`index_v4/processor.py:382-459` (`reconcile` — the per-key wholesale pass), `:394-441`
(the audit enumeration: `_leaf_concretes` ∪ persisted incoming R-node concretes),
`run_cascade` (`:694-740`). This file closes W3d-1b:

* **`ReachedByW3dC`** — the coverage chain: `ReachedByW3d` with each cascade leg
  additionally carrying the per-job audit-enumeration coverage clauses
  (`W3dJobCoverage`). In Python these are properties of `reconcile`'s enumeration
  (every persisted edge holder and every store-supported subject is re-enumerated by
  EVERY pass); here they are chain-side hypotheses — proving them about a modeled
  enumeration is W3d-1c.
* **Targeted-key RE-settlement** (`settledComplete_cascade_targeted`): a cascade leg
  re-establishes `SettledKey` + `CompleteKey` at every key one of its jobs targets —
  the last targeting job wholesale-rewrites the row and diff-audits the edges, with
  every filter guard read at its mid-batch state where `checkFn = sem` (the W3d read
  bridge holds mid-batch).
* **The settledness invariant** (`reachedByW3dC_settled`): at every W3dC state, every
  declared derived key is dirty (`∈ cascadeKeys`) or settled+complete.
* **`graph_correct_w3d`**: `check = sem` at every fully-drained (`cascadeKeys = []`)
  W3dC state — the W3d T2b.

**Attack-first (2026-07-11h, machine-checked `#eval` vs the real `writeLoggedRules`/
`runCascade`/`check`/`sem`; scratch deleted).** The NEW edge-holder coverage clause
(`j.cands ⊇ pre-leg edge holders at j's key` — Python's audit enumerates persisted
incoming R-node concretes, `processor.py:394-441`) was attacked both ways on
`viewer := member ∖ banned`:
* **Refutation without the clause, CONFIRMED live**: `write member(alice) → cascade →
  write banned(alice) → cascade with cands = []` reaches a FULLY-DRAINED state
  (`cascadeKeys = []`) with `check = true ≠ sem = false` — the diffing pass keeps a
  non-candidate's stale edge (`reconcileKeyD_edge_char`'s second disjunct), so
  re-settlement genuinely needs the pre-leg holders enumerated.
* With the clause satisfied (`cands = [alice]`) the same chain reads `check = sem`.
* A job missing an EARLIER same-leg job's added edge is benign (the added edge carried
  a `sem`-true guard): `write member(alice) → cascade → write member(bob) → cascade
  with cands = [bob]` stays correct — the clause is about STALE holders; the ∀-holders
  form is what Python's enumeration actually provides.
-/

namespace Zanzibar

/-! ## Chain-level structure — schema fixity, edge-target discipline -/

/-- The `writeDirect` fold keeps the baked-in schema. -/
theorem foldl_writeDirect_schema (us : List Tuple) :
    ∀ (σ : GraphState), (us.foldl (fun acc u => acc.writeDirect u) σ).schema = σ.schema := by
  induction us with
  | nil => intro σ; rfl
  | cons u rest ih =>
    intro σ
    simp only [List.foldl_cons]
    rw [ih, writeDirect_schema]

/-- The diffing batch keeps the baked-in schema. -/
theorem reconcileJobsD_schema {S : Schema} {T : Store} :
    ∀ (jobs : List W3cJob) (σ : GraphState), (reconcileJobsD S T σ jobs).schema = σ.schema := by
  intro jobs
  induction jobs with
  | nil => intro σ; rfl
  | cons j rest ih =>
    intro σ
    have hfold : reconcileJobsD S T σ (j :: rest)
        = reconcileJobsD S T (j.applyD S T σ) rest := by
      unfold reconcileJobsD
      rw [List.foldl_cons]
    rw [hfold, ih]
    unfold W3cJob.applyD GraphState.reconcileStarsKeyD
    rw [reconcileKeyD_schema, reconcileResidueKey_schema]

/-- **Every W3d state carries its own schema** — the read's `isDerived` routing reads
    the right `S`. -/
theorem reachedByW3d_schema {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d σ S T) : σ.schema = S := by
  induction h with
  | empty S => rfl
  | @write σp S T t hadm hprev ih =>
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).schema]
    show ((rewriteClosure S t).foldl (fun acc u => acc.writeDirect u) σp).schema = S
    rw [foldl_writeDirect_schema]
    exact ih
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    rcases runCascade_cases S T σp jobs with hrc | hrc
    · rw [hrc]
      show (reconcileJobsL S T σp jobs).schema = S
      rw [(reconcileJobsL_evalEq (EvalEq.refl σp) S T jobs).schema, reconcileJobsD_schema]
      exact ih
    · rw [hrc]
      exact ih

/-- **Every W3d edge target has a non-`BARE` predicate** (the W3d analog of
    `reachedByW3a_edge_target_ne_bare`): routed targets carry declared relations,
    cascade targets carry the job's derived `R ≠ BARE`. Store hypotheses right of the
    colon, prefix-weakened. -/
theorem reachedByW3d_edge_target_ne_bare {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d σ S T) :
    WF S → StoreValidRules S T → ∀ a b, (a, b) ∈ σ.edges → b.pred ≠ BARE := by
  induction h with
  | empty S =>
    intro _ _ a b hab
    simp [emptyState] at hab
  | @write σp S T t hadm hprev ih =>
    intro hWF hSV a b hab
    rw [(writeLoggedRules_evalEq (EvalEq.refl σp) S t).edges] at hab
    rcases foldl_writeDirect_edges_sound (rewriteClosure S t) hab with hold | ⟨u, hu, _, h2⟩
    · exact ih hWF (fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')) a b hold
    · rw [h2, objNode_pred]
      exact rewriteClosure_rel_ne_bare hWF hSV List.mem_cons_self hu
  | @cascade σp S T jobs hjv hcover hscope hprev ih =>
    intro hWF hSV a b hab
    rcases runCascade_cases S T σp jobs with hrc | hrc
    · rw [hrc] at hab
      have hab' : (a, b) ∈ (reconcileJobsL S T σp jobs).edges := hab
      rw [(reconcileJobsL_evalEq (EvalEq.refl σp) S T jobs).edges] at hab'
      rcases reconcileJobsD_edge_sound jobs σp a b hab' with hold | ⟨j, hj, c, _, _, h2⟩
      · exact ih hWF hSV a b hold
      · obtain ⟨hRne, _⟩ := hjv j hj
        rw [h2, objNode_pred]
        exact hRne
    · rw [hrc] at hab
      exact ih hWF hSV a b hab

/-- A `BARE`-predicate node is never an edge target on a W3d state. -/
theorem reachedByW3d_bareNode_no_inedge {σ : GraphState} {S : Schema} {T : Store}
    (hWF : WF S) (hSV : StoreValidRules S T) (h : ReachedByW3d σ S T)
    {k : NodeKey} (hk : k.pred = BARE) : ∀ x, (x, k) ∉ σ.edges := by
  intro x hxk
  exact reachedByW3d_edge_target_ne_bare h hWF hSV x k hxk hk

/-- **Every in-edge source at a `RootBoolean` derived R-node is bare** on a W3d state:
    write legs never land there (model-level I5, as in `writeLeg_derived_inedges_eq`),
    cascade edges are sourced at bare candidates. -/
theorem reachedByW3d_Rnode_source_bare {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {e : Expr}
    (h : ReachedByW3d σ S T) :
    NodupKeys S → S.lookup (dt, R) = some e → RootBoolean e → StoreValidRules S T →
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∈ σ.edges → x.pred = BARE := by
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
      · obtain ⟨_, hcb, _⟩ := hjv j hj
        rw [h1, subjNode_pred]
        exact hcb c hc
    · rw [hrc] at hx
      exact ih hNK hlk hroot hSV x hx

/-- **The W3d reach collapse at a `RootBoolean` derived R-node**: any path into the
    R-node is a single edge — in-edge sources are bare, and bare nodes have no
    in-edges (the W3d analog of `reachedByW3a_reach_collapse_root`). -/
theorem reachedByW3d_reach_collapse_root {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {e : Expr} {u : NodeKey}
    (hWF : WF S) (hSV : StoreValidRules S T) (hNK : NodupKeys S)
    (hlk : S.lookup (dt, R) = some e) (hroot : RootBoolean e)
    (h : ReachedByW3d σ S T)
    (hr : NReaches σ.edges u (objNode ⟨dt, on⟩ R)) :
    (u, objNode ⟨dt, on⟩ R) ∈ σ.edges := by
  refine nreaches_collapse_of_source_notarget ?_ hr
  intro x hxv
  exact reachedByW3d_bareNode_no_inedge hWF hSV h
    (reachedByW3d_Rnode_source_bare h hNK hlk hroot hSV x hxv)

/-! ## The coverage chain `ReachedByW3dC` (decision: wrapper, not a constructor change)

`reconcile`'s audit enumeration (`processor.py:394-441`) re-derives, on EVERY pass:
the store-supported concretes of every leaf (`_leaf_concretes`), the persisted
incoming R-node concretes (the edge holders), and the persisted `neg`/`upos` members.
The four clauses below are the `sem`-level content of that enumeration, carried as
chain-side hypotheses on each cascade leg (proving them about a modeled enumeration
is W3d-1c). `ReachedByW3d` keeps its lean shape — everything proved over it
transfers through the projection. -/

/-- **Per-job audit-enumeration coverage** (relative to the leg-start state `σ` and
    the store `T`): the job's edge candidates include every pre-leg edge holder at
    its key (the attack-confirmed stale-holder clause) and every `sem`-true bare
    star-free subject; its `negCands` include every covered-but-`sem`-false star-free
    subject; its `uposCands` include every `sem`-true star-free userset subject. -/
def W3dJobCoverage (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) : Prop :=
  (∀ s : SubjectRef, (subjNode s, objNode ⟨j.dt, j.on⟩ j.R) ∈ σ.edges → s ∈ j.cands) ∧
  (∀ s : SubjectRef, s.predicate = BARE → s.name ≠ STAR →
    sem S T ⟨s, j.R, ⟨j.dt, j.on⟩⟩ = true → s ∈ j.cands) ∧
  (∀ s : SubjectRef, s.name ≠ STAR → s.shape ∈ wildcardShapes S →
    sem S T ⟨starSubj s.shape, j.R, ⟨j.dt, j.on⟩⟩ = true →
    sem S T ⟨s, j.R, ⟨j.dt, j.on⟩⟩ = false → s ∈ j.negCands) ∧
  (∀ s : SubjectRef, s.predicate ≠ BARE → s.name ≠ STAR →
    sem S T ⟨s, j.R, ⟨j.dt, j.on⟩⟩ = true → s ∈ j.uposCands)

/-- **`ReachedByW3dC`** — the W3d scheduler closure with coverage-complete cascade
    legs: `ReachedByW3d` plus, per cascade, `W3dJobCoverage` for every job. -/
inductive ReachedByW3dC : GraphState → Schema → Store → Prop where
  | empty (S : Schema) : ReachedByW3dC (emptyState S) S []
  | write {σ : GraphState} {S : Schema} {T : Store} (t : Tuple)
      (hadm : FoldAdmits σ (rewriteClosure S t))
      (hprev : ReachedByW3dC σ S T) :
      ReachedByW3dC (σ.writeLoggedRules S t) S (t :: T)
  | cascade {σ : GraphState} {S : Schema} {T : Store} (jobs : List W3cJob)
      (hjv : ∀ j ∈ jobs, W3cJobValid S j)
      (hcover : ∀ k ∈ cascadeKeys S σ, ∃ j ∈ jobs, j.key = k)
      (hscope : ∀ j ∈ jobs, j.key ∈ cascadeKeys S σ)
      (hcovg : ∀ j ∈ jobs, W3dJobCoverage S T σ j)
      (hprev : ReachedByW3dC σ S T) :
      ReachedByW3dC (runCascade S T σ jobs) S T

/-- The projection: every coverage-chain state is a plain W3d state — ALL W3d
    theorems (shadow, bridge, fan-out completeness, transports) apply. -/
theorem reachedByW3dC_toW3d {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3dC σ S T) : ReachedByW3d σ S T := by
  induction h with
  | empty S => exact ReachedByW3d.empty S
  | write t hadm _ ih => exact ReachedByW3d.write t hadm ih
  | cascade jobs hjv hcover hscope _ _ ih =>
    exact ReachedByW3d.cascade jobs hjv hcover hscope ih

/-! ## `CompleteKey` — the completeness half of per-key settledness

`SettledKey` (CascadeStable) is the soundness half: what IS materialised carries its
`sem` verdict. `CompleteKey` is the converse: everything `sem`-true at the key is
readable — mirroring `W3cComplete`'s clause shapes, per key. -/

/-- Everything `sem`-true at the derived key is materialised: the row exists when a
    declared shape is `sem`-covered; an UNCOVERED `sem`-true bare star-free subject
    has its edge; a `sem`-true star-free userset is in `upos`; a covered-but-
    `sem`-false star-free subject is in `neg` (the exclusion actually excludes). -/
def CompleteKey (S : Schema) (T : Store) (σ : GraphState) (dt on R : String) : Prop :=
  (∀ sh ∈ wildcardShapes S, sem S T ⟨starSubj sh, R, ⟨dt, on⟩⟩ = true →
    (σ.residue (objNode ⟨dt, on⟩ R) R).isSome = true) ∧
  (∀ s : SubjectRef, s.predicate = BARE → s.name ≠ STAR →
    sem S T ⟨s, R, ⟨dt, on⟩⟩ = true →
    ¬(s.shape ∈ wildcardShapes S ∧ sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true) →
    (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges) ∧
  (∀ s : SubjectRef, s.predicate ≠ BARE → s.name ≠ STAR →
    sem S T ⟨s, R, ⟨dt, on⟩⟩ = true →
    ∃ res, σ.residue (objNode ⟨dt, on⟩ R) R = some res ∧ s ∈ res.upos) ∧
  (∀ s : SubjectRef, s.name ≠ STAR → s.shape ∈ wildcardShapes S →
    sem S T ⟨starSubj s.shape, R, ⟨dt, on⟩⟩ = true → sem S T ⟨s, R, ⟨dt, on⟩⟩ = false →
    ∃ res, σ.residue (objNode ⟨dt, on⟩ R) R = some res ∧ s ∈ res.neg)

/-- Settledness reads only residue and edges — congruence for the
    `runCascade`-accept record update and `EvalEq` transfers. -/
theorem settledKey_congr {S : Schema} {T : Store} {σ' σ : GraphState}
    (hres : σ'.residue = σ.residue) (hedge : σ'.edges = σ.edges) {dt on R : String}
    (h : SettledKey S T σ dt on R) : SettledKey S T σ' dt on R := by
  obtain ⟨hrow, hedgeH⟩ := h
  constructor
  · intro res hres'
    rw [hres] at hres'
    exact hrow res hres'
  · intro s hb hstar he
    rw [hedge] at he
    exact hedgeH s hb hstar he

/-- `CompleteKey` congruence on residue/edges. -/
theorem completeKey_congr {S : Schema} {T : Store} {σ' σ : GraphState}
    (hres : σ'.residue = σ.residue) (hedge : σ'.edges = σ.edges) {dt on R : String}
    (h : CompleteKey S T σ dt on R) : CompleteKey S T σ' dt on R := by
  obtain ⟨hrowE, hedgeC, huposC, hnegC⟩ := h
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro sh hws hsm
    rw [hres]
    exact hrowE sh hws hsm
  · intro s hb hstar hsm hnc
    rw [hedge]
    exact hedgeC s hb hstar hsm hnc
  · intro s hu hstar hsm
    rw [hres]
    exact huposC s hu hstar hsm
  · intro s hstar hws hsemStar hsemF
    rw [hres]
    exact hnegC s hstar hws hsemStar hsemF

/-! ## `CompleteKey` transports — write legs at unmapped keys, cascades at untargeted keys -/

/-- **`CompleteKey` transports across a write leg at an unmapped key** — the
    representation is untouched and the key's `sem` is unchanged
    (`writeLeg_sem_stable`), mirroring `settledKey_writeLeg`. -/
theorem completeKey_writeLeg {σ : GraphState} {S : Schema} {T : Store} {t : Tuple}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S (t :: T)) (hBS : BareStarStore (t :: T))
    (hTS : TtuStarFree S (t :: T))
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR (t :: T) R)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d σ S T) (hadm : FoldAdmits σ (rewriteClosure S t))
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t))
    (hon : on ≠ STAR)
    (hcomp : CompleteKey S T σ dt on R) :
    CompleteKey S (t :: T) (σ.writeLoggedRules S t) dt on R := by
  obtain ⟨hrowE, hedgeC, huposC, hnegC⟩ := hcomp
  have hroot : RootBoolean e := hRootB ⟨(dt, R), e⟩ (mem_defs_of_lookup hlk) hder
  have hsem : ∀ s : SubjectRef, (s.name = STAR → s.predicate = BARE) →
      sem S (t :: T) ⟨s, R, ⟨dt, on⟩⟩ = sem S T ⟨s, R, ⟨dt, on⟩⟩ :=
    fun s hs => writeLeg_sem_stable hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat
      hterm h hadm hlk hder hco hleafUnt hunmapped hs hon
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro sh hws hsm
    rw [writeLoggedRules_residue]
    refine hrowE sh hws ?_
    rw [← hsem (starSubj sh) (fun _ => hWSbare sh hws)]
    exact hsm
  · intro s hb hstar hsm hnc
    rw [writeLeg_derived_inedges_eq hNK hSV hlk hroot (subjNode s)]
    refine hedgeC s hb hstar ?_ ?_
    · rw [← hsem s (fun hx => absurd hx hstar)]
      exact hsm
    · rintro ⟨hws, hsemstar⟩
      refine hnc ⟨hws, ?_⟩
      rw [hsem (starSubj s.shape) (fun _ => hWSbare _ hws)]
      exact hsemstar
  · intro s hu hstar hsm
    rw [writeLoggedRules_residue]
    refine huposC s hu hstar ?_
    rw [← hsem s (fun hx => absurd hx hstar)]
    exact hsm
  · intro s hstar hws hsemStar hsemF
    rw [writeLoggedRules_residue]
    refine hnegC s hstar hws ?_ ?_
    · rw [← hsem (starSubj s.shape) (fun _ => hWSbare _ hws)]
      exact hsemStar
    · rw [← hsem s (fun hx => absurd hx hstar)]
      exact hsemF

/-- **`CompleteKey` is untouched by a cascade at untargeted keys** — the store (hence
    `sem`) is unchanged, and the passes touch only their own keys' rows/in-edges. -/
theorem completeKey_cascade_untargeted {S : Schema} {T : Store} {σ : GraphState}
    {jobs : List W3cJob} {dt on R : String}
    (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (hnot : ∀ j ∈ jobs, ¬ j.keyMatch dt on R) (hon : on ≠ STAR)
    (hcomp : CompleteKey S T σ dt on R) :
    CompleteKey S T (runCascade S T σ jobs) dt on R := by
  rcases runCascade_cases S T σ jobs with hrc | hrc
  · rw [hrc]
    have hev := reconcileJobsL_evalEq (EvalEq.refl σ) S T jobs
    obtain ⟨hres, hedges⟩ := reconcileJobsD_other_key_fixed jobs σ hon hjv hnot
    obtain ⟨hrowE, hedgeC, huposC, hnegC⟩ := hcomp
    have hres' : ({ reconcileJobsL S T σ jobs with
        watermark := (reconcileJobsL S T σ jobs).maxOutboxId }).residue
          (objNode ⟨dt, on⟩ R) R = σ.residue (objNode ⟨dt, on⟩ R) R := by
      show (reconcileJobsL S T σ jobs).residue (objNode ⟨dt, on⟩ R) R = _
      rw [hev.residue]
      exact hres
    refine ⟨?_, ?_, ?_, ?_⟩
    · intro sh hws hsm
      rw [hres']
      exact hrowE sh hws hsm
    · intro s hb hstar hsm hnc
      show (subjNode s, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsL S T σ jobs).edges
      rw [hev.edges]
      exact (hedges (subjNode s)).mpr (hedgeC s hb hstar hsm hnc)
    · intro s hu hstar hsm
      rw [hres']
      exact huposC s hu hstar hsm
    · intro s hstar hws hsemStar hsemF
      rw [hres']
      exact hnegC s hstar hws hsemStar hsemF
  · rw [hrc]
    exact hcomp

/-! ## Targeted-key RE-settlement — the cascade leg's own keys

The LAST job targeting a key wholesale-rewrites its row and diff-audits its edges;
its filter guards are read at its mid-batch state, where the shadow persists and
`checkFn = sem` (the mid-batch read bridge). The edge half additionally needs the
attack-confirmed edge-holder coverage clause: without it a pre-leg STALE edge of a
non-candidate survives the diff audit (see header). -/

/-- Split a batch at its LAST job targeting the key. -/
theorem exists_last_targeting {dt on R : String} :
    ∀ (jobs : List W3cJob), (∃ j ∈ jobs, j.keyMatch dt on R) →
      ∃ pre j post, jobs = pre ++ j :: post ∧ j.keyMatch dt on R ∧
        ∀ j' ∈ post, ¬ j'.keyMatch dt on R := by
  intro jobs
  induction jobs with
  | nil =>
    rintro ⟨j, hj, _⟩
    exact absurd hj List.not_mem_nil
  | cons a rest ih =>
    intro hex
    by_cases hrest : ∃ j ∈ rest, j.keyMatch dt on R
    · obtain ⟨pre, j, post, heq, hkm, hnone⟩ := ih hrest
      exact ⟨a :: pre, j, post, by rw [heq]; rfl, hkm, hnone⟩
    · obtain ⟨j, hj, hkm⟩ := hex
      rcases List.mem_cons.mp hj with rfl | hjr
      · refine ⟨[], j, rest, rfl, hkm, ?_⟩
        intro j' hj' hkm'
        exact hrest ⟨j', hj', hkm'⟩
      · exact absurd ⟨j, hjr, hkm⟩ hrest

/-- The unlogged diffing batch never makes the key's R-node a source. -/
theorem reconcileJobsD_Rnode_not_source {S : Schema} {T : Store} {σ : GraphState}
    {jobs : List W3cJob} {dt on R : String} (hRne : R ≠ BARE)
    (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) :
    ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ (reconcileJobsD S T σ jobs).edges := by
  intro y hy
  rcases reconcileJobsD_edge_sound jobs σ _ y hy with hold | ⟨j, hj, c, hc, h1, _⟩
  · exact hRns y hold
  · obtain ⟨_, hcb, _⟩ := hjv j hj
    have hpred : (objNode ⟨dt, on⟩ R).pred = c.predicate := by rw [h1, subjNode_pred]
    rw [objNode_pred, hcb c hc] at hpred
    exact hRne hpred

/-- **Batch edge origin at a fixed derived key**: an edge of the diffing batch at the
    key carries a `sem`-true subject, or predates the batch. Each targeting pass's
    guard is read at its own mid-batch state, where the shadow persists and the read
    bridge holds; non-targeting passes leave the key's in-edges untouched. -/
theorem reconcileJobsD_key_edge_sem {S : Schema} {T : Store} {σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hRne : R ≠ BARE) (hon : on ≠ STAR) (hco : ComputedOnly e)
    (hlu : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false) :
    ∀ (js : List W3cJob) (σ : GraphState),
      (∀ j ∈ js, W3cJobValid S j) →
      UntaintedShadow S σ σ0 →
      (∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) →
      ∀ s : SubjectRef,
        (subjNode s, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsD S T σ js).edges →
        sem S T ⟨s, R, ⟨dt, on⟩⟩ = true ∨ (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges := by
  intro js
  induction js with
  | nil =>
    intro σ _ _ _ s hs
    exact Or.inr hs
  | cons j rest ih =>
    intro σ hjv hsh hRns s hs
    have hfold : reconcileJobsD S T σ (j :: rest)
        = reconcileJobsD S T (j.applyD S T σ) rest := by
      unfold reconcileJobsD
      rw [List.foldl_cons]
    rw [hfold] at hs
    have hjv1 := hjv j List.mem_cons_self
    have hsh' : UntaintedShadow S (j.applyD S T σ) σ0 :=
      untaintedShadow_applyD hsh (reachedByRules_of_admitted h0) hSV hNK hRootB hjv1
    have hRns' : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ (j.applyD S T σ).edges := by
      intro y hy
      unfold W3cJob.applyD at hy
      rcases reconcileStarsKeyD_edge_sound T j.dt j.on j.R j.e (wildcardShapes S)
        j.cands j.negCands j.uposCands σ _ y hy with hold | ⟨c, hc, h1, _⟩
      · exact hRns y hold
      · obtain ⟨_, hcb, _⟩ := hjv1
        have hpred : (objNode ⟨dt, on⟩ R).pred = c.predicate := by rw [h1, subjNode_pred]
        rw [objNode_pred, hcb c hc] at hpred
        exact hRne hpred
    rcases ih (j.applyD S T σ) (fun j' hj' => hjv j' (List.mem_cons_of_mem _ hj')) hsh' hRns'
        s hs with hsem | hmem
    · exact Or.inl hsem
    · by_cases hkm : j.keyMatch dt on R
      · -- the pass targets the key: the edge char decides s's edge at pass start
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
        unfold W3cJob.applyD at hmem
        simp only at hmem
        have hchar := reconcileStarsKeyD_edge_char (S := S) T dt on R e (wildcardShapes S)
          jc jn ju hRne hon hder hco hlu hcb hRns hsh.closed s
        rcases hchar.mp hmem with ⟨hcands, hguard⟩ | ⟨_, hold⟩
        · rw [Bool.and_eq_true] at hguard
          have hchk := hguard.1
          have hsstar : s.name ≠ STAR := hcS s hcands
          rw [checkFn_eq_sem_w3d hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm
            h0 hsh hlk hco hlu (fun hx => absurd hx hsstar) hon] at hchk
          exact Or.inl hchk
        · exact Or.inr hold
      · obtain ⟨_, hedges⟩ := applyD_other_key_fixed hjv1 hon hkm
        exact Or.inr ((hedges (subjNode s)).mp hmem)

/-- **Targeted-key RE-settlement.** After a cascade leg on the fragment, every key one
    of its jobs targets is `SettledKey` AND `CompleteKey` w.r.t. the (unchanged)
    store: the last targeting job wholesale-rewrites the row (its three filters read
    at its mid-batch state, where `checkFn = sem`) and diff-audits the edges (the
    edge char + the edge-holder/`sem`-completeness coverage clauses); later jobs
    never touch the key. -/
theorem settledComplete_cascade_targeted {σ : GraphState} {S : Schema} {T : Store}
    {jobs : List W3cJob}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hSV : StoreValidRules S T) (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (h : ReachedByW3d σ S T)
    (hjv : ∀ j ∈ jobs, W3cJobValid S j)
    (hcovg : ∀ j ∈ jobs, W3dJobCoverage S T σ j)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hon : on ≠ STAR)
    (htgt : ∃ j ∈ jobs, j.keyMatch dt on R) :
    SettledKey S T (runCascade S T σ jobs) dt on R ∧
    CompleteKey S T (runCascade S T σ jobs) dt on R := by
  have hco := hCO _ _ _ hlk hder
  have hlu := hLU _ _ _ hlk hder
  -- the reject branch is dead on the fragment
  have hacc := runCascade_no_abort hterm hLU hjv h
  have hev := reconcileJobsL_evalEq (EvalEq.refl σ) S T jobs
  have hresEq : ({ reconcileJobsL S T σ jobs with
      watermark := (reconcileJobsL S T σ jobs).maxOutboxId }).residue
        = (reconcileJobsD S T σ jobs).residue := hev.residue
  have hedgeEq : ({ reconcileJobsL S T σ jobs with
      watermark := (reconcileJobsL S T σ jobs).maxOutboxId }).edges
        = (reconcileJobsD S T σ jobs).edges := hev.edges
  -- split at the LAST targeting job
  obtain ⟨pre, j, post, hsplit, hkm, hpostn⟩ := exists_last_targeting jobs htgt
  have hjmem : j ∈ jobs := hsplit ▸ List.mem_append_right _ List.mem_cons_self
  have hjvpre : ∀ j' ∈ pre, W3cJobValid S j' :=
    fun j' hj' => hjv j' (hsplit ▸ List.mem_append_left _ hj')
  have hjvpost : ∀ j' ∈ post, W3cJobValid S j' :=
    fun j' hj' => hjv j' (hsplit ▸ List.mem_append_right _ (List.mem_cons_of_mem _ hj'))
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
  -- the shadow and the leg-start / prefix-state facts
  obtain ⟨σ0, h0, hsh⟩ := reachedByW3d_shadow h hNK hRootB hSV hterm
  set σpre := reconcileJobsD S T σ pre with hσpre_def
  have hshpre : UntaintedShadow S σpre σ0 :=
    untaintedShadow_reconcileJobsD pre σ σ0 hsh (reachedByRules_of_admitted h0)
      hSV hNK hRootB hjvpre
  have hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges :=
    reachedByW3d_Rnode_not_source hterm hRne hder h
  have hRnspre : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σpre.edges :=
    reconcileJobsD_Rnode_not_source hRne hjvpre hRns
  -- the mid-batch read bridge at the last targeting job's pass start
  have hbridge : ∀ (x : SubjectRef), (x.name = STAR → x.predicate = BARE) →
      σpre.checkFn T x dt on R e = sem S T ⟨x, R, ⟨dt, on⟩⟩ :=
    fun x hx => checkFn_eq_sem_w3d hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm
      h0 hshpre hlk hco hlu hx hon
  have hcovsem : ∀ sh ∈ wildcardShapes S,
      σpre.coveredFn T dt on R e sh = sem S T ⟨starSubj sh, R, ⟨dt, on⟩⟩ :=
    fun sh hws => hbridge (starSubj sh) (fun _ => hWSbare sh hws)
  -- the batch factors through the last targeting job
  have hfold : reconcileJobsD S T σ jobs
      = reconcileJobsD S T
          ((⟨dt, on, R, e, jc, jn, ju⟩ : W3cJob).applyD S T σpre) post := by
    rw [hsplit, hσpre_def]
    unfold reconcileJobsD
    rw [List.foldl_append, List.foldl_cons]
  obtain ⟨hpostres, hpostedges⟩ :=
    reconcileJobsD_other_key_fixed post
      ((⟨dt, on, R, e, jc, jn, ju⟩ : W3cJob).applyD S T σpre) hon hjvpost hpostn
  -- the final row is the last targeting pass's wholesale recompute at σpre
  have hrowfinal : (reconcileJobsD S T σ jobs).residue (objNode ⟨dt, on⟩ R) R
      = some ⟨(wildcardShapes S).filter (fun sh => σpre.coveredFn T dt on R e sh),
              jn.filter (fun c =>
                ((wildcardShapes S).filter
                  (fun sh => σpre.coveredFn T dt on R e sh)).contains c.shape
                    && !(σpre.checkFn T c dt on R e)),
              ju.filter (fun c =>
                !(((wildcardShapes S).filter
                  (fun sh => σpre.coveredFn T dt on R e sh)).contains c.shape)
                    && σpre.checkFn T c dt on R e)⟩ := by
    rw [hfold, hpostres]
    show (σpre.reconcileStarsKeyD T dt on R e (wildcardShapes S) jc jn ju).residue
      (objNode ⟨dt, on⟩ R) R = _
    rw [reconcileStarsKeyD_residue_self, reconcileResidueKey_residue_self]
  -- the final edge membership at the key, characterised at σpre
  have hchar := reconcileStarsKeyD_edge_char (S := S) T dt on R e (wildcardShapes S)
    jc jn ju hRne hon hder hco hlu hcb hRnspre hshpre.closed
  have hedgefinal : ∀ s : SubjectRef,
      ((subjNode s, objNode ⟨dt, on⟩ R) ∈ (reconcileJobsD S T σ jobs).edges
        ↔ (subjNode s, objNode ⟨dt, on⟩ R)
            ∈ ((⟨dt, on, R, e, jc, jn, ju⟩ : W3cJob).applyD S T σpre).edges) := by
    intro s
    rw [hfold]
    exact hpostedges (subjNode s)
  -- the stars row reads at `sem` level
  have hstars_iff : ∀ sh : Shape,
      ((wildcardShapes S).filter (fun sh => σpre.coveredFn T dt on R e sh)).contains sh
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
  -- === the settled half ===
  have hsettledD : SettledKey S T (reconcileJobsD S T σ jobs) dt on R := by
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
        have hchkF : σpre.checkFn T n dt on R e = false := by
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
      have hedgej : (subjNode s, objNode ⟨dt, on⟩ R)
          ∈ (σpre.reconcileStarsKeyD T dt on R e (wildcardShapes S) jc jn ju).edges := hedge
      rcases (hchar s).mp hedgej with ⟨hcands, hguard⟩ | ⟨hncand, holdpre⟩
      · rw [Bool.and_eq_true] at hguard
        have hchk := hguard.1
        rw [hbridge s (fun hx => absurd hx (hcS s hcands))] at hchk
        exact hchk
      · rcases reconcileJobsD_key_edge_sem hWF hTT hNK hR hSV hBS hTS hRootB hMatch
            hStrat hterm h0 hlk hder hRne hon hco hlu pre σ hjvpre hsh hRns s holdpre
          with hsem | hpreleg
        · exact hsem
        · exact absurd (hcovE s hpreleg) hncand
  -- === the completeness half ===
  have hcompleteD : CompleteKey S T (reconcileJobsD S T σ jobs) dt on R := by
    refine ⟨?_, ?_, ?_, ?_⟩
    · -- row existence: the targeting pass always writes the row
      intro _ _ _
      rw [hrowfinal]
      rfl
    · -- an uncovered `sem`-true bare subject's edge is materialised
      intro s hb hstar hsm hnc
      rw [hedgefinal s]
      have hcmem : s ∈ jc := hcovC s hb hstar hsm
      have hncov : ((wildcardShapes S).filter
          (fun sh => σpre.coveredFn T dt on R e sh)).contains s.shape = false := by
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
          (fun sh => σpre.coveredFn T dt on R e sh)).contains s.shape = false := by
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
  rw [hacc]
  exact ⟨settledKey_congr hresEq hedgeEq hsettledD,
    completeKey_congr hresEq hedgeEq hcompleteD⟩

end Zanzibar
