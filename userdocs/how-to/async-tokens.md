# Use async mode and freshness tokens

This page shows how to run a {py:class}`zanzibar.Store` whose graph index is updated
after the write commits, not as part of it, and how to use freshness tokens so that a
read still sees a given write. For why the library works this way and what each read
guarantees, see [Consistency: the tuple log, tokens and stalls](../explanation/consistency.md).

Two words come up throughout. The **tuple log** is the table that records every write, in
order; it is the source of truth. The **set engine** computes answers directly from the
stored tuples, so it is never behind; the **graph index** is the precomputed copy that
async mode updates later. [The two backends](../explanation/two-backends.md) explains
both.

The examples use a SQLite file so that two sessions can share one database. The first
block deletes that file, so the page prints the same values each time you run it. On
PostgreSQL the calls are the same; see [Run on PostgreSQL](postgresql.md) for the
session and isolation-level rules.

## Open a store in async mode

Pass `sync=False`. Each write still commits to the tuple log and returns a token, but the
graph index does not change until something calls
{py:meth}`~zanzibar.Store.catch_up`.

```python
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
"""

Path("async-demo.db").unlink(missing_ok=True)   # start from an empty database each run
engine = create_engine("sqlite:///async-demo.db")
SQLModel.metadata.create_all(engine)

session = Session(engine)
store = Store(session, "my-app", schema=SCHEMA, sync=False)

token = store.add_tuple("user:alice", "viewer", "doc:d1")
print(store.lag())  # -> 1
```

{py:meth}`~zanzibar.Store.lag` counts the log rows the index has not applied yet. It runs
a `COUNT` query, which is why it is a method and not a property.

`sync` belongs to the instance. It is not stored with the store, so every process that
opens the store chooses for itself.

## Schedule `catch_up` yourself

The library ships no background worker. `catch_up()` applies every committed log row the
index has not seen and returns how many it applied:

```python
print(store.catch_up())  # -> 1
print(store.lag())  # -> 0
```

Run it on a schedule that suits you, for example in a process of its own. A minimal
loop:

```python
# not run: loops forever
import logging
import time

from sqlmodel import Session
from zanzibar import Store

log = logging.getLogger("zanzibar-worker")

with Session(engine) as worker_session:
    worker = Store(worker_session, "my-app", sync=False)
    while True:
        try:
            applied = worker.catch_up(batch=500)
            if applied:
                log.info("applied %d log rows", applied)
        except Exception:
            # catch_up() has already recorded the failure on the index as a stall
            # before re-raising, so stall_error is set here. See
            # "Recover a stalled index" for what to do next.
            log.exception("catch_up failed: %s", worker.stall_error)
        time.sleep(1.0)
```

Points to keep in mind:

- **Catch every exception, not only {py:exc}`zanzibar.ZanzibarError`.** A lock timeout or
  a dropped connection arrives as a SQLAlchemy error. The stall is recorded whatever the
  error was, and a later successful `catch_up()` that applies at least one row clears it.
  A stall recorded while nothing was pending stays until some write has been applied; see
  [Recover a stalled index](stall-recovery.md).
- **`batch` sets how many log rows go into one transaction.** Each batch commits on its
  own, and a batch that fails changes nothing. With `batch=None` (the default) all
  pending rows are one transaction, so a failure keeps none of them.
- **Any instance may run `catch_up()`.** Every `catch_up()` takes a per-store lock before
  it reads how far the index has got, so two workers on one store take turns and never
  apply a row twice; running more than one gains nothing.
- **The write fan-out cap does not apply inside `catch_up()`.** A row that a sync
  write would have refused with {py:exc}`zanzibar.ClosureFanoutExceeded` is already
  committed, so `catch_up()` applies it and logs a warning. See
  [Cap write fan-out](fanout-cap.md).

## Read your own write with a token

Every write returns a **freshness token**, an `int`. Treat it as opaque: compare it and
pass it back, nothing else. Token numbers are shared by every store in the database, so
they are not consecutive within one store.

Pass the token as `at_least=` to {py:meth}`~zanzibar.Store.check`. If the index has not
applied that write yet, `check` answers from the set engine instead, which always has it.

```python
token = store.add_tuple("user:bob", "viewer", "doc:d1")

print(store.check("user:bob", "viewer", "doc:d1"))  # -> False
print(store.check("user:bob", "viewer", "doc:d1", at_least=token))  # -> True
```

The first call has no token, so it reads the index as it is, and the index has not
applied the write yet.

To read through every write made so far rather than one particular write, use
{py:meth}`~zanzibar.Store.watermark`, the newest token in the store's log:

```python
print(store.watermark() == token)  # -> True
print(store.check("user:bob", "viewer", "doc:d1", at_least=store.watermark()))  # -> True
```

Adding a tuple that is already stored writes nothing and returns the current watermark.
That is still a correct token to wait for, because the tuple was already there.

```python
print(store.add_tuple("user:bob", "viewer", "doc:d1") == store.watermark())  # -> True
```

A token is the write's id, so you can hand it to another part of your system, for
example in a response header, and pass it back on the next request. Another instance
opened on the same store accepts it.

## Lookups with a token

