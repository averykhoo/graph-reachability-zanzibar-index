# Prune the change outbox

Every write that changes the graph index adds rows to the `zanzibar_delta_outbox` table,
one for each pair of things whose connection appeared or disappeared. The library never
deletes them. This guide shows how to delete the ones that are no longer needed, so that
the table stops growing.

Nothing calls this for you. Run it yourself from time to time, for example from a
scheduled job.

## Prune a store's outbox

Use {py:func}`zanzibar.graphindex.prune_outbox` with the store's current outbox position,
{py:func}`zanzibar.graphindex.outbox_watermark`, in a session of its own, and commit:

```python
from sqlmodel import SQLModel, Session, create_engine, text
from zanzibar import Store
from zanzibar.graphindex import outbox_watermark, prune_outbox

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

engine = create_engine("sqlite:///perms.db")
SQLModel.metadata.create_all(engine)

store = Store(Session(engine), "my-app", schema=SCHEMA)
store.add_tuple("user:alice", "member", "group:eng")
store.add_tuple("group:eng#member", "viewer", "doc:roadmap")
store.add_tuple("user:bob", "member", "group:eng")

def outbox_rows(session):
    return session.exec(text(
        "SELECT count(*) FROM zanzibar_delta_outbox WHERE store_id = 'my-app'")).one()[0]

with Session(engine) as session:
    print(outbox_rows(session))  # -> 5
    removed = prune_outbox(session, "my-app", outbox_watermark(session, "my-app"))
    session.commit()
    print(removed)  # -> 4
    print(outbox_rows(session))  # -> 1
```

`prune_outbox` deletes the store's rows at or below the position you pass, and returns how
many it deleted. It does not commit, so commit the session yourself. It always keeps the
newest row, which is why one row is left: that row keeps the outbox's ids increasing, so
`outbox_watermark` returns the same value before and after a prune.

The store carries on as before:

```python
store.add_tuple("user:carol", "member", "group:eng")
store.remove_tuple("user:bob", "member", "group:eng")
print(store.check("user:carol", "viewer", "doc:roadmap"))  # -> True
print(store.check("user:bob", "viewer", "doc:roadmap"))  # -> False
```

Pruning is per store id: rows of other stores in the same database are not touched. A
position of `0` deletes nothing, and a negative one raises {py:exc}`ValueError`.

## Choose the position

Pass the lowest position that anything still reading the outbox needs. Rows above it are
never deleted, and a row that a reader still needs must not be deleted: the change it
records would be lost, and the `and` / `but not` relations that depend on it would stay
wrong.

For a `Store`, the position read after its last commit is always safe: the library reads
outbox rows only inside the transaction that wrote them (the `and` / `but not` update, and
the `"full"` / `"fixpoint"` runtime checks), so a committed row is never needed again. This
holds for `sync=False` too. If you drive {py:class}`zanzibar.graphindex.DeltaProcessor`
yourself and hold a position across transactions, pass the lowest position you still hold.

The prune takes no store lock: it only deletes rows that no reader needs any more. It is
still a write, so run it in its own transaction, not inside a store's session.

## See also

- [Database tables](../reference/tables.md): what each table holds and how it grows.
- [Limits and costs](../explanation/limits.md): what else grows with every write.
- [Turn on runtime checks in production](runtime-checks.md).
