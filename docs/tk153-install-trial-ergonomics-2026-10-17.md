# TK153 -- 0.0.5 install-trial ergonomics findings: verification and landing map (2026-10-17)

> **FROZEN 2026-10-17 -- provenance, not a living document.** Status lines below are
> as-of-then and several may now be false; live state: `HANDOFF.md` + the session
> ledger. Corrections are appended dated at the top, never edited into the body.

> **Was ACTIVE-PLAN** (`docs/README.md` sec 3) until `TK153` closed 2026-10-17. The working record for `TK153`: which of the
> 0.0.5 install-trial findings on the row
> ([`pypi-trial-0.0.5-2026-10-15.md`](pypi-trial-0.0.5-2026-10-15.md)) reproduced against
> `src/` at HEAD `7f45d5a`, and what landed for each. Corrections are appended **dated at the
> top**, never edited into the body. FROZEN when `TK153` closes.
>
> Provenance labels: **PROBE** = a probe under `.scratch/ultracode-2026-10-17/tk153-probes/`
> was run by the TK153 workflow agent against `src/` (`zanzibar.__file__` confirmed in the
> checkout) and its output is quoted; **READ** = the agent read the code at the cited
> `file::symbol`; **REASONED** = inference, not run. Line numbers appear only dated (sec 4);
> the `file::symbol` is the cite. Everything here is the agent's work: the session must
> re-verify anything headed for a gate pin. The renames are the 0.1.0 break the user asked
> for (`TK153` row, 2026-10-16): they are under `CHANGELOG.md` `[Unreleased]`, and the
> version stays 0.0.5.

## Corrections (newest first)

- **2026-10-17, second review-fix pass (workflow agent; PROBE = rerun first-hand, tests
  quoted).** Three minor review findings, all real, all fixed.
  * **F11's reason was false for a relation-less declared type.** PROBE
    (`.scratch/ultracode-2026-10-17/tk153-review2-p1.py`): with `type folder` declared but
    given no relations and named by no restriction, writing `user:a member folder:f` read
    `... names an undeclared relation folder#member: type 'folder' is not declared in the
    schema` on the set engine, `RuleSet.apply` and `Store`. Cause (READ):
    `schema/syntax.py::declared_relations` built `types` from the AST alone, and a
    relation-less type leaves no trace there. The set engine's message came from its own
    `compile_ruleset` call, not from `SetEngine._validate` (PROBE: the message had the
    `RuleSet.apply` format). Fix: new `schema/parser.py::_parse_schema_ast_checked`
    returns `(ast, declared_types)` (`parse_schema_ast` returns its `[0]`);
    `declared_relations(ast, declared_types)`; `compile_ruleset` gains keyword-only
    `declared_types` (messages only, CHANGELOG Added); `parse_openfga_schema` and
    `SetEngine.__init__` pass it. Now all three say `type 'folder' declares no relations`
    (the existing branch of `syntax.py::no_restriction_reason`). This is not a divergence:
    the backends agreed before and still agree, and no verdict changes. Pin:
    `tests/test_tk153_install_trial_ergonomics.py::
    test_f11_relation_less_declared_type_is_not_called_undeclared`. Sabotage SB10
    (`types = set()`): `1 failed, 65 deselected`.
  * **The F9 / ASK-1 dangling-userset messages dropped `:*`.** PROBE: `[team:*#member]`
    rendered as `[team#member]` in both branches of
    `schema/parser.py::_validate_ast_consistency`. Fix: both use
    `syntax.py::_render_restriction`. Message text only. The oracle twin's wording is
    independent and was not touched. Pin: `test_f9_wildcard_userset_restriction_keeps_its_star`
    (2 params). Sabotage SB11: `2 failed, 64 deselected`.
  * **The ASCII pin read less than `help()` renders.** READ:
    `tests/test_tk153_ascii_public_text.py::_public_doc_targets` skipped every dunder except
    `__init__`, and skipped nested classes. Fix: members now follow pydoc's `visiblename`
    rule (dunders and public names in, `_single` out), with recursion into nested classes.
    PROBE: `help(Outer)` lists a nested class only as an attribute, but
    `help(Outer.Nested)` renders it, so the pin reads it. The widened scan is green on the
    real tree, which confirms the reviewer's AST census. New instrument test
    `test_the_pin_reads_what_help_renders`. Sabotage (old filter restored): `1 failed,
    3 passed`.
  * **Counts:** `doc_counts --generate`: `tests/` 2737 -> 2741 (+4 tests, all from this
    pass), `MIN_TESTS_ALL` ratcheted 2737 -> 2741, `--check` rc=0. Batch rerun: 1185 passed
    (schema, parser-parity, refused-shape-comments, snapshot, TK123/TK137/TK153 modules, and
    the conformance fragment pin). The full gate was NOT run in this pass.
