---
id: TT-5
title: Phase B-prime prereq 3: sync --check drift is task.py lint check 13
brief: check_board_sync: no board -> pass; board with no table -> red (retires with sync at cutover); drift -> red + report
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

Landed 2026-09-06c as task.py lint check 13, check_board_sync (APPENDED; checks are citations). No board found -> pass; board without a row table -> red naming the cutover; sync_report drift > 0 -> one violation carrying the rendered report; sync Refused -> violation not traceback; skipped when check 1 failed. Evidence: test_lint_check_13_reports_board_drift_and_a_tableless_board, sabotage test_sabotage_bprime_check_13_can_go_blind (observed: 'a rewritten item block did not redden lint: task lint: clean (13 checks, 7 task file(s) parsed)'). Seven existing tests asserted lint rc 0 on a deliberately drifted board; they now use assert_intact_but_drifted (every violation is check 13's AND the drift is reported).
