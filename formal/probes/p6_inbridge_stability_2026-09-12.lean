/-
  ★ P6 / increment-B ATTACK-FIRST PROBE (designed 2026-09-12) — does an in-bridge on the
  LEAF-ROUTED write leg make the write-leg STABILITY theorems FALSE, or only in need of a
  new premise?  Decided for ALL THREE TIERS.

  Kept OUTSIDE the lake package on purpose (same reason as
  `d3_negedgefree_postflip_2026-09-05.lean:3-5`): it costs ZERO cone, it is not part of the
  gated build, it is evidence that can be re-run.  Run from formal/lean (needs the built
  oleans):

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_inbridge_stability_2026-09-12.lean

  ⚠ Expect tens of seconds: the sweeps are ~1k `GraphState.reach` calls per arm over eight
  arms, plus two `cascadeLeg`s and a `sem` grid.  rc=0 with no output means a `#eval`
  silently elaborated to `()` — that is a FAILED run, not a green one.

  ── LITERAL TRANSCRIPT (paste the run's own output here; do not paraphrase) ───────────────

  RAN 2026-09-12 by the designated Probe agent, rc=0, 335 lines, re-run byte-identical
  after one lint fix.  Command: `export PATH="$HOME/.elan/bin:$PATH" && cd formal/lean &&
  lake env lean ../probes/p6_inbridge_stability_2026-09-12.lean`.  Everything between the
  rules below is the VERBATIM stdout: nothing added, removed, reordered or re-indented.

  ---------------------------------- BEGIN VERBATIM ----------------------------------------

("DOMAINS (subjects, semSubjects, nodes, derivedKeys, grid)", 42, 42, 144, 4, 546)
("DERIVED KEYS PROBED", [("doc", "admin", "d1"), ("doc", "admin", "d2"), ("doc", "gate", "d1"), ("doc", "gate", "d2")])
("BRIDGED-IN SHAPE (folder,viewer): (isSubjectWildcardUserset, isStarTuplesetThrough)", true, true)
("CONTROL - BARE pred is excluded (must be false)", false)
("NARROW rejects / WIDE admits the prefix store", some (false, true))
("PREFIX drained? / PREFIX edges",
 some (true,
  [({ type := "user", name := "alice", pred := "...", variant := Zanzibar.Variant.plain },
    { type := "folder", name := "f1", pred := "viewer", variant := Zanzibar.Variant.plain }),
   ({ type := "folder", name := "*", pred := "viewer", variant := Zanzibar.Variant.wAny },
    { type := "doc", name := "d1", pred := "gate.0", variant := Zanzibar.Variant.plain }),
   ({ type := "folder", name := "*", pred := "viewer", variant := Zanzibar.Variant.wAny },
    { type := "doc", name := "d1", pred := "admin.0", variant := Zanzibar.Variant.plain }),
   ({ type := "folder", name := "*", pred := "viewer", variant := Zanzibar.Variant.wAny },
    { type := "doc", name := "d1", pred := "access", variant := Zanzibar.Variant.plain }),
   ({ type := "folder", name := "*", pred := "...", variant := Zanzibar.Variant.wAny },
    { type := "doc", name := "d1", pred := "parent", variant := Zanzibar.Variant.plain })]))
("rewriteClosureL (tObj)",
 [{ subject := { type := "user", name := "bob", predicate := "..." },
    relation := "viewer",
    object := { type := "folder", name := "f2" } }])
("rewriteClosureL (tSub)",
 [{ subject := { type := "folder", name := "f1", predicate := "viewer" },
    relation := "banned",
    object := { type := "doc", name := "d2" } },
  { subject := { type := "folder", name := "f1", predicate := "viewer" },
    relation := "admin.1",
    object := { type := "doc", name := "d2" } }])
("HAZARD",
 some [{ arm := "prefix σ0 (drained)",
    bridgeFired := 0,
    aliceReach := false,
    bobReach := false,
    cKeys := [],
    hazardUnmapped := true },
  { arm := "BASE", bridgeFired := 0, aliceReach := false, bobReach := false, cKeys := [], hazardUnmapped := true },
  { arm := "B-OBJ",
    bridgeFired := 1,
    aliceReach := false,
    bobReach := true,
    cKeys := [("doc", "admin", "d1"), ("doc", "gate", "d1")],
    hazardUnmapped := false },
  { arm := "BASE-S",
    bridgeFired := 0,
    aliceReach := false,
    bobReach := false,
    cKeys := [("doc", "admin", "d2"), ("doc", "admin", "d2")],
    hazardUnmapped := true },
  { arm := "B-SUB",
    bridgeFired := 2,
    aliceReach := true,
    bobReach := false,
    cKeys := [("doc", "admin", "d2"), ("doc", "admin", "d2")],
    hazardUnmapped := true },
  { arm := "B-SUB-L",
    bridgeFired := 2,
    aliceReach := true,
    bobReach := false,
    cKeys := [("doc", "admin", "d2"),
              ("doc", "admin", "d2"),
              ("doc", "admin", "d1"),
              ("doc", "gate", "d1"),
              ("doc", "admin", "d2"),
              ("doc", "admin", "d2"),
              ("doc", "admin", "d1"),
              ("doc", "gate", "d1")],
    hazardUnmapped := false }])
("P6 PROBE",
 some [{ name := "BASE (plain live leg, tObj)",
    vac := { edges := 6,
             legEdges := 6,
             bridges := 0,
             frontier := 1,
             ckeys := 0,
             keys := 4,
             unmapped := 4,
             reachPairs := 1152,
             guardPairs := 168 },
    t1 := { reachStable := true,
            reachStableAll := true,
            wAllDead := true,
            graphRecStable := true,
            checkFnStable := true },
    t2 := { semEq := false,
            guardPre := false,
            guardPost := false,
            rowsFixed := true,
            inEdgesFixed := true,
            ops2Tested := 2,
            ops2Unmapped := true },
    t3 := { filtNonTrivial := true,
            semFiltEq := true,
            checkFnMatched := true,
            checkFnRStable := true,
            checkFnRTested := 168 },
    hazardUnmapped := true,
    hazardReachPre := false,
    hazardReachPost := false,
    verdict := "GREEN  - every tier instrument survives this routing" },
  { name := "NULL (plain leg + ensureInBridges at a NON-bridged node)",
    vac := { edges := 6,
             legEdges := 6,
             bridges := 0,
             frontier := 1,
             ckeys := 0,
             keys := 4,
             unmapped := 4,
             reachPairs := 1152,
             guardPairs := 168 },
    t1 := { reachStable := true,
            reachStableAll := true,
            wAllDead := true,
            graphRecStable := true,
            checkFnStable := true },
    t2 := { semEq := false,
            guardPre := false,
            guardPost := false,
            rowsFixed := true,
            inEdgesFixed := true,
            ops2Tested := 2,
            ops2Unmapped := true },
    t3 := { filtNonTrivial := true,
            semFiltEq := true,
            checkFnMatched := true,
            checkFnRStable := true,
            checkFnRTested := 168 },
    hazardUnmapped := true,
    hazardReachPre := false,
    hazardReachPost := false,
    verdict := "GREEN  - every tier instrument survives this routing" },
  { name := "POS  (plain leg + RAW unlogged edge into doc:d1#access)",
    vac := { edges := 7,
             legEdges := 6,
             bridges := 1,
             frontier := 1,
             ckeys := 0,
             keys := 4,
             unmapped := 4,
             reachPairs := 1152,
             guardPairs := 168 },
    t1 := { reachStable := false,
            reachStableAll := false,
            wAllDead := true,
            graphRecStable := false,
            checkFnStable := false },
    t2 := { semEq := false,
            guardPre := false,
            guardPost := false,
            rowsFixed := true,
            inEdgesFixed := true,
            ops2Tested := 2,
            ops2Unmapped := true },
    t3 := { filtNonTrivial := true,
            semFiltEq := true,
            checkFnMatched := false,
            checkFnRStable := false,
            checkFnRTested := 168 },
    hazardUnmapped := true,
    hazardReachPre := false,
    hazardReachPost := false,
    verdict := "FALSE  - unstable AND ('doc','admin','d1') is UNMAPPED: no premise on (dt,R,on) saves the statement" },
  { name := "B-OBJ  (bridge on the leaf-routed OBJECT endpoint, unlogged)",
    vac := { edges := 7,
             legEdges := 6,
             bridges := 1,
             frontier := 1,
             ckeys := 2,
             keys := 4,
             unmapped := 2,
             reachPairs := 576,
             guardPairs := 84 },
    t1 := { reachStable := true,
            reachStableAll := false,
            wAllDead := true,
            graphRecStable := true,
            checkFnStable := true },
    t2 := { semEq := false,
            guardPre := false,
            guardPost := false,
            rowsFixed := true,
            inEdgesFixed := true,
            ops2Tested := 1,
            ops2Unmapped := true },
    t3 := { filtNonTrivial := true,
            semFiltEq := true,
            checkFnMatched := true,
            checkFnRStable := true,
            checkFnRTested := 84 },
    hazardUnmapped := false,
    hazardReachPre := false,
    hazardReachPost := false,
    verdict := "GREEN  - every tier instrument survives this routing" },
  { name := "B-BOTH (bridge on BOTH leaf-routed endpoints, unlogged)",
    vac := { edges := 7,
             legEdges := 6,
             bridges := 1,
             frontier := 1,
             ckeys := 2,
             keys := 4,
             unmapped := 2,
             reachPairs := 576,
             guardPairs := 84 },
    t1 := { reachStable := true,
            reachStableAll := false,
            wAllDead := true,
            graphRecStable := true,
            checkFnStable := true },
    t2 := { semEq := false,
            guardPre := false,
            guardPost := false,
            rowsFixed := true,
            inEdgesFixed := true,
            ops2Tested := 1,
            ops2Unmapped := true },
    t3 := { filtNonTrivial := true,
            semFiltEq := true,
            checkFnMatched := true,
            checkFnRStable := true,
            checkFnRTested := 84 },
    hazardUnmapped := false,
    hazardReachPre := false,
    hazardReachPost := false,
    verdict := "GREEN  - every tier instrument survives this routing" },
  { name := "BASE-S (plain live leg, tSub)",
    vac := { edges := 7,
             legEdges := 7,
             bridges := 0,
             frontier := 2,
             ckeys := 2,
             keys := 4,
             unmapped := 3,
             reachPairs := 864,
             guardPairs := 126 },
    t1 := { reachStable := true,
            reachStableAll := false,
            wAllDead := true,
            graphRecStable := true,
            checkFnStable := true },
    t2 := { semEq := true,
            guardPre := false,
            guardPost := false,
            rowsFixed := true,
            inEdgesFixed := true,
            ops2Tested := 2,
            ops2Unmapped := false },
    t3 := { filtNonTrivial := true,
            semFiltEq := true,
            checkFnMatched := true,
            checkFnRStable := true,
            checkFnRTested := 126 },
    hazardUnmapped := true,
    hazardReachPre := false,
    hazardReachPost := false,
    verdict := "GREEN  - every tier instrument survives this routing" },
  { name := "B-SUB  (bridge on the leaf-routed SUBJECT endpoint, unlogged)",
    vac := { edges := 9,
             legEdges := 7,
             bridges := 2,
             frontier := 2,
             ckeys := 2,
             keys := 4,
             unmapped := 3,
             reachPairs := 864,
             guardPairs := 126 },
    t1 := { reachStable := false,
            reachStableAll := false,
            wAllDead := true,
            graphRecStable := false,
            checkFnStable := false },
    t2 := { semEq := true,
            guardPre := false,
            guardPost := false,
            rowsFixed := true,
            inEdgesFixed := true,
            ops2Tested := 2,
            ops2Unmapped := false },
    t3 := { filtNonTrivial := true,
            semFiltEq := true,
            checkFnMatched := false,
            checkFnRStable := false,
            checkFnRTested := 126 },
    hazardUnmapped := true,
    hazardReachPre := false,
    hazardReachPost := true,
    verdict := "FALSE  - unstable AND ('doc','admin','d1') is UNMAPPED: no premise on (dt,R,on) saves the statement" },
  { name := "B-SUB-L(bridge on the SUBJECT endpoint, bridge source LOGGED)",
    vac := { edges := 9,
             legEdges := 7,
             bridges := 2,
             frontier := 4,
             ckeys := 8,
             keys := 4,
             unmapped := 1,
             reachPairs := 288,
             guardPairs := 42 },
    t1 := { reachStable := true,
            reachStableAll := false,
            wAllDead := true,
            graphRecStable := true,
            checkFnStable := true },
    t2 := { semEq := true,
            guardPre := false,
            guardPost := false,
            rowsFixed := true,
            inEdgesFixed := true,
            ops2Tested := 1,
            ops2Unmapped := false },
    t3 := { filtNonTrivial := true,
            semFiltEq := true,
            checkFnMatched := true,
            checkFnRStable := true,
            checkFnRTested := 42 },
    hazardUnmapped := false,
    hazardReachPre := false,
    hazardReachPost := true,
    verdict := "GREEN  - every tier instrument survives this routing" }])
("REPAIR",
 some { gridSize := 546,
   baseDrained := true,
   bridgeDrained := true,
   baseAgree := false,
   baseMismatch := 14,
   bridgedAgree := false,
   bridgedMismatch := 9 })
("ROUTING (leaf-routed vs public-keyed)",
 { derivedKey := true,
   rawRels := ["approver.0"],
   throughShapeDeclared := true,
   publicBridged := true,
   leafBridged := false,
   legEdges := 1,
   legEdgesIntoPublic := 0,
   legEdgesIntoLeaf := 1,
   bridgesOnLeafRouted := 0,
   bridgesOnPublicKeyed := 1 })

  ----------------------------------- END VERBATIM -----------------------------------------

  ── WHAT IS BEING DECIDED ────────────────────────────────────────────────────────────────

  `UsStarWrite.lean:213 GraphState.ensureInBridges` is proved (`:274 structInv_ensureInBridges`,
  `:256 ensureInBridges_mono`, `:238 ensureInBridges_schema`) and `:112` says outright "no
  live chain calls `ensureInBridges` yet".  Increment B ROUTES it into the live post-flip
  write leg `Cascade.lean:190-191 GraphState.writeLoggedRules`
  (`(rewriteClosureL S (rawWriteTuples S t)).foldl writeLoggedOne`).

  Every write-leg stability theorem in all three tiers is stated at an UNMAPPED key —
  `hunmapped : (dt, R, on) ∉ cascadeKeys S (σ.writeLoggedRules S t)`
  (`CascadeStable.lean:367`).  So each arm has exactly three possible outcomes, and this
  probe computes which one, mechanically, in `verdictOf`:

    * instrument still holds                       → GREEN   (no hazard at this routing)
    * instrument breaks, hazard key is MAPPED       → PREMISE (hunmapped already excludes it;
                                                      the STATEMENT survives, the PROOF's
                                                      `nreaches_factor` step needs a new
                                                      "new edges are routed-or-bridged" lemma)
    * instrument breaks, hazard key is UNMAPPED     → FALSE   (no premise on (dt,R,on) can
                                                      save the statement; the repair must be
                                                      an invariant/fence, or the bridge must
                                                      emit a delta)

  You cannot `#eval` a theorem, so each tier is represented by the COMPUTABLE CONTENT its
  theorem asserts is stable, at the specific keys:

    tier 1 (`CascadeStable.lean` writeLeg_reach_stable :362, writeLeg_reach_wAll_false :417,
            writeLeg_graphRec_stable :444, writeLeg_checkFn_stable :467)
            → `GraphState.reach` into `objNode ⟨dt,on⟩ r'`, `reach` into `wAllNode dt r'`,
              `GraphModel.graphRec`, `GraphState.checkFn`.
    tier 2 (`CascadeStable.lean` writeLeg_sem_stable :2066, settledKey_writeLeg :2134;
            `CascadeStrataSettle.lean` writeLeg_sem_stable_sh :2521,
            settledKey_writeLeg_sem :2564, completeKey_writeLeg_sem :2607,
            writeLeg_sem_stable2 :2651)
            → ⚠ the CONCLUSION `sem S (t::T) q = sem S T q` is σ-INDEPENDENT, so it cannot
              go red from an edge; reporting it alone would be a probe that passes for free.
              The load-bearing content is the MIDDLE of the calc: the W3d read bridge
              `σ'.checkFn (t::T) = sem S (t::T)` (`guardPost`) and its pre-write twin
              (`guardPre`), plus the two structural transports the settledness lemmas use
              (`writeLoggedRules_residue` → `rowsFixed`;
              `writeLeg_derived_inedges_eq` → `inEdgesFixed`), plus `writeLeg_sem_stable2`'s
              extra premise `hopsUnmapped` on the derived operand key (`ops2Unmapped`).
    tier 3 (`CascadeStrataSettle.lean` writeLeg_sem_stable_sh_d :4768,
            settledKey_writeLeg_sem_d :4859, completeKey_writeLeg_sem_d :4904,
            writeLeg_sem_stable2_d :5051)
            → the `_d` family's two distinguishing features: the shadow sits at the
              UNTAINTED-FILTERED store (`T.filter (fun tp => !isDerived S (tp.object.type,
              tp.relation))`, admitting a stored DERIVED-relation tuple under
              `StoreValidRulesD`), and the recursion is the ROUTED
              `CascadeStrata.lean:113 GraphState.checkFnR` / `:97 GraphModel.graphRecR`.
              So tier 3 measures `checkFnR` stability at the store-MATCHED form plus
              `sem`-through-the-filter, not a re-run of tier 1.

  ── (!) THE WITNESS TRAP (scope doc S9.1; template :46-48) ────────────────────────────────

  Every domain below is ROUTING-INDEPENDENT: built from the CORPUS tuples' objects/subjects
  and the SCHEMA's declared relations (bare and at leaf indices 0/1), NEVER from `σ.nodes`
  and never from `σ.edges`.  A leaf-routed write and a bridge both CHANGE `σ.nodes`, so a
  σ-derived domain would measure nothing.  `Vac.reachPairs` / `Vac.guardPairs` /
  `Vac.keys` / `Vac.unmapped` are the non-vacuity numbers: a green sweep with
  `unmapped = 0` is VACUOUS, and `Tier1.reachStableAll` (over ALL probed keys, mapped
  included) is printed beside `Tier1.reachStable` (unmapped keys only) precisely so a
  vacuous green is visible as `reachStable = true, reachStableAll = false`.

  ── THE ARMS ─────────────────────────────────────────────────────────────────────────────

  All arms share the DRAINED prefix state σ0 = graphRunOps Sp [add tPar, add tView].

    (BASE)     plain live leg, no bridge.  MUST be green on every tier instrument — it is
               the landed, proved configuration.  A red here invalidates the whole probe.
    (NULL)     plain leg + `ensureInBridges` at a node that is NOT a declared bridged-in
               shape.  MUST add 0 edges and stay green: the INSTRUMENT control for the
               harness's own `ensureInBridges` wiring (an arm that reddened because the
               harness perturbs state would be a mutation dying of the wrong cause).
    (POS)      plain leg + one RAW unlogged edge straight into the operand node
               `doc:d1#access`.  MUST be RED with `hazardUnmapped = true`.  If this reads
               green the instrument is BLIND and nothing else in the file means anything.
    (B-OBJ)    increment B routed on the leaf-routed list, bridge at the OBJECT endpoint
               (`folder:f2#viewer`).  PREDICTION: unstable, key MAPPED → "PREMISE".
    (B-SUB)    increment B routed on the leaf-routed list, bridge at the SUBJECT endpoint
               (`folder:f1#viewer`, a stored userset subject).  PREDICTION: unstable, key
               UNMAPPED → "FALSE".  The delta row sits at the OBJECT node, whose reach cone
               (`Cascade.lean:485 affectedObjects`) runs DOWNSTREAM and therefore never sees
               an upstream subject-side bridge.
    (B-SUB-L)  same, with the bridge SOURCE logged (`pushDelta c c.pred true`).  PREDICTION:
               unstable, key MAPPED → "PREMISE".  This is the candidate REPAIR: if B-SUB is
               FALSE and B-SUB-L is PREMISE, increment B's design answer is "bridges emit a
               delta at their concrete source", and all 23 at-risk theorems keep their
               statements.
    (B-BOTH)   both endpoints bridged, unlogged — the naive composition, for completeness.

  A separate section (`Routing`) measures the CRITICAL CONSTRAINT on a second, tiny schema
  `Sd`: the bridge must be materialised on the LEAF-ROUTED list, never keyed on the public
  relation name (`formal/history/PROOF_STATUS.md` sec 3 at :392-411, NOT sec 2).  It reports
  as numbers, not prose: `legEdgesIntoLeaf` vs `legEdgesIntoPublic` (post-flip the public
  node has ZERO write-leg in-edges), and `bridgesOnLeafRouted` vs `bridgesOnPublicKeyed`.
  ⚠ If `bridgesOnLeafRouted = 0` while `bridgesOnPublicKeyed = 1`, then routing
  `ensureInBridges` through the leaf-routed list does NOT inhabit `ttuStarFree` for a
  DERIVED through-shape at all — the minted leaf name `approver.0` is not a declared shape
  — and increment B's scope is strictly narrower than "route the existing machinery".

  ── THE REPAIR MEASUREMENT (the P6 payoff, and a second positive control) ─────────────────

  `Repair` cascades BASE and B-OBJ to drained and compares `GraphModel.check` against `sem`
  over a routing-independent query grid.  On the star-tupleset store the UNBRIDGED model is
  machine-checked WRONG (`formal/history/PROOF_STATUS.md` 2026-08-10; `TtuStarWide.lean:32-39`),
  so `baseAgree` MUST be false.  If `baseAgree` reads true the store is not in the
  newly-admitted region and the schema below is wrong.  `bridgedAgree = true` is the
  evidence that the bridge does the job increment B exists for.

  Non-vacuity of the region itself is pinned by `ttuStarFreeB Sp T = false` (narrow rejects)
  and `ttuStarFreeWB Sp T = true` (wide admits) — `TtuStarWide.lean:247/251`'s witness shape.

  ⚠ The change is INERT on all 26 `corpus.SCHEMAS`, so the ten-phase gate CANNOT see it
  (`docs/sabotage-procedure.md`, "The INERT change").  Whatever this probe finds must land
  as NEW LEAN PINS in a tracked file the same hour, not as a `.scratch/` log.
