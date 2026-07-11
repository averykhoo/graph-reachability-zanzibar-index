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
| T3/T6 `backend_equivalence*` / `exclusion_effective*` / `no_ghost_grant*` | `Equiv.lean` | per-fragment corollaries (incl. `_w3a`, `_w3b`) |

**Staged T2 widening: W1 ✅ → W2 ✅ → W3a ✅ → W3b ✅ → W3c (next) → W3d → W4.**
**W3b is CLOSED (2026-07-11):** userset subjects on derived keys, answered by the edge-free
`upos` residue (blind-audit P4). `graph_correct_w3b` (`GraphIndex/ReconcileUposComplete.lean`):
`check = sem` on EVERY star-free query — bare AND userset subjects — over a `W3bComplete`
state; T3/T6 corollaries `*_w3b` in `Equiv.lean` (T6a now covers a userset excluded by a
derived `but not`). The W3a summary (`graph_correct_w3a`, `checkFn_eq_sem`, Step A restriction
machinery) is in the 2026-07-11 PROOF_STATUS entries; fragment hypotheses are unchanged from
W3a (hCO/hLU/hterm/hRootB/hMatch/hStrat + the W2 pack) — only the query scope widened.

W3b machinery (`ReconcileUpos.lean` = write half, `ReconcileUposComplete.lean` = closure+assembly):
- **write model** `reconcileUposStep`/`reconcileUposKey` — per-candidate insert/remove fold on the
  key's `upos` list via `putResidue` (faithful to `reconcile_subject`'s userset branch,
  `processor.py:345-357`; star-free ⇒ `covered = false` ⇒ `want_upos = should`, `want_neg = false`);
- **congruence spine**: `reach`/`probeNonDerived`/`graphRec`/`checkFn_congr` — `checkFn` reads only
  the edge/node core, so it is CONSTANT across the upos fold; whole-fold membership
  characterization `reconcileUposKey_upos_mem` (x ∈ upos-after ⟺ candidate ∧ pass-start guard,
  or non-candidate ∧ already-present);
- **read collapse** `probeDerived_uposOnly`/`check_derived_uposOnly` on `ResidueUposOnly` states
  (star ⇒ false, userset ⇒ `upos.contains`, bare ⇒ the W3a edge probe);
- **`ReachedByW3b`** (admitted base + interleaved `reconcileKey`/`reconcileUposKey` legs) and the
  **SHADOW PROJECTION** `reachedByW3b_shadow`: every W3b state has a W3a-admitted shadow with an
  identical core (`CoreEq`, replay minus upos passes) — ALL W3a edge/reach facts (collapse,
  terminality, edge soundness, `checkFn_eq_sem`) transfer with zero new induction;
- **T2a** `reachedByW3b_inv`: full `Inv` with **contentful I6** — `uposEdgeFree` proved for real
  (a upos member is userset-shaped; every path onto the `RootBoolean` R-node is a single
  bare-sourced edge), `neg` clauses by emptiness; + residue provenance;
- **correspondence**: `checkFn_eq_sem_w3b` (subject-generic, via the shadow); `upos` soundness
  `reachedByW3b_upos_sound`; `upos` persistence `reconcileJobsB_upos_persist` (a same-key
  re-reconcile re-evaluates the fold-constant guard = `sem` = true, so it keeps the entry);
  `W3bComplete` (edge jobs cover `sem`-true bare subjects, upos jobs cover `sem`-true usersets);
  `w3bComplete_derived_edge` / `w3bComplete_derived_upos`; assembly `graph_correct_w3b`.

Attack-first (2026-07-11, recorded in `ReconcileUpos.lean` header): planned model vs `sem` on a
180-query grid over `viewer := member but not banned` with userset grants (direct + via computed
union operand + banned + ghost + the derived key itself as a subject) — no refutation; pass order
irrelevant, idempotent, P4 non-leak holds, upos members never reach the R-node (I6 confirmed).

---

## The next task — W3c (star data on derived keys → `stars` / `neg`)

**W3b is CLOSED.** Start W3c: the star-coverage residue content. On the derived key the processor
persists `stars` (the star×boolean fold `plan.stars_fn`, `processor.py:388-389` — which shapes are
wholesale-covered by wildcard grants through the boolean) and `neg` (star-covered ∧ expr-false
concrete subjects, `processor.py:391-411`), and the reads' fallback branches go live: bare subject
⇒ edge probe **∨ (shape ∈ stars ∧ ∉ neg)**; star subject ⇒ `shape ∈ stars`; userset `upos` branch
gains its `stars`/`neg` fallback. Edge maintenance changes too: `want_edge = should ∧ ¬covered`
(`processor.py:359`) — a covered subject holds NO edge, so the store is no longer star-free.

1. **Attack-first** (house rule 2): `#eval` the star×boolean fold vs `sem` — the key subtleties are
   (a) `stars_fn`'s boolean over shape coverage (an `and` of a starred and an unstarred operand is
   NOT covered; `but not` with a starred subtrahend kills coverage), (b) concrete-only exclusion
   does not defeat `*` (spec §5.4 — that is what `neg` is for), (c) `want_edge = should ∧ ¬covered`
   drops edges that W3b would have written. Try to refute the planned read equation
   `members = edges ∪ upos ∪ (⋃_{σ∈stars} pop(σ) ∖ neg)` against `sem` with wildcard grants on
   operands. The T1 `MemberSet` algebra (`SetEngine/MemberSet.lean`) is the residue-semantics
   reference; `boolean spec §5.3-5.4`, `wildcard.py:398-432`.
2. **Relax `StarFreeStore`.** The W2 base machinery is proved under `StarFreeStore T`; star grants
   on operand relations materialise as wildcard-bridge edges (W1's machinery). Expect this to be
   the expensive half: the shadow projection survives (upos/stars writes are still edge-inert),
   but the base leg needs W1+W2 composition (`ObjStar`/`UsStar` closures + rule routing).
   Consider sub-staging: W3c-i = stars on the DERIVED key only (operand stores still star-free —
   `stars_fn` folds over object-wildcard shapes declared for the derived type); W3c-ii = star
   grants inside operand cones.
3. **Model + correspondence.** Extend the residue write model with `stars`/`neg` maintenance
   (wholesale recompute per pass, `processor.py:388-411`); relax `ResidueUposOnly`; new read
   collapse; extend `W3bComplete` coverage to `neg` candidates (negative-leaf concretes ∪ derived
   `neg` propagation) and star coverage; `negEdgeFree`/`negStarCovered` (I6) become contentful.

**Immediately reusable from W3b**: the congruence spine + shadow projection pattern
(`ReconcileUposComplete.lean` — stars/neg writes are `putResidue`-only, so `CoreEq` and
`checkFn`-constancy carry over verbatim), `reconcileUposKey_upos_mem`-style characterizations,
`checkFn_eq_sem_w3b`, the `W3bJob` batch scaffolding, `uposAt_of_residue`/`residue_of_uposAt_mem`.

---

## After W3c (the remaining road)
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
