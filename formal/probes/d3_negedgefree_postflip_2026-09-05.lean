/-
  ★ TRACKED COPY (2026-09-05b) of the D.3 / 2026-08-08 attack-first probe, RE-RUN on the
  POST-FLIP model's OWN write leg (board `P3` landed (α)+(R5)). Kept OUTSIDE the lake
  package on purpose: it is not part of the gated build, it is evidence that can be
  re-run. Run from formal/lean (needs the built oleans):

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/d3_negedgefree_postflip_2026-09-05.lean

  Literal result on the landed tree, 2026-09-05 (rc=0; re-run first-hand by the session,
  identical in both prefix orders):

    ("PROBE",
     some ("(A subject-leafrouted, B bare-preflip, C drained, D bridge-sabotage)",
      { edges := 5, rows := 1, negTested := 2, negFree := true,  uposTested := 0, uposFree := true },
      { edges := 5, rows := 1, negTested := 2, negFree := false, uposTested := 0, uposFree := true },
      { edges := 5, rows := 1, negTested := 4, negFree := true,  uposTested := 0, uposFree := true },
      { edges := 6, rows := 1, negTested := 2, negFree := false, uposTested := 0, uposFree := true }))

  (A) the model's own `writeLoggedRules` lands the write on `doc:d1#approver.0`, the bare
  `doc:d1#approver` node carries no incoming edge, and `Inv.negEdgeFree`'s instrument is
  GREEN at negTested := 2 over a routing-independent 144-pair key domain (rows := 1, so the
  2026-08-08 vacuity trap did not recur); (B) the pre-flip bare edge on the SAME drained
  state and the SAME residue rows reproduces D.3's kill; (C) drained stays green; (D) a
  hypothetical `approver.0 -> approver` bridge turns (A) red, so the instrument is
  reachability-sensitive. `negTested` counts `neg` entries with multiplicity (the residue
  row is `neg := [bob, bob]`), which is why the counts read 2/2/4 where 2026-08-08 read
  1/1/3. Measurement over the fuel-capped `GraphState.reach`, ONE schema shape — NOT a
  proof; the theorem is board item `P5`. Original probe header follows.
-/
/-
  D.3 / 2026-08-08 attack-first probe, RE-RUN on the POST-FLIP model's OWN write leg.

  Scratch only (gitignored). Run from formal/lean:
      lake env lean ../../.scratch/d3_negedgefree_postflip.lean

  Subject   (A): drained prefix state, then the model's OWN GraphState.writeLoggedRules
                 (no hand-routing), pre-cascade.
  Control   (B): same drained state, hand-written BARE public edge (writeLoggedOne tw) --
                 what the pre-flip write leg did.  Expect negFree := false, negTested := 1.
  Control   (C): subject + one cascade leg (drained).  Expect negFree := true.
  Control   (D): subject + a hypothetical approver.0 -> approver bridge edge.  Expect
                 negFree := false -- proves the instrument is REACHABILITY-sensitive and
                 not merely key-equality-sensitive.

  WITNESS TRAP (scope doc S9.1): the residue key domain MUST be routing-INDEPENDENT.
  It is built from the STORE's objects x the SCHEMA's declared relations x
  {bare, .0, .1, .2}, never from sigma.nodes.
-/
import ZanzibarProofs

open Zanzibar

namespace D3Probe

/-! ## The routing-independent key domain -/

/-- Predicate names: every declared relation, bare and at leaf indices 0/1/2.
    Depends on the SCHEMA only -- no state, no routing. -/
def predNames (S : Schema) : List String :=
  S.keys.flatMap (fun k => [k.2, leafPred k.2 0, leafPred k.2 1, leafPred k.2 2])

/-- Objects: every object mentioned by the STORE/op corpus, deduplicated.
    Depends on the tuples only -- no state, no routing. -/
def objsOf (ts : List Tuple) : List ObjectRef :=
  ts.foldl (fun acc t => if acc.contains t.object then acc else acc ++ [t.object]) []

/-- The full routing-independent residue key domain:
    (object x predName) node keys, crossed with (predName) residue relations. -/
def keyDomain (S : Schema) (ts : List Tuple) : List (NodeKey × String) :=
  (objsOf ts).flatMap (fun o =>
    (predNames S).flatMap (fun p =>
      (predNames S).map (fun r => (objNode o p, r))))

