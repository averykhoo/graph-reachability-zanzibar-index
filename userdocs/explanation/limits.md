# Limits and costs

This page explains what grows with your data, what each part of the library costs, and
what the library refuses in order to stay bounded. It ends with the cases where this
library is the wrong choice.

```{admonition} About the numbers on this page
:class: note

Unless a section or a table row gives its own date, the measurements were taken on
2026-10-14 and 2026-10-16 on one laptop (Intel i7-1365U, Windows 11, Python 3.13, a SQLite database file, runtime
invariant checks off), which other work was sharing. Treat them as orders of magnitude,
not as a specification, and measure on your own hardware and data before relying on them.
```

## Writes pay so that reads are cheap

The graph index stores every permission that follows from your tuples, not only the tuples
themselves (see [How the graph index works](graph-index.md)). That makes a `check` a single
lookup, and it makes some writes large. When a write links a subject to an object, the
index adds one row for every pair of "something that reaches the subject" and "something
the object reaches", plus one for each of those on its own. In practice:

- granting `group:eng#member` access to `doc:1`, when the group has *N* members, adds
  about *N* rows;
- adding a user to a group whose members can reach *M* objects adds about *M* rows;
- linking a group with *a* members to a folder containing *d* documents adds about
  *a* × *d* rows, from a single tuple.

Each added row costs time, memory in the writing process during the write, and disk. The
measured cost per row was:

| | SQLite file | PostgreSQL 17 (same laptop) |
| --- | --- | --- |
| write time per added row | about 270 to 370 µs | 1.05 to 1.3 times SQLite |
| writer memory per added row, during the write | about 4.6 to 8.6 KB | the same (it is held client-side) |
| disk per added row | about 130 bytes | about 270 to 280 bytes |

On top of the per-row cost there is a fixed part of about 0.1 s per write in that
benchmark, so small writes are dominated by it and large writes by the rows. The cost grew
linearly with the number of rows from 1,000 up to 1,000,000, with no knee before the
writer ran out of memory:

| rows added by one write | write time | peak writer memory |
| --- | --- | --- |
| 1,000 | about 0.4 s | about 6 MB |
| 10,000 | about 2.4 to 3.4 s | about 50 to 70 MB |
| 100,000 | about 27 to 37 s | about 0.45 to 0.85 GB |
| 1,000,000 | about 270 s | about 4.5 GB (the cheapest shape; two other shapes did not finish in the memory available) |

Three consequences follow:

- **A write holds the store's write lock for its whole duration.** Every other write to the
  same store waits. A write that adds 100,000 rows blocks the store's writers for about
  half a minute.
- **Removing a tuple costs about half as much as adding it on SQLite**, but on PostgreSQL
  removals measured 4 to 7 times slower than on SQLite: 69 to 81 s to remove a tuple whose
  addition had added 100,000 rows. Removals are never capped (below).
- **Reads do not slow down as the index grows.** `check` through a
  {py:class}`zanzibar.Store` took roughly 1 to 4 ms in the same benchmark, whether the store
  had thousands or a million index rows.

## Runtime checks add to the write cost

The runtime invariant checks (*paranoia* levels, off by default; see
[Turn on runtime checks in production](../how-to/runtime-checks.md)) run inside every write,
so they add to its cost. They never run on a read. Three benchmarks measured them, each
comparing the same writes with the checks off and on. The two small-write runs took the
best of three runs; the 2026-10-14 run took the median of three:

| measured | workload | `"residue"` | `"full"` |
| --- | --- | --- | --- |
| 2026-07-26 | 162 and 478 small writes, each committed on its own, on a schema using `and` or `but not`; SQLite | +4.3% and +5.7% | +124% and +303% |
| 2026-10-12 | 160 and 480 small writes, each committed on its own, on a schema with `and` / `but not` and `user:*`; in-memory SQLite | +18.4% and +7.4% | not measured |
| 2026-10-12 | the same method, on a schema with `but not` and object wildcards | +28.3% and +23.8% | not measured |
| 2026-10-14 | one write adding 10,000 or 100,000 index rows, on a schema with no `and` / `but not`; SQLite file, the laptop in the note above | within noise (×1.08, ×0.93) | ×2.2 and ×2.0 on the write, ×3.4 and ×3.0 on removing it again |

Read the table as follows:

- **`"residue"` costs from a few percent to about a quarter of the write time.** It checks
  the bookkeeping behind `and` / `but not` relations and wildcards that the store holds,
  and the wildcard paths the write touched. So its cost grows with how much of that state
  the store holds, not only with the schema; only the wildcard-path part is limited to what
  the write touched. On a schema with none of it there is little to check. Small-write benchmarks like these are noisy: within the
  October run the same check read +18% at one size and +7% at the other, so the gap
  between the July and October figures is not by itself evidence that the check became
  more expensive.
- **`"full"` grows with the size of the whole store.** It reads the entire index on every
  commit, which is why its overhead rose from +124% to +303% as the same workload's store
  grew. Do not run it under production write load.
