/-
  ★ P6 PART (iv) PAYOFF PROBE (2026-09-14) — re-measure the answer gap on the LIVE
  post-part-(ii) write leg.

  WHY. The `2026-09-13b` entry on task `P6` measured `baseMismatch := 14 →
  bridgedMismatch := 9` at the in-scope store `Sp`: a CANDIDATE bridging routing (`legB`)
  narrowed the answer gap but did NOT close it. Part (ii) has since LANDED (step 3b,
  2026-09-14e): `Cascade.lean:508::GraphState.bridgePreLogged` is composed into
  `::writeLoggedOne`, and `LeafRules.lean::GraphState.writeRulesRaw` folds `writeBridgedOne`.
  So the arm that was called "base" on 2026-09-13b — `σ.writeLoggedRules S t` — IS the
  bridged leg today.

  Nobody has re-measured it. That number decides whether `P6` part (iv) is INHABITABLE at
  all: if the live leg still mismatches `sem` at the store `TtuStarFreeW` newly admits, then
  widening `FullScope.lean:340::W4Fragment.ttuStarFree` would admit stores the graph answers
  WRONGLY on, and part (iv) must not be attempted before that gap is understood. Measuring
  it costs one probe; paying the part (iv) cone costs a session.

  Schema, corpus, domains and grid are copied VERBATIM from
  `p6_inbridge_stability_2026-09-12.lean` §1-§2/§6 so the numbers are comparable to the
  `14 → 9` on the row. Kept outside the lake package: zero cone, ungated, re-runnable.

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_partiv_live_leg_payoff_2026-09-14.lean

  ⚠ rc=0 with NO output is a FAILED run, not a green one.
  ⚠ A `liveMismatch := 0` is only believable beside `POSITIVE CONTROL` being NONZERO and
    `semTrue` being NONZERO. A grid that compared nothing agrees perfectly.

  ── THE VERDICT (2026-09-14) ──────────────────────────────────────────────────────────────

  **`14 → 2`, and the residual `2` is NOT a generic materialisation gap.**

  1. The widening is ENGAGED at this store: `(1)` narrow `false`, wide `true`; and `(8)` says
     the store fails EXACTLY `ttuStarFree` among `storeValidRules / bareStarStore /
     ttuStarFree / hterm`. So whatever `(4)` measures is attributable to the one condition
     part (iv) widens, not to some other fragment field.
  2. `(4)` `liveMismatch := 2` on a grid of `546`, against `14` for the same expression on
     2026-09-13b and `9` for that date's candidate routing. **Part (ii) did most of the
     work the candidate routing only approximated**, and it did it on the shipped leg.
  3. The instrument is live: `ctlNoWrite := 8` (a state that never saw the write DOES
     mismatch) and `semTrue := 25` (the grid is not uniformly `False`). A `0` here would have
     been believable; a `0` without these two would not.
  4. `(10)` **ARM A — materialise `folder:f9` and the count goes to `0`**, with `semTrue`
     rising to `29`. `(11)` ARM B — drop `f9` from the domain and it is also `0`. The two
     divergent queries `(5)` are both at the UNMATERIALISED userset subject
     `folder:f9#viewer`, whose only mention is the domain-only tuple `tDom`.
  5. `(12)` is the one that says the BRIDGE WORKS: at that same unmaterialised subject,
     `access` — the TTU relation the star-tupleset bridge actually serves — is
     `check = sem = true`. The divergence is confined to `admin` and `gate`, both DERIVED.
     An incomplete bridge would have failed at `access` first.

  ⚠ **BUT the obvious explanation is REFUTED, so do not write it down.** "Derived relations
  over a never-written node are always empty" is ruled out by `(15)`: CONTROL 2 puts a
  derived relation above a star-USERSET grant with no `ttu` arm anywhere, asks the same
  question at the same unmaterialised subject, and gets `mismatch := 0` with `semTrue := 16`
  — i.e. the situation WAS built and the graph answered it correctly. So the residue is
  specific to the star-TUPLESET through-shape with a derived relation above it, and the
  next increment owes an explanation of that asymmetry.

  ⚠ `(14)` is **INERT** and attributes nothing — `semTrue := 2` shows the edit never built the
  situation. It is kept, and labelled, because an inert control reads exactly like a clean
  one (`docs/sabotage-procedure.md`). `(6)`/`(7)`/`(9)` likewise: that control is INVALID —
  `(9)` shows the concrete-parent store fails `storeValidRules`, so its `2` is a different
  phenomenon at a different pair of queries, not a comparison.

  **Consequence for part (iv):** the flip is NOT unconditionally safe. `W4Fragment` widened
  to `TtuStarFreeW` would admit this store, and at it `check ≠ sem` for two queries unless
  some other fragment field, admission field, or query-subject scoping excludes an
  unmaterialised userset subject. Settling that is the first thing part (iv) owes — before
  step 1 of the plan, not after. See `docs/p6-part-iv-plan-2026-09-14.md`.

  ── LITERAL TRANSCRIPT (the run's own stdout; nothing added, removed or reordered) ─────────

  RAN 2026-09-14, rc=0, from `formal/lean` via
  `export PATH="$HOME/.elan/bin:$PATH" && lake env lean ../probes/p6_partiv_live_leg_payoff_2026-09-14.lean`.

  --------------------------------- BEGIN VERBATIM -----------------------------------------

("(1) widening engaged at Sp: (narrow ttuStarFreeB, wide ttuStarFreeWB) over corpus", false, true)
("(2) the through-shape (folder,viewer): (isStarTuplesetThrough, isSubjectWildcardUserset)", true, true)
("(3) ttu arm survives the taint filter -- NON-VACUITY",
 [{ objectType := "doc", matchRel := "parent", outRel := "access", kind := Zanzibar.RuleKind.ttu "viewer" }])
("(4) ★ PAYOFF -- live post-(ii) leg vs sem",
 some { gridSize := 546, semTrue := 25, liveDrained := true, liveMismatch := 2, ctlNoWrite := 8 })
("(5) ★ the divergent queries (check, sem)",
 some [({ subject := { type := "folder", name := "f9", predicate := "viewer" },
     relation := "admin",
     object := { type := "doc", name := "d1" } },
   false,
   true),
  ({ subject := { type := "folder", name := "f9", predicate := "viewer" },
     relation := "gate",
     object := { type := "doc", name := "d1" } },
   false,
   true)])
("(6) CONTROL -- concrete tupleset parent (inside today's fragment); must mismatch 0", true, some (546, 11, true, 2))
("(7) ★ CONTROL's divergent queries -- SAME as (5) or DIFFERENT?",
 some [({ subject := { type := "folder", name := "f1", predicate := "..." },
     relation := "parent",
     object := { type := "doc", name := "d1" } },
   true,
   false),
  ({ subject := { type := "folder", name := "f1", predicate := "..." },
     relation := "parent",
     object := { type := "doc", name := "d1" } },
   true,
   false)])
("(8) deciders (storeValidRules, bareStarStore, ttuStarFree, hterm) -- STAR store", some (true, true, false, true))
("(9) deciders -- CONTROL store (concrete tupleset parent)", some (false, true, true, true))
("(10) ARM A -- folder:f9 MATERIALISED (grid, semTrue, mismatch, which)", some (546, 29, 0, []))
("(11) ARM B -- folder:f9 out of the DOMAIN (grid, semTrue, mismatch)", some (408, 21, 0))
("(12) ★ side by side (label, check, sem)",
  some
    [("f1#viewer admin d1 (MATERIALISED)", true, true), ("f9#viewer admin d1 (UNMATERIALISED)", false, true),
      ("f1#viewer access d1 (MATERIALISED)", true, true), ("f9#viewer access d1 (UNMATERIALISED)", true, true)])
("(13) CONTROL schema: no ttu arm, so TtuStarFree holds outright", [], true)
("(14) ★ CONTROL -- unmaterialised userset at a DERIVED relation, no TTU anywhere", some (150, 2, 0, []))
("(15) ★ CONTROL 2 -- star USERSET grant, no ttu; (grid, semTrue, mismatch, ttuStarFree, which)",
 some (150, 16, 0, true, []))

  ----------------------------------- END VERBATIM -----------------------------------------
-/
import ZanzibarProofs

open Zanzibar

namespace P6PartIvPayoffProbe

/-! ## §1 The store — `p6_inbridge_stability_2026-09-12.lean:504-537`, verbatim -/

def Sp : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, true)]),
    (("doc", "access"),    .ttu "viewer" "parent"),
    (("doc", "banned"),    .direct [("user", BARE, false), ("folder", "viewer", false)]),
    (("doc", "admin"),     .excl (.computed "access") (.computed "banned")),
    (("doc", "gate"),      .inter (.computed "admin") (.computed "access"))], []⟩

