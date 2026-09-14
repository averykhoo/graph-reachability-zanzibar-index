/-
  ★ P6 PART (iv), route `D` cone — step 2: WHY the star fold left `stars` empty (2026-09-14g).

  WHY. Two measurements now bracket the phantom-subject divergence:

  * `formal/probes/p6_partiv_residue_locus_2026-09-14.lean` — the LEAN residue at
    `(doc:d1, admin)` is `stars := []`, `upos := [f2#viewer, f1#viewer]`. The read path is
    innocent; the cascade under-populated `stars`.
  * `formal/probes/p6_partiv_python_residue_2026-09-14.py` — the SHIPPED residue at the same
    key is `stars := [('folder','viewer')]`, `upos := []`. Opposite representations: Python
    covers the shape intensionally, the Lean model enumerates concrete members extensionally.
    Its control `(5)` (`banned` has empty stars) makes that falsifiable.

  So the Lean star fold *should* have produced `("folder","viewer")` and did not. This probe
  asks WHY, and it has a specific suspect.

  THE SUSPECT. The fold's coverage test is
  `GraphIndex/ReconcileStars.lean::GraphState.coveredFn`, which is defined as
  `σ.checkFn T (starSubj sh) dt on R e` — i.e. it asks
  `GraphIndex/ReconcileWrite.lean::GraphState.checkFn` at the intensional star subject
  `⟨folder, *, viewer⟩`, whose predicate is `viewer` and so is a USERSET subject. And
  `formal/CORRESPONDENCE.md:1213` §7 already records, from `P6` step 2 (2026-09-13b):

  > All four are the stratum-2 relation only — never the stratum-1 one — at userset
  > subjects, with `GraphIndex/ReconcileWrite.lean::GraphState.checkFn` reading `false`
  > while `GraphIndex/State.lean::GraphModel.check` and `sem` both read `true`.

  **If that is the cause, the two §7 boundaries — "the phantom userset subject" and "the
  stratum-2 reader gap" — are ONE defect recorded twice**, and route `D` is not "teach the
  fold a new shape" but "fix `checkFn`", which is the entry that already says the
  proof-side reader is the wrong one.

  ⚠ This is a PREDICTION. It is tested below, not assumed, and it is falsifiable: if
  `coveredFn` comes back TRUE at `admin` then `checkFn` is innocent and the fold is
  dropping the shape somewhere later, which is a different and larger cone.

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_partiv_starfold_cause_2026-09-14.lean

  ⚠ rc=0 with NO output is a FAILED run, not a green one.
  ⚠ INSTRUMENT CONTROL `(I)`: a `coveredFn` that returns `false` because it was handed the
    wrong expression or object reads exactly like a reader gap. `(I)` demands `coveredFn`
    come back TRUE somewhere in this same state before any `false` below is believed.

  ── THE VERDICT (2026-09-14g) ──────────────────────────────────────────────────────────────

  **THE SUSPECT IS REFUTED AT `admin`, AND THAT IS THE USEFUL RESULT.**

  | relation | `coveredFn` | `GraphModel.check` | `sem` |
  |---|---|---|---|
  | `access` (not derived) | `true` | `true` | `true` |
  | `admin` (stratum-1 derived) | **`true`** | `false` | `true` |
  | `gate` (stratum-2 derived) | `false` | `false` | `true` |

  1. At `admin` the coverage test **already returns `true`** for `("folder","viewer")`. So
     `checkFn` is INNOCENT there, and the recorded stratum-2 reader gap
     (`CORRESPONDENCE.md:1213`) does **not** explain the phantom-subject divergence. The
     prediction in the header above is wrong; it is kept, labelled, because it was a
     plausible single-cause story that would have sent the next session to fix the wrong
     function.
  2. ⚠ **CORRECTED 2026-09-14g, LATER THE SAME SESSION — this row said "Two defects, not
     one" and that is REFUTED.** It read `gate`'s `coveredFn` `false` against `sem` `true` as
     a second, independent instance of the stratum-2 gap. **`coveredFn` is the UNROUTED
     reader, and the live fold `CascadeStrata.lean:187::reconcileResidueKeyR` uses the ROUTED
     `coveredFnR`**, which additionally consults the residue. Measured in
     `p6_partiv_stage0_killcheck_2026-09-14.lean` `(5)`: with the enumeration corrected and
     the strata taken in order, `coveredFnR` at `gate` is **`true`**, and `(2)` there shows
     BOTH divergent queries reaching `check = sem`. So `gate`'s failure was DOWNSTREAM of the
     missing shape — **one defect, not two** — and the recorded gap at
     `CORRESPONDENCE.md:1213` does not explain this store. The original wording is kept above
     the correction because it was quoted into the plan doc and the task row before it was
     checked.
  3. Since the live fold is `CascadeStrata.lean:187`'s
     `stars := shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)` and a `filter` cannot
     mint a shape its input never held, `coveredFn = true` with `stars = []` forces the
     conclusion that **`("folder","viewer")` was never in `shapes`**. That is chased to
     ground in `p6_partiv_shapes_gap_2026-09-14.lean`, which finds the enumeration
     `ReconcileStars.lean:97::wildcardShapes` missing Python's second pass entirely.

  `(I)` INSTRUMENT CONTROL PASSED: `coveredFn` is `true` at `access` and `false` at a shape
  the schema does not cover (`("user", BARE)`), so the reader is live AND falsifiable — a
  `false` at `gate` is a real `false`, not a mis-wired call.

  ⚠ NOTE the reader disagreement at `admin` runs the OTHER way from the recorded gap: there
  `coveredFn`/`checkFn` agrees with `sem` and `GraphModel.check` is the outlier — because
  `check` routes through the residue, which is the thing that is empty. Do not read row
  `admin` as a second instance of the stratum-2 gap.

  ── LITERAL TRANSCRIPT (the run's own stdout; nothing added, removed or reordered) ─────────

  RAN 2026-09-14g, rc=0, from `formal/lean` via
  `export PATH="$HOME/.elan/bin:$PATH" && lake env lean ../probes/p6_partiv_starfold_cause_2026-09-14.lean`.

  --------------------------------- BEGIN VERBATIM -----------------------------------------

("(0) the expressions under test (access, admin, gate)",
 some (Zanzibar.Expr.ttu "viewer" "parent"),
 some (Zanzibar.Expr.excl (Zanzibar.Expr.computed "access") (Zanzibar.Expr.computed "banned")),
 some (Zanzibar.Expr.inter (Zanzibar.Expr.computed "admin") (Zanzibar.Expr.computed "access")))
("(1) ★ coveredFn at shape (folder,viewer), object doc:d1 -- (access, admin, gate)", some true, some true, some false)
("(2) ★ at the star subject folder:*#viewer -- (relation, coveredFn/checkFn, check, sem)",
  some [("access", some true, true, true), ("admin", some true, false, true), ("gate", some false, false, true)])
("(I) INSTRUMENT CONTROL -- coveredFn must be TRUE somewhere; (access at the same shape/object) and (a shape the schema does not cover)",
  some true, some false)
("(3) isDerived (access, admin, gate) -- the stratum split, restated here so the transcript is self-contained", false,
  true, true)

  ---------------------------------- END VERBATIM ------------------------------------------

-/
import ZanzibarProofs

open Zanzibar

namespace P6PartIvStarFoldCause

/-! ## §1 The store — VERBATIM from the residue-locus probe §1. -/

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

/-! ## §2 The shape and the expressions the fold is run with -/

def shV : Shape := ("folder", "viewer")

def exprOf (R : String) : Option Expr := Sp.lookup ("doc", R)

#eval ("(0) the expressions under test (access, admin, gate)",
        exprOf "access", exprOf "admin", exprOf "gate")

