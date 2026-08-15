import ZanzibarProofs.GraphIndex.Exec

/-!
# The WIDENED `ttuStarFree` and its decision procedure — part (iv)'s blocking question, ANSWERED

`formal/HANDOFF.md` and the project board have carried this since 2026-08-14:

> ⚠ **(iv) has an unanswered question that could block it outright:** `removeGateB` is a
> runtime decision procedure that must decide the guard fail-closed, so the widened
> predicate has to stay **decidable by a boolean function**. If it is not, the remove leg
> cannot widen at all. Answer that before scheduling (iv).

**The answer is NO-BLOCK, and this file is the machine-checked artifact rather than the
argument.** `TtuStarFreeW` below is the widened predicate; `ttuStarFreeWB` is a `Bool`
function; `ttuStarFreeWB_iff` proves they agree. Nothing about the widening leaves the
decidable fragment:

* `TtuStarFree` (`RulesBareStar.lean`) is a bounded quantification over two **finite
  lists** — the store `T` and `schemaRewrites S` — which is why `Exec.lean::ttuStarFreeB`
  exists at all;
* the widening only weakens the *body* of that quantification, from `¬(match)` to
  `match → bridged`, and the new conjunct is
  `Schema.isSubjectWildcardUserset : Schema → String → String → Bool` — **already
  `Bool`-valued and already kernel-computable** (`UsStarWrite.lean`, disjunct (b) being
  `Schema.isStarTuplesetThrough`, landed as part (i) 2026-08-14);
* so `removeGateB` widens by exactly the same textual edit as the `Prop`, and
  `removeGateB_gate` keeps its shape. `removeGateBW` below demonstrates that, and
  `removeGateBW_gate` proves the widened gate still supplies every hypothesis.

## ⚠ WHY THIS IS ADDITIVE AND NOT THE LIFT

**`W4Fragment.ttuStarFree` is NOT changed by this file, and must not be until part (ii)
lands.** Dropping or widening the live clause makes `graph_correct` and
`backend_equivalence` machine-checked **FALSE** — that refutation
(`formal/history/PROOF_STATUS.md` 2026-08-10) stands, because Lean's `writeRules` /
`writeLoggedRules` are bridge-free folds that call `ensureInBridges` **never**, so the
in-bridge the widened predicate *assumes exists* is not materialized. Part (ii) is what
materializes it. Until then the widened predicate is the right *specification* of the
fragment and the wrong *hypothesis* for the current write model.

What this file therefore buys, precisely:

1. the blocking question is **closed** — part (iv) can be scheduled on effort alone;
2. the widening is proved a genuine **weakening** (`ttuStarFreeW_of_ttuStarFree`), so no
   store admitted today stops being admitted;
3. it is proved **strictly** wider at a store (`WideWitness.wide_admits` /
   `::narrow_rejects`), so part (iv) is not a relabeling;
4. the exact store that the widening newly admits is exhibited, which is the store part
   (ii) must make the graph answer correctly on — a standing target rather than prose.

Reference: `formal/history/PROOF_STATUS.md` 2026-08-10 and 2026-08-16;
`GraphIndex/RulesBareStar.lean::TtuStarFree`; `GraphIndex/Exec.lean::ttuStarFreeB`.
-/

namespace Zanzibar

/-! ## The widened predicate -/

