"""Board row `P17` — the BULK-BUILT index pinned to the model-driven state.

`test_conformance_state.py::test_state_leangraph_vs_pythongraph` pins the final
materialized state of an index GROWN write-by-write (`backends.graphindex_drive`:
rule routing + same-transaction cascade, the synchronous v1 path) against the
Lean operational graph model. That is the only construction the proof knows:
the `ReachedBy` chain's sole base constructor is `empty`
(`formal/lean/ZanzibarProofs/GraphIndex/CascadeStrataAssemble.lean`,
`ReachedByW3d2E`), so every headline theorem quantifies over indexes reached
from `emptyState` by logged writes and cascades.

`connectedstore.build_index` — the production bootstrap — does NOT build an
index that way. Its default `bulk=True` (`connectedstore/build.py`) hands the
tuple snapshot to `index_v4/bulk_build.py`, which routes every tuple once,
computes closed-form path counts, runs the in-memory boolean backfill
(`bulk_backfill.py`) and bulk-INSERTs the final rows. Nothing in the proof
describes that constructor; and until this module, nothing in
`formal/conformance/` exercised it either (the only pins were Python-vs-Python:
`tests/test_bulk_build.py::test_bulk_build_identical_to_incremental` over its
`_CORPORA`, and `tests/test_connectedstore_build.py::test_built_index_equals_live_maintained`
over one fixed history).

This module closes that with a two-legged differential per `GRAPH_FRAGMENT`
corpus, `test_state_bulkbuild_vs_pythongraph`:

  1. **EXACT equality against the write-by-write Python state** — the anchor,
     because it is the state the existing differential has already pinned to
     the Lean model (so equality here is Lean-anchoring by transitivity, on the
     same canonical form: `extractor.extract_sql_state`, projections P1/P2/P5/P7).
     Both sides are Python, so there is no P3 exemption on this leg: edge
     MULTIPLICITY is compared exactly on the DERIVED arm too (Python's
     `_reconcile_subject` writes derived edges by presence diff, uniformly 1,
     and `bulk_backfill` must reproduce exactly that), plus the per-edge
     `EdgeV4.derived` flag (I5) and every residue triple.
  2. **`diff_states(lean, bulk)` directly** — the same projections and the same
     P3 derived-arm drop as the existing gate, so the bulk state is ALSO pinned
     to the model without going through leg 1's anchor. Redundant if leg 1 and
     the sibling test are both green; kept so this test is a Lean anchor on its
     own and not merely a Python identity gate parked in `formal/`.

What this does NOT cover, said plainly:

  * **Remove histories.** Every `GRAPH_FRAGMENT` corpus is an add-only tuple
    list (that is what `graphindex_drive` replays), so the snapshot the bulk
    side builds from is the whole list and the "surviving tuples" are all of
    them. A bulk build over a store whose log contains REMOVEs is pinned only
    by `tests/test_connectedstore_build.py::test_built_index_equals_live_maintained`
    (one history, one remove).
  * **The outbox.** `bulk_build.py` writes exactly one `ADDED` row per final
    closure pair by design (Phase W (3)); the incremental path's outbox is a
    per-write delta history. Neither is in the canonical state, and the Lean
    `graph-state` dump has no outbox channel. `tests/test_bulk_build.py`
    compares the outbox as a multiset against `bulk=False`.
  * **Bridges / crossable middles (P2, I14).** Measured 2026-09-06: every one
    of the 25 in-fragment corpora compiles EMPTY `bridged_in_shapes` /
    `bridged_out_shapes` (`extractor.py` P2 paragraph, re-measured 2026-08-09),
    so `bulk_build.py`'s Phase B and its I14 crossable-middle loop are reached
    by NO corpus here — see the INERT sabotage below. Phase B (plain bridges)
    is pinned by `tests/test_bulk_build.py` (`wildcards`, `rc2_star_tupleset`).
    The I14 loop is pinned by NOTHING: the same sabotage left every
    `build_index` caller in `tests/` green, because no bulk-built corpus in
    the tree has a crossable shape (evidence in the test docstring).
  * **The materialized CLOSURE — Phase P's path counts and the pure-indirect
    rows.** The canonical form is `extract_sql_state`'s, and its P1 keeps only
    rows with `direct_edge_count > 0`; `indirect_edge_count` is never read.
    So the one thing `bulk_build.py` computes that the incremental path does
    NOT (the closed-form `pvec` DP, Phase P) is INVISIBLE to both legs here:
    clamping `indirect_edge_count` to `min(1, ...)`, or writing no
    pure-indirect row at all, leaves this module green (literal output in the
    test docstring). Those are pinned ONLY by `tests/test_bulk_build.py`
    (`snapshot_rows` compares every `EdgeV4` column as a multiset), so this
    module pins the bulk-built DIRECT multigraph + derived flags + residues
    to the model-driven state — not the closure rows a `check` actually reads.

Skips cleanly if the Lean binary is not built (verify.sh preflights the
binary, so the hard gate never runs skipped).
"""

