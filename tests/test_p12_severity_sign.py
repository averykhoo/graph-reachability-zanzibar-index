"""P12 -- the 2026-08-09 sibling's SEVERITY SIGN, observed rather than predicted.

## What this pins (one sentence)

With the I14 crossing-middle fix simulated away, the OWC x star-parent x TTU defect of
``docs/spec-deviations.md`` 2026-08-09 is fail-CLOSED under its positive consumer and
fail-OPEN -- an authorization over-grant -- under every negated consumer the graph index
compiles; with the fix live, all of it agrees with the oracle.

## Why it exists

The 2026-08-09 entry filed that defect as *"a false negative (under-grant): it fails closed,
so it is not a security fail-open"*, drawn from the positive consumer alone.
``docs/sabotage-procedure.md`` ("Probe BOTH signs") says a dropped path is a false NEGATIVE
under a positive consumer and a false POSITIVE under a negated one, and the 2026-08-10 entry
fenced the sibling off as a PREDICTION, not an observation. ``P12`` measured it:
``docs/p12-severity-sign-revert-probe-2026-09-27.md`` carries the literal-revert run (the
pre-fix tree ``33242de^`` = the docs' ``c042056^``, exported with ``git archive``, no
product file touched) and the grid counts. This module keeps the result permanently
WITHOUT shipping bad code: the pre-fix behaviour is simulated in the test by no-op'ing
``src/zanzibar/graphindex/wildcard.py::WildcardIndex._ensure_entity_middles`` -- the same narrowest
weakening ``tests/test_i14_crossing_middles.py`` uses -- on a store with paranoia OFF
(paranoia's I14 check would otherwise abort the first write, which is the other half of
today's severity and is pinned below too).

## The consumer the 2026-08-10 entry proposed does not compile

``define access: [user] but not viewer from parent`` directly over ``owc_star_ttu.fga``
is refused by the graph compiler (``src/zanzibar/schema/compiler.py::_reject_object_wildcard_scope``,
blind-audit D4: the object-wildcard shape ``(folder, viewer)`` would be the TTU target of
a derived relation). ``test_the_proposed_negated_consumer_is_refused`` pins that, so the
next reader does not re-derive it. The negated consumers that DO compile are the three in
``_CONSUMERS``.

## Evidence (literal, 2026-09-27; the plan doc § 3 is the full record)

The literal revert, every subset of an 8-tuple pool on the pre-fix tree ``33242de^``
(``.scratch/p12/probe.py``, throwaway; its output is transcribed in the plan doc)::

    tree=pre_i14 case=B   states=256 rejected_adds=0 queries=3072 divergences=36
      access     fail-OPEN   12
      viewer     fail-CLOSED 24

D and E split the same way (``access`` OPEN 6 / 6; ``viewer`` CLOSED 24 / 24; E's positive
``blocked`` CLOSED 12). The simulation used below, on ``d4ea804``, reproduced ``case=B``
exactly -- ``divergences=36``, OPEN 12, CLOSED 24 -- and the unsabotaged tree gave
``divergences=0``. That equality is what makes a simulated pin honest here.

``test_which_paranoia_level_catches_the_simulated_revert`` records a finding of its own:
``residue`` -- the production level ``CLAUDE.md`` recommends -- does NOT catch this
regression (I14 lives in ``check_invariants``, ``full`` and up), measured::

    B-computed residue  positive: oracle=True graph=False  negated: oracle=False graph=True
    B-computed full     RAISED InvariantViolation: store='g' [pre-commit] I14: entity
                        folder:f1 exists but its crossing middle folder:f1#viewer for
                        crossable shape ('folder', 'viewer') is missing

## Sabotage + mutation sweep (docs/sabotage-procedure.md -- literal, 2026-09-27)

``.scratch/p12/mut.py``: anchor asserted to occur once, file restored in ``finally`` and
hash-checked, no outer timeout. Each mutant's red set is exactly the tests that guard it::

    M0 [control: no change]                                        14 passed
    M1 [product: _ensure_entity_middles creates no middle]         3 failed, 11 passed
         test_live_graph_agrees_with_the_oracle x3
    M2 [product: no w_all -> concrete out-bridge]                  6 failed, 8 passed
         test_live_graph_agrees_with_the_oracle x3, ..._heals_when_the_middle_... x3
    M3 [product: the I14 checker checks nothing]                   2 failed, 12 passed
         test_which_paranoia_level_...[full-abort], [fixpoint-abort]
    M4 [instrument: simulation patches _sync_entity_middles]       7 failed, 7 passed
         test_simulated_revert_is_fail_open_... x3, test_which_paranoia_level_... x4
    M5 [instrument: sign classifier inverted]                      5 failed, 9 passed
         test_simulated_revert_is_fail_open_... x3, ...[off-fail-OPEN], [residue-fail-OPEN]
    M6 [instrument: heal control loses its healing tuple]          3 failed, 11 passed
         test_simulated_revert_heals_when_the_middle_is_interned_by_data x3
    ALL RESTORED (hash-checked)

Honest limits: M4 leaves the heal controls green, by design -- they pass with or without
the simulation, and M6 is what shows they have teeth. No mutant flips the SIGN while
keeping the live graph right; the sign pin guards the recorded measurement against a
product change that alters how negated consumers read ``doc#viewer``, which no single-line
mutant here produces.
"""

