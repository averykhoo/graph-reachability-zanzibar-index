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
| T3/T6 `backend_equivalence*` / `exclusion_effective*` / `no_ghost_grant*` | `Equiv.lean` | per-fragment corollaries |

**Staged T2 widening: W1 ✅ → W2 ✅ → W3 (in flight) → W4.** Current stage: **W3a**
(star-free bare-subject derived booleans — `and`/`but not` over `computed` refs to
untainted operands; the processor stores NO residue row here, so a derived relation
only adds edges). Done so far in W3a (`Reconcile.lean`, `ReconcileWrite.lean`,
`ReconcileCorrect.lean`):
- read collapse (`check_derived_ResidueEmpty`: derived read = bare edge probe);
- write model (`checkFn` = compiled check_fn as `evalE` reading the graph via
  `graphRec` = `probeNonDerived`; `reconcileKey` guarded `writeDirect` fold; closure
  `ReachedByW3a` with `Inv`/residue-free/quiescence preserved);
- `checkFn_eq_semStep` (checkFn = one `sem` step, given per-relation agreement `hag`
  at the def's `computed` leaves — `computedRefs`-restricted, so the assembly never
  needs agreement at the derived key itself);
- reach-collapse (`reachedByW3a_reach_collapse_root`: a path to the derived R-node is
  a SINGLE reconcile edge, on `RootBoolean` defs — `inter`/`excl`-rooted, giving
  `NoRuleOutputs`);
- R-terminality (`NoTtuTarget`/`NoStoreSubjectR` ⇒ R-node never an edge source) and
  reconcile-edge inertness folded to the untainted base
  (`reachedByW3a_reach_inert_iff`);
- **`graphRec_reduce_base`**: the operand read on the full W3a state equals the read
  on an untainted `ReachedByRules` base σ0, for every untainted operand relation.
- **Step A, the `hag` base reduction (`RestrictBase.lean`, 2026-07-11):** schema
  restriction `S↾U := restrictUntainted S` (drop tainted defs) is untainted
  (`untaintedSchema_restrict`); `restrictUntainted_lookup` (schemas agree at untainted
  keys); **`semAux_restrict`** — `sem` over `S` and `S↾U` coincide at every untainted key
  (the semantic heart: untaintedness is hereditary, so an untainted read never touches a
  dropped def); and the rewrite fan-out is preserved (`schemaRewrites_restrict`,
  `rewriteClosureAux_restrict`) — the state-transfer groundwork. **Remaining: the fuel
  bridge + admitted state transfer + fuel-bridged assembly (see "The next task").**

**W3a fragment (assembled so far):** derived defs are `ComputedOnly` ∧ `RootBoolean`,
operands untainted, `hterm` (every derived R: `NoTtuTarget S R ∧ NoStoreSubjectR T R`),
plus the W2 fragment on the untainted part (`WF ∧ NodupKeys ∧ RewriteRanked ∧
TtuTuplesetsDirect ∧ StoreValidRules ∧ StarFreeStore`) and the new constructor
star-freeness (`hcands` bare, `hcStar`/`honStar` star-free).

---

## The next task — finish W3a (`graph_correct_w3a`), in three steps

### Step A — discharge `hag` on the base (schema-restriction route; ~half done)

Needed: for a `ReachedByRules σ0 S T` state over the MIXED schema `S` and an untainted
operand `r'` (`isDerived S (dt, r') = false`),
`graphRec σ0 s dt on r' = semAux S s T q f dt on r'`. `graph_correct_rules` proves this
under WHOLE-schema `UntaintedSchema` — too strong for W3's mixed schema — so restrict `S`
to `S↾U := restrictUntainted S` (drop tainted defs) and reuse W2 as a black box.

**DONE (`GraphIndex/RestrictBase.lean`, 2026-07-11):** the restriction + its facts.
`untaintedSchema_restrict` (`S↾U` untainted, under `NodupKeys`); `restrictUntainted_lookup`
(schemas agree at untainted keys); **`semAux_restrict`** (the semantic heart: `sem` over `S`
and `S↾U` coincide at every untainted key — heredity via `evalE_congr` + `untainted_closed`);
and the rewrite-fan-out preservation `schemaRewrites_restrict` / `rewriteStep_restrict` /
`rewriteClosureAux_restrict` (the closure at any FIXED fuel is unchanged), given the fragment
fact `hDrop` (every tainted def emits no arms — `RootBoolean` ⇒ `exprArms_rootBoolean`).

