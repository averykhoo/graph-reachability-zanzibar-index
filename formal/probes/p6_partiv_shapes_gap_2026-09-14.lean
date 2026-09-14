/-
  ★ P6 PART (iv), route `D` cone — step 3: the ROOT CAUSE, and the trap in fixing it
  (2026-09-14g).

  THE CHAIN, measured across three probes this session:

  1. `p6_partiv_residue_locus_2026-09-14.lean` — the Lean residue at `(doc:d1, admin)` has
     `stars := []`; the read path is innocent.
  2. `p6_partiv_python_residue_2026-09-14.py` — the SHIPPED residue there has
     `stars := [('folder','viewer')]` and `upos := []`. Opposite representations.
  3. `p6_partiv_starfold_cause_2026-09-14.lean` — `coveredFn` at that shape and object
     already returns **true** for `admin`. So the coverage TEST is innocent too.

  The live fold is `CascadeStrata.lean:187::GraphState.reconcileResidueKeyR`:

      let stars := shapes.filter (fun sh => σ.coveredFnR T dt on R e sh)

  A `filter` cannot produce a shape its input list never contained. So if the test says
  `true` and `stars` is empty, `("folder","viewer")` was never in `shapes`.

  THE ROOT CAUSE (READ). `zanzibar_utils_v1.py` builds `SchemaInfo.subject_wildcard_shapes`
  in TWO passes — declared wildcard restrictions (`:993-995`), **plus** a star-tupleset
  through-shape pass (`:1001-1008`): for each TTU, if its tupleset relation carries a bare
  wildcard restriction, add `(r.type, ttu.target_rel)`. Its own comment says why — *"that
  through-shape must be declared or the graph rejects a schema-legal write the set engine
  accepts."*

  `GraphIndex/ReconcileStars.lean:97::wildcardShapes` implements **only the first pass**,
  while its docstring cites that very Python function as its correspondent. Measured live:
  Python returns `[('folder','...'), ('folder','viewer')]`; Lean returns `[("folder", BARE)]`.

  ⚠ THE TRAP THIS PROBE EXISTS TO CATCH. `FullScope.lean:322::W4Fragment` carries
  `wsBare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE`. If `wildcardShapes` is corrected to
  include the through-shape, that shape's predicate is `"viewer"`, NOT `BARE` — so `wsBare`
  goes **false** at exactly the schemas part (iv) is trying to admit. Fixing the model
  faithfully could therefore make the `TtuStarFreeW` widening INERT: the fragment would
  keep rejecting the store, just via a different field.

  **That is the question this probe answers, and it decides whether route `D` helps part
  (iv) or defeats it.** It is measured rather than argued because the 2026-09-14f session
  lost a step exactly here — reasoning about `wsBare` from the definition instead of
  evaluating it.

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_partiv_shapes_gap_2026-09-14.lean

  ⚠ rc=0 with NO output is a FAILED run, not a green one.
  ⚠ INSTRUMENT CONTROL `(I)`: the local `wildcardShapesFixed` below is MY transcription of
    Python's two passes, not the shipped function. If it were simply "pass 1 plus a constant"
    it would add the shape everywhere and prove nothing. `(I)` runs it on a schema with NO
    star tupleset and demands it AGREE with `wildcardShapes` there.

  ── THE VERDICT (2026-09-14g) ──────────────────────────────────────────────────────────────

  **The root cause is confirmed, the transcription matches the shipped output exactly, AND
  THE TRAP FIRED.**

  1. `(1)` `wildcardShapes Sp = [("folder", "...")]`; `(2)` the second pass mints
     `[("folder","viewer")]`; `(3)` together they are
     `[("folder","..."), ("folder","viewer")]` — **identical to the shipped
     `SchemaInfo.subject_wildcard_shapes`** measured at
     `formal/probes/p6_partiv_python_residue_2026-09-14.py`. So the Lean model is missing
     precisely Python's second pass, and nothing else.
  2. `(5)` the newly-minted shape IS covered at `(doc:d1, admin)` (`true`), while the BARE
     shape is not (`false`). So with the corrected list the fold's `filter` retains it,
     `stars` acquires `("folder","viewer")`, and the phantom-subject divergence closes.
  3. ⚠ `(4)` **`wsBare` goes `true` → `false`.** Correcting the enumeration makes
     `FullScope.lean::W4Fragment.wsBare` FALSE at `Sp`, because the through-shape's
     predicate is `"viewer"` and `wsBare` demands every wildcard shape be `BARE`. **The
     fragment would then reject this store via `wsBare` instead of via `ttuStarFree` — so
     the part (iv) widening would admit nothing new at this schema.**

  **The fix that makes the model honest also makes the widening inert. That is the whole
  decision, and it is now measured rather than forecast.**

  `(I)` INSTRUMENT CONTROL PASSED: on `Sc` (concrete tupleset) the second pass adds nothing
  and `wildcardShapesFixed = wildcardShapes` exactly. So `throughShapes` is not "pass 1 plus
  a constant" — it fires on the star tupleset specifically, which is what makes `(2)`/`(4)`
  attributable.

  ── ADDED 2026-09-14g, SECOND RUN: the naive fix falsifies an AUDITED theorem ──────────────

  `(6)` `(true, false)` at `W4Witness.SxThruDerived`. **Correcting `wildcardShapes` without
  re-pointing `wsBare` makes `FullScope.lean:1113::sxThruDerived_wsBare_holds_but_usWild_fails`
  FALSE** — an audited name (`formal/audited_theorems.txt:91`) whose first conjunct is
  `∀ sh ∈ wildcardShapes SxThruDerived, sh.2 = BARE`, proved `by decide`. `(7)` shows pass 2
  minting `("folder","viewer")` there, from the bare star tupleset at `doc#parent` that the
  schema's own docstring calls *"`wsBare`-legal"*.

  This was reported by a `claude-fable-5` subagent and is verified here first-hand rather
  than quoted, per `CLAUDE.md` § Delegation — it was headed for a gate-pin decision.

  **Consequence: re-pointing `wsBare` at a `declaredWildcardShapes` (today's one-pass body,
  renamed) is MANDATORY for any enumeration fix, not merely preferable.** The
  `D1`-vs-`D2` framing that priced `D2` as "the cone alone" was an underprice.

  `(I2)` INSTRUMENT CONTROL PASSED: the sibling `SxThruPlain` — which differs on ONE axis,
  the boolean operator — gains the SAME shape. So pass 2 keys off the star tupleset and not
  the operator, which is what makes `(6)` attributable to the enumeration.

  ⚠ WHAT THIS DOES NOT ESTABLISH. `wildcardShapesFixed` is a LOCAL transcription living in
  this probe; the shipped `wildcardShapes` is untouched and nothing is proved about the
  corrected version. Whether `wsBare` can be soundly weakened to tolerate the through-shape
  — the obvious repair — is a proof-architecture question this probe does not answer. The
  `wildcardShapes` cone is `235` references across `18` files (as-of 2026-09-14g, `rg` over
  `formal/lean/ZanzibarProofs/`), so this is not a one-line change.

  ── LITERAL TRANSCRIPT (the run's own stdout; nothing added, removed or reordered) ─────────

  RAN 2026-09-14g, rc=0, from `formal/lean` via
  `export PATH="$HOME/.elan/bin:$PATH" && lake env lean ../probes/p6_partiv_shapes_gap_2026-09-14.lean`.

  --------------------------------- BEGIN VERBATIM -----------------------------------------

("(1) ★ wildcardShapes Sp -- what the Lean model enumerates today", [("folder", "...")])
("(2) ★ throughShapes Sp -- what Python's SECOND pass adds", [("folder", "viewer")])
("(3) ★ wildcardShapesFixed Sp -- should match Python's [('folder','...'), ('folder','viewer')]",
  [("folder", "..."), ("folder", "viewer")])
("(4) ★★ wsBare under (today's wildcardShapes, the corrected one) at Sp -- if this is (true, false) the fix DEFEATS the widening at this schema",
  true, false)
("(I) INSTRUMENT CONTROL -- on the CONCRETE-tupleset schema Sc the second pass must add NOTHING; (wildcardShapes, throughShapes, fixed, agree?)",
  [], [], [], true)
("(5) for each shape the CORRECTED list mints, is it covered at (doc:d1, admin)?",
  some [(("folder", "..."), false), (("folder", "viewer"), true)])
("(6) ★★★ at W4Witness.SxThruDerived (AUDITED, FullScope.lean:1113): wsBare under (today's wildcardShapes, the corrected one) -- (true, false) means the naive fix FALSIFIES an audited theorem",
  true, false)
("(7) what the corrected list mints at W4Witness.SxThruDerived -- (today, added by pass 2)", [("folder", "...")],
  [("folder", "viewer")])
("(I2) INSTRUMENT CONTROL for (6) -- SxThruPlain must gain the SAME shape (pass 2 keys off the star tupleset, not the boolean operator)",
  [("folder", "viewer")], true)

  ---------------------------------- END VERBATIM ------------------------------------------

  ⚠ `(6)`/`(7)`/`(I2)` were added in a SECOND run; `(1)`-`(5)` and `(I)` are byte-identical
  across both runs. The first run's rc=1 was my own error (an unqualified `SxThruDerived`
  and a `/-- -/` doc comment on an `#eval`), not a measurement.

