"""`zanzibar_utils_v1.py::graph_admission_report` -- the operator surface of `TK104`.

The report covers the two `GraphAdmission` fields that Python neither refused nor shadowed
until ASK-1 (`matchDecl`, `ranked`). Since 2026-09-26 both parsers REFUSE every violation of
them (`tests/test_schema_self_consistency.py`), and the report reads the UNCHECKED parse
(`_parse_schema_ast_unchecked`) so it can still describe one. Its per-field verdict is differential-pinned to Lean's decider
`AdmissionDecide.lean::graphAdmissionB` in
`formal/conformance/test_conformance_fragment.py` section (J). That differential runs only
on schemas both parsers accept and only where `zcli` is built, so this module pins the
parts it cannot see: the input forms, that the report never raises on an out-of-scope
schema, and that the cycle search does not recurse (a Python-recursive DFS would die on a
long computed chain, which is a valid schema).
"""
from __future__ import annotations

from zanzibar_utils_v1 import (
    GRAPH_ADMISSION_REPORTED_FIELDS,
    _parse_schema_ast_unchecked,
    graph_admission_report,
)

DANGLING = """
type user
type doc
  define viewer: [user] or editor
"""

CYCLE = """
type user
type doc
  define a: [user] or b
  define b: [user] or a
"""

NESTED_FOLDERS = """
type user
type folder
  define parent: [folder]
  define viewer: [user] or viewer from parent
"""


def test_field_list_is_the_two_silent_fields_in_declaration_order():
    assert GRAPH_ADMISSION_REPORTED_FIELDS == ("matchDecl", "ranked")


def test_known_answers():
    assert graph_admission_report(DANGLING).failures == ("matchDecl",)
    assert graph_admission_report(CYCLE).failures == ("ranked",)
    rep = graph_admission_report(NESTED_FOLDERS)
    assert rep.failures == () and rep.silent_fields_hold
    assert dict(rep.fields) == {"matchDecl": True, "ranked": True}


def test_accepts_the_ast_as_well_as_text():
    for text in (DANGLING, CYCLE, NESTED_FOLDERS):
        assert (graph_admission_report(_parse_schema_ast_unchecked(text))
                == graph_admission_report(text))


def test_a_derived_def_contributes_no_rule():
    """`schemaRewrites` skips tainted defs, so a boolean def over an undeclared operand
    is NOT a `matchDecl` failure. (Referencing a derived relation taints the referrer, so
    no untainted rule can match one either; section (J) pins that against Lean.)"""
    schema = """
    type user
    type doc
      define banned: [user]
      define view: missing but not banned
    """
    assert graph_admission_report(schema).failures == ()


def test_a_long_computed_chain_does_not_recurse():
    """4000 relations in one computed chain, closed into a cycle at the end. A recursive
    DFS would exceed Python's default recursion limit well before the cycle."""
    n = 4000
    lines = ["type user", "type doc", "  define r0: [user] or r%d" % (n - 1)]
    lines += ["  define r%d: [user] or r%d" % (i, i - 1) for i in range(1, n)]
    assert graph_admission_report("\n".join(lines)).failures == ("ranked",)
    lines[2] = "  define r0: [user]"
    assert graph_admission_report("\n".join(lines)).failures == ()
