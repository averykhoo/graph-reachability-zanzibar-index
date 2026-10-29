---
id: TK174
title: release 0.1.1 (TK172 lag fix): tag on the user's word, babysit CI, confirm PyPI, install trial
brief: TK172 fix is on master; tag v0.1.1 ONLY on the user's word, then CI babysitter, PyPI-live, install trial
pri: NOW
size: S
deps: []
related: [TK171, TK172]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-10-30
moved: 2026-10-30b
updated: 2026-10-30b
closed:
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-10-30

State: TK172 fixed on master under CHANGELOG `## [Unreleased]`; __version__ still 0.1.0. At the cut: bump src/zanzibar/__init__.py::__version__ to 0.1.1, rename the heading `## [0.1.1] - <date>`, mirror it into userdocs/reference/changelog.md (never under the word "Unreleased", tests/test_userdocs_prerelease_prose.py), full gate, commit, push master, publish dry run green, THEN tag v0.1.1 on the user's word (publish.yml header recipe). Then babysitter through upload, PyPI-live check, install trial + installed_smoke.py. Optional: fold TK173 doc fixes in first.

### 2026-10-30b

TK173 folded in. __version__ 0.1.1, CHANGELOG `## [0.1.1] - 2026-10-30`, userdocs changelog mirrored. Next: full gate, commit, push master, publish dry run green, tag v0.1.1 (user said "push a 0.1.1 fix", 2026-10-30), babysit, PyPI-live, install trial.
