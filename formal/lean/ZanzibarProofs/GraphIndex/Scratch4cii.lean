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

/-- The proposed `LeafNode` carrier for Route B: `Leaf.lean::publicOfLeaf`, NOT
    `isLeafPred` — `isLeafPred_bare` proves `isLeafPred BARE = true`, so an
    `isLeafPred`-based carrier would classify every bare-subject node as "extra" and
    kill `untaintedShadow_writeLeg`'s `hsubj` premise everywhere (E3 below). -/
def leafNodeB (S : Schema) (k : NodeKey) : Bool :=
  (publicOfLeaf S k.type k.pred).isSome

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
    `LeafNode` definition, or prove the empty name unreachable. -/
theorem bare_publicOfLeaf_none : publicOfLeaf SlV "doc" BARE = none := by decide

/-- The node-level form: a bare subject node is NOT a `leafNodeB` node. Observed `false`. -/
theorem bare_subject_not_leafNode :
    leafNodeB SlV (subjNode ⟨"user", "alice", BARE⟩) = false := by decide

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
    so `UntaintedShadow.classify` (unweakened) has no branch for it. -/
theorem strong_shadow_false_at_raw :
    ¬ UntaintedShadow SlV (sR SlV tlEditor) (sP SlV tlEditor) := by
  intro h
  have hmem : (subjNode ⟨"user", "alice", BARE⟩,
      objNode ⟨"doc", "d1"⟩ (leafPred "viewer" 0)) ∈ (sR SlV tlEditor).edges := by decide
  rcases h.classify _ hmem with h0 | hD
  · exact absurd h0 (by decide)
  · rw [← derNodeB_correct] at hD
    exact absurd hD (by decide)

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
-/
