---
id: TK132
title: Lean isPure: test a TTU target over the tupleset's parent types, not derivedAnywhere (TK126 a+)
brief: model/code leaf-allocation gap since TK126: Lean isPure .ttu asks by NAME, Python by (type, relation)
pri: LATER
size: M
deps: []
related: [TK126]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-10-08
moved: 2026-10-08
updated: 2026-10-08
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
