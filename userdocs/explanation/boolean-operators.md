# How `and` and `but not` work

A schema can combine relations with `and` ("both") and `but not` ("this, unless that"):

```text
define viewer: [user, group#member] but not banned
define publisher: editor and approved
```

The set engine evaluates these directly. The graph index cannot, at least not in the way
it handles everything else, and the way it handles them anyway explains both their cost
and the one rule they impose on schemas: a relation may not recurse through them. This
page assumes you have read [How the graph index works](graph-index.md).

## Why they do not fit the closure

The graph index answers "does alice have `viewer`?" with "is there a path from alice to
`viewer`?". That works because, for `or` and `from`, having a relation means being
connected by some chain of tuples, and adding a tuple can only add chains.

Neither operator has that shape.

- **`but not` can take access away by adding a tuple.** Writing `user:mallory banned
  doc:1` must make mallory stop being a viewer. A path from mallory to `doc:1#viewer` is
  still there; it simply no longer counts. No set of paths means "connected, unless there
  is also this other path".
- **`and` needs two paths at once.** Alice is a `publisher` if she reaches `editor` *and*
  reaches `approved`. Neither path on its own is enough, so neither can be the edge that
  answers the check.

The set engine has no such problem. It computes each relation's members as a set when it
is asked, so `or`, `and` and `but not` are union, intersection and difference of sets.

## Derived relations

The graph index handles the operators by turning such relations into *derived* relations,
whose members it computes and stores itself rather than reading off paths.

A relation is derived if its definition uses `and` or `but not`, or if it depends on a
relation that is derived (a plain `or` over a derived relation is derived too). Every other
relation is handled exactly as before.

When the schema is compiled, each operand of an operator that is an ordinary relation
becomes an internal relation of its own. For
`define viewer: [user, user:*] but not banned`, the left-hand side gets an internal name
(`viewer.0`), and so does the right-hand side (`viewer.1`). Those internal relations are
ordinary paths in the closure, maintained as on the previous page: a tuple written as
`viewer` is stored on the internal relation that holds it, and `banned` tuples feed the
other one. Internal names contain a `.`, which is why a relation name in a schema may not.
They are not part of the readable surface: a check against `viewer.0` answers `False`.

What remains is to keep the members of the public `viewer` relation up to date as the
operands change.

## The delta processor

Every change the closure makes is recorded as a row in an outbox table: "this subject
gained (or lost) a path to this object's relation". After each write to the index, and in
the same transaction, a component called the **delta processor** reads those rows and, for
each derived relation they could affect, recomputes membership for the subjects and
objects involved, from the current state of the operands. It then stores the result:

- a concrete user who is a member, and is not already covered by a wildcard grant, gets a
  *derived edge* to the relation, so a check is an ordinary indexed lookup again;
- members who come from a wildcard grant get no edges at all. Instead, the object keeps a
  small *residue* record: which wildcard shapes cover the relation ("every user"), and
  which of the users they cover are excluded ("except mallory").

