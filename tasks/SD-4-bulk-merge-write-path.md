---
id: SD-4
title: bulk-merge write path
brief:
pri: SOMEDAY
size: L
deps: []
related: []
parent:
labels: [infra]
source: board
source_hash: 051bc26b11fd
created: 2026-08-16
moved: 2026-08-16
updated: 2026-08-16
closed:
---

bulk-merge write path

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [sketch](docs/architecture/bulk-merge-design.md)

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.
