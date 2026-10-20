# zanzibar-index

Relationship-based permissions for Python applications, in the style of Google's Zanzibar,
stored in SQLite or PostgreSQL.

You describe your permission model in a schema, written in a subset of the
[OpenFGA](https://openfga.dev) modelling language, plus a few
[extensions](reference/schema-language.md#extensions-beyond-openfga): users, groups, folders, documents, and
how a relationship on one implies a relationship on another. Your application then
records relationships ("alice is a member of eng", "eng can view the projects folder") and
asks questions about them ("can alice view this document?", "who can view it?").

The package is called `zanzibar-index` on PyPI and is imported as `zanzibar`. It is not
affiliated with Google or OpenFGA.

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

:::{note}
These pages follow the source code on the main branch. While it has changes that are not
on PyPI yet, a banner at the top of every page says so, and the examples may not run on the
release that `pip install zanzibar-index` gives you. In that case install from source
instead:

```text
pip install git+https://github.com/averykhoo/graph-reachability-zanzibar-index
```

In particular, version 0.1 renames the main class: on 0.0.x releases there is no
`zanzibar.Store`. See [Upgrade from 0.0.x to 0.1](how-to/upgrade-0.1.md).
:::

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

## License

Apache-2.0. The license text is the `LICENSE` file in the
[source repository](https://github.com/averykhoo/graph-reachability-zanzibar-index).

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

```{toctree}
:maxdepth: 2
:hidden:

tutorials/index
how-to/index
reference/index
explanation/index
```
