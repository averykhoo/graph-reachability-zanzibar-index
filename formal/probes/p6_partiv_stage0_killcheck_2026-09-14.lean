/-
  ★ P6 PART (iv) — STAGE 0, THE KILL-CHECK (2026-09-14g).

  WHY. The `D1-split` decision (task row `P6`, 2026-09-14g) commits to correcting
  `GraphIndex/ReconcileStars.lean:97::wildcardShapes` to match the shipped two-pass
  `zanzibar_utils_v1.py::SchemaInfo.subject_wildcard_shapes`, and to re-pointing
  `FullScope.lean::W4Fragment.wsBare` at a `declaredWildcardShapes` so the fragment does not
  shrink. That cone is `235` references across `18` files.

  Before paying it, one question decides whether part (iv) gets anything for the money:

      does the corrected enumeration take BOTH divergent queries to `check = sem`,
      or does `gate` survive on the SECOND defect?

  The second defect is `formal/CORRESPONDENCE.md:1213` §7 — `GraphState.checkFn`, the
  proof-side reader that *computes* coverage, under-reads a derived relation at a userset
  subject. `gate` is stratum-2. `admin` is not. If `gate` survives, part (iv) additionally
  needs the stratum-2 `checkFn` repair, which is a separate cone and a re-pricing, not a
  continuation.

  This is the repo's own rule — the kill, made before the cone is paid.

  HOW. `wildcardShapes` is used INSIDE the live cascade, so the corrected list cannot be
  injected without editing shipped source. Instead this probe reproduces the fold's own
  formula from `CascadeStrata.lean:187::reconcileResidueKeyR` —

      stars := shapes.filter (fun sh => coveredFn …)
      neg   := negCands.filter  (fun c => stars.contains c.shape && !(checkFn … c))
      upos  := uposCands.filter (fun c => !(stars.contains c.shape) && checkFn … c)

  — over the CORRECTED shape list, writes the result back with `putResidue`, and then asks
  `GraphModel.check` on the patched state. `(4)` restates the fold's formula against the
  UNCORRECTED list first and requires it to reproduce the residue the live leg actually
  produced, which is what makes the simulation trustworthy rather than a fresh invention.

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_partiv_stage0_killcheck_2026-09-14.lean

  ⚠ rc=0 with NO output is a FAILED run, not a green one.
  ⚠ INSTRUMENT CONTROL `(4)`: if the simulated fold under TODAY's shapes does not reproduce
    the live residue, the simulation is wrong and nothing below may be read.

  ── THE VERDICT (2026-09-14g) ──────────────────────────────────────────────────────────────

  **THE KILL-CHECK PASSES. The corrected enumeration closes BOTH divergent queries, and the
  feared second defect does NOT materialise at this store.**

  1. `(2)` at the phantom `folder:f9#viewer`: `admin` `(true, true)` and **`gate`
     `(true, true)`** — both agree with `sem`. `(3)` the materialised control `f1` still
     answers correctly at both, so the fix does not buy the phantom by breaking the control.
  2. `(1)` in STRATUM ORDER, `admin` acquires `stars := [("folder","viewer")]` and **so does
     `gate`** — because `gate`'s routed reader consults `admin`'s now-corrected residue.
  3. `(5)` `coveredFnR` at `gate`, evaluated on the state where `admin` is already corrected,
     is **`true`**. So `gate`'s coverage failure was DOWNSTREAM of the missing shape, not an
     independent reader defect.

  ⚠ **THIS PROBE'S FIRST FORM GOT THE OPPOSITE ANSWER, AND ITS INSTRUMENT CONTROL IS THE
  ONLY REASON THAT IS NOT NOW WRITTEN DOWN AS A FINDING.** The first form reported
  `gate (false, true)` — "the second defect kills part (iv)" — on two errors of mine:

  * it used the UNROUTED `coveredFn`/`checkFn` where the live fold
    (`CascadeStrata.lean:187::reconcileResidueKeyR`) uses the ROUTED `coveredFnR`/`checkFnR`,
    which additionally consult the residue (`CascadeStrata.lean:143-146`); and
  * it computed `admin` and `gate` from the SAME pre-patch state, denying `gate` the very
    input the fix exists to give it — the cascade reconciles in stratum order.

  Both errors push in the same direction: they manufacture a `gate` failure. `(4)` caught it
  because the simulated residue under TODAY's shapes did not reproduce the live one. **A
  simulation that uses the wrong reader reads exactly like a correct one; it just answers a
  different question.** Neither error is exotic — the routed/unrouted pair differ by one
  letter.

  ⚠ **CONSEQUENCE — a standing claim of this session is REFUTED.** The "two defects, not one"
  conclusion in `p6_partiv_starfold_cause_2026-09-14.lean` and in the plan doc's third
  correction rested on `coveredFn` (unrouted) being `false` at `gate`. The live fold does not
  use that reader. **The recorded stratum-2 gap (`CORRESPONDENCE.md:1213`) does not explain
  `gate` at this store, and there is no evidence here for a second live defect.** The
  recorded gap may still be real in its own context; this probe neither confirms nor refutes
  it there.

  ⚠ WHAT THIS DOES NOT ESTABLISH. This is a SIMULATION: `wildcardShapes` is untouched and the
  corrected residues are written with `putResidue` rather than produced by a real cascade run.
  It shows the fix WOULD close both queries at THIS store; it proves nothing in general, and
  no Lean proof is implied. `(4)` matches the live residue as a SET — the simulated `upos` is
  `[f1, f2]` against the live `[f2, f1]` — which is the order a fold over a different
  candidate enumeration produces, not a discrepancy in content.

  ── LITERAL TRANSCRIPT (the run's own stdout; nothing added, removed or reordered) ─────────

  RAN 2026-09-14g, rc=0, from `formal/lean` via
  `export PATH="$HOME/.elan/bin:$PATH" && lake env lean ../probes/p6_partiv_stage0_killcheck_2026-09-14.lean`.

  --------------------------------- BEGIN VERBATIM -----------------------------------------

("(4) INSTRUMENT CONTROL -- simulated fold under TODAY's shapes vs the LIVE residue at (doc:d1, admin); the stars/upos must MATCH or nothing below is readable",
 some ({ stars := [],
    neg := [],
    upos := [{ type := "folder", name := "f1", predicate := "viewer" },
             { type := "folder", name := "f2", predicate := "viewer" }] },
  { stars := [],
    neg := [],
    upos := [{ type := "folder", name := "f2", predicate := "viewer" },
             { type := "folder", name := "f1", predicate := "viewer" }] }))
("(1) ★ simulated residues under the CORRECTED shapes, IN STRATUM ORDER -- (admin, gate)",
 some ({ stars := [("folder", "viewer")], neg := [], upos := [] },
  { stars := [("folder", "viewer")], neg := [], upos := [] }))
("(2) ★★ THE KILL-CHECK -- at the PHANTOM folder:f9#viewer, (relation, check, sem, agree?)",
  some [("admin", true, true, true), ("gate", true, true, true)])
("(3) REGRESSION CONTROL -- the MATERIALISED control f1 must still answer correctly after the patch; (relation, check, sem, agree?)",
  some [("admin", true, true, true), ("gate", true, true, true)])
("(5) coveredFnR per shape -- admin on the LIVE state, gate on the state where admin is ALREADY corrected; a `false` at gate there IS the stratum-2 under-read",
  some
    ([(("folder", "..."), false), (("folder", "viewer"), true)],
      [(("folder", "..."), false), (("folder", "viewer"), true)]))

  ---------------------------------- END VERBATIM ------------------------------------------

  ⚠ `(5)`'s label still says *"a `false` at gate there IS the stratum-2 under-read"* — written
  before the run, when that was the expected outcome. It came back `true`. The label is left
  as written so the transcript is not retro-fitted to its result.

-/
import ZanzibarProofs

open Zanzibar

namespace P6PartIvStage0

/-! ## §1 Store, schema and the corrected enumeration — as in the sibling probes. -/

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
def prefixOps : List GraphOp := [GraphOp.add tPar, GraphOp.add tView]

def live : Option (GraphState × Store) :=
  (graphRunOps Sp prefixOps).map (fun p =>
    let To := tObj :: p.2
    (cascadeLeg Sp To (p.1.writeLoggedRules Sp tObj), To))

def throughShapes (S : Schema) : List Shape :=
  S.defs.flatMap (fun d =>
    (exprTtus d.2).flatMap (fun tt =>
      match S.lookup (d.1.1, tt.2) with
      | none => []
      | some tse =>
        (exprRestrictions tse).filterMap (fun r =>
          if r.2.2 && r.2.1 == BARE then some ((r.1, tt.1) : Shape) else none)))

def wildcardShapesFixed (S : Schema) : List Shape :=
  wildcardShapes S ++ (throughShapes S).filter (fun sh => !(wildcardShapes S).contains sh)

/-! ## §2 The fold's own formula, re-expressed here

Mirrors `CascadeStrata.lean:187::GraphState.reconcileResidueKeyR`. The candidate lists are
the userset subjects the store can name at this object — the two materialised folder
usersets plus the phantom, so the simulation is not quietly excluding the subject under
test. -/

def sF1 : SubjectRef := ⟨"folder", "f1", "viewer"⟩
def sF2 : SubjectRef := ⟨"folder", "f2", "viewer"⟩
def sF9 : SubjectRef := ⟨"folder", "f9", "viewer"⟩

/-- The fold's candidate subjects. **The phantom `sF9` is deliberately ABSENT**, because the
    live cascade enumerates candidates from materialised nodes and `folder:f9` has none —
    control `(4)` confirms this by reproducing the live residue exactly. That absence is the
    conceptual heart of the whole item: an EXTENSIONAL `upos` cannot answer a subject that
    was never a candidate, which is why the INTENSIONAL `stars` is the only path to a
    correct answer at a phantom, and why the missing enumeration pass matters. -/
def cands : List SubjectRef := [sF1, sF2]

/-- The fold, run at `(doc:d1, R)` over an arbitrary shape list.

    ⚠ **Uses the ROUTED readers `coveredFnR`/`checkFnR`, not `coveredFn`/`checkFn`.** The
    first form of this probe used the unrouted pair and its instrument control `(4)` caught
    it: the routed readers additionally consult the RESIDUE (`CascadeStrata.lean:143-146`),
    so on a stratified schema the unrouted simulation reproduces neither the live `admin`
    residue nor the live `gate` one. Kept in the record because an unrouted simulation reads
    exactly like a routed one — it just answers a different question. -/
def foldResidue (σ : GraphState) (T : Store) (R : String) (e : Expr)
    (shapes : List Shape) : Residue :=
  let stars := shapes.filter (fun sh => σ.coveredFnR T "doc" "d1" R e sh)
  let neg := cands.filter (fun c => stars.contains c.shape && !(σ.checkFnR T c "doc" "d1" R e))
  let upos := cands.filter (fun c => !(stars.contains c.shape) && σ.checkFnR T c "doc" "d1" R e)
  ⟨stars, neg, upos⟩

def exprOf (R : String) : Option Expr := Sp.lookup ("doc", R)

/-! ## §3 INSTRUMENT CONTROL — does the simulation reproduce the LIVE residue? -/

#eval ("(4) INSTRUMENT CONTROL -- simulated fold under TODAY's shapes vs the LIVE residue " ++
       "at (doc:d1, admin); the stars/upos must MATCH or nothing below is readable",
        live.bind (fun p => (exprOf "admin").map (fun e =>
          (foldResidue p.1 p.2 "admin" e (wildcardShapes Sp),
           (p.1.residue (objNode ⟨"doc", "d1"⟩ "admin") "admin").getD Residue.empty))))

