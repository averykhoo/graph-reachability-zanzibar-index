# formal/ — machine-checked correctness for the two backends

This directory holds the formal-verification effort for the set engine and graph
index: a Lean 4 proof that both compute the stratified-Datalog¬ perfect model of
`(schema, tuples)` — hence are equivalent — plus a conformance harness pinning the
Python implementations to the proven models.

## Orientation (read in this order)

1. **`HANDOFF.md` — START HERE.** The compact entry point: state of the world,
   house rules, build commands, and the precise next task. A working session needs
   this file plus the target `.lean` and nothing else up front.
2. `PROOF_STATUS.md` — the append-only session ledger (newest first). Read the top
   entry for resume-point detail.
3. `ROADMAP.md` — per-stage designs (W1–W4 staged widening) and post-mortems.
4. `SEMANTICS.md` — the Phase-0 specification (the trust root): the domain, AST,
   well-formedness, the `sem` fixpoint semantics, both backend models, the exact
   theorem hypotheses, and the open ambiguities. Everything downstream proves things
   *about this document*.
5. `../docs/formal-verification-plan.md` — the original full plan: strategy, phases,
   process rules, risk register, and the §7 honesty clauses (final-report wording).

## Layout

```
formal/
  README.md          -- this file
  HANDOFF.md         -- session entry point (state + next task + rules)
  SEMANTICS.md       -- Phase 0 spec
  PROOF_STATUS.md    -- append-only ledger
  ROADMAP.md         -- staged plan + designs
  REVIEW.md          -- historical session digest (2026-07-09→10)
  CORRESPONDENCE.md  -- Lean def ↔ Python file:line map (the audit backbone)
  FINAL_REVIEW.md    -- the final claim (plan §7 verbatim + clause cross-check)
  verify.sh          -- the one-command green gate
  lean/              -- the Lean 4 development
  conformance/       -- pytest harness pinning Python to the Lean models
```

## The claim (what this does and does NOT prove)

**See `FINAL_REVIEW.md`** — the plan-§7 claim verbatim, cross-checked clause by
clause against the tree. Short form: the set-engine and graph-index **algorithms**,
as modeled in Lean at the level of `CORRESPONDENCE.md`, are proven to compute the
stratified perfect model and hence to be equivalent (machine-checked, axiom-audited;
set engine at full scope, graph index at the documented `W4Fragment` scope). The
**Python implementations** are pinned to those models by the correspondence map and
check-level differential conformance (98 tests, including the Lean operational graph
model vs the real graph index). Not yet earned: state-level conformance equality and
exhaustive small-scope enumeration. Residual unverified surface: the fragment carries,
the interner/bitmap representation layer, the SQL/transaction/concurrency layer,
non-stratifiable schemas, `expand`/`lookup`, and the fidelity of the model-to-code
correspondence itself.

**This never rounds up to "the code is formally verified."**

## Status

See `HANDOFF.md` (kept current every session). Snapshot 2026-07-12k: the tree is
**sorry-free and axiom-clean** (`bash formal/verify.sh` = build + 0 sorries + zcli +
axiom audit + 98 conformance tests, all green). T0a/T0b/T1/T4 fully closed;
T2a/T2b/T3/T5/T6 closed over the operational closure `ReachedBy` at `W4Fragment`
scope (staged widening W1→W4 complete); Phase 6 hardening: graph-state conformance
mode, `CORRESPONDENCE.md`, and `FINAL_REVIEW.md` landed — state-level conformance
remains the open item.
