# Changelog

All notable changes to the `zanzibar-index` distribution (import package `zanzibar`).
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/), with the usual 0.x caveat that any minor release
may break the API. The newest version heading must equal `zanzibar.__version__`
(`tests/test_tk122_release_metadata.py`).

## [Unreleased]

## [0.0.3]

Fixes everything the fresh-user install trial of the published 0.0.2 found broken
(`docs/pypi-trial-0.0.2-2026-10-07.md`).

### Fixed
- The graph index now serves `x from parent` when `x` names a boolean (`and` / `but not`)
  relation on some type, which is the common OpenFGA pattern of every type defining its
  own `viewer`. Before, `parse_openfga_schema` and `ConnectedStore` raised
  `UnsupportedByGraphIndex` on schemas the set engine accepted. The admission checks now
  compare `(type, relation)` instead of the bare relation name.
- `define viewer: ([user] or viewer from parent) but not banned` no longer crashes both
  backends with an internal `ValueError: Rule then-pattern carries a derived subject
  predicate`. It is served.
- A schema that declares no type (empty, whitespace, comments only, or only the
  `model` / `schema 1.1` header) is refused at parse time, and so is one whose types declare
  no relation. The same goes for an OpenFGA JSON model with no `type_definitions` or no
  relations. `ConnectedStore` used to persist these schemas write-once, which made the
  store id unusable.
- A write field that is not a `str` (`None`, numbers, bytes) is refused with
  `AdmissionRejected` on every backend and for every field. A `None` subject predicate
  used to leak `sqlalchemy.exc.IntegrityError` from `ConnectedStore`, and `SetEngine`
  silently accepted it as the bare predicate.
- A store id must be a `str` containing a non-whitespace character. `None`, numbers,
  bytes and blank strings now raise `AdmissionRejected` in every constructor. Before, they
  were accepted, or leaked a database error.

## [0.0.2]

First release published to PyPI. Same library as 0.0.1.

### Fixed
- `formal/conformance/test_runner_retry.py`'s spawn-error stub now sets `.winerror`
  explicitly. Only Windows CPython derives it from `OSError`'s fourth argument, so on the
  Linux CI runner the retry test failed and the no-retry test passed for the wrong reason.
  Test-only; no library change.

## [0.0.1]

Tagged but never published: the release gate failed on the Linux CI runner (the test
above), so the upload was skipped. A trial of the release pipeline (tag -> gate -> fuzz ->
PyPI), not a stability promise.

### Added
- The `zanzibar` package: `zanzibar.schema` (OpenFGA-DSL parser and compiler, including
  `and` / `but not`), `zanzibar.setengine`, `zanzibar.graphindex` and
  `zanzibar.connectedstore`.
- Apache-2.0 licence, `py.typed` marker, PyPI metadata.

### Changed
- All database tables are prefixed `zanzibar_` (`node` -> `zanzibar_node`, ...), as are the
  explicit constraint and index names. The tables no longer set `extend_existing`, so a
  name clash with an application's own table raises instead of silently merging the two.
  This is a schema change for any existing database. There is no migration: rebuild the
  store from its tuples.
