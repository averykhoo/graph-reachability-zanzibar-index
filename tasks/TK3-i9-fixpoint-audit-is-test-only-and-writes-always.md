---
id: TK3
title: I9 fixpoint audit is test-only and 'writes always cascade' is convention, not a check
pri: LATER
size: M
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-08-21b
updated: 2026-08-21b
closed:
---

`install_paranoia` (`index_v4/invariants.py::install_paranoia`) wires, at `level='full'`, the invariant checker plus the delta-scoped verifier — and at `level='residue'` only `check_residue_hygiene`. **`audit_fixpoint` is not among them**, deliberately: `invariants.py:184` says *"Not here, by design: I9 is the processor's fixpoint audit"*. Every I9 call site is a test. Second half, same gap: nothing structural forces `run_cascade` to run on a boolean write — cascade-as-precondition is convention, enforced by review and by `GraphBackend.apply` in the test harness, not by a checked invariant.

`formal/SEMANTICS.md:891-899` raises the escalation in as many words — *"do you want a Phase-7-style check that the write paths always cascade?"* — and it was never answered. `grep -n 'I9\|audit_fixpoint' HANDOFF.md` returns 0 hits.

The deliverable is the ADJUDICATION first (is the scope boundary accepted, or is a per-commit/per-write check wanted?), then whichever of the two it implies. Recording the accepted boundary is a real outcome; leaving the question open in a doc is not.

## Traps

⚠ **This is an assurance gap, so the fix is the thing most likely to fail by PASSING.** Read [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) BEFORE adding any check here — it is mandatory for exactly this class. A cascade-precondition check that cannot fire is worse than the convention it replaces, because it converts an acknowledged gap into a false green.

⚠ **Cost is the reason it is not already on.** I9 is a fixpoint audit; wiring it into every commit is not free, and `ZANZIBAR_PARANOIA=residue` exists precisely because the full tier is too expensive for production (~+5% on writes for the residue tier alone). Any proposal must state which TIER it lands in and what it costs.

## Read first

- [`formal/SEMANTICS.md`](formal/SEMANTICS.md)`:891-899` — item A1 and the unanswered escalation; also `:549-554`
- `index_v4/invariants.py::install_paranoia` — what the tiers actually wire (`:773-803`), and `:184` for the by-design exclusion
- `index_v4/processor.py::DeltaProcessor.audit_fixpoint` — the check itself
- `tests/parity.py:98` — the "paranoia dose" call site, one of the test-only ones
- [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) — mandatory before adding the check

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-3 (`SEM-A1`, tier 1, sweep-g only); CONFIRMED OPEN in code by COVERAGE.md §C3 against index_v4/invariants.py:773-803. The escalation at formal/SEMANTICS.md:898-899 is verbatim unanswered.
