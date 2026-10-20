# How-to guides

Recipes for specific tasks, for when you already know what you want to do. If you are
new to the library, start with [the tutorials](../tutorials/index.md); for exact
signatures and every option, see [the reference](../reference/index.md).

**Model your permissions**

- [Port an OpenFGA model](port-openfga.md): load an existing model and its tuples.
- [Rewrite a refused schema shape](rewrite-refused-shape.md): read a refusal and apply
  the fix.
- [Common modelling patterns](patterns.md): groups, roles, parent inheritance, public
  access, block lists, requiring two relations.
- [Change a schema](change-schema.md): move a store's tuples to a new schema.

**Load and read data**

- [Bulk-load or adopt an existing store](bulk-load-adopt.md): build the index for
  tuples you already have.
- [Find who can access what](query-access.md): list the users of an object, or the
  objects a user can reach.
- [Use async mode and freshness tokens](async-tokens.md): write without waiting for the
  index, and read your own writes.
- [Use the backends directly](backends-direct.md): open a set engine without a `Store`,
  for tooling and experiments. An application should use a `Store` instead.

**Run in production**

- [Run on PostgreSQL](postgresql.md): isolation level, sessions, several instances.
- [Turn on runtime checks in production](runtime-checks.md): detect a corrupt index.
- [Cap write fan-out](fanout-cap.md): refuse a write that would add too many index rows.
- [Handle errors](errors.md): what to catch, and what to let through.

**Maintain a running store**

- [Recover a stalled index](stall-recovery.md): clear a row the index cannot apply.
- [Prune the change outbox](prune-outbox.md): stop the outbox table growing.
- [Upgrade from 0.0.x to 0.1](upgrade-0.1.md): renamed names and changed answers.

```{toctree}
:maxdepth: 1
:hidden:

port-openfga
rewrite-refused-shape
patterns
change-schema
bulk-load-adopt
query-access
async-tokens
backends-direct
postgresql
runtime-checks
fanout-cap
errors
stall-recovery
prune-outbox
upgrade-0.1
```
