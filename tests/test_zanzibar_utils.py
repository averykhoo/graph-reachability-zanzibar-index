from collections import Counter
from pathlib import Path
import pytest

from zanzibar_utils_v1 import (
    Entity,
    EntityPattern,
    RelationalTriple,
    RelationalTriplePattern,
    Filter,
    Rule,
    RuleSet,
    parse_openfga_schema,
    parse_schema_ast,
    Union,
    Intersection,
    Exclusion,
    UnsupportedByGraphIndex,
)


def test_entity_pattern_match():
    pattern = EntityPattern(type='user', name='alice')
    assert pattern.match(Entity('user', 'alice'))
    assert not pattern.match(Entity('user', 'bob'))
    assert not pattern.match(Entity('group', 'alice'))

    pattern_any_user = EntityPattern(type='user')
    assert pattern_any_user.match(Entity('user', 'alice'))
    assert pattern_any_user.match(Entity('user', 'bob'))
    assert not pattern_any_user.match(Entity('group', 'alice'))


def test_relational_triple_pattern_match():
    pattern = RelationalTriplePattern(
        subject_type='user',
        subject_name='alice',
        relation='owner',
        object_type='document',
        object_name='doc1'
    )
    triple = RelationalTriple(
        subject=Entity('user', 'alice'),
        relation='owner',
        object=Entity('document', 'doc1'),
        subject_predicate='...'
    )
    assert pattern.match(triple)

    triple_diff = RelationalTriple(
        subject=Entity('user', 'alice'),
        relation='viewer',
        object=Entity('document', 'doc1'),
        subject_predicate='...'
    )
    assert not pattern.match(triple_diff)


def test_filter_apply():
    flt = Filter(RelationalTriplePattern(subject_type='user', relation='member', object_type='group'))
    triple = RelationalTriple(Entity('user', 'alice'), 'member', Entity('group', 'g1'))
    assert flt.apply(triple) is True

    triple_diff = RelationalTriple(Entity('user', 'alice'), 'owner', Entity('document', 'doc1'))
    assert flt.apply(triple_diff) is False


def test_rule_apply():
    rule = Rule(
        if_pattern=RelationalTriplePattern(relation='owner', object_type='document'),
        then_pattern=RelationalTriplePattern(relation='writer', object_type='document')
    )
    triple = RelationalTriple(Entity('user', 'alice'), 'owner', Entity('document', 'doc1'))
    result = rule.apply(triple)
    assert result is not None
    assert result.relation == 'writer'
    assert result.object.type == 'document'
    assert result.object.name == 'doc1'
    assert result.subject.type == 'user'
    assert result.subject.name == 'alice'

    triple_diff = RelationalTriple(Entity('user', 'alice'), 'viewer', Entity('document', 'doc1'))
    result_diff = rule.apply(triple_diff)
    assert result_diff is None


def test_ruleset_apply():
    # If a user is an owner, they are a writer
    rule1 = Rule(
        RelationalTriplePattern(relation='owner', object_type='document'),
        RelationalTriplePattern(relation='writer', object_type='document')
    )
    # If a user is a writer, they are a viewer
    rule2 = Rule(
        RelationalTriplePattern(relation='writer', object_type='document'),
        RelationalTriplePattern(relation='viewer', object_type='document')
    )
    # Filter to accept direct owners
    flt = Filter(RelationalTriplePattern(subject_type='user', relation='owner', object_type='document'))

    ruleset = RuleSet([flt, rule1, rule2])
    
    triple = RelationalTriple(Entity('user', 'alice'), 'owner', Entity('document', 'doc1'))
    
    results = list(ruleset.apply(triple))
    assert len(results) == 3
    
    relations = {r.relation for r in results}
    assert relations == {'owner', 'writer', 'viewer'}
    
    # Try an invalid triple (e.g. viewer, which doesn't pass the filter)
    triple_viewer = RelationalTriple(Entity('user', 'alice'), 'viewer', Entity('document', 'doc1'))
    results_viewer = list(ruleset.apply(triple_viewer))
    assert len(results_viewer) == 0


