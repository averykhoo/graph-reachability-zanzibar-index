"""
P2 compile tests (boolean spec §3, §11-P2): taint, plan trees, leaf naming, strata,
cycle rejection, decision-15 scope errors, write routing (fan-in + exclusivity), the
'.'-reservation, and the parse->unparse->parse round-trip.

Boolean compilation is opt-in (`enable_boolean=True`) until the P7 matrix flip wires
the delta processor in; the default path must stay byte-identical (guarded here and by
tests/test_compile_snapshot.py).
"""

from pathlib import Path

import pytest

from zanzibar.schema import (
    Entity, Exclusion, Intersection, RelationalTriple, RewriteFilter, Rule, Union,
    UnsupportedByGraphIndex,
    PClosureLeaf, PDerivedTTU, PExclusion,
    PIntersection, PUnion,
    compute_taint, parse_openfga_schema, parse_schema_ast, unparse_schema_ast,
)
from tests.wildcard_helpers import make_wildcard_index

#: A CURATED subset of `tests/fga_schemas/`, not the whole corpus -- so this list stays
#: hand-written. What is no longer hand-written is the boolean/pure SPLIT.
#:
#: ⚠ Until 2026-09-20g the split was two hardcoded index slices, `ALL_FIXTURES[:4]` and
#: `ALL_FIXTURES[4:]`, and adding `star_admitting_intersection.fga` (`TK83`) walked
#: straight into them: inserted at index 4 it was BOTH missing from the boolean leg and
#: routed into `test_pure_fixtures_identical_under_enable_boolean`, which asserts a
#: schema has NO tainted relations. That one reddened -- loudly, by luck, because the
#: complement slice happens to assert something a boolean schema violates. The other
#: direction is the silent one: append a boolean fixture at the END and it simply never
#: gets its boolean-specific assertions, green throughout. That is exactly how
#: `owc_star_ttu.fga` spent its whole life in the weak leg
#: (`tests/test_schema.py::test_boolean_fga_files_is_derived_not_hardcoded`),
#: and it is the hand-maintained-list-beside-a-derivation pattern this tree has now been
#: bitten by three times. Derived from the SCHEMA, order is no longer load-bearing.
ALL_FIXTURES = ['boolean_wildcards.fga', 'demorgans_law_1.fga', 'demorgans_law_2.fga',
                'demorgans_reverse.fga', 'star_admitting_intersection.fga',
                'confluence.fga', 'custom_roles.fga',
                'gdrive.fga', 'github.fga', 'master_store.fga', 'wildcards.fga']


def _is_boolean_fixture(name: str) -> bool:
    """Does this fixture contain a boolean operator anywhere? Independent of the compiler:
    an AST scan, the same derivation `tests/test_schema.py::_is_boolean_fixture`
    uses. Deliberately NOT `rs.compiled.tainted` -- routing the split through the thing
    under test means a taint-analysis bug reclassifies the fixtures that would have
    caught it.
    """
    def walk(e):
        yield e
        if isinstance(e, (Union, Intersection)):
            for c in e.children:
                yield from walk(c)
        elif isinstance(e, Exclusion):
            yield from walk(e.base)
            yield from walk(e.subtract)

    ast = parse_schema_ast(
        (Path(__file__).parent / 'fga_schemas' / name).read_text(encoding='utf-8'))
    return any(isinstance(n, (Intersection, Exclusion))
               for expr in ast.values() for n in walk(expr))


BOOLEAN_FIXTURES = [f for f in ALL_FIXTURES if _is_boolean_fixture(f)]
PURE_FIXTURES = [f for f in ALL_FIXTURES if not _is_boolean_fixture(f)]

# ANTI-VACUITY. A derivation that returned `[]` would make one whole leg vanish into
# `0 collected` and the module would still report green -- the failure mode the slices
# were replaced to avoid, reintroduced one level up.
assert BOOLEAN_FIXTURES and PURE_FIXTURES, (
    f'the boolean/pure split collapsed: {BOOLEAN_FIXTURES} / {PURE_FIXTURES}')
assert len(BOOLEAN_FIXTURES) + len(PURE_FIXTURES) == len(ALL_FIXTURES)
assert {'boolean_wildcards.fga', 'demorgans_law_1.fga', 'demorgans_law_2.fga',
        'demorgans_reverse.fga', 'star_admitting_intersection.fga'} == set(BOOLEAN_FIXTURES), (
    f'the derivation lost or gained a known-boolean fixture: {BOOLEAN_FIXTURES}')


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
    """TRIMMED 2026-09-26 (TK106). The fixture used to chain three `from`s over boolean
    tuplesets (`unmatchable_conds`, `matched_roles`, `matched_users`), five tainted
    relations in all; a non-direct tupleset is now a parse refusal, and only the legal
    `non_labels` core is left."""
    ast = parse_schema_ast(load_fga_schema('demorgans_law_1.fga'))
    assert compute_taint(ast) == frozenset({('doc', 'non_labels')})


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
    """The star-minus-concrete `non_labels` plan.

    Until 2026-09-26 this also pinned the derived-tupleset TTU chain (three
    `PDerivedTuplesetTTU` plans over five strata, and `target_feeders` for their untainted
    targets). TK106 made a non-direct tupleset a parse refusal and the fixture was trimmed
    to its legal core, so the chain cannot be written; the compiler path it exercised is
    unreachable from a checked parse (dead-code follow-up on the TK106 row)."""
    rs = parse_openfga_schema(load_fga_schema('demorgans_law_1.fga'), enable_boolean=True)
    plans = rs.compiled.plans

    non_labels = plans[('doc', 'non_labels')]
    assert non_labels.tree == PExclusion(
        PClosureLeaf('non_labels.0', True), PClosureLeaf('non_labels.1', False))
    assert set(plans) == {('doc', 'non_labels')}
    assert rs.compiled.strata == [[('doc', 'non_labels')]]
    assert not rs.compiled.target_feeders
    # (The retired chain assertions are in git history: `git show 9d1bedf:tests/test_boolean_compile.py`.)


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


