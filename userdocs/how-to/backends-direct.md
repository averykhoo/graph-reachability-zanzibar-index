# Use the backends directly

A {py:class}`zanzibar.Store` is three parts kept in step for you: a tuple log, the set
engine ({py:class}`zanzibar.setengine.SetEngine`) and the graph index
({py:class}`zanzibar.graphindex.WildcardIndex`). Every write goes into the log, and the store
then applies it to both backends in the right order. Both backends are public, and you can
build either one on its own. This page shows how to use the set engine on its own, and
warns against writing to the graph index on its own.

**In an application, prefer the `Store`**, with one exception. Open a set engine without a
`Store` for tooling, experiments, and write-heavy loads where the graph index is the wrong
trade (see [When not to use this library](../explanation/limits.md#when-not-to-use-this-library)).
Never write to the graph index without a `Store`: driving it yourself means doing by hand
what the `Store` does on every write, and a skipped step fails silently, so the index then
gives wrong answers with no error.
[The two backends](../explanation/two-backends.md) explains how they differ.

## Decide whether you need this

Use the **set engine on its own** when you want answers computed from stored tuples and you
do not need the graph index, the tuple log or freshness tokens. Examples are a test, a
script that evaluates a model against some tuples, a one-off analysis, or a load where
writes far outnumber reads, so the graph index's write-time cost does not pay off. Keep in
mind:

- It never commits. `add_tuple` and `remove_tuple` stage rows on your session, and you
  commit it.
- Its state lives in memory. Opening one reads every stored tuple of the store, so opening
  costs time and memory in proportion to the store.
- Each instance has its own copy of that state. An engine does not see tuples that another
  engine instance wrote after it was opened, until you call its `rebuild()`.
- It takes the six-part tuple form only (`"..."`, `"user"`, `"alice"`, `"viewer"`, `"doc"`,
  `"1"`). The `"user:alice"` form is a `Store` feature.

Do not write to the **graph index on its own**; see
[the last section](#do-not-drive-the-graph-index-on-its-own).

## Use the set engine on its own

Create the tables, open an engine on a store id with a schema, write, commit, and read:

`SQLModel.metadata.create_all` creates only the tables of the modules imported so far, so
import `zanzibar.store` first. It brings in every table the library uses, which you will
need if you later move to a `Store` or build a graph index in the same database.

```python
from sqlmodel import SQLModel, Session, create_engine
import zanzibar.store                            # registers every zanzibar_* table
from zanzibar.setengine import SetEngine

SCHEMA = """
model
  schema 1.1

type user

type doc
  relations
    define banned: [user]
    define viewer: [user] but not banned
    define can_view: viewer
"""

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)

session = Session(engine)
se = SetEngine(session, "notes", SCHEMA)
se.add_tuple("...", "user", "alice", "viewer", "doc", "1")
se.add_tuple("...", "user", "bob", "viewer", "doc", "1")
se.add_tuple("...", "user", "bob", "banned", "doc", "1")
session.commit()                                  # the engine never commits for you

print(se.check("...", "user", "alice", "can_view", "doc", "1"))  # -> True
print(se.check("...", "user", "bob", "can_view", "doc", "1"))  # -> False
```

`lookup` and `lookup_reverse` return a {py:class}`zanzibar.setengine.SetLookupResult`,
which holds ids that only this engine instance can translate. Turn it into
`(type, name, predicate)` keys with `result_keys` (and `excluded_keys` for the subjects a
wildcard grant leaves out) before you keep it or send it anywhere:

```python
viewers = se.lookup_reverse("can_view", "doc", "1")
users = sorted(k for k in se.result_keys(viewers) if k[0] == "user")
print(users)  # -> [('user', 'alice', '...')]
```

Translate a result straight away. After a later write that removes a tuple, after a
`rebuild()`, or on another engine instance, `result_keys` refuses an older result with
{py:exc}`zanzibar.StaleLookupIds` rather than risk naming the wrong entity. Run the lookup
again and translate the new result.

A second engine on the same store id, opened earlier, does not see new tuples until it
rebuilds:

```python
other = SetEngine(Session(engine), "notes", SCHEMA)

se.add_tuple("...", "user", "carol", "viewer", "doc", "1")
session.commit()

print(other.check("...", "user", "carol", "viewer", "doc", "1"))  # -> False
other.rebuild()
print(other.check("...", "user", "carol", "viewer", "doc", "1"))  # -> True
```

For Expand, prefer {py:meth}`zanzibar.Store.expand`, which returns `(type, name, predicate)`
keys. `SetEngine.expand` returns a {py:class}`zanzibar.setengine.MemberSet`, whose ids are
handles that only this engine instance can translate, with the same caveat as a
`SetLookupResult`.

### Move to a `Store` later

A store id whose tuples a standalone set engine wrote has no tuple log, so a `Store`
refuses to open it, with {py:exc}`zanzibar.UnloggedTuplesPresent`. Adopt it instead:
{py:meth}`zanzibar.Store.adopt` saves the schema, builds the graph index from the stored
tuples and opens the store, in one transaction.

```python
from zanzibar import Store, UnloggedTuplesPresent

refused = False
try:
    Store(session, "notes", schema=SCHEMA)
except UnloggedTuplesPresent:
    refused = True
    session.rollback()
print(refused)  # -> True

store, report = Store.adopt(session, "notes", schema=SCHEMA)

print(store.check("user:carol", "can_view", "doc:1"))  # -> True
```

From then on the store id belongs to the `Store`. A `SetEngine` on it can still read, but
its `add_tuple` and `remove_tuple` raise {py:exc}`zanzibar.UnloggedWriteRefused`, because a
write that skips the log would leave the graph index behind for good. Write through the
`Store`. [Bulk-load or adopt an existing store](bulk-load-adopt.md) covers adoption in more
detail.

```python
from zanzibar import UnloggedWriteRefused

refused = False
try:
    se.add_tuple("...", "user", "dave", "viewer", "doc", "1")
except UnloggedWriteRefused:
    refused = True
    session.rollback()
print(refused)  # -> True

store.add_tuple("user:dave", "viewer", "doc:1")

print(store.check("user:dave", "can_view", "doc:1"))  # -> True
session.close()
```

## Do not drive the graph index on its own

The graph index ({py:class}`zanzibar.graphindex.WildcardIndex`) is public so that you can
study or measure it. Do not write to it directly from an application; use a `Store`.

**On a schema with `and` or `but not`, a direct write must be followed by
{py:meth}`zanzibar.graphindex.DeltaProcessor.run_cascade` in the same transaction.** The
graph index keeps each boolean relation up to date with a
{py:class}`zanzibar.graphindex.DeltaProcessor`, and only the cascade brings the relation in
line with the write. The index refuses a write on the boolean relation's own name (here
`viewer`) with a `ValueError`; a write has to be rewritten onto the relation's internal
parts first. That rewritten write is the dangerous one: if the cascade were skipped, the index would
answer wrongly from then on. On the schema above, `alice` would never get `can_view` on
`doc:1`, although she is a viewer and is not banned. So the commit refuses it: committing a
transaction that wrote to the index on a boolean schema and ran no cascade after that write
raises {py:exc}`zanzibar.CascadeNotRun`, and the transaction stays open, for you to roll it
back or run the cascade and commit again. The check proves that a cascade was called, not
that it was called with the right watermark: pass the `outbox_watermark` read before the
first write. A refused write (for example {py:exc}`zanzibar.ClosureFanoutExceeded`) still
leaves the transaction owing a cascade or a rollback. A `Store` runs the cascade for you,
in the same transaction that applies the write to the index: the write itself with
`sync=True`, or {py:meth}`zanzibar.Store.catch_up` with `sync=False`.

## Errors only the backends raise

You meet these only when you drive the backends or the offline index tools yourself: a
`Store`'s reads and writes never raise them (`Store.adopt`, which runs the index build,
can raise the last one). All three are {py:exc}`zanzibar.ZanzibarError`s; their
attributes are in the [exceptions reference](../reference/exceptions.md).

- {py:exc}`zanzibar.CascadeNotRun`: you wrote to a bare graph index on a schema with
  `and` / `but not` and committed without running the delta processor's `run_cascade`
  after your last write. The commit is refused and the transaction stays open: roll back,
  or run the cascade and commit again (see the section above).
- {py:exc}`zanzibar.MissingDeltaProcessor`: you drove the index's apply step yourself,
  on a schema with `and` / `but not`, without the delta processor that maintains those
  relations.
- {py:exc}`zanzibar.IndexExists`: {py:func}`zanzibar.store.build_index` was pointed at an
  index that already exists. Use a new index store id, or
  {py:func}`zanzibar.store.rebuild_index` to rebuild one in place.
  {py:meth}`zanzibar.Store.adopt` raises it too, for a store id that already has an index:
  open that one with `Store(session, store_id)` instead.
