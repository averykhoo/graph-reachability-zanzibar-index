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
moved: 2026-10-12
updated: 2026-10-12
closed: 2026-10-12
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

### 2026-10-12

LANDED (2026-10-12): `src/zanzibar/connectedstore/schema_io.py::ensure_schema` now calls the new `_same_schema`, which accepts identical text, otherwise `parse_schema_ast(stored) == parse_schema_ast(passed)`. Shapes are still compared exactly, and the persisted text is never rewritten. FIRST-HAND READ: `SchemaAST` is a dict keyed by (type, relation), so dict equality ignores the order of type blocks and define lines. Operand order inside `or` and `[...]` restriction order are tuples, so they are still refused. That refusal is pinned as conservative, not widened (a refusal on reopen is the safe side of write-once). Both backends compile only from (AST, shapes), so an equal AST is the same schema. A passed text that does not parse raises the parser ValueError.
PINS: `tests/test_tk136_schema_reopen_semantic.py`, 9 accepted variants (identical, trailing/no final newline, CRLF, indent, comment, model header, type order, define order) and 6 refused (changed/added/removed/renamed relation, or-operand order, restriction order), plus shapes and unparseable-text cases. SABOTAGE (literal output in the module docstring): byte compare restored -> 9 failed, 8 passed; always-equal -> 7 failed, 10 passed.
SMOKE: `scripts/installed_smoke.py` reopens store x with QUICK in CRLF plus a trailing CRLF. With `--allow-checkout`: 67 passed, 0 failed. With the byte compare restored: 66 passed, 1 FAIL (TK136 ...SchemaMismatch).
CHANGELOG: entry under [Unreleased]. NEXT: release as 0.0.4 ONLY on the user's word (bump `__version__` + CHANGELOG heading, tag v0.0.4, babysit CI, install trial).
