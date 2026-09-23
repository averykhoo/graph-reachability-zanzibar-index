---
id: P5
title: Inv.negEdgeFree under leaf routing; retire the T2a caveat
brief: NOW 2026-09-23: P4 dep removed (measured); residual = one hco binder + 3 edgeHyg1 re-points; run D3 probe at Sd/Td FIRST
pri: NOW
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: ab020841d395
created: 2026-08-16
moved: 2026-09-23b
updated: 2026-09-23b
closed: 2026-09-23b
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

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule. Enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`; `TK59` is the row that would re-enforce it.)
- [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §9.1–9.3 + §7 step 6

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-09-05b

2026-09-05b: UNBLOCKED IN SUBSTANCE by P3 landing (deps still P4 -- re-check whether 4b is really prerequisite). The T2a carry is now PROOF WORK, not a design decision: the model routes a Direct-arm write onto the leaf family exactly as Python does, and the D.3/2026-08-08 probe re-run on the model's OWN write leg gives negFree := true at negTested := 2 over a routing-independent 144-pair key domain, with the pre-flip bare edge on the SAME state reproducing D.3's kill (negFree := false) and a hypothetical approver.0 -> approver bridge turning the subject red. Tracked source: formal/probes/d3_negedgefree_postflip_2026-09-05.lean (run with lake env lean from formal/lean). Measurement over fuel-capped GraphState.reach, one schema shape -- the theorem is what this item owes: Inv.negEdgeFree on the _d fragment for the leaf-routed write leg, then restate graph_reached_inv without W4NarrowT2a (FullScope.lean:330; outside_narrow_t2a :1728 still holds today). Witness trap: Sd/Td is vacuous for this (no wildcard => neg = []); use LeafWitness.Sw/tw. See PROOF_STATUS 2026-09-05b sec 9.5.

### 2026-09-06b

Board cell rewritten 2026-09-05b: re-scoped to PROOF work (T2a did not widen with P3; D.3 probe re-run says negFree := true; negEdgeFree is the only clause; Sd/Td witness vacuous, use LeafWitness.Sw/tw). Task summary, Traps and brief now carry it; the 2026-09-05b Log entry already had the detail. Diff source: git 51642dc -> HEAD.

### 2026-09-23

The dep on P4 is REMOVED this session, measured not assumed. Inv (GraphIndex/State.lean:717-730, NOT :706 -- that cite is stale by 11 lines) is a statement about nodes/edges/residue and NReaches only: negEdgeFree at :724-725 says no neg members subject node reaches the rows key node. It mentions no store, no evalE, no directLeaf and no probe, so the leaf-probe <-> directLeaf bridge cannot discharge any part of it. Confirmed the other way too: probeNonDerived and directLeaf occur ZERO times in CascadeStrataEdge.lean and CascadeStrataInv.lean, the two files owning EdgeHyg1 and the lemma that produces negEdgeFree. P4 -> P5 was a PLAN ordering from scope doc section 7, not a proof dependency, and the landed architecture severed it (see P4s 2026-09-23 note: the tree took the refusal route, not the bridge route). RESIDUAL COST of retiring W4NarrowT2a, measured: hN.computedOnly threads CascadeStrataEdge.lean::edgeHyg1_runCascade2 :178 -> ::edgeHyg1_reconcileJobsLR :140 -> ::edgeHyg1_applyLoggedR :86, which at :115 feeds CascadeStrataInv.lean::reconcileStarsKeyDR_row_edge_consistent :418 (hco : ComputedOnly e binder at :422, EXACTLY ONE call site). That lemma plus the three-lemma edgeHyg1 re-point is the work; no edgeHyg1_*_d twin exists (grep returns nothing), while writeLeg_inedges_eq_of_unmapped :4342 and removeLeg_inedges_eq_of_unmapped :4374 are already there taking neither ComputedOnly nor StoreValidRules. TRAP, first action not last: the d3_negedgefree_postflip_2026-09-05 probe runs at LeafWitness.Sw (union arm, wildcard viewer) while outside_narrow_t2a refutes at Sd/Td which has NEITHER -- the obstacle-is-gone measurement and the bundle-still-bites refutation are at two different stores, and the probe has never been run at Sd/Td. ALSO: graph_reached_inv has ZERO proof consumers (whole-tree grep 2026-09-23; every other hit is prose or Audit.lean #print axioms), so weakening it cannot go red -- a dual positive witness at Sd/Td is owed alongside any hN removal. Map: docs/p4-leaf-probe-bridge-2026-09-23.md.

### 2026-09-23b

DONE 2026-09-23b. graph_reached_inv (T2a) now takes ONLY GraphAdmission + W4Fragment -- the same two bundles as every other headline theorem; W4NarrowT2a, w4NarrowT2a_of_untainted and W4WitnessDirect.outside_narrow_t2a are DELETED. STEP 0 (the row's trap), MEASURED: probe formal/probes/p5_negedgefree_sd_td_2026-09-23.lean at Sd/Td4 reads negTested := 0 on every leg including the pre-flip control -- Sd has no wildcard, so neg = [] everywhere; outside_narrow_t2a refuted the BUNDLE (narrow storeValid), never the invariant, and the clause only bites at LeafWitness.Sw (same run reproduces 2026-09-05 there). PROOF: the T2a chain (CascadeStrataEdge.lean edgeHyg1_* / reachedByW3d2E_edgeHyg1 / _edgeHygienic / _inv, and CascadeStrataInv.lean::reconcileStarsKeyDR_row_edge_consistent) widened IN PLACE to the _d fragment -- every narrow consumer already had a _d twin (the core needed only reconcileStarsKeyDR_edge_char_d); the 2026-09-23 estimate undercounted by five sites, all twinned. New helper CascadeStrataEdge.lean::objNode_ne_derived_of_untainted. WITNESSES: FullScope.lean::W4WitnessDirect.reached_inv_applies/_applies4 (scope; neg = [] there, says so) and Exec.lean::P5Witness.leafRouted_inv_preflip_not + prefix_facts (content, at Sw: from one drained prefix state the leaf-routed write reaches a chain state satisfying Inv with bob in the approver neg row, and the pre-flip bare write from the SAME state violates Inv). SABOTAGE: M1 (drop the star) and M2 (claim the routed write lands bob->approver) each redden prefix_facts; M3 (weaken Inv.negEdgeFree) dies upstream at State.lean::inv_putResidue -- instrument limit. Pins regenerated deliberately: headline_statements (graph_reached_inv loses hN; outside_narrow_t2a -> 4 new), headline_definitions, audited_theorems (one removed, justified in formal/history/PROOF_STATUS.md 2026-09-23). Map: docs/p5-negedgefree-under-leaf-routing-2026-09-23.md (FROZEN at close).

CORRECTION to the close message above: TWO audited names were removed, not one -- W4WitnessDirect.outside_narrow_t2a AND w4NarrowT2a_of_untainted (audited_theorems.txt regenerated to 628 names). A case-sensitive grep for W4NarrowT2a missed the lowercase w4 helper, and a whole-package lake build does not build ZanzibarProofs.Audit; the gate lean phase (audit build: Unknown constant w4NarrowT2a_of_untainted) caught it. Justification for both: formal/history/PROOF_STATUS.md, session 2026-09-23.
