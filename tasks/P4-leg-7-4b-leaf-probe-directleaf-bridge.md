---
id: P4
title: leg 7 4b -- leaf-probe <-> directLeaf bridge
brief: Unblocked 2026-09-05b (P3 closed; deps swept); bridge target is the live leaf-routed write path
pri: LATER
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 015e6dd88c0d
created: 2026-08-16
moved: 2026-09-06b
updated: 2026-09-06b
closed:
---

leg 7 **4b** — leaf-probe ↔ `directLeaf` bridge. Unblocked 2026-09-05b (`P3` closed; deps
swept): the whole leaf-routed write path is live in the model (`Cascade.lean:190-191`,
`:340-341`, `affectedKeys` `:542-546`), so the bridge target is the landed leg, not a plan.

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §7

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-09-05b

2026-09-05b: dep P3 swept (landed). Re-scope before starting: the leaf-probe <-> directLeaf bridge now has the whole leaf-routed write path live in the model (Cascade.lean:190-191, :340-341, affectedKeys :542-546), and the toolkit it was going to bridge to is the one CascadeStrataSettle.lean:3721 rawWriteRels_ne_nil_of_exprDirectsAll already walks (persistedLeaves/unionSpineLeaves/atomLeaves/pureLeaves/splitPure vs exprDirectsAll).

### 2026-09-06b

Board cell appended 2026-09-05b: 'Unblocked 2026-09-05b (P3 closed; deps swept)'. Task summary + brief now carry it (the 2026-09-05b Log entry already had the re-scope detail). Diff source: git 51642dc -> HEAD.
