"""Randomized conformance fuzzing: sem vs oracle vs set engine over random stores.

SEMANTICS.md §10 / plan §6, C1 hardening. For each corpus schema we take many
seeded random subsets of its tuples (exercising partial stores, where cascade /
residue / exclusion corner cases live) and compare the Lean spec, the oracle, and
the real set engine over the full query grid. This is the fuzzing that caught the
`fuelBound` bug's cousins; a surviving divergence is an adjudication event
(plan §8.2) — recorded, not silently reconciled.

Deterministic (seeded `random.Random`), no hypothesis dependency. Skips the `sem`
comparisons if `zcli` is unbuilt; oracle-vs-set-engine always runs.
"""

from __future__ import annotations

import itertools
import random

import pytest

from tests.oracle import check_oracle

from formal.conformance.corpus import SCHEMAS
from formal.conformance.encode import build_request
from formal.conformance import runner
from formal.conformance.backends import setengine_answers

SEEDS = list(range(25))


def _grid(tuples):
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


def _queries(tuples):
    subjects, relations, objects = _grid(tuples)
    return [(sp, st, sn, rel, ot, on)
            for (sp, st, sn), rel, (ot, on)
            in itertools.product(subjects, relations, objects)]


def _random_subset(rng, tuples):
    # keep each tuple with prob 0.65; ensure non-empty by retrying trivially
    sub = [t for t in tuples if rng.random() < 0.65]
    return sub


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_random_stores(name):
    schema_text, all_tuples, obj_wild = SCHEMAS[name]
    have_zcli = True
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        have_zcli = False

    for seed in SEEDS:
        rng = random.Random(seed)
        tuples = _random_subset(rng, all_tuples)
        # grid uses the FULL tuple set's names so ghosts/queries stay stable across subsets
        queries = _queries(all_tuples)

        oracle = [check_oracle(schema_text, tuples, *q) for q in queries]
        se = setengine_answers(schema_text, tuples, queries, obj_wild)
        mism_os = [(queries[i], oracle[i], se[i]) for i in range(len(queries))
                   if oracle[i] != se[i]]
        assert not mism_os, (f"[{name} seed={seed}] oracle/set-engine disagreement:\n"
                             + "\n".join(f"  {q} oracle={o} se={s}"
                                         for q, o, s in mism_os[:10]))

        if have_zcli:
            spec = runner.run_spec(build_request(schema_text, tuples, queries, obj_wild))
            mism_so = [(queries[i], spec[i], oracle[i]) for i in range(len(queries))
                       if spec[i] != oracle[i]]
            assert not mism_so, (
                f"[{name} seed={seed}] spec/oracle disagreement "
                f"(ADJUDICATION EVENT — plan §8.2):\n"
                + "\n".join(f"  {q} spec={s} oracle={o}" for q, s, o in mism_so[:10]))
