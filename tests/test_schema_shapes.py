"""Schema SHAPES the `.fga` fixture corpus could not express before 2026-08-11.

Three fixtures, added from two different lines of evidence, sharing one harness.

**Where they came from.** ``userset_over_derived`` and ``heterogeneous_tupleset`` were
adapted (never copied) from a corpus of real OpenFGA models reviewed 2026-08-11 --
``openfga/sample-stores`` plus a set of internal stores. Nothing here is a vendored
schema; each is the *shape* rewritten against this repo's feature set, in the same
spirit as the existing ``demorgans_*`` fixtures. ``tupleset_shapes`` came instead from
auditing the fixture corpus against ``tests/genswarm.py``'s DERIVED feature alphabet
and taking what was missing.

**WHY A FIXTURE, when the hypothesis campaign already generates these shapes.** Because
the fixture corpus feeds gates the generated schemas never reach: the byte-identity
compiled-RuleSet snapshot (``test_compile_snapshot.py``), the bulk-vs-incremental
differential gate (``test_bulk_build.py``), and the lookup oracle. A feature absent from
``tests/fga_schemas/`` is absent from all three, however well ``genswarm`` fuzzes it.

**What each contributes, measured against the derived alphabet** (see ``REQUIRED``
below; every one of these was at ZERO occurrences across the pre-existing fixtures, and
``test_features_are_unique_to_this_fixture`` re-checks that on every run rather than
trusting this comment):

  * ``userset_over_derived``   -- a userset restriction whose TARGET relation is derived
    (``[team#active_member]`` where ``active_member`` is an Exclusion). 4 features.
  * ``heterogeneous_tupleset`` -- a TTU whose TUPLESET admits more than one type
    (``[basic_group, custom_group]``), target derived on one arm, untainted on the other.
    ★ The sharpest of the three: **every TTU tupleset in the old corpus was single-type**,
    so ``parent_types`` was never exercised with breadth > 1 -- and ``parent_types``
    breadth is exactly what RC1 got wrong. A single-type corpus cannot distinguish
    "computes the set correctly" from "returns the only candidate".
  * ``tupleset_shapes``        -- three tupleset-axis features at once: a tupleset defined
    by an Intersection, an UNDECLARED tupleset, and a type reaching the tupleset ONLY
    through an Exclusion's negative arm.

★ **``tupleset_shapes`` is a genuine RC1 regression pin, and the only one of the three
that is.** Its ``via_negonly`` arm is RC1's exact shape. Under the RC1 sabotage
(``_member_types``'s Exclusion branch narrowed to ``walk(e.base)``) it does not merely
answer wrong -- it refuses to compile, because the 2026-08-11 invariant catches the
class before any tuple is written::

    ValueError: TTU 'viewer' from 'mixed_parent' in doc#via_negonly: compiled
    parent_types ('folder',) omits type(s) ['doc'] that ADMISSION accepts onto
    doc#mixed_parent ...

The other two stay GREEN under that same sabotage, and the difference is worth
understanding: RC1 lives on the TUPLESET axis, while their derived-ness is on the
TARGET axis. Same feature cross, different axis.

**Both TTU directions are driven for every fixture, deliberately** -- a positive
consumer and a negated one. Per the severity-sign rule from the RC1/RC2 arc: *a dropped
TTU parent is a false NEGATIVE under a positive TTU and a false POSITIVE -- an
authorization fail-open -- under a negated one*, so probing one direction
mis-classifies severity by a sign.

SABOTAGE EVIDENCE (``docs/sabotage-procedure.md`` -- literal observed output). Each
guard here was broken and watched go red before it was believed:

  * *the feature assertion* -- ``define editor: [team#active_member]`` -> ``[user]`` in
    ``userset_over_derived.fga``::

        FAILED test_schema_shapes.py::test_fixture_carries_its_features[userset_over_derived]

  * *pool relevance* -- deleting the single tuple
    ``('active_member', 'team', 't1', 'editor', 'folder', 'f1')``::

        FAILED ...::test_userset_over_derived_answers[query0-True]
        FAILED ...::test_userset_over_derived_answers[query2-False]
        2 failed, 2 passed, 14 deselected

    Note it reddens BOTH TTU directions -- the severity-sign rule as a test property.

  * *the graph-joined control* -- widening ``subgroup`` to
    ``[basic_group, custom_group, group]``, reintroducing the recursion of the first
    draft::

        E  AssertionError: ... did not join the graph index: CyclicDerivedDependency:
           derived relations form a dependency cycle ... [('doc', 'quarantined'),
           ('doc', 'viewer'), ('group', 'member')]

    Without that assertion the same schema ran 13 writes with 0 divergences and
    reported green, having never once exercised the graph index.

  * *a trap this file walked into and had to fix* -- the first ``tupleset_shapes`` draft
    gave ``doc`` no ``viewer`` relation, so the neg-only ``doc`` parent had nothing to
    contribute and RC1's drop could not change any answer. It compiled, drove clean, and
    covered the feature on paper: a "compiled but never driven" cell. ``doc.viewer`` was
    added so ``carol`` -- reachable ONLY through the neg-only parent -- becomes the
    witness, with ``alice`` as the positive-arm control.

    Deleting ``doc.viewer`` again is now caught, though by a different guard than the
    one that motivated it -- carol's tuple stops being ADMISSIBLE at all::

        E  AssertionError: tupleset_shapes: write refused unexpectedly:
           ('...', 'user', 'carol', 'viewer', 'doc', 'd2')

    Note it surfaces as pytest ERRORs (the module fixture dies) rather than FAILEDs.
    That is a weaker signal than a targeted assertion but it is still red, and it is
    why ``driven`` asserts each ``add_tuple`` rather than calling it for effect: a pool
    whose writes are silently refused drives nothing and would otherwise pass.

  * *the feature-uniqueness claim* -- verified by construction rather than by sabotage:
    all eight features across the three fixtures were measured at ZERO occurrences over
    the 11 pre-existing ``.fga`` files before these landed.
"""
from pathlib import Path

