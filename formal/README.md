# formal/ — machine-checked correctness for the two backends

This directory holds the formal-verification effort for the set engine and graph
index: a Lean 4 proof that both compute the stratified-Datalog¬ perfect model of
`(schema, tuples)` — hence are equivalent — plus a conformance harness pinning the
Python implementations to the proven models.

## Orientation (which doc for what)

The staged proof arc W1→W4 is **complete and green** — but "complete" here means *the
planned proof stages all landed*, not *the assurance question is closed*. Two things a
reader should know before trusting the word:

* **The final graph theorems are VACUOUS on the canonical boolean idiom**
  (`can_view: [user] but not blocked`). Not narrower coverage — no theorem there at all.
  `FullScope.lean:564` machine-checks that such a store fails
  `GraphAdmission.storeValid`. Read `FINAL_REVIEW.md` §3.0 / `ARCHITECTURE.md` §6.0
  before quoting anything graph-side.
* **A genuine model-vs-Python infidelity was found in the audited chain AFTER this
  directory was first described as "complete"** (2026-07-20b: Lean's `affectedKeys`
  lacked Python's LeafFamily own-key branch, yielding a modeled *drained* state with
  `check = true` and `sem = false`; fixed 2026-07-20c). Correspondence review is a
  sampling process, not a proof. `FINAL_REVIEW.md` §3 item 1 has the full account.

The four durable docs point:

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
`REVIEW.md`). The original full plan is `history/formal-verification-plan.md`.

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
to be equivalent (machine-checked, axiom-audited; set engine at **full scope** — the
equality is literally unconditional, all three hypotheses of `setEngine_correct` are
underscored and unused — graph index at the documented
`GraphAdmission ∧ W4Fragment` scope, **which is vacuous on `Direct`-arm derived
stores, `FINAL_REVIEW.md` §3.0**). The **Python
implementations** are pinned to those models by the correspondence map, five-corner
differential conformance (including the Lean operational graph model vs the real
graph index), **state-level equality under six documented projections**,
**exhaustive small-scope enumeration** up to tiny documented bounds, a
**remove-path answer gate** (the driven set engine AND the driven graph index vs
`sem` × oracle on the final store, plus driven == a fresh build at state level;
both Python remove paths pinned, and the Lean remove leg now CLOSED at the
validly-stored + drained-prior scope (2026-07-19f) and DRIVEN end-to-end by the Exec
driver / zcli op stream (2026-07-19, `graphRunOps` / `test_conformance_remove_graph.py`)
— driven over every in-fragment corpus **except `direct_arm_exclusion`**, which
`_REMOVE_EXCLUDED` skips because the remove guard fail-closes on Direct-arm stores —
its validly-stored scope decision approved by Avery 2026-07-19),
and a **generated-schema answer gate** (seeded generated schemas outside the
curated corpora, spec-side only). Gate size as last measured (**2026-07-27**, by
`pytest formal/conformance/ -q --collect-only`): **391** conformance tests collected,
46 of them gate-tooling unit tests (`test_sorry_scan.py`, `test_runner_retry.py`)
rather than comparisons. Re-measure; nothing pins these numbers except the `-ge`
floors in `verify.sh`.
Residual unverified surface: the fragment carries, the compiler artifacts, the
interner/bitmap representation layer, the SQL/transaction/concurrency layer
(including the HA/multi-instance replica tailing), the **bulk build/backfill
constructor — the default `build_index` path, with no Lean model at all**,
non-stratifiable schemas, `expand`/`lookup`, and the fidelity of the model-to-code
correspondence itself. `FINAL_REVIEW.md` §3 is the full list and governs.

**This never rounds up to "the code is formally verified."**

## Status

See `HANDOFF.md` (kept current every session). The arc is **complete** in the sense set
out under "Orientation" above: the tree is
**sorry-free and axiom-clean**, and `bash formal/verify.sh` (the fail-closed gate;
agents run it **phased** per [`docs/gate-runbook.md`](../docs/gate-runbook.md) —
the one-shot exceeds the ~10-min command cap) is green — `lake build` + 0 sorries +
zcli preflight + axiom audit (**457** `#print axioms` reports, one per audited
theorem, only `[propext, Classical.choice, Quot.sound]`, measured 2026-07-27) +
**391** conformance tests collected (`conf-heavy` 80 + `conf-rest` the rest; floors
88 / 303), 0 skips, 0 xfails; `tests/` **728** collected (2026-07-27) — 744 with a
PostgreSQL DSN configured, since `tests/test_postgres_ha.py` is dropped at collection
without one. **Most of
these counts are measurements, not gate-enforced invariants** — re-measure rather
than trusting the numbers here, and never read a count as coverage
(`FINAL_REVIEW.md` header). What IS enforced, since the 2026-07-26/27 gate
hardening: `-ge` floors on the audit count (457), the conformance collection (391),
the `tests/` collection (728) and the scanned-`.lean`-file count (64); an **identity
pin** (`formal/audited_theorems.txt` — WHICH theorems are audited, not just how
many); a **statement pin** (`formal/headline_statements.txt` — what the 26 headline
theorems SAY, so `theorem graph_correct : True := trivial` fails instead of
building green); a suspicion check on an axiom-free headline theorem; a
`CORRESPONDENCE.md` anchor-resolution pin; and zero-tolerance
`skipped`/`xpassed`/`deselected` parsing with a declared xfail budget for `tests/`
only. See `docs/gate-runbook.md` §2. T0a/T0b/T1/T4 fully closed; T2a/T2b/T3/T5/T6 closed over
the operational closure `ReachedBy` at `GraphAdmission ∧ W4Fragment` scope (staged
widening W1→W4 complete). Phase 6 hardening complete: the graph-state conformance
mode, `CORRESPONDENCE.md`, `FINAL_REVIEW.md`, **state-level conformance**,
**exhaustive small-scope enumeration**, the **remove-path answer gate**, and the
**generated-schema answer gate** all landed. What remains is assurance-widening —
**"optional" is the plan's word, and for the `Direct`-arm fragment widening it is the
wrong word**: until that lands on the E chain the final theorems say nothing about
`can_view: [user] but not blocked` stores (`FINAL_REVIEW.md` §3.0, §4(c)). (Fragment
widening — the Lean
remove leg itself is DONE 2026-07-19f at the validly-stored + drained-prior scope and
DRIVEN end-to-end by the Exec driver 2026-07-19 (`graphRunOps`/`test_conformance_remove_graph.py`,
minus the `direct_arm_exclusion` exclusion),
its validly-stored scope decision approved by Avery 2026-07-19 —
wider bounds, and the two never-modeled surfaces: the bulk build/backfill constructor and
the multi-instance/HA layer — `FINAL_REVIEW.md` §3/§4; the once-pinned lookup-gate
divergence was fixed 2026-07-13 Python-side, `FINAL_REVIEW.md` §3's resolved note).
