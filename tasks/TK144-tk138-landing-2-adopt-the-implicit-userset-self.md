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
moved: 2026-10-16
updated: 2026-10-16
closed:
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
