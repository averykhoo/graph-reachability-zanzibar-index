/-
  `P4` (leg 7 step 4b) — ATTACK-FIRST probe of the leaf-probe ↔ `directLeaf` bridge,
  house rule 2. Kept OUTSIDE the lake package on purpose: it is not part of the gated
  build, it is evidence that can be re-run. Run from formal/lean (needs built oleans):

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p4_leaf_probe_bridge_2026-09-23.lean

  THE STATEMENT UNDER ATTACK (scope doc §8.1, 2026-08-05):

      probeNonDerived σ ⟨s, leafPred R i, o⟩  =  directLeaf rec s T q rs o.type o.name R

  for every `.storage rs` leaf at allocation index `i` of the derived def `(o.type, R)`,
  on a state reached by the model's OWN write leg.

  SUBJECT  (A): drained state from `graphRunOps`, each side evaluated per (leaf, subject).
  CONTROL  (B): the SAME comparison at a leaf index the allocation did NOT mint
                (one past the LAST leaf of any kind) — both sides must be `false`.
                ⚠ Its first form took "one past the last STORAGE leaf", which on all
                three shapes is a real `.closure` leaf: the control reddened on the
                instrument, not on the subject. Recorded because that is the house
                failure mode (`docs/sabotage-procedure.md`, control your instrument).
  CONTROL  (C): non-vacuity — how many (leaf, subject) rows have LHS `true`. A bridge
                that holds only because both sides are uniformly `false` proves nothing
                (the §C.3 lesson: budget a non-vacuity WITNESS, not just a green run).
  CONTROL  (D): INSTRUMENT sabotage — evaluate the LHS at the PUBLIC name instead of the
                minted leaf name. If (A) and (D) agree everywhere, the probe is blind to
                the very re-addressing it is supposed to measure.
  CONTROL  (E): CROSS-PAIRING — on the fan-out shape, compare leaf `i`'s probe against
                leaf `j≠i`'s restriction list. A bridge that survives cross-pairing is
                not measuring the per-leaf routing at all.
-/
import ZanzibarProofs

open Zanzibar

namespace P4Bridge

/-! ## Enumerating the storage leaves of a derived def -/

/-- Total leaf count of `(ty, R)`, all kinds — the first index the allocation does
    NOT mint. -/
def leafCount (S : Schema) (ty R : String) : Nat :=
  match S.lookup (ty, R) with
  | none => 0
  | some e => (persistedLeaves S ty e).length

/-- `(allocation index, merged restriction list)` for every `.storage` leaf of
    `(ty, R)` — the positions `rawWriteRels` routes a raw write onto. -/
def storageLeaves (S : Schema) (ty R : String) : List (Nat × List Restriction) :=
  match S.lookup (ty, R) with
  | none => []
  | some e => (persistedLeaves S ty e).zipIdx.filterMap fun pi =>
      match pi.1 with
      | .storage rs => some (pi.2, rs)
      | _ => none

/-- Every subject the corpus mentions, deduplicated, plus the shape-star of each —
    a STORE-derived grid, never read off `σ.nodes` (the §9.1 witness trap). -/
def subjectGrid (ts : List Tuple) : List SubjectRef :=
  let base := ts.foldl (fun acc t => if acc.contains t.subject then acc else acc ++ [t.subject]) []
  let stars := base.foldl (fun acc s =>
      let st : SubjectRef := ⟨s.type, STAR, s.predicate⟩
      if acc.contains st then acc else acc ++ [st]) []
  let ghost : SubjectRef := ⟨"user", "nobody", BARE⟩
  base ++ stars ++ [ghost]

/-! ## The instrument -/

structure Row where
  idx : Nat
  subj : SubjectRef
  lhs : Bool
  rhs : Bool
  agree : Bool
deriving Repr

structure Summary where
  rows : Nat
  disagreements : Nat
  lhsTrue : Nat
  rhsTrue : Nat
deriving Repr

/-- One comparison. `atPred` lets control (D) swap the minted leaf name for the public
    one without touching anything else. -/
def compareAt (S : Schema) (σ : GraphState) (T : Store) (o : ObjectRef) (R : String)
    (atPred : String → Nat → String) (subs : List SubjectRef) : List Row :=
  (storageLeaves S o.type R).flatMap fun ir =>
    subs.map fun s =>
      let q : Query := ⟨s, R, o⟩
      let l := GraphModel.probeNonDerived σ ⟨s, atPred R ir.1, o⟩
      let r := directLeaf (GraphModel.graphRec σ s) s T q ir.2 o.type o.name R
      { idx := ir.1, subj := s, lhs := l, rhs := r, agree := l == r }

def summarize (rs : List Row) : Summary :=
  rs.foldl (fun acc r =>
      { rows := acc.rows + 1
        disagreements := acc.disagreements + (if r.agree then 0 else 1)
        lhsTrue := acc.lhsTrue + (if r.lhs then 1 else 0)
        rhsTrue := acc.rhsTrue + (if r.rhs then 1 else 0) })
    { rows := 0, disagreements := 0, lhsTrue := 0, rhsTrue := 0 }

