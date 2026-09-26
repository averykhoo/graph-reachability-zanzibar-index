# `ASK-1`: schemas must be self-consistent (dangling references and reference cycles are refused)

**FROZEN 2026-09-26, at `ASK-1`'s close — provenance, not a living document.** Status lines
below are as-of-then; live state: `HANDOFF.md` + the session ledger. Corrections are
appended dated at the top, never edited into the body. (Was ACTIVE-PLAN earlier the same
day, `docs/README.md` §3.) Live state is `python scripts/task.py show ASK-1`, never this
file. Every figure below was measured on `2026-09-26` against HEAD `a6e997d` plus this
session's diff.

Provenance labels: **READ** (first-hand, this session), **REASONED**, **MEASURED** (a run
whose output is quoted), **UNVERIFIED**. No subagent was used.

## § 0 The decision (the user's, 2026-09-26)

`ASK-1` asked whether the compiler should refuse a dangling reference, as OpenFGA does. The
user answered: *"I think we can strictly expect schemas to be self consistent."* Asked
separately whether reference cycles should be refused too: *"Okay yes refuse both."*

So both formerly SILENT `GraphAdmission` fields become LOUD:

- `matchDecl`: a dangling reference, e.g. `define viewer: [user] or editor` with no `editor`.
- `ranked`: an untainted cycle of references, e.g. `a: [user] or b`, `b: [user] or a`.

## § 1 What OpenFGA does (READ, `openfga/openfga` `pkg/typesystem/typesystem.go`, main, 2026-09-26)

- `::isUsersetRewriteValid`: a computed ref must be declared on its own type
  (`ErrRelationUndefined`), and so must a TTU tupleset. The tupleset must be DIRECT-only. The
  TTU target must be declared on at least one of the tupleset's directly related types
  (schema 1.1), or on any type (schema 1.0).
- `::validateTypeRestrictions`: every restriction type is declared, and a `[T#P]` restriction
  needs `T#P` declared.
