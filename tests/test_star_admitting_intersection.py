"""The star-admitting intersection with a derived dep -- `TK83`.

Until 2026-09-20g **no fixture in the tree had one**, and that is the whole reason this
module exists. `docs/tk74-staleness-net-2026-09-18.md` §9.5 recorded that a half-stale
intersection writes **no residue at all** and that "the divergence is carried entirely in
materialized closure edges". That was true of the fixture it was measured on and false in
general: §9.5's own caveat flagged the STARRED case as *untested, not tested-and-clean*,
and §10.5 refuted it -- on `.scratch/tk74d-starisect/star_isect.fga`, a **gitignored** file.
So the shape that breaks §9.5 existed only somewhere the repo's own rule calls already lost.

`tests/fga_schemas/star_admitting_intersection.fga` is that file, in the tree. It is
`demorgans_law_2.fga` with **one token changed** (`define assigned: [user]` ->
`[user, user:*]`), which is what makes the intersection star-admitting and the half-stale
case reachable at all. The two fixtures are kept as a PAIR and neither is retirable --
see `tests/test_schema_shapes.py::MASKED_PAIRS`, which cites this module by name.

★ WHAT THIS MODULE DOES AND DOES NOT CLAIM. It pins **reachability** and the **residue
channel**: the shape exists in the corpus, and the intersection really does write a starred
residue that its one-token twin does not. It does NOT re-run §10.5's 144 fault-injection
arms and says nothing about what the settle pass or the paranoia tiers catch under a
skipped reconcile -- that remains `TK74`'s assurance gap, untouched. Putting the fixture in
the tree does not close that gap; it makes the gap's subject reachable by `pytest`.

★ WHY A STRUCTURAL GUARD AND NOT A COVERAGE FLOOR. `tests/test_schema_shapes.py` scores the
corpus in `genswarm`'s pairwise feature vocabulary, and **that vocabulary cannot see this
fixture at all**: measured 2026-09-20g, the symmetric feature difference between
`star_admitting_intersection` and `demorgans_law_2` is the **empty set**. Adding a star to
one restriction list moves no genswarm feature. So the corpus floors would stay green with
this fixture deleted, and `test_corpus_has_a_star_admitting_intersection_with_a_derived_dep`
below is the only thing that would go red. That test is the retirement guard.

The one-token control is load-bearing and is asserted, not assumed: every residue claim
below is stated as a DIFFERENCE against `demorgans_law_2.fga` under the identical workload.
A claim of the form "the starred fixture writes stars" is unfalsifiable on its own -- the
in-tree twin writing none at the same key is what makes it evidence.

Probe and verbatim output: `formal/probes/tk83_star_intersection_2026-09-20.py`.

---------------------------------------------------------------------------------------
MUTATION SWEEP (`docs/sabotage-procedure.md` §"Sweep the TEST MODULE with mutations").
See the table at the bottom of this file -- it is evidence and it lives where the next
reader already is.
"""
import json
from itertools import combinations
from pathlib import Path

import pytest
from sqlmodel import select

from index_v4.models import NodeV4, ResidueV1
from tests.parity import ParityEngine
from zanzibar_utils_v1 import (
    Computed, Direct, Exclusion, Intersection, PIntersection, TTU, Union,
    parse_openfga_schema, parse_schema_ast,
)

_FGA_DIR = Path(__file__).parent / 'fga_schemas'

#: The fixture this module exists for, and its one-token twin.
STARRED = 'star_admitting_intersection'
CONTROL = 'demorgans_law_2'

#: The intersection key and its derived dep, measured 2026-09-20g. Pinned rather than
#: rediscovered so a schema edit that moves the intersection is loud.
ISECT_KEY = ('role', 'authorized_user')
ISECT_DEP = ('role', 'role_user_met')
ISECT_OBJECT = 'r3'
#: One relation further downstream -- §10.5's propagation target.
DOWNSTREAM = ('doc', 'access', 'd2')


def _load(stem: str) -> str:
    return (_FGA_DIR / f'{stem}.fga').read_text(encoding='utf-8')


