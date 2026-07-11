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
| T3/T6 `backend_equivalence*` / `exclusion_effective*` / `no_ghost_grant*` | `Equiv.lean` | per-fragment corollaries (incl. `_w3a`) |

**Staged T2 widening: W1 ✅ → W2 ✅ → W3a ✅ → W3b (next) → W3c → W3d → W4.**
**W3a is CLOSED (2026-07-11):** star-free bare-subject derived booleans — `and`/`but not`
over `computed` refs to untainted operands; the processor stores NO residue row, so a
derived relation only adds edges, and the derived read collapses to a bare edge probe.
The whole read correspondence `graph_correct_w3a` (`GraphIndex/ReconcileComplete.lean`) is
proved: `check = sem` on every **bare-subject** star-free query, with the T3/T6a/T6b
corollaries (`*_w3a` in `Equiv.lean`). Scope note (attack-first, recorded): a **userset**
subject on a derived key can be `sem`-true while the residue-empty read is `false`, so
W3a's derived-query claim is bare-subject-only — usersets are W3b's `upos` residue.

W3a machinery, in dependency order (`Reconcile.lean`, `ReconcileWrite.lean`,
`ReconcileCorrect.lean`, `RestrictBase.lean`, **`ReconcileComplete.lean`**):
- read collapse (`check_derived_ResidueEmpty`: derived read = bare edge probe);
- write model (`checkFn` = compiled check_fn as `evalE` via `graphRec` = `probeNonDerived`;
  `reconcileKey` guarded `writeDirect` fold; closures `ReachedByW3a` / `ReachedByW3aAdmitted`);
- `checkFn_eq_semStep` → **`checkFn_eq_sem`** (checkFn on a W3a-admitted state = `sem` of the
  derived key), via `graphRec_reduce_base_adm` + Step A's `graphRec_base_eq` + `semAux_qirrel`
  (`sem` is query-independent) + fuel stability;
- **soundness** `reachedByW3aAdmitted_derived_edge_sound` (a materialised derived edge ⇒ `sem`;
  reach-collapse `reachedByW3a_reach_collapse_root` + edge-provenance `reconcileKey_edge_guard`);
- **completeness** `w3aComplete_derived_edge` (`sem` ⇒ edge; `W3aComplete` = admitted base + a
  coverage-complete batch of reconcile jobs, `reconcileKey_edge_present` writes+persists);
- assembly `graph_correct_w3a`; Step C corollaries `*_w3a`.

Step A detail (schema restriction `S↾U`, `semAux_restrict`, the fuel bridge, the state transfer,
`graphRec_base_eq`) is in `RestrictBase.lean` and the PROOF_STATUS ledger (2026-07-11 entries).

**W3a fragment hypotheses** (all faithful, carried by `graph_correct_w3a`): derived defs are
`ComputedOnly` ∧ `RootBoolean` with untainted `computed` leaves (`hCO`/`hLU`); `hterm` (every
derived R: `NoTtuTarget S R ∧ NoStoreSubjectR T R`); `hRootB`, `RewriteMatchDeclared`, `Stratifiable`;
the W2 fragment on the untainted part (`WF ∧ NodupKeys ∧ RewriteRanked ∧ TtuTuplesetsDirect ∧
StoreValidRules ∧ StarFreeStore`); the closure `W3aComplete` (admitted base + coverage-complete
reconcile jobs); and bare-subject star-free queries.

---

## The next task — W3b (userset subjects on derived keys → `upos` residue)

**W3a is CLOSED.** Start W3b: the first residue **content** — userset subjects on a derived key. This
is exactly the scope gap the W3a attack-first found: `sem ⟨us, R, o⟩` can be true for a userset `us`
(e.g. a userset granted `member` under `viewer := member but not banned`), but the residue-empty read
returns `false`. W3b makes the read's `upos` branch (`probeDerived`, `State.lean:562-565`) go live so
usersets are answered.

1. **Attack-first the read + write semantics FIRST** (house rule 2). `#eval` the Python/`sem`
   behaviour of userset subjects on derived keys against the graph's `probeDerived` `upos` path;
   read `wildcard.py:398-432`, `_store_residue` (userset branch), boolean spec §7.6, and I6
   hygiene (`uposEdgeFree` / `uposNegDisjoint` in `Inv`). Record any false statement killed.
2. **Model `_store_residue` for usersets.** The processor stores a `upos` entry `⟨t,n,p⟩` at the
   derived key when a userset is a member (edge-free — the P4 rule). The W3a closure currently keeps
   `ResidueEmpty`; W3b relaxes that to a residue carrying `upos` (still `stars = neg = ∅`), so
   `reachedByW3a*_inv`'s residue-free conjunct and `check_derived_ResidueEmpty` must be generalised
   to a `upos`-only residue (new read-collapse lemma reading the `upos` branch).
3. **Correspondence.** `checkFn` already evaluates the boolean for ANY subject (not just bare); the
   new work is that a userset's membership lands in `upos` (not an edge) and the read consults `upos`.
   Reuse `checkFn_eq_sem` (it is subject-generic — the `graphRec_base_eq` operand read holds for any
   `s`, so only the bare-vs-userset MATERIALISATION differs). Widen `W3aComplete`'s coverage +
   `w3aComplete_derived_edge` analog to `upos` membership.

**Immediately reusable from W3a** (`ReconcileComplete.lean`): `checkFn_eq_sem` (subject-generic),
`graphRec_base_eq` / `graphRec_reduce_base_adm`, `reconcileKey_edge_guard` /
`reconcileKey_edge_present` (adapt to `upos` writes), the `W3aJob`/`reconcileJobs`/`W3aComplete`
scaffolding, `semAux_qirrel`, `isDerived_declared`.

---

## After W3b (the remaining road)
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