- `::hasCycle` (called from `::validateRelation`): any cycle made only of computedUserset
  edges on one type, walked through union / intersection / difference, is `ErrCycle` ("an
  authorization model cannot contain a cycle"). `this` and tupleToUserset end the walk. This
  applies whether or not the relations have entrypoints.
- SpiceDB (READ, authzed.com/docs/spicedb/modeling/recursion-and-max-depth): recursion goes
  through relations such as `group#member`. Cycles are unsupported and are caught at runtime
  by a 50-hop depth limit. Whether its schema compiler refuses permission cycles is
  **UNVERIFIED**.

**The prior claim was wrong.** `docs/tk104-graphadmission-scope-2026-09-24.md` §3 said
"`ranked` cannot be made LOUD without refusing legitimate recursive schemas". REASONED: every
`ranked` failure is a cycle made only of computed edges, or one that passes through a TTU
edge. A TTU edge needs a tupleset with an incoming rule arm, i.e. a non-direct tupleset,
which Python already refuses for untainted tuplesets (`ttuDirect`, LOUD half). Legitimate
recursion goes through stored tuples, not schema edges:

- nested groups, `member: [user, group#member]`;
- folder hierarchies, `viewer: [user] or viewer from parent`;
- OpenFGA's self-referential boolean flag (READ, openfga.dev/docs/best-practices/modeling-abac):
  `sso_enabled: [organization]`, `can_use_sso: member from sso_enabled`, with the tuple
  `organization:acme#sso_enabled@organization:acme`.

None of these makes a reference edge that closes a cycle. The flag pattern is already a
curated corpus (`SELF_REF:self_flag`).

## § 2 The rules (session's call on scope; `zanzibar_utils_v1.py::_validate_ast_consistency`)

1. A computed ref and a TTU tupleset must be declared on the defining type.
2. A TTU target must be declared on at least one type the tupleset admits. When the tupleset
   admits no type, it must be declared on some type (OpenFGA's schema-1.0 rule).
3. A `[T#P]` restriction (including `T:*#P`) needs `T#P` declared.
4. No cycle of computed / TTU-tupleset references, through any operator. This is wider than
   `ranked`, which only looks at untainted union arms. Same-type cycles through `and` /
   `but not` were already refused at COMPILE time by `_stratify`; now the parse refuses
   them. A derived cycle through a TTU TARGET is still refused only by `_stratify`
   (MEASURED 2026-09-26: `define a: ([user] but not blk) or a from parent` raises
   `CyclicDerivedDependency`).

**Not adopted, and why:**

- **Bare subject types (`[user]` with no `type user`).** A relation-less `type` line leaves
  no trace in a `SchemaAST`, so `unparse_schema_ast` could not round-trip a schema that
  passes. Checking it would mean carrying declared types through the AST. That is not a
  dangling *relation*, and neither proof field depends on it.
- **OpenFGA's "a tupleset must be direct-only" rule.** That is `ttuDirect`, a different
  field (MIXED, with its silent half shadowed by `W4Fragment.computedOrDirect`). It is not a
  dangling reference.

**Where it runs:** both front ends (`parse_schema_ast`, `parse_openfga_json`), and the
oracle's independent twin `tests/oracle.py::_validate_consistency`.

**The unchecked paths, and why they exist:** `zanzibar_utils_v1.py::_parse_schema_ast_unchecked`
and `tests/oracle.py::parse_schema_ast_unchecked`.

- `w4_fragment_report` and `graph_admission_report` promise never to raise, so they read the
  unchecked parse.
- The conformance encoder (`formal/conformance/encode.py::schema_to_json`) is a translator:
  Lean decides admission for itself, so it must be able to receive a refused schema.
- Without the unchecked parse, the Lean differential (J) in `test_conformance_fragment.py`
  would lose every failing input and compare `()` with `()`.

## § 3 Pins

- `test_conformance_fragment.py` (K), `::test_reported_failures_are_refused_by_both_parsers`:
  if the report (== Lean, by (J)) says an input fails `matchDecl` or `ranked`, both parsers
  refuse it. Every curated corpus is accepted. The converse is NOT claimed, because the
  refusal is deliberately wider. `::test_refusal_sweep_sees_both_fields_fail` is the
  anti-vacuity control.
- `test_graphadmission_scope_pin.py`: `matchDecl` and `ranked` are LOUD (LOUD 12 / MIXED 2 /
  SILENT 0), and their four probes now expect `ValueError`.

## § 4 Breakage census (MEASURED 2026-09-26)

**Setup.** `pytest tests/ --continue-on-collection-errors`, with only the refusal and the
oracle twin in place.

**Result.** `57 failed, 1208 passed, 1 error in 1224.19s`. The error was a collection
failure in `tests/test_zanzibar_utils.py`, from the shared fixture
`tests/fga_schemas/tupleset_shapes.fga`. **No curated conformance corpus is refused.** A scan
of all 36 `ALL_CORPORA` against both parsers found none; only the probes built to violate
a field are refused.

Each group, and what was done about it:

| module | n | cause | resolution |
|---|---|---|---|
| `test_generator_coverage.py` | 14 | `genswarm` `ts_undeclared` switch; `ast_features` parsed with the checked parser | witness `undeclared-tupleset-with-derived-target` replaced by `dangling-reference`; `cyclic-derived-dependency` moved to a TTU-target cycle; `ast_features` reads the unchecked parse; the negative control became `test_undeclared_tupleset_is_refused_whatever_its_target` |
| `test_cascade_quiesce_gc.py` | 12 | the TK73 witness schema had dangling `admin` / `editor` | declared as direct relations that no write touches, placed last. Still empty, and the module's own guards (settle pass runs, detects genuine staleness) stay green |
| `test_schema_ast.py` | 8 | grammar tests with one-line fragments (`define x: a and b`) | the helper `_rel` reads the unchecked parse |
| `test_zt_p5_readjudication.py` | 6 | `test_zt_p5_undefined_references_compile_silently_and_read_empty`, which was written for exactly this decision | now `::test_zt_p5_undefined_references_are_refused`, plus `::test_zt_p5_undefined_restriction_type_still_compiles_and_reads_empty` for the one form not refused |
| `test_graph_admission_report.py` | 4 | called the checked parser on violating inputs | reads `_parse_schema_ast_unchecked` |
| `test_blind_audit_regressions.py` | 4 | memo-poisoning repros used schema cycles | oracle repro rebuilt as a DATA cycle and sabotaged (below); the set-engine / ParityEngine schema's graph-refused part is now a TTU-target derived cycle |
| `test_schema_shapes.py` | 3 | `tupleset_shapes.fga`'s `via_undeclared` | arm and its two queries removed; `ttu.ts:undeclared` moved to `EXPECTED_UNREACHED`; `MIN_COOCCURRING_PAIRS` 839 -> 813 (all 26 lost pairs contain `ttu.ts:undeclared`, measured) |
| `test_compile_snapshot.py` | 1 | same fixture | golden regenerated; the diff is exactly one deleted rule (`relation='ghost_parent'`) |
| `test_parity_engine.py` | 1 | 3-way degrade forced by a same-type `but not` cycle | TTU-target derived cycle |
| `test_oracle.py` | 1 | classification test with undeclared `group#member` / `parent` | declared |
| `test_hypothesis.py` | 1 | `match='cycle'` against the new message | message now starts `reference cycle:` |
| `test_w4_fragment_report.py` | 1 | report parsed with the checked parser | report reads the unchecked parse |

**Two findings made along the way:**

- **The set engine refuses a group-membership DATA cycle whenever the graph index can
  compile the schema.** MEASURED: with the old same-type `x2` / `y2` cycle simply removed,
  `AdmissionRejected ... would create a cycle in the userset membership topology`. So a
  test that needs a data cycle on the set engine must keep a graph-refused element in its
  schema. That is why the shared schema carries a TTU-target derived cycle.
- **`CyclicDerivedDependency` is still reachable, only through a TTU TARGET.** Same-type
  derived cycles are now parse refusals. Every test that needed "the graph refuses, the set
  engine accepts" moved to `define a: ([user] but not blk) or a from parent`.

**Oracle memo-poisoning witness, sabotaged 2026-09-26.** The memo branch in
`tests/oracle.py::Oracle.check` (`if my_low >= depth:`) was replaced by `if True:`. Output
of `.scratch`-probe `memo_witness.py`, literal:

    baseline   {'a': True, 'up': True, 'r': True,  'r2': False}
    sabotaged  {'a': True, 'up': True, 'r': False, 'r2': True}

## § 5 Mutation sweep (MEASURED 2026-09-26, `docs/sabotage-procedure.md`)

**Setup.** 16 mutations of `zanzibar_utils_v1.py::_validate_ast_consistency` / `::_iter_refs`
/ the two front-end call sites (M*) and of `tests/oracle.py::_validate_consistency` (O*).
Each is an exact-once replacement, restored in `finally`, and both files byte-compared
against pre-sweep copies afterwards (`RESTORED-OK`).

**Target.** `tests/test_schema_self_consistency.py`, `tests/test_zt_p5_readjudication.py`
and `formal/conformance/test_conformance_fragment.py` under
`-k 'undefined or refuse or refusal or legal or json or chain or unchecked'`.

**Baseline.** `122 passed, 320 deselected`. **Result: 16 of 16 CAUGHT, 0 INERT.** The M0
control is attributed to exactly the test it targets. Literal (failing test names
abbreviated to their last `::` part):

    M0-control: refuse the flag pattern: CAUGHT | 1 failed | test_recursion_through_stored_tuples_stays_legal[self-referential-boolean-flag]
    M1 computed ref not checked: CAUGHT | 6 failed | ...[GA_PROBE:matchDecl/undeclared-computed-ref], test_json_front_end_refuses_a_dangling_reference, test_production_parser_refuses[computed-ref-inside-a-boolean], [computed-ref], test_zt_p5_undefined_references_are_refused[boolean_arm], [computed]
    M2 tupleset not checked: CAUGHT | 3 failed | ...[GA_PROBE:matchDecl/undeclared-tupleset-untainted-target], test_production_parser_refuses[ttu-tupleset], test_zt_p5_..._refused[ttu_tupleset]
    M3 ttu target not checked: CAUGHT | 3 failed | test_production_parser_refuses[ttu-target-declared-nowhere-for-an-untyped-tupleset], [ttu-target-on-no-tupleset-type], test_zt_p5_..._refused[ttu_target]
    M4 untyped tupleset target vacuous: CAUGHT | 1 failed | test_production_parser_refuses[ttu-target-declared-nowhere-for-an-untyped-tupleset]
    M5 userset restriction not checked: CAUGHT | 3 failed | test_production_parser_refuses[userset-restriction], [wildcard-userset-restriction], test_zt_p5_..._refused[userset_relation]
    M6 refs not found under Exclusion: CAUGHT | 2 failed | test_production_parser_refuses[computed-ref-inside-a-boolean], test_zt_p5_..._refused[boolean_arm]
    M7 self-loop ignored: CAUGHT | 4 failed | ...[GA_PROBE:ranked/computed-self-loop], test_production_parser_refuses[computed-self-loop], [cycle-through-a-rewritten-tupleset], test_zt_p5_..._refused[self_computed]
    M8 ttu-tupleset edges not in cycle graph: CAUGHT | 1 failed | test_production_parser_refuses[cycle-through-a-rewritten-tupleset]
    M9 json front end unchecked: CAUGHT | 2 failed | test_json_front_end_refuses_a_cycle, test_json_front_end_refuses_a_dangling_reference
    M10 dsl front end unchecked: CAUGHT | 22 failed
    O1 oracle computed ref not checked: CAUGHT | 5 failed | ...[GA_PROBE:matchDecl/undeclared-computed-ref], test_oracle_parser_refuses[computed-ref-inside-a-boolean], [computed-ref], test_zt_p5_..._refused[boolean_arm], [computed]
    O2 oracle cycle walk off: CAUGHT | 7 failed | ...[GA_PROBE:ranked/computed-self-loop], [GA_PROBE:ranked/computed-two-cycle], test_oracle_parser_refuses[computed-self-loop], [computed-two-cycle], [cycle-through-a-boolean], [cycle-through-a-rewritten-tupleset], ...
    O3 oracle ttu target not checked: CAUGHT | 3 failed | test_oracle_parser_refuses[ttu-target-declared-nowhere-for-an-untyped-tupleset], [ttu-target-on-no-tupleset-type], test_zt_p5_..._refused[ttu_target]
    O4 oracle userset restriction not checked: CAUGHT | 3 failed | test_oracle_parser_refuses[userset-restriction], [wildcard-userset-restriction], test_zt_p5_..._refused[userset_relation]
    O5 oracle tupleset not checked: CAUGHT | 3 failed | ...[GA_PROBE:matchDecl/undeclared-tupleset-untainted-target], test_oracle_parser_refuses[ttu-tupleset], test_zt_p5_..._refused[ttu_tupleset]

**Single-point catches, recorded so nobody deletes the only witness:**

- M4 is caught only by `REFUSED['ttu-target-declared-nowhere-for-an-untyped-tupleset']`.
- M8 is caught only by `REFUSED['cycle-through-a-rewritten-tupleset']`.

Both live in `tests/test_schema_self_consistency.py`.

**Instrument limit.** The sweep's target excludes the slow `tests/test_generator_coverage.py`,
so these attribution lists mean "at least these".
