# Criteria

LIVING. The definition of correct (FRAMEWORK §3.3). One row per criterion; ids are `AC-n`, never reused
or renumbered. `status` is `planned`, `tested` or `retired`: a criterion moves to `tested` only
when a test claims it and that test has been seen to fail with the behaviour broken.

**How a test claims a criterion.** In a pytest repo, mark the test
`@pytest.mark.criterion("AC-n")` and register the marker in the pytest config
(`markers = ["criterion(id): the AC-n criterion in docs/criteria.md that this test claims"]`).
Elsewhere, put `criterion: AC-n` in a comment on the line above the test. Either way, the trace
check by hand is: every `tested` row has at least one claiming test, and every claimed id has a
row here.

The owner accepted all of these in [DEC-22](decisions/DEC-22-charter-goals-anti-goals-mandates-and.md)
(2026-11-24). AC-6 is the headline, the owner's "tldr"; it is numbered last because the
framework mints no `-0` id. Claiming tests and the sabotage each needs are TK-309.

| Id | Criterion | Story | Status | Claimed by |
|---|---|---|---|---|
| AC-1 | check agrees across the oracle, the set engine and the graph index over the full query grid, under both SetOps (the validation matrix, tests/test_matrix.py). | DEC-22 | planned |  |
| AC-2 | lookup, lookup_reverse and expand agree with brute-force reference lookups built from the oracle's check, on both backends (the lookup-oracle gate, tests/test_lookup_oracle.py). | DEC-22 | planned |  |
| AC-3 | A schema the graph index cannot represent is refused at parse time with a reason, never answered wrongly. | DEC-22 | planned |  |
| AC-4 | A read naming an undeclared type or relation raises, identically on both backends. | DEC-22, DEC-16 | planned |  |
| AC-5 | The PyPI quickstart (PYPI_README.md) runs as published. | DEC-22 | planned |  |
| AC-6 | Headline: there is no way to put the engines into a state where they disagree with each other or fall out of spec with respect to the proof (for example by breaking an invariant); AC-1..AC-5 are its parts. | DEC-22 | planned |  |
