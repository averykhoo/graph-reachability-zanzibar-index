# zanzibar-index

Zanzibar-style relationship-based access control (ReBAC) for Python, on top of SQLModel.
Schemas are written in the [OpenFGA](https://openfga.dev) modelling DSL, including the
`and` / `but not` operators. The package is not affiliated with Google or OpenFGA.

Two evaluation backends give the **same answers** with **opposite cost models**:

* `zanzibar.setengine` stores only the raw tuples and computes memberships on the fly
  with bitmap algebra (roaring bitmaps). Writes are cheap, reads do the work.
* `zanzibar.graphindex` materializes the transitive closure as reference-counted edges,
  so `check` is a single indexed lookup. Writes do the work, reads are cheap.

`zanzibar.connectedstore` composes them: an append-only tuple log is the source of truth,
the graph index is a materialized view over it, and reads fall back to the set engine
when the index is behind.

## Status: alpha, research code, no support promised

This is a personal research project. It is tested heavily: a differential suite checks
both backends against an independent reference oracle, there is property-based fuzzing,
and the core algorithms have machine-checked Lean proofs. It has **never run in
production**, there is **no performance target**, and the API may change between 0.x
releases. Issues and pull requests are welcome, but answers are best-effort.

## Install

```
pip install zanzibar-index              # SQLite
pip install "zanzibar-index[postgres]"  # adds psycopg2-binary for PostgreSQL
```

Python 3.13 or later. The import name is `zanzibar`.

## Quickstart

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar.connectedstore import ConnectedStore

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
SQLModel.metadata.create_all(engine)   # creates the zanzibar_* tables (see below)

with Session(engine) as session:
    store = ConnectedStore(session, "my-app", schema=SCHEMA)
    # add_tuple(subject_predicate, subject_type, subject_name, relation, object_type, object_name)
    store.add_tuple("...", "user", "alice", "member", "group", "eng")      # "..." = the bare user
    store.add_tuple("member", "group", "eng", "viewer", "doc", "d1")       # group#member is a viewer
    store.check("...", "user", "alice", "viewer", "doc", "d1")             # True

    store.add_tuple("...", "user", "alice", "banned", "doc", "d1")
    store.check("...", "user", "alice", "viewer", "doc", "d1")             # False
```

Each write commits and returns a log id. Pass it back as `check(..., at_least=token)` to
read your own writes when the index is maintained asynchronously (`sync=False`).
Reopening a store with `ConnectedStore(session, "my-app")` reads its persisted schema;
a store's schema is write-once.

## Things to know before you use it

* **Tables.** The library declares its tables on SQLModel's default metadata, all named
  `zanzibar_*`, so `SQLModel.metadata.create_all(engine)` creates them next to your own.
  A table of yours that reuses one of those names is a loud `InvalidRequestError`,
  whichever is declared first; the two are never silently merged.
* **Databases.** SQLite and PostgreSQL only. On PostgreSQL the session must use
  `READ COMMITTED`; any other isolation level is refused at construction.
* **Runtime checks.** `ConnectedStore(..., paranoia="residue")` or the
  `ZANZIBAR_PARANOIA=residue` environment variable turns on a cheap runtime corruption
  detector for the index. It is off by default and recommended for anything
  security-sensitive.
* **Schema shapes.** Some valid OpenFGA shapes are refused with an explanation of what to
  write instead: for example, a `from` tupleset must be a direct relation. Wildcard
  usersets (`[group:*#member]`) and object wildcards go beyond OpenFGA. They work, but
  they are outside the proved fragment and emit `UnprovenExtensionWarning`.
* **Write cap.** A single write that would add more than `ZANZIBAR_MAX_CLOSURE_FANOUT`
  closure edges (default 100,000; `0` disables) is refused with `ClosureFanoutExceeded`.
  The write then lands in neither backend.
* **Public API.** Each subpackage's `__all__` is the public surface. Underscore-prefixed
  names that happen to be re-exported are internal.

## Documentation

Design docs, the correctness argument and the Lean proofs live in the repository:
<https://github.com/averykhoo/graph-reachability-zanzibar-index>. Start at
[`docs/architecture/overview.md`](https://github.com/averykhoo/graph-reachability-zanzibar-index/blob/master/docs/architecture/overview.md).

## License

Apache-2.0. See `LICENSE`.
