"""Schema persistence + self-describing store open helpers.

The schema SOURCE is the stored artifact; everything compiled from it (RuleSet,
SchemaInfo, plans) is cache, rebuilt on open -- the exact analogue of
``SetEngine.rebuild()`` over ``RelationTuple``.

Write-once is the static-schema invariant made mechanical: a second ``save_schema``
for the same store raises, and opening with an explicit schema that disagrees with
the stored one is a loud error, never silent divergence.
"""
# Provenance (moved out of the docstring, TK123 item 14): connected-store spec §2/§4.

from __future__ import annotations

import contextlib
import json
from typing import cast

from sqlmodel import Session

from zanzibar.graphindex import ReachabilityIndex, IndexStore, WildcardIndex
from zanzibar.setengine import SetEngine
from zanzibar.setengine.setops import SetOps, DEFAULT_SETOPS, require_setops
from zanzibar.schema.argcheck import require_instance, require_session, require_shapes, require_str
from zanzibar.schema import RuleSet, SchemaInfo, parse_openfga_schema, parse_schema_ast, validate_store_id
from zanzibar.schema.syntax import explain_difference, first_schema_difference
from zanzibar.schema.parser import _parse_schema_ast_checked
from zanzibar.schema.compiler import _validate_object_wildcard_shapes
# ``SchemaMismatch`` (TK123 A53) and ``PersistedSchemaRefused`` (TK153 F17) live in
# ``zanzibar.schema.errors`` so the set engine can raise them without importing this
# layer; re-exported here, the same class objects.
from zanzibar.schema.errors import (PersistedSchemaRefused, SchemaMismatch,  # noqa: F401
                                    ShapeNoLongerAccepted, ZanzibarError)

from .models import SchemaRecord


class StoreNotFound(ZanzibarError, KeyError):
    """The store id has no persisted schema in this database: the store was never
    created here (or the session points at another database).

    A ``KeyError`` subclass, as the bare ``KeyError`` it replaces was. ``store_id`` is an
    attribute. Create the store once by passing its schema:
    ``Store(session, store_id, schema=...)``."""

    def __init__(self, store_id: str):
        self.store_id = store_id
        super().__init__(
            f"store {store_id!r} has no persisted schema: no store with this id was "
            f"created in this database. Create it once by passing its schema: "
            f"Store(session, {store_id!r}, schema=...)")

    def __str__(self) -> str:
        # KeyError.__str__ would repr() the message, quoting it a second time.
        return str(self.args[0])


class TablesNotCreated(ZanzibarError, RuntimeError):
    """The database has no ``zanzibar_*`` tables (or only some of them): the
    ``SQLModel.metadata.create_all(engine)`` step was skipped. ``missing`` lists the
    absent table names. Raised by ``Store`` in place of the driver's own error, which
    differs per database."""

    def __init__(self, missing: list[str]):
        self.missing = list(missing)
        super().__init__(
            f"the zanzibar tables are missing from this database ({', '.join(missing)}): "
            f"run SQLModel.metadata.create_all(engine) once, after importing "
            f"zanzibar.store, before opening a Store")


class TablesOutdated(ZanzibarError, RuntimeError):
    """The ``zanzibar_node`` table in this SQLite database was created by zanzibar-index
    0.0.x without ``AUTOINCREMENT``, so SQLite can reuse a deleted node's id and a
    ``LookupResult`` held across a write could name the wrong node. ``table`` is the
    table name. 0.1.0 does not migrate 0.0.x files: create the zanzibar tables in a new
    database file (``SQLModel.metadata.create_all(engine)`` after importing
    ``zanzibar.store``) and write the tuples again."""
    # Provenance: TK154 (docs/tk154-stale-lookup-ids-2026-10-16.md).

    def __init__(self, table: str = 'zanzibar_node'):
        self.table = table
        super().__init__(
            f"table {table!r} in this SQLite database has no AUTOINCREMENT (it was created "
            f"by zanzibar-index 0.0.x), so a deleted node's id can be reused and a "
            f"LookupResult held across a write could name the wrong node. Create the "
            f"zanzibar tables in a NEW database file (SQLModel.metadata.create_all(engine), "
            f"after importing zanzibar.store) and write the tuples again; 0.1.0 does not "
            f"migrate 0.0.x files")

    def __reduce__(self):
        # args holds only the message; without this, unpickling/copying would call
        # __init__(message) and set .table to the whole message.
        return (self.__class__, (self.table,))


