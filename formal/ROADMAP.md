# ROADMAP — closing the remaining `sorry`s (3 left, was 9)

A per-theorem plan for discharging the remaining deep obligations. Synthesizes a
Gemini review roadmap **with corrections from actually type-checking against the
code** (Gemini wrote without a compiler and made several concrete errors, flagged
below). Read alongside `PROOF_STATUS.md` (status) and `SEMANTICS.md` (the spec).

Original 9 sorries; **✅ CLOSED: `pathCount_addEdge`/`pathCount_removeEdge` (T4),
`stratify_none_iff_cycle`/`stratify_topological` (T0b), `setEngine_correct` (T1),
`cascade_converges` (T5).** Remaining 3: `semAux_fuel_stable_step` (T0a);
`graph_reached_inv` (only its `Inv` conjunct) and `graph_correct` (T2a/T2b).

**Graph model concretized (2026-07-10):** all 7 opaque graph placeholders in
`GraphIndex/State.lean` are now real definitions (`GraphState`, `GraphModel.check`,
`Inv`, `ReachedBy`, `Quiescent`, `GraphAccepts`), so the remaining T2 sorries relate
concrete definitions, not stubs. The next attempt at T2a/T2b starts from that model.

---

## T1 — `setEngine_correct` — ✅ DONE (2026-07-09)

**Closed and axiom-clean.** `SetEngine/Correct.lean` is `sorry`-free; the
`opaque SetEngineModel.check` is a concrete expand model (`SetEngine/Eval.lean`). See
PROOF_STATUS "Session 2026-07-09 (T1 FULLY CLOSED)" for the full lemma list and the
tactic notes. Key wins vs. the original plan below:
- **`Id := SubjectRef`** (as the correction demanded — `MemberSet String` was unsound).
- **The confinement obligation evaporates.** `containsShape` never reads `pop`, so a
  **query-focused population** `popOf s σ = {s}` at `s`'s shape (else `∅`) makes
  `PopFocus`/`Grounded`/`WFp` hold *definitionally* — no `pos ⊆ U` induction. The
  distribution lemmas guarantee the probe answer is pop-invariant, so this focused
  population computes the same answers as the real global one.
- **T1 needs no WF/Stratifiable/AllValid** — the expansion equals `semAux` at every
  fuel; the hypotheses are retained (underscored) but unused.

The distribution core (`containsShape_*_focus`, below) was the genuinely hard,
previously-`FALSE`-then-corrected lemma; the leaves/structure/fuel inductions built on
it. **T3/T6a/T6b now route through T1∘T2b — real the moment T2b lands.**

### (original plan)

**Plan.** Replace `opaque SetEngineModel.check` with a concrete `expand`-based model:
`expandAux : Nat → … → MemberSet Id` (fuel-recursive like `sem`), booleans via
`MemberSet.union/intersect/subtract`, `check` = `containsStar/containsEntity/
containsUserset` of the query subject. Prove T1 by induction on fuel then on the AST.

**CORRECTION to Gemini:** its model used `MemberSet String` (ids = subject *names*).
That is **unsound** — `alice:user` and `alice:group` collide in `pos`. Use
`Id = String × String` (type, name) (or `SubjectRef`), and its `pop` had an unproved
injectivity `sorry`. Fix both.

**The intensional distribution — RESOLVED as a corrected lemma (2026-07-09), in
`SetEngine/Contains.lean`.** The naive law `containsShape (op M N) = containsShape M
⟨op⟩ containsShape N` under `WF` alone is **FALSE** — `#eval`-confirmed counterexample
with both operands `WF`: `a = {stars := {σ}}`, `b = {stars := {shape}, neg := {uid}}`
with `uid ∈ pop σ`, `σ ≠ shape`; both answer `false` for `shape` but `union a b`
answers `true`. The fix is the missing invariant **`PopFocus pop uid shape := ∀ σ,
uid ∈ pop σ → σ = shape`**. Proved, axiom-clean:
- `containsShape_union_focus` — needs `PopFocus` + `WFp` operands;
- `containsShape_intersect_focus` / `containsShape_subtract_focus` — additionally
  need **`Grounded pop uid shape m := uid ∈ m.pos → uid ∈ pop shape`**.

---

## T4 — `pathCount_addEdge` / `pathCount_removeEdge` — ✅ DONE (2026-07-09)

