"""TK101 -- EXHAUSTIVE small-scope enumeration of OBJECT-WILDCARD WRITES.

`test_conformance_enum.py::_tuple_space` emits `"*"` only as a SUBJECT, and none of
its six shapes declares an object-wildcard shape, so no store it enumerates holds a
`T:*` object (hole H4, `docs/goal-census-2026-09-22.md` sec 2). This module is the
missing arm. For each shape below it enumerates EVERY store of size 1..K, drawn from
the shape's declared tuple space, that contains AT LEAST ONE `*`-object tuple. The
stores with no `*` object are the parent module's business, so the cost here is
additive, not multiplicative. Each store is compared over the full shared grid
(`grid.py`, `*` objects included):

    Lean spec `sem` (zcli)  x  independent oracle  x  real `SetEngine`
                            [x  real graph index, where the graph admits the schema]

THE TUPLE SPACE. The concrete part is `test_conformance_enum.py::_tuple_space`
(imported, so the two cannot drift). The star part (`_star_space`) is every Direct
restriction of a DECLARED object-wildcard shape, with object `*` and pool subjects.
DECLARED only, not the closed set: the set engine's admission validates against
the closed set only when the graph compiles the schema (`SetEngine.__init__` adopts
the compiled `SchemaInfo`). On a graph-refused schema a write on a closed-but-
undeclared shape is refused, so the declared set is the one write surface both
cases share.

THE GRAPH LEG IS NOT THEOREM-BACKED, and it is not silent either. `object_wildcard`
stores are outside `GRAPH_FRAGMENT` (`corpus.py`: `BareStarStore` requires concrete
stored objects), so the graph is compared Python-to-agreed-answer over the FULL grid,
`*` objects included, as `tests/test_matrix.py` does. Whether the graph admits a
shape is PINNED (`graph` in `_SHAPES`, checked against `parse_openfga_schema`), so a
shape cannot quietly drop to 3-way. `boolean_exclusion` is 3-way on purpose: the
graph refuses an object wildcard that expands onto a boolean leaf
(`zanzibar_utils_v1.py::_reject_object_wildcard_scope`). It is here because a
`doc:*#banned` write is the revocation-shaped `*` object that `TK116` found a set-
engine fail-open on.

THE BRANCH RAN, and this is pinned, not asserted by hope. A green differential over
stores whose `*` tuples changed nothing would prove nothing. For every store the
oracle is also asked with the `*`-object tuples REMOVED, and the concrete-object
answers that differ are counted: `grants` (False -> True) and `revokes`
(True -> False). Both counts are pinned EXACTLY per shape. A star tuple that every
backend silently ignored would agree everywhere and still move these counts, because
the oracle is the referee.

Map, measurements and the mutation sweep: docs/tk101-object-star-enumeration-2026-10-04.md.
"""

from __future__ import annotations

import itertools
from typing import NamedTuple

import pytest

from tests.oracle import Oracle, parse_schema_ast, t as mk_tuple

from formal.conformance import runner
from formal.conformance.backends import setengine_answers, graphindex_answers
from formal.conformance.corpus import SCHEMAS
from formal.conformance.encode import build_request
from formal.conformance.grid import grid as _grid, fmt_mismatches as _fmt
from formal.conformance.test_conformance_enum import (
    _POOL,
    _direct_restrictions,
    _tuple_space,
)
from zanzibar_utils_v1 import UnsupportedByGraphIndex, parse_openfga_schema


class Shape(NamedTuple):
    base: str                      # corpus entry whose schema text is used
    owc: frozenset                 # DECLARED object-wildcard shapes
    graph: bool                    # does the graph index admit (schema, owc)?
    k: int                         # max store size
    conc: int                      # concrete tuple-space size (pinned)
    star: int                      # star-object tuple-space size (pinned)
    stores: int                    # star-bearing stores of size 1..k (pinned)
    queries: int                   # full grid size (pinned)
    grants: int                    # concrete answers a `*` tuple turned True
    revokes: int                   # concrete answers a `*` tuple turned False


_SHAPES: dict[str, Shape] = {
    # star TTU target (`folder:*#viewer`) AND star tupleset (`doc:*#parent`)
    "ttu": Shape("ttu", frozenset({("folder", "viewer"), ("doc", "parent")}),
                 True, 3, 8, 4, 206, 252, 888, 0),
    # star object on a userset-subject relation and on the relation it feeds,
    # with the `user:*` subject wildcard in the same space
    "wildcard_group_member": Shape(
        "wildcard_group_member",
        frozenset({("group", "member"), ("doc", "viewer")}),
        True, 3, 10, 5, 400, 216, 2128, 0),
    # star object on a relation a Computed arm reads, and on the union root
    "union_computed": Shape("union_computed",
                            frozenset({("doc", "editor"), ("doc", "viewer")}),
                            True, 3, 8, 4, 206, 84, 556, 0),
    # graph-REFUSED (3-way): star grant AND star ban under `but not`
    "boolean_exclusion": Shape("boolean_exclusion",
                               frozenset({("doc", "editor"), ("doc", "banned")}),
                               False, 3, 8, 4, 206, 153, 596, 40),
}


