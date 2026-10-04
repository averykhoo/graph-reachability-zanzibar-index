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

``rebuild_index`` is the same build run IN PLACE over an index that already exists:
the recovery for an async index stalled behind a log row it can never apply (TK121,
``docs/tk121-stall-recovery-2026-10-04.md``).
"""

from __future__ import annotations

from sqlalchemy import delete
from sqlmodel import Session, select

from index_v4 import EdgeV4, NodeV4, WildcardIndex
from index_v4.bulk_build import bulk_build
from index_v4.models import ResidueRefV1, ResidueV1
from index_v4.processor import DeltaProcessor
from setengine.models import TupleV1
from zanzibar_utils_v1 import Entity, RelationalTriple, RuleSet

from .apply import ensure_cursor, _norm
from .models import IndexCursorV1
from .schema_io import ensure_schema, load_schema, open_graph_index
from .source import log_watermark


class BuildReport(tuple):
    """``build_index``'s return: the historical ``(cursor, widx, ruleset)``
    3-tuple, plus ``.constructor`` naming WHICH branch actually ran --
    ``'bulk'`` (``index_v4.bulk_build``) or ``'incremental'`` (the per-tuple
    ``widx.add_tuple`` replay + ``DeltaProcessor.backfill()``).

    A plain ``tuple`` subclass, so every existing
    ``cursor, widx, ruleset = build_index(...)`` call site is untouched.

    WHY THIS FIELD EXISTS. The two constructors are byte-identical in effect by
    design (P13's correctness bar), so no assertion about the resulting STATE --
    anywhere, in any test -- can tell them apart. A flipped default, or a silent
    fallback added here, would downgrade every "bulk" test in the repo to a
    second run of the incremental path with nothing going red. Measured
    2026-09-20 (`docs/tk91-tk80-removal-coverage-2026-09-20.md`): forcing
    ``if bulk:`` to ``if False:`` left
    ``formal/conformance/test_conformance_remove.py::test_graph_remove_bulk_build_survivors``
    at ``26 passed, 104 deselected`` rc=0 while ``bulk_build`` ran 0 times
    instead of 130. This is the repo's house failure mode -- an assurance step
    that fails by PASSING -- and ``docs/sabotage-procedure.md`` prefers a
    mechanical refusal over a doc warning, so callers that need the bulk path
    refuse on this field (``formal/conformance/backends.py::bulk_build_drive``).

    The label is assigned INSIDE each branch, AFTER that branch's constructor
    returns, and ``build_index`` gives it no default: deleting an assignment is
    an ``UnboundLocalError``, not a wrong label.
    """

    def __new__(cls, cursor: IndexCursorV1, widx: WildcardIndex,
                ruleset: RuleSet, constructor: str) -> 'BuildReport':
        if constructor not in ('bulk', 'incremental'):
            raise ValueError(f'unknown build_index constructor {constructor!r}')
        self = super().__new__(cls, (cursor, widx, ruleset))
        self.constructor = constructor
        return self


def build_index(session: Session, source_store_id: str,
                index_store_id: str | None = None,
                *, bulk: bool = True,
                ) -> BuildReport:
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

    Returns a `BuildReport`: the ``(cursor, widx, ruleset)`` tuple it has always
    returned, plus ``.constructor`` naming which of the two branches ran -- the
    only thing that distinguishes them, since their state is identical by design.
    """
    index_store_id = index_store_id or source_store_id

    _require_clean_session(session, 'build_index')

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
                f"{existing_cursor.applied_log_id}); build_index is for fresh builds "
                f"(rebuild_index replaces an existing index in place)")
        has_nodes = session.exec(
            select(NodeV4).where(NodeV4.store_id == index_store_id).limit(1)
        ).first()
        if has_nodes is not None:
            raise ValueError(
                f"index store {index_store_id!r} already holds graph state; "
                f"build_index is for fresh builds")

        widx, ruleset = open_graph_index(session, index_store_id, ruleset=boot_ruleset)
        constructor = _materialise(session, source_store_id, index_store_id, widx,
                                   ruleset, bulk=bulk)
        _require_quiescent(session, source_store_id, watermark, 'build_index')

        cursor = ensure_cursor(session, index_store_id, source_store_id)
        cursor.applied_log_id = watermark
        session.add(cursor)
        session.commit()
        return BuildReport(cursor, widx, ruleset, constructor)
    except Exception:
        session.rollback()
        raise