# --------------------------------------------------------------------------- #
# The structural census -- shared with formal/probes/tk83_star_intersection_2026-09-20.py
# --------------------------------------------------------------------------- #

class _TtuChild(Exception):
    """A TTU child would make the star column an UNDER-count, not a measurement."""


def _star_admitting(expr, otype, ast, tainted, seen=()):
    """True iff this LEAF child of an intersection admits a ``T:*`` subject.

    "Leaf child" is the compiler's own unit: ``PClosureLeaf`` is the maximal boolean-free,
    derived-free subtree, so a ``Computed`` reference to an UNTAINTED relation is inlined
    and its restrictions count, while a ``Computed`` to a tainted one is a derived dep and
    stops the walk.

    ★ That distinction IS the measurement, and getting it wrong is the easy mistake.
    Stars DO reach `demorgans_law_2`'s intersection through its derived dep -- and it
    still writes no residue, because ``stars ∩ no-stars = ∅``. A walker that followed the
    dep would report True for the control, and the whole census would then say "every
    intersection is star-admitting", which is a green that means nothing.
    """
    if isinstance(expr, Direct):
        return any(r.wildcard for r in expr.restrictions)
    if isinstance(expr, Computed):
        key = (otype, expr.relation)
        if key in tainted or key in seen or key not in ast:
            return False
        return _star_admitting(ast[key], otype, ast, tainted, seen + (key,))
    if isinstance(expr, (Union, Intersection)):
        return any(_star_admitting(c, otype, ast, tainted, seen) for c in expr.children)
    if isinstance(expr, Exclusion):
        return (_star_admitting(expr.base, otype, ast, tainted, seen)
                or _star_admitting(expr.subtract, otype, ast, tainted, seen))
    if isinstance(expr, TTU):
        # Not reachable in today's corpus and asserted so below. Raising beats returning
        # False: a silent False would turn an under-count into a measurement.
        raise _TtuChild(f'{otype}: TTU child {expr!r} -- the star column is not total')
    return False


def intersection_census():
    """``[(stem, key, stratum, deps, star_admitting)]`` over every ``.fga`` in the corpus."""
    rows = []
    for path in sorted(_FGA_DIR.glob('*.fga')):
        text = path.read_text(encoding='utf-8')
        ruleset = parse_openfga_schema(text)
        if ruleset.compiled is None:
            continue
        ast = parse_schema_ast(text)
        for key, plan in sorted(ruleset.compiled.plans.items()):
            if not isinstance(plan.tree, PIntersection):
                continue
            expr = ast[key]
            children = expr.children if isinstance(expr, Intersection) else ()
            starred = any(_star_admitting(c, key[0], ast, ruleset.compiled.tainted)
                          for c in children)
            rows.append((path.stem, key, plan.stratum, plan.deps, starred))
    return rows


# --------------------------------------------------------------------------- #
# The driven engines. Module-scoped: ParityEngine runs paranoia (invariant checker +
# delta-scoped verifier) inside every commit and re-runs the whole query grid against a
# freshly rebuilt oracle after every write, so one engine per test costs minutes.
# The reads below are read-only, so sharing is safe.
# --------------------------------------------------------------------------- #

#: Shape-identical on both fixtures. `role:r3 assigned user:*` is the ONLY tuple the
#: control cannot take -- its `assigned` is `[user]` -- and that refusal is itself pinned.
_WORKLOAD = [
    ('...', 'user', 'alice', 'has_attr', 'attr', 'at1'),
    ('...', 'attr', 'at1', 'requires', 'cond', 'c1'),
    ('...', 'user', '*', '_all_users', 'cond', 'c1'),
    ('...', 'cond', 'c1', 'match_any', 'role', ISECT_OBJECT),
    ('...', 'role', ISECT_OBJECT, 'associated_role', 'doc', 'd2'),
]
_STAR_GRANT = ('...', 'user', '*', 'assigned', 'role', ISECT_OBJECT)
_CONCRETE_GRANT = ('...', 'user', 'alice', 'assigned', 'role', ISECT_OBJECT)


