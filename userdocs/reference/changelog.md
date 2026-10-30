# Release notes

What changed in each release, newest first, in short. The complete list, with every
reworded message and every fixed edge case, is the project's
[CHANGELOG.md](https://github.com/averykhoo/graph-reachability-zanzibar-index/blob/master/CHANGELOG.md).
Read it before you upgrade: any 0.x release may change the API, including a patch release.

## 0.1.1 (2026-10-30)

Fixes from the 0.1.0 install trial and one crash found in testing; no permission answer
changes.

- {py:meth}`zanzibar.Store.lag` sees another instance's `catch_up()` without a
  `refresh()`. It used to keep reporting the old backlog (it never under-reported).
- A tuple that makes an object its own parent (`doc:d1 parent doc:d1`) under a `from`
  chain could fail with a raw `IntegrityError` and, in async mode, stall the index. Where
  the schema accepts such a tuple, it is written normally now; a `from` chain that recurses
  through `parent` still refuses it as a cycle, as documented for
  {py:exc}`zanzibar.AdmissionRejected`. No wrong answer was served.
- Clearer errors: an old 0.0.x keyword such as `s_type=` is named with its 0.1 name;
  `ops=PySets()` says to pass `ops=PySets`; a trailing `# comment`, `[user: *]` and a chain
  of two `but not`s say what to write instead; a `SchemaMismatch` says when swapped
  `or` / `and` / `but not` operands are the difference.
- Each docs page uses its own SQLite file, so two pages run in one folder no longer clash.

## 0.1.0 (2026-10-30)

A deliberate break of the 0.0.x API, with no compatibility aliases. Code written for 0.0.5
stops importing until you rename a few things; [Upgrade from 0.0.x to 0.1](../how-to/upgrade-0.1.md)
walks through every step.

Breaking:

- `zanzibar.connectedstore.ConnectedStore` is now {py:class}`zanzibar.Store`, importable
  from the top level. The graph index's bookkeeping table model is now `IndexStore`, and
  the set engine's result type is `SetLookupResult`.
- Keyword names are `subject_type`, `subject_name`, `object_type` and `object_name`.
- `build_index` and `rebuild_index` take `index_store_id` by keyword only.
- The Python `Ellipsis` is refused as a subject predicate; a bare subject is the string
  `"..."`.
- Each subpackage's `__all__` lists only its public names, and **exceptions are exported
  from `zanzibar` only**: write `from zanzibar import StaleRead`, not
  `from zanzibar.store import StaleRead`.
- The parsers raise {py:exc}`zanzibar.SchemaError` (still a `ValueError`).
  `ShapeRefusedSinceTK137` is renamed {py:exc}`zanzibar.ShapeNoLongerAccepted`.
- {py:exc}`zanzibar.UnsupportedByGraphIndex` and {py:exc}`zanzibar.DoublyBridgedShapeError`
  are now `ValueError`s, so an `except ValueError` that let them through now catches them.
- `at_least` must be `None` or an `int` of 0 or more.
- A freshness token from another store is refused on every tokened read with the new
  {py:exc}`zanzibar.ForeignToken` (a `StaleRead`); before, one at or below the store's own
  writes was accepted without error.
- A `Store` refuses a `Session` with unsaved changes of yours, a database without the
  `zanzibar_*` tables ({py:exc}`zanzibar.TablesNotCreated`) and a SQLite file created by
  0.0.x ({py:exc}`zanzibar.TablesOutdated`).
- A `SetEngine` raises {py:exc}`zanzibar.PersistedSchemaRefused` for a store whose saved
  schema this version refuses, as every other entry point does.
- An `object_wildcard_shapes` entry must name a declared relation.
- **Some answers change.** A userset such as `doc:1#banned` is now a member of itself, as in
  OpenFGA, so one previously allowed check on a `but not` relation is now denied, and
  `lookup_reverse` results include the object's own userset.
- Many messages are reworded; code that matches on message text may need updating.

Added:

- {py:meth}`zanzibar.Store.expand` (Zanzibar Expand) and {py:meth}`zanzibar.Store.adopt`.
- Filters on lookups: `object_type` / `relation` on `lookup`, and `subject_type` /
  `subject_predicate` on `lookup_reverse`.
- The OpenFGA tuple form, `add_tuple("user:alice", "viewer", "doc:d1")`, and OpenFGA JSON
  models as `schema=`.
- {py:meth}`zanzibar.Store.result_keys` and {py:meth}`zanzibar.Store.excluded_keys`, and
  `LookupResult.implicit_keys` / `implicit_excluded_keys` for answers that have no node
  id (a userset that is a member of itself before any tuple names it).
- {py:exc}`zanzibar.ZanzibarError`, the base of every exception the library raises on
  purpose, plus new specific exceptions such as {py:exc}`zanzibar.StoreNotFound`,
  {py:exc}`zanzibar.StaleLookupIds` and {py:exc}`zanzibar.ForeignToken`.
- Public types and helpers: {py:class}`zanzibar.graphindex.DeltaProcessor`,
  {py:func}`zanzibar.store.open_set_engine`, and the schema types that appear in public
  signatures ({py:class}`zanzibar.schema.SchemaInfo`,
  {py:class}`zanzibar.schema.CompiledBooleans`, {py:class}`zanzibar.schema.Entity`,
  {py:class}`zanzibar.schema.RelationalTriple`).

Fixed:

- With paranoia `full` or `fixpoint`, a failed post-commit check now raises
  {py:exc}`zanzibar.InvariantViolation` after the commit, saying the write is committed, and
  the `Store` stays usable. It used to surface as SQLAlchemy's `InvalidRequestError` and
  leave the `Store` unusable.
- Public docstrings no longer cite internal task ids or repository paths, and the ones that
  were missing were written.
- A lookup result held across a write could translate to the wrong subjects; it is now
  refused with `StaleLookupIds`.
- A write refused by the fan-out cap is cheap to refuse: the graph index counts the rows
  it would touch and refuses before loading them, and a `Store` no longer rebuilds its set
  engine after the refusal. See
  [A refused write is not free](../explanation/limits.md#a-refused-write-is-not-free).
- A direct graph-index write on a schema with `and` / `but not` that is committed without
  running the delta processor's cascade is refused at the commit with the new
  {py:exc}`zanzibar.CascadeNotRun`, instead of committing derived relations that disagree
  with the set engine. A `Store` is not affected.
- With `ZANZIBAR_PARANOIA=full` or `fixpoint`, releasing a savepoint
  (`session.begin_nested()`) ran the after-commit check, which on an in-memory SQLite
  database rolled back the caller's whole open transaction. The check now runs only when
  the outermost transaction commits.
- A stall recorded while nothing was pending is cleared by the next successful
  `catch_up()`, even one that applies nothing; until then untokened lookups raised
  {py:exc}`zanzibar.IndexStalled`.
- A sync write refused because an earlier backlog row cannot be applied now says so,
  names that row, and gives the recovery, instead of reading as if your own write was too
  big. See [Recover from a stalled index](../how-to/stall-recovery.md).
- A user string with a `:` in its relation part, such as `"user:a#b:c"`, raises
  {py:exc}`zanzibar.MalformedTupleString` on reads as well as writes.
- The `StaleRead` and `WatermarkGap` messages say "set engine" where they said
  "evaluator".

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
