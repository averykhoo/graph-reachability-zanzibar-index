/-
  ★ P6 PART (iv) STEP 4′ — BLOCKERS 1 AND 4, SETTLED IN THE KERNEL (2026-09-15c)

  `docs/p6-step4prime-scout-2026-09-15.md` § Blockers and unknowns, item 1:

      "UNVERIFIED (kernel): the four 'outright FALSE' verdicts … Every agent labelled these
       REASONED, no build was run anywhere in this sweep. Cheapest probe: one
       `formal/probes/*.lean` file that `decide`s the negation of
       `reachedByRulesAdmitted_edge_target_ne_wAny`'s conclusion on the existing fixture
       `LeafRules.lean::SlBridgeWitness` … That is ~10 lines and settles all four at once
       by exhibiting the witness."

  and item 4:

      "UNVERIFIED: is a bridged-in node's predicate ever a minted leaf name? … If none
       exists, `CascadeStrataSettle.lean::reachedByRulesAdmitted_edge_target_notLeaf` is a
       FIFTH outright-false lemma rather than a repair-with-a-new-case."

  Kept OUTSIDE the lake package, like every other probe here: zero cone, ungated,
  re-runnable evidence.  Run from `formal/lean` against the built oleans:

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_partiv_blocker1_kernel_2026-09-15.lean

  ⚠ rc=0 with NO output is a FAILED run, not a green one — every `#eval` line below must
  print.  The `theorem … := by decide` lines are the load-bearing half: they are KERNEL
  refutations, not evaluator readings, and a failure there is a compile error, so a clean
  compile IS the result.

  ── THE VERDICT ───────────────────────────────────────────────────────────────────────────

  **BLOCKER 1: ALL FOUR VERDICTS CONFIRMED IN THE KERNEL, and a FIFTH is added.** The
  scouting doc's four REASONED "becomes FALSE under the twin" calls are all correct, and each
  is refuted by the SAME single edge.  V1 `reachedByRulesAdmitted_edge_target_ne_wAny`, V2
  `reachedByRules_edge_sound`, V3 `reachedByRulesAdmitted_edges_plain`, V4
  `rulesAdmitted_edge_endpoints_bs` — all four are `¬ (conclusion)` proved in the kernel at a
  state the twin's own `step` reaches (N1/B1: `FoldAdmitsBridged` holds, by `decide`).

  **(1) V2 IS FALSE EVEN AFTER THE OBVIOUS DOMAIN REPAIR.** Moving the existential's domain
  from `rewriteClosure S t` to the twin's own `rewriteClosureL S (rawWriteTuples S t)` does
  NOT rescue `reachedByRules_edge_sound` (V2b): the bridge edge is not any closure member's
  grant edge at all.  The shape that DOES cover it is the third disjunct that
  `UsStarWrite.lean::foldl_writeBridgedOne_edges_sound` already carries — pinned positively
  as V2c, so step 6 is a "lift the existing three-disjunct fold lemma", not new mathematics
  at the disjunct level.

  **(2) ★ THE `SlBridgeWitness` STORE IS NOT `StoreValidRules`-VALID** (N8, measured
  `false`).  The concrete subject `group:g1#member` does not match the schema's only
  `group#member` restriction, which is declared WILDCARD-only — the SAME trap the
  2026-09-15b grid hit at `SwT` (`docs/p6-part-iv-plan-2026-09-14.md` § (ninth)).  None of
  V1–V4 carries that premise, so the refutations stand; but the ROUTE they matter for
  (`::graph_correct_rulesBS`) does.  Fixture B (`SlBridgeSV` = fixture A plus ONE extra
  CONCRETE restriction, wildcard flag retained) closes it: there every premise of every one
  of the four lemmas is true — including `StoreValidRules` — and all four are still refuted.
  ⚠ Do not cite fixture A alone for a fragment-relevance claim.

  **(3) BLOCKER 4: YES, a bridged-in node's predicate CAN be a minted leaf name** — fixture C
  (C3/C4): `Core/Schema.lean::WF` constrains declared relation KEYS (`p.1.2`) and says
  nothing about a restriction's predicate, so a schema may declare `[doc:*#viewer.0]` at the
  minted name `Leaf.lean::leafPred "viewer" 0`, and `UsStarWrite.lean::bridgePre`'s
  OBJECT-side call then bridges the leaf copy's object node to `w_any(doc, viewer.0)`.

  **(4) ⚠ …BUT THAT IS NOT WHY `notLeaf` DIES, AND THE SCOUTING DOC'S BLOCKER 4 ASKS THE
  WRONG QUESTION.** `CascadeStrataSettle.lean::reachedByRulesAdmitted_edge_target_notLeaf` is
  a FIFTH false lemma for the twin at fixture A ITSELF (V5a) — refuted by the ordinary LEAF
  GRANT edge `group:g1#member → doc:d1#viewer.0`, whose target predicate is the minted name.
  The BRIDGE edge does not refute it there at all (V5b: the bridge target's pred is the
  declared `member`).  The control that separates the two causes is C7: with the wildcard
  flag OFF — nothing bridged anywhere — `notLeaf` is STILL false.  **So `notLeaf` is falsified
  by the twin's ROUTING, one fold step before bridging is reached**, which means it is not a
  4′ cost at all: any leaf-routed admission predicate breaks it, including part (ii)'s
  already-landed `writeRulesRaw`.  Step 7 of the scouting doc's sub-step list must be
  re-scoped accordingly, and its "⚠ not in `audited_theorems.txt`, so a silent weakening
  costs no gate pin" warning becomes MORE urgent, not less.

  **(5) INSTRUMENT LIMITS, both recorded rather than worked around.** (a) `WF` cannot be
  discharged by `decide` here: its `relNameOK` is `¬ String.contains name '.'`, and
  `String.contains` → `String.anyAux` is well-founded recursion that does not reduce in the
  kernel.  Every `wf_*` pin below is therefore the `toList.contains` formulation of the same
  property (identical to `Leaf.lean::isLeafPred`'s own body), labelled as such — it is not
  the `WF` structure itself.  (b) `#eval` cannot print a `Prop`; membership readings use
  `List.contains`, while the load-bearing membership facts are the `∈` theorems.

  ── MUTATION SWEEP (2026-09-15, two arms, each a whole-file `lake env lean` on a TEMP COPY;
     the tracked file was never mutated) ──────────────────────────────────────────────────

  ```
  M0  INSTRUMENT CONTROL -- flip `v5b_bridge_edge_does_not_refute_notLeaf`'s own claim,
      `isLeafPred w.pred = false` -> `= true`.
      RED: exactly 1, and the attribution names it.
        error: m0.lean:421:81: Tactic `decide` proved that the proposition
          isLeafPred w.pred = true
        is false
      -> the harness attributes a single-declaration red.  Without this row the tables
         below could be a broken file reading as a discovery (`P6` step 0, 2026-09-13).

  M1  ATTRIBUTION -- fixture B's wildcard flag alone, `("group", "member", true)` ->
      `("group", "member", false)`.  Routing, store-validity and leaf allocation unmoved.
      RED (first run, BEFORE the repair below): exactly 2 -- `b3_still_bridges` and
      `b3_bridge_edge_present`.  All four `v*B_*` refutations stayed GREEN.
      ⚠ ★ THAT WAS `TK68` (2026-09-13e) FIRING INSIDE THIS PROBE.  The four refutations
      consumed `b3_bridge_edge_present` as a NAMED HELPER; when its proof failed, Lean
      error-recovered and still admitted it at its stated type, so every downstream
      refutation elaborated cleanly off a declaration that had just been refuted.  A
      mutation that DESTROYS the witness therefore left the claims looking green.
      REPAIR: every refutation now proves its own membership inline
      (`(by decide : (aB, wB) ∈ sigmaB.edges)`), off the primitive the mutation touches.
      RED (re-run, AFTER the repair): exactly 6 -- the same 2 plus all four refutations,
      each reddening at its OWN inlined witness:
        error: m1b.lean:355:85: ... (emptyState SlBridgeSV).bridgedInConcrete aB = true
        error: m1b.lean:357:63: ... (aB, wB) ∈ sigmaB.edges
        error: m1b.lean:368:23: ... (aB, wB) ∈ sigmaB.edges
        error: m1b.lean:375:25: ... (aB, wB) ∈ sigmaB.edges
        error: m1b.lean:382:29: ... (aB, wB) ∈ sigmaB.edges
        error: m1b.lean:391:29: ... (aB, wB) ∈ sigmaB.edges
      GREEN as predicted: every fixture A and fixture C declaration, and fixture B's five
      premise pins -- so the mutation is scoped to the flag, and the refutations are the
      BRIDGE's doing rather than "these four lemmas were always false of `writeRulesRaw`".
      (That last alternative is separately killed positively by the C8 green controls.)
  ```

  ⚠ Line numbers inside the fenced block are the MUTATED TEMP COPIES' and do not resolve in
  the file you are reading.  Resolve by SYMBOL; every declaration named is in this file.

  ⚠ Honest limit: this is a FILE sweep, not a tree sweep.  It says these pins are
  load-bearing *here*; it says nothing about the development, which does not import probes.

  ── TRANSCRIPT (literal, `lake env lean`, rc=0, 2026-09-15) ───────────────────────────────

  ("(A1) fixture A: twin admission (evaluator mirror) -- must be true", true)
  ("(A8) ★ storeValidRules at fixture A -- MEASURED false, see verdict (2)", false)
  ("(B1) fixture B: every premise of all four lemmas, incl. storeValidRules", true, true, true, true, true)
  ("(V5b) fixture A bridge target pred / isLeafPred -- the BRIDGE does not refute notLeaf", "member", false)
  ("(V5a) fixture A leaf GRANT target pred / isLeafPred -- THIS is what refutes notLeaf", "viewer.0", true)
  ("(C1) leaf routing is live / leafRewrites",
   true,
   [{ objectType := "doc", matchRel := "editor", outRel := "viewer.0", kind := Zanzibar.RuleKind.computed },
    { objectType := "doc", matchRel := "banned", outRel := "viewer.1", kind := Zanzibar.RuleKind.computed }])
  ("(C2) closure of the write (twin's own list)",
   [{ subject := { type := "user", name := "alice", predicate := "..." },
      relation := "editor",
      object := { type := "doc", name := "d1" } },
    { subject := { type := "user", name := "alice", predicate := "..." },
      relation := "viewer.0",
      object := { type := "doc", name := "d1" } }])
  ("(C3) is the leaf copy's OBJECT node bridged in? -- must be true", true)
  ("(C4) the bridge edge, and whether its target pred is a leaf name", true, "viewer.0", true)
  ("(C5) notLeaf premises at fixture C: relNames-dot-free / storeValidRules", true, true)
  ("(C6) twin admission at fixture C -- must be true or C4 is unreachable", true)
  ("(C7) ★ CONTROL, flag OFF: bridged? / does notLeaf survive? -- false, false", false, false)
  ("(C8) ★ GREEN CONTROL: with no bridging, V1's and V3's conclusions both HOLD", true, true)
  ("(S1) one edge refutes V1/V3/V4 -- present, and its target is wAny", true, true)
  ("(S2) V2: neither domain contains the bridge edge's target",
   [{ type := "doc", name := "d1", pred := "editor", variant := Zanzibar.Variant.plain }],
   [{ type := "doc", name := "d1", pred := "editor", variant := Zanzibar.Variant.plain },
    { type := "doc", name := "d1", pred := "viewer.0", variant := Zanzibar.Variant.plain }])
  ("(S3) fixture A twin state edges -- inspectable",
   [({ type := "group", name := "g1", pred := "member", variant := Zanzibar.Variant.plain },
     { type := "doc", name := "d1", pred := "viewer.0", variant := Zanzibar.Variant.plain }),
    ({ type := "group", name := "g1", pred := "member", variant := Zanzibar.Variant.plain },
     { type := "doc", name := "d1", pred := "editor", variant := Zanzibar.Variant.plain }),
    ({ type := "group", name := "g1", pred := "member", variant := Zanzibar.Variant.plain },
     { type := "group", name := "*", pred := "member", variant := Zanzibar.Variant.wAny })])

  ── WHAT WOULD FALSIFY THIS ───────────────────────────────────────────────────────────────

  Every refutation is `¬ (conclusion)` at a CONCRETE state, so the only way they are wrong is
  if that state is not one the twin reaches.  That is what the `FoldAdmitsBridged` pins
  (A1/B1/C6, `by decide`) are for.  If the twin is declared with a DIFFERENT admission
  binder, re-run these three lines first — the rest of the file follows from them.
-/
import ZanzibarProofs

open Zanzibar

namespace P6PartIvBlocker1

/-! ## §0 The twin, transcribed

The twin the scouting doc's step 3 declares (`docs/p6-step4prime-scout-2026-09-15.md`
§ Ordered sub-steps for 4′, step 3) is

    | step t (hprev) (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t))) :
        ReachedByRulesRawAdmitted (σ.writeRulesRaw S t) S (t :: T)

