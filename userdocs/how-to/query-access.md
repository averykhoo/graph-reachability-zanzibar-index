# Find who can access what

`check` answers one yes/no question. This page covers the three list questions:

| question | call | served by |
|---|---|---|
| What can this subject reach? | {py:meth}`Store.lookup <zanzibar.Store.lookup>` | the graph index |
| Who can reach this object's relation? | {py:meth}`Store.lookup_reverse <zanzibar.Store.lookup_reverse>` | the graph index |
| Who has this relation on the object (Zanzibar Expand)? | {py:meth}`Store.expand <zanzibar.Store.expand>` | the set engine |

A store keeps two backends that give the same answers: the **graph index**, a precomputed
table of who reaches what, and the **set engine**, which computes answers from the stored
tuples in memory. Which one serves a call matters only for freshness on an async store;
[The two backends](../explanation/two-backends.md) explains them.

`lookup` and `lookup_reverse` return a {py:class}`zanzibar.LookupResult`, which you read
through {py:meth}`Store.result_keys <zanzibar.Store.result_keys>` and
{py:meth}`Store.excluded_keys <zanzibar.Store.excluded_keys>`. `expand` returns a
{py:class}`zanzibar.ExpandResult`, which needs no translation.

Every answer comes back as `(type, name, predicate)` keys. The predicate is a relation name,
or `"..."` for a bare subject such as a user: `("user", "alice", "...")` is the user
`user:alice`, `("group", "eng", "member")` is the userset `group:eng#member`, and
`("doc", "d1", "viewer")` is "viewer of `doc:d1`".

## The example store

The examples on this page share one store. `doc:d1` is shared with the `eng` group, whose
member mallory is banned from it. `doc:d2` is public (`user:*`) except for mallory. carol
can view the folder that holds `doc:d1`.

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

SCHEMA = """
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type folder
  relations
    define viewer: [user, group#member]
type doc
  relations
    define parent: [folder]
    define banned: [user]
    define viewer: [user, user:*, group#member] but not banned
    define can_read: viewer or viewer from parent
"""

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
session = Session(engine)
store = Store(session, "my-app", schema=SCHEMA)

store.add_tuple("user:alice", "member", "group:eng")
store.add_tuple("user:mallory", "member", "group:eng")
store.add_tuple("group:eng#member", "viewer", "doc:d1")
store.add_tuple("user:mallory", "banned", "doc:d1")
store.add_tuple("folder:f1", "parent", "doc:d1")
store.add_tuple("user:carol", "viewer", "folder:f1")
store.add_tuple("user:*", "viewer", "doc:d2")
store.add_tuple("user:mallory", "banned", "doc:d2")
```

## List what a subject can access

Pass the subject to `lookup`, in the same forms `check` takes: `"user:alice"`, a userset
such as `"group:eng#member"`, or the three parts `lookup("...", "user", "alice")`. The
three-part form takes the parts in the order *predicate, type, name*: `"..."` is the
predicate of a plain user (the user themselves), so `lookup("member", "group", "eng")` is
the same as `lookup("group:eng#member")`. Translate the result with `result_keys`:

```python
found = store.lookup("user:alice")
print(sorted(store.result_keys(found)))  # -> [('doc', 'd1', 'can_read'), ('doc', 'd1', 'viewer'), ('doc', 'd2', 'can_read'), ('doc', 'd2', 'viewer'), ('group', 'eng', 'member')]
```

The result holds every relation alice reaches on every object, usersets on the way
included (`group:eng#member`). The public grant on `doc:d2` is listed as a concrete
object: from `lookup`, a `user:*` grant needs no special reading.

