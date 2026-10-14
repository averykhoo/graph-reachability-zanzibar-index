---
id: TK132
title: Lean isPure: test a TTU target over the tupleset's parent types, not derivedAnywhere (TK126 a+)
brief: model/code leaf-allocation gap since TK126: Lean isPure .ttu asks by NAME, Python by (type, relation)
pri: NEXT
size: M
deps: []
related: [TK126]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-10-08
moved: 2026-10-14
updated: 2026-10-14
closed:
---

The Lean leaf-allocation model asks whether a TTU arm is PURE by relation NAME:
`GraphIndex/Leaf.lean::isPure`'s `.ttu` case calls `derivedAnywhere` ("is this name
derived on ANY type"). Python (`src/zanzibar/schema/boolean.py::_is_pure`) asks over the
tupleset's member types. Since TK126 (2026-10-08) Python COMPILES the shapes where the two
disagree (both I5 checks are `(type, relation)`-keyed), so the model now allocates leaves
differently from the code on e.g. `GraphIndex/LeafRules.lean::SlXt`: the model drops the
TTU arm (`banned` at leaf 0), Python keeps it as closure leaf `access.0` with `banned` at
`access.1` (pinned Python-side by
`tests/test_tk126_ttu_target_name_collision.py::test_slxt_python_allocation_is_the_recorded_gap`).

Recorded, not fixed: `formal/CORRESPONDENCE.md` sec 7.1, the `TK126` entry. It is dead
inside `W4Fragment` (`computedOrDirect` bans a `.ttu` inside a derived def), so no headline
theorem is affected; this row is design (a+) of
`docs/tk126-ttu-target-boolean-name-2026-10-07.md` sec 5: make the model describe the
shipped compiler again with no recorded gap.

**Next action:** change `isPure`'s `.ttu` case to test `(pt, tgt)` for `pt` in the
`directTypes` of the tupleset's definition (as `Spec/Stratify.lean::exprRefs` already does
for taint); regenerate the `derivedAnywhere` / `isPure` rows of
`formal/headline_definitions.txt`; repair the use sites (51 lines measured 2026-10-07:
`LeafRules.lean` 41, `CascadeStable.lean` 6, `Leaf.lean` 4). The `SlXt` attack pins
(`lrXt_cross_type_drop`, `slXt_viewer_derived_anywhere`) INVERT: with a type-aware test the
cross-type arm is not dropped. Then delete the CORRESPONDENCE sec 7.1 `TK126` entry's gap
and the dated notes in `Leaf.lean` / `LeafRules.lean`. Size REASONED M (the branch is dead
inside `W4Fragment`, so headline proofs need re-plumbing, not new math), UNVERIFIED.

## Traps

- (!) Statement/definition pins (`formal/conformance/statement_pin.py`) move: regenerate
  deliberately and say why.
- (!) Do not touch `term` / `NoTtuTarget` here; that is the separate SOMEDAY row.

## Read first

- [`docs/tk126-ttu-target-boolean-name-2026-10-07.md`](../docs/tk126-ttu-target-boolean-name-2026-10-07.md) sec 4.2-4.3 and 5 (a+) (the Lean side, measured counts).
- [`formal/CORRESPONDENCE.md`](../formal/CORRESPONDENCE.md) sec 7.1, the `TK126` entry (the recorded gap).
- [`tests/test_tk126_ttu_target_name_collision.py`](../tests/test_tk126_ttu_target_name_collision.py) (the differential evidence for the served shapes).

## Log

### 2026-10-13d

Sprint re-rank 2026-10-13d (user-approved in chat): LATER -> NEXT. The Lean model allocates TTU leaves by name while the Python keys on (type, relation): a proof describing other code is the goal (formal/CORRESPONDENCE.md sec 8).

### 2026-10-14

Scout + challenge, 2026-10-14. Map: docs/tk132-lean-ispure-ttu-target-2026-10-14.md (ACTIVE-PLAN; challenge X1-X7 at the top).

MEASURED (scout PROBE P1-P7, re-run byte-identical by challenge-TK132): the Python is right and the Lean model is out of date. On SlXt and TK126 variant D (the mainstream "inherit from parent, minus a ban" idiom) the Python graph index agrees with the oracle on every grid query; the Lean model allocates leaves differently (Python viewer.0/1/2, Lean viewer.0/1). The sizing premise "re-plumbing, not new math" is wrong: GraphIndex/LeafRules.lean::ttuTargetsSatL_ne_of_noTtuTarget gets its leaf half from the name test, is FALSE under a type-aware isPure (counterexample LeafRuleWitness.SlXt, checked in Lean), and feeds the two headline-pinned statements runCascade2_no_abort and cascade2_drains. Scout recommendation: design L-A (type-aware isPure .ttu arm + one decidable carry LeafTtuTargetsUnderived S discharged from W4Fragment.computedOrDirect, threaded beside hNBD; M math, L edit surface, about 70 declarations / 15 files). Separate and out of scope: the 2026-08-14 Lean graph-mode fail-closed class (SlXtR, StD).

