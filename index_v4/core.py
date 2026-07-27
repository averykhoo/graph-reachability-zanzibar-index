import os
import threading
import time
from contextlib import contextmanager
from types import EllipsisType
from sqlalchemy import insert, tuple_, update
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from legacy.index_v1 import MultiSet
from zanzibar_utils_v1 import (AdmissionRejected, validate_write_identifiers,
                               validate_node_identifiers)
from .invariants import InvariantViolation
from .models import DeltaOutboxV1, EdgeV4, NodeV4, Edge, Node, StoreV4

# ``AdmissionRejected`` is DEFINED in ``zanzibar_utils_v1`` (the shared schema layer,
# which imports no backend) so that both backends can raise one rejection type; it is
# re-exported here because ``index_v4`` is where its raise sites mostly live, and
# because the import direction forbids the reverse (``core`` already imports
# ``zanzibar_utils_v1``; ``zanzibar_utils_v1`` importing ``index_v4`` would cycle).
# It is the mirror of ``InvariantViolation``: rejection = correct refusal (a
# ``ValueError`` subclass, for backward compatibility with every existing
# ``except ValueError`` around a write); violation = corruption (an ``AssertionError``
# subclass, which therefore never enters a ``ValueError`` handler at all).
__all_exceptions__ = ('AdmissionRejected', 'InvariantViolation', 'WriteLockUnsafe')

# Per-batch node-resolution cache sentinels (perf N15). ``_UNCACHED`` distinguishes
# "key absent from the cache" (do the DB lookup) from ``_MISSING`` ("known-absent this
# batch" -- a negative cache entry). Both are private module singletons.
_UNCACHED = object()
_MISSING = object()


class _ThreadFlag(threading.local):
    """A boolean whose value is private to the thread that set it, default False.

    Backs the delta processor's derived-write window (ZT-P1-8e), whose whole job is
    to say "the WRITE I am doing right now is the processor's". A plain attribute
    answered that question for every thread at once, so a window opened by the
    cascade on one thread also opened it for an unrelated user write on another --
    and that window is the ONLY thing standing between a user tuple and a derived
    (processor-owned) family, i.e. the failure is an authorization-state corruption
    that commits cleanly, not an error anyone sees.

    Subclassing ``threading.local`` rather than holding one is what supplies the
    DEFAULT: an attribute never set in the current thread falls back to the class
    attribute, so a thread that never opened the window reads a CLOSED one -- which
    is the fail-closed direction at every read site."""
    on = False

# --------------------------------------------------------------------------- #
# Per-write closure fan-out cap (zero-trust review ZT-P1-6a)
# --------------------------------------------------------------------------- #

#: Ceiling on the number of closure rows ONE direct-edge addition may materialise.
#: There was no fuel counter, fan-out cap, depth limit or tuple quota anywhere in
#: this library; a single write expands |ancestors(subject)| x |descendants(object)|
#: rows (240 raw tuples in a hub topology measured 14,640 closure rows in 5.1 s) and
#: does it INSIDE ``advance_index`` while holding both the source lock and the graph
#: store lock -- so one write stalls every other writer on the store for its whole
#: duration. This is a BLAST-RADIUS bound, not an authorization policy.
#:
#: The default is chosen so it cannot refuse anything this repo has ever written:
#: instrumented over the whole suite on 2026-07-27, the largest single-write
#: expansion is 44 rows in ``tests/`` and 124 rows in ``formal/conformance/``, so
#: this leaves ~800x headroom and still admits e.g. granting one 90,000-member
#: group. An operator who wants a bound that actually bites should MEASURE their own
#: topology and lower it (``max_closure_fanout=`` or the env var below); the point of
#: the default is to turn "unbounded" into "bounded and visible", not to guess a
#: workload. ``0`` disables the check entirely.
DEFAULT_MAX_CLOSURE_FANOUT = 100_000

#: Process-wide override for ``DEFAULT_MAX_CLOSURE_FANOUT``, so an operator can retune
#: the bound without touching every ``ReachabilityIndex`` construction site (the
#: constructor argument still wins, and is what a per-store policy should use).
MAX_CLOSURE_FANOUT_ENV = 'ZANZIBAR_MAX_CLOSURE_FANOUT'


def resolve_max_closure_fanout(value: int | None) -> int:
    """Constructor argument > environment > module default; ``0`` means unbounded.

    Fails LOUD on a malformed setting rather than falling back to the default: a
    typo'd env var silently restoring the unbounded behaviour is precisely the class
    of "safe by default" that is not."""
    if value is None:
        raw = os.environ.get(MAX_CLOSURE_FANOUT_ENV)
        if raw is None or raw.strip() == '':
            return DEFAULT_MAX_CLOSURE_FANOUT
        try:
            value = int(raw)
        except ValueError as e:
            raise ValueError(
                f'{MAX_CLOSURE_FANOUT_ENV}={raw!r} is not an integer (use a positive '
                f'row count, or 0 to disable the cap)') from e
    if value < 0:
        raise ValueError(
            f'max_closure_fanout must be >= 0 (0 disables the cap), got {value}')
    return value


# --------------------------------------------------------------------------- #
# Writer serialization primitives (zero-trust review ZT-P1-4)
# --------------------------------------------------------------------------- #

#: Minimum SQLite ``busy_timeout`` (ms) this library installs on a connection before
#: taking a write lock. SQLite's own busy handler IS the correct backoff for write-lock
#: contention -- it retries internally instead of failing the statement -- and its
#: default is 0 (fail immediately). A caller that already configured a HIGHER timeout
#: keeps it; nothing is ever lowered.
SQLITE_BUSY_TIMEOUT_MS = 10_000

#: Bounded statement-level retry for the residual ``SQLITE_BUSY`` that the busy handler
#: cannot absorb (e.g. a WAL write-after-read snapshot conflict, which fails instantly
#: by design). Exponential backoff; after the last attempt the error propagates so the
#: caller can retry the whole transaction on a fresh snapshot.
SQLITE_BUSY_RETRIES = 4
SQLITE_BUSY_BACKOFF = 0.01


class WriteLockUnsafe(RuntimeError):
    """The documented per-store write lock cannot actually be taken on this session's
    bind, so a write's check-then-act admission is not atomic against other writers
    (zero-trust review ZT-P1-4). The message names the configuration fix."""


def is_sqlite(session: Session) -> bool:
    """True when this session's bind is SQLite (pysqlite renders ``FOR UPDATE`` to
    NOTHING, so the lock path has to differ -- see ``take_row_write_lock``)."""
    try:
        return session.get_bind().dialect.name == 'sqlite'
    except Exception:                                   # pragma: no cover - no bind
        return False


def _sqlite_raw_connection(session: Session):
    """The raw ``sqlite3.Connection`` behind this session (for ``in_transaction``)."""
    return session.connection().connection.dbapi_connection


def _sqlite_busy(exc: BaseException) -> bool:
    msg = str(getattr(exc, 'orig', exc)).lower()
    return 'locked' in msg or 'busy' in msg