-/
import ZanzibarProofs

open Zanzibar

namespace P6BridgeProbe

/-! ## §1  The schema — a star-tupleset through-shape over a two-stratum boolean fragment

`(folder, "viewer")` is a declared subject-wildcard userset shape through disjunct (b)
(`UsStarWrite.lean:115 Schema.isSubjectWildcardUserset` → `:89 Schema.isStarTuplesetThrough`):
`doc#access := viewer from parent` is a TTU whose tupleset `doc#parent` carries the BARE
wildcard restriction `[folder:*]`.  This is `TtuStarWide.lean:225 WideWitness.SwT`'s shape,
extended with the boolean fragment the stability theorems quantify over:

* `doc#admin := access but not banned`  — DERIVED, `ComputedOnly`, operands UNTAINTED
  (stratum 1: `writeLeg_sem_stable` / `settledKey_writeLeg` / the `_sh` and `_d` clones);
* `doc#gate  := admin and access`       — DERIVED, reads a DERIVED operand
  (stratum 2: `writeLeg_sem_stable2`'s `hopsUnmapped` / `hopsSettled`).

Every wildcard restriction is BARE-predicated, so `hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE`
holds; no TTU targets a derived relation, so `hterm`'s `NoTtuTarget` holds; no object
wildcards, so this is not the I14 shape. -/
def Sp : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, true)]),
    (("doc", "access"),    .ttu "viewer" "parent"),
    (("doc", "banned"),    .direct [("user", BARE, false), ("folder", "viewer", false)]),
    (("doc", "admin"),     .excl (.computed "access") (.computed "banned")),
    (("doc", "gate"),      .inter (.computed "admin") (.computed "access"))], []⟩

