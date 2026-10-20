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
backends. `parse_openfga_schema` and the exceptions and warning that
[zanzibar.schema](schema.md) re-exports (listed at the foot of its page, from
`ZanzibarError` to `UnprovenExtensionWarning`) never import it.

| Name | Kind | Documented at |
|---|---|---|
| `Store` | class | {py:class}`zanzibar.Store` (on the [zanzibar.store](store.md) page) |
| `ExpandResult` | class | {py:class}`zanzibar.ExpandResult` (on the [zanzibar.store](store.md) page) |
| `LookupResult` | class | {py:class}`zanzibar.LookupResult` (on the [zanzibar.graphindex](graphindex.md) page) |
| `parse_openfga_schema` | function | {py:func}`zanzibar.parse_openfga_schema` (on the [zanzibar.schema](schema.md) page) |
| `__version__` | string | {py:data}`zanzibar.__version__`, below |
| every exception, and `UnprovenExtensionWarning` | exception classes | the [Exceptions](../exceptions.md) page |

The same classes are also importable from their subpackage (`from zanzibar.store import
Store` and `from zanzibar import Store` give the same object). Each is documented once,
under its top-level name.

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

   The installed version of the library as a string, for example ``"0.0.5"``.
```

## Subpackages

| Subpackage | Contents |
|---|---|
| [zanzibar.store](store.md) | The composed store: the tuple log, the schema record, `Store`, and the offline build functions. Start here. |
| [zanzibar.schema](schema.md) | Parsing, converting and compiling schemas; the schema AST; identifier helpers. |
| [zanzibar.setengine](setengine.md) | The set engine: stores raw tuples and computes answers on each read. |
| [zanzibar.graphindex](graphindex.md) | The graph index: a precomputed closure, so a check is a few indexed lookups. |

Each subpackage re-exports some of the exceptions its code raises; the foot of each page
lists which. Not every exception a subpackage raises is re-exported there (for example,
`zanzibar.setengine` raises {py:exc}`~zanzibar.AdmissionRejected` but does not export it).
Every exception is importable from `zanzibar`, which is the one place to import from when
you catch one. The re-exports are the same classes as the top-level names, and they are
documented on the [Exceptions](../exceptions.md) page.

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
  `("user", "...", "any")` means every user (a `user:*` tuple).
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

How to read markers together with their exclusions, and how to compare the two shapes, is
covered in [Find who can access what](../../how-to/query-access.md#read-wildcard-grants).

```{toctree}
:maxdepth: 1
:hidden:

store
schema
setengine
graphindex
```
