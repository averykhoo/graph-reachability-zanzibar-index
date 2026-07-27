# n-ary / ≥3-strata coverage — what `twoStrata` costs, re-verified 2026-07-27

ZT-P4-4 follow-up. The 2026-07-26 review recorded three language-feature holes
(max 2 strata anywhere, every operator binary, wildcard usersets at zero) and a
partial fix (`test_conformance_nary_strata.py`). This session re-measured all of
it against the working tree, re-verified the load-bearing Lean claim **in the
Lean sources rather than second-hand**, closed what was reachable, and states
precisely what is not.

Every number below comes from a command that was run; the command is quoted.

---

## 1. What was re-measured

**Command** (repo root, `PYTHONPATH=.`, the repo conda interpreter): a `python -c`
script that walks `zanzibar_utils_v1.parse_schema_ast` + `parse_openfga_schema`
over **69 schemas** — the four corpus dicts in `formal/conformance/corpus.py`
(`SCHEMAS`, `MULTI_STRATUM_SCHEMAS`, `TTU_USERSET_SCHEMAS`,
`SELF_REFERENTIAL_SCHEMAS`, 28 corpora) plus the 40 seeded generated schemas
from `test_conformance_generated._case` plus `three_strata_chain`.

| measurement | 2026-07-26 review | 2026-07-27 re-measurement |
|---|---|---|
| max strata anywhere | 2 | **3** — `three_strata_chain` + **12 of the 40 generated schemas** (seeds 3, 7, 8, 11, 12, 15, 17, 18, 34, 35, 36, 39). Histogram: `{0: 14, 1: 17, 2: 25, 3: 13}` |
| max operator arity anywhere | 2 (all binary) | **3**, reached by exactly **2 nodes** (`nary_union`, `nary_intersection`) — histogram `{2: 120 nodes, 3: 2 nodes}`; **both untainted** |
| wildcard usersets (`[T:*#p]`) | 0 | **still 0** |
| plan-leaf kinds compiled | not measured | `closure` 211 · `derived-computed` 42 · `derived-ttu` 50 · **`derived-userset` 0** · **`derived-tupleset-ttu` 0** |

So: the ≥3-strata hole had already been closed on the **Python** side by the
2026-07-26 work, the arity hole had **not** been closed at the arity it exists
for (the ceiling was 3, and the ceiling was never derived), and a fourth hole —
plan-leaf kinds — was undiscovered.

## 2. The Lean claim, re-verified in the sources (not taken second-hand)

The 2026-07-26 note said the graph-side ≥3-strata path was blocked because
"Lean's `twoStrata` is load-bearing and `runCascade2` is fixed at 2 rounds".
**Both halves hold, and are structural rather than a relaxable hypothesis:**

* `formal/lean/ZanzibarProofs/GraphIndex/CascadeStrata.lean::runCascade2` is
  literally two nested `reconcileJobsLR S T (reconcileJobsLR S T σ jobs1) jobs2`
  applications plus one quiescence check. The round count is **not a parameter**.
  A third stratum has no round to settle in.
* `formal/lean/ZanzibarProofs/FullScope.lean::W4Fragment` carries a `twoStrata`
  field, quantified exactly like `hLU2`, and it is a hypothesis of the final
  `FullScope.lean::graph_correct` (threaded through
  `CascadeStrata.lean::runCascade2_no_abort` as `hLU2`, and via that into
  `backend_equivalence` / `graph_reached_inv` / `Exec.graphRun_check_eq_sem`).
* `runCascade2_no_abort`'s own in-file attack note records the refutation that
  makes `hLU2` load-bearing: on `a := b ∨ y, b := c ∨ x, c := x ∖ y` (three
  strata) `hLU2` is FALSE and the round-2 reject FIRES, so `runCascade2` returns
  the pre-state. `W4Fragment`'s doc comment says the same in one line:
  *"attack-confirmed load-bearing: a 3-stratum schema fires the round-2 reject.
  Python handles arbitrary strata."*

**Cost of widening (why it is not a corpus problem):** it needs a
`runCascadeN`/fuel-indexed scheduler in place of `runCascade2`, and then a
re-proof of the entire W3d-2 layer — every lemma from `CascadeStrata.lean`
through `CascadeStrataSettle` / `Resettle` / `Enum` / `Assemble` / `Inv` /
`Edge` is stated over exactly two rounds (per-round frontier cursors, the
"round 2 never targets stratum-1 keys" fence, the two-round coverage chain).
`Exec.lean`'s driver and the graph-state conformance mode ride on top. That is a
multi-session Lean project, and it is squarely inside `formal/lean/**`, which
this workstream may not touch.

