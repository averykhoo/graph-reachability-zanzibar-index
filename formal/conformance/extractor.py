"""State-level graph conformance — the canonical-state extractors (G1,
FINAL_REVIEW §4(a)).

Two extractors producing THE SAME representation-neutral canonical form:

  * `python_graph_state` — drive the real `WildcardIndex` + `DeltaProcessor`
    through the synchronous v1 write path (exactly as `graphindex_answers` /
    `test_conformance_graph.py` do — same `graphindex_drive` helper), then read
    the final SQL state (`NodeV4` / `EdgeV4` / `ResidueV1` rows) back out.
  * `lean_graph_state` — run `zcli` mode `"graph-state"` (the `graphRun` fold of
    the `ReachedBy` chain's own constructors, `GraphIndex/Exec.lean` +
    `Cli.lean`) and parse its canonical JSON.

Canonical form::

    {"edges":    frozenset of (subj_key, obj_key),
     "residues": {(obj_type, obj_name, relation):
                      (stars, neg, upos)}}         # three frozensets

with node keys the SYMBOLIC `(type, name, predicate, wildcard)` 4-tuples
(`wildcard` in `''`/`'any'`/`'all'` — the `NodeV4.wildcard` encoding, which the
Lean side maps its `Variant` onto), `stars` a frozenset of `(type, predicate)`
shapes, and `neg`/`upos` frozensets of `(type, name, predicate)` subject
triples (Python node ids decoded through `NodeV4`).

The encodings differ BY DESIGN (HANDOFF item 1), so the comparison applies the
following documented projections — nothing else is dropped, and a mismatch
outside these classes fails the gate:

  P1 **Closure rows.** Python materializes the transitive closure as `EdgeV4`
     rows; the Lean model computes reachability on demand from direct edges
     only. Projection: keep only rows with `direct_edge_count > 0` — the
     closure is a FUNCTION of the direct set, so equality of the direct sets
     pins the closure too (and check-parity over the shared grid observes it).
  P2 **Wildcard bridges.** Python materializes bridge edges (`concrete →
     w_any` in-bridges and `w_all → concrete` out-bridges,
     `wildcard.py:_ensure_bridges`) so `check` stays O(1); the Lean model
     never creates them — its read probes the `w_any`/`w_all` endpoints
     directly (`probeNonDerived`, `State.lean`). The model creates NO edge
     into a `w_any` node and NO edge out of a `w_all` node (grant edges run
     `w_any → object` and `subject → w_all`), so the bridge classes are
     exactly identifiable: drop Python direct edges whose TARGET is a `w_any`
     node or whose SOURCE is a `w_all` node.
     Honesty note (probed 2026-07-12; RE-MEASURED 2026-07-27 over the 21
     then-current corpora — 447 raw edge rows, 0 dropped; **RE-MEASURED AGAIN
     2026-07-29 over all 23 current `GRAPH_FRAGMENT` corpora — 477 raw edge
     rows, P2 dropped 0 of them**, and the compiled
     `bridged_in_shapes`/`bridged_out_shapes` are EMPTY on every one of the 23):
     bridges arise only for wildcard-userset / object-wildcard shapes,
     both outside `W4Fragment`, so P2 still never fires; it is kept (and
     documented) for robustness if the corpus set ever widens, not because it
     is load-bearing today. Re-measure this when `GRAPH_FRAGMENT` grows — the
     claim is only as current as the corpus set it was measured over, which is
     how it went stale at 19 and again at 21.
  P3 **Multiplicity — NARROWED 2026-07-29 to the DERIVED arm only; the
     untainted arm is now compared EXACTLY.** This projection used to read
     "Python ref-counts a repeated direct edge in one row
     (`direct_edge_count = 2`); the model's edge list repeats the pair. Both
     sides compare as SETS (the Lean dump already deduplicates)" — i.e. it
     asserted the two multiplicities CORRESPOND and only the representation
     differs, and dropped both. That was wrong in two ways, and it is the
     adjudication of `CORRESPONDENCE.md` §7.2.

     **(a) The claim is false on the derived arm.** Python writes a
     processor-derived edge by a presence DIFF —
     `index_v4/processor.py::DeltaProcessor._reconcile_subject` computes
     `want_edge and not has_edge` — so a re-derived edge changes NOTHING and
     `direct_edge_count` on such a row is always 0 or 1. The Lean model has no
     presence test (`GraphIndex/Write.lean::admitEdge` is `(a != b) && !reach b a`;
     `GraphIndex/State.lean::addEdge` conses unconditionally) and its cascade
     re-enumerates every existing copy (`GraphIndex/CascadeEnum.lean::edgeHolders`),
     so multiplicity compounds per cascade leg.

     **(b) The drop was hiding a correspondence that HOLDS.** On edges whose
     target relation is NOT derived, the model's list multiplicity and Python's
     `direct_edge_count` agree exactly — including the genuinely non-unit case
     (`nary_union` routes `alice` onto the untainted `any_of` from all three
     arms: both sides say 3). Dropping that was pure lost assurance.

     Projection as it now stands: compare `direct_edge_count`-weighted
     multiplicity EXACTLY on every edge whose target relation is untainted, and
     drop it only on edges into a derived (boolean-tainted) relation, where it
     is a declared model artifact. The dropped quantity is not un-gated — it is
     pinned per corpus against a golden by
     `test_conformance_state.py::test_derived_arm_multiplicity_ledger`, so the
     artifact's SHAPE is now a checked quantity rather than an invisible one.

     **Measured 2026-07-29** over all 23 `GRAPH_FRAGMENT` corpora: of 171
     compared edges, **153 are untainted-arm and agree exactly** (152 at
     multiplicity 1, one at 3) and **18 are derived-arm and all diverge** —
     Python uniformly 1, Lean 4 … **1013** (`two_stratum_cascade`). Note the
     Lean growth is worse than the `1 → 2 → 4 → 8` recorded in
     `CORRESPONDENCE.md` §7.2 when the finding was filed: with several
     candidates at a key it compounds superlinearly.

     The exemption is decided from the SCHEMA (`zanzibar_utils_v1.compute_taint`),
     not from `EdgeV4.derived`, so a mis-set flag cannot silently move the
     boundary — and the two classifications are cross-checked against each other
     (`_classify_edges`), which is itself a new I5-adjacent pin.
  P4 **Empty residues.** Python deletes an all-empty residue row
     (`processor._store_residue`: "empty residues are deleted, never
     stored"); the Lean model stores possibly-empty rows
     (`reconcileResidueKey`, read-equivalent via `getD Residue.empty`). The
     Lean dump emits its rows RAW so the divergence stays observable;
     `lean_graph_state` applies the documented drop here.
  P5 **Nodes are not compared.** Python GCs implicit nodes at refcount 0 and
     the processor GCs derived-public anchors; the model never removes a node
     (and never creates bridge endpoints' `w` nodes). Node sets differ by
     design; the state gate compares what nodes MEAN — edges and residues.
     **Precisely what P5 costs (ZT-P4-5(c), measured 2026-07-27).** It is not
     "the Lean model has no nodes": `GraphIndex/State.lean::GraphState` HAS a
     `nodes : List NodeKey` field. Three separate facts make it uncomparable:
     (i) zcli's `"graph-state"` dump emits only `edges` and `residues`
     (`Cli.lean::stateJson` has no node key), so no node data crosses the seam
     at all; (ii) even if it did, the model never GCs while Python does, so
     node-SET equality is false by design — the gate would have to compare a
     projection, and any projection weak enough to hold is implied by the edge
     and residue equality already asserted; (iii) there is no comparable node
     PROPERTY — Python's `NodeV4.implicit` and `NodeV4.reference_count` have no
     counterpart in Lean's `NodeKey` (which is just `(type, name, pred,
     variant)`). Quantified: of **235** `NodeV4` rows across the in-fragment
     corpora, **194** are endpoints/references of the COMPARED state and so are
     pinned implicitly by the edge+residue equality; the remaining **41** are
     invisible to this gate entirely — they exist only to carry P1-dropped
     closure rows or P6-dropped leaf-family edges. What IS gated instead, and
     Python-side only:
     `test_conformance_state.py::test_python_nodes_are_all_justified` (no orphan
     node rows; 0 orphans measured across every in-fragment corpus). Node FLAG
     behaviour remains, in `CORRESPONDENCE.md` §7's words, "invisible to the
     gate by construction" — the concession is now quantified, and repeated in
     `FINAL_REVIEW.md` §3 / `ARCHITECTURE.md` §6.
  P6 **Leaf-family storage split.** Python's compiler routes a boolean def's
     untainted operand relations onto `<relation>.<index>` closure-leaf
     families (`RuleSet.apply` emits e.g. `editor` -> `viewer.0` copies —
     observed even on ComputedOnly defs, correcting `CORRESPONDENCE.md` §7's
     "the shapes coincide" note, which holds only for `storage=True` leaves:
     `storage=False` closure leaves still hold routed edges). The Lean model
     deliberately has NO leaf-family split (CORRESPONDENCE §7 divergence 4) —
     it reads the raw boolean defs. Projection: drop Python direct edges
     whose TARGET predicate contains `'.'` — `'.'` is reserved in declared
     relation names (`zanzibar_utils_v1`), so such a family can only be
     compiler-generated. The dropped edges' CONTENT is not unpinned: the
     compiled plans read exactly these leaves, and their evaluation output —
     the residues and processor-written derived edges — is compared EXACTLY
     here, on top of check-verdict conformance and the compiled-RuleSet
     snapshot tests.

  P7 **`ResidueV1.version` is dropped** (declared 2026-07-27, ZT-P4-5(b); it
     was being dropped SILENTLY before, which is the thing this projection
     fixes — an undeclared exclusion is indistinguishable from an oversight).
     `index_v4/models.py::ResidueV1` carries a `version` column, incremented by
     `index_v4/processor.py::DeltaProcessor._store_residue` on every changing
     reconcile and checked for monotonicity by invariant **I7**
     (`index_v4/invariants.py::_check_residue_rows`).
     **Reason it cannot be compared: the Lean model has no such field.**
     `GraphIndex/State.lean::Residue` is `⟨stars, neg, upos⟩` — its doc comment
     says so in as many words ("whose `version` column has NO Lean
     counterpart") — and `grep -rn 'version' lean/ZanzibarProofs/GraphIndex/`
     finds only that comment. There is no monotone counter anywhere in the
     model to compare against, so this is a MODELLING GAP, not a
     representation difference like P1–P6 (the other six): unlike those, no argument recovers
     the dropped information from what remains. It is recorded as such in
     `CORRESPONDENCE.md` §7.2, and the consequence is stated there and here:
     **I7 is gated by nothing formal.** Its only pins are Python-side —
     `index_v4/invariants.py` under paranoia mode in `tests/`. Concretely, the
     `version` values this gate throws away are real data: measured 2026-07-27,
     the 11 residue rows across the curated state gate carry versions 2 and 3
     (and the `residue_rich` corpus's rows 4 and 5), i.e. the counter is
     genuinely advancing and genuinely unobserved here.

Anything NOT projected — the direct grant/rewrite edge set (including
rule-routed fan-out and processor-written derived edges) and every non-empty
residue's stars/neg/upos — must be EQUAL, per corpus. This gate found P6 on
its first run (state-level divergence with full check-parity): the state gate
demonstrably fails on representation drift the verdict gate cannot see.
"""