def _residue_rows(eng) -> dict[tuple[str, str, str], dict]:
    """Every ``ResidueV1`` row, joined to ``NodeV4``.

    Joined and complete, never a guessed subset: §9.5's G5 hypothesis was killed by
    dumping ALL rows, and a dump filtered to the key you expect can only confirm you.
    """
    session = eng.graph.widx.idx.session
    out = {}
    for res, node in session.exec(
            select(ResidueV1, NodeV4)
            .where(ResidueV1.object_node_id == NodeV4.id)
            .where(ResidueV1.store_id == eng.graph.widx.idx.store_id)).all():
        out[(node.type, res.relation, node.name)] = {
            'stars': json.loads(res.stars),
            'neg': json.loads(res.neg),
            'upos': json.loads(res.upos),
        }
    return out


@pytest.fixture(scope='module')
def driven():
    """``{stem: (engine, residue_rows, star_grant_taken)}`` for the pair."""
    engines, built = [], {}
    try:
        for stem in (STARRED, CONTROL):
            eng = ParityEngine(_load(stem))
            engines.append(eng)
            # ★ THE CONTROL THAT MATTERS. ParityEngine degrades to 3-way when the graph
            # refuses a schema and then reports green having never run the index. Every
            # residue read below would be against a store the graph never wrote.
            assert eng.graph is not None, (
                f'{stem}.fga did not join the graph index: {eng.graph_drop_reason}. '
                f'This module compares the graph against the other backends; a 3-way '
                f'run here passes while testing nothing it was added for.')
            for raw in _WORKLOAD:
                assert eng.add_tuple(*raw), f'{stem}: refused {raw}'
            star_taken = bool(eng.add_tuple(*_STAR_GRANT))
            assert eng.add_tuple(*_CONCRETE_GRANT), f'{stem}: refused {_CONCRETE_GRANT}'
            built[stem] = (eng, _residue_rows(eng), star_taken)
        yield built
    finally:
        for eng in engines:
            eng.close()


# --------------------------------------------------------------------------- #
# The pins. One per claim -- a module that guards N cases must assert on all N.
# --------------------------------------------------------------------------- #

def test_the_census_reproduces_the_known_intersections():
    """ANTI-VACUITY for every census-based test below.

    A walker that found nothing would make
    `test_corpus_has_a_star_admitting_intersection_with_a_derived_dep` fail loudly, but it
    would make the *uniqueness* half of it pass silently. Pin the three intersections
    `docs/tk74-staleness-net-2026-09-18.md` §10.5 measured, star column included, so a
    broken walker cannot masquerade as a finding.
    """
    got = {(stem, key): starred for stem, key, _, _, starred in intersection_census()}
    for expected_key, expected_star in {
            (CONTROL, ISECT_KEY): False,
            ('boolean_wildcards', ('doc', 'restricted')): True,
            ('tupleset_shapes', ('doc', 'approved_parent')): False}.items():
        assert expected_key in got, (
            f'the census lost {expected_key}, measured by §10.5 on 2026-09-18c. The '
            f'walker is broken or a fixture changed; nothing else here is evidence.')
        assert got[expected_key] == expected_star, (
            f'{expected_key} star column is {got[expected_key]}, §10.5 measured '
            f'{expected_star}. Reconcile before reading the new fixture.')


def test_corpus_has_a_star_admitting_intersection_with_a_derived_dep():
    """★ THE RETIREMENT GUARD, cited by `test_schema_shapes.py::MASKED_PAIRS`.

    `docs/tk74-staleness-net-2026-09-18.md` §10.5 measured this count as **0** across all
    15 fixtures: no `PIntersection` had BOTH a non-empty `Plan.deps` and a star-admitting
    leaf child, which is exactly why §9.5's "the residue channel is clean" survived as long
    as it did. Deleting `star_admitting_intersection.fga` puts it back to 0, and **no
    corpus floor would notice** -- the fixture contributes no genswarm feature its twin
    does not (measured 2026-09-20g). This assertion is the only thing that reds.
    """
    hits = [(stem, key) for stem, key, _, deps, starred in intersection_census()
            if deps and starred]
    assert hits, (
        'no fixture has an intersection with BOTH a non-empty derived dep and a '
        'star-admitting leaf child. That is the state §10.5 measured on 2026-09-18c, '
        'and tk74-staleness-net §9.5 recorded a FALSE general claim from it. If '
        'star_admitting_intersection.fga was deleted or narrowed, restore it; the '
        'corpus feature floors cannot see this shape and will stay green without it.')
    assert (STARRED, ISECT_KEY) in hits, (
        f'{STARRED}.fga no longer carries the shape it was added for; hits={hits}')