def refuse_reusable_node_ids(session: Session) -> None:
    """On SQLite, refuse a ``zanzibar_node`` table created without AUTOINCREMENT (raises
    ``TablesOutdated``): such a table re-hands a removed node's id, so a held lookup result
    could name a different node. A no-op on other dialects, and when the table does not
    exist (``TablesNotCreated`` covers that)."""
    # TK154. Dialect gate is graphindex/core.py::is_sqlite, the one dialect seam.
    from sqlalchemy import text
    from zanzibar.graphindex.core import is_sqlite
    if not is_sqlite(session):
        return
    ddl = session.connection().execute(
        text("select sql from sqlite_master where type='table' and name='zanzibar_node'")
    ).scalar()
    if ddl is None:
        return          # no table at all: the caller's TablesNotCreated path reports it
    if 'AUTOINCREMENT' not in ddl.upper():
        raise TablesOutdated('zanzibar_node')


def missing_tables(session: Session) -> list[str]:
    """The ``zanzibar_*`` tables of the package's models that the session's database
    lacks. Dialect-neutral: it asks the inspector, never parses a driver message."""
    from sqlalchemy import inspect as sa_inspect
    from sqlmodel import SQLModel
    insp = sa_inspect(session.connection())
    return sorted(name for name in SQLModel.metadata.tables
                  if name.startswith('zanzibar_') and not insp.has_table(name))


@contextlib.contextmanager
def _persisted_schema_parse(store_id: str):
    """Wrap a parse of ``store_id``'s PERSISTED text (and its object-wildcard shapes): a
    `TK137` or `TK147` refusal (``ShapeNoLongerAccepted``) becomes
    ``PersistedSchemaRefused`` (C10). Any other ``ValueError`` passes through unchanged:
    only such a shape can have been saved by an older version and be refused now, so
    anything else is not a version break. A text the CALLER passed is never parsed under
    this wrapper (its refusal is the caller's to fix, not a stored-store break)."""
    try:
        yield
    except ShapeNoLongerAccepted as e:
        raise PersistedSchemaRefused(store_id, e) from e


def save_schema(session: Session, store_id: str, schema_text: str,
                object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset()
                ) -> tuple[SchemaRecord, RuleSet]:
    """Persist a store's schema, write-once.

    Compiles first so an invalid schema is rejected before anything lands. Saving the
    schema the store already has is a no-op ("the same" as ``Store(..., schema=...)``
    judges it on reopen: same parsed schema and the same ``object_wildcard_shapes``); a
    different one raises ``SchemaMismatch`` (a ``ValueError``) naming the first
    difference -- schemas are static; a new schema means a new store. Returns the
    persisted row and the compiled ``RuleSet`` so a bootstrapping caller can reuse it
    instead of re-parsing the same text via ``open_graph_index`` (the schema is compiled
    once, not twice).
    """
    # Provenance (moved out of the docstring, TK123 item 14): spec §2.1.
    validate_store_id(store_id)  # TK127 follow-up: the one SchemaRecord insert
    require_session('save_schema', session)                 # TK179
    require_str('save_schema', 'schema_text', schema_text)  # TK179 G7
    object_wildcard_shapes = require_shapes('save_schema', object_wildcard_shapes)
    existing = session.get(SchemaRecord, store_id)
    if existing is not None:
        _verify_same_schema(existing, schema_text, object_wildcard_shapes)
        return existing, parse_openfga_schema(
            schema_text, object_wildcard_shapes=object_wildcard_shapes)
    ruleset = parse_openfga_schema(schema_text, object_wildcard_shapes=object_wildcard_shapes)
    row = SchemaRecord(
        store_id=store_id,
        schema_text=schema_text,
        object_wildcard_shapes=json.dumps(sorted([list(s) for s in object_wildcard_shapes])),
    )
    session.add(row)
    session.flush()
    return row, ruleset


