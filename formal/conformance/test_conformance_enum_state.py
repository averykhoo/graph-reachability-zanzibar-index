"""Phase 6 extra — STATE-level gate over the ENUMERATED stores (widening
§4(e) increment (d), 2026-07-18).

`test_conformance_enum.py` drives the exhaustive small-scope enumeration at
ANSWER level (spec `sem` × oracle × set engine × real graph index `check`, per
store). This module is the STATE-level analog of that enumeration, and the
enumeration analog of the curated-corpus `test_conformance_state.py`: for a
DETERMINISTIC SAMPLE of the enumerated stores it compares the Lean operational
graph model's canonical final materialized state (zcli mode `"graph-state"` —
the `graphRun` fold of the `ReachedBy` chain's own constructors) against the
real Python graph index's extracted `EdgeV4`/`ResidueV1` state, under the SAME
documented projections P1–P6 as `test_conformance_state.py`.

It reuses `extractor.py`'s `lean_graph_state` / `python_graph_state` /
`diff_states` UNCHANGED — same canonical form, same P1–P6, same
symmetric-difference diff. Nothing here re-implements or widens a projection.

Why this exists (house rule 2 — attack first): a state-level comparison over
ENUMERATED stores exercises write-order / partial-store interleavings the 18
curated `GRAPH_FRAGMENT` corpora never reach — and state-level enumeration is
EXACTLY the class of run that originally FOUND the P6 leaf-family divergence
(`CORRESPONDENCE.md` §7) and the 2026-07-17 stale-fanout state divergence. The
answer-level enum leg (increment (a)) cannot see representation drift that keeps
every check verdict equal (P6 was invisible to the verdict gate); this leg can.
A sampled store whose Lean-model state ≠ extracted Python state under P1–P6,
outside those documented projection classes, is an ADJUDICATION EVENT to record
(plan §8.2) — never a golden/oracle/projection to edit.

--------------------------------------------------------------------------- #
SHAPE COVERAGE — all six enum shapes get the state gate; none excluded.
--------------------------------------------------------------------------- #
The six enum shapes (`test_conformance_enum._SHAPES`) are all inside
`GRAPH_FRAGMENT`, so the state extractor + zcli `"graph-state"` mode support
every one (the curated `test_conformance_state.py` runs the exact same
machinery over all of `GRAPH_FRAGMENT`, `two_stratum_cascade`'s 2-stratum
derived state and the star/residue state of the wildcard/TTU shapes included).
Probed 2026-07-18 over the full stride-4 sample below: ZERO Lean
admission/drain errors (rc 2/3) on any sampled store, so the graph-state mode
admits and drains every one — no shape is unsupported, and there is no
documented shape-exclusion for this leg.

--------------------------------------------------------------------------- #
SAMPLING — deterministic, documented; NO silent caps.
--------------------------------------------------------------------------- #
One state comparison per store is expensive: a fresh `zcli` process
(`"graph-state"`, ~120 MB static binary) PLUS a full SQL graph-index build +
cascade + row extraction. Measured on the reference machine at ~150–205
ms/store (avg ~180 ms). Exhaustive state over all 1021 enumerated stores would
add ~3 min — far past the conf-rest command-cap budget (already ~7:49 after
increments (a)+(b)). So this leg SAMPLES.

Sampling method: for each shape, take the size-ordered enumerated store list
(`test_conformance_enum._all_stores`, sizes 0,1,…,K in deterministic
`itertools.combinations` order) and keep every `_STATE_STRIDE`-th store
(`stores[::_STATE_STRIDE]`, `_STATE_STRIDE = 4`). Because the list is ordered
by store SIZE, a fixed stride spreads the sample across the whole 0..K size
spectrum (the empty store is always included at index 0). The resulting
per-shape sample size is ASSERTED below (`_STATE_SAMPLE`) so the sampled
fraction cannot silently drift, exactly as the enum asserts its store counts.

What is state-checked vs answer-only (the honest fraction):

    shape                    stores(K)  state-sampled  answer-checked
    boolean_exclusion         163 (4)        41            all 163
    boolean_intersection      163 (4)        41            all 163
    boolean_star_exclusion     57 (4)        15            all  57
    ttu                       163 (4)        41            all 163
    two_stratum_cascade       299 (3)        75            all 299
    wildcard_group_member     176 (3)        44            all 176
    ------------------------------------------------------------------
    total                    1021           257            all 1021

So 257 of the 1021 enumerated stores (~25%) are compared at STATE level here;
the remaining ~75% are compared at ANSWER level by `test_conformance_enum`
(increment (a): the real graph index `check` == `sem` == oracle == set engine).
The two legs together: every enumerated store is answer-pinned, and a
deterministic ~1-in-4 spread across every store size is additionally
state-pinned.

Cost: 257 stores × ~180 ms ≈ ~47 s added to the conf-rest phase (measured
2026-07-18: boolean_exclusion 7.9 s, boolean_intersection 7.8 s,
boolean_star_exclusion 2.7 s, ttu 6.9 s, two_stratum_cascade 14.6 s,
wildcard_group_member 6.7 s). conf-rest ~7:49 → ~8:36, under the ~9:15 target
(≥45 s below the 10-min command cap). This is the sanctioned lever: sample a
documented deterministic fraction, keep the leg MODEST, leave the exhaustive
part at answer level.

Skips cleanly ONLY if the Lean binary is not built (`verify.sh` preflights the
binary, so under the gate this leg runs with 0 skips — the sampling is a
parametrize-list stride, not a runtime skip).
"""

