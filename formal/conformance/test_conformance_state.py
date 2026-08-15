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

**What this gate actually compares is now MEASURED AND PINNED, not narrated here.**
`extractor.projection_ledger` / `::graph_fragment_ledger` drive every in-fragment
corpus and count the drops per projection; the totals are published in
`FINAL_REVIEW.md`'s generated counts block and checked by `verify.sh` step 4e.
**Read the numbers there.** `test_projection_ledger_is_not_vacuous` below pins the
properties that make them meaningful.

This paragraph used to restate the figures, and it is *why* the ledger exists: the
2026-07-27 measurement (21 corpora — 447 raw rows, 231 by P1, 62 by P6, 154
compared, 235 `NodeV4`, 11 residue rows over 5 corpora) was still being quoted on
2026-08-05 against a 23-corpus set whose real figures were then 477 / 233 / 73 /
171 / 266 / 13-over-6. Every number in the old paragraph except the P2 zero had drifted,
and the recipe for re-deriving them existed only as an English description of a
`python -c` invocation. Per `ZT-P3-5`: a quoted count is not merely stale, it is
*unenforced*. Nodes are still not compared at all (P5) — see
`test_python_nodes_are_all_justified` below for the one node-level property that IS
gated, and `extractor.py`'s P5 paragraph for what that costs. The `residue_rich`
corpus (added 2026-07-27, pinned by `test_residue_rich_corpus_is_really_rich`) is
the first with a multi-shape `stars`, a multi-subject `neg` and a `upos` member, so
the residue half is no longer singleton-only; it remains true that most corpora
contribute edges only.

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


def test_projection_ledger_is_not_vacuous():
    """The state-gate projection ledger measures a real, firing filter.

    `FINAL_REVIEW.md`'s generated block publishes how many raw rows each
    projection drops. A published count is worth nothing unless breaking the
    filter breaks the count, so this pins the three properties that make it
    meaningful: the cascade partitions the raw rows exactly, P6 actually FIRES,
    and something actually survives to be compared. `extract_sql_state` and
    `projection_ledger` share ONE predicate (`extractor._edge_projection`), so
    there is no second implementation to drift.

    ★ SABOTAGE EVIDENCE (2026-08-05, `docs/sabotage-procedure.md`). Deleting the
    P6 branch from `_edge_projection` — i.e. exactly what "retire P6" will look
    like — turns `doc_counts --check` RED with the literal diff::

        doc:  | dropped by P6 (leaf-family copy) | **73** |
        tree: | dropped by P6 (leaf-family copy) | **0** |
        doc:  | **compared against Lean** | **171** |
        tree: | **compared against Lean** | **244** |
        doc_counts --check exit: 1

    and this test fails its `P6 > 0` assertion. So the number is load-bearing.

    ★ AND THE CONTROL FOUND A DEAD BRANCH, recorded rather than glossed. The
    NARROWER sabotage — dropping P6's `and obj[2] != "..."` guard — left the
    ledger byte-identical (`P6: 73` both ways, `--check` exit 0). Measured cause
    (2026-07-29): across the 23 corpora then in the fragment, of the 244 rows
    then surviving
    P1, **73 had an object predicate containing `'.'` and ZERO had object
    predicate `'...'`**.
    The guard is dead code on this corpus set — `'...'` is the bare SUBJECT
    sentinel and object nodes carry relation names. That is a coverage gap in the
    corpus, not in this pin, and `test_p6_bare_sentinel_guard_is_unexercised`
    below is its permanent record so it cannot quietly become load-bearing.
    """
    from formal.conformance.extractor import graph_fragment_ledger

    led = graph_fragment_ledger()
    assert led["corpora"] == len(GRAPH_FRAGMENT), (
        f"ledger drove {led['corpora']} corpora, GRAPH_FRAGMENT has "
        f"{len(GRAPH_FRAGMENT)} — the ledger is describing a different set")
    assert led["P1"] + led["P2"] + led["P6"] + led["compared"] == led["raw"], (
        f"projection cascade does not partition the raw rows: {led}")
    # The filter fires. Without this, deleting P6 would leave a green ledger that
    # merely reported a different (still self-consistent) number.
    assert led["P6"] > 0, f"P6 never fires — the published drop count is a lie: {led}"
    # Something survives. Guards the dual collapse (everything dropped ⇒ the
    # differential gate compares nothing and still reports "equal").
    assert led["compared"] > 0, f"nothing survives the projections: {led}"
    assert led["raw"] > led["compared"], (
        f"raw == compared means no projection drops anything; the ledger would "
        f"be measuring a gate that has no blind spot, which is false: {led}")


