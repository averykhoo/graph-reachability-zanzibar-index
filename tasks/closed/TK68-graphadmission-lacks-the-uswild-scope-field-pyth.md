---
id: TK68
title: GraphAdmission lacks the usWild scope field Python enforces (UnsupportedByGraphIndex)
brief: Blocks P6 step 3b: reachedByW3d_edge_source_ne_R is FALSE once the write leg bridges
pri: LATER
size: S
deps: []
related: [P6]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-13d
moved: 2026-09-13e
updated: 2026-09-13e
closed: 2026-09-13e
---

`FullScope.lean::GraphAdmission` mirrors Python's schema-admission rejections field by
field, and one of them is missing: it has `objWild` for `UnsupportedByGraphIndex` on OBJECT
wildcards over derived relations, and no twin for the same rejection on WILDCARD USERSETS
over derived relations. The Lean admission predicate is therefore strictly weaker than the
shipped compiler. Inert today because no live chain calls `ensureInBridges`; `P6` step 3b
makes it live and immediately needs the field.

## Traps

⚠ **Do not try to save `reachedByW3d_edge_source_ne_R` with a premise — restate it.** The
type-index trap is in the `2026-09-13d` Log entry: `isDerived` and
`isSubjectWildcardUserset` are keyed on `(type, relation)` while that theorem concludes
about the predicate STRING, and a literal `[x:*#R]` restriction at an untainted key
`(x, R)` is legal Python. The wrapper `::reachedByW3d_Rnode_not_source` survives only
because it fixes the type to `dt`.

⚠ **This row is ONE measured instance, not a census of `GraphAdmission`.** It was found by
following a single broken proof. Whether other Python admission rejections are unmirrored
is unmeasured; do not let closing this row imply the structure was swept.

## Read first

- the `2026-09-13d` Log entry below — the gap, why it is inert today, and the type-index trap
- `formal/lean/ZanzibarProofs/FullScope.lean::GraphAdmission` — the structure, and `objWild`
  as the field this one should sit beside
- `formal/lean/ZanzibarProofs/GraphIndex/UsStarWrite.lean::Schema.isSubjectWildcardUserset` —
  the predicate the new field must constrain, and its two disjuncts
- `formal/lean/ZanzibarProofs/GraphIndex/Cascade.lean::reachedByW3d_edge_source_ne_R` and
  `::reachedByW3d_Rnode_not_source` — the theorem that goes false and its one consumer
- `tasks/P6-ttustarfree-ii-bridges-on-rule-routed-write-path.md` — the `2026-09-13d` entry,
  for where this sits in step 3b

## Log

### 2026-09-13d

Found by P6 step 3a (2026-09-13d) while measuring the cone, not by a sweep of the admission structure -- so treat the scope of this row as ONE measured instance, not a census.

THE GAP. `FullScope.lean::GraphAdmission` (`:160`) carries `objWild : forall tr in S.objectWildcards, isDerived S tr = false` -- the Lean mirror of Python refusing OBJECT wildcards on derived relations. `zanzibar_utils_v1.py` rejects TWO shapes with `UnsupportedByGraphIndex`, the other being WILDCARD USERSETS OVER DERIVED RELATIONS (CLAUDE.md "Layout / mental model" names both), and `GraphAdmission` has no field for the second. So the Lean admission predicate admits a schema the shipped compiler refuses.

WHY IT IS INERT TODAY, AND WHEN IT STOPS BEING. `Schema.isSubjectWildcardUserset` only reaches a live chain through `ensureInBridges`, and no live chain calls that yet -- `writeRules` / `writeLoggedRules` are bridge-free folds. P6 step 3b is what makes it live, and the obligation surfaces immediately there: `Cascade.lean::reachedByW3d_edge_source_ne_R` (audited, `Audit.lean:714`) says no edge on a W3d state is sourced at a node with predicate R. A bridge edge is sourced at its CONCRETE endpoint, so once the write leg bridges, that statement is FALSE for any bridged-in shape whose predicate is R -- and its one Lean consumer, `::reachedByW3d_Rnode_not_source`, needs exactly `isSubjectWildcardUserset S dt R = false` at the SAME key `(dt, R)` it already knows is derived. That is this field.

MEASURED, not predicted: with the step-3b composition in the tree, `reachedByW3d_edge_source_ne_R` is the ONLY error `Cascade.lean` reports that is not mechanical, and `reachedByW3d_Rnode_not_source` is the only Lean consumer of it (grep 2026-09-13d: three other hits are two Audit lines and one prose citation in `CascadeStrata.lean:1594`).

