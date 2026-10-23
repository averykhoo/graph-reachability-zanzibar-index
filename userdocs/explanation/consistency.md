# Consistency: the tuple log, tokens and stalls

A permission system is only as good as its answer right after a change. If you remove
Mallory from a document and the next request still lets her in, the removal did not
happen as far as she is concerned. This page explains what a read can and cannot see
after a write, why the answer depends on how the index is kept up to date, and why some
reads refuse to answer instead of guessing.

For the steps to set up asynchronous mode, see
[Use async mode and freshness tokens](../how-to/async-tokens.md). To recover an index
that has stopped advancing, see [Recover a stalled index](../how-to/stall-recovery.md).

## The tuple log is the truth; the index is a view of it

A {py:class}`zanzibar.Store` keeps three things in your database and one in memory:

- **The tuples** you have written, one row each.
- **The tuple log**: one row per successful write, `ADD` or `REMOVE`, never deleted. Each
  row has an id that only grows. The log is the source of truth; everything else can be
  rebuilt from it.
- **The graph index**: the precomputed answers that make `check` a single lookup (see
  [How the graph index works](graph-index.md)). With it, a **cursor** row records the id
  of the last log row the index has applied.
- **The set engine**, in memory in each `Store` instance. It holds the tuples as bitmaps
  and works an answer out when asked (see [The two backends](two-backends.md)). It is
  built by replaying the stored tuples when the store opens, and then kept up to date by
  reading log rows it has not seen yet.

A write goes through the same steps every time. The store takes a per-store lock, brings
its set engine up to date with every write already committed (by any instance), checks the
new tuple against the schema and the current state, and appends a log row. The id of that
row is the write's **freshness token**, and the write method returns it.

What happens next, and so what a later read sees, depends on one setting.

## Sync and async

**Synchronous** (`sync=True`, the default). The write also applies its log row to the
graph index, in the same database transaction, before it commits. The tuple, the log row,
the index change and the cursor move commit together or not at all. When the write
returns, this instance's reads already see it, and so does any other instance whose
database session can see the commit. You never need a token in this mode, as long as
every instance writing to the store is synchronous.

**Asynchronous** (`sync=False`). The write appends to the log, updates the writing
instance's in-memory set engine, and commits. The graph index is left behind. It catches
up when something calls {py:meth}`zanzibar.Store.catch_up`, which applies the log rows past
the cursor in batches, one transaction per batch. The rows of a batch and the cursor move
commit together, so a batch that fails moves nothing, and a retry applies the same rows
again. The library ships no background worker; you decide when `catch_up()` runs (the
how-to has a worker loop).

Async mode makes writes cheaper for the writer: the cost of updating the index moves to
whoever runs `catch_up()`. The price is that, for a while, the index is behind the log.
{py:meth}`zanzibar.Store.lag` counts the log rows the index has not applied yet.

```{image} img/consistency-sync-async.svg
:class: only-light
:alt: Two tuple logs of six rows. With sync=True the cursor is after row 6, so lag is 0. With sync=False the cursor is after row 4, and rows 5 and 6 wait for catch_up, so lag is 2. The id of the newest row is the newest write's token.
```

```{image} img/consistency-sync-async-dark.svg
:class: only-dark
:alt: Two tuple logs of six rows. With sync=True the cursor is after row 6, so lag is 0. With sync=False the cursor is after row 4, and rows 5 and 6 wait for catch_up, so lag is 2. The id of the newest row is the newest write's token.
```

`sync` is a property of one `Store` object, not of the stored data. Two instances on the
same store id can use different settings. A synchronous instance applies whatever backlog
async instances left only at its own next write or `catch_up()`, so opening a store
synchronously does not by itself bring its index up to date.

Here is the gap in action. A synchronous store answers at once; an async one answers from
an index that has not seen the write:

