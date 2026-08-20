# ARCHITECTURE.md — the formal-verification development, by subject

This is the durable, topical map of the Lean 4 formal development: the trust root, the
two backend models, the theorems and their scopes, how the Python code is pinned to the
models, and the honest residual surface. It is organized by **subject**, not by the
timeline in which the work was done. Stage names from that timeline (`W1`…`W4`,
`T0`…`T6`, dated session tags) appear only where explicitly labelled *(historical
staging — see `history/`)*; the `T`-labels are the durable theorem IDs and do survive.

**Companion docs.** [`SEMANTICS.md`](./SEMANTICS.md) is the human-readable spec (the
trust root). [`CORRESPONDENCE.md`](./CORRESPONDENCE.md) is the Lean-def ↔ Python-file:line
map. [`FINAL_REVIEW.md`](./FINAL_REVIEW.md) is the authoritative, clause-checked claim.
[`HANDOFF.md`](./HANDOFF.md) is the state-of-the-world entry point. The provenance
archive — the session ledger, the staged-widening designs, and the early digest — lives
under [`history/`](./history/README.md).

---

## 1. What this proves (and what it does not)

The set-engine and graph-index **algorithms**, as modeled in Lean at the level of
`CORRESPONDENCE.md`, are **proven** to compute the stratified-Datalog¬ Zanzibar
semantics `sem`, and hence to be equivalent — machine-checked and axiom-audited. The
set-engine result holds at **full scope** (`setEngine_correct`'s three hypotheses are
all underscored and unused — the equality is literally unconditional). The graph-index
result holds at a **documented fragment** (`GraphAdmission ∧ W4Fragment`), not
everything the Python code admits. **Since 2026-08-05 that fragment DOES include stores
written through the `Direct` arm of a derived def (`can_view: [user] but not blocked`,
the canonical Zanzibar boolean shape) — it used to hold VACUOUSLY there, and for T2a
(`graph_reached_inv`) it still does. Read §6.0 before quoting any graph-side claim from
this document.** The **Python implementations** are pinned to those models empirically: by the
`CORRESPONDENCE.md` structural review, by five-corner differential conformance including
state-level equality under seven documented projections, and by exhaustive small-scope
enumeration up to tiny documented bounds. `FINAL_REVIEW.md` is the exact clause-by-clause
statement and governs; nothing in this document may claim more than it does.

**This never rounds up.** "The algorithms are proven" is not "the code is formally
verified": the interner/bitmap layer, the SQL/transaction/concurrency layer, the
compiler artifacts, the fragment carries, and the fidelity of the model-to-code
correspondence itself are all unverified surface (§6.1) — as are two whole subsystems with
no Lean model at all: the bulk build/backfill constructor (the DEFAULT `build_index` path)
and the multi-instance/HA layer.

---

## 2. The trust root — the specification `sem`

Everything downstream is proved **about `sem`**, the executable stratified perfect-model
evaluator defined in `SEMANTICS.md` and Lean's `Spec/` + `Core/`. `sem` is transcribed
from the repository's **independent oracle** (`tests/oracle.py`), which shares no code
with either backend — so the conformance triangle (spec · oracle · backend) has three
genuinely independent corners and one parser bug cannot corrupt two of them.

- **Domain** (`Core/`): schema AST (`Expr`/`Schema`, binary `union`/`inter` left-folded
  from the n-ary DSL), tuples/queries (`Refs.lean`), the store and its query universe
  (`Store.lean`), opaque valid identifiers (`Ident.lean`).
- **The store as a Datalog¬ program** (`SEMANTICS.md` §3): each `(schema, store)` denotes
  a stratified Datalog-with-negation program; `sem` is its perfect model.
- **Well-formedness** `WF S` (`Core/Schema.lean`, §4.2) and **stratifiability**
  `Stratifiable S` (`Spec/Stratify.lean`, §4.4): the verified envelope. Non-stratifiable
  schemas are rejected upstream and out of scope.
- **The evaluator** (`Spec/Semantics.lean`): `directLeaf` (star + userset branches),
  `ttuLeaf` (stored-parent TTU — TTU parents are STORED tupleset tuples, never computed
  membership), boolean composition, and `evalE`/`sem` — a **fuel-bounded primitive
  recursion** mirroring the oracle's depth-bounded provisional-false recursion. Faithful
  and total.

Two well-definedness theorems anchor the root, both full-scope, sorry-free, axiom-audited:

- **T0a** `sem_fuel_stable` (`Spec/WellDef.lean`): over declared stores (`StoreDeclared`)
  and stratifiable schemas, the evaluator is **fuel-stable** — for any fuel `≥ fuelBound
  S T`, `semAux … = sem S T q`. (`StoreDeclared` is load-bearing, not decoration: without
  it the statement is machine-checked FALSE — `Spec/Counterexample.lean`. There is no
  separate relational `Sem`; the Phase-0 "relational ≡ executable" form was never built.)
- **T0b** `stratify_none_iff_cycle` / `stratify_topological` (`Spec/WellDef.lean`):
  `stratify` fails **exactly** on a derived-dependency cycle, and on success the stratum
  assignment is topological.

---

## 3. The two backend models

Both models are **concrete Lean definitions** (not opaque postulates), each mapped to a
Python module by `CORRESPONDENCE.md`.

### 3.1 The set-engine model (`SetEngine/`)

The star-closed `MemberSet` algebra (`pos`/`stars`/`neg`, `MemberSet.lean`) plus
on-the-fly expansion (`expandDirect`, `expandTtu`, `SetEngineModel.check` in `Eval.lean`).
It stores raw tuples and computes memberships on demand with set algebra — the model of
`setengine/`. No materialized closure.

### 3.2 The operational graph-index model (`GraphIndex/`, `FullScope.lean`)

A concrete state machine `GraphState` (nodes / path-counted closure edges / residues /
outbox / watermark, `State.lean`) with reads via `GraphModel.check` (route by
`isDerived`; ≤ 4 probes for untainted, edge-probe + `stars`∖`neg` / `upos` residue for
derived). The model of `index_v4/`.

The load-bearing object is the **operational closure** `ReachedBy` (`:=
ReachedByW3d2E`, `FullScope.lean` / `CascadeStrataAssemble.lean`) — the set of states
reachable from empty by the **synchronous v1 Python write path**, modeled as a chain of:

> admitted logged **rule-routed writes** → the **reconcile diffing pass** (stale-edge
> retraction + residue recompute) → the **per-stratum two-round cascade** over the
> outbox → **drain** to quiescence,

interleaved as Python interleaves them (`connectedstore.advance_index` →
`DeltaProcessor.run_cascade`). The chain was **add-only** by construction until
2026-07-19f, when a `remove` constructor — gated on removing a validly-stored tuple
(`t ∈ T`) from a drained prior state (`cascadeKeys = []`), with the pre-remove
store's disciplines carried, faithful to `TupleSource.remove` — was added to
`ReachedByW3d2`/`C`/`E`, so T2a/T2b now cover retraction at that scope. The Exec
driver / zcli graph mode now DRIVES removes end-to-end (2026-07-19, `5a35ec3`):
the op-stream driver `graphRunOps` runs one runtime-gated `remove` chain leg
(`removeGateB`, fail-closed) per op and zcli takes an optional `"ops"` add/remove
stream, so remove-correctness is now both proved over the chain AND driven
end-to-end (differential-gated at answer level by `test_conformance_remove_graph.py`)
— **over every in-fragment corpus except `direct_arm_exclusion`, which that gate's
`_REMOVE_EXCLUDED` skips because the guard's plain-`StoreValidRules` precondition makes
`removeGateB` fail closed there (§5, §6.0).**
`CORRESPONDENCE.md` §4–6 maps
every step (`reconcileStarsKeyD`, `graphRecR`/`checkFnR`, `affectedKeys`, `runCascade2`)
to `processor.py` line ranges.

