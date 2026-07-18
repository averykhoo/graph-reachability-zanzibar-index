import ZanzibarProofs.GraphIndex.RemoveOccCount

/-!
# The remove-then-drain confluence — the UNTAINTED arm (W3d remove-leg R4, part 1)

**What this file proves (this increment).** The UNTAINTED half of the R4 confluence: after
the logged rule-routed retraction `removeLoggedRules S t` (then a drain), the multiplicity of
an UNTAINTED direct edge `(a,b)` is exactly its occurrence count over the SMALLER store
`T.erase t` — the same value R3 (`reachedByW3d2E_untOccCount`) gives for a fresh add-only
rebuild over `T.erase t`. So an untainted edge's presence after remove-drain matches the
rebuild's, at multiset (hence membership) level.

The confluence claim was attack-first CONFIRMED (house rule 2; `#eval` vs the real
`check`/`sem`, scratch deleted): over `viewer := editor or manager` (rc≥2 untainted survival)
+ `r := a but not b` (derived exclusion), removing each of five tuples then draining gives
`check (drain (removeLoggedRules σ t)) q = sem S (T.erase t) q` across the whole query grid —
NO mismatch, including the rc=2 survival case (`(alice,editor)`/`(alice,manager)` both granted,
removing one leaves the viewer edge) and the derived-exclusion flips.

**This is ADDITIVE** (a new file + a one-line aggregator import; no constructor / existing def
touched). The `remove` constructor on `ReachedByW3d2E` is the final leg R5, armed with the full
confluence (untainted arm here + the derived membership arm to follow).

