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
      (`TupleSource`/`RuleSet.apply` filter admission). -/
structure GraphAdmission (S : Schema) (T : Store) : Prop where
  wf : WF S
  nodup : NodupKeys S
  strat : Stratifiable S
  ttuDirect : TtuTuplesetsDirect S
  matchDecl : RewriteMatchDeclared S
  ranked : RewriteRanked S
  objWild : ∀ tr ∈ S.objectWildcards, isDerived S tr = false
  storeValid : StoreValidRules S T

/-- **`W4Fragment S T` — the honest fragment carries.** Scope restrictions the
    current proof needs that Python admission does NOT imply (each is a documented
    gap, ROADMAP "W4 — honest gaps at W4 close"):

    * `computedOnly` — derived defs read only computed operands (the compiled
      leaf-split form with `PClosureLeaf`-as-computed-leaf). Python also compiles
      `PDerivedTTU`/`PDerivedUserset` plan leaves — out of scope (W3a decision).
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
    remove legs in `ReachedBy` — not a hypothesis here. -/
structure W4Fragment (S : Schema) (T : Store) : Prop where
  computedOnly : ∀ dt R e, S.lookup (dt, R) = some e →
    isDerived S (dt, R) = true → ComputedOnly e
  twoStrata : ∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true →
    ∀ r' ∈ computedRefs e, isDerived S (dt, r') = true →
      ∀ e', S.lookup (dt, r') = some e' →
        ∀ r'' ∈ computedRefs e', isDerived S (dt, r'') = false
  wsBare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE
  bareStar : BareStarStore T
  ttuStarFree : TtuStarFree S T
  term : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R

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
    contrapositive of this. It is the replacement `w4_within_scope`'s TTU clause will consume
    once `W4Fragment.computedOnly` widens to `ComputedOrDirect` + `hNoUD`, where
    `directsOnly_of_computedOnly` above stops applying (`directsOnly (.direct rs) = true`). -/
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
    (3) a TTU tupleset relation is never derived — a derived def is `ComputedOnly`
    (`computedOnly`), `ComputedOnly` exprs are not directs-only, and `ttuDirect`
    forces declared tupleset defs to be directs-only. The CONVERSE is false:
    `GraphAccepts` admits schemas outside `W4Fragment` (the honest-gaps list); this
    lemma orients the fragment inside the accepted class, it does not claim to cover it. -/
theorem w4_within_scope {S : Schema} {T : Store}
    (hA : GraphAdmission S T) (hF : W4Fragment S T) : GraphAccepts S := by
  refine ⟨hA.objWild, ?_, ?_⟩
  · -- wildcard usersets: `wsBare` says every wildcard restriction is bare
    intro d hd r hr hwild hne
    exact absurd (hF.wsBare (r.1, r.2.1)
      (List.mem_flatMap.mpr ⟨d, hd, List.mem_filterMap.mpr
        ⟨r, hr, by rw [hwild]; rfl⟩⟩)) hne
  · -- derived TTU tuplesets: `ComputedOnly` defs are never directs-only
    intro d hd tt htt
    by_contra hder
    rw [Bool.not_eq_false] at hder
    obtain ⟨e, hlk⟩ := isDerived_declared hder
    have hdo := hA.ttuDirect d hd tt htt ((d.1.1, tt.2), e)
      (mem_defs_of_lookup hlk) rfl
    have hco := hF.computedOnly d.1.1 tt.2 e hlk hder
    rw [directsOnly_of_computedOnly hco] at hdo
    exact absurd hdo (by decide)

/-! ## The final T-theorems -/

/-- **T2b (`graph_correct`), full W4 scope.** At every fully-drained state of the
    operational closure, the graph read computes the stratified-Datalog¬ perfect
    model — for derived AND untainted queries (the statement splits internally).
    Query scope: star subjects are bare (`hqs`), objects concrete (`hqo`).
    This is `graph_correct_w3d2E` with its hypothesis set split by provenance. -/
theorem graph_correct {S : Schema} {T : Store} {σ : GraphState} (q : Query)
    (hA : GraphAdmission S T) (hF : W4Fragment S T)
    (h : ReachedBy σ S T) (hq : Drained S σ)
    (hqs : q.subject.name = STAR → q.subject.predicate = BARE)
    (hqo : q.object.name ≠ STAR) :
    GraphModel.check σ q = sem S T q :=
  graph_correct_w3d2E q hA.wf hA.ttuDirect hA.nodup hA.ranked hA.storeValid
    hF.bareStar hF.ttuStarFree hA.matchDecl hA.strat hF.term
    hF.computedOnly hF.twoStrata hF.wsBare h hq hqs hqo

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
    `ReachedBy`, with the same provenance-split hypothesis bundle as
    `graph_correct`. It is `reachedByW3d2E_inv` with the bundles unpacked. -/
theorem graph_reached_inv {S : Schema} {T : Store} {σ : GraphState}
    (hA : GraphAdmission S T) (hF : W4Fragment S T) (h : ReachedBy σ S T) :
    Inv S σ :=
  reachedByW3d2E_inv h hA.wf hA.ttuDirect hA.nodup hA.ranked hA.matchDecl
    hA.strat hF.computedOnly hF.twoStrata hF.wsBare hA.storeValid hF.bareStar
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

/-- On an untainted schema the fragment bundle collapses to its three contentful
    fields — every derived-scoped carry is vacuous (`isDerived` is constantly
    `false`). -/
