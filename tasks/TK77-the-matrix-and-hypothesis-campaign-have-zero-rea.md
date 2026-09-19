---
id: TK77
title: the matrix and hypothesis campaign have ZERO reach into the _sync_entity_middles surface
brief: crossable_shapes == [] for wildcards.fga and boolean_wildcards.fga under the matrix OBJECT_WC; census EMPTY 2026-09-18
pri: NOW
size: M
deps: []
related: [TK75, TK44]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-18
moved: 2026-09-19b
updated: 2026-09-19b
closed:
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-09-18

AGENT-MEASURED, independently confirmed by two agents from opposite directions (a census sweep and a coverage probe); NOT re-run first-hand here, so treat the counts as evidence and re-measure before quoting them.

`tests/test_matrix.py`, `tests/test_hypothesis.py`, `tests/test_wildcard_property.py` and `tests/test_zt_p5_readjudication.py` -- **66 tests, 4m37s -- produce an EMPTY `_sync_entity_middles` census.** Not "few hits": **zero** calls on a crossable-type entity.

CAUSE: `tests/fga_schemas/wildcards.fga` and `tests/fga_schemas/boolean_wildcards.fga` both compute `crossable_shapes == []` under the matrix's `OBJECT_WC`. Crossability needs a shape bridged IN *and* OUT; these are bridged OUT only. Coverage of this surface exists ONLY in `tests/test_i14_crossing_middles.py`, `tests/test_owc_star_parent_cross.py` and `tests/test_bulk_build.py` -- three hand-written modules, none of them differential and none of them fuzzed.

(!) **CORROBORATION FROM A SECOND DIRECTION, first-hand (this session, on `TK72`):** both ZT-P5 object-wildcard corpora also measure `crossable_shapes: []`, including the TTU one with `[user, user:*]`. **A subject wildcard does NOT create an in-bridge.** So the "it looks like an object-wildcard schema, therefore it exercises the crossing machinery" inference is wrong in at least four fixtures, and it is why `TK75` sat without a witness.

WHY IT MATTERS: the validation matrix and the hypothesis campaign are the two mechanisms this repo relies on to find semantic divergence. A surface they structurally cannot reach is a surface where the graph index and the set engine could disagree indefinitely -- and I14 / crossing middles is exactly the area that produced `TK69`, `TK70` and `P22`.

FIRST ACTION: measure `crossable_shapes` for every fixture in `tests/fga_schemas/` and publish the table (which fixtures are crossable at all, under which `object_wildcard_shapes`). That is cheap, it is the thing nobody has, and it decides whether the fix is a new matrix fixture or a generator change. Related: `TK44` (the unreached generator pair-cell space) may share a cause.

### 2026-09-19b

INHERITED FROM `TK75` (closed 2026-09-19b): this row now owns the re-add-arm fixture question, and it has a first-hand measurement to start from.

Census run first-hand 2026-09-19b over exactly the three modules this row names as the only coverage of the crossable surface -- `tests/test_i14_crossing_middles.py`, `tests/test_owc_star_parent_cross.py`, `tests/test_bulk_build.py`, run together: **7 `_sync_entity_middles` calls in total, 1 of them inside a reconcile-time GC, and that one takes the STRIP arm.** The in-GC RE-ADD arm (`_ensure_entity_middles`, the witness-survives branch) is reached **zero** times by any of them. Two of the three modules make no `_sync_entity_middles` call at all -- the count is identical whether the run is all three or `test_i14_crossing_middles.py` alone.

That tightens this row's claim in a useful direction: it is not only that the matrix and the hypothesis campaign cannot reach the crossable surface, it is that the three hand-written modules that CAN reach it exercise one branch of one function once. So the deliverable is the same fixture work this row already names, and the re-add arm is a concrete acceptance target for it.

(!) The ceiling control on that census was LEFT-ARMED and must not be read as a null result: the arm that punches an I14 hole before the real call never fired (`holes=0`) because `_entity_has_witness` was never true in-GC. The measurement supports "not REACHED", not "reached and emits nothing". The 2026-09-18 "269 in-GC re-add calls, every one emitting zero rows" figure on `TK75` was over a wider run and stays AGENT-MEASURED -- re-measure before quoting it.

`TK75` decided the re-add arm gets a RECORDED NEGATIVE rather than a forced-strip control test, on the grounds that such a test would pin a fixture invented for the probe and assert behaviour on a store state I14 forbids. That decision is reversible here once a real crossable fixture exists. The strip arm itself is now pinned: `tests/test_i14_crossing_middles.py::test_the_strip_arm_emits_from_inside_a_reconcile_time_gc` (3 rows, nesting `cascade=1 reconcile=1 gc=1`, and the honest rider that those rows map to no derived key so `_settle is None`).
