"""ASK-1 (user decision, 2026-09-26): a schema must be SELF-CONSISTENT.

Both parsers refuse a dangling reference and a cycle of schema references:
`zanzibar_utils_v1.py::_validate_ast_consistency` (both front ends) and its independent
twin `tests/oracle.py::_validate_consistency`. These are the `GraphAdmission` fields
`matchDecl` and `ranked`, which were SILENT until this change. The Lean-side tie (every
input Lean says fails either field is refused by both parsers) is
`formal/conformance/test_conformance_fragment.py::test_reported_failures_are_refused_by_both_parsers`.
This module pins what that differential cannot see: the per-rule refusals, the JSON front
end, and the recursive schemas that must stay LEGAL. Map:
`docs/ask1-schema-self-consistency-2026-09-26.md`.
"""
from __future__ import annotations

import json

import pytest

from tests import oracle
from zanzibar_utils_v1 import parse_openfga_json, parse_schema_ast

#: label -> (schema, substring of the PRODUCTION message). The oracle's messages differ
#: on purpose (independence contract); only that it refuses is asserted for it.
REFUSED = {
    "computed-ref": ("""
        type user
        type doc
          relations
            define viewer: [user] or editor
        """, "undeclared relation doc#editor"),
    "computed-ref-inside-a-boolean": ("""
        type user
        type doc
          relations
            define banned: [user]
            define view: missing but not banned
        """, "undeclared relation doc#missing"),
    "ttu-tupleset": ("""
        type user
        type folder
          relations
            define viewer: [user]
        type doc
          relations
            define view: viewer from parent
        """, "undeclared relation doc#parent"),
    "ttu-target-on-no-tupleset-type": ("""
        type user
        type folder
          relations
            define owner: [user]
        type doc
          relations
            define parent: [folder]
            define view: viewer from parent
        """, "undeclared relation on every tupleset type"),
    "ttu-target-declared-nowhere-for-an-untyped-tupleset": ("""
        type user
        type doc
          relations
            define a: [user]
            define parent: a
            define view: nothing from parent
        """, "undeclared relation on every tupleset type"),
    "userset-restriction": ("""
        type user
        type group
          relations
            define owner: [user]
        type doc
          relations
            define viewer: [group#member]
        """, "undeclared relation group#member"),
    "wildcard-userset-restriction": ("""
        type user
        type group
          relations
            define owner: [user]
        type doc
          relations
            define viewer: [group:*#member]
        """, "undeclared relation group#member"),
    "computed-self-loop": ("""
        type user
        type doc
          relations
            define viewer: [user] or viewer
        """, "depend on themselves"),
    "computed-two-cycle": ("""
        type user
        type doc
          relations
            define a: [user] or b
            define b: [user] or a
        """, "depend on themselves"),
    "cycle-through-a-boolean": ("""
        type user
        type doc
          relations
            define blk: [user]
            define a: ([user] but not blk) or b
            define b: [user] and a
        """, "depend on themselves"),
    "cycle-through-a-rewritten-tupleset": ("""
        type user
        type folder
          relations
            define parent: [folder] or parent from parent
        """, "depend on themselves"),
}

#: Recursion through STORED TUPLES makes no schema-reference edge and must stay legal.
ACCEPTED = {
    # nested groups
    "nested-groups": """
        type user
        type group
          relations
            define member: [user, group#member]
        """,
    # a folder hierarchy
    "folder-hierarchy": """
        type user
        type folder
          relations
            define parent: [folder]
            define viewer: [user] or viewer from parent
        """,
    # OpenFGA's self-referential boolean flag (openfga.dev/docs/best-practices/modeling-abac);
    # the tuple organization:acme#sso_enabled@organization:acme is data, not schema
    "self-referential-boolean-flag": """
        type user
        type organization
          relations
            define member: [user]
            define sso_enabled: [organization]
            define can_use_sso: member from sso_enabled
        """,
    # a TTU target declared on only ONE of the tupleset's types is enough
    "ttu-target-on-one-of-two-tupleset-types": """
        type user
        type team
          relations
            define lead: [user]
        type folder
          relations
            define viewer: [user]
        type doc
          relations
            define parent: [folder, team]
            define view: viewer from parent
        """,
    # a relation referenced before its definition is not dangling
    "forward-reference": """
        type user
        type doc
          relations
            define viewer: [user] or editor
            define editor: [user]
        """,
}


@pytest.mark.parametrize("label", sorted(REFUSED))
def test_production_parser_refuses(label):
    schema, message = REFUSED[label]
    with pytest.raises(ValueError, match=message):
        parse_schema_ast(schema)


@pytest.mark.parametrize("label", sorted(REFUSED))
def test_oracle_parser_refuses(label):
    with pytest.raises(ValueError):
        oracle.parse_schema_ast(REFUSED[label][0])


@pytest.mark.parametrize("label", sorted(REFUSED))
def test_unchecked_parses_accept_what_the_refusal_rejects(label):
    """Control: the refusal is the ONLY thing rejecting these, so the rows above test it
    and not some other parse error."""
    from zanzibar_utils_v1 import _parse_schema_ast_unchecked
    _parse_schema_ast_unchecked(REFUSED[label][0])
    oracle.parse_schema_ast_unchecked(REFUSED[label][0])


@pytest.mark.parametrize("label", sorted(ACCEPTED))
def test_recursion_through_stored_tuples_stays_legal(label):
    parse_schema_ast(ACCEPTED[label])
    oracle.parse_schema_ast(ACCEPTED[label])


def test_json_front_end_refuses_a_dangling_reference():
    model = {
        "schema_version": "1.1",
        "type_definitions": [
            {"type": "user"},
            {"type": "doc",
             "relations": {"viewer": {"union": {"child": [
                 {"this": {}}, {"computedUserset": {"relation": "editor"}}]}}},
             "metadata": {"relations": {"viewer": {
                 "directly_related_user_types": [{"type": "user"}]}}}},
        ],
    }
    with pytest.raises(ValueError, match="undeclared relation doc#editor"):
        parse_openfga_json(json.dumps(model))


def test_json_front_end_refuses_a_cycle():
    rel = lambda other: {"union": {"child": [  # noqa: E731
        {"this": {}}, {"computedUserset": {"relation": other}}]}}
    meta = {"directly_related_user_types": [{"type": "user"}]}
    model = {
        "schema_version": "1.1",
        "type_definitions": [
            {"type": "user"},
            {"type": "doc", "relations": {"a": rel("b"), "b": rel("a")},
             "metadata": {"relations": {"a": meta, "b": meta}}},
        ],
    }
    with pytest.raises(ValueError, match="depend on themselves"):
        parse_openfga_json(json.dumps(model))


def test_a_long_computed_chain_does_not_recurse():
    """4000 relations in one computed chain. A recursive cycle search would exceed Python's
    default recursion limit; this one must accept the chain and refuse it once closed."""
    n = 4000
    lines = ["type user", "type doc", "  relations", "    define r0: [user]"]
    lines += ["    define r%d: [user] or r%d" % (i, i - 1) for i in range(1, n)]
    parse_schema_ast("\n".join(lines))
    lines[3] = "    define r0: [user] or r%d" % (n - 1)
    with pytest.raises(ValueError, match="depend on themselves"):
        parse_schema_ast("\n".join(lines))
