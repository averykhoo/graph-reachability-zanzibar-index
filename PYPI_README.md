# zanzibar-index

Zanzibar-style relationship-based access control (ReBAC) for Python, on top of SQLModel.
Schemas are written in a subset of the [OpenFGA](https://openfga.dev) modelling DSL
(schema 1.1, including the `and` / `but not` operators; no conditions or modules), plus a
few extensions listed under "Schema shapes" below. The package is not affiliated with Google or OpenFGA.

Two evaluation backends give the **same answers** with **opposite cost models**:

* `zanzibar.setengine` stores only the raw tuples and computes memberships on the fly
  with bitmap algebra (roaring bitmaps). Writes are cheap, reads do the work.
* `zanzibar.graphindex` materializes the transitive closure as reference-counted edges,
  so `check` is a single indexed lookup. Writes do the work, reads are cheap.

`zanzibar.store` composes them: an append-only tuple log is the source of truth,
the graph index is a materialized view over it, and a `check` carrying a freshness token
falls back to the set engine when the index is behind that token (see "Freshness tokens
and async mode").

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
from zanzibar.store import Store

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
    store = Store(session, "my-app", schema=SCHEMA)
    # add_tuple(user, relation, object), in OpenFGA's "type:name[#relation]" form
    store.add_tuple("user:alice", "member", "group:eng")
    store.add_tuple("group:eng#member", "viewer", "doc:d1")     # group#member is a viewer
    print(store.check("user:alice", "viewer", "doc:d1"))        # True

    # or six parts: subject_predicate ("..." = the bare user), subject_type, subject_name,
    # relation, object_type, object_name
    store.add_tuple("...", "user", "alice", "banned", "doc", "d1")
    print(store.check("...", "user", "alice", "viewer", "doc", "d1"))  # False

    # lookup: everything alice reaches, read as (type, name, relation) keys
    found = store.lookup("user:alice")
    assert store.result_keys(found) == {
        ("doc", "d1", "banned"), ("group", "eng", "member")}   # no longer doc:d1#viewer
```

Every tuple method (`add_tuple`, `remove_tuple`, `check`) takes either OpenFGA's
`user, relation, object` strings (`"user:alice"`, a userset `"group:eng#member"`, every
user `"user:*"`; objects are `"type:name"`) or the six parts `subject_predicate,
subject_type, subject_name, relation, object_type, object_name`, positionally or by those
keyword names. `lookup("user:alice")` and `lookup_reverse("viewer", "doc:d1")` take the
same two forms. A malformed string raises `MalformedTupleString` (a `ValueError`).

`schema=` also accepts an OpenFGA JSON authorization model, as a `dict` or a JSON string,
bare or wrapped as `{"authorization_model": {...}}` (what an OpenFGA server returns). It is
converted to DSL and stored as DSL, so reopening with the same JSON is accepted.

Each write commits and returns a freshness token. Pass it back as
`check(..., at_least=token)` to read your own writes when the index is maintained
asynchronously (`sync=False`; see "Freshness tokens and async mode").
Reopening a store with `Store(session, "my-app")` reads its persisted schema;
a store's schema is write-once.

### Reading lookup results

`lookup` (what can this subject reach?) and `lookup_reverse` (who can reach this
object's relation?) return a `LookupResult` with five fields:

* `node_ids`: ids of `zanzibar.graphindex.Node` rows. `store.result_keys(result)` turns
  them into `(type, name, predicate)` keys, as above, where `predicate` is the relation,
  or `"..."` for a bare subject such as a user. Results cover every relation the subject
  reaches, usersets on the way included: alice above reaches `group:eng#member` and
  `doc:d1#banned`. From `lookup_reverse`, a userset such as `group:eng#member` means that
  the userset itself is an allowed subject. It does not mean every member is allowed:
  under `but not banned`, a banned member of `group:eng` is still refused, so ask `check`
  about a member rather than expanding the userset. To list the USERS `lookup_reverse`
  allows, take the keys of type `user` (members of a granted group are already listed
  one by one, and refused ones are left out), plus each `user` marker minus the excluded
  keys; never add the members of a userset key, which would re-admit the refused ones.
* `markers`: wildcard grants, as `(type, predicate, variant)` triples. From
  `lookup_reverse`, `("user", "...", "any")` means "every user", from a `[user:*]` tuple.
  The variant `"all"` appears only with `object_wildcard_shapes` (an extension): from
  `lookup`, `("doc", "reader", "all")` means "reader of every doc" (a `doc:*` tuple).
* `implicit_keys` / `implicit_excluded_keys`: the same two parts for answers that have no
  node yet, as `(type, name, predicate)` keys. A userset is a member of itself (as in
  OpenFGA), so `lookup_reverse("viewer", "doc:d1")` lists `doc:d1#viewer` even before any
  tuple names it. `store.result_keys(result)` and `store.excluded_keys(result)` include
  them, so read results through those two.
* `excluded_node_ids`: subjects a marker would cover but who are refused (for example by
  `but not banned`). `store.excluded_keys(result)` gives their keys. Subtract them from
  the marker yourself: "every user except mallory".

Ids are row ids and are never reused. Translate a result before the next write:
`result_keys` / `excluded_keys` raise `StaleLookupIds` (a `KeyError`) for an id whose node
a later write removed. A subject that a marker already covers may also
be listed in `node_ids` (the set engine leaves it out), so compare results by what they
cover: the keys, plus every subject of a marker's shape, minus the excluded keys.

A standalone `zanzibar.setengine.SetEngine` returns a `SetLookupResult` (a dataclass) with
the same five fields, in its own id
space: markers are `(type, predicate)` pairs and ids are in-memory handles. Translate with
`engine.result_keys(res)` and `engine.excluded_keys(res)` before the next write and in the
same engine instance: once any write frees an id, the engine is rebuilt, or the result is
handed to another instance, both raise `StaleLookupIds` instead of translating. Send both with the markers, and subtract the exclusions exactly as
above; markers without their exclusions grant too much.

## Freshness tokens and async mode

Every write returns a **freshness token**: an `int` that only grows within a store. Treat
it as opaque; the only things to do with one are compare it and pass it back.
`store.watermark()` returns the newest one. A token is a read-your-writes demand:
`check(..., at_least=token)` answers as of that write or later. Adding a tuple that is
already present changes nothing and returns the current `store.watermark()`, which may be
another write's token; it is still a correct demand, because the tuple was already there.

By default a `Store` is synchronous (`sync=True`): a write updates the graph index in the
same transaction, so that instance's reads see it at once and need no token.

With `Store(session, "my-app", sync=False)` a write only appends to the log (and updates the
in-memory set engine). The graph index catches up when something calls `store.catch_up()`.
**No background worker ships with the library**: schedule `catch_up()` yourself, for
example in a process of its own:

```
import time
from sqlmodel import Session
from zanzibar import Store, ZanzibarError

with Session(engine) as session:
    worker = Store(session, "my-app", sync=False)
    while True:
        try:
            worker.catch_up()            # applies every committed write; returns how many
        except ZanzibarError:
            print(worker.stall_error)    # see "Stall recovery" below
        time.sleep(1.0)
```

While the index is behind (`store.lag()` counts the log rows it has not applied):

* An untokened `check` or `lookup` reads the index as it is. It can be stale in both
  directions: a new grant reads as denied, and **a revoked grant still reads as allowed**
  until `catch_up()` applies the removal.
* `check(..., at_least=token)` answers from the set engine when the index is behind the
  token, so it always reflects that write. Use a token for any decision that must see a
  revoke.
* `lookup` / `lookup_reverse` with `at_least=` have no such fallback: they raise
  `LookupNotFresh` until the index has caught up.
* A token this session cannot see yet (committed after its read transaction began) raises
  `StaleRead` from `check`; call `store.refresh()` and retry. The message also says when
  the token belongs to another store, or was never issued.

**`sync` is a per-instance choice, and is not stored.** Reopening a store with
`Store(session, "my-app")` gives a synchronous instance, but it does not apply a backlog
that async instances left: it applies it at its own next write or `catch_up()`. So a
read-only instance of an async store must run `catch_up()` itself or pass tokens.

## Stall recovery

`catch_up()` stops at a log row it cannot apply and records a **stall**, visible to every
instance: `store.index_stalled` is `True` and `store.stall_error` names the log row and
the error. While it lasts, an untokened `check` answers from the set engine (correct,
slower), and an untokened `lookup` / `lookup_reverse` raises `IndexStalled`.

A stall from a transient error (a lock timeout, a lost connection) clears at the next
successful `catch_up()`. A row the index can never apply (`PathCountExceeded`) does not
clear, not even after a later write removes the tuple, because that removal waits behind
it. Remove the tuple at the source with `store.remove_tuple(...)` (writes still work while
stalled), stop the `catch_up()` worker, then rebuild the index in place:
`zanzibar.store.rebuild_index(session, "my-app")`, which commits.

## Wildcards

The user `"user:*"` means every user. A wildcard tuple is accepted only where the
relation's restriction lists `user:*`, as in `define viewer: [user, user:*] but not banned`;
anywhere else the write raises `AdmissionRejected`. `but not` still excludes individuals.
With that schema:

```
store.add_tuple("user:*", "viewer", "doc:d2")
store.add_tuple("user:mallory", "banned", "doc:d2")
store.check("user:bob", "viewer", "doc:d2")       # True
store.check("user:mallory", "viewer", "doc:d2")   # False
```

`lookup_reverse("viewer", "doc:d2")` reports the grant as the marker
`("user", "...", "any")`, and `store.excluded_keys(result)` holds
`("user", "mallory", "...")`: see "Reading lookup results" above.

## Exceptions

Every exception below imports from the top level (`from zanzibar import AdmissionRejected`).
Each derives from `zanzibar.ZanzibarError` and keeps the builtin base shown, so
`except ZanzibarError` catches all of them and `except ValueError` still works.

| exception | base | raised when |
| --- | --- | --- |
| `AdmissionRejected` | `ValueError` | a write is refused: an undeclared type or relation, a user the restriction does not admit, a cycle, removing a tuple that is not stored |
| `MalformedTupleString` | `ValueError` | a `"type:name#relation"` argument does not parse |
| `SchemaError` | `ValueError` | the schema text is refused; the message says what to write instead |
| `ShapeNoLongerAccepted` | `ValueError` | a `SchemaError` for a shape 0.0.4 and earlier accepted; `.instead` is the rewrite that keeps its meaning |
| `PersistedSchemaRefused` | `ValueError` | a store's STORED schema uses such a shape, whichever call opens it (`Store`, `SetEngine`, `build_index`, ...); `.instead` is the rewrite, which needs a new store id |
| `CyclicDerivedDependency` | `ValueError` | a relation recurses through `and` / `but not` (see below) |
| `SchemaMismatch` | `ValueError` | a store is opened with a schema other than the one it was created with |
| `StoreNotFound` | `KeyError` | `Store(session, id)` without `schema=` names a store that does not exist |
| `TablesNotCreated` | `RuntimeError` | `SQLModel.metadata.create_all(engine)` was not run |
| `TablesOutdated` | `RuntimeError` | a `Store` opens a SQLite file whose `zanzibar_node` table was created by 0.0.x (ids reusable) |
| `StaleLookupIds` | `KeyError` | `result_keys` / `excluded_keys` on a lookup result whose ids may have been reused: after a write, a rebuild, or on another instance |
| `StaleRead` | `RuntimeError` | a token cannot be satisfied (see "Freshness tokens") |
| `LookupNotFresh` | `RuntimeError` | a tokened lookup while the index lags (a `StaleRead`) |
| `IndexStalled` | `RuntimeError` | an untokened lookup while the index is stalled (a `LookupNotFresh`) |
| `ClosureFanoutExceeded` | `ValueError` | a write would add too many index rows (an `IndexResourceLimit`, an `AdmissionRejected`) |
| `PathCountExceeded` | `ValueError` | a write would overflow a path count (an `IndexResourceLimit`, an `AdmissionRejected`) |
| `UnloggedWriteRefused` | `RuntimeError` | a standalone `SetEngine` writes to a store a `Store` owns |
| `UnloggedTuplesPresent` | `RuntimeError` | a `Store` opens over tuples a standalone `SetEngine` wrote |
| `IndexExists` | `ValueError` | `build_index` targets an index that already exists |
| `MissingDeltaProcessor` | `ValueError` | the apply step is driven by hand without a `zanzibar.graphindex.DeltaProcessor` on a schema with `and` / `but not` |
| `UnsafeIsolationLevel` | `RuntimeError` | a PostgreSQL session is not at `READ COMMITTED` |

`InvariantViolation` (an `AssertionError`) is deliberately **not** a `ZanzibarError`: it
means the stored index is corrupt (it comes from the `paranoia` checks), and a handler for
refusals must not swallow it. `UnprovenExtensionWarning` is a warning, not an exception.

## Sessions, transactions and threads

* **Give each `Store` a `Session` of its own.** A `Store` owns its transactions: it
  commits when it opens and on every successful write, and rolls back on a refused write
  and in `refresh()`. It refuses a session that has pending ORM changes (`ValueError`), so
  it never commits or discards rows of yours. A committed grant stays committed even if
  your own code later rolls back.
* **One `Session` per thread**, and never share a `Store` between threads. Several
  instances (threads, processes, machines) may open the same store id; writers take a
  per-store lock, so writes to one store are serialised.
* **A standalone `SetEngine` is the opposite: it never commits.** Commit the session
  yourself after its writes.
* **PostgreSQL** needs `READ COMMITTED`, its default:
  `create_engine(url, isolation_level="READ COMMITTED")` if you set one. **SQLite**
  serialises writers itself; a concurrent writer can get `database is locked` and must
  retry.

## Memory and storage

* **State is held in memory and rebuilt on open.** Each `Store` (and each standalone
  `SetEngine`) keeps the set engine's bitmaps in memory, built by replaying every stored
  tuple of the store when it opens and again on `refresh()`. Opening costs time and memory
  in proportion to the store's tuples, in every instance: keep a `Store` open rather than
  opening one per request.
* **The tuple log is permanent.** Every write adds a row; nothing compacts it.
* **The delta outbox grows on every write** and is never pruned for you. Prune it from
  time to time:

  ```
  from zanzibar.graphindex import outbox_watermark, prune_outbox

  prune_outbox(session, "my-app", outbox_watermark(session, "my-app"))
  session.commit()
  ```

  This form is safe with `paranoia` off (the default). With `paranoia` on, read
  `help(prune_outbox)` first: rows a checker has not read yet must stay.

## Things to know before you use it

* **Tables.** The library declares its tables on SQLModel's default metadata, all named
  `zanzibar_*`, so `SQLModel.metadata.create_all(engine)` creates them next to your own.
  A table of yours that reuses one of those names is a loud `InvalidRequestError`,
  whichever is declared first; the two are never silently merged. SQLAlchemy's message
  suggests `extend_existing=True`: do not, rename your table instead.
* **One write path per store id.** Write a store that a `Store` owns through the
  `Store` only. A standalone `SetEngine` opened on the same id can read it, but its
  `add_tuple` / `remove_tuple` raise `UnloggedWriteRefused`, and it must be given the
  store's own schema (`zanzibar.store.open_set_engine(session, id)` loads it); a
  different one raises `SchemaMismatch`. A `Store` will not
  take over an id that a standalone `SetEngine` already wrote to (`UnloggedTuplesPresent`).
  To adopt such a store, call `save_schema(session, id, schema)`, commit, then
  `build_index(session, id)`, then open `Store(session, id)`.
* **Databases.** SQLite and PostgreSQL only. On PostgreSQL the session must use
  `READ COMMITTED`; any other isolation level is refused at construction.
* **Runtime checks.** `Store(..., paranoia="residue")` or the
  `ZANZIBAR_PARANOIA=residue` environment variable turns on a cheap runtime corruption
  detector for the index. It is off by default and recommended for anything
  security-sensitive.
* **Schema shapes.** Conditions (`with`) and modules are not supported. Refused shapes
  come with an explanation of what to write instead; for example, as in OpenFGA, a `from`
  tupleset must be a direct relation. Only schema 1.1 is implemented: the header is
  optional, but a `schema` line naming any other version (`schema 1.2` included) is
  refused. That is stricter than OpenFGA, which also accepts `1.2`. As in OpenFGA, a
  `model` / `schema 1.1` / `relations` line must stand alone (a comment goes on its own
  line), every type a restriction names must be declared with a `type` line, and
  `but not` may not share a level with `or` / `and`: write
  `(a or b) but not c` or `a but not (b or c)`, never `a or b but not c`. Wildcard usersets
  (`[group:*#member]`), wildcard tuplesets (`parent: [folder:*]`) and object wildcards go
  beyond OpenFGA. They work, but they are outside the proved fragment and emit
  `UnprovenExtensionWarning`. Also beyond OpenFGA's DSL syntax, and accepted here: more than
  one `[...]` block in a definition (`[user] or [group#member]`), a `[...]` block that is not
  the first operand (`editor or [user]`, `viewer but not [user:*]`), no `model` /
  `schema 1.1` header, and a `define` with no `relations` line above it. A schema using them
  may not load in OpenFGA's own tools.
* **"All" does not imply "some" when there are none.** A grant on every instance of a
  type reaches a grant on "any" instance only through an instance that exists. With
  `object_wildcard_shapes=frozenset({("folder", "viewer")})` (so `folder:*` can hold a
  viewer grant), `doc`
  declaring `define parent: [folder, folder:*]` and `define viewer: viewer from parent`,
  and the tuples `alice viewer folder:*` and `folder:* parent doc:1`: while no folder is
  stored, alice cannot view `doc:1`. Once any folder exists, she can. This strict reading
  is the current mode on both backends; a lenient mode may come later.
* **No recursion through `and` / `but not`.** A relation that reaches itself through an
  operator, such as `define viewer: ([user] or viewer from parent) but not blocked`, is
  refused by the graph index and so by `Store` (`CyclicDerivedDependency`), while a
  standalone `zanzibar.setengine.SetEngine` accepts it. The usual rewrite recurses on a plain
  relation and applies the operator on top:
  `define viewer_base: [user] or viewer_base from parent` then
  `define viewer: viewer_base but not blocked`. It is **not** the same schema: `blocked`
  then applies only at the object you query, not at every folder above it.
* **Tuple data must be acyclic.** A write that would close a cycle, such as group `a`
  inside group `b` inside group `a`, a group inside itself, or a folder that is its own
  ancestor, is refused with `AdmissionRejected` by both backends. OpenFGA accepts such
  tuples, so check imported data for cycles first.
* **A userset is a member of itself, as in OpenFGA, with one exception.** `doc:1#banned` is
  a member of `doc:1#banned`, and so of anything built on it: with
  `define vx: [user, doc#banned] but not banned` and the tuple `doc:1#banned vx doc:1`,
  checking `doc:1#banned` for `vx` on `doc:1` is denied (it was allowed before 0.1.0).
  Lookups list such usersets too, so `lookup_reverse("viewer", "doc:d1")` includes
  `doc:d1#viewer` itself. The exception: with `define parent: [folder, team]` and
  `define x: viewer from parent` where `team` declares no `viewer`, checking
  `team:1#viewer` for `x` on a doc whose parent is `team:1` is allowed here, while OpenFGA
  rejects the query (`relation 'team#viewer' not found`). Plain users and `user:*` are
  never affected.
* **Reads are lenient; writes are strict.** A write naming an undeclared type or relation,
  or a malformed name, raises `AdmissionRejected`. A `check` with the same mistake returns
  `False` with no error, so a typo in a relation name reads as "denied". On a read,
  `None` as the subject predicate means the bare subject, like `"..."`. A typo in the
  SCHEMA, such as `define viewer: [usr]` with no `type usr`, is refused when the schema is
  parsed (`SchemaError`, a `ValueError`), before any write.
* **Write cap.** A single write that would add more than `ZANZIBAR_MAX_CLOSURE_FANOUT`
  closure edges (default 100,000; `0` disables) is refused with `ClosureFanoutExceeded`.
  The cap is checked only when the index is maintained synchronously (the default):
  the refused write then lands in neither backend. With `sync=False` the write is
  accepted and the index materialises it anyway when it catches up, logging a warning.
* **Public API.** Each subpackage's `__all__` is the public surface. Underscore-prefixed
  names that happen to be re-exported are internal. `Store`, `LookupResult`,
  `parse_openfga_schema` and every exception also import from the top level
  (`from zanzibar import Store, ZanzibarError`), lazily.
* **Exceptions.** See "Exceptions" above: `except ZanzibarError` catches every refusal,
  and `InvariantViolation` (corruption) is deliberately outside it.

## Documentation

Design docs, the correctness argument and the Lean proofs live in the repository:
<https://github.com/averykhoo/graph-reachability-zanzibar-index>. Start at
[`docs/architecture/overview.md`](https://github.com/averykhoo/graph-reachability-zanzibar-index/blob/master/docs/architecture/overview.md).

## License

Apache-2.0. See `LICENSE`.
