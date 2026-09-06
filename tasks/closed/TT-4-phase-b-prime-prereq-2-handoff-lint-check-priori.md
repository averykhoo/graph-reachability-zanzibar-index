---
id: TT-4
title: Phase B-prime prereq 2: handoff_lint check_priority_capacities falls back to the task tree
brief: when HANDOFF.md has no row table, NOW==1 / NEXT<=3 come from tasks/*.md pri: fields; board wins while it has rows
pri: LATER
size: S
deps: []
related: [TT-1]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-06c
moved: 2026-09-06c
updated: 2026-09-06c
closed: 2026-09-06c
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-09-06c

Landed 2026-09-06c. handoff_lint.py::_tree_open_pris + check_priority_capacities: board rows while the table exists (unchanged); when the board has no pri rows, NOW==1 / NEXT<=3 are read from open tasks/*.md pri: fields (BANNER/README excluded), with a tree-naming message; None tree and empty harvest are still violations. Evidence: tests/test_handoff_lint_b_prime.py (stub board + two NOW files -> 'found 2 NOW open task files', red; four NEXT -> red; empty tree -> red; board with table + two NOW files -> green, task.py check 5 owns that). Instrument control: 'if not tree' -> 'if tree is None' stayed red but for the wrong reason (0 NOW), so the test asserts the message text.
