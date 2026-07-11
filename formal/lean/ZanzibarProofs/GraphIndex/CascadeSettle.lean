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
    its key (the attack-confirmed stale-holder clause) and every UNCOVERED `sem`-true
    bare star-free subject; its `negCands` include every covered-but-`sem`-false
    star-free subject; its `uposCands` include every `sem`-true star-free userset
    subject.

    The uncovered guard on clause (2) is load-bearing for SATISFIABILITY, not for the
    proofs (2026-07-11j, `#eval`-checked): under a covering `T:*` grant EVERY fresh
    unstored subject of the shape is `sem`-true — infinitely many — so without the
    guard no finite job satisfies the clause and the coverage chain admits NO cascade
    on covering stores (the W3d theorems would hold there only for write-only
    histories). Covered subjects need no enumeration: they read through `stars ∖ neg`,
    never through an edge (`want_edge = checkFn ∧ ¬covered`), which is exactly the
    guard `CompleteKey`'s edge clause already carries. Python's `_leaf_concretes`
    likewise only ever enumerates store-SUPPORTED subjects (`processor.py:394-441`). -/
def W3dJobCoverage (S : Schema) (T : Store) (σ : GraphState) (j : W3cJob) : Prop :=
  (∀ s : SubjectRef, (subjNode s, objNode ⟨j.dt, j.on⟩ j.R) ∈ σ.edges → s ∈ j.cands) ∧
  (∀ s : SubjectRef, s.predicate = BARE → s.name ≠ STAR →
    sem S T ⟨s, j.R, ⟨j.dt, j.on⟩⟩ = true →
    ¬(s.shape ∈ wildcardShapes S ∧
      sem S T ⟨starSubj s.shape, j.R, ⟨j.dt, j.on⟩⟩ = true) → s ∈ j.cands) ∧
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
      have hcmem : s ∈ jc := hcovC s hb hstar hsm hnc
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

/-! ## The settledness invariant over the coverage chain -/

/-- `sem` is false at every declared derived key over the EMPTY store: the compiled
    guard reads an edgeless graph (all four probes false at every leaf), and the
    bridge holds at the empty admitted base. -/
