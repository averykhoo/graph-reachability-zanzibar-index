"""
Outbox helpers (boolean spec §4/§5.1): watermark + keyset drains over DeltaOutboxV1.

The write paths never materialise ``list[PermissionDelta]`` (spec decision 7); tests
and back-compat consumers drain a cursor range to a list with ``drain_deltas``.
"""

from sqlmodel import Session, select

from .models import DeltaOutboxV1, PermissionDelta


def outbox_watermark(session: Session, store_id: str) -> int:
    """Highest outbox id for the store (0 if empty) -- the keyset cursor."""
    rows = session.exec(
        select(DeltaOutboxV1.id)
        .where(DeltaOutboxV1.store_id == store_id)
        .order_by(DeltaOutboxV1.id.desc())  # type: ignore[union-attr]
        .limit(1)
    ).first()
    return rows or 0


def outbox_rows(session: Session, store_id: str, after_id: int = 0) -> list[DeltaOutboxV1]:
    """All outbox rows with id > after_id, in cursor order."""
    return list(session.exec(
        select(DeltaOutboxV1)
        .where(DeltaOutboxV1.store_id == store_id)
        .where(DeltaOutboxV1.id > after_id)
        .order_by(DeltaOutboxV1.id)  # type: ignore[arg-type]
    ).all())


def drain_deltas(session: Session, store_id: str, after_id: int = 0) -> list[PermissionDelta]:
    """Thin back-compat helper: a cursor range rendered as the legacy delta list."""
    return [
        PermissionDelta(store_id=r.store_id, subject_id=r.subject_node_id,
                        object_id=r.object_node_id, action=r.action)
        for r in outbox_rows(session, store_id, after_id)
    ]
