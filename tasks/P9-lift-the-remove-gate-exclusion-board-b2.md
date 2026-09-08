---
id: P9
title: lift the remove-gate exclusion (board B2)
brief:
pri: LATER
size: M
deps: []
related: []
parent: B2
labels: [formal]
source: board
source_hash: 549794abdb73
created: 2026-08-16
moved: 2026-08-16
updated: 2026-08-16
closed:
---

lift the remove-gate exclusion (board `B2`)

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- `formal/conformance/test_conformance_remove_graph.py`

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.
