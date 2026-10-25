# Semantics and differences from OpenFGA

The schema language of this library is a subset of the [OpenFGA](https://openfga.dev)
modelling language (schema 1.1), and for the schemas both accept, the library aims to give
the answers OpenFGA gives. This page lists where it does not: shapes it refuses, shapes it
accepts that OpenFGA does not, and a few questions it answers differently. Each difference
is deliberate, and each is explained here with its reason.

The claims below about this library are shown by the examples on this page, which run as
part of the library's tests. The claims about OpenFGA come from OpenFGA's documentation
and grammar, unless a difference says it was compared against an OpenFGA server.

For the rules of the schema language itself, see the
[schema language reference](../reference/schema-language.md). To move an existing model
over, see [Port an OpenFGA model](../how-to/port-openfga.md) and
[Rewrite a refused schema shape](../how-to/rewrite-refused-shape.md).

The examples share one in-memory SQLite database:

```python
import itertools
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store, AdmissionRejected, SchemaError, parse_openfga_schema

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
_ids = itertools.count()

def new_store(schema, **kwargs):
    """A fresh store with its own id and its own session."""
    return Store(Session(engine), f"store-{next(_ids)}", schema=schema, **kwargs)

def refused(fn):
    """The name of the exception fn raises, or 'accepted'."""
    try:
        fn()
    except Exception as exc:
        return type(exc).__name__
    return "accepted"
```

## The common ground

Most of the model works as in OpenFGA: types, relations, direct type restrictions such as
`[user, group#member]`, computed relations (`define viewer: editor`), tuple-to-userset
(`define viewer: viewer from parent`), `or`, `and`, `but not`, and the public wildcard
`[user:*]`. Tuples use OpenFGA's `user, relation, object` form (`"user:alice"`,
`"group:eng#member"`, `"user:*"`; objects are `"type:name"`). A `Store` also accepts an
OpenFGA JSON authorization model in place of DSL text.

## Not supported: conditions and modules

Conditions (`[user with some_condition]`) and modules (schema 1.2, `module`,
`extend type`) are refused with {py:exc}`zanzibar.SchemaError`. The only version line
accepted is `schema 1.1`; a `schema 1.2` header is refused even when the rest of the
schema would be valid 1.1.

```python
WITH_CONDITION = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user with office_hours]
"""
print(refused(lambda: parse_openfga_schema(WITH_CONDITION)))   # -> 'SchemaError'

SCHEMA_1_2 = """
model
  schema 1.2
type user
"""
print(refused(lambda: parse_openfga_schema(SCHEMA_1_2)))   # -> 'ShapeNoLongerAccepted'
```

{py:exc}`zanzibar.ShapeNoLongerAccepted` is a kind of `SchemaError`, used for shapes an
earlier release accepted; its `.instead` attribute holds the rewrite.

## A schema must be self-consistent

Every relation and type a schema mentions must be declared, and computed or tupleset
references may not form a cycle (`define a: b` with `define b: a`). Both are refused when
the schema is parsed, so a typo such as `[usr]` or `define viewer: edtor` surfaces before
any tuple is written, rather than as a relation that silently never matches.

```python
DANGLING = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: editor
"""
print(refused(lambda: parse_openfga_schema(DANGLING)))   # -> 'SchemaError'
```

Recursion through stored tuples stays legal: `define viewer: [user] or viewer from parent`
is the usual folder hierarchy. What is refused is a definition that refers back to itself
without going through a tuple.

## Tuplesets must be direct, and may not name a userset

The relation after `from` (the **tupleset**) is followed through the tuples that are
stored on it. OpenFGA's documentation states two rules for it: it may not refer to another
relation, and its type restrictions may not be wildcards or usersets. This library applies
the same rules, at parse time, with two relaxations noted below.

**Why.** `from` only walks stored tuples. If the tupleset had a computed arm (`define
parent: [folder] or owner`) or an operator, that arm would be silently ignored, and a
`[folder#member]` restriction would have its `#member` silently ignored, because a
stored parent link is followed to the folder, not to the folder's members. Refusing these
shapes means the schema always means what it says.