so its ONE-STEP state over a store `[t]` is literally `(emptyState S).writeRulesRaw S t`.
Every `sigma*` below is of that form, and every fixture pins the `FoldAdmitsBridged` side
condition, because a state no admitted write path reaches refutes nothing. -/

/-! ## §1 FIXTURE A — the in-tree fixture, reused BY NAME

`LeafRules.lean::SlBridgeWitness` (nested in `LeafRuleWitness`).  Referenced, never copied,
so a fixture edit cannot silently desynchronise this file. -/

abbrev S : Schema := LeafRuleWitness.SlBridgeWitness.SlBridge
abbrev t : Tuple := LeafRuleWitness.SlBridgeWitness.tlGrp
abbrev T : Store := [LeafRuleWitness.SlBridgeWitness.tlGrp]

/-- Fixture A's twin state. -/
def sigmaTwin : GraphState := (emptyState S).writeRulesRaw S t

/-- The bridge edge's source: the concrete userset node `group:g1#member`. -/
abbrev a : NodeKey := subjNode LeafRuleWitness.SlBridgeWitness.tlGrp.subject

/-- The bridge edge's target: `w_any(group, member)`. -/
abbrev w : NodeKey := LeafRuleWitness.SlBridgeWitness.wGrp

/-- The LEAF GRANT edge's target — `doc:d1#viewer.0`, pred a MINTED name.  This node is what
    §4 turns out to hinge on, and it is NOT a bridge node. -/
