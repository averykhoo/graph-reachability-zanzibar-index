"""The apply step: tuple-log rows -> graph index.

``advance_index`` is the ONLY moving part of index maintenance. The sync schedule
inlines it into the write transaction (cursor pinned at the log head); the async
schedule loops it in a worker. Same machinery, two schedules.

Exactly-once comes from transactionality, not bookkeeping: the caller
commits applied rows and the cursor advance together; a failed batch moves nothing
and a retry re-reads the same rows.

Validity was enforced at admission, so the log contains only appliable
ops -- a rejection here is a HARD failure (corruption signal), mirroring the delta
processor's cycle guard. **One documented exception:** ``IndexResourceLimit``
(``ClosureFanoutExceeded``, ``PathCountExceeded``) is a resource limit the index applies
and admission cannot predict, so it escapes that promotion and propagates as itself
(see ``_apply_row``).
"""
# Provenance (moved out of the docstring, TK123 item 14): connected-store spec §4.
# Provenance (moved out of the docstring, TK123 item 14): spec §2.6; spec §2.4.

from __future__ import annotations

from typing import cast

from sqlmodel import Session, select

from zanzibar.graphindex import WildcardIndex
from zanzibar.graphindex.invariants import InvariantViolation
from zanzibar.graphindex.outbox import outbox_watermark
from zanzibar.graphindex.processor import DeltaProcessor
from zanzibar.schema.errors import ZanzibarError
from zanzibar.schema import (Entity, IndexResourceLimit, RelationalTriple,
                               RuleSet, norm_pred as _norm)

from .models import IndexCursor, TupleLog
from .source import WatermarkGap, log_gap, log_rows


def ensure_cursor(session: Session, index_store_id: str,
                  source_store_id: str) -> IndexCursor:
    """Fetch-or-create the index's cursor row ("reflects the source through N")."""
    row = session.exec(
        select(IndexCursor).where(IndexCursor.index_store_id == index_store_id)
    ).first()
    if row is None:
        row = IndexCursor(index_store_id=index_store_id,
                            source_store_id=source_store_id, applied_log_id=0)
        session.add(row)
        session.flush()
    elif row.source_store_id != source_store_id:
        raise ValueError(
            f"index {index_store_id!r} already materializes source "
            f"{row.source_store_id!r}, not {source_store_id!r}")
    return row


def render_log_row(row: TupleLog) -> str:
    """One log row in the OpenFGA string form, for messages: ``ADD user:alice viewer
    doc:d1`` (a userset subject as ``group:eng#member``)."""
    user = f'{row.subject_type}:{row.subject_name}'
    if row.subject_predicate != '...':
        user += f'#{row.subject_predicate}'
    return f'{row.op} {user} {row.relation} {row.object_type}:{row.object_name}'


def _attach_failing_row(exc: BaseException, row: TupleLog) -> None:
    """Record on ``exc`` which log row the apply step failed on: the attribute
    ``failing_log_row`` = ``(log id, rendered row)`` and a note in the traceback. The
    innermost attachment wins (a re-raise through an outer loop keeps it)."""
    # TK123 item 13: a stalled index used to report only the resource limit, with no
    # way to find the row to remove at the source.
    if getattr(exc, 'failing_log_row', None) is None:
        exc.failing_log_row = (row.id, render_log_row(row))  # type: ignore[attr-defined]  # deliberate dynamic attribute, read back via getattr
        exc.add_note(f'zanzibar: the index apply step failed on log row {row.id}: '
                     f'{render_log_row(row)}')


def _apply_row(row: TupleLog, widx: WildcardIndex, ruleset: RuleSet) -> None:
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
    except IndexResourceLimit:
        # NOT corruption, and the one refusal FAMILY that must escape the promotion
        # below: `ClosureFanoutExceeded` (ZT-P1-6a) and `PathCountExceeded` (TK111).
        # `TupleSource` admission has no knowledge of `max_closure_fanout`, so it
        # provably could NOT have refused this row at write time -- the row is validly
        # logged and the INDEX is declining to materialise it. Promoting it would
        # report a resource limit as "corruption or a validity-parity bug", which is
        # exactly what `src/zanzibar/graphindex/core.py`'s raise site says it must not be. Re-raised
        # unchanged so the caller sees the cap's own actionable message; note the
        # consequence, which is real: the cursor cannot advance past this row until
        # the cap is raised (or disabled with 0). See ZT-P1-6a. On the async schedule
        # `Store.catch_up` records the stall, and the read path then stops
        # serving the index (TK111/TK112), so the consequence is an availability loss
        # rather than a stale ALLOW.
        raise
    except ValueError as e:
        raise InvariantViolation(
            f'log row {row.id} ({render_log_row(row)}) was rejected by the index -- the log is '
            f'admission-validated, so this is corruption or a validity-parity bug: {e}'
        ) from e


class MissingDeltaProcessor(ZanzibarError, ValueError):
    """``advance_index`` was called with ``proc=None`` on a schema with boolean
    (``and`` / ``but not``) relations.

    The apply step writes only the leaf families; the derived families are maintained by
    the ``DeltaProcessor``'s cascade. Without it the index silently disagrees with the set
    engine (an equivalence failure, measured: a granted user read ``False`` from the index
    and ``True`` from the source), so this is refused instead. A ``ValueError`` subclass,
    as a bad argument is."""
    # Provenance (moved out of the docstring, TK123 item 14): TK123 A16.


