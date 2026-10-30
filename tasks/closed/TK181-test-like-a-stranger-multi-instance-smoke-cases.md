---
id: TK181
title: test like a stranger: multi-instance smoke cases, docs pages run twice and in pairs in one folder
brief: smoke + tests: two Store instances / two processes on one store; docs pages run twice and in pairs in one folder
pri: NEXT
size: S
deps: []
related: [TK172, TK176, TK178]
parent:
labels: []
source: hand
source_hash:
created: 2026-10-30b
moved: 2026-10-30b
updated: 2026-10-30b
closed: 2026-10-30b
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-10-30b

Why: TK172 (lag stale across instances) needed two Store instances; the 0.1.0 trial F22 and 0.1.1 trial F5 were docs pages run in the same folder or twice; tests/test_userdocs_examples.py runs each page once in a fresh tmp dir. Next action: add two-instance and two-process cases to scripts/installed_smoke.py (lag, check after another instance catch_up, concurrent writes); make the docs runner run every page twice in one dir and compare output, and run all pages in one shared dir.

Map: docs/tk180-tk181-stranger-tests-2026-10-30.md. scripts/installed_smoke.py section 5: two Store instances and a second OS process on one SQLite file (TK172 lag without refresh), TK175 self-parent sync+async, TK176 sync=None / ops=str refusals; 102 checks on the checkout (was 67), +~2 s; sabotage by monkeypatch red for TK172 (3 failed), TK175 (2), TK176 (1). tests/test_userdocs_examples.py: pages that leave a file run twice in the same dir (stdout must match) + all file-touching pages in ONE shared dir + a self-test of the checks; +~28 s. Its first run caught the session TK179 regression of the documented None read predicate.
