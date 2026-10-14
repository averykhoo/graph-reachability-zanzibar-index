"""TK137 (2026-10-14) -- DSL shapes OpenFGA refuses, refused here too, in BOTH parsers.

Map, census and decisions: `docs/tk137-dsl-openfga-refusals-2026-10-14.md` (scout +
challenge sections). Parity of the refusals between the product parser and the oracle is
pinned by `tests/test_p23_parser_refusal_parity.py`; THIS module pins each check itself, with
the message it must give, plus the unparser and JSON front-end changes that keep every new
refusal unreachable from `unparse_schema_ast`.

Refused since TK137:

- **H1** a ``schema`` line naming any version but ``1.1`` (the version used to be ignored).
- **H2** a ``model`` / ``schema 1.1`` / ``relations`` line with more words on it, a trailing
  comment included. ``relations define viewer: [user]`` used to parse and DROP ``viewer``.
- **S7** ``but not`` sharing a parenthesis level with ``or`` / ``and`` / a second ``but not``.
  ``a but not b or c`` used to mean ``a but not (b or c)``.
- **S8** a restriction naming a type no ``type`` line declares (``[usr]``, ``[usr:*]``,
  ``[usr#...]``), in both checked parsers and the JSON front end. It extends ASK-1.
- **S9** (messages only, no new refusal) ``module``, ``extend type``, ``condition`` blocks and
  ``[user with cond]`` now name the OpenFGA feature instead of a generic error.

Kept on purpose, as documented extensions of OpenFGA's DSL syntax (they are legal OpenFGA
MODELS in JSON form): two direct blocks (``[user] or [doc]``), a direct block not first
(``a but not [user]``), no ``model`` / ``schema`` header, ``define`` with no ``relations``
line, a ``relations`` line before any ``type``, a header after a ``type`` block, and a
forward reference to a type declared further down.

SABOTAGE (2026-10-14, TK137 builder, gitignored `.scratch/now-next/probes/build-TK137/
sabotage.py`, so this docstring is the tracked record). Each mutation is one asserted-unique
anchor in one file, run against this module (44 tests), the file restored byte-for-byte and
sha256-checked afterwards. Literal pytest tails; every one RED, and each failing set is
exactly the tests that name the mutated check:

- SA1  parser.py H1 condition -> ``False``: ``5 failed, 39 passed`` (the five
  ``test_schema_header_must_be_1_1`` ids).
- SA2  parser.py H2 condition -> ``False``: ``4 failed, 40 passed`` (the relations test, the
  three ``test_header_line_with_extra_words_is_refused`` ids).
- SA3  parser.py reject call after the SUBTRAHEND -> ``pass``: ``3 failed, 41 passed``
  (``[then-or]``, ``[then-and]``, ``[twice]``; the generic "unexpected token" still refused
  them, so only the message assertion sees this, challenge C1).
- SA4  parser.py reject call after the CHAIN -> ``pass``: ``2 failed, 42 passed``
  (``[or-then]``, ``[and-then]``).
- SA5  parser.py `parse_schema_ast`'s S8 call deleted: ``5 failed, 39 passed`` (four
  ``test_undeclared_restriction_type_is_refused`` ids + the ConnectedStore test).
- SA6  json_frontend.py S8 call deleted: ``1 failed, 43 passed``
  (`test_json_undeclared_restriction_type_is_refused`).
- SA7  unparse.py relationless ``type`` emission skipped: ``8 failed, 36 passed`` (the
  unparse tests, both round-trip-guard tests and the JSON test: every rendering of
  ``[user]`` is then refused by S8 on re-parse).
- SA8  unparse.py pre-TK137 ``_chain`` operand rendering restored: ``2 failed, 42 passed``
  (``[union-base]``, ``[intersection-subtrahend]``).
- SA9  json_frontend.py `_validate_json_round_trip` made a no-op: ``2 failed, 42 passed``.
- SA10 json_frontend.py the `_validate_json_round_trip(ast)` call deleted: ``1 failed, 43
  passed`` (`test_parse_openfga_json_still_calls_the_round_trip_guard`, challenge C3).
- SA11 parser.py ``'module'`` entry of `_UNSUPPORTED_OPENFGA_HEADS` deleted: ``1 failed, 43
  passed`` (``[module]``).
- SA12a oracle.py S8 call deleted: ``4 failed, 40 passed``. SA12b oracle.py reject call after
  the subtrahend -> ``pass``: ``3 failed, 41 passed``.
- SA13 CONTROL, parser.py `_parse_expr` refuses every ``but not``: ``11 failed, 33 passed``
  (all six parenthesised controls, ``[direct-not-first]``, the four unparse round trips).
- SA14 oracle.py `_validate_header_line` call deleted: ``9 failed, 35 passed``.
- SA15 parser.py `_reject_conditional_restriction` call deleted: ``1 failed, 43 passed``
  (``[with]``).
"""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

