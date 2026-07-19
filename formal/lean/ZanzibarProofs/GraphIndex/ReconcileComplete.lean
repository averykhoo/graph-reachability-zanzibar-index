import ZanzibarProofs.GraphIndex.RestrictBase

/-!
# The derived reconcile — candidate completeness + the `check_fn ↔ sem` bridge (ROADMAP W3a, Step B)

Step A (`RestrictBase.lean`) closed the base `hag` equation `graphRec_base_eq`: on an admitted
rule-routed base over the mixed schema `S`, the operand read equals `sem S T` for every untainted
operand. Step B assembles the full W3a read correspondence `graph_correct_w3a`.

This first increment lands the **`checkFn ↔ sem` bridge**: for a W3a state whose operand reads
reduce to an admitted base (`hinert`), the compiled `check_fn` for a bare subject `s` at a derived
key `(dt, R)` equals `sem S T ⟨s, R, ⟨dt,on⟩⟩`. The route composes
- `checkFn_eq_semStep` (`ReconcileCorrect.lean`): `checkFn = semAux (f+1)` given per-relation
  agreement `hag` at the def's `computed` leaves;
- `graphRec_base_eq` (`RestrictBase.lean`): the base operand read = `sem` for untainted operands;
- `sem`'s **query-independence** (`semAux_qirrel`, this file): `semAux` never consults the query
  `q` except through `instances`, which discards it — so the operand `sem` (query `⟨s,r',o⟩`) and
  the fuel-`semAux` at the derived query `⟨s,R,o⟩` coincide;
- T0a fuel-stability (`sem_fuel_stable`) to erase the extra `+1` fuel on the mixed (stratifiable)
  schema.

The fragment fact consumed here is that every `computed` leaf of a derived def is untainted
(`hleafUnt`) — the W3a "operands are computed refs to untainted relations" shape.
-/

namespace Zanzibar

/-! ## `sem` is independent of the query `q`

