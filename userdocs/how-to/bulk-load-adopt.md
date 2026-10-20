# Bulk-load or adopt an existing store

This page covers two related tasks:

- **Loading many tuples before a store goes live**, in one transaction instead of one
  commit per tuple.
- **Adopting a store that a standalone {py:class}`zanzibar.setengine.SetEngine` wrote**, so
  that a {py:class}`zanzibar.Store` can serve it.

Both end the same way: {py:meth}`zanzibar.Store.adopt` builds the graph index from the
stored tuples in one pass and opens the `Store`.

## Load the tuples with a standalone `SetEngine`

A `SetEngine` opened on a store id that has no saved schema yet writes tuples straight
into the tuple table. It checks each tuple against the schema, as a `Store` would, but it writes no
tuple-log rows and **never commits**: you commit once, at the end.

`SetEngine.add_tuple` takes the six-part form only: subject predicate (`"..."` for a plain
subject), subject type, subject name, relation, object type, object name.

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store
from zanzibar.setengine import SetEngine

SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user]
type doc
  relations
    define viewer: [user, group#member]
"""

engine = create_engine("sqlite:///app.db")
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    loader = SetEngine(session, "my-app", SCHEMA)
    for i in range(1000):
        loader.add_tuple("...", "user", f"u{i}", "member", "group", f"team{i % 10}")
    loader.add_tuple("member", "group", "team1", "viewer", "doc", "handbook")
    session.commit()
```

The second write grants `viewer` on `doc:handbook` to the userset `group:team1#member`, so
its members can view the doc.

Import `Store` (or `zanzibar.store`) before `SQLModel.metadata.create_all`, as above.
`create_all` creates only the tables of the modules imported so far, and importing
`zanzibar.setengine` alone does not create the tables a `Store` needs; `Store.adopt`
would then raise {py:exc}`zanzibar.TablesNotCreated`.

A tuple the schema does not allow raises {py:exc}`zanzibar.AdmissionRejected` from
`add_tuple`, before anything is staged for it. The engine also holds every tuple of the
store in memory while it is open.

## Adopt the store

{py:meth}`zanzibar.Store.adopt` saves the schema, builds the graph index from the stored
tuples, and opens the `Store`. The schema and the index commit together. It returns the
open store and a {py:class}`zanzibar.store.BuildReport`:

```python
session = Session(engine)
store, report = Store.adopt(session, "my-app", schema=SCHEMA)

print(report.constructor)  # -> 'bulk'
print(store.check("user:u1", "viewer", "doc:handbook"))  # -> True
print(store.check("user:u2", "viewer", "doc:handbook"))  # -> False
```

`report.constructor` names the build that ran: `"bulk"` (the default, one in-memory pass
and bulk inserts) or `"incremental"` (with `bulk=False`, the tuples replayed one at a
time). The two produce the same index. `Store.adopt` also takes `sync`, `paranoia` and
`ops`, and passes them to the `Store` it opens.

From now on, write through the `Store`. The loaded tuples have no tuple-log rows, so the
store's freshness tokens start after them:

```python
print(store.watermark())  # -> 0
token = store.add_tuple("user:u2", "viewer", "doc:handbook")
print(store.check("user:u2", "viewer", "doc:handbook", at_least=token))  # -> True
```

Leave `schema=` out when the store already has a saved schema. A schema that differs from
the saved one raises {py:exc}`zanzibar.SchemaMismatch`, and a store id with neither raises
{py:exc}`zanzibar.StoreNotFound`.

## Why not just open a `Store` on it?

A `Store` that opens a store id for the first time starts its index empty and fills it
from the tuple log. Tuples written by a standalone `SetEngine` are not in the log, so
the index would never see them. The `Store` refuses instead, with
{py:exc}`zanzibar.UnloggedTuplesPresent`, and writes nothing:

```python
from zanzibar import UnloggedTuplesPresent

with Session(engine) as session:
    loader = SetEngine(session, "legacy", SCHEMA)
    loader.add_tuple("...", "user", "zoe", "viewer", "doc", "old-report")
    session.commit()

try:
    Store(Session(engine), "legacy", schema=SCHEMA)
except UnloggedTuplesPresent as exc:
    print(type(exc).__name__)  # -> 'UnloggedTuplesPresent'

legacy, _ = Store.adopt(Session(engine), "legacy", schema=SCHEMA)
print(legacy.check("user:zoe", "viewer", "doc:old-report"))  # -> True
```

## Adopt a store only once

Once a store has an index, open it with `Store(session, store_id)`. Adopting it again
raises {py:exc}`zanzibar.IndexExists` and commits nothing:

```python
from zanzibar import IndexExists

try:
    Store.adopt(Session(engine), "my-app")
except IndexExists as exc:
    print("open it with Store(session, 'my-app')" in str(exc))  # -> True

again = Store(Session(engine), "my-app")
print(again.check("user:u2", "viewer", "doc:handbook"))  # -> True
```

`Store.adopt` also refuses, committing nothing, if a write to the store commits while the
index is being built (a `RuntimeError` saying "concurrent writes"; retry when the store is
quiet), and on any of the checks a `Store` makes when it opens: the isolation level, the
tables, the session having no pending changes.

## Keep one write path per store id

After adoption the `Store` owns the store id, and the tuple log is the only way in. A
`SetEngine` on that id can still read it (leave the schema out and it loads the saved
one), but its writes raise {py:exc}`zanzibar.UnloggedWriteRefused`:

```python
from zanzibar import UnloggedWriteRefused

with Session(engine) as session:
    reader = SetEngine(session, "my-app")
    print(reader.check("...", "user", "u1", "viewer", "doc", "handbook"))  # -> True
    try:
        reader.add_tuple("...", "user", "u3", "viewer", "doc", "handbook")
    except UnloggedWriteRefused as exc:
        print(type(exc).__name__)  # -> 'UnloggedWriteRefused'
```

A write that bypassed the log would be invisible to the index and to every freshness
token, which is why it is refused. Opening such a `SetEngine` with a schema other than the
store's raises {py:exc}`zanzibar.SchemaMismatch`.

## Do the steps by hand

`Store.adopt` is three public steps in one call. To run them yourself: save the schema
with {py:func}`zanzibar.store.save_schema` and commit, build the index with
{py:func}`zanzibar.store.build_index` (it commits), then open the `Store` without
`schema=`. Load every tuple **before** `save_schema`: once the saved schema is committed, the
`SetEngine`'s writes on that store id raise `UnloggedWriteRefused`.

```python
from zanzibar.store import build_index, save_schema

with Session(engine) as session:
    loader = SetEngine(session, "by-hand", SCHEMA)
    loader.add_tuple("...", "user", "yan", "viewer", "doc", "notes")
    session.commit()

    save_schema(session, "by-hand", SCHEMA)
    session.commit()
    build_index(session, "by-hand")

by_hand = Store(Session(engine), "by-hand")
print(by_hand.check("user:yan", "viewer", "doc:notes"))  # -> True
```

`save_schema` takes the DSL text only; `Store.adopt` also accepts an OpenFGA JSON model.
`build_index` on a store that already has an index raises `IndexExists`. To throw an
existing index away and build it again from the tuples, use
{py:func}`zanzibar.store.rebuild_index`; see [Recover a stalled index](stall-recovery.md).

## Or load through a `Store` instead

If you would rather every tuple be in the tuple log from the start, write them through a
`Store`. Each `add_tuple` is then its own transaction. With `sync=False` each write only
appends to the log, and one `catch_up()` call at the end applies them all to the index;
see [Use async mode and freshness tokens](async-tokens.md).

## See also

- [Change a schema](change-schema.md): schemas are fixed per store, so a new schema means
  copying tuples into a new store id.
- [Use the backends directly](backends-direct.md) for more on the standalone `SetEngine`.
- {py:meth}`zanzibar.Store.adopt`, {py:func}`zanzibar.store.build_index` and
  {py:class}`zanzibar.store.BuildReport` in the [API reference](../reference/api/store.md).