from tests import oracle as oracle_mod
from zanzibar.connectedstore import ConnectedStore
from zanzibar.schema import (Computed, Direct, Exclusion, Intersection, Restriction, TTU, Union,
                             _parse_schema_ast_unchecked, parse_openfga_json,
                             parse_openfga_schema, parse_schema_ast, unparse_schema_ast)
from zanzibar.schema import json_frontend
from zanzibar.schema.json_frontend import _validate_json_round_trip

_HEADER = "model\n  schema 1.1\n"
_TYPES = ("type user\ntype doc\n  relations\n"
          "    define a: [user]\n    define b: [user]\n    define c: [user]\n")
_SCHEMA = _HEADER + _TYPES

USER = Restriction('user', '...', False)
A, B, C = Computed('a'), Computed('b'), Computed('c')
_ABC = {('doc', 'a'): Direct((USER,)), ('doc', 'b'): Direct((USER,)),
        ('doc', 'c'): Direct((USER,))}


def _x(body: str, schema: str = _SCHEMA) -> str:
    return schema + f"    define x: {body}\n"


def _oracle_shape(expr):
    """A product `Expr` in the oracle's structural classes, so one expected AST checks both
    parsers. Test-side code: the oracle itself still imports nothing from the package."""
    if isinstance(expr, Direct):
        return oracle_mod.ODirect(tuple((r.type, r.predicate, r.wildcard)
                                        for r in expr.restrictions))
    if isinstance(expr, Computed):
        return oracle_mod.OComputed(expr.relation)
    if isinstance(expr, TTU):
        return oracle_mod.OTTU(expr.target_rel, expr.tupleset_rel)
    if isinstance(expr, Union):
        return oracle_mod.OUnion(tuple(_oracle_shape(c) for c in expr.children))
    if isinstance(expr, Intersection):
        return oracle_mod.OIntersection(tuple(_oracle_shape(c) for c in expr.children))
    assert isinstance(expr, Exclusion), expr
    return oracle_mod.OExclusion(_oracle_shape(expr.base), _oracle_shape(expr.subtract))


def _assert_both_parse_to(text: str, expected: dict) -> None:
    assert parse_schema_ast(text) == expected
    assert oracle_mod.parse_schema_ast(text) == {k: _oracle_shape(v) for k, v in expected.items()}


def _refused_by_both(text: str, product_match: str, oracle_match: str) -> None:
    with pytest.raises(ValueError, match=product_match):
        parse_schema_ast(text)
    with pytest.raises(ValueError, match=oracle_match):
        oracle_mod.parse_schema_ast(text)


# --------------------------------------------------------------------------- #
# H1 / H2 -- header lines
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('line', ['schema 1.2', 'schema 9.9', 'schema 1.0', 'schema abc',
                                  'schema'])
def test_schema_header_must_be_1_1(line):
    """H1. Before TK137 every one of these parsed, the version IGNORED (plan sec 2, probe
    rows S1a-S1e). OpenFGA accepts ``1.2`` too (modular models); this library implements
    only 1.1, so it refuses 1.2 rather than read it as 1.1.

    Sabotage SA1 (product H1 condition made ``False``): RED, the five product halves here
    (module docstring)."""
    text = _SCHEMA.replace('schema 1.1', line)
    _refused_by_both(text, r"only 'schema 1\.1' is implemented", 'unsupported schema version')


def test_relations_line_with_a_define_is_refused_not_dropped():
    """H2, the silent drop. Pre-fix probe (scout, plan sec 2, literal)::

        S3b  'relations define viewer: [user]', then '  relations' / 'define owner: [user]'
             -> {('doc', 'owner'): Direct((R(user),))}          # doc#viewer IS GONE, no error

    Sabotage SA2 (product H2 condition made ``False``): RED here and in
    `test_header_line_with_extra_words_is_refused` (module docstring)."""
    text = (_HEADER + "type user\ntype doc\n  relations define viewer: [user]\n  relations\n"
            "    define owner: [user]\n")
    _refused_by_both(text, "'relations' line with extra words", 'header line with extra words')


