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
moved: 2026-09-05b
updated: 2026-09-05b
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

### 2026-09-05b

2026-09-05b: UNBLOCKED IN SUBSTANCE by P3 landing (deps still P4 -- re-check whether 4b is really prerequisite). The T2a carry is now PROOF WORK, not a design decision: the model routes a Direct-arm write onto the leaf family exactly as Python does, and the D.3/2026-08-08 probe re-run on the model's OWN write leg gives negFree := true at negTested := 2 over a routing-independent 144-pair key domain, with the pre-flip bare edge on the SAME state reproducing D.3's kill (negFree := false) and a hypothetical approver.0 -> approver bridge turning the subject red. Tracked source: formal/probes/d3_negedgefree_postflip_2026-09-05.lean (run with lake env lean from formal/lean). Measurement over fuel-capped GraphState.reach, one schema shape -- the theorem is what this item owes: Inv.negEdgeFree on the _d fragment for the leaf-routed write leg, then restate graph_reached_inv without W4NarrowT2a (FullScope.lean:330; outside_narrow_t2a :1728 still holds today). Witness trap: Sd/Td is vacuous for this (no wildcard => neg = []); use LeafWitness.Sw/tw. See PROOF_STATUS 2026-09-05b sec 9.5.
