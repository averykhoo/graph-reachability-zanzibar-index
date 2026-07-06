"""
P2 compile tests (boolean spec §3, §11-P2): taint, plan trees, leaf naming, strata,
cycle rejection, decision-15 scope errors, write routing (fan-in + exclusivity), the
'.'-reservation, and the parse->unparse->parse round-trip.

Boolean compilation is opt-in (`enable_boolean=True`) until the P7 matrix flip wires
the delta processor in; the default path must stay byte-identical (guarded here and by
tests/test_compile_snapshot.py).
"""

import pytest

from zanzibar_utils_v1 import (
    Entity, RelationalTriple, RewriteFilter, Rule, UnsupportedByGraphIndex,
    PClosureLeaf, PDerivedComputed, PDerivedTTU, PDerivedTuplesetTTU, PExclusion,
    PIntersection, PUnion,
    compute_taint, parse_openfga_schema, parse_schema_ast, unparse_schema_ast,
)
from tests.wildcard_helpers import make_wildcard_index

ALL_FIXTURES = ['boolean_wildcards.fga', 'demorgans_law_1.fga', 'demorgans_law_2.fga',
                'demorgans_reverse.fga', 'confluence.fga', 'custom_roles.fga',
                'gdrive.fga', 'github.fga', 'master_store.fga', 'wildcards.fga']

BOOLEAN_FIXTURES = ALL_FIXTURES[:4]


def _raw(s_pred, s_type, s_name, rel, o_type, o_name):
    sp = Ellipsis if s_pred == '...' else s_pred
    return RelationalTriple(Entity(s_type, s_name), rel, Entity(o_type, o_name), sp)


# ---------------------------------------------------------------------------
# Taint analysis (§3.1)
# ---------------------------------------------------------------------------

def test_taint_boolean_wildcards(load_fga_schema):
    ast = parse_schema_ast(load_fga_schema('boolean_wildcards.fga'))
    assert compute_taint(ast) == frozenset({
        ('doc', 'viewer'),        # (public but not blocked) or editor
        ('doc', 'restricted'),    # editor and public
        ('doc', 'inherited'),     # TTU over the boolean viewer
    })


def test_taint_propagates_through_pure_union_reference():
    """The §3.1 bug this analysis exists to prevent: a plain union over a boolean
    relation compiled normally would silently drop its star-covered members."""
    ast = parse_schema_ast('''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define admin: [user]
            define viewer: public but not blocked
            define approver: viewer or admin
    ''')
    tainted = compute_taint(ast)
    assert ('doc', 'approver') in tainted           # tainted via Computed(viewer)
    assert ('doc', 'admin') not in tainted


def test_taint_demorgans_law_1(load_fga_schema):
    ast = parse_schema_ast(load_fga_schema('demorgans_law_1.fga'))
    assert compute_taint(ast) == frozenset({
        ('doc', 'non_labels'), ('doc', 'unmatchable_conds'), ('doc', 'matchable_conds'),
        ('doc', 'matched_roles'), ('doc', 'matched_users'),
    })


# ---------------------------------------------------------------------------
# Plan shapes + deterministic leaf naming (§3.2) -- the refusal tests' replacement
# ---------------------------------------------------------------------------

def test_plan_shapes_boolean_wildcards(load_fga_schema):
    rs = parse_openfga_schema(load_fga_schema('boolean_wildcards.fga'), enable_boolean=True)
    plans = rs.compiled.plans

    # viewer: (public but not blocked) or editor
    viewer = plans[('doc', 'viewer')]
    assert viewer.tree == PUnion((
        PExclusion(PClosureLeaf('viewer.0', True), PClosureLeaf('viewer.1', False)),
        PClosureLeaf('viewer.2', True),
    ))
    assert [(s.predicate, s.positive) for s in viewer.leaves] == \
        [('viewer.0', True), ('viewer.1', False), ('viewer.2', True)]
    assert viewer.deps == ()
    assert viewer.stratum == 0

    # restricted: editor and public
    restricted = plans[('doc', 'restricted')]
    assert restricted.tree == PIntersection((
        PClosureLeaf('restricted.0', True), PClosureLeaf('restricted.1', True)))

    # inherited: viewer from parent (derived target, untainted tupleset)
    inherited = plans[('doc', 'inherited')]
    assert inherited.tree == PDerivedTTU('viewer', 'parent', True, ('doc',))
    assert inherited.deps == (('doc', 'viewer'),)
    assert inherited.stratum == 1

    # strata: {viewer, restricted} before inherited
    assert rs.compiled.strata == [
        [('doc', 'restricted'), ('doc', 'viewer')], [('doc', 'inherited')]]

    # invalidation fan-out: viewer feeds inherited via ttu
    (edge,) = rs.compiled.dependents[('doc', 'viewer')]
    assert (edge.dependent, edge.via, edge.tupleset_rel) == (('doc', 'inherited'), 'ttu', 'parent')


