"""`TK132`: the leaf-row projection of graph STATE, Lean model vs Python graph index.

`test_conformance_leaf_rules.py` (`TK119`) compares the COMPILED RULES. This module is the
second, independent instrument the `TK132` decision keeps
(`docs/tk132-lean-ispure-ttu-target-2026-10-14.md`, "Decision 2026-10-14", T2): it drives
the Lean operational model (`zcli mode="graph-state"`, `extractor.lean_graph_state`) and the
real Python graph index (`extractor.python_graph_state`) over the same tuples and compares
the materialized EDGES whose OBJECT predicate is a leaf name (`<relation>.<i>`).

WHY THE OBJECT SIDE ONLY (challenge X7): a bare subject predicate `...` also contains `.`,
so a "contains a dot" filter on the subject would sweep in every bare edge.

THE FIXTURES are the shapes where the model's old `Leaf.lean::isPure` (a type-agnostic NAME
test on the TTU target) and Python's `boolean.py::_is_pure` (over the tupleset's parent
types) disagreed -- `SlXt`, TK126 variant `D` and `D_nested` -- plus two controls on which
they always agreed: `SlXtR` (`SlXt` with `team#viewer` renamed, no name collision) and `StD`
(the target derived on the ADMITTED type; both sides drop the arm). Schemas are the
verbatim `corpus.py::TK126_SERVED_SCHEMAS` entries where one exists; tuples are the scout's
P2/P6 probes.

BEFORE / AFTER (first-hand, 2026-10-14). Before `TK132` the leaf rows differed on `SlXt`
(scout P1: 4 leaf-row edges, e.g. `edge only in LEAN model : ('user', 'alice', '...', '') ->
('doc', 'd2', 'access.0', '')`), `D` and `D_nested` (P6), and agreed on `SlXtR`/`StD`
(P2). On the `TK132` tree the leaf rows are EQUAL on all five (4 leaf edges each side,
multiplicities equal) -- that is `test_leaf_rows_equal`.

THE RESIDUAL IS A KNOWN, SEPARATE DIVERGENCE, POSITIVELY PINNED (never xfailed):
`TK149` (the 2026-08-14 class, `formal/CORRESPONDENCE.md` §0). The model under-reports a
`.ttu` arm inside a derived def: on every fixture here Python has one more PUBLIC edge
(`alice -> doc:d1#<rel>`) and two more residue rows (`doc:d1#<rel>`, `doc:d2#<rel>`, each
`upos = {folder:f1#viewer}`). Python matches the oracle on all five (scout P2/P6), and the
case is fail-closed and outside `W4Fragment`. `test_residual_public_diff_is_exactly_the_c4_rows`
pins those rows EXACTLY, so fixing `TK149` (or widening the gap) turns it red and forces a
re-adjudication. After `TK132`, `SlXt`'s residual equals `SlXtR`'s, which is the scout's
acceptance criterion (doc §2.2).

SABOTAGE (S4, permanent): `test_python_name_test_sabotage_reddens_exactly_the_tk132_shapes`
puts `_is_pure`'s TTU arm back on the NAME test. Python then allocates like the OLD model,
and the leaf rows must differ on EXACTLY `SlXt`, `D`, `D_nested` and stay equal on `SlXtR`
and `StD`. The Lean-side sabotages are recorded in
`formal/history/tk132-ispure-parent-types-2026-10-14.md`.
"""
from __future__ import annotations

import warnings

import pytest

from formal.conformance import runner
from formal.conformance.corpus import TK126_SERVED_SCHEMAS
from formal.conformance.extractor import lean_graph_state, python_graph_state
from tests.oracle import t
from zanzibar.schema import boolean as boolean_mod
from zanzibar.schema.syntax import TTU

_HEAD = 'model\n  schema 1.1\n'
_SLXT = TK126_SERVED_SCHEMAS["SlXt"]
_SLXTR = _SLXT.replace('define viewer: z but not y', 'define tviewer: z but not y')
assert _SLXTR != _SLXT
_STD = _HEAD + """type user
type folder
  relations
    define e: [user]
    define b: [user]
    define viewer: e but not b
type doc
  relations
    define parent: [folder]
    define banned: [user]
    define access: viewer from parent but not banned
"""

_T_COMMON = [
    t('...', 'folder', 'f1', 'parent', 'doc', 'd1'),
    t('...', 'folder', 'f1', 'parent', 'doc', 'd2'),
    t('...', 'user', 'alice', 'banned', 'doc', 'd2'),
]
_T_D = ([t('...', 'user', 'alice', 'viewer', 'folder', 'f1')] + _T_COMMON
        + [t('...', 'user', 'bob', 'viewer', 'doc', 'd1')])
_T_XT = _T_COMMON + [t('...', 'user', 'alice', 'viewer', 'folder', 'f1'),
                     t('...', 'user', 'bob', 'z', 'team', 't1')]