-/
import ZanzibarProofs

open Zanzibar

namespace P6PartIvShapesGap

/-! ## §1 The schema under test — VERBATIM from the sibling probes. -/

def Sp : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, true)]),
    (("doc", "access"),    .ttu "viewer" "parent"),
    (("doc", "banned"),    .direct [("user", BARE, false), ("folder", "viewer", false)]),
    (("doc", "admin"),     .excl (.computed "access") (.computed "banned")),
    (("doc", "gate"),      .inter (.computed "admin") (.computed "access"))], []⟩

/-- CONTROL schema: same shape of thing, but the TTU's tupleset parent is CONCRETE, so
    Python's second pass adds nothing. Used by `(I)`. -/
def Sc : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, false)]),
    (("doc", "access"),    .ttu "viewer" "parent"),
    (("doc", "admin"),     .excl (.computed "access") (.computed "viewer"))], []⟩

/-! ## §2 The shipped second pass, transcribed into Lean

Mirrors `zanzibar_utils_v1.py:1001-1008`: for every TTU in every def, look up the TTU's
TUPLESET relation on the SAME object type; if that relation carries a wildcard restriction
whose predicate is bare, contribute `(restriction type, ttu target relation)`. -/

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

/-! ## §3 ★ THE GAP -/

#eval ("(1) ★ wildcardShapes Sp -- what the Lean model enumerates today", wildcardShapes Sp)
#eval ("(2) ★ throughShapes Sp -- what Python's SECOND pass adds", throughShapes Sp)
#eval ("(3) ★ wildcardShapesFixed Sp -- should match Python's [('folder','...'), ('folder','viewer')]",
        wildcardShapesFixed Sp)

