---
id: TK122
title: publish the zanzibar package to PyPI (zanzibar-index, first release 0.0.1)
brief: 0.0.1 tagged, never published (Linux-only test stub bug, fixed); releasing 0.0.2, then the blank-env install test
pri: NEXT
size: M
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-10-07
moved: 2026-10-07b
updated: 2026-10-07b
closed:
---

Publish the library to PyPI as `zanzibar-index` (Alpha; import name `zanzibar`). The
user asked on 2026-10-07 to settle everything except the publishing itself, and that part
LANDED that day: Apache-2.0 `LICENSE`, `zanzibar_*` table namespace without `extend_existing`,
`PYPI_README.md` as the long description (quickstart executed by a test), full metadata,
single-source version, `py.typed`, a trimmed sdist, `CHANGELOG.md`, and CI
(`.github/workflows/gate.yml` = the ten verify.sh phases; `fuzz.yml` = the multi-seed sweep,
on demand), and the tag-only `.github/workflows/publish.yml` (same pattern as the sibling
repos). The user then said (2026-10-07): release **0.0.1** as a pipeline trial, push and
tag it, have an agent install it from PyPI into a blank conda env and try it, fix anything
broken and bump again, and write that install check into CLAUDE.md once it has run.

**Next action:** push master (on the user's word) with a CI-babysitter subagent
(`~/.claude/CLAUDE.md` sec Git), and fix what only Linux CI shows. The tests tiles were
already run under WSL on Linux on 2026-10-07; the `lean` and `conf` jobs were not. Then run
`publish.yml` by `workflow_dispatch` as a dry run. A `v*` tag IS a release and is pushed
only on the user's explicit word (given for `v0.0.1`, 2026-10-07). The publisher was registered by the user
2026-10-07.

## Traps

- (!) **The trusted-publisher registration is keyed on the workflow FILE NAME and the
  environment name.** Fixed 2026-10-07 and given to the user: owner `averykhoo`, repo
  `graph-reachability-zanzibar-index`, workflow `publish.yml`, environment `pypi`
  (test.pypi.org: `testpypi`, unused -- deploys are tag-only to PyPI), project
  `zanzibar-index`. Renaming either one breaks the upload with an OIDC error at release
  time. The siblings use environment `release`; do not "align" this one.
- (!) **Neither workflow has ever run on GitHub.** `actionlint` passed and the tests tiles
  ran green on Linux (WSL, the newest dependency versions), but the `lean` job (elan
  install, `lake exe cache get`, the zcli artifact hand-off, the exec bit) is unverified.
- (!) **CI installs the NEWEST deps; the local gate runs the conda env's** (floors in
  `pyproject.toml` = the conda versions, 2026-10-07). A CI-only red may be a dependency
  upgrade, not a regression.
- (!) **The fuzz sweep runs before a release and on demand, never on a schedule** (user
  decision 2026-10-07). `publish.yml` calls both `gate.yml` and `fuzz.yml` (`workflow_call`).
- (!) **Do not ship a second copy of the version.** `pyproject.toml` reads
  `zanzibar.__version__` (setuptools `dynamic`), and
  `tests/test_tk122_release_metadata.py::test_pyproject_takes_its_version_from_the_package`
  goes red on a static one. A release bumps `__version__` AND `CHANGELOG.md`'s newest heading.

## Read first

- [`docs/pypi-readiness-2026-10-07.md`](../docs/pypi-readiness-2026-10-07.md) -- sec 0 is
  what landed and what is unverified; sec 4 is the publishing mechanics.
- `.github/workflows/publish.yml` (the release), `.github/workflows/gate.yml`,
  `.github/workflows/fuzz.yml`.

## Log

### 2026-10-07

Scouted 2026-10-07 (user: settle PyPI publishing this session). Map: docs/pypi-readiness-2026-10-07.md. RAN: wheel+sdist build, twine check PASSED, clean-venv install + ConnectedStore smoke test correct. BLOCKERS: B1 no licence (user decision); B2 ten generic table names on the global SQLModel.metadata with extend_existing=True -- a user node table defined before import zanzibar.graphindex silently gains our columns (RAN); B3 README has no install/quickstart and 14 relative links. Next action: user picks licence + confirms table-name fix shape; then metadata, README, trusted-publishing workflow, TestPyPI dry run.

Settled everything except publishing (user: Apache-2.0, rename tables, full gate + fuzz-before-release in CI, not nightly; dist name zanzibar-index picked by the model). LANDED: see docs/pypi-readiness-2026-10-07.md sec 0. NEW PINS: tests/test_tk122_table_namespace.py (6, sabotages S1-S3), tests/test_tk122_release_metadata.py (3, sabotages Q1-Q3), MIN_TESTS_ALL 1740 -> 1749. UNVERIFIED: gate.yml / fuzz.yml have never run on GitHub. Trusted-publisher values fixed: publish.yml, environments pypi / testpypi.

User registered the PyPI trusted publisher and asked for tag-only deploys as in the sibling repos. publish.yml written (ngram-movers-distance pattern: validate-tag -> gate.yml + fuzz.yml via workflow_call -> build/twine/wheel smoke = PYPI_README quickstart/attest/upload on tag only; workflow_dispatch = dry run). Environment pypi as registered. All actions SHA-pinned; actionlint clean. CI-babysitter rule added to ~/.claude/CLAUDE.md (user instruction).

### 2026-10-07b

v0.0.1 pushed (master 5d9c92f, tag pushed separately after a first combined push rejected master but accepted the tag; that stray tag was deleted, nothing published). CI first run, babysat by a subagent: lean, tests 1-4, conf 1/3/4/5 and all five fuzz modules GREEN on GitHub; conf (2) RED in both the master gate run and the publish run -- formal/conformance/test_runner_retry.py::test_spawn_oserror_retried_then_succeeds, 1 failed / 217 passed. Cause verified first-hand: only Windows CPython maps OSError 4th arg to .winerror, so on Linux the retry never fired (and the no-retry test passed vacuously). Fixed in the stub; a Linux-modelling control (del e.winerror) reproduces 1 failed / 6 passed. Deploy was skipped, PyPI 404: 0.0.1 is tagged, never published. Bumped to 0.0.2 per user instruction.
