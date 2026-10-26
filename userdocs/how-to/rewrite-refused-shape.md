# Rewrite a refused schema shape

When a schema is refused, the error names the relation at fault and, for most shapes,
what to write instead. This page shows how to read a refusal and works through the
rewrites you are most likely to need. The complete list of refused shapes is in
[the refused shapes reference](../reference/refused-shapes.md).

## Read the refusal

A schema is checked when you pass it to {py:class}`zanzibar.Store` (or to
{py:func}`zanzibar.parse_openfga_schema`, which runs the same checks without a
database). Catch {py:exc}`zanzibar.ZanzibarError` to handle every refusal at once.
Every refusal is also a `ValueError`. The individual types are listed in
[the exceptions reference](../reference/exceptions.md). A
{py:exc}`zanzibar.ShapeNoLongerAccepted` is a shape an earlier version accepted (its
`accepted_through` attribute names that version), and its `instead` attribute is the
rewrite that keeps the old meaning.

The message names the relation at fault, usually as `<type>#<relation>` or
`relation '<name>'`.

The examples on this page use a small helper that returns the refusal instead of raising
it:

```python
from zanzibar import ZanzibarError, parse_openfga_schema

HEADER = """
model
  schema 1.1
type user
"""


def refusal(schema):
    """The exception the schema is refused with, or None if it is accepted."""
    try:
        parse_openfga_schema(HEADER + schema)
    except ZanzibarError as exc:
        return exc
    return None


err = refusal("""
type doc
  relations
    define viewer: [user] or editor
""")
print(type(err).__name__)  # -> 'SchemaError'
print(str(err))  # -> 'doc#viewer: references undeclared relation doc#editor'
```

## A `from` tupleset must be a list of types

In `viewer from parent`, `parent` is the *tupleset*: the relation after `from`, whose
stored tuples link an object to the objects it inherits from. A tupleset may contain
only type restrictions: `[folder]`, `[folder, doc]`. Any other arm, such as
`or editor`, `and ...`, `but not ...` or a nested `from`, would be silently ignored,
because `from` follows only stored tuples. OpenFGA has the same rule. The message contains `a tupleset must be direct`.

```python
err = refusal("""
type folder
  relations
    define viewer: [user]
type doc
  relations
    define blocked_folder: [folder]
    define parent: [folder] but not blocked_folder
    define viewer: viewer from parent
""")
print("a tupleset must be direct" in str(err))  # -> True
```

Store the links on a relation of types only, and apply the operator to the relation
that uses the `from`:

```python
fixed = """
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder]
    define blocked: [user]
    define viewer: (viewer from parent) but not blocked
"""
print(refusal(fixed))  # -> None
```

If the old tupleset was an alias of another relation (`define parent: folder_link`),
use that relation in the `from` directly: `viewer from folder_link`.

## A `from` tupleset may not hold a userset

`define parent: [folder#member]` under `viewer from parent` is refused, because `from`
would ignore the `#member`. OpenFGA has the same rule. The message contains
`a tupleset may not restrict to a userset` and names the rewrite.

```python
err = refusal("""
type folder
  relations
    define member: [user]
    define viewer: [user]
type doc
  relations
    define parent: [folder#member]
    define viewer: viewer from parent
""")
print("a tupleset may not restrict to a userset" in str(err))  # -> True
```

Store the bare link, and if you also wanted "the members of the parent folder", spell
that as its own relation:

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

FIXED = """
model
  schema 1.1
type user
type folder
  relations
    define member: [user]
    define viewer: [user]
type doc
  relations
    define parent: [folder]
    define parent_member: member from parent
    define viewer: viewer from parent
"""

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
store = Store(Session(engine), "tupleset-fix", schema=FIXED)

store.add_tuple("folder:f", "parent", "doc:1")        # was "folder:f#member"
store.add_tuple("user:alice", "viewer", "folder:f")
store.add_tuple("user:bob", "member", "folder:f")

print(store.check("user:alice", "viewer", "doc:1"))  # -> True
print(store.check("user:bob", "parent_member", "doc:1"))  # -> True
```

## Every reference must be declared

A schema must be self-consistent: every relation, type and tupleset it names must be
declared. An undeclared name is refused rather than read as "nobody", because it is
almost always a typo.

| refused | message contains | fix |
| --- | --- | --- |
| `define viewer: [user] or editor`, no `editor` | `references undeclared relation doc#editor` | declare `define editor: [user]` on the same type, or fix the spelling |
| `[group#member]`, `group` declares no `member` | `names an undeclared relation group#member` | declare it, or write `[group]` if the group object itself was meant |
| `[usr]` with no `type usr` | `names an undeclared type 'usr'` | fix the spelling, or add `type usr` |
| `viewer from parent`, no `parent` | `is undeclared relation doc#parent` | declare the link: `define parent: [folder]` |
| `viewer from parent`, `parent: [folder]`, `folder` has no `viewer` | `is an undeclared relation on every tupleset type` | declare `viewer` on `folder`, or let `parent` admit a type that has it |