/-! ## §4 ★★ THE TRAP — does correcting the enumeration flip `wsBare`?

`W4Fragment.wsBare` is `∀ sh ∈ wildcardShapes S, sh.2 = BARE`, stated here in its decidable
`.all` form. If the corrected list makes this FALSE, then a faithful fix to
`wildcardShapes` excludes `Sp` from `W4Fragment` via `wsBare` — and the `ttuStarFreeW`
widening admits nothing new at this schema. -/

def wsBareOf (shapes : List Shape) : Bool := shapes.all (fun sh => sh.2 == BARE)

#eval ("(4) ★★ wsBare under (today's wildcardShapes, the corrected one) at Sp -- " ++
       "if this is (true, false) the fix DEFEATS the widening at this schema",
        wsBareOf (wildcardShapes Sp), wsBareOf (wildcardShapesFixed Sp))

/-! ## §5 INSTRUMENT CONTROL -/

#eval ("(I) INSTRUMENT CONTROL -- on the CONCRETE-tupleset schema Sc the second pass must " ++
       "add NOTHING; (wildcardShapes, throughShapes, fixed, agree?)",
        wildcardShapes Sc, throughShapes Sc, wildcardShapesFixed Sc,
        wildcardShapesFixed Sc == wildcardShapes Sc)

