---
id: TK62
title: nothing checks the R6-N transcribed figures against the audit they came from
brief:
pri: LATER
size: M
deps: []
related: [TT-1]
parent:
labels: [infra]
source: docs/history/tasktool-scratch-archive-2026-09-07.md
source_hash:
created: 2026-09-07
moved: 2026-10-13
updated: 2026-10-13
closed: 2026-10-13
---

Thirteen open `R6-N` bodies carry measurements transcribed BY HAND out of
`docs/perf-round6-audit-2026-08.md`. Nothing checks the transcription, and nothing notices
when the audit is corrected.

This has already cost real fidelity: `R6-11`'s inflated "8x" was wrong in four places for a
week (it was a cProfile generator-resume artifact -- a `@contextmanager` records two counts
per `with` -- and the halving is now pinned at `benchmarks/profile_r6.py::_ctxmgr_entries`,
which refuses an odd ncalls). The corrected figure had to be propagated by hand to every
copy.

The durable fix proposed in `notes.md` "Still open" item 5 is the shape `verify.sh lean`
already uses for `CORRESPONDENCE.md`: resolve each `### R6-N` heading and each quoted
figure against the audit at lint time, and fail when one stops matching. It is not built,
and the record proposing it died with `.scratch/tasktool/`.

## Traps

- The anchor check in `verify.sh lean` guarantees that pointers RESOLVE, not that claims
  are TRUE. A figure check is the stronger thing and needs its own sabotage: change one
  digit in the audit and watch the gate go red.
- The audit itself carries a known internal contradiction -- its status banner says "ten to
  land, five declined" where its body lists eleven and four. Any check keyed on the banner
  rather than the verdict tables inherits that error.

## Read first

- [`docs/history/tasktool-scratch-archive-2026-09-07.md`](../docs/history/tasktool-scratch-archive-2026-09-07.md) section 5 item 7 and section 2.4
- `docs/perf-round6-audit-2026-08.md` -- the source of the transcribed figures

## Log

### 2026-09-07b

PLAN AGREED 2026-09-07b (user), not started. Batch 3 of the TK57-TK65 sweep.

THE FIGURE-EQUALITY CHECK IS DECLINED, and this is a decision, not a deferral. Reopen it
only with new information, and say what changed.

Why: the proposal was to diff each R6-N body figure against docs/perf-round6-audit-2026-08.md
at lint time. There is no machine-readable truth in that file to diff against. It is prose,
and it carries a known internal contradiction (banner says "ten to land, five declined",
body lists eleven and four) already filed as TK48. A check keyed on the banner inherits the
error; a check keyed on the verdict tables has to parse prose tables that no format pins. It
would be red on arrival or subtly wrong, and a check that is red on arrival is a check
someone deletes.

WHAT IS IN SCOPE INSTEAD, and it rides TK59 rather than being its own mechanism: each R6-N
body already cites the audit by section. Check 14 (see TK59) resolves the "### R6-N"
heading. That gets the property that actually protects a session -- the pointer resolves --
without asserting an equality nothing can adjudicate. Same limit as verify.sh lean has over
CORRESPONDENCE.md, stated honestly: pointers resolve, claims are not verified.

Also in scope and small: fix the audit banner contradiction while in the file (TK48).

IF figure-level assurance is wanted later, the right move is not a checker. It is to
regenerate the audit verdict tables from benchmarks/ output and DELETE the figures from the
task bodies, so there is one home and nothing to diff. That is a larger, separate task.

Evidence this matters is unchanged and stays on the record: R6-11 inflated "8x" was wrong in
four places for a week (a cProfile generator-resume artifact; the halving is now pinned at
benchmarks/profile_r6.py::_ctxmgr_entries, which refuses an odd ncalls).

### 2026-10-04g

Closability sweep 2026-10-04g (agent report, UNVERIFIED first-hand unless marked; the session did not act on it): PARTLY STALE. TK48 banner fix landed and the figure check was declined on the row. Its claim that check 14 resolves the ### R6-N heading is FALSE: scripts/task.py::check_read_first docstring says THE PATH ONLY, NEVER THE LINE. Serves only R6, deprioritized by the 2026-09-22c goal decision: demote candidate.

### 2026-10-13

CLOSED AS DECLINED 2026-10-13 (assurance triage, lane L3). The gap is real, but the work is obsolete. Re-verified first-hand (READ, 2026-10-13):
(1) The figure-equality check was DECLINED on this row on 2026-09-07b, with the user's agreement: the audit is prose and has no machine-readable truth to diff against.
(2) The in-scope substitute, check 14 resolving the `### R6-N` heading, was never built and cannot be built as written. scripts/task.py::check_read_first resolves THE PATH ONLY, NEVER THE LINE (docstring, task.py:3213 as of 2026-10-13). No figure or heading checker exists anywhere: the R6 mentions in scripts/task.py (:384, :1570, :3192) are docstring examples, and the ones in scripts/handoff_lint.py are id matching.
(3) The banner contradiction trap is fixed (TK48 closed). The motivating R6-11 incident is pinned at source by benchmarks/profile_r6.py::_ctxmgr_entries (:114), which refuses an odd ncalls.
(4) Perf is deprioritized (user goal 2026-09-22c). The 14 R6 rows are all LATER (11) or HOLD (3).
Building a checker over deprioritized rows would WIDEN the assurance surface for no live catch. Figures in R6-N bodies stay hand-copied and unchecked, and docs/perf-round6-audit-2026-08.md is authoritative over them. REOPEN ONLY IF perf round 6 is reactivated. Then do the shape this row already named: regenerate the audit verdict tables from benchmarks/ output and DELETE the figures from the task bodies, so there is one home and nothing to diff. Do not build a figure differ.
