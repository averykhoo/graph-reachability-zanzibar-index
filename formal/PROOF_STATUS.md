# PROOF_STATUS.md — living status / ledger / adjudications

The session-persistent brain for the formal-verification build (plan §8.3). Update
this before ending ANY session. A fresh session should read, in order:
`docs/formal-verification-plan.md` → this file → `formal/SEMANTICS.md`.

---

## Overnight autonomous run (2026-07-09 → 07-10)

User granted full autonomy ("keep going til you're done, I'll review tomorrow in one
go"). Plan, in priority order, committing each GREEN increment and documenting every
decision here:
1. Harden the spec: randomized conformance fuzzing (sem vs oracle vs set engine over
   random tuple subsets + grids). Safe (pure Python); catches spec bugs like the
   fuelBound one. Any unresolved divergence → adjudication log, don't block.
2. Concrete set-engine `expand` model (remove `opaque SetEngineModel.check`) + prove
   T1 with the algebra lemmas. Main proof effort.
3. Attempt T0a pigeonhole (`semAux_fuel_stable_step`) and T0b Kahn lemmas.
4. Attempt T4: define `pathCount` concretely, prove the first-edge recurrence + the
   counting theorem.
5. Shrink the opaque surface: concrete graph state types (even if T2/T5 stay sorry).
6. Final documentation + review summary.
Discipline: never commit a broken build; if a proof stalls past reasonable effort,
leave a documented `sorry` and move on. Update this file continuously.

## Overnight run RESULT (2026-07-10, end of session)

Delivered, all green + pushed (see REVIEW.md for the digest):
- **Found + fixed a real spec bug** (`fuelBound` additive→multiplicative), confirmed
  empirically, locked with the `deep_grid` regression. This was the headline outcome.
- **Conformance: 15 schemas, 60 tests green** (handwritten + randomized), three
  evaluators (`sem` / oracle / real set engine) agree everywhere. Added adversarial
  boolean corners (taint-over-boolean, nested boolean, double exclusion).
- **Proved (axiom-clean):** full MemberSet algebra + membership/constructor lemmas;
  `restrictionMatches_type` / T6c (real, not placeholder); `sem_fuel_stable` (T0a)
  reduced to one pigeonhole lemma. Axiom audit shows no custom axioms.
- **Tooling:** `zcli` CLI, `verify.sh` green gate, `Audit.lean` axiom check.
- **Handled a Gemini review:** adopted the valid fuelBound catch + WellDef
  decomposition (corrected); rejected the `phat_def` axiom (C4 cleanliness).

Remaining = the irreducible hard core (9 sorries): T1 (needs concrete expand model),
T2a/b + T5 (need concrete graph state machine), T4 counting (needs concrete pathCount
+ combinatorics), T0a pigeonhole core, T0b Kahn. All honestly deferred — NONE faked.
These want fresh context + the statement-review feedback; each is multi-hour.

**Next session resume:** see `formal/ROADMAP.md` (per-sorry plan, with corrections to
a Gemini roadmap). Phase 3 T1: the boolean STAR cases are done (`containsStar_*`); the
remaining nut is the INTENSIONAL `containsShape` distribution for concrete/ghost
subjects under a WF invariant — attempted this session, `simp; tauto` did NOT close
it (goal too large), so it's documented in ROADMAP with the intended route (a
`containsShape` normal-form lemma + per-atom split) rather than left as a `sorry`.
Gemini corrections logged: its set-engine model used `MemberSet String` (unsound —
name collisions across types; use `String × String`); its T0a pigeonhole is invalid
(our `semAux` has no visited-set); its T4 `phat_def` axiom rejected (C4 gate).

## Session 2026-07-10 (T2a groundwork — reachability layer fully proved)

User: "get the rest of T2 finished; commit often, push whenever you can." Scope
call (user-adjudicated mid-session via a fidelity question): **keep T2a honest,
DEFER** — do not postulate I6 as a `WriteStep` postcondition (the A1-style
operational shortcut was explicitly declined for `Inv`); instead **build toward the
genuine close** (the `reach ↔ NReaches` stabilization + a faithful reconcile). No
`sorry` discharged (count held at 3, as the user accepted); six green+pushed
increments of genuine, axiom-clean infrastructure delivered. `verify.sh` green
throughout (build + 60 conformance + audit).

**All in `GraphIndex/State.lean`, all axiom-clean (three standard axioms or fewer):**

