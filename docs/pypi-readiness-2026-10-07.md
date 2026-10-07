# PyPI release readiness -- 2026-10-07

> **ACTIVE-PLAN** (`docs/README.md` sec 3). Scouting for the PyPI-publishing row, done
> 2026-10-07 at the user's request ("how ready is this library for a release?").
> Corrections go at the top, dated. FROZEN when the row closes.
> Provenance labels: **READ** = first-hand read of the tree; **RAN** = first-hand executed
> this session; **REASONED** = inference, not executed. No subagents were used.
> Probe artifacts lived in the gitignored `.scratch/pypi-readiness/`; everything that
> matters from them is transcribed here.

## 0. Progress, 2026-10-07 (same session, after the user's answers) -- newest first

**2026-10-07b, first GitHub CI run (via the `v0.0.1` tag):** RAN on GitHub, babysat by a
subagent. GREEN: Lean (elan, `lake exe cache get`, `verify.sh lean`, zcli artifact), `tests`
1-4, `conf` 1/3/4/5, and the fuzz sweep (5 modules). RED: `conf (2)`, with one test,
`formal/conformance/test_runner_retry.py::test_spawn_oserror_retried_then_succeeds`. The cause
is in the test stub, not the library: `.winerror` is set from `OSError`'s fourth argument on
Windows only. The stub was fixed and a control reproduced the CI failure. Deploy was skipped,
so 0.0.1 was never published, and **0.0.2** is the release. The sec 4 assumption that the Lean
job was the risky one turned out wrong: it worked on its first run.

**Release decision (user, 2026-10-07):** the first release is **0.0.1**, not 0.1.0, "since
we're testing for now". Push it, tag it, then have an agent install it from PyPI into a blank
conda env and try it out. Anything broken is fixed and bumped (0.0.2), and the install check
goes into CLAUDE.md once the trial has run. `__version__` and `CHANGELOG.md` say 0.0.1. The
0.1.0 figures below are what was measured before the bump.

**Later the same session, the repo side of publishing:** the user registered the trusted
publisher ("okay done for pypi") and asked for **deploys only on tags, as in the sibling
repos** (`ngram-movers-distance/.github/workflows/publish-to-pypi.yml`,
`python-peass/.github/workflows/release.yml`, both READ). `.github/workflows/publish.yml`
mirrors ngram's: `validate-tag` (tag on master, tag == `__version__`, version not already on
PyPI), then `gate.yml` + `fuzz.yml` via `workflow_call`, then one `deploy` job (build,
`twine check --strict`, a clean-venv wheel smoke that runs the `PYPI_README.md`
quickstart, build-provenance attestation, then upload only when the ref is a tag). On
`workflow_dispatch` it is a dry run. Environment `pypi`, as registered. The siblings use
`release`, but this repo must match what was registered. **TestPyPI is not used by any
workflow**: deploys are tag-only, so the `testpypi` publisher registration is harmless and
inert. Every action in all three workflows is SHA-pinned (ngram's pins for checkout /
setup-python / attest / pypi-publish; `cache` v6.1.0, `upload-artifact` v7.0.1 and
`download-artifact` v8.0.1 resolved via `git ls-remote`, 2026-10-07). RAN on all three:
`actionlint` clean. The version-guard and smoke-test scripts were run locally: the guard
accepted `v0.1.0`, rejected `v0.1.1`, and PyPI returned 404 for 0.1.0; the smoke passed
against the installed wheel. The user's standing rule that **every push gets a CI-babysitter
subagent** is in `~/.claude/CLAUDE.md` sec "Git: gate, commit, push" (machine-wide), with
a pointer in this repo's `CLAUDE.md`.

**User decisions (2026-10-07, in chat):** licence **Apache-2.0**; table rename **approved**;
"settle everything EXCEPT publishing"; CI should run the **full gate**, and the fuzz sweep
runs **before a release, not nightly** ("nobody's gonna look at it"); the user did not
want to claim the bare `zanzibar` PyPI name. Distribution name **`zanzibar-index`** was the
model's pick from the user's two suggestions (import name stays `zanzibar`). It is one line
in `pyproject.toml` to change before the first upload.

**Trusted-publisher values, FIXED so the user can register the pending publisher now:**
owner `averykhoo`, repo `graph-reachability-zanzibar-index`, workflow **`publish.yml`**,
environment **`pypi`** (pypi.org) / **`testpypi`** (test.pypi.org), project `zanzibar-index`.
`publish.yml` itself is NOT written (publishing deferred); when it is, it should
`workflow_call` `gate.yml` and `fuzz.yml` and then build + upload.

**What landed (each RAN unless marked):**
- B1: `LICENSE` is the canonical Apache-2.0 text (fetched from apache.org; md5
  `3b83ef96387f14655fc854ddc3c6bd57`). PEP 639 `license` / `license-files` in
  `pyproject.toml`, so `setuptools>=77`.
