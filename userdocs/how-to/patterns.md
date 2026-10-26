# Common modelling patterns

Recipes for the permission shapes most applications need. Each recipe gives the schema
fragment, the tuples you write, and the checks that follow. Every example on this page
runs as written; the setup block below opens a fresh store per recipe.

For the full grammar see [the schema language reference](../reference/schema-language.md).
For why `and` / `but not` cost what they cost, see
[how `and` and `but not` work](../explanation/boolean-operators.md).

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)


def open_store(store_id, schema):
    """A new Store with its own Session (one Session per Store)."""
    return Store(Session(engine), store_id, schema=schema)
```

## Groups, including groups of groups

Give the group a `member` relation that admits users and the members of other groups,
then grant access to a group's members with the userset `group:<name>#member`.

```python
store = open_store("groups", """
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define viewer: [user, group#member]
""")

store.add_tuple("user:alice", "member", "group:eng")
store.add_tuple("group:eng#member", "member", "group:staff")   # eng is inside staff
store.add_tuple("group:staff#member", "viewer", "doc:handbook")

print(store.check("user:alice", "viewer", "doc:handbook"))  # -> True
print(store.check("user:bob", "viewer", "doc:handbook"))  # -> False
```

- The `group#member` in `define member: [user, group#member]` is what allows nesting.
  Leave it out if groups never contain groups.
- Group membership data must be acyclic. A write that would put a group inside itself,
  directly or through other groups, is refused with {py:exc}`zanzibar.AdmissionRejected`.

```python
from zanzibar import AdmissionRejected

refused = False
try:
    store.add_tuple("group:staff#member", "member", "group:eng")   # staff inside eng: a cycle
except AdmissionRejected:
    refused = True
print(refused)  # -> True
print(store.check("user:alice", "viewer", "doc:handbook"))  # -> True
```

## Roles that imply other roles

Name another relation of the same type in a definition to make one role include
another. Here every owner is an editor and every editor is a viewer.

```python
store = open_store("roles", """
model
  schema 1.1
type user
type doc
  relations
    define owner: [user]
    define editor: [user] or owner
    define viewer: [user] or editor
""")

store.add_tuple("user:alice", "owner", "doc:1")
store.add_tuple("user:bob", "viewer", "doc:1")

print(store.check("user:alice", "viewer", "doc:1"))  # -> True
print(store.check("user:bob", "editor", "doc:1"))  # -> False
```

The relation you name must be declared on the same type. A loop of such references
(`define a: [user] or b` with `define b: a`) is refused when the schema is parsed.

## Inherit access from a parent

Store the link to the parent on a relation that holds only type restrictions (here
`parent: [folder]`), then use `<relation> from parent`. The relation after `from` must
be declared on at least one of the types the link relation admits (here `folder`).

```python
store = open_store("parents", """
model
  schema 1.1
type user
type folder
  relations
    define parent: [folder]
    define viewer: [user] or viewer from parent
type doc
  relations
    define parent: [folder]
    define viewer: [user] or viewer from parent
""")

store.add_tuple("user:alice", "viewer", "folder:root")
store.add_tuple("folder:root", "parent", "folder:projects")    # projects is inside root
store.add_tuple("folder:projects", "parent", "doc:plan")       # plan is inside projects

print(store.check("user:alice", "viewer", "doc:plan"))  # -> True
print(store.check("user:alice", "viewer", "folder:projects"))  # -> True
```

- The parent tuple's user is the folder itself (`"folder:root"`), not a userset.
- `viewer from parent` on `folder` makes the inheritance work through any depth of
  nested folders. Folder data must be acyclic, as with groups.
- The relation after `from` must be a plain list of types, such as `[folder]` or
  `[folder, doc]`. To see why and what to write when yours is not, see
  [Rewrite a refused schema shape](rewrite-refused-shape.md).

## Public access

List `user:*` in the restriction, then write the tuple with the user `"user:*"`. It
grants every user, including users no tuple has ever named.

```python
store = open_store("public", """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user, user:*]
""")

store.add_tuple("user:*", "viewer", "doc:press-release")

print(store.check("user:anyone", "viewer", "doc:press-release"))  # -> True
print(store.check("user:anyone", "viewer", "doc:draft"))  # -> False
```

Writing `"user:*"` to a relation whose restriction does not list `user:*` is refused
with {py:exc}`zanzibar.AdmissionRejected`. A restriction such as `[user:*]` is plain
OpenFGA; the wildcard forms beyond it are covered in
[wildcard extensions](../explanation/wildcard-extensions.md).

