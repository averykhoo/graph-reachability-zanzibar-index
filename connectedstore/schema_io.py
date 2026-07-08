"""Schema persistence + self-describing store open helpers (connected-store spec §2/§4).

The schema SOURCE is the stored artifact; everything compiled from it (RuleSet,
SchemaInfo, plans) is cache, rebuilt on open -- the exact analogue of
``SetEngine.rebuild()`` over ``TupleV1``.

Write-once is the static-schema invariant made mechanical: a second ``save_schema``
for the same store raises, and opening with an explicit schema that disagrees with
the stored one is a loud error, never silent divergence.
"""

from __future__ import annotations

import json

from sqlmodel import Session, select

from index_v4 import ReachabilityIndex, StoreV4, WildcardIndex
from setengine import SetEngine
from setengine.setops import SetOps, DEFAULT_SETOPS
from zanzibar_utils_v1 import RuleSet, parse_openfga_schema

from .models import SchemaV4


class SchemaMismatch(ValueError):
    """An explicit schema disagrees with the store's persisted (immutable) schema."""


def save_schema(session: Session, store_id: str, schema_text: str,
                object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset()) -> SchemaV4:
    """Persist a store's schema, write-once (spec §2.1).

    Compiles first so an invalid schema is rejected before anything lands. Raises
    ``ValueError`` if the store already has a schema -- schemas are static; a new
    schema means a new store.
    """
    existing = session.get(SchemaV4, store_id)
    if existing is not None:
        raise ValueError(
            f"store {store_id!r} already has a schema (schemas are static -- "
            f"create a new store for a new schema)")
    parse_openfga_schema(schema_text, object_wildcard_shapes=object_wildcard_shapes)
    row = SchemaV4(
        store_id=store_id,
        schema_text=schema_text,
        object_wildcard_shapes=json.dumps(sorted([list(s) for s in object_wildcard_shapes])),
    )
    session.add(row)
    session.flush()
    return row


def load_schema(session: Session, store_id: str) -> tuple[str, frozenset[tuple[str, str]]]:
    """The store's persisted (schema_text, object_wildcard_shapes)."""
    row = session.get(SchemaV4, store_id)
    if row is None:
        raise KeyError(f"store {store_id!r} has no persisted schema")
    shapes = frozenset(tuple(s) for s in json.loads(row.object_wildcard_shapes))
    return row.schema_text, shapes


def ensure_schema(session: Session, store_id: str, schema_text: str,
                  object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset()
                  ) -> SchemaV4:
    """Idempotent bootstrap: persist the schema if the store has none, verify it
    matches if it does (spec §5-S1: an explicit schema must agree with a persisted
    one -- loud ``SchemaMismatch``, never silent divergence)."""
    row = session.get(SchemaV4, store_id)
    if row is None:
        return save_schema(session, store_id, schema_text, object_wildcard_shapes)
    stored_shapes = frozenset(tuple(s) for s in json.loads(row.object_wildcard_shapes))
    if row.schema_text != schema_text or stored_shapes != object_wildcard_shapes:
        raise SchemaMismatch(
            f"explicit schema for store {store_id!r} disagrees with its persisted "
            f"schema; schemas are static (write-once)")
    return row


def open_set_engine(session: Session, store_id: str, *,
                    ops: SetOps = DEFAULT_SETOPS,
                    ruleset: RuleSet | None = None) -> SetEngine:
    """Open the set engine on a self-describing store (schema loaded from the DB).
    ``ruleset`` skips recompiling a schema the caller already compiled."""
    schema_text, shapes = load_schema(session, store_id)
    return SetEngine(session, store_id, schema_text,
                     object_wildcard_shapes=shapes, ops=ops, ruleset=ruleset)


def open_graph_index(session: Session, store_id: str,
                     *, create_store_row: bool = True) -> tuple[WildcardIndex, RuleSet]:
    """Open the graph index on a self-describing store: load + compile the schema,
    return the wildcard façade and its compiled RuleSet (plans included)."""
    schema_text, shapes = load_schema(session, store_id)
    ruleset = parse_openfga_schema(schema_text, object_wildcard_shapes=shapes)
    if create_store_row and session.get(StoreV4, store_id) is None:
        session.add(StoreV4(id=store_id))
        session.flush()
    idx = ReachabilityIndex(session, store_id=store_id)
    return WildcardIndex(idx, ruleset.schema_info), ruleset
