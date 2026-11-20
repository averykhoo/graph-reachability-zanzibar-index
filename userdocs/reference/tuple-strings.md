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
form it is written by leaving `#relation` off; `"user:alice#..."` is refused. What `None`
means in the predicate's place depends on the call; see
[`None` as the subject predicate](#none-as-the-subject-predicate).

### Result keys are in a different order

{py:meth}`Store.result_keys <zanzibar.Store.result_keys>`,
{py:meth}`Store.excluded_keys <zanzibar.Store.excluded_keys>` and
{py:meth}`Store.expand <zanzibar.Store.expand>` give each subject or object as a key
`(type, name, predicate)`, such as `("user", "alice", "...")`. The parts form takes the
same three values in another order, `(subject_predicate, subject_type, subject_name)`. So
a key cannot be passed back with `*key`: `check(*key, "viewer", "doc", "1")` puts `"user"`
in the predicate's place and `"alice"` in the type's. Unpack it by name instead:

```python
key = ("user", "alice", "...")  # a result key: (type, name, predicate)
key_type, key_name, key_predicate = key
print(store.check(key_predicate, key_type, key_name, "viewer", "doc", "1"))  # -> True
```

The misordered call names an undeclared subject type (`alice`), so it is refused rather
than answered, and the message shows the call that was meant; see
[What a read checks](#what-a-read-checks).

```python
from zanzibar import UndeclaredTypeOrRelation

try:
    store.check(*key, "viewer", "doc", "1")
    message = None
except UndeclaredTypeOrRelation as err:
    message = str(err)
print(message)  # -> "check() names an undeclared subject type 'alice': type 'alice' is not declared in the schema. A result key is (type, name, predicate); check takes (subject_predicate, subject_type, subject_name, relation, object_type, object_name): write check('...', 'user', 'alice', 'viewer', 'doc', '1')"
```

## Object strings

An object string is `"type:name"`. It never has a `#relation`: pass the relation as its
own argument. `"doc:*"` is the object wildcard, every `doc`, and is accepted on a write
only for a relation enabled with `object_wildcard_shapes` (see
[Wildcards](schema-language.md#wildcards)).

## Splitting rules

A user string is a type and a name joined by exactly one `:`, followed by at most one
`#relation`. The string is split at its `#` first; the part before it must then hold
exactly one `:`, and the relation after it none. An object string is the same without the `#relation`. A string that does
not split this way raises {py:exc}`zanzibar.MalformedTupleString`, which is a `ValueError`.
Its message names the expected form.

| Input | Raises |
|---|---|
| `"alice"` (no `:`) | `MalformedTupleString` |
| `"user:"`, `":alice"` (an empty part) | `MalformedTupleString` |
| `"user:a:b"` (a second `:`) | `MalformedTupleString` |
| `"user:a#b:c"` (a `:` in the relation) | `MalformedTupleString` |
| `"user:alice#"` (an empty relation) | `MalformedTupleString` |
| `"group:eng#a#b"` (a second `#`) | `MalformedTupleString` |
| `"user:alice#..."` | `MalformedTupleString`: write `"user:alice"` |
| object `"doc:1#viewer"` | `MalformedTupleString`: an object has no `#relation` |
| a non-`str` user or object, such as `5` | `TypeError` |

Splitting only checks the shape. Whether the parts are valid identifiers, and whether
the schema admits the tuple, is checked afterwards; see the next section. So a relation
part with another character outside the allowed set, such as `"group:eng#b c"`, is not
malformed: a write with it is refused with {py:exc}`zanzibar.AdmissionRejected`, and a
read with it is refused with {py:exc}`zanzibar.UndeclaredTypeOrRelation`, because no type
declares a relation `b c`.

```python
from zanzibar import MalformedTupleString

for bad in ["alice", "user:a:b", "user:a#b:c", "user:alice#...", "group:eng#a#b"]:
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

### What a write checks

A **write** (`add_tuple`, `remove_tuple`) with an invalid identifier, or one naming an
undeclared type or relation, raises {py:exc}`zanzibar.AdmissionRejected`, a `ValueError`.
So does a subject the relation's type restrictions do not admit, and removing a tuple that
is not stored. On a write every identifier must be a string: a relation or a part that is
not one, `None` included, is refused with `AdmissionRejected` too, like any other invalid
identifier. A user or object string that is not a `str` is a `TypeError`.

### What a read checks

A **read** (`check`, `lookup`, `lookup_reverse`, `expand`) checks the types and relations
it names, but not the names:

- A **type or relation** the schema does not declare raises
  {py:exc}`zanzibar.UndeclaredTypeOrRelation`, a `ValueError`, before anything is
  answered. That covers the object's type, the relation on it, the subject's type, the
  relation of a userset subject (`group:eng#nosuch`), and the type and relation filters of
  `lookup` and `lookup_reverse`. The message is the one a write with the same mistake
  gets, so a typo in a relation name is reported, not read as "denied".
- A **name** is not checked. An object or subject that no tuple mentions (`doc:999`), a
  wildcard name (`user:*`), or a name a write would refuse (`user:al ice`) matches
  nothing, and `check` answers `False`. Asking about an object that does not exist yet is
  normal.
- A part that is not a string at all (`None`, a number, bytes) is a mistake, not a name,
  and raises `TypeError`, with one exception: `None` as the subject predicate, described
  in the next section.

{py:class}`zanzibar.Store`, {py:class}`zanzibar.store.TupleSource` and
{py:class}`zanzibar.setengine.SetEngine` all refuse the same calls with the same message.

```python
from zanzibar import AdmissionRejected

try:
    store.add_tuple("user:al ice", "viewer", "doc:1")
except AdmissionRejected as err:
    print(isinstance(err, ValueError))  # -> True

print(store.check("user:al ice", "viewer", "doc:1"))  # -> False
print(store.check("user:alice", "viewer", "doc:999"))  # -> False
try:
    store.add_tuple("group:eng#member x", "viewer", "doc:1")  # a space in the relation part
    refused = False
except AdmissionRejected:
    refused = True
print(refused)  # -> True

try:
    store.check("user:alice", "veiwer", "doc:1")
    message = None
except UndeclaredTypeOrRelation as err:
    message = str(err)
    print(isinstance(err, ValueError))  # -> True
print(message)  # -> "check() names an undeclared relation doc#veiwer: type 'doc' declares no relation 'veiwer'; did you mean 'viewer'?"
try:
    store.check("group:eng#member x", "viewer", "doc:1")
    message = None
except UndeclaredTypeOrRelation as err:
    message = str(err)
print(message)  # -> "check() names an undeclared subject relation group#member x: type 'group' declares no relation 'member x'; did you mean 'member'?"
```

### `None` as the subject predicate

`None` in the subject predicate's place means a different thing in each of three places:

| Where | `None` means |
|---|---|
| a read's subject: `check`, `lookup` | the bare subject, the same as `"..."` |
| a write's subject: `add_tuple`, `remove_tuple` | nothing: it is refused with {py:exc}`zanzibar.AdmissionRejected`; write `"..."` |
| the `subject_predicate=` filter of `lookup_reverse` | no filter, the default: bare subjects and usersets both come back; pass `"..."` to keep only bare subjects |

```python
print(store.check(None, "user", "alice", "viewer", "doc", "1"))  # -> True
try:
    store.add_tuple(None, "user", "dave", "viewer", "doc", "1")
    refused = False
except AdmissionRejected:
    refused = True
print(refused)  # -> True
everyone = store.lookup_reverse("viewer", "doc:1", subject_predicate=None)
print(sorted(store.result_keys(everyone)))  # -> [('doc', '1', 'viewer'), ('group', 'eng', 'member'), ('user', 'alice', '...')]
bare = store.lookup_reverse("viewer", "doc:1", subject_predicate="...")
print(sorted(store.result_keys(bare)))  # -> [('user', 'alice', '...')]
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
