# Test your permission model

A schema is code, so test it like code: open a store in memory, write the tuples a case
needs, and assert the answers. An in-memory SQLite database (`sqlite://`) is created
fresh for every test, so tests do not share state and need no clean-up.

Put a fixture and your tests in a test file, for example `test_permissions.py`:

```python
import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar import Store

SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user]
type doc
  relations
    define banned: [user]
    define viewer: [user, group#member] but not banned
"""


@pytest.fixture
def store():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield Store(session, "test", schema=SCHEMA, paranoia="full")


def test_group_member_can_view(store):
    store.add_tuple("user:alice", "member", "group:eng")
    store.add_tuple("group:eng#member", "viewer", "doc:roadmap")
    assert store.check("user:alice", "viewer", "doc:roadmap")


def test_ban_overrides_group_grant(store):
    store.add_tuple("user:alice", "member", "group:eng")
    store.add_tuple("group:eng#member", "viewer", "doc:roadmap")
    store.add_tuple("user:alice", "banned", "doc:roadmap")
    assert not store.check("user:alice", "viewer", "doc:roadmap")
```

Run them with `pytest`. Test the cases that should be refused as well as the ones that
should be allowed: a missing `but not` or a wrong `from` usually shows up as a grant that
should not be there, not as an error.

`paranoia="full"` checks the whole index after every write. It is too slow for production
(use `"residue"` there, see [Turn on runtime checks in production](runtime-checks.md)), but
in a test it turns a bug in the index into an error at the write that caused it.

The test functions are plain functions, so you can also call one with a store of your
own, for example while you work out a case in a REPL:

```python
engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
with Session(engine) as session:
    test_ban_overrides_group_grant(Store(session, "test", schema=SCHEMA, paranoia="full"))
print("passed")  # -> 'passed'
```

To make tests fail when a schema uses a wildcard extension that is not part of OpenFGA,
turn {py:class}`zanzibar.UnprovenExtensionWarning` into an error; see
[Handle errors](errors.md).
