# FINAL_REVIEW.md — what is proved, what is pinned, what is not

Phase 6 item 3 (plan §7 / §8; `HANDOFF.md`'s dated resume blocks — the section
once called "The next task" no longer exists). This is the final
review document for the formal-verification effort: the claim in the plan's
own words, a clause-by-clause cross-check against what actually stands in the
tree, the theorem inventory in English, and the residual risk. Nothing here
rounds up.

**Verification state.** `bash formal/verify.sh` green in all ten phases —
`lake build` + **0 sorries** + `zcli` + the axiom audit (each audited theorem
depending only on `[propext, Classical.choice, Quot.sound]`) + the audit identity,
headline-statement and headline-definition pins + the `CORRESPONDENCE.md` anchor
pin + this document's counts pin (step 4e) + `formal/conformance/` + `tests/`,
**0 skips, 0 xfails** throughout. Interpreter overridable via `ZANZIBAR_PY`.

<!-- BEGIN GENERATED COUNTS (formal/conformance/doc_counts.py) -->
<!-- Do not hand-edit. Regenerate:
     python -m formal.conformance.doc_counts --generate
     `verify.sh lean` step 4e fails if this block disagrees with the tree. -->

**Counts — MEASURED, not asserted.** Every number in this block is generated from
the tree and re-checked by `formal/verify.sh` (step 4e). If one is wrong, the gate
is red, not the document. Numbers elsewhere in this file, and in every other doc,
are hand-maintained prose — check them against this block, and prefer moving a
number INTO it over restating it.

| quantity | value |
|---|---|
| `formal/conformance/` collected | **546** |
| `tests/` collected | **1131** |
| whole-repo suite | **1677** |
| differential conformance tests | **475** across **14** files |
| gate-tooling conformance tests | **71** across **4** files |
| audited theorems (`#print axioms` in `Audit.lean`) | **587** |
| audit identity pin (`audited_theorems.txt`) | **587** |
| headline definition pin | **251** rows (**242** declarations + ambient) |
| `CORRESPONDENCE.md` anchors | **592** (**354** Python + **238** Lean) |
| `corpus.SCHEMAS` | **26** |
| `corpus.GRAPH_FRAGMENT` (graph-side gates) | **25** |
| spec-scope corpora (four dicts) | **35** = 26 + 6 `TTU_USERSET` + 2 `SELF_REFERENTIAL` + 1 `MULTI_STRATUM` |
| gate floors (`verify.sh`) | `MIN_CONF_ALL`=546 (=104+442), `MIN_TESTS_ALL`=1131, `EXPECTED_MIN_AUDITS`=460 |

**State-gate projection ledger — what the differential gate does NOT compare.**
Driven fresh over all **25** `GRAPH_FRAGMENT` corpora through the real graph
index (`extractor.projection_ledger`). Read this as the honest width of the
state-level claim: of the raw `EdgeV4` rows Python writes, only the `compared`
row is checked against Lean. **Do not restate these numbers elsewhere** — three
prose copies rotted through two corpus additions before this became generated.

| edge projection | rows |
|---|---|
| raw `EdgeV4` rows | **498** |
| dropped by P1 (closure-only) | **233** |
| dropped by P2 (bridge) | **0** |
| **compared against Lean** | **265** |
| raw `NodeV4` rows (all dropped by P5) | **282** |
| residue rows kept | **13** |

Per conformance file:

| file | tests | kind |
|---|---|---|
| `test_conformance_spec.py` | 105 | differential |
| `test_conformance_remove.py` | 104 | differential |
| `test_conformance_state.py` | 56 | differential |
| `test_conformance_graph.py` | 51 | differential |
| `test_sorry_scan.py` | 44 | tooling |
| `test_conformance_generated.py` | 40 | differential |
| `test_conformance_bulk_state.py` | 26 | differential |
| `test_conformance_random.py` | 26 | differential |
| `test_conformance_remove_graph.py` | 23 | differential |
| `test_conformance_nary_strata.py` | 19 | differential |
| `test_w4fragment_scope_pin.py` | 15 | tooling |
| `test_runner_retry.py` | 7 | tooling |
| `test_conformance_enum.py` | 6 | differential |
| `test_conformance_enum_state.py` | 6 | differential |
| `test_cli_mode.py` | 5 | differential |
| `test_leaf_namespace_correspondence.py` | 5 | tooling |
| `test_conformance_direct_arm.py` | 4 | differential |
| `test_grid_independence.py` | 4 | differential |

<!-- END GENERATED COUNTS -->

Corpora composition: `GRAPH_FRAGMENT` is the subset of `SCHEMAS` driven through the
graph-side gates (`object_wildcard` is the one exclusion). The `TTU_USERSET_SCHEMAS`,
`SELF_REFERENTIAL_SCHEMAS` and `MULTI_STRATUM_SCHEMAS` dicts sit OUTSIDE `SCHEMAS` —
spec/oracle/set-engine only (full scope), so the graph-side suites stay
`W4Fragment`-scoped. The `MULTI_STRATUM` entry (`three_strata_chain`) is the
>2-strata spec-side leg; there is no graph-side ≥3-strata coverage, by decision
(`ARCHITECTURE.md` §6 residual surface, decided 2026-07-27 — `HANDOFF.md` carried
that numbered residual list at the time and no longer does).

**House rule, and what now makes it meaningful.** Nothing anywhere in the repo may
claim more than this document. That rule was empty twice: this file once stated BOTH
263 and 326 conformance tests and BOTH 19 and 15 corpora (`ZT-P3-5`, 2026-07-26), and
after a hand-fix it drifted back into stating two different values for the same
quantity by 2026-07-29. A self-contradictory target binds nothing. **The block above
is now GENERATED from the tree and re-checked by `verify.sh` step 4e**, so the
governing numbers cannot rot silently again; §1–§4 below cite it and must not restate
a different figure. Hand-written counts elsewhere in this file and in other docs are
still prose — check them against the block, and prefer moving a number INTO it over
restating it.

---

## 1. The claim (plan §7, verbatim), and its cross-check

The plan's honesty clause says the final claim is exactly this, no more:

> The set-engine and graph-index **algorithms**, as modeled in Lean at the
> level of `CORRESPONDENCE.md`, are **proven** to compute stratified-Datalog
> Zanzibar semantics and hence to be equivalent (machine-checked, axiom-audited).
> The **Python implementations** are pinned to those models by structural
> correspondence review, six-way differential conformance including state-level
> equality, and exhaustive small-scope enumeration up to the documented bounds.
> Residual unverified surface: the interner/bitmap representation layer, the
> SQL/transaction/concurrency layer (optional TLA+ phase), non-stratifiable
> schemas, `expand`/`lookup`, and the fidelity of the model-to-code
> correspondence itself.

Clause-by-clause, what is actually true today:

| §7 clause | status |
|---|---|
| set-engine **algorithm** proven to compute `sem` | ✅ **Full scope, unconditional.** `setEngine_correct` (T1): for every schema, store and query, the Lean set-engine model's `check` equals `sem`. (Until 2026-09-06 the statement carried three unused binders — well-formed, stratifiable, "identifier-valid" — the last over an `opaque` predicate no store could be shown to satisfy; all three are gone, see `SEMANTICS.md` §2.1 history.) |
| graph-index **algorithm** proven to compute `sem` | ⚠️ **At the documented fragment, not beyond (§3; and §3.0 for what that fragment stopped excluding on 2026-08-05, plus the one theorem it still excludes).** `graph_correct` (T2b): at every fully-drained state of the operational closure `ReachedBy` (logged rule-routed writes + the state-derived two-round cascade — the model of the synchronous v1 Python write path), graph `check` = `sem`, for stores/schemas satisfying `GraphAdmission` (the Python-admission mirror) **and** `W4Fragment` (honest carries: derived defs are boolean trees over computed refs AND `Direct` grant arms — whose restrictions must be bare and concrete and must not be union-reachable — with derived operands computed-only; ≤ 2 strata, bare declared wildcards, bare-star stores, star-free TTU tuplesets, derived terminality — **TEN** fields since E-chain leg 5 (2026-08-05) split `computedOnly` into five; `structure W4Fragment` in `FullScope.lean`; the derived-def ROOT operator has been UNRESTRICTED since 2026-07-17, when `rootB`/`RootBoolean` were deleted, and the chain has carried a scoped `remove` constructor since 2026-07-19f), for queries with concrete objects and bare star subjects. See §3 for the gap list and §3.0 for the Direct-arm history — including the fact that **T2a `graph_reached_inv` alone did NOT widen** and carries an extra `W4NarrowT2a` bundle. |
| hence equivalent | ✅ `backend_equivalence` (T3), by transitivity through `sem`, **exactly T2b's hypotheses and scope since 2026-09-06** (the extra undischargeable `hValid` is gone, and T3 is now instantiated at a concrete executed store: `W4WitnessDirect.equivalence_applies`, `Exec.lean::graphRunOps_directArm_backend_equivalence`); plus `exclusion_effective` / `no_ghost_grant` (T6a/T6b) — the security corollaries with real exclusion content. **All three are stated over the PUBLIC graph read `GraphModel.checkPublic` since 2026-08-28c** (the fenced entry modelling `WildcardIndex.check`; `graph_correct` itself remains the internal-layer statement over `GraphModel.check` = `_check_internal`, and is what `graph_correct_public` appeals to off the fence). |
| machine-checked, axiom-audited | ✅ 0 sorries; the Audit module `#print axioms` every key theorem; `verify.sh` hard-fails on any axiom beyond `propext`, `Classical.choice`, `Quot.sound`. |
| pinned by structural correspondence review | ✅ `CORRESPONDENCE.md` — the Lean-def ↔ Python-file:line map, with the known intentional divergences listed (scoped removes (validly-stored, drained-prior), fixed two rounds, fragment surplus). **"No leaf-family split" came OFF that list 2026-09-05** — leg 7's flip re-pointed both logged write legs at the leaf-routed closure, so the split is modeled and §7.4's entry reads RESOLVED. |
| pinned by differential conformance | ✅ **check-verdict level, five corners** (`verify.sh` step 5; 310 differential-conformance tests of the 330 collected — see the per-file table above): Lean `sem` (zcli) × independent oracle × real `SetEngine` over the 25 spec-scope corpora + seeded randomized substores, **plus (Phase 6)** the Lean *operational graph model* (zcli mode `"graph"`, whose runtime output is covered by the theorem via `graphRun_reached` / `graphRun_check_eq_sem` — the driver is the chain's own constructors, by proof, not analogy) × the real Python `WildcardIndex`+`DeltaProcessor` × `sem`, over every `GRAPH_FRAGMENT` corpus (the count is `corpus.GRAPH_FRAGMENT` in the generated block above; this cell said "19" from its first writing until 2026-09-05, when it was re-checked against the live set, then 25), including two designed attack corpora (stale-edge cross-stratum re-settle; star churn over two strata). **Scope caveat on one of those corpora:** `direct_arm_exclusion` (added 2026-07-20e) is listed in `GRAPH_FRAGMENT` but is machine-checked to be OUTSIDE the final theorems' bundle (`FullScope.lean::outside_old_admission`) — its comparisons are a differential test between two implementations, NOT coverage by `graph_correct`. See §3.0. All answer suites share one query grid (`formal/conformance/grid.py`) that unions schema-DECLARED relations type-aware into the target set — so derived/boolean roots are queried on every corpus (previously targets came only from stored tuples and derived-only boolean roots went unqueried — the boolean-root conformance evidence was vacuous exactly there) — and emits concrete-named userset-shaped subjects over a bounded pool (inside the proved graph scope: `hqs` constrains only star-NAMED subjects). zcli's dispatch is itself conformance-tested (`test_cli_mode.py`; rc enumeration 0 answers-or-state / 1 usage-parse / 2 admission / 3 not-drained / 4 unknown mode / **5 `"ops"` supplied in spec mode**), so spec answers can never masquerade as graph answers and an op stream can never be silently ignored. **The remove gates:** `test_conformance_remove.py` (80 tests, the `conf-heavy` phase) pins BOTH Python backends' REMOVE paths at answer level — the real `SetEngine` and the real `WildcardIndex`+`DeltaProcessor` driven through seeded interleaved add/remove/re-add sequences over the spec-scope corpora × 5 seeds, equal to `sem` (zcli) × oracle on the FINAL store — plus Python-internal convergence pins: driven == fresh `rebuild()` / fresh add-only build over the grid AND at id-free state-fingerprint granularity (interner keys/refcounts, population masks, node_sets/member_of, flow edges; graph side: `snapshot_rows` + symbolic residues), and full-churn tests asserting complete state emptiness mid-cycle (graph: no `NodeV4`/`EdgeV4`/`ResidueV1` rows) with I12 non-mutation on a rejected repeat remove. Scope honesty: the graph-side **Python** remove path is pinned to oracle/`sem` transitively (via `graph == oracle` on the same corpora the set-engine leg pins `sem == oracle`); the graph-side **Lean** remove leg is CLOSED at the validly-stored + drained-prior scope (2026-07-19f, §4(d)) — `graph_correct` / `graph_reached_inv` / `Exec.graphRun_check_eq_sem` cover retraction of a tuple that is in the store (`t ∈ T`), from a drained prior state (`cascadeKeys = []`), whose PRE-remove store satisfies the W4 disciplines (`StoreValidRules` / `BareStarStore` / `TtuStarFree` / `htermT`, faithful to `TupleSource.remove`); and the Exec driver / zcli graph mode DRIVES removes end-to-end (2026-07-19, `5a35ec3`) — `graphRunOps` runs one runtime-gated `remove` chain leg (`removeGateB`, fail-closed) per op, zcli graph/graph-state modes take an optional `"ops"` add/remove stream (absent ⇒ the legacy add-only `graphRun`, byte-identical), and `test_conformance_remove_graph.py` differential-gates seeded streams against the real Python graph index and the oracle on the erased store. **"Driven end-to-end" carries one live exclusion:** `test_conformance_remove_graph.py::_REMOVE_EXCLUDED` is `frozenset({"direct_arm_exclusion"})`, because the chain's `remove` guard is stated over plain `StoreValidRules`, under which a Direct-arm-under-exclusion tuple is inadmissible, so `removeGateB` fail-closes on essentially every seeded stream over that corpus. Removes are therefore driven end-to-end over every in-fragment corpus EXCEPT that one (the newest). That gate compares at ANSWER level only; the Lean-vs-Python STATE comparisons for removes remain driven-vs-fresh-build Python-internal, never vs Lean. `test_conformance_generated.py` (40 tests) closes the disjoint-pools gap (§3 item 1, previously the #1 residual risk): a seeded deterministic re-implementation of the hypothesis `schema_asts` generator (NO hypothesis dependency — the formal/ convention; placed inside `formal/conformance/` so `verify.sh` gates it fail-closed) feeds GENERATED schemas + stores — shapes outside the curated corpora — asserting zcli `sem` == oracle == real `SetEngine` over the shared grid. Answer-level, spec-side only; the graph backend stays pinned by the curated corpora. The repository-wide validation matrix separately pins Python-graph × Python-set × oracle on every push. |
| … "including state-level equality" | ✅ **At a documented representation-neutral projection, per corpus.** `test_conformance_state.py` (**19** in-fragment corpora): the Lean operational graph model's FINAL MATERIALIZED STATE (zcli mode `"graph-state"` — the same `graphRun` fold, same admission/drain gates, emitting canonical edges + residues) equals the real Python graph index's final SQL state (`EdgeV4`/`ResidueV1` decoded through `NodeV4` to symbolic keys). Compared: the DIRECT edge set over `(type, name, predicate, wildcard)` node keys, and per derived key the full residue triple (`stars` shapes, `neg`/`upos` subject sets). **Five live edge projections since 2026-09-05** — this list ran P1–P6 until **P6 was RETIRED 2026-09-05**, and P7 (the `ResidueV1.version` drop, §3 item 4) is deliberately NOT renumbered — each documented and justified in `formal/conformance/extractor.py` (P1 closure rows are a function of the direct set; P2 wildcard bridges — inert, **re-verified 2026-07-26 over the widened 19-corpus set**: `bridged_in_shapes`/`bridged_out_shapes` compile EMPTY on all 19, the only non-empty pair in `SCHEMAS` being the excluded `object_wildcard` corpus, so P2 still never fires; P3 edge multiplicity — **NARROWED 2026-07-29**: compared EXACTLY on the untainted arm (153 of 171 compared edges, `nary_union`'s non-unit fan-in included), dropped only on the derived arm where Python's presence diff caps the count at 1 while the model compounds, and there golden-pinned per corpus by `test_conformance_state.py::test_derived_arm_multiplicity_ledger` — see `CORRESPONDENCE.md` §7.2; P4 all-empty residue rows the model stores and Python deletes; P5 node sets, GC'd vs never-GC'd — **no `NodeV4` row is compared at all**; ~~P6 leaf-family closure-leaf copies, whose evaluation OUTPUT — residues + derived edges — is compared exactly~~ — **P6 RETIRED 2026-09-05** by leg 7's flip: the Lean logged write path now folds the leaf-routed closure, so those rows are compared DIRECTLY rather than via their evaluation output. Measured 2026-09-05 over the 25 in-fragment corpora: 76 leaf-family rows moved from dropped to compared, `compared against Lean` 189 → **265**, and the `"P6"` ledger key is gone rather than pinned at 0). `test_conformance_enum_state.py` extends the state comparison to a deterministic stride-4 sample of the enumerated stores (257 of 1021). Attack-first: the state gate's first run FOUND P6 (state divergence under full check-parity); a deliberately corrupted extraction fails with the symmetric-difference message. |
| … "exhaustive small-scope enumeration up to the documented bounds" | ✅ **At the documented (tiny) bounds.** `test_conformance_enum.py`: ALL stores of ≤ K tuples from the declared tuple space over a 2-names-per-type pool, for **six** representative fragment shapes at a per-shape K of 3 or 4 — boolean_exclusion (K=4, 163 stores), boolean_intersection (K=4, 163), two_stratum_cascade (K=3, 299), boolean_star_exclusion (K=4, 57), wildcard_group_member (K=3, 176), ttu (K=4, 163); **1021 stores total**, spec × oracle × set engine over the shared grid, per-shape tuple-space size / K / store count all ASSERTED so the bounds cannot silently drift. Zero disagreements. `test_conformance_enum_state.py` adds a state-level leg over a **stride-4 sample, 257 of the 1021** (sample size likewise asserted). Scope honesty: the graph backend is not part of the ANSWER enumeration (runtime; it stays pinned by the curated-corpora graph + state gates), and the bounds are deliberately tiny — this earns "exhaustive up to the documented bounds", nothing more. |
| residual unverified surface | ✅ Acknowledged in full, and LARGER than §7's list — see §3. |

**The current honest claim is therefore §7's claim with one explicit
subtraction and THREE scope qualifiers:** the graph-side theorems hold at the
`W4Fragment` scope (not everything Python admits) — which since 2026-08-05 DOES
include stores written through the `Direct` arm of a derived def, the canonical
Zanzibar boolean shape, **except for T2a `graph_reached_inv`, which alone is still
VACUOUS there (§3.0, still the single most important caveat in this document)**;
state-level equality holds under the six DOCUMENTED projections of
`extractor.py` — P1–P5 and P7 since **P6 retired 2026-09-05**; a divergence inside a
projected class is pinned elsewhere, not here, and nodes are not compared at all.
(⚠ This sentence used to give **leaf-family edge content** as the example of a
projected class. That is exactly what stopped being one: the flip put those 76 rows
under the direct comparison. `ResidueV1.version` (P7) is the honest example now, being
a modelling gap with nothing on the Lean side to compare against.)
enumeration is exhaustive only up to its tiny documented bounds
(k ≤ 3 or 4 tuples, 2 names/type, six shapes). Two Python-side artifacts sit
outside the state gate's canonical form entirely — the `EdgeV4.derived` flag
and the outbox rows/watermark (drained-ness is gated as a boolean, not row
equality) — so they are pinned only by the Python-internal invariants
(I5, I10 + the §8.3 delta-scoped verifier), never against Lean. Never let a
summary round any of these back up, and never let "the algorithms are proven"
become "the code is formally verified."

## 2. The theorem inventory (English)

All in `formal/lean/ZanzibarProofs/`, all sorry-free, all axiom-audited.

* **T0a/T0b** (`Spec/WellDef.lean`): `sem` is fuel-stable over declared stores;
  stratification succeeds iff there is no derived-dependency cycle, and is
  topological.
* **T1** (`SetEngine/Correct.lean`): the set-engine model computes `sem` — full
  scope (WF + stratifiable + valid identifiers).
* **T2a** (`FullScope.graph_reached_inv`): the 8-clause graph invariant
  (structural I1–I3 + the four I6 residue-hygiene clauses) holds at EVERY
  operationally-reached state — dirty keys and mid-drain included.
* **T2b** (`FullScope.graph_correct`): graph `check` = `sem` at every fully
  drained reached state, W4 scope as above.
* **T3/T6a/T6b** (`FullScope.lean`): backend equivalence; exclusion
  effectiveness; no ghost grants.
* **T4** (`GraphIndex/Closure.lean`): path-count maintenance under edge
  add/remove.
* **T5** (`Cascade.lean`, `CascadeStrata.lean`): the cascade converges; the
  scheduler's abort branch is provably dead at ≤ 2 strata (and provably LIVE at
  3 — attack-confirmed, which is why `twoStrata` is an honest carry).
* **Phase 6 driver honesty** (`GraphIndex/Exec.lean`): the conformance CLI's
  graph mode is a fold of the chain's own constructors (`graphRun_reached`),
  its runtime gates decide the theorem's side conditions (`foldAdmitsB_iff`,
  `drainedB_iff`), and under the W4 bundles every verdict it prints is `sem`
  (`graphRun_check_eq_sem`). "Every verdict it prints" is literal since 2026-08-28c:
  the driver prints `Exec.lean::graphModeAnswers`, the capstones are stated over that
  same PUBLIC read, and the definition is statement-pinned so the two cannot silently
  drift apart (`graphModeAnswers_eq_sem`).
* **Non-vacuity** (`FullScope.lean` `W4Witness`): the hypothesis bundles are
  machine-checked inhabited by a real compiled boolean schema — the final
  theorems are not vacuous. Honesty caveat: what is kernel-checked is
  inhabitation of the hypothesis BUNDLES (`GraphAdmission ∧ W4Fragment`).
  Joint inhabitation of a drained, non-trivially-REACHED state is demonstrated
  empirically — the zcli graph mode folds real corpora through the chain and
  refuses non-drained final states — together with the proved
  `cascade2_drains`; that joint witness is not itself a kernel-checked term.

Method note: **six** false theorem statements were killed by attack-first `#eval`
refutation during the original W1→W4 arc (additive fuel bound; abstract write-step
closure; T0a without store-declaredness; the naive W2 TTU fragment; the W3a
single-edge collapse without `NoRuleOutputs`; W3d-2 "round-1 keys are stratum-1")
— and that figure is now an UNDER-count, kept only because §8 narrates those six.
The discipline has continued to kill false statements: **at least seven further
kills are recorded in `history/PROOF_STATUS.md`** during the 2026-07-18…20 remove
and Direct-arm legs, including `graph_correct_w3a_d`, the chain-level
`removeLoggedRules`-as-fold identity, the filter-all `removeEdgePair` shape, the
derived-arm `count ∈ {0,1}` invariant, the naive `reachedByW3d2_shadow_d`, the
paired `reachedByW3d2C_settled_d` / `graph_correct_w3d2_d` (see §3 item 1's
2026-07-20b note), and the first proposed `affectedKeys` fix.

The ledger (`history/PROOF_STATUS.md`) records each. **Honesty note on the
companion sentence** that used to sit here — "no adjudication event is open; none
was silently reconciled": that is an assertion over a ledger which has since grown
by an order of magnitude, and NOTHING in `verify.sh` checks it. It is re-verified
only by reading `history/PROOF_STATUS.md` end to end; as of the 2026-07-26
zero-trust review no open adjudication event was found there, but the review also
found orphaned findings that live only in `history/` and never reached any board
(e.g. the `w3cJobValid_enumJob2D` star-freeness hole; `PDerivedUserset` never
modeled in Lean). Read this as "none found on the last read", not as an invariant.

## 3. Residual unverified surface (the full list)

### 3.0 The Direct-arm vacuity - RETIRED for T2b (2026-08-05), STILL LIVE for T2a

**Read this before quoting anything else in this document.** From the first version
of this claim until 2026-08-05 this section said the headline graph theorems were
VACUOUS - not narrow, *no theorem at all* - on the most common Zanzibar boolean
shape there is:

```
can_view: [user] but not blocked
```

That was true, and it was machine-checked rather than suspected.
`W4Fragment.computedOnly` required every derived def to read only `computed` operand
leaves, and `GraphAdmission.storeValid` **was** `StoreValidRules`, whose negation is
proved at exactly such a store by
`formal/lean/ZanzibarProofs/FullScope.lean::W4WitnessDirect.outside_old_admission`:

```lean
theorem outside_old_admission : not (StoreValidRules Sd Td)
```

(`Sd` = `banned := [user]`, `approver := [user] but not banned`; `Td` = one write of
`user:alice` through the derived def's `Direct` arm. The reason is structural: the
Direct arm sits under `excl`, so `exprDirects` on the derived def is empty and no
rule can justify the stored tuple.) `history/PROOF_STATUS.md` put it in one line:
*"the CURRENT admission bundle is UNSATISFIABLE"* on that shape.

#### What changed - E-chain legs 5 and 6, 2026-08-05

The seven-leg widening arc
(`formal/history/echain-widening-plan-2026-07-28.md`) finished its T2b half:

* **leg 2 (2026-08-04)** swapped the operational enumeration, `enumJob2` -> `enumJob2D`;
* **legs 3-4 (2026-08-05)** built the `_d` projection `reachedByW3d2E_toC_d` and the
  E-chain final `graph_correct_w3d2E_d`, refactoring the audited originals into
  byte-identical wrappers;
* **leg 5 (2026-08-05)** rebased the bundles themselves - `GraphAdmission.storeValid`
  is now `StoreValidRulesD`, and `W4Fragment`'s single `computedOnly` field became
  five derived-def clauses (`computedOrDirect`, `directArmsBare`,
  `directArmsConcrete`, `computedOnlyOperands`, `noUnionDirects`);
* **leg 6 (2026-08-05)** carried it into the conformance classification.

**So for T2b and everything routed through it, the vacuity is retired.**
`W4WitnessDirect.final_applies` instantiates the *unsuffixed* `graph_correct_public` at
that store, and `final_applies4` does it at the four-tuple `direct_arm_exclusion` corpus
store verbatim. (Both instantiated `graph_correct` until the 2026-08-28c public-read
migration; they take the same hypothesis bundles either way — `graph_correct_public`
adds none.) `graph_correct` (T2b), `backend_equivalence` (T3), the T6 security
corollaries and `Exec.graphRun_check_eq_sem` / `graphRunOps_check_eq_sem` all carry
the shape.

Two things keep this honest rather than a relabeling:

* `outside_old_admission` / `outside_old_admission4` are **kept and still audited**.
  They are now the proof that the widening was contentful: the shape really was
  outside, and a rebase moved it.
* `w4Fragment_of_computedOnly` proves the pre-leg-5 six fields imply all ten, so
  nothing that held before stopped holding.

#### The one thing that has NOT changed - T2a (`graph_reached_inv`)

`graph_reached_inv` now takes a **third** bundle, `W4NarrowT2a` (schema-wide
`ComputedOnly` + the narrow `StoreValidRules`), and
`W4WitnessDirect.outside_narrow_t2a` machine-checks that the Direct-arm store fails
it. **T2a is still vacuous exactly where T2b no longer is.**

This is a declared carry with a counterexample attached. **Until 2026-09-05 it was also
declared "not a proof gap that effort would close". That half is RETIRED: what is owed
now is PROOF WORK, not a design decision.**

*The retired justification, kept dated because it was load-bearing for five weeks and
is quoted in three other docs.* Leg-0 probe D.3 (2026-07-28) machine-checked
`Inv.negEdgeFree` FALSE on the `_d` fragment: under `StoreValidRulesD` a Direct-arm
write lands an edge at the very derived R-node whose residue carries the `neg` row,
which `Inv` forbids. **Python was never wrong** - verified on the real backends:
`RuleSet.apply` routes the write onto the leaf family, so the edge lands on
`#approver.0`/`#approver.2` and never on `#approver` where the `neg` row lives;
different nodes, I6 disjointness intact, 0 mismatches over the grid and a 6-way order
sweep. That made it a modelling limit of projection **P6** (the leaf-family collapse),
and the answer picked 2026-08-05 was option (c) - model the leaf-family split and
retire P6.

**★ 2026-09-05 - option (c) LANDED, and T2a did not move with it.**
`formal/lean/ZanzibarProofs/GraphIndex/Cascade.lean::GraphState.writeLoggedRules` now
folds `rewriteClosureL S (rawWriteTuples S t)`, i.e. the Lean write path routes a
Direct-arm write onto the leaf family exactly as `RuleSet.apply` does, and projection
P6 is deleted from `formal/conformance/extractor.py`. So D.3's mechanism no longer
exists in the model. But `graph_reached_inv` still takes `W4NarrowT2a`
(`FullScope.lean`) and `W4WitnessDirect.outside_narrow_t2a` still holds - **the carry
outlived its justification.** Two steps are owed, both of them proof:

1. prove `Inv.negEdgeFree` on the `_d` fragment for the leaf-routed write leg (it is
   ONE clause, not two - see the 2026-08-08 measurement below);
2. restate `graph_reached_inv` without `W4NarrowT2a`.

Do not write "a modelling limit of P6" or "a design decision is owed" anywhere in this
document again. ((a) "restate T2a at drained states only" and (b) "weaken
`negEdgeFree` to exempt the un-cascaded write leg" remain the claim-shrinking
alternatives that nobody chose. (b) used to name `uposEdgeFree` too; that pairing was
refuted by measurement 2026-08-08 - `uposEdgeFree` is structurally immune on the
`_d` fragment, so the Inv-side obligation is ONE clause. See
`history/leaf-family-split-scope-2026-08-05.md` SS 9.2.)
The plan (SS F) predicted this asymmetry as the arc's
expected honest end state and called it the most valuable output rather than a
failure.

##### The post-flip probe, literal output (2026-09-05)

D.3's probe re-run against the post-flip model - `lake env lean` on a single file
against the already-built oleans, exit code 0, no repo file modified. Transcribed here
because the probe file lives in gitignored `.scratch/` and the 2026-08-08 original was
lost exactly that way. Schema is D.3's own `Leaf.lean::LeafWitness.Sw` (3 relations,
wildcard-carrying, two strata, three tuples, one object `doc:d1`); `variant :=
Zanzibar.Variant.plain`/`.wAny` abbreviated to `plain`/`wAny` for width, nothing else
elided.

