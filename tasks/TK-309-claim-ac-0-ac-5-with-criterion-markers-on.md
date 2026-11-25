---
type: Task
id: TK-309
title: Claim AC-1..AC-6 with criterion markers on existing tests; tested only after a sabotage seen red
brief: No row moves to tested without a recorded sabotage seen red (P7); marker adds no tests
pri: NEXT
state: open
deps: []
source: session 2026-11-24a
created: 2026-11-24
moved: 2026-11-24a
updated: 2026-11-25a
---

Claim the criteria in `docs/criteria.md` (AC-1..AC-6, all `planned`, owner-accepted in DEC-22) with existing tests, and move each row to `tested` only once a claiming test has been seen red with the behaviour broken (FRAMEWORK P7, `docs/sabotage-procedure.md`).

- Register the marker in `pytest.ini`: `criterion(id): the AC-n criterion in docs/criteria.md that this test claims`, and check `--strict-markers` still passes.
- Tag the existing tests that carry each criterion with `@pytest.mark.criterion("AC-n")`. Candidates (UNVERIFIED, to be confirmed at pickup): AC-1 `tests/test_matrix.py`; AC-2 `tests/test_lookup_oracle.py`; AC-3 the parse-refusal tests (`tests/test_p23_parser_refusal_parity.py`, `tests/test_refused_shape_comments.py`); AC-4 the DEC-16 undeclared-name read tests; AC-5 `tests/test_tk122_release_metadata.py`; AC-6 (the headline) the ParityEngine stateful machine in `tests/test_hypothesis.py` plus the invariant checker.
- For each criterion: sabotage the behaviour it guards, watch the claiming test go red, record the literal output in the test's docstring and the commit message, then `context-engine criterion set AC-n --status tested`.
- Then consider setting `[guards] tests = ["tests", "formal/conformance"]` in `context.toml` so lint G-T2 checks the claims (it needs `[working] criteria`, already set).

Done when: every AC-1..AC-6 row is `tested` with a `Claimed by` file, each move backed by a recorded sabotage seen red; the marker is registered; the gate is green; `context-engine lint` is clean.

## Traps
- Adding a marker must not change collected counts (`MIN_TESTS_ALL` / `MIN_CONF_ALL` have zero headroom); a marker adds none, but check with `--collect-only`.
- A hypothesis example database can replay a stored failure and fake a sabotage catch (TK-146): clear it or use a fresh seed for each sabotage.
- AC-6 is the headline; it is claimed by the conjunction of the others plus the invariant checker, so its sabotage must break an invariant (I1-I14), not just one surface.

## Read first
- `docs/criteria.md`
- `docs/sabotage-procedure.md`
- `docs/runbooks/manual-mode.md` § Criteria

## Log

- 2026-11-25a (claude-code/claude-opus-5-5): rerank 2026-11-25a, applying the 2026-11-24b proposal on the owner yes (ASK-13): stays NEXT, #1; do after TK-146 (hypothesis replay would fake its sabotage catches).
