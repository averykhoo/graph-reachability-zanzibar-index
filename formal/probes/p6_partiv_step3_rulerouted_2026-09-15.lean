/-
  ★ P6 PART (iv) STEP-3 PROBE (2026-09-15) — attack the CALL SITES before restating the
  lemma, exactly as step 2 attacked the lemma before restating it.

  `docs/p6-part-iv-plan-2026-09-14.md` § Ordered steps, step 3:

      "Restate `ttuLeaf_elim_nss` (premise + conclusion) and repair its `3` shape-B call
       sites."

  Step 2 settled the LEMMA's shape.  This probe asks the question step 2 did not: can the
  SECOND shape-B call site — `RulesBareStar.lean::nreaches_of_semAux_rulesBS`, the
  completeness half of `::graph_correct_rulesBS` — be repaired at all?  That site does not
  merely re-shuffle a witness; it must produce a GRAPH PATH for the star witness, and the
  write model it is stated over (`RulesComplete.lean::ReachedByRulesAdmitted`, whose step is
  `RulesWrite.lean::GraphState.writeRules` = a bridge-free `writeDirect` fold) materialises
  no in-bridge.

  Kept OUTSIDE the lake package, like every other probe here: zero cone, ungated,
  re-runnable evidence.  Run from `formal/lean` against the built oleans:

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_partiv_step3_rulerouted_2026-09-15.lean

  ⚠ rc=0 with NO output is a FAILED run, not a green one.

  ── THE VERDICT ───────────────────────────────────────────────────────────────────────────

  **(A) STEP 3 AS PLANNED CANNOT BE COMPLETED, AND NOT FOR A PROOF-SHAPE REASON.** The second
  shape-B call site is `::nreaches_of_semAux_rulesBS`, the completeness half of
  `::graph_correct_rulesBS`.  That theorem's CONCLUSION is false under `TtuStarFreeW`: line
  (5) gives `sem = true`, `GraphModel.check = false` at a store the widened predicate admits
  and the narrow one rejects (1).  Every other hypothesis of `graph_correct_rulesBS` holds at
  the witness — store side conditions (2), query side conditions (4), and the admission side
  condition of EVERY `ReachedByRulesAdmitted.step` (3).  So there is nothing to repair: the
  site's surrounding theorem stops being true.

  **(B) THE CAUSE IS THE MISSING IN-BRIDGE, MEASURED NOT ARGUED.** Line (8): adding the ONE
  edge `folder:f1#viewer → w_any(folder,viewer)` by `UsStarWrite.lean::ensureInBridges` flips
  `check` to `true`.  Line (11) prints the three-edge graph so the gap is inspectable.
  `RulesWrite.lean::GraphState.writeRules` — the step of `ReachedByRulesAdmitted` — is a
  bridge-free `writeDirect` fold, which is exactly what `RulesBareStar.lean`'s own header has
  said since 2026-07-11.

  **(C) THE REPAIR EXISTS AND ALREADY WORKS.** Line (12): the SAME store written through
  `LeafRules.lean::writeRulesRaw` (a `UsStarWrite.lean::writeBridgedOne` fold — what `P6`
  part (ii) landed) answers `check = sem = true`.  Control (13): the concrete-parent store
  still agrees there.  This is the first measurement of part (ii)'s payoff ON the store part
  (iv) exists to admit, and it is positive.

  **(D) ★ THE ARCHITECTURAL HALF — the widening severs the route to `graph_correct_rulesBS`
  BEFORE that theorem is reached.** The W4 chain does not apply it to its own state; it
  applies it to a bridge-free SHADOW and transports the read by
  `CascadeStable.lean::shadow_graphRec_agree`, whose hypothesis is
  `::UntaintedShadow = ShadowOver (DerNode ∨ LeafNode ∨ BridgeNode)`.  `ShadowOver.term`
  (`CascadeStable.lean:712`) demands an extras node have NO OUTGOING EDGE — that is what makes
  a bridge inert for an untainted read.  Under the widening a star tupleset parent's rewrite
  output is sourced AT the bridge node, so `term` is false: `::no_untaintedShadow_at_widened_store`
  proves `∀ σ0, ¬ UntaintedShadow SwT (buildW SwT T) σ0` **by `decide`**, and its control
  `::control_edge_absent_at_concrete` shows the same route fails at a concrete parent.
  Line (15): the outgoing edge is present at all three write models, so this is not an artefact
  of one of them.

  **(E) NEITHER HALF IS VACUOUS.**  The store is INSIDE the widened fragment, not adjacent to
  it: `FullScope.lean::w4Fragment_of_untainted` collapses `W4Fragment` on an untainted schema
  to `wsBare` + `bareStar` + `ttuStarFree`, and line (17) gives untainted `true` and
  `wsBare` `true` (`declaredWildcardShapes = [(folder, BARE)]`), line (2) `bareStar` `true`,
  and `TtuStarWide.lean::WideWitness.wide_admits` already pins the third under the widening.
  Line (18): the state is reachable — `ReachedByW3d2E.write`'s only side condition holds at
  both writes.  ⚠ (18) is EVALUATOR evidence, not kernel; see the instrument-limit note at the
  foot of this file.

  **CONSEQUENCE FOR THE PLAN.** Part (iv)'s remaining work is a WRITE-MODEL composition, not
  a proof-shape sweep: the untainted core must itself carry the bridges (shadow written by a
  bridging fold, `BridgeNode` dropped from `ShadowOver`'s extras, `graph_correct_rulesBS`
  restated over a bridged admission predicate).  The old steps 3–5 become sub-steps of that,
  and step 6 is unchanged.  Written up at
  `docs/p6-part-iv-plan-2026-09-14.md` § "Corrections appended 2026-09-15 (eighth)".

  ── LITERAL TRANSCRIPT (the run's own stdout; nothing added, removed or reordered) ─────────

  RAN 2026-09-15, rc=0, from `formal/lean` via
  `lake env lean ../probes/p6_partiv_step3_rulerouted_2026-09-15.lean`

  ("(1) widening engaged at T: narrow REJECTS, wide ADMITS -- must be false, true", false, true)
  ("(2) store side conditions: bareStarStore / storeValidRules -- must be true, true", true, true)
  ("(3) ★ ADMISSION -- every writeRules step admits; must be true or (5) is vacuous", true)
  ("(4) query side conditions hqs / hqo -- must be true, true", true, true)
  ("(5) ★ THE DIVERGENCE -- sem / check at the widened store; equal = survives", true, false)
  ("(6) CONTROL b -- concrete parent: sem / check must AGREE (the encoding works)", true, true)
  ("(7) the node IS of a bridged-in shape (else (8) proves nothing) -- must be true", true)
  ("(8) ★ ATTRIBUTION -- add the ONE in-bridge by hand: check must flip to true", true)
  ("(9) CONTROL -- the graph is not simply empty: user:u DOES reach folder:f1#viewer", true)
  ("(10) CONTROL -- and the wAny(folder,viewer) node DOES reach the target", true)
  ("(11) the edge list, verbatim -- the missing link is cNode -> wAny(folder,viewer)",
   [({ type := "user", name := "u", pred := "...", variant := Zanzibar.Variant.plain },
     { type := "folder", name := "f1", pred := "viewer", variant := Zanzibar.Variant.plain }),
    ({ type := "folder", name := "*", pred := "viewer", variant := Zanzibar.Variant.wAny },
     { type := "doc", name := "d1", pred := "access", variant := Zanzibar.Variant.plain }),
    ({ type := "folder", name := "*", pred := "...", variant := Zanzibar.Variant.wAny },
     { type := "doc", name := "d1", pred := "parent", variant := Zanzibar.Variant.plain })])
  ("(12) ★ leaf-routed + bridged write of the SAME store: sem / check", true, true)
  ("(13) CONTROL b on the leaf-routed path -- concrete parent still agrees", true, true)
  ("(14) the bridge node's shape IS declared (so `bridgeNode_wAnyNode` applies)", true)
  ("(15) ★ the bridge node HAS an outgoing edge -- logged/bridged, shadow-style, leaf", true, true, true)
  ("(16) CONTROL b -- at a concrete parent the bridge node has NO outgoing edge", false, false)
  ("(17) untainted schema / wsBare -- the two other contentful W4Fragment fields", true, true, [("folder", "...")])
  ("(18) ★ the W4 write ctor's ONLY side condition, at both writes -- must be true, true", true, true)

  ----------------------------------- END VERBATIM -----------------------------------------

  ⚠ CONTROLS, and what each rules out:
  * (1)/(17)/(2) NON-VACUITY — the widening is engaged at this store AND the store satisfies
    the rest of the widened `W4Fragment`. Without these the divergence could be about a store
    part (iv) never admits.
  * (3) ADMISSION — every `writeRules` step admits. Without it the refuted theorem's `hRA`
    premise could be unsatisfiable and (5) would refute nothing.
  * (6)/(13)/(16) CONTROL b, a CONCRETE tupleset parent — `sem` and `check` AGREE, and the
    bridge node has no outgoing edge. This is what attributes (5) and (15) to the STAR parent
    rather than to a broken encoding of `check`, `build`, or the edge test.
  * (9)/(10) — the two halves of the missing path are each present. Rules out "the graph is
    empty / the query is nonsense".
  * (7) — the hand-added bridge is added at a node that really is of a bridged-in shape, so
    (8) is `ensureInBridges` doing its job rather than an arbitrary edge insertion.
-/
import ZanzibarProofs

open Zanzibar

namespace P6PartIvStep3Probe

/-! ## §1 The subject — `TtuStarWide.lean::WideWitness.SwT`, reused by NAME (not copied)

`doc#access := viewer from parent`, tupleset `doc#parent` carrying the BARE wildcard
restriction `[folder:*]`, so `(folder, "viewer")` is a declared star-tupleset through-shape.
`WideWitness.narrow_rejects` / `::wide_admits` already pin that the widening is engaged at
the one-tuple store `TwT`. -/

abbrev S : Schema := WideWitness.SwT

/-- The star tupleset parent (`WideWitness.twT`) plus the grant that makes the star branch of
    `ttuLeaf` reachable through a CONCRETE folder instance. Without the grant the star branch
    fires only on the `s.type = pt` disjunct and the interesting path does not exist. -/
def tGrant : Tuple := ⟨⟨"user", "u", BARE⟩, "viewer", ⟨"folder", "f1"⟩⟩

def T : Store := [tGrant, WideWitness.twT]

/-- CONTROL b: the same store with a CONCRETE tupleset parent — today's fragment. -/
def tConc : Tuple := ⟨⟨"folder", "f1", BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def Tc : Store := [tGrant, tConc]

def q : Query := ⟨⟨"user", "u", BARE⟩, "access", ⟨"doc", "d1"⟩⟩

/-! ## §2 The write model under test — `ReachedByRulesAdmitted`, transcribed

`RulesComplete.lean:111`:

    | empty (S) : ReachedByRulesAdmitted (emptyState S) S []
    | step t (hprev) (hadm : FoldAdmits σ (rewriteClosure S t)) :
        ReachedByRulesAdmitted (σ.writeRules S t) S (t :: T)

so the state of a store `t :: rest` is `(build rest).writeRules S t`, and the admission side
condition is `FoldAdmits (build rest) (rewriteClosure S t)` at EVERY step. `admitsAll` below
is that conjunction — ⚠ without it the refutation could be vacuous (a store no admitted
write path reaches refutes nothing). -/

def build (S : Schema) : Store → GraphState
  | [] => emptyState S
  | t :: rest => (build S rest).writeRules S t

def admitsAll (S : Schema) : Store → Bool
  | [] => true
  | t :: rest => admitsAll S rest && foldAdmitsB (build S rest) (rewriteClosure S t)

/-! ## §3 Non-vacuity — is the widening engaged at THIS store, and is the store in-fragment? -/

#eval ("(1) widening engaged at T: narrow REJECTS, wide ADMITS -- must be false, true",
        ttuStarFreeB S T, ttuStarFreeWB S T)
