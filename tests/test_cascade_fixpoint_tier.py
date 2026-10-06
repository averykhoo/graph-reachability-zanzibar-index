"""TK82: the opt-in ``'fixpoint'`` paranoia tier -- the per-cascade I9 check.

WHAT IT IS. After a boolean cascade drains, re-reconcile every key the cascade
SCHEDULED and require each to be a fixpoint (I9). It is the only detector for an
*execution-side* missed reconcile: TK74 established that the terminal settle pass is
structurally blind to one *within the cascade that skipped it*
(``docs/tk74-staleness-net-2026-09-18.md`` §9.2), and that no I1-I12 clause fires on the
closure-edge-only staleness a skip leaves behind (§8.4, narrowed in §9.6). Ranked above
``'full'`` so nothing selects it implicitly; roughly doubles cascade cost, so it is a
diagnosis tier, never a production one. Design and the two decisions this module pins:
``docs/tk82-cascade-fixpoint-tier-2026-09-19.md``.

⚠ WHY THE SABOTAGE IS A PERMANENT TEST AND NOT A TRANSCRIPT. On unmutated traffic the
cascade's SCHEDULED-key union and its DISPATCHED (reconciled) set are byte-identical --
``union_minus_dispatched = 0`` over 3,744 clean cascades (TK74 §10.3, 2026-09-18c). The
right design and the wrong one therefore have the same cost, the same union size and the
same (zero) false-positive rate: **no benchmark and no clean-traffic test can tell them
apart.** Only fault injection can. Without ``test_sabotage_reconciled_union_ships_dead``
a refactor could re-source the union from the execution side and every other signal in
this repo would stay green while the detector shipped dead.

THE SABOTAGE RECORD (literal output, 2026-09-19, ``.scratch/tk82/probe3.py``, on
``demorgans_reverse`` with the reconcile of ``('cond','requirement_not_met','c1')``
suppressed inside the cascade loop):

    == skip ('cond', 'requirement_not_met', 'c1')                 [scheduled union]
        skipped=1 dispatched=[('attr', 'does_not_label', 'a1')]
        union=[('attr','does_not_label','a1'), ('cond','requirement_not_met','c1')]
        changed=[('cond', 'requirement_not_met', 'c1')]
        RAISED: I9: the cascade left derived state STALE at
                [('cond', 'requirement_not_met', 'c1')] ...
    == SABOTAGE reconciled-union, skip requirement_not_met
        skipped=1 dispatched=[('attr', 'does_not_label', 'a1')]
        union=[('attr', 'does_not_label', 'a1')]
        changed=[]
        NO RAISE
    == tier OFF (full), skip requirement_not_met
        union=None  changed=None  NO RAISE

Read the sabotage arm's union: it is **non-empty** (one key), not trivially empty. A
reconciled-union tier looks alive -- it examines keys, it costs the same -- and is blind,
because the skipped key is absent from the dispatched set *by construction*: its
reconcile is precisely what did not run.

CONTROLS, and why each is here rather than assumed:
  * the skip must make the store GENUINELY WRONG, or the raise is an artifact --
    ``test_the_suppressed_reconcile_makes_the_store_oracle_wrong`` measures 4 divergences
    over a 49-query grid against the independent oracle, with the tier OFF.
  * the fault injection must have FIRED -- every arm asserts ``skipped == 1``. A sabotage
    that quietly disarmed itself reads exactly like a clean pin (TK73's earlier form did).
  * the tier must be the INSTRUMENT, never the subject -- the suppression is lifted the
    moment ``_check_cascade_fixpoint`` is entered. Left armed, it suppresses the tier's
    OWN re-reconcile of the skipped key and every arm comes back green
    (``.scratch/tk82/probe2.py``, 2026-09-19: four skips, four ``NO RAISE``). That is the
    instrument failing in the direction that looks like a clean result.
  * ``'full'`` must NOT imply the tier (it is opt-in) AND must be implied BY it (it sits
    above ``full`` on the ladder) -- the two halves of the placement decision, pinned by
    ``test_full_does_not_imply_the_tier`` and ``test_fixpoint_tier_is_at_least_full``.
    The second guards a real trap: ``ParanoiaGuard``'s listeners branched on
    ``level == PARANOIA_FULL``, so appending a rank above ``full`` routed the STRONGEST
    tier into the residue branch and made it weaker than ``full``.
"""
import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from zanzibar.connectedstore import ConnectedStore
from zanzibar.graphindex.invariants import (InvariantViolation, PARANOIA_ENV_VAR,
                                 PARANOIA_FIXPOINT, PARANOIA_FULL,
                                 install_paranoia, paranoia_at_least)