from pathlib import Path

import pytest

from zanzibar.graphindex.invariants import InvariantViolation
from zanzibar.graphindex.wildcard import WildcardIndex
from zanzibar.setengine import ALL_SETOPS
from tests.oracle import Oracle, OracleTuple
from tests.test_matrix import GraphBackend, SetBackend
from zanzibar.schema import UnsupportedByGraphIndex, parse_openfga_schema


def _owc_star_ttu() -> str:
    return (Path(__file__).parent / 'fga_schemas' / 'owc_star_ttu.fga').read_text().rstrip() + '\n'


_BOTH = frozenset({('folder', 'viewer'), ('doc', 'viewer')})
_FOLDER_ONLY = frozenset({('folder', 'viewer')})

_REPORT = """
type report
  relations
    define parent: [doc]
    define blocked: [user, doc#viewer]
"""

# The 2026-08-09 minimal three tuples (tests/test_owc_star_parent_cross.py).
_WITNESS = ('...', 'user', 'u9', 'editor', 'folder', 'f1')     # folder:f1 exists, not (folder,viewer)
_OWC_GRANT = ('...', 'user', 'u1', 'viewer', 'folder', '*')    # -> w_all(folder, viewer)
_STAR_PARENT = ('...', 'folder', '*', 'parent', 'doc', 'd1')   # -> w_any(folder, '...')
_HEAL = ('...', 'user', 'u2', 'viewer', 'folder', 'f1')        # interns folder:f1#viewer

_POSITIVE_Q = ('...', 'user', 'u1', 'viewer', 'doc', 'd1')

# name -> (schema, object-wildcard shapes, extra tuples, negated query)
_CONSUMERS = {
    'B-computed': (
        _owc_star_ttu() + '    define access: [user] but not viewer\n', _FOLDER_ONLY,
        [('...', 'user', 'u1', 'access', 'doc', 'd1')],
        ('...', 'user', 'u1', 'access', 'doc', 'd1')),
    'D-ttu': (
        _owc_star_ttu() + _REPORT + '    define access: [user] but not viewer from parent\n',
        _FOLDER_ONLY,
        [('...', 'doc', 'd1', 'parent', 'report', 'r1'),
         ('...', 'user', 'u1', 'access', 'report', 'r1')],
        ('...', 'user', 'u1', 'access', 'report', 'r1')),
    'E-userset': (
        _owc_star_ttu() + _REPORT + '    define access: [user] but not blocked\n', _BOTH,
        [('viewer', 'doc', 'd1', 'blocked', 'report', 'r1'),
         ('...', 'user', 'u1', 'access', 'report', 'r1')],
        ('...', 'user', 'u1', 'access', 'report', 'r1')),
}


def _simulate_pre_fix(monkeypatch):
    """The pre-``33242de`` graph: no crossing middles. ``raising=True`` (the default) makes a
    renamed target a loud AttributeError instead of a silent no-sabotage."""
    monkeypatch.setattr(WildcardIndex, '_ensure_entity_middles',
                        lambda self, entity_type, name: None)


def _answers(schema, owc, tuples, queries, *, paranoia):
    """{query: (oracle, graph, [set engines])} after adding ``tuples`` in order. Admission
    is asserted in lockstep, so no answer can be explained by a quietly refused write."""
    graph = GraphBackend(schema, owc, paranoia=paranoia)
    sets = [SetBackend(schema, owc, ops) for ops in ALL_SETOPS]
    try:
        for raw in tuples:
            assert graph.apply(raw, 'add'), f'graph refused {raw}'
            for s in sets:
                assert s.apply(raw, 'add'), f'{s.name} refused {raw}'
        oracle = Oracle(schema, [OracleTuple(*r) for r in tuples])
        return {q: (oracle.check(*q), graph.check(q), [s.check(q) for s in sets])
                for q in queries}
    finally:
        graph.close()
        for s in sets:
            s.close()


def _sign(oracle, graph):
    if oracle == graph:
        return 'agree'
    return 'fail-OPEN' if graph else 'fail-CLOSED'


