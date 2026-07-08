from types import EllipsisType
from sqlmodel import Session, select

from legacy.index_v1 import MultiSet
from zanzibar_utils_v1 import validate_write_identifiers, validate_node_identifiers
from .models import DeltaOutboxV1, EdgeV4, NodeV4, Edge, Node, StoreV4


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

    def _emit(self, subject_id: int, object_id: int, action: str) -> None:
        """Record a reachability flip in the outbox (boolean spec §4: deltas are rows
        inserted inside the writing transaction, never in-memory lists). Endpoint
        identities are denormalized at emission -- the nodes are alive here, but
        implicit-node GC may delete them before the cascade reads the row."""
        s = self.session.get(NodeV4, subject_id)
        o = self.session.get(NodeV4, object_id)
        self.session.add(DeltaOutboxV1(
            store_id=self.store_id, subject_node_id=subject_id, object_node_id=object_id,
            action=action,
            subject_type=s.type if s else '', subject_name=s.name if s else '',
            subject_predicate=s.predicate if s else '',
            object_type=o.type if o else '', object_name=o.name if o else '',
            object_predicate=o.predicate if o else ''))

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
        """
        self.session.exec(
            select(StoreV4).where(StoreV4.id == self.store_id).with_for_update()
        ).first()

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

    def _add_direct_edge_unsafe(self, subject_id: int, object_id: int, count: int) -> None:
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

        # Expand transitive paths
        for from_node_id, from_count in reachable_before_subject.items():
            for to_node_id, to_count in reachable_after_object.items():
                self._add_db_edges_unsafe(from_node_id, to_node_id, 0, from_count * to_count * count)

        for to_node_id, path_count in reachable_after_object.items():
            self._add_db_edges_unsafe(subject_id, to_node_id, 0, path_count * count)

        for from_node_id, path_count in reachable_before_subject.items():
            self._add_db_edges_unsafe(from_node_id, object_id, 0, path_count * count)

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
            for other_id, debit in neighbour_debits.items():
                _n = self.session.exec(
                    select(NodeV4).where(NodeV4.store_id == self.store_id)
                    .where(NodeV4.id == other_id)).first()
                if _n is None:
                    continue
                assert _n.reference_count - debit >= 0
                if _n.reference_count - debit == 0 and _n.implicit:
                    self.session.delete(_n)
                else:
                    _n.reference_count -= debit
                    self.session.add(_n)
            _node = self.session.exec(
                select(NodeV4).where(NodeV4.store_id == self.store_id).where(NodeV4.id == subject_id)).first()
            if _node:
                self.session.delete(_node)
        else:
            for node_id in (subject_id, object_id):
                _node = self.session.exec(
                    select(NodeV4).where(NodeV4.store_id == self.store_id).where(NodeV4.id == node_id)).first()
                if _node:
                    assert _node.reference_count + count >= 0
                    if _node.reference_count + count == 0 and _node.implicit:
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

        found = self.session.exec(
            select(NodeV4)
            .where(NodeV4.store_id == self.store_id)
            .where(NodeV4.predicate == predicate)
            .where(NodeV4.type == entity_type)
            .where(NodeV4.name == entity_name)
            .where(NodeV4.wildcard == wildcard)
        ).first()

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
        return _node

    def _require_live_nodes(self, *node_ids: int) -> None:
        """Both endpoints must still exist (checked INSIDE the store lock): a stale
        id from a pre-lock resolution racing a concurrent remove_node would otherwise
        insert a dangling edge -- and SQLite rowid reuse could later turn it into a
        phantom permission on an unrelated node (blind-audit C2)."""
        for nid in node_ids:
            row = self.session.exec(
                select(NodeV4).where(NodeV4.store_id == self.store_id)
                .where(NodeV4.id == nid)).first()
            if row is None:
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