```
("DOMAIN SIZE (routing-independent key pairs)", 144)
("PRED NAMES",
  ["banned", "banned.0", "banned.1", "banned.2", "viewer", "viewer.0", "viewer.1",
   "viewer.2", "approver", "approver.0", "approver.1", "approver.2"])
("rawWriteRels S tW", ["approver.0"])
("rawWriteTuples S tW",
 [{ subject := { type := "user", name := "bob", predicate := "..." },
    relation := "approver.0",
    object := { type := "doc", name := "d1" } }])
("rewriteClosureL S (rawWriteTuples S tW)",
 [{ subject := { type := "user", name := "bob", predicate := "..." },
    relation := "approver.0",
    object := { type := "doc", name := "d1" } }])
("SUBJECT EDGES (A: writeLoggedRules, pre-cascade)",
 some [({ type := "user", name := "bob", pred := "...", variant := plain },
        { type := "doc", name := "d1", pred := "approver.0", variant := plain }),
       ({ type := "user", name := "*", pred := "...", variant := wAny },
        { type := "doc", name := "d1", pred := "approver.1", variant := plain }),
       ({ type := "user", name := "*", pred := "...", variant := wAny },
        { type := "doc", name := "d1", pred := "viewer", variant := plain }),
       ({ type := "user", name := "bob", pred := "...", variant := plain },
        { type := "doc", name := "d1", pred := "approver.2", variant := plain }),
       ({ type := "user", name := "bob", pred := "...", variant := plain },
        { type := "doc", name := "d1", pred := "banned", variant := plain })])
("SUBJECT RESIDUE ROWS (A)",
 some [({ type := "doc", name := "d1", pred := "approver", variant := plain },
        "approver",
        { stars := [("user", "...")],
          neg := [{ type := "user", name := "bob", predicate := "..." },
                  { type := "user", name := "bob", predicate := "..." }],
          upos := [] })])
("A vs B: (rows identical?, A-only edges, B-only edges)",
 some (true,
  [({ type := "user", name := "bob", pred := "...", variant := plain },
    { type := "doc", name := "d1", pred := "approver.0", variant := plain })],
  [({ type := "user", name := "bob", pred := "...", variant := plain },
    { type := "doc", name := "d1", pred := "approver", variant := plain })]))
("DRAINED? (prefix, subject-A, cascaded-C)", some (true, false, true))
("PROBE",
 some ("(A subject-leafrouted, B bare-preflip, C drained, D bridge-sabotage)",
  { edges := 5, rows := 1, negTested := 2, negFree := true,  uposTested := 0, uposFree := true },
  { edges := 5, rows := 1, negTested := 2, negFree := false, uposTested := 0, uposFree := true },
  { edges := 5, rows := 1, negTested := 4, negFree := true,  uposTested := 0, uposFree := true },
  { edges := 6, rows := 1, negTested := 2, negFree := false, uposTested := 0, uposFree := true }))
("PROBE, PREFIX ORDER SWAPPED (A, B, C, D)"
  -- identical 4-tuple of ProbeResults to the line above)
```