abbrev lgrant : NodeKey := objNode ⟨"doc", "d1"⟩ (leafPred "viewer" 0)

/-! ### Non-vacuity at fixture A -/

/-- (A1) ★ The twin's admission side condition holds at this step, so the state IS reached
    by `ReachedByRulesRawAdmitted.step` from `empty`.  KERNEL, not evaluator. -/
theorem a1_twin_step_is_admitted :
    FoldAdmitsBridged (emptyState S) (rewriteClosureL S (rawWriteTuples S t)) := by decide

#eval ("(A1) fixture A: twin admission (evaluator mirror) -- must be true",
        foldAdmitsBridgedB (emptyState S) (rewriteClosureL S (rawWriteTuples S t)))

/-- (A2) The bridge edge is in the twin's state — `SlBridgeWitness::
    writeRulesRaw_creates_the_bridge` restated locally so this file stands alone. -/
theorem a2_bridge_edge_present : (a, w) ∈ sigmaTwin.edges := by decide

/-- (A3) …and its target is a `wAny` node. -/
theorem a3_target_is_wAny : w.variant = Variant.wAny := by decide

/-- (A4) `StarFreeStore` — the hypothesis of `RulesComplete.lean::
    reachedByRulesAdmitted_edges_plain`.  `group:g1` and `doc:d1` are both concrete. -/
theorem a4_starFreeStore : StarFreeStore T := by
  show ∀ u ∈ T, u.subject.name ≠ STAR ∧ u.object.name ≠ STAR
  decide

/-- (A5) `BareStarStore` — one of the three hypotheses of `RulesBareStar.lean::
    rulesAdmitted_edge_endpoints_bs`. -/
theorem a5_bareStarStore : BareStarStore T := by
  show ∀ u ∈ T, (u.subject.name = STAR → u.subject.predicate = BARE) ∧ u.object.name ≠ STAR
  decide

/-- (A6) `TtuTuplesetsDirect` — the second of those three. -/
theorem a6_ttuTuplesetsDirect : TtuTuplesetsDirect S := by
  show ∀ d ∈ S.defs, ∀ tt ∈ exprTtus d.2,
    ∀ d' ∈ S.defs, d'.1 = (d.1.1, tt.2) → directsOnly d'.2 = true
  decide

/-- (A7) `TtuStarFree` — the third.  Routed through the AUDITED boolean mirror
    (`Exec.lean::ttuStarFreeB_iff`) because the `Prop` quantifies over an unbounded `tr`. -/
theorem a7_ttuStarFree : TtuStarFree S T :=
  (ttuStarFreeB_iff S T).mp (by decide)

/-- (A8) ★ **AND ONE PREMISE THAT FAILS.** The in-tree fixture's store is NOT
    `StoreValidRules`-valid: the concrete subject `group:g1#member` matches no restriction,
    because the schema declares `group#member` WILDCARD-only (`("group", "member", true)`).
    Same class as the 2026-09-15b grid's failed control at `WideWitness.SwT`.

    None of V1–V4 carries this premise, so §3 stands at fixture A; `notLeaf` (§4) and the
    route to `::graph_correct_rulesBS` DO carry it, which is why fixture B exists. -/
