/-
  ★ P6 PART (iv) STEP-2 PROBE (2026-09-14i) — attack step 3 BEFORE doing it, and settle
  `§ Blockers` item 2 in the same `#eval` session.

  `docs/p6-part-iv-plan-2026-09-14.md` § Ordered steps, step 2:

      "Attack step 3 before doing it: probe whether `ttuLeaf_elim_nss`'s conclusion survives
       with only its `hnostar` premise widened, or whether the `tup.subject.name ≠ STAR`
       component must go too."

  and § Blockers item 2:

      "is `term`'s `NoTtuTarget` half IMPLIED by `RewriteMatchDeclared`, which
       `FullScope.lean:1350` carries separately?  If yes,
       `ttuStarFreeW_through_untainted` becomes hypothesis-free and step 6 has one fewer
       premise to thread.  Settle it in step 2's probe run — it is the same `#eval`
       session."

  `RulesBareStar.lean::ttuLeaf_elim_nss` is the SHAPE-B lemma: three call sites
  (`::evalE_lift_bs`, `RulesBareStar.lean` second site, `RestrictBase.lean`) feed it a
  per-leaf instance of the narrow `TtuStarFree` as `hnostar` and read back a witness tuple.
  Its conclusion carries `tup.subject.name ≠ STAR` as a COMPONENT, so widening the premise
  is not obviously a substitution.

  Kept OUTSIDE the lake package, like every other probe here: zero cone, ungated,
  re-runnable evidence.  Run from `formal/lean` against the built oleans:

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_partiv_step2_ttuleaf_2026-09-14.lean

  ⚠ rc=0 with NO output is a FAILED run, not a green one.

  ── THE VERDICT ───────────────────────────────────────────────────────────────────────────

  **(A) THE CONCLUSION DOES NOT SURVIVE.  The `≠ STAR` component must go, exactly as the plan
  forecast.**  Line (7): the leaf FIRES at the widened in-scope store.  Line (8): the witness
  list for TODAY's conclusion is `0, []`.  So `ttuLeaf_elim_nss` cannot be restated by
  widening `hnostar` alone — with the star branch of `ttuLeaf` alive, every witness the leaf
  offers has `subject.name = STAR`, and the conclusion is FALSE as written.  Step 3 is a
  statement change on BOTH sides of the lemma, not a premise substitution.

  ⚠ This is the one forecast in the plan that the kernel CONFIRMS rather than corrects
  (`§ The census`, the ⚠ under Shape B).  Four consecutive P6 increments went the other way,
  so it is worth saying which one this is.

  **(B) THE REPAIR IS THE STAR BRANCH OF `ttuLeaf`, MADE EXPLICIT, AND IT IS A SCOPE RESULT.**
  Line (10): the repaired disjunctive conclusion has `1` witness — the star tuple itself,
  `⟨folder, *, ...⟩ parent doc:d1`.  Line (11): at CONTROL a (through-shape undeclared) it has
  `0`, so the added disjunct is FALSIFIABLE and not a tautology.  Line (12): at CONTROL b
  (concrete parent) it still has `1`, so the repair does not lose today's case.

  ⚠ Note WHICH tuple line (10) returns: the witness's own predicate is `BARE`, not `"viewer"`.
  The side condition is `isSubjectWildcardUserset tup.subject.type tr` — keyed on the RULE's
  target `tr`, not on the stored subject's predicate.  A repair phrased over
  `tup.subject.predicate` would be measuring the wrong string and would pass here by accident.

  **(C) `§ Blockers` ITEM 2 IS ANSWERED: NO.  `NoTtuTarget` is NOT implied by
  `RewriteMatchDeclared`.**  Line (15) at the new witness `Sdt`: `RewriteMatchDeclared` HOLDS
  (`true`) while `noTtuTargetB Sdt "approver"` and `htermB Sdt []` are both `false`.  So
  `ttuStarFreeW_through_untainted` KEEPS its `hterm` premise and step 6 has no premise to
  drop.

  The route, and why `TermNonvacuityWitness.Sund` could not settle this: `Sund` fails
  `RewriteMatchDeclared` (line 16, `false`) because it leaves the tupleset relation
  UNDECLARED, which is precisely what that predicate forbids — the hole the
  `TtuStarWide.lean` docstring flagged on 2026-09-13.  `Sdt` closes it by a DIFFERENT route:
  `exprRefs`'s `.ttu` case adds the target ref `(pt, tr)` only for the parent types the
  tupleset DECLARES, while `hterm` quantifies over ALL `dt`.  So `("folder","approver")` is
  untainted (line 13) — the owner stays untainted and the arm survives the taint filter
  (line 14) — while `("group","approver")`, the same relation NAME at a type the tupleset
  never mentions, is derived (line 13).  ★ **The gap is the cross-TYPE quantification in
  `hterm`, and no match-key condition can close it.**

  ⚠ SCOPE OF (C).  This refutes the IMPLICATION.  It does not show that `Sdt` survives the
  rest of `W4Fragment` / `GraphAdmission` — seven of those fields have no `Bool` decider
  (AGENT census, 2026-09-14g, recorded so it is not re-commissioned), so that question is not
  answerable at this price.  What is settled is that `RewriteMatchDeclared` alone does not
  hand `hterm` over, which is what the blocker asked.

  ⚠ CONTROLS, and what each rules out:
  * (1)/(2) NON-VACUITY — the through-shape is declared and the widening is ENGAGED at this
    store (narrow `false`, wide `true`).  Without this every line is about a store the
    widening never reaches.
  * (3)/(5)/(11) CONTROL a — the same store with the shape UNDECLARED.  The widened predicate
    rejects it, the widened per-leaf premise is false, and the repaired conclusion explains
    nothing.  This is what makes (8) and (10) attributable to the predicate ADMITTING.
  * (6)/(9)/(12) CONTROL b — a CONCRETE tupleset parent.  The leaf still fires and TODAY's
    conclusion still has a witness, so the `0` at line (8) is the STAR subject specifically
    and not a broken encoding of the conclusion.
  * (16) INSTRUMENT CONTROL for §7 — `rewriteMatchDeclaredB` is encoded here (no `Bool`
    mirror exists in the tree), so it is checked against `Sund`, where it must read `false`.
    It does.  A constantly-`true` encoding would have made (15) meaningless.
  * (17) CONTROL for §7 — at the clean in-scope `SwT` both predicates HOLD, so (15)'s split
    verdict is not an artefact of the encoding rejecting everything.

  ⚠ THE FIRST RUN FAILED ITS OWN CONTROL AND IS RECORDED: line (16) named
  `TtuStarWide.TermNonvacuityWitness.Sund`, an unknown identifier (the witness is under
  `namespace Zanzibar`, already `open`ed), so the run was `rc=1` and lines (15)/(17) printed
  with the control MISSING.  Every other line was identical.  A control that does not run is
  not a control; the transcript below is the re-run, `rc=0`, all seventeen lines.

  ── LITERAL TRANSCRIPT (the run's own stdout; nothing added, removed or reordered) ─────────

  RAN 2026-09-14i, rc=0, from `formal/lean` via
  `lake env lean ../probes/p6_partiv_step2_ttuleaf_2026-09-14.lean`

  ("(1) through-shape declared / isSubjectWildcardUserset (folder,viewer)", true, true)
  ("(2) STAR store: narrow REJECTS, wide ADMITS -- the widening is engaged", false, true)
  ("(3) CONTROL a -- undeclared shape: narrow rejects AND wide rejects (out of scope)", false, false)
  ("(4) per-leaf premise at the STAR store: narrow / widened -- must be false, true", false, true)
  ("(5) CONTROL a -- widened per-leaf premise is FALSE where the shape is undeclared", false)
  ("(6) CONTROL b -- concrete parent: narrow premise HOLDS (today's fragment)", true, true)
  ("(7) does the leaf FIRE at the STAR store? -- NON-VACUITY, must be true", true)
  ("(8) ★ witnesses of TODAY's conclusion at the STAR store -- 0 REFUTES step 3's", 0, [])
  ("(9) CONTROL b -- concrete parent: leaf fires AND today's conclusion has a witness", true, 1)
  ("(10) ★ witnesses of the REPAIRED conclusion at the STAR store -- must be >= 1",
   1,
   [{ subject := { type := "folder", name := "*", predicate := "..." },
      relation := "parent",
      object := { type := "doc", name := "d1" } }])
  ("(11) CONTROL a -- the repaired conclusion must FAIL where the shape is undeclared", 0)
  ("(12) CONTROL b -- the repaired conclusion still covers today's concrete case", 1)
  ("(13) Sdt taint: (folder,approver) / (group,approver) / (doc,control)", false, true, false)
  ("(14) the arm SURVIVES the taint filter -- NON-VACUITY, must be non-empty",
   [{ objectType := "doc", matchRel := "parent", outRel := "control", kind := Zanzibar.RuleKind.ttu "approver" }])
  ("(15) ★ RewriteMatchDeclared HOLDS / NoTtuTarget FAILS  ==> NOT implied", true, false, false)
  ("(16) INSTRUMENT CONTROL -- the encoding of (15) detects Sund, where it must be false", false, false)
  ("(17) CONTROL -- SwT, where both must HOLD (a clean in-scope schema)", true, true)

  ----------------------------------- END VERBATIM -----------------------------------------
-/
import ZanzibarProofs

open Zanzibar

namespace P6PartIvStep2Probe

/-! ## §1 The subject — `TtuStarWide.lean::WideWitness.SwT`, verbatim

`doc#access := viewer from parent`, tupleset `doc#parent` carrying the BARE wildcard
restriction `[folder:*]`, so `(folder, "viewer")` is a declared star-tupleset through-shape
and `WideWitness.wide_admits` holds while `::narrow_rejects` does not. -/
def SwT : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"), .direct [("folder", BARE, true)]),
    (("doc", "access"), .ttu "viewer" "parent")], []⟩

