"""Direct-arm boolean differential — PYTHON-ONLY (no Lean `sem`/zcli).

Widens the boolean corpus to a derived relation with a **Direct arm under an
exclusion**: `approver := (direct[user]) but not banned`, AST
`excl (direct[user]) (computed banned)` with `banned := direct[user]` (see
`corpus.DIRECT_ARM_SCHEMAS`). The excluded-FROM operand is a genuine storage leaf
ON the derived relation (not a named computed union like `boolean_exclusion`'s
`editor` base), so — like `self_flag` — the shape is OUTSIDE `W4Fragment` and is
kept out of `SCHEMAS`/`GRAPH_FRAGMENT`; the Lean graph-side integration is done
separately later.

This is the repo's "validation matrix" spirit, restricted to the THREE Python
backends and run entirely in-process (no zcli, so nothing here builds Lean):

    independent oracle  ==  real SetEngine  ==  real graph index
                            (`WildcardIndex` + `DeltaProcessor` cascade)

over the full shared query grid (`grid.queries_for`), under BOTH SetOps
(RoaringSets and PySets). The oracle is the reference (never edited to match a
backend). Attack-first: `test_direct_arm_attack_stores` re-runs the same
three-way differential over an exhaustive small-scope store enumeration, so a
graph/oracle disagreement on this shape would surface as a hard failure with the
offending store printed — a genuine finding, not a silently-passed sample.
"""

from __future__ import annotations

import itertools

import pytest

from setengine import SetEngine
from setengine.setops import ALL_SETOPS
from sqlmodel import Session, SQLModel, create_engine

from tests.oracle import Oracle, t as mk_tuple

from formal.conformance.backends import graphindex_answers
from formal.conformance.corpus import DIRECT_ARM_SCHEMAS
from formal.conformance.grid import queries_for, fmt_mismatches as _fmt


def _setengine_answers(schema_text, tuples, queries, ops, object_wildcards=()):
    """Mirror `backends.setengine_answers` but pin an explicit SetOps so the
    differential runs under both bitmap backends."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    eng = SetEngine(Session(engine), "s1", schema_text, ops=ops,
                    object_wildcard_shapes=frozenset(object_wildcards))
    for tup in tuples:
        eng.add_tuple(tup.subject_predicate, tup.subject_type, tup.subject_name,
                      tup.relation, tup.object_type, tup.object_name)
    return [bool(eng.check(sp, st, sn, rel, ot, on))
            for (sp, st, sn, rel, ot, on) in queries]


def _three_way(schema_text, tuples, obj_wild, ops):
    """Return (queries, mismatches) for oracle == set engine == graph index."""
    queries = queries_for(schema_text, tuples)
    oracle = Oracle(schema_text, tuples)
    orc = [oracle.check(*q) for q in queries]
    se = _setengine_answers(schema_text, tuples, queries, ops, obj_wild)
    graph = graphindex_answers(schema_text, tuples, queries, obj_wild)
    se_mism = [(queries[i], orc[i], se[i]) for i in range(len(queries))
               if orc[i] != se[i]]
    gr_mism = [(queries[i], orc[i], graph[i]) for i in range(len(queries))
               if orc[i] != graph[i]]
    return queries, se_mism, gr_mism


@pytest.mark.parametrize("ops", ALL_SETOPS, ids=lambda o: o.name)
@pytest.mark.parametrize("name", sorted(DIRECT_ARM_SCHEMAS))
def test_direct_arm_three_way(name, ops):
    """oracle == set engine == graph index over the full grid, both SetOps."""
    schema_text, tuples, obj_wild = DIRECT_ARM_SCHEMAS[name]
    _q, se_mism, gr_mism = _three_way(schema_text, tuples, obj_wild, ops)
    assert not se_mism, (
        f"[{name}/{ops.name}] oracle/set-engine disagreement:\n"
        f"{_fmt(se_mism, 'oracle', 'setengine')}")
    assert not gr_mism, (
        f"[{name}/{ops.name}] oracle/graph-index disagreement (Direct-arm shape "
        f"— a genuine finding):\n{_fmt(gr_mism, 'oracle', 'graph')}")


# --- Attack-first: exhaustive small-scope store enumeration on the shape -------
# `approver = [user] but not banned` over a 2-user / 1-doc pool: all admission-
# valid writes (banned + approver over {u1,u2} x {d1}) = 4 tuples, every store of
# size 0..4 = 16 stores. Each store re-runs the SAME three-way differential, so a
# graph-vs-oracle divergence on ANY store fails loudly with the store printed.
_ATK_SCHEMA = DIRECT_ARM_SCHEMAS["direct_arm_exclusion"][0]
_ATK_SPACE = [
    mk_tuple("...", "user", u, rel, "doc", "d1")
    for rel in ("banned", "approver") for u in ("u1", "u2")
]


def _atk_stores():
    for size in range(len(_ATK_SPACE) + 1):
        yield from itertools.combinations(_ATK_SPACE, size)


@pytest.mark.parametrize("ops", ALL_SETOPS, ids=lambda o: o.name)
def test_direct_arm_attack_stores(ops):
    """Try to break agreement: every store of <=4 admission-valid tuples must
    keep oracle == set engine == graph index on the Direct-arm shape."""
    for store in _atk_stores():
        store = list(store)
        _q, se_mism, gr_mism = _three_way(_ATK_SCHEMA, store, (), ops)
        assert not se_mism, (
            f"[attack/{ops.name}] oracle/set-engine disagreement at store "
            f"{store}:\n{_fmt(se_mism, 'oracle', 'setengine')}")
        assert not gr_mism, (
            f"[attack/{ops.name}] oracle/graph-index disagreement at store "
            f"{store} (GENUINE FINDING):\n{_fmt(gr_mism, 'oracle', 'graph')}")
