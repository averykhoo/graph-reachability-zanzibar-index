import ZanzibarProofs.Equiv
import ZanzibarProofs.GraphIndex.CascadeStrataAssemble
import ZanzibarProofs.GraphIndex.CascadeStrataEdge

/-!
# W4 — the full-scope restatement (`ReachedBy`, `GraphAdmission`, the final T-theorems)

The W1→W3d-2 arc closed `check = sem` over the fully-operational two-round scheduler
chain (`ReachedByW3d2E`, `CascadeStrataAssemble.lean`). This file is the W4 assembly:

* **`ReachedBy`** — THE operational write-closure, by name. `:= ReachedByW3d2E`
  (logged writes + the state-derived two-round cascade). This is the model of the
  Python write path: `TupleSource` admission → `advance_index` → `DeltaProcessor.
  run_cascade` (`processor.py`, synchronous v1).
* **`GraphAdmission`** — the model-level admission bundle: hypotheses the Python
  compiler/write admission guarantees for EVERY accepted schema and store. Each
  field cites the enforcing mechanism.
* **`W4Fragment`** — the HONEST fragment carries: restrictions the current proof
  needs that Python admission does NOT imply. Each field names the gap (ROADMAP
  "W4 — honest gaps"). The final theorems take BOTH bundles; the claim is never
  rounded up to "everything the Python accepts" (plan §7).
* **`w4_within_scope`** — the bundles imply the spec's decision-15 scope predicate
  `GraphAccepts S` (`State.lean:625`, `SEMANTICS.md` §8): the proved fragment sits
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
    (`connectedstore.advance_index` → `DeltaProcessor.run_cascade`). -/
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
    * `ttuDirect` — `_validate_ttu_tuplesets` (`zanzibar_utils_v1.py:898-935`):
      an untainted TTU tupleset relation must be direct-only.
    * `matchDecl` — compiled `Rule`s route onto declared, untainted families
      (leaf routing splits derived storage onto leaf predicates; `RewriteFilter`
      targets are declared relations).
    * `ranked` — the untainted rewrite graph is acyclic/ranked (the compiler's
      rank assignment; `RulesSaturate.lean`).
    * `objWild` — object-wildcard shapes never target a derived relation
      (`_reject_object_wildcard_scope`, `zanzibar_utils_v1.py:1029-1034`).
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
      (`zanzibar_utils_v1.py:1446-1451`); over untainted ones they are admitted
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
end Zanzibar