from zanzibar.graphindex.models import Node
from zanzibar.graphindex.outbox import outbox_watermark
from tests.oracle import Oracle, OracleTuple
from tests.test_cascade_quiesce_gc import (LEFTOVER_KEY as GC_LEFTOVER_KEY,
                                           SCHEMA as GC_SCHEMA, WITNESS as GC_WITNESS)
from tests.test_matrix import GraphBackend
from tests.wildcard_helpers import make_wildcard_index
from zanzibar.schema import parse_openfga_schema

SCHEMA = ('model\n'
          '  schema 1.1\n'
          'type doc\n'
          'type attr\n'
          '  relations\n'
          '    define _all_docs: [doc:*]\n'
          '    define labels: [doc]\n'
          '    define does_not_label: _all_docs but not labels\n'
          'type cond\n'
          '  relations\n'
          '    define _all_docs: [doc:*]\n'
          '    define requires: [attr]\n'
          '    define requirement_not_met: does_not_label from requires\n'
          '    define requirement_met: _all_docs but not requirement_not_met\n'
          'type role\n'
          '  relations\n'
          '    define match_any: [cond]\n'
          '    define access: requirement_met from match_any\n'
          'type user\n'
          '  relations\n'
          '    define assigned: [role]\n'
          '    define access: access from assigned\n')

# Five strata, so a skip at a non-final one leaves work provably downstream of it.
SETUP = [(('...', 'doc', '*', '_all_docs', 'attr', 'a1'), 'add'),
         (('...', 'doc', '*', '_all_docs', 'cond', 'c1'), 'add'),
         (('...', 'attr', 'a1', 'requires', 'cond', 'c1'), 'add'),
         (('...', 'cond', 'c1', 'match_any', 'role', 'r1'), 'add'),
         (('...', 'role', 'r1', 'assigned', 'user', 'u1'), 'add')]
TARGET = (('...', 'doc', 'd1', 'labels', 'attr', 'a1'), 'add')

#: The cascade the target write drives, one key per stratum, SORTED (the tier reports
#: sorted). Written down rather than derived so a change in scheduling is a visible
#: failure and not a silently smaller test.
CASCADE_KEYS = [('attr', 'does_not_label', 'a1'),
                ('cond', 'requirement_met', 'c1'),
                ('cond', 'requirement_not_met', 'c1'),
                ('role', 'access', 'r1'),
                ('user', 'access', 'u1')]
#: Every key but the TOP of the dependency order. A skip at ``('user','access','u1')``
#: schedules nothing downstream of itself, so it is a weaker arm; the detection claim is
#: made against the four that do have dependents.
NON_FINAL_KEYS = [k for k in CASCADE_KEYS if k != ('user', 'access', 'u1')]


