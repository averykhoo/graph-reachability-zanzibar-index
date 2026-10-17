---
id: TK153
title: 0.0.5 install-trial ergonomics findings not on the TK123 accept list
brief: 0.0.5 trial: non-ASCII docstrings, DeltaProcessor not exported, refusal class name, 3 exceptions/1 cause
pri: NOW
size: M
deps: []
related: [TK123, TK151]
parent:
labels: [docs]
source: docs/pypi-trial-0.0.5-2026-10-15.md
source_hash:
created: 2026-10-15
moved: 2026-10-17
updated: 2026-10-17
closed: 2026-10-17
---

These are the 0.0.5 install-trial CONFUSING / DOC GAP findings that are NOT already on
`TK123`'s accepted list (the mapping of the rest is on `TK123`, 2026-10-15). All are agent
findings, UNVERIFIED except F3, which the session confirmed first-hand.

- F3: public docstrings carry non-ASCII (`advance_index` has U+00A7 and U+2464), so `help()`
  piped to a redirected Windows stdout raises `UnicodeEncodeError`. Consider an ASCII-only pin
  on public docstrings.
- F8: the `MissingDeltaProcessor` message says pass `DeltaProcessor(widx, ruleset.compiled)`,
  but `DeltaProcessor` is in no `__all__`, and the message doesn't say where it is imported from
  (`zanzibar.graphindex.processor`).
- F9: the TK137 refusal class is publicly named `ShapeRefusedSinceTK137` and is not in
  `__all__`. Its `.instead` attribute is undocumented. `[team#member]` with no `type team`
  reports an undeclared RELATION, not an undeclared type.
- F11: a write to an undeclared relation says "matches no declared type restriction for
  doc#vewer" instead of saying that the relation is not declared.
- F17: one condition (a store persisted with a now-refused shape) raises three exception types,
  depending on the entry point: `PersistedSchemaRefused`, `SchemaMismatch` and
  `ShapeRefusedSinceTK137`.
- F6: `IndexCursor`'s repr is `IndexCursor()`; `save_schema` / `build_index` return values
  print the whole compiled RuleSet.
- F19 (doc, goes to TK151 if not done here): to list USERS from `lookup_reverse`, take the
  user-typed nodes plus markers minus exclusions. Never expand a userset node, because that
  re-includes excluded members.

## Read first

- docs/pypi-trial-0.0.5-2026-10-15.md

## Log

### 2026-10-16

USER 2026-10-16 (in chat): bumped LATER -> NEXT; in scope for 0.1.0. The renames (DeltaProcessor export, ShapeRefusedSinceTK137, the three-exceptions-one-cause F17) belong in the 0.1.0 break.

Two more help()-visible text findings from the TK150 scout (docs/closure-fanout-cost-2026-10-14.md, Correction 2026-10-16 (c), READ 2026-10-16): (1) src/zanzibar/schema/errors.py::ClosureFanoutExceeded docstring says the bug "does not bite at the 100,000 default, which is why no test caught it" -- FALSE (spec-deviations "Corrected 2026-10-03b (TK112)": a grant or ban over a >100,000-member group bites at the default); (2) core.py comment above DEFAULT_MAX_CLOSURE_FANOUT says "44 rows in tests/" -- re-measured 93 (2026-10-16). Check claim_rot pins before editing either.

NEXT -> NOW at the 2026-10-16 write-back (TK154 closed, NOW was empty). Why this row first: its exception-naming items (ShapeRefusedSinceTK137, the three-exceptions-one-cause F17, DeltaProcessor export) are API renames that belong in the 0.1.0 break, and TK154 just added StaleLookupIds / TablesOutdated to the same exception surface, so settle the naming once. User order for the rest of NEXT: TK147, then TK138/TK144 last.

### 2026-10-17

2026-10-17 workflow agent (ultracode). Map: docs/tk153-install-trial-ergonomics-2026-10-17.md (ACTIVE-PLAN; which findings reproduced first-hand, what landed, sabotage, the fan-out re-measure). UNCOMMITTED; the full gate is the next stage's.