@pytest.mark.parametrize('consumer', sorted(_CONSUMERS))
def test_simulated_revert_is_fail_open_under_a_negated_consumer(consumer, monkeypatch):
    """★ The sign, observed: positive consumer fail-CLOSED, negated consumer fail-OPEN."""
    schema, owc, extra, neg_q = _CONSUMERS[consumer]
    _simulate_pre_fix(monkeypatch)
    got = _answers(schema, owc, [_WITNESS, _OWC_GRANT, _STAR_PARENT] + extra,
                   [_POSITIVE_Q, neg_q], paranoia='off')
    (po, pg, ps), (no, ng, ns) = got[_POSITIVE_Q], got[neg_q]
    # the spec side first: if these trip, the ORACLE moved -- re-adjudicate, do not edit
    assert (po, no) == (True, False), f'oracle moved: positive={po} negated={no}'
    assert ps == [True] * len(ps) and ns == [False] * len(ns), \
        f'set engines disagree with the oracle: positive={ps} negated={ns}'
    assert (_sign(po, pg), _sign(no, ng)) == ('fail-CLOSED', 'fail-OPEN'), (
        f'{consumer}: the simulated pre-fix graph no longer has the recorded signs '
        f'(positive graph={pg}, negated graph={ng}); re-measure and re-record P12')


@pytest.mark.parametrize('consumer', sorted(_CONSUMERS))
def test_live_graph_agrees_with_the_oracle(consumer):
    """CONTROL: the same states on the shipped code (paranoia full) agree everywhere, so the
    sign pin above is about the removed middles and nothing else."""
    schema, owc, extra, neg_q = _CONSUMERS[consumer]
    got = _answers(schema, owc, [_WITNESS, _OWC_GRANT, _STAR_PARENT] + extra,
                   [_POSITIVE_Q, neg_q], paranoia='full')
    for q, (o, g, s) in got.items():
        assert g == o and s == [o] * len(s), f'{consumer} {q}: oracle={o} graph={g} sets={s}'


@pytest.mark.parametrize('consumer', sorted(_CONSUMERS))
def test_simulated_revert_heals_when_the_middle_is_interned_by_data(consumer, monkeypatch):
    """CONTROL: under the same simulation, a tuple that interns ``folder:f1#viewer`` by
    itself (the 2026-08-09 positive control's witness) restores agreement -- the divergence
    is the missing middle, not the harness, the schema or the consumer."""
    schema, owc, extra, neg_q = _CONSUMERS[consumer]
    _simulate_pre_fix(monkeypatch)
    tuples = [_WITNESS, _HEAL, _OWC_GRANT, _STAR_PARENT] + extra
    got = _answers(schema, owc, tuples, [_POSITIVE_Q, neg_q], paranoia='off')
    for q, (o, g, _s) in got.items():
        assert g == o, f'{consumer} {q}: oracle={o} graph={g}'


@pytest.mark.parametrize('level,outcome', [
    ('off', 'fail-OPEN'),
    ('residue', 'fail-OPEN'),     # ★ the level CLAUDE.md recommends for production
    ('full', 'abort'),
    ('fixpoint', 'abort'),
])
def test_which_paranoia_level_catches_the_simulated_revert(level, outcome, monkeypatch):
    """Today's severity per paranoia level, measured. I14 runs only in ``check_invariants``
    (``full`` and up), so at ``full``/``fixpoint`` the regression is a refused write, but at
    ``residue`` -- ``ZANZIBAR_PARANOIA=residue``, the tier ``CLAUDE.md`` recommends in
    production -- and at the library default ``off`` it is the silent fail-OPEN above.
    A detector at the test default, not a mitigation in production."""
    schema, owc, extra, neg_q = _CONSUMERS['B-computed']
    _simulate_pre_fix(monkeypatch)
    tuples = [_WITNESS, _OWC_GRANT, _STAR_PARENT] + extra
    if outcome == 'abort':
        graph = GraphBackend(schema, owc, paranoia=level)
        try:
            with pytest.raises(InvariantViolation, match='I14: entity folder:f1 exists'):
                for raw in tuples:
                    graph.apply(raw, 'add')
        finally:
            graph.session.rollback()
            graph.close()
        return
    got = _answers(schema, owc, tuples, [neg_q], paranoia=level)
    oracle, graph_answer, _sets = got[neg_q]
    assert _sign(oracle, graph_answer) == outcome, \
        f'paranoia={level}: oracle={oracle} graph={graph_answer}'


def test_the_proposed_negated_consumer_is_refused():
    """The consumer the 2026-08-10 entry proposed for this probe does not compile for the
    graph index (blind-audit D4), with either object-wildcard declaration."""
    schema = _owc_star_ttu() + '    define access: [user] but not viewer from parent\n'
    for owc in (_BOTH, _FOLDER_ONLY):
        with pytest.raises(UnsupportedByGraphIndex, match=r'TTU target of derived relation'):
            parse_openfga_schema(schema, object_wildcard_shapes=owc)
