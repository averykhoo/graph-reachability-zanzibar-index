---
id: TT-6
title: Phase B-prime prereq 6: ack adopts a source: hand task that has a board row
brief: hand -> board flip + digest + Log line, one direction, observed fact only; hand-without-row and path sources refused
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

Landed 2026-09-06c. op_ack fifth case: source: hand with a board row -> source flips to board, digest stamped, Log entry carries '(ack adopted this task: source hand -> board ...)'; moved held. hand-without-row and path sources still refused (existing test unchanged). Evidence: test_ack_adopts_a_hand_task_that_has_a_row (sync --check BODY T5 -> ack rc 0 -> sync CLEAN, lint clean; path-source T8 with a row -> rc 2), sabotage test_sabotage_bprime_ack_adoption_can_skip_the_flip (observed: 'ack accepted T5 but did not adopt it (rc=2): task ack: REFUSED'). Docs: tasktool-spec.md ack row; test_source_is_written_once_and_never_again docstring notes the one exception.
