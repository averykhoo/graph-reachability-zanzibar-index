# `TK107`: remove the tainted-tupleset code path that `TK106` made unreachable

**FROZEN 2026-10-05 (`TK107` closed).** Was an ACTIVE-PLAN (`docs/README.md` §3), opened
2026-10-05. Live state is `python scripts/task.py show TK107`, never
this file. Line numbers are as of HEAD `edfa9cf` (2026-10-05) and will rot; the
`file::symbol` cites are the anchors.

Provenance labels: **READ** (first-hand, this session), **REASONED**, **MEASURED** (a run
whose output is quoted), **UNVERIFIED**. No subagent was used for the census.

## § 0 Decision: REMOVE, behind a compile-time refusal (the model's, under `CLAUDE.md` "Who decides")

The row offered "remove (or mark)". Removed, for three reasons.

1. **Equivalence is not at stake.** Since `TK106` both checked parsers refuse a non-direct
   tupleset (`zanzibar_utils_v1.py::_validate_tuplesets_direct`, oracle twin
   `tests/oracle.py::_validate_tuplesets_direct`). A direct-only tupleset mentions no
   relation, so `compute_taint` never taints it (REASONED from
   `zanzibar_utils_v1.py::_mentions`: a `Direct` adds only userset-restriction keys, and a
   userset restriction on a tupleset is refused since `TK108`). So no checked schema reaches
   `PDerivedTuplesetTTU`, and the set engine and oracle never see a schema the graph would
   compile through it.
2. **The only remaining way in is the UNCHECKED parse** (`_parse_schema_ast_unchecked`), used
   by reports, the conformance encoder, `genswarm` witness features, and two conformance
   tests. Leaving the branch there means a hand-built AST compiles through code that no
   differential exercises. The fix is to make the GRAPH COMPILER refuse it too:
   `_validate_ttu_tuplesets` drops its `ts_key not in tainted` exemption, so ANY non-direct
   tupleset raises `UnsupportedByGraphIndex` before plan construction. The plan-builder
   branch is then unreachable from every input, not just from checked parses.
3. **No Lean change is owed.** The Lean tree names `PDerivedTuplesetTTU` only in two comments
   (`GraphIndex/ReconcileCorrect.lean`, READ); there is no twin constructor. The
   `CORRESPONDENCE.md` anchor pin cites one dead symbol,
   `index_v4/processor.py::DeltaProcessor.derived_stored_star_types` (READ, pin line ~350),
   which must leave the map and the pin together.

**Kept, deliberately:**

- `zanzibar_utils_v1.py::_member_types` keeps all its arms. The row (via the TK106 triage
  § 18) listed its Exclusion / Intersection / Computed / TTU arms as dead. They are not
  dead: `compute_taint` -> `_mentions` calls `_member_types` on EVERY TTU, before any
  refusal, and on unchecked ASTs too, and `compute_taint` is differential-pinned to Lean
  (`formal/conformance/test_conformance_fragment.py::test_lean_taint_equals_python_compute_taint`).
  Narrowing it could move a taint verdict. REASONED; not worth the risk for four lines.
- `_assert_ttu_parent_types_cover_admission` keeps its RewriteFilter-to-storage-leaf branch.
  Only the `PDerivedTuplesetTTU` half of its isinstance goes. REASONED: that branch keys
  admission by a TAINTED owner relation, and the check only looks up a TTU's tupleset, which
  is now never tainted, so the branch's entries are never read. It is inert, not wrong, and
  it sits inside a sabotage-pinned invariant
  (`tests/test_ttu_tupleset_parent_types.py::test_compile_refuses_parent_types_narrower_than_admission`),
  so it is left alone.
- Shared helpers used by the live `derived-ttu` path stay:
  `DeltaProcessor._stored_tupleset_subjects`, `::_expand_tupleset_parents`,
  `::tupleset_parents`, `::tupleset_star_types`, and the bulk twins (READ).
- **`P25`-adjacent bridge code: not part of this dead set.** `P25` closed 2026-10-04g
  because the graph REFUSES that shape (`_reject_object_wildcard_scope`). The bridge path its
  row described (`DeltaProcessor._write_derived` -> `WildcardIndex.add_tuple` ->
  `_ensure_bridges`) is shared with every derived write (REASONED from the P25 row text), so
  nothing there is dead because of `TK106`.

## § 1 Census of the dead code (READ 2026-10-05, grep over `*.py` excluding `.scratch/`, `legacy/`)

### Product

