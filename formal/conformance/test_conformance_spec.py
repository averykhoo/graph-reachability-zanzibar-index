"""C1 answer conformance: Lean spec `sem` vs the oracle vs the real set engine.

SEMANTICS.md §10 / plan §6. The cheap validation that the Lean spec is the RIGHT
spec (Phase 2, before deep proofs). Over a full query grid per schema we compare:
  * the repository oracle (`tests/oracle.Oracle`, one instance per store),
  * the Lean executable spec (`zcli`), and
  * the real Python set engine (`setengine.SetEngine`).
A disagreement is a spec-adjudication event (plan §8.2): STOP and record it.

`sem` == set engine is direct pre-proof evidence for T1.

Skips the `sem` comparisons cleanly if the Lean `zcli` binary is not built; the
oracle-vs-setengine comparison always runs.
"""

from __future__ import annotations

import pytest

from tests.oracle import Oracle

from formal.conformance.corpus import (
    SCHEMAS, TTU_USERSET_SCHEMAS, SELF_REFERENTIAL_SCHEMAS)
from formal.conformance.encode import build_request
from formal.conformance.grid import queries_for, fmt_mismatches as _fmt
from formal.conformance import runner
from formal.conformance.backends import setengine_answers


# The spec comparisons (spec `sem` / oracle / set engine) are FULL-SCOPE — T1
# places no fragment restriction on the set engine, and `sem`/oracle are the
# reference for every stratifiable schema — so they additionally carry the TTU
# userset-subject corpora (the 2026-07-13 X4 shapes) and the self-referential-tuple
# corpora (the 2026-07-13 self-referential fix; both docs/spec-deviations.md /
# FINAL_REVIEW §3). Those are kept OUT of the base SCHEMAS so the graph-side
# suites (graph / state / remove) don't carry out-of-W4Fragment shapes.
_SPEC_SCHEMAS = {**SCHEMAS, **TTU_USERSET_SCHEMAS, **SELF_REFERENTIAL_SCHEMAS}


def _oracle_answers(schema_text, tuples, queries):
    """One Oracle per store (parse the schema once), pointwise checks."""
    orc = Oracle(schema_text, tuples)
    return [orc.check(*q) for q in queries]


@pytest.mark.parametrize("name", sorted(_SPEC_SCHEMAS))
def test_spec_vs_oracle(name):
    schema_text, tuples, obj_wild = _SPEC_SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    queries = queries_for(schema_text, tuples)
    spec = runner.run_spec(build_request(schema_text, tuples, queries, obj_wild))
    oracle = _oracle_answers(schema_text, tuples, queries)

    mism = [(queries[i], spec[i], oracle[i]) for i in range(len(queries))
            if spec[i] != oracle[i]]
    assert not mism, (f"[{name}] spec/oracle disagreement "
                      f"(ADJUDICATION EVENT — plan §8.2):\n{_fmt(mism, 'spec', 'oracle')}")


@pytest.mark.parametrize("name", sorted(_SPEC_SCHEMAS))
def test_spec_vs_setengine(name):
    schema_text, tuples, obj_wild = _SPEC_SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built")

    queries = queries_for(schema_text, tuples)
    spec = runner.run_spec(build_request(schema_text, tuples, queries, obj_wild))
    se = setengine_answers(schema_text, tuples, queries, obj_wild)

    mism = [(queries[i], spec[i], se[i]) for i in range(len(queries))
            if spec[i] != se[i]]
    assert not mism, (f"[{name}] spec/set-engine disagreement "
                      f"(ADJUDICATION EVENT — plan §8.2):\n{_fmt(mism, 'spec', 'setengine')}")


@pytest.mark.parametrize("name", sorted(_SPEC_SCHEMAS))
def test_oracle_vs_setengine(name):
    """Independent of the Lean toolchain — always runs."""
    schema_text, tuples, obj_wild = _SPEC_SCHEMAS[name]
    queries = queries_for(schema_text, tuples)
    oracle = _oracle_answers(schema_text, tuples, queries)
    se = setengine_answers(schema_text, tuples, queries, obj_wild)

    mism = [(queries[i], oracle[i], se[i]) for i in range(len(queries))
            if oracle[i] != se[i]]
    assert not mism, (f"[{name}] oracle/set-engine disagreement:\n"
                      f"{_fmt(mism, 'oracle', 'setengine')}")
