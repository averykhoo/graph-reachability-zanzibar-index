---
id: TK137
title: DSL parsers silently accept shapes OpenFGA refuses (schema X.Y header, [a] or [b], or+but not mix)
brief: both parsers accept schema 1.2 headers, [a] or [b], unparenthesised or+but not; OpenFGA refuses
pri: NEXT
size: S
deps: []
related: []
parent:
labels: []
source: docs/openfga-claims-audit-2026-10-13.md
source_hash:
created: 2026-10-13c
moved: 2026-10-14
updated: 2026-10-14
closed: 2026-10-14
---

Found by the 2026-10-13 OpenFGA claims audit; probe and sources in
`docs/openfga-claims-audit-2026-10-13.md` sec 4 item 1 (PROBE, first-hand).

Both checked parsers (`src/zanzibar/schema/parser.py::parse_schema_ast`, oracle twin)
silently accept: any `schema X.Y` header (`1.2`, `9.9`; the JSON front end refuses all but
1.1), no header at all, `define viewer: [user] or [doc]` (two direct blocks), and an
unparenthesised `[user] or a but not b`, read as `([user] or a) but not b`. OpenFGA's
grammar (`OpenFGAParser.g4::relationDefPartials`) refuses the last two.

Decide per shape: refuse (with the REFUSED SHAPE / WHY / INSTEAD block, in BOTH parsers,
`tests/test_p23_parser_refusal_parity.py`), or keep and document as an extension. The
silent header is the sharpest: a `schema 1.2` model that uses 1.2 features would parse
here with different meaning or fail confusingly. Any new refusal is a breaking change for
schemas that parse today, so it wants a CHANGELOG line.

## Read first

- `docs/openfga-claims-audit-2026-10-13.md` (sec 2 fact 2, sec 4 item 1).
- `src/zanzibar/schema/parser.py::parse_schema_ast`; oracle twin `tests/oracle.py::parse_schema_ast`.

## Log

### 2026-10-13c

0.0.4 install trial (docs/pypi-trial-0.0.4-2026-10-13.md, p15/p16, p16 re-run first-hand): (a) a restriction naming an undeclared type, `define viewer: [usr]` with no `type usr`, parses, and both backends then admit a `usr:x` write and check says True; OpenFGA validates restriction types against declared types, and the PyPI README sentence "a write naming an undeclared type ... raises AdmissionRejected" is only true for a typo in the write, not in the schema. (b) DSL conditions and modules are refused, but with generic messages (`invalid subject type in restriction user with c`, `unrecognized schema line: module core`); the JSON path names conditions. Both belong in this row decision.

### 2026-10-13d

Sprint re-rank 2026-10-13d (user-approved in chat): LATER -> NEXT. User-visible OpenFGA-compat gap from the 2026-10-13 claims audit.

### 2026-10-14

Scout + challenge + build, 2026-10-14. Map: docs/tk137-dsl-openfga-refusals-2026-10-14.md (ACTIVE-PLAN; challenge C1-C12 at the top; section 0 is the shape table).

