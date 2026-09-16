---
id: TK73
title: LIVE BUG: a REMOVE makes the boolean cascade fail to quiesce (star parent + TTU + boolean)
brief: found by the TK69 fuzz sweep, seed 2027; PROVEN pre-existing; 3 writes, no object wildcards, InvariantViolation
pri: NOW
size: M
deps: []
related: [TK69]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-16b
moved: 2026-09-16b
updated: 2026-09-16b
closed:
---

## What it is

**A LIVE CORRECTNESS BUG.** Three writes on a legal boolean schema with NO object
wildcards raise, out of the graph index's stratified IVM delta processor:

    index_v4.invariants.InvariantViolation: cascade failed to quiesce after 1 strata
    rounds; leftover keys: [('folder', 'owner', 'x')]

The two adds are clean. **The REMOVE is what fails to converge.** Tracked evidence, with
the literal transcript and one control per ingredient:
[`formal/probes/cascade_quiesce_remove_2026-09-16.py`](../formal/probes/cascade_quiesce_remove_2026-09-16.py)
(rc=1 while this row is open, by design).

    type user
    type folder
      relations
        define parent: [folder, folder:*]
        define viewer: [user] or admin from parent
        define owner: viewer but not editor

    add    ('...', 'folder', '*', 'parent', 'folder', 'x')     <- STAR parent
    add    ('...', 'folder', 'x', 'parent', 'folder', 'y')
    remove ('...', 'folder', 'x', 'parent', 'folder', 'y')     <- RAISES

## How it was found

NOT by looking for it. It fell out of the multi-seed fuzz sweep run as the gate's
algorithm-change requirement for `TK69`:
`tests/test_hypothesis.py::TestBoolStarBridgeParityMachine`, deep profile,
`--hypothesis-seed=2027` -> `1 failed, 29 passed`. **Seeds 11 and 909 are GREEN**, which is
the entire argument for sweeping more than one seed rather than one.

## (!) Traps

- **(!) IT IS NOT THE `TK69` FIX, and this was settled BEFORE anything was committed.**
  Two independent proofs: (1) the falsifying schema has `object_wildcard_shapes=frozenset()`,
  so `bridged_out_shapes` is empty, so `SchemaInfo.crossable_shapes` is EMPTY -- the `TK69`
  hop in `setengine/engine.py::SetEngine._flow_reaches` is unreachable on it; (2) the
  minimal witness reproduces IDENTICALLY on a pre-`TK69` copy of the tree (verified
  genuinely pre-fix: zero occurrences of `_any_entity_of_type`). The failure is also raised
  from `index_v4/`, and the `TK69` fix touched only `setengine/`. **Do not re-litigate this
  by reverting `TK69`.**
- **(!) EVERY INGREDIENT IS REQUIRED -- MEASURED, one drop at a time.** Drop the boolean
  relation `owner` -> no failure. Make the TTU self-referential (`viewer from parent`
  instead of `admin from parent`) -> no failure. Make the first parent concrete instead of
  `folder:*` -> no failure. Adds only, no remove -> no failure. Remove write 1 instead of
  write 2 -> no failure. **So it is specifically: a STAR parent, a TTU onto a DIFFERENT
  relation, a boolean relation over it, and a REMOVE.** A "simplification" of the witness
  will silently stop testing it -- the probe carries all five controls and fails loudly if
  one starts firing.
- **(!) `editor` and `admin` are never DECLARED on `folder` and the parser accepts the
  references anyway.** That leniency is NOT this bug (the original 5-relation falsifying
  schema declared both, and dropping the declarations changed nothing), but it is why the
  witness looks odd. If you think the undeclared reference is the cause, re-read the
  controls: the declared 5-relation form fails identically.
- **(!) "cascade failed to quiesce" is a CONVERGENCE failure, not a refusal.** Do not treat
  it as an admission question (that is `TK70`) and do not "fix" it by raising the strata
  round budget until it passes -- the leftover key means the delta processor's fixpoint
  reasoning disagrees with its own stratification on this shape. Find out WHY
  `('folder','owner','x')` is still dirty after the declared number of rounds.
- **(!) The board line "Known live correctness bugs: 0" is FALSE while this is open.**

## Read first

- [`formal/probes/cascade_quiesce_remove_2026-09-16.py`](../formal/probes/cascade_quiesce_remove_2026-09-16.py)
  -- the witness, the literal transcript, and the five ingredient controls.
- `index_v4/processor.py` -- the delta processor; the quiescence check and the strata-round
  budget that reports `leftover keys`. The hypothesis explanation fingered
  `index_v4/processor.py:1589` as a line run ONLY by failing cases (2026-09-16; line
  numbers rot -- resolve it by content, not by number).
- `tests/test_hypothesis.py::TestBoolStarBridgeParityMachine` and the comment block above
  `_star_bridge_schema` -- the generator that found it, and the reg9/reg10/reg11 history of
  this schema class.
- `index_v4/invariants.py` -- what the quiescence assertion guarantees, and what a leftover
  key means for the state left behind after the raise (is the store still consistent?).

## Log
