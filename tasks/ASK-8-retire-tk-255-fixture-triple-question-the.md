---
type: Question
id: ASK-8
title: Retire TK-255 (fixture-triple question; the register test already owns it)?
brief: 'recommend retire: test_subsumption_register_is_current owns it; title stale (6 fixtures, not 5)'
pri: LATER
state: closed
deps: []
source: session 2026-11-20a
created: 2026-11-20
moved: 2026-11-20a
updated: 2026-11-21a
last_asked: 2026-11-21a
status: deprecated
closed: 2026-11-21a
answered: {on: 2026-11-21, session: 2026-11-21a, decision: DEC-21}
---

**Question:** Retire TK-255 (the fixture-TRIPLE question for the subsumed .fga fixtures)?

**Context:** TK-255 (alias P11) asks whether to retire the `.fga` fixtures that another fixture subsumes. `tests/test_schema_shapes.py::KNOWN_SUBSUMED` already registers them, and `tests/test_schema_shapes.py::test_subsumption_register_is_current` keeps the register current; its docstring calls the retirement "a judgement call with no urgency". The row's title is stale: the register now holds 6 names, not 5. It went to SOMEDAY at the 2026-11-20a re-rank.

**Why owner-only:** removing a row from the board is the owner's call (procedures § Rerank step 4).

**Options:**

- A. Retire it: close TK-255; the register test owns the question and makes any new subsumption visible.
- B. Keep it at SOMEDAY (and fix the title to 6).

**Recommendation:** A. The register test already makes the subsumption visible and keeps it current, so the row restates what a test owns, and its title has already rotted once.

**Blocks:** none

## Log

- 2026-11-21a (claude-code/claude-opus-5-5): answered by the owner: DEC-21
