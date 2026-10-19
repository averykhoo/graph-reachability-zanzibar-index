# TK155 -- `Store.expand`: Zanzibar Expand on the composed store, returning keys (2026-10-19)

> **FROZEN 2026-10-19, at `TK155`'s close -- provenance, not a living document.** Status
> lines below are as-of-then and several may now be false; live state: `HANDOFF.md` + the
> session ledger, and `python scripts/task.py show TK155`. Corrections are appended dated at
> the top, never edited into the body. Was ACTIVE-PLAN (`docs/README.md` sec 3) until that
> close: the working record for `TK155`.

Row: `python scripts/task.py show TK155`. Source: `docs/tk123-api-review-2026-10-14.md` row
A26 (call SPLIT). Session key `2026-10-19b`, agent `TK155/implement` (workflow minion).

## Corrections

- **2026-10-19 (review + fix pass, agents `TK155/review*` and `TK155/fix`; transcribed by the
  records agent, REASONED from their reports).** The review found no semantic divergence
  (90 fixture walks + 116 generated-schema walks, 0 FAIL). It found one should-fix: no test
  reached a userset-star marker such as `(group, member)`; mutation M8 (drop non-bare
  markers) stayed green. Fixed by
  `tests/test_tk155_store_expand.py::test_expand_userset_star_marker`; M8 then RED
  ("1 failed, 13 passed"), recorded as S6 in the module docstring. Nits fixed: the
  `ExpandResult` docstring now states that its markers are `(type, predicate)` pairs while
  `LookupResult.markers` are `(type, predicate, 'any')` triples (NOT aligned; an API choice
  left for the 0.1.0 cut), and "its own members are listed too" was reworded; the duplicated
  `StaleRead` raise became `Store._require_evaluator_at`, used by `Store.check` and
  `Store.expand` (helper sabotage RED, "4 failed, 83 passed"). Still NOT covered: the `ineg`
  term of `excluded_keys` (mutation M1 stays green; no reachable state found; declared in the
  module docstring). Declined: the `SetEngine.expand` docstring pointer, deferred to `TK151`
  (engine.py's anchored content pin, D3). Module after fix: "14 passed".

## 1. Scout (2026-10-19)

Provenance labels: **READ** = read first-hand in the tree today; **REASONED** = inferred
from what was read; **UNVERIFIED** = not checked.

- **READ** `src/zanzibar/setengine/engine.py::SetEngine.expand` -- signature
  `expand(self, relation, o_type, o_name, memo=None) -> MemberSet`. Returns interner ids
  (instance-local, recycled) in `pos` / `neg`, `(type, predicate)` shapes in `stars`, and
  (since TK144) uninterned `(type, name, predicate)` keys in `ipos` / `ineg`. Never interns
  on read. Ends with `_self_relation_corrected(...)`.
- **READ** `src/zanzibar/setengine/memberset.py::MemberSet` -- extensional meaning
  `ext = pos | (UNION pop(shape) for shape in stars) - neg`, "pos wins over neg". After
  renormalisation `pos = E - starpop`, so **`pos` omits a subject that a star covers**: a
  reader that takes `pos` alone as "the members" under-reports (the A26 addition).
  `contains_key` reads the key channel the same way.
- **READ** `src/zanzibar/setengine/engine.py::SetEngine.lookup_reverse` -- already renders
  `expand` as `SetLookupResult` (`node_ids = pos`, `markers = stars`,
  `excluded_node_ids = neg`, `implicit_keys = ipos`, `implicit_excluded_keys = ineg`) and
  states `pos` and `neg` are disjoint by construction (`memberset._normalize`).
- **READ** `src/zanzibar/store/_store.py::Store.check` -- the freshness ladder: index if
  `_fresh_enough(at_least)`, re-read the cursor once, then the set engine. On the set-engine
  rung: untokened (stalled index) -> `self.source.catch_up_evaluator()` then serve; tokened ->
  catch up if `evaluator_watermark < at_least`, still behind -> `StaleRead` with
  `token_diagnosis`. `validate_token(at_least)` first.
- **READ** `src/zanzibar/store/source.py::TupleSource.check` -- the same tokened rung with no
  index; `TupleSource.engine` is the read-only evaluator.
- **READ** `src/zanzibar/store/_store.py::Store.lookup_reverse` -- call forms via
  `schema/tuplestr.py::lookup_reverse_args` (`relation, "type:name"` or
  `relation, object_type, object_name`).
- **READ** `formal/CORRESPONDENCE.md` anchors `setengine/engine.py::SetEngine.expand` and its
  nested closures (A26 row: rows ~261-264, 284-286 as of 2026-10-14). This change does not
  touch `engine.py` at all, so no anchor or `claim_rot` content pin moves. **REASONED.**
- **READ** public-surface pins: `tests/test_tk123_top_level.py::_EXPECTED_ALL` (exact set
  per subpackage `__all__`) and `zanzibar/__init__.py::_LAZY` (top-level lazy names;
  `LookupResult` is there, the precedent for a result type). ASCII docstrings:
  `tests/test_tk153_ascii_public_text.py`. No internal refs in public docstrings:
  `tests/test_tk123_no_internal_refs.py`.
- **READ** the oracle-gate style: `tests/test_lookup_oracle.py::_check_set_expand` (S1/S2)
  composes `tests/oracle.py::Oracle.check` over `_subject_candidates` (schema-derived shapes x
  {<=2 names, ghost, `*`}).

## 2. Decisions (REASONED; recorded on the row)

- **D1 result type.** New frozen dataclass `ExpandResult` in `store/_store.py`:
  `keys` (concrete members, `(type, name, predicate)`, `"..."` for a bare subject),
  `markers` (`(type, predicate)` shapes: every subject of the shape is a member) and
  `excluded_keys` (subjects a marker covers that are NOT members). Membership
  `key in res` = `key in keys or ((t, p) in markers and key not in excluded_keys)`.
  Names follow `LookupResult` / `Store.result_keys` / `Store.excluded_keys`, so a reader of
  `lookup_reverse` reads `expand` the same way. Keys only, never ids: the translation runs
  inside the call, so no `StaleLookupIds` window exists. Exported from `zanzibar.store` and
  the top level (the `LookupResult` precedent).
- **D2 freshness.** `Store.expand` is served by the set engine only (Expand has no graph
  index form; the index's `lookup_reverse` is the enumeration surface). It always runs
  `TupleSource.catch_up_evaluator()` first (O(delta); one empty log query when nothing is
  new), then, with `at_least`, raises `StaleRead` if the evaluator is still behind -- exactly
  `Store.check`'s set-engine rung. Untokened `expand` therefore reflects every write visible
  in this session's snapshot, including other instances' (stronger than an untokened
  index read, and cheap against the cost of an expand). It is never affected by a stalled
  index.
- **D3 do not touch `SetEngine.expand`.** Delegation only; the A26 `memo -> _memo` rename is
  NOT done here (it would move the anchored `def` line's content pin for no user gain).
- **D4 pinning.** Brute force against the independent oracle over the candidate grid on
  both `SetOps`, plus a cross-backend tie: `Store.expand` coverage == `Store.lookup_reverse`
  coverage (graph index) on every candidate subject.

## 3. Landing log

### 2026-10-19 -- agent TK155/implement (first-hand RUN unless marked)

- **LANDED** `src/zanzibar/store/_store.py::ExpandResult` (frozen dataclass, `covers` /
  `__contains__`) and `src/zanzibar/store/_store.py::Store.expand` (D1, D2). Exports:
  `src/zanzibar/store/__init__.py::__all__`, `src/zanzibar/__init__.py::_LAZY` (+ the
  `TYPE_CHECKING` import). Surface pin updated deliberately, one name added:
  `tests/test_tk123_top_level.py::_EXPECTED_ALL['zanzibar.store']`. `engine.py` untouched
  (D3). CHANGELOG `[Unreleased]` / Added entry; version stays 0.0.5.
- **PROBE** (smoke, `.scratch/tk155-157/TK155/probes/smoke.py`): under
  `viewer: [user, user:*, group#member] but not banned` with `user:*`, mallory banned and
  `group:eng#member` granted (bob a member), `expand` gives `keys = {group:eng#member,
  doc:d1#viewer}`, `markers = {(user, ...)}`, `excluded_keys = {user:mallory}` -- bob is
  NOT in `keys` (the A26 pos-omits-star reading, first-hand), and `covers` answers True.
- **TESTS** `tests/test_tk155_store_expand.py`, 13 collected: oracle gates (E1/E2) +
  graph `lookup_reverse` tie (E3) on `boolean_wildcards.fga` seeds {0, 4} and
  `wildcards.fga` seeds {0, 1}, each under both `SetOps`; reach tripwires (measured
  2026-10-19, PySets: boolean seed 4 excluded-states 3 / star-omitted 16; wildcards seed 0
  -> 5, seed 1 -> 15 star-omitted; every walk graph-joined, 12-14 accepted writes);
  freshness (another instance, `at_least`, bad tokens, `sync=False` lag); call forms;
  a permanent checker control. `13 passed`.
- **SABOTAGE** S1-S5 + E3-alone, all RED; literal lines in the test module docstring
  (the record; `.scratch/` outputs are gitignored).
- **RUN** targeted: TK155 + top-level / ASCII / no-internal-refs / release-metadata /
  rename / call-forms / TK154 -> `94 passed`; `tests/test_connectedstore*.py`,
  `test_tk12*`, `test_tk14*`, `test_tk15*`, `test_tk123*`, refused-shape comments ->
  `900 passed`. Full gate NOT run (orchestrator). **UNVERIFIED**: `verify.sh lean` (no Lean
  or anchored symbol touched, so expected green; the FINAL_REVIEW generated counts block
  will need `doc_counts --generate` for the new tests).
- **NOT DONE (D3)**: the A26 side-note `memo -> _memo` on `SetEngine.expand`.