def test_p6_bare_sentinel_guard_is_unexercised():
    """P6's `obj[2] != '...'` clause is DEAD on the current corpus set.

    Not a defect — a recorded coverage fact, found by controlling the sabotage of
    `test_projection_ledger_is_not_vacuous` (removing this clause changed
    nothing). Object nodes carry relation names; `'...'` is the bare SUBJECT
    predicate sentinel, so no object node should ever carry it.

    This test exists so the situation cannot change silently. If a future corpus
    DOES produce an object node with predicate `'...'`, this fails — and at that
    moment the clause becomes load-bearing and the narrow sabotage above starts
    discriminating. Either outcome is informative; drifting between them silently
    is not.
    """
    from sqlmodel import select

    from formal.conformance.backends import graphindex_drive
    from index_v4.models import EdgeV4, NodeV4

    surviving_p1 = dotted = bare = 0
    for name in sorted(GRAPH_FRAGMENT):
        schema_text, tuples, object_wildcards = SCHEMAS[name]
        session, _widx, store_id = graphindex_drive(
            schema_text, tuples, object_wildcards)
        try:
            nodes = {
                n.id: (n.type, n.name, n.predicate, n.wildcard)
                for n in session.exec(
                    select(NodeV4).where(NodeV4.store_id == store_id)).all()
            }
            for e in session.exec(
                    select(EdgeV4).where(EdgeV4.store_id == store_id)).all():
                if e.direct_edge_count <= 0:
                    continue
                surviving_p1 += 1
                pred = nodes[e.object_id][2]
                dotted += "." in pred
                bare += pred == "..."
        finally:
            session.close()

    assert surviving_p1 > 0 and dotted > 0, (
        f"instrument check: expected some P1-surviving dotted rows, got "
        f"{surviving_p1} surviving / {dotted} dotted")
    assert bare == 0, (
        f"{bare} object node(s) now carry predicate '...' — P6's bare-sentinel "
        f"guard has become load-bearing. Update this test AND re-run the narrow "
        f"sabotage in test_projection_ledger_is_not_vacuous, which was recorded "
        f"as non-discriminating precisely because this count was 0.")

# Anti-vacuity floor for the leaf-row structural pin below. Measured 2026-08-09
# over all 25 in-fragment corpora (`GRAPH_FRAGMENT` had just grown 23 -> 25 with
# `reconvergent_diamond` / `reconvergent_derived`; the 2026-08-08 measurement of
# the 23-corpus set was 75 = 73 + 2): **78** leaf-TARGET `EdgeV4` rows — 76 of
# them surviving P1 (and hence P6-dropped), the other 2 closure-only rows P1
# drops first. Set AT measured reality per the repo's floor discipline.
# Re-derive with the test's own selector — note it has NO P1 filter, which is
# the point of the test (it runs upstream of `_edge_projection`):
#   $ZANZIBAR_PY -c "
#   from sqlmodel import select
#   from formal.conformance.corpus import SCHEMAS, GRAPH_FRAGMENT
#   from formal.conformance.backends import graphindex_drive
#   from index_v4.models import EdgeV4, NodeV4
#   n = 0
#   for name in sorted(GRAPH_FRAGMENT):
#       sch, tup, ow = SCHEMAS[name]
#       s, _w, sid = graphindex_drive(sch, tup, ow)
#       preds = {x.id: x.predicate
#                for x in s.exec(select(NodeV4).where(NodeV4.store_id == sid))}
#       n += sum('.' in preds[e.object_id] and preds[e.object_id] != '...'
#                for e in s.exec(select(EdgeV4).where(EdgeV4.store_id == sid)))
#       s.close()
#   print(n)"
# ★ SABOTAGE (2026-08-09, at floor 78): adding `if e.direct_edge_count <= 0:
# continue` to the test's selector — the plausible "route it through the P1/P6
# projection" refactor, which silently loses only the 2 closure-only leaf rows —
# fires THIS floor and nothing else (the two property assertions never run):
#   AssertionError: instrument check: inspected 76 leaf rows, floor 78 — the
#   selector stopped finding its subject, so the two property assertions below
#   would pass vacuously
#   assert 76 >= 78
# A floor one notch below reality (76) would have stayed green under that edit.
_MIN_LEAF_ROWS = 78


