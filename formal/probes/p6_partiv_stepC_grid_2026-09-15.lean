/-
  ★ P6 PART (iv) — THE (C) GRID (2026-09-15).  Turn the ONE witness of
  `p6_partiv_step3_rulerouted_2026-09-15.lean` line (12) into a differential SWEEP.

  `docs/p6-part-iv-plan-2026-09-14.md` § "Corrections appended 2026-09-15 (eighth)",
  § "Still not established at this line", first bullet:

      "**No grid.** (C)'s payoff is one witness.  A differential sweep of the bridged leg
       against `sem` over a query grid at star-tupleset stores is the natural next
       measurement and is cheap now that the pipeline is known to `#eval`."

  This is that sweep.  The question it answers is NOT "does the bridged leg answer this one
  query" (line (12) already said yes) but **"is the bridge-free → bridged swap of step 4′ a
  net repair over a grid, or does it merely move the mismatch"**.

  Kept OUTSIDE the lake package, like every other probe here: zero cone, ungated,
  re-runnable evidence.  Run from `formal/lean` against the built oleans:

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_partiv_stepC_grid_2026-09-15.lean

  ⚠ rc=0 with NO output is a FAILED run, not a green one.

  ── THE VERDICT ───────────────────────────────────────────────────────────────────────────

  **STEP 4′'s SWAP IS A NET REPAIR ON THE GRID, AND THE CEILING SAYS IT IS COMPLETE.**
  On a store-valid star-tupleset corpus under `WideWitness.SwT`, over a `175`-DISTINCT-query
  routing-independent grid (`25` answered TRUE by `sem`, so the grid is not vacuous):

  * the BRIDGE-FREE leg — `RulesWrite.lean::GraphState.writeRules`, the fold that
    `RulesComplete.lean::ReachedByRulesAdmitted.step` is actually stated over — mismatches
    `sem` on **6** queries (line (5));
  * the BRIDGED leg — `LeafRules.lean::GraphState.writeRulesRaw`, what part (ii) landed and
    what step 4′ proposes substituting — mismatches on **0** (line (5));
  * the CEILING (bridged, then `ensureInBridges` folded over EVERY node) also mismatches on
    **0**, so `0` is not merely the best this fold achieves, it is the best ANY amount of
    bridging could achieve on this grid (line (5));
  * the REGRESSION check is `[]` — the swap repairs six queries and breaks none (line (9)).

  So `§ Blockers` item 3's payoff, measured at one witness by the step-3 probe, holds over a
  grid: **6 → 0 of 175 distinct queries**, with no regression and nothing left on the table.
  ⚠ UNIT: `175` is DISTINCT queries; the raw generated list is `182` (line (13)).  The six
  repaired queries are exactly `{user:u, user:v, user:w} × {doc:d1, doc:d2} @ access` — i.e.
  every grant, through BOTH star parents, at the derived relation: the whole star-tupleset
  surface this corpus exposes, not a corner of it.

  ⚠ **CONTROL b had to change schema, and that is itself a finding.**  The first draft of
  this probe put a CONCRETE parent tuple (`folder:f3 → doc:d2#parent`) in a `SwT` store, as
  `p6_partiv_step3_rulerouted_2026-09-15.lean::tConc` does.  That store is **not store-valid**:
  `SwT` declares `doc#parent`'s restriction as `[folder:*]` — the WILDCARD form only — so a
  concrete folder subject satisfies no restriction.  Measured in
  `p6_partiv_stepC_diag_2026-09-15.lean`: `storeValidRulesB SwT [tConcPar] = false` (a1), and
  at such a tuple `sem = false` while `GraphModel.check = true` on BOTH legs (b2) — an
  apparent "divergence" that is nothing but the store-validity precondition being violated.
  It contaminated every leg equally and made CONTROL b read `4` instead of `0`.
  **The concrete-parent control belongs on `WideWitness.SwTn`**, the sibling witness that
  declares `[folder]` rather than `[folder:*]` (`TtuStarWide.lean:343`), which is what it now
  uses.  See `§ Provenance note` at the foot of this file for what this implies about the
  step-3 probe's own control.

  ── VERBATIM TRANSCRIPT (2026-09-15, rc=0) ────────────────────────────────────────────────

  ("(1) ★ widening engaged at the grid corpus: narrow / wide -- must be false, true", false, true)
  ("(2) ★ PRECONDITION -- bareStarStore / storeValidRules; a false here voids everything below", true, true)
  ("(3) ADMISSION -- every writeRules step admits; false makes the plain leg vacuous", true)
  ("(4) CONTROL b corpus on SwTn: storeValid / narrow ttuStarFree -- must be true, true", true, true)
  ("(5) ★ THE SWEEP -- star-tupleset store",
   { gridSize := 175, semTrue := 25, plainMismatch := 6, bridgedMismatch := 0, ceilMismatch := 0 })
  ("(6) ★ CONTROL b -- concrete parent on SwTn; plain/bridged/ceil must ALL be 0",
   { gridSize := 161, semTrue := 9, plainMismatch := 0, bridgedMismatch := 0, ceilMismatch := 0 })
  ("(7) queries the BRIDGE-FREE leg gets wrong",
   [user:u#... access doc:d1, user:v#... access doc:d1, user:w#... access doc:d1,
    user:u#... access doc:d2, user:v#... access doc:d2, user:w#... access doc:d2])
  ("(8) ★ queries the BRIDGED leg still gets wrong (ideally [])", [])
  ("(9) ★ REGRESSION CHECK -- wrong on BRIDGED but RIGHT on bridge-free; must be []", [])
  ("(10) queries the CEILING still gets wrong (bounds every write model)", [])
  ("(11) the in-bridge edge is ABSENT on the bridge-free leg / PRESENT on the bridged leg", false, true)
  ("(12) edge counts: bridge-free / bridged / ceiling", 7, 10, 10)
  ("(13) grid UNIT check -- distinct / raw; the counts above are DISTINCT", 175, 182)

  ⚠ Line (7) is abbreviated above for width; the run prints full `Query` records, and the
  six are exactly the three grants × the two star-parented docs at `access`.  Lines (8)/(9)/
  (10) print literally `[]`.

  ----------------------------------- END VERBATIM -----------------------------------------

  ⚠ CONTROLS, and what each rules out — read these BEFORE the numbers.

  This repo's house failure mode is an assurance step that fails by PASSING, and a grid is a
  rich source of them: a grid that compares nothing agrees perfectly.  Five controls, and the
  first three are what make `bridgedMismatch = 0` mean anything at all:

  * **(2) STORE VALIDITY, the PRECONDITION.**  Learned the hard way on this probe's own first
    run (see the ⚠ above).  An out-of-fragment store makes `sem` and `check` disagree for
    reasons that have nothing to do with the thing under test, on every leg at once.  A
    `false` at (2) voids every number below it.
  * **`semTrue` NON-VACUITY** — how many grid queries `sem` answers TRUE.  If this were `0`
    the grid would be uniformly False, both legs would agree trivially, and `0` mismatches
    would be meaningless.
  * **`plainMismatch` POSITIVE CONTROL (the INSTRUMENT)** — the bridge-free leg, i.e. the
    write model `ReachedByRulesAdmitted` is actually stated over.  This must be **NONZERO**:
    it is the gap step 4′ exists to close.  If it were `0`, the grid would never exercise the
    missing in-bridge and the bridged leg's `0` would not be a repair, it would be a grid
    that cannot see the defect.
  * **`ceilMismatch` CEILING CONTROL** — `P6` step 1's dual (2026-09-13b): the arm that does
    strictly MORE than the mechanism under test can.  Here: the bridged leg, then
    `ensureInBridges` folded over EVERY node in the state.  No write model can bridge more
    than that.  It separates *"`writeRulesRaw` is incomplete"* (`ceil < bridged`) from
    *"those queries were never reachable by bridging at all"* (`ceil = bridged`).  Here both
    are `0`, so the bridged fold is not merely better — on this grid it is optimal.
    ⚠ The ceiling deliberately reads `σ.nodes`, which every other arm here refuses to do
    (the grid is schema+corpus-derived, routing-independent).  That is sound *for a ceiling*
    — it is supposed to be maximal — but `ceilMismatch` is NOT a candidate write model, only
    a bound.
  * **(9) REGRESSION, the direction the counts hide.**  A net `3 → 0` would look identical if
    the swap had repaired five queries and broken two.  (9) asks the asymmetric question
    directly: which queries are wrong on the BRIDGED leg but right on the bridge-free one.
-/
import ZanzibarProofs

open Zanzibar

namespace P6PartIvStepCGrid

/-! ## §1 The subject — `TtuStarWide.lean::WideWitness.SwT`, reused by NAME (not copied)

`doc#access := viewer from parent`, tupleset `doc#parent` carrying the BARE wildcard
restriction `[folder:*]`, so `(folder, "viewer")` is a declared star-tupleset through-shape.
`WideWitness.narrow_rejects` / `::wide_admits` pin that the widening is engaged here.

⚠ `SwT` declares `doc#parent` as `[folder:*]` — the wildcard form ONLY.  A concrete folder
subject on `parent` is therefore NOT store-valid under this schema, which is why CONTROL b
lives on `SwTn` (§1b) instead.  This is the trap that broke the first run of this probe. -/

abbrev S : Schema := WideWitness.SwT

def tStarD1 : Tuple := WideWitness.twT                                      -- folder:* → doc:d1#parent
def tStarD2 : Tuple := ⟨⟨"folder", STAR, BARE⟩, "parent", ⟨"doc", "d2"⟩⟩    -- folder:* → doc:d2#parent
def gU      : Tuple := ⟨⟨"user", "u", BARE⟩, "viewer", ⟨"folder", "f1"⟩⟩
def gV      : Tuple := ⟨⟨"user", "v", BARE⟩, "viewer", ⟨"folder", "f2"⟩⟩
def gW      : Tuple := ⟨⟨"user", "w", BARE⟩, "viewer", ⟨"folder", "f3"⟩⟩

/-- The star-tupleset corpus: star parents on two docs, and three grants at three different
    folders.  Every tuple is store-valid under `SwT` — asserted at line (2), not assumed. -/
def corpus : List Tuple := [tStarD1, tStarD2, gU, gV, gW]

/-! ### §1b CONTROL b — the concrete tupleset parent, on the schema that ADMITS one

`TtuStarWide.lean:343::WideWitness.SwTn` is `SwT` with the one-restriction delta: `parent`
declares `[folder]` rather than `[folder:*]`.  It is the schema `::control_no_through_shape`
and `::unbridged_still_rejected` are stated over — i.e. the shape today's NARROW fragment
already covers.  A concrete parent is store-valid there, and both legs must agree. -/

abbrev Sc : Schema := WideWitness.SwTn

def tConcD1 : Tuple := ⟨⟨"folder", "f1", BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def tConcD2 : Tuple := ⟨⟨"folder", "f3", BARE⟩, "parent", ⟨"doc", "d2"⟩⟩

def corpusC : List Tuple := [tConcD1, tConcD2, gU, gV, gW]

/-! ## §2 Routing-independent domains — schema+corpus only, NEVER `σ.nodes`/`σ.edges`

Copied from `p6_partiv_live_leg_payoff_2026-09-14.lean` §2, which took them from
`p6_inbridge_stability_2026-09-12.lean`, with ONE addition: the grid is DEDUPLICATED.
`subjDomain` reaches the same subject by two routes (once from `subjsOf`, once from the
`objsOf × subjPreds` cross), so the raw list counts some queries twice.  Duplicates do not
change a mismatch *ratio* but they do inflate every absolute count, and this repo's standing
rule is that a figure without a stated unit is meaningless — so the unit here is DISTINCT
queries.  Line (13) reports the raw size alongside, so the two are never confused.

Deriving the grid from the STATE would let a leg that materialises fewer nodes be asked fewer
questions — the grid must not depend on the thing under test. -/

def subjPreds (S : Schema) : List String := BARE :: S.keys.map (·.2)

def objsOf (ts : List Tuple) : List ObjectRef :=
  ts.foldl (fun acc t => if acc.contains t.object then acc else acc ++ [t.object]) []

def subjsOf (ts : List Tuple) : List SubjectRef :=
  ts.foldl (fun acc t => if acc.contains t.subject then acc else acc ++ [t.subject]) []

def subjDomain (S : Schema) (ts : List Tuple) : List SubjectRef :=
  subjsOf ts ++ (wildcardShapes S).map starSubj
    ++ (objsOf ts).flatMap (fun o => (subjPreds S).map (fun p => ⟨o.type, o.name, p⟩))

def dedup (qs : List Query) : List Query :=
  qs.foldl (fun acc q => if acc.contains q then acc else acc ++ [q]) []

def queryGridRaw (S : Schema) (ts : List Tuple) : List Query :=
  S.keys.flatMap (fun k =>
    (objsOf ts).flatMap (fun o =>
      if o.type == k.1 then (subjDomain S ts).map (fun s => ⟨s, k.2, o⟩) else []))

def queryGrid (S : Schema) (ts : List Tuple) : List Query := dedup (queryGridRaw S ts)

def GRID  : List Query := queryGrid S corpus
def GRIDC : List Query := queryGrid Sc corpusC

/-! ## §3 The two write legs, plus the ceiling

`buildP` is `RulesComplete.lean::ReachedByRulesAdmitted`'s own step — a bridge-free
`RulesWrite.lean::GraphState.writeRules` fold.  `buildL` is part (ii)'s
`LeafRules.lean::GraphState.writeRulesRaw`, a `UsStarWrite.lean::GraphState.writeBridgedOne`
fold.  Step 4′ proposes swapping the first for the second at `CascadeStable.lean:3735`
(2026-09-15 line snapshot; the enclosing symbol is the durable anchor). -/

def buildP (S : Schema) : Store → GraphState
  | [] => emptyState S
  | t :: rest => (buildP S rest).writeRules S t

def buildL (S : Schema) : Store → GraphState
  | [] => emptyState S
  | t :: rest => (buildL S rest).writeRulesRaw S t

/-- THE CEILING: the bridged leg, then `ensureInBridges` at EVERY node in the state.
    `UsStarWrite.lean::GraphState.ensureInBridges` guards itself on `::bridgedInConcrete`, so
    folding it over all nodes is exactly "bridge everything that is bridgeable".  No write
    model can do more. -/
def buildCeil (S : Schema) (T : Store) : GraphState :=
  let σ := buildL S T
  σ.nodes.foldl (fun acc n => acc.ensureInBridges n) σ

/-- The admission side condition of EVERY `ReachedByRulesAdmitted.step`, conjoined. -/
def admitsAllPlain (S : Schema) : Store → Bool
  | [] => true
  | t :: rest => admitsAllPlain S rest && foldAdmitsB (buildP S rest) (rewriteClosure S t)

/-! ## §4 Preconditions — the widening is ENGAGED, and the store is IN the fragment -/

#eval ("(1) ★ widening engaged at the grid corpus: narrow / wide -- must be false, true",
        ttuStarFreeB S corpus, ttuStarFreeWB S corpus)
#eval ("(2) ★ PRECONDITION -- bareStarStore / storeValidRules; a false here voids everything below",
        bareStarStoreB corpus, storeValidRulesB S corpus)