What that does and does not license, in the order that matters:

* ⚠ **It is a MEASUREMENT, not a proof, and must not be upgraded to "CONFIRMED".** The
  instrument evaluates the fuel-capped executable probe
  `GraphIndex/State.lean::GraphState.reach` (`= reachB σ.edges (σ.nodes.length + 1)`),
  NOT `NReaches`, which is what `Inv.negEdgeFree` is stated over.
* **The positive control reproduced the kill in the SAME run.** Leg B drives the
  pre-flip bare write over the same drained prefix state and gives `negFree := false`
  at `negTested := 2`, where leg A gives `negFree := true` at the same `negTested :=
  2` - and `rows identical? = true`, so those are the same two (row, `neg` member)
  pairs, not two different tests.
* **The 2026-08-08 vacuity trap did NOT recur:** `rows := 1` on every leg, and the row
  is keyed at the BARE `doc:d1#approver` node - the key whose falling out of the
  domain produced the vacuous green last time. The key domain is routing-independent
  by construction (scope doc SS 9.1): tuple-corpus objects x `predNames S` x
  `predNames S` = 1 x 12 x 12 = 144 pairs, never derived from `sigma.nodes`.
* **Second instrument control (D):** adding a hypothetical `doc:d1#approver.0 ->
  doc:d1#approver` bridge edge turns the subject state RED (`edges := 6, negFree :=
  false`), so the probe is reachability-sensitive, not merely key-equality-sensitive.