def test_the_starred_intersection_sits_where_it_was_measured():
    """The stratum and dep, pinned. A schema edit that moves the intersection to stratum 0
    (or drops its dep) leaves a fixture that still *has* a star and no longer has the
    interaction -- which is `boolean_wildcards.fga`, a fixture that already exists.
    """
    rows = {(stem, key): (stratum, deps)
            for stem, key, stratum, deps, _ in intersection_census()}
    stratum, deps = rows[(STARRED, ISECT_KEY)]
    assert deps == (ISECT_DEP,), f'deps moved to {deps}, measured {(ISECT_DEP,)} 2026-09-20g'
    assert stratum == 4, f'stratum moved to {stratum}, measured 4 on 2026-09-20g'
    # The twin must still sit in the SAME place, or the pair is no longer one token apart
    # and every difference below stops being attributable to the star.
    assert rows[(CONTROL, ISECT_KEY)] == (stratum, deps), (
        f'{CONTROL} and {STARRED} no longer share stratum/deps: '
        f'{rows[(CONTROL, ISECT_KEY)]} vs {(stratum, deps)}')


def test_the_two_fixtures_differ_by_exactly_the_star():
    """The pair is only evidence while it is a ONE-TOKEN difference.

    If someone edits either schema, every residue difference below silently stops being
    attributable to the star -- and the tests keep passing, because they assert a
    difference and would still find one. This is the arm that refuses that.
    """
    a = _load(CONTROL).replace('\r\n', '\n').splitlines()
    b = _load(STARRED).replace('\r\n', '\n').splitlines()
    assert len(a) == len(b), f'the fixtures differ in line count: {len(a)} vs {len(b)}'
    diff = [(i, x, y) for i, (x, y) in enumerate(zip(a, b), 1) if x != y]
    assert diff == [(21, '    define assigned: [user]',
                     '    define assigned: [user, user:*]')], (
        f'the pair is no longer one token apart: {diff}')


def test_the_control_refuses_the_star_grant(driven):
    """ANTI-VACUITY for the residue comparison: the workloads are not identical, and the
    ONE way they differ is the thing under test. `assigned: [user]` admits no wildcard, so
    the control cannot even store the grant. If this ever passed on both sides the
    comparison would be measuring two different workloads, not two different schemas.
    """
    assert driven[STARRED][2] is True, f'{STARRED} refused the star grant {_STAR_GRANT}'
    assert driven[CONTROL][2] is False, (
        f'{CONTROL} ACCEPTED {_STAR_GRANT}; its `assigned` must be `[user]`, so either '
        f'the fixture changed or admission stopped enforcing the restriction list')


def test_the_starred_intersection_writes_a_starred_residue(driven):
    """★ THE §9.5 REFUTATION, as a positive pin.

    §9.5: "a half-stale intersection ... writes **none** [no residue]. ... The divergence
    is carried entirely in materialized closure edges." §10.5 refuted it on a gitignored
    file; this is the same measurement from the tree. Stated as a difference against the
    one-token twin, because "the starred fixture writes stars" alone is unfalsifiable.
    """
    key = (ISECT_KEY[0], ISECT_KEY[1], ISECT_OBJECT)
    starred_rows, control_rows = driven[STARRED][1], driven[CONTROL][1]

    assert key in starred_rows, (
        f'{STARRED}: no residue row at {key} at all. §10.5 measured '
        f"stars=[['user', '...']] there on 2026-09-18c -- if this is empty the "
        f'intersection stopped writing a residue and §9.5 would be right again.')
    assert starred_rows[key]['stars'] == [['user', '...']], (
        f"{STARRED}: stars at {key} are {starred_rows[key]['stars']}, measured "
        f"[['user', '...']] on 2026-09-20g")
    assert key not in control_rows, (
        f'{CONTROL} now writes a residue row at {key} too: {control_rows.get(key)}. '
        f'The star is no longer what distinguishes the pair, so nothing above is '
        f'evidence about stars.')


