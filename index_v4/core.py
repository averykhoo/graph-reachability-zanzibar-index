from contextlib import contextmanager
from types import EllipsisType
from sqlalchemy import insert, tuple_
from sqlmodel import Session, select

from legacy.index_v1 import MultiSet
from zanzibar_utils_v1 import validate_write_identifiers, validate_node_identifiers
from .models import DeltaOutboxV1, EdgeV4, NodeV4, Edge, Node, StoreV4

# Per-batch node-resolution cache sentinels (perf N15). ``_UNCACHED`` distinguishes
# "key absent from the cache" (do the DB lookup) from ``_MISSING`` ("known-absent this
# batch" -- a negative cache entry). Both are private module singletons.
_UNCACHED = object()
_MISSING = object()


class ReachabilityIndex:
    """
    Stateful interface to interact with the transitive closure DAG.
    Operates inside a provided Session to allow multi-edge transactional batching.

    Concurrency: every write funnels through ``_lock_store`` (a ``FOR UPDATE`` row lock on
    the store row) so that a whole logical write -- the check-then-act cycle test *and* the
    read-modify-write ref-count updates across the affected closure region -- is atomic
    with respect to other writers to the same store. Without it, two concurrent writers on
    an MVCC backend (PostgreSQL/MySQL, READ COMMITTED) would (a) lose ref-count increments
    on any shared edge and (b) be able to each pass the cycle check yet jointly create a
    cycle. See ``_lock_store`` for why the lock is at store rather than per-edge granularity.
    """

    def __init__(self, session: Session, store_id: str):
        self.session = session
        self.store_id = store_id
        # When True, direct-edge writes flag their rows EdgeV4.derived (boolean spec
        # §4/I5). Only the delta processor's façade path sets this, around its own
        # writes into derived-public families.
        self._writing_derived = False
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

        On PostgreSQL/MySQL this blocks other writers to the store until this transaction
        commits/rolls back. On SQLite ``with_for_update()`` renders to nothing (the engine
        already takes a database-level write lock), so tests are unaffected. A missing
        store row simply yields no lock (harmless).

        Transaction-scoped memo (perf P12a): the lock is held for the whole transaction,
        so re-issuing the ``SELECT ... FOR UPDATE`` on a row this transaction already
        locked is a pure no-op round trip. We remember the ``SessionTransaction`` object
        under which the lock was taken and short-circuit while it is still live. Keying
        on the object *identity* (not a boolean) is what makes this rollback-safe:
        ``Session.get_transaction()`` returns a fresh ``SessionTransaction`` after every
        commit/rollback and ``None`` before autobegin, so the memo can never match into a
        retried transaction -- a retry re-takes the real lock, which is exactly the
        lost-update guard this method exists to provide. (No savepoints/``begin_nested``
        in the repo, so root-transaction identity is the whole story.)
        """
        txn = self.session.get_transaction()
        if txn is not None and txn is self._locked_txn:
            return
        self.session.exec(
            select(StoreV4).where(StoreV4.id == self.store_id).with_for_update()
        ).first()
        # Capture AFTER the select: the lock SELECT itself may have autobegun the
        # transaction, so ``get_transaction()`` was potentially None above.
        self._locked_txn = self.session.get_transaction()

    def _add_db_edges_unsafe(
            self,
            subject_id: int | None,
            object_id: int | None,
            direct_count: int | None,
            indirect_count: int | None
    ) -> None:

        assert subject_id is not None or object_id is not None
        assert subject_id != object_id
        assert direct_count != 0 or indirect_count != 0

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

            assert (indirect_count or 0) >= (direct_count or 0)
            assert (indirect_count or 0) > 0

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

            assert triple.indirect_edge_count >= triple.direct_edge_count
            assert triple.indirect_edge_count > 0

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
                assert indirect_delta > 0
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

            assert triple.indirect_edge_count >= triple.direct_edge_count
            assert triple.indirect_edge_count > 0

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
        assert count in {-1, 1}

        # Remove direct edge first to preserve invariant on subtraction
        if subject_id != object_id and count < 0:
            self._add_db_edges_unsafe(subject_id, object_id, count, count)

        # Node removal shortcut: unsets direct edge counts globally
        if subject_id == object_id:
            if count != -1:
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

        assert reachable_before_subject[object_id] == 0, "Cycle detected in backward path"
        assert reachable_after_object[subject_id] == 0, "Cycle detected in forward path"

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
                assert _n.reference_count - debit >= 0
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
                    assert _node.reference_count + count >= 0
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
                raise ValueError(f'node id {nid} no longer exists (concurrent removal?)')

    def _add_edge_locked(self, subject_id: int, object_id: int) -> None:
        """Cycle pre-check + ref-counted +1 direct-edge update. Caller holds the
        store lock and has established both ids are live (resolution under the lock
        counts: every writer serializes on it, so no concurrent removal can land)."""
        if subject_id == object_id:
            # a tuple whose subject node IS its object node is the trivial cycle;
            # a real rejection, not an assert (under -O the assert would fall into
            # the node-DELETION shortcut and corrupt the store -- blind-audit C3)
            raise ValueError(
                f'{subject_id=} equals {object_id=}: self-referential edge would '
                f'create a cycle')

        triple = self.session.exec(
            select(EdgeV4)
            .where(EdgeV4.store_id == self.store_id)
            .where(EdgeV4.subject_id == object_id)
            .where(EdgeV4.object_id == subject_id)
        ).first()

        if triple is not None and triple.indirect_edge_count > 0:
            raise ValueError(
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
            raise ValueError(
                f'{subject_id=} equals {object_id=}: no self-referential edge can exist')

        triple = self.session.exec(
            select(Edge)
            .where(Edge.store_id == self.store_id)
            .where(Edge.subject_id == subject_id)
            .where(Edge.object_id == object_id)
        ).first()

        if triple is None or triple.direct_edge_count == 0:
            raise ValueError(
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
            raise ValueError('Non-existent edge cannot be removed') from e

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
        assert leftover is None, (
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
