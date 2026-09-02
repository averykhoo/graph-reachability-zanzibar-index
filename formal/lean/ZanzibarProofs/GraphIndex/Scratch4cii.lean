import ZanzibarProofs.GraphIndex.LeafRules
import ZanzibarProofs.GraphIndex.CascadeStable
import ZanzibarProofs.GraphIndex.CascadeEnum
import ZanzibarProofs.GraphIndex.CascadeStrataEnum

/-!
# The 4c-ii shadow-chain adjudication battery (2026-08-20, board row `P3`)

The `#eval` battery that settles the proof-design adjudication `PROOF_STATUS.md`
2026-08-16c blocked leg 7 on. It probes proposition (★) — the three clauses that decide
whether `CascadeStable.lean::UntaintedShadow` can be weakened (Route B) or
`RulesWrite.lean::ReachedByRules` widened (Route C) — at every `LeafRules.lean` witness
schema, on BOTH admission chains, with the instrument controlled per
`docs/sabotage-procedure.md`.

**Zero-cone by construction**: downstream of `LeafRules` (documented "nothing here is
wired into a caller") + the Cascade enum modules; nothing imports this file except the
library root aggregator. Everything here is additive; no existing definition changes.

Findings, verdict, and the route budgets: `formal/history/PROOF_STATUS.md`
`## Session 2026-08-20b` and scope doc §11.9. Observed `#eval` outputs are quoted
verbatim in the docstrings below and in the `## Observed outputs` block at the end.
-/

namespace Zanzibar
namespace Scratch4cii

open LeafRuleWitness

/-! ## The instrument — Bool mirrors, PROVED and controlled

`CascadeStable.lean::DerNode` is a `Prop` with an existential over `String`s, so the
probe needs hand-written `Bool` mirrors. A wrong mirror silently returns `true` for
every clause (the 2026-07-28 Leg-0 sweep and the 2026-08-16 `persistedLeaves`
transcription both failed exactly there), so `derNodeB` is not merely spot-checked: it
is proved equivalent (`derNodeB_correct`), and the behavioural control
(`slV_extras_not_der` below) is kept anyway. -/

/-- Bool mirror of `CascadeStable.lean::DerNode`. ⚠ The scout's draft mirror omitted the
    `variant == .plain` conjunct — `objNode` with a non-STAR name always yields a
    `.plain` node, so `DerNode` constrains the variant too. `derNodeB_correct` is what
    makes this mirror trustworthy rather than plausible. -/
def derNodeB (S : Schema) (k : NodeKey) : Bool :=
  isDerived S (k.type, k.pred) && k.pred != BARE && k.name != STAR
    && k.variant == Variant.plain

/-! ⚠ **There is deliberately NO local `leafNodeB` here.** Until 2026-08-30d this file
defined its own `def leafNodeB S k := (publicOfLeaf S k.type k.pred).isSome` at this
point — a *proxy*, written before the real carrier existed. Step 1 of 4c-ii then added
the guarded carrier `Leaf.lean::leafNodeB` (`publicOfLeaf` **and** `leafPublic ≠ ""` and
`name ≠ STAR` and `variant = .plain`) in the parent namespace `Zanzibar`, and nothing
went red, because shadowing is legal: the local proxy kept winning every unqualified
reference in this file — including `clsB` and `termB`, the definitions the entire
weakened battery below is stated over.

That error ran in the UNSAFE direction. A *broader* leaf predicate makes the `weak`
disjunct of `clsB` easier to satisfy, so the `weak := true` rows could have been green
while the real widened `classify` fails. The proxy is therefore deleted rather than
renamed: every `leafNodeB` below now resolves to `Leaf.lean::leafNodeB`, the carrier
that `Leaf.lean::leafNodeB_correct` proves decides `Leaf.lean::LeafNode`. -/

/-- **The instrument is PROVED, not trusted**: `derNodeB` decides `DerNode`. -/
theorem derNodeB_correct (S : Schema) (k : NodeKey) :
    derNodeB S k = true ↔ DerNode S k := by
  constructor
  · intro h
    simp only [derNodeB, Bool.and_eq_true, bne_iff_ne, beq_iff_eq] at h
    obtain ⟨⟨⟨hd, hp⟩, hn⟩, hv⟩ := h
    refine ⟨k.type, k.name, k.pred, hd, hp, hn, ?_⟩
    cases k
    simp only [objNode, if_neg hn]
    simp_all
  · rintro ⟨dt, on, R, hd, hR, hon, rfl⟩
    simp [derNodeB, objNode, hd, hR, hon]

/-! ## The harness -/

/-- The leaf-routed (post-4c-ii) single write from empty. -/
def sR (S : Schema) (t : Tuple) : GraphState := (emptyState S).writeRulesRaw S t

/-- Today's rule-routed single write from empty. -/
def sP (S : Schema) (t : Tuple) : GraphState := (emptyState S).writeRules S t

/-- The σ-only extra edges of the raw write relative to today's write. -/
def extras (S : Schema) (t : Tuple) : List (NodeKey × NodeKey) :=
  (sR S t).edges.filter (fun ab => !((sP S t).edges.contains ab))

/-- Clause 1 of (★): nothing today's write produces is lost. -/
def mono (S : Schema) (t : Tuple) : Bool :=
  (sP S t).edges.all ((sR S t).edges.contains ·)

/-- Clause 2 of (★): every extra edge is leaf-targeted. -/
def extrasLeaf (S : Schema) (t : Tuple) : Bool :=
  (extras S t).all (fun ab => leafNodeB S ab.2)

/-- **THE INSTRUMENT CONTROL** — clause 2 with `derNodeB` substituted. At a tainted
    witness this MUST be `false` (extras are leaf-targeted, and a leaf name is not a
    declared derived relation), or the probe is comparing nothing. -/
def extrasDer (S : Schema) (t : Tuple) : Bool :=
  (extras S t).all (fun ab => derNodeB S ab.2)

/-- Clause 3 of (★): leaf nodes are never edge SOURCES (the `term` extension). -/
def noLeafSources (S : Schema) (t : Tuple) : Bool :=
  (sR S t).edges.all (fun ab => !leafNodeB S ab.1)

/-- Clause 3's structural, schema-wide twin: no rule READS a leaf predicate.
    `SlStP` is the witness that can falsify it — `applyRRule`'s `.ttu` arm rewrites the
    SUBJECT predicate. -/
def noLeafMatch (S : Schema) : Bool :=
  (schemaRewritesL S).all (fun r => !isLeafPred r.matchRel)

/-! ## Write tuples (untainted arms — the narrow-chain probes) -/

def tViewer : Tuple := ⟨⟨"user", "carol", BARE⟩, "viewer", ⟨"doc", "d1"⟩⟩
def tParent : Tuple := ⟨⟨"folder", "f1", BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def tA : Tuple := ⟨⟨"user", "alice", BARE⟩, "a", ⟨"doc", "d1"⟩⟩
def tX : Tuple := ⟨⟨"user", "alice", BARE⟩, "x", ⟨"doc", "d1"⟩⟩
def tMal : Tuple := ⟨⟨"user", "mallory", BARE⟩, "banned", ⟨"doc", "d1"⟩⟩
def tUnt : Tuple := ⟨⟨"user", "erin", BARE⟩, "editor", ⟨"doc", "d1"⟩⟩

/-! ## Write tuples (derived-key — the `_d`-chain probes)

`StoreValidRules` + `ComputedOnly` admits NO stored derived-key tuple
(`ReconcileCorrect.lean::exprDirects_computedOnly`), so these are reachable only on the
`StoreValidRulesD` chain — the chain T2b lives on since leg 5, and the one a
narrow-chain-only battery would leave unadjudicated. -/

/-- Derived-key Direct-arm write on `LeafWitness.Sw` (storage leaf at index 0). -/
def tApp : Tuple := ⟨⟨"user", "alice", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩

/-- Derived-key Direct-arm write on `LeafWitness.SwU` (storage leaf at index **2** —
    the shape the `".0"`-stripper failed on). -/
def tAppU : Tuple := ⟨⟨"user", "bob", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩

/-! ## E1 + E2 pins — narrow chain (untainted writes), all five tainted witnesses

Each records the literal observed `#eval` output in its docstring. A green here is a
NO-KILL result, not a theorem: (★) is quantified over all `WF`/`StoreValid*` stores and
six schemas with one write each do not establish it — the general clauses are owed in
the 4c-ii cone. -/

/-- Observed: `#eval mono SlV tlEditor` → `true`. -/
theorem slV_mono : mono SlV tlEditor = true := by decide
/-- Observed: `#eval extrasLeaf SlV tlEditor` → `true`. -/
theorem slV_extras_leaf : extrasLeaf SlV tlEditor = true := by decide
/-- Non-vacuity. Observed: `#eval (extras SlV tlEditor).length` → `1`
    (the `doc:d1#viewer.0@user:alice` copy — the edge P6 drops today). -/
theorem slV_extras_nonvacuous : (extras SlV tlEditor).length = 1 := by decide
/-- **THE MANDATORY INSTRUMENT CONTROL, kept as a permanent pin.** The clause-2 probe
    under `derNodeB` alone. Observed: `#eval extrasDer SlV tlEditor` → `false` — the
    leaf disjunct is doing the work; the probe is not always-true.
    (A naive `#guard extrasDer SlV tlEditor` would FAIL the build here — that failing
    guard, observed 2026-08-20, is exactly what makes the greens above evidence.) -/
theorem slV_extras_not_der : extrasDer SlV tlEditor = false := by decide
/-- Observed: `#eval noLeafSources SlV tlEditor` → `true`. -/
theorem slV_no_leaf_sources : noLeafSources SlV tlEditor = true := by decide
/-- Observed: `#eval noLeafMatch SlV` → `true`. -/
theorem slV_no_leaf_matchRel : noLeafMatch SlV = true := by decide

/-- Observed: `mono/extrasLeaf/noLeafSources` all `true`, `extras.length = 1`
    (`approver.1` copy), `extrasDer` `false` at `SlSw`/`tViewer`. -/
theorem slSw_battery :
    (mono SlSw tViewer, extrasLeaf SlSw tViewer, (extras SlSw tViewer).length,
     extrasDer SlSw tViewer, noLeafSources SlSw tViewer, noLeafMatch SlSw)
      = (true, true, 1, false, true, true) := by decide

/-- **The TTU witness — the only one that can falsify clause 3** (`applyRRule`'s `.ttu`
    arm mints a SUBJECT predicate). Observed: the minted subject predicate is the
    declared `"viewer"`, not a leaf name — `noLeafSources`/`noLeafMatch` stay `true`;
    extras = the `access.0` TTU copy, `extrasDer` `false`. -/
theorem slStP_battery :
    (mono SlStP tParent, extrasLeaf SlStP tParent, (extras SlStP tParent).length,
     extrasDer SlStP tParent, noLeafSources SlStP tParent, noLeafMatch SlStP)
      = (true, true, 1, false, true, true) := by decide

/-- The merge witness. Observed: all green, 1 extra (`r.0`), control `false`. -/
theorem slA_battery :
    (mono SlA tA, extrasLeaf SlA tA, (extras SlA tA).length,
     extrasDer SlA tA, noLeafSources SlA tA, noLeafMatch SlA)
      = (true, true, 1, false, true, true) := by decide

/-- The n-ary spine witness (in `GRAPH_FRAGMENT`; the one that already caught a wrong
    allocation). Observed at BOTH arms — `a` (spine leaf `any_of4.0`) and `x` (the
    derived-feeding `safe.0`): all green, control `false` at each. The `x` probe also
    shows a leaf edge stays terminal even where its public relation (`safe`) feeds
    ANOTHER derived key (`any_of4`) — that propagation is reconcile-emission business,
    not rule business. -/
theorem slN_battery_tA :
    (mono SlN tA, extrasLeaf SlN tA, (extras SlN tA).length,
     extrasDer SlN tA, noLeafSources SlN tA, noLeafMatch SlN)
      = (true, true, 1, false, true, true) := by decide

theorem slN_battery_tX :
    (mono SlN tX, extrasLeaf SlN tX, (extras SlN tX).length,
     extrasDer SlN tX, noLeafSources SlN tX)
      = (true, true, 1, false, true) := by decide

/-- **The negative control.** At the untainted witness the raw and routed writes are
    IDENTICAL: zero extras, so the battery is green under BOTH instruments and
    vacuously so — with `LeafRules.lean::lrUnt_no_leaf_rules`/`lrUnt_subsumed` as the
    independent explanation. Observed: `extras = []`, `mono` `true`, `extrasDer` `true`
    (vacuous), `noLeafSources` `true`. -/
theorem slUnt_battery :
    (mono SlUnt tUnt, (extras SlUnt tUnt).length, extrasLeaf SlUnt tUnt,
     extrasDer SlUnt tUnt, noLeafSources SlUnt tUnt, noLeafMatch SlUnt)
      = (true, 0, true, true, true, true) := by decide

/-- A two-write CHAIN at `SlV` (not just single writes from empty): both extras are
    leaf-targeted, monotone, no leaf sources. Observed: 2 extras
    (`viewer.0@alice`, `viewer.1@mallory`), both `leafNodeB`, neither `derNodeB`. -/
theorem slV_chain_battery :
    (((sR SlV tlEditor).writeRulesRaw SlV tMal).edges.filter
        (fun ab => !(((sP SlV tlEditor).writeRules SlV tMal).edges.contains ab))
      |>.all (fun ab => leafNodeB SlV ab.2 && !derNodeB SlV ab.2)) = true
    ∧ (((sP SlV tlEditor).writeRules SlV tMal).edges.all
        (((sR SlV tlEditor).writeRulesRaw SlV tMal).edges.contains ·)) = true
    ∧ (((sR SlV tlEditor).writeRulesRaw SlV tMal).edges.filter
        (fun ab => !(((sP SlV tlEditor).writeRules SlV tMal).edges.contains ab))).length
        = 2 := by
  refine ⟨by decide, by decide, by decide⟩

/-! ## The `_d`-chain probes — where (★) AS WRITTEN is REFUTED

★★ **FINDING (2026-08-20): clause 1 of the scout's (★) is FALSE on the `_d` chain.**
At a derived-key Direct-arm write, today's `writeRules` writes the tuple at the PUBLIC
R-node (its closure seed survives — `schemaRewrites` just has no rule matching a
derived relation), while `writeRulesRaw` routes it to the storage leaf. So
`(σ.writeRules S t).edges ⊆ (σ.writeRulesRaw S t).edges` fails: the public-node edge
is on the LEFT only. Pinned below (`slSwD_not_mono`).

**This kills neither route.** On the shadow chain the derived-key write is NEVER
replayed on the σ0 side — σ0 is rebuilt over the FILTERED store and
`CascadeStrataSettle.lean::untaintedShadow_writeLoggedOne_derived` holds σ0 FIXED,
classifying today's public-node edge as a σ-only `DerNode`-targeted extra. After
4c-ii the same write's σ-only extra is LEAF-targeted instead (pinned below). So the
correct per-chain proposition (★′) is:

* narrow chain (`StoreValidRules`+`ComputedOnly`): no derived-key tuple exists, stage 1
  is the identity, and clauses 1–3 hold as stated (the pins above);
* `_d` chain: derived-key writes are σ-only extras with σ0 fixed, and the obligation is
  only that the extra's TARGET is classifiable (`DerNode` today, `LeafNode` after
  4c-ii) and TERMINAL (clause 3) — which is precisely `UntaintedShadow.classify`'s new
  disjunct under Route B, or is absorbed into σ0 itself under Route C.
