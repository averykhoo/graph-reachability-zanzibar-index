---
id: TK52
title: the 2026-08-30 trial verdict -- two questions; the irreversible one is where TK findings live
brief:
pri: NEXT
size: S
deps: []
related: []
parent:
labels: [docs]
source: board
source_hash: 2928e2150c6b
created: 2026-08-29
moved: 2026-08-29b
updated: 2026-08-29b
closed: 2026-08-29b
---

The `tasks/` trial ends **2026-08-30**. Until this row existed, that deadline appeared in
`CLAUDE.md` prose, the three trial docs and the session log, and in **no tracked item on
either tree** -- no board row, no task file (re-verified 2026-08-29 by grep for
`2026-08-30` over `HANDOFF.md` and all 150 task files: zero hits). A deadline governing
both record systems was tracked by neither, which is its own finding about both. Filing it
on both trees discharges the `Still owed` line carried since 2026-08-24c
(`docs/history/session-log.md:435`).

## The verdict is TWO questions, not one

**(a) Does the query beat the file?** What the protocol's sections 1-7 measured. Reversible
either way.

**(b) If `tasks/` goes, where do the unranked `TK*` findings live?** Never posed
(`docs/tasktool-trial-protocol.md`, the 2026-08-24c append, T2). `CLAUDE.md`'s exit plan --
"delete `tasks/`, `scripts/task.py` and this bullet, which is one revert" -- bundles the
two, and understates (b): it is one revert for the *tool* and a deletion of findings for
the *repo*.

Answer (b) first: it is the irreversible half.

## What landed 2026-08-29, and what it does NOT settle

The open `TK*` findings were snapshotted into
`docs/history/tasktool-findings-2026-08-29.md` (FROZEN, dated), so a DELETE verdict is now
**non-destructive** and (a) can be decided on its merits. That file also carries the
measured census and the isolation table, which is where those figures live -- not here.

The snapshot makes DELETE *safe*. It does **not** decide which findings deserve promotion
to board rows, appending to a live doc, or an explicit write-off. **That adjudication is
this row's deliverable and it is still owed.**

## Traps

(!) **Do not read the snapshot as having answered (b).** Safe-to-delete and
decided-what-to-keep are different states. The third option -- deleting without choosing --
is the one taken by default if this row is closed on the strength of the snapshot alone.

(!) **Do not restate the finding counts in this body or in the board row.** They are
method-sensitive and already rotted once: the 2026-08-24c census said "49 open, 2 closed"
and was correct then; two ids closed the same day. The measured figures live once, in the
snapshot's own census section. This is the `HS-5`/`TK49` disease, and this row is exactly
the kind of place it recurs.

(!) **The trial's own instruments are spent -- do not plan a re-run.** The Q3 dye marker no
longer separates the arms, and re-minting a discrepancy means deliberately leaving one tree
stale, which the parallel-update contract forbids.

## Read first

- `docs/history/tasktool-findings-2026-08-29.md` -- the rescued findings, the census, and
  the isolation table
- `docs/tasktool-trial-protocol.md` -- section 6, newest append first; the 2026-08-29 entry
  is the state on the eve of the verdict
- `CLAUDE.md`, the "ON TRIAL 2026-08-23 -> 2026-08-30" bullet -- the exit plan whose wording
  bundles the two questions

## Log

### 2026-08-29

First reconciliation. Filed and given its HANDOFF.md board row in the same session, per the parallel-update contract; this stamps the row digest so any later board edit shows as drift.

Verdict input added at the user's request: a first-hand FRICTION LOG from one session of ordinary use is now docs/tasktool-trial-protocol.md section 6, append 2026-08-29, item A7 -- six observed items, including one that is this repo's house failure mode (ack on a --source hand task prints a success line, exits 0, and stamps nothing, so sync reports that task as drift forever while the operator is told it is acked). Sections 1-7 measured READING cost and never measured the cost of OPERATING the tool, which is the recurring price if it graduates; A6 and A7 are the only evidence on that, and both are one session deep.

### 2026-08-29b

Question (b) DECIDED and recorded: docs/history/tk-findings-adjudication-2026-08-29.md buckets every open TK* id -- 5 written off against a named living carrier, 3 discharged this session (TK48 corrected, TK51 already implemented, TK49 landed into docs/README.md sec 2), the rest APPEND with a named destination. Method: nine-way live-tree fan-out, then an independent refutation pass on every proposed write-off, which OVERTURNED 6 of 11 -- so a single-pass adjudication would have written off six findings having no living carrier. The unlanded appends are carried by new board row TK53, not left as a residual with no owner (the TK11 defect). Question (a), does the query beat the file, is deliberately NOT decided here: deleting tasks/ and scripts/task.py is the user's call and the recommendation is in the ledger.
