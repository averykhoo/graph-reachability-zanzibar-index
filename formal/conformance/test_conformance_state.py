"""Phase 6 extra — STATE-level graph conformance (FINAL_REVIEW §4(a)).

`test_conformance_graph.py` pins check VERDICTS; this suite pins the final
MATERIALIZED STATE: per corpus, the Lean operational graph model's edges +
residues (zcli mode `"graph-state"` — the same `graphRun` fold of the
`ReachedBy` chain's own constructors, same rc 2/3 admission/drain gates) must
equal the real Python graph index's final SQL state (`EdgeV4`/`ResidueV1` rows
after the synchronous v1 write path), at the representation-neutral canonical
form of `extractor.py`:

  * the DIRECT edge set over symbolic `(type, name, predicate, wildcard)` node
    keys, and
  * per derived `(object, relation)` key the residue triple
    `(stars, neg, upos)` as sets of shapes / subject triples.

Every projection the comparison applies is enumerated and justified in
`extractor.py` (P1 closure rows, P2 bridges, P3 multiplicity — **derived arm
only since 2026-07-29; untainted-arm multiplicity is compared EXACTLY**, P4
empty residues, P5 nodes, P6 leaf-family split, P7 residue version). Nothing else is dropped: a
divergence outside those documented classes fails here even when every check
verdict agrees — which is exactly the drift class the verdict gate cannot see
(P6 was FOUND by this gate's first run).

Attack-first findings (2026-07-12, scratch probes deleted after recording):
  * duplicate-tuple corpus: Python ref-counts (`direct_edge_count = 2`), the
    model repeats the list entry — check-parity held and the gate stays green
    only because P3 compares sets (multiplicity is projected, documented);
  * boolean_exclusion: the model STORES an all-empty residue row at
    `(doc, d1, viewer)` where Python deletes it — check-parity held, the raw
    dump shows the row, and the gate fails without P4 (the drop is applied
    Python-side so the divergence stays observable);
  * a corrupted extraction (one edge endpoint mutated) makes the gate fail
    with the symmetric-difference message — the gate can fail.

Anti-vacuity (ZT-P4-4, 2026-07-26): `diff_states` returns `None` for two EMPTY
states just as readily as for two equal non-empty ones, so `assert diff is None`
alone cannot distinguish "the states match" from "there were no states". Every
comparison below now asserts a floor on the number of state ROWS actually
compared (edges + residues), on BOTH sides. Hence the floor is 1, and it is a
guard against a COLLAPSED extraction (both sides empty ⇒ `diff is None` ⇒ green),
not a coverage claim.

**What this gate actually compares — measured 2026-07-27 (ZT-P4-5(a)), command:
`python -c` driving `graphindex_drive` over `sorted(GRAPH_FRAGMENT)` and applying
`extractor.extract_sql_state`'s own filters, per corpus.** Over the 21 in-fragment
corpora of that day (**23** as of 2026-07-29; only the P2 leg has been re-measured
since — 477 raw rows, still 0 dropped, see `extractor.py`'s P2 honesty note):
**447 raw `EdgeV4` rows → 231 dropped by P1 (closure-only),
0 by P2 (bridges: never fires, as P2's own honesty note says), 62 by P6
(leaf-family copies), 154 actually compared**; **all 235 `NodeV4` rows dropped by
P5** (nodes are not compared at all — see `test_python_nodes_are_all_justified`
below for the one node-level property that IS gated, and `extractor.py`'s P5
paragraph for what that costs); and **only 5 of 21 corpora produced ANY residue
row (11 rows total)**, so 16 corpora compared two empty residue dicts. Every one
of those 11 rows had `|stars| == 1` and `|neg| == 1`. The `residue_rich` corpus
(added 2026-07-27, pinned by `test_residue_rich_corpus_is_really_rich`) is the
first with a multi-shape `stars`, a multi-subject `neg` and a `upos` member, so
the residue half of the comparison is no longer singleton-only. It remains true
that most corpora contribute edges only.

Skips cleanly if the Lean binary is not built (verify.sh preflights the
binary, so the hard gate never runs skipped).
"""

from __future__ import annotations

import json
import os
import pathlib

import pytest

from formal.conformance import runner
from formal.conformance.corpus import SCHEMAS, GRAPH_FRAGMENT
from formal.conformance.extractor import (
    _classify_edges,
    derived_relations,
    diff_states,
    lean_graph_state,
    python_graph_state,
)