**REMAINING — the fuel bridge, state transfer, and assembly:**
1. **Fuel bridge (the crux).** The canonical closures run at DIFFERENT fuels: `rewriteClosure
   S t` at `|S.keys|+1`, `rewriteClosure (S↾U) t` at the smaller `|S↾U.keys|+1`. Via
   `rewriteClosureAux_restrict`, `rewriteClosure (S↾U) t = rewriteClosureAux S (|S↾U.keys|+1)
   [t]`, so prove **membership equality of the two S-closures across the gap**. Both saturate:
   `rewriteClosure_saturated` (RewriteRanked S) for the big side; the small side needs a rewrite
   chain from a stored (⇒ untainted: `exprDirects_rootBoolean` + `StoreValidRules`) seed to STAY
   untainted (an arm's `outRel` is its def's relation; tainted defs emit no arms ⇒ no rule
   outputs a tainted relation) ⇒ depth ≤ `|S↾U.keys|`. Either build `RewriteRanked (S↾U)` (rank
   compressed to `S↾U`'s key count) or a direct "untainted cone saturates at `|S↾U.keys|+1`".
2. **State transfer.** On the *admitted* path (`FoldAdmits` ⇒ no cycle rejection), edges are
   EXACTLY `reachedByRules_edge_sound` (⊆) + `reachedByRulesAdmitted_edge_complete` (⊇). With (1),
   build `ReachedByRulesAdmitted σ' (S↾U) T` and show `σ'.edges ≈ σ0.edges` (membership); `reach`
   depends only on edge membership (`reach_iff_nreaches` + `edgesClosed`).
3. **Base `hag` equation.** `graphRec σ0 = probeNonDerived σ0` (`probeNonDerived_plainEdges`)
   `= check σ'` (edges agree, `S↾U` routes to the probe) `= sem (S↾U) T q'`
   (`graph_correct_rules`) `= sem S T q'` (`semAux_restrict` + untainted-schema fuel stability to
   bridge `fuelBound (S↾U)` vs `fuelBound S`). Compose with `graphRec_reduce_base`. The W3a base
   is currently `ReachedByRules` not `…Admitted`; the completeness half needs Step B's admitted
   W3a closure, so Step A can land the equation over an *admitted* base as the reusable fact.

Fallback route (if the fuel bridge fights): re-thread `RulesSound`/`RulesChain`/`RulesComplete`
per-relation, replacing `UntaintedSchema S` by untaintedness of the keys actually consulted.
More churn; only if (1)–(3) stall.

### Step B — candidate completeness + assembly `graph_correct_w3a` (~1 session)

1. **Edge provenance with the guard:** strengthen the reconcile edge story — every
   derived R-node in-edge `subjNode c → objNode ⟨dt,on⟩ R` was written by some fold
   step whose mid-state `checkFn` was TRUE for `c` (new lemma peeling `reconcileKey`;
   note a mid-fold state IS a `ReachedByW3a` state — a pass with a prefix of `cands`).
2. **Admitted closure `ReachedByW3aAdmitted`** (analog of `ReachedByRulesAdmitted`):
   models the processor's candidate enumeration `_leaf_concretes` — for every derived
   key and every bare subject `s` with `sem S T ⟨s,R,o⟩ = true`, some reconcile pass
   enumerated `s` in `cands` (then `checkFn` = `sem` = true ⇒ its edge is present;
   edges persist by `reconcileKey_edges_mono`).
3. **Assembly, derived query:** route → `probeDerived` → `check_derived_ResidueEmpty`
   (residue provably empty) → edge probe → forward: reach ⇒ single edge
   (`reachedByW3a_reach_collapse_root`) ⇒ provenance (1) ⇒ `checkFn` at that sub-state
   ⇒ `checkFn_eq_semStep` + `hag` (Step A via `graphRec_reduce_base`, whose `computedRefs`
   restriction needs the fragment fact "every computed leaf of a derived def is
   untainted") ⇒ `sem`. Backward: `sem` ⇒ admitted enumeration (2) ⇒ `checkFn` true ⇒
   edge ⇒ reach. **Untainted query:** reduce to the base read (`graphRec_reduce_base`
   at query endpoints) + Step A's base fact.
4. Fuel bookkeeping: everything through `sem_fuel_stable` (mixed schema IS
   stratifiable — check/prove `stratifiable` for the W3a fragment; cf.
   `stratifiable_untainted`).

### Step C — widen T3/T6 (~1 hour)

`backend_equivalence_w3a` / `exclusion_effective_w3a` / `no_ghost_grant_w3a` in
`Equiv.lean`, mirroring the `_rules` versions (T1 ∘ `graph_correct_w3a`). T6a gets its
first REAL exclusion content (a derived `but not` actually excluding). Add audit
entries; update docs; this closes W3a — tick it in ROADMAP.

---

## After W3a (the remaining road)

- **W3b — userset subjects on derived keys (`upos`).** First residue CONTENT: the
  read's `upos` branch goes live. Model `_store_residue` for usersets; I6 hygiene.
  Attack-first the read semantics (wildcard.py:398-432, boolean spec §7.6).
- **W3c — star data on derived keys (`stars`/`neg`).** The `stars ∖ neg` fallback
  branch + `negEdgeFree` disjointness (I6) becomes contentful. The T1 `MemberSet`
  algebra is the reference for residue semantics.
- **W3d — multi-stratum cascade.** The outbox/watermark loop (`run_cascade`), cross-key
  re-reconcile hazard (an edge write re-reaching an existing residue key), contentful
  T5 (non-empty outbox drained). `processor.py` is the model source.
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
