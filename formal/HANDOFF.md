# HANDOFF.md — START HERE (the formal-verification entry point)

**A fresh session reads THIS FILE FIRST, top to bottom (~250 lines), then goes straight
to work on "The next task" below.** Pull in other docs only on demand:

| doc | what it's for | when to read |
|---|---|---|
| `ARCHITECTURE.md` | the durable topical map (trust root, models, theorem table + scopes, pinning, residual surface) | for "how it all fits together" |
| `FINAL_REVIEW.md` | the exact, clause-checked claim (plan §7 + cross-check) | for the precise wording of what is/isn't proved |
| `SEMANTICS.md` | the spec / trust root (`sem`, models, theorem statements) | when touching spec-level defs |
| `CORRESPONDENCE.md` | the Lean-def ↔ Python-file:line map | when auditing the model↔code tie |
| `history/PROOF_STATUS.md` | append-only session ledger (newest first) | the TOP entry only, for fine detail on a resume point |
| `history/ROADMAP.md` | per-stage designs + historical plans | the section for a stage's provenance |
| `history/REVIEW.md` | historical one-shot session digest (2026-07-09→10) | never (history) |
| `formal/history/formal-verification-plan.md` | original strategy/phases/honesty clauses | rarely; §7 for claim wording |

**End goal:** a machine-checked proof that the set engine and graph index both compute
the stratified-Datalog¬ perfect model `sem` — hence are equivalent — with the Python
implementations pinned to the Lean models by the conformance harness. The honest claim
never rounds up to "the code is formally verified" (plan §7).

---

## House rules (non-negotiable, user-adjudicated)

1. **Honesty norm.** Never fake a proof, never postulate the thing being proven
   (no `check := sem` models, no invariant-as-postcondition). A documented `sorry`
   plus genuine infrastructure beats a fragile/unfaithful close. Never edit a
   golden/oracle/snapshot to make something pass.
