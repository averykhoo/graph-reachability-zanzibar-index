import ZanzibarProofs.GraphIndex.ReconcileUposComplete

/-!
# The derived reconcile — star coverage and the `stars`/`neg` residue (ROADMAP W3c, write half)

`SEMANTICS.md` §7.6; `boolean spec §5.3-5.4`; `index_v4/processor.py` (`reconcile`,
`:382-459`: step 1 the star fold, step 2 the `neg` recompute, step 2c `upos`, step 3
the residue upsert, step 4 the edge audit; `reconcile_subject` `:321-380`:
`want_edge = should ∧ ¬covered` at `:359`); `index_v4/wildcard.py:398-432` (the full
residue read: bare ⇒ edge ∨ (shape ∈ stars ∧ ∉ neg), star ⇒ shape ∈ stars, userset ⇒
upos ∨ (shape ∈ stars ∧ ∉ neg)).

W3b lifted the bare-subject restriction; the store stayed **star-free**, so residues
carried only `upos`. **W3c makes the star-coverage content go live**: with `user:*`
grants on operand relations the processor persists

* `stars` — the star×boolean fold `plan.stars_fn` (`zanzibar_utils_v1.py:1533-1561`):
  per closure leaf, `leaf_stars` holds a declared wildcard shape `sh` iff the graph's
  *star-subject* read `widx.check(sh.pred, sh.type, '*', leaf, o)` is true
  (`processor.py:58-62`); `Union → ∪`, `Intersection → ∩`, `Exclusion → −` over those
  sets. **Pointwise this fold is exactly the boolean evaluation on the star subject**:
  `sh ∈ stars_fn(ctx) ⟺ check_fn(ctx, (sh.pred, sh.type, '*'))` — each set constructor
  matches the corresponding connective (`∪/∨`, `∩/∧`, `−/∧¬`). The model uses the
  pointwise form: `stars = shapes.filter (coveredFn := checkFn on the star subject)`.
* `neg` — star-covered ∧ expr-false concrete subjects (`processor.py:406-411`), and
* `upos` — with its `¬covered` guard now contentful (`:438-439`),

and the edge audit materialises an edge only for **uncovered** expr-true bare
subjects (`want_edge = should ∧ ¬covered`, `:359`) — a covered subject holds NO edge
(the space rule; the read answers it wholesale from `stars ∖ neg`).

**Attack-first (2026-07-11, machine-checked `#eval` vs `sem`, scratch deleted).** On
`viewer := member ∖ banned`, `viewer2 := member ∩ editor`, `viewer3 := (member ∩
editor) ∖ banned` (`member = direct ∪ computed editor`, `rsFull` admitting `user`,
`user:*`, `group#mem`) over 6 objects exercising: a star grant with concrete +
userset exclusions; a starred subtrahend (kills coverage); `and` of starred+unstarred
(not covered) and of two starred (covered); userset-driven `neg` under a star base;
star coverage arriving via D1 FLOW-THROUGH (`member@group:h#mem` + `group:h#mem@user:*`
— no direct star grant); a nested boolean root. The planned model's `check` equalled
`sem` on the full 342-query grid (bare incl. ghosts / star / userset / star-userset
subjects); a second full pass was idempotent; reversed key order with permuted and
DUPLICATED candidate lists agreed; covered subjects held zero edges (doc:1, doc:4);
`neg` captured concrete-under-star (bob), userset-driven exclusions (bob+carol via
`banned@group:g#mem`), and the nested root (eve); concrete-only exclusion did NOT
defeat the star query (stars true while bob ∈ neg). No refutation.

## What this file proves (and what it defers)

