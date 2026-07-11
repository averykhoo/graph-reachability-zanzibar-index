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
| T3/T6 `backend_equivalence*` / `exclusion_effective*` / `no_ghost_grant*` | `Equiv.lean` | per-fragment corollaries (incl. `_w3a`, `_w3b`) |

**Staged T2 widening: W1 ✅ → W2 ✅ → W3a ✅ → W3b ✅ → W3c ◐ (write half ✅, read-half step 1 [star-relaxed base equation] ✅, batch layer + assembly NEXT) → W3d → W4.**
**W3c write half is CLOSED (2026-07-11)** — `GraphIndex/ReconcileStars.lean`: the `stars`/`neg`
residue model and **T2a with ALL FOUR I6 clauses contentful**, with **no `StarFreeStore`
hypothesis anywhere in the file**. Machinery:
- **write model**: `wildcardShapes` (schema-fixed `subject_wildcard_shapes`), `coveredFn` (the
  star-subject `checkFn` — the compiled star fold `plan.stars_fn` is POINTWISE the boolean
  evaluation on the star subject: `∪/∩/−` over leaf star sets = `∨/∧/∧¬` over membership, a
  closure leaf's star set being the graph's star-subject read), `reconcileResidueKey` (wholesale
  stars/neg/upos recompute, one `putResidue`; `neg` = covered ∧ expr-false, `upos` = ¬covered ∧
  expr-true), `reconcileKeyC` (edge fold with `want_edge = should ∧ ¬covered`,
  `processor.py:359`), `reconcileStarsKey` = residue-THEN-edges (the faithful atomic unit —
  `reconcile` stores the residue at `:446` before the edge audit `:450-455`; order load-bearing);
- **covered-filter collapse** `reconcileKeyC_eq_filter`: the covered guard is fold-constant, so
  the W3c edge fold IS a W3a `reconcileKey` on the covered-filtered candidates — all W3a fold
  machinery transfers with zero new induction;
- **shadow projection** `reachedByW3c_shadow` (W3b pattern; residue writes core-inert + collapse);
- **star-general operand-read inertness** `graphRec_reconcileKey_inert` (NO `StarFreeStore`): a
  pass adds only edges onto its terminal R-node and all four `probeNonDerived` targets at
  untainted keys differ from it — subject-generic, star subjects included. This replaces the
  plain-edges shortcut and is the TEMPLATE for the read-half base work;
- **`reachedByW3c_master`**: one canonical base σ0 per chain — operand reads = base reads; every
  residue row carries the CANONICAL stars (`wildcardShapes.filter (coveredFn σ0)`); **guard
  canonicity**: `neg` members canonically expr-false, `upos` members canonically expr-true, every
  R-node in-edge from a canonically-uncovered, canonically-expr-true bare candidate
  (`reconcileKey_edge_guard` + prefix-mid-state inertness);
- **T2a `reachedByW3c_inv`**: full `Inv` — `negStarCovered` (write-time filter),
  `uposNegDisjoint` (covered vs ¬covered, same row), `uposEdgeFree` (userset member vs
  bare-sourced collapsed edge), `negEdgeFree` (the space rule cross-pass: canonically covered
  member vs canonically uncovered edge source — contradiction).

Attack-first (2026-07-11, recorded in `ReconcileStars.lean` header): planned model vs `sem`, 342
queries, `viewer/viewer2/viewer3` (incl. nested root) over 6 objects with `user:*` operand
grants — starred subtrahend kills coverage; mixed `and` uncovered; concrete-only exclusion does
not defeat `*`; covered subjects hold zero edges; D1 flow-through coverage; userset-driven `neg`;
idempotent, key-order/candidate-permutation independent. No refutation.

The W3b summary (upos machinery, `graph_correct_w3b`) and W3a summary are in the 2026-07-11
PROOF_STATUS entries.

