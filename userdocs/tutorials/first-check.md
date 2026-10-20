# Your first permission check

In this tutorial you will set up a permission store for a small document-sharing app, give
two people access to a document, and then ask the store who can do what. It takes about
ten minutes.

You need Python 3.13 or later. Everything runs on SQLite, which comes with Python, so there
is no database server to set up.

## Install the package

Create a new folder for this tutorial, open a terminal in it, and install the package:

```text
pip install zanzibar-index
```

Now create a file called `first_check.py` in that folder. You will add each piece of code
below to the end of this file, and run the file after each step with `python first_check.py`.

## Write a schema

A schema says what kinds of things exist in your app and how people can be related to
them. Add this to `first_check.py`:

```python
SCHEMA = """
model
  schema 1.1

type user

type doc
  relations
    define editor: [user]
    define viewer: [user] or editor
"""
```

This schema has two types, `user` and `doc`. A doc has two relations:

- `editor`: a user can be made an editor of a doc directly.
- `viewer`: a user can be made a viewer directly, **or** is one because they are an editor.

## Create a store

The store keeps its data in database tables. Add the code that creates a SQLite database
file, creates the tables, and opens a store named `"my-app"` with your schema:

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

engine = create_engine("sqlite:///first-check.db")
SQLModel.metadata.create_all(engine)

session = Session(engine)
store = Store(session, "my-app", schema=SCHEMA)
print(store.store_id)  # -> 'my-app'
```

Run the file. It prints `my-app`, and a new file `first-check.db` appears in the folder.
That file now holds the store and its schema.

A store's schema cannot be changed once it is created. If you edit the schema later in this
tutorial, delete `first-check.db` before you run the file again. If you forget, opening
the store raises {py:exc}`zanzibar.SchemaMismatch`, whose message says the schema
"disagrees with its persisted schema".

## Record who can do what

Each fact you record is a *relationship tuple*: a user, a relation and an object. Make
alice an editor of the document `doc:readme`, and bob a viewer of it:

```python
store.add_tuple("user:alice", "editor", "doc:readme")
store.add_tuple("user:bob", "viewer", "doc:readme")
```

The strings `"user:alice"` and `"doc:readme"` are written as `type:name`. The type must be
one the schema declares, the relation must be one that type declares, and the user must be
of a type listed in the relation's brackets (`[user]` here). A tuple that breaks any of
these rules is refused with {py:exc}`zanzibar.AdmissionRejected`.

Each `add_tuple` call is saved to the database straight away; you do not commit anything
yourself. Adding a tuple that is already stored does nothing, so running the file again
after each step, as this tutorial asks, is safe.

## Check access

Now ask the store questions. Add these lines and run the file:

```python
print(store.check("user:alice", "editor", "doc:readme"))  # -> True
print(store.check("user:alice", "viewer", "doc:readme"))  # -> True
print(store.check("user:bob", "viewer", "doc:readme"))  # -> True
print(store.check("user:bob", "editor", "doc:readme"))  # -> False
```

Each line prints `True` or `False`. Alice is a viewer even though you never said so: the
schema says every editor is a viewer. Bob is a viewer but not an editor.

## List what a user can reach

`check` answers a yes-or-no question about one user and one object. To list every document
alice can view, use `lookup`, and turn its result into readable keys with `result_keys`:

```python
found = store.lookup("user:alice", object_type="doc", relation="viewer")
print(sorted(store.result_keys(found)))  # -> [('doc', 'readme', 'viewer')]
```

Each key is a `(type, name, relation)` triple: alice is a `viewer` of `doc:readme`.

## List who can reach an object

The opposite question, "who can view `doc:readme`?", is `lookup_reverse`. Ask it for the
users only:

```python
found = store.lookup_reverse("viewer", "doc:readme", subject_type="user")
print(sorted(store.result_keys(found)))  # -> [('user', 'alice', '...'), ('user', 'bob', '...')]
```

Both alice and bob are listed. The `"..."` in each key means "the user themselves", as
opposed to a group of users.

## Take access away

Remove bob's tuple, and check again:

```python
store.remove_tuple("user:bob", "viewer", "doc:readme")
print(store.check("user:bob", "viewer", "doc:readme"))  # -> False
print(store.check("user:alice", "viewer", "doc:readme"))  # -> True
```

Bob has lost access. Alice still has it, because she is still an editor.

## Open the store again

Everything you wrote is in `first-check.db`. Close the session, then open the store again
by name. You do not pass the schema this time, because the store already has one:

```python
session.close()

session = Session(engine)
store = Store(session, "my-app")
print(store.check("user:alice", "viewer", "doc:readme"))  # -> True
session.close()
```

Alice's access survived, because it is stored in the database.

## What you have done

You have written a schema, created a store on SQLite, recorded relationships, checked
access, listed what a user can reach and who can reach an object, removed access, and
reopened the store.

The [next tutorial](drive-app.md) builds a larger model, with groups, folders that pass
their access on to the documents inside them, public documents, and a ban list.

To learn more about the ideas behind this tutorial, read
[Zanzibar and relationship-based access control](../explanation/zanzibar-intro.md).
