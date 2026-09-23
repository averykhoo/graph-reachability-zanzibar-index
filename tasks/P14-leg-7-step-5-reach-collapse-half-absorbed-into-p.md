---
id: P14
title: leg 7 step 5, reach-collapse half ONLY -- classification half landed with P3 (2026-09-05b)
brief: P3 closed 2026-09-05b: the absorbed classification half landed with it; only the reach-collapse half remains
pri: LATER
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 5984b012cc7a
created: 2026-08-20b
moved: 2026-09-23
updated: 2026-09-23
closed:
---

leg 7 **step 5, reach-collapse half ONLY** — the classification half (re-partition `DerNode`/`UntaintedShadow`) was **absorbed into `P3` on 2026-08-20b** under Route B, which is what breaks the old `P3 → P14 → P4 → P3` cycle. `P3` closed
2026-09-05b — the absorbed half landed with it; only this reach-collapse half remains.

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §5 + §7 step 5, and §11.9 for the split

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-20b`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-09-05b

2026-09-05b: P3 (which absorbed this item's classification half) LANDED; the reach-collapse half is untouched. Re-size against the landed tree before starting.

### 2026-09-06b

Board cell appended 2026-09-05b: 'P3 closed 2026-09-05b -- the absorbed half landed with it; only this reach-collapse half remains'. Task summary, title and brief now carry it. Diff source: git 51642dc -> HEAD.

### 2026-09-23

The dep on P4 is REMOVED this session, same measurement as P5s 2026-09-23 note: the leaf-probe <-> directLeaf bridge touches neither of the files this items reach-collapse half lives in (probeNonDerived and directLeaf occur ZERO times in CascadeStrataEdge.lean and CascadeStrataInv.lean). P4 -> P14 was a plan ordering from scope doc section 7 step 5, not a proof dependency. Still owed here, unchanged and still un-resized against the landed tree: re-partition DerNode/UntaintedShadow and re-prove the reach-collapse family. Note before sizing: much of the leaf-side classification already landed with the 2026-09-05 flip (CascadeStable.lean carries LeafNode, bare_is_leafPred and rewriteClosureL_extras_leafNode today), so the 2026-08-05 scope estimate is an upper bound, not a measurement. Map: docs/p4-leaf-probe-bridge-2026-09-23.md.