def test_leaf_rows_are_structurally_untainted():
    """Leaf-family edge rows are `derived=False` AND schema-untainted — for a
    STRUCTURAL reason, not because P6 hides them.

    This pins the claim that `extractor._classify_edges` actually depends on: that
    schema taint and `EdgeV4.derived` cannot disagree on a `<rel>.<n>` leaf row.
    Until 2026-08-08 that function justified the agreement with "leaf families
    which P6 already dropped" — an explanation that is false as reasoning (the
    agreement holds for reasons unrelated to P6) and that would have SILENTLY
    become wrong when P6 retires. This test is that paragraph converted into a
    refusal, because the next person will not read the paragraph.

    Note the deliberate scope: it runs against the RAW `EdgeV4` rows, upstream of
    `_edge_projection`, so it keeps testing exactly the same property after P6 is
    deleted. That is the point — it is the check that makes retiring P6 safe
    (`formal/history/leaf-family-split-scope-2026-08-05.md` §7 step 2), so it must
    not itself be routed through the filter being retired.

    ★ SABOTAGE EVIDENCE (2026-08-08, `docs/sabotage-procedure.md`). Three
    sabotages were run, and the FIRST one — the obvious one, the one this test was
    written to catch — turned out to be non-discriminating. Recorded as measured,
    because a sabotage that passes is exactly the finding the procedure exists to
    surface, and writing the intended-but-false version here would have made this
    docstring the defect.

      1. **Registry merge — NON-DISCRIMINATING (dead).** Making
         `WildcardIndex._derived_write_ctx` consult `leaf_families` in addition to
         `derived_families` leaves this test GREEN. Measured cause: the
         `processor_writes and ...` conjunct short-circuits first, and leaf rows
         are written by USER-routed raw writes (`RuleSet.apply` fan-in), which run
         with `processor_writes == False`. Inspected directly under the edit —
         `boolean_exclusion` still reports `('doc','d1','viewer.0') derived=False`
         on all three leaf rows. So the `derived=False` half is guarded by the
         processor-writes gate, NOT by the family registry.
      2. **Taint side — RED, and this is what assertion 2 actually pins.** Making
         `derived_relations` emit the compiled `leaf_families` alongside the
         derived ones (the plausible "extend taint to cover leaf predicates" edit)
         fails with `75 leaf pair(s) entered the schema taint set`, naming
         `boolean_exclusion doc:d1#viewer.0` first.
      3. **Forcing the derived stamp on leaf writes — RED, but NOT HERE.**
         Returning `True` from `_derived_write_ctx` for any dotted relation never
         reaches an assertion in this file: the drive itself dies in paranoia mode
         with `[pre-commit] I5: derived flag on a non-derived-direct edge row`.
         So assertion 1 is defended in DEPTH by I5's runtime checker, which
         refuses to even construct the state. It is a second line, not the only
         line — stated plainly so nobody credits this test with I5's work.

    Net: assertion 2 is load-bearing here; assertion 1 is corroborating. The
    property as a whole is worth pinning upstream of the filter anyway, because
    once P6 retires a disagreement becomes a raise in the middle of the state
    gate, and `test_state_leangraph_vs_pythongraph` cannot see it today — P6 drops
    these rows before `_classify_edges` is ever called.

    ★ AND THE INSTRUMENT IS CONTROLLED. `_MIN_LEAF_ROWS` is not decoration: with
    the leaf-row selector inverted to a predicate matching nothing, both property
    assertions pass VACUOUSLY (0 violations of 0 rows) and only the floor goes red
    — observed literally 2026-08-08 (floor then 75, 23-corpus fragment):
    `inspected 0 leaf rows, floor 75 — the selector stopped finding its subject`.
    Re-run 2026-08-09 at floor 78 on the 25-corpus fragment with a NARROWER
    sabotage (a P1 filter losing just the 2 closure-only rows) — literal output
    in the floor's own comment above. A pin whose subject can vanish silently
    verifies nothing.
    """
    from sqlmodel import select

    from formal.conformance.backends import graphindex_drive
    from index_v4.models import EdgeV4, NodeV4

    inspected = 0
    flagged_derived: list[str] = []
    in_taint: list[str] = []
    for name in sorted(GRAPH_FRAGMENT):
        schema_text, tuples, object_wildcards = SCHEMAS[name]
        tainted = derived_relations(schema_text)
        session, _widx, store_id = graphindex_drive(
            schema_text, tuples, object_wildcards)
        try:
            nodes = {
                n.id: (n.type, n.name, n.predicate, n.wildcard)
                for n in session.exec(
                    select(NodeV4).where(NodeV4.store_id == store_id)).all()
            }
            for e in session.exec(
                    select(EdgeV4).where(EdgeV4.store_id == store_id)).all():
                obj = nodes[e.object_id]
                if "." not in obj[2] or obj[2] == "...":
                    continue                            # not a leaf-family row
                inspected += 1
                where = f"{name} {obj[0]}:{obj[1]}#{obj[2]}"
                if e.derived:
                    flagged_derived.append(where)
                if (obj[0], obj[2]) in tainted:
                    in_taint.append(where)
        finally:
            session.close()

    assert inspected >= _MIN_LEAF_ROWS, (
        f"instrument check: inspected {inspected} leaf rows, floor "
        f"{_MIN_LEAF_ROWS} — the selector stopped finding its subject, so the "
        f"two property assertions below would pass vacuously")
    assert not flagged_derived, (
        f"{len(flagged_derived)} leaf row(s) carry derived=True: "
        f"{sorted(flagged_derived)[:5]}. `_classify_edges` classifies by SCHEMA "
        f"taint, which can never contain a dotted pair, so a derived=True leaf "
        f"row is a genuine disagreement — and once P6 retires it becomes a raise "
        f"in the middle of the state gate.")
    assert not in_taint, (
        f"{len(in_taint)} leaf pair(s) entered the schema taint set: "
        f"{sorted(in_taint)[:5]}. `.` is reserved in declared relation names, so "
        f"`compute_taint` should be structurally incapable of emitting one.")