**W3c read-half step 1 is CLOSED (2026-07-11)** — the star-relaxed base equation, three layers:
- **`graph_correct_rulesBS`** (`GraphIndex/RulesBareStar.lean`): W2's untainted `check = sem`
  over `BareStarStore` + **`TtuStarFree`** (no TTU arm matches a stored star tuple — attack-
  CONFIRMED necessary: a `folder:* → doc#parent` tupleset tuple makes `sem` true via `ttuLeaf`'s
  `instances` branch while the bridge-free `writeRules` graph answers false; star TTU parents
  need the W1c in-bridge machinery, deferred). Query scope: object concrete, subject concrete
  or star-BARE. Machinery: closure star-characterisation (`rewriteClosure_star_subject` — no
  ttu arm ever fires on a star closure member, so it carries the seed's full bare subject),
  subject-generic per-hop soundness/lift/chain composition (`subjNode_inj_total`), the
  star→concrete transfer `semAux_star_to_bare` (a probe-2 `wAny`-source chain IS a star-subject
  chain), completeness `nreaches_of_semAux_rulesBS` (probe-1 ∨ probe-2 disjunction).
- **`graphRec_base_eq_bs`** (`RestrictBase.lean`): the mixed-schema admitted base's operand
  read = `sem` — same schema-restriction route, `TtuStarFree` transfers to `S↾U` because the
  restriction preserves `schemaRewrites` (`ttuStarFree_restrict`).
- **`graphRec_reduce_base_adm_bs` + `checkFn_eq_sem_bs`** (`ReconcileComplete.lean`): the W3a-
  admitted reduce-to-base with NO `StarFreeStore` — the plain-edges probe-killing shortcut is
  replaced by transferring ALL FOUR probes (both probe targets carry the untainted key
  `(dt, r')`, so `reachedByW3aAdmitted_reach_inert` applies verbatim) — and the composed
  star-relaxed `checkFn ↔ sem` bridge, subject-generic up to star-BARE (the `coveredFn` reads).

---

## The next task — W3c read half, steps 2–3: the `W3cComplete` batch layer → `graph_correct_w3c`

Step 1 (the star-relaxed base equation, `checkFn_eq_sem_bs`) is CLOSED — see above. What
remains to close W3c:

1. **The `W3cComplete` batch layer** (W3b-style, mirror `W3aComplete`/`W3bComplete`): jobs =
   full-object `reconcileStarsKey` passes over a `ReachedByRulesAdmitted` base (note: the
   admitted-closure analog of `ReachedByW3c` may need defining, as `ReachedByW3aAdmitted`
   was); coverage clauses on the enumeration (edge cands ⊇ `sem`-true uncovered bare subjects;
   negCands ⊇ negative-leaf concretes ∪ derived-neg ids, `processor.py:394-404`; uposCands ⊇
   `sem`-true uncovered usersets); persistence = canonical-content stability (rows are
   wholesale-recomputed to the SAME canonical content — `reachedByW3c_master` already proves
   the content is chain-position-independent).
2. **Glue `checkFn_eq_sem_bs` to the W3c state**: `reachedByW3c_master` pins residue content
   to `coveredFn σ0`/`checkFn σ0` on the canonical base; `checkFn_eq_sem_bs` (over a
   `ReachedByW3aAdmitted` state) turns base `checkFn`/`coveredFn` reads into `sem` — the W3c
   chain's base is `ReachedByRules`; an ADMITTED variant of the W3c closure (or a master
   restated over an admitted base) is likely needed so the bs bridge applies. The fragment
   hypotheses now include `BareStarStore T` + `TtuStarFree S T` (replacing `StarFreeStore`).
3. **Assembly** `graph_correct_w3c` through the (already fully general) `probeDerived`: bare ⇒
   edge ∨ (stars ∖ neg), star ⇒ stars, userset ⇒ upos ∨ (stars ∖ neg); each branch glued by
   master's canonicity + `checkFn_eq_sem_bs`/`graphRec_base_eq_bs` + completeness. The star
   branch: `stars.contains s.shape` ↔ `coveredFn σ0 s.shape` (master) ↔ `sem` at the star-bare
   subject (`checkFn_eq_sem_bs`). Then T3/T6 `*_w3c` in `Equiv.lean`.

Scope guard (decision-15): object wildcards and wildcard usersets over derived relations stay
rejected; `wildcardShapes` carries only bare-subject-star shapes on this fragment; wildcard
TTU parents excluded (`TtuStarFree`). `hterm` (`NoTtuTarget`/`NoStoreSubjectR`) and
hCO/hLU/hRootB stay as in W3a/W3b.

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
