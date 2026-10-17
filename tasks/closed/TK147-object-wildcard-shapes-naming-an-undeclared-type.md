---
id: TK147
title: object_wildcard_shapes naming an undeclared type or relation is silently accepted (TK137 C7)
brief: a typo in owc shapes is a silent no-op (fails closed); refuse it with a REFUSED SHAPE block
pri: NOW
size: S
deps: []
related: [TK137]
parent:
labels: []
source: docs/tk137-dsl-openfga-refusals-2026-10-14.md
source_hash:
created: 2026-10-14
moved: 2026-10-17
updated: 2026-10-17
closed: 2026-10-17
---

Sibling of TK137 (challenge C7, `docs/tk137-dsl-openfga-refusals-2026-10-14.md`), deliberately kept out of TK137's DSL scope.

`object_wildcard_shapes` naming an undeclared type or relation is silently ACCEPTED. Challenge PROBE X9, 2026-10-14: `parse_openfga_schema(..., object_wildcard_shapes={('nosuch','viewer')})` and `{('doc','nosuchrel')}` both accept. REASONED: it fails closed (the shape is a no-op, no access is granted), so it is not a grant like TK137's S8 (undeclared restriction type), but it is the same typo class: the caller believes an object wildcard is enabled and it is not.

Proposed (REASONED): refuse at construction, in every path that accepts `object_wildcard_shapes` (`parse_openfga_schema`, `SetEngine`, and wherever the store/JSON front end passes it through), with a REFUSED SHAPE / WHY / INSTEAD block per the refused-shape rule; mirror in the oracle if the oracle accepts the same argument, so the parity tests stay two-sided.

Done when: both an undeclared type and an undeclared relation are refused with a message naming the shape, pinned by tests that go red when the check is deleted.

## Traps

- Persisted stores: if any persisted record carries owc shapes, a new refusal may stop an old store reopening (the same question as TK137 R1); check before landing.

## Read first

- `docs/tk137-dsl-openfga-refusals-2026-10-14.md` (Corrections, C7).
- `src/zanzibar/schema/parser.py`.

## Log

### 2026-10-16

USER 2026-10-16 (in chat): bumped LATER -> NEXT; in scope for 0.1.0.

### 2026-10-17

2026-10-17 (TK147 workflow agent). LANDED, uncommitted; row stays OPEN until the gate stage runs. Map: `docs/tk147-owc-shape-refusal-2026-10-17.md` (ACTIVE-PLAN).

TRAP ANSWERED (READ of `store/schema_io.py::save_schema`): yes, a store saved by 0.0.5 CAN carry an undeclared-type or undeclared-relation owc shape (save_schema compiled it and wrote the JSON). A compiled-leaf name could not be saved, because the graph compile refused it.

DECISION (agent, against "graph == set engine, oracle referees"; recorded per CLAUDE.md "Who decides"): refuse it on reopen as a VERSION BREAK, the same way TK137 handled R1/C10, with the one type TK153 F17 settled on. The check raises `ShapeNoLongerAccepted`, and every persisted path converts it to `PersistedSchemaRefused`, whatever the caller passes. That includes the CORRECTED shapes, which used to raise SchemaMismatch: the persisted record is now validated first in `schema_io.py::_verify_same_schema` and `engine.py::_assert_schema_matches_record`. Why: a lenient reopen mode doubles the parity surface (R1), and it would buy nothing here. PROBE `probe_noop.py` shows the shape changed no admission and no answer, so the rewrite "drop the entry" preserves meaning exactly. `ShapeNoLongerAccepted` gains `accepted_through`/`refused_since` (defaults 0.0.4/0.0.5, unchanged for TK137). TK147 passes 0.0.5/0.1.0, so the message says "saved by zanzibar-index 0.0.5 or earlier ... see the 0.1.0 changelog".

DECISION 2: a compiled-leaf name `('doc','view.0')` counts as an undeclared relation and is refused on BOTH backends. Before, it was graph-only, and the set engine ran with no graph partner. TK116 witness `owc-names-a-leaf` moved to UNREACHABLE. DECISION 3: a non-pair entry is refused too. A 2-char string used to unpack silently.

WHAT LANDED: one check, `src/zanzibar/schema/compiler.py::_validate_object_wildcard_shapes`, with 3 REFUSED SHAPE / WHY / INSTEAD blocks. It is called from `derive_schema_info` (new kw-only `declared_types=`, which `parse_openfga_schema` passes) and from `SetEngine.__init__`, which covers the `ruleset=` path. Other changes: `errors.py`, `engine.py` (`_record_shapes`, `_refuse_record_shapes`), `schema_io.py`. No oracle twin is needed: `tests/oracle.py::Oracle` takes no shapes, and p23 is text-only and still green. There is no JSON front-end path: `parse_openfga_json` takes no shapes. Tests: `tests/test_tk147_owc_shape_refusal.py`, 78 tests covering every path, undeclared type and undeclared relation, 13 persisted openers x 3 shapes, plus controls. Floors ratcheted in `tests/test_refused_shape_comments.py` to 53/43. The `derive_schema_info` anchor pin was regenerated after re-reading CORRESPONDENCE rows 362,363,396-398,414,1120; all are still true. CHANGELOG [Unreleased] has a summary bullet and a Changed entry.