from __future__ import annotations

import pytest

from formal.conformance import runner
from formal.conformance.corpus import SCHEMAS, GRAPH_FRAGMENT
from formal.conformance.extractor import (
    derived_relations,
    diff_states,
    lean_graph_state,
    python_bulk_graph_state,
    python_graph_state,
)


# Anti-vacuity floor on the number of canonical state rows on EACH side. Same
# value and reasoning as `test_conformance_state._MIN_STATE_ROWS`: 1 = the
# thinnest real corpus state (`wildcard_public`); 0 on either side means the
# extraction collapsed and an exact comparison of two empty dicts is green.
_MIN_STATE_ROWS = 1


def _n_rows(state) -> int:
    return len(state["edges"]) + len(state["residues"])


def _exact_state_diff(inc: dict, bulk: dict) -> str | None:
    """Field-by-field EXACT diff of two `extract_sql_state` dicts; None iff equal.

    Deliberately not `diff_states`: that applies the P3 derived-arm drop (a Lean
    model artifact) and ignores `derived_flag`. Both sides here are Python, so
    every key OF THE CANONICAL FORM is compared with no exemption — but the
    canonical form is already `extract_sql_state`'s projection (P1 direct rows
    only, P2, P5 no nodes, P7 no residue version); see the module docstring's
    "materialized CLOSURE" bullet for what that leaves unpinned here.
    """
    lines: list[str] = []
    for e in sorted(inc["edges"] - bulk["edges"]):
        lines.append(f"  edge only in INCREMENTAL : {e[0]} -> {e[1]}")
    for e in sorted(bulk["edges"] - inc["edges"]):
        lines.append(f"  edge only in BULK        : {e[0]} -> {e[1]}")
    for k in sorted(set(inc["edge_counts"]) & set(bulk["edge_counts"])):
        iv, bv = inc["edge_counts"][k], bulk["edge_counts"][k]
        if iv != bv:
            lines.append(f"  edge MULTIPLICITY {k[0]} -> {k[1]}: "
                         f"incremental={iv} bulk={bv}")
        fi, fb = inc["derived_flag"][k], bulk["derived_flag"][k]
        if fi != fb:
            lines.append(f"  edge DERIVED flag {k[0]} -> {k[1]}: "
                         f"incremental={fi} bulk={fb}")
    ikeys, bkeys = set(inc["residues"]), set(bulk["residues"])
    for k in sorted(ikeys - bkeys):
        lines.append(f"  residue only in INCREMENTAL : {k} = {inc['residues'][k]}")
    for k in sorted(bkeys - ikeys):
        lines.append(f"  residue only in BULK        : {k} = {bulk['residues'][k]}")
    for k in sorted(ikeys & bkeys):
        for field, iv, bv in zip(("stars", "neg", "upos"),
                                 inc["residues"][k], bulk["residues"][k]):
            if iv != bv:
                lines.append(
                    f"  residue {k} field {field}: only-incremental="
                    f"{sorted(iv - bv)} only-bulk={sorted(bv - iv)}")
    return "\n".join(lines) if lines else None


