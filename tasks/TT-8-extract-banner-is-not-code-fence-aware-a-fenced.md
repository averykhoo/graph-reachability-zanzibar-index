---
id: TT-8
title: extract_banner is not code-fence-aware: a fenced ## Banner fools board and lint 12 alike
brief: audit finding 2026-09-06d, deferred from the cutover commit; fix + sabotage clause in the check-12 test
pri: LATER
size: S
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-06d
moved: 2026-09-06d
updated: 2026-09-06d
closed:
---

`task.py::extract_banner` finds the `## Banner` section of `HANDOFF.md` by scanning for lines that equal `BANNER_HEADING`, with no awareness of fenced code blocks. A `## Banner` line inside a ``` fence anywhere in the note (a doc example, say) would either be taken as the section or would end the real one early, and `board` and lint check 12 share the extractor so both would agree on the wrong text. Found by the 2026-09-06d cutover audit (adversarial lens), confirmed, deferred because the note is 39 lines and hand-written and the cutover commit had to stay one revertable change.

Fix shape: skip lines between fence markers when scanning for `## ` headings, and refuse (not warn) on a second `## Banner`. Pin it the house way: sabotage a copy of the note with a fenced `## Banner` and watch check 12 go red BEFORE believing the fix (`docs/sabotage-procedure.md`).

## Read first

- `scripts/task.py::extract_banner`, `banner_lines`, `check_banner`
- `tests/test_tasktool.py::test_lint_check_12_catches_the_three_banner_failures` (add the clause there)

## Log
