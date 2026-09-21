#!/usr/bin/env python
"""`TK93` -- WHICH TEST moves `_ensure/raw`? Per-nodeid attribution + a cross-run diff.

WHY THIS EXISTS. `formal/probes/tk77_crossable_census_2026-09-19.py` books `_ensure/raw`
(calls to ``index_v4/wildcard.py::WildcardIndex._ensure_entity_middles``) by MODULE -- its
``pytest_runtest_logstart`` hook does ``nodeid.split('::')[0]`` -- so a column that moves by
up to 38 between runs on one unchanged tree names 31 tests at once. `TK93`'s acceptance asks
for per-test resolution and suggests a `-k` bisection; this is the same answer one level
cheaper: attribute by FULL nodeid and by CALLER, run the module N times in separate
subprocesses at a fixed seed, and diff.

WHAT IS COUNTED, and why it is three things and not one.

  * ``raw``       -- calls to ``_ensure_entity_middles``, the census's column, per nodeid.
  * ``by_caller`` -- the same calls split by immediate caller (``file:line:func``). The live
    callers are ``_ensure_bridges`` (two per ``add_tuple``), the migration loop at
    ``wildcard.py:415`` and the crossable-types loop at ``wildcard.py:540``. A drift under
    ``_ensure_bridges`` means the test WROTE a different number of tuples; a drift under the
    other two means the same writes walked a different number of entities.
  * ``bridges``   -- calls to ``_ensure_bridges``, i.e. write volume, so those two causes
    stay distinguishable even if a caller line number moves.

(!) INSTRUMENT CONTROLS -- this probe has to be trusted before its table is.

  (i)   CONSERVATION. The per-nodeid ``raw`` values are summed and compared against a
        separately accumulated TOTAL. A mismatch prints as INSTRUMENT FAILURE. That is what
        pins "the attribution did not lose calls into an unbooked row".
  (ii)  RESOLUTION CONTROL (`M0`-shaped, `docs/sabotage-procedure.md` sec "Sweep the TEST
        MODULE with mutations"). ``--control <nodeid>`` runs one extra arm in which the
        wrapper books one SYNTHETIC extra call whenever that nodeid is current; the driver
        then demands the diff name exactly that nodeid. A broken attribution reports every
        test as clean, which reads exactly like a clean module -- this control is what tells
        those two apart.
  (iii) A missing or unreadable JSON is reported as INSTRUMENT FAILURE, never as zeros, and
        the pytest rc and summary travel with every run (`CLAUDE.md`'s exit-code footgun).

USAGE
  python formal/probes/tk93_ensure_raw_bisect_2026-09-21.py [--runs N] [--seed S | --unset]
                                                            [--control <nodeid>] [--keep DIR]
  python formal/probes/tk93_ensure_raw_bisect_2026-09-21.py --pytest <pytest args...>
      (the plugin arm; the driver spawns this form, it is not normally run by hand)

THE VERDICT -- see the RAN block appended at the bottom of this file after the run.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_PY = sys.executable
_TARGET = 'tests/test_generator_coverage.py'

# =========================================================================== #
# The pytest plugin half
# =========================================================================== #

RAW: collections.Counter = collections.Counter()
BY_CALLER: collections.Counter = collections.Counter()
BRIDGES: collections.Counter = collections.Counter()
BRIDGE_CALLER: collections.Counter = collections.Counter()
APPLY: collections.Counter = collections.Counter()
ADDS: collections.Counter = collections.Counter()
ABORT: collections.Counter = collections.Counter()
_POS = [0]
TOTAL: collections.Counter = collections.Counter()
_CUR = ['<setup>']
_SUMMARY = ['?']


def pytest_configure(config):        # noqa: D103  (pytest hook)
    import index_v4.wildcard as W

    ctl_nodeid = os.environ.get('TK93_CTL_NODEID') or None

    _eem = W.WildcardIndex._ensure_entity_middles

    def ensure_entity_middles(self, entity_type, name, *a, **k):
        f = sys._getframe(1)
        caller = f'{Path(f.f_code.co_filename).name}:{f.f_lineno}:{f.f_code.co_name}'
        RAW[_CUR[0]] += 1
        TOTAL['raw'] += 1
        BY_CALLER[(_CUR[0], caller)] += 1
        if ctl_nodeid is not None and _CUR[0] == ctl_nodeid:
            # (ii) the resolution control: one synthetic extra call for ONE named test.
            RAW[_CUR[0]] += 1
            TOTAL['raw'] += 1
            BY_CALLER[(_CUR[0], '<TK93-CONTROL>')] += 1
        return _eem(self, entity_type, name, *a, **k)

    W.WildcardIndex._ensure_entity_middles = ensure_entity_middles

    _eb = W.WildcardIndex._ensure_bridges

    def ensure_bridges(self, node):
        # Depth 2: ``by_caller`` above only ever names ``_ensure_bridges:339``, which is
        # the callee's own line. WHICH write path called it (``add_tuple`` vs the delta
        # processor's candidate loop vs a migration) is the thing that separates "the
        # test wrote a different number of tuples" from "the same writes walked a
        # different number of nodes", so the chain is recorded two frames up.
        chain = []
        f = sys._getframe(1)
        for _ in range(2):
            if f is None:
                break
            chain.append(f'{Path(f.f_code.co_filename).name}:{f.f_lineno}:{f.f_code.co_name}')
            f = f.f_back
        BRIDGES[_CUR[0]] += 1
        TOTAL['bridges'] += 1
        BRIDGE_CALLER[(_CUR[0], ' <- '.join(chain))] += 1
        return _eb(self, node)

    W.WildcardIndex._ensure_bridges = ensure_bridges

    # ---------------------------------------------------------------- #
    # The mechanism arm: fan-out ORDER
    # ---------------------------------------------------------------- #
    # ``tests/parity.py::_GraphSide.apply`` runs
    #     try:  [ add_tuple(d) for d in ruleset.apply(triple) ]  except ValueError: rollback
    # and ``zanzibar_utils_v1.py::RuleSet.apply`` yields out of a **set** (``seeds``, or the
    # ``unprocessed.pop()`` worklist). So when one member of a fan-out raises, HOW MANY
    # ``add_tuple`` calls already completed is the raiser's position in a set iteration
    # order -- seed-dependent -- while the decision (rollback, False) is not.
    #
    # ``sorted``: same multiset of writes, deterministic order. Nothing else. If the column
    # goes seed-INDEPENDENT under this arm, fan-out order is the mechanism; if it does not,
    # this refutes it. Materialising the generator is safe for that claim because the
    # raiser is ``add_tuple`` (the consumer), not the generator -- ``RuleSet.apply``'s own
    # ``AdmissionRejected``s are raised before the first yield.
    import zanzibar_utils_v1 as Z

    _ra = Z.RuleSet.apply
    sort_fanout = os.environ.get('TK93_SORTED_FANOUT') == '1'

    def _tkey(t):
        return (str(t.subject_predicate), t.subject.type, t.subject.name,
                t.relation, t.object.type, t.object.name)

    def ruleset_apply(self, triple):
        APPLY[_CUR[0]] += 1
        TOTAL['ruleset_apply'] += 1
        _POS[0] = 0                     # position within THIS raw tuple's fan-out
        if sort_fanout:
            return iter(sorted(_ra(self, triple), key=_tkey))
        return _ra(self, triple)        # lazy, order untouched

    Z.RuleSet.apply = ruleset_apply

    _at = W.WildcardIndex.add_tuple

    def add_tuple(self, *a, **k):
        ADDS[_CUR[0]] += 1
        TOTAL['add_tuple'] += 1
        _POS[0] += 1
        try:
            return _at(self, *a, **k)
        except BaseException as e:       # noqa: BLE001 -- recorded, then re-raised
            # THE truncation event. ``_GraphSide.apply``'s loop dies here, so the
            # number of completed writes for this raw tuple is ``_POS[0] - 1`` -- and
            # that is the raiser's POSITION in the fan-out, which is a set iteration
            # order. Position > 1 is the case that makes the count seed-dependent.
            ABORT[(_CUR[0], type(e).__name__, _POS[0])] += 1
            TOTAL['aborts'] += 1
            raise

    W.WildcardIndex.add_tuple = add_tuple


def pytest_runtest_logstart(nodeid, location):      # noqa: D103  (pytest hook)
    _CUR[0] = nodeid


def pytest_sessionfinish(session, exitstatus):      # noqa: D103  (pytest hook)
    out = os.environ.get('TK93_OUT')
    if not out:
        return
    # Read the counts off the terminal reporter HERE rather than from
    # ``pytest_terminal_summary``: sessionfinish implementations run LIFO, so this
    # plugin's runs before the terminal reporter's and a summary captured there would
    # still be '?' by the time it is serialised.
    rep = session.config.pluginmanager.get_plugin('terminalreporter')
    if rep is not None:
        _SUMMARY[0] = ' '.join(f'{k}={len(v)}' for k, v in sorted(rep.stats.items()) if k)
    payload = {
        'raw': dict(RAW),
        'bridges': dict(BRIDGES),
        'apply': dict(APPLY),
        'adds': dict(ADDS),
        'abort': {f'{n}	{k}	pos={i}': v for (n, k, i), v in ABORT.items()},
        'by_caller': {f'{n}\t{c}': v for (n, c), v in BY_CALLER.items()},
        'bridge_caller': {f'{n}\t{c}': v for (n, c), v in BRIDGE_CALLER.items()},
        'total': dict(TOTAL),
        'exitstatus': int(exitstatus),
        'summary': _SUMMARY[0],
        'hashseed': os.environ.get('PYTHONHASHSEED'),
    }
    Path(out).write_text(json.dumps(payload, indent=1, sort_keys=True), encoding='utf-8')


# =========================================================================== #
# The driver half
# =========================================================================== #

def one_run(out_path: Path, seed, ctl_nodeid=None, extra_args=(), sorted_fanout=False):
    env = dict(os.environ)
    env['TK93_SORTED_FANOUT'] = '1' if sorted_fanout else '0'
    if seed is None:
        env.pop('PYTHONHASHSEED', None)
    else:
        env['PYTHONHASHSEED'] = str(seed)
    env['TK93_OUT'] = str(out_path)
    if ctl_nodeid:
        env['TK93_CTL_NODEID'] = ctl_nodeid
    else:
        env.pop('TK93_CTL_NODEID', None)
    p = subprocess.run(
        [_PY, str(Path(__file__).resolve()), '--pytest', _TARGET,
         '-q', '-p', 'no:cacheprovider', '-s', *extra_args],
        cwd=_REPO_ROOT, capture_output=True, text=True, env=env)
    if not out_path.exists():
        return p.returncode, None, (p.stdout[-2000:] + p.stderr[-2000:])
    try:
        return p.returncode, json.loads(out_path.read_text(encoding='utf-8')), ''
    except Exception as e:                                  # noqa: BLE001
        return p.returncode, None, f'JSON unreadable: {e!r}'


def _check(payload) -> list:
    """(i) CONSERVATION -- per-nodeid raw must sum to the independently kept TOTAL."""
    problems = []
    s = sum(payload['raw'].values())
    t = payload['total'].get('raw')
    if s != t:
        problems.append(f'INSTRUMENT FAILURE: per-nodeid raw sums to {s}, TOTAL says {t}')
    if payload['raw'].get('<setup>'):
        problems.append(f"NOTE: {payload['raw']['<setup>']} calls booked to <setup>")
    if payload['exitstatus'] != 0:
        problems.append(f"RUN NOT CLEAN: exitstatus={payload['exitstatus']} "
                        f"summary={payload['summary']}")
    return problems


def _diff(runs, key):
    labels = sorted({k for r in runs for k in r.get(key, {})})
    moved = {}
    for lab in labels:
        vals = [r.get(key, {}).get(lab, 0) for r in runs]
        if len(set(vals)) > 1:
            moved[lab] = vals
    return labels, moved


def _report(runs) -> None:
    for key in ('raw', 'bridges', 'apply', 'adds'):
        labels, moved = _diff(runs, key)
        print(f'\n=== {key}: {len(labels)} nodeids, {len(moved)} MOVED across '
              f'{len(runs)} runs ===')
        for lab, vals in sorted(moved.items(), key=lambda kv: min(kv[1]) - max(kv[1])):
            print(f'  spread {max(vals) - min(vals):>6}  {vals}  {lab}')
        if not moved:
            print('  (every nodeid identical in every run)')

    for key in ('by_caller', 'bridge_caller', 'abort'):
        labels, moved = _diff(runs, key)
        print(f'\n=== {key}: {len(labels)} (nodeid, caller) cells, {len(moved)} MOVED ===')
        for lab, vals in sorted(moved.items(), key=lambda kv: min(kv[1]) - max(kv[1])):
            print(f'  spread {max(vals) - min(vals):>6}  {vals}  {lab}')
        if not moved:
            print('  (every cell identical in every run)')


def drive() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--seed', default='0')
    ap.add_argument('--unset', action='store_true', help='leave PYTHONHASHSEED unset')
    ap.add_argument('--seeds', default='',
                    help='comma-separated PYTHONHASHSEED values; one run each, then a '
                         'BETWEEN-seed diff. This is the arm that separates "varies '
                         'run to run" from "varies seed to seed"')
    ap.add_argument('--sorted-fanout', action='store_true',
                    help='MECHANISM ARM: make RuleSet.apply yield its fan-out in sorted '
                         'order (same writes, deterministic order). Seed-independence '
                         'under this arm confirms fan-out order as the mechanism')
    ap.add_argument('--control', default='', help='nodeid for the resolution-control arm')
    ap.add_argument('--keep', default='', help='directory for the per-run JSON')
    ap.add_argument('--load', default='', help='re-report from a --keep directory, no runs')
    args = ap.parse_args(sys.argv[1:])
    seed = None if args.unset else args.seed

    if args.load:
        runs = [json.loads(p.read_text(encoding='utf-8'))
                for p in sorted(Path(args.load).glob('run*.json'))]
        print(f'loaded {len(runs)} run(s) from {args.load}')
        if len(runs) < 2:
            print('VERDICT: INCONCLUSIVE -- fewer than two usable runs')
            return 1
        _report(runs)
        return 0

    tmp = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(prefix='tk93-'))
    tmp.mkdir(parents=True, exist_ok=True)
    print(f'JSON -> {tmp}')

    if args.seeds:
        seeds = [s.strip() for s in args.seeds.split(',')]
        runs = []
        for s in seeds:
            rc, payload, tail = one_run(
                tmp / f'run-seed{s}.json', None if s == 'unset' else s,
                sorted_fanout=args.sorted_fanout)
            if payload is None:
                print(f'  seed {s}: INSTRUMENT FAILURE (no usable JSON) rc={rc}\n{tail}')
                continue
            for p in _check(payload):
                print(f'  seed {s}: (!) {p}')
            print(f"  seed {s}: rc={rc} raw={payload['total']['raw']} "
                  f"bridges={payload['total']['bridges']} "
                  f"ruleset_apply={payload['total'].get('ruleset_apply')} "
                  f"add_tuple={payload['total'].get('add_tuple')} "
                  f"seed={payload['hashseed']} {payload['summary']}")
            runs.append(payload)
        if len(runs) < 2:
            print('VERDICT: INCONCLUSIVE -- fewer than two usable runs')
            return 1
        print('\n(!) the tables below are a BETWEEN-SEED diff -- a cell that moves here is '
              'seed-dependent, which is a different claim from run-to-run drift')
        _report(runs)
        return 0

    runs = []
    for i in range(args.runs):
        rc, payload, tail = one_run(tmp / f'run{i}.json', seed)
        if payload is None:
            print(f'  run {i}: INSTRUMENT FAILURE (no usable JSON) rc={rc}\n{tail}')
            continue
        for p in _check(payload):
            print(f'  run {i}: (!) {p}')
        print(f"  run {i}: rc={rc} raw={payload['total']['raw']} "
              f"bridges={payload['total']['bridges']} "
              f"ruleset_apply={payload['total'].get('ruleset_apply')} "
              f"add_tuple={payload['total'].get('add_tuple')} "
              f"seed={payload['hashseed']} {payload['summary']}")
        runs.append(payload)

    if len(runs) < 2:
        print('VERDICT: INCONCLUSIVE -- fewer than two usable runs')
        return 1
    _report(runs)

    if args.control:
        print(f'\n===== RESOLUTION CONTROL arm: {args.control} =====')
        rc, payload, tail = one_run(tmp / 'ctl.json', seed, ctl_nodeid=args.control)
        if payload is None:
            print(f'  INSTRUMENT FAILURE (no usable JSON) rc={rc}\n{tail}')
            return 1
        base = runs[0]
        deltas = {k: payload['raw'].get(k, 0) - base['raw'].get(k, 0)
                  for k in set(payload['raw']) | set(base['raw'])}
        named = {k: v for k, v in deltas.items() if v}
        print(f'  nodeids whose raw differs from run 0: {named}')
        ok = named.get(args.control, 0) >= 1
        print(f'  CONTROL {"PASSED" if ok else "FAILED"}: the synthetic extra call '
              f'{"was" if ok else "was NOT"} attributed to {args.control}')
        print('  (!) other movers in this list are the drift itself, not control failures')
    return 0


def main() -> int:
    os.chdir(_REPO_ROOT)
    if '--pytest' in sys.argv:
        import pytest
        args = sys.argv[sys.argv.index('--pytest') + 1:]
        rc = pytest.main(args, plugins=[sys.modules[__name__]])
        print(f'PYTEST_RC={rc}')
        return int(rc)
    return drive()


if __name__ == '__main__':
    raise SystemExit(main())

# =========================================================================== #
# RAN 2026-09-21 -- THE VERDICT
# =========================================================================== #
#
#   --seeds 0,1,2,3                 raw = 6617 / 6627 / 6609 / 6605   (31 passed each)
#   --seeds 0,1,2,3 --sorted-fanout raw = 6627 / 6627 / 6627 / 6627   (0 MOVED, every cell)
#   --runs 3 --seed 0               raw = 6617, 6617, 6617            (0 MOVED)
#   --runs 2 --seed 1               raw = 6627, 6627                  (0 MOVED)
#   --runs 2 --seed 2               raw = 6609, 6609                  (0 MOVED)
#
# `_ensure/raw` is a FUNCTION OF `PYTHONHASHSEED`, not a run-to-run drift: 20 seeded runs,
# four seeds, zero within-seed variation. `TK89`'s `{6589, 6609, 6617, 6627}` is four SEEDS.
#
# WHERE: two tests only (`::test_dense_regime_finds_no_fail_open_divergence`,
# `::test_sparse_regime_finds_no_fail_closed_divergence`), entirely through
# `wildcard.py:600/601:_add_tuple_trusted <- wildcard.py:563:add_tuple`.
#
# WHY: `RuleSet.apply` yields its fan-out out of a `set`; `tests/parity.py::_GraphSide.apply`
# consumes it in one `try` that rolls back on `ValueError`. Raw tuples POSED is `7499` at
# every seed and the abort count is invariant (`21`, all at fan-out position >= 2) -- only
# the raiser's POSITION moves, and `2 x` the completed-prefix delta accounts for the column
# exactly (dense +3 writes -> +6 raw; sparse +2 -> +4).
#
# Nothing observable moves. Full write-up, including the four instrument controls and what
# is left owed: `docs/tk93-ensure-raw-seed-dependence-2026-09-21.md`.
