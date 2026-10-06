"""`src/zanzibar/schema/reports.py::w4_fragment_report` -- the input surface the Lean differential
cannot see (`DW-1` step 3, 2026-09-23).

The per-field VERDICT is pinned against Lean's decider in
`formal/conformance/test_conformance_fragment.py` (D)/(E). That differential only ever
feeds corpus tuples, which `tests/oracle.py::t` has already normalised, so it is blind to
how the report reads an operator's tuples. This module pins that half. The mutation
sweep recorded in `docs/dw1-decidable-w4fragment-2026-09-23.md` (step-3 progress block)
found the differential INERT to dropping the `Ellipsis` normalisation; the first test
here is the one that reddens.
"""
from __future__ import annotations

from zanzibar.setengine.models import RelationTuple
from tests.oracle import OracleTuple
from zanzibar.schema import (
    W4_FRAGMENT_FIELDS,
    parse_schema_ast,
    w4_fragment_report,
)

_SCHEMA = """
type user
type doc
  define viewer: [user, user:*]
"""
_ROW = ("user", "*", "viewer", "doc", "d1")


def test_every_bare_predicate_spelling_is_the_bare_predicate():
    """A `user:*` subject is in scope for `bareStar` only with a BARE predicate. The
    production write API spells bare as `...` (Ellipsis) as well as `'...'`, and `None`
    reaches here from JSON-ish callers. All three must read as bare."""
    for bare in ("...", Ellipsis, None):
        rep = w4_fragment_report(_SCHEMA, [(bare, *_ROW)])
        assert rep.in_fragment, (bare, rep.failures)
    # ...and the check is live: a userset predicate on the star subject fails bareStar.
    assert w4_fragment_report(_SCHEMA, [("member", *_ROW)]).failures == ("bareStar",)


def test_tuple_carriers_agree():
    """`RelationTuple` rows, `OracleTuple`s and plain 6-sequences give one report."""
    rows = [("member", "user", "*", "viewer", "doc", "d1"),
            ("...", "user", "alice", "viewer", "doc", "*")]
    plain = w4_fragment_report(_SCHEMA, rows)
    assert plain.failures == ("bareStar",)
    oracle = w4_fragment_report(_SCHEMA, [OracleTuple(*r) for r in rows])
    v1 = w4_fragment_report(_SCHEMA, [RelationTuple(store_id="s", subject_predicate=r[0],
                                              subject_type=r[1], subject_name=r[2],
                                              relation=r[3], object_type=r[4],
                                              object_name=r[5]) for r in rows])
    assert plain == oracle == v1


def test_ast_and_text_agree_and_the_empty_store_is_the_schema_half():
    text_rep = w4_fragment_report(_SCHEMA)
    assert text_rep == w4_fragment_report(parse_schema_ast(_SCHEMA))
    assert tuple(name for name, _ok in text_rep.fields) == W4_FRAGMENT_FIELDS
    assert text_rep.in_fragment and text_rep.tainted == frozenset()


def test_a_schema_the_compiler_refuses_is_reported_not_raised():
    """The report is pure. A LOUD out-of-scope schema (compile raises
    `UnsupportedByGraphIndex`) still gets a verdict, because parsing succeeds."""
    rep = w4_fragment_report("""
        type user
        type org
          define banned: [user]
          define member: [user] but not banned
        type doc
          define view: member from parent
        """)
    assert rep.failures == ("term",)