/-! ## §4 ★ THE KILL-CHECK — the fold under the CORRECTED list -/

/-- Patch the derived residues with the corrected fold's output, **in STRATUM ORDER**.

    ⚠ `gate` is reconciled AFTER `admin` and its routed reader consults `admin`'s residue, so
    `gate`'s fold must run on the state where `admin` has ALREADY been corrected. The first
    form of this probe computed both from the same pre-patch state, which silently denies
    `gate` the very input the fix is supposed to give it — i.e. it would have reported a
    `gate` failure that the real cascade would not produce. -/
def patched : Option (GraphState × Store) :=
  live.bind (fun p => (exprOf "admin").bind (fun ea => (exprOf "gate").map (fun eg =>
    let σ1 := p.1.putResidue (objNode ⟨"doc", "d1"⟩ "admin") "admin"
                (foldResidue p.1 p.2 "admin" ea (wildcardShapesFixed Sp))
    let σ2 := σ1.putResidue (objNode ⟨"doc", "d1"⟩ "gate") "gate"
                (foldResidue σ1 p.2 "gate" eg (wildcardShapesFixed Sp))
    (σ2, p.2))))

#eval ("(1) ★ simulated residues under the CORRECTED shapes, IN STRATUM ORDER -- (admin, gate)",
        patched.map (fun p =>
          ((p.1.residue (objNode ⟨"doc", "d1"⟩ "admin") "admin").getD Residue.empty,
           (p.1.residue (objNode ⟨"doc", "d1"⟩ "gate") "gate").getD Residue.empty)))