theorem sem_nil_derived_false {S : Schema}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S) (hR : RewriteRanked S)
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (htermS : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R)
    {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hlu : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    {s : SubjectRef} (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    sem S [] ⟨s, R, ⟨dt, on⟩⟩ = false := by
  have hSV : StoreValidRules S ([] : Store) := fun t ht => absurd ht List.not_mem_nil
  have hBS : BareStarStore ([] : Store) := fun t ht => absurd ht List.not_mem_nil
  have hTS : TtuStarFree S ([] : Store) := fun t ht => absurd ht List.not_mem_nil
  have hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR ([] : Store) R :=
    fun dt R hd => ⟨htermS dt R hd, fun t ht => absurd ht List.not_mem_nil⟩
  rw [← checkFn_eq_sem_bs hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm
    (ReachedByW3aAdmitted.base (ReachedByRulesAdmitted.empty S)) hlk hco hlu hs hon]
  cases hc : (emptyState S).checkFn ([] : Store) s dt on R e
  · rfl
  · exfalso
    unfold GraphState.checkFn at hc
    obtain ⟨r', _, hleaf⟩ := evalE_computedOnly_true_leaf e hco hc
    have hreach : ∀ u v, (emptyState S).reach u v = false := by
      intro u v
      cases hr : (emptyState S).reach u v
      · rfl
      · exfalso
        have hN := reach_sound hr
        cases hN with
        | edge hmem => simp [emptyState] at hmem
        | head hmem _ => simp [emptyState] at hmem
    unfold GraphModel.graphRec GraphModel.probeNonDerived at hleaf
    simp [hreach] at hleaf

/-- **The settledness invariant** (`reachedByW3dC_settled`): at every state of the
    coverage chain, every declared derived key at a concrete object is DIRTY
    (`∈ cascadeKeys`) or `SettledKey ∧ CompleteKey`. Write legs dirty their mapped
    keys and transport the rest (fan-out completeness makes unmapped keys keep
    representation AND meaning); cascade legs re-settle every targeted key (dirty
    keys ARE targeted, `hcover`) and leave the untargeted ones alone. -/
theorem reachedByW3dC_settled {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3dC σ S T) :
    WF S → TtuTuplesetsDirect S → NodupKeys S → RewriteRanked S →
    (∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2) →
    RewriteMatchDeclared S → Stratifiable S →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e) →
    (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false) →
    (∀ sh ∈ wildcardShapes S, sh.2 = BARE) →
    StoreValidRules S T → BareStarStore T → TtuStarFree S T →
    (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) →
    ∀ dt on R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → on ≠ STAR →
      (dt, R, on) ∈ cascadeKeys S σ ∨
      (SettledKey S T σ dt on R ∧ CompleteKey S T σ dt on R) := by
  induction h with
  | empty S =>
    intro hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare _hSV _hBS _hTS hterm
      dt on R e hlk hder hon
    have hsemF : ∀ (s : SubjectRef), (s.name = STAR → s.predicate = BARE) →
        sem S [] ⟨s, R, ⟨dt, on⟩⟩ = false :=
      fun s hs => sem_nil_derived_false hWF hTT hNK hR hRootB hMatch hStrat
        (fun dt R hd => (hterm dt R hd).1) hlk (hCO _ _ _ hlk hder)
        (hLU _ _ _ hlk hder) hs hon
    refine Or.inr ⟨⟨?_, ?_⟩, ?_, ?_, ?_, ?_⟩
    · intro res hres
      simp [emptyState] at hres
    · intro s _ _ hedge
      simp [emptyState] at hedge
    · intro sh hws hsm
      have := hsemF (starSubj sh) (fun _ => hWSbare sh hws)
      rw [hsm] at this
      exact absurd this (by decide)
    · intro s _ hstar hsm _
      have := hsemF s (fun hx => absurd hx hstar)
      rw [hsm] at this
      exact absurd this (by decide)
    · intro s _ hstar hsm
      have := hsemF s (fun hx => absurd hx hstar)
      rw [hsm] at this
      exact absurd this (by decide)
    · intro s hstar hws hsemStar _
      have := hsemF (starSubj s.shape) (fun _ => hWSbare _ hws)
      rw [hsemStar] at this
      exact absurd this (by decide)
  | @write σp S T t hadm hprev ih =>
    intro hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare hSV hBS hTS hterm
      dt on R e hlk hder hon
    by_cases hmap : (dt, R, on) ∈ cascadeKeys S (σp.writeLoggedRules S t)
    · exact Or.inl hmap
    · have hSVw : StoreValidRules S T := fun t' ht' => hSV t' (List.mem_cons_of_mem _ ht')
      have hBSw : BareStarStore T := fun t' ht' => hBS t' (List.mem_cons_of_mem _ ht')
      have hTSw : TtuStarFree S T := fun t' ht' => hTS t' (List.mem_cons_of_mem _ ht')
      have htermw : ∀ dt R, isDerived S (dt, R) = true →
          NoTtuTarget S R ∧ NoStoreSubjectR T R :=
        fun dt R hd => ⟨(hterm dt R hd).1,
          fun t' ht' => (hterm dt R hd).2 t' (List.mem_cons_of_mem _ ht')⟩
      have hW3d : ReachedByW3d σp S T := reachedByW3dC_toW3d hprev
      rcases ih hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare hSVw hBSw hTSw htermw
          dt on R e hlk hder hon with hdirty | ⟨hset, hcomp⟩
      · exact absurd
          (cascadeKeys_writeLeg_mono (reachedByW3d_edgesClosed hW3d) _ hdirty) hmap
      · exact Or.inr
          ⟨settledKey_writeLeg hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm
            hWSbare hW3d hadm hlk hder (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder)
            hmap hon hset,
          completeKey_writeLeg hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm
            hWSbare hW3d hadm hlk hder (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder)
            hmap hon hcomp⟩
  | @cascade σp S T jobs hjv hcover hscope hcovg hprev ih =>
    intro hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare hSV hBS hTS hterm
      dt on R e hlk hder hon
    have hW3d : ReachedByW3d σp S T := reachedByW3dC_toW3d hprev
    by_cases htgt : ∃ j ∈ jobs, j.keyMatch dt on R
    · exact Or.inr (settledComplete_cascade_targeted hWF hTT hNK hR hSV hBS hTS hRootB
        hMatch hStrat hterm hCO hLU hWSbare hW3d hjv hcovg hlk hder hon htgt)
    · have hnot : ∀ j ∈ jobs, ¬ j.keyMatch dt on R :=
        fun j hj hkm => htgt ⟨j, hj, hkm⟩
      rcases ih hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare hSV hBS hTS hterm
          dt on R e hlk hder hon with hdirty | ⟨hset, hcomp⟩
      · exfalso
        obtain ⟨j, hj, hkey⟩ := hcover _ hdirty
        have h1 : j.dt = dt := congrArg Prod.fst hkey
        have h23 : (j.R, j.on) = (R, on) := congrArg Prod.snd hkey
        have h2 : j.R = R := congrArg Prod.fst h23
        have h3 : j.on = on := congrArg Prod.snd h23
        exact htgt ⟨j, hj, h1, h3, h2⟩
      · exact Or.inr ⟨settledKey_cascade_untargeted hjv hnot hon hset,
          completeKey_cascade_untargeted hjv hnot hon hcomp⟩