theorem a8_store_is_NOT_rules_valid : storeValidRulesB S T = false := by decide

#eval ("(A8) ★ storeValidRules at fixture A -- MEASURED false, see verdict (2)",
        storeValidRulesB S T)

/-! ## §2 THE FOUR VERDICTS — each the target lemma's CONCLUSION VERBATIM, instantiated at
    the twin's state, refuted in the kernel.

All four fall to the SAME single edge.  That is the finding: the twin materialises one new
KIND of edge, and these four lemmas are the four places the development assumed it could
not exist. -/

/-- ★ (V1) `CascadeStrataSettle.lean::reachedByRulesAdmitted_edge_target_ne_wAny`
    (`:751`, 2026-09-15 snapshot) is FALSE for the twin. -/
theorem v1_ne_wAny_is_false :
    ¬ (∀ x y : NodeKey, (x, y) ∈ sigmaTwin.edges → y.variant ≠ Variant.wAny) :=
  fun h => h a w (by decide) (by decide)

/-- ★ (V2a) `RulesCorrect.lean::reachedByRules_edge_sound` (`:125`) is FALSE for the twin in
    its PLAIN-closure shape: the bridge edge materialises no member of `rewriteClosure S t`. -/
theorem v2a_edge_sound_plain_is_false :
    ¬ (∀ x y : NodeKey, (x, y) ∈ sigmaTwin.edges →
        ∃ u ∈ T, ∃ v ∈ rewriteClosure S u,
          x = subjNode v.subject ∧ y = objNode v.object v.relation) := by
  intro h
  have hw := h a w (by decide : (a, w) ∈ sigmaTwin.edges)
  revert hw
  decide

