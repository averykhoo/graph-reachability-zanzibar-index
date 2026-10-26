---
id: TK167
title: an unappliable backlog row refuses every sync write on the store id with an unhelpful message
brief: after a PathCountExceeded stall every sync add/remove fails, even removing the bad tuple
pri: LATER
size: S
deps: []
related: [TK151]
parent:
labels: []
source: docs/tk151-repros-2026-10-20/README.md
source_hash:
created: 2026-10-20b
moved: 2026-10-26e
updated: 2026-10-26e
closed: 2026-10-26e
---

Working as designed for correctness (rolled-back writes are absent from both backends), but a sync=True instance cannot even remove the offending tuple; the documented recovery is a sync=False removal plus rebuild_index. Agent fix: when a sync write fails on a backlog row that is not the caller s, say so and point at the recovery.

Repro and first-hand output: `docs/tk151-repros-2026-10-20/README.md` section B6 (`docs/tk151-repros-2026-10-20/B6.py`). Found by the TK151 docs pass 2026-10-20b; the user docs describe the CURRENT behaviour as a caveat, so fixing this means updating the pages that section lists.

## Read first

- `docs/tk151-repros-2026-10-20/README.md`

## Log

### 2026-10-26e

Landed: src/zanzibar/store/_store.py::_name_blocking_backlog_row, called in the IndexResourceLimit arm of Store._write; when failing_log_row id != the caller token the same exception (type unchanged) is reworded to name the blocking backlog row and the recovery (PathCountExceeded: sync=False removal + rebuild_index; ClosureFanoutExceeded: catch_up). Own-row refusals unchanged. Tests: tests/test_tk167_backlog_row_named.py 5 passed; related tk111/121/123/158/165 modules 115 passed; userdocs examples + prose + pypi page 53 passed. Sabotage S1 (helper no-op) 3 failed, S2 (guard inverted) 4 failed. Docs: fanout-cap.md, stall-recovery.md, errors.md, reference/exceptions.md, explanation/consistency.md, CHANGELOG [Unreleased] Changed. Body + literal outputs: docs/tk167-backlog-row-message-2026-10-26.md. Not done: recording a stall on the sync path (deliberate). Full gate not run (later stage).

Repair round 1 (review blocking): the own-row guard compared failing_log_row[0] with the returned token, which on a duplicate add is the log head = the poison row, so the bare message came back. LANDED: `_store.py::_name_blocking_backlog_row(exc, own_row_id, store_id)` takes the id of the row this call appended (pending-rows hint in `Store._write`, None on a duplicate add; message then says "a duplicate add, which appends no log row"). New test `test_tk167_backlog_row_named.py::test_sync_duplicate_add_names_the_backlog_row` (unrelated dup + poison dup, asserts poison is the head). Sabotage S4 (pass token again) -> 2 failed, 5 passed; restored cmp-identical, 7 passed. Reviewer S3 recorded. CHANGELOG + userdocs/how-to/fanout-cap.md mention the duplicate-add wording; correction block dated at top of docs/tk167-backlog-row-message-2026-10-26.md. Affected modules: 163 passed. Next: full gate by the commit stage.