def test_parse_openfga_schema():
    schema = '''
    model
      schema 1.1

    type user

    type domain
      relations
        define member: [user]

    type folder
      relations
        define can_share: writer
        define owner: [user, domain#member] or owner from parent_folder
        define parent_folder: [folder]
        define viewer: [user, domain#member] or writer or viewer from parent_folder
        define writer: [user, domain#member] or owner or writer from parent_folder
    '''
    ruleset = parse_openfga_schema(schema)
    
    # Check that owner correctly filters
    owner_triple = RelationalTriple(Entity('user', 'alice'), 'owner', Entity('folder', 'f1'))
    assert len(list(ruleset.apply(owner_triple))) > 0

    # owner implies writer (from "writer: ... or owner")
    results = list(ruleset.apply(owner_triple))
    relations = {r.relation for r in results}
    assert 'owner' in relations
    assert 'writer' in relations
    assert 'viewer' in relations # because writer implies viewer

    # Test "owner from parent_folder"
    # The triple for parent_folder is (folder1, parent_folder, folder2)
    parent_owner_triple = RelationalTriple(
        subject=Entity('folder', 'f1'),
        relation='parent_folder',
        object=Entity('folder', 'f2'),
        subject_predicate=Ellipsis
    )
    results = list(ruleset.apply(parent_owner_triple))
    relations = {r.relation for r in results}
    assert 'owner' in relations
    assert 'writer' in relations
    assert 'viewer' in relations
    
    # Check that it implies folder2#owner @ folder1#owner
    implied_owner = [r for r in results if r.relation == 'owner'][0]
    assert implied_owner.subject.type == 'folder'
    assert implied_owner.subject.name == 'f1'
    assert implied_owner.subject_predicate == 'owner'
    assert 'writer' in relations
    assert 'viewer' in relations



# Some fixtures use boolean operators (`and` / `but not`) and compile into derived
# predicates; the rest are pure-union. The two are asserted DIFFERENTLY below, so the
# split has to be right.
#
# ★ THIS SET IS DERIVED, NOT HAND-WRITTEN, AND THAT IS THE POINT. It used to be a
# literal `{'demorgans_law_1.fga', ...}`. `FGA_FILES` is a glob, so adding a boolean
# fixture without remembering to extend that literal routed it into
# `test_parse_fga_schemas`, whose only assertion is `len(rules_and_filters) > 0` --
# which a boolean schema satisfies. The new fixture would then be "covered" while
# every boolean-specific assertion (compiled plans, derived families, the
# `enable_boolean=False` refusal) silently never ran on it. That is the house failure
# mode (`docs/sabotage-procedure.md`): a hand-maintained list beside a glob.
# Sabotage evidence is in `test_boolean_fga_files_is_derived_not_hardcoded` below.
def _is_boolean_fixture(path: Path) -> bool:
    def walk(e):
        yield e
        if isinstance(e, (Union, Intersection)):
            for c in e.children:
                yield from walk(c)
        elif isinstance(e, Exclusion):
            yield from walk(e.base)
            yield from walk(e.subtract)

    ast = parse_schema_ast(path.read_text(encoding='utf-8'))
    return any(isinstance(n, (Intersection, Exclusion))
               for expr in ast.values() for n in walk(expr))


_FGA_DIR = Path(__file__).parent / "fga_schemas"
FGA_FILES = [f.name for f in _FGA_DIR.glob("*.fga")]
BOOLEAN_FGA_FILES = {f for f in FGA_FILES if _is_boolean_fixture(_FGA_DIR / f)}
UNION_FGA_FILES = [f for f in FGA_FILES if f not in BOOLEAN_FGA_FILES]

# Anti-vacuity: both parametrize lists must be non-empty, and the boolean set must
# still contain the fixtures it was seeded from. A derivation that silently returns
# `set()` would make every boolean assertion below vanish into `0 collected`.
assert UNION_FGA_FILES, "no pure-union fixtures found -- the union leg is vacuous"
assert {'demorgans_law_1.fga', 'demorgans_law_2.fga', 'demorgans_reverse.fga',
        'boolean_wildcards.fga'} <= BOOLEAN_FGA_FILES, (
    f"the derivation lost a known-boolean fixture; got {sorted(BOOLEAN_FGA_FILES)}")