import pytest

from tests import genswarm
from tests.parity import ParityEngine

_FGA_DIR = Path(__file__).parent / 'fga_schemas'


def _load(name: str) -> str:
    return (_FGA_DIR / f'{name}.fga').read_text(encoding='utf-8')


# --------------------------------------------------------------------------- #
# Driving pools. Each was chosen so that REMOVING the shape changes an answer
# below -- the "compiled but never driven" trap in the docstring is what happens
# when it is not.
# --------------------------------------------------------------------------- #

_USERSET_OVER_DERIVED_POOL = [
    ('...', 'user', 'alice', 'member', 'team', 't1'),
    ('...', 'user', 'bob', 'member', 'team', 't1'),
    ('...', 'user', 'bob', 'suspended', 'team', 't1'),
    ('active_member', 'team', 't1', 'editor', 'folder', 'f1'),
    ('...', 'folder', 'f1', 'parent', 'doc', 'd1'),
    ('...', 'user', 'carol', 'editor', 'doc', 'd1'),
    ('active_member', 'team', 't1', 'editor', 'doc', 'd2'),
    ('...', 'user', 'alice', 'locked', 'doc', 'd1'),
    ('...', 'user', 'dave', 'locked', 'doc', 'd1'),
]

_HETEROGENEOUS_POOL = [
    ('...', 'user', 'alice', 'member', 'custom_group', 'cg1'),
    ('...', 'user', 'bob', 'member', 'custom_group', 'cg1'),
    ('...', 'user', 'bob', 'banned', 'custom_group', 'cg1'),
    ('...', 'service-account', 'svc1', 'member', 'custom_group', 'cg1'),
    ('...', 'user', 'dave', 'member', 'basic_group', 'bg1'),
    ('...', 'user', '*', 'member', 'basic_group', 'bg2'),
    ('...', 'custom_group', 'cg1', 'subgroup', 'group', 'g1'),
    ('...', 'basic_group', 'bg1', 'subgroup', 'group', 'g1'),
    ('...', 'basic_group', 'bg2', 'subgroup', 'group', 'g2'),
    ('...', 'user', 'frank', 'member', 'group', 'g1'),
    ('...', 'group', 'g1', 'parent', 'doc', 'd1'),
    ('...', 'custom_group', 'cg1', 'parent', 'doc', 'd2'),
    ('...', 'group', 'g2', 'parent', 'doc', 'd3'),
    ('...', 'user', 'erin', 'quarantined', 'doc', 'd1'),
    ('...', 'user', 'alice', 'quarantined', 'doc', 'd1'),
]

