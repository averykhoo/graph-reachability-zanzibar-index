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
  `rewriteClosureAux_restrict`).
- **Step A, the fuel bridge — CLOSED (`RestrictBase.lean`, 2026-07-11):**
  **`rewriteClosure_restrict_mem_iff`** — `rewriteClosure S t` (fuel `|S.keys|+1`) and
  `rewriteClosure (S↾U) t` (smaller fuel `|S↾U.keys|+1`) have identical membership. `⊇` is
  unconditional fuel monotonicity (`rewriteClosureAux_mono` via the `stepN` layer algebra +
  `restrictUntainted_keys_length_le`); `⊆` is saturation of the `S↾U`-closure, whose
  `RewriteRanked (S↾U)` is built from `RewriteRanked S` by rank compression
  (`rewriteRanked_restrict`), given the faithful side condition **`RewriteMatchDeclared`**
  (every rewrite's match key is a declared untainted relation).
- **Step A — CLOSED (`RestrictBase.lean`, 2026-07-11): state transfer + base `hag` equation.**
  **`foldAdmits_of_acyclic`** — a `writeDirect` fold admits every write when each materialised
  edge lands in an acyclic target relation containing the running edges (order-insensitive: only
  the *set* of materialised edges matters). **`exists_admitted_restrict`** — from an admitted
  rule-routed state over mixed `S`, build a canonical `ReachedByRulesAdmitted σ' (S↾U) T` with
  identical edge membership (both edge sets are the materialised closures, equal by the fuel
  bridge; admissions transfer via acyclicity of the shared target `σ0.edges` — closes the flagged
  "different fold lists" subtlety). **`graphRec_base_eq`** (the deliverable) — on an admitted base
  over mixed `S`, `graphRec σ0 s dt on r' = sem S T ⟨s,r',⟨dt,on⟩⟩` for untainted `r'`, via
  `graphRec σ0 = probeNonDerived σ0 = probeNonDerived σ' = check σ' = sem (S↾U) T q' = sem S T q'`
  (edge agreement · `graph_correct_rules` over `S↾U` · `semAux_restrict` + fuel stability). The W2
  restriction hyps transfer to `S↾U`; `RootBoolean`-derived defs force stored relations untainted.
  **Fragment premise `hRootB` (every derived def `RootBoolean`) supersedes the old `hDrop`.** The
  base is `…Admitted`; Step B supplies the admitted W3a closure to feed it.

**W3a fragment (assembled so far):** derived defs are `ComputedOnly` ∧ `RootBoolean`,
operands untainted, `hterm` (every derived R: `NoTtuTarget S R ∧ NoStoreSubjectR T R`),
plus the W2 fragment on the untainted part (`WF ∧ NodupKeys ∧ RewriteRanked ∧
TtuTuplesetsDirect ∧ StoreValidRules ∧ StarFreeStore`) and the new constructor
star-freeness (`hcands` bare, `hcStar`/`honStar` star-free).

---

## The next task — finish W3a (`graph_correct_w3a`): Step B, then Step C

**Step A is CLOSED** (all of `GraphIndex/RestrictBase.lean`, 2026-07-11): the `hag` base
correspondence is proved end-to-end as **`graphRec_base_eq`** — on an admitted rule-routed state
over the MIXED schema `S`, the operand read equals `sem S T` for every untainted operand. See the
"State of the world" bullets above for the shape (schema restriction · `semAux_restrict` · fuel
bridge · state transfer · the composed equation). The reusable Step A fact requires an **admitted**
base (`ReachedByRulesAdmitted`), which is exactly what Step B's admitted W3a closure will supply.

**Immediately usable in Step B:** `graphRec_base_eq` (base `hag`), `graphRec_reduce_base`
(`ReconcileCorrect.lean` — reduces the full W3a state's operand read to the base read; NB it
currently yields a `ReachedByRules` base, so its `hag` half still needs the admitted upgrade — the
cleanest path is to re-cut `graphRec_reduce_base` to hand back a `ReachedByRulesAdmitted` base, or
prove the reduction preserves admission). Both consume the `hRootB` fragment premise (every derived
def `RootBoolean`) and `RewriteMatchDeclared`.

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