CHALLENGE FINDINGS (verdict NEEDS-CHANGES):
X1 the step-3(d) discharge lemma is FALSE as specified under DUPLICATE KEYS: leafRewrites iterates S.defs.filter isDerived while computedOrDirect quantifies over S.lookup, so a duplicated key's second def emits leaf rules lookup never sees (PROBE DupKeys.lean, witness SDup). Fix: add (hNK : NodupKeys S), bridged with RulesSound.lean::lookup_of_mem; all 3 STOP sites hold hA : GraphAdmission S T, so hA.nodup supplies it. Optional permanent decide pin at SDup.
X2 a .all -> .any slip over parent types is UNPINNED: over all 64 named Lean schemas only T0aCounter.S differs, and it has no allocation pin. Witness SMix (doc#parent: [folder, team], team#viewer derived, folder#viewer plain). Fix: permanent pin lrMix_mixed_parent_drop : leafRewrites SMix = [...] by decide, SMix in the T2 / TK119 fixtures, sabotage S5 (.all -> .any) must turn it red; Python-side control is "compile raises" (Python fails closed with the I5 ValueError).
X3 the headline theorems get STRICTLY NARROWER on served shapes, not merely "vacuous on W4Fragment": on SD and SlXt the schema-level premises hold today and the new carry is false under the type-aware allocation, so after L-A both statements stop covering D, D_nested and SlXt. Their coverage today is of a model that is not the code, which is the honest reason to accept the loss; it must be stated in the commit, the formal/history note and here.
Also: X4 the intermediate lemma is type-blind (a typed repair must restate it typed); X5 L-B (store-validity premise, no scope loss on D) is cheaper than the scout claimed (UNVERIFIED) and must be weighed against L-A deliberately; X6 TK119's 4th mismatch is W3 (pure-UNION merge path), so add a Lean twin of W3 with its own decide pin; X7 minor (T2 filter on the object predicate only).
Interaction with TK119: if TK119 lands first, TK132's acceptance becomes "_TK132_EXPECTED empties and the leaf-rules differential is green", deleting those entries in the same commit.

STATUS: a decision (L-A with X1-X3 fixes vs L-B) is being taken now (2026-10-14). Nothing built. Not closed here.

BUILT 2026-10-14 (agent build-TK132), design L-A amended by X1/X2/X6 per the "Decision 2026-10-14" section of docs/tk132-lean-ispure-ttu-target-2026-10-14.md; build corrections appended at the top of its Corrections; pin-regeneration WHY + literal sabotage outputs in formal/history/tk132-ispure-parent-types-2026-10-14.md.

LANDED: Leaf.lean::ttuParentTypes + isPure .ttu arm = !isDerived S (ty, ts) && (ttuParentTypes S ty ts).all (fun pt => !isDerived S (pt, tgt)). LeafRules.lean::LeafTtuTargetsUnderived (decidable carry); ttuTargetsSatL_ne_of_noTtuTarget / rewriteClosureL_subject_pred_ne_of_noTtuTarget take hLTU after hder; the two derivedAnywhere_eq_false_of_mem_* lemmas deleted. Discharge CascadeStable.lean::leafTtuTargetsUnderived_of_computedOrDirect (hNK, X1) + _of_computedOnly. Threading MEASURED at 13 declarations / 14 discharge sites (not P3's ~52/~21). Witnesses: lrXt_cross_type_kept (inverted), hLTU_load_bearing, slXt_not_leafTtuTargetsUnderived, SMix/lrMix_mixed_parent_drop, SlW3/lrW3_merged_computed_ttu, leafTtuTargetsUnderived_snlBoth, FragmentDecide.lean::LeafRuleWitness.leafTtuTargetsUnderived_needs_nodup (SDup). TK119's four _TK132_EXPECTED pins FLIPPED (each reported got {}), dict + test deleted, mismatching set now EMPTY, SMix added, floor 44 -> 49. New formal/conformance/test_conformance_tk132_leaf_rows.py (T2): leaf rows EQUAL on SlXt/SlXtR/StD/D/D_nested, residual positively pinned as TK149 (filed, LATER: the 2026-08-14 Lean graph under-report).

WHY the two headline statements moved (verbatim): the two statements gain a schema carry the faithful allocation needs; it is vacuous on W4Fragment, and it is FALSE on D/D_nested/SlXt, whose previous coverage was of the wrong model. L-B (buys D back) stays deferred to TK133.

SABOTAGES, each red first (literal in the history note): S1 revert arm -> lrXt_cross_type_kept, hLTU_load_bearing.3, slXt_not_*, lrW3 red; S2 same-type -> stD_leaves (S2b: lrStD_no_ttu_rule) red; S3 wrong-def lookup -> stD_leaves red; S5 .all->.any -> ONLY lrMix red, Python any-control raises (permanent); S6 drop hNK -> discharge build red; S4 Python name test (permanent, both modules) -> exactly D/D_nested/SlXt/W3 (rules) and SlXt/D/D_nested (state).

BUILDS: lake build ZanzibarProofs rc=0, zcli rc=0, Audit standard axioms only, statement/definition/anchor/claim-rot pins regenerated and green, both conformance modules green. The full phased gate is run after this comment; its verdict is in the commit message. NEXT ACTION: close TK132 once that commit lands (freeze the ACTIVE-PLAN doc then).