class Arm:
    """One fault-injected cascade: build the store, suppress ONE key's reconcile inside
    the cascade loop, run the target write's cascade, report what the tier concluded."""

    def __init__(self, level, skip_key=None, union_from_reconciled=False):
        self.graph = GraphBackend(SCHEMA, frozenset())
        install_paranoia(self.graph.session, 'g', self.graph.ruleset.schema_info,
                         level=level)
        for raw, op in SETUP:
            assert self.graph.apply(raw, op), f'setup write rejected: {raw}'
        self.proc = self.graph.proc
        self.skipped = 0
        self.dispatched = []
        #: Whether the cascade's own node-resolution cache was still installed when the
        #: tier ran. It must not be -- see ``test_the_tier_runs_outside_the_cache_scopes``.
        self.cache_scope_open = None
        self._armed = False
        self._skip_key = skip_key
        self._recon_union = union_from_reconciled
        o_rec, o_recs = self.proc.reconcile, self.proc.reconcile_subject
        o_check = self.proc._check_cascade_fixpoint

        def suppress(key) -> bool:
            if not self._armed:
                return False
            if key == self._skip_key:
                self.skipped += 1
                return True
            self.dispatched.append(key)
            # THE SABOTAGE: re-source the union from the EXECUTION side. One symbol.
            if self._recon_union and self.proc._tier_union is not None:
                self.proc._tier_union.add(key)
            return False

        def w_rec(object_type, rel, obj_name):
            if suppress((object_type, rel, obj_name)):
                return False
            return o_rec(object_type, rel, obj_name)

        def w_recs(object_type, rel, obj_name, subject):
            if suppress((object_type, rel, obj_name)):
                return False
            return o_recs(object_type, rel, obj_name, subject)

        def w_check():
            # The tier is the INSTRUMENT. Disarm before it runs, or it suppresses its
            # own re-reconcile of the skipped key and every arm comes back green.
            self._armed = False
            self.cache_scope_open = self.graph.widx.idx._node_cache is not None
            return o_check()

        self.proc.reconcile = w_rec
        self.proc.reconcile_subject = w_recs
        self.proc._check_cascade_fixpoint = w_check
        if union_from_reconciled:
            self.proc._tier_schedule = lambda keys: None

    def run(self):
        """Drive the target write's cascade. Returns the InvariantViolation or None.

        The cascade is driven directly rather than through ``GraphBackend.apply`` so the
        tier is the only detector in play: ``apply`` commits, and a commit at this level
        also runs the FULL checker, whose unrelated I6 catch on this fixture (TK74 §9.6,
        ~2.4% of skip arms) would otherwise be indistinguishable from a tier raise."""
        self._armed = True
        wm = outbox_watermark(self.graph.session, 'g')
        self.graph._derived(*TARGET)
        try:
            self.proc.run_cascade(wm)
            return None
        except InvariantViolation as exc:
            return exc
        finally:
            self._armed = False

    @property
    def tier(self):
        return self.proc._tier

    def close(self):
        self.graph.session.rollback()
        self.graph.close()


@pytest.fixture
def arm():
    made = []

    def _make(level, skip_key=None, union_from_reconciled=False):
        a = Arm(level, skip_key, union_from_reconciled)
        made.append(a)
        return a

    yield _make
    for a in made:
        a.close()


# --------------------------------------------------------------------------- #
# (a) the tier is OPT-IN, and it is real when opted into
# --------------------------------------------------------------------------- #

def test_full_does_not_imply_the_tier(arm):
    """``'full'`` is what every existing caller gets (``make_wildcard_index`` defaults to
    ``paranoia=True``). It must not acquire a doubled cascade: the tier sits ABOVE it.

    The arm skips a reconcile, so this also shows what the tier is FOR -- at ``'full'``
    the same corruption passes in silence."""
    a = arm(PARANOIA_FULL, skip_key=('cond', 'requirement_not_met', 'c1'))
    assert a.run() is None, 'full raised on a skip -- then the tier detects nothing new'
    assert a.skipped == 1, f'fault injection fired {a.skipped}x, expected 1'
    assert a.tier is None, (
        "the fixpoint tier ran at level 'full' -- it is no longer opt-in, and every "
        'caller passing paranoia=True just started paying a doubled cascade')


def test_tier_runs_and_is_a_fixpoint_on_clean_traffic(arm):
    """No skip: the tier RAN, looked at the whole cascade, and found nothing.

    Asserting it RAN and that the union is the full multi-stratum cascade is what keeps
    every raise-arm below from being green for an unrelated reason -- a tier that
    silently examined zero keys would pass those arms' 'no raise' controls too."""
    a = arm(PARANOIA_FIXPOINT)
    assert a.run() is None
    assert a.skipped == 0
    tier = a.tier
    assert tier is not None, 'the tier did not run at level fixpoint'
    assert list(tier.keys) == CASCADE_KEYS, (
        f'tier examined {list(tier.keys)}, expected the five-stratum cascade '
        f'{CASCADE_KEYS} -- scheduling moved, so the arms below may be weaker than '
        f'they read')
    assert tier.changed == (), (
        f'FALSE POSITIVE: the tier called clean traffic stale at {list(tier.changed)}')
    assert list(tier.keys) == sorted(set(a.dispatched)), (
        'on clean traffic the scheduled union and the dispatched set must coincide; '
        'that they are identical here is exactly why the sabotage below cannot be '
        'replaced by a benchmark')


