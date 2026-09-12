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

/-! ## Wall 1 — the through-shape is UNTAINTED inside the fragment  (P6 step 0)

**Decided 2026-09-12b, landed 2026-09-12c.** The 2026-09-12 attack-first probe
(`formal/probes/p6_inbridge_stability_2026-09-12.lean` §7) measured what looked like a
*scope defect* blocking part (ii) outright: on a store carrying a **derived** through-
relation, no routing of the in-bridge can satisfy `TtuStarFreeW`'s side condition, because
the post-flip write leg keys the MINTED LEAF name (`approver.0`) while the only declared
shape is the PUBLIC name (`approver`) — `bridgesOnLeafRouted = 0` beside
`bridgesOnPublicKeyed = 1`, and a public-keyed bridge re-creates the ghost grant the
kernel refuted (`formal/history/PROOF_STATUS.md` §3).

The question that decides whether part (ii) owes anything there is: **can
`W4Fragment` — the one intended consumer of `TtuStarFreeW`, as the replacement for its
`ttuStarFree` field — reach such a store at all?** It cannot, and the two reasons below
are independent. Neither narrows `TtuStarFreeW`, so the four audited names at
`formal/audited_theorems.txt:537-540` are untouched.

1. the lemma below, which is available as a HYPOTHESIS at every consumption site
   (`W4Fragment.term`, `removeGateBW_gate`);
2. `RoutingArmWitness` below, which is hypothesis-free, store-independent, and
   **corrects the reason recorded on 2026-09-12b** — see the ★ block there.
-/

/-- **Wall 1, resolved by LEMMA rather than by narrowing the predicate.** Under the
    `NoTtuTarget` half of `W4Fragment.term` (`FullScope.lean:299`), the through-shape a TTU
    arm rewrites its subject onto — `(dt, tr)` for `tr` the arm's target relation — is never
    DERIVED, at any object type `dt`.

    So inside the fragment `TtuStarFreeW`'s side condition
    `S.isSubjectWildcardUserset t.subject.type tr` is only ever asked about an UNTAINTED
    relation. There the write leg keys the public name and the declared shape IS the public
    name: no leaf minting, no keying mismatch, and nothing for part (ii) to bridge that it
    cannot reach.

    ⚠ `t ∈ T`, `t.subject.name = STAR` and the `matchRel`/`objectType` match are **NOT
    needed** — the fact is about the SCHEMA alone. Do not add them back as binders; a
    reader would take them for load-bearing and the next widening would inherit a
    restriction that was never required.

    Proof: `isDerived S (dt, tr) = true` hands `NoTtuTarget S tr` to the arm `a`, whose
    conclusion at `tr` is `tr ≠ tr`. -/
theorem ttuStarFreeW_through_untainted {S : Schema}
    (hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R)
    {a : RRule} (ha : a ∈ schemaRewrites S) {tr : String}
    (hkind : a.kind = RuleKind.ttu tr) (dt : String) :
    isDerived S (dt, tr) = false := by
  rcases Bool.eq_false_or_eq_true (isDerived S (dt, tr)) with h | h
  · exact absurd rfl (hterm dt tr h a ha tr hkind)
  · exact h

/-! ## ★ The ROUTING-arm store, MEASURED — and the 2026-09-12b reason CORRECTED

The 2026-09-12b plan entry on task `P6` recorded the kill condition as "`Sd` **violates**
`W4Fragment.term`, because `("doc","control")` is a `.ttu "approver"` arm and `approver` is
derived". **That is FALSE, and the pins below are what it is instead.** Measured
2026-09-12c with `lake env lean` on a throwaway probe, verbatim:

```text
("taintedKeys Sd", [("folder", "approver"), ("doc", "control")])
("isDerived (folder,approver) / (doc,control) / (doc,parent) / (folder,blocked)", true, true, false, false)
("schemaRewrites Sd", [])
("noTtuTargetB Sd approver / control", true, true)
("htermB Sd Td / Sd TdStar / Sd []", true, true, true)
("isStarTuplesetThrough (folder,approver)", true)
("isSubjectWildcardUserset (folder,approver)", true)
("ttuStarFreeB / ttuStarFreeWB on TdStar", true, true)
("lookup (doc,control)", some (Zanzibar.Expr.ttu "approver" "parent"))
```