## The key facts
* `count_removeLoggedOne` / `count_removeLoggedRules` — the retraction's count-SHRINK law: the
  exact dual of R3's `count_foldl_writeDirect` / `count_writeLoggedRules`. Holds
  UNCONDITIONALLY (Nat subtraction floors: an absent closure edge's `removeLoggedOne` is a
  no-op and `0 - 1 = 0` in `Nat`, so no "enough copies present" guard is needed for the
  arithmetic — R3's invariant supplies the ≥ that makes the floor exact at the confluence).
* `untOccCount_erase` — the store-erase split of the occurrence count: for `t ∈ T`,
  `untOccCount S T = untOccCount S (T.erase t) + (t's closure occurrences)`.
* `removeLoggedRules_untOccCount` — the pre-drain untainted confluence (combine the two).
* `cascadeLeg_removeLoggedRules_untOccCount` — the drained form (the two-round drain is
  untainted-count-inert, R3's `count_runCascade2_of_ne` + `enumJobs2At_Rnode_ne`).
-/

namespace Zanzibar

open scoped List

/-! ## The retraction's count-shrink law -/

/-- One logged retraction's effect on `count p`: it decrements by one iff `u`'s materialized
    edge IS `p` (Nat subtraction floors the absent case). The exact dual of `writeLoggedOne`'s
    `+1` (`count_foldl_writeDirect`'s per-step growth). -/
theorem count_removeLoggedOne (u : Tuple) (p : NodeKey × NodeKey) (σ : GraphState) :
    (σ.removeLoggedOne u).edges.count p
      = σ.edges.count p - (if edgeOfTuple u = p then 1 else 0) := by
  unfold GraphState.removeLoggedOne edgeOfTuple
  by_cases hmem : (subjNode u.subject, objNode u.object u.relation) ∈ σ.edges
  · rw [if_pos hmem, pushDelta_edges, removeEdgeOne_edges]
    by_cases hp : (subjNode u.subject, objNode u.object u.relation) = p
    · rw [if_pos hp]; subst hp; exact List.count_erase_self
    · rw [if_neg hp, Nat.sub_zero]
      exact List.count_erase_of_ne (fun h => hp h.symm)
  · rw [if_neg hmem]
    by_cases hp : (subjNode u.subject, objNode u.object u.relation) = p
    · rw [if_pos hp]; subst hp
      have hz : σ.edges.count (subjNode u.subject, objNode u.object u.relation) = 0 :=
        List.count_eq_zero.mpr hmem
      omega
    · rw [if_neg hp, Nat.sub_zero]

/-- The logged rule-routed retraction's count-shrink law: `count p` drops by the number of
    closure members whose materialized edge is `p` — the exact dual of R3's
    `count_writeLoggedRules`. UNCONDITIONAL (Nat subtraction). -/
theorem count_removeLoggedRules (p : NodeKey × NodeKey) (S : Schema) (t : Tuple) :
    ∀ (σ : GraphState),
      (σ.removeLoggedRules S t).edges.count p
        = σ.edges.count p - ((rewriteClosure S t).map edgeOfTuple).count p := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosure S t = us
  induction us with
  | nil => intro σ; simp
  | cons u rest ih =>
    intro σ
    simp only [List.foldl_cons]
    rw [ih (σ.removeLoggedOne u), count_removeLoggedOne u p σ, List.map_cons]
    by_cases hp : edgeOfTuple u = p
    · subst hp
      rw [if_pos rfl, List.count_cons_self]
      omega
    · rw [if_neg hp, List.count_cons_of_ne hp]
      omega

/-! ## The store-erase split of the occurrence count -/

/-- Erasing a stored tuple `t ∈ T` splits the occurrence count: the total over `T` is the
    total over `T.erase t` plus `t`'s own closure occurrences. `List.erase` drops the FIRST
    copy, and `List.count` is permutation-invariant, so this holds even if `t` recurs in `T`
    (a store multiset). The store-side identity R4's confluence needs to match the smaller
    rebuild. -/
theorem untOccCount_erase (S : Schema) (T : Store) (t : Tuple) (a b : NodeKey) (ht : t ∈ T) :
    untOccCount S T a b
      = untOccCount S (T.erase t) a b
        + ((rewriteClosure S t).map edgeOfTuple).count (a, b) := by
  unfold untOccCount
  have hperm : T ~ t :: T.erase t := List.perm_cons_erase ht
  have h1 := ((hperm.flatMap_right (rewriteClosure S)).map edgeOfTuple).count_eq (a, b)
  rw [h1, List.flatMap_cons, List.map_append, List.count_append]
  omega

/-! ## The untainted confluence — pre-drain and drained -/

/-- **The pre-drain untainted confluence.** After the logged retraction of a stored `t`, an
    UNTAINTED edge `(a,b)`'s multiplicity is exactly its occurrence count over `T.erase t`
    (R3's `untOccCount`) — the same value R3 gives for a fresh add-only rebuild over
    `T.erase t`. Combine the count-shrink law with R3's invariant and the store-erase split;
    R3 supplies the `≥` that makes the Nat subtraction exact. -/
theorem removeLoggedRules_untOccCount {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T) (t : Tuple) (ht : t ∈ T) (a b : NodeKey)
    (hb : isDerived S (b.type, b.pred) = false) :
    (σ.removeLoggedRules S t).edges.count (a, b) = untOccCount S (T.erase t) a b := by
  rw [count_removeLoggedRules (a, b) S t σ, reachedByW3d2E_untOccCount h a b hb,
    untOccCount_erase S T t a b ht]
  omega

/-- **The drained untainted confluence.** Draining after the retraction (the R5 `remove`
    constructor's target state) leaves the untainted count untouched — the two-round diffing
    cascade only ever writes/removes edges into DERIVED R-nodes (R3's `count_runCascade2_of_ne`
    + `enumJobs2At_Rnode_ne`). So the drained post-remove untainted multiplicity is
    `untOccCount S (T.erase t)` — bit-identical to R3 on a fresh rebuild over `T.erase t`,
    hence membership matches (`count > 0 ↔ mem`). -/
theorem drain_removeLoggedRules_untOccCount {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T) (t : Tuple) (ht : t ∈ T) (a b : NodeKey)
    (hb : isDerived S (b.type, b.pred) = false) :
    (runCascade2 S (T.erase t) (σ.removeLoggedRules S t)
        (enumJobs2R1 S (σ.removeLoggedRules S t))
        (enumJobs2R2 S (T.erase t) (σ.removeLoggedRules S t))).edges.count (a, b)
      = untOccCount S (T.erase t) a b := by
  have hkfacts : ∀ (σe : GraphState) (n : Nat),
      ∀ k ∈ cascadeKeysAbove S σe n, isDerived S (k.1, k.2.1) = true ∧ k.2.2 ≠ STAR :=
    fun σe n k hk => ⟨(mem_cascadeKeysAbove_props hk).1, (mem_cascadeKeysAbove_props hk).2.2⟩
  have h1 : ∀ j ∈ enumJobs2R1 S (σ.removeLoggedRules S t),
      b ≠ objNode ⟨j.dt, j.on⟩ j.R := enumJobs2At_Rnode_ne (hkfacts _ _) hb
  have h2 : ∀ j ∈ enumJobs2R2 S (T.erase t) (σ.removeLoggedRules S t),
      b ≠ objNode ⟨j.dt, j.on⟩ j.R := enumJobs2At_Rnode_ne (hkfacts _ _) hb
  rw [count_runCascade2_of_ne S (T.erase t) (σ.removeLoggedRules S t) _ _ h1 h2]
  exact removeLoggedRules_untOccCount h t ht a b hb

/-- **The untainted membership confluence** (`count > 0 ↔ mem`). An untainted edge `(a,b)`
    survives the remove-then-drain iff it still has a positive occurrence count over
    `T.erase t` — i.e. iff at least one SURVIVING stored write still derives it. This is the
    membership-level statement R5's read-transport consumes on the untainted side: it is
    exactly the presence R3 (`reachedByW3d2E_untOccCount` + `List.count_pos_iff`) would report
    for a fresh add-only rebuild over `T.erase t`. -/
theorem mem_drain_removeLoggedRules_untainted {σ : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T) (t : Tuple) (ht : t ∈ T) (a b : NodeKey)
    (hb : isDerived S (b.type, b.pred) = false) :
    (a, b) ∈ (runCascade2 S (T.erase t) (σ.removeLoggedRules S t)
        (enumJobs2R1 S (σ.removeLoggedRules S t))
        (enumJobs2R2 S (T.erase t) (σ.removeLoggedRules S t))).edges
      ↔ 0 < untOccCount S (T.erase t) a b := by
  rw [← drain_removeLoggedRules_untOccCount h t ht a b hb, Nat.pos_iff_ne_zero, ne_eq,
    List.count_eq_zero, not_not]

/-! ## `ReadEq` — the MEMBERSHIP-level read-agreement relation (R4 part 2, deliverable iii)

**Why a new relation.** `EvalEq` (`Cascade.lean:170`) equates edges by LIST equality
(`σ'.edges = σ.edges`). That is TOO STRONG for the remove confluence: the add-only rebuild
over `T.erase t` and the remove-then-drain fold produce the SAME edge SET but in different
MULTIPLICITIES and orders — the model stacks derived duplicates across passes (the R3 KILL,
`RemoveOccCount.lean`; compensated by the filter-all `removeEdgePair`), and the untainted
occurrence count is a permutation-order artifact of the fold — so the two `edges` LISTS are
never equal. `ReadEq` weakens exactly the edge clause to edge-SET MEMBERSHIP, which is all any
READ consults:

* `reachB` (`State.lean:139`) queries the edge list ONLY through `List.any` — a membership
  test, blind to order and multiplicity (`any_congr_of_mem` below). So `reach` — and hence
  `probeNonDerived` and the bare-subject arm of `probeDerived` — is edge-SET congruent.
* `probeDerived`/`probeNonDerived` otherwise read `residue` and `schema`, equated directly.

So `ReadEq` is congruent for the ENTIRE read surface (`reachB`/`reach`/`probeNonDerived`/
`probeDerived`/`check`) yet is SATISFIABLE across the differing fold orders — the projection
R5 transports `check`/`reachB` through. It is strictly weaker than `EvalEq` (`EvalEq.toReadEq`).

**Scope of what part 2 lands (honest).** The UNTAINTED half of the `edgeMem` clause between the
drained-remove state and any rebuild over `T.erase t` is proved here
(`untEdgeMem_drain_removeLoggedRules_rebuild`, off R3 + the untainted arm). The DERIVED half of
`edgeMem` and the `residue` clause are CHAIN-BOUND: the drained-remove state's derived edges +
residue equal `sem S (T.erase t)` only via the settledness machinery
(`reachedByW3d2C_settled` / `settledComplete_cascade2_targeted` /`graph_correct_w3d2`), every
route of which requires a `ReachedByW3d2`/`ReachedByW3d2C` witness for the state — and NO
add-only rebuild term exists to supply one additively. They close in R5, where the `remove`
constructor makes the drained state a `ReachedByW3d2E` and `graph_correct_w3d2E` characterises
its derived edges + residue by `sem S (T.erase t)` in one shot (see the R4-part-2 finding in
`history/optional-widening-2026-07.md`). This file therefore delivers the reusable `ReadEq`
relation + full read-congruence (the transport vehicle) + the untainted membership arm; the
derived/residue arms are R5's, discharged there against the constructor, not faked here. -/

/-- Membership-level read agreement: schema/nodes/residue equal, and the edge SETS coincide
    (`∈`-equivalence, NOT list equality). The faithful projection for the remove confluence
    (differing add-chain vs remove+drain fold orders give equal edge SETS, unequal lists). -/
structure ReadEq (σ' σ : GraphState) : Prop where
  schema : σ'.schema = σ.schema
  nodes : σ'.nodes = σ.nodes
  residue : σ'.residue = σ.residue
  edgeMem : ∀ e, e ∈ σ'.edges ↔ e ∈ σ.edges

theorem ReadEq.refl (σ : GraphState) : ReadEq σ σ := ⟨rfl, rfl, rfl, fun _ => Iff.rfl⟩

theorem ReadEq.symm {σ' σ : GraphState} (h : ReadEq σ' σ) : ReadEq σ σ' :=
  ⟨h.schema.symm, h.nodes.symm, h.residue.symm, fun e => (h.edgeMem e).symm⟩

theorem ReadEq.trans {σ₁ σ₂ σ₃ : GraphState} (h₁ : ReadEq σ₁ σ₂) (h₂ : ReadEq σ₂ σ₃) :
    ReadEq σ₁ σ₃ :=
  ⟨h₁.schema.trans h₂.schema, h₁.nodes.trans h₂.nodes, h₁.residue.trans h₂.residue,
   fun e => (h₁.edgeMem e).trans (h₂.edgeMem e)⟩

/-- `EvalEq` (LIST-equal edges) is strictly stronger than `ReadEq` (edge-SET-equal). Lets any
    existing `EvalEq` fact feed a `ReadEq` transport. -/
theorem EvalEq.toReadEq {σ' σ : GraphState} (h : EvalEq σ' σ) : ReadEq σ' σ :=
  ⟨h.schema, h.nodes, h.residue, fun e => by rw [h.edges]⟩

/-! ### The read-congruence suite -/

/-- **`List.any` is blind to order and multiplicity.** Two lists with the SAME membership have
    equal `.any p`. The base fact behind `reachB`'s edge-SET (not edge-LIST) congruence — the
    reason `ReadEq` suffices for the whole read surface. -/
theorem any_congr_of_mem {α : Type _} (p : α → Bool) {l l' : List α}
    (h : ∀ x, x ∈ l ↔ x ∈ l') : l.any p = l'.any p := by
  have key : l.any p = true ↔ l'.any p = true := by
    simp only [List.any_eq_true]
    exact ⟨fun ⟨x, hx, hpx⟩ => ⟨x, (h x).mp hx, hpx⟩,
           fun ⟨x, hx, hpx⟩ => ⟨x, (h x).mpr hx, hpx⟩⟩
  cases hl : l.any p <;> cases hl' : l'.any p <;> simp_all

/-- **`reachB` is edge-SET congruent.** Fuel-bounded reachability queries the edges only via
    `List.any`, so equal edge SETS (membership) give equal `reachB` at every fuel — no LIST
    equality needed. Fuel induction; the recursive predicate is aligned by the IH. -/
theorem reachB_congr_of_mem {es es' : List (NodeKey × NodeKey)}
    (h : ∀ e, e ∈ es ↔ e ∈ es') :
    ∀ (fuel : Nat) (u v : NodeKey), reachB es fuel u v = reachB es' fuel u v := by
  intro fuel
  induction fuel with
  | zero => intro u v; rfl
  | succ n ih =>
    intro u v
    show es.any (fun e => e.1 == u && (e.2 == v || reachB es n e.2 v))
       = es'.any (fun e => e.1 == u && (e.2 == v || reachB es' n e.2 v))
    have hp : (fun e : NodeKey × NodeKey => e.1 == u && (e.2 == v || reachB es n e.2 v))
            = (fun e : NodeKey × NodeKey => e.1 == u && (e.2 == v || reachB es' n e.2 v)) := by
      funext e; rw [ih e.2 v]
    rw [hp]
    exact any_congr_of_mem _ h

/-- `reach` (the read probe, fuel `nodes.length + 1`) agrees across `ReadEq` states. -/
theorem reach_readEq {σ' σ : GraphState} (h : ReadEq σ' σ) (u v : NodeKey) :
    σ'.reach u v = σ.reach u v := by
  unfold GraphState.reach
  rw [h.nodes]
  exact reachB_congr_of_mem h.edgeMem _ u v

/-- `reachB` over the two states' edges (at the shared `ReadEq` fuel) agrees — the explicit
    `reachB` congruence R5 transports through. -/
theorem reachB_readEq {σ' σ : GraphState} (h : ReadEq σ' σ) (u v : NodeKey) :
    reachB σ'.edges (σ'.nodes.length + 1) u v = reachB σ.edges (σ.nodes.length + 1) u v :=
  reach_readEq h u v

/-- The non-derived ≤4-probe read agrees across `ReadEq` states (edge-SET congruence of
    `reach`). -/
theorem probeNonDerived_readEq {σ' σ : GraphState} (h : ReadEq σ' σ) (q : Query) :
    GraphModel.probeNonDerived σ' q = GraphModel.probeNonDerived σ q := by
  unfold GraphModel.probeNonDerived
  simp only [reach_readEq h]

/-- The derived residue-path read agrees across `ReadEq` states (residue equal + `reach`
    edge-SET congruent for the bare-subject edge probe). -/
theorem probeDerived_readEq {σ' σ : GraphState} (h : ReadEq σ' σ) (q : Query) :
    GraphModel.probeDerived σ' q = GraphModel.probeDerived σ q := by
  unfold GraphModel.probeDerived
  simp only [reach_readEq h, h.residue]

/-- **The `check` read agrees across `ReadEq` states** — the headline congruence: schema
    equal (dispatch), then `probeDerived`/`probeNonDerived` congruent. This is what R5 uses to
    transport `check(post-remove) = sem` through a `ReadEq` to a rebuild. -/
theorem check_readEq {σ' σ : GraphState} (h : ReadEq σ' σ) (q : Query) :
    GraphModel.check σ' q = GraphModel.check σ q := by
  unfold GraphModel.check
  rw [h.schema]
  split
  · exact probeDerived_readEq h q
  · exact probeNonDerived_readEq h q

/-! ## The untainted edge-SET membership arm of the confluence -/

/-- **The untainted `edgeMem` arm.** For ANY add-only rebuild `σr` over the smaller store
    `T.erase t`, the drained post-remove state and `σr` AGREE on the membership of every
    UNTAINTED edge `(a,b)` — both hold it iff `0 < untOccCount S (T.erase t) a b` (R3
    `reachedByW3d2E_untOccCount` for `σr`; the untainted arm
    `mem_drain_removeLoggedRules_untainted` for the drained remove). This is the UNTAINTED half
    of the `ReadEq.edgeMem` clause between the two states. The DERIVED half + the `residue`
    clause are chain-bound (they equal `sem S (T.erase t)` only via the settledness machinery
    over a `ReachedByW3d2C` witness the drained state lacks additively) and close in R5 against
    the `remove` constructor. -/
theorem untEdgeMem_drain_removeLoggedRules_rebuild {σ σr : GraphState} {S : Schema} {T : Store}
    (h : ReachedByW3d2E σ S T) (t : Tuple) (ht : t ∈ T)
    (hr : ReachedByW3d2E σr S (T.erase t)) (a b : NodeKey)
    (hb : isDerived S (b.type, b.pred) = false) :
    (a, b) ∈ (runCascade2 S (T.erase t) (σ.removeLoggedRules S t)
        (enumJobs2R1 S (σ.removeLoggedRules S t))
        (enumJobs2R2 S (T.erase t) (σ.removeLoggedRules S t))).edges
      ↔ (a, b) ∈ σr.edges := by
  rw [mem_drain_removeLoggedRules_untainted h t ht a b hb,
    ← reachedByW3d2E_untOccCount hr a b hb, List.count_pos_iff]

/-! ## The retraction is residue-inert and edge-shrinking — the T2a Group-A remove-case
substrate (R5 pre-discharge)

The logged rule-routed retraction `removeLoggedRules` touches ONLY the edge multiset (via
`removeEdgeOne`) and the outbox (via `pushDelta`); it never writes a `residue` row. So the
STRUCTURAL invariant clauses that read only `residue` (`ResidueHygienic`, `ResidueDeclared`)
transport verbatim across a retraction, and any "no edge here" clause (`EdgeHyg1`, once in
scope) transports because the edge SET only shrinks. Together with the already-landed
`structInv_removeLoggedRules` (`CascadeInv.lean`, R2) these are exactly the discharges the
R5 `remove` constructor's Group-A cases will consume — proved here additively, ahead of the
constructor, so they carry no chain hypotheses. (`EdgeHyg1` lives downstream in
`CascadeStrataEdge.lean`; its remove case is `mem_removeLoggedRules_edges` + the residue-eq
below, placed with the constructor.) -/

/-- One logged retraction leaves the residue map untouched (`removeEdgeOne`/`pushDelta` are
    both residue-inert). -/
@[simp] theorem removeLoggedOne_residue (σ : GraphState) (t : Tuple) :
    (σ.removeLoggedOne t).residue = σ.residue := by
  unfold GraphState.removeLoggedOne
  by_cases hmem : (subjNode t.subject, objNode t.object t.relation) ∈ σ.edges
  · rw [if_pos hmem, pushDelta_residue, removeEdgeOne_residue]
  · rw [if_neg hmem]

/-- The logged rule-routed retraction leaves the residue map untouched (fold of the above). -/
theorem removeLoggedRules_residue (σ : GraphState) (S : Schema) (t : Tuple) :
    (σ.removeLoggedRules S t).residue = σ.residue := by
  unfold GraphState.removeLoggedRules
  generalize rewriteClosure S t = us
  induction us generalizing σ with
  | nil => rfl
  | cons u rest ih =>
    simp only [List.foldl_cons]
    rw [ih (σ.removeLoggedOne u), removeLoggedOne_residue]

/-- The retraction only SHRINKS the edge multiset: any surviving edge was already present.
    (Off the R4 count-shrink law `count_removeLoggedRules` — a present edge has positive
    count, which the retraction can only lower, so it was positive, hence present, in `σ`.) -/
theorem mem_removeLoggedRules_edges {σ : GraphState} {S : Schema} {t : Tuple}
    {e : NodeKey × NodeKey} (h : e ∈ (σ.removeLoggedRules S t).edges) : e ∈ σ.edges := by
  rw [← List.count_pos_iff] at h ⊢
  rw [count_removeLoggedRules e S t σ] at h
  omega

/-- **`ResidueHygienic` survives a retraction** (both clauses read only `residue`, which is
    inert). The R5 `reachedByW3d2E_residueHygienic` remove-case discharge. -/
theorem residueHygienic_removeLoggedRules {σ : GraphState} (S : Schema) (t : Tuple)
    (h : ResidueHygienic σ) : ResidueHygienic (σ.removeLoggedRules S t) := by
  obtain ⟨h1, h2⟩ := h
  refine ⟨fun k r res hrow n hn => ?_, fun k r res hrow n hn => ?_⟩
  · rw [removeLoggedRules_residue] at hrow; exact h1 k r res hrow n hn
  · rw [removeLoggedRules_residue] at hrow; exact h2 k r res hrow n hn

/-- **`ResidueDeclared` survives a retraction** (reads only `residue`). The R5
    `reachedByW3d2E_residueDeclared` remove-case discharge. -/
theorem residueDeclared_removeLoggedRules {σ : GraphState} (S : Schema) (t : Tuple)
    (h : ResidueDeclared S σ) : ResidueDeclared S (σ.removeLoggedRules S t) := by
  intro k r res hrow
  rw [removeLoggedRules_residue] at hrow
  exact h k r res hrow

/-! ## R5a — build-FROM-store rebuild-existence (the sub-store admitted rebuild)

The `remove` constructor (leg R5b) removes a tuple `t ∈ T` from the store, landing over
`T.erase t`. BOTH discharge routes traced in `history/PROOF_STATUS.md` (2026-07-19c) converge
on a build-FROM-store admitted witness over the SMALLER store — route (a)'s
`reachedByW3d2_shadow` remove case needs `∃ σ0, ReachedByRulesAdmitted σ0 S (T.erase t)`,
route (b)'s `ReadEq` transport needs a drained `ReachedByW3d2E` rebuild over `T.erase t`, whose
untainted-core shadow is again this admitted term. The tree lacked it: every existing
`∃ …, ReachedByRulesAdmitted …` is a shadow-FROM-an-existing-chain (`reachedByW3d2_shadow`),
never a build-FROM-store.

We build it as the **store-restriction dual of `exists_admitted_restrict`** (`RestrictBase.lean`,
which restricts the SCHEMA). The one new ingredient the recon flagged — closure-acyclicity of the
admission target over the smaller store — is obtained NOT from scratch but by INHERITANCE from an
already-admitted larger store: its complete edge relation `σ0.edges` is acyclic (`Inv.acyclic`)
and already contains every materialised closure edge of every sub-store
(`reachedByRulesAdmitted_edge_complete`); a subgraph of an acyclic graph is acyclic, so
`foldAdmits_of_acyclic` (`RestrictBase.lean:392`) discharges every `writeDirect` fold over the
sub-store against `Ef := σ0.edges`. This is exactly what R5b has in hand — it removes from a store
already carrying an admitted chain.

**★ Attack-first (house rule 2) — a SCOPING KILL of the more-general statement, not of this
lemma.** Rebuild-existence over an ARBITRARY store is FALSE, even under `RewriteRanked`. Witness:
the userset 2-cycle store `{⟨group:g1#member, member, group:g2⟩, ⟨group:g2#member, member,
group:g1⟩}`. It uses NO rewrite rules (so `RewriteRanked` holds vacuously), yet its two
materialised closure edges are `objNode(g1,member) → objNode(g2,member)` and
`objNode(g2,member) → objNode(g1,member)` (a userset subject `o#r` materialises at `objNode o r`),
forming a 2-cycle. `admitEdge` (`State.lean`, `a ≠ b ∧ ¬reach b a`) REJECTS the second write once
the first edge is present (`reach (objNode g1 member) (objNode g2 member) = true`), so no
`FoldAdmits` and no `ReachedByRulesAdmitted` chain exists over this store — the Python graph index
rolls the cyclic write back identically. So from-scratch admissibility is NOT free; it is free ONLY
over a SUB-store of an admitted store (a subgraph of an acyclic graph), which is the only shape R5b
consumes. Hence the statement is honestly premised on `ReachedByRulesAdmitted σ0 S T`, never
free-standing. This SHAPES R5b: the erased store's admissibility must be derived FROM the
pre-remove store's (as `exists_admitted_erase` does), not asserted. -/

/-- **The from-store admitted-rebuild core.** Given a FIXED acyclic target relation `Ef`
    already containing every materialised closure edge of every tuple of a store `T'`, fold an
    admitted rule-routed chain over `T'`: each write's fold admits by `foldAdmits_of_acyclic`
    (target `Ef`, `σp.edges ⊆ Ef` recovered from `reachedByRules_edge_sound`), and the built
    edges stay inside `Ef`. The store-analog of the write-path induction inside
    `exists_admitted_restrict`, with the acyclic target supplied rather than reconstructed. -/
theorem exists_admitted_ofAcyclicTarget {S : Schema} {Ef : List (NodeKey × NodeKey)}
    (hacyc : ∀ v, ¬ NReaches Ef v v) :
    ∀ T' : Store,
      (∀ t' ∈ T', ∀ u ∈ rewriteClosure S t',
        (subjNode u.subject, objNode u.object u.relation) ∈ Ef) →
      ∃ σ0', ReachedByRulesAdmitted σ0' S T' ∧ (∀ e ∈ σ0'.edges, e ∈ Ef) := by
  intro T'
  induction T' with
  | nil =>
    intro _
    exact ⟨emptyState S, ReachedByRulesAdmitted.empty S,
      by intro e he; simp [emptyState] at he⟩
  | cons t' T'' ih =>
    intro hmatAll
    obtain ⟨σp, hp, hsubp⟩ := ih (fun t'' ht'' u hu =>
      hmatAll t'' (List.mem_cons_of_mem _ ht'') u hu)
    have hSI : StructInv S σp :=
      (reachedByRules_inv (reachedByRules_of_admitted hp)).1.toStruct
    have hmat : ∀ u ∈ rewriteClosure S t',
        (subjNode u.subject, objNode u.object u.relation) ∈ Ef :=
      fun u hu => hmatAll t' List.mem_cons_self u hu
    have hFA : FoldAdmits σp (rewriteClosure S t') :=
      foldAdmits_of_acyclic hacyc (rewriteClosure S t') hSI hsubp hmat
    refine ⟨σp.writeRules S t', ReachedByRulesAdmitted.step t' hp hFA, ?_⟩
    -- every edge of the new state materialises a closure tuple of `t' :: T''`, all in `Ef`
    rintro ⟨a, b⟩ hab
    obtain ⟨t'', ht'', u, hu, h1, h2⟩ :=
      reachedByRules_edge_sound
        (reachedByRules_of_admitted (ReachedByRulesAdmitted.step t' hp hFA)) a b hab
    rw [h1, h2]
    exact hmatAll t'' ht'' u hu

/-- **Rebuild-existence over a SUBSET store.** From an admitted chain over `T`, any store `T'`
    whose tuples all lie in `T` admits its own rule-routed chain, with edges inside `σ0`'s.
    Acyclicity is inherited from `σ0` (`Inv.acyclic`); completeness of the target from
    `reachedByRulesAdmitted_edge_complete`. Route-agnostic (stated over ⊆, not just `erase`). -/
theorem exists_admitted_ofSubset {S : Schema} {T T' : Store} {σ0 : GraphState}
    (h0 : ReachedByRulesAdmitted σ0 S T) (hsub : T' ⊆ T) :
    ∃ σ0', ReachedByRulesAdmitted σ0' S T' ∧ (∀ e ∈ σ0'.edges, e ∈ σ0.edges) := by
  refine exists_admitted_ofAcyclicTarget
    ((reachedByRules_inv (reachedByRules_of_admitted h0)).1.acyclic) T' ?_
  intro t' ht' u hu
  exact reachedByRulesAdmitted_edge_complete h0 t' (hsub ht') u hu

/-- **Rebuild-existence over `T.erase t` — the R5b tool.** The specific instance route (a)'s
    `reachedByW3d2_shadow` remove case consumes: erasing one occurrence yields a subset store
    (`List.erase_subset`), so an admitted rebuild exists over it, with edges ⊆ `σ0`'s. R5b will
    match this rebuild against the actual retraction state via the R4 confluence (`ReadEq`). -/
theorem exists_admitted_erase {S : Schema} {T : Store} {σ0 : GraphState}
    (h0 : ReachedByRulesAdmitted σ0 S T) (t : Tuple) :
    ∃ σ0', ReachedByRulesAdmitted σ0' S (T.erase t) ∧ (∀ e ∈ σ0'.edges, e ∈ σ0.edges) :=
  exists_admitted_ofSubset h0 (List.erase_subset)

end Zanzibar
