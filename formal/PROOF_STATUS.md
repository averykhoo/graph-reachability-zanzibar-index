# PROOF_STATUS.md — living status / ledger / adjudications

The session-persistent brain for the formal-verification build (plan §8.3). Update
this before ending ANY session. A fresh session should read, in order:
`docs/formal-verification-plan.md` → this file → `formal/SEMANTICS.md`.

---

## Current phase & resume point

- **Phase:** 0 (Semantics extraction) — **COMPLETE, awaiting user checkpoint.**
- **Next action:** user reviews `formal/SEMANTICS.md` (esp. §11 ambiguities A1 & A4,
  which request explicit sign-off). Do NOT start Phase 1 (Lean) until the spec is
  signed off — proving a wrong spec is the project's top risk (plan §10 risk table).
- **Blocked on:** user review.

---

## Phase ledger

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 0 | Semantics extraction | **done (checkpoint pending)** | SEMANTICS.md written with file:line cites; 7 ambiguities logged |
| 0.5 | (implied) verify compiler's undefined-reference behavior (A3) | todo | do during Phase 1 setup |
| 1 | Lean skeleton + spec + theorem statements | not started | CHECKPOINT on statements |
| 2 | Conformance bridge v1 (before deep proofs) | not started | validates spec cheaply |
| 3 | Set-engine model + T1 | not started | |
| 4 | Graph-index model + T2/T4/T5 | not started | ~half total effort |
| 5 | Equivalence T3 + security T6 | not started | |
| 6 | Hardening + CI + handoff | not started | |
| 7 | (optional) concurrency/crash in TLA+ | not started | separate go/no-go |

## Theorem ledger

All theorems are **stated only in SEMANTICS.md §8** so far; none encoded in Lean.
Status vocabulary: {planned, stated (Lean compiles w/ sorry), proved, blocked}.

| Theorem | Status | Note |
|---------|--------|------|
| T0a executable≡relational spec | planned | |
| T0b stratify soundness | planned | comparatively mechanical, do first in P1 |
| T1 set engine = sem | planned | MemberSet algebra lemmas are the work |
| T2a graph state invariant + materialize | planned | hardest; Phase 4 |
| T2b graph read = sem | planned | residue case analysis |
| T3 equivalence | planned | corollary of T1+T2b |
| T4 counting-IVM under acyclicity | planned | the crux lemma |
| T5 cascade settles in ≤#strata | planned | |
| T6a/b/c security corollaries | planned | |

## `sorry` ledger

Zero Lean written. Count = 0 by vacuous truth. Must be monotone non-increasing
within a phase once Lean exists.

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
- **Pending user sign-off (SEMANTICS.md §11):**
  - **A1** cascade-as-precondition: Lean model bakes cascade into each write op; the
    Python's reliance on the always-call convention (I9 is test-only) is recorded as
    a documented scope boundary, not proven away.
  - **A4** modeling boundary: propose modeling the graph at the *connectedstore
    (deduped) set* boundary, not the raw multigraph `WildcardIndex` boundary. This
    determines which Python `add_tuple` the correspondence table cites.

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
