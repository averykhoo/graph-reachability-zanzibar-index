"""
P0 tests (spec §2): the recursive-descent parser, the SchemaAST it produces, and
the parse/compile split. The parser unit tests over the demorgans fixtures replace
the retired `test_integration_demorgans` xfail (spec §7.4a).
"""

import pytest

from zanzibar_utils_v1 import (
    Direct,
    Restriction,
    Computed,
    TTU,
    Union,
    Intersection,
    Exclusion,
    parse_schema_ast,
    derive_schema_info,
    compile_ruleset,
    parse_openfga_schema,
    UnsupportedByGraphIndex,
)


# ---------------------------------------------------------------------------
# Leaf parsing
# ---------------------------------------------------------------------------

def _rel(schema, obj_type, relation):
    return parse_schema_ast(schema)[(obj_type, relation)]


def test_direct_leaf_restriction_list():
    schema = '''
    type user
    type group
      relations
        define member: [user, group#member, user:*, group:*#member]
    '''
    expr = _rel(schema, 'group', 'member')
    assert expr == Direct((
        Restriction('user', '...', False),
        Restriction('group', 'member', False),
        Restriction('user', '...', True),
        Restriction('group', 'member', True),
    ))


def test_computed_leaf():
    schema = '''
    type doc
      relations
        define viewer: editor
    '''
    assert _rel(schema, 'doc', 'viewer') == Computed('editor')


def test_ttu_leaf():
    schema = '''
    type doc
      relations
        define viewer: viewer from parent_folder
    '''
    assert _rel(schema, 'doc', 'viewer') == TTU('viewer', 'parent_folder')


def test_union_of_leaves():
    schema = '''
    type user
    type doc
      relations
        define viewer: [user] or editor or viewer from parent
    '''
    assert _rel(schema, 'doc', 'viewer') == Union((
        Direct((Restriction('user', '...', False),)),
        Computed('editor'),
        TTU('viewer', 'parent'),
    ))


def test_single_leaf_not_wrapped_in_union():
    schema = '''
    type user
    type g
      relations
        define member: [user]
    '''
    assert _rel(schema, 'g', 'member') == Direct((Restriction('user', '...', False),))


# ---------------------------------------------------------------------------
# Boolean operators
# ---------------------------------------------------------------------------

def test_exclusion():
    schema = '''
    type doc
      relations
        define x: a but not b
    '''
    assert _rel(schema, 'doc', 'x') == Exclusion(Computed('a'), Computed('b'))


def test_intersection():
    schema = '''
    type doc
      relations
        define x: a and b and c
    '''
    assert _rel(schema, 'doc', 'x') == Intersection((Computed('a'), Computed('b'), Computed('c')))


def test_exclusion_binds_loosest():
    # `a or b but not c` == `(a or b) but not c`
    schema = '''
    type doc
      relations
        define x: a or b but not c
    '''
    assert _rel(schema, 'doc', 'x') == Exclusion(
        Union((Computed('a'), Computed('b'))), Computed('c'))


def test_parenthesized_unit():
    schema = '''
    type doc
      relations
        define x: (a or b) and c
    '''
    assert _rel(schema, 'doc', 'x') == Intersection((
        Union((Computed('a'), Computed('b'))), Computed('c')))


def test_mixing_or_and_without_parens_is_error():
    schema = '''
    type doc
      relations
        define x: a or b and c
    '''
    with pytest.raises(ValueError, match='x'):
        parse_schema_ast(schema)


def test_both_sides_of_but_not_may_be_chains():
    schema = '''
    type doc
      relations
        define x: a or b but not (c and d)
    '''
    assert _rel(schema, 'doc', 'x') == Exclusion(
        Union((Computed('a'), Computed('b'))),
        Intersection((Computed('c'), Computed('d'))),
    )


# ---------------------------------------------------------------------------
# Demorgans fixtures: AST shape (replaces the retired xfail, spec §7.4a)
# ---------------------------------------------------------------------------

def test_demorgans_law_1_ast(load_fga_schema):
    ast = parse_schema_ast(load_fga_schema('demorgans_law_1.fga'))
    assert ast[('doc', '_all_attrs')] == Direct((Restriction('attr', '...', True),))
    assert ast[('doc', 'labels')] == Direct((Restriction('attr', '...', False),))
    assert ast[('doc', 'non_labels')] == Exclusion(Computed('_all_attrs'), Computed('labels'))
    assert ast[('doc', 'matchable_conds')] == Exclusion(
        Computed('_all_conds'), Computed('unmatchable_conds'))
    assert ast[('doc', 'unmatchable_conds')] == TTU('required_by', 'non_labels')
    assert ast[('doc', 'matched_roles')] == TTU('assigned', 'matchable_conds')
    assert ast[('doc', 'matched_users')] == TTU('granted', 'matched_roles')