@pytest.mark.parametrize('skip_key', NON_FINAL_KEYS)
def test_tier_detects_a_skipped_reconcile(arm, skip_key):
    """THE DETECTION CLAIM: a suppressed reconcile at any key with dependents raises, and
    the message names the key that was skipped."""
    a = arm(PARANOIA_FIXPOINT, skip_key=skip_key)
    exc = a.run()
    assert a.skipped == 1, (
        f'fault injection fired {a.skipped}x, expected 1 -- INSTRUMENT BROKEN, this '
        f'arm asserted nothing')
    assert exc is not None, f'the tier did not see the skipped reconcile of {skip_key}'
    tier = a.tier
    assert tier is not None and list(tier.changed) == [skip_key], (
        f'tier reported changed='
        f'{None if tier is None else list(tier.changed)}, expected exactly [{skip_key}]')
    assert skip_key in tier.keys, (
        'the skipped key was not in the scheduled union -- then this arm is testing '
        'something other than the design claim')
    assert 'I9' in str(exc) and str(skip_key) in str(exc), (
        f'raised, but not from the tier assert: {exc}')


def test_the_suppressed_reconcile_makes_the_store_oracle_wrong():
    """CONTROL: the arms above detect a REAL defect, not an artifact of the injection.

    With the tier OFF the fault-injected store commits happily and then disagrees with
    the independent oracle. Without this, a raise would only show the tier reacting to
    its own monkeypatch."""
    skip_key = ('cond', 'requirement_not_met', 'c1')
    graph = GraphBackend(SCHEMA, frozenset())
    try:
        install_paranoia(graph.session, 'g', graph.ruleset.schema_info,
                         level=PARANOIA_FULL)          # tier OFF
        for raw, op in SETUP:
            assert graph.apply(raw, op)
        proc, state = graph.proc, {'skipped': 0, 'armed': False}
        o_rec, o_recs = proc.reconcile, proc.reconcile_subject

        def hit(key):
            if state['armed'] and key == skip_key:
                state['skipped'] += 1
                return True
            return False

        proc.reconcile = lambda ot, r, on: False if hit((ot, r, on)) else o_rec(ot, r, on)
        proc.reconcile_subject = (
            lambda ot, r, on, s: False if hit((ot, r, on)) else o_recs(ot, r, on, s))
        state['armed'] = True
        wm = outbox_watermark(graph.session, 'g')
        graph._derived(*TARGET)
        proc.run_cascade(wm)
        graph.session.commit()
        state['armed'] = False
        assert state['skipped'] == 1, 'the injection never fired -- nothing was tested'

        oracle = Oracle(SCHEMA, [OracleTuple(*t) for t, _ in SETUP]
                        + [OracleTuple(*TARGET[0])])
        subjects = [('...', 'user', 'u1'), ('...', 'doc', 'd1'), ('...', 'doc', '*'),
                    ('...', 'attr', 'a1'), ('...', 'cond', 'c1'), ('...', 'role', 'r1'),
                    ('...', 'user', 'ghost')]
        targets = [('does_not_label', 'attr', 'a1'), ('labels', 'attr', 'a1'),
                   ('_all_docs', 'attr', 'a1'), ('requirement_not_met', 'cond', 'c1'),
                   ('requirement_met', 'cond', 'c1'), ('access', 'role', 'r1'),
                   ('access', 'user', 'u1')]
        grid = [(sp, st, sn, r, ot, on)
                for (sp, st, sn) in subjects for (r, ot, on) in targets]
        assert len(grid) == 49
        wrong = [q for q in grid if graph.check(q) != oracle.check(*q)]
        assert len(wrong) == 4, (
            f'expected the documented 4 divergences, measured {len(wrong)}: {wrong}')
        assert ('...', 'doc', 'd1', 'access', 'user', 'u1') in wrong, (
            'the divergence did not reach the top stratum -- the arm is weaker than '
            'this module claims')
    finally:
        graph.session.rollback()
        graph.close()


