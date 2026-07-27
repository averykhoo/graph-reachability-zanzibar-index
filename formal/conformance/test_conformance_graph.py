"""Phase 6 — graph-state conformance: the Lean OPERATIONAL graph model vs the
real Python graph index (and vs `sem`).

HANDOFF.md Phase 6 item 1. `zcli` mode "graph" runs `graphRun` — a fold of the
`ReachedBy` chain's OWN constructors (one admitted logged write + one two-round
cascade leg per tuple, `GraphIndex/Exec.lean`) — and answers with the graph read
`GraphModel.check`. Per corpus we compare two ways:

  * Lean graph model  vs  real Python graph index (`WildcardIndex` + cascade)
    — THE Phase 6 pin: the model the proof talks about computes what the
    Python graph computes;
  * Lean graph model  vs  Lean spec `sem`;
  * (Python graph vs oracle is already pinned repo-wide by the validation
    matrix; not repeated here.)

--------------------------------------------------------------------------- #
WHAT THE COMPARISON IS WORTH — two DIFFERENT things, corpus by corpus.
--------------------------------------------------------------------------- #
This file used to claim, flatly, that `GRAPH_FRAGMENT` is "inside GraphAdmission
+ W4Fragment" and that the model's answers "are covered by `graph_correct`
verbatim". That was FALSE for one corpus, and the Lean tree itself proves it
false. Corrected 2026-07-26 (ZT-P3-3). The honest statement is:

**(A) THEOREM-BACKED — `_THEOREM_BACKED`, 22 of the 23 corpora.** These satisfy
`GraphAdmission` + `W4Fragment`, so the honesty theorems `graphRun_reached` /
`graphRun_check_eq_sem` (`GraphIndex/Exec.lean`) compose with the final T2b
`graph_correct` (`FullScope.lean`): whatever this driver prints for such a
corpus is a value `graph_correct` covers, and a `lean-graph != spec`
disagreement would CONTRADICT a machine-checked theorem — instant adjudication.
The per-corpus fragment argument lives in `corpus.py` next to each entry.

**(B) DIFFERENTIAL-ONLY — `_DIFFERENTIAL_ONLY`, currently `direct_arm_exclusion`
alone.** This corpus is provably OUTSIDE the final theorems' scope, on two
independently machine-checked counts:

  * `FullScope.lean` `W4WitnessDirect.outside_old_admission` proves
    `¬ StoreValidRules Sd Td` — and `StoreValidRules` IS `GraphAdmission.
    storeValid`, while `Sd`/`Td` IS this corpus in compiled form. The store is
    admissible only under the WIDENED `StoreValidRulesD` (leg 5a). So the
    `graph_correct` hypothesis bundle is not merely unproved here, it is
    *refuted*.
  * `W4Fragment.computedOnly` rejects the `direct` leaf under the derived def,
    and `FullScope.lean` records the widening of the final E-chain theorems
    (`enumJob2 -> enumJob2D` + a `_d` projection of `reachedByW3d2E_toC`) as a
    "recorded follow-up, NOT done".

What DOES exist at this shape is the NARROWER C-chain T2b `graph_correct_w3d2_d`
(`CascadeStrataResettle.lean`, audited), with `W4WitnessDirect` pinning that the
corpus inhabits its hypothesis bundle. But this driver folds the **E-chain**
constructors (`graphRun` builds `ReachedByW3d2E` states), and the `_d` projection
that would carry an E-chain state into the C-chain theorem is exactly the piece
recorded as not done. **There is therefore NO proved bridge from what this file
runs to the theorem that covers the shape.** For this corpus the two assertions
below are a DIFFERENTIAL TEST between two independent implementations — valuable
(it is a real Lean-model-vs-Python comparison over a real boolean shape, and it
has adjudication value if it ever fires), but it is not theorem-backed coverage,
and nothing here may be reported as such.

The corpus stays in the gate deliberately: the comparison has value; only the
claim about it was wrong.

--------------------------------------------------------------------------- #
SCOPE DISCIPLINE — and what does NOT enforce it.
--------------------------------------------------------------------------- #
  * queries: the proved query scope — concrete objects (`hqo`), star subjects
    only bare (`hqs`; the shared grid's userset subjects are all concrete-named,
    so they satisfy `hqs` vacuously and stay IN scope — W3b/W3c reach userset
    subjects via `upos`, and zcli's graph-mode gates are corpus-level, not
    per-query);
  * **zcli does NOT check `GraphAdmission` or `W4Fragment`.** The previous
    docstring claimed it "refuses (nonzero rc) on admission failure ... so an
    out-of-scope run FAILS loudly instead of comparing garbage". It does not.
    `Cli.lean` exits nonzero on exactly two conditions: rc 2 when an op fails
    its own RUNTIME gate (per-write edge admission / `removeGateB`), and rc 3
    when the final state is not drained. Neither decides the schema-level
    fragment carries or `StoreValidRules`. An out-of-fragment corpus added to
    `GRAPH_FRAGMENT` therefore runs GREEN and silently compares two models no
    theorem relates — which is precisely how `direct_arm_exclusion` came to be
    described as theorem-backed.
  * The enforcement that DOES exist is `test_graph_fragment_scope_classified`
    below: every `GRAPH_FRAGMENT` corpus must appear in exactly one of
    `_THEOREM_BACKED` / `_DIFFERENTIAL_ONLY`, and the counts must match what this
    docstring claims. Adding a corpus to `GRAPH_FRAGMENT` without classifying it
    FAILS. That is a *review* forcing function, not a proof — a corpus put in
    `_THEOREM_BACKED` without the fragment argument is still a lie, just a lie
    somebody had to type.
  * A runtime fragment gate in the CLI would be the real fix (the tree shows how:
    `removeGateB` already decides six `Prop`s at runtime). Recorded, not done.

Anti-vacuity (ZT-P4-4): every comparison below asserts a nonzero, floored
comparison count. `_graph_queries_for` filters `on != "*"`, which yields exactly
ZERO queries for a corpus whose objects are all `*` (`object_wildcard`) — an
`assert not mism` over an empty list passes silently, so the count is asserted
explicitly.

Skips cleanly if the Lean binary is not built.
"""

