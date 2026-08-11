"""Two schema SHAPES taken from real-world OpenFGA models, neither reachable by any
fixture in ``tests/fga_schemas/`` before 2026-08-11.

Provenance: adapted (not copied) from a corpus of real stores reviewed 2026-08-11 --
the canonical ``openfga/sample-stores`` plus a set of internal models. Nothing here is
a verbatim vendored schema; each is the *shape* rewritten against this repo's feature
set, in the same spirit as the existing ``demorgans_*`` fixtures. The corpus review is
recorded in ``HANDOFF.md``.

WHAT IS NEW, AND HOW THAT WAS MEASURED. A scan of all 11 pre-existing ``.fga``
fixtures scored three shapes at ZERO occurrences each:

  S1  a userset restriction whose TARGET relation is derived   ``[team#active_member]``
  S2  a TTU whose TUPLESET admits more than one type           ``[basic_group, custom_group]``
  S3  S2 where the target relation is derived on some -- but not all -- of those types

S2 mattering is the least obvious and the most useful: **every TTU tupleset in the old
corpus was single-type**, so ``parent_types`` was never exercised with breadth > 1.
``parent_types`` breadth is exactly what RC1 got wrong (2026-08-10) -- it dropped a type
that reached the tupleset only through an Exclusion's subtrahend. A single-type corpus
cannot distinguish "computes the set correctly" from "returns the only candidate".

BOTH TTU DIRECTIONS ARE DRIVEN, DELIBERATELY. Each schema carries a positive consumer
(``inherited`` / ``viewer``) and a negated one (``locked`` / ``quarantined``). Per the
severity-sign rule established by the RC1/RC2 arc: *a dropped TTU parent is a false
NEGATIVE under a positive TTU and a false POSITIVE -- an authorization fail-open --
under a negated one*, so probing one direction mis-classifies severity by a sign.

These schemas are NOT regression pins for a known bug: both drive clean today, and an
RC1 sabotage leaves them green (RC1 lives on the tupleset relation; here the derived-ness
is on the target side). They are corpus breadth for shapes the tree could not previously
express.

SABOTAGE EVIDENCE (`docs/sabotage-procedure.md` -- literal observed output). Each guard
in this file was broken and watched go red before it was believed:

  * *the shape assertion*  -- ``define editor: [team#active_member]`` -> ``[user]`` in
    ``userset_over_derived.fga`` (removing exactly the shape the file exists for)::

        FAILED test_real_world_shapes.py::test_shape_is_actually_present[userset_over_derived]
        1 failed, 1 passed, 16 deselected

  * *pool relevance* -- deleting the single tuple
    ``('active_member', 'team', 't1', 'editor', 'folder', 'f1')``::

        FAILED ...::test_userset_over_derived_answers[query0-True]
        FAILED ...::test_userset_over_derived_answers[query2-False]
        2 failed, 2 passed, 14 deselected

    Note it reddens BOTH TTU directions -- the positive (``inherited``) and the negated
    (``locked``). That is the severity-sign rule showing up as a test property.

  * *the graph-joined control* -- widening ``subgroup`` to ``[basic_group, custom_group,
    group]``, reintroducing the recursion of the first draft::

        E  AssertionError: heterogeneous_tupleset.fga did not join the graph index:
           CyclicDerivedDependency: derived relations form a dependency cycle ...
           [('doc', 'quarantined'), ('doc', 'viewer'), ('group', 'member')]

    Without that assertion the same schema ran 13 writes with 0 divergences and reported
    green, having never once exercised the graph index.
"""
from pathlib import Path

import pytest

from tests.parity import ParityEngine
from zanzibar_utils_v1 import (parse_schema_ast, Direct, TTU,
                               Union, Intersection, Exclusion)

_FGA_DIR = Path(__file__).parent / 'fga_schemas'


def _load(name: str) -> str:
    return (_FGA_DIR / f'{name}.fga').read_text(encoding='utf-8')


def _walk(e):
    yield e
    if isinstance(e, (Union, Intersection)):
        for c in e.children:
            yield from _walk(c)
    elif isinstance(e, Exclusion):
        yield from _walk(e.base)
        yield from _walk(e.subtract)


def _shape_counts(schema: str) -> dict:
    """(S1, S2, S3) occurrence counts -- see the module docstring."""
    ast = parse_schema_ast(schema)
    derived = {(ot, r) for (ot, r), ex in ast.items()
               if any(isinstance(n, (Intersection, Exclusion)) for n in _walk(ex))}
    s1 = s2 = s3 = 0
    for (ot, rel), ex in ast.items():
        for n in _walk(ex):
            if isinstance(n, Direct):
                for r in n.restrictions:
                    if r.predicate != '...' and (r.type, r.predicate) in derived:
                        s1 += 1
            elif isinstance(n, TTU):
                ts = ast.get((ot, n.tupleset_rel))
                if ts is None:
                    continue
                types = {r.type for m in _walk(ts) if isinstance(m, Direct)
                         for r in m.restrictions if r.predicate == '...'}
                if len(types) > 1:
                    s2 += 1
                    if any((t, n.target_rel) in derived for t in types):
                        s3 += 1
    return {'S1': s1, 'S2': s2, 'S3': s3}


