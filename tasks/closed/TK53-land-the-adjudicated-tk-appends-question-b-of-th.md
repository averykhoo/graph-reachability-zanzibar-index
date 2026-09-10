---
id: TK53
title: land the adjudicated TK* appends — question (b) of the trial verdict is DECIDED (
brief: 15 appends remain; until they land, deleting tasks/ drops statements no living doc carries. Re-verify each row
pri: NEXT
size: M
deps: []
related: []
parent:
labels: []
source: board
source_hash: 045f47f3553e
created: 2026-08-29b
moved: 2026-09-10
updated: 2026-09-10
closed: 2026-09-10
---

Question (b) of the trial verdict is decided and recorded in
[`tk-findings-adjudication-2026-08-29.md`](docs/history/tk-findings-adjudication-2026-08-29.md):
every open `TK*` id is bucketed. Five are written off against a named living carrier, three
were discharged in the deciding session (`TK48` corrected, `TK51` found already
implemented, `TK49` landed into `docs/README.md` §2), and the rest are **appends**: one
statement each, with a named destination doc, that exists nowhere but `tasks/`.

**Work the table in the adjudication file.** Each row names the destination and what is
missing there; the prose is written against the live doc when it lands, never copied from
the table. The heaviest concentration is `docs/perf-round6-audit-2026-08.md` (the appendix
leads and their cross-links) and `docs/latent-gaps.md` (the unmodelled-surface findings,
which belong in its "Latent, but owned by another doc" section).

## Traps

⚠ **Rows are not equal and some are already stale.** `TK45` is flagged in the file as a
probable CLOSE, not an append — both its residuals appear to have landed since it was
filed, exactly as `TK51`'s had. **Re-verify each row against the live tree before writing
it**; the underlying snapshot's own header says its citations were copied verbatim and
never re-checked, and `TK51` is the proof that at least one finding outlived its defect.

⚠ **`formal/CORRESPONDENCE.md` destinations are gate-anchored.** `verify.sh lean` resolves
every `file::symbol` anchor in that file, so an append naming a symbol that does not
resolve turns the gate red. Land those rows with a `lean` run, not on inspection.

## Read first

- board pointer: [adjudication](docs/history/tk-findings-adjudication-2026-08-29.md)) and the appends are the unlanded half. Each is a statement that exists only in `tasks/` and has a named destination in a living doc. ⚠ **This row is what makes DELETE lossless** — until it closes, deleting `tasks/` drops statements that no living doc carries. `TK52` closed on the decision; this carries the execution, so the decision is not a residual with no owner

 the adjudication file's table and its "Method" section (which records that
the adversarial pass overturned 6 of 11 proposed write-offs — the reason a single-pass
sweep of the remainder is not good enough), then
[`tasktool-findings-2026-08-29.md`](docs/history/tasktool-findings-2026-08-29.md) for the
finding text itself, then the destination doc.

## Log

### 2026-08-29b

Item block compressed to a pointer in the same session it was filed: the four traps and the disposition table live in docs/history/tk-findings-adjudication-2026-08-29.md, per docs/README.md sec 1 (one home per statement) and sec 4's defined trap-overflow move. HANDOFF.md was over its 260-line ceiling and its 10-badge trap budget on first write; both are clean now, and the ceiling was NOT raised.

Row and block rewritten at end of session 2026-08-29c to record progress (22 landed, 15 remain) and to carry the re-verify trap onto the board itself, since that trap earned its place: re-verification overturned rows in BOTH directions. Also re-flowed to keep HANDOFF.md at its 260-line ceiling without raising it.

### 2026-09-10

CLOSED 2026-09-10. All 15 remaining appends are dispositioned, and `tasks/` no longer sole-homes any of the statements -- which is precisely what this row existed to achieve ("until it closes, deleting tasks/ drops statements that no living doc carries").

Scout reproduced the count independently before any work: the adjudication file's APPEND table has 42 rows, set-differenced against the tree gives exactly 15 still open, matching the "15 remain" figure recorded on 2026-08-29c.

11 LANDED: TK3 (formal/README.md), TK4 + TK35 + TK36 (docs/spec-deviations.md), TK11 (perf-round6-audit), TK28 (perf-next-round), TK38 + TK50 (formal/CORRESPONDENCE.md), TK39 (root README.md), TK43 (docs/README.md), TK44 (docs/sabotage-procedure.md).
3 NOT APPENDS, already carried: TK15, TK33, TK34 -- writing them would have created a second home.
1 SUPERSEDED: TK6, whose destination (a P4 board row in HANDOFF.md) was abolished by the 2026-09-06 cutover.

TK35 and TK36 were RE-HOMED from `docs/specs/wildcard-materialization-spec.md` to `docs/spec-deviations.md`. `docs/README.md:122-124` holds `docs/specs/` frozen at landing BY HAND -- nothing walks it -- so an append there looks legal and is not. Per-row reasoning is on each row.

The re-verify trap on this row was the load-bearing part and it fired hard. Every one of the eleven drafted appends carried at least one factual defect, and FOUR verdicts were overturned between the two passes (TK4 and TK50 from already-carried to append, TK44 from already-carried to append, TK6 to superseded). Defects caught before writing included: a claim that `install_paranoia` is not wired into `ConnectedStore` (it is, `store.py:193` -- the true statement is that DEFAULT_PARANOIA is OFF), a severity error calling the BL-1 leak an answer-level bug (it is recorded STATE-ONLY, explicitly not a fail-open), a mis-description of what spec sec 10 conditions its non-goal on, and a link form already known to resolve to the wrong file. A single-pass sweep would have written all of them.

The adversarial pass was itself wrong once, which is why nothing here was transcribed: it claimed perf lead A10 rewrites the `_bumped` fan-out. The audit (:857-862) says A10 routes onto `_reconcile_subject`, a different sec 7 gap. The weaker accurate claim is what landed.

TK44 turned up a live ZT-P3-5 recurrence in the process: `tests/test_generator_coverage.py:68` (~19%) and `:428` (~28%) state the same measurement with identical wording and different values, inside one module, and `check_restated_counts` cannot see it (wrong file type, wrong pattern). Recorded in the landed text.

Not done here, deliberately: the individual TK rows stay OPEN. Landing a statement into a living doc discharges the SOLE-HOME problem, not the underlying question -- several of these rows (TK4's hook adjudication, TK34's canary decision, TK44's residue question) are undecided work that belongs to a human. Closing them is a backlog call, not a consequence of this row.
