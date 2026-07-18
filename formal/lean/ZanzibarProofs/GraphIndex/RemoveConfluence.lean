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

end Zanzibar