- **Fuel-free reachability `NReaches`** (transitive closure of the edge list;
  distinct from WellDef's `Key`-typed `Reaches`). `Inv`'s reachability clauses
  (`acyclic`/`negEdgeFree`/`uposEdgeFree`) restated over it — this sidesteps the
  `nodes.length`-fuel churn that perturbs a capped probe when a write adds nodes.
  Lemmas: `NReaches.tail/trans/mono`, `NReachesR.trans`, `nreaches_nil`,
  `nreaches_cons_split` (first-use decomposition), **`acyclic_addEdge`**
  (cycle-rejection preserves acyclicity — the load-bearing I2 lemma).
- **Write-path primitives + preservation.** `addNode`/`addEdge`/`putResidue` with
  `@[simp]` projections; `StructInv` (the 4 structural clauses) + `structInv_addNode`
  / `structInv_addEdge` (genuine, cycle-rejection via `acyclic_addEdge`) /
  `structInv_empty` / `Inv.toStruct`; **`inv_putResidue`** (full `Inv` preserved by
  writing one I6-hygienic residue — other keys untouched; depends on *no* axioms).
- **`reach ↔ NReaches` BRIDGE — the ROADMAP-flagged "T2b blocker", now CLOSED.**
  `reachB_sound` + `reachB_mono` (soundness, any fuel); `reachB_of_nreaches` +
  `nreaches_iff_reachB` (unbounded equivalence); then the **shortest-walk
  compression** — `Trail` walk API (`trail_split`, `reachB_of_trail`,
  `trail_of_nreaches`, `trail_verts_mem`), pigeonhole plumbing (`mem_split_aux`,
  `exists_dup_split`, `nodup_len_le`), **`trail_compress`** (a walk with interiors
  in `nodes` shortens to ≤ `nodes.length` interiors), giving **`reach_complete`** and
  **`reach_iff_nreaches`**: the executable fixed-fuel probe `σ.reach` EXACTLY decides
  `NReaches` on any endpoint-closed state.

**What still blocks the two T2 sorries (unchanged in kind, now sharply isolated):**
the **faithful write/reconcile model** — how one tuple write produces the exact
edges + reconciled residues. Needed by BOTH: T2a (global I6 re-establishment after
edge changes — `inv_putResidue` handles one key; the write must cover all
reachability-affected keys with the *semantically correct* residues, so a
delete-only "reconcile-by-construction" is unfaithful and would break T2b) and T2b
(`check = sem` — the ≤4-probe decomposition now has its reachability half via the
bridge, but still needs the residue = `sem` half from the write model). This is the
genuine multi-session core; the reachability layer under it is now done.

## Session 2026-07-10 (T2 graph model CONCRETIZED — T5 closed)

**Scope decision (user-approved): "concretize + partial proofs," not the full T2
close** (T2 is the ~half-effort multi-session core; a faithful full close isn't
honestly doable in one pass, and a cooked `check := sem` model was explicitly
rejected). Delivered, `verify.sh` green (build + 60 conformance + audit),
count **4 → 3**:

- **All 7 opaque graph placeholders are now CONCRETE** (`GraphIndex/State.lean`,
  `sorry`-free): `GraphState` (nodes with `plain/wAny/wAll` variants, direct edges,
  residues `(stars,neg,upos)`, outbox+watermark), `GraphModel.check` (the faithful
  §7.5 ≤4-probe read + §7.6 residue path, routed by `isDerived`), `Inv` (I-series
  core: node encoding, I1 endpoint existence, I2 acyclicity, I6 residue hygiene incl.
  the load-bearing `neg ∩ edge-holders = ∅`), `ReachedBy` (inductive write-closure
  from `emptyState` via a minimal operational `WriteStep`), `Quiescent`
  (outbox-drain), `GraphAccepts` (decision-15 scope). The C4 "pending opaque" list
  for the graph model is cleared.
- **Reads model reachability, not path counts.** `check` probes a fuel-bounded
  transitive closure `reachB` of the direct edges (`p(u,v)>0`), factoring the
  path-*counting* layer out to `Closure.lean`/T4 — this dodges threading a
  `Fintype NodeKey` (infinite key space) through the read and keeps `check`
  executable. `Inv.acyclic` pins the DAG property T4 needs.
- **T5 `cascade_converges` CLOSED, axiom-clean** (`[propext]`). The model bakes the
  in-txn cascade into each write (§7.8 / A1, user-approved), so outbox-drain is a
  `WriteStep` postcondition and `Quiescent` holds at every reachable state by
  induction on `ReachedBy`.
- **T2a `graph_reached_inv`**: the `Quiescent` conjunct is closed (via
  `cascade_converges`); the `Inv` conjunct stays a tracked `sorry` (needs the full
  operational write path — edge/bridge/reconcile — which `WriteStep` abstracts).
- **Partial base-case lemmas, axiom-clean:** `inv_empty`, `quiescent_empty`,
  `reach_empty` (`reachB [] = false`).

**Remaining 3 sorries:** `semAux_fuel_stable_step` (T0a); `graph_reached_inv`'s `Inv`
half and `graph_correct` (T2b, the read = `sem` completeness argument) — the genuine
deep content, deferred as before. The concretization makes those statements relate
*real* definitions (not opaque constants), so the next attempt starts from a concrete
model rather than a stub.

## Session 2026-07-09 (T1 FULLY CLOSED — set engine = sem)

**T1 is DONE** — `setEngine_correct` is proved and axiom-clean (`[propext,
Classical.choice, Quot.sound]`, verified in `Audit.lean`). Count 5 → 4. `verify.sh`
green (build + 60 conformance + audit). The `opaque SetEngineModel.check` is replaced
by a concrete MemberSet-expand model. **T1 needs no WF/Stratifiable/AllValid** — the
hypotheses are retained (underscored) but unused: the expansion computes `semAux` at
*every* fuel, so equality at the shared `fuelBound` is unconditional.

**The model (`SetEngine/Eval.lean`).** `Id := SubjectRef`; `expandAux` is pure
fuel-recursion mirroring `semAux` (`expandStep`/`expandE` mirror `step`/`evalE`);
boolean nodes fold with `union`/`intersect`/`subtract`; leaves are `grantMS`/`parentMS`
(token `singletonEntity`/shape `star` + flow-through recursion), faithfully
transcribing `engine.py:direct_expand`/`ttu_expand`. `check` = `containsShape` of the
expanded query node at the query subject.

**The key modeling insight (makes the whole thing tractable).** `containsShape` *never
reads `pop`* — only `pos`/`stars`/`neg`. The distribution lemmas
(`containsShape_*_focus`) prove the probe answer is invariant across *any* population
satisfying `PopFocus`/`WFp`/`Grounded`. So I use a **query-focused population**
`popOf s σ = {s}` at `s`'s own shape, `∅` elsewhere — which makes all three invariants
hold *definitionally* (`popFocus_popOf`, `grounded_popOf` are trivial; `WFp` is every
`normalize` output). This discharges the "confinement" obligation the ROADMAP flagged
as the largest remaining piece, with **no** `pos ⊆ U` induction.

**Proof structure (`SetEngine/Correct.lean`, all axiom-clean).**
- `containsShape_unionFold` — probing a `union`-fold = `any` of the probes.
- `containsShape_grantMS` — one grant's probe = `grantMatch || grantFlow` (4-way on
  subject kind × wildness); `containsShape_expandDirect` assembles via `any_or_distrib`
  and a per-subject-kind match, `directLeaf`'s `memberOfGranted` = `any grantFlow` by
  `rfl`.
