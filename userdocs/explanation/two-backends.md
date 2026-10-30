# The two backends

Every permission question can be answered in one of two ways: work out the answer when
someone asks, or work it out in advance, every time the data changes, so that asking is
just reading. This library does both. It has two evaluation backends that give the same
answers and spend their effort in opposite places, and a {py:class}`zanzibar.Store` uses
them together. This page explains why.

## Two places to do the work

Take a schema where documents inherit viewers from folders, folders from parent folders,
and groups contain other groups. To answer "can alice view this document?", something has
to follow the chain: from the document to its folder, up the folder tree, to the groups
that were granted access, down through nested groups, until it finds alice or runs out of
paths.

**The set engine** ({py:mod}`zanzibar.setengine`) follows that chain when you ask. It keeps
only the tuples you wrote, held in memory as compressed bitmaps (roaring bitmaps), and
evaluates the schema's rules over them on each query with set operations: union for `or`,
intersection for `and`, difference for `but not`. A write is cheap: it records one more
tuple. A read does the work, and costs more the deeper the nesting and the wider the
fan-out it has to walk.

**The graph index** ({py:mod}`zanzibar.graphindex`) follows the chain when you write. It
stores, for every pair of things connected by at least one path, a row saying so: alice to
`doc:roadmap#viewer`, alice to `group:eng#member`, `group:eng#member` to
`folder:projects#viewer`, and so on. That is the *transitive closure* of the relationship
graph. A check is then a small, fixed number of indexed database lookups, however large
the data and however deep the nesting. A write
does the work: adding one tuple adds a row for every new pair it connects, which can be
many, and removing it takes them away again. [How the graph index works](graph-index.md)
explains how that is kept exact.

Here is the chain from the example further down this page, both ways: alice is in `eng`,
`eng` is in `staff`, `staff` can view `folder:root`, which is the parent of
`folder:projects`, which is the parent of `doc:roadmap`.

```{image} img/backends-work.svg
:class: only-light
:alt: The same chain of six nodes, from user:alice down to doc:roadmap#viewer, twice. The set engine walks all five hops on every check. The graph index stored one row from user:alice to doc:roadmap#viewer when the chain was connected, so a check reads that one row.
```

```{image} img/backends-work-dark.svg
:class: only-dark
:alt: The same chain of six nodes, from user:alice down to doc:roadmap#viewer, twice. The set engine walks all five hops on every check. The graph index stored one row from user:alice to doc:roadmap#viewer when the chain was connected, so a check reads that one row.
```

These are the two ends of one spectrum. A cache in front of the set engine would sit
somewhere in the middle: it remembers some answers and has to forget them when the data
changes. The graph index is the far end, where every answer is remembered and nothing is
ever forgotten by accident, because each write updates exactly the rows it affects. The
set engine is the other end, where nothing is remembered between questions.

| | graph index | set engine |
|---|---|---|
| what it stores | a row for every connected pair, in the database | the tuples, in the database and as bitmaps in memory |
| cost of a write | grows with the number of pairs the write connects or disconnects | small and roughly constant |
| cost of a check | a few indexed lookups, independent of data size and nesting depth | grows with nesting depth and fan-out |
| lookups ("what can alice view?") | read straight from the stored rows | computed on demand |
| `and` / `but not` | maintained by an extra step on each write ([how](boolean-operators.md)) | ordinary set operations on read |
| state on open | nothing to rebuild; the rows are in the database | rebuilt in memory by replaying the store's tuples |

Neither is better in general. Precomputing pays off when reads far outnumber writes and
the graph is deep, which is the usual shape for permissions. It costs space, and the price
of a single write can be large: granting a group access to a folder at the top of a big
tree touches a row for every member and every document below. The library caps how large
one write may be, as described in [Limits and costs](limits.md).

## How a Store combines them

A {py:class}`zanzibar.Store` is built around a different idea from both backends: the
tuples you wrote are the truth, and everything else is derived from them.

- **The tuples and the tuple log are the source of truth.** Every write is recorded in
  two tables: the current set of tuples, and {py:class}`zanzibar.store.TupleLog`, an
  append-only log with one row per write that changes the tuples, never compacted. A
  write returns the id of its log row, which is its *freshness token*. A duplicate add is
  a no-op: it writes no row and returns the current log position.
- **The set engine validates every write.** Before a write is logged, the store's set
  engine checks it against the schema and the current tuples: is the type declared, does
  the relation accept this kind of user, would it create a cycle? A refused write
  ({py:exc}`zanzibar.AdmissionRejected`) changes nothing. The set engine reads any new log
  rows before it validates a write or answers a read, so it is as fresh as the log that
  this database session can see.
