"""A REMOVE makes the boolean cascade fail to quiesce -- FIXED 2026-09-17 (`TK73`).

(!) STATUS, 2026-09-17: this probe now exits **0**. The bug is closed; the cause was the
terminal quiescence check testing a SYNTACTIC proxy for a SEMANTIC property, and
reconcile-time node GC pulling the two apart. `index_v4/processor.py::DeltaProcessor
._run_cascade` now ends in a bounded settle-and-assert pass. Full record:
`docs/tk73-cascade-quiesce-gc-2026-09-17.md`; model gap: `formal/CORRESPONDENCE.md` §7.1.

(!) THIS PROBE IS NOT THE ACCEPTANCE SIGNAL, and must never be used as one -- all six of
its controls assert "no failure", so simply DELETING the quiescence check makes it rc=0
exactly as a real fix does (measured 2026-09-17). The positive pin is
`tests/test_cascade_quiesce_gc.py`, which reads the settle pass's own verdict and carries
the sabotage that a round-budget bump cannot pass. This file is kept as the MINIMISED
WITNESS and its ingredient controls, not as a gate.

  Run:  PYTHONPATH=. <env-python> formal/probes/cascade_quiesce_remove_2026-09-16.py

Three writes on a legal boolean schema with NO object wildcards raise

    index_v4.invariants.InvariantViolation: cascade failed to quiesce after 1 strata
    rounds; leftover keys: [('folder', 'owner', 'x')]

out of the graph index's stratified IVM delta processor (`index_v4/processor.py`), on the
REMOVE. The two adds are clean; the removal is what fails to converge.

HOW IT WAS FOUND, and why that matters. It was NOT found by looking for it. It fell out of
the multi-seed fuzz sweep run as the gate's algorithm-change requirement for `TK69`
(`tests/test_hypothesis.py::TestBoolStarBridgeParityMachine`, deep profile,
`--hypothesis-seed=2027`: `1 failed, 29 passed`). Seeds 11 and 909 are green, which is the
whole argument for sweeping more than one seed.

(!) IT IS NOT CAUSED BY THE `TK69` FIX, and that was established before anything was
committed, two independent ways:

  1. the falsifying schema has `object_wildcard_shapes=frozenset()`, so
     `bridged_out_shapes` is empty and `SchemaInfo.crossable_shapes` is EMPTY -- the
     `TK69` hop in `setengine/engine.py::SetEngine._flow_reaches` is unreachable on it;
  2. the minimal witness below reproduces IDENTICALLY against a pre-`TK69` copy of the
     tree (verified genuinely pre-fix: zero occurrences of `_any_entity_of_type`).

Also note the failure is raised from `index_v4/`, and the `TK69` fix touched only
`setengine/`.

-- THE MINIMAL WITNESS, and every ingredient measured ------------------------------------

Each line below was measured by dropping exactly one thing from the witness (2026-09-16).
All five ingredients are REQUIRED; removing any one makes the failure disappear:

    the boolean relation `owner`      drop it                  -> no failure
    the TTU target being ANOTHER      `viewer from parent`     -> no failure
      relation (`admin from parent`)    (self-referential)
    the STAR parent (write 1)         concrete `folder:z`      -> no failure
    the REMOVE                        adds only                -> no failure
    removing write 2 specifically     remove write 1 instead   -> no failure

`editor` and `admin` are never declared on `folder` and the parser accepts the references
anyway; dropping the `editor`/`admin` declarations from the original 5-relation schema
changes nothing. That leniency is NOT this bug, but it is why the witness looks odd.

-- TRANSCRIPT (literal, 2026-09-16, rc=1) ------------------------------------------------

  == the witness ==
    W1+ W2+ W2-: RAISED on remove -> InvariantViolation: cascade failed to quiesce after
                 1 strata rounds; leftover keys: [('folder', 'owner', 'x')]
  == ingredient controls ==
    concrete first parent           : no failure
    W2 add/remove only (no star)    : no failure
    drop `owner` (no boolean)       : no failure
    self-referential TTU            : no failure
    adds only (no remove)           : no failure
    remove the star parent instead  : no failure

(!) THIS PROBE EXITS NONZERO WHILE THE BUG IS OPEN. rc=0 means the cascade now quiesces --
at which point the row that owns this should be closed and a positive pin landed in
`tests/`. Do not "fix" the rc by weakening the witness.
"""
import sys

from tests.test_matrix import GraphBackend

SCHEMA = ('type user\n'
          'type folder\n'
          '  relations\n'
          '    define parent: [folder, folder:*]\n'
          '    define viewer: [user] or admin from parent\n'
          '    define owner: viewer but not editor\n')

W1 = ('...', 'folder', '*', 'parent', 'folder', 'x')   # STAR parent -- required
W2 = ('...', 'folder', 'x', 'parent', 'folder', 'y')

WITNESS = [(W1, 'add'), (W2, 'add'), (W2, 'remove')]

# (label, schema, sequence, ) -- the witness first, then one control per ingredient.
SELF_TTU = SCHEMA.replace('admin from parent', 'viewer from parent')
NO_BOOL = ('type user\ntype folder\n  relations\n'
           '    define parent: [folder, folder:*]\n'
           '    define viewer: [user] or admin from parent\n')
W1_CONCRETE = ('...', 'folder', 'z', 'parent', 'folder', 'x')

CONTROLS = [
    ('concrete first parent', SCHEMA,
     [(W1_CONCRETE, 'add'), (W2, 'add'), (W2, 'remove')]),
    ('W2 add/remove only (no star)', SCHEMA, [(W2, 'add'), (W2, 'remove')]),
    ('drop `owner` (no boolean)', NO_BOOL, WITNESS),
    ('self-referential TTU', SELF_TTU, WITNESS),
    ('adds only (no remove)', SCHEMA, [(W1, 'add'), (W2, 'add')]),
    ('remove the star parent instead', SCHEMA,
     [(W1, 'add'), (W2, 'add'), (W1, 'remove')]),
]


def run(schema, seq):
    """Apply seq; return the exception text, or None if every op succeeded."""
    try:
        g = GraphBackend(schema, frozenset())
    except Exception as e:                                  # pragma: no cover - guard
        return f'schema rejected: {type(e).__name__}: {e}'
    for raw, op in seq:
        try:
            g.apply(raw, op)
        except Exception as e:
            return f'RAISED on {op} -> {type(e).__name__}: {e}'
    return None


def main() -> int:
    print('== the witness ==')
    err = run(SCHEMA, WITNESS)
    print(f'  W1+ W2+ W2-: {err or "no failure"}')

    print('== ingredient controls (each must show NO failure) ==')
    bad_controls = []
    for label, schema, seq in CONTROLS:
        cerr = run(schema, seq)
        print(f'  {label:32}: {cerr or "no failure"}')
        if cerr:
            bad_controls.append(label)

    print()
    if bad_controls:
        print('(!) A CONTROL FIRED -- the witness is no longer minimal, or the failure '
              f'widened: {bad_controls}')
        return 1
    if err is None:
        print('THE CASCADE NOW QUIESCES -- the bug is gone. Close the row and land a '
              'positive pin in tests/.')
        return 0
    print('BUG STILL LIVE: the remove fails to quiesce, and every ingredient is required.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
