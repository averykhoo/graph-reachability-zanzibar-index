# Explanation

These pages explain why the library works the way it does. They are for reading away from
the keyboard: none of them asks you to do anything, and none of them is needed to get a
first check working. For that, start with the [tutorials](../tutorials/index.md). For a
specific job, see the [how-to guides](../how-to/index.md). For exact names, arguments and
exceptions, see the [reference](../reference/index.md).

[Zanzibar and relationship-based access control](zanzibar-intro.md)
: What relationship-based access control is, what Google's Zanzibar paper contributed,
  and where this library and its schema language come from.

[The two backends](two-backends.md)
: The library answers every question in two different ways, one that does the work when
  you write and one that does it when you ask. Why both exist, how a `Store` combines
  them, and how they are kept in agreement.

[How the graph index works](graph-index.md)
: Precomputing who can reach what, counting paths so that a removal can be undone
  exactly, and representing `user:*` without listing every user.

[How `and` and `but not` work](boolean-operators.md)
: Why the operators cannot be precomputed like the rest, how the graph index keeps them
  up to date anyway, and why a relation may not recurse through them.

[Consistency: the tuple log, tokens and stalls](consistency.md)
: What a read can and cannot see after a write, especially when the index is kept up to
  date in the background.

[Semantics and differences from OpenFGA](semantics-vs-openfga.md)
: Where the library behaves exactly like OpenFGA, and where it deliberately does not.

[Wildcard extensions beyond OpenFGA](wildcard-extensions.md)
: Wildcard usersets, wildcard tuplesets and wildcard objects, and why using them emits a
  warning.

[How correctness is checked](assurance.md)
: How the two backends are tested against each other and against an independent
  reference, what has been proved, and what has not.

[Limits and costs](limits.md)
: What grows with your data, and what the library refuses in order to stay bounded.

```{toctree}
:maxdepth: 1
:hidden:

zanzibar-intro
two-backends
graph-index
boolean-operators
consistency
semantics-vs-openfga
wildcard-extensions
assurance
limits
```