/-- **INSTRUMENT CONTROL (a): the through-shape is NOT declared** (`[folder]`, concrete), so
    the WIDENED predicate REJECTS this store and the arm is out of scope. -/
def SwTn : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"), .direct [("folder", BARE, false)]),
    (("doc", "access"), .ttu "viewer" "parent")], []⟩

/-- The stored STAR tupleset parent — forbidden by the narrow predicate, admitted by the
    widened one. -/
def tStar : Tuple := ⟨⟨"folder", STAR, BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def TStar : Store := [tStar]

/-- **INSTRUMENT CONTROL (b): a CONCRETE tupleset parent**, the case today's fragment
    already reaches. -/
def tConc : Tuple := ⟨⟨"folder", "f1", BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def TConc : Store := [tConc]

/-! ## §2 The leaf coordinates, read off the one TTU arm of `SwT` -/

def tr : String := "viewer"   -- `targetRel`
def ts : String := "parent"   -- `tuplesetRel`
def ot : String := "doc"      -- `otype`
def on : String := "d1"       -- `oname`

/-- The query subject that makes the STAR branch of `ttuLeaf` fire syntactically: the star
    USERSET subject part (ii)'s in-bridge materialises. -/
def sStar : SubjectRef := ⟨"folder", STAR, "viewer"⟩