@pytest.mark.parametrize('lines', [
    ('model x', 'schema 1.1'),
    ('model # people', 'schema 1.1'),        # a trailing comment is refused (challenge C5)
    ('model', 'schema 1.1 # c'),
], ids=['model-junk', 'model-comment', 'schema-comment'])
def test_header_line_with_extra_words_is_refused(lines):
    """H2 on the header lines. A trailing comment on a ``model`` / ``schema`` / ``relations``
    line is refused like any other extra word, consistently with a trailing comment on a
    ``define`` line (refused before TK137); the INSTEAD is a comment on its own line."""
    text = f"{lines[0]}\n  {lines[1]}\n" + _TYPES
    _refused_by_both(text, 'line with extra words', 'header line with extra words')
    relations_comment = _HEADER + "type user\ntype doc\n  relations # c\n    define v: [user]\n"
    _refused_by_both(relations_comment, "'relations' line with extra words",
                     'header line with extra words')


# --------------------------------------------------------------------------- #
# S7 -- but not beside another operator
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('body', [
    '[user] or a but not b',
    'a but not b or c',
    'a and b but not c',
    'a but not b and c',
    'a but not b but not c',
], ids=['or-then', 'then-or', 'and-then', 'then-and', 'twice'])
def test_but_not_mixed_with_or_and_is_refused(body):
    """S7. Pre-fix ASTs (scout probe, plan sec 2, literal): ``a but not b or c`` ->
    ``Exclusion(base=Computed('a'), subtract=Union((Computed('b'), Computed('c'))))``, which
    reads as ``(a but not b) or c`` and grants differently.

    The restructured grammar refuses these shapes STRUCTURALLY (challenge C1: with no
    `_reject_unparenthesised_but_not` call at all they still fail, as "unexpected token"), so
    this test asserts the MESSAGE in both parsers: a bare ``pytest.raises`` would fail by
    passing.

    Sabotage SA3 (product: the reject call after the SUBTRAHEND deleted): RED for then-or,
    then-and, twice. SA4 (the call after the CHAIN deleted): RED for or-then, and-then.
    SA12b (oracle: its call after the subtrahend deleted): RED for the oracle half of the same
    three (module docstring)."""
    _refused_by_both(_x(body), 'parenthesise the intended reading',
                     'parenthesise the intended reading')


@pytest.mark.parametrize('body, expected', [
    ('(a or b) but not c', Exclusion(Union((A, B)), C)),
    ('a but not (b or c)', Exclusion(A, Union((B, C)))),
    ('([user] or a) but not b', Exclusion(Union((Direct((USER,)), A)), B)),
    ('(a but not b) or c', Union((Exclusion(A, B), C))),
    ('(a and b) but not (b or c)', Exclusion(Intersection((A, B)), Union((B, C)))),
    ('a but not b', Exclusion(A, B)),
], ids=['base-union', 'subtrahend-union', 'direct-in-base', 'exclusion-in-or', 'both-chains',
        'plain'])
def test_parenthesised_but_not_still_parses(body, expected):
    """The control for S7: every parenthesised reading parses to the expected FULL AST, in
    the product AND (structurally) the oracle (challenge C6: a key-only comparison would miss
    a grammar regression that keeps the keys).

    Sabotage SA13 (product: `_parse_expr` refuses every ``but not``): RED here, all six
    (module docstring)."""
    _assert_both_parse_to(_x(body), {**_ABC, ('doc', 'x'): expected})


# --------------------------------------------------------------------------- #
# The extensions kept on purpose
# --------------------------------------------------------------------------- #

_DIRECT_X = {('doc', 'x'): Direct((USER,))}


@pytest.mark.parametrize('text, expected', [
    (_x('[user] or [doc]'),
     {**_ABC, ('doc', 'x'): Union((Direct((USER,)), Direct((Restriction('doc', '...', False),))))}),
    (_x('a but not [user]'), {**_ABC, ('doc', 'x'): Exclusion(A, Direct((USER,)))}),
    ("type user\ntype doc\n  relations\n    define x: [user]\n", _DIRECT_X),
    (_HEADER + "type user\ntype doc\n    define x: [user]\n", _DIRECT_X),
    ("relations\ntype user\ntype doc\n  relations\n    define x: [user]\n", _DIRECT_X),
    ("type user\ntype doc\n  relations\n    define x: [user]\n" + _HEADER, _DIRECT_X),
    ("type doc\n  relations\n    define x: [user]\ntype user\n", _DIRECT_X),
], ids=['two-directs', 'direct-not-first', 'no-header', 'define-without-relations-line',
        'relations-line-before-any-type', 'header-after-types', 'forward-reference'])
def test_kept_extensions_still_parse(text, expected):
    """Kept extensions (decided on the TK137 row): both parsers accept each with the expected
    full AST. ``forward-reference`` matters most (challenge C4): the S8 check must run on the
    FINAL declared set, or a schema declaring ``type user`` last would be refused, and a
    per-``define`` check would pass every other test."""
    _assert_both_parse_to(text, expected)