* ⚠ `negTested` counts pairs WITH MULTIPLICITY (`neg := [bob, bob]`), so today's
  2 / 2 / 4 is not comparable one-for-one with the 2026-08-08 run's 1 / 1 / 3.
* ⚠ The subject state is deliberately NOT drained (`(prefix, A, C) = (true, false,
  true)`): it is the intermediate post-write pre-cascade state, so no headline theorem
  is instantiated at it.
* `uposTested := 0` on every leg - a re-observation of the structural immunity above,
  not new evidence about the `upos` clause.
* **Scope:** one schema shape, one object, two prefix orders, the WRITE leg only.
  Nothing about `removeLoggedRules`, the other `Inv` clauses, Python, or longer op
  streams.

#### What this does to the conformance evidence

`direct_arm_exclusion` moved from `test_conformance_graph._DIFFERENTIAL_ONLY` into
`_THEOREM_BACKED` on 2026-08-05, so the split is now `(23, 0)`. That move is
licensed by `W4WitnessDirect.final_applies4` and by nothing weaker: both bundles are
STORE-indexed, so the witness is taken at `Td4` - the corpus's own four tuples - not
at the one-tuple minimal store. A `lean-graph != spec` disagreement on that corpus
would now contradict a machine-checked theorem.

Two carve-outs survive and must not be over-read away:

* the **T2a** asymmetry above (that module compares `check` answers, which is T2b's
  business, so the classification is unaffected - but `Inv` is not proved there);
* the **Lean REMOVE gate**: `removeGateB` decides plain `storeValidRulesB`, so the
  corpus stays in `test_conformance_remove_graph._REMOVE_EXCLUDED` - now for that
  reason ALONE, no longer for the admission reason recorded there before leg 5.
  Lifting it needs a `storeValidRulesDB` decision procedure, its soundness lemma and
  a widened `remove` constructor: its own leg.

Finally, the standing hazard that made this section necessary is unchanged: **the
CLI does not gate on `GraphAdmission`/`W4Fragment` at all** (rc 2/3 test run-success
and drained-ness only). Membership in `GRAPH_FRAGMENT` is not membership in the
proved fragment; only a written per-field argument or a Lean witness makes it so.

### 3.1 The list

Everything §7 lists, plus the fragment carries:

1. **Model-to-code fidelity** — the theorems are about the Lean models; the tie
   to Python is `CORRESPONDENCE.md` + empirical conformance. A Python behavior
   outside the corpora/grids could diverge without failing the gate. *Narrowed
   2026-07-12:* the schema-SHAPE half of this risk — a `sem`/model-fidelity
   divergence on shapes outside the curated corpora, previously invisible to
   every gate because the generated (hypothesis) and curated pools were
   disjoint — is closed AT ANSWER LEVEL, spec-side, by
   `test_conformance_generated.py`. Behaviors outside the generated envelope,
   and the graph backend on non-curated shapes, remain unpinned.

   ***Evidence that `CORRESPONDENCE.md` review is a SAMPLING process, not a proof
   — 2026-07-20b.*** A genuine model-vs-Python infidelity was found **inside the
   audited chain, after this effort was described as "complete"**, and it was found
   by attack-first `#eval` while widening scope — not by correspondence review, and
   not by any gate. Lean's `affectedKeys` (`Cascade.lean`) was **reader-only**: it
   derived dirty keys from `computedRefs` / `_fan_out via='computed'` and lacked
   Python's **LeafFamily own-key branch** (`processor.py`: a delta on a leaf-family
   row also dirties that family's OWN derived key). Consequence at the Direct-arm
   schema: the seed write's own key was never dirtied, the drain was a no-op, and
   the resulting state satisfied `cascadeKeys = []` (drained) while
   **`check = true` and `sem = false`** — a modeled drained state that grants a
   `sem`-false query. `reachedByW3d2C_settled_d` and `graph_correct_w3d2_d` were
   therefore FALSE as specified, and were killed. Fixed 2026-07-20c by adding the
   own-key branch via a `Delta.leaf` provenance tag (a first, naive fix was itself
   attack-killed as unfaithful before the real one landed). Two things about this
   are load-bearing for how much weight `CORRESPONDENCE.md` can bear: (a) the
   omission was **benign within the then-proved `ComputedOnly` scope** — no
   leaf-family delta ever lands on a derived key there — so it did not invalidate
   any shipped theorem, but that was luck of scope, not review; (b) the Lean
   **docstring immediately above the definition CLAIMED the missing branch**, so a
   reviewer cross-checking the two artifacts against each other would have read
   agreement where the code disagreed. Recorded in `history/PROOF_STATUS.md`
   (2026-07-20b/c) and `CORRESPONDENCE.md` §7; it had reached NEITHER this document
   nor `ARCHITECTURE.md` until 2026-07-26.
