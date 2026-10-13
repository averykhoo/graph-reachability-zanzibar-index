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
moved: 2026-10-13
updated: 2026-10-13
closed: 2026-10-13
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

### 2026-10-13

LANDED 2026-10-13 (batch lane L4a). DECISION: the `read:` receipt measures the session's ENTRY POINT, meaning which bounded surface it started from. There are three sanctioned ones: the board query alone, the board plus the note, or a named row's `task.py show` because the user assigned the work (CLAUDE.md: a user-assigned task overrides the ranking). With two tokens, the third legitimate entry had no true answer. CENSUS (READ, docs/history/session-log.md): 4 of the 10 entries from 2026-10-06 to 2026-10-12c wrote the nearest FALSE token and caveated it (2026-10-06, 2026-10-07, 2026-10-07d, 2026-10-08), plus the original 2026-09-07b. ADDED exactly one CLOSED token: `read: show <id>[, <id>]`. The ids must match the row-id shape (`handoff_lint.py::_READ_ID`, upper-case, `(?![\w-])` trailing guard) and must be KNOWN to the tree (open, closed or retired, via `_tree_ids`); a session may close the row it entered at. NOT added: `read: none`, and any continuation token (`same session as ...`). A continuation also entered by one of the three surfaces and writes that one. Every extra token weakens the receipt (the row's own trap). The token-less entry stays RED: pinned by `tests/test_handoff_lint_b_prime.py::test_read_show_token_is_closed` (8 near misses: `read: show`, `show <id>`, `show everything`, `show tk57`, `show TK57b`, `shown TK57`, `none`, `same session as 2026-10-07d`), by `::test_read_show_names_a_row_the_tree_knows`, and by the pre-existing `::test_receipt_is_red_when_either_line_is_missing_from_the_newest_entry`. Three show shapes were added to READ_SHAPES (green across all 6 lint shapes). SABOTAGE (first-hand 2026-10-13, temp-dir copy): R1 `_READ_ID` widened to `\S+` -> 5 FAILED (show <id> / everything / tk57 / TK57b + tree test). R2 unknown-id block disabled -> FAILED test_read_show_names_a_row_the_tree_knows. R3 the show alternative dropped from `_READ_RECEIPT` -> 19 FAILED (18 accepts_every_shape cases + tree test). docs/README.md sec 7 step 1 updated. Records stage 2026-10-13: the minted-shape placeholder id (TK + 999) in the handoff_lint.py comment (which reddened tests/test_tasktool.py::test_shipped_config_is_measured_not_an_example) was reworded to `<unknown id>`; the docs/history/session-log.md header (rules, not an entry) now lists the third token too. NOT done: CLAUDE.md "Start here" still names only the two old tokens; a CLAUDE.md edit is left to the owning session (docs/README.md sec 7 is the authoritative spec).
