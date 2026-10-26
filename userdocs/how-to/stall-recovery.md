# Recover a stalled index

This page is for a store run in async mode (`sync=False`, see
[Use async mode and freshness tokens](async-tokens.md)) whose
{py:meth}`~zanzibar.Store.catch_up` has started failing. It shows how to tell a stall that
clears by itself from one that does not, and how to recover from the second kind.

## Before you start

`catch_up()` applies log rows in order. When it cannot apply one, it raises and records a
**stall** on the index, which every instance of the store sees. While the index is stalled,
untokened lookups raise {py:exc}`zanzibar.IndexStalled`, untokened `check` answers from the
set engine, and writes through a `sync=True` instance are refused. What each call does
during a stall, and why, is in
[Stalls](../explanation/consistency.md#stalls).

## Detect a stall

Use {py:attr}`~zanzibar.Store.index_stalled` and {py:attr}`~zanzibar.Store.stall_error`.
`stall_error` is `None` unless the index is stalled; then it names the last log id the
index applied, the row that failed and the error. Both are as fresh as this session's
view of the index, so an instance that did not run the failing `catch_up()` sees the stall
after its next {py:meth}`~zanzibar.Store.refresh`.

The rest of this page builds a store that really stalls. Its schema lets groups contain
groups, and the tuples form a chain of 32 "diamonds": each layer has two groups that are
both members of both groups in the next layer. The number of distinct paths from the top
group to the bottom one doubles with every layer, and the index stores that count in a
32-bit column, so the last tuple pushes it past the limit.

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
"""

engine = create_engine("sqlite:///stall.db")
SQLModel.metadata.create_all(engine)

store = Store(Session(engine), "my-app", schema=SCHEMA, sync=False)
store.add_tuple("user:alice", "member", "group:a0")

LAYERS = 32
for i in range(LAYERS):
    for upper in ("a", "b"):
        for lower in ("a", "b") if i < LAYERS - 1 else ("a",):
            store.add_tuple(f"group:{upper}{i}#member", "member", f"group:{lower}{i + 1}")
```

The worker's `catch_up()` raises, and the store is now stalled:

```python
from zanzibar import IndexStalled, PathCountExceeded

try:
    store.catch_up(batch=50)
except PathCountExceeded as exc:
    print(type(exc).__name__)  # -> 'PathCountExceeded'

print(store.index_stalled)  # -> True
print("ADD group:b31#member member group:a32" in store.stall_error)  # -> True
```

Because `batch=50` was given, every batch that finished before the failing one was
committed. A batch is applied whole or not at all, so the index stopped at the start of
the batch that holds the bad row, not just before the row: here 27 rows are still pending.
With no `batch`, everything pending is one transaction and the index stays where it was.

```python
print(store.lag())  # -> 27
```

Untokened reads behave as a stall makes them:

```python
print(store.check("user:alice", "member", "group:a32"))  # -> True

try:
    store.lookup("user:alice")
except IndexStalled as exc:
    print(type(exc).__name__)  # -> 'IndexStalled'
```

## Decide whether it will clear by itself

- **Transient: a lock timeout, a lost connection, the database restarting.** Nothing is
  wrong with the row. The next successful `catch_up()` clears the stall, so keep the
  worker running. A worker loop that logs and retries is enough; see the worker loop in
  [Use async mode and freshness tokens](async-tokens.md). This includes a stall recorded
  while nothing was pending (for example a connection lost while the worker polled an
  idle store): a later `catch_up()` that finds nothing to apply clears it, because it has
  just confirmed the index is at the head of the log.
- **Permanent: {py:exc}`zanzibar.PathCountExceeded`.** The row can never be applied, so
  every later row waits behind it forever. That includes a later removal of the same
  tuple: the removal is a log row too, and it queues behind the row it would undo. This
  stall needs the recipe below.

If `stall_error` names the same row and the same error after several attempts, treat it
as permanent.

The write fan-out cap ({py:exc}`zanzibar.ClosureFanoutExceeded`) never stalls the
index: `catch_up()` applies an over-cap row with a logged warning instead of refusing it.
Until it has, the row still blocks synchronous writers; see
[A pending row can block every synchronous write](fanout-cap.md#a-pending-row-can-block-every-synchronous-write).

### Writes through a sync instance fail too

While the bad row is pending, every write through a `sync=True` instance runs into it,
even the removal of the bad tuple itself, and is refused with `PathCountExceeded`. The
message says that the backlog holds a row the index cannot apply, names that row (also in
`failing_log_row`), and points to the recovery below (the general rule is in
[A pending row can block every synchronous write](fanout-cap.md#a-pending-row-can-block-every-synchronous-write)).
`stall_error` on the async instance names the same row:

```python
sync_store = Store(Session(engine), "my-app")

try:
    sync_store.add_tuple("user:bob", "member", "group:a0")
except PathCountExceeded as exc:
    print("group:a32" in str(exc))  # -> True
    print("rebuild_index" in str(exc))  # -> True
```

The write was rolled back. Make the repair writes below through a `sync=False` instance.

## Recover from a permanent stall

### 1. Remove the offending tuple at the source

`stall_error` names the row. Remove it (or restructure the grants so that far fewer
parallel paths reach the same group) through an **async** instance. Its writes only
append to the log, so they work while the index is stalled.

```python
store.remove_tuple("group:b31#member", "member", "group:a32")
```

### 2. Stop the `catch_up()` worker and the writers

They need stopping for different reasons:

- **The worker**: the rebuild holds the store's lock while it runs, and so does every
  `catch_up()`. Pause the worker so it does not wait on, or contend with, that lock.
- **Writers**: the rebuild refuses to finish if any write commits while it runs (a
  `RuntimeError` saying "concurrent writes"). Stop them, or retry the rebuild when the
  store is quiet.

### 3. Rebuild the index in place

{py:func}`zanzibar.store.rebuild_index` throws the index's state away and builds it again
from the stored tuples, in one transaction, and commits. Give it a clean session of its
own:

```python
from zanzibar.store import rebuild_index

with Session(engine) as ops_session:
    rebuild_index(ops_session, "my-app")
```

If the stored tuples still overflow somewhere, the rebuild raises `PathCountExceeded`
naming the next closure row that overflows, and **changes nothing**: the old index and its
stall stay, and reads stay as correct as they were. Fix that grant too and run the rebuild
again. `stall_error` names only the first row that failed, so a grant graph with several
overflowing paths can take more than one round.

### 4. Refresh the other instances and restart the worker

Each open instance sees the cleared stall after its next `refresh()`:

```python
store.refresh()
print(store.index_stalled)  # -> False
print(store.catch_up())  # -> 0
```

The index is serving again:

```python
print(store.check("user:alice", "member", "group:a32"))  # -> True
print(("group", "a32", "member") in store.result_keys(store.lookup("user:alice")))  # -> True
```

On a `sync=True` store the same tuple is refused at the write, with
`PathCountExceeded`, and nothing is stored, so a sync store never stalls on it.

## Avoid the overflow

The count that overflows is the number of distinct derivation paths between a subject and
an object, not the number of members. It grows when many parallel routes lead to the same
place: groups nested inside several sibling groups, layer after layer. Shallow group
nesting with one route per member stays far from the limit. See
[Limits and costs](../explanation/limits.md).

## See also

- [Use async mode and freshness tokens](async-tokens.md).
- [Handle errors](errors.md).
- {py:func}`zanzibar.store.rebuild_index` and {py:func}`zanzibar.store.build_index` in the
  [API reference](../reference/api/store.md).