**Closed and axiom-clean.** `GraphIndex/Closure.lean` is `sorry`-free. The plan below was
executed: walk API (`pathsOfLength_pos_iff`) → pigeonhole vanishing
(`pathsOfLength_card_vanish`) → last-edge/monotonicity/no-back-path → recurrence
uniqueness (`rec_closed_form`/`rec_unique`) → `pathCount_addEdge`; `removeEdge` is its
inverse via `(g.removeEdge u v).addEdge u v = g`. Kept over ℕ (no ℤ needed) with **no**
custom axioms. Original plan retained below for the record.

### (original plan)

**Plan.** Replace `opaque pathCount`: add `[Fintype V]`, define
`pathsOfLength : Nat → V → V → Nat` (`0 ↦ [u=v]`; `k+1 ↦ ∑ w, dcount u w *
pathsOfLength k w v`), `pathCount = ∑ k ∈ Ico 1 (card V + 1), pathsOfLength k`,
`phat = pathCount + [u=v]`.

**CORRECTION to Gemini:** do NOT introduce the recurrence as an `axiom` (its
`phat_def`). A custom axiom about the opaque constant fails the C4 axiom-cleanliness
gate. Prove the recurrence as a LEMMA from the definition.

**Hard core:** `phat_recurrence : Acyclic g → phat u v = [u=v] + ∑ w, dcount u w *
phat w v`. From the definition this reduces to showing the boundary term
`∑ w, dcount u w * pathsOfLength (card V) w v = 0` — i.e. **no walk of length
`card V` exists in a DAG** (pigeonhole: such a walk repeats a vertex ⇒ a closed
subwalk ⇒ `pathCount x x > 0` ⇒ ¬Acyclic). This is the genuine combinatorial lemma;
our multigraph has no Mathlib `Walk` API, so it must be built (or bridged to
`Mathlib.Combinatorics.…`). Then `pathCount_addEdge` follows by algebraic expansion
of `(A + E_{uv})` using `phat_recurrence` and the DAG condition `v` cannot reach `u`;
deletion is the exact inverse in `(ℤ,+)`.

---

## T0a — `semAux_fuel_stable_step` (subtle — Gemini's proof is WRONG here)

**CORRECTION to Gemini:** it claims "the Tarjan-lowlink guard (which sem mimics)
yields false on a revisit," so pigeonhole gives stability. **But `semAux` has NO
visited-set** — it is pure fuel recursion. Pigeonhole on the state space does not
directly apply.

**Real options:**
(a) *Monotonicity argument.* For a stratifiable schema, positive recursion is
monotone (more fuel only adds `True`, stabilizing once all grants are found via their
shortest acyclic path ≤ state-space size); negative positions (`but not` subtrahends)
are lower strata, hence acyclic and fuel-stable. Formalizing this ties `Stratifiable`
(a Kahn property on `depEdges`) to the evaluation's DAG-depth — substantial.
(b) *Refactor `semAux` to carry a visited-set* (mirroring the oracle). Then Gemini's
pigeonhole applies cleanly — but it is a SPEC CHANGE and must be re-validated by the
conformance suite before relying on it. Prefer (b) if (a) proves too hard; do it
before Phase 5.

**DECISION (2026-07-09): pursue (a), no spec change.** Detailed structure worked out
(see `Spec/FuelStable.lean` header) and **ingredient 1 is proved** (`evalE_mono`:
untainted/positive-fragment monotonicity — on an exclusion-free expr, `evalE`
preserves truth under a `rec` refinement `RecLe`). The full argument:
1. Taint propagates upward ⇒ untainted keys reference only untainted keys and are
   exclusion-free ⇒ a monotone fragment (converges by #reachable untainted atoms —
   what makes `fuelBound` multiplicative; `evalE_mono` is this step).
2. `depEdges` includes *all* tainted-tainted references and Kahn makes them a DAG ⇒
   each tainted key's `Φ` depends only on strictly-lower-rank tainted atoms +
   untainted atoms ⇒ each rank stabilizes one fuel-step after its inputs (**crucially,
   a same-key different-name reference among tainted keys is a self-edge, rejected —
   so no cross-entity chaining *within* a tainted rank; only untainted chains**).
**Remaining to build (next pass):** the finite reachable-atom set + confinement lemma
(`semAux` depends only on `rec` there), the untainted monotone-convergence count, the
per-rank stabilization induction, and the arithmetic that the total level ≤
`|keys|·(2|T|+4)`. This is the multi-session core; ingredient 1 is the foothold.