## Block lists with `but not`

Subtract a relation of blocked users. The block wins over every way of being granted,
public access included.

```python
store = open_store("blocklist", """
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define blocked: [user]
    define viewer: [user, user:*, group#member] but not blocked
""")

store.add_tuple("user:*", "viewer", "doc:1")
store.add_tuple("user:alice", "member", "group:eng")
store.add_tuple("group:eng#member", "viewer", "doc:1")
store.add_tuple("user:alice", "blocked", "doc:1")

print(store.check("user:alice", "viewer", "doc:1"))  # -> False
print(store.check("user:bob", "viewer", "doc:1"))  # -> True

store.remove_tuple("user:alice", "blocked", "doc:1")
print(store.check("user:alice", "viewer", "doc:1"))  # -> True
```

Put the `but not` on the relation you check, not on a relation that refers to itself.
`define member: [user, group#member] but not banned` is refused by
{py:class}`zanzibar.Store` with {py:exc}`zanzibar.CyclicDerivedDependency`, because
`member` recurses through itself.

To block at a folder and have the block reach everything inside it, make the block list
inherit, and subtract it from a relation that inherits separately:

```python
store = open_store("folder-blocks", """
model
  schema 1.1
type user
type folder
  relations
    define parent: [folder]
    define blocked: [user] or blocked from parent
    define viewer_base: [user] or viewer_base from parent
    define viewer: viewer_base but not blocked
type doc
  relations
    define parent: [folder]
    define blocked: [user] or blocked from parent
    define viewer_base: [user] or viewer_base from parent
    define viewer: viewer_base but not blocked
""")

store.add_tuple("user:alice", "viewer_base", "folder:root")
store.add_tuple("folder:root", "parent", "folder:secret")
store.add_tuple("folder:secret", "parent", "doc:payroll")
store.add_tuple("user:alice", "blocked", "folder:secret")

print(store.check("user:alice", "viewer", "folder:root"))  # -> True
print(store.check("user:alice", "viewer", "doc:payroll"))  # -> False
```

Grant on `viewer_base` and check `viewer`. The block overrides every grant below the
blocked folder, including a `viewer_base` grant made directly on a folder or doc inside
it.

The one-relation form `define viewer: ([user] or viewer from parent) but not blocked` is
refused; [Rewrite a refused schema shape](rewrite-refused-shape.md#recursion-through-and-or-but-not)
explains why and how the rewrite differs.

## Require two relations with `and`

`and` grants only subjects that are in both relations. Here a user may publish a doc
only if they can edit it and are a member of the publishers group of its organisation.

```python
store = open_store("both", """
model
  schema 1.1
type user
type org
  relations
    define publisher: [user]
type doc
  relations
    define org: [org]
    define editor: [user]
    define can_publish: editor and publisher from org
""")

store.add_tuple("org:acme", "org", "doc:1")
store.add_tuple("user:alice", "editor", "doc:1")
store.add_tuple("user:bob", "editor", "doc:1")
store.add_tuple("user:alice", "publisher", "org:acme")

print(store.check("user:alice", "can_publish", "doc:1"))  # -> True
print(store.check("user:bob", "can_publish", "doc:1"))  # -> False
```

You cannot write tuples to `can_publish`: it has no type restriction. Grant its parts
instead.

## Combining operators

`but not` may not share a level with `or`, `and` or another `but not`, and `or` may not
be mixed with `and` without parentheses. Parenthesise the reading you mean:

| you mean | write |
| --- | --- |
| either relation, minus the blocked | `(editor or viewer) but not blocked` |
| the base, minus either list | `viewer but not (blocked or suspended)` |
| editors, or viewers who are not blocked | `editor or (viewer but not blocked)` |
| both, or the owner | `owner or (editor and approver)` |

An unparenthesised `a or b but not c` is refused with a message that names this rule.
See [Rewrite a refused schema shape](rewrite-refused-shape.md).

## One store per tenant

A store id may be any non-blank string ([Store ids](../reference/tuple-strings.md#store-ids)),
so `"tenant:acme"` works as a tenant key. All stores share the same ten tables, and each has
its own schema and tuples. A freshness token belongs to the store that returned it:
passing it to another store raises {py:exc}`zanzibar.ForeignToken`. To remove a tenant,
see [Deleting a store](../reference/tables.md#deleting-a-store).