@pytest.mark.parametrize('fixture', PURE_FIXTURES)
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


def test_object_wildcard_on_derived_ttu_tupleset_rejected():
    """Decision-15 family: an object-wildcard shape on the TUPLESET relation of a
    TTU inside a tainted plan. tupleset_parents enumerates direct stored tuples on
    the tupleset node, so a `doc:p parent doc:*` grant (w_all state) would be
    silently invisible to derived evaluation -- wrong denials with no invariant
    tripping (review 3)."""
    schema = '''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define viewer: public but not blocked
            define parent: [doc]
            define inherited: viewer from parent
    '''
    with pytest.raises(UnsupportedByGraphIndex, match='tupleset of TTU'):
        parse_openfga_schema(schema, object_wildcard_shapes=frozenset({('doc', 'parent')}))


def test_star_tupleset_through_shape_over_derived_rejected():
    """A star tupleset [S:*] whose TTU target is derived: the through-shape
    (S, target_rel) is a wildcard userset over a derived relation -- the same v1
    scope hook _build_plan_tree rejects when declared directly. Left underived it
    landed in bridged_in_shapes, which the processor's idx.node() path never
    bridges, structurally violating I3 (review 3)."""
    schema = '''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define viewer: public but not blocked
            define parent: [doc:*]
            define inherited: viewer from parent
    '''
    with pytest.raises(UnsupportedByGraphIndex, match='symbolic composition'):
        parse_openfga_schema(schema)


def test_object_wildcard_expanding_onto_leaf_rejected():
    """Decision-15 ordering: the scope guards must run AFTER shape expansion. A
    shape on an untainted relation that a tainted plan's closure leaf routes
    (Rule editor -> view.0) is the same wildcard-object-into-derived-state class
    the leaf guard rejects when declared directly; unguarded, the first legal
    star-object write crashed the delta processor mid-transaction (review 3)."""
    schema = '''
        type user
        type doc
          relations
            define editor: [user]
            define banned: [user]
            define view: editor but not banned
    '''
    with pytest.raises(UnsupportedByGraphIndex, match='compiled leaf predicate'):
        parse_openfga_schema(schema, object_wildcard_shapes=frozenset({('doc', 'editor')}))


def test_object_wildcard_upstream_of_derived_ttu_target_rejected():
    """D4 through expansion: the shape is declared one Computed hop upstream of
    the TTU target (folder#editor -> folder#viewer), so the declared-only guard
    missed it while the rewrite rules routed the same w_all state into the
    guarded position (review 3)."""
    schema = '''
        type user
        type folder
          relations
            define editor: [user]
            define viewer: [user] or editor
        type doc
          relations
            define parent: [folder]
            define banned: [user]
            define access: viewer from parent but not banned
    '''
    with pytest.raises(UnsupportedByGraphIndex, match='TTU target'):
        parse_openfga_schema(schema,
                             object_wildcard_shapes=frozenset({('folder', 'editor')}))


def test_rewritten_untainted_tupleset_rejected():
    """Zanzibar tupleset semantics read STORED tuples only. An untainted tupleset
    with computed arms would let the graph's TTU rule illegally propagate rewritten
    members (which the oracle and set engine, reading raw tuples, would not).

    Since TK106 (2026-09-26, user decision) the schema is refused at PARSE time by every
    backend, as OpenFGA refuses it. Until then only the graph refused it
    (`UnsupportedByGraphIndex`, 'stored tuples only'), and the set engine degraded to
    ruleset-less evaluation and answered, silently ignoring the `or alias` arm, which is
    what this test pinned. The graph compiler's own refusal
    (`_validate_ttu_tuplesets`) is now unreachable from a checked parse. The whole
    refused family is pinned in `tests/test_tupleset_must_be_direct.py`."""
    schema = '''
        type user
        type folder
          relations
            define viewer: [user]
        type doc
          relations
            define alias: [folder]
            define parent: [folder] or alias
            define viewer: [user] or viewer from parent
    '''
    with pytest.raises(ValueError, match='tupleset must be direct'):
        parse_openfga_schema(schema)
    with pytest.raises(ValueError, match='tupleset must be direct'):
        parse_openfga_schema(schema, enable_boolean=False)

    # the set engine refuses too; it no longer degrades past the schema
    from sqlmodel import Session, SQLModel, create_engine
    from zanzibar.setengine import SetEngine
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        with pytest.raises(ValueError, match='tupleset must be direct'):
            SetEngine(session, 's', schema)


# `test_derived_tupleset_still_compiles` was RETIRED 2026-09-26 (TK106). It asserted that a
# DERIVED (tainted) tupleset keeps compiling, via demorgans_law_1's `required_by from
# non_labels`. That is now false by design: every non-direct tupleset is a parse refusal
# (`tests/test_tupleset_must_be_direct.py`), because `from` walks stored tuples and would
# silently ignore the boolean arm.


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

    from zanzibar.graphindex.outbox import drain_deltas, outbox_watermark
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
