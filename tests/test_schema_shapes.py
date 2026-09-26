"""Schema SHAPES the `.fga` fixture corpus could not express before 2026-08-11.

Four fixtures, added from two different lines of evidence, sharing one harness.

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
below, which ``test_fixture_carries_its_features`` re-checks on every run rather than
trusting this comment). Note the claim is "this fixture COVERS these", not "only this
fixture covers these" -- see ``test_subsumption_register_is_current`` for why per-fixture
uniqueness is the wrong bar:

  * ``userset_over_derived``   -- a userset restriction whose TARGET relation is derived
    (``[team#active_member]`` where ``active_member`` is an Exclusion). 4 features.
  * ``heterogeneous_tupleset`` -- a TTU whose TUPLESET admits more than one type
    (``[basic_group, custom_group]``), target derived on one arm, untainted on the other.
    ★ The sharpest of the three: **every TTU tupleset in the old corpus was single-type**,
    so ``parent_types`` was never exercised with breadth > 1 -- and ``parent_types``
    breadth is exactly what RC1 got wrong. A single-type corpus cannot distinguish
    "computes the set correctly" from "returns the only candidate".
  * ``tupleset_shapes``        -- RETIRED 2026-09-26 (TK106). It carried a tupleset defined
    by an Intersection and a type reaching the tupleset ONLY through an Exclusion's
    negative arm; TK106 (user decision) made every non-direct tupleset a parse refusal,
    so no relation in it survived. Its features are now carried by the genswarm
    rejection witnesses ``tupleset-intersection`` / ``tupleset-neg-only-type``.
  * ``wildcard_userset_cross``  -- contributes no NEW feature; its value is entirely
    CO-OCCURRENCE, and that is the point. ``restr:wildcard-userset`` (``group:*#member``)
    lived only in ``wildcards.fga``, a schema with no boolean operator anywhere, so the
    wildcard userset had **never met an ``and``/``but not`` in the fixture corpus** -- 35
    of its pairs were unrealised and 21 close here. genswarm's cell space is pairwise and
    this project's position is that every bug it has found is an interaction bug, so a
    fixture that only crosses existing features still earns its place. It also chains a
    subject wildcard (``user:*`` member of a group) INTO the wildcard userset INTO a TTU.

★ **RETIRED 2026-09-26 (TK106), kept as history: ``tupleset_shapes`` WAS a genuine RC1
regression pin, and the only one of the three that was.** RC1's shape (a type reaching a
tupleset only through a ``but not`` arm) is now a parse refusal in both parsers, so the
bug class cannot be written; the refusal is pinned in
``tests/test_ttu_tupleset_parent_types.py``. What follows is the pin as it stood. Its ``via_negonly`` arm is RC1's exact shape. Under the RC1 sabotage
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

  * *the bar itself* -- the two corpus floors (`test_corpus_pair_coverage_does_not_regress`
    and `test_fga_corpus_feature_coverage_does_not_regress`) are what actually protect
    coverage, and both were sabotaged by deleting a fixture: the feature floor named the
    exact three lost features, and the pair floor drops below 839 (its value then).

    ⚠ **An earlier version of this file asserted per-fixture UNIQUENESS instead, and it
    was wrong twice over.** It reddened when ``wildcard_userset_cross`` legitimately
    re-covered features two earlier fixtures had introduced -- punishing exactly the
    corpus growth this file exists to encourage -- and leave-one-out uniqueness masks
    itself, since two fixtures jointly holding the only copy of a feature each see the
    other in their "others" set and BOTH score zero. Replaced with corpus-level
    bar-raising floors plus a retirement register. The eight features of the first three
    fixtures were measured at ZERO occurrences over the 11 pre-existing ``.fga`` files
    before they landed; that was true, it was just never the right thing to ASSERT.
"""
from itertools import combinations
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