def load_schema(session: Session, store_id: str) -> tuple[str, frozenset[tuple[str, str]]]:
    """The store's persisted (schema_text, object_wildcard_shapes)."""
    row = session.get(SchemaRecord, store_id)
    if row is None:
        raise StoreNotFound(store_id)
    shapes = frozenset(tuple(s) for s in json.loads(row.object_wildcard_shapes))
    return row.schema_text, shapes


def ensure_schema(session: Session, store_id: str, schema_text: str,
                  object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset()
                  ) -> tuple[SchemaRecord, RuleSet | None]:
    """Idempotent bootstrap: persist the schema if the store has none, verify it
    matches if it does (an explicit schema must agree with a persisted
    one -- loud ``SchemaMismatch``, never silent divergence).

    Returns ``(row, ruleset)``; ``ruleset`` is the freshly compiled ``RuleSet`` when
    this call bootstrapped the schema (so the caller can hand it to
    ``open_graph_index`` and avoid a second parse), else ``None`` (the schema was
    already present and only verified, so nothing was compiled).

    "Agrees" means the same PARSED schema: both texts parse to an equal
    ``SchemaAST``, so whitespace, line endings, comments, header lines and the order of
    type blocks or of ``define`` lines do not matter. Everything either backend compiles
    is derived from ``(SchemaAST, object_wildcard_shapes)``, so an equal AST is the same
    schema. The persisted text stays the source of truth and is never rewritten."""
    # Provenance (moved out of the docstring, TK123 item 14): connected-store spec sec 5-S1.
    # Provenance (moved out of the docstring, TK123 item 14): `TK136`.
    row = session.get(SchemaRecord, store_id)
    if row is None:
        return save_schema(session, store_id, schema_text, object_wildcard_shapes)
    _verify_same_schema(row, schema_text, object_wildcard_shapes)
    return row, None


def _verify_same_schema(row: SchemaRecord, schema_text: str,
                        object_wildcard_shapes: frozenset[tuple[str, str]]) -> None:
    """Raise ``SchemaMismatch`` unless ``schema_text`` / ``object_wildcard_shapes`` are
    the schema persisted in ``row`` (see ``_schema_difference``). A persisted schema this
    version refuses -- its text, or (TK147) its object-wildcard shapes -- raises
    ``PersistedSchemaRefused`` FIRST, whatever was passed (one type for one cause)."""
    store_id = row.store_id
    # cast: normalises list-shaped pairs (e.g. JSON-decoded) back to the declared tuples
    object_wildcard_shapes = cast('frozenset[tuple[str, str]]',
                                  frozenset(tuple(s) for s in object_wildcard_shapes))
    stored_shapes = frozenset(tuple(s) for s in json.loads(row.object_wildcard_shapes))
    with _persisted_schema_parse(store_id):
        stored_ast, stored_declared = _parse_schema_ast_checked(row.schema_text)
        _validate_object_wildcard_shapes(stored_ast, stored_shapes, stored_declared)
    if stored_shapes != object_wildcard_shapes:
        raise SchemaMismatch(
            f"explicit schema for store {store_id!r} disagrees with its persisted "
            f"schema: object_wildcard_shapes {sorted(object_wildcard_shapes)} != "
            f"{sorted(stored_shapes)}; schemas are static (write-once)")
    diff = _schema_difference(store_id, row.schema_text, schema_text, stored_ast=stored_ast)
    if diff is not None:
        raise SchemaMismatch(
            f"explicit schema for store {store_id!r} disagrees with its persisted "
            f"schema, first at {explain_difference(diff)}; schemas are static (write-once)")