- B2: all ten tables, the five explicit constraint names and the four explicit index names
  carry `zanzibar_`; `extend_existing` is gone. Pinned by
  `tests/test_tk122_table_namespace.py` with three sabotages in its docstring.
  `tests/test_reads.py::test_untainted_check_is_one_edge_statement` went red on the
  rename before its filters were updated (its docstring records it). The anchor content
  pin moved for five `models.py` classes; the cited `CORRESPONDENCE.md` rows (313, 378,
  626, 1717, dated 2026-10-07) were re-read and none states a table name, then it was
  regenerated.
- B3: `PYPI_README.md` is the PyPI long description (install, quickstart, caveats,
  absolute links). Its quickstart is EXECUTED by
  `tests/test_tk122_release_metadata.py`, which also pins `CHANGELOG.md`'s newest version
  to `zanzibar.__version__` (now the single version source, via setuptools `dynamic`).
- sec 3 items: metadata (authors -- name only, no email published -- classifiers, urls,
  keywords), dependency floors at the gate env's versions (`sqlmodel>=0.0.39`,
  `pyroaring>=1.1.0`), `py.typed`, `MANIFEST.in` pruning `tests/` etc. from the sdist,
  `CHANGELOG.md`. Rebuilt artifacts pass `twine check --strict`; the wheel installed in a
  clean venv ran the README quickstart green (sqlmodel 0.0.48 / SQLAlchemy 2.1.3).
- CI: `.github/workflows/gate.yml` (the ten verify.sh phases; `lean` uploads `zcli` to the
  five conformance tiles) and `.github/workflows/fuzz.yml` (on demand / `workflow_call`,
  multi-seed via `--hypothesis-seed`). `actionlint` 1.7.12 clean on both, and it flagged
  a deliberately broken control file (shellcheck integration was NOT available, so the
  `run:` scripts are unlinted). **UNVERIFIED on GitHub: neither workflow has run**, since
  that needs a push. The Linux portability of the tests tiles was checked in WSL; see the
  ledger lines below.

## 1. What already works (RAN, 2026-10-07)

- `python -m build` in a throwaway venv (setuptools >= 68, Python 3.13.14) produces
  `zanzibar-0.1.0-py3-none-any.whl` (~252 KB) and `zanzibar-0.1.0.tar.gz` (~839 KB), rc 0.
- `twine check` PASSED on both; `check-wheel-contents` OK on the wheel.
- The wheel holds only `zanzibar/**.py` plus dist-info -- no tests, no formal/, no data.
- Installed into a SECOND clean venv (deps resolved: sqlmodel 0.0.48, SQLAlchemy 2.1.3,
  pydantic 2.13.5, pyroaring 1.2.0), `import zanzibar` resolves to site-packages, and a
  `ConnectedStore` smoke test over in-memory SQLite gave the right answers: a user granted
  `viewer` on a doc via `group#member` -> `True`; after a `banned` tuple under
  `but not banned` -> `False`.
- `src/` imports nothing from `tests/`, `formal/`, `benchmarks/` or `scripts/`, and
  reads no files by path (READ: grep for `from tests|formal|...`, `open(`,
  `Path(__file__`, `importlib.resources` -- 0 hits).
- The names `zanzibar`, `zanzibar-index`, `graph-zanzibar`, `pyzanzibar` all return 404
  on both `pypi.org/pypi/<n>/json` and `pypi.org/simple/<n>/` (RAN). REASONED: 404 means
  no live project; PyPI can still refuse a name (prohibited/previously-deleted names), and
  that is only learned at first upload -- a TestPyPI dry run settles it.

## 2. Blockers (must fix before a public release)

### B1. No licence (READ)
No `LICENSE` file, no `license` field in `pyproject.toml`. The GitHub repo is public
(RAN: API 200). REASONED: without a licence nobody may legally use, copy or redistribute
the code -- a PyPI upload grants PyPI distribution rights but grants USERS nothing. This is
the user's call (which licence), not an engineering one.

### B2. Generic table names in the global `SQLModel.metadata`, with `extend_existing=True` (RAN)
The library registers ten tables on SQLModel's DEFAULT metadata under generic names --
`store`, `node`, `edge`, `residue`, `residue_ref`, `delta_outbox`, `relation_tuple`,
`schema_record`, `tuple_log`, `index_cursor` -- and every one sets
`{'extend_existing': True}` (READ: `src/zanzibar/graphindex/models.py`,
`src/zanzibar/setengine/models.py`, `src/zanzibar/connectedstore/models.py`).
Consequences, both executed against the installed wheel:

- **user's `node` table defined FIRST, then `import zanzibar.graphindex`: NO error, and the
  user's table silently gains zanzibar's columns** (`['id', 'label', 'store_id',
  'predicate', 'type', 'name', 'wildcard', 'implicit', 'reference_count']`). That is this
  repo's house failure mode (fails by passing) handed to every consumer.