# Anti-vacuity floor on the number of canonical state rows compared per corpus
# (see the module docstring). 1 = the thinnest real corpus state measured
# (`wildcard_public`); zero on either side means the extraction collapsed and
# `diff_states` would report "equal" for two empty dicts.
_MIN_STATE_ROWS = 1

# Anti-vacuity floors for the derived-arm multiplicity ledger below. Measured
# 2026-07-29: 18 derived-arm rows, 18 of them with lean multiplicity > 1. Set AT
# measured reality (the repo's floor discipline), so losing a single derived-arm
# comparison is loud.
_MIN_LEDGER_ROWS = 18
_MIN_LEDGER_STACKED = 18


def _n_rows(state) -> int:
    return len(state["edges"]) + len(state["residues"])


@pytest.mark.parametrize("name", sorted(GRAPH_FRAGMENT))
def test_state_leangraph_vs_pythongraph(name):
    """Final materialized state: Lean operational graph model == Python graph
    index, per corpus, under the documented projections (extractor.py).

    Since 2026-07-29 this also compares edge MULTIPLICITY exactly on the
    untainted arm (P3 as narrowed; `CORRESPONDENCE.md` §7.2). That half is real
    content, not a formality: 153 of the 171 compared edges carry a multiplicity
    nothing had ever compared, and one of them is genuinely non-unit
    (`nary_union` routes `alice` onto the untainted `any_of` from all three
    arms — both sides say 3).

    SABOTAGE EVIDENCE, literal observed output — note each fails on EXACTLY the
    one corpus with a non-unit untainted multiplicity, which is what shows the
    check has precise content rather than being a blanket assertion:
      * `extract_sql_state` weights by `1` instead of `direct_edge_count` (the
        "multiplicity doesn't matter" refactor that reopens the hole) =>
        `edge MULTIPLICITY (untainted arm, P3) ('user','alice','...','') ->
         ('doc','d1','any_of',''): lean=3 python=1`, `1 failed, 47 passed`
      * `Cli.lean::edgeCountsJson` emits a constant 1 => the same line with
        `lean=1 python=3`
      * `derived_relations` returns `frozenset()` (exemption boundary lost) =>
        `AssertionError: P3 edge classification disagreement (schema taint vs
         EdgeV4.derived)`
    """
    schema_text, tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    lean = lean_graph_state(schema_text, tuples, obj_wild)
    py = python_graph_state(schema_text, tuples, obj_wild)

    # ANTI-VACUITY (ZT-P4-4): `diff_states({}, {})` is None. Assert both sides
    # actually produced state before trusting their agreement.
    assert _n_rows(lean) >= _MIN_STATE_ROWS and _n_rows(py) >= _MIN_STATE_ROWS, (
        f"[{name}] ANTI-VACUITY: state extraction collapsed — lean has "
        f"{len(lean['edges'])} edge(s)/{len(lean['residues'])} residue(s), python "
        f"has {len(py['edges'])}/{len(py['residues'])} (floor {_MIN_STATE_ROWS} row "
        f"each). Two EMPTY states diff clean, so the assertion below would pass "
        f"having compared nothing.")

    diff = diff_states(lean, py, derived_relations(schema_text))
    assert diff is None, (
        f"[{name}] Lean graph model / Python graph index STATE disagreement "
        f"(ADJUDICATION EVENT — plan §8.2; symmetric difference):\n{diff}")


# --------------------------------------------------------------------------- #
# P3 (narrowed 2026-07-29) — the DERIVED-arm multiplicity ledger
# --------------------------------------------------------------------------- #

_LEDGER_PATH = pathlib.Path(__file__).with_name("derived_arm_multiplicity.json")
_UPDATE = os.environ.get("ZANZIBAR_UPDATE_SNAPSHOTS") == "1"


def _ledger_key(edge) -> str:
    (st, sn, sp, sw), (ot, on, op, ow) = edge
    return f"{st}:{sn}#{sp}/{sw} -> {ot}:{on}#{op}/{ow}"


def _derived_arm_rows(lean, py, tainted) -> dict:
    arms = _classify_edges(py, tainted)
    return {_ledger_key(k): [lean["edge_counts"][k], py["edge_counts"][k]]
            for k in sorted(arms["derived"]) if k in lean["edge_counts"]}


