"""Exec-driver remove hardening — interleaved add/remove op streams DRIVEN through
the Lean zcli graph mode (`graphRunOps`) vs the real Python graph index and the
oracle, over the `GRAPH_FRAGMENT` corpora.

The add-only graph conformance (`test_conformance_graph.py`) pins the Lean
operational graph model against the Python graph index for pure builds. The Lean
chain's remove leg is now complete (`ReachedByW3d2E.remove`) AND driven
end-to-end by `graphRunOps` (`GraphIndex/Exec.lean`), so this gate exercises
RETRACTION through the SAME honesty theorems (`graphRunOps_reached` /
`graphRunOps_check_eq_sem`) that `graph_correct` covers verbatim. Each op stream
is add / remove / re-add over the corpus tuple space (the SAME generator as
`test_conformance_remove.py`), landing on a strict-subset final store (>= 1 net
removal forced). The Lean driver fails CLOSED (nonzero rc, `runner.run_spec`
raises) on ANY out-of-scope op, so a green run is direct evidence that every op —
removes included — stayed inside the proved scope and the printed verdict IS
`sem` of the accepted final store.

We compare, per corpus x seed, on the driven final state:
  * Lean graph model (zcli `graphRunOps`)  vs  the real Python graph index driven
    through the identical op stream (`graphindex_drive_ops`) — THE Phase 6 pin,
    extended to removes;
  * Lean graph model  vs  oracle(accepted final store) — the independent
    correctness anchor (== `sem` transitively: `sem` == oracle is pinned repo-wide
    and by the sibling `test_conformance_remove.py`).

Scope discipline (apples-to-apples with `graph_correct`):
  * corpora: `GRAPH_FRAGMENT` only (inside GraphAdmission + W4Fragment);
  * universe: the corpus tuples THEMSELVES (no recombined extras), so every
    intermediate store is a SUBSET of a fragment store. The remove gate's store
    disciplines (`BareStarStore` / `TtuStarFree` / `StoreValidRules` / `htermT`)
    are all monotone under subset, so they hold throughout and the driver accepts
    the whole stream (rc 0);
  * queries: concrete objects only (`hqo`), star subjects bare (`hqs`) — as in
    `test_conformance_graph.py`.

Anti-vacuous: asserts every stream actually net-removes (a strict-subset final
store) AND the Lean driver's verdicts equal the oracle on that ERASED store — a
driver that silently dropped removes would answer on the full universe and be
caught here. Skips cleanly if the Lean binary is not built.
"""

from __future__ import annotations

import itertools
import random

import pytest

from tests.oracle import Oracle

from formal.conformance import runner
from formal.conformance.backends import graphindex_drive_ops
from formal.conformance.corpus import SCHEMAS, GRAPH_FRAGMENT
from formal.conformance.encode import build_request
from formal.conformance.grid import grid as _grid, fmt_mismatches as _fmt
# Reuse the exact interleaved add/remove/re-add generator the set-engine and
# graph remove gates already drive (same shapes, deterministic per seed).
from formal.conformance.test_conformance_remove import _sequence

SEEDS = [0, 1, 2]

# Op-universe cap. A cascade leg's cost grows sharply with store size for the
# stratum-heavy schemas (an add-only `two_stratum_cascade` build is ~18s at 5
# tuples), and `graphRunOps` re-cascades after EVERY op, so a full-corpus churn
# stream blows the per-spawn zcli timeout. Capping the op universe to 3 tuples
# keeps every intermediate store small (each spawn <= ~2s, worst-case) while
# still exercising the full add / remove / re-add churn — the remove code path is
# identical at any store size, and full-build correctness is already pinned by
# `test_conformance_graph.py`. Queries range over the capped universe.
_UNIVERSE_CAP = 3


def _graph_queries_for(schema_text, tuples):
    """The shared query grid restricted to the proved query scope: concrete
    objects only (`hqo`); star subjects stay (grid emits them bare, so `hqs`
    holds). Mirrors `test_conformance_graph._graph_queries_for`."""
    subjects, targets = _grid(schema_text, tuples)
    targets = [(rel, ot, on) for (rel, ot, on) in targets if on != "*"]
    return [
        (sp, st, sn, rel, ot, on)
        for (sp, st, sn), (rel, ot, on) in itertools.product(subjects, targets)
    ]


