import ZanzibarProofs.Equiv
import ZanzibarProofs.GraphIndex.CascadeStrataAssemble
import ZanzibarProofs.GraphIndex.CascadeStrataEdge

/-!
# W4 — the full-scope restatement (`ReachedBy`, `GraphAdmission`, the final T-theorems)

The W1→W3d-2 arc closed `check = sem` over the fully-operational two-round scheduler
chain (`ReachedByW3d2E`, `CascadeStrataAssemble.lean`). This file is the W4 assembly:

* **`ReachedBy`** — THE operational write-closure, by name. `:= ReachedByW3d2E`
  (logged writes + the state-derived two-round cascade). This is the model of the
  Python write path: `connectedstore/source.py::TupleSource` admission →
  `connectedstore/apply.py::advance_index` →
  `index_v4/processor.py::DeltaProcessor.run_cascade` (a thin node-cache-scope wrapper
  over `::DeltaProcessor._run_cascade`, which is the modeled body). **Scope note
  (`ZT-P4-2c`):** only the SYNCHRONOUS/interleaved schedule is modeled — under
  `ConnectedStore(sync=False)` / `build_index`, `advance_index` applies the WHOLE batch
  and then runs ONE cascade, which `removeGateB`'s drained-prior-state gate excludes.
* **`GraphAdmission`** — the model-level admission bundle: hypotheses the Python
  compiler/write admission guarantees for EVERY accepted schema and store. Each
  field cites the enforcing mechanism.
* **`W4Fragment`** — the HONEST fragment carries: restrictions the current proof
  needs that Python admission does NOT imply. Each field names the gap (ROADMAP
  "W4 — honest gaps"). The final theorems take BOTH bundles; the claim is never
  rounded up to "everything the Python accepts" (plan §7).
* **`w4_within_scope`** — the bundles imply the spec's decision-15 scope predicate
  `GraphAccepts S` (`GraphIndex/State.lean::GraphAccepts`, `SEMANTICS.md` §8): the
  proved fragment sits
  INSIDE the accepted class (the converse is false — acceptance admits more than
  the fragment; that surplus is exactly the honest-gaps list).
* The final **`graph_correct`** (T2b) / **`backend_equivalence`** (T3) /
  **`exclusion_effective`** (T6a) / **`no_ghost_grant`** (T6b) over `ReachedBy` —
  discharging the obligations whose abstract predecessors were deleted-as-false
  (2026-07-10). The W1 pure-direct versions keep their proofs under `*_direct`
  names in `Equiv.lean`.
* **Non-vacuity witnesses** (`W4Witness`): a concrete boolean schema + store
  satisfying both bundles, so the hypothesis set is machine-checked satisfiable —
  the attack of record for a restatement stage (a bundle nobody can inhabit would
  make every theorem below vacuously true).
* **`w4Fragment_of_untainted`** / **`drained_of_untainted`**: on an untainted
  schema every derived-scoped carry is vacuous and every chain state is drained —
  the W2 subsumption argument (ROADMAP W4 delta (2)) as theorems.

**T2a at this scope (`graph_reached_inv` over `ReachedBy`) is PROVED** — the full
8-clause `Inv` holds at every state of the two-round chain (`reachedByW3d2E_inv`,
`CascadeStrataEdge.lean`), and the final `graph_reached_inv` assembles here; closed
2026-07-12j (ROADMAP W4). The W1 pure-direct version keeps its proof as
`graph_reached_inv_direct`.

**★ Leg 5 of the E-chain Direct-arm widening landed here (2026-08-05).**
`GraphAdmission.storeValid` is now `StoreValidRulesD` and `W4Fragment`'s single
`computedOnly` field is five derived-def clauses, so T2b/T3/T6a/T6b are **no longer
VACUOUS on `can_view: [user] but not blocked`** — `W4WitnessDirect.final_applies`
instantiates the unsuffixed `graph_correct` at exactly that store, and
`W4WitnessDirect.outside_old_admission` machine-checks the pre-leg-5 bundle could not be.
`w4Fragment_of_computedOnly` proves the old six fields imply all ten, so nothing that held
before stopped holding. **T2a did NOT widen**: `graph_reached_inv` gained a third bundle
`W4NarrowT2a`, whose docstring carries the reason (probe D.3 machine-checked
`Inv.negEdgeFree` FALSE on the `_d` fragment — a P6 leaf-family modelling limit, not a
Python bug) and whose counterexample at the Direct-arm store is
`W4WitnessDirect.outside_narrow_t2a`.
-/

namespace Zanzibar

/-! ## The final operational closure -/

/-- **`ReachedBy` — the operational write-closure of the graph index, by name.**
    The fully-operational two-round scheduler chain: admitted logged writes
    (`writeLoggedRules`) interleaved with cascade legs that run the state-derived
    enumerated rounds (`runCascade2` over `enumJobs2R1`/`enumJobs2R2` — no
    chain-side hypotheses). Mirrors the Python synchronous write path
    (`connectedstore/apply.py::advance_index` →
    `index_v4/processor.py::DeltaProcessor.run_cascade` →
    `::DeltaProcessor._run_cascade`), in its INTERLEAVED (sync) schedule only. -/
abbrev ReachedBy : GraphState → Schema → Store → Prop := ReachedByW3d2E

/-- **Fully drained**: no dirty derived key above the watermark. The Python
    invariant at every commit boundary (synchronous v1 runs the cascade in the
    writing transaction; boolean spec §7.8). Read correctness holds exactly here —
    mid-drain states are honestly stale (the 12h attack). -/
abbrev Drained (S : Schema) (σ : GraphState) : Prop := cascadeKeys S σ = []

/-! ## The admission bundle and the fragment carries -/

/-- **`GraphAdmission S T` — the model-level admission bundle.** What the Python
    compiler + write admission guarantee for every schema/store they accept; the
    Lean mirror of "this schema compiled and these writes were admitted". Fields
    cite the enforcing mechanism:

    * `wf` — `"."` reserved in declared relation names (`parse_schema_ast`;
      `Core/Schema.lean` `relNameOK`).
    * `nodup` — the AST is dict-keyed: one def per `(type, relation)`.
    * `strat` — derived-dependency cycles raise `ValueError`
      (`compile_boolean_schema`; CLAUDE.md "derived-dependency cycles").
    * `ttuDirect` — `zanzibar_utils_v1.py::_validate_ttu_tuplesets`:
      an untainted TTU tupleset relation must be direct-only.
    * `matchDecl` — compiled `Rule`s route onto declared, untainted families
      (leaf routing splits derived storage onto leaf predicates; `RewriteFilter`
      targets are declared relations).
    * `ranked` — the untainted rewrite graph is acyclic/ranked (the compiler's
      rank assignment; `RulesSaturate.lean`).
    * `objWild` — object-wildcard shapes never target a derived relation
      (`zanzibar_utils_v1.py::_reject_object_wildcard_scope`, first loop).
    * `storeValid` — write admission: every stored tuple matches a declared
      `Direct` restriction of its `(object.type, relation)` def
      (`TupleSource`/`RuleSet.apply` filter admission). **Widened to
      `StoreValidRulesD` by E-chain leg 5 (2026-08-05)**: the untainted disjunct is
      the old `StoreValidRules` clause verbatim, and the derived disjunct admits a
      BARE-subject tuple matching a `Direct` leaf reachable through boolean nesting
      (`exprDirectsAll`) — which is what Python actually admits, since `RuleSet.apply`
      routes a public-name write on `can_view: [user] but not blocked` onto the
      derived def's Direct leaf family. The narrow form rejected exactly that store
      (`W4WitnessDirect.outside_old_admission` machine-checks it), which is why the
      headline theorems used to be VACUOUS on the canonical Zanzibar boolean shape. -/
structure GraphAdmission (S : Schema) (T : Store) : Prop where
  wf : WF S
  nodup : NodupKeys S
  strat : Stratifiable S
  ttuDirect : TtuTuplesetsDirect S
  matchDecl : RewriteMatchDeclared S
  ranked : RewriteRanked S
  objWild : ∀ tr ∈ S.objectWildcards, isDerived S tr = false
  storeValid : StoreValidRulesD S T