/-- The concrete query subject, for CONTROL (b). -/
def sConc : SubjectRef := ⟨"folder", "f1", "viewer"⟩

def qStar : Query := ⟨sStar, "access", ⟨"doc", "d1"⟩⟩
def qConc : Query := ⟨sConc, "access", ⟨"doc", "d1"⟩⟩

/-- **The recursion answers NOTHING.** With `rec := fun _ _ _ => false` the only way
    `ttuLeaf` can return `true` is the SYNTACTIC subject match, so a `true` below cannot be
    an artefact of an unconstrained `rec`. -/
def recF : Rec := fun _ _ _ => false

/-! ## §3 Is the widening ENGAGED at all? (non-vacuity) -/

#eval ("(1) through-shape declared / isSubjectWildcardUserset (folder,viewer)",
        SwT.isStarTuplesetThrough "folder" "viewer",
        SwT.isSubjectWildcardUserset "folder" "viewer")
#eval ("(2) STAR store: narrow REJECTS, wide ADMITS -- the widening is engaged",
        ttuStarFreeB SwT TStar, ttuStarFreeWB SwT TStar)
#eval ("(3) CONTROL a -- undeclared shape: narrow rejects AND wide rejects (out of scope)",
        ttuStarFreeB SwTn TStar, ttuStarFreeWB SwTn TStar)

