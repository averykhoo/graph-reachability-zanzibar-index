---
id: TK70
title: the DETONATION: the graph refuses an ordinary grant after admitting a latent-cycle write
brief: F2 of TK69, CONFIRMED first-hand: fix belongs GRAPH-side (refuse the latent write), not by propagating it
pri: NOW
size: M
deps: []
related: [TK69]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-16b
moved: 2026-09-17b
updated: 2026-09-17b
closed: 2026-09-17b
---

## What it is

The SECOND admission divergence family, found 2026-09-16 while fixing `TK69`'s audited
case, and CONFIRMED FIRST-HAND with the tracked probe
[`formal/probes/tk69_admission_parity_2026-09-16.py`](../formal/probes/tk69_admission_parity_2026-09-16.py)
(case `F2`). It is NOT the case `TK69` was filed for and it does not have the same fix.

Same four writes as `TK69`, different order -- B, C, D, A:

    B  ('member','group','g','viewer','folder','*')    object-wildcard userset grant
    C  ('...','folder','*','parent','doc','d1')        bare-star tupleset parent
    D  ('viewer','doc','d1','member','group','g')      closes the userset cycle
    A  ('...','user','u1','editor','folder','f1')      an ORDINARY grant

With no `folder` entity in the store yet, the graph ACCEPTS D -- the cycle is latent, not
closed -- and then REFUSES A, a write that names no wildcard, no userset, and not the
crossable relation `viewer`. Minting `folder:f1`'s I14 crossing middle emits the bridge
edge `(folder,*,viewer)/all -> (folder,f1,viewer)`, and THAT edge closes the cycle.
Measured, literal:

    F2  ok       add ('member','group','g','viewer','folder','*')  -> graph=True  set:py=True  set:roaring=True
        ok       add ('...','folder','*','parent','doc','d1')      -> graph=True  set:py=True  set:roaring=True
        ok       add ('viewer','doc','d1','member','group','g')    -> graph=True  set:py=True  set:roaring=True
        DIVERGES add ('...','user','u1','editor','folder','f1')    -> graph=False set:py=True  set:roaring=True

Through `ConnectedStore` it wedges exactly as `TK69` did (PROBED first-hand, async
schedule): the write is accepted into the log, `catch_up` then raises
`InvariantViolation` every time, `cursor=0 lag=4`, and an untokened
`check(u1 editor f1)` reads `False` -- the whole index frozen by an ordinary grant.

## (!) Traps

- **(!) DO NOT FIX THIS BY NARROWING THE SET ENGINE.** That is the obvious move and it is
  wrong. `index_v4/wildcard.py::WildcardIndex._reject_star_self_edge` was written to
  prevent precisely this outcome and its docstring names it: admitting the edge while the
  shape has no concretes yet *"does not avoid the cycle -- it defers it onto the next
  innocent write, which is then permanently rejected (the 'detonation': the graph locks
  itself out of a grant the set engine and the oracle both allow)"*. Teaching the set
  engine to detonate too would make BOTH backends refuse a grant the ORACLE allows, which
  trades an admission divergence for an oracle divergence -- a strictly worse trade under
  `CLAUDE.md` "Who decides".
- **The fix direction is GRAPH-side: refuse D early.** `_reject_star_self_edge` already
  does this for the same-shape `w_any -> w_all` ROUTED edge it covers; F2 is a hole in
  that coverage -- the same by-construction latent cycle arriving through the entity
  middles rather than through a directly routed same-shape edge. Extending the early
  rejection is what makes the counterintuitive refusal go away instead of propagating it.
- **(!) An early rejection is an OVER-REJECT risk on a legal, oracle-pinned schema class.**
  `_reject_star_self_edge`'s docstring records that rejecting the SCHEMA over-rejects
  (reg11 / `owc_star_ttu` is legal and every other write on it must keep working,
  `docs/spec-deviations.md` 2026-07-26). Whatever refuses D must refuse D and nothing
  else; build the over-reject control FIRST, as `TK69`'s CTRL case did.
- **(!) Do not close this by editing the pin.**
  `tests/test_reg_tk69_entity_crossing.py::test_family2_detonation_is_still_open` asserts
  today's divergence POSITIVELY (never an xfail). Closing F2 turns it RED on purpose --
  flip it to assert unanimity then, and say so in the commit.

## Read first

- [`formal/probes/tk69_admission_parity_2026-09-16.py`](../formal/probes/tk69_admission_parity_2026-09-16.py)
  -- the pre/post instrument; case `F2` is this row, case `CTRL` is the over-reject control.
- `index_v4/wildcard.py::WildcardIndex._reject_star_self_edge` -- READ THE DOCSTRING IN
  FULL before deciding anything; it already contains the verdict on this shape.
- `index_v4/wildcard.py::WildcardIndex._ensure_entity_middles` and
  `zanzibar_utils_v1.py::SchemaInfo.crossable_shapes` -- why minting an entity emits the
  bridge edge that closes the cycle.
- [`docs/spec-deviations.md`](../docs/spec-deviations.md) 2026-09-16 -- the `TK69` entry,
  whose closing paragraphs state this split and why the two families take opposite fixes.
- [`docs/tk69-admission-parity-2026-09-16.md`](../docs/tk69-admission-parity-2026-09-16.md)
  -- the measured map for both families.

## Log

### 2026-09-17b

CLOSED 2026-09-17b. The rule the repo already wrote down on 2026-07-26 held only at LENGTH 1; F2 is the length-n case, and the fix is the generalisation, in both backends, as ONE rule.