/-- The stored STAR tupleset parent — the tuple today's `TtuStarFree` forbids and the
    widened `TtuStarFreeW` admits. -/
def tPar : Tuple := ⟨⟨"folder", STAR, BARE⟩, "parent", ⟨"doc", "d1"⟩⟩

/-- The concrete folder grant.  Its object endpoint `folder:f1#viewer` is the bridged-in
    concrete node; `alice` reaches it, and (only through the in-bridge) `doc:d1#access`. -/
def tView : Tuple := ⟨⟨"user", "alice", BARE⟩, "viewer", ⟨"folder", "f1"⟩⟩

/-- Scenario OBJ's probe write: the bridged-in shape is the write's OBJECT endpoint. -/
def tObj : Tuple := ⟨⟨"user", "bob", BARE⟩, "viewer", ⟨"folder", "f2"⟩⟩

/-- Scenario SUB's probe write: the bridged-in shape is the write's SUBJECT endpoint —
    a stored userset subject.  Admission-valid: `doc#banned` declares `[folder#viewer]`. -/
def tSub : Tuple := ⟨⟨"folder", "f1", "viewer"⟩, "banned", ⟨"doc", "d2"⟩⟩

/-- Tier 3 only: a stored DERIVED-relation tuple, so the `_d` family's untainted FILTER is
    non-trivial (`StoreValidRulesD` admits it; `StoreValidRules` does not). -/
