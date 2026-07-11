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
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
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
        graphRec_base_eq hWF hTT hNK hR hSV hSF hRootB hMatch h0 hs hon r' (hleafUnt r' hr')]
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
      (hder : isDerived S (dt, R) = true)
      (hcStar : ∀ c ∈ cands, c.name ≠ STAR) (honStar : on ≠ STAR) :
      ReachedByW3aAdmitted σ S T → ReachedByW3aAdmitted (σ.reconcileKey T dt on R e cands) S T

/-- The admitted W3a closure forgets to the plain W3a closure — all soundness lemmas transfer. -/
theorem reachedByW3aAdmitted_toW3a {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3aAdmitted σ S T) : ReachedByW3a σ S T := by
  induction h with
  | base hr => exact ReachedByW3a.base (reachedByRules_of_admitted hr)
  | reconcile dt on R e cands hRne hcands hder hcStar honStar _ ih =>
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
  | reconcile dt on R e cands hRne hcands hder _hcStar _honStar h' ih =>
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
    (hRootB : ∀ d ∈ S.defs, isDerived S d.1 = true → RootBoolean d.2)
    (hMatch : RewriteMatchDeclared S) (hStrat : Stratifiable S)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (h : ReachedByW3aAdmitted σ S T)
    {s : SubjectRef} {dt on R : String} {e : Expr}
    (hlk : S.lookup (dt, R) = some e) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hs : s.name ≠ STAR) (hon : on ≠ STAR) :
    σ.checkFn T s dt on R e = sem S T ⟨s, R, ⟨dt, on⟩⟩ := by
  obtain ⟨σ0, h0, hred⟩ := graphRec_reduce_base_adm hSF hterm h (s := s) (dt := dt) (on := on)
  exact checkFn_eq_sem_of_base hWF hTT hNK hR hSV hSF hRootB hMatch hStrat h0 hlk hco hleafUnt
    (fun r' hr' => hred r' (hleafUnt r' hr')) hs hon

end Zanzibar
