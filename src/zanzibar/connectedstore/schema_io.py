"""Schema persistence + self-describing store open helpers (connected-store spec §2/§4).

The schema SOURCE is the stored artifact; everything compiled from it (RuleSet,
SchemaInfo, plans) is cache, rebuilt on open -- the exact analogue of
``SetEngine.rebuild()`` over ``RelationTuple``.

Write-once is the static-schema invariant made mechanical: a second ``save_schema``
for the same store raises, and opening with an explicit schema that disagrees with
the stored one is a loud error, never silent divergence.
"""

from __future__ import annotations

import contextlib
import json

from sqlmodel import Session, select

from zanzibar.graphindex import ReachabilityIndex, Store, WildcardIndex
from zanzibar.setengine import SetEngine
from zanzibar.setengine.setops import SetOps, DEFAULT_SETOPS
from zanzibar.schema import RuleSet, parse_openfga_schema, parse_schema_ast, validate_store_id
# ``SchemaMismatch`` moved to ``zanzibar.schema.errors`` (TK123 A53) so the set engine can
# raise it without importing this layer; re-exported here, the same class object.
from zanzibar.schema.errors import SchemaMismatch, ShapeRefusedSinceTK137  # noqa: F401

from .models import SchemaRecord


class PersistedSchemaRefused(ValueError):
    """A store's PERSISTED schema text uses a shape this version refuses, so the store
    cannot be opened (`TK137` review challenge C10, 2026-10-14).

    Every open re-parses the stored text (the compiled schema is cache), so a store saved
    by zanzibar-index 0.0.4 or earlier with a shape `TK137` refuses stops opening. The
    message says so, quotes the parser's refusal, and gives the rewrite that keeps the
    meaning the store was serving, so the break reads as a version break, not corruption.
    There is no lenient mode on purpose: schemas are write-once, and a store opened under
    a schema the parser refuses would run text no fresh store may hold. ``store_id``,
    ``refusal`` (the parser's ``ShapeRefusedSinceTK137``, also ``__cause__``) and
    ``instead`` are attributes. A ``ValueError`` subclass, as the parser's refusal was."""

    def __init__(self, store_id: str, refusal: ShapeRefusedSinceTK137):
        self.store_id = store_id
        self.refusal = refusal
        self.instead = refusal.instead
        super().__init__(
            f"store {store_id!r}: its persisted schema was saved by zanzibar-index 0.0.4 "
            f"or earlier using a shape this version refuses (TK137): {refusal}. To rewrite: "
            f"{refusal.instead}. Schemas are write-once, so the rewritten schema needs a NEW "
            f"store id, with this store's tuples written again (see CHANGELOG.md, TK137).")


@contextlib.contextmanager
def _persisted_schema_parse(store_id: str):
    """Wrap a parse of ``store_id``'s PERSISTED text: a `TK137` refusal becomes
    ``PersistedSchemaRefused`` (C10). Any other ``ValueError`` passes through unchanged:
    only a TK137 shape can have been saved by an older version and be refused now, so
    anything else is not a version break. A text the CALLER passed is never parsed under
    this wrapper (its refusal is the caller's to fix, not a stored-store break)."""
    try:
        yield
    except ShapeRefusedSinceTK137 as e:
        raise PersistedSchemaRefused(store_id, e) from e


def save_schema(session: Session, store_id: str, schema_text: str,
                object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset()
                ) -> tuple[SchemaRecord, RuleSet]:
    """Persist a store's schema, write-once (spec §2.1).

    Compiles first so an invalid schema is rejected before anything lands. Raises
    ``ValueError`` if the store already has a schema -- schemas are static; a new
    schema means a new store. Returns the persisted row and the compiled ``RuleSet``
    so a bootstrapping caller can reuse it instead of re-parsing the same text via
    ``open_graph_index`` (the schema is compiled once, not twice).
    """
    validate_store_id(store_id)  # TK127 follow-up: the one SchemaRecord insert
    existing = session.get(SchemaRecord, store_id)
    if existing is not None:
        raise ValueError(
            f"store {store_id!r} already has a schema (schemas are static -- "
            f"create a new store for a new schema)")
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
        raise KeyError(f"store {store_id!r} has no persisted schema")
    shapes = frozenset(tuple(s) for s in json.loads(row.object_wildcard_shapes))
    return row.schema_text, shapes


def ensure_schema(session: Session, store_id: str, schema_text: str,
                  object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset()
                  ) -> tuple[SchemaRecord, RuleSet | None]:
    """Idempotent bootstrap: persist the schema if the store has none, verify it
    matches if it does (spec §5-S1: an explicit schema must agree with a persisted
    one -- loud ``SchemaMismatch``, never silent divergence).

    Returns ``(row, ruleset)``; ``ruleset`` is the freshly compiled ``RuleSet`` when
    this call bootstrapped the schema (so the caller can hand it to
    ``open_graph_index`` and avoid a second parse), else ``None`` (the schema was
    already present and only verified, so nothing was compiled).

    "Agrees" means the same PARSED schema (`TK136`): both texts parse to an equal
    ``SchemaAST``, so whitespace, line endings, comments, header lines and the order of
    type blocks or of ``define`` lines do not matter. Everything either backend compiles
    is derived from ``(SchemaAST, object_wildcard_shapes)``, so an equal AST is the same
    schema. The persisted text stays the source of truth and is never rewritten."""
    row = session.get(SchemaRecord, store_id)
    if row is None:
        return save_schema(session, store_id, schema_text, object_wildcard_shapes)
    stored_shapes = frozenset(tuple(s) for s in json.loads(row.object_wildcard_shapes))
    if stored_shapes != object_wildcard_shapes or not _same_schema(
            store_id, row.schema_text, schema_text):
        raise SchemaMismatch(
            f"explicit schema for store {store_id!r} disagrees with its persisted "
            f"schema; schemas are static (write-once)")
    return row, None


def _same_schema(store_id: str, stored_text: str, schema_text: str) -> bool:
    """True when the passed text parses to the stored text's ``SchemaAST``. Identical text
    short-circuits, so a stored schema is never re-parsed just to be reopened verbatim. A
    passed text that does not parse raises the parser's own ``ValueError``; a STORED text
    refused since `TK137` raises ``PersistedSchemaRefused`` (C10)."""
    if stored_text == schema_text:
        return True
    with _persisted_schema_parse(store_id):
        stored_ast = parse_schema_ast(stored_text)
    return stored_ast == parse_schema_ast(schema_text)


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
    if create_store_row and session.get(Store, store_id) is None:
        session.add(Store(id=store_id))
        session.flush()
    idx = ReachabilityIndex(session, store_id=store_id)
    return WildcardIndex(idx, ruleset.schema_info), ruleset
