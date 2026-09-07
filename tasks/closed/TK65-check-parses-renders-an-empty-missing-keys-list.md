---
id: TK65
title: check_parses renders an empty missing-keys list as a bare dash
brief:
pri: SOMEDAY
size: S
deps: []
related: [TT-1]
parent:
labels: [infra]
source: docs/history/tasktool-scratch-archive-2026-09-07.md
source_hash:
created: 2026-09-07
moved: 2026-09-07b
updated: 2026-09-07b
closed: 2026-09-07b
---

`notes.md` "Still open" item 2. Two lint messages shared one cosmetic defect: an empty list
rendered as a bare `-`, so a failure read `missing keys -, unknown keys ['status']`, where
the dash is the ABSENCE of missing keys and looks like a value.

`check_pri_budget`'s half was fixed. `check_parses`'s was not: verified 2026-09-07,
`scripts/task.py:1110-1112` still renders `missing or '-'`. The live renderer elsewhere uses
`(none)`, which is the wording to match.

Cosmetic, and filed only because its twin was fixed and the record of the pair existed
solely in the deleted directory -- an unmatched half is the kind of thing that gets
rediscovered as a "new" defect two years later.

## Traps

- `(none)` is the established wording (`scripts/task.py:1946`, `:1978`, `:2273-2278`).
  Do not invent a third rendering.

## Read first

- [`docs/history/tasktool-scratch-archive-2026-09-07.md`](../docs/history/tasktool-scratch-archive-2026-09-07.md) section 5 item 8

## Log

### 2026-09-07b

LANDED. task.py check_parses renders an empty list as `(none)`, matching the established
wording at :1946/:1978/:2273-2278 rather than inventing a third spelling. The live line was
:1120, not the :1110-1112 this row cited -- a drifted line citation, which is itself the
argument for the path-only rule now recorded on TK59.

Pinned by extending the EXISTING sabotage test rather than adding a new one:
tests/test_tasktool.py::test_sabotage_check_parses already produces this exact message, so
it now asserts `unknown keys (none)` and refuses `unknown keys -`. Its docstring carries the
pre-fix observed line, which is where the bare dash is visible in the record.

Both halves of the 2026-08-21 pair are now closed.
