"""
P1 boolean golden tests for the pointwise oracle (spec §3).

Every expected boolean is computed BY HAND in the comments (a human reading the
schema + tuples), never by an implementation. Covers De Morgan scenarios over the
`demorgans_law_2.fga` fixture, intersection, and the star × exclusion corners from
the §3 semantics table (including star-inside-exclusion, spec §7.2).
"""

from tests.oracle import Oracle, OracleTuple, t


# ---------------------------------------------------------------------------
# 1. De Morgan fixture: missing_user = _all_users but not has_attr
# ---------------------------------------------------------------------------

def test_demorgans_law_2_missing_user(load_fga_schema):
    schema = load_fga_schema('demorgans_law_2.fga')
    # a1's _all_users is turned on (every user), and alice has the attribute.
    tuples = [
        t('...', 'user', '*', '_all_users', 'attr', 'a1'),      # _all_users := everyone
        t('...', 'user', 'alice', 'has_attr', 'attr', 'a1'),    # alice has_attr
    ]
    o = Oracle(schema, tuples)

    # missing_user = _all_users but not has_attr.
    #   bob: in _all_users (bare-star) AND not has_attr -> True
    assert o.check('...', 'user', 'bob', 'missing_user', 'attr', 'a1') is True
    #   ghost: same as any concrete non-alice user -> True
    assert o.check('...', 'user', 'ghost', 'missing_user', 'attr', 'a1') is True
    #   alice: in _all_users AND in has_attr -> base ∧ ¬sub = True ∧ ¬True = False
    assert o.check('...', 'user', 'alice', 'missing_user', 'attr', 'a1') is False
    #   '*' query: star-covered in _all_users (a bare-star tuple exists) and NOT
    #   star-covered in has_attr (only concrete alice) -> True (§3 table)
    assert o.check('...', 'user', '*', 'missing_user', 'attr', 'a1') is True


def test_demorgans_law_2_missing_user_no_all_users(load_fga_schema):
    schema = load_fga_schema('demorgans_law_2.fga')
    # _all_users is NOT turned on for a2; alice merely has_attr.
    tuples = [t('...', 'user', 'alice', 'has_attr', 'attr', 'a2')]
    o = Oracle(schema, tuples)
    # base (_all_users) is empty, so missing_user is empty for everyone.
    assert o.check('...', 'user', 'bob', 'missing_user', 'attr', 'a2') is False
    assert o.check('...', 'user', 'alice', 'missing_user', 'attr', 'a2') is False
    assert o.check('...', 'user', '*', 'missing_user', 'attr', 'a2') is False


# ---------------------------------------------------------------------------
# 2. Star inside exclusion: [user:*] but not blocked  (spec §7.2)
# ---------------------------------------------------------------------------

STAR_EXCLUSION_SCHEMA = '''
type user
type doc
  relations
    define blocked: [user]
    define access: [user:*] but not blocked
'''


def test_star_inside_exclusion():
    o = Oracle(STAR_EXCLUSION_SCHEMA, [
        t('...', 'user', '*', 'access', 'doc', 'd'),        # public access (base = [user:*])
        t('...', 'user', 'alice', 'blocked', 'doc', 'd'),   # ...except alice
    ])
    # ghost user: star-covered by base, not blocked -> True
    assert o.check('...', 'user', 'ghost', 'access', 'doc', 'd') is True
    # blocked alice: star-covered by base but subtracted -> False
    assert o.check('...', 'user', 'alice', 'access', 'doc', 'd') is False
    # '*' query: star-covered in base, NOT star-covered in blocked (concrete only) -> True
    assert o.check('...', 'user', '*', 'access', 'doc', 'd') is True


def test_exclusion_of_star_empties_concretes():
    # `[user] but not [user:*]`: subtrahend is a star, so every concrete is subtracted.
    schema = '''
    type user
    type doc
      relations
        define x: [user] but not [user:*]
    '''
    o = Oracle(schema, [
        t('...', 'user', 'alice', 'x', 'doc', 'd'),
        t('...', 'user', '*', 'x', 'doc', 'd'),
    ])
    # alice: base True (direct [user]), but [user:*] star covers her -> subtracted -> False
    assert o.check('...', 'user', 'alice', 'x', 'doc', 'd') is False
    # '*' query: base ([user]) has no star tuple -> not star-covered in base -> False
    assert o.check('...', 'user', '*', 'x', 'doc', 'd') is False


# ---------------------------------------------------------------------------
# 3. Intersection
# ---------------------------------------------------------------------------

INTERSECTION_SCHEMA = '''
type user
type doc
  relations
    define a: [user, user:*]
    define b: [user, user:*]
    define both: a and b
'''


def test_intersection_membership():
    o = Oracle(INTERSECTION_SCHEMA, [
        t('...', 'user', 'alice', 'a', 'doc', 'd'),
        t('...', 'user', 'alice', 'b', 'doc', 'd'),
        t('...', 'user', 'bob', 'a', 'doc', 'd'),      # bob only in a
    ])
    assert o.check('...', 'user', 'alice', 'both', 'doc', 'd') is True    # in a AND b
    assert o.check('...', 'user', 'bob', 'both', 'doc', 'd') is False     # a only
    assert o.check('...', 'user', 'carol', 'both', 'doc', 'd') is False   # neither


def test_intersection_with_empty_branch():
    # d2 has an `a` grant but no `b` grant -> intersection empty (spec §7.2).
    o = Oracle(INTERSECTION_SCHEMA, [t('...', 'user', 'alice', 'a', 'doc', 'd2')])
    assert o.check('...', 'user', 'alice', 'both', 'doc', 'd2') is False


def test_intersection_star_covered_in_both():
    # '*' ∈ A∧B iff star-covered in both branches (§3 table).
    o = Oracle(INTERSECTION_SCHEMA, [
        t('...', 'user', '*', 'a', 'doc', 'd'),
        t('...', 'user', '*', 'b', 'doc', 'd'),
    ])
    assert o.check('...', 'user', '*', 'both', 'doc', 'd') is True
    # Only one branch has the star -> not covered in both.
    o2 = Oracle(INTERSECTION_SCHEMA, [
        t('...', 'user', '*', 'a', 'doc', 'd'),
        t('...', 'user', 'alice', 'b', 'doc', 'd'),
    ])
    assert o2.check('...', 'user', '*', 'both', 'doc', 'd') is False
    # ...but concrete alice is in a (via star) and b (direct) -> True
    assert o2.check('...', 'user', 'alice', 'both', 'doc', 'd') is True