def tAdm : Tuple := ⟨⟨"user", "dave", BARE⟩, "admin", ⟨"doc", "d1"⟩⟩

/-- Domain-only: never written, never stored.  Present so `carol` and `folder:f9` are in the
    routing-independent domains and the POS control's raw edge has a source in them. -/
def tDom : Tuple := ⟨⟨"user", "carol", BARE⟩, "viewer", ⟨"folder", "f9"⟩⟩

def corpus : List Tuple := [tPar, tView, tObj, tSub, tAdm, tDom]

def prefixOps : List GraphOp := [GraphOp.add tPar, GraphOp.add tView]

/-! ## §2  The routing-independent domains  (!) NEVER `σ.nodes`, NEVER `σ.edges` -/

/-- Subject-side predicates: bare, plus every DECLARED relation.  Schema-only. -/
def subjPreds (S : Schema) : List String := BARE :: S.keys.map (·.2)

/-- Object-side predicates: every declared relation, bare and at leaf indices 0/1 — the
    minted `<R>.<i>` names the post-flip leg actually addresses.  Schema-only. -/
def objPreds (S : Schema) : List String :=
  S.keys.flatMap (fun k => [k.2, leafPred k.2 0, leafPred k.2 1])

def objsOf (ts : List Tuple) : List ObjectRef :=
  ts.foldl (fun acc t => if acc.contains t.object then acc else acc ++ [t.object]) []