- `any_filter_guard` + `containsShape_expandTtu` — `ttuLeaf`'s guarded `T.any` =
  filtered `ttuParents.any`; per-parent probe matches by `pn == STAR` case split.
- `containsShape_expandE` (structural: boolean via `*_focus`, leaves via the above,
  `computed` = `HR`), `containsShape_expandAux` (fuel induction: `HR` = the fuel-IH,
  `HW` = `wfp_expandAux`), then `setEngine_correct`.
- Tactic notes for the leaf Bool-algebra: `beq_eq_decide` bridges `==`↔`decide`;
  `bool_eq_of_iff` + expanding `= true` lemmas + `SubjectRef.eq_iff` reduces to pure
  Props; `eq_comm` in *full* `simp_all` LOOPS with `decide`/`Bool` present (max-recursion)
  — keep it out; canonicalize orientation at Prop level or fall back to `tauto`/`aesop`.

**Now unblocked:** T3/T6a/T6b `rw`-route through T1∘T2b — they become real the moment
T2b lands. Remaining 4 sorries: T0a `semAux_fuel_stable_step`; T2a/T2b/T5 (need the
concrete graph state machine). Next-most-tractable: T0a (see ROADMAP option (a)).

## Session 2026-07-09 (T1 core corrected + T0a ingredient 1)

User asked to build T0a and T1. Both are multi-session (each needs its concrete
model/infrastructure first — see ROADMAP). This session delivered genuine, committed,
axiom-clean progress on both fronts; **no `sorry` discharged** (count held at 5), and
`verify.sh` stays green (build + 60 conformance + audit).

**Headline: the ROADMAP's T1 lemma was FALSE; corrected and proved.** The naive
intensional distribution `containsShape (op M N) = containsShape M ⟨op⟩ containsShape N`
under `WF` alone does NOT hold — `#eval`-confirmed counterexample with both operands
`WF`: `a={stars:={σ}}`, `b={stars:={shape}, neg:={uid}}`, `uid∈pop σ`, `σ≠shape` ⇒
both operands `false`, `union a b` `true`. This is exactly why last session's
`simp; tauto` never closed it. **Root cause:** the query shape must be the subject's
*own* shape and populations partition the id space by shape — the missing invariant
`PopFocus pop uid shape := ∀ σ, uid∈pop σ → σ=shape`. New file `SetEngine/Contains.lean`
(axiom-clean, `[propext, Classical.choice, Quot.sound]`):
- `containsShape_union_focus` (needs `PopFocus` + `WFp`),
- `containsShape_intersect_focus` / `containsShape_subtract_focus` (additionally need
  `Grounded pop uid shape m := uid∈m.pos → uid∈pop shape` — else a positive *ghost* is
  dropped by the extensional meet/difference; also `#eval`-confirmed false without it),