---

## T0b — `stratify_none_iff_cycle` / `stratify_topological` — ✅ DONE (2026-07-09)

**Closed and axiom-clean.** `Spec/WellDef.lean`'s T0b theorems are `sorry`-free. The plan
below was executed almost verbatim (no Mathlib topological-sort lemma reused — hand-rolled
on the concrete `kahn`). See PROOF_STATUS "Session 2026-07-09 (T0b fully closed)" for the
full lemma list. Original plan retained below for the record.

### (original plan)

**Plan.** Standard Kahn correctness on `depEdges`/`kahn`. Forward
(`none → cycle`): if `kahn` returns `none`, the surviving `remaining` set has every
node with an out-edge into `remaining` (min out-degree ≥ 1) ⇒ a cycle (finite +
pigeonhole walk). Reverse (`cycle → none`): cycle nodes always retain an in-`remaining`
out-edge, so `readyNodes` never peels them ⇒ `remaining` stays non-empty.
`stratify_topological`: invariant that a peeled layer's nodes depend only on
already-peeled nodes. Check `Mathlib.Combinatorics` / `Order` for reusable
topological-sort / acyclicity lemmas before hand-rolling.

---

## T2 / T5 — `graph_reached_inv`, `graph_correct`, `cascade_converges`

**✅ Model concretized + `cascade_converges` (T5) closed (2026-07-10).** The opaque
placeholders are now real (`GraphIndex/State.lean`, `sorry`-free):
- `GraphState := { schema, edges : List (NodeKey × NodeKey), nodes, residue : NodeKey
  → String → Option Residue, outbox, watermark }` (`NodeKey = (type,name,pred,variant∈
  {plain,wAny,wAll})`; `Residue = (stars, neg, upos)`).
- `GraphModel.check` = the ≤4-probe read (`probeNonDerived`) + residue path
  (`probeDerived`), routed by `isDerived` (§7.5–7.6). **Reads probe reachability
  `reachB` (transitive closure of direct edges), not path counts** — the counting
  layer stays factored in `Closure.lean`/T4, dodging a `Fintype NodeKey`.
- `Inv` = the I-series core (node encoding, I1 endpoint existence, I2 `acyclic` via
  `reach`, I6 residue hygiene incl. `neg ∩ edge-holders = ∅`).
- `ReachedBy` = inductive write-closure from `emptyState` via `WriteStep` (a minimal
  operational spec that bakes the in-txn cascade ⇒ outbox drained).
- `cascade_converges` (T5) is **proved** (axiom-clean): `Quiescent` = outbox-drain is
  a `WriteStep` postcondition, so it holds at every reachable state by induction.
  Base cases `inv_empty`/`quiescent_empty`/`reach_empty` proved.

**Reachability layer DONE (2026-07-10, axiom-clean, `GraphIndex/State.lean`):**
`Inv` restated over a fuel-free `NReaches`; `acyclic_addEdge` (cycle-rejection
preserves acyclicity); write-path primitives `addNode`/`addEdge`/`putResidue` with
`structInv_addNode`/`structInv_addEdge`/`inv_putResidue`; and — closing the
**ROADMAP-flagged T2b blocker** — the full `reach ↔ NReaches` bridge
(`reach_iff_nreaches`) via shortest-walk compression (`Trail` API + `trail_compress`
pigeonhole). So the executable fixed-fuel probe now provably equals fuel-free
reachability, and each write primitive's structural preservation is proved.

**Write model STARTED (2026-07-10, `GraphIndex/Write.lean`, axiom-clean).** The
untainted (residue-free) fragment of the faithful write model is now concrete:
`writeDirect` (one guarded direct-edge write, cycle-rejection faithful to §7.3),
`inv_writeDirect` (preserves the whole `Inv` — residue clauses vacuous on the
fragment), and `ReachedByDirect`/`reachedByDirect_inv` (**T2a's `Inv` conjunct
honestly proved for the untainted fragment**), embedding in the abstract
`ReachedBy` via `writeDirect_writeStep`. Two blockers remain, now sharply isolated:
(a) **derived reconcile** — residue materialization + the cross-key hazard (an edge
write re-reaching an existing residue key breaks `negEdgeFree` until reconcile);
(b) **T2b read = sem** — even the pure-direct case needs an acyclic-*data*
hypothesis, because `writeDirect` drops cycle-forming edges while `sem`
fuel-evaluates them.

