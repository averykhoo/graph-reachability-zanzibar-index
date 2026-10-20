# Release notes

What changed in each release, newest first, in short. The complete list, with every
reworded message and every fixed edge case, is the project's
[CHANGELOG.md](https://github.com/averykhoo/graph-reachability-zanzibar-index/blob/master/CHANGELOG.md).
Read it before you upgrade: any 0.x release may change the API, including a patch release.

## 0.1.0 (unreleased)

A deliberate break of the 0.0.x API, with no compatibility aliases. Code written for 0.0.5
stops importing until you rename a few things; [Upgrade from 0.0.x to 0.1](../how-to/upgrade-0.1.md)
walks through every step.

Breaking:

- `zanzibar.connectedstore.ConnectedStore` is now {py:class}`zanzibar.Store`, importable
  from the top level. The graph index's bookkeeping table model is now `IndexStore`, and
  the set engine's result type is `SetLookupResult`.
- Keyword names are `subject_type`, `subject_name`, `object_type` and `object_name`.
- `build_index` and `rebuild_index` take `index_store_id` by keyword only.
- The parsers raise {py:exc}`zanzibar.SchemaError` (still a `ValueError`).
  `ShapeRefusedSinceTK137` is renamed {py:exc}`zanzibar.ShapeNoLongerAccepted`.
- `at_least` must be `None` or an `int` of 0 or more.
- A `Store` refuses a `Session` with unsaved changes of yours, a database without the
  `zanzibar_*` tables ({py:exc}`zanzibar.TablesNotCreated`) and a SQLite file created by
  0.0.x ({py:exc}`zanzibar.TablesOutdated`).
- An `object_wildcard_shapes` entry must name a declared relation.
- **Some answers change.** A userset such as `doc:1#banned` is now a member of itself, as in
  OpenFGA, so one previously allowed check on a `but not` relation is now denied, and
  `lookup_reverse` results include the object's own userset.
- Many messages are reworded; code that matches on message text may need updating.

Added:

- {py:meth}`zanzibar.Store.expand` (Zanzibar Expand), {py:meth}`zanzibar.Store.adopt`, and
  `object_type` / `relation` filters on `lookup` and `lookup_reverse`.
- The OpenFGA tuple form, `add_tuple("user:alice", "viewer", "doc:d1")`, and OpenFGA JSON
  models as `schema=`.
- {py:meth}`zanzibar.Store.result_keys` and {py:meth}`zanzibar.Store.excluded_keys`.
- {py:exc}`zanzibar.ZanzibarError`, the base of every exception the library raises on
  purpose, plus new specific exceptions such as {py:exc}`zanzibar.StoreNotFound` and
  {py:exc}`zanzibar.StaleLookupIds`.

Fixed: a lookup result held across a write could translate to the wrong subjects; it is now
refused with `StaleLookupIds`.

## 0.0.5 (2026-10-14)

- **Breaking:** four schema shapes that OpenFGA refuses are refused here too: a `schema`
  version other than `1.1`, extra words on a `model`, `schema` or `relations` line, `but not`
  beside `or` / `and` without parentheses, and a restriction naming an undeclared type. A
  store saved by 0.0.4 or earlier with one of them no longer opens.
- `SetEngine.excluded_keys` was added.
- Fixed: under a wildcard grant, a standalone set engine's `lookup_reverse` did not list
  the users a `but not` refuses as excluded; a set engine opened on a store that a `ConnectedStore` owns
  answered under whatever schema it was given and could write past the tuple log; a
  `relations` line with a `define` on it silently dropped the relation.

## 0.0.4

- A malformed OpenFGA JSON model is refused with a message that names the field.
- Reopening a store with its own schema no longer fails over formatting: the parsed
  schema is compared, not the text.
- The `residue` runtime check covers one more kind of index corruption.

## 0.0.3

- The graph index serves `x from parent` when `x` uses `and` or `but not`.
- Several crashes on unusual schemas and on non-string write fields are now clear
  refusals.

## 0.0.2

The first release published to PyPI: the same library as 0.0.1, with a test-only fix.

## 0.0.1

Tagged but never published. It introduced the package: the schema parser and compiler, the
set engine, the graph index and the composed store, under the Apache-2.0 licence, with
every database table named `zanzibar_*`.