def _ensure_sqlite_busy_timeout(session: Session) -> None:
    """Raise this connection's ``busy_timeout`` to ``SQLITE_BUSY_TIMEOUT_MS`` if it is
    lower. SQLite's busy handler is the in-engine retry-with-backoff for write-lock
    contention; with the default 0 a second writer fails instantly instead of waiting
    (there was no ``SQLITE_BUSY`` handling anywhere in the library -- ZT-P1-4).

    Memoized in ``Connection.info``, whose lifetime is exactly the DBAPI connection's --
    the same scope the PRAGMA itself has -- so this costs one extra round trip per
    connection, not one per lock."""
    conn = session.connection()
    if conn.info.get('_zanzibar_busy_timeout_ms', 0) >= SQLITE_BUSY_TIMEOUT_MS:
        return
    current = conn.exec_driver_sql('PRAGMA busy_timeout').scalar()
    conn.info['_zanzibar_busy_timeout_ms'] = max(int(current or 0), SQLITE_BUSY_TIMEOUT_MS)
    if current is None or int(current) < SQLITE_BUSY_TIMEOUT_MS:
        # PRAGMA takes no bound parameters; the value is a module constant int, so
        # this stays inside the project's "no user data in raw SQL" property.
        conn.exec_driver_sql(f'PRAGMA busy_timeout={int(SQLITE_BUSY_TIMEOUT_MS)}')


def take_row_write_lock(session: Session, lock_select, lock_update) -> None:
    """Take the per-store write lock for the rest of the transaction (ZT-P1-4).

    Two arms, one contract ("no other writer can commit against this store until this
    transaction ends"):

    * **PostgreSQL** (the supported server; this arm is what any non-SQLite dialect
      gets) -- ``lock_select``, a ``SELECT ... FOR UPDATE`` on the store's lock row.
      Unchanged from before this fix, and first exercised for real on 2026-07-27:
      it blocks a second writer, at ROW granularity, and releases on commit
      (``tests/test_postgres_ha.py``).
    * **SQLite** -- ``with_for_update()`` compiles to a PLAIN SELECT on pysqlite (no
      ``FOR UPDATE`` in the emitted statement; verified), so the documented lock was a
      silent NO-OP and, worse, pysqlite's default ``isolation_level=''`` runs SELECTs
      in autocommit, so the validating reads of a write were not even in the same
      transaction as its INSERT. We therefore issue ``lock_update`` -- a no-op UPDATE
      of the same lock row -- which takes SQLite's RESERVED (database write) lock for
      the rest of the transaction: a genuine writer serialization, and it promotes the
      connection into a real transaction so every subsequent SELECT of the check-then-
      act sequence reads inside it. Verified empirically: a second connection's write
      blocks while the lock is held, and the UPDATE takes the lock even when it
      matches zero rows (a store row that does not exist yet).

    SQLITE_BUSY: the busy timeout is floored first (SQLite's own backoff), then a
    bounded statement-level retry covers the residual; after that the error propagates
    for the caller to retry the transaction (the existing concurrency tests already
    retry ``OperationalError``)."""
    if not is_sqlite(session):
        session.exec(lock_select).first()
        return
    _ensure_sqlite_busy_timeout(session)
    stmt = lock_update.execution_options(synchronize_session=False)
    for attempt in range(SQLITE_BUSY_RETRIES):
        try:
            session.execute(stmt)
            return
        except OperationalError as exc:
            last = attempt == SQLITE_BUSY_RETRIES - 1
            if last or not _sqlite_busy(exc) or not session.is_active:
                raise
            time.sleep(SQLITE_BUSY_BACKOFF * (2 ** attempt))


def store_lock_statements(store_id: str):
    """The (SELECT ... FOR UPDATE, no-op UPDATE) pair that locks one store's row."""
    return (
        select(StoreV4).where(StoreV4.id == store_id).with_for_update(),
        # no-op UPDATE (SQLite arm): same row, unchanged value -- it exists to take the
        # write lock, not to change data.
        update(StoreV4).where(StoreV4.id == store_id)
        .values(description=StoreV4.description),
    )


def probe_store_write_lock(session: Session, store_id: str) -> None:
    """Open-time ZT-P1-4 check: take the store write lock for real and verify it held.

    SQLite only (off it ``FOR UPDATE`` is genuine, and issuing a lock at open would
    break a legitimate read-only open against a hot standby). Call this as the FIRST
    statement of the transaction: before any read has pinned a WAL snapshot, so lock
    contention WAITS on the busy timeout (an effective ``BEGIN IMMEDIATE``) instead of
    failing instantly with SQLite's write-after-read ``SQLITE_BUSY``."""
    if not is_sqlite(session):
        return
    take_row_write_lock(session, *store_lock_statements(store_id))
    assert_write_lock_effective(session)


def assert_write_lock_effective(session: Session) -> None:
    """Fail loudly, at open time, when this session cannot hold the write lock at all
    (ZT-P1-4). Dialect-aware: a no-op off SQLite (``FOR UPDATE`` is real there).

    The check is EMPIRICAL rather than a guess at the config: the caller has just
    taken the lock, so the raw connection must now be inside a transaction. It is not
    when the connection runs in autocommit -- SQLAlchemy ``isolation_level='AUTOCOMMIT'``,
    or pysqlite ``isolation_level=None`` / ``autocommit=True`` with nothing emitting
    ``BEGIN`` -- in which case the lock was released the instant it was taken and two
    writers can both pass admission against a state their combined result invalidates.

    Both SAFE configurations pass: pysqlite's DEFAULT (``isolation_level=''``, which
    auto-begins on our lock UPDATE) and the recommended recipe
    (``isolation_level=None`` + a ``begin`` listener emitting ``BEGIN``)."""
    if not is_sqlite(session):
        return
    raw = _sqlite_raw_connection(session)
    if getattr(raw, 'in_transaction', False):
        return
    raise WriteLockUnsafe(
        "SQLite bind: the per-store write lock did NOT hold -- this connection is in "
        "autocommit mode, so it was released the moment it was taken and a write's "
        "check-then-act admission (duplicate detection, remove-existence, cycle "
        "parity) is not atomic against another writer (zero-trust review ZT-P1-4). "
        "Fix the engine configuration: either leave pysqlite's DEFAULT "
        "isolation_level ('') in place, or use the documented SQLAlchemy recipe -- a "
        "'connect' listener setting dbapi.isolation_level = None PLUS a 'begin' "
        "listener running conn.exec_driver_sql('BEGIN') (see "
        "tests/test_connectedstore_multi_instance.py). Do NOT open the engine or "
        "session with isolation_level='AUTOCOMMIT', and do not set the sqlite3 "
        "connection's autocommit=True.")