---

## 4. The theorem structure

All theorems are in `formal/lean/ZanzibarProofs/`, all **sorry-free**, all
**axiom-audited** (each depends only on `[propext, Classical.choice, Quot.sound]`). They
quantify over a schema `S`, a finite store `T`, and a query `q`.

| topic | ID | Lean name (file) | scope |
|---|---|---|---|
| well-definedness | T0a | `sem_fuel_stable` (`Spec/WellDef.lean`) | full |
| well-definedness | T0b | `stratify_none_iff_cycle` / `stratify_topological` (`Spec/WellDef.lean`) | full |
| set-engine correctness | T1 | `setEngine_correct` (`SetEngine/Correct.lean`) | **full** |
| graph invariant | T2a | `graph_reached_inv` (`FullScope.lean`) | GraphAdmission ∧ W4Fragment |
| graph correctness | T2b | `graph_correct` (`FullScope.lean`) | GraphAdmission ∧ W4Fragment, drained |
| backend equivalence | T3 | `backend_equivalence` (`FullScope.lean`) | = T2b |
| path-count maintenance | T4 | `pathCount_addEdge` / `pathCount_removeEdge` (`GraphIndex/Closure.lean`) | full (acyclic) |
| cascade termination | T5 | `runCascade2_no_abort` / `cascade2_drains` (`GraphIndex/CascadeStrata.lean`) | ≤ 2 strata |
| security: exclusion | T6a | `exclusion_effective` (`FullScope.lean`) | = T2b |
| security: no ghost grant | T6b | `no_ghost_grant` (`FullScope.lean`) | = T2b |
| security: wildcard scoping | T6c | `wildcard_scoping` (`Equiv.lean`) | full |

What each says, in English:

- **T1** — for every WF, stratifiable schema and identifier-valid store, the set-engine
  model's `check` equals `sem`. Full scope. (The three hypotheses are retained to match
  the equivalence route but the equality is unconditional — all three are underscored
  and unused in the proof, `SetEngine/Correct.lean::setEngine_correct`. "Full scope" is if anything an
  under-claim here.)
- **T2a** — the 8-clause graph invariant `Inv` (structural I1–I3 + the four I6
  residue-hygiene clauses) holds at **every** operationally-reached state — dirty keys
  and mid-drain included. (There is **no** `materialized = materialize …` state-equality
  theorem; state-level agreement is pinned empirically, §5.)
- **T2b** — at every **fully drained** reached state, `GraphModel.check σ q = sem S T q`,
  for derived and untainted queries with a concrete object and bare-predicate star
  subjects.
- **T3** — `SetEngineModel.check S T q = GraphModel.check σ q` (T1 ∘ T2b, transitivity
  through `sem`; same scope as T2b, never wider).
- **T4** — under acyclicity, adding/removing one direct edge preserves the path count
  `p = #paths` (the counting theorem — the basis of exact reference-counted removal).
- **T5** — the two-round cascade drains every dirty key; the scheduler's abort branch is
  provably **dead** at ≤ 2 derived strata (and provably **live** at 3 — attack-confirmed,
  which is exactly why `twoStrata` is an honest carry, below).
- **T6a/T6b/T6c** — real exclusion content (a subject removed by a `but not` operand is
  denied by both backends, incl. under a `T:*` grant); no stale edge/residue survives a
  drain to grant a `sem`-false query; a `T:*` grant never leaks across subject types.

### 4.1 The graph-side scope split — two bundles, by provenance

The graph theorems (T2a/T2b/T3/T6a/T6b) carry two hypothesis bundles, split by where the
restriction comes from (`FullScope.lean`):

- **`GraphAdmission S T`** — the **Python-admission mirror**: what the Python compiler +
  write admission already guarantee for every accepted schema/store. Fields (each
  docstring cites the enforcing Python mechanism): `wf`, `nodup`, `strat`, `ttuDirect`
  (untainted TTU tuplesets direct-only), `matchDecl`, `ranked`, `objWild` (object-wildcard
  shapes never on derived relations), `storeValid`. This bundle imposes **nothing Python
  does not already impose**.
- **`W4Fragment S T`** — the **honest carries**: scope restrictions the current proof
  needs that Python admission does **not** imply. `structure W4Fragment`
  (`FullScope.lean`) has exactly **TEN** fields since E-chain leg 5 (2026-08-05) split
  the single `computedOnly` into five. The five SHAPE conditions on a derived def:
  `computedOrDirect` (a boolean tree over `computed` refs AND `direct` grant arms —
  `.ttu` leaves still banned), `directArmsBare` (its `Direct` arms carry only BARE
  restrictions), `directArmsConcrete` (…and no wildcard-flagged ones), `computedOnlyOperands`
  (its DERIVED operands are themselves `ComputedOnly` — only the top def may carry a
  `Direct` arm), `noUnionDirects` (its `Direct` arms sit under `inter`/`excl` only, never
  union-reachable — the canonical `but not`). The derived-def ROOT operator has been
  unrestricted since the 2026-07-17 widening **deleted `rootB`/`RootBoolean`**. Then the
  five carried over verbatim: `twoStrata` (≤ 2 derived strata —
  attack-confirmed load-bearing), `wsBare` (declared wildcard restrictions all bare
  `[T:*]`), `bareStar` (stored star subjects bare, objects concrete), `ttuStarFree` (no
  stored star subject feeds a TTU tupleset), `term` (derived relations never TTU targets
  nor stored userset-subject predicates). Every field is a documented gap (§6.1 item 3), and
  `computedOnly`'s gap is the §6.0 vacuity. There is **no `rootB` field** — any doc
  still listing one is stale by more than a week. The ADD-ONLY restriction is likewise
  not a field: it was a property of the chain, and since 2026-07-19f the chain carries a
  scoped `remove` constructor (§3.2).

`w4_within_scope` (`FullScope.lean`) proves `GraphAdmission ∧ W4Fragment → GraphAccepts`
— the proved fragment sits **inside** the decision-15 accepted class. The converse is
false: `GraphAccepts` admits schemas outside `W4Fragment`, and no theorem covers that
surplus. **Non-vacuity**: `W4Witness` machine-checks that both bundles are inhabited by a
real compiled boolean schema, so the final theorems are not vacuous. (Honesty caveat,
per `FINAL_REVIEW.md` §2: what is kernel-checked is inhabitation of the hypothesis
*bundles*; joint inhabitation of a drained, non-trivially-reached state is demonstrated
empirically via the conformance driver plus the proved `cascade2_drains`, not as a single
kernel-checked term.)

