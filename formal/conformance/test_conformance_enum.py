"""Phase 6 extra — EXHAUSTIVE small-scope enumeration (FINAL_REVIEW §4(b)).

Replaces sampling with genuine exhaustion at tiny scope: for each of the six
representative fragment shapes below, enumerate ALL stores of up to K tuples
from the DECLARED tuple space (every write matching a direct restriction of a
declared relation — exactly the admission-valid writes) over a 2-names-per-type
pool, and for EVERY enumerated store compare, over the full shared query grid
(`grid.py`, computed once per shape from the full tuple space so all stores
share one grid):

    Lean spec `sem` (zcli)  ×  independent oracle  ×  real `SetEngine`

THE DOCUMENTED BOUNDS (the §7 claim's "up to the documented bounds"):

    name pool   : user in {u1, u2}, doc in {d1, d2}, group in {g1, g2},
                  folder in {f1, f2}                 (2 names per type)
    K           : 3 tuples per store (all stores of size 0, 1, 2, 3)
    shapes      : boolean_exclusion      —  8-tuple space,  93 stores
                  boolean_intersection   —  8-tuple space,  93 stores
                  two_stratum_cascade    — 12-tuple space, 299 stores
                  boolean_star_exclusion —  6-tuple space,  42 stores
                  wildcard_group_member  — 10-tuple space, 176 stores
                  ttu                    —  8-tuple space,  93 stores
                  (total: 796 stores, exhaustive at K=3; each shape's space
                  and store count is ASSERTED below so the documented bound
                  cannot silently drift)

The last two shapes (added 2026-07-18, widening §4(e) increment (c)) reach the
userset-subject and TTU read branches the four boolean shapes never touched:
`wildcard_group_member` (`viewer: [group#member]`) exercises userset subjects
plus the public `user:*` group member; `ttu` (`viewer: viewer from parent`)
exercises the tupleset-to-userset rewrite. The SELF-referential nested-group
schema `group_userset` (`member: [user, group#member]`) is DELIBERATELY NOT used
here: at K=3 it makes 132 of its 299 stores admission-INVALID for the set engine
(its userset-membership cycle guard, engine.py:770, rejects `g1#member member g1`
and the g1<->g2 2-cycle), which would break the "exhaustive over admission-valid
writes" premise. On the 167 acyclic stores spec/oracle/set engine agree exactly
(probed 2026-07-18) — the exclusion is an admission-domain difference, not a
check-semantics divergence.

Stores are SETS of tuples (Zanzibar raw tuples are a set; multiplicity is a
write-path concern outside `sem`), enumerated as sorted-space combinations, so
the enumeration is genuinely exhaustive and deterministic.

Scope notes (honest, not silent):
  * one zcli invocation per store — the request format carries ONE store per
    call (Cli.lean: a single `"tuples"` array), so batching happens at the
    query level (the full grid rides in each call). Runtime for the whole
    module is ~90 s on the reference machine (796 stores over six shapes; the
    zcli spec cache absorbs most of the added shapes' cost), inside the
    conf-rest phase cap.
  * the GRAPH side (zcli mode "graph" × the real `WildcardIndex`) is NOT
    enumerated here: it would roughly triple the runtime (a second zcli run
    plus a full SQL index build + cascade per store, 527×). The required core
    — spec × oracle × set engine — is the three-way this suite exhausts; the
    graph model stays pinned by `test_conformance_graph.py` /
    `test_conformance_state.py` over the curated corpora.
  * K=3 was chosen so no shape's space exceeds ~20k stores (the largest is
    299); no shape needed the documented K=2 fallback.
"""

from __future__ import annotations

import itertools

import pytest

from tests.oracle import (
    ODirect,
    OExclusion,
    OIntersection,
    OUnion,
    Oracle,
    parse_schema_ast,
    t as mk_tuple,
)

from formal.conformance import runner
from formal.conformance.backends import setengine_answers
from formal.conformance.corpus import SCHEMAS
from formal.conformance.encode import build_request
from formal.conformance.grid import grid as _grid, fmt_mismatches as _fmt

_POOL: dict[str, tuple[str, ...]] = {
    "user": ("u1", "u2"), "doc": ("d1", "d2"),
    "group": ("g1", "g2"), "folder": ("f1", "f2"),
}
_K = 3