from __future__ import annotations

import json

from sqlmodel import select

from formal.conformance import runner
from formal.conformance.backends import graphindex_drive
from formal.conformance.encode import build_request

NodeKey = tuple  # (type, name, predicate, wildcard)
SubjKey = tuple  # (type, name, predicate)


def derived_relations(schema_text: str) -> frozenset:
    """The `(type, relation)` pairs that compile to DERIVED (boolean-tainted)
    predicates — the P3 multiplicity exemption boundary.

    Read from the SCHEMA via `zanzibar_utils_v1.compute_taint`, deliberately not
    from `EdgeV4.derived`: the exemption must not be movable by the very flag a
    divergence would corrupt. `_classify_edges` cross-checks the two.
    """
    from zanzibar_utils_v1 import compute_taint, parse_schema_ast

    return compute_taint(parse_schema_ast(schema_text))


# --------------------------------------------------------------------------- #
# Python side
# --------------------------------------------------------------------------- #

def extract_sql_state(session, store_id: str) -> dict:
    """Read the canonical state off the SQL tables (projections P1–P2, P5–P7;
    P3 is applied by `diff_states`, which needs the schema's taint set).

    `edge_counts` carries `direct_edge_count`-weighted multiplicity for the same
    keys as `edges`; `derived_flag` records `EdgeV4.derived` per key so the
    schema-driven P3 exemption can be cross-checked against it.
    """
    from index_v4.models import EdgeV4, NodeV4, ResidueV1

    nodes: dict[int, NodeKey] = {
        n.id: (n.type, n.name, n.predicate, n.wildcard)
        for n in session.exec(
            select(NodeV4).where(NodeV4.store_id == store_id)).all()
    }

    edges = set()
    edge_counts: dict[tuple, int] = {}
    derived_flag: dict[tuple, bool] = {}
    for e in session.exec(
            select(EdgeV4).where(EdgeV4.store_id == store_id)).all():
        if e.direct_edge_count <= 0:
            continue                                    # P1: closure-only row
        subj, obj = nodes[e.subject_id], nodes[e.object_id]
        if obj[3] == "any" or subj[3] == "all":
            continue                                    # P2: bridge edge
        if "." in obj[2] and obj[2] != "...":
            continue                                    # P6: leaf-family copy
        edges.add((subj, obj))
        # P3: multiplicity is KEPT here and compared exactly on the untainted
        # arm; `diff_states` applies the derived-arm drop.
        edge_counts[(subj, obj)] = (edge_counts.get((subj, obj), 0)
                                    + e.direct_edge_count)
        derived_flag[(subj, obj)] = derived_flag.get((subj, obj), False) or e.derived

    residues: dict[tuple, tuple] = {}
    for r in session.exec(
            select(ResidueV1).where(ResidueV1.store_id == store_id)).all():
        obj = nodes.get(r.object_node_id)
        if obj is None:
            raise AssertionError(
                f"residue row {r.id} references missing node {r.object_node_id} "
                f"(dangling id — extraction cannot be trusted)")
        stars = frozenset((t, p) for (t, p) in json.loads(r.stars))

        def _subjects(ids_json: str, field: str) -> frozenset:
            out = set()
            for nid in json.loads(ids_json):
                n = nodes.get(nid)
                if n is None:
                    raise AssertionError(
                        f"residue row {r.id} {field} references missing node "
                        f"{nid} (dangling id)")
                out.add((n[0], n[1], n[2]))
            return frozenset(out)

        key = (obj[0], obj[1], r.relation)
        # P7: `r.version` is deliberately NOT part of the canonical form — Lean's
        # `Residue` has no such field, so there is nothing to compare it to. See
        # the P7 paragraph in the module docstring; I7 is gated Python-side only.
        residues[key] = (stars, _subjects(r.neg, "neg"),
                         _subjects(r.upos, "upos"))

    return {"edges": frozenset(edges), "edge_counts": edge_counts,
            "derived_flag": derived_flag, "residues": residues}


