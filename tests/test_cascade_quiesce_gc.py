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

(!) CORRECTED 2026-09-19b (TK76). This paragraph used to read "the sabotage runs with
paranoia OFF on purpose. With it on, I6 catches the corrupted residue first and the settle
assert -- the instrument under test -- is never reached." That is true of the standalone
.scratch script above, which commits; it is FALSE of the shipped test, which raises inside
``run_cascade`` and never reaches ``session.commit()``. Measured at all four tiers: the
settle clause raises in every arm and none of the messages carries ``_violations_tagged``'s
``store=`` commit-phase prefix. Stronger still: the corruption this test performs is
INVISIBLE to the commit-phase checker -- delete that residue row (or all of them) on a
clean witness store at ``paranoia='full'`` and the commit raises nothing -- so I6 could
not have preempted the settle assert even had the tier really been off. TEST 3 is now
PARAMETRIZED over the tiers and asserts both facts, TEST 4 shows the second assertion can
fail, and the line that was supposed to implement the old claim
(``graph.widx.paranoia = False``) set an attribute that does not exist.
(!) An earlier form of that sabotage fired one reconcile too early and BOTH arms stayed
green with every M0 control passing, because owner@x's residue is the reference that
DEFERS the GC: dropping it early removed the sabotage's own precondition and no settle
pass ever ran. ``test_settle_pass_runs_and_is_a_fixpoint`` asserting the pass RAN is what
distinguishes a clean pin from a sabotage that quietly disarmed itself.

THE MUTATION SWEEP (literal output, 2026-09-19b, `.scratch/tk76/sweep.py`; anchors dated
the same day). 13 mutations, 13 RED, 0 INERT, M0 and N0 both attributing. M-rows are
TK76's, N-rows are TK75's:

    BASELINE  rc=0  12 passed in 1.53s
    M0   RED   attributed=3/3   the tier control's own claim flipped to == 'full'
    M1   RED   attributed=3/3   GraphBackend stops forwarding `paranoia`
    M2   RED   attributed=3/3   the TK76 bug restored (set an attribute instead)
    M3   RED   attributed=4/4   settle pass stops raising on `changed`
    M4   RED   attributed=4/4   settle pass reports `changed=()` regardless
    M5   RED   attributed=9/9   settle pass examines no keys at all
    M6   RED   attributed=1/1   `_violations_tagged` drops the `store=` prefix
    M7   RED   attributed=1/1   TEST 4 corrupts nothing
    N0   RED   attributed=3/3   TEST 2b's expected key hard-coded to witness 1's
    N1   RED   attributed=4/4   `_witness` ignores its argument (the family collapses)
    N2   RED   attributed=3/3   the grid stops naming the star target among its objects
    N2b  RED   attributed=3/3   `_grid` ignores its argument entirely
    N3   RED   attributed=1/1   the no-GC control points at a target that DOES gc
    RESTORED  rc=0  12 passed in 1.57s

(!) READ THE ATTRIBUTION COLUMNS, not just the verdicts. M0/M1/M2 redden the `off`,
`residue` and `fixpoint` arms and leave `full` GREEN -- which is exactly why the
single-arm version of TEST 3 could not have caught the knob failure it claimed to be
controlling for, and why the parametrization is the fix rather than a flourish. M3/M4/M5
redden `full` too, so the settle-pass pins are tier-independent as claimed. N0 leaves the
`x` arm green for the mirror-image reason: witness 1 IS the hard-coded key.

(!) N2's FIRST form was INERT, and the INERT row is what earned the tightening. It
removes `star_target` from the grid's object names, and TEST 2b's vacuity guard then
still passed -- because the guard asked only whether the target appeared ANYWHERE in a
query, and the SUBJECT entries satisfy that. Say what the edit was supposed to move and
check it moved: the guard now demands `owner@folder:<star_target>` on the OBJECT side,
which is the query that can actually catch a wrong answer at the leftover key, and N2
reddens.

