"""Phase 6 — graph-state conformance: the Lean OPERATIONAL graph model vs the
real Python graph index (and vs `sem`).

HANDOFF.md Phase 6 item 1. `zcli` mode "graph" runs `graphRun` — a fold of the
`ReachedBy` chain's OWN constructors (one admitted logged write + one two-round
cascade leg per tuple, `GraphIndex/Exec.lean`) — and answers with the graph read
`GraphModel.check`. Its honesty theorems (`graphRun_reached`,
`graphRun_check_eq_sem`) mean these answers are covered by `graph_correct`
verbatim, so over the fragment corpora we compare three ways:

  * Lean graph model  vs  real Python graph index (`WildcardIndex` + cascade)
    — THE Phase 6 pin: the model the proof talks about computes what the
    Python graph computes;
  * Lean graph model  vs  Lean spec `sem` — the machine-checked theorem
    re-observed end-to-end on real corpora (a mismatch here would contradict
    `graph_correct` + the runtime drain gate: instant adjudication);
  * (Python graph vs oracle is already pinned repo-wide by the validation
    matrix; not repeated here.)

Scope discipline (apples-to-apples with the proved theorem):
  * corpora: `GRAPH_FRAGMENT` only (inside GraphAdmission + W4Fragment — see
    corpus.py for the two documented exclusions);
  * queries: the proved query scope — concrete objects (`hqo`), star subjects
    only bare (`hqs`; the shared grid's userset subjects are all concrete-named,
    so they satisfy `hqs` vacuously and stay IN scope — W3b/W3c reach userset
    subjects via `upos`, and zcli's graph-mode gates are corpus-level
    (admission + drained), not per-query);
  * zcli refuses (nonzero rc) on admission failure or a non-drained final
    state, so an out-of-scope run FAILS loudly instead of comparing garbage.

Skips cleanly if the Lean binary is not built.
"""

from __future__ import annotations

import itertools

import pytest

from formal.conformance import runner
from formal.conformance.backends import graphindex_answers
from formal.conformance.corpus import SCHEMAS, GRAPH_FRAGMENT
from formal.conformance.encode import build_request
from formal.conformance.grid import grid as _grid, fmt_mismatches as _fmt


def _graph_queries_for(schema_text, tuples):
    """The shared query grid, restricted to the PROVED query scope: concrete
    objects only (`hqo : q.object.name != STAR`). Star subjects stay — the grid
    emits them bare-predicate only (userset subjects are concrete-named),
    satisfying `hqs` (`graphRun_check_eq_sem`, GraphIndex/Exec.lean)."""
    subjects, targets = _grid(schema_text, tuples)
    targets = [(rel, ot, on) for (rel, ot, on) in targets if on != "*"]
    return [
        (sp, st, sn, rel, ot, on)
        for (sp, st, sn), (rel, ot, on) in itertools.product(subjects, targets)
    ]


@pytest.mark.parametrize("name", sorted(GRAPH_FRAGMENT))
def test_leangraph_vs_pythongraph(name):
    """The Phase 6 pin: Lean operational graph model == real Python graph index."""
    schema_text, tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    queries = _graph_queries_for(schema_text, tuples)
    lean_graph = runner.run_spec(
        build_request(schema_text, tuples, queries, obj_wild, mode="graph"))
    py_graph = graphindex_answers(schema_text, tuples, queries, obj_wild)

    mism = [(queries[i], lean_graph[i], py_graph[i]) for i in range(len(queries))
            if lean_graph[i] != py_graph[i]]
    assert not mism, (
        f"[{name}] Lean graph model / Python graph index disagreement "
        f"(ADJUDICATION EVENT — plan §8.2):\n{_fmt(mism, 'lean-graph', 'py-graph')}")


@pytest.mark.parametrize("name", sorted(GRAPH_FRAGMENT))
def test_leangraph_vs_spec(name):
    """`graph_correct` re-observed end-to-end: the graph mode's answers equal
    `sem` on the same corpus (the store the chain accumulates is the same
    multiset of tuples; `sem` is order-insensitive on these corpora)."""
    schema_text, tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built")

    queries = _graph_queries_for(schema_text, tuples)
    lean_graph = runner.run_spec(
        build_request(schema_text, tuples, queries, obj_wild, mode="graph"))
    spec = runner.run_spec(build_request(schema_text, tuples, queries, obj_wild))

    mism = [(queries[i], lean_graph[i], spec[i]) for i in range(len(queries))
            if lean_graph[i] != spec[i]]
    assert not mism, (
        f"[{name}] Lean graph model / spec disagreement (would CONTRADICT "
        f"graph_correct + the drain gate):\n{_fmt(mism, 'lean-graph', 'spec')}")