```python
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

engine = create_engine("sqlite:///consistency.db")
SQLModel.metadata.create_all(engine)

store = Store(Session(engine), "docs", schema=SCHEMA, sync=False)
token = store.add_tuple("user:alice", "viewer", "doc:1")

print(store.lag())                                      # -> 1
print(store.check("user:alice", "viewer", "doc:1"))     # -> False
```

The write committed, but the index has not applied it, and an untokened `check` reads the
index as it is.

## Freshness tokens

A token is an `int`: the id of the write's log row. Treat it as opaque. The only useful
things to do with it are to keep it, compare it with another token from the same store,
and pass it back as `at_least=`.

`at_least=token` is a demand: "answer as of that write, or later". It is not a request to
read the past. There is no way to ask what the answer was at an older token; every read
answers from the newest state the read path has.

A few properties follow from tokens being log ids:

- **They only grow.** A later write to a store gets a larger token.
- **They belong to one store.** Log ids are numbered across every store in the database,
  so a token from store A says nothing about store B; each tokened read looks the token's
  log row up and refuses another store's token, above or below what B has applied, with
  {py:exc}`zanzibar.ForeignToken` (what to do about it is in
  {ref}`A token from another store <foreign-token-handling>`).
- **Adding a tuple that is already there writes nothing.** It returns the newest token in
  the store's log, {py:meth}`zanzibar.Store.watermark`, which may be another write's
  token. That is still a correct demand: the tuple was already present at that point.
- **Only `None` or an `int` of 0 or more is accepted.** `True` and negative numbers are
  refused.

If you know Zanzibar, this is a simplified zookie. A Zanzibar zookie lets a read be
evaluated at a snapshot at least as fresh as a given write. Here the token does the same
job ("at least as fresh as"), but there is no snapshot selection and no other consistency
mode.

The same async store, with the token:

```python
print(store.check("user:alice", "viewer", "doc:1", at_least=token))   # -> True
```

The index was still behind the token, so `check` answered from the set engine instead,
which already has the write.

## What can be stale, and in which direction

Every read surface makes the same promise when it is given a token: it answers as of that
write or later, or it raises. They differ in what they do without one, and in what they
fall back to.

| read | without a token | with `at_least=token` |
| --- | --- | --- |
| `check` | the index as it is; if the index is **stalled**, the set engine | the index if it has reached the token; otherwise the set engine, brought up to the token |
| `lookup`, `lookup_reverse` | the index as it is; if the index is **stalled**, raises {py:exc}`zanzibar.IndexStalled` | the index if it has reached the token; otherwise raises {py:exc}`zanzibar.LookupNotFresh` |
| `expand` | always the set engine, brought up to date with every write this session can see | the same, and raises {py:exc}`zanzibar.StaleRead` if the token is not visible yet |

An untokened read from the index is **stale in both directions** while the index lags:

- A new grant reads as denied. That is the harmless direction.
- **A revoked grant still reads as allowed** until `catch_up()` applies the removal. That
  is the dangerous direction, and it is the reason tokens exist.

So the rule for an async deployment is: any decision that must see a recent revoke carries
the revoke's token, or the newest one from `watermark()`.

Continuing the example, revoke Alice and ask again:

```python
store.catch_up()                       # the index applies the grant
revoke = store.remove_tuple("user:alice", "viewer", "doc:1")

print(store.check("user:alice", "viewer", "doc:1"))                     # -> True
print(store.check("user:alice", "viewer", "doc:1", at_least=revoke))    # -> False
```

The first answer is the stale ALLOW: the removal is in the log but not in the index. The
second carries the revoke's token and is correct.

```{image} img/consistency-revoke.svg
:class: only-light
:alt: The log holds t1, the grant, and t2, the revoke; the index has applied only t1, while the set engine has read t2. A check without a token reads the index and returns True, a stale allow. A check with at_least=t2 sees that the index cursor is before t2, falls back to the set engine, and returns False.
```

