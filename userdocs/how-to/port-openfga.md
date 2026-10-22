# Port an OpenFGA model

This guide takes an existing OpenFGA authorization model and its tuples and loads them
into a {py:class}`zanzibar.Store`. Most schema 1.1 models load unchanged. The ones that
do not are refused when the schema is parsed, with a message that says what to change.

For how the answers can differ from an OpenFGA server once a model loads, see
[semantics and differences from OpenFGA](../explanation/semantics-vs-openfga.md).

## 1. Load the model

Pass the model as DSL text, or as the JSON authorization model (a `dict` or a JSON
string, bare or wrapped as `{"authorization_model": {...}}`, the form an OpenFGA server
returns):

```python
from sqlmodel import SQLModel, Session, create_engine
from zanzibar import Store

MODEL = {
    "schema_version": "1.1",
    "type_definitions": [
        {"type": "user"},
        {
            "type": "doc",
            "relations": {"viewer": {"this": {}}},
            "metadata": {"relations": {"viewer": {"directly_related_user_types": [
                {"type": "user"}, {"type": "user", "wildcard": {}}]}}},
        },
    ],
}

engine = create_engine("sqlite:///perms.db")
SQLModel.metadata.create_all(engine)
store = Store(Session(engine), "my-app", schema={"authorization_model": MODEL})
```

A JSON model is converted to DSL and stored as DSL. To see the DSL it becomes, use
{py:func}`zanzibar.schema.openfga_json_to_dsl`:

```python
from zanzibar.schema import openfga_json_to_dsl

print("define viewer: [user, user:*]" in openfga_json_to_dsl(MODEL))  # -> True
```

Reopening the store with the same JSON is accepted. A store's schema is saved once and
never changes; to load a different model, see [Change a schema](change-schema.md).

## 2. Fix what is refused

If the model is refused, the error is a {py:exc}`zanzibar.ZanzibarError` (for an
OpenFGA model, a {py:exc}`zanzibar.SchemaError` or
{py:exc}`zanzibar.CyclicDerivedDependency`, both also `ValueError`) whose message names
the relation at fault. [Rewrite a refused schema
shape](rewrite-refused-shape.md) works through each fix. Check your model against this
list (a *tupleset* is the relation after `from`, such as `parent` in `viewer from parent`):

| in your OpenFGA model | here | what to do |
| --- | --- | --- |
| conditions: `[user with in_office]`, `condition` blocks, JSON `conditions` | refused | no direct equivalent. If the condition stands for a stored fact, make it a relation (`define viewer: [user] but not suspended`) |
| modules: `module`, `extend type`, `schema 1.2` | refused | merge the files into one schema 1.1 text, each type's relations in one `type` block |
| a `from` tupleset with anything but type restrictions | refused, as in OpenFGA | store the links on `define parent: [folder]` and use `from parent` |
| a `from` tupleset restricted to a userset, `[folder#member]` | refused, as in OpenFGA | `[folder]`, plus `define parent_member: member from parent` if the userset was meant |
| a reference to an undeclared type or relation, or a loop of references | refused, as in OpenFGA | declare it or fix the spelling; delete one direction of a loop |
| `a or b but not c` with no parentheses | refused, as in OpenFGA's grammar | `(a or b) but not c` |
| a relation that recurses through `and` or `but not`, such as `define member: [user, group#member] but not banned` | refused | recurse on a plain relation and apply the operator on top; this changes the meaning, see the rewrite guide |
| a declared name with characters outside `[A-Za-z0-9_./@+=-]`, or a `.` in a relation name | refused | rename it, for example `can_view` |

Everything else in schema 1.1 carries over: direct restrictions, usersets
(`[group#member]`), public access (`[user:*]`), computed relations (`or editor`),
`from`, `or`, `and` and `but not`. The `model` / `schema 1.1` header is optional here.

Some DSL that loads here is not valid OpenFGA DSL, such as several `[...]` blocks in
one definition. That only matters if the schema must also load in OpenFGA's tools; see
[the schema language reference](../reference/schema-language.md).

## 3. Copy the tuples

OpenFGA tuples have the same `user`, `relation`, `object` strings that
{py:meth}`zanzibar.Store.add_tuple` takes, so a read from OpenFGA can be written back
one tuple at a time. Write them through the `Store` and collect the ones it refuses:

```python
from zanzibar import AdmissionRejected, MalformedTupleString

openfga_tuples = [
    {"user": "user:alice", "relation": "viewer", "object": "doc:1"},
    {"user": "user:*", "relation": "viewer", "object": "doc:press"},
    {"user": "user:google-oauth2|1234", "relation": "viewer", "object": "doc:1"},
    {"user": "user:bob", "relation": "viewer", "object": "doc:2",
     "condition": {"name": "in_office"}},
]

refused = []
for t in openfga_tuples:
    if "condition" in t:
        refused.append((t, "conditional tuple"))
        continue
    try:
        store.add_tuple(t["user"], t["relation"], t["object"])
    except (AdmissionRejected, MalformedTupleString) as exc:
        refused.append((t, str(exc)))

print(len(refused))  # -> 2
print(store.check("user:alice", "viewer", "doc:1"))  # -> True
print(store.check("user:carol", "viewer", "doc:press"))  # -> True
```

Each `add_tuple` commits on its own. For a large import, see [bulk-load or adopt an
existing store](bulk-load-adopt.md).

Three kinds of tuple OpenFGA accepts do not load here:

- **Identifiers outside the character set** are refused. Type, name and relation strings must match
  `[A-Za-z0-9_./@+=-]`, 1 to 256 characters. OpenFGA allows more, so ids such as
  `google-oauth2|1234` need mapping to an allowed form (replace the `|`, or use your own
  user ids) before import, and the same mapping at every later call.
- **Conditional tuples** cannot be expressed here: {py:meth}`zanzibar.Store.add_tuple`
  has no condition argument, so the library never sees a condition and cannot refuse
  one. Your import code must leave such tuples out (the loop above does), or turn the
  condition into tuples of its own as described above. Writing one without its
  condition would grant unconditionally.
- **Cycles in the data** are refused. A tuple that would put a group inside itself, directly or
  through other groups, or make a folder its own ancestor, is refused with
  {py:exc}`zanzibar.AdmissionRejected`. OpenFGA accepts these, so check imported data
  for cycles and decide which link to drop.

```python
print(refused[0][1].startswith("invalid subject_name 'google-oauth2|1234'"))  # -> True
```

## 4. Compare answers

Before switching traffic, ask both systems the same questions. A few answers can differ
by design even for a model that loads: for example, a check whose user is a userset
such as `team:1#viewer`, where `team` declares no `viewer`, is answered here and
rejected as an error by OpenFGA. The cases are listed in
[semantics and differences from OpenFGA](../explanation/semantics-vs-openfga.md).