_WILDCARD_USERSET_CROSS_POOL = [
    ('...', 'user', 'alice', 'member', 'group', 'g1'),
    ('...', 'user', '*', 'member', 'group', 'g2'),
    ('member', 'group', 'g1', 'member', 'group', 'g3'),
    ('...', 'user', 'bob', 'lead', 'team', 't1'),
    ('...', 'user', 'carol', 'lead', 'team', 't1'),
    ('...', 'user', 'carol', 'blocked', 'team', 't1'),
    ('active_lead', 'team', 't1', 'owner', 'folder', 'f1'),
    ('member', 'group', 'g1', 'viewer', 'folder', 'f1'),
    # ★ the wildcard userset: "member of ANY group"
    ('member', 'group', '*', 'viewer', 'folder', 'f2'),
    ('...', 'folder', 'f1', 'parent', 'doc', 'd1'),
    ('...', 'folder', 'f2', 'parent', 'doc', 'd2'),
    ('...', 'group', 'g1', 'parent', 'doc', 'd3'),
    ('...', 'user', 'dave', 'sealed', 'doc', 'd1'),
    ('...', 'user', 'alice', 'sealed', 'doc', 'd1'),
]

#: fixture -> the alphabet features it exists to contribute. Names come from
#: ``genswarm.alphabet()``, which is DERIVED from six compiler sites, so this is not a
#: hand-invented taxonomy -- and a compiler change that renames a feature breaks these
#: keys loudly instead of leaving them quietly meaningless.
REQUIRED = {
    'userset_over_derived': {'family:userset-storage', 'leaf:derived-userset',
                             'plan:PDerivedUserset', 'via:userset'},
    'heterogeneous_tupleset': {'ttu.ts:multitype'},
    # `tupleset_shapes` ({'ttu.ts:Intersection', 'ttu.ts:neg-only-type'}) RETIRED
    # 2026-09-26 by TK106: both are now parse refusals (see EXPECTED_UNREACHED).
    # Contributes no NEW feature -- its value is co-occurrence. `restr:wildcard-userset`
    # lived only in the non-boolean wildcards.fga and had never met a boolean operator;
    # 21 of its 35 unpaired combinations close here.
    'wildcard_userset_cross': {'restr:wildcard-userset', 'ttu.ts:multitype',
                               'family:userset-storage', 'plan:PDerivedComputed'},
}