- **The graph index is a materialized view of the log.** It applies log rows in order and
  remembers how far it has got. By default (`sync=True`) it applies each write in the same
  transaction as the write itself, so it is never behind. With `sync=False`, a write only
  goes to the log and the set engine, and the index catches up when
  {py:meth}`zanzibar.Store.catch_up` runs. Because the index is derived, it can be thrown
  away and built again from the tuples ({py:func}`zanzibar.store.rebuild_index`), provided
  the stored tuples fit the index's limits; see
  [Recover a stalled index](../how-to/stall-recovery.md).

Reads then go to whichever backend can answer correctly:

- `check` reads the graph index when the index is fresh enough, and otherwise falls back
  to the set engine. "Fresh enough" means: caught up to the token you passed, or not
  stalled when you passed none. An untokened `check` against an index that is merely
  behind reads the index as it is; [Consistency](consistency.md) explains when that
  matters.
- `lookup` and `lookup_reverse` are served by the graph index only. With a token, they
  raise {py:exc}`zanzibar.LookupNotFresh` rather than return a list that misses that
  write. Without a token, they raise {py:exc}`zanzibar.IndexStalled` only when the index
  is stalled, and otherwise read the index as it is, the same as an untokened `check`.
- `expand` is served by the set engine only, so it never waits for the index.

```{image} img/store-composition.svg
:class: only-light
:alt: A write first is validated by the set engine, then appended to the tuple log, which returns its id as the token, then applied to the graph index, in the same transaction when sync or later in catch_up when async. The set engine reads new log rows; the index applies them in order. expand always reads the set engine; check reads the index if it is fresh enough and the set engine otherwise; lookup and lookup_reverse read only the index and raise LookupNotFresh or IndexStalled when it is not fresh.
```

```{image} img/store-composition-dark.svg
:class: only-dark
:alt: A write first is validated by the set engine, then appended to the tuple log, which returns its id as the token, then applied to the graph index, in the same transaction when sync or later in catch_up when async. The set engine reads new log rows; the index applies them in order. expand always reads the set engine; check reads the index if it is fresh enough and the set engine otherwise; lookup and lookup_reverse read only the index and raise LookupNotFresh or IndexStalled when it is not fresh.
```

So in a store, the graph index is what makes reads fast and lookups possible, and the set
engine is what keeps writes honest and lets a read be correct while the index is catching
up.

### Who owns the transaction

Because the log, the set engine and the index must move together, a `Store` owns the
transactions of the session you give it. It commits when it opens, on every successful
write, and in {py:meth}`~zanzibar.Store.catch_up`; it rolls back on any write that fails
and in {py:meth}`~zanzibar.Store.refresh`. So a write is durable as soon as `add_tuple` or
`remove_tuple` returns, and it is not part of any transaction of your own: **a committed
grant stays committed even if your own code later rolls back.** If a grant must be undone
when your own work fails, remove it explicitly.

This is also why each `Store` should get a `Session` of its own, separate from the one
your application writes its own rows through. A store's commit commits everything on its
session, including any SQL you already flushed or executed there. The store refuses a
session holding objects you added but have not flushed, but it cannot see a flushed object
or a statement you ran, and its next commit makes them permanent.

In the example below the application records an order through its own session, the
grant is committed in the middle of that work, and then the application's work fails.
Its own row is rolled back; the grant is not:

```python
from pathlib import Path
from sqlmodel import Field, SQLModel, Session, create_engine, select
from zanzibar import Store

class Order(SQLModel, table=True):              # one of your application's tables
    id: int | None = Field(default=None, primary_key=True)
    item: str

Path("txn.db").unlink(missing_ok=True)   # start from an empty database each run
engine = create_engine("sqlite:///txn.db")
SQLModel.metadata.create_all(engine)
SCHEMA = """
type user
type doc
  relations
    define viewer: [user]
"""

store = Store(Session(engine), "txn-demo", schema=SCHEMA)
app_session = Session(engine)                  # your application's own work

app_session.add(Order(item="report for alice"))
store.add_tuple("user:alice", "viewer", "doc:1")  # committed here, by the store
app_session.rollback()                            # your work then fails

print(len(app_session.exec(select(Order)).all()))  # -> 0
print(store.check("user:alice", "viewer", "doc:1"))  # -> True
store.remove_tuple("user:alice", "viewer", "doc:1")  # undo it explicitly
print(store.check("user:alice", "viewer", "doc:1"))  # -> False
```

## Seeing both answer

A `Store` keeps its set engine to itself, but you can open a second, standalone
{py:class}`zanzibar.setengine.SetEngine` on the same store, with its own session, and ask
it the same questions. A standalone engine opened on a store that a `Store` owns reads the
store's saved schema and its tuples, and refuses to write. It loads the tuples once, when
it is opened: to see later writes, call its `rebuild()` method or open a new one.

