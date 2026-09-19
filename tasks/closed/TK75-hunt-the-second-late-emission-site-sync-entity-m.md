---
id: TK75
title: hunt the SECOND late-emission site (_sync_entity_middles) and the unreproduced second TK73 witness
brief: TK73 left two unpinned: the strip-AND-re-add call site on crossable schemas, and a reported witness never reproduced
pri: NOW
size: S
deps: []
related: [TK73]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-17
moved: 2026-09-19b
updated: 2026-09-19b
closed: 2026-09-19b
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

### 2026-09-19b

BOTH ITEMS CLOSED 2026-09-19b, and both are now PERMANENT TESTS rather than recorded observations. Everything below was re-derived FIRST-HAND this session; the 2026-09-18 entry's agent-measured claims are confirmed where they are repeated and sharpened where they were loose.

ITEM 2 -- THE SECOND WITNESS IS PINNED, AND THE "UNEXPLAINED" GREEN IS EXPLAINED.
`tests/test_cascade_quiesce_gc.py::test_the_witness_generalises_on_its_star_target` parametrizes the witness on its STAR TARGET (the add/remove pair is always `folder:x parent folder:y`; only the star write moves) over x/z/w/q and asserts, per arm, `settle.keys == [('folder','owner',E)]`, `settle.changed == ()`, and full oracle + both-SetOps parity over a grid rebuilt per target. E='z' is the reported-but-never-reproduced second witness; it reproduces.

The row instructed: "the leftover entity is the STAR PARENT'S OBJECT for E in {x,z,w,q} but NOT for E='y', which is green and UNEXPLAINED -- do not encode the unqualified generalisation in a docstring." It is now explained, and it is refcount arithmetic rather than anything about the cascade. MEASURED: at E='y' the star write and the concrete write name the SAME object, so `parent@folder:y` carries reference_count 2 going into the remove and the remove takes it to 1. Nothing is released, `_demote_released_node` is never called (`demoted=[]`), no reconcile-time GC runs, nothing is emitted late, and `_settle is None` -- the pass never RAN, as distinct from ran-and-found-nothing. At E in {x,z,w} the same node is at 1 and goes to 0, `admin@folder:x` is demoted, and the GC chain fires. `::test_the_star_target_that_shares_the_removed_object` pins that with its CAUSE (the refcount-2 precondition), not just its symptom, because `assert _settle is None` alone would stay green for any future reason the code stops being reached -- this row's own trap.

ITEM 1 -- THE STRIP ARM IS PINNED; THE RE-ADD ARM IS A RECORDED NEGATIVE, RE-HOMED TO TK77.
`tests/test_i14_crossing_middles.py::test_the_strip_arm_emits_from_inside_a_reconcile_time_gc` is the first witness for the second late-emission site. Instrumented first-hand: the removal's cascade takes `_sync_entity_middles`' no-witness branch, calls `_strip_bridges` on `('folder','viewer')`, and that call emits 3 outbox rows at nesting `cascade=1, reconcile=1, gc=1`. The nesting assertion is the load-bearing one -- outside a reconcile-time GC this is an ordinary write, not a late emission.

(!) THE HONEST OTHER HALF, which the earlier entry did not have: on this fixture those late rows map back to NO derived key, so `leftover` stays empty and `_settle is None`. The second site is a late EMITTER here; it is not a late LEFTOVER producer, so it does NOT reproduce TK73's shape. Do not let a future reader upgrade "second late-emission site, witnessed" into "TK73 reproduces at the second site".

DECISION on the inert re-add arm (the row's open executive question): RECORDED NEGATIVE, not a permanent forced-strip control test, and the reason is stronger than "it is inert". Census run first-hand over every module TK77 names as the only coverage of the crossable surface -- `test_i14_crossing_middles.py`, `test_owc_star_parent_cross.py`, `test_bulk_build.py` -- gives 7 `_sync_entity_middles` calls in total, 1 of them inside a reconcile-time GC, and that one takes the STRIP arm. The in-GC re-add arm is reached ZERO times by any of them. A forced-strip control here would therefore pin a fixture invented for the probe rather than the shipped surface, and it would assert behaviour on a store state I14 forbids and paranoia already catches. The fixture question is TK77's deliverable, noted on that row.

(!) The ceiling control for that census was LEFT-ARMED and is reported as such: the arm that punches an I14 hole before the real call never fired (`holes=0`), precisely because `_entity_has_witness` was never true in-GC. So the measurement supports "the re-add arm is not REACHED here" and does NOT independently re-confirm the 2026-09-18 "269 calls, zero rows" figure, which stays AGENT-MEASURED over a wider run.

SWEEPS. `tests/test_cascade_quiesce_gc.py`: 13 mutations, 13 RED, 0 INERT, M0 and N0 both attributing (table in the module docstring). N2 was INERT on its first form and that is what earned a tightening -- TEST 2b's vacuity guard asked only whether the star target appeared anywhere in a query, which the SUBJECT entries satisfy; it now demands `owner@folder:<star_target>` on the OBJECT side, and N2 reddens. `tests/test_i14_crossing_middles.py`: 5 mutations, 5 RED, 0 INERT, P0 attributing, every row reddening the new pin (table in its docstring). (!) P4's first form died of a `KeyError`, not of the property -- it injected a key that is not derived on that schema, so the cascade blew up in plan lookup before the assertion. It reddened and proved nothing; GL-1's instrument failure verbatim. With a real derived key it dies on the `_settle is None` clause itself.

VERIFY: `pytest tests/test_cascade_quiesce_gc.py tests/test_i14_crossing_middles.py -q` -> `17 passed`. Full ten-phase gate green on this tree.