(!) THE TYPE-INDEX TRAP, which is why the general lemma must be RESTATED and not merely re-premised. `isDerived` and `isSubjectWildcardUserset` are both keyed on `(type, relation)`, but `reachedByW3d_edge_source_ne_R` concludes about the predicate STRING `R`. A literal `[x:*#R]` restriction at an UNTAINTED key `(x, R)` is legal Python and bridges a node whose pred is `R`, so `a.pred != R` is false as a general claim no matter what field is added. The wrapper survives because it fixes the type to `dt`. Do not try to save the general statement with a premise.

SCOPE. Add the field next to `objWild`, discharge it where the other admission fields are discharged, and use it at `reachedByW3d_Rnode_not_source`. Sized S on the assumption that P6 step 3b pays the surrounding cone anyway; filed separately because it is a FIDELITY gap in its own right -- the Lean admission predicate is weaker than the shipped compiler -- and would be worth closing even if P6 were abandoned.

### 2026-09-13e

CLOSED. The field, the carry and the bridge are in the tree, audited, swept twice, and the
cone is MEASURED. Whole-tree Lean build green (1089 jobs, job count UNCHANGED). Full write-up:
`formal/history/tk68-uswild-admission-field-2026-09-13.md` (FROZEN) -- the def-pin
adjudication `verify.sh` step 4c demands lives there, not here.

WHAT LANDED.
* `FullScope.lean::GraphAdmission.usWild` -- `forall k in taintedKeys S,
  S.isSubjectWildcardUserset k.1 k.2 = false`, beside `objWild` and in the same
  quantify-over-a-computed-list shape, so all SEVEN construction sites (4 `where`-blocks in
  `FullScope.lean`, 3 anonymous `refine` constructors in `GraphIndex/Exec.lean`) discharge it
  `by decide`. The row said "discharge it where the other admission fields are discharged";
  the census found seven sites, three of them positional, and the positional ones break
  silently on an arity change.
* `GraphIndex/UsStarWrite.lean::NoBridgedDerived` -- the schema-level, store-FREE carry
  (`forall dt R, isDerived -> isSubjectWildcardUserset = false`), and
  `FullScope.lean::GraphAdmission.noBridgedDerived` as the bridge from the decidable field to
  it. Two forms on purpose: the field must be `decide`-shaped for the seven sites, the carry
  must be a forall-over-strings for the consumers.

THE FIDELITY CLAIM IS PINNED, NOT ASSERTED. `sxUsWild_not_admitted` /
`sxThruDerived_not_admitted` (the bundle REFUSES the two schemas Python refuses) and
`sxUsPlain_admitted` / `sxThruPlain_admitted` (it ACCEPTS their one-bit-away controls -- one
`wildcard` flag, one boolean operator).

(!) THE SHARP HALF, and the reason the obvious independence pin was not enough.
`sxUsWild_other_admission_fields_hold` copies the `computedRefsNotLeaf` precedent and shows
`usWild` is independent of the other ADMISSION fields. That leaves it dismissible at the
HEADLINES, because `W4Fragment.wsBare` forces every shape in `wildcardShapes S` BARE and
therefore makes disjunct (a) of `isSubjectWildcardUserset` identically false on the whole W4
fragment -- and `SxUsWild` carries a non-bare wildcard restriction, so `wsBare` is false at
it. `sxThruDerived_wsBare_holds_but_usWild_fails` closes that: `wsBare` HOLDS and `usWild`
fails anyway, through the purely schematic star-tupleset THROUGH-shape, which neither
`wsBare` nor the store-indexed `ttuStarFree` constrains. That is also the disjunct `P6` is
about.

(!) THE SWEEP CHANGED THE DELIVERABLE -- the seventh consecutive time, and it is step 3a's
lesson recurring one step later. On run 1, `M1` (re-range `usWild` over `S.objectWildcards`,
the plausible copy-paste slip from the field beside it) and `M2` (re-range it over `[]`,
vacuous on EVERY schema) -- i.e. THE TAUTOLOGY ATTACK, the one thing the whole block exists
to refuse -- reddened `GraphAdmission.noBridgedDerived` and NOTHING else. A broken PROOF, not
a broken claim. The cause is transferable and worth carrying: **every pin RE-SPELLED the
predicate instead of reading the FIELD**, so no mutation of the field could move them by
construction. The four `_admitted`/`_not_admitted` pins were added in response; they name
`GraphAdmission` in their statements, so a tautological field makes them FALSE rather than
merely unproved.