/-- ★ (V2b) …and it is still FALSE after the DOMAIN is repaired to the twin's own leaf-routed
    list.  This is the measurement that matters: swapping `rewriteClosure S t` for
    `rewriteClosureL S (rawWriteTuples S t)` — the obvious first repair — does NOT rescue the
    statement, because the bridge edge is not any closure member's grant edge at all. -/
theorem v2b_edge_sound_L_is_false :
    ¬ (∀ x y : NodeKey, (x, y) ∈ sigmaTwin.edges →
        ∃ u ∈ T, ∃ v ∈ rewriteClosureL S (rawWriteTuples S u),
          x = subjNode v.subject ∧ y = objNode v.object v.relation) := by
  intro h
  have hw := h a w (by decide : (a, w) ∈ sigmaTwin.edges)
  revert hw
  decide

/-- ★ (V2c) POSITIVE CONTROL for V2a/V2b — the repair shape that DOES cover the witness is
    the third disjunct `UsStarWrite.lean::foldl_writeBridgedOne_edges_sound` (`:937`) already
    carries.  Without this arm V2a/V2b would read as "the twin has no edge-soundness law",
    which is false and would mis-plan the scouting doc's step 6. -/
theorem v2c_third_disjunct_covers_the_witness :
    (emptyState S).bridgedInConcrete a = true ∧ w = wAnyNode (a.type, a.pred) := by decide

/-- ★ (V3) `RulesComplete.lean::reachedByRulesAdmitted_edges_plain` (`:363`) is FALSE for the
    twin — at a store that IS star-free (A4), so the hypothesis is not the escape. -/
theorem v3_edges_plain_is_false :
    ¬ (∀ e ∈ sigmaTwin.edges, e.1.variant = Variant.plain ∧ e.2.variant = Variant.plain) := by
  intro h
  have hw := (h (a, w) (by decide : (a, w) ∈ sigmaTwin.edges)).2
  revert hw
  decide

/-- ★ (V4) `RulesBareStar.lean::rulesAdmitted_edge_endpoints_bs` (`:767`) is FALSE for the
    twin — at a store satisfying all three of its hypotheses (A5/A6/A7).  It is the SECOND
    conjunct (`e.2.variant = plain`) that dies.  This is the one the scouting doc's blocker 3
    calls "the surviving premise": it is the route to `::graph_correct_rulesBS`. -/
theorem v4_endpoints_bs_is_false :
    ¬ (∀ e ∈ sigmaTwin.edges,
        (e.1.variant = Variant.plain ∨ (e.1.variant = Variant.wAny ∧ e.1.pred = BARE))
        ∧ e.2.variant = Variant.plain) := by
  intro h
  have hw := (h (a, w) (by decide : (a, w) ∈ sigmaTwin.edges)).2
  revert hw
  decide

/-- ★ (V4b) ATTRIBUTION — V4's FIRST conjunct SURVIVES at this witness, so V4's red is
    attributable to the target half alone.  A refutation that killed both halves would not
    tell step 6 which conjunct to restate. -/
theorem v4b_source_conjunct_survives :
    (a.variant = Variant.plain ∨ (a.variant = Variant.wAny ∧ a.pred = BARE)) := by decide

/-! ## §3 FIXTURE B — the same four refutations with EVERY premise satisfied

Fixture A's store is not `StoreValidRules`-valid (A8).  V1–V4 do not carry that premise, but
`::graph_correct_rulesBS` — the theorem V4 is the route to — does, so a critic could call the
§2 refutations out-of-fragment.  `SlBridgeSV` closes that with ONE additive change to fixture
A's schema: the `group#member` restriction is declared CONCRETE as well as wildcard.  The
wildcard flag is retained, so `isSubjectWildcardUserset` is unmoved and the bridge still
fires; the concrete restriction is what `restrictionMatches` needs for the stored tuple. -/

namespace FixtureB

