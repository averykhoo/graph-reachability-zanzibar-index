---
id: TK98
title: session-log receipt vocabulary cannot express 'entered via show'
brief: a session had to write the nearest FALSE token with a caveat; observed 2026-09-07b
pri: LATER
size: S
deps: []
related: [TK97]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-22
moved: 2026-09-22
updated: 2026-09-22
closed:
---

The session-log receipt vocabulary has no token for "entered via `show`".
`handoff_lint.py::check_session_receipt` requires the newest ledger entry to carry
`read: board only` or `read: board + note` -- an honest self-report of what the session
actually read to start work. Neither token is true of a session that entered directly at
`task.py show <id>` on a user instruction, skipping `board`.

FIRST OBSERVED 2026-09-07b, when a session entered at `show TK57` and had to write the
nearest FALSE token with a caveat beside it. A receipt whose vocabulary cannot express the
truth teaches sessions to write something untrue and annotate around it -- which destroys
the one measurement the receipt exists to take: whether the bounded query actually REPLACED
the file read.

Either extend the vocabulary (`read: show <id>`, or `read: none`) or decide deliberately
that the two tokens are exhaustive and say why on this row. Carried in `HANDOFF.md`'s
`## Still owed` from 2026-09-07b to 2026-09-22 as "Unfiled", which is 15 days in a section
that has no checker; filed here by the 2026-09-22 disposition.

## Traps

- (!) **Widening the vocabulary widens what passes.** The check's value is that an
  unreadable-honest answer is impossible; a third token that means "I read something else"
  makes every future receipt weaker. Decide what the measurement IS before adding a token.
- (!) **Sabotage it** (`docs/sabotage-procedure.md`): whatever token is added, an entry
  missing ALL tokens must still turn `verify.sh lean` RED.

## Read first

- `scripts/handoff_lint.py::check_session_receipt` -- the check and its current two-token
  vocabulary.
- [`../docs/history/session-log.md`](../docs/history/session-log.md) -- header, "Two literal
  receipt lines"; and the `2026-09-07b` entry, which is the first observation.
- [`../docs/README.md`](../docs/README.md) sec 7 step 1 -- where the receipt is specified.

## Log
