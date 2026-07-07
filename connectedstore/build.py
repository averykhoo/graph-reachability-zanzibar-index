"""build_index: the offline bootstrap builder (connected-store spec §4).

Materializes a graph index for an EXISTING tuple store: capture the log watermark,
bulk-load the ``TupleV1`` snapshot through the rewrite fan-out, run the delta
processor's ``backfill()`` (the P6 bulk path), and set the cursor to the watermark.
The Leopard paper's offline builder; the async worker then streams the tail.
Deliberately NOT the async seam -- this is how any index is born, under either
schedule.

Same schema always (schemas are static): the index inherits the source store's
persisted schema; a separate-id index gets the schema copied so it is
self-describing too.
"""

from __future__ import annotations

from sqlmodel import Session, select

from index_v4 import NodeV4, WildcardIndex
from index_v4.processor import DeltaProcessor
from setengine.models import TupleV1
from zanzibar_utils_v1 import Entity, RelationalTriple, RuleSet

from .apply import ensure_cursor, _norm
from .models import IndexCursorV1
from .schema_io import ensure_schema, load_schema, open_graph_index
from .source import log_watermark


def build_index(session: Session, source_store_id: str,
                index_store_id: str | None = None,
                ) -> tuple[IndexCursorV1, WildcardIndex, RuleSet]:
    """Build a fresh graph index from a tuple store's current snapshot.

    One transaction (committed on success, rolled back on failure). Refuses to run
    on an index that already has state -- a fresh build wants a fresh store; use
    ``advance_index`` to catch an existing index up instead.
    """
    index_store_id = index_store_id or source_store_id

    try:
        watermark = log_watermark(session, source_store_id)
        schema_text, shapes = load_schema(session, source_store_id)
        if index_store_id != source_store_id:
            ensure_schema(session, index_store_id, schema_text, shapes)

        existing_cursor = session.exec(
            select(IndexCursorV1)
            .where(IndexCursorV1.index_store_id == index_store_id)
        ).first()
        if existing_cursor is not None:
            raise ValueError(
                f"index {index_store_id!r} already exists (cursor at "
                f"{existing_cursor.applied_log_id}); build_index is for fresh builds")
        has_nodes = session.exec(
            select(NodeV4).where(NodeV4.store_id == index_store_id).limit(1)
        ).first()
        if has_nodes is not None:
            raise ValueError(
                f"index store {index_store_id!r} already holds graph state; "
                f"build_index is for fresh builds")

        widx, ruleset = open_graph_index(session, index_store_id)

        # bulk-load the snapshot through the rewrite fan-out (leaf writes only)
        rows = session.exec(
            select(TupleV1).where(TupleV1.store_id == source_store_id)
            .order_by(TupleV1.id)  # type: ignore[arg-type]
        ).all()
        for r in rows:
            sp = Ellipsis if r.subject_predicate == '...' else r.subject_predicate
            triple = RelationalTriple(Entity(r.subject_type, r.subject_name), r.relation,
                                      Entity(r.object_type, r.object_name), sp)
            for d in ruleset.apply(triple):
                widx.add_tuple(_norm(d.subject_predicate), d.subject.type, d.subject.name,
                               d.relation, d.object.type, d.object.name)

        # derive the boolean state in one offline pass (P6 backfill precedent)
        proc = None
        if ruleset.compiled is not None and ruleset.compiled.plans:
            proc = DeltaProcessor(widx, ruleset.compiled)
            proc.backfill()

        cursor = ensure_cursor(session, index_store_id, source_store_id)
        cursor.applied_log_id = watermark
        session.add(cursor)
        session.commit()
        return cursor, widx, ruleset
    except Exception:
        session.rollback()
        raise