# Anti-vacuity floors for the derived-arm multiplicity ledger below. Measured
# 2026-08-09 over all 25 in-fragment corpora (`GRAPH_FRAGMENT` had just grown
# 23 -> 25 with `reconvergent_diamond` / `reconvergent_derived`; the 2026-07-29
# measurement of the 23-corpus set was 18/18): **19** derived-arm rows, **19**
# of them with lean multiplicity > 1. Set AT measured reality (the repo's floor
# discipline), so losing a single derived-arm comparison is loud. Re-derive from
# the golden — which `test_derived_arm_multiplicity_ledger` pins equal to the
# live observation, so this is the live number whenever that test is green:
#   $ZANZIBAR_PY -c "
#   import json
#   from formal.conformance.test_conformance_state import _LEDGER_PATH
#   g = json.loads(_LEDGER_PATH.read_text(encoding='utf-8'))
#   print(sum(len(v) for v in g.values()),
#         sum(1 for v in g.values() for lv, _ in v.values() if lv > 1))"
# ★ SABOTAGE (2026-08-09, at floors 19/19), one per floor, both firing on the
# ANTI-VACUITY assertion itself (NOT the golden diff, which sits after it and
# never ran — checked, because a sabotage that trips a different assertion
# proves nothing about the floor):
#   * _MIN_LEDGER_ROWS — `_derived_arm_rows` iterating
#     `sorted(arms["derived"])[1:]` (the selector silently losing comparisons,
#     the same class as its `if k in lean["edge_counts"]` guard) =>
#       AssertionError: ANTI-VACUITY: the derived-arm ledger observed 8 row(s)
#       (8 with lean multiplicity > 1); floors are 19/19. An empty ledger
#       matches an empty golden and pins nothing.
#       assert (8 >= 19)
#   * _MIN_LEDGER_STACKED — clamping the lean side to `min(lean_count, 1)` (the
#     de-duplicating-emit accident, reproduced Python-side) leaves n_rows at 19,
#     so the literal output shows the stacked half firing ALONE:
#       AssertionError: ANTI-VACUITY: the derived-arm ledger observed 19 row(s)
#       (0 with lean multiplicity > 1); floors are 19/19. ...
#       assert (19 >= 19 and 0 >= 19)
_MIN_LEDGER_ROWS = 19
_MIN_LEDGER_STACKED = 19


