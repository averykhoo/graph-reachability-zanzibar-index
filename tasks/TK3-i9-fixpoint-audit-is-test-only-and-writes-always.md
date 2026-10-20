---
id: TK3
title: nothing checks that a boolean-schema write ran run_cascade (bare WildcardIndex API)
brief: 0.1.0 BLOCKER: build the always-on O(1) cascade-ran mark before the API freeze; keep WildcardIndex public
pri: NEXT
size: M
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-08-21b
moved: 2026-10-20b
updated: 2026-10-20b
closed:
---

`install_paranoia` (`src/zanzibar/graphindex/invariants.py::install_paranoia`) wires, at `level='full'`, the invariant checker plus the delta-scoped verifier — and at `level='residue'` only `check_residue_hygiene`. **`audit_fixpoint` is not among them**, deliberately: `invariants.py:184` says *"Not here, by design: I9 is the processor's fixpoint audit"*. Every I9 call site is a test. Second half, same gap: nothing structural forces `run_cascade` to run on a boolean write — cascade-as-precondition is convention, enforced by review and by `GraphBackend.apply` in the test harness, not by a checked invariant.

`formal/SEMANTICS.md:891-899` raises the escalation in as many words — *"do you want a Phase-7-style check that the write paths always cascade?"* — and it was never answered. `grep -n 'I9\|audit_fixpoint' HANDOFF.md` returns 0 hits.

The deliverable is the ADJUDICATION first (is the scope boundary accepted, or is a per-commit/per-write check wanted?), then whichever of the two it implies. Recording the accepted boundary is a real outcome; leaving the question open in a doc is not.

## Traps

⚠ **This is an assurance gap, so the fix is the thing most likely to fail by PASSING.** Read [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) BEFORE adding any check here — it is mandatory for exactly this class. A cascade-precondition check that cannot fire is worse than the convention it replaces, because it converts an acknowledged gap into a false green.

⚠ **Cost is the reason it is not already on.** I9 is a fixpoint audit; wiring it into every commit is not free, and `ZANZIBAR_PARANOIA=residue` exists precisely because the full tier is too expensive for production (~+5% on writes for the residue tier alone). Any proposal must state which TIER it lands in and what it costs.

## Read first

- [`formal/SEMANTICS.md`](formal/SEMANTICS.md)`:891-899` — item A1 and the unanswered escalation; also `:549-554`
- `src/zanzibar/graphindex/invariants.py::install_paranoia` — what the tiers actually wire (`:773-803`), and `:184` for the by-design exclusion
- `src/zanzibar/graphindex/processor.py::DeltaProcessor.audit_fixpoint` — the check itself
- `tests/parity.py:98` — the "paranoia dose" call site, one of the test-only ones
- [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) — mandatory before adding the check

## Log

### 2026-08-21b

**Provenance.** COVERAGE.md PART 1 U-3 (`SEM-A1`, tier 1, sweep-g only); CONFIRMED OPEN in code by COVERAGE.md §C3 against src/zanzibar/graphindex/invariants.py:773-803. The escalation at formal/SEMANTICS.md:898-899 is verbatim unanswered.

### 2026-09-10

LANDED 2026-09-10 (TK53 append). The statement now lives in `formal/README.md`, appended to the "Residual unverified surface:" paragraph in "## The claim (what this does and does NOT prove)": the I9 cascade precondition is a CONVENTION, `install_paranoia` wires the checker and the delta-scoped verifier but not I9, and `SEMANTICS.md` sec 11-A1 flags it as wanting sign-off that was never given.