VERIFIED first-hand (PROBE vs src at 7f45d5a): F3 yes (18 public docstrings), F8 yes, F9 rename NO (already ShapeNoLongerAccepted via TK123; .instead now documented), F9 [team#member] message yes, F11 partly (TK123 gave the reason, lead still wrong), F17 yes (SetEngine raised SchemaMismatch / ShapeNoLongerAccepted; also a 4th path, SetEngine(s, id) with no schema), F6 yes (committed rows print SchemaRecord(); save_schema printed every Filter), F19 yes on both backends (doc gap, not a divergence).

LANDED: ASCII public docstrings + pin tests/test_tk153_ascii_public_text.py; DeltaProcessor in zanzibar.graphindex.__all__, MissingDeltaProcessor names the import; DECISION F17 = ONE type: PersistedSchemaRefused from every entry point incl. SetEngine, class moved to schema/errors.py, exported from zanzibar.schema (reason on the doc sec 2: one fact about the store, one fix, so one name; not a SchemaMismatch subclass since nothing mismatches when no schema is passed); F9 undeclared-type message (parser + JSON front end, verdict unchanged); F11 lead 'names an undeclared relation' via schema/syntax.py::no_restriction_message on both backends; short reprs for RuleSet / SchemaRecord / IndexCursor; F19 recipe in PYPI_README + Store.lookup_reverse docstring (not sent to TK151); exception-table rows; ClosureFanoutExceeded docstring corrected; DEFAULT_MAX_CLOSURE_FANOUT comment re-measured 2026-10-17 (tests/ max 93, 440 the control; probe tracked at formal/probes/tk153_fanout_probe_plugin_2026_10_17.py); CHANGELOG [Unreleased] entries; claim_rot pin regenerated after re-reading the cited CORRESPONDENCE rows (509/509). Tests: tests/test_tk153_install_trial_ergonomics.py (54) + ascii (3); sabotage SB1-SB9 all RED, recorded in the docstrings.

BUILDS/GREEN (targeted): 1242 passed over 43 related modules; 246 passed final batch; full tests/ probe run 2666 passed, 8 failed = claim_rot only (before the regenerate). RED/OWED: doc_counts --generate for formal/FINAL_REVIEW.md (new tests) not run; full gate not run.

NEXT ACTION: gate (all phases) + doc_counts regenerate, then commit by path and close TK153.

Review-fix pass 2026-10-17 (workflow agent). FIXED: (1) F17 hole: save_schema/ensure_schema with the stored refused text now raise PersistedSchemaRefused (store/schema_io.py::_schema_difference parses the stored text under _persisted_schema_parse before the identical-text return); 8 new ENTRY_POINTS rows, sabotage 8 failed. (2) F6 repr side effect: store/models.py::_row_repr reads under session.no_autoflush; pin test_f6_repr_never_flushes_the_session, sabotage 1 failed. (3) FINAL_REVIEW.md counts regenerated (tests 2737, MIN_TESTS_ALL ratcheted 2671->2737); doc_counts --check rc=0, claim_rot --check rc=0. Record: docs/tk153-install-trial-ergonomics-2026-10-17.md Corrections. NOT run: full gate; not committed. Next action: run every verify.sh phase, then commit by path.

Second review-fix pass (2026-10-17, workflow agent): all three minor findings were real and are fixed. Write-up: docs/tk153-install-trial-ergonomics-2026-10-17.md, Corrections, "second review-fix pass".
LANDED: (1) F11 wording. A declared type with no relations is now reported as "type 'folder' declares no relations", not "not declared in the schema", on SetEngine, RuleSet.apply and Store. It goes through parser.py::_parse_schema_ast_checked -> syntax.py::declared_relations(ast, declared_types), with a new keyword-only compile_ruleset(declared_types=...). (2) The dangling-userset messages in parser.py::_validate_ast_consistency now keep the ':*' (via _render_restriction). (3) The ASCII pin now reads dunders and nested classes, following pydoc's visiblename rule, and has a new instrument test.
DECISION: compile_ruleset gets an additive keyword-only declared_types, rather than SetEngine patching ruleset.declared after compiling. Reason: SetEngine compiles its own RuleSet, and that RuleSet is where the set engine's refusal text comes from. One parameter keeps both backends' text from one source. It changes messages only, never a verdict (RuleSet.declared is compare=False).
BUILDS: 1185 passed (schema / parser-parity / refused-shape / snapshot / TK123 / TK137 / TK153 modules + conformance fragment). Sabotage SB10 (1 failed), SB11 (2 failed) and the pin's old filter (1 failed); the literal output is in the test docstrings. doc_counts: tests 2737 -> 2741, MIN_TESTS_ALL ratcheted, --check rc=0.
RED: nothing known. The full gate was NOT run.
NEXT: the session runs the full phased gate (lean, conf-tile 1-5, tests-tile 1-4), then commits by path.

Landed (map: docs/tk153-install-trial-ergonomics-2026-10-17.md, FROZEN at close). F3 ASCII-only public docstrings, pinned by tests/test_tk153_ascii_public_text.py. F8 DeltaProcessor exported from zanzibar.graphindex and MissingDeltaProcessor names the import. F9 ShapeNoLongerAccepted.instead documented, undeclared-type message fixed in parser + JSON front end. F11 undeclared-relation lead on both backends via schema/syntax.py::no_restriction_message, plus declares-no-relations wording. F17 one type, PersistedSchemaRefused, from every entry point incl. SetEngine and save_schema/ensure_schema. F6 short reprs for RuleSet / SchemaRecord / IndexCursor, read under no_autoflush. F19 lookup_reverse users recipe in PYPI_README + Store.lookup_reverse docstring. ClosureFanoutExceeded docstring corrected, fan-out comment re-measured (probe formal/probes/tk153_fanout_probe_plugin_2026_10_17.py). Tests: tests/test_tk153_install_trial_ergonomics.py + tests/test_tk153_ascii_public_text.py; sabotage SB1-SB11 all RED, literal output in docstrings. Full phased gate run at close (see the commit).
