"""C1 answer conformance: Lean spec `sem` vs the oracle vs the real set engine.

SEMANTICS.md §10 / plan §6. The cheap validation that the Lean spec is the RIGHT
spec (Phase 2, before deep proofs). Over a full query grid per schema we compare:
  * the repository oracle (`tests/oracle.check_oracle`),
  * the Lean executable spec (`zcli`), and
  * the real Python set engine (`setengine.SetEngine`).
A disagreement is a spec-adjudication event (plan §8.2): STOP and record it.

`sem` == set engine is direct pre-proof evidence for T1.

Skips the `sem` comparisons cleanly if the Lean `zcli` binary is not built; the
oracle-vs-setengine comparison always runs.
"""

from __future__ import annotations

import itertools

import pytest

from tests.oracle import check_oracle

from formal.conformance.corpus import SCHEMAS
from formal.conformance.encode import build_request
from formal.conformance import runner
from formal.conformance.backends import setengine_answers


def _grid(tuples):
    """Query grid: per type, concrete names in tuples + one ghost + '*' (bare
    subjects), crossed with every (relation, object) in the tuples."""
    names_by_type: dict[str, set[str]] = {}
    relations: set[str] = set()
    objects: set[tuple[str, str]] = set()
    for tup in tuples:
        for ty, nm in ((tup.subject_type, tup.subject_name),
                       (tup.object_type, tup.object_name)):
            names_by_type.setdefault(ty, set())
            if nm != "*":
                names_by_type[ty].add(nm)
        relations.add(tup.relation)
        objects.add((tup.object_type, tup.object_name))
    subjects = []
    for ty in sorted(names_by_type):
        for nm in sorted(names_by_type[ty]) + [f"ghost_{ty}", "*"]:
            subjects.append(("...", ty, nm))
    return subjects, sorted(relations), sorted(objects)


def _queries_for(tuples):
    subjects, relations, objects = _grid(tuples)
    return [
        (sp, st, sn, rel, ot, on)
        for (sp, st, sn), rel, (ot, on) in itertools.product(subjects, relations, objects)
    ]


def _fmt(mismatches, a_name, b_name):
    return "\n".join(
        f"  query={q} {a_name}={a} {b_name}={b}" for q, a, b in mismatches[:20])


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_spec_vs_oracle(name):
    schema_text, tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")

    queries = _queries_for(tuples)
    spec = runner.run_spec(build_request(schema_text, tuples, queries, obj_wild))
    oracle = [check_oracle(schema_text, tuples, *q) for q in queries]

    mism = [(queries[i], spec[i], oracle[i]) for i in range(len(queries))
            if spec[i] != oracle[i]]
    assert not mism, (f"[{name}] spec/oracle disagreement "
                      f"(ADJUDICATION EVENT — plan §8.2):\n{_fmt(mism, 'spec', 'oracle')}")


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_spec_vs_setengine(name):
    schema_text, tuples, obj_wild = SCHEMAS[name]
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built")

    queries = _queries_for(tuples)
    spec = runner.run_spec(build_request(schema_text, tuples, queries, obj_wild))
    se = setengine_answers(schema_text, tuples, queries, obj_wild)

    mism = [(queries[i], spec[i], se[i]) for i in range(len(queries))
            if spec[i] != se[i]]
    assert not mism, (f"[{name}] spec/set-engine disagreement "
                      f"(ADJUDICATION EVENT — plan §8.2):\n{_fmt(mism, 'spec', 'setengine')}")


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_oracle_vs_setengine(name):
    """Independent of the Lean toolchain — always runs."""
    schema_text, tuples, obj_wild = SCHEMAS[name]
    queries = _queries_for(tuples)
    oracle = [check_oracle(schema_text, tuples, *q) for q in queries]
    se = setengine_answers(schema_text, tuples, queries, obj_wild)

    mism = [(queries[i], oracle[i], se[i]) for i in range(len(queries))
            if oracle[i] != se[i]]
    assert not mism, (f"[{name}] oracle/set-engine disagreement:\n"
                      f"{_fmt(mism, 'oracle', 'setengine')}")
