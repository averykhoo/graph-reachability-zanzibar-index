# PROOF_STATUS.md — living status / ledger / adjudications

The session-persistent brain for the formal-verification build (plan §8.3). Update
this before ending ANY session. A fresh session should read, in order:
`docs/formal-verification-plan.md` → this file → `formal/SEMANTICS.md`.

---

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
| 2 | Conformance bridge v1 | **core done** | `zcli` + spec-vs-oracle green (6/6); add backends in P3/4 |
| 3 | Set-engine model + T1 | **in progress** | replace opaque check; prove T1 |
| 4 | Graph-index model + T2/T4/T5 | not started | ~half total effort |
| 5 | Equivalence T3 + security T6 | statements done | T3/T6a/b `rw`-proved modulo T1/T2b |
| 6 | Hardening + CI + handoff | not started | |
| 7 | (optional) concurrency/crash in TLA+ | not started | separate go/no-go |

## Theorem ledger

Status: {planned, stated (compiles w/ sorry), proved-mod-deps, proved, blocked}.

| Theorem | Lean name | Status | Note |
|---------|-----------|--------|------|
| T0a spec well-defined (fuel-stable) | `sem_fuel_stable` | stated (sorry) | rests on stratified non-monotone fixpoint |
| T0b stratify soundness | `stratify_none_iff_cycle`, `stratify_topological` | stated (sorry) | Kahn correctness — not as mechanical as plan hoped |
| T1 set engine = sem | `setEngine_correct` | stated (sorry) | Phase 3; needs concrete model first |
| T2a graph invariant + materialize | `graph_reached_inv` | stated (sorry) | hardest; Phase 4 |
| T2b graph read = sem | `graph_correct` | stated (sorry) | residue case analysis |
| T3 equivalence | `backend_equivalence` | **proved-mod-deps** | `rw` through T1∘T2b (real once those land) |
| T4 counting-IVM (insert/delete) | `pathCount_addEdge/removeEdge` | stated (sorry) | the crux; opaque `pathCount` |
| T5 cascade converges | `cascade_converges` | stated (sorry) | subsumed by T2a |
| T6a exclusion-effective | `exclusion_effective` | **proved-mod-deps** | via T1/T2b |
| T6b no-ghost-grant | `no_ghost_grant` | **proved-mod-deps** | via T2b |
| T6c wildcard scoping | `wildcard_scoping` | placeholder (`rfl`) | refine to real statement in Phase 5 |
| (lemma) `ext_normalize` | `MemberSet.ext_normalize` | **proved** | MemberSet renorm correctness |
| (lemmas) algebra ext laws | `ext_union/ext_intersect/ext_subtract` | **proved** | `ext (a⊕b) = ext a ⊕ ext b` (Algebra.lean); T1 workhorses |
| (lemmas) star laws | `stars_union/intersect/subtract` | **proved** | `rfl` |
| (lemmas) star×boolean | `containsStar_union/intersect/subtract` | **proved** | the pinned intensional `'*'` table (§5.6) |

## `sorry` ledger

**Count = 9** (must be monotone non-increasing within a phase). Locations:
- `Spec/WellDef.lean`: `sem_fuel_stable`, `stratify_none_iff_cycle`,
  `stratify_topological` (3)
- `SetEngine/Correct.lean`: `setEngine_correct` (1)
- `GraphIndex/Closure.lean`: `pathCount_addEdge`, `pathCount_removeEdge` (2)
- `GraphIndex/Correct.lean`: `graph_reached_inv`, `graph_correct`,
  `cascade_converges` (3)

## Pending axioms (opaque placeholders — to be replaced, flagged by the C4 axiom audit)

`opaque` declarations standing in for not-yet-built models: `ValidIdent`
(Core/Ident — intended to stay abstract), `SetEngineModel.check` (→ Phase 3 def),
`GraphState`, `GraphModel.check`, `Inv`, `ReachedBy`, `Quiescent`, `GraphAccepts`
(→ Phase 4 defs), `pathCount` (→ Phase 4 def). The final axiom audit must show only
`propext, Classical.choice, Quot.sound` — every opaque here must become a real
definition before Phase 6.

---

## Adjudications (spec/oracle/backend disagreements)

None yet. Per plan §8.2: any disagreement → STOP, record here (schema, ops, query,
each system's answer, analysis), ask the user. Do NOT edit oracle/goldens/Python
semantics or weaken a theorem to match.

_(none)_

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
