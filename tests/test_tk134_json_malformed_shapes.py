"""TK134: a malformed OpenFGA JSON model is refused with a ``ValueError`` naming the field.

Found 2026-10-08 by the TK127 adversarial review: `zanzibar.schema.parse_openfga_json` read
the model with ``.get`` / ``[...]`` and leaked a bare ``AttributeError`` / ``TypeError`` /
``KeyError`` that named no field. Measured first-hand 2026-10-13 before the fix: 23 of the 26
``MALFORMED`` cases below leaked one of the three (the row's four repros included), e.g.
``model-null -> AttributeError: 'NoneType' object has no attribute 'get'`` and
``type-definition-no-type -> KeyError: 'type'``. The other three already raised
``ValueError``, but ``metadata-array`` blamed the missing user types and ``user-type-number``
blamed the DSL rendering. The fix is the three `_validate_json_*` shape helpers in
`src/zanzibar/schema/json_frontend.py`.

SABOTAGE (2026-10-13, literal output): `_json_rewrite`'s ``computedUserset`` arm reverted to
``Computed(body['relation'])``, file restored and sha256-checked::

    FAILED tests/test_tk134_json_malformed_shapes.py::test_malformed_shape_is_a_value_error_naming_the_field[computed-no-relation]
    FAILED tests/test_tk134_json_malformed_shapes.py::test_malformed_shape_is_a_value_error_naming_the_field[computed-relation-number]
    2 failed, 28 passed in 0.46s
"""
from __future__ import annotations

import copy

import pytest

from zanzibar.schema import SchemaError, openfga_json_to_dsl, parse_openfga_json

USER = {'type': 'user'}


def _model(type_definitions):
    return {'schema_version': '1.1', 'type_definitions': type_definitions}


def _doc(rewrite, user_types=None):
    return {'type': 'doc', 'relations': {'viewer': rewrite},
            'metadata': {'relations': {'viewer': {'directly_related_user_types':
                                                  user_types if user_types is not None
                                                  else [{'type': 'user'}]}}}}


#: label -> (model, the message fragment that must name the field)
MALFORMED = {
    'model-null': (None, r'the model must be an object, got null'),
    'model-array': ([], r'the model must be an object, got an array'),
    'model-number': (3, r'the model must be an object, got a number'),
    'model-json-text-array': ('[]', r'the model must be an object, got an array'),
    'type-definitions-string': (_model('user'), r'type_definitions must be an array'),
    'type-definitions-object': (_model({'type': 'user'}), r'type_definitions must be an array'),
    'type-definition-no-type': (_model([{}]), r"type_definitions\[0\] has no 'type'"),
    'type-definition-string': (_model(['user']), r'type_definitions\[0\] must be an object'),
    'type-definition-null': (_model([None]), r'type_definitions\[0\] must be an object'),
    'type-number': (_model([{'type': 3}]), r"'type' must be a string, got a number"),
    'relations-array': (_model([USER, {'type': 'doc', 'relations': ['viewer']}]),
                        r'type doc: relations must be an object'),
    'metadata-array': (_model([USER, {'type': 'doc', 'relations': {'viewer': {'this': {}}},
                                      'metadata': []}]),
                       r'type doc: metadata must be an object'),
    'metadata-relations-array': (
        _model([USER, {'type': 'doc', 'relations': {'viewer': {'this': {}}},
                       'metadata': {'relations': []}}]),
        r'type doc: metadata.relations must be an object'),
    'relation-metadata-string': (
        _model([USER, {'type': 'doc', 'relations': {'viewer': {'this': {}}},
                       'metadata': {'relations': {'viewer': 'x'}}}]),
        r'relation doc#viewer: metadata must be an object'),
    'user-types-string': (_model([USER, _doc({'this': {}}, 'user')]),
                          r'directly_related_user_types must be an array'),
    'user-type-string': (_model([USER, _doc({'this': {}}, ['user'])]),
                         r'directly_related_user_types\[0\] must be an object'),
    'user-type-no-type': (_model([USER, _doc({'this': {}}, [{}])]),
                          r"directly_related_user_types\[0\] has no 'type'"),
    'user-type-number': (_model([USER, _doc({'this': {}}, [{'type': 1}])]),
                         r"directly_related_user_types\[0\]: 'type' must be a string"),
    'computed-no-relation': (_model([USER, _doc({'computedUserset': {}})]),
                             r"computedUserset has no 'relation'"),
    'computed-string': (_model([USER, _doc({'computedUserset': 'owner'})]),
                        r'computedUserset must be an object, got a string'),
    'computed-relation-number': (_model([USER, _doc({'computedUserset': {'relation': 5}})]),
                                 r"computedUserset: 'relation' must be a string"),
    'ttu-no-tupleset': (
        _model([USER, _doc({'tupleToUserset': {'computedUserset': {'relation': 'viewer'}}})]),
        r'tupleToUserset.tupleset must be an object, got null'),
    'ttu-null': (_model([USER, _doc({'tupleToUserset': None})]),
                 r'tupleToUserset must be an object, got null'),
    'union-no-child': (_model([USER, _doc({'union': {}})]), r'union.child must be an array'),
    'union-array': (_model([USER, _doc({'union': [{'this': {}}]})]),
                    r'union must be an object, got an array'),
    'difference-no-base': (_model([USER, _doc({'difference': {'subtract': {'this': {}}}})]),
                           r'difference.base must be an object, got null'),
}


