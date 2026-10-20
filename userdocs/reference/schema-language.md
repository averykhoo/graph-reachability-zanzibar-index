# Schema language

A schema declares the object types of your application and, for each type, its
relations and how they are computed. The language is a subset of the
[OpenFGA modelling language](https://openfga.dev/docs/configuration-language), schema
version 1.1, including the `and` and `but not` operators, plus a few extensions listed
[below](#extensions-beyond-openfga).

A schema is passed as text to {py:class}`zanzibar.Store` (`schema=`) or to
{py:func}`zanzibar.parse_openfga_schema`. An OpenFGA JSON model is also accepted; see
[JSON models](#json-models). Text the parser refuses raises
{py:exc}`zanzibar.SchemaError`, a `ValueError`. Every refused shape, with the reason and
the rewrite, is listed in [Refused schema shapes](refused-shapes.md).

## Example

```python
from zanzibar import parse_openfga_schema

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
    define owner: [user]
    define editor: [user] or owner
    define banned: [user]
    define viewer: ([user, user:*] or editor or viewer from parent) but not banned
"""

rules = parse_openfga_schema(SCHEMA)
print(type(rules).__name__)  # -> 'RuleSet'
```

## Lines

A schema is read one line at a time. Leading and trailing whitespace is removed from each
line, so indentation carries no meaning (spaces and tabs both work); the indentation
used on this page is the OpenFGA convention.

| Line | Meaning |
|---|---|
| empty | ignored |
| `# text` | a comment; the line must start with `#` |
| `model` | header, optional; must stand alone |
| `schema 1.1` | header, optional; `1.1` is the only accepted version |
| `type NAME` | starts the block of type `NAME` |
| `relations` | optional; must stand alone |
| `define NAME: EXPRESSION` | declares relation `NAME` on the current type |

Anything else is refused. In particular:

- **No trailing comments.** `define viewer: [user]  # people` is refused. Put the comment
  on its own line.
- **Header lines stand alone.** `relations define viewer: [user]`, `model x` and
  `schema 1.1 # comment` are refused.
- **Only schema 1.1.** `schema 1.2`, any other version, and a bare `schema` line are
  refused. OpenFGA also accepts `1.2`; this library does not.
- **No modules, `extend type` or `condition` blocks.** Lines starting with `module`,
  `extend` or `condition` are refused.

The header may appear anywhere, or not at all. A `define` line belongs to the most recent
`type` line above it; a `define` before any `type` line is refused.

## Types

`type NAME` declares an object type. Rules:

- `NAME` follows the [identifier rules](tuple-strings.md#identifiers): characters from
  `A-Z a-z 0-9 _ . / @ + = -`, 1 to 256 of them. A type name may contain `.`.
- `type` takes exactly one name; `type user extra` is refused.
- Each type is declared once. A second `type doc` block is refused, rather than merged.
- A type may have no relations (`type user`). It can still be named in a restriction.
- The schema must declare at least one type, and at least one relation on some type. An
  empty schema, a schema of comments, and a schema of relation-less types are refused.

Types may appear in any order: a restriction may name a type declared further down.

## Relations

`define NAME: EXPRESSION` declares relation `NAME` on the current type. Whitespace around
the name and the colon is free (`define viewer:[user]` and `define  viewer : [user]` both
parse). Rules:

- `NAME` follows the [identifier rules](tuple-strings.md#identifiers), except that it may
  **not** contain `.`, which is reserved for relations the compiler generates. Use `_`
  (`can_view`, not `can.view`).
- The name may not be empty (`define : [user]` is refused).
- Each relation is declared once per type. A second `define viewer` on the same type is
  refused; join the alternatives with `or` in one definition.
- The words `or`, `and`, `but`, `not` and `from` are keywords of the expression syntax. A
  relation with one of these names can be declared, but no expression can refer to it.

## Expressions

An expression is built from four kinds of operand and three operators.

### Operands

`[RESTRICTION, ...]`
: **Direct relationship.** The relation holds for a subject when a tuple stores it. The
  brackets list which subjects a tuple may store; see [Type restrictions](#type-restrictions).

`REL`
: **Computed relation.** The relation holds wherever relation `REL` of the same object
  holds. `define editor: [user] or owner` makes every owner an editor. `REL` must be
  declared on the same type.

`REL from TUPLESET`
: **Relation through a link** (OpenFGA's *tuple to userset*). For each object stored
  under `TUPLESET` on this object, the relation holds wherever `REL` holds on that linked
  object. `define viewer: viewer from parent` gives a doc the viewers of its parent
  folder. See [Tuplesets](#tuplesets-from).

`( EXPRESSION )`
: **Grouping.** Parentheses may nest to any depth.

### Operators

`A or B or ...`
: **Union.** The relation holds when any operand holds.

`A and B and ...`
: **Intersection.** The relation holds when every operand holds.

`A but not B`
: **Exclusion.** The relation holds when `A` holds and `B` does not.

### Precedence and grouping

The operators have **no relative precedence**. Where a reading would depend on one, the
parser refuses the expression and asks for parentheses:

- One chain uses one operator. `a or b or c` and `a and b and c` parse; `a or b and c` is
  refused. Write `(a or b) and c` or `a or (b and c)`.
- `but not` takes exactly two operands and shares its level with no other operator.
  `a but not b` parses; `a or b but not c`, `a but not b or c`, `a and b but not c` and
  `a but not b but not c` are refused. Write `(a or b) but not c`, `a but not (b or c)`
  or `(a but not b) or c`, whichever you mean. Version 0.0.4 and earlier accepted these
  and read `but not` as binding loosest on both sides; since 0.0.5 they raise
  {py:exc}`zanzibar.ShapeNoLongerAccepted`, a `SchemaError` that carries the rewrite
  keeping the old meaning in its `instead` attribute.
- Each operand of `but not` is a single operand: a restriction list, a relation, a
  `from`, or a parenthesised expression.

A nested exclusion is fine when parenthesised: `a but not (b but not c)`.

### Grammar

```text
definition := "define" NAME ":" expr
expr       := unit "but not" unit
            | unit ( "or" unit )*
            | unit ( "and" unit )*
unit       := "(" expr ")" | leaf
leaf       := "[" restriction ( "," restriction )* "]"
            | REL
            | REL "from" REL
restriction:= TYPE | TYPE ":*" | TYPE "#" REL | TYPE ":*#" REL
```

Tokens are separated by whitespace or by brackets and parentheses. A `[...]` list is one
token. Spaces around its entries, commas and `#` are free (`[ user , group # member ]`),
but `:*` must be written without spaces: `[user: *]` is refused.

The restriction `T#...` is accepted and means the same as `T`: `...` is the bare-subject
predicate (see [Tuple strings](tuple-strings.md#identifiers)).

## Type restrictions

A restriction list names the subjects a tuple on this relation may store. A write whose
subject matches no entry is refused with {py:exc}`zanzibar.AdmissionRejected`.

| Entry | Admits | In OpenFGA |
|---|---|---|
| `user` | a single subject of type `user`, written `"user:alice"` | yes |
| `user:*` | the wildcard subject `"user:*"`: every `user` | yes |
| `group#member` | a userset, written `"group:eng#member"`: every member of that group | yes |
| `group:*#member` | the members of every `group` | no: an [extension](#extensions-beyond-openfga) |

Rules:

- The list may not be empty (`[]`), and no entry may be empty (`[user,]`).
- Every type named must be declared by a `type` line. With no `type usr`, a bare or
  wildcard restriction (`[usr]`, `[usr:*]`) raises
  {py:exc}`zanzibar.ShapeNoLongerAccepted`, and a userset restriction (`[usr#member]`)
  raises a plain `SchemaError`, because its relation is undeclared too.
- In `T#r` and `T:*#r`, relation `r` must be declared on type `T`.
- An entry may not contain more than one `#`.
- **No conditions.** `[user with in_office]` is refused; neither backend evaluates
  OpenFGA conditions. Where the condition is a stored fact, model it as a relation, for
  example `define viewer: [user] but not suspended`.

A definition may hold several restriction lists, anywhere in the expression:
`[user] or [group#member]`, `editor or [user]` and `viewer but not [user:*]` all parse.

## Tuplesets (`from`)

In `REL from TUPLESET`:

- `TUPLESET` must be declared on the same type.
- `TUPLESET` must be a **direct** relation: one restriction list (`[folder]`,
  `[folder, doc]`), or a union of restriction lists (`[folder] or [doc]`). A tupleset with
  a computed, `from`, `and` or `but not` arm is refused, because `from` follows the tuples
  stored on the tupleset, never its computed members.
- `TUPLESET` may not restrict to a userset. `parent: [folder#member]` under
  `viewer from parent` is refused; `from` would ignore the `#member`. Use `[folder]` for
  the link.
- `REL` must be declared on at least one of the types `TUPLESET` admits.

## Consistency rules

A schema must be self-consistent. The first three rules below are checked when the
schema is parsed and the last when it is compiled; either way, before any tuple is
written.

- **Every reference is declared**: a computed `REL`, a tupleset, a `from` target, and the
  relation in a `T#r` restriction.
- **No reference cycles.** Relations may not depend on themselves through computed
  relations and tuplesets alone: `define a: [user] or b` with `define b: a` is refused.
  Recursion through **stored tuples** is allowed and is how hierarchies are modelled:
  `define member: [user, group#member]` (nested groups) and
  `define viewer: [user] or viewer from parent` (folder inheritance).
- **No recursion through `but not`.** A relation may not depend on itself through the
  right-hand side of a `but not`, at any distance. Put the recursion in the relation being
  subtracted instead:
  `define blocked: [user] or blocked from parent` then
  `define viewer: [user] but not blocked`.
- **No recursion through `and` or `but not` at all**, when the schema is compiled (by a
  {py:class}`zanzibar.Store` or by {py:func}`zanzibar.parse_openfga_schema`). A relation
  that reaches itself through a relation using one
  of these operators, such as
  `define viewer: ([user] or viewer from parent) but not blocked`, parses but is refused
  when compiled, with {py:exc}`zanzibar.CyclicDerivedDependency` (a `ValueError`, not a
  `SchemaError`). The usual rewrite recurses on a plain relation and applies the operator
  on top: `define viewer_base: [user] or viewer_base from parent` then
  `define viewer: viewer_base but not blocked`. This is not the same schema: `blocked`
  then applies only at the object queried, not at every folder above it.

```python
from zanzibar import CyclicDerivedDependency, SchemaError

def refusal(text):
    try:
        parse_openfga_schema(text)
    except (SchemaError, CyclicDerivedDependency) as err:
        return type(err).__name__
    return "accepted"

print(refusal("type user\ntype doc\n  relations\n    define viewer: [usr]"))  # -> 'ShapeNoLongerAccepted'
print(refusal("type user\ntype doc\n  relations\n    define viewer: [user] or editor"))  # -> 'SchemaError'
print(refusal("type user\ntype doc\n  relations\n    define a: [user]\n    define b: [user]\n    define c: [user]\n    define viewer: a or b and c"))  # -> 'SchemaError'
print(refusal("type user\ntype doc\n  relations\n    define a: [user]\n    define b: [user]\n    define c: [user]\n    define viewer: (a or b) and c"))  # -> 'accepted'
print(refusal("type user\ntype folder\n  relations\n    define parent: [folder]\n    define blocked: [user]\n    define viewer: ([user] or viewer from parent) but not blocked"))  # -> 'CyclicDerivedDependency'
```

## Wildcards

`[user:*]` lets a single tuple grant a relation to every user: the tuple's user is
written `"user:*"`. It is part of OpenFGA. A `but not` still excludes individuals:
with `define viewer: [user, user:*] but not banned`, a banned user is refused even when
`user:*` is a viewer.

Three further wildcard forms go beyond OpenFGA. They work on both backends, but each
emits {py:class}`zanzibar.UnprovenExtensionWarning` when the schema is compiled, because
they are outside the part of the language whose backend equivalence is formally checked.
See [Wildcard extensions](../explanation/wildcard-extensions.md).

| Form | Written as |
|---|---|
| Wildcard userset | `[group:*#member]`: the members of every group |
| Wildcard tupleset | `define parent: [folder:*]` used by a `from` |
| Object wildcard | a tuple on `doc:*`: the relation on every `doc` |

Object wildcards have **no schema syntax**. Enable each one by passing its
`(object_type, relation)` pair in `object_wildcard_shapes`, to {py:class}`zanzibar.Store`
or to {py:func}`zanzibar.parse_openfga_schema`. A pair that names an undeclared type or
relation is refused with {py:exc}`zanzibar.ShapeNoLongerAccepted`.

```python
import warnings

from sqlmodel import Session, SQLModel, create_engine
from zanzibar import Store, UnprovenExtensionWarning

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)

with Session(engine) as session, warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    store = Store(session, "wildcards", schema="""
type user
type doc
  relations
    define viewer: [user]
""", object_wildcard_shapes=frozenset({("doc", "viewer")}))
    store.add_tuple("user:alice", "viewer", "doc:*")
    print(store.check("user:alice", "viewer", "doc:any-doc"))  # -> True
    print(any(w.category is UnprovenExtensionWarning for w in caught))  # -> True
```

## Extensions beyond OpenFGA

Accepted here, and not by OpenFGA's own tools, so a schema using them may not load
there:

- more than one restriction list in a definition: `[user] or [group#member]`;
- a restriction list that is not the first operand: `editor or [user]`,
  `viewer but not [user:*]`;
- no `model` / `schema 1.1` header;
- a `define` with no `relations` line above it;
- a tupleset written as a union of restriction lists: `[folder] or [doc]`;
- the three wildcard forms in [Wildcards](#wildcards), which also emit a warning.

## JSON models

{py:class}`zanzibar.Store` also accepts an OpenFGA JSON authorization model as `schema=`:
a `dict`, a JSON string, or either one wrapped as `{"authorization_model": {...}}` (the
shape an OpenFGA server returns). The model is converted to the DSL and stored as DSL,
so reopening the store with the same JSON is accepted.

The JSON front end reads `schema_version` `"1.1"` and the rewrite nodes `this` (with
`directly_related_user_types` metadata), `computedUserset`, `tupleToUserset`, `union`,
`intersection` and `difference`. Conditions, other schema versions and unknown rewrite
operators are refused, as are duplicate keys in JSON text. A model must pass every rule on
this page once converted.

Two functions expose the front end directly:
{py:func}`zanzibar.schema.openfga_json_to_dsl` returns the DSL text, and
{py:func}`zanzibar.schema.parse_openfga_json` returns the parsed schema.

```python
from zanzibar.schema import openfga_json_to_dsl

model = {
    "schema_version": "1.1",
    "type_definitions": [
        {"type": "user"},
        {"type": "doc",
         "relations": {"viewer": {"this": {}}},
         "metadata": {"relations": {"viewer": {
             "directly_related_user_types": [{"type": "user"}]}}}},
    ],
}
dsl = openfga_json_to_dsl(model)
print("define viewer: [user]" in dsl)  # -> True
```

## Python entry points

| Function | Returns |
|---|---|
| {py:func}`zanzibar.parse_openfga_schema` | the compiled rule set; takes `object_wildcard_shapes` |
| {py:func}`zanzibar.schema.parse_schema_ast` | the parsed schema, a dict from `(type, relation)` to an expression tree |
| {py:func}`zanzibar.schema.unparse_schema_ast` | DSL text for a parsed schema |
| {py:func}`zanzibar.schema.parse_openfga_json` | the parsed schema of a JSON model |
| {py:func}`zanzibar.schema.openfga_json_to_dsl` | DSL text for a JSON model |

{py:func}`zanzibar.schema.parse_schema_ast` applies every rule on this page except the
compile-time ones: the `and` / `but not` recursion refusal and the `object_wildcard_shapes`
check happen in {py:func}`zanzibar.parse_openfga_schema` and {py:class}`zanzibar.Store`.

```python
from zanzibar.schema import parse_schema_ast, unparse_schema_ast

tree = parse_schema_ast("type user\ntype doc\n  relations\n    define viewer: [user] or editor\n    define editor: [user]")
print(sorted(tree))  # -> [('doc', 'editor'), ('doc', 'viewer')]
print(unparse_schema_ast(tree).splitlines()[0])  # -> 'type user'
```