-/

/-- ★ Observed: `#eval mono SlSw tApp` → `false` — (★) clause 1 as literally
    quantified is REFUTED at a derived-key write. Kept as a positive pin so the
    refutation cannot be un-learned. -/
theorem slSwD_not_mono : mono SlSw tApp = false := by decide

/-- The paired classification swap, observed:
    today's σ-only extra (vs the empty shadow) targets the public R-node —
    `derNodeB = true`, `leafNodeB = false`; the raw write's extra targets the storage
    leaf `approver.0` — `leafNodeB = true`, `derNodeB = false`. Route B's weakening is
    exactly this swap, edge for edge. -/
theorem slSwD_classification_swap :
    ((sP SlSw tApp).edges.all (fun ab => derNodeB SlSw ab.2 && !leafNodeB SlSw ab.2))
      = true
    ∧ ((sR SlSw tApp).edges.all (fun ab => leafNodeB SlSw ab.2 && !derNodeB SlSw ab.2))
      = true
    ∧ (sR SlSw tApp).edges.length = 1 ∧ (sP SlSw tApp).edges.length = 1 := by
  refine ⟨by decide, by decide, by decide, by decide⟩

/-- Clause 3 holds on the `_d` probe too: the leaf edge's SOURCE is the plain subject
    node. Observed `true`. -/