def SlBridgeSV : Schema :=
  ⟨[(("doc", "editor"), .direct [("user", BARE, false), ("group", "member", true),
                                 ("group", "member", false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .excl (.computed "editor") (.computed "banned"))], []⟩

abbrev tB : Tuple := LeafRuleWitness.SlBridgeWitness.tlGrp
abbrev TB : Store := [LeafRuleWitness.SlBridgeWitness.tlGrp]

def sigmaB : GraphState := (emptyState SlBridgeSV).writeRulesRaw SlBridgeSV tB

abbrev aB : NodeKey := subjNode LeafRuleWitness.SlBridgeWitness.tlGrp.subject
abbrev wB : NodeKey := wAnyNode ("group", "member")

/-- (B1) ★ EVERY premise of all four lemmas, at once — including the one fixture A fails. -/
theorem b1_admitted :
    FoldAdmitsBridged (emptyState SlBridgeSV) (rewriteClosureL SlBridgeSV (rawWriteTuples SlBridgeSV tB)) := by
  decide

theorem b1_storeValidRules : StoreValidRules SlBridgeSV TB :=
  (storeValidRulesB_iff SlBridgeSV TB).mp (by decide)

theorem b1_starFreeStore : StarFreeStore TB := by
  show ∀ u ∈ TB, u.subject.name ≠ STAR ∧ u.object.name ≠ STAR
  decide

theorem b1_bareStarStore : BareStarStore TB := by
  show ∀ u ∈ TB, (u.subject.name = STAR → u.subject.predicate = BARE) ∧ u.object.name ≠ STAR
  decide

theorem b1_ttuTuplesetsDirect : TtuTuplesetsDirect SlBridgeSV := by
  show ∀ d ∈ SlBridgeSV.defs, ∀ tt ∈ exprTtus d.2,
    ∀ d' ∈ SlBridgeSV.defs, d'.1 = (d.1.1, tt.2) → directsOnly d'.2 = true
  decide

theorem b1_ttuStarFree : TtuStarFree SlBridgeSV TB :=
  (ttuStarFreeB_iff SlBridgeSV TB).mp (by decide)

/-- (B2) ⚠ INSTRUMENT LIMIT — this is the `toList.contains` formulation of `Core/Schema.lean::
    WF.relNames`, not `WF` itself.  `relNameOK` is `¬ String.contains name '.'`, and
    `String.contains` → `String.anyAux` is well-founded recursion that does not reduce in the
    kernel, so `decide` cannot discharge the structure.  The predicate pinned here is
    character-identical to `Leaf.lean::isLeafPred`'s body. -/
theorem b2_relNames_dot_free : SlBridgeSV.defs.all (fun p => !isLeafPred p.1.2) = true := by
  decide

/-- (B3) The routing and the bridge are both still live at fixture B — without this the
    fixture could have "fixed" store-validity by killing the phenomenon. -/
theorem b3_still_derived : isDerived SlBridgeSV ("doc", "viewer") = true := by decide

theorem b3_still_bridges : (emptyState SlBridgeSV).bridgedInConcrete aB = true := by decide

theorem b3_bridge_edge_present : (aB, wB) ∈ sigmaB.edges := by decide

#eval ("(B1) fixture B: every premise of all four lemmas, incl. storeValidRules",
        storeValidRulesB SlBridgeSV TB,
        foldAdmitsBridgedB (emptyState SlBridgeSV) (rewriteClosureL SlBridgeSV (rawWriteTuples SlBridgeSV tB)),
        bareStarStoreB TB, ttuStarFreeB SlBridgeSV TB,
        sigmaB.edges.contains (aB, wB))

/-- ★ (V1-B) …and all four are still refuted. -/
theorem v1B_ne_wAny_is_false :
    ¬ (∀ x y : NodeKey, (x, y) ∈ sigmaB.edges → y.variant ≠ Variant.wAny) :=
  fun h => h aB wB (by decide) (by decide)

theorem v2B_edge_sound_L_is_false :
    ¬ (∀ x y : NodeKey, (x, y) ∈ sigmaB.edges →
        ∃ u ∈ TB, ∃ v ∈ rewriteClosureL SlBridgeSV (rawWriteTuples SlBridgeSV u),
          x = subjNode v.subject ∧ y = objNode v.object v.relation) := by
  intro h
  have hw := h aB wB (by decide : (aB, wB) ∈ sigmaB.edges)
  revert hw
  decide

theorem v3B_edges_plain_is_false :
    ¬ (∀ e ∈ sigmaB.edges, e.1.variant = Variant.plain ∧ e.2.variant = Variant.plain) := by
  intro h
  have hw := (h (aB, wB) (by decide : (aB, wB) ∈ sigmaB.edges)).2
  revert hw
  decide

theorem v4B_endpoints_bs_is_false :
    ¬ (∀ e ∈ sigmaB.edges,
        (e.1.variant = Variant.plain ∨ (e.1.variant = Variant.wAny ∧ e.1.pred = BARE))
        ∧ e.2.variant = Variant.plain) := by
  intro h
  have hw := (h (aB, wB) (by decide : (aB, wB) ∈ sigmaB.edges)).2
  revert hw
  decide

end FixtureB

/-! ## §4 BLOCKER 4 — and the question it asks is not the one that decides `notLeaf`

The scouting doc asks whether a BRIDGED-IN node's predicate can be a minted leaf name,
treating that as what would make `CascadeStrataSettle.lean::
reachedByRulesAdmitted_edge_target_notLeaf` (`:693`) a fifth false lemma.  The kernel says:
the answer is YES (§4b), but `notLeaf` does not need it — the twin's ordinary LEAF GRANT
edge already refutes it, at fixture A, with no bridging involved. -/

/-- ★ (V5a) THE FIFTH FALSE LEMMA, and the refuting edge is the LEAF GRANT, not the bridge:
    `group:g1#member → doc:d1#viewer.0`, whose target predicate is the minted name. -/
theorem v5a_leaf_grant_edge_present : (a, lgrant) ∈ sigmaTwin.edges := by decide

theorem v5a_leaf_grant_target_is_leaf : isLeafPred lgrant.pred = true := by decide

theorem v5a_notLeaf_is_false :
    ¬ (∀ x y : NodeKey, (x, y) ∈ sigmaTwin.edges → isLeafPred y.pred = false) := by
  intro h
  have hw := h a lgrant (by decide : (a, lgrant) ∈ sigmaTwin.edges)
  rw [show isLeafPred lgrant.pred = true by decide] at hw
  exact Bool.noConfusion hw

/-- ★ (V5b) ATTRIBUTION — the BRIDGE edge does NOT refute `notLeaf` at fixture A: its target
    predicate is the DECLARED relation `member`, which is dot-free.  So V5a is the routing's
    doing, and blocker 4's question is not what settles this lemma. -/
theorem v5b_bridge_edge_does_not_refute_notLeaf : isLeafPred w.pred = false := by decide

#eval ("(V5b) fixture A bridge target pred / isLeafPred -- the BRIDGE does not refute notLeaf",
        w.pred, isLeafPred w.pred)