/-- **`W4Fragment S T` — the honest fragment carries.** Scope restrictions the
    current proof needs that Python admission does NOT imply (each is a documented
    gap, ROADMAP "W4 — honest gaps at W4 close"):

    * `computedOrDirect` — derived defs are boolean trees over `computed` refs AND
      `direct` grant arms (E-chain leg 5 widened this from `ComputedOnly`, which
      banned the `Direct` arm outright and thereby made every final theorem VACUOUS
      on `can_view: [user] but not blocked`). `.ttu` leaves are still banned —
      Python also compiles `PDerivedTTU`/`PDerivedUserset` plan leaves, still out of
      scope (W3a decision).
    * `directArmsBare` — a derived def's `Direct` arms carry only BARE restrictions
      (`[user]`, never a userset `[group#member]`). Python admits userset
      restrictions on a derived Direct arm; the model's userset flow-through into
      another relation is the next leg, not this one. **Proof-side carry.**
    * `directArmsConcrete` — a derived def's `Direct` arms carry no wildcard-flagged
      restriction. **Python admits the shape this excludes**:
      `define approver: [user, user:*] but not banned` compiles (1 stratum,
      `subject_wildcard_shapes={('user','...')}`, no rejection) and all three
      backends agree over the query grid. Why it is needed: a stored `T:*` grant on a
      derived Direct arm puts a STAR-named subject in *both* `storedDirectSubjects`
      and `edgeHolders`, and `W3cJobValid`'s star-free-candidate clauses then fail for
      **every** enumerated job at that key — so the operational chain has no cascade
      constructor there. It is a **vacuity** boundary, not an unsoundness one.
      Untainted defs' wildcard arms are untouched. **Proof-side carry, not a Python
      restriction** (see `ReconcileCorrect.lean::DirectArmsConcrete`).
    * `computedOnlyOperands` — a derived def's DERIVED computed operands are
      themselves `ComputedOnly`. Only the top derived def may carry a `Direct` arm;
      a Direct arm one stratum down is out of scope for this leg.
    * `noUnionDirects` — a derived def's `Direct` arms sit under `inter`/`excl` only,
      never union-reachable (`exprDirects e = []`): the canonical `but not` shape.
      This is what scopes the chain's `remove` leg (`removeLeg_sem_stable2_d`), and
      it is what `w4_within_scope`'s TTU clause consumes now that
      `directsOnly_of_computedOnly` no longer applies.
    * `twoStrata` — at most TWO derived strata dependency-wise (`hLU2`;
      attack-confirmed load-bearing: a 3-stratum schema fires the round-2 reject,
      `CascadeStrata.lean`). Python handles arbitrary strata.
    * `wsBare` — every declared wildcard restriction is bare (`[T:*]`). Python
      rejects wildcard USERSETS (`[T:*#p]`) only over derived relations
      (the `r.wildcard` raise in `zanzibar_utils_v1.py::_build_plan_tree.build`'s
      `Direct` arm, plus the derived-through-shape form in
      `::_reject_object_wildcard_scope`); over untainted ones they are admitted
      (W1c covered their tuples on the pure-direct fragment only).
    * `bareStar` — stored star subjects are bare and objects concrete: no
      object-wildcard (`w_all`) tuples beyond W1b, no userset-star tuples beyond
      W1c, on this chain.
    * `ttuStarFree` — no stored star subject feeds a TTU tupleset.
    * `term` — derived relations are never TTU targets and never appear as stored
      userset-subject predicates (`NoTtuTarget`/`NoStoreSubjectR`, W3a
      terminality).

    The ADD-ONLY store restriction (decision 6) is a property of the chain — no
    remove legs in `ReachedBy` — not a hypothesis here.

    **Leg-5 note (2026-08-05).** The single `computedOnly` field became the five
    derived-def clauses above. `w4Fragment_of_computedOnly` shows the old bundle is
    subsumed: on a `ComputedOnly` schema every one of the five is vacuous or
    immediate, so nothing that held before stopped holding. What is NOT subsumed is
    **T2a** — see `W4NarrowT2a`. -/
structure W4Fragment (S : Schema) (T : Store) : Prop where
  computedOrDirect : ∀ dt R e, S.lookup (dt, R) = some e →
    isDerived S (dt, R) = true → ComputedOrDirect e
  directArmsBare : ∀ dt R e, S.lookup (dt, R) = some e →
    isDerived S (dt, R) = true → DirectArmsBare e
  directArmsConcrete : DirectArmsConcrete S
  computedOnlyOperands : ∀ dt R e, S.lookup (dt, R) = some e →
    isDerived S (dt, R) = true →
    ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' → ComputedOnly e'
  noUnionDirects : ∀ dt R e, S.lookup (dt, R) = some e →
    isDerived S (dt, R) = true → exprDirects e = []
  twoStrata : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
    ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false
  wsBare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE
  bareStar : BareStarStore T
  ttuStarFree : TtuStarFree S T
  term : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R

/-- **`W4NarrowT2a S T` — the extra carries T2a (`graph_reached_inv`) still needs,
    and T2b no longer does.** The two clauses the E-chain widening could NOT move:
    schema-wide `ComputedOnly` derived defs, and the narrow `StoreValidRules` store
    admission.

    **This is a DECLARED asymmetry, not an oversight.** Leg-0 probe D.3 (2026-07-28)
    machine-checked `Inv.negEdgeFree` FALSE on the `_d` fragment: under
    `StoreValidRulesD` a Direct-arm write lands an edge at the very derived R-node
    whose residue carries the `neg` row, and `Inv` forbids exactly that. It is a
    **modelling limit of the P6 leaf-family collapse, not a Python bug** — verified on
    the real backends, `RuleSet.apply` routes the write onto the leaf family, so the
    edge lands on `#approver.0`/`#approver.2` and never on `#approver` where the `neg`
    row lives; different nodes, I6 disjointness intact throughout (0 mismatches over
    the grid and a 6-way order sweep).

    So `graph_reached_inv` takes this bundle IN ADDITION to `GraphAdmission` +
    `W4Fragment`, and `W4WitnessDirect.outside_narrow_t2a` machine-checks that the
    canonical Direct-arm store does not satisfy it. Widening T2a needs a **design
    decision** first — (a) restate at drained states only, (b) weaken
    `negEdgeFree`/`uposEdgeFree` to exempt the current un-cascaded write leg, or
    (c) model the leaf-family split — not more proof effort. -/
structure W4NarrowT2a (S : Schema) (T : Store) : Prop where
  computedOnly : ∀ dt R e, S.lookup (dt, R) = some e →
    isDerived S (dt, R) = true → ComputedOnly e
  storeValid : StoreValidRules S T

/-! ## The bundles sit inside the spec's accepted scope -/

/-- A `ComputedOnly` expr is never `directs-only` — its leaves are all `computed`,
    which `directsOnly` rejects (and `inter`/`excl` roots are rejected outright). -/
theorem directsOnly_of_computedOnly : ∀ {e : Expr}, ComputedOnly e → directsOnly e = false := by
  intro e
  induction e with
  | computed _ => intro _; rfl
  | direct _ => intro h; exact h.elim
  | ttu _ _ => intro h; exact h.elim
  | union a b iha ihb => intro h; simp only [directsOnly, iha h.1, Bool.false_and]
  | inter _ _ _ _ => intro _; rfl
  | excl _ _ _ _ => intro _; rfl

/-- **A `directs-only` expr always HAS a union-reachable `Direct` arm.** `directsOnly` is
    true only at `.direct _` (where `exprDirects = [rs] ≠ []`) and at a `union` of
    directs-only exprs, whose left operand already supplies one.

    Hypothesis-free by design: Leg-0 probe D.5 (2026-07-28) enumerated all 19,280 depth-3
    `Expr`s and found **0** countermodels **with or without** a `ComputedOrDirect` side
    condition, so the premised form the E-chain plan sketched
    (`ComputedOrDirect e → exprDirects e = [] → directsOnly e = false`) is a strictly weaker
    contrapositive of this. It **is** what `w4_within_scope`'s TTU clause consumes as of
    leg 5 (2026-08-05), now that `W4Fragment.computedOnly` has widened to
    `computedOrDirect` + `noUnionDirects` and `directsOnly_of_computedOnly` above stops
    applying (`directsOnly (.direct rs) = true`). -/
theorem exprDirects_ne_nil_of_directsOnly :
    ∀ {e : Expr}, directsOnly e = true → exprDirects e ≠ [] := by
  intro e
  induction e with
  | direct rs => intro _; simp [exprDirects]
  | computed _ => intro h; simp [directsOnly] at h
  | ttu _ _ => intro h; simp [directsOnly] at h
  | inter _ _ _ _ => intro h; simp [directsOnly] at h
  | excl _ _ _ _ => intro h; simp [directsOnly] at h
  | union a b iha ihb =>
    intro h
    simp only [directsOnly, Bool.and_eq_true] at h
    simp only [exprDirects]
    intro hnil
    exact iha h.1 (List.append_eq_nil_iff.mp hnil).1