def _require_proc_for_boolean_schema(ruleset: RuleSet, proc: DeltaProcessor | None) -> None:
    """Refuse ``proc=None`` when ``ruleset`` compiled boolean plans (TK123 A16)."""
    compiled = ruleset.compiled
    if proc is None and compiled is not None and compiled.plans:
        raise MissingDeltaProcessor(
            'advance_index(..., proc=None) on a schema with boolean (and / but not) '
            'relations would build a graph index that disagrees with the set engine: '
            'the derived relations are only maintained by the delta processor. Pass '
            'DeltaProcessor(widx, ruleset.compiled) as proc (from zanzibar.graphindex '
            'import DeltaProcessor), or drive the index through Store (refresh() / '
            'catch_up()), which does.')


def advance_index(session: Session, cursor: IndexCursor, widx: WildcardIndex,
                  ruleset: RuleSet, proc: DeltaProcessor | None, *,
                  batch: int | None = None,
                  rows_hint: list[TupleLog] | None = None) -> int:
    """Apply log rows past the cursor to the index; advance the cursor; return the
    number of rows applied. The CALLER commits -- applied rows + cursor advance land
    in one transaction (exactly-once).

    ``batch`` caps how many ``TupleLog`` rows are consumed per call (``None`` =
    drain to the log head). Splitting a caller's logical write burst across several
    batches is semantically safe because the log is a strict causal order:
    ``TupleLog.id`` is a monotonically increasing primary key, so ``log_rows``
    returns a contiguous, strictly ordered slice starting just past the cursor, and
    each batch applies an exact PREFIX of that order. Every intermediate index state
    is therefore a valid causal partial-progress point -- it reflects the source
    through some earlier log id, never a gap or reordering. The cursor
    (``applied_log_id``) advances monotonically to ``rows[-1].id`` each batch, so
    freshness tokens/watermarks only ever move forward; a reader comparing its token
    against the cursor sees a truthful "reflects the source through N", whatever the
    batch size. Batch size thus affects only latency/granularity, not the final
    materialized state or any semantic guarantee.

    That whole argument rests on ``rows`` being a contiguous prefix of the LOG, not just
    of what this snapshot can see, so the advance is contiguity-CHECKED: a committed row hidden by a pinned read snapshot would otherwise be
    jumped over and never applied again, with ``_fresh_enough`` certifying the stale
    answers that follow. A detected gap raises ``WatermarkGap`` and the batch commits
    nothing.

    ``rows_hint`` is the sync fast path: the just-flushed ``TupleLog``
    rows this transaction appended, handed straight through so the re-SELECT of the rows
    this transaction wrote is skipped. It is USED only when it is provably equal to
    what ``log_rows`` would return -- non-empty, its first id is exactly one past the
    (post-refresh) cursor, and its ids are strictly contiguous ascending -- so the
    contract above stays literally true: same contiguous prefix, same monotone cursor
    advance, same exactly-once shape. Any mismatch (empty hint, or a store reopened
    ``sync=True`` with leftover async-era lag between the cursor and the hint) falls
    back to ``log_rows`` exactly as today.

    ``proc`` is REQUIRED when the schema has boolean (``and`` / ``but not``) relations,
    i.e. when ``ruleset.compiled.plans`` is non-empty, and is refused with
    ``MissingDeltaProcessor`` before anything is read or written otherwise.
    Without the cascade the derived families are never maintained, so the index would
    silently answer differently from the set engine. ``None`` is only for pure-union
    schemas, which never cascade."""
    # Provenance (moved out of the docstring, TK123 item 14): connected-store spec sec 2.6.
    # Provenance (moved out of the docstring, TK123 item 14): perf P12b.
    # Provenance (moved out of the docstring, TK123 item 14): spec §4; ZT-P1-5, 2026-07-26;
    # TK123 A16.
    _require_proc_for_boolean_schema(ruleset, proc)
    # Serialize concurrent appliers on the index store BEFORE reading the cursor:
    # two workers reading the same cursor value would double-apply log rows (a
    # lost-update on ref-counted state). A real ``SELECT ... FOR UPDATE`` on the
    # supported server (PostgreSQL -- verified row-granular and genuinely blocking in
    # tests/test_postgres_ha.py); on SQLite the database write lock + the caller's
    # retry-on-busy provide the same serialization (the cursor is re-read fresh on
    # retry).
    widx.idx._lock_store()
    session.refresh(cursor)

    # cast: persisted TupleLog rows always carry their primary key
    if rows_hint and cursor.applied_log_id == cast(int, rows_hint[0].id) - 1 and all(
            rows_hint[i].id == cast(int, rows_hint[i - 1].id) + 1
            for i in range(1, len(rows_hint))):
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
            try:
                _apply_row(row, widx, ruleset)
            except Exception as e:
                _attach_failing_row(e, row)    # TK123 item 13
                raise
        if proc is not None:
            proc.run_cascade(cast(int, wm))     # wm is set whenever proc is
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
    head = cast(int, rows[-1].id)        # a persisted row always carries its id
    gap = log_gap(session, cursor.source_store_id, cursor.applied_log_id, head,
                  [r.id for r in rows])
    if gap is not None:
        raise WatermarkGap(
            f'index cursor {cursor.applied_log_id} -> {head} would skip committed log '
            f'row {gap} of source store {cursor.source_store_id!r}: this session\'s '
            f'read snapshot predates it, so the apply step could not see it. Roll back '
            f'to start a fresh snapshot and retry the batch (nothing was committed).')
    cursor.applied_log_id = head
    # TK111: a successful advance ends any recorded stall. Redundant with the
    # ``stalled_after == applied_log_id`` liveness rule, kept so the row reads honestly.
    cursor.stalled_after = None
    cursor.stall_error = None
    session.add(cursor)
    session.flush()
    return len(rows)