def test_the_star_propagates_to_the_dependent_relation(driven):
    """§10.5 measured the loss propagating one relation further, to `('doc','access','d2')`.
    Pinned as a difference: present-and-starred on the starred fixture, present-and-EMPTY
    on the twin. Both fixtures have the row -- it is the `stars` column that moves, which
    is a sharper claim than "a row appears".
    """
    starred_rows, control_rows = driven[STARRED][1], driven[CONTROL][1]
    assert DOWNSTREAM in starred_rows and DOWNSTREAM in control_rows, (
        f'{DOWNSTREAM} missing from one side: '
        f'{DOWNSTREAM in starred_rows} / {DOWNSTREAM in control_rows}')
    assert starred_rows[DOWNSTREAM]['stars'] == [['user', '...']], (
        f"stars at {DOWNSTREAM} are {starred_rows[DOWNSTREAM]['stars']}, measured "
        f"[['user', '...']] on 2026-09-20g")
    assert control_rows[DOWNSTREAM]['stars'] == [], (
        f"{CONTROL} stars at {DOWNSTREAM} are {control_rows[DOWNSTREAM]['stars']}, "
        f'measured [] on 2026-09-20g -- the propagation is no longer star-specific')


#: Workload B -- the HALF-STARRED store. Same as `_WORKLOAD` minus the `_all_users` star on
#: `cond:c1`, which is what gives `('role','role_user_met')` its stars. The intersection then
#: has ONE starred child (`assigned`, via the wildcard grant) and one unstarred one.
_WORKLOAD_HALF = [t for t in _WORKLOAD if t[3] != '_all_users']


@pytest.fixture(scope='module')
def half_starred():
    eng = ParityEngine(_load(STARRED))
    try:
        assert eng.graph is not None, f'half_starred: {eng.graph_drop_reason}'
        for raw in _WORKLOAD_HALF:
            assert eng.add_tuple(*raw), f'half_starred: refused {raw}'
        assert eng.add_tuple(*_STAR_GRANT)
        yield eng, _residue_rows(eng)
    finally:
        eng.close()