class ReachabilityIndex:
    """
    Stateful interface to interact with the transitive closure DAG.
    Operates inside a provided Session to allow multi-edge transactional batching.

    Concurrency: every write funnels through ``_lock_store`` (a ``FOR UPDATE`` row lock on
    the store row) so that a whole logical write -- the check-then-act cycle test *and* the
    read-modify-write ref-count updates across the affected closure region -- is atomic
    with respect to other writers to the same store. Without it, two concurrent writers on
    a real MVCC backend (PostgreSQL at READ COMMITTED, the only supported server/level
    combination) would (a) lose ref-count increments on any shared edge and (b) be able to
    each pass the cycle check yet jointly create a cycle. See ``_lock_store`` for why the
    lock is at store rather than per-edge granularity.
    """

    def __init__(self, session: Session, store_id: str, *,
                 max_closure_fanout: int | None = None):
        self.session = session
        self.store_id = store_id
        # Per-write closure fan-out cap (ZT-P1-6a). Resolved once, here, so the value
        # an index enforces is fixed at construction and cannot be moved under a
        # running transaction by an env change; see ``resolve_max_closure_fanout``.
        self.max_closure_fanout = resolve_max_closure_fanout(max_closure_fanout)
        # When True, direct-edge writes flag their rows EdgeV4.derived (boolean spec
        # §4/I5). Only the delta processor's façade path sets this, around its own
        # writes into derived-public families. THREAD-SCOPED (ZT-P1-8e): this is the
        # downstream half of ``WildcardIndex.processor_writes`` -- see the property
        # below and that attribute's comment for why the window must belong to the
        # thread that opened it.
        self._writing_derived_flag = _ThreadFlag()
        # Identity of the SessionTransaction under which this store's FOR UPDATE lock
        # is already held (perf P12a). ``None`` = no lock taken in the current
        # transaction. See ``_lock_store``.
        self._locked_txn = None
        # Outbox emit buffer (perf N16): ``_emit`` denormalizes endpoint identities
        # eagerly (while the nodes are alive) but stages the row as a plain dict here
        # instead of ``session.add``-ing an ORM instance. ``_flush_outbox`` drains the
        # whole buffer in ONE ``insert(DeltaOutboxV1), [rows]`` (SQLAlchemy
        # insertmanyvalues -> a single INSERT statement) at the end of every
        # ``_add_direct_edge_unsafe`` -- the sole driver of ``_emit`` and a call during
        # which nothing reads the outbox -- so the emitted ids stay monotone in
        # emission order (SQLite/Postgres autoincrement is monotone in list order,
        # empirically verified) and every outbox reader (cascade frontier drain,
        # ``outbox_watermark``, the paranoia delta verifier) still observes a fully
        # materialized stream. The row dicts are byte-identical to the old ORM path.
        self._outbox_buffer: list[dict] = []
        # Per-batch node-resolution cache (perf N15): ``(predicate, type, name,
        # wildcard) -> NodeV4 | _MISSING``. ``None`` outside a write batch, so every
        # ``node`` / ``cached_concrete_node`` resolution behaves exactly as pre-N15
        # (no memoization). Installed only for the bounded duration of one write batch
        # via ``_node_cache_scope`` (an ``advance_index`` apply-loop + cascade, or a
        # standalone ``run_cascade``); the five NodeV4 delete sites evict through
        # ``_evict_node`` and the sole creation choke point (``node``) overwrites the
        # negative entry, so a stale hit can never resurrect a dead node. Keyed by the
        # IMMUTABLE identity tuple (only ``implicit`` / ``reference_count`` mutate), so
        # it is immune to the SQLite rowid reuse that sank every id-based cache
        # (blind-audit W2 -- that hazard was cross-session; this cache never survives a
        # commit/rollback, see ``_node_cache_scope``).
        self._node_cache: dict[tuple[str, str, str, str], NodeV4] | None = None

    @property
    def _writing_derived(self) -> bool:
        """Whether THIS thread is inside the delta processor's derived-write window.

        A plain instance bool made the window shared state: with two threads on one
        index, thread A's processor write decided whether thread B's row got stamped
        ``derived``, which is an I5 (derived-exclusivity) violation that survives
        commit rather than a DB error. Reading per-thread makes an un-opened window
        read closed, which is the fail-CLOSED direction on both sites that consult it
        (a missing stamp trips I5's checker loudly; a spurious one is a grant)."""
        return self._writing_derived_flag.on

    @_writing_derived.setter
    def _writing_derived(self, value: bool) -> None:
        self._writing_derived_flag.on = bool(value)

    @contextmanager
    def _node_cache_scope(self):
        """Install the per-batch node-resolution cache for one write batch (perf N15).

        Reentrant, mirroring the processor's ``_residue_cache_scope`` (perf P3): a
        nested entry shares the outer cache and only the OUTERMOST installs/tears down,
        so ``advance_index`` can wrap its whole batch while the ``run_cascade`` it calls
        just no-ops its own scope. A standalone ``run_cascade`` (e.g. the test-matrix
        GraphBackend) is the outermost and installs its own.

        The cache MUST NOT survive a commit/rollback: callers commit AFTER the scope
        closes (``advance_index`` / GraphBackend both commit past ``run_cascade``), so
        the paranoia checker (fires on ``before_commit``) always reads TRUE state with
        the cache already torn down, and no cross-transaction entry is ever served."""
        outer = self._node_cache is None
        if outer:
            self._node_cache = {}
        try:
            yield
        finally:
            if outer:
                self._node_cache = None

    def _evict_node(self, node: NodeV4) -> None:
        """Evict a node from the per-batch cache immediately before deleting its row
        (perf N15). The row is removed in this transaction, so a later same-batch
        resolution must miss -- we record ``_MISSING`` rather than dropping the key, so
        repeated probes for the now-dead identity stay cheap. Keyed by the node's
        immutable identity, so a subsequent re-creation of the same identity through
        ``node`` re-populates the entry. No-op when no batch cache is installed. MUST be
        called at every NodeV4 ``session.delete`` site (three in
        ``_add_direct_edge_unsafe_impl``; ``DeltaProcessor._gc_subject_node`` /
        ``_gc_public_node``)."""
        cache = self._node_cache
        if cache is not None:
            cache[(node.predicate, node.type, node.name, node.wildcard)] = _MISSING

    def _emit(self, subject_id: int, object_id: int, action: str,
              node_map: dict[int, NodeV4] | None = None) -> None:
        """Record a reachability flip in the outbox (boolean spec §4: deltas are rows
        inserted inside the writing transaction, never in-memory lists). Endpoint
        identities are denormalized at emission -- the nodes are alive here, but
        implicit-node GC may delete them before the cascade reads the row.

        The row is staged in ``self._outbox_buffer`` and bulk-inserted by
        ``_flush_outbox`` at the end of the driving ``_add_direct_edge_unsafe`` (perf
        N16); the endpoint-identity capture below is UNCHANGED and still happens here,
        eagerly, so a later implicit-node GC can never strip the denormalized columns.

        ``node_map`` is an optional ``{id: NodeV4}`` region snapshot hoisted by the
        caller (perf P7b) to collapse the per-emit ``session.get`` round trips. It is
        a pure optimization: a miss falls back to ``session.get``, so the emitted
        identity is byte-identical to the unhoisted path. Endpoint node identity
        (type/name/predicate) is never mutated by edge/refcount updates, and the
        batch expansion deletes no nodes, so a snapshot taken at the driving call
        site stays valid for every emit it feeds."""
        def _resolve(nid: int) -> NodeV4 | None:
            if node_map is not None:
                hit = node_map.get(nid)
                if hit is not None:
                    return hit
            return self.session.get(NodeV4, nid)

        s = _resolve(subject_id)
        o = _resolve(object_id)
        self._outbox_buffer.append(dict(
            store_id=self.store_id, subject_node_id=subject_id, object_node_id=object_id,
            action=action,
            subject_type=s.type if s else '', subject_name=s.name if s else '',
            subject_predicate=s.predicate if s else '',
            object_type=o.type if o else '', object_name=o.name if o else '',
            object_predicate=o.predicate if o else ''))

    def _flush_outbox(self) -> None:
        """Bulk-insert the buffered outbox rows in one statement, then reset the buffer
        (perf N16). Called at the end of ``_add_direct_edge_unsafe`` -- the sole emit
        driver -- so the buffer is empty whenever control leaves that method and no
        outbox reader (all of which run BETWEEN write ops or at commit) can observe a
        starved stream. ``session.execute(insert(...), rows)`` runs synchronously and
        assigns autoincrement ids monotone in list order, i.e. in emission order, which
        the cascade's ``id > watermark`` frontier drain and the §8.3 delta verifier
        both depend on. A Core insert (not ORM ``add``) does not populate the identity
        map, which is irrelevant: outbox rows are append-only and every reader
        re-SELECTs them fresh."""
        if not self._outbox_buffer:
            return
        rows, self._outbox_buffer = self._outbox_buffer, []
        self.session.execute(insert(DeltaOutboxV1), rows)

    def _load_nodes(self, ids) -> dict[int, NodeV4]:
        """Batch-load nodes by id in chunked ``IN`` queries (perf P7b). Used to hoist
        a region snapshot for ``_emit``; a returned instance is identical to what
        ``session.get`` would hand back per id (SQLAlchemy identity map), so passing
        this map into ``_emit`` never changes the denormalized endpoint identity."""
        want = [i for i in dict.fromkeys(ids) if i is not None]
        out: dict[int, NodeV4] = {}
        _CHUNK = 900  # single-column IN: stay under SQLite's 999 bind-param default
        for start in range(0, len(want), _CHUNK):
            rows = self.session.exec(
                select(NodeV4).where(NodeV4.store_id == self.store_id)
                .where(NodeV4.id.in_(want[start:start + _CHUNK]))  # type: ignore[attr-defined]
            ).all()
            for n in rows:
                out[n.id] = n
        return out

    def _lock_store(self) -> None:
        """Serialize concurrent writers to this store for the rest of the transaction.

        A single ``add_edge`` / ``remove_edge`` mutates a data-dependent set of
        transitive-closure rows *and* performs a check-then-act cycle test; both must be
        atomic w.r.t. other writers. We take a row-level ``FOR UPDATE`` lock on the store
        row rather than locking each affected edge: the affected set is discovered while
        walking the graph, so locking it piecemeal in graph order invites deadlocks --
        serializing at store granularity is deadlock-free and matches the reality that one
        logical write already touches many rows.

        On PostgreSQL this blocks other writers to the store until this transaction
        commits/rolls back; that the block is real and row-granular is now observed, not
        assumed (``tests/test_postgres_ha.py`` holds this very ``StoreV4`` row and watches
        a writer queue on it). A missing store row simply yields no lock (harmless).

        SQLITE (ZT-P1-4, 2026-07-26): ``with_for_update()`` compiles to a plain SELECT
        on pysqlite, so this lock used to be a silent NO-OP -- the old docstring's
        "the engine already takes a database-level write lock" is only true from the
        first WRITE statement onward, which is *after* the check-then-act cycle test
        and (with pysqlite's default ``isolation_level=''``) not even in the same
        transaction as the validating SELECTs. ``take_row_write_lock`` therefore issues
        a no-op UPDATE of the store row on a SQLite bind, which takes SQLite's RESERVED
        write lock here, at lock time, and holds it until the transaction ends.

        Transaction-scoped memo (perf P12a): the lock is held for the whole transaction,
        so re-issuing the ``SELECT ... FOR UPDATE`` on a row this transaction already
        locked is a pure no-op round trip. We remember the ``SessionTransaction`` object
        under which the lock was taken and short-circuit while it is still live. Keying
        on the object *identity* (not a boolean) is what makes this rollback-safe:
        ``Session.get_transaction()`` returns a fresh ``SessionTransaction`` after every
        commit/rollback and ``None`` before autobegin, so the memo can never match into a
        retried transaction -- a retry re-takes the real lock, which is exactly the
        lost-update guard this method exists to provide.

        SAVEPOINTS (ZT-P1-7, 2026-07-26): the memo key is the ``(root, nested)`` pair,
        NOT the root alone. ``get_transaction()`` returns the ROOT ``SessionTransaction``
        even inside ``begin_nested()``, so keying on it alone was unsound: a caller could
        take the lock inside a savepoint, roll that savepoint back -- PostgreSQL RELEASES
        locks acquired inside a rolled-back savepoint -- and the next call would match the
        memo and take NO lock at all. The repo itself uses no ``begin_nested``, but the
        ``Session`` is caller-supplied, and wrapping a speculative write in a savepoint and
        rolling back on rejection is an ordinary caller pattern. Including the nested
        transaction's identity makes entering or leaving any savepoint invalidate the memo,
        so the real lock is re-taken.
        """
        txn = self.session.get_transaction()
        key = (txn, self.session.get_nested_transaction())
        if txn is not None and key == self._locked_txn:
            return
        take_row_write_lock(self.session, *store_lock_statements(self.store_id))
        # Capture AFTER the select: the lock SELECT itself may have autobegun the
        # transaction, so ``get_transaction()`` was potentially None above. Store the
        # ``(root, nested)`` pair -- see the savepoint note in the docstring.
        self._locked_txn = (self.session.get_transaction(),
                            self.session.get_nested_transaction())

    def _add_db_edges_unsafe(
            self,
            subject_id: int | None,
            object_id: int | None,
            direct_count: int | None,
            indirect_count: int | None
    ) -> None:

        if not (subject_id is not None or object_id is not None):
            raise InvariantViolation('edge write needs at least one live endpoint id')
        if not (subject_id != object_id):
            raise InvariantViolation('edge write endpoints coincide (trivial cycle); admission must reject this before here')
        if not (direct_count != 0 or indirect_count != 0):
            raise InvariantViolation('edge write with both counts zero is a no-op that must not reach the row writer')

        _select = select(EdgeV4).where(EdgeV4.store_id == self.store_id)
        if subject_id is not None:
            _select = _select.where(EdgeV4.subject_id == subject_id)
        if object_id is not None:
            _select = _select.where(EdgeV4.object_id == object_id)

        triples = self.session.exec(_select).all()

        # Handle Brand New Edges
        if not triples:
            if not direct_count and not indirect_count:
                return
            if subject_id is None or object_id is None:
                return

            if not ((indirect_count or 0) >= (direct_count or 0)):
                raise InvariantViolation('I1 violated: indirect_edge_count < direct_edge_count')
            if not ((indirect_count or 0) > 0):
                raise InvariantViolation('I1 violated: zero-reachability row would be persisted (indirect_edge_count == 0)')

            edge = EdgeV4(
                store_id=self.store_id,
                subject_id=subject_id,
                object_id=object_id,
                direct_edge_count=direct_count or 0,
                indirect_edge_count=indirect_count or 0,
                derived=bool(self._writing_derived and (direct_count or 0) > 0),
            )
            self.session.add(edge)
            self._emit(subject_id, object_id, "ADDED")
            return

        # Handle Updates to Existing Edges
        for triple in triples:
            old_indirect = triple.indirect_edge_count

            direct_will_be_zero = False
            if direct_count is None:
                direct_will_be_zero = True
                new_direct = 0
            else:
                new_direct = triple.direct_edge_count + direct_count
                if new_direct == 0:
                    direct_will_be_zero = True

            indirect_will_be_zero = False
            if indirect_count is None:
                indirect_will_be_zero = True
                new_indirect = 0
            else:
                new_indirect = triple.indirect_edge_count + indirect_count
                if new_indirect == 0:
                    indirect_will_be_zero = True

            # If both fall to zero, delete entirely
            if direct_will_be_zero and indirect_will_be_zero:
                self.session.delete(triple)
                self._emit(triple.subject_id, triple.object_id, "REMOVED")
                continue

            triple.direct_edge_count = new_direct
            triple.indirect_edge_count = new_indirect

            if not (triple.indirect_edge_count >= triple.direct_edge_count):
                raise InvariantViolation('I1 violated: indirect_edge_count < direct_edge_count')
            if not (triple.indirect_edge_count > 0):
                raise InvariantViolation('I1 violated: zero-reachability row would be persisted (indirect_edge_count == 0)')

            # Derived flag follows the direct edge (boolean spec I5): set when the
            # processor writes the direct edge, cleared when the direct count retires
            # (a surviving indirect-only row is closure state, not a derived grant).
            if direct_will_be_zero:
                triple.derived = False
            elif self._writing_derived and (direct_count or 0) > 0:
                triple.derived = True

            self.session.add(triple)

            if old_indirect == 0 and new_indirect > 0:
                self._emit(triple.subject_id, triple.object_id, "ADDED")

    def _add_indirect_edges_batch_unsafe(
            self, deltas: list[tuple[int, int, int]],
            node_map: dict[int, NodeV4] | None = None
    ) -> None:
        """Batched, indirect-only form of ``_add_db_edges_unsafe`` for the
        O(ancestors x descendants) closure region emitted by the expansion loops.

        Each entry is a CONCRETE ``(from_id, to_id, indirect_delta)`` with an
        implicit ``direct_count == 0`` -- the expansion loops only touch indirect
        path counts (the direct edge is applied separately: subtracted first on
        removal, added last on addition). Because those loops enumerate
        ancestors x descendants plus the subject/object fringes -- and subject is
        never an ancestor, object never a descendant, and there are no self-edges
        -- every emitted pair is DISTINCT. So one region ``SELECT`` (chunked
        row-value ``IN``), in-memory increments, and a single flush reproduce the
        per-pair ``_add_db_edges_unsafe`` EXACTLY: identical final ref counts,
        identical delete-when-both-zero, the ``derived`` flag untouched (never a
        derived grant with ``direct_count == 0``), and one outbox action per pair
        in loop order (each distinct pair flips at most once, so the *final*
        per-pair action ``verify_outbox_deltas`` keys off is preserved). This
        collapses the N+1 point-``SELECT`` round trip (perf handoff P2); the
        ref-count math below is a faithful copy of ``_add_db_edges_unsafe``
        specialised to ``direct_count == 0`` concrete endpoints.
        """
        if not deltas:
            return

        # One region read, chunked so the row-value IN never exceeds the driver's
        # bind-parameter cap (2 params/pair; ~400 pairs stays well under SQLite's
        # 999 default). Load the WHOLE region before any mutation, so no chunk's
        # autoflush can observe an increment applied for an earlier chunk (moot for
        # distinct pairs, but keeps the batch read a pure snapshot).
        existing: dict[tuple[int, int], EdgeV4] = {}
        _CHUNK = 400
        for start in range(0, len(deltas), _CHUNK):
            pairs = [(f, t) for (f, t, _d) in deltas[start:start + _CHUNK]]
            rows = self.session.exec(
                select(EdgeV4).where(EdgeV4.store_id == self.store_id)
                .where(tuple_(EdgeV4.subject_id, EdgeV4.object_id).in_(pairs))
            ).all()
            for r in rows:
                existing[(r.subject_id, r.object_id)] = r

        for from_id, to_id, indirect_delta in deltas:
            triple = existing.get((from_id, to_id))

            # Brand-new edge (mirrors the `if not triples` arm of _add_db_edges_unsafe).
            if triple is None:
                if not indirect_delta:
                    continue
                if not (indirect_delta > 0):
                    raise InvariantViolation('pure-indirect delta for a brand-new edge must be positive')
                edge = EdgeV4(
                    store_id=self.store_id,
                    subject_id=from_id,
                    object_id=to_id,
                    direct_edge_count=0,
                    indirect_edge_count=indirect_delta,
                    derived=False,  # direct_count == 0 -> never a derived grant
                )
                self.session.add(edge)
                existing[(from_id, to_id)] = edge
                self._emit(from_id, to_id, "ADDED", node_map)
                continue

            # Update existing edge. With direct_count == 0, new_direct == old_direct,
            # so direct_will_be_zero iff the direct count was already zero.
            old_indirect = triple.indirect_edge_count
            new_indirect = old_indirect + indirect_delta

            # If both fall to zero, delete entirely (direct is zero here iff it was).
            if triple.direct_edge_count == 0 and new_indirect == 0:
                self.session.delete(triple)
                del existing[(from_id, to_id)]
                self._emit(triple.subject_id, triple.object_id, "REMOVED", node_map)
                continue

            triple.indirect_edge_count = new_indirect

            if not (triple.indirect_edge_count >= triple.direct_edge_count):
                raise InvariantViolation('I1 violated: indirect_edge_count < direct_edge_count')
            if not (triple.indirect_edge_count > 0):
                raise InvariantViolation('I1 violated: zero-reachability row would be persisted (indirect_edge_count == 0)')

            # Derived flag follows the direct edge (boolean spec I5): a surviving
            # indirect-only row is closure state, not a derived grant. With
            # direct_count == 0 the "set" branch is unreachable; the clear branch
            # mirrors _add_db_edges_unsafe's `if direct_will_be_zero`.
            if triple.direct_edge_count == 0:
                triple.derived = False

            self.session.add(triple)

            if old_indirect == 0 and new_indirect > 0:
                self._emit(triple.subject_id, triple.object_id, "ADDED", node_map)

    def _add_direct_edge_unsafe(self, subject_id: int, object_id: int, count: int) -> None:
        """N16 outbox-drain boundary: this is the SOLE driver of ``_emit`` (every
        ``_add_db_edges_unsafe`` / ``_add_indirect_edges_batch_unsafe`` call originates
        here) and nothing reads the outbox for its duration, so draining the emit buffer
        exactly once at its end keeps outbox ids monotone in emission order while
        collapsing the per-row INSERTs into one statement. The ``finally`` is a leak
        guard: on any error path the buffered rows were never inserted and belong to a
        transaction the caller rolls back, so we drop them -- mirroring how the old
        ``session.add`` path relied on rollback to discard pending outbox rows, so a
        reused index instance never bleeds them into a later successful transaction."""
        try:
            self._add_direct_edge_unsafe_impl(subject_id, object_id, count)
            self._flush_outbox()
        finally:
            self._outbox_buffer = []

    def _add_direct_edge_unsafe_impl(self, subject_id: int, object_id: int, count: int) -> None:
        if not (count in {-1, 1}):
            raise InvariantViolation('direct-edge delta must be exactly -1 or +1')

        # Remove direct edge first to preserve invariant on subtraction
        if subject_id != object_id and count < 0:
            self._add_db_edges_unsafe(subject_id, object_id, count, count)

        # Node removal shortcut: unsets direct edge counts globally
        if subject_id == object_id:
            if count != -1:
                # DELIBERATELY NOT AdmissionRejected: an internal-contract failure (no
                # user write can reach it), so it must stay a bug signal.
                raise ValueError('node-removal shortcut only supports count == -1')
            # Blind-audit C1: the shortcut retires every incident direct edge by
            # count math, so the neighbours' reference_counts (incremented per direct
            # edge on add) must be decremented FIRST -- and the same implicit-GC rule
            # applied -- or every neighbour of a removed node keeps an inflated count
            # forever, defeating bridge GC (wildcard §7.3) and _gc_public_node.
            incident = self.session.exec(
                select(EdgeV4).where(EdgeV4.store_id == self.store_id)
                .where((EdgeV4.subject_id == subject_id) | (EdgeV4.object_id == subject_id))
                .where(EdgeV4.direct_edge_count > 0)  # type: ignore[arg-type]
            ).all()
            neighbour_debits: dict[int, int] = {}
            for e in incident:
                other = e.object_id if e.subject_id == subject_id else e.subject_id
                if other != subject_id:
                    neighbour_debits[other] = neighbour_debits.get(other, 0) + e.direct_edge_count
            self._add_db_edges_unsafe(subject_id, None, None, 0)
            self._add_db_edges_unsafe(None, object_id, None, 0)
            # Debits are APPLIED at the tail (with the logical node deletion): the
            # expansion loops below retire the surviving indirect counts and emit
            # REMOVED deltas, and _emit denormalizes endpoint identities from live
            # node rows (I10) -- GC-ing a neighbour here would strip them.

        # Build local reachability map based on current DB state
        reachable_before_subject = MultiSet()
        reachable_after_object = MultiSet()

        triples_from = self.session.exec(
            select(EdgeV4).where(EdgeV4.store_id == self.store_id).where(EdgeV4.object_id == subject_id)
        ).all()
        for triple in triples_from:
            reachable_before_subject[triple.subject_id] = triple.indirect_edge_count

        triples_to = self.session.exec(
            select(EdgeV4).where(EdgeV4.store_id == self.store_id).where(EdgeV4.subject_id == object_id)
        ).all()
        for triple in triples_to:
            reachable_after_object[triple.object_id] = triple.indirect_edge_count

        # SECURITY-CRITICAL: the only cycle guard on this (batch/bridge expansion)
        # path. As `raise`, not `assert` -- under `python -O` an assert here vanishes
        # and the expansion loops below proceed on a cyclic graph, producing unbounded
        # path counts, hence permanent phantom reachability, hence a stale ALLOW.
        # Same reasoning as the self-edge rejection in `_add_edge_locked`
        # (blind-audit C3); hardened by the zero-trust review 2026-07-26 (ZT-P1-2).
        if reachable_before_subject[object_id] != 0:
            raise InvariantViolation("Cycle detected in backward path")
        if reachable_after_object[subject_id] != 0:
            raise InvariantViolation("Cycle detected in forward path")

        # BLAST-RADIUS BOUND (ZT-P1-6a): refuse an addition whose closure region is
        # larger than this index's cap, BEFORE materialising any of it.
        #
        # Counted, not built: the three loops below emit exactly |A|x|D| + |D| + |A|
        # distinct pairs (subject is never an ancestor, object never a descendant, no
        # self-edges -- the same fact the batch writer's correctness rests on), so the
        # arithmetic is exact and costs nothing.
        #
        # WHERE it sits is the whole no-partial-state argument: on the addition path
        # (`count > 0`) every statement above this point is a read -- the direct-edge
        # decrement at the top runs only for `count < 0`, and the node-removal shortcut
        # only for `subject_id == object_id`. So this raise leaves the transaction
        # exactly as it found it, the same contract as the two cycle rejections just
        # above, and the caller's rollback (this layer never commits) discards the
        # node rows an `add_edge` may have created during resolution.
        #
        # REMOVALS ARE DELIBERATELY EXEMPT. A cap that refused removes would make an
        # over-large region permanently unshrinkable -- a strictly worse denial of
        # service than the one this guard exists to bound, and the only way back would
        # be raising the cap. It would also fire AFTER the direct-edge decrement above,
        # i.e. on partial state. The bound is on GROWTH.
        #
        # NOT capped either: `bulk_build.py`, which constructs the closure in memory and
        # never reaches this method. That is an offline, single-writer bootstrap holding
        # nobody up, so bounding it would only add a way to fail an import.
        n_anc = len(reachable_before_subject)
        n_desc = len(reachable_after_object)
        fanout = n_anc * n_desc + n_anc + n_desc
        if count > 0 and self.max_closure_fanout and fanout > self.max_closure_fanout:
            # AdmissionRejected, like the cycle refusals: a correct refusal of THIS
            # write, classifiable by every harness that already handles rejection --
            # not an InvariantViolation, because nothing is corrupt.
            raise AdmissionRejected(
                f'closure fan-out cap exceeded: this edge would materialise {fanout} '
                f'closure rows ({n_anc} ancestors x {n_desc} descendants + fringes), '
                f'over the limit of {self.max_closure_fanout} for store '
                f'{self.store_id!r}. Raise it with '
                f'ReachabilityIndex(max_closure_fanout=...) or {MAX_CLOSURE_FANOUT_ENV} '
                f'(0 disables the cap), or split the grant -- this write would hold the '
                f'store write lock for its whole expansion')

        # Expand transitive paths. The three loops enumerate DISTINCT concrete
        # pairs (subject is never an ancestor, object never a descendant, no
        # self-edges), each with a pure-indirect delta -- so gathering them and
        # applying the closure region in one batched pass reproduces the per-pair
        # _add_db_edges_unsafe EXACTLY while collapsing its N+1 SELECT round trip
        # (perf handoff P2). The append order below is the original loop order, so
        # the emitted outbox rows keep their order too.
        indirect_deltas: list[tuple[int, int, int]] = []
        for from_node_id, from_count in reachable_before_subject.items():
            for to_node_id, to_count in reachable_after_object.items():
                indirect_deltas.append((from_node_id, to_node_id, from_count * to_count * count))

        for to_node_id, path_count in reachable_after_object.items():
            indirect_deltas.append((subject_id, to_node_id, path_count * count))

        for from_node_id, path_count in reachable_before_subject.items():
            indirect_deltas.append((from_node_id, object_id, path_count * count))

        # Hoist the region's {id: node} snapshot ONCE (perf P7b): every pair the
        # batch emits has its endpoints in A (reachable_before_subject) ∪ D
        # (reachable_after_object) ∪ {subject, object}, so one IN-query replaces the
        # per-emit session.get round trips. The batch mutates only edges (no node is
        # deleted until the tail, after this call), so the snapshot stays valid for
        # every emit; a miss falls back to session.get, keeping it byte-identical.
        region_ids: set[int] = {subject_id, object_id}
        region_ids.update(k for k, _ in reachable_before_subject.items())
        region_ids.update(k for k, _ in reachable_after_object.items())
        node_map = self._load_nodes(region_ids)

        self._add_indirect_edges_batch_unsafe(indirect_deltas, node_map)

        # Add the direct edge last to preserve invariants on addition
        if subject_id != object_id and count > 0:
            self._add_db_edges_unsafe(subject_id, object_id, count, count)

        # Handle logical Node deletion
        if subject_id == object_id:
            # Blind-audit C1: apply the neighbour refcount debits computed in the
            # shortcut (one per retired incident direct edge) with the same
            # implicit-GC rule as remove_edge -- otherwise every neighbour of a
            # removed node keeps an inflated count forever, defeating bridge GC
            # (wildcard §7.3) and _gc_public_node. Done here, after the expansion
            # loops, so every REMOVED delta was emitted while its endpoints lived.
            # One IN-query hoists the neighbours + the subject node in place of the
            # per-neighbour point SELECTs (debits differ per neighbour, so they are
            # applied in Python, not a single UPDATE); by-id fetch, so identical rows.
            nodes = self._load_nodes(list(neighbour_debits.keys()) + [subject_id])
            for other_id, debit in neighbour_debits.items():
                _n = nodes.get(other_id)
                if _n is None:
                    continue
                if not (_n.reference_count - debit >= 0):
                    raise InvariantViolation('reference_count would go negative (neighbour debit exceeds count)')
                if _n.reference_count - debit == 0 and _n.implicit:
                    self._evict_node(_n)            # N15: evict before delete
                    self.session.delete(_n)
                else:
                    _n.reference_count -= debit
                    self.session.add(_n)
            _node = nodes.get(subject_id)
            if _node:
                self._evict_node(_node)             # N15: evict before delete
                self.session.delete(_node)
        else:
            for node_id in (subject_id, object_id):
                _node = self.session.exec(
                    select(NodeV4).where(NodeV4.store_id == self.store_id).where(NodeV4.id == node_id)).first()
                if _node:
                    if not (_node.reference_count + count >= 0):
                        raise InvariantViolation('reference_count would go negative')
                    if _node.reference_count + count == 0 and _node.implicit:
                        self._evict_node(_node)     # N15: evict before delete
                        self.session.delete(_node)
                    else:
                        _node.reference_count += count
                        self.session.add(_node)

    def node(self, predicate: str | EllipsisType, entity_type: str, entity_name: str, *, create_if_missing: bool,
             implicit: bool | None = None, wildcard: str = '') -> NodeV4:
        if predicate is Ellipsis:
            predicate = '...'

        # A wildcard node stores name='*' with wildcard in {'any','all'}; a concrete
        # node stores wildcard=''. The two facts are equivalent -- reject any attempt
        # to smuggle in an ambiguous node (spec §1.3).
        # Both raises below stay plain ValueError DELIBERATELY: they police the node
        # ENCODING contract, whose only reachable caller is this library (the façade's
        # `_resolve` routes every '*' through the wildcard branch before it gets here).
        # A hit means a caller is broken, so it must not be classified as a refusal.
        if wildcard not in {'', 'any', 'all'}:
            raise ValueError(f"wildcard must be '', 'any', or 'all', got {wildcard!r}")
        if (entity_name == '*') != (wildcard != ''):
            raise ValueError(
                f"name=='*' and a non-empty wildcard must go together, got "
                f"{entity_name=!r}, {wildcard=!r}"
            )

        # Per-batch resolution cache (perf N15). Serve/record positive and negative
        # (``_MISSING``) hits keyed by the identity tuple; ``None`` cache => the
        # unmemoized pre-N15 path. Negative caching is what collapses the boolean
        # cascade's repeated probes for absent nodes (ghost subjects etc.).
        cache = self._node_cache
        key = (predicate, entity_type, entity_name, wildcard)
        if cache is not None:
            entry = cache.get(key, _UNCACHED)
            if entry is _UNCACHED:
                found = self._db_node(predicate, entity_type, entity_name, wildcard)
                cache[key] = found if found is not None else _MISSING
            else:
                found = None if entry is _MISSING else entry
        else:
            found = self._db_node(predicate, entity_type, entity_name, wildcard)

        if found is not None:
            # explicit is sticky: an implicit node can be promoted to explicit, never
            # demoted (the processor's residue anchoring depends on this)
            if implicit is False and found.implicit:
                found.implicit = False
                self.session.add(found)
            return found

        if not create_if_missing:
            raise KeyError(f'Node missing: {predicate=}, {entity_type=}, {entity_name=}')

        # Default new nodes to implicit. Passing implicit=None straight through relies on
        # SQLModel coercing it back to the column default (True); make that explicit so
        # the implicit-GC predicate (`_node.implicit`) can never see a NULL/None and skip
        # collection. Only affects creation -- the found-node branch above is untouched.
        if implicit is None:
            implicit = True

        _node = NodeV4(store_id=self.store_id, predicate=predicate, type=entity_type, name=entity_name,
                       wildcard=wildcard, implicit=implicit)
        self.session.add(_node)
        self.session.flush()  # flush to get auto-increment id immediately without committing transaction
        # Creation-site invalidation (perf N15): this is the SOLE node-creation choke
        # point on the batch path, so overwriting the (possibly ``_MISSING``) entry here
        # is what keeps a negative cache honest -- a subsequent resolution of the same
        # identity sees the freshly created node.
        if cache is not None:
            cache[key] = _node
        return _node

    def _db_node(self, predicate: str, entity_type: str, entity_name: str,
                 wildcard: str) -> NodeV4 | None:
        """The raw ``NodeV4`` identity SELECT shared by ``node`` and
        ``cached_concrete_node`` (perf N15). No caching, no interning."""
        return self.session.exec(
            select(NodeV4)
            .where(NodeV4.store_id == self.store_id)
            .where(NodeV4.predicate == predicate)
            .where(NodeV4.type == entity_type)
            .where(NodeV4.name == entity_name)
            .where(NodeV4.wildcard == wildcard)
        ).first()

    def cached_concrete_node(self, predicate: str, entity_type: str,
                             name: str) -> NodeV4 | None:
        """Read-only, cache-aware resolution of a CONCRETE node (``wildcard == ''``);
        returns the node or ``None``, never creates, never promotes implicit->explicit
        (perf N15). Shares ``node``'s per-batch cache, so a concrete resolved, created,
        or evicted through the ``node`` choke point stays coherent with this read path.
        Outside a batch (cache ``None``) it is a single point SELECT -- byte-identical
        to the pre-N15 ``DeltaProcessor._node``, whose sole implementation this is."""
        cache = self._node_cache
        key = (predicate, entity_type, name, '')
        if cache is not None:
            entry = cache.get(key, _UNCACHED)
            if entry is not _UNCACHED:
                return None if entry is _MISSING else entry
        row = self._db_node(predicate, entity_type, name, '')
        if cache is not None:
            cache[key] = row if row is not None else _MISSING
        return row

    def _require_live_nodes(self, *node_ids: int) -> None:
        """Both endpoints must still exist (checked INSIDE the store lock): a stale
        id from a pre-lock resolution racing a concurrent remove_node would otherwise
        insert a dangling edge -- and SQLite rowid reuse could later turn it into a
        phantom permission on an unrelated node (blind-audit C2). Cache-blind by
        contract: this is a liveness check, so it hits the DB directly (never the
        N15 node cache) -- one IN-query for both endpoints, not a SELECT per id."""
        live = set(self.session.exec(
            select(NodeV4.id).where(NodeV4.store_id == self.store_id)
            .where(NodeV4.id.in_(list(dict.fromkeys(node_ids))))  # type: ignore[attr-defined]
        ).all())
        for nid in node_ids:
            if nid not in live:
                # DELIBERATELY NOT AdmissionRejected: a stale id reaching the row writer
                # is a liveness/locking failure, not a refusal of the user's write.
                raise ValueError(f'node id {nid} no longer exists (concurrent removal?)')

    def _add_edge_locked(self, subject_id: int, object_id: int) -> None:
        """Cycle pre-check + ref-counted +1 direct-edge update. Caller holds the
        store lock and has established both ids are live (resolution under the lock
        counts: every writer serializes on it, so no concurrent removal can land)."""
        if subject_id == object_id:
            # a tuple whose subject node IS its object node is the trivial cycle;
            # a real rejection, not an assert (under -O the assert would fall into
            # the node-DELETION shortcut and corrupt the store -- blind-audit C3).
            # AdmissionRejected states "a real rejection" as a TYPE (ZT-P4-7).
            raise AdmissionRejected(
                f'{subject_id=} equals {object_id=}: self-referential edge would '
                f'create a cycle')

        triple = self.session.exec(
            select(EdgeV4)
            .where(EdgeV4.store_id == self.store_id)
            .where(EdgeV4.subject_id == object_id)
            .where(EdgeV4.object_id == subject_id)
        ).first()

        if triple is not None and triple.indirect_edge_count > 0:
            # AdmissionRejected: the reverse-reachability pre-check -- admitting this
            # edge would close a cycle. A correct refusal of the write.
            raise AdmissionRejected(
                f'{subject_id=} is reachable from {object_id=}, adding this edge would create a cycle')

        self._add_direct_edge_unsafe(subject_id, object_id, 1)

    def add_edge_by_id(self, subject_id: int, object_id: int) -> None:
        """Add a direct edge between two already-resolved node ids.

        Performs the same reverse-reachability cycle pre-check as add_edge, then
        the ref-counted +1 direct-edge update. The façade uses this so it never
        re-resolves names it already resolved. Reachability flips are recorded in
        the delta outbox (boolean spec §4); drain with index_v4.outbox helpers.
        """
        # Serialize the cycle check + ref-counted closure mutation against other writers
        # (held until commit): otherwise the check and the update are separate steps, so
        # concurrent adds can jointly create a cycle or lose count increments. The ids
        # may come from a PRE-lock resolution, so re-verify liveness inside the lock.
        self._lock_store()
        self._require_live_nodes(subject_id, object_id)
        self._add_edge_locked(subject_id, object_id)

    def _remove_edge_locked(self, subject_id: int, object_id: int) -> None:
        """Direct-edge existence check + ref-counted -1 update. Caller holds the
        store lock (same contract as ``_add_edge_locked``)."""
        if subject_id == object_id:
            # AdmissionRejected: the remove-side mirror of the self-edge cycle refusal.
            # Reachable from a user write (`remove_tuple('p','T','x','p','T','x')`
            # resolves both endpoints to the SAME node), and no such edge can ever have
            # existed -- so this is "removing what is not there", a correct refusal.
            raise AdmissionRejected(
                f'{subject_id=} equals {object_id=}: no self-referential edge can exist')

        triple = self.session.exec(
            select(Edge)
            .where(Edge.store_id == self.store_id)
            .where(Edge.subject_id == subject_id)
            .where(Edge.object_id == object_id)
        ).first()

        if triple is None or triple.direct_edge_count == 0:
            # AdmissionRejected: same family as 'Non-existent edge cannot be removed'
            # (that one is the node-resolution miss; this one is the edge-row miss).
            # Validity parity with the set engine's 'non-existent tuple cannot be
            # removed'.
            raise AdmissionRejected(
                f'{subject_id=} has no direct edge to {object_id=}, cannot remove nonexistent edge')

        self._add_direct_edge_unsafe(subject_id, object_id, -1)

    def remove_edge_by_id(self, subject_id: int, object_id: int) -> None:
        """Remove a direct edge between two already-resolved node ids (ref-counted -1)."""
        self._lock_store()   # serialize the ref-counted closure mutation (held until commit)
        self._require_live_nodes(subject_id, object_id)
        self._remove_edge_locked(subject_id, object_id)

    def check_reachable_by_id(self, subject_id: int, object_id: int) -> bool:
        """The edge point lookup only: is object reachable from subject?"""
        triple = self.session.exec(
            select(Edge)
            .where(Edge.store_id == self.store_id)
            .where(Edge.subject_id == subject_id)
            .where(Edge.object_id == object_id)
        ).first()

        return triple is not None and triple.indirect_edge_count > 0

    def direct_edge_exists_by_id(self, subject_id: int, object_id: int) -> bool:
        """Whether a *direct* edge row exists (used by the façade for idempotent bridges)."""
        triple = self.session.exec(
            select(Edge)
            .where(Edge.store_id == self.store_id)
            .where(Edge.subject_id == subject_id)
            .where(Edge.object_id == object_id)
        ).first()

        return triple is not None and triple.direct_edge_count > 0

    def add_edge(self, subject_predicate: str | EllipsisType, subject_type: str, subject_name: str, relation: str,
                 object_type: str, object_name: str) -> None:
        validate_write_identifiers(subject_predicate, subject_type, subject_name,
                                   relation, object_type, object_name)
        self._lock_store()   # lock BEFORE resolution: a concurrent remove_node in the
        # resolve-then-mutate gap would hand us stale ids (blind-audit C2)
        _subject = self.node(subject_predicate, subject_type, subject_name, create_if_missing=True)
        _object = self.node(relation, object_type, object_name, create_if_missing=True)
        # resolved under the lock: live by construction, no re-verification round trip
        self._add_edge_locked(_subject.id, _object.id)

    def remove_edge(self, subject_predicate: str | EllipsisType, subject_type: str, subject_name: str, relation: str,
                    object_type: str, object_name: str) -> None:
        validate_write_identifiers(subject_predicate, subject_type, subject_name,
                                   relation, object_type, object_name)
        self._lock_store()   # lock before resolution (blind-audit C2)
        try:
            _subject = self.node(subject_predicate, subject_type, subject_name, create_if_missing=False)
            _object = self.node(relation, object_type, object_name, create_if_missing=False)
        except KeyError as e:
            # AdmissionRejected: an endpoint the store never saw -- removing what is
            # not there is a correct refusal (validity parity with the set engine).
            raise AdmissionRejected('Non-existent edge cannot be removed') from e

        self._remove_edge_locked(_subject.id, _object.id)

    def remove_node(self, predicate: str | EllipsisType, entity_type: str, entity_name: str) -> None:
        validate_node_identifiers(predicate, entity_type, entity_name)
        self._lock_store()   # serialize node deletion + its closure fixups (held until commit)
        _node = self.node(predicate, entity_type, entity_name, create_if_missing=False)
        node_id = _node.id
        self._add_direct_edge_unsafe(node_id, node_id, -1)
        # Post-condition (defense in depth): the counting math must have retired every
        # edge row touching the node before the node row itself was deleted -- a
        # leftover here would be a dangling reference (SQLite does not enforce FKs by
        # default). Cheap targeted check; a hit means corrupted counts, so fail loudly
        # inside the transaction rather than persist ghosts.
        leftover = self.session.exec(
            select(EdgeV4).where(EdgeV4.store_id == self.store_id)
            .where((EdgeV4.subject_id == node_id) | (EdgeV4.object_id == node_id))
            .limit(1)
        ).first()
        # As `raise`, not `assert`: this is the last barrier between `remove_node` and a
        # dangling edge row, on a table with no enforced foreign keys -- and SQLite
        # rowid reuse can later repoint that row at an unrelated principal
        # (zero-trust review 2026-07-26, ZT-P1-2).
        if leftover is not None:
            raise InvariantViolation(
                f'remove_node left a dangling edge row {leftover} referencing deleted '
                f'node {node_id} -- path-count corruption')

    def check_reachable(self, subject_predicate: str | EllipsisType, subject_type: str, subject_name: str,
                        relation: str, object_type: str, object_name: str) -> bool:
        try:
            _subject = self.node(subject_predicate, subject_type, subject_name, create_if_missing=False)
            _object = self.node(relation, object_type, object_name, create_if_missing=False)
        except KeyError:
            return False

        return self.check_reachable_by_id(_subject.id, _object.id)

    def lookup_reachable(self, subject_id: int) -> set[int]:
        triples = self.session.exec(
            select(EdgeV4).where(EdgeV4.store_id == self.store_id).where(EdgeV4.subject_id == subject_id)
        ).all()
        return {t.object_id for t in triples if t.indirect_edge_count > 0}

    def lookup_reverse(self, object_id: int) -> set[int]:
        triples = self.session.exec(
            select(EdgeV4).where(EdgeV4.store_id == self.store_id).where(EdgeV4.object_id == object_id)
        ).all()
        return {t.subject_id for t in triples if t.indirect_edge_count > 0}
