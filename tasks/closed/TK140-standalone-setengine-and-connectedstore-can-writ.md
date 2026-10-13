---
id: TK140
title: Standalone SetEngine and ConnectedStore can write one store id (fail-open remove; adopted store)
brief: 0.0.4 trial BROKEN-2/3: standalone SetEngine and ConnectedStore can share a store id; fail-open, InvariantViolation
pri: NEXT
size: M
deps: []
related: []
parent:
labels: []
source: docs/pypi-trial-0.0.4-2026-10-13.md
source_hash:
created: 2026-10-13c
moved: 2026-10-13d
updated: 2026-10-13d
closed: 2026-10-13d
---

BROKEN in the 0.0.4 install trial, re-run first-hand: `docs/pypi-trial-0.0.4-2026-10-13.md`
(BROKEN-2 = p12, BROKEN-3 = p09, both repros inline there).

Nothing ties a store id to one write path:
1. A standalone `SetEngine(s, id, schema)` on a store a `ConnectedStore` owns starts with
   `log_governed=False` (only `TupleSource.__init__` sets it), so its unlogged
   add/remove is accepted. After an unlogged remove, `ConnectedStore.check` stays True
   (fail-OPEN) and `ConnectedStore.remove_tuple` refuses with `AdmissionRejected
   non-existent tuple`, so the grant cannot be revoked through the store.
2. `ConnectedStore(s, id, schema=...)` silently adopts a store id that a standalone
   `SetEngine` already wrote `RelationTuple` rows to: index empty, `check` False, and
   `remove_tuple` raises `InvariantViolation` ("corruption").

Fix direction (to decide): `SetEngine.__init__` refuses (or becomes log-governed) when a
`SchemaRecord` / `TupleLog` exists for the store id; `ConnectedStore` refuses to bootstrap
a store id that has `RelationTuple` rows but no log, and names `build_index` instead.
Both refusals need the `# REFUSED SHAPE` style WHY / INSTEAD and a PostgreSQL leg run
(multi-instance state).

## Read first

- `src/zanzibar/connectedstore/source.py::TupleSource.__init__` (where `log_governed` is set).
- `src/zanzibar/setengine/engine.py::SetEngine.__init__`.
- `src/zanzibar/connectedstore/schema_io.py::ensure_schema`.

## Log

### 2026-10-13d

Decision (lead, REASONED; no Agent/fable tool available to this lead): (1) a SetEngine on a store id with a SchemaRecord becomes log_governed (auto-govern, not refuse: reads stay legal), probed at construction and once per transaction before a standalone write; table named by string + has_table guard so setengine keeps importing nothing from connectedstore. (2) ConnectedStore refuses to create its IndexCursor over RelationTuple rows the log does not account for (count vs ADD-REMOVE), rolls back, raises UnloggedTuplesPresent naming save_schema + build_index. Residual: concurrent write skew under READ COMMITTED, documented. Plan: docs/tk140-one-write-path-per-store-2026-10-13.md

Fixed. Doc: docs/tk140-one-write-path-per-store-2026-10-13.md (map, decision, runs). LANDED: SetEngine latches log_governed when the store id has a SchemaRecord (probe at construction + once per transaction before a standalone write; engine.py store_has_schema_record / SetEngine._probe_log_governance / _reject_unlogged_write); ConnectedStore refuses a first open over RelationTuple rows the log does not account for (store.py _reject_unlogged_adoption, new UnloggedTuplesPresent, rolls back, names save_schema + build_index; recipe verified). Pins: tests/test_tk140_one_write_path.py (12, p12 + p09 positive pins, runs on PG via shared_engine); sabotage S1-S10 all red, literal output in its docstring. Two tests adapted (they wrote unlogged on a SchemaRecord store): test_connectedstore_source replay, test_connectedstore_schema self-describing. PG leg: 81 passed 3 pre-existing skips; server stopped. RED but not TK140: claim-rot pin for SetEngine.lookup_reverse (TK139 body change) and task.py lint 0 NOW rows. verify.sh NOT run. Residual (documented): concurrent standalone write vs uncommitted bootstrap under READ COMMITTED. Next: gate agent runs verify.sh.

Review fixes (fix lead, 2026-10-13d). Doc: docs/tk140-one-write-path-per-store-2026-10-13.md, dated correction at the top. LANDED: (1) the adoption check now reads its three counts in ONE statement, store.py::_adoption_counts. The three separate COUNTs could be split on PG READ COMMITTED by a LOGGED write: reviewer RUN gave a spurious UnloggedTuplesPresent on a fully-logged store. Pin test_the_adoption_counts_are_one_statement; sabotage S12 (three statements) gave 1 failed, 12 passed. PG stress, 1000 rounds each: old form 1 spurious refusal, new form 0. tk139+tk140 modules on PG: 19 passed; pg_local stopped afterwards. (2) test_a_reopened_store_is_never_reaudited now counts _adoption_counts calls; sabotage S11 (has_cursor short-circuit off) gave 2 failed (was 1, incidental). (3) The sec 4 non-TK140 reds are resolved (claim-rot regenerated; lint clean with TK142 at NOW). Also: doc_counts --generate ratcheted MIN_TESTS_ALL 2377->2401. RED: none targeted. Next: the full gate.