```python
USERSET_TUPLESET = """
model
  schema 1.1
type user
type folder
  relations
    define member: [user]
    define viewer: [user]
type doc
  relations
    define parent: [folder#member]
    define viewer: viewer from parent
"""
print(refused(lambda: parse_openfga_schema(USERSET_TUPLESET)))   # -> 'SchemaError'
```

The error message says what to write instead. For the userset case it is `[folder]` for
the link plus `define parent_member: member from parent` where the userset is what you
meant; for a computed tupleset, put the links on a direct relation of their own and point
the `from` at that.

The two relaxations: a tupleset may be a union of direct blocks (`[folder] or [doc]`), and
it may include a wildcard type (`[folder, folder:*]`, a "star tupleset"). The first is not
OpenFGA syntax; the second is one of this library's
[wildcard extensions](wildcard-extensions.md).

## A userset is a member of itself, and one difference from OpenFGA

OpenFGA treats a tuple such as `doc:1#viewer viewer doc:1` as implicit: the userset
`doc:1#viewer` is, by definition, a viewer of `doc:1`, and you cannot (and need not) write
that tuple. This library does the same. It is visible when the *subject* of a check is a
userset, and it carries through everything built on the relation, `but not` included:

```python
s = new_store("""
model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define viewer: [user, doc#viewer]
    define vx: [user, doc#banned] but not banned
""")

# On an empty store, doc:1#viewer is a viewer of doc:1
print(s.check("doc:1#viewer", "viewer", "doc:1"))        # -> True

# Writing the implicit tuple is refused (here as a cycle)
print(refused(lambda: s.add_tuple("doc:1#viewer", "viewer", "doc:1")))   # -> 'AdmissionRejected'

# doc:1#banned is a member of banned, so its own `but not banned` excludes it
s.add_tuple("doc:1#banned", "vx", "doc:1")
print(s.check("doc:1#banned", "vx", "doc:1"))            # -> False
```

Lookups show it too: `lookup_reverse("viewer", "doc:1")` lists `doc:1#viewer` itself,
even when no tuple names it (see [Find who can access what](../how-to/query-access.md)).
The rule only ever adds the userset itself, never its members, so checks on plain users
and on `user:*` are unaffected. It was compared against OpenFGA v1.22.0 when it was
introduced; before 0.1.0 this library answered these checks the other way (see
[Upgrade from 0.0.x to 0.1](../how-to/upgrade-0.1.md)).

**The difference** is a `from` whose tupleset allows a type that does not declare the
target relation. The userset still counts as a member of itself here, where OpenFGA
refuses the question:

```python
s = new_store("""
model
  schema 1.1
type user
type team
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder, team]
    define x: viewer from parent
""")
s.add_tuple("team:1", "parent", "doc:1")
print(s.check("team:1#viewer", "x", "doc:1"))            # -> True
```

`team` has no `viewer` relation, yet `team:1#viewer` counts as an `x` of `doc:1` here,
through the self-membership rule. OpenFGA rejects this query with a validation error
(`relation 'team#viewer' not found`). OpenFGA has also announced that models whose
tupleset types lack the target relation will stop building at all, with no date set as of
October 2026.

## Wildcard subjects in a check

`user:*` as the *subject* of a check is read literally: the question is whether the
wildcard subject itself holds the relation, not whether every user does.

```python
s = new_store("""
model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define viewer: [user, user:*] but not banned
""")
s.add_tuple("user:*", "viewer", "doc:1")
s.add_tuple("user:mallory", "banned", "doc:1")

print(s.check("user:bob", "viewer", "doc:1"))            # -> True
print(s.check("user:mallory", "viewer", "doc:1"))        # -> False
print(s.check("user:*", "viewer", "doc:1"))              # -> True
```