def test_derived_arm_multiplicity_ledger():
    """The one quantity projection P3 still drops is PINNED, not invisible.

    P3 used to compare edges as sets on both sides, so the model's derived-edge
    multiplicity — which compounds per cascade leg because `admitEdge` never
    rejects a present edge and `edgeHolders` re-enumerates every existing copy —
    was structurally unobservable (`CORRESPONDENCE.md` §7.2, filed UNADJUDICATED
    2026-07-28). The untainted arm is now compared exactly by
    `test_state_leangraph_vs_pythongraph`; this ledger is what closes the rest of
    the hole, by turning the remaining artifact into a golden that any change in
    EITHER side's multiplicity behaviour must break.

    Two things it asserts beyond the golden, both load-bearing:

    * **Python's derived-arm multiplicity is uniformly 1** — the direct
      observable consequence of `_reconcile_subject`'s presence diff
      (`want_edge and not has_edge`). If this ever fails, Python has started
      stacking derived edges and the adjudication below is void.
    * **the golden covers exactly `GRAPH_FRAGMENT`** — so adding a corpus cannot
      silently leave its multiplicity unpinned, which is how this class of hole
      opened in the first place.

    Measured 2026-07-29 when the ledger was created: 18 derived-arm edges across
    23 corpora, Python all 1, Lean 4 … 1013.

    SABOTAGE EVIDENCE (docs/sabotage-procedure.md), literal observed output:
      * one golden value `13 -> 12` =>
        `[boolean_exclusion] user:alice#.../ -> doc:d1#viewer/: golden=[12, 1]
         observed=[13, 1]`
      * drop `_reconcile_subject`'s presence guard (`if want_edge:`) — the
        SUBJECT, not the instrument =>
        `PYTHON derived-arm direct_edge_count is no longer uniformly 1:
         {'nary_union_derived4:...': 4, ..., 'two_stratum_cascade:...': 4}`
      * `_MIN_LEDGER_ROWS` 18 -> 19 =>
        `ANTI-VACUITY: the derived-arm ledger observed 18 row(s) (18 with lean
         multiplicity > 1); floors are 19/18`
      * `Cli.lean::edgeCountsJson` emits a constant 1 (the plausible accident:
        reusing the de-duplicating `canonJsonArr`) =>
        `ANTI-VACUITY: ... 18 row(s) (0 with lean multiplicity > 1)`
      * remove `edgeCounts` from `Cli.lean::stateJson` =>
        `graph-state output shape unexpected: keys=['edges', 'residues']`
    """
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    observed: dict[str, dict] = {}
    for name in sorted(GRAPH_FRAGMENT):
        schema_text, tuples, obj_wild = SCHEMAS[name]
        lean = lean_graph_state(schema_text, tuples, obj_wild)
        py = python_graph_state(schema_text, tuples, obj_wild)
        observed[name] = _derived_arm_rows(lean, py,
                                           derived_relations(schema_text))

    # ANTI-VACUITY: an all-empty ledger compares equal to an all-empty golden.
    n_rows = sum(len(v) for v in observed.values())
    n_stacked = sum(1 for v in observed.values() for lv, _ in v.values() if lv > 1)
    assert n_rows >= _MIN_LEDGER_ROWS and n_stacked >= _MIN_LEDGER_STACKED, (
        f"ANTI-VACUITY: the derived-arm ledger observed {n_rows} row(s) "
        f"({n_stacked} with lean multiplicity > 1); floors are "
        f"{_MIN_LEDGER_ROWS}/{_MIN_LEDGER_STACKED}. An empty ledger matches an "
        f"empty golden and pins nothing.")

    # The property that makes the Python half of P3 inert. Not a golden value —
    # a claim about `_reconcile_subject`, checked directly.
    offenders = {f"{n}:{k}": v[1] for n, rows in observed.items()
                 for k, v in rows.items() if v[1] != 1}
    assert not offenders, (
        f"PYTHON derived-arm `direct_edge_count` is no longer uniformly 1: "
        f"{offenders}. `DeltaProcessor._reconcile_subject` writes a derived edge "
        f"by presence diff (`want_edge and not has_edge`), so re-deriving must "
        f"not bump the count. If this is intended, P3's adjudication in "
        f"extractor.py and CORRESPONDENCE.md §7.2 must be redone.")

    if not _LEDGER_PATH.exists():
        if not _UPDATE:
            pytest.fail(
                f"no derived-arm multiplicity golden at {_LEDGER_PATH.name}. A "
                f"missing golden means the baseline was deleted, not that there "
                f"is nothing to check. Regenerate deliberately with "
                f"ZANZIBAR_UPDATE_SNAPSHOTS=1 and say why in "
                f"docs/spec-deviations.md.")
        _LEDGER_PATH.write_text(json.dumps(observed, indent=2, sort_keys=True)
                                + "\n", encoding="utf-8")
        pytest.skip("generated derived-arm multiplicity baseline (opt-in)")

    golden = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))

    assert set(golden) == set(GRAPH_FRAGMENT), (
        f"the derived-arm ledger does not cover GRAPH_FRAGMENT exactly — "
        f"unpinned corpora {sorted(set(GRAPH_FRAGMENT) - set(golden))}, stale "
        f"golden entries {sorted(set(golden) - set(GRAPH_FRAGMENT))}. A new "
        f"corpus must not land with its multiplicity behaviour unrecorded.")

    if observed != golden:
        lines = []
        for name in sorted(set(observed) | set(golden)):
            o, g = observed.get(name, {}), golden.get(name, {})
            for k in sorted(set(o) | set(g)):
                if o.get(k) != g.get(k):
                    lines.append(f"  [{name}] {k}: golden={g.get(k)} "
                                 f"observed={o.get(k)}  (as [lean, python])")
        pytest.fail(
            "derived-arm edge MULTIPLICITY changed — this is the quantity "
            "projection P3 drops, and it is pinned precisely so a change here "
            "is an adjudication event rather than a silent one "
            "(CORRESPONDENCE.md §7.2).\n" + "\n".join(lines) +
            "\n\nIf the change is intended (e.g. the E-chain Leg-2 enumeration "
            "change, which is EXPECTED to move these numbers — see "
            "formal/history/echain-widening-plan-2026-07-28.md §D.6), "
            "regenerate with ZANZIBAR_UPDATE_SNAPSHOTS=1 in its own commit.")


