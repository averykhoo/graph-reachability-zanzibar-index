# Changelog

All notable changes to the `zanzibar-index` distribution (import package `zanzibar`).
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/), with the usual 0.x caveat that any minor release
may break the API. The newest version heading must equal `zanzibar.__version__`
(`tests/test_tk122_release_metadata.py`).

## [0.0.4]

### Fixed
- A malformed OpenFGA JSON model is refused with a `ValueError` that names the field:
  the model given as `null` or a list, `type_definitions` that is not an array, a type
  definition with no `"type"`, a `computedUserset` with no `"relation"`, a union with no
  `"child"`, and so on. `parse_openfga_json` used to leak a bare `AttributeError`,
  `TypeError` or `KeyError`. An optional object or array given as `null` (OpenFGA's API
  emits `"metadata": null`) still reads as absent; a non-object `metadata` such as `[]`,
  previously ignored, is now refused.
- The `CyclicDerivedDependency` message names only the relations on the cycle, not every
  relation that depends on it. It no longer cites an internal spec, and it says what to
  write instead and how that rewrite differs.
- Reopening a store with `ConnectedStore(session, store_id, schema=...)` now compares the
  parsed schema, not the text. Before, a trailing newline, Windows line endings, a different
  indent, a comment, or reordered `type` / `define` blocks raised `SchemaMismatch` for the
  store's own schema. A different schema is still refused, and the stored text is never
  rewritten (found by the 0.0.3 install trial, `docs/pypi-trial-0.0.3-2026-10-08.md`).

### Changed
- `ZANZIBAR_PARANOIA=residue` (`paranoia='residue'`) now also checks crossing-middle
  completeness (invariant I14), but only for the entities each write touches. A regression
  of the 2026-08-09 crossing-middle fix used to grant access silently at this level. It now
  aborts the write with `InvariantViolation`. The check costs nothing on a schema without
  object wildcards (`object_wildcard_shapes`).

### Documentation
- The PyPI README now covers what the 0.0.3 install trial had to discover by hand: recursion
  through `and` / `but not` (refused by `ConnectedStore`, accepted by `SetEngine`, with a
  rewrite and how it differs), acyclic tuple data, lenient reads, and how to read a
  `LookupResult` (resolving node ids, markers, exclusions). `LookupResult` has a docstring.

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
