---
id: P14
title: leg 7 step 5, reach-collapse half ONLY -- classification half landed with P3 (2026-09-05b)
brief: NOW 2026-09-23b: _d reach-collapse lemmas already exist; first state what is still owed, else close as absorbed
pri: NOW
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 5984b012cc7a
created: 2026-08-20b
moved: 2026-09-23c
updated: 2026-09-23c
closed: 2026-09-23c
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

### 2026-09-23b

2026-09-23b (P5 closed): P5 is the other half of goal step 2 and landed WITHOUT needing this item, so this is now the only open formal-milestone row -- promoted to NOW. A sizing fact P5 produced, READ first-hand: the T2a chain now consumes CascadeStrataSettle.lean::reachedByW3d2_reach_collapse_root_d, ::reachedByW3d2_Rnode_source_bare_d, ::reachedByW3d2_bareNode_no_inedge_d and ::reachedByW3d2_Rnode_source_name_ne_star_d -- the reach-collapse family ALREADY exists on the Direct-arm (_d) fragment over the landed leaf-routed write leg, and graph_correct (via reachedByW3d2E_toC_d) and graph_reached_inv both rest on it today. So before re-proving anything, the first action here is to say WHAT the reach-collapse half still owes that those _d lemmas do not already give: re-read scope doc formal/history/leaf-family-split-scope-2026-08-05.md sec 5 + sec 7 step 5 against them, and if the answer is nothing, close this as absorbed (the way P3 absorbed the classification half) with the lemma list as evidence. Map of what P5 used: docs/p5-negedgefree-under-leaf-routing-2026-09-23.md sec 2.

### 2026-09-23c

CLOSED AS ABSORBED, nothing owed. (1) The classification half landed with P3 (2026-09-05b). (2) The reach-collapse family IS re-proved over the leaf-routed chain: ReachedByW3d2.write steps by writeLoggedRules (the rewriteClosureL fold since the 2026-09-05 flip), and CascadeStrataSettle.lean::reachedByW3d2_reach_collapse_root_d / _Rnode_source_bare_d / _bareNode_no_inedge_d are proved over it (re-proof recorded in the _Rnode_source_bare_d proof comment, step 4c-ii). The mid-batch ::reconcileJobsLR_reach_collapse has no scope premise. (3) The per-leaf-node collapse and the graphRec/checkFn re-point have no Lean reader: P4 found the tree took the REFUSAL route, and the Python leaf_check side is P4s CORRESPONDENCE sec 7.3 item. MEASURED: probe formal/probes/p14_collapse_closure_2026-09-23.lean (rc=0, controls IN/OUT both behave) shows all eight headline theorems rest on the _d W3d2 collapse family + reconcileJobsLR_reach_collapse ONLY. Every narrow, W3d and W3a collapse lemma is OUT. Goal step 2 is complete. Follow-up TK103 (LATER): audited names vs headline closure. Map: docs/p14-reach-collapse-absorbed-2026-09-23.md (FROZEN).