# --------------------------------------------------------------------------- #
# Driving pools. Each was chosen so that REMOVING the shape changes an answer
# below -- see test_pools_actually_exercise_the_shape.
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

CASES = {
    'userset_over_derived': (_USERSET_OVER_DERIVED_POOL, {'S1': 2, 'S2': 0, 'S3': 0}),
    'heterogeneous_tupleset': (_HETEROGENEOUS_POOL, {'S1': 0, 'S2': 3, 'S3': 3}),
}


@pytest.fixture(params=sorted(CASES))
def case(request):
    name = request.param
    pool, shapes = CASES[name]
    return name, _load(name), pool, shapes


# --------------------------------------------------------------------------- #


def test_shape_is_actually_present(case):
    """ANTI-VACUITY. The fixtures below drive a schema and assert answers; if someone
    edits the ``.fga`` and removes the shape, every one of those assertions would keep
    passing on a schema that no longer covers anything new. Pin the shape itself.
    """
    name, schema, _pool, expected = case
    assert _shape_counts(schema) == expected, (
        f'{name}.fga no longer has the shape it exists for. This file is corpus '
        f'breadth, not a regression pin -- if the schema legitimately changed, '
        f'update CASES and say why in the commit message.')


def test_shape_is_not_covered_by_the_older_corpus(case):
    """The claim "these shapes were unreachable before" is checked, not asserted.

    Without this, the module docstring's central justification is prose that nothing
    verifies -- and if a future fixture happens to introduce S1/S2/S3, this file's
    reason for existing quietly evaporates while it stays green.
    """
    name, _schema, _pool, expected = case
    older = [p for p in sorted(_FGA_DIR.glob('*.fga'))
             if p.stem not in CASES]
    assert older, 'no older fixtures found -- comparison is vacuous'
    for p in older:
        counts = _shape_counts(p.read_text(encoding='utf-8'))
        for key, want in expected.items():
            if want:
                assert counts[key] == 0, (
                    f'{p.name} now also carries shape {key}; {name}.fga is no longer '
                    f'the only source of it. Not a failure of the code -- re-derive '
                    f'this file\'s justification or retire the claim.')


def test_drives_clean_across_every_backend(case):
    """ParityEngine asserts unanimity + FULL-GRID oracle parity inside every write, so
    the expectation is DERIVED (from the independent oracle), not hand-maintained here.
    """
    name, schema, pool, _shapes = case
    eng = ParityEngine(schema)

    # ★ THE CONTROL THAT MATTERS, AND IT IS NOT HYPOTHETICAL. ParityEngine degrades to
    # 3-way (oracle + both set engines) when the graph refuses a schema, and reports
    # green. The first draft of heterogeneous_tupleset.fga did exactly that -- it made
    # `group.member` recursive through a boolean, and the observed output was:
    #
    #     [heterogeneous_tupleset] graph joined: False  DROPPED: CyclicDerivedDependency:
    #       derived relations form a dependency cycle ... [('doc', 'quarantined'),
    #       ('doc', 'viewer'), ('group', 'member')]
    #     [heterogeneous_tupleset] 13 writes, 0 divergences
    #
    # 13 writes, zero divergences, and the graph index -- the entire point of the
    # fixture -- never ran. This assertion is what turns that into a red.
    assert eng.graph is not None, (
        f'{name}.fga did not join the graph index ({eng.graph_drop_reason}). These '
        f'fixtures exist to compare the graph against the other backends; a 3-way run '
        f'here passes while testing nothing it was added for.')

    try:
        for raw in pool:
            assert eng.add_tuple(*raw), f'write refused unexpectedly: {raw}'
    finally:
        eng.close()


# Driving a ParityEngine is expensive -- paranoia runs the invariant checker and the
# delta-scoped verifier inside every commit, and _assert_grid_parity re-runs the whole
# query grid against a freshly rebuilt oracle after every write. Building one engine
# per parametrized query cost 86 s for this file; module scope makes it 8 s. The checks
# below are read-only, so sharing is safe. (Cost matters: `verify.sh`'s worst tests-tile
# already runs ~295 s against a 600 s cap.)
@pytest.fixture(scope='module')
def driven():
    engines = {}
    for name, (pool, _shapes) in CASES.items():
        eng = ParityEngine(_load(name))
        assert eng.graph is not None, (
            f'{name}.fga did not join the graph index: {eng.graph_drop_reason}')
        for raw in pool:
            eng.add_tuple(*raw)
        engines[name] = eng
    yield engines
    for eng in engines.values():
        eng.close()


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