def _star_space(schema_text: str, owc) -> list:
    """Every admission-valid `*`-OBJECT tuple: each Direct restriction of each
    DECLARED object-wildcard shape, subjects from `_POOL` (or `*`)."""
    ast = parse_schema_ast(schema_text)
    space = []
    for (ty, rel) in sorted(ast):
        if (ty, rel) not in owc:
            continue
        for (rt, rp, wild) in _direct_restrictions(ast[(ty, rel)]):
            for sn in (("*",) if wild else _POOL.get(rt, ())):
                space.append(mk_tuple(rp, rt, sn, rel, ty, "*"))
    return space


def _star_stores(space: list, k: int):
    """Every store of size 1..k holding at least one `*`-object tuple."""
    for size in range(1, k + 1):
        for store in itertools.combinations(space, size):
            if any(tup.object_name == "*" for tup in store):
                yield list(store)


def _graph_admits(schema_text: str, owc) -> bool:
    try:
        parse_openfga_schema(schema_text, object_wildcard_shapes=owc)
    except UnsupportedByGraphIndex:
        return False
    return True


@pytest.mark.parametrize("name", sorted(_SHAPES))
def test_object_star_small_scope(name):
    """spec == oracle == set engine (== graph, where admitted) on EVERY store with
    a `*`-object write, up to the pinned bound; and the `*` writes moved answers."""
    shape = _SHAPES[name]
    schema_text = SCHEMAS[shape.base][0]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    assert _graph_admits(schema_text, shape.owc) is shape.graph, (
        f"[{name}] graph admission changed (pinned graph={shape.graph}): a shape "
        f"that drops to 3-way, or one that newly compiles, is a decision to make "
        f"deliberately, never silently")

    conc = _tuple_space(schema_text)
    star = _star_space(schema_text, shape.owc)
    assert (len(conc), len(star)) == (shape.conc, shape.star), (
        f"[{name}] tuple space drifted: conc={len(conc)} star={len(star)}, "
        f"pinned conc={shape.conc} star={shape.star}")
    space = conc + star

    subjects, targets = _grid(schema_text, space)
    queries = [
        (sp, st, sn, rel, ot, on)
        for (sp, st, sn), (rel, ot, on) in itertools.product(subjects, targets)
    ]
    assert len(queries) == shape.queries, (
        f"[{name}] grid is {len(queries)} queries, pinned {shape.queries}")
    assert any(on == "*" for (_r, _t, on) in targets), (
        f"[{name}] the grid asks no `*`-object target")
    concrete = [i for i, q in enumerate(queries) if q[5] != "*"]

    n_stores = n_graph = grants = revokes = 0
    for store in _star_stores(space, shape.k):
        n_stores += 1
        spec = runner.run_spec(build_request(schema_text, store, queries,
                                             shape.owc))
        orc = [Oracle(schema_text, store).check(*q) for q in queries]
        se = setengine_answers(schema_text, store, queries, shape.owc)

        mism = [(queries[i], spec[i], orc[i]) for i in range(len(queries))
                if spec[i] != orc[i]]
        assert not mism, (
            f"[{name}] spec/oracle disagreement (ADJUDICATION EVENT -- plan "
            f"sec 8.2) at star store #{n_stores} = {store}:\n"
            f"{_fmt(mism, 'spec', 'oracle')}")
        mism = [(queries[i], spec[i], se[i]) for i in range(len(queries))
                if spec[i] != se[i]]
        assert not mism, (
            f"[{name}] spec/set-engine disagreement at star store #{n_stores} "
            f"= {store}:\n{_fmt(mism, 'spec', 'setengine')}")

        if shape.graph:
            n_graph += 1
            graph = graphindex_answers(schema_text, store, queries, shape.owc)
            mism = [(queries[i], spec[i], graph[i]) for i in range(len(queries))
                    if spec[i] != graph[i]]
            assert not mism, (
                f"[{name}] graph/spec disagreement (graph check != sem == oracle "
                f"== set engine; Python-vs-agreed, outside GRAPH_FRAGMENT) at "
                f"star store #{n_stores} = {store}:\n{_fmt(mism, 'spec', 'graph')}")

        bare = Oracle(schema_text,
                      [tup for tup in store if tup.object_name != "*"])
        for i in concrete:
            without = bare.check(*queries[i])
            grants += orc[i] and not without
            revokes += without and not orc[i]

    assert n_stores == shape.stores, (
        f"[{name}] enumerated {n_stores} star stores, pinned {shape.stores}")
    assert n_graph == (n_stores if shape.graph else 0), (
        f"[{name}] the graph was compared on {n_graph} of {n_stores} stores "
        f"(graph={shape.graph}): a 4-way shape ran 3-way, or the reverse")
    assert (grants, revokes) == (shape.grants, shape.revokes), (
        f"[{name}] `*` writes moved concrete answers grants={grants} "
        f"revokes={revokes}, pinned grants={shape.grants} "
        f"revokes={shape.revokes}")