# shape -> (expected tuple-space size, expected store count at K) — asserted,
# so the docstring's documented bounds cannot silently drift from the code.
_SHAPES: dict[str, tuple[int, int]] = {
    "boolean_exclusion": (8, 93),
    "boolean_intersection": (8, 93),
    "two_stratum_cascade": (12, 299),
    "boolean_star_exclusion": (6, 42),
    # userset-subject + TTU read branches (widening §4(e) increment (c),
    # 2026-07-18). Both are acyclic under the pool — no admission-cycle skips,
    # spec == oracle == set engine on every enumerated store.
    "wildcard_group_member": (10, 176),
    "ttu": (8, 93),
}


def _direct_restrictions(expr):
    """All `(type, predicate, wildcard)` Direct restrictions in a def (the
    admission-valid write shapes for its relation)."""
    if isinstance(expr, ODirect):
        return list(expr.restrictions)
    if isinstance(expr, (OUnion, OIntersection)):
        return [r for c in expr.children for r in _direct_restrictions(c)]
    if isinstance(expr, OExclusion):
        return (_direct_restrictions(expr.base)
                + _direct_restrictions(expr.subtract))
    return []  # OComputed / OTTU: no direct write surface


def _tuple_space(schema_text: str) -> list:
    """The declared tuple space over `_POOL`: for every declared relation and
    every Direct restriction, all admission-valid tuples with pool names."""
    ast = parse_schema_ast(schema_text)  # {(type, relation): OExpr}
    space = []
    for (ty, rel) in sorted(ast):
        for (rt, rp, wild) in _direct_restrictions(ast[(ty, rel)]):
            for on in _POOL.get(ty, ()):
                if wild:
                    space.append(mk_tuple(rp, rt, "*", rel, ty, on))
                else:
                    for sn in _POOL.get(rt, ()):
                        space.append(mk_tuple(rp, rt, sn, rel, ty, on))
    return space


def _all_stores(space: list, k: int):
    """Every store (tuple SET) of size 0..k, deterministically ordered."""
    for size in range(k + 1):
        yield from itertools.combinations(space, size)


@pytest.mark.parametrize("name", sorted(_SHAPES))
def test_exhaustive_small_scope(name):
    """spec == oracle == set engine on EVERY store up to the documented bound."""
    schema_text, _corpus_tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    space = _tuple_space(schema_text)
    exp_space, exp_stores = _SHAPES[name]
    assert len(space) == exp_space, (
        f"[{name}] declared tuple space drifted: {len(space)} tuples "
        f"(documented bound says {exp_space}) — update the documented bounds "
        f"deliberately, never silently")

    # ONE grid per shape, derived from the full space, shared by every store.
    subjects, targets = _grid(schema_text, space)
    queries = [
        (sp, st, sn, rel, ot, on)
        for (sp, st, sn), (rel, ot, on) in itertools.product(subjects, targets)
    ]

    n_stores = 0
    for store in _all_stores(space, _K):
        n_stores += 1
        store = list(store)
        spec = runner.run_spec(build_request(schema_text, store, queries,
                                             obj_wild))
        oracle = Oracle(schema_text, store)
        orc = [oracle.check(*q) for q in queries]
        se = setengine_answers(schema_text, store, queries, obj_wild)

        mism = [(queries[i], spec[i], orc[i]) for i in range(len(queries))
                if spec[i] != orc[i]]
        assert not mism, (
            f"[{name}] spec/oracle disagreement (ADJUDICATION EVENT — plan "
            f"§8.2) at enumerated store #{n_stores} = {store}:\n"
            f"{_fmt(mism, 'spec', 'oracle')}")
        mism = [(queries[i], spec[i], se[i]) for i in range(len(queries))
                if spec[i] != se[i]]
        assert not mism, (
            f"[{name}] spec/set-engine disagreement (ADJUDICATION EVENT — "
            f"plan §8.2) at enumerated store #{n_stores} = {store}:\n"
            f"{_fmt(mism, 'spec', 'setengine')}")

    assert n_stores == exp_stores, (
        f"[{name}] enumerated {n_stores} stores but the documented bound says "
        f"{exp_stores} — the enumeration or the docstring drifted")
