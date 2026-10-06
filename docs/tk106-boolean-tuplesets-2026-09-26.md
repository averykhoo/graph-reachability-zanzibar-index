# `TK106`: a `from`-tupleset must be direct-only (boolean and computed tuplesets are refused)

**ACTIVE-PLAN (`docs/README.md` §3), opened 2026-09-26 (session `2026-09-26b`).** Corrections
are appended dated at the top. FROZEN when `TK106` closes. Live state is
`python scripts/task.py show TK106`, never this file. Figures were measured on `2026-09-26`
against HEAD `9d1bedf` plus the working-tree diff of sessions `2026-09-26` and `2026-09-26b`.

**2026-10-06 (`TK120`):** the code moved into the `src/zanzibar/` package and lost its version suffixes after this doc was written; its paths and class names are the OLD ones. Key: `docs/architecture/overview.md` § "Renamed in TK120".

Provenance labels: **READ** (first-hand, this session), **REASONED**, **MEASURED** (a run
whose output is quoted), **UNVERIFIED**. No subagent was used.

## § 0 The decision (the user's, 2026-09-26)

"Okay yes let's close block this shape then". Refuse a boolean tupleset, as OpenFGA does:
"the relation is referenced in at least one tupleset and thus must be a direct relation"
(`pkg/typesystem/typesystem.go::isUsersetRewriteValid`, READ 2026-09-26 by the previous
session). The reason, the five blocked patterns and their rewrites are on the row.

## § 1 Design decisions taken in-session (the model's, under CLAUDE.md "Who decides")

**D1: refuse at PARSE time in both parsers, not at graph compile time.** READ:
`setengine/engine.py::SetEngine.__init__` catches `UnsupportedByGraphIndex` from
`compile_ruleset` and DEGRADES to a ruleset-less, oracle-only mode. So the row's map,
which drops the `ts_key not in tainted` exemption in
`zanzibar_utils_v1.py::_validate_ttu_tuplesets`, would have made only the graph refuse. The
set engine and the oracle would still have accepted the schema, with `from` silently
ignoring the boolean arm. That is the "graph refuses, set engine accepts" shape the
equivalence goal counts as a divergence. The refusal is therefore a model-level rule, like
`ASK-1`: `zanzibar_utils_v1.py::_validate_tuplesets_direct`, called from `parse_schema_ast`
and `parse_openfga_json`, and the oracle's independent twin
`tests/oracle.py::_validate_tuplesets_direct`, called from `oracle.parse_schema_ast`. The
unchecked parses (`_parse_schema_ast_unchecked`, `oracle.parse_schema_ast_unchecked`) do
NOT refuse, so the reports and the conformance encoder can still see such a schema.

**D2: the rule covers UNTAINTED computed tuplesets too** (`parent: [folder] or other`,
`parent: [folder] or parent from up`). This is OpenFGA's rule as written, and it is the
same bug: `from` walks stored tuples, so the computed arm was silently ignored. Before the
change the graph refused this form (`_validate_ttu_tuplesets`, `UnsupportedByGraphIndex`)
while the set engine degraded past it and answered. REASONED: widening fixes a divergence
rather than narrowing a working feature. `_validate_ttu_tuplesets`'s directs-only branch
becomes an unreachable last line of defence on the checked-parse path.

**D3: userset restrictions in tuplesets (`parent: [folder#member]`) are NOT folded in.**
OpenFGA refuses them too, and they have the same graph-refuses / set-engine-degrades gap
(`_validate_ttu_tuplesets`, READ). They are outside what the user approved for this item,
so they are left as a follow-up (to be filed as a row). Wildcard restrictions
(`[folder:*]`, star tuplesets) stay legal by `ASK-2`.

## § 2 Probe: both parsers refuse the five patterns (MEASURED 2026-09-26)

`.scratch/probe_tk106.py`, one schema per pattern, over `zanzibar_utils_v1.parse_schema_ast`
and `tests/oracle.py::parse_schema_ast`:

```
1 but-not                prod=REFUSE (tupleset must be direct) oracle=REFUSE (tupleset must be direct)
2 and                    prod=REFUSE (tupleset must be direct) oracle=REFUSE (tupleset must be direct)
3 but-not-direct(RC1)    prod=REFUSE (tupleset must be direct) oracle=REFUSE (tupleset must be direct)
4 ref-to-boolean         prod=REFUSE (tupleset must be direct) oracle=REFUSE (tupleset must be direct)
5a computed-union        prod=REFUSE (tupleset must be direct) oracle=REFUSE (tupleset must be direct)
OK direct                prod=accept                           oracle=accept
OK union-directs         prod=accept                           oracle=accept
OK star                  prod=accept                           oracle=accept
```

(A 5b nested-`from` probe was refused for a dangling target, a defect in the probe schema,
not in the rule; it is to be re-probed with a declared target.)

## § 3 Breakage census (PENDING)

Full `tests/` and `formal/conformance/` with the refusal in place,
`--continue-on-collection-errors`. First attempt without that flag stopped at collection:
`tests/test_boolean_compile.py` and `tests/test_zanzibar_utils.py` build a module-level
schema whose `doc#non_labels` tupleset has boolean arms (`unmatchable_conds`).

### § 3a Fixture corpus: 2 of 18 refused (MEASURED 2026-09-26)

Every file in `tests/fga_schemas/` through the checked parse (`parse_schema_ast`, or
`parse_openfga_json` for `.json`). All others accept.

```
demorgans_law_1.fga   REFUSE  doc#unmatchable_conds: 'required_by' from 'non_labels': a tupleset must be direct ...
tupleset_shapes.fga   REFUSE  doc#via_intersection: 'viewer' from 'approved_parent': a tupleset must be direct ...
```

- `tupleset_shapes.fga` is made only of the blocked shapes (`approved_parent: [folder] and
  vetted`, `mixed_parent: [folder] but not [doc]`), so it has no legal arm left. It is RC1's
  only regression pin (`tests/test_schema_shapes.py` module docstring); RC1's shape is now
  unreachable from any parse.
- `demorgans_law_1.fga` chains three `from`s over boolean tuplesets
  (`unmatchable_conds: required_by from non_labels`, `matched_roles: assigned from
  matchable_conds`, `matched_users: granted from matched_roles`). READ:
  `tests/test_processor.py` already pins that chain as CONSTANTLY EMPTY ("no STORED
  non_labels tuple"). The fixture's evident intent is computed-tupleset semantics, which
  neither this repo nor OpenFGA has, so it silently evaluated to nothing. This is the bug
  TK106 closes, in its plainest form. REASONED: the fixture's other role (exercising
  residue algebra on `non_labels`, a star-minus-concrete `but not`) does not need the
  `from` chain and can be kept by dropping the three `from` relations.

### § 3b `tests/` census (MEASURED 2026-09-26, 33 min, run concurrently with § 3c)

`python -m pytest tests/ -q -p no:cacheprovider -rfE --continue-on-collection-errors`:

```
68 failed, 1166 passed, 9 skipped, 28 errors in 2008.13s (0:33:28)
```

(The 9 skips are this bare run's own; the gate's tiles run with zero. Not investigated.)
Two modules fail to COLLECT and so contribute nothing to the counts:
`test_boolean_compile.py` and `test_zanzibar_utils.py` (module-level `demorgans_law_1`).
Per module (FAILED/ERROR lines from the short summary):

```
26 ERROR  test_schema_shapes.py         (module fixture `driven` loads tupleset_shapes.fga)
13 FAILED test_generator_coverage.py
11 FAILED test_ttu_tupleset_parent_types.py
 9 FAILED test_hypothesis.py
 5 FAILED test_star_admitting_intersection.py
 5 FAILED test_schema_shapes.py
 4 FAILED test_pure_union_ttu.py
 3 FAILED test_backfill_enumeration.py
 2 each   test_userset_bridge_release_leak.py, test_stored_cache_scope.py, test_schema_ast.py,
          test_reads.py, test_processor.py, test_matrix.py, test_lookup_oracle.py,
          test_compile_snapshot.py, test_bulk_build.py
 1 ERROR  test_zanzibar_utils.py, test_boolean_compile.py (collection)
```