/-! ## Shapes — three allocations, chosen so the index is not always 0 -/

/-- `approver := ([user] or viewer) but not banned` — one storage leaf, index 0. -/
abbrev S1 : Schema := LeafWitness.Sw
/-- `approver := (viewer but not banned) or [user]` — storage leaf at index **2**. -/
abbrev S2 : Schema := LeafWitness.SwU
/-- `approver := [user] or ([user, employee] but not banned)` — **two** storage leaves. -/
abbrev S3 : Schema := LeafWitness.SwF

def d1 : ObjectRef := ⟨"doc", "d1"⟩

def opsOf (ts : List Tuple) : List GraphOp := ts.map GraphOp.add

/-- Corpus for `S1`/`S2`: a bare grant on the derived relation, a wildcard `viewer`,
    and a `banned` row, so the exclusion arm is live. -/
def c12 : List Tuple :=
  [⟨⟨"user", "bob", BARE⟩, "banned", d1⟩,
   ⟨⟨"user", STAR, BARE⟩, "viewer", d1⟩,
   ⟨⟨"user", "bob", BARE⟩, "approver", d1⟩,
   ⟨⟨"user", "alice", BARE⟩, "approver", d1⟩]

/-- Corpus for `S3`: `alice` fans out onto BOTH storage leaves, `employee:carol` onto
    the second only (`LeafWitness.swF_fanout` / `::swF_second_only`). -/
def c3 : List Tuple :=
  [⟨⟨"user", "bob", BARE⟩, "banned", d1⟩,
   ⟨⟨"user", "alice", BARE⟩, "approver", d1⟩,
   ⟨⟨"employee", "carol", BARE⟩, "approver", d1⟩]

/-- Run one shape and return (A, B, C-as-part-of-A, D). -/
def runShape (S : Schema) (corpus : List Tuple) :
    Option (List Row × Summary × Summary × Summary) :=
  (graphRunOps S (opsOf corpus)).map fun p =>
    let σ := p.1
    let T := p.2
    let subs := subjectGrid corpus
    let A := compareAt S σ T d1 "approver" leafPred subs
    -- (B) one index past the last minted leaf OF ANY KIND
    let unminted := leafCount S "doc" "approver"
    let B := (subs.map fun s =>
        let q : Query := ⟨s, "approver", d1⟩
        let l := GraphModel.probeNonDerived σ ⟨s, leafPred "approver" unminted, d1⟩
        let r := directLeaf (GraphModel.graphRec σ s) s T q [] "doc" "d1" "approver"
        { idx := unminted, subj := s, lhs := l, rhs := r, agree := l == r })
    -- (D) instrument sabotage: probe the PUBLIC name, keep the RHS unchanged
    let D := compareAt S σ T d1 "approver" (fun R _ => R) subs
    (A, summarize A, summarize B, summarize D)

/-- **Control (E) — cross-pairing.** Leaf `i`'s probe against leaf `j`'s restrictions,
    for every ordered pair `i ≠ j` of STORAGE leaves. -/
def crossRows (S : Schema) (corpus : List Tuple) : Option (List Row × Summary) :=
  (graphRunOps S (opsOf corpus)).map fun p =>
    let σ := p.1
    let T := p.2
    let subs := subjectGrid corpus
    let ls := storageLeaves S "doc" "approver"
    let rows := ls.flatMap fun ir =>
      (ls.filter (fun jr => jr.1 != ir.1)).flatMap fun jr =>
        subs.map fun s =>
          let q : Query := ⟨s, "approver", d1⟩
          let l := GraphModel.probeNonDerived σ ⟨s, leafPred "approver" ir.1, d1⟩
          let r := directLeaf (GraphModel.graphRec σ s) s T q jr.2 "doc" "d1" "approver"
          { idx := ir.1, subj := s, lhs := l, rhs := r, agree := l == r }
    (rows, summarize rows)

/-! ## Output -/

#eval ("STORAGE LEAVES S1", storageLeaves S1 "doc" "approver")
#eval ("STORAGE LEAVES S2", storageLeaves S2 "doc" "approver")
#eval ("STORAGE LEAVES S3", storageLeaves S3 "doc" "approver")

#eval ("DRAINED? S1/S2/S3",
  ((graphRunOps S1 (opsOf c12)).map (fun p => drainedB S1 p.1),
   (graphRunOps S2 (opsOf c12)).map (fun p => drainedB S2 p.1),
   (graphRunOps S3 (opsOf c3)).map (fun p => drainedB S3 p.1)))

#eval ("S1 (A summary, B summary, D summary)", (runShape S1 c12).map (fun r => (r.2.1, r.2.2.1, r.2.2.2)))
#eval ("S2 (A summary, B summary, D summary)", (runShape S2 c12).map (fun r => (r.2.1, r.2.2.1, r.2.2.2)))
#eval ("S3 (A summary, B summary, D summary)", (runShape S3 c3).map (fun r => (r.2.1, r.2.2.1, r.2.2.2)))