from __future__ import annotations

import itertools

import pytest

from formal.conformance import runner
from formal.conformance.backends import graphindex_answers
from formal.conformance.corpus import SCHEMAS, GRAPH_FRAGMENT
from formal.conformance.encode import build_request
from formal.conformance.grid import (
    assert_grid_nonvacuous, grid as _grid, fmt_mismatches as _fmt)


# --------------------------------------------------------------------------- #
# The scope classification the docstring claims — machine-checked below.
# --------------------------------------------------------------------------- #

#: Corpora that satisfy `GraphAdmission` + `W4Fragment`, so the answers compared
#: here are covered by `graph_correct` via `graphRun_reached` /
#: `graphRun_check_eq_sem`. Adding a corpus here asserts you checked the
#: fragment fields against `FullScope.lean` and wrote the argument down in
#: `corpus.py` — see the n-ary block's entries for the shape that argument takes.
_THEOREM_BACKED: frozenset[str] = frozenset({
    "deep_grid",
    "union_computed",
    "group_userset",
    "ttu",
    "wildcard_public",
    "wildcard_group_member",
    "boolean_exclusion",
    "boolean_intersection",
    "boolean_star_exclusion",
    "two_stratum_cascade",
    "taint_union_over_boolean",
    "taint_union_userset_arm",
    "taint_computed_root_over_boolean",
    "nested_boolean",
    "double_exclusion",
    "demorgans",
    "cross_stratum_resettle",
    "star_two_strata_churn",
    "nary_union",
    "nary_intersection",
    # Added 2026-07-27 (ZT-P4-4 / ZT-P4-5(d)). Fields checked against
    # FullScope.lean::W4Fragment + GraphAdmission, argument written down in the
    # corpus.py entries:
    #   `nary_union_derived4` — computedOnly (both derived defs read only
    #     computed operands; the 4-arm union's arms are a/b/c/safe, all computed
    #     refs), twoStrata (measured 2), wsBare + bareStar vacuous (no wildcard
    #     restriction and no star tuple anywhere), ttuStarFree + term's
    #     NoTtuTarget vacuous (no TTU), term's NoStoreSubjectR holds (every
    #     stored subject predicate is `...`), storeValid holds (no Direct arm on
    #     a derived def).
    #   `residue_rich` — structurally `taint_union_userset_arm` (already
    #     theorem-backed here) plus a second bare star shape `svc:*` and a second
    #     excluded subject: computedOnly (viewer = base but not blocked, approver
    #     = viewer or admin — all operands are computed refs to untainted or
    #     derived relations, no Direct arm on a derived def), twoStrata (viewer
    #     then approver), wsBare (both wildcard shapes are BARE: (user,'...'),
    #     (svc,'...')), bareStar (both star subjects bare-predicate, every object
    #     concrete), ttuStarFree + NoTtuTarget vacuous (no TTU),
    #     NoStoreSubjectR (the one userset-subject tuple is `group:eng#member`,
    #     and `member` is UNTAINTED — no stored subject predicate names a derived
    #     relation), storeValid holds.
    "nary_union_derived4",
    "residue_rich",
})