Classified by each failure section's text (`.scratch/tk106/classify.py`): **86 contain
`tupleset must be direct`**, i.e. the test itself builds a now-refused schema. The other
3 are knock-on generator floors, not refusals:

```
test_every_alphabet_feature_is_hit_or_rejection_explained: 7 alphabet feature(s) are neither HIT by the enumerator nor carried by a rejection witness
test_enumerator_cell_coverage_floor: enumerator cell coverage 508/1275 is below the floor 800 (measured 841 on 2026-08-10)
test_swarm_campaign_reaches_cells_and_never_starves_a_switch: swarm campaign reached 273 cells at 120 draws, floor 430
```

REASONED: the drop from 841 to 508 is not 333 cells of real loss. `ts_boolean`, `ts_negonly`
and `ts_computed` now yield ONLY refused configs, and every other feature co-occurring
in those configs is lost with them. The fix is in the generator (stop generating a refused
shape except as a rejection witness), then a deliberate re-measure of the floors.

### § 3c `formal/conformance/` census (MEASURED 2026-09-26, 46 min, concurrent with § 3b)

```
14 failed, 1024 passed in 2742.37s (0:45:42)
```

10 of the 14 failure sections contain `tupleset must be direct`. Failing ids (short summary):

```
test_conformance_fragment.py::test_lean_taint_equals_python_compute_taint[TTU_USERSET:derived_tupleset_ttu]
test_conformance_fragment.py::test_reported_failures_are_refused_by_both_parsers[TTU_USERSET:derived_tupleset_ttu]
test_conformance_nary_strata.py::test_every_plan_leaf_kind_is_reached_by_some_corpus
test_conformance_nary_strata.py::test_harness_wide_wildcard_userset_floor
test_conformance_nary_strata.py::test_derived_tupleset_ttu_corpus_features
test_conformance_nary_strata.py::test_zero_coverage_shapes_three_way[derived_tupleset_ttu-py|roaring]
test_conformance_spec.py::test_spec_vs_oracle|test_spec_vs_setengine|test_oracle_vs_setengine[derived_tupleset_ttu]
test_graphadmission_scope_pin.py::test_schema_probe_outcome_still_holds[ttuDirect.derived/derived-tupleset]
test_graphadmission_scope_pin.py::test_schema_probe_outcome_still_holds[ttuDirect.untainted/tupleset-with-computed-arm]
test_grid_independence.py::test_declared_keys_agree_on_every_corpus
test_leaf_namespace_correspondence.py::test_no_corpus_rule_mints_a_leaf_named_ttu_target
```

Almost all of it is ONE corpus entry, `derived_tupleset_ttu` (`formal/conformance/corpus.py`),
plus the two `ttuDirect` probes the row predicted.

## § 4 Generator (`tests/genswarm.py`): cell loss attributed (MEASURED 2026-09-26)

Instrument: `.scratch/tk106/probe_cells.py`, which recomputes `_enumerate` of
`tests/test_generator_coverage.py` (K<=2, compile-only) for HEAD's `genswarm.py` with
`_validate_tuplesets_direct` patched to a no-op, against the working `genswarm.py` with the
refusal live. It classifies each lost cell: does it contain a feature that no config
reaches any more (lost by design), or only still-reached features (generator gap)?

| step | new cells | lost | by design | GAP | gained |
|---|---|---|---|---|---|
| refusal only, genswarm untouched (census) | 508 | - | - | - | - |
| swarm grammar direct-only + witnesses | 575 | 257 | 249 | 8 | 24 |
| `ts_boolean` -> legal `[..] or [doc]` union, `r8` `and` under it too | 623 | 234 | 229 | 5 | 49 |
| `r8` a derived union, `r9: [user] but not r8` (second stratum) | **685** | 229 | 229 | **0** | 106 |

