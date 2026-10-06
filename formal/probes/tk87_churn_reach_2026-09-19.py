#!/usr/bin/env python
"""`TK87` -- what a REMOVAL pass buys the swarm. Probe for docs/tk87-swarm-churn-2026-09-19.md.

THE PREMISE, MEASURED 2026-09-19f, first-hand, before any edit::

    python formal/probes/tk77_crossable_census_2026-09-19.py --pytest \\
        tests/test_generator_coverage.py -q -p no:cacheprovider -s
    tests/test_generator_coverage.py  parse_total 1661  parse_crossable 18
                                      _ensure/raw 6521  _ensure/EFF 46
                                      _sync/raw      0  _sync/EFF    0   CTL 110

``_sync/raw`` **0** is the sharper number: the module did not merely fail to reach the
crossing on a removal, it never executed a removal at all. Every caller of
``src/zanzibar/graphindex/wildcard.py::_sync_entity_middles`` is a removal path (``::remove_edge``,
``::remove_node``, and ``src/zanzibar/graphindex/processor.py``'s reconcile-time GC), and
``tests/genswarm.py::Diff`` exposed ``add`` and ``sweep`` only.

WHAT THIS PROBE ANSWERS
  ``reach``   -- per driven config (``K <= DRIVE_K``), under each regime, with the churn
                 pass ON: EFFECTIVE ``_sync_entity_middles`` calls, removal-sweep
                 comparisons, unrestored backends, divergences. This is the acceptance
                 measurement for the new pin.
  ``regimes`` -- the same sweep with churn OFF vs ON, reporting the divergence sets and
                 wall time of each. The question it settles is whether turning churn on
                 INSIDE the two positive controls would change what they detect; a
                 control whose meaning moved would have to be re-derived, not assumed
                 (``tasks/TK87...``: *"changes what a regime IS"*).

INSTRUMENT NOTE (the census probe's trap (a), which applies here unchanged). A RAW call
count is not reach: both middles entrypoints return at a ``crossable_shapes`` guard, so a
non-crossable schema books calls and reaches nothing. EFF below counts only calls past
that guard, and ``CTL`` (``_ensure_own_bridges`` on a crossable store) is the ceiling
control that tells a real zero from a dead instrument.

USAGE
  python formal/probes/tk87_churn_reach_2026-09-19.py reach   [sparse|dense|full]
  python formal/probes/tk87_churn_reach_2026-09-19.py regimes [sparse|dense|full]
"""
from __future__ import annotations

import collections
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import tests.genswarm as G                                          # noqa: E402
import zanzibar.graphindex.wildcard as W                                       # noqa: E402
from zanzibar.schema import (                                     # noqa: E402
    parse_openfga_schema, unparse_schema_ast)

DRIVE_K = 2                     # must track tests/test_generator_coverage.py::DRIVE_K
STATS: collections.Counter = collections.Counter()


def _instrument():
    """Patch the two middles entrypoints + the ceiling control. Returns a restore fn."""
    saved = {}
    for attr, col in (('_ensure_entity_middles', '_ensure'),
                      ('_sync_entity_middles', '_sync')):
        saved[attr] = getattr(W.WildcardIndex, attr)

        def make(orig=saved[attr], col=col):
            def wrapper(self, entity_type, entity_name, *a, **k):
                STATS[col + '/raw'] += 1
                if entity_name != '*' and any(
                        t == entity_type for (t, _p) in self.schema_info.crossable_shapes):
                    STATS[col + '/EFF'] += 1
                return orig(self, entity_type, entity_name, *a, **k)
            return wrapper

        setattr(W.WildcardIndex, attr, make())

    saved['_ensure_own_bridges'] = W.WildcardIndex._ensure_own_bridges

    def eob(self, node, _orig=saved['_ensure_own_bridges']):
        if self.schema_info.crossable_shapes:
            STATS['CTL'] += 1
        return _orig(self, node)

    W.WildcardIndex._ensure_own_bridges = eob

    def restore():
        for attr, fn in saved.items():
            setattr(W.WildcardIndex, attr, fn)
    return restore


def _configs():
    """``(switches, ast, owc, crossable)`` for every driven config that COMPILES."""
    out = []
    for sw in G.enumerate_configs(DRIVE_K):
        ast, owc = G.witness(sw)
        try:
            rs = parse_openfga_schema(unparse_schema_ast(ast), object_wildcard_shapes=owc)
        except Exception:                                           # noqa: BLE001
            continue
        out.append((tuple(sorted(sw)), ast, owc,
                    bool(rs.schema_info.crossable_shapes)))
    return out