#: Corpora KNOWN to be outside the final theorems' scope, kept in the gate as an
#: implementation-vs-implementation differential. Every entry needs a machine-
#: checked citation for WHY it is outside (not an opinion) — see the module
#: docstring section (B).
_DIFFERENTIAL_ONLY: frozenset[str] = frozenset({
    # `W4WitnessDirect.outside_old_admission` : ¬ StoreValidRules Sd Td.
    "direct_arm_exclusion",
})

#: The split this module's docstring claims, asserted so the prose cannot rot.
_EXPECTED_SPLIT = (22, 1)

# Anti-vacuity floor for the graph query grid (ZT-P4-4). Measured 2026-07-26
# over `GRAPH_FRAGMENT`: the smallest grid is `wildcard_public` at 7 queries
# (largest: `deep_grid` at 2880). The floor is deliberately just under that, so
# it catches a grid that COLLAPSED (the live zero-query configuration is
# `object_wildcard`, whose every object name is `*` and whose `hqo` filter
# therefore removes every target) without re-encoding each corpus's exact size.
_MIN_GRAPH_QUERIES = 7


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


_HQO_HINT = (
    "`_graph_queries_for` drops every target whose object name is '*' (the proved "
    "`hqo` query scope), so a corpus whose objects are ALL star — `object_wildcard` "
    "— yields exactly zero graph queries. Do not move such a corpus into "
    "GRAPH_FRAGMENT expecting it to be compared.")


def _assert_compared(name, queries):
    """Anti-vacuity (ZT-P4-4): a differential over an EMPTY query list is an
    `assert not mism` over `[]`, which passes while comparing nothing."""
    return assert_grid_nonvacuous(name, queries, _MIN_GRAPH_QUERIES, _HQO_HINT)


