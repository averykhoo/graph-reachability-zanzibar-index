---
id: TK44
title: Generator pair-cell UNKNOWN residue: no generator gap left, rest derived refused-only
brief:
pri: NOW
size: M
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-10-12c
updated: 2026-10-12c
closed: 2026-10-12c
---

Best measured union is **891/1275** pair cells (`docs/design/generator-coverage/README.md:566`, FROZEN): some of the residue is REJ-with-witness and legitimately unreachable, the rest is UNKNOWN with no witness explaining it. The LIVING carrier is [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md)`:482-487`, which uses it as a methodological caution: *"read a green gate as 'the instruments we have found nothing', never as 'there is nothing'."*

That is why this is `HOLD` and not a defect: it is **published honesty**, deliberately not rounded away, and the design doc's own position is that the number should be published rather than eliminated. What has never been decided is whether the UNKNOWN residue is worth attacking, or whether publishing it is the whole intended answer. That decision is the work.

## Traps

⚠ **The obvious "fix" is the forbidden one.** `tests/test_generator_coverage.py:257` explicitly argues AGAINST a hand-written `EXPECTED_UNREACHABLE` list — *"a future silent gap"* — and does not have one. Closing cells by exempting them is the failure mode, not the fix.

⚠ **Do not quote a percentage.** The two carriers say ~30% and "roughly a quarter" of the same measurement; the honest handle is the fraction at its source and the date. Re-measure before citing.

## Read first

- [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) § "What this procedure cannot do" — the LIVING carrier and the methodological point (about `:788-817` as of 2026-10-13; the old `:482-487` and `:641-647` pointers are dead -- find it by the section heading)
- [`docs/design/generator-coverage/README.md`](docs/design/generator-coverage/README.md)`:564-570` — §6, the measurement (FROZEN)
- `tests/test_generator_coverage.py` — the gate, and `test_rejection_witness_is_still_refused`'s docstring, the argument against an exemption list (was `:257`; about `:292` as of 2026-10-13)

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-29 (`J-27`, tier 4; sweep-j + sweep-k, two documents). Sweep-k guessed `GS-1`; `GS-1` is a closed gate-tree-id row and does not cover it. Both carriers re-read this pass; the LIVING one is docs/sabotage-procedure.md:482-487.

### 2026-09-10

LANDED 2026-09-10 (TK53 append) into `docs/sabotage-procedure.md`, section "What this procedure cannot do", after the residue paragraph. The row's own citation (:482-487) and the adjudication's (:524-526) are BOTH dead -- the paragraph is at :641-647 now.

The first pass called this ALREADY_CARRIED and the adversarial pass OVERTURNED it, and the overturn is the interesting part: the first pass reconstructed the wrong half of the finding from a frozen history file and matched it against a carrier for a statement the adjudication never claimed was missing.

The real half is a live ZT-P3-5 recurrence, and I verified all four figures first-hand rather than trusting the report: `tests/test_generator_coverage.py:68` says ~19% and `:428` says ~28% -- the SAME claim, identical wording ("unreached even at `deep`"), contradicting each other inside ONE module -- while `:1152` says ~30% and `docs/sabotage-procedure.md:643` says "roughly a quarter".

Nothing mechanical catches it, and this is worth carrying: `check_restated_counts` (TK58, landed 2026-09-08) is scoped to top-level `docs/` and `tasks/` markdown and to check/open-task/test counts, so a PERCENTAGE in a `.py` docstring is out of scope twice over. The landed text points at `tests/test_generator_coverage.py::test_report_cell_coverage` (:1149, run with -s) as the single live source.

### 2026-10-04g

PROMOTED LATER -> NEXT 2026-10-04g (user pick: NEXT raised to 5). Why: ~30% of the generator pair-cell space unreached even at deep budget, with unexplained residue -- each unreached cell is an input class no property test has ever seen, so explaining (or reaching) them can surface real bugs. Open-ended: time-box the census first and record it in an ACTIVE-PLAN doc. Do NOT close the gap by adding cells to an exemption list.

### 2026-10-05b

Note (pre-TK120 scratch sweep, 2026-10-05b): the 2026-08-21b body still says "That is why this is HOLD"; the row has been NEXT since 2026-10-04g. The body is history, the pri field is current.

### 2026-10-12b