**T2b groundwork DONE (2026-07-10, axiom-clean) — read=`sem` scaffolded from both
ends.** `GraphIndex/Correct.lean` + `State.lean` + `Write.lean`:
- **Base case CLOSED:** `graph_correct_empty` (`check (emptyState S) q = sem S [] q`,
  both `false`) — the `ReachedBy.empty` case, via `sem_empty_store` + `check_empty`.
- **Read → reachability:** `probeNonDerived_iff` rewrites the executable ≤4-probe read
  as a disjunction of four `NReaches` conditions (via `reach_iff_nreaches`).
- **Reachability → chain:** `TupleChain` + `reachedByDirect_nreaches_chain`
  (+`reachedByDirect_edge_sound`, `writeDirect_edges`) — an untainted graph path IS a
  stored-tuple membership chain. This is T2b's reachability-half soundness, relational.

**FINDING (2026-07-10, taking stock): the two T2 sorries are FALSE as stated, not
merely unproven.** `WriteStep` is a thin postcondition spec (schema fixed, nodes
monotone, outbox drained) and `Inv` never ties `σ.edges`/`σ.residue` to the store
`T`. Counter-model: from `emptyState S`, one `WriteStep` into a state carrying a
single arbitrary acyclic edge `(a,b)` (both nodes added, encoding-valid, outbox
empty) satisfies `ReachedBy σ S [t]`, `Inv S σ`, and every schema hypothesis — yet
`check` answers `true` on the corresponding query while `sem S [t]` answers `false`
for an unrelated `t`. Consequence: **no proof effort can close `graph_correct` or
`graph_reached_inv`'s `Inv` conjunct in their current form.** The operational write
model is not merely "the blocker", it is *mandatory for the statements to be true*.
Endgame: complete the operational write path (untainted `writeDirect` ✓ done;
wildcard bridges; derived reconcile), then RESTATE T2a/T2b over that operational
closure (either replace `WriteStep` by the concrete write or keep fragment-indexed
theorems). The abstract statements stay as tracked sorries only as placeholders for
the final restatement — do not sink proof effort into them as written.

**Remaining (the genuine multi-session cores):**
- **T2b semantic core:** `TupleChain T u v ↔ sem`-membership — match the membership
  chain against `directLeaf`/`memberOfGranted`'s userset recursion, the wildcard-node
  promotion (`wAny`/`wAll` in `probeNonDerived_iff`), `instances`, `matchingObjects`.
  Plus the converse edge-completeness (`TupleChain → NReaches`), which needs an
  acyclic-*data* hypothesis (`writeDirect` drops cycle-forming edges while `sem`
  fuel-evaluates them). The read/reachability plumbing is done; this is the last mile.

  **✅ EXECUTED (2026-07-10, same session): the semantic core is CLOSED on the
  star-free pure-direct fragment** — `GraphIndex/DirectCorrect.lean` is sorry-free
  and `graph_correct_direct` is axiom-clean (`[propext, Classical.choice,
  Quot.sound]`, audited). The plan below was executed verbatim (steps 1–6 map to
  `semAux_mono`, `TupleChainN`/`chainN_of_trail`, `semAux_lift`,
  `semAux_of_chainN`, `nreaches_of_semAux`, `graph_correct_direct`). The original
  plan is retained for the record:

  Plan: close the semantic core end-to-end on the star-free pure-direct fragment,
  as a genuine, non-vacuous
  `graph_correct_direct`. Fragment: every schema def is `.direct rs` (`PureDirect`),
  the store is admission-valid (`StoreValid`: each tuple's `(object.type, relation)`
  is declared `.direct rs` with `restrictionMatches rs t`; matches the Python
  admission gate) and star-free; the state is reached by *admitted* writes
  (`ReachedByAdmitted` — faithful to the composed system, where a cycle-rejected
  write rolls back the tuple insert too, so the store never holds a rejected tuple).
  Proof structure, worked out against the code:
  1. `semAux_mono` (fuel monotonicity on exclusion-free schemas, from `evalE_mono`)
     — dual-use: also T0a ingredient 1½.
  2. Length-indexed chains `TupleChainN` + `chainN_of_trail` (via
     `reachedByDirect_edge_sound`), giving NReaches → short chain (`trail_compress`).
  3. **Userset lifting** (the heart): if `s ∈ sem`-member of userset `s'` at fuel f₀
     and `s'` is a member of node `v` at fuel `f`, then `s ∈ v` at `f + f₀` — by fuel
     induction; every direct-match of `s'` at a grant is absorbed by `s`'s
     `memberOfGranted` flow-through on the same grant (needs `s'.predicate ≠ BARE`,
     from `WF.relNames` since `BARE` contains `'.'`).
  4. Soundness: `TupleChainN n → semAux` at fuel `n` (single = direct match at fuel 1;
     cons = lifting with f₀ = 1); fuel fits `fuelBound` since `n ≤ nodes.length + 1
     = 2·|T| + 1 < |keys|·(2|T|+4)` (keys nonempty from `StoreValid` + chain ≠ []).
  5. Completeness: `∀ f, semAux s f ot on r → NReaches (subjNode s) (objNode ⟨ot,on⟩ r)`
     by fuel induction: direct-match ⇒ the grant's own edge (edge-completeness from
     `ReachedByAdmitted`); `memberOfGranted` ⇒ IH + `objNode ⟨g.sub.type,g.sub.name⟩
     g.sub.pred = subjNode g.subject` (both plain, star-free) + `NReaches.tail`.
  6. Assembly: `PureDirect → taintedKeys = []` (so `check` routes to
     `probeNonDerived`); star-free store ⇒ no edge touches `wAny`/`wAll` nodes ⇒
     probes 2–4 are `false`; probe 1 ↔ NReaches (`reach_iff_nreaches`) ↔ chain ↔ sem.
  Wildcards (bridge materialization — the model has none yet; read-side promotion
  only covers the *first* hop), TTU/computed/union defs, and the derived/residue path
  are the explicitly deferred extensions, each widening the fragment.