def test_the_tier_runs_outside_the_cache_scopes(arm):
    """``run_cascade`` runs the tier AFTER closing ``_node_cache_scope`` and
    ``_stored_cache_scope``, and that placement is deliberate
    (``docs/tk82-cascade-fixpoint-tier-2026-09-19.md`` §2): a memoized node resolution
    or stored-tuple enumeration must not be able to mask a divergence the check exists
    to see, and it is the placement TK74 §10.3 actually measured.

    Pinned mechanically because the mutation sweep found moving the call inside the
    ``with`` block completely INERT (2026-09-19, ``M6-inside-cache-scopes``): no
    behavioural assertion in this module can see it, so without this line the decision
    is a doc warning and the next refactor may quietly reverse it.

    ⚠ It pins that this method opens no scope the tier runs under -- NOT that no scope
    is ever installed. Under ``connectedstore.advance_index`` an OUTER node-cache scope
    spans the whole apply loop, and ``run_cascade`` cannot close a caller's scope."""
    a = arm(PARANOIA_FIXPOINT)
    assert a.run() is None
    assert a.tier is not None, 'the tier never ran -- the assertion below is vacuous'
    assert a.cache_scope_open is False, (
        'the fixpoint tier ran with the cascade node cache still installed -- it has '
        'been moved inside the cache scopes run_cascade opens')


def test_the_union_includes_the_terminal_leftover_keys():
    """The union is per-round scheduled keys PLUS the terminal ``leftover`` (TK74 §9.9),
    and the second half is not decoration: on TK73's GC witness the leftover key is
    ``('folder','owner','x')`` while that cascade's rounds scheduled only ``owner@y``,
    so dropping it shrinks the union from 2 keys to 1 (measured 2026-09-19).

    HONEST BOUND, so nobody reads this as more than it is: on that path the settle pass
    has ALREADY proved the leftover key a fixpoint before the tier runs, so the leftover
    half cannot currently produce a raise. It is pinned because it makes the union a
    complete record of what the cascade scheduled -- the tier's completeness then does
    not rest on the settle pass, which is the mechanism TK74 found structurally blind.
    Without this arm the leftover call site is INERT under mutation
    (``.scratch/tk82/sweep.py``, ``M2-no-leftover-schedule``): the fixture in this
    module never drives a non-empty leftover at all."""
    graph = GraphBackend(GC_SCHEMA, frozenset())
    try:
        install_paranoia(graph.session, 'g', graph.ruleset.schema_info,
                         level=PARANOIA_FIXPOINT)
        scheduled = []
        original = graph.proc._tier_schedule

        def spy(keys):
            scheduled.append(sorted(keys))
            return original(keys)

        graph.proc._tier_schedule = spy
        for raw, op in GC_WITNESS:
            scheduled.clear()
            assert graph.apply(raw, op), f'{op} {raw} was REJECTED'
        # the final remove: rounds schedule owner@y, the settle pass's leftover is owner@x
        assert graph.proc._settle is not None, (
            'no settle pass on the GC witness -- this cascade has no leftover, so the '
            'arm cannot distinguish the two halves of the union')
        rounds, leftover = scheduled[:-1], scheduled[-1]
        in_rounds = {k for batch in rounds for k in batch}
        assert leftover == [GC_LEFTOVER_KEY], f'leftover was {leftover}'
        assert GC_LEFTOVER_KEY not in in_rounds, (
            'the leftover key was already scheduled in a round -- then this arm proves '
            'nothing about the leftover half')
        assert GC_LEFTOVER_KEY in graph.proc._tier.keys, (
            'the leftover key never reached the tier union')
        assert len(graph.proc._tier.keys) == len(in_rounds) + 1
    finally:
        graph.session.rollback()
        graph.close()


# --------------------------------------------------------------------------- #
# (b) THE SABOTAGE -- permanent, because no clean-traffic signal can replace it
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('skip_key', NON_FINAL_KEYS)
def test_sabotage_reconciled_union_ships_dead(arm, skip_key):
    """The narrowest plausible weakening: take the union from the RECONCILED set instead
    of the SCHEDULED set. It must FAIL BY PASSING on the very arms above -- and it does.

    This is the whole justification for ``_tier_schedule`` being called from the
    scheduling side. On clean traffic the two sources are byte-identical (TK74 §10.3:
    ``union_minus_dispatched = 0`` over 3,744 cascades), so if this test is ever deleted
    the choice becomes unfalsifiable and a refactor can swap the source with every other
    signal staying green."""
    a = arm(PARANOIA_FIXPOINT, skip_key=skip_key, union_from_reconciled=True)
    exc = a.run()
    assert a.skipped == 1, f'fault injection fired {a.skipped}x, expected 1'
    assert exc is None, (
        f'the RECONCILED-union tier caught the skip at {skip_key} -- if that is real, '
        f'the scheduled-vs-reconciled distinction this design rests on is gone: {exc}')
    tier = a.tier
    assert tier is not None, 'the sabotaged tier never ran -- it proved nothing'
    assert skip_key not in tier.keys, (
        'the skipped key reached the reconciled union; the sabotage did not sabotage')
    assert tier.changed == ()


