---
id: TK144
title: TK138 landing 2: adopt the implicit userset self-relation in all four corners, one atomic change
brief: one atomic Python+Lean change set; never one corner alone; behind TK123/TK119/TK132
pri: NEXT
size: L
deps: [TK123, TK119, TK132]
related: [TK138]
parent: TK138
labels: []
source: docs/tk138-userset-self-relation-2026-10-14.md
source_hash:
created: 2026-10-14
moved: 2026-10-19
updated: 2026-10-19
closed: 2026-10-19
---

Landing 2 of TK138 (decision 2026-10-14, `decide-TK138`, recorded on TK138): adopt OpenFGA's implicit userset self-relation (a userset `T:o#r` is related to `r'` on `T:o` whenever `r` is in r''s computed seeds; propagates across objects) in ALL FOUR corners at once: oracle, set engine, graph index, and the Lean spec / set-engine / graph models. ONE uncommitted change set, committed only on a fully green gate. Landing 1 (TK138 itself, S) pins today's divergence positively in `tests/test_tk138_userset_self_relation.py`; this row turns that pin into agreement.

Measured shape (REASONED from first-hand PROBEs in the plan doc): L Python + XL Lean. Not deferrable to a CORRESPONDENCE.md section-7 gap entry, because the conformance suites compare executable Lean.

Plan: `docs/tk138-userset-self-relation-2026-10-14.md` section 5 steps 2-9 with the decision's refinements:
- Derived graph side: build challenge C5 first (read-time seed-aware `plan.check_fn` for userset subjects on DERIVED relations), falling back to C1 (a)-(d) (inverse seed expansion of the reconcile key set, seed probes inside `_EvalContext`, the same key set in invariants I9 and the delta-scoped verifier) only if `WildcardIndex` cannot reach `check_fn` without importing the processor.
- Tests per challenge C2: model C (cross-object, `group:1#admin` / `group:3#admin`) with OpenFGA v1.22.0's literal answers, the variant without `[group#admin]`, a model-C-shaped corpus schema in `formal/conformance/corpus.py`, widened `ParityEngine._grid` / `_subject_candidates` (every declared relation of a userset shape's type), and the own-object-only sabotage.
- Sub-decisions D1-D4 as recorded on TK138 (D1 star subjects excluded; D2 the spec is the disjunct form; D3a lookups list implicit usersets; D4 keep the `ttu_leaf` from-chain disjunct).
- CHANGELOG entry plus a MINOR version bump (an ALLOW-to-DENY flip, e.g. `vx`, is not a patch). Hypothesis sweep with --hypothesis-seed=N. `headline_definitions.txt`, `headline_statements.txt` and `claim_rot --generate` regenerated deliberately after re-reading the cited rows. Re-check `Spec/WellDef.lean::sem_fuel_stable` on model C's `group:3` (C7).

Sequenced behind TK123 (the lookup channel: `LookupResult` carries `(type, name, predicate)` keys, needed by D3a), TK119 and TK132 (no concurrent Lean edits to the same model).

## Traps

- Do NOT move one corner alone, or the Python without all three Lean models; no xfail; do not delete the TTU from-chain disjunct or refuse the query shape; do not materialize self edges in the closure; do not intern on read; do not narrow the Lean fragment to exclude the shape; never edit a golden, snapshot or oracle result to pass.
- Do not start the Lean graph edits while TK119 / TK132 are open.
- The gate is RED from step 3 to step 6 of the plan by design; commit nothing in between.

## Read first

- `docs/tk138-userset-self-relation-2026-10-14.md` (Decision recommendation, Corrections C1-C7, sections 3 and 5).

## Log

### 2026-10-16

USER 2026-10-16 (in chat): "push 144 down to the bottom of next" -- work it after every other NEXT row (TK147, TK150, TK153, and TK138 only as its parent). The board sorts a tier by id and has no rank field, so the order is recorded here and in the HANDOFF banner, not in frontmatter. In scope for 0.1.0 (user: all open items).

### 2026-10-17

TK144 build stage (ultracode, session 2026-10-17): the four-corner change set LANDED and is UNCOMMITTED. The row stays open until the full gate is green. Body: docs/tk138-userset-self-relation-2026-10-14.md, Corrections 2026-10-17 (build decisions, PROBE 6 transcript, and the end-of-stage block).

DECISIONS (recorded in the doc): C5, not C1, for the derived graph side. The read-time branch in WildcardIndex._check_derived evaluates the plan with a reflexive _EvalContext. The reconcile, the invariants, I9 and bulk build stay reflexive=False, so canonical state and the Lean reconcile model are unchanged. The untainted graph side uses a static seed table (compiler.py::_self_seed_table, SchemaInfo.self_seeds). Lean keeps sem/step as the NON-reflexive base, and the spec is the new semR (Spec/SelfRelation.lean). C7 is settled: semR_fuel_stable holds at the same fuelBound. D1-D4 are as on TK138.

