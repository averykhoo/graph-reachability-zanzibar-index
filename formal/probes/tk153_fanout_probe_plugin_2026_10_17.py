"""TK153 fan-out probe plugin (2026-10-17): record every closure fan-out cap comparison.

Regenerates the tests/ figure in the comment above
src/zanzibar/graphindex/core.py::DEFAULT_MAX_CLOSURE_FANOUT. Run (Bash, repo root):

    FANOUT_OUT=/tmp/fanout.jsonl PYTHONPATH=formal/probes python -m pytest -q         -p tk153_fanout_probe_plugin_2026_10_17 tests/

then take the max of the "max" field. Instrument control: on
tests/test_reg17_closure_fanout_cap.py alone it must record the deliberate 440-row control
(it did, 2026-10-17: maxima [0, 4, 24, 440]). Full tests/ run 2026-10-17: 906 tests with a
cap comparison, 41,606 comparisons, max 440 (the control), next 93
(test_tk111_path_count_bound.py::test_sync_overflow_is_a_clean_refusal_at_the_int4_ceiling),
max under fanout_cap_suspended 92, 0 writes over 1,000.


`core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` compares `fanout >
self.max_closure_fanout`. Wrapping the cap in an int subclass whose reflected `__lt__`
is overridden makes Python call it FIRST for `int > Rec`, so each comparison is recorded
with no edit to src/. Writes one line per test with its max to $FANOUT_OUT, flushing as it goes.
"""
import os, json
import pytest

_cur = {'max': 0, 'max_susp': 0, 'n': 0}
_OUT = os.environ.get('FANOUT_OUT', 'fanout.jsonl')


class Rec(int):
    def __new__(cls, v, idx):
        o = int.__new__(cls, v); o._idx = idx; return o

    def __lt__(self, other):          # reflected `other > self`
        if isinstance(other, int) and not isinstance(other, Rec):
            susp = bool(self._idx._fanout_cap_suspended.on)
            _cur['n'] += 1
            key = 'max_susp' if susp else 'max'
            if other > _cur[key]:
                _cur[key] = other
        if not isinstance(other, int):
            return NotImplemented
        return int(self) < int(other)

    def __reduce__(self):
        return (int, (int(self),))


def pytest_configure(config):
    from zanzibar.graphindex.core import ReachabilityIndex
    orig = ReachabilityIndex.__init__

    def init(self, *a, **k):
        orig(self, *a, **k)
        if self.max_closure_fanout:
            self.max_closure_fanout = Rec(self.max_closure_fanout, self)
    ReachabilityIndex.__init__ = init


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    _cur.update(max=0, max_susp=0, n=0)
    yield
    if _cur['n']:
        with open(_OUT, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'test': item.nodeid, **_cur}) + '\n')