#eval ("(2) store side conditions: bareStarStore / storeValidRules -- must be true, true",
        bareStarStoreB T, storeValidRulesB S T)
#eval ("(3) ★ ADMISSION -- every writeRules step admits; must be true or (5) is vacuous",
        admitsAll S T)
#eval ("(4) query side conditions hqs / hqo -- must be true, true",
        (q.subject.name != STAR || q.subject.predicate == BARE), q.object.name != STAR)

/-! ## §4 THE ATTACK — does `graph_correct_rulesBS`'s CONCLUSION survive the widening?

Its conclusion is `GraphModel.check σ q = sem S T q`. Every other hypothesis is checked
above; `hTS` is the only one that has to move from `TtuStarFree` to `TtuStarFreeW`. -/

#eval ("(5) ★ THE DIVERGENCE -- sem / check at the widened store; equal = survives",
        sem S T q, GraphModel.check (build S T) q)
#eval ("(6) CONTROL b -- concrete parent: sem / check must AGREE (the encoding works)",
        sem S Tc q, GraphModel.check (build S Tc) q)

/-! ## §5 ATTRIBUTION — is the MISSING IN-BRIDGE the sole cause?

`UsStarWrite.lean:296::GraphState.ensureInBridges` is the bridge materialiser. If adding the
one in-bridge for the concrete userset node `folder:f1#viewer` flips `check` to agree with
`sem`, the gap is exactly the bridge that `writeRules` does not write — not some other
missing edge, and not a broken encoding. -/

