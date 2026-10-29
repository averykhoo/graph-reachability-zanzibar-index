# Configuration

Everything you can set: two environment variables and the arguments of
{py:class}`zanzibar.Store` and {py:meth}`zanzibar.Store.adopt`. The library reads no
configuration file and no other environment variable.

## Environment variables

| variable | values | default | read by |
| --- | --- | --- | --- |
| `ZANZIBAR_PARANOIA` | `off`, `residue`, `full`, `fixpoint`; or `1` / `true` / `yes` / `on` (= `full`) and `0` / `false` / `no` / `off` (= `off`); case-insensitive | `off` | every {py:class}`~zanzibar.Store` when it is created, unless `paranoia=` is passed |
| `ZANZIBAR_MAX_CLOSURE_FANOUT` | a whole number of index rows; `0` disables the cap | `100000` | the graph index when a {py:class}`~zanzibar.Store` opens it |

An empty value counts as unset. A value that cannot be parsed is a {py:exc}`ValueError`
when the store is created; it never falls back to the default.

Both are read when the store is created, so set them before that. Changing one later does
not change a store that is already open.

### `ZANZIBAR_PARANOIA`

Selects the runtime invariant checks that run inside each of the store's commits. An
explicit `paranoia=` argument to {py:class}`~zanzibar.Store` always wins over the
variable, so a deployment cannot override a choice made in code.

(paranoia-levels)=
The levels:

| level | what runs | cost |
| --- | --- | --- |
| `off` | nothing | none |
| `residue` | before each commit: a check of the index's stored wildcard and exclusion state, and, on a schema with object wildcards, a check of the wildcard paths through the objects the write touched. The recommended production setting. | a few percent to roughly +25% on synchronous per-write commits, depending on the schema and the store's size (measured 2026-07 and 2026-10); reads are unaffected |
| `full` | before each commit: every state invariant plus a verifier of the write's effect. After each commit: the state invariants again. | grows with the store's size (it more than doubled the cost of writes, measured 2026-07); for tests and pre-release runs, not production load |
| `fixpoint` | everything in `full`, plus a check that each `and` / `but not` update reached a fixed point | roughly doubles the cost of those updates; for diagnosis only. Only the explicit word `fixpoint` selects it. |

