# zanzibar-index

Relationship-based permissions for Python applications, in the style of Google's Zanzibar,
stored in SQLite or PostgreSQL.

You describe your permission model in a schema, written in a subset of the
[OpenFGA](https://openfga.dev) modelling language: users, groups, folders, documents, and
how a relationship on one implies a relationship on another. Your application then
records relationships ("alice is a member of eng", "eng can view the projects folder") and
asks questions about them ("can alice view this document?", "who can view it?").

The package is called `zanzibar-index` on PyPI and is imported as `zanzibar`. It is not
affiliated with Google or OpenFGA.

It is a library, not a service: its tables live in your own SQLite or PostgreSQL database,
next to your application's, and you call it in-process, so there is no server to run and no
network API ([what it is, and is not](explanation/zanzibar-intro.md#what-this-library-is-and-is-not)).
Inside, two backends give the same answers with opposite cost models: the set engine stores
only the raw tuples and computes each answer when you ask, while the graph index stores every
implied relationship ahead of time, so a check is a few indexed lookups whatever the data
and the work moves to writes ([the two backends](explanation/two-backends.md)). An
application does not pick one: it uses a `Store`, which keeps both in step, and the choice
it actually makes is whether writes update the index at once (sync, the default) or later
([async mode](how-to/async-tokens.md)). The exception is a load where writes dominate:
there the set engine on its own is the better trade
([when not to use this library](explanation/limits.md#when-not-to-use-this-library)).

```{warning}
This is alpha research software: a personal research project, with no support promised.
It is heavily tested, but it has never run in production, it has no performance target,
and its API may change in any 0.x release, including a patch release. Issues and pull
requests are welcome; answers are best-effort.
```

## Install

```text
pip install zanzibar-index
```

It needs Python 3.13 or later. For PostgreSQL, install `"zanzibar-index[postgres]"`
instead, which adds the database driver.

Coming from a 0.0.x release? Version 0.1 renames the main class and changes some answers;
see [Upgrade from 0.0.x to 0.1](how-to/upgrade-0.1.md).

## A first look

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

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

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
session = Session(engine)

store = Store(session, "my-app", schema=SCHEMA)
store.add_tuple("user:alice", "member", "group:eng")
store.add_tuple("group:eng#member", "viewer", "doc:roadmap")

print(store.check("user:alice", "viewer", "doc:roadmap"))  # -> True
print(store.check("user:bob", "viewer", "doc:roadmap"))  # -> False
```

Alice can view the roadmap because she is a member of `eng`, and every member of `eng` can
view it. Bob is in no group, so he cannot.

## Where to go next

This documentation has four parts. Each answers a different kind of question.

[Tutorials](tutorials/index.md)
: Start here if you are new. Short lessons that you follow from start to finish, typing
  the code as you go.

[How-to guides](how-to/index.md)
: Recipes for a specific job, such as running on PostgreSQL, porting an OpenFGA model, or
  finding out who can access an object.

[Reference](reference/index.md)
: Exact descriptions of the Python API, the schema language, the exceptions and the
  configuration options.

[Explanation](explanation/index.md)
: Background and design: what Zanzibar-style permissions are, how the library answers a
  question, and how far its answers can be trusted.

Before a first deploy, read [Use async mode and freshness tokens](how-to/async-tokens.md),
[Turn on runtime checks in production](how-to/runtime-checks.md),
[Prune the change outbox](how-to/prune-outbox.md) and [Handle errors](how-to/errors.md).

## License

Apache-2.0. The license text is the `LICENSE` file in the
[source repository](https://github.com/averykhoo/graph-reachability-zanzibar-index).

```{toctree}
:maxdepth: 2
:hidden:

tutorials/index
how-to/index
reference/index
explanation/index
```
