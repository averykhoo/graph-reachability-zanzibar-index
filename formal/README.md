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
  CORRESPONDENCE.md  -- Lean def ↔ Python file:line map (Phase 6, not yet written)
  verify.sh          -- the one-command green gate
  lean/              -- the Lean 4 development
  conformance/       -- pytest harness pinning Python to the Lean models
```

## The claim (what this will and will NOT prove)

When complete, the honest claim is: the set-engine and graph-index **algorithms**,
as modeled in Lean at the level of `CORRESPONDENCE.md`, are proven to compute the
stratified perfect model and hence to be equivalent (machine-checked, axiom-audited).
The **Python implementations** are pinned to those models by structural correspondence
review, six-way differential conformance including state-level equality, and
exhaustive small-scope enumeration. Residual unverified surface: the interner/bitmap
representation layer, the SQL/transaction/concurrency layer, non-stratifiable schemas,
`expand`/`lookup`, and the fidelity of the model-to-code correspondence itself.

**This never rounds up to "the code is formally verified."** See the plan's §7
honesty clause; the final report will use its wording verbatim.

## Status

See `HANDOFF.md` (kept current every session). Snapshot 2026-07-11: the tree is
**sorry-free and axiom-clean** (`bash formal/verify.sh` = build + 0 sorries + axiom
audit + 60 conformance tests, all green). T1/T0a/T0b/T4 fully closed; T2/T3/T5/T6
proved at staged fragment scope — W1 (wildcards) and W2 (rule routing) closed
end-to-end, W3a (derived booleans) in flight; W4 (full scope) and Phase-6 hardening
remain.
