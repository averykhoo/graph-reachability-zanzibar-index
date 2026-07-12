# FINAL_REVIEW.md — what is proved, what is pinned, what is not

Phase 6 item 3 (plan §7 / §8; HANDOFF "The next task"). This is the final
review document for the formal-verification effort: the claim in the plan's
own words, a clause-by-clause cross-check against what actually stands in the
tree, the theorem inventory in English, and the residual risk. Nothing here
rounds up.

Verification state as of 2026-07-12 (post state-level + enumeration gates):
`bash formal/verify.sh` green — `lake build` + **0 sorries** + `zcli` + axiom
audit (every audited theorem depends only on `[propext, Classical.choice,
Quot.sound]`; the gate requires exactly one observed report per `#print axioms`
command) + **137** tests under `formal/conformance/` (0 skips — the conformance
step fails on any skipped test or zero passes; interpreter overridable via
`ZANZIBAR_PY`). The 137 = **120 differential-conformance tests** (98 answer-corner
[`test_conformance_spec` 51 + `test_conformance_random` 17 + `test_conformance_graph`
30] + 3 mode-dispatch [`test_cli_mode.py`] + 15 state-level [`test_conformance_state.py`]
+ 4 exhaustive small-scope enumeration [`test_conformance_enum.py`]) + **17
gate-tooling unit tests** (not Lean-vs-Python comparisons: 13 sorry-scanner
[`test_sorry_scan.py`] + 4 zcli-runner transient-retry [`test_runner_retry.py`]).

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
| set-engine **algorithm** proven to compute `sem` | ✅ **Full scope.** `setEngine_correct` (T1): for every well-formed, stratifiable schema and identifier-valid store, the Lean set-engine model's `check` equals `sem`. |
| graph-index **algorithm** proven to compute `sem` | ✅ **At the documented fragment, not beyond.** `graph_correct` (T2b): at every fully-drained state of the operational closure `ReachedBy` (logged rule-routed writes + the state-derived two-round cascade — the model of the synchronous v1 Python write path), graph `check` = `sem`, for stores/schemas satisfying `GraphAdmission` (the Python-admission mirror) **and** `W4Fragment` (honest carries: boolean-rooted derived defs, computed-only operands, ≤ 2 strata, bare declared wildcards, bare-star add-only stores, star-free TTU tuplesets, derived terminality), for queries with concrete objects and bare star subjects. See §3 for the gap list. |
| hence equivalent | ✅ `backend_equivalence` (T3), by transitivity through `sem`, same scope as T2b; plus `exclusion_effective` / `no_ghost_grant` (T6a/T6b) — the security corollaries with real exclusion content. |
| machine-checked, axiom-audited | ✅ 0 sorries; the Audit module `#print axioms` every key theorem; `verify.sh` hard-fails on any axiom beyond `propext`, `Classical.choice`, `Quot.sound`. |
| pinned by structural correspondence review | ✅ `CORRESPONDENCE.md` — the Lean-def ↔ Python-file:line map, with the known intentional divergences listed (add-only, fixed two rounds, fragment surplus, no leaf-family split). |
| pinned by differential conformance | ✅ **check-verdict level, five corners** (`verify.sh` step 5; 120 differential-conformance tests — the conformance step runs 133 under `formal/conformance/`, the other 13 being `test_sorry_scan.py` gate-tooling unit tests): Lean `sem` (zcli) × independent oracle × real `SetEngine` over 17 corpora + 25-seed randomized substores, **plus (Phase 6)** the Lean *operational graph model* (zcli mode `"graph"`, whose runtime output is covered by the theorem via `graphRun_reached` / `graphRun_check_eq_sem` — the driver is the chain's own constructors, by proof, not analogy) × the real Python `WildcardIndex`+`DeltaProcessor` × `sem`, over the 15 in-fragment corpora including two designed attack corpora (stale-edge cross-stratum re-settle; star churn over two strata). All three answer suites share one query grid (`formal/conformance/grid.py`) that unions schema-DECLARED relations type-aware into the target set — so derived/boolean roots are queried on every corpus (previously targets came only from stored tuples and derived-only boolean roots went unqueried — the boolean-root conformance evidence was vacuous exactly there) — and emits concrete-named userset-shaped subjects over a bounded pool (inside the proved graph scope: `hqs` constrains only star-NAMED subjects). zcli's mode dispatch is itself conformance-tested (`test_cli_mode.py`: unknown / non-string `"mode"` → rc 4, never silently answered as spec). The repository-wide validation matrix separately pins Python-graph × Python-set × oracle on every push. |
| … "including state-level equality" | ✅ **At a documented representation-neutral projection, per corpus.** `test_conformance_state.py` (15 in-fragment corpora): the Lean operational graph model's FINAL MATERIALIZED STATE (zcli mode `"graph-state"` — the same `graphRun` fold, same admission/drain gates, emitting canonical edges + residues) equals the real Python graph index's final SQL state (`EdgeV4`/`ResidueV1` decoded through `NodeV4` to symbolic keys). Compared: the DIRECT edge set over `(type, name, predicate, wildcard)` node keys, and per derived key the full residue triple (`stars` shapes, `neg`/`upos` subject sets). Six projections, each documented and justified in `formal/conformance/extractor.py` (P1 closure rows are a function of the direct set; P2 wildcard bridges — currently inert, bridged shapes compile empty on all 15 corpora; P3 edge multiplicity, sets both sides; P4 all-empty residue rows the model stores and Python deletes; P5 node sets, GC'd vs never-GC'd; P6 leaf-family closure-leaf copies, whose evaluation OUTPUT — residues + derived edges — is compared exactly). Attack-first: the gate's first run FOUND P6 (state divergence under full check-parity); a deliberately corrupted extraction fails with the symmetric-difference message. |
| … "exhaustive small-scope enumeration up to the documented bounds" | ✅ **At the documented (tiny) bounds.** `test_conformance_enum.py`: ALL stores of ≤ 3 tuples from the declared tuple space over a 2-names-per-type pool, for four representative fragment shapes — boolean_exclusion (93 stores), boolean_intersection (93), two_stratum_cascade (299), boolean_star_exclusion (42); 527 stores total, spec × oracle × set engine over the shared grid, store counts ASSERTED so the bounds cannot silently drift. Zero disagreements. Scope honesty: the graph backend is not part of the enumeration (runtime; it stays pinned by the curated-corpora graph + state gates), and the bounds are deliberately tiny — this earns "exhaustive up to the documented bounds", nothing more. |
| residual unverified surface | ✅ Acknowledged in full, and LARGER than §7's list — see §3. |

**The current honest claim is therefore §7's claim with one explicit
subtraction and two scope qualifiers:** the graph-side theorems hold at the
`W4Fragment` scope (not everything Python admits); state-level equality holds
under the six DOCUMENTED projections of `extractor.py` (a divergence inside a
projected class — e.g. leaf-family edge content — is pinned elsewhere, not
here); enumeration is exhaustive only up to its tiny documented bounds
(k ≤ 3 tuples, 2 names/type, four shapes). Never let a summary round any of
these back up, and never let "the algorithms are proven" become "the code is
formally verified."

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
  (`graphRun_check_eq_sem`).
* **Non-vacuity** (`FullScope.lean` `W4Witness`): the hypothesis bundles are
  machine-checked inhabited by a real compiled boolean schema — the final
  theorems are not vacuous. Honesty caveat: what is kernel-checked is
  inhabitation of the hypothesis BUNDLES (`GraphAdmission ∧ W4Fragment`).
  Joint inhabitation of a drained, non-trivially-REACHED state is demonstrated
  empirically — the zcli graph mode folds real corpora through the chain and
  refuses non-drained final states — together with the proved
  `cascade2_drains`; that joint witness is not itself a kernel-checked term.

Method note: six false theorem statements were killed by attack-first `#eval`
refutation before proving (additive fuel bound; abstract write-step closure;
T0a without store-declaredness; the naive W2 TTU fragment; the W3a single-edge
collapse without `NoRuleOutputs`; W3d-2 "round-1 keys are stratum-1"). The
ledger (`history/PROOF_STATUS.md`) records each. No adjudication event (spec vs oracle
vs backend disagreement) is open; none was silently reconciled.

## 3. Residual unverified surface (the full list)

Everything §7 lists, plus the fragment carries:

1. **Model-to-code fidelity** — the theorems are about the Lean models; the tie
   to Python is `CORRESPONDENCE.md` + empirical conformance. A Python behavior
   outside the corpora/grids could diverge without failing the gate.
2. **The Python COMPILER artifacts are trusted, not modeled.** `compile_ruleset`'s
   outputs — the taint computation, strata assignment, derived-predicate plans
   and fan-out tables, and leaf-family routing — have no Lean counterpart: the
   Lean model reads the RAW boolean defs and derives taint/strata/jobs itself
   (`isDerived`, `stratify`, the state-derived job enumerations). The pins are
   the compiled-RuleSet snapshot tests (`tests/snapshots/`) and the conformance
   corpora (which drive the real compiled artifacts through the Python write
   path); a compiler bug on a schema shape those pins don't exercise would not
   fail any Lean gate.
3. **Fragment scope** (each a documented gap, none hidden — `history/ROADMAP.md`
   "W4 — honest gaps"): > 2 derived strata; non-root booleans (Python taints through
   `union`/`computed` roots); `PDerivedTTU`/`PDerivedUserset` plan leaves;
   declared wildcard-userset restrictions (`[T#p:*]`-style) anywhere; stored
   object-wildcard (`w_all`) tuples; stored userset-star tuples; **removes**
   (the chain is add-only); star-subject queries with non-bare predicates;
   star-object queries on the graph side.
   *Empirical note (2026-07-12k): union-rooted-taint and object-wildcard
   corpora were probed anyway — zero check-level divergence observed; the
   exclusions are proof-scope, not known disagreements.*
4. **The state-gate projections** — state-level conformance IS implemented
   (§1), but a divergence strictly inside a projected class would not fail it:
   leaf-family edge content (P6 — pinned instead by the plans' evaluation
   output, check conformance, and the RuleSet snapshots), edge multiplicity
   (P3 — refcounts vs list repeats), bridge edges (P2 — inert on the current
   corpora), and node GC (P5). Each is documented with its justification in
   `formal/conformance/extractor.py`.
5. **The representation layers** — interner/bitmap (`setengine`), SQL rows /
   ref-counted closure storage (`index_v4`), sessions/transactions/concurrency
   (the `_lock_store` protocol), `rebuild()`/crash recovery.
6. **Non-stratifiable schemas** (rejected upstream; the model assumes
   stratifiability), `expand` / `lookup` / `list-objects` read surfaces.
7. **The toolchain trust base** — Lean 4 kernel + the pinned Mathlib, and the
   conformance harness's own encoder (`encode.py` reuses the independent
   oracle's parser precisely so one backend parser bug cannot corrupt both
   sides).

## 4. Where the next marginal assurance is

Items (a) state-level graph conformance and (b) exhaustive small-scope
enumeration are DONE (2026-07-12, §1 rows above). In descending
value-per-effort, what remains: (c) widening `W4Fragment` (union roots first —
the probe already suggests the model is faithful there); (d) remove legs (the
delta processor's removal branch is modeled by the diffing pass but never
exercised by the add-only chain); (e) widening the enumeration/state bounds
(graph backend in the enumeration; k = 4; a userset/TTU shape; state gate over
the enumerated stores).