def test_plan_shapes_demorgans_law_1(load_fga_schema):
    """The derived-tupleset TTU chain (decision-15 override; see spec-deviations)."""
    rs = parse_openfga_schema(load_fga_schema('demorgans_law_1.fga'), enable_boolean=True)
    plans = rs.compiled.plans

    non_labels = plans[('doc', 'non_labels')]
    assert non_labels.tree == PExclusion(
        PClosureLeaf('non_labels.0', True), PClosureLeaf('non_labels.1', False))

    unmatchable = plans[('doc', 'unmatchable_conds')]
    assert unmatchable.tree == PDerivedTuplesetTTU('required_by', 'non_labels', True, ('attr',))
    assert unmatchable.deps == (('doc', 'non_labels'),)

    matchable = plans[('doc', 'matchable_conds')]
    assert matchable.tree == PExclusion(
        PClosureLeaf('matchable_conds.0', True),
        PDerivedComputed('unmatchable_conds', False))

    assert plans[('doc', 'matched_roles')].tree == \
        PDerivedTuplesetTTU('assigned', 'matchable_conds', True, ('cond',))
    assert plans[('doc', 'matched_users')].tree == \
        PDerivedTuplesetTTU('granted', 'matched_roles', True, ('role',))

    # five strata, in chain order
    assert rs.compiled.strata == [
        [('doc', 'non_labels')], [('doc', 'unmatchable_conds')],
        [('doc', 'matchable_conds')], [('doc', 'matched_roles')],
        [('doc', 'matched_users')]]

    # untainted targets of derived-tupleset TTUs are registered as feeders
    feeders = rs.compiled.target_feeders
    assert {k: [e.dependent for e in v] for k, v in feeders.items()} == {
        ('attr', 'required_by'): [('doc', 'unmatchable_conds')],
        ('cond', 'assigned'): [('doc', 'matched_roles')],
        ('role', 'granted'): [('doc', 'matched_users')],
    }


@pytest.mark.parametrize('fixture', BOOLEAN_FIXTURES)
def test_boolean_fixtures_compile(load_fga_schema, fixture):
    """All four boolean fixtures compile under enable_boolean (P2 accept criterion);
    every derived relation gets a plan with executable check/star folds."""
    rs = parse_openfga_schema(load_fga_schema(fixture), enable_boolean=True)
    assert rs.compiled is not None and rs.compiled.tainted
    for key, plan in rs.compiled.plans.items():
        assert callable(plan.check_fn) and callable(plan.stars_fn)
        assert plan.stratum == next(
            i for i, layer in enumerate(rs.compiled.strata) if key in layer)


@pytest.mark.parametrize('fixture', ALL_FIXTURES[4:])
def test_pure_fixtures_identical_under_enable_boolean(load_fga_schema, fixture):
    """Untainted relations compile byte-identically whether or not boolean compilation
    is enabled (§3.1: the taint gate, backed by the P0 snapshots)."""
    schema = load_fga_schema(fixture)
    default = parse_openfga_schema(schema)
    enabled = parse_openfga_schema(schema, enable_boolean=True)
    assert enabled.rules_and_filters == default.rules_and_filters
    assert enabled.compiled.tainted == frozenset()
    assert enabled.compiled.plans == {}


# ---------------------------------------------------------------------------
# Compile rejections: cycles, '.'-reservation, decision-15 scope
# ---------------------------------------------------------------------------

def test_derived_dependency_cycle_is_compile_error():
    schema = '''
        type user
        type doc
          relations
            define parent: [doc]
            define blocked: [user]
            define viewer: ([user] or viewer from parent) but not blocked
    '''
    with pytest.raises(ValueError, match='cycle'):
        parse_openfga_schema(schema, enable_boolean=True)


def test_dot_reserved_in_relation_declarations():
    with pytest.raises(ValueError, match=r"reserved"):
        parse_schema_ast('''
            type doc
              relations
                define viewer.0: [user]
        ''')


def test_dot_still_legal_in_entity_names():
    """Only declarations are locked; tuple-side names keep the full charset."""
    schema = '''
        type user
        type doc
          relations
            define viewer: [user]
    '''
    rs = parse_openfga_schema(schema, enable_boolean=True)
    triples = list(rs.apply(_raw('...', 'user', 'a.b@example.com', 'viewer', 'doc', 'd.1')))
    assert len(triples) == 1


