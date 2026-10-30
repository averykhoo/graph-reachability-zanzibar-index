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
moved: 2026-10-30c
updated: 2026-10-30c
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

### 2026-10-30c

Cut prepared (user 2026-10-30c: "do all that" = bump, gate, commit, push, CI gate + 6-seed fuzz + publish dry run; NOT the tag). __version__ 0.1.2; CHANGELOG `## [0.1.2] - 2026-10-30` with an intro line; userdocs/reference/changelog.md 0.1.2 entry. Next: once CI is green on the pushed commit, ASK the user for the v0.1.2 tag; then babysit through upload, PyPI JSON 200, install trial + installed_smoke.py.

CI RED on 540bb50: gate lean 4h mypy (processor.py:1263, Residue object_node_id int|None) under CI deps sqlmodel 0.0.48 / SQLAlchemy 2.1.6 / pydantic 2.14.2; locally green with 0.0.39 / 2.0.51 / 2.13.4. Publish dry run red for the same reason; fuzz (6 seeds) and docs green. Reproduced in a venv with the CI versions, fixed with persisted_id(node) (a cast, no runtime change), mypy clean under both dep sets, anchor pin regenerated for DeltaProcessor._store_residue after re-reading its 4 CORRESPONDENCE rows. Drift gap filed as TK183. Next: full gate, commit, push, re-run publish dry run (+ gate on push), then ASK for the tag.
