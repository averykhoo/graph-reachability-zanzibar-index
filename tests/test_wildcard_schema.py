"""
P2 schema-layer tests (spec §2): wildcard declaration parsing, strict-vs-permissive
pattern matching, SchemaInfo, and the §2.2 propagation regression.
"""

import pytest

from zanzibar_utils_v1 import (
    Entity,
    EntityPattern,
    RelationalTriple,
    RelationalTriplePattern,
    parse_relation_rule,
    parse_openfga_schema,
    SchemaInfo,
)


# ---------------------------------------------------------------------------
# parse_relation_rule: wildcard subject tokens
# ---------------------------------------------------------------------------

def test_parse_relation_rule_wildcard_subjects():
    assert parse_relation_rule('[user]') == ([('user', None, None)], [])
    assert parse_relation_rule('[user:*]') == ([('user', None, '*')], [])
    assert parse_relation_rule('[group#member]') == ([('group', 'member', None)], [])
    assert parse_relation_rule('[group:*#member]') == ([('group', 'member', '*')], [])
    # mixed list keeps concrete and wildcard entries distinct
    assert parse_relation_rule('[user, user:*]') == ([('user', None, None), ('user', None, '*')], [])
    # non-bracket input is a parse error: the rewrite-reference fallbacks were
    # dead in production (_RelationParser only hands bracket tokens here)
    with pytest.raises(ValueError, match='bracketed'):
        parse_relation_rule('writer')
    with pytest.raises(ValueError, match='bracketed'):
        parse_relation_rule('owner from parent')


# ---------------------------------------------------------------------------
# EntityPattern strict vs permissive (spec §2.2)
# ---------------------------------------------------------------------------

def test_entity_pattern_strict_rejects_wildcard():
    # Default (strict): a name-agnostic pattern refuses a wildcard entity.
    p = EntityPattern(type='user')
    assert p.match(Entity('user', 'alice')) is True
    assert p.match(Entity('user', '*')) is False


def test_entity_pattern_permissive_accepts_wildcard():
    # Permissive + name is None: skip the wildcard guard, match both.
    p = EntityPattern(type='user', match_wildcards=True)
    assert p.match(Entity('user', 'alice')) is True
    assert p.match(Entity('user', '*')) is True


def test_entity_pattern_permissive_still_pins_explicit_name():
    # Permissive only relaxes when name is None. A pinned name still matches literally.
    p = EntityPattern(type='user', name='*', match_wildcards=True)
    assert p.match(Entity('user', '*')) is True
    assert p.match(Entity('user', 'alice')) is False


# ---------------------------------------------------------------------------
# Filters stay strict: [user] rejects user:*, [user:*] accepts only wildcard
# ---------------------------------------------------------------------------

CONCRETE_ONLY_SCHEMA = '''
type user
type document
  relations
    define viewer: [user]
'''

WILDCARD_SCHEMA = '''
type user
type document
  relations
    define viewer: [user:*, user]
'''


def test_concrete_filter_rejects_wildcard_tuple():
    # [user] must keep rejecting a user:* tuple (spec §2.1). A raw tuple matching no
    # declared restriction is REJECTED LOUDLY (ValueError), not silently dropped: a
    # silent drop vacuously "accepts" (graph writes nothing) while the set engine
    # raises on the same tuple -- an accept/reject divergence (see reg13 in
    # tests/test_lookup_oracle.py, docs/spec-deviations.md 2026-07-17).
    ruleset = parse_openfga_schema(CONCRETE_ONLY_SCHEMA)
    wildcard_tuple = RelationalTriple(Entity('user', '*'), 'viewer', Entity('document', 'x'), Ellipsis)
    with pytest.raises(ValueError, match='no declared type restriction'):
        list(ruleset.apply(wildcard_tuple))
    # ...but a concrete user still passes.
    concrete = RelationalTriple(Entity('user', 'alice'), 'viewer', Entity('document', 'x'), Ellipsis)
    assert len(list(ruleset.apply(concrete))) == 1


def test_wildcard_declaration_accepts_wildcard_tuple():
    ruleset = parse_openfga_schema(WILDCARD_SCHEMA)
    wildcard_tuple = RelationalTriple(Entity('user', '*'), 'viewer', Entity('document', 'x'), Ellipsis)
    results = list(ruleset.apply(wildcard_tuple))
    assert len(results) == 1
    assert results[0].subject.name == '*'
    # concrete still accepted too (the `user` entry).
    concrete = RelationalTriple(Entity('user', 'alice'), 'viewer', Entity('document', 'x'), Ellipsis)
    assert len(list(ruleset.apply(concrete))) == 1


