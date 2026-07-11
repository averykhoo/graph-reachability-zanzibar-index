# HANDOFF.md — START HERE (the formal-verification entry point)

**A fresh session reads THIS FILE FIRST, top to bottom (~250 lines), then goes straight
to work on "The next task" below.** Pull in other docs only on demand:

| doc | what it's for | when to read |
|---|---|---|
| `PROOF_STATUS.md` | append-only session ledger (newest first) | the TOP entry only, for fine detail on the resume point |
| `ROADMAP.md` | per-stage designs + historical plans | the section for the stage you're working |
| `SEMANTICS.md` | the Phase-0 spec (`sem`, models, theorem statements) | when touching spec-level defs |
| `docs/formal-verification-plan.md` | original strategy/phases/honesty clauses | rarely; §7 for claim wording |
| `REVIEW.md` | historical one-shot session digest (2026-07-09→10) | never (history) |

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
   + **0 sorries** + zcli + axiom audit (only `[propext, Classical.choice, Quot.sound]`)
   + 60 Python conformance tests. Add new key theorems to `lean/ZanzibarProofs/Audit.lean`.
4. **Rhythm.** Commit each green increment with a `formal: <stage> — <what>` message;
   push at session end. Before ending: update this file's "The next task" + add a
   PROOF_STATUS.md session entry (top) + tick the ROADMAP stage marker.
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
bash formal/verify.sh                                   # THE gate (from repo root; ~5 min)
```

Python side runs under the repo conda env
(`C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe`).

**Lean/Mathlib gotchas (hard-won):** unfold plain defs with `unfold f` / `simp only [f]`,
not `rw [f]`. `omega` treats `∑`-atoms as opaque — good for combining sum `have`s.
`Finset.Ico` ← `Mathlib.Order.Interval.Finset.Nat`; big-operator ring lemmas ←
`Mathlib.Algebra.BigOperators.Ring.Finset`; `ring` ← `Mathlib.Tactic.Ring`.
`NReaches` is head-oriented: back-append is `NReaches.tail`; back-REPLACE needs
last-edge surgery (`nreaches_last`, cf. `nreaches_relation_rewrite`).

## State of the world (2026-07-12i — all sorry-free, axiom-clean, verify.sh green)

| theorem | file (`lean/ZanzibarProofs/`) | scope |
|---|---|---|
| T1 `setEngine_correct` | `SetEngine/Correct.lean` | full |
| T0a `sem_fuel_stable` (over `StoreDeclared`) | `Spec/WellDef.lean` | full |
| T0b `stratify_none_iff_cycle` / `stratify_topological` | `Spec/WellDef.lean` | full |
| T4 `pathCount_addEdge` / `_removeEdge` | `GraphIndex/Closure.lean` | full |
| T5 `cascade_converges`, T2a `graph_reached_inv` | `GraphIndex/Correct.lean` | fragment |
| T2b `graph_correct_direct` | `GraphIndex/DirectCorrect.lean` | star-free pure-direct |
| T2b `graph_correct_bareStar` | `GraphIndex/BareStarCorrect.lean` | + bare `[user:*]` grants |
| T2b `graph_correct_objStar` | `GraphIndex/ObjStarClosure.lean` | + object wildcards (out-bridges) |
| T2b `graph_correct_usStar` | `GraphIndex/UsStarClosure.lean` | + userset stars (in-bridges) |
| T2b `graph_correct_rules` | `GraphIndex/RulesComplete.lean` | untainted computed/ttu/union |
| T2b `graph_correct_w3a` | `GraphIndex/ReconcileComplete.lean` | + one `RootBoolean` derived key, bare-subject queries |
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
| **W4 T2a groundwork** — `StructInv` / edge-free I6 (`ResidueHygienic`) / `ResidueDeclared` at every `ReachedByW3d2`/`W3d2C`/`W3d2E` state (E-chain versions HYPOTHESIS-FREE, `enumJobs2At_keyFacts`); **pass-local I6** `reconcileStarsKeyDR_row_edge_consistent` (+ `enumJob2_negCands_subset`) — the routed pass's row is edge-consistent with its OWN audit, no settled verdicts, so it holds at re-dirtied stale keys (12h attack shape) where the W3d-1 coverage route can't go | `GraphIndex/CascadeStrataInv.lean` | the fragment-free 3 of 8 `Inv` clauses over the OPERATIONAL chain + the core of the edge-referencing 2; assembly = the next task |

**Staged T2 widening: W1 ✅ → W2 ✅ → W3a ✅ → W3b ✅ → W3c ✅ → W3d-1a ✅ → W3d-1b ✅ → W3d-1c ✅ → W3d-2 ✅ → W4 IN PROGRESS (opened 2026-07-12i — design pass + `FullScope.lean` restatements + T2a groundwork + pass-local I6; REMAINING: the T2a assembly below, then Phase 6).**

**W3c is CLOSED (2026-07-11d).** Full detail: the 2026-07-11* PROOF_STATUS entries and the
ROADMAP W3c paragraphs. The pieces a W3d session will actually reuse:
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

## The next task — W4 T2a assembly: edge hygiene over `ReachedBy`, then `reachedByW3d2E_inv` + the `graph_reached_inv` restatement

**W4 is OPEN and mostly landed (2026-07-12i — READ THE TOP PROOF_STATUS ENTRY).**
`FullScope.lean` has the final T2b/T3/T6 + bundles + witnesses;
`CascadeStrataInv.lean` has `StructInv`/`ResidueHygienic`/`ResidueDeclared` over
all three two-round chains plus the pass-local I6 core. What remains for W4 is
T2a over the operational chain:

1. **`EdgeHyg1` batch induction (the assembly of the pass-local core).** Define
   the single-EDGE hygiene predicate (`∀ k r res` row, no `(subjNode n, k)` edge
   for `n ∈ neg ∪ upos`) and prove it preserved by `reconcileJobsLR` batches of
   ENUMERATED jobs, by induction carrying the prefix-state context:
   - at the job's own key: `reconcileStarsKeyDR_row_edge_consistent`
     (`CascadeStrataInv.lean`) — its `hnc` from `enumJob2_negCands_subset`, `hup`
     from `W3cJobValid` field 5, `hσS`/`hcl` from `StructInv` (preserved
     stepwise, `structInv_applyLoggedR`), `hRns` from the R-node terminality
     batch transports (12d layer, `CascadeStrata.lean`), `hsb` from
     `reconcileJobsLR_source_bare` stepwise, `hrne` via `computedRefs_ne_self`
     (`CascadeStrataResettle.lean:31`, needs `hLU2`), key facts from
     `enumJobs2At_keyFacts`;
   - at every other key: `applyLoggedR_other_key_fixed`
     (`CascadeStrataSettle.lean:764` — row AND in-edges verbatim; the other key's
     `on ≠ STAR` from `ResidueDeclared`).
   Then `runCascade2` (two batches + watermark, reject = id) and the chain:
   write legs are residue-inert with derived in-edges fixed
   (`writeLeg_derived_inedges_eq`, needs `hRootB`/`hNK`/`hSV` + row declaredness).
2. **`reachedByW3d2E_edgeHygienic`**: convert `EdgeHyg1` to the `Inv` clauses'
   `¬NReaches` form via the reach collapse at chain states
   (`reachedByW3d2_reach_collapse_root`, `CascadeStrataSettle.lean:256`).
3. **`reachedByW3d2E_inv`** (the full 8-clause `Inv` at every operational state,
   assembling 1–2 with the three fragment-free layers) and the **final
   `graph_reached_inv`** restatement in `FullScope.lean` (T2a over `ReachedBy`,
   hypothesis bundles as in `graph_correct`); Audit entries; tick ROADMAP.
4. Then **Phase 6** (below).

DESIGN NOTE (why NOT the W3d-1 route): `reachedByW3dC_edgeHygienic` went through
settled verdicts, but W3d2C coverage is CONDITIONAL (12h) — at a re-dirtied
round-1 stratum-2 key there is no `SettledKey`. The pass-local core needs no
settledness at all: the last targeting pass's row and edges are mutually
consistent against ITS OWN pass-start guard, stale or not. Attack duty for the
new statements is light — they consume the proved `reconcileStarsKeyDR_edge_char`
and the batch-fixedness layer; the one genuinely new claim (`EdgeHyg1` survives a
batch) should still get a quick refutation pass at write-leg/star-key corners
(row declaredness gives `on ≠ STAR`; write legs can add edges into UNTAINTED
nodes only — check the derived-in-edge fixedness covers wAny sources).

**After W4 → Phase 6** (graph-model conformance extension — drive the Lean
`writeDirect`/`check` model against the PYTHON graph index over the fragment corpora;
CORRESPONDENCE.md; final review doc using plan §7 wording verbatim).

---

## After W3d (the remaining road)
- **W4 — full-scope restatement. IN PROGRESS (2026-07-12i).** DONE: `ReachedBy` /
  `Drained`, the `GraphAdmission`/`W4Fragment` provenance split, `w4_within_scope`,
  the final unsuffixed T2b/T3/T6 (`FullScope.lean`), W2-subsumption lemmas,
  non-vacuity witnesses, and the T2a fragment-free layers + pass-local I6
  (`CascadeStrataInv.lean`). REMAINING: the T2a assembly ("The next task" above) —
  `EdgeHyg1` batch induction → `reachedByW3d2E_edgeHygienic` →
  `reachedByW3d2E_inv` → the final `graph_reached_inv`.
- **Phase 6 — hardening.** (a) graph-model conformance extension: drive the Lean
  `writeDirect`/`check` model against the PYTHON graph index over the fragment corpora
  (zcli already exists for `sem`; add a graph-state mode); (b) `CORRESPONDENCE.md`
  (Lean def ↔ Python file:line map); (c) final review doc using plan §7 wording
  verbatim.

Historical detail for every closed stage: `PROOF_STATUS.md` (ledger, newest first)
and `ROADMAP.md` (designs + post-mortems).