A failed check raises {py:exc}`zanzibar.InvariantViolation`. When the check that fails is
the one before the commit, at any level, the commit does not happen and the store is rolled
back. At `full` and `fixpoint` the check after the commit runs once the write is already
committed, so when it fails the write stays in the database and the error reports
corruption that is already stored; the message says the transaction is committed (see
[When a check fails](../how-to/runtime-checks.md#when-a-check-fails)).

The variable's name is also exported as `zanzibar.store.PARANOIA_ENV_VAR`. To choose and
roll out a level, see [Turn on runtime checks in production](../how-to/runtime-checks.md).

### `ZANZIBAR_MAX_CLOSURE_FANOUT`

The most index rows any single link that a synchronous write adds to the graph index may
touch: everything that reaches the link's subject times everything its object reaches,
plus each of those on its own, counting rows that already exist. The cap applies to each
link separately, so on a schema with `and`, `but not` or wildcards one tuple, which can add
several links, may write more rows in total. A write over the
cap raises {py:exc}`zanzibar.ClosureFanoutExceeded`, and nothing is written: not to the
tuple log, not to either backend. It bounds how long one write holds the store's write
lock; it is not an access rule, and a revoking write (such as a `but not` ban) is capped
like any other. Removing a tuple is never capped.

The cap applies only where its refusal can reach the writer. Rows that are already in the
tuple log are never refused: {py:meth}`Store.catch_up <zanzibar.Store.catch_up>` (the
asynchronous schedule) and {py:func}`~zanzibar.store.build_index` with `bulk=False` apply an
over-cap row and log a warning on the `zanzibar.graphindex.core` logger, and the bulk
builder (`bulk=True`, the default) does not apply the cap at all.
{py:class}`~zanzibar.Store` has no argument for the cap; the variable is the only way to
change it for a store. To pick a value and handle the refusal, see
[Cap write fan-out](../how-to/fanout-cap.md).

```python
import os
from sqlmodel import SQLModel, Session, create_engine
import zanzibar
import zanzibar.store  # registers the zanzibar_* tables before create_all

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

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)

os.environ["ZANZIBAR_MAX_CLOSURE_FANOUT"] = "3"     # a tiny cap, to show the refusal
try:
    with Session(engine) as session:
        store = zanzibar.Store(session, "fanout-demo", schema=SCHEMA)
        for name in ["a", "b", "c", "d"]:
            store.add_tuple(f"user:{name}", "member", "group:eng")
        try:
            store.add_tuple("group:eng#member", "viewer", "doc:1")   # 4 new rows > 3
        except zanzibar.ClosureFanoutExceeded:
            refused = True
        print(refused)  # -> True
        print(store.check("user:a", "viewer", "doc:1"))  # -> False
finally:
    del os.environ["ZANZIBAR_MAX_CLOSURE_FANOUT"]
```

## `Store` arguments

`Store(session, store_id, *, schema=None, object_wildcard_shapes=frozenset(), ops=<default>, sync=True, paranoia=None)`

| argument | type | default | meaning |
| --- | --- | --- | --- |
| `session` | {py:class}`sqlmodel.Session` | required | the session the store reads and writes through. Give each store its own: the store commits when it opens and on every successful write, and rolls back on a refused write and in `refresh()`. A session with pending changes is refused ({py:exc}`ValueError`). |
| `store_id` | `str` | required | the store's key in the database. Any string with at least one non-whitespace character; the identifier character rules for tuples do not apply. Anything else raises {py:exc}`zanzibar.AdmissionRejected`. |
| `schema` | `str`, `dict` or `None` | `None` | the authorization model: OpenFGA DSL text, or an OpenFGA JSON model as a `dict` or JSON string (also wrapped as `{"authorization_model": {...}}`). Pass it to create the store; it is stored once and never changes. Leave it out to open an existing store ({py:exc}`zanzibar.StoreNotFound` if there is none). A different schema for an existing store raises {py:exc}`zanzibar.SchemaMismatch`; the same schema reformatted, with comments, or with its type blocks, `define` lines or restriction lists reordered is accepted. Swapping the operands of `or`, `and` or `but not` is a different schema. |
| `object_wildcard_shapes` | `frozenset` of `(type, relation)` | empty | the object-wildcard shapes (`folder:*`) the store allows; there is no DSL syntax for them. Saved with `schema` when the store is created. Ignored when `schema` is `None`: the stored shapes apply. Passing `schema` with different shapes from the stored ones raises {py:exc}`zanzibar.SchemaMismatch`. Every open of a store that has shapes, creating or reopening, emits {py:exc}`zanzibar.UnprovenExtensionWarning`. |
| `ops` | {py:class}`zanzibar.setengine.SetOps` | {py:obj}`~zanzibar.setengine.RoaringSets` | the set representation the in-memory set engine uses: `RoaringSets` (compressed bitmaps) or {py:obj}`~zanzibar.setengine.PySets` (builtin sets). Both are ready-made objects: pass `ops=PySets`, do not call it. Not stored; answers are the same either way. |
| `sync` | `bool` | `True` | `True`: every write also updates the graph index, so this instance's reads see it at once. `False`: writes go to the tuple log only, and the index advances when you call {py:meth}`~zanzibar.Store.catch_up`. Not stored; it is per instance. See [Use async mode and freshness tokens](../how-to/async-tokens.md). |
| `paranoia` | `str`, `bool`, `0` / `1` or `None` | `None` | the runtime check level (see `ZANZIBAR_PARANOIA` above). `True` / `1` mean `full`, `False` / `0` mean `off`. `None` defers to the environment variable, then to `off`. Any other value raises {py:exc}`ValueError`. |

The level a store ended up with is its `paranoia` attribute:

```python
import os
from sqlmodel import SQLModel, Session, create_engine
import zanzibar
import zanzibar.store  # registers the zanzibar_* tables before create_all

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
SCHEMA = "type user\ntype doc\n  relations\n    define viewer: [user]\n"

os.environ["ZANZIBAR_PARANOIA"] = "residue"
try:
    with Session(engine) as session:
        print(zanzibar.Store(session, "s1", schema=SCHEMA).paranoia)  # -> 'residue'
    with Session(engine) as session:
        # an explicit argument beats the environment
        print(zanzibar.Store(session, "s1", paranoia="off").paranoia)  # -> 'off'
finally:
    del os.environ["ZANZIBAR_PARANOIA"]

with Session(engine) as session:
    print(zanzibar.Store(session, "s1").paranoia)  # -> 'off'
```

## `Store.adopt` arguments

`Store.adopt(session, store_id, *, schema=None, object_wildcard_shapes=frozenset(), bulk=True, ops=<default>, sync=True, paranoia=None)`
returns `(store, report)`. It takes every {py:class}`~zanzibar.Store` argument with the same
meaning, plus:

| argument | type | default | meaning |
| --- | --- | --- | --- |
| `bulk` | `bool` | `True` | build the index with the offline bulk builder (`True`) or by replaying the stored tuples one by one (`False`). Passed to {py:func}`~zanzibar.store.build_index`. |

With `schema=None` the store's stored schema and object-wildcard shapes are used, and
`object_wildcard_shapes` is ignored. See [Bulk-load or adopt an existing store](../how-to/bulk-load-adopt.md).

## Fixed limits

These are not settings; they are listed so you do not look for a knob.

| limit | value |
| --- | --- |
| identifier length (type, name, relation) | 1 to 256 characters from `A-Za-z0-9_./@+=-`; see [Tuple strings and identifiers](tuple-strings.md) |
| path count per index row | 2,147,483,647 (the 32-bit integer limit, on SQLite and PostgreSQL alike); a synchronous write past it raises {py:exc}`zanzibar.PathCountExceeded`; with `sync=False`, `catch_up()` raises it and the index stalls ([Recover a stalled index](../how-to/stall-recovery.md)) |
| SQLite busy timeout | raised to at least 10,000 ms on a connection before the store takes its write lock; a higher timeout you set is kept |
| isolation level (PostgreSQL) | `READ COMMITTED` only; see [Supported environments](environments.md) |
