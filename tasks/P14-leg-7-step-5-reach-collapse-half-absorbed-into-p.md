---
id: P14
title: leg 7 step 5, reach-collapse half -- absorbed into P3 (Route B), breaks P3->P14->P4->P3 cycle
pri: LATER
size: M
deps: [P4]
related: []
parent:
labels: [formal]
source: board
source_hash: 7cbc1a1dc6fb
created: 2026-08-20b
moved: 2026-08-20b
updated: 2026-08-20b
closed:
---

leg 7 **step 5, reach-collapse half ONLY** — the classification half (re-partition `DerNode`/`UntaintedShadow`) was **absorbed into `P3` on 2026-08-20b** under Route B, which is what breaks the old `P3 → P14 → P4 → P3` cycle

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §5 + §7 step 5, and §11.9 for the split

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-20b`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.
