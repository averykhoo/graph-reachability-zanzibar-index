# formal/ — machine-checked correctness for the two backends

This directory holds the formal-verification effort for the set engine and graph
index: a Lean 4 proof that both compute the stratified-Datalog¬ perfect model of
`(schema, tuples)` — hence are equivalent — plus a conformance harness pinning the
Python implementations to the proven models.

## Orientation (which doc for what)

The effort is **complete**. The four durable docs point:

1. **`ARCHITECTURE.md` — the topical map.** The durable, timeline-free architecture
   of the formal development: the trust root, the two backend models, the theorem
   table + scopes, how Python is pinned, and the honest residual surface. Start here
   for "how does it all fit together".
2. **`HANDOFF.md` — the state of the world.** Compact entry point: the theorem
   table, house rules, build/verify commands, and the remaining (optional) extras.
3. **`FINAL_REVIEW.md` — the exact claim.** The plan-§7 claim verbatim,
   cross-checked clause by clause. Authoritative; nothing may claim more than it.
4. **`SEMANTICS.md` — the trust root.** The specification (`sem`): domain, AST,
   well-formedness, the `sem` fixpoint semantics, both backend models, and the exact
   theorem hypotheses. Everything downstream proves things *about this document*.
   `CORRESPONDENCE.md` is the Lean-def ↔ Python-file:line map alongside it.

For provenance — the append-only session ledger, the staged-widening designs, and the
early digest — see [`history/`](./history/README.md) (`PROOF_STATUS.md`, `ROADMAP.md`,
`REVIEW.md`). The original full plan is `../docs/formal-verification-plan.md`.

## Layout

```
formal/
  README.md          -- this file
  ARCHITECTURE.md    -- the durable topical map of the formal development
  HANDOFF.md         -- session entry point (state + rules + build/verify)
  SEMANTICS.md       -- the spec / trust root
  CORRESPONDENCE.md  -- Lean def ↔ Python file:line map (the audit backbone)
  FINAL_REVIEW.md    -- the final claim (plan §7 verbatim + clause cross-check)
  verify.sh          -- the one-command green gate
  history/           -- provenance archive (see history/README.md):
                        PROOF_STATUS.md · ROADMAP.md · REVIEW.md
  lean/              -- the Lean 4 development
  conformance/       -- pytest harness pinning Python to the Lean models
```

## The claim (what this does and does NOT prove)

**See `FINAL_REVIEW.md`** — the plan-§7 claim verbatim, cross-checked clause by
clause against the tree; **see `ARCHITECTURE.md`** for the topical breakdown. Short
form: the set-engine and graph-index **algorithms**, as modeled in Lean at the level
of `CORRESPONDENCE.md`, are proven to compute the stratified perfect model and hence
to be equivalent (machine-checked, axiom-audited; set engine at full scope, graph
index at the documented `GraphAdmission ∧ W4Fragment` scope). The **Python
implementations** are pinned to those models by the correspondence map, five-corner
differential conformance (including the Lean operational graph model vs the real
graph index), **state-level equality under six documented projections**,
**exhaustive small-scope enumeration** up to tiny documented bounds, a
**remove-path answer gate** (the driven set engine AND the driven graph index vs
`sem` × oracle on the final store, plus driven == a fresh build at state level;
both Python remove paths pinned, only the Lean remove legs open),
and a **generated-schema answer gate** (seeded generated schemas outside the
curated corpora, spec-side only) — 248 tests, 20 of them gate-tooling unit tests
rather than comparisons.
Residual unverified surface: the fragment carries, the compiler artifacts, the
interner/bitmap representation layer, the SQL/transaction/concurrency layer,
non-stratifiable schemas, `expand`/`lookup`, and the fidelity of the model-to-code
correspondence itself.

**This never rounds up to "the code is formally verified."**

## Status

See `HANDOFF.md` (kept current every session). The arc is **complete**: the tree is
**sorry-free and axiom-clean**, and `bash formal/verify.sh` (the one-command,
fail-closed gate) is green — `lake build` + 0 sorries + zcli preflight + axiom audit
(412 `#print axioms` reports, one per audited theorem, only
`[propext, Classical.choice, Quot.sound]`) + **248
conformance tests, 0 skips**. T0a/T0b/T1/T4 fully closed; T2a/T2b/T3/T5/T6 closed over
the operational closure `ReachedBy` at `GraphAdmission ∧ W4Fragment` scope (staged
widening W1→W4 complete). Phase 6 hardening complete: the graph-state conformance
mode, `CORRESPONDENCE.md`, `FINAL_REVIEW.md`, **state-level conformance**,
**exhaustive small-scope enumeration**, the **remove-path answer gate**, and the
**generated-schema answer gate** all landed. What remains is optional
assurance-widening (fragment widening, Lean/graph-side remove legs, wider
bounds — `FINAL_REVIEW.md` §4; the once-pinned lookup-gate divergence was fixed
2026-07-13 Python-side, `FINAL_REVIEW.md` §3's resolved note).