def tPar : Tuple := ⟨⟨"folder", STAR, BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def tView : Tuple := ⟨⟨"user", "alice", BARE⟩, "viewer", ⟨"folder", "f1"⟩⟩
def tObj : Tuple := ⟨⟨"user", "bob", BARE⟩, "viewer", ⟨"folder", "f2"⟩⟩
def tSub : Tuple := ⟨⟨"folder", "f1", "viewer"⟩, "banned", ⟨"doc", "d2"⟩⟩
def tAdm : Tuple := ⟨⟨"user", "dave", BARE⟩, "admin", ⟨"doc", "d1"⟩⟩
def tDom : Tuple := ⟨⟨"user", "carol", BARE⟩, "viewer", ⟨"folder", "f9"⟩⟩

def corpus : List Tuple := [tPar, tView, tObj, tSub, tAdm, tDom]
def prefixOps : List GraphOp := [GraphOp.add tPar, GraphOp.add tView]

/-! ## §2 Routing-independent domains — schema+corpus only, NEVER `σ.nodes`/`σ.edges` -/

def subjPreds (S : Schema) : List String := BARE :: S.keys.map (·.2)

def objsOf (ts : List Tuple) : List ObjectRef :=
  ts.foldl (fun acc t => if acc.contains t.object then acc else acc ++ [t.object]) []