#eval ("S1 DISAGREEING ROWS", (runShape S1 c12).map (fun r => r.1.filter (fun x => !x.agree)))
#eval ("S2 DISAGREEING ROWS", (runShape S2 c12).map (fun r => r.1.filter (fun x => !x.agree)))
#eval ("S3 DISAGREEING ROWS", (runShape S3 c3).map (fun r => r.1.filter (fun x => !x.agree)))

#eval ("LEAF COUNTS S1/S2/S3", (leafCount S1 "doc" "approver", leafCount S2 "doc" "approver", leafCount S3 "doc" "approver"))
#eval ("S3 CROSS-PAIR CONTROL (E)", (crossRows S3 c3).map (·.2))
#eval ("S3 CROSS-PAIR DISAGREEING ROWS", (crossRows S3 c3).map (fun r => r.1.filter (fun x => !x.agree)))

#eval ("S1 ALL ROWS", (runShape S1 c12).map (·.1))
#eval ("S3 ALL ROWS", (runShape S3 c3).map (·.1))

end P4Bridge

namespace P4Bridge

/-! ## Tally form — the exact shape landed in `GraphIndex/Exec.lean`

The three definitions below are **byte-identical** to the ones landed in the gated tree
(`Exec.lean`, `P4` block). They live here too so this probe can compute the tallies the
landed `by decide` theorems pin, without a build-read-build cycle whose two halves could
drift. -/

namespace Landed

structure BridgeTally where
  rows : Nat
  agree : Nat
  bothTrue : Nat
deriving Repr, DecidableEq

def storageLeaves (S : Schema) (ty R : String) : List (Nat × List Restriction) :=
  match S.lookup (ty, R) with
  | none => []
  | some e => (persistedLeaves S ty e).zipIdx.filterMap fun pi =>
      match pi.1 with
      | .storage rs => some (pi.2, rs)
      | _ => none

def bridgeTally (σ : GraphState) (T : Store) (o : ObjectRef) (R : String)
    (pairs : List (String × List Restriction)) (subs : List SubjectRef) : BridgeTally :=
  pairs.foldl (fun acc pr =>
      subs.foldl (fun a s =>
          let l := GraphModel.probeNonDerived σ ⟨s, pr.1, o⟩
          let r := directLeaf (GraphModel.graphRec σ s) s T ⟨s, R, o⟩ pr.2 o.type o.name R
          { rows := a.rows + 1
            agree := a.agree + (if l == r then 1 else 0)
            bothTrue := a.bothTrue + (if l && r then 1 else 0) })
        acc)
    ⟨0, 0, 0⟩

end Landed

def pairsLeaf (S : Schema) : List (String × List Restriction) :=
  (Landed.storageLeaves S "doc" "approver").map (fun ir => (leafPred "approver" ir.1, ir.2))

def pairsPublic (S : Schema) : List (String × List Restriction) :=
  (Landed.storageLeaves S "doc" "approver").map (fun ir => ("approver", ir.2))

/-- Cross-paired: leaf `i`'s NAME against leaf `j`'s RESTRICTIONS, `i ≠ j`. -/
def pairsCross (S : Schema) : List (String × List Restriction) :=
  let ls := Landed.storageLeaves S "doc" "approver"
  ls.flatMap fun ir =>
    (ls.filter (fun jr => jr.1 != ir.1)).map fun jr => (leafPred "approver" ir.1, jr.2)

def gridSw : List SubjectRef :=
  [⟨"user", "bob", BARE⟩, ⟨"user", "alice", BARE⟩, ⟨"user", STAR, BARE⟩,
   ⟨"user", "nobody", BARE⟩, ⟨"user", "alice", "viewer"⟩]

def gridSwF : List SubjectRef :=
  [⟨"user", "alice", BARE⟩, ⟨"employee", "carol", BARE⟩, ⟨"user", "bob", BARE⟩,
   ⟨"user", STAR, BARE⟩, ⟨"employee", "nobody", BARE⟩]

def tallyOf (S : Schema) (corpus : List Tuple)
    (mk : Schema → List (String × List Restriction)) (grid : List SubjectRef) :
    Option (Bool × Landed.BridgeTally) :=
  (graphRunOps S (corpus.map GraphOp.add)).map fun p =>
    (drainedB S p.1, Landed.bridgeTally p.1 p.2 d1 "approver" (mk S) grid)

#eval ("Sw  LEAF   ", tallyOf S1 c12 pairsLeaf gridSw)
#eval ("Sw  PUBLIC ", tallyOf S1 c12 pairsPublic gridSw)
#eval ("SwU LEAF   ", tallyOf S2 c12 pairsLeaf gridSw)
#eval ("SwU PUBLIC ", tallyOf S2 c12 pairsPublic gridSw)
#eval ("SwF LEAF   ", tallyOf S3 c3 pairsLeaf gridSwF)
#eval ("SwF CROSS  ", tallyOf S3 c3 pairsCross gridSwF)
#eval ("SwF PUBLIC ", tallyOf S3 c3 pairsPublic gridSwF)

end P4Bridge
