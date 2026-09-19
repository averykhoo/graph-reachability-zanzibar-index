"""TK77 -- the GENERATOR half of the crossable census: what the two fuzzers can reach.

Companion to ``formal/probes/tk77_crossable_census_2026-09-19.py`` (the corpus census,
sections 2-6 of ``docs/tk77-crossable-census-2026-09-19.md``). That probe answers "which
corpora are crossable-capable"; this one answers the two questions section 7 items (2) and
(3) left open, and BOTH of its answers contradicted the section they came from:

  owc       ``tests/genswarm.py::witness`` over its CLOSED switch-subset space, at three
            candidate object-wildcard-shape sets, counting the COMPILE outcome as well as
            the static ``derive_schema_info`` verdict. Section 4 measured the static column
            only and reported 0 of 65535; compiled, the LIVE generator is crossable in 128
            configs -- ``_expand_object_wildcard_shapes`` propagates the declared
            ('doc','parent') onto the TTU head ('doc','r2'), which ``self_ttu`` then makes
            a through-shape. Every one of those 128 needs a switch TRIPLE and ``DRIVE_K``
            is 2, which is why the DRIVEN space was 0 either way.
            The ``guarded`` column is what landed in ``witness``.

  reweight  ``tests/test_hypothesis.py::star_bridge_configs`` drawn-rate census under four
            weightings. Section 5 called the crossable arm "simply rare"; measured, the
            strategy draws crossable at 10.7% of draws -- exactly its closed-domain
            fraction (24/224), i.e. hypothesis samples it about uniformly and it is not
            rare at all. The module's 3-crossable-parses-in-644 is a CONSUMER budget
            figure (how many examples the star-bridge machines get), not a weighting one.

Neither mode writes anything. Run either from the repo root:

    python formal/probes/tk77_generator_reach_2026-09-19.py owc [kmax]
    python formal/probes/tk77_generator_reach_2026-09-19.py reweight [draws] [seed]

``kmax`` defaults to 2 (the DRIVEN width, ``tests/test_generator_coverage.py::DRIVE_K``);
pass 16 for the whole closed space (~95 s). ``reweight`` prints all four variants at one
seed; the landed weighting is ``both``.
"""
from __future__ import annotations

import collections
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, 'tests'))


# --------------------------------------------------------------------------- #
# mode `owc` -- genswarm.witness over its closed switch space
# --------------------------------------------------------------------------- #

def _live_owc(sw):
    """``witness``'s owc BEFORE the 2026-09-19e change (the tupleset shape alone)."""
    return frozenset({('doc', 'parent')}) if 'owc' in sw else frozenset()


def _guarded_owc(sw):
    """What ``witness`` declares NOW: the tupleset shape plus the TTU target, minus the
    two switches whose presence would turn that into a scope refusal."""
    owc = set(_live_owc(sw))
    if owc and 'body_boolean' not in sw and 'body_wc_userset' not in sw:
        owc.add(('doc', 'r1'))
    return frozenset(owc)


def _plus_r1_owc(sw):
    """The naive form of the same idea -- no guard. Kept because it is the argument FOR the
    guard, and the argument is not the one you would guess: MEASURED 2026-09-19e over the
    whole closed space it costs 256 fresh ``DoublyBridgedShapeError`` refusals (4991
    compiled -> 4735) and reaches ``crossable_compiled`` **128** -- the same figure as the
    UNCHANGED generator, and 64 fewer than ``guarded``. It buys nothing and deletes 256
    configs, because the shapes it opens are exactly the ones it then refuses."""
    owc = set(_live_owc(sw))
    if owc:
        owc.add(('doc', 'r1'))
    return frozenset(owc)