HEAD's own figure under this instrument is **808**, not the 841 the floor's comment records
from 2026-08-10: 33 cells of drift before this item (ASK-1's refusals are one known cause).
The features HIT before and not now are exactly the refused shapes and their compiled
consequences: `leaf:derived-tupleset-ttu`, `plan:PDerivedTuplesetTTU`, `ttu.ts:Computed`,
`ttu.ts:Exclusion`, `ttu.ts:Intersection`, `ttu.ts:neg-only-type`, `ttu.ts:tainted`,
`via:tupleset-ttu`. `ttu.ts:Union` looked lost at step 2 but is LEGAL (`[a] or [b]`); it
was reached before only through refused shapes, and the step-3 arm restores it.

Generator changes (all in `tests/genswarm.py`):

- the swarm's tupleset grammar is direct-only (`leaf` / `union` of Directs; no `Computed`
  leaf; the neg-only arm is no longer applied, and `_tupleset_body` was removed);
- `witness`: `ts_computed` and `ts_negonly` stay as refusal-proving arms, the precedent
  `ts_undeclared` set for ASK-1; `ts_boolean` now builds the legal union; under
  `body_boolean` or `ts_boolean`, `r8: ([user] and r0) or [user]` and `r9: [user] but not r8`;
- `REJECTION_WITNESSES`: `tupleset-rewritten-arms` and `tupleset-is-itself-a-ttu` move to
  `ValueError` / `TUPLESET_MUST_BE_DIRECT`; new `tupleset-intersection` and
  `tupleset-neg-only-type`; `owc-on-derived-relation` RETIRED (its family was reached only
  through `ts_boolean` + `owc`; the refusal stays pinned by
  `tests/test_boolean_compile.py::test_object_wildcard_on_derived_rejected`);
- `_witness_features`: a `TUPLESET_MUST_BE_DIRECT` witness is described by the real
  compiler on the unchecked AST (`features(checked=False)`), because the features it
  exempts are compiled ones. It falls back to `ast_features` when the graph compiler also
  refuses (an untainted computed tupleset).

## § 5 Fix decisions (the model's, 2026-09-26b; per-test detail in the triage doc)

**D4: retire `tests/fga_schemas/tupleset_shapes.fga`** and its golden
`tests/snapshots/compiled_ruleset/tupleset_shapes.fga.txt` (`git rm`). Every relation in
it is a refused shape. Its RC1 pin is replaced by refusal pins, and its features
(`ttu.ts:Intersection`, `ttu.ts:neg-only-type`) are carried by the genswarm witnesses
`tupleset-intersection` and `tupleset-neg-only-type`.

**D5: TRIM `tests/fga_schemas/demorgans_law_1.fga` to its legal core, not retire it:**
`_all_attrs: [attr:*]`, `labels: [attr]`, `non_labels: _all_attrs but not labels`
(the `role`/`cond` types and the three `from` relations are gone). Reasons:
- the `from` chain was constantly empty, so it never discriminated anything;
- the `non_labels` star-minus-concrete residue is the only corpus asserted to reach
  `test_bulk_build.py`'s check (e), an edge-free explicit rc=0 node;
- keeping it keeps `test_compile_snapshot.py::MIN_FIXTURES = 15` true without a lowering.

The file keeps its name, which is now historical; its golden is regenerated deliberately,
with a `docs/spec-deviations.md` entry.

**D6: work split.** Delegated to write-capable agents, each confined to its own files and
each reporting to `.scratch/tk106/agent-<name>.md`:
- the `tests/test_hypothesis.py` / `tests/test_lookup_oracle.py` strategy constraint;
- the `formal/conformance/` fixes.

The session does the rest first-hand, including every RC2 / memo / RC1 pin rewrite and its
sabotage.

## § 6 RC1 / RC2 pins moved to the live path (MEASURED 2026-09-26, first-hand)

The hypothesis-strategy agent found (`docs/tk106-agent-reports-2026-09-26.md` § A, S4) that,
after the trim, NO generated tupleset is tainted, so sabotaging RC2's live fix site leaves
the property tests GREEN. RC2 is therefore pinned only by
`tests/test_ttu_tupleset_parent_types.py`, rewritten so that a stored `doc:*` parent flows
through the LIVE `derived-ttu` path: `parent: [folder, doc, doc:*]` with `folder#viewer`
derived (`[user] but not banned`) and `doc#viewer: [user]`. RC1's class moves to a
multi-type tupleset under a derived target (`parent: [folder, doc]`, both viewers derived).