/-! ## §4 The premise, narrow and widened, as `ttuLeaf_elim_nss` sees it per leaf

`hnostar` is the per-leaf instance of `TtuStarFree`; `hnostarW` is what the per-leaf instance
of `TtuStarFreeW` would be. The attack needs `hnostarW` TRUE and `hnostar` FALSE at the same
store — otherwise it is measuring something other than the widening. -/

def hnostarB (T : Store) : Bool :=
  T.all (fun tup => !(tup.subject.name == STAR) || !(tup.relation == ts && tup.object.type == ot))

def hnostarWB (S : Schema) (T : Store) : Bool :=
  T.all (fun tup =>
    !(tup.subject.name == STAR)
      || !(tup.relation == ts && tup.object.type == ot)
      || S.isSubjectWildcardUserset tup.subject.type tr)

#eval ("(4) per-leaf premise at the STAR store: narrow / widened -- must be false, true",
        hnostarB TStar, hnostarWB SwT TStar)
#eval ("(5) CONTROL a -- widened per-leaf premise is FALSE where the shape is undeclared",
        hnostarWB SwTn TStar)
#eval ("(6) CONTROL b -- concrete parent: narrow premise HOLDS (today's fragment)",
        hnostarB TConc, hnostarWB SwT TConc)

/-! ## §5 THE ATTACK — does `ttuLeaf_elim_nss`'s CONCLUSION survive?

`h : ttuLeaf rec s' T q tr ts ot on = true` plus the widened premise; the conclusion is

    ∃ tup ∈ T, tup.relation = ts ∧ tup.object.type = ot ∧
      (matchingObjects on).contains tup.object.name = true ∧
      tup.subject.name ≠ STAR ∧
      ((s'.type = tup.subject.type ∧ s'.name = tup.subject.name ∧ s'.predicate = tr)
        ∨ rec tup.subject.type tup.subject.name tr = true)

encoded below as the list of tuples that WITNESS it. If `ttuLeaf` fires and the witness list
is EMPTY, the conclusion is false as written. -/

def conclWitnesses (rec : Rec) (s' : SubjectRef) (T : Store) : List Tuple :=
  T.filter (fun tup =>
    tup.relation == ts && tup.object.type == ot
      && (matchingObjects on).contains tup.object.name
      && !(tup.subject.name == STAR)
      && ((s'.type == tup.subject.type && s'.name == tup.subject.name && s'.predicate == tr)
          || rec tup.subject.type tup.subject.name tr))

#eval ("(7) does the leaf FIRE at the STAR store? -- NON-VACUITY, must be true",
        ttuLeaf recF sStar TStar qStar tr ts ot on)
#eval ("(8) ★ witnesses of TODAY's conclusion at the STAR store -- 0 REFUTES step 3's",
        (conclWitnesses recF sStar TStar).length, conclWitnesses recF sStar TStar)
#eval ("(9) CONTROL b -- concrete parent: leaf fires AND today's conclusion has a witness",
        ttuLeaf recF sConc TConc qConc tr ts ot on,
        (conclWitnesses recF sConc TConc).length)

/-! ## §6 The REPAIRED conclusion — the star branch of `ttuLeaf`, made explicit

`Spec/Semantics.lean:93::ttuLeaf`'s star branch reads

    (s.type == pt && s.predicate == targetRel)
      || (instances T q pt).any (fun inst => rec pt inst targetRel)

so the honest restatement disjoins today's non-star witness with a STAR witness carrying that
disjunction, guarded by the widened premise's side condition
(`S.isSubjectWildcardUserset tup.subject.type tr`) — exactly the shape part (ii)'s in-bridge
materialises. Two things must both hold for that to be a scope result rather than a
tautology: it must EXPLAIN the store below (non-empty), and it must FAIL at CONTROL a. -/