#eval ("(3) ADMISSION -- every writeRules step admits; false makes the plain leg vacuous",
        admitsAllPlain S corpus)
#eval ("(4) CONTROL b corpus on SwTn: storeValid / narrow ttuStarFree -- must be true, true",
        storeValidRulesB Sc corpusC, ttuStarFreeB Sc corpusC)

/-! ## §5 ★ THE MEASUREMENT -/

structure Sweep where
  gridSize        : Nat   -- DISTINCT queries (see §2 on deduplication)
  semTrue         : Nat   -- NON-VACUITY: must be NONZERO
  plainMismatch   : Nat   -- ★ POSITIVE CONTROL / INSTRUMENT: must be NONZERO
  bridgedMismatch : Nat   -- ★ THE NUMBER
  ceilMismatch    : Nat   -- CEILING: bounds what any write model could achieve
deriving Repr

def missOn (S : Schema) (σ : GraphState) (T : Store) (G : List Query) : Nat :=
  (G.filter (fun q => !(GraphModel.check σ q == sem S T q))).length

def sweepOn (S : Schema) (T : Store) (G : List Query) : Sweep :=
  { gridSize        := G.length
    semTrue         := (G.filter (fun q => sem S T q)).length
    plainMismatch   := missOn S (buildP S T) T G
    bridgedMismatch := missOn S (buildL S T) T G
    ceilMismatch    := missOn S (buildCeil S T) T G }

