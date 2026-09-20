#!/usr/bin/env python
"""`TK77` -- the crossable-shape census. Probe for docs/tk77-crossable-census-2026-09-19.md.

WHAT IT MEASURES. A schema reaches the I14 crossing-middle machinery
(``index_v4/wildcard.py::_ensure_entity_middles`` / ``::_sync_entity_middles``) only if its
``zanzibar_utils_v1.py::SchemaInfo.crossable_shapes`` is non-empty. This probe measures that
property over every corpus and generator in the repo, statically (sections 2-5 of the doc)
and live (section 6).

THREE INSTRUMENT TRAPS. (a) and (b) are what this probe was built to avoid; (c) is one it
WALKED INTO and was caught by `TK89` -- read all three before changing it.

  (a) A RAW call count of ``_ensure_entity_middles`` / ``_sync_entity_middles`` is NOT reach.
      Both are called unconditionally (from ``::_ensure_bridges`` and from
      ``index_v4/processor.py``) and return at a guard when ``crossable_shapes`` is empty, so
      a module with zero crossable schemas still books hundreds of calls. Measured 2026-09-19c
      over seven modules: 7408 raw ``_ensure`` calls, 257 EFFECTIVE; 524 raw ``_sync`` calls,
      8 EFFECTIVE. Reading raw as reach inverts the table's conclusion.

  (b) A zero is ambiguous without a CEILING CONTROL (docs/sabotage-procedure.md). ``CTL`` below
      counts ``_ensure_own_bridges`` calls made while the store's schema IS crossable: it is
      nonzero for every module with a nonzero ``parse_crossable``, so a zero in an EFF column
      means "never reached" rather than "instrument dead". Without it, a patching mistake and
      a genuine coverage hole look identical.

  (c) ⚠ `_ensure/raw` IS NOT REPRODUCIBLE RUN TO RUN, AND NOBODY KNOWS WHY YET. **Do not
      difference it.** MEASURED 2026-09-20g (`TK89`), six runs of the `--pytest
      tests/test_generator_coverage.py` invocation on ONE unchanged tree:

          PYTHONHASHSEED unset : 6617, 6589
          PYTHONHASHSEED=0     : 6627, 6627, 6609, 6627

      Every other column held still in all six -- `parse_total` 1858, `parse_crossable` 24,
      `_ensure/EFF` 78, `_sync/raw` 44, `_sync/EFF` 20, `CTL` 166 -- and the crossable
      shape-set breakdown was byte-identical throughout. So the instrument is reproducible
      on every column an acceptance table has ever quoted; this one column is not.

      ⚠ **Hash randomisation is REFUTED as the cause, by a fix that failed its own
      sabotage.** The first version of this trap blamed `PYTHONHASHSEED` (unset repo-wide,
      so `set` iteration order varies per process) on the strength of two seeded runs that
      agreed. A re-exec-seeded guard was added, and then the guard was sabotaged the only
      way a cross-run non-determinism can be -- run it twice -- and the two seeded runs
      booked **6609** and **6627**. The guard was removed rather than kept as decoration.
      The `n=2` agreement was luck, and believing it would have shipped a wrong mechanism
      with a mechanism-shaped fix attached.

      The remaining trap is therefore a real one and is NOT closed: the column varies by up
      to **38** (0.6%) with no known input changing. Trap (a) already says a raw count is
      not reach, so nothing an acceptance table quotes is affected -- but a future session
      reading a small delta off this column would be reading noise. Localising it is filed
      as `TK93`. Write-up, including why the historical `17` vs `18` was NOT this:
      `docs/tk89-census-reproducibility-2026-09-20.md`.

The static half is deliberately CLOSED and RNG-free where it can be: ``genswarm.witness`` takes
every enabled switch unconditionally, so enumerating all 65535 switch subsets is an exhaustive
statement about that generator's config space rather than a sample.

USAGE
  python formal/probes/tk77_crossable_census_2026-09-19.py             # sections 2-5
  python formal/probes/tk77_crossable_census_2026-09-19.py --pytest <pytest args...>

  The live `PYTHONHASHSEED` is printed into the census table so a transcribed number carries
  its own provenance -- it does NOT make the run reproducible (trap (c)).
"""
from __future__ import annotations

import collections
import glob
import itertools
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# =========================================================================== #
# The pytest plugin -- section 6 of the doc (the LIVE census)
# =========================================================================== #

STATS: collections.Counter = collections.Counter()
CROSS: collections.Counter = collections.Counter()
CTL: collections.Counter = collections.Counter()
BY_MOD: dict = collections.defaultdict(collections.Counter)
_CUR = ['<setup>']

