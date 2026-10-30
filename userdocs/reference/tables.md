# Database tables

The library stores everything in ten tables, all named `zanzibar_*`, with every explicit
index named `ix_zanzibar_*`. Many stores share one set of tables: each row carries its store
id.

## Creating them

The tables are declared on SQLModel's default metadata, `SQLModel.metadata`. Create them
with `SQLModel.metadata.create_all(engine)`, once per database, after the library's models
are imported. `import zanzibar` on its own imports no models; touching
{py:class}`zanzibar.Store` or importing `zanzibar.store` imports all of them. Importing
another subpackage registers only some: after `import zanzibar.setengine` alone,
`SQLModel.metadata` holds only `zanzibar_relation_tuple`, so `create_all` would create one
table and the first {py:class}`~zanzibar.Store` would raise
{py:exc}`zanzibar.TablesNotCreated` naming the other nine.

```python
from pathlib import Path
from sqlmodel import SQLModel, create_engine
import zanzibar.store  # registers the zanzibar_* tables on SQLModel.metadata

Path("tables.db").unlink(missing_ok=True)   # start from an empty database each run
engine = create_engine("sqlite:///tables.db")
SQLModel.metadata.create_all(engine)  # creates them next to your own tables

print(sorted(n for n in SQLModel.metadata.tables if n.startswith("zanzibar_")))  # -> ['zanzibar_delta_outbox', 'zanzibar_edge', 'zanzibar_index_cursor', 'zanzibar_node', 'zanzibar_relation_tuple', 'zanzibar_residue', 'zanzibar_residue_ref', 'zanzibar_schema_record', 'zanzibar_store', 'zanzibar_tuple_log']
```

Import `zanzibar.store` (or `from zanzibar import Store`) *before* calling `create_all`.
Calling it after a bare `import zanzibar` creates none of the library's tables, and the
first {py:class}`~zanzibar.Store` then raises {py:exc}`zanzibar.TablesNotCreated`.

`create_all` skips tables that already exist and never alters one. The library ships no
migrations.

## The tables

| table | holds | grows |
| --- | --- | --- |
| `zanzibar_schema_record` | one row per store: its schema as DSL text, and its object-wildcard shapes as a JSON list. Written once, never changed. | per store |
| `zanzibar_tuple_log` | every accepted write, as an `ADD` or `REMOVE` row. A row's `id` is the freshness token the write returned. The source of truth; rows are never updated or deleted. | every write, permanently |
| `zanzibar_relation_tuple` | the tuples that are currently stored | with the live tuples |
| `zanzibar_index_cursor` | one row per graph index: the last log id it has applied, and the stall marker when it cannot apply the next row | per store |
| `zanzibar_store` | one row per graph index store id | per store |
| `zanzibar_node` | the graph index's nodes: an entity, a userset or a relation on an object | with the index |
| `zanzibar_edge` | the graph index's precomputed reachability, with reference counts | with the index |
| `zanzibar_residue` | the graph index's wildcard and exclusion state for relations that use `and` / `but not` | with the index |
| `zanzibar_residue_ref` | a reverse lookup for `zanzibar_residue` | with the index |
| `zanzibar_delta_outbox` | a row for every change in reachability, read by the `and` / `but not` maintenance | every write, until pruned |

Of these, `zanzibar_schema_record`, `zanzibar_tuple_log` and `zanzibar_relation_tuple` are
the source data. Everything else is the graph index, which can be built again from them
({py:func}`zanzibar.store.rebuild_index`).

Nothing prunes `zanzibar_delta_outbox` for you; prune it with
{py:func}`zanzibar.graphindex.prune_outbox`. The tuple log is not compacted.

The row classes behind some of these tables are public, for reading:
{py:class}`zanzibar.store.SchemaRecord`, {py:class}`zanzibar.store.TupleLog`,
{py:class}`zanzibar.setengine.RelationTuple`, {py:class}`zanzibar.graphindex.IndexStore`,
{py:class}`zanzibar.graphindex.Node` and {py:class}`zanzibar.graphindex.Edge`. They are
exported for reading; the library's write path is {py:class}`zanzibar.Store`.

(deleting-a-store)=
## Deleting a store

The library has no call that deletes a store. To remove one (for example a tenant's data),
close every `Store` instance on that store id, then delete its rows from all ten tables in
one transaction. Eight tables carry the id in `store_id`; `zanzibar_store` holds it in `id`
and `zanzibar_index_cursor` in `index_store_id`. Delete the graph index's rows before
`zanzibar_store`, which they reference. The SQL is yours to write and run; for example:

```sql
DELETE FROM zanzibar_residue_ref    WHERE store_id = :id;
DELETE FROM zanzibar_residue        WHERE store_id = :id;
DELETE FROM zanzibar_edge           WHERE store_id = :id;
DELETE FROM zanzibar_node           WHERE store_id = :id;
DELETE FROM zanzibar_delta_outbox   WHERE store_id = :id;
DELETE FROM zanzibar_index_cursor   WHERE index_store_id = :id;
DELETE FROM zanzibar_store          WHERE id = :id;
DELETE FROM zanzibar_relation_tuple WHERE store_id = :id;
DELETE FROM zanzibar_tuple_log      WHERE store_id = :id;
DELETE FROM zanzibar_schema_record  WHERE store_id = :id;
```

Other stores in the same tables are not touched. The deleted store's freshness tokens
mean nothing afterwards; do not pass them to any store. The same id can then be created
again, with any schema, by `Store(session, store_id, schema=...)`.

## A name clash is an error

No `zanzibar_*` table is declared with `extend_existing`. A table of yours with the same
name as one of them raises SQLAlchemy's {py:exc}`~sqlalchemy.exc.InvalidRequestError`,
whichever of the two is declared first, so the two are never silently merged. The
SQLAlchemy message suggests `extend_existing=True`; that would merge your table's columns
into the library's table.

## Missing tables: `TablesNotCreated`

If `create_all` was not run, opening a {py:class}`~zanzibar.Store` (or calling
{py:meth}`Store.adopt <zanzibar.Store.adopt>`) raises {py:exc}`zanzibar.TablesNotCreated`
instead of the database driver's own error. Its `missing` attribute lists the absent table
names. It is a {py:exc}`RuntimeError`.

```python
from sqlmodel import Session, create_engine
import zanzibar

empty = create_engine("sqlite://")      # create_all never ran on this one
with Session(empty) as session:
    try:
        zanzibar.Store(session, "my-app", schema="type user\n")
    except zanzibar.TablesNotCreated as exc:
        missing = exc.missing
print("zanzibar_tuple_log" in missing)  # -> True
```

## Old SQLite files: `TablesOutdated`

This refusal is new in 0.1.0; the 0.0.x releases do not have it.

The 0.0.x releases created `zanzibar_node` on SQLite without `AUTOINCREMENT`, so SQLite
could reuse a deleted node's id, and a lookup result held across a write could name the
wrong node. From 0.1.0, opening a {py:class}`~zanzibar.Store` on such a file raises
{py:exc}`zanzibar.TablesOutdated`; its `table` attribute is `"zanzibar_node"`. The library
does not migrate the file. PostgreSQL databases are not affected.

To move a store to a new file, see
[Upgrade from 0.0.x to 0.1](../how-to/upgrade-0.1.md).