def conclWitnessesW (S : Schema) (rec : Rec) (s' : SubjectRef) (T : Store) (q : Query) :
    List Tuple :=
  T.filter (fun tup =>
    tup.relation == ts && tup.object.type == ot
      && (matchingObjects on).contains tup.object.name
      && (((!(tup.subject.name == STAR))
            && ((s'.type == tup.subject.type && s'.name == tup.subject.name
                  && s'.predicate == tr)
                || rec tup.subject.type tup.subject.name tr))
          || ((tup.subject.name == STAR)
                && S.isSubjectWildcardUserset tup.subject.type tr
                && ((s'.type == tup.subject.type && s'.predicate == tr)
                    || (instances T q tup.subject.type).any
                         (fun inst => rec tup.subject.type inst tr)))))

#eval ("(10) ★ witnesses of the REPAIRED conclusion at the STAR store -- must be >= 1",
        (conclWitnessesW SwT recF sStar TStar qStar).length,
        conclWitnessesW SwT recF sStar TStar qStar)
#eval ("(11) CONTROL a -- the repaired conclusion must FAIL where the shape is undeclared",
        (conclWitnessesW SwTn recF sStar TStar qStar).length)
#eval ("(12) CONTROL b -- the repaired conclusion still covers today's concrete case",
        (conclWitnessesW SwT recF sConc TConc qConc).length)

/-! ## §7 `§ Blockers` item 2 — is `NoTtuTarget` implied by `RewriteMatchDeclared`?

`ttuStarFreeW_through_untainted` (`TtuStarWide.lean:443`) takes

    hterm : ∀ dt R, isDerived S (dt, R) = true → NoTtuTarget S R

`TtuStarWide.lean::TermNonvacuityWitness.Sund` shows `hterm` is not vacuous, but `Sund`
reaches that by leaving the tupleset relation UNDECLARED — which is exactly what
`RewriteMatchDeclared` forbids, so `Sund` cannot settle the implication. The witness below
closes that hole: the tupleset IS declared, and the taint that `hterm` trips on lives at a
DIFFERENT object type than the one the tupleset's restrictions name.

`exprRefs`'s `.ttu` case adds the target ref `(pt, tr)` only for parent types `pt` the
tupleset declares. `hterm` quantifies over ALL `dt`. So a relation NAME derived at a type the
tupleset never mentions leaves the owner untainted, the arm reaches `schemaRewrites`, and
`NoTtuTarget` fails while every match key stays declared and untainted. -/

/-- `doc#control := approver from parent`, `doc#parent` DECLARED with parent type `folder`.
    `folder#approver` is untainted (so the owner stays untainted and the arm survives), while
    `group#approver` — same relation NAME, different type — is derived. -/
def Sdt : Schema :=
  ⟨[(("folder", "approver"), .direct [("user", BARE, false)]),
    (("group", "blocked"),   .direct [("user", BARE, false)]),
    (("group", "approver"),  .excl (.direct [("user", BARE, false)]) (.computed "blocked")),
    (("doc", "parent"),      .direct [("folder", BARE, false)]),
    (("doc", "control"),     .ttu "approver" "parent")], []⟩

/-- `RewriteMatchDeclared S` as a `Bool`: every rewrite arm's MATCH key is declared and
    untainted. (No `Bool` mirror exists in the tree — `RestrictBase.lean:312` is `Prop`-only
    — so it is encoded here and the encoding is controlled at line (16).) -/
def rewriteMatchDeclaredB (S : Schema) : Bool :=
  (schemaRewrites S).all (fun r =>
    S.keys.contains (r.objectType, r.matchRel) && !(isDerived S (r.objectType, r.matchRel)))

#eval ("(13) Sdt taint: (folder,approver) / (group,approver) / (doc,control)",
        isDerived Sdt ("folder", "approver"), isDerived Sdt ("group", "approver"),
        isDerived Sdt ("doc", "control"))
#eval ("(14) the arm SURVIVES the taint filter -- NON-VACUITY, must be non-empty",
        schemaRewrites Sdt)
#eval ("(15) ★ RewriteMatchDeclared HOLDS / NoTtuTarget FAILS  ==> NOT implied",
        rewriteMatchDeclaredB Sdt, noTtuTargetB Sdt "approver", htermB Sdt [])
#eval ("(16) INSTRUMENT CONTROL -- the encoding of (15) detects Sund, where it must be false",
        rewriteMatchDeclaredB TermNonvacuityWitness.Sund,
        noTtuTargetB TermNonvacuityWitness.Sund "approver")
#eval ("(17) CONTROL -- SwT, where both must HOLD (a clean in-scope schema)",
        rewriteMatchDeclaredB SwT, htermB SwT [])

end P6PartIvStep2Probe
