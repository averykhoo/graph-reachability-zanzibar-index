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
skip a row. A single-writer deployment degrades to one uncontended lock plus one empty
indexed SELECT per write. (On a SQLite bind that lock is a no-op UPDATE of the same row
rather than ``FOR UPDATE``, which pysqlite renders to nothing -- zero-trust review
ZT-P1-4; see ``_lock_source``.)
"""

from __future__ import annotations

from sqlalchemy import update
from sqlmodel import Session, select

from index_v4.core import is_sqlite, take_row_write_lock
from setengine import SetEngine
from setengine.setops import SetOps, DEFAULT_SETOPS

from .models import SchemaV4, TupleLogV1
from .schema_io import open_set_engine


class StaleRead(RuntimeError):
    """A read carrying an ``at_least`` token could not be satisfied: the index lags
    the token AND the write is not visible in this session's read snapshot. Start a
    fresh snapshot (``refresh()``) and retry."""


class WatermarkGap(RuntimeError):
    """A watermark/cursor advance would have SKIPPED committed log rows (zero-trust
    review ZT-P1-5) -- refused instead of proceeding.

    Both watermarks ("the evaluator reflects the log through here" and the index
    cursor's "reflects the source through N") used to advance straight to the newest
    id they had seen, ASSUMING the catch-up that preceded them was complete. Against a
    real MVCC server it need not be, in two distinct ways:

    * **Out-of-order commit, at the SUPPORTED level.** PostgreSQL assigns a log id at
      INSERT and publishes it at COMMIT, so a LOWER id can become visible after a
      higher one; a catch-up that ran in between saw a hole (reproduced in
      ``tests/test_postgres_ha.py::test_log_gap_finds_a_row_committed_out_of_id_order``).
    * **A pinned read snapshot**, under any level above READ COMMITTED: an earlier read
      in the transaction fixes the view and a concurrent commit stays invisible for good.
      That one is fenced off at construction instead (``assert_read_isolation``), because
      the contiguity check itself reads through the same blind snapshot.

    Either way the catch-up tails nothing, the watermark jumps past those rows, and they
    are never applied AGAIN, permanently. The freshness token then certifies the
    resulting stale answer, because it compares >= against the bogus watermark. So the
    advance is now contiguity-checked and this is raised on a detected gap.

    RETRYABLE, and distinct from ``StaleRead`` on purpose -- nothing is corrupt; the
    reader/writer merely acted on a stale snapshot. Roll back to start a fresh one
    (``ConnectedStore.refresh()`` / ``TupleSource.refresh_evaluator()``) and retry the
    operation; a fresh snapshot sees the missing rows and applies them normally."""


#: Optimistic attempts at a self-consistent (watermark, rebuild) pair before
#: ``_consistent_rebuild`` stops guessing and takes the shared source lock. Three,
#: because each attempt is one indexed LIMIT-1 SELECT plus a full rebuild: retrying is
#: cheap enough to be the common path and expensive enough that spinning on a hot store
#: is worse than blocking for one write. See ``_consistent_rebuild``.
SNAPSHOT_ATTEMPTS = 3


class UnsafeIsolationLevel(RuntimeError):
    """This session's bind runs at an isolation level under which a committed log row
    can stay invisible for the lifetime of a transaction, so log tailing / the cursor
    advance cannot be trusted (zero-trust review ZT-P1-5). The message names the fix."""


#: Isolation levels the log-tailing design is safe under. Exactly one.
#:
#: ``READ COMMITTED`` -- each STATEMENT sees the newest commit, so a catch-up inside a
#: long transaction really does reach the head. That per-statement freshness is the
#: whole premise of log tailing; every other level pins a snapshot somewhere.
#:
#: ``SERIALIZABLE`` WAS accepted here and was REMOVED on 2026-07-27, the first day this
#: code met a real PostgreSQL server. The justification it carried -- "PostgreSQL aborts
#: with a serialization failure rather than letting it act on a stale view, and MySQL
#: promotes every plain SELECT to a locking read" -- was half about a database this
#: project does not support, and false about the one it does. Measured: PostgreSQL SSI
#: does NOT abort on this pattern (a plain log read is not a dangerous SSI structure,
#: and ``SELECT ... FOR UPDATE`` against a row another transaction only LOCK-modified
#: raises no conflict), so a SERIALIZABLE bind reproduces the entire ZT-P1-5 scenario
#: this guard exists to prevent: a committed REMOVE stays invisible, the watermark jumps
#: past it, and ``check(..., at_least=token)`` then certifies the revoked grant as
#: ALLOWED, permanently. Reproduction:
#: ``tests/test_postgres_ha.py::test_serializable_bind_is_refused``.
#:
#: ``REPEATABLE READ`` is rejected for the same reason, one step more obviously: the
#: read view is pinned at the first read. ``READ UNCOMMITTED`` is rejected because it
#: makes admission validate against uncommitted state.
SAFE_ISOLATION_LEVELS = frozenset({'READ COMMITTED'})


def assert_read_isolation(session: Session) -> None:
    """Refuse to open against a bind whose read snapshot can hide a committed log row
    (ZT-P1-5). Dialect-aware, and deliberately silent where the question does not
    apply:

    * **SQLite** -- not applicable. There is no server-side isolation level to pin; a
      pinned WAL read snapshot cannot silently hide a row from a writer either, because
      the write fails loudly with ``SQLITE_BUSY`` instead. Checking would be a false
      alarm (pysqlite reports ``SERIALIZABLE`` regardless of configuration).
    * **A dialect that cannot report its level** -- skipped rather than guessed at."""
    if is_sqlite(session):
        return
    try:
        level = session.connection().get_isolation_level()
    except (NotImplementedError, AttributeError):        # pragma: no cover - dialect
        return
    if level is None or level.upper() in SAFE_ISOLATION_LEVELS:
        return
    raise UnsafeIsolationLevel(
        f'isolation level {level!r} is unsafe for this store: a committed tuple-log '
        f'row can stay invisible for the whole transaction, so a catch-up silently '
        f'stops short and the watermark advance would skip it permanently -- while '
        f'at_least tokens keep certifying the stale answers (zero-trust review '
        f'ZT-P1-5). Open the engine with READ COMMITTED -- '
        f'create_engine(url, isolation_level="READ COMMITTED") -- which is the only '
        f'level this design is safe under. SERIALIZABLE is NOT an alternative: on '
        f'PostgreSQL it pins a snapshot without aborting on this access pattern, and '
        f'reproduces exactly the hazard named above '
        f'(tests/test_postgres_ha.py::test_serializable_bind_is_refused).')


def log_gap(session: Session, store_id: str, after_id: int, head_id: int,
            applied_ids) -> int | None:
    """The lowest COMMITTED log id in ``(after_id, head_id]`` for the store that is not
    in ``applied_ids`` -- i.e. a row that advancing a watermark to ``head_id`` would
    skip permanently (ZT-P1-5). ``None`` when the advance is contiguous.

    Two properties make this both sound and nearly free:

    * **Free in the common case.** The half-open interval holds exactly
      ``head_id - after_id`` ids; if the caller applied that many, there is no room for
      an unapplied one and no query is issued. That is the single-store steady state
      (log ids are contiguous), including the sync write path's one-row batch.
    * **A LOCKING read** (``FOR SHARE``; shared, not exclusive -- we only need to read,
      not reserve). On SQLite it renders to a plain SELECT, which is fine: SQLite cannot
      silently hide a committed row from a writer, it fails the write loudly with
      SQLITE_BUSY instead.

    WHAT THE LOCKING READ DOES **NOT** BUY YOU (corrected 2026-07-27, measured against a
    real PostgreSQL). This comment used to argue that ``FOR SHARE`` is what makes the
    check sound, because "InnoDB serves locking reads from the LATEST committed
    version". That is an InnoDB property, and this project does not support MySQL. On
    PostgreSQL a locking read under a PINNED snapshot (REPEATABLE READ / SERIALIZABLE)
    is served from the TRANSACTION SNAPSHOT like any other read: measured, ``FOR SHARE``
    returned ``[]`` for a row committed after the snapshot, and ``log_gap`` returned
    ``None`` -- blind to exactly the row it exists to find
    (``tests/test_postgres_ha.py::test_log_gap_locking_read_surfaces_a_snapshot_hidden_row``).

    So the real guarantee is upstream: ``assert_read_isolation`` admits READ COMMITTED
    and nothing else, and under READ COMMITTED every statement -- locking or not -- sees
    the newest commit. The gap check is sound BECAUSE of that gate, not because of the
    lock hint. Weakening ``SAFE_ISOLATION_LEVELS`` therefore silently disarms this
    function too; the two must be read together."""
    if head_id - after_id == len(applied_ids):
        return None
    stmt = (select(TupleLogV1.id)
            .where(TupleLogV1.store_id == store_id)
            .where(TupleLogV1.id > after_id)
            .where(TupleLogV1.id <= head_id)
            .order_by(TupleLogV1.id)                     # type: ignore[arg-type]
            .with_for_update(read=True))
    seen = set(applied_ids)
    for row_id in session.exec(stmt).all():
        if row_id not in seen:
            return row_id
    return None


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
        # The isolation gate belongs HERE, not only in ConnectedStore (added
        # 2026-07-27). ``TupleSource`` is exported from ``connectedstore/__init__``
        # and is a complete write path -- lock, catch up, validate, append -- so a
        # caller using it directly used to get no isolation check at all, and every
        # mechanism ZT-P1-5 added (contiguous watermark advance, ``log_gap``, the
        # freshness tokens) silently ran on a pinned snapshot. The reproduced
        # SERIALIZABLE escalation ran entirely through this constructor, never
        # touching ``ConnectedStore``. Cheap and idempotent: a no-op on SQLite, and
        # ``ConnectedStore`` calling it too costs one extra dialect check.
        assert_read_isolation(session)
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
        #
        # The watermark read and the rebuild must be ATOMIC with respect to other
        # instances' commits -- see ``_consistent_rebuild``. Attempt 1 constructs the
        # engine (``SetEngine.__init__`` rebuilds); any retry re-runs ``rebuild()`` on
        # the engine we already have, which is the same replay for a fraction of the
        # setup cost (no reparse, no recompile).
        self._engine: SetEngine | None = None
        #: Attempts the last ``_consistent_rebuild`` needed (1 = uncontended;
        #: SNAPSHOT_ATTEMPTS + 1 = it had to take the lock). Observable so a test can
        #: assert the race was really constructed, and so an operator can see
        #: open-time contention rather than infer it.
        self.snapshot_attempts = 0

        def _open_or_rebuild() -> None:
            if self._engine is None:
                self._engine = open_set_engine(session, store_id, ops=ops,
                                               ruleset=ruleset)
            else:
                self._engine.rebuild()

        self.evaluator_watermark = self._consistent_rebuild(_open_or_rebuild)
        # ZT-P1-8a: from here on this engine is LOG-GOVERNED -- direct
        # ``add_tuple``/``remove_tuple`` on it are refused, because they would mutate
        # the source of truth with no ``TupleLogV1`` row and nothing downstream (index
        # cursor, replica tailers, ``at_least`` tokens, ``lag()``) would ever notice.
        # ``add``/``remove`` below go through the ``_*_direct`` bodies instead, and
        # append the log row themselves.
        self._engine.log_governed = True
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
        # retried transaction. Deliberately NOT set by ``_lock_source_shared``: a
        # FOR SHARE lock does not satisfy a later ``_lock_source``, which needs
        # FOR UPDATE.
        self._locked_txn = None

    @property
    def engine(self) -> SetEngine:
        """The online evaluator, READ-ONLY (ZT-P1-8a).

        Kept as a public attribute because reads through it are legitimate and used
        (``check``/``expand``/``lookup`` against always-fresh in-memory state), but a
        property so it cannot be swapped for a different engine behind this instance's
        watermark bookkeeping. The write half of the hazard is closed on the engine
        itself: it is marked ``log_governed``, so ``engine.add_tuple(...)`` raises
        ``UnloggedWriteRefused`` rather than silently writing ``TupleV1`` with no log
        row. Both halves are needed -- privacy alone would not have helped, since a
        rename cannot stop a caller that already holds the object."""
        assert self._engine is not None
        return self._engine

    # ------------------------------------------------------------------ #
    # Opening / refreshing: (watermark, rebuild) has to be ONE atomic pair
    # ------------------------------------------------------------------ #

    def _lock_source_shared(self) -> None:
        """Block writers on this store for the rest of the transaction WITHOUT
        becoming one -- the terminating fallback of ``_consistent_rebuild``.

        A SHARED (``FOR SHARE``) lock on the same ``SchemaV4`` row ``_lock_source``
        takes exclusively. That is exactly the mutual exclusion an OPENER needs and no
        more: writers acquire ``FOR UPDATE`` and so block on us, while other openers
        (also shared) proceed concurrently. Taking the writers' exclusive lock here
        would be wrong twice over -- a read-only replica opening an instance is not a
        writer, and it would serialize every concurrent open on a busy store behind
        one another for no benefit.

        On SQLite ``take_row_write_lock`` ignores the SELECT arm and issues the no-op
        UPDATE instead, i.e. the SQLite fallback IS exclusive. That asymmetry is
        accepted rather than papered over: SQLite has one database-level write lock and
        no shared-row concept, the fallback is only reached after
        ``SNAPSHOT_ATTEMPTS`` failures, and SQLite's single-writer model makes reaching
        it very unlikely in the first place.

        DEADLOCK NOTE: this instance may later upgrade to ``FOR UPDATE`` on its first
        write, and two instances that both fell back and then both wrote could
        deadlock on the upgrade. PostgreSQL detects that and aborts one with a
        retryable error; the alternative (take the exclusive lock up front) trades a
        rare, detected, retryable abort for guaranteed serialization of every
        contended open, which is the worse deal."""
        take_row_write_lock(
            self.session,
            select(SchemaV4).where(SchemaV4.store_id == self.store_id)
            .with_for_update(read=True),
            # SQLite arm: same no-op UPDATE ``_lock_source`` uses (the store's schema
            # row is write-once, so re-writing ``created_at`` with its own value
            # changes nothing; the point is the RESERVED lock).
            update(SchemaV4).where(SchemaV4.store_id == self.store_id)
            .values(created_at=SchemaV4.created_at),
        )

    def _consistent_rebuild(self, rebuild) -> int:
        """Rebuild the in-memory evaluator and return a watermark that is TRUE of the
        state it just built. Returns the watermark; does not assign it.

        THE WINDOW (2026-07-27, found by the PostgreSQL leg). "Read the watermark, then
        rebuild from ``TupleV1``" is two statements. Under SQLite-WAL both run in one
        pinned read snapshot, so the pair is atomic by accident. At PostgreSQL READ
        COMMITTED -- the ONLY level ``assert_read_isolation`` admits, precisely because
        every statement must re-snapshot -- a write committed BETWEEN them lands in the
        rebuild but not in the watermark. The instance is then born with its evaluator
        AHEAD of its own watermark, and the next ``catch_up_evaluator()`` replays that
        row into ``apply_logged``, whose strict-replay guard raises ``RuntimeError``
        ("log ADD of an already-present tuple ... watermark corruption") -- permanently,
        for every later write on that instance, since ``add``/``remove`` catch up first.

        WHY NOT JUST READ THE WATERMARK AFTER THE REBUILD. Because that swaps a loud
        failure for a silent one: rows committed in the gap would be counted as applied
        while the rebuild never saw them, and the ``at_least`` machinery would then
        certify stale answers off a watermark that is a lie. The ordering is not the
        bug; the non-atomicity is.

        THE FIX -- optimistic, then pessimistic. Read ``wm1``, rebuild, read ``wm2``.
        ``log_watermark`` is the store's max log id, and a commit changes it iff it
        appended a log row (a duplicate add appends nothing AND changes no tuple), so
        ``wm2 == wm1`` proves no commit landed across the rebuild and the pair is
        consistent. Otherwise retry: a retry is one more rebuild, and it starts from a
        watermark that already covers everything the previous rebuild could have seen.
        After ``SNAPSHOT_ATTEMPTS`` losses -- possible under a sustained write stream,
        which is exactly when spinning is worst -- take the shared source lock so
        writers stop, and do the pair once under it. That terminates.

        NOTE the retry can fire spuriously (a commit landing between the rebuild and
        ``wm2`` is harmless -- the rebuild simply predates it). Costing a rebuild to
        avoid distinguishing them is the right trade: false retries are cheap and the
        alternative is another window to reason about.

        Both openers use this: ``__init__`` and ``refresh_evaluator`` had the identical
        shape, and ``refresh_evaluator`` sits on ``ConnectedStore._write``'s error
        path -- so the constructor race could also be entered by any failed write."""
        for attempt in range(1, SNAPSHOT_ATTEMPTS + 1):
            wm = log_watermark(self.session, self.store_id)
            rebuild()
            self.snapshot_attempts = attempt
            if log_watermark(self.session, self.store_id) == wm:
                return wm
        self._lock_source_shared()
        wm = log_watermark(self.session, self.store_id)
        rebuild()
        self.snapshot_attempts = SNAPSHOT_ATTEMPTS + 1
        return wm

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

        On PostgreSQL this blocks other writer instances until this transaction
        commits/rolls back -- verified against a live server, including that the
        block is row-granular (a second writer on a DIFFERENT store's ``SchemaV4``
        row proceeds) and that the ordering above holds: ``tests/test_postgres_ha.py``
        ``::test_for_update_source_lock_really_blocks_a_second_writer`` and
        ``::test_lock_ordering_source_lock_is_held_before_the_store_lock``.
        On SQLite ``with_for_update()`` renders to
        NOTHING, so this lock was a silent no-op (ZT-P1-4) and two default-configured
        writers could both pass admission; ``take_row_write_lock`` now issues a no-op
        UPDATE of this same ``SchemaV4`` row on a SQLite bind, taking SQLite's RESERVED
        write lock for the rest of the transaction (and promoting the connection into a
        real transaction, so the validating SELECTs below share it with the log append).
        Transaction-scoped memo (mirrors
        ``ReachabilityIndex._lock_store``, perf P12a): the lock is held for the
        whole transaction, so re-locking within one transaction short-circuits;
        keying the memo on ``Session.get_transaction()`` object identity means it
        can never match into a retried transaction -- a retry re-takes the real
        lock.

        SAVEPOINTS (ZT-P1-7, 2026-07-26): the memo key is the ``(root, nested)``
        pair, not the root alone -- ``get_transaction()`` returns the ROOT
        ``SessionTransaction`` even inside ``begin_nested()``, so a caller that took
        this lock inside a savepoint and rolled that savepoint back (PostgreSQL
        RELEASES locks taken inside it) would otherwise match the memo on the next
        call and take no lock at all. Mirrors ``ReachabilityIndex._lock_store``."""
        txn = self.session.get_transaction()
        key = (txn, self.session.get_nested_transaction())
        if txn is not None and key == self._locked_txn:
            return
        take_row_write_lock(
            self.session,
            select(SchemaV4).where(SchemaV4.store_id == self.store_id).with_for_update(),
            # no-op UPDATE (SQLite arm): the store's schema row is write-once, so
            # re-writing ``created_at`` with its own value changes nothing; the point
            # is the RESERVED lock the statement takes. (``schema_text`` is deliberately
            # not the column touched -- no need to rewrite a large value per write.)
            update(SchemaV4).where(SchemaV4.store_id == self.store_id)
            .values(created_at=SchemaV4.created_at),
        )
        # Capture AFTER the select: the lock SELECT itself may have autobegun the
        # transaction, so ``get_transaction()`` was potentially None above. Store the
        # ``(root, nested)`` pair -- see the savepoint note in the docstring.
        self._locked_txn = (self.session.get_transaction(),
                            self.session.get_nested_transaction())

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
        # ``_add_tuple_direct``, not ``add_tuple``: this instance marked the engine
        # log-governed, so the public method now refuses (ZT-P1-8a). WE are the
        # sanctioned writer -- the ``_append`` two lines down is the log row that
        # earns the bypass, in this same transaction.
        if not self._engine._add_tuple_direct(s_pred, s_type, s_name,
                                              relation, o_type, o_name):
            # duplicate: idempotent no-op, no log row; the current watermark
            # trivially satisfies the token contract
            return log_watermark(self.session, self.store_id)
        token = self._append('ADD', s_pred, s_type, s_name, relation, o_type, o_name)
        self._advance_watermark(token)
        return token

    def remove(self, subject_predicate, s_type: str, s_name: str,
               relation: str, o_type: str, o_name: str) -> int:
        """Remove a raw tuple; returns the freshness token (log id). Raises
        ``ValueError`` (and logs nothing) if the tuple is not present."""
        # Same multi-instance critical section as ``add`` (see there).
        self._lock_source()
        self.catch_up_evaluator()
        s_pred = '...' if subject_predicate is Ellipsis else subject_predicate
        # ``_remove_tuple_direct``: see the note in ``add`` (ZT-P1-8a).
        self._engine._remove_tuple_direct(s_pred, s_type, s_name,
                                          relation, o_type, o_name)
        token = self._append('REMOVE', s_pred, s_type, s_name, relation, o_type, o_name)
        self._advance_watermark(token)
        return token

    def _advance_watermark(self, token: int) -> None:
        """Advance the evaluator watermark to this write's own token -- ASSIGNMENT, and
        only across a verified-contiguous stretch (ZT-P1-5).

        Was ``max(self.evaluator_watermark, token)``, which assumed the catch-up above
        had really tailed everything below ``token``. Under a pinned read snapshot it
        has not (see ``WatermarkGap``), and the jump then buries those rows forever
        while ``at_least`` keeps certifying the answers. The only row this instance
        applied in ``(watermark, token]`` is its OWN append, so any other committed row
        in that interval is a row about to be skipped -- refuse instead."""
        if token <= self.evaluator_watermark:
            # Cannot happen for a real append (log ids are monotone and the lock keeps
            # them in commit order), and if it somehow does, the watermark must not
            # move BACKWARDS -- keep the stronger claim.
            return
        gap = log_gap(self.session, self.store_id, self.evaluator_watermark,
                      token, (token,))
        if gap is not None:
            raise WatermarkGap(
                f'evaluator watermark {self.evaluator_watermark} -> {token} would skip '
                f'committed log row {gap} for store {self.store_id!r}: this session\'s '
                f'read snapshot predates it, so the catch-up could not see it. Roll '
                f'back to start a fresh snapshot, refresh_evaluator(), and retry.')
        self.evaluator_watermark = token

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
        RESET the evaluator watermark to it. Assignment, not max: after a rollback the
        old watermark may claim a token that never committed.

        The watermark/rebuild pair goes through ``_consistent_rebuild`` (2026-07-27).
        It used to be a bare read-then-rebuild, whose comment called reading the
        watermark first "conservative: rows committed in between are included in the
        rebuild but not claimed" -- that is precisely BACKWARDS. A row in the rebuild
        but not in the watermark leaves the evaluator AHEAD of its watermark, and the
        next catch-up replays it into ``apply_logged``'s strict guard and bricks the
        instance. Live on PostgreSQL READ COMMITTED, and this method sits on
        ``ConnectedStore._write``'s error path, so any failed write could enter it."""
        self.evaluator_watermark = self._consistent_rebuild(self.engine.rebuild)

    def watermark(self) -> int:
        return log_watermark(self.session, self.store_id)