2. **Attack first.** Before proving any NEW theorem statement, try to REFUTE it —
   concrete scenarios via `#eval` against the real `check`/`sem` (delete the scratch
   after recording the finding). This has killed six false statements so far
   (additive fuelBound, abstract WriteStep closure, T0a-sans-StoreDeclared, naive-W2
   TTU fragment, W3a single-edge collapse sans NoRuleOutputs, W3d-2 "round-1 keys are
   stratum-1"). A session that kills a false statement is a GOOD session; record the
   finding.
3. **Green gate.** Every increment must keep `bash formal/verify.sh` green: lake build
   + **0 sorries** + zcli + axiom audit (415 `#print axioms` reports, one per audited
   theorem, only `[propext, Classical.choice, Quot.sound]`) + 288 Python conformance
   tests, 0 skips
   (incl. the Phase-6 graph mode, the state-level gate over zcli mode `"graph-state"`,
   the exhaustive small-scope enumeration, the remove-path and generated-schema answer
   gates, the TTU userset-subject and self-referential-tuple spec corpora, and the
   zcli mode-rejection tests; the gate
   fails closed on any skip or zero passes). Add new key theorems to
   `lean/ZanzibarProofs/Audit.lean`.
4. **Rhythm.** Commit each green increment with a `formal: <stage> — <what>` message;
   push at session end. Before ending: update this file's "The next task" + add a
   `history/PROOF_STATUS.md` session entry (top) + tick the `history/ROADMAP.md` stage
   marker.
5. **Faithfulness.** Model hypotheses must be faithful to the Python (cite file:line
   or the spec §). New fragment conditions need a comment saying what Python mechanism
   they mirror. Where a spec and the code disagree on a name, the code wins.
6. **Subagents** don't parallelize proof-closing (compiler-in-loop, deep coupling);
   use them only for read-only exploration/design.

## Build & verify

```bash
export PATH="$HOME/.elan/bin:$PATH"                    # Lean v4.31.0, Mathlib pinned
cd formal/lean && lake build                            # library (incremental ~1 min)
lake build ZanzibarProofs.GraphIndex.ReconcileCorrect   # one module (~20 s)
bash formal/verify.sh                                   # THE gate (from repo root)
```

⚠ The one-shot `verify.sh` is now ~13–16 min and **blows the agent harness's
~10-min command cap** — agents run it PHASED: `verify.sh lean` → `conf-heavy` →
`conf-rest` (each cap-fitting, same anti-vacuous guards; three green phases ≡ a
green one-shot). Full recipe + suite-split + fuzz gate:
[`docs/gate-runbook.md`](../docs/gate-runbook.md).

Python side runs under the repo conda env
(`C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe`).

**Lean/Mathlib gotchas (hard-won):** unfold plain defs with `unfold f` / `simp only [f]`,
not `rw [f]`. `omega` treats `∑`-atoms as opaque — good for combining sum `have`s.
`Finset.Ico` ← `Mathlib.Order.Interval.Finset.Nat`; big-operator ring lemmas ←
`Mathlib.Algebra.BigOperators.Ring.Finset`; `ring` ← `Mathlib.Tactic.Ring`.
`NReaches` is head-oriented: back-append is `NReaches.tail`; back-REPLACE needs
last-edge surgery (`nreaches_last`, cf. `nreaches_relation_rewrite`).

## State of the world (2026-07-12m — the arc is COMPLETE; all sorry-free, axiom-clean, verify.sh green)

> **Update 2026-07-18 — OPTIONAL assurance-widening arc OPENED (4 targets scoped;
> `FINAL_REVIEW.md §4`).** All four remaining optional widenings were recon'd + (for #1)
> attack-first probed; the durable design + resume state for ALL of them is
> [`history/optional-widening-2026-07.md`](history/optional-widening-2026-07.md) —
> **read it to resume any target.** Progress so far: **#1 Leaf widening (Direct arm)**
> legs 1–3 LANDED (commits `98773d3` read-half `evalE_computedOrDirect`, `0dd8d7b`
> write-half admission `StoreValidRulesD` + the diffing retraction crux
> `reconcileKeyD_retracts_excluded`, `8a9bee1` base-equation WALL characterized —
> `graphRec_base_eq_d` needs a `NoStoreSubjectR` hyp, attack-pinned). Direct-arm leg 4 =
> the wall (3 named lemmas A/B/C, see the design file). **#3 state/enum widening
> increments (c) + (a) LANDED (2026-07-18b/c).** (c): userset (`wildcard_group_member`,
> 176 stores) + TTU (`ttu`, 93 stores) enum shapes added to `test_conformance_enum.py`
> (the self-referential `group_userset` attack-rejected as admission-cyclic for the set
> engine, recorded). (a): the REAL graph index (`WildcardIndex`+`DeltaProcessor`) now runs
> INSIDE the enum at answer level over all six in-`GRAPH_FRAGMENT` shapes — attack-first
> found NO graph≠sem divergence, NO `ValueError` (796 stores × graph grid). Full gate green
> incl. conf phases (290 conf, 0 skip). (b) k=4 LANDED (2026-07-18d): per-shape
> K (four shapes K=4, the two dominators `two_stratum_cascade`/`wildcard_group_member`
> capped at K=3 for the graph-leg-inflated cap). (d) state gate LANDED (2026-07-18e): new
> `test_conformance_enum_state.py` — stride-4 sampled (257/1021) Lean-model vs Python-graph
> STATE compare under `extractor.py` P1–P6, all six shapes, ZERO mismatches. **TARGET #3
> (state/enum widening) COMPLETE** (all of c/a/b/d green, no divergence). Conf now 296, 0
> skip. **#4 remove legs RECON+PROBE DONE (2026-07-18f):
> Route 1 GO with a KILL** — the design's "fold `removeEdgePair` (filter-all)" is a FALSE
> statement in-fragment (rc≥2 shared derivation drops a surviving edge); faithful op is
> `List.erase` (decrement one), and NO `GraphState` ripple (edges already a multiset =
> ref-count). Corrected legs R1–R4 in the design file (R3 occurrence-count invariant is the
> hard content). **Leg R1 LANDED (2026-07-18g)** — `GraphState.removeEdgeOne` (erase-one,
> mirror of `core.py`'s `-1` update) + membership/`count` lemmas + `structInv_removeEdgeOne`;
> additive, verify.sh lean 415/415, conf re-green. **THE NEXT TASK: #4 Leg R2** — land
> `removeLoggedRules`/`removeLoggedOne` (the deferred rewrite-closure fold + retraction-delta
> emission) + the `remove` constructor on `ReachedByW3d2E` + `RemoveAdmits` + thread hyps
> through `reachedByW3d2E_toC`. Then R3 (hard occurrence-count invariant), R4 (confluence).
> After #4: back to #1 Direct-arm leg 4+ / TTU half, #2 strata (>2). Not started: #1
> TTU/userset half, #2 strata, #4 legs R2–R4.

> **Update 2026-07-17 — rootB fragment widening LANDED (3 legs).** `W4Fragment`
> no longer restricts the derived-def ROOT operator: `RootBoolean` is DELETED and
> the shape condition is `ComputedOnly` alone, so union- and computed-rooted
> derived defs are inside the proved scope. Three commits: (1) `397f975` —
> `schemaRewrites` taint-filtered (`S.defs.filter (!isDerived …)`, the faithful
> mirror of `compile_ruleset`'s taint routing; a probe had found the UNFILTERED
> fanout leaked a stale userset-sourced edge `group:eng#member → approver` at a
> union-rooted derived R-node into the drained state — a real model-vs-Python
> state divergence); (2) `c3d3113` — `RootBoolean` deleted, `W4Fragment` widened;
> (3) this leg — the union-rooted non-vacuity witness `W4WitnessUnion`
> (`FullScope.lean`, audited) + the conformance widening: `taint_union_over_boolean`
> moved INTO `GRAPH_FRAGMENT`, two new pins added (`taint_union_userset_arm` — the
> stale-fanout STATE regression; `taint_computed_root_over_boolean` — computed
> roots). Gate green: audit 415, conformance 288/0-skip.

| theorem | file (`lean/ZanzibarProofs/`) | scope |
|---|---|---|
| T1 `setEngine_correct` | `SetEngine/Correct.lean` | full |
| T0a `sem_fuel_stable` (over `StoreDeclared`) | `Spec/WellDef.lean` | full |
| T0b `stratify_none_iff_cycle` / `stratify_topological` | `Spec/WellDef.lean` | full |
| T4 `pathCount_addEdge` / `_removeEdge` | `GraphIndex/Closure.lean` | full |
| T5 `cascade_converges_direct`, T2a `graph_reached_inv_direct` | `GraphIndex/Correct.lean` | fragment (W1; the contentful T5 is `runCascade_no_abort`/`cascade2_drains`) |
| T2b `graph_correct_direct` | `GraphIndex/DirectCorrect.lean` | star-free pure-direct |
| T2b `graph_correct_bareStar` | `GraphIndex/BareStarCorrect.lean` | + bare `[user:*]` grants |
| T2b `graph_correct_objStar` | `GraphIndex/ObjStarClosure.lean` | + object wildcards (out-bridges) |
| T2b `graph_correct_usStar` | `GraphIndex/UsStarClosure.lean` | + userset stars (in-bridges) |
| T2b `graph_correct_rules` | `GraphIndex/RulesComplete.lean` | untainted computed/ttu/union |
| T2b `graph_correct_w3a` | `GraphIndex/ReconcileComplete.lean` | + one `ComputedOnly` derived key (root operator UNRESTRICTED since the 2026-07-17 `RootBoolean` removal), bare-subject queries |
| T2b `graph_correct_w3b` | `GraphIndex/ReconcileUposComplete.lean` | + userset subjects via `upos` (bare-subject restriction LIFTED) |
| T2a `reachedByW3c_inv` / `reachedByW3c_master` | `GraphIndex/ReconcileStars.lean` | W3c write half: `stars`/`neg` model, ALL I6 clauses contentful, star-general (no `StarFreeStore`) |
| T2b `graph_correct_rulesBS` | `GraphIndex/RulesBareStar.lean` | W2 untainted correspondence over `BareStarStore`+`TtuStarFree`, star-BARE subjects incl. |
| `graphRec_base_eq_bs` / `checkFn_eq_sem_bs` | `RestrictBase.lean` / `ReconcileComplete.lean` | the STAR-RELAXED base equation + `checkFn ↔ sem` bridge (no `StarFreeStore`) |
| T2b `graph_correct_w3c` + `coveredFn_declared` (the linchpin) + `w3c_row_char` + batch completeness | `ReconcileStarsComplete.lean` | + star-carrying stores: bare `T:*` grants, `stars`/`neg`/`upos` reads, bare/star-BARE/userset subjects |
| T3/T6 `backend_equivalence*` / `exclusion_effective*` / `no_ghost_grant*` | `Equiv.lean` | per-fragment corollaries (incl. `_w3a`, `_w3b`, `_w3c`) |
| **T5** `runCascade_no_abort` / `cascade_drains` + `ReachedByW3d` | `GraphIndex/Cascade.lean` | W3d-1a: the scheduler in the model — logged writes, `affectedKeys`, the drain loop; reject branch provably dead at one stratum; `Quiescent` earned — RE-EARNED over the diffing pass (decision 7) |
| the DIFFING pass + per-key edge EXACTNESS | `GraphIndex/ReconcileDiff.lean` | W3d-1b groundwork: `reconcileStarsKeyD` (stale-edge retraction, `processor.py:359-367`), both-direction reach inertness, guard fold-invariance, `reconcileStarsKeyD_edge_char` (the re-settle as a theorem) |
| FAN-OUT COMPLETENESS + the untainted-core shadow + settledness transport | `GraphIndex/CascadeStable.lean` | W3d-1b core: `writeLeg_checkFn_stable` (unmapped keys' guards unchanged), `reachedByW3d_shadow`/`checkFn_eq_sem_w3d` (guard = `sem` at EVERY W3d state, incl. mid-batch), `writeLeg_sem_stable` (unmapped keys keep their MEANING), `SettledKey` + write-leg/untargeted-cascade transport |
| T2b **`graph_correct_w3d`** + the settledness invariant + targeted RE-settlement | `GraphIndex/CascadeSettle.lean` | W3d-1b CLOSED: `ReachedByW3dC` (coverage chain: per-job `W3dJobCoverage`, attack-confirmed edge-holder clause), `settledComplete_cascade_targeted`, `CompleteKey` + transports, `reachedByW3dC_settled` (dirty-or-settled at EVERY state), the W3d reach collapse, `check = sem` at every fully-drained (`cascadeKeys = []`) state; T3/T6 `*_w3d` |
| T2a **`reachedByW3dC_inv`** — the FULL 8-clause `Inv` (+ `reachedByW3d_structInv` / `reachedByW3d_residueHygienic` / `reachedByW3d_residueDeclared` / `reachedByW3dC_edgeHygienic`) | `GraphIndex/CascadeInv.lean` | W3d-1c piece A CLOSED: `Inv` at EVERY coverage-chain state (dirty keys, mid-drain included). Structural half + edge-free I6: NO fragment hyps. Edge-referencing I6 (`negEdgeFree`/`uposEdgeFree`): attack-REFUTED over the plain chain (stale non-candidate edge — the coverage clauses are load-bearing for the invariant itself, not just the read theorem); proved over `ReachedByW3dC` via row-key declaredness + the reach collapse + the `SettledKey` verdict clash at targeted keys |
| **`w3dJobCoverage_enumJob`** (+ the collapse `checkFn_eq_coveredFn_of_no_extra`, `leafConcretes`/`edgeHolders`, per-clause discharges, `w3d_leg_context`) | `GraphIndex/CascadeEnum.lean` | W3d-1c piece B CORE: **`W3dJobCoverage` is now a THEOREM** of a state-derived enumeration (was a chain-side hypothesis). Spine: a star-free subject's operand leaf reads decompose pointwise as star-read ∨ two concrete probes (`probeNonDerived_concrete_decomp`); a subject hitting neither probe reads exactly as its shape-star (`evalE` congruence, exclusion-safe). `w3d_leg_context` rebuilds the read bridge + coverage-declaredness at any W3d state via the shadow |
| **`graph_correct_w3dE`** / **`reachedByW3dE_inv`** (+ `ReachedByW3dE`, `reachedByW3dE_toC`, `enumJobs`/`_valid`/`_cover`/`_scope`/`_covg`, `w3cJobValid_enumJob`, `reachedByW3d_Rnode_source_name_ne_star`) | `GraphIndex/CascadeEnum.lean` | **W3d-1c piece B TAIL — W3d-1c CLOSED.** The enumerated-cascade restatement: `ReachedByW3dE` is the fully-operational scheduler chain (cascade legs run the state-derived `enumJobs`, NO `W3dJobCoverage`/`hcover`/`hscope`/`hjv` in the constructor); `reachedByW3dE_toC` projects it to `ReachedByW3dC` (the four hyps discharged by `enumJobs_*`, store hyps weakened along write prefixes). `check = sem` (fully-drained) and the full 8-clause `Inv` (every state) now hold UNCONDITIONALLY over the operational chain |
| the ROUTED leaf dispatch + conservativity + the TWO-ROUND scheduler | `GraphIndex/CascadeStrata.lean` | W3d-2 OPENING: `graphRecR`/`checkFnR`/`coveredFnR` (every operand leaf reads the graph's own `check` — untainted ⇒ `probeNonDerived`, derived ⇒ `probeDerived`; `processor.py:43-70, 182-188`), `checkFnR_eq_checkFn` (conservativity: on untainted-operand defs the routed read IS the W3d read), `checkFnR_evalEq` (the routed read consults exactly the `EvalEq` core — residue+schema now included), the routed diffing pass + `reconcileJobsLR_eq` (W3d-1 is the single-stratum image of the routed scheduler), `runCascade2` (rounds = 2, per-round frontier cursor, leftover reject), `ReachedByW3d2` (C-style two-batch closure), `reachedByW3d2_schema`. Attack-first: fully-drained `check = sem` SURVIVED all cross-stratum vectors; mid-drain staleness real; within-round order not load-bearing |
| **T5 at TWO STRATA** — `runCascade2_no_abort` / `cascade2_drains` + the W3d-2 structural layer | `GraphIndex/CascadeStrata.lean` | W3d-2 items 1–2 (2026-07-12d): routed-batch outbox/edge soundness (`reconcileJobsLR_outbox_sound`/`_edge_sound`), R-node terminality over the two-round closure (+ the round-STACKABLE batch transport), cursor arithmetic (`outbox_le_frontierMax` — a round's read is exhaustive). The reject branch provably dead under **`hLU2`** (two-stratum condition, dependency-wise; strictly wider than `hLU`, `hLU2_of_hLU`); attack-confirmed load-bearing (3-stratum schema ⇒ `hLU2` FALSE and the reject FIRES) |
| **per-stratum operand-read INERTNESS** — `check_reconcileStarsKeyDR_other` / `checkFnR_reconcileStarsKeyDR_other` | `GraphIndex/CascadeStrata.lean` | W3d-2 item 3a (2026-07-12d): a routed pass is read-inert at every OTHER key WHATEVER its stratum (untainted probe via `graphRec_reconcileStarsKeyDR_inert`, derived read via `probeDerived_reconcileStarsKeyDR_other` — node inequality from key inequality; guard form via `evalE_computedOnly`), on routed mirrors of the W3d-1b reach-inertness/closure/residue-other layer. The base fact for the stratum-staged settledness transport |
| **the W3d2 SHADOW + the stratum-staged READ BRIDGE + settledness transports + `ReachedByW3d2C`** — `reachedByW3d2_shadow`, `probeDerived_eq_sem_settled`, **`checkFnR_eq_sem_settled`**, `round2_key_reads_derived`, **`writeLeg_sem_stable2`**, `reconcileJobsLR_emits`/`round1_emission_dirties`, `reconcileJobsLR_reach_collapse` | `GraphIndex/CascadeStrataSettle.lean` | W3d-2 item 3b (2026-07-12e): W3d2 chain structural mirrors + the shadow at every state (mid-round prefixes incl.); the settled-key derived read (factored from `graph_correct_w3d`); the stratum-staged bridge (routed guard = `sem` at settled+complete derived operand keys — attack-confirmed load-bearing); per-round settled/complete transports + the stratum fence (round 2 never targets stratum-1 keys); write-leg `sem` stability at BOTH strata (stratum-2 needs key AND operand keys unmapped — the attack-REFUTED "dirty ∨ settled" gains the third disjunct "operand-dirty"); every job EMITS (round-1 operand passes provably re-dirty stratum-2 readers); the two-round coverage chain (round-2 coverage rel. the MID state) |
| **`graph_correct_w3d2`** + **`reachedByW3d2C_settled`** (the THREE-disjunct invariant) + the ROUTED edge char + the two-round re-settlement — `reconcileStarsKeyDR_edge_char` (via `computedRefs_ne_self`), `reconcileJobsLR_key_edge_sem`, `settledComplete_jobsLR_targeted`/`settledComplete_cascade2_targeted`, `sem_nil_derived_false2`, `graphRec_star_declared` | `GraphIndex/CascadeStrataResettle.lean` + `Equiv.lean` | **W3d-2 ENDGAME (2026-07-12f)**: `check = sem` at every fully-drained `ReachedByW3d2C` state — TWO strata (`hLU2`), W3d-1 subject/query scope; the settled ∨ dirty ∨ operand-dirty invariant at EVERY state; no-ghost-star-coverage at ANY stratum via the drained-state routed bridge; T3/T6 `*_w3d2` |
| the DERIVED-leaf decomposition + routed reads-as-star + `enumJob2` coverage — `probeDerived_concrete_off_named`, `residueNamed`, `checkFnR_eq_star_of_not_enum`, `enumJob2`/`w3dJobCoverage_enumJob2`, `checkFnR_star_declared`/`w3d2_leg_context`, `w3dJobCoverage_enumJob2_state` | `GraphIndex/CascadeStrataEnum.lean` | **W3d-2 E-chain tail CORE (2026-07-12g)**: the two-round chain's audit enumeration + its `W3dJobCoverage`. Finding (c)'s residue-named candidates (`neg`/`upos`, edge-free/I6) folded into `enumJob2`; routed reads-as-star (no reach-collapse needed); coverage from the routed leg context (`checkFnR_eq_sem_settled` + `checkFnR_star_declared`) at any `ReachedByW3d2` state given operand settledness (`hsettledOps`) |
| **`graph_correct_w3d2E`** / **`ReachedByW3d2E`** / **`reachedByW3d2E_toC`** + the CONDITIONAL coverage chain (`W3dJobOpsSettled`, `covg_of_opsSettled`) + `enumJobs2R1`/`enumJobs2R2`/`enumJobs2At_*` + `ResidueSubjectsStarFree`/`reachedByW3d2_residueStarFree` + `w3cJobValid_enumJob2` + R-node source star-freeness (chain+batch) | `GraphIndex/CascadeStrataAssemble.lean` (+ `CascadeStrataSettle/Resettle` hyp changes) | **W3d-2 CLOSED (2026-07-12h).** Attack-REFUTED (kill #6): "round-1 keys are stratum-1" is FALSE — a write to a DIRECT untainted leaf of a stratum-2 def dirties it at the watermark, where the leg-start enumeration provably misses a fresh grant living only in the dirty operand's future residue. So `ReachedByW3d2C`'s per-round coverage is CONDITIONAL on the job's operand baseline (`W3dJobOpsSettled` — exactly what the 12f re-settlement consumes), and the E-chain discharges it from state: round 1 hands the baseline premise to `w3dJobCoverage_enumJob2_state`, round 2 runs the routed leg context at the transported MID state. `check = sem` at every fully-drained state of the FULLY-OPERATIONAL two-round scheduler chain |

| **W4** `ReachedBy`/`Drained` + **`GraphAdmission`** (Python-admission mirror, per-field citations, incl. `objWild`) / **`W4Fragment`** (the honest carries) + **`w4_within_scope`** (bundles ⇒ the spec's decision-15 `GraphAccepts`) + the FINAL unsuffixed **`graph_correct` / `backend_equivalence` / `exclusion_effective` / `no_ghost_grant`** (W1 versions renamed `*_direct`) + W2-subsumption lemmas (`drained_of_untainted`/`w4Fragment_of_untainted`) + **non-vacuity witnesses** (`W4Witness.accepts`/`fragment`/`within_scope` — both bundles inhabited by a real compiled boolean schema) | `FullScope.lean` | the deleted-as-false T2b/T3/T6 obligations DISCHARGED at the achieved scope; hypotheses split by provenance; honest-gaps list in ROADMAP W4 |
| **W4 T2a groundwork** — `StructInv` / edge-free I6 (`ResidueHygienic`) / `ResidueDeclared` at every `ReachedByW3d2`/`W3d2C`/`W3d2E` state (E-chain versions HYPOTHESIS-FREE, `enumJobs2At_keyFacts`); **pass-local I6** `reconcileStarsKeyDR_row_edge_consistent` (+ `enumJob2_negCands_subset`) — the routed pass's row is edge-consistent with its OWN audit, no settled verdicts, so it holds at re-dirtied stale keys (12h attack shape) where the W3d-1 coverage route can't go | `GraphIndex/CascadeStrataInv.lean` | the fragment-free 3 of 8 `Inv` clauses over the OPERATIONAL chain + the core of the edge-referencing 2 |
| **W4 T2a ASSEMBLY — `reachedByW3d2E_inv` (full 8-clause `Inv`, every state) + the final `graph_reached_inv`** (`EdgeHyg1` direct-edge form; `edgeHyg1_applyLoggedR`/`_reconcileJobsLR`/`_runCascade2` — pass-local at the job key, other-key fixedness elsewhere, batch of ENUMERATED jobs; `reachedByW3d2E_edgeHyg1`→`_edgeHygienic` via the reach collapse; write legs via `writeLeg_derived_inedges_eq`) | `GraphIndex/CascadeStrataEdge.lean` + `FullScope.lean` | **W4 CLOSED.** T2a over `ReachedBy` with the provenance-split bundles; W1 direct version renamed `graph_reached_inv_direct` |

| **Phase 6 driver honesty** — `foldAdmitsB_iff` / **`graphRun_reached`** / `graphRun_store` / `drainedB_iff` / **`graphRun_check_eq_sem`** | `GraphIndex/Exec.lean` | the zcli graph mode IS the chain: the driver folds the `ReachedBy` constructors, its runtime gates decide the theorem's side conditions, and under the W4 bundles every printed verdict is `sem` |

**Staged T2 widening: W1 ✅ → W2 ✅ → W3a ✅ → W3b ✅ → W3c ✅ → W3d-1a ✅ → W3d-1b ✅ → W3d-1c ✅ → W3d-2 ✅ → W4 ✅ (CLOSED 2026-07-12j — full T2a/T2b/T3/T6 over `ReachedBy := ReachedByW3d2E`). Phase 6 items 1–3 ✅ (CLOSED 2026-07-12k — graph-state conformance mode + `CORRESPONDENCE.md` + `FINAL_REVIEW.md`).**

**W3c is CLOSED (2026-07-11d).** Full detail: the 2026-07-11* `history/PROOF_STATUS.md`
entries and the `history/ROADMAP.md` W3c paragraphs. The pieces a W3d session will reuse:
- **Write model** (`ReconcileStars.lean`): `wildcardShapes` / `coveredFn` (star-subject
  `checkFn`) / `reconcileResidueKey` (wholesale stars+neg+upos recompute) / `reconcileKeyC`
  (covered-guarded edge fold) / `reconcileStarsKey` (residue-THEN-edges, the faithful atomic
  unit). Three structural devices: the **covered-filter collapse** (`reconcileKeyC_eq_filter` —
  the W3c edge fold IS a W3a `reconcileKey` on filtered candidates), the **shadow projection**
  (`reachedByW3c_shadow` — every W3c state has a W3a-admitted shadow with identical core), and
  **star-general operand-read inertness** (`graphRec_reconcileKey_inert`, no `StarFreeStore`).
  `reachedByW3c_master`: canonical base σ0 per chain — canonical `stars` rows + guard canonicity.
  T2a `reachedByW3c_inv` with ALL FOUR I6 clauses contentful.
- **Read half** (`ReconcileStarsComplete.lean`): `checkFn_eq_sem_w3c` (bridge on any W3c state);
  **the LINCHPIN `coveredFn_declared`** (no ghost star coverage: a `sem`-covered shape is
  DECLARED — first edge out of the `wAny` node is a materialised closure tuple whose star seed
  matched a wildcard-flagged restriction); `w3c_row_char` (persisted rows read at `sem` level);
  batch completeness for the WHOLESALE recompute (`reconcileJobsC_row_isSome`,
  `_neg_complete`/`_upos_complete` with the **∀-targeting-jobs enumeration form** — attack-
  confirmed necessary: a later same-key pass with an incomplete `negCands` drops the exclusion);
  `w3cComplete_derived_edge`; **`graph_correct_w3c`** (star ⇒ `stars`, bare ⇒ edge ∨ `stars`∖`neg`,
  userset ⇒ `upos` exactly — `hWSbare` kills userset coverage). Fragment hyps: `BareStarStore` +
  `TtuStarFree` + `hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE` (decision-15) + the W3a/W3b
  carries (`hterm`/`hCO`/`hLU`/`hRootB`); query scope `hqs : name = STAR → predicate = BARE`,
  concrete object. T3/T6 `*_w3c` incl. `exclusion_effective_w3c` (a concrete subject excluded
  from UNDER a `T:*` grant — the space rule's `neg` actually excludes).

---

## Status — the arc is COMPLETE; what remains is optional

**The formal-verification arc is finished.** T1 + T2a/T2b + T3/T6 over `ReachedBy`,
the graph conformance mode (zcli `"graph"` + `test_conformance_graph.py`),
**state-level graph conformance** (zcli mode `"graph-state"` emitting the model's
canonical final state; `formal/conformance/extractor.py` reading the Python
`EdgeV4`/`ResidueV1` rows back to the same form under six DOCUMENTED projections
P1–P6; `test_conformance_state.py`, 15 corpora — its first run FOUND the P6
leaf-family divergence, recorded in `CORRESPONDENCE.md` §7), **exhaustive small-scope
enumeration** (`test_conformance_enum.py`: ALL stores ≤ 3 tuples, 2 names/type, four
shapes, 527 stores, spec × oracle × set engine, counts asserted), the **remove-path
answer gate** (`test_conformance_remove.py`: seeded add/remove/re-add sequences ×
17 corpora × 5 seeds, driven `SetEngine` == `sem` × oracle on the final store, driven
== `rebuild()` at grid + state-fingerprint level — and, added 2026-07-13, the SAME
sequences/seeds driven through the real GRAPH index (`WildcardIndex`+`DeltaProcessor`,
I5 leaf-routing): driven graph `check` == oracle, driven graph SQL state == a fresh
add-only build's, full-churn drains to a fresh-EMPTY graph with I12 non-mutation on a
rejected repeat remove; so BOTH Python remove paths are now pinned, only the Lean
remove legs stay open), the **generated-schema answer gate**
(`test_conformance_generated.py`: 40 seeded generated schemas outside the curated
corpora, spec == oracle == set engine — closes the disjoint-pools risk at answer
level), `CORRESPONDENCE.md`, and `FINAL_REVIEW.md` are all landed and gated.
verify.sh: 288 conformance tests, 0 skips. **No open blocker for the claim as written in `FINAL_REVIEW.md`.** The topical
map is `ARCHITECTURE.md`; the exact claim is `FINAL_REVIEW.md`; provenance is
`history/`. The one known check-level graph-vs-set divergence (derived-TTU
userset subjects — outside `W4Fragment` and the conformance grids) was FIXED
2026-07-13 Python-side; its strict xfails in `tests/test_lookup_oracle.py` are
now plain regression pins, Lean untouched — see `FINAL_REVIEW.md` §3's
resolved note and `docs/spec-deviations.md` 2026-07-13.

**Done 2026-07-13 (spec-side, no Lean changes) — the X4 adjudication is now
anchored to `sem`.** The 2026-07-13 X4 fix followed the ORACLE where the boolean
spec is SILENT on userset subjects through a TTU's stored tupleset parents; the
formal trust root (`sem`) had never been consulted on those exact shapes (no
corpus exercised them). Three spec-side corpora now do — `TTU_USERSET_SCHEMAS`
in `corpus.py` (from-chain userset through an untainted TTU; the cross-object
membership lift; from-chain userset through a TTU over a DERIVED boolean target),
consumed ONLY by `test_conformance_spec.py`'s full-scope spec/oracle/set-engine
comparisons (T1 places no fragment restriction). Result: `sem` == oracle == set
engine on every grid query (the from-chain userset answers True on all three,
matching the oracle the graph was fixed toward) — the adjudication is anchored,
not merely asserted. Kept OUT of `SCHEMAS`/`GRAPH_FRAGMENT` on purpose: the
shapes are outside `W4Fragment`, so the graph/state/remove gates must not carry
them. Conformance 248 → 257 (+9 = 3 corpora × 3 comparisons).

What remains is entirely OPTIONAL assurance-widening, ranked in `FINAL_REVIEW.md` §4:

1. **Fragment widening (leaves + strata)** — the derived-def ROOT gap is ✅ **DONE
   (2026-07-17)**: `RootBoolean` deleted, union-/computed-rooted derived defs in
   scope, `taint_union_over_boolean` + two new pins now in `GRAPH_FRAGMENT`. What
   REMAINS is the LEAF/strata fragment — `computedOnly` still bans `Direct`/TTU
   arms in derived defs (`PDerivedTTU`/`PDerivedUserset` plan leaves), and
   `twoStrata` still caps at ≤ 2 derived strata (attack-confirmed load-bearing:
   a 3-stratum schema fires the round-2 reject). Widening either is the open
   fragment work; both are genuine proof effort (not just a probe-faithful gap
   like roots was). **IN PROGRESS 2026-07-18:** the LEAF Direct-arm sub-legs 1–3
   landed (`98773d3`/`0dd8d7b`/`8a9bee1`); leg 4 (the base-equation wall) + leg 5
   + the TTU/userset half + strata all scoped in
   [`history/optional-widening-2026-07.md`](history/optional-widening-2026-07.md).
2. **Remove legs** (the diffing pass models retraction but the Lean chain is
   add-only; BOTH Python remove paths are now pinned at answer level by
   `test_conformance_remove.py` — the set engine at rebuild-fingerprint level, the
   graph index by fresh-build state convergence + full drain — so only the Lean
   legs remain the open part). **[my recommendation #3, second half — biggest
   lift, highest ceiling: makes the Lean model a post-remove reference.]**
3. **Widening the state/enumeration bounds** — graph backend inside the
   enumeration, k = 4, a userset/TTU shape, state gate over enumerated stores.
   (The current bounds, their runtime rationale, and why the graph side was
   left out are documented in `test_conformance_enum.py`'s module docstring —
   read it first; it is half the plan.) **[my recommendation #3, first half —
   Python-only; the graph-in-enumeration half is the meaty part.]**
4. **Model the read surfaces in Lean** — LOWEST priority, deferred to the
   eventual full-spec effort. `lookup` / `lookup_reverse` / `expand`
   (list-objects / list-users) have no Lean model yet. Cheap to specify (a
   comprehension over `sem`) but the completeness proof drags in the
   interner/candidate-universe layer T1 abstracts away, and the surface is
   empirically subtle (X1/X3/X4 all lived here). Pinned empirically for now by
   `tests/test_lookup_oracle.py` + the hypothesis campaign (lookup coverage
   added 2026-07-13). NOT out of scope — just not done; see `FINAL_REVIEW.md`
   §4(g).
4. ~~**Fixing the derived-TTU userset-subject divergence** pinned in
   `tests/test_lookup_oracle.py`, then flipping its strict xfails.~~ ✅ **DONE
   (2026-07-13, Python-side — Lean untouched, `W4Fragment` unchanged;
   processor from-chain rule + `upos` lift, set-engine write-time interning;
   gate now 16 passed / 0 xfail; see the `history/PROOF_STATUS.md` top entry).**

Repo-side (outside the formal effort, smaller, Python-only):

- ~~**Pure-union latent gap**~~ — **DONE 2026-07-13.** Fixture written
  (`tests/test_pure_union_ttu.py`); **no real divergence** — the shape is
  unreachable on the graph. `_validate_ttu_tuplesets` rejects any untainted
  tupleset with a computed arm at compile time, so a directs-only tupleset only
  ever gets raw stored edges (a rewrite rule lands edges only on the relation it
  defines). Set engine + oracle accept the schema and agree (stored-only, no
  over-grant). Closed as benign; resolution appended to `docs/spec-deviations.md`
  P5 #3.
- **Symmetric subject-keyed residues** — the engineering hook that would lift
  the two remaining scope rejections (object wildcards on derived relations;
  wildcard usersets over derived relations); `README.md` TODO list.
- README editorial TODOs (unfinished narrative sections) — Avery's voice,
  surgical edits only.

## After W3d (the remaining road)
- **W4 — full-scope restatement. ✅ CLOSED (2026-07-12j).** `ReachedBy` /
  `Drained`, the `GraphAdmission`/`W4Fragment` provenance split, `w4_within_scope`,
  the final unsuffixed T2b/T3/T6 + **T2a `graph_reached_inv`** (`FullScope.lean`),
  W2-subsumption lemmas, non-vacuity witnesses, the T2a fragment-free layers +
  pass-local I6 (`CascadeStrataInv.lean`), and the edge-hygiene ASSEMBLY
  (`CascadeStrataEdge.lean`: `EdgeHyg1` → `reachedByW3d2E_inv`).
- **Phase 6 — hardening. ✅ items 1–3 CLOSED (2026-07-12k).** (a) the graph-state
  conformance mode (`Exec.lean` driver + honesty theorems, zcli `"graph"`,
  `test_conformance_graph.py` hard gate, attack corpora + findings);
  (b) `CORRESPONDENCE.md`; (c) `FINAL_REVIEW.md` (plan §7 verbatim + cross-check).
  **State-level conformance + exhaustive small-scope enumeration ✅ CLOSED
  (2026-07-12m)** — the two formerly-unearned §7 clauses. Remaining extras
  (optional, FINAL_REVIEW §4): fragment widening (the ROOT-operator gap is DONE
  2026-07-17; the LEAF/strata gaps remain), remove legs, wider bounds.

Historical detail for every closed stage: `history/PROOF_STATUS.md` (ledger, newest
first) and `history/ROADMAP.md` (designs + post-mortems); the topical synthesis is
`ARCHITECTURE.md`.