```{image} img/consistency-revoke-dark.svg
:class: only-dark
:alt: The log holds t1, the grant, and t2, the revoke; the index has applied only t1, while the set engine has read t2. A check without a token reads the index and returns True, a stale allow. A check with at_least=t2 sees that the index cursor is before t2, falls back to the set engine, and returns False.
```

The staleness of an untokened read is **bounded**: the index trails the log by whatever the
async worker has not applied *yet*. That bound is what makes an untokened read acceptable
at all, and it is why a stalled index (below) changes the rules.

### When the token is not visible yet

A read happens inside your database session's current transaction. If the write behind a
token was committed by another instance after that transaction began, this session cannot
see the log row, so the set engine cannot catch up to it either. Rather than serve an
answer that ignores the write it was asked to include, the read raises
{py:exc}`zanzibar.StaleRead`. Call {py:meth}`zanzibar.Store.refresh`, which starts a new
transaction, and retry. (Another store's token is not a freshness problem; it raises
`ForeignToken`, as above.)

This is also why a `Store` on PostgreSQL refuses any isolation level other than
`READ COMMITTED` ({py:exc}`zanzibar.UnsafeIsolationLevel`), stricter levels included. Under
`REPEATABLE READ` or `SERIALIZABLE`, a transaction keeps reading the snapshot it started
with, so catching up to "the newest committed write" silently stops at that snapshot, and
a token could then vouch for an answer that misses a committed revoke. See
[Run on PostgreSQL](../how-to/postgresql.md).

## Why lookups refuse instead of falling back

`check` can fall back to the set engine because its answer is a `bool`: which backend
produced it makes no difference to you. A lookup result is not like that. The two backends
return different things:

- **Different ids.** A {py:class}`zanzibar.LookupResult` from the index holds database row
  ids of index nodes. The set engine's result holds its own in-memory ids, which it
  reuses after a tuple is removed. A result that sometimes held one kind and sometimes the
  other, depending on how far behind the worker happened to be, would mean different
  things on different calls.
- **Different marker shapes.** The index reports wildcard grants as triples, the set
  engine as pairs (see {ref}`Result markers <api-result-markers>`).

Serving the stale index list instead is worse. A revoked user staying listed in an
access-review screen is exactly the failure the token was meant to rule out. So a lookup
with a token the index has not reached raises {py:exc}`zanzibar.LookupNotFresh`, and you
choose: run `catch_up()` and retry, or, for a single yes/no decision, use `check` with the
same token, which does fall back.

{py:meth}`zanzibar.Store.expand` is the exception that proves the rule. It never reads the
index, so it never needs a fallback: it always answers from the set engine, and it returns
`(type, name, predicate)` keys rather than ids. See
[Find who can access what](../how-to/query-access.md) for how to read its result next to a
lookup's.

```python
from zanzibar import LookupNotFresh

try:
    store.lookup_reverse("viewer", "doc:1", at_least=revoke)
    outcome = "answered"
except LookupNotFresh:
    outcome = "refused"
print(outcome)                         # -> 'refused'

store.catch_up()
found = store.lookup_reverse("viewer", "doc:1", at_least=revoke)
print(("user", "alice", "...") in store.result_keys(found))             # -> False
```

## Stalls

`catch_up()` applies log rows in order, and it cannot skip one: a later row may depend on
an earlier one. If applying a row fails, the batch rolls back, the exception propagates to
whoever called `catch_up()`, and the store records a **stall** on the cursor row: "the index
could not advance past this point", with the error and, when applying a log row failed,
which row.

A stall is recorded for **every** failure, including ones that will go away by themselves
(a lock timeout, a lost connection). That is deliberate. A false stall costs some slower
reads until the next good batch clears it. A missed stall is far worse: if the failing row
can never be applied, every later row waits behind it forever, revocations included, and
the index's staleness is no longer bounded. A classifier that tried to guess which errors
are permanent would open that hole the first time it guessed wrong.

