---
id: P5
title: Inv.negEdgeFree under leaf routing; retire the T2a caveat
brief: PROOF work, not a design call: T2a did NOT widen with P3; negEdgeFree is the only clause; probe with LeafWitness.Sw/tw
pri: LATER
size: M
deps: [P4]
related: []
parent:
labels: [formal]
source: board
source_hash: ab020841d395
created: 2026-08-16
moved: 2026-09-06b
updated: 2026-09-06b
closed:
---

`Inv.negEdgeFree` under leaf routing; retire the T2a caveat. **Re-scoped 2026-09-05b: this
is PROOF work, not a design call** — T2a did NOT widen with `P3` (`graph_reached_inv` still
takes `W4NarrowT2a`; `outside_narrow_t2a` holds) and its "`P6` modelling limit"
justification is retired, since the model now routes exactly as Python does. The D.3 probe
re-run on the landed model (`formal/probes/d3_negedgefree_postflip_2026-09-05.lean`) says
`negFree := true` on the model's own write leg while the bridge-sabotage control reproduces
D.3's kill — so the clause is plausibly provable, and `negEdgeFree`
(`GraphIndex/State.lean:706`) is the only clause implicated. PROOF_STATUS `2026-09-05b` §9.5.

## Traps

⚠ D.3's witness (`Sd`/`Td`) is now VACUOUS under routing (no wildcard ⇒ `neg = []`); probe
with `LeafWitness.Sw`/`tw`.

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §9.1–9.3 + §7 step 6

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-09-05b

2026-09-05b: UNBLOCKED IN SUBSTANCE by P3 landing (deps still P4 -- re-check whether 4b is really prerequisite). The T2a carry is now PROOF WORK, not a design decision: the model routes a Direct-arm write onto the leaf family exactly as Python does, and the D.3/2026-08-08 probe re-run on the model's OWN write leg gives negFree := true at negTested := 2 over a routing-independent 144-pair key domain, with the pre-flip bare edge on the SAME state reproducing D.3's kill (negFree := false) and a hypothetical approver.0 -> approver bridge turning the subject red. Tracked source: formal/probes/d3_negedgefree_postflip_2026-09-05.lean (run with lake env lean from formal/lean). Measurement over fuel-capped GraphState.reach, one schema shape -- the theorem is what this item owes: Inv.negEdgeFree on the _d fragment for the leaf-routed write leg, then restate graph_reached_inv without W4NarrowT2a (FullScope.lean:330; outside_narrow_t2a :1728 still holds today). Witness trap: Sd/Td is vacuous for this (no wildcard => neg = []); use LeafWitness.Sw/tw. See PROOF_STATUS 2026-09-05b sec 9.5.

### 2026-09-06b

Board cell rewritten 2026-09-05b: re-scoped to PROOF work (T2a did not widen with P3; D.3 probe re-run says negFree := true; negEdgeFree is the only clause; Sd/Td witness vacuous, use LeafWitness.Sw/tw). Task summary, Traps and brief now carry it; the 2026-09-05b Log entry already had the detail. Diff source: git 51642dc -> HEAD.
