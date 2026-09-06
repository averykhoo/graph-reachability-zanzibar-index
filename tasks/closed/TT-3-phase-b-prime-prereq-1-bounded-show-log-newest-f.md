---
id: TT-3
title: Phase B-prime prereq 1: bounded show -- Log newest-first above the body, --section, --head
brief: show renders the Log newest-first (Jira order), bounded by SHOW_LOG_HEAD; --section/--head slices; file is append-only
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

Landed 2026-09-06c. task.py: SHOW_LOG_HEAD=5, split_body/section_slug, op_show rewritten (Log newest-first above the body; truncation announced with --head 0 hint; --section summary|log|<slug>, unknown refused naming the list; --json carries log/sections/summary uncut). File byte-unchanged. Evidence: tests/test_tasktool.py::test_show_renders_the_log_newest_first_and_never_touches_the_file, sabotage test_sabotage_bprime_show_can_print_the_log_oldest_first (reversed() dropped -> observed keys ['2026-08-21a', ... 'e'] oldest-first, red). User feedback that drove it: obsolete info at the top of a task because comments append.
