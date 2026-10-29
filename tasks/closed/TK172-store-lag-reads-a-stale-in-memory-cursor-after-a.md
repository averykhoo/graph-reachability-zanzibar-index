---
id: TK172
title: Store.lag() reads a stale in-memory cursor after another instance's catch_up (0.1.0 trial F18)
brief: 0.1.0 trial F18: lag() counts against the ORM-cached cursor; over-reports after another process's catch_up
pri: NEXT
size: S
deps: []
related: [TK171]
parent:
labels: []
source: hand
source_hash:
created: 2026-10-30
moved: 2026-10-30
updated: 2026-10-30
closed: 2026-10-30
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-10-30

FIXED on master 2026-10-30 (unreleased; ships in 0.1.1, TK174). Repro first-hand against src/ at 556011e: writer lag() 1 -> other process catch_up() 1 -> writer lag() still 1 (check() already True); fresh instance 0; after refresh() 0. Cause: src/zanzibar/store/_store.py::Store.lag compared against the ORM-cached self.cursor.applied_log_id. Fix: count against the committed cursor row (scalar subquery on IndexCursor.applied_log_id by self.cursor.id); docstring says so. Pin: tests/test_tk172_lag_reads_committed_cursor.py, red before the fix (assert 1 == 0 on watcher.lag()), green after. PostgreSQL leg (ZANZIBAR_PG_REQUIRED=1): postgres_ha + concurrency + async + tk111/121/165 + tk172 -> 51 passed, 2 skipped (the documented SQLite-only pair); the F18 scenario on PG: before 1, catch_up 1, after 0. CHANGELOG [Unreleased] entry added. Trial doc: docs/pypi-trial-0.1.0-2026-10-30.md F18.