/-! ## §6 Does the corrected list actually let the fold produce the shape?

`(2)` of the star-fold probe measured `coveredFn` TRUE for `("folder","viewer")` at `admin`.
With the shape now in the candidate list, the fold's `filter` would retain it. This restates
that coverage here so the transcript stands alone, and checks the shape really is the one
the corrected enumeration mints. -/

def tPar : Tuple := ⟨⟨"folder", STAR, BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def tView : Tuple := ⟨⟨"user", "alice", BARE⟩, "viewer", ⟨"folder", "f1"⟩⟩
def tObj : Tuple := ⟨⟨"user", "bob", BARE⟩, "viewer", ⟨"folder", "f2"⟩⟩
def prefixOps : List GraphOp := [GraphOp.add tPar, GraphOp.add tView]

def live : Option (GraphState × Store) :=
  (graphRunOps Sp prefixOps).map (fun p =>
    let To := tObj :: p.2
    (cascadeLeg Sp To (p.1.writeLoggedRules Sp tObj), To))

#eval ("(5) for each shape the CORRECTED list mints, is it covered at (doc:d1, admin)?",
        live.bind (fun p => (Sp.lookup ("doc", "admin")).map (fun e =>
          (wildcardShapesFixed Sp).map (fun sh =>
            (sh, p.1.coveredFn p.2 "doc" "d1" "admin" e sh)))))

/-! ## §7 ★★★ DOES THE FIX FALSIFY AN AUDITED THEOREM? (added 2026-09-14g, second run)

A `claude-fable-5` subagent, asked to decide the route, reported that the naive fix
(correct `wildcardShapes`, leave `wsBare`'s text pointing at it) would make
`FullScope.lean:1113::sxThruDerived_wsBare_holds_but_usWild_fails` FALSE — an AUDITED name
(`formal/audited_theorems.txt:91`). A subagent's report is evidence, not a finding
(`CLAUDE.md` § Delegation), and this one is headed for a gate-pin decision, so it is
verified here first-hand rather than quoted.

The theorem's first conjunct is `∀ sh ∈ wildcardShapes W4Witness.SxThruDerived, sh.2 = BARE`, proved
`by decide`. `W4Witness.SxThruDerived` declares `doc#parent := [folder, folder:*]` (a BARE star
tupleset — its own docstring calls it *"`wsBare`-legal"*) and `doc#viewer := viewer from
parent`. Python's second pass therefore mints `("folder","viewer")` there, whose predicate
is not BARE.

If `(6)` shows `true → false`, the naive fix falsifies an audited theorem, and re-pointing
`wsBare` at a `declaredWildcardShapes` (today's one-pass body, renamed) is MANDATORY for any
enumeration fix — not merely preferable. -/

#eval ("(6) ★★★ at W4Witness.SxThruDerived (AUDITED, FullScope.lean:1113): wsBare under " ++
       "(today's wildcardShapes, the corrected one) -- (true, false) means the naive fix " ++
       "FALSIFIES an audited theorem",
        wsBareOf (wildcardShapes W4Witness.SxThruDerived),
        wsBareOf (wildcardShapesFixed W4Witness.SxThruDerived))

#eval ("(7) what the corrected list mints at W4Witness.SxThruDerived -- (today, added by pass 2)",
        wildcardShapes W4Witness.SxThruDerived, throughShapes W4Witness.SxThruDerived)

/-! CONTROL for `(6)`: the sibling schema `SxThruPlain` differs from `SxThruDerived` on ONE
axis (the boolean operator), and its through-shape is derived-free. Pass 2 keys off the star
tupleset, not the operator, so it must mint the SAME shape here — otherwise `(6)` is about
the operator rather than about the enumeration. -/

#eval ("(I2) INSTRUMENT CONTROL for (6) -- SxThruPlain must gain the SAME shape " ++
       "(pass 2 keys off the star tupleset, not the boolean operator)",
        throughShapes W4Witness.SxThruPlain,
        throughShapes W4Witness.SxThruPlain == throughShapes W4Witness.SxThruDerived)

end P6PartIvShapesGap