theorem slSwD_no_leaf_sources : noLeafSources SlSw tApp = true := by decide

/-- The index-2 `_d` probe (`SwU` — Python really mints `approver.2`): same swap at a
    non-zero index, so nothing here depends on index-0 accidents. Observed as pinned. -/
theorem swUD_classification_swap :
    ((sR LeafWitness.SwU tAppU).edges.all
        (fun ab => leafNodeB LeafWitness.SwU ab.2 && !derNodeB LeafWitness.SwU ab.2))
      = true
    ∧ ((sP LeafWitness.SwU tAppU).edges.all
        (fun ab => derNodeB LeafWitness.SwU ab.2)) = true
    ∧ (sR LeafWitness.SwU tAppU).edges.length = 1 := by
  refine ⟨by decide, by decide, by decide⟩

/-! ## E3 — the BARE trap: the `LeafNode` carrier must be `publicOfLeaf` -/

/-- Observed: `#eval publicOfLeaf SlV "doc" BARE` → `none` — while
    `Leaf.lean::isLeafPred_bare` proves `isLeafPred BARE = true`. So `publicOfLeaf` is
    the correct Route-B carrier and `isLeafPred` is not: an `isLeafPred`-based
    `LeafNode` makes every bare-subject node "extra" and falsifies
    `untaintedShadow_writeLeg`'s `hsubj` premise everywhere.

    ⚠ One residual for the Route-B implementer: `leafPublic BARE = ""`, and
    `Core/Schema.lean::relNameOK` does NOT forbid the empty relation name, so a
    (pathological) schema declaring a derived relation named `""` would make
    `publicOfLeaf _ _ BARE` return `some ""` and bare-subject nodes classify as
    `LeafNode`. Carry `leafPublic p ≠ ""` (or a WF nonempty-name clause) in the
    `LeafNode` definition, or prove the empty name unreachable.

    ⚠ Severity, adjudicated 2026-08-29b — do NOT re-raise this on re-read. It was
    once filed tier-1 ("a soundness hole in a well-formedness condition"); it is not.
    It constrained code that had not been written, so nothing in the tree was false
    because of it. Reading a design constraint as a live defect is what produced the
    original tier-1 filing.

    ⚠ **Status moved, 2026-08-30d.** This docstring used to add "no `LeafNode`
    definition exists anywhere in this tree, only the `leafNodeB` proxy above". Both
    halves are now false: step 1 of 4c-ii wrote `Leaf.lean::LeafNode`, and the proxy has
    been deleted. The constraint this docstring describes was ANSWERED rather than
    dropped — `LeafNode` carries the `leafPublic p ≠ ""` conjunct precisely for it, and
    it is pinned against a schema that actually exhibits the pathology at
    `Leaf.lean::swEmptyRel_bare_subject_not_leafNode`. -/
theorem bare_publicOfLeaf_none : publicOfLeaf SlV "doc" BARE = none := by decide

/-- The node-level form: a bare subject node is NOT a `leafNodeB` node. Observed `false`.

    ⚠ Cite this as `Scratch4cii.lean::bare_subject_not_leafNode`, never bare: a
    SAME-NAMED theorem lives at `Leaf.lean:1180`. -/
theorem bare_subject_not_leafNode :
    leafNodeB SlV (subjNode ⟨"user", "alice", BARE⟩) = false := by decide

/-- **The instrument's own guard — a mechanical refusal, not a docstring.**

    Every `leafNodeB` in this file must resolve to `Leaf.lean::leafNodeB`, the carrier
    that `Leaf.lean::leafNodeB_correct` proves decides `Leaf.lean::LeafNode`. From step
    1 of 4c-ii until 2026-08-30d it did NOT: this file defined its own unguarded proxy
    `(publicOfLeaf S k.type k.pred).isSome`, which shadowed the real carrier for `clsB`
    and `termB` and hence for the whole weakened battery below — silently, in the unsafe
    direction, because nothing goes red when a legal shadow is introduced.

    This theorem makes the shadow impossible to re-introduce silently. At
    `LeafWitness.SwEmptyRel` the two predicates DISAGREE by construction: the second
    conjunct records that the proxy's sole test passes there (`publicOfLeaf` is `some ""`,
    via `isLeafPred BARE`), while the first records that the guarded carrier still says
    `false` — the `leafPublic … ≠ ""` conjunct, E3's residual guard. So any local
    redefinition of `leafNodeB` without that guard turns THIS file red at THIS line.

    OBSERVED 2026-08-30d, deleting the proxy at the old `:51`: rc=0,
    `Build completed successfully (1089 jobs)` — i.e. re-pointing the battery at the
    strictly narrower carrier changed no verdict in this file, so the recorded prediction
    of "a diagnostic red confined to the file" was wrong and the battery's rows are valid
    as measured. That is a green result and therefore proves nothing by itself, which is
    exactly why this discriminating pin exists beside it.

    SABOTAGE, run to control THIS pin (`docs/sabotage-procedure.md`): re-add the deleted
    proxy verbatim above `derNodeB_correct`. Observed rc=1, and this line was the
    **only** error in the build:

    ```text
    error: ZanzibarProofs/GraphIndex/Scratch4cii.lean:344:78: Tactic `decide` proved
      that the proposition
      leafNodeB LeafWitness.SwEmptyRel (subjNode { type := "user", name := "alice",
        predicate := BARE }) = false ∧
        (publicOfLeaf LeafWitness.SwEmptyRel "user" BARE).isSome = true
    is false
    ```

    "Only error" is the load-bearing half of that observation, and it is what upgrades
    the green above from an absence of evidence into a measurement: this pin is the sole
    thing in the file that separates the two carriers, so every OTHER row here is
    insensitive to the shadowing. Proxy removed again: rc=0, 1089 jobs. -/
theorem leafNodeB_here_is_the_guarded_carrier :
    leafNodeB LeafWitness.SwEmptyRel (subjNode ⟨"user", "alice", BARE⟩) = false
      ∧ (publicOfLeaf LeafWitness.SwEmptyRel "user" BARE).isSome = true := by decide