{py:meth}`~zanzibar.Store.lookup` and {py:meth}`~zanzibar.Store.lookup_reverse` also take
`at_least=`, but they cannot fall back to the set engine. If the index is behind the
token they raise {py:exc}`zanzibar.LookupNotFresh` instead of returning an out-of-date
list:

```python
from zanzibar import LookupNotFresh

try:
    store.lookup("user:bob", at_least=token)
except LookupNotFresh as exc:
    print(type(exc).__name__)  # -> 'LookupNotFresh'
```

To serve it, bring the index up to date and retry:

```python
store.catch_up()
result = store.lookup("user:bob", at_least=token)
print(store.result_keys(result))  # -> {('doc', 'd1', 'viewer')}
```

For a single yes-or-no decision, `check(..., at_least=token)` is the better call: it
never needs a catch-up. {py:meth}`~zanzibar.Store.expand` is answered by the set engine,
so it never raises `LookupNotFresh` either.

## Handle `StaleRead`

A tokened read raises {py:exc}`zanzibar.StaleRead` when the write behind the token is not
visible in this session's current read transaction, so neither the index nor the set
engine can show it yet. The usual cause is a token that another session committed after
this session's transaction began. The fix is to call {py:meth}`~zanzibar.Store.refresh`,
which starts a new read transaction, and retry. A helper in this shape does that (in the
example below the token is this session's own watermark, so the retry branch does not
run; the next example is the one that raises `StaleRead`):

```python
from zanzibar import ForeignToken, StaleRead

def check_at_least(store, user, relation, obj, token):
    try:
        return store.check(user, relation, obj, at_least=token)
    except ForeignToken:
        raise                       # another store's token: no retry can fix it
    except StaleRead:
        store.refresh()
        return store.check(user, relation, obj, at_least=token)

print(check_at_least(store, "user:alice", "viewer", "doc:d1", store.watermark()))  # -> True
```

If the retry raises again, the token is not one this store can satisfy. The message
says why when it can tell, for example that the token is past the newest log id and has
not been issued yet.

The helper re-raises {py:exc}`zanzibar.ForeignToken`, a `StaleRead` that means the token
came from a write to another store, before its `except StaleRead`, because no refresh can
fix it; keep each token with the store it came from (see
{ref}`A token from another store <foreign-token-handling>`).

`refresh()` also rebuilds the instance's in-memory set engine from the stored tuples, so
it costs time in proportion to the store. Call it when a read needs it, not before every
request. It refuses a session that has uncommitted ORM changes, because it would discard
them.

## Avoid the stale-revoke trap

An untokened read on an async store is stale in **both** directions, and **a revoked
grant still reads as allowed** until `catch_up()` applies the removal (why:
[What can be stale, and in which direction](../explanation/consistency.md#what-can-be-stale-and-in-which-direction)):

```python
revoke_token = store.remove_tuple("user:bob", "viewer", "doc:d1")

print(store.check("user:bob", "viewer", "doc:d1"))  # -> True
print(store.check("user:bob", "viewer", "doc:d1", at_least=revoke_token))  # -> False
```

The first answer is wrong in the dangerous direction. So:

- **Pass a token on every decision that must see a revocation.** After removing access,
  keep the removal's token (or read {py:meth}`~zanzibar.Store.watermark` after the
  removal) and pass it to the checks that enforce it.
- **A revocation screen should list with a token.** A tokened `lookup` or
  `lookup_reverse` raises `LookupNotFresh` rather than listing a user who was just
  removed.
- **Use `sync=True` if you cannot pass tokens.** A synchronous store updates the index in
  the write's own transaction, so that instance's reads need no token.

## Read from an async store in another process

A second instance on the same store, sync or async, sees the same tuple log:

```python
reader = Store(Session(engine), "my-app")
print(reader.check("user:bob", "viewer", "doc:d1", at_least=revoke_token))  # -> False
```

Opening a store with the default `sync=True` does **not** apply the backlog that async
instances left. The instance applies it at its own next write or `catch_up()`, so until
then its untokened reads are as stale as an async instance's. A read-only process
serving an async store must either run `catch_up()` itself or pass tokens.

```python
print(reader.lag())  # -> 1
print(reader.check("user:bob", "viewer", "doc:d1"))  # -> True
reader.catch_up()
print(reader.check("user:bob", "viewer", "doc:d1"))  # -> False
```

## Check that the index is applying

`catch_up()` stops at a row it cannot apply and marks the index **stalled**. While that
lasts, untokened `check` answers from the set engine and untokened lookups raise
{py:exc}`zanzibar.IndexStalled`. Watch {py:attr}`~zanzibar.Store.index_stalled` and
`lag()` from your monitoring:

```python
print(store.index_stalled)  # -> False
print(store.stall_error)  # -> None
```

If it is `True`, follow [Recover a stalled index](stall-recovery.md).

## See also

- [Consistency: the tuple log, tokens and stalls](../explanation/consistency.md)
  explains what each kind of read guarantees.
- [Recover a stalled index](stall-recovery.md).
- [Run on PostgreSQL](postgresql.md) covers isolation levels and several instances.
- [Handle errors](errors.md) lists the exceptions and which ones you can retry.