# --------------------------------------------------------------------------- #
# S8 -- a restriction to an undeclared type
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('restriction', ['[usr]', '[usr:*]', '[usr#...]', '[user, usr]'],
                         ids=['bare', 'wildcard', 'ellipsis', 'second-entry'])
def test_undeclared_restriction_type_is_refused(restriction):
    """S8. Before TK137 all four parsed, and ``[usr]`` then ADMITTED a ``usr:x`` write with
    check True (0.0.4 install trial p16, TK137 row log 2026-10-13c). ``[usr#...]`` is a BARE
    restriction (`predicate='...'`), so ASK-1 never saw it (challenge C12).

    The unchecked parse (non-raising reports) still accepts it, as it accepts ASK-1's
    dangling references.

    Sabotage SA5 (product: the `_validate_restriction_types_declared` call in
    `parse_schema_ast` deleted): RED, the product halves here and the ConnectedStore test.
    SA12a (oracle: its call deleted): RED, the oracle halves (module docstring)."""
    text = _SCHEMA + f"    define x: {restriction}\n"
    _refused_by_both(text, "names an undeclared type 'usr'", "undeclared type 'usr'")
    assert ('doc', 'x') in _parse_schema_ast_unchecked(text)
    assert ('doc', 'x') in oracle_mod.parse_schema_ast_unchecked(text)


def test_connected_store_refuses_a_typo_schema_up_front():
    """The shipped consequence. Before TK137, ``ConnectedStore(schema=<[usr] typo>)`` was
    built, a ``usr:x`` write was admitted and check said True (TK137 row log 2026-10-13c,
    p16). Now construction refuses the schema, naming the type, and compilation does too."""
    typo = _SCHEMA + "    define viewer: [usr]\n"
    with pytest.raises(ValueError, match="undeclared type 'usr'"):
        parse_openfga_schema(typo)
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        with pytest.raises(ValueError, match="undeclared type 'usr'"):
            ConnectedStore(session, 'tk137-typo', schema=typo)


def _json_model(restricted_type: str, declare_user: bool = True) -> dict:
    types = [{'type': 'user'}] if declare_user else []
    return {
        'schema_version': '1.1',
        'type_definitions': types + [
            {'type': 'doc',
             'relations': {'viewer': {'this': {}}},
             'metadata': {'relations': {'viewer': {
                 'directly_related_user_types': [{'type': restricted_type}]}}}},
        ],
    }


def test_json_undeclared_restriction_type_is_refused():
    """S8 in the JSON front end, checked BEFORE the round trip, so the message names the
    type rather than "its DSL rendering ...". OpenFGA refuses such a model too
    (`typesystem.go::validateTypeRestrictions`).

    Sabotage SA6 (the call in `json_frontend.py::parse_openfga_json` deleted): RED here (the
    round trip then refuses it with "its DSL rendering does not parse") (module docstring)."""
    with pytest.raises(ValueError, match="doc#viewer: restriction \\[usr\\] names an undeclared "
                                         "type 'usr'"):
        parse_openfga_json(_json_model('usr'))
    with pytest.raises(ValueError, match="names an undeclared type 'user'"):
        parse_openfga_json(_json_model('user', declare_user=False))
    assert set(parse_openfga_json(_json_model('user'))) == {('doc', 'viewer')}


# --------------------------------------------------------------------------- #
# The unparser keeps every new refusal unreachable
# --------------------------------------------------------------------------- #

def test_unparse_declares_referenced_types():
    """Step 2. The unparser declares every restriction type that keys no relation, FIRST and
    sorted, so its output passes S8 and still round-trips (a relation-less type is not an AST
    key). Before TK137 it emitted no ``type user`` line, which S8 now refuses.

    Sabotage SA7 (the relationless emission skipped): RED here (module docstring).
    Instrument check (2026-10-14, review fix): with the oracle made to drop ``:*`` (its
    restriction parse sets ``wild`` False), this test is ``rc=1 | 1 failed``; the earlier
    keys-only oracle assertion was ``rc=0 | 1 passed`` under the same break."""
    ast = {('doc', 'viewer'): Direct((USER, Restriction('group', '...', True))),
           ('doc', 'owner'): Direct((Restriction('doc', 'viewer', False),))}
    text = unparse_schema_ast(ast)
    assert text.splitlines()[:2] == ['type group', 'type user']
    # Full AST on BOTH parsers (TK137 review fix, 2026-10-14): a keys-only oracle check
    # would pass an oracle that parsed the restrictions wrongly.
    _assert_both_parse_to(text, ast)