/-! ## The starvation check (scope-doc §(c) residual) — does moving the Direct-arm
edge off the R-node starve the reconcile candidate enumerators?

Answer, measured: the EDGE channel (`CascadeEnum.lean::edgeHolders`) does starve —
after the raw write there is no in-edge at the public R-node, so the holder list is
empty where today it holds the grant subject. But the STORE channel
(`CascadeStrataEnum.lean::storedDirectSubjects`) enumerates exactly the stored
Direct-arm grants and reads the STORE, not σ — it is untouched by any σ re-pointing
and returns the same candidate. So the Direct-arm candidate survives; what 4b/P4 owes
is the leaf-probe bridge for the EDGE-side reads, not a rescue of the candidate set.
`edgeHolders`' remaining (post-4c-ii) feed at the R-node is reconcile emissions —
which is the stale-holder population it exists to enumerate. -/

/-- Observed: today's write feeds `edgeHolders` at the R-node with `user:alice`; the
    raw write leaves it EMPTY; `storedDirectSubjects` returns `user:alice` from the
    store either way. -/
theorem slSwD_starvation :
    edgeHolders (sP SlSw tApp) "doc" "d1" "approver"
      = [⟨"user", "alice", BARE⟩]
    ∧ edgeHolders (sR SlSw tApp) "doc" "d1" "approver" = []
    ∧ ((SlSw.lookup ("doc", "approver")).map
        (storedDirectSubjects [tApp] "doc" "d1" "approver"))
      = some [⟨"user", "alice", BARE⟩] := by
  refine ⟨by decide, by decide, by decide⟩

/-! ## Follow-up (2026-08-20, same session): the equivalence-check polarity question

Asked before the Route B/C pick: does weakening `UntaintedShadow` degrade
`backend_equivalence`? The dependency-chain answer is in `PROOF_STATUS.md` 2026-08-20b
§7 (polarity census: the shadow is hypothesis-position at every bridge whose conclusion
reaches the headline, conclusion-position only in the existence/preservation lemmas
that discharge those hypotheses; it is absent from `headline_statements.txt`,
`headline_definitions.txt`, and every audited STATEMENT pin). The theorem below is the
machine-checked half: at a leaf-routed state the UNWEAKENED shadow is already **FALSE**
against its rules-built σ0 — so post-4c-ii the choice is never "strong shadow vs weak
shadow"; it is "weakened-but-inhabited vs strong-but-uninhabited", and an uninhabited
shadow makes the W3d read bridge UNPROVABLE (not false) at every leaf-routed state. -/

/-- **The strong shadow is uninhabited at a leaf-routed state.** The raw write's
    `viewer.0` extra is neither in the rules-built σ0's edges nor `DerNode`-targeted,
    so the unweakened `classify` has no branch for it.

    ⚠ **ANCHORED at `ShadowOver (DerNode …)`, deliberately — do NOT "simplify" this back
    to `UntaintedShadow`.** `UntaintedShadow` is a reducible `abbrev`, so the two spellings
    are definitionally equal *today* and this is a no-op. They stop being equal the moment
    4c-ii re-points the abbrev at `DerNode ∨ LeafNode`, and at that point this theorem
    spelled with the abbrev would become **FALSE, not merely unprovable** — `d_weak_holds`
    below proves the weak mirror TRUE at a sibling fixture. Anchoring says what this
    theorem is *for*: it is a claim about the STRONG shadow specifically. -/
theorem strong_shadow_false_at_raw :
    ¬ ShadowOver (DerNode SlV) (sR SlV tlEditor) (sP SlV tlEditor) := by
  intro h
  have hmem : (subjNode ⟨"user", "alice", BARE⟩,
      objNode ⟨"doc", "d1"⟩ (leafPred "viewer" 0)) ∈ (sR SlV tlEditor).edges := by decide
  rcases h.classify _ hmem with h0 | hD
  · exact absurd h0 (by decide)
  · rw [← derNodeB_correct] at hD
    exact absurd hD (by decide)

/-! ## P14 (2026-08-28d): the six fields, against the σ0 the `_d` chain ACTUALLY builds

Everything above compares `sR` against `sP`. For the narrow chain that is the right
pairing. For the `_d` chain it is **not**, and no probe in this file noticed.

`CascadeStrataSettle.lean::reachedByW3d2_shadow_d` (:1179-1190) concludes over

    ∃ σ0, ReachedByRulesAdmitted σ0 S
            (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation)))
          ∧ UntaintedShadow S σ σ0

— the derived-key seeds are DROPPED from σ0's store, which that theorem's own docstring
calls "exactly what keeps σ0 inside the drained σ" (:1170-1171). Since
`ReachedByRulesAdmitted.step` is `σ.writeRules S t` on store `t :: T`
(`RulesComplete.lean:87-92`), a store of one derived-key tuple filters to `[]` and the
only σ0 the `_d` chain can build is `emptyState S`. `sP SlSw tApp` — which writes the
derived tuple onto the public `approver` R-node — is a σ0 that chain never pairs against.

So `slSwD_not_mono` (:241) is a true statement about `sR` vs `sP` and is **not** a
refutation of the `_d` chain's clause 1. The battery below re-asks it against `sF`, and
extends it to the three `UntaintedShadow` fields nothing in this file has ever touched:
everything above is edge-only (`mono` = `sub`, `extrasLeaf`/`extrasDer` = `classify`,
`noLeafSources` = `term`), leaving `nodesSub`, `closed` and `closed0` unprobed. If
`writeRulesRaw` minted leaf EDGES without minting leaf NODES, `closed` would fail and
4c-ii would owe an unbudgeted edit to `LeafRules.lean::writeRulesRaw`.

Store order matters: `ReachedByRulesAdmitted.step` PREPENDS, so a `Store` is
head-most-recent and both folds below run over `T.reverse`.
-/

/-- σ0 exactly as `reachedByW3d2_shadow_d` builds it: rules-routed over the
    untainted-FILTERED store. -/
def sF (S : Schema) (T : Store) : GraphState :=
  (T.filter (fun tp => !isDerived S (tp.object.type, tp.relation))).reverse.foldl
    (fun acc u => acc.writeRules S u) (emptyState S)

/-- The post-4c-ii σ over a whole store (the leaf-routed fold `sR` does for one write). -/
def sRf (S : Schema) (T : Store) : GraphState :=
  T.reverse.foldl (fun acc u => acc.writeRulesRaw S u) (emptyState S)

/-- `UntaintedShadow.classify` as a Bool. `weak := true` is Route B's `LeafNode`
    disjunct; `weak := false` is today's structure. -/
def clsB (S : Schema) (weak : Bool) (σ σ0 : GraphState) : Bool :=
  σ.edges.all (fun ab => σ0.edges.contains ab || derNodeB S ab.2 || (weak && leafNodeB S ab.2))

/-- `UntaintedShadow.sub`. -/
def subB (σ σ0 : GraphState) : Bool := σ0.edges.all (σ.edges.contains ·)

/-- `UntaintedShadow.nodesSub`. -/
def nodesSubB (σ σ0 : GraphState) : Bool := σ0.nodes.all (σ.nodes.contains ·)

/-- `UntaintedShadow.closed` (and `.closed0`, which is the same predicate at σ0). -/
def closedB (σ : GraphState) : Bool :=
  σ.edges.all (fun ab => σ.nodes.contains ab.1 && σ.nodes.contains ab.2)

/-- `UntaintedShadow.term`, extended over leaf nodes when `weak` — the clause-3 half of
    Route B. `term` quantifies over ALL keys; "no `DerNode` has an out-edge" is
    equivalent to "every edge's SOURCE is not a `DerNode`", which is what this decides. -/