def _n_rows(state) -> int:
    return len(state["edges"]) + len(state["residues"])


@pytest.mark.parametrize("name", sorted(GRAPH_FRAGMENT))
def test_state_leangraph_vs_pythongraph(name):
    """Final materialized state: Lean operational graph model == Python graph
    index, per corpus, under the documented projections (extractor.py).

    Since 2026-07-29 this also compares edge MULTIPLICITY exactly on the
    untainted arm (P3 as narrowed; `CORRESPONDENCE.md` §7.2). That half is real
    content, not a formality — measured 2026-07-29, over the 23 corpora then in
    the fragment: 153 of the 171 edges then compared carried a multiplicity
    nothing had ever compared, and one was genuinely non-unit (`nary_union`
    routes `alice` onto the untainted `any_of` from all three arms — both sides
    say 3).

    SABOTAGE EVIDENCE (run 2026-07-29, on the fragment as of then), literal
    observed output — note each failed on EXACTLY the one corpus that then had
    a non-unit untainted multiplicity, which is what shows the check has precise
    content rather than being a blanket assertion:
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

    Measured 2026-07-29 when the ledger was created, over the 23 corpora then in
    the fragment: 18 derived-arm edges, Python all 1, Lean 4 … 1013.

    SABOTAGE EVIDENCE (docs/sabotage-procedure.md; run 2026-07-29 on the
    23-corpus fragment, when the anti-vacuity floors were 18/18 — the two
    floor-sabotage literals below read accordingly; the floors' own comment
    above carries the 2026-08-09 re-run at 19/19), literal observed output:
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

    ZT-P4-5(d), measured 2026-07-27: before this corpus, all 11 residue rows in
    the whole curated state gate had `|stars| == 1` and `|neg| == 1`, so
    `diff_states`' set comparison of those fields had never had to distinguish
    two elements from one, and (same 2026-07-27 measurement) 16 of the 21
    corpora then in the fragment compared two EMPTY residue dicts. A corpus added
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
    Measured 2026-07-27, across the corpora then in the fragment: of 235
    `NodeV4` rows, 194 were edge/residue endpoints of the COMPARED state and
    thus pinned
    implicitly by the edge+residue equality above; the other **41 are invisible
    to the gate entirely** — they exist only to carry P1-dropped closure rows or
    P6-dropped leaf-family edges.

    So this test gates the one node-level property that is checkable Python-side
    and is a real failure mode the state comparison cannot see: a leaked node
    (GC that failed to fire) is invisible to an edge/residue diff. Measured
    2026-07-27 across every corpus then in the fragment: 0 orphans."""
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