def cNode : NodeKey := ⟨"folder", "f1", "viewer", Variant.plain⟩

#eval ("(7) the node IS of a bridged-in shape (else (8) proves nothing) -- must be true",
        (build S T).bridgedInConcrete cNode)
#eval ("(8) ★ ATTRIBUTION -- add the ONE in-bridge by hand: check must flip to true",
        GraphModel.check ((build S T).ensureInBridges cNode) q)
#eval ("(9) CONTROL -- the graph is not simply empty: user:u DOES reach folder:f1#viewer",
        (build S T).reach (subjNode q.subject) (objNode ⟨"folder", "f1"⟩ "viewer"))
#eval ("(10) CONTROL -- and the wAny(folder,viewer) node DOES reach the target",
        (build S T).reach (wAnyNode ("folder", "viewer")) (objNode ⟨"doc", "d1"⟩ "access"))
#eval ("(11) the edge list, verbatim -- the missing link is cNode -> wAny(folder,viewer)",
        (build S T).edges)

/-! ## §6 Does the LEAF-routed write path bridge it?

`LeafRules.lean:348::GraphState.writeRulesRaw` folds `UsStarWrite.lean:363::writeBridgedOne`
instead of `writeDirect` — that is what `P6` part (ii) landed. If the same store through
THAT fold answers correctly, the repair for step 3 is a write-model question, not a
proof-shape question. -/