The **write model + T2a**: the wholesale residue recompute (`reconcileResidueKey`),
the covered-guarded edge fold (`reconcileKeyC`), the combined per-key reconcile
(`reconcileStarsKey`, faithful to `reconcile`'s residue-THEN-edge-audit order), the
W3c closure, its W3a shadow, and the full invariant `reachedByW3c_inv` — with
**every I6 clause contentful for the first time** (`negStarCovered`, `negEdgeFree`,
`uposEdgeFree`, `uposNegDisjoint`) and **no `StarFreeStore` hypothesis anywhere**:
the invariant layer is fully star-relaxed.

Three structural devices make it cheap:
1. **The covered-filter collapse** (`reconcileKeyC_eq_filter`): the covered guard is
   fold-constant (edge writes never touch residues), so the W3c edge fold IS the W3a
   `reconcileKey` on the covered-filtered candidate list — every W3a fold lemma
   transfers with zero new induction.
2. **The shadow projection** (`reachedByW3c_shadow`): residue writes are core-inert,
   so every W3c state has a W3a-admitted shadow with an identical core (the W3b
   pattern, `ReconcileUposComplete.lean`).
3. **Star-general operand-read inertness** (`graphRec_reconcileKey_inert` — NO
   `StarFreeStore`): a reconcile pass adds only edges onto its terminal R-node, so
   ALL FOUR probes of `probeNonDerived` at untainted keys are unchanged — subject-
   generic, including the star subjects `coveredFn` evaluates. This pins every
   persisted `stars` row to the *canonical* star set of the chain's base
   (`reachedByW3c_master`), which is what turns the space rule into `negEdgeFree`.

**Deferred (W3c read half):** `graph_correct_w3c` — the read ↔ `sem` correspondence
on star-carrying stores. It needs `graphRec_base_eq`/`checkFn_eq_sem` re-proved
without `StarFreeStore` (the W1 bare-star machinery composed with W2 rule routing:
wildcard probes 2–4 go live on the base). See HANDOFF "The next task".
-/

namespace Zanzibar

/-! ## Declared subject-wildcard shapes

`SchemaInfo.subject_wildcard_shapes` (`zanzibar_utils_v1.py`): the shapes `(type,
pred)` declared with a wildcard restriction anywhere in the schema. The processor
enumerates its star fold over exactly this (schema-fixed) list
(`DeltaProcessor.__init__`, `processor.py:135`; `leaf_stars`, `:60-62`). -/
def wildcardShapes (S : Schema) : List Shape :=
  S.defs.flatMap (fun d => (exprRestrictions d.2).filterMap
    (fun r => if r.2.2 then some (r.1, r.2.1) else none))

/-- The star subject of a shape — the intensional `(type, '*', pred)` probe subject
    (`leaf_stars` passes `'*'` as the subject name, `processor.py:62`). -/
def starSubj (sh : Shape) : SubjectRef := ⟨sh.1, STAR, sh.2⟩

@[simp] theorem starSubj_shape (sh : Shape) : (starSubj sh).shape = sh := rfl

/-! ## The write model -/

/-- **Star coverage of one shape = the star-subject `checkFn`.** The pointwise form
    of the compiled star fold `plan.stars_fn` (see the header: `∪/∩/−` over leaf star
    sets is `∨/∧/∧¬` over leaf star membership, and a closure leaf's star membership
    is the graph's star-subject read = `graphRec` at the leaf — the same dispatch
    `checkFn` uses). -/
def GraphState.coveredFn (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (sh : Shape) : Bool :=
  σ.checkFn T (starSubj sh) dt on R e

/-! ## The Direct-arm star/concrete coverage split (leg 5 sub-step 2)

`checkFn_eq_coveredFn_of_no_extra` (`CascadeEnum.lean`) says a star-free subject that
triggers no concrete leaf-reach reads as its shape-star's coverage. That is FALSE once the
def carries a bare `Direct` arm: a subject with its OWN concrete `[user]` grant reads the arm
`true`, but its shape-star reads it `false` (attack-first `#eval` KILL 2026-07-19: schema
`approver := excl (direct [user]) (computed banned)`, store `{(alice,approver,doc)}` — `checkFn
alice = true ≠ coveredFn * = false`; `directLeaf` at `alice` fires the bare-concrete match
disjunct that the star branch lacks). The FIX (probe-confirmed): gate the split on the subject
having NO concrete Direct-arm grant (`NoConcDirect`) — under it the bare-concrete match disjunct
is dead, so `directLeaf` at the subject reduces to the SAME `[user:*]`-coverage read as at the
star (both fire iff a bare STAR grant of the shape exists). Concrete grants are exactly the
subjects the coverage enumeration must additionally enumerate (sub-step 2's second half). -/

/-- A grant tuple whose subject is a bare CONCRETE match for `s` (the `directLeaf`
    bare-subject-branch disjunct that has no counterpart in the star branch). -/
def concMatch (s : SubjectRef) (g : Tuple) : Bool :=
  g.subject.name != STAR && g.subject.predicate == BARE
    && g.subject.type == s.type && g.subject.name == s.name

/-- **`NoConcDirect T s dt on rel e`** — subject `s` has no concrete grant on any `Direct`
    arm of `e` (same object `(dt, on)` / enclosing relation `rel`). The faithful gate under
    which the star/concrete coverage split holds: it kills exactly `directLeaf`'s
    bare-concrete match disjunct, leaving the `[user:*]`-coverage read shared with the star. -/
def NoConcDirect (T : Store) (s : SubjectRef) (dt on rel : String) : Expr → Prop
  | .computed _ => True
  | .direct rs => (grantsOf T rs dt on rel).any (concMatch s) = false
  | .union a b => NoConcDirect T s dt on rel a ∧ NoConcDirect T s dt on rel b
  | .inter a b => NoConcDirect T s dt on rel a ∧ NoConcDirect T s dt on rel b
  | .excl a b => NoConcDirect T s dt on rel a ∧ NoConcDirect T s dt on rel b
  | .ttu _ _ => True

/-- `List.any` congruence on members (order/multiplicity blind), local to this module. -/
theorem any_congr_mem {α : Type _} (l : List α) (f g : α → Bool)
    (h : ∀ x ∈ l, f x = g x) : l.any f = l.any g := by
  induction l with
  | nil => rfl
  | cons a t ih =>
    simp only [List.any_cons]
    rw [h a (List.mem_cons_self ..), ih (fun x hx => h x (List.mem_cons_of_mem a hx))]

/-- **The bare `Direct` leaf reads the same at a no-concrete-grant subject and its star.**
    For a bare-concrete `s` with no concrete grant (`hnc`) on a leaf whose restrictions are
    all bare (`hb`), `directLeaf` at `s` equals `directLeaf` at `starSubj s.shape`: both reduce
    to the shape's bare-STAR coverage read (`memberOfGranted` dead on bare grants; the
    concrete-match disjunct dead by `hnc`). Any `rec`/query on either side (bare-arm
    independence). -/
theorem directLeaf_star_of_noConc {rec1 rec2 : Rec} {T : Store} {q1 q2 : Query}
    {s : SubjectRef} {rs : List Restriction} {ot on rel : String}
    (hb : ∀ r ∈ rs, r.2.1 = BARE) (hsn : s.name ≠ STAR) (hsp : s.predicate = BARE)
    (hnc : (grantsOf T rs ot on rel).any (concMatch s) = false) :
    directLeaf rec1 s T q1 rs ot on rel
      = directLeaf rec2 (starSubj s.shape) T q2 rs ot on rel := by
  have hbareG : ∀ g ∈ grantsOf T rs ot on rel, g.subject.predicate = BARE :=
    grantsOf_bare_subjects T rs ot on rel hb
  have hmog : ∀ (rec : Rec) (q : Query),
      memberOfGranted rec T q (grantsOf T rs ot on rel) = false :=
    fun rec q => memberOfGranted_of_bareGrants rec T q _ hbareG
  unfold directLeaf
  have hsn' : (s.name == STAR) = false := beq_eq_false_iff_ne.mpr hsn
  have hstar : (starSubj s.shape).name == STAR := by
    show (STAR == STAR) = true; simp
  simp only [hsn', hsp, if_false, beq_self_eq_true, if_true, hstar, hmog, Bool.or_false,
    starSubj, SubjectRef.shape]
  -- LHS: any (concMatch ∨ starBare); RHS: any (starBare'); concMatch-any is false (hnc)
  rw [any_congr_mem _ _ (fun g =>
        (g.subject.name == STAR && g.subject.type == s.type && g.subject.predicate == BARE))]
  · -- from hnc + reordering: any(A ∨ B) = any B
    have : (grantsOf T rs ot on rel).any (fun g =>
        (g.subject.name != STAR && g.subject.predicate == BARE
          && g.subject.type == s.type && g.subject.name == s.name)
        || (g.subject.name == STAR && g.subject.predicate == BARE && g.subject.type == s.type))
      = (grantsOf T rs ot on rel).any (fun g =>
          g.subject.name == STAR && g.subject.type == s.type && g.subject.predicate == BARE) := by
      apply any_congr_mem
      intro g hg
      have hAg : concMatch s g = false := by
        have := List.any_eq_false.mp hnc g hg; simpa [concMatch] using this
      simp only [concMatch] at hAg
      -- A g = false; reorder B
      cases hb1 : (g.subject.name == STAR) <;>
        cases hb2 : (g.subject.type == s.type) <;>
        cases hb3 : (g.subject.predicate == BARE) <;>
        cases hb4 : (g.subject.name == s.name) <;>
        simp_all [Bool.and_eq_true, Bool.or_eq_true]
    exact this
  · intro g _; rfl

/-- **The star/concrete `evalE` split over a `ComputedOrDirect` tree.** Given a bare-concrete
    subject `s` with no concrete Direct-arm grant (`NoConcDirect`) and computed-leaf `rec`
    agreement between `s` and its star, `evalE` at `s` equals `evalE` at `starSubj s.shape`:
    computed leaves ride the `rec` agreement, bare `Direct` arms ride
    `directLeaf_star_of_noConc`. The `_cd` analog of the subject-varying `evalE_computedOnly`. -/
theorem evalE_star_of_noConc {rec1 rec2 : Rec} {T : Store} {q1 q2 : Query} {s : SubjectRef}
    {dt on rel : String} (hsn : s.name ≠ STAR) (hsp : s.predicate = BARE) :
    ∀ e : Expr, ComputedOrDirect e → DirectArmsBare e → NoConcDirect T s dt on rel e →
      (∀ r' ∈ computedRefs e, rec1 dt on r' = rec2 dt on r') →
      evalE rec1 s T q1 dt on rel e = evalE rec2 (starSubj s.shape) T q2 dt on rel e := by
  intro e
  induction e with
  | computed r' =>
    intro _ _ _ hag; simp only [evalE]; exact hag r' (List.mem_singleton.mpr rfl)
  | direct rs =>
    intro _ hb hnc _; simp only [evalE]
    exact directLeaf_star_of_noConc hb hsn hsp hnc
  | union a b iha ihb =>
    intro hcd hba hnc hag; simp only [evalE]
    rw [iha hcd.1 hba.1 hnc.1 (fun r' hr' => hag r' (List.mem_append_left _ hr')),
        ihb hcd.2 hba.2 hnc.2 (fun r' hr' => hag r' (List.mem_append_right _ hr'))]
  | inter a b iha ihb =>
    intro hcd hba hnc hag; simp only [evalE]
    rw [iha hcd.1 hba.1 hnc.1 (fun r' hr' => hag r' (List.mem_append_left _ hr')),
        ihb hcd.2 hba.2 hnc.2 (fun r' hr' => hag r' (List.mem_append_right _ hr'))]
  | excl a b iha ihb =>
    intro hcd hba hnc hag; simp only [evalE]
    rw [iha hcd.1 hba.1 hnc.1 (fun r' hr' => hag r' (List.mem_append_left _ hr')),
        ihb hcd.2 hba.2 hnc.2 (fun r' hr' => hag r' (List.mem_append_right _ hr'))]
  | ttu tr ts => intro hcd _ _ _; exact hcd.elim

