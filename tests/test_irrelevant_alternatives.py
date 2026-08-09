"""
Irrelevance of irrelevant alternatives (IIA) -- a metamorphic property over WRITES.

**This module is currently RED, deliberately.** It is written BEFORE the fix it guards
(the 2026-08-09 graph under-report, ``docs/spec-deviations.md`` 2026-08-09), so the red
is attributable to that pre-existing divergence and not to anything this file changed.
Do NOT xfail it, do NOT weaken the property -- fix the graph and watch it go green.

## The property

Let S be a store (a list of accepted raw tuples), t an additional tuple, q a query.
Call t an *irrelevant alternative* for q when

    oracle.check(S, q) == oracle.check(S + t, q)

i.e. adding t does not move the SEMANTICS of q (the oracle is the spec; independence
contract in ``tests/oracle.py``). Then every backend's answer to q must also be unmoved:

    graph.check(S, q)     == graph.check(S + t, q)
    setengine.check(S, q) == setengine.check(S + t, q)      (for BOTH SetOps)

A failure means a backend's answer to q moved for a reason the semantics does not
license: one principal's access changed because of an unrelated grant to someone else.

## Why this property (and why it is not redundant with the parity gates)

The matrix / lookup gates compare each backend against the oracle PER STATE. IIA
compares a backend against ITSELF ACROSS STATES, conditioned on the oracle being
stable. That catches the same bugs from a different, operationally meaningful angle --
"user A's access flipped when user B was granted something" is exactly the symptom an
auditor sees -- and it localizes blame to the single write that moved the answer.

The live bug filed 2026-08-09 in ``docs/spec-deviations.md`` is exactly an IIA
violation. On ``tests/fga_schemas/owc_star_ttu.fga`` with ``object_wildcard_shapes``
``{('folder','viewer'), ('doc','viewer')}``::

    S = [(user:u1, editor, folder:f1),     # witness: folder:f1 exists
         (user:u1, viewer, folder:*),      # OBJECT-wildcard grant
         (folder:*, parent, doc:d1)]       # SUBJECT-wildcard (star) tupleset
    q = check(user:u1, viewer, doc:d1)     # oracle True, both sets True, GRAPH False
    t = (user:u9, viewer, folder:f1)       # a grant to a DIFFERENT user

The oracle answers q True both before and after t (t is irrelevant to q), but the
graph flips False -> True: t interns a node of shape ``(folder, viewer)``, which is
the witness ``index_v4/wildcard.py::_ensure_bridges`` was missing (root cause measured
in ``docs/spec-deviations.md`` 2026-08-09; the set engine's analogue is the star-parent
cross, ``setengine/engine.py:1476-1480``). One user's access depends on an unrelated
grant to another user. ``tests/test_owc_star_parent_cross.py`` pins the per-state
parity divergence; this module pins the cross-state flip.

## Non-vacuity (house rule: an assurance step that fails by PASSING)

Every probe COUNTS the (q, t) pairs where t was actually irrelevant-and-checked and
asserts the count > 0, so a run that compared nothing fails loudly instead of
reporting green. Observed counts (2026-08-09, this tree):

* deterministic red test: checked = 570 irrelevant (q, t) pairs (the full 15x38
  subjects-x-objects grid of the owc_star_ttu corpus; ``u9`` is not a grid subject,
  so t moved no grid query and every pair was checked).
* green control: checked = 570 (same grid; the extra grants only ``u9``, so again
  no grid query moved).
* hypothesis leg, ci profile: checked ranged 317-734 per example across the 12
  examples of a green run (wildcards 317-320, boolean 511, owc_star_ttu 568-569,
  demorgans_reverse 722-734; measured via a temporary print, then removed).

## Sabotage evidence (docs/sabotage-procedure.md -- literal observed output)

* Positive control / the subject: the current tree IS the defect. The deterministic
  test fails with::

      AssertionError: IIA violated on corpus 'owc_star_ttu': 1 backend answer(s)
      moved when the irrelevant tuple ('...', 'user', 'u9', 'viewer', 'folder', 'f1')
      was added (oracle unmoved on each):
        graph: ('...', 'user', 'u1', 'viewer', 'doc', 'd1') flipped False -> True

* Instrument sabotage 1 (skip-all): inverting the irrelevance filter so every query
  is treated as relevant (``!=`` -> ``==`` in ``_iia_probe``) made the comparison
  vacuous; the non-vacuity floor caught it in BOTH the deterministic test and the
  control -- ``AssertionError: vacuous IIA probe: no (q, t) pair was
  irrelevant-and-checked`` / ``assert 0 > 0``, ``2 failed in 1.58s``. Restored,
  red/green as before.
* Instrument sabotage 2 (self-comparison): comparing each backend's AFTER answer to
  itself (``before[name][q] != after`` -> ``after != after``) silenced the property
  entirely: ``2 passed in 2.65s`` -- the deterministic RED test went green, the
  named house failure mode. That observation is exactly why the deterministic test
  is the instrument's positive control and must stay in this file next to the
  property. Restored, red again.

## What the hypothesis leg can and cannot do (honest statement)

Observed on this tree (2026-08-09): the deterministic test finds the violation; the
ci hypothesis leg does NOT -- it ran GREEN (``1 passed in 14.91s``). The ci profile
does not draw this shape: 12 examples never produced the base constellation (OWC
grant + star parent + non-viewer witness) together with a shape-interning extra. The
deterministic pin is what catches the filed bug, and the hypothesis leg is coverage
against OTHER IIA violations, not this one. Do not read its green as evidence it
would have caught the filed bug -- that is the "green by seed luck" failure mode
already filed for the lookup machine in ``docs/spec-deviations.md`` 2026-08-09. A
``HYPOTHESIS_PROFILE=deep`` (max_examples=120) hunt was started but had not finished
when this file was finalized; that experiment is recorded as UNRUN and no claim is
made about its outcome.
"""