@pytest.mark.parametrize('expr, rendered', [
    (Exclusion(Union((A, B)), C), '(a or b) but not c'),
    (Exclusion(A, Intersection((B, C))), 'a but not (b and c)'),
    (Exclusion(Exclusion(A, B), C), '(a but not b) but not c'),
    (Exclusion(A, B), 'a but not b'),
], ids=['union-base', 'intersection-subtrahend', 'exclusion-base', 'leaves'])
def test_unparse_parenthesises_but_not_operands(expr, rendered):
    """Step 1. Both operands of ``but not`` render as units. Before TK137 the base rendered
    bare unless it was itself an exclusion, so ``Exclusion(Union(a, b), c)`` became
    ``a or b but not c``, which S7 now refuses.

    Sabotage SA8 (the pre-TK137 ``_chain`` rendering restored for both operands): RED for
    union-base and intersection-subtrahend (module docstring)."""
    ast = {**_ABC, ('doc', 'x'): expr}
    text = unparse_schema_ast(ast)
    assert f'    define x: {rendered}' in text.splitlines()
    assert parse_schema_ast(text) == ast


# --------------------------------------------------------------------------- #
# The TK115 round-trip guard keeps live witnesses (challenge C2, C3)
# --------------------------------------------------------------------------- #

def test_round_trip_guard_keeps_a_live_witness():
    """S8 took over every JSON witness of the TK115 round-trip guard (a malformed
    restriction-type string is never a declared type), so no JSON input reaches either of its
    branches. These direct calls keep both branches pinned.

    "Different schema": a one-child ``Union`` renders ``owner`` and re-parses as
    ``Computed('owner')``. "Does not parse": a restriction type ``us er`` renders the malformed
    line ``type us er``.

    Sabotage SA9 (`_validate_json_round_trip` made a no-op): RED, both halves (see the
    module docstring)."""
    different = {('doc', 'owner'): Direct((USER,)), ('doc', 'viewer'): Union((Computed('owner'),))}
    with pytest.raises(ValueError, match=r"parses to a different schema \(added \[\], lost \[\], "
                                         r"changed \[\('doc', 'viewer'\)\]\)"):
        _validate_json_round_trip(different)
    unparseable = {('doc', 'viewer'): Direct((Restriction('us er', '...', False),))}
    with pytest.raises(ValueError, match='its DSL rendering does not parse'):
        _validate_json_round_trip(unparseable)
    _validate_json_round_trip({('doc', 'viewer'): Direct((USER,))})     # control: no raise


def test_parse_openfga_json_still_calls_the_round_trip_guard(monkeypatch):
    """The witness above pins the guard's BODY; this pins its CALL in `parse_openfga_json`
    (challenge C3). A perturbed rendering (``[user]`` -> ``[user:*]``) must be refused for a
    VALID model, which parses cleanly without the perturbation.

    Sabotage SA10 (the `_validate_json_round_trip(ast)` call deleted): RED here (see the
    module docstring)."""
    model = _json_model('user')
    assert set(parse_openfga_json(model)) == {('doc', 'viewer')}
    real = json_frontend.unparse_schema_ast
    monkeypatch.setattr(json_frontend, 'unparse_schema_ast',
                        lambda ast: real(ast).replace('define viewer: [user]',
                                                      'define viewer: [user:*]'))
    with pytest.raises(ValueError, match='parses to a different schema'):
        parse_openfga_json(model)


# --------------------------------------------------------------------------- #
# S9 -- OpenFGA features are refused BY NAME
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('text, product_match, oracle_match', [
    ("module core\n" + _TYPES, r"modular models \('module'", 'modular models'),
    (_SCHEMA + "extend type doc\n", r"modular models \('extend type'", 'modular models'),
    (_SCHEMA + "condition in_office(ip: ipaddress) {\n", r"OpenFGA conditions \('condition'",
     'OpenFGA conditions'),
    (_x('[user with in_office]'), r"conditional type restriction 'user with in_office'",
     r"conditional type restriction 'user with in_office'"),
], ids=['module', 'extend', 'condition', 'with'])
def test_openfga_features_are_named(text, product_match, oracle_match):
    """S9, messages only: these were refused before as ``unrecognized schema line: 'module
    core'`` and ``invalid subject type in restriction 'user with c'`` (plan sec 2, S9a-S9d),
    which did not say that the feature is unsupported.

    Sabotage SA11 (the product ``module`` entry removed from `_UNSUPPORTED_OPENFGA_HEADS`):
    RED for module, which falls back to the generic message (module docstring)."""
    _refused_by_both(text, product_match, oracle_match)