Why the recorded reason fails: `NoTtuTarget` quantifies over `schemaRewrites`, and
`schemaRewrites` **filters DERIVED defs out** (`RulesWrite.lean:82-83`, the faithful mirror
of `zanzibar_utils_v1.py::compile_ruleset`'s `if key not in tainted` loop). The TTU arm's own
owner `("doc","control")` is itself tainted — `exprRefs`'s `.ttu` case
(`Spec/Stratify.lean:36-42`) adds `("folder","approver")` via the tupleset's parent types, and
that key is derived — so the arm is never in `schemaRewrites` and `NoTtuTarget` never sees
it. `term` HOLDS at this store.

**What the measurement gives instead is a STRONGER fact, and it strengthens the plan's
conclusion rather than weakening it.** `schemaRewrites Sd = []`, so at this store *both*
`ttuStarFreeB` and `ttuStarFreeWB` are **vacuously true**: the widened predicate is not
merely satisfiable there, it is not ENGAGED there. The probe's ROUTING arm was never a
widening case, so "14 → 9 of 546 mismatches" was measured on a store part (ii) has no
obligation toward — the in-scope payoff is UNMEASURED, not failed, which is what
2026-09-12b concluded. And `Sd` leaves `W4Fragment` at `computedOrDirect`, for EVERY store
(`outside_fragment` below) — a store-independent kill, where the `term` reason would have
been store-dependent.

Contrast with `WideWitness.SwT` above, which is the in-scope shape: there `folder#viewer` is
untainted, the arm IS in `schemaRewrites` (`ttu_arm_present`), and `narrow_rejects` /
`wide_admits` separate. `no_rewrite_arms` versus `ttu_arm_present` is what keeps the vacuity
here attributable instead of accidental.

The derived through-shape itself is a declared fragment boundary that Python DOES cover, via
the processor's public-node bridge (`index_v4/processor.py::DeltaProcessor._write_derived` →
`WildcardIndex.add_tuple` → `_ensure_bridges` on both endpoints, `index_v4/wildcard.py:521-522`;
retraction `processor.py::_gc_public_node` → `_maybe_remove_bridges`). Recorded in
`formal/CORRESPONDENCE.md` §7, and filed as task `P25`.
-/

namespace RoutingArmWitness

/-- The probe's ROUTING-arm schema, verbatim from
    `formal/probes/p6_inbridge_stability_2026-09-12.lean:902-906`. `folder#approver` is
    derived (a `but not`), and `doc#control := approver from parent` makes
    `(folder, "approver")` a declared star-tupleset through-shape — the derived through-shape.

    Renamed from the probe's `Sd` on purpose: `FullScope.lean::W4WitnessDirect.Sd` is an
    unrelated schema, and `statement_pin.py::_refs` resolves receiver dot-calls by SUFFIX. -/
def SdRouting : Schema :=
  ⟨[(("folder", "blocked"),  .direct [("user", BARE, false)]),
    (("folder", "approver"), .excl (.direct [("user", BARE, false)]) (.computed "blocked")),
    (("doc", "parent"),      .direct [("folder", BARE, true)]),
    (("doc", "control"),     .ttu "approver" "parent")], []⟩

/-- A star tupleset tuple matching the `doc#control := approver from parent` arm — the
    shape `TtuStarFreeW` would be about if the arm survived the taint filter. -/
def tdStar : Tuple := ⟨⟨"folder", STAR, BARE⟩, "parent", ⟨"doc", "d1"⟩⟩

def TdStar : Store := [tdStar]

/-- Non-vacuity 1: the through-relation really is DERIVED — this is the shape the probe
    attacked, not a mis-transcription. -/
theorem through_relation_derived : isDerived SdRouting ("folder", "approver") = true := by
  decide

/-- Non-vacuity 2: the through-shape really is DECLARED, so the store is a genuine
    near-miss rather than an irrelevant schema. -/
theorem through_shape_declared :
    SdRouting.isStarTuplesetThrough "folder" "approver" = true := by decide

/-- **The reason the arm never reaches `NoTtuTarget`**: the TTU arm's own owner key is
    tainted too, by `exprRefs`'s `.ttu` case pulling in the derived target. -/
theorem ttu_owner_also_derived : isDerived SdRouting ("doc", "control") = true := by decide

/-- **…so the taint filter empties the rule set.** Contrast `WideWitness.ttu_arm_present`,
    where the arm survives; that pair is what makes the vacuity below attributable. -/
theorem no_rewrite_arms : schemaRewrites SdRouting = [] := by decide

/-- **`term` HOLDS here.** The pin that refutes the reason recorded on 2026-09-12b: this
    store does not leave the fragment by terminality. -/