def subjsOf (ts : List Tuple) : List SubjectRef :=
  ts.foldl (fun acc t => if acc.contains t.subject then acc else acc ++ [t.subject]) []

/-- Corpus subjects, the schema's declared star subjects, and every
    (corpus object × declared predicate) userset subject. -/
def subjDomain (S : Schema) (ts : List Tuple) : List SubjectRef :=
  subjsOf ts ++ (wildcardShapes S).map starSubj
    ++ (objsOf ts).flatMap (fun o => (subjPreds S).map (fun p => ⟨o.type, o.name, p⟩))

/-- The `x` of `writeLeg_reach_stable` ranges over ALL of `NodeKey`, so the node domain is
    broad: subject nodes, object nodes at bare AND leaf predicates, and every declared
    `w_any` / `w_all`. -/
def nodeDomain (S : Schema) (ts : List Tuple) : List NodeKey :=
  (subjDomain S ts).map subjNode
    ++ (objsOf ts).flatMap (fun o => (objPreds S).map (fun p => objNode o p))
    ++ S.keys.map (fun k => wAnyNode (k.1, k.2))
    ++ S.keys.map (fun k => wAllNode k.1 k.2)

/-- A derived key the tiers quantify over, carrying its `Expr` so `checkFn` is callable. -/
structure DKey where
  dt : String
  R : String
  on : String
  e : Expr
deriving Repr, Inhabited

/-- Declared DERIVED keys × corpus object names of the matching type, `on ≠ STAR`
    (`hon` in every tier).  Schema + corpus only. -/
def dkeys (S : Schema) (ts : List Tuple) : List DKey :=
  S.defs.flatMap (fun d =>
    if isDerived S d.1 then
      (objsOf ts).filterMap (fun o =>
        if o.type == d.1.1 && o.name != STAR then some ⟨d.1.1, d.1.2, o.name, d.2⟩ else none)
    else [])

def SUBS : List SubjectRef := subjDomain Sp corpus
/-- `hs : s.name = STAR → s.predicate = BARE` — the scope of every `sem`-level tier. -/
def SEMSUBS : List SubjectRef := SUBS.filter (fun s => !(s.name == STAR) || (s.predicate == BARE))
def NODES : List NodeKey := nodeDomain Sp corpus
def KEYS : List DKey := dkeys Sp corpus

/-! ## §3  The write legs — the LIVE post-flip leg, and increment B's candidate routings -/

