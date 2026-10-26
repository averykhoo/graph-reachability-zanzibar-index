# zanzibar-index

Zanzibar-style relationship-based access control (ReBAC) for Python, stored in SQLite or
PostgreSQL through SQLModel. You write your permission model in a subset of the
[OpenFGA](https://openfga.dev) modelling language (schema 1.1, including `and` and
`but not`), record relationships such as "alice is a member of eng", and ask questions such
as "can alice view this document?" and "who can view it?". The package is not affiliated
with Google or OpenFGA.

Two backends give the same answers with opposite cost models. The set engine stores only
the raw tuples and computes each answer when you ask; the graph index stores every implied
relationship ahead of time, so a check is a few indexed lookups and the work moves to writes.

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
  [configuration](https://averykhoo.github.io/graph-reachability-zanzibar-index/reference/configuration.html),
  [database tables](https://averykhoo.github.io/graph-reachability-zanzibar-index/reference/tables.html),
  and the [release notes](https://averykhoo.github.io/graph-reachability-zanzibar-index/reference/changelog.html).
* [Explanation](https://averykhoo.github.io/graph-reachability-zanzibar-index/explanation/index.html):
  [the two backends](https://averykhoo.github.io/graph-reachability-zanzibar-index/explanation/two-backends.html),
  [differences from OpenFGA](https://averykhoo.github.io/graph-reachability-zanzibar-index/explanation/semantics-vs-openfga.html),
  [limits and costs](https://averykhoo.github.io/graph-reachability-zanzibar-index/explanation/limits.html)
  and [how correctness is checked](https://averykhoo.github.io/graph-reachability-zanzibar-index/explanation/assurance.html).

Before a first deploy, read the guides to [async mode and freshness tokens](https://averykhoo.github.io/graph-reachability-zanzibar-index/how-to/async-tokens.html),
[runtime checks in production](https://averykhoo.github.io/graph-reachability-zanzibar-index/how-to/runtime-checks.html),
[pruning the change outbox](https://averykhoo.github.io/graph-reachability-zanzibar-index/how-to/prune-outbox.html), and the
[exceptions reference](https://averykhoo.github.io/graph-reachability-zanzibar-index/reference/exceptions.html).

## License

Apache-2.0. See `LICENSE` in the
[source repository](https://github.com/averykhoo/graph-reachability-zanzibar-index).
