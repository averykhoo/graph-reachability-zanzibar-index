/-
  ★ P6 PART (iv) ATTACK-FIRST PROBE (2026-09-14) — under the WIDENED `TtuStarFreeW`, do the
  two star-subject closure theorems survive, or are they FALSE?

  House rule 2 (`formal/HANDOFF.md` §"House rules"): before proving any new statement, try
  to REFUTE it.  Part (iv) replaces `FullScope.lean::W4Fragment.ttuStarFree : TtuStarFree S T`
  with `TtuStarWide.lean:72::TtuStarFreeW S T`.  The deepest ELIMINATE site of the narrow
  predicate is `RulesBareStar.lean:126` inside `::starSeed_step`, which feeds

      `RulesBareStar.lean:142::rewriteClosure_star_subject`
        — a star-subject closure member carries the SEED's full subject;
      `RulesBareStar.lean:168::rewriteClosure_star_bare`
        — ...and is therefore BARE-predicated.

  Both are stated with `(hTS : TtuStarFree S T)`.  The question this probe answers is whether
  they can be RESTATED over `TtuStarFreeW` unchanged (part (iv) = a type edit) or whether
  they go FALSE and need a new disjunct (part (iv) = a proof leg).

  Kept OUTSIDE the lake package, like every other probe here: zero cone, ungated, re-runnable
  evidence.  Run from `formal/lean` against the built oleans:

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_partiv_closure_star_2026-09-14.lean

  ⚠ rc=0 with NO output is a FAILED run, not a green one.

  ── THE VERDICT ───────────────────────────────────────────────────────────────────────────

  **BOTH THEOREMS ARE FALSE UNDER THE WIDENING.**  Line (7) and line (8) each exhibit ONE
  violator at the in-scope store, and it is the same tuple: the seed's subject rewritten onto
  the through-shape, `⟨"folder", STAR, "viewer"⟩`, whose predicate is `"viewer"` and not
  `BARE`.  So part (iv) is a PROOF LEG, not a type edit — `rewriteClosure_star_subject` and
  `rewriteClosure_star_bare` cannot be restated over `TtuStarFreeW` with their conclusions
  unchanged, and every consumer that reads "the star-subject closure member is the bare seed"
  inherits the obligation.

  The repair the probe also tests: conclude a DISJUNCTION — the member carries the seed's
  subject, or it is `⟨t.subject.type, STAR, tr⟩` for a `tr` with
  `S.isSubjectWildcardUserset t.subject.type tr = true`, i.e. exactly the shape part (ii)'s
  in-bridge materialises.  Line (11) says that disjunct is EXHAUSTIVE here (0 unexplained),
  and line (12) says it is FALSIFIABLE (at CONTROL a it explains nothing), so it is a scope
  result and not a tautology.

  ⚠ CONTROLS, and what each one rules out:
  * (4)/(9) CONTROL a — the same closure with the through-shape UNDECLARED.  The violator is
    still there (line 9: `1, 1`) because the closure does not depend on the declaration; what
    changes is that the WIDENED predicate rejects the store (line 4: `false, false`), so the
    arm is out of scope, and the proposed disjunct fails to explain it (line 12).  This is
    what makes the refutation attributable to the predicate ADMITTING rather than to the
    closure shape.
  * (5)/(10) CONTROL b — a CONCRETE tupleset parent.  Closure length is still 2, so the TTU
    arm fired and the measurement ran on something; violators are `0, 0`.  So the refutation
    is attributable to the STAR subject specifically.
  * (1) NON-VACUITY — `schemaRewrites SwT` is non-empty, i.e. the arm survived the taint
    filter.  This is the fact `TtuStarWide.lean::RoutingArmWitness.no_rewrite_arms` shows a
    derived through-shape does NOT have, and without it every line below would be vacuous.

  ── LITERAL TRANSCRIPT (the run's own stdout; nothing added, removed or reordered) ─────────

  RAN 2026-09-14, rc=0, from `formal/lean` via
  `export PATH="$HOME/.elan/bin:$PATH" && lake env lean ../probes/p6_partiv_closure_star_2026-09-14.lean`.

  --------------------------------- BEGIN VERBATIM -----------------------------------------

("(1) ttu arm survives the taint filter  -- NON-VACUITY, must be non-empty",
 [{ objectType := "doc", matchRel := "parent", outRel := "access", kind := Zanzibar.RuleKind.ttu "viewer" }])
("(2) through-shape declared / isSubjectWildcardUserset (folder,viewer)", true, true)
("(3) STAR store: narrow REJECTS, wide ADMITS  -- the widening is engaged", false, true)
("(4) CONTROL a -- undeclared shape: narrow rejects AND wide rejects (out of scope)", false, false)
("(5) CONTROL b -- concrete parent: narrow ADMITS (today's fragment reaches it)", true, true)
("(6) closure of the STAR seed, in full  -- NON-VACUITY: length must exceed 1",
 2,
 [{ subject := { type := "folder", name := "*", predicate := "..." },
    relation := "parent",
    object := { type := "doc", name := "d1" } },
  { subject := { type := "folder", name := "*", predicate := "viewer" },
    relation := "access",
    object := { type := "doc", name := "d1" } }])
("(7) ★ rewriteClosure_star_subject VIOLATORS at the widened store",
 1,
 [{ subject := { type := "folder", name := "*", predicate := "viewer" },
    relation := "access",
    object := { type := "doc", name := "d1" } }])
("(8) ★ rewriteClosure_star_bare VIOLATORS at the widened store",
 1,
 [{ subject := { type := "folder", name := "*", predicate := "viewer" },
    relation := "access",
    object := { type := "doc", name := "d1" } }])
("(9) CONTROL a (undeclared shape) -- violators, and the predicate that rejects", 1, 1, false)
("(10) CONTROL b (concrete parent) -- closure length, then violators; must be 0/0", 2, 0, 0)
("(11) ★ violators NOT explained by the proposed bridged-through-shape disjunct", 0, [])
("(12) CONTROL a -- the disjunct must NOT explain these (nonzero means falsifiable)",
 1,
 [{ subject := { type := "folder", name := "*", predicate := "viewer" },
    relation := "access",
    object := { type := "doc", name := "d1" } }])

  ----------------------------------- END VERBATIM -----------------------------------------
-/
import ZanzibarProofs

open Zanzibar

namespace P6PartIvClosureProbe

/-! ## §1 The subject — `TtuStarWide.lean:225::WideWitness.SwT`, verbatim

The in-scope widening witness: `doc#access := viewer from parent`, tupleset `doc#parent`
carrying the BARE wildcard restriction `[folder:*]`, so `(folder, "viewer")` is a declared
star-tupleset through-shape and `WideWitness.wide_admits` holds.  Every key is UNTAINTED, so
the TTU arm survives `schemaRewrites`' taint filter (`WideWitness.ttu_arm_present`) — which
is exactly what `RoutingArmWitness` does NOT have. -/
def SwT : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"), .direct [("folder", BARE, true)]),
    (("doc", "access"), .ttu "viewer" "parent")], []⟩

