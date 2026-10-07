"""TK124 -- a schema that declares no type is refused at PARSE time, before a store persists it.

Property guarded
----------------
A schema text with no ``type`` line -- ``""``, whitespace, comments only, or only the
``model`` / ``schema 1.1`` header -- is refused by BOTH DSL parsers (product
``src/zanzibar/schema/parser.py::_validate_declares_a_type`` and its independent twin
``tests/oracle.py::_validate_declares_a_type``), checked and unchecked, and an OpenFGA JSON
model with no ``type_definitions`` is refused by
``src/zanzibar/schema/json_frontend.py::_validate_json_declares_a_type``. Because
``connectedstore/schema_io.py::save_schema`` parses before it adds the ``SchemaRecord``, the
refusal persists nothing, and the same store id can then be bootstrapped with a real schema.

A schema that declares types but no relation anywhere (``type user``) is refused too, by the
second guard in the same two functions (and ``json_frontend.py::_validate_json_declares_a_relation``
for JSON). That half is the TK127 review follow-up (2026-10-08, below).

Deliberately NOT refused (accept controls below; the P23 parity family pins the same):
a relationless type beside a type that declares a relation, and a schema without the
``model`` / ``schema 1.1`` header.

TK127 follow-up (2026-10-08). Reviewer probe ``.scratch/tk127-2026-10-08/tmp-small-fixes/
probe_tk124.py``, re-run first-hand on the first TK124 fix (gitignored; this is the record)::

    type_only          BOOTSTRAPPED -> BRICKED: SchemaMismatch: explicit schema for store 'x'
                       disagrees with its persisted schema; schemas are static (wri...
    two_types_no_rel   BOOTSTRAPPED -> BRICKED: SchemaMismatch: ...

The new cases written first, on that tree: ``27 failed, 118 passed, 1 deselected in 1.23s``
(19 x ``DID NOT RAISE ValueError`` across both parsers and ConnectedStore, 6 x the same in P23,
2 x the JSON message "Regex pattern did not match" -- it said "DSL rendering does not
parse (schema declares no type ...)"). Sabotage (``.scratch/.../fix-tk127-sab124.py``, each new
``if not ast:`` -> ``if False:``, anchor asserted, sha256-restored; this module + P23 +
refused-shape), literal summary lines::

    S1 product guard off   17 failed, 157 passed in 3.63s
    S2 oracle guard off     8 failed, 166 passed in 3.77s
    S3 JSON guard off       2 failed, 172 passed in 3.59s

Pre-fix evidence (0.0.2 install trial, B2, ``docs/pypi-trial-0.0.2-2026-10-07.md`` sec 1;
re-run first-hand 2026-10-08 on HEAD 7296eb1, ``.scratch/tk127-2026-10-08/impl-tk124-probes/
probe1.py``, gitignored -- this docstring is the tracked record)::

    empty        prod=ACCEPT keys=0 | prod_unchecked=ACCEPT keys=0 | oracle=ACCEPT keys=0 | ...
    header-only  prod=ACCEPT keys=0 | ...
    json-empty-type_definitions  json=ACCEPT keys=0
    ConnectedStore(schema="") constructed OK
    SchemaRecord row for x: created_at=... store_id='x' schema_text='' object_wildcard_shapes='[]'

SABOTAGE (2026-10-08, ``.scratch/tk127-2026-10-08/impl-tk124-probes/sabotage.py``: each guard's
``if`` replaced by ``if False:``, anchor count asserted == 1, file restored byte-for-byte and
sha256-checked; targets this module + ``test_p23_parser_refusal_parity.py`` +
``test_refused_shape_comments.py``), literal summary lines::

    S1 product guard off   32 failed, 117 passed in 2.32s
       (21 product-parse cases, 3 P23 product cases, the 7 ConnectedStore cases, the JSON
        round-trip case)
    S2 oracle guard off    17 failed, 132 passed in 2.57s   (14 oracle cases, 3 P23 oracle)
    S3 JSON guard off       4 failed, 145 passed in 2.93s
       FAILED ...::test_json_front_end_refuses_a_model_with_no_type[absent] (also
       [empty-list], [null], [json-text]) -- the model was still refused, but by the
       round trip with the misleading "DSL rendering does not parse"; the named message
       is what this pins
    S4 all three off (= pre-fix behaviour)   53 failed, 96 passed in 2.37s

Census (2026-10-08, a recorder plugin wrapping both parsers' refusal and the product's empty-AST
path, full ``tests/`` and ``formal/conformance/`` run on the fixed tree): no pre-existing test
parses a zero-type schema, and none parses a schema whose types declare no relation.
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tests import oracle as oracle_mod
from zanzibar.connectedstore import ConnectedStore
from zanzibar.connectedstore.models import SchemaRecord, TupleLog
from zanzibar.schema import (
    _parse_schema_ast_unchecked, openfga_json_to_dsl, parse_openfga_json,
    parse_openfga_schema, parse_schema_ast,
)

#: Every shape of "declares no type" the 2026-10-08 probe tried. Each must be refused.
NO_TYPE = {
    'empty': '',
    'whitespace': '   \n\t\n  ',
    'newlines': '\n\n\n',
    'comments-only': '# a schema file\n  # with nothing in it\n',
    'header-only': 'model\n  schema 1.1\n',
    'header-and-relations-word': 'model\n  schema 1.1\nrelations\n',
    'header-and-comment': 'model\n  # TODO\n  schema 1.1\n',
}

#: Types, but no relation anywhere (TK127 follow-up, 2026-10-08). The AST is keyed by
#: ``(type, relation)``, so these parse to the same empty AST as ``""`` and bricked a store
#: id the same way. Each must be refused, with its own message.
NO_RELATION = {
    'one-type-no-relation': 'model\n  schema 1.1\ntype user\n',
    'types-no-relations-no-header': 'type user\ntype doc\n',
    'types-with-empty-relations-blocks': 'type user\n  relations\ntype doc\n  relations\n',
}

#: Accept controls: the near-misses that must still parse in both parsers.
REAL = ('model\n  schema 1.1\ntype user\ntype doc\n  relations\n'
        '    define viewer: [user]\n')
STILL_ACCEPTED = {
    'no-header': 'type user\ntype doc\n  relations\n    define viewer: [user]\n',
    'real': REAL,
    # one relation anywhere is enough; relationless types BESIDE it stay legal
    'one-relation-among-relationless-types': ('type user\ntype team\ntype doc\n'
                                              '  relations\n    define viewer: [user]\n'),
}

_MSG = r'declares no type'
_MSG_REL = r'declares no relation'


@pytest.mark.parametrize('label', sorted(NO_TYPE))
@pytest.mark.parametrize('parse', [
    parse_schema_ast, _parse_schema_ast_unchecked,
    lambda t: parse_openfga_schema(t),
], ids=['prod-checked', 'prod-unchecked', 'prod-compile'])
def test_production_refuses_a_schema_with_no_type(parse, label):
    with pytest.raises(ValueError, match=_MSG):
        parse(NO_TYPE[label])


@pytest.mark.parametrize('label', sorted(NO_TYPE))
@pytest.mark.parametrize('parse', [
    oracle_mod.parse_schema_ast, oracle_mod.parse_schema_ast_unchecked,
], ids=['oracle-checked', 'oracle-unchecked'])
def test_oracle_refuses_a_schema_with_no_type_independently(parse, label):
    with pytest.raises(ValueError, match=_MSG):
        parse(NO_TYPE[label])


@pytest.mark.parametrize('label', sorted(NO_RELATION))
@pytest.mark.parametrize('parse', [
    parse_schema_ast, _parse_schema_ast_unchecked,
    lambda t: parse_openfga_schema(t),
    oracle_mod.parse_schema_ast, oracle_mod.parse_schema_ast_unchecked,
], ids=['prod-checked', 'prod-unchecked', 'prod-compile', 'oracle-checked',
        'oracle-unchecked'])
def test_both_parsers_refuse_a_schema_whose_types_declare_no_relation(parse, label):
    with pytest.raises(ValueError, match=_MSG_REL):
        parse(NO_RELATION[label])


@pytest.mark.parametrize('label', sorted(STILL_ACCEPTED))
def test_both_parsers_still_accept_a_relation_and_no_header(label):
    text = STILL_ACCEPTED[label]
    assert set(parse_schema_ast(text)) == set(oracle_mod.parse_schema_ast(text))
    assert set(_parse_schema_ast_unchecked(text)) == set(
        oracle_mod.parse_schema_ast_unchecked(text))


# --------------------------------------------------------------------------- #
# JSON front end
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('model', [
    {'schema_version': '1.1'},
    {'schema_version': '1.1', 'type_definitions': []},
    {'schema_version': '1.1', 'type_definitions': None},
    '{"schema_version": "1.1", "type_definitions": []}',
], ids=['absent', 'empty-list', 'null', 'json-text'])
def test_json_front_end_refuses_a_model_with_no_type(model):
    with pytest.raises(ValueError, match=r'the model declares no type'):
        parse_openfga_json(model)
    with pytest.raises(ValueError, match=r'the model declares no type'):
        openfga_json_to_dsl(model)


@pytest.mark.parametrize('model', [
    {'schema_version': '1.1', 'type_definitions': [{'type': 'user'}]},
    {'schema_version': '1.1', 'type_definitions': [
        {'type': 'user'}, {'type': 'doc', 'relations': {}}]},
], ids=['one-type', 'empty-relations'])
def test_json_types_without_relations_are_refused_with_their_own_message(model):
    """At HEAD 7296eb1 this was accepted and `openfga_json_to_dsl` returned ``''`` -- the
    brick, reached through JSON. The first TK124 fix refused it only through the round trip,
    with the misleading "DSL rendering does not parse (schema declares no type ...)"; the
    TK127 follow-up (2026-10-08) names the real shape."""
    with pytest.raises(ValueError, match=r'the model declares no relation'):
        parse_openfga_json(model)
    with pytest.raises(ValueError, match=r'the model declares no relation'):
        openfga_json_to_dsl(model)


def test_json_control_accepts():
    model = {'schema_version': '1.1', 'type_definitions': [
        {'type': 'user'},
        {'type': 'doc', 'relations': {'viewer': {'this': {}}},
         'metadata': {'relations': {'viewer': {
             'directly_related_user_types': [{'type': 'user'}]}}}}]}
    assert set(parse_openfga_json(model)) == {('doc', 'viewer')}


# --------------------------------------------------------------------------- #
# The shipped consequence: nothing persists, and the store id stays usable
# --------------------------------------------------------------------------- #

def _engine(tmp_path):
    engine = create_engine(f'sqlite:///{(tmp_path / "tk124.db").as_posix()}')
    SQLModel.metadata.create_all(engine)
    return engine


_BRICKS = {**{k: (NO_TYPE[k], _MSG) for k in ('empty', 'comments-only', 'header-only')},
           **{k: (v, _MSG_REL) for k, v in NO_RELATION.items()}}


@pytest.mark.parametrize('sync', [True, False], ids=['sync', 'async'])
@pytest.mark.parametrize('label', sorted(_BRICKS))
def test_connected_store_refuses_before_persisting_and_the_id_stays_usable(
        tmp_path, label, sync):
    text, msg = _BRICKS[label]
    engine = _engine(tmp_path)
    with Session(engine) as s:
        with pytest.raises(ValueError, match=msg):
            ConnectedStore(s, 'x', schema=text, sync=sync)
        # never even flushed into this session's transaction
        assert s.get(SchemaRecord, 'x') is None
        s.rollback()
    # nothing committed: a fresh connection sees no schema row and no log row
    with Session(engine) as s:
        assert s.exec(select(SchemaRecord)).all() == []
        assert s.exec(select(TupleLog)).all() == []
    # the same store id bootstraps with the intended schema and serves writes
    with Session(engine) as s:
        cs = ConnectedStore(s, 'x', schema=REAL, sync=sync)
        cs.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
        if not sync:
            cs.catch_up()
        assert cs.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True
        assert cs.check('...', 'user', 'bob', 'viewer', 'doc', 'd1') is False
    # and it reopens (persisted schema re-parsed) without a schema argument
    with Session(engine) as s:
        cs = ConnectedStore(s, 'x', sync=sync)
        assert cs.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True


def test_same_session_can_bootstrap_after_the_refusal(tmp_path):
    """The refused constructor leaves the session usable after a rollback."""
    engine = _engine(tmp_path)
    with Session(engine) as s:
        with pytest.raises(ValueError, match=_MSG):
            ConnectedStore(s, 'x', schema='')
        s.rollback()
        cs = ConnectedStore(s, 'x', schema=REAL)
        cs.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
        assert cs.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True
