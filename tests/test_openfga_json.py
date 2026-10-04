"""
S5 (connected-store spec §5-S5): the OpenFGA authorization-model JSON front-end.

JSON twins of the DSL fixtures must parse to IDENTICAL SchemaASTs -- one AST, two
front-ends; everything downstream untouched. Unsupported OpenFGA features are
rejected loudly. openfga_json_to_dsl gives the persistable schema source, so a
ConnectedStore is constructible straight from an OpenFGA model.

TK115 (2026-10-04) added the fidelity pins at the bottom: the JSON front end must render the
schema it was given, or refuse. MUTATION SWEEP (2026-10-04, `.scratch/tk115/sweep.py`, each
anchor asserted, both files restored and sha256-checked; literal tails, run on this module +
`tests/test_refused_shape_comments.py`, baseline `37 passed`):

- M0 control, a pin claims ``{}`` is refused: RED, ``1 failed, 37 passed``, exactly
  ``test_rejects_wildcard_that_is_not_an_empty_object[value6]`` -- attribution works.
- M1 hook dropped / M2 hook keeps the first value: RED, ``3 failed, 34 passed`` each.
- M3 the pre-TK115 wildcard line: RED, ``6 failed, 31 passed``. M4 any dict accepted:
  ``1 failed`` ([value5]). M5 refuse only bools: ``4 failed``. M6 ``null`` read as a star:
  ``1 failed`` (the canonical-meaning pin).
- M7 round-trip step dropped: RED, ``3 failed, 34 passed``. M8 key sets only: ``1 failed``
  ([comma-splits-restriction], the only witness with equal keys). M9 an unparseable
  rendering accepted: ``1 failed`` ([V14-unparseable]).
- M10 ``lost`` ignored: INERT, ``37 passed`` -- REASONED unreachable alone: a key can only
  leave the re-parse by being re-homed under another type (which ADDS one) or by a parse
  error, so ``lost`` is diagnostic text, never the deciding field. Map:
  `docs/tk115-json-front-end-fidelity-2026-10-04.md` sec 4.
"""

import json
import re

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


# ---------------------------------------------------------------------------
# TK115: the JSON front end renders the schema it was given, or refuses
# ---------------------------------------------------------------------------
#
# Witnesses and the decision: docs/tk115-json-front-end-fidelity-2026-10-04.md (V-ids below
# are that doc's sec 1 table). Before TK115 every shape refused here was ACCEPTED and
# rendered a DIFFERENT schema than the JSON declared. Mutation sweep: the module docstring.

def _with_restriction(entry):
    model = _minimal()
    model['type_definitions'][1]['metadata']['relations']['viewer'][
        'directly_related_user_types'] = [entry]
    return model


@pytest.mark.parametrize('value', [False, 0, '', True, [], {'enabled': False}])
def test_rejects_wildcard_that_is_not_an_empty_object(value):
    """V2 / V12 / V13: ``"wildcard": false`` rendered ``define viewer: [user:*]`` -- a PUBLIC
    grant from a value that reads "not a wildcard"."""
    with pytest.raises(ValueError, match='"wildcard" must be'):
        parse_openfga_json(_with_restriction({'type': 'user', 'wildcard': value}))


def test_wildcard_empty_object_and_null_keep_their_canonical_meaning():
    """V10 / V11, the positive half: the refusal above must not eat canonical OpenFGA."""
    star = parse_openfga_json(_with_restriction({'type': 'user', 'wildcard': {}}))
    assert openfga_json_to_dsl(_with_restriction({'type': 'user', 'wildcard': {}})) \
        .splitlines()[2].strip() == 'define viewer: [user:*]'
    assert star[('doc', 'viewer')].restrictions[0].wildcard is True
    plain = parse_openfga_json(_with_restriction({'type': 'user', 'wildcard': None}))
    assert plain[('doc', 'viewer')].restrictions[0].wildcard is False


_DUP_RELATION = (
    '{"schema_version": "1.1", "type_definitions": [{"type": "user"}, {"type": "doc", '
    '"relations": {"viewer": {"this": {}}, "viewer": {"computedUserset": {"relation": '
    '"owner"}}, "owner": {"this": {}}}, "metadata": {"relations": {"viewer": '
    '{"directly_related_user_types": [{"type": "user"}]}, "owner": '
    '{"directly_related_user_types": [{"type": "user"}]}}}}]}')
_DUP_TOP_LEVEL = ('{"schema_version": "1.0", "schema_version": "1.1", '
                  '"type_definitions": [{"type": "user"}]}')
_DUP_DEEP = (
    '{"schema_version": "1.1", "type_definitions": [{"type": "user"}, {"type": "doc", '
    '"relations": {"viewer": {"this": {}}}, "metadata": {"relations": {"viewer": '
    '{"directly_related_user_types": [{"type": "group", "type": "user"}]}}}}]}')


@pytest.mark.parametrize('text', [_DUP_RELATION, _DUP_TOP_LEVEL, _DUP_DEEP],
                         ids=['V3-relation', 'V17-top-level', 'restriction-entry'])
def test_rejects_duplicate_json_keys_at_any_depth(text):
    """V3 / V17: ``json.loads`` keeps the LAST value silently, so a second ``"viewer"`` won
    and a ``"schema_version": "1.0"`` vanished. Each of these round-trips EQUAL, which is
    why the round-trip check alone could not catch them (skeptic, 2026-10-03c)."""
    with pytest.raises(ValueError, match='duplicate key'):
        parse_openfga_json(text)


@pytest.mark.parametrize('subject_type, shape', [
    ('user]' + chr(10) + '    define secret: [user', 'parses to a different schema'),   # V9: adds a key
    ('user,group', re.escape("parses to a different schema (added [], lost [], changed "
                             "[('doc', 'viewer')])")),   # SAME keys, another expression
    ('us er', 'does not parse'),          # V14: the DSL parser refuses the rendering
], ids=['V9-injects-relation', 'comma-splits-restriction', 'V14-unparseable'])
def test_rejects_model_whose_dsl_rendering_is_a_different_schema(subject_type, shape):
    """A bare restriction type is not a declared name (P23 does not see it) and ASK-1 does
    not check bare restriction types, so before TK115 V9 rendered a second relation
    ``secret`` that a ConnectedStore would then admit writes on. The comma case keeps the
    key set equal, so it pins that the comparison is over EXPRESSIONS, not keys."""
    with pytest.raises(ValueError, match=f'OpenFGA JSON: its DSL rendering {shape}'):
        parse_openfga_json(_with_restriction({'type': subject_type}))


@pytest.mark.parametrize('where', ['type', 'relation'])
def test_rejects_newline_in_a_declared_name(where):
    """V1 / V4 (the original H5 witnesses), refused since P23 by `_validate_declared_name`;
    pinned here because the P23 parity test does not include a newline."""
    model = _minimal()
    if where == 'type':
        model['type_definitions'][1]['type'] = 'doc' + chr(10) + 'type folder2'
    else:
        model['type_definitions'][1]['relations']['x: [user]' + chr(10) + '    define s'] = {
            'computedUserset': {'relation': 'viewer'}}
    with pytest.raises(ValueError, match=f'declared {where} name'):
        parse_openfga_json(model)