_COLS = ('parse_total', 'parse_crossable',
         '_ensure/raw', '_ensure/EFF', '_sync/raw', '_sync/EFF', 'CTL')


def _bump(key: str, n: int = 1) -> None:
    STATS[key] += n
    BY_MOD[_CUR[0]][key] += n


def pytest_configure(config):        # noqa: D103  (pytest hook)
    import zanzibar_utils_v1 as Z
    import index_v4.wildcard as W

    _parse = Z.parse_openfga_schema

    def parse(*a, **k):
        rs = _parse(*a, **k)
        try:
            cs = frozenset(rs.schema_info.crossable_shapes)
        except Exception:                                   # hand-built rulesets
            cs = frozenset()
        _bump('parse_total')
        if cs:
            _bump('parse_crossable')
            CROSS[(_CUR[0], tuple(sorted(cs)))] += 1
        return rs

    Z.parse_openfga_schema = parse
    # Rebind the `from zanzibar_utils_v1 import parse_openfga_schema` re-exports that
    # already resolved. Modules imported later pick up the patched attribute themselves.
    for mod in list(sys.modules.values()):
        if mod is not None and getattr(mod, 'parse_openfga_schema', None) is _parse:
            mod.parse_openfga_schema = parse

    # EFFECTIVE = past both early returns. See trap (a) above.
    for attr, col in (('_ensure_entity_middles', '_ensure'),
                      ('_sync_entity_middles', '_sync')):
        orig = getattr(W.WildcardIndex, attr)

        def make(orig=orig, col=col):
            def wrapper(self, entity_type, entity_name, *a, **k):
                _bump(col + '/raw')
                if entity_name != '*' and any(
                        t == entity_type for (t, _p) in self.schema_info.crossable_shapes):
                    _bump(col + '/EFF')
                return orig(self, entity_type, entity_name, *a, **k)
            return wrapper

        setattr(W.WildcardIndex, attr, make())

    # The ceiling control. See trap (b) above.
    _eob = W.WildcardIndex._ensure_own_bridges

    def ensure_own_bridges(self, node):
        CTL['calls'] += 1
        if self.schema_info.crossable_shapes:
            _bump('CTL')
        return _eob(self, node)

    W.WildcardIndex._ensure_own_bridges = ensure_own_bridges


def pytest_runtest_logstart(nodeid, location):      # noqa: D103  (pytest hook)
    _CUR[0] = nodeid.split('::')[0]


def pytest_sessionfinish(session, exitstatus):      # noqa: D103  (pytest hook)
    print('\n=== TK77 EFFECTIVE MIDDLES CENSUS (attributed) ===')
    # ⚠ The warning travels WITH the table, not only in the docstring -- a number gets
    # transcribed into a doc far more often than a probe gets re-read (trap (c)).
    print(f"  PYTHONHASHSEED={os.environ.get('PYTHONHASHSEED')!r}   "
          f"(!) `_ensure/raw` is NOT reproducible run-to-run and pinning this seed does "
          f"NOT fix it -- observed 6589/6609/6617/6627 on one unchanged tree "
          f"(TK89, 2026-09-20g). Do not difference that column. Every other column held.")
    print(f'{"module":40}' + ''.join(f'{c:>18}' for c in _COLS))
    for mod in sorted(BY_MOD):
        row = BY_MOD[mod]
        print(f'{mod:40}' + ''.join(f'{row[c]:>18}' for c in _COLS))
    print(f'{"TOTAL":40}' + ''.join(f'{STATS[c]:>18}' for c in _COLS))
    print('  crossable shape-sets seen at parse, by module:')
    for (mod, shapes), n in sorted(CROSS.items()):
        print(f'    {mod:40} {list(shapes)} x{n}')
    if not CTL:
        print('  (!) INSTRUMENT DEAD: not even the ceiling control fired -- the numbers '
              'above are meaningless, not a null result.')


# =========================================================================== #
# The static censuses -- sections 2-5 of the doc
# =========================================================================== #

def _classify(ast):
    """``(bridged_in, literal-T:*#p subset, star-tupleset through-shapes)``.

    The split is the whole point: ``_reject_doubly_bridged_shapes`` categorically refuses to
    let a literal ``T:*#p`` shape also be an object wildcard, so only the through-shapes can
    ever close a crossing."""
    from zanzibar_utils_v1 import derive_schema_info, wildcard_userset_restriction_shapes
    bridged_in = frozenset(derive_schema_info(ast, frozenset()).bridged_in_shapes)
    literal = wildcard_userset_restriction_shapes(ast)
    return bridged_in, bridged_in & literal, bridged_in - literal