@pytest.mark.parametrize("name", sorted(GRAPH_FRAGMENT))
def test_state_bulkbuild_vs_pythongraph(name):
    """`build_index(bulk=True)` lands on EXACTLY the state the logged write path
    lands on — and that state diffs clean against the Lean model — per corpus.

    Leg 1 is exact (both arms' multiplicity, `derived` flag, residues) against
    `python_graph_state`; leg 2 is `diff_states(lean, bulk)` under the state
    gate's documented projections. See the module docstring for why the
    write-by-write Python state is the anchor and what is out of scope.

    ★ SABOTAGE EVIDENCE (2026-09-06, `docs/sabotage-procedure.md`), literal
    observed output, all on the 25-corpus fragment (module runs are
    ``26 passed`` = 25 corpora + `test_bulk_leg_covers_graph_fragment_exactly`):

      * **The suggested sabotage is INERT — and inert EVERYWHERE, which is the
        finding.** `if crossable:` -> `if False:` in `bulk_build.py` (deleting
        the whole I14 crossable-middle loop, `:206-221`) leaves this module
        GREEN, ``26 passed in 10.02s``; disabling Phase B's bridge loop
        (`for key in concretes:` -> `for key in ():`) likewise, ``26 passed``.
        Expected here: no in-fragment corpus compiles a bridged shape (P2 drops
        0 rows fragment-wide, `extractor.py`), so those phases have nothing to
        write. NOT expected: the I14 edit ALSO leaves every other
        `build_index` caller green — `tests/test_bulk_build.py` +
        `test_connectedstore_build.py` + `test_zt_p5_readjudication.py` +
        `test_i14_crossing_middles.py`: ``37 passed in 105.87s``;
        `test_residue_ref_index.py` + `test_ttu_tupleset_parent_types.py`:
        ``24 passed``. Measured cause: none of `test_bulk_build.py`'s
        `_CORPORA` has a CROSSABLE shape (`wildcards` is bridged in on `(group, member)`
        and out on `(folder|document, viewer)` — never the same shape both
        ways; `rc2_star_tupleset` is in-only). So `bulk_build.py`'s I14 mirror
        is pinned by no test in the tree. Filed as a finding, not fixed here.
      * Phase W `'direct_edge_count': min(1, m.get((a, b), 0))` — the plausible
        "a pair is present or it isn't" de-dup accident — fails on EXACTLY the
        one corpus with a non-unit untainted multiplicity::

            AssertionError: [nary_union] bulk-built state != write-by-write
            state (P17 — ...):
              edge MULTIPLICITY ('user', 'alice', '...', '') ->
              ('doc', 'd1', 'any_of', ''): incremental=3 bulk=1
            1 failed, 25 passed in 14.87s

        Under the same edit, leg 2 alone (`diff_states(lean, bulk)`) reports
        ``edge MULTIPLICITY (untainted arm, P3) ... lean=3 python=1`` — so the
        Lean anchor sees it without leg 1.
      * Phase W `'derived': False` on every edge row (dropping the
        processor-written stamp — the I5 half of the comparison, which
        `diff_states` never looks at) fails on exactly the corpora that have a
        derived arm (11 of them on the fragment as it was 2026-09-06), first::

            AssertionError: [boolean_exclusion] bulk-built state != ...:
              edge DERIVED flag ('user', 'alice', '...', '') ->
              ('doc', 'd1', 'viewer', ''): incremental=True bulk=False
            11 failed, 15 passed in 14.29s

      * Phase W residues written with `'upos': '[]'` (the residue arm only two
        corpora reach with a non-empty value) fails on exactly those two::

            AssertionError: [residue_rich] bulk-built state != ...:
              residue ('doc', 'd1', 'approver') field upos:
              only-incremental=[('group', 'eng', 'member')] only-bulk=[]
            FAILED ...[residue_rich]
            FAILED ...[taint_union_userset_arm]
            2 failed, 24 passed in 12.68s

      * ★ **GREEN by construction (review 2026-09-06): the CLOSURE.** Phase W
        `'indirect_edge_count': min(1, pvec[a][b])` (Phase P's path counts
        collapsed to presence — the weakening the "path-count clamp" above
        was described as but is not; that one clamps Phase R's DIRECT
        multiplicity) leaves this module green, ``26 passed in 13.08s``; so does
        writing NO pure-indirect closure row at all (`edge_pairs` filtered on
        `m.get((a, b), 0) > 0` instead of `pvec[a][b] > 0`), ``26 passed in
        10.54s``. Cause: P1 in `extract_sql_state` keeps `direct_edge_count > 0`
        rows only and never reads `indirect_edge_count`. Both are RED in
        `tests/test_bulk_build.py` (``1 failed`` under `-x`,
        ``[wildcards] snapshot_rows differ``), which is therefore the ONLY pin
        on the bulk closure — this module does not replace it.
      * The INSTRUMENT: `bulk_build_drive` seeding only `tuples[1:]` (the
        snapshot silently one tuple short) is refused before any comparison
        runs (`group_userset`)::

            AssertionError: bulk_build_drive: 2 TupleV1 row(s) landed for a
            corpus of 3 tuple(s) — the snapshot build_index will read is not
            the tuple list graphindex_drive replays (a duplicate the source
            deduplicated, or a rejected write). Refusing to compare two
            different stores.
            1 failed in 0.95s
    """
    schema_text, tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    inc = python_graph_state(schema_text, tuples, obj_wild)
    bulk = python_bulk_graph_state(schema_text, tuples, obj_wild)

    # ANTI-VACUITY (ZT-P4-4): two empty states compare equal. Both sides must
    # have produced state before their agreement means anything.
    assert _n_rows(inc) >= _MIN_STATE_ROWS and _n_rows(bulk) >= _MIN_STATE_ROWS, (
        f"[{name}] ANTI-VACUITY: state extraction collapsed — incremental has "
        f"{len(inc['edges'])} edge(s)/{len(inc['residues'])} residue(s), bulk has "
        f"{len(bulk['edges'])}/{len(bulk['residues'])} (floor {_MIN_STATE_ROWS} "
        f"row each). Two EMPTY states compare equal, so the assertions below "
        f"would pass having compared nothing.")

    # Leg 1: EXACT — no P3 exemption, both arms, derived flag, residues.
    diff = _exact_state_diff(inc, bulk)
    assert diff is None, (
        f"[{name}] bulk-built state != write-by-write state (P17 — the bulk "
        f"constructor has drifted from the modeled logged path; both sides are "
        f"Python, nothing in the canonical form is exempted):\n{diff}")

    # Leg 2: the Lean anchor, directly, under the state gate's projections.
    lean = lean_graph_state(schema_text, tuples, obj_wild)
    assert _n_rows(lean) >= _MIN_STATE_ROWS, (
        f"[{name}] ANTI-VACUITY: the Lean state extraction collapsed "
        f"({len(lean['edges'])} edge(s)/{len(lean['residues'])} residue(s))")
    ldiff = diff_states(lean, bulk, derived_relations(schema_text))
    assert ldiff is None, (
        f"[{name}] Lean graph model / BULK-BUILT Python index STATE disagreement "
        f"(ADJUDICATION EVENT — plan §8.2; symmetric difference):\n{ldiff}")