from __future__ import annotations

import pytest

from formal.conformance import runner
from formal.conformance.corpus import SCHEMAS
from formal.conformance.extractor import (
    diff_states,
    lean_graph_state,
    python_graph_state,
)
from formal.conformance.test_conformance_enum import (
    _SHAPES,
    _all_stores,
    _tuple_space,
)

# Deterministic sampling stride over the size-ordered store list (see the module
# docstring). Chosen so the whole leg adds only ~47 s to conf-rest.
_STATE_STRIDE = 4

# Expected per-shape state-sample size at `_STATE_STRIDE` — ASSERTED so the
# sampled fraction cannot silently drift from the code (mirrors the enum's
# store-count assertions). len(range(0, N, 4)) == ceil(N/4).
_STATE_SAMPLE: dict[str, int] = {
    "boolean_exclusion": 41,        # of 163
    "boolean_intersection": 41,     # of 163
    "boolean_star_exclusion": 15,   # of 57
    "ttu": 41,                       # of 163
    "two_stratum_cascade": 75,      # of 299
    "wildcard_group_member": 44,    # of 176
}


@pytest.mark.parametrize("name", sorted(_SHAPES))
def test_enum_state_leangraph_vs_pythongraph(name):
    """Final materialized STATE, Lean graph model == Python graph index, over a
    deterministic stride-4 SAMPLE of the enumerated stores, under the documented
    P1–P6 projections (extractor.py)."""
    schema_text, _corpus_tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    space = _tuple_space(schema_text)
    exp_space, k, exp_stores = _SHAPES[name]
    assert len(space) == exp_space, (
        f"[{name}] declared tuple space drifted: {len(space)} tuples "
        f"(documented bound says {exp_space}) — the enum bound and this leg's "
        f"sample must stay in lock-step; update deliberately, never silently")

    stores = list(_all_stores(space, k))
    assert len(stores) == exp_stores, (
        f"[{name}] enumerated {len(stores)} stores but the documented bound "
        f"says {exp_stores} — the enumeration or the docstring drifted")

    sample = stores[::_STATE_STRIDE]
    exp_sample = _STATE_SAMPLE[name]
    assert len(sample) == exp_sample, (
        f"[{name}] stride-{_STATE_STRIDE} state sample is {len(sample)} stores "
        f"but the documented sample size is {exp_sample} — the sampled "
        f"fraction drifted; update `_STATE_SAMPLE` + the docstring deliberately")

    for i, store in enumerate(sample):
        store = list(store)
        lean = lean_graph_state(schema_text, store, obj_wild)
        py = python_graph_state(schema_text, store, obj_wild)
        diff = diff_states(lean, py)
        assert diff is None, (
            f"[{name}] Lean graph model / Python graph index STATE "
            f"disagreement (ADJUDICATION EVENT — plan §8.2; symmetric "
            f"difference) at sampled enumerated store #{i} = {store}:\n{diff}")
