# Changelog

All notable changes to the `zanzibar-index` distribution (import package `zanzibar`).
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/), with the usual 0.x caveat that any minor release
may break the API. The newest version heading must equal `zanzibar.__version__`
(`tests/test_tk122_release_metadata.py`).

## [0.0.5] - 2026-10-14

### Added
- `SetEngine.excluded_keys(result)`: the portable `(type, name, predicate)` form of a
  `LookupResult`'s `excluded_node_ids`, the companion of `result_keys`. A lookup result
  that leaves the process is three parts: `result_keys`, `markers` and `excluded_keys`.
  `result_keys`'s docstring had called its output alone "the portable form", which would
  drop a `but not` exclusion at a service boundary (TK139 review).

### Changed
- **Breaking: four DSL shapes that OpenFGA refuses are refused here too** (`ValueError` at
  parse, with what to write instead) (TK137):
  - a `schema` line naming any version but `1.1` (`schema 1.2`, a bare `schema`). The version
    used to be ignored. Write `schema 1.1`; schema 1.2's modules are not supported.
  - extra words on a `model`, `schema 1.1` or `relations` line, a trailing comment included
    (`relations # docs`). Put each `define`, and each comment, on its own line.
  - `but not` beside `or` / `and` / a second `but not` at one level. It used to bind loosest,
    so `a but not b or c` meant `a but not (b or c)`. Parenthesise the reading you mean:
    `(a or b) but not c`, `a but not (b or c)`, `(a but not b) or c`.
  - a restriction naming a type no `type` line declares (`define viewer: [usr]` with no
    `type usr`), also in `parse_openfga_json`. Before, the typo let a `usr:x` write in and
    `check` said True. Declare the type or fix the spelling.
- `unparse_schema_ast` and `openfga_json_to_dsl` now declare every restriction type that has
  no relations (`type user`) at the top, and parenthesise both operands of `but not`, so
  their output parses under the rules above.
- `module`, `extend type`, `condition` blocks and `[user with cond]` were already refused;
  the message now names the unsupported OpenFGA feature.
- **No migration path for persisted stores.** Opening a store re-parses its persisted schema
  text, so a store saved under 0.0.4 or earlier with one of the refused shapes (including
  `openfga_json_to_dsl` output that restricts to a relation-less type, or renders
  `a or b but not c`) now refuses to open, and no public API drops a store id. The only
  way forward is a new store id with the rewritten schema, with its tuples written again.
  Such a store's open raises `zanzibar.connectedstore.PersistedSchemaRefused` (a
  `ValueError`), whose message says the schema was saved by 0.0.4 or earlier using a shape
  this version refuses, quotes the refusal, and gives the rewrite that keeps the meaning the
  store was serving (`instead` attribute), so the break does not read as corruption.

### Fixed
- `advance_index(..., proc=None)` on a schema with `and` / `but not` relations now raises
  `zanzibar.connectedstore.MissingDeltaProcessor` (a `ValueError`) before reading or writing
  anything, and the message names the fix: pass `DeltaProcessor(widx, ruleset.compiled)`, or
  let `ConnectedStore` advance the index (`refresh()` / `catch_up()`). Before, it applied the
  log without maintaining the `and` / `but not` relations, so the graph index silently
  disagreed with the set engine: with `define viewer: [user] but not banned` and alice
  granted, the index said False and the set engine True. A schema with only unions still
  takes `proc=None` (TK123).
- A `SetEngine` opened on a store id that a `ConnectedStore` owns (the id has a persisted
  schema) now compares the schema it is given with the store's and raises `SchemaMismatch`
  if they differ, by the same rule as `ConnectedStore(..., schema=...)`: the parsed schema
  and the declared `object_wildcard_shapes` must be equal, so formatting and the order of
  `type` / `define` lines do not matter. Before, it answered under whatever schema it was
  given: with the store's `but not banned` dropped, a banned user read as allowed.
  `zanzibar.connectedstore.open_set_engine(session, store_id)` opens one with the store's
  own schema. A `SetEngine` on a store id no `ConnectedStore` owns is unchanged: it uses
  the schema it is given. `SchemaMismatch` now lives in `zanzibar.schema.errors` and is also
  exported from `zanzibar.schema`; `zanzibar.connectedstore.SchemaMismatch` is the same
  class, so existing `except` clauses still catch it (TK123).
