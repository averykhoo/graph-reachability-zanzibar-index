---
id: P5
title: Inv.negEdgeFree under leaf routing; retire the T2a caveat
brief:
pri: LATER
size: M
deps: [P4]
related: []
parent:
labels: [formal]
source: board
source_hash: 9b3fb5f244d7
created: 2026-08-16
moved: 2026-08-16
updated: 2026-08-16
closed:
---

`Inv.negEdgeFree` under leaf routing; retire the T2a caveat

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §9.1–9.3 + §7 step 6

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.
