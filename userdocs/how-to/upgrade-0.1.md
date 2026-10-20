# Upgrade from 0.0.x to 0.1

Version 0.1.0 breaks the public API of 0.0.x on purpose, and there are no compatibility
aliases: code written for 0.0.5 stops importing until you rename a few things. It also
changes some answers on models that use `and` / `but not` with userset subjects. This page
walks through the upgrade in the order the problems will show up: imports, call
signatures, database files, then answers.

The full list of changes is in the [changelog](../reference/changelog.md). This page covers
what a 0.0.x caller has to change, and its last steps list the smaller changes and what
0.1 adds.

```{note}
Until 0.1.0 is released, a build from the source tree already has every change on this
page but still reports `zanzibar.__version__ == "0.0.5"`. Do not use the version number to
decide which API you have.
```

## 1. Rename the imports

The package that holds the composed store was renamed, and so was its class:

| 0.0.x | 0.1 |
|---|---|
| `zanzibar.connectedstore` | `zanzibar.store` |
| `zanzibar.connectedstore.ConnectedStore` | `zanzibar.Store` (also `zanzibar.store.Store`) |
| `zanzibar.graphindex.Store` (the index's bookkeeping table model) | `zanzibar.graphindex.IndexStore` |
| `zanzibar.setengine.LookupResult` (the set engine's result) | `zanzibar.setengine.SetLookupResult` |
| `ShapeRefusedSinceTK137` | `zanzibar.ShapeNoLongerAccepted` |

Everything else in `zanzibar.store` keeps its 0.0.x name: `TupleSource`, `build_index`,
`rebuild_index`, `save_schema`, `SchemaRecord`, `TupleLog`. The database table names did not
change either; the `IndexStore` model still uses the table `zanzibar_store`.

Before, in 0.0.x:

```python
# not run: 0.0.x code, which no longer imports
from zanzibar.connectedstore import ConnectedStore

store = ConnectedStore(session, "app", schema=SCHEMA)
```

After:

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

SCHEMA = """
model
  schema 1.1

type user

type doc
  relations
    define banned: [user]
    define viewer: [user, doc#banned] but not banned
"""

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
session = Session(engine)
store = Store(session, "app", schema=SCHEMA)
print(type(store).__name__)  # -> 'Store'
```

The common names now import from the top level, `from zanzibar import Store, LookupResult,
ExpandResult, parse_openfga_schema`, together with every exception class. These imports are
lazy, so `import zanzibar` on its own does not load the database libraries.

Each subpackage's `__all__` now lists only its public names. Helpers that were removed from
`__all__` (for example `advance_index` in `zanzibar.store`, or `Interner` and `NodeSets` in
`zanzibar.setengine`) still import by name, but `from zanzibar.store import *` no longer
brings them in, and they are not part of the documented API.

## 2. Fix keyword arguments and other call signatures

**Keyword names.** The six tuple parameters are now spelled out in full on `add_tuple`,
`remove_tuple`, `check`, `lookup` and `lookup_reverse` of {py:class}`zanzibar.Store`,
{py:class}`zanzibar.setengine.SetEngine` and {py:class}`zanzibar.graphindex.WildcardIndex`,
and on `TupleSource.add` / `remove` / `check`:

| 0.0.x keyword | 0.1 keyword |
|---|---|
| `s_type` | `subject_type` |
| `s_name` | `subject_name` |
| `o_type` | `object_type` |
| `o_name` | `object_name` |

`subject_predicate` and `relation` are unchanged. Positional calls work as before; only
calls that pass the old names as keywords raise `TypeError`.

```python
allowed = store.check("...", subject_type="user", subject_name="alice",
                      relation="viewer", object_type="doc", object_name="1")
print(allowed)  # -> False
```

A `Store` (and a `TupleSource`) also accepts the OpenFGA tuple form now, which is shorter:
`store.check("user:alice", "viewer", "doc:1")`. The six-part form still works.

**Other signature changes:**

- `build_index` and `rebuild_index` take `index_store_id` by keyword only. Write
  `build_index(session, "src", index_store_id="idx")`. `build_index` now returns a
  `BuildReport` named tuple, which still unpacks as `cursor, widx, ruleset = ...`.
- The Python `Ellipsis` (`...` without quotes) is refused as a subject predicate. The bare
  subject is the string `"..."`. Writes raise {py:exc}`zanzibar.AdmissionRejected` and
  reads raise `TypeError`. `None` still means a bare subject on a read.
- `at_least` must be `None` or an `int` that is 0 or more. `True` and negative numbers are
  refused (`TypeError` / `ValueError`).

```python
refused = False
try:
    store.check(..., "user", "alice", "viewer", "doc", "1")
except TypeError:
    refused = True
print(refused)  # -> True

refused = False
try:
    store.check("user:alice", "viewer", "doc:1", at_least=True)
except TypeError:
    refused = True
print(refused)  # -> True
```

## 3. Commit your own changes before calling the store

A `Store` commits and rolls back its own transactions. In 0.0.x, rows you had added to the
same `Session` but not committed were committed along with a store write, or thrown away by
a store rollback, without telling you. In 0.1 a `Store` refuses a `Session` with pending ORM
changes, when it opens, on every write and in `refresh()`, with a `ValueError`. Commit or
roll back your own changes first, or give the store its own session.

```python
from sqlmodel import Field

class Note(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    text: str

SQLModel.metadata.create_all(engine)

session.add(Note(text="not committed yet"))
refused = False
try:
    store.add_tuple("user:bob", "viewer", "doc:1")
except ValueError:
    refused = True
print(refused)  # -> True

session.commit()                                  # your change first
store.add_tuple("user:bob", "viewer", "doc:1")    # now the store can write
print(store.check("user:bob", "viewer", "doc:1"))  # -> True
```

## 4. Update exception handling

Exception classes keep their builtin bases, so `except ValueError`, `except KeyError` and
`except RuntimeError` handlers keep catching what they caught before. The one handler that
can stop matching is `except UnsupportedByGraphIndex` around `object_wildcard_shapes`; see
the last bullet but one. What changed:

- Every exception the library raises on purpose is now a {py:exc}`zanzibar.ZanzibarError`,
  so one `except ZanzibarError` catches them all. {py:exc}`zanzibar.InvariantViolation`
  (store corruption) is deliberately not one.
- The schema parsers raise {py:exc}`zanzibar.SchemaError` (still a `ValueError`). Code that
  tests `type(e) is ValueError` must change; `except ValueError` still works.
- Opening a store id that was never created raises {py:exc}`zanzibar.StoreNotFound` (still a
  `KeyError`).
- Opening a `Store` on a database without the `zanzibar_*` tables raises
  {py:exc}`zanzibar.TablesNotCreated` (a `RuntimeError`) instead of the database driver's own
  error.
- `build_index` over an index that already exists raises {py:exc}`zanzibar.IndexExists`
  (still a `ValueError`).
- A `SetEngine` opened on a store whose saved schema this version refuses raises
  {py:exc}`zanzibar.PersistedSchemaRefused`, as `Store` already did. In 0.0.5 it raised
  `SchemaMismatch` or the parser's own refusal.
- An `object_wildcard_shapes` entry that names an undeclared type or relation, or a compiled
  name such as `("doc", "view.0")`, raises {py:exc}`zanzibar.ShapeNoLongerAccepted`. 0.0.5
  accepted an undeclared name (it had no effect) and refused a compiled name with
  {py:exc}`zanzibar.UnsupportedByGraphIndex`. `ShapeNoLongerAccepted` is a
  {py:exc}`zanzibar.SchemaError`, not an `UnsupportedByGraphIndex`, so an
  `except UnsupportedByGraphIndex` handler no longer catches it: catch
  `ShapeNoLongerAccepted` or `SchemaError` instead. A store saved by 0.0.5 with such an
  entry no longer opens; see [Change a schema](change-schema.md), because schemas are
  write-once.
- Many messages are reworded so they say what to do next. If your code matches on message
  text, check it against the new messages.

```python
import zanzibar

caught = None
try:
    Store(session, "no-such-store")
except zanzibar.StoreNotFound as e:
    caught = e
print(isinstance(caught, KeyError) and isinstance(caught, zanzibar.ZanzibarError))  # -> True
```

## 5. Recreate SQLite database files

A `Store` refuses a SQLite file whose tables 0.0.x created, with
{py:exc}`zanzibar.TablesOutdated`. In those files SQLite could hand a deleted node's id to a
new node, so a lookup result held across a write could name the wrong entity. 0.1 does not
migrate the file in place: create the tables in a new file and write the tuples again.

The tuples and the schema are plain rows in the old file, so you can read them with the
standard `sqlite3` module and replay them through the public API. Replace `"app"` with your
store id, and run this once per store id:

```python
# not run: needs a SQLite file written by 0.0.x
import json
import sqlite3

from sqlmodel import SQLModel, Session, create_engine
import zanzibar.store
from zanzibar import Store

old = sqlite3.connect("old.db")
schema_text, wildcard_shapes = old.execute(
    "select schema_text, object_wildcard_shapes from zanzibar_schema_record"
    " where store_id = ?", ("app",)).fetchone()
tuples = old.execute(
    "select subject_predicate, subject_type, subject_name,"
    "       relation, object_type, object_name"
    " from zanzibar_relation_tuple where store_id = ? order by id", ("app",)).fetchall()
old.close()

engine = create_engine("sqlite:///new.db")
SQLModel.metadata.create_all(engine)
with Session(engine) as session:
    store = Store(session, "app", schema=schema_text,
                  object_wildcard_shapes=frozenset(tuple(s) for s in json.loads(wildcard_shapes)))
    for t in tuples:
        store.add_tuple(*t)
```

`zanzibar_relation_tuple` holds the tuples that are stored now; the old file's tuple log is
history and is not copied. Every replayed tuple gets a new log id, so **discard any
freshness tokens (`at_least` values) your app saved against the old file**: they mean
nothing in the new one, and one past the new log's head is refused.

The new file has no stored schema yet, so `Store(...)` parses the text you pass it. If the
old schema uses a shape this version refuses, that line raises
{py:exc}`zanzibar.ShapeNoLongerAccepted` (a {py:exc}`zanzibar.SchemaError`); its message,
and its `instead` attribute, give the rewrite to use. See
[Rewrite a refused schema shape](rewrite-refused-shape.md).

The loop above commits once per tuple. For a large store, write the tuples with a
standalone `SetEngine` in a few large transactions and then call `Store.adopt`, which
builds the graph index in bulk; see [Bulk-load or adopt an existing store](bulk-load-adopt.md).

The check is made only on SQLite, where the old tables let a deleted id be handed out again.
On PostgreSQL a `Store` opens the 0.0.x tables as they are.

## 6. Check answers for userset subjects on `and` / `but not` models

In 0.1 a userset is a member of itself, as in OpenFGA: the subject `doc:1#banned` counts as
a `banned` of `doc:1`, whether or not any tuple says so. 0.0.x did not apply this rule. For
users (`user:alice`), for `user:*` and for userset-star subjects such as `doc:*#viewer`,
nothing changes: the rule only ever adds the userset itself, never its members.

On a model with only `or` this can only add access. On a model with `but not` or `and` it
can also take access away. Here is the case that flips from ALLOW to DENY. The schema from
step 1 says that a viewer is a direct viewer who is not banned, and it lets the userset
`doc#banned` be a viewer:

```text
define banned: [user]
define viewer: [user, doc#banned] but not banned
```

With the tuple `doc:1#banned viewer doc:1`, 0.0.x answered that `doc:1#banned` is a viewer
of `doc:1`. 0.1 answers no, because `doc:1#banned` is now in its own `banned`:

```python
# not run: 0.0.x code; 0.0.5 printed True here
store.add_tuple("banned", "doc", "1", "viewer", "doc", "1")
print(store.check("banned", "doc", "1", "viewer", "doc", "1"))
```

```python
store.add_tuple("doc:1#banned", "viewer", "doc:1")
print(store.check("doc:1#banned", "viewer", "doc:1"))  # -> False
print(store.check("doc:1#banned", "banned", "doc:1"))  # -> True
```

The opposite flip, DENY to ALLOW, happens with `and`. With
`define vy: [user, doc#editor] and editor` and the tuple `doc:1#editor vy doc:1`,
`check("doc:1#editor", "vy", "doc:1")` was `False` and is now `True`. When `doc` declares
`viewer`, `check("doc:1#viewer", "viewer", "doc:1")` is now `True` even on an empty store.

Code that only ever checks users is unaffected. If your app stores tuples whose subject is a
userset of the same object, as above, re-run your permission tests after upgrading and look
for these changes.

**Lookups list these usersets too.** `lookup_reverse("viewer", "doc:1")` now includes the
userset `doc:1#viewer` itself, and the other usersets of `doc:1` that `viewer` is built on.
Read results through `store.result_keys(result)`. If you list users by keeping only keys
of type `user`, nothing changes for you:

```python
result = store.lookup_reverse("viewer", "doc:1")
print(sorted(store.result_keys(result)))  # -> [('doc', '1', 'viewer'), ('user', 'bob', '...')]
users = sorted(k for k in store.result_keys(result) if k[0] == "user")
print(users)  # -> [('user', 'bob', '...')]
```

A userset that no tuple names has no node in the index, so it arrives in the new
`implicit_keys` field of the result rather than in `node_ids`; `result_keys` includes both.
No tuple mentions `doc:9`, so its only answer is implicit:

```python
result = store.lookup_reverse("viewer", "doc:9")
print(result.implicit_keys)  # -> {('doc', '9', 'viewer')}
print(result.node_ids)  # -> set()
print(sorted(store.result_keys(result)))  # -> [('doc', '9', 'viewer')]
```

[Semantics and differences from OpenFGA](../explanation/semantics-vs-openfga.md) explains
the rule, the one place where it still applies differently from OpenFGA (a `from` whose
parent type does not declare the target relation), and the other differences from OpenFGA.

## 7. Check the smaller changes

These break less code, but look for them:

- `zanzibar.setengine.LookupResult` no longer exists, and `SetLookupResult` is now a
  dataclass: build one with keyword arguments, and compare two with `==`.
- `Store(schema=...)` takes DSL text or an OpenFGA JSON model. A compiled `RuleSet` now
  raises `TypeError`; pass the schema text it was compiled from.
- {py:exc}`zanzibar.UnprovenExtensionWarning` is now raised once, attributed to your line
  that called `Store(...)`, `parse_openfga_schema(...)` or `SetEngine(...)` rather than to a
  line inside the library. A `warnings` filter keyed on the library's module or line number
  needs updating; one keyed on the category keeps working.
- `SetEngine(session, store_id)` may leave out the schema when a `Store` created the store;
  it reads the saved schema.

The [changelog](../reference/changelog.md) has the rest.

## 8. Optional: use what 0.1 adds

None of these is needed to upgrade, but each one replaces something you may have written by
hand on 0.0.x.

**Filters on lookups.** `lookup` takes `object_type=` and `relation=`, and `lookup_reverse`
takes `subject_type=` and `subject_predicate=`. You no longer need to filter the result
yourself:

```python
users_only = store.lookup_reverse("viewer", "doc:1",
                                  subject_type="user", subject_predicate="...")
print(sorted(store.result_keys(users_only)))  # -> [('user', 'bob', '...')]
```

**`Store.expand`.** Zanzibar's Expand on the store: every subject that has a relation on an
object, as `(type, name, predicate)` keys. In 0.0.x the only Expand was
`SetEngine.expand`, which returns ids that mean nothing outside that engine instance.
Test one subject with `in`:

```python
members = store.expand("viewer", "doc:1")
print(("user", "bob", "...") in members)  # -> True
```

**`Store.adopt`.** In 0.0.x, opening a `Store` on tuples written without the tuple log took
four steps (`save_schema`, commit, `build_index`, `Store(...)`). `Store.adopt(session, id,
schema=...)` does it in one call and returns `(store, report)`. See
[Bulk-load or adopt an existing store](bulk-load-adopt.md).

**Reading results.** `store.result_keys(result)` and `store.excluded_keys(result)` turn a
`lookup` / `lookup_reverse` result into `(type, name, predicate)` keys, with no SQL on the
`zanzibar_node` table. [Find who can access what](query-access.md) shows how to read a
result, including its wildcard markers.

**JSON models.** `Store(schema=...)` also accepts an OpenFGA JSON model, as a `dict` or a
JSON string.

```python
session.close()
```