import os

from hypothesis import HealthCheck, Phase, assume, given, settings, strategies as st

from tests.oracle import Oracle, OracleTuple
from tests.test_lookup_hypothesis import _CORPORA, _corpus
from tests.test_lookup_oracle import _Gate

# Same profiles as tests/test_hypothesis.py / tests/test_lookup_hypothesis.py
# (re-registration is idempotent -- last writer wins with identical config -- so this
# module is order-independent).
settings.register_profile('ci', max_examples=12, stateful_step_count=8,
                          deadline=None, suppress_health_check=[HealthCheck.too_slow],
                          phases=(Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink))
settings.register_profile('deep', max_examples=120, stateful_step_count=25,
                          deadline=None, suppress_health_check=[HealthCheck.too_slow])
settings.load_profile(os.environ.get('HYPOTHESIS_PROFILE', 'ci'))


# ---------------------------------------------------------------------------
# The probe (shared by the deterministic red test, the green control and the
# hypothesis leg -- one instrument, controlled in both directions, see module
# docstring "Sabotage evidence")
# ---------------------------------------------------------------------------

def _backend_checks(gate):
    """(name, check_fn) for every backend: the graph index + both set engines."""
    return ([('graph', gate.graph.widx.check)]
            + [(side.name, side.se.check) for side in gate.sets])


def _grid(gate):
    """The full schema-derived query grid: ``_Gate``'s subject candidates x object
    candidates (the same grid the lookup-surface gates assert over)."""
    return [subj + obj for subj in gate.subjects for obj in gate.objects]


def _oracle_answers(gate, grid):
    oracle = Oracle(gate.schema, [OracleTuple(*r) for r in gate.present])
    return {q: oracle.check(*q) for q in grid}


def _iia_probe(gate, extra):
    """Add ``extra`` to the gate's store and check IIA over the whole grid.

    Returns ``(accepted, violations, checked)``:

    * ``accepted`` -- whether admission accepted ``extra`` (a rejection is a correct
      refusal, not a violation; ``_Gate.apply`` converts admission ``ValueError``s to
      ``False`` in lockstep across backends, ``tests/parity.py``).
    * ``violations`` -- ``(backend, q, before, after)`` for every grid query q where
      the oracle's answer was UNMOVED by ``extra`` but the backend's answer moved.
    * ``checked`` -- the count of (q, extra) pairs that were irrelevant-and-checked;
      the callers assert it is > 0 (non-vacuity, house rule).
    """
    grid = _grid(gate)
    oracle_before = _oracle_answers(gate, grid)
    before = {name: {q: fn(*q) for q in grid} for name, fn in _backend_checks(gate)}
    if not gate.apply('add', extra):
        return False, [], 0
    oracle_after = _oracle_answers(gate, grid)
    violations, checked = [], 0
    for q in grid:
        if oracle_before[q] != oracle_after[q]:
            continue        # extra is RELEVANT for q: the property claims nothing
        checked += 1
        for name, fn in _backend_checks(gate):
            after = fn(*q)
            if before[name][q] != after:
                violations.append((name, q, before[name][q], after))
    return True, violations, checked