/-! ## The instrument -/

structure ProbeResult where
  edges : Nat
  rows : Nat
  negTested : Nat
  negFree : Bool
  uposTested : Nat
  uposFree : Bool
deriving Repr

/-- `Inv.negEdgeFree` (State.lean:706) evaluated: over the routing-independent key
    domain, for every persisted residue row and every `neg` member, is the member's
    subject node UNABLE to reach the residue's key node?  `negTested` counts the
    (row, neg member) pairs actually tested -- the non-vacuity number. -/
def probe (σ : GraphState) (dom : List (NodeKey × String)) : ProbeResult :=
  dom.foldl (fun acc kr =>
      match σ.residue kr.1 kr.2 with
      | none => acc
      | some res =>
        { acc with
          rows := acc.rows + 1
          negTested := acc.negTested + res.neg.length
          negFree := acc.negFree && res.neg.all (fun n => !(σ.reach (subjNode n) kr.1))
          uposTested := acc.uposTested + res.upos.length
          uposFree := acc.uposFree && res.upos.all (fun n => !(σ.reach (subjNode n) kr.1)) })
    { edges := σ.edges.length, rows := 0, negTested := 0, negFree := true,
      uposTested := 0, uposFree := true }

/-! ## D.3's exact schema / store -/

/-- D.3's schema is already in the tree: `LeafWitness.Sw`
    (`approver := ([user] or viewer) but not banned`, wildcard on `viewer`). -/
abbrev S : Schema := LeafWitness.Sw

/-- `user:bob#banned@doc:d1` -- already in the tree as `LeafWitness.tb`. -/
abbrev tBanned : Tuple := LeafWitness.tb

/-- `user:*#viewer@doc:d1` -- the load-bearing wildcard grant. -/
def tStarViewer : Tuple := ⟨⟨"user", STAR, BARE⟩, "viewer", ⟨"doc", "d1"⟩⟩

/-- The probe write, on the DERIVED public relation -- `LeafWitness.tw`. -/
abbrev tW : Tuple := LeafWitness.tw

/-- The prefix, cascaded to drained by the driver (one cascade leg per op). -/
def prefixOps : List GraphOp := [GraphOp.add tBanned, GraphOp.add tStarViewer]

def corpus : List Tuple := [tBanned, tStarViewer, tW]

def dom : List (NodeKey × String) := keyDomain S corpus

/-- The hypothetical bridge edge `doc:d1#approver.0 -> doc:d1#approver`. -/
def bridgeEdge : NodeKey × NodeKey :=
  (objNode ⟨"doc", "d1"⟩ (leafPred "approver" 0), objNode ⟨"doc", "d1"⟩ "approver")

/-! ## The run -/

def results : Option (String × ProbeResult × ProbeResult × ProbeResult × ProbeResult) :=
  (graphRunOps S prefixOps).map (fun p =>
    let σ0 := p.1
    let T0 := p.2
    -- (A) SUBJECT: the model's OWN write leg, pre-cascade.
    let σA := σ0.writeLoggedRules S tW
    -- (B) POSITIVE CONTROL: the bare public edge, as the pre-flip leg wrote it.
    let σB := σ0.writeLoggedOne tW
    -- (C) DRAINED CONTROL: subject + one cascade leg.
    let σC := cascadeLeg S (tW :: T0) σA
    -- (D) INSTRUMENT CONTROL: subject + a hypothetical approver.0 -> approver bridge.
    let σD := { σA with edges := bridgeEdge :: σA.edges }
    ("(A subject-leafrouted, B bare-preflip, C drained, D bridge-sabotage)",
     probe σA dom, probe σB dom, probe σC dom, probe σD dom))

def drainedFlags : Option (Bool × Bool × Bool) :=
  (graphRunOps S prefixOps).map (fun p =>
    let σ0 := p.1
    let σA := σ0.writeLoggedRules S tW
    (drainedB S σ0, drainedB S σA, drainedB S (cascadeLeg S (tW :: p.2) σA)))

def subjectEdges : Option (List (NodeKey × NodeKey)) :=
  (graphRunOps S prefixOps).map (fun p => (p.1.writeLoggedRules S tW).edges)

def prefixEdges : Option (List (NodeKey × NodeKey)) :=
  (graphRunOps S prefixOps).map (fun p => p.1.edges)

