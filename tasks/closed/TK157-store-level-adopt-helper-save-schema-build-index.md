---
id: TK157
title: Store-level adopt helper (save_schema + build_index in one call)
brief: TK123 SPLIT A25b: returns the named BuildReport
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

SPLIT from `TK123` (review item A25b, `docs/tk123-api-review-2026-10-14.md`, call SPLIT).
Adopting an existing tuple set into a logged store is a multi-step recipe today
(`save_schema` + `build_index` + opening `Store`, the README adoption recipe). Add one
`Store`-level adopt helper that runs it and returns the named `BuildReport`. A feature, hence
not in the TK123 API break; `save_schema` / `build_index` stay public either way.

## Read first

- `docs/tk123-api-review-2026-10-14.md` — row A25 (the SPLIT of the adopt helper, A25b)
- `src/zanzibar/store/build.py::build_index` — the bootstrap step the helper wraps

## Log

### 2026-10-19b

LANDED (uncommitted, workflow agent TK157/implement): classmethod Store.adopt(session, id, *, schema=None, object_wildcard_shapes, bulk, ops, sync, paranoia) -> (store, BuildReport) in src/zanzibar/store/_store.py::Store.adopt. Schema+index commit together (save_schema flushed, build_index commits/rolls back both); assert_read_isolation + refuse_reusable_node_ids run BEFORE the build; IndexExists on an indexed id; DBAPIError -> TablesNotCreated. UnloggedTuplesPresent message now names Store.adopt first. Plan + decisions D1-D7 + sabotage table: docs/tk157-adopt-helper-2026-10-19.md. Tests: tests/test_tk157_store_adopt.py (14 passed); sabotage S1 (commit after save_schema), S2 (drop TablesOutdated pre-check), S3 (drop isolation pre-check) each red with E assert (True, ...) == (False, False), restored green. CHANGELOG [Unreleased]/Added and PYPI_README adoption bullet updated. No __all__ change (Store already exported). PG leg: reasoned skip (D7, no new SQL/lock/isolation code; tests use shared_engine so a DSN run covers them). RED: nothing known; verify.sh not run. NEXT: orchestrator runs the gate phases, commits by path, then closes TK157.

Review fix (agent TK157/fix). LANDED: Store.adopt now checks paranoia (resolve_paranoia_level, env var included) and ops (isinstance SetOps -> TypeError) BEFORE anything is built; reviewers showed a bad paranoia/ops committed schema+index and a retry hit IndexExists (reproduced first-hand). IndexExists gained optional hint + detail attr; adopt re-raises it with "open it with Store(session, id)". Docstring/CHANGELOG/plan doc corrected (shapes used only with schema; bulk ValueError vs AdmissionRejected split for an undeclared doc:* row documented, not changed: pre-existing build_index behaviour). Tests: +paranoia/ops/env refusal pins (state read), object_wildcard_shapes pin, ops=PySets pass-through, SchemaMismatch in_transaction, tautological top-level test replaced. 19 passed; 24 related modules 659 passed rc=0. Sabotage S4 4 failed/15 passed, S5 1 failed/18 passed, restored. Doc: docs/tk157-adopt-helper-2026-10-19.md correction 2026-10-19. RED: none. Next: orchestrator gate + commit.

LANDED (uncommitted at close; the orchestrator gates and commits by path): classmethod `Store.adopt(session, store_id, *, schema=None, object_wildcard_shapes=frozenset(), bulk=True, ops, sync=True, paranoia=None)` in `src/zanzibar/store/_store.py`, returning `(store, BuildReport)` (D1). save_schema only flushes, so build_index's one commit lands schema + index together and a refusal commits nothing. Checks BEFORE building: assert_read_isolation, refuse_reusable_node_ids, resolve_paranoia_level (incl. ZANZIBAR_PARANOIA), isinstance(ops, SetOps). TablesNotCreated / StoreNotFound / SchemaMismatch / IndexExists (re-raised with an adopt-specific hint via the new optional `hint` on `src/zanzibar/store/build.py::IndexExists`). UnloggedTuplesPresent names Store.adopt first. CHANGELOG + PYPI_README updated.
DOC: docs/tk157-adopt-helper-2026-10-19.md (FROZEN at this close; dated review-fix correction at the top).
TESTS: tests/test_tk157_store_adopt.py "19 passed"; 24 build_index/IndexExists modules "659 passed".
SABOTAGE (all RED): S1 commit after save_schema, S2 no node-id check, S3 no isolation check (each "1 failed, 13 passed"), S4 early paranoia/ops checks removed ("4 failed, 15 passed"), S5 shapes dropped ("1 failed, 18 passed").
DECLINED: bulk=True ValueError vs bulk=False AdmissionRejected for an undeclared doc:* stored row is pre-existing build_index behaviour; documented in the adopt docstring, not unified. PG leg: reasoned skip (no new SQL/locks/isolation logic).