def test_graph_fragment_scope_classified():
    """Every `GRAPH_FRAGMENT` corpus is classified as theorem-backed or
    differential-only, and the split matches what the module docstring says.

    This is the forcing function for ZT-P3-3: `direct_arm_exclusion` sat in
    `GRAPH_FRAGMENT` for six days under a docstring asserting the exact opposite
    of what `FullScope.lean` machine-checks about it. Adding a corpus to
    `GRAPH_FRAGMENT` without deciding which side it is on now FAILS here."""
    fragment = frozenset(GRAPH_FRAGMENT)
    assert len(GRAPH_FRAGMENT) == len(fragment), (
        f"GRAPH_FRAGMENT has duplicate entries: {sorted(GRAPH_FRAGMENT)}")
    overlap = _THEOREM_BACKED & _DIFFERENTIAL_ONLY
    assert not overlap, (
        f"a corpus cannot be both theorem-backed and differential-only: "
        f"{sorted(overlap)}")

    unclassified = fragment - _THEOREM_BACKED - _DIFFERENTIAL_ONLY
    assert not unclassified, (
        f"GRAPH_FRAGMENT corpora with no scope classification: "
        f"{sorted(unclassified)}.\n"
        f"Decide, and write the reason down: put it in `_THEOREM_BACKED` only if "
        f"you checked every `W4Fragment`/`GraphAdmission` field against "
        f"FullScope.lean and recorded the argument in corpus.py; otherwise put it "
        f"in `_DIFFERENTIAL_ONLY` with the machine-checked citation for why it is "
        f"outside. zcli will NOT tell you — it gates only on runtime write "
        f"admission (rc 2) and drained-ness (rc 3), never on the fragment.")

    stale = (_THEOREM_BACKED | _DIFFERENTIAL_ONLY) - fragment
    assert not stale, (
        f"classified corpora that are no longer in GRAPH_FRAGMENT: "
        f"{sorted(stale)} — drop them from the classification too")

    split = (len(_THEOREM_BACKED), len(_DIFFERENTIAL_ONLY))
    assert split == _EXPECTED_SPLIT, (
        f"the theorem-backed / differential-only split is {split} but this "
        f"module's docstring (and `_EXPECTED_SPLIT`) claims {_EXPECTED_SPLIT} — "
        f"update BOTH the prose and the constant, deliberately")


@pytest.mark.parametrize("name", sorted(GRAPH_FRAGMENT))
def test_leangraph_vs_pythongraph(name):
    """The Phase 6 pin: Lean operational graph model == real Python graph index.

    Theorem-backed for `_THEOREM_BACKED`; an implementation differential for
    `_DIFFERENTIAL_ONLY` (module docstring section (B))."""
    schema_text, tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    queries = _graph_queries_for(schema_text, tuples)
    _assert_compared(name, queries)
    lean_graph = runner.run_spec(
        build_request(schema_text, tuples, queries, obj_wild, mode="graph"))
    py_graph = graphindex_answers(schema_text, tuples, queries, obj_wild)

    assert len(lean_graph) == len(queries) and len(py_graph) == len(queries), (
        f"[{name}] answer-vector length mismatch: {len(queries)} queries, "
        f"lean={len(lean_graph)}, python={len(py_graph)} — the comparison below "
        f"would silently skip the tail")
    mism = [(queries[i], lean_graph[i], py_graph[i]) for i in range(len(queries))
            if lean_graph[i] != py_graph[i]]
    assert not mism, (
        f"[{name}] Lean graph model / Python graph index disagreement "
        f"(ADJUDICATION EVENT — plan §8.2):\n{_fmt(mism, 'lean-graph', 'py-graph')}")


@pytest.mark.parametrize("name", sorted(GRAPH_FRAGMENT))
def test_leangraph_vs_spec(name):
    """The graph mode's answers equal `sem` on the same corpus (the store the
    chain accumulates is the same multiset of tuples; `sem` is order-insensitive
    on these corpora).

    For `_THEOREM_BACKED` this is `graph_correct` re-observed end-to-end, and a
    failure would contradict a machine-checked theorem. For `_DIFFERENTIAL_ONLY`
    it is a comparison of the operational model against the spec with no proved
    bridge between them at that shape."""
    schema_text, tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built")

    queries = _graph_queries_for(schema_text, tuples)
    _assert_compared(name, queries)
    lean_graph = runner.run_spec(
        build_request(schema_text, tuples, queries, obj_wild, mode="graph"))
    spec = runner.run_spec(build_request(schema_text, tuples, queries, obj_wild))

    assert len(lean_graph) == len(queries) and len(spec) == len(queries), (
        f"[{name}] answer-vector length mismatch: {len(queries)} queries, "
        f"graph={len(lean_graph)}, spec={len(spec)}")
    mism = [(queries[i], lean_graph[i], spec[i]) for i in range(len(queries))
            if lean_graph[i] != spec[i]]
    assert not mism, (
        f"[{name}] Lean graph model / spec disagreement "
        f"({'would CONTRADICT graph_correct + the drain gate' if name in _THEOREM_BACKED else 'model-vs-spec differential, no proved bridge at this shape'}):"
        f"\n{_fmt(mism, 'lean-graph', 'spec')}")
