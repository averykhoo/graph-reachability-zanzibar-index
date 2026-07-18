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

end Zanzibar