def python_graph_state(schema_text: str, tuples, object_wildcards=()) -> dict:
    """Drive the real graph index over the corpus, extract the final state."""
    session, _widx, store_id = graphindex_drive(schema_text, tuples,
                                                object_wildcards)
    try:
        return extract_sql_state(session, store_id)
    finally:
        session.close()


# --------------------------------------------------------------------------- #
# Lean side
# --------------------------------------------------------------------------- #

def lean_graph_state(schema_text: str, tuples, object_wildcards=()) -> dict:
    """Run zcli mode "graph-state" on the corpus and parse the canonical form.

    Applies projection P4 here (drop all-empty residue rows): the Lean dump
    emits its stored-but-empty rows raw, so the model/Python divergence is
    observable upstream of this documented drop.
    """
    raw = runner.run_state(build_request(schema_text, tuples, [],
                                         object_wildcards, mode="graph-state"))
    edges = frozenset(
        (tuple(subj), tuple(obj)) for subj, obj in raw["edges"])
    edge_counts: dict[tuple, int] = {}
    for (subj, obj), n in raw["edgeCounts"]:
        edge_counts[(tuple(subj), tuple(obj))] = n
    if set(edge_counts) != set(edges):
        raise AssertionError(
            "zcli edgeCounts / edges disagree on the key set — the multiplicity "
            "channel is not describing the same edges as the set channel "
            f"(only-counts={sorted(set(edge_counts) - set(edges))}, "
            f"only-edges={sorted(set(edges) - set(edge_counts))})")
    residues: dict[tuple, tuple] = {}
    for (ot, on, rel), stars, neg, upos in raw["residues"]:
        stars_s = frozenset((t, p) for (t, p) in stars)
        neg_s = frozenset((t, n, p) for (t, n, p) in neg)
        upos_s = frozenset((t, n, p) for (t, n, p) in upos)
        if not (stars_s or neg_s or upos_s):
            continue                                    # P4: empty row
        key = (ot, on, rel)
        if key in residues:
            raise AssertionError(f"duplicate residue key in zcli dump: {key}")
        residues[key] = (stars_s, neg_s, upos_s)
    return {"edges": edges, "edge_counts": edge_counts, "residues": residues}


