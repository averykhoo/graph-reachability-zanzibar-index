# n-ary / ≥3-strata coverage — what `twoStrata` costs, re-verified 2026-07-27

> **FROZEN 2026-07-28 — provenance, not a living document.** A completed re-measurement of
> the `twoStrata` / n-ary coverage holes, plus its 2026-07-28 addendum closing the last
> two. Every figure measures the tree AS IT WAS THEN and several are now false; read it
> for the method and the quoted commands, never for state. Live state:
> [`HANDOFF.md`](../../HANDOFF.md) + the session ledgers. Corrections are appended dated
> at the top, never edited into the body.

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
| wildcard usersets `[T:*#p]` | **CLOSED 2026-07-28** — see the addendum below | ~~Python rejects them only over *derived* relations; over untainted ones they are admitted. `W4Fragment.wsBare` excludes them, so any corpus must be spec-side.~~ |
| `PDerivedTuplesetTTU` (`derived-tupleset-ttu`) plan leaf | **CLOSED 2026-07-28** — see the addendum below | ~~The last plan-leaf kind produced by no corpus. Deliberately excluded from `_REQUIRED_LEAF_KINDS` rather than faked.~~ |
| a DERIVED n-ary operator at arity ≥ 5 | open, low value | The Lean model's round-2 job enumeration hits a measured cliff in DISTINCT SUBJECTS (2 subj 0.1 s → 5 subj 115 s). Arity itself is cheap; witnesses are not. |

---

## Addendum 2026-07-28 — the last two zero-coverage holes, closed

Board item (C). **Reachability was established empirically FIRST**, because both
findings as filed read wider than the reachable surface. Answers, with the exact
schema text and observed output:

### (1) wildcard usersets `[T:*#p]` — reachable ONLY over untainted relations

Over a **derived** relation the shape is a deliberate scope rejection, so no
corpus can carry it: `_build_plan_tree`'s `Direct` arm raises. Observed on

```
type user
type group
  define base: [user]
  define kicked: [user]
  define member: base but not kicked
type doc
  define viewer: [group:*#member]
```

> `UnsupportedByGraphIndex: relation doc#viewer: wildcard userset restriction
> [group:*#member] over the derived relation group#member needs symbolic
> composition through residues (v1 scope hook; see spec-deviations)`

