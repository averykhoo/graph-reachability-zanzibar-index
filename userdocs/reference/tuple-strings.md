# Tuple strings and identifiers

A relationship tuple says that a **user** (a subject) has a **relation** to an
**object**: `user:alice` is a `viewer` of `doc:1`. The methods of
{py:class}`zanzibar.Store` that take a tuple accept it in two forms: OpenFGA's three
strings, or six separate parts.

## The two call forms

| Method | String form | Parts form |
|---|---|---|
| `add_tuple`, `remove_tuple`, `check` | `user, relation, object` | `subject_predicate, subject_type, subject_name, relation, object_type, object_name` |
| `lookup` | `user` | `subject_predicate, subject_type, subject_name` |
| `lookup_reverse`, `expand` | `relation, object` | `relation, object_type, object_name` |

{py:class}`zanzibar.store.TupleSource` takes the same two forms in `add`, `remove` and
`check`.

Arguments may be passed positionally or by those keyword names. The form is chosen like
this:

1. A keyword that belongs to only one of the method's two forms decides the form:
   - tuple methods: `user` or `object` picks the string form; `subject_predicate`,
     `subject_type`, `subject_name`, `object_type` or `object_name` picks the parts form;
   - `lookup`: `user`, or `subject_predicate` / `subject_type` / `subject_name`;
   - `lookup_reverse` and `expand`: `object`, or `object_type` / `object_name`.
2. Otherwise the number of arguments decides: three or six for a tuple, one or three for
   `lookup`, two or three for `lookup_reverse` and `expand`.

Any other count, or a mix the chosen form cannot bind, raises `TypeError`. Keyword-only
options, such as `at_least=` and the result filters of `lookup` and `lookup_reverse`
(see [Find who can access what](../how-to/query-access.md)), are not part of either form and
do not count.

```python
from sqlmodel import Session, SQLModel, create_engine
from zanzibar import Store

SCHEMA = """
type user
type group
  relations
    define member: [user]
type doc
  relations
    define viewer: [user, user:*, group#member]
"""

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
session = Session(engine)
store = Store(session, "tuple-strings", schema=SCHEMA)

# the string form
store.add_tuple("user:alice", "member", "group:eng")
store.add_tuple("group:eng#member", "viewer", "doc:1")
store.add_tuple(user="user:*", relation="viewer", object="doc:public")

# the parts form: "..." is the bare subject
store.add_tuple("...", "user", "bob", "viewer", "doc", "2")

print(store.check("user:alice", "viewer", "doc:1"))  # -> True
print(store.check("...", "user", "bob", "viewer", "doc", "2"))  # -> True
allowed = store.check(subject_predicate="...", subject_type="user", subject_name="carol",
                      relation="viewer", object_type="doc", object_name="public")
print(allowed)  # -> True
```

## User strings

| String | Parts `(subject_predicate, subject_type, subject_name)` | Means |
|---|---|---|
| `"user:alice"` | `("...", "user", "alice")` | one subject |
| `"group:eng#member"` | `("member", "group", "eng")` | a userset: every member of `group:eng` |
| `"user:*"` | `("...", "user", "*")` | every `user` (needs `user:*` in the restriction) |
| `"group:*#member"` | `("member", "group", "*")` | the members of every `group` (needs `group:*#member`, an extension) |

The predicate `"..."` means "the subject itself, not a relation of it". In the string
form it is written by leaving `#relation` off; `"user:alice#..."` is refused.

## Object strings

