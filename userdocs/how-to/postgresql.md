# Run on PostgreSQL

SQLite is fine for development, tests and a single process. For a server, and for several
processes or machines sharing one permission store, use PostgreSQL. These are the only two
supported databases.

The code on this page needs a running PostgreSQL server, so the documentation build does
not run it. Replace the connection URL with your own.

## Install the driver

```text
pip install "zanzibar-index[postgres]"
```

The `postgres` extra installs `psycopg2-binary`.

## Connect at READ COMMITTED

The store must run at the `READ COMMITTED` isolation level, which is PostgreSQL's default.
If you leave the isolation level alone, there is nothing to do. If you set one, set that
one:

```python
# not run: needs PostgreSQL
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

URL = "postgresql+psycopg2://app:secret@db.example.com/permissions"
engine = create_engine(URL, isolation_level="READ COMMITTED")
```

Any other level is refused with {py:exc}`zanzibar.UnsafeIsolationLevel` as soon as you open
a store, before it reads or writes anything. That includes `REPEATABLE READ` and
`SERIALIZABLE`: both keep one snapshot for a whole transaction, so the store could miss a
write that another connection committed, including a revocation, and go on answering as if
it had not happened. The check asks the server for the level the connection actually runs
at, so a database whose default level was changed to something else is refused too.

```python
# not run: needs PostgreSQL
from zanzibar import UnsafeIsolationLevel

strict = create_engine(URL, isolation_level="REPEATABLE READ")
try:
    Store(Session(strict), "my-app")
except UnsafeIsolationLevel as error:
    print(error)    # says to use isolation_level="READ COMMITTED"
```

## Create the tables

The library's tables are declared on SQLModel's default metadata, so the same
`create_all` call that creates your own SQLModel tables creates them too. Import the
library first, so that its tables are registered, then call it once, for example in a
deployment step:

```python
# not run: needs PostgreSQL
import zanzibar.store              # registers the zanzibar_* tables
SQLModel.metadata.create_all(engine)
```

`create_all` creates only the tables that are missing. Every table, constraint and index
the library creates is named `zanzibar_*` or `ix_zanzibar_*`. If one of your own tables
uses one of those names, SQLAlchemy raises an error rather than merging the two; rename
your table. A store opened before the tables exist raises
{py:exc}`zanzibar.TablesNotCreated`, which lists the missing tables.

Then create the store once, with its schema, as on SQLite:

```python
# not run: needs PostgreSQL
SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
"""

with Session(engine) as session:
    Store(session, "my-app", schema=SCHEMA)
```

## One session per thread

A `Store` commits and rolls back its session itself, and is not safe to share between
threads. So:

- **Give each thread its own `Session` and its own `Store`.** The engine can be shared.
- **Give each `Store` a session of its own**, not one your application also uses for its
  own rows. A `Store` refuses a session that has unsaved changes of yours.
- **Keep a `Store` open** for as long as the thread lives, rather than opening one per
  request. Opening a store loads every tuple of the store into memory, which takes time
  in proportion to the size of the store.
- **Expect a long-lived `Store`'s connection to sit "idle in transaction".** A read
  (`check`, `lookup`, `expand`) does not commit, so between reads the store's session
  keeps a transaction open, and `pg_stat_activity` shows the connection as
  `idle in transaction`. `refresh()` does not change that: it reads again, which opens a
  new transaction. So do not set `idle_in_transaction_session_timeout` for the role the
  store connects as, or set it longer than the longest gap between reads. If the server
  does close the connection, the next call raises a driver error
  (`sqlalchemy.exc.OperationalError`, then `PendingRollbackError`); call `refresh()` on
  that store, which rolls back and reconnects, and retry.

One way to do that is a store per thread, created on first use:

```python
# not run: needs PostgreSQL
import threading

_local = threading.local()

def get_store() -> Store:
    store = getattr(_local, "store", None)
    if store is None:
        store = Store(Session(engine), "my-app")
        _local.store = store
    return store

def grant(user: str, doc: str) -> int:
    return get_store().add_tuple(f"user:{user}", "viewer", f"doc:{doc}")

threads = [threading.Thread(target=grant, args=(f"u{i}", "1")) for i in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

## Run several instances on one store

Any number of threads, processes or machines can open the same store id at once. Each one
is an *instance* of the store.

- **Writes to one store are serialised.** Every write takes a row lock on the store, so
  writes to the same store run one at a time, across all instances, while writes to
  different stores do not wait for each other. A write that adds many index rows holds
  that lock for longer; see [Cap write fan-out](fanout-cap.md).
- **Reads see other instances' writes.** With the default `sync=True`, each write updates
  the graph index in the same transaction, and at `READ COMMITTED` every query sees the
  latest committed data. So another instance's `check` reflects a write as soon as it has
  committed.
- **To read a write you have just made through another instance, pass its token.** Every
  write returns a freshness token. Pass it to the other instance's `check` as
  `at_least=`, and the answer is guaranteed to reflect that write:

```python
# not run: needs PostgreSQL
with Session(engine) as s1, Session(engine) as s2:
    writer = Store(s1, "my-app")
    reader = Store(s2, "my-app")

    token = writer.add_tuple("user:carol", "viewer", "doc:1")
    print(reader.check("user:carol", "viewer", "doc:1", at_least=token))   # True
```

Hand the token to the other instance however your application talks to it: in a response
header, a message, or a column next to your own data. It is an `int`.

Each instance also holds an in-memory copy of the tuples, which it brings up to date by
itself when it needs to (for a write, or for a `check` whose token the graph index has not
reached yet). {py:meth}`zanzibar.Store.refresh` starts a fresh transaction and reloads that
copy from the database. Call it when an error tells you to
({py:exc}`zanzibar.StaleRead`, {py:exc}`zanzibar.WatermarkGap`), not on every request:
like opening a store, it reads every tuple.

If you write through the lower-level `zanzibar.store.TupleSource` instead of a `Store`,
its `catch_up_evaluator()` method applies the log rows other instances have written since
its last read to its in-memory copy, and `refresh_evaluator()` reloads it from scratch.
A `Store` does both for you.

## Async instances

With `Store(session, "my-app", sync=False)`, a write only goes into the tuple log, and the
graph index catches up when something calls `catch_up()`. No worker ships with the
library: run one yourself, in its own process with its own session. While the index is
behind, an untokened read can still show a revoked grant as allowed. See
[Use async mode and freshness tokens](async-tokens.md) before you use it.

## Related

- [Handle errors](errors.md), for {py:exc}`zanzibar.UnsafeIsolationLevel` and the
  freshness errors.
- [Turn on runtime checks in production](runtime-checks.md).
