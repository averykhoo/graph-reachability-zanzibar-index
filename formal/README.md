# formal/ — machine-checked correctness for the two backends

This directory holds the formal-verification effort for the set engine and graph
index: a Lean 4 proof that both compute the stratified-Datalog¬ perfect model of
`(schema, tuples)` — hence are equivalent — plus a conformance harness pinning the
Python implementations to the proven models.

## Orientation (read in this order)

1. `../docs/formal-verification-plan.md` — the full plan: strategy, phases, process
   rules, risk register. Written before the build; the executable contract.
2. `PROOF_STATUS.md` — living status: current phase, resume point, theorem/`sorry`
   ledgers, adjudications, and the variations log. **Read this to know where things
   stand.**
3. `SEMANTICS.md` — the Phase-0 specification (the trust root): the domain, AST,
   well-formedness, the `sem` fixpoint semantics, both backend models, the exact
   theorem hypotheses, and the open ambiguities. Everything downstream proves things
   *about this document*.

## Layout (created as phases proceed)

```
formal/
  README.md          -- this file
  SEMANTICS.md       -- Phase 0 spec (done)
  PROOF_STATUS.md    -- living status (done)
  CORRESPONDENCE.md  -- Lean def ↔ Python file:line map (Phase 4)
  lean/              -- the Lean 4 development (Phase 1+)
  conformance/       -- pytest harness pinning Python to the Lean models (Phase 2+)
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

Phase 0 complete; awaiting user sign-off on `SEMANTICS.md` (especially the §11
ambiguities). No Lean written yet; toolchain not yet installed (needs user
permission per repo rules).