2. **The Python COMPILER artifacts are trusted, not modeled.** `compile_ruleset`'s
   outputs — the taint computation, strata assignment, derived-predicate plans
   and fan-out tables — have no Lean counterpart: the
   Lean model reads the RAW boolean defs and derives taint/strata/jobs itself
   (`isDerived`, `stratify`, the state-derived job enumerations). The pins are
   the compiled-RuleSet snapshot tests (`tests/snapshots/`) and the conformance
   corpora (which drive the real compiled artifacts through the Python write
   path); a compiler bug on a schema shape those pins don't exercise would not
   fail any Lean gate.
   ★ **`leaf-family routing` was in that list until 2026-09-05 and is not any more.**
   Leg 7 models the allocation (`GraphIndex/Leaf.lean`'s `persistedLeaves`), the storage
   fan-in (`rawWriteRels`/`rawWriteTuples`) and the closure-leaf rule minting
   (`GraphIndex/LeafRules.lean`'s `leafRewrites`), and the flip re-pointed both logged
   write legs at `rewriteClosureL`. With P6 retired the routing is now differentially
   compared per corpus rather than trusted.
3. **Fragment scope** (each a documented gap, none hidden — `history/ROADMAP.md`
   "W4 — honest gaps"): > 2 derived strata; non-`ComputedOnly` derived operand
   leaves — `Direct`/TTU arms under a boolean, i.e. `PDerivedTTU`/`PDerivedUserset`
   plan leaves (**this is the §3.0 vacuity, not a coverage narrowing — the
   `Direct`-arm half of it makes the final theorems say nothing at all about
   `can_view: [user] but not blocked` stores**; the derived-def ROOT operator is
   NO LONGER a gap — see the note);
   declared wildcard-userset restrictions (`[T#p:*]`-style) anywhere; stored
   object-wildcard (`w_all`) tuples; stored userset-star tuples; **removes**
   (now CLOSED for a VALIDLY-STORED tuple from a drained prior state, 2026-07-19f
   — the `remove` constructor on `ReachedByW3d2`/`C`/`E` carries T2a/T2b over
   remove-states under `t ∈ T` + `cascadeKeys = []` + the pre-remove store's
   `StoreValidRules`/`BareStarStore`/`TtuStarFree`/`htermT` disciplines, faithful
   to `TupleSource.remove`; BOTH Python remove paths were already answer-pinned via
   `test_conformance_remove.py`; the Exec driver / zcli graph mode now DRIVES
   removes end-to-end too (2026-07-19, `graphRunOps` / `removeGateB` /
   `test_conformance_remove_graph.py`), so remove-correctness is now both PROVED
   and end-to-end DRIVEN **over every in-fragment corpus except one** —
   `test_conformance_remove_graph.py::_REMOVE_EXCLUDED` is
   `frozenset({"direct_arm_exclusion"})`, because the chain's remove guard
   is stated over plain `StoreValidRules` and therefore fail-closes
   (`removeGateB` rejects, rc ≠ 0) while a Direct-arm-under-exclusion tuple is in
   store; that corpus's Python remove path is still differentially gated by
   `test_conformance_remove.py`, just not against Lean — and the guard's
   validly-stored precondition was APPROVED by Avery 2026-07-19); star-subject
   queries with non-bare predicates; star-object queries on the graph side.
   *Empirical note (2026-07-12k / 2026-07-17): the derived-ROOT operator is no
   longer a fragment gap — union- and computed-rooted derived defs entered the
   proved scope 2026-07-17 (`W4Fragment.rootB`/`RootBoolean` deleted; the shape
   condition is `ComputedOnly` alone; taint routing on `schemaRewrites` now
   mirrors `compile_ruleset`), and their corpora (`taint_union_over_boolean`,
   `taint_union_userset_arm`, `taint_computed_root_over_boolean`) are now IN
   `GRAPH_FRAGMENT` at both check AND state level. Only the object-wildcard corpus
   stays probe-confirmed-but-excluded — zero check-level divergence observed, the
   exclusion is proof-scope (`bareStar`), not a known disagreement. **Caveat on
   that last inference (added 2026-07-26):** "the exclusion is proof-scope, not
   behavioral" is an inference from CHECK-level evidence, and this repo has already
   had it fail once — on 2026-07-17 a real model-vs-Python divergence was found at
   STATE level in exactly that situation. The object-wildcard corpus has never been
   probed at state level. Treat the sentence as a hypothesis, not a finding.*

   **The two `GraphAdmission` fields added by the flip (`FullScope.lean::GraphAdmission`,
   13 fields), classified with `test_w4fragment_scope_pin.py`'s vocabulary (LOUD = Python
   raises on schemas/writes outside the field; SILENT = accepted; MIXED = some sub-cases
   raise), added 2026-09-06 (`TK55`):**

   | field | demands | class | evidence |
   |---|---|---|---|
   | `keysNonempty` | every declared relation name is non-empty | **LOUD** | refused at parse time by both parsers as of 2026-09-06 — `zanzibar_utils_v1.py::parse_schema_ast`'s empty-name lock and, independently, `tests/oracle.py::parse_schema_ast`'s; pinned by `tests/test_reg_empty_relation_name.py`. ⚠ It was SILENT until that day, while `FullScope.lean` and `CORRESPONDENCE.md` §6 both claimed LOUD ("rejected at parse time by the identifier charset") — the charset is write-path only, and the empty name was reachable through `define : viewer` (untainted: graph accepts the write and answers `check=False` against oracle `True`; boolean: graph refuses in `DeltaProcessor._write_derived`, set engine accepts) |
   | `noLeafSubjects` | no rule of the full leaf-routed rule set mints a leaf-named (`'.'`-carrying) SUBJECT predicate | **LOUD** | refused at parse time by the PRODUCTION parser: a `'.'` in a declared name is `zanzibar_utils_v1.py::parse_schema_ast`'s dot-lock (pinned by `tests/test_boolean_compile.py::test_dot_reserved_in_relation_declarations`), and a `'.'` in any referenced name — TTU target/tupleset, `Direct` restriction predicate, `computed` operand — is `zanzibar_utils_v1.py::_validate_ast_references` (pinned by `tests/test_openfga_json.py::test_rejects_reserved_dot_in_referenced_names`); both backends construct through that parser, so nothing outside the field can be built. ⚠ Unlike `keysNonempty`, this lock is NOT mirrored in the oracle's parser: `tests/oracle.py::parse_schema_ast` accepts `define ...: viewer` (probe 2026-09-06), so the oracle cannot refuse it independently — a `TK55`-shaped follow-up, not a scope hole |

4. **The state-gate projections** — state-level conformance IS implemented
   (§1), but a divergence strictly inside a projected class would not fail it:
   ~~leaf-family edge content (P6 — pinned instead by the plans' evaluation
   output, check conformance, and the RuleSet snapshots)~~ — **no longer a
   projected class: P6 RETIRED 2026-09-05**, the flip put the leaf rows under a
   direct state comparison (76 rows, `compared` 189 → **265**, measured
   2026-09-05 over the 25 in-fragment corpora), edge multiplicity
   (P3 — **derived arm only since 2026-07-29; the untainted arm is compared
   exactly and the derived arm is golden-pinned**), bridge edges (P2 — inert), node GC
   (P5 — **`NodeV4` rows are not compared at all**), and residue versioning
   (**P7** — `ResidueV1.version`, declared as a projection 2026-07-27; it was
   silently dropped before). Each is documented with its justification in
   `formal/conformance/extractor.py`.

   **QUANTIFIED, because "state-level equality" implies far more than this gate
   compares — and since 2026-08-05 the quantification is GENERATED, not narrated.**
   The live figures are in the **"State-gate projection ledger"** table of this
   file's generated counts block above (`extractor.py::graph_fragment_ledger`,
   checked by `verify.sh` step 4e). **Read them there.** This paragraph used to
   restate them and had drifted to the point where this document stated two
   different values for the same quantity — the exact defect the counts pin was
   built to stop, recurring inside the pin's own file because the pin covers one
   delimited block and prose outside it is still hand-maintained (`doc_counts.py`
   says so in as many words).
   For the record, the 2026-07-27 figures this paragraph carried — 21 corpora,
   447 raw rows, 231 P1, 0 P2, 62 P6, 154 compared, 235 `NodeV4` (194 referenced /
   41 invisible), 11 residue rows over 5 corpora, all `|stars|=|neg|=1` — are
   **superseded in every leg but the P2 zero**. The `NodeV4` referenced/invisible
   split re-derives as 217/49 but is deliberately NOT pinned: it has no in-repo
   implementation to reuse and the reconstruction is method-sensitive
   (`CORRESPONDENCE.md` records the caveat).

   **Three things follow, and they are the honest reading of §1's "state-level
   equality" row.** (i) **P5 is not a formality.** The Lean `GraphState` *does*
   have a `nodes` field, but zcli's `"graph-state"` dump emits only edges and
   residues, the model never GCs while Python does (so set equality is false by
   design), and Python's `NodeV4.implicit` / `reference_count` have no Lean
   counterpart at all — there is no node property to compare. What is gated
   instead is Python-side only:
   `test_conformance_state.py::test_python_nodes_are_all_justified` (no orphan
   node rows; 0 measured). `CORRESPONDENCE.md` §7's 2026-07-17 concession that
   node-flag behaviour is "invisible to the gate by construction" is exactly
   this, now with numbers. (ii) **P7 means invariant I7 (residue-version
   monotonicity) is gated by nothing formal** — Lean's `Residue` has no version
   field, so this is a modelling gap, not a representation difference; I7's only
   pins are `tests/` paranoia runs. (iii) **The residue half was near-vacuous**
   and is now partly closed: `corpus.py::SCHEMAS`'s `"residue_rich"` entry (listed in
   `corpus.py::GRAPH_FRAGMENT`, pinned by
   `test_conformance_state.py::test_residue_rich_corpus_is_really_rich`) is the first corpus
   with a multi-shape `stars`, a multi-subject `neg` and a `upos` member on two
   derived keys. Most corpora still contribute edges only.
