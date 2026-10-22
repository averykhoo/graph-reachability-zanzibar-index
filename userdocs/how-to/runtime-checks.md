# Turn on runtime checks in production

A {py:class}`zanzibar.Store` can check the graph index for corruption inside every write,
before the write commits. The checks are called *paranoia* levels. They are off by
default. For anything security-sensitive, turn on the `residue` level.

## Turn on the recommended level

Pass `paranoia="residue"` when you open the store:

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define blocked: [user]
    define viewer: [user] but not blocked
"""

engine = create_engine("sqlite:///checks.db")
SQLModel.metadata.create_all(engine)

store = Store(Session(engine), "my-app", schema=SCHEMA, paranoia="residue")
store.add_tuple("user:alice", "viewer", "doc:1")
print(store.check("user:alice", "viewer", "doc:1"))  # -> True
```

Or set it for a whole deployment, without a code change, with the environment variable
`ZANZIBAR_PARANOIA`:

```text
export ZANZIBAR_PARANOIA=residue
```

## Choose a level

There are four levels: `"off"` (the default, which checks nothing), `"residue"` for
production, `"full"` for tests and before a release, and `"fixpoint"` for diagnosing a
suspected bug. The {ref}`table of levels <paranoia-levels>` in the configuration reference says
exactly what each one runs and what it costs.

Every level above `"off"` makes writes slower, `"full"` and `"fixpoint"` by more as the
store grows. The measured costs are in
[Limits and costs](../explanation/limits.md#runtime-checks-add-to-the-write-cost); measure
on your own schema and data before choosing.

- **`"residue"`** looks for the corruption that matters most for security: a record behind
  an `and` or `but not` relation that refers to an index row that no longer exists. That
  kind of fault can grant access that should be denied. It also checks the wildcard paths
  that the write touched. It does not look for every kind of corruption: some faults are
  found only by `"full"`.
- **`"full"`** reads the whole index on every commit, recomputes what the write changed,
  and checks again after the commit. Use it in tests and before a release, not under
  production write load.
- **`"fixpoint"`** adds a re-check of the `and` / `but not` updates each write made. It is
  for diagnosing a suspected bug in how those relations are updated. Nothing turns it on
  unless you name it.

The checks run when a store commits a write. A read (`check`, `lookup`, `lookup_reverse`,
`expand`) is never checked and never slowed down.

## Which setting wins

1. The `paranoia=` argument, when you pass one.
2. Otherwise `ZANZIBAR_PARANOIA`, when it is set and not empty.
3. Otherwise `"off"`.

So code that passes `paranoia=` explicitly cannot be overridden by the environment. The
level a store ended up with is in `store.paranoia`:

```python
import os

os.environ["ZANZIBAR_PARANOIA"] = "residue"
print(Store(Session(engine), "my-app").paranoia)  # -> 'residue'
print(Store(Session(engine), "my-app", paranoia="off").paranoia)  # -> 'off'
```

Both the argument and the variable also accept `True` / `"1"` / `"on"` / `"true"` /
`"yes"` for `"full"`, and `False` / `"0"` / `"off"` / `"false"` / `"no"` for `"off"`. Anything
else is refused with a `ValueError` when the store opens, so a misspelt setting never
silently means "off":

```python
os.environ["ZANZIBAR_PARANOIA"] = "residu"
try:
    Store(Session(engine), "my-app")
except ValueError as error:
    print(str(error).startswith("bad paranoia level 'residu'"))  # -> True
del os.environ["ZANZIBAR_PARANOIA"]
```

## When a check fails

A failed check is reported as {py:exc}`zanzibar.InvariantViolation`. Its message names the
store, whether the check ran before or after the commit, and the rule that was broken.

- **Before the commit** (`"residue"`, `"full"` and `"fixpoint"`): the write raises
  `InvariantViolation` and is not committed. The store rolls it back and stays usable, but
  the index was found in a state it should never reach.
- **After the commit** (`"full"` and `"fixpoint"` only): the write has already been
  committed when this check runs, so the problem is in data that is now stored. In the
  current version the write does not raise `InvariantViolation` itself here: it raises
  `sqlalchemy.exc.InvalidRequestError` ("This session is in 'committed' state"), with the
  `InvariantViolation` attached as its `__context__`. That `Store` object cannot be used
  again: every later `check`, write or `refresh()` on it raises the same
  `InvalidRequestError`. Discard it, and open a new `Store` on a new `Session` for the
  steps below. A release that changes this behaviour says so in the
  [changelog](../reference/changelog.md).

To recognise both cases in one handler, look at the exception and at its `__context__`:

```python
from sqlalchemy.exc import InvalidRequestError
from zanzibar import InvariantViolation

def is_invariant_violation(error: BaseException) -> bool:
    if isinstance(error, InvariantViolation):
        return True
    return (isinstance(error, InvalidRequestError)
            and isinstance(error.__context__, InvariantViolation))

print(is_invariant_violation(InvariantViolation("example")))  # -> True
```

`InvariantViolation` is an `AssertionError`, and it is deliberately **not** a
{py:exc}`zanzibar.ZanzibarError`, so a handler for ordinary refusals does not swallow it.
Do not treat it as a rejected request. It means the library has a bug or the database was
changed behind the library's back. When you see one:

1. Stop writing to that store and alert someone. Keep the full message (for the
   after-commit case, the message of the `InvariantViolation` in `__context__`).
2. Report it as a bug, with the message and, if you can, the sequence of writes that led
   to it.
3. Rebuild the index from the stored tuples, which are the source of truth, with
   {py:func}`zanzibar.store.rebuild_index`. Stop every async worker for the store first.
   See [Recover a stalled index](stall-recovery.md) for the procedure.

See [Handle errors](errors.md) for how this exception relates to the others.