- **T2b residue path:** for derived relations, residue = `sem` via `ext_normalize`/T1
  MemberSet lemmas; bare-subject edge-hit ≡ full residue via `Inv.negEdgeFree`. Needs
  the write model to know what the residues *are* (the reconcile output).
- **T2a** (`graph_reached_inv`, `Inv` conjunct): the write must re-establish I6 for
  *all* reachability-affected keys with the semantically-correct residues.
  `inv_putResidue` closes the per-key step; a delete-only reconcile-by-construction is
  **unfaithful** (changes residue meaning ⇒ breaks T2b), so the faithful delta output
  must be modeled. Structural clauses already discharged by the `structInv_*` lemmas.

---

## Suggested order

1. ~~**T4**~~ ✅ DONE (axiom-clean; `Closure.lean` sorry-free). Unblocks T2b's edge reasoning.
2. ~~**T0b**~~ ✅ DONE (axiom-clean; `WellDef.lean` T0b theorems sorry-free). Hand-rolled
   Kahn correctness (`stuck_cycle` pigeonhole + `kahn_none_stuck`/`kahn_cycle_none` +
   `kahn_topo`). The `List`-bookkeeping estimate held (needed hand-rolled `getD_app_*`).
3. ~~**T1**~~ ✅ DONE (axiom-clean; `Correct.lean` sorry-free). Concrete expand model
   + query-focused population + fuel/AST induction. Unblocks T3/T6 (route through T1∘T2b).
4. **T2/T5** — graph model CONCRETIZED; **T5 `cascade_converges` ✅ DONE**; the
   **reachability layer ✅ DONE** (2026-07-10: `reach ↔ NReaches` bridge, cycle-
   rejection, structural write-primitive preservation, per-key `inv_putResidue`).
   **T2b groundwork ✅ DONE** (base case + `probeNonDerived_iff` + `TupleChain`/
   `reachedByDirect_nreaches_chain`). **T2b SEMANTIC CORE ✅ DONE** (2026-07-10:
   `graph_correct_direct` — end-to-end `check = sem` on the star-free pure-direct
   fragment, axiom-clean; userset lifting + chain⇔`sem` both directions,
   `DirectCorrect.lean`). Remaining, in suggested order: (a) **wildcard bridges**
   (materialize concrete→`wAny` bridges in the write model + extend the fragment
   theorem to star data/queries); (b) **computed/union/TTU defs** (rule-routed
   edge materialization — the graph writes edges onto rule-derived families);
   (c) the **faithful reconcile model** (residue output) for T2a and the derived
   T2b path; then (d) restate/replace the abstract `graph_correct`/
   `graph_reached_inv` over the completed operational closure (they are FALSE as
   currently stated — see the FINDING above).