- A `relations` line with a `define` on it (`relations define viewer: [user]`) parsed and
  silently dropped the relation. It is now refused (TK137).
- `SetEngine.lookup_reverse` now fills `excluded_node_ids` with the subjects a `but not`
  refuses under a wildcard grant, as `ConnectedStore.lookup_reverse` already did. Before,
  with `define viewer: [user:*] but not banned`, a `user:*` grant and `mallory` banned, it
  returned the "every user" marker with nothing excluded, so a list-users page built on the
  standalone set engine listed mallory although `check` refused her (TK139).
- A standalone `SetEngine` opened on a store id that a `ConnectedStore` owns (the id has a
  persisted schema) now refuses `add_tuple` / `remove_tuple` with `UnloggedWriteRefused`;
  reads through it still work. Before, its writes skipped the tuple log: an unlogged
  `remove_tuple` left the grant ALLOWed by `ConnectedStore.check` with `lag() == 0`, and
  `ConnectedStore.remove_tuple` then refused to revoke it. The engine also refuses once the
  id is claimed after it was opened, from its next transaction on (TK140).
- `ConnectedStore(session, store_id, ...)` refuses, with the new
  `zanzibar.connectedstore.UnloggedTuplesPresent`, to open a store id for the first time
  when it holds tuples the tuple log does not account for (written by a standalone
  `SetEngine`). Before, it adopted them silently: its index never saw them (`check` False
  while the set engine said True), and removing one raised `InvariantViolation`. The
  refused open writes nothing. To adopt such a store: `save_schema(session, id, schema)`,
  commit, `build_index(session, id)`, then `ConnectedStore(session, id)` (TK140).

### Documentation
- **A userset is not a member of itself here, unlike OpenFGA** (documented, not changed;
  TK138). OpenFGA counts `doc:1#banned` as a member of `doc:1#banned`, and so of every
  relation built on it; this library does not, except through a `from` parent. The
  security-relevant case: with `define vx: [user, doc#banned] but not banned` and the tuple
  `doc:1#banned vx doc:1`, checking `doc:1#banned` for `vx` on `doc:1` is allowed here and
  denied by OpenFGA. The opposite also happens: `define vy: [user, doc#editor] and editor`
  with `doc:1#editor vy doc:1` is denied here and allowed by OpenFGA. Only userset subjects
  are affected; plain users and `user:*` are not. The PyPI README lists it. Adopting
  OpenFGA's rule is planned for a later minor version, because it changes answers.
- The READMEs now state that a grant on every instance (`folder:*`) does not reach a grant
  on "any" instance while no instance exists, with a zero-folders example. This strict
  reading is the current mode; a lenient mode may come later, in all backends together
  (TK4).

## [0.0.4]

### Fixed
- A malformed OpenFGA JSON model is refused with a `ValueError` that names the field:
  the model given as `null` or a list, `type_definitions` that is not an array, a type
  definition with no `"type"`, a `computedUserset` with no `"relation"`, a union with no
  `"child"`, and so on. `parse_openfga_json` used to leak a bare `AttributeError`,
  `TypeError` or `KeyError`. An optional object or array given as `null` (OpenFGA's
  DSL-to-JSON transformer emits `"metadata": null`) still reads as absent; a non-object
  `metadata` such as `[]`, previously ignored, is now refused.
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
- Statements about OpenFGA were checked against its documentation and source, and the
  inaccurate ones corrected. The schema language is described as a subset of the OpenFGA
  DSL (no conditions or modules). Wildcard tuplesets (`parent: [folder:*]`) are listed with
  the other extensions beyond OpenFGA. The userset-tupleset refusal message now tags only
  the refusal itself as the OpenFGA rule, not its suggested rewrite.

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