| file::symbol | what goes |
|---|---|
| `zanzibar_utils_v1.py::_validate_ttu_tuplesets` | CHANGES: drop the `ts_key not in tainted` exemption; refusal comment/message updated |
| `zanzibar_utils_v1.py::PDerivedTuplesetTTU` | class deleted |
| `zanzibar_utils_v1.py::_build_plan_tree` | TTU arm's tainted-tupleset return |
| `zanzibar_utils_v1.py::_is_pure` | TTU arm's `tupleset in tainted` early return |
| `zanzibar_utils_v1.py::_plan_leaves` | `derived-tupleset-ttu` LeafSpec emission |
| `zanzibar_utils_v1.py::_compile_check_fn`, `::_compile_stars_fn` | `PDerivedTuplesetTTU` arms |
| `zanzibar_utils_v1.py::_plan_deps_and_fanout` | `PDerivedTuplesetTTU` arm (all `'tupleset-ttu'` DependentEdges) |
| `zanzibar_utils_v1.py::_assert_ttu_parent_types_cover_admission` | `PDerivedTuplesetTTU` half of the isinstance |
| `zanzibar_utils_v1.py::LeafSpec.kind`, `::DependentEdge.via` | comments drop the dead values |
| `index_v4/processor.py::_EvalContext.tupleset_ttu_check`, `::tupleset_ttu_stars` | deleted |
| `index_v4/processor.py::DeltaProcessor._ts_leaf_predicates`, `::_derived_stored_split`, `::_split_star_types`, `::_split_parents`, `::derived_stored_parents`, `::derived_stored_star_types`, `::_stored_parent_objects_of_entity` | deleted |
| `index_v4/processor.py::DeltaProcessor._from_chain_keys`, `::_derived_leaf_neg_ids`, `::_leaf_concretes`, `::_live_keys_of` | `derived-tupleset-ttu` branches |
| `index_v4/processor.py::DeltaProcessor` keys-from-deltas loop (the `LeafFamily` arm feeding `'tupleset-ttu'` dependents; the `target_feeders` `'tupleset-ttu'` arm) and `::_fan_out` (`'tupleset-ttu'` arm) | branches; `_fan_out` keeps its `unknown via` AssertionError |
| `index_v4/processor.py` comments: N3-WITHDRAWN note, `_stored_cache_scope` docstring, `_expand_tupleset_parents` docstring | drop the dead names |
| `index_v4/bulk_backfill.py::_BulkEvalContext.tupleset_ttu_check`, `::tupleset_ttu_stars`; `_BulkBackfill._ts_leaf_predicates`, `::_derived_stored_parents`, `::_derived_stored_star_types` | deleted |
| `index_v4/bulk_backfill.py::_BulkBackfill._leaf_concretes`, `::_derived_leaf_neg_ids`, `::_from_chain_keys`, `::_live_keys_of` | `derived-tupleset-ttu` branches |

Every leaf-kind dispatch ends in `raise TypeError(f'unknown leaf kind ...')` (READ), so a
stray `derived-tupleset-ttu` after removal fails LOUD, not open.

### Tests and conformance that pin the dead path (READ)

| file::symbol | change |
|---|---|
| `formal/conformance/test_conformance_nary_strata.py::_REQUIRED_LEAF_KINDS`, `::_REFUSED_LEAF_KINDS` | the kind leaves both; the exclusion mechanism goes |
| `formal/conformance/test_conformance_nary_strata.py::test_derived_tupleset_ttu_carrier_is_refused_and_still_mints_the_leaf` | becomes "refused by every checked parser AND by the graph compiler on the unchecked parse" |
| `formal/conformance/test_conformance_nary_strata.py::test_every_plan_leaf_kind_is_reached_by_some_corpus` | drops the refused-kind exception branch |
| `tests/test_generator_coverage.py::_SITE_COUNTS['plan node classes']` | 8 -> 7 (derived from source) |
| `tests/test_schema_shapes.py` expected-unreached set | drop `plan:PDerivedTuplesetTTU`, `leaf:derived-tupleset-ttu`, `via:tupleset-ttu` if the alphabet no longer derives them |
| `tests/test_reg_tk92_bulk_rel_term.py` enumerator mirror | drop the `derived-tupleset-ttu` branch |
| `tests/genswarm.py::_witness_features` / `::features(checked=False)` | the unchecked compile now raises for every TK106 witness; re-read after the change |
| `formal/CORRESPONDENCE.md` + `formal/correspondence_anchor_pin.txt` | drop `derived_stored_star_types` |

Docstring mentions in `test_ttu_tupleset_parent_types.py`, `test_stored_cache_scope.py`,
`test_backfill_enumeration.py`, `test_bulk_build.py`, `corpus.py` are history; they are
edited only where they describe current code.

## § 2 Order

1. The compile-time refusal plus a positive pin that the graph compiler refuses a tainted
   tupleset on the unchecked parse. Sabotage: restore the exemption, watch the pin go red.
2. Delete the compiler half, then the processor and bulk halves.
3. Fix the pins in § 1, run the affected modules, then the full ten-phase gate.

## § 3 Results (MEASURED 2026-10-05 unless marked)

**Landed.** Every symbol in § 1's product table is deleted or changed as listed:
`zanzibar_utils_v1.py` -62/+22, `index_v4/processor.py` ~-230, `index_v4/bulk_backfill.py`
~-60 (git diff --stat). `_member_types` is untouched (§ 0). Leaf-kind dispatches still end in
`raise TypeError`, and `_fan_out` still ends in `AssertionError('unknown dependency via')`.

