---
id: P16
title: widen the enumeration/state bounds
brief:
pri: SOMEDAY
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 00325e1ec314
created: 2026-08-16
moved: 2026-10-13d
updated: 2026-10-13d
closed:
---

widen the enumeration/state bounds

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md) §4(e); read `formal/conformance/test_conformance_enum.py`'s module docstring, which is half the plan

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-10-13d

Sprint re-rank 2026-10-13d (user-approved in chat): LATER -> SOMEDAY. The row widens the formal surface, against the current goal (user 2026-09-22c: make the assurance surface honest and legible, not wider). Revisit only on a concrete need.