#eval ("(5) ★ THE SWEEP -- star-tupleset store", sweepOn S corpus GRID)
#eval ("(6) ★ CONTROL b -- concrete parent on SwTn; plain/bridged/ceil must ALL be 0",
        sweepOn Sc corpusC GRIDC)

/-! ## §6 WHERE they disagree — a count is not a diagnosis

If `plainMismatch` is nonzero these are the queries it gets wrong, and if `bridgedMismatch`
is nonzero these are the ones the swap does NOT repair.  Listing them is what distinguishes
"the bridged leg repairs the star-tupleset gap" from "it repairs a different set and breaks
some the plain leg got right" — a net count of `3 → 0` would hide the latter entirely, which
is what line (9) exists to refuse. -/

def whichOn (S : Schema) (σ : GraphState) (T : Store) (G : List Query) : List Query :=
  G.filter (fun q => !(GraphModel.check σ q == sem S T q))

#eval ("(7) queries the BRIDGE-FREE leg gets wrong", whichOn S (buildP S corpus) corpus GRID)
#eval ("(8) ★ queries the BRIDGED leg still gets wrong (ideally [])",
        whichOn S (buildL S corpus) corpus GRID)
#eval ("(9) ★ REGRESSION CHECK -- wrong on BRIDGED but RIGHT on bridge-free; must be []",
        (whichOn S (buildL S corpus) corpus GRID).filter
          (fun q => !((whichOn S (buildP S corpus) corpus GRID).contains q)))
