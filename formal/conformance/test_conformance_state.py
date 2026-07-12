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
`extractor.py` (P1 closure rows, P2 bridges, P3 multiplicity, P4 empty
residues, P5 nodes, P6 leaf-family split). Nothing else is dropped: a
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

Skips cleanly if the Lean binary is not built (verify.sh preflights the
binary, so the hard gate never runs skipped).
"""

from __future__ import annotations

import pytest

from formal.conformance import runner
from formal.conformance.corpus import SCHEMAS, GRAPH_FRAGMENT
from formal.conformance.extractor import (
    diff_states,
    lean_graph_state,
    python_graph_state,
)


@pytest.mark.parametrize("name", sorted(GRAPH_FRAGMENT))
def test_state_leangraph_vs_pythongraph(name):
    """Final materialized state: Lean operational graph model == Python graph
    index, per corpus, under the documented projections (extractor.py)."""
    schema_text, tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    lean = lean_graph_state(schema_text, tuples, obj_wild)
    py = python_graph_state(schema_text, tuples, obj_wild)

    diff = diff_states(lean, py)
    assert diff is None, (
        f"[{name}] Lean graph model / Python graph index STATE disagreement "
        f"(ADJUDICATION EVENT — plan §8.2; symmetric difference):\n{diff}")
