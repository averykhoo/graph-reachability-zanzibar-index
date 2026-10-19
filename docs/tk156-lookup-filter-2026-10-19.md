# TK156 -- `lookup` / `lookup_reverse`: optional object-type and relation filter (2026-10-19)

> **FROZEN 2026-10-19, at `TK156`'s close -- provenance, not a living document.** Status
> lines below are as-of-then and several may now be false; live state: `HANDOFF.md` + the
> session ledger, and `python scripts/task.py show TK156`. Corrections are appended dated at
> the top, never edited into the body. Was ACTIVE-PLAN (`docs/README.md` sec 3) until that
> close: the working record for `TK156`.

Row: `python scripts/task.py show TK156`. Source: `docs/tk123-api-review-2026-10-14.md` row
A21 (call DO; the relation/object-type filter SPLIT as A21b). Session key `2026-10-19b`,
agent `TK156/implement` (workflow minion).

## Corrections

- **2026-10-19 (review + fix pass, agents `TK156/review*` and `TK156/fix`; transcribed by the
  records agent, REASONED from their reports).** BLOCKING, fixed: the first landing cited
  `TK156` in three public docstrings (`WildcardIndex.filter_result`,
  `SetEngine.filter_result`, `schema/tuplestr.py::shape_filter`), which turned
  `tests/test_tk123_no_internal_refs.py` red ("1 failed, 2 passed"). The ids moved into
  `# Provenance` comments, and that module is green again. Should-fix, fixed: the
  `implicit_excluded_keys` channel was untested (reviewer mutants M3/M4 survived; no seeded
  walk reached a non-empty one), so
  `tests/test_tk156_lookup_filter.py::test_filter_keeps_implicit_exclusions_by_shape` pins it
  with a hand-set key channel. `StaleLookupIds` from `filter_result` was untested (M5
  survived); now `::test_filter_result_refuses_a_stale_result` on both backends. Nit, fixed:
  `shape_filter` takes the caller's keyword names, so `Store.lookup` / `Store.lookup_reverse`
  refuse a bad filter naming `object_type` / `relation` / `subject_type` /
  `subject_predicate` (with the "write the string '...'" hint for an Ellipsis). Mutants M3,
  M4, M5, M11 and M12 each go RED ("1 failed, 2 passed"). After the fix:
  "219 passed" across tk156 + tk155 + tk123_* + tk153*.

## 1. Scout (2026-10-19)

Provenance labels: **READ** = read first-hand in the tree today; **REASONED** = inferred
from what was read; **UNVERIFIED** = not checked; **PROBE** = a script run today (the
script is gitignored; its output is transcribed here).

- **READ** `docs/tk123-api-review-2026-10-14.md` row A21: the 2026-10-14 verifier probe
  hit `lookup() got an unexpected keyword argument 'relation'`; the call was "DO; SPLIT the
  relation/object-type filter (a feature, TK123 follow-up row)".
