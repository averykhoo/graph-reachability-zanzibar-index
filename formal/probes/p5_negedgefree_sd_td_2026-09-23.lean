/-
  P5 step 0 (2026-09-23): the D.3 post-flip probe RE-AIMED at the Direct-arm store
  `W4WitnessDirect.Sd` / `Td4`, the store `outside_narrow_t2a` refutes the T2a bundle at.
  The 2026-09-05 run measured only `LeafWitness.Sw`, so "the obstacle is gone" and "the
  bundle still bites" had never been measured at the same store (P5 row, 2026-09-23 trap).
  Kept OUTSIDE the lake package on purpose -- evidence that can be re-run, not gated build.
  Run from formal/lean (needs the built oleans):

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p5_negedgefree_sd_td_2026-09-23.lean

  Legs, per store:
    (A) drained prefix, then the model's OWN writeLoggedRules, pre-cascade.
    (B) same drained prefix, the pre-flip BARE public edge (writeLoggedOne) -- control.
    (C) (A) + one cascade leg (drained).
    (D) (A) + a hypothetical `<derived>.0 -> <derived>` bridge edge -- instrument control.
  Same routing-independent key domain as the 2026-09-05 probe (objects x predNames^2).
-/
import ZanzibarProofs

open Zanzibar

namespace P5Probe

def predNames (S : Schema) : List String :=
  S.keys.flatMap (fun k => [k.2, leafPred k.2 0, leafPred k.2 1, leafPred k.2 2])

def objsOf (ts : List Tuple) : List ObjectRef :=
  ts.foldl (fun acc t => if acc.contains t.object then acc else acc ++ [t.object]) []

def keyDomain (S : Schema) (ts : List Tuple) : List (NodeKey × String) :=
  (objsOf ts).flatMap (fun o =>
    (predNames S).flatMap (fun p =>
      (predNames S).map (fun r => (objNode o p, r))))

structure ProbeResult where
  edges : Nat
  rows : Nat
  starsRows : Nat
  negTested : Nat
  negFree : Bool
  uposTested : Nat
  uposFree : Bool
deriving Repr

def probe (σ : GraphState) (dom : List (NodeKey × String)) : ProbeResult :=
  dom.foldl (fun acc kr =>
      match σ.residue kr.1 kr.2 with
      | none => acc
      | some res =>
        { acc with
          rows := acc.rows + 1
          starsRows := acc.starsRows + (if res.stars.isEmpty then 0 else 1)
          negTested := acc.negTested + res.neg.length
          negFree := acc.negFree && res.neg.all (fun n => !(σ.reach (subjNode n) kr.1))
          uposTested := acc.uposTested + res.upos.length
          uposFree := acc.uposFree && res.upos.all (fun n => !(σ.reach (subjNode n) kr.1)) })
    { edges := σ.edges.length, rows := 0, starsRows := 0, negTested := 0, negFree := true,
      uposTested := 0, uposFree := true }

/-- One store's four legs. `derived` is the derived relation the bridge control targets. -/
def run (S : Schema) (prefixOps : List GraphOp) (tW : Tuple) (corpus : List Tuple)
    (derived : String) :
    Option (ProbeResult × ProbeResult × ProbeResult × ProbeResult) :=
  let dom := keyDomain S corpus
  (graphRunOps S prefixOps).map (fun p =>
    let σ0 := p.1
    let σA := σ0.writeLoggedRules S tW
    let σB := σ0.writeLoggedOne tW
    let σC := cascadeLeg S (tW :: p.2) σA
    let bridge := (objNode tW.object (leafPred derived 0), objNode tW.object derived)
    let σD := { σA with edges := bridge :: σA.edges }
    (probe σA dom, probe σB dom, probe σC dom, probe σD dom))

def rowsAfter (S : Schema) (prefixOps : List GraphOp) (tW : Tuple) (corpus : List Tuple) :
    Option (List (NodeKey × String × Residue)) :=
  (graphRunOps S prefixOps).map (fun p =>
    let σC := cascadeLeg S (tW :: p.2) (p.1.writeLoggedRules S tW)
    (keyDomain S corpus).filterMap (fun kr =>
      (σC.residue kr.1 kr.2).map (fun res => (kr.1, kr.2, res))))

/-! ## Sd / Td4 -- the Direct-arm corpus store (no wildcard anywhere) -/

def ta : Tuple := ⟨⟨"user", "alice", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩
def tbA : Tuple := ⟨⟨"user", "bob", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩
def tbB : Tuple := ⟨⟨"user", "bob", BARE⟩, "banned", ⟨"doc", "d1"⟩⟩
def tcB : Tuple := ⟨⟨"user", "carol", BARE⟩, "banned", ⟨"doc", "d1"⟩⟩

/-- Prefix = the other three `Td4` tuples; the probe write = bob's Direct-arm grant, so the
    subject write lands on a key that ALSO carries a ban (the D.3 shape, minus the star). -/
def sdPrefix : List GraphOp := [GraphOp.add ta, GraphOp.add tbB, GraphOp.add tcB]
def sdCorpus : List Tuple := [ta, tbA, tbB, tcB]

#eval ("Sd: DOMAIN SIZE", (keyDomain W4WitnessDirect.Sd sdCorpus).length)
#eval ("Sd: declaredWildcardShapes", declaredWildcardShapes W4WitnessDirect.Sd)
#eval ("Sd: rawWriteRels tbA", rawWriteRels W4WitnessDirect.Sd tbA)
#eval ("Sd: PROBE (A subject, B bare-preflip, C drained, D bridge)",
  run W4WitnessDirect.Sd sdPrefix tbA sdCorpus "approver")
#eval ("Sd: DRAINED ROWS (C)", rowsAfter W4WitnessDirect.Sd sdPrefix tbA sdCorpus)

/-! ## Sw -- the 2026-09-05 store, re-run in the SAME file as the positive control -/

def tStarViewer : Tuple := ⟨⟨"user", STAR, BARE⟩, "viewer", ⟨"doc", "d1"⟩⟩
def swPrefix : List GraphOp := [GraphOp.add LeafWitness.tb, GraphOp.add tStarViewer]
def swCorpus : List Tuple := [LeafWitness.tb, tStarViewer, LeafWitness.tw]

#eval ("Sw: DOMAIN SIZE", (keyDomain LeafWitness.Sw swCorpus).length)
#eval ("Sw: PROBE (A subject, B bare-preflip, C drained, D bridge)",
  run LeafWitness.Sw swPrefix LeafWitness.tw swCorpus "approver")

end P5Probe
