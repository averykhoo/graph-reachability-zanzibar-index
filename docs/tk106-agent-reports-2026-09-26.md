# `TK106` subagent reports (2026-09-26)

**Companion to [`tk106-boolean-tuplesets-2026-09-26.md`](tk106-boolean-tuplesets-2026-09-26.md);
FROZEN with it when `TK106` closes.** Each section below was transcribed verbatim from a
subagent's gitignored `.scratch/tk106/agent-<name>.md` the same hour it returned, per
CLAUDE.md "SCOUTING IS A DELIVERABLE". **A subagent's report is evidence, not a finding.**
Its sabotage outputs are quoted literally from its own runs. The session re-checks by
running the touched modules in the gate before anything here is relied on.

---

## A. `tests/test_hypothesis.py` + `tests/test_lookup_oracle.py` strategy trim

# agent-hypothesis: TK106 strategy trim in tests/test_hypothesis.py + tests/test_lookup_oracle.py (2026-09-26)

## Step 0 -- baseline (first-hand)
- Both files: CRLF on every line (test_hypothesis.py 2224/2224, test_lookup_oracle.py 1799/1799), git-clean at start.
- collect-only BEFORE: `tests/test_hypothesis.py` -> `31 tests collected`; `tests/test_lookup_oracle.py` -> `45 tests collected`.
- Probe `.scratch/tk106/hyp_probe_union.py` (READ, 2026-09-26): `_ts_probe_schema(kind)` through both checked parsers:
  intersection / negonly-multitype / negonly-star -> REFUSED by zanzibar.schema.parse_schema_ast AND tests/oracle.parse_schema_ast, message contains `tupleset must be direct`; plain / multitype / wildcard / multitype-wildcard / union -> ok on both. Triage §3 claim CONFIRMED.
- Probe `.scratch/tk106/hyp_probe_union2.py` (READ): `parent: [doc] or [folder]` -> `compute_taint` = [] and CompiledBooleans.plans = [] (same as `[doc, folder]` and `[doc]`). The 'union' comment ("tainted ... DERIVED predicate with storage leaves") is STALE. Triage side finding CONFIRMED.

## Step 1-3 -- edits to tests/test_hypothesis.py (first-hand; CRLF preserved, checked with grep -c $'\r$' == wc -l)
- `::_TUPLESET_BODIES`: removed 'intersection', 'negonly-multitype', 'negonly-star'. Remaining 5: multitype, multitype-wildcard, plain, union, wildcard. Dated TK106 note above the table (parse refusal via `src/zanzibar/schema/parser.py::_validate_tuplesets_direct` + oracle twin; refusal pinned in `tests/genswarm.py::REJECTION_WITNESSES`). Pre-TK106 "NEG-ONLY TRAP" comment replaced by that note. 'union' comment rewritten: compiles UNTAINTED (probe above). Header comment "Booleans ... are all drawn" corrected.
- `::schema_asts` docstring: "boolean and neg-only-arm tuplesets" -> dated TK106 note.
- `::test_negonly_tupleset_bodies_really_have_a_type_only_in_the_negative_arm`: DELETED; dated comment left in its place.
- `::test_every_tupleset_kind_is_reachable_and_the_grid_queries_it`: floor `>= 8` -> `>= 5`, dated provenance comment.
- `::test_schema_asts_draws_the_whole_tupleset_grammar`: dropped BOOLEAN and NEG-ONLY asserts with dated note; docstring updated.