## 3. What IS covered at ≥3 strata (correcting the "spec-side only" framing)

The Python ≥3-stratum cascade is **not** uncovered. As of 2026-07-26 it is
driven and checked in three places:

1. `test_conformance_nary_strata.py::test_multi_stratum_three_way` — the real
   `WildcardIndex` + `DeltaProcessor` cascade (`backends.graphindex_answers`)
   vs the independent oracle vs the real `SetEngine`, over the full shared grid,
   under **both** `SetOps`. This is a genuine graph-side gate; it is
   Python-to-Python, and the module says so.
2. `test_conformance_spec.py` — Lean `sem` vs oracle vs set engine on
   `three_strata_chain`. `sem` is a pure function of the final store with no
   cascade and no round bound, so this leg is scope-clean at any stratum count.
3. `test_conformance_generated.py` — 12 of its 40 seeds compile to 3 strata
   (measured above), giving spec-level ≥3-strata coverage outside the curated
   corpora too.

**What is ungated is the LEAN OPERATIONAL MODEL at ≥3 strata**, and it is ungated
because no such model exists. Putting `three_strata_chain` into `GRAPH_FRAGMENT`
would compare the operational model outside every theorem that covers it and
would **not fail loudly** — `Cli.lean` gates only on runtime write admission
(rc 2) and drained-ness (rc 3), never on `W4Fragment`. That is exactly the
ZT-P3-3 mistake, and `test_three_strata_corpus_features` asserts the corpus stays
out of `SCHEMAS` and `GRAPH_FRAGMENT`.

## 4. What was added (all reachable without touching `formal/lean/**`)

* **`corpus.py::nary_union_derived4`** — the first **≥4-arity** operator in the
  harness, and the first high-arity operator that is **DERIVED**
  (`any_of4: a or b or c or safe`, `safe: x but not blocked`). Closes both the
  arity ceiling and the residue `test_conformance_nary_strata.py` used to record
  in as many words ("a DERIVED n-ary union is not gated Lean-side anywhere").
  Two strata, so it is IN `GRAPH_FRAGMENT` and classified `_THEOREM_BACKED` with
  the per-field argument written down. Measured runtime: zcli spec 0.1 s,
  graph-state 0.5 s, Python graph index 0.5 s.
* **`test_harness_wide_arity_ceiling`** — floors the harness-wide maximum
  operator arity at 4 and pins that the high-arity node is really derived.
* **`corpus.py::TTU_USERSET_SCHEMAS['derived_userset']`** — the first corpus
  anywhere that compiles a **`PDerivedUserset`** plan leaf (see §1's leaf-kind
  histogram: it was at zero). Spec-side only; scope argument in situ.
* **`test_every_plan_leaf_kind_is_reached_by_some_corpus`** — asserts every
  required `compile_ruleset` leaf kind is produced by some corpus, so this class
  of hole cannot reopen silently.

## 5. What remains open, precisely

| hole | status | what closing it takes |
|---|---|---|
| Lean operational model at ≥3 strata | **OPEN — needs a Lean fragment widening** | `runCascadeN` + re-proof of the whole W3d-2 layer + `Exec`/graph-state ripple. Multi-session, inside `formal/lean/**`. |
| wildcard usersets `[T:*#p]` | **OPEN — zero coverage** | Python rejects them only over *derived* relations; over untainted ones they are admitted. `W4Fragment.wsBare` excludes them, so any corpus must be spec-side. Not attempted here: needs its own scope argument. |
| `PDerivedTuplesetTTU` (`derived-tupleset-ttu`) plan leaf | **OPEN — zero coverage** | The last plan-leaf kind produced by no corpus. Deliberately excluded from `_REQUIRED_LEAF_KINDS` rather than faked; needs its own scope argument and corpus. |
| a DERIVED n-ary operator at arity ≥ 5 | open, low value | The Lean model's round-2 job enumeration hits a measured cliff in DISTINCT SUBJECTS (2 subj 0.1 s → 5 subj 115 s). Arity itself is cheap; witnesses are not. |
