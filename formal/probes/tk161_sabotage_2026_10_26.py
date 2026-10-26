"""TK161 sabotage plugin (2026-10-26). Patches ``WildcardIndex._check_derived``'s source in
memory at pytest configure time (anchor asserted to occur exactly once; the method is
recompiled in its own module's globals and rebound on the same class). The source tree is
never edited. Same mechanism as ``tk144_sabotage_plugin_2026_10_17.py``.

Modes (verdicts recorded in ``tests/test_tk161_seedless_phantom_arm.py``'s docstring):

* S1 -- the residue USERSET arm's phantom branch requires a materialised node
  (``subj is not None and ...``), i.e. the Lean edges-alone reading.
* S2 -- the same edit on the BARE-subject arm only (wrong-arm control).

Run (Bash, repo root):

    SAB161=S1 PYTHONPATH=formal/probes python -m pytest -p tk161_sabotage_2026_10_26 \\
        tests/test_tk161_seedless_phantom_arm.py -q
"""
import __future__
import inspect
import os
import sys
import textwrap

MODES = [m for m in os.environ.get('SAB161', '').split(',') if m]

# Indentation is the dedented method's: the userset arm's return sits at 8 spaces, the
# bare-subject arm's at 4, so each anchor occurs once.
_ANCHORS = {
    'S1': ('\n        return subj is None or subj.id not in neg',
           '\n        return subj is not None and subj.id not in neg'),
    'S2': ('\n    return subj is None or subj.id not in neg',
           '\n    return subj is not None and subj.id not in neg'),
}


def _patch(cls, name, old, new):
    fn = getattr(cls, name)
    src = textwrap.dedent(inspect.getsource(fn))
    n = src.count(old)
    if n != 1:
        raise RuntimeError(f'SAB161 anchor for {cls.__name__}.{name} occurs {n} times')
    src = src.replace(old, new)
    module = sys.modules[fn.__module__]
    ns = dict(module.__dict__)
    flags = __future__.annotations.compiler_flag
    exec(compile(src, f'<sab161 {cls.__name__}.{name}>', 'exec', flags=flags,
                 dont_inherit=True), ns)
    setattr(cls, name, ns[name])


def pytest_configure(config):
    from zanzibar.graphindex.wildcard import WildcardIndex
    for mode in MODES:
        old, new = _ANCHORS[mode]
        _patch(WildcardIndex, '_check_derived', old, new)