def test_bulk_leg_covers_graph_fragment_exactly():
    """The bulk differential runs over the SAME corpus set as the state gate.

    `test_state_bulkbuild_vs_pythongraph` is parametrized over
    `sorted(GRAPH_FRAGMENT)` by construction, so this cannot drift today; it
    exists so that a future re-parametrization (a hand-picked subset "because
    the others are slow") is a visible edit to a named pin rather than a quiet
    narrowing. It also pins the fragment against collapsing: the docs cite this
    module as covering N corpora, and N must be the live `len(GRAPH_FRAGMENT)`,
    never a restated number.
    """
    # `pytestmark` carries the decorator's argument list; the corpus names are
    # its second positional argument.
    names: set[str] = set()
    for m in test_state_bulkbuild_vs_pythongraph.pytestmark:
        if m.name == "parametrize":
            names |= set(m.args[1])
    assert names == set(GRAPH_FRAGMENT), (
        f"bulk differential parametrized over {sorted(names)}, GRAPH_FRAGMENT is "
        f"{sorted(GRAPH_FRAGMENT)} — the bulk leg no longer covers the state "
        f"gate's corpus set")
    # FLOOR PROVENANCE: 25 = `len(GRAPH_FRAGMENT)` measured 2026-09-06
    # (`python -c "from formal.conformance.corpus import GRAPH_FRAGMENT;
    # print(len(GRAPH_FRAGMENT))"`). Set AT reality: adding a corpus is free,
    # losing one is loud.
    assert len(GRAPH_FRAGMENT) >= 25, (
        f"GRAPH_FRAGMENT shrank to {len(GRAPH_FRAGMENT)} corpora; the bulk leg's "
        f"documented width is stated against the live fragment")
