---
id: TK115
title: JSON front-end fidelity: openfga_json_to_dsl can render a different schema than the JSON declared
brief: openfga_json_to_dsl pastes names unescaped; refuse on round-trip mismatch, dup keys, bad wildcard
pri: NOW
size: M
deps: []
related: [P23]
parent:
labels: []
source: docs/p10-scope-audit-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-10-04b
updated: 2026-10-04b
closed: 2026-10-04b
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

### 2026-10-03c

PROMOTED LATER -> NEXT (user decision 2026-10-03c: "is 115 a real bug? if so add that, otherwise add 117"). VERDICT: real bug. Reproduced FIRST-HAND 2026-10-03c: `openfga_json_to_dsl` on a `directly_related_user_types` entry `{"type": "user", "wildcard": false}` returns `define viewer: [user:*]` -- a public grant from a value meaning "not a wildcard". Cause, read first-hand: `zanzibar_utils_v1.py::_json_restrictions` sets `wildcard = 'wildcard' in e and e['wildcard'] is not None`. Honest bounds: canonical OpenFGA emits `"wildcard": {}`, never `false`, so the trigger is malformed input; no product module calls the JSON front end (only tests); and it is upstream of all three evaluators, so it is a fail-open, not a backend divergence. Skeptic (AGENT-REPORTED 2026-10-03c, WEAKENED) also found this row's own fix (1), refuse-unless-round-trip-equal, MISSES the `wildcard: false` and duplicate-key cases (both round-trip equal), so the fix is several refusals: dict-only `wildcard`, `object_pairs_hook` duplicate-key refusal, declared-name contract shared with `P23`, then the round-trip check. Map: `docs/promote-next-triage-2026-10-03.md` sec 4.

### 2026-10-03e

P23 (closed 2026-10-03e) gave parse_openfga_json the declared-name contract: zanzibar_utils_v1.py::_validate_declared_name runs on every JSON type and relation name, so V8 (empty name) and V6 (can view) are now refused, pinned by tests/test_p23_parser_refusal_parity.py::test_json_front_end_refuses_the_same_declared_names. Still open here: duplicate keys (last wins), wildcard false widening, and the round-trip check. A newline-or-colon name (H5) is now refused too, since neither is in the charset; it is not separately pinned.

### 2026-10-04b

CLOSED 2026-10-04b. Re-probed first-hand on 8045eef: P23 had closed V1/V4 (newline declared names) but NOT the class. Still accepted: V2/V12/V13 (wildcard false / {"enabled": false} / 0 all rendered [user:*], a public grant), V3/V17 (duplicate JSON keys, last wins; both round-trip EQUAL), and two vectors the row did not list -- V9, a bare restriction type carrying a newline, rendered a second relation (round-trip NOT equal), and V14, a restriction type the DSL parser refuses (us er), was accepted by JSON. LANDED: zanzibar_utils_v1.py::_reject_duplicate_json_keys (object_pairs_hook, any depth, JSON text only), ::_validate_json_wildcard (absent / null / exactly {}), ::_validate_json_round_trip (last step of parse_openfga_json; refuses a rendering that does not parse or parses to a different AST, compared per expression, not per key). Each carries REFUSED SHAPE / WHY / INSTEAD; MIN_HEADERS product 34 -> 37. Pinned in tests/test_openfga_json.py (TK115 block, 15 new test ids). Mutation sweep 11 mutations with an M0 control: M1-M9 RED, M10 (lost ignored) INERT and REASONED unreachable alone. Decision (session's, CLAUDE.md Who decides): the round trip is the class-closer; per-field charset checks on restriction types were rejected as enumerating only the names someone thought of. No oracle change (no JSON front end there). Map (FROZEN): docs/tk115-json-front-end-fidelity-2026-10-04.md.
