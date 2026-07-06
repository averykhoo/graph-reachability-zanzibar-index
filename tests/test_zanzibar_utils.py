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



# The demorgans fixtures use boolean operators (`and` / `but not`); the graph index
# refuses them loudly (spec §2.3). Every other fixture is pure-union and must compile.
BOOLEAN_FGA_FILES = {'demorgans_law_1.fga', 'demorgans_law_2.fga', 'demorgans_reverse.fga',
                     'boolean_wildcards.fga'}
FGA_FILES = [f.name for f in (Path(__file__).parent / "fga_schemas").glob("*.fga")]
UNION_FGA_FILES = [f for f in FGA_FILES if f not in BOOLEAN_FGA_FILES]

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