def bareControlEdges : Option (List (NodeKey × NodeKey)) :=
  (graphRunOps S prefixOps).map (fun p => (p.1.writeLoggedOne tW).edges)

/-- The residue rows the instrument found on the SUBJECT state, printed so the reader
    can see WHICH (key, relation) pair carried the tested `neg` member. -/
def subjectRows : Option (List (NodeKey × String × Residue)) :=
  (graphRunOps S prefixOps).map (fun p =>
    let σA := p.1.writeLoggedRules S tW
    dom.filterMap (fun kr => (σA.residue kr.1 kr.2).map (fun res => (kr.1, kr.2, res))))

def prefixStore : Option Store := (graphRunOps S prefixOps).map (·.2)

/-- The same rows on the BARE control (B) and the DRAINED control (C). -/
def rowsOf (σ : GraphState) : List (NodeKey × String × Residue) :=
  dom.filterMap (fun kr => (σ.residue kr.1 kr.2).map (fun res => (kr.1, kr.2, res)))

def bareRows : Option (List (NodeKey × String × Residue)) :=
  (graphRunOps S prefixOps).map (fun p => rowsOf (p.1.writeLoggedOne tW))

def drainedRows : Option (List (NodeKey × String × Residue)) :=
  (graphRunOps S prefixOps).map (fun p =>
    rowsOf (cascadeLeg S (tW :: p.2) (p.1.writeLoggedRules S tW)))

def drainedEdges : Option (List (NodeKey × NodeKey)) :=
  (graphRunOps S prefixOps).map (fun p =>
    (cascadeLeg S (tW :: p.2) (p.1.writeLoggedRules S tW)).edges)

/-- A vs B: same residue rows, and edge lists differing in exactly the ONE routed edge. -/
def aVsB : Option (Bool × List (NodeKey × NodeKey) × List (NodeKey × NodeKey)) :=
  (graphRunOps S prefixOps).map (fun p =>
    let σA := p.1.writeLoggedRules S tW
    let σB := p.1.writeLoggedOne tW
    (rowsOf σA == rowsOf σB,
     σA.edges.filter (fun e => !(σB.edges.contains e)),
     σB.edges.filter (fun e => !(σA.edges.contains e))))

/-! ## Output -/

#eval ("DOMAIN SIZE (routing-independent key pairs)", dom.length)
#eval ("PRED NAMES", predNames S)
#eval ("rawWriteRels S tW", rawWriteRels S tW)
#eval ("rawWriteTuples S tW", rawWriteTuples S tW)
#eval ("rewriteClosureL S (rawWriteTuples S tW)", rewriteClosureL S (rawWriteTuples S tW))
#eval ("PREFIX STORE", prefixStore)
#eval ("PREFIX EDGES (drained)", prefixEdges)
#eval ("SUBJECT EDGES (A: writeLoggedRules, pre-cascade)", subjectEdges)
#eval ("BARE CONTROL EDGES (B: writeLoggedOne on pred approver)", bareControlEdges)
#eval ("SUBJECT RESIDUE ROWS (A)", subjectRows)
#eval ("BARE CONTROL RESIDUE ROWS (B)", bareRows)
#eval ("DRAINED CONTROL EDGES (C)", drainedEdges)
#eval ("DRAINED CONTROL RESIDUE ROWS (C)", drainedRows)
#eval ("A vs B: (rows identical?, A-only edges, B-only edges)", aVsB)
#eval ("DRAINED? (prefix, subject-A, cascaded-C)", drainedFlags)
#eval ("PROBE", results)

/-! ## Prefix-order swap (the 2026-08-08 run's stability check) -/

def prefixOpsSwapped : List GraphOp := [GraphOp.add tStarViewer, GraphOp.add tBanned]

def resultsSwapped : Option (ProbeResult × ProbeResult × ProbeResult × ProbeResult) :=
  (graphRunOps S prefixOpsSwapped).map (fun p =>
    let σ0 := p.1
    let σA := σ0.writeLoggedRules S tW
    let σB := σ0.writeLoggedOne tW
    let σC := cascadeLeg S (tW :: p.2) σA
    let σD := { σA with edges := bridgeEdge :: σA.edges }
    (probe σA dom, probe σB dom, probe σC dom, probe σD dom))

#eval ("PROBE, PREFIX ORDER SWAPPED (A, B, C, D)", resultsSwapped)

end D3Probe
