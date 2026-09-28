---
id: TK115
title: JSON front-end fidelity: openfga_json_to_dsl can render a different schema than the JSON declared
brief: openfga_json_to_dsl pastes names unescaped; refuse on round-trip mismatch, dup keys, bad wildcard
pri: LATER
size: M
deps: []
related: []
parent:
labels: []
source: docs/p10-scope-audit-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-09-27d
updated: 2026-09-27d
closed:
---

Filed from the P10 re-run (2026-09-27d). Full witness, provenance and reconciliation: [`docs/p10-scope-audit-2026-09-27.md`](../docs/p10-scope-audit-2026-09-27.md) §5 H5. The section is copied below as it stood when filed; the doc is the body of record.


**Witness** (*verify* `PROBED`, independent `vprobe.py`, 2026-09-27):

```
V1 relation name 'x: [user]\n    define secret' (computedUserset of owner)
   rendered DSL: define owner: [user] / define x: [user] / define secret: owner
   ROUND-TRIP equal: False
   add user:alice x doc:d1: OK -> 1 ; check alice x d1: OK -> True
V2 {"type":"user","wildcard":false} -> define viewer: [user:*]
   add user:alice ... RAISES AdmissionRejected ; add user:* ... OK -> 1 ; check ghost viewer d1: OK -> True
V3 JSON string with duplicate "viewer" key: accepted, last value wins (DSL twin: duplicate relation definition)
V4 type name 'doc\ntype folder2' re-parses with keys [('folder2','viewer')]
V5 control (well-formed model): ROUND-TRIP equal: True
```

Sites (`READ`, verify): `zanzibar_utils_v1.py::parse_openfga_json` checks no whitespace,
newline or `:` in declared names, and calls `json.loads` with no `object_pairs_hook`.
`::_json_restrictions` has `wildcard = 'wildcard' in e and e['wildcard'] is not None`.
`::unparse_schema_ast` writes names raw. `::openfga_json_to_dsl` never re-parses its own
output. The oracle has no JSON front end.

**Proposed row** — *"JSON front-end fidelity: `openfga_json_to_dsl` can render a different
schema than the JSON declared"*, **LATER**, size S-M.
Brief: the JSON path admits declared names containing a newline, `:` or whitespace, a
duplicate JSON key (last wins), and `"wildcard": false` (which widens to `[T:*]`). The
rendered DSL then declares different relations or types, and `ConnectedStore` admits writes
against a relation the JSON never declared (witness above). The front end's own header
promises unsupported input is "rejected loudly, never skipped". Fix, strongest first:
(1) refuse unless `parse_schema_ast(unparse_schema_ast(ast)) == ast`, which closes the class;
(2) refuse non-DSL-safe declared names, reusing P23's contract once it is decided;
(3) refuse duplicate keys via `object_pairs_hook`;
(4) require `wildcard` to be a JSON object.
Each refusal lives in a `_validate_*` / `_reject_*` function with REFUSED SHAPE / WHY /
INSTEAD, and raises `tests/test_refused_shape_comments.py`'s `MIN_HEADERS`. Pin V1–V4 in
`tests/test_openfga_json.py`, sabotaged. This is not a graph-vs-set divergence, because both
read the rendered DSL. Operator nesting is fine: *audit* measured `checked 32 queries,
mismatches 0` (2026-09-27).

## Log