theorem term_holds : htermB SdRouting TdStar = true := by decide

/-- …nor by the `NoTtuTarget` half alone, which is vacuously true. -/
theorem noTtuTarget_holds : noTtuTargetB SdRouting "approver" = true := by decide

/-- **The widening is not ENGAGED here**: with no rewrite arms, the narrow predicate
    already admits the star tupleset store. -/
theorem narrow_admits : ttuStarFreeB SdRouting TdStar = true := by decide

/-- …and so, vacuously, does the widened one. So the ROUTING arm's mismatch count was
    measured on a store `TtuStarFreeW` says nothing about. -/
theorem wide_admits_vacuously : ttuStarFreeWB SdRouting TdStar = true := by decide

/-- **THE KILL CONDITION, store-independent.** `W4Fragment` cannot reach this schema under
    ANY store: `("doc","control")` is derived and its definition is a `.ttu`, and
    `ComputedOrDirect (.ttu _ _)` is `False` (`ReconcileCorrect.lean:151`). This is what
    2026-09-12b's `term` reason was reaching for, in the form that is actually true — and
    it is stronger, because it quantifies over every store rather than one. -/
theorem outside_fragment (T : Store) : ¬ W4Fragment SdRouting T := by
  intro hW
  exact hW.computedOrDirect "doc" "control" (.ttu "approver" "parent") rfl (by decide)

end RoutingArmWitness

/-! ## ★ `hterm` is NON-VACUOUS — the lemma's hypothesis excludes a real schema

`ttuStarFreeW_through_untainted` would be worthless if `NoTtuTarget` held at every derived
relation of every schema: the lemma would be true, the mutation sweep's M1 would still
redden (the hypothesis is *referenced*), and nothing would have been proved. That is the
"the only net" trap (`docs/sabotage-procedure.md` §"'The only net' is a claim about a test").

`RoutingArmWitness` shows the near-miss direction (a derived through-shape whose arm the
taint filter drops, so `term` HOLDS). `TermNonvacuityWitness` below shows the other: an
arm that SURVIVES the filter with a derived target, so `term` FAILS. The surviving route is
narrow and worth naming — `exprRefs`'s `.ttu` case only adds the target ref `(pt, tr)` for
parent types it can find, so an **undeclared tupleset relation** produces no target ref, the
owner stays untainted, and the arm reaches `schemaRewrites`. Measured 2026-09-13, verbatim:

```text
("taintedKeys Sund", [("folder", "approver")])
("isDerived (folder,approver) / (doc,control)", true, false)
("schemaRewrites Sund",
 [{ objectType := "doc", matchRel := "parent", outRel := "control", kind := Zanzibar.RuleKind.ttu "approver" }])
("noTtuTargetB Sund approver  -- FALSE here means term is NOT vacuous", false)
("htermB Sund []", false)
("rewriteMatchDeclaredB? see below", none)
```

⚠ **Scope of the claim.** This makes `term` non-vacuous *as a predicate*. It does NOT settle
whether `term`'s `NoTtuTarget` half is independent of the other carries inside the full
theorem chain: `Sund` also fails `RewriteMatchDeclared` (`FullScope.lean:1350` carries that
one separately from `W4Fragment`), so a chain that already assumes declared tuplesets might
get `NoTtuTarget` for free. Nobody has measured that, and this file does not claim it.
Filed on task `P6`'s log, 2026-09-13.
-/

namespace TermNonvacuityWitness

/-- `doc#control := approver from parent` with `doc#parent` **undeclared**, so the ttu arm's
    target ref is never added and the owner key stays untainted. -/
def Sund : Schema :=
  ⟨[(("folder", "blocked"),  .direct [("user", BARE, false)]),
    (("folder", "approver"), .excl (.direct [("user", BARE, false)]) (.computed "blocked")),
    (("doc", "control"),     .ttu "approver" "parent")], []⟩

/-- Non-vacuity of the witness itself: the arm's target relation IS derived. -/
theorem target_derived : isDerived Sund ("folder", "approver") = true := by decide

/-- …and unlike `RoutingArmWitness.no_rewrite_arms`, the arm SURVIVES the taint filter,
    because the owner key is untainted. -/
theorem owner_untainted : isDerived Sund ("doc", "control") = false := by decide

/-- **`term` FAILS here.** So `ttuStarFreeW_through_untainted`'s hypothesis is a real
    restriction and the lemma has content. -/