def qAt (s : SubjectRef) (R : String) : Query := ⟨s, R, ⟨"doc", "d1"⟩⟩

#eval ("(2) ★★ THE KILL-CHECK -- at the PHANTOM folder:f9#viewer, (relation, check, sem, agree?)",
        patched.map (fun p =>
          ["admin", "gate"].map (fun R =>
            let c := GraphModel.check p.1 (qAt sF9 R)
            let s := sem Sp p.2 (qAt sF9 R)
            (R, c, s, c == s))))

#eval ("(3) REGRESSION CONTROL -- the MATERIALISED control f1 must still answer correctly " ++
       "after the patch; (relation, check, sem, agree?)",
        patched.map (fun p =>
          ["admin", "gate"].map (fun R =>
            let c := GraphModel.check p.1 (qAt sF1 R)
            let s := sem Sp p.2 (qAt sF1 R)
            (R, c, s, c == s))))

/-! ## §5 Why `gate`, if it fails — the second defect, restated in this transcript -/

#eval ("(5) coveredFnR per shape -- admin on the LIVE state, gate on the state where admin " ++
       "is ALREADY corrected; a `false` at gate there IS the stratum-2 under-read",
        live.bind (fun p => (exprOf "admin").bind (fun ea => (exprOf "gate").map (fun eg =>
          let σ1 := p.1.putResidue (objNode ⟨"doc", "d1"⟩ "admin") "admin"
                      (foldResidue p.1 p.2 "admin" ea (wildcardShapesFixed Sp))
          ((wildcardShapesFixed Sp).map (fun sh => (sh, p.1.coveredFnR p.2 "doc" "d1" "admin" ea sh)),
           (wildcardShapesFixed Sp).map (fun sh => (sh, σ1.coveredFnR p.2 "doc" "d1" "gate" eg sh)))))))

end P6PartIvStage0