A `lookup` for a userset subject such as `"group:eng#member"` is slow on a large store
whose schema uses `and` / `but not`: it took seconds at 10,000 tuples in a benchmark. See
[Lookups for a userset](../explanation/limits.md#lookups-for-a-userset-slow-on-large-stores-with-and--but-not)
before you put one on a request path.

To ask a narrower question, filter by object type and/or relation. "Which documents can
alice view?":

```python
docs = store.lookup("user:alice", object_type="doc", relation="viewer")
print(sorted(store.result_keys(docs)))  # -> [('doc', 'd1', 'viewer'), ('doc', 'd2', 'viewer')]
```

To get bare object names, take the middle field:

```python
print(sorted(name for _type, name, _rel in store.result_keys(docs)))  # -> ['d1', 'd2']
```

The `but not banned` rule is already applied. mallory is a member of `eng`, but she is banned
from both documents, so she can view neither:

```python
mallory = store.lookup("user:mallory", object_type="doc", relation="viewer")
print(store.result_keys(mallory))  # -> set()
```

A filter that names a type or relation the schema does not declare matches nothing (it is
not an error), the same way `check` answers `False` for an undeclared name:

```python
print(store.result_keys(store.lookup("user:alice", object_type="invoice")))  # -> set()
```

## List who can access an object

Pass the relation and the object to `lookup_reverse`:

```python
who = store.lookup_reverse("viewer", "doc:d1")
print(sorted(store.result_keys(who)))  # -> [('doc', 'd1', 'viewer'), ('group', 'eng', 'member'), ('user', 'alice', '...')]
```

Three kinds of key come back:

- `("user", "alice", "...")`: a user who is allowed. Members of a granted group are listed
  one by one, and refused members are left out, so mallory is missing.
- `("group", "eng", "member")`: the userset `group:eng#member` is itself an allowed subject.
  This is **not** a claim about each of its members (see the next section).
- `("doc", "d1", "viewer")`: a userset is a member of itself, as in OpenFGA, so
  `doc:d1#viewer` is always a viewer of `doc:d1`. It is listed even when no tuple names it.

To keep only the users, filter by subject type and predicate. `subject_predicate="..."`
keeps bare subjects:

```python
users = store.lookup_reverse("viewer", "doc:d1", subject_type="user", subject_predicate="...")
print(sorted(store.result_keys(users)))  # -> [('user', 'alice', '...')]
```

`subject_predicate="member"` keeps only `member` usersets:

```python
groups = store.lookup_reverse("viewer", "doc:d1", subject_predicate="member")
print(sorted(store.result_keys(groups)))  # -> [('group', 'eng', 'member')]
```

Rules that reach through other objects are followed for you. `can_read` adds the viewers of
the parent folder, so carol appears:

```python
readers = store.lookup_reverse("can_read", "doc:d1", subject_type="user", subject_predicate="...")
print(sorted(store.result_keys(readers)))  # -> [('user', 'alice', '...'), ('user', 'carol', '...')]
```

## Do not expand a userset key yourself

A userset key in a `lookup_reverse` result means the userset is allowed. It is tempting to
replace it with that group's members. Do not: the members a `but not` refuses are already
left out of the result, and expanding the group adds them back.

Here is the mistake, done on purpose:

```python
# WRONG: replacing group:eng#member with every member of eng
members = store.lookup_reverse("member", "group:eng", subject_type="user", subject_predicate="...")
naive = {name for _t, name, _p in store.result_keys(members)}
print(sorted(naive))  # -> ['alice', 'mallory']
print(store.check("user:mallory", "viewer", "doc:d1"))  # -> False
```

The naive list grants mallory, but mallory is banned. The users allowed are the keys of type
`user` in the `lookup_reverse` result (above: only alice), plus any `user` marker, minus
`excluded_keys` (next section). For any single subject you are unsure about, ask `check`.

## Read wildcard grants

A `user:*` tuple grants every user, including users no tuple mentions. A list of names
cannot say that, so `lookup_reverse` reports it as a **marker** in `result.markers`,
together with the users that the marker covers but who are refused:

```python
public = store.lookup_reverse("viewer", "doc:d2", subject_type="user", subject_predicate="...")
print(store.result_keys(public))  # -> set()
print(public.markers)  # -> {('user', '...', 'any')}
print(store.excluded_keys(public))  # -> {('user', 'mallory', '...')}
```

Read the three parts together: "the listed keys, plus every subject of a marker's shape,
minus the excluded keys". Here that is "every user except mallory". A marker read without
its exclusions grants too much, so always subtract `excluded_keys`.

A marker is a `(type, predicate, variant)` triple; in a `lookup_reverse` result, the
variant that carries meaning is `"any"`, a subject-side wildcard such as `user:*`.
{ref}`Result markers <api-result-markers>` lists every variant and what it claims, and has
a helper that tests whether one subject is covered (a `LookupResult` has no `in` test of
its own; `expand`, below, gives a result that does).

From `lookup`, a `user:*` grant needs none of this: the objects it opens are listed as keys
for every user. zed has no tuple at all, yet:

```python
zed = store.lookup("user:zed", object_type="doc", relation="viewer")
print(sorted(store.result_keys(zed)))  # -> [('doc', 'd2', 'viewer')]
```

A store opened with `object_wildcard_shapes` (an extension beyond OpenFGA) can also return
an object-side `"all"` marker from `lookup`, meaning "this relation on every object of the
type"; see
[How wildcards show up in lookups](../explanation/wildcard-extensions.md#how-wildcards-show-up-in-lookups).

## Expand a relation on one object

`expand` answers "who has this relation on this object?" with an
{py:class}`zanzibar.ExpandResult`. It holds keys directly, so there is no translation step:

```python
exp = store.expand("viewer", "doc:d1")
print(sorted(exp.keys))  # -> [('doc', 'd1', 'viewer'), ('group', 'eng', 'member'), ('user', 'alice', '...')]
```

The same rules apply as for `lookup_reverse`: the userset `group:eng#member` is a member
in its own right, its allowed members are already listed, and expanding it again yourself
would re-admit mallory.

An `ExpandResult` has three parts:

- `keys`: subjects listed one by one;
- `markers`: `(type, predicate)` shapes granted through a wildcard, where every subject of
  that shape is a member;
- `excluded_keys`: subjects a marker covers that are not members. Always subtract them.

On the public document:

```python
exp2 = store.expand("viewer", "doc:d2")
print(sorted(exp2.keys))  # -> [('doc', 'd2', 'viewer')]
print(exp2.markers)  # -> frozenset({('user', '...')})
print(exp2.excluded_keys)  # -> frozenset({('user', 'mallory', '...')})
```

You do not have to combine the three parts yourself. `key in result` does it, and so does
{py:meth}`ExpandResult.covers <zanzibar.ExpandResult.covers>`:

```python
print(("user", "zed", "...") in exp2)  # -> True
print(("user", "mallory", "...") in exp2)  # -> False
print(exp2.covers(("user", "alice", "...")))  # -> True
```

`ExpandResult.markers` are `(type, predicate)` pairs, without the variant of a
`LookupResult` marker; {ref}`Result markers <api-result-markers>` shows how to compare the
two shapes.

### `lookup_reverse` or `expand`?

Both answer "who has this relation on this object?" and give the same keys for the same
question. Choose by what you need around the answer:

- Use `lookup_reverse` when you want the `subject_type` / `subject_predicate` filters.
  `expand` has none, so filter its keys yourself, for example
  `{k for k in exp.keys if k[0] == "user" and k[2] == "..."}`.
- Use `expand` when you want keys with no translation step, or when the read must keep
  working while the index is stalled. `expand` is served by the set engine, while
  `lookup_reverse` reads the index and raises {py:exc}`zanzibar.IndexStalled` on a stalled
  one (see [Freshness](#freshness)).

## Read a lookup result before the next write

A `LookupResult` is a snapshot of the moment it was taken. A later write can change who has
access, and the old result does not notice: after any write, run the lookup again rather
than reuse an old result.

`LookupResult.node_ids` and `excluded_node_ids` are database row ids, so translate them with
`result_keys` / `excluded_keys` straight away. If a later write deleted a node the result
names, translation raises {py:exc}`zanzibar.StaleLookupIds` (a `KeyError`) rather than
returning a wrong key:

```python
import zanzibar

before = store.lookup_reverse("viewer", "doc:d1")
store.remove_tuple("group:eng#member", "viewer", "doc:d1")
try:
    store.result_keys(before)
except zanzibar.StaleLookupIds:
    print("stale")  # -> 'stale'
after = store.lookup_reverse("viewer", "doc:d1")
print(sorted(store.result_keys(after)))  # -> [('doc', 'd1', 'viewer')]
```

`StaleLookupIds` catches only that case. It is not a staleness check. A write that removes
an edge but leaves every node in place (here, alice leaving `eng`) leaves the old result
translating without error, and its keys are now wrong:

```python
store.add_tuple("group:eng#member", "viewer", "doc:d1")   # restore the share
old = store.lookup("user:alice", object_type="doc", relation="viewer")
store.remove_tuple("user:alice", "member", "group:eng")
print(sorted(store.result_keys(old)))  # -> [('doc', 'd1', 'viewer'), ('doc', 'd2', 'viewer')]
print(store.check("user:alice", "viewer", "doc:d1"))  # -> False
new = store.lookup("user:alice", object_type="doc", relation="viewer")
print(sorted(store.result_keys(new)))  # -> [('doc', 'd2', 'viewer')]
session.close()
```

An `ExpandResult` holds keys, not ids, so it can never raise `StaleLookupIds`. It is a
snapshot in the same way: run `expand` again after a write.

A result also holds `implicit_keys` / `implicit_excluded_keys`, for answers that have no row
in the index (such as `doc:d1#viewer` being a viewer of `doc:d1` on an empty store).
`result_keys` and `excluded_keys` already fold these in, which is why you should always
read a result through them rather than through `node_ids`.

## Freshness

With the default `sync=True`, a write is visible to the next lookup on the same instance.
On an async store (`sync=False`), `lookup` and `lookup_reverse` read the index and never
fall back: behind a token they raise {py:exc}`zanzibar.LookupNotFresh`, and on a stalled
index {py:exc}`zanzibar.IndexStalled`, a subclass of `LookupNotFresh` (so put
`except IndexStalled` first if you handle the two differently); `expand` is served by the
set engine instead.
[What can be stale, and in which direction](../explanation/consistency.md#what-can-be-stale-and-in-which-direction)
has the full table, [Use async mode and freshness tokens](async-tokens.md) the recipes, and
[Handle errors](errors.md) what to do with each exception.
