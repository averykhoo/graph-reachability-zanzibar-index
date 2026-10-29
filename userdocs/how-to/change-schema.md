# Change a schema

A store's schema is saved when the store is created and never changes. Opening the store
with a different schema raises {py:exc}`zanzibar.SchemaMismatch`; the same schema
reformatted (different blank lines or spacing) is not a change and opens normally. To
change the schema,
create a new store with the new schema, copy the tuples into it, and point your
application at the new store id.

## 1. Create the new store

```python
from sqlmodel import SQLModel, Session, create_engine, select
from zanzibar import SchemaMismatch, Store
from zanzibar.setengine import RelationTuple

OLD_SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define reader: [user]
"""

NEW_SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define blocked: [user]
    define viewer: [user] but not blocked
"""

engine = create_engine("sqlite:///change-schema.db")
SQLModel.metadata.create_all(engine)

# The store as it exists today.
old = Store(Session(engine), "app-v1", schema=OLD_SCHEMA)
old.add_tuple("user:alice", "reader", "doc:1")
old.add_tuple("user:bob", "reader", "doc:1")
old.add_tuple("user:bob", "reader", "doc:2")
old.remove_tuple("user:bob", "reader", "doc:1")

mismatch = False
try:
    Store(Session(engine), "app-v1", schema=NEW_SCHEMA)
except SchemaMismatch:
    mismatch = True
print(mismatch)  # -> True

new = Store(Session(engine), "app-v2", schema=NEW_SCHEMA)
```

Use a new store id for the new schema. The old store and its tuple log stay in the
database; the library has no call that deletes a store, but you can delete its rows
yourself ([Deleting a store](../reference/tables.md#deleting-a-store)).

If the old store was created with `object_wildcard_shapes`, pass the same argument
(updated for any renames) when you create the new store. Without it, copied tuples whose
object name is `*` are refused.

## 2. Copy the tuples

A store's current tuples are the {py:class}`zanzibar.setengine.RelationTuple` rows with
its `store_id`; removed tuples are not among them. Read them, translate each one to the
new schema, and write it through the new store, so every tuple is checked against the
new schema:

```python
from zanzibar import AdmissionRejected

RENAMED = {"reader": "viewer"}

with Session(engine) as session:
    rows = session.exec(
        select(RelationTuple).where(RelationTuple.store_id == "app-v1")
    ).all()

refused = []
for row in rows:
    relation = RENAMED.get(row.relation, row.relation)
    try:
        new.add_tuple(row.subject_predicate, row.subject_type, row.subject_name,
                      relation, row.object_type, row.object_name)
    except AdmissionRejected as exc:
        refused.append((row, str(exc)))

print(len(rows))  # -> 2
print(refused)  # -> []
```

The six-part form of {py:meth}`zanzibar.Store.add_tuple` takes the row's columns as
they are, so usersets (`subject_predicate` other than `"..."`) and `user:*` copy
without string handling. A tuple the new schema does not admit is refused with
{py:exc}`zanzibar.AdmissionRejected` and nothing else is written for it; decide what
each refused tuple should become.

Reading the rows needs no `Store`, so it also works for an old store that no longer
opens because its stored schema uses a shape this version refuses
({py:exc}`zanzibar.PersistedSchemaRefused`).

For a large store, writing one tuple per commit is slow. See
[bulk-load or adopt an existing store](bulk-load-adopt.md) for building the index in one
pass.

## 3. Check, then switch

Compare answers for the questions your application asks, then change the store id it
opens:

```python
print(new.check("user:alice", "viewer", "doc:1"))  # -> True
print(new.check("user:bob", "viewer", "doc:1"))  # -> False
print(new.check("user:bob", "viewer", "doc:2"))  # -> True
```

Writes made to the old store after you read its rows are not in the new one, so stop
writing to the old store before you read its rows, and keep it stopped until the switch.
