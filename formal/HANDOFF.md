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

## State of the world (2026-07-11g — all sorry-free, axiom-clean, verify.sh green)

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

**Staged T2 widening: W1 ✅ → W2 ✅ → W3a ✅ → W3b ✅ → W3c ✅ → W3d-1a ✅ → W3d-1b NEARLY DONE (fan-out completeness ✅, read bridge ✅, settledness transport ✅; targeted-key RE-settlement + assembly NEXT) → W3d-1c → W3d-2 → W4.**

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

## The next task — W3d-1b (final leg): targeted-key RE-settlement + the invariant + `graph_correct_w3d`

**Session 2026-07-11g delivered the 1b core — READ ITS PROOF_STATUS ENTRY.** All in
`GraphIndex/CascadeStable.lean`:
- **Fan-out completeness (contrapositive), PROVED**: `writeLeg_checkFn_stable` — an
  unmapped key's operand `graphRec`/guard is unchanged by a logged write leg (route:
  `nreaches_factor` → `writeLoggedRules_edge_delta` → `mem_affectedKeys`). Attack
  finding: OUT-of-fragment object-star writes REFUTE it (the `wAll` head's name is
  STAR, `processor.py:604-605` skips it) — plain edge targets
  (`reachedByW3d_edges_target_plain`, from `BareStarStore`) are load-bearing.
- **The W3d read bridge, PROVED at EVERY state**: `UntaintedShadow` (a rules-ADMITTED
  state on the CURRENT store, differing only in edges into terminal `DerNode`s) +
  `reachedByW3d_shadow` (the write-leg ADMISSION transfer is the new content) ⇒
  `checkFn_eq_sem_w3d`. Mid-batch too: `untaintedShadow_applyD`/`_reconcileJobsD` —
  every prefix state of a cascade's job loop keeps the shadow.
- **Settledness transport, PROVED**: `writeLeg_sem_stable` (an unmapped key keeps its
  MEANING — the double-bridge trick: sem(t::T) = guard σ' = guard σ = sem(T));
  `SettledKey` (soundness-side: row members carry `sem` verdicts vs the CURRENT store;
  derived edges witness `sem`-true bare subjects) transports across write legs at
  unmapped keys (`settledKey_writeLeg` — rows write-inert, `writeLeg_derived_inedges_eq`
  = model-level I5) and cascades at untargeted keys (`settledKey_cascade_untargeted`).

**What remains for 1b (in dependency order):**
1. **Cascade-leg RE-settlement at targeted keys** (`settledKey_cascade_targeted`): after
   `runCascade` (accept), a key targeted by a job is `SettledKey` w.r.t. the (unchanged)
   store. Row half: the LAST targeting job wholesale-rewrites the row; its filters are
   guard-evaluated at ITS mid-batch state, where the read bridge holds
   (`untaintedShadow_reconcileJobsD` prefix + `checkFn_eq_sem_w3d`) — so `stars` =
   declared ∧ `sem`-covered (needs `coveredFn_declared` for the ↔, as in `w3c_row_char`),
   `neg`/`upos` members get their `sem` verdicts from their filter guards. Fold shape:
   induction over the batch, "some job so far targeted the key ⇒ row settled", later
   non-targeting jobs leave it (`applyD_other_key_fixed`), later targeting jobs re-derive
   it. Edge half: `reconcileStarsKeyD_edge_char` per pass + a NEW job-side coverage
   clause **`cands ⊇ pre-batch edge holders at the key`** (Python's audit enumerates
   persisted incoming R-node concretes, `processor.py:394-441`): a post-batch edge is a
   wanted candidate (guard = `sem`-true) or a non-candidate added by an EARLIER same-key
   job as a wanted candidate (`sem`-true too); pre-batch stale edges are candidates and
   get retracted. Attack-first the exact statement (hunt: two same-key jobs where the
   second's `cands` misses the first's added edge — should be fine since sem-true; a
   pre-batch stale edge NOT in cands — should break it, confirming the clause).
2. **The settledness invariant over `ReachedByW3d`**: `∀ derived key, key ∈ cascadeKeys
   S σ (dirty) ∨ SettledKey S T σ key`, by induction: write legs — dirty stays dirty
   (`cascadeKeys_writeLeg_mono`), settled+unmapped stays settled (`settledKey_writeLeg`),
   settled+mapped goes dirty (fine); cascade legs — `hcover` says every dirty key is
   targeted (re-settles, step 1), untargeted keys were settled (`hscope` ensures jobs sit
   at cascade keys; `settledKey_cascade_untargeted`); `cascade_drains`/no-abort ⇒ at
   CASCADED states `cascadeKeys = []` (a `Quiescent` state has an empty frontier) ⇒ ALL
   keys settled. NB the invariant needs the per-leg job coverage clauses (edge-holder
   coverage, `negCands`/`uposCands`/`cands` sem-completeness) carried as chain-side
   hypotheses — either strengthen `ReachedByW3d`'s cascade leg or define a
   `ReachedByW3dC` wrapper; completeness clauses become theorems in W3d-1c.
3. **Assemble `graph_correct_w3d`** at cascaded states: derived read via settledness
   (soundness) + the completeness clauses (row existence, `neg`/`upos`/edge
   completeness — mirror `W3cComplete`'s clause shapes as chain-side hypotheses);
   untainted read via the shadow + `graphRec_base_eq_bs`. Needs the W3d analog of
   `reachedByW3a_reach_collapse_root` (a multi-hop path into a derived R-node collapses
   to a single edge — in-edge sources are bare plain candidate nodes, whose own
   in-edges would be `BARE`-pred targets, dead on the fragment). Then
   `reachedByW3d_inv` (T2a carry) + T3/T6 `*_w3d` corollaries.

Fragment carries: `hterm`/`hCO`/`hLU`/`hRootB`/`hWSbare` + `BareStarStore`/`TtuStarFree`
+ W2 carries; add-only STORE (decision 6). House rule 6: subagents only for read-only
exploration.

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