def subjsOf (ts : List Tuple) : List SubjectRef :=
  ts.foldl (fun acc t => if acc.contains t.subject then acc else acc ++ [t.subject]) []

def subjDomain (S : Schema) (ts : List Tuple) : List SubjectRef :=
  subjsOf ts ++ (wildcardShapes S).map starSubj
    ++ (objsOf ts).flatMap (fun o => (subjPreds S).map (fun p => ⟨o.type, o.name, p⟩))

def queryGrid (S : Schema) (ts : List Tuple) : List Query :=
  S.keys.flatMap (fun k =>
    (objsOf ts).flatMap (fun o =>
      if o.type == k.1 then (subjDomain S ts).map (fun s => ⟨s, k.2, o⟩) else []))

def GRID : List Query := queryGrid Sp corpus

/-! ## §3 Is the widening ENGAGED at this store? -/

#eval ("(1) widening engaged at Sp: (narrow ttuStarFreeB, wide ttuStarFreeWB) over corpus",
        ttuStarFreeB Sp corpus, ttuStarFreeWB Sp corpus)
#eval ("(2) the through-shape (folder,viewer): (isStarTuplesetThrough, isSubjectWildcardUserset)",
        Sp.isStarTuplesetThrough "folder" "viewer",
        Sp.isSubjectWildcardUserset "folder" "viewer")
#eval ("(3) ttu arm survives the taint filter -- NON-VACUITY", schemaRewrites Sp)

/-! ## §4 THE MEASUREMENT — the live leg against `sem`

