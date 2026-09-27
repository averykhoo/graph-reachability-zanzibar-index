---
id: TK96
title: the ASK-* channel: questions only the user can answer, filed as rows
brief: decided with user 2026-09-22: ASK-* series, LATER by default; at NEXT the session must nag in chat
pri: NOW
size: M
deps: []
related: [TK97]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-22
moved: 2026-09-27c
updated: 2026-09-27c
closed:
---

The user needs a channel for work only THEY can do -- fact-finding, requirements gathering,
a priority call -- kept distinct from engineering work the model should simply decide
(`CLAUDE.md` sec "Who decides"). DECIDED 2026-09-22 WITH THE USER: file them as an
**`ASK-<n>` id series** in this tree via `task.py new --id ASK-1`. This needs NO schema
change -- `tasks/README.md` sec "Filing a task" already blesses out-of-series prefixes, and
`P` / `R6` / `B` / `N` / `HS` / `SD` / `GS` / `BL` / `AW` / `DW` / `LT` / `ZT` are precedent.

**The defaults the user set (2026-09-22):** an `ASK-*` row sits at `LATER` by default. If it
is pressing enough that the user must be reminded every session, it goes to `NEXT` -- and a
session that sees an `ASK-*` at `NEXT` must raise it with the user, in chat, at least once
that session. `NEXT` is capped at 3 (`handoff_lint.py::NEXT_MAX`,
`task.py::check_pri_budget`), so there are at most three standing nags and an ASK row
competes for those slots on the same terms as any other row. That cap is the feature: it
forces the same ranking argument.

**Why the tree and not a new section.** The tree is already the sole authority on open work
(2026-09-06 cutover), and a fact-finding request IS open work -- it just has a different
owner. Filing it as a row inherits permanent ids, a dated `## Log`, the `moved`-based
neglect warning, and `close -m` recording the ANSWER where it can be cited later.

**The composition is the real argument.** A blocked engineering row declares `deps:
[ASK-3]`; `task.py ready` then excludes it automatically, and `close ASK-3` sweeps the id
out of every `deps` cell (`docs/README.md` sec 7 step 3), so answering the question makes
the blocked work ready in one op. An ASK with no dependents is just a question; an ASK with
dependents is a hard blocker -- and the dep graph tells them apart with no new field.

Three pieces of build work:

1. `task.py asks` -- print open `ASK-*` rows, oldest first, with age in days.
2. One bounded footer line on `board`, matching the existing `ready ...` line:
   `asks   3 open, oldest 12 days   (python scripts/task.py asks)`.
3. The nag, made mechanical rather than remembered: extend
   `handoff_lint.py::check_session_receipt` to require a third literal line in the newest
   session-log entry -- `asked: ASK-3` or `asked: none` -- whenever any `ASK-*` sits at
   `NEXT`. Same shape as the existing `read:` receipt, and for the same reason: a receipt
   is the only way to find out whether the thing actually happened.

## Traps

- (!) **Do not let `ASK-*` become a dumping ground.** It is for facts only the user can
  supply and priorities only the user can set. An engineering call the model should take --
  "mechanise this ratchet or not" -- is a plain `TK` row. `CLAUDE.md` sec "Who decides" is
  the test, and it is the whole reason this series is narrow.
- (!) **Steps 1-2 alone are a doc warning.** They make ASK rows visible to a SESSION; only
  step 3 makes the user-facing nag fail-red. Landing 1 and 2 and calling it done is this
  project's house failure mode -- an assurance step that fails by passing.
- (!) **Sabotage before believing it** (`docs/sabotage-procedure.md`): an `ASK-*` at `NEXT`
  with no `asked:` line must turn `verify.sh lean` RED, and the sweep must cover the whole
  module with mutations, not just the one obvious case.
- (!) **`ASK-*` is never a `## Still owed` bullet.** A question for the user is durable by
  nature; the note's Still-owed section is a depth-one baton (see the sibling row on lint
  check 15). Two homes for the same question is the drift this series exists to end.

## Read first

- [`../docs/README.md`](../docs/README.md) sec 4 -- the priority vocabulary and the badge
  table. The `(nav)` compass badge is the DRIFTED predecessor of this channel: it is
  documented there as "waiting on a user decision" and every live use of it had decayed
  into meaning "see also" (censused 2026-09-22, first-hand). It now points at an `ASK-*` id
  instead of carrying the question.
- [`README.md`](README.md) sec "Filing a task" -- `--id`, and why a miscategorised id is
  permanent.
- `scripts/handoff_lint.py::check_session_receipt` -- the receipt mechanism step 3 extends.
- `scripts/task.py::op_board` / `::footer_lines` / `::NEXT_COMMANDS` -- where the footer
  line goes, and the `ready ...` line it should mirror.

## Log