_TUPLESET_SHAPES_POOL = [
    ('...', 'user', 'alice', 'viewer', 'folder', 'f1'),
    # carol is reachable ONLY through the neg-only `doc` parent -- the RC1 witness
    ('...', 'user', 'carol', 'viewer', 'doc', 'd2'),
    ('...', 'folder', 'f1', 'vetted', 'doc', 'd1'),
    ('...', 'folder', 'f1', 'approved_parent', 'doc', 'd1'),
    ('...', 'folder', 'f1', 'mixed_parent', 'doc', 'd1'),
    ('...', 'doc', 'd2', 'mixed_parent', 'doc', 'd1'),
]

#: fixture -> the alphabet features it exists to contribute. Names come from
#: ``genswarm.alphabet()``, which is DERIVED from six compiler sites, so this is not a
#: hand-invented taxonomy -- and a compiler change that renames a feature breaks these
#: keys loudly instead of leaving them quietly meaningless.
REQUIRED = {
    'userset_over_derived': {'family:userset-storage', 'leaf:derived-userset',
                             'plan:PDerivedUserset', 'via:userset'},
    'heterogeneous_tupleset': {'ttu.ts:multitype'},
    'tupleset_shapes': {'ttu.ts:Intersection', 'ttu.ts:neg-only-type',
                        'ttu.ts:undeclared'},
}

POOLS = {
    'userset_over_derived': _USERSET_OVER_DERIVED_POOL,
    'heterogeneous_tupleset': _HETEROGENEOUS_POOL,
    'tupleset_shapes': _TUPLESET_SHAPES_POOL,
}

assert set(REQUIRED) == set(POOLS), 'every fixture needs both a feature set and a pool'


@pytest.fixture(params=sorted(REQUIRED))
def case(request):
    return request.param


# --------------------------------------------------------------------------- #


def test_fixture_carries_its_features(case):
    """ANTI-VACUITY. The answer tests below would keep passing on a schema that had been
    edited to drop the very shape it was added for. Pin the features themselves.
    """
    got = genswarm.features(_load(case))
    missing = REQUIRED[case] - got
    assert not missing, (
        f'{case}.fga no longer carries {sorted(missing)}. This fixture exists to bring '
        f'those features into the .fga corpus; if the schema legitimately changed, '
        f'update REQUIRED and say why in the commit message.')


def test_features_are_unique_to_this_fixture(case):
    """The claim "no other fixture reaches these" is CHECKED, not asserted in prose.

    If a future fixture happens to introduce one of these features, this file's reason
    for existing has partly evaporated -- and without this test it would stay green
    while that happened.
    """
    others = [p for p in sorted(_FGA_DIR.glob('*.fga')) if p.stem not in REQUIRED]
    assert others, 'no older fixtures to compare against -- the check is vacuous'
    for p in others:
        overlap = REQUIRED[case] & genswarm.features(p.read_text(encoding='utf-8'))
        assert not overlap, (
            f'{p.name} now also carries {sorted(overlap)}, so {case}.fga is no longer '
            f'the corpus\'s only source of it. Not a code failure -- re-derive this '
            f'fixture\'s justification or retire the claim.')