def test_the_intersection_intersects_its_childrens_stars(half_starred):
    """★ THE FOLD ITSELF — added 2026-09-20g because the mutation sweep found this module
    BLIND to it, and the finding is worth more than the pin.

    `zanzibar_utils_v1.py::_compile_stars_fn`'s `PIntersection` branch folds children with
    `frozenset.__and__`, one line below the `PUnion` branch that folds with `__or__`. Two
    plausible edits — the copy-paste (`&` -> `|`) and the "short-circuit" (`fns[0](ctx)`) —
    were swept, and **neither moved a single assertion in this module** on the main
    workload. MEASURED, not reasoned: the sweep's WITH arm named only
    `tests/test_matrix.py::test_demorgan_oracle_equals_setengine_equals_graph`.

    The reason is the discipline `docs/sabotage-procedure.md` asks for — *say what the edit
    was supposed to move, and check that it moved*. On `_WORKLOAD` **both** children of the
    intersection carry `('user','...')`, so `&`, `|` and `first-child` all return the same
    set. The mutation changed the fold and changed nothing observable here.

    Workload B removes the `_all_users` star from `cond:c1`, which is the sole source of
    `('role','role_user_met')`'s stars. Now exactly one child is starred, and the three
    candidate folds separate:

        &            -> {}                  (the shipped behaviour, asserted below)
        |            -> {('user','...')}    (the copy-paste)
        fns[0](ctx)  -> {('user','...')}    (the short-circuit)

    An empty star set is not stored (`index_v4/models.py::ResidueV1`: "Empty residues are
    deleted, never stored"), so the shipped fold leaves the intersection with no residue row
    at all. MEASURED on workload B, 2026-09-20g: rows exist at
    `('cond','user_missing_requirement','c1')`, `('doc','access','d2')` and
    `('role','role_user_met','r3')` — all with `stars=[]` — and **none** at
    `('role','authorized_user','r3')`.

    ⚠ The first draft of this test asserted its ceiling against a leaf family's residue row
    and reddened immediately: a `PClosureLeaf`'s stars live in the materialised closure, not
    in `ResidueV1`, which only carries DERIVED relations. The control was mis-aimed, and it
    said so rather than passing — recorded because that is the ceiling working.
    """
    eng, rows = half_starred
    key = (ISECT_KEY[0], ISECT_KEY[1], ISECT_OBJECT)

    # CEILING, both halves. Without these, "the intersection has no stars" is indistinguishable
    # from "nothing in this store has any stars", which would hold for a fold that did nothing.
    #  (a) the STARRED child is genuinely starred, shown behaviourally: `bob` holds no
    #      concrete `assigned` tuple, so a True here can only come through `[user:*]`.
    assert eng.check('...', 'user', 'bob', 'assigned', 'role', ISECT_OBJECT) is True, (
        'the starred arm is not starred at this store, so there is no star to intersect '
        'away and the assertion below is vacuous')
    #  (b) the OTHER child is genuinely unstarred.
    assert rows[('role', 'role_user_met', ISECT_OBJECT)]['stars'] == [], (
        f"workload B was supposed to leave `role_user_met` unstarred; it carries "
        f"{rows[('role', 'role_user_met', ISECT_OBJECT)]['stars']}. Removing the "
        f'`_all_users` star from `cond:c1` no longer starves it, so the two children are '
        f'not actually differently-starred and this test measures nothing.')

    assert key not in rows or rows[key]['stars'] == [], (
        f"the intersection at {key} carries stars {rows.get(key, {}).get('stars')} on a "
        f'store where exactly one of its two children is starred. `&` cannot produce '
        f"that -- `_compile_stars_fn`'s PIntersection branch is folding with the wrong "
        f'operator (`|`) or dropping a child (`fns[0]`).')

    # And the ANSWER follows the fold, which is the part a residue dump cannot fake: under
    # `|` or `fns[0]` the intersection's residue would carry ('user','...') and `check`
    # would grant `bob` -- a fail-open -- through an arm he is not a member of.
    assert eng.check('...', 'user', 'bob', 'authorized_user', 'role', ISECT_OBJECT) is False


def test_the_star_changes_the_answer_end_to_end(driven):
    """The star is load-bearing, not decoration. `bob` is granted nothing anywhere; he
    reaches `doc:d2` only through `assigned: [user:*]`.

    Every `check` here is a `ParityEngine` check, so it is unanimous across the graph
    index, both `SetOps` set engines, and the oracle -- this is also the only place the
    new shape's ANSWERS get compared 4-way.
    """
    starred_eng, control_eng = driven[STARRED][0], driven[CONTROL][0]
    q = ('...', 'user', 'bob', 'access', 'doc', 'd2')
    assert starred_eng.check(*q) is True, 'the star stopped granting bob access'
    assert control_eng.check(*q) is False, (
        'the twin grants bob access without a star -- the fixtures are no longer '
        'distinguished by the wildcard')
    # The concretely-granted subject must agree on BOTH, or the difference above is not
    # isolated to the wildcard.
    alice = ('...', 'user', 'alice', 'access', 'doc', 'd2')
    assert starred_eng.check(*alice) is True and control_eng.check(*alice) is True


def test_the_corpus_has_no_ttu_intersection_child():
    """The star column is TOTAL only while no intersection has a TTU child -- `_star_admitting`
    raises on one rather than returning a quiet False. Asserted here so that if someone adds
    such a fixture the census fails on its own terms instead of under-counting.
    """
    intersection_census()   # raises _TtuChild if the assumption breaks