def test_the_sabotaged_union_is_not_trivially_empty(arm):
    """Control on the sabotage itself: a reconciled-union tier that examined NOTHING
    would pass the arms above for the boring reason. It examines real keys and is blind
    anyway, which is the more convincing failure."""
    a = arm(PARANOIA_FIXPOINT, skip_key=('cond', 'requirement_not_met', 'c1'),
            union_from_reconciled=True)
    assert a.run() is None
    assert a.tier.keys == (('attr', 'does_not_label', 'a1'),), (
        f'sabotaged union was {list(a.tier.keys)} -- expected the one key the cascade '
        f'did dispatch before the skip')


# --------------------------------------------------------------------------- #
# (c) the ladder placement, both halves
# --------------------------------------------------------------------------- #

_PLAIN = ('model\n'
          '  schema 1.1\n'
          'type user\n'
          'type doc\n'
          '  relations\n'
          '    define viewer: [user]\n')


def test_fixpoint_tier_is_at_least_full():
    """The trap the placement created: ``ParanoiaGuard``'s listeners branched on
    ``level == PARANOIA_FULL``, so a rank appended ABOVE ``full`` fell into the residue
    branch -- the strongest tier would have been WEAKER than ``full``.

    Pinned behaviourally, not by asserting the constant: an I13 refcount corruption is
    O(store) to see, so it is exactly what the residue tier misses and the full tier
    catches (``tests/test_paranoia_wiring.py::test_tier_boundary_is_what_it_says_it_is``
    pins that boundary). At ``'fixpoint'`` it must still raise."""
    assert paranoia_at_least(PARANOIA_FIXPOINT, PARANOIA_FULL)
    schema_info = parse_openfga_schema(_PLAIN).schema_info
    session, widx = make_wildcard_index(schema_info, store_id='g',
                                        paranoia=PARANOIA_FIXPOINT)
    try:
        widx.add_tuple('...', 'user', 'u1', 'viewer', 'doc', 'd1')
        session.commit()
        node = session.exec(select(Node).where(Node.store_id == 'g')).first()
        assert node is not None, 'no node to corrupt -- the check below is vacuous'
        node.reference_count += 7
        session.add(node)
        with pytest.raises(InvariantViolation, match='I13'):
            widx.add_tuple('...', 'user', 'u2', 'viewer', 'doc', 'd1')
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_the_env_var_arms_the_tier_end_to_end(monkeypatch):
    """``ZANZIBAR_PARANOIA=fixpoint`` must reach the CASCADE, not merely the guard.

    The tier is read out of the guard registry on the processor's own session
    (``src/zanzibar/graphindex/invariants.py::paranoia_level``), and nothing else in this module proves
    that registry is the same one ``ConnectedStore`` writes to -- every other arm installs
    the guard by hand. §9.7 of TK74 is the reason this is a test and not an assumption: a
    tier knob that silently resolves to the wrong level is a failure mode this repo has
    already shipped once.
    """
    monkeypatch.setenv(PARANOIA_ENV_VAR, PARANOIA_FIXPOINT)
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    try:
        cs = ConnectedStore(session, 'cs', schema=SCHEMA)
        assert cs.paranoia == PARANOIA_FIXPOINT
        assert cs.paranoia_guard is not None
        assert cs.paranoia_guard.level == PARANOIA_FIXPOINT
        for raw, op in SETUP:
            assert op == 'add'
            cs.add_tuple(*raw)
        cs.add_tuple(*TARGET[0])
        assert cs.proc is not None, 'no processor -- the assertion below is vacuous'
        tier = cs.proc._tier
        assert tier is not None, (
            'the env var set the guard but the cascade tier never ran -- the processor '
            'is reading a different registry than ConnectedStore writes')
        assert tier.changed == (), f'false positive on clean traffic: {list(tier.changed)}'
        assert tier.keys, 'the tier ran but examined nothing'
    finally:
        session.rollback()
        session.close()