- support: `WFp`, `wfp_normalize`/`wfp_union/intersect/subtract`, `PopFocus`,
  `Grounded`, `mem_starpop_focus`, `mem_ext_focus`, `containsShape_normalize`,
  `wfp_atoms`, `bool_ext`. Technique: reduce to 7 membership atoms, then
  `by_cases`-on-all-7 `<;> simp_all` (tauto times out).
**T1 next:** build the concrete `SetEngineModel.check` expand model whose `pop`/`Id`
*satisfy `PopFocus`+`WFp`+`Grounded` per node*, then the `Direct`/`TTU` leaf-vs-`sem`
equalities. The distribution core is now done.

**T0a: decision + ingredient 1.** Chose option (a) (real proof, no spec change).
New file `Spec/FuelStable.lean` (axiom-clean): `evalE_mono` — untainted/positive
fragment monotonicity (`RecLe`-refinement preserves truth on exclusion-free exprs),
via `memberOfGranted_mono`/`directLeaf_mono`/`ttuLeaf_mono` + `Expr.noExcl`. This is
step 1 of the convergence argument (untainted fragment = monotone iteration). The
full worked-out structure (untainted monotone layer + tainted Kahn-DAG ranks + the
reachable-atom counting bound) is in the file header and ROADMAP. Confirmed: pure
pigeonhole is invalid (no visited-set; `Φ` non-monotone via `.excl`).

## Session 2026-07-09 (T0b fully closed — Kahn correctness)

**T0b is DONE** — `stratify_none_iff_cycle` and `stratify_topological` are proved and
axiom-clean (`[propext, Classical.choice, Quot.sound]`). All in `Spec/WellDef.lean`, built
from scratch on the concrete `kahn`/`readyNodes`/`depEdges` (no new model needed, as the
ROADMAP predicted). Count 7 → 5. `verify.sh` green (build + 60 conformance + audit).

Infrastructure proved (all axiom-clean, reusable):
- `mem_readyNodes_iff` — `n` ready ↔ remaining ∧ every out-edge leaves remaining.
- `kahn_succ` — one-step unfolding of `kahn` on a non-empty remaining set (isolates the
  definitional `if`/`let` churn once).
- `stuck_cycle` — **the pigeonhole core**: a non-empty stuck set (no ready nodes) has a
  cycle. Builds a total successor `g` (choice), iterates `g^[·]` into `R.toFinset`,
  `Finset.exists_ne_map_eq_of_card_lt_of_maps_to` gives a repeat, `reaches_orbit` turns
  the sub-walk into `Reaches edges k k`.
- `kahn_none_stuck` (⟹): `kahn = none` ⇒ a stuck set exists. The invariant
  `|remaining| ≤ fuel` (fuel starts at `|nodes|`, each round drops ≥1 via
  `List.length_filter_eq_length_iff`) rules out the fuel-exhaustion branch, so only a
  genuine stuck set can fail.
- `first_edge` / `cyc_out` — a cycle node has an out-edge to another cycle node.
- `kahn_cycle_none` (⟸): every cycle node persists in `remaining` (never ready), so the
  run never empties ⇒ `none`.
- `depEdges_mem` — both endpoints of a dependency edge are tainted keys (pins cycle
  nodes ⊆ initial `remaining`).
- `kahn_topo` — **the topological invariant**: threads (H1) `acc.reverse` is already
  topological + (H2) peeled nodes' out-edges have left `remaining`. Newly-peeled ready
  layer is appended last; readiness + H2 force its edges strictly earlier, so the
  invariant is preserved and the final `L` is `TopoLayered`. Needed hand-rolled
  `getD_app_lt`/`getD_app_ge`/`getD_ge_default`/`mem_getD_singleton` (this Mathlib has no
  `getD_append`).

**Next-most-tractable remaining:** T0a `semAux_fuel_stable_step` (subtle — see ROADMAP;
may want the visited-set spec refactor + conformance re-validation), then T1/T2 which need
their concrete models built first.

## Session 2026-07-09 (T4 fully closed)