```python
from pathlib import Path
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store
from zanzibar.setengine import SetEngine

SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type folder
  relations
    define parent: [folder]
    define viewer: [user, group#member] or viewer from parent
type doc
  relations
    define parent: [folder]
    define viewer: [user] or viewer from parent
"""

Path("two-backends.db").unlink(missing_ok=True)   # start from an empty database each run
engine = create_engine("sqlite:///two-backends.db")
SQLModel.metadata.create_all(engine)

store = Store(Session(engine), "my-app", schema=SCHEMA)
store.add_tuple("user:alice", "member", "group:eng")
store.add_tuple("group:eng#member", "member", "group:staff")
store.add_tuple("group:staff#member", "viewer", "folder:root")
store.add_tuple("folder:root", "parent", "folder:projects")
store.add_tuple("folder:projects", "parent", "doc:roadmap")

# The Store is synchronous, so this check is answered by the graph index.
print(store.check("user:alice", "viewer", "doc:roadmap"))  # -> True

# A second, independent evaluation of the same tuples.
set_engine = SetEngine(Session(engine), "my-app")
print(set_engine.check("...", "user", "alice", "viewer", "doc", "roadmap"))  # -> True
```

The graph index found alice's row for `doc:roadmap#viewer`, written when the last tuple
connected the chain. The set engine walked from the document up two folders, across to
`group:staff`, and down through `group:eng` to alice. Asked the same six questions, they
agree:

```python
questions = [
    (user, relation, obj)
    for user in ["alice", "bob"]
    for relation, obj in [("viewer", "doc:roadmap"), ("viewer", "folder:projects"),
                          ("member", "group:staff")]
]
same = all(
    store.check(f"user:{user}", relation, obj)
    == set_engine.check("...", "user", user, relation, *obj.split(":"))
    for user, relation, obj in questions
)
print(same)  # -> True
```

A later write reaches the standalone engine only after it reloads:

```python
store.add_tuple("user:bob", "viewer", "folder:projects")
print(store.check("user:bob", "viewer", "doc:roadmap"))  # -> True
print(set_engine.check("...", "user", "bob", "viewer", "doc", "roadmap"))  # -> False
set_engine.rebuild()
print(set_engine.check("...", "user", "bob", "viewer", "doc", "roadmap"))  # -> True
```

You will rarely need to do this yourself. It is shown here because it is, in a much larger
and more systematic form, how the library is tested.

## How they are kept in agreement

Two implementations of the same rules will drift apart unless something stops them. Three
things do.

**One schema layer.** Both backends are built from the same parsed schema, and the
decision whether a write is acceptable is made the same way for both. A schema shape whose
meaning is unclear, or that one backend could not evaluate correctly, is refused when the
schema is parsed, with an explanation and a suggested rewrite; the
[refused shapes reference](../reference/refused-shapes.md) lists them. The few shapes
that only the graph index refuses are described at the end of this page.

**Constant comparison.** The test suite runs the two backends side by side, together with
a third, deliberately simple reference implementation that shares no code with the library
(it even parses schemas itself, so a parser bug cannot hide by affecting both sides). After
each write in a scenario, every check over a grid of questions is compared across all
three, and lookups and expands are compared against answers built from the reference.
Property-based tests generate further scenarios at random. When the backends disagree, the
default assumption is that the library is wrong, and it is fixed; the reference is not
edited to match.

**Proofs about the algorithms.** Models of both algorithms have machine-checked proofs that
they compute the same answers, and the Python is tied to those models by tests. The proofs
are about the models, not the Python itself, and for the graph index they cover a
documented part of the schema language rather than all of it.
[How correctness is checked](assurance.md) says exactly what is and is not covered.

## Where they differ on purpose

A few schemas are evaluated by the set engine but refused by the graph index. A
{py:class}`zanzibar.Store` needs the graph index, so it refuses them too; a standalone set
engine accepts them.

- A relation that recurses through `and` or `but not`, such as a group whose `member`
  relation is `[user, group#member] but not banned`, is refused with
  {py:exc}`zanzibar.CyclicDerivedDependency`.
  [How `and` and `but not` work](boolean-operators.md) explains why, and what to write
  instead.
- Some combinations of `and` / `but not` with the wildcard extensions, such as a
  `[group:*#member]` restriction where `group#member` itself uses `but not`, are refused
  with {py:exc}`zanzibar.UnsupportedByGraphIndex`. See
  [Wildcard extensions beyond OpenFGA](wildcard-extensions.md).

The two also return lookup results in different id spaces, because one names database rows
and the other names in-memory handles. A {py:class}`zanzibar.Store` translates for you;
[Use the backends directly](../how-to/backends-direct.md) covers reading a standalone
engine's results.
