---
id: TK171
title: release 0.1.0: tag on the user's word, babysit CI, confirm PyPI, run the install trial
brief: 0.1.0 prepared on the tree; tag v0.1.0 ONLY on the user's word, then CI babysitter, PyPI-live, install trial
pri: NOW
size: S
deps: []
related: [TK151, TK122]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-10-26e
moved: 2026-10-26e
updated: 2026-10-26e
closed:
---

## What

0.1.0 is prepared on the tree (session 2026-10-26e: `__version__ = "0.1.0"`,
`CHANGELOG.md` `## [0.1.0] - 2026-10-26`, `userdocs/reference/changelog.md` re-dated,
pre-release prose removed; TK151 closed). What remains needs the user's explicit word:

1. The user says to tag. Push the release commit, then the `v0.1.0` tag
   (`.github/workflows/publish.yml` header is the recipe; a tag is a RELEASE).
2. CI babysitter subagent on the pushed SHA and the tag (`~/.claude/CLAUDE.md` § Git),
   through the PyPI upload step.
3. Confirm `https://pypi.org/pypi/zanzibar-index/0.1.0/json` returns 200.
4. Fresh-user install trial subagent on the published artifact, plus
   `scripts/installed_smoke.py` against the wheel; transcribe the trial into a tracked doc
   the same hour; file a row per BROKEN finding (fixed in 0.1.1).

TRAP: the next `[Unreleased]` CHANGELOG section must not be mirrored into
`userdocs/reference/changelog.md` under that word
(`tests/test_userdocs_prerelease_prose.py`); title it "Next release".

## Log