A check on a derived relation reads one possible edge and that residue record. So
`[user:*] but not banned` costs one record for the document, plus one entry for each
banned user, rather than an edge for every user in the system:

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define viewer: [user, user:*] but not banned
"""

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
store = Store(Session(engine), "public-docs", schema=SCHEMA)

store.add_tuple("user:*", "viewer", "doc:1")
store.add_tuple("user:mallory", "banned", "doc:1")

print(store.check("user:bob", "viewer", "doc:1"))  # -> True
print(store.check("user:mallory", "viewer", "doc:1"))  # -> False
```

```{image} img/boolean-residue.svg
:class: only-light
:alt: The tuple user:* viewer doc:1 becomes a closure edge to the leaf doc:1#viewer.0, and user:mallory banned doc:1 an edge to doc:1#viewer.1. The delta processor writes no derived edges for doc:1#viewer, only a residue record: covered by user:*, except user:mallory. So bob is a viewer and mallory is not.
```

```{image} img/boolean-residue-dark.svg
:class: only-dark
:alt: The tuple user:* viewer doc:1 becomes a closure edge to the leaf doc:1#viewer.0, and user:mallory banned doc:1 an edge to doc:1#viewer.1. The delta processor writes no derived edges for doc:1#viewer, only a residue record: covered by user:*, except user:mallory. So bob is a viewer and mallory is not.
```

The same structure shows through in a reverse lookup, which reports the wildcard grant as
a marker and mallory as an exclusion from it, rather than listing every user:

```python
found = store.lookup_reverse("viewer", "doc:1")
print(found.markers)  # -> {('user', '...', 'any')}
print(store.excluded_keys(found))  # -> {('user', 'mallory', '...')}
```

[Find who can access what](../how-to/query-access.md) explains how to read such a result.

A userset that qualifies (say `group:eng#member` as a viewer) is also recorded in the
residue rather than given an edge. An edge from the userset would carry through the
closure to every member of the group, including a member who is banned, and `but not` has
to be decided for each member separately.

### A question about `user:*`

You can ask a check about `user:*` itself. Under a wildcard grant with exclusions, it asks
whether the relation is granted through the wildcard, not whether every user happens to
qualify:

```python
print(store.check("user:*", "viewer", "doc:1"))  # -> True
```

`user:*` is covered by the `viewer` grant and is not covered by a `banned` grant; that
mallory individually is banned does not change it. Both backends give this answer. OpenFGA
has announced that it plans to return an error for this question instead (announced July
2026; no date has been set for the change); see
[Semantics and differences from OpenFGA](semantics-vs-openfga.md).

## Layers

Derived relations can depend on other derived relations:

```text
define viewer: [user] but not banned
define commenter: viewer and verified
```

`commenter` can only be computed once `viewer` is right. So the schema compiler sorts
derived relations into layers (*strata*): a relation's operands all sit in lower layers.
Layer 0 is the closure itself, holding the plain relations and the internal operand
relations (`viewer.0` holds the stored `viewer` tuples, `viewer.1` the `banned` side,
`commenter.0` the `verified` side). Every derived relation sits one layer above the
highest layer it reads:

```{image} img/boolean-layers.svg
:class: only-light
:alt: Three layers. Layer 0 is the closure, with the internal relations doc:1#viewer.0, doc:1#viewer.1 and doc:1#commenter.0. Layer 1 is doc:1#viewer, computed as viewer.0 but not viewer.1. Layer 2 is doc:1#commenter, computed as viewer and commenter.0.
```

```{image} img/boolean-layers-dark.svg
:class: only-dark
:alt: Three layers. Layer 0 is the closure, with the internal relations doc:1#viewer.0, doc:1#viewer.1 and doc:1#commenter.0. Layer 1 is doc:1#viewer, computed as viewer.0 but not viewer.1. Layer 2 is doc:1#commenter, computed as viewer and commenter.0.
```

After a write, the delta processor works in rounds. Each round reads the outbox rows that
the previous step added, recomputes the derived relations they touch, lowest layer first,
and writes the result as derived edges and residue rows, which add outbox rows of their
own. So a derived relation is always computed from layers that are already final, and a
change climbs the layers one round at a time until a round finds nothing to do. Here is
the write that bans alice, with alice already a viewer and verified:

```{image} img/boolean-cascade.svg
:class: only-light
:alt: One write, three steps. Layer 0: the write adds edges from alice to doc:1#banned and doc:1#viewer.1. Layer 1: viewer is recomputed for alice and her derived edge removed. Layer 2: commenter is recomputed from the updated viewer and her derived edge removed. Then the transaction commits.
```

```{image} img/boolean-cascade-dark.svg
:class: only-dark
:alt: One write, three steps. Layer 0: the write adds edges from alice to doc:1#banned and doc:1#viewer.1. Layer 1: viewer is recomputed for alice and her derived edge removed. Layer 2: commenter is recomputed from the updated viewer and her derived edge removed. Then the transaction commits.
```

Each recomputation works out a member's state from scratch and compares it with what is
stored, so repeating one changes nothing.

All of this happens inside the transaction that updates the index. In the default
synchronous mode that is the write itself, so a check made after `add_tuple` returns sees
every derived relation already settled.

## What it costs

The operators make writes more expensive, while reads stay bounded:

- a change to an operand recomputes every derived relation built on it, layer by layer.
  The deeper the layers, the more work each write does;
- adding or removing a wildcard grant that feeds a derived relation recomputes that
  relation for every subject that has state on that object. That is bounded by your data,
  not by the number of possible users, but it can be large;
- each object with a wildcard member of a derived relation has one residue row.

A check on a derived relation reads one edge probe plus one residue row.

## Why recursion through them is refused

Recursion is normal in schemas. `define viewer: [user] or viewer from parent` makes a
document's viewers include the viewers of its folder, its folder's folder, and so on, and
nested groups (`define member: [user, group#member]`) are the same idea. With `and` and
`but not` in the loop, there are two cases, and the library refuses both, for different
reasons.

### Recursion through the subtracted side

```text
define parent: [doc]
define viewer: [user] but not viewer from parent
```

This says "a viewer of a document is anyone granted it, unless they are a viewer of the
parent". A definition that refers to its own negation has no single meaning: on some data
no assignment of viewers satisfies it, and on other data several do. There is no right
answer for the backends to agree on, so both refuse the schema when it is parsed, with
{py:exc}`zanzibar.SchemaError`:

```python
from zanzibar import SchemaError

NEGATIVE = """
model
  schema 1.1
type user
type doc
  relations
    define parent: [doc]
    define viewer: [user] but not viewer from parent
"""

try:
    Store(Session(engine), "negative", schema=NEGATIVE)
    refused = False
except SchemaError as error:
    refused = "recursion through negation" in str(error)
print(refused)  # -> True
```

This is the standard rule for logic programs with negation, called *stratified negation*:
recursion may not pass through a "not". The usual intent can be written by putting the
recursion in the relation being subtracted, which does not depend on the one being
defined:

```text
define blocked: [user] or blocked from parent
define viewer: [user] but not blocked
```

### Recursion through the kept side, or through `and`

```text
define parent: [folder]
define viewer: ([user] or viewer from parent) but not blocked
```

This one has a clear meaning: viewers inherit down the folder tree, and at every level
the blocked users of that folder are removed. The set engine evaluates it. The graph index
cannot: `viewer` is derived, and a derived relation is computed from layers below it that
are already final, but this one depends on itself, so it belongs to no layer. Since a
{py:class}`zanzibar.Store` maintains a graph index, it refuses the schema with
{py:exc}`zanzibar.CyclicDerivedDependency`. A standalone
{py:class}`zanzibar.setengine.SetEngine` accepts it. The same holds for recursion through
either side of an `and`, such as a group whose `member` is
`[user, group#member] and verified`.

```python
from zanzibar import CyclicDerivedDependency

POSITIVE = """
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
    Store(Session(engine), "positive", schema=POSITIVE)
    refused = False
except CyclicDerivedDependency:
    refused = True
print(refused)  # -> True
```

The usual rewrite recurses on a plain relation and applies the operator once, on top:

```text
define viewer_base: [user] or viewer_base from parent
define viewer: viewer_base but not blocked
```

This is not the same schema; the differences, and the inheriting-block variant, are worked
through in [Rewrite a refused schema shape](../how-to/rewrite-refused-shape.md#recursion-through-and-or-but-not).
