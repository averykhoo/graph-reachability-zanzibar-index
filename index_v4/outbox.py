"""
Outbox helpers (boolean spec §4/§5.1): watermark + keyset drains over DeltaOutboxV1.

The write paths never materialise ``list[PermissionDelta]`` (spec decision 7); tests
and back-compat consumers drain a cursor range to a list with ``drain_deltas``.
"""

from sqlalchemy import delete
from sqlmodel import Session, col, select

from .models import DeltaOutboxV1, PermissionDelta


def outbox_watermark(session: Session, store_id: str) -> int:
    """Highest outbox id for the store (0 if empty) -- the keyset cursor."""
    rows = session.exec(
        select(DeltaOutboxV1.id)
        .where(DeltaOutboxV1.store_id == store_id)
        .order_by(col(DeltaOutboxV1.id).desc())
        .limit(1)
    ).first()
    return rows or 0


def outbox_rows(session: Session, store_id: str, after_id: int = 0) -> list[DeltaOutboxV1]:
    """All outbox rows with id > after_id, in cursor order."""
    return list(session.exec(
        select(DeltaOutboxV1)
        .where(DeltaOutboxV1.store_id == store_id)
        .where(DeltaOutboxV1.id > after_id)
        .order_by(col(DeltaOutboxV1.id))
    ).all())


def prune_outbox(session: Session, store_id: str, before_watermark: int) -> int:
    """Delete this store's DRAINED outbox rows; return how many were removed
    (zero-trust review ZT-P1-8, retention).

    ``delta_outbox_v1`` had no ``DELETE`` anywhere: every reachability flip ever
    emitted stayed for the life of the store, even though the cascade -- its only
    in-tree consumer -- reads a row exactly once, in the transaction that wrote it.

    WHICH ROWS ARE SAFE, and why. Every consumer in this module's contract is a
    keyset cursor: it reads ``id > cursor`` (``outbox_rows`` / ``drain_deltas``) and
    then advances the cursor. ``DeltaProcessor._run_cascade`` starts from the
    watermark captured before the write, ``ParanoiaGuard`` from the last committed
    one. So a row is drained exactly when its id is ``<= cursor`` for EVERY live
    consumer, and this function deletes ``id <= before_watermark`` -- the caller
    supplies that number because only the caller knows its consumers. Pass the
    minimum cursor across them (with one synchronous cascade per write, that is
    simply ``outbox_watermark`` after the last commit). Rows ABOVE it are never
    touched: deleting an undrained row loses its delta permanently -- there is no
    other record that a pair's reachability flipped, so the derived state that flip
    would have reconciled just stays wrong.

    THE HEAD ROW IS ALWAYS KEPT, and this is not tidiness. ``id`` is the table's
    primary key, i.e. the rowid on SQLite, where the next insert gets
    ``max(rowid) + 1`` -- so emptying the table restarts ids at 1 and a consumer
    holding cursor 500 would never see the next 500 deltas. Retaining the highest row
    pins ``max(id)``, so ids stay monotone for the life of the store and
    ``outbox_watermark`` keeps returning the same value across a prune. The cost is
    one row per store; the alternative is silent, permanent delta loss on the one
    dialect CI runs.

    NOT called from any write path, deliberately: "drained" is knowledge the caller
    has and the library does not. Concurrency-wise this only writes rows at or below
    a fully-drained watermark, which no reader is looking at and no writer will
    re-emit, so it needs no store lock -- but it is a write, so run it in its own
    transaction and commit.
    """
    if before_watermark < 0:
        raise ValueError(
            f'before_watermark must be a non-negative outbox cursor, got {before_watermark}')
    head = outbox_watermark(session, store_id)
    # `head - 1`: keep the anchor. `min`: never cross the caller's drained mark.
    cutoff = min(before_watermark, head - 1)
    if cutoff <= 0:
        return 0
    result = session.execute(
        delete(DeltaOutboxV1)
        .where(DeltaOutboxV1.store_id == store_id)
        .where(DeltaOutboxV1.id <= cutoff)
        .execution_options(synchronize_session=False))
    return result.rowcount


def drain_deltas(session: Session, store_id: str, after_id: int = 0) -> list[PermissionDelta]:
    """Thin back-compat helper: a cursor range rendered as the legacy delta list."""
    return [
        PermissionDelta(store_id=r.store_id, subject_id=r.subject_node_id,
                        object_id=r.object_node_id, action=r.action)
        for r in outbox_rows(session, store_id, after_id)
    ]