def buildL (S : Schema) : Store → GraphState
  | [] => emptyState S
  | t :: rest => (buildL S rest).writeRulesRaw S t

#eval ("(12) ★ leaf-routed + bridged write of the SAME store: sem / check",
        sem S T q, GraphModel.check (buildL S T) q)
#eval ("(13) CONTROL b on the leaf-routed path -- concrete parent still agrees",
        sem S Tc q, GraphModel.check (buildL S Tc) q)

/-! ## §7 THE ARCHITECTURAL HALF — `ShadowOver.term` at the bridge disjunct

The W4 chain does not hand `graph_correct_rulesBS` its own state; it hands it a bridge-free
SHADOW and transports the read across by `CascadeStable.lean::shadow_graphRec_agree`, whose
hypothesis is `::UntaintedShadow S σ σ0 = ShadowOver (DerNode ∨ LeafNode ∨ BridgeNode) σ σ0`.

`ShadowOver.term` (`CascadeStable.lean:712`) says an extras node has **no outgoing edge in
`σ`** — that is what makes a bridge inert for an untainted read: a path may enter the
`wAny` node and can never leave it. Under the widening a star tupleset parent's rewrite
output is sourced *at that very node*, so `term` is false — at the real logged/bridged state
and at the bridge-free one alike. -/

def bNode : NodeKey := wAnyNode ("folder", "viewer")
def target : NodeKey := objNode ⟨"doc", "d1"⟩ "access"

def buildW (S : Schema) : Store → GraphState
  | [] => emptyState S
  | t :: rest => (buildW S rest).writeLoggedRules S t

#eval ("(14) the bridge node's shape IS declared (so `bridgeNode_wAnyNode` applies)",
        S.isSubjectWildcardUserset "folder" "viewer")
