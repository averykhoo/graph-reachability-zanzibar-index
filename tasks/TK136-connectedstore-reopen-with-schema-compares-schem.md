---
id: TK136
title: ConnectedStore reopen with schema= compares schema text byte-for-byte; whitespace/CRLF refused
brief: BROKEN in the 0.0.3 install trial: reopen with schema= refuses a trailing newline / CRLF; compare semantics, not bytes
pri: NOW
size: S
deps: []
related: [TK127, TK124]
parent:
labels: [infra]
source: docs/pypi-trial-0.0.3-2026-10-08.md
source_hash:
created: 2026-10-08b
moved: 2026-10-08b
updated: 2026-10-08b
closed:
---

`ConnectedStore(session, store_id, schema=...)` on an EXISTING store compares the passed
schema text to the persisted one byte-for-byte
(`src/zanzibar/connectedstore/schema_io.py::ensure_schema`: `row.schema_text != schema_text`,
line 82 on 2026-10-08). The constructor docstring sells "open (or bootstrap)", and the
natural app code passes its schema file every start. So a trailing newline, a CRLF checkout,
an indent change, an added comment or a type reorder makes the app refuse to open its own
store with `SchemaMismatch`. Found BROKEN by the 0.0.3 install trial (probe06), re-run
FIRST-HAND 2026-10-08b against `src/`: identical text accepted; trailing newline, CRLF,
4-space indent and an appended comment each refused.

**Decision (2026-10-08b, delegated per CLAUDE.md "Who decides"; not yet implemented):**
compare SEMANTICS, not bytes: parse both texts and compare the parsed schema (plus
`object_wildcard_shapes`); keep the persisted text as the source of truth, never rewrite it.
A semantically different schema still raises `SchemaMismatch` (write-once is the contract;
only the comparison is too strict). Check whether `SchemaAST` equality is order-independent
across types before relying on it; if not, compare `unparse_schema_ast` canonical forms.

**Done when:** a test pins accepted variants (newline, CRLF, indent, comment, type order)
and a refused one (a changed relation), with a sabotage run recorded; then a smoke check in
`scripts/installed_smoke.py`; per the release rule this ships as 0.0.4 (release on the
user's word only).

## Log