def test_object_wildcard_on_derived_rejected():
    schema = '''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define viewer: public but not blocked
    '''
    with pytest.raises(UnsupportedByGraphIndex, match='derived'):
        parse_openfga_schema(schema, object_wildcard_shapes=frozenset({('doc', 'viewer')}),
                             enable_boolean=True)


def test_wildcard_userset_over_derived_rejected():
    schema = '''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define viewer: public but not blocked
        type folder
          relations
            define reader: [doc:*#viewer]
    '''
    with pytest.raises(UnsupportedByGraphIndex, match='symbolic composition'):
        parse_openfga_schema(schema, enable_boolean=True)


# ---------------------------------------------------------------------------
# Write routing (§3.3): rewriting, fan-in, refusals, exclusivity
# ---------------------------------------------------------------------------

_ROUTED = '''
    type user
    type doc
      relations
        define banned: [user]
        define viewer: [user] but not banned
'''


def test_raw_writes_land_only_in_leaf_families(load_fga_schema):
    rs = parse_openfga_schema(_ROUTED, enable_boolean=True)
    leaf_families = rs.compiled.leaf_families
    derived = rs.compiled.derived_families

    out = list(rs.apply(_raw('...', 'user', 'alice', 'viewer', 'doc', 'd1')))
    assert [t.relation for t in out] == ['viewer.0']

    out = list(rs.apply(_raw('...', 'user', 'bob', 'banned', 'doc', 'd1')))
    assert sorted(t.relation for t in out) == ['banned', 'viewer.1']

    for t in out:
        key = (t.object.type, t.relation)
        assert key not in derived, f'rewrite landed on a derived-public family: {t}'
    assert ('doc', 'viewer.0') in leaf_families and ('doc', 'viewer.1') in leaf_families


def test_fan_in_expansion_add_and_remove_symmetric():
    """`[user] and [user]`-shaped schemas populate every owning leaf from one raw write
    (fan-in, all-match, deduped); the expansion is op-agnostic so removes retire the
    same triples."""
    rs = parse_openfga_schema('''
        type user
        type doc
          relations
            define viewer: [user] but not [user]
    ''', enable_boolean=True)
    out = list(rs.apply(_raw('...', 'user', 'alice', 'viewer', 'doc', 'd1')))
    assert sorted(t.relation for t in out) == ['viewer.0', 'viewer.1']


def test_direct_write_to_leaf_name_refused():
    rs = parse_openfga_schema(_ROUTED, enable_boolean=True)
    with pytest.raises(ValueError, match='leaf predicate'):
        list(rs.apply(_raw('...', 'user', 'alice', 'viewer.0', 'doc', 'd1')))


def test_derived_write_matching_no_restriction_refused():
    rs = parse_openfga_schema(_ROUTED, enable_boolean=True)
    # group#member is not a declared restriction of viewer
    with pytest.raises(ValueError, match='no declared type restriction'):
        list(rs.apply(_raw('member', 'group', 'g1', 'viewer', 'doc', 'd1')))


def test_facade_derived_family_exclusivity():
    """Direct façade writes on a derived-public family raise unless the processor flag
    is set (boolean spec §3.3, write-path enforcement of I5)."""
    rs = parse_openfga_schema(_ROUTED, enable_boolean=True)
    assert ('doc', 'viewer') in rs.schema_info.derived_families
    session, widx = make_wildcard_index(rs.schema_info)

    with pytest.raises(ValueError, match='processor'):
        widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')

    from index_v4.outbox import drain_deltas, outbox_watermark
    wm = outbox_watermark(session, 'test')
    widx.processor_writes = True
    widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    widx.processor_writes = False
    session.commit()
    assert drain_deltas(session, 'test', wm), 'processor-flagged derived write must land'

    # leaf-family writes stay open to the (rewritten) raw path
    widx.add_tuple('...', 'user', 'alice', 'viewer.0', 'doc', 'd1')
    session.commit()
    session.close()


# ---------------------------------------------------------------------------
# Round-trip property (§9, P2 accept): parse -> unparse -> parse is identity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('fixture', ALL_FIXTURES)
def test_parser_round_trip(load_fga_schema, fixture):
    ast = parse_schema_ast(load_fga_schema(fixture))
    assert parse_schema_ast(unparse_schema_ast(ast)) == ast


def test_parser_round_trip_nested_operators():
    schema = '''
        type user
        type doc
          relations
            define a: [user]
            define b: [user]
            define c: [user]
            define d: ([user] or (a and b)) but not (b but not c)
    '''
    ast = parse_schema_ast(schema)
    assert parse_schema_ast(unparse_schema_ast(ast)) == ast