(!) The sweep's FIRST run reported `attributed=0/0` on every row -- P6 step 0's instrument
failure verbatim: `pytest -q` does not print nodeids, so the harness's
``FAILED <nodeid>`` regex matched nothing and an all-RED table carried an attribution
column that meant nothing. `-rf` fixed it. A sweep without an M0 control cannot tell that apart from a
clean module.
"""
import pytest
from sqlmodel import select

from zanzibar.graphindex.invariants import (PARANOIA_LEVELS, InvariantViolation,
                                 paranoia_level)
from zanzibar.graphindex.models import Edge, Residue
from zanzibar.setengine import ALL_SETOPS
from tests.oracle import Oracle, OracleTuple
from tests.test_matrix import GraphBackend, SetBackend

#: `admin` and `editor` were UNDECLARED (a dangling TTU target and a dangling computed
#: ref, both read as empty) until ASK-1 (2026-09-26) made that a parse refusal. They are
#: now declared direct relations that no witness write touches, so they are still empty;
#: they go LAST so every relation the witness drives keeps its compile position.
SCHEMA = ('type user\n'
          'type folder\n'
          '  relations\n'
          '    define parent: [folder, folder:*]\n'
          '    define viewer: [user] or admin from parent\n'
          '    define owner: viewer but not editor\n'
          '    define admin: [user]\n'
          '    define editor: [user]\n')

W1 = ('...', 'folder', '*', 'parent', 'folder', 'x')    # STAR parent -- required
W2 = ('...', 'folder', 'x', 'parent', 'folder', 'y')
WITNESS = [(W1, 'add'), (W2, 'add'), (W2, 'remove')]

# The surviving tuple set after the witness: W2 was added and removed again.
SURVIVING = [OracleTuple(*W1)]
LEFTOVER_KEY = ('folder', 'owner', 'x')

#: TK75, 2026-09-19b. The witness generalises on its STAR TARGET: the add/remove pair is
#: always `folder:x parent folder:y`, and only the star write moves. Witness 1 is the
#: E='x' case; the second, independently reported TK73 witness -- leftover
#: `('folder','owner','z')`, recovered by the TK74 fan-out and never re-derived until now
#: -- is the E='z' case. MEASURED first-hand 2026-09-19b: the leftover key is
#: `('folder','owner',E)` for every one of these, i.e. the STAR PARENT'S OBJECT and not
#: the removed edge's object.
STAR_TARGETS = ('x', 'z', 'w', 'q')

#: ⚠ The one star target that is GREEN, and it is a negative control rather than an
#: anomaly. `TK75` recorded it as "UNEXPLAINED -- do not encode the unqualified
#: generalisation in a docstring". EXPLAINED and MEASURED 2026-09-19b, by refcount
#: arithmetic: with E='y' the star write and the concrete write name the SAME object, so
#: `parent@folder:y` is at reference_count **2** before the remove and the remove drops it
#: to 1. Nothing is released, `_demote_released_node` is never called, and the whole
#: reconcile-time-GC chain TK73 is about never starts -- `_settle is None`, not a settle
#: pass that found nothing. At E in STAR_TARGETS that node is at 1 and goes to 0.
#: Pinned, with its cause, by `test_the_star_target_that_shares_the_removed_object`.
STAR_TARGET_NO_GC = 'y'


def _witness(star_target):
    """The three writes, with the star write retargeted. `_witness('x') == WITNESS`."""
    return [(('...', 'folder', '*', 'parent', 'folder', star_target), 'add'),
            (W2, 'add'), (W2, 'remove')]


def _grid(star_target='x'):
    """Every probe path on this schema: concretes, a ghost, and the wildcard name, with
    userset subjects for the TTU from-chain. `star_target` is folded into both the
    subject and the target names so a retargeted witness is actually probed at its own
    entity -- a grid that never mentions E would agree with the oracle vacuously."""
    names = ('x', 'y', 'ghost', '*', star_target)
    subjects = [('...', 'user', 'u1'), ('...', 'user', 'ghost'), ('...', 'user', '*'),
                ('...', 'folder', 'x'), ('...', 'folder', 'y'), ('...', 'folder', '*'),
                ('...', 'folder', star_target),
                ('viewer', 'folder', 'x'), ('owner', 'folder', 'x'),
                ('viewer', 'folder', star_target), ('owner', 'folder', star_target),
                ('admin', 'folder', 'y'), ('parent', 'folder', 'x')]
    targets = [(rel, 'folder', name)
               for rel in ('parent', 'viewer', 'owner')
               for name in dict.fromkeys(names)]
    return [(sp, st, sn, rel, ot, on)
            for (sp, st, sn) in dict.fromkeys(subjects)
            for (rel, ot, on) in targets]


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


@pytest.mark.parametrize('star_target', STAR_TARGETS)
def test_the_witness_generalises_on_its_star_target(star_target):
    """TEST 2b (TK75): the witness is a FAMILY, and the leftover key tracks the STAR
    write's object rather than the removed edge's object.

    This is the second, independently reported TK73 witness -- leftover
    `('folder','owner','z')` -- finally pinned, plus the two further targets that show the
    name is not load-bearing. The add/remove pair is identical in every arm
    (`folder:x parent folder:y`); only the star write moves, and the leftover key moves
    with it. `star_target='x'` is witness 1, kept in the parametrization as the
    overlapping-name arm so a change that only broke the retargeted cases is visible as a
    3-of-4 failure rather than a whole-test failure.

    Both claims are asserted, because they fail differently: the black-box one (answers
    still match the independent oracle and both SetOps over a grid that mentions
    `star_target`) and the white-box one (the settle pass ran, looked at exactly
    `('folder','owner',star_target)`, and found it already at fixpoint).

    (!) The grid is rebuilt per target on purpose. A grid hard-coded to x/y agrees with
    the oracle at `star_target='q'` without ever probing q -- vacuously green."""
    writes = _witness(star_target)
    surviving = [OracleTuple(*writes[0][0])]
    leftover_key = ('folder', 'owner', star_target)

    graph = GraphBackend(SCHEMA, frozenset())
    try:
        for raw, op in writes:
            assert graph.apply(raw, op), f'{op} {raw} was REJECTED'
        graph.post_op()                 # assert_wildcard_invariants + I9 audit_fixpoint

        settle = graph.proc._settle
        assert settle is not None, (
            f'no settle pass ran at star_target={star_target!r} -- the cascade drained '
            f'without reaching the assertion, so this arm is green for an unrelated '
            f'reason (that is what star_target={STAR_TARGET_NO_GC!r} does, and why it is '
            f'a separate test with its cause pinned)')
        assert list(settle.keys) == [leftover_key], (
            f'settle pass examined {list(settle.keys)}, expected [{leftover_key}] -- the '
            f'leftover key is supposed to follow the STAR write, not the removed edge')
        assert settle.changed == (), (
            f'settle pass found genuine staleness at {list(settle.changed)}')

        oracle = Oracle(SCHEMA, surviving)
        sets = [SetBackend(SCHEMA, frozenset(), ops) for ops in ALL_SETOPS]
        try:
            for s in sets:
                for raw, op in writes:
                    assert s.apply(raw, op), f'{s.name} REJECTED {op} {raw}'
            grid = _grid(star_target)
            # ⚠ Instrument control, and it must name the OBJECT side. "the grid mentions
            # star_target somewhere" is satisfied by the subject entries alone and was
            # INERT under the sweep's N2 arm (2026-09-19b); the query that can actually
            # catch a wrong answer at the leftover key is `owner@folder:<star_target>`.
            assert any(q[3:] == ('owner', 'folder', star_target) for q in grid), (
                f'the grid never probes owner@folder:{star_target} -- it would agree '
                f'with the oracle vacuously, INSTRUMENT BROKEN')
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


def test_the_star_target_that_shares_the_removed_object():
    """TEST 2c (TK75): the ONE star target that runs no settle pass, and WHY.

    `TK75` recorded that the leftover appears for star targets x/z/w/q but not for 'y',
    and labelled that green **UNEXPLAINED**, with the standing instruction not to encode
    the unqualified generalisation in a docstring. MEASURED and explained 2026-09-19b, and
    it is refcount arithmetic rather than anything about the cascade: at
    `star_target='y'` the star write and the concrete write name the SAME object, so
    `parent@folder:y` carries **two** references going into the remove. The remove takes
    it to 1, nothing is released, `_demote_released_node` is never called, no
    reconcile-time GC runs, nothing is emitted late, and the cascade drains with an empty
    `leftover` -- so `_settle` is None because the pass never ran, NOT because it ran and
    found nothing.

    (!) The refcount assertion is the load-bearing one. `assert _settle is None` alone
    would stay green for any future reason the cascade stops reaching this code, which is
    precisely the shape TK75's own trap warns about: an un-fireable probe reads exactly
    like a clean surface. TEST 2b is the positive arm -- the same three writes with the
    star elsewhere DO produce a settle pass."""
    writes = _witness(STAR_TARGET_NO_GC)
    graph = GraphBackend(SCHEMA, frozenset())
    demoted = []
    try:
        for raw, op in writes[:-1]:
            assert graph.apply(raw, op), f'{op} {raw} was REJECTED'

        shared = graph.widx.idx.node('parent', 'folder', STAR_TARGET_NO_GC,
                                     create_if_missing=False)
        assert shared.reference_count == 2, (
            f'parent@folder:{STAR_TARGET_NO_GC} is at reference_count '
            f'{shared.reference_count}, expected 2 (the star write and the concrete '
            f'write) -- the premise of this whole test is gone, so its green means '
            f'nothing')

        original = graph.proc._demote_released_node
        graph.proc._demote_released_node = lambda n, *a, **k: (
            demoted.append((n.predicate, n.name)), original(n, *a, **k))[1]

        assert graph.apply(*writes[-1]), 'the remove was REJECTED'

        assert demoted == [], (
            f'a node WAS released at star_target={STAR_TARGET_NO_GC!r} ({demoted}), so '
            f'the reconcile-time GC did run and this test no longer explains the green')
        assert graph.proc._settle is None, (
            f'a settle pass ran after all: {graph.proc._settle}')
        assert graph.widx.idx.node(
            'parent', 'folder', STAR_TARGET_NO_GC,
            create_if_missing=False).reference_count == 1, (
            'the shared parent node did not drop to exactly one reference')
        graph.post_op()
    finally:
        graph.close()


@pytest.mark.parametrize('tier', PARANOIA_LEVELS)
def test_settle_pass_detects_genuine_staleness(tier):
    """TEST 3: the settle assert has TEETH -- on genuinely stale state it RAISES, and it
    is the settle assert that raises AT EVERY PARANOIA TIER.

    The choosing sabotage, made permanent (docs/sabotage-procedure.md ranks a permanent
    test above a recorded transcript). The corruption lands immediately before the settle
    pass's own reconcile -- the moment a round-budget bump would instead have silently
    repaired it.

    (!) TK76, 2026-09-19b. This test used to run one arm and open with
    ``graph.widx.paranoia = False`` under a docstring claiming "Paranoia is OFF so the
    settle assert is the instrument under test rather than I6". BOTH halves were wrong.
    ``WildcardIndex`` has no ``paranoia`` attribute (``grep -c paranoia
    src/zanzibar/graphindex/wildcard.py`` -> 0), so that line created a fresh instance attribute nothing
    reads and the arm actually ran at FULL paranoia -- the project's house failure mode,
    a control that fails by passing, sitting inside the module that pins TK73. And the
    rationale was false in its premise too: the tier is IRRELEVANT here, because the
    settle assert raises inside ``run_cascade``, before ``session.commit()``, so no
    commit-time checker can preempt it. MEASURED 2026-09-19b at all four tiers --
    ``settle-clause=True commit-prefix=False`` in every arm, with
    ``fired=1 row_existed=True``.

    So the fix is not to restore the claimed control but to make it REAL and mechanical:
    the tier is threaded through ``GraphBackend`` (``install_paranoia`` can only RAISE,
    so it cannot produce an off store after construction), ``paranoia_level`` is asserted
    to be the tier actually requested -- the TK74 sec 9.7 lesson, a tier knob that does
    not forward is a lie -- and the raise is asserted to carry NO ``store=`` prefix,
    which is what ``_violations_tagged`` adds at commit time. That last assertion is the
    mechanical form of "the settle assert is the instrument under test"."""
    graph = GraphBackend(SCHEMA, frozenset(), paranoia=tier)
    try:
        # THE INSTRUMENT CONTROL. Read the registry, which IS the authority: a knob that
        # silently did not forward would leave this equal to 'full' on every arm.
        assert paranoia_level(graph.session, 'g') == tier, (
            f'asked for paranoia={tier!r}, store is at '
            f'{paranoia_level(graph.session, "g")!r} -- the tier did not forward, so '
            f'this arm is not the arm it says it is')
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
                            select(Residue)
                            .where(Residue.store_id == 'g')
                            .where(Residue.object_node_id == node.id)).first()
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
        # ``_violations_tagged`` prefixes every commit-phase violation with
        # ``store=... [pre-commit]``/``[post-commit]``. Its ABSENCE is the mechanical
        # proof that a paranoia checker did not get there first -- which is what the old
        # docstring asserted in prose and never checked.
        assert not str(exc.value).startswith('store='), (
            f'a commit-phase paranoia check raised first at tier {tier!r}, so the '
            f'settle assert is not the instrument under test here: {exc.value}')
    finally:
        graph.session.rollback()
        graph.close()


def test_a_commit_phase_violation_is_tagged_so_test_3_can_tell_them_apart():
    """TEST 4: the INSTRUMENT CONTROL for TEST 3's last assertion.

    TEST 3 ends with ``not str(exc.value).startswith('store=')`` and reads it as "no
    commit-phase paranoia check got there first". An assertion no arm can ever fail is a
    false green, so this test shows the discriminator FIRES: corrupt state that the
    commit-phase checker does catch, and its message is prefixed by
    ``_violations_tagged`` exactly as TEST 3 assumes.

    (!) MEASURED 2026-09-19b, and it is why TEST 3's four arms are not redundant: the
    residue-row deletion TEST 3 performs is INVISIBLE to the commit-phase checker.
    Deleting that row (or every residue row, or bumping a version) and committing at
    ``paranoia='full'`` raises NOTHING. So the module docstring's old "with paranoia on,
    I6 catches the corrupted residue first" was false in both directions -- the tier was
    never off, and it would not have preempted anything if it had been on. A closure edge
    is the corruption that does reach the checker (I13)."""
    graph = GraphBackend(SCHEMA, frozenset(), paranoia='full')
    try:
        _apply_witness(graph)
        edge = graph.session.exec(
            select(Edge).where(Edge.store_id == 'g')).first()
        assert edge is not None, (
            'no closure edge on the witness store -- INSTRUMENT BROKEN, there is '
            'nothing here to corrupt and this test asserts nothing')
        graph.session.delete(edge)

        with pytest.raises(InvariantViolation) as exc:
            graph.session.commit()

        assert str(exc.value).startswith("store='g' [pre-commit]"), (
            f'a commit-phase violation did NOT carry the store/phase prefix, so TEST '
            f"3's `not startswith('store=')` assertion discriminates nothing: "
            f'{exc.value}')
    finally:
        graph.session.rollback()
        graph.close()