MEASURED (scout PROBE, re-run byte-identical by challenge): both parsers accept and agree on every shape; H2 relations-line junk silently drops a relation; S7 a but not b or c parses as a but not (b or c); S8 [usr] admits a usr:x write; fuzz floor at 6000 trials projected 455 vs floor 450. tests --collect-only 2401 = MIN_TESTS_ALL.
DECIDED (refuse/keep split, section 0): REFUSE H1 (schema version other than 1.1), H2 (extra words on model/schema/relations lines), S7 (but not sharing a level with or/and/but not), S8 (restriction to an undeclared type, incl. [usr#...], checked against the FINAL declared set so forward references stay legal; also in parse_openfga_json BEFORE the round trip). S9 keeps refusing but names the feature. KEEP as documented extensions: H3 no header, H4 define without relations, S5 two direct blocks, S6 direct block not first, S10 names, S11 [group#...]. S8 is a FRESH decision extending ASK-1, not a completion of it (C11).

BUILDER DECISIONS (worktree-wf_9a094007-20b-14 @124069c): (1) unparse_schema_ast emits relationless restriction types FIRST, sorted (C12: every OpenFGA example declares type user first), and renders both but-not operands as units, so no new refusal is reachable from the unparser; (2) a relations line before any type (X1) and a model/schema header after types (X2) are KEPT as documented extensions; (3) trailing comments on model / schema / relations lines are REFUSED as H2 (C5; INSTEAD: comment on its own line), consistent with TK123 finding A33; (4) H1 is STRICTER than OpenFGA, which also accepts schema 1.2; the WHY says only 1.1 is implemented and the version was silently ignored. Sabotage SA1-SA15 + SA-F all red in the new tests/test_tk137_openfga_dsl_refusals.py (44 tests); _FUZZ_TRIALS 6000 -> 12000; MIN_TESTS_ALL 2401 -> 2489. Not run there: lean phase, Lean leg of conformance, PostgreSQL leg.
REVIEW: CHANGES-NEEDED; fixes in progress (2026-10-14). Not merged.

OPEN USER QUESTION R1 (C10, a goal question, so it goes to the user, not decided here): stores persisted under <= 0.0.4 whose schema text has a now-refused shape (H2, S7, S8) cannot reopen (schema_io.py::open_set_engine re-parses with the checked parser) and there is no migration path. Coordinator default pending the user's word: accept the break in the API-break release, with a clear "persisted by <= 0.0.4, refused since TK137: <reason>" message at load/open and a CHANGELOG line.
Sequencing (C8): TK137 steps 1-2 (the unparser) land before or with TK123's A36.
Filed: TK147 (LATER) object_wildcard_shapes naming an undeclared type or relation is accepted (C7, out of DSL scope). Next action: land the review fixes, run the phased gate, raise R1 with the user. Not closed here.

LANDED: commit be62738. Both checked parsers (and parse_openfga_json, before its round trip) now refuse the shapes OpenFGA refuses, each with a REFUSED SHAPE / WHY / INSTEAD block in both parsers: H1 a schema version other than 1.1 (stricter than OpenFGA, which also takes 1.2; only 1.1 is implemented and the version used to be ignored), H2 extra words or a trailing comment on model / schema / relations lines, S7 an unparenthesised but not sharing a level with or / and / but not, S8 a restriction to an undeclared type (checked against the final declared set, so forward references stay legal). S9 still refuses but names the feature. Kept and documented as extensions: H3, H4, S5, S6, S10, S11, X1, X2. unparse_schema_ast emits relationless types first and renders but-not operands as units, so the unparser reaches no new refusal. Sabotage SA1-SA15 + SA-F red in tests/test_tk137_openfga_dsl_refusals.py; _FUZZ_TRIALS 6000 -> 12000. Gate: tests-tile 1-4 in the commit, and lean + conf-tile 1-5 green on the combined round tree (e3581aa message).
User decision R1 (C10), 2026-10-14, verbatim: "i'm willing to bet there are zero users now so backwards compat isn't an issue, but we can always bump a minor version if there's an issue". So the default stands: a store persisted by <= 0.0.4 whose schema uses a now-refused shape does not reopen, and says so legibly (src/zanzibar/connectedstore/schema_io.py::_persisted_schema_parse raises PersistedSchemaRefused, quoting the refusal and the rewrite that keeps the 0.0.4 meaning; pinned by tests/test_tk137_persisted_schema_refused.py). No lenient mode.
Plan doc docs/tk137-dsl-openfga-refusals-2026-10-14.md is FROZEN now (banner added 2026-10-14).
Stays open: TK147 (LATER, object_wildcard_shapes naming an undeclared type or relation is accepted, C7). The user-facing write-up of the refused shapes belongs to the docs rows (TK143 and the Diataxis docs row filed 2026-10-14).
Next action: none on this row. The CHANGELOG line for the break ships with the next release (TK123's).