`liveMismatch` is the `2026-09-13b` row's `baseMismatch` recomputed today. On that date the
same expression measured `14`, with a candidate routing reaching `9`. -/

structure Payoff where
  gridSize      : Nat
  semTrue       : Nat          -- NON-VACUITY: how many grid queries `sem` answers TRUE
  liveDrained   : Bool
  liveMismatch  : Nat          -- ★ THE NUMBER
  ctlNoWrite    : Nat          -- POSITIVE CONTROL: must be NONZERO
deriving Repr

def payoff : Option Payoff :=
  (graphRunOps Sp prefixOps).map (fun p =>
    let σ0 := p.1
    let T0 := p.2
    let To := tObj :: T0
    let miss := fun (σ : GraphState) (T : Store) =>
      (GRID.filter (fun q => !(GraphModel.check σ q == sem Sp T q))).length
    -- the LIVE post-(ii) leg: `writeLoggedRules` now folds the bridged write
    let dLive := cascadeLeg Sp To (σ0.writeLoggedRules Sp tObj)
    { gridSize     := GRID.length
      semTrue      := (GRID.filter (fun q => sem Sp To q)).length
      liveDrained  := drainedB Sp dLive
      liveMismatch := miss dLive To
      -- POSITIVE CONTROL: the same grid against a state that never saw the write.
      -- If this is 0 the instrument cannot see a difference and NO number here means
      -- anything.
      ctlNoWrite   := miss (cascadeLeg Sp To σ0) To })

#eval ("(4) ★ PAYOFF -- live post-(ii) leg vs sem", payoff)

/-! ## §5 WHERE it still disagrees, if it does

A count is not a diagnosis. If `liveMismatch` is nonzero, these are the actual queries and
the direction of each disagreement (`check` first, `sem` second), so the next session reads a
shape rather than a number. -/

def divergences : Option (List (Query × Bool × Bool)) :=
  (graphRunOps Sp prefixOps).map (fun p =>
    let To := tObj :: p.2
    let dLive := cascadeLeg Sp To (p.1.writeLoggedRules Sp tObj)
    GRID.filterMap (fun q =>
      let c := GraphModel.check dLive q
      let s := sem Sp To q
      if c == s then none else some (q, c, s)))

#eval ("(5) ★ the divergent queries (check, sem)", divergences)

/-! ## §6 Is the STAR tupleset the cause?

CONTROL: the same everything with the star tupleset parent `tPar` replaced by a CONCRETE
one. Today's narrow `TtuStarFree` reaches that store, so it is inside the PROVED fragment
and must agree. A nonzero count here would mean §4's number is not about the widening. -/

def tParC : Tuple := ⟨⟨"folder", "f1", BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def corpusC : List Tuple := [tParC, tView, tObj, tSub, tAdm, tDom]
def prefixOpsC : List GraphOp := [GraphOp.add tParC, GraphOp.add tView]
def GRIDC : List Query := queryGrid Sp corpusC

def payoffConcrete : Option (Nat × Nat × Bool × Nat) :=
  (graphRunOps Sp prefixOpsC).map (fun p =>
    let To := tObj :: p.2
    let dLive := cascadeLeg Sp To (p.1.writeLoggedRules Sp tObj)
    (GRIDC.length,
     (GRIDC.filter (fun q => sem Sp To q)).length,
     drainedB Sp dLive,
     (GRIDC.filter (fun q => !(GraphModel.check dLive q == sem Sp To q))).length))

#eval ("(6) CONTROL -- concrete tupleset parent (inside today's fragment); must mismatch 0",
        ttuStarFreeB Sp corpusC, payoffConcrete)

/-- ⚠ The run of 2026-09-14 returned `2` here as well, so the count ALONE cannot attribute
    §4's `2` to the widening. The only thing that settles it is WHICH queries diverge: if the
    control's two are the same two, the residue is a pre-existing gap that has nothing to do
    with the star tupleset, and §4's number is not a part-(iv) obstacle at all. -/
