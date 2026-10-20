# Supported environments

## Python

Python **3.13 or later** (`requires-python = ">=3.13"`). 3.13 is the version the library is
tested on. The package is pure Python and declares no operating-system restriction.

The distribution is `zanzibar-index`; the import name is `zanzibar`.

## Dependencies

| package | required version | why |
| --- | --- | --- |
| `sqlmodel` | `>=0.0.39` | the table models and sessions; brings SQLAlchemy |
| `pyroaring` | `>=1.1.0` | the compressed bitmaps behind the default set representation |

### Extras

| extra | adds | for |
| --- | --- | --- |
| `postgres` | `psycopg2-binary` | connecting to PostgreSQL |
| `test` | `pytest`, `hypothesis` | running the library's test suite, in a source checkout of the repository (the tests are not in the published package) |
| `docs` | `sphinx>=8,<9`, `myst-parser>=4,<5`, `furo` | building this documentation, in a source checkout of the repository. New in 0.1.0 (unreleased): 0.0.5 has no `docs` extra |

```text
pip install zanzibar-index              # SQLite
pip install "zanzibar-index[postgres]"  # adds the PostgreSQL driver
```

## Databases

**SQLite and PostgreSQL only.** No other database is supported, MySQL included.

### PostgreSQL

- The session's isolation level must be **`READ COMMITTED`**, PostgreSQL's default. Any
  other level, `SERIALIZABLE` and `REPEATABLE READ` included, is refused when the store
  opens, with {py:exc}`zanzibar.UnsafeIsolationLevel`: under a level that pins a read
  snapshot, a committed write can stay invisible to the index's catch-up, and a freshness
  token would then certify a stale answer. If you set a level, set this one:
  `create_engine(url, isolation_level="READ COMMITTED")`.
- Writers to one store are serialised by a row lock (`SELECT ... FOR UPDATE`), so several
  processes or machines may open the same store id.
- The `postgres` extra installs `psycopg2`, so the URL starts `postgresql+psycopg2://` (or
  `postgresql://`, SQLAlchemy's default for that driver).

See [Run on PostgreSQL](../how-to/postgresql.md).

### SQLite

- There is no isolation level to check; SQLite serialises writers itself. A concurrent
  writer can get `database is locked` and must retry. The store raises the connection's
  busy timeout to at least 10 seconds before it takes its write lock, so a waiting writer
  first waits that long.
- The connection must **not** be in autocommit mode, because the store's write lock would
  be released the moment it was taken. Opening a store on such a connection raises
  {py:exc}`zanzibar.WriteLockUnsafe`, whose message names the fix. The Python `sqlite3`
  default, which is what `create_engine("sqlite://...")` gives you, is fine.
- A file whose tables were created by a 0.0.x release is refused with
  {py:exc}`zanzibar.TablesOutdated`; see [Database tables](tables.md).

```python
from sqlmodel import SQLModel, Session, create_engine
import zanzibar
import zanzibar.store  # registers the zanzibar_* tables before create_all

SCHEMA = "type user\ntype doc\n  relations\n    define viewer: [user]\n"

ok = create_engine("sqlite://")                     # the default: fine
SQLModel.metadata.create_all(ok)
with Session(ok) as session:
    store = zanzibar.Store(session, "env-demo", schema=SCHEMA)
    store.add_tuple("user:alice", "viewer", "doc:1")
    print(store.check("user:alice", "viewer", "doc:1"))  # -> True

autocommit = create_engine("sqlite://", connect_args={"isolation_level": None})
SQLModel.metadata.create_all(autocommit)
with Session(autocommit) as session:
    try:
        zanzibar.Store(session, "env-demo", schema=SCHEMA)
    except zanzibar.WriteLockUnsafe:
        refused = True
print(refused)  # -> True
```

## Threads and processes

- Give each {py:class}`~zanzibar.Store` its own `Session`, and use one `Session` per thread.
  Never share a `Store` between threads.
- Each `Store` keeps the set engine's state in memory, rebuilt from the stored tuples when
  it opens. Several instances, in threads, processes or on other machines, may serve the
  same store id.

## Status and license

| | |
| --- | --- |
| development status | `Development Status :: 3 - Alpha`; what that means for you is in [the warning on the home page](../index.md) |
| license | Apache-2.0 (`license = "Apache-2.0"`, text in the repository's `LICENSE` file) |