- **READ** `src/zanzibar/store/_store.py::Store.lookup` / `::Store.lookup_reverse`: both
  take `*args, at_least=None, **kwargs`, bind the call form through
  `src/zanzibar/schema/tuplestr.py::lookup_args` / `::lookup_reverse_args`, then return the
  graph index's `LookupResult` unchanged. `_LOOKUP_LONG = (subject_predicate, subject_type,
  subject_name)`, `_REVERSE_LONG = (relation, object_type, object_name)` -- so the keyword
  names `object_type` / `relation` are FREE on `lookup`, and `subject_type` /
  `subject_predicate` are FREE on `lookup_reverse` (no clash with the call-form binder).
- **READ** `docs/tk154-stale-lookup-ids-2026-10-16.md` sec 4 + `formal/correspondence_anchor_pin.txt`
  (grep, 2026-10-19): CONTENT-PINNED (any code change reds `verify.sh lean` until a
  deliberate regenerate): `graphindex/wildcard.py::WildcardIndex.lookup`,
  `::WildcardIndex.lookup_reverse`, `setengine/engine.py::SetEngine.lookup_reverse`,
  `::SetEngine._lookup_sweep`, `graphindex/core.py::ReachabilityIndex.lookup_reachable` /
  `::lookup_reverse`. NOT pinned: `::SetEngine.lookup`, `::SetLookupResult`, graph
  `::LookupResult`, every `Store.*` lookup/translator method.
- **READ** `tests/test_tk123_call_forms.py` line ~92 (2026-10-19): pins the parameter NAMES
  of `SetEngine.lookup` / `lookup_reverse` and `WildcardIndex.lookup` / `lookup_reverse`
  literally; so adding keyword params to the backend lookups would also move that pin.
- **READ** result shapes: graph `LookupResult` (`node_ids`, `markers` as `(type, predicate,
  variant)`, `excluded_node_ids`, `implicit_keys`, `implicit_excluded_keys`); set
  `SetLookupResult` (same fields, `markers` as `(type, predicate)`, plus `id_stamp`).
  Every entry of every field names a `(type, predicate)` shape: ids through
  `Node` / the interner key, markers directly, implicit keys as `(type, name, predicate)`.
- **PROBE** `.scratch/tk155-157/TK156/probes/p1_undeclared.py` (2026-10-19): every Store
  read is LENIENT on an undeclared name: `check('user:alice', 'nope', 'doc:d1')` -> `False`;
  `lookup_reverse('nope', 'doc:d1')`, `lookup_reverse('viewer', 'nodoc:d1')`,
  `lookup('nouser:bob')` -> empty `LookupResult`; `expand('nope', 'doc:d1')` -> empty
  `ExpandResult`. (Also `CLAUDE.md` "Reads are lenient".)

## 2. Decisions (2026-10-19, agent TK156/implement)

- **D1 post-filter, not candidate pruning.** The filter restricts an already-computed
  result; it never changes which candidates a lookup generates. So it is NOT an algorithm
  change: no Lean model describes it, no CORRESPONDENCE anchor moves (REASONED from
  `CLAUDE.md` "Perf work & the Lean model": only a change to the modelled algorithm needs
  Lean). Pruning the walk by the filter would be a perf optimisation on pinned bodies; out
  of scope, perf is deprioritised.
- **D2 the filter lives at UNPINNED surfaces.** Each backend gains a NEW method,
  `WildcardIndex.filter_result(res, entity_type=None, predicate=None)` and
  `SetEngine.filter_result(res, entity_type=None, predicate=None)`, which keep exactly the
  entries whose `(type, predicate)` matches every given filter (ids classified through the
  backend's own node/interner map; markers by shape; implicit keys by key). The pinned
  lookup bodies and the literal-signature pin in `test_tk123_call_forms.py` stay untouched.
  `Store.lookup(..., object_type=None, relation=None)` and
  `Store.lookup_reverse(..., subject_type=None, subject_predicate=None)` call the graph
  index's `filter_result`. Equivalence is pinned by applying each backend's
  `filter_result` to its own lookup and checking the filtered result against the oracle.
- **D3 names.** `lookup` filters the OBJECTS: `object_type=`, `relation=`.
  `lookup_reverse` filters the SUBJECTS: `subject_type=`, `subject_predicate=` (`"..."`
  for a bare subject such as a user; a relation name for a userset). These are the names
  the long call forms already use for those parts.
- **D4 lenient, like every read.** An undeclared filter value yields an empty result
  (PROBE p1 above: `check` / `lookup` / `expand` all answer an undeclared name with
  False / empty). A non-`str`, non-`None` value is a `TypeError`. Refusing an undeclared
  name on reads would be a cross-surface decision for all reads, not TK156's (open
  question, noted on the row).
- **D5 exclusions follow their marker.** An excluded id/key always has the shape of a
  marker in the same result (pinned by the oracle gate's G4/S4 sweeps), so filtering both
  by the same shape keeps "marker minus exclusions" exact within the filter.

## 3. What landed / builds / is red (2026-10-19, agent TK156/implement)

**LANDED** (uncommitted; the orchestrator commits):

- `src/zanzibar/schema/tuplestr.py::shape_filter` -- the shared filter predicate (None/str
  check, `TypeError` otherwise; `None` when no filter is given).
- `src/zanzibar/graphindex/wildcard.py::WildcardIndex.filter_result` and
  `src/zanzibar/setengine/engine.py::SetEngine.filter_result` -- new, unpinned. The graph
  one classifies ids with one `ReachabilityIndex._load_nodes` batch and raises
  `StaleLookupIds` for a dead id; the set one goes through `SetEngine._translate` (stamp +
  dead-id refusal, the `result_keys` rule) and keeps `id_stamp`.
- `src/zanzibar/store/_store.py::Store.lookup` (`object_type=`, `relation=`) and
  `::Store.lookup_reverse` (`subject_type=`, `subject_predicate=`), overloads included.
- `CHANGELOG.md` `[Unreleased]` / Added. Version unchanged (0.0.5). No new top-level
  name: these are methods/keywords, and `__all__` is unchanged.
- **Untouched on purpose:** `WildcardIndex.lookup` / `::lookup_reverse`,
  `SetEngine.lookup` / `::lookup_reverse` (bodies and signatures), so neither
  `formal/correspondence_anchor_pin.txt` nor `tests/test_tk123_call_forms.py`'s literal
  signature pin moves. No Lean change (D1).

**TESTS** `tests/test_tk156_lookup_filter.py` (8 tests; first-hand run 2026-10-19:
`8 passed in 112.22s`). F1/F2 subclass `tests/test_lookup_oracle.py::_Gate` and reuse its
`_check_graph_forward` / `_check_graph_reverse` / `_check_set_forward` on the filtered
result over the candidates the filter keeps, plus an out-of-filter non-coverage check;
gates: `wildcards.fga` seed 0 and `boolean_wildcards.fga` seed 4 (the TK142 exclusion
seed), each 8 steps + drain. Reach asserts: a filtered marker forward on both backends
(wildcards), a filtered reverse result that kept an exclusion on both backends (boolean),
and every filter asked at least once.

- **Measured, then fixed (first-hand, 2026-10-19):** the first version asked every filter
  at every state (10m47s) and drew reverse filters from the AST's object-side shapes, so
  `('user', '...')` was never asked and the boolean exclusion reach was 0 on both backends
  (`graph=0, set=0`). Reverse filters now come from the subject-candidate shapes, and each
  state asks 2 round-robin filters plus the whole result's marker-shape filters.

**SABOTAGE** (first-hand, 2026-10-19): S1-S7, all RED; literal output in the test module's
docstring. S2 (graph drops exclusions) is caught only by the boolean seed-4 gate.

**Hypothesis seeds: not run, reasoned skip.** D1: no candidate generation or lookup
algorithm changed (`filter_result` runs after the lookup), so the multi-seed sweep that
`CLAUDE.md` asks for an algorithm change does not apply.

**Open (for the orchestrator / user):** D4 keeps an undeclared filter name lenient (empty
result), matching every read today. Whether reads should REFUSE undeclared names is a
decision across all reads, not just this one; not opened as a row.
