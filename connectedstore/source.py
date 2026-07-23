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

Multi-instance discipline: several ``TupleSource`` instances may write the same
store, but each instance's evaluator is instance-LOCAL in-memory state -- so every
write runs a per-store critical section: ``_lock_source`` (a ``FOR UPDATE`` lock on
the store's ``SchemaV4`` row) then ``catch_up_evaluator`` (tail the committed log
into the evaluator). Under the lock no new commit can appear, so admission
(duplicate detection, remove-existence, cycle parity) validates against the CURRENT
store state, not a stale local cache; and because the log append now happens inside
the critical section, log ids commit in id order per store -- ``id > watermark``
tailing (this evaluator's tailer and ``advance_index``'s cursor alike) can never
skip a row. A single-writer deployment degrades to one no-op-rendered lock plus one
empty indexed SELECT per write.
"""

from __future__ import annotations

from sqlmodel import Session, select

from setengine import SetEngine
from setengine.setops import SetOps, DEFAULT_SETOPS

from .models import SchemaV4, TupleLogV1
from .schema_io import open_set_engine


class StaleRead(RuntimeError):
    """A read carrying an ``at_least`` token could not be satisfied: the index lags
    the token AND the write is not visible in this session's read snapshot. Start a
    fresh snapshot (``refresh()``) and retry."""


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
        # last catch-up/rebuild plus this instance's own writes. evaluator_watermark
        # tracks exactly that ("the evaluator reflects the log through here"), so
        # freshness-token fallbacks can catch up O(delta) on demand
        # (``catch_up_evaluator``) instead of trusting a stale cache.
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
        # Transaction-scoped lock memo (mirrors ReachabilityIndex._lock_store, P12a):
        # the SessionTransaction under which _lock_source last took the SchemaV4 row
        # lock. Object identity, not a boolean, so the memo can never match into a
        # retried transaction.
        self._locked_txn = None

    # ------------------------------------------------------------------ #
    # Writes (lock -> catch up -> validate -> TupleV1 -> log append; one txn)
    # ------------------------------------------------------------------ #

    def _lock_source(self) -> None:
        """Serialize concurrent writer instances on this store for the rest of the
        transaction.

        A write is a check-then-act against the evaluator (duplicate detection,
        remove-existence, cycle parity), and the evaluator is instance-local memory
        -- both are only sound if no other instance can commit between the catch-up
        and this write's commit. We take a row-level ``FOR UPDATE`` lock on the
        store's ``SchemaV4`` row (every ``TupleSource`` store has one: construction
        requires a persisted schema via ``load_schema``) -- one row per store, so
        serialization is at store granularity and deadlock-free.

        LOCK ORDERING invariant: writers take this source lock (the ``SchemaV4``
        row) BEFORE the graph store lock (the ``StoreV4`` row, taken later inside
        ``advance_index`` via ``ReachabilityIndex._lock_store``). One global order
        across both locks -- deadlock-free.

        On PostgreSQL/MySQL this blocks other writer instances until this
        transaction commits/rolls back. On SQLite ``with_for_update()`` renders to
        nothing (the engine already takes a database-level write lock), so tests
        are unaffected. Transaction-scoped memo (mirrors
        ``ReachabilityIndex._lock_store``, perf P12a): the lock is held for the
        whole transaction, so re-locking within one transaction short-circuits;
        keying the memo on ``Session.get_transaction()`` object identity means it
        can never match into a retried transaction -- a retry re-takes the real
        lock."""
        txn = self.session.get_transaction()
        if txn is not None and txn is self._locked_txn:
            return
        self.session.exec(
            select(SchemaV4).where(SchemaV4.store_id == self.store_id).with_for_update()
        ).first()
        # Capture AFTER the select: the lock SELECT itself may have autobegun the
        # transaction, so ``get_transaction()`` was potentially None above.
        self._locked_txn = self.session.get_transaction()

    def add(self, subject_predicate, s_type: str, s_name: str,
            relation: str, o_type: str, o_name: str) -> int:
        """Add a raw tuple; returns the freshness token (log id).

        Idempotent on duplicates (raw tuples are a set): no state change, no log
        row, current watermark returned."""
        # The multi-instance critical section: lock, then catch the evaluator up to
        # the committed head (under the lock no new commit can appear), so admission
        # below validates against CURRENT store state and the log append lands
        # inside the critical section (log ids commit in id order per store).
        # Catch-up never re-applies this session's own flushed-but-uncommitted
        # rows: their ids are already <= evaluator_watermark (advanced via
        # max(token) below). Rows it DOES apply were committed by other writers, so
        # a later rollback of this transaction leaves the evaluator truthful.
        self._lock_source()
        self.catch_up_evaluator()
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
        # Same multi-instance critical section as ``add`` (see there).
        self._lock_source()
        self.catch_up_evaluator()
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

    def check(self, *q, at_least: int | None = None) -> bool:
        """Evaluate a check against the online evaluator; ``at_least`` demands the
        evaluator reflect the log through that token first (catch up O(delta) on
        demand; ``StaleRead`` if the token is not visible in this session's
        snapshot -- rollback/refresh and retry)."""
        if at_least is not None and self.evaluator_watermark < at_least:
            self.catch_up_evaluator()
            if self.evaluator_watermark < at_least:
                raise StaleRead(
                    f'token {at_least} is not visible in this session snapshot '
                    f'(evaluator at {self.evaluator_watermark}); rollback to start '
                    f'a fresh read transaction, refresh the evaluator, and retry')
        return self.engine.check(*q)

    def catch_up_evaluator(self, batch: int | None = None) -> int:
        """Tail committed log rows past the evaluator watermark into the in-memory
        evaluator (``SetEngine.apply_logged`` per row, watermark advanced to each
        applied row's id); loops until the log read comes back empty. Returns the
        number of rows applied. O(delta) where ``refresh_evaluator`` is O(store) --
        the incremental refresh. ``batch`` caps rows per log query (``None`` = one
        drain query).

        Visibility: the rows tailed are this SESSION's read snapshot -- a long-lived
        read session must ``rollback()`` first to advance its snapshot (blind-audit
        X2). Gap-freedom relies on the writer lock discipline (``_lock_source``):
        the log append happens inside the per-store critical section, so ids commit
        in id order per store and ``id > watermark`` tailing never skips a row.
        After a rollback of this instance's OWN uncommitted write the watermark may
        claim an id that never committed -- callers must ``refresh_evaluator()``
        after rolling back their own writes, exactly the pre-existing contract.

        ``apply_logged``'s ``RuntimeError`` propagates: a presence mismatch during
        trusted replay means the watermark is corrupt, and the loud failure is the
        point -- recovery is ``refresh_evaluator()``."""
        total = 0
        while True:
            rows = log_rows(self.session, self.store_id,
                            self.evaluator_watermark, limit=batch)
            if not rows:
                return total
            for row in rows:
                self.engine.apply_logged(
                    row.op, row.subject_predicate, row.subject_type,
                    row.subject_name, row.relation, row.object_type, row.object_name)
                assert row.id is not None
                self.evaluator_watermark = row.id
            total += len(rows)

    def evaluator_lag(self) -> int:
        """Log rows the evaluator has not yet applied (0 = fully caught up). A COUNT
        query -- never materializes rows (ids are globally monotonic across stores,
        so counting, not id-subtraction, is also what makes the number meaningful)."""
        from sqlalchemy import func
        return self.session.exec(
            select(func.count())
            .select_from(TupleLogV1)
            .where(TupleLogV1.store_id == self.store_id)
            .where(TupleLogV1.id > self.evaluator_watermark)
        ).one()

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
