2026-09-01e — gate re-run after the step-8 increment; verdict line in the session-log entry.

(nav) **STEP 8's FREE HALF LANDED AND THE FLIP IS A CLOSED LIST — 5 SITES / 4 DECLS / 2
FILES.** `untaintedShadow_applyD` + `untaintedShadow_applyLoggedR{,_d}` PRE-WIDENED in place:
no new declaration, no signature change, no pin exposure; `hoffW` costs no premise (`hcb` +
`bare_subjNode_not_leafNode`). Green first attempt, 1089 jobs. The lower bound closed by
staging the probe with `sorry` so `lake` builds PAST the red module — retiring "~20 sites".
(!) **STEP 9 IS BLOCKED ON A DESIGN DECISION, NOT PROOF EFFORT.** The seed-side
`NotLeafName t.subject.predicate` at three `rewriteClosure` sites wants a store-level
`NoLeafStoreSubjects T` threaded through their signatures — changing downstream statements
and hence potentially the headline theorems. **Do not thread it unasked.**

(!) **A PRE-WIDEN's control is the flip PROBE, never a weakening** — §11.13 **(n)**, which
generalises (k): S1 (`hoffW` narrowed to `DerNode`) is GREEN unflipped, RED flipped.
