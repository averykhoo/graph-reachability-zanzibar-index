# TK147 -- refuse `object_wildcard_shapes` naming an undeclared type or relation (2026-10-17)

> **FROZEN 2026-10-17, at `TK147`'s close -- provenance, not a living document.** Status
> lines below are as-of-then and several may now be false; live state: `HANDOFF.md` + the
> session ledger, and `python scripts/task.py show TK147`. Corrections are appended dated at
> the top, never edited into the body. Was ACTIVE-PLAN (`docs/README.md` sec 3) until that
> close: the working record for `TK147` (TK137 challenge C7,
> `docs/tk137-dsl-openfga-refusals-2026-10-14.md`).
>
> Provenance labels: **PROBE** = a script under `.scratch/ultracode-2026-10-17/tk147/` was
> run by the TK147 workflow agent against `src/` and its output is quoted here (the
> `.scratch/` copy is gitignored; this doc is the record); **READ** = the agent read the
> code at the cited `file::symbol`; **REASONED** = inference, not run. The session must
> re-verify anything headed for a gate pin. Line numbers are deliberately absent; the
> `file::symbol` is the cite.

## Corrections (newest first)

- **2026-10-17 (review fix, TK147 review-fix agent).** Five review findings, each verified
  first-hand, all fixed:
  1. *A hand-built `SchemaInfo` skipped the check* (READ + reviewer PROBE `p1_bypass.py`):
     `compile_ruleset(ast, SchemaInfo(object_wildcard_shapes={('nosuch','viewer')}))` was
     ACCEPTED. Now `src/zanzibar/schema/compiler.py::compile_ruleset` calls
     `_validate_object_wildcard_shapes` on its input `SchemaInfo` FIRST, before
     `_expand_object_wildcard_shapes` closes it. DECISION: `SetEngine(ruleset=)` does NOT
     re-validate `ruleset.schema_info`, because that is the CLOSED set (compiler output),
     and READ of `compiler.py::_reject_object_wildcard_scope` shows the closure can carry a
     shape onto a leaf name, so validating it would refuse a legal store. Still unchecked
     (documented in the check's docstring, the engine comment and the test module): a
     `RuleSet` built by hand and `WildcardIndex(idx, schema_info)`, which has no AST. The
     sec 3 "every path" wording means every path that derives or compiles a `SchemaInfo`.
     The declared-leaf branch of `_reject_object_wildcard_scope` is now unreachable even
     from a hand-built `SchemaInfo` (TK116 UNREACHABLE note updated).
  2. *`declared_types` plumbing was unpinned* (the reviewer's monkeypatch left the 78-test
     module green): the `relationless-type` case used `folder`, which a restriction also
     declares. New BAD case `unrestricted-relationless-type` (`type team`, no relation,
     nothing restricts to it), also in `PERSISTABLE`; `test_derive_schema_info_refuses` now
     passes `declared_types=`, and a new test pins the documented wording without it.
  3. *CHANGELOG*: PROBE (`.scratch/ultracode-2026-10-17/tk147-review-fix/p_leaf_head.py`,
     HEAD `4438bf9` from `git archive` vs the worktree): at HEAD `{('doc','view.0')}` raised
     `UnsupportedByGraphIndex` from `parse_openfga_schema`; `{('doc','nosuch')}` and
     `{('nosuch','viewer')}` were ACCEPTED. Now all three raise `ShapeNoLongerAccepted`
     (not an `UnsupportedByGraphIndex`). The summary bullet and Changed entry now say so,
     list `derive_schema_info` / `compile_ruleset` as raising, and Added lists
     `derive_schema_info(..., declared_types=)`.
  4. *No spec-deviations entry*: added `docs/spec-deviations.md` entry `## 2026-10-17` (TK147).
  5. *Count mismatch* (row "384" vs sec 4 "444" for the 14-module run): no log of that run
     survives (only `run_b.log` = `5 failed, 463 passed` and `run_c.log` = `720 passed`), so
     NEITHER number is supported and both are withdrawn. Re-measured instead, after these
     fixes (PROBE, 2026-10-17, NOT the gate): the 14 modules named in sec 4 plus both
     `test_tk153_*`, `test_tk116_oracle_only_setengine`, `test_tk147_owc_shape_refusal`,
     `test_tk122_release_metadata` and `test_tk123_top_level` (19 files): `611 passed in
     64.72s`, rc=0. `tests/test_tk147_owc_shape_refusal.py` is now 105 tests.
  New sabotage (PROBE, `.scratch/ultracode-2026-10-17/tk147-review-fix/sab.py`, module only,
  file restored and sha256-checked): baseline `rc=0 | 105 passed`; SB11 `declared_types`
  dropped at every binding `rc=1 | 19 failed, 86 passed`; SB12 the `compile_ruleset` call
  deleted `rc=1 | 7 failed, 98 passed`. Content pin: `claim_rot.py --check` flagged
  `compile_ruleset` (rows 364,375,1293,1363,1632,2144); re-read (READ), they describe the
  taint loop, the emitted Rules and the `_node_removal_fence` tail, which a refusal of bad
  input leaves unchanged on return; regenerated `509 anchors (1 changed, 0 added, 0
  removed)`, `--check` rc=0.
  Broad run (PROBE, 2026-10-17, NOT the gate): every `tests/test_*.py` and
  `formal/conformance/test_*.py` module mentioning `object_wildcard_shapes`,
  `compile_ruleset` or `SchemaInfo(` (54 files, list in the gitignored
  `.scratch/ultracode-2026-10-17/tk147-review-fix/broad_modules.txt`): `1810 passed in
  1570.11s`, rc=0. (It collected `test_tk116_oracle_only_setengine.py` before its
  UNREACHABLE note was reworded; re-run alone after: `37 passed`.)

## 1. The pre-change behaviour (PROBE, HEAD `4438bf9`, before any edit)

`probe_noop.py`: schema `type user / type folder (viewer: [user]) / type doc (parent:
[folder], viewer: [user] or viewer from parent)`, a `Store` built with and without the
shape, the same six writes and six checks on each.

```
parse accepts [('nosuch', 'viewer')] -> schema_info.owc [('nosuch', 'viewer')]
  with    (['ok', 'ok', 'AdmissionRejected', 'AdmissionRejected', 'AdmissionRejected', 'ok'], [True, False, True, False, True, False])
  without (['ok', 'ok', 'AdmissionRejected', 'AdmissionRejected', 'AdmissionRejected', 'ok'], [True, False, True, False, True, False])
  SAME
parse accepts [('doc', 'nosuchrel')] -> schema_info.owc [('doc', 'nosuchrel')]
  with    (... identical ...)
  SAME
zanzibar.schema.errors.UnsupportedByGraphIndex: object-wildcard shape (doc, viewer.0) names a compiled leaf predicate
```

- So C7 reproduces: both typo shapes are ACCEPTED, carried into `SchemaInfo`, and change
  no admission and no answer (the `doc:*` write is refused either way). It fails closed,
  silently.
- A compiled-leaf shape `('doc', 'viewer.0')` was refused by the GRAPH only
  (`compiler.py::_reject_object_wildcard_scope`, `UnsupportedByGraphIndex`); the set
  engine swallows that family and ran without a graph partner (READ:
  `tests/test_tk116_oracle_only_setengine.py` witness `owc-names-a-leaf`).
- REASONED: an undeclared shape cannot feed anything. `_expand_object_wildcard_shapes`
  expands from rewrite rules, whose sources are declared relations; the doubly-bridged set
  needs a `[T:*#p]` restriction, and ASK-1 refuses one whose `T#p` is undeclared. Its only
  effects were `UnprovenExtensionWarning` (spurious) and `_maintain_shape_index` (perf).

## 2. The persisted-store trap (the row's Trap) -- decision

- READ: `store/schema_io.py::save_schema` (0.0.5, HEAD) compiles with the caller's shapes
  and writes them to `SchemaRecord.object_wildcard_shapes` as JSON. So **yes, a store
  saved by 0.0.5 can carry an undeclared-type or undeclared-relation shape** (not a leaf
  name: the same compile refused that, so it never persisted).
- **DECISION (agent, against the goal "graph == set engine, oracle referees"): refuse it on
  reopen as a VERSION BREAK, exactly as TK137 handled R1 (C10) and with the one type TK153
  F17 settled on.** The refusal raises `ShapeNoLongerAccepted`; every persisted-schema path
  converts it to `PersistedSchemaRefused`. Reasons:
  * A lenient reopen mode would be a second acceptance mode (TK137 R1 rejected that: it
    doubles the parity surface), and here it buys nothing, because the shape enabled
    nothing (sec 1).
  * The rewrite is exact and meaning-preserving: drop the entry. `.instead` says so.
  * One condition, one type (TK153 F17): every open raises `PersistedSchemaRefused`,
    whatever the caller passes (no schema, the same text, the same text plus the bad
    shapes, the CORRECTED shapes, which was `SchemaMismatch` before the reorder).
- The message must not say "saved by 0.0.4 or earlier": 0.0.5 accepted these. So
  `ShapeNoLongerAccepted` gains keyword-only `accepted_through` (default `'0.0.4'`) and
  `refused_since` (default `'0.0.5'`), and `PersistedSchemaRefused` quotes them. TK147
  passes `'0.0.5'` / `'0.1.0'`. The TK137 messages are unchanged (pinned by
  `tests/test_tk137_persisted_schema_refused.py::VERSION_BREAK`, still green).
- Also decided: **a compiled-leaf name is an undeclared relation**, refused on BOTH
  backends. It moves the TK116 witness `owc-names-a-leaf` to `UNREACHABLE` (the graph-side
  raise in `_reject_object_wildcard_scope` stays as defense in depth for a hand-built
  `SchemaInfo`). This is the equivalence direction: graph-refuses / set-accepts became
  both-refuse.
- Also refused, same type: an entry that is not a `(type, relation)` pair of strings. READ:
  a two-character string `'ab'` unpacked silently into `('a', 'b')` in
  `_reject_object_wildcard_scope`; a longer one crashed there with a raw unpack error.

## 3. What landed (READ of the diff; tests PROBE-run)

- `src/zanzibar/schema/compiler.py::_validate_object_wildcard_shapes`: the one check, three
  REFUSED SHAPE blocks (not a pair / undeclared type / undeclared relation). Types counted
  as declared: AST keys, every restriction type (TK137 S8 makes those declared), and the
  optional `declared_types` (relation-less `type` lines); they pick the MESSAGE only.
  Called from `derive_schema_info` (new keyword-only `declared_types=`, so
  `parse_openfga_schema`) and from `SetEngine.__init__` inside its parse `try` (so the
  `ruleset=` path, which skips `derive_schema_info`, is covered).
- `src/zanzibar/schema/errors.py`: `ShapeNoLongerAccepted.accepted_through` /
  `.refused_since`; `PersistedSchemaRefused` message uses them.
- `src/zanzibar/setengine/engine.py`: `_refuse_persisted_shape` also checks the record's
  shapes; `_assert_schema_matches_record` checks the persisted text AND shapes FIRST, then
  compares (new helpers `_record_shapes`, `_refuse_record_shapes`).
- `src/zanzibar/store/schema_io.py::_verify_same_schema`: parses the stored text and
  validates the stored shapes under `_persisted_schema_parse` before comparing;
  `_schema_difference` takes the already-parsed `stored_ast` (no second parse).
- Paths covered, each pinned in `tests/test_tk147_owc_shape_refusal.py`:
  `parse_openfga_schema`, `derive_schema_info`, standalone `SetEngine`, `SetEngine(ruleset=)`,
  fresh `Store` / `save_schema` / `ensure_schema` (nothing saved), `ParityEngine`; and on a
  0.0.5-persisted bad shape, 13 openers x 3 shapes: `Store()`, `Store(schema)`,
  `Store(schema, bad)`, `Store(schema, corrected)`, `open_set_engine`, `TupleSource`,
  `SetEngine()`, `SetEngine(text)`, `SetEngine(text, bad)`, `save_schema(bad)`,
  `ensure_schema(bad)`, `ensure_schema(corrected)`, `build_index(other id)`.
- No JSON front-end path: READ `schema/json_frontend.py::parse_openfga_json(model)` takes
  no shapes; a JSON model reaches the store as DSL text plus the separate shapes argument.
- No oracle twin: READ `tests/oracle.py::Oracle.__init__(schema, tuples)` takes no shapes
  (star objects are answered intensionally); `test_the_oracle_takes_no_shapes` pins the
  premise. The p23 parser-parity contract is over schema TEXT and is untouched (its module
  re-run green).
- Floors: `tests/test_refused_shape_comments.py` `MIN_HEADERS[schema]` 50 -> 53,
  `MIN_IN_SCOPE_RAISES[schema]` 39 -> 43 (PROBE: HEAD before TK147 already measured 40, one
  above the recorded floor). `CHANGELOG.md` `[Unreleased]`: summary bullet + Changed entry.

## 4. Sabotage (PROBE, 2026-10-17, `.scratch/ultracode-2026-10-17/tk147/sabotage.py`)

One asserted-unique anchor per mutation, file restored byte-for-byte and sha256-checked
(`restored, sha256 ok`); `tests/test_tk147_owc_shape_refusal.py` only (78 tests),
`-p no:cacheprovider`. Literal tails, every one RED (also in that module's docstring):

```
SB1 whole check deleted (early return): rc=1 | 74 failed, 4 passed in 9.84s
SB2 derive_schema_info call deleted: rc=1 | 22 failed, 56 passed in 9.04s
SB3 SetEngine.__init__ call deleted: rc=1 | 12 failed, 66 passed in 8.18s
SB4 undeclared-type branch off: rc=1 | 19 failed, 59 passed in 7.96s
SB5 undeclared-relation branch off: rc=1 | 44 failed, 34 passed in 8.63s
SB6 not-a-pair branch off: rc=1 | 11 failed, 67 passed in 8.14s
SB7 schema_io persisted-shape check deleted: rc=1 | 15 failed, 63 passed in 8.26s
SB8 engine _assert_schema_matches_record shape check deleted: rc=1 | 3 failed, 75 passed in 7.87s
SB9 engine _refuse_persisted_shape shape check deleted: rc=1 | 6 failed, 72 passed in 8.16s
SB10 accepted_through dropped on the undeclared-type raise: rc=1 | 19 failed, 59 passed in 7.94s
```

Targeted runs on the changed tree (PROBE, 2026-10-17; NOT the gate):
- 14 modules (tk137 persisted, refused-shape comments, p23 parity, schema_ast,
  boolean_compile, tk153, unproven warning, connectedstore_schema, tk136, tk123
  equivalence refusals, admission_rejected, schema, schema_shapes, wildcard_schema):
  `444 passed`.
- `tests/test_tk116_oracle_only_setengine.py` after the witness move: `37 passed`.
- 27 owc-touching modules (matrix, integration, scenarios, wildcard, bulk_build, ...):
  `5 failed, 463 passed`; the 5 were all TK116 `owc-names-a-leaf`, because that run had
  collected the module BEFORE the witness moved (the re-run above is green).
- `tests/test_tk147_owc_shape_refusal.py`: `78 passed`.
- Generators / property / conformance (`test_tk147`, `test_lookup_oracle`,
  `test_wildcard_property`, `test_lookup_hypothesis`, `test_hypothesis` (ci profile),
  conformance `enum_objstar`, `fragment`, `graphadmission_scope_pin`, `w4fragment_scope_pin`,
  `leaf_namespace_correspondence`, `direct_arm`): `720 passed in 587.36s`, rc=0.

Content pin (PROBE, 2026-10-17): `claim_rot.py --check` flagged exactly one anchor,
`src/zanzibar/schema/compiler.py::derive_schema_info` (BODY CHANGED, rows
362,363,396,397,398,414,1120). Re-read (READ): every row describes the subject-wildcard
loops (pass 1 / pass 2 / "in full" feeding `subject_wildcard_shapes`) or the boolean
admission of `[user, user:*]`. The new call is a refusal of bad `object_wildcard_shapes`
input; when it returns, the output is unchanged, so every row is still true.
Regenerated: `509 anchors (1 changed, 0 added, 0 removed)`; `--check` then `rc=0`.
(Rows 397/398 cite `:990-995` / `:1001-1009`, line numbers that were already stale before
TK147; not touched.)

## 5. What remains

- The full gate (another stage runs it). READ: `tests/genswarm.py` draws shapes from the
  schema's own keys, and the hypothesis modules above ran green (ci profile, default seed).
- `formal/FINAL_REVIEW.md`'s generated counts block (verify.sh step 4e) is NOT regenerated
  here: this change adds 78 tests and removes 4 (the TK116 leaf witness), and other
  tasks in the same run change the counts too, so the gate stage regenerates it once
  (`python -m formal.conformance.doc_counts --generate`) and may ratchet `MIN_TESTS_ALL`.
- Close the row after the gate.