5. **The representation layers** — interner/bitmap (`setengine`), SQL rows /
   ref-counted closure storage (`index_v4`), `rebuild()`/crash recovery, and the
   whole **sessions/transactions/concurrency** layer. That last one is wider than
   the `_lock_store` protocol this item used to name alone, and none of it is in
   any Lean model:
   * `ReachabilityIndex._lock_store` (the graph store-row `FOR UPDATE` lock);
   * `TupleSource._lock_source` (the `SchemaV4`-row lock) and the **writer lock
     ordering** between the two (source lock BEFORE graph store lock);
   * **multi-instance / HA replica tailing** — `catch_up_evaluator` →
     `SetEngine.apply_logged`, i.e. instance-local set engines synced by tailing
     the permanent log, and the per-`Session` state that makes that safe;
   * catch-up cadence and freshness-token (`at_least`) plumbing.

   `CORRESPONDENCE.md` §7 ("Multi-instance scheduling is OUT-OF-MODEL,
   2026-07-23") states the reasoned argument for why no Lean change was needed —
   a replica's state is the fold of a log PREFIX and every prefix is a valid
   store, so T1 applies pointwise — but that argument is a reasoned scope
   boundary, **not** a machine-checked one, and the lock discipline it depends on
   is what makes "the log is one serial admitted-op sequence" true in the first
   place. There is no TLA+ phase; concurrency coverage in CI is SQLite-shaped,
   where both locks render to no-ops.
6. **Bulk build / bulk backfill — a second, unmodeled constructor of index
   state, and it is the DEFAULT.** `index_v4/bulk_build.py` (P13/N18) and
   `index_v4/bulk_backfill.py` (R4-BF) construct the final pre-backfill and
   post-backfill index state **directly** — one in-memory closure pass +
   bulk INSERTs, T4's closed form computed in closed form rather than
   incrementally — instead of replaying routed triples through the incremental
   `WildcardIndex.add_tuple` / `DeltaProcessor` path that the Lean `ReachedBy`
   chain models. `connectedstore.build_index` takes `bulk: bool = True`, so this
   is the path a real bootstrap takes. Its `bulk=False` side is NOT the modeled
   path either (this item said it was until 2026-09-06): it loads every tuple
   through `add_tuple` and then runs `DeltaProcessor.backfill()`, which
   `CORRESPONDENCE.md` §7 lists as unmodeled. The modeled constructor is the
   ONLINE one — logged writes each followed by a same-transaction cascade, the
   `ReachedBy` chain's only constructors. **Scope statement (`P17`, 2026-09-06):
   the headline theorems hold for indexes grown from `emptyState` by logged
   writes and cascades; a bulk-built index is pinned to that model-driven state
   by `formal/conformance/test_conformance_bulk_state.py::test_state_bulkbuild_vs_pythongraph`
   over the 25 `GRAPH_FRAGMENT` corpora (exact multiplicities on every arm,
   derived flags, residues; a second leg diffs the bulk state directly against
   the Lean dump), not by the proof.** "Every arm" means the DIRECT multigraph
   only: the canonical form is `extract_sql_state`'s P1 projection, which keeps
   `direct_edge_count > 0` rows and never reads `indirect_edge_count`, so the
   bulk builder's materialized closure (Phase-P path counts, pure-indirect rows)
   is outside that module's reach and is pinned only by `tests/test_bulk_build.py`
   (its module docstring records the two green sabotages). What that test does not cover: remove
   histories (only `tests/test_connectedstore_build.py::test_built_index_equals_live_maintained`'s
   single add+remove history reaches the bulk builder), the outbox rows bulk
   writes (one ADDED per closure pair; the Lean dump has no outbox channel), and
   the bridge / I14 crossable-middle phases, which no `GRAPH_FRAGMENT` corpus
   reaches — bridges are pinned by `tests/test_bulk_build.py`'s `wildcards` and
   `rc2_star_tupleset` corpora; the I14 loop (`index_v4/bulk_build.py:206-221`)
   is pinned by NOTHING (disabling it was green in every `build_index` caller
   in `tests/` and in the conformance module — the complete reach of
   `bulk_build`, which only `connectedstore/build.py` imports, 2026-09-06).
   The Python-vs-Python identity gate remains as a second net
   (`tests/test_bulk_build.py`, 7 corpora: same snapshot built both ways must
   produce byte-identical state, plus the I1–I13 checker and an oracle
   read-parity grid). Both surfaces are documented in
   `CORRESPONDENCE.md` §7/§8.1 — this document and `ARCHITECTURE.md` are simply
   the two honesty ledgers that stopped being updated; that omission was found by
   the 2026-07-26 zero-trust review, not by any gate.
7. **Non-stratifiable schemas** (rejected upstream; the model assumes
   stratifiability). The `expand` / `lookup` / `lookup_reverse` (list-objects /
   list-users) read surfaces are **not yet modeled in Lean** — a deferred
   low-priority TODO (§4, last item), NOT a permanent exclusion; both backends'
   surfaces are pinned empirically by `tests/test_lookup_oracle.py` and, since
   2026-07-13, the hypothesis campaign (`tests/test_hypothesis.py`).
8. **The toolchain trust base** — Lean 4 kernel + the pinned Mathlib, and the
   conformance harness's own encoder (`encode.py` reuses the independent
   oracle's parser precisely so one backend parser bug cannot corrupt both
   sides).

