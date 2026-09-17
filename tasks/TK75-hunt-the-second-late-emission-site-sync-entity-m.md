---
id: TK75
title: hunt the SECOND late-emission site (_sync_entity_middles) and the unreproduced second TK73 witness
brief: TK73 left two unpinned: the strip-AND-re-add call site on crossable schemas, and a reported witness never reproduced
pri: NEXT
size: S
deps: []
related: [TK73]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-17
moved: 2026-09-18
updated: 2026-09-18
closed:
---

## What it is

`TK73` fixed the cascade's terminal check after reconcile-time node GC emitted outbox rows
inside the last budgeted round. Two things about that emission were left open, and both are
about **coverage of the emitting surface**, not about the fix:

1. **`_sync_entity_middles` is a SECOND late-emission site.** It is
   `index_v4/processor.py::DeltaProcessor._gc_subject_node`'s final act (READ), and
   `::_gc_public_node` carries the same call. Unlike `_maybe_remove_bridges` it both
   **strips AND re-adds** bridges, so on a schema with non-empty `crossable_shapes` it can
   emit in both directions. A `TK73` verifier built a crossable schema and could not make
   it fire; there is no witness in hand.
2. **A SECOND independent witness was reported and never reproduced** -- a randomised sweep
   trial with leftover `('folder','owner','z')` on a schema adding
   `editor: [user, user:*]` (UNVERIFIED).

The settle-and-assert fix covers both **by construction** (it asks the semantic question
regardless of which call site emitted), so this row is about PINNING the surface, not
about a live bug.

## (!) Traps

- **(!) This is NOT a reopening of `TK73`.** The fix is call-site-independent on purpose.
  If a witness here raises, the interesting question is which CLAIM it breaks -- do not
  reach for the round budget (`TK73` measured that `rounds+1` silently repairs genuine
  staleness, which is why it was rejected).
- **(!) An `INERT` result here is the expected outcome, and that is the trap.** If a hunt
  finds nothing, say what the probe was supposed to move and check it moved -- an
  un-fireable probe reads exactly like a clean surface.
- **(!) `crossable_shapes` is EMPTY on the `TK73` witness schema** (it has no object
  wildcards), so that schema cannot exercise `_sync_entity_middles`' re-add arm at all.
  A new fixture is required; reusing the witness would be a green that proves nothing.

## Read first

- [`docs/tk73-cascade-quiesce-gc-2026-09-17.md`](../docs/tk73-cascade-quiesce-gc-2026-09-17.md)
  sec 3 (the emission mechanism) and sec 7 (both open items, labelled by provenance).
- `index_v4/processor.py::DeltaProcessor._gc_subject_node` / `::_gc_public_node` -- the two
  callers of `_sync_entity_middles`.
- `tests/test_cascade_quiesce_gc.py` -- the existing pin; a new shape extends this module.

## Log

### 2026-09-18

ITEM 2 IS CLOSED; ITEM 1 IS HALF CLOSED AND ITS TRAP IS WRONG. Map: [`docs/tk74-staleness-net-2026-09-18.md`](../docs/tk74-staleness-net-2026-09-18.md) sec 5 (ACTIVE-PLAN). Evidence is AGENT-MEASURED with two-sided instrument controls, and each claim below survived two adversarial skeptics; the parts this session re-verified first-hand are marked READ.

**ITEM 2 -- THE SECOND `TK73` WITNESS IS RECOVERED AND REPRODUCED.** Found in `.scratch/tk73adv/sweep.py` (seeded `random.Random(20260917)`), replayed with the pre-`TK73` check reinstalled by monkeypatch, reproduced ON THE FIRST RUN with the exact reported leftover `[('folder','owner','z')]`. It is answer **(a), the boring one**, now MEASURED rather than assumed: byte-identical to witness 1 modulo the entity name, same chain `_run_cascade -> reconcile_subject -> _gc_subject_node -> _demote_released_node -> _maybe_remove_bridges -> _emit x3`. Minimised to three writes -- `add folder:* parent folder:z`; `add folder:x parent folder:y`; `remove folder:x parent folder:y` -- and **the `editor: [user, user:*]` declaration is IRRELEVANT** (schema S1, which lacks it, raises the same key). The leftover entity is the STAR PARENT'S OBJECT for E in {x,z,w,q} but **NOT for E='y'** (the removed edge's own object), which is green and **UNEXPLAINED** -- do not encode the unqualified generalisation in a docstring. Instrument control was two-sided: the reinstalled old check raised on both witnesses with the historically recorded text, and over the full 120-trial sweep counted `{'calls': 624, 'raises': 1}`, so it is not a blanket raiser; two negative controls (no star write; concrete parent) stay green.

**ITEM 1 -- THE STRIP ARM HAS A WITNESS, AND IT IS ALREADY IN THE SUITE.** `index_v4/wildcard.py::WildcardIndex._sync_entity_middles` (`:404`) no-witness branch -> `::_strip_bridges` (`:421`) emits 3 REMOVED outbox rows above the final frontier from inside a reconcile, on `tests/test_i14_crossing_middles.py::test_middles_retire_with_their_entity`, reached via `index_v4/processor.py::DeltaProcessor._gc_public_node` (`:1307`), **delete branch only** (`:1300-1307`). (!) **THIS ROW'S TRAP "crossable_shapes is EMPTY on the TK73 witness schema ... A NEW FIXTURE IS REQUIRED" IS WRONG.** It is right about the `TK73` schema and wrong that a new fixture is needed -- the existing suite already fires the site; only instrumentation was missing.

**THE RE-ADD ARM IS REACHED BUT INERT.** 269 re-add calls inside a reconcile-time GC inside a cascade, **every one emitting ZERO rows** -- it only re-ensures a middle that is already complete. It could be made to emit only by manufacturing an I14 hole first (forced `_strip_bridges` on the crossing middle immediately before the real call: detector then reports emissions at BOTH GC callsites, so the probe can go red). The row's own trap was right that an INERT result reads like a clean pin; it is inert, and the control is what makes that statement worth anything.

(!) **TWO CLAIMS FROM THIS INVESTIGATION ARE REFUTED -- DO NOT REPEAT THEM.**
* "a genuine third late-emission callsite that the TK73 doc does not name" -- two agents asserted it, three skeptics killed it independently. `docs/tk73-cascade-quiesce-gc-2026-09-17.md` sec 7 (`:189-193`) names `_gc_public_node` verbatim, and item 1 of this row repeats it. The contribution is the first WITNESS, not the discovery.
* "TK75's coverage claim is measurably false" -- refuted and settled against the agent. The settle pass IS call-site-independent; coverage is mediated by `::_map_deltas_to_keys`. And `leftover == {}` is the GLOBAL NORM, not a fact about this site: 558 cascades measured, settle ran on 3 (READ, first-hand this session -- `TK74` log, 2026-09-18).

**NEXT ACTION (single):** extend `tests/test_cascade_quiesce_gc.py` with the second witness shape, parameterised on a star target distinct from both 'x' and 'y' ('z' is correct), asserting `settle.keys == [('folder','owner','z')]` and `settle.changed == ()`. Then decide whether the inert re-add arm earns the forced-strip control as a permanent test or a recorded negative.

Related and newly filed: `TK77` -- the validation matrix and the hypothesis campaign make ZERO `_sync_entity_middles` calls on a crossable-type entity (66 tests, 4m37s, empty census), because `tests/fga_schemas/wildcards.fga` and `boolean_wildcards.fga` both compute `crossable_shapes == []` under the matrix's `OBJECT_WC`. That is why this surface had no witness: the campaigns cannot reach it.