# --------------------------------------------------------------------------- #
# ZT-P4-5(d) — the RESIDUE half of the gate must not be singleton-only
# --------------------------------------------------------------------------- #

_RESIDUE_RICH = "residue_rich"

# Measured 2026-07-27 on the corpus as committed (see `corpus.py::residue_rich`).
# Exact expectations, not floors: this corpus exists ONLY to make the residue
# comparison non-trivial, so silent degradation to a singleton must fail loudly.
_RESIDUE_RICH_EXPECTED = {
    ("doc", "d1", "viewer"): (
        frozenset({("svc", "..."), ("user", "...")}),
        frozenset({("user", "eve", "..."), ("user", "mallory", "...")}),
        frozenset()),
    ("doc", "d1", "approver"): (
        frozenset({("svc", "..."), ("user", "...")}),
        frozenset({("user", "eve", "..."), ("user", "mallory", "...")}),
        frozenset({("group", "eng", "member")})),
}


def test_residue_rich_corpus_is_really_rich():
    """The `residue_rich` corpus really produces the multi-element residue state
    it was added for — on BOTH sides, and equal.

    ZT-P4-5(d): before this corpus, all 11 residue rows in the whole curated
    state gate had `|stars| == 1` and `|neg| == 1`, so `diff_states`' set
    comparison of those fields had never had to distinguish two elements from
    one, and 16 of 21 corpora compared two EMPTY residue dicts. A corpus added
    for a feature must be pinned to actually reach it (the
    `tests/test_bulk_build.py::_assert_r4bf_features` idiom) or it degrades into
    testing nothing while still reporting green."""
    assert _RESIDUE_RICH in GRAPH_FRAGMENT, (
        f"[{_RESIDUE_RICH}] left GRAPH_FRAGMENT — the residue half of the state "
        f"gate is singleton-only again")
    schema_text, tuples, obj_wild = SCHEMAS[_RESIDUE_RICH]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    lean = lean_graph_state(schema_text, tuples, obj_wild)
    py = python_graph_state(schema_text, tuples, obj_wild)

    for side, state in (("PYTHON", py), ("LEAN", lean)):
        assert state["residues"] == _RESIDUE_RICH_EXPECTED, (
            f"[{_RESIDUE_RICH}/{side}] residue state drifted from the shape this "
            f"corpus exists for.\n  expected {_RESIDUE_RICH_EXPECTED}\n  got      "
            f"{state['residues']}")
        # The specific non-vacuity this corpus buys, asserted as such.
        stars, neg, upos = state["residues"][("doc", "d1", "approver")]
        assert len(stars) >= 2, (
            f"[{_RESIDUE_RICH}/{side}] |stars| = {len(stars)}: the multi-SHAPE "
            f"star comparison is back to a singleton")
        assert len(neg) >= 2, (
            f"[{_RESIDUE_RICH}/{side}] |neg| = {len(neg)}: the multi-SUBJECT "
            f"exclusion comparison is back to a singleton")
        assert upos, (
            f"[{_RESIDUE_RICH}/{side}] `upos` is empty — the edge-free userset "
            f"membership arm is not exercised here")

    diff = diff_states(lean, py, derived_relations(schema_text))
    assert diff is None, (
        f"[{_RESIDUE_RICH}] Lean/Python STATE disagreement on the residue-rich "
        f"corpus (ADJUDICATION EVENT):\n{diff}")