# --------------------------------------------------------------------------- #
# The diff
# --------------------------------------------------------------------------- #

def _classify_edges(py: dict, tainted: frozenset) -> dict:
    """Split compared edge keys into derived-arm / untainted-arm by SCHEMA taint,
    cross-checking the classification against Python's own `EdgeV4.derived` flag.

    The two must agree: I5 makes the delta processor the only writer of incoming
    direct edges on derived-public families, and users' raw writes are routed onto
    `<rel>.<n>` leaf families which P6 already dropped. A disagreement means either
    the taint computation or the `derived` flag is wrong, and either way the P3
    exemption boundary is not where this module claims it is — so it raises rather
    than silently exempting the wrong set.
    """
    derived, untainted, bad = set(), set(), []
    for key in py["edge_counts"]:
        obj = key[1]
        by_schema = (obj[0], obj[2]) in tainted
        by_flag = py["derived_flag"].get(key, False)
        if by_schema != by_flag:
            bad.append((key, by_schema, by_flag))
        (derived if by_schema else untainted).add(key)
    if bad:
        raise AssertionError(
            "P3 edge classification disagreement (schema taint vs "
            "EdgeV4.derived) — the multiplicity exemption boundary is not "
            "where extractor.py claims:\n" + "\n".join(
                f"  {k[0]} -> {k[1]}: by_schema={s} by_flag={f}"
                for k, s, f in sorted(bad)))
    return {"derived": derived, "untainted": untainted}


