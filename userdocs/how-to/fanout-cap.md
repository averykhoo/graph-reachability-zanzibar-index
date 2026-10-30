# Cap write fan-out

One write to the graph index can add many index rows at once (granting a group access to a
document adds about one row per member), and it holds the store's write lock while it does.
The **write fan-out cap** refuses, with {py:exc}`zanzibar.ClosureFanoutExceeded`, a
synchronous write that would touch more index rows than a limit. (The exception and the
environment variable call it the *closure* fan-out cap: the index rows are the
permission closure, every who-reaches-what pair the index stores.) How the rows are counted,
and what a large write costs, is explained in
[Limits and costs](../explanation/limits.md#the-write-fan-out-cap).

This page shows how to set the limit, what it applies to, and how to handle a refusal.

## Set the limit

The limit is the environment variable `ZANZIBAR_MAX_CLOSURE_FANOUT`. The default is
100,000, and `0` turns the cap off.

```text
export ZANZIBAR_MAX_CLOSURE_FANOUT=10000
```

A {py:class}`zanzibar.Store` reads the variable once, when it is opened, and keeps that
limit for its lifetime. Changing the variable later does not affect a store that is
already open. There is no `Store` argument for it. A value that is not an integer makes
opening the store fail with a `ValueError` that names the variable, and a negative value is
refused with a `ValueError` too, rather than either falling back to the default. An empty
value means the default.

### Choosing a value

The default is set high so that ordinary workloads never reach it: it turns "unbounded"
into "bounded" and is not tuned for any workload. A tighter limit is a choice about how
long you can tolerate one write holding the write lock. Measure the cost of large writes on
your own hardware and data; [Limits and costs](../explanation/limits.md#writes-pay-so-that-reads-are-cheap)
gives laptop figures for the time and memory a write takes per index row.

## See the cap refuse a write

This example sets a very small limit, so that a grant to a ten-member group is over it.
In a real deployment you would set the variable in the process environment instead of in
code:

```python
from pathlib import Path
import os
os.environ["ZANZIBAR_MAX_CLOSURE_FANOUT"] = "5"   # must be set before the Store opens

from sqlmodel import SQLModel, Session, create_engine
from zanzibar import ClosureFanoutExceeded, Store

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

Path("fanout.db").unlink(missing_ok=True)   # start from an empty database each run
engine = create_engine("sqlite:///fanout.db")
SQLModel.metadata.create_all(engine)
store = Store(Session(engine), "my-app", schema=SCHEMA)

for i in range(10):
    store.add_tuple(f"user:u{i}", "member", "group:big")
before = store.watermark()

try:
    store.add_tuple("group:big#member", "viewer", "doc:1")
    refused = False
except ClosureFanoutExceeded as error:
    refused = True
    message = str(error)

print(refused)  # -> True
```

The message gives the count for this write and the limit:

```python
print(message.startswith("closure fan-out cap exceeded: this write would add 10"))  # -> True
```

The refusal is complete: the tuple is not in the store, no index rows were written, and
both backends agree. The store stays usable for other writes:

```python
print(store.watermark() == before)  # -> True
print(store.check("user:u1", "viewer", "doc:1"))  # -> False
store.add_tuple("user:u1", "viewer", "doc:1")
print(store.check("user:u1", "viewer", "doc:1"))  # -> True
```

## What the cap applies to

The cap applies to every write that **adds** a tuple on a synchronous store
(`sync=True`, the default). That includes writes that take access away under `but not`:
adding a user to a ban list, or adding a member to a banned group, adds index rows and is
capped like any grant.

The cap does **not** apply to:

- **Removing a tuple.** A removal is never refused by the cap for its own size, so you can
  shrink a large group or revoke a large grant. (On a synchronous instance, an over-limit
  row still waiting from an async writer can block a removal too; see
  [A pending row can block every synchronous write](#sync-writers-blocked-by-backlog).)
- **The async apply step.** On a store opened with `sync=False`, a write only goes into the
  tuple log, and {py:meth}`zanzibar.Store.catch_up` applies it later. The tuple is already
  committed by then, so `catch_up` applies an over-limit write anyway and logs a warning on
  the `zanzibar.graphindex.core` logger instead of refusing it.
- **Building an index from existing tuples** with {py:func}`zanzibar.store.build_index`,
  {py:func}`zanzibar.store.rebuild_index` or {py:meth}`zanzibar.Store.adopt`. The default
  bulk build never checks the cap, and the incremental build (`bulk=False`) logs a warning
  instead of refusing.

Continuing the example, an async instance accepts the same grant that the sync one
refused, and `catch_up` applies it:

```python
async_store = Store(Session(engine), "my-app", sync=False)
async_store.add_tuple("group:big#member", "viewer", "doc:2")
print(async_store.lag())  # -> 1
```

Until `catch_up` has applied that row, it blocks the synchronous instance, as the next
section explains.

(sync-writers-blocked-by-backlog)=
## A pending row can block every synchronous write

A `sync=True` instance applies the pending backlog (rows other instances wrote with
`sync=False` and no `catch_up()` has applied yet) as part of each of its own writes,
before its own row, and that step is capped like any synchronous write. So while a row
that the index refuses is pending, **every** write through a `sync=True` instance on the
same store id fails, even an unrelated small grant, and removals included. The exception's
message says so: it starts "this write (log row N) was rolled back because the index
backlog ... holds an earlier log row it cannot apply", names that pending row, and says how
to unblock the store. Its `failing_log_row` attribute is `(log id, row)` for that pending
row. (A duplicate add appends no log row, so its message starts "this write (a duplicate
add, which appends no log row)" instead.) Two refusals behave this way:

- {py:exc}`zanzibar.ClosureFanoutExceeded`, for a pending row over the write fan-out cap.
  `catch_up()` applies such a row anyway (with a warning), which unblocks the writers.
- {py:exc}`zanzibar.PathCountExceeded`, for a pending row past the path-count limit.
  `catch_up()` cannot apply that row either: the index stalls, and the row has to be
  removed at the source. See [Recover a stalled index](stall-recovery.md).

Continuing the example, a small grant through the synchronous instance is refused because
of the pending grant to `group:big`:

```python
store.refresh()
try:
    store.add_tuple("user:u1", "viewer", "doc:9")
    refused = False
except ClosureFanoutExceeded as error:
    refused = True
    message = str(error)
    pending_row = error.failing_log_row
print(refused)  # -> True
print("this write would add 10" in message)  # -> True
print("holds an earlier log row it cannot apply" in message)  # -> True
print("run Store.catch_up()" in message)  # -> True
print(pending_row[1])  # -> 'ADD group:big#member viewer doc:2'
```

Run `catch_up()` first; once the row is applied, the synchronous instance writes again:

```python
print(async_store.catch_up())  # -> 1
print(async_store.check("user:u7", "viewer", "doc:2"))  # -> True
store.refresh()
store.add_tuple("user:u1", "viewer", "doc:9")
print(store.check("user:u1", "viewer", "doc:9"))  # -> True
```

So the cap protects writers on the synchronous path. With `sync=False` it does not limit
what the index stores; it only stops a single synchronous write from holding the lock for
too long. If you write over-limit rows asynchronously, either keep that store id fully
asynchronous, or make sure `catch_up()` runs before the synchronous writers resume.

## Handle a refusal

{py:exc}`zanzibar.ClosureFanoutExceeded` is an {py:exc}`zanzibar.AdmissionRejected`, and so
a `ValueError` and a {py:exc}`zanzibar.ZanzibarError`. Catch it before a broader
`AdmissionRejected` handler if you want to treat it differently: an `AdmissionRejected`
usually means the request itself was wrong, while this one means the request was valid but
too large for one write.

Retrying the same write does not help, because the index has not changed. Your options:

- **Split the grant.** Grant several smaller groups instead of one very large one, so each
  write stays under the limit. The members end up with the same access.
- **Raise the limit** for the process that makes such writes, or set it to `0` there.
- **Do it asynchronously.** Write through a `sync=False` store, where the cap does not
  refuse, and let `catch_up` apply the write. The lock is then held by the apply step
  instead of by the writer. Until `catch_up` has applied it, synchronous writers on the
  same store id are refused (see
  [A pending row can block every synchronous write](#sync-writers-blocked-by-backlog)). See
  [Use async mode and freshness tokens](async-tokens.md).

## Expect the first write after opening to be slow

Once a store has taken one write since it was opened, the cap refuses a grant to a very
large group quickly: it counts the rows the write would touch and refuses before reading
them. The first write after a store is opened is the exception, and so is the first write
after each {py:meth}`zanzibar.Store.refresh`, which rebuilds the set engine. That write is
slow on a large store whether it is refused or admitted, because the set engine first
builds the graph it uses to check for cycles, and it holds the write lock while it does.
That build grows with the size of the whole store, so allow for the delay after every
restart, and do not call `refresh()` on a writing store more often than you need to.
Measured figures are in
[A refused write is not free](../explanation/limits.md#a-refused-write-is-not-free).

## Related

- [Handle errors](errors.md) for where this exception sits among the others.
- {py:exc}`zanzibar.PathCountExceeded`, the other index resource limit, which cannot be
  turned off: see [Recover a stalled index](stall-recovery.md).
