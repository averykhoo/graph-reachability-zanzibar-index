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
from index_v4.bulk_build import bulk_build
from index_v4.processor import DeltaProcessor
from setengine.models import TupleV1
from zanzibar_utils_v1 import Entity, RelationalTriple, RuleSet

from .apply import ensure_cursor, _norm
from .models import IndexCursorV1
from .schema_io import ensure_schema, load_schema, open_graph_index
from .source import log_watermark


def build_index(session: Session, source_store_id: str,
                index_store_id: str | None = None,
                *, bulk: bool = True,
                ) -> tuple[IndexCursorV1, WildcardIndex, RuleSet]:
    """Build a fresh graph index from a tuple store's current snapshot.

    One transaction (committed on success, rolled back on failure). Refuses to run
    on an index that already has state -- a fresh build wants a fresh store; use
    ``advance_index`` to catch an existing index up instead.

    ``bulk`` (default True, P13) constructs the final pre-backfill state directly via
    ``index_v4.bulk_build`` -- one in-memory pass + bulk INSERTs -- instead of replaying
    every routed triple through the incremental ``widx.add_tuple``. ``bulk=False`` keeps
    that per-tuple loop; it is byte-identical in effect and is the identity gate's
    reference side (``tests/test_bulk_build.py``). Everything else (guards, backfill,
    watermark re-check, cursor) is shared by both paths.
    """
    index_store_id = index_store_id or source_store_id

    if session.new or session.dirty or session.deleted:
        raise ValueError(
            'build_index owns the transaction (commit on success, rollback on '
            'failure): call it on a clean session, not one with pending changes')

    try:
        watermark = log_watermark(session, source_store_id)
        schema_text, shapes = load_schema(session, source_store_id)
        boot_ruleset = None
        if index_store_id != source_store_id:
            # Copying the schema to a separate index store compiles it here; reuse
            # that RuleSet in open_graph_index instead of re-parsing the same text.
            _, boot_ruleset = ensure_schema(session, index_store_id, schema_text, shapes)

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

        widx, ruleset = open_graph_index(session, index_store_id, ruleset=boot_ruleset)

        if bulk:
            # P13 + R4-BF: construct the final state directly (one in-memory pass + bulk
            # INSERTs) -- including, on a boolean schema, the derived state that the
            # incremental path produces via DeltaProcessor.backfill(). Identical in effect
            # to the bulk=False reference path below, so this branch skips backfill().
            bulk_build(session, source_store_id, index_store_id, ruleset,
                       widx.schema_info)
        else:
            # Reference path: bulk-load the snapshot through the rewrite fan-out one
            # routed triple at a time (leaf writes only), then derive the boolean state
            # in one offline pass (P6 backfill precedent). This IS the identity gate's
            # reference side (tests/test_bulk_build.py), so it stays maintained.
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

            if ruleset.compiled is not None and ruleset.compiled.plans:
                DeltaProcessor(widx, ruleset.compiled).backfill()

        # Blind-audit X1: watermark and snapshot were two unserialized reads -- a
        # write committed between them would be IN the snapshot AND above the
        # watermark, so the tail stream would re-apply it (refcount 2 on a
        # ref-counted index: a later revoke retires only one -- a permanent phantom
        # grant). Re-read the watermark after the snapshot; if it moved, writes
        # were concurrent and the snapshot/watermark pair is not a consistent cut.
        if log_watermark(session, source_store_id) != watermark:
            raise RuntimeError(
                f'concurrent writes to source store {source_store_id!r} during '
                f'build_index; retry when the store is quiescent (or stop writers)')

        cursor = ensure_cursor(session, index_store_id, source_store_id)
        cursor.applied_log_id = watermark
        session.add(cursor)
        session.commit()
        return cursor, widx, ruleset
    except Exception:
        session.rollback()
        raise