The final theorems are **unsuffixed** in `FullScope.lean`; the pure-direct starter
versions survive under `*_direct` names *(historical staging — the W1→W4 widening, see
`history/`)*.

### The staged T2 ladder (moved here from `HANDOFF.md`, 2026-08-16)

The table above is the *final* inventory. The one below is the **staging history** — one row
per intermediate fragment, each naming the file that holds it. It is the map to use when a
proof mentions `graph_correct_w3a` or `reachedByW3d2C_settled` and you need to know which
module to open; roughly fifteen of these filenames appear nowhere in the final table.
It lived in `formal/HANDOFF.md` until the 2026-08-16 deep-half restructure
(redesign §9 step 12), which moved it here, its declared home.

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
| the DIFFING pass + per-key edge EXACTNESS | `GraphIndex/ReconcileDiff.lean` | W3d-1b groundwork: `reconcileStarsKeyD` (stale-edge retraction, `processor.py::DeltaProcessor._reconcile_subject`), both-direction reach inertness, guard fold-invariance, `reconcileStarsKeyD_edge_char` (the re-settle as a theorem) |
| FAN-OUT COMPLETENESS + the untainted-core shadow + settledness transport | `GraphIndex/CascadeStable.lean` | W3d-1b core: `writeLeg_checkFn_stable` (unmapped keys' guards unchanged), `reachedByW3d_shadow`/`checkFn_eq_sem_w3d` (guard = `sem` at EVERY W3d state, incl. mid-batch), `writeLeg_sem_stable` (unmapped keys keep their MEANING), `SettledKey` + write-leg/untargeted-cascade transport |
| T2b **`graph_correct_w3d`** + the settledness invariant + targeted RE-settlement | `GraphIndex/CascadeSettle.lean` | W3d-1b CLOSED: `ReachedByW3dC` (coverage chain: per-job `W3dJobCoverage`, attack-confirmed edge-holder clause), `settledComplete_cascade_targeted`, `CompleteKey` + transports, `reachedByW3dC_settled` (dirty-or-settled at EVERY state), the W3d reach collapse, `check = sem` at every fully-drained (`cascadeKeys = []`) state; T3/T6 `*_w3d` |
| T2a **`reachedByW3dC_inv`** — the FULL 8-clause `Inv` (+ `reachedByW3d_structInv` / `reachedByW3d_residueHygienic` / `reachedByW3d_residueDeclared` / `reachedByW3dC_edgeHygienic`) | `GraphIndex/CascadeInv.lean` | W3d-1c piece A CLOSED: `Inv` at EVERY coverage-chain state (dirty keys, mid-drain included). Structural half + edge-free I6: NO fragment hyps. Edge-referencing I6 (`negEdgeFree`/`uposEdgeFree`): attack-REFUTED over the plain chain (stale non-candidate edge — the coverage clauses are load-bearing for the invariant itself, not just the read theorem); proved over `ReachedByW3dC` via row-key declaredness + the reach collapse + the `SettledKey` verdict clash at targeted keys |
| **`w3dJobCoverage_enumJob`** (+ the collapse `checkFn_eq_coveredFn_of_no_extra`, `leafConcretes`/`edgeHolders`, per-clause discharges, `w3d_leg_context`) | `GraphIndex/CascadeEnum.lean` | W3d-1c piece B CORE: **`W3dJobCoverage` is now a THEOREM** of a state-derived enumeration (was a chain-side hypothesis). Spine: a star-free subject's operand leaf reads decompose pointwise as star-read ∨ two concrete probes (`probeNonDerived_concrete_decomp`); a subject hitting neither probe reads exactly as its shape-star (`evalE` congruence, exclusion-safe). `w3d_leg_context` rebuilds the read bridge + coverage-declaredness at any W3d state via the shadow |
| **`graph_correct_w3dE`** / **`reachedByW3dE_inv`** (+ `ReachedByW3dE`, `reachedByW3dE_toC`, `enumJobs`/`_valid`/`_cover`/`_scope`/`_covg`, `w3cJobValid_enumJob`, `reachedByW3d_Rnode_source_name_ne_star`) | `GraphIndex/CascadeEnum.lean` | **W3d-1c piece B TAIL — W3d-1c CLOSED.** The enumerated-cascade restatement: `ReachedByW3dE` is the fully-operational scheduler chain (cascade legs run the state-derived `enumJobs`, NO `W3dJobCoverage`/`hcover`/`hscope`/`hjv` in the constructor); `reachedByW3dE_toC` projects it to `ReachedByW3dC` (the four hyps discharged by `enumJobs_*`, store hyps weakened along write prefixes). `check = sem` (fully-drained) and the full 8-clause `Inv` (every state) now hold UNCONDITIONALLY over the operational chain |
| the ROUTED leaf dispatch + conservativity + the TWO-ROUND scheduler | `GraphIndex/CascadeStrata.lean` | W3d-2 OPENING: `graphRecR`/`checkFnR`/`coveredFnR` (every operand leaf reads the graph's own `check` — untainted ⇒ `probeNonDerived`, derived ⇒ `probeDerived`; `processor.py::_EvalContext.leaf_check` / `::_EvalContext.derived_check` / `::_EvalContext.tupleset_ttu_check`), `checkFnR_eq_checkFn` (conservativity: on untainted-operand defs the routed read IS the W3d read), `checkFnR_evalEq` (the routed read consults exactly the `EvalEq` core — residue+schema now included), the routed diffing pass + `reconcileJobsLR_eq` (W3d-1 is the single-stratum image of the routed scheduler), `runCascade2` (rounds = 2, per-round frontier cursor, leftover reject), `ReachedByW3d2` (C-style two-batch closure), `reachedByW3d2_schema`. Attack-first: fully-drained `check = sem` SURVIVED all cross-stratum vectors; mid-drain staleness real; within-round order not load-bearing |
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

---

## 5. Pinning the Python to the models

The theorems are about the Lean models. The tie to Python is the `CORRESPONDENCE.md`
review plus the **conformance harness** (`formal/conformance/`), gated by the
one-command `formal/verify.sh`. The gate is **fail-closed**; the live counts are
GENERATED into `FINAL_REVIEW.md`'s counts block and re-checked by `verify.sh` step 4e,
and this file must not disagree with it. When measured for this revision (2026-07-29)
it was green:

> `lake build` + **0 sorries** (`formal/conformance/sorry_scan.py`) + `zcli` preflight +
> **axiom audit** (**460** observed reports = 460 `#print axioms` commands, exactly one
> per command, only `[propext, Classical.choice, Quot.sound]`) + **465 conformance
> tests, 0 skips, 0 xfails** (the conformance step fails on any skipped test or zero
> passes).

**What the gate did NOT do** (zero-trust review 2026-07-26, `ZT-P2-1`/`ZT-P2-2`): it
derived the "expected" axiom-report count from `Audit.lean` itself and compared for
equality with no floor, and it asserted only `skipped == 0 && passed > 0` on
conformance. Deleting audited theorems, or a whole conformance suite, kept it green;
an `xfail` was invisible to it. That hole was closed by the 2026-07-26/27 floor
hardening (`EXPECTED_MIN_AUDITS`/`MIN_CONF_ALL`/`MIN_TESTS_ALL` + the identity,
statement and definition pins + zero-tolerance skip/xfail parsing — `docs/gate-runbook.md`
§2). The counts above remain dated measurements rather than the enforced floors —
re-measure, and never read a count as coverage.

Because the Lean spec is executable, the same artifact is both proof subject and the CLI
oracle `zcli`. The collected tests are **differential-conformance comparisons** plus a
small set of **gate-tooling unit tests** (not Lean-vs-Python comparisons: the
sorry-scanner, `test_sorry_scan.py`, and the zcli-runner transient-init retry,
`test_runner_retry.py`). The totals and the per-file table are GENERATED into
`FINAL_REVIEW.md`'s counts block — do not restate them here; by subject the
differential comparisons break down as:

- **Answer conformance — the five corners.** Over a shared query grid, `check` verdicts
  are compared five ways: Lean `sem` (zcli) × the independent oracle × the real
  `SetEngine` × the Lean **operational graph model** (zcli mode `"graph"`) × the real
  Python `WildcardIndex`+`DeltaProcessor`. The Lean graph model's verdicts are covered by
  T2b *by proof, not analogy*: `Exec.lean`'s driver folds the `ReachedBy` constructors
  (`graphRun_reached`), its runtime gates decide the theorem's side conditions
  (`foldAdmitsB_iff`, `drainedB_iff`), and under the W4 bundles every printed verdict is
  `sem` (`graphRun_check_eq_sem`). Suites: `test_conformance_spec.py` (every
  spec-scope corpus — `SCHEMAS` plus the `TTU_USERSET_SCHEMAS`,
  `SELF_REFERENTIAL_SCHEMAS` and `MULTI_STRATUM_SCHEMAS` (`three_strata_chain`) corpora
  that are deliberately kept out of the graph-side gates; the four-dict total is in the
  generated counts block),
  `test_conformance_random.py` (seeded randomized substores), `test_conformance_graph.py`
  (every in-fragment corpus, incl. two designed attack corpora — stale-edge
  cross-stratum re-settle, star churn over two strata), `test_conformance_direct_arm.py`
  (the Direct-arm corpus, at C-chain scope only — §6.0). **Scope caveat:** one of
  them, `direct_arm_exclusion`, is listed in `GRAPH_FRAGMENT` but is machine-checked to be
  OUTSIDE the final theorems' hypotheses, so its comparisons are a differential test
  between two implementations, not coverage by T2b. The CLI does not gate on
  `GraphAdmission`/`W4Fragment` at all — its rc 2/3 gates test run-success and
  drained-ness only. See §6.0.
- **The shared grid** (`formal/conformance/grid.py`): targets are the stored-tuple cross
  product **plus** every schema-**DECLARED** `(type, relation)` unioned type-aware — so
  derived/boolean roots are queried on every corpus (previously derived-only boolean roots
  went unqueried and that evidence was vacuous exactly there); subjects include bounded
  userset-shaped subjects. The concrete-named userset queries sit inside the proved graph
  query scope (`hqs` constrains only star-NAMED subjects).
- **Mode-dispatch fail-closure** (`test_cli_mode.py`): an unknown / non-string zcli
  `"mode"` returns rc 4, and an `"ops"` stream supplied in spec mode returns rc **5**
  rather than being silently ignored (full rc enumeration: 0 answers-or-state /
  1 usage-parse / 2 admission / 3 not-drained / 4 unknown mode / 5 `"ops"` in spec mode),
  so spec answers can never masquerade as graph answers and an op stream can never be
  dropped on the floor.
- **State-level graph conformance** (`test_conformance_state.py`, every
  `GRAPH_FRAGMENT` corpus): the
  Lean graph model's FINAL MATERIALIZED STATE (zcli mode `"graph-state"` — same
  `graphRun` fold, same admission/drain gates, emitting canonical direct edges + residue
  triples) is diffed against the real Python graph index's final SQL state
  (`EdgeV4`/`ResidueV1` decoded through `NodeV4`). Compared under **seven documented
  projections** P1–P7, each justified in `formal/conformance/extractor.py`: P1 closure
  rows (a function of the direct set), P2 wildcard bridges (inert — RE-MEASURED
  2026-07-29 over the 23 corpora then in the fragment: 477 raw `EdgeV4` rows, **P2
  dropped 0 of them**, and `bridged_in_shapes`/`bridged_out_shapes` compiled EMPTY on
  all 23, the only non-empty pairs in the corpus file being shapes excluded from
  `GRAPH_FRAGMENT`; the generated projection ledger keeps the live P2 row, still
  0), **P3 edge multiplicity —
  NARROWED 2026-07-29 to the DERIVED arm only** (the untainted arm is now compared
  EXACTLY, and the derived arm is golden-pinned by
  `test_conformance_state.py::test_derived_arm_multiplicity_ledger`; see
  `CORRESPONDENCE.md` §7.2 for the adjudication), P4 all-empty residue rows, P5 node GC (**no `NodeV4` row is compared at
  all**), P6 leaf-family closure-leaf copies
  (evaluation output compared exactly), **P7 `ResidueV1.version`** — declared
  2026-07-27, and unlike P1–P6 a **MODELLING GAP, not a representation difference**:
  Lean's `Residue` has no version field at all, so invariant **I7 is gated by nothing
  formal** (§6.1 item 4). Attack-first: the gate's first run FOUND the P6
  divergence under full check-parity; a deliberately corrupted extraction fails with the
  symmetric-difference message.
- **Exhaustive small-scope enumeration** (`test_conformance_enum.py`): ALL stores of ≤ K
  tuples over a 2-names-per-type pool, for **six** representative fragment shapes at a
  per-shape K of 3 or 4 — boolean_exclusion (K=4, 163 stores), boolean_intersection
  (K=4, 163), two_stratum_cascade (K=3, 299), boolean_star_exclusion (K=4, 57),
  wildcard_group_member (K=3, 176), ttu (K=4, 163); **1021 stores total, per-shape space
  size / K / store count all asserted** so the bounds cannot
  silently drift. spec × oracle × set engine over the shared grid; zero disagreements.
  `test_conformance_enum_state.py` adds a state-level leg over a deterministic stride-4
  sample — **257 of those 1021 stores** (~25 %), sample size asserted. The
  graph backend is deliberately not in the ANSWER enumeration (it stays pinned by the
  curated-corpora graph + state gates), and the bounds are deliberately tiny.
- **Remove-path conformance** (`test_conformance_remove.py` — exactly the `conf-heavy`
  gate phase; its test count is in the generated per-file table): the REAL `SetEngine`
  driven through seeded
  interleaved add/remove/re-add sequences (all spec-scope corpora × 5 seeds) equals
  `sem` (zcli) × the oracle on the FINAL store — the first ANSWER-LEVEL pin on Python's
  remove path — plus two Python-internal convergence pins: the driven engine equals a
  fresh `rebuild()` over the grid AND at id-free state-fingerprint granularity (interner
  keys/refcounts, population masks, node_sets/member_of, flow-graph edges), and a full
  add-all/remove-all/re-add churn test asserts complete state emptiness mid-cycle. The
  **graph-index** leg drives the SAME sequences/seeds through the real `WildcardIndex`
  +`DeltaProcessor` (synchronous v1 write path, I5 leaf-routing symmetry so a remove
  retracts exactly what its add materialized): driven graph `check` == oracle on the
  accepted final store, driven graph SQL state (`snapshot_rows` + id-free symbolic
  residues) == a fresh add-only build's, and a full-churn test asserts the graph drains to
  a fresh-EMPTY state (no `NodeV4`/`EdgeV4`/`ResidueV1` rows) with I12 non-mutation on a
  rejected repeat remove. Scope honesty: BOTH Python remove paths are now pinned to
  oracle/`sem` (the graph transitively, via `graph == oracle` on the corpora the set-engine
  leg pins `sem == oracle`); the Lean-side remove leg is now CLOSED too (2026-07-19f, §6)
  at the validly-stored + drained-prior scope, and the Exec driver DRIVES it
  end-to-end (2026-07-19, `graphRunOps` / zcli `"ops"`; `test_conformance_remove_graph.py`
  differential-gates seeded add/remove/re-add streams == the real Python graph index
  == oracle on the erased store, at ANSWER level), so remove-correctness is both
  proved AND driven — **with one live exclusion:
  `test_conformance_remove_graph.py::_REMOVE_EXCLUDED` is
  `frozenset({"direct_arm_exclusion"})`, because the chain's remove guard is
  stated over plain `StoreValidRules`, under which a Direct-arm-under-exclusion tuple is
  inadmissible, so `removeGateB` fail-closes (rc ≠ 0) on essentially every seeded stream
  over that corpus. Removes are driven end-to-end over every in-fragment corpus EXCEPT
  that one (the newest); its Python remove path is still gated by
  `test_conformance_remove.py`, just not against Lean.** The Lean-vs-Python state
  comparisons for removes remain driven-vs-fresh-build Python-internal, never vs Lean.
- **Generated-schema conformance** (`test_conformance_generated.py`, 40 tests,
  2026-07-12): a seeded deterministic re-implementation of the hypothesis `schema_asts`
  generator (NO hypothesis dependency — the formal/ convention; inside
  `formal/conformance/` so `verify.sh` gates it fail-closed) produces schemas + stores
  OUTSIDE the curated corpora, asserting zcli `sem` == oracle == real `SetEngine` over
  the shared grid. This closes the disjoint-pools gap — a `sem`/model-fidelity divergence
  on non-curated schema shapes was previously invisible to every gate (§6.1 item 1).
  Answer-level, spec-side only; the graph backend stays pinned by the curated corpora.

Separately, the repository-wide **validation matrix** (`tests/test_matrix.py`) pins
Python-graph × Python-set × oracle on every push, and the **compiled-RuleSet snapshot
tests** (`tests/snapshots/`, `tests/test_compile_snapshot.py`) are the byte-identity gate
on untainted compilation — the pin on the compiler artifacts the Lean model does not
cover (§6.1 item 2). The **lookup-surface oracle gate** (`tests/test_lookup_oracle.py`,
2026-07-12) pins `lookup`/`lookup_reverse`/`expand` on both Python backends by composing
`oracle.check` into brute-force reference lookups; the four genuine divergences it found
(X1–X4) were fixed 2026-07-13 Python-side and stand as plain regression pins (§6.1 item 3's note,
`docs/spec-deviations.md` 2026-07-13).

---

## 6. Honest scope + residual unverified surface

Mirroring `FINAL_REVIEW.md` §3/§4 (which governs — if the two ever disagree, that file
wins and this one is stale). The current honest claim is §1's, with **one explicit
subtraction and three scope qualifiers**: the graph-side theorems hold at `W4Fragment`
scope (not everything Python admits) — which since 2026-08-05 includes the canonical
boolean idiom, **except for T2a `graph_reached_inv`, still vacuous there, §6.0**;
state-level equality holds under the seven documented
projections (a divergence *inside* a projected class is pinned elsewhere, not here;
nodes are not compared at all);
enumeration is exhaustive only up to its tiny documented bounds. Never round these up.

### 6.0 The Direct-arm vacuity: RETIRED for T2b (2026-08-05), STILL LIVE for T2a

Until 2026-08-05 this section read *"The headline graph theorems are VACUOUS on the
canonical boolean idiom"* and meant it literally: not "narrower coverage" but **no
theorem**. `W4Fragment.computedOnly` required every derived def to read only `computed`
operand leaves, so a store holding a tuple written through the **`Direct` arm of a
derived def** —

```
can_view: [user] but not blocked
```

— the commonest Zanzibar boolean shape there is, fell outside the bundle, in the
strongest available sense: `GraphAdmission.storeValid` **was** `StoreValidRules`, and
`FullScope.lean::W4WitnessDirect.outside_old_admission` machine-checks its negation at
exactly such a store (`Sd` = `banned := [user]`, `approver := [user] but not banned`;
`Td` = one write of `user:alice` through the derived def's `Direct` arm). The reason is
structural: the Direct arm sits under `excl`, so `exprDirects` on the derived def is
empty and no rule can justify the stored tuple. `history/PROOF_STATUS.md` said it in one
line - *"the CURRENT admission bundle is UNSATISFIABLE"* on that shape.

**The E-chain Direct-arm widening arc closed this for T2b on 2026-08-05.** Leg 2 swapped
the operational enumeration (`enumJob2` -> `enumJob2D`); legs 3-4 built the `_d`
projection (`reachedByW3d2E_toC_d` / `graph_correct_w3d2E_d`, the audited originals now
byte-identical wrappers); **leg 5 rebased the bundles** - `GraphAdmission.storeValid` is
`StoreValidRulesD`, and `W4Fragment`'s single `computedOnly` field became five
derived-def clauses (`computedOrDirect`, `directArmsBare`, `directArmsConcrete`,
`computedOnlyOperands`, `noUnionDirects`); leg 6 carried it into the conformance
classification.

So `graph_correct` (T2b), `backend_equivalence` (T3), the T6 security corollaries and
`Exec.graphRun{,Ops}_check_eq_sem` now **cover** that shape.
`W4WitnessDirect.final_applies` instantiates the unsuffixed `graph_correct` at the
minimal Direct-arm store and `final_applies4` at the four-tuple `direct_arm_exclusion`
corpus store verbatim. `outside_old_admission`/`outside_old_admission4` are kept and
still audited - they are now the proof that this was a **widening** and not a
relabeling - and `w4Fragment_of_computedOnly` proves the pre-leg-5 six fields imply all
ten, so nothing that held before stopped holding.

**The one exception, and it is a real one: T2a.** `graph_reached_inv` now takes a THIRD
bundle, `W4NarrowT2a` (schema-wide `ComputedOnly` + the narrow `StoreValidRules`), and
`W4WitnessDirect.outside_narrow_t2a` machine-checks that the Direct-arm store fails it.
**T2a is still vacuous exactly where T2b no longer is.** That is a declared carry with a
counterexample attached, not a proof gap: Leg-0 probe D.3 machine-checked
`Inv.negEdgeFree` FALSE on the `_d` fragment (under `StoreValidRulesD` a Direct-arm write
lands an edge at the very derived R-node whose residue carries the `neg` row). **Python
is fine** - `RuleSet.apply` routes the write onto the leaf family, so the edge and the
`neg` row live on different nodes; 0 mismatches over the grid and a 6-way order sweep on
the real backends. It is a modelling limit of projection **P6** (the leaf-family
collapse), and a **design decision** is owed before further work: (a) restate T2a at
drained states only, (b) weaken `negEdgeFree` to exempt the current
un-cascaded write leg, or (c) model the leaf-family split.
(⚠ (b) used to read `negEdgeFree`/`uposEdgeFree`; the pairing was refuted by
measurement 2026-08-08 — `uposEdgeFree` is structurally immune on the `_d`
fragment. See `history/leaf-family-split-scope-2026-08-05.md` §9.2.)

**The conformance evidence on that shape is now theorem-backed for answers.**
`direct_arm_exclusion` moved into `test_conformance_graph._THEOREM_BACKED` (the split is
`(23, 0)`), licensed by `final_applies4` and by nothing weaker - both bundles are
STORE-indexed, so the witness had to be taken at the corpus's own four tuples, not at a
one-tuple subset. Two carve-outs remain: the T2a asymmetry above, and the Lean REMOVE
gate (`removeGateB` decides plain `storeValidRulesB`, so the corpus stays in
`_REMOVE_EXCLUDED` - now for THAT reason alone, no longer for the admission reason it
carried before leg 5; §5).

The standing hazard that made this section necessary is unchanged: **the CLI never gates
on `GraphAdmission`/`W4Fragment`** (rc 2/3 test run-success and drained-ness only), so
membership in `GRAPH_FRAGMENT` is not membership in the proved fragment. Only a written
per-field argument or a Lean witness makes it so.

### 6.1 The residual unverified surface, in full

1. **Model-to-code fidelity itself** — the theorems are about the Lean models; the tie to
   Python is `CORRESPONDENCE.md` + empirical conformance. A Python behavior outside the
   corpora/grids could diverge without failing the gate. *Narrowed 2026-07-12:* the
   schema-SHAPE half of this risk is closed at answer level, spec-side, by the
   generated-schema gate (`test_conformance_generated.py`, §5); behaviors outside the
   generated envelope, and the graph backend on non-curated shapes, remain unpinned.
   **And correspondence review is a sampling process, demonstrated (2026-07-20b):** a
   real model-vs-Python infidelity was found *inside the audited chain, after this effort
   was described as complete* — Lean's `affectedKeys` was reader-only and lacked Python's
   LeafFamily own-key branch, producing a modeled state that was drained
   (`cascadeKeys = []`) with `check = true` and `sem = false`. It killed
   `reachedByW3d2C_settled_d` / `graph_correct_w3d2_d` as specified; fixed 2026-07-20c
   via a `Delta.leaf` provenance tag (a first naive fix was itself attack-killed).
   It was found by attack-first `#eval` while widening scope, not by review and not by
   any gate; it was benign within the then-proved `ComputedOnly` scope, which was luck of
   scope rather than diligence; and the Lean **docstring above the definition claimed the
   missing branch**, so cross-checking the two artifacts would have shown false
   agreement. See `FINAL_REVIEW.md` §3 item 1 and `CORRESPONDENCE.md` §7.
2. **The Python COMPILER artifacts are trusted, not modeled** — `compile_ruleset`'s taint
   computation, strata assignment, derived-predicate plans, fan-out tables, and
   leaf-family routing have no Lean counterpart (the Lean model reads the RAW boolean defs
   and derives taint/strata/jobs itself). Pinned by the snapshot tests + the conformance
   corpora; a compiler bug on an unexercised shape would not fail any Lean gate.
3. **Fragment carries** — the `W4Fragment` gaps (§4.1): > 2 derived strata; non-`ComputedOnly`
   derived operand leaves (`Direct`/TTU arms under a boolean — `PDerivedTTU`/`PDerivedUserset`
   plan leaves; **the `Direct`-arm half of this is the §6.0 vacuity, not a coverage
   narrowing**; the derived-ROOT operator is NO LONGER a gap, widened 2026-07-17);
   declared wildcard-userset restrictions anywhere; stored object-wildcard tuples; stored
   userset-star tuples; **removes** (now CLOSED for a VALIDLY-STORED tuple from a drained
   prior state, 2026-07-19f — the `remove` constructor on `ReachedByW3d2`/`C`/`E` carries
   T2a/T2b under `t ∈ T` + `cascadeKeys = []` + the pre-remove store's disciplines, faithful
   to `TupleSource.remove`; BOTH Python remove paths were already answer-pinned via
   `test_conformance_remove.py`; the Exec driver / zcli graph mode now DRIVES removes
   end-to-end too (2026-07-19, `graphRunOps` / `test_conformance_remove_graph.py`), so
   remove-correctness is both proved AND driven end-to-end **over every in-fragment corpus
   except `direct_arm_exclusion`, excluded by `_REMOVE_EXCLUDED` because the guard
   fail-closes there** — and the guard's
   validly-stored scope decision was APPROVED by Avery 2026-07-19);
   star-subject queries with non-bare predicates;
   star-object queries on the graph side.

   *Empirical note.* The derived-ROOT gap was CLOSED 2026-07-17 — union- and
   computed-rooted derived defs are now in scope and in `GRAPH_FRAGMENT` (check + state).
   Only the object-wildcard corpus stays probe-confirmed-but-excluded: zero check-level
   divergence observed, and the exclusion is proof-scope (`bareStar`), not a known
   disagreement. **Caveat on that last inference (2026-07-26):** "proof-scope, not
   behavioral" is an inference from CHECK-level evidence, and it has already failed once
   in this repo — on 2026-07-17 a real model-vs-Python divergence turned up at STATE
   level in exactly that situation. The object-wildcard corpus has never been probed at
   state level; treat the sentence as a hypothesis. Separately, inside the `PDerivedTTU`
   gap a REAL check-level divergence WAS found (2026-07-12, by
   `tests/test_lookup_oracle.py`: the graph index answered False on userset-shaped
   subjects flowing through a stored tupleset parent of a derived TTU where the oracle and
   both set engines answer True) and FIXED 2026-07-13 Python-side (processor from-chain
   rule + `upos` lift; xfails flipped to regression pins, matrix grids widened) — the
   shape stays outside `W4Fragment` (`computedOnly` bans `ttu` leaves in derived defs), so
   the theorems and the `formal/` gates were and remain untouched; see `FINAL_REVIEW.md`
   §3's resolved note and `docs/spec-deviations.md` 2026-07-13.
4. **The state-gate projections** — state-level conformance IS implemented, but a
   divergence strictly inside a projected class (P6 leaf-family edge content, P3 edge
   multiplicity **on the derived arm only since 2026-07-29 — the untainted arm is now
   compared exactly and the derived arm is golden-pinned**, P2 bridge edges — inert — P5 node GC, under which **no `NodeV4` row is
   compared at all**, and **P7** `ResidueV1.version`, declared as a projection
   2026-07-27 after being dropped silently) would not fail it; each is pinned elsewhere
   and documented in `extractor.py`. Two artifacts sit outside the canonical form
   entirely: the `EdgeV4.derived` flag and the outbox rows/watermark (drained-ness is
   gated as a boolean, not row equality) — pinned only by Python-internal I5/I10 + the
   §8.3 verifier, never against Lean.

   **How thin the gate actually is (ZT-P4-5) — the quantification is GENERATED, not
   restated here.** The projection ledger — of the raw `EdgeV4` rows Python writes,
   how many each projection drops and how many survive to be compared against Lean,
   plus the `NodeV4` rows P5 drops wholesale — lives in `FINAL_REVIEW.md`'s generated
   counts block ("State-gate projection ledger", re-checked by `verify.sh` step 4e).
   Read it as the honest width of the state-level claim: only the `compared` row is
   ever checked against Lean, and a portion of the dropped nodes are not even
   endpoints/references of compared state, i.e. invisible to the gate entirely (that
   endpoint split is method-sensitive and deliberately NOT under the pin —
   `CORRESPONDENCE.md` §7.2). This paragraph carried its own copies of the ledger
   figures (measured 2026-07-27 over the 21 corpora then in the fragment) and they
   went stale through two corpus additions before the ledger became generated. One
   dated observation from that 2026-07-27 measurement is still worth keeping: only
   **5 of the 21** then-current corpora produced ANY residue row (11 rows),
   and all 11 had `|stars| == 1` and `|neg| == 1`. **P5 cannot be closed by comparing
   harder:** the Lean `GraphState` has a `nodes` field, but zcli's `"graph-state"` dump
   emits only edges and residues, the model never GCs while Python does (so set equality
   is false by design), and `NodeV4.implicit` / `reference_count` have no Lean
   counterpart — there is no node property to compare. What is gated instead is
   Python-side: `test_conformance_state.py::test_python_nodes_are_all_justified` (no
   orphan node rows; 0 measured). This is §6's "invisible to the gate by construction"
   concession, made precise. **P7's consequence is separate and sharper:** Lean's
   `Residue` has no version field, so invariant **I7 (residue-version monotonicity) is
   gated by nothing formal** — it is a modelling gap, and its only pins are `tests/`
   paranoia runs. The residue half was near-vacuous and is now partly closed by
   `corpus.py::SCHEMAS`'s `"residue_rich"` entry (multi-shape `stars`, multi-subject `neg`, a `upos`
   member), pinned non-vacuously; most corpora still contribute edges only.
5. **The representation layers, and the whole concurrency layer** — interner/bitmap
   (`setengine`), SQL rows / ref-counted closure storage (`index_v4`), `rebuild()` / crash
   recovery, and sessions/transactions/concurrency, which is **wider than the
   `_lock_store` protocol this item used to name alone**. Also out-of-model:
   `TupleSource._lock_source` (the `SchemaV4`-row lock) and the **writer lock ordering**
   between it and the graph store lock; **multi-instance / HA replica tailing** —
   `catch_up_evaluator` → `SetEngine.apply_logged`, i.e. instance-local set engines synced
   by tailing the permanent log — and the per-`Session` state that makes that safe; plus
   catch-up cadence and the `at_least` freshness plumbing. `CORRESPONDENCE.md` §7
   ("Multi-instance scheduling is OUT-OF-MODEL", 2026-07-23) argues why no Lean change was
   needed — a replica's state is the fold of a log PREFIX, every prefix is a valid store,
   so T1 applies pointwise — but that is a *reasoned* scope boundary, not a machine-checked
   one, and the lock discipline is precisely what makes "the log is one serial admitted-op
   sequence" true in the first place. There is no TLA+ phase; CI concurrency coverage is
   SQLite-shaped, where both locks render to no-ops.
6. **Bulk build / bulk backfill — a second, unmodeled constructor of index state, and it
   is the DEFAULT path.** `index_v4/bulk_build.py` (P13/N18) and
   `index_v4/bulk_backfill.py` (R4-BF) build the final index state **directly** — one
   in-memory closure pass + bulk INSERTs, T4's closed form evaluated in closed form —
   instead of replaying routed triples through the incremental
   `WildcardIndex.add_tuple` / `DeltaProcessor` path that the Lean `ReachedBy` chain
   models. `connectedstore.build_index` takes `bulk: bool = True`, so a real bootstrap
   takes this path; the modeled incremental path survives as `bulk=False`, kept as the
   reference side. **No Lean model describes the bulk constructor at all**; its entire net
   is a Python-vs-Python differential identity gate (`tests/test_bulk_build.py`, six
   corpora: the same snapshot built both ways must produce identical state, plus the
   I1–I13 checker and an oracle read-parity grid). Documented in `CORRESPONDENCE.md`
   §7/§8.1 — this list and `FINAL_REVIEW.md` §3 are simply the two honesty ledgers that
   stopped being updated, which is why the 2026-07-26 zero-trust review had to find it.
7. **Non-stratifiable schemas** (rejected upstream; the model assumes stratifiability). The
   `expand` / `lookup` / `lookup_reverse` (list-objects / list-users) read surfaces are
   **not yet modeled in Lean** — a deferred low-priority TODO (`FINAL_REVIEW.md` §4, last
   item), not a permanent exclusion; both backends' surfaces are pinned empirically by
   `tests/test_lookup_oracle.py` and, since 2026-07-13, the hypothesis campaign.
8. **The toolchain trust base** — the Lean 4 kernel + pinned Mathlib, and the conformance
   harness's own encoder (`encode.py` reuses the independent oracle's parser precisely so
   one parser bug cannot corrupt both sides).

