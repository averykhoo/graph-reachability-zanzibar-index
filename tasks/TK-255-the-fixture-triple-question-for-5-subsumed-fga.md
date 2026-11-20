---
type: Task
id: TK-255
aliases: [P11]
title: the fixture-TRIPLE question for 5 subsumed .fga fixtures
brief:
pri: SOMEDAY
state: open
size: S
deps: []
related: []
parent:
labels: [infra]
source: board
source_hash: 0de79c8fa25a
created: 2026-08-16
taskpy_moved: '2026-08-16'
taskpy_updated: '2026-08-16'
moved: 2026-11-20a
updated: 2026-11-20a
---

the fixture-TRIPLE question for 5 subsumed `.fga` fixtures

## Traps

None recorded. This row sits below `NEXT`, so it never had an item block; traps for it, if any, live at the pointer below.

## Read first

- `tests/test_schema_shapes.py::KNOWN_SUBSUMED`

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.
- 2026-11-20a (claude-code/claude-opus-5-5): rerank 2026-11-20a: LATER -> SOMEDAY. No urgency: the register test already owns the question (tests/test_schema_shapes.py::test_subsumption_register_is_current docstring: a judgement call with no urgency). Title stale: KNOWN_SUBSUMED now holds 6 names, not 5. Its retirement is put to the owner as a question.