`M0` attributed correctly (the step-0 regex defect has not returned) and no anchor missed
(the step-2 CRLF defect has not returned). `M11`'s first form appended a `True := trivial`
marker and came back INERT -- it did not touch the property under test, which is step 2's
`M12` trap; re-aimed at the ROUTING, where an INERT verdict is the expected one and is itself
the finding.

(!) THE ROW'S THIRD CLAUSE IS NOT SIZE `S`, AND THE ROW NAMED HALF THE WORK. "use it at
`reachedByW3d_Rnode_not_source`" is `P6` step 3b, and it is bigger than this row said,
measured first-hand (`.scratch/tk68_declcone.py`; unit: APPLICATIONS = occurrences in
comment-stripped bodies, CONE = transitive closure excl. the seeds):

  `Cascade.lean::reachedByW3d_edge_source_ne_R`        audited   1 app   14 decls / 5 files
  `Cascade.lean::reachedByW3d_Rnode_not_source`        audited   2 app   13 decls / 5 files
  `CascadeStrata.lean::reachedByW3d2_edge_source_ne_R` NOT aud.  1 app   35 decls / 8 files
  `CascadeStrata.lean::reachedByW3d2_Rnode_not_source` audited   8 app   34 decls / 8 files
  union of the four                                             12 app   47 decls / 12 files
                                                                         (51 with the seeds)

This row and `P6`'s `2026-09-13d` entry both name ONLY the W3d pair. The two-round twins
(`CascadeStrata.lean:1595`/`:1667`) are verbatim analogues whose `write` case takes the same
`writeLoggedRules_evalEq -> writeRulesRaw -> foldl_writeDirect_edges_sound` step, so they go
false for the same reason -- and it is the W3d2 pair, not the W3d pair, that is ON THE
HEADLINE PATH: the W3d cone stops below the headlines, the W3d2 cone reaches `FullScope.lean`
and contains `graph_correct`, `graph_correct_public`, `backend_equivalence`,
`exclusion_effective`, `no_ghost_grant`, `graph_reached_inv`.

Two facts make that affordable, and they are why the carry is shaped as it is:
(1) it TERMINATES in `GraphAdmission` -- `graph_correct` (`FullScope.lean:616`) already binds
    `hA` and passes explicit field projections down, so `hA.noBridgedDerived` is one more
    projection and NO headline gains a hypothesis (the `leafScope` route);
(2) it is STORE-FREE, so it needs no weakening lambdas. The neighbouring `W4Fragment.term` is
    store-indexed, spelled out at 134 declarations, and needs a two-line weakening lambda at
    22 of them -- so extending THAT conclusion by a conjunct, the obvious-looking route, is a
    134-site edit. Do not take it.

(!) THE RESTATEMENT IS LEGAL, measured: neither theorem's STATEMENT is pinned. Neither name
appears in `formal/headline_statements.txt` or `formal/headline_definitions.txt` (those pin
`def`s reachable from headline statements; these are theorems used only in proofs). Only the
NAMES are pinned, in `formal/audited_theorems.txt`. So 3b may restate them freely provided
the names stay audited -- which is the "restate, don't rescue" move this row prescribed.

NOT DONE, DELIBERATELY: the restatements themselves. They only become PROVABLE once the write
leg actually bridges, and restating now would mean moving an audited theorem to a form
nothing yet needs. The type-index trap on this row still stands and is now also recorded on
`NoBridgedDerived`'s docstring, where the person doing the restatement will meet it.

THE DEF-PIN FIRED, AS DESIGNED, and was regenerated deliberately: `GraphAdmission` gained a
field and `Schema.isSubjectWildcardUserset` + `::isStarTuplesetThrough` became newly reachable
from a headline statement (251 -> 253 rows, no row removed). `headline_statements.txt` did not
move (51/51). Direction of the change, stated because it matters: a new admission field makes
the headlines cover FEWER schemas -- legitimate here only because the schemas removed are
exactly the ones `compile_ruleset` REFUSES, so no shipped behaviour left the claim. This is
the fragment catching up to the code, not the narrowing `CLAUDE.md` "Who decides" forbids.

SCOPE UNCHANGED: this row was ONE measured instance, not a census of `GraphAdmission`.
Closing it does not mean the structure was swept for other unmirrored Python rejections.