Because the stall is stored in the database, every instance sees it, each as soon as its
own session reads the cursor row again (a replica that only reads sees it after its next
`refresh()`). {py:attr}`zanzibar.Store.index_stalled` is `True` while it lasts, and
{py:attr}`zanzibar.Store.stall_error` names the error and, when applying a log row failed,
which row.

While the index is stalled, an untokened read can no longer rely on the bound, so the
rules change:

| call | while the index is stalled |
| --- | --- |
| `check(...)` without a token | answers from the set engine: correct, but slower |
| `check(..., at_least=token)` | unchanged: the index if it has reached the token, otherwise the set engine |
| `lookup` / `lookup_reverse` without a token | raises {py:exc}`zanzibar.IndexStalled`, a kind of `LookupNotFresh`, for the reasons in the section above |
| `lookup` / `lookup_reverse` with a token | unchanged: served from the index if it already applied the token's write, otherwise `LookupNotFresh`. A token at or below the cursor is genuinely reflected in the index, stalled or not |
| `expand(...)` | unchanged: it never reads the index |
| writes through a `sync=False` instance | unchanged: they only append to the log |
| writes through a `sync=True` instance | such an instance applies the pending backlog as part of each write, so while the failing row is pending its writes run into it and are refused |

So a stall costs lookups, some speed, and synchronous writes. It never makes `check` give
a wrong answer.

```{image} img/consistency-stall.svg
:class: only-light
:alt: Seven log rows. Rows 1 to 3 are applied and the cursor is after row 3. Row 4 fails, and rows 5 to 7, revokes included, wait behind it. While the stall lasts, a check without a token uses the set engine, a lookup without a token raises IndexStalled, and writes through a sync=True instance are refused.
```

```{image} img/consistency-stall-dark.svg
:class: only-dark
:alt: Seven log rows. Rows 1 to 3 are applied and the cursor is after row 3. Row 4 fails, and rows 5 to 7, revokes included, wait behind it. While the stall lasts, a check without a token uses the set engine, a lookup without a token raises IndexStalled, and writes through a sync=True instance are refused.
```

**How a stall ends.** A successful `catch_up()` that applies at least one row clears it, so
a transient failure clears at the next good run that has work to do. (A stall recorded
while nothing was pending stays until a later write has been applied; see
[Recover a stalled index](../how-to/stall-recovery.md).) A row the index can never apply does not clear by itself.
With the write fan-out cap suspended inside `catch_up()` (an over-cap row is applied with a
warning instead; see [Cap write fan-out](../how-to/fanout-cap.md)), the remaining cause of
such a row is a path count too large to store, {py:exc}`zanzibar.PathCountExceeded`.
Removing the tuple is necessary ({py:meth}`zanzibar.Store.remove_tuple` through a
`sync=False` instance works while stalled; a `sync=True` instance's removal runs into the
failing row too, as in the table above; see
[step 1 of the recovery](../how-to/stall-recovery.md#1-remove-the-offending-tuple-at-the-source)), but the removal alone does not clear the stall, because it is itself a log row
waiting behind the failing one. Remove the tuple, then rebuild the index from the tuples
with {py:func}`zanzibar.store.rebuild_index`; the
[stall recovery guide](../how-to/stall-recovery.md) has the steps.

## Summary

- The tuple log is the truth. The graph index is a view of it, and the set engine is an
  in-memory evaluator rebuilt from it.
- In sync mode (the default) a write and its index update commit together; there is
  nothing to wait for.
- In async mode an untokened read can be stale in both directions, a revoked grant still
  allowed included. Pass the write's token to any read that must see it.
- With a token, `check` falls back to the set engine; lookups refuse
  (`LookupNotFresh`); `expand` never uses the index at all.
- A stall makes the index's staleness unbounded, so untokened `check` switches to the set
  engine and untokened lookups refuse (`IndexStalled`) until a successful `catch_up()`, or
  a rebuild for a row that can never be applied.
