"""Phase 6 extra — EXHAUSTIVE small-scope enumeration (FINAL_REVIEW §4(b)).

Replaces sampling with genuine exhaustion at tiny scope: for each of the six
representative fragment shapes below, enumerate ALL stores of up to K tuples
from the DECLARED tuple space (every write matching a direct restriction of a
declared relation — exactly the admission-valid writes) over a 2-names-per-type
pool, and for EVERY enumerated store compare, over the full shared query grid
(`grid.py`, computed once per shape from the full tuple space so all stores
share one grid):

    Lean spec `sem` (zcli)  ×  independent oracle  ×  real `SetEngine`
                            ×  real graph index (`WildcardIndex` + cascade)

THE DOCUMENTED BOUNDS (the §7 claim's "up to the documented bounds"):

    name pool   : user in {u1, u2}, doc in {d1, d2}, group in {g1, g2},
                  folder in {f1, f2}                 (2 names per type)
    K           : PER SHAPE (see "K per shape" below) — four shapes reach K=4
                  (all stores of size 0..4); the two largest tuple spaces stay
                  at K=3 for runtime (documented, never silent)
    shapes      : boolean_exclusion      —  8-tuple space, K=4, 163 stores
                  boolean_intersection   —  8-tuple space, K=4, 163 stores
                  two_stratum_cascade    — 12-tuple space, K=3, 299 stores
                  boolean_star_exclusion —  6-tuple space, K=4,  57 stores
                  wildcard_group_member  — 10-tuple space, K=3, 176 stores
                  ttu                    —  8-tuple space, K=4, 163 stores
                  (total: 1021 stores; each shape's space, K, and store count
                  is ASSERTED below so the documented bound cannot silently
                  drift)

K per shape (widening §4(e) increment (b), 2026-07-18 — NO silent caps):

    Increment (b) widens the enumeration from a uniform K=3 to K=4. But
    increment (a) had already put the REAL graph index (a full SQL index build
    + cascade) inside the enumeration per store, so per-store cost roughly
    doubled; a naive all-shapes K=4 (1726 stores) blows the ~10-min conf-rest
    command cap. K is therefore PER SHAPE, chosen from measured runtime on the
    reference machine:

      * K=4 (reached):  boolean_exclusion, boolean_intersection,
                        boolean_star_exclusion, ttu.
      * K=3 (CAPPED):   two_stratum_cascade (12-tuple space — dominates: 794
                        stores and ~137 s at K=3 already, the single largest
                        leg) and wildcard_group_member (10-tuple space — 386
                        stores/~132 s at K=4, the next-largest). Both stay at
                        K=3.

    Why these two: at K=4 the enum module alone measured ~7.6 min (conf-rest
    ~9.2 min) with only two_stratum capped — too tight against the 10-min cap.
    Capping BOTH large shapes at K=3 brings the module to ~6.4 min (conf-rest
    ~7.9 min), restoring the ≥1-min margin the phase budget wants. This is the
    sanctioned lever: cap the two dominating tuple spaces, take the other four
    shapes to K=4 (they exercise every read branch — plain/star exclusion,
    intersection, TTU — at the wider depth). The capped shapes remain fully
    exhaustive at K=3; only their size-4 stratum is deferred.

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
    module is ~6.4 min on the reference machine (1021 stores over six shapes at
    the per-shape K above, including the graph leg; the zcli spec cache absorbs
    most of the per-shape cost), inside the conf-rest phase cap.
  * the GRAPH side (the real `WildcardIndex` + `DeltaProcessor`, I5 leaf-
    routing + same-txn cascade) IS enumerated here as of §4(e) increment (a)
    (2026-07-18), over the per-shape K above: for every enumerated store whose
    shape is inside `GRAPH_FRAGMENT` (all six shapes qualify) the real graph
    index `check` is
    compared, over the PROVED graph query scope (concrete objects, star
    subjects bare — `_graph_query_filter`), against the already-agreed
    `sem` (== oracle == set engine). This drives write-order / partial-store
    interleavings the curated corpora never reached — exactly the class of run
    that historically FOUND the P6 leaf-family and 2026-07-17 stale-fanout
    divergences. No zcli "graph" run is needed: the answer-level pin against
    `sem` covers it (the Lean graph model is pinned to `sem` by `graph_correct`
    and to the Python graph by `test_conformance_graph.py`). Adds ~a full SQL
    index build + cascade per store, but no second zcli call, so it stays in
    the conf-rest phase cap.
  * the per-shape K (above) is bounded by the conf-rest command cap, not by
    the combinatorial store count: even the K=4 shapes stay small (largest is
    163 stores); the caps on two_stratum_cascade / wildcard_group_member are
    purely a per-store runtime (graph-leg) budget, not a store-count blowup.
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
from formal.conformance.backends import setengine_answers, graphindex_answers
from formal.conformance.corpus import SCHEMAS, GRAPH_FRAGMENT
from formal.conformance.encode import build_request
from formal.conformance.grid import grid as _grid, fmt_mismatches as _fmt

_POOL: dict[str, tuple[str, ...]] = {
    "user": ("u1", "u2"), "doc": ("d1", "d2"),
    "group": ("g1", "g2"), "folder": ("f1", "f2"),
}

# shape -> (tuple-space size, PER-SHAPE enumeration depth K, store count at K) —
# all three asserted, so neither the documented bounds nor the per-shape K can
# silently drift from the code. K is PER-SHAPE (widening §4(e) increment (b),
# 2026-07-18): four shapes reach K=4; the two largest tuple spaces stay at K=3
# because the graph leg (increment (a)) makes a naive all-shapes K=4 blow the
# ~10-min conf-rest command cap. See the module docstring's "K per shape" block
# for the measured runtime rationale — no cap is silent.
_SHAPES: dict[str, tuple[int, int, int]] = {
    "boolean_exclusion": (8, 4, 163),
    "boolean_intersection": (8, 4, 163),
    "two_stratum_cascade": (12, 3, 299),      # CAPPED K=3 (12-tuple space)
    "boolean_star_exclusion": (6, 4, 57),
    # userset-subject + TTU read branches (widening §4(e) increment (c),
    # 2026-07-18). Both are acyclic under the pool — no admission-cycle skips,
    # spec == oracle == set engine on every enumerated store.
    "wildcard_group_member": (10, 3, 176),    # CAPPED K=3 (10-tuple space)
    "ttu": (8, 4, 163),
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


def _graph_query_filter(subjects, targets):
    """Restrict the shared grid to the PROVED graph query scope (mirrors
    `test_conformance_graph._graph_queries_for`): concrete objects only
    (`hqo : q.object.name != STAR`); star subjects stay, since the grid emits
    them bare-predicate only (userset subjects are concrete-named), satisfying
    `hqs` (`graphRun_check_eq_sem`, GraphIndex/Exec.lean)."""
    targets = [(rel, ot, on) for (rel, ot, on) in targets if on != "*"]
    return [
        (sp, st, sn, rel, ot, on)
        for (sp, st, sn), (rel, ot, on) in itertools.product(subjects, targets)
    ]


@pytest.mark.parametrize("name", sorted(_SHAPES))
def test_exhaustive_small_scope(name):
    """spec == oracle == set engine on EVERY store up to the documented bound."""
    schema_text, _corpus_tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    space = _tuple_space(schema_text)
    exp_space, k, exp_stores = _SHAPES[name]
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

    # Graph leg (widening §4(e) increment (a)): exhaustively drive the REAL
    # graph index (WildcardIndex + DeltaProcessor, I5 leaf-routing + cascade)
    # over EVERY enumerated store, compared at ANSWER level against the already-
    # agreed spec (== oracle == set engine). Gated to shapes inside
    # GRAPH_FRAGMENT (apples-to-apples with graph_correct); all six enum shapes
    # qualify. Query scope narrowed to the PROVED graph scope (`_graph_query_
    # filter`); graph_queries is a subset of `queries`, so the spec answers
    # computed above are the reference (no extra zcli call).
    run_graph = name in GRAPH_FRAGMENT
    graph_queries = _graph_query_filter(subjects, targets) if run_graph else []

    n_stores = 0
    for store in _all_stores(space, k):
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

        if run_graph:
            ref = {q: spec[i] for i, q in enumerate(queries)}  # spec == agreed
            graph = graphindex_answers(schema_text, store, graph_queries,
                                       obj_wild)
            mism = [(graph_queries[i], ref[graph_queries[i]], graph[i])
                    for i in range(len(graph_queries))
                    if ref[graph_queries[i]] != graph[i]]
            assert not mism, (
                f"[{name}] graph/spec disagreement (ADJUDICATION EVENT — plan "
                f"§8.2; graph check != sem == oracle == set engine) at "
                f"enumerated store #{n_stores} = {store}:\n"
                f"{_fmt(mism, 'spec', 'graph')}")

    assert n_stores == exp_stores, (
        f"[{name}] enumerated {n_stores} stores but the documented bound says "
        f"{exp_stores} — the enumeration or the docstring drifted")