/-! ## §3 ★ THE COVERAGE TEST the star fold actually makes -/

def covered (R : String) : Option Bool :=
  live.bind (fun p => (exprOf R).map (fun e =>
    p.1.coveredFn p.2 "doc" "d1" R e shV))

#eval ("(1) ★ coveredFn at shape (folder,viewer), object doc:d1 -- (access, admin, gate)",
        covered "access", covered "admin", covered "gate")

/-! ## §4 The three readers side by side at the INTENSIONAL star subject

`coveredFn` is `checkFn` at `starSubj sh`. If the suspect is right, `checkFn` (via
`coveredFn`) says `false` at the derived relations while `GraphModel.check` and `sem` say
`true` at the very same subject — the disagreement `CORRESPONDENCE.md:1213` records. -/

def qStar (R : String) : Query := ⟨starSubj shV, R, ⟨"doc", "d1"⟩⟩

#eval ("(2) ★ at the star subject folder:*#viewer -- (relation, coveredFn/checkFn, check, sem)",
        live.map (fun p =>
          ["access", "admin", "gate"].map (fun R =>
            (R, covered R, GraphModel.check p.1 (qStar R), sem Sp p.2 (qStar R)))))

/-! ## §5 INSTRUMENT CONTROL — is `coveredFn` live at all?

A `false` from a reader handed the wrong expression, object or shape is indistinguishable
from a reader gap. `(I)` must come back TRUE somewhere: `access` is stratum-1 and the
star-tupleset bridge serves it, so it is the natural positive. If `(I)` is false EVERYWHERE,
this probe measures nothing and `(1)`/`(2)` must not be read. -/

#eval ("(I) INSTRUMENT CONTROL -- coveredFn must be TRUE somewhere; " ++
       "(access at the same shape/object) and (a shape the schema does not cover)",
        covered "access",
        live.bind (fun p => (exprOf "access").map (fun e =>
          p.1.coveredFn p.2 "doc" "d1" "access" e ("user", BARE))))

/-! ## §6 Is it STRATUM, as the recorded gap says?

`access` is stratum-1 (a ttu over a stored tupleset); `admin` sits above it and `gate` above
that. The recorded claim is that the disagreement is at the stratum-2 relation ONLY. If `(1)`
shows `access` true and `admin`/`gate` false, that is the same signature. -/

#eval ("(3) isDerived (access, admin, gate) -- the stratum split, restated here so the " ++
       "transcript is self-contained",
        isDerived Sp ("doc", "access"), isDerived Sp ("doc", "admin"),
        isDerived Sp ("doc", "gate"))

end P6PartIvStarFoldCause