/-- Bridge-before-grant at one endpoint, `UsStarWrite.lean:228 writeUsStar`'s order: the
    endpoint must be live before `ensureInBridges` (its docstring's precondition). -/
def bridgeAt (σ : GraphState) (c : NodeKey) : GraphState := (σ.addNode c).ensureInBridges c

/-- Increment B, candidate routing: bridge the endpoints of every member of the LEAF-ROUTED
    list, then the logged grant.  `bs` bridges the subject endpoint, `bo` the object
    endpoint, `logBridge` emits a delta at a bridge SOURCE that actually fired. -/
def legB (S : Schema) (bs bo logBridge : Bool) (σ : GraphState) (t : Tuple) : GraphState :=
  (rewriteClosureL S (rawWriteTuples S t)).foldl
    (fun acc u =>
      let a := subjNode u.subject
      let b := objNode u.object u.relation
      let acc1 := if bs then
                    (if (acc.addNode a).bridgedInConcrete a then
                       (if logBridge then (bridgeAt acc a).pushDelta a a.pred true
                        else bridgeAt acc a)
                     else acc)
                  else acc
      let acc2 := if bo then
                    (if (acc1.addNode b).bridgedInConcrete b then
                       (if logBridge then (bridgeAt acc1 b).pushDelta b b.pred true
                        else bridgeAt acc1 b)
                     else acc1)
                  else acc1
      acc2.writeLoggedOne u) σ

/-! ## §4  The per-tier instruments -/

structure Vac where
  edges       : Nat   -- |σ'.edges|
  legEdges    : Nat   -- |plain-leg edges| — what the live leg alone adds
  bridges     : Nat   -- |σ'.edges| − |plain-leg edges| — the bridge count, MUST be > 0 in B-*
  frontier    : Nat   -- |σ'.frontierRows| — the rows `cascadeKeys` folds over
  ckeys       : Nat   -- |cascadeKeys Sp σ'|
  keys        : Nat   -- |KEYS| probed
  unmapped    : Nat   -- how many are UNMAPPED in σ' — a green sweep at 0 is VACUOUS
  reachPairs  : Nat
  guardPairs  : Nat
deriving Repr

structure Tier1 where
  reachStable    : Bool  -- writeLeg_reach_stable, restricted to UNMAPPED keys
  reachStableAll : Bool  -- …over ALL probed keys: green+red here = "the bridge mapped the key"
  wAllDead       : Bool  -- writeLeg_reach_wAll_false
  graphRecStable : Bool  -- writeLeg_graphRec_stable
  checkFnStable  : Bool  -- writeLeg_checkFn_stable  (ONE store, both sides)
deriving Repr

structure Tier2 where
  semEq        : Bool  -- the CONCLUSION; σ-independent, so arm-invariant BY CONSTRUCTION
  guardPre     : Bool  -- σ.checkFn T  = sem S T        (checkFn_eq_sem_w3d, right end)
  guardPost    : Bool  -- σ'.checkFn T'= sem S T'       (checkFn_eq_sem_w3d, left end)
  rowsFixed    : Bool  -- writeLoggedRules_residue
  inEdgesFixed : Bool  -- writeLeg_derived_inedges_eq
  ops2Tested   : Nat   -- (key, DERIVED operand) pairs — 0 ⇒ stratum 2 is VACUOUS here
  ops2Unmapped : Bool  -- writeLeg_sem_stable2's hopsUnmapped
deriving Repr

structure Tier3 where
  filtNonTrivial : Bool -- the untainted filter actually drops a tuple — else this is tier 2
  semFiltEq      : Bool -- sem_untaintedFilter_co's content
  checkFnMatched : Bool -- writeLeg_checkFn_stable at the store-MATCHED `_d` form
  checkFnRStable : Bool -- CascadeStrata.lean:113 checkFnR — the ROUTED recursion
  checkFnRTested : Nat
deriving Repr

structure Arm where
  name           : String
  vac            : Vac
  t1             : Tier1
  t2             : Tier2
  t3             : Tier3
  hazardUnmapped : Bool    -- ("doc","admin","d1") ∉ cascadeKeys Sp σ'  — literally hunmapped
  hazardReachPre : Bool    -- σ.reach  alice → doc:d1#access
  hazardReachPost: Bool    -- σ'.reach alice → doc:d1#access  (the flip the bridge causes)
  verdict        : String
deriving Repr

def unmappedOf (S : Schema) (σ' : GraphState) (ks : List DKey) : List DKey :=
  ks.filter (fun k => !((cascadeKeys S σ').contains (k.dt, k.R, k.on)))

/-- Tier 1 is SCHEMA-FREE by construction (`_S` is unreferenced on purpose): every
    instrument reads only the two states, the routing-independent `NODES`/`SUBS`, and the
    post store.  Keeping the parameter keeps the call shape uniform across tiers. -/
def tier1Of (_S : Schema) (σ σ' : GraphState) (T' : Store) (ks ksU : List DKey) : Tier1 :=
  { reachStable :=
      ksU.all (fun k => (computedRefs k.e).all (fun r' =>
        NODES.all (fun x =>
          σ'.reach x (objNode ⟨k.dt, k.on⟩ r') == σ.reach x (objNode ⟨k.dt, k.on⟩ r'))))
    reachStableAll :=
      ks.all (fun k => (computedRefs k.e).all (fun r' =>
        NODES.all (fun x =>
          σ'.reach x (objNode ⟨k.dt, k.on⟩ r') == σ.reach x (objNode ⟨k.dt, k.on⟩ r'))))
    wAllDead :=
      ks.all (fun k => (computedRefs k.e).all (fun r' =>
        NODES.all (fun u =>
          (σ'.reach u (wAllNode k.dt r') == false) && (σ.reach u (wAllNode k.dt r') == false))))
    graphRecStable :=
      ksU.all (fun k => (computedRefs k.e).all (fun r' =>
        SUBS.all (fun s =>
          GraphModel.graphRec σ' s k.dt k.on r' == GraphModel.graphRec σ s k.dt k.on r')))
    checkFnStable :=
      ksU.all (fun k => SUBS.all (fun s =>
        σ'.checkFn T' s k.dt k.on k.R k.e == σ.checkFn T' s k.dt k.on k.R k.e)) }

def tier2Of (S : Schema) (σ σ' : GraphState) (T T' : Store) (ks ksU : List DKey) : Tier2 :=
  { semEq :=
      ks.all (fun k => SEMSUBS.all (fun s =>
        sem S T' ⟨s, k.R, ⟨k.dt, k.on⟩⟩ == sem S T ⟨s, k.R, ⟨k.dt, k.on⟩⟩))
    guardPre :=
      ks.all (fun k => SEMSUBS.all (fun s =>
        σ.checkFn T s k.dt k.on k.R k.e == sem S T ⟨s, k.R, ⟨k.dt, k.on⟩⟩))
    guardPost :=
      ks.all (fun k => SEMSUBS.all (fun s =>
        σ'.checkFn T' s k.dt k.on k.R k.e == sem S T' ⟨s, k.R, ⟨k.dt, k.on⟩⟩))
    rowsFixed :=
      ks.all (fun k =>
        σ'.residue (objNode ⟨k.dt, k.on⟩ k.R) k.R == σ.residue (objNode ⟨k.dt, k.on⟩ k.R) k.R)
    inEdgesFixed :=
      ks.all (fun k => NODES.all (fun x =>
        σ'.edges.contains (x, objNode ⟨k.dt, k.on⟩ k.R)
          == σ.edges.contains (x, objNode ⟨k.dt, k.on⟩ k.R)))
    ops2Tested :=
      (ksU.flatMap (fun k =>
        (computedRefs k.e).filter (fun r' => isDerived S (k.dt, r')))).length
    ops2Unmapped :=
      ksU.all (fun k => (computedRefs k.e).all (fun r' =>
        !(isDerived S (k.dt, r')) || !((cascadeKeys S σ').contains (k.dt, r', k.on)))) }

def tier3Of (S : Schema) (σ σ' : GraphState) (Td : Store) (ks ksU : List DKey) : Tier3 :=
  let Tf := Td.filter (fun tp => !isDerived S (tp.object.type, tp.relation))
  { filtNonTrivial := Tf.length < Td.length
    semFiltEq :=
      ks.all (fun k => SEMSUBS.all (fun s =>
        sem S Td ⟨s, k.R, ⟨k.dt, k.on⟩⟩ == sem S Tf ⟨s, k.R, ⟨k.dt, k.on⟩⟩))
    checkFnMatched :=
      ksU.all (fun k => SUBS.all (fun s =>
        σ'.checkFn Td s k.dt k.on k.R k.e == σ.checkFn Td s k.dt k.on k.R k.e))
    checkFnRStable :=
      ksU.all (fun k => SUBS.all (fun s =>
        σ'.checkFnR Td s k.dt k.on k.R k.e == σ.checkFnR Td s k.dt k.on k.R k.e))
    checkFnRTested := ksU.length * SUBS.length }

/-- ★ THE DECISION TABLE, mechanised.  This is the whole point of the probe: the
    premise-vs-false question is answered by a computation, not by a reading. -/
def verdictOf (a : Tier1) (b : Tier2) (c : Tier3) (hz : Bool) : String :=
  if a.reachStable && a.graphRecStable && a.checkFnStable && c.checkFnRStable
     && b.rowsFixed && b.inEdgesFixed then
    "GREEN  - every tier instrument survives this routing"
  else if hz then
    "FALSE  - unstable AND ('doc','admin','d1') is UNMAPPED: no premise on (dt,R,on) saves the statement"
  else
    "PREMISE- unstable but the key is MAPPED: hunmapped already excludes it; only the PROOF breaks"

/-- The hazard node: the operand node of the designated derived key `("doc","admin","d1")`
    whose def reads `access` as a `computed` operand (`mem_affectedKeys`'s `hr'`). -/
def hazardNode : NodeKey := objNode ⟨"doc", "d1"⟩ "access"
def alice : NodeKey := subjNode ⟨"user", "alice", BARE⟩
def bob : NodeKey := subjNode ⟨"user", "bob", BARE⟩

/-- `σ` = pre-write state, `σplain` = the plain live leg (the bridge baseline),
    `σ'` = this arm's post state; `T` = PRE store, `Tpost` = POST store (`t :: T`),
    `Td` = the tier-3 store carrying the stored DERIVED-relation tuple. -/
def mkArm (nm : String) (σ σplain σ' : GraphState) (T Tpost Td : Store) : Arm :=
  let ksU := unmappedOf Sp σ' KEYS
  let a := tier1Of Sp σ σ' Tpost KEYS ksU
  let b := tier2Of Sp σ σ' T Tpost KEYS ksU
  let c := tier3Of Sp σ σ' Td KEYS ksU
  { name := nm
    vac :=
      { edges := σ'.edges.length
        legEdges := σplain.edges.length
        bridges := σ'.edges.length - σplain.edges.length
        frontier := σ'.frontierRows.length
        ckeys := (cascadeKeys Sp σ').length
        keys := KEYS.length
        unmapped := ksU.length
        reachPairs := ksU.length * 2 * NODES.length
        guardPairs := ksU.length * SUBS.length }
    t1 := a
    t2 := b
    t3 := c
    hazardUnmapped := !((cascadeKeys Sp σ').contains ("doc", "admin", "d1"))
    hazardReachPre := σ.reach alice hazardNode
    hazardReachPost := σ'.reach alice hazardNode
    verdict := verdictOf a b c (!((cascadeKeys Sp σ').contains ("doc", "admin", "d1"))) }

/-! ## §5  The run -/

/-- The POS control's raw edge: straight into the operand node, unlogged, from a subject
    that is in the routing-independent domain.  MUST redden tier 1. -/
def posEdge : NodeKey × NodeKey := (subjNode ⟨"user", "carol", BARE⟩, hazardNode)

/-- The NULL control's target: `doc:d2#banned` is NOT a declared bridged-in shape, so
    `ensureInBridges` there is a no-op and `Vac.bridges` MUST read 0. -/
def nullNode : NodeKey := objNode ⟨"doc", "d2"⟩ "banned"

def arms : Option (List Arm) :=
  (graphRunOps Sp prefixOps).map (fun p =>
    let σ0 := p.1
    let T0 := p.2
    -- scenario OBJ: the bridged-in shape is the write's OBJECT endpoint
    let To := tObj :: T0
    let Tdo := tAdm :: To
    let pO := σ0.writeLoggedRules Sp tObj
    -- scenario SUB: the bridged-in shape is the write's SUBJECT endpoint
    let Ts := tSub :: T0
    let Tds := tAdm :: Ts
    let pS := σ0.writeLoggedRules Sp tSub
    [ mkArm "BASE (plain live leg, tObj)" σ0 pO pO T0 To Tdo
    , mkArm "NULL (plain leg + ensureInBridges at a NON-bridged node)" σ0 pO
        (bridgeAt pO nullNode) T0 To Tdo
    , mkArm "POS  (plain leg + RAW unlogged edge into doc:d1#access)" σ0 pO
        { pO with edges := posEdge :: pO.edges } T0 To Tdo
    , mkArm "B-OBJ  (bridge on the leaf-routed OBJECT endpoint, unlogged)" σ0 pO
        (legB Sp false true false σ0 tObj) T0 To Tdo
    , mkArm "B-BOTH (bridge on BOTH leaf-routed endpoints, unlogged)" σ0 pO
        (legB Sp true true false σ0 tObj) T0 To Tdo
    , mkArm "BASE-S (plain live leg, tSub)" σ0 pS pS T0 Ts Tds
    , mkArm "B-SUB  (bridge on the leaf-routed SUBJECT endpoint, unlogged)" σ0 pS
        (legB Sp true false false σ0 tSub) T0 Ts Tds
    , mkArm "B-SUB-L(bridge on the SUBJECT endpoint, bridge source LOGGED)" σ0 pS
        (legB Sp true false true σ0 tSub) T0 Ts Tds ])

/-! ### The hazard, in one line per arm — the mechanism, visible -/

structure Hazard where
  arm            : String
  bridgeFired    : Nat
  aliceReach     : Bool
  bobReach       : Bool
  cKeys          : List (String × String × String)
  hazardUnmapped : Bool
deriving Repr

def hazards : Option (List Hazard) :=
  (graphRunOps Sp prefixOps).map (fun p =>
    let σ0 := p.1
    let pO := σ0.writeLoggedRules Sp tObj
    let pS := σ0.writeLoggedRules Sp tSub
    let mk := fun (nm : String) (base σ' : GraphState) =>
      ({ arm := nm
         bridgeFired := σ'.edges.length - base.edges.length
         aliceReach := σ'.reach alice hazardNode
         bobReach := σ'.reach bob hazardNode
         cKeys := cascadeKeys Sp σ'
         hazardUnmapped := !((cascadeKeys Sp σ').contains ("doc", "admin", "d1")) } : Hazard)
    [ mk "prefix σ0 (drained)" σ0 σ0
    , mk "BASE"    pO pO
    , mk "B-OBJ"   pO (legB Sp false true false σ0 tObj)
    , mk "BASE-S"  pS pS
    , mk "B-SUB"   pS (legB Sp true false false σ0 tSub)
    , mk "B-SUB-L" pS (legB Sp true false true σ0 tSub) ])

/-! ## §6  The REPAIR measurement — does the bridge fix the 2026-08-10 refutation?

`baseAgree` MUST be false: without the in-bridge the drained graph answers `false` where
`sem` answers `true` on this exact store (`TtuStarWide.lean:32-39`).  A true here means the
store is not in the newly-admitted region and this file's schema is wrong. -/

def queryGrid (S : Schema) (ts : List Tuple) : List Query :=
  S.keys.flatMap (fun k =>
    (objsOf ts).flatMap (fun o =>
      if o.type == k.1 then (subjDomain S ts).map (fun s => ⟨s, k.2, o⟩) else []))

def GRID : List Query := queryGrid Sp corpus

structure Repair where
  gridSize     : Nat
  baseDrained  : Bool
  bridgeDrained: Bool
  baseAgree    : Bool
  baseMismatch : Nat
  bridgedAgree : Bool
  bridgedMismatch : Nat
deriving Repr

def repair : Option Repair :=
  (graphRunOps Sp prefixOps).map (fun p =>
    let σ0 := p.1
    let T0 := p.2
    let To := tObj :: T0
    let dBase := cascadeLeg Sp To (σ0.writeLoggedRules Sp tObj)
    let dBr := cascadeLeg Sp To (legB Sp true true false σ0 tObj)
    let miss := fun (σ : GraphState) =>
      (GRID.filter (fun q => !(GraphModel.check σ q == sem Sp To q))).length
    { gridSize := GRID.length
      baseDrained := drainedB Sp dBase
      bridgeDrained := drainedB Sp dBr
      baseAgree := miss dBase == 0
      baseMismatch := miss dBase
      bridgedAgree := miss dBr == 0
      bridgedMismatch := miss dBr })

/-! ## §7  The CRITICAL CONSTRAINT, measured: leaf-routed vs public-name keying

`Sd` carries a DERIVED through-shape: `doc#control := approver from parent` declares
`(folder, "approver")` a star-tupleset through-shape (`isStarTuplesetThrough`, a purely
syntactic one-pass check), while `folder#approver` is a DERIVED key with a storage leaf, so
`rawWriteRels Sd` genuinely mints `approver.0`.

⚠ A bridge keyed on the PUBLIC relation name lands on a node the post-flip write leg no
longer touches, re-creating the ghost-grant divergence the kernel refuted
(`formal/history/PROOF_STATUS.md` sec 3 at :392-411, NOT sec 2).  `legEdgesIntoPublic = 0`
is that constraint as a NUMBER.  And if `bridgesOnLeafRouted = 0` while
`bridgesOnPublicKeyed = 1`, increment B cannot inhabit `ttuStarFree` for a derived
through-shape by routing alone — the minted leaf name is not a declared shape. -/
def Sd : Schema :=
  ⟨[(("folder", "blocked"),  .direct [("user", BARE, false)]),
    (("folder", "approver"), .excl (.direct [("user", BARE, false)]) (.computed "blocked")),
    (("doc", "parent"),      .direct [("folder", BARE, true)]),
    (("doc", "control"),     .ttu "approver" "parent")], []⟩

def td : Tuple := ⟨⟨"user", "alice", BARE⟩, "approver", ⟨"folder", "f1"⟩⟩
def publicNode : NodeKey := objNode ⟨"folder", "f1"⟩ "approver"
def leafNode0 : NodeKey := objNode ⟨"folder", "f1"⟩ (leafPred "approver" 0)

structure Routing where
  derivedKey            : Bool   -- isDerived Sd ("folder","approver")
  rawRels               : List String
  throughShapeDeclared  : Bool   -- isStarTuplesetThrough "folder" "approver"
  publicBridged         : Bool   -- isSubjectWildcardUserset "folder" "approver"
  leafBridged           : Bool   -- isSubjectWildcardUserset "folder" "approver.0"
  legEdges              : Nat
  legEdgesIntoPublic    : Nat    -- post-flip this MUST be 0
  legEdgesIntoLeaf      : Nat
  bridgesOnLeafRouted   : Nat
  bridgesOnPublicKeyed  : Nat
deriving Repr

def routing : Routing :=
  let σ0 := emptyState Sd
  let σw := σ0.writeLoggedRules Sd td
  let σleaf := (rewriteClosureL Sd (rawWriteTuples Sd td)).foldl
                 (fun acc u => bridgeAt (bridgeAt acc (subjNode u.subject))
                                        (objNode u.object u.relation)) σw
  let σpub := bridgeAt σw publicNode
  { derivedKey := isDerived Sd ("folder", "approver")
    rawRels := rawWriteRels Sd td
    throughShapeDeclared := Sd.isStarTuplesetThrough "folder" "approver"
    publicBridged := Sd.isSubjectWildcardUserset "folder" "approver"
    leafBridged := Sd.isSubjectWildcardUserset "folder" (leafPred "approver" 0)
    legEdges := σw.edges.length
    legEdgesIntoPublic := (σw.edges.filter (fun e => e.2 == publicNode)).length
    legEdgesIntoLeaf := (σw.edges.filter (fun e => e.2 == leafNode0)).length
    bridgesOnLeafRouted := σleaf.edges.length - σw.edges.length
    bridgesOnPublicKeyed := σpub.edges.length - σw.edges.length }

/-! ## §8  Output -/

/-! ### Scope + non-vacuity of the REGION (must read: narrow false, wide true) -/
#eval ("DOMAINS (subjects, semSubjects, nodes, derivedKeys, grid)",
       SUBS.length, SEMSUBS.length, NODES.length, KEYS.length, GRID.length)
#eval ("DERIVED KEYS PROBED", KEYS.map (fun k => (k.dt, k.R, k.on)))
#eval ("BRIDGED-IN SHAPE (folder,viewer): (isSubjectWildcardUserset, isStarTuplesetThrough)",
       Sp.isSubjectWildcardUserset "folder" "viewer",
       Sp.isStarTuplesetThrough "folder" "viewer")
#eval ("CONTROL - BARE pred is excluded (must be false)",
       Sp.isSubjectWildcardUserset "folder" BARE)
#eval ("NARROW rejects / WIDE admits the prefix store",
       (graphRunOps Sp prefixOps).map (fun p => (ttuStarFreeB Sp p.2, ttuStarFreeWB Sp p.2)))
#eval ("PREFIX drained? / PREFIX edges", (graphRunOps Sp prefixOps).map
       (fun p => (drainedB Sp p.1, p.1.edges)))
#eval ("rewriteClosureL (tObj)", rewriteClosureL Sp (rawWriteTuples Sp tObj))
#eval ("rewriteClosureL (tSub)", rewriteClosureL Sp (rawWriteTuples Sp tSub))

/-! ### The mechanism, one line per arm -/
#eval ("HAZARD", hazards)

/-! ### THE PROBE — all three tiers, all arms -/
#eval ("P6 PROBE", arms)

/-! ### Does the bridge REPAIR the 2026-08-10 refutation? -/
#eval ("REPAIR", repair)

/-! ### The leaf-vs-public routing constraint, as numbers -/
#eval ("ROUTING (leaf-routed vs public-keyed)", routing)

end P6BridgeProbe