def reach(regime: str) -> int:
    cfgs = _configs()
    print(f'driven configs that compile at K<={DRIVE_K}: {len(cfgs)} '
          f'({sum(1 for c in cfgs if c[3])} crossable)   regime={regime}')
    print(f'{"switches":34}{"X":>3}{"acc":>6}{"rm":>5}{"rmCmp":>8}'
          f'{"_sync/EFF":>11}{"unrest":>8}{"div":>5}')
    restore = _instrument()
    tot = collections.Counter()
    try:
        for sw, ast, owc, crossable in cfgs:
            before = (STATS['_sync/EFF'], STATS['_sync/raw'])
            r = G.drive_config(ast, owc, regime=regime, k=DRIVE_K, seed=7, churn=True)
            eff = STATS['_sync/EFF'] - before[0]
            raw = STATS['_sync/raw'] - before[1]
            tot['acc'] += r.accepted
            tot['rm'] += r.removed
            tot['rmCmp'] += r.remove_comparisons
            tot['eff'] += eff
            tot['raw'] += raw
            tot['unrest'] += len(r.unrestored)
            tot['div'] += len(r.divergences)
            if crossable or r.unrestored or r.divergences:
                print(f'{",".join(sw)[:33]:34}{"Y" if crossable else "-":>3}'
                      f'{r.accepted:>6}{r.removed:>5}{r.remove_comparisons:>8}'
                      f'{eff:>11}{len(r.unrestored):>8}{len(r.divergences):>5}')
    finally:
        restore()
    print(f'{"TOTAL":34}{"":>3}{tot["acc"]:>6}{tot["rm"]:>5}{tot["rmCmp"]:>8}'
          f'{tot["eff"]:>11}{tot["unrest"]:>8}{tot["div"]:>5}')
    print(f'  _sync/raw {tot["raw"]}   CTL {STATS["CTL"]}   '
          f'_ensure/EFF {STATS["_ensure/EFF"]}')
    if not STATS['CTL']:
        print('  (!) INSTRUMENT DEAD: the ceiling control never fired -- the EFF zeros '
              'above are meaningless, not a null result.')
    return 0


def regimes(regime: str) -> int:
    """Churn OFF vs ON over the same configs, same seed: does the regime's VERDICT move?"""
    cfgs = _configs()
    rows = {}
    for churn in (False, True):
        t0 = time.time()
        fo: dict = {}
        fc: dict = {}
        cmp_ = att = acc = driven = 0
        for sw, ast, owc, _x in cfgs:
            r = G.drive_config(ast, owc, regime=regime, k=DRIVE_K, seed=7, churn=churn)
            cmp_ += r.comparisons
            att += r.attempted
            acc += r.accepted
            driven += 1 if r.driven else 0
            for d in r.fail_open:
                fo.setdefault(sw, d)
            for d in r.fail_closed:
                fc.setdefault(sw, d)
        rows[churn] = dict(wall=time.time() - t0, cmp=cmp_, att=att, acc=acc,
                           driven=driven, fo=set(fo), fc=set(fc))
    print(f'regime={regime}  configs={len(cfgs)}')
    for churn in (False, True):
        r = rows[churn]
        print(f'  churn={str(churn):5} wall={r["wall"]:7.1f}s cmp={r["cmp"]:>7} '
              f'att={r["att"]:>5} acc={r["acc"]:>5} driven={r["driven"]:>4} '
              f'FO={len(r["fo"])} fc={len(r["fc"])}')
    same = (rows[False]['fo'] == rows[True]['fo']
            and rows[False]['fc'] == rows[True]['fc'])
    print(f'  detection sets IDENTICAL: {same}')
    if not same:
        print(f'    FO only with churn: {sorted(rows[True]["fo"] - rows[False]["fo"])}')
        print(f'    FO only without:    {sorted(rows[False]["fo"] - rows[True]["fo"])}')
        print(f'    fc only with churn: {sorted(rows[True]["fc"] - rows[False]["fc"])}')
        print(f'    fc only without:    {sorted(rows[False]["fc"] - rows[True]["fc"])}')
    return 0


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'reach'
    reg = sys.argv[2] if len(sys.argv) > 2 else G.SPARSE
    sys.exit({'reach': reach, 'regimes': regimes}[mode](reg))