LANDED: oracle sat disjunct; SetEngine.check.sat, the expand top-level correction (SetEngine._self_relation_corrected) and the D3a key channel (MemberSet.ipos/ineg, implicit_keys/implicit_excluded_keys on both result types); the graph seed probes, C5, and the lookup/lookup_reverse key channel. Lean files: Spec/SelfRelation, SetEngine/SelfRelation, GraphIndex/SelfBridge, GraphIndex/SelfRead (graph_correctR and the T3/T6 and driver restatements, proved from graph_correct), GraphIndex/SelfWitness. zcli spec mode prints semR; graph mode prints graphModeAnswersR. tests/test_tk138_userset_self_relation.py now agrees with the literal OpenFGA v1.22.0 table, apart from the two recorded repo exceptions. Corpora: selfrel_cross_object and selfrel_cross_object_no_admin_restriction (theorem-backed, in-premise by zcli fragment mode); selfrel_boolean_flip (spec-side; outside directArmsBare by Lean AND the DW-1 mirror). CHANGELOG [Unreleased], spec-deviations, PYPI_README, SEMANTICS, CORRESPONDENCE (rows plus section 7.5) and FINAL_REVIEW (sections 1, 2, 3.1 item 9) are updated. HEADLINE_AUDITS gains the nine semR capstones.

SABOTAGE: S1-S12 are each red, with literal output in the TK138 test docstring (formal/probes/tk144_sabotage_plugin_2026_10_17.py). FINDING: tests/test_p6_phantom_subject.py's recorded S1 is now INERT at its old site (S13: 183 passed across 11 derived-read modules), while the same reading on the C5 return is RED (S14, same literal query). This is recorded in that module's docstring.

PINS, regenerated after re-reading what each covers: claim_rot (19 changed bodies; 13 rows got dated notes), statement pin and audit pin (additions only), doc_counts (floors up; nine stale corpus-count lines marked past), the two verdict tables in test_conformance_fragment.py, and the derived-arm ledger (+2 corpora; the 25 prior entries are unchanged). test_claim_rot_gate's python-body anchor now carries the line above the fence, because _check_fenced duplicates it.

NOT RUN: the gate tiles and the PostgreSQL leg.

NEXT ACTION: run the full phased gate, then commit by path.

OPEN:
- The MINOR version bump at release time (__version__ stays 0.0.5 in this set).
- The residue userset arm's phantom branch is now reachable only from a seedless facade: pin it or delete it.
- The cost of the brute-force graph lookups on large stores is unmeasured.

TK144 verification, the same day (first-hand). verify.sh lean PASSED: holes=0, audits=745, pinned=745, defs=306, 26 headline theorems all axiom-dependent, anchors 838/838, content pin 539/539, doc counts / handoff lint / task lint green. The HEADLINE_AUDITS additions are sabotage-checked by formal/probes/tk144_headline_loop_sabotage_2026_10_17.sh (one dropped report -> red, one faked axiom-free report -> red; literals in verify.sh). Hypothesis sweep over tests/test_hypothesis.py + tests/test_lookup_hypothesis.py: --hypothesis-seed=11 49 passed, --hypothesis-seed=23 49 passed. The gate tiles and the PostgreSQL leg have NOT been run on this tree. Next action unchanged: the full phased gate, then commit by path. Details: the plan doc's end-of-stage block.

### 2026-10-19

TK138 landing 2 LANDED: the implicit userset self-relation (OpenFGA semantics, D1-D4) in all four corners (oracle, set engine, graph index, Lean spec/set-engine/graph models) as one atomic change set, committed in session 2026-10-19 on a fully green ten-phase gate run on the committed tree (lean + conf-tile 1/5..5/5 + tests-tile 1/4..4/4; gate_status COVERED). Evidence carried from 2026-10-17 (first-hand): verify.sh lean PASSED on the change set; S1-S12 sabotage each red (formal/probes/tk144_sabotage_plugin_2026_10_17.py); HEADLINE_AUDITS additions sabotage-checked (formal/probes/tk144_headline_loop_sabotage_2026_10_17.sh); hypothesis sweep over tests/test_hypothesis.py + tests/test_lookup_hypothesis.py with --hypothesis-seed=11 (49 passed) and --hypothesis-seed=23 (49 passed). PostgreSQL leg: NOT run, a REASONED skip -- the only store change is a read-side key translation in src/zanzibar/store/_store.py (result_keys / excluded_keys); no locking, watermark, isolation or multi-instance state changed, which is the trigger CLAUDE.md names for the PG leg. OPEN items moved out: residue userset arm phantom branch -> TK161 (LATER, S); brute-force graph lookup cost on large stores -> TK162 (LATER, M); the MINOR version bump (ALLOW-to-DENY flip) -> recorded on TK151, which gates the 0.1.0 cut (no separate release row exists). Body: docs/tk138-userset-self-relation-2026-10-14.md (Corrections 2026-10-17).
