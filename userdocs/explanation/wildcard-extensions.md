# Wildcard extensions beyond OpenFGA

OpenFGA has one wildcard: a *subject* such as `user:*`, meaning every user, allowed where a
relation's restriction lists it (`define viewer: [user, user:*]`). OpenFGA's documentation
says you cannot use `<type>:*` in a tuple's object, nor as part of a userset in the user
field. This library supports that standard wildcard, with one difference (a check whose
*subject* is `user:*` under `but not`; see
[Semantics and differences from OpenFGA](semantics-vs-openfga.md#wildcard-subjects-in-a-check)),
and adds three more:

| extension | how you write it | what a tuple means |
| --- | --- | --- |
| wildcard userset | `[group:*#member]` in a restriction | `group:*#member viewer doc:1`: the members of every group are viewers of `doc:1` |
| star tupleset | `[folder, folder:*]` on the relation after `from` | `folder:* parent doc:1`: every folder is a parent of `doc:1` |
| wildcard object | no DSL syntax; `object_wildcard_shapes={("folder", "viewer")}` | `user:alice viewer folder:*`: alice is a viewer of every folder |

They let you say "every X" in one tuple. A schema that uses any of them emits
{py:class}`zanzibar.UnprovenExtensionWarning`. This page explains what each one means, why
the warning exists, and when you might keep it, silence it or make it an error. A plain
`[user:*]` is standard and never warns.

The examples share one in-memory database. They silence the warning while setting up (see
[Keeping it, silencing it, or making it an error](#keeping-it-silencing-it-or-making-it-an-error)):

```python
import itertools
import warnings
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store, UnprovenExtensionWarning

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
_ids = itertools.count()

def new_store(schema, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UnprovenExtensionWarning)
        return Store(Session(engine), f"store-{next(_ids)}", schema=schema, **kwargs)
```

## Wildcard usersets: `[group:*#member]`

A userset names the members of one object's relation: `group:eng#member`. A wildcard
userset names the members of that relation on *every* object of the type.

```python
s = new_store("""
model
  schema 1.1
type user
type group
  relations
    define member: [user]
type doc
  relations
    define viewer: [user, group:*#member]
""")
s.add_tuple("group:*#member", "viewer", "doc:1")    # members of any group can view doc:1
s.add_tuple("user:alice", "member", "group:eng")

print(s.check("user:alice", "viewer", "doc:1"))     # -> True
print(s.check("user:bob", "viewer", "doc:1"))       # -> False
```

Alice is in a group, so she can view `doc:1`; Bob is in none. The restriction admits only
the wildcard form: writing `group:eng#member viewer doc:1` to this relation is refused,
because `[group:*#member]` does not list `group#member`.

A wildcard userset that would contain itself is a cycle and is refused like any other:
with `define member: [user, group:*#member]`, the tuple `group:*#member member group:g`
would make the members of `g` include the members of every group, `g` among them.
Over a relation that uses `and` or `but not`, the graph index (and so a `Store`) refuses a
wildcard userset, while a standalone set engine accepts it; see
{ref}`Shapes the graph index cannot compile <refused-shapes-the-graph-index-cannot-compile>`.

## Star tuplesets: `parent: [folder, folder:*]`

A tupleset is the relation after `from`; its stored tuples link an object to the objects
whose relations it inherits (see
[Semantics and differences from OpenFGA](semantics-vs-openfga.md#tuplesets-must-be-direct-and-may-not-name-a-userset)).
A star tupleset allows a wildcard in that link: "every folder is my parent".

```python
s = new_store("""
model
  schema 1.1
type user
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder, folder:*]
    define viewer: viewer from parent
""")
s.add_tuple("folder:*", "parent", "doc:1")          # every folder is a parent of doc:1
s.add_tuple("user:alice", "viewer", "folder:f1")

print(s.check("user:alice", "viewer", "doc:1"))     # -> True
print(s.check("user:bob", "viewer", "doc:1"))       # -> False
```

A viewer of any folder is now a viewer of `doc:1`. When the relation the `from` reads uses
`and` or `but not`, a star tupleset is refused; see
{ref}`Shapes the graph index cannot compile <refused-shapes-the-graph-index-cannot-compile>`.

## Wildcard objects: `object_wildcard_shapes`

The third extension puts the wildcard on the *object* side: a grant on every folder. It has
no DSL syntax, so you declare which `(type, relation)` pairs may take a wildcard object when
you create the store, with `object_wildcard_shapes`. The same argument exists on
{py:func}`zanzibar.parse_openfga_schema` and on the set engine. The declared shapes are saved
with the store's schema, so reopening the store does not need them again. A shape must name
a relation the schema declares; anything else is refused (see
{ref}`Object-wildcard shapes <refused-object-wildcard-shapes>`), and so is a shape the
graph index cannot serve, such as one on a relation that uses `but not` (see
{ref}`Shapes the graph index cannot compile <refused-shapes-the-graph-index-cannot-compile>`
and {ref}`A shape wildcarded on both sides <refused-a-shape-wildcarded-on-both-sides>`).

```python
s = new_store("""
model
  schema 1.1
type user
type folder
  relations
    define viewer: [user]
""", object_wildcard_shapes=frozenset({("folder", "viewer")}))
s.add_tuple("user:alice", "viewer", "folder:*")     # alice views every folder

print(s.check("user:alice", "viewer", "folder:f1"))  # -> True
```

`folder:f1` appears in no tuple, and Alice can still view it: a direct check against a
wildcard object does not need the folder to exist. A store without the declared shape
refuses the same write with {py:exc}`zanzibar.AdmissionRejected`.

Inheritance through a wildcard object is different. When "viewer of every folder" has to
reach a document through *some* folder, at least one folder has to exist; with none, the
answer is `False`. That rule, and an example, is in
[Semantics and differences from OpenFGA](semantics-vs-openfga.md#all-does-not-imply-some-when-there-are-none).

## How wildcards show up in lookups

A lookup does not expand a wildcard into the list of everyone it covers, because that list
may be unbounded. It reports a **marker** instead. From a `Store`, markers are
`(type, predicate, variant)` triples; the variant says which kind of wildcard it is:

- `"any"`: a wildcard *subject*. `("user", "...", "any")` is "every user", from `user:*`;
  `("group", "member", "any")` is "the members of every group", from `group:*#member`.
- `"all"`: a wildcard *object*, which only appears with `object_wildcard_shapes`.
  `("folder", "viewer", "all")` is "viewer of every folder".

```python
print(s.lookup("user:alice").markers)                # -> {('folder', 'viewer', 'all')}
```

{py:meth}`zanzibar.Store.expand` reports its markers as `(type, predicate)` pairs, without
the variant. Compare a marker from one with a marker from the other by their first two
fields. A marker always comes with a (possibly empty) set of subjects it covers but who
are refused (by a `but not`, for example), which you must subtract; see
[Find who can access what](../how-to/query-access.md).

## Why they emit a warning

The two backends of this library are kept in agreement in two ways (see
[How correctness is checked](assurance.md)):

1. **Tests.** A large differential test suite compares the graph index, the set engine and
   an independent reference implementation on the same schemas and tuples, including
   randomly generated ones.
2. **Proofs.** For a defined family of schemas, machine-checked proofs show that the
   graph index's algorithm and the set engine's algorithm give the same answers.

The three extensions are outside the family of schemas the proofs cover. They are tested,
in the same differential suite as everything else, but the agreement on them rests on
the tests alone. The warning tells you so, at the point where you choose to rely on
it. It is not a sign that something is broken, and it
does not change any answer.

It is raised each time a schema using an extension is loaded: on every `Store` open
(creating the store and reopening it), on each {py:func}`zanzibar.parse_openfga_schema`
call, and when a set engine is constructed. The warning points at your own line of code,
not at a line inside the library, and its message names the extensions it found, for
example `wildcard usersets [group:*#member]`.

## Keeping it, silencing it, or making it an error

`UnprovenExtensionWarning` is an ordinary Python warning (a `UserWarning`), so the standard
{py:mod}`warnings` machinery controls it, by its class, without touching other warnings.
Which setting is right depends on what you want the warning to protect:

- **Keep it** while you are deciding whether to use an extension at all. It is the only
  place the library tells you a schema has left the family the proofs cover.
- **Silence it** once you have chosen an extension on purpose. Then the warning has done
  its job, and repeating it on every store open is noise. Silence it next to the code that
  opens the store, with a comment saying which extension you rely on and why, so the
  choice stays visible in your code rather than in a log.
- **Make it an error** where schemas must stay inside the proved family, for example in
  your test suite. Opening a store with such a schema then raises the warning as an
  exception, so an extension cannot creep in unnoticed.

The examples on this page silence it around store creation only, because the warning
would otherwise repeat on every example. The code for both settings is in
[Handle errors](../how-to/errors.md#silence-the-wildcard-extension-warning-or-make-it-an-error).

## The cost of declaring a shape

Wildcard usersets and wildcard objects are not free in the graph index, even before you
write a single wildcard tuple: declaring such a shape makes the index keep extra rows for
every instance of the type, so that a later wildcard grant can be answered in a single
lookup. Declare only the shapes you use. A plain `[user:*]` has no such cost.
[Limits and costs](limits.md) has the details.
