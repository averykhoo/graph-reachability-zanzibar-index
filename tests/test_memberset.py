"""
P2 brute-force property suite for the star-closed algebra (spec §4).

Enumerate random ``MemberSet``s over a tiny universe (3 shapes, <=10 ids), materialize
each extensionally as a plain frozenset (star ⇒ whole population), and assert the
algebra is a homomorphism:

    materialize(op(a, b)) == op(materialize(a), materialize(b))   for union/intersect/subtract

plus ``contains_entity`` / ``contains_userset`` agreement with materialisation on known
ids, the intensional ``contains_star`` per op, and ghost-safety (coverage of ids never
in any population is decided by shape). Runs under EVERY ``SetOps`` implementation.
"""

import random

import pytest

from setengine.setops import ALL_SETOPS
from setengine import memberset as ms
from setengine.memberset import MemberSet


# --- tiny universe: each id belongs to exactly one shape's population ---
POP = {
    ('user', '...'): (0, 1, 2, 3, 4),      # bare user entities
    ('group', '...'): (5, 6, 7),           # bare group entities
    ('group', 'member'): (8, 9),           # group#member usersets
}
SHAPES = list(POP)
ALL_IDS = tuple(sorted(uid for ids in POP.values() for uid in ids))
ID_SHAPE = {uid: shape for shape, ids in POP.items() for uid in ids}
GHOSTS = {'user': 900, 'group': 901}       # ids in no population


def _pop(shape):
    return POP.get(shape, ())


def _random_memberset(rng, ops) -> MemberSet:
    pos = ops.freeze(uid for uid in ALL_IDS if rng.random() < 0.4)
    stars = frozenset(s for s in SHAPES if rng.random() < 0.5)
    neg = ops.freeze(uid for uid in ALL_IDS if rng.random() < 0.3)
    return MemberSet(pos, stars, neg)


def _materialize(m, ops):
    return ms.materialize(m, ops, _pop)


def _contains_known(m, uid) -> bool:
    typ, pred = ID_SHAPE[uid]
    if pred == '...':
        return m.contains_entity(uid, typ)
    return m.contains_userset(uid, (typ, pred))


def _assert_contains_matches_materialisation(m, ops):
    ext = _materialize(m, ops)
    for uid in ALL_IDS:
        assert _contains_known(m, uid) == (uid in ext), (uid, m)


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_memberset_algebra_homomorphism(ops):
    rng = random.Random(1234)
    for _ in range(3000):
        a = _random_memberset(rng, ops)
        b = _random_memberset(rng, ops)
        ma, mb = _materialize(a, ops), _materialize(b, ops)

        # contains agrees with materialisation on the operands themselves
        _assert_contains_matches_materialisation(a, ops)

        for op, ref, star_expected in (
            (ms.union, ma | mb, lambda s: (s in a.stars) or (s in b.stars)),
            (ms.intersect, ma & mb, lambda s: (s in a.stars) and (s in b.stars)),
            (ms.subtract, ma - mb, lambda s: (s in a.stars) and (s not in b.stars)),
        ):
            r = op(a, b, ops, _pop)
            assert _materialize(r, ops) == ref, (op.__name__, a, b)
            _assert_contains_matches_materialisation(r, ops)
            for s in SHAPES:
                assert r.contains_star(s) is bool(star_expected(s)), (op.__name__, s, a, b)


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_ghost_safety(ops):
    # A ghost entity (never in any population) is covered iff its bare star shape is
    # starred and it is not explicitly excluded -- decided by shape, not population.
    star_user = MemberSet(ops.freeze(), frozenset({('user', '...')}), ops.freeze())
    assert star_user.contains_entity(GHOSTS['user'], 'user') is True
    assert star_user.contains_entity(GHOSTS['group'], 'group') is False   # wrong type shape

    # ghost explicitly negated -> not covered
    neg_ghost = MemberSet(ops.freeze(), frozenset({('user', '...')}), ops.freeze((GHOSTS['user'],)))
    assert neg_ghost.contains_entity(GHOSTS['user'], 'user') is False

    # ghost in pos wins over neg
    pos_ghost = MemberSet(ops.freeze((GHOSTS['user'],)), frozenset({('user', '...')}),
                          ops.freeze((GHOSTS['user'],)))
    assert pos_ghost.contains_entity(GHOSTS['user'], 'user') is True


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_contains_star_is_intensional(ops):
    # contains_star reports shape membership, independent of whether the population is
    # empty -- the strict ∀⇒∃ marker survives even with zero concrete instances.
    m = MemberSet(ops.freeze(), frozenset({('group', 'member')}), ops.freeze())
    assert m.contains_star(('group', 'member')) is True
    assert m.contains_star(('user', '...')) is False