def test_no_corpus_nests_a_pure_union_inside_an_impure_one():
    """The binary `Expr` cannot represent Python's leaf allocation for a NESTED union.

    `Core/Schema.lean`'s header models n-ary `or`/`and` as left folds of the binary
    node, justified by associativity+commutativity. That is true of `sem` and **false
    of the leaf ALLOCATION** `GraphIndex/Leaf.lean::persistedLeaves` models, because
    `zanzibar_utils_v1.py::_build_plan_tree` merges a union only when the WHOLE n-ary
    node is `_is_pure`. Measured 2026-08-16 on live compiles:

        r: a or b or safe      ->  2 leaves   (a@0, b@1; `safe` derived, no index)
        r: (a or b) or safe    ->  1 leaf     (the inner pure union MERGES)
        r: a or (b or safe)    ->  2 leaves

    and `formal/conformance/encode.py::_fold_binary` maps the first two to the SAME
    Lean `Expr`. So the model is necessarily faithful to only one of them; it models
    the FLAT form (`LeafWitness.smN_models_the_flat_form` states that as a theorem).

    This test refuses the shape that would make the choice observable: an `Intersection`
    or `Union` child that is itself a `Union` **and** is pure while its parent is not.
    A doc warning would not survive; a mechanical refusal does.

    ANTI-VACUITY: the scan is asserted to have visited a non-trivial number of union
    nodes, so a corpus that stopped containing unions could not pass this silently.

    SABOTAGE-VERIFIED (S15, 2026-08-16). Rewriting `nary_union_derived4`'s
    `define any_of4: a or b or c or safe` as `(a or b) or c or safe` -- semantically
    identical, and green on every other gate in the project -- makes this fail with the
    literal output::

        AssertionError: A corpus schema nests a PURE union directly inside an IMPURE one:
              SCHEMAS:nary_union_derived4: doc#any_of4

    The anti-vacuity floor was ALSO sabotage-tested, by accident and usefully: its first
    draft carried an estimated `>= 18` and went red at the live 8.
    """
    from zanzibar_utils_v1 import (Union, Intersection, Exclusion, Direct, Computed,
                                   TTU, compute_taint, parse_schema_ast, _member_types)

    def is_pure(e, ot, tainted, ast):
        if isinstance(e, Direct):
            return all(not (r.predicate != '...' and (r.type, r.predicate) in tainted)
                       for r in e.restrictions)
        if isinstance(e, Computed):
            return (ot, e.relation) not in tainted
        if isinstance(e, TTU):
            if (ot, e.tupleset_rel) in tainted:
                return False
            return all((t, e.target_rel) not in tainted
                       for t in _member_types(ot, e.tupleset_rel, ast, frozenset()))
        if isinstance(e, Union):
            return all(is_pure(c, ot, tainted, ast) for c in e.children)
        return False

    import glob
    import os

    from formal.conformance import corpus as _corpus

    sources: list[tuple[str, str]] = []
    for _dname in ('SCHEMAS', 'MULTI_STRATUM_SCHEMAS', 'TTU_USERSET_SCHEMAS',
                   'SELF_REFERENTIAL_SCHEMAS'):
        _d = getattr(_corpus, _dname, None)
        if isinstance(_d, dict):
            sources += [(f"{_dname}:{k}", v[0]) for k, v in _d.items()]
    sources += [(f"fga:{os.path.basename(f)}", open(f).read())
                for f in sorted(glob.glob('tests/fga_schemas/*.fga'))]

    offenders = []
    unions_seen = 0
    for name, schema_text in sources:
        try:
            ast = parse_schema_ast(schema_text)
            tainted = compute_taint(ast)
        except Exception:                                   # not our concern here
            continue
        for (ot, rel), expr in ast.items():
            if (ot, rel) not in tainted:
                continue                                    # allocation only runs on derived keys
            stack = [expr]
            while stack:
                e = stack.pop()
                if isinstance(e, Union):
                    unions_seen += 1
                    if not is_pure(e, ot, tainted, ast):
                        for c in e.children:
                            if isinstance(c, Union) and is_pure(c, ot, tainted, ast):
                                offenders.append((name, ot, rel))
                    stack.extend(e.children)
                elif isinstance(e, Intersection):
                    stack.extend(e.children)
                elif isinstance(e, Exclusion):
                    stack.extend([e.base, e.subtract])

    # FLOOR PROVENANCE: **8** union nodes under derived keys, MEASURED 2026-08-16
    # across all four corpus dicts in corpus.py plus every tests/fga_schemas/*.fga.
    # Floored just below live so adding a corpus is free and losing union coverage is
    # loud. (The first draft of this floor was written as 18 from an ESTIMATE and went
    # red on its first run -- which is the floor doing its job: the number is measured,
    # not guessed.)
    assert unions_seen >= 6, (
        f"ANTI-VACUITY: only {unions_seen} union node(s) scanned across derived keys — "
        f"the refusal below would pass having examined essentially nothing")
    assert not offenders, (
        "A corpus schema nests a PURE union directly inside an IMPURE one:\n"
        + "\n".join(f"    {n}: {t}#{r}" for n, t, r in sorted(set(offenders)))
        + "\n\nPython's `_build_plan_tree` merges that inner union into ONE leaf, but "
          "`encode.py::_fold_binary` left-folds it into a shape indistinguishable from "
          "the FLAT n-ary form, which `GraphIndex/Leaf.lean::persistedLeaves` allocates "
          "as one leaf PER member. The Lean model would therefore mis-index this key's "
          "leaf family, invisibly today (projection P6 drops leaf edges) and as a "
          "`diff_states` divergence the moment leg 7 step 7 retires P6.\n"
          "Either rewrite the schema in flat n-ary form (same semantics, same "
          "allocation) or make `Expr` n-ary — see Leaf.lean's 2026-08-16b block.")