**Resolved divergence (found 2026-07-12 by the new repo-side lookup gate;
FIXED 2026-07-13, Python-side).** `tests/test_lookup_oracle.py` (the
brute-force oracle-lookup parity gate, outside `formal/` — it pins
`lookup`/`lookup_reverse`/`expand` by composing `oracle.check` over the
candidate universe) found a CHECK-level graph-vs-set divergence, wider than
the lookup surfaces it was built for: on a derived TTU, userset-shaped
subjects whose truth flows through a stored tupleset parent answered
**False on the graph index** where the oracle AND both set engines answer
**True** — two shapes, the from-chain userset itself and userset membership
lifted through the parent's target (the residue `upos` never received
cross-object userset memberships); it also reproduced on
`demorgans_reverse.fga` (X4; plus three narrower lookup-only divergences
X1–X3). All four were fixed 2026-07-13 **on the Python side only** — the
graph delta processor gained the from-chain identity rule + a from-chain
reconcile pass + the cross-object `upos` lift; the set engine gained
write-time reverse-dependency interning — the boolean spec being SILENT on
these shapes, the oracle was followed (adjudication recorded in
`docs/spec-deviations.md`, both 2026-07-13 entries). The strict xfails were
flipped to plain regression pins (the gate now stands at 16 passed, 0
xfail, with its one-sided walk escapes removed — properties strengthened,
never relaxed), and the repo matrix grids were widened to query from-chain
and userset subjects on derived-TTU families (closing the P7 grid gap that
hid X4). **The FORMAL claim is unchanged:** derived-TTU shapes remain
outside `W4Fragment` (`computedOnly` requires derived defs to have no `ttu`
leaves, `FullScope.lean::GraphAdmission` / `ReconcileCorrect.lean::ComputedOnly`; `PDerivedTTU`
plan leaves stay item 3's documented gap), every new graph behavior is
gated on leaf kinds absent from the in-fragment corpora, and the
state-level gate (exact edge+residue equality vs Lean) passed unchanged —
no theorem, gate, or bound above widened.

**`sem` anchor (2026-07-13).** The fix above followed the ORACLE where the
boolean spec is silent; the Lean spec `sem` — the formal trust root the oracle
stands in for — is now checked directly on these shapes. Three spec-side
corpora (`TTU_USERSET_SCHEMAS` in `formal/conformance/corpus.py`: from-chain
userset through an untainted TTU, the cross-object membership lift, and
from-chain userset through a TTU over a DERIVED boolean target) run through
`test_conformance_spec`'s full-scope spec/oracle/set-engine comparisons, and
`sem` == oracle == set engine on every grid query (the from-chain userset
answers True on all three, matching the oracle the graph was fixed toward). So
the adjudication is anchored to `sem`, not asserted from the oracle alone. The
corpora are kept OUT of `SCHEMAS`/`GRAPH_FRAGMENT` — the shapes are outside
`W4Fragment`, so the graph/state/remove gates do not carry them; the anchor is
spec-side, where the set engine is proved to compute `sem` at full scope (T1).

## 4. Where the next marginal assurance is

**Every item still open in this section now has a board row** (added 2026-08-16, after an
audit found this section ranking work [`HANDOFF.md`](../HANDOFF.md) did not list at all —
the board's charter claims to rank *every* open item, so the omission made that charter
false): (c)(i) → `P5`, on the leg-7 chain `P3`/`P4`/`P14`; (c)(ii) → `P15`, its
remove-guard half → `P9`; (d)'s suspected under-claim → `AW-1`; (e) → `P16`; (g) → `P19`;
(h) → `P17`; (i) → `P18`; (j) → `SD-1`. The board's `pri` column is what *ranks* them; the
descending value-per-effort argument below is the reasoning behind that ranking, and the
two must not be allowed to disagree.

Items (a) state-level graph conformance and (b) exhaustive small-scope
enumeration are DONE (2026-07-12, §1 rows above). Two further answer-level
gates landed the same day: the generated-schema gate closed the
disjoint-pools risk (formerly item 1's biggest exposure) spec-side, and the
remove-path gate pinned the set engine's remove path (answer level +
rebuild state-fingerprint). A **2026-07-13** addition pinned the GRAPH-INDEX
Python remove path too (answer level + fresh-build state convergence + full
drain, `test_conformance_remove.py::test_graph_*`). In descending
value-per-effort, what remains: (c) further widening `W4Fragment` — the
derived-ROOT operator gap is **DONE 2026-07-17** (union- and computed-rooted
derived defs now in scope: `rootB`/`RootBoolean` deleted, the taint filter on
`schemaRewrites` restored set/graph parity and closed a stale userset-sourced
fanout edge, pinned by `taint_union_userset_arm`); the **`Direct`-arm half of the
LEAF gap is DONE 2026-08-05** — the E-chain widening arc's legs 2→6 carried it all
the way onto the FINAL unsuffixed theorems (`enumJob2D` swap, leg 2; the
`reachedByW3d2E_toC` `_d` projection, legs 3–4; **`GraphAdmission.storeValid` →
`StoreValidRulesD` and `W4Fragment.computedOnly` → the five derived-def clauses,
leg 5**; the conformance reclassification, leg 6), so `graph_correct` and
everything routed through it now cover `can_view: [user] but not blocked` and are
no longer vacuous there (§3.0). **Two pieces of that gap survive and are the
highest-value remaining items:** (i) **T2a alone did not widen** — `graph_reached_inv`
carries an extra `W4NarrowT2a` bundle that the Direct-arm store provably fails
(`outside_narrow_t2a`), and since **2026-09-05 what is owed is PROOF WORK, not a design
decision**: leg 7's flip landed (`GraphState.writeLoggedRules` folds
`rewriteClosureL S (rawWriteTuples S t)`; projection P6 deleted), so probe D.3's
mechanism — and with it the "P6 leaf-family modelling limit" justification this item
used to carry — is gone, while the bundle is still taken. The two steps are: prove
`Inv.negEdgeFree` on the `_d` fragment for the leaf-routed write leg, then restate
`graph_reached_inv` without `W4NarrowT2a` (§3.0 has the post-flip probe output and its
caveats); (ii) the remaining leaf shapes —
`PDerivedTTU`/`PDerivedUserset` (TTU/userset arms under a derived def, still
`False` under `ComputedOrDirect`) and > 2 strata — plus the Lean REMOVE guard,
which still decides plain `storeValidRulesB` and so keeps `direct_arm_exclusion`
out of the remove-driving gate; (d) remove
legs on the LEAN side — **DONE 2026-07-19f** at the validly-stored + drained-prior
scope: the `remove` constructor now lives on `ReachedByW3d2`/`C`/`E`, so T2a
(`graph_reached_inv`) and T2b (`graph_correct`) — and `Exec.graphRun_check_eq_sem`
— cover retraction of a tuple that is in the store (`t ∈ T`) from a drained prior
state (`cascadeKeys = []`), with the PRE-remove store's `StoreValidRules` /
`BareStarStore` / `TtuStarFree` / `htermT` disciplines carried on the guard
(faithful to `TupleSource.remove`, which only retracts validly-admitted tuples;
these are exactly the `W4Fragment` carries `graph_correct` already assumes). So
the Lean model IS now a post-remove reference under that precondition — the honest
claim is "correct after removing a VALIDLY-STORED tuple from a drained state,"
never more. The Exec driver / zcli graph mode now DRIVES removes end-to-end too
(2026-07-19, `5a35ec3`): `graphRunOps` runs one runtime-gated `remove` chain leg
(`removeGateB`, fail-closed) per op, zcli graph/graph-state modes take an optional
`"ops"` add/remove stream, and `test_conformance_remove_graph.py` differential-gates
seeded add/remove/re-add streams (zcli `graphRunOps`) against the real Python graph
index and the oracle on the erased store (ANSWER-level) — so remove-correctness is
now both PROVED over the operational chain AND DRIVEN end-to-end — **except over
`direct_arm_exclusion`, which `_REMOVE_EXCLUDED` skips because the guard
fail-closes there (§1's remove row, §3 item 3)**. The guard's
validly-stored scope decision (it strengthens an audited inductive) was reviewed
and **APPROVED by Avery (2026-07-19)** as the honest, faithful framing — no longer
an open flag;

⚠ **This item's scope wording is suspected to UNDER-claim (open, board row `AW-1`, small).**
It was written 2026-07-19f and has not been re-read since the remove leg closed, so the
"validly-stored + drained-prior" hedging may now be narrower than what is actually proved.
**Plausibly subsumed by the `ZT-P3-4` / `ZT-P3-5` sweeps — never confirmed either way.**
**Completion criterion:** re-derive the claim from the current `remove` constructor's
hypotheses and either tighten this paragraph or record that it was already correct. Do
**not** widen the wording without re-reading the guard, since §1's remove row and §3
item 3 depend on it. Note `_REMOVE_EXCLUDED` (board row `P9`) is a *different*, still-live
gap.

(e) widening the enumeration/state bounds — **partly DONE**: the enumeration now
runs six shapes (a userset/wildcard shape and a TTU shape added), K = 4 on four of
them, and a state-level leg over a stride-4 sample (`test_conformance_enum_state.py`,
257 of 1021 stores); what remains under (e) is the graph backend in the ANSWER
enumeration, K = 4 on the two capped shapes, and state coverage beyond the 25 %
sample. Item (f) — fixing the derived-TTU userset-subject check divergence and
flipping its strict xfails — is **DONE** (2026-07-13, Python-side; §3's resolved
note). New under this heading since 2026-07-26: **(h) model or explicitly
scope-exclude the bulk build/backfill constructor** (§3 item 6 — it is the default
`build_index` path and has no Lean counterpart; the scope-exclusion half is DONE
2026-09-06 under `P17`: §3 item 6 now states the scope, and
`formal/conformance/test_conformance_bulk_state.py::test_state_bulkbuild_vs_pythongraph`
pins the bulk-built state to the model-driven state over 25 corpora — the
"model it" half, a Lean `bulk = replay` theorem, is a SOMEDAY row, not started), and **(i) the concurrency /
multi-instance layer** (§3 item 5 — the deferred TLA+ phase, never started).

**(j) the two SCOPE REJECTIONS — object wildcards on derived relations, and wildcard
usersets over derived relations.** Both raise `UnsupportedByGraphIndex` at compile time
(`zanzibar_utils_v1.py`); they are the only constructs the repo rejects outright rather
than models, and the sole items not modeled in Lean at all. The documented fix is a
**symmetric subject-keyed residue** (symbolic composition through residues). Tracked as
board row `SD-1` (SOMEDAY).
**Priority argument CORRECTED 2026-07-29** — the old "low priority, the OpenFGA DSL does
not support these either" is INVALID (`ZT-P5` bullet 1): this repo ships object wildcards
as a deliberate extension BEYOND OpenFGA (no DSL syntax; passed via
`object_wildcard_shapes`), so "OpenFGA lacks it" cannot deprioritise a construct the repo
invented. The honest surviving argument is different: no concrete need has appeared, the
rejection is LOUD (compile-time, never a silent wrong answer), and the one plausible
pattern (broad grant + per-object boolean exception) is expressible via a supported
TTU/hierarchy. **Revisit on a concrete need — not on the old reasoning.**
**And that deferral is EVIDENCE-BACKED, not assumed (measured 2026-08-11):** a crawl of a
real OpenFGA corpus (canonical `openfga/sample-stores` + internal models) measured **48
schema files, 22 compile, and `UnsupportedByGraphIndex` rejections = 0** — no real schema
hit either rejection — so do NOT re-file "go measure real schemas against these
rejections"; that instrument was built, run, and retired on 2026-08-11
(`docs/history/handoff-status-2026-08.md`, §"Retired 2026-08-16 (leg 7 4c-i session)",
the retired "Vendor a corpus of REAL OpenFGA schemas, crawled from the wild" item).
⚠ **Scope note (2026-07-28):** wildcard usersets over an UNTAINTED relation are fully
supported and have corpus coverage; **only the DERIVED case is rejected.** Do not widen the
rejection message or the tests to imply otherwise.
**Completion criterion:** both rejections lifted, the validation matrix 4-way green on the
two shapes, and the residue composition either modeled in Lean or logged in
`formal/CORRESPONDENCE.md` §7.

Lowest priority — **(g) model the read surfaces in Lean** (`lookup` /
`lookup_reverse` / `expand` = list-objects / list-users): give them a Lean spec
(a comprehension over the already-proved `sem`) and prove the Python computes
it. Deferred to the eventual full-spec effort — the definition is cheap, but the
completeness proof pulls in the interner/candidate-universe layer T1 abstracts
away, and the surface is empirically subtle (the X1/X3/X4 divergences all lived
here). Until then both backends' surfaces are pinned by
`tests/test_lookup_oracle.py` + the hypothesis campaign (added 2026-07-13), not
proved. This is a deferred TODO, NOT a permanent non-goal.
