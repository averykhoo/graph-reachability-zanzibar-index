"""Schema persistence + self-describing store open helpers (connected-store spec §2/§4).

The schema SOURCE is the stored artifact; everything compiled from it (RuleSet,
SchemaInfo, plans) is cache, rebuilt on open -- the exact analogue of
``SetEngine.rebuild()`` over ``RelationTuple``.

Write-once is the static-schema invariant made mechanical: a second ``save_schema``
for the same store raises, and opening with an explicit schema that disagrees with
the stored one is a loud error, never silent divergence.
"""

from __future__ import annotations

import json

from sqlmodel import Session, select

from zanzibar.graphindex import ReachabilityIndex, Store, WildcardIndex
from zanzibar.setengine import SetEngine
from zanzibar.setengine.setops import SetOps, DEFAULT_SETOPS
from zanzibar.schema import RuleSet, parse_openfga_schema, validate_store_id

from .models import SchemaRecord


class SchemaMismatch(ValueError):
    """An explicit schema disagrees with the store's persisted (immutable) schema."""


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
    already present and only verified, so nothing was compiled)."""
    row = session.get(SchemaRecord, store_id)
    if row is None:
        return save_schema(session, store_id, schema_text, object_wildcard_shapes)
    stored_shapes = frozenset(tuple(s) for s in json.loads(row.object_wildcard_shapes))
    if row.schema_text != schema_text or stored_shapes != object_wildcard_shapes:
        raise SchemaMismatch(
            f"explicit schema for store {store_id!r} disagrees with its persisted "
            f"schema; schemas are static (write-once)")
    return row, None


def open_set_engine(session: Session, store_id: str, *,
                    ops: SetOps = DEFAULT_SETOPS,
                    ruleset: RuleSet | None = None) -> SetEngine:
    """Open the set engine on a self-describing store (schema loaded from the DB).
    ``ruleset`` skips recompiling a schema the caller already compiled."""
    schema_text, shapes = load_schema(session, store_id)
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
        ruleset = parse_openfga_schema(schema_text, object_wildcard_shapes=shapes)
    if create_store_row and session.get(Store, store_id) is None:
        session.add(Store(id=store_id))
        session.flush()
    idx = ReachabilityIndex(session, store_id=store_id)
    return WildcardIndex(idx, ruleset.schema_info), ruleset