def termB (S : Schema) (weak : Bool) (σ : GraphState) : Bool :=
  σ.edges.all (fun ab => !(derNodeB S ab.1 || (weak && leafNodeB S ab.1)))

/-- All six fields of `UntaintedShadow` at once, against an EXPLICIT σ0. -/
def shadowB (S : Schema) (weak : Bool) (σ σ0 : GraphState) : Bool :=
  clsB S weak σ σ0 && subB σ σ0 && nodesSubB σ σ0
    && closedB σ && closedB σ0 && termB S weak σ

/-- Per-field breakdown in `UntaintedShadow` declaration order
    (`classify`, `sub`, `nodesSub`, `closed`, `closed0`, `term`), so a `false` names
    the field that failed instead of just the conjunction. -/
def shadowFields (S : Schema) (weak : Bool) (σ σ0 : GraphState) :
    Bool × Bool × Bool × Bool × Bool × Bool :=
  (clsB S weak σ σ0, subB σ σ0, nodesSubB σ σ0, closedB σ, closedB σ0, termB S weak σ)

/-! ### The instrument is PROVED, not plausible

`derNodeB_correct` (:55) made the 2026-08-20 battery trustworthy one predicate at a
time. This battery reads SIX fields, five of which are new hand transcriptions of
`CascadeStable.lean:528-534`, so the same discipline is applied to the whole mirror:
in its UNWEAKENED form `shadowB` decides `UntaintedShadow` exactly. A transcription
slip in any of the six now fails to compile instead of silently returning `true`.

⚠ **Corrected 2026-09-02c — this paragraph used to say the weakened form "has no such
theorem AND CANNOT HAVE ONE".** The "cannot" was wrong, and wrong in the direction that
costs an instrument: it inferred from *`UntaintedShadow` is not yet widened* that *the
widened predicate cannot be named*, when `ShadowOver` has been generic in its extras
predicate since 2026-08-30c (scope doc §11.13 item 1) and `fun k => DerNode S k ∨
LeafNode S k` is nameable today. `clsB_correct_weak` / `termB_correct_weak` /
`shadowB_correct_weak` below are that theorem. They are stated at the EXPLICIT widened
predicate and never at `UntaintedShadow`, which is what makes them landable BEFORE the
4c-ii flip and unchanged AFTER it.

✅ **The flip has since happened (4c-ii, 2026-09-02d)**, so the paragraph below is no
longer a prediction: `UntaintedShadow` now abbreviates
`ShadowOver (fun k => DerNode S k ∨ LeafNode S k)`, and the `_weak` twins are what keeps
this battery pointed at the live structure. The anchored originals stay ANCHORED — they
are the negative pins that justify the widening, and re-pointing them would make them
vacuous.

Why it mattered enough to land ahead of the flip: from the moment `UntaintedShadow` is
re-pointed, `shadowB_correct` (:583) goes on deciding `ShadowOver (DerNode S)` — it is
deliberately ANCHORED there — so without a widened twin the six-field mirror would stop
instrumenting the structure the live tree actually uses, while every `decide` row below
stayed green. That is precisely the 2026-08-28d `closedB` failure recorded at :551-575,
one layer down, and the reason the fix is a proved twin rather than more `decide` rows.
The `weak := true` rows below are still measurements of a PROPOSED structure — but their
mirror is now proved to decide it.

⚠ **Corrected 2026-08-30d.** This paragraph used to add "`leafNodeB` likewise still has
no `leafNodeB_correct` twin (:51)". That was true when written and was falsified in
silence by step 1 of 4c-ii, which added BOTH `Leaf.lean::leafNodeB` and its
`leafNodeB_correct` in the parent namespace while this file's local proxy went on
shadowing them. The proxy is gone; `leafNodeB` here IS the proved carrier, and
`leafNodeB_here_is_the_guarded_carrier` above keeps it that way. -/

theorem clsB_correct (S : Schema) (σ σ0 : GraphState) :
    clsB S false σ σ0 = true ↔ (∀ ab ∈ σ.edges, ab ∈ σ0.edges ∨ DerNode S ab.2) := by
  simp only [clsB, List.all_eq_true]
  constructor
  · intro h ab hab
    have h1 := h ab hab
    simp only [Bool.false_and, Bool.or_false, Bool.or_eq_true, List.contains_iff_mem] at h1
    exact h1.imp id (derNodeB_correct S ab.2).mp
  · intro h ab hab
    have h1 := h ab hab
    simp only [Bool.false_and, Bool.or_false, Bool.or_eq_true, List.contains_iff_mem]
    exact h1.imp id (derNodeB_correct S ab.2).mpr

theorem subB_correct (σ σ0 : GraphState) :
    subB σ σ0 = true ↔ (∀ ab ∈ σ0.edges, ab ∈ σ.edges) := by
  simp [subB, List.all_eq_true, List.contains_iff_mem]

theorem nodesSubB_correct (σ σ0 : GraphState) :
    nodesSubB σ σ0 = true ↔ (∀ k ∈ σ0.nodes, k ∈ σ.nodes) := by
  simp [nodesSubB, List.all_eq_true, List.contains_iff_mem]

theorem closedB_correct (σ : GraphState) :
    closedB σ = true ↔ (∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes) := by
  simp [closedB, List.all_eq_true, List.contains_iff_mem]