def divergencesConcrete : Option (List (Query × Bool × Bool)) :=
  (graphRunOps Sp prefixOpsC).map (fun p =>
    let To := tObj :: p.2
    let dLive := cascadeLeg Sp To (p.1.writeLoggedRules Sp tObj)
    GRIDC.filterMap (fun q =>
      let c := GraphModel.check dLive q
      let s := sem Sp To q
      if c == s then none else some (q, c, s)))

#eval ("(7) ★ CONTROL's divergent queries -- SAME as (5) or DIFFERENT?", divergencesConcrete)

/-! ## §7 Is either store even inside the proved fragment?

`ttuStarFree` is ONE of `W4Fragment`'s ten fields. A divergence at a store that fails some
OTHER field refutes nothing that is proved — but it has to be MEASURED, not assumed, or the
numbers above get read as a correctness finding they do not support. -/

def fragmentDeciders (T : Store) : Bool × Bool × Bool × Bool :=
  (storeValidRulesB Sp T, bareStarStoreB T, ttuStarFreeB Sp T, htermB Sp T)

#eval ("(8) deciders (storeValidRules, bareStarStore, ttuStarFree, hterm) -- STAR store",
        (graphRunOps Sp prefixOps).map (fun p => fragmentDeciders (tObj :: p.2)))
#eval ("(9) deciders -- CONTROL store (concrete tupleset parent)",
        (graphRunOps Sp prefixOpsC).map (fun p => fragmentDeciders (tObj :: p.2)))

/-! ## §8 ATTRIBUTION — is the residual `2` the WIDENING, or an UNMATERIALISED node?

§6's control was INVALID: `(9)` shows the concrete-parent store fails `storeValidRules`
(`doc#parent` declares `[folder:*]`, so a concrete `folder:f1` subject is not admissible),
and its two divergences `(7)` are a different shape entirely. It attributes nothing.

The honest attribution runs on the STAR store, which `(8)` shows fails EXACTLY `ttuStarFree`
and none of the other measured conditions. Both divergent subjects are `folder:f9#viewer`,
and `folder:f9` appears ONLY in `tDom` — which is domain-only and is NEVER written
(`prefixOps` adds `tPar` and `tView`; the probe write is `tObj`). `folder:f1#viewer` IS
materialised, is in the same grid, and does NOT diverge.

So the competing explanation is: the graph cannot answer a SELF-REFERENTIAL userset query
about an object it has never seen, and that has nothing to do with the star tupleset. The
two arms below separate the hypotheses.

* **ARM A — materialise `folder:f9`** by writing `tDom` in the prefix. If the widening is the
  cause, the count stays `2`; if materialisation is the cause, it drops to `0`.
* **ARM B — drop `tDom` from the corpus** so `folder:f9` leaves the DOMAIN. Same prediction,
  from the other side. -/

def prefixOpsA : List GraphOp := [GraphOp.add tPar, GraphOp.add tView, GraphOp.add tDom]

def armA : Option (Nat × Nat × Nat × List (Query × Bool × Bool)) :=
  (graphRunOps Sp prefixOpsA).map (fun p =>
    let To := tObj :: p.2
    let dLive := cascadeLeg Sp To (p.1.writeLoggedRules Sp tObj)
    (GRID.length, (GRID.filter (fun q => sem Sp To q)).length,
     (GRID.filter (fun q => !(GraphModel.check dLive q == sem Sp To q))).length,
     GRID.filterMap (fun q =>
       let c := GraphModel.check dLive q
       let s := sem Sp To q
       if c == s then none else some (q, c, s))))

#eval ("(10) ARM A -- folder:f9 MATERIALISED (grid, semTrue, mismatch, which)", armA)

def corpusB : List Tuple := [tPar, tView, tObj, tSub, tAdm]
def GRIDB : List Query := queryGrid Sp corpusB