An object string is `"type:name"`. It never has a `#relation`: pass the relation as its
own argument. `"doc:*"` is the object wildcard, every `doc`, and is accepted on a write
only for a relation enabled with `object_wildcard_shapes` (see
[Wildcards](schema-language.md#wildcards)).

## Splitting rules

A user string is a type and a name joined by exactly one `:`, followed by at most one
`#relation`. The string is split at its `#` first, and the part before it must then hold
exactly one `:`. An object string is the same without the `#relation`. A string that does
not split this way raises {py:exc}`zanzibar.MalformedTupleString`, which is a `ValueError`.
Its message names the expected form.

The relation after `#` is not checked for `:` when the string is split, so
`"user:a#b:c"` splits into type `user`, name `a` and relation `b:c`. A write of it is
refused when its identifiers are checked (see [Identifiers](#identifiers)), with
{py:exc}`zanzibar.AdmissionRejected`; a read such as `check` answers `False`.

| Input | Raises |
|---|---|
| `"alice"` (no `:`) | `MalformedTupleString` |
| `"user:"`, `":alice"` (an empty part) | `MalformedTupleString` |
| `"user:a:b"` (a second `:`) | `MalformedTupleString` |
| `"user:alice#"` (an empty relation) | `MalformedTupleString` |
| `"group:eng#a#b"` (a second `#`) | `MalformedTupleString` |
| `"user:alice#..."` | `MalformedTupleString`: write `"user:alice"` |
| object `"doc:1#viewer"` | `MalformedTupleString`: an object has no `#relation` |
| a non-`str` user or object, such as `5` | `TypeError` |

Splitting only checks the shape. Whether the parts are valid identifiers, and whether
the schema admits the tuple, is checked afterwards; see the next section. So a relation
part with a character outside the allowed set, such as `"group:eng#b:c"`, is not
malformed: a read with it answers `False`, and a write is refused with
{py:exc}`zanzibar.AdmissionRejected`.

```python
from zanzibar import MalformedTupleString

for bad in ["alice", "user:a:b", "user:alice#...", "group:eng#a#b"]:
    try:
        store.check(bad, "viewer", "doc:1")
    except MalformedTupleString as err:
        print(isinstance(err, ValueError))  # -> True
```

## Identifiers

Every type, name and relation in a tuple, and every type and relation declared in a
schema, is an identifier:

- 1 to 256 characters,
- each from `A-Z`, `a-z`, `0-9` and `_ . / @ + = -`.

No other character is allowed, so no spaces, no `:` or `#`, and nothing outside ASCII.
The set is available as {py:data}`zanzibar.schema.IDENTIFIER_CHARSET`, in regular
expression character-class form, and {py:func}`zanzibar.schema.is_valid_identifier` tests
a string against it.

Two values are reserved and are valid only in one position each:

| Value | Allowed as | Means |
|---|---|---|
| `"*"` | a subject or object **name** | every subject or object of that type |
| `"..."` | a **subject predicate** | the bare subject |

`is_valid_identifier` does not apply these position rules. It returns `False` for `"*"`,
and `True` for `"..."`, which is a run of `.` characters; the write validator is what
allows each value only in its own position.

Pass `"..."` as a string. The Python `Ellipsis` (`...`) is refused: on a write with
{py:exc}`zanzibar.AdmissionRejected`, on a read with `TypeError`.

```python
from zanzibar.schema import IDENTIFIER_CHARSET, is_valid_identifier

print(IDENTIFIER_CHARSET)  # -> 'A-Za-z0-9_./@+=-'
print(is_valid_identifier("team/eng@example.com"))  # -> True
print(is_valid_identifier("a b"))  # -> False
print(is_valid_identifier("*"))  # -> False
print(is_valid_identifier("..."))  # -> True
```

### In a schema

Declared names follow the same rules, with one more: a **relation** name may not contain
`.`, which is reserved for relations the compiler generates. A type name may contain `.`.
See [Schema language](schema-language.md#relations).

### Writes are strict, reads are lenient

- A **write** (`add_tuple`, `remove_tuple`) with an invalid identifier, or one naming an
  undeclared type or relation, raises {py:exc}`zanzibar.AdmissionRejected`, a
  `ValueError`. So does a subject the relation's type restrictions do not admit, and
  removing a tuple that is not stored. On a write the subject predicate must be a string;
  `None` is refused.
- A **read** (`check`, `lookup`, `lookup_reverse`, `expand`) does not validate
  identifiers. A name that cannot exist, or an undeclared type or relation, matches
  nothing: `check` returns `False` with no error, so a typo in a relation name reads as
  "denied". On a read, `None` as the subject predicate means the bare subject, like
  `"..."`.

```python
from zanzibar import AdmissionRejected

try:
    store.add_tuple("user:al ice", "viewer", "doc:1")
except AdmissionRejected as err:
    print(isinstance(err, ValueError))  # -> True

print(store.check("user:al ice", "viewer", "doc:1"))  # -> False
try:
    store.add_tuple("group:eng#member:x", "viewer", "doc:1")  # ':' in the relation part
    refused = False
except AdmissionRejected:
    refused = True
print(refused)  # -> True
print(store.check("group:eng#member:x", "viewer", "doc:1"))  # -> False
print(store.check("user:alice", "veiwer", "doc:1"))  # -> False
print(store.check(None, "user", "alice", "viewer", "doc", "1"))  # -> True
session.close()
```

A common slip is passing an OpenFGA string to a parts-form call, such as
`add_tuple("...", "user:alice", "x", ...)`. The refusal's message says so and shows the
string form.

### Store ids

A store id is not an identifier. It may be any `str` with at least one non-whitespace
character (`"tenant:acme"`, a UUID); the character set does not apply.
{py:func}`zanzibar.schema.validate_store_id` applies the rule, and a store id that breaks
it raises {py:exc}`zanzibar.AdmissionRejected`.