theorem termB_correct (S : Schema) (σ : GraphState) :
    termB S false σ = true ↔ (∀ k, DerNode S k → ∀ y, (k, y) ∉ σ.edges) := by
  simp only [termB, List.all_eq_true]
  constructor
  · intro h k hk y hy
    have h1 := h (k, y) hy
    simp only [Bool.false_and, Bool.or_false, Bool.not_eq_true'] at h1
    exact absurd ((derNodeB_correct S k).mpr hk) (by simp [h1])
  · intro h ab hab
    simp only [Bool.false_and, Bool.or_false, Bool.not_eq_true']
    by_contra hcon
    simp only [ne_eq, Bool.not_eq_false] at hcon
    exact h ab.1 ((derNodeB_correct S ab.1).mp hcon) ab.2 (by simpa using hab)

/-- **The six-field mirror decides the structure.**

    SABOTAGE (2026-08-28d, `docs/sabotage-procedure.md`) — the narrowest *plausible*
    weakening, not a catastrophe: a maintainer trims `closedB`'s `ab.2` conjunct as
    redundant, and updates `closedB_correct`'s statement to match, so the mirror and its
    own lemma stay CONSISTENT. Observed, `lake build`:

        error: …/Scratch4cii.lean:475:43: Application type mismatch: The argument
          (closedB_correct σ).mp hcl
        has type
          ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes
        but is expected to have type
          ∀ ab ∈ σ.edges, ab.1 ∈ σ.nodes ∧ ab.2 ∈ σ.nodes
        in the application
          UntaintedShadow.mk …

    (line numbers are the run's, before this docstring was added; the anchors that keep
    are the symbols.) rc=1, three errors, **all three inside `shadowB_correct`**. ⚠ The
    load-bearing half of that observation is what did NOT fail: every `decide` pin below,
    from `d_sigma0_is_empty` on, stayed GREEN, because a weakened `closedB`
    returns `true` wherever the honest one did. So the battery cannot police its own
    transcription — only this theorem can, and it can only do it because it names
    `UntaintedShadow` and lets `UntaintedShadow.mk` reject the argument. That is
    2026-08-28c's "a guard-only pin cannot catch a fence removal" one layer further
    down: **do not replace this with more `decide` rows.**

    ⚠ **ANCHORED at `ShadowOver (DerNode …)`** — see `strong_shadow_false_at_raw`. Note
    what the anchoring does *not* cost: the sabotage recorded above still works, because
    `ShadowOver.mk` is the same constructor `UntaintedShadow.mk` abbreviates. What it buys
    is that `shadowB … false` keeps deciding the **strong** shadow after the 4c-ii flip,
    instead of silently becoming a wrong mirror of a widened one — which is the exact
    failure this theorem exists to make impossible. -/
theorem shadowB_correct (S : Schema) (σ σ0 : GraphState) :
    shadowB S false σ σ0 = true ↔ ShadowOver (DerNode S) σ σ0 := by
  simp only [shadowB, Bool.and_eq_true]
  constructor
  · rintro ⟨⟨⟨⟨⟨hc, hs⟩, hn⟩, hcl⟩, hcl0⟩, ht⟩
    exact ⟨(clsB_correct S σ σ0).mp hc, (subB_correct σ σ0).mp hs,
           (nodesSubB_correct σ σ0).mp hn, (closedB_correct σ).mp hcl,
           (closedB_correct σ0).mp hcl0, (termB_correct S σ).mp ht⟩
  · intro h
    exact ⟨⟨⟨⟨⟨(clsB_correct S σ σ0).mpr h.classify, (subB_correct σ σ0).mpr h.sub⟩,
             (nodesSubB_correct σ σ0).mpr h.nodesSub⟩, (closedB_correct σ).mpr h.closed⟩,
           (closedB_correct σ0).mpr h.closed0⟩, (termB_correct S σ).mpr h.term⟩

/-! ### …and the WIDENED mirror is proved too (4c-ii step 10, 2026-09-02c)

The three twins below close the hole the corrected paragraph at :492-518 describes.
`shadowB_correct` above is ANCHORED at `ShadowOver (DerNode S)` on purpose, so it
survives the 4c-ii flip *as a pin on the strong shadow* — but that is exactly why it
stops policing the live structure the moment `UntaintedShadow` is re-pointed. These
state the same six-field decision at `fun k => DerNode S k ∨ LeafNode S k`, the
predicate the flipped `UntaintedShadow` will name.

⚠ Stated at the EXPLICIT predicate, NEVER at `UntaintedShadow`. That is not a stylistic
choice: writing `UntaintedShadow` here would make these theorems change meaning under
the flip, i.e. it would reproduce the very failure they exist to prevent, and it would
make them unlandable before it. -/

theorem clsB_correct_weak (S : Schema) (σ σ0 : GraphState) :
    clsB S true σ σ0 = true ↔
      (∀ ab ∈ σ.edges, ab ∈ σ0.edges ∨ (DerNode S ab.2 ∨ LeafNode S ab.2)) := by
  simp only [clsB, List.all_eq_true]
  constructor
  · intro h ab hab
    have h1 := h ab hab
    simp only [Bool.true_and, Bool.or_eq_true, List.contains_iff_mem] at h1
    rcases h1 with (h2 | h2) | h2
    · exact Or.inl h2
    · exact Or.inr (Or.inl ((derNodeB_correct S ab.2).mp h2))
    · exact Or.inr (Or.inr ((leafNodeB_correct S ab.2).mp h2))
  · intro h ab hab
    simp only [Bool.true_and, Bool.or_eq_true, List.contains_iff_mem]
    rcases h ab hab with h2 | h2 | h2
    · exact Or.inl (Or.inl h2)
    · exact Or.inl (Or.inr ((derNodeB_correct S ab.2).mpr h2))
    · exact Or.inr ((leafNodeB_correct S ab.2).mpr h2)

/-- **SABOTAGE** (`docs/sabotage-procedure.md`), run 2026-09-02c — and it is this theorem,
    not `shadowB_correct_weak`, that turned out to be the instrument.

    The narrowest *plausible* weakening is not "delete the twin" but a maintainer
    simplifying `termB`'s `weak` disjunct away as redundant: `:477-478`'s
    `!(derNodeB S ab.1 || (weak && leafNodeB S ab.1))` trimmed to `!(derNodeB S ab.1)`.
    Observed, `lake build`, rc=1, **four error sites, ALL inside this declaration**:

        error: …/Scratch4cii.lean:652:61: Invalid projection: Projections extract
          constructor fields for one-constructor inductive types. The expression
          h1
        has type `derNodeB S k = false` which has no fields.
        error: …/Scratch4cii.lean:652:52: unsolved goals
        …
        h1 : derNodeB S k = false
        hk : DerNode S k
        ⊢ derNodeB S k = false

    ⚠ **The load-bearing half is what did NOT fail.** Every `decide` row in the battery
    stayed GREEN — `d_weak_holds`, `mixed_weak_holds_strong_fails` and the rest — because
    a `termB` that has forgotten leaves returns `true` wherever the honest one did. So
    the battery is blind to this weakening in exactly the way `:551-575` records for
    `closedB` in 2026-08-28d, and before this twin existed the trim would have built
    green while the whole `weak := true` battery went on measuring a predicate that no
    longer mentions leaf nodes at all. That is the entire case for landing the twins
    ahead of the flip rather than with it. -/
theorem termB_correct_weak (S : Schema) (σ : GraphState) :
    termB S true σ = true ↔
      (∀ k, (DerNode S k ∨ LeafNode S k) → ∀ y, (k, y) ∉ σ.edges) := by
  simp only [termB, List.all_eq_true]
  constructor
  · intro h k hk y hy
    have h1 := h (k, y) hy
    simp only [Bool.true_and, Bool.not_eq_true', Bool.or_eq_false_iff] at h1
    rcases hk with hk | hk
    · exact absurd ((derNodeB_correct S k).mpr hk) (by simp [h1.1])
    · exact absurd ((leafNodeB_correct S k).mpr hk) (by simp [h1.2])
  · intro h ab hab
    simp only [Bool.true_and, Bool.not_eq_true', Bool.or_eq_false_iff]
    refine ⟨?_, ?_⟩
    · by_contra hc
      exact h ab.1 (Or.inl ((derNodeB_correct S ab.1).mp (by simpa using hc))) ab.2
        (by simpa using hab)
    · by_contra hc
      exact h ab.1 (Or.inr ((leafNodeB_correct S ab.1).mp (by simpa using hc))) ab.2
        (by simpa using hab)

/-- **The six-field mirror decides the WIDENED structure.** The post-flip twin of
    `shadowB_correct`; see the section note above for why it is stated at the explicit
    predicate rather than at `UntaintedShadow`. -/
theorem shadowB_correct_weak (S : Schema) (σ σ0 : GraphState) :
    shadowB S true σ σ0 = true ↔ ShadowOver (fun k => DerNode S k ∨ LeafNode S k) σ σ0 := by
  simp only [shadowB, Bool.and_eq_true]
  constructor
  · rintro ⟨⟨⟨⟨⟨hc, hs⟩, hn⟩, hcl⟩, hcl0⟩, ht⟩
    exact ⟨(clsB_correct_weak S σ σ0).mp hc, (subB_correct σ σ0).mp hs,
           (nodesSubB_correct σ σ0).mp hn, (closedB_correct σ).mp hcl,
           (closedB_correct σ0).mp hcl0, (termB_correct_weak S σ).mp ht⟩
  · intro h
    exact ⟨⟨⟨⟨⟨(clsB_correct_weak S σ σ0).mpr h.classify, (subB_correct σ σ0).mpr h.sub⟩,
             (nodesSubB_correct σ σ0).mpr h.nodesSub⟩, (closedB_correct σ).mpr h.closed⟩,
           (closedB_correct σ0).mpr h.closed0⟩, (termB_correct_weak S σ).mpr h.term⟩

/-- A mixed store on `SlSw`: one derived-key write (`approver`) and one untainted write
    (`viewer`). The filter keeps exactly the second. This is the shape the unowned
    obligation `CascadeStable.lean::reachedByW3d_shadow` is about — post-re-point the
    leaf list is a strict superset "on a mixed schema even for untainted tuples". -/
def tMix : Store := [tApp, tViewer]

/-! ### P1 — the σ0s genuinely differ, and only on the `_d` chain

The whole point turns on `sF ≠ sP` at a derived-key write and `sF = sP` without one.
Pinned first, or every row below is about a distinction that might not exist. -/

/-- Observed: `(sF SlSw [tApp]).edges.length` → `0`, `.nodes.length` → `0` — the filter
    drops the only tuple, so the `_d` chain's σ0 is literally `emptyState`, while
    `sP SlSw tApp` carries the public `approver` R-node edge. That gap is the entire
    content of `slSwD_not_mono` (:241). -/
theorem d_sigma0_is_empty :
    (sF SlSw [tApp]).edges = [] ∧ (sF SlSw [tApp]).nodes = []
    ∧ (sP SlSw tApp).edges.length = 1 := by
  refine ⟨by decide, by decide, by decide⟩

/-- …and on the narrow chain the filter drops NOTHING, so `sF` and `sP` agree and the
    2026-08-20 battery's pairing was right there. Observed: both `1`, equal. -/
theorem narrow_sigma0_agrees :
    (sF SlV [tlEditor]).edges = (sP SlV tlEditor).edges
    ∧ (sF SlV [tlEditor]).edges.length = 1 := by
  refine ⟨by decide, by decide⟩

/-! ### P2 — the six-field battery

Read the tuples in `UntaintedShadow` declaration order:
`(classify, sub, nodesSub, closed, closed0, term)`. -/

/-- **A — the `_d` chain against its OWN σ0: the weakened shadow holds, all six fields.**
    Observed: `shadowB SlSw true (sR SlSw tApp) (sF SlSw [tApp])` → `true`,
    fields → `(true, true, true, true, true, true)`. -/
theorem d_weak_holds :
    shadowB SlSw true (sR SlSw tApp) (sF SlSw [tApp]) = true
    ∧ shadowFields SlSw true (sR SlSw tApp) (sF SlSw [tApp])
        = (true, true, true, true, true, true) := by
  refine ⟨by decide, by decide⟩

/-- **A' — and the UNWEAKENED shadow fails, on `classify` ALONE.** Observed fields →
    `(false, true, true, true, true, true)`. This is the sharp form of the Route B
    claim: the weakening needed is exactly one disjunct on exactly one field. In
    particular `term` holds even in its leaf-extended form, so clause 3 costs nothing. -/
theorem d_strong_fails_only_on_classify :
    shadowFields SlSw false (sR SlSw tApp) (sF SlSw [tApp])
      = (false, true, true, true, true, true) := by decide

/-- **B — the instrument artifact, isolated.** Against `sP` (the σ0 the `_d` chain never
    builds) the failing fields are `sub` and `nodesSub`, NOT `classify`. Observed fields
    → `(true, false, false, true, true, true)`. `mono` (:81) IS `sub`, so
    `slSwD_not_mono`'s `false` is this `sub` — a true fact about the wrong pairing. -/
theorem d_vs_sP_fails_on_sub :
    shadowFields SlSw true (sR SlSw tApp) (sP SlSw tApp)
      = (true, false, false, true, true, true) := by decide

/-- **C — narrow chain**: weak holds; strong fails on `classify` alone. Observed
    `(true,…)` and `(false, true, true, true, true, true)`. Consistent with
    `strong_shadow_false_at_raw`, which used `sP` — legitimate here by
    `narrow_sigma0_agrees`. -/
theorem narrow_weak_holds_strong_fails :
    shadowB SlV true (sR SlV tlEditor) (sF SlV [tlEditor]) = true
    ∧ shadowFields SlV false (sR SlV tlEditor) (sF SlV [tlEditor])
        = (false, true, true, true, true, true) := by
  refine ⟨by decide, by decide⟩

/-- **D — the index-2 `_d` witness** (`SwU`, storage leaf at index 2): same result, so
    nothing above is an index-0 accident. Observed → `true`. -/
theorem d_idx2_weak_holds :
    shadowB LeafWitness.SwU true (sR LeafWitness.SwU tAppU)
      (sF LeafWitness.SwU [tAppU]) = true := by decide

/-! ### P3 — the MIXED store: the unowned obligation's own shape

`P3`'s item block records an unowned obligation at
`CascadeStable.lean::reachedByW3d_shadow` (via `untaintedShadow_writeLeg`): post-re-point
"the leaf list is a strict superset on a mixed schema **even for untainted tuples** — no
slice owned it". `tMix` is that shape: one derived-key write plus one untainted `viewer`
write on `SlSw`. Measured, the superset is real and it is 2 edges wide — and BOTH extras
classify under the single `LeafNode` disjunct, including the one minted by the untainted
tuple. -/

/-- Observed: `(sRf SlSw tMix).edges.length` → `3` vs `(sF SlSw tMix).edges.length` → `1`
    — a strict superset, exactly as the unowned obligation predicted. -/
theorem mixed_is_strict_superset :
    (sRf SlSw tMix).edges.length = 3 ∧ (sF SlSw tMix).edges.length = 1
    ∧ subB (sRf SlSw tMix) (sF SlSw tMix) = true := by
  refine ⟨by decide, by decide, by decide⟩

/-- **The two extras, verbatim as observed.** `approver.0` is minted by the DERIVED-key
    write; `approver.1` is minted by the UNTAINTED `viewer` write being rule-routed onto
    a leaf. The second is the case no slice owned, and it is leaf-targeted like the
    first. -/
theorem mixed_extras_are_the_two_leaves :
    (sRf SlSw tMix).edges.filter (fun ab => !((sF SlSw tMix).edges.contains ab))
      = [(⟨"user", "alice", BARE, Variant.plain⟩, ⟨"doc", "d1", leafPred "approver" 0,
            Variant.plain⟩),
         (⟨"user", "carol", BARE, Variant.plain⟩, ⟨"doc", "d1", leafPred "approver" 1,
            Variant.plain⟩)] := by decide

/-- **E — the mixed store carries the weakened shadow, all six fields**, and the
    unweakened one fails on `classify` alone. Observed `true` and
    `(false, true, true, true, true, true)`. -/
theorem mixed_weak_holds_strong_fails :
    shadowB SlSw true (sRf SlSw tMix) (sF SlSw tMix) = true
    ∧ shadowFields SlSw false (sRf SlSw tMix) (sF SlSw tMix)
        = (false, true, true, true, true, true) := by
  refine ⟨by decide, by decide⟩

/-! ### P4 — the Prop-level consequence

`shadowB_correct` turns the strong rows above into statements about the strong shadow
itself, not about a Bool mirror of it. This is what `strong_shadow_false_at_raw`
says for the narrow chain, now said for the chain where it was NOT previously
established — and against the σ0 that chain actually builds.

(Both citations here carried a stale `(:332)` until 2026-08-30d; the theorem has not been
at `:332` for some time. Line numbers in citations rot silently — this file's own
`shadowB_correct` docstring already says "the anchors that keep are the symbols", so the
numbers are dropped rather than refreshed.) -/

/-- **The unweakened shadow is uninhabited at a leaf-routed `_d` state, against the σ0
    `reachedByW3d2_shadow_d` itself constructs.** So post-4c-ii the `_d` chain's choice is
    not "strong shadow vs weak shadow" either: it is "weakened-but-inhabited vs
    strong-but-uninhabited".

    ⚠ **ANCHORED** — see `strong_shadow_false_at_raw`. This one matters most of the four:
    `CascadeStable.lean`'s `ShadowOver` docstring cites *this* symbol as the justification
    for the whole genericization, so re-pointing it silently would leave that contract
    citing a theorem that no longer says what it is cited for. And `d_weak_holds` (below)
    proves the weak mirror TRUE at exactly this fixture — so under the abbrev spelling
    this statement would flip from true to false at the flip. -/
theorem strong_shadow_false_at_d_own_sigma0 :
    ¬ ShadowOver (DerNode SlSw) (sR SlSw tApp) (sF SlSw [tApp]) := by
  intro h
  exact absurd ((shadowB_correct SlSw (sR SlSw tApp) (sF SlSw [tApp])).mpr h) (by decide)

/-- …and on the mixed store, where the untainted tuple contributes an extra of its own.
    ⚠ **ANCHORED** — see `strong_shadow_false_at_raw`. -/
theorem strong_shadow_false_at_mixed :
    ¬ ShadowOver (DerNode SlSw) (sRf SlSw tMix) (sF SlSw tMix) := by
  intro h
  exact absurd ((shadowB_correct SlSw (sRf SlSw tMix) (sF SlSw tMix)).mpr h) (by decide)

end Scratch4cii
end Zanzibar

/-!
## Observed outputs (the raw `#eval` transcript, 2026-08-20)

Recorded verbatim from the first build of this module, which carried the battery as
live `#eval`s before they were converted to the `decide` pins above (sabotage-procedure
rank 2: the pins ARE the battery, re-checked on every build; the `#eval`s were then
removed so clean builds stay quiet). Line numbers are the pre-conversion file's.

```text
info: "E1 SlV/tlEditor: mono=true extrasLeaf=true n=1"
info: "CONTROL SlV: extrasDer=false"
info: "extras SlV = [({ type := \"user\", name := \"alice\", pred := \"...\", variant := plain },
  { type := \"doc\", name := \"d1\", pred := \"viewer.0\", variant := plain })]"
info: "E2 SlV: noLeafSources=true noLeafMatch=true"
info: "E1 SlSw/tViewer: mono=true extrasLeaf=true n=1 extrasDer=false noLeafSources=true noLeafMatch=true"
info: "E1 SlStP/tParent: mono=true extrasLeaf=true n=1 extrasDer=false noLeafSources=true noLeafMatch=true"
info: "extras SlStP = [({ type := \"folder\", name := \"f1\", pred := \"viewer\", variant := plain },
  { type := \"doc\", name := \"d1\", pred := \"access.0\", variant := plain })]"
info: "E1 SlA/tA: mono=true extrasLeaf=true n=1 extrasDer=false noLeafSources=true noLeafMatch=true"
info: "E1 SlN/tA: mono=true extrasLeaf=true n=1 extrasDer=false"
info: "E1 SlN/tX: mono=true extrasLeaf=true n=1 extrasDer=false noLeafSources(tA)=true noLeafSources(tX)=true noLeafMatch=true"
info: "NEGCTL SlUnt/tUnt: mono=true n=0 extrasLeaf=true extrasDer=true noLeafSources=true noLeafMatch=true"
info: "CHAIN SlV 2-write: n=2"
info: "D-CHAIN SlSw/tApp: mono=false  <-- (STAR) clause 1 as stated"
info: "D-CHAIN sP extra der/leaf = [(true, false)]  sR extra der/leaf = [(false, true)]"
info: "D-CHAIN sR edges = [({user, alice, ..., plain}, {doc, d1, approver.0, plain})]
       sP edges = [({user, alice, ..., plain}, {doc, d1, approver, plain})]"
info: "D-CHAIN SwU/tAppU: sR targets leaf@2 = [approver.2]"
info: "E3: isLeafPred BARE = true; publicOfLeaf SlV doc BARE = none; leafNodeB(bare subj) = false"
info: "STARVE: edgeHolders(sP)=[{ user, alice, ... }] edgeHolders(sR)=[]
       storedDirectSubjects=some [{ user, alice, ... }]"
```

## The two in-place sabotage runs (both restored; `docs/sabotage-procedure.md`)

**(Sa) `leafNodeB` carrier inverted** — `(publicOfLeaf S k.type k.pred).isSome` replaced
by `isLeafPred k.pred`, the plausible wrong carrier. NINE reds, each attributable to the
BARE sentinel (`isLeafPred_bare`), none anywhere else — the clause-1/2 pins and the
`_d`-chain swap pins stayed green, so the red isolates the carrier choice:

```text
error: Scratch4cii.lean:148: decide proved that the proposition
  noLeafSources SlV tlEditor = true
is false
error: Scratch4cii.lean:289: decide proved that the proposition
  leafNodeB SlV (subjNode { type := "user", name := "alice", predicate := BARE }) = false
is false
  (+ the noLeafSources component of every witness battery: 157, 166, 172, 183, 188,
   198, 258)
```

**(Sb) `leafRewrites` dropped from `schemaRewritesL`** (in `LeafRules.lean`, restored
byte-identical — `git diff` empty after). The tree's own pins fire before this module
even builds, plus this module's non-vacuity pins would fire next:

```text
error: LeafRules.lean:452: decide proved that the proposition
  (rewriteClosureL SlV (rawWriteTuples SlV tlEditor)).contains {... leafPred "viewer" 0 ...} = true
is false
error: LeafRules.lean:463: decide proved that the proposition
  ((emptyState SlV).writeRulesRaw SlV tlEditor).edges ≠ ((emptyState SlV).writeRules SlV tlEditor).edges
is false
```
(`lrUnt_subsumed` stayed green under (Sb), as it must — the untainted fragment does not
see the leaf half.)

## Observed outputs — the P14 six-field battery (2026-08-28d)

Raw `#eval` transcript from the first build of the P14 block, before its rows were
converted to the `decide` pins above. Tuples read
`(label, shadowB, (classify, sub, nodesSub, closed, closed0, term))`.

```text
info: ("A  _d weak   vs sF", true,  (true,  true,  true,  true, true, true))
info: ("A' _d strong vs sF", false, (false, true,  true,  true, true, true))
info: ("B  _d weak   vs sP", false, (true,  false, false, true, true, true))
info: ("C  narrow weak   vs sF", true,  (true,  true, true, true, true, true))
info: ("C' narrow strong vs sF", false, (false, true, true, true, true, true))
info: ("D  _d idx2 weak vs sF", true,  (true, true, true, true, true, true))
info: ("E  mixed weak   vs sF", true,  (true,  true, true, true, true, true))
info: ("E' mixed strong vs sF", false, (false, true, true, true, true, true))
info: ("sizes", 1, 0, 0, 3, 1, 2, 1)
info: ("mixed extras",
 [({ type := "user", name := "alice", pred := "...", variant := Zanzibar.Variant.plain },
   { type := "doc", name := "d1", pred := "approver.0", variant := Zanzibar.Variant.plain }),
  ({ type := "user", name := "carol", pred := "...", variant := Zanzibar.Variant.plain },
   { type := "doc", name := "d1", pred := "approver.1", variant := Zanzibar.Variant.plain })])
```

`sizes` reads `(sR SlSw tApp).edges`, `(sF SlSw [tApp]).edges`, `(sF SlSw [tApp]).nodes`,
`(sRf SlSw tMix).edges`, `(sF SlSw tMix).edges`, `(sR SlV tlEditor).edges`,
`(sF SlV [tlEditor]).edges` — lengths.

**What the eight rows say together.** `classify` is the only field that ever fails, and
only in its unweakened form; `sub`/`nodesSub` fail only against `sP`, the σ0 the `_d`
chain never builds. The three fields no probe had ever touched (`nodesSub`, `closed`,
`closed0`) hold everywhere, on both chains and on the mixed store — so 4c-ii owes no
edit to `LeafRules.lean::writeRulesRaw` for endpoint closure, a risk that was open
until this battery ran.
-/