/-- **The W4 hypotheses imply the decision-15 scope predicate `GraphAccepts S`**
    (`SEMANTICS.md` §8): (1) object wildcards land on untainted relations —
    admission field `objWild`; (2) a wildcard USERSET restriction cannot reference
    a derived relation — `wsBare` bans non-bare wildcard restrictions outright;
    (3) a TTU tupleset relation is never derived — `ttuDirect` forces a declared
    tupleset def to be directs-only, a directs-only expr always HAS a union-reachable
    `Direct` arm (`exprDirects_ne_nil_of_directsOnly`), and `noUnionDirects` says a
    derived def has none. The CONVERSE is false:
    `GraphAccepts` admits schemas outside `W4Fragment` (the honest-gaps list); this
    lemma orients the fragment inside the accepted class, it does not claim to cover it.

    **Leg-5 note.** Clause 3 used to run through `directsOnly_of_computedOnly`, which
    stops applying once derived defs may carry a `Direct` arm
    (`directsOnly (.direct rs) = true`). The replacement is hypothesis-free and was
    proved in leg 1 after probe D.5 enumerated all 19,280 depth-3 `Expr`s and found no
    countermodel — so the plan's `directsOnly_of_computedOrDirect_of_noUD` was never
    needed (see the plan's §C.5). -/
theorem w4_within_scope {S : Schema} {T : Store}
    (hA : GraphAdmission S T) (hF : W4Fragment S T) : GraphAccepts S := by
  refine ⟨hA.objWild, ?_, ?_⟩
  · -- wildcard usersets: `wsBare` says every wildcard restriction is bare
    intro d hd r hr hwild hne
    exact absurd (hF.wsBare (r.1, r.2.1)
      (List.mem_flatMap.mpr ⟨d, hd, List.mem_filterMap.mpr
        ⟨r, hr, by rw [hwild]; rfl⟩⟩)) hne
  · -- derived TTU tuplesets: a directs-only def HAS a union-reachable `Direct` arm,
    -- and `noUnionDirects` says a derived def has none
    intro d hd tt htt
    by_contra hder
    rw [Bool.not_eq_false] at hder
    obtain ⟨e, hlk⟩ := isDerived_declared hder
    have hdo := hA.ttuDirect d hd tt htt ((d.1.1, tt.2), e)
      (mem_defs_of_lookup hlk) rfl
    exact exprDirects_ne_nil_of_directsOnly hdo (hF.noUnionDirects d.1.1 tt.2 e hlk hder)

/-! ## The final T-theorems -/

/-- **T2b (`graph_correct`), full W4 scope.** At every fully-drained state of the
    operational closure, the graph read computes the stratified-Datalog¬ perfect
    model — for derived AND untainted queries (the statement splits internally).
    Query scope: star subjects are bare (`hqs`), objects concrete (`hqo`).
    This is `graph_correct_w3d2E_d` with its hypothesis set split by provenance.

    **Leg-5 (2026-08-05): this theorem's STATEMENT is byte-identical and its MEANING
    is wider.** It routed through `graph_correct_w3d2E` (schema-wide `ComputedOnly`,
    plain `StoreValidRules`) and now routes through `graph_correct_w3d2E_d`. The
    difference is the whole point of the E-chain arc: the old bundle was
    **UNINHABITABLE** on `can_view: [user] but not blocked`, so this theorem was
    VACUOUS — not narrow — on the most common Zanzibar boolean shape.
    `W4WitnessDirect.final_applies` now instantiates it at exactly such a store, and
    `W4WitnessDirect.outside_old_admission` machine-checks that the old bundle could
    not be. This asymmetry (statement pinned, meaning changed) is precisely what
    `formal/headline_definitions.txt` exists to make visible. -/
theorem graph_correct {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem S T q :=
  graph_correct_w3d2E_d q hA.wf hA.ttuDirect hA.nodup hA.ranked hA.storeValid
    hF.bareStar hF.ttuStarFree hA.matchDecl hA.strat hF.term
    hF.computedOrDirect hF.directArmsBare hF.directArmsConcrete
    hF.computedOnlyOperands hF.twoStrata hF.wsBare hF.noUnionDirects h hq hqs hqo

/-- **T3 (`backend_equivalence`), full W4 scope.** The set engine and the graph
    index agree — by transitivity through `sem` (T1 ∘ T2b). The whole point of the
    shared-spec architecture. -/
theorem backend_equivalence {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ) (hValid : AllValid T)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    SetEngineModel.check S T q = GraphModel.check σ q := by
  rw [setEngine_correct S T q hA.wf hA.strat hValid,
      graph_correct q hA hF h hq hqs hqo]

/-- **T6a (`exclusion_effective`), full W4 scope.** Whenever the spec denies, BOTH
    backends deny — with real exclusion content at this scope: `sem` denies a
    subject removed by a `but not` operand, so neither backend can grant it
    (`exclusion_effective_w3c` exhibits the concrete under-a-star-grant case). -/
theorem exclusion_effective {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ) (hValid : AllValid T)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T q = false) :
    SetEngineModel.check S T q = false ∧ GraphModel.check σ q = false := by
  refine ⟨?_, ?_⟩
  · rw [setEngine_correct S T q hA.wf hA.strat hValid]; exact hDeny
  · rw [graph_correct q hA hF h hq hqs hqo]; exact hDeny

/-- **T6b (`no_ghost_grant`), full W4 scope.** If the spec denies on the chain's
    own store, the graph denies at any fully-drained state — no stale edge or
    residue row survives the drain (`T'` is the store as written; `σ'` its
    operationally reached state). -/
theorem no_ghost_grant {S : Schema} {T' : Store} {σ' : GraphState} (q : Query)
    (hA : GraphAdmission S T') (hF : W4Fragment S T')
    (h : ReachedBy σ' S T') (hq : Drained S σ')
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR)
    (hDeny : sem S T' q = false) :
    GraphModel.check σ' q = false := by
  rw [graph_correct q hA hF h hq hqs hqo]; exact hDeny

/-- **T2a (`graph_reached_inv`), full W4 scope.** The graph-index structural and
    residue invariant `Inv` (I1–I3 well-formedness/acyclicity + the four I6
    residue-hygiene clauses) holds at EVERY operationally-reached state — dirty
    keys and mid-drain states included, NOT only the drained ones. This discharges
    the T2a obligation whose abstract predecessor was deleted-as-false (2026-07-10,
    it quantified over a junk-admitting closure); the honest restatement is over
    `ReachedBy`. It is `reachedByW3d2E_inv` with the bundles unpacked.

    **⚠ Leg-5 (2026-08-05): T2a takes a THIRD bundle that T2b does not.** Before the
    E-chain widening the hypothesis split was the same as `graph_correct`'s. It is not
    any more: `W4NarrowT2a` re-imposes schema-wide `ComputedOnly` and the narrow
    `StoreValidRules`, so **`graph_reached_inv` is still vacuous on Direct-arm derived
    stores while `graph_correct` no longer is**
    (`W4WitnessDirect.outside_narrow_t2a` machine-checks the store fails this bundle).
    That is not a proof gap that more effort would close — probe D.3 machine-checked
    `Inv.negEdgeFree` FALSE on the `_d` fragment; read `W4NarrowT2a`'s docstring for
    why Python is nonetheless fine and what design decision is owed. Making the
    asymmetry a visible extra argument, rather than leaving it buried in a widened
    bundle, is the deliberate output of this leg. -/
theorem graph_reached_inv {S : Schema} {T : Store} {σ : GraphState}
    (hA : GraphAdmission S T) (hF : W4Fragment S T) (hN : W4NarrowT2a S T)
    (h : ReachedBy σ S T) :
    Inv S σ :=
  reachedByW3d2E_inv h hA.wf hA.ttuDirect hA.nodup hA.ranked hA.matchDecl
    hA.strat hN.computedOnly hF.twoStrata hF.wsBare hN.storeValid hF.bareStar
    hF.ttuStarFree hF.term

/-! ## The W2 subsumption — untainted schemas sit inside the full scope

ROADMAP W4 delta (2): on an `UntaintedSchema` every derived-scoped carry is
vacuous and every chain state is drained, so `graph_correct` needs only the three
contentful carries (`wsBare`/`bareStar`/`ttuStarFree`). The residual generality of
W2's `graph_correct_rulesBS` (no `hWSbare`/`hMatch`, plain-fold chain) is recorded
in the ROADMAP inventory, not re-proved here. -/

/-- On an untainted schema no key is derived, so `affectedKeys` emits nothing and
    every state is drained — the cascade never has work. -/
theorem drained_of_untainted {S : Schema} (hUT : UntaintedSchema S)
    (σ : GraphState) : Drained S σ := by
  show cascadeKeys S σ = []
  unfold cascadeKeys
  rw [List.flatMap_eq_nil_iff]
  intro d _
  unfold affectedKeys
  rw [if_neg (by simp [isDerived_untainted hUT]), List.nil_append]
  rw [List.flatMap_eq_nil_iff]
  intro v _
  split
  · rfl
  · rw [List.filterMap_eq_nil_iff]
    intro k _
    simp [isDerived_untainted hUT k]

/-- **The pre-leg-5 `ComputedOnly` fragment is SUBSUMED by the widened one.** Given
    exactly the six fields `W4Fragment` carried before the E-chain Direct-arm
    widening, all ten hold: a `ComputedOnly` derived def is `ComputedOrDirect`
    (`computedOnly_computedOrDirect`), vacuously `DirectArmsBare`
    (`computedOnly_directArmsBare`), has no `Direct` leaf at all under boolean
    nesting (`exprDirectsAll_computedOnly` ⇒ `DirectArmsConcrete` is vacuous) and
    none union-reachable either (`exprDirects_computedOnly` ⇒ `noUnionDirects`),
    and its derived operands are `ComputedOnly` by the same schema-wide hypothesis.

    This is the machine-checked form of "nothing that held before stopped holding" —
    the leg widened the bundle rather than trading one scope for another. It is also
    what keeps `W4Witness`/`W4WitnessUnion` (both `ComputedOnly` schemas) inhabiting
    the new bundle without re-deciding anything. **The T2a half is NOT subsumed**;
    see `W4NarrowT2a`. -/
theorem w4Fragment_of_computedOnly {S : Schema} {T : Store}
    (hCO : ∀ dt R e, S.lookup (dt, R) = some e →
      isDerived S (dt, R) = true → ComputedOnly e)
    (hLU2 : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
        ∀ e', S.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false)
    (hWS : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T)
    (hterm : ∀ dt R, isDerived S (dt, R) = true →
      NoTtuTarget S R ∧ NoStoreSubjectR T R) : W4Fragment S T where
  computedOrDirect := fun dt R e hlk hder =>
    computedOnly_computedOrDirect (hCO dt R e hlk hder)
  directArmsBare := fun dt R e hlk hder =>
    computedOnly_directArmsBare (hCO dt R e hlk hder)
  directArmsConcrete := by
    intro dt R e hlk hder rs hrs
    rw [exprDirectsAll_computedOnly (hCO dt R e hlk hder)] at hrs
    cases hrs
  computedOnlyOperands := fun _ _ _ _ _ _ _ hder' e' hlk' => hCO _ _ e' hlk' hder'
  noUnionDirects := fun dt R e hlk hder => exprDirects_computedOnly (hCO dt R e hlk hder)
  twoStrata := hLU2
  wsBare := hWS
  bareStar := hBS
  ttuStarFree := hTS
  term := hterm

/-- On an untainted schema the fragment bundle collapses to its three contentful
    fields — every derived-scoped carry is vacuous (`isDerived` is constantly
    `false`). -/
theorem w4Fragment_of_untainted {S : Schema} {T : Store} (hUT : UntaintedSchema S)
    (hWS : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T) : W4Fragment S T :=
  w4Fragment_of_computedOnly
    (fun dt R _ _ hder => absurd hder (by simp [isDerived_untainted hUT]))
    (fun dt R _ _ hder => absurd hder (by simp [isDerived_untainted hUT]))
    hWS hBS hTS
    (fun dt R hder => absurd hder (by simp [isDerived_untainted hUT]))

/-- On an untainted schema the T2a narrow bundle is free too: the `ComputedOnly`
    carry is vacuous, and `StoreValidRulesD` collapses to `StoreValidRules` because
    every stored tuple lands on an untainted key (the widened form's second disjunct
    needs `isDerived = true`). So the leg-5 asymmetry costs untainted schemas
    nothing — it is a purely derived-side carry. -/
theorem w4NarrowT2a_of_untainted {S : Schema} {T : Store} (hUT : UntaintedSchema S)
    (hSVD : StoreValidRulesD S T) : W4NarrowT2a S T where
  computedOnly := fun dt R _ _ hder => absurd hder (by simp [isDerived_untainted hUT])
  storeValid := by
    intro t ht
    rcases hSVD t ht with ⟨_, h⟩ | ⟨hder, _⟩
    · exact h
    · exact absurd hder (by simp [isDerived_untainted hUT])

end Zanzibar

/-! ## Non-vacuity witnesses (the attack of record for a restatement stage)

A restatement can be "proved" vacuously if its hypothesis bundle is uninhabitable.
`Sx`/`Tx` is a REAL boolean schema in compiled form — `r := a but not b` at type
`doc`, exactly the shape `compile_ruleset` emits for a root exclusion — with a
store granting `a` to a concrete subject. Both bundles are inhabited, so the
final theorems have content. -/

namespace Zanzibar
namespace W4Witness

/-- `doc#a := [user]`, `doc#b := [user]`, `doc#r := a but not b` (compiled form:
    the boolean root reads its operands via `computed`). -/
def Sx : Schema :=
  ⟨[(("doc", "a"), .direct [("user", BARE, false)]),
    (("doc", "b"), .direct [("user", BARE, false)]),
    (("doc", "r"), .excl (.computed "a") (.computed "b"))], []⟩

/-- One admitted write: `user:alice ∈ a@doc:1`. -/
def Tx : Store := [⟨⟨"user", "alice", BARE⟩, "a", ⟨"doc", "1"⟩⟩]

/-- The admission bundle is inhabited by the witness schema/store. -/
theorem accepts : GraphAdmission Sx Tx where
  wf := ⟨by
    intro p hp
    simp only [Sx, List.mem_cons, List.not_mem_nil, or_false] at hp
    rcases hp with rfl | rfl | rfl <;> simp [relNameOK]⟩
  nodup := by unfold NodupKeys; decide
  strat := by unfold Stratifiable; decide
  ttuDirect := by unfold TtuTuplesetsDirect; decide
  matchDecl := by unfold RewriteMatchDeclared; decide
  ranked := ⟨fun _ => 0, by decide, fun _ => Nat.zero_le _⟩
  objWild := by decide
  storeValid := by
    intro t ht
    simp only [Tx, List.mem_singleton] at ht
    subst ht
    -- untainted key `doc#a` ⇒ `StoreValidRulesD`'s FIRST disjunct, which is the
    -- pre-leg-5 `StoreValidRules` clause verbatim
    exact Or.inl ⟨by decide, .direct [("user", BARE, false)], [("user", BARE, false)],
      rfl, by simp [exprDirects], by decide⟩

/-- The fragment bundle is inhabited by the witness schema/store. `Sx` is
    `ComputedOnly`, so the five derived-def clauses the leg-5 widening introduced
    come free through `w4Fragment_of_computedOnly` — this witness proves the same
    six facts it always did, in the same order. -/
theorem fragment : W4Fragment Sx Tx := by
  refine w4Fragment_of_computedOnly ?_ ?_ ?_ ?_ ?_ ?_
  -- (1) `computedOnly`
  · intro dt R e hlk hder
    have hmem := mem_defs_of_lookup hlk
    simp only [Sx, List.mem_cons, List.not_mem_nil, or_false,
      Prod.mk.injEq] at hmem
    rcases hmem with ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩
    · exact absurd hder (by decide)
    · exact absurd hder (by decide)
    · exact ⟨trivial, trivial⟩
  -- (2) `twoStrata`
  · intro dt R e hlk hder r' hr' hder' e' hlk' r'' hr''
    have hmem := mem_defs_of_lookup hlk
    simp only [Sx, List.mem_cons, List.not_mem_nil, or_false,
      Prod.mk.injEq] at hmem
    rcases hmem with ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩
    · exact absurd hder (by decide)
    · exact absurd hder (by decide)
    · -- `r`'s operands `a`/`b` are untainted, contradicting `hder'`
      simp only [computedRefs, List.cons_append, List.nil_append,
        List.mem_cons, List.not_mem_nil, or_false] at hr'
      rcases hr' with rfl | rfl
      · exact absurd hder' (by decide)
      · exact absurd hder' (by decide)
  -- (3) `wsBare`
  · decide
  -- (4) `bareStar`
  · unfold BareStarStore; decide
  -- (5) `ttuStarFree`
  · intro t _ _ a ha tr _
    rw [show schemaRewrites Sx = [] from rfl] at ha
    cases ha
  -- (6) `term`
  · intro dt R hder
    have hkey : (dt, R) = ("doc", "r") := by
      unfold isDerived at hder
      rw [show taintedKeys Sx = [("doc", "r")] from by decide] at hder
      simpa using hder
    rw [Prod.mk.injEq] at hkey
    obtain ⟨rfl, rfl⟩ := hkey
    refine ⟨?_, ?_⟩
    · intro r hr tr _
      rw [show schemaRewrites Sx = [] from rfl] at hr
      cases hr
    · intro t ht
      simp only [Tx, List.mem_singleton] at ht
      subst ht
      decide

/-- The witness bundles are jointly inside the spec's accepted scope. -/
theorem within_scope : GraphAccepts Sx := w4_within_scope accepts fragment

-- (No `AllValid Tx` witness: `ValidIdent` is deliberately OPAQUE (`Core/Ident.lean`),
-- so identifier validity of a concrete store is not derivable in the model — the
-- T3/T6 inhabitation claim is `GraphAdmission ∧ W4Fragment` + the T2b witness above.)

end W4Witness

/-! ## A UNION-ROOTED derived witness (the exact scope Legs 1-2 widened)

`Sy`/`Ty` is the conformance corpus `taint_union_over_boolean` in compiled form:
a boolean `viewer := base ∖ blocked` over a bare-star base, then a
UNION-rooted derived def `approver := viewer ∪ admin`. Before the rootB widening
the fragment's `rootB` field rejected this (a union at the derived root); with
`RootBoolean` deleted (Leg 2) and the taint filter on `schemaRewrites` (Leg 1),
BOTH bundles are inhabited — so the widened `W4Fragment` non-vacuously admits a
union-rooted derived schema, and the final theorems have content there. The taint
filter is what makes `schemaRewrites Sy = []` (the `approver` union arms are
routed OFF the fanout because `approver` is derived), exactly as `compile_ruleset`
does — the mirror that closed the stale-fanout state divergence (2026-07-17). -/

namespace W4WitnessUnion

/-- `doc#base := [user:*]` (bare star), `doc#blocked := [user]`,
    `doc#viewer := base but not blocked`, `doc#admin := [user]`,
    `doc#approver := viewer or admin` (UNION at the derived root). -/
def Sy : Schema :=
  ⟨[(("doc", "base"), .direct [("user", BARE, true)]),
    (("doc", "blocked"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .excl (.computed "base") (.computed "blocked")),
    (("doc", "admin"), .direct [("user", BARE, false)]),
    (("doc", "approver"), .union (.computed "viewer") (.computed "admin"))], []⟩

/-- The corpus's three admitted writes: `user:*` (bare star) ∈ base@doc:d1,
    `user:mallory` ∈ blocked@doc:d1, `user:root` ∈ admin@doc:d1. -/
def Ty : Store :=
  [⟨⟨"user", STAR, BARE⟩, "base", ⟨"doc", "d1"⟩⟩,
   ⟨⟨"user", "mallory", BARE⟩, "blocked", ⟨"doc", "d1"⟩⟩,
   ⟨⟨"user", "root", BARE⟩, "admin", ⟨"doc", "d1"⟩⟩]

/-- The admission bundle is inhabited by the union-rooted witness. -/
theorem accepts : GraphAdmission Sy Ty where
  wf := ⟨by
    intro p hp
    simp only [Sy, List.mem_cons, List.not_mem_nil, or_false] at hp
    rcases hp with rfl | rfl | rfl | rfl | rfl <;> simp [relNameOK]⟩
  nodup := by unfold NodupKeys; decide
  strat := by unfold Stratifiable; decide
  ttuDirect := by unfold TtuTuplesetsDirect; decide
  matchDecl := by unfold RewriteMatchDeclared; decide
  ranked := ⟨fun _ => 0, by decide, fun _ => Nat.zero_le _⟩
  objWild := by decide
  storeValid := by
    intro t ht
    simp only [Ty, List.mem_cons, List.not_mem_nil, or_false] at ht
    -- all three writes land on untainted keys (`base`/`blocked`/`admin`) ⇒
    -- `StoreValidRulesD`'s FIRST disjunct, the pre-leg-5 clause verbatim
    rcases ht with rfl | rfl | rfl
    · exact Or.inl ⟨by decide, .direct [("user", BARE, true)], [("user", BARE, true)],
        rfl, by simp [exprDirects], by decide⟩
    · exact Or.inl ⟨by decide, .direct [("user", BARE, false)], [("user", BARE, false)],
        rfl, by simp [exprDirects], by decide⟩
    · exact Or.inl ⟨by decide, .direct [("user", BARE, false)], [("user", BARE, false)],
        rfl, by simp [exprDirects], by decide⟩

/-- The fragment bundle is inhabited by the union-rooted witness. `Sy` is
    `ComputedOnly` too, so the leg-5 clauses come free through
    `w4Fragment_of_computedOnly`. -/
theorem fragment : W4Fragment Sy Ty := by
  refine w4Fragment_of_computedOnly ?_ ?_ ?_ ?_ ?_ ?_
  -- (1) `computedOnly`
  · intro dt R e hlk hder
    have hmem := mem_defs_of_lookup hlk
    simp only [Sy, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hmem
    rcases hmem with ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩ |
      ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩
    · exact absurd hder (by decide)                    -- base (untainted)
    · exact absurd hder (by decide)                    -- blocked (untainted)
    · exact ⟨trivial, trivial⟩                          -- viewer := excl (computed) (computed)
    · exact absurd hder (by decide)                    -- admin (untainted)
    · exact ⟨trivial, trivial⟩                          -- approver := union (computed) (computed)
  -- (2) `twoStrata`
  · intro dt R e hlk hder r' hr' hder' e' hlk' r'' hr''
    have hmem := mem_defs_of_lookup hlk
    simp only [Sy, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hmem
    rcases hmem with ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩ |
      ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩
    · exact absurd hder (by decide)                    -- base
    · exact absurd hder (by decide)                    -- blocked
    · -- viewer's operands `base`/`blocked` are untainted, contradicting `hder'`
      simp only [computedRefs, List.cons_append, List.nil_append,
        List.mem_cons, List.not_mem_nil, or_false] at hr'
      rcases hr' with rfl | rfl
      · exact absurd hder' (by decide)
      · exact absurd hder' (by decide)
    · exact absurd hder (by decide)                    -- admin
    · -- approver's operands are `viewer` (derived, stratum 2) and `admin` (untainted)
      simp only [computedRefs, List.cons_append, List.nil_append,
        List.mem_cons, List.not_mem_nil, or_false] at hr'
      rcases hr' with rfl | rfl
      · -- r' = viewer; its def `excl base blocked` reads only untainted leaves
        rw [show Sy.lookup ("doc", "viewer")
              = some (Expr.excl (.computed "base") (.computed "blocked")) from rfl,
            Option.some.injEq] at hlk'
        subst hlk'
        simp only [computedRefs, List.cons_append, List.nil_append,
          List.mem_cons, List.not_mem_nil, or_false] at hr''
        rcases hr'' with rfl | rfl
        · decide                                        -- isDerived (doc, base) = false
        · decide                                        -- isDerived (doc, blocked) = false
      · exact absurd hder' (by decide)                  -- r' = admin (untainted)
  -- (3) `wsBare`
  · decide
  -- (4) `bareStar`
  · unfold BareStarStore; decide
  -- (5) `ttuStarFree`
  · intro t _ _ a ha tr _
    rw [show schemaRewrites Sy = [] from by decide] at ha
    cases ha
  -- (6) `term`
  · intro dt R hder
    -- `R` is one of the two derived relations `viewer`/`approver` — neither is `...`
    have hkey : (dt, R) = ("doc", "viewer") ∨ (dt, R) = ("doc", "approver") := by
      unfold isDerived at hder
      rw [show taintedKeys Sy = [("doc", "viewer"), ("doc", "approver")] from by decide] at hder
      simpa using hder
    refine ⟨?_, ?_⟩
    · intro r hr tr _
      rw [show schemaRewrites Sy = [] from by decide] at hr
      cases hr
    · -- every stored subject is bare (`...`); a derived relation name is never `...`
      have hRne : R ≠ BARE := by
        rcases hkey with h | h <;> (rw [Prod.mk.injEq] at h; rw [h.2]; decide)
      intro t ht
      simp only [Ty, List.mem_cons, List.not_mem_nil, or_false] at ht
      rcases ht with rfl | rfl | rfl <;> exact hRne.symm

/-- The union-rooted witness bundles are jointly inside the spec's accepted scope. -/
theorem within_scope : GraphAccepts Sy := w4_within_scope accepts fragment

end W4WitnessUnion

/-! ## A DIRECT-ARM derived witness (the C-chain `graph_correct_w3d2_d` scope)

`Sd`/`Td` is the conformance corpus `direct_arm_exclusion` in compiled form:
`approver := [user] but not banned` — a derived def whose exclusion BASE is a
**`Direct` storage arm on the derived relation itself** (AST
`excl (direct [user]) (computed banned)`), with `banned := [user]` untainted and
a store granting `user:alice` through that Direct arm.

This is the shape the whole E-chain Direct-arm widening exists for, and **as of leg
5 (2026-08-05) it is INSIDE the final T2b's scope** — `final_applies` below
instantiates the unsuffixed `graph_correct` here. The record of how it got there,
because the intermediate states are easy to confuse:

* It used to sit outside on TWO counts (the honest record, 2026-07-20e).
  `W4Fragment.computedOnly` rejected the `direct` leaf in the derived def, and
  `GraphAdmission.storeValid` (plain `StoreValidRules`) is FALSE at `Td` — the
  Direct arm sits under `excl`, so `exprDirects = []` on the derived def and a
  stored Direct-arm grant is admissible only under `StoreValidRulesD`.
  `outside_old_admission` below machine-checks that second one, and it is KEPT
  precisely because it is now the proof that the widening was contentful rather
  than a relabeling.
* Both counts are closed. Leg 2 (2026-08-04) changed the operational enumeration
  model (`enumJob2` → `enumJob2D`); legs 3–4 (2026-08-05) built the `_d`
  projection (`reachedByW3d2E_toC_d` / `graph_correct_w3d2E_d`, instantiated at
  THIS pair by `w3d2E_correct_applies`); leg 5 rebased `W4Fragment` and
  `GraphAdmission` themselves, so the `_d` chain no longer stands BESIDE the final
  theorems — it IS them.
* **T2a is the exception and stays one.** `graph_reached_inv` carries a third
  bundle `W4NarrowT2a`, and `outside_narrow_t2a` below machine-checks that `Td`
  fails it. Probe D.3 proved `Inv.negEdgeFree` FALSE on the `_d` fragment; that is
  a P6 leaf-family MODELLING limit, not a Python bug.

The declarations below therefore come in two layers. The `_d`-chain layer inhabits
the hypothesis bundle of the C-chain T2b `graph_correct_w3d2_d`
(`CascadeStrataResettle.lean`, audited) at `Sd`/`Td` — `accepts` (the admission
side, with `StoreValidRulesD` in place of `storeValid`), `fragment` (the `_d`
fragment carries), `correct_applies`, `coverage_applies`, `toC_applies`,
`w3d2E_correct_applies`. The leg-5 layer (`admission` / `w4fragment` /
`final_applies` / `outside_narrow_t2a`) inhabits the HEADLINE bundles. Non-vacuity
of the chain itself is operational: the Exec driver reaches drained states over
exactly this schema (attack-run 2026-07-20e: the 4-tuple corpus store drains with
`check = sem` on the full truth table). -/

namespace W4WitnessDirect

/-- `doc#banned := [user]` (untainted), `doc#approver := [user] but not banned`
    (compiled form: the exclusion's base is a `Direct` arm ON the derived def). -/
def Sd : Schema :=
  ⟨[(("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "approver"), .excl (.direct [("user", BARE, false)]) (.computed "banned"))], []⟩

/-- One admitted write THROUGH THE DIRECT ARM of the derived def:
    `user:alice ∈ approver@doc:d1`. -/
def Td : Store := [⟨⟨"user", "alice", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩]

/-- **The witness store is genuinely outside the OLD admission bundle**: plain
    `StoreValidRules` (= `GraphAdmission.storeValid`) rejects the Direct-arm
    grant — its arm is under `excl`, so `exprDirects` on the derived def is
    empty. The widening is contentful, not a relabeling. -/
theorem outside_old_admission : ¬ StoreValidRules Sd Td := by
  intro h
  obtain ⟨e, rs, hlk, hrs, _⟩ := h ⟨⟨"user", "alice", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩
    (List.mem_singleton.mpr rfl)
  rw [show Sd.lookup ("doc", "approver")
        = some (Expr.excl (.direct [("user", BARE, false)]) (.computed "banned")) from rfl,
      Option.some.injEq] at hlk
  subst hlk
  simp [exprDirects] at hrs

/-- The admission side of `graph_correct_w3d2_d`'s bundle is inhabited —
    `GraphAdmission` with `storeValid` WIDENED to `StoreValidRulesD` (the
    faithful mirror of Python admission on Direct-arm schemas: `RuleSet.apply`
    routes a public-name write onto the derived def's Direct leaf family). -/
theorem accepts : WF Sd ∧ NodupKeys Sd ∧ Stratifiable Sd ∧ TtuTuplesetsDirect Sd ∧
    RewriteMatchDeclared Sd ∧ RewriteRanked Sd ∧ StoreValidRulesD Sd Td := by
  refine ⟨⟨?_⟩, by unfold NodupKeys; decide, by unfold Stratifiable; decide,
    by unfold TtuTuplesetsDirect; decide, by unfold RewriteMatchDeclared; decide,
    ⟨fun _ => 0, by decide, fun _ => Nat.zero_le _⟩, ?_⟩
  · intro p hp
    simp only [Sd, List.mem_cons, List.not_mem_nil, or_false] at hp
    rcases hp with rfl | rfl <;> simp [relNameOK]
  · intro t ht
    simp only [Td, List.mem_singleton] at ht
    subst ht
    refine Or.inr ⟨by decide, rfl,
      .excl (.direct [("user", BARE, false)]) (.computed "banned"),
      [("user", BARE, false)], rfl, ?_, by decide, ?_⟩
    · simp [exprDirectsAll]
    · intro r hr
      simp only [List.mem_singleton] at hr
      subst hr; rfl

/-- The `_d` fragment carries are inhabited: schema-wide `ComputedOrDirect` +
    `DirectArmsBare` on derived defs, derived OPERANDS `ComputedOnly` (vacuous —
    `banned` is untainted), two strata, bare wildcard shapes, `hNoUD` (the Direct
    arm sits under `excl`, the canonical `but not` shape), and the store
    disciplines (`BareStarStore`/`TtuStarFree`/terminality). -/
theorem fragment :
    (∀ dt R e, Sd.lookup (dt, R) = some e → isDerived Sd (dt, R) = true →
      ComputedOrDirect e) ∧
    (∀ dt R e, Sd.lookup (dt, R) = some e → isDerived Sd (dt, R) = true →
      DirectArmsBare e) ∧
    (∀ dt R e, Sd.lookup (dt, R) = some e → isDerived Sd (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived Sd (dt, r') = true →
        ∀ e', Sd.lookup (dt, r') = some e' → ComputedOnly e') ∧
    (∀ dt R e, Sd.lookup (dt, R) = some e → isDerived Sd (dt, R) = true →
      ∀ r' ∈ computedRefs e, isDerived Sd (dt, r') = true →
        ∀ e', Sd.lookup (dt, r') = some e' →
          ∀ r'' ∈ computedRefs e', isDerived Sd (dt, r'') = false) ∧
    (∀ sh ∈ wildcardShapes Sd, sh.2 = BARE) ∧
    (∀ dt R e, Sd.lookup (dt, R) = some e → isDerived Sd (dt, R) = true →
      exprDirects e = []) ∧
    BareStarStore Td ∧ TtuStarFree Sd Td ∧
    (∀ dt R, isDerived Sd (dt, R) = true → NoTtuTarget Sd R ∧ NoStoreSubjectR Td R) := by
  have hkeys : ∀ dt R e, Sd.lookup (dt, R) = some e → isDerived Sd (dt, R) = true →
      (dt, R) = ("doc", "approver") ∧
      e = Expr.excl (.direct [("user", BARE, false)]) (.computed "banned") := by
    intro dt R e hlk hder
    have hmem := mem_defs_of_lookup hlk
    simp only [Sd, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hmem
    rcases hmem with ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩
    · exact absurd hder (by decide)
    · exact ⟨rfl, rfl⟩
  refine ⟨?_, ?_, ?_, ?_, by decide, ?_, by unfold BareStarStore; decide, ?_, ?_⟩
  · intro dt R e hlk hder
    obtain ⟨_, rfl⟩ := hkeys dt R e hlk hder
    exact ⟨trivial, trivial⟩
  · intro dt R e hlk hder
    obtain ⟨_, rfl⟩ := hkeys dt R e hlk hder
    refine ⟨?_, trivial⟩
    intro r hr
    simp only [List.mem_singleton] at hr
    subst hr; rfl
  · -- operand-`ComputedOnly`: approver's only computed ref is `banned`, untainted
    intro dt R e hlk hder r' hr' hder'
    obtain ⟨⟨rfl, rfl⟩, rfl⟩ := hkeys dt R e hlk hder
    simp only [computedRefs, List.nil_append,
      List.mem_cons, List.not_mem_nil, or_false] at hr'
    subst hr'
    exact absurd hder' (by decide)
  · -- two strata: same vacuity — the only computed ref is untainted
    intro dt R e hlk hder r' hr' hder'
    obtain ⟨⟨rfl, rfl⟩, rfl⟩ := hkeys dt R e hlk hder
    simp only [computedRefs, List.nil_append,
      List.mem_cons, List.not_mem_nil, or_false] at hr'
    subst hr'
    exact absurd hder' (by decide)
  · -- `hNoUD`: the Direct arm sits under `excl`, so no union-reachable arm
    intro dt R e hlk hder
    obtain ⟨_, rfl⟩ := hkeys dt R e hlk hder
    rfl
  · intro t _ _ a ha tr _
    rw [show schemaRewrites Sd = [] from rfl] at ha
    cases ha
  · intro dt R hder
    have hkey : (dt, R) = ("doc", "approver") := by
      unfold isDerived at hder
      rw [show taintedKeys Sd = [("doc", "approver")] from by decide] at hder
      simpa using hder
    rw [Prod.mk.injEq] at hkey
    obtain ⟨rfl, rfl⟩ := hkey
    refine ⟨?_, ?_⟩
    · intro r hr tr _
      rw [show schemaRewrites Sd = [] from rfl] at hr
      cases hr
    · intro t ht
      simp only [Td, List.mem_singleton] at ht
      subst ht
      decide

/-- The witness schema is inside the spec's decision-15 accepted scope. -/
theorem within_scope : GraphAccepts Sd := by
  refine ⟨by decide, ?_, by decide⟩
  intro d hd r hr hwild _
  simp only [Sd, List.mem_cons, List.not_mem_nil, or_false] at hd
  rcases hd with rfl | rfl <;>
    (simp only [exprRestrictions, List.mem_cons, List.append_nil,
        List.not_mem_nil, or_false] at hr;
     subst hr; exact absurd hwild (by decide))

/-- **The bundle is JOINTLY dischargeable**: the audited Direct-arm T2b
    `graph_correct_w3d2_d` instantiates at the witness pair with every
    schema/store hypothesis closed by `accepts` + `fragment` — the machine check
    that the Direct-arm fragment's hypothesis set is satisfiable by a real
    compiled Direct-arm boolean schema (the attack of record for a widening). -/
theorem correct_applies {σ : GraphState} (q : Query)
    (h : ReachedByW3d2C σ Sd Td) (hq : cascadeKeys Sd σ = [])
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem Sd Td q := by
  obtain ⟨hWF, hNK, hStrat, hTT, hMatch, hR, hSV⟩ := accepts
  obtain ⟨hCD, hDAB, hCOop, hLU2, hWSbare, hNoUD, hBS, hTS, hterm⟩ := fragment
  exact graph_correct_w3d2_d q hWF hTT hNK hR hSV hBS hTS hMatch hStrat hterm
    hCD hDAB hCOop hLU2 hWSbare hNoUD h hq hqs hqo

/-- **The `_d`/`_filt` COVERAGE packaging is jointly dischargeable too** — the leg-3
    non-vacuity attack (2026-08-05). `w3dJobCoverage_enumJob2D_state` instantiates at the
    witness pair, at the real derived key `doc#approver` whose expression carries the
    Direct arm, with every schema/store hypothesis closed by `accepts` + `fragment`.

    This is the check a packaging clone actually needs. The theorem is nothing but a
    chain of `_d`/`_filt` forms, and the failure mode of record for such a chain is a
    hypothesis pair no store can satisfy — the 2026-07-20b kill was exactly that (the
    FULL-store `_d` shadow pair is jointly unsatisfiable on this fragment, which is why
    the packaging must route through `reachedByW3d2_shadow_d` / `w3d2_leg_context_d_filt`
    and not their unfiltered siblings). Typechecking alone cannot see that: a lemma with
    unsatisfiable premises compiles, audits clean, and passes every pin in the gate
    (`formal/conformance/statement_pin.py` says so in as many words).

    **The widening is contentful, not a relabeling**: the untainted twin
    `w3dJobCoverage_enumJob2_state` demands `StoreValidRules Sd Td`, which
    `outside_old_admission` machine-checks is FALSE. So the base theorem cannot be
    instantiated here at all and this one can — and that is what makes this witness an
    instrument rather than a decoration.

    **Controlled 2026-08-05, and the control is the whole point.** Sabotage: give
    `w3dJobCoverage_enumJob2D_state` one extra premise `(_hSABOTAGE : StoreValidRules S T)`
    — the narrowest plausible weakening, a premise that is FALSE at every store this
    theorem is supposed to be about, added in a form the proof never uses. Observed:

        A. lake build ZanzibarProofs.GraphIndex.CascadeStrataEnum
           → Build completed successfully (1061 jobs).
        B. lake build ZanzibarProofs.FullScope
           → error: … Application type mismatch: The argument
               h
             has type
               ReachedByW3d2 σ Sd Td
             but is expected to have type
               StoreValidRules Sd Td
             in the application
               w3dJobCoverage_enumJob2D_state hWF hTT hNK hR hSV hBS hTS hMatch
                 hStrat hterm hCD hDAB hWSbare h

    (the error lands on the `exact` below; its line number is deliberately not quoted —
    it moves every time this docstring is edited)

    (A) is the finding: **the sabotaged theorem compiles, and would have audited clean
    and passed every pin in the gate.** Lean is happy to prove things about nothing.
    (B) is this declaration doing the only work that catches it. Delete `coverage_applies`
    and the vacuity is invisible to the entire repo.

    Scope, stated rather than implied. `hsettledOps` is DISCHARGED here (vacuously —
    `approver`'s only computed ref is `banned`, which is untainted), so this witness
    exercises the packaging, not the operand-settled path; the same vacuity is already
    recorded for `fragment`'s operand-`ComputedOnly` clause. `h` stays a hypothesis, the
    same KIND of residual `correct_applies` carries — though a strictly weaker one:
    `correct_applies` assumes the DRAINED `ReachedByW3d2C`, this assumes plain
    `ReachedByW3d2`, and `reachedByW3d2C_toW3d2` goes that way and not the other. Either
    way, non-vacuity of the CHAIN itself is operational (the Exec driver reaches these
    states over exactly this schema), not proof-side. -/
theorem coverage_applies {σ : GraphState} {on : String} (hqo : on ≠ STAR)
    (h : ReachedByW3d2 σ Sd Td) :
    W3dJobCoverage Sd Td σ
      (enumJob2D σ Td "doc" on "approver"
        (.excl (.direct [("user", BARE, false)]) (.computed "banned"))) := by
  obtain ⟨hWF, hNK, hStrat, hTT, hMatch, hR, hSV⟩ := accepts
  obtain ⟨hCD, hDAB, hCOop, hLU2, hWSbare, _, hBS, hTS, hterm⟩ := fragment
  have hlk : Sd.lookup ("doc", "approver")
      = some (Expr.excl (.direct [("user", BARE, false)]) (.computed "banned")) := rfl
  have hder : isDerived Sd ("doc", "approver") = true := by decide
  have hsettledOps : ∀ r' ∈ computedRefs
      (Expr.excl (.direct [("user", BARE, false)]) (.computed "banned")),
      isDerived Sd ("doc", r') = true →
        SettledKey Sd Td σ "doc" on r' ∧ CompleteKey Sd Td σ "doc" on r' := by
    intro r' hr' hd'
    simp only [computedRefs, List.nil_append,
      List.mem_cons, List.not_mem_nil, or_false] at hr'
    subst hr'
    exact absurd hd' (by decide)
  exact w3dJobCoverage_enumJob2D_state hWF hTT hNK hR hSV hBS hTS hMatch hStrat hterm
    hCD hDAB hWSbare h hlk hder (hCD _ _ _ hlk hder) (hDAB _ _ _ hlk hder) hqo
    (hCOop _ _ _ hlk hder) (hLU2 _ _ _ hlk hder) hsettledOps

/-- `DirectArmsConcrete` at the witness schema — leg 1's fragment clause, which the
    `fragment` bundle above does not carry because nothing before leg 4 consumed it.
    `approver`'s single Direct arm is `[("user", BARE, false)]`: the restriction's
    wildcard flag is `false`, so no `T:*` grant can reach the derived key. -/
theorem directArmsConcrete : DirectArmsConcrete Sd := by
  intro dt R e hlk hder
  have hmem := mem_defs_of_lookup hlk
  simp only [Sd, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hmem
  rcases hmem with ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩
  · exact absurd hder (by decide)
  · decide

/-- **The leg-4 `_d` PROJECTION is jointly dischargeable** — the non-vacuity attack for
    `reachedByW3d2E_toC_d` (2026-08-05). Leg 3 established the discipline and §C.3 of the
    plan generalises it forward: a `_d` packaging is nothing but a chain of `_d`/`_filt`
    forms, so if its hypotheses are jointly unsatisfiable it compiles, audits with
    standard axioms only, and passes every pin in the gate. Leg 4 is a much bigger
    packaging than leg 3, so it gets its own instrument rather than riding leg 3's.

    Every schema/store hypothesis is CLOSED here by `accepts` + `fragment` +
    `directArmsConcrete`; only `h`, the chain membership itself, stays a hypothesis —
    the same residual `correct_applies` and `coverage_applies` carry, and non-vacuity of
    the chain is operational (the Exec driver reaches these states over exactly this
    schema), not proof-side.

    **Contentful, not a relabeling**: the untainted twin `reachedByW3d2E_toC` demands
    `StoreValidRules Sd Td`, which `outside_old_admission` machine-checks is FALSE. The
    old theorem cannot be instantiated at this pair at all; this one can.

    **Controlled 2026-08-05.** Sabotage: one extra unused premise
    `(_hSABOTAGE : StoreValidRules S T)` on BOTH `reachedByW3d2E_toC_d` and
    `graph_correct_w3d2E_d` — false at every store those theorems are about, threaded
    between them and supplied from `hSV` by the two `ComputedOnly` wrappers, so the
    defining module keeps compiling. Observed:

        A. lake build ZanzibarProofs.GraphIndex.CascadeStrataAssemble
           → ✔ [1062/1062] Built … Build completed successfully (1062 jobs).
        B. lake build ZanzibarProofs.FullScope
           → error: … Application type mismatch: The argument
                h
              has type
                ReachedByW3d2E σ Sd Td
              but is expected to have type
                StoreValidRules ?m ?m
              in the application
                reachedByW3d2E_toC_d h
           → error: … Application type mismatch: The argument
                hWF
              has type
                WF Sd
              but is expected to have type
                StoreValidRules ?m ?m
              in the application
                graph_correct_w3d2E_d q hWF

    (A) is the finding, and it is leg 3's finding again one leg further on: **the
    sabotaged theorems are green in their own module**, and would have audited clean and
    passed the identity, statement and definition pins. (B) is these two declarations
    doing the only work in the repo that catches it. One incidental confirmation the
    control also produced: placing the premise BEFORE `h` and leaving it in scope makes
    `induction h` generalise it into the motive, which reddens the module — the honest
    sabotage needed `clear _hSABOTAGE` so the premise really is unused. -/
theorem toC_applies {σ : GraphState} (h : ReachedByW3d2E σ Sd Td) :
    ReachedByW3d2C σ Sd Td := by
  obtain ⟨hWF, hNK, hStrat, hTT, hMatch, hR, hSV⟩ := accepts
  obtain ⟨hCD, hDAB, hCOop, hLU2, hWSbare, _, hBS, hTS, hterm⟩ := fragment
  exact reachedByW3d2E_toC_d h hWF hTT hNK hR hMatch hStrat hCD hDAB directArmsConcrete
    hCOop hLU2 hWSbare hSV hBS hTS hterm

/-- **The leg-4 E-chain FINAL is jointly dischargeable at the Direct-arm pair**:
    `check = sem` at every drained state of the fully-operational two-round scheduler
    chain over `can_view: [user] but not blocked`.

    **Weaker as a STATEMENT, stronger as an INSTRUMENT — say it that way round.** As a
    theorem this is weaker than `correct_applies`: `ReachedByW3d2E` states project INTO
    `ReachedByW3d2C` (that projection is exactly what `toC_applies` says), so assuming
    the operational chain assumes MORE, and this follows from `correct_applies` composed
    with `toC_applies`. What it checks is nonetheless strictly more, which is the point
    of a witness: it discharges the whole leg-4 bundle — including `DirectArmsConcrete`,
    which no earlier witness touches — and it runs the projection rather than starting
    after it.

    (Historical note, superseded by leg 5: this docstring used to end "It does NOT mean
    the headline `graph_correct` covers this store … that rebase is leg 5." The rebase
    has landed — see `final_applies` below.) -/
theorem w3d2E_correct_applies {σ : GraphState} (q : Query)
    (h : ReachedByW3d2E σ Sd Td) (hq : cascadeKeys Sd σ = [])
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem Sd Td q := by
  obtain ⟨hWF, hNK, hStrat, hTT, hMatch, hR, hSV⟩ := accepts
  obtain ⟨hCD, hDAB, hCOop, hLU2, hWSbare, hNoUD, hBS, hTS, hterm⟩ := fragment
  exact graph_correct_w3d2E_d q hWF hTT hNK hR hSV hBS hTS hMatch hStrat hterm hCD hDAB
    directArmsConcrete hCOop hLU2 hWSbare hNoUD h hq hqs hqo

/-! ### Leg 5 — the HEADLINE bundles, inhabited at the Direct-arm pair

Everything above instantiates a `_d` theorem standing BESIDE the headline ones. The
three declarations below are the leg-5 payoff: `GraphAdmission` and `W4Fragment`
themselves — the bundles `graph_correct` / `backend_equivalence` / `exclusion_effective`
/ `no_ghost_grant` / `Exec.graphRun_check_eq_sem` actually take — are inhabited by
`can_view: [user] but not blocked`, so those theorems are no longer vacuous there.
`outside_old_admission` (above, unchanged) is what makes that a widening rather than a
relabeling: the PRE-leg-5 `GraphAdmission.storeValid` was plain `StoreValidRules`, and
it is machine-checked FALSE at `Td`. -/

/-- The leg-5 `GraphAdmission` is inhabited at the Direct-arm pair. Identical to
    `accepts` except that it is the real structure, and it adds `objWild` (`Sd`
    declares no object-wildcard shapes). -/
theorem admission : GraphAdmission Sd Td where
  wf := accepts.1
  nodup := accepts.2.1
  strat := accepts.2.2.1
  ttuDirect := accepts.2.2.2.1
  matchDecl := accepts.2.2.2.2.1
  ranked := accepts.2.2.2.2.2.1
  objWild := by decide
  storeValid := accepts.2.2.2.2.2.2

/-- The leg-5 `W4Fragment` is inhabited at the Direct-arm pair — including
    `directArmsConcrete`, which arrives from its own theorem rather than from the flat
    `fragment` conjunction (that bundle predates any consumer of the clause). -/
theorem w4fragment : W4Fragment Sd Td where
  computedOrDirect := fragment.1
  directArmsBare := fragment.2.1
  directArmsConcrete := directArmsConcrete
  computedOnlyOperands := fragment.2.2.1
  noUnionDirects := fragment.2.2.2.2.2.1
  twoStrata := fragment.2.2.2.1
  wsBare := fragment.2.2.2.2.1
  bareStar := fragment.2.2.2.2.2.2.1
  ttuStarFree := fragment.2.2.2.2.2.2.2.1
  term := fragment.2.2.2.2.2.2.2.2

/-- **★ THE LEG-5 INSTRUMENT: the HEADLINE `graph_correct` applies at
    `can_view: [user] but not blocked`.** Not a `_d` twin — the unsuffixed T2b, with
    both of its real bundles discharged at the canonical Zanzibar boolean shape that
    `FINAL_REVIEW.md` §3.0 has called out as VACUOUS since the claim was first written.

    **Why a witness and not just a green build.** A bundle rebase is exactly the shape a
    green build cannot vet: had the widened `GraphAdmission`/`W4Fragment` turned out
    jointly uninhabitable on Direct-arm stores, `graph_correct` would still compile,
    still audit with standard axioms only, and still pass the identity, statement and
    definition pins — while saying nothing at all. That is not hypothetical; it is the
    2026-07-20b kill, and it is why legs 3 and 4 each landed a witness after their plan
    cells asked for none. `formal/conformance/statement_pin.py` states the same limit
    about itself ("a definition that is vacuous on its own terms … passes this pin with
    its text intact. That remains the job of the non-vacuity witnesses").

    **Sabotage-controlled** (`docs/sabotage-procedure.md`; house rule 2), and the
    sabotage chosen is not an obvious catastrophe but the **plausible half-done leg**:
    widen `W4Fragment` (all five new clauses) but leave `GraphAdmission.storeValid` at
    the narrow `StoreValidRules`, routing `graph_correct` through the conversion lemma
    `storeValidRulesD_of_storeValidRules_directArmsBare` — which typechecks. That state
    looks exactly like a successful widening: `graph_correct`'s statement is
    byte-identical, the definition pin moves (so the gate reports "meaning changed"),
    every audit is standard-axioms-only, and the theorem is still **worth nothing on
    Direct-arm stores**, because `outside_old_admission` refutes `StoreValidRules Sd Td`.

    Observed, 2026-08-05:

        A. lake build (whole library, witness block present)
             → error: FullScope.lean:1114:16: Type mismatch
                 accepts.right.right.right.right.right.right
               has type
                 StoreValidRulesD Sd Td
               but is expected to have type
                 StoreValidRules Sd Td
               — ONE error, at `admission.storeValid`. Nothing else in the tree.
        B. same sabotage, with only the four leg-5 witness declarations below deleted
             → Build completed successfully (1084 jobs).

    (B) is the finding, and it is legs 3 and 4's finding a third time: **the sabotaged
    tree is entirely green** — `graph_correct`, `graph_reached_inv`,
    `Exec.graphRun_check_eq_sem`, every pinned subject — and since both goldens are
    GENERATED from the tree, the leg would have regenerated them to a self-consistent
    pair and passed the whole gate. These four declarations are the only thing in the
    repo that distinguishes "T2b covers the canonical boolean shape" from "T2b is
    silent there".

    ⚠ **T2a is a different story and stays one.** `graph_reached_inv` also takes
    `W4NarrowT2a`, and `outside_narrow_t2a` below machine-checks that `Td` fails it. -/
theorem final_applies {σ : GraphState} (q : Query)
    (h : ReachedBy σ Sd Td) (hq : Drained Sd σ)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem Sd Td q :=
  graph_correct q admission w4fragment h hq hqs hqo

/-- **The T2a asymmetry is machine-checked, not asserted.** `W4NarrowT2a` re-imposes the
    narrow `StoreValidRules`, which `outside_old_admission` refutes at `Td` — so
    `graph_reached_inv` remains VACUOUS on the Direct-arm store that `final_applies`
    above brings into `graph_correct`'s scope.

    This is the arc's expected honest end state (`echain-widening-plan-2026-07-28.md`
    §F: "T2b widened and T2a explicitly not"), and it is a **declared** carry with a
    counterexample attached rather than a silent gap. What is owed before leg 7 is a
    design decision, not proof effort — see `W4NarrowT2a`'s docstring and probe D.3. -/
theorem outside_narrow_t2a : ¬ W4NarrowT2a Sd Td :=
  fun hN => outside_old_admission hN.storeValid

/-! ### Leg 6 — the bundles at the REAL conformance store, not the minimal one

`Td` above is the *minimal* Direct-arm store: one tuple, chosen so
`outside_old_admission` is as sharp as possible. The conformance corpus
`direct_arm_exclusion` (`formal/conformance/corpus.py`) is FOUR tuples — it walks the
whole truth table (alice granted, bob granted-and-banned, carol banned-only, ghost
nothing). `Td4` is that store.

**Why this is not pedantry.** `test_conformance_graph.py::_THEOREM_BACKED` asserts that
a corpus satisfies `GraphAdmission ∧ W4Fragment` **at the store the driver actually
runs**, and both bundles are store-indexed (`storeValid`, `bareStar`, `ttuStarFree`,
`term`'s `NoStoreSubjectR`). A witness at a one-tuple subset would not establish that,
and `test_graph_fragment_scope_classified`'s own docstring records why the distinction
is load-bearing here: *"`direct_arm_exclusion` sat in `GRAPH_FRAGMENT` for six days
under a docstring asserting the exact opposite of what `FullScope.lean` machine-checks
about it."* Reclassifying it on the strength of the minimal witness would be a smaller
version of the same error. -/

/-- The `direct_arm_exclusion` conformance corpus store, verbatim: alice granted
    `approver` through the Direct arm; bob granted AND banned; carol banned only. -/
def Td4 : Store :=
  [⟨⟨"user", "alice", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩,
   ⟨⟨"user", "bob", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩,
   ⟨⟨"user", "bob", BARE⟩, "banned", ⟨"doc", "d1"⟩⟩,
   ⟨⟨"user", "carol", BARE⟩, "banned", ⟨"doc", "d1"⟩⟩]

/-- The corpus store is outside the OLD admission bundle too — same reason as `Td`
    (its `approver` grants take the Direct arm under `excl`, so `exprDirects = []`).
    Kept so the leg-6 reclassification cannot be read as "the corpus was always in
    scope and we mislabelled it": it was genuinely outside, and leg 5 moved it. -/
theorem outside_old_admission4 : ¬ StoreValidRules Sd Td4 := by
  intro h
  obtain ⟨e, rs, hlk, hrs, _⟩ := h ⟨⟨"user", "alice", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩
    (by simp [Td4])
  rw [show Sd.lookup ("doc", "approver")
        = some (Expr.excl (.direct [("user", BARE, false)]) (.computed "banned")) from rfl,
      Option.some.injEq] at hlk
  subst hlk
  simp [exprDirects] at hrs

/-- `GraphAdmission` at the corpus store. The two `approver` tuples take
    `StoreValidRulesD`'s DERIVED disjunct (bare subject, `exprDirectsAll` leaf, bare
    restriction); the two `banned` tuples take the untainted disjunct. -/
theorem admission4 : GraphAdmission Sd Td4 where
  wf := accepts.1
  nodup := accepts.2.1
  strat := accepts.2.2.1
  ttuDirect := accepts.2.2.2.1
  matchDecl := accepts.2.2.2.2.1
  ranked := accepts.2.2.2.2.2.1
  objWild := by decide
  storeValid := by
    intro t ht
    simp only [Td4, List.mem_cons, List.not_mem_nil, or_false] at ht
    rcases ht with rfl | rfl | rfl | rfl
    · exact Or.inr ⟨by decide, rfl,
        .excl (.direct [("user", BARE, false)]) (.computed "banned"),
        [("user", BARE, false)], rfl, by simp [exprDirectsAll], by decide,
        fun r hr => by simp only [List.mem_singleton] at hr; subst hr; rfl⟩
    · exact Or.inr ⟨by decide, rfl,
        .excl (.direct [("user", BARE, false)]) (.computed "banned"),
        [("user", BARE, false)], rfl, by simp [exprDirectsAll], by decide,
        fun r hr => by simp only [List.mem_singleton] at hr; subst hr; rfl⟩
    · exact Or.inl ⟨by decide, .direct [("user", BARE, false)],
        [("user", BARE, false)], rfl, by simp [exprDirects], by decide⟩
    · exact Or.inl ⟨by decide, .direct [("user", BARE, false)],
        [("user", BARE, false)], rfl, by simp [exprDirects], by decide⟩

/-- `W4Fragment` at the corpus store. Every schema-scoped clause is shared with
    `w4fragment`; only the four store-scoped ones (`bareStar`, `ttuStarFree`, and
    `term`'s `NoStoreSubjectR`) are re-discharged at `Td4`. -/
theorem w4fragment4 : W4Fragment Sd Td4 where
  computedOrDirect := fragment.1
  directArmsBare := fragment.2.1
  directArmsConcrete := directArmsConcrete
  computedOnlyOperands := fragment.2.2.1
  noUnionDirects := fragment.2.2.2.2.2.1
  twoStrata := fragment.2.2.2.1
  wsBare := fragment.2.2.2.2.1
  bareStar := by unfold BareStarStore; decide
  ttuStarFree := by
    intro t _ _ a ha tr _
    rw [show schemaRewrites Sd = [] from rfl] at ha
    cases ha
  term := by
    intro dt R hder
    have hkey : (dt, R) = ("doc", "approver") := by
      unfold isDerived at hder
      rw [show taintedKeys Sd = [("doc", "approver")] from by decide] at hder
      simpa using hder
    rw [Prod.mk.injEq] at hkey
    obtain ⟨rfl, rfl⟩ := hkey
    refine ⟨?_, ?_⟩
    · intro r hr tr _
      rw [show schemaRewrites Sd = [] from rfl] at hr
      cases hr
    · intro t ht
      simp only [Td4, List.mem_cons, List.not_mem_nil, or_false] at ht
      rcases ht with rfl | rfl | rfl | rfl <;> decide

/-- **★ THE LEG-6 RECLASSIFICATION LICENCE.** The headline `graph_correct` at the
    schema AND store the `direct_arm_exclusion` conformance driver actually runs. This
    is what `test_conformance_graph.py` moving that corpus from `_DIFFERENTIAL_ONLY`
    into `_THEOREM_BACKED` rests on — the corpus is no longer "an
    implementation-vs-implementation differential with no proved bridge"; a
    `lean-graph != spec` disagreement there would now contradict a machine-checked
    theorem, which is the whole meaning of that classification.

    Note what is still NOT covered, so the reclassification is not over-read:
    `graph_reached_inv` (T2a) — `outside_narrow_t2a` — and the Lean REMOVE gate, whose
    `removeGateB` decides plain `storeValidRulesB`; `direct_arm_exclusion` therefore
    stays in `test_conformance_remove_graph._REMOVE_EXCLUDED`, now for that reason
    alone rather than for the admission reason recorded there before leg 5. -/
theorem final_applies4 {σ : GraphState} (q : Query)
    (h : ReachedBy σ Sd Td4) (hq : Drained Sd σ)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem Sd Td4 q :=
  graph_correct q admission4 w4fragment4 h hq hqs hqo

end W4WitnessDirect
end Zanzibar
