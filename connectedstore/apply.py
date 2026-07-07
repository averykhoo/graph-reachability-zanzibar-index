"""The apply step: tuple-log rows -> graph index (connected-store spec §4).

``advance_index`` is the ONLY moving part of index maintenance. The sync schedule
inlines it into the write transaction (cursor pinned at the log head); the async
schedule loops it in a worker. Same machinery, two schedules.

Exactly-once comes from transactionality, not bookkeeping (spec §2.6): the caller
commits applied rows and the cursor advance together; a failed batch moves nothing
and a retry re-reads the same rows.

Validity was enforced at admission (spec §2.4), so the log contains only appliable
ops -- a rejection here is a HARD failure (corruption signal), mirroring the delta
processor's cycle guard.
"""

from __future__ import annotations

from types import EllipsisType

from sqlmodel import Session, select

from index_v4 import WildcardIndex
from index_v4.invariants import InvariantViolation
from index_v4.outbox import outbox_watermark
from index_v4.processor import DeltaProcessor
from zanzibar_utils_v1 import Entity, RelationalTriple, RuleSet

from .models import IndexCursorV1, TupleLogV1
from .source import log_rows


def ensure_cursor(session: Session, index_store_id: str,
                  source_store_id: str) -> IndexCursorV1:
    """Fetch-or-create the index's cursor row ("reflects the source through N")."""
    row = session.exec(
        select(IndexCursorV1).where(IndexCursorV1.index_store_id == index_store_id)
    ).first()
    if row is None:
        row = IndexCursorV1(index_store_id=index_store_id,
                            source_store_id=source_store_id, applied_log_id=0)
        session.add(row)
        session.flush()
    elif row.source_store_id != source_store_id:
        raise ValueError(
            f"index {index_store_id!r} already materializes source "
            f"{row.source_store_id!r}, not {source_store_id!r}")
    return row


def _norm(pred: str | EllipsisType) -> str:
    return '...' if pred is Ellipsis else pred


def _apply_row(row: TupleLogV1, widx: WildcardIndex, ruleset: RuleSet) -> None:
    """Route one log row through the rewrite fan-out into the index."""
    sp = Ellipsis if row.subject_predicate == '...' else row.subject_predicate
    triple = RelationalTriple(Entity(row.subject_type, row.subject_name), row.relation,
                              Entity(row.object_type, row.object_name), sp)
    fn = widx.add_tuple if row.op == 'ADD' else widx.remove_tuple
    try:
        for d in ruleset.apply(triple):
            fn(_norm(d.subject_predicate), d.subject.type, d.subject.name,
               d.relation, d.object.type, d.object.name)
    except ValueError as e:
        raise InvariantViolation(
            f'log row {row.id} ({row.op}) was rejected by the index -- the log is '
            f'admission-validated, so this is corruption or a validity-parity bug: {e}'
        ) from e


def advance_index(session: Session, cursor: IndexCursorV1, widx: WildcardIndex,
                  ruleset: RuleSet, proc: DeltaProcessor | None, *,
                  batch: int | None = None) -> int:
    """Apply log rows past the cursor to the index; advance the cursor; return the
    number of rows applied. The CALLER commits -- applied rows + cursor advance land
    in one transaction (exactly-once, spec §2.6)."""
    # Serialize concurrent appliers on the index store BEFORE reading the cursor:
    # two workers reading the same cursor value would double-apply log rows (a
    # lost-update on ref-counted state). FOR UPDATE on PostgreSQL/MySQL; on SQLite
    # the database write lock + the caller's retry-on-busy provide the same
    # serialization (the cursor is re-read fresh on retry).
    widx.idx._lock_store()
    session.refresh(cursor)

    rows = log_rows(session, cursor.source_store_id, cursor.applied_log_id, limit=batch)
    if not rows:
        return 0
    wm = outbox_watermark(session, widx.idx.store_id)
    for row in rows:
        _apply_row(row, widx, ruleset)
    if proc is not None:
        proc.run_cascade(wm)
    cursor.applied_log_id = rows[-1].id
    session.add(cursor)
    session.flush()
    return len(rows)