@pytest.mark.parametrize("fga_file", UNION_FGA_FILES)
def test_parse_fga_schemas(load_fga_schema, fga_file):
    schema = load_fga_schema(fga_file)
    ruleset = parse_openfga_schema(schema)
    assert len(ruleset.rules_and_filters) > 0


@pytest.mark.parametrize("fga_file", sorted(BOOLEAN_FGA_FILES))
def test_parse_boolean_fga_schemas_compile_for_graph(load_fga_schema, fga_file):
    # The P7 flip (boolean spec §10): boolean schemas compile into derived predicates
    # (leaf routing + executable plans) instead of being refused. The refusal remains
    # reachable via enable_boolean=False for callers that want the historical guard.
    schema = load_fga_schema(fga_file)
    ruleset = parse_openfga_schema(schema)
    assert ruleset.compiled is not None and ruleset.compiled.plans
    assert ruleset.schema_info.derived_families
    with pytest.raises(UnsupportedByGraphIndex):
        parse_openfga_schema(schema, enable_boolean=False)


def test_boolean_fga_files_is_derived_not_hardcoded():
    """The routing above must come from the SCHEMA, not from a maintained literal.

    Sabotage (`docs/sabotage-procedure.md` -- break the narrowest plausible weakening,
    not an obvious catastrophe). The plausible failure is not "the list is deleted"; it
    is "someone adds a boolean fixture and forgets the list". Simulated by restoring the
    exact pre-2026-08-11 literal. Literal observed output::

        BOOLEAN_FGA_FILES = {'demorgans_law_1.fga', 'demorgans_law_2.fga',
                             'demorgans_reverse.fga', 'boolean_wildcards.fga'}

        E         'owc_star_ttu.fga'
        E         'userset_over_derived.fga'
        FAILED tests/test_zanzibar_utils.py::test_boolean_fga_files_is_derived_not_hardcoded
        1 failed, 19 passed

    ★ Note WHICH files that names. ``owc_star_ttu.fga`` is not new -- it carries
    ``define restricted: editor but not blocked`` and has been in the tree since the
    2026-08-09 I14 work, routed by that literal into ``test_parse_fga_schemas``, whose
    only assertion is ``len(rules_and_filters) > 0``. A boolean schema passes that. So
    for the whole of its life the fixture's boolean-specific assertions -- compiled
    plans, derived families, the ``enable_boolean=False`` refusal -- never ran on it,
    and the suite was green throughout. The hand-maintained list beside a glob had
    already failed silently once before anyone added a fixture to it.

    This test pins the property that makes that impossible: EVERY fixture containing a
    boolean operator is in the boolean set, checked against an independent scan of the
    raw source text rather than against the AST walk the derivation itself uses.
    """
    # Independent instrument: crude textual scan, NOT the AST walk `_is_boolean_fixture`
    # uses. A bug in the walk cannot hide from this, because they share no derivation.
    textual = set()
    for name in FGA_FILES:
        body = (_FGA_DIR / name).read_text(encoding='utf-8')
        # strip comments, then look for the operator tokens in relation bodies
        src = '\n'.join(l.split('#')[0] for l in body.splitlines())
        if ' but not ' in src or ' and ' in src:
            textual.add(name)

    assert textual == BOOLEAN_FGA_FILES, (
        f"the derived boolean set disagrees with an independent textual scan.\n"
        f"  only in textual scan : {sorted(textual - BOOLEAN_FGA_FILES)}\n"
        f"  only in derived set  : {sorted(BOOLEAN_FGA_FILES - textual)}\n"
        f"A fixture in the first list would be asserted as if it were pure-union.")
    assert not (BOOLEAN_FGA_FILES & set(UNION_FGA_FILES)), \
        "a fixture is in BOTH legs -- the split is not a partition"