/-- A quiescent state's cascade key set is empty — the "fully drained" read scope
    every accepted cascade run produces (`cascade_drains`). -/
theorem cascadeKeys_nil_of_quiescent (S : Schema) {σ : GraphState} (h : Quiescent σ) :
    cascadeKeys S σ = [] := by
  unfold cascadeKeys GraphState.frontierRows
  have hfil : σ.outbox.filter (fun d => σ.watermark < d.id) = [] := by
    rw [List.filter_eq_nil_iff]
    intro d hd hc
    have hlt : σ.watermark < d.id := of_decide_eq_true hc
    have hle := h d hd
    omega
  rw [hfil]
  rfl

/-! ## `graph_correct_w3d` — the W3d T2b -/

/-- **T2b, W3d fragment (`graph_correct_w3d`) — `check = sem` at every fully-drained
    state of the interleaved scheduler chain.** The state is any `ReachedByW3dC` state
    with an empty cascade-key set (every accepted `runCascade` produces one:
    `cascade_drains` + `cascadeKeys_nil_of_quiescent`); the store carries bare `T:*`
    grants; subjects may be bare, star-BARE, or usersets.

    * **Untainted query:** the untainted-core shadow + the star-relaxed base equation.
    * **Derived query:** the settledness invariant with `cascadeKeys = []` leaves
      every key settled+complete: star ⇒ the `stars` row (linchpin declaredness at
      the shadow, row existence from `CompleteKey`); bare ⇒ edge ∨ (`stars` ∖ `neg`)
      (the W3d reach collapse + the settled edge half; `neg` completeness for the
      covered fallback); userset ⇒ exactly `upos`. -/