def census_fixtures() -> None:
    """Section 2: ``tests/fga_schemas/``."""
    from zanzibar_utils_v1 import parse_schema_ast
    print('=== 2. tests/fga_schemas/ ===')
    print(f'{"fixture":24} {"in":>3} {"lit":>3} {"thru":>4}  through-shapes')
    capable = []
    for path in sorted(glob.glob(str(_REPO_ROOT / 'tests' / 'fga_schemas' / '*.fga'))):
        name = Path(path).stem
        bridged_in, literal, thru = _classify(parse_schema_ast(Path(path).read_text()))
        print(f'{name:24} {len(bridged_in):3} {len(literal):3} {len(thru):4}  {sorted(thru)}')
        if thru:
            capable.append(name)
    print(f'CROSSABLE-CAPABLE fixtures: {capable}\n')


def census_conformance() -> None:
    """Section 3: the conformance enum corpus, each at its OWN declared owc."""
    import formal.conformance.test_conformance_enum as E
    from zanzibar_utils_v1 import parse_schema_ast
    print('=== 3. formal/conformance test_conformance_enum.SCHEMAS ===')
    capable = []
    for name, entry in sorted(E.SCHEMAS.items()):
        text, owc = entry[0], entry[2]
        bridged_in, _lit, thru = _classify(parse_schema_ast(text))
        if thru:
            capable.append(name)
        print(f'  {name:34} in={len(bridged_in)} thru={sorted(thru)} owc={sorted(owc)}')
    print(f'CROSSABLE-CAPABLE conformance schemas: {capable}\n')


def census_genswarm() -> None:
    """Section 4: ``genswarm.witness`` over its CLOSED switch-subset space."""
    sys.path.insert(0, str(_REPO_ROOT / 'tests'))
    import genswarm as G
    from zanzibar_utils_v1 import derive_schema_info
    print('=== 4. tests/genswarm.py witness space (closed, RNG-free) ===')
    configs = G.enumerate_configs(len(G.SWARM_SWITCHES))
    crossable = 0
    thru_seen, owc_seen = set(), set()
    for switches in configs:
        ast, owc = G.witness(switches)
        thru_seen |= _classify(ast)[2]
        owc_seen |= set(owc)
        if derive_schema_info(ast, frozenset(owc)).crossable_shapes:
            crossable += 1
    print(f'  switches                       {len(G.SWARM_SWITCHES)}')
    print(f'  configs enumerated             {len(configs)}')
    print(f'  configs with NON-EMPTY crossable  {crossable}')
    print(f'  through-shapes ever produced   {sorted(thru_seen)}')
    print(f'  owc shapes ever declared       {sorted(owc_seen)}')
    print('  (disjoint sets => no draw count can cross them)\n')


def census_star_bridge() -> None:
    """Section 5: ``test_hypothesis.star_bridge_configs`` over its CLOSED domain."""
    import tests.test_hypothesis as H
    from zanzibar_utils_v1 import parse_openfga_schema
    print('=== 5. tests/test_hypothesis.py::star_bridge_configs (closed domain) ===')
    total = rejected = crossable = 0
    by_arm: collections.Counter = collections.Counter()
    for T in H._SB_TYPES:
        for A in H._SB_RELS:
            for B in H._SB_RELS:
                schema = H._star_bridge_schema(T, A, B)
                domain = sorted({(T, 'parent'), (T, A), (T, B)})
                for size in range(len(domain) + 1):
                    for owc in itertools.combinations(domain, size):
                        total += 1
                        try:
                            rs = parse_openfga_schema(
                                schema, object_wildcard_shapes=frozenset(owc))
                        except Exception:
                            rejected += 1          # doubly-bridged: refused on both backends
                            continue
                        if rs.schema_info.crossable_shapes:
                            crossable += 1
                            by_arm['A==B' if A == B else 'A!=B'] += 1
    print(f'  closed config space               {total}')
    print(f'  compile-REJECTED (doubly-bridged) {rejected}')
    print(f'  CROSSABLE                         {crossable}')
    print(f'  crossable configs by arm          {dict(by_arm)}\n')


def main() -> int:
    os.chdir(_REPO_ROOT)
    if '--pytest' in sys.argv:
        import pytest
        args = sys.argv[sys.argv.index('--pytest') + 1:]
        rc = pytest.main(args, plugins=[sys.modules[__name__]])
        print(f'PYTEST_RC={rc}')
        return int(rc)
    census_fixtures()
    census_conformance()
    census_genswarm()
    census_star_bridge()
    return 0


if __name__ == '__main__':
    sys.exit(main())