# ---------------------------------------------------------------------------
# §2.2 regression: wildcard name survives rewrites
# ---------------------------------------------------------------------------

COMPUTED_SCHEMA = '''
type user
type document
  relations
    define writer: [user:*]
    define viewer: writer
'''


def test_wildcard_propagates_through_computed_userset():
    # define viewer: writer  =>  writer=>viewer rule must carry the user:* subject.
    ruleset = parse_openfga_schema(COMPUTED_SCHEMA)
    t = RelationalTriple(Entity('user', '*'), 'writer', Entity('document', 'x'), Ellipsis)
    results = list(ruleset.apply(t))
    by_rel = {r.relation: r for r in results}
    assert 'writer' in by_rel and 'viewer' in by_rel
    # the derived viewer tuple keeps the '*' subject name
    assert by_rel['viewer'].subject.name == '*'
    assert by_rel['viewer'].subject.type == 'user'


# parent must accept folder:* for a wildcard parent tuple to be valid; only then can
# the from-rule rewrite it (a concrete-only [folder] parent correctly rejects folder:*).
FROM_SCHEMA = '''
type user
type folder
  relations
    define parent: [folder, folder:*]
    define viewer: [user:*] or viewer from parent
type document
  relations
    define parent: [folder, folder:*]
    define viewer: [user:*] or viewer from parent
'''


def test_wildcard_propagates_through_from_chain():
    # A wildcard parent tuple (folder:* parent document:d) rewrites via "viewer from
    # parent" to subject folder:*#viewer, preserving the '*' name (spec §2.2).
    ruleset = parse_openfga_schema(FROM_SCHEMA)
    t = RelationalTriple(
        subject=Entity('folder', '*'),
        relation='parent',
        object=Entity('document', 'd'),
        subject_predicate=Ellipsis,
    )
    results = list(ruleset.apply(t))
    derived_viewers = [r for r in results if r.relation == 'viewer']
    assert derived_viewers, 'from-rule should derive a viewer tuple'
    assert all(r.subject.name == '*' for r in derived_viewers)
    assert all(r.subject.type == 'folder' for r in derived_viewers)


def test_replace_preserves_wildcard_name():
    # Direct check on the rewrite primitive: a name=None pattern preserves '*'.
    pattern = RelationalTriplePattern(relation='viewer', object_type='document', match_wildcards=True)
    t = RelationalTriple(Entity('user', '*'), 'writer', Entity('document', 'x'), Ellipsis)
    out = pattern.replace(t)
    assert out.subject.name == '*'
    assert out.relation == 'viewer'


# ---------------------------------------------------------------------------
# SchemaInfo
# ---------------------------------------------------------------------------

def test_schema_info_subject_wildcard_shapes():
    ruleset = parse_openfga_schema(WILDCARD_SCHEMA)
    info = ruleset.schema_info
    assert info is not None
    assert info.subject_wildcard_shapes == frozenset({('user', '...')})
    # no object wildcards declared
    assert info.object_wildcard_shapes == frozenset()


def test_schema_info_bridged_shapes(load_fga_schema):
    schema = load_fga_schema('wildcards.fga')
    ruleset = parse_openfga_schema(schema, object_wildcard_shapes={('folder', 'viewer'), ('document', 'viewer')})
    info = ruleset.schema_info

    # user:* -> (user,'...'); group:*#member -> (group,'member')
    assert info.subject_wildcard_shapes == frozenset({('user', '...'), ('group', 'member')})
    assert info.object_wildcard_shapes == frozenset({('folder', 'viewer'), ('document', 'viewer')})

    # bare shapes never need in-bridges; only the userset wildcard shape does.
    assert info.bridged_in_shapes == frozenset({('group', 'member')})
    # bridged-out == declared object-wildcard shapes.
    assert info.bridged_out_shapes == frozenset({('folder', 'viewer'), ('document', 'viewer')})


def test_schema_info_defaults_empty():
    info = SchemaInfo()
    assert info.subject_wildcard_shapes == frozenset()
    assert info.object_wildcard_shapes == frozenset()
    assert info.bridged_in_shapes == frozenset()
    assert info.bridged_out_shapes == frozenset()