- **`"fixpoint"` has not been measured.** It adds a second pass over the `and` / `but not`
  updates each write made, on top of everything `"full"` does; working from the code, that
  pass roughly doubles the cost of those updates.

The 2026-07-26 and 2026-10-12 runs did not record the machine they ran on.

## The set engine lives in memory

The set engine keeps no derived state in the database. Each {py:class}`zanzibar.Store`, and
each standalone {py:class}`zanzibar.setengine.SetEngine`, holds the store's tuples as
in-memory bitmaps, built by replaying every stored tuple when it opens and again on
{py:meth}`zanzibar.Store.refresh`. So:

- **Memory grows with the number of tuples, in every process** that has the store open.
  Several instances of an application each hold their own copy.
- **Opening a store costs time in proportion to its tuples.** Rebuilding the set engine of a
  store with a million tuples took about 40 s (2026-10-14). Keep a `Store` open; do not open
  one per request.
- The set engine's memory per tuple has not been measured on its own.

## Two caps on a single write

### The closure fan-out cap

To stop one write from holding the write lock indefinitely, a synchronous write is
refused with {py:exc}`zanzibar.ClosureFanoutExceeded` when any single link it adds to the
index would expand into more index rows than a limit. For each link the count is the one
described above: everything that reaches the subject times everything the object reaches,
plus each of those on its own. Index rows that already exist count too, because the write
still has to update them, so a write that creates few new rows can still be over the
limit. The limit is the `ZANZIBAR_MAX_CLOSURE_FANOUT` environment
variable; the default is 100,000 rows, and `0` disables the cap. The variable is read when
a {py:class}`zanzibar.Store` is opened, so set it before opening the store; changing it
later does not affect a store that is already open, and a value that is not a whole number
of zero or more is an error. The refusal is complete: the tuple is in neither backend and
nothing was written.

The limit applies to each link separately, not to the total a write produces. On a schema
with `and` or `but not`, or with wildcards, one tuple can add several links, so it can
write more rows in total than the limit without being refused.

The default is a bound on the damage one link can do, not a tuning for any workload. By
the table above, a write just under it still holds the lock for about half a minute and
needs up to about 0.85 GB in the writer. If your application cannot tolerate that, lower
the limit.

The cap applies only to **adding** a tuple on a synchronous store. Removals are never
capped, so a large grant can always be revoked. An asynchronous store's catch-up, and
{py:func}`zanzibar.store.build_index` with `bulk=False`, apply an over-limit link anyway and
log a warning, because those tuples are already committed. Until `catch_up()` has applied
such a row, though, a synchronous instance on the same store id applies the backlog as part
of its own writes, under the cap, so every write through it is refused with
`ClosureFanoutExceeded` naming the backlog row. The default bulk
{py:func}`zanzibar.store.build_index`, and so {py:meth}`zanzibar.Store.adopt` by default,
does not check the fan-out cap at all; it still enforces the path-count cap below. How to set the limit and handle a refusal is in
[Cap write fan-out](../how-to/fanout-cap.md).

### The path-count cap

Each index row records how many distinct paths connect its two ends, so that a removal can
be undone exactly. That count is stored as a 32-bit integer, so a write that would push any
count past 2,147,483,647 is refused with {py:exc}`zanzibar.PathCountExceeded`. This is a
storage limit, not a setting, and it applies the same way on SQLite and PostgreSQL. Reaching
it takes a very densely connected graph, for example many overlapping groups nested inside
one another.

Unlike the fan-out cap, it also applies during an asynchronous store's catch-up. There the
tuple is already committed, so the index cannot move past it and **stalls**. A stalled index
is not used: an untokened `check` falls back to the set engine, and a lookup raises
{py:exc}`zanzibar.IndexStalled`. See [Recover a stalled index](../how-to/stall-recovery.md)
and [Consistency: the tuple log, tokens and stalls](consistency.md).

## A refused write is not free

The fan-out cap limits how many rows each link of a write may **touch**, not how much work it
takes to decide that the write is too large. Refusing a write costs:

- the set engine's own admission of the tuple, which also grows with the number of members
  that reach the subject and of objects the object reaches,
- reading every row that reaches the subject and every row the object reaches, before
  counting them, and
- rebuilding the whole set engine from the stored tuples afterwards, because the set engine
  had already accepted the tuple before the graph index refused it.

All three happen while the write lock is held. When the fan-out comes from the product of two
moderate sets, the refusal is quick: a 1,000-member group linked to a 1,000-document folder
was refused in 0.18 s. When it comes from one very large set, it is not:

| refused write (2026-10-14) | time to refuse | peak writer memory |
| --- | --- | --- |
| grant to a group of 100,001 members | 8.4 s | 352 MB |
| grant to a group of 1,000,000 members | 91 s | 3.8 GB |

Of the 91 s, about 40 s was the set-engine rebuild, which grows with the size of the whole
store, not of the refused write, and about 20 s was the set engine's admission. So if your data has very large groups, keep grants to them
rare and expect a refused one to be slow. This section describes the library as it was
measured on 2026-10-14; a release that changes how a refusal is made says so in the
[changelog](../reference/changelog.md).

