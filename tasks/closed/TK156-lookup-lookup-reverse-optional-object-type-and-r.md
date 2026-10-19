---
id: TK156
title: lookup / lookup_reverse: optional object-type and relation filter
brief: TK123 SPLIT A21b: both backends, pinned by the lookup oracle
pri: NEXT
size: S
deps: []
related: [TK123]
parent:
labels: []
source: docs/tk123-api-review-2026-10-14.md
source_hash:
created: 2026-10-15b
moved: 2026-10-19b
updated: 2026-10-19b
closed: 2026-10-19b
---

SPLIT from `TK123` (review item A21b, `docs/tk123-api-review-2026-10-14.md`, call SPLIT).
`Store.lookup` / `lookup_reverse` take no object-type or relation filter, so a user who wants
"documents alice can view" filters the `result_keys` themselves (the 2026-10-14 probe:
`lookup() got an unexpected keyword argument 'relation'`). Add an optional type/relation filter
on the lookup surfaces, on both backends, pinned by `tests/test_lookup_oracle.py`'s brute-force
reference. A feature, hence not in the TK123 API break.

## Read first

- `docs/tk123-api-review-2026-10-14.md` — row A21 (the SPLIT of the filter, A21b)
- `src/zanzibar/store/_store.py::Store.lookup` — the surface to extend
- `tests/test_lookup_oracle.py` — the brute-force reference that must pin it

## Log

### 2026-10-19b

TK156/implement (workflow minion), 2026-10-19. Plan doc: docs/tk156-lookup-filter-2026-10-19.md (decisions D1-D5, sec 3 = landed/red). LANDED (uncommitted, orchestrator commits): Store.lookup(..., object_type=, relation=) and Store.lookup_reverse(..., subject_type=, subject_predicate=); new unpinned WildcardIndex.filter_result and SetEngine.filter_result (post-filter of a computed result; pinned lookup bodies and the literal signature pin in test_tk123_call_forms untouched, so no anchor-pin regenerate and no Lean change); shared schema/tuplestr.py::shape_filter; CHANGELOG [Unreleased] Added. Undeclared filter name -> empty result (lenient like every read, PROBE p1); non-str -> TypeError. TESTS: tests/test_tk156_lookup_filter.py, 8 passed in 112s; F1/F2 reuse test_lookup_oracle _Gate + its G1-G4/S4 checkers on filtered results over both backends (wildcards seed 0, boolean seed 4 with exclusion reach). Sabotage S1-S7 all RED, literal output in the module docstring. Regression set (lookup_oracle, tk123 call_forms/returns/top_level, tk155, tk122 release metadata, tk154): 151 passed; tk153 ascii/ergonomics, refused-shape comments, tk120 layout: 107 passed. RED: nothing known; verify.sh not run (orchestrator gates). Hypothesis multi-seed sweep skipped: not an algorithm change (D1). OPEN: whether reads should refuse undeclared names is a cross-read decision, not taken here. NEXT: orchestrator runs the gate and commits; then close TK156.

Review fixes (agent TK156/fix, 2026-10-19). (1) BLOCKING: removed TK156 from the public docstrings of WildcardIndex.filter_result, SetEngine.filter_result and tuplestr.shape_filter (tests/test_tk123_no_internal_refs.py was red; now green). (2) New test_filter_keeps_implicit_exclusions_by_shape pins the implicit_keys / implicit_excluded_keys channel on both backends; no seeded walk (seeds 0-5, both fixtures) or crafted TK144 schema produced a non-empty implicit exclusion, so the key channel is set by hand on a real lookup_reverse result. (3) New test_filter_result_refuses_a_stale_result pins StaleLookupIds on both backends. (4) Nit: shape_filter takes the caller keyword names; Store.lookup / lookup_reverse validate first, so a refusal reads "lookup_reverse(): subject_predicate must be a str or None, not ellipsis; write the string ... for a bare subject". Sabotage M3/M4/M5/M11/M12 all RED (recorded in the test module docstring). Targeted run: tk156 + tk155 + tk123_* + tk153 = 219 passed. Gate not run (orchestrator). Next: orchestrator gates and commits.

LANDED (uncommitted at close; the orchestrator gates and commits by path): `Store.lookup(..., object_type=, relation=)` and `Store.lookup_reverse(..., subject_type=, subject_predicate=)`, via new post-filters `WildcardIndex.filter_result` and `SetEngine.filter_result` over the shared `src/zanzibar/schema/tuplestr.py::shape_filter`. Keeps a node id / marker / exclusion / implicit key only if its (type, predicate) matches; exclusions stay with their marker shape. Content-pinned lookup bodies untouched, no CORRESPONDENCE anchor moved, no Lean change, no __all__ change. Undeclared filter names give an empty result (as check() answers False); a non-str filter is TypeError naming the caller keyword. CHANGELOG [Unreleased].
DOC: docs/tk156-lookup-filter-2026-10-19.md (FROZEN at this close; review/fix correction at the top).
TESTS: tests/test_tk156_lookup_filter.py (oracle gates on wildcards + boolean fixtures, implicit-exclusion shape pin, StaleLookupIds pin on both backends, Store-level pins); with tk155 + tk123_* + tk153*: "219 passed".
SABOTAGE (all RED): S1-S7 (graph keeps markers, graph drops exclusions, set matches name, set keeps implicit keys, Store ignores filter, Store swaps filters, shape_filter ignores predicate); review mutants M3, M4, M5, M11, M12 each "1 failed, 2 passed". BLOCKING review finding (TK156 cited in three public docstrings -> test_tk123_no_internal_refs red) FIXED and re-run green.
PG leg: reasoned skip (read-only post-filter). Hypothesis sweep: not applicable (no lookup algorithm change).
