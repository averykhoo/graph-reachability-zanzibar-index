---
id: TK178
title: release 0.1.2 (TK176 sync= / ops= checks): tag on the user word, babysit, PyPI, install trial
brief: TK176 fix (sync= truthiness) is on master under [Unreleased]; tag v0.1.2 ONLY on the user word, then babysit + trial
pri: NOW
size: S
deps: [TK177, TK179, TK180, TK181, TK182]
related: [TK176, TK174]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-10-30b
moved: 2026-10-30b
updated: 2026-10-30b
closed:
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-10-30b

At the cut: __version__ 0.1.2, rename CHANGELOG `## [Unreleased]` to `## [0.1.2] - <date>`, mirror into userdocs/reference/changelog.md (never under the word Unreleased), full gate, commit, push, publish dry run green, THEN tag v0.1.2 on the user word (publish.yml header recipe); babysit through upload, PyPI-live, install trial + installed_smoke.py. The user word given 2026-10-30 covered 0.1.1 only.

User 2026-10-30b: improve testing before 0.1.2. Release blocked on TK177, TK179, TK180, TK181 (deps); TK176 (sync=/ops= fix) is already closed on master. Plan: docs/tk179-strict-public-args-plan-2026-10-30.md.

All deps closed (TK177, TK179, TK180, TK181, TK182) on 2026-10-30b; 0.1.2 content is under CHANGELOG [Unreleased]. Next: full gate + fuzz, commit, push, publish dry run, then ASK the user for the v0.1.2 tag.