# The gate fails on ANY skip, so filter non-removable corpora (< 2 tuples, e.g.
# `wildcard_public`) out of the parametrization rather than skipping them —
# net-removal needs at least two tuples in the op universe.
#
# `direct_arm_exclusion` is excluded on PROOF-SCOPE grounds (2026-07-20e,
# attack-probed via `#eval` first): the Lean chain's `remove` constructor
# guards its PRE store with PLAIN `StoreValidRules`, under which a stored
# Direct-arm-under-exclusion tuple is inadmissible (`exprDirects = []` on the
# derived def — the `hNoUD` fragment scoping, PROOF_STATUS 2026-07-20d), so
# `removeGateB` REJECTS every remove while such a tuple is in store and
# `graphRunOps` fails closed (rc != 0) on essentially every seeded stream.
# That is the model's honest fail-closed signal, not a divergence: the real
# Python remove path over this corpus IS differentially gated (python-side) by
# `test_conformance_remove.py`, and the add-only Lean gates (graph/state)
# carry the corpus. Lifting this exclusion needs the remove-leg guard widened
# to `StoreValidRulesD` (with the star->concrete `sem` monotonicity lemma the
# `hNoUD` lift requires) — recorded follow-up in HANDOFF.
_REMOVE_EXCLUDED = frozenset({"direct_arm_exclusion"})
_REMOVABLE = sorted(n for n in GRAPH_FRAGMENT
                    if len(SCHEMAS[n][1]) >= 2 and n not in _REMOVE_EXCLUDED)


def _final_store(ops):
    """The accepted final store of a poison-free op stream (the corpus-only
    universe is admission-clean, so every add commits). Erases the FIRST matching
    occurrence per remove — matching the Lean chain's `List.erase` and the Python
    driver's set semantics (the streams never hold a duplicate)."""
    present = []
    for kind, t in ops:
        if kind == "add":
            present.append(t)
        else:
            present.remove(t)
    return present


@pytest.mark.parametrize("name", _REMOVABLE)
def test_leangraph_remove_vs_pythongraph_and_oracle(name):
    """Interleaved add/remove/re-add streams driven through zcli `graphRunOps`:
    Lean graph model == real Python graph index (driven identically) == oracle on
    the accepted final store."""
    schema_text, corpus_tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    universe = list(corpus_tuples)[:_UNIVERSE_CAP]
    queries = _graph_queries_for(schema_text, universe)
    total_removes = 0

    for seed in SEEDS:
        rng = random.Random(seed)
        ops = _sequence(rng, universe)
        n_removes = sum(1 for kind, _ in ops if kind == "remove")
        assert n_removes > 0, f"[{name} seed={seed}] generated stream has no removes"
        total_removes += n_removes

        final = _final_store(ops)
        assert len(final) < len(universe), (
            f"[{name} seed={seed}] stream must net-remove something")

        # Lean operational graph model over the op stream (fails closed on any
        # out-of-scope op — a nonzero rc raises here, which is the honest signal).
        lean_graph = runner.run_spec(build_request(
            schema_text, [], queries, obj_wild, mode="graph", ops=ops))

        # Real Python graph index driven through the IDENTICAL stream.
        session, widx, _proc, _store, accepted = graphindex_drive_ops(
            schema_text, ops, obj_wild)
        try:
            assert sorted(accepted) == sorted(final), (
                f"[{name} seed={seed}] Python driver accepted store diverged from "
                f"the poison-free expectation (a corpus add was rejected?)")
            py_graph = [bool(widx.check(*q)) for q in queries]
        finally:
            session.close()

        mism = [(queries[i], lean_graph[i], py_graph[i])
                for i in range(len(queries)) if lean_graph[i] != py_graph[i]]
        assert not mism, (
            f"[{name} seed={seed}] Lean graph model / Python graph index "
            f"disagreement over a remove stream (ADJUDICATION EVENT — plan §8.2):"
            f"\n{_fmt(mism, 'lean-graph', 'py-graph')}")

        # Independent correctness anchor: the ERASED store's oracle == the Lean
        # verdicts. A driver that dropped removes would answer on the full
        # universe and mismatch here.
        orc = Oracle(schema_text, sorted(final))
        oracle = [orc.check(*q) for q in queries]
        mism = [(queries[i], lean_graph[i], oracle[i])
                for i in range(len(queries)) if lean_graph[i] != oracle[i]]
        assert not mism, (
            f"[{name} seed={seed}] Lean graph model / oracle disagreement on the "
            f"erased store (would CONTRADICT graphRunOps_check_eq_sem + the drain "
            f"gate):\n{_fmt(mism, 'lean-graph', 'oracle')}")

    assert total_removes > 0, f"[{name}] anti-vacuous: no remove ops were exercised"