def test_demorgans_law_2_ast(load_fga_schema):
    ast = parse_schema_ast(load_fga_schema('demorgans_law_2.fga'))
    assert ast[('attr', '_all_users')] == Direct((Restriction('user', '...', True),))
    assert ast[('attr', 'missing_user')] == Exclusion(Computed('_all_users'), Computed('has_attr'))
    assert ast[('cond', 'user_missing_requirement')] == TTU('missing_user', 'requires')
    assert ast[('cond', 'user_met_requirement')] == Exclusion(
        Computed('_all_users'), Computed('user_missing_requirement'))
    assert ast[('role', 'authorized_user')] == Intersection(
        (Computed('assigned'), Computed('role_user_met')))
    assert ast[('doc', 'access')] == TTU('authorized_user', 'associated_role')


def test_demorgans_reverse_ast(load_fga_schema):
    ast = parse_schema_ast(load_fga_schema('demorgans_reverse.fga'))
    assert ast[('attr', 'does_not_label')] == Exclusion(Computed('_all_docs'), Computed('labels'))
    assert ast[('cond', 'requirement_met')] == Exclusion(
        Computed('_all_docs'), Computed('requirement_not_met'))
    assert ast[('role', 'access')] == TTU('requirement_met', 'match_any')
    assert ast[('user', 'access')] == TTU('access', 'assigned')


# ---------------------------------------------------------------------------
# SchemaInfo derivation from the AST
# ---------------------------------------------------------------------------

def test_derive_schema_info_from_ast(load_fga_schema):
    ast = parse_schema_ast(load_fga_schema('wildcards.fga'))
    info = derive_schema_info(ast, object_wildcard_shapes={('folder', 'viewer'), ('document', 'viewer')})
    assert info.subject_wildcard_shapes == frozenset({('user', '...'), ('group', 'member')})
    assert info.object_wildcard_shapes == frozenset({('folder', 'viewer'), ('document', 'viewer')})


def test_derive_schema_info_sees_wildcards_inside_booleans():
    # A `T:*` restriction buried in an exclusion still registers as a subject-wildcard shape.
    schema = '''
    type user
    type doc
      relations
        define blocked: [user]
        define x: [user:*] but not blocked
    '''
    info = derive_schema_info(parse_schema_ast(schema))
    assert ('user', '...') in info.subject_wildcard_shapes


# ---------------------------------------------------------------------------
# compile_ruleset: pure-union compiles, booleans refused (spec §2.3)
# ---------------------------------------------------------------------------

def test_compile_pure_union_succeeds(load_fga_schema):
    ast = parse_schema_ast(load_fga_schema('wildcards.fga'))
    info = derive_schema_info(ast)
    ruleset = compile_ruleset(ast, info)
    assert len(ruleset.rules_and_filters) > 0
    assert ruleset.schema_info is info


# ---------------------------------------------------------------------------
# The P7 flip: boolean schemas COMPILE into derived predicates (boolean spec §10 --
# these replace the historical refusal tests; plan-shape depth lives in
# tests/test_boolean_compile.py).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('fixture', ['demorgans_law_1.fga', 'demorgans_law_2.fga', 'demorgans_reverse.fga'])
def test_compile_accepts_booleans(load_fga_schema, fixture):
    ast = parse_schema_ast(load_fga_schema(fixture))
    ruleset = compile_ruleset(ast, derive_schema_info(ast))
    assert ruleset.compiled is not None and ruleset.compiled.plans
    assert ruleset.compiled.strata, 'derived relations must stratify'
    # every tainted relation has an executable plan in a stratum
    for key in ruleset.compiled.tainted:
        assert key in ruleset.compiled.plans


def test_compile_boolean_intersection_gets_plan():
    schema = '''
    type user
    type doc
      relations
        define a: [user]
        define b: [user]
        define x: a and b
    '''
    ast = parse_schema_ast(schema)
    ruleset = compile_ruleset(ast, derive_schema_info(ast))
    plan = ruleset.compiled.plans[('doc', 'x')]
    assert [s.kind for s in plan.leaves] == ['closure', 'closure']
    assert callable(plan.check_fn) and callable(plan.stars_fn)


def test_enable_boolean_false_restores_refusal(load_fga_schema):
    # the historical behavior stays reachable for callers that want the guard
    with pytest.raises(UnsupportedByGraphIndex):
        parse_openfga_schema(load_fga_schema('demorgans_law_2.fga'), enable_boolean=False)
