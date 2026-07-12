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
     Honesty note (probed 2026-07-12): on ALL 15 `GRAPH_FRAGMENT` corpora the
     compiled `bridged_in_shapes`/`bridged_out_shapes` are EMPTY — bridges
     arise only for wildcard-userset / object-wildcard shapes, both outside
     `W4Fragment` — so P2 currently never fires; it is kept (and documented)
     for robustness if the corpus set ever widens, not because it is
     load-bearing today.
  P3 **Multiplicity.** Python ref-counts a repeated direct edge in one row
     (`direct_edge_count = 2`); the model's edge list repeats the pair. Both
     sides compare as SETS (the Lean dump already deduplicates).
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


# --------------------------------------------------------------------------- #
# Python side
# --------------------------------------------------------------------------- #

def extract_sql_state(session, store_id: str) -> dict:
    """Read the canonical state off the SQL tables (projections P1–P3, P5)."""
    from index_v4.models import EdgeV4, NodeV4, ResidueV1

    nodes: dict[int, NodeKey] = {
        n.id: (n.type, n.name, n.predicate, n.wildcard)
        for n in session.exec(
            select(NodeV4).where(NodeV4.store_id == store_id)).all()
    }

    edges = set()
    for e in session.exec(
            select(EdgeV4).where(EdgeV4.store_id == store_id)).all():
        if e.direct_edge_count <= 0:
            continue                                    # P1: closure-only row
        subj, obj = nodes[e.subject_id], nodes[e.object_id]
        if obj[3] == "any" or subj[3] == "all":
            continue                                    # P2: bridge edge
        if "." in obj[2] and obj[2] != "...":
            continue                                    # P6: leaf-family copy
        edges.add((subj, obj))                          # P3: set, not multiset

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
        residues[key] = (stars, _subjects(r.neg, "neg"),
                         _subjects(r.upos, "upos"))

    return {"edges": frozenset(edges), "residues": residues}


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
    return {"edges": edges, "residues": residues}


# --------------------------------------------------------------------------- #
# The diff
# --------------------------------------------------------------------------- #

def diff_states(lean: dict, py: dict) -> str | None:
    """Symmetric-difference diff of two canonical states; None iff equal."""
    lines: list[str] = []

    only_lean = sorted(lean["edges"] - py["edges"])
    only_py = sorted(py["edges"] - lean["edges"])
    for e in only_lean:
        lines.append(f"  edge only in LEAN model : {e[0]} -> {e[1]}")
    for e in only_py:
        lines.append(f"  edge only in PYTHON     : {e[0]} -> {e[1]}")

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