def test_the_pair_is_not_dead_weight_in_the_corpus_vocabulary():
    """Measured 2026-09-20g and pinned because it is counter-intuitive.

    Scored leave-one-out, BOTH fixtures come back "fully covered by other fixtures" --
    each is masked by its twin. Yet dropping the two TOGETHER loses **6** co-occurring
    feature pairs. So the pair is jointly load-bearing even in `genswarm`'s own vocabulary,
    which is the justification for `test_schema_shapes.py::MASKED_PAIRS` holding them out
    of the retirement register rather than listing them as retirement candidates.
    """
    from tests import genswarm
    per = {p.stem: genswarm.features(p.read_text(encoding='utf-8'))
           for p in sorted(_FGA_DIR.glob('*.fga'))}
    pairs = {k: {(a, b) for a, b in combinations(sorted(v), 2)} for k, v in per.items()}
    group = {STARRED, CONTROL}
    rest = [k for k in per if k not in group]
    lost = set().union(*(pairs[k] for k in group)) - set().union(*(pairs[k] for k in rest))
    assert len(lost) >= 6, (
        f'dropping {sorted(group)} together now loses only {len(lost)} co-occurring '
        f'pairs, measured 6 on 2026-09-20g. Raising this is free; a DROP means another '
        f'fixture absorbed the interaction and the pair-masking argument needs re-making.')


# --------------------------------------------------------------------------- #
# MUTATION SWEEP (docs/sabotage-procedure.md §"Sweep the TEST MODULE with mutations").
# The table is the evidence; the full write-up is
# docs/tk83-star-intersection-fixture-2026-09-20.md §7-§8.
#
# ★ THE QUESTION WAS NOT "does this module redden" BUT "does the FIXTURE earn its place".
# So every production mutation was run TWICE over the same target set -- WITH the new
# fixture, and WITHOUT it (`-k "not star_admitting"`, i.e. the corpus as it stood before
# 2026-09-20g). Target set: this module + test_matrix + test_reads + test_oracle_boolean
# + test_schema_shapes. MEASURED 2026-09-20g.
#
#   id  mutation                                     WITH            WITHOUT        verdict
#   --  -------------------------------------------  --------------  -------------  ----------------
#   M0  the fixture stops being star-admitting       6 failed        84 passed      control: OK,
#       (the CONTROL -- expected red named first)    (6 pins named)  (14 deselect)  attributed
#   P1  _compile_stars_fn PIntersection  & -> |      4 failed        2 failed       ALREADY COVERED
#   P2  _compile_stars_fn PIntersection  -> fns[0]   2 failed        84 passed      EARNS ITS PLACE
#
# P2 is the result. The "short-circuit" edit to the intersection star fold is invisible to
# the entire pre-existing corpus -- 84 passed, nothing red -- and reddens the moment the
# starred intersection is reachable. P1 is recorded as ALREADY COVERED rather than claimed:
# `test_matrix_4way_boolean` catches `&`->`|` on `boolean_wildcards.fga` without this
# fixture, and saying otherwise would be taking credit for someone else's pin.
#
# ⚠ THE SWEEP FOUND A HOLE IN THIS MODULE, and it is why
# `test_the_intersection_intersects_its_childrens_stars` exists. On the run above, the WITH
# arm for P1 and P2 named only `tests/test_matrix.py::test_demorgan_...` -- NOT one
# assertion here. `_WORKLOAD` leaves BOTH children of the intersection starred, so `&`, `|`
# and `fns[0]` all return the same set and the mutation moved nothing this module looks at.
# That is `P6` step 2's quiet failure exactly: an edit that does not move the property under
# test. Workload B (one child starred, one not) separates the three folds, and a re-sweep of
# the module ALONE then attributed all three mutations to the new pin:
#
#   M0  starve workload B's other arm (control)   RED  -> named the new pin      OK
#   P1  & -> |                                    RED  -> named the new pin (+4) OK
#   P2  -> fns[0]                                 RED  -> named the new pin      OK
#
# ⚠ INSTRUMENT LIMIT, recorded because it bounds what that table proves. Under P1/P2 the
# red arrives as an ERROR raised inside the `half_starred` / `driven` fixtures --
# `ParityEngine` asserts backend unanimity and full-grid oracle parity inside every
# `add_tuple`, so it detects the divergence while the store is still being built and this
# module's own assertions never execute. The pin is REACHED and correctly attributed, but
# what fires is the engine, not the assert. That is the shipped detector and the point of
# the item (the shape is now reachable by something that already checks equivalence) -- it
# is simply not evidence that these particular assertions are load-bearing.
# --------------------------------------------------------------------------- #