**T4 is DONE** — `GraphIndex/Closure.lean` is `sorry`-free and axiom-clean. Built the
walk API the ROADMAP called the blocker, then the counting theorem, all from scratch on
the concrete `pathsOfLength`:
- `pathsOfLength_pos_iff` — walk-count positivity ↔ an `IsChain` vertex list (bridges to
  Mathlib's `List.IsChain` reachability API).
- `pathsOfLength_card_vanish` — **the pigeonhole vanishing lemma**: an acyclic graph has
  no length-`|V|` walk (`|V|+1` vertices ⇒ repeat ⇒ closed sub-walk via `IsChain.drop/take`
  + `getElem?_drop`/`getElem?_take_of_succ` ⇒ `pathCount x x > 0` ⇒ ⊥). Discharges the
  `hvanish` hypothesis of `phat_recurrence`.
- `pathsOfLength_succ_last` (last-edge decomposition), `pathsOfLength_mono`,
  `acyclic_of_addEdge`, `no_back_path` (the new edge can't close a cycle — needs L2).
- `rec_closed_form` / `rec_unique` — the affine recurrence `X a = c a + ∑ dcount·X`
  has a **unique** solution in a DAG (unroll `|V|` steps; the `X`-tail vanishes, leaving a
  matrix series in `c` only). No Nat subtraction anywhere.
- `pathCount_addEdge` — `phat g'` and the target formula both solve `g'`'s recurrence, so
  by `rec_unique` they coincide; the spurious back-path term vanishes by `no_back_path`.
- `pathCount_removeEdge` — the exact inverse: `(g.removeEdge u v).addEdge u v = g`, so it
  is `pathCount_addEdge` applied to `g.removeEdge u v`.

Count 9 → 7. `verify.sh` green (build + 60 conformance + audit). **Next-most-tractable
remaining: T0b Kahn** (self-contained, no new model needed); then T1/T2 need their
concrete models built first (see ROADMAP).

## Current phase & resume point

- **Phase 1 DONE** (Lean skeleton + all T0–T6 stated; `lake build` green with 9
  `sorry`s). **Phase 2 CORE DONE ahead of schedule**: conformance CLI (`zcli`) live;
  spec-vs-oracle answer conformance green (6/6 grid comparisons). No adjudication
  events — the executable `sem` matches the reference oracle.
- **User is reviewing `SEMANTICS.md` async** ("keep going, I'll review async"); A1 &
  A4 accepted. Continue proving; revisit if the review changes the spec.
- **Resume point → Phase 3:** replace the `opaque SetEngineModel.check`
  (`SetEngine/Eval.lean`) with a concrete MemberSet-expand model, prove T1
  (`setEngine_correct`), and extend conformance to compare the set-engine MODEL.
- **Commands:** `cd formal/lean && lake build` (lib) / `lake build zcli` (CLI);
  `python -m pytest formal/conformance/ -q` (needs `zcli` built).

---

## Phase ledger

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 0 | Semantics extraction | **done** | SEMANTICS.md; 7 ambiguities logged |
| 0.5 | verify compiler undefined-reference behavior (A3) | todo | refine `WF` in Phase 3/4 |
| 1 | Lean skeleton + spec + theorem statements | **done** | builds green; all T0–T6 stated |
| 2 | Conformance bridge v1 | **done** | three-way `sem`/oracle/set-engine over 11 schemas, 33 tests green; graph backend TODO in P4 |
| 3 | Set-engine model + T1 | **done** | concrete expand model; T1 proved, axiom-clean |
| 4 | Graph-index model + T2/T4/T5 | not started | ~half total effort |
| 5 | Equivalence T3 + security T6 | statements done | T3/T6a/b `rw`-proved modulo T1/T2b |
| 6 | Hardening + CI + handoff | not started | |
| 7 | (optional) concurrency/crash in TLA+ | not started | separate go/no-go |

## Theorem ledger

Status: {planned, stated (compiles w/ sorry), proved-mod-deps, proved, blocked}.

| Theorem | Lean name | Status | Note |
|---------|-----------|--------|------|
| T0a spec well-defined (fuel-stable) | `sem_fuel_stable` | **proved-mod-deps** | proved from `semAux_fuel_stable_step` by `Nat.le_induction` |
| T0a pigeonhole core | `semAux_fuel_stable_step` | stated (sorry) | one-more-fuel-is-a-no-op above the bound |
| T0b stratify soundness | `stratify_none_iff_cycle`, `stratify_topological` | **proved** | Kahn correctness; axiom-clean. Pigeonhole `stuck_cycle` + fuel invariant `kahn_none_stuck` + cycle-persistence `kahn_cycle_none` + topo invariant `kahn_topo` |
| T0b pigeonhole core | `stuck_cycle` | **proved** | stuck set (no ready nodes) ⇒ cycle, via orbit + `Finset` pigeonhole |
| T0b Kahn helpers | `mem_readyNodes_iff`, `kahn_succ`, `kahn_none_stuck`, `kahn_cycle_none`, `kahn_topo`, `depEdges_mem` | **proved** | reusable Kahn/`readyNodes` API (WellDef.lean) |
| T1 set engine = sem | `setEngine_correct` | **proved** | axiom-clean; concrete expand model + fuel/AST induction; WF/Strat/AllValid unused |
| T1 leaf/structure/fuel | `containsShape_expandDirect/expandTtu/expandE/expandAux` | **proved** | grant/parent probe correspondence, structural + fuel inductions (Correct.lean) |
| T1 model + invariants | `expandAux`, `popOf`, `wfp_expandAux`, `popFocus_popOf`, `grounded_popOf` | **proved** | query-focused population makes PopFocus/WFp/Grounded definitional |
| T1 containsShape distribution | `containsShape_union/intersect/subtract_focus` | **proved** | Contains.lean; corrected (naive WF-only version is FALSE) — needs `PopFocus`(+`Grounded` for ∩/∖); axiom-clean |
| T1 distribution support | `WFp`, `wfp_normalize`, `mem_starpop_focus`, `mem_ext_focus`, `containsShape_normalize`, `wfp_atoms` | **proved** | Contains.lean building blocks |
| T0a untainted monotonicity | `evalE_mono` | **proved** | FuelStable.lean; ingredient 1 (excl-free ⇒ `RecLe` preserves truth); axiom-clean `[propext, Quot.sound]` |
| T0a monotonicity leaves | `memberOfGranted_mono`, `directLeaf_mono`, `ttuLeaf_mono` | **proved** | FuelStable.lean; positive `rec` use at leaves |
| T2a graph invariant + materialize | `graph_reached_inv` | **proved-mod-deps** | `Quiescent` conjunct closed; `Inv` conjunct sorry (needs operational write path) |
| T2b graph read = sem | `graph_correct` | stated (sorry) | residue case analysis; now over CONCRETE model |
| graph model concretization | `GraphState`/`GraphModel.check`/`Inv`/`ReachedBy`/`Quiescent`/`GraphAccepts` | **concrete** | State.lean; 7 opaque placeholders → real defs, sorry-free |
| graph model base cases | `inv_empty`, `quiescent_empty`, `reach_empty` | **proved** | axiom-clean; `emptyState` ⊨ `Inv`/`Quiescent`, reaches nothing |
| T3 equivalence | `backend_equivalence` | **proved-mod-deps** | `rw` through T1∘T2b (real once those land) |
| T4 counting-IVM (insert/delete) | `pathCount_addEdge/removeEdge` | **proved** | the crux; axiom-clean. Walk API + pigeonhole vanishing + recurrence-uniqueness |
| T4 pigeonhole vanishing | `pathsOfLength_card_vanish` | **proved** | `Acyclic → no length-\|V\| walk`; the ROADMAP-flagged blocker |
| T4 walk correspondence | `pathsOfLength_pos_iff` | **proved** | positivity ↔ `IsChain` vertex list |
| T4 recurrence uniqueness | `rec_unique`, `rec_closed_form` | **proved** | affine recurrence has unique solution in a DAG (matrix series) |
| T4 last-edge / monotonicity | `pathsOfLength_succ_last`, `pathsOfLength_mono`, `no_back_path` | **proved** | supporting lemmas for the counting expansion |
| T4 first-edge recurrence | `phat_recurrence` | **proved** | conditional on the DAG no-`|V|`-walk hyp; axiom-clean |
| T4 boundary sum-identity | `phat_boundary` | **proved** | the sum-manipulation heart, no acyclicity; axiom-clean |
| (lemma) sum-shift | `sum_Ico_shift_boundary` | **proved** | Nat induction |
| T5 cascade converges | `cascade_converges` | **proved** | axiom-clean `[propext]`; outbox-drain quiescence by induction on `ReachedBy` |
| T6a exclusion-effective | `exclusion_effective` | **proved-mod-deps** | via T1/T2b |
| T6b no-ghost-grant | `no_ghost_grant` | **proved-mod-deps** | via T2b |
| T6c wildcard scoping | `wildcard_scoping` | **proved** | real theorem now: `T:*` grants are type-scoped, via `restrictionMatches_type` |
| (lemma) grant type-scoping | `restrictionMatches_type` | **proved** | axiom-clean `[propext, Quot.sound]` |
| (lemma) `ext_normalize` | `MemberSet.ext_normalize` | **proved** | MemberSet renorm correctness |
| (lemmas) membership/constructors | `mem_ext_union/intersect/subtract`, `ext_empty/singletonEntity/star`, `neg_subset_starpop` | **proved** | T1 leaf/composition building blocks (Algebra.lean) |
| (lemmas) algebra ext laws | `ext_union/ext_intersect/ext_subtract` | **proved** | `ext (a⊕b) = ext a ⊕ ext b` (Algebra.lean); T1 workhorses |
| (lemmas) star laws | `stars_union/intersect/subtract` | **proved** | `rfl` |
| (lemmas) star×boolean | `containsStar_union/intersect/subtract` | **proved** | the pinned intensional `'*'` table (§5.6) |

## `sorry` ledger

**Count = 3** (was 9; **T4 + T0b + T1 closed 2026-07-09; T5 `cascade_converges`
closed 2026-07-10**, monotone non-increasing). Locations:
- `Spec/WellDef.lean`: `semAux_fuel_stable_step` (feeds `sem_fuel_stable`) (1)
- `GraphIndex/Correct.lean`: `graph_reached_inv` (only the `Inv` conjunct — the
  `Quiescent` conjunct is proved), `graph_correct` (2)

**`GraphIndex/State.lean` is `sorry`-free** — the 7 opaque graph placeholders are now
concrete definitions; `cascade_converges` (T5) is closed off the concrete `ReachedBy`.

**`SetEngine/Correct.lean` is now `sorry`-free** — `setEngine_correct` (T1) proved and
axiom-clean; the `opaque SetEngineModel.check` is replaced by a concrete expand model.

**`Spec/WellDef.lean`'s T0b theorems are now `sorry`-free** — `stratify_none_iff_cycle`
and `stratify_topological` proved and axiom-clean.

**`GraphIndex/Closure.lean` is now `sorry`-free** — `pathCount_addEdge` /
`pathCount_removeEdge` proved and axiom-clean (`[propext, Classical.choice, Quot.sound]`).

## Axiom audit snapshot (C4) — `lake build ZanzibarProofs.Audit`

Run 2026-07-09. `#print axioms` on representative results:
- `ext_normalize`, `ext_union`, `containsStar_subtract`, `mem_ext_union` →
  `[propext, Classical.choice, Quot.sound]` (the 3 standard axioms — clean).
- `restrictionMatches_type`, `wildcard_scoping`, `evalE_mono` → `[propext,
  Quot.sound]` (cleaner).
- `containsShape_union/intersect/subtract_focus` (T1 corrected core) → the 3 standard
  axioms.
- `sem_fuel_stable`, `backend_equivalence` → `[sorryAx]` (honestly flagged;
  route through tracked sorries). **No custom axioms** — Gemini's suggested
  `phat_def` axiom was rejected, keeping the surface clean for the final C4 gate.

## T4 progress (2026-07-10, this session)

`GraphIndex/Closure.lean`: `pathCount` **concretized** (weighted-walk sum over
`Fintype V`; the `opaque` is gone). Proved (axiom-clean): `pathsOfLength_zero/succ`,
`sum_Ico_shift_boundary` (Nat induction), `phat_boundary` (the first-edge recurrence
WITH the length-`|V|` boundary term, pure `Finset.sum` manipulation, no acyclicity),
and `phat_recurrence` (the clean recurrence, taking the DAG no-`|V|`-walk property as
an explicit hypothesis). Remaining T4 obligations (still `sorry`, count held at 9):
`pathCount_addEdge`/`removeEdge` — the algebraic expansion — plus discharging the
`hvanish` hypothesis via the pigeonhole vanishing lemma (needs a walk API; see
ROADMAP). Net: the mathematical heart of the counting theorem is proved; the
opaque is removed; count unchanged.

## Pending axioms (opaque placeholders — to be replaced, flagged by the C4 axiom audit)

The only remaining `opaque` is `ValidIdent` (Core/Ident — intended to stay abstract
per §2.1). **The entire graph model is now CONCRETE** — `GraphState`,
`GraphModel.check`, `Inv`, `ReachedBy`, `Quiescent`, `GraphAccepts` became real
definitions 2026-07-10 (State.lean); `pathCount` and `SetEngineModel.check` were
concretized earlier. The final axiom audit must show only `propext, Classical.choice,
Quot.sound` — no opaque model constants remain to eliminate (only the tracked
`sorry`s in `graph_reached_inv`/`graph_correct`/`semAux_fuel_stable_step`).

---

## Adjudications (spec/oracle/backend disagreements)

Per plan §8.2: any disagreement → STOP, record here (schema, ops, query, each
system's answer, analysis). Do NOT edit oracle/goldens/Python semantics or weaken a
theorem to match.

- **2026-07-09 — `fuelBound` too small (spec bug, not a semantic ambiguity). RESOLVED.**
  Found via a Gemini review of the Lean spec; **confirmed empirically**: a schema
  with `n` computed relations chained per object and linked across an `m`-object
  parent chain by TTU (a `deep_grid`, n=m=8) evaluates at depth ~`n·m`=64, but the
  additive `fuelBound = |keys| + 2|T| + 4` = 29 cut `semAux` off early → spec
  returned `false` where the oracle returned `true`. The oracle is ground truth; the
  bug was mine (under-provisioned fuel). **Fix:** `fuelBound = |keys| · (2|T| + 4)`
  (multiplicative — the recursion depth is bounded by the `(entity × relation)` state
  space, not their sum). Added `deep_grid` to the conformance corpus as a permanent
  regression; conformance 33→36 green. The shallow original corpus is why it slipped
  past — lesson logged. No user adjudication needed (spec bug, clear resolution).

---

## Decisions & variations log

Variations from the plan (`docs/formal-verification-plan.md`) or from the repo's
own specs, with rationale. (The user asked that variations be documented.)

- **2026-07-09 — Phase 0 delivered as SEMANTICS.md + PROOF_STATUS.md + README.md**
  under `formal/`, matching plan §8.4 layout. No deviation.
- **2026-07-09 — Executable spec will use per-stratum fixpoint iteration, NOT the
  oracle's Tarjan-lowlink provisional-False control flow** (SEMANTICS.md §11-A2).
  Rationale: cleaner T0a/termination proof; agreement with the oracle asserted by
  conformance C1 rather than by matching control flow. The oracle is being demoted
  from ground truth to cross-check, so this is sound.
- **2026-07-09 — Non-stratifiable schemas are OUT of the verified envelope**
  (SEMANTICS.md §4.4). All theorems carry `stratify S = some strata`. This matches
  the security audit's recommendation to reject cyclic-through-boolean upstream.
- **2026-07-09 — User approved: "lgtm, write everything." A1 & A4 accepted as
  proposed.** Proceeding: Lean graph model bakes the cascade into write ops (A1);
  graph modeled at the connectedstore deduped-set boundary (A4).

### Phase 1 (Lean) decisions

- **Toolchain:** Lean `v4.31.0` (stable) + Mathlib pinned to tag `v4.31.0`, built
  against the prebuilt cache (`lake exe cache get`). `elan` installed to
  `~/.elan`. Project at `formal/lean/`, lib `ZanzibarProofs`.
- **`sem` is fuel-based and primitive-recursive on the fuel `Nat`** (§ Semantics.lean):
  `semAux (fuel+1)` = one immediate-consequence `step` applied to `semAux fuel`.
  `step` is parameterized by the sub-node answer function `rec`, so no
  termination entanglement; the boolean/leaf logic is all in `step`. Mirrors the
  oracle's depth-bounded provisional-False recursion. `sem` runs at `fuelBound`.
- **Binary `union`/`inter`** in the AST instead of n-ary (associativity + WF arity≥2
  make it faithful; no empty-fold fail-open). Logged in Schema.lean.
- **Backend models are `opaque` placeholders in Phase 1** (`SetEngineModel.check`,
  `GraphState`, `GraphModel.check`, `Inv`, `ReachedBy`, `Quiescent`,
  `GraphAccepts`). This keeps T1/T2/T5 non-vacuous (they relate an opaque model to
  `sem`, provable only once the model is concrete). Phases 3–4 replace the opaque
  declarations with real definitions. T3/T6a/T6b are ALREADY proved by `rw`
  through T1/T2b (so they become real the moment T1/T2b are discharged).
- **`stratify`/taint is an independent reimplementation** of `compute_taint` +
  `_stratify` (Kahn layering over derived-dependency edges). Fidelity to the Python
  is a Phase-2 conformance check, not assumed.
- **Reality check on "T0 is mechanical" (plan §9 P1):** it is NOT. `sem_fuel_stable`
  (T0a) rests on the stratified fixpoint being reached by `fuelBound` — a genuine
  theorem because exclusion is non-monotone in fuel. `stratify_*` (T0b) is Kahn
  correctness. Both are STATED (compiling) in Phase 1 with `sorry`; proofs are
  tracked and deferred rather than force-fit. `MemberSet.ext_normalize` IS proved.
- **T6c (`wildcard_scoping`)** is a trivial `rfl` placeholder to be refined to the
  precise scoping statement in Phase 5.

---

## Key facts a fresh session must not re-derive

- The spec `sem` = **stratified Datalog¬ perfect model, queried pointwise** — both
  backends compute it; equivalence is a corollary (`theory.md:192-198`).
- The oracle (`tests/oracle.py`) is the operational reference we are *replacing* with
  the Lean executable spec; it becomes a cross-check, not a proof target.
- **I9 (fixpoint audit) is test-suite-only**, not per-commit — so cascade-runs-in-txn
  is an assumed precondition (SEMANTICS.md §7.8, §11-A1). Most load-bearing fact.
- The counting theorem (T4) is sound **only because cycles are rejected** — the group
  `(ℤ,+)` inverse argument fails with cycles (`theory.md:57-61`). Rejecting cyclic
  schemas is a *necessity*, not a policy.
- Toolchain (elan/Lean/lake) is **not yet installed**; installing requires user
  permission (repo rule). Lean lives outside the conda env; conformance harness runs
  under the `graph-reachability-zanzibar-index` conda env.
- Python is READ-ONLY for this project except test-only conformance code under
  `formal/conformance/` (plan §8.3).