— raised by `parse_openfga_schema` itself, i.e. before any corpus dict could be
walked. (The set engine *does* answer this schema, and matched the oracle on all
102 grid queries; but the plan-leaf coverage floor and `test_grid_independence`
both call `parse_openfga_schema` on every entry of every corpus dict, so such an
entry would crash the harness rather than extend it. Recorded, not corpus'd.)

Over an **untainted** relation the shape compiles and runs everywhere. Observed
on the corpus that landed (`TTU_USERSET_SCHEMAS['wildcard_userset']`,
`viewer: [user, group:*#member]` + `can_view: viewer but not banned`, 5 tuples,
210-query grid): **Lean `sem` == oracle == set engine == real graph index**,
14 True, zcli 0.10 s. That untainted surface IS the reachable one.

*Scope:* spec-side + a python-only three-backend leg. **Never `GRAPH_FRAGMENT`** —
`W4Fragment.wsBare` is `∀ sh ∈ wildcardShapes S, sh.2 = BARE` and this schema's
shape set contains the non-bare `(group, member)`, so `wsBare` is FALSE and every
theorem routed through `graph_correct` says nothing here. `wsBare`'s own doc
comment already records the asymmetry, so this is a declared Lean gap, not a
discovery.

### (2) `derived-tupleset-ttu` — reachable, and the reason it was never covered is instructive

It is **not** unreachable-by-construction: `_build_plan_tree`'s `TTU` arm emits
`PDerivedTuplesetTTU` whenever `(object_type, tupleset_rel)` is tainted, and
`tests/test_boolean_compile.py::test_plan_shapes_demorgans_law_1` has pinned
three of them since P2. What makes it *hard* to cover is that the leaf is
compiled far more easily than it is **driven**: TTU parents are the STORED
tupleset tuples, never computed membership (spec-deviations 2026-07-07 P5 #1), so
a derived tupleset with no `Direct` restriction holds no stored tuples and its
dependent TTU is constantly EMPTY. That is exactly the shape of
`demorgans_law_1.fga` — the only in-tree schema compiling this leaf — whose
`unmatchable_conds` / `matched_roles` / `matched_users` are ∅ by construction.
A corpus built on that shape would have raised the histogram and tested nothing.

The corpus that landed gives the tupleset a storage leaf:

```
type user
type folder
  define viewer: [user]
type doc
  define detached: [folder]
  define parent: [folder] but not detached
  define inherited: viewer from parent
```

Compiles to `strata=[[('doc','parent')], [('doc','inherited')]]` with
`('doc','inherited') -> LeafSpec('viewer', 'derived-tupleset-ttu', True)` and
`('doc','parent') -> LeafSpec('parent.0','closure',True,storage=True)`.
Observed over the 200-query grid: **Lean `sem` == oracle == set engine == real
graph index**, 8 True, zcli 0.08 s. The load-bearing witness is the asymmetry
`parent(f2,d1) = False` (the derived tupleset's exclusion bites) while
`inherited(bob,d1) = True` (f2 is still a STORED `parent` tuple) — that IS the
semantic content of the kind, and it is what distinguishes it from `derived-ttu`.

*Scope:* spec-side + the python-only leg. **Never `GRAPH_FRAGMENT`**, and here
the Lean exclusion is doubled: outside `W4Fragment.computedOnly` (a `ttu` node is
never `ComputedOnly`) **and** outside the ADMISSION bundle
`GraphAdmission.ttuDirect` (`TtuTuplesetsDirect` forces a declared tupleset def
to be directs-only; `parent` is an `excl`). `w4_within_scope`'s third clause is
literally "a TTU tupleset relation is never derived".

### What landed

* `corpus.py::TTU_USERSET_SCHEMAS['wildcard_userset']` and `['derived_tupleset_ttu']`,
  each with the per-field scope argument in situ.
* `_REQUIRED_LEAF_KINDS` raised to include `derived-tupleset-ttu` — the floor now
  names EVERY kind `_plan_leaves` can emit, and
  `test_required_leaf_kinds_are_exactly_the_compilers_kinds` reads the kinds out
  of the compiler's own source so a NEW kind cannot be added while the
  hand-maintained floor stays silently one short.
* `test_harness_wide_wildcard_userset_floor` — floors the harness-wide count of
  DISTINCT **non-bare** wildcard shapes at 1. Counting non-bare shapes
  specifically is the point: the bare `[T:*]` shapes many corpora carry would
  otherwise keep the assertion green while the feature stayed at zero.
* `test_wildcard_userset_corpus_features` / `test_derived_tupleset_ttu_corpus_features`
  — the anti-vacuity/load-bearing pins, including the scope assertions
  (`not in SCHEMAS`, `not in GRAPH_FRAGMENT`).
* `test_zero_coverage_shapes_three_way` — python-only oracle == set engine ==
  real graph index, full grid, both `SetOps`.

Conformance count 450 → 464.

### Sabotage (house rule: watch every new check go red)

| sabotage | observed |
|---|---|
| delete the `derived_tupleset_ttu` corpus | `plan-leaf kind(s) ['derived-tupleset-ttu'] are produced by NO corpus … Observed histogram: {'closure': 22, 'derived-computed': 9, 'derived-ttu': 2, 'derived-userset': 1}` |
| delete the `wildcard_userset` corpus | `harness-wide DISTINCT wildcard-userset shapes = 0, floor 1` |
| add a new leaf kind to `_plan_leaves` | `emitted by _plan_leaves but NOT in the floor: ['brand-new-kind']` |
| **swap `[group:*#member]` for the bare `[user:*]`** (still "a wildcard") | floor fires (`= 0, floor 1`) **and** `no longer carries the literal group:*#member restriction: []` — this is the fail-by-passing case the non-bare counting exists for |
| **make the derived tupleset storage-leaf-free** (`parent: _all but not detached`) — the leaf is STILL compiled, so the coverage floor stays green | `the derived tupleset 'parent' has no storage leaf, so it can hold no stored tuples and 'inherited' is constantly EMPTY — the leaf would be compiled but never driven` |
| drop the `detached` tuple | `'detached' no longer excludes f2 from 'parent', so the tupleset relation is effectively untainted and the leaf under test is a plain derived-ttu` |
| leak both corpora into `GRAPH_FRAGMENT` | `[wildcard_userset] leaked into GRAPH_FRAGMENT` / `[derived_tupleset_ttu] leaked into GRAPH_FRAGMENT` |