def armB : Option (Nat × Nat × Nat) :=
  (graphRunOps Sp prefixOps).map (fun p =>
    let To := tObj :: p.2
    let dLive := cascadeLeg Sp To (p.1.writeLoggedRules Sp tObj)
    (GRIDB.length, (GRIDB.filter (fun q => sem Sp To q)).length,
     (GRIDB.filter (fun q => !(GraphModel.check dLive q == sem Sp To q))).length))

#eval ("(11) ARM B -- folder:f9 out of the DOMAIN (grid, semTrue, mismatch)", armB)

/-- The two specific queries, side by side: a MATERIALISED userset subject and an
    UNMATERIALISED one, at the same relation and object, on the unmodified star store. -/
def sideBySide : Option (List (String × Bool × Bool)) :=
  (graphRunOps Sp prefixOps).map (fun p =>
    let To := tObj :: p.2
    let dLive := cascadeLeg Sp To (p.1.writeLoggedRules Sp tObj)
    [("f1#viewer admin d1 (MATERIALISED)",
      GraphModel.check dLive ⟨⟨"folder", "f1", "viewer"⟩, "admin", ⟨"doc", "d1"⟩⟩,
      sem Sp To ⟨⟨"folder", "f1", "viewer"⟩, "admin", ⟨"doc", "d1"⟩⟩),
     ("f9#viewer admin d1 (UNMATERIALISED)",
      GraphModel.check dLive ⟨⟨"folder", "f9", "viewer"⟩, "admin", ⟨"doc", "d1"⟩⟩,
      sem Sp To ⟨⟨"folder", "f9", "viewer"⟩, "admin", ⟨"doc", "d1"⟩⟩),
     ("f1#viewer access d1 (MATERIALISED)",
      GraphModel.check dLive ⟨⟨"folder", "f1", "viewer"⟩, "access", ⟨"doc", "d1"⟩⟩,
      sem Sp To ⟨⟨"folder", "f1", "viewer"⟩, "access", ⟨"doc", "d1"⟩⟩),
     ("f9#viewer access d1 (UNMATERIALISED)",
      GraphModel.check dLive ⟨⟨"folder", "f9", "viewer"⟩, "access", ⟨"doc", "d1"⟩⟩,
      sem Sp To ⟨⟨"folder", "f9", "viewer"⟩, "access", ⟨"doc", "d1"⟩⟩)])

#eval ("(12) ★ side by side (label, check, sem)", sideBySide)

/-! ## §9 THE ATTRIBUTION CONTROL — the same gap with NO TTU AT ALL

`(12)` already shows the divergence is confined to the DERIVED relations `admin`/`gate`
while `access` — the TTU the star bridge actually serves — AGREES at the unmaterialised
subject. That is the opposite of what an incomplete star-tupleset bridge would look like.

This control removes the TTU entirely. `Sw` grants `doc#access` through a WILDCARD USERSET
restriction `[folder:*#viewer]` instead, so `schemaRewrites Sw` has no `ttu` arm and
`TtuStarFree` is satisfied outright — today's narrow fragment reaches this schema. If the
unmaterialised-subject divergence at `admin` reproduces here, it is a PRE-EXISTING property
of derived relations over never-written nodes and is **not** part (iv)'s problem. -/

def Sw : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "access"),    .direct [("folder", "viewer", true)]),
    (("doc", "banned"),    .direct [("user", BARE, false)]),
    (("doc", "admin"),     .excl (.computed "access") (.computed "banned"))], []⟩

def wView : Tuple := ⟨⟨"user", "alice", BARE⟩, "viewer", ⟨"folder", "f1"⟩⟩
def wObj : Tuple := ⟨⟨"user", "bob", BARE⟩, "viewer", ⟨"folder", "f2"⟩⟩
def wDom : Tuple := ⟨⟨"user", "carol", BARE⟩, "viewer", ⟨"folder", "f9"⟩⟩
def wCorpus : List Tuple := [wView, wObj, wDom, ⟨⟨"user", "dave", BARE⟩, "access", ⟨"doc", "d1"⟩⟩]
def wPrefix : List GraphOp := [GraphOp.add wView]
def GRIDW : List Query := queryGrid Sw wCorpus

