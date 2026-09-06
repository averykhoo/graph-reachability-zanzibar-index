"""TK55 -- an EMPTY declared relation name is refused at parse time, by BOTH parsers.

Property guarded
----------------
``define : [user]`` (a ``define`` line whose name is empty or whitespace-only) is a
``ValueError`` from ``zanzibar_utils_v1.parse_schema_ast`` AND, independently, from
``tests.oracle.parse_schema_ast``; the message names the enclosing type. This is what
makes ``FullScope.lean::GraphAdmission.keysNonempty`` (a declared relation name is
non-empty) a Python-enforced SCOPE claim rather than a proof-side assumption. Before
2026-09-06 the Lean docstring and ``CORRESPONDENCE.md`` §6 both said Python already
rejected it "at parse time via the identifier charset" -- that was FALSE: the charset
is applied on the WRITE path only, and the schema parsers accepted the empty name.

The two checks are deliberately NOT shared code: the oracle's parser imports nothing
from the backends (its independence contract), so each parser is pinned by its own
test here and a regression in one cannot be masked by the other.

Pre-fix evidence, literal output (2026-09-06, ``.scratch/tk55_probe_empty_relation*.py``
run against the tree BEFORE this change; the ``.scratch/`` copies are gitignored, this
docstring is the tracked record)::

    === schema plain ===                       # define : [user]
    production parse_schema_ast: ACCEPTED keys=[('doc', '')]
    oracle parse_schema_ast: ACCEPTED keys=[('doc', '')]
    parse_openfga_schema: ACCEPTED empty-relation Filters=1 sample=[Filter(if_pattern=RelationalTriplePattern(subject_predicate=Ellipsis, subject_type='user', subject_name=None, relation='', object_type='doc', object_name=None, match_wildcards=False, object_match_wildcards=True))] derived=[]
    set:py add_tuple: RAISED AdmissionRejected: invalid relation '': must match [A-Za-z0-9_./@+=-] (1-256 chars)
    set:roaring add_tuple: RAISED AdmissionRejected: invalid relation '': must match [A-Za-z0-9_./@+=-] (1-256 chars)
    ParityEngine add_tuple: returned=False

    === schema computed-untainted ===          # define viewer: [user] / define : viewer
    parse_openfga_schema: ACCEPTED derived=[]
    graph apply(viewer write): returned=True
    graph check(alice, "", d1): False
    set:py add_tuple(viewer write): ACCEPTED returned=True
    set:py check(alice, "", d1): True
    set:roaring add_tuple(viewer write): ACCEPTED returned=True
    set:roaring check(alice, "", d1): True
    ParityEngine add_tuple: RAISED AssertionError: check parity broken after add ('...', 'user', 'alice', 'viewer', 'doc', 'd1'): q=('...', 'user', 'alice', '', 'doc', 'd1') graph=False oracle=True

    === schema computed-boolean ===            # ... / define : viewer but not blocked
    parse_openfga_schema: ACCEPTED derived=[('doc', '')]
    graph apply(viewer write): returned=False
    graph write RAISED: AdmissionRejected: invalid relation '': must match [A-Za-z0-9_./@+=-] (1-256 chars)
    set:py add_tuple(viewer write): ACCEPTED returned=True
    set:py check(alice, "", d1): True
    set:roaring add_tuple(viewer write): ACCEPTED returned=True
    set:roaring check(alice, "", d1): True
    ParityEngine add_tuple: RAISED AssertionError: accept/reject disagreement on add ('...', 'user', 'alice', 'viewer', 'doc', 'd1'): {'graph': False, 'set:py': True, 'set:roaring': True}

So a DIRECT write on ``''`` was already refused by both backends (the charset), but a
COMPUTED reference to the empty name was reachable through a valid write and the
backends disagreed there: untainted -> the graph accepts the write and answers
``check=False`` where oracle + both set engines answer ``True`` (a 3-way divergence);
boolean -> the graph refuses the write in ``DeltaProcessor._write_derived`` while both
set engines accept it and answer ``True``. ``test_empty_name_is_unconstructible_end_to_end``
pins that neither state can be built any more.

Sabotage (docs/sabotage-procedure.md), each the narrowest plausible weakening --
deleting ONE parser's ``if not name: raise`` and leaving the other intact::

    A: production check made unreachable (`if False and not relation_name`) ->
        E       Failed: DID NOT RAISE ValueError
        FAILED tests/test_reg_empty_relation_name.py::test_production_parser_refuses_empty_declared_name[boolean]
        FAILED ...[computed]  ...[computed-boolean]  ...[plain]  ...[whitespace]
        FAILED tests/test_reg_empty_relation_name.py::test_refusal_message_names_the_type
        FAILED tests/test_reg_empty_relation_name.py::test_empty_name_is_unconstructible_end_to_end[computed]
        FAILED tests/test_reg_empty_relation_name.py::test_empty_name_is_unconstructible_end_to_end[computed-boolean]
        8 failed, 7 passed in 0.37s     (rc=1; all 5 oracle-side pins + both controls stayed GREEN)
    B: oracle check made unreachable (`if False and not name`) ->
        E       Failed: DID NOT RAISE ValueError
        FAILED tests/test_reg_empty_relation_name.py::test_oracle_parser_refuses_empty_declared_name_independently[boolean]
        FAILED ...[computed]  ...[computed-boolean]  ...[plain]  ...[whitespace]
        FAILED tests/test_reg_empty_relation_name.py::test_refusal_message_names_the_type
        6 failed, 9 passed in 0.40s     (rc=1; all 5 production-side pins + end-to-end + controls stayed GREEN)

Each sabotage reddens exactly one parser's pins (plus the shared message test), so a
red here names WHICH parser regressed. Restored after each; `15 passed` on the clean tree.
"""

