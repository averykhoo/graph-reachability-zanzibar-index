"""The source-of-truth write path (connected-store spec §2.3/§2.4/§4).

``TupleSource`` owns a tuple store: every write is validated up front (charset,
type restrictions, wildcard shapes, and -- for index-compilable schemas -- the graph
backend's cycle parity via the set engine's flow graph), then lands the ``TupleV1``
mutation and the ``TupleLogV1`` append in the SAME transaction. Rejected writes
leave no row anywhere; a rolled-back transaction discards tuple and log together.

Validity at admission (spec §2.4) is what keeps the log replayable: it contains only
index-appliable ops, so a rejection during index apply is a corruption signal, never
an op rejection.

Write ops return the log id -- the freshness token (spec §2.5): an index whose
cursor is >= the token reflects this write. Duplicate adds are idempotent no-ops
(raw tuples are a SET) and return the current watermark, which trivially satisfies
the token contract.

Tokens are STORE-LOCAL (blind-audit X6): the token domain is this store's own
``TupleLogV1`` id sequence, so a token minted against one store means nothing to
another (log ids are per-database autoincrements, not a global clock). Comparing or
carrying tokens across stores is a category error; multi-store consistency needs an
external ordering.
"""

from __future__ import annotations

from sqlmodel import Session, select

from setengine import SetEngine
from setengine.setops import SetOps, DEFAULT_SETOPS

from .models import TupleLogV1
from .schema_io import open_set_engine


def log_watermark(session: Session, store_id: str) -> int:
    """Highest log id for the store (0 if empty) -- the cursor/token domain."""
    row = session.exec(
        select(TupleLogV1.id)
        .where(TupleLogV1.store_id == store_id)
        .order_by(TupleLogV1.id.desc())  # type: ignore[union-attr]
        .limit(1)
    ).first()
    return row or 0


def log_rows(session: Session, store_id: str, after_id: int = 0,
             limit: int | None = None) -> list[TupleLogV1]:
    """Log rows with id > after_id, in cursor order (optionally capped for batching)."""
    stmt = (select(TupleLogV1)
            .where(TupleLogV1.store_id == store_id)
            .where(TupleLogV1.id > after_id)
            .order_by(TupleLogV1.id))  # type: ignore[arg-type]
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.exec(stmt).all())


class TupleSource:
    """Source-of-truth writes for one tuple store (the Zanzibar half)."""

    def __init__(self, session: Session, store_id: str, *, ops: SetOps = DEFAULT_SETOPS,
                 ruleset=None):
        self.session = session
        self.store_id = store_id
        # the set engine is the online evaluator AND the admission validator
        # (restrictions + wildcard gating + cycle parity with the graph backend).
        # Its state is IN-MEMORY, rebuilt from TupleV1: it is only as fresh as its
        # last rebuild plus this instance's own writes. evaluator_watermark tracks
        # exactly that ("the evaluator reflects the log through here"), so freshness-
        # token fallbacks can rebuild on demand instead of trusting a stale cache.
        # ``ruleset`` skips recompiling a schema the caller already compiled.
        self.evaluator_watermark = log_watermark(session, store_id)
        self.engine: SetEngine = open_set_engine(session, store_id, ops=ops,
                                                 ruleset=ruleset)
        # The row flushed by the most recent ``_append``, until ``pop_pending_rows``
        # drains it (perf P12b). Under the sync schedule the caller drains this
        # immediately after each write and hands it to ``advance_index`` as a
        # log-read hint, so it never spans a transaction boundary. The duplicate-add
        # path appends nothing (natural empty hint). A single slot, not a list: one
        # write appends exactly one row, and overwriting keeps the buffer bounded
        # even for a direct ``TupleSource`` user that never pops.
        self._pending_row: TupleLogV1 | None = None

    # ------------------------------------------------------------------ #
    # Writes (validate -> TupleV1 -> log append; one transaction)
    # ------------------------------------------------------------------ #

    def add(self, subject_predicate, s_type: str, s_name: str,
            relation: str, o_type: str, o_name: str) -> int:
        """Add a raw tuple; returns the freshness token (log id).

        Idempotent on duplicates (raw tuples are a set): no state change, no log
        row, current watermark returned."""
        s_pred = '...' if subject_predicate is Ellipsis else subject_predicate
        if not self.engine.add_tuple(s_pred, s_type, s_name, relation, o_type, o_name):
            # duplicate: idempotent no-op, no log row; the current watermark
            # trivially satisfies the token contract
            return log_watermark(self.session, self.store_id)
        token = self._append('ADD', s_pred, s_type, s_name, relation, o_type, o_name)
        self.evaluator_watermark = max(self.evaluator_watermark, token)
        return token

    def remove(self, subject_predicate, s_type: str, s_name: str,
               relation: str, o_type: str, o_name: str) -> int:
        """Remove a raw tuple; returns the freshness token (log id). Raises
        ``ValueError`` (and logs nothing) if the tuple is not present."""
        s_pred = '...' if subject_predicate is Ellipsis else subject_predicate
        self.engine.remove_tuple(s_pred, s_type, s_name, relation, o_type, o_name)
        token = self._append('REMOVE', s_pred, s_type, s_name, relation, o_type, o_name)
        self.evaluator_watermark = max(self.evaluator_watermark, token)
        return token

    def _append(self, op: str, s_pred: str, s_type: str, s_name: str,
                relation: str, o_type: str, o_name: str) -> int:
        row = TupleLogV1(store_id=self.store_id, op=op,
                         subject_predicate=s_pred, subject_type=s_type,
                         subject_name=s_name, relation=relation,
                         object_type=o_type, object_name=o_name)
        self.session.add(row)
        self.session.flush()            # autoincrement id now; still uncommitted
        assert row.id is not None
        # Stash the flushed row for the sync fast path (perf P12b): the caller drains
        # it via ``pop_pending_rows`` before the transaction ends.
        self._pending_row = row
        return row.id

    def pop_pending_rows(self) -> list[TupleLogV1]:
        """Return the row(s) flushed since the last pop and reset the buffer (perf P12b).

        The sync write path drains this right after a successful append to hand
        ``advance_index`` the exact rows it would otherwise re-SELECT; the rollback/except
        paths drain-and-discard it so no row ever survives into a later transaction."""
        row, self._pending_row = self._pending_row, None
        return [] if row is None else [row]

    # ------------------------------------------------------------------ #
    # Reads (the always-fresh online evaluator)
    # ------------------------------------------------------------------ #

    def check(self, *q) -> bool:
        return self.engine.check(*q)

    def refresh_evaluator(self) -> None:
        """Rebuild the in-memory evaluator from the current TupleV1 snapshot and
        RESET the evaluator watermark to it. The watermark is read BEFORE the rebuild
        (conservative: rows committed in between are included in the rebuild but not
        claimed). Assignment, not max: after a rollback the old watermark may claim
        a token that never committed."""
        wm = log_watermark(self.session, self.store_id)
        self.engine.rebuild()
        self.evaluator_watermark = wm

    def watermark(self) -> int:
        return log_watermark(self.session, self.store_id)