The last answer is `True` although Mallory is excluded: `user:*` was granted and is not
itself banned. Ask about individual users when that difference matters. This reading has
not been checked against an OpenFGA server, and OpenFGA has announced that a check with
`user:*` as the subject on a relation that uses `but not` will return an error.

## Tuple data must be acyclic

A write that would close a cycle in the tuples, such as group `a` inside group `b` inside
group `a`, a group inside itself, or a folder that is its own ancestor, is refused with
{py:exc}`zanzibar.AdmissionRejected`, by both backends.

```python
s = new_store("""
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
""")
s.add_tuple("group:a#member", "member", "group:b")
print(refused(lambda: s.add_tuple("group:b#member", "member", "group:a")))   # -> 'AdmissionRejected'
```

**Why.** The graph index stores, for every pair it connects, how many paths join them, so
that removing one tuple undoes exactly what it added (see
[How the graph index works](graph-index.md)). In a cycle the number of paths is infinite.
Refusing cycles at write time keeps that count finite, and the set engine refuses the same
writes so that the two backends always accept the same data. If you import tuples from
another system, OpenFGA included, check them for cycles first: one cyclic tuple makes the
import stop at that write.

## No recursion through `and` or `but not`

A relation that reaches itself through an operator, such as
`define viewer: ([user] or viewer from parent) but not blocked`, is refused by `Store` with
{py:exc}`zanzibar.CyclicDerivedDependency`. A standalone set engine accepts it, but the
graph index cannot maintain it, and a `Store` runs both.

```python
RECURSES_THROUGH_BUT_NOT = """
model
  schema 1.1
type user
type folder
  relations
    define parent: [folder]
    define blocked: [user]
    define viewer: ([user] or viewer from parent) but not blocked
"""
print(refused(lambda: new_store(RECURSES_THROUGH_BUT_NOT)))   # -> 'CyclicDerivedDependency'
```

The usual rewrite recurses on a plain relation and applies the operator on top
(`define viewer_base: [user] or viewer_base from parent`, then
`define viewer: viewer_base but not blocked`). It is not the same schema: `blocked` then
applies only on the object you ask about, not on every folder above it.
[How `and` and `but not` work](boolean-operators.md) explains why the index needs this.
OpenFGA accepts such models today, but has announced that models with recursion through
`and` or `but not` will stop building.

## Writes are strict, reads are lenient

A write is checked against the schema: an undeclared type or relation, a subject the
relation's restriction does not admit, or a malformed name is refused with
{py:exc}`zanzibar.AdmissionRejected`, and the message says what was wrong. A read with the
same mistake does not raise. It answers `False`. The leniency covers names and declared
relations only: a string that is not of the form `type:name`, `type:name#relation` or
`type:*` (such as `useralice`, `user:`, `group:g#b:c`, or an object `doc:1#viewer`)
raises {py:exc}`zanzibar.MalformedTupleString` on reads and writes alike.

```python
s = new_store("""
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
""")
print(refused(lambda: s.add_tuple("user:alice", "vewer", "doc:1")))   # -> 'AdmissionRejected'
print(s.check("user:alice", "vewer", "doc:1"))           # -> False
print(refused(lambda: s.check("useralice", "viewer", "doc:1")))   # -> 'MalformedTupleString'
```

So a typo in a relation name in your application code reads as "denied". That is the
safe direction for an access check, but it is silent; test your call sites. OpenFGA returns
an error for a check on an undeclared relation instead.

**Why.** A bad write would put data into the store that no query could ever reach, and the
mistake would only show up later. A read changes nothing, and answering `False` keeps a
check usable as a plain boolean everywhere.

Names are restricted on writes to the characters `A-Z a-z 0-9 _ . / @ + = -`, 1 to 256 of
them (see [Tuple strings and identifiers](../reference/tuple-strings.md)). Declared names
in the schema are held to the same characters, and a relation name may not contain `.`.

## Syntax: a little looser in places, as strict in others

