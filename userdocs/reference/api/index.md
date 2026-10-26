# Python API

The public Python API. A name is public if it is exported from the top-level `zanzibar`
package or listed in a subpackage's `__all__`; anything else can change without notice.
Each subpackage's `__all__` is its public surface. A name that starts with an underscore
is internal, even where a module happens to make it importable.
Most entries are generated from the docstrings; a few (type aliases, constants, and
members whose docstrings describe internals) are written by hand on these pages.

```{eval-rst}
.. py:module:: zanzibar
```

## The top-level package

Most programs need only the names importable from `zanzibar` itself. They load lazily:
`import zanzibar` imports none of the library's modules. The database stack (SQLModel and
SQLAlchemy) is imported the first time you touch a name that needs it: `Store`,
`ExpandResult`, `LookupResult`, and the exceptions defined by the store and the two
backends. `parse_openfga_schema` and the exceptions and warning defined in
`zanzibar.schema` (from `ZanzibarError` to `UnprovenExtensionWarning`) never import it.

| Name | Kind | Documented at |
|---|---|---|
| `Store` | class | {py:class}`zanzibar.Store` (on the [zanzibar.store](store.md) page) |
| `ExpandResult` | class | {py:class}`zanzibar.ExpandResult` (on the [zanzibar.store](store.md) page) |
| `LookupResult` | class | {py:class}`zanzibar.LookupResult` (on the [zanzibar.graphindex](graphindex.md) page) |
| `parse_openfga_schema` | function | {py:func}`zanzibar.parse_openfga_schema` (on the [zanzibar.schema](schema.md) page) |
| `__version__` | string | {py:data}`zanzibar.__version__`, below |
| every exception, and `UnprovenExtensionWarning` | exception classes | the [Exceptions](../exceptions.md) page |

`Store`, `ExpandResult`, `LookupResult` and `parse_openfga_schema` are also importable
from their subpackage (`from zanzibar.store import Store` and `from zanzibar import Store`
give the same object). Each is documented once, under its top-level name.

```python
import sys
import zanzibar

print("sqlmodel" in sys.modules)  # -> False
zanzibar.parse_openfga_schema
zanzibar.SchemaError
print("sqlmodel" in sys.modules)  # -> False
from zanzibar.store import Store
print(Store is zanzibar.Store)  # -> True
print("sqlmodel" in sys.modules)  # -> True
```

```{eval-rst}
.. py:data:: __version__
   :type: str

   The installed version of the library as a string, for example ``"0.1.0"``.
```

## Subpackages

| Subpackage | Contents |
|---|---|
| [zanzibar.store](store.md) | The composed store: the tuple log, the schema record, `Store`, and the offline build functions. Start here. |
| [zanzibar.schema](schema.md) | Parsing, converting and compiling schemas; the schema AST; identifier helpers. |
| [zanzibar.setengine](setengine.md) | The set engine: stores raw tuples and computes answers on each read. |
| [zanzibar.graphindex](graphindex.md) | The graph index: a precomputed closure, so a check is a few indexed lookups. |

Exceptions have one public home: `zanzibar`. No subpackage lists an exception or the
warning in its `__all__`. An older import such as `from zanzibar.store import StaleRead`
still gives the same class, but it is not part of the API. The exceptions are documented
on the [Exceptions](../exceptions.md) page.

(api-result-markers)=
## Result markers

{py:class}`zanzibar.LookupResult` and {py:class}`zanzibar.ExpandResult` both report access
granted through a wildcard as *markers*, in different shapes:

| Result | Field | Element shape |
|---|---|---|
| `LookupResult` (from `lookup`, `lookup_reverse`) | `markers` | `(type, predicate, variant)` |
| `ExpandResult` (from `expand`) | `markers` | `(type, predicate)` |

`predicate` is `"..."` for a bare subject such as a user, or a relation name for a userset.

The `variant` of a `LookupResult` marker is one of:

- `"any"`: a subject-side wildcard. It is meaningful in a `lookup_reverse` result, where
  `("user", "...", "any")` means every user (a `user:*` tuple), and
  `("group", "member", "any")` means every `member` userset of every group (a
  `[group:*#member]` grant, an extension).
- `"all"`: an object-side wildcard, which exists only when the store is opened with
  `object_wildcard_shapes`. It is meaningful in a `lookup` result, where
  `("doc", "reader", "all")` means reader of every doc (a `doc:*` tuple).

An `"all"` marker in a `lookup_reverse` result, or an `"any"` marker in a `lookup` result,
is a by-product of how wildcards are stored and makes no claim on its own.

For the same grant, a `lookup_reverse` marker `(t, p, "any")` and an `ExpandResult` marker
`(t, p)` have the same first two fields.

The subjects a marker covers but that are refused (by a `but not`, or an `and`, under a
wildcard grant) are held in these fields:

| Result | Field | Holds |
|---|---|---|
| `ExpandResult` | `excluded_keys` | `(type, name, predicate)` keys |
| `LookupResult` | `excluded_node_ids` | ids of graph-index nodes |
| `LookupResult` | `implicit_excluded_keys` | `(type, name, predicate)` keys that have no node |

{py:meth}`Store.excluded_keys(result) <zanzibar.Store.excluded_keys>` returns a
`LookupResult`'s exclusions as keys, both fields together.

For one public grant, `lookup_reverse` and `expand` report it in the two shapes:

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user, user:*]
"""

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    store = Store(session, "markers", schema=SCHEMA)
    store.add_tuple("user:*", "viewer", "doc:1")
    print(sorted(store.lookup_reverse("viewer", "doc:1").markers))  # -> [('user', '...', 'any')]
    print(sorted(store.expand("viewer", "doc:1").markers))  # -> [('user', '...')]
```

### Testing whether a subject is covered

A result means "the listed keys, plus every subject of a marker's shape, minus the excluded
keys". A subject that a marker already covers may also appear as a key, so do not compare
two results by equality of their key sets; compare them by what they cover.

An `ExpandResult` does this for you: `key in result` and
{py:meth}`ExpandResult.covers <zanzibar.ExpandResult.covers>`. A `LookupResult` has no
`covers()` method or `in` test of its own, because it holds internal ids that only the
store can translate. For a `lookup_reverse` result, a helper in this shape answers the same
question, and the first two fields of each triple compare a lookup's markers with an
`expand`'s:

```python
BANNED_SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define viewer: [user, user:*] but not banned
"""

def covers(store, result, key):
    """Is the (type, name, predicate) subject in this lookup_reverse result?"""
    t, _name, p = key
    starred = (t, p, "any") in result.markers
    return key in store.result_keys(result) or (
        starred and key not in store.excluded_keys(result))

with Session(engine) as session:
    store = Store(session, "covers", schema=BANNED_SCHEMA)
    store.add_tuple("user:*", "viewer", "doc:2")
    store.add_tuple("user:mallory", "banned", "doc:2")
    public = store.lookup_reverse("viewer", "doc:2")
    print(covers(store, public, ("user", "zed", "...")))  # -> True
    print(covers(store, public, ("user", "mallory", "...")))  # -> False

    exp = store.expand("viewer", "doc:2")
    print(("user", "mallory", "...") in exp)  # -> False
    lookup_shapes = {(t, p) for t, p, _variant in public.markers}
    print(lookup_shapes == set(exp.markers))  # -> True
```

How to read markers in practice is covered in
[Find who can access what](../../how-to/query-access.md#read-wildcard-grants).

```{toctree}
:maxdepth: 1
:hidden:

store
schema
setengine
graphindex
```