@pytest.mark.parametrize('label', sorted(MALFORMED), ids=str)
def test_malformed_shape_is_a_value_error_naming_the_field(label):
    model, message = MALFORMED[label]
    for parse in (parse_openfga_json, openfga_json_to_dsl):
        with pytest.raises(ValueError, match=message) as info:
            parse(copy.deepcopy(model))
        # SchemaError exactly (a ValueError; a KeyError/TypeError is not): pin the class so
        # a future subclass with a different contract is a deliberate edit, not an accident.
        # Was ``ValueError`` exactly until TK123 item 6 (2026-10-15) made every schema-parser
        # refusal a ``SchemaError`` -- that deliberate edit.
        assert type(info.value) is SchemaError


def test_the_table_covers_the_rows_four_repros():
    """The TK134 row's own repros: a None model, a list model, ``type_definitions='user'``
    and ``type_definitions=[{}]``."""
    assert {'model-null', 'model-array', 'type-definitions-string',
            'type-definition-no-type'} <= set(MALFORMED)


def test_null_optional_fields_read_as_absent():
    """OpenFGA's DSL-to-JSON transformer (openfga/language, behind ``fga model transform``)
    emits ``"metadata": null`` for a type with no relations; the front end must keep
    accepting it. ``relations`` / ``directly_related_user_types`` as
    ``null`` read as absent too, which can only narrow the schema."""
    model = _model([
        {'type': 'user', 'relations': None, 'metadata': None},
        {'type': 'doc',
         'relations': {'owner': {'this': {}},
                       'viewer': {'computedUserset': {'relation': 'owner'}}},
         'metadata': {'relations': {
             'owner': {'directly_related_user_types': [{'type': 'user', 'relation': None}]},
             'viewer': None}}},
    ])
    assert set(parse_openfga_json(model)) == {('doc', 'owner'), ('doc', 'viewer')}


def test_this_with_null_user_types_is_still_refused_as_before():
    """``null`` user types read as absent, and ``this`` with none is the existing refusal."""
    with pytest.raises(ValueError, match=r'`this` requires directly_related_user_types'):
        parse_openfga_json(_model([USER, _doc({'this': {}}, None) | {
            'metadata': {'relations': {'viewer': {'directly_related_user_types': None}}}}]))


def test_unknown_operator_keeps_its_own_message():
    """The shape check runs only on KNOWN operators, so a misspelt one is still named."""
    with pytest.raises(ValueError, match=r"unsupported rewrite operator 'computedUserSet'"):
        parse_openfga_json(_model([USER, _doc({'computedUserSet': 'owner'})]))