/-- The stored STAR tupleset parent — forbidden by the narrow predicate, admitted by the
    widened one. -/
def tStar : Tuple := ⟨⟨"folder", STAR, BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def TStar : Store := [tStar]

/-- **INSTRUMENT CONTROL (a): the shape is NOT declared.** Same store, tupleset restriction
    made concrete (`[folder]`), so `isStarTuplesetThrough` is false and the WIDENED predicate
    REJECTS this store (`WideWitness.unbridged_still_rejected`).  The closure here is
    shape-identical, so if the refutation below fired on the closure alone rather than on the
    predicate ADMITTING, this arm would look the same — it must be reported OUT OF SCOPE. -/
def SwTn : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"), .direct [("folder", BARE, false)]),
    (("doc", "access"), .ttu "viewer" "parent")], []⟩

/-- **INSTRUMENT CONTROL (b): a CONCRETE tupleset parent.** The narrow predicate holds here
    (no stored star subject at all), so both closure theorems apply today.  A refutation on
    THIS arm would mean the probe is measuring something other than the widening. -/
def tConc : Tuple := ⟨⟨"folder", "f1", BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def TConc : Store := [tConc]

/-! ## §2 Is the widening ENGAGED? -/

#eval ("(1) ttu arm survives the taint filter  -- NON-VACUITY, must be non-empty",
        schemaRewrites SwT)
#eval ("(2) through-shape declared / isSubjectWildcardUserset (folder,viewer)",
        SwT.isStarTuplesetThrough "folder" "viewer",
        SwT.isSubjectWildcardUserset "folder" "viewer")