#eval ("(V5a) fixture A leaf GRANT target pred / isLeafPred -- THIS is what refutes notLeaf",
        lgrant.pred, isLeafPred lgrant.pred)

/-! ### §4b Blocker 4's own question, answered YES — and `WF` does not stop it

The subject-side bridge can only target a shape `(subject.type, subject.predicate)`, and a
stored subject predicate is a declared relation name — that is why V5b is dot-free.  The
OBJECT-side bridge is the hole: `UsStarWrite.lean::bridgePre` (`:357`) bridges
`objNode u.object u.relation` too, and for a LEAF COPY that relation is a MINTED name
(`Leaf.lean::leafPred`, `:195`).  So the question reduces to whether a schema can declare a
subject-wildcard restriction AT a minted name.  `Core/Schema.lean::WF` (`:70`) constrains
`p.1.2` — the declared relation KEYS — and says nothing about a restriction's predicate.

`SlLeaf` is fixture A's schema with ONE change: the bridged-in restriction is
`("doc", leafPred "viewer" 0, true)` instead of `("group", "member", true)`. -/

namespace FixtureC

def SlLeaf : Schema :=
  ⟨[(("doc", "editor"), .direct [("user", BARE, false), ("doc", leafPred "viewer" 0, true)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .excl (.computed "editor") (.computed "banned"))], []⟩

/-- A plain `editor` write.  Its LEAF COPY has relation `viewer.0`, so the copy's object node
    is `doc:d1#viewer.0` — a concrete node of the declared bridged-in shape. -/
def tEd : Tuple := ⟨⟨"user", "alice", BARE⟩, "editor", ⟨"doc", "d1"⟩⟩

def Tl : Store := [tEd]

def sigmaLeaf : GraphState := (emptyState SlLeaf).writeRulesRaw SlLeaf tEd

/-- The object node of the leaf copy. -/
abbrev cLeaf : NodeKey := objNode ⟨"doc", "d1"⟩ (leafPred "viewer" 0)

/-- Its bridge target — pred `viewer.0`, a MINTED leaf name. -/
abbrev wLeaf : NodeKey := wAnyNode ("doc", leafPred "viewer" 0)

#eval ("(C1) leaf routing is live / leafRewrites", isDerived SlLeaf ("doc", "viewer"),
        leafRewrites SlLeaf)
#eval ("(C2) closure of the write (twin's own list)",
        rewriteClosureL SlLeaf (rawWriteTuples SlLeaf tEd))
#eval ("(C3) is the leaf copy's OBJECT node bridged in? -- must be true",
        (emptyState SlLeaf).bridgedInConcrete cLeaf)
#eval ("(C4) the bridge edge, and whether its target pred is a leaf name",
        sigmaLeaf.edges.contains (cLeaf, wLeaf), wLeaf.pred, isLeafPred wLeaf.pred)
#eval ("(C5) notLeaf premises at fixture C: relNames-dot-free / storeValidRules",
        SlLeaf.defs.all (fun p => !isLeafPred p.1.2), storeValidRulesB SlLeaf Tl)
#eval ("(C6) twin admission at fixture C -- must be true or C4 is unreachable",
        foldAdmitsBridgedB (emptyState SlLeaf) (rewriteClosureL SlLeaf (rawWriteTuples SlLeaf tEd)))

