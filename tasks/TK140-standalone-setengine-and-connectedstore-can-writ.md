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
moved: 2026-10-13c
updated: 2026-10-13c
closed:
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