/-- **The wholesale residue recompute** for one derived key (`reconcile` steps 1–3,
    `processor.py:388-446`): `stars` = the covered shapes; `neg` = the candidate
    subjects that are star-covered ∧ expr-false (`:406-411`); `upos` = the userset
    candidates that are uncovered ∧ expr-true (`:434-441`). One `putResidue` upsert
    (`_store_residue`); the model stores a possibly-empty row where Python deletes an
    all-empty one — read-equivalent via the `getD Residue.empty` default. -/
def GraphState.reconcileResidueKey (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) : GraphState :=
  let stars := shapes.filter (fun sh => σ.coveredFn T dt on R e sh)
  let neg := negCands.filter (fun c => stars.contains c.shape && !(σ.checkFn T c dt on R e))
  let upos := uposCands.filter (fun c => !(stars.contains c.shape) && σ.checkFn T c dt on R e)
  σ.putResidue (objNode ⟨dt, on⟩ R) R ⟨stars, neg, upos⟩

/-- Coverage as persisted: is the shape in the stored `stars` row?
    (`reconcile_subject` re-reads `_residue_state` per subject, `processor.py:341-342`.) -/
def GraphState.coveredAt (σ : GraphState) (k : NodeKey) (R : String) (sh : Shape) : Bool :=
  ((σ.residue k R).getD Residue.empty).stars.contains sh

/-- **The covered-guarded edge fold** (`reconcile` step 4 → `reconcile_subject`,
    `want_edge = should ∧ ¬covered`, `processor.py:359`): materialise the derived
    edge iff expr-true AND the subject's shape is not star-covered. `covered` reads
    the *persisted* row — which the fold never writes, so it is fold-constant. -/
def GraphState.reconcileKeyC (σ : GraphState) (T : Store) (dt on R : String) (e : Expr)
    (cands : List SubjectRef) : GraphState :=
  cands.foldl (fun acc c =>
    if acc.checkFn T c dt on R e && !(acc.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)
    then acc.writeDirect ⟨c, R, ⟨dt, on⟩⟩ else acc) σ

/-- **One full-object reconcile** (`reconcile`, `processor.py:382-459`): the residue
    recompute (steps 1–3) **then** the edge audit (step 4). The order is
    load-bearing: the edge fold's covered guard reads the row this pass just wrote
    (Python stores the residue at `:446` before auditing edges at `:450-455`). -/