MECHANISM (first-hand, dumped). After B,C,D the store holds exactly three grant edges -- w_any(folder,viewer) -> doc:d1#viewer (C, via the TTU rewrite), doc:d1#viewer -> group:g#member (D), group:g#member -> w_all(folder,viewer) (B) -- i.e. a PATH w_any --> w_all on the crossable shape. `_reject_star_self_edge` refuses exactly that configuration as ONE routed edge; at length 3 nothing looked at it. A then mints folder:f1's I14 middle and the out-bridge detonates at wildcard.py:279.

LANDED. (1) `WildcardIndex::_reject_latent_star_cycle` refuses any routed edge completing w_any(T,p) --> w_all(T,p) on a crossable shape, placed beside the length-1 rule and BEFORE any mutation; only the grant edge needs checking, and the docstring carries the inductive reason (neither bridge direction can create such a path unless one already exists). (2) `SetEngine::_flow_reaches`'s I14 crossing hop is now SCHEMATIC AND UNGATED, like the doubly-bridged ghost hop three lines above it; `_any_entity_of_type` deleted with its last caller. Without (2) the divergence MOVES onto the cycle-closing write instead of closing.

(!) THIS RETRACTS A "MUST NOT BE DROPPED" WRITTEN THE DAY BEFORE. The 2026-09-16 entity gate was justified by "with no entity of type T the graph mints no middle and ACCEPTS the same write, so an ungated hop over-rejects". That premise WAS TK70. The gate was reading data about a rule that is about the schema.

MEASURED. `formal/probes/tk70_latent_cycle_sweep_2026-09-17.py` (NEW, tracked, the over-reject control, built and run BEFORE the fix as the row's trap required): 720 orderings of six writes x 3 backends. PRE 80 divergent write decisions (on A and on E, 40 each) + 156 latent-cycle states; POST 0 and 0. The OVERREJECT arm -- the same corpus minus the cycle-forming write, 120 orderings -- is 0 refusals BEFORE AND AFTER, which is what says the refusal MOVED rather than spread. `formal/probes/tk69_admission_parity_2026-09-16.py` now rc=0.

(!) READ THE CENSUS, NOT THE COUNT. Unanimous refusals rise 824 -> 840 and that is the fix working: A and E go from graph-refused-in-40-orderings-each to refused in ZERO, and the growth is entirely B/C/D, the three writes that form the path, because the refusal now lands on whichever arrives last instead of being deferred onto a victim.

(!) THE FIRST DRAFT OF THE PROBE MANUFACTURED A FINDING. It stated the property per-write ("an innocent write is never refused") and reported 144 orderings unanimously refusing F = folder:f1 parent doc:d1, which reads like a second, larger family. It is not: the TTU routes F to folder:f1#viewer -> doc:d1#viewer, whose subject IS a concrete of the crossable shape, so with D present F genuinely closes the loop. A SYNTACTIC INNOCENCE TEST CANNOT SEE A ROUTED EDGE. The property is a STORE INVARIANT -- after every accepted write, no crossable shape has a w_any --> w_all path -- measured with an INDEPENDENT instrument (BFS over stored direct edge rows, not the closure query the fix itself uses).

PINS. `tests/test_reg_tk69_entity_crossing.py` 4 -> 32 tests. Two flipped deliberately: `test_family2_detonation_is_still_open` -> `test_family2_detonation_closed` (it pinned the divergence POSITIVELY so closing it would force this edit), and `test_ctrl_no_entity_means_no_refusal` -> `test_ctrl_cycle_free_corpus_fully_accepted` -- its [B,C,D] arm asserted the latent admission itself and COULD NOT survive the fix, so it is restated over five corpora containing no cycle-forming write, which is what the control was always for. New: `test_no_latent_star_cycle_is_ever_admitted` (invariant L over all 24 orderings) and `test_ordinary_grant_accepted_in_every_ordering`.

SEVEN-MUTATION SWEEP with an M0 attribution control (table in the module docstring). M0 named its own pin, so the run is interpretable. M4 (restore the entity gate) reddens the two PARITY arms and leaves the store-invariant arm green -- the signature of a divergence rather than a bug, and the reason those are separate tests. M5 (drop the obj-reaches-w_all half) is the only mutation reaching the over-reject control; it still refuses D, so the F1/F2 arms alone cannot tell it from the correct rule. M6 is INERT FOR A STATED REASON: on this schema crossable == bridged_in == bridged_out, so the edit could not move anything the module observes.

MAP: docs/tk70-detonation-2026-09-17.md (ACTIVE-PLAN). Ledger: docs/spec-deviations.md 2026-09-17. Model: `formal/CORRESPONDENCE.md` sec 8.1 TK70 bullet -- write admission is unmapped on both sides, and the three-leg inertness argument of ZT-P5-NEW transfers verbatim (the guard precondition is still bridged_in n bridged_out != empty, unsatisfiable in both modeled fragments), so no Lean definition describes dead code. `docs/tk69-admission-parity-2026-09-16.md` FROZEN with a dated correction retracting the entity-gate claim and the S2 sabotage row.

NOT ESTABLISHED: that F1 and F2 are the only two families. That still rests on the unreproduced 2026-09-16 agent sweep; this session's 720 orderings are first-hand but over the same six writes and one schema.

F2 CLOSED. Graph-side `_reject_latent_star_cycle` (the length-n form of the ZT-P5 rule) + the set engine crossing hop made schematic. 720 orderings: 80 divergences and 156 latent-cycle states -> 0 and 0, over-reject control at 0 refusals before AND after. Pins 4 -> 32, two flipped on purpose. See the 2026-09-17b log entry.