theorem term_not_vacuous : htermB Sund [] = false := by decide

/-- …attributable to the `NoTtuTarget` half specifically, with an empty store so the
    `NoStoreSubjectR` half cannot be what fails. -/
theorem noTtuTarget_fails : noTtuTargetB Sund "approver" = false := by decide

end TermNonvacuityWitness

/-! ## ★ CONTROLLED — MUTATION SWEEP over everything added for P6 step 0 (2026-09-13)

A `decide` pin cannot "fail by passing" the way a test can: it either proves the
proposition or reds. Its failure mode is **stating a proposition that is true regardless
of the witness** — an inert pin that reads like evidence. So the sweep below mutates the
WITNESS (and, for the lemma, its hypothesis) one plausible edit at a time and records which
NAMED declaration reddens. Rule applied: every pin must be reddened by at least one
mutation, or it is inert and says so out loud
(`docs/sabotage-procedure.md` §"Sweep the TEST MODULE with mutations").

`M0` is the INSTRUMENT CONTROL — it flips `term_holds`'s own claim, and the sweep must
attribute the red to exactly `term_holds`. The first run of this sweep reported
`RED: <unattributed>` for all six mutations because the error-location regex expected
`…lean:N:C: error` while lake prints `error: …lean:N:C:`; the "candidate inert pins" list
was then the whole module, i.e. the instrument failed in the direction that looks like a
finding (`docs/sabotage-procedure.md` §"Sabotage your instrument too"). M0 is what makes
that visible on every future run.

```text
M0 INSTRUMENT CONTROL: flip term_holds's own claim true -> false  | RED: term_holds
M1 lemma: weaken hterm's NoTtuTarget to TtuTargetsSat _ (fun _ => True)
                                                                 | RED: ttuStarFreeW_through_untainted
M2 SdRouting: doc#parent restriction wildcard true -> false      | RED: through_shape_declared
M3 SdRouting: un-taint folder#approver (.excl -> .direct)         | RED: through_relation_derived,
     ttu_owner_also_derived, no_rewrite_arms, noTtuTarget_holds, narrow_admits, outside_fragment
M4 SdRouting: doc#control .ttu -> .computed                       | RED: through_shape_declared,
     ttu_owner_also_derived, no_rewrite_arms, outside_fragment
M5 SdRouting store: tdStar subject STAR -> concrete "f1"          | INERT (nothing reddened)
M6 SdRouting: retarget the TTU to the UNTAINTED relation
     (approver -> blocked) -- the IN-SCOPE shape                  | RED: through_shape_declared,
     ttu_owner_also_derived, no_rewrite_arms, narrow_admits, outside_fragment
M7 SdRouting: M6 + M2 -- arm SURVIVES and the through-shape is
     NOT declared; the only shape where the widening can REJECT   | RED: through_shape_declared,
     ttu_owner_also_derived, no_rewrite_arms, narrow_admits, wide_admits_vacuously, outside_fragment
M8 Sund: declare the missing doc#parent                           | RED: owner_untainted,
     term_not_vacuous, noTtuTarget_fails
M9 Sund: un-taint the arm's target (.excl -> .direct)             | RED: target_derived,
     term_not_vacuous
```

**M5 is INERT, and that is honest rather than a hole — but it has to be said, because a
reader would otherwise take the star subject for load-bearing.** `narrow_admits` and
`wide_admits_vacuously` hold at `SdRouting` for ANY store, star or concrete, because
`schemaRewrites SdRouting = []` leaves the quantifier body unreachable. That vacuity IS
the claim those two pins make; `no_rewrite_arms` is the pin that carries it, and M3/M6/M7
redden that. The star subject is present so the store is the shape the probe measured, not
because any pin depends on it.

**M7 is the one that earns `wide_admits_vacuously`.** Across M0–M6 it never reddened: in
every one of those shapes the widened predicate admits, so on its own it distinguishes
nothing. Only M7 — a surviving arm plus an undeclared through-shape — makes it fire. A pin
that needs a two-part mutation to redden is a pin whose content is a conjunction, and this
one's is "the widening admits *and* it is not engaged".

**M1 shows `hterm` is referenced; `TermNonvacuityWitness` shows it is non-trivial.** Both
are needed: a hypothesis that is used in the proof but satisfied by every schema would make
the lemma a tautology dressed as a scope result.

The sweep script is throwaway and gitignored (`.scratch/p6_step0_mutation_sweep.py`); this
table is the evidence.
-/

end Zanzibar
