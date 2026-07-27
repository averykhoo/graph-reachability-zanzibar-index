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

from sqlmodel import Session, select

from index_v4 import WildcardIndex
from index_v4.invariants import InvariantViolation
from index_v4.outbox import outbox_watermark
from index_v4.processor import DeltaProcessor
from zanzibar_utils_v1 import Entity, RelationalTriple, RuleSet, norm_pred as _norm

from .models import IndexCursorV1, TupleLogV1
from .source import WatermarkGap, log_gap, log_rows


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


def _apply_row(row: TupleLogV1, widx: WildcardIndex, ruleset: RuleSet) -> None:
    """Route one log row through the rewrite fan-out into the index."""
    sp = Ellipsis if row.subject_predicate == '...' else row.subject_predicate
    triple = RelationalTriple(Entity(row.subject_type, row.subject_name), row.relation,
                              Entity(row.object_type, row.object_name), sp)
    # Trusted graph-write fast path (perf N9): the raw tuple was charset-validated at
    # admission (spec §2.4) and ``ruleset.apply`` only rewrites the relation to a
    # compiler-generated leaf predicate ``<rel>.<idx>`` (charset-valid by construction),
    # so re-running ``validate_write_identifiers`` per derived triple is provably
    # redundant. Skip ONLY that check via the trusted entry points -- everything else
    # (derived-exclusivity assert, cycle handling) is unchanged.
    fn = widx._add_tuple_trusted if row.op == 'ADD' else widx._remove_tuple_trusted
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
                  batch: int | None = None,
                  rows_hint: list[TupleLogV1] | None = None) -> int:
    """Apply log rows past the cursor to the index; advance the cursor; return the
    number of rows applied. The CALLER commits -- applied rows + cursor advance land
    in one transaction (exactly-once, spec §2.6).

    ``batch`` caps how many ``TupleLogV1`` rows are consumed per call (``None`` =
    drain to the log head). Splitting a caller's logical write burst across several
    batches is semantically safe because the log is a strict causal order:
    ``TupleLogV1.id`` is a monotonically increasing primary key, so ``log_rows``
    returns a contiguous, strictly ordered slice starting just past the cursor, and
    each batch applies an exact PREFIX of that order. Every intermediate index state
    is therefore a valid causal partial-progress point -- it reflects the source
    through some earlier log id, never a gap or reordering (spec §4). The cursor
    (``applied_log_id``) advances monotonically to ``rows[-1].id`` each batch, so
    freshness tokens/watermarks only ever move forward; a reader comparing its token
    against the cursor sees a truthful "reflects the source through N", whatever the
    batch size. Batch size thus affects only latency/granularity, not the final
    materialized state or any semantic guarantee.

    That whole argument rests on ``rows`` being a contiguous prefix of the LOG, not just
    of what this snapshot can see, so the advance is contiguity-CHECKED (ZT-P1-5,
    2026-07-26): a committed row hidden by a pinned read snapshot would otherwise be
    jumped over and never applied again, with ``_fresh_enough`` certifying the stale
    answers that follow. A detected gap raises ``WatermarkGap`` and the batch commits
    nothing.

    ``rows_hint`` (perf P12b) is the sync fast path: the just-flushed ``TupleLogV1``
    rows this transaction appended, handed straight through so ⑤ (re-SELECTing rows
    this transaction wrote) is skipped. It is USED only when it is provably equal to
    what ``log_rows`` would return -- non-empty, its first id is exactly one past the
    (post-refresh) cursor, and its ids are strictly contiguous ascending -- so the
    contract above stays literally true: same contiguous prefix, same monotone cursor
    advance, same exactly-once shape. Any mismatch (empty hint, or a store reopened
    ``sync=True`` with leftover async-era lag between the cursor and the hint) falls
    back to ``log_rows`` exactly as today."""
    # Serialize concurrent appliers on the index store BEFORE reading the cursor:
    # two workers reading the same cursor value would double-apply log rows (a
    # lost-update on ref-counted state). A real ``SELECT ... FOR UPDATE`` on the
    # supported server (PostgreSQL -- verified row-granular and genuinely blocking in
    # tests/test_postgres_ha.py); on SQLite the database write lock + the caller's
    # retry-on-busy provide the same serialization (the cursor is re-read fresh on
    # retry).
    widx.idx._lock_store()
    session.refresh(cursor)

    if rows_hint and cursor.applied_log_id == rows_hint[0].id - 1 and all(
            rows_hint[i].id == rows_hint[i - 1].id + 1 for i in range(1, len(rows_hint))):
        rows = rows_hint
    else:
        rows = log_rows(session, cursor.source_store_id, cursor.applied_log_id, limit=batch)
    if not rows:
        return 0
    # The cascade replays the outbox rows these applies write (id > wm), so the
    # watermark must be captured BEFORE the apply loop. Only the delta processor
    # consumes it -- pure-union stores (proc is None) never cascade, so skip the
    # SELECT entirely for them.
    wm = outbox_watermark(session, widx.idx.store_id) if proc is not None else None
    # Per-batch node-resolution cache (perf N15) spanning the apply loop AND the
    # synchronous cascade of this one batch: the same subject/object/bridge/leaf nodes
    # are re-resolved across the batch's rewrite fan-out and the cascade. The scope is
    # reentrant, so ``proc.run_cascade`` shares this outer cache instead of installing
    # its own. It is torn down before the CALLER commits, so no entry survives a
    # commit/rollback (advance_index never commits; exactly-once is the caller's, §2.6).
    with widx.idx._node_cache_scope():
        for row in rows:
            _apply_row(row, widx, ruleset)
        if proc is not None:
            proc.run_cascade(wm)
    # ZT-P1-5: advance to the CONTIGUOUS head, never blindly to ``rows[-1].id``. The
    # rows above are a contiguous prefix of what this session could SEE, which is not
    # the same as a contiguous prefix of the LOG. On a real MVCC server the two come
    # apart even at READ COMMITTED, the only level ``assert_read_isolation`` admits:
    # PostgreSQL assigns the log id at INSERT time but publishes visibility at COMMIT
    # time, so a LOWER id can land after a higher one and a read taken in between has a
    # genuine hole in it (measured -- test_postgres_ha.py::
    # test_log_gap_finds_a_row_committed_out_of_id_order). Advance blindly and that row
    # is jumped over and never applied again, while ``_fresh_enough(token)`` happily
    # certifies the resulting stale ALLOW. ``log_gap`` re-reads the interval and costs
    # nothing at all in the contiguous case, including the sync one-row fast path.
    # (It does NOT rescue a snapshot-PINNED session: under REPEATABLE READ/SERIALIZABLE
    # the re-read is served from the same blind snapshot -- which is why those levels
    # are refused at construction rather than compensated for here.)
    head = rows[-1].id
    gap = log_gap(session, cursor.source_store_id, cursor.applied_log_id, head,
                  [r.id for r in rows])
    if gap is not None:
        raise WatermarkGap(
            f'index cursor {cursor.applied_log_id} -> {head} would skip committed log '
            f'row {gap} of source store {cursor.source_store_id!r}: this session\'s '
            f'read snapshot predates it, so the apply step could not see it. Roll back '
            f'to start a fresh snapshot and retry the batch (nothing was committed).')
    cursor.applied_log_id = head
    session.add(cursor)
    session.flush()
    return len(rows)