/-- (C-N1) NON-VACUITY: the state is reached by the twin. -/
theorem cN1_admitted :
    FoldAdmitsBridged (emptyState SlLeaf) (rewriteClosureL SlLeaf (rawWriteTuples SlLeaf tEd)) := by
  decide

/-- (C-N2) ⚠ the `toList.contains` formulation of `WF.relNames` — see (B2) for why this is
    not the structure itself. -/
theorem cN2_relNames_dot_free : SlLeaf.defs.all (fun p => !isLeafPred p.1.2) = true := by decide

/-- (C-N3) …and the store IS rules-valid here, so `notLeaf`'s own premises hold. -/
theorem cN3_storeValidRules : StoreValidRules SlLeaf Tl :=
  (storeValidRulesB_iff SlLeaf Tl).mp (by decide)

/-- ★★ (C4) BLOCKER 4 ANSWERED: a bridged-in node's predicate CAN be a minted leaf name. -/
theorem c4_bridge_edge : (cLeaf, wLeaf) ∈ sigmaLeaf.edges := by decide

theorem c4_bridged_in : (emptyState SlLeaf).bridgedInConcrete cLeaf = true := by decide

theorem c4_target_is_leaf : isLeafPred wLeaf.pred = true := by decide

/-- ★ (C7) THE CONTROL THAT SEPARATES THE TWO CAUSES.  Same schema, wildcard flag OFF, so
    NOTHING is bridged anywhere — and `notLeaf` is STILL false.  Hence `notLeaf` is falsified
    by the twin's LEAF ROUTING, one fold step before bridging is reached; C4 is a second,
    independent cause, not the cause. -/
def SlLeafCtl : Schema :=
  ⟨[(("doc", "editor"), .direct [("user", BARE, false), ("doc", leafPred "viewer" 0, false)]),
    (("doc", "banned"), .direct [("user", BARE, false)]),
    (("doc", "viewer"), .excl (.computed "editor") (.computed "banned"))], []⟩

theorem c7_no_bridge_without_the_flag :
    (emptyState SlLeafCtl).bridgedInConcrete cLeaf = false := by decide

theorem c7_notLeaf_still_false :
    ¬ (∀ e ∈ ((emptyState SlLeafCtl).writeRulesRaw SlLeafCtl tEd).edges,
        isLeafPred e.2.pred = false) := by decide

#eval ("(C7) ★ CONTROL, flag OFF: bridged? / does notLeaf survive? -- false, false",
        (emptyState SlLeafCtl).bridgedInConcrete cLeaf,
        ((emptyState SlLeafCtl).writeRulesRaw SlLeafCtl tEd).edges.all
          (fun e => !isLeafPred e.2.pred))

/-! ### §4c ★ GREEN CONTROLS — the four conclusions are not universally false

A `¬ (conclusion)` proof is only evidence about BRIDGING if the same conclusion HOLDS where
nothing bridges.  Without this section V1/V3/V4 would be equally consistent with "these
lemmas were always false of `writeRulesRaw`", which would mis-attribute the whole of step 4′.
`SlLeafCtl` is the no-bridge schema of C7, and the twin's state over it satisfies both
shapes — proved positively, by `decide`. -/

theorem c8_v1_conclusion_HOLDS_without_bridging :
    ∀ e ∈ ((emptyState SlLeafCtl).writeRulesRaw SlLeafCtl tEd).edges,
      e.2.variant ≠ Variant.wAny := by decide

theorem c8_v3_conclusion_HOLDS_without_bridging :
    ∀ e ∈ ((emptyState SlLeafCtl).writeRulesRaw SlLeafCtl tEd).edges,
      e.1.variant = Variant.plain ∧ e.2.variant = Variant.plain := by decide

#eval ("(C8) ★ GREEN CONTROL: with no bridging, V1's and V3's conclusions both HOLD",
        ((emptyState SlLeafCtl).writeRulesRaw SlLeafCtl tEd).edges.all
          (fun e => e.2.variant != Variant.wAny),
        ((emptyState SlLeafCtl).writeRulesRaw SlLeafCtl tEd).edges.all
          (fun e => e.1.variant == Variant.plain && e.2.variant == Variant.plain))

end FixtureC

/-! ## §5 The scoreboard, printed. -/

#eval ("(S1) one edge refutes V1/V3/V4 -- present, and its target is wAny",
        sigmaTwin.edges.contains (a, w), w.variant == Variant.wAny)
#eval ("(S2) V2: neither domain contains the bridge edge's target",
        (rewriteClosure S t).map (fun v => objNode v.object v.relation),
        (rewriteClosureL S (rawWriteTuples S t)).map (fun v => objNode v.object v.relation))
#eval ("(S3) fixture A twin state edges -- inspectable", sigmaTwin.edges)

end P6PartIvBlocker1