theorem w4Fragment_of_untainted {S : Schema} {T : Store} (hUT : UntaintedSchema S)
    (hWS : ∀ sh ∈ wildcardShapes S, sh.2 = BARE)
    (hBS : BareStarStore T) (hTS : TtuStarFree S T) : W4Fragment S T where
  computedOnly := fun dt R _ _ hder => absurd hder (by simp [isDerived_untainted hUT])
  twoStrata := fun dt R _ _ hder => absurd hder (by simp [isDerived_untainted hUT])
  wsBare := hWS
  bareStar := hBS
  ttuStarFree := hTS
  term := fun dt R hder => absurd hder (by simp [isDerived_untainted hUT])

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
    exact ⟨.direct [("user", BARE, false)], [("user", BARE, false)],
      rfl, by simp [exprDirects], by decide⟩

/-- The fragment bundle is inhabited by the witness schema/store. -/
theorem fragment : W4Fragment Sx Tx where
  computedOnly := by
    intro dt R e hlk hder
    have hmem := mem_defs_of_lookup hlk
    simp only [Sx, List.mem_cons, List.not_mem_nil, or_false,
      Prod.mk.injEq] at hmem
    rcases hmem with ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩
    · exact absurd hder (by decide)
    · exact absurd hder (by decide)
    · exact ⟨trivial, trivial⟩
  twoStrata := by
    intro dt R e hlk hder r' hr' hder' e' hlk' r'' hr''
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
  wsBare := by decide
  bareStar := by unfold BareStarStore; decide
  ttuStarFree := by
    intro t _ _ a ha tr _
    rw [show schemaRewrites Sx = [] from rfl] at ha
    cases ha
  term := by
    intro dt R hder
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
    rcases ht with rfl | rfl | rfl
    · exact ⟨.direct [("user", BARE, true)], [("user", BARE, true)],
        rfl, by simp [exprDirects], by decide⟩
    · exact ⟨.direct [("user", BARE, false)], [("user", BARE, false)],
        rfl, by simp [exprDirects], by decide⟩
    · exact ⟨.direct [("user", BARE, false)], [("user", BARE, false)],
        rfl, by simp [exprDirects], by decide⟩

/-- The fragment bundle is inhabited by the union-rooted witness. -/
theorem fragment : W4Fragment Sy Ty where
  computedOnly := by
    intro dt R e hlk hder
    have hmem := mem_defs_of_lookup hlk
    simp only [Sy, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at hmem
    rcases hmem with ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩ |
      ⟨⟨rfl, rfl⟩, rfl⟩ | ⟨⟨rfl, rfl⟩, rfl⟩
    · exact absurd hder (by decide)                    -- base (untainted)
    · exact absurd hder (by decide)                    -- blocked (untainted)
    · exact ⟨trivial, trivial⟩                          -- viewer := excl (computed) (computed)
    · exact absurd hder (by decide)                    -- admin (untainted)
    · exact ⟨trivial, trivial⟩                          -- approver := union (computed) (computed)
  twoStrata := by
    intro dt R e hlk hder r' hr' hder' e' hlk' r'' hr''
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
  wsBare := by decide
  bareStar := by unfold BareStarStore; decide
  ttuStarFree := by
    intro t _ _ a ha tr _
    rw [show schemaRewrites Sy = [] from by decide] at ha
    cases ha
  term := by
    intro dt R hder
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

This is the leg-5d fragment's motivating shape, and it sits OUTSIDE the final
theorems' current scope on TWO counts (the honest record, 2026-07-20e):

* `W4Fragment.computedOnly` rejects the `direct` leaf in the derived def; the
  final `graph_correct`/`graph_reached_inv` are E-chain theorems
  (`graph_correct_w3d2E`), still `ComputedOnly`-scoped — widening them needs the
  operational enumeration model change (`enumJob2` → `enumJob2D`) plus a `_d`
  projection of `reachedByW3d2E_toC` (recorded follow-up, NOT done).
* `GraphAdmission.storeValid` (plain `StoreValidRules`) is FALSE at `Td`: the
  Direct arm sits under `excl`, so `exprDirects = []` on the derived def and a
  stored Direct-arm grant is only admissible under the WIDENED
  `StoreValidRulesD` (leg 5a) — `Td` is machine-checked to be genuinely outside
  the old bundle (`outside_old_admission` below).

What IS proved at this scope is the C-chain T2b **`graph_correct_w3d2_d`**
(`CascadeStrataResettle.lean`, audited): `check = sem` at every fully-drained
`ReachedByW3d2C` state on the Direct-arm fragment. The theorems below inhabit
its FULL hypothesis bundle at `Sd`/`Td` — `accepts` (the admission side, with
`StoreValidRulesD` in place of `storeValid`), `fragment` (the `_d` fragment
carries: `ComputedOrDirect` + `DirectArmsBare` + operand-`ComputedOnly` +
`hLU2` + `hWSbare` + `hNoUD` + the store disciplines), and `correct_applies`
(the bundle is JOINTLY dischargeable: `graph_correct_w3d2_d` instantiates at
the witness pair with every schema/store hypothesis closed). Non-vacuity of the
chain itself is operational: the Exec driver reaches drained `ReachedByW3d2C`
states over exactly this schema (attack-run 2026-07-20e: the 4-tuple corpus
store drains with `check = sem` on the full truth table). -/

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

    Scope, stated rather than implied: `hsettledOps` is DISCHARGED here (vacuously —
    `approver`'s only computed ref is `banned`, which is untainted), so this witness
    exercises the packaging, not the operand-settled path; the same vacuity is already
    recorded for `fragment`'s operand-`ComputedOnly` clause. `h` stays a hypothesis, the
    identical residual `correct_applies` carries: non-vacuity of the CHAIN is
    operational (the Exec driver reaches these states over exactly this schema), not
    proof-side. -/
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

end W4WitnessDirect
end Zanzibar
