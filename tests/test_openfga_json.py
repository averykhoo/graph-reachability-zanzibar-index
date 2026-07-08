"""
S5 (connected-store spec §5-S5): the OpenFGA authorization-model JSON front-end.

JSON twins of the DSL fixtures must parse to IDENTICAL SchemaASTs -- one AST, two
front-ends; everything downstream untouched. Unsupported OpenFGA features are
rejected loudly. openfga_json_to_dsl gives the persistable schema source, so a
ConnectedStore is constructible straight from an OpenFGA model.
"""

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine

from connectedstore import ConnectedStore
from zanzibar_utils_v1 import (openfga_json_to_dsl, parse_openfga_json,
                               parse_schema_ast)


@pytest.mark.parametrize('pair', [
    ('wildcards.json', 'wildcards.fga'),
    ('boolean_wildcards.json', 'boolean_wildcards.fga'),
])
def test_json_twin_parses_to_identical_ast(load_fga_schema, pair):
    json_name, dsl_name = pair
    from_json = parse_openfga_json(load_fga_schema(json_name))
    from_dsl = parse_schema_ast(load_fga_schema(dsl_name))
    assert from_json == from_dsl


def test_json_to_dsl_round_trips(load_fga_schema):
    """JSON -> AST -> DSL -> AST is identity: the rendered DSL is a faithful,
    persistable schema source."""
    ast = parse_openfga_json(load_fga_schema('boolean_wildcards.json'))
    assert parse_schema_ast(openfga_json_to_dsl(load_fga_schema('boolean_wildcards.json'))) == ast


def test_connected_store_from_openfga_json(load_fga_schema):
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        dsl = openfga_json_to_dsl(load_fga_schema('boolean_wildcards.json'))
        cs = ConnectedStore(session, 'json-store', schema=dsl)
        cs.add_tuple('...', 'user', '*', 'public', 'doc', 'd1')
        cs.add_tuple('...', 'user', 'u1', 'blocked', 'doc', 'd1')
        assert cs.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1') is True
        assert cs.check('...', 'user', 'u1', 'viewer', 'doc', 'd1') is False


# ---------------------------------------------------------------------------
# Loud rejections
# ---------------------------------------------------------------------------

def _minimal(**overrides):
    model = {
        'schema_version': '1.1',
        'type_definitions': [
            {'type': 'user'},
            {'type': 'doc',
             'relations': {'viewer': {'this': {}}},
             'metadata': {'relations': {'viewer': {'directly_related_user_types': [
                 {'type': 'user'}]}}}},
        ],
    }
    model.update(overrides)
    return model


def test_rejects_wrong_schema_version():
    with pytest.raises(ValueError, match='schema_version'):
        parse_openfga_json(_minimal(schema_version='1.2'))


def test_rejects_model_conditions():
    with pytest.raises(ValueError, match='conditions'):
        parse_openfga_json(_minimal(conditions={'c1': {}}))


def test_rejects_conditional_type_restrictions():
    model = _minimal()
    model['type_definitions'][1]['metadata']['relations']['viewer'][
        'directly_related_user_types'][0]['condition'] = 'c1'
    with pytest.raises(ValueError, match='conditional'):
        parse_openfga_json(model)


def test_rejects_unknown_rewrite_operator():
    model = _minimal()
    model['type_definitions'][1]['relations']['viewer'] = {'exclusiveOr': {}}
    with pytest.raises(ValueError, match='unsupported rewrite operator'):
        parse_openfga_json(model)


def test_rejects_this_without_metadata():
    model = _minimal()
    del model['type_definitions'][1]['metadata']
    with pytest.raises(ValueError, match='directly_related_user_types'):
        parse_openfga_json(model)


def test_rejects_reserved_dot_in_relation_name():
    model = _minimal()
    model['type_definitions'][1]['relations']['viewer.0'] = {'this': {}}
    with pytest.raises(ValueError, match='reserved'):
        parse_openfga_json(model)


def test_rejects_duplicate_type_definitions():
    """S-6 parity with the DSL front-end: a duplicate type_definitions entry used
    to silently REPLACE the earlier one's relations, so a store bootstrapped from
    the JSON ran a different schema than the operator wrote (review 3)."""
    model = _minimal()
    model['type_definitions'].append({
        'type': 'doc',
        'relations': {'viewer': {'computedUserset': {'relation': 'editor'}}},
    })
    with pytest.raises(ValueError, match='duplicate type declaration'):
        parse_openfga_json(model)


def test_rejects_reserved_dot_in_referenced_names():
    """S-5 parity with the DSL front-end: the '.'-namespace lock covers REFERENCED
    names too. A directly_related_user_types entry (or computedUserset/TTU ref)
    naming '<relation>.<index>' was a foreign write handle into a compiled leaf
    family (review 3)."""
    restriction = _minimal()
    restriction['type_definitions'][1]['metadata']['relations']['viewer'][
        'directly_related_user_types'].append({'type': 'doc', 'relation': 'viewer.0'})
    with pytest.raises(ValueError, match='reserved leaf namespace'):
        parse_openfga_json(restriction)

    computed = _minimal()
    computed['type_definitions'][1]['relations']['owner'] = {
        'computedUserset': {'relation': 'viewer.0'}}
    with pytest.raises(ValueError, match='reserved leaf namespace'):
        parse_openfga_json(computed)


def test_accepts_json_string_input(load_fga_schema):
    text = load_fga_schema('wildcards.json')
    assert parse_openfga_json(text) == parse_openfga_json(json.loads(text))
