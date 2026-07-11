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

## State of the world (2026-07-11 — all sorry-free, axiom-clean, verify.sh green)

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

**Staged T2 widening: W1 ✅ → W2 ✅ → W3a ✅ → W3b ✅ → W3c ✅ → W3d (multi-stratum cascade) NEXT → W4.**

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

## The next task — W3d: the multi-stratum cascade (design first)

W3a–W3c all treat a reconcile pass as an externally-scheduled batch job over ONE derived
stratum (every operand untainted, `hLU`). W3d models the processor's actual **scheduling
loop** and (sub-stage 2) **derived-reading-derived** strata. Model source:
`index_v4/processor.py` `run_cascade` (`:694-740`) + `_map_deltas_to_keys`/`_fan_out` +
`outbox.py`; boolean spec §5.1. Shape of the Python loop: per stratum round, read outbox
rows above the frontier, map deltas to affected derived keys (fan-out tables + pending
residue bumps), reconcile each key **lower strata first**, flush; after `len(strata)`
rounds a non-empty leftover raises (stratification guarantees drain).

**Start by DESIGNING the sub-staging (read-only exploration + attack-first, then commit a
plan to ROADMAP before proving).** The natural split:
- **W3d-1 — the drain loop on the current one-stratum fragment.** Model outbox writes
  (`writeDirect` currently leaves the outbox empty in the model — decide whether to add
  delta emission or to model `run_cascade` as "keys-to-reconcile computed from a delta
  set") and the cascade as: compute affected keys from deltas, run `reconcileStarsKey`
  per key, advance the watermark. Contentful **T5** (a non-empty outbox drains to
  `Quiescent`) and the **cross-key re-reconcile hazard** (an operand edge write
  re-reaching an EXISTING residue key must re-reconcile it — this is where the
  ∀-targeting-jobs completeness clauses become theorems about the enumeration instead of
  hypotheses: `_fan_out` is what guarantees every targeting pass sees the subject).
- **W3d-2 — two strata (derived operand cones).** Relax `hLU`: a derived def may read a
  LOWER-stratum derived relation. `checkFn`'s leaf dispatch must then route derived
  operands through the residue read (`probeDerived`), not `probeNonDerived` — a real
  model extension (Python's `check_fn` leaf calls `widx.check`, which routes). Expect the
  W3a-admitted shadow and `graphRec_reconcileKey_inert` to need per-stratum
  generalisation (inertness of a stratum-k pass for stratum-<k reads).

Attack-first candidates: outbox interleavings/watermark skips vs the Python loop; a
stratum-2 def whose operand's residue is stale mid-cascade; re-reconcile after operand
REMOVAL (the model has no removes yet — check whether W3d-1 stays add-only, and say so
honestly in the fragment conditions).

House rule 6 applies: use subagents only for the read-only design exploration.

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
