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
   after recording the finding). This has killed five false statements so far
   (additive fuelBound, abstract WriteStep closure, T0a-sans-StoreDeclared, naive-W2
   TTU fragment, W3a single-edge collapse sans NoRuleOutputs). A session that kills a
   false statement is a GOOD session; record the finding.
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

## State of the world (2026-07-12g — all sorry-free, axiom-clean, verify.sh green)

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
| the DERIVED-leaf decomposition + routed reads-as-star + `enumJob2` coverage — `probeDerived_concrete_off_named`, `residueNamed`, `checkFnR_eq_star_of_not_enum`, `enumJob2`/`w3dJobCoverage_enumJob2`, `checkFnR_star_declared`/`w3d2_leg_context`, `w3dJobCoverage_enumJob2_state` | `GraphIndex/CascadeStrataEnum.lean` | **W3d-2 E-chain tail CORE (2026-07-12g)**: the two-round chain's audit enumeration + its `W3dJobCoverage`. Finding (c)'s residue-named candidates (`neg`/`upos`, edge-free/I6) folded into `enumJob2`; routed reads-as-star (no reach-collapse needed); coverage from the routed leg context (`checkFnR_eq_sem_settled` + `checkFnR_star_declared`) at any `ReachedByW3d2` state given operand settledness (`hsettledOps` — the one remaining obligation). Closure ASSEMBLY (`enumJobs2`, `ReachedByW3d2E`, `graph_correct_w3d2E`) is the next task |

**Staged T2 widening: W1 ✅ → W2 ✅ → W3a ✅ → W3b ✅ → W3c ✅ → W3d-1a ✅ → W3d-1b ✅ → W3d-1c ✅ (piece A `reachedByW3dC_inv` ✅ 2026-07-11j; piece B core `w3dJobCoverage_enumJob` ✅ 2026-07-12; piece B tail — enumerated-cascade restatement, `graph_correct_w3dE`/`reachedByW3dE_inv` — ✅ 2026-07-12b) → W3d-2 ◕ (OPENED 2026-07-12c: routed dispatch + conservativity + two-round scheduler + `ReachedByW3d2`; 12d: structural layer + T5-at-two-strata + per-stratum operand-read inertness; 12e: the W3d2 shadow + the stratum-staged read bridge + settledness transports + `ReachedByW3d2C`; **12f: ENDGAME CLOSED — the two-round re-settlement, `reachedByW3d2C_settled`, `graph_correct_w3d2` + T3/T6**; **12g: E-chain tail CORE — the derived-leaf decomposition, routed reads-as-star, `enumJob2` coverage + the routed leg context (`w3dJobCoverage_enumJob2_state`); only the closure ASSEMBLY remains**) → W4.**

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

## The next task — the W3d-2 E-chain tail: the CLOSURE ASSEMBLY

**The E-chain tail CORE is CLOSED (2026-07-12g — READ THE TOP PROOF_STATUS ENTRY).**
The NEW `GraphIndex/CascadeStrataEnum.lean` (sorry-free, axiom-clean, verify.sh green)
mirrors W3d-1c piece B (`CascadeEnum.lean`) over the two-round chain — the ENUMERATION
and its `W3dJobCoverage` are done:
- **The derived-leaf decomposition** (finding (c)): `probeDerived_concrete_off_named`
  (a star-free subject reads a derived leaf as its shape's `stars` row unless it hits
  one of three concrete-specific terms — an incoming edge, `res.neg`, `res.upos`);
  `residueNamed` (the neg+upos candidates Python's audit adds at a derived-reading key,
  `_derived_leaf_neg_ids`/`processor.py:461-495`, `upos` `:425-429` — edge-free/I6, so
  invisible to reach-probe enumeration).
- **The routed reads-as-star**: `graphRecR_leaf_agree` (per-leaf, both leaf kinds) →
  **`checkFnR_eq_star_of_not_enum`** (routed analog of W3d-1's
  `checkFn_eq_coveredFn_of_not_mem`; NO reach-collapse needed — reach into a leaf node
  already makes the subject a leaf concrete).