/-- **`TtuStarFreeW S T`** — the widened fragment condition. A stored star-subject tuple
    matching a TTU rewrite arm is no longer forbidden outright; it is admitted **provided
    the through-shape it produces is bridged in**, i.e. the subject shape the TTU rule
    rewrites it to — `(t.subject.type, tr)` — is a declared subject-wildcard userset
    shape.

    That side condition is exactly what `Schema.isSubjectWildcardUserset` decides, and
    disjunct (b) of it (`Schema.isStarTuplesetThrough`, part (i)) is precisely the
    star-tupleset through-shape derivation Python has always had
    (`zanzibar_utils_v1.py::derive_schema_info`'s second loop). So the widened condition
    says "Python declares this shape and would build the bridge", which is the honest
    statement of what the graph covers once part (ii) composes `ensureInBridges` into the
    rule-routed write path. -/
def TtuStarFreeW (S : Schema) (T : Store) : Prop :=
  ∀ t ∈ T, t.subject.name = STAR →
    ∀ a ∈ schemaRewrites S, ∀ tr, a.kind = RuleKind.ttu tr →
      (t.relation = a.matchRel ∧ t.object.type = a.objectType) →
        S.isSubjectWildcardUserset t.subject.type tr = true

/-- **THE ANSWER TO PART (iv)'s BLOCKING QUESTION.** The widened predicate is decided by
    a `Bool` function — the same shape as `Exec.lean::ttuStarFreeB`, with the outright
    refusal `!(rel && otype)` weakened to `!(rel && otype) || bridged`. -/
def ttuStarFreeWB (S : Schema) (T : Store) : Bool :=
  T.all fun t =>
    !(t.subject.name == STAR) ||
      (schemaRewrites S).all (fun a =>
        match a.kind with
        | RuleKind.ttu tr =>
            !((t.relation == a.matchRel) && (t.object.type == a.objectType))
              || S.isSubjectWildcardUserset t.subject.type tr
        | RuleKind.computed => true)

/-- **Decidability, machine-checked.** The `Bool` function and the `Prop` agree. This is
    the theorem the board's open question asks for; everything else in this file is
    context for it. -/
theorem ttuStarFreeWB_iff (S : Schema) (T : Store) :
    ttuStarFreeWB S T = true ↔ TtuStarFreeW S T := by
  unfold ttuStarFreeWB TtuStarFreeW
  rw [List.all_eq_true]
  refine ⟨fun h t ht hstar a ha tr hkind hmatch => ?_, fun h t ht => ?_⟩
  · have hh := h t ht
    simp only [Bool.or_eq_true, Bool.not_eq_true', beq_eq_false_iff_ne, ne_eq] at hh
    have hall := hh.resolve_left (by simp [hstar])
    rw [List.all_eq_true] at hall
    have ha' := hall a ha
    rw [hkind] at ha'
    simp only [Bool.or_eq_true, Bool.not_eq_true', Bool.and_eq_false_iff,
      beq_eq_false_iff_ne, ne_eq] at ha'
    rcases ha' with hne | hbr
    · exact absurd hmatch (by
        rintro ⟨hrel, hobj⟩
        rcases hne with hr | ho
        · exact hr hrel
        · exact ho hobj)
    · exact hbr
  · simp only [Bool.or_eq_true, Bool.not_eq_true', beq_eq_false_iff_ne, ne_eq]
    by_cases hstar : t.subject.name = STAR
    · refine Or.inr ?_
      rw [List.all_eq_true]
      intro a ha
      cases hk : a.kind with
      | computed => rfl
      | ttu tr =>
          simp only [Bool.or_eq_true, Bool.not_eq_true', Bool.and_eq_false_iff,
            beq_eq_false_iff_ne, ne_eq]
          by_cases hrel : t.relation = a.matchRel
          · by_cases hobj : t.object.type = a.objectType
            · exact Or.inr (h t ht hstar a ha tr hk ⟨hrel, hobj⟩)
            · exact Or.inl (Or.inr hobj)
          · exact Or.inl (Or.inl hrel)
    · exact Or.inl hstar

/-! ## The widening is a genuine WEAKENING -/

/-- **No store admitted today stops being admitted.** The narrow predicate forbids the
    match outright, so its conclusion `False` discharges anything. -/
theorem ttuStarFreeW_of_ttuStarFree {S : Schema} {T : Store} (h : TtuStarFree S T) :
    TtuStarFreeW S T := by
  intro t ht hstar a ha tr hkind hmatch
  exact absurd hmatch (h t ht hstar a ha tr hkind)

/-- The same at the `Bool` level, so a widened `removeGateB` can only accept MORE ops. -/
theorem ttuStarFreeWB_of_ttuStarFreeB {S : Schema} {T : Store}
    (h : ttuStarFreeB S T = true) : ttuStarFreeWB S T = true :=
  (ttuStarFreeWB_iff S T).mpr (ttuStarFreeW_of_ttuStarFree ((ttuStarFreeB_iff S T).mp h))

/-! ## The widened runtime gate — the shape part (iv) actually lands

`Exec.lean::removeGateB` conjoins six deciders; only the `ttuStarFree` one moves. This
shows the edit is textual and that the gate keeps supplying every hypothesis, so part
(iv)'s cost is the CONSUMERS of the hypothesis (part (iii)), not the gate. -/

/-- `removeGateB` with the widened `ttuStarFree` decider substituted. -/
def removeGateBW (S : Schema) (σ : GraphState) (T : Store) (t : Tuple) : Bool :=
  decide (t ∈ T) && drainedB S σ && storeValidRulesB S T
    && bareStarStoreB T && ttuStarFreeWB S T && htermB S T

/-- **The widened gate still decides its guard**, with `TtuStarFree` replaced by
    `TtuStarFreeW`. Byte-for-byte `removeGateB_gate`'s proof shape — which is the
    evidence that part (iv)'s gate half is mechanical. -/
theorem removeGateBW_gate {S : Schema} {σ : GraphState} {T : Store} {t : Tuple}
    (hg : removeGateBW S σ T t = true) :
    RemoveAdmits σ T t ∧ cascadeKeys S σ = [] ∧ StoreValidRules S T ∧
      BareStarStore T ∧ TtuStarFreeW S T ∧
      (∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R) := by
  unfold removeGateBW at hg
  simp only [Bool.and_eq_true, decide_eq_true_eq] at hg
  obtain ⟨⟨⟨⟨⟨hmem, hdr⟩, hsv⟩, hbs⟩, hts⟩, hterm⟩ := hg
  exact ⟨hmem, (drainedB_iff S σ).mp hdr, (storeValidRulesB_iff S T).mp hsv,
    (bareStarStoreB_iff T).mp hbs, (ttuStarFreeWB_iff S T).mp hts,
    (htermB_iff S T).mp hterm⟩

/-- **The widened gate accepts everything the current one does.** So part (iv) cannot
    regress the remove leg — a store driven today keeps being driven. -/
theorem removeGateBW_of_removeGateB {S : Schema} {σ : GraphState} {T : Store} {t : Tuple}
    (h : removeGateB S σ T t = true) : removeGateBW S σ T t = true := by
  unfold removeGateB at h
  unfold removeGateBW
  simp only [Bool.and_eq_true] at h ⊢
  obtain ⟨⟨⟨⟨⟨hmem, hdr⟩, hsv⟩, hbs⟩, hts⟩, hterm⟩ := h
  exact ⟨⟨⟨⟨⟨hmem, hdr⟩, hsv⟩, hbs⟩, ttuStarFreeWB_of_ttuStarFreeB hts⟩, hterm⟩

/-! ## Non-vacuity — the widening is STRICT, at a store

Everything above is consistent with `TtuStarFreeW = TtuStarFree`, which would make part
(iv) a relabeling and this file worthless. The witness below is the star-tupleset shape
the 2026-08-10 refutation is about: a stored `folder:*` tupleset parent under a TTU whose
target relation is declared as a through-shape.

## ★ CONTROLLED — two sabotages, run 2026-08-16 (`docs/sabotage-procedure.md`)

**(S12) The bridged-shape exemption is dropped** — BOTH the `Prop`'s conclusion and the
`Bool`'s disjunct collapse back to the narrow form ("the exemption is not needed", the
one-line simplification a future reader would reach for). The attributable red is
```text
ZanzibarProofs/GraphIndex/TtuStarWide.lean:238: Tactic `decide` proved that the
  proposition ttuStarFreeWB SwT TwT = true is false
```
i.e. **`wide_admits` REDDENS**, while `narrow_rejects`, `unbridged_still_rejected`,
`through_shape_declared` and `ttu_arm_present` all stay GREEN. This is the sabotage that
proves the widening is STRICT; without it `wide_admits` could hold vacuously.
(`ttuStarFreeWB_iff`'s proof script also breaks — a tactic artifact of rewriting both
sides at once, not a second semantic finding.)

**(S13) The exemption is made UNCONDITIONAL** — the `isSubjectWildcardUserset` conjunct
is replaced by `true`, i.e. every star-subject TTU match is admitted regardless of
whether the shape is declared. The attributable red is
```text
ZanzibarProofs/GraphIndex/TtuStarWide.lean:254: Tactic `decide` proved that the
  proposition ttuStarFreeWB SwTn TwT = false is false
```
i.e. **`unbridged_still_rejected` REDDENS while `wide_admits` stays GREEN.** This is the
control that matters most: an unconditional exemption satisfies `wide_admits` perfectly
and is *unsound* — the widened predicate would admit stores whose bridge Python never
builds. The one-restriction delta between the two witness schemas (`SwT` declares
`[folder:*]`, `SwTn` declares `[folder]`) is what separates them, and S12/S13 redden
disjoint pins, so neither witness is carrying the other.
-/

namespace WideWitness

/-- A star-tupleset TTU shape: `access := viewer from parent`, with `parent`'s
    restrictions carrying a **bare wildcard** `[folder:*]`. That wildcard is what makes
    `(folder, "viewer")` a declared through-shape
    (`Schema.isStarTuplesetThrough`), so Python's `derive_schema_info` second loop
    declares the bridged-in shape and the graph builds the in-bridge. -/
def SwT : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"), .direct [("folder", BARE, true)]),
    (("doc", "access"), .ttu "viewer" "parent")], []⟩

/-- The stored **star** tupleset parent — the tuple the narrow predicate forbids. -/
def twT : Tuple := ⟨⟨"folder", STAR, BARE⟩, "parent", ⟨"doc", "d1"⟩⟩

def TwT : Store := [twT]

/-- **Non-vacuity, half 1: the through-shape really is declared.** Without this the whole
    witness could pass by the shape being irrelevant. -/
theorem through_shape_declared : SwT.isStarTuplesetThrough "folder" "viewer" = true := by
  decide

/-- **Non-vacuity, half 2: the TTU arm really is in the rule set**, so the quantifier the
    predicate ranges over is non-empty at this store. -/
theorem ttu_arm_present :
    (schemaRewrites SwT).contains ⟨"doc", "parent", "access", .ttu "viewer"⟩ = true := by
  decide

/-- **The narrow predicate REJECTS this store** — today's fragment excludes it. -/
theorem narrow_rejects : ttuStarFreeB SwT TwT = false := by decide

/-- **…and the widened predicate ADMITS it.** Together with `narrow_rejects` this is the
    strictness fact: part (iv) is a genuine widening, not a relabeling. -/
theorem wide_admits : ttuStarFreeWB SwT TwT = true := by decide

/-- The one-character control: the same schema with the tupleset's wildcard restriction
    made **concrete** (`[folder]` instead of `[folder:*]`), so no through-shape is
    declared. -/
def SwTn : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"), .direct [("folder", BARE, false)]),
    (("doc", "access"), .ttu "viewer" "parent")], []⟩

theorem control_no_through_shape : SwTn.isStarTuplesetThrough "folder" "viewer" = false := by
  decide

/-- **The widened predicate is not a blank cheque.** With the shape undeclared, the same
    star tupleset tuple is STILL rejected — the exemption is conditional on Python having
    declared the bridge, which is what makes the widened fragment honest. -/
theorem unbridged_still_rejected : ttuStarFreeWB SwTn TwT = false := by decide

/-- The remove gate inherits the strictness: the widened gate's `ttuStarFree` conjunct
    passes at this store where today's fails. Stated on the deciders rather than on the
    full gate so the fact is not masked by an unrelated conjunct. -/
theorem gate_conjunct_widens :
    ttuStarFreeB SwT TwT = false ∧ ttuStarFreeWB SwT TwT = true := ⟨narrow_rejects, wide_admits⟩

end WideWitness

end Zanzibar
