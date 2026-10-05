# `.scratch/` salvage, 2026-10-05 — what the pre-`TK120` sweep found nowhere else

**FROZEN 2026-10-05 — provenance, not a living document.** Status lines below are
as-of-then and may now be false; live state is the tree (`task.py show <id>`).
Corrections are appended dated at the top, never edited in.

**Provenance.** The `.scratch/` directory (285 files, excluding `__pycache__`) was swept
before the `TK120` restructure, because a re-layout would make every path in it stale. A
read-only subagent classified each file as DERIVABLE / SUPERSEDED / SALVAGE / UNCLEAR, with
evidence (its report counted 154 SUPERSEDED, 128 DERIVABLE, 3 SALVAGE, 0 UNCLEAR). The
session READ all three SALVAGE files first-hand before transcribing them here. The rest went
to the Windows Recycle Bin. Everything below came from `.scratch/wf-0927/`, the crash bag of
the 2026-09-27/28 workflow run that built `P10`, `P12`, `P13` and `TK96`.

Both target docs are FROZEN
([`docs/p12-severity-sign-revert-probe-2026-09-27.md`](../p12-severity-sign-revert-probe-2026-09-27.md),
[`docs/p10-scope-audit-2026-09-27.md`](../p10-scope-audit-2026-09-27.md)), so the findings
land here and the closed `P12` and `P10` rows point at this file.

---

## 1. `P12`: the adversarial verifier's own mutation sweep (V0–V8)

Source: `wf-0927/P12-verify.md` (verifier log, 2026-09-28). Tracked before this file: only
the verdict, "ACCEPT, with an independent literal revert" (`docs/history/session-log.md`,
the `P12` entry). The per-mutation table and its two GREEN results existed only in
`.scratch/`.

The verifier re-measured the pre-fix export independently. Its figures match the doc:

```
B  states=256  queries=3072  div=36  (access OPEN 12, viewer CLOSED 24)
D                            div=30  (OPEN 6, CLOSED 24)
E  queries=3840              div=42  (OPEN 6, blocked CLOSED 12, viewer CLOSED 24)
today's tree + --sabotage-middles, paranoia off, B: div=36 OPEN 12 / CLOSED 24; unsabotaged: 0
```

Sweep over the `P12` pins (`tests/test_p12_severity_sign.py`, 14 collected then). The
verbatim verdicts:

| id | mutation | result |
|---|---|---|
| V0 | none (control) | 14 passed |
| V1 | middle left unbridged | 3 failed (live x3) |
| V2 | `break` vs `continue` | **GREEN, INERT**: `crossable_shapes == [('folder','viewer')]` for B/D/E, so `break` == `continue` on every fixture |
| V3 | node-wise middle | 3 failed (live x3) |
| V4 | I14 witness node-wise | 2 failed (full/fixpoint abort) |
| V5 | `full` skips the pre-commit check | 1 failed (full abort) |
| V6 | oracle built without the last tuple (the consumer grant) | **GREEN, equivalent mutant**: every queried oracle value is the same with or without it (negated `False` because the subtrahend holds; positive independent) |
| V7 | `ALL_SETOPS[:0]` | **GREEN, unreachable**: `setengine/setops.py::ALL_SETOPS` is `[PySets] + [...]`, never empty |
| V8 | oracle without the OWC grant | 11 failed |

**V2 is the finding.** It is a sabotage that passed for a structural reason: no `P12`
fixture has more than one crossable shape, so nothing distinguishes stopping at the first
crossable shape from visiting all of them. V6 and V7 are explained and need nothing. V2 is
an unpinned degree of freedom. Closing it needs a fixture with two crossable shapes
(REASONED; not attempted).

## 2. `P10`: per-sub-case differential coverage of the admitted `W4Fragment`

Source: `wf-0927/p10-verify-silent-fields-differential-coverage-2.md` (verifier log) and
`wf-0927/probes/silent-fields-differential-coverage/verify2/agg_final.txt` (its aggregate),
2026-09-28. Tracked before this file: only `records=502, failed=0` in the `P10` doc.

**Verdict, verbatim: "audit UPHELD, SOUND".** Every admitted sub-case, split finer than
`zanzibar_utils_v1.py::w4_fragment_report` can split it (the report is field-level only, so
it cannot separate `bareStar` into objWildcard vs usersetStar, or `computedOrDirect` into a
TTU onto a derived vs an untainted target), has at least one deterministic test in which the
graph ANSWERED and the oracle said True on a state carrying that sub-case. The instrument
was a pytest plugin (`v2plug.py`) that labelled sub-cases at `Oracle.check` time and counted
`WildcardIndex.check` calls.

**Correction it made to the audit:** `tests/test_matrix.py::test_matrix_4way_union_wildcard[0]`
covers `bareStar.objWildcard`, NOT the userset-star subject. `bareStar.usersetStar` is
covered by
`formal/conformance/test_conformance_nary_strata.py::test_zero_coverage_shapes_three_way[wildcard_userset-py|roaring]`
and `tests/test_schema_shapes.py::driven` (`_WILDCARD_USERSET_CROSS_POOL`).

