---
id: TK60
title: no parent-census lint check; R6's census sentence is hand-maintained prose
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

`notes.md` "Still open" item 1 named a parent-census lint check as the durable fix for a
known weakness: the `R6` parent's census sentence and its children's trap count are
hand-maintained PROSE with nothing recomputing them. The check has now been deferred
through three renumbering opportunities -- slot 11 went to `check_parent_depth`, slot 12 to
`check_banner`, slot 13 to `check_board_sync` (retired at the cutover, number never
reused).

The mitigation that was used instead -- correct the prose by hand -- has already been
needed once: the `R6` title moved from "11 to land" to "10 to land" when `R6-6` closed. The
failure mode is exactly the one the check would have caught, and the record that predicted
it lived only in the deleted `.scratch/tasktool/`.

A census check recomputes, from the children on disk, what the parent's title and body
assert about them, and fails when the two disagree.

## Traps

- The next check appended is number 14; 13 is retired and never reused
  (`scripts/task.py::LINT_CHECKS`).
- Do not restate the check count anywhere in prose while doing this -- that is the defect
  class this whole family of work exists to stop.
- The parent's census sentence is generated text in origin. Recomputing it at lint time is
  the fix; rewriting it by hand again is not.

## Read first

- [`docs/history/tasktool-scratch-archive-2026-09-07.md`](../docs/history/tasktool-scratch-archive-2026-09-07.md) section 5 item 5
- `scripts/task.py` -- `LINT_CHECKS` and `check_parent_depth` as the nearest shape

## Log