def _render(corpus, base, extra, violations):
    lines = ''.join(f'\n  {name}: {q} flipped {b} -> {a}'
                    for (name, q, b, a) in violations)
    return (f"IIA violated on corpus {corpus!r}: {len(violations)} backend answer(s) "
            f"moved when the irrelevant tuple {extra} was added (oracle unmoved on "
            f"each):{lines}\nbase store:\n"
            + '\n'.join(f'  add {raw}' for raw in base))


# ---------------------------------------------------------------------------
# 1. Deterministic red: the filed 2026-08-09 case, pinned as an IIA violation
# ---------------------------------------------------------------------------

_WITNESS = ('...', 'user', 'u1', 'editor', 'folder', 'f1')
_OWC_GRANT = ('...', 'user', 'u1', 'viewer', 'folder', '*')
_STAR_PARENT = ('...', 'folder', '*', 'parent', 'doc', 'd1')
_BASE = (_WITNESS, _OWC_GRANT, _STAR_PARENT)
_IRRELEVANT_GRANT = ('...', 'user', 'u9', 'viewer', 'folder', 'f1')
_QUERY = ('...', 'user', 'u1', 'viewer', 'doc', 'd1')


def test_iia_deterministic_graph_flips_on_unrelated_grant():
    """CURRENTLY RED -- the 2026-08-09 divergence, framed as the IIA violation it is.

    ``u9``'s viewer grant on ``folder:f1`` does not change what ``u1`` may see (the
    oracle answers ``_QUERY`` True before AND after -- asserted below as the
    irrelevance precondition), yet the graph's answer to ``_QUERY`` flips
    False -> True, because the grant interns the ``(folder, viewer)``-shaped node
    ``_ensure_bridges`` needed (``docs/spec-deviations.md`` 2026-08-09). Observed on
    this tree: checked=570, and the violation list is exactly::

        graph: ('...', 'user', 'u1', 'viewer', 'doc', 'd1') flipped False -> True

    Only the property assertion may be red: the preconditions (oracle True and
    unmoved, both set engines unmoved) must hold before and after any fix, so this
    test goes green when -- and only when -- the graph stops moving.
    """
    schema, owc, pool = _corpus('owc_star_ttu')
    gate = _Gate(schema, owc, pool)
    try:
        for raw in _BASE:
            assert gate.apply('add', raw), f'admission rejected base tuple {raw}'
        oracle_before = Oracle(schema, [OracleTuple(*r) for r in gate.present])
        assert oracle_before.check(*_QUERY) is True, \
            'the oracle is the spec; if this flipped, re-adjudicate 2026-08-09 first'

        accepted, violations, checked = _iia_probe(gate, _IRRELEVANT_GRANT)
        assert accepted, f'admission rejected {_IRRELEVANT_GRANT}'
        # the irrelevance precondition, restated on the headline query:
        oracle_after = Oracle(schema, [OracleTuple(*r) for r in gate.present])
        assert oracle_after.check(*_QUERY) is True, \
            't must be irrelevant for the headline query; if not, the repro rotted'
        assert checked > 0, \
            'vacuous IIA probe: no (q, t) pair was irrelevant-and-checked'
        assert not violations, _render('owc_star_ttu', _BASE, _IRRELEVANT_GRANT,
                                       violations)
    finally:
        gate.close()


# ---------------------------------------------------------------------------
# 2. Green control: same composition, witness already interns (folder, viewer)
# ---------------------------------------------------------------------------