def GraphState.reconcileStarsKey (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (cands negCands uposCands : List SubjectRef) :
    GraphState :=
  (σ.reconcileResidueKey T dt on R e shapes negCands uposCands).reconcileKeyC
    T dt on R e cands

/-! ## Structural equalities — the residue recompute is `putResidue`-only -/

@[simp] theorem reconcileResidueKey_edges (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKey T dt on R e shapes negCands uposCands).edges = σ.edges := rfl

@[simp] theorem reconcileResidueKey_nodes (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKey T dt on R e shapes negCands uposCands).nodes = σ.nodes := rfl

@[simp] theorem reconcileResidueKey_schema (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKey T dt on R e shapes negCands uposCands).schema = σ.schema := rfl

@[simp] theorem reconcileResidueKey_outbox (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKey T dt on R e shapes negCands uposCands).outbox = σ.outbox := rfl

@[simp] theorem reconcileResidueKey_watermark (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKey T dt on R e shapes negCands uposCands).watermark = σ.watermark := rfl

/-- The residue recompute leaves every other `(key, relation)` untouched. -/
theorem reconcileResidueKey_residue_other {σ : GraphState} {T : Store} {dt on R : String}
    {e : Expr} {shapes : List Shape} {negCands uposCands : List SubjectRef}
    {k' : NodeKey} {r' : String} (h : ¬(k' = objNode ⟨dt, on⟩ R ∧ r' = R)) :
    (σ.reconcileResidueKey T dt on R e shapes negCands uposCands).residue k' r'
      = σ.residue k' r' := by
  unfold GraphState.reconcileResidueKey
  rw [putResidue_residue, if_neg h]

/-- The row the residue recompute writes at its own key — the three filters,
    evaluated at the pass-start state. -/
theorem reconcileResidueKey_residue_self (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (negCands uposCands : List SubjectRef) :
    (σ.reconcileResidueKey T dt on R e shapes negCands uposCands).residue
        (objNode ⟨dt, on⟩ R) R =
      some ⟨shapes.filter (fun sh => σ.coveredFn T dt on R e sh),
            negCands.filter (fun c =>
              (shapes.filter (fun sh => σ.coveredFn T dt on R e sh)).contains c.shape
                && !(σ.checkFn T c dt on R e)),
            uposCands.filter (fun c =>
              !((shapes.filter (fun sh => σ.coveredFn T dt on R e sh)).contains c.shape)
                && σ.checkFn T c dt on R e)⟩ := by
  unfold GraphState.reconcileResidueKey
  rw [putResidue_residue, if_pos ⟨rfl, rfl⟩]

/-- The residue recompute preserves core agreement on the (unchanged) shadow side. -/
theorem reconcileResidueKey_coreEq {σ' σ : GraphState} (h : CoreEq σ' σ) (T : Store)
    (dt on R : String) (e : Expr) (shapes : List Shape)
    (negCands uposCands : List SubjectRef) :
    CoreEq σ' (σ.reconcileResidueKey T dt on R e shapes negCands uposCands) :=
  ⟨h.schema, h.edges, h.nodes, h.outbox, h.watermark⟩

/-! ## The covered-filter collapse — the W3c edge fold IS a W3a `reconcileKey`

The covered guard reads the persisted `stars` row, which `writeDirect` never touches
— so it is constant across the fold, and dropping the covered candidates up front
gives the same fold. Every `reconcileKey` lemma (edge soundness, monotonicity,
reach-inertness, `Inv` preservation, `CoreEq`) transfers to `reconcileKeyC`. -/

/-- `writeDirect` never moves the persisted coverage. -/
theorem coveredAt_writeDirect (σ : GraphState) (t : Tuple) (k : NodeKey) (R : String)
    (sh : Shape) : (σ.writeDirect t).coveredAt k R sh = σ.coveredAt k R sh := by
  unfold GraphState.coveredAt
  rw [writeDirect_residue]

/-- **The collapse**: the covered-guarded fold equals the plain W3a `reconcileKey`
    over the covered-filtered candidate list (filter evaluated at the fold start —
    where Python's step-4 audit reads the row written by step 3). -/
theorem reconcileKeyC_eq_filter (T : Store) (dt on R : String) (e : Expr) :
    ∀ (cands : List SubjectRef) (σ : GraphState),
      σ.reconcileKeyC T dt on R e cands =
        σ.reconcileKey T dt on R e
          (cands.filter (fun c => !(σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape))) := by
  intro cands
  induction cands with
  | nil => intro σ; rfl
  | cons c rest ih =>
    intro σ
    have hstep : σ.reconcileKeyC T dt on R e (c :: rest)
        = (if σ.checkFn T c dt on R e && !(σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)
           then σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩ else σ).reconcileKeyC T dt on R e rest := by
      unfold GraphState.reconcileKeyC
      rw [List.foldl_cons]
    by_cases hcov : σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape = true
    · -- covered: the step is the identity, and the filter drops `c`
      rw [hstep, hcov]
      simp only [Bool.not_true, Bool.and_false, if_neg (Bool.false_ne_true)]
      rw [ih σ, List.filter_cons_of_neg (by simp [hcov])]
    · -- uncovered: both folds take the same `checkFn`-guarded step
      have hcov' : σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape = false :=
        Bool.eq_false_iff.mpr hcov
      rw [hstep, hcov']
      simp only [Bool.not_false, Bool.and_true]
      rw [List.filter_cons_of_pos (by simp [hcov'])]
      show _ = σ.reconcileKey T dt on R e (c :: List.filter _ rest)
      have hunf : σ.reconcileKey T dt on R e
          (c :: rest.filter (fun c' => !(σ.coveredAt (objNode ⟨dt, on⟩ R) R c'.shape)))
          = (if σ.checkFn T c dt on R e then σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩ else σ).reconcileKey
              T dt on R e
              (rest.filter (fun c' => !(σ.coveredAt (objNode ⟨dt, on⟩ R) R c'.shape))) := by
        unfold GraphState.reconcileKey
        rw [List.foldl_cons]
      rw [hunf]
      by_cases hchk : σ.checkFn T c dt on R e = true
      · rw [if_pos hchk, ih (σ.writeDirect ⟨c, R, ⟨dt, on⟩⟩)]
        congr 1
        apply List.filter_congr
        intro x _
        rw [coveredAt_writeDirect]
      · rw [if_neg hchk]
        exact ih σ

/-! ### Transfers through the collapse -/

/-- The covered-guarded fold never touches residues. -/
theorem reconcileKeyC_residue (T : Store) (dt on R : String) (e : Expr)
    (cands : List SubjectRef) (σ : GraphState) :
    (σ.reconcileKeyC T dt on R e cands).residue = σ.residue := by
  rw [reconcileKeyC_eq_filter]
  exact reconcileKey_residue T dt on R e _ σ

/-- Old edges persist through the covered-guarded fold. -/
theorem reconcileKeyC_edges_mono {σ : GraphState} (T : Store) (dt on R : String)
    (e : Expr) (cands : List SubjectRef) :
    ∀ ab ∈ σ.edges, ab ∈ (σ.reconcileKeyC T dt on R e cands).edges := by
  rw [reconcileKeyC_eq_filter]
  exact reconcileKey_edges_mono T dt on R e _

/-- Every new edge of the covered-guarded fold comes from an **uncovered** candidate
    (the filter membership) targeting the fold's own R-node. -/
theorem reconcileKeyC_edge_sound {σ : GraphState} (T : Store) (dt on R : String)
    (e : Expr) (cands : List SubjectRef) :
    ∀ a b, (a, b) ∈ (σ.reconcileKeyC T dt on R e cands).edges →
      (a, b) ∈ σ.edges ∨
      ∃ c ∈ cands, a = subjNode c ∧ b = objNode ⟨dt, on⟩ R ∧
        σ.coveredAt (objNode ⟨dt, on⟩ R) R c.shape = false := by
  intro a b hab
  rw [reconcileKeyC_eq_filter] at hab
  rcases reconcileKey_edge_sound T dt on R e _ a b hab with hold | ⟨c, hc, ha, hb⟩
  · exact Or.inl hold
  · obtain ⟨hcmem, hcunc⟩ := List.mem_filter.mp hc
    exact Or.inr ⟨c, hcmem, ha, hb, by simpa using hcunc⟩

/-! ## Whole-pass structural facts -/

/-- The combined pass leaves every other `(key, relation)` residue untouched. -/
theorem reconcileStarsKey_residue_other {σ : GraphState} {T : Store} {dt on R : String}
    {e : Expr} {shapes : List Shape} {cands negCands uposCands : List SubjectRef}
    {k' : NodeKey} {r' : String} (h : ¬(k' = objNode ⟨dt, on⟩ R ∧ r' = R)) :
    (σ.reconcileStarsKey T dt on R e shapes cands negCands uposCands).residue k' r'
      = σ.residue k' r' := by
  unfold GraphState.reconcileStarsKey
  rw [reconcileKeyC_residue, reconcileResidueKey_residue_other h]

/-- The combined pass persists exactly the pass-start filters at its own key. -/
theorem reconcileStarsKey_residue_self (σ : GraphState) (T : Store) (dt on R : String)
    (e : Expr) (shapes : List Shape) (cands negCands uposCands : List SubjectRef) :
    (σ.reconcileStarsKey T dt on R e shapes cands negCands uposCands).residue
        (objNode ⟨dt, on⟩ R) R =
      (σ.reconcileResidueKey T dt on R e shapes negCands uposCands).residue
        (objNode ⟨dt, on⟩ R) R := by
  unfold GraphState.reconcileStarsKey
  rw [reconcileKeyC_residue]

/-! ## The W3c write-closure -/

/-- **`ReachedByW3c σ S T`** — an admitted rule-routed base plus full-object star
    reconcile passes (`reconcileStarsKey` — the faithful atomic unit: `reconcile`
    always writes the residue *before* auditing edges, `processor.py:443-455`; a
    free-floating covered-guard edge pass without its residue write is NOT a Python
    behaviour and would break the space rule). Side conditions mirror the audit
    enumeration: edge candidates are concrete bare subjects (`reconcile` step 4 runs
    `reconcile_subject` only for `predicate == '...'` rows, `:452-453`; enumerated
    nodes are concrete, `wildcard == ''`); `neg` candidates are concrete
    (`_leaf_concretes` + persisted ids, `:394-404`); `upos` candidates are concrete
    userset-shaped (`:434-437`); the shapes list is the schema-fixed
    `subject_wildcard_shapes` (`:135`). -/
inductive ReachedByW3c : GraphState → Schema → Store → Prop where
  | base {σ : GraphState} {S : Schema} {T : Store} :
      ReachedByRulesAdmitted σ S T → ReachedByW3c σ S T
  | reconcileS {σ : GraphState} {S : Schema} {T : Store}
      (dt on R : String) (e : Expr) (cands negCands uposCands : List SubjectRef)
      (hRne : R ≠ BARE)
      (hcands : ∀ c ∈ cands, c.predicate = BARE)
      (hcStar : ∀ c ∈ cands, c.name ≠ STAR)
      (hnegStar : ∀ c ∈ negCands, c.name ≠ STAR)
      (huposP : ∀ c ∈ uposCands, c.predicate ≠ BARE)
      (huposStar : ∀ c ∈ uposCands, c.name ≠ STAR)
      (hder : isDerived S (dt, R) = true) (hlke : S.lookup (dt, R) = some e)
      (honStar : on ≠ STAR) :
      ReachedByW3c σ S T →
      ReachedByW3c
        (σ.reconcileStarsKey T dt on R e (wildcardShapes S) cands negCands uposCands) S T

/-- **The W3c shadow projection.** Every W3c state has a W3a-admitted shadow with an
    identical core: the residue half of each pass is core-inert, and the edge half IS
    a W3a `reconcileKey` on the covered-filtered candidate list (the collapse) — a
    legitimate W3a reconcile leg (filtering preserves bare/star-free). All W3a
    edge/reach facts (collapse, terminality, edge soundness) transfer. -/
theorem reachedByW3c_shadow {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3c σ S T) :
    ∃ σ', ReachedByW3aAdmitted σ' S T ∧ CoreEq σ' σ := by
  induction h with
  | base hr => exact ⟨_, ReachedByW3aAdmitted.base hr, CoreEq.refl _⟩
  | @reconcileS σp S T dt on R e cands negCands uposCands hRne hcands hcStar _hnegStar
      _huposP _huposStar hder hlke honStar _hprev ih =>
    obtain ⟨σ', hσ', hcore⟩ := ih
    unfold GraphState.reconcileStarsKey
    rw [reconcileKeyC_eq_filter]
    exact ⟨_, ReachedByW3aAdmitted.reconcile dt on R e _ hRne
      (fun c hc => hcands c (List.mem_of_mem_filter hc)) hder hlke
      (fun c hc => hcStar c (List.mem_of_mem_filter hc)) honStar hσ',
      reconcileKey_coreEq _
        (reconcileResidueKey_coreEq hcore T dt on R e (wildcardShapes S) negCands uposCands)⟩

/-- Endpoint-closure of a W3c state's edges (through the shadow's `Inv`). -/
theorem reachedByW3c_edgesClosed {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3c σ S T) :
    ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes := by
  obtain ⟨σ', hσ', hcore⟩ := reachedByW3c_shadow h
  have hInv := (reachedByW3a_inv (reachedByW3aAdmitted_toW3a hσ')).1
  rw [← hcore.edges, ← hcore.nodes]
  exact hInv.edgesClosed

/-- A derived (`ComputedOnly`-fragment) R-node is never an edge source on a W3c state
    (through the shadow; `hterm` supplies the no-TTU-target / no-store-subject
    terminality conditions). -/
theorem reachedByW3c_Rnode_not_source {σ : GraphState} {S : Schema} {T : Store}
    {dt on R : String}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hRne : R ≠ BARE) (hder : isDerived S (dt, R) = true)
    (h : ReachedByW3c σ S T) :
    ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges := by
  obtain ⟨σ', hσ', hcore⟩ := reachedByW3c_shadow h
  obtain ⟨hnt, hns⟩ := hterm dt R hder
  intro y hy
  exact reachedByW3a_Rnode_not_source hnt hns hRne (reachedByW3aAdmitted_toW3a hσ')
    (objNode_pred ⟨dt, on⟩ R) y (by rw [hcore.edges]; exact hy)

/-! ## Star-general operand-read inertness — NO `StarFreeStore`

`graphRec_reduce_base_adm` (W3a) reduced the operand read to the base under
`StarFreeStore` (all edges plain ⇒ wildcard probes dead). W3c's `coveredFn`
evaluates `checkFn` on **star subjects**, whose probes leave from `w_any` nodes — so
the star-free shortcut is unavailable. But it is also unnecessary for *inertness*:
a reconcile pass only adds edges onto its terminal R-node, and **all four** probe
targets of an untainted-key read (`objNode ⟨dt',on'⟩ r'` and `wAllNode dt' r'`, both
carrying the untainted `pred = r'`) differ from that R-node — so each probe's
reachability is unchanged (`reconcileKey_reach_inert`), subject-generically. -/

/-- One reconcile pass leaves the operand read of every untainted key unchanged —
    for EVERY subject, star subjects included. -/
theorem graphRec_reconcileKey_inert {σ : GraphState} {S : Schema} (T : Store)
    (dt on R : String) (e : Expr) (cands : List SubjectRef) (hRne : R ≠ BARE)
    (hcands : ∀ c ∈ cands, c.predicate = BARE)
    (hRns : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ.edges)
    (honStar : on ≠ STAR) (hder : isDerived S (dt, R) = true)
    (hcl : ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes)
    (hcl2 : ∀ ab ∈ (σ.reconcileKey T dt on R e cands).edges,
        ab.1 ∈ (σ.reconcileKey T dt on R e cands).nodes
          ∧ ab.2 ∈ (σ.reconcileKey T dt on R e cands).nodes)
    (s : SubjectRef) (dt' on' r' : String) (hunt : isDerived S (dt', r') = false) :
    GraphModel.graphRec (σ.reconcileKey T dt on R e cands) s dt' on' r'
      = GraphModel.graphRec σ s dt' on' r' := by
  -- probe targets of the untainted read differ from the reconciled R-node
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
  -- lift both probe reads to `NReaches`, then transfer disjunct-by-disjunct
  have hiff2 := GraphModel.probeNonDerived_iff hcl2 (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  have hiff1 := GraphModel.probeNonDerived_iff hcl (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  have hmono : ∀ {u v : NodeKey}, NReaches σ.edges u v →
      NReaches (σ.reconcileKey T dt on R e cands).edges u v := fun hn =>
    NReaches.mono_subset (fun ab hab => reconcileKey_edges_mono T dt on R e cands ab hab) hn
  have hinert1 : ∀ {u : NodeKey},
      NReaches (σ.reconcileKey T dt on R e cands).edges u (objNode ⟨dt', on'⟩ r') →
      NReaches σ.edges u (objNode ⟨dt', on'⟩ r') := fun hn =>
    reconcileKey_reach_inert T dt on R e cands hRne hvne1 hcands hRns hn
  have hinert3 : ∀ {u : NodeKey},
      NReaches (σ.reconcileKey T dt on R e cands).edges u (wAllNode dt' r') →
      NReaches σ.edges u (wAllNode dt' r') := fun hn =>
    reconcileKey_reach_inert T dt on R e cands hRne hvne3 hcands hRns hn
  unfold GraphModel.graphRec
  cases hb2 : GraphModel.probeNonDerived (σ.reconcileKey T dt on R e cands)
      (⟨s, r', ⟨dt', on'⟩⟩ : Query)
    <;> cases hb1 : GraphModel.probeNonDerived σ (⟨s, r', ⟨dt', on'⟩⟩ : Query)
  · rfl
  · -- after-pass false, before-pass true: monotonicity contradiction
    exfalso
    have hd := hiff1.mp hb1
    have : GraphModel.probeNonDerived (σ.reconcileKey T dt on R e cands)
        (⟨s, r', ⟨dt', on'⟩⟩ : Query) = true := by
      apply hiff2.mpr
      rcases hd with h1 | ⟨hs, h2⟩ | ⟨ho, h3⟩ | ⟨hs, ho, h4⟩
      · exact Or.inl (hmono h1)
      · exact Or.inr (Or.inl ⟨hs, hmono h2⟩)
      · exact Or.inr (Or.inr (Or.inl ⟨ho, hmono h3⟩))
      · exact Or.inr (Or.inr (Or.inr ⟨hs, ho, hmono h4⟩))
    rw [hb2] at this
    cases this
  · -- after-pass true, before-pass false: inertness contradiction
    exfalso
    have hd := hiff2.mp hb2
    have : GraphModel.probeNonDerived σ (⟨s, r', ⟨dt', on'⟩⟩ : Query) = true := by
      apply hiff1.mpr
      rcases hd with h1 | ⟨hs, h2⟩ | ⟨ho, h3⟩ | ⟨hs, ho, h4⟩
      · exact Or.inl (hinert1 h1)
      · exact Or.inr (Or.inl ⟨hs, hinert1 h2⟩)
      · exact Or.inr (Or.inr (Or.inl ⟨ho, hinert3 h3⟩))
      · exact Or.inr (Or.inr (Or.inr ⟨hs, ho, hinert3 h4⟩))
    rw [hb1] at this
    cases this
  · rfl

/-- `checkFn` agreement across two states whose operand reads agree at the def's
    `computed` leaves — subject-generic (`evalE_computedOnly`). -/
theorem checkFn_agree_of_graphRec {σ σ0 : GraphState} {S : Schema} (T : Store)
    (s : SubjectRef) (dt on R : String) (e : Expr) (hco : ComputedOnly e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hag : ∀ (s' : SubjectRef) (r' : String), isDerived S (dt, r') = false →
      GraphModel.graphRec σ s' dt on r' = GraphModel.graphRec σ0 s' dt on r') :
    σ.checkFn T s dt on R e = σ0.checkFn T s dt on R e := by
  unfold GraphState.checkFn
  exact evalE_computedOnly e hco (fun r' hr' => hag s r' (hleafUnt r' hr'))

/-- `checkFn` agreement across two states agreeing on the def's `computed` leaves, WIDENED to a
    `ComputedOrDirect` def with bare `Direct` arms (leg 1's `evalE_computedOrDirect`). Subject-
    SHARED (a `Direct` arm reads the store at the fixed subject — the varying-subject form is
    refuted; `ReconcileCorrect` widening-leg note); only `rec`/query vary, all `wantEdge` needs.
    (Lives here, not `ReconcileDiff`, so the W3c master `_d` core can consume it.) -/
theorem checkFn_agree_of_graphRec_cd {σ σ0 : GraphState} {S : Schema} (T : Store)
    (s : SubjectRef) (dt on R : String) (e : Expr)
    (hcd : ComputedOrDirect e) (hba : DirectArmsBare e)
    (hleafUnt : ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (hag : ∀ (s' : SubjectRef) (r' : String), isDerived S (dt, r') = false →
      GraphModel.graphRec σ s' dt on r' = GraphModel.graphRec σ0 s' dt on r') :
    σ.checkFn T s dt on R e = σ0.checkFn T s dt on R e := by
  unfold GraphState.checkFn
  exact evalE_computedOrDirect e hcd hba (fun r' hr' => hag s r' (hleafUnt r' hr'))

/-! ## The master provenance — canonical stars, covered `neg`, uncovered edges

The load-bearing consequence of inertness: `coveredFn` is CONSTANT along the whole
W3c chain (it reads only untainted operand keys), so every persisted `stars` row
equals the **canonical star set of the chain's base** — and the space rule
(`want_edge = should ∧ ¬covered`) becomes checkable across passes: `neg` members are
canonically covered, edge sources are canonically uncovered. That contradiction is
`negEdgeFree`. -/

/-- **`reachedByW3c_master`** — along any W3c chain there is a single admitted base
    `σ0` such that (1) every untainted operand read equals the base's (subject-
    generic), (2) every persisted residue row sits at a derived R-node key and
    carries the canonical `stars` row, filter-guaranteed `neg`/`upos` members, and
    (3) every in-edge of a derived R-node is a base edge or a canonically-uncovered
    bare reconcile edge. -/
theorem reachedByW3c_master_d {σ : GraphState} {S : Schema} {T : Store}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hcd : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOrDirect e)
    (hba : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → DirectArmsBare e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : ReachedByW3c σ S T) :
    ∃ σ0, ReachedByRulesAdmitted σ0 S T ∧
      (∀ (s : SubjectRef) (dt on r' : String), isDerived S (dt, r') = false →
        GraphModel.graphRec σ s dt on r' = GraphModel.graphRec σ0 s dt on r') ∧
      (∀ k r res, σ.residue k r = some res →
        ∃ dt on e', k = objNode ⟨dt, on⟩ r ∧ isDerived S (dt, r) = true ∧ r ≠ BARE ∧
          on ≠ STAR ∧ S.lookup (dt, r) = some e' ∧
          res.stars = (wildcardShapes S).filter (fun sh => σ0.coveredFn T dt on r e' sh) ∧
          (∀ n ∈ res.neg, res.stars.contains n.shape = true ∧ n.name ≠ STAR ∧
            σ0.checkFn T n dt on r e' = false) ∧
          (∀ n ∈ res.upos, res.stars.contains n.shape = false ∧ n.predicate ≠ BARE ∧
            n.name ≠ STAR ∧ σ0.checkFn T n dt on r e' = true)) ∧
      (∀ (dt on r : String) (e' : Expr), isDerived S (dt, r) = true →
        S.lookup (dt, r) = some e' → on ≠ STAR →
        ∀ u, (u, objNode ⟨dt, on⟩ r) ∈ σ.edges →
          (u, objNode ⟨dt, on⟩ r) ∈ σ0.edges ∨
          ∃ c : SubjectRef, u = subjNode c ∧ c.predicate = BARE ∧ c.name ≠ STAR ∧
            ((wildcardShapes S).filter
              (fun sh => σ0.coveredFn T dt on r e' sh)).contains c.shape = false ∧
            σ0.checkFn T c dt on r e' = true) := by
  induction h with
  | base hr =>
    refine ⟨_, hr, fun _ _ _ _ _ => rfl, ?_, ?_⟩
    · intro k r res hres
      rw [(reachedByRules_inv (reachedByRules_of_admitted hr)).2.1 k r] at hres
      cases hres
    · intro dt on r e' _hder _hlk _hon u hu
      exact Or.inl hu
  | @reconcileS σp S T dt on R e cands negCands uposCands hRne hcands hcStar hnegStar
      huposP huposStar hder hlke honStar hprev ih =>
    obtain ⟨σ0, hσ0, hag, hres, hedge⟩ := ih hterm hcd hba hLU
    -- the current state is a W3c state too
    have hcur : ReachedByW3c
        (σp.reconcileStarsKey T dt on R e (wildcardShapes S) cands negCands uposCands) S T :=
      ReachedByW3c.reconcileS dt on R e cands negCands uposCands hRne hcands hcStar
        hnegStar huposP huposStar hder hlke honStar hprev
    -- the edge half is a plain reconcileKey on the covered-filtered candidates
    set σ1 := σp.reconcileResidueKey T dt on R e (wildcardShapes S) negCands uposCands
      with hσ1
    have hsplit : σp.reconcileStarsKey T dt on R e (wildcardShapes S) cands negCands uposCands
        = σ1.reconcileKey T dt on R e
            (cands.filter (fun c => !(σ1.coveredAt (objNode ⟨dt, on⟩ R) R c.shape))) := by
      unfold GraphState.reconcileStarsKey
      rw [reconcileKeyC_eq_filter]
    -- graphRec is untouched by the residue half (edges/nodes are literally equal)
    have hσ1e : σ1.edges = σp.edges := by simp [hσ1]
    have hσ1n : σ1.nodes = σp.nodes := by simp [hσ1]
    have hag1 : ∀ (s : SubjectRef) (dt'' on'' r' : String),
        GraphModel.graphRec σ1 s dt'' on'' r' = GraphModel.graphRec σp s dt'' on'' r' := by
      intro s dt'' on'' r'
      rw [graphRec_congr hσ1e hσ1n s]
    -- per-leg operand-read inertness for the edge half
    have hRns1 : ∀ y, (objNode ⟨dt, on⟩ R, y) ∉ σ1.edges := by
      have hns := reachedByW3c_Rnode_not_source hterm hRne hder hprev (on := on)
      intro y hy
      rw [hσ1e] at hy
      exact hns y hy
    have hcl1 : ∀ ab ∈ σ1.edges, ab.1 ∈ σ1.nodes ∧ ab.2 ∈ σ1.nodes := by
      have hec := reachedByW3c_edgesClosed hprev
      intro ab hab
      rw [hσ1e] at hab
      rw [hσ1n]
      exact hec ab hab
    have hcl2 : ∀ ab ∈ (σ1.reconcileKey T dt on R e
          (cands.filter (fun c => !(σ1.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)))).edges,
        ab.1 ∈ (σ1.reconcileKey T dt on R e
          (cands.filter (fun c => !(σ1.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)))).nodes
        ∧ ab.2 ∈ (σ1.reconcileKey T dt on R e
          (cands.filter (fun c => !(σ1.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)))).nodes := by
      have := reachedByW3c_edgesClosed hcur
      rw [hsplit] at this
      exact this
    have hstepag : ∀ (s : SubjectRef) (dt'' on'' r' : String),
        isDerived S (dt'', r') = false →
        GraphModel.graphRec (σ1.reconcileKey T dt on R e
            (cands.filter (fun c => !(σ1.coveredAt (objNode ⟨dt, on⟩ R) R c.shape))))
          s dt'' on'' r' = GraphModel.graphRec σ1 s dt'' on'' r' := by
      intro s dt'' on'' r' hunt
      exact graphRec_reconcileKey_inert T dt on R e _ hRne
        (fun c hc => hcands c (List.mem_of_mem_filter hc)) hRns1 honStar hder hcl1 hcl2
        s dt'' on'' r' hunt
    -- checkFn at the pass start equals the canonical (base) checkFn — any subject
    have hchk_eq : ∀ (x : SubjectRef), σp.checkFn T x dt on R e = σ0.checkFn T x dt on R e :=
      fun x => checkFn_agree_of_graphRec_cd T x dt on R e (hcd dt R e hlke hder)
        (hba dt R e hlke hder) (hLU dt R e hlke hder) (fun s' r' hr' => hag s' dt on r' hr')
    -- the pass-start star filter equals the canonical (base) star filter
    have hstars_eq : (wildcardShapes S).filter (fun sh => σp.coveredFn T dt on R e sh)
        = (wildcardShapes S).filter (fun sh => σ0.coveredFn T dt on R e sh) := by
      apply List.filter_congr
      intro sh _
      unfold GraphState.coveredFn
      rw [hchk_eq (starSubj sh)]
    refine ⟨σ0, hσ0, ?_, ?_, ?_⟩
    · -- (1) operand-read agreement carries through the pass
      intro s dt'' on'' r' hunt
      rw [hsplit, hstepag s dt'' on'' r' hunt, hag1 s dt'' on'' r', hag s dt'' on'' r' hunt]
    · -- (2) residue rows: own key = the canonical filters; other keys by IH
      intro k r res hresrow
      by_cases hkey : k = objNode ⟨dt, on⟩ R ∧ r = R
      · obtain ⟨hk, hr⟩ := hkey
        rw [hsplit] at hresrow
        rw [show (σ1.reconcileKey T dt on R e
            (cands.filter (fun c => !(σ1.coveredAt (objNode ⟨dt, on⟩ R) R c.shape)))).residue
            = σ1.residue from reconcileKey_residue T dt on R e _ σ1] at hresrow
        rw [hk, hr, hσ1, reconcileResidueKey_residue_self] at hresrow
        obtain rfl := (Option.some.inj hresrow).symm
        refine ⟨dt, on, e, by rw [hr]; exact hk, by rw [hr]; exact hder,
          by rw [hr]; exact hRne, honStar, by rw [hr]; exact hlke,
          by rw [hr]; exact hstars_eq, ?_, ?_⟩
        · intro n hn
          obtain ⟨hnmem, hnfil⟩ := List.mem_filter.mp hn
          simp only [Bool.and_eq_true, Bool.not_eq_true'] at hnfil
          refine ⟨hnfil.1, hnegStar n hnmem, ?_⟩
          rw [hr, ← hchk_eq n]
          exact hnfil.2
        · intro n hn
          obtain ⟨hnmem, hnfil⟩ := List.mem_filter.mp hn
          simp only [Bool.and_eq_true, Bool.not_eq_true'] at hnfil
          refine ⟨hnfil.1, huposP n hnmem, huposStar n hnmem, ?_⟩
          rw [hr, ← hchk_eq n]
          exact hnfil.2
      · rw [reconcileStarsKey_residue_other hkey] at hresrow
        exact hres k r res hresrow
    · -- (3) R-node in-edges: old edges by IH, new edges are canonically uncovered
      -- AND canonically guard-true (`reconcileKey_edge_guard` + prefix-mid-state inertness)
      intro dtq onq rq eq' hderq hlkq honq u hu
      rw [hsplit] at hu
      rcases reconcileKey_edge_guard _ σ1 hu with hold | ⟨pre, c, hpre, hc, hueq, hbeq, hchk⟩
      · -- an old edge of σ1 = σp
        rw [hσ1e] at hold
        exact hedge dtq onq rq eq' hderq hlkq honq u hold
      · -- a new edge: same key by injectivity
        obtain ⟨hdt, hon, hR⟩ := objNode_inj_of_ne_star honq honStar hbeq
        have he : eq' = e := by
          rw [hdt, hR] at hlkq
          exact Option.some.inj (hlkq.symm.trans hlke)
        obtain ⟨hcmem', hcunc⟩ := List.mem_filter.mp hc
        -- the prefix mid-state's guard is the canonical guard: the mid-state is
        -- core-shadowed by a W3a-admitted state, and the prefix fold is operand-inert
        have hpre_bare : ∀ x ∈ pre, x.predicate = BARE := fun x hx =>
          hcands x (List.mem_of_mem_filter (hpre.subset hx))
        obtain ⟨σ', hσ', hcore⟩ := reachedByW3c_shadow hprev
        have hcore1 : CoreEq σ' σ1 := by
          rw [hσ1]
          exact reconcileResidueKey_coreEq hcore T dt on R e (wildcardShapes S)
            negCands uposCands
        have hmidAdm : ReachedByW3aAdmitted (σ'.reconcileKey T dt on R e pre) S T :=
          ReachedByW3aAdmitted.reconcile dt on R e pre hRne hpre_bare hder hlke
            (fun x hx => hcStar x (List.mem_of_mem_filter (hpre.subset hx))) honStar hσ'
        have hcoremid : CoreEq (σ'.reconcileKey T dt on R e pre)
            (σ1.reconcileKey T dt on R e pre) := reconcileKey_coreEq pre hcore1
        have hclmid : ∀ ab ∈ (σ1.reconcileKey T dt on R e pre).edges,
            ab.1 ∈ (σ1.reconcileKey T dt on R e pre).nodes
              ∧ ab.2 ∈ (σ1.reconcileKey T dt on R e pre).nodes := by
          have hInvm := (reachedByW3a_inv (reachedByW3aAdmitted_toW3a hmidAdm)).1
          intro ab hab
          rw [← hcoremid.edges] at hab
          rw [← hcoremid.nodes]
          exact hInvm.edgesClosed ab hab
        have hmidag : ∀ (s : SubjectRef) (r' : String), isDerived S (dt, r') = false →
            GraphModel.graphRec (σ1.reconcileKey T dt on R e pre) s dt on r'
              = GraphModel.graphRec σ1 s dt on r' :=
          fun s r' hunt' => graphRec_reconcileKey_inert T dt on R e pre hRne hpre_bare
            hRns1 honStar hder hcl1 hclmid s dt on r' hunt'
        have hguard0 : σ0.checkFn T c dt on R e = true := by
          have h1 : (σ1.reconcileKey T dt on R e pre).checkFn T c dt on R e
              = σ1.checkFn T c dt on R e :=
            checkFn_agree_of_graphRec_cd T c dt on R e (hcd dt R e hlke hder)
              (hba dt R e hlke hder) (hLU dt R e hlke hder) hmidag
          have h2 : σ1.checkFn T c dt on R e = σp.checkFn T c dt on R e :=
            checkFn_agree_of_graphRec_cd T c dt on R e (hcd dt R e hlke hder)
              (hba dt R e hlke hder) (hLU dt R e hlke hder) (fun s' r' _ => hag1 s' dt on r')
          have hcv := hchk
          rw [h1, h2, hchk_eq c] at hcv
          exact hcv
        refine Or.inr ⟨c, hueq, hcands c hcmem', hcStar c hcmem', ?_, ?_⟩
        · rw [hdt, hon, hR, he]
          -- the persisted row the guard read is the pass-start filter = the canonical filter
          have hrow : σ1.coveredAt (objNode ⟨dt, on⟩ R) R c.shape
              = ((wildcardShapes S).filter
                  (fun sh => σp.coveredFn T dt on R e sh)).contains c.shape := by
            unfold GraphState.coveredAt
            rw [hσ1, reconcileResidueKey_residue_self]
            rfl
          rw [← hstars_eq, ← hrow]
          simpa using hcunc
        · rw [hdt, hon, hR, he]
          exact hguard0

/-- **`reachedByW3c_master`** — the `ComputedOnly` wrapper over the `_d` core
    `reachedByW3c_master_d`. Byte-identical statement to HEAD; delegates by deriving
    `ComputedOrDirect`/`DirectArmsBare` from `ComputedOnly` at each derived key
    (`computedOnly_computedOrDirect`/`_directArmsBare`). -/
theorem reachedByW3c_master {σ : GraphState} {S : Schema} {T : Store}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : ReachedByW3c σ S T) :
    ∃ σ0, ReachedByRulesAdmitted σ0 S T ∧
      (∀ (s : SubjectRef) (dt on r' : String), isDerived S (dt, r') = false →
        GraphModel.graphRec σ s dt on r' = GraphModel.graphRec σ0 s dt on r') ∧
      (∀ k r res, σ.residue k r = some res →
        ∃ dt on e', k = objNode ⟨dt, on⟩ r ∧ isDerived S (dt, r) = true ∧ r ≠ BARE ∧
          on ≠ STAR ∧ S.lookup (dt, r) = some e' ∧
          res.stars = (wildcardShapes S).filter (fun sh => σ0.coveredFn T dt on r e' sh) ∧
          (∀ n ∈ res.neg, res.stars.contains n.shape = true ∧ n.name ≠ STAR ∧
            σ0.checkFn T n dt on r e' = false) ∧
          (∀ n ∈ res.upos, res.stars.contains n.shape = false ∧ n.predicate ≠ BARE ∧
            n.name ≠ STAR ∧ σ0.checkFn T n dt on r e' = true)) ∧
      (∀ (dt on r : String) (e' : Expr), isDerived S (dt, r) = true →
        S.lookup (dt, r) = some e' → on ≠ STAR →
        ∀ u, (u, objNode ⟨dt, on⟩ r) ∈ σ.edges →
          (u, objNode ⟨dt, on⟩ r) ∈ σ0.edges ∨
          ∃ c : SubjectRef, u = subjNode c ∧ c.predicate = BARE ∧ c.name ≠ STAR ∧
            ((wildcardShapes S).filter
              (fun sh => σ0.coveredFn T dt on r e' sh)).contains c.shape = false ∧
            σ0.checkFn T c dt on r e' = true) :=
  reachedByW3c_master_d hterm
    (fun dt R e hlk hder => computedOnly_computedOrDirect (hCO dt R e hlk hder))
    (fun dt R e hlk hder => computedOnly_directArmsBare (hCO dt R e hlk hder))
    hLU h

/-! ## T2a at W3c — the full invariant, every I6 clause contentful -/

/-- **T2a for the W3c fragment (`reachedByW3c_inv`).** Every W3c state satisfies the
    full I-series invariant and quiescence — with, for the first time, **all four I6
    residue-hygiene clauses contentful**:

    * `negStarCovered` — write-time filter (`neg` demands `stars.contains`).
    * `uposNegDisjoint` — `upos` demands `¬covered`, `neg` demands `covered`, over
      the same row.
    * `uposEdgeFree` — a `upos` member is userset-shaped; every path onto the
      derived R-node collapses to a single bare-sourced edge (shadow).
    * `negEdgeFree` — the space rule, cross-pass: a `neg` member is *canonically*
      covered (master), every reconcile edge source is *canonically* uncovered
      (master), and canonical coverage is pass-invariant (star-general inertness) —
      contradiction.

    **No `StarFreeStore` hypothesis** — the invariant layer holds on star-carrying
    stores. -/
theorem reachedByW3c_inv {σ : GraphState} {S : Schema} {T : Store}
    (hWF : WF S) (hNK : NodupKeys S) (hSV : StoreValidRules S T)
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R)
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOnly e)
    (hLU : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = false)
    (h : ReachedByW3c σ S T) :
    Inv S σ ∧ Quiescent σ := by
  obtain ⟨σ', hσ', hcore⟩ := reachedByW3c_shadow h
  have hW3a := reachedByW3aAdmitted_toW3a hσ'
  obtain ⟨hInv', _hre', hQ'⟩ := reachedByW3a_inv hW3a
  obtain ⟨σ0, hσ0, _hag, hres, hedge⟩ := reachedByW3c_master hterm hCO hLU h
  constructor
  · refine ⟨hcore.schema.symm.trans hInv'.schemaEq,
      by rw [← hcore.nodes]; exact hInv'.nodeEnc,
      by rw [← hcore.edges, ← hcore.nodes]; exact hInv'.edgesClosed,
      by rw [← hcore.edges]; exact hInv'.acyclic,
      ?_, ?_, ?_, ?_⟩
    · -- negStarCovered: the write-time filter
      intro k r res hrow n hn
      obtain ⟨_, _, _, _, _, _, _, _, _, hnegm, _⟩ := hres k r res hrow
      exact (hnegm n hn).1
    · -- negEdgeFree: canonical coverage vs canonical uncoveredness
      intro k r res hrow n hn hreach
      obtain ⟨dt, on, e', hk, hderr, hRner, honr, hlkr, hstars, hnegm, _⟩ :=
        hres k r res hrow
      subst hk
      have hco' : ComputedOnly e' := hCO dt r e' hlkr hderr
      -- collapse the path to a single edge (through the shadow)
      have hreach' : NReaches σ'.edges (subjNode n) (objNode ⟨dt, on⟩ r) := by
        rw [hcore.edges]; exact hreach
      have hedge1 := reachedByW3a_reach_collapse_root hWF hSV hlkr hderr hco' hW3a hreach'
      rw [hcore.edges] at hedge1
      rcases hedge dt on r e' hderr hlkr honr (subjNode n) hedge1 with hbase | ⟨c, huc, _, hcs, hunc, _⟩
      · -- a base in-edge of a derived R-node is impossible
        exact reachedByRules_derived_no_inedge hSV hlkr hderr hco'
          (reachedByRules_of_admitted hσ0) (subjNode n) hbase
      · -- the reconcile edge's source is n itself: covered AND uncovered
        obtain ⟨hcov, hnstar, _⟩ := hnegm n hn
        have hcn : c = n := subjNode_inj_of_ne_star hcs hnstar huc.symm
        rw [hstars] at hcov
        rw [hcn] at hunc
        rw [hcov] at hunc
        cases hunc
    · -- uposEdgeFree: userset-shaped member vs bare-sourced single edge
      intro k r res hrow n hn hreach
      obtain ⟨dt, on, e', hk, hderr, _hRner, honr, hlkr, _hstars, _, huposm⟩ :=
        hres k r res hrow
      subst hk
      have hco' : ComputedOnly e' := hCO dt r e' hlkr hderr
      have hreach' : NReaches σ'.edges (subjNode n) (objNode ⟨dt, on⟩ r) := by
        rw [hcore.edges]; exact hreach
      have hedge1 := reachedByW3a_reach_collapse_root hWF hSV hlkr hderr hco' hW3a hreach'
      rw [hcore.edges] at hedge1
      rcases hedge dt on r e' hderr hlkr honr (subjNode n) hedge1 with hbase | ⟨c, huc, hcb, hcs, _, _⟩
      · exact reachedByRules_derived_no_inedge hSV hlkr hderr hco'
          (reachedByRules_of_admitted hσ0) (subjNode n) hbase
      · obtain ⟨_, hnp, hnstar, _⟩ := huposm n hn
        have hcn : c = n := subjNode_inj_of_ne_star hcs hnstar huc.symm
        exact hnp (hcn ▸ hcb)
    · -- uposNegDisjoint: ¬covered (upos) vs covered (neg), same row
      intro k r res hrow n hn
      obtain ⟨_, _, _, _, _, _, _, _, _, hnegm, huposm⟩ := hres k r res hrow
      obtain ⟨hnunc, _, _, _⟩ := huposm n hn
      cases hcontains : res.neg.contains n
      · rfl
      · exfalso
        have hnneg : n ∈ res.neg := by
          rw [List.contains_eq_mem] at hcontains
          exact of_decide_eq_true hcontains
        have := (hnegm n hnneg).1
        rw [this] at hnunc
        cases hnunc
  · -- quiescence transfers across the core agreement
    intro d hd
    rw [← hcore.outbox] at hd
    rw [← hcore.watermark]
    exact hQ' d hd

end Zanzibar
