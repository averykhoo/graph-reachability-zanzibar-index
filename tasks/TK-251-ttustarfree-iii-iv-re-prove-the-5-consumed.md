---
type: Task
id: TK-251
aliases: [P7]
title: ttuStarFree (iii)+(iv) -- re-prove the 5 consumed sites, widen the gate
brief:
pri: SOMEDAY
state: open
size: M
deps: [TK-277]
related: []
parent:
labels: [formal]
source: board
source_hash: bcf52c3deec7
created: 2026-08-16
taskpy_moved: 2026-10-13d
taskpy_updated: 2026-10-13d
---

`ttuStarFree` **(iii)+(iv)** — re-prove the 5 consumed sites, widen the gate

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [`PROOF_STATUS.md`](formal/history/PROOF_STATUS.md) 2026-08-16

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-10-13d

Sprint re-rank 2026-10-13d (user-approved in chat): LATER -> SOMEDAY. The row widens the formal surface, against the current goal (user 2026-09-22c: make the assurance surface honest and legible, not wider). Revisit only on a concrete need.
