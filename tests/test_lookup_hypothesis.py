"""
Hypothesis-driven lookup-surface coverage (closes the gap left by the fixed-fixture
gate ``tests/test_lookup_oracle.py``).

``test_lookup_oracle.py`` pins the three read surfaces -- ``lookup`` /
``lookup_reverse`` / ``expand`` -- on BOTH backends against a brute-force oracle
reference, but only over hand-written seeds [0, 1] and dense scripted states. This
module drives the SAME verified reference-lookup assertion battery
(``_Gate.assert_surfaces``, which composes every ``_check_graph_*`` / ``_check_set_*``
checker in ``test_lookup_oracle``) from Hypothesis-generated randomized add/remove op
sequences, so the surfaces are exercised over a far wider state space than the fixed
seeds reach -- including removal/GC/residue-shrink constellations no seed constructs.

Nothing here reinvents or weakens a checker: the machine reuses ``_Gate`` verbatim (it
already runs the graph + both set engines in lockstep and asserts all three surfaces
vs the oracle). The Hypothesis layer only chooses the walk. If a generated walk ever
trips a checker, that is a genuine lookup/expand divergence the properties (the spec)
forbid -- capture the minimal example and REPORT it; do NOT relax the assertions.

Corpora (reused from the fixed gate, so the state space stays inside the runtime
budget): the pure-union wildcard schema, the boolean fixture (exclusion / intersection
/ TTU-over-derived), and the nested-exclusion demorgans_reverse chain. The machine
draws one corpus per example in ``initialize`` and asserts every surface after every
accepted op via an ``@invariant`` (matching the fixed gate's per-op cadence, which is
also end-of-sequence coverage since invariants run after the final step).

Profiles: 'ci' (fast, default) / 'deep' (HYPOTHESIS_PROFILE=deep), matching
tests/test_hypothesis.py.
"""

import os
from pathlib import Path

from hypothesis import HealthCheck, Phase, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from tests.test_lookup_oracle import _Gate
from tests.test_matrix import _boolean_pool, _demorgan_pool
from tests.test_wildcard_property import OBJECT_WC, _candidate_raw_tuples

# Same profiles as tests/test_hypothesis.py (re-registration is idempotent -- last
# writer wins with identical config -- so this module is order-independent).
settings.register_profile('ci', max_examples=12, stateful_step_count=8,
                          deadline=None, suppress_health_check=[HealthCheck.too_slow],
                          phases=(Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink))
settings.register_profile('deep', max_examples=120, stateful_step_count=25,
                          deadline=None, suppress_health_check=[HealthCheck.too_slow])
settings.load_profile(os.environ.get('HYPOTHESIS_PROFILE', 'ci'))


def _load_fga(filename: str) -> str:
    with open(Path(__file__).parent / 'fga_schemas' / filename, 'r') as f:
        return f.read()


def _corpus(name: str):
    """(schema_text, object_wildcard_shapes, pool) for a named fixed-gate corpus."""
    if name == 'wildcards':
        return _load_fga('wildcards.fga'), OBJECT_WC, _candidate_raw_tuples()
    if name == 'boolean':
        return _load_fga('boolean_wildcards.fga'), frozenset(), _boolean_pool()
    if name == 'demorgans_reverse':
        schema = _load_fga('demorgans_reverse.fga')
        return schema, frozenset(), _demorgan_pool(schema)
    raise AssertionError(name)


_CORPORA = ['wildcards', 'boolean', 'demorgans_reverse']


class LookupSurfaceMachine(RuleBasedStateMachine):
    """Randomized add/remove walk over a fixed-gate corpus, asserting the full
    lookup/lookup_reverse/expand-vs-oracle battery (``_Gate.assert_surfaces``) on the
    real graph index + both real set engines after every accepted op.

    The reference-lookup checkers are the SAME verified ones the fixed-fixture gate
    uses -- imported, not reimplemented -- so this only widens the state space; a
    failure here is a genuine surface divergence, never a checker weakness.
    """

    @initialize(corpus=st.sampled_from(_CORPORA))
    def setup(self, corpus):
        schema, object_wc, pool = _corpus(corpus)
        self.pool = pool
        self.gate = _Gate(schema, object_wc, pool)

    @rule(data=st.data())
    def add(self, data):
        cands = [r for r in self.pool if r not in self.gate.present]
        if not cands:
            return
        self.gate.apply('add', data.draw(st.sampled_from(cands)))

    @rule(data=st.data())
    def remove(self, data):
        if not self.gate.present:
            return
        self.gate.apply('remove', data.draw(st.sampled_from(sorted(self.gate.present))))

    @invariant()
    def surfaces_match_oracle(self):
        # Runs after initialize and after every rule (so end-of-sequence too):
        # forward lookup + lookup_reverse (graph) and forward lookup + expand +
        # lookup_reverse (both set engines), each exact/one-sided per the fixed gate.
        if hasattr(self, 'gate'):
            self.gate.assert_surfaces(context='hypothesis walk')

    def teardown(self):
        if hasattr(self, 'gate'):
            self.gate.close()


TestLookupSurfaceMachine = LookupSurfaceMachine.TestCase