The parser accepts a few spellings that OpenFGA's grammar does not, such as more than one
`[...]` block in one definition (`[user] or [group#member]`). A schema that uses them works
here but may not load in OpenFGA's own tools, so avoid them in a model you also run there.
The [schema language reference](../reference/schema-language.md#extensions-beyond-openfga)
lists each one. Two of them, a schema with no `model` / `schema 1.1` header and a `define`
with no `relations` line above it, have not been checked against OpenFGA, so do not rely on
OpenFGA refusing or accepting them either.

Elsewhere it is as strict as OpenFGA's grammar, in places people porting a model often trip
over: `but not` may not share a level with `or` or `and`, so `a or b but not c` needs
parentheses ([Precedence and grouping](../reference/schema-language.md#precedence-and-grouping)),
and a `model`, `schema 1.1` or `relations` line must stand alone, not even followed by a
comment:

```python
TRAILING_COMMENT = """
model
  schema 1.1
type user
type doc
  relations # docs
    define viewer: [user]
"""
print(refused(lambda: parse_openfga_schema(TRAILING_COMMENT)))   # -> 'ShapeNoLongerAccepted'
```

The [refused schema shapes](../reference/refused-shapes.md) reference lists every refusal
with its rewrite.

## Beyond OpenFGA: wildcard extensions

Three features have no OpenFGA counterpart: wildcard usersets (`[group:*#member]`), star
tuplesets (`[folder, folder:*]` after `from`) and wildcard objects (`folder:*` as the
object of a tuple). They are covered on their own page,
[Wildcard extensions beyond OpenFGA](wildcard-extensions.md). One consequence belongs
here, because it is a rule about meaning.

### "All" does not imply "some" when there are none

Take an object wildcard on `(folder, viewer)`, so that `folder:*` can hold a viewer grant,
and a star tupleset on `doc#parent`:

```python
import warnings
from zanzibar import UnprovenExtensionWarning

with warnings.catch_warnings():
    warnings.simplefilter("ignore", UnprovenExtensionWarning)   # deliberate: see the wildcard page
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
""", object_wildcard_shapes=frozenset({("folder", "viewer")}))

s.add_tuple("user:alice", "viewer", "folder:*")   # alice views every folder
s.add_tuple("folder:*", "parent", "doc:1")        # every folder is a parent of doc:1

print(s.check("user:alice", "viewer", "doc:1"))           # -> False
```

Alice views *every* folder, and *every* folder is a parent of `doc:1`. But to view `doc:1`
she needs to view *some* parent folder, and while no folder exists there is none. As soon
as any folder appears in a stored tuple, the answer changes:

```python
s.add_tuple("user:bob", "viewer", "folder:f1")
print(s.check("user:alice", "viewer", "doc:1"))           # -> True
```

This strict reading is the current mode on both backends. A lenient reading, where "all"
implies "some" even with no instances, is not implemented; it may be added later, and only
on both backends at once so that they never disagree.

## Summary

| topic | OpenFGA | this library |
| --- | --- | --- |
| conditions, modules, schema 1.2 | supported | refused (`SchemaError`) |
| undeclared names, reference cycles in the schema | refused (per OpenFGA's documentation) | refused when the schema is parsed |
| tupleset with a computed arm or a userset restriction | refused | refused, with the rewrite in the message |
| tupleset that is a union of direct blocks, or includes `T:*` | refused | accepted |
| userset `T:o#r` as a member of `T:o#r` | implicit | implicit, the same way |
| `from` whose tupleset type lacks the target relation | validation error | answers through self-membership |
| check with subject `user:*` under `but not` | announced: an error | the wildcard subject's own answer |
| cyclic tuple data | (not compared) | refused (`AdmissionRejected`) |
| recursion through `and` / `but not` | accepted (announced: will be refused) | refused by `Store` |
| check naming an undeclared relation | error | `False` |
| a few looser spellings (see the schema language reference) | not in the grammar | accepted |
| a trailing comment on a `model`, `schema` or `relations` line | refused | refused |
| wildcard usersets, star tuplesets, wildcard objects | not available | available, with a warning |
