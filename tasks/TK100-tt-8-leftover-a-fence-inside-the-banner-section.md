---
id: TK100
title: TT-8 leftover: a fence inside the banner section is unpinned behaviour
brief: observed in TT-8, never pinned; extract_banner is SHARED by check_banner and op_board
pri: LATER
size: S
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-22
moved: 2026-09-22
updated: 2026-09-22
closed:
---

`TT-8` left one behaviour OBSERVED but UNPINNED: a fence (a fenced code block) placed
*inside* the `## Banner` section now counts as banner content, so such a corpus fails the
line cap rather than truncating.

This came out of the `TT-8` work on `task.py::extract_banner` (2026-09-10), whose sabotage
record is the reason the fence handling exists at all: a fenced `## Banner` is a code line,
so a note whose only `## Banner` is a worked EXAMPLE now fails `check_banner` instead of
linting clean while `board` printed the example. That fix is landed and pinned. What is NOT
pinned is the adjacent behaviour above -- it was observed during the same session and never
got a test.

An unpinned observed behaviour is one refactor away from silently changing, and
`extract_banner` is SHARED by `task.py::check_banner` and `task.py::op_board` -- which is
exactly what made the original `TT-8` defect dangerous: both consumers agreed on the wrong
text.

Carried in `HANDOFF.md`'s `## Still owed` until the 2026-09-22 disposition filed it here.

## Traps

- (!) **`TT-8`'s own lesson applies to its leftovers**: 7 of 12 weakenings left everything
  green because the clause guarded one fence SHAPE, not the fence GRAMMAR. Pin the grammar,
  and sweep the module with mutations -- one sabotage certifies one test
  (`docs/sabotage-procedure.md`).
- (!) **Decide whether failing the cap is the RIGHT behaviour before pinning it.** A pin
  freezes whatever is there; if truncating is actually correct, this row is a bug fix, not a
  test-addition. Say which on the row before writing the test.

## Read first

- `scripts/task.py::extract_banner` -- the function, its docstring, and the literal sabotage
  output recorded there.
- `scripts/task.py::check_banner` -- check 12, the consumer that shares `extract_banner`
  with `op_board`, and its "FENCES AND SECOND BANNERS (`TT-8`, 2026-09-10)" paragraph.
- [`../docs/sabotage-procedure.md`](../docs/sabotage-procedure.md) sec "Sweep the TEST
  MODULE with mutations" -- `TT-8` is one of the named cases.

## Log
