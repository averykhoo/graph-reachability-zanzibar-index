---
id: TK64
title: handoff_lint's zero-NOW failure prints the >1 branch's sentence
brief:
pri: LATER
size: S
deps: []
related: [TT-1]
parent:
labels: [infra]
source: docs/history/tasktool-scratch-archive-2026-09-07.md
source_hash:
created: 2026-09-07
moved: 2026-09-07
updated: 2026-09-07
closed:
---

`AUDIT.md` finding T3 (2026-08-21): the zero-`NOW` lint failure printed the `> 1` branch's
sentence. The message on a corpus with NO ranked row read "...must be exactly 1. NOW is
what an unassigned session picks up; two of them is no ranking at all" -- a true sentence
about the opposite failure, told to someone whose actual problem is that nothing is ranked.

It was fixed in the task tool and pinned at
`tests/test_tasktool.py::test_regression_zero_now_message_is_true_of_zero`;
`scripts/task.py:2443` records the fix in its own comment. It was never ported back to the
sibling checker: verified 2026-09-07, `scripts/handoff_lint.py:439` still carries the
`> 1` wording on a possibly-zero count.

Small, but it is a message a session reads at exactly the moment it is confused, and the
two checkers now disagree about the same invariant -- which the scratch records name as
worse than either being wrong alone, because whichever you meet first teaches you the wrong
rule.

## Traps

- Fix the MESSAGE, not the check. The capacity rule is correct in both files.
- `handoff_lint.py::check_priority_capacities` gained a tree fallback at the 2026-09-06
  cutover, so it now reports on tree state, not board rows -- the zero case is reachable.

## Read first

- [`docs/history/tasktool-scratch-archive-2026-09-07.md`](../docs/history/tasktool-scratch-archive-2026-09-07.md) section 5 item 4
- `scripts/task.py:2443` -- the fix and its reasoning, already made once

## Log