def mode_owc(kmax: int) -> None:
    import genswarm as G
    from zanzibar_utils_v1 import (derive_schema_info, parse_openfga_schema,
                                   unparse_schema_ast)
    configs = G.enumerate_configs(kmax)
    variants = (('live', _live_owc), ('guarded', _guarded_owc), ('plus_r1', _plus_r1_owc))
    stats: dict = {n: collections.Counter() for n, _ in variants}
    for sw in configs:
        ast, _owc_now = G.witness(sw)
        text = unparse_schema_ast(ast)
        for name, fn in variants:
            cand = fn(sw)
            c = stats[name]
            c['configs'] += 1
            c['crossable_static'] += bool(derive_schema_info(ast, cand).crossable_shapes)
            try:
                rs = parse_openfga_schema(text, object_wildcard_shapes=cand)
            except Exception as e:                    # noqa: BLE001 (census, not logic)
                c['REJ:' + type(e).__name__] += 1
                continue
            c['compiled'] += 1
            c['crossable_compiled'] += bool(rs.schema_info.crossable_shapes)
    print(f'=== genswarm.witness owc candidates, K<={kmax} ({len(configs)} configs) ===')
    for name, _fn in variants:
        print(f'  {name:9} {dict(sorted(stats[name].items()))}')
    print('  NOTE: `crossable_compiled` is the column the graph index reads (WildcardIndex')
    print('        keys off the COMPILED schema_info); `crossable_static` is the one')
    print('        section 4 of the census measured, and they do not agree.')


# --------------------------------------------------------------------------- #
# mode `reweight` -- star_bridge_configs drawn rates
# --------------------------------------------------------------------------- #

def mode_reweight(draws: int, seed: int) -> None:
    from hypothesis import HealthCheck, given, settings
    from hypothesis import seed as hseed
    from hypothesis import strategies as st

    import tests.test_hypothesis as H
    from zanzibar_utils_v1 import parse_openfga_schema

    def make(variant):
        @st.composite
        def cand(draw):
            T = draw(st.sampled_from(H._SB_TYPES))
            A = draw(st.sampled_from(H._SB_RELS))
            if variant in ('selfbias', 'both'):
                B = A if draw(st.booleans()) else draw(st.sampled_from(H._SB_RELS))
            else:
                B = draw(st.sampled_from(H._SB_RELS))
            domain = sorted({(T, 'parent'), (T, A), (T, B)})
            owc = set(draw(st.sets(st.sampled_from(domain), max_size=len(domain))))
            if variant in ('owcbias', 'both') and A == B and draw(st.booleans()):
                owc.add((T, B))
            return H._star_bridge_schema(T, A, B), frozenset(owc), A == B
        return cand()

    print(f'=== star_bridge_configs drawn rates, {draws} draws, hypothesis seed {seed} ===')
    for variant in ('live', 'selfbias', 'owcbias', 'both'):
        c: collections.Counter = collections.Counter()

        @given(cfg=make(variant))
        @settings(max_examples=draws, deadline=None, database=None,
                  suppress_health_check=list(HealthCheck))
        @hseed(seed)
        def run(cfg):
            schema, owc, selfref = cfg
            c['draws'] += 1
            c['A==B' if selfref else 'A!=B'] += 1
            try:
                rs = parse_openfga_schema(schema, object_wildcard_shapes=owc)
            except Exception as e:                    # noqa: BLE001 (census, not logic)
                c['REJ:' + type(e).__name__] += 1
                return
            c['compiled'] += 1
            c['crossable'] += bool(rs.schema_info.crossable_shapes)

        run()
        print(f'  {variant:9} crossable/draws={100.0 * c["crossable"] / c["draws"]:5.1f}%'
              f'  compiled/draws={100.0 * c["compiled"] / c["draws"]:5.1f}%'
              f'  A==B={c["A==B"]:4}  {dict(sorted(c.items()))}')
    print('  `live` is the weighting before 2026-09-19e; `both` is what landed.')


def main(argv) -> int:
    if len(argv) < 2 or argv[1] not in ('owc', 'reweight'):
        print(__doc__)
        return 2
    if argv[1] == 'owc':
        mode_owc(int(argv[2]) if len(argv) > 2 else 2)
    else:
        mode_reweight(int(argv[2]) if len(argv) > 2 else 300,
                      int(argv[3]) if len(argv) > 3 else 0)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