theorem graph_correct_w3d {S : Schema} {T : Store} {σ : GraphState} (q : Query)
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
    (h : ReachedByW3dC σ S T) (hq : cascadeKeys S σ = [])
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem S T q := by
  have hW3d : ReachedByW3d σ S T := reachedByW3dC_toW3d h
  have hschema : σ.schema = S := reachedByW3d_schema hW3d
  have hcl := reachedByW3d_edgesClosed hW3d
  obtain ⟨σ0, h0, hsh⟩ := reachedByW3d_shadow hW3d hNK hRootB hSV hterm
  obtain ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ := q
  replace hqs : sn = STAR → sp = BARE := hqs
  replace hqo : on ≠ STAR := hqo
  by_cases hder : isDerived S (dt, R) = true
  · -- ===== derived query: the residue/edge read at a settled+complete key =====
    obtain ⟨e, hlk⟩ := isDerived_declared hder
    have hco := hCO _ _ _ hlk hder
    have hleafUnt := hLU _ _ _ hlk hder
    have hroot : RootBoolean e := hRootB ⟨(dt, R), e⟩ (mem_defs_of_lookup hlk) hder
    obtain ⟨hset, hcomp⟩ :=
      (reachedByW3dC_settled h hWF hTT hNK hR hRootB hMatch hStrat hCO hLU hWSbare
        hSV hBS hTS hterm dt on R e hlk hder hqo).resolve_left
        (by rw [hq]; exact List.not_mem_nil)
    obtain ⟨hrowS, hedgeS⟩ := hset
    obtain ⟨hrowE, hedgeC, huposC, hnegC⟩ := hcomp
    have hroute : GraphModel.check σ ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
        = GraphModel.probeDerived σ ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ := by
      unfold GraphModel.check
      rw [hschema]
      simp [hder]
    rw [hroute, probeDerived_eq σ hqo]
    -- LINCHPIN at the shadow: a `sem`-covered bare shape is DECLARED
    have hsem_ws : ∀ sh : Shape, sh.2 = BARE →
        sem S T ⟨starSubj sh, R, ⟨dt, on⟩⟩ = true → sh ∈ wildcardShapes S := by
      intro sh hshb hsm
      refine coveredFn_declared hTT hSV hTS h0 hco (dt := dt) (on := on) (R := R) ?_
      show σ0.checkFn T (starSubj sh) dt on R e = true
      rw [checkFn_eq_sem_bs hWF hTT hNK hR hSV hBS hTS hRootB hMatch hStrat hterm
        (ReachedByW3aAdmitted.base h0) hlk hco hleafUnt (fun _ => hshb) hqo]
      exact hsm
    -- reach ⇒ sem for star-free bare subjects: the W3d collapse + the settled edges
    have hreach_sem : sn ≠ STAR → sp = BARE →
        σ.reach (subjNode ⟨st, sn, sp⟩) (objNode ⟨dt, on⟩ R) = true →
        sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ = true := by
      intro hsn hspb hr
      have hedge := reachedByW3d_reach_collapse_root hWF hSV hNK hlk hroot hW3d
        (reach_sound hr)
      exact hedgeS ⟨st, sn, sp⟩ hspb hsn hedge
    by_cases hstar : sn = STAR
    · -- ---- star subject: the `stars` read ----
      subst hstar
      have hsp : sp = BARE := hqs rfl
      subst hsp
      rw [if_pos rfl]
      cases hrow : σ.residue (objNode ⟨dt, on⟩ R) R with
      | none =>
        rw [Option.getD_none]
        cases hsm : sem S T ⟨⟨st, STAR, BARE⟩, R, ⟨dt, on⟩⟩
        · rfl
        · exfalso
          have hws := hsem_ws (st, BARE) rfl hsm
          have hsome := hrowE (st, BARE) hws hsm
          rw [hrow] at hsome
          exact absurd hsome (by decide)
      | some res =>
        rw [Option.getD_some]
        cases hc : res.stars.contains (st, BARE) <;>
          cases hsm : sem S T ⟨⟨st, STAR, BARE⟩, R, ⟨dt, on⟩⟩
        · rfl
        · exfalso
          have hws := hsem_ws (st, BARE) rfl hsm
          have := ((hrowS res hrow).1 (st, BARE)).mpr ⟨hws, hsm⟩
          rw [hc] at this
          exact absurd this (by decide)
        · exfalso
          obtain ⟨_, hs⟩ := ((hrowS res hrow).1 (st, BARE)).mp hc
          have hs' : sem S T ⟨⟨st, STAR, BARE⟩, R, ⟨dt, on⟩⟩ = true := hs
          rw [hsm] at hs'
          exact absurd hs' (by decide)
        · rfl
    · rw [if_neg hstar]
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
            · have hsome := hrowE (st, BARE) hcov.1 hcov.2
              rw [hrow] at hsome
              exact absurd hsome (by decide)
            · have hedge := hedgeC ⟨st, sn, BARE⟩ rfl hstar hsm hcov
              have hrc := reach_complete hcl (NReaches.edge hedge)
              rw [hr] at hrc
              exact absurd hrc (by decide)
          · exfalso
            have hsemT := hreach_sem hstar rfl hr
            rw [hsm] at hsemT
            exact absurd hsemT (by decide)
          · rfl
        | some res =>
          rw [Option.getD_some]
          obtain ⟨hstars_iff, hnegRow, _⟩ := hrowS res hrow
          have hfwd : (σ.reach (subjNode ⟨st, sn, BARE⟩) (objNode ⟨dt, on⟩ R)
              || (res.stars.contains (st, BARE) && !res.neg.contains ⟨st, sn, BARE⟩)) = true →
              sem S T ⟨⟨st, sn, BARE⟩, R, ⟨dt, on⟩⟩ = true := by
            intro hread
            rw [Bool.or_eq_true, Bool.and_eq_true] at hread
            rcases hread with hr | ⟨hcS, hnN⟩
            · exact hreach_sem hstar rfl hr
            · by_contra hsm
              rw [Bool.not_eq_true] at hsm
              obtain ⟨hws, hsemStar⟩ := (hstars_iff (st, BARE)).mp hcS
              obtain ⟨res', hres', hmem⟩ := hnegC ⟨st, sn, BARE⟩ hstar hws hsemStar hsm
              rw [hrow] at hres'
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
            · refine Or.inr ⟨(hstars_iff (st, BARE)).mpr hcov, ?_⟩
              cases hcnt : res.neg.contains ⟨st, sn, BARE⟩
              · rfl
              · exfalso
                have hmem : (⟨st, sn, BARE⟩ : SubjectRef) ∈ res.neg := by
                  rw [List.contains_eq_mem] at hcnt
                  exact of_decide_eq_true hcnt
                obtain ⟨_, hsemF⟩ := hnegRow _ hmem
                rw [hsm] at hsemF
                exact absurd hsemF (by decide)
            · exact Or.inl (reach_complete hcl (NReaches.edge
                (hedgeC ⟨st, sn, BARE⟩ rfl hstar hsm hcov)))
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
      · -- ---- userset subject: the `upos` read ----
        rw [if_neg hbare]
        cases hrow : σ.residue (objNode ⟨dt, on⟩ R) R with
        | none =>
          rw [Option.getD_none]
          show false = sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
          cases hsm : sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
          · rfl
          · exfalso
            obtain ⟨res', hres', _⟩ := huposC ⟨st, sn, sp⟩ hbare hstar hsm
            rw [hrow] at hres'
            cases hres'
        | some res =>
          rw [Option.getD_some]
          obtain ⟨hstars_iff, _, huposRow⟩ := hrowS res hrow
          have hns : res.stars.contains (st, sp) = false := by
            by_contra hcx
            rw [Bool.not_eq_false] at hcx
            obtain ⟨hws, _⟩ := (hstars_iff (st, sp)).mp hcx
            exact hbare (hWSbare (st, sp) hws)
          rw [hns]
          show (if res.upos.contains ⟨st, sn, sp⟩ = true then true else false)
              = sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
          cases hu : res.upos.contains ⟨st, sn, sp⟩ <;>
            cases hsm : sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
          · rfl
          · exfalso
            obtain ⟨res', hres', hmem⟩ := huposC ⟨st, sn, sp⟩ hbare hstar hsm
            rw [hrow] at hres'
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
            obtain ⟨_, _, hsemT⟩ := huposRow _ hmem
            rw [hsm] at hsemT
            exact absurd hsemT (by decide)
          · rfl
  · -- ===== untainted query: the shadow + the star-relaxed base equation =====
    have hd : isDerived S (dt, R) = false := by simpa using hder
    have hroute : GraphModel.check σ ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
        = GraphModel.probeNonDerived σ ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ := by
      unfold GraphModel.check
      rw [hschema]
      simp [hd]
    rw [hroute]
    calc GraphModel.probeNonDerived σ ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩
        = GraphModel.graphRec σ ⟨st, sn, sp⟩ dt on R := rfl
      _ = GraphModel.graphRec σ0 ⟨st, sn, sp⟩ dt on R :=
          shadow_graphRec_agree hsh ⟨st, sn, sp⟩ on hd
      _ = sem S T ⟨⟨st, sn, sp⟩, R, ⟨dt, on⟩⟩ :=
          graphRec_base_eq_bs hWF hTT hNK hR hSV hBS hTS hRootB hMatch h0
            (s := ⟨st, sn, sp⟩) (dt := dt) (on := on) hqs hqo R hd

end Zanzibar