- **2026-10-17, review-fix pass (workflow agent; PROBE = rerun first-hand, tests quoted).**
  Two review findings were real and are fixed; the counts block is regenerated.
  * **F17 had a hole (blocking):** `save_schema(s, id, <the stored refused text>)` raised the
    bare `ShapeNoLongerAccepted`, and `ensure_schema(s, id, <that text>)` returned
    `(row, None)` silently. Both contradicted `PersistedSchemaRefused`'s docstring and the
    CHANGELOG. Cause (READ): `store/schema_io.py::_schema_difference` returned `None` on
    identical text BEFORE parsing the stored text under `_persisted_schema_parse`. Fix: parse
    the stored text under the wrapper first (once), then short-circuit. Pins: `ENTRY_POINTS`
    in `tests/test_tk153_install_trial_ergonomics.py` gains `save_schema(old)` and
    `ensure_schema(old)` (8 new rows over the four TK137 shapes). Sabotage (early return
    restored above the parse): `8 failed, 40 passed` (`-k entry_point`), `Failed: DID NOT
    RAISE PersistedSchemaRefused`. Cost (REASONED): a reopen that passes the same text now
    parses the stored schema once, where it used to parse nothing.
  * **F6's repr flushed the session (blocking):** `store/models.py::_row_repr` reloads expired
    attributes, and the reload autoflushed pending writes, so `repr(row)` flushed a pending
    insert and, for a conflicting one, swallowed the IntegrityError (fields `?`) and left the
    session in `PendingRollbackError`. Fix: the reads run under `session.no_autoflush`. Pin:
    `test_f6_repr_never_flushes_the_session`. Sabotage (guard -> `contextlib.nullcontext()`):
    `1 failed, 3 passed` (`-k f6`), `assert 0 == 1` on the pending count.
  * **Counts block:** `python -m formal.conformance.doc_counts --generate` run: `tests/`
    2671 -> 2737 (54 + 3 + 9 TK153 tests), `MIN_TESTS_ALL` ratcheted 2671 -> 2737 in
    `formal/verify.sh`; `--check` then rc=0. Re-check before the gate if another session
    adds tests. `claim_rot.py --check` rc=0 (509/509) after the fix.
  * Batch after the fix (PROBE, 2026-10-17): TK153 + TK137 + schema/returns/safety/TK136
    modules `167 passed`; store / connected / TK12x / TK14x modules `675 passed`.

## 1. What the trial's findings look like on the tree now

`TK123` items 4-26 (commit `d94e307`) landed AFTER the trial and already fixed part of what
the row lists. Verdicts, first-hand:

| finding | reproduced at `7f45d5a`? | evidence |
|---|---|---|
| F3 non-ASCII public docstrings | **YES** (18 public docstrings, 0 runtime messages) | PROBE `nonascii.py`: a census over exactly the surface `tests/test_tk123_no_internal_refs.py::docstring_leaks` reads (e.g. `store/apply.py advance_index ['0x2464']`, `graphindex/wildcard.py WildcardIndex.lookup ['0x2208', '0x2209', '0x2227']`, `setengine/memberset.py <module>`, six more files). The section sign was already gone from public docstrings (TK123's leak regex refuses it). |
| F8 `DeltaProcessor` not public | **YES** | PROBE `verify.py`: `'DeltaProcessor' in zanzibar.graphindex.__all__` -> `False`; the `MissingDeltaProcessor` message said `Pass DeltaProcessor(widx, ruleset.compiled) as proc` and named no import. |
| F9a `ShapeRefusedSinceTK137` name / export / `.instead` | **NO, already fixed by TK123** | READ: `src/zanzibar/schema/errors.py::ShapeNoLongerAccepted` (a `SchemaError`), in `zanzibar.__all__` and `zanzibar.schema.__all__`; CHANGELOG `[Unreleased]` "`ShapeRefusedSinceTK137` is now `ShapeNoLongerAccepted`". `.instead` WAS undocumented in a user-visible place: fixed here (docstring + `PYPI_README.md` exception table). |
| F9b `[team#member]`, no `type team` | **YES** | PROBE: `doc#v: restriction [team#member] names an undeclared relation team#member` (the `[usr]` case already said `undeclared type 'usr'`). |
| F11 undeclared-relation write message | **PARTLY**: TK123 added the reason, the lead was still wrong | PROBE: `tuple doc:d#vewer@user:a#... matches no declared type restriction for doc#vewer: type 'doc' declares no relation 'vewer'; did you mean 'viewer'?` |
| F17 three exception types for one cause | **YES** (two of the three; the set engine) | PROBE, a 0.0.4-era `SchemaRecord` with `a or b but not c`: `Store(s, id)`, `Store(s, id, schema=rewritten)`, `open_set_engine`, `save_schema`, `build_index` -> `PersistedSchemaRefused`; `SetEngine(s, id, rewritten)` -> `SchemaMismatch`; `SetEngine(s, id, old_text)` -> `ShapeNoLongerAccepted`. Also found: `SetEngine(s, id)` with NO schema -> `ShapeNoLongerAccepted` (a fourth path the trial did not list). |
| F6 reprs | **YES** for `save_schema`; `BuildReport` already short (TK123) | PROBE `repr6.py`: after `commit()`, `repr(save_schema(...))` = `(SchemaRecord(), RuleSet(rules_and_filters=[Filter(...` (594 chars for a one-relation schema; 1,223 before the commit). The empty `SchemaRecord()` / `IndexCursor()` is SQLModel's repr reading an EXPIRED `__dict__` (REASONED from that output: before the commit the same row printed its fields). `build_index` returns `BuildReport(index_store_id='p6i', applied_log_id=0, constructor='bulk')` (TK123). |
| F19 `lookup_reverse` userset nodes | **YES**, both backends agree (doc gap, not a divergence) | PROBE `f19.py`, `viewer: [user, group#member] but not banned`, g = {ok, m1}, m1 banned: `Store` keys `[('group','g','member'), ('user','ok','...')]`, no markers, no exclusions; `check m1` False; `SetEngine` the same keys. `PYPI_README.md` already warned against expanding a userset; the "list the users" recipe was missing. |
| TK150 scout (1): `ClosureFanoutExceeded` docstring "does not bite at the 100,000 default" | **YES** | READ `src/zanzibar/schema/errors.py::ClosureFanoutExceeded`; also "the store cannot advance past it until the cap is raised", false since replay runs under `ReachabilityIndex.fanout_cap_suspended` (READ `graphindex/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl`). No claim_rot pin on either text (READ: `tests/test_claim_rot_gate.py` has no match for `fanout`, `44` or `errors.py`). |
| TK150 scout (2): `DEFAULT_MAX_CLOSURE_FANOUT` comment "44 rows in `tests/`" | **YES** (stale) | see sec 3. |

## 2. What landed (uncommitted at the agent's return; the gate is another stage's)

- **F3.** 18 public docstrings rewritten to ASCII by a span-limited rewriter (docstring line
  ranges of public targets only; e.g. `facade`, `x`, `WARNING:`, `in` / `not in` / `and`,
  `->`, `...`, `UNION`). Pin: `tests/test_tk153_ascii_public_text.py` (public docstrings,
  runtime message strings, and the trial's literal `cp1252` repro on `advance_index`).
  Sabotage SB7-SB9 recorded in its docstring, all RED.
- **F8.** `zanzibar.graphindex.DeltaProcessor` exported (`__init__`, `__all__`, a
  user-facing class docstring); the `MissingDeltaProcessor` message now says
  `(from zanzibar.graphindex import DeltaProcessor)`.
  `tests/test_tk123_top_level.py::_EXPECTED_ALL` updated (a deliberate surface change).
- **F9.** `src/zanzibar/schema/parser.py::_validate_ast_consistency` takes the declared type
  set (from `parse_schema_ast` and `json_frontend.py::parse_openfga_json`) and, for a
  userset restriction whose TYPE is undeclared, says `names an undeclared type 'team', so
  team#member is an undeclared relation; ...`. Message only: the verdict is unchanged, it
  stays a `SchemaError` (refused since ASK-1, before 0.0.4, so it is NOT a
  `ShapeNoLongerAccepted` and the persisted-store conversion must not touch it), and the
  substring `undeclared relation` that `tests/genswarm.py::DANGLING_REFERENCE` matches is
  kept. The oracle twin needs no change (verdict parity, `tests/test_p23_parser_refusal_parity.py`, passes).
- **F11.** `src/zanzibar/schema/syntax.py::no_restriction_message` builds the whole
  admission refusal for both backends (`rules.py::RuleSet.apply` twice,
  `setengine/engine.py::SetEngine._validate`): an undeclared type or relation leads with
  `names an undeclared relation doc#vewer`, every other case keeps `matches no declared
  type restriction for ...`. `tests/test_tk123_safety_messages.py::test_admission_refusal_explains_itself`
  now pins the lead per case.
- **F17. DECISION: one type, not a common base.** `PersistedSchemaRefused` is raised by
  every entry point, the set engine included. Reasoning: the condition is one fact about
  the STORE (its stored text is refused by this version), and the user-facing fix is the
  same whichever call found it (rewrite, new store id), so a common base over three types
  would keep three names for one cause. It is not made a `SchemaMismatch` subclass: with no
  schema passed nothing is "mismatched". The class moved to `schema/errors.py` (the shared
  layer, as `SchemaMismatch` did in TK123 A53) so `setengine` raises it without importing
  the store layer; `zanzibar.store` re-exports the same object. `SetEngine` converts in
  two places: `engine.py::_assert_schema_matches_record` (rewritten text) and
  `engine.py::_refuse_persisted_shape` (old text, or none, when the STORED text is also
  refused; a refused text over a good stored schema stays the caller's
  `ShapeNoLongerAccepted`). Pin: `tests/test_tk153_install_trial_ergonomics.py`, 10 entry
  points x the four TK137 shapes, plus both controls. Breaking: CHANGELOG `[Unreleased]`.
- **F6.** `RuleSet.__repr__` counts (`RuleSet(N rules and filters, K boolean relations)`;
  the snapshot gate reads `rules_and_filters` element reprs, not this, READ
  `tests/test_compile_snapshot.py::_canonical_ruleset`); `SchemaRecord` / `IndexCursor`
  get `store/models.py::_row_repr`, which reloads an expired attribute on an attached row
  and prints `?` for one it cannot read (never raises from `repr`).
- **F19.** `PYPI_README.md` "Reading lookup results" and `Store.lookup_reverse`'s docstring
  give the recipe: user-typed keys, plus each `user` marker minus the exclusions; never
  expand a userset key. Not sent to `TK151`.
- **Exception table** (`PYPI_README.md`): rows for `ShapeNoLongerAccepted` (`.instead`),
  `PersistedSchemaRefused` and `MissingDeltaProcessor`.
- **ClosureFanoutExceeded** docstring rewritten (it can bite at the default; sync-only;
  replay applies with a warning; why it has its own type); the history moved to a `#`
  comment.

## 3. The `DEFAULT_MAX_CLOSURE_FANOUT` comment's `tests/` figure

PROBE, 2026-10-17, re-measured rather than copied from the TK150 scout's 93
(`docs/closure-fanout-cost-2026-10-14.md` Correction 2026-10-16 (c)). Instrument: the probe
plugin now TRACKED at `formal/probes/tk153_fanout_probe_plugin_2026_10_17.py` (it wraps the
cap in an `int` subclass whose reflected `__lt__` records every `fanout > cap` comparison in
`graphindex/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl`; no `src/` edit).
Instrument control: on `tests/test_reg17_closure_fanout_cap.py` alone it recorded maxima
`[0, 4, 24, 440]`, i.e. it sees the deliberate 440-row control (re-run from the tracked copy:
`11 passed`, the 440 present).

Full `tests/` run (one process, ~28.5 min, the working tree mid-edit):

- 906 tests reached a cap comparison, 41,606 comparisons in all.
- max **440** = the deliberate control
  (`test_reg17_closure_fanout_cap.py::test_default_admits_a_region_far_larger_than_any_test_writes`);
  next **93** (`test_tk111_path_count_bound.py::test_sync_overflow_is_a_clean_refusal_at_the_int4_ceiling`),
  then 89, 24; max under `fanout_cap_suspended` 92; **0 writes over 1,000**. Same as the
  scout's 2026-10-16 figures.
- The run's verdict: `8 failed, 2666 passed`, rc 1. All 8 failures are
  `tests/test_claim_rot_gate.py`, because this agent's edits changed four anchored
  bodies before the pin was regenerated (sec 4); after regeneration that module is
  `42 passed`. So the rest of `tests/` passed with these changes applied (REASONED for
  the edits made after collection: the ASCII-only and message edits it ran against were
  already in place; the later edits are comments, the claim-rot pin and `PYPI_README.md`).

Landed: the `#:` comment above `core.py::DEFAULT_MAX_CLOSURE_FANOUT` now says 93 (re-measured
2026-10-17, 440 the control) and 124 for `formal/conformance/` (2026-10-16, the scout's; not
re-run here), and names the probe; `tests/test_reg17_closure_fanout_cap.py`'s comment above
`MEASURED_SUITE_MAX_FANOUT` gets the same dated annotation (the constant stays 124: it is the
larger suite's max, which this did not re-measure).

## 4. Gate-adjacent effects for the gate stage (READ / PROBE)

- `formal/conformance/claim_rot.py --check` went RED on four anchored bodies this item
  changed: `parser.py::_validate_ast_consistency`, `parser.py::parse_schema_ast`,
  `rules.py::RuleSet.apply`, `engine.py::SetEngine._validate`. The cited `CORRESPONDENCE.md`
  rows (179, 212, 250, 304, 365-377, 443, 977, 1013, 1217 on 2026-10-17) were re-read: they
  describe refusal sets, routing and admission steps, none of which changed (the edits are
  message text and an argument used only to choose a message). Regenerated deliberately
  (`claim_rot.py --generate`): `509/509 bodies match`.
- `formal/FINAL_REVIEW.md`'s generated counts block will need
  `python -m formal.conformance.doc_counts --generate` (two new test modules, 57 tests);
  NOT run here, because other sessions may also be adding tests before the gate.
- Targeted batch, 2026-10-17 (PROBE): 43 related modules, `1242 passed`; the two TK153
  modules `57 passed`; `task.py lint` clean; `handoff_lint.py` clean.

## 5. What remains

- Nothing of the row's list is left undone in code. The gate (all phases) and the doc-counts
  regeneration are the next stage's. F19 was landed here, so it does not go to `TK151`.
- Not addressed, not on the row: the trial's F5 / F12 / F13 items map to `TK123` (done there).