5. **T0a** (decide (a) vs (b) first) — the only remaining `Spec/` sorry; ingredient 1
   (`evalE_mono`) proved.

---

## Session handoff — environment & hard-won Lean/Mathlib notes

For a fresh session. Read `PROOF_STATUS.md` (status/resume) → this file → the target
`.lean`. Everything is committed; `.lake/` (mathlib clone + cache) is on disk and
gitignored (regenerate with `lake exe cache get` if missing).

**Build/verify commands** (Lean toolchain is at `~/.elan/bin`):
```
export PATH="$HOME/.elan/bin:$PATH"
cd formal/lean && lake build                 # library (~min incremental; use background)
lake build ZanzibarProofs.GraphIndex.Closure # one module (~20s)
lake build zcli                              # conformance CLI
rm -f .lake/build/lib/lean/ZanzibarProofs/Audit.olean && lake build ZanzibarProofs.Audit  # axiom audit
bash formal/verify.sh                         # full gate (build + sorries + audit + pytest)
```
Conformance uses the repo conda env python (`.../envs/graph-reachability-zanzibar-index/python.exe -m pytest formal/conformance/ -q`). Lean = v4.31.0, Mathlib pinned v4.31.0.

**Mathlib import quirks (v4.31.0) — these cost build cycles to find:**
- `Finset.Ico` ← `import Mathlib.Order.Interval.Finset.Nat`
- `Finset.sum_Ico_succ_top`, `sum_Ico_consecutive` ← `Mathlib.Algebra.BigOperators.Intervals`
- big-operator ring lemmas (`Finset.mul_sum`, distribution) ← `Mathlib.Algebra.BigOperators.Ring.Finset`
- `∑ w : V, …` Fintype sums ← `Mathlib.Data.Fintype.BigOperators`
- `Finset.biUnion` ← `Mathlib.Data.Finset.Union`
- `Mathlib.Algebra.BigOperators.Basic` / `.Ring` do **NOT** exist (reorganized). `ring`
  tactic needs `Mathlib.Tactic.Ring` (not transitively available).

**Tactic gotchas learned this session:**
- To unfold a plain `def` inside a goal use `unfold f` or `simp only [f]`, **not**
  `rw [f]` (rw usually won't fire on a non-pattern-matching def — this cost ~4 cycles
  on `phat`). `pathCount`/`phat` unfold fine under `simp only [...]`.
- `Nat` distribution: `exact Nat.left_distrib _ _ _` (term-mode, no import).
- `omega` closes linear-Nat goals treating `∑`-terms as opaque atoms — ideal for
  combining `have`s about sums (used to finish `phat_boundary`, `sum_Ico_shift_boundary`).
- `simp only at h` with no lemmas errors "no progress"; drop it (elaboration already
  beta-reduces instantiated lambdas, so `omega` sees the reduced form).
- `Finset.sum_Ico_succ_top (h : a ≤ b)` peels the TOP term of `Ico a (b+1)`; supply the
  witness for `b`, not `b+1` (e.g. `Nat.le_add_left 1 m : 1 ≤ m+1`, not `… (m+1)`).
- Prefer explicit `have e1/e2 … ; calc` over `congr 1` for sum equalities — `congr 1`
  split fragilely here.

**The T4 blocker (do this first to finish T4):** a **walk API** for the Nat-weighted
multigraph. Concretely: (i) `pathsOfLength g k u v > 0 ↔ ∃ (walk : List V) of length k
from u to v with all edges positive` (induction on `k`); (ii) the **vanishing lemma**
`Acyclic g → pathsOfLength g |V| w v = 0` (a length-`|V|` walk has `|V|+1` vertices ⇒
pigeonhole repeat ⇒ closed sub-walk ⇒ `pathCount x x > 0` ⇒ ¬Acyclic) — this discharges
`phat_recurrence`'s `hvanish`; (iii) `pathCount_addEdge` by decomposing `g'`-walks into
"uses new edge `(u,v)` 0 or 1 times" (acyclic ⇒ ≤ 1). Check whether
`Mathlib.Combinatorics.SimpleGraph.Walk` or `Quiver.Path` can be adapted before rolling
your own. Once (ii)+(iii) land, `pathCount_removeEdge` is the `(ℤ,+)` inverse of (iii).

**Realistic scope:** closing all 9 is multi-session. Each of T1/T2 needs its concrete
model built first (see the per-theorem sections above); T0b/T0a and the T4 walk API are
each self-contained multi-hour proofs.