Probe `.scratch/tk106/probe_rc_new.py` runs `_answers` (oracle, graph, both set engines),
first as a baseline and then under two sabotages of the RC2 fix site in
`index_v4/processor.py`:
- (A) `_stored_tupleset_subjects` drops star parents;
- (B) `_expand_tupleset_parents` ignores `star_types`.

Literal output:

```
--- BASELINE
  RC2 star inherited             oracle=True graph=True sets=[True, True]
  RC2 star access(neg)           oracle=False graph=False sets=[False, False]
  RC2 concrete inherited         oracle=True graph=True sets=[True, True]
  RC2 concrete access(neg)       oracle=False graph=False sets=[False, False]
  RC1c doc-parent inherited      oracle=True graph=True sets=[True, True]
  RC1c doc-parent access(neg)    oracle=False graph=False sets=[False, False]
  RC1c no-parent inherited       oracle=False graph=False sets=[False, False]
--- SABOTAGE A: _stored_tupleset_subjects drops star parents
  RC2 star inherited             oracle=True graph=False sets=[True, True]
  RC2 star access(neg)           oracle=False graph=True sets=[False, False]
  RC2 concrete inherited         oracle=True graph=True sets=[True, True]
  RC2 concrete access(neg)       oracle=False graph=False sets=[False, False]
  RC1c doc-parent inherited      oracle=True graph=True sets=[True, True]
  RC1c doc-parent access(neg)    oracle=False graph=False sets=[False, False]
  RC1c no-parent inherited       oracle=False graph=False sets=[False, False]
--- SABOTAGE B: _expand_tupleset_parents ignores star_types
  RC2 star inherited             oracle=True graph=False sets=[True, True]
  RC2 star access(neg)           oracle=False graph=True sets=[False, False]
  RC2 concrete inherited         oracle=True graph=True sets=[True, True]
  RC2 concrete access(neg)       oracle=False graph=False sets=[False, False]
  RC1c doc-parent inherited      oracle=True graph=True sets=[True, True]
  RC1c doc-parent access(neg)    oracle=False graph=False sets=[False, False]
  RC1c no-parent inherited       oracle=False graph=False sets=[False, False]
--- RESTORED
  RC2 star inherited             oracle=True graph=True sets=[True, True]
  RC2 star access(neg)           oracle=False graph=False sets=[False, False]
  RC2 concrete inherited         oracle=True graph=True sets=[True, True]
  RC2 concrete access(neg)       oracle=False graph=False sets=[False, False]
  RC1c doc-parent inherited      oracle=True graph=True sets=[True, True]
  RC1c doc-parent access(neg)    oracle=False graph=False sets=[False, False]
  RC1c no-parent inherited       oracle=False graph=False sets=[False, False]
```

Both sabotages reproduce RC2's original signature on the new schema, in BOTH directions.
The positive `from` fails closed, and the negated `from` fails OPEN (graph True, oracle
False). The concrete-parent controls and the RC1-class cases stay green under both, so the
pins discriminate the star arm alone.

Module-level sabotage of the REWRITTEN `tests/test_ttu_tupleset_parent_types.py`
(`.scratch/tk106/sab_rc_module.py`, in-process monkeypatch + `pytest.main`), 2026-09-26:

```
== A  (_stored_tupleset_subjects returns no star types)
FAILED ...::test_rc2_star_stored_parent_on_derived_ttu_is_a_ttu_parent
FAILED ...::test_rc2_star_stored_parent_dropped_is_an_authorization_fail_open
2 failed, 11 passed
== B  (_expand_tupleset_parents ignores star_types)
FAILED ...::test_rc2_star_stored_parent_on_derived_ttu_is_a_ttu_parent
FAILED ...::test_rc2_star_stored_parent_dropped_is_an_authorization_fail_open
2 failed, 11 passed
== C  (_member_types drops 'doc' for doc#parent: RC1's mechanism)
8 failed, 5 passed   (every derived-path test; the compile-time invariant refuses)
restored: 13 passed
```