SABOTAGE: SB1-SB10 all RED, literal tails in the test docstring and map sec 4. Example: the whole check deleted gives `rc=1 | 74 failed, 4 passed`.

GREEN (targeted, NOT the gate): 384 + 720 + 463 passed. The only reds were 5 stale-module TK116 failures from a run that collected the module before the witness edit; the re-run is green.

REMAINS: the full gate. Regenerate the FINAL_REVIEW counts block (+78 tests, -4 TK116) and possibly ratchet MIN_TESTS_ALL. Then commit and close.

2026-10-17 (TK147 review-fix agent). Five review findings, verified first-hand, all FIXED, uncommitted. Detail: dated Correction at the top of `docs/tk147-owc-shape-refusal-2026-10-17.md`.

(1) A hand-built SchemaInfo skipped the check: `compile_ruleset(ast, SchemaInfo(object_wildcard_shapes=BAD))` was accepted. FIX: `src/zanzibar/schema/compiler.py::compile_ruleset` now validates its input shapes first, before the closure. DECISION (agent, against "graph == set engine, oracle referees"): `SetEngine(ruleset=)` does NOT re-validate `ruleset.schema_info`. That is the CLOSED set, which the compiler outputs, and READ of `_reject_object_wildcard_scope` shows the closure can reach leaf names. Validating it would refuse a legal store and buy no parity: an untouched hand-built RuleSet is below the public pipeline. Still unchecked, and documented in the check's docstring, the engine comment, the test module and spec-deviations: a hand-built RuleSet, and `WildcardIndex(idx, schema_info)`, which has no AST.

(2) `declared_types` was unpinned. New BAD case `unrestricted-relationless-type` (`type team`), also in PERSISTABLE. SB11 (declared_types dropped) gives `rc=1 | 19 failed, 86 passed`, and SB12 (compile_ruleset call deleted) gives `rc=1 | 7 failed, 98 passed`. Baseline is `rc=0 | 105 passed`.

(3) CHANGELOG now says a compiled-leaf shape raised UnsupportedByGraphIndex at 0.0.5 (PROBE against HEAD 4438bf9) and now raises ShapeNoLongerAccepted. It also lists derive_schema_info and compile_ruleset as raising, and Added has `derive_schema_info(..., declared_types=)`.

(4) Added `docs/spec-deviations.md` entry `## 2026-10-17` (TK147).

(5) WITHDRAWN: the earlier "384 + 720 + 463 passed" line. No log of the 14-module run survives, and the map doc said 444, so neither number holds. Re-measured on 2026-10-17 (targeted, NOT the gate): 19 files, `611 passed`, rc=0.

Content pin: compile_ruleset re-read at CORRESPONDENCE rows 364,375,1293,1363,1632,2144. All still hold. Regenerated `509 anchors (1 changed)`, and `--check` gives rc=0.

REMAINS (unchanged): the full gate, then regenerate the FINAL_REVIEW counts. The test module now has 105 tests, and TK116 lost 4. Then commit and close.

Review-fix addendum: broad run (targeted, NOT the gate) of the 54 tests/ + formal/conformance modules that mention object_wildcard_shapes, compile_ruleset or SchemaInfo( gave 1810 passed in 1570.11s, rc=0. TK116 was re-run alone after its note edit: 37 passed. task.py lint, anchor_check, claim_rot --check and handoff_lint: all rc=0. NEXT ACTION: the full gate, then FINAL_REVIEW counts, then commit + close.

2026-10-17 (TK147 gate agent). CLOSED: done-criteria met. An undeclared type AND an undeclared relation in object_wildcard_shapes are refused with a message naming the shape, on every construction path (parse_openfga_schema via derive_schema_info(declared_types=), compile_ruleset, SetEngine.__init__), and on reopen of a persisted store as a version break (ShapeNoLongerAccepted -> PersistedSchemaRefused). One check: src/zanzibar/schema/compiler.py::_validate_object_wildcard_shapes, 3 REFUSED SHAPE / WHY / INSTEAD blocks; no oracle twin needed (tests/oracle.py::Oracle takes no shapes). Map: docs/tk147-owc-shape-refusal-2026-10-17.md (FROZEN on close). Tests: tests/test_tk147_owc_shape_refusal.py (105); TK116 witness owc-names-a-leaf moved to UNREACHABLE; refused-shape floors ratcheted. Sabotage SB1-SB12 all RED (e.g. check deleted -> rc=1 | 74 failed, 4 passed; declared_types dropped -> rc=1 | 19 failed, 86 passed; compile_ruleset call deleted -> rc=1 | 7 failed, 98 passed), literal tails in the test docstring and map sec 4. FINAL_REVIEW counts regenerated by doc_counts --generate; full phased gate run before commit (verdicts in the commit body).
