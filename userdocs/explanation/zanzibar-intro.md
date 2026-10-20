# Zanzibar and relationship-based access control

This page explains the model of permissions that the library implements, where it comes
from, and how much of it the library takes on. It assumes no prior knowledge of Zanzibar
or OpenFGA.

## Permissions as relationships

Many applications start with access control lists: each document carries a list of who
may read it. Others use roles: alice is an "editor", and editors may edit. Both work until
permissions start to follow the shape of the data. In a file-sharing app, alice can read
a document because she is in a team, the team was given a folder, and the document is in
that folder. Neither a list on the document nor a role on alice says that directly. It is
a chain of relationships, and changing any link in it changes what alice can do.

*Relationship-based access control* (ReBAC) takes that chain as the model. You store the
relationships themselves, and permissions are computed from them by rules:

- alice is a **member** of the team `eng`;
- the members of `eng` are **viewers** of the folder `projects`;
- the folder `projects` is the **parent** of the document `roadmap`;
- and a rule says that a viewer of a document's parent is a viewer of the document.

So alice can view `roadmap`. Nothing about alice, `eng` or `roadmap` had to be written
specially for that answer. Moving `roadmap` to another folder, or removing alice from
`eng`, changes it at once, and the application never maintains a derived list.

## Tuples, usersets and schemas

The stored relationships are called **relationship tuples**, or just tuples. Each one has
three parts, which this library writes the way OpenFGA does:

```text
user               relation   object
user:alice         member     group:eng
group:eng#member   viewer     folder:projects
folder:projects    parent     doc:roadmap
```

An **object** is written `type:name`. The **user** side of a tuple is one of three things:

- a single object, such as `user:alice` (or `folder:projects` in the last row, because a
  folder can be a parent);
- a **userset**, written `type:name#relation`, meaning "everyone who has that relation on
  that object". `group:eng#member` is "the members of `eng`", so the second row grants the
  folder to the whole team at once, including people who join later;
- a **wildcard**, such as `user:*`, meaning every user, for public access.

A tuple only records a fact. The rules that turn facts into permissions live in a
**schema**, which declares the types, the relations each type has, and how relations
imply one another:

```text
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
    define viewer: [user] or viewer from parent
```

The part in brackets says what may be stored directly: a group's `member` may be a user or
the members of another group. After the brackets come *rewrites*, the rules that compute a
relation from others. `viewer from parent` reads "a viewer of whatever this document's
parent is". Rewrites can also refer to another relation on the same object
(`define viewer: [user] or editor`), and can combine relations with `and` and `but not`
(`define viewer: [user] but not blocked`).

With tuples and a schema in place, the library answers four kinds of question:

- **check**: does this user have this relation on this object? ("Can alice view
  `roadmap`?")
- **lookup**: which objects can this user reach? ("What can alice view?")
- **reverse lookup**: who has this relation on this object? ("Who can view `roadmap`?")
- **expand**: the same question as a reverse lookup, answered as a set of users, usersets
  and wildcards.

How to ask each of them is in the [first tutorial](../tutorials/first-check.md) and in
[Find who can access what](../how-to/query-access.md).

## Google's Zanzibar

The model above is not new. Google described it in 2019 in the paper
[*Zanzibar: Google's Consistent, Global Authorization System*](https://www.usenix.org/conference/atc19/presentation/pang)
(USENIX ATC 2019). Zanzibar is the single service that stores the access relationships for
many of Google's products and answers their permission checks. The paper introduced most
of the vocabulary used here: relation tuples, usersets, per-type configurations with
*userset rewrite rules*, and the tuple-to-userset rewrite that `from` expresses.

The paper also deals with two problems that any implementation of the model meets, and
this library meets them too.

**Freshness.** Permissions change, and a check must not miss a change that the user can
see has happened. The paper calls this the "new enemy" problem: someone is removed from a
folder, and new documents are then put in it. A check that still sees the old membership
would show them the new documents. Zanzibar hands out a consistency token, the *zookie*, with each write, and a later
check can demand to be at least that fresh. This library's freshness tokens play the same
role, in a much simpler form: they are positions in one store's append-only log of writes,
not timestamps in a globally replicated database. The
[consistency page](consistency.md) explains what they guarantee.

**Deep nesting.** Groups inside groups inside groups make a check slow, because answering
it means following every chain. The paper describes a separate index, *Leopard*, that
precomputes nested group memberships so those checks become lookups. This library takes
that idea further: its graph index precomputes the result of every rule in the schema, so
every check is a lookup. That has a price, paid on every write, and it is why the library
also keeps a second evaluator that does no precomputation at all.
[The two backends](two-backends.md) explains the trade.

## What this library is, and is not

Zanzibar is a globally distributed service. This library is not: it is a Python package
that keeps its tables in your own SQLite or PostgreSQL database, next to your application's
tables, and you call it in-process. It follows Zanzibar's data model and rewrite semantics,
not its architecture. In particular:

- there is no server, no network API and no replication of its own. Several processes may
  share one store through the database, and the
  [PostgreSQL guide](../how-to/postgresql.md) covers how;
- a store's schema is fixed when the store is created. Changing it means building a new
  store, as [Change a schema](../how-to/change-schema.md) describes;
- freshness tokens order the writes of one store only. There is no global clock and no
  "read as of exactly this moment".

## OpenFGA and the schema language

The paper writes its configurations in a Google-internal format. Several open-source
systems have since implemented Zanzibar's model, and [OpenFGA](https://openfga.dev) is one
of them. Its modelling language is compact and
readable, and it is the language this library reads: the schema above is OpenFGA syntax.
The library also accepts an OpenFGA authorization model in its JSON form.

It reads a subset of that language, with a few extensions. Version 1.1 of the language is
supported, including `and` and `but not`. Conditions (`with`) and modules are not. Some
shapes OpenFGA accepts are refused here, each with an explanation and a rewrite, and a few
shapes are accepted here that OpenFGA does not have. The details are in the
[schema language reference](../reference/schema-language.md),
[Semantics and differences from OpenFGA](semantics-vs-openfga.md) and
[Port an OpenFGA model](../how-to/port-openfga.md).

The library is not affiliated with Google or with OpenFGA, and it does not talk to an
OpenFGA server. Its claim is narrower: a schema written in the supported subset means the
same thing here as it does in OpenFGA, except where the documentation says otherwise.

## Further reading

- The Zanzibar paper: <https://www.usenix.org/conference/atc19/presentation/pang>, and an
  annotated copy at <https://zanzibar.tech>.
- OpenFGA's introduction to its modelling language:
  <https://openfga.dev/docs/configuration-language>.
