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
moved: 2026-08-29d
updated: 2026-08-29d
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
