"""
Declarative handwritten scenarios (spec §7.2) -- the human anchor of the validation
matrix. Every expected boolean is computed BY HAND with a justifying comment; each
scenario runs against the set engine (both SetOps) AND the oracle (see test_scenarios).

Scenario shape:
    {
      'name': str,
      'schema': str,                      # inline OpenFGA DSL
      'object_wildcard_shapes': set,      # optional
      'ops': [ (s_pred, s_type, s_name, relation, o_type, o_name), ... ],   # adds
      'expect': [ (s_pred, s_type, s_name, relation, o_type, o_name, bool), ... ],
    }
"""

E = '...'

SCENARIOS = [
    # -------------------------------------------------------------------
    # De Morgan pair with absolute values: missing_user = _all_users but not has_attr
    # -------------------------------------------------------------------
    {
        'name': 'demorgan_missing_user_absolute',
        'schema': '''
            type user
            type attr
              relations
                define _all_users: [user:*]
                define has_attr: [user]
                define missing_user: _all_users but not has_attr
        ''',
        'ops': [
            (E, 'user', '*', '_all_users', 'attr', 'a1'),     # everyone is in _all_users(a1)
            (E, 'user', 'alice', 'has_attr', 'attr', 'a1'),   # alice has the attribute
        ],
        'expect': [
            # bob: in _all_users (bare star), not has_attr -> missing
            (E, 'user', 'bob', 'missing_user', 'attr', 'a1', True),
            # ghost: same as any non-alice user
            (E, 'user', 'ghost', 'missing_user', 'attr', 'a1', True),
            # alice: in _all_users AND has_attr -> NOT missing
            (E, 'user', 'alice', 'missing_user', 'attr', 'a1', False),
            # '*': star-covered in _all_users, not star-covered in has_attr -> True
            (E, 'user', '*', 'missing_user', 'attr', 'a1', True),
            # no grants on a2 -> nobody missing
            (E, 'user', 'bob', 'missing_user', 'attr', 'a2', False),
        ],
    },

    # -------------------------------------------------------------------
    # (A and B) where the two branches are satisfied by DIFFERENT mechanisms:
    #   A = direct_ed (direct tuple);  B = inherited_ed (via `from parent` chain)
    # -------------------------------------------------------------------
    {
        'name': 'intersection_direct_and_from_chain',
        'schema': '''
            type user
            type folder
              relations
                define parent: [folder]
                define direct_ed: [user]
                define inherited_ed: direct_ed from parent
                define both: direct_ed and inherited_ed
        ''',
        'ops': [
            (E, 'user', 'alice', 'direct_ed', 'folder', 'child'),   # A: direct on child
            (E, 'user', 'alice', 'direct_ed', 'folder', 'par'),     # for the from-chain
            (E, 'folder', 'par', 'parent', 'folder', 'child'),      # child's parent is par
        ],
        'expect': [
            # alice: direct_ed(child)=True (direct) AND inherited_ed(child)=True (alice
            # direct_ed par, par is child's parent) -> both = True
            (E, 'user', 'alice', 'both', 'folder', 'child', True),
            # alice IS a direct editor and inherited editor individually
            (E, 'user', 'alice', 'direct_ed', 'folder', 'child', True),
            (E, 'user', 'alice', 'inherited_ed', 'folder', 'child', True),
            # bob has neither
            (E, 'user', 'bob', 'both', 'folder', 'child', False),
        ],
    },

    # -------------------------------------------------------------------
    # [user:*] but not blocked, including a ghost (spec §7.2)
    # -------------------------------------------------------------------
    {
        'name': 'public_but_not_blocked',
        'schema': '''
            type user
            type doc
              relations
                define blocked: [user]
                define access: [user:*] but not blocked
        ''',
        'ops': [
            (E, 'user', '*', 'access', 'doc', 'd'),        # public
            (E, 'user', 'alice', 'blocked', 'doc', 'd'),   # except alice
        ],
        'expect': [
            (E, 'user', 'ghost', 'access', 'doc', 'd', True),    # covered by star, not blocked
            (E, 'user', 'alice', 'access', 'doc', 'd', False),   # blocked
            (E, 'user', '*', 'access', 'doc', 'd', True),        # star in A, not in B
        ],
    },

    # -------------------------------------------------------------------
    # Exclusion whose subtrahend is a star: [user] but not [user:*] -> empty concretes
    # -------------------------------------------------------------------
    {
        'name': 'exclude_star_subtrahend',
        'schema': '''
            type user
            type doc
              relations
                define x: [user] but not [user:*]
        ''',
        'ops': [
            (E, 'user', 'alice', 'x', 'doc', 'd'),
            (E, 'user', '*', 'x', 'doc', 'd'),
        ],
        'expect': [
            # concrete alice: base [user] True, but [user:*] star covers her -> False
            (E, 'user', 'alice', 'x', 'doc', 'd', False),
            # '*': base [user] has no star -> not covered in base -> False
            (E, 'user', '*', 'x', 'doc', 'd', False),
        ],
    },

    # -------------------------------------------------------------------
    # Intersection with an empty branch
    # -------------------------------------------------------------------
    {
        'name': 'intersection_empty_branch',
        'schema': '''
            type user
            type doc
              relations
                define a: [user]
                define b: [user]
                define both: a and b
        ''',
        'ops': [
            (E, 'user', 'alice', 'a', 'doc', 'd'),     # only branch a is populated
        ],
        'expect': [
            (E, 'user', 'alice', 'both', 'doc', 'd', False),   # b empty -> intersection empty
            (E, 'user', 'alice', 'a', 'doc', 'd', True),
            (E, 'user', 'alice', 'b', 'doc', 'd', False),
        ],
    },
]
