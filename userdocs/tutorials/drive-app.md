# Model a Drive-style app

In this tutorial you will build the permission model of a small file-sharing app, like a
simplified Google Drive. It has users, groups of users, folders and documents. By the end:

- a document's owner can view it;
- a group can be given access, and every member gets it;
- a document inherits the viewers of the folder it is in;
- a document can be made public, so that every user can view it;
- a ban list takes access away from someone, whatever else grants it.

You will add one rule at a time and check access after each one. It takes about twenty
minutes. If you have not done [Your first permission check](first-check.md) yet, do that
first: this tutorial assumes you have the package installed and know what `add_tuple` and
`check` do.

## Set up

Create a file called `drive.py`. As in the first tutorial, you will add each piece of code
to the end of the file and run it with `python drive.py` after each step.

This time the database lives in memory (`"sqlite://"`), so every run starts from an empty
store. That suits a tutorial, because each run replays every step from the start.

## The schema

A store's schema is fixed when the store is created, so you will write the whole schema
now and then use it one rule at a time. Add this to `drive.py`:

```python
SCHEMA = """
model
  schema 1.1

type user

type group
  relations
    define member: [user, group#member]

type folder
  relations
    define owner: [user]
    define viewer: [user, group#member] or owner

type doc
  relations
    define parent: [folder]
    define owner: [user]
    define banned: [user]
    define viewer: ([user, user:*, group#member] or owner or viewer from parent) but not banned
"""
```

Do not worry about reading all of it yet. Each step below points at the part it uses.

Now open a store with it:

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
session = Session(engine)
store = Store(session, "drive", schema=SCHEMA)
```

## Step 1: owners can view their documents

The `doc` type says `define owner: [user]`, and its `viewer` relation includes `owner`.
Make alice the owner of a document called `doc:plan`:

```python
store.add_tuple("user:alice", "owner", "doc:plan")

