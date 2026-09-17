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
moved: 2026-09-17
updated: 2026-09-17
closed: 2026-09-17
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

### 2026-09-17

FIXED. The CHECK was wrong, not the cascade: on the witness the graph's answers were already correct and already a fixpoint, and the terminal quiescence assertion over-fired on membership-NEUTRAL GC traffic.

MECHANISM (first-hand). `_run_cascade` snapshots its frontier at the TOP of a round and reconciles afterwards. A reconcile's step (5) may collect a recorded-subject node (`index_v4/processor.py::DeltaProcessor._gc_subject_node`; `::_reconcile_subject` has its OWN call, so the emitter is not a single call site). That demotes the node (the BL-1 demote-before-strip order), which lets `index_v4/wildcard.py::WildcardIndex._maybe_remove_bridges` strip the star in-bridge, and the ref-counted closure contraction EMITS outbox rows -- after the snapshot, inside the last budgeted round (`rounds = len(strata)`, 1 here). One row carries predicate `owner.0`, so `_map_deltas_to_keys` maps it back to ('folder','owner','x'). The rows are honest BALANCED retractions an external `drain_deltas` replica must see; they are merely membership-neutral, which is why the answer was right while the traffic was real. The old check tested a SYNTACTIC proxy ("no outbox row above the final frontier maps to a derived key") for the SEMANTIC property it wants ("no derived key is stale").

FIX. `::DeltaProcessor._run_cascade` now ends in a bounded SETTLE-AND-ASSERT: reconcile each leftover key once, raise iff that reconcile was NOT a fixpoint (the I9 property), verdict recorded on `::DeltaProcessor._settle` (`::SettlePass`).

(!) THE ROUND BUDGET WAS DELIBERATELY NOT BUMPED, and that is the main result. `rounds = len(strata) + 1` ALSO makes the witness green -- so the witness cannot choose between the two fixes. The sabotage can: with the leftover key made GENUINELY stale, settle-and-assert RAISES "settle pass CHANGED [('folder','owner','x')]" while `rounds+1` goes GREEN, silently repairing it and reporting success. A budget bump is an assurance step that fails by passing. The shipped fix is strictly stronger, not merely different.

(!) THE PROBE IS NOT THE ACCEPTANCE SIGNAL. All six controls of `formal/probes/cascade_quiesce_remove_2026-09-16.py` assert "no failure", so DELETING the quiescence check makes it rc=0 exactly as a real fix does (measured). The obvious white-box pin fails by passing too: `reconcile` is a REPAIRING mutator, so "assert reconcile(...) is False afterwards" passes on corrupted state. PIN: `tests/test_cascade_quiesce_gc.py` (3 tests) reads the settle pass's own verdict before any repairing reconcile, and makes the choosing sabotage permanent. Module mutation sweep: 6 of 7 reddened the test that claims them, M0 control attributed correctly, M6 INERT as predicted.

EVIDENCE. Originating fuzz signal FLIPPED first-hand: `TestBoolStarBridgeParityMachine` deep profile `--hypothesis-seed=2027` was `1 failed`, now `1 passed in 63.63s`; seeds 11 and 909 stay green. Model gap recorded in `formal/CORRESPONDENCE.md` sec 7.1 + sec 7.4 (the Lean theorems are NOT falsified -- `CascadeStrata.lean::W3cJob.applyLoggedR` models a reconcile emitting one coalesced row at its own key, and sec 8.1 already declares node GC unmodeled; TK73 is the third bug found in that region after ZT-P0-1 and BL-1).

MAP: `docs/tk73-cascade-quiesce-gc-2026-09-17.md` (ACTIVE-PLAN) -- carries the rejected alternatives, the two INSTRUMENT FAILURES (a sabotage that removed its own precondition and read as a clean pin; a trigger that never fired because round 1 uses `reconcile_subject`), and four UNVERIFIED items handed forward.