**Sabotage of the new pin, step 1** (exemption restored at the compiler site only). The
FIRST attempt matched its anchor TWICE (the parse-time `_validate_tuplesets_direct` carries
the same condition), so the script's `count == 1` assert stopped it and the "1 passed" it
printed was the unmutated tree. That is an instrument failure, caught, not evidence. The
retry anchored on the condition plus the following `raise UnsupportedByGraphIndex(`::

    E       Failed: DID NOT RAISE UnsupportedByGraphIndex
    1 failed in 0.59s

**Mutation sweep** of `_validate_ttu_tuplesets`' tupleset condition (`.scratch/tk107_sweep.py`,
seven modules: `test_conformance_nary_strata`, `test_graphadmission_scope_pin`,
`test_pure_union_ttu`, `test_boolean_compile`, `test_tk116_oracle_only_setengine`,
`test_generator_coverage`, `test_refused_shape_comments`). Run 1, before the
`test_graphadmission_scope_pin` pin existed, without that module::

    M0 control (no change): rc=0 | 156 passed
    M1 restore tainted exemption: rc=1 | 1 failed  [nary_strata carrier test]
    M2 refuse tainted only: rc=0 | 156 passed | []        <- SURVIVED
    M3 check deleted: rc=1 | 1 failed  [nary_strata carrier test]

M2 showed the UNTAINTED half of the compile refusal was unpinned on the unchecked path. That
gap is older than TK107: the TK106 rewrite of `test_pure_union_ttu` moved its pin to the
parse refusal. Fixed by
`formal/conformance/test_graphadmission_scope_pin.py::test_ttudirect_probe_is_refused_by_the_graph_compiler_on_the_unchecked_ast`,
one row per half, which asserts which half each probe covers. Run 2::

    M0 control (no change): rc=0 | 223 passed
    M1 restore tainted exemption: rc=1 | 2 failed  [nary_strata carrier; scope_pin derived row]
    M2 refuse tainted only: rc=1 | 1 failed  [scope_pin untainted row]
    M3 check deleted: rc=1 | 3 failed  [all three]

**Pins that moved, each re-measured, not differenced:**
- `tests/test_generator_coverage.py::_SITE_COUNTS`: leaf kinds 5->4, plan node classes 8->7,
  via kinds 4->3 (printed `genswarm.DERIVATIONS`). Alphabet 51->48, universe 1275->1128.
- `_CELL_FLOOR_WITH_REJ` 820->720: enumerator 685 (K<=2) / 701 (K<=3), UNCHANGED, with
  witnesses 760 (was 866). The lost cells came from compiling TK106 witnesses on the
  unchecked AST, a compile that no longer exists.
- The bare `> _BASELINE_CELLS * 1.5` became `_MIN_GAIN_OVER_BASELINE = 1.4`. The baseline
  was RE-MEASURED in the new universe by replaying `tests/test_hypothesis.py` at `1cbaad0`
  through today's `genswarm.features` (`.scratch/tk107_baseline.py`, derandomized): 514
  (614 draws accepted, 596 refused). Instrument control: 158 cells at 1 draw per generator,
  514 already at 20. The ratio is 760/514 = 1.48 (was 1.68).
- `tests/genswarm.py::_witness_features`: a TK106 witness now carries its AST features plus
  `ttu.ts:tainted` / `ttu.target:tainted` from the PRODUCTION `compute_taint` on the
  unchecked AST. `features(checked=False)` was deleted.
- `tests/test_schema_shapes.py` expected-unreached: the three deleted features left it.
- `formal/conformance/test_conformance_nary_strata.py`: `_REQUIRED_LEAF_KINDS` lost the kind;
  `_REFUSED_LEAF_KINDS` and `_unchecked_leaf_kinds` were deleted; the carrier test was renamed
  `..._is_refused_by_every_parser_and_the_graph_compiler`.
- `formal/CORRESPONDENCE.md`: the channel-list row (`_map_deltas_to_keys` / `_fan_out`) and
  the RC2 star-parent row were rewritten; the other 11 flagged rows were re-read and describe
  nothing deleted. `formal/correspondence_anchor_pin.txt` was regenerated: 486/486 match;
  removed `_stored_parent_objects_of_entity` and `derived_stored_star_types`.

**Not done (docs on hold until TK120, user 2026-10-04c).** Live docs that still name deleted
symbols: `docs/architecture/derived-predicates.md` (plan-node list), and
`docs/architecture/r4bf-bulk-backfill-design.md` (`derived_stored_parents`). `formal/HANDOFF.md`,
`formal/ARCHITECTURE.md`, `formal/SEMANTICS.md`, and `docs/design/generator-coverage/*` also
mention them; not yet triaged for whether they describe current code or history.
