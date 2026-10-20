# How the graph index works

The graph index is the backend that does its work when you write, so that a check is just
a lookup. [The two backends](two-backends.md) explains why the library has it; this
page explains how it stays exact while tuples are added and removed, and how it handles
`user:*` without a row for every user. Everything here is about the relations built from
`or`, `from` and direct grants; `and` and `but not` need an extra mechanism, described in
[How `and` and `but not` work](boolean-operators.md).

## Tuples as a graph

The index treats every `type:name#relation` as a node of a directed graph, and every user
as a node too (`user:alice` is the node `user:alice` with no relation). A tuple is an edge
from its user to its object's relation: `group:eng#member viewer doc:roadmap` is an edge
from the node `group:eng#member` to the node `doc:roadmap#viewer`.

The schema's rewrites add more edges when tuples are written, so that every way of having
a relation becomes a path:

- `define viewer: [user] or editor` turns each `editor` tuple into an `editor` edge plus a
  matching `viewer` edge. Writing `user:alice editor doc:1` adds an edge from `user:alice`
  to both `doc:1#editor` and `doc:1#viewer`.
- `define viewer: ... or viewer from parent` turns each `parent` tuple into a link
  between the viewers. Writing `folder:p parent doc:1` adds an edge from `folder:p#viewer`
  to `doc:1#viewer`, so every viewer of the folder now has a path to the document.

"Does alice have `viewer` on `doc:1`?" is then the question "is there a path from
`user:alice` to `doc:1#viewer`?"

## Remembering every path

Following paths on every check is what the set engine does. The graph index instead stores
the answer for every pair of nodes at once: a row for each pair `(a, b)` with at least one
path from `a` to `b`. That table is the *transitive closure* of the graph. A check is a
lookup of one row; a lookup ("what can alice reach?") reads the rows that start at
`user:alice`; a reverse lookup ("who can view `doc:1`?") reads the rows that end at
`doc:1#viewer`.

Adding an edge is easy to reflect in such a table. When an edge `u -> v` appears, every
node that reaches `u` now reaches every node that `v` reaches, so the index adds those
pairs.

Removing an edge is the hard part. If the edge `u -> v` goes away, does `a` still reach
`b`? Perhaps there was another path that did not use that edge. A table of yes/no answers
cannot tell: after "yes, for two reasons", it has no way to take one reason away.

## Counting paths

The index solves this by counting. Each row stores not just "there is a path" but **how
many distinct paths** there are, and separately how many of them are direct edges. The
counts can then be updated exactly in both directions.

In a graph with no cycles, a path can use a given edge at most once. So when a new edge
`u -> v` is added, the new paths from `a` to `b` are exactly the combinations of a path
from `a` to `u` with a path from `v` to `b`, and the count goes up by their product:

```text
paths(a, b)  +=  paths(a, u) × paths(v, b)
```

Here `paths(x, x)` counts as 1, for the empty path. Removing the edge subtracts the same
product, computed without the edge. A pair whose count reaches zero is no longer connected,
and its row is deleted. Nothing has to be searched or recomputed from scratch: a removal is
local arithmetic over the rows that touch the edge's two ends.

You can see the counts in the index's tables. The table layout is an implementation detail
and may change; it is shown here only to make the idea concrete. Alice is in `eng`, `eng`
is inside `staff`, and both groups are granted `doc:1`, so alice has two paths to it:

```python
from sqlmodel import SQLModel, Session, create_engine, select
from zanzibar import Store
from zanzibar.graphindex import Edge, Node

SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define viewer: [user, group#member]
"""

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
session = Session(engine)
store = Store(session, "counting", schema=SCHEMA)

store.add_tuple("user:alice", "member", "group:eng")
store.add_tuple("group:eng#member", "member", "group:staff")
store.add_tuple("group:eng#member", "viewer", "doc:1")
store.add_tuple("group:staff#member", "viewer", "doc:1")


def path_count(subject, obj):
    """Number of paths the index has recorded between two nodes."""
    def node_id(type_, name, predicate):
        node = session.exec(select(Node).where(
            Node.store_id == "counting", Node.type == type_, Node.name == name,
            Node.predicate == predicate, Node.wildcard == "")).one()
        return node.id
    row = session.exec(select(Edge).where(
        Edge.store_id == "counting",
        Edge.subject_id == node_id(*subject),
        Edge.object_id == node_id(*obj))).first()
    return 0 if row is None else row.indirect_edge_count


alice = ("user", "alice", "...")
doc_viewer = ("doc", "1", "viewer")
print(path_count(alice, doc_viewer))  # -> 2
```

The two paths are alice → `eng` → `doc:1`, and alice → `eng` → `staff` → `doc:1`. Remove
one grant and the count drops to one; alice can still view the document, and nothing had
to be searched to find that out:

```python
store.remove_tuple("group:eng#member", "viewer", "doc:1")
print(path_count(alice, doc_viewer))  # -> 1
print(store.check("user:alice", "viewer", "doc:1"))  # -> True

store.remove_tuple("group:staff#member", "viewer", "doc:1")
print(store.check("user:alice", "viewer", "doc:1"))  # -> False
```

## Why cycles are refused

Counting only works without cycles. With a cycle, a path could go round it any number of
times, the number of paths would be infinite, and the arithmetic above would no longer be
exact. So the index refuses any write that would close a cycle in the graph: a group
inside itself, two groups inside each other, a folder that is its own ancestor.

