"""TK73: the boolean cascade must QUIESCE on a remove that triggers reconcile-time GC.

The bug (found 2026-09-16 by the multi-seed fuzz sweep the gate requires for an algorithm
change -- ``TestBoolStarBridgeParityMachine``, deep profile, ``--hypothesis-seed=2027``;
seeds 11 and 909 were green): three writes on a legal boolean schema with NO object
wildcards raised, on the REMOVE,

    InvariantViolation: cascade failed to quiesce after 1 strata rounds;
                        leftover keys: [('folder', 'owner', 'x')]

WHY IT HAPPENED. A reconcile's step (5) may collect a recorded-subject node
(``DeltaProcessor._gc_subject_node``). That demotes the node and hands it to
``WildcardIndex._maybe_remove_bridges``, whose strip contracts ref-counted closure edges
and EMITS outbox rows -- after the round's frontier snapshot, and on the last budgeted
round nothing drains them. The rows are honest, balanced retractions (rows #13/#14/#15
exactly retract #7/#5/#6 on node 9, measured 2026-09-17) but membership-NEUTRAL, so the
derived key they map back to is ALREADY at its fixpoint. The old check tested a SYNTACTIC
proxy -- "no outbox row above the final frontier maps to a derived key" -- for the
SEMANTIC property it wanted, "no derived key is stale". Late GC emission pulls them apart.

WHY THESE THREE TESTS, AND NOT THE OBVIOUS ONE. Two weaker pins were tried and rejected:

  * ``formal/probes/cascade_quiesce_remove_2026-09-16.py`` CANNOT be the acceptance
    signal. All six of its controls assert "no failure", so simply DELETING the
    quiescence check makes it rc=0 exactly as a real fix does (verified 2026-09-17).
  * "after the remove, assert ``reconcile(...) is False`` and ``audit_fixpoint()``
    passes" FAILS BY PASSING: ``reconcile`` is a REPAIRING mutator, so on genuinely stale
    state the first call repairs and every later call returns False. The assertion passes
    on corrupted state.

So the pin observes the settle pass's OWN verdict, recorded on ``DeltaProcessor._settle``
before any repairing reconcile can launder it (``test_settle_pass_runs_and_is_a_fixpoint``),
and ``test_settle_pass_detects_genuine_staleness`` makes the choosing sabotage permanent.

THE SABOTAGE RECORD (literal output, 2026-09-17, `.scratch/tk73-lead/sabotage_settle_vs_budget.py`,
rc=0). Both candidate fixes make the witness green, so the witness cannot choose between
them. Making the leftover key genuinely stale does:

    == unsabotaged: both arms must be GREEN (the witness cannot choose) ==
      A settle-and-assert   : green   settle=([('folder', 'owner', 'x')], [])
      B rounds+1            : green
    == SABOTAGED (owner@x residue dropped after its productive reconcile) ==
      A settle-and-assert   : RAISED: cascade failed to quiesce after 1 strata rounds;
                              the settle pass CHANGED derived state at
                              [('folder', 'owner', 'x')] -- those keys were genuinely
                              stale (leftover keys: [('folder', 'owner', 'x')])
      B rounds+1            : green

``rounds = len(strata) + 1`` SILENTLY REPAIRS the staleness and reports success. That is
why the round budget was deliberately left alone: a budget bump is an assurance step that
fails by passing, this repo's house failure mode.

(!) The sabotage runs with paranoia OFF on purpose. With it on, I6 catches the corrupted
residue first and the settle assert -- the instrument under test -- is never reached.
(!) An earlier form of that sabotage fired one reconcile too early and BOTH arms stayed
green with every M0 control passing, because owner@x's residue is the reference that
DEFERS the GC: dropping it early removed the sabotage's own precondition and no settle
pass ever ran. ``test_settle_pass_runs_and_is_a_fixpoint`` asserting the pass RAN is what
distinguishes a clean pin from a sabotage that quietly disarmed itself.
"""
import pytest
from sqlmodel import select

from index_v4.invariants import InvariantViolation
from index_v4.models import ResidueV1
from setengine import ALL_SETOPS
from tests.oracle import Oracle, OracleTuple
from tests.test_matrix import GraphBackend, SetBackend

SCHEMA = ('type user\n'
          'type folder\n'
          '  relations\n'
          '    define parent: [folder, folder:*]\n'
          '    define viewer: [user] or admin from parent\n'
          '    define owner: viewer but not editor\n')

W1 = ('...', 'folder', '*', 'parent', 'folder', 'x')    # STAR parent -- required
W2 = ('...', 'folder', 'x', 'parent', 'folder', 'y')
WITNESS = [(W1, 'add'), (W2, 'add'), (W2, 'remove')]

# The surviving tuple set after the witness: W2 was added and removed again.
SURVIVING = [OracleTuple(*W1)]
LEFTOVER_KEY = ('folder', 'owner', 'x')