Re-ranked 2026-10-12b (user approved the order in chat): TK118 NOW, then TK79, then TK102 (NEXT); TK97 and TK44 down to LATER (process tooling / coverage research with no known bug); TK134+TK135 stay LATER, user says no rush to release 0.0.4. Why TK118 first: it is the only row about a fail-OPEN, and it bears on what we tell production users about residue today.

### 2026-10-12c

PROMOTED LATER -> NOW 2026-10-12c: the user asked in chat for TK79, TK102 and TK44 to be done in this session via subagents, in that order. TK79 and TK102 are closed; TK44 is the remaining item. Suggested first step stands (2026-10-04): a time-boxed census of the UNKNOWN unreached cells, recorded in a tracked ACTIVE-PLAN doc; re-measure via tests/test_generator_coverage.py::test_report_cell_coverage (-s) before quoting any figure.

CENSUS LANDED 2026-10-12c in docs/tk44-generator-coverage-census-2026-10-12.md (ACTIVE-PLAN, provenance-labelled; not committed). Denominator is 1128 cells / 48 features since TK107, not 1275. Measured 2026-10-12 at 8a76ff4 via test_report_cell_coverage -s: ci +REJ 760/1128 (UNKNOWN 368), deep 776/1128 (UNKNOWN 352); union of every generator in the repo 780/1128 (UNKNOWN 348). Of the 348: 312 are STRUCTURALLY IMPOSSIBLE (one feature is refused-only by TK106/TK108/ASK-1 parse refusals; 180 of them are not even witnessable, refused-only x compiled-only); 36 are GENERATOR GAPS, all reachable (6 hand-built accepted schemas reach 36/36), one cause: genswarm.witness wires every arm to r1/parent so body_boolean collides with owc/self_ttu/body_wc_userset/ts_wildcard. Zero cells unexplained. Also found: swarm_schema_asts tests body_ttu which is not in SWARM_SWITCHES (dead arm). Enumerator saturates at K<=3 (full 2^16 space = 701). Nothing in tests changed. NEXT: doc section 5 item 1 (second untainted referent in witness, closes 32/36), then drive the new configs; item 5 reports class S as a derived set, never a list.

DECIDED 2026-10-12c (executive, CLAUDE.md "Who decides"; full reasoning + work list in docs/tk44-generator-coverage-census-2026-10-12.md section "Decision", dated at the top). Of the 348 UNKNOWN: class G (36, both features HIT individually) is ATTACKED NOW by widening genswarm.witness (second untainted referent r0/parent2 for owc/self_ttu/body_wc_userset when body_boolean is on, plus a star parent2 arm over r0; census sec 5 items 1-2), and the new configs must be DRIVEN through ParityEngine by the sweeps, not just compiled -- that drive is the only equivalence value here. Class K (16, deep-only) goes in the same change if it is the same referent edit (item 3), else is the single named follow-up. The dead body_ttu swarm arm is fixed by ADDING body_ttu to SWARM_SWITCHES (floors re-measured after). Class S (312, one feature carried only by parse-refusal witnesses) is NOT attacked: S2 (180) can never be witnessed and S1/S3 witnesses are cosmetic; instead test_report_cell_coverage reports S as a DERIVED class computed from REJECTION_WITNESSES and the HIT set -- not an exemption list, because a generator HIT or a revoked witness moves its cells back to UNKNOWN automatically. Positive pin = the raised floor in test_enumerator_cell_coverage_floor, sabotaged by reverting the witness change alone. Any ParityEngine disagreement on a newly driven config is a Python bug: row + positive pin, never xfail, never drop the config. Residue stays published from the -s run with its date; strip the stale percentages at test_generator_coverage.py :68/:428/:1152 and sabotage-procedure.md ~:643. Row's Read-first pointer :482-487 is dead; the live paragraph is ~:641-647. Close TK44 when G is 0 at ci and S is reported derived. Tests untouched this step.

