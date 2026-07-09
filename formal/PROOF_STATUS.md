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
| 3 | Set-engine model + T1 | **in progress** | replace opaque check; prove T1 |
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
| T0b stratify soundness | `stratify_none_iff_cycle`, `stratify_topological` | stated (sorry) | Kahn correctness — not as mechanical as plan hoped |
| T1 set engine = sem | `setEngine_correct` | stated (sorry) | Phase 3; needs concrete model first |
| T2a graph invariant + materialize | `graph_reached_inv` | stated (sorry) | hardest; Phase 4 |
| T2b graph read = sem | `graph_correct` | stated (sorry) | residue case analysis |
| T3 equivalence | `backend_equivalence` | **proved-mod-deps** | `rw` through T1∘T2b (real once those land) |
| T4 counting-IVM (insert/delete) | `pathCount_addEdge/removeEdge` | **proved** | the crux; axiom-clean. Walk API + pigeonhole vanishing + recurrence-uniqueness |
| T4 pigeonhole vanishing | `pathsOfLength_card_vanish` | **proved** | `Acyclic → no length-\|V\| walk`; the ROADMAP-flagged blocker |
| T4 walk correspondence | `pathsOfLength_pos_iff` | **proved** | positivity ↔ `IsChain` vertex list |
| T4 recurrence uniqueness | `rec_unique`, `rec_closed_form` | **proved** | affine recurrence has unique solution in a DAG (matrix series) |
| T4 last-edge / monotonicity | `pathsOfLength_succ_last`, `pathsOfLength_mono`, `no_back_path` | **proved** | supporting lemmas for the counting expansion |
| T4 first-edge recurrence | `phat_recurrence` | **proved** | conditional on the DAG no-`|V|`-walk hyp; axiom-clean |
| T4 boundary sum-identity | `phat_boundary` | **proved** | the sum-manipulation heart, no acyclicity; axiom-clean |
| (lemma) sum-shift | `sum_Ico_shift_boundary` | **proved** | Nat induction |
| T5 cascade converges | `cascade_converges` | stated (sorry) | subsumed by T2a |
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

**Count = 7** (was 9; **T4 fully closed 2026-07-09**, monotone non-increasing). Locations:
- `Spec/WellDef.lean`: `semAux_fuel_stable_step` (feeds `sem_fuel_stable`),
  `stratify_none_iff_cycle`, `stratify_topological` (3)
- `SetEngine/Correct.lean`: `setEngine_correct` (1)
- `GraphIndex/Correct.lean`: `graph_reached_inv`, `graph_correct`,
  `cascade_converges` (3)

**`GraphIndex/Closure.lean` is now `sorry`-free** — `pathCount_addEdge` /
`pathCount_removeEdge` proved and axiom-clean (`[propext, Classical.choice, Quot.sound]`).

## Axiom audit snapshot (C4) — `lake build ZanzibarProofs.Audit`

Run 2026-07-09. `#print axioms` on representative results:
- `ext_normalize`, `ext_union`, `containsStar_subtract`, `mem_ext_union` →
  `[propext, Classical.choice, Quot.sound]` (the 3 standard axioms — clean).
- `restrictionMatches_type`, `wildcard_scoping` → `[propext, Quot.sound]` (cleaner).
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

`opaque` declarations standing in for not-yet-built models: `ValidIdent`
(Core/Ident — intended to stay abstract), `SetEngineModel.check` (→ Phase 3 def),
`GraphState`, `GraphModel.check`, `Inv`, `ReachedBy`, `Quiescent`, `GraphAccepts`
(→ Phase 4 defs). (`pathCount` is now CONCRETE — no longer opaque.) The final axiom
audit must show only `propext, Classical.choice, Quot.sound` — every remaining opaque
must become a real definition before Phase 6.

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