def _grid():
    """Every probe path on this schema: concretes, a ghost, and the wildcard name, with
    userset subjects for the TTU from-chain."""
    subjects = [('...', 'user', 'u1'), ('...', 'user', 'ghost'), ('...', 'user', '*'),
                ('...', 'folder', 'x'), ('...', 'folder', 'y'), ('...', 'folder', '*'),
                ('viewer', 'folder', 'x'), ('owner', 'folder', 'x'),
                ('admin', 'folder', 'y'), ('parent', 'folder', 'x')]
    targets = [(rel, 'folder', name)
               for rel in ('parent', 'viewer', 'owner')
               for name in ('x', 'y', 'ghost', '*')]
    return [(sp, st, sn, rel, ot, on)
            for (sp, st, sn) in subjects for (rel, ot, on) in targets]


def _apply_witness(backend):
    for raw, op in WITNESS:
        assert backend.apply(raw, op), f'{op} {raw} was REJECTED'


def test_witness_commits_and_agrees_with_the_oracle():
    """TEST 1 (black-box): all three writes commit, and the graph's answers match the
    independent oracle AND both set-engine SetOps over the full grid.

    This is the answer-level claim: the cascade's result was always CORRECT -- the raise
    was the check over-firing on membership-neutral GC traffic, not a wrong answer."""
    graph = GraphBackend(SCHEMA, frozenset())
    try:
        _apply_witness(graph)
        graph.post_op()                 # assert_wildcard_invariants + I9 audit_fixpoint

        oracle = Oracle(SCHEMA, SURVIVING)
        sets = [SetBackend(SCHEMA, frozenset(), ops) for ops in ALL_SETOPS]
        try:
            for s in sets:
                _apply_witness(s)
            grid = _grid()
            assert grid, 'empty grid -- this test would assert nothing'
            for q in grid:
                want = oracle.check(*q)
                assert graph.check(q) == want, f'graph vs oracle disagree on {q}'
                for s in sets:
                    assert s.check(q) == want, f'{s.name} vs oracle disagree on {q}'
        finally:
            for s in sets:
                s.session.close()
    finally:
        graph.close()


def test_settle_pass_runs_and_is_a_fixpoint():
    """TEST 2 (white-box): the terminal settle pass RAN on the witness, looked at exactly
    the leftover key, and found it already at fixpoint.

    ``_settle`` is read instead of calling ``reconcile`` afterwards because reconcile
    REPAIRS: a post-hoc call returns False on stale state too, so it cannot tell the two
    apart. Asserting the pass ran is also what catches a sabotage that disarmed itself.
    A plain round-budget bump cannot make this assertion true -- it has no settle pass."""
    graph = GraphBackend(SCHEMA, frozenset())
    try:
        _apply_witness(graph)
        settle = graph.proc._settle
        assert settle is not None, (
            'no settle pass ran on the witness -- the cascade drained without reaching '
            'the assertion, so this module is green for an unrelated reason')
        assert list(settle.keys) == [LEFTOVER_KEY], (
            f'settle pass examined {list(settle.keys)}, expected [{LEFTOVER_KEY}]')
        assert settle.changed == (), (
            f'settle pass found genuine staleness at {list(settle.changed)} -- the '
            f'cascade left a derived key stale')
    finally:
        graph.close()


def test_settle_pass_detects_genuine_staleness():
    """TEST 3: the settle assert has TEETH -- on genuinely stale state it RAISES.

    The choosing sabotage, made permanent (docs/sabotage-procedure.md ranks a permanent
    test above a recorded transcript). Paranoia is OFF so the settle assert is the
    instrument under test rather than I6, and the corruption lands immediately before the
    settle pass's own reconcile -- the moment a round-budget bump would instead have
    silently repaired it."""
    graph = GraphBackend(SCHEMA, frozenset())
    try:
        graph.widx.paranoia = False
        proc = graph.proc
        original = proc.reconcile
        state = {'seen': 0, 'fired': 0, 'row_existed': None}

        def wrapped(object_type, rel, obj_name):
            if state['armed'] and (object_type, rel, obj_name) == LEFTOVER_KEY:
                state['seen'] += 1
                if state['fired'] == 0:
                    state['fired'] += 1
                    node = graph.widx.idx.node('owner', 'folder', 'x',
                                               create_if_missing=False)
                    row = None
                    if node is not None:
                        row = graph.session.exec(
                            select(ResidueV1)
                            .where(ResidueV1.store_id == 'g')
                            .where(ResidueV1.object_node_id == node.id)).first()
                    state['row_existed'] = row is not None
                    if row is not None:
                        graph.session.delete(row)
                        graph.session.flush()
            return original(object_type, rel, obj_name)

        proc.reconcile = wrapped
        state['armed'] = False
        for raw, op in WITNESS[:-1]:
            assert graph.apply(raw, op)
        state['armed'] = True

        with pytest.raises(InvariantViolation) as exc:
            graph.apply(*WITNESS[-1])

        # Control the instrument before believing the result: a sabotage that never
        # fired, or deleted a row that was not there, proves nothing.
        assert state['fired'] == 1, f"sabotage fired {state['fired']}x, expected 1"
        assert state['row_existed'] is True, (
            'the residue row did not exist, so deleting it was a no-op -- INSTRUMENT '
            'BROKEN, this test asserted nothing')
        assert 'settle pass CHANGED' in str(exc.value), (
            f'raised, but not from the settle assert: {exc.value}')
        assert str(LEFTOVER_KEY) in str(exc.value)
    finally:
        graph.session.rollback()
        graph.close()