`tests/test_stored_cache_scope.py::test_star_expansion_is_not_frozen_by_the_memo` moved to
the same live-path schema (the `derived_stored_parents` route is dead and was dropped).
Re-sabotaged 2026-09-26 (`.scratch/tk106/sab_memo.py`): memoizing `_expand_tupleset_parents`
(S2), and separately `_instances_of_type` (S2c), inside the scope each gave
`AssertionError: FROZEN STAR EXPANSION ... tupleset_parents did not see it`, `1 failed`.

`tests/test_bulk_build.py`'s `rc2_star_tupleset` corpus moved to the same live-path schema
(plus a `folder` parent). Re-sabotaged 2026-09-26 (`.scratch/tk106/sab_bulk.py`): dropping
star parents from the BULK `_stored_tupleset_subjects` alone, and separately from the
processor's alone, each gave `AssertionError: [rc2_star_tupleset] snapshot_rows differ`,
`1 failed`. So each copy of the RC2 fix site stays pinned on the bulk path.

## § 7 The userset-bridge release leak pin survives on a legal schema (MEASURED 2026-09-26)

The triage marked `tests/test_userset_bridge_release_leak.py` as a LOST pin, because its
module docstring said the leak needs a DERIVED tupleset. First-hand probe
`.scratch/tk106/probe_leak.py` re-implements `DeltaProcessor._gc_subject_node` in its
PRE-FIX order (strip bridges, then demote; the 2026-08-21 fix is demote-then-strip). It
measures add-then-remove row leakage on the filed schema (refusal patched off) and on three
legal candidates:

```
--- FIXED ORDER
  ORIGINAL (refusal off)                           leaked (nodes, edges) = (0, 0)
  A body-but-not + star tupleset TTU elsewhere     leaked (nodes, edges) = (0, 0)
  B r1 = (r0 from parent or [doc#r0]) but not blk  leaked (nodes, edges) = (0, 0)
  C r1 = r0 from parent or ([doc#r0] but not blk)  leaked (nodes, edges) = (0, 0)
--- SABOTAGE: pre-fix order
  ORIGINAL (refusal off)                           leaked (nodes, edges) = (2, 1)
  A body-but-not + star tupleset TTU elsewhere     leaked (nodes, edges) = (2, 1)
  B r1 = (r0 from parent or [doc#r0]) but not blk  leaked (nodes, edges) = (2, 1)
  C r1 = r0 from parent or ([doc#r0] but not blk)  leaked (nodes, edges) = (2, 1)
```

So the fix is still reachable. The docstring's "derived tupleset is load-bearing" was too
narrow: what matters is a derived relation recording the bridged userset subject. The pins
moved to candidate A. Module run under the pre-fix order (`.scratch/tk106/sab_leak.py`):
`2 failed` (both pins); with the fix: `2 passed`.

## § 8 `tests/test_tupleset_must_be_direct.py`: mutation sweep (MEASURED 2026-09-26)

The new module has 75 tests:
- blocked patterns × construction paths, 6 × 7 = 42;
- legal controls × paths, 4 × 7 = 28;
- the JSON front-end, 1;
- rewrite-preserves-answers pins, 4.

The refusal was mutated in-process (`.scratch/tk106/mut_refusal.py`; the 4 rewrite pins
deselected), one mutant per run:

| mutant | what | result |
|---|---|---|
| M0 | none (control) | `71 passed` |
| M1 | production `_validate_tuplesets_direct` -> no-op | `31 failed`: 6 patterns x 5 production paths + JSON |
| M2 | oracle twin -> no-op | `12 failed`: 6 patterns x the 2 oracle paths, nothing else |
| M3 | production `_directs_only` accepts `but not` | `11 failed`: patterns 1 and 3 x 5 production paths + JSON |
| M4 | production re-exempts TAINTED tuplesets (the pre-TK106 rule) | `21 failed`: patterns 1-4 (tainted) x 5 production paths + JSON; 5a/5b (untainted) still refused |
| M5 | oracle twin accepts `and` | `2 failed`: pattern 2 x the 2 oracle paths |

Every mutant is caught, and caught only where it should be. The independence of the two
parsers is visible: M1 leaves the oracle paths green, and M2 leaves the production paths green.