**Controls:** 69/180 graph+oracle records carried NO label, so the plugin did not label
everything. A self-test fired each label on its own `SCOPE_PROBES` fixture, and the
in-scope control gave `[]`. The 4 plugin errors were all in
`tests/test_tk108_userset_tupleset_rewrite.py` (an Oracle built without `__init__` for
REFUSED shapes), which does not touch admitted coverage. Runs: `264 passed in 1722.30s`
(named modules), `238 passed in 513.17s` (extra).

**The residual (REASONED, verifier): durability.** The coverage is incidental. No
`W4FRAGMENT_SCOPE` row names its differential test, and no row owns tying them together
(the `P10` doc §7 "optional LATER hardening"). The map below is the input to that work. It
is a 2026-09-28 snapshot, taken before `TK106`/`TK107`/`TK108` changed the tupleset
surface. Test ids may have moved since; re-measure before relying on one.

```
records=502 passed_with_graph_checks=232 errs=4 failed=0
label                     driven  with_true  first tests carrying it (up to 4 listed)
computedOrDirect            41      37   test_bulk_build::..incremental[boolean], [rc2_star_tupleset];
                                         test_cascade_fixpoint_tier::test_the_suppressed_reconcile_makes_the_store_oracle_wrong;
                                         test_connectedstore::test_connected_store_parity_walk[0]
cod.ttuOntoDerived          36      32   (same four as computedOrDirect)
cod.ttuOntoUntainted         5       5   test_lookup_oracle::test_graph_from_chain_userset_through_boolean_ttu_arm;
                                         test_self_referential_tuples::test_pderived_recording_promote_demote_hysteresis;
                                         test_tupleset_must_be_direct::test_rewrite_keeps_the_old_answers[1-but-not], [2-and]
directArmsBare              10       9   conformance/test_conformance_remove::test_graph_full_churn_restores[derived_userset_subject],
                                         ::test_graph_remove_sequences[derived_userset_subject];
                                         test_bulk_build::..incremental[derived_member];
                                         test_lookup_oracle::test_graph_userset_member_through_granted_userset_over_derived
directArmsConcrete           6       6   test_lookup_oracle::test_graph_userset_subject_through_derived_wildcard_gap;
                                         test_parity_engine::test_parity_engine_scenarios[exclude_star_subtrahend], [public_but_not_blocked];
                                         test_schema_shapes::test_drives_clean_across_every_backend[heterogeneous_tupleset]
computedOnlyOperands        21      21   test_cascade_fixpoint_tier::test_the_suppressed_reconcile_makes_the_store_oracle_wrong;
                                         test_irrelevant_alternatives::test_iia_hypothesis;
                                         test_lookup_oracle::test_graph_from_chain_userset_through_boolean_ttu_arm,
                                         ::test_graph_userset_subject_through_derived_wildcard_gap
noUnionDirects               8       8   conformance/test_conformance_remove (both derived_userset_subject cases);
                                         test_lookup_oracle (the two userset tests above)
twoStrata                    4       4   conformance/test_conformance_nary_strata::test_multi_stratum_three_way[three_strata_chain-py|roaring];
                                         test_lookup_oracle::test_graph_userset_subject_through_derived_wildcard_gap
wsBare                      11      10   conformance/test_conformance_nary_strata::test_zero_coverage_shapes_three_way[wildcard_userset-py|roaring];
                                         test_bulk_build::..incremental[wildcards]; test_irrelevant_alternatives::test_iia_hypothesis
wsBare.untainted            10       9   (same four as wsBare)
wsBare.derived               1       1   test_schema_shapes::test_drives_clean_across_every_backend[heterogeneous_tupleset]
bareStar                    30      27   conformance/test_conformance_nary_strata::..[wildcard_userset-py|roaring];
                                         conformance/test_conformance_remove::..[object_wildcard] (both)
bareStar.objWildcard        19      18   conformance/test_conformance_remove::..[object_wildcard] (both);
                                         test_bulk_build::..incremental[owc_star_ttu], [wildcards]
bareStar.usersetStar        13      10   conformance/test_conformance_nary_strata::..[wildcard_userset-py|roaring];
                                         test_bulk_build::..incremental[wildcards];
                                         test_schema_shapes::..[heterogeneous_tupleset]
ttuStarFree                 22      22   test_bulk_build::..incremental[owc_star_ttu];
                                         test_cascade_quiesce_gc::test_the_witness_generalises_on_its_star_target[q|w|x]
term                        21      17   (same four as directArmsBare)
term.NoStoreSubjectR        21      17   (same four as directArmsBare)
term.NoTtuTarget             0       0   expected: the LOUD corner; its admitted half is cod.ttuOntoDerived
```

One first-hand probe in the same log: the `term.NoTtuTarget` untainted-TTU-onto-derived
schema from `SCOPE_PROBES`, run through `ParityEngine` for 9 hand ops with the graph joined,
gave `RESULT: no divergence`. Its `--sabotage` arm (oracle negated on `view(u1,doc:d)`)
gave `RESULT: DIVERGED ... {'graph': False, 'set:py': False, 'set:roaring': False, 'oracle': True}`.
