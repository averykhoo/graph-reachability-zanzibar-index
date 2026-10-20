# zanzibar-index

Zanzibar-style relationship-based access control (ReBAC) for Python, stored in SQLite or
PostgreSQL through SQLModel. You write your permission model in a subset of the
[OpenFGA](https://openfga.dev) modelling language (schema 1.1, including `and` and
`but not`), record relationships such as "alice is a member of eng", and ask questions such
as "can alice view this document?" and "who can view it?". The package is not affiliated
with Google or OpenFGA.

Two backends give the same answers with opposite cost models. The set engine stores only
the raw tuples and computes each answer when you ask; the graph index stores every implied
relationship ahead of time, so a check is one indexed lookup and the work moves to writes.

**Status: alpha, research code, no support promised.** It is heavily tested but has never
run in production, it has no performance target, and the API may change in any 0.x release.
Issues and pull requests are welcome; answers are best-effort.

## Install

```
pip install zanzibar-index              # SQLite
pip install "zanzibar-index[postgres]"  # adds psycopg2-binary for PostgreSQL
```

Python 3.13 or later. The import name is `zanzibar`.

## Quickstart

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define banned: [user]
    define viewer: [user, group#member] but not banned
"""

engine = create_engine("sqlite:///perms.db")
SQLModel.metadata.create_all(engine)   # creates the zanzibar_* tables

with Session(engine) as session:
    store = Store(session, "my-app", schema=SCHEMA)
    # add_tuple(user, relation, object), in OpenFGA's "type:name[#relation]" form
    store.add_tuple("user:alice", "member", "group:eng")
    store.add_tuple("user:bob", "member", "group:eng")
    store.add_tuple("group:eng#member", "viewer", "doc:d1")   # every member of eng
    print(store.check("user:alice", "viewer", "doc:d1"))      # True
    print(store.check("user:carol", "viewer", "doc:d1"))      # False

    store.add_tuple("user:bob", "banned", "doc:d1")
    print(store.check("user:bob", "viewer", "doc:d1"))        # False
    print(store.check("user:alice", "viewer", "doc:d1"))      # True
```

Each write commits and returns a freshness token. A store's schema is write-once:
reopening with `Store(session, "my-app")` reads the stored one.

## Documentation

The user documentation is at
<https://averykhoo.github.io/graph-reachability-zanzibar-index/>:

* [Tutorials](https://averykhoo.github.io/graph-reachability-zanzibar-index/tutorials/index.html):
  start with [your first permission check](https://averykhoo.github.io/graph-reachability-zanzibar-index/tutorials/first-check.html).
* [How-to guides](https://averykhoo.github.io/graph-reachability-zanzibar-index/how-to/index.html):
  [find who can access what](https://averykhoo.github.io/graph-reachability-zanzibar-index/how-to/query-access.html),
  [run on PostgreSQL](https://averykhoo.github.io/graph-reachability-zanzibar-index/how-to/postgresql.html),
  [port an OpenFGA model](https://averykhoo.github.io/graph-reachability-zanzibar-index/how-to/port-openfga.html),
  [use async mode and freshness tokens](https://averykhoo.github.io/graph-reachability-zanzibar-index/how-to/async-tokens.html),
  [handle errors](https://averykhoo.github.io/graph-reachability-zanzibar-index/how-to/errors.html),
  [upgrade from 0.0.x](https://averykhoo.github.io/graph-reachability-zanzibar-index/how-to/upgrade-0.1.html).
* [Reference](https://averykhoo.github.io/graph-reachability-zanzibar-index/reference/index.html):
  the Python API, the [schema language](https://averykhoo.github.io/graph-reachability-zanzibar-index/reference/schema-language.html),
  [exceptions](https://averykhoo.github.io/graph-reachability-zanzibar-index/reference/exceptions.html),
  [configuration](https://averykhoo.github.io/graph-reachability-zanzibar-index/reference/configuration.html)
  and [database tables](https://averykhoo.github.io/graph-reachability-zanzibar-index/reference/tables.html).
* [Explanation](https://averykhoo.github.io/graph-reachability-zanzibar-index/explanation/index.html):
  [the two backends](https://averykhoo.github.io/graph-reachability-zanzibar-index/explanation/two-backends.html),
  [differences from OpenFGA](https://averykhoo.github.io/graph-reachability-zanzibar-index/explanation/semantics-vs-openfga.html),
  [limits and costs](https://averykhoo.github.io/graph-reachability-zanzibar-index/explanation/limits.html)
  and [how correctness is checked](https://averykhoo.github.io/graph-reachability-zanzibar-index/explanation/assurance.html).

The rest of this page is a summary of the parts most often needed before a first deploy.
The documentation site is the full version of each.

## Async mode in brief

Every write returns a freshness token, an `int` that only grows within a store;
`store.watermark()` is the newest one. Adding a tuple that is
already present changes nothing and returns the current `store.watermark()`.
`check(..., at_least=token)` answers as of that write or later. A token means something
only to the store whose write returned it: another store's token is refused only when it
is newer than this store's writes, and is otherwise accepted without error and guarantees
nothing.

A `Store` is synchronous by default. With `Store(session, "my-app", sync=False)` a write
only appends to the log, and the graph index catches up when something calls
`store.catch_up()`. No background worker ships with the library:

```
import time
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session
from zanzibar import Store, ZanzibarError

with Session(engine) as session:
    worker = Store(session, "my-app", sync=False)
    while True:
        try:
            worker.catch_up()            # applies every committed write
        except (ZanzibarError, SQLAlchemyError):   # a lock timeout is a SQLAlchemy error
            print(worker.stall_error)    # the log row it could not apply, and why
        time.sleep(1.0)
```

While the index is behind (`store.lag()` rows), an untokened `check` can be stale in both
directions: **a revoked grant can still read as allowed**. Pass a token for any decision
that must see a revoke. A token this session cannot see yet raises `StaleRead`: call
`store.refresh()` and retry. When `store.index_stalled` is `True`, see
[Recover a stalled index](https://averykhoo.github.io/graph-reachability-zanzibar-index/how-to/stall-recovery.html).
Lookup results are translated with `store.result_keys(result)` and
`store.excluded_keys(result)`; a revoke is `store.remove_tuple(...)`.

The change outbox grows on every write and is never pruned for you:

```
from zanzibar.graphindex import outbox_watermark, prune_outbox

prune_outbox(session, "my-app", outbox_watermark(session, "my-app"))
session.commit()
```

This form is safe with `paranoia` off (the default); with it on, read `help(prune_outbox)`
first.

## Exceptions

Every exception below imports from the top level and derives from `zanzibar.ZanzibarError`,
keeping the builtin base shown, so `except ZanzibarError` catches all of them.
`InvariantViolation` (an `AssertionError`, raised when the stored index is corrupt) is
deliberately outside it.

| exception | base | raised when |
| --- | --- | --- |
| `AdmissionRejected` | `ValueError` | a write is refused |
| `MalformedTupleString` | `ValueError` | a tuple string does not parse |
| `SchemaError` | `ValueError` | the schema is refused; the message says what to write instead |
| `ShapeNoLongerAccepted` | `ValueError` | a schema shape 0.0.4 and earlier accepted |
| `PersistedSchemaRefused` | `ValueError` | a store's stored schema uses such a shape |
| `CyclicDerivedDependency` | `ValueError` | a relation recurses through `and` / `but not` |
| `SchemaMismatch` | `ValueError` | a store is opened with a different schema |
| `StoreNotFound` | `KeyError` | a store opened without `schema=` does not exist |
| `TablesNotCreated` | `RuntimeError` | `SQLModel.metadata.create_all(engine)` was not run |
| `TablesOutdated` | `RuntimeError` | a SQLite file's tables were created by 0.0.x |
| `StaleLookupIds` | `KeyError` | a lookup result is translated after its ids may have been reused |
| `StaleRead` | `RuntimeError` | a freshness token cannot be satisfied |
| `LookupNotFresh` | `RuntimeError` | a tokened lookup while the index lags |
| `IndexStalled` | `RuntimeError` | an untokened lookup while the index is stalled |
| `ClosureFanoutExceeded` | `ValueError` | a write would add too many index rows |
| `PathCountExceeded` | `ValueError` | a write would overflow a path count |
| `UnloggedWriteRefused` | `RuntimeError` | a standalone `SetEngine` writes to a store a `Store` owns |
| `UnloggedTuplesPresent` | `RuntimeError` | a `Store` opens over tuples a standalone `SetEngine` wrote |
| `IndexExists` | `ValueError` | `build_index` targets an index that already exists |
| `MissingDeltaProcessor` | `ValueError` | the graph index is driven by hand on a boolean schema without its processor |
| `UnsafeIsolationLevel` | `RuntimeError` | a PostgreSQL session is not at `READ COMMITTED` |

## License

Apache-2.0. See `LICENSE` in the
[source repository](https://github.com/averykhoo/graph-reachability-zanzibar-index).