def _schema_difference(store_id: str, stored_text: str, schema_text: str, *,
                       stored_ast=None) -> str | None:
    """``None`` when the passed text parses to the stored text's schema, up to the order
    of type blocks, ``define`` lines and restriction lists; else the first differing
    ``type#relation`` (TK123 item 18). A passed text that does not parse raises the
    parser's own error; a STORED text refused since `TK137` raises
    ``PersistedSchemaRefused`` (C10), including when the passed text IS the stored text
    (identical text is parsed once, under the persisted-schema wrapper, not twice)."""
    # TK153 F17 review (2026-10-17): identical text used to return None BEFORE any parse, so
    # save_schema(id, <stored refused text>) raised the bare ShapeNoLongerAccepted from its
    # own later parse, and ensure_schema returned (row, None) silently. ``stored_ast``: the
    # caller already parsed the stored text under the wrapper (TK147, no second parse).
    if stored_ast is None:
        with _persisted_schema_parse(store_id):
            stored_ast = parse_schema_ast(stored_text)
    if stored_text == schema_text:
        return None
    diff = first_schema_difference(stored_ast, parse_schema_ast(schema_text))
    if diff is None:
        return None
    return (diff.replace('only in the first schema', 'only in the persisted schema')
                .replace('only in the second schema', 'only in the schema passed here'))


def _same_schema(store_id: str, stored_text: str, schema_text: str) -> bool:
    """True when the passed text is the stored schema (see ``_schema_difference``)."""
    return _schema_difference(store_id, stored_text, schema_text) is None


def open_set_engine(session: Session, store_id: str, *,
                    ops: SetOps = DEFAULT_SETOPS,
                    ruleset: RuleSet | None = None) -> SetEngine:
    """Open the set engine on a store a ``Store`` created, with the schema persisted in
    the database (so you cannot pass a different one by mistake).

    This is the remedy the ``SchemaMismatch`` from ``SetEngine(session, store_id, schema)``
    names. Raises ``StoreNotFound`` when no schema is saved under ``store_id``, and
    ``PersistedSchemaRefused`` when this version refuses the saved schema. ``ruleset``
    skips recompiling a schema the caller already compiled (it must be that schema's).
    Public since 0.1.0."""
    validate_store_id(store_id)  # TK179 G6/G8: refuse before load_schema's statement
    require_session('open_set_engine', session)
    require_setops(ops)
    require_instance('open_set_engine', 'ruleset', ruleset, RuleSet, optional=True,
                     what="None or the RuleSet compiled from this store's schema")
    schema_text, shapes = load_schema(session, store_id)
    with _persisted_schema_parse(store_id):
        return SetEngine(session, store_id, schema_text,
                         object_wildcard_shapes=shapes, ops=ops, ruleset=ruleset)


def open_graph_index(session: Session, store_id: str,
                     *, create_store_row: bool = True,
                     ruleset: RuleSet | None = None) -> tuple[WildcardIndex, RuleSet]:
    """Open the graph index on a self-describing store: load + compile the schema,
    return the wildcard facade and its compiled RuleSet (plans included).
    ``ruleset`` skips re-parsing a schema the caller just compiled (bootstrap reuse)."""
    if ruleset is None:
        schema_text, shapes = load_schema(session, store_id)
        with _persisted_schema_parse(store_id):
            ruleset = parse_openfga_schema(schema_text, object_wildcard_shapes=shapes)
    if create_store_row and session.get(IndexStore, store_id) is None:
        session.add(IndexStore(id=store_id))
        session.flush()
    idx = ReachabilityIndex(session, store_id=store_id)
    # cast: a compiled RuleSet (parse_openfga_schema) always carries its SchemaInfo
    return WildcardIndex(idx, cast(SchemaInfo, ruleset.schema_info)), ruleset