IMPLEMENTED 2026-10-12c (implementing agent; NOT committed, gate not run, row left open for the finish stage). Body: docs/tk44-generator-coverage-census-2026-10-12.md section "Implementation, re-measured" (dated, above Decision). LANDED in tests/genswarm.py::witness: split = body_boolean and not derived_star re-wires owc / self_ttu / body_wc_userset / ts_wildcard to a fresh untainted r15 via parent2 (r0 was unusable: it feeds the derived r8, owc on it is refused); body_userset adds an always-tainted referent r13 (item 3); SWARM_SWITCHES gains body_ttu (own witness arm r14) and derived_star, a witness-only [expect REJECT] switch that keeps the four decision-15 refusal families live at K<=2 (without it test_every_rejection_witness_family_is_actually_exercised_by_the_enumerator goes red). Live (test_report_cell_coverage -s, ci and deep identical): HIT 741, +REJ 816/1128, UNKNOWN 312 = refused-only 312 + gap 0 + other 0. Drive probe: all 100 accepted K<=2 configs driven in sparse and dense, all 56 gained cells driven, 0 divergences. Checks, each sabotaged red: floors raised to 741/741/816 (zero headroom; split=False gives 721); new test_every_pair_of_hit_features_is_reached_together (G==0, derived by _unknown_classes); _assert_non_vacuous now requires every compiling config to be driven. Item 8 was already done 2026-09-10 (GC-1). Read-first pointer fix: the live sabotage-procedure.md paragraph is section What this procedure cannot do, about :800-815 as of 2026-10-12 (not :482-487, not :641-647). RED: none in the targeted runs; PRE-EXISTING deep-only red: test_swarm_campaign_reaches_cells_and_never_starves_a_switch deep floor 670 vs 592 measured at 8a76ff4. NEXT: full gate, commit by path, freeze the census doc, close TK44 (G is 0 at ci, S reported derived).

REVIEW FIXES 2026-10-12c (fix-1 and fix-2 agents; NOT committed, gate not run, row open for the finish stage). Body: census doc, the two dated "Correction 2026-10-13" sections at the top. This SUPERSEDES the IMPLEMENTED entry's "deep floor 670 pre-existing red, not lowered": fix-1 LOWERED the deep swarm floor in test_swarm_campaign_reaches_cells_and_never_starves_a_switch from 670 to 527. It was red at 8a76ff4 (592) and is 586 on this tree. Provenance and sabotage are in the test comment. Also fix-1: new test_refused_only_features_are_tupleset_shapes (sabotaged red), witness docstring r0->r15, ENUM_K comment re-measured (171 configs at K<=2, 987 at K<=3). Fix-2: that test now also checks per feature that every witness carrying a refused-only feature refuses with a tupleset-shape message (TUPLESET_MUST_BE_DIRECT / TUPLESET_NO_USERSET / new genswarm.DANGLING_REFERENCE). Sabotaged red on ttu.ts:owc; the pre-fix-2 test stays green under the same sabotage. Residual: ttu.ts:Union and ttu.ts:multitype are caught only by the HIT floor. Other fix-2 changes: the ts_wildcard comment says r15; title retitled with no residue count (GC-1); Read-first pointers fixed. Not fixed (out of scope, disclosed in the test): dropping the all-ON swarm stratum is caught by no floor. NEXT: finish stage. Run the full gate, commit by path, FREEZE the census doc, close TK44.

CLOSED 2026-10-12c. Class G (generator gap) is 0 at ci and deep; class S (refused-only) is reported DERIVED, never listed. LANDED: tests/genswarm.py::witness re-wires owc/self_ttu/body_wc_userset/ts_wildcard to a fresh untainted r15 via parent2 when body_boolean is on, adds r13 for body_userset; SWARM_SWITCHES gains body_ttu (dead arm revived) and the witness-only derived_star; new tests/genswarm.py::DANGLING_REFERENCE. Checks in tests/test_generator_coverage.py, each sabotaged red: ::test_enumerator_cell_coverage_floor raised (zero headroom), ::test_every_pair_of_hit_features_is_reached_together (G==0 via ::_unknown_classes), ::test_refused_only_features_are_tupleset_shapes (per-feature tupleset-shape refusal), _assert_non_vacuous requires every compiling config driven. Every newly reached accepted config driven through ParityEngine sparse+dense, 0 divergences. Deep swarm floor lowered 670 -> 527 (red at 8a76ff4), provenance in the test comment. Live residue: ::test_report_cell_coverage -s, never quoted elsewhere. Body: docs/tk44-generator-coverage-census-2026-10-12.md (FROZEN). Residual, disclosed in the tests: ttu.ts:Union / ttu.ts:multitype going un-HIT is caught only by the HIT floor; dropping the all-ON swarm stratum is caught by no floor. Carriers updated: docs/sabotage-procedure.md "What this procedure cannot do", docs/promote-next-triage-2026-10-03.md dated correction.
