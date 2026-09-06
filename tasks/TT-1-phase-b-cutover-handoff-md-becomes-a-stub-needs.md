---
id: TT-1
title: Phase B cutover -- HANDOFF.md becomes a stub; needs an explicit user go
brief: Landing this IS the trial's question-(a) verdict -- one commit, revert line in the message, explicit user go only
pri: LATER
size: M
deps: []
related: []
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-08-29d
moved: 2026-09-06b
updated: 2026-09-06b
closed:
---

Phase A of `docs/tree-sole-authority-spec-2026-08-29.md` is LANDED (2026-08-29d): the
tool's suite is in the gate as `tests/test_tasktool.py`, the six A7 footguns are fixed and
sabotaged, `brief` + `tasks/BANNER.md` + `tasks/README.md` exist, and `handoff_lint.py`
resolves ledger row ids against the tree as well as the board. What remains is **Phase B,
the cutover**, and it is gated on an explicit user go -- landing it IS the trial's
question-(a) verdict (keep tree / retire board), so it must not happen as a side effect.

## Traps

⚠ **Phase B lands in ONE commit with the revert line in the commit message.** A partial
cutover leaves two half-authoritative trees, which is strictly worse than either.

⚠ **Until Phase B lands the dual-update contract in `CLAUDE.md` is IN FORCE** -- every
`HANDOFF.md` board edit gets the mirrored `task.py` op, same `--session` key.
`handoff_lint.py::check_ledger_row_ids` now FAILS when a board row has no task file, so
this is mechanical rather than remembered.

⚠ **`sync`/`ack`/`source_hash` retire WITH the board.** Their tests flip to expect the
retirement refusal; they are not deleted. `sync_sabotage.py` (14 cases) and
`sync_accept.py` (57 assertions) were never ported out of `.scratch/` on the grounds that
`sync` is scheduled for retirement -- **if the cutover does not happen, that gap is real**
(recorded in `docs/history/tasktool-proof-2026-08.md`).

## Read first

- [`docs/tree-sole-authority-spec-2026-08-29.md`](docs/tree-sole-authority-spec-2026-08-29.md) section 2 -- the Phase B checklist, and section 3, the pre-registered week-two measurement
- [`docs/tasktool-trial-protocol.md`](docs/tasktool-trial-protocol.md) section 6 A7 + its 2026-08-29d resolution table
- [`docs/history/tasktool-proof-2026-08.md`](docs/history/tasktool-proof-2026-08.md) -- what was sabotaged and what was not

## Log

### 2026-08-30

Trial window EXTENDED to 2026-09-06 and DELETE taken off the table (user, 2026-08-30). This row is unchanged in substance -- Phase B still needs an explicit go and is still the question-(a) verdict -- but the question it answers narrowed from keep-or-delete to cutover-or-keep-both. Its third trap (the unported sync suites) is now filed as its own row, TT-2, because the ground it rested on -- 'sync retires at cutover' -- expired with the extension.

### 2026-09-06b

2026-09-06b measurement (no decision; user deferred the authority call). Read tally by script over docs/history/session-log.md, per session entry: 35 trial-window entries, 27 'board + HANDOFF', 6 'board only', 0 'HANDOFF only' self-reports, 2 entries without a read line (2026-08-24, 2026-08-30c). sync --check at session start: 9 BODY drifts (P6 R6 P4 P5 P14 TK55 TK54 P21 DW-1) -- P6's tree brief still said 'NOT parallel-safe with P3' a session after the board said P3 LANDED; three were unackable (source: hand with a board row; op_ack refuses, task.py:3175). All nine reconciled, sync CLEAN, lint clean. Phase B-prime candidate (tree authoritative, HANDOFF.md a one-hop note) drafted as the dated 2026-09-06 amendment at the top of docs/tree-sole-authority-spec-2026-08-29.md, sections (i)-(vi), with the prerequisites sized. Retired-ids parity checked: all 14 named Closed ids resolve to tasks/closed/, ZT-* covers 36 closed files + ZT-P5 open on HOLD; counts' '0 retired' is retired-ids.txt being deliberately empty, not a gap.