#eval ("(10) queries the CEILING still gets wrong (bounds every write model)",
        whichOn S (buildCeil S corpus) corpus GRID)

/-! ## §7 The bridge itself — is the swap doing what we think?

A mismatch count can move for reasons unrelated to bridging.  These lines pin that the
bridged leg really does materialise the in-bridge that the step-3 probe's line (8) had to add
by hand, and that the bridge-free leg really does not. -/

def cNode : NodeKey := ⟨"folder", "f1", "viewer", Variant.plain⟩

#eval ("(11) the in-bridge edge is ABSENT on the bridge-free leg / PRESENT on the bridged leg",
        ((buildP S corpus).edges.contains (cNode, wAnyNode ("folder", "viewer"))),
        ((buildL S corpus).edges.contains (cNode, wAnyNode ("folder", "viewer"))))
#eval ("(12) edge counts: bridge-free / bridged / ceiling",
        (buildP S corpus).edges.length,
        (buildL S corpus).edges.length,
        (buildCeil S corpus).edges.length)
#eval ("(13) grid UNIT check -- distinct / raw; the counts above are DISTINCT",
        GRID.length, (queryGridRaw S corpus).length)

/-! ## §8 Provenance note — what this implies about the step-3 probe's own CONTROL b

`p6_partiv_step3_rulerouted_2026-09-15.lean::tConc` is a concrete parent tuple in a `SwT`
store (`::Tc`), and that probe's lines (6)/(13)/(16) use it as CONTROL b.  By (a1) of
`p6_partiv_stepC_diag_2026-09-15.lean` that store is **not store-valid** under `SwT`.

This does NOT overturn the step-3 probe's finding, and the distinction matters:

* Its (5) — the refutation — is measured on the STAR store `T`, whose validity that probe
  asserts at its own line (2).  Unaffected.
* Its CONTROL b lines asked only the DERIVED query `user:u ∈ doc:d1#access`.  The
  store-validity violation shows up on queries about the tupleset relation `doc#parent`
  itself (diag (b2)); at the derived query, diag (b3) gives `sem = check = true` on both
  legs.  So the control's verdict — "the encoding is not simply broken" — still holds.
* But it holds for a weaker reason than it appears to: the control store is outside the
  precondition its own theorem assumes, so it attributes the divergence to the star parent
  only for the one query it asks.  A control on `SwTn`, as used here, is the stronger form.

⚠ Recorded rather than silently fixed, per this repo's rule that a probe is evidence and
evidence is not edited after the fact.  The step-3 probe is left as it ran.
-/

end P6PartIvStepCGrid
