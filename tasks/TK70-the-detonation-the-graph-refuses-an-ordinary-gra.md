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
moved: 2026-09-17
updated: 2026-09-17
closed:
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