Verified first-hand before writing, not taken from the agent report: `src/zanzibar/graphindex/processor.py::DeltaProcessor.audit_fixpoint` is defined at :1658 and EVERY call site is under `tests/` (parity.py:98, test_connectedstore*.py, test_connectedstore_concurrency.py:145) -- no production caller. `invariants.py:184` states the exclusion by design. `SEMANTICS.md` sec 11 is at :902 and A1 at :907 (the row's own `## Read first` cites :891-899, which is 16 lines stale -- lint check 14 resolves pointers, not line numbers, so it stays green).

Not closed: the row is still the open question of whether a per-write check is wanted. What changed is that the STATEMENT is no longer sole-homed in `tasks/`.

### 2026-10-04g

Closability sweep 2026-10-04g (agent report, UNVERIFIED first-hand unless marked; the session did not act on it): PARTLY SUPERSEDED. TK82 shipped the per-cascade fixpoint tier (src/zanzibar/graphindex/invariants.py PARANOIA_FIXPOINT), so 'I9 is test-only' no longer holds for the execution-side class. Remaining: 'writes always cascade' is still a convention (src/zanzibar/connectedstore/apply.py always cascades on the composed path); the never-scheduled class is TK85. Merge with TK85 or narrow this row to the convention half.

### 2026-10-13

NARROWED + A1 DECIDED 2026-10-13 (assurance triage, lane L3). Under CLAUDE.md 'Who decides' (2026-09-12b), the model decides; this is no longer waiting on the user.
SCOPE NOW: only the cascade-precondition half. On a boolean schema, nothing checks that a graph write ran DeltaProcessor.run_cascade in the same transaction. The I9 'test-only' half is MOVED to TK85. TK82's opt-in 'fixpoint' tier (src/zanzibar/graphindex/invariants.py::PARANOIA_FIXPOINT -> DeltaProcessor._check_cascade_fixpoint, called at the end of run_cascade) covers execution-side misses inside a cascade that RAN. The never-SCHEDULED class (DeltaProcessor.audit_fixpoint, still 0 production callers) is TK85's.
EVIDENCE (READ 2026-10-13):
- The composed path always cascades: src/zanzibar/connectedstore/apply.py::advance_index calls run_cascade when a processor exists.
- The exposure is the bare exported API: src/zanzibar/graphindex/__init__.py exports WildcardIndex, and a caller on a boolean schema must construct and run DeltaProcessor itself.
- No paranoia tier sees a cascade that was never called. The fixpoint tier runs INSIDE run_cascade, and check_invariants excludes I9 by design (invariants.py::check_invariants docstring, :239 as of 2026-10-13).
DECISION A1: (1) The proof scope boundary is ACCEPTED: Lean cannot speak to Python call discipline, so baking the cascade into each modelled write op is the faithful model. (2) A cascade-ran CHECK IS WANTED. A skipped cascade makes the graph index silently disagree with the set engine on a public API, and CLAUDE.md prefers a mechanical refusal over a doc convention.
INTENDED SHAPE (REASONED, unbuilt): O(1), always-on, outside the paranoia ladder (it costs ~nothing, so tiering it would only let it be off). It is a per-session 'cascade owed' mark, set by a WildcardIndex write when the ruleset has compiled plans, cleared by run_cascade and by DeltaProcessor.backfill, and asserted clear in a before_commit hook.
TRAPS:
(a) Do NOT use 'outbox head == drained frontier'. The cascade's own reconcile-time GC emits outbox rows late (tests/test_tk79_outbox_replica.py pins three sites), so that comparison is REASONED to misfire.
(b) The mark catches 'never called', not 'called with a too-high watermark'. State that bound in the docstring.
(c) Tests that corrupt state on purpose, or write without cascading (the TK74 staleness tests are likely), need an explicit opt-out. Census them FIRST.
(d) Sabotage per docs/sabotage-procedure.md: drop the clear in run_cascade -> every boolean write must go red; drop the hook -> the no-cascade witness must go red.
DOCS FIXED this session: formal/README.md residual paragraph (no longer says I9 has no runtime tier; names the WildcardIndex exposure and TK85), formal/SEMANTICS.md sec 7.7 (dated correction naming the TK82 tier), sec 7.8 (re-checked note), sec 11 header + A1 (decision recorded in place). The row's Read-first line numbers are stale: SEMANTICS sec 11-A1 is now ~:933-960 and invariants.py's 'Not here, by design' is now :239 (2026-10-13).
NEXT ACTION: census the tests/ and formal/conformance/ call sites that write to a WildcardIndex on a boolean schema without run_cascade/backfill in the same transaction. Record the census in a tracked ACTIVE-PLAN doc before wiring the mark. Size stays M.

### 2026-10-13d

Sprint re-rank 2026-10-13d (user-approved in chat): stays LATER, first in line after HS-5 when a NEXT slot frees. TK3 gave its slot to TK123 (user put the rename in NEXT); P21 gave its slot to TK138.

### 2026-10-20b

0.1.0 BLOCKER (user, 2026-10-20b, in chat). WildcardIndex is public (src/zanzibar/graphindex/__init__.py::__all__), so on a boolean schema a caller who skips DeltaProcessor.run_cascade after a write silently diverges the graph index from the set engine, and only a doc line guards the project primary rule (equivalence). 0.1.0 freezes the API, so this lands before the cut. DECISION (model, under Who decides): build the O(1) per-transaction cascade-ran mark already chosen on 2026-10-13, ALWAYS ON (no paranoia tier), refusing the commit when a boolean-schema write ran no cascade; keep WildcardIndex exported. Rejected alternative: drop WildcardIndex from the public exports. It removes the exposure only for top-level importers (the module path stays importable), takes away the low-level API before anyone has asked for that, and leaves the gap unchecked for Store internals too. Mandatory: docs/sabotage-procedure.md, sabotage (delete the run_cascade call in a test write path) and watch it go red before believing it. Next action: find the transaction boundary the mark hangs on (WildcardIndex write paths vs Session commit) and write the plan doc.