#eval ("(3) STAR store: narrow REJECTS, wide ADMITS  -- the widening is engaged",
        ttuStarFreeB SwT TStar, ttuStarFreeWB SwT TStar)
#eval ("(4) CONTROL a -- undeclared shape: narrow rejects AND wide rejects (out of scope)",
        ttuStarFreeB SwTn TStar, ttuStarFreeWB SwTn TStar)
#eval ("(5) CONTROL b -- concrete parent: narrow ADMITS (today's fragment reaches it)",
        ttuStarFreeB SwT TConc, ttuStarFreeWB SwT TConc)

/-! ## §3 THE ATTACK — the closure of the star seed

`rewriteClosure_star_subject` says: every `u ∈ rewriteClosure S t` with
`u.subject.name = STAR` has `u.subject = t.subject`.  `rewriteClosure_star_bare` adds
`u.subject.predicate = BARE`.  Both are proved from `hTS` killing the `ttu` branch of
`starSeed_step`; under `TtuStarFreeW` that branch is ALIVE whenever the shape is bridged. -/

def closureOf (S : Schema) (t : Tuple) : List Tuple := rewriteClosure S t

/-- Members that WITNESS a violation of `rewriteClosure_star_subject`. -/
def subjectViolators (S : Schema) (t : Tuple) : List Tuple :=
  (closureOf S t).filter (fun u => u.subject.name == STAR && !(u.subject == t.subject))

/-- Members that WITNESS a violation of `rewriteClosure_star_bare`. -/
def bareViolators (S : Schema) (t : Tuple) : List Tuple :=
  (closureOf S t).filter (fun u => u.subject.name == STAR && !(u.subject.predicate == BARE))

#eval ("(6) closure of the STAR seed, in full  -- NON-VACUITY: length must exceed 1",
        (closureOf SwT tStar).length, closureOf SwT tStar)
#eval ("(7) ★ rewriteClosure_star_subject VIOLATORS at the widened store",
        (subjectViolators SwT tStar).length, subjectViolators SwT tStar)
#eval ("(8) ★ rewriteClosure_star_bare VIOLATORS at the widened store",
        (bareViolators SwT tStar).length, bareViolators SwT tStar)

/-! ## §4 The controls, on the same two measurements -/

#eval ("(9) CONTROL a (undeclared shape) -- violators, and the predicate that rejects",
        (subjectViolators SwTn tStar).length, (bareViolators SwTn tStar).length,
        ttuStarFreeWB SwTn TStar)
#eval ("(10) CONTROL b (concrete parent) -- closure length, then violators; must be 0/0",
        (closureOf SwT tConc).length,
        (subjectViolators SwT tConc).length, (bareViolators SwT tConc).length)

/-! ## §5 What a RESTATED conclusion would have to say

If §3 refutes, the honest restatement is a disjunction: a star-subject closure member either
carries the seed's subject, or is the seed's subject REWRITTEN onto a declared through-shape
`⟨t.subject.type, STAR, tr⟩` with `S.isSubjectWildcardUserset t.subject.type tr = true` — the
shape part (ii)'s in-bridge covers.  The count below is the check that the proposed disjunct
is EXHAUSTIVE at this store: every violator must satisfy it, so `unexplained` must be 0. -/

def unexplained (S : Schema) (t : Tuple) : List Tuple :=
  (subjectViolators S t).filter (fun u =>
    !(u.subject.type == t.subject.type
        && u.subject.name == STAR
        && S.isSubjectWildcardUserset u.subject.type u.subject.predicate))

#eval ("(11) ★ violators NOT explained by the proposed bridged-through-shape disjunct",
        (unexplained SwT tStar).length, unexplained SwT tStar)

/-! ## §6 Does the proposed disjunct stay FALSIFIABLE?

A disjunct that every star-subject member satisfies regardless would be a tautology dressed
as a scope result.  The control below asks the same question at CONTROL a, where the shape is
undeclared: there the disjunct must FAIL to explain the violators (otherwise it is inert). -/

#eval ("(12) CONTROL a -- the disjunct must NOT explain these (nonzero means falsifiable)",
        (unexplained SwTn tStar).length, unexplained SwTn tStar)

end P6PartIvClosureProbe