**Where the next marginal assurance is** (`FINAL_REVIEW.md` §4; state-level + enumeration
+ the remove-path and generated-schema answer gates are DONE): (c) widening `W4Fragment`
— **union roots are DONE (2026-07-17: `rootB`/`RootBoolean` deleted, the derived-def ROOT
operator is unrestricted)**, and the **`Direct`-arm half of the LEAF fragment is DONE
2026-08-05** — the E-chain arc carried it onto the FINAL unsuffixed theorems (leg 2
`enumJob2 → enumJob2D`; legs 3–4 the `_d` projection; **leg 5 the bundle rebase**; leg 6
the conformance reclassification), so those theorems are no longer vacuous on the
commonest boolean schema in the language (§6.0). What remains under (c), and these are
now the highest-value items: **T2a alone did not widen** (`graph_reached_inv` carries an
extra `W4NarrowT2a` bundle the Direct-arm store provably fails — a DESIGN DECISION is
owed, not proof effort), the TTU/userset leaf arms (`PDerivedTTU`/`PDerivedUserset`,
still `False` under `ComputedOrDirect`), **> 2 strata**, and the Lean REMOVE guard, which
still decides plain `storeValidRulesB`; (d) remove legs on the Lean side — **DONE 2026-07-19f** at the
validly-stored + drained-prior scope: the `remove` constructor on `ReachedByW3d2`/`C`/`E`
makes T2a/T2b + `Exec.graphRun_check_eq_sem` cover retraction of a `t ∈ T` from a drained
state under the pre-remove store's disciplines (faithful to `TupleSource.remove`), so the
Lean model IS now a post-remove reference at that scope; the Exec driver DRIVES removes
end-to-end too (2026-07-19, `graphRunOps` / `test_conformance_remove_graph.py`, minus the
`direct_arm_exclusion` exclusion); the guard's
validly-stored scope decision was APPROVED by Avery 2026-07-19; (e) widening the
state/enumeration bounds — **partly DONE**: six shapes now (a userset/wildcard shape and a
TTU shape added), K = 4 on four of them, and a state-level leg over a stride-4 sample
(`test_conformance_enum_state.py`, 257 of 1021 stores); what remains is the graph backend
in the ANSWER enumeration, K = 4 on the two capped shapes, and state coverage beyond the
25 % sample. Item
(f) — fixing the derived-TTU userset-subject divergence and flipping its strict xfails —
is **DONE** (2026-07-13, Python-side; `FINAL_REVIEW.md` §3's resolved note). Added
2026-07-26: **(h)** model or explicitly scope-exclude the bulk build/backfill constructor
(item 6), and **(i)** the concurrency / multi-instance layer (item 5 — the deferred TLA+
phase, never started).

---

## 7. Map of the `formal/` tree

```
formal/
  ARCHITECTURE.md    -- this file: the durable topical map
  SEMANTICS.md       -- the trust root: sem, WF, both models, theorem hypotheses
  CORRESPONDENCE.md  -- Lean def <-> Python file:line map (the audit backbone)
  FINAL_REVIEW.md    -- the authoritative, clause-checked claim (governs)
  HANDOFF.md         -- execution-state entry point + house rules + build/verify
                        (ranks nothing; the repo board ../HANDOFF.md does)
  README.md          -- one-page orientation
  REFERENCES.md      -- external references
  verify.sh          -- the one-command fail-closed green gate
  history/           -- provenance archive (ledger, staged designs, early digest)
                        PROOF_STATUS.md · ROADMAP.md · REVIEW.md · README.md
  lean/ZanzibarProofs/
    Core/            -- domain: Ident, Refs, Schema, Store
    Spec/            -- sem + well-definedness: Semantics, Stratify, WellDef (T0),
                        Confine, Stabilize, FuelStable, Counterexample
    SetEngine/       -- the set-engine model + T1: MemberSet, Algebra, Eval, Correct
    GraphIndex/      -- the operational graph model + T2/T4/T5: State, Closure (T4),
                        Cascade/CascadeStrata* (T5 + the two-round scheduler),
                        Reconcile*/Rules* (the staged write/read layers),
                        Exec (the conformance driver honesty theorems)
    FullScope.lean   -- the final unsuffixed T2a/T2b/T3/T6 over ReachedBy; the
                        GraphAdmission / W4Fragment split; non-vacuity witnesses
    Equiv.lean       -- T3/T6 corollaries (incl. T6c wildcard_scoping)
    Audit.lean       -- the #print-axioms audit surface
    Cli.lean         -- the zcli JSON conformance endpoint (modes: spec/graph/graph-state)
  conformance/       -- the pytest harness: encode, grid, corpus, backends, extractor,
                        runner, sorry_scan, and the test_conformance_*/test_cli_mode suites
```

---

## 8. The attack-first method

The effort ran under a hard, owner-adjudicated **honesty norm**: never fake a proof,
never postulate the thing being proved (no `check := sem` models, no
invariant-as-postcondition), never edit a golden/oracle/snapshot to make something pass,
and never round scope up. Where a doc and the code disagree on a name, the code wins.

Its central discipline was **attack-first**: before proving any new theorem *statement*,
try to REFUTE it with concrete `#eval` scenarios against the real `check`/`sem`. Six
false statements were killed this way during the original W1→W4 arc, before any proof
effort was spent on them *(historical staging — the stage names are explained in
`history/`)*. **Six is an under-count of the method's yield, kept here only because these
six are the ones narrated below**: at least seven further kills are recorded in
`history/PROOF_STATUS.md` during the 2026-07-18…20 remove and Direct-arm legs, including
`graph_correct_w3a_d`, the chain-level `removeLoggedRules`-as-fold identity, the
filter-all `removeEdgePair` shape, the derived-arm `count ∈ {0,1}` invariant, the naive
`reachedByW3d2_shadow_d`, the paired `reachedByW3d2C_settled_d`/`graph_correct_w3d2_d`
(the `affectedKeys` model gap, §6.1 item 1), and the first proposed fix for that gap.

1. **additive `fuelBound`** — the recursion depth is bounded by the `(entity × relation)`
   state space, a **product**, not a sum. The additive bound `|keys| + 2|T| + 4` cut deep
   TTU-linked chains off early, so `sem` returned **false** where the oracle returns
   **true** (depth ~64 at a shallow-looking schema). Fixed to the multiplicative
   `|keys| · (2|T| + 4)` — the load-bearing sizing rationale, and the original reason the
   "validate before proving" phase exists.
2. **abstract write-step closure** — the abstract reached-state closure admitted junk
   states; the graph theorems were re-proved over the concrete operational chain instead.
3. **T0a without `StoreDeclared`** — an admission-invalid tupleset tuple closes a
   consultation cycle stratification never sees, and `semAux` oscillates; T0a is false
   without the declared-store precondition (`Spec/Counterexample.lean`).
4. **the naive-W2 TTU fragment** — the first TTU fragment shape was refuted before proving.
5. **the W3a single-edge collapse without `NoRuleOutputs`** — the collapse fails unless
   the derived key emits no rule outputs.
6. **W3d-2 "round-1 keys are stratum-1"** — false: a write to a direct untainted leaf of a
   stratum-2 def dirties it at the watermark, where the leg-start enumeration misses a
   fresh grant living only in the dirty operand's future residue. The two-round coverage
   was made conditional on the job's operand baseline and discharged from state instead.

A session that killed a false statement was a good session. Each kill is recorded in the
`history/PROOF_STATUS.md` ledger, and none of the six was quietly reconciled.

**Honesty note on the sentence that used to end this file** — "no adjudication event
(spec vs oracle vs backend disagreement) remains open": that is an assertion over a
ledger that has since grown by an order of magnitude, and NOTHING in `verify.sh` checks
it. It is re-verified only by reading `history/PROOF_STATUS.md` end to end. As of the
2026-07-26 zero-trust review no open adjudication event was found there — but that review
also found findings that live ONLY in `history/` and never reached any board (the
`w3cJobValid_enumJob2D` star-freeness hole, an open attack surface naming a
Python-ADMITTED schema shape; `PDerivedUserset` fixed Python-side 2026-07-13/17 and never
modeled in Lean; the `reconcile_subject` cheap path, unmodeled and since grown real
logic). Read the claim as "none found on the last read", not as an invariant.

**Update (2026-07-26) — the `reconcile_subject` gap grew again.** The `ZT-P0-1` fix
(withdrawing the unsound N3 `_keys_referencing` elision) added a THIRD piece of real
logic to that already-recorded unmodeled cheap path: `_reconcile_subject`'s userset
branch now **escalates to the full-object `_reconcile`** when the subject node has
disappeared mid-round (`s_node is None`), instead of silently no-oping — the
proximate leak in the reproduced authorization escalation. Together with the
2026-07-17 Fix B promote-on-record rule, the "cheap path" now carries a
state-functional node-flag rule and a control-flow escalation, neither of which any
Lean constructor describes (the chain models only the full-object reconcile). This
does not widen the gap's *disposition* — it was already an unmodeled surface — but it
does mean the gap is no longer plausibly characterizable as "a thin fast path".
Recorded in `CORRESPONDENCE.md` §7.1 (cheap-path entry) and §8.1 (`ZT-P0-1`);
regression pin `tests/test_reg14_residue_gc_elision.py`.
