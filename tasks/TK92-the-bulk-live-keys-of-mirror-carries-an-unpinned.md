---
id: TK92
title: the bulk _live_keys_of mirror carries an unpinned copy of the line TK91 just pinned
brief: deleting [rel] from bulk_backfill.py:811 leaves 4 modules at 29 passed; unreachable-by-construction is UNPROVED
pri: LATER
size: S
deps: []
related: [TK91]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-20f
moved: 2026-09-20f
updated: 2026-09-20f
closed:
---

`index_v4/bulk_backfill.py:811` carries its OWN `_live_keys_of`, a mirror of
`index_v4/processor.py::DeltaProcessor._live_keys_of` including the leading `rel` term in
`preds`. `TK91` pinned the processor's copy on 2026-09-20f
(`tests/test_reg_tk91_live_keys_repair.py`). The mirror is UNPINNED.

MEASURED 2026-09-20f, first-hand, twice by two agents independently:

* Deleting `[rel]` from the BULK mirror leaves `tests/test_reg_tk91_live_keys_repair.py`,
  `tests/test_backfill_enumeration.py`, `tests/test_bulk_build.py` and
  `tests/test_invariants_derived.py` at `29 passed`.
* The `TK91` bulk arm cannot see it either: over all 130 (corpus, seed) survivor cells the
  top-level live-key enumeration is IDENTICAL clean vs mutated
  (`LIVE-KEY ENUMERATION IDENTICAL clean vs M16`).

WHY THAT IS NOT AUTOMATICALLY A HOLE, and why this row exists rather than a fix.
The processor's `rel` term is a REPAIR AFFORDANCE reachable only on an INCONSISTENT store
(that is the whole finding of `TK91` -- see
[`docs/tk91-tk80-removal-coverage-2026-09-20.md`](../docs/tk91-tk80-removal-coverage-2026-09-20.md)
section 4.2). The bulk path may have no inconsistent store to repair:
`connectedstore/build.py::build_index` "refuses to run on an index that already has state",
so the bulk backfill arguably only ever runs over a pre-backfill state it constructed itself.

(!) THAT ARGUMENT IS **REASONED, AND NOBODY HAS PROVED IT.** It is recorded in
`tests/test_reg_tk91_live_keys_repair.py`'s docstring as a hypothesis, explicitly labelled.
Scope was deliberately not widened on 2026-09-20f.

## The two honest outcomes

1. **The term is unreachable by construction in the bulk path.** Then it is DEAD CODE in a
   mirror, and the right move is to delete it and say so -- or to leave it with a comment
   that cites the proof. Either way the proof has to exist.
2. **It is reachable.** Then it is an unpinned copy of a line whose deletion is a live
   authorization FAIL-OPEN on the processor side (`check` stays True after a retracted
   grant, and I9 reports OK because it enumerates through the same crippled function). That
   would want the same treatment `TK91` gave the original.

## First action

Decide which, with evidence, before writing any test. The cheap probe is to ask whether any
reachable call sequence puts the bulk backfill in front of a store carrying derived state
that outlives its leaf -- `.scratch/tk91-tk80/probe_stale.py` is the shape of the
reproduction on the processor side and was promoted into
`tests/test_reg_tk91_live_keys_repair.py`.

(!) Do NOT pin it by mutating the mirror and hunting for something that reddens. That is
how an INERT row gets written up as a clean pin. Say what the edit is supposed to move, and
check it moved (`docs/sabotage-procedure.md`).

## Read first

- [`docs/tk91-tk80-removal-coverage-2026-09-20.md`](../docs/tk91-tk80-removal-coverage-2026-09-20.md)
  section 4.2 (what the `rel` term guards, and the fail-open it prevents) and section 8.2
  (this trap, alongside the other still-unpinned weakenings found by the same sweeps).
- `tests/test_reg_tk91_live_keys_repair.py` -- the processor-side pin and the hypothesis.

## Log