```python
from zanzibar import AdmissionRejected

try:
    store.add_tuple("group:staff#member", "member", "group:eng")  # eng is already in staff
    refused = False
except AdmissionRejected:
    refused = True
print(refused)  # -> True
```

For any schema a `Store` accepts, its set engine refuses the same writes, so the two
backends accept the same data.
OpenFGA, by contrast, accepts cyclic tuples, so data imported from it may need checking
first; see [Semantics and differences from OpenFGA](semantics-vs-openfga.md).

## What a write costs

Adding an edge `u -> v` touches one row for each pair of a node that reaches `u` and a node
that `v` reaches. In permission data, that product can be large: granting a big group
access to a folder at the top of a deep tree creates a row for every member of the group
and every relation on everything under the folder. This is the price of a one-lookup
check, and it is paid inside the write.

Two limits stop a single write from growing without bound:

- adding an edge `u -> v` that would touch more closure rows than a configurable cap
  (100,000 by default) is refused with {py:exc}`zanzibar.ClosureFanoutExceeded`, and the
  write changes nothing. The rows counted are those for the pairs above, roughly the
  nodes that reach `u` times the nodes `v` reaches, whether or not they already exist. The cap is checked for each edge a
  write adds, and one tuple can add several edges through the schema's rewrites. It
  applies when the index is updated as part of the write, which is the default;
- a write that would push a path count beyond what the index can store (2³¹ − 1 paths
  between one pair) is refused with {py:exc}`zanzibar.PathCountExceeded`.

With `sync=False`, the index is updated later, after the write has been accepted, so
neither limit can refuse it then; [Consistency](consistency.md) describes what happens
instead.

[Limits and costs](limits.md) and [Cap write fan-out](../how-to/fanout-cap.md) go into
both.

## Wildcards without listing everyone

A tuple such as `user:* viewer folder:p` grants the folder to every user, including users
the store has never heard of. Writing an edge to every existing user would be wrong twice
over: it would miss users who appear later, and it would miss users who never appear in
any tuple at all but are still asked about.

Instead, the index gives the wildcard a node of its own, written here `user:*`, and the
grant becomes one edge from that node, exactly as if `user:*` were a single user.
`folder:p parent doc:1` then carries it on to `doc:1#viewer` like any other path. A check
for `user:bob` makes two probes in the same query: is there a path from `user:bob`, and is
there a path from `user:*`? Either one is enough. Because the second probe does not need
a node for bob, a user who appears in no tuple at all is still a viewer, and a check never
creates a node.

```python
SCHEMA_PUBLIC = """
model
  schema 1.1
type user
type folder
  relations
    define viewer: [user, user:*]
type doc
  relations
    define parent: [folder]
    define viewer: [user] or viewer from parent
"""

public = Store(Session(engine), "public", schema=SCHEMA_PUBLIC)
public.add_tuple("user:*", "viewer", "folder:p")
public.add_tuple("folder:p", "parent", "doc:1")
print(public.check("user:someone-new", "viewer", "doc:1"))  # -> True
```

This is why `check` stays a small, fixed number of indexed lookups whatever the data: the paths through the middle of the graph are all stored, and only the two ends of
the question (the user asked about, and the object asked about) can involve a wildcard
that is not.

### "Some" and "all"

The library also supports wildcards in places OpenFGA does not: usersets such as
`group:*#member` ("the members of every group") and, if you declare them, objects such as
`folder:*` ("every folder"). These use two kinds of wildcard node:

- an *any* node, meaning "some instance". Every concrete instance has an edge into it
  ("`group:eng#member` is an instance of `group:*#member`"), and grants made to the
  wildcard leave from it.
- an *all* node, meaning "every instance". Grants made on the wildcard object arrive at
  it, and it has an edge out to every concrete instance ("what is granted on every folder
  is granted on `folder:p`").

A wildcard userset shape such as `group:*#member` gets an *any* node, a declared wildcard
object such as `folder:*` gets an *all* node, and a shape that is both gets both.

These extra instance edges, called *bridges*, are what makes the stored paths through the
middle of the graph complete. They cost one edge per instance, plus closure rows, as soon
as the shape is declared, even before any wildcard tuple is written. The plain `[user:*]`
needs no bridges at all.

There is deliberately no edge from an *any* node to an *all* node. If there were, being
one user would grant what was given to every user: alice would reach bob through
`user:*`. A consequence is that "every folder" leads to "some folder" only through a folder
that actually exists. Suppose alice is a viewer of `folder:*`, and a document's parent is
`folder:*`, so that viewers of any folder can view it. While no folder is stored, alice
cannot view the document; as soon as one folder exists, she can. Both backends answer
that way.
[Wildcard extensions beyond OpenFGA](wildcard-extensions.md) covers these extensions, why
they emit {py:class}`zanzibar.UnprovenExtensionWarning`, and how to avoid them.

## Where the index lives

The index is a set of ordinary tables in your database, next to the tuple log, and it is
written in the same transaction as the write that changed it (or, with `sync=False`, in the
transaction that catches it up). It is derived data: given the stored tuples, there is
exactly one correct index, and {py:func}`zanzibar.store.rebuild_index` can rebuild it from
them at any time, provided the tuples fit the index's
[limits](limits.md). [Database tables](../reference/tables.md) lists the tables.
