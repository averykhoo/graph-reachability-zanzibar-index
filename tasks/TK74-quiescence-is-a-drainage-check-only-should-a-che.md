---
id: TK74
title: quiescence is a DRAINAGE check only -- should a cheap per-write staleness check exist?
brief: TK73 fallout: I9 audit_fixpoint is the only correctness net and runs per-write ONLY under GraphBackend.post_op
pri: NOW
size: M
deps: []
related: [TK73]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-17
moved: 2026-09-18
updated: 2026-09-18
closed:
---

## What it is

`TK73` settled that the cascade's terminal assertion is a **drainage** check, not a
staleness check -- and after the fix it is a *fixpoint* assertion over the leftover keys
only, not over every derived key.

**The load-bearing observation (UNVERIFIED -- reported by a diagnosis verifier during
`TK73`, NOT reproduced first-hand; reproduce it before acting):** skipping a reconcile in
a *productive* round produced **2 wrong answers** against the oracle with **no raise from
either candidate fix**, paranoia off.

If that reproduces, the only real correctness net is I9 `audit_fixpoint`, which runs
per-write **only** under `tests/test_matrix.py::GraphBackend.post_op` -- i.e. in tests,
not in production. The question this row owns: should a cheap per-write staleness check
exist at all, and what would it cost?

## (!) Traps

- **(!) Reproduce the 2-wrong-answers claim FIRST.** It is the entire premise and it is
  unverified. If it does not reproduce, close this row rather than designing against it.
- **(!) Do not widen the settle pass into a full-store audit to "solve" this.** The settle
  pass is bounded at one extra reconcile per leftover key on purpose; making it O(store)
  per write trades a correctness gap for a performance cliff, and `audit_fixpoint` already
  exists for the full sweep.
- **(!) `ZANZIBAR_PARANOIA=residue` already exists** as the shipped runtime detector for
  the `ZT-P0-1` escalation class. Measure what it does and does NOT catch here before
  proposing a new knob -- the answer may be "widen paranoia", not "new check".

## Read first

- [`docs/tk73-cascade-quiesce-gc-2026-09-17.md`](../docs/tk73-cascade-quiesce-gc-2026-09-17.md)
  sec 7 -- where this question was raised and why it was left open.
- `index_v4/processor.py::DeltaProcessor.audit_fixpoint` -- the I9 net, and its cost shape.
- `index_v4/invariants.py` -- paranoia wiring and the sec 8.3 delta-scoped verifier.

## Log

### 2026-09-18

THE PREMISE REPRODUCES -- AND IT IS AN ASSURANCE GAP, NOT A LIVE BUG. Map: [`docs/tk74-staleness-net-2026-09-18.md`](../docs/tk74-staleness-net-2026-09-18.md) (ACTIVE-PLAN). 17-agent fan-out (6 angles, 2 adversarial skeptics each, 1 completeness critic) plus this session's own first-hand re-measurement of the two load-bearing numbers.

**(1) REPRODUCED.** Skipping one productive reconcile in a cascade round yields oracle divergences with no raise from the shipped settle pass, none from the rejected `rounds+1`, and none at ANY paranoia tier. Two independent probes, both instrument-controlled in both directions. The row's two-wrong-answers number lands exactly: seed 0 ordinal 18 and seed 2 ordinal 13 both give `div=2 raise=no` on both arms.

**(2) (!) BUT THE FLAG WAS WRONG AND I HAVE CORRECTED IT.** Two agents returned `is_wrong_answer_bug: true`; all four skeptics said false, and they are right -- every wrong answer required a deliberate monkeypatch, and the unmutated control arms are `divergences=0`. **The board's "Known live correctness bugs: 0" line STAYS AT 0.** Reconciled, not averaged (`CLAUDE.md` sec  Delegation).

**(3) MECHANISM, READ FIRST-HAND at `index_v4/processor.py:1628-1636`.** `leftover` has exactly two sources: outbox rows above the frontier, and `self._bumped` (sole append at `:1351`, INSIDE a reconcile). A reconcile that never runs writes nothing, emits nothing, bumps nothing -- so it cannot enter `leftover` by any path, and `self._settle = None; if not leftover: return` exits ABOVE both checks. Both candidate fixes are gated on the same outbox-derived set. This is not a defect in the `TK73` fix: that pass was aimed at work the cascade does not SCHEDULE, never at a scheduled reconcile that did not run.

**(4) THE DESIGN QUESTION IS NOW ANSWERED, and the answer is narrow.** Per-op `audit_fixpoint` raised at exactly the op of the first wrong answer in **8 of 8** divergent cases; end-of-run `audit_fixpoint` was **clean in 4 of 8**, because a later write re-reconciles the key and LAUNDERS the corruption. Staleness is often TRANSIENT and the wrong answers are served inside the window. **So "audit periodically" is not a design option** -- this row narrows to a per-write check or nothing. (Counts: the originating agent said 9/18 and 4/9; two skeptics independently measured 8/18 and 4/8. Use 8.)

**(5) (!) THE BOUND NOBODY NOTICED -- MEASURED FIRST-HAND, AND IT IS THE REAL DELIVERABLE.** A pytest plugin wrapping `_run_cascade` and reading `self._settle` in a `finally`, bucketed by `len(compiled.strata)`:

    run 1 (4 modules, 34 passed): 118 cascades -- 3 SETTLE_RAN, all strata=1
    run 2 (6 modules, 104 passed): 440 cascades -- 0 SETTLE_RAN; 415 of them strata>=2

**558 cascades, the settle pass executed on 3 (0.54%), all at `strata == 1`, all three inside the module written to make it run. It has NEVER been observed to execute on a multi-stratum schema.** INSTRUMENT CONTROL: run 1 moved BOTH arms, so run 2's zero is a measured zero from a live counter (the plugin prints an explicit INERT warning on a one-arm run, and run 2 printed it). Mechanical reason, READ: `::_map_deltas_to_keys` (`:1379`) routes a `DerivedFamily` object row through `::_fan_out` to its DEPENDENTS, never to its own key.

**This bounds (3).** Every skip experiment ran at `rounds` 1 or 2. The one shape where the settle pass could plausibly catch a skip -- skip a LOWER-stratum reconcile, let a higher stratum compute off stale input and emit rows that `_fan_out` maps BACK onto the skipped key -- was never driven. "Blind by construction" is proven only for the single-stratum case.

**NEXT ACTION (single):** one skipped-reconcile experiment on a multi-stratum schema -- `tests/fga_schemas/demorgans_law_2.fga` (6 strata) or `wildcard_userset_cross.fga` (4) -- skipping a reconcile in a NON-final stratum. Do that BEFORE designing any per-write check.

Spun out: `TK76` (a shipped pin's stated control is inert), `TK77` (the matrix/hypothesis campaign cannot reach the `_sync_entity_middles` surface), `TK78` (`bulk_backfill.py` unaudited; `backfill()` drops `_bumped`), `TK79` (the late-GC rows' own design justification is pinned by nothing). `TK3` demoted to LATER: its census question is answered in sec 3 of the doc (`audit_fixpoint` has zero production callers, READ).

(!) PROCESS: four of six agents detected a CONCURRENT WRITER mutating `index_v4/processor.py` (`_sk[:-1]`, a skip-the-last-key sabotage) at ~23:28-23:35 on 2026-09-17, reverted before I looked. It produced false readings in two agents' runs. Tree verified clean at HEAD 6c5b97c before and after; nothing from that window was committed. Rule earned, doc sec 7: pin a `git archive HEAD` export and check `git status --porcelain` before AND after any probe that matters.