# Driving a ParityEngine is expensive -- paranoia runs the invariant checker and the
# delta-scoped verifier inside every commit, and _assert_grid_parity re-runs the whole
# query grid against a freshly rebuilt oracle after every write. One engine per
# parametrized query cost 86 s for this file; module scope makes it ~15 s. The checks
# are read-only, so sharing is safe. (Cost matters: verify.sh's worst tests-tile
# already runs ~280 s against a 600 s cap.)
@pytest.fixture(scope='module')
def driven():
    engines = {}
    for name, pool in POOLS.items():
        eng = ParityEngine(_load(name))
        # ★ THE CONTROL THAT MATTERS, AND IT IS NOT HYPOTHETICAL -- see the docstring's
        # sabotage section. ParityEngine degrades to 3-way when the graph refuses a
        # schema, and reports green having never run the index these fixtures exist to
        # compare.
        assert eng.graph is not None, (
            f'{name}.fga did not join the graph index: {eng.graph_drop_reason}. These '
            f'fixtures exist to compare the graph against the other backends; a 3-way '
            f'run here passes while testing nothing it was added for.')
        for raw in pool:
            assert eng.add_tuple(*raw), f'{name}: write refused unexpectedly: {raw}'
        engines[name] = eng
    yield engines
    for eng in engines.values():
        eng.close()


def test_drives_clean_across_every_backend(driven, case):
    """ParityEngine asserts unanimity + FULL-GRID oracle parity inside every write, so
    the expectation is DERIVED from the independent oracle, not maintained here. Reaching
    this point at all means every write in the pool held."""
    assert driven[case].graph is not None


@pytest.mark.parametrize('query,expected', [
    # positive TTU through a userset-over-derived: alice is an active_member of t1,
    # t1#active_member is editor of f1, f1 is parent of d1
    (('...', 'user', 'alice', 'inherited', 'doc', 'd1'), True),
    # bob is suspended -> not active_member -> the derived userset does not carry him
    (('...', 'user', 'bob', 'inherited', 'doc', 'd1'), False),
    # NEGATED TTU (the fail-open direction): alice holds a `locked` grant but is
    # excluded by `but not editor from parent`
    (('...', 'user', 'alice', 'locked', 'doc', 'd1'), False),
    # dave holds the same grant and is NOT an editor -> the exclusion does not fire.
    # alice-vs-dave differ ONLY by the exclusion, so this pair pins the negated arm.
    (('...', 'user', 'dave', 'locked', 'doc', 'd1'), True),
])
def test_userset_over_derived_answers(driven, query, expected):
    assert driven['userset_over_derived'].check(*query) is expected


@pytest.mark.parametrize('query,expected', [
    # through the DERIVED arm of the multi-type tupleset (custom_group.member)
    (('...', 'user', 'alice', 'viewer', 'doc', 'd1'), True),
    # ... and its exclusion still bites two hops away
    (('...', 'user', 'bob', 'viewer', 'doc', 'd1'), False),
    # through the UNTAINTED arm of the same tupleset (basic_group.member)
    (('...', 'user', 'dave', 'viewer', 'doc', 'd1'), True),
    # a non-`user` subject type, admitted only by the derived arm
    (('...', 'service-account', 'svc1', 'viewer', 'doc', 'd1'), True),
    # the derived group as a DIRECT tupleset parent, not via subgroup
    (('...', 'user', 'alice', 'viewer', 'doc', 'd2'), True),
    # a subject wildcard reaching through the multi-type tupleset
    (('...', 'user', 'zoe', 'viewer', 'doc', 'd3'), True),
    # NEGATED TTU over the multi-type tupleset -- the fail-open direction
    (('...', 'user', 'alice', 'quarantined', 'doc', 'd1'), False),
    (('...', 'user', 'erin', 'quarantined', 'doc', 'd1'), True),
])
def test_heterogeneous_tupleset_answers(driven, query, expected):
    assert driven['heterogeneous_tupleset'].check(*query) is expected