# --------------------------------------------------------------------------- #
# ZT-P4-5(c) — P5 says "nodes are not compared". This is what IS gated.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("name", sorted(GRAPH_FRAGMENT))
def test_python_nodes_are_all_justified(name):
    """No orphan `NodeV4` rows: every node is an endpoint of some `EdgeV4` row or
    is referenced by a residue (as the row's object node, or inside `neg`/`upos`).

    HONESTY (read this before citing it): this is **not** a Lean comparison and
    cannot be one. The Lean `GraphState` does have a `nodes : List NodeKey`
    field, but (i) zcli's `"graph-state"` dump emits only `edges` and `residues`
    (`Cli.lean::stateJson`), and (ii) the model NEVER removes a node while Python
    GCs implicit nodes at refcount 0 and the processor GCs derived-public
    anchors — so raw node-set equality is FALSE BY DESIGN, which is why P5
    exists. Nor is there any comparable node PROPERTY: `NodeV4.implicit` and
    `NodeV4.reference_count` have no counterpart in Lean's `NodeKey` at all.
    Measured 2026-07-27: of 235 `NodeV4` rows across the in-fragment corpora,
    194 are edge/residue endpoints of the COMPARED state and thus pinned
    implicitly by the edge+residue equality above; the other **41 are invisible
    to the gate entirely** — they exist only to carry P1-dropped closure rows or
    P6-dropped leaf-family edges.

    So this test gates the one node-level property that is checkable Python-side
    and is a real failure mode the state comparison cannot see: a leaked node
    (GC that failed to fire) is invisible to an edge/residue diff. Measured
    2026-07-27 across every in-fragment corpus: 0 orphans."""
    from sqlmodel import select
    import json as _json
    from index_v4.models import EdgeV4, NodeV4, ResidueV1
    from formal.conformance.backends import graphindex_drive

    schema_text, tuples, obj_wild = SCHEMAS[name]
    session, _widx, store_id = graphindex_drive(schema_text, tuples, obj_wild)
    try:
        nodes = {n.id: (n.type, n.name, n.predicate, n.wildcard)
                 for n in session.exec(
                     select(NodeV4).where(NodeV4.store_id == store_id)).all()}
        justified = set()
        for e in session.exec(
                select(EdgeV4).where(EdgeV4.store_id == store_id)).all():
            justified.add(e.subject_id)
            justified.add(e.object_id)
        for r in session.exec(
                select(ResidueV1).where(ResidueV1.store_id == store_id)).all():
            justified.add(r.object_node_id)
            justified |= set(_json.loads(r.neg)) | set(_json.loads(r.upos))
    finally:
        session.close()

    # ANTI-VACUITY: a store with no nodes would pass the orphan check trivially.
    assert nodes, (
        f"[{name}] ANTI-VACUITY: the index produced ZERO NodeV4 rows — the "
        f"orphan check below would pass having examined nothing")
    orphans = sorted(nodes[i] for i in nodes if i not in justified)
    assert not orphans, (
        f"[{name}] {len(orphans)} orphan NodeV4 row(s) — nodes with no edge and "
        f"no residue reference. P5 drops nodes from the Lean/Python state "
        f"comparison, so a GC leak here is invisible to that gate:\n"
        + "\n".join(f"    {o}" for o in orphans))