## Step 4a -- re-measurement (READ, `.scratch/tk106/hyp_measure.py` -> `hyp_measure.out`, 2026-09-26, post-trim tree)
- four-way sweep (`_sweep_schema_asts`, seeds 7/19/31 x 60): **144/180 = 80.0%** (was 158/180 = 88% on 2026-08-10). Draws per kind: multitype 32, multitype-wildcard 37, plain 44, union 35, wildcard 32. Joins: 32 / 19 / 44 / 35 / 14. All 36 drops are "star tupleset [doc:*] on 'parent' derives the wildcard userset shape ..." (decision-15). Floor `_SCHEMA_ASTS_FOUR_WAY_FLOOR = 0.60` unchanged.
- lookup gate join (seeds 0..239): **185/240 = 77%** (floor-div), rejected 55, empty-pool 0 (was 195/240 = 81%). Per-kind, 120 seeds each with tupleset_kind pinned: multitype 100%, plain 100%, union 100%, multitype-wildcard 60/120 = 50%, wildcard 60/120 = 50%. Floor 60% unchanged; `rejected > 0` still holds.

## Step 4b -- sabotages (all 2026-09-26, on the post-trim tree; test-file sabotages applied/restored byte-exactly by `.scratch/tk106/hyp_sab.py`, sha1 of tests/test_hypothesis.py checked identical after every restore: RESTORED-IDENTICAL x3)
- **S1** `_schema_ast`: `tupleset_kind = ch.one(_TUPLESET_KINDS)` -> `tupleset_kind = 'wildcard'` (log `sab1.log`, `3 failed in 7.27s`):
  - test_schema_asts_four_way_rate: `AssertionError: only 89/180 = 49% of generated schemas compile for the graph index (floor 60%); the campaign has drifted into fuzzing 3-way. Reasons: ["relation doc#r1: star tupleset [doc:*] on 'parent' derives the wildcard userset shape (doc, r0) over the derived relation doc#r0, which needs symbolic composition through residues (v1 scope hook; see spec-deviations)", ...]`
  - test_lookup_oracle_gate_generated_schemas_graph_join_rate: `AssertionError: only 116/240 = 48% of generated schemas join the graph index (floor 60%); test_lookup_oracle_gate_generated_schemas is skipping most draws and asserting nothing`
  - test_schema_asts_draws_the_whole_tupleset_grammar (collateral): `180 draws realised only 1 of the 5 tupleset bodies; missing ['multitype', 'multitype-wildcard', 'plain', 'union']`