## Lookups for a userset: a cost that has not been measured

A userset such as `group:eng#member` is a member of itself, as in OpenFGA (see
[Semantics and differences from OpenFGA](semantics-vs-openfga.md)). To include those
answers, the graph index does extra work in two lookups:

- {py:meth}`zanzibar.Store.lookup` for a **userset subject** (for example "what can
  `group:eng#member` view?") on a schema with `and` or `but not` runs a full `check` for
  every relation defined with `and` / `but not`, or built on one (such as
  `viewer from parent` where `viewer` uses `but not`), against every object of that relation's type
  that the index holds, plus one `check` for every relation of the subject's own object.
- {py:meth}`zanzibar.Store.lookup_reverse` on a relation defined with `and` or `but not`
  runs a full `check` for every candidate userset.

Lookups for a plain subject such as `user:alice` are not affected by this extra pass. On
schemas with no `and` or `but not` the extra work is small, with one exception:
{py:meth}`zanzibar.Store.lookup_reverse` on a schema that grants a wildcard userset (such
as `[group:*#member]`) can also go through every entity of that type the index holds. The
cost of the extra pass therefore grows with the number of objects in the store, not with
the size of the answer. This page gives no figures for it. If your application lists
permissions for usersets on a large store with boolean relations, measure it on your own
data first.

## Storage that only grows

- **The tuple log is permanent.** Every write adds a row, removals included, and nothing
  compacts it.
- **The change outbox grows on every write** that changes the index, one row per index row
  added or removed. The library never prunes it for you. See
  {py:func}`zanzibar.graphindex.prune_outbox` and the [database tables](../reference/tables.md)
  reference.

## SQLite or PostgreSQL

Both are supported, for different jobs. MySQL is not supported.

- **SQLite** is for development, tests and single-machine use. It serialises writers itself:
  the library waits up to 10 s for the write lock and retries briefly, and beyond that a
  concurrent writer gets `database is locked` and must retry the transaction.
- **PostgreSQL** is the server option. It must run at the `READ COMMITTED` isolation level,
  its default; a `Store` refuses any other level, `SERIALIZABLE` included, with
  {py:exc}`zanzibar.UnsafeIsolationLevel`. Writers to one store take a row lock, so several
  processes and machines can share a store. See [Run on PostgreSQL](../how-to/postgresql.md).

On either database, **writes to one store are serialised**: one writer at a time, each
holding the lock for as long as its index rows take to write. Write throughput per store is
bounded accordingly. On PostgreSQL, writes to different stores do not block each other;
on SQLite, every writer to the same database file waits for the others, whatever the store.

## When not to use this library

This library is probably the wrong choice if:

- **You need OpenFGA features it does not implement**, such as conditions (`with`) or
  modules, or tuple data with cycles (a group inside itself), which it refuses. See
  [Semantics and differences from OpenFGA](semantics-vs-openfga.md) and the
  [schema language](../reference/schema-language.md) reference.
- **You need an authorization service** that applications in other languages call over the
  network. This is an in-process Python library over your own database.
- **Writes dominate your load: do not use the graph index.** The graph index makes reads
  cheap by doing their work at write time, which is the wrong trade when writes outnumber
  reads. The exception is a simple schema with no `and` / `but not`, where each write adds
  only a few index rows. Otherwise the write cost adds up: in the benchmark above a write
  cost about 0.1 s plus about 0.3 ms per added index row, one write at a time per store, and
  a schema with `and` / `but not` also updates those relations on every write. Granting
  large groups is where the rows multiply: a store kept up with at most about one write
  every 3 s when each added 10,000 rows, and one every 30 s at 100,000.
  - **Use the set engine on its own instead.** It has no per-row cost: a write stores one
    tuple, so its write rate is your database's insert rate. It pays elsewhere. Every read
    computes its answer, and that cost has not been measured for large groups. Every
    process holds all the tuples in memory and replays them when it opens. There is no
    tuple log and there are no tokens, so one process does not see another's writes until
    it calls `rebuild()`. See [Use the backends directly](../how-to/backends-direct.md).
  - **Async mode (`sync=False`) is not a way around it.** It takes the index work out of
    the write, but the index still applies every row later, at the same cost per row. It
    absorbs bursts. Under a rate that stays above what `catch_up()` can apply, the index
    falls further behind for good: untokened reads see an ever older index, and lookups
    with a token raise {py:exc}`zanzibar.LookupNotFresh`. See
    [Use async mode](../how-to/async-tokens.md).
- **You need high write throughput on a single store.** Writes to one store are serialised.
- **You need a database other than SQLite or PostgreSQL**, or an isolation level other than
  `READ COMMITTED`.
- **Your schema changes often.** A schema is fixed for the life of a store; changing it means
  building a new store (see [Change a schema](../how-to/change-schema.md)).
- **You need a mature, stable API.** The library is at version 0.0.x, and any
  release, including a patch release, may change the API. Pin an exact version and read the
  changelog's "Breaking" entries before upgrading (see the
  [changelog](../reference/changelog.md)).

For how the answers themselves are checked, see [How correctness is checked](assurance.md).