```python
err = refusal("""
type folder
  relations
    define owner: [user]
type doc
  relations
    define parent: [folder]
    define viewer: viewer from parent
""")
print("is an undeclared relation on every tupleset type" in str(err))  # -> True
```

## Relations may not refer to each other in a loop

Two relations that name each other (`define a: [user] or b` and `define b: a`) are
refused with `reference cycle`. There is no rewrite for a pure loop: delete one
direction. Recursion through stored tuples is allowed and is how nesting works, for
example `define member: [user, group#member]` or `define viewer: [user] or viewer from
parent` (see [patterns](patterns.md)).

```python
err = refusal("""
type doc
  relations
    define a: [user] or b
    define b: a
""")
print(str(err).startswith("reference cycle"))  # -> True
```

## Parenthesise `but not`, and `or` mixed with `and`

`but not` may not share a level with `or`, `and` or a second `but not`, and `or` and
`and` may not be mixed without parentheses, because each such expression has two
readings. OpenFGA's grammar refuses the first too.

```python
err = refusal("""
type doc
  relations
    define editor: [user]
    define viewer: [user]
    define blocked: [user]
    define can_read: editor or viewer but not blocked
""")
print(type(err).__name__)  # -> 'ShapeNoLongerAccepted'
fixed = """
type doc
  relations
    define editor: [user]
    define viewer: [user]
    define blocked: [user]
    define can_read: (editor or viewer) but not blocked
"""
print(refusal(fixed))  # -> None
```

Write the reading you mean: `(a or b) but not c`, `a or (b but not c)`,
`(a or b) and c` or `a or (b and c)`.

## Recursion through `and` or `but not`

A relation that reaches itself through `and` or `but not` cannot be served by the
[graph index](../explanation/graph-index.md), so {py:class}`zanzibar.Store` refuses it
with {py:exc}`zanzibar.CyclicDerivedDependency` (why: [how `and` and `but not`
work](../explanation/boolean-operators.md)). Typical cases are a group with a ban list and
a folder tree with a block list:

```python
from zanzibar import CyclicDerivedDependency

err = refusal("""
type folder
  relations
    define parent: [folder]
    define blocked: [user]
    define viewer: ([user] or viewer from parent) but not blocked
""")
print(isinstance(err, CyclicDerivedDependency))  # -> True
```

Recurse on a plain relation and apply the operator on top:

```python
fixed = """
type folder
  relations
    define parent: [folder]
    define blocked: [user]
    define viewer_base: [user] or viewer_base from parent
    define viewer: viewer_base but not blocked
"""
print(refusal(fixed))  # -> None
```

This is **not** the same schema, and no rewrite reproduces the refused form exactly. In
the refused form a block on a folder stops access inherited *through* that folder, but a
grant made directly on a folder below it still works. In the rewrite, `blocked` applies
only at the folder you check, so access inherited from above the block still reaches the
folders below it.

To make the block reach down the tree, make the block list inherit as well:
`define blocked: [user] or blocked from parent`. That is stronger than the refused form:
it denies everything below the blocked folder, grants made lower down included. The full
example is in [patterns](patterns.md), under "Block lists".

A relation that depends on itself through the right-hand side of `but not` (for example
`define viewer: [user] but not viewer from parent`) is refused with
`recursion through negation`: it has no single meaning. The fix is the same shape:
subtract a separate relation and put the recursion in it.

## Names

Declared type and relation names must match `[A-Za-z0-9_./@+=-]` (1 to 256
characters), the character set a tuple may use, so that a write can reach them. A
relation name may not contain `.`, because the library uses `.` for names it generates;
a type name may. Use `_` instead: `define can_view: [user]`.

```python
err = refusal("""
type doc
  relations
    define can.view: [user]
""")
print(type(err).__name__)  # -> 'SchemaError'
```

## Header lines, conditions and modules

| refused | rewrite |
| --- | --- |
| `schema 1.2` (or any version but `1.1`) | `schema 1.1`, or delete the line; the header is optional |
| `relations define viewer: [user]`, `model x`, `schema 1.1 # comment` | one keyword per line; each `define` and each comment on its own line |
| conditions, modules | no rewrite; see [Port an OpenFGA model](port-openfga.md#2-fix-what-is-refused) |
| a second `type doc` block, or a second `define viewer` in one type | merge them: one `type` block per type, one `define` per relation joining the arms with `or` |
| an empty schema, or one where no type has a `define` | declare at least one relation; a store saves its schema once and could never be used |

## When the refused schema is already stored

If a store was created by an older version with a shape this version refuses, opening
it raises {py:exc}`zanzibar.PersistedSchemaRefused`. Its `instead` attribute is the
rewrite that keeps the meaning the store was serving. A store's schema cannot be
changed, so the rewritten schema needs a new store id with the tuples copied across:
see [Change a schema](change-schema.md).
