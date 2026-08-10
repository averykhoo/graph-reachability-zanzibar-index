"""Measure what the CURRENT hypothesis generators reach in the derived cell space.

Draws far MORE examples than the `ci` profile (default 400/generator vs ci's 12) so the
number reported is the generators' CEILING, not a seed-luck sample: a cell missing here is
UNREACHABLE by the present grammar at any max_examples.
"""
from __future__ import annotations

import sys, os, collections, json

sys.path.insert(0, r'C:\Users\user\AppData\Local\Temp')
sys.path.insert(0, r'C:\Users\user\PycharmProjects\graph-reachability-zanzibar-index')

from hypothesis import HealthCheck, Phase, given, settings, strategies as st

import zz_cells as C
from zanzibar_utils_v1 import unparse_schema_ast

N = int(os.environ.get('N', '400'))

import tests.test_hypothesis as H

A = C.alphabet()
ALL_PAIRS = {frozenset(p) for p in __import__('itertools').combinations(sorted(A), 2)}

hits_feat: collections.Counter = collections.Counter()
hits_cell: set = set()
rejected: collections.Counter = collections.Counter()
n_draws = collections.Counter()


def record(gen: str, schema: str, owc=frozenset()):
    n_draws[gen] += 1
    try:
        fs = C.features(schema, owc)
    except Exception as e:                       # compile-rejected config
        rejected[f'{gen}:{type(e).__name__}'] += 1
        return
    for f in fs:
        hits_feat[f] += 1
    hits_cell.update(C.cells_of(fs))


@settings(max_examples=N, deadline=None, database=None,
          suppress_health_check=list(HealthCheck), phases=[Phase.generate])
@given(ast=H.schema_asts())
def collect_schema_asts(ast):
    record('schema_asts', unparse_schema_ast(ast))


@settings(max_examples=N, deadline=None, database=None,
          suppress_health_check=list(HealthCheck), phases=[Phase.generate])
@given(cfg=H.star_bridge_configs())
def collect_star_bridge(cfg):
    record('star_bridge_configs', cfg[0], cfg[1])


@settings(max_examples=N, deadline=None, database=None,
          suppress_health_check=list(HealthCheck), phases=[Phase.generate])
@given(cfg=H.bool_star_bridge_configs())
def collect_bool_star_bridge(cfg):
    record('bool_star_bridge_configs', cfg[0], cfg[1])


DETERMINISTIC = [
    # the handwritten schemas that live in test_hypothesis.py alongside the generators
    ('metamorphic', s, frozenset()) for pair in H.METAMORPHIC_PAIRS for s in pair
] + [
    ('wc_schema', H._WC_SCHEMA, frozenset()),
    ('sb_pin', H._star_bridge_schema('folder', 'admin', 'viewer'),
     frozenset({('folder', 'parent'), ('folder', 'viewer')})),
    ('sb_selfref_pin', H._star_bridge_schema('folder', 'admin', 'admin'),
     frozenset({('folder', 'parent')})),
    ('bool_sb_pin', H._bool_star_bridge_schema('folder', 'admin', 'viewer', 'blocked',
                                               'but not'),
     frozenset({('folder', 'parent')})),
]


def main():
    for fn in (collect_schema_asts, collect_star_bridge, collect_bool_star_bridge):
        fn()
    gen_only_cells = set(hits_cell)
    gen_only_feats = set(hits_feat)
    for name, schema, owc in DETERMINISTIC:
        record('deterministic-pins', schema, owc)

    print(f'alphabet features       : {len(A)}')
    print(f'pair-cell universe      : {len(ALL_PAIRS)}')
    print(f'draws                   : {dict(n_draws)}')
    print(f'compile-rejected draws  : {dict(rejected)}')
    print()
    print(f'FEATURES hit by generators alone      : {len(gen_only_feats)}/{len(A)}'
          f'  ({100*len(gen_only_feats)/len(A):.0f}%)')
    print(f'FEATURES hit incl. deterministic pins : {len(hits_feat)}/{len(A)}'
          f'  ({100*len(hits_feat)/len(A):.0f}%)')
    print(f'CELLS    hit by generators alone      : {len(gen_only_cells)}/{len(ALL_PAIRS)}'
          f'  ({100*len(gen_only_cells)/len(ALL_PAIRS):.1f}%)')
    print(f'CELLS    hit incl. deterministic pins : {len(hits_cell)}/{len(ALL_PAIRS)}'
          f'  ({100*len(hits_cell)/len(ALL_PAIRS):.1f}%)')
    print()
    missing = sorted(set(A) - set(hits_feat))
    print(f'NEVER-HIT FEATURES ({len(missing)}):')
    for m in missing:
        print(f'   {m}')
    print()
    rare = sorted((c, f) for f, c in hits_feat.items() if c <= 3)
    print(f'RARE features (<=3 draws of {sum(n_draws.values())}): {rare}')
    with open('zz_hits.json', 'w') as fh:
        json.dump({'alphabet': list(A), 'features': dict(hits_feat),
                   'n_cells_universe': len(ALL_PAIRS),
                   'cells_gen': sorted('|'.join(sorted(c)) for c in gen_only_cells),
                   'cells_all': sorted('|'.join(sorted(c)) for c in hits_cell)}, fh)


if __name__ == '__main__':
    main()
