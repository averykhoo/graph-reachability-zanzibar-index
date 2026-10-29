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
moved: 2026-10-30
updated: 2026-10-30
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

### 2026-10-30

User gave the word to tag (2026-10-30). Pre-tag run, in order:

- Pushed master 984f00b. CI on that SHA (babysitter, `.scratch/ci-watch/984f00b.md`): gate 40913621849 SUCCESS, docs 40913622084 SUCCESS, fuzz 40913639601 SUCCESS (6 seeds), **publish dry run 40913645340 FAILURE** at "Smoke-test the built wheel in a clean venv": `AssertionError: 0`.
- Root cause (first-hand READ): the smoke step in `.github/workflows/publish.yml` kept its own copy of the quickstart regex; TK123 item 22 retargeted `tests/test_tk122_release_metadata.py::_EXPECT` to `print(store.check(...))  # True` and missed the workflow copy, so it matched 0 lines. Had we tagged 984f00b, validate/gate/fuzz would pass and the release would die before upload, burning the v0.1.0 tag.
- Fix: the workflow regex now matches the print form. New pin `tests/test_tk122_release_metadata.py::test_the_publish_smoke_step_runs_on_the_current_readme` extracts the step's heredoc and runs it against PYPI_README.md. Sabotage: regex reverted -> `1 failed, 3 passed`, `AssertionError: 0` (same as CI); restored -> `4 passed`.
- Also pre-flight: local wheel of 0.1.0 in a fresh venv, `scripts/installed_smoke.py --version 0.1.0` -> `68 checks passed, 0 failed, 13.8s`.
- CHANGELOG.md and userdocs/reference/changelog.md re-dated to 2026-10-30.

Next: full gate on this tree, commit, push master, re-run the publish dry run (must be green), then tag v0.1.0.