- **S2** `_schema_ast`: literal pre-2026-08-10 line `ast = {('doc', 'parent'): Direct((Restriction('doc', '...', False),))}` (log `sab2.log`, `1 failed in 0.76s`): `AssertionError: 180 draws realised only 1 of the 5 tupleset bodies; missing ['multitype', 'multitype-wildcard', 'union', 'wildcard'] -- the TTU tupleset is hardcoded again`
- **S3** `_op_pool`: untyped fallback `names = ['*'] if r.wildcard else (USERS if r.type == 'user' else DOCS)` (log `sab3.log`, `1 failed in 1.26s`): `AssertionError: tupleset kind 'multitype': 4/14 candidates write to entities the check grid never queries, so they are admitted and inert: [('...', 'folder', 'd1', 'parent', 'doc', 'd1'), ('...', 'folder', 'd1', 'parent', 'doc', 'd2'), ('...', 'folder', 'd2', 'parent', 'doc', 'd1'), ('...', 'folder', 'd2', 'parent', 'doc', 'd2')]`
- **S4 (GREEN -- a finding)** RC2 re-introduced at its live processor fix site, IN-PROCESS monkeypatch (`.scratch/tk106/hyp_sab_rc2.py`; processor.py is out of my edit scope and another session runs tests): `DeltaProcessor._expand_tupleset_parents(self, concretes, star_types)` -> ignores `star_types`. test_every_tupleset_kind_is_driven_against_the_oracle: control `1 passed in 10.74s`, sabotage `1 passed in 12.91s`. REASONED: every remaining probe cell has an UNTAINTED tupleset AND an untainted TTU target (`r0: [user]`), so the TTU leaf is a rule-routed leaf (star bridge), never `PDerivedTTU`/`ttu_check`; the RC2 processor branch is reached only by a derived TTU target. After TK106 this test no longer guards the RC2 processor site (it did pre-TK106 only via `negonly-star`, a DERIVED tupleset). All 10 cells are DRIVEN (none skipped as out-of-fragment): probe `.scratch/tk106/hyp_cells.py`.
- **S5 (RED)** graph-only, IN-PROCESS (`.scratch/tk106/hyp_sab_through.py`): `zanzibar.schema.derive_schema_info` (module global, read by `parse_openfga_schema`; setengine's own import untouched) returns SchemaInfo minus the star-tupleset through-shapes (`(S, target_rel)` for `[S:*]` on a tupleset). `1 failed in 10.75s`:
  `AssertionError: the generated tupleset grammar DRIVES a backend divergence on [('multitype-wildcard', 'negated TTU'), ('multitype-wildcard', 'positive TTU'), ('wildcard', 'negated TTU'), ('wildcard', 'positive TTU')]:` each `accept/reject disagreement on add ('...', 'doc', '*', 'parent', 'doc', 'd1'): {'graph': False, 'set:py': True, 'set:roaring': True}`. 6 cells stay green (multitype, plain, union x both polarities).
- Side finding (REASONED, not sabotaged): the driven-test probe grants `r0` only on `doc:d1`, so a stored `folder:f1 parent doc:d1` parent yields `r1 = False` on every backend whether or not the graph walks it. A graph that dropped the `folder` type from a tupleset's parent types would stay GREEN here; the folder arm of `multitype` / `multitype-wildcard` / `union` is admitted and driven but not discriminating in this test.

## Step 4c -- docstring/provenance edits (first-hand)
- `tests/test_hypothesis.py::test_op_pool_is_schema_valid_and_co_varies_with_the_grid`: S3 re-observation on 'multitype' recorded; 'intersection' output kept, labelled pre-TK106 history. Admission figure re-measured (`.scratch/tk106/hyp_admission.py`): **3730/3730 = 100.0%** (was 3550/3550).
- `::test_every_tupleset_kind_is_driven_against_the_oracle`: dated TK106 block -- old red table labelled PRE-TK106 HISTORY; 10 cells all driven; S5 RED output recorded; S4 GREEN finding recorded (RC2 processor site `_EvalContext.ttu_check` no longer guarded here); folder-arm non-discrimination recorded as REASONED.
- `::test_schema_asts_draws_the_whole_tupleset_grammar`: S2 re-observation + per-body draw counts recorded; 8-body output kept as history.
- `::_SCHEMA_ASTS_FOUR_WAY_FLOOR` provenance comment: re-measured 144/180 = 80.0%, per-body joins, 'wildcard' pin = 49%; floor UNCHANGED 0.60.
- `::test_schema_asts_four_way_rate`: S1 re-observation (49%) recorded; negonly-star output kept as history.
- `::ParityMachine` docstring: one-line TK106 history note on the RC1 schema it once assembled.
- `tests/test_lookup_oracle.py::test_lookup_oracle_gate_generated_schemas_graph_join_rate`: dated TK106 block -- re-measured 185/240 = 77%, per-kind rates, S1 re-observation (48%); old figures kept as history. Floor UNCHANGED 60%.
- collect-only AFTER: test_hypothesis.py `30 tests collected` (31 -> 30: the deleted negonly guard); test_lookup_oracle.py `45 tests collected` (unchanged).

## Step 5 -- final runs (2026-09-26, rc captured as `cmd > log 2>&1; rc=$?`, summary line read)
- `tests/test_hypothesis.py`: `30 passed in 188.73s (0:03:08)`, rc=0 (log `.scratch/tk106/run-hypothesis.log`)
- `tests/test_lookup_oracle.py`: `45 passed in 178.88s (0:02:58)`, rc=0 (log `.scratch/tk106/run-lookup.log`)
- ⚠ The `tests/` collected count dropped by 1 (the deleted negonly guard). `MIN_TESTS_ALL` in formal/verify.sh has ZERO headroom, so the floor needs a deliberate lowering by the orchestrating session (not in my edit scope).

---

## B. `formal/conformance/` under the TK106 rule

Final full-directory run by the agent: `1081 passed in 3004.72s (0:50:04)`, 0 failed / 0 skipped.
Every "session still owes" item listed at the end below was done by the session the same day
(floors, `FINAL_REVIEW.md` regeneration, the five count-prose lines, the Lean doc comments and
`formal/*.md`).

# TK106 conformance agent report (2026-09-26)

Baseline (before edits): `pytest formal/conformance -q --collect-only` -> `1038 tests collected in 1.41s` (first-hand).
Census before edits (other session's log .scratch/tk106/census-conf.log): `14 failed, 1024 passed in 2742.37s`.

## Probe 1 (first-hand, .scratch/tk106/conf_probe1.py, 2026-09-26) -- what every surface does with the carrier `derived_tupleset_ttu`

    prod parse_schema_ast: ValueError: doc#inherited: 'viewer' from 'parent': a tupleset must be direct (...)
    oracle parse_schema_ast: ValueError: doc#inherited: tupleset must be direct, but doc#parent is not
    oracle Oracle(): ValueError: doc#inherited: tupleset must be direct, but doc#parent is not
    parse_openfga_schema: ValueError: doc#inherited: 'viewer' from 'parent': a tupleset must be direct (...)
    SetEngine(): ValueError: doc#inherited: 'viewer' from 'parent': a tupleset must be direct (...)
    unchecked compile leaf kinds: ['closure', 'derived-tupleset-ttu']
    unchecked taint: [('doc', 'inherited'), ('doc', 'parent')]
    probe ttuDirect.derived/derived-tupleset: ValueError: doc#view: 'viewer' from 'parent': a tupleset must be direct (...)
    probe ttuDirect.untainted/tupleset-with-computed-arm: ValueError: doc#view: 'viewer' from 'parent': a tupleset must be direct (...)

So: every checked entry point refuses; the UNCHECKED parse + compile_ruleset still mints the `derived-tupleset-ttu` leaf
(the carrier is really the carrier), and the untainted computed-arm probe now dies at parse time with ValueError before
the graph compiler's UnsupportedByGraphIndex can fire.

## Module 1: formal/conformance/corpus.py (CRLF preserved: 1327 CR / 1327 lines after first edits)
- `corpus.py::TTU_USERSET_SCHEMAS` loses `derived_tupleset_ttu`; new dict `corpus.py::REFUSED_TUPLESET_SCHEMAS`
  holds it verbatim (schema + store unchanged), with a dated TK106 header saying it is NOT a conformance family and
  why it is kept (sole carrier of plan-leaf kind `derived-tupleset-ttu`, unreachable from any checked parse).
  The as-written 2026-07-28 (f) block kept, prefixed by a note that it describes the abolished semantics.
- Decision: MOVE, not delete, not filter-in-consumers. Every positive consumer iterates the family dicts by name
  (spec, grid_independence, leaf_namespace, state, fragment, nary_strata), so moving it out removes it from all
  positive comparisons at once with no per-consumer skip; the consumers that need it (exclusion + refusal pins)
  import the new dict explicitly.
- Dated notes added at the TTU_USERSET header and at the `derived_userset_subject` licence sentence.

## Module 2: formal/conformance/test_conformance_nary_strata.py (CRLF preserved) -- GREEN `20 passed in 3.98s`
- New `_REFUSED_LEAF_KINDS = {"derived-tupleset-ttu": "derived_tupleset_ttu"}`, `_TUPLESET_REFUSAL`,
  helpers `_checked_refusals` (prod parse / oracle parse / parse_openfga_schema; re-raises a ValueError without the
  TK106 fragment) and `_unchecked_leaf_kinds`.
- `test_every_plan_leaf_kind_is_reached_by_some_corpus`: kinds in `_REFUSED_LEAF_KINDS` excluded from the floor, and
  the exclusion asserted three ways: (i) no ACCEPTED corpus reaches the kind (else exclusion stale), (ii) carrier is
  refused by every checked entry point, (iii) carrier still mints the kind on the unchecked compile.
  `_REQUIRED_LEAF_KINDS` unchanged (must still equal the compiler's emitted kinds).
- `test_derived_tupleset_ttu_corpus_features` REPLACED by
  `test_derived_tupleset_ttu_carrier_is_refused_and_still_mints_the_leaf` (refusal on 3 checked entry points, in no
  conformance family, unchecked compile mints the leaf + `parent` has a storage leaf). The old answer assertions
  (bob inherits via a stored-but-excluded parent) were the abolished semantics; dropped, not edited.
- `test_zero_coverage_shapes_three_way` now parametrized over `wildcard_userset` only; new
  `test_refused_tupleset_three_way_refusal[py|roaring]`: Oracle(), SetEngine(ops), parse_openfga_schema all REFUSE
  (agreement by refusal is the positive pin). Net collected count for the module unchanged (1 -> 1, 2 -> 2).
- `test_harness_wide_wildcard_userset_floor` needed no change: it failed only because the loop parsed the carrier;
  floor stays 1 (`wildcard_userset` supplies it).

## Module 3: formal/conformance/test_conformance_fragment.py (LF preserved) -- GREEN `427 passed in 12.74s` (zcli present, 0 skipped)
- New `REFUSED_CORPORA` (from `corpus.py::REFUSED_TUPLESET_SCHEMAS`, key `REFUSED_TUPLESET:derived_tupleset_ttu`) and
  `REPORTED_INPUTS = ALL_CORPORA | REFUSED_CORPORA`. `ALL_CORPORA` stays "accepted curated corpora".
- `MIN_CORPORA` LOWERED 36 -> 35, dated provenance comment (measured len(ALL_CORPORA)=35, len(REFUSED_CORPORA)=1);
  `test_corpus_sweep_is_not_vacuous` additionally asserts REFUSED_CORPORA non-empty and disjoint.
- (B) `test_lean_verdict_matches_the_independent_mirror`, (C) `test_lean_taint_equals_python_compute_taint`,
  (G) `test_lean_admission_verdict_matches_the_prediction`, (D) `DIFFERENTIAL_INPUTS`, (J)/(K) `_mirror_inputs` now
  sweep REPORTED_INPUTS. Expectation rows re-keyed `TTU_USERSET:derived_tupleset_ttu` ->
  `REFUSED_TUPLESET:derived_tupleset_ttu`, verdicts UNCHANGED (computedOrDirect / ttuDirect) -- the unchecked parse
  is the same schema, and Lean still says exactly that (green).
- DECISION (C): refused key parsed with `_parse_schema_ast_unchecked`, NOT excluded. Reason: taint equality is a
  claim about the analysis; shipped code (`w4_fragment_report`, `graph_admission_report`) runs compute_taint on the
  unchecked parse of refused schemas; and it is the only sweep input where taint flows through a tupleset reference
  (`.ttu` case of exprRefs). Curated corpora keep the checked parse; (K) pins the refused one really is refused.
- (H) stays over ALL_CORPORA only (shadowing is about what the premise could silently cover; a refused input is
  covered by nothing). `_SHADOW_FIELD` loses `ttuDirect` (LOUD now: an accepted corpus failing it must go red).
- (K): new branch -- a REFUSED_CORPORA key must be refused by BOTH parsers with `tupleset must be direct`.
- NEW (L) `test_lean_ttudirect_failures_are_refused_by_both_parsers[*]` over `_mirror_inputs()` (47 inputs): if Lean's
  graphAdmissionB fails ttuDirect, both checked parsers raise ValueError matching `tupleset must be direct`; a recorded
  witness on which Lean says the field HOLDS is red. Anti-vacuity `test_ttudirect_refusal_sweep_is_not_vacuous`:
  witnesses {REFUSED_TUPLESET:derived_tupleset_ttu, GA_PROBE:ttuDirect.derived/derived-tupleset,
  GA_PROBE:ttuDirect.untainted/tupleset-with-computed-arm} are in the sweep. This is the Lean-anchored evidence for
  ttuDirect LOUD (the (K) idiom one field over). Converse NOT claimed (REASONED only).
- (F)/w4_scope_probes.py: NO change needed. Every `w4_scope_probes.py::SCOPE_PROBES` tupleset is direct
  ([folder], [org], [team], [folder, folder:*]) -- read first-hand; census had no (F) failure; module green.

## Module 4: graphadmission_scope_probes.py (LF, ASCII) + test_graphadmission_scope_pin.py (CRLF, ASCII) -- GREEN (with fragment: `492 passed in 15.20s`)
- `graphadmission_scope_probes.py::SCHEMA_PROBES`: `ttuDirect.untainted/tupleset-with-computed-arm` expected
  `UnsupportedByGraphIndex` -> `ValueError` (parse-time check now fires before the graph compiler);
  `ttuDirect.derived/derived-tupleset` `ADMITTED` -> `ValueError`. Dated TK106 comments on both.
- `graphadmission_scope_probes.py::SHADOWED`: entry `ttuDirect.derived/derived-tupleset -> computedOrDirect` REMOVED
  (no SILENT half left); comment records why. storeValid's two SHADOWED probes remain, so
  `test_every_mixed_row_has_a_shadowed_probe` holds.
- `test_graphadmission_scope_pin.py::GRAPHADMISSION_SCOPE['ttuDirect']`: MIXED -> LOUD, `shadowed_by` removed,
  evidence `src/zanzibar/schema/compiler.py::_validate_ttu_tuplesets` -> `src/zanzibar/schema/parser.py::_validate_tuplesets_direct`,
  note rewritten (dated). Module docstring: new dated UPDATE paragraph "LOUD 13, MIXED 1, SILENT 0".
- `test_the_classification_ratio_is_the_finding`: asserts `{"LOUD": 13, "MIXED": 1, "SILENT": 0}` (measured by the
  green run: the test counts the table, and `test_classification_agrees_with_its_probes` ties ttuDirect LOUD to both
  probes RAISING -- MEASURED by `test_schema_probe_outcome_still_holds`).
- Stale-prose fix: a dated annotation line inserted before the literal `36 curated corpora` output line in the [count as it was then; 2026-09-26]
  2026-09-24 probe transcript (doc_counts prose check would otherwise flag it; the literal line is untouched).

## Modules 5: test_grid_independence.py, test_leaf_namespace_correspondence.py -- no edit, GREEN `9 passed in 1.43s`
- Both failed only because their family sweep parsed the carrier; the move fixed them.
- Live figures (conf_probe2.py, 2026-09-26): leaf_namespace sweep sources 50, ttu_targets 27, leaf_layer_rules 89
  (floors 45/24/80 -- all hold, no floor change; note ttu_targets 28 -> 27 vs the 2026-08-31 measurement, the
  docstring/message "measured 28 on 2026-08-31" is a dated past measurement and left alone). grid_independence
  corpora 35 (floor 28). `_mirror_inputs` 47 (floor 47, unchanged).

## Sabotage (docs/sabotage-procedure.md) -- in-process monkeypatch, NO file edited (.scratch/tk106/conf_sabotage.py)
Targets: nary floor/carrier/three-way-refusal, fragment (K) and (L), pin schema-probe outcomes (a target set of 116 (then, 2026-09-26)).
    none                 -> 116 passed in 9.35s
    prod_noop            -> 10 failed, 106 passed   (floor, carrier, 3-way x2, (K) refused, (L) x3, pin ttuDirect x2)
    oracle_noop          -> 8 failed, 108 passed    (floor, carrier, 3-way x2, (K) refused, (L) x3)
    both_noop_inject     -> 11 failed, 107 passed   (instrument control: carrier injected into TTU_USERSET_SCHEMAS)
    prod_derived_exempt  -> 8 failed, 108 passed    (narrowest weakening = pre-TK106 rule; untainted witnesses stay green)
Literal key lines:
    prod_derived_exempt: AssertionError: `derived-tupleset-ttu`'s carrier REFUSED_TUPLESET_SCHEMAS['derived_tupleset_ttu'] is ACCEPTED by ['zanzibar.schema.parse_openfga_schema', 'zanzibar.schema.parse_schema_ast']. The TK106 refusal relaxed, ...
    prod_derived_exempt: AssertionError: [derived_tupleset_ttu/py] backends disagree on a refused shape: {'oracle': 'REFUSED', 'setengine': 'ACCEPTED', 'graph': 'ACCEPTED'}
    oracle_noop:         AssertionError: [derived_tupleset_ttu/py] backends disagree on a refused shape: {'oracle': 'ACCEPTED', 'setengine': 'REFUSED', 'graph': 'REFUSED'}
    both_noop_inject:    AssertionError: `derived-tupleset-ttu` is excluded from the coverage floor as unreachable since TK106 (2026-09-26), but ACCEPTED corpora reach it: ['TTU_USERSET_SCHEMAS:derived_tupleset_ttu']. The exclusion is stale: ...
    (L) under prod_derived_exempt: Failed: DID NOT RAISE ValueError on [GA_PROBE:ttuDirect.derived/derived-tupleset] and [REFUSED_TUPLESET:derived_tupleset_ttu] only
Transcribed into docstrings: nary `test_every_plan_leaf_kind_is_reached_by_some_corpus`, fragment
`test_lean_ttudirect_failures_are_refused_by_both_parsers`.

## Module 6: test_conformance_spec.py (CRLF preserved) -- comment only
- Dated note at `_SPEC_SCHEMAS` that REFUSED_TUPLESET_SCHEMAS is deliberately not a spec family (oracle + set engine
  refuse; no answers to compare with `sem`). The 3 `[derived_tupleset_ttu]` spec tests disappear with the move.
- Touched modules together: spec + nary_strata + fragment + graphadmission pin -> `617 passed in 28.71s`.

## Collected count
- Before: `1038 tests collected in 1.41s`. After: `1081 tests collected in 1.17s` (+43 =
  spec -3, fragment (H) -1, fragment (L) +47 parametrized, (L) anti-vacuity +1; nary_strata net 0).
- MIN_CONF_ALL in formal/verify.sh has zero headroom and is set to the old live count: it must be re-set
  deliberately by the session (upward move; I may not edit verify.sh). FINAL_REVIEW.md's generated counts block
  (doc_counts --generate) is stale too: conf_total, per-file counts, `ttu_userset` 6 -> 5, `spec_scope` 36 -> 35.

Full-directory run launched detached 2026-09-26 (PowerShell Start-Process, pid 27032) -> .scratch/tk106/conf-final.log

## Out-of-scope files that now state something FALSE (I must not edit; session to fix) -- grepped first-hand 2026-09-26
Lean doc comments:
- `formal/lean/ZanzibarProofs/FullScope.lean` GraphAdmission docstring (~:107-112): "LOUD 12, MIXED 2" -> now LOUD 13,
  MIXED 1 (ttuDirect LOUD). The `ttuDirect` bullet (~:122-129) says Python ACCEPTS derived tuplesets and cites
  `_validate_ttu_tuplesets`'s tainted exemption as "Proof scope, not a mirrored refusal" -- false since TK106:
  `src/zanzibar/schema/parser.py::_validate_tuplesets_direct` refuses every non-direct tupleset at parse time.
- `formal/lean/ZanzibarProofs/GraphIndex/AdmissionDecide.lean` module doc (~:16-20): "two MIXED but shadowed by
  W4Fragment" -- now one (storeValid). (`refutes_ttuDirect` itself is fine.)
formal/*.md:
- `formal/ARCHITECTURE.md` ~:183-195: "`ttuDirect` (untainted TTU tuplesets direct-only)", "2 are MIXED (`ttuDirect`,
  `storeValid`...)", "LOUD 12 / MIXED 2 / SILENT 0" -> LOUD 13 / MIXED 1; ttuDirect now covers derived tuplesets too.
- `formal/SEMANTICS.md` ~:224 ("TTU tupleset restriction rule (`_validate_ttu_tuplesets:898`) ... the graph rejects TTU
  tuplesets with computed/rewritten arms") and ~:638-639 ("`ttuDirect` (untainted TTU tuplesets direct-only,
  `_validate_ttu_tuplesets`)"): the enforcing mechanism is now the parse-time `_validate_tuplesets_direct` on BOTH
  parsers, for derived tuplesets too.
- `formal/CORRESPONDENCE.md` ~:1222: "`PDerivedTuplesetTTU`) are untouched by this and remain netted only" -- the leaf
  is now unreachable from any checked parse (netted by the refusal + nary exclusion, not by a differential).
- `formal/HANDOFF.md` ~:393-416: "CLOSED 2026-07-28 by `TTU_USERSET_SCHEMAS['derived_tupleset_ttu']`" -- that corpus
  moved to `REFUSED_TUPLESET_SCHEMAS`; the leaf kind is now excluded from the floor as unreachable (TK106).
- `formal/FINAL_REVIEW.md`: generated counts block stale (conf total 1038 -> 1081, per-file rows for
  test_conformance_fragment.py / test_conformance_spec.py, ttu_userset 6 -> 5, spec_scope 36 -> 35) -> regenerate
  with `python -m formal.conformance.doc_counts --generate` AFTER MIN_CONF_ALL is re-set.
- `formal/verify.sh`: `MIN_CONF_ALL` (zero headroom) must become the new live collected count 1081 (if no other
  session changes conformance collection meanwhile) -- re-measure with --collect-only first.
docs/*.md -- flagged by `doc_counts.check_corpus_count_prose()` (would make `doc_counts --check`, verify.sh step 4e, RED):
    docs/dw1-decidable-w4fragment-2026-09-23.md:48: '36 corpora' [count as it was then; 2026-09-26]
    docs/dw1-decidable-w4fragment-2026-09-23.md:142: '36 curated corpora' [count as it was then; 2026-09-26]
    docs/perf-round6-audit-2026-08.md:628: '6 corpora'       (6 was TTU_USERSET's live size; now 5)
    docs/tk104-graphadmission-scope-2026-09-24.md:72: '36 corpora'
    docs/tk104-graphadmission-scope-2026-09-24.md:284: '36 curated corpora'
  Fix: add a pastness word ('then'/'was') on the line or the two above it (they already carry dates), or drop the
  number. (Live registry sizes now [1, 2, 5, 25, 27, 35].)
Other docs mentioning derived_tupleset_ttu that may read as current: docs/spec-deviations.md,
docs/tk94-derived-userset-corpus-2026-09-22.md (not audited line-by-line). formal/history/* is FROZEN, not flagged.

## FINAL (2026-09-26)
Full directory, detached run (.scratch/tk106/conf-final.log): `1081 passed in 3004.72s (0:50:04)` -- 0 failed, 0 skipped.
Collected: before `1038 tests collected`, after `1081 tests collected`.
No git state changed. No file outside formal/conformance/ edited (scratch probes under .scratch/tk106/conf_*.py, sab-*.log).