#eval ("(13) CONTROL schema: no ttu arm, so TtuStarFree holds outright",
        schemaRewrites Sw, ttuStarFreeB Sw wCorpus)

def armControl : Option (Nat × Nat × Nat × List (Query × Bool × Bool)) :=
  (graphRunOps Sw wPrefix).map (fun p =>
    let To := wObj :: p.2
    let dLive := cascadeLeg Sw To (p.1.writeLoggedRules Sw wObj)
    (GRIDW.length, (GRIDW.filter (fun q => sem Sw To q)).length,
     (GRIDW.filter (fun q => !(GraphModel.check dLive q == sem Sw To q))).length,
     GRIDW.filterMap (fun q =>
       let c := GraphModel.check dLive q
       let s := sem Sw To q
       if c == s then none else some (q, c, s))))

#eval ("(14) ★ CONTROL -- unmaterialised userset at a DERIVED relation, no TTU anywhere",
        armControl)

/-! ### ⚠ `(14)` is INERT, and that must be said out loud

`(14)` returned `0` divergences — but `semTrue := 2` shows it never built the situation it
was meant to build. `doc#access := [folder:*#viewer]` is a DIRECT restriction, so `sem` only
grants it where a TUPLE exists; no unmaterialised userset is ever granted `access`, so the
derived relation above it was never asked the question. The edit did not move the property
under test (`docs/sabotage-procedure.md`; the `M12` failure mode). It attributes nothing.

`Sw2` below is the same idea built correctly: the grant is a STORED tuple whose SUBJECT is
the wildcard userset `folder:*#viewer`, so `sem` grants `access` on `d1` to every
`folder:X#viewer` INCLUDING the unmaterialised `f9`, and `doc#admin := access but not banned`
puts a DERIVED relation above it. Still no `ttu` arm anywhere.

⚠ Honest scope: this store carries a non-`BARE` star subject, so it fails `BareStarStore` —
it is outside today's fragment for a reason unrelated to `ttuStarFree`. It is offered as an
attribution control for the MECHANISM, not as a fragment claim. -/

def Sw2 : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "access"),    .direct [("user", BARE, false), ("folder", "viewer", true)]),
    (("doc", "banned"),    .direct [("user", BARE, false)]),
    (("doc", "admin"),     .excl (.computed "access") (.computed "banned"))], []⟩

/-- The star USERSET grant: `folder:*#viewer` has `access` on `doc:d1`. -/
def wStar : Tuple := ⟨⟨"folder", STAR, "viewer"⟩, "access", ⟨"doc", "d1"⟩⟩
def w2Corpus : List Tuple := [wStar, wView, wObj, wDom]
def w2Prefix : List GraphOp := [GraphOp.add wStar, GraphOp.add wView]
def GRIDW2 : List Query := queryGrid Sw2 w2Corpus

def armControl2 : Option (Nat × Nat × Nat × Bool × List (Query × Bool × Bool)) :=
  (graphRunOps Sw2 w2Prefix).map (fun p =>
    let To := wObj :: p.2
    let dLive := cascadeLeg Sw2 To (p.1.writeLoggedRules Sw2 wObj)
    (GRIDW2.length, (GRIDW2.filter (fun q => sem Sw2 To q)).length,
     (GRIDW2.filter (fun q => !(GraphModel.check dLive q == sem Sw2 To q))).length,
     ttuStarFreeB Sw2 To,
     GRIDW2.filterMap (fun q =>
       let c := GraphModel.check dLive q
       let s := sem Sw2 To q
       if c == s then none else some (q, c, s))))

#eval ("(15) ★ CONTROL 2 -- star USERSET grant, no ttu; (grid, semTrue, mismatch, ttuStarFree, which)",
        armControl2)

end P6PartIvPayoffProbe