#eval ("(15) ★ the bridge node HAS an outgoing edge -- logged/bridged, shadow-style, leaf",
        (buildW S T).edges.contains (bNode, target),
        (build S T).edges.contains (bNode, target),
        (buildL S T).edges.contains (bNode, target))
#eval ("(16) CONTROL b -- at a concrete parent the bridge node has NO outgoing edge",
        (buildW S Tc).edges.contains (bNode, target),
        (build S Tc).edges.contains (bNode, target))

/-- ★ **No shadow decomposition exists at this store, for ANY `σ0`.** Not "the current proof
    breaks" — the hypothesis `shadow_graphRec_agree` consumes is unsatisfiable here, so the
    W4 chain's route to `graph_correct_rulesBS` is severed by the widening independently of
    how `graph_correct_rulesBS` itself is restated. -/
theorem no_untaintedShadow_at_widened_store :
    ∀ σ0 : GraphState, ¬ UntaintedShadow S (buildW S T) σ0 := by
  intro σ0 hsh
  exact hsh.term bNode (Or.inr (Or.inr (bridgeNode_wAnyNode (by decide)))) target
    (by decide)

/-- CONTROL for the theorem above: the same refutation ROUTE must FAIL at the concrete-parent
    store, or it is an artefact of the encoding rather than of the star tupleset parent. -/
theorem control_edge_absent_at_concrete :
    (buildW S Tc).edges.contains (bNode, target) = false := by decide

/-! ## §8 THE TWO VACUITY KILLERS

A state with no shadow refutes nothing unless (a) the W4 chain REACHES it and (b) the
WIDENED fragment ADMITS its store. Both are settled here mechanically.

(a) `ReachedByW3d2E.write`'s only side condition is `FoldAdmitsBridged`
(`CascadeStrataAssemble.lean:431`), so the reachability is a TERM, not an argument.

(b) `FullScope.lean::w4Fragment_of_untainted` collapses the bundle on an untainted schema to
`wsBare`, `bareStar` and `ttuStarFree` — and `WideWitness.wide_admits` already pins the third
under the widening. So with part (iv)'s flip in place, `W4Fragment SwT T` HOLDS at this
store: it is inside the widened fragment, not merely adjacent to it. -/

#eval ("(17) untainted schema / wsBare -- the two other contentful W4Fragment fields",
        S.defs.all (fun d => !containsBool d.2),
        (declaredWildcardShapes S).all (fun sh => sh.2 == BARE),
        declaredWildcardShapes S)

#eval ("(18) ★ the W4 write ctor's ONLY side condition, at both writes -- must be true, true",
        foldAdmitsBridgedB (buildW S [WideWitness.twT])
          (rewriteClosureL S (rawWriteTuples S tGrant)),
        foldAdmitsBridgedB (emptyState S)
          (rewriteClosureL S (rawWriteTuples S WideWitness.twT)))

/- ⚠ **INSTRUMENT LIMIT, recorded rather than hidden.** The reachability above wants to be a
   TERM, not an `#eval`:

       theorem w4_reaches_widened_store : ReachedByW3d2E (buildW S T) S T :=
         ReachedByW3d2E.write tGrant ((foldAdmitsBridgedB_iff _ _).mp (by decide))
           (ReachedByW3d2E.write WideWitness.twT
             ((foldAdmitsBridgedB_iff _ _).mp (by decide)) (ReachedByW3d2E.empty S))

   It does not elaborate at this size. `by decide` hits `(deterministic) timeout at whnf` at
   the default 200000 heartbeats AND at 4000000; `by rfl` was killed at a 10-minute wall
   clock. The kernel reduces `buildW` happily (the `by decide` at
   `::no_untaintedShadow_at_widened_store` and `::control_edge_absent_at_concrete` both go
   through) — it is `FoldAdmitsBridged`'s `admitEdge`, and through it `reachB` at fuel
   `nodes.length + 1`, that does not. So line (18) is EVALUATOR evidence for the side
   condition while lines above it are KERNEL evidence, and the difference is stated here
   rather than papered over. Promoting the reachability to a kernel term needs a smaller
   witness or a lemma, and is worth doing when these findings become tree pins. -/

end P6PartIvStep3Probe
