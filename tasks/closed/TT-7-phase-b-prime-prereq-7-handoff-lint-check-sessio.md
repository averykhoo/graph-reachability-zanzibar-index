---
id: TT-7
title: Phase B-prime prereq 7: handoff_lint check_session_receipt -- both receipt lines in the newest entry
brief: task lint: line and read: <READ_VOCAB> line, normalised for the four shapes C1 found; newest entry only
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

Landed 2026-09-06c. handoff_lint.py::check_session_receipt (APPENDED, 11th check): newest '## <key> ' entry of docs/history/session-log.md must contain a 'task lint: clean (N checks, M task file(s) parsed[, W warning(s)])' or 'task lint: N violation(s)' line and a 'read: <READ_VOCAB>' line (board only | board + HANDOFF | HANDOFF only); backticks/bold/indent stripped, line SEARCHED so the `lint: <receipt>` and `python scripts/task.py lint -> <receipt>` shapes pass. Evidence: tests/test_handoff_lint_b_prime.py -- 24 parametrised green shapes, missing lint line red, missing read line red, paraphrase red, no-entry ledger red, missing ledger red; instrument control: whole-ledger scan instead of newest entry -> observed 'AssertionError: []' (red). READ_VOCAB is a constant so the cutover changes it in one place.