@pytest.mark.parametrize('query,expected', [
    # tupleset defined by an INTERSECTION: folder:f1 is both a direct arm member and
    # `vetted`, so it survives the `and` and carries alice through
    (('...', 'user', 'alice', 'via_intersection', 'doc', 'd1'), True),
    # ★ RC1's SHAPE. carol is viewer on doc:d2, and doc:d2 is a STORED mixed_parent of
    # doc:d1 -- reachable only because `doc` appears in the Exclusion's negative arm.
    # CLAUDE.md pins stored-tuple TTU semantics: the TTU walks the stored tuple whatever
    # the exclusion decides about d2's membership. Under the RC1 sabotage this schema
    # does not even compile.
    (('...', 'user', 'carol', 'via_negonly', 'doc', 'd1'), True),
    # positive-arm control: alice arrives via folder:f1, the POSITIVE arm. If this were
    # the only probe, RC1 would be invisible -- it is what makes carol attributable.
    (('...', 'user', 'alice', 'via_negonly', 'doc', 'd1'), True),
    # an UNDECLARED tupleset can hold no tuples, so the TTU is constantly empty
    (('...', 'user', 'alice', 'via_undeclared', 'doc', 'd1'), False),
    (('...', 'user', 'carol', 'via_undeclared', 'doc', 'd1'), False),
])
def test_tupleset_shapes_answers(driven, query, expected):
    assert driven['tupleset_shapes'].check(*query) is expected


# --------------------------------------------------------------------------- #
# Corpus-level floor. Individual fixtures are pinned above; this pins the WHOLE
# .fga corpus so deleting one cannot quietly shrink what the fixture-driven gates
# (snapshot / bulk / lookup) see.
# --------------------------------------------------------------------------- #

#: Features of `genswarm.alphabet()` that NO .fga fixture reaches, and why each is
#: acceptable. Pinned as an exact set, not a count: a floor on the number reached
#: would let a NEW gap open as long as some other feature was added the same day.
#:
#: Measured 2026-08-11. Every entry is either a measurement artifact or carries an
#: executable rejection witness in `genswarm.rejection_features()` -- i.e. the compiler
#: is ASSERTED to refuse it, so it is unreachable by design rather than by omission.
#: Relax a scope check and the witness stops matching, which is how that stays honest.
EXPECTED_UNREACHED = {
    # Not a DSL construct -- object wildcards are passed via `object_wildcard_shapes`.
    # owc_star_ttu.fga DOES mint this when parsed with its real shapes
    # {('folder','viewer'), ('doc','viewer')}; scoring a bare file cannot see it.
    'schema:owc',
    # Refused by scope; witnesses: tupleset-userset-restriction,
    # tupleset-wildcard-userset-restriction, tupleset-rewritten-arms.
    'ttu.ts.restr:userset',
    'ttu.ts.restr:wildcard-userset',
    'ttu.ts:Union',
    # Reachable in some configurations but refused in the common ones; witnesses:
    # owc-on-a-ttu-tupleset, owc-on-derived-relation. Same parameter caveat as above.
    'ttu.ts:owc',
}


def test_fga_corpus_feature_coverage_does_not_regress():
    """The .fga corpus must keep reaching everything it reaches today.

    Provenance: on 2026-08-11 the corpus went from 43/51 features (903/1275 pairwise
    cells) to 46/51 (1035/1275) when the three fixtures above landed. This test pins
    the RESULT, so removing a fixture -- or a compiler change that stops minting a
    feature -- is loud rather than a silently thinner snapshot/bulk/lookup gate.
    """
    alphabet = set(genswarm.alphabet())
    reached = set()
    for p in sorted(_FGA_DIR.glob('*.fga')):
        reached |= genswarm.features(p.read_text(encoding='utf-8'))

    assert reached <= alphabet, (
        f'fixture minted a feature outside the derived alphabet: '
        f'{sorted(reached - alphabet)} -- the alphabet or the scorer is stale')

    unreached = alphabet - reached
    new_gaps = unreached - EXPECTED_UNREACHED
    assert not new_gaps, (
        f'the .fga corpus stopped reaching {sorted(new_gaps)}. Either a fixture was '
        f'removed/edited, or the compiler stopped minting it. Do not add these to '
        f'EXPECTED_UNREACHED to go green -- that list is for features unreachable BY '
        f'DESIGN, each backed by a rejection witness.')

    closed = EXPECTED_UNREACHED - unreached
    assert not closed, (
        f'{sorted(closed)} is now reached by a fixture but still listed as '
        f'unreachable-by-design. Good news -- remove it from EXPECTED_UNREACHED so the '
        f'list keeps meaning what it says.')