print(store.check("user:alice", "owner", "doc:plan"))  # -> True
print(store.check("user:alice", "viewer", "doc:plan"))  # -> True
print(store.check("user:bob", "viewer", "doc:plan"))  # -> False
```

Alice can view her document because she owns it. Bob has no relationship to it, so he
cannot.

## Step 2: groups

The `group` type says `define member: [user, group#member]`: a group's members are users,
or the members of another group. Put bob and carol in a group called `eng`:

```python
store.add_tuple("user:bob", "member", "group:eng")
store.add_tuple("user:carol", "member", "group:eng")

print(store.check("user:bob", "member", "group:eng"))  # -> True
print(store.check("user:dave", "member", "group:eng"))  # -> False
```

Now give the whole group access to a document. The user in this tuple is not a single
user but `group:eng#member`, which means "every member of `group:eng`":

```python
store.add_tuple("group:eng#member", "viewer", "doc:specs")

print(store.check("user:bob", "viewer", "doc:specs"))  # -> True
print(store.check("user:carol", "viewer", "doc:specs"))  # -> True
print(store.check("user:alice", "viewer", "doc:specs"))  # -> False
```

You wrote one tuple, and both members of `eng` can view the document. Alice is not in
`eng`, so she cannot.

Groups can contain groups. Put a new group, `interns`, inside `eng`, and add erin to it:

```python
store.add_tuple("group:interns#member", "member", "group:eng")
store.add_tuple("user:erin", "member", "group:interns")

print(store.check("user:erin", "member", "group:eng"))  # -> True
print(store.check("user:erin", "viewer", "doc:specs"))  # -> True
```

Erin is a member of `interns`, every member of `interns` is a member of `eng`, and every
member of `eng` can view `doc:specs`.

## Step 3: folders pass access on to their documents

Folders have viewers too: `define viewer: [user, group#member] or owner`. Let the `eng`
group view a folder called `folder:projects`:

```python
store.add_tuple("group:eng#member", "viewer", "folder:projects")

print(store.check("user:bob", "viewer", "folder:projects"))  # -> True
```

A document records the folder it is in through its `parent` relation,
`define parent: [folder]`. Put a new document, `doc:roadmap`, in `folder:projects`. The
"user" of this tuple is the folder:

```python
store.add_tuple("folder:projects", "parent", "doc:roadmap")
```

The doc's `viewer` relation includes `viewer from parent`, which means "anyone who is a
viewer of this document's parent folder". So everyone who can view the folder can now view
the document, although no tuple connects them to it directly:

```python
print(store.check("user:bob", "viewer", "doc:roadmap"))  # -> True
print(store.check("user:erin", "viewer", "doc:roadmap"))  # -> True
print(store.check("user:alice", "viewer", "doc:roadmap"))  # -> False
```

Make alice the owner of the folder. A folder's owners are its viewers, so she can now view
the document inside it as well:

```python
store.add_tuple("user:alice", "owner", "folder:projects")

print(store.check("user:alice", "viewer", "doc:roadmap"))  # -> True
```

Ask who can view the roadmap. Filter the answer to users, so that you get a list of people
(without the filter the answer also contains groups and other usersets that have access;
[Find who can access what](../how-to/query-access.md) shows the unfiltered form):

```python
found = store.lookup_reverse("viewer", "doc:roadmap", subject_type="user")
print(sorted(store.result_keys(found)))  # -> [('user', 'alice', '...'), ('user', 'bob', '...'), ('user', 'carol', '...'), ('user', 'erin', '...')]
```

Everyone with access through the folder is listed: alice as its owner, and bob, carol and
erin through `eng`.

## Step 4: public documents

The doc's `viewer` relation also lists `user:*` in its brackets. That allows one special
tuple, whose user is `user:*`, meaning "every user". Make the handbook public:

```python
store.add_tuple("user:*", "viewer", "doc:handbook")

print(store.check("user:dave", "viewer", "doc:handbook"))  # -> True
print(store.check("user:someone-new", "viewer", "doc:handbook"))  # -> True
```

Every user can view it, including users who appear in no other tuple.

Asking who can view the handbook cannot list every user, so the answer carries a *marker*
instead. The marker `("user", "...", "any")` means "any user":

```python
found = store.lookup_reverse("viewer", "doc:handbook", subject_type="user")
print(sorted(store.result_keys(found)))  # -> []
print(found.markers)  # -> {('user', '...', 'any')}
```

No user is listed by name, and the marker says that every user is a viewer.

## Step 5: a ban list

The whole `viewer` definition of `doc` is wrapped in `(...) but not banned`. Whatever
grants someone access, a `banned` tuple takes it away again. Ban mallory from the handbook:

```python
store.add_tuple("user:mallory", "banned", "doc:handbook")

print(store.check("user:mallory", "viewer", "doc:handbook"))  # -> False
print(store.check("user:dave", "viewer", "doc:handbook"))  # -> True
```

The handbook is still public, except to mallory. The answer to "who can view it?" now says
so: the marker still covers every user, and `excluded_keys` lists the users it leaves out.
Exclusions are reported only next to a marker like this one; when there is no marker, a
banned user is simply missing from the list:

```python
found = store.lookup_reverse("viewer", "doc:handbook", subject_type="user")
print(found.markers)  # -> {('user', '...', 'any')}
print(sorted(store.excluded_keys(found)))  # -> [('user', 'mallory', '...')]
```

Read the two together: every user, except mallory.

A ban also beats access that comes through a group or a folder. Ban carol from the
roadmap, which she can view through `eng` and `folder:projects`:

```python
store.add_tuple("user:carol", "banned", "doc:roadmap")

print(store.check("user:carol", "viewer", "doc:roadmap"))  # -> False
print(store.check("user:bob", "viewer", "doc:roadmap"))  # -> True
print(store.check("user:carol", "viewer", "folder:projects"))  # -> True
```

Carol can still view the folder: the ban is on the document only.

## Step 6: what can one user see?

`lookup` answers the question from the user's side. List the documents carol can view:

```python
found = store.lookup("user:carol", object_type="doc", relation="viewer")
print(sorted(store.result_keys(found)))  # -> [('doc', 'handbook', 'viewer'), ('doc', 'specs', 'viewer')]
```

Carol can view the handbook (it is public) and the specs (through `eng`). The roadmap is
missing, because she is banned from it.

## Step 7: removing access

Take erin out of the `interns` group:

```python
store.remove_tuple("user:erin", "member", "group:interns")

print(store.check("user:erin", "member", "group:eng"))  # -> False
print(store.check("user:erin", "viewer", "doc:specs"))  # -> False
print(store.check("user:erin", "viewer", "doc:roadmap"))  # -> False
print(store.check("user:erin", "viewer", "doc:handbook"))  # -> True
```

Erin loses everything she had through the group, and keeps the handbook, which is public.

Close the session when you are done:

```python
session.close()
```

## What you have done

You have modelled a file-sharing app with owners, nested groups, folders whose viewers can
view the documents inside them, public documents and a ban list, and you have seen how
`check`, `lookup` and `lookup_reverse` answer questions about it.

From here:

- For how the library answers these questions, and the words the how-to guides use for its
  parts (the set engine, the graph index, the tuple log), see
  [The two backends](../explanation/two-backends.md).
- For more modelling recipes (block lists, requiring two relations with `and`, and others),
  see [Common modelling patterns](../how-to/patterns.md).
- For the details of reading `lookup` results, markers and exclusions, see
  [Find who can access what](../how-to/query-access.md).
- For how `but not` is evaluated, see
  [How `and` and `but not` work](../explanation/boolean-operators.md).
- For everything the schema language accepts, see the
  [schema language reference](../reference/schema-language.md).