def diff_states(lean: dict, py: dict, tainted: frozenset) -> str | None:
    """Symmetric-difference diff of two canonical states; None iff equal.

    `tainted` is the schema's derived `(type, relation)` pairs, from
    `derived_relations`; it drives projection P3 as narrowed 2026-07-29 — edge
    MULTIPLICITY is compared exactly on the untainted arm and dropped only on the
    derived arm.

    **It is REQUIRED, deliberately.** Defaulting it to `None` would mean a new
    caller that forgot it silently got the pre-2026-07-29 set-only comparison
    back — i.e. this gate quietly reopening the exact blind spot it was narrowed
    to close, at full green. That is this repo's house failure mode
    (`docs/sabotage-procedure.md`), so the signature refuses rather than the
    docstring warning.
    """
    lines: list[str] = []

    only_lean = sorted(lean["edges"] - py["edges"])
    only_py = sorted(py["edges"] - lean["edges"])
    for e in only_lean:
        lines.append(f"  edge only in LEAN model : {e[0]} -> {e[1]}")
    for e in only_py:
        lines.append(f"  edge only in PYTHON     : {e[0]} -> {e[1]}")

    arms = _classify_edges(py, tainted)
    for key in sorted(arms["untainted"] & set(lean["edge_counts"])):
        lv, pv = lean["edge_counts"][key], py["edge_counts"][key]
        if lv != pv:
            lines.append(
                f"  edge MULTIPLICITY (untainted arm, P3) {key[0]} -> "
                f"{key[1]}: lean={lv} python={pv}")

    lkeys, pkeys = set(lean["residues"]), set(py["residues"])
    for k in sorted(lkeys - pkeys):
        lines.append(f"  residue only in LEAN model : {k} = {lean['residues'][k]}")
    for k in sorted(pkeys - lkeys):
        lines.append(f"  residue only in PYTHON     : {k} = {py['residues'][k]}")
    for k in sorted(lkeys & pkeys):
        lres, pres = lean["residues"][k], py["residues"][k]
        for field, lv, pv in zip(("stars", "neg", "upos"), lres, pres):
            if lv != pv:
                lines.append(
                    f"  residue {k} field {field}: "
                    f"only-lean={sorted(lv - pv)} only-python={sorted(pv - lv)}")

    return "\n".join(lines) if lines else None