def test_iia_control_no_flip_when_shape_witness_interned():
    """GREEN control for the instrument (sabotage-procedure: control your instrument).

    The same OWC x star-parent x TTU composition, but the witness tuple is itself a
    viewer grant, so a ``(folder, viewer)``-shaped node is interned from the start
    and the graph answers the doc query True BEFORE the extra tuple. The extra
    (``u9`` editor on ``folder:f2``) is irrelevant to EVERY grid query -- ``u9`` is
    not a grid subject -- so the probe must report zero violations over a nonzero
    checked count (observed on this tree: checked=570, the whole grid). Together
    with the red test above this pins the instrument from both sides: it fires on
    the known defect and stays quiet on an honest state. Must keep passing through
    any fix.
    """
    schema, owc, pool = _corpus('owc_star_ttu')
    gate = _Gate(schema, owc, pool)
    try:
        base = (('...', 'user', 'u2', 'viewer', 'folder', 'f1'),   # interns the shape
                _OWC_GRANT, _STAR_PARENT)
        for raw in base:
            assert gate.apply('add', raw), f'admission rejected base tuple {raw}'
        assert gate.graph.widx.check(*_QUERY) is True, \
            'control precondition: with the shape interned the graph already grants'

        accepted, violations, checked = _iia_probe(
            gate, ('...', 'user', 'u9', 'editor', 'folder', 'f2'))
        assert accepted
        assert checked > 0, \
            'vacuous IIA probe: no (q, t) pair was irrelevant-and-checked'
        assert not violations, _render('owc_star_ttu', base,
                                       ('...', 'user', 'u9', 'editor', 'folder', 'f2'),
                                       violations)
    finally:
        gate.close()


# ---------------------------------------------------------------------------
# 3. Hypothesis leg: IIA over drawn (corpus, base store, extra tuple)
# ---------------------------------------------------------------------------

@st.composite
def _iia_cases(draw):
    """(corpus name, base tuples, extra tuple): base is a unique subset of the
    corpus pool, extra a pool tuple not in base (so an accept is the common case
    and a duplicate add can never masquerade as an irrelevant write)."""
    corpus = draw(st.sampled_from(_CORPORA))
    _schema, _owc, pool = _corpus(corpus)
    # cap the base below the pool size so an extra always remains (the
    # demorgans_reverse pool has only 7 tuples)
    base = draw(st.lists(st.sampled_from(pool), min_size=0,
                         max_size=min(8, len(pool) - 1), unique=True))
    extra = draw(st.sampled_from([r for r in pool if r not in base]))
    return corpus, base, extra


@given(case=_iia_cases())
def test_iia_hypothesis(case):
    """IIA over Hypothesis-drawn states of the four fixed-gate corpora.

    Draws a base store and one extra tuple, applies the base through the lockstep
    ``_Gate`` (skipping tuples admission rejects -- a rejection is a correct refusal,
    not a violation; a rejected EXTRA discards the example via ``assume``), then
    asserts IIA over the full subjects-x-objects query grid on the graph index and
    both set engines. Each example additionally asserts its own non-vacuity: at
    least one (q, extra) pair must have been irrelevant-and-checked.

    Honest coverage statement (see module docstring): observed on this tree
    (2026-08-09), the ci profile does NOT draw this shape -- this leg ran GREEN
    (``1 passed in 14.91s``) while the deterministic test above was red. The
    deterministic pin is what catches the filed bug; this leg is coverage against
    OTHER IIA violations, not that one. Per-example non-vacuity counts observed
    under ci: 317-734 (breakdown in the module docstring). A deep-profile hunt was
    started but not finished at finalization time; it is recorded as UNRUN and no
    deep result is claimed.
    """
    corpus, base, extra = case
    schema, owc, pool = _corpus(corpus)
    gate = _Gate(schema, owc, pool)
    try:
        applied = [raw for raw in base if gate.apply('add', raw)]
        accepted, violations, checked = _iia_probe(gate, extra)
        assume(accepted)        # rejected extra: correct refusal, nothing to claim
        assert checked > 0, \
            'vacuous IIA probe: no (q, t) pair was irrelevant-and-checked'
        assert not violations, _render(corpus, applied, extra, violations)
    finally:
        gate.close()