POOLS = {
    'userset_over_derived': _USERSET_OVER_DERIVED_POOL,
    'heterogeneous_tupleset': _HETEROGENEOUS_POOL,
    'wildcard_userset_cross': _WILDCARD_USERSET_CROSS_POOL,
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


def _pairs(fs):
    """Feature co-occurrences -- the unit genswarm's cell space is built from."""
    return {(a, b) for a, b in combinations(sorted(fs), 2)}


def _corpus():
    """{fixture stem -> features} for every .fga in the corpus."""
    return {p.stem: genswarm.features(p.read_text(encoding='utf-8'))
            for p in sorted(_FGA_DIR.glob('*.fga'))}


#: Fixtures whose features AND pairs are all covered by other fixtures. Being listed
#: here is NOT a failure and carries no obligation to delete -- these are the large,
#: realistic schemas, and pairwise scoring cannot see a unique TRIPLE, compile-order
#: effect, or sheer scale. It is a RETIREMENT REGISTER: when a fixture lands here it
#: has become a candidate to retire someday, and the list makes that visible instead of
#: leaving it to be rediscovered by an audit nobody runs.
#:
#: Measured 2026-08-11, and robust two ways: leave-one-out says each is subsumed, and
#: dropping ALL FIVE AT ONCE also loses 0 features and 0 pairs -- so this is not the
#: leave-one-out masking artifact where two fixtures jointly hold something unique and
#: hide it from each other. (Checked: 0 features and 0 pairs are held by exactly two
#: fixtures both on this list.)
#:
#: `demorgans_law_1` joined 2026-09-26 (TK106): trimmed to its legal `non_labels` core,
#: it adds no feature or pair of its own. It is kept because it is the only corpus
#: asserted to reach `test_bulk_build.py`'s edge-free explicit rc=0 node (check (e)).
KNOWN_SUBSUMED = {'confluence', 'custom_roles', 'demorgans_law_1', 'gdrive', 'github',
                  'master_store'}

#: ★ A DIFFERENT THING FROM `KNOWN_SUBSUMED`, AND THE DISTINCTION IS LOAD-BEARING.
#: Groups of fixtures that score "subsumed" ONLY because they mask each other -- the
#: leave-one-out artifact `test_subsumption_register_is_current`'s own docstring names.
#: `KNOWN_SUBSUMED` means "retirement candidate". These are the opposite: retiring EITHER
#: member destroys the property the group exists for, and the register saying otherwise
#: would be an invitation to delete it.
#:
#: Added 2026-09-20g (`TK83`). Landing `star_admitting_intersection.fga` -- which is
#: `demorgans_law_2.fga` with one token changed -- made BOTH fixtures score subsumed at
#: once, because each is the other's cover. Measured the same day: each member is NOT
#: subsumed once the other is dropped, and dropping the two TOGETHER loses 6 co-occurring
#: pairs. Both of those are asserted by `test_masked_groups_are_really_masked` rather than
#: taken on trust, so a group cannot be parked here to silence a genuine subsumption.
#:
#: Each group names the test that makes retirement MECHANICALLY impossible -- a doc
#: warning is not a guard, and `CLAUDE.md` requires a cited symbol to exist.
#: `test_masked_groups_cite_a_live_guard` resolves the `file::symbol`.
MASKED_PAIRS = {
    frozenset({'demorgans_law_2', 'star_admitting_intersection'}):
        'tests/test_star_admitting_intersection.py::'
        'test_corpus_has_a_star_admitting_intersection_with_a_derived_dep',
}
_MASKED_MEMBERS = frozenset().union(*MASKED_PAIRS) if MASKED_PAIRS else frozenset()
#: OPEN QUESTION (board row P11, ~1/2 session) -- the fixture-TRIPLE question.
#: Pairwise scoring is what put these five here; a TRIPLE score is what would settle
#: keep-or-delete. Completion criterion: score feature TRIPLES over these five against
#: the rest of the corpus; if a listed fixture holds a unique triple it is NOT subsumed
#: and comes off this list, otherwise its retirement candidacy is confirmed and deletion
#: becomes a real option.
#: WARNING -- do NOT extend `test_corpus_pair_coverage_does_not_regress` or
#: `test_fga_corpus_feature_coverage_does_not_regress` to TRIPLE coverage corpus-wide.
#: The pair space is already this gate's cost centre and triples are cubic in features.
#: And cost is NOT the only reason -- corpus-wide triple coverage would redden on
#: exactly these five, and the tempting fix (adding them to an exemption list) is the
#: hand-maintained-list-beside-a-glob pattern that has ALREADY FAILED TWICE in this
#: tree. So scoping the triples to a subset to dodge the cost does not make this safe.
#: Score the five OFFLINE and pin only what the scoring actually settles.
#: (The board previously cited a `test_fixture_earns_its_place` for this trap; no such
#: test has ever existed -- corrected 2026-08-16.)


def test_subsumption_register_is_current():
    """Track which fixtures have become fully covered by others. Informational, but
    asserted so it cannot rot -- a register nothing checks is a register nobody trusts.

    ★ THIS IS DELIBERATELY NOT "every fixture must be unique". An earlier version of
    this file asserted per-fixture uniqueness and it was wrong twice over:

      * it reddened when ``wildcard_userset_cross`` legitimately re-covered features
        that two earlier fixtures had introduced -- punishing the corpus growth this
        file exists to encourage; and
      * leave-one-out uniqueness masks itself: two fixtures that jointly hold the only
        copy of a feature each see the other in their "others" set, so BOTH score zero
        and both look like dead weight.

    The bar that matters is corpus-level and is enforced by the two floors below --
    coverage must not go DOWN. Whether any individual fixture is redundant is a
    retirement question, and retirement is a judgement call with no urgency.
    """
    per = _corpus()
    all_pairs = {k: _pairs(v) for k, v in per.items()}

    subsumed = set()
    for name in per:
        other_f = set().union(*(v for k, v in per.items() if k != name))
        other_p = set().union(*(v for k, v in all_pairs.items() if k != name))
        if not (per[name] - other_f) and not (all_pairs[name] - other_p):
            subsumed.add(name)

    newly = subsumed - KNOWN_SUBSUMED - _MASKED_MEMBERS
    assert not newly, (
        f'{sorted(newly)} became fully covered by other fixtures. Nothing is broken '
        f'and nothing must be deleted -- add them to KNOWN_SUBSUMED. They are now '
        f'retirement candidates, and if you DO retire one the corpus floors below will '
        f'tell you immediately whether it was really redundant.')

    resurrected = KNOWN_SUBSUMED - subsumed - _MASKED_MEMBERS
    assert not resurrected, (
        f'{sorted(resurrected)} is listed as subsumed but now contributes something no '
        f'other fixture does -- probably because a fixture that covered it was removed '
        f'or narrowed. Drop it from KNOWN_SUBSUMED so the register keeps meaning what '
        f'it says.')

    # Sabotage, literal observed output -- BOTH arms, because a two-sided assertion
    # where only one side has ever fired is half-tested:
    #   copy confluence.fga to zz_dupe.fga ->
    #     E AssertionError: ['zz_dupe'] became fully covered by other fixtures. ...
    #   add 'wildcards' to KNOWN_SUBSUMED ->
    #     E AssertionError: ['wildcards'] is listed as subsumed but now contributes
    #       something no other fixture does ...


def test_masked_groups_are_really_masked():
    """`MASKED_PAIRS` is an EXEMPTION from the register above, so it needs a bar of its
    own -- otherwise it is a list you park a fixture on to make a red go away, which is
    the hand-maintained-list-beside-a-glob pattern this file has already been bitten by
    twice.

    Three things are asserted per group, and each refuses a different abuse:

      1. every member really does score subsumed today -- a group listed here that is NOT
         subsumed is stale, and hiding it from the `resurrected` arm loses a real signal;
      2. no member is subsumed once the REST OF ITS GROUP is dropped -- that is the
         definition of mutual masking, and it is what distinguishes these from
         `KNOWN_SUBSUMED`, where dropping all five at once still loses nothing;
      3. dropping the whole group loses at least one feature or pair -- so the group is
         not collectively dead weight, which masking alone would not rule out.

    Measured 2026-09-20g for the one group: (1) both subsumed, (2) neither subsumed with
    the other dropped, (3) 0 features and **6** pairs lost.
    """
    per = _corpus()
    all_pairs = {k: _pairs(v) for k, v in per.items()}

    def _is_subsumed(name, universe):
        others = [k for k in universe if k != name]
        assert others, f'{name}: nothing to score against'
        of = set().union(*(per[k] for k in others))
        op = set().union(*(all_pairs[k] for k in others))
        return not (per[name] - of) and not (all_pairs[name] - op)

    for group, guard in MASKED_PAIRS.items():
        missing = group - set(per)
        assert not missing, (
            f'MASKED_PAIRS names {sorted(missing)}, which is not in the corpus. A group '
            f'whose members were deleted is not an exemption, it is a stale list.')
        assert len(group) >= 2, f'{sorted(group)}: a masked group needs >= 2 members'

        for name in group:
            assert _is_subsumed(name, list(per)), (
                f'{name} is NOT subsumed by the rest of the corpus, so it does not need '
                f'this exemption. Drop it from MASKED_PAIRS -- while it is listed, the '
                f'register cannot report it and a real change goes unseen.')
            solo = [k for k in per if k not in group or k == name]
            assert not _is_subsumed(name, solo), (
                f'{name} is still subsumed with the rest of {sorted(group)} dropped, so '
                f'its subsumption is NOT a masking artifact -- some third fixture covers '
                f'it. It belongs in KNOWN_SUBSUMED as a genuine retirement candidate.')

        rest = [k for k in per if k not in group]
        lost_f = set().union(*(per[k] for k in group)) - set().union(*(per[k] for k in rest))
        lost_p = (set().union(*(all_pairs[k] for k in group))
                  - set().union(*(all_pairs[k] for k in rest)))
        assert lost_f or lost_p, (
            f'dropping all of {sorted(group)} loses 0 features and 0 pairs, so the group '
            f'is collectively redundant in this vocabulary. Masking is not enough to earn '
            f'the exemption -- either these belong in KNOWN_SUBSUMED, or the property '
            f'they carry is invisible here and {guard} is the only thing holding them.')


def test_masked_groups_cite_a_live_guard():
    """★ The exemption is only safe because something ELSE refuses the deletion.

    A `MASKED_PAIRS` entry says "not a retirement candidate" and then points at the test
    that enforces it. `CLAUDE.md` has a standing trap about this: the board carried a
    "do not extend `test_fixture_earns_its_place`" warning for weeks against a test that
    has never existed. A guard cited by a name that does not resolve is worse than no
    guard, because it reads like one.

    Resolved the cheap, mechanical way -- the file exists and defines the symbol.
    """
    root = Path(__file__).resolve().parents[1]
    for group, guard in MASKED_PAIRS.items():
        rel, _, symbol = guard.partition('::')
        assert symbol, f'{sorted(group)}: guard {guard!r} names no ::symbol'
        path = root / rel
        assert path.exists(), (
            f'{sorted(group)} cites {rel}, which does not exist. Restore the guard or '
            f'move the group to KNOWN_SUBSUMED -- an unenforceable exemption is how a '
            f'fixture gets deleted with everything green.')
        src = path.read_text(encoding='utf-8')
        assert f'def {symbol}(' in src, (
            f'{sorted(group)} cites {guard}, but {rel} defines no such function. '
            f'Renaming a guard without updating its citation retires it silently.')

    # Sabotage, literal observed output (2026-09-20g) -- BOTH arms, because a guard check
    # that has only ever passed is itself unverified:
    #   point the entry at a nonexistent module ->
    #     E AssertionError: ['demorgans_law_2', 'star_admitting_intersection'] cites
    #       tests/test_no_such_module.py, which does not exist. ...
    #   rename the cited symbol (append 'X') ->
    #     E AssertionError: ['demorgans_law_2', 'star_admitting_intersection'] cites
    #       tests/test_star_admitting_intersection.py::test_corpus_has_a_star_admitting_intersection_with_a_derived_depX,
    #       but tests/test_star_admitting_intersection.py defines no such function. ...


# --------------------------------------------------------------------------- #
# The bar. Both floors use >=, so ADDING coverage is always free and only LOSING
# it is loud -- the same discipline as verify.sh's counts.
# --------------------------------------------------------------------------- #

#: Co-occurring feature pairs across the corpus, measured 2026-08-11. This is the
#: INTERACTION bar: pairs that appear together in at least one fixture. Raising it is
#: free; a drop means a fixture was removed or narrowed.
#: History: 778 before wildcard_userset_cross.fga, 839 after. LOWERED to 813 on
#: 2026-09-26, deliberately: ASK-1 made an undeclared tupleset a parse refusal, so
#: `tupleset_shapes.fga` lost `via_undeclared`. MEASURED that day: the old fixture (fed
#: to `genswarm.features` with the refusal switched off) gives 839 and the new one 813;
#: all 26 lost pairs contain `ttu.ts:undeclared`, which is now unreachable by design
#: (EXPECTED_UNREACHED), and no other pair moved.
#: LOWERED to 597 on 2026-09-26, deliberately: TK106 (user decision) made every non-direct
#: tupleset a parse refusal, retiring `tupleset_shapes.fga` and trimming
#: `demorgans_law_1.fga` to its legal `non_labels` core. MEASURED that day
#: (`.scratch/tk106/probe_corpus_now.py`: HEAD's two fixture texts fed to
#: `genswarm.features` with the refusal patched off): 813 -> 591, 222 pairs lost, 218 of
#: them containing a now-unreachable feature. The other 4 are LEGAL and were lost on
#: purpose: `ast:Intersection` / `plan:PIntersection` x `schema:storage-leaf` /
#: `ttu.ts:multitype`. Adding `cleared: [user] and viewer` to
#: `heterogeneous_tupleset.fga` recovers them (597), but MEASURED it also covers the 6
#: pairs the `demorgans_law_2` / `star_admitting_intersection` group holds uniquely,
#: dissolving that MASKED_PAIRS exemption and making `demorgans_reverse` subsumed too.
#: Four pairs do not justify that, and all four stay covered where interactions are
#: generated: each is a cell of the genswarm enumerator at K<=2 (MEASURED,
#: `.scratch/tk106/probe_4cells.py`, all True).
MIN_COOCCURRING_PAIRS = 591


def test_corpus_pair_coverage_does_not_regress():
    """Bar-raising floor on INTERACTIONS, not features.

    Feature coverage alone is the weaker measure -- this project's position is that
    every bug it has found is an interaction bug, and genswarm's cell space is pairwise
    for that reason. A corpus can reach every feature and still never cross any two.
    """
    per = _corpus()
    assert per, 'no .fga fixtures found -- this floor would pass vacuously'
    co = set().union(*(_pairs(v) for v in per.values()))
    assert len(co) >= MIN_COOCCURRING_PAIRS, (
        f'corpus co-occurring pairs fell to {len(co)}, below the {MIN_COOCCURRING_PAIRS} '
        f'floor measured 2026-08-11. A fixture was removed or narrowed. Never lower this '
        f'to go green -- re-derive why the interaction is no longer worth covering.')


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


# (`test_tupleset_shapes_answers` was RETIRED with its fixture on 2026-09-26, TK106: its
# three queries ran through `approved_parent: [folder] and vetted` and RC1's
# `mixed_parent: [folder] but not [doc]`, both now parse refusals.)


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
    # tupleset-wildcard-userset-restriction.
    'ttu.ts.restr:userset',
    'ttu.ts.restr:wildcard-userset',
    # ⚠ NOT refused: a union of Directs (`[a] or [b]`) is a LEGAL tupleset, before and
    # after TK106. No fixture happens to carry one (genswarm reaches it through
    # `ts_boolean`), and it is listed so the exact-set assertion below holds; a fixture
    # adopting the form is the "Good news" branch. The old comment called it "refused by
    # scope" on the strength of `tupleset-rewritten-arms`, which is a COMPUTED arm.
    'ttu.ts:Union',
    # Reachable in some configurations but refused in the common ones; witnesses:
    # owc-on-a-ttu-tupleset, owc-on-derived-relation. Same parameter caveat as above.
    'ttu.ts:owc',
    # Refused at PARSE time since ASK-1 (2026-09-26, user decision: schemas must be
    # self-consistent); witness: dangling-reference. `tupleset_shapes.fga` carried it
    # until then as `via_undeclared`.
    'ttu.ts:undeclared',
    # Refused at PARSE time since TK106 (2026-09-26, user decision: a tupleset must be
    # direct-only). The tupleset-body shapes and their compiled consequences, which only
    # a tainted tupleset produced. Witnesses: tupleset-intersection,
    # tupleset-neg-only-type, tupleset-rewritten-arms, tupleset-is-itself-a-ttu.
    # `tupleset_shapes.fga` and `demorgans_law_1.fga` carried them until then.
    'ttu.ts:Computed',
    'ttu.ts:Exclusion',
    'ttu.ts:Intersection',
    'ttu.ts:TTU',
    'ttu.ts:neg-only-type',
    'ttu.ts:tainted',
    'plan:PDerivedTuplesetTTU',
    'leaf:derived-tupleset-ttu',
    'via:tupleset-ttu',
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


@pytest.mark.parametrize('query,expected', [
    # a plain group userset reaching a folder that is a TTU parent
    (('...', 'user', 'alice', 'reader', 'doc', 'd1'), True),
    # ★ userset over a DERIVED relation (team#active_lead), consumed through `or owner`
    # and then through the TTU -- bob is a lead and not blocked
    (('...', 'user', 'bob', 'reader', 'doc', 'd1'), True),
    # ... and the exclusion still bites two hops away: carol is a blocked lead
    (('...', 'user', 'carol', 'reader', 'doc', 'd1'), False),
    # ★ THE WILDCARD USERSET: `group:*#member` grants to anyone who is a member of ANY
    # group. alice is a member of g1.
    (('...', 'user', 'alice', 'reader', 'doc', 'd2'), True),
    # zoe belongs to no group EXPLICITLY, but g2 carries (user:*, member, group:g2), so
    # she is a member of a group and the wildcard userset reaches her. This is the cell
    # the corpus never had: a subject wildcard feeding a wildcard userset feeding a TTU.
    (('...', 'user', 'zoe', 'reader', 'doc', 'd2'), True),
    # NEGATED TTU over the same chain -- the fail-open direction
    (('...', 'user', 'alice', 'sealed', 'doc', 'd1'), False),
    (('...', 'user', 'dave', 'sealed', 'doc', 'd1'), True),
])
def test_wildcard_userset_cross_answers(driven, query, expected):
    assert driven['wildcard_userset_cross'].check(*query) is expected