- zanzibar imported FIRST, then the user's `node` table: loud `InvalidRequestError: Table
  'node' is already defined for this MetaData instance`.
- REASONED: any consumer calling `SQLModel.metadata.create_all(engine)` for their OWN app
  also creates all ten zanzibar tables in their database, and vice versa.

`extend_existing` was there to tolerate the `legacy/index_v3.py` double registration
(`docs/tk120-repo-restructure-2026-10-05.md` A4b); `legacy/` was deleted by `TK120`, so
REASONED: it no longer has a reason to exist. Fix shape (decision for the row): a private
`MetaData` / SQLModel registry for the library (users call `zanzibar.<x>.create_all(engine)`
or similar) and/or a table prefix (`zanzibar_node` ...), and drop `extend_existing`.
**A table rename is a schema migration for any persisted PostgreSQL store** (TK120 doc
sec 7 item 7) -- REASONED: acceptable now because nothing is deployed (HANDOFF banner
2026-09-22c: "no production deployment anywhere"), and it gets more expensive after a
release, which is why it is a blocker and not a follow-up. Tests that match table names in
captured SQL text must move with it: READ `tests/test_reads.py:35` (dated 2026-10-07)
matches a table name by word-boundary regex over the lowercased SQL; the full census of
such sites is not done (UNVERIFIED that it is the only one).

### B3. The README is not a PyPI landing page (READ)
`pyproject.toml` uses `readme = "README.md"`, a 686-line research narrative ("another
~~yak-shaving exercise~~ exploratory side project") with no install line and no usage
example; table setup (`SQLModel.metadata.create_all`) is undocumented anywhere a user
would look. It carries 14 relative links (`](./...` / `](docs/...`), which PyPI does not
resolve (REASONED: PyPI renders the description without a base URL). Options: a short
package README for PyPI (install, quickstart mirroring the sec 1 smoke test, the
paranoia knob, supported DBs, link to the GitHub docs), keeping the long one in the repo.
Note `TK43` (README editorial TODOs) forbids deleting its markers.

## 3. Should fix (not blocking a 0.1.0 alpha)

- **Metadata gaps** (READ `pyproject.toml`): no `authors`, `license`, `classifiers`
  (at least `Development Status :: 3 - Alpha`, Python versions, OS Independent), `urls`
  (Homepage/Source/Issues), `keywords`.
- **No lower bounds on deps** (READ): `sqlmodel` is 0.0.x and breaks across minors.
  Floor at the versions the gate actually runs (read them from the conda env, not from
  sec 1's venv).
- **`requires-python = ">=3.13"`** (READ) is untested below 3.13 and possibly needlessly
  tight. REASONED: either keep it (honest -- it is the only version the gate runs) or
  add a 3.11/3.12 test leg before lowering it. Keep is the default.
- **sdist ships 105 files of `tests/`** but not `formal/`, the root `conftest.py` or
  `pytest.ini` (RAN: `tar tzf`), so the shipped tests cannot run from the sdist.
  REASONED: exclude `tests/` from the sdist (setuptools auto-includes `test*.py`), or ship
  enough to run them. Excluding is simpler and honest.
- **No `py.typed`** (RAN: none under `src/`). The code is annotated and `pyrefly.toml`
  exists; adding the marker lets consumers' type checkers use it.
- **Private names re-exported** from `zanzibar.schema` (`_iter_directs`,
  `_parse_schema_ast_unchecked`, `_member_types`, `_plan_leaves` -- READ
  `src/zanzibar/schema/__init__.py`). Fine for 0.x; say in the README that only `__all__`
  is public.
- **No CHANGELOG.**

## 4. Publishing mechanics (REASONED, nothing set up yet)

- No `.github/workflows/` exists (RAN). The gate is local-only (`formal/verify.sh`, ten
  phases, Lean toolchain) and is NOT reproducible in CI today, so the release workflow
  should only BUILD and UPLOAD; the gate is run locally on the tagged tree first
  (`CLAUDE.md`: gate before push).
- Recommended: PyPI **Trusted Publishing** (OIDC) from a GitHub Actions workflow triggered
  by a version tag, so no API token is stored anywhere. Needs the user to register the
  pending publisher on pypi.org (and test.pypi.org) -- an account-side step only the user
  can do.
- Dry run on TestPyPI first (settles the name question in sec 1).
- Version single-sourcing: `__version__` in `src/zanzibar/__init__.py` and `version` in
  `pyproject.toml` are two copies of `0.1.0` (READ). Use setuptools dynamic version from
  `zanzibar.__version__`, or a test pinning them equal.

## 5. Maturity, for the release notes (READ, HANDOFF/board 2026-10-07)

Known live correctness bugs: none recorded (banner line, 2026-10-03b). 64 open rows.
No performance target, SLA or production deployment exists (banner 2026-09-22c), and
paranoia defaults OFF with `residue` recommended for production
(`src/zanzibar/connectedstore/store.py::ConnectedStore.DEFAULT_PARANOIA`). Supported DBs:
SQLite and PostgreSQL at `READ COMMITTED` only. REASONED: an honest classifier is Alpha.
