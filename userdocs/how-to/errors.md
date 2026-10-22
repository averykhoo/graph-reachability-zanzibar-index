# Handle errors

Almost every exception the library raises on purpose derives from
{py:exc}`zanzibar.ZanzibarError`, and every one of them can be imported from the top level
(`from zanzibar import ...`), which is their one public home. Every one also keeps a
builtin base class (`ValueError`, `KeyError` or `RuntimeError`), so existing
`except ValueError:` code keeps working. A few
deliberate errors are not `ZanzibarError`s at all; they are listed under
[What `except ZanzibarError` does not catch](#what-except-zanzibarerror-does-not-catch).

This page groups the exceptions into four kinds by what you should do about them, and
names the ones you are most likely to meet. The
[exceptions reference](../reference/exceptions.md) lists every class, with when it is
raised, its base classes and its attributes.

## Catch everything the library refuses

The examples on this page use this store:

```python
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store, ZanzibarError

SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
"""

for leftover in ("errors.db", "empty.db"):     # start from empty files each run
    Path(leftover).unlink(missing_ok=True)
engine = create_engine("sqlite:///errors.db")
SQLModel.metadata.create_all(engine)
store = Store(Session(engine), "my-app", schema=SCHEMA)
```

`except ZanzibarError` catches every refusal, limit and freshness error. A refused write
changes nothing, and the store stays usable afterwards:

```python
try:
    store.add_tuple("user:alice", "editor", "doc:1")   # doc declares no "editor"
except ZanzibarError as error:
    print(type(error).__name__)  # -> 'AdmissionRejected'

store.add_tuple("user:alice", "viewer", "doc:1")
print(store.check("user:alice", "viewer", "doc:1"))  # -> True
```

Some exceptions derive from others, so when you catch several, put the more specific one
first. For example, {py:exc}`zanzibar.ClosureFanoutExceeded` is also an
{py:exc}`zanzibar.AdmissionRejected`, and {py:exc}`zanzibar.IndexStalled` is also a
{py:exc}`zanzibar.LookupNotFresh` and a {py:exc}`zanzibar.StaleRead`. The
[hierarchy](../reference/exceptions.md#hierarchy) shows them all.

## Bad input: fix the request, do not retry

These mean the request itself is wrong. Retrying it gives the same answer. In a web
service, they usually become a 400-style response, or a bug in the code that built the
request.

- {py:exc}`zanzibar.AdmissionRejected`: a write was refused, for example because the tuple
  names a relation the schema does not declare, would create a cycle, or removes a tuple
  that is not stored.
- {py:exc}`zanzibar.MalformedTupleString`: a `"type:name"` or `"type:name#relation"`
  argument does not have that shape.

```python
from zanzibar import AdmissionRejected, MalformedTupleString

try:
    store.add_tuple("alice", "viewer", "doc:1")          # missing the "user:" part
except MalformedTupleString:
    print("malformed")  # -> 'malformed'

try:
    store.remove_tuple("user:bob", "viewer", "doc:1")    # bob was never added
except AdmissionRejected as error:
    print(str(error).startswith("non-existent tuple cannot be removed"))  # -> True
```

Reads are lenient where writes are strict: a `check` that names an undeclared relation
returns `False` instead of raising. So a typo in a relation name reads as "denied":

```python
print(store.check("user:alice", "veiwer", "doc:1"))  # -> False
```

### Resource limits: change the write, or the limit

{py:exc}`zanzibar.ClosureFanoutExceeded` and {py:exc}`zanzibar.PathCountExceeded` are
`AdmissionRejected`s for a valid write that is too large for the graph index. On a
synchronous store the write is refused completely: it is in neither backend. Retrying the
same write does not help; split it, or raise the limit. See
[Cap write fan-out](fanout-cap.md).

While such a row, written by a `sync=False` instance, waits in the log, every write
through a `sync=True` instance of the same store fails with the same exception, about
that row rather than yours; see
[A pending row can block every synchronous write](fanout-cap.md#a-pending-row-can-block-every-synchronous-write).

## Schema problems: fix the schema

These are raised when a schema is parsed or a store is opened. They are setup errors, not
something to handle per request.

- {py:exc}`zanzibar.SchemaError`: the schema text is refused. The message
  says what is wrong and, for a shape the library does not accept, what to write instead.
  See [Rewrite a refused schema shape](rewrite-refused-shape.md).
- {py:exc}`zanzibar.CyclicDerivedDependency`: a relation that uses `and` or `but not`
  depends on itself. It is a `ValueError` but **not** a `SchemaError`, so
  `except SchemaError` does not catch it. The same is true of
  {py:exc}`zanzibar.UnsupportedByGraphIndex`, raised when a wildcard feature reaches a
  relation that uses `and` or `but not`.
- {py:exc}`zanzibar.SchemaMismatch`: you opened an existing store with a
  different schema from the one it was created with. Schemas cannot be changed; see
  [Change a schema](change-schema.md).

```python
from zanzibar import SchemaError, SchemaMismatch, parse_openfga_schema

try:
    parse_openfga_schema("type user\ntype doc\n  relations\n    define viewer: [usr]\n")
except SchemaError as error:
    print(str(error))  # -> "doc#viewer: restriction [usr] names an undeclared type 'usr'; declare it (type usr) or fix the spelling"

try:
    Store(Session(engine), "my-app", schema=SCHEMA.replace("[user]", "[user, doc#viewer]"))
except SchemaMismatch:
    print("schemas are write-once")  # -> 'schemas are write-once'
```

A relation that uses `but not` and recurses through the side it keeps (here
`viewer from parent`) is refused with `CyclicDerivedDependency`, which an
`except SchemaError` lets through. Catch it by name, or catch `ZanzibarError`:

```python
from zanzibar import CyclicDerivedDependency

FOLDERS = """
model
  schema 1.1
type user
type folder
  relations
    define parent: [folder]
    define blocked: [user]
    define viewer: ([user] or viewer from parent) but not blocked
"""

try:
    parse_openfga_schema(FOLDERS)
except (SchemaError, CyclicDerivedDependency) as error:
    refusal = error
print(type(refusal).__name__)  # -> 'CyclicDerivedDependency'
print(isinstance(refusal, SchemaError))  # -> False
print(isinstance(refusal, ZanzibarError))  # -> True
```

To fix the schema, see
[Recursion through `and` or `but not`](rewrite-refused-shape.md#recursion-through-and-or-but-not).
The rest of this kind ({py:exc}`zanzibar.ShapeNoLongerAccepted`,
{py:exc}`zanzibar.PersistedSchemaRefused`, {py:exc}`zanzibar.DoublyBridgedShapeError`) are
in the [schema errors reference](../reference/exceptions.md#schema-errors).

## Setup and configuration: fix the deployment

These come from how the database, the tables or the store were set up. Fix the
configuration; retrying does not help.

- {py:exc}`zanzibar.TablesNotCreated`: the `zanzibar_*` tables are missing. Run
  `SQLModel.metadata.create_all(engine)` after importing the library. Its `missing`
  attribute lists the missing tables.
- {py:exc}`zanzibar.TablesOutdated`: the `zanzibar_*` tables in a SQLite file were created
  by a 0.0.x release, which made them in an older layout. Create the tables in a new
  database file and write the tuples again. Until 0.1.0 is released, a build from source
  also reports version 0.0.5, so check how the file was made, not the version number; see
  the [note on the upgrade page](upgrade-0.1.md).
- {py:exc}`zanzibar.StoreNotFound`: `Store(session, store_id)` without a
  schema names a store that does not exist in this database. Create it once by passing
  `schema=`, or check that the session points at the right database.

The others of this kind are {py:exc}`zanzibar.UnsafeIsolationLevel` (see
[Run on PostgreSQL](postgresql.md)), {py:exc}`zanzibar.WriteLockUnsafe`, and
{py:exc}`zanzibar.UnloggedTuplesPresent` / {py:exc}`zanzibar.UnloggedWriteRefused` (see
[Bulk-load or adopt an existing store](bulk-load-adopt.md)); the
[reference](../reference/exceptions.md#opening-a-store) describes each. A few more come
only from driving the backends or the offline index tools yourself; they are listed in
[Use the backends directly](backends-direct.md#errors-only-the-backends-raise).

```python
from zanzibar import StoreNotFound, TablesNotCreated

try:
    Store(Session(engine), "no-such-store")
except StoreNotFound as error:
    print(error.store_id)  # -> 'no-such-store'

empty = create_engine("sqlite:///empty.db")        # tables never created
try:
    Store(Session(empty), "my-app", schema=SCHEMA)
except TablesNotCreated as error:
    print("zanzibar_relation_tuple" in error.missing)  # -> True
```

## Freshness: refresh and retry

These mean a read could not be answered as fresh as you asked. Nothing is wrong with the
data, and the same request usually succeeds after a refresh or once the index catches up.
See [Use async mode and freshness tokens](async-tokens.md).

- {py:exc}`zanzibar.StaleRead`: a `check` or `expand` with `at_least=token` names a write
  this session cannot see yet. Call {py:meth}`zanzibar.Store.refresh` and retry once. If
  the retry fails the same way, the token is wrong, and retrying further will not help.
  The message's "evaluator" is the store's in-memory set engine.
- {py:exc}`zanzibar.LookupNotFresh`: a `lookup` or `lookup_reverse` with
  `at_least=` while the index is behind that write. Run `catch_up()`, or wait for your
  worker to, and retry. For a single decision, `check(..., at_least=token)` answers anyway.
- {py:exc}`zanzibar.IndexStalled`: a `lookup` or `lookup_reverse`
  without a token while the index is stalled. See
  [Recover a stalled index](stall-recovery.md).

{py:exc}`zanzibar.WatermarkGap` (refresh and retry) and {py:exc}`zanzibar.StaleLookupIds`
(run the lookup again; see [Find who can access what](query-access.md)) belong here too;
see the [freshness reference](../reference/exceptions.md#freshness-and-the-index).

```python
from zanzibar import StaleRead

token = store.add_tuple("user:bob", "viewer", "doc:1")
try:
    store.check("user:bob", "viewer", "doc:1", at_least=token + 1000)   # not issued yet
except StaleRead as error:
    print("was not issued yet" in str(error))  # -> True
print(store.check("user:bob", "viewer", "doc:1", at_least=token))  # -> True
```

(foreign-token-handling)=
### A token from another store

{py:exc}`zanzibar.ForeignToken`, a `StaleRead`, means the token was returned by a write to
a *different* store. Every tokened read refuses it (`check`, `lookup`, `lookup_reverse`,
`expand`), whatever its value, and the message starts with that cause and names both
stores. **Do not retry**: nothing about this store can make the token valid. Pass a token
from one of this store's own writes. If a handler of yours retries on `StaleRead`, catch
`ForeignToken` before it. A lookup with a token from another store raises `ForeignToken`,
not `LookupNotFresh`.

```python
from zanzibar import ForeignToken

other = Store(Session(engine), "other-app", schema=SCHEMA)
foreign = other.add_tuple("user:carol", "viewer", "doc:9")
try:
    store.check("user:bob", "viewer", "doc:1", at_least=foreign)
except ForeignToken as error:
    print((error.issued_by, error.store_id))  # -> ('other-app', 'my-app')
```

## What `except ZanzibarError` does not catch

- {py:exc}`zanzibar.InvariantViolation`, an `AssertionError`. It means the stored index is
  corrupt, not that a request was refused, so it is kept out of `ZanzibarError` on purpose.
  Let it reach your error reporting. When it comes from the check that runs after a commit,
  the current version raises `sqlalchemy.exc.InvalidRequestError` instead, with the
  `InvariantViolation` as its `__context__`, and that `Store` object cannot be used again.
  See [Turn on runtime checks in production](runtime-checks.md#when-a-check-fails).
- {py:class}`zanzibar.UnprovenExtensionWarning`, a warning, not an exception. It is
  emitted for a schema that uses a wildcard feature beyond OpenFGA's; see
  [the section below](#silence-the-wildcard-extension-warning-or-make-it-an-error).
- A misspelt `ZANZIBAR_PARANOIA` or `ZANZIBAR_MAX_CLOSURE_FANOUT`, or an invalid
  `paranoia=` argument, raises a plain `ValueError` when the store opens.
- Errors from the database driver pass through unchanged. On SQLite, a write that
  competes with another writer can fail with `sqlite3.OperationalError: database is
  locked` (wrapped by SQLAlchemy); the store has rolled back, and the write can be retried.
- A `Store` refuses a `Session` that has unsaved changes of yours (objects added but not
  committed) with a plain `ValueError`, because it commits and rolls back the session
  itself. Give each `Store` a session of its own.
- An `at_least=` that is not an `int` (a string, a float, `True`) raises a plain
  `TypeError`, and a negative one a plain `ValueError`. Pass the token exactly as a write
  returned it.
- Any other `ValueError` that is not a `ZanzibarError`, escaping from a write, is a bug in
  the library or in how it is being called, not a refusal. Report it.

## Silence the wildcard-extension warning, or make it an error

A schema that uses a wildcard feature beyond OpenFGA's (for example `[group:*#member]`)
emits {py:class}`zanzibar.UnprovenExtensionWarning` when a store opens. It is a
`UserWarning`, so you control it with the standard {py:mod}`warnings` module, by its class.
[Wildcard extensions beyond OpenFGA](../explanation/wildcard-extensions.md) explains when
each choice makes sense.

To silence it where you have chosen the extension on purpose, filter it around the code
that opens the store, and say in a comment which extension you rely on:

```python
import warnings
import zanzibar

EXT_SCHEMA = """
model
  schema 1.1

type user

type group
  relations
    define member: [user]

type doc
  relations
    define viewer: [user, group:*#member]
"""

ext_engine = create_engine("sqlite://")
SQLModel.metadata.create_all(ext_engine)

with warnings.catch_warnings(record=True) as seen:
    warnings.simplefilter("always")
    # We rely on [group:*#member] ("every member of any group") on purpose.
    warnings.filterwarnings("ignore", category=zanzibar.UnprovenExtensionWarning)
    ext_store = Store(Session(ext_engine), "ext-quiet", schema=EXT_SCHEMA)

print(len(seen))  # -> 0
```

To make it an error, for example in your test suite, turn the warning into an exception.
Opening a store with such a schema then raises it:

```python
with warnings.catch_warnings():
    warnings.simplefilter("error", zanzibar.UnprovenExtensionWarning)
    try:
        Store(Session(ext_engine), "ext-strict", schema=EXT_SCHEMA)
        escalated = False
    except zanzibar.UnprovenExtensionWarning:
        escalated = True

print(escalated)  # -> True
```

In a pytest suite the same effect comes from the `filterwarnings` setting, for example
`error::zanzibar.UnprovenExtensionWarning`.