- **`enum2Base`/`enumJob2`** (W3d-1's `enumJob` with residue-named candidates folded in)
  + **`w3dJobCoverage_enumJob2`** (all four coverage clauses from the ROUTED leg
  context `hbridge`/`hcovDecl`).
- **The routed leg context**: `checkFnR_star_declared` (routed no-ghost-star-coverage,
  factored from `graph_correct_w3d2`'s `hsem_ws`) + `w3d2_leg_context` +
  **`w3dJobCoverage_enumJob2_state`** — `enumJob2` coverage over ANY `ReachedByW3d2`
  state given only that the derived operand keys are settled+complete (`hsettledOps`,
  the single remaining obligation).

**Next increment — the CLOSURE ASSEMBLY (pure scheduler plumbing, but intricate):**
1. **`enumJobs2`** — two per-round job lists, cursor-parameterized: round 1 over
   `cascadeKeysAbove S σ σ.watermark`, round 2 over
   `cascadeKeysAbove S (reconcileJobsLR S T σ jobs1) (σ.frontierMax σ.watermark)` (the
   MID state). Mirror `enumJobs_cover`/`_scope`/`_valid`. `W3cJobValid` for `enumJob2`
   is NEW work beyond W3d-1's `enumJob`: cands/negCands bare+star-free (bare filter +
   `edgeHolders`); uposCands non-bare star-free — the residue-named `neg`/`upos`
   members are star-free/non-bare by `SettledKey`'s `res.neg`/`res.upos` clauses (needs
   settledness at the enumerated key, so likely thread it through).
2. **Discharge `hsettledOps` per round.** Round 1: keys are STRATUM-1 (untainted
   operands) ⇒ `hsettledOps` VACUOUS — **the key sub-lemma to prove/find: a
   `cascadeKeysAbove S σ σ.watermark` key reads NO derived operand** (the dual of
   `round2_key_reads_derived`; the 12e attack established writes dirty only stratum-1
   operand keys). Round 2: stratum-1 operands settled by round 1 — thread
   `settledComplete_cascade2_targeted` / the per-round `SettledKey`/`CompleteKey`
   transports (`CascadeStrataSettle.lean`) to supply `hsettledOps` at the MID state.
3. **`ReachedByW3d2E`** (cascade legs run `enumJobs2` for both rounds) + the projection
   `reachedByW3d2E_toC` discharging all 8 `ReachedByW3d2C.cascade` hyps from state
   (`hjv*/hcover*/hscope*` structurally; `hcovg1/hcovg2` via
   `w3dJobCoverage_enumJob2_state` + the round-wise `hsettledOps`). Payoff:
   **`graph_correct_w3d2E`** — the two-stratum read theorem over the fully-operational
   scheduler chain, no chain-side coverage hypotheses.

Fragment carries: exactly W3d-2's (`hterm`/`hCO`/`hRootB`/`hWSbare` +
`BareStarStore`/`TtuStarFree` + W2 carries; add-only STORE, decision 6; `hLU2`).
House rules: **attack-first the round-1 stratum-1 sub-lemma (item 2)** — if a
`cascadeKeysAbove`-at-watermark key COULD read a derived operand, `hsettledOps` is not
vacuous and the whole round-1 discharge changes shape. Subagents read-only.

**After W3d-2 → W4** (full-scope restatement — combine W1+W2+W3 generality, name the
closure `ReachedBy`, restate at `GraphAccepts` scope), then **Phase 6** (graph-model
conformance extension, CORRESPONDENCE.md, final review doc).

---

## After W3d (the remaining road)
- **W4 — full-scope restatement.** Combine W1+W2+W3 generality; name the closure
  `ReachedBy`; restate `graph_correct` / `graph_reached_inv` / `backend_equivalence` /
  T6a/T6b over it at `GraphAccepts` scope (discharges the deleted-as-false abstract
  obligations). Carry: `NodupKeys`, `RewriteRanked`, `TtuTuplesetsDirect`, `hterm`
  (re-examine which W3a terminality conditions W4 must relax — `PDerivedTTU`/
  `PDerivedUserset` shapes were deferred).
- **Phase 6 — hardening.** (a) graph-model conformance extension: drive the Lean
  `writeDirect`/`check` model against the PYTHON graph index over the fragment corpora
  (zcli already exists for `sem`; add a graph-state mode); (b) `CORRESPONDENCE.md`
  (Lean def ↔ Python file:line map); (c) final review doc using plan §7 wording
  verbatim.

Historical detail for every closed stage: `PROOF_STATUS.md` (ledger, newest first)
and `ROADMAP.md` (designs + post-mortems).
