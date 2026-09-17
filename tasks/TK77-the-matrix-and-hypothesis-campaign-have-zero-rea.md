---
id: TK77
title: the matrix and hypothesis campaign have ZERO reach into the _sync_entity_middles surface
brief: crossable_shapes == [] for wildcards.fga and boolean_wildcards.fga under the matrix OBJECT_WC; census EMPTY 2026-09-18
pri: NEXT
size: M
deps: []
related: [TK75, TK44]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-18
moved: 2026-09-18
updated: 2026-09-18
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