def rebuild_index(session: Session, source_store_id: str,
                  index_store_id: str | None = None,
                  *, bulk: bool = True,
                  ) -> BuildReport:
    """Throw away an EXISTING index's graph state and build it again, in place, from
    the source's current snapshot (TK121). The recovery for an index the async apply
    step cannot advance: a logged row the index refuses forever (``PathCountExceeded``
    -- a storage-width bound, never suspended) stalls ``catch_up`` in front of every
    later row, including the REMOVE that would undo it, so catch-up alone never gets
    past it. Procedure and decision: ``docs/tk121-stall-recovery-2026-10-04.md``.

    In place because a ``ConnectedStore`` always reads the index stored under its own
    store id; a separately-built index is one nothing in the composed system can serve.

    The source must already be representable: remove the offending tuple at the source
    FIRST (``ConnectedStore.remove_tuple`` works while stalled -- it only appends to the
    log). A snapshot that still overflows is refused by the build exactly as
    ``build_index`` refuses it.

    One transaction, under the graph store lock: delete this index store's
    ``EdgeV4`` / ``ResidueRefV1`` / ``ResidueV1`` / ``NodeV4`` rows, run the same build as
    ``build_index``, then move the EXISTING cursor row to the watermark and clear its stall
    marker. The cursor row is reused, not recreated, so other instances that hold it see
    the rebuild after their next ``refresh()``. ``DeltaOutboxV1`` is left alone: its ids
    are a consumer cursor domain (see ``index_v4.outbox.prune_outbox`` for why emptying it
    is unsafe on SQLite), the old rows are drained, and the build appends above them.

    **On ANY failure nothing changes**: the old index and its stall marker survive, so a
    rebuild that cannot succeed (the snapshot still overflows, a concurrent writer moved
    the watermark) leaves reads exactly as correct as before it ran -- untokened
    ``check`` still falls back to the set engine and lookups still refuse.

    Stop the store's async worker first: a write committed during the rebuild makes it
    refuse with "concurrent writes", as ``build_index`` does.
    """
    index_store_id = index_store_id or source_store_id
    _require_clean_session(session, 'rebuild_index')

    try:
        cursor = session.exec(
            select(IndexCursorV1)
            .where(IndexCursorV1.index_store_id == index_store_id)
        ).first()
        if cursor is None:
            raise ValueError(
                f"index {index_store_id!r} does not exist (no cursor); rebuild_index "
                f"replaces an existing index -- use build_index for a fresh one")
        if cursor.source_store_id != source_store_id:
            raise ValueError(
                f"index {index_store_id!r} materializes source "
                f"{cursor.source_store_id!r}, not {source_store_id!r}")

        widx, ruleset = open_graph_index(session, index_store_id)
        # The same store lock every applier takes first (``advance_index``): a
        # concurrent catch_up cannot interleave with the delete-and-rebuild.
        widx.idx._lock_store()
        session.refresh(cursor)
        watermark = log_watermark(session, source_store_id)

        # FK order: edges and residues reference node rows. A residue left behind
        # would name a node id the rebuild may hand to a DIFFERENT node -- the ZT-P0-1
        # escalation class -- which is why this is not a hand procedure.
        for model in (EdgeV4, ResidueRefV1, ResidueV1, NodeV4):
            session.execute(delete(model).where(model.store_id == index_store_id))
        session.flush()

        constructor = _materialise(session, source_store_id, index_store_id, widx,
                                   ruleset, bulk=bulk)
        _require_quiescent(session, source_store_id, watermark, 'rebuild_index')

        cursor.applied_log_id = watermark
        cursor.stalled_after = None
        cursor.stall_error = None
        session.add(cursor)
        session.commit()
        return BuildReport(cursor, widx, ruleset, constructor)
    except Exception:
        session.rollback()
        raise


def _require_clean_session(session: Session, surface: str) -> None:
    if session.new or session.dirty or session.deleted:
        raise ValueError(
            f'{surface} owns the transaction (commit on success, rollback on '
            f'failure): call it on a clean session, not one with pending changes')


def _materialise(session: Session, source_store_id: str, index_store_id: str,
                 widx: WildcardIndex, ruleset: RuleSet, *, bulk: bool) -> str:
    """Load the source snapshot into an EMPTY index store; return which constructor
    ran (``BuildReport.constructor``). Shared by ``build_index`` and ``rebuild_index``
    so the two cannot drift on what they admit."""
    if bulk:
        # P13 + R4-BF: construct the final state directly (one in-memory pass + bulk
        # INSERTs) -- including, on a boolean schema, the derived state that the
        # incremental path produces via DeltaProcessor.backfill(). Identical in effect
        # to the bulk=False reference path below, so this branch skips backfill().
        bulk_build(session, source_store_id, index_store_id, ruleset,
                   widx.schema_info)
        constructor = 'bulk'
    else:
        # Reference path: bulk-load the snapshot through the rewrite fan-out one
        # routed triple at a time (leaf writes only), then derive the boolean state
        # in one offline pass (P6 backfill precedent). This IS the identity gate's
        # reference side (tests/test_bulk_build.py), so it stays maintained.
        rows = session.exec(
            select(TupleV1).where(TupleV1.store_id == source_store_id)
            .order_by(TupleV1.id)  # type: ignore[arg-type]
        ).all()
        # The fan-out cap is suspended for the whole replay (TK112, 2026-10-03b):
        # these rows are committed truth, and the bulk path above was never capped,
        # so the two constructors must not disagree on what they admit.
        with widx.idx.fanout_cap_suspended():
            for r in rows:
                sp = Ellipsis if r.subject_predicate == '...' else r.subject_predicate
                triple = RelationalTriple(Entity(r.subject_type, r.subject_name),
                                          r.relation,
                                          Entity(r.object_type, r.object_name), sp)
                for d in ruleset.apply(triple):
                    widx.add_tuple(_norm(d.subject_predicate), d.subject.type,
                                   d.subject.name, d.relation, d.object.type,
                                   d.object.name)

            if ruleset.compiled is not None and ruleset.compiled.plans:
                DeltaProcessor(widx, ruleset.compiled).backfill()
        constructor = 'incremental'
    return constructor


def _require_quiescent(session: Session, source_store_id: str, watermark: int,
                       surface: str) -> None:
    # Blind-audit X1: watermark and snapshot were two unserialized reads -- a
    # write committed between them would be IN the snapshot AND above the
    # watermark, so the tail stream would re-apply it (refcount 2 on a
    # ref-counted index: a later revoke retires only one -- a permanent phantom
    # grant). Re-read the watermark after the snapshot; if it moved, writes
    # were concurrent and the snapshot/watermark pair is not a consistent cut.
    if log_watermark(session, source_store_id) != watermark:
        raise RuntimeError(
            f'concurrent writes to source store {source_store_id!r} during '
            f'{surface}; retry when the store is quiescent (or stop writers)')