from __future__ import annotations

import pytest

from tests import oracle as oracle_mod
from tests.parity import ParityEngine
from zanzibar_utils_v1 import parse_openfga_schema, parse_schema_ast

# One schema per shape the empty name can take. `whitespace` is the `strip()` case;
# `boolean` mints the `.0` leaf predicate the Lean docstring reasons about;
# `computed`/`computed-boolean` are the two shapes that produced the pre-fix
# divergences (a valid write on `viewer` reaching the empty-named relation).
_EMPTY_NAME_SCHEMAS = {
    'plain': "type user\ntype doc\n  relations\n    define : [user]\n",
    'whitespace': "type user\ntype doc\n  relations\n    define    : [user]\n",
    'boolean': ("type user\ntype doc\n  relations\n"
                "    define blocked: [user]\n"
                "    define : [user] but not blocked\n"),
    'computed': ("type user\ntype doc\n  relations\n"
                 "    define viewer: [user]\n"
                 "    define : viewer\n"),
    'computed-boolean': ("type user\ntype doc\n  relations\n"
                         "    define viewer: [user]\n"
                         "    define blocked: [user]\n"
                         "    define : viewer but not blocked\n"),
}

# The non-empty sibling of `plain`: identical except the name is present. Both parsers
# must ACCEPT it and agree on the keys, or the refusal above is a parser that refuses
# everything (non-vacuity control).
_SIBLING = "type user\ntype doc\n  relations\n    define viewer: [user]\n"
_SIBLING_SPACED = "type user\ntype doc\n  relations\n    define   viewer  : [user]\n"


@pytest.mark.parametrize('shape', sorted(_EMPTY_NAME_SCHEMAS))
def test_production_parser_refuses_empty_declared_name(shape):
    """`zanzibar_utils_v1.parse_schema_ast` raises on every empty-name shape.

    Sabotage A (2026-09-06): make the `if not relation_name: raise` in
    `zanzibar_utils_v1.py::parse_schema_ast` unreachable (leave the oracle's) ->
    `E       Failed: DID NOT RAISE ValueError` on all five shapes,
    `FAILED tests/test_reg_empty_relation_name.py::test_production_parser_refuses_empty_declared_name[plain]`
    ... `8 failed, 7 passed`; the oracle-side pins stayed green."""
    with pytest.raises(ValueError, match=r"declared relation name may not be empty"):
        parse_schema_ast(_EMPTY_NAME_SCHEMAS[shape])


@pytest.mark.parametrize('shape', sorted(_EMPTY_NAME_SCHEMAS))
def test_oracle_parser_refuses_empty_declared_name_independently(shape):
    """`tests.oracle.parse_schema_ast` raises on its own -- the oracle shares no
    parser with production, so this test cannot be satisfied by the production
    check.

    Sabotage B (2026-09-06): make the `if not name: raise` in
    `tests/oracle.py::parse_schema_ast` unreachable (leave production's) ->
    `E       Failed: DID NOT RAISE ValueError` on all five shapes,
    `FAILED tests/test_reg_empty_relation_name.py::test_oracle_parser_refuses_empty_declared_name_independently[plain]`
    ... `6 failed, 9 passed`; the production-side pins stayed green."""
    with pytest.raises(ValueError, match=r"declared relation name may not be empty"):
        oracle_mod.parse_schema_ast(_EMPTY_NAME_SCHEMAS[shape])


def test_refusal_message_names_the_type():
    """Both messages carry the enclosing type (`'doc'`), so a multi-type schema's
    error is locatable. Pinned on both parsers separately."""
    with pytest.raises(ValueError, match=r"^type 'doc': ") as prod:
        parse_schema_ast(_EMPTY_NAME_SCHEMAS['plain'])
    with pytest.raises(ValueError, match=r"^type 'doc': ") as orc:
        oracle_mod.parse_schema_ast(_EMPTY_NAME_SCHEMAS['plain'])
    assert "'doc'" in str(prod.value) and "'doc'" in str(orc.value)


@pytest.mark.parametrize('schema', [_SIBLING, _SIBLING_SPACED], ids=['sibling', 'sibling-spaced'])
def test_non_empty_sibling_still_parses_on_both(schema):
    """Non-vacuity control: the same schema with a name present is ACCEPTED by both
    parsers and they agree on the declared keys. Guards against the refusal being
    written as `if not relation_name.strip()` on an un-stripped field, or any other
    over-wide rewrite that would refuse a legitimate `define`."""
    prod_keys = set(parse_schema_ast(schema))
    orc_keys = set(oracle_mod.parse_schema_ast(schema))
    assert prod_keys == orc_keys == {('doc', 'viewer')}


@pytest.mark.parametrize('shape', ['computed', 'computed-boolean'])
def test_empty_name_is_unconstructible_end_to_end(shape):
    """The two pre-fix divergences (see module docstring) cannot be reached any
    more: neither the compiled `RuleSet` nor a `ParityEngine` can be built over an
    empty-named relation, so no write ever gets to disagree about it."""
    with pytest.raises(ValueError, match=r"declared relation name may not be empty"):
        parse_openfga_schema(_EMPTY_NAME_SCHEMAS[shape])
    with pytest.raises(ValueError, match=r"declared relation name may not be empty"):
        ParityEngine(_EMPTY_NAME_SCHEMAS[shape])
