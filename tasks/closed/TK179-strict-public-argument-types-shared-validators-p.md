---
id: TK179
title: strict public argument types: shared validators plus a census test over every public parameter
brief: census test over every public arg (wrong type -> refused before any SQL; unlisted arg = red) + shared validators
pri: NEXT
size: M
deps: []
related: [TK176, TK178]
parent:
labels: []
source: hand
source_hash:
created: 2026-10-30b
moved: 2026-10-30b
updated: 2026-10-30b
closed: 2026-10-30b
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-10-30b

Map: docs/tk179-strict-public-args-plan-2026-10-30.md (measurements + decision). DECIDED (user asked for the reasoning, then said file it): explicit validators at the public boundary + a census test that fails on any unclassified parameter; NOT a runtime type-check decorator. Latency is not the reason (generic bind 3.5 us = 0.6% of a ~595 us check; isinstance ~43 ns): annotations do not encode the contract (at_least must refuse True, paranoia accepts it, None is meaningful for several args), the hot methods are *args/**kwargs (two call forms; choke point tuplestr._bind), and refusals must name the rewrite. Known gap already: check("user:a", None, "doc:1") and relation=7 silently return False. Next action: write the census test, append its first red list to the plan doc, then the validators.

Map: docs/tk179-strict-public-args-plan-2026-10-30.md (first census: 391 probes, 82 ACCEPTED, 86 LATE, 36 WRONG-EXC; 60 more WRONG-EXC were the INSTRUMENT, fixed). Shared validators in src/zanzibar/schema/argcheck.py (require_str/optional_str/bool/int/session/shapes/instance) + setops.require_setops, wired at Store/adopt/TupleSource/SetEngine constructors, build_index/rebuild_index/save_schema/open_set_engine/prune_outbox/parse_openfga_schema, and tuplestr.require_parts for every call form. DECIDED: writes keep AdmissionRejected (0.1.0 changelog promise) but raise it before any SQL; reads raise TypeError for a non-str part EXCEPT None as subject predicate, which keeps its DOCUMENTED meaning (bare subject; userdocs/reference/tuple-strings.md) -- my first cut broke that and the TK181 docs runner caught it; only index_store_id=None means in place now. Census tests/test_tk179_public_arg_census.py: 681 tests, completeness check red on any unlisted public parameter; sabotage S1-S4 red (tails in docstring). Graph-index classes exempt: public to study, not to drive (backends-direct.md).

Gate tests-tile:1/4 red: my require_shapes refused malformed shape ENTRIES with TypeError, pre-empting the pinned TK147 refusal (ShapeNoLongerAccepted, with WHY/INSTEAD) in tests/test_tk147_owc_shape_refusal.py. Fixed by extracting the schema-free pair check from compiler.py::_validate_object_wildcard_shapes into compiler.py::_reject_non_pair_shapes (comment block moved with it) and calling that from argcheck.require_shapes, so the entry refusal keeps its TK147 type and text and now also precedes any SQL. TK147 + census + refused-shape-comments: 828 passed.