The evaluator threads the query `q` only into `instances T q`, and `instances` (`Core/Store.lean`)
is `universeOf … includeEndpoints:=false`, whose endpoint contribution — the sole place `q` is
read — is dead. So `semAux` (hence `sem`'s fuel-`semAux` reads) does not depend on `q`. This lets
the base `hag` (stated with the operand query `⟨s,r',o⟩`) feed `checkFn_eq_semStep` (which fixes the
enclosing derived query `⟨s,R,o⟩`). -/

/-- `instances` discards the query — its endpoint branch is under `includeEndpoints := false`. -/
theorem instances_qirrel (T : Store) (q1 q2 : Query) (t : String) :
    instances T q1 t = instances T q2 t := rfl

/-- `memberOfGranted` is query-independent (its only `q`-use is `instances`). -/
theorem memberOfGranted_qirrel (rec : Rec) (T : Store) (q1 q2 : Query) (grants : List Tuple) :
    memberOfGranted rec T q1 grants = memberOfGranted rec T q2 grants := by
  unfold memberOfGranted
  simp only [instances_qirrel T q1 q2]

/-- `directLeaf` is query-independent. -/
theorem directLeaf_qirrel (rec : Rec) (subject : SubjectRef) (T : Store) (q1 q2 : Query)
    (rs : List Restriction) (otype oname rel : String) :
    directLeaf rec subject T q1 rs otype oname rel
      = directLeaf rec subject T q2 rs otype oname rel := by
  simp only [directLeaf, memberOfGranted_qirrel rec T q1 q2]

/-- `ttuLeaf` is query-independent (its only `q`-use is `instances`). -/
theorem ttuLeaf_qirrel (rec : Rec) (subject : SubjectRef) (T : Store) (q1 q2 : Query)
    (tr ts otype oname : String) :
    ttuLeaf rec subject T q1 tr ts otype oname
      = ttuLeaf rec subject T q2 tr ts otype oname := by
  unfold ttuLeaf
  simp only [instances_qirrel T q1 q2]

/-- **`evalE` is query-independent** (same node-recursion `rec`). By induction on the expr; the
    `direct` / `ttu` leaves are the only `q`-consumers and both discard it. -/
theorem evalE_qirrel (rec : Rec) (subject : SubjectRef) (T : Store) (q1 q2 : Query)
    (otype oname rel : String) (e : Expr) :
    evalE rec subject T q1 otype oname rel e
      = evalE rec subject T q2 otype oname rel e := by
  induction e with
  | union a b iha ihb => simp only [evalE, iha, ihb]
  | inter a b iha ihb => simp only [evalE, iha, ihb]
  | excl a b iha ihb => simp only [evalE, iha, ihb]
  | computed r => rfl
  | direct rs => exact directLeaf_qirrel rec subject T q1 q2 rs otype oname rel
  | ttu tr ts => exact ttuLeaf_qirrel rec subject T q1 q2 tr ts otype oname

/-- **`semAux` is independent of the query `q`.** Fuel induction: at `f+1` the two fuel-`f` recs
    coincide as functions (IH ⇒ `funext`), so the step reduces to `evalE`'s query-independence. -/
theorem semAux_qirrel (S : Schema) (subject : SubjectRef) (T : Store) (q1 q2 : Query) :
    ∀ (f : Nat) (ot on rel : String),
      semAux S subject T q1 f ot on rel = semAux S subject T q2 f ot on rel := by
  intro f
  induction f with
  | zero => intro ot on rel; rfl
  | succ f ih =>
    intro ot on rel
    have hfun : semAux S subject T q1 f = semAux S subject T q2 f := by
      funext ot' on' rel'; exact ih ot' on' rel'
    show step S subject T q1 (semAux S subject T q1 f) ot on rel
       = step S subject T q2 (semAux S subject T q2 f) ot on rel
    rw [hfun]
    unfold step
    cases S.lookup (ot, rel) with
    | none => rfl
    | some e => exact evalE_qirrel _ subject T q1 q2 ot on rel e

/-! ## The `check_fn ↔ sem` bridge -/

/-- **`checkFn` equals `sem` on the derived key, given the operand reads reduce to an admitted
    base.** For a W3a state `σ` whose operand reads reduce to an admitted rule-routed base `σ0`
    (`hinert`: `graphRec σ = graphRec σ0` at the def's untainted `computed` leaves), a bare subject
    `s`, and a derived key `(dt, R)` with a `ComputedOnly` def `e` whose computed leaves are
    untainted (`hleafUnt`):

        checkFn σ T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩.

    Composition: `hag` (per-leaf agreement at fuel `fuelBound S T`) is `hinert` ⟶ `graphRec_base_eq`
    ⟶ `sem`-def ⟶ query-independence; `checkFn_eq_semStep` then gives `checkFn = semAux (f+1)`, and
    fuel stability (mixed schema `Stratifiable`) erases the extra fuel. -/
theorem checkFn_eq_sem_of_base {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hinert : ∀ r' ∈ computedRefs e,
      GraphModel.graphRec σ s dt on r' = GraphModel.graphRec σ0 s dt on r')
    (hs : s.name ≠ STAR) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hDecl : StoreDeclared S T := storeDeclared_of_validRules hSV
  -- per-leaf agreement at fuel `fuelBound S T`, enclosing query `⟨s, R, ⟨dt,on⟩⟩`
  have hag : ∀ r' ∈ computedRefs e,
      GraphModel.graphRec σ s dt on r'
        = semAux S s T ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r' := by
    intro r' hr'
    rw [hinert r' hr',
        graphRec_base_eq hWF hTT hNK hR hSV hSF hCO hMatch h0 hs hon r' (hleafUnt r' hr')]
    -- sem S T ⟨s,r',o⟩ = semAux S s T ⟨s,r',o⟩ fuelBound dt on r' (def); query-independence to ⟨s,R,o⟩
    show sem S T ⟨s, r', ⟨dt, on⟩⟩ = semAux S s T ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r'
    exact semAux_qirrel S s T ⟨s, r', ⟨dt, on⟩⟩ ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r'
  -- checkFn = semAux (fuelBound+1) at the derived key
  rw [checkFn_eq_semStep (S := S) (σ := σ) (T := T) (q := ⟨s, R, ⟨dt, on⟩⟩) hlk hco hag]
  -- erase the extra fuel via T0a stability
  have hstab := sem_fuel_stable S T ⟨s, R, ⟨dt, on⟩⟩ hStrat hDecl (fuelBound S T + 1) (Nat.le_succ _)
  exact hstab

/-! ## The admitted W3a write-closure — an admitted base for the correspondence

`checkFn_eq_sem_of_base` and `graphRec_base_eq` both need an **admitted** rule-routed base
(`ReachedByRulesAdmitted`), whose edges are complete for every materialised closure tuple. The
plain `ReachedByW3a` closure only records a `ReachedByRules` base, so we mirror it with an admitted
base leg. Everything else is identical — a reconcile leg is a guarded `writeDirect` fold either way
— so the whole soundness spine (`reachedByW3a_*`) transfers through `reachedByW3aAdmitted_toW3a`. -/

/-- **`ReachedByW3aAdmitted σ S T`** — the W3a write-closure whose untainted base was reached by
    *admitted* rule-routed writes. Reconcile legs carry the same faithful side conditions as
    `ReachedByW3a.reconcile`. It forgets to `ReachedByW3a` (`reachedByW3aAdmitted_toW3a`), so all the
    W3a soundness/inertness lemmas apply; the extra admitted base is what feeds `graphRec_base_eq`. -/
inductive ReachedByW3aAdmitted : GraphState → Schema → Store → Prop where
  | base {σ : GraphState} {S : Schema} {T : Store} :
      ReachedByRulesAdmitted σ S T → ReachedByW3aAdmitted σ S T
  | reconcile {σ : GraphState} {S : Schema} {T : Store}
      (dt on R : String) (e : Expr) (cands : List SubjectRef) (hRne : R ≠ BARE)
      (hcands : ∀ c ∈ cands, c.predicate = BARE)
      (hder : isDerived S (dt, R) = true) (hlke : S.lookup (dt, R) = some e)
      (hcStar : ∀ c ∈ cands, c.name ≠ STAR) (honStar : on ≠ STAR) :
      ReachedByW3aAdmitted σ S T → ReachedByW3aAdmitted (σ.reconcileKey T dt on R e cands) S T

/-- The admitted W3a closure forgets to the plain W3a closure — all soundness lemmas transfer. -/
theorem reachedByW3aAdmitted_toW3a {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3aAdmitted σ S T) : ReachedByW3a σ S T := by
  induction h with
  | base hr => exact ReachedByW3a.base (reachedByRules_of_admitted hr)
  | reconcile dt on R e cands hRne hcands hder _hlke hcStar honStar _ ih =>
    exact ReachedByW3a.reconcile dt on R e cands hRne hcands hder hcStar honStar ih

/-- **Multi-pass reconcile inertness, admitted base** — the admitted analog of
    `reachedByW3a_reach_inert`: reachability into any untainted-key node reduces from the full W3a
    state to an **admitted** rule-routed base `σ0`. Same induction; the reconcile leg forgets its
    predecessor to `ReachedByW3a` for the terminality lemma, and carries the admitted base up. -/
theorem reachedByW3aAdmitted_reach_inert {σ : GraphState} {S : Schema} {T : Store}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3aAdmitted σ S T) :
    ∃ σ0, ReachedByRulesAdmitted σ0 S T ∧ (∀ ab ∈ σ0.edges, ab ∈ σ.edges) ∧
      ∀ {u v : NodeKey}, isDerived S (v.type, v.pred) = false →
        NReaches σ.edges u v → NReaches σ0.edges u v := by
  induction h with
  | base hr => exact ⟨_, hr, fun _ hab => hab, fun _ hn => hn⟩
  | reconcile dt on R e cands hRne hcands hder _hlke _hcStar _honStar h' ih =>
    obtain ⟨σ0, hσ0, hsub, htrans⟩ := ih hterm
    refine ⟨σ0, hσ0, ?_, ?_⟩
    · intro ab hab
      exact reconcileKey_edges_mono _ dt on R e cands ab (hsub ab hab)
    · intro u v hv hreach
      obtain ⟨hnt, hns⟩ := hterm dt R hder
      have hRns0 := reachedByW3a_Rnode_not_source hnt hns hRne
        (reachedByW3aAdmitted_toW3a h') (objNode_pred ⟨dt, on⟩ R)
      have hvne : v ≠ objNode ⟨dt, on⟩ R := by
        intro heq
        rw [heq, objNode_type, objNode_pred, hder] at hv
        exact absurd hv (by decide)
      have hstep := reconcileKey_reach_inert _ dt on R e cands hRne hvne hcands hRns0 hreach
      exact htrans hv hstep

/-- **The operand read reduces to an admitted base.** The admitted analog of
    `graphRec_reduce_base`: for an untainted operand `r'`, the full W3a state's operand read equals
    the read on an **admitted** rule-routed base `σ0`. Identical to `graphRec_reduce_base` but
    threading the admitted base out of `reachedByW3aAdmitted_reach_inert`. -/
theorem graphRec_reduce_base_adm {σ : GraphState} {S : Schema} {T : Store}
    (hSF : StarFreeStore T)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3aAdmitted σ S T) {s : SubjectRef} {dt on : String} :
    ∃ σ0, ReachedByRulesAdmitted σ0 S T ∧
      ∀ r', isDerived S (dt, r') = false →
        GraphModel.graphRec σ s dt on r' = GraphModel.graphRec σ0 s dt on r' := by
  obtain ⟨σ0, hσ0, hsub, htrans⟩ := reachedByW3aAdmitted_reach_inert hterm h
  refine ⟨σ0, hσ0, ?_⟩
  intro r' hunt
  have hplainσ := reachedByW3a_edges_plain hSF (reachedByW3aAdmitted_toW3a h)
  have hplainσ0 : ∀ e ∈ σ0.edges, e.1.variant = Variant.plain ∧ e.2.variant = Variant.plain := by
    intro e he
    obtain ⟨t, ht, w, hw, h1, h2⟩ :=
      reachedByRules_edge_sound (reachedByRules_of_admitted hσ0) e.1 e.2 he
    have hws : w.subject.name ≠ STAR := rewriteClosure_subjectName hw ▸ (hSF t ht).1
    have hwo : w.object.name ≠ STAR := rewriteClosure_object hw ▸ (hSF t ht).2
    exact ⟨by rw [h1, subjNode_plain hws], by rw [h2, objNode_plain hwo]⟩
  unfold GraphModel.graphRec
  rw [probeNonDerived_plainEdges _ hplainσ, probeNonDerived_plainEdges _ hplainσ0]
  have hcl_σ := (reachedByW3a_inv (reachedByW3aAdmitted_toW3a h)).1.edgesClosed
  have hcl_σ0 := (reachedByRules_inv (reachedByRules_of_admitted hσ0)).1.edgesClosed
  have hunt' : isDerived S ((objNode ⟨dt, on⟩ r').type, (objNode ⟨dt, on⟩ r').pred) = false := by
    rw [objNode_type, objNode_pred]; exact hunt
  have key : σ.reach (subjNode s) (objNode ⟨dt, on⟩ r') = true ↔
             σ0.reach (subjNode s) (objNode ⟨dt, on⟩ r') = true := by
    rw [reach_iff_nreaches hcl_σ, reach_iff_nreaches hcl_σ0]
    exact ⟨fun hn => htrans hunt' hn, fun h0 => NReaches.mono_subset hsub h0⟩
  cases h1 : σ.reach (subjNode s) (objNode ⟨dt, on⟩ r') <;>
    cases h2 : σ0.reach (subjNode s) (objNode ⟨dt, on⟩ r') <;>
    simp_all

/-- **`checkFn` equals `sem` on a W3a-admitted state.** Discharges the `hinert` hypothesis of
    `checkFn_eq_sem_of_base` via `graphRec_reduce_base_adm`: the operand reads of a W3a-admitted
    state reduce to its admitted base, whose reads equal `sem` (`graphRec_base_eq`). So for a bare
    subject `s` at a `ComputedOnly` derived key `(dt, R)` with untainted computed leaves,
    `checkFn σ T s dt on R e = sem S T ⟨s, R, ⟨dt,on⟩⟩`. -/
theorem checkFn_eq_sem {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3aAdmitted σ S T)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hs : s.name ≠ STAR) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  obtain ⟨σ0, h0, hred⟩ := graphRec_reduce_base_adm hSF hterm h (s := s) (dt := dt) (on := on)
  exact checkFn_eq_sem_of_base hWF hTT hNK hR hSV hSF hCO hMatch hStrat h0 hlk hco hleafUnt
    (fun r' hr' => hred r' (hleafUnt r' hr')) hs hon

/-! ## The leaf-widened `checkFn = sem` bridge (Direct-arm leg 5, sub-step 1)

The `_d` variants of `checkFn_eq_sem_of_base` / `checkFn_eq_sem`: they admit a derived def
carrying **bare `Direct` arms** (`ComputedOrDirect e ∧ DirectArmsBare e`) in place of the
`ComputedOnly` restriction, routing the operand read through the widened base equation
`graphRec_base_eq_d` (`StoreValidRulesD` store, the `hterm` bundle — no `hCO`) and the
widened read bridge `checkFn_eq_semStep_cd`. The `.direct` arm rides for free: a bare arm
reads the store alone at the fixed subject, independent of `rec`/query
(`directLeaf_bare_indep`), so only the `computed` operand leaves need the base agreement —
exactly what `graphRec_reduce_base_adm` + `graphRec_base_eq_d` supply. Concrete-subject
scope (`hs : s.name ≠ STAR`); the star-subject/coverage half is sub-step 2. -/

/-- **Widened `checkFn = sem` from an admitted base (Direct arm).** `checkFn_eq_sem_of_base`
    over `StoreValidRulesD` + `ComputedOrDirect`/`DirectArmsBare`, via `checkFn_eq_semStep_cd`
    and `graphRec_base_eq_d`. -/
theorem checkFn_eq_sem_of_base_d {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRulesD S T) (hSF : StarFreeStore T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hinert : ∀ r' ∈ computedRefs e,
      GraphModel.graphRec σ s dt on r' = GraphModel.graphRec σ0 s dt on r')
    (hs : s.name ≠ STAR) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hDecl : StoreDeclared S T := storeDeclared_of_validRulesD hSV
  have hag : ∀ r' ∈ computedRefs e,
      GraphModel.graphRec σ s dt on r'
        = semAux S s T ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r' := by
    intro r' hr'
    rw [hinert r' hr',
        graphRec_base_eq_d hWF hTT hNK hR hSV hSF hMatch hterm h0 hs hon r' (hleafUnt r' hr')]
    show sem S T ⟨s, r', ⟨dt, on⟩⟩ = semAux S s T ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r'
    exact semAux_qirrel S s T ⟨s, r', ⟨dt, on⟩⟩ ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r'
  rw [checkFn_eq_semStep_cd (S := S) (σ := σ) (T := T) (q := ⟨s, R, ⟨dt, on⟩⟩) hlk hcd hba hag]
  exact sem_fuel_stable S T ⟨s, R, ⟨dt, on⟩⟩ hStrat hDecl (fuelBound S T + 1) (Nat.le_succ _)

/-- **Widened `checkFn = sem` on a W3a-admitted state (Direct arm).** `checkFn_eq_sem` over
    `StoreValidRulesD` + `ComputedOrDirect`/`DirectArmsBare`; discharges `hinert` via
    `graphRec_reduce_base_adm` and delegates to `checkFn_eq_sem_of_base_d`. -/
theorem checkFn_eq_sem_d {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRulesD S T) (hSF : StarFreeStore T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3aAdmitted σ S T)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hs : s.name ≠ STAR) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  obtain ⟨σ0, h0, hred⟩ := graphRec_reduce_base_adm hSF hterm h (s := s) (dt := dt) (on := on)
  exact checkFn_eq_sem_of_base_d hWF hTT hNK hR hSV hSF hMatch hStrat hterm h0 hlk hcd hba hleafUnt
    (fun r' hr' => hred r' (hleafUnt r' hr')) hs hon

/-! ## Derived-edge soundness — a materialised derived edge is `sem`-true

The forward half of the derived-query correspondence: on a W3a-admitted state, a materialised
derived edge `subjNode s → objNode ⟨dt,on⟩ R` implies `sem S T ⟨s,R,⟨dt,on⟩⟩ = true`. The edge was
written by *some* reconcile pass whose guard (`checkFn` at a mid-fold state) held; that mid-state is
itself W3a-admitted, so `checkFn_eq_sem` turns the guard into `sem`. -/

/-- Node injectivity for star-free subjects. -/
theorem subjNode_inj_of_ne_star {s c : SubjectRef} (hs : s.name ≠ STAR) (hc : c.name ≠ STAR)
    (h : subjNode s = subjNode c) : s = c := by
  unfold subjNode at h
  rw [if_neg hs, if_neg hc] at h
  obtain ⟨st, sn, sp⟩ := s; obtain ⟨ct, cn, cp⟩ := c
  simp only [NodeKey.mk.injEq] at h
  obtain ⟨h1, h2, h3, _⟩ := h
  simp [h1, h2, h3]

/-- Node injectivity for star-free objects (with relation). -/
theorem objNode_inj_of_ne_star {dt on dt' on' R R' : String} (hon : on ≠ STAR) (hon' : on' ≠ STAR)
    (h : objNode ⟨dt, on⟩ R = objNode ⟨dt', on'⟩ R') : dt = dt' ∧ on = on' ∧ R = R' := by
  unfold objNode at h
  rw [if_neg hon, if_neg hon'] at h
  simp only [NodeKey.mk.injEq] at h
  exact ⟨h.1, h.2.1, h.2.2.1⟩

/-- **The reconcile fold's edge provenance.** Every edge of a `reconcileKey` fold either was
    already present in the base `σ`, or was materialised at a mid-fold state whose guard held: it
    equals `subjNode c → objNode ⟨dt,on⟩ R` for a candidate `c`, with `checkFn` TRUE at the
    accumulator `σ.reconcileKey T … pre` reached after some *prefix* `pre`. The prefix mid-state is
    what the assembly recognises as W3a-admitted, so `checkFn_eq_sem` applies there. -/
theorem reconcileKey_edge_guard {T : Store} {dt on R : String} {e : Expr} :
    ∀ (cands : List SubjectRef) (σ : GraphState) {a b : NodeKey},
      (a, b) ∈ (σ.reconcileKey T dt on R e cands).edges →
      (a, b) ∈ σ.edges ∨
      ∃ (pre : List SubjectRef) (c : SubjectRef),
        pre <+: cands ∧ c ∈ cands ∧ a = subjNode c ∧ b = objNode ⟨dt, on⟩ R ∧
        (σ.reconcileKey T dt on R e pre).checkFn T c dt on R e = true := by
  intro cands
  induction cands with
  | nil =>
    intro σ a b h
    rw [show σ.reconcileKey T dt on R e [] = σ from rfl] at h
    exact Or.inl h
  | cons s0 rest ih =>
    intro σ a b h
    have hfold : σ.reconcileKey T dt on R e (s0 :: rest)
        = (if σ.checkFn T s0 dt on R e then σ.writeDirect ⟨s0, R, ⟨dt, on⟩⟩ else σ).reconcileKey
            T dt on R e rest := by
      unfold GraphState.reconcileKey; rw [List.foldl_cons]
    rw [hfold] at h
    set σ1 := if σ.checkFn T s0 dt on R e then σ.writeDirect ⟨s0, R, ⟨dt, on⟩⟩ else σ with hσ1
    rcases ih σ1 h with hin1 | ⟨pre, c, hpre, hc, ha, hb, hchk⟩
    · -- the edge is present at the head-step state `σ1`
      by_cases hguard : σ.checkFn T s0 dt on R e = true
      · rw [hσ1, if_pos hguard, writeDirect_edges] at hin1
        split at hin1
        · rcases List.mem_cons.mp hin1 with heq | hmem0
          · exact Or.inr ⟨[], s0, List.nil_prefix, List.mem_cons_self,
              congrArg Prod.fst heq, congrArg Prod.snd heq,
              by rw [show σ.reconcileKey T dt on R e [] = σ from rfl]; exact hguard⟩
          · exact Or.inl hmem0
        · exact Or.inl hin1
      · rw [hσ1, if_neg hguard] at hin1; exact Or.inl hin1
    · -- the edge appears in the rest-fold from `σ1`; prepend `s0` to its prefix
      obtain ⟨tl, htl⟩ := hpre
      refine Or.inr ⟨s0 :: pre, c, ⟨tl, by rw [List.cons_append, htl]⟩,
        List.mem_cons_of_mem _ hc, ha, hb, ?_⟩
      have : σ.reconcileKey T dt on R e (s0 :: pre)
          = σ1.reconcileKey T dt on R e pre := by
        unfold GraphState.reconcileKey; rw [List.foldl_cons]
      rw [this]; exact hchk

/-- **A derived R-node has no in-edge in a rule-routed base.** A closure tuple landing
    on `objNode ⟨dt,on⟩ R` would be either a stored `(dt,R)` tuple (none — a `ComputedOnly` def
    has no `Direct` arm, `StoreValidRules`) or a rewrite output `(dt,R)` (none —
    `noRuleOutputs_of_derived`, from the taint filter). So the untainted base never feeds the
    R-node; every in-edge is a reconcile edge. -/
theorem reachedByRules_derived_no_inedge {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String} {e : Expr}
    (hSV : StoreValidRules S T)
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true) (hco : ComputedOnly e)
    (h : ReachedByRules σ S T) :
    ∀ x, (x, objNode ⟨dt, on⟩ R) ∉ σ.edges := by
  intro x hx
  obtain ⟨t, ht, u, hu, _hasub, hbobj⟩ := reachedByRules_edge_sound h x _ hx
  have htype : dt = u.object.type := by
    simpa [objNode_type] using congrArg NodeKey.type hbobj
  have hrel : R = u.relation := by
    simpa [objNode_pred] using congrArg NodeKey.pred hbobj
  rcases rewriteClosure_produced hu with heq | ⟨r, hr', hro, hrout⟩
  · rw [heq] at htype hrel
    obtain ⟨e', rs, hlk', hrs, _⟩ := hSV t ht
    rw [← htype, ← hrel, hlk, Option.some.injEq] at hlk'
    rw [← hlk', exprDirects_computedOnly hco] at hrs
    simp at hrs
  · exact noRuleOutputs_of_derived hder r hr' ⟨hro.trans htype.symm, hrout.trans hrel.symm⟩

/-- **Derived-edge soundness (the forward half).** On a W3a-admitted state, every materialised
    derived edge `subjNode s → objNode ⟨dt,on⟩ R` (bare, star-free `s`; `on ≠ STAR`) witnesses
    `sem S T ⟨s,R,⟨dt,on⟩⟩ = true`. By induction over the write path: the base leg cannot feed the
    derived R-node (`reachedByRules_derived_no_inedge`); a reconcile leg either inherits
    the edge (IH — the predecessor is W3a-admitted) or wrote it fresh, and then the guard at a
    W3a-admitted prefix mid-state gives `sem` via `checkFn_eq_sem`. -/
theorem reachedByW3aAdmitted_derived_edge_sound {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : ReachedByW3aAdmitted σ S T) :
    ∀ {s : SubjectRef} {dt on R : String} {e : Expr},
      S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      s.name ≠ STAR → on ≠ STAR →
      (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges → sem S T ⟨s, R, ⟨dt, on⟩⟩ = true := by
  -- `induction` generalises the schema/store, reverting the S/T-dependent fragment facts into
  -- each case; re-introduce them (order = signature) and thread them through the IH.
  induction h with
  | base hr =>
    intro s dt on R e hlk hder _hs _hon hedge
    exact absurd hedge (reachedByRules_derived_no_inedge hSV hlk hder (hCO _ _ _ hlk hder)
      (reachedByRules_of_admitted hr) (subjNode s))
  | reconcile dt' on' R' e' cands hRne hcands hder' hlke' hcStar honStar hprev ih =>
    intro s dt on R e hlk hder hs hon hedge
    rcases reconcileKey_edge_guard cands _ hedge with hin | ⟨pre, c, hpre, hc, ha, hb, hchk⟩
    · exact ih hWF hTT hNK hR hSV hSF hMatch hStrat hterm hCO hLU hlk hder hs hon hin
    · -- match endpoints: c = s, (dt',on',R') = (dt,on,R)
      obtain ⟨hdt, hon', hRR⟩ := objNode_inj_of_ne_star hon honStar hb
      subst hdt; subst hon'; subst hRR
      have hcs : c = s := (subjNode_inj_of_ne_star hs (hcStar c hc) ha).symm
      subst hcs
      -- the prefix mid-state is W3a-admitted; checkFn there = sem (via the def `e'` at key (dt,R))
      have hpremem : ∀ x ∈ pre, x ∈ cands := fun x hx => hpre.subset hx
      have hmid := ReachedByW3aAdmitted.reconcile dt on R e' pre hRne
        (fun x hx => hcands x (hpremem x hx)) hder' hlke'
        (fun x hx => hcStar x (hpremem x hx)) honStar hprev
      have hsem := checkFn_eq_sem hWF hTT hNK hR hSV hSF hCO hMatch hStrat hterm hmid
        hlke' (hCO _ _ _ hlke' hder') (hLU _ _ _ hlke' hder') (hcStar c hc) honStar
      rw [hchk] at hsem
      exact hsem.symm

/-! ## Candidate completeness — a `sem`-true bare subject is materialised

The backward half: on a suitably-covered W3a-admitted state, `sem S T ⟨s,R,⟨dt,on⟩⟩ = true` (bare
star-free `s`) implies the derived edge is present. The reconcile pass covering `(dt,on,R)`
enumerates `s`; its guard (`checkFn` at every prefix mid-state) is `sem = true` (`checkFn_eq_sem`),
so the edge is admitted (the derived R-node is terminal, so no cycle rejects it) and persists.

Coverage is modelled by an explicit list of reconcile *jobs* over an admitted base — faithful to
`reconcile`/`_leaf_concretes` (`processor.py:382-423,497-507`): the processor enumerates, per
derived key/object, all concrete candidate subjects. The completeness hypothesis is that this
enumeration is *complete* (covers every `sem`-member) — a property of the construction, not the
edge conclusion. -/

/-- A node with no out-edge reaches nothing (`NReaches` is head-oriented). -/
theorem nreaches_no_source {edges : List (NodeKey × NodeKey)} {b a : NodeKey}
    (hb : ∀ y, (b, y) ∉ edges) : ¬ NReaches edges b a := by
  intro h; cases h with
  | edge hbv => exact hb _ hbv
  | head hbw _ => exact hb _ hbw

/-- **A `sem`-true candidate's edge is materialised by the reconcile pass.** If `s ∈ cands`, the
    derived R-node is terminal in the base `σ` (`hRns` — maintained across the fold), and the guard
    `checkFn` holds for `s` at every prefix mid-state (`hguard` — discharged via `checkFn_eq_sem`
    since `sem = true`), then the reconcile pass materialises `subjNode s → objNode ⟨dt,on⟩ R`. The
    write is admitted: the endpoints differ (`s` bare, `R ≠ BARE`) and the R-node has no in-path
    (terminal), so no cycle rejects it; the edge then persists to the end of the pass. -/
theorem reconcileKey_edge_present {T : Store} {dt on R : String} {e : Expr} (hRne : R ≠ BARE)
    {s : SubjectRef} :
    ∀ (cands : List SubjectRef) (σ : GraphState), (∀ c ∈ cands, c.predicate = BARE) →
      s ∈ cands → (∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges) →
      (∀ pre, pre <+: cands → (σ.reconcileKey T dt on R e pre).checkFn T s dt on R e = true) →
      (subjNode s, objNode ⟨dt, on⟩ R) ∈ (σ.reconcileKey T dt on R e cands).edges := by
  -- a bare-sourced write onto the R-node is never a self-loop (BARE ≠ R)
  have hsrcne : ∀ c : SubjectRef, c.predicate = BARE → subjNode c ≠ objNode ⟨dt, on⟩ R := by
    intro c hcb heq
    have := congrArg NodeKey.pred heq
    rw [subjNode_pred, objNode_pred, hcb] at this
    exact hRne this.symm
  intro cands
  induction cands with
  | nil => intro σ _ hmem _ _; exact absurd hmem List.not_mem_nil
  | cons s0 rest ih =>
    intro σ hcb hmem hRns hguard
    have hs0b : s0.predicate = BARE := hcb s0 List.mem_cons_self
    have hfold : σ.reconcileKey T dt on R e (s0 :: rest)
        = (if σ.checkFn T s0 dt on R e then σ.writeDirect ⟨s0, R, ⟨dt, on⟩⟩ else σ).reconcileKey
            T dt on R e rest := by
      unfold GraphState.reconcileKey; rw [List.foldl_cons]
    -- the head write admits when its guard fires (R-node terminal ⇒ no back-path; distinct preds)
    have hadmit : σ.admitEdge (subjNode s0) (objNode ⟨dt, on⟩ R) = true := by
      unfold GraphState.admitEdge
      have hnr : σ.reach (objNode ⟨dt, on⟩ R) (subjNode s0) = false := by
        by_contra hc
        rw [Bool.not_eq_false] at hc
        exact nreaches_no_source hRns (reach_sound hc)
      rw [Bool.and_eq_true, bne_iff_ne]; exact ⟨hsrcne s0 hs0b, by rw [hnr]; rfl⟩
    rcases List.mem_cons.mp hmem with rfl | hmemrest
    · -- s = s0: its guard fires at the empty prefix, so the write materialises the edge
      have hg0 : σ.checkFn T s dt on R e = true := hguard [] List.nil_prefix
      rw [hfold, if_pos hg0]
      refine reconcileKey_edges_mono _ dt on R e rest _ ?_
      rw [writeDirect_edges, if_pos hadmit]
      exact List.mem_cons_self
    · -- s ∈ rest: recurse from the head-step state (R-node still terminal, guard transfers)
      rw [hfold]
      set σ1 := if σ.checkFn T s0 dt on R e then σ.writeDirect ⟨s0, R, ⟨dt, on⟩⟩ else σ with hσ1
      have hRns1 : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ1.edges := by
        intro y hy
        by_cases hg : σ.checkFn T s0 dt on R e = true
        · rw [hσ1, if_pos hg, writeDirect_edges, if_pos hadmit] at hy
          rcases List.mem_cons.mp hy with heq | hmem0
          · exact hsrcne s0 hs0b (congrArg Prod.fst heq).symm
          · exact hRns y hmem0
        · rw [hσ1, if_neg hg] at hy; exact hRns y hy
      have hguard1 : ∀ pre, pre <+: rest →
          (σ1.reconcileKey T dt on R e pre).checkFn T s dt on R e = true := by
        intro pre hpre
        have : σ1.reconcileKey T dt on R e pre = σ.reconcileKey T dt on R e (s0 :: pre) := by
          unfold GraphState.reconcileKey; rw [List.foldl_cons]
        rw [this]
        obtain ⟨tl, htl⟩ := hpre
        exact hguard (s0 :: pre) ⟨tl, by rw [List.cons_append, htl]⟩
      exact ih σ1 (fun c hc => hcb c (List.mem_cons_of_mem _ hc)) hmemrest hRns1 hguard1

/-! ## The W3a-complete state — an admitted base plus a coverage-complete batch of reconcile jobs

A W3a-complete state is an admitted rule-routed base with a batch of reconcile jobs (one per derived
key/object), whose candidate enumeration is *complete*: every `sem`-true bare subject for a derived
key is enumerated. Faithful to `build_index`/`reconcile` (`processor.py`): the processor reconciles
every derived key over every object, enumerating all concrete candidates (`_leaf_concretes`). The
completeness clause is a property of the *enumeration* (which subjects were fed to `reconcile`), not
of the edge conclusion. -/

/-- A reconcile job: reconcile derived key `(dt, R)` at object name `on` (def `e`) over `cands`. -/
structure W3aJob where
  dt : String
  on : String
  R : String
  e : Expr
  cands : List SubjectRef
deriving Repr

/-- Apply one reconcile job. -/
def W3aJob.apply (T : Store) (σ : GraphState) (j : W3aJob) : GraphState :=
  σ.reconcileKey T j.dt j.on j.R j.e j.cands

/-- Run a batch of reconcile jobs left-to-right over a base state. -/
def reconcileJobs (T : Store) (σ0 : GraphState) (jobs : List W3aJob) : GraphState :=
  jobs.foldl (W3aJob.apply T) σ0

/-- A job is valid on `S` iff it targets a declared *derived* key with its compiled def, over
    star-free bare candidates at a star-free object — exactly a `ReachedByW3aAdmitted.reconcile`
    leg's side conditions. -/
def W3aJobValid (S : Schema) (j : W3aJob) : Prop :=
  j.R ≠ BARE ∧ (∀ c ∈ j.cands, c.predicate = BARE) ∧ isDerived S (j.dt, j.R) = true ∧
    S.lookup (j.dt, j.R) = some j.e ∧ (∀ c ∈ j.cands, c.name ≠ STAR) ∧ j.on ≠ STAR

/-- Running valid jobs over any W3a-admitted state keeps it W3a-admitted (each job is a reconcile
    leg). Base generalised so the fold recurses. -/
theorem reconcileJobs_pres {S : Schema} {T : Store} :
    ∀ (jobs : List W3aJob) (σ : GraphState), ReachedByW3aAdmitted σ S T →
      (∀ j ∈ jobs, W3aJobValid S j) → ReachedByW3aAdmitted (reconcileJobs T σ jobs) S T := by
  intro jobs
  induction jobs with
  | nil => intro σ h _; exact h
  | cons j js ih =>
    intro σ h hv
    obtain ⟨hRne, hcb, hder, hlke, hcStar, hon⟩ := hv j List.mem_cons_self
    have hstep : ReachedByW3aAdmitted (j.apply T σ) S T :=
      ReachedByW3aAdmitted.reconcile j.dt j.on j.R j.e j.cands hRne hcb hder hlke hcStar hon h
    have : reconcileJobs T σ (j :: js) = reconcileJobs T (j.apply T σ) js := by
      unfold reconcileJobs; rw [List.foldl_cons]
    rw [this]
    exact ih (j.apply T σ) hstep (fun j' hj' => hv j' (List.mem_cons_of_mem _ hj'))

/-- Jobs only add edges: base edges survive the whole batch. -/
theorem reconcileJobs_edges_mono {T : Store} :
    ∀ (jobs : List W3aJob) (σ : GraphState) (ab : NodeKey × NodeKey),
      ab ∈ σ.edges → ab ∈ (reconcileJobs T σ jobs).edges := by
  intro jobs
  induction jobs with
  | nil => intro σ ab h; exact h
  | cons j js ih =>
    intro σ ab h
    have : reconcileJobs T σ (j :: js) = reconcileJobs T (j.apply T σ) js := by
      unfold reconcileJobs; rw [List.foldl_cons]
    rw [this]
    exact ih (j.apply T σ) ab (reconcileKey_edges_mono T j.dt j.on j.R j.e j.cands ab h)

/-- **`W3aComplete S T σ`** — `σ` is an admitted rule-routed base with a coverage-complete batch of
    reconcile jobs. The base + jobs supply the `ReachedByW3aAdmitted` structure (soundness); the
    coverage clause (every `sem`-true bare subject for a derived key/object is enumerated in some
    job) supplies backward completeness. -/
def W3aComplete (S : Schema) (T : Store) (σ : GraphState) : Prop :=
  ∃ (σ0 : GraphState) (jobs : List W3aJob),
    ReachedByRulesAdmitted σ0 S T ∧ σ = reconcileJobs T σ0 jobs ∧
    (∀ j ∈ jobs, W3aJobValid S j) ∧
    (∀ dt on R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ s : SubjectRef, s.predicate = BARE → s.name ≠ STAR → on ≠ STAR →
        sem S T ⟨s, R, ⟨dt, on⟩⟩ = true →
        ∃ j ∈ jobs, j.dt = dt ∧ j.on = on ∧ j.R = R ∧ s ∈ j.cands)

/-- A W3a-complete state is W3a-admitted. -/
theorem w3aComplete_reached {S : Schema} {T : Store} {σ : GraphState}
    (h : W3aComplete S T σ) : ReachedByW3aAdmitted σ S T := by
  obtain ⟨σ0, jobs, h0, hσ, hv, _⟩ := h
  rw [hσ]; exact reconcileJobs_pres jobs σ0 (ReachedByW3aAdmitted.base h0) hv

/-- **Candidate completeness (the backward half).** On a W3a-complete state, a `sem`-true bare
    star-free subject `s` at a derived key `(dt,R)` (`on ≠ STAR`) has its derived edge materialised:
    the covering job enumerates `s`; its guard is `sem = true` at every prefix mid-state
    (`checkFn_eq_sem`); the write is admitted (terminal derived R-node) and persists through
    the remaining jobs. -/
theorem w3aComplete_derived_edge {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : W3aComplete S T σ)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hder : isDerived S (dt, R) = true)
    (hsb : s.predicate = BARE) (hs : s.name ≠ STAR) (hon : on ≠ STAR)
    (hsem : sem S T ⟨s, R, ⟨dt, on⟩⟩ = true) :
    (subjNode s, objNode ⟨dt, on⟩ R) ∈ σ.edges := by
  obtain ⟨σ0, jobs, h0, hσ, hv, hcov⟩ := h
  obtain ⟨j, hj, hjdt, hjon, hjR, hjs⟩ := hcov dt on R e hlk hder s hsb hs hon hsem
  obtain ⟨hjRne, hjcb, hjder, hjlke, hjcStar, hjon'⟩ := hv j hj
  -- align the query key/def with the covering job's
  subst hjdt; subst hjon; subst hjR
  have hje : e = j.e := Option.some.inj (hlk.symm.trans hjlke)
  subst hje
  -- split the jobs at the covering job
  obtain ⟨pre, post, hsplit⟩ := List.append_of_mem hj
  have hσpre : ReachedByW3aAdmitted (reconcileJobs T σ0 pre) S T := by
    refine reconcileJobs_pres pre σ0 (ReachedByW3aAdmitted.base h0) ?_
    intro j' hj'; exact hv j' (hsplit ▸ List.mem_append_left _ hj')
  set σpre := reconcileJobs T σ0 pre with hσpre_def
  -- R-node terminal in σpre
  obtain ⟨hnt, hns⟩ := hterm j.dt j.R hder
  have hRns : ∀ y, (objNode ⟨j.dt, j.on⟩ j.R, y) ∉ σpre.edges :=
    reachedByW3a_Rnode_not_source hnt hns hjRne
      (reachedByW3aAdmitted_toW3a hσpre) (objNode_pred ⟨j.dt, j.on⟩ j.R)
  -- guard: checkFn = sem = true at every prefix mid-state
  have hguard : ∀ pre', pre' <+: j.cands →
      (σpre.reconcileKey T j.dt j.on j.R j.e pre').checkFn T s j.dt j.on j.R j.e = true := by
    intro pre' hpre'
    have hcbpre : ∀ c ∈ pre', c.predicate = BARE := fun c hc => hjcb c (hpre'.subset hc)
    have hcSpre : ∀ c ∈ pre', c.name ≠ STAR := fun c hc => hjcStar c (hpre'.subset hc)
    have hmid : ReachedByW3aAdmitted (σpre.reconcileKey T j.dt j.on j.R j.e pre') S T :=
      ReachedByW3aAdmitted.reconcile j.dt j.on j.R j.e pre' hjRne hcbpre hder hlk hcSpre hon hσpre
    have := checkFn_eq_sem hWF hTT hNK hR hSV hSF hCO hMatch hStrat hterm hmid
      hlk (hCO _ _ _ hlk hder) (hLU _ _ _ hlk hder) hs hon
    rw [this, hsem]
  -- the covering job materialises the edge; it persists through `post`
  have hedge_j : (subjNode s, objNode ⟨j.dt, j.on⟩ j.R) ∈ (j.apply T σpre).edges := by
    show (subjNode s, objNode ⟨j.dt, j.on⟩ j.R) ∈
      (σpre.reconcileKey T j.dt j.on j.R j.e j.cands).edges
    exact reconcileKey_edge_present hjRne j.cands σpre hjcb hjs hRns hguard
  -- reassemble: σ = reconcileJobs (j.apply σpre) post
  have hσeq : σ = reconcileJobs T (j.apply T σpre) post := by
    rw [hσ, hsplit, hσpre_def]
    unfold reconcileJobs
    rw [List.foldl_append, List.foldl_cons]
  rw [hσeq]
  exact reconcileJobs_edges_mono post (j.apply T σpre) _ hedge_j

/-! ## The W3a assembly — `check = sem` on bare-subject star-free queries

Combining soundness and completeness with the read collapse. Scope: **bare-subject** star-free
queries — the derived read on a residue-empty state is the bare edge probe, so it can only decide
bare subjects (an attack-first `#eval` confirmed a userset subject on a derived key can be
`sem`-true while the residue-empty read is `false`; userset subjects are W3b's `upos` residue). -/

/-- A derived key is declared, so it has a compiled def. -/
theorem isDerived_declared {S : Schema} {k : String × String} (h : isDerived S k = true) :
    ∃ e, S.lookup k = some e := by
  have hmem : k ∈ taintedKeys S := by
    unfold isDerived at h; rw [List.contains_eq_mem] at h; exact of_decide_eq_true h
  exact lookup_some_of_mem S (taintChain_subset_keys S S.keys.length k hmem)

/-- **T2b, W3a fragment (`graph_correct_w3a`) — `check = sem` on bare-subject star-free queries.**
    On a W3a-complete state over the mixed (one `ComputedOnly` derived key per untainted operand cone)
    fragment, the graph read equals the specification for every bare-subject star-free query.

    * **Untainted query:** the read routes to `probeNonDerived`, which reduces to the admitted base
      (`graphRec_reduce_base_adm`) whose read is `sem` (`graphRec_base_eq`).
    * **Derived query:** the residue-empty read collapses to the bare edge probe
      (`check_derived_ResidueEmpty`); `reach ↔ sem` glues via soundness (reach ⇒ single reconcile
      edge ⇒ `sem`, `reachedByW3aAdmitted_derived_edge_sound`) and completeness (`sem` ⇒ the covering
      job's edge ⇒ reach, `w3aComplete_derived_edge`). -/
theorem graph_correct_w3a {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T) (hSF : StarFreeStore T)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : W3aComplete S T σ)
    (hqbare : q.subject.predicate = BARE) (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem S T q := by
  have hadm := w3aComplete_reached h
  have hInv := (reachedByW3a_inv (reachedByW3aAdmitted_toW3a hadm)).1
  have hcl := hInv.edgesClosed
  by_cases hder : isDerived S (q.object.type, q.relation) = true
  · -- derived query: residue-empty edge probe, glued by soundness/completeness
    have hre : ResidueEmpty σ := reachedByW3a_residueEmpty (reachedByW3aAdmitted_toW3a hadm)
    have hderσ : isDerived σ.schema (q.object.type, q.relation) = true := by rw [hInv.schemaEq]; exact hder
    rw [GraphModel.check_derived_ResidueEmpty hre q hderσ]
    have e1 : (q.object.name != STAR) = true := by rw [bne_iff_ne]; exact hqo
    have e2 : (q.subject.name != STAR) = true := by rw [bne_iff_ne]; exact hqs
    have e3 : (q.subject.predicate == BARE) = true := by rw [beq_iff_eq]; exact hqbare
    rw [e1, e2, e3, Bool.true_and, Bool.true_and, Bool.true_and]
    obtain ⟨e, hlk⟩ := isDerived_declared hder
    have hco : ComputedOnly e := hCO _ _ _ hlk hder
    -- `reach ↔ sem`
    have hfwd : σ.reach (subjNode q.subject) (objNode q.object q.relation) = true →
        sem S T q = true := by
      intro hr
      have hN := reach_sound hr
      have hedge := reachedByW3a_reach_collapse_root hWF hSV hlk hder hco
        (reachedByW3aAdmitted_toW3a hadm) hN
      exact reachedByW3aAdmitted_derived_edge_sound hWF hTT hNK hR hSV hSF hMatch hStrat
        hterm hCO hLU hadm hlk hder hqs hqo hedge
    have hbwd : sem S T q = true →
        σ.reach (subjNode q.subject) (objNode q.object q.relation) = true := by
      intro hsemq
      have hedge := w3aComplete_derived_edge hWF hTT hNK hR hSV hSF hMatch hStrat hterm hCO hLU
        h hlk hder hqbare hqs hqo hsemq
      exact reach_complete hcl (NReaches.edge hedge)
    cases hr : σ.reach (subjNode q.subject) (objNode q.object q.relation) <;>
      cases hsm : sem S T q <;> simp_all
  · -- untainted query: reduce the non-derived probe to the admitted base
    have hd : isDerived S (q.object.type, q.relation) = false := by
      simpa using hder
    have hroute : GraphModel.check σ q = GraphModel.probeNonDerived σ q := by
      unfold GraphModel.check; rw [hInv.schemaEq, hd]; simp
    rw [hroute]
    obtain ⟨σ0, hσ0adm, hredx⟩ :=
      graphRec_reduce_base_adm hSF hterm hadm (s := q.subject)
        (dt := q.object.type) (on := q.object.name)
    have h2 := hredx q.relation hd
    have h3 := graphRec_base_eq hWF hTT hNK hR hSV hSF hCO hMatch hσ0adm hqs hqo q.relation hd
    -- graphRec σ q.subject … q.relation = probeNonDerived σ q  (definitional, via ObjectRef eta)
    show GraphModel.probeNonDerived σ q = sem S T q
    calc GraphModel.probeNonDerived σ q
        = GraphModel.graphRec σ q.subject q.object.type q.object.name q.relation := rfl
      _ = GraphModel.graphRec σ0 q.subject q.object.type q.object.name q.relation := h2
      _ = sem S T ⟨q.subject, q.relation, ⟨q.object.type, q.object.name⟩⟩ := h3
      _ = sem S T q := rfl

/-! ## The STAR-RELAXED `checkFn ↔ sem` stack (W3c read half, step 1 cont.)

`checkFn_eq_sem` without `StarFreeStore`, subject-generic up to star-BARE subjects — the
form the W3c `coveredFn` correspondence consumes. Two star-free shortcuts are replaced:

* `graphRec_reduce_base_adm` killed the wildcard probes 2–4 via plain edges
  (`probeNonDerived_plainEdges`). Star grants make probe 2 LIVE, so
  `graphRec_reduce_base_adm_bs` instead transfers ALL FOUR probes to the base: every probe
  target — `objNode ⟨dt,on⟩ r'` and `wAllNode dt r'` — carries the untainted key
  `(dt, r')`, so the multi-pass reach-inertness (`reachedByW3aAdmitted_reach_inert`, which
  never needed star-freeness) applies to each probe verbatim.
* the base equation is `graphRec_base_eq_bs` (`RestrictBase.lean`). -/

/-- **The operand read reduces to an admitted base — star-relaxed, all four probes.** -/
theorem graphRec_reduce_base_adm_bs {σ : GraphState} {S : Schema} {T : Store}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3aAdmitted σ S T) {s : SubjectRef} {dt on : String} :
    ∃ σ0, ReachedByRulesAdmitted σ0 S T ∧
      ∀ r', isDerived S (dt, r') = false →
        GraphModel.graphRec σ s dt on r' = GraphModel.graphRec σ0 s dt on r' := by
  obtain ⟨σ0, hσ0, hsub, htrans⟩ := reachedByW3aAdmitted_reach_inert hterm h
  refine ⟨σ0, hσ0, ?_⟩
  intro r' hunt
  have hcl_σ := (reachedByW3a_inv (reachedByW3aAdmitted_toW3a h)).1.edgesClosed
  have hcl_σ0 := (reachedByRules_inv (reachedByRules_of_admitted hσ0)).1.edgesClosed
  -- `reach` agrees between σ and σ0 at every untainted-key target
  have key : ∀ (u v : NodeKey), isDerived S (v.type, v.pred) = false →
      σ.reach u v = σ0.reach u v := by
    intro u v hv
    cases h1 : σ.reach u v <;> cases h2 : σ0.reach u v <;> try rfl
    · exfalso
      have := reach_complete hcl_σ (NReaches.mono_subset hsub (reach_sound h2))
      rw [h1] at this; exact absurd this (by decide)
    · exfalso
      have := reach_complete hcl_σ0 (htrans hv (reach_sound h1))
      rw [h2] at this; exact absurd this (by decide)
  -- both probe targets carry the untainted key (dt, r')
  have hobj : isDerived S ((objNode ⟨dt, on⟩ r').type, (objNode ⟨dt, on⟩ r').pred) = false := by
    rw [objNode_type, objNode_pred]; exact hunt
  have hall : isDerived S ((wAllNode dt r').type, (wAllNode dt r').pred) = false := hunt
  show GraphModel.probeNonDerived σ ⟨s, r', ⟨dt, on⟩⟩
     = GraphModel.probeNonDerived σ0 ⟨s, r', ⟨dt, on⟩⟩
  unfold GraphModel.probeNonDerived
  simp only
  rw [key (subjNode s) _ hobj, key (wAnyNode (SubjectRef.shape s)) _ hobj,
      key (subjNode s) _ hall, key (wAnyNode (SubjectRef.shape s)) _ hall]

/-- **`checkFn` equals `sem` given the operand reads reduce to an admitted base —
    star-relaxed** (mirror of `checkFn_eq_sem_of_base` over `graphRec_base_eq_bs`;
    star-BARE subjects included). -/
theorem checkFn_eq_sem_of_base_bs {S : Schema} {T : Store} {σ σ0 : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (h0 : ReachedByRulesAdmitted σ0 S T)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hinert : ∀ r' ∈ computedRefs e,
      GraphModel.graphRec σ s dt on r' = GraphModel.graphRec σ0 s dt on r')
    (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  have hDecl : StoreDeclared S T := storeDeclared_of_validRules hSV
  have hag : ∀ r' ∈ computedRefs e,
      GraphModel.graphRec σ s dt on r'
        = semAux S s T ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r' := by
    intro r' hr'
    rw [hinert r' hr',
        graphRec_base_eq_bs hWF hTT hNK hR hSV hBS hTS hCO hMatch h0 hs hon r'
          (hleafUnt r' hr')]
    show sem S T ⟨s, r', ⟨dt, on⟩⟩ = semAux S s T ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r'
    exact semAux_qirrel S s T ⟨s, r', ⟨dt, on⟩⟩ ⟨s, R, ⟨dt, on⟩⟩ (fuelBound S T) dt on r'
  rw [checkFn_eq_semStep (S := S) (σ := σ) (T := T) (q := ⟨s, R, ⟨dt, on⟩⟩) hlk hco hag]
  exact sem_fuel_stable S T ⟨s, R, ⟨dt, on⟩⟩ hStrat hDecl (fuelBound S T + 1) (Nat.le_succ _)

/-- **`checkFn` equals `sem` on a W3a-admitted state — star-relaxed.** No `StarFreeStore`;
    the query subject may be star-BARE (the `coveredFn` reads). Composition of
    `graphRec_reduce_base_adm_bs` and `checkFn_eq_sem_of_base_bs`. -/
theorem checkFn_eq_sem_bs {S : Schema} {T : Store} {σ : GraphState}
    (hWF : WF S) (hTT : TtuTuplesetsDirect S) (hNK : NodupKeys S)
    (hR : RewriteRanked S) (hSV : StoreValidRules S T)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3aAdmitted σ S T)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hs : s.name = STAR → s.predicate = BARE) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  obtain ⟨σ0, h0, hred⟩ := graphRec_reduce_base_adm_bs hterm h (s := s) (dt := dt) (on := on)
  exact checkFn_eq_sem_of_base_bs hWF hTT hNK hR hSV hBS hTS hCO hMatch hStrat h0 hlk hco
    hleafUnt (fun r' hr' => hred r' (hleafUnt r' hr')) hs hon

end Zanzibar
