---
id: TK124
title: an empty schema is accepted and persisted write-once, bricking the store id
brief: ConnectedStore(schema="") persists an empty write-once schema; the store id is then unusable
pri: LATER
size: S
deps: []
related: [TK122]
parent: TK127
labels: [infra]
source: hand
source_hash:
created: 2026-10-07b
moved: 2026-10-08
updated: 2026-10-08
closed: 2026-10-08
---

`ConnectedStore(session, "x", schema="")` is accepted and persisted write-once as an empty
ruleset, after which every write is refused and re-opening with the real schema raises
`SchemaMismatch`. There is no public way to drop a store, so the store id is lost (CONFIRMED
2026-10-07, 0.0.2 install trial). Fix: refuse a schema that declares no types, at parse time,
in BOTH parsers (product and oracle twin), with a `# REFUSED SHAPE` / `# WHY` / `# INSTEAD`
block (`tests/test_refused_shape_comments.py`). Pin the parity in
`tests/test_p23_parser_refusal_parity.py`'s family.

## Traps

- (!) Do NOT also refuse a schema without the `model` / `schema 1.1` header in the same
  change. Many in-repo test schemas may omit it (UNVERIFIED count). Measure first; that is a
  separate call.
- (!) A new refusal in one parser without its twin is red by design (`P23` parity fuzz).

## Read first

- [`docs/pypi-trial-0.0.2-2026-10-07.md`](../docs/pypi-trial-0.0.2-2026-10-07.md) sec 1 B2.
- `CLAUDE.md` sec "Gotchas / invariants" (refused-shape comment rule, parser parity).

## Log

### 2026-10-08

impl-tk124 (2026-10-08, UNCOMMITTED): zero-type schema now refused at parse time. LANDED: src/zanzibar/schema/parser.py::_validate_declares_a_type (end of _parse_schema_ast_unchecked, so checked/unchecked/compile all refuse), twin tests/oracle.py::_validate_declares_a_type, JSON src/zanzibar/schema/json_frontend.py::_validate_json_declares_a_type (type_definitions absent/null/[]); REFUSED SHAPE blocks in all three; MIN_HEADERS 39/17/1, MIN_IN_SCOPE_RAISES 27. Refused: empty, whitespace, comments-only, model/schema header only. NOT refused (decision per row trap + measurement): types with no relations (type user) and no-header schemas. A JSON model whose types all lack relations IS refused, by the pre-existing round trip (its DSL rendering is empty). save_schema parses before adding SchemaRecord, so nothing persists; same store id bootstraps afterwards (pinned sync+async, fresh and same session). Pins: tests/test_tk124_empty_schema.py (52 tests) + 3 refused / 2 accept entries in tests/test_p23_parser_refusal_parity.py (fuzz cannot generate a type-less text). Sabotage: product guard off 32 red, oracle off 17, JSON off 4, all off 53. Census: no pre-existing test in tests/ or formal/conformance parses a zero-type or a relation-less schema. Full tests/: 8 failed, 2042 passed -- all 8 tests/test_claim_rot_gate.py, the anchor pin for tests/oracle.py::parse_schema_ast_unchecked moved; CORRESPONDENCE.md row (encoder) re-read, still true, one sentence added. NEXT: orchestrator runs python formal/conformance/claim_rot.py --generate (expect exactly 1 changed + 1 added), then the gate. conformance: 1087 passed.

TK127 review follow-up (fix-tk127, 2026-10-08): the relationless half is now refused too. Reviewer repro re-run first-hand: ConnectedStore(s, "x", schema="type user") BOOTSTRAPPED then the id was BRICKED (SchemaMismatch). Decision (a): parser.py::_validate_declares_a_type(seen_types, ast) gained a second guard (schema declares no relation), oracle twin likewise, JSON front end json_frontend.py::_validate_json_declares_a_relation (named message, no longer the misleading round-trip one). REFUSED SHAPE blocks added; MIN_HEADERS 41/18/1, MIN_IN_SCOPE_RAISES 29 (measured). P23: type-without-relations moved accept->refused, plus types-with-empty-relations-blocks; new accept control relationless-type-beside-a-relation. Red first: 27 failed, 118 passed; sabotage S1/S2/S3 = 17/8/2 failed (literal in tests/test_tk124_empty_schema.py docstring). unparse.py docstring corrected (empty AST is not a parse output). Claim-rot: oracle parse_schema_ast_unchecked body moved again; orchestrator regenerates. Scratch: .scratch/tk127-2026-10-08/fix-tk127.md

Done 2026-10-08. parser.py::_validate_declares_a_type + oracle twin + json_frontend.py::_validate_json_declares_a_type refuse a schema declaring no type OR no relation (review follow-up: a relationless schema bricked a store the same way), with REFUSED SHAPE blocks; MIN_HEADERS raised; P23 parity pins. Header-less schemas still accepted (row trap). First-hand 2026-10-08: '', header-only and 'type user' refused; same store id then opens with a real schema. Gated with the 2026-10-08 commit (0.0.3). Workflow reports: docs/history/tk127-fixes-2026-10-08.md.