#: name -> (schema, tuples, the public relation carrying the TTU arm)
CASES: dict[str, tuple[str, list, str]] = {
    "SlXt": (_SLXT, _T_XT, "access"),
    "SlXtR": (_SLXTR, _T_XT, "access"),
    "StD": (_STD, _T_COMMON + [t('...', 'user', 'alice', 'e', 'folder', 'f1'),
                               t('...', 'user', 'carol', 'e', 'folder', 'f1'),
                               t('...', 'user', 'carol', 'b', 'folder', 'f1')], "access"),
    "D": (TK126_SERVED_SCHEMAS["D"], _T_D, "viewer"),
    "D_nested": (TK126_SERVED_SCHEMAS["D_nested"], _T_D, "viewer"),
}

#: The fixtures where the old NAME test and the type test disagree (scout P5).
_TK132_SHAPE = frozenset({"SlXt", "D", "D_nested"})


def _require_zcli() -> None:
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")


def _is_leaf_edge(e: tuple) -> bool:
    """An edge whose OBJECT predicate is a leaf name. Declared names cannot contain `.`
    (`P23`), so on the object side a dot means a leaf family. Never the subject side
    (X7): `...` contains dots."""
    return "." in e[1][2]


def _states(name: str) -> tuple[dict, dict]:
    schema, tuples, _rel = CASES[name]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return lean_graph_state(schema, tuples), python_graph_state(schema, tuples)


def _leaf_rows(state: dict) -> tuple[frozenset, dict]:
    edges = frozenset(e for e in state["edges"] if _is_leaf_edge(e))
    counts = {e: n for e, n in state["edge_counts"].items() if _is_leaf_edge(e)}
    return edges, counts


def _leaf_rows_equal(name: str) -> bool:
    lean, py = _states(name)
    return _leaf_rows(lean) == _leaf_rows(py)


@pytest.mark.parametrize("name", sorted(CASES))
def test_leaf_rows_equal(name):
    """The leaf-row edges (object predicate `<rel>.<i>`) and their multiplicities are EQUAL,
    and non-vacuous (>= 1 leaf edge on each side)."""
    _require_zcli()
    lean, py = _states(name)
    (le, lc), (pe, pc) = _leaf_rows(lean), _leaf_rows(py)
    assert le, f"{name}: Lean produced no leaf-row edge (vacuous comparison)"
    assert pe, f"{name}: Python produced no leaf-row edge (vacuous comparison)"
    assert le == pe, (f"{name}: leaf-row edges differ: only-lean={sorted(le - pe)} "
                      f"only-python={sorted(pe - le)}")
    assert lc == pc, f"{name}: leaf-row multiplicities differ: lean={lc} python={pc}"


@pytest.mark.parametrize("name", sorted(CASES))
def test_residual_public_diff_is_exactly_the_c4_rows(name):
    """POSITIVE pin of `TK149` (the 2026-08-14 `.ttu`-in-derived-def under-report): outside
    the leaf rows, the two states differ by EXACTLY one Python-only public edge and two
    Python-only residue rows, literal per fixture. Red if `TK149` is fixed or widens."""
    _require_zcli()
    lean, py = _states(name)
    rel = CASES[name][2]
    only_lean = sorted(e for e in lean["edges"] - py["edges"] if not _is_leaf_edge(e))
    only_py = sorted(e for e in py["edges"] - lean["edges"] if not _is_leaf_edge(e))
    assert only_lean == []
    assert only_py == [(('user', 'alice', '...', ''), ('doc', 'd1', rel, ''))]
    upos = (frozenset(), frozenset(), frozenset({('folder', 'f1', 'viewer')}))
    assert set(lean["residues"]) - set(py["residues"]) == set()
    assert {k: py["residues"][k] for k in set(py["residues"]) - set(lean["residues"])} == {
        ('doc', 'd1', rel): upos, ('doc', 'd2', rel): upos}
    for k in set(lean["residues"]) & set(py["residues"]):
        assert lean["residues"][k] == py["residues"][k], k


def _is_pure_name_test(monkeypatch) -> None:
    """`_is_pure`'s TTU arm on the model's OLD type-agnostic NAME test."""
    orig = boolean_mod._is_pure

    def name_test(expr, object_type, tainted, ast):
        if isinstance(expr, TTU):
            return not any(rel == expr.target_rel for (_t, rel) in tainted)
        return orig(expr, object_type, tainted, ast)
    monkeypatch.setattr(boolean_mod, "_is_pure", name_test)


def test_python_name_test_sabotage_reddens_exactly_the_tk132_shapes(monkeypatch):
    """S4, permanent: with the Python side put back on the NAME test, the leaf rows differ
    on EXACTLY `_TK132_SHAPE` and stay equal on the two controls. Proves the equality above
    is a measurement of the type-aware test, not an artefact of the fixtures."""
    _require_zcli()
    assert all(_leaf_rows_equal(n) for n in CASES)  # baseline
    with monkeypatch.context() as m:
        _is_pure_name_test(m)
        red = {n for n in CASES if not _leaf_rows_equal(n)}
    assert red == set(_TK132_SHAPE), sorted(red)
    assert all(_leaf_rows_equal(n) for n in CASES)  # patch undone
