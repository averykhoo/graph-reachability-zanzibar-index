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

from sqlmodel import Session, select

from zanzibar.graphindex import ReachabilityIndex, IndexStore, WildcardIndex
from zanzibar.setengine import SetEngine
from zanzibar.setengine.setops import SetOps, DEFAULT_SETOPS
from zanzibar.schema import RuleSet, parse_openfga_schema, parse_schema_ast, validate_store_id
from zanzibar.schema.syntax import first_schema_difference
# ``SchemaMismatch`` moved to ``zanzibar.schema.errors`` (TK123 A53) so the set engine can
# raise it without importing this layer; re-exported here, the same class object.
from zanzibar.schema.errors import SchemaMismatch, ShapeNoLongerAccepted, ZanzibarError  # noqa: F401

from .models import SchemaRecord


class PersistedSchemaRefused(ZanzibarError, ValueError):
    """A store's PERSISTED schema text uses a shape this version refuses, so the store
    cannot be opened.

    Every open re-parses the stored text (the compiled schema is cache), so a store saved
    by zanzibar-index 0.0.4 or earlier with a shape 0.0.5 refuses stops opening. The
    message says so, quotes the parser's refusal, and gives the rewrite that keeps the
    meaning the store was serving, so the break reads as a version break, not corruption.
    There is no lenient mode on purpose: schemas are write-once, and a store opened under
    a schema the parser refuses would run text no fresh store may hold. ``store_id``,
    ``refusal`` (the parser's ``ShapeNoLongerAccepted``, also ``__cause__``) and
    ``instead`` are attributes. A ``ValueError`` subclass, as the parser's refusal was."""
    # Provenance (moved out of the docstring, TK123 item 14): TK137.
    # Provenance (moved out of the docstring, TK123 item 14): `TK137` review challenge C10,
    # 2026-10-14.

    def __init__(self, store_id: str, refusal: ShapeNoLongerAccepted):
        self.store_id = store_id
        self.refusal = refusal
        self.instead = refusal.instead
        super().__init__(
            f"store {store_id!r}: its persisted schema was saved by zanzibar-index 0.0.4 "
            f"or earlier using a shape this version refuses: {refusal}. To rewrite: "
            f"{refusal.instead}. Schemas are write-once, so the rewritten schema needs a NEW "
            f"store id, with this store's tuples written again (see the 0.0.5 changelog).")


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
    """Wrap a parse of ``store_id``'s PERSISTED text: a `TK137` refusal becomes
    ``PersistedSchemaRefused`` (C10). Any other ``ValueError`` passes through unchanged:
    only a TK137 shape can have been saved by an older version and be refused now, so
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
    the schema persisted in ``row`` (see ``_schema_difference``)."""
    store_id = row.store_id
    object_wildcard_shapes = frozenset(tuple(s) for s in object_wildcard_shapes)
    stored_shapes = frozenset(tuple(s) for s in json.loads(row.object_wildcard_shapes))
    if stored_shapes != object_wildcard_shapes:
        raise SchemaMismatch(
            f"explicit schema for store {store_id!r} disagrees with its persisted "
            f"schema: object_wildcard_shapes {sorted(object_wildcard_shapes)} != "
            f"{sorted(stored_shapes)}; schemas are static (write-once)")
    diff = _schema_difference(store_id, row.schema_text, schema_text)
    if diff is not None:
        raise SchemaMismatch(
            f"explicit schema for store {store_id!r} disagrees with its persisted "
            f"schema, first at {diff}; schemas are static (write-once)")


def _schema_difference(store_id: str, stored_text: str, schema_text: str) -> str | None:
    """``None`` when the passed text parses to the stored text's schema, up to the order
    of type blocks, ``define`` lines and restriction lists; else the first differing
    ``type#relation`` (TK123 item 18). Identical text short-circuits, so a stored schema
    is never re-parsed just to be reopened verbatim. A passed text that does not parse
    raises the parser's own error; a STORED text refused since `TK137` raises
    ``PersistedSchemaRefused`` (C10)."""
    if stored_text == schema_text:
        return None
    with _persisted_schema_parse(store_id):
        stored_ast = parse_schema_ast(stored_text)
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
    """Open the set engine on a self-describing store (schema loaded from the DB).
    ``ruleset`` skips recompiling a schema the caller already compiled."""
    schema_text, shapes = load_schema(session, store_id)
    with _persisted_schema_parse(store_id):
        return SetEngine(session, store_id, schema_text,
                         object_wildcard_shapes=shapes, ops=ops, ruleset=ruleset)


def open_graph_index(session: Session, store_id: str,
                     *, create_store_row: bool = True,
                     ruleset: RuleSet | None = None) -> tuple[WildcardIndex, RuleSet]:
    """Open the graph index on a self-describing store: load + compile the schema,
    return the wildcard façade and its compiled RuleSet (plans included).
    ``ruleset`` skips re-parsing a schema the caller just compiled (bootstrap reuse)."""
    if ruleset is None:
        schema_text, shapes = load_schema(session, store_id)
        with _persisted_schema_parse(store_id):
            ruleset = parse_openfga_schema(schema_text, object_wildcard_shapes=shapes)
    if create_store_row and session.get(IndexStore, store_id) is None:
        session.add(IndexStore(id=store_id))
        session.flush()
    idx = ReachabilityIndex(session, store_id=store_id)
    return WildcardIndex(idx, ruleset.schema_info), ruleset
