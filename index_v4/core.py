from types import EllipsisType
from sqlmodel import Session, select

from index_v1 import MultiSet
from .models import EdgeV4, NodeV4, PermissionDelta, Edge, Node


class ReachabilityIndex:
    """
    Stateful interface to interact with the transitive closure DAG.
    Operates inside a provided Session to allow multi-edge transactional batching.
    """

    def __init__(self, session: Session, store_id: str):
        self.session = session
        self.store_id = store_id

    def _add_db_edges_unsafe(
            self,
            subject_id: int | None,
            object_id: int | None,
            direct_count: int | None,
            indirect_count: int | None
    ) -> list[PermissionDelta]:

        assert subject_id is not None or object_id is not None
        assert subject_id != object_id
        assert direct_count != 0 or indirect_count != 0

        deltas = []
        _select = select(EdgeV4).where(EdgeV4.store_id == self.store_id)
        if subject_id is not None:
            _select = _select.where(EdgeV4.subject_id == subject_id)
        if object_id is not None:
            _select = _select.where(EdgeV4.object_id == object_id)

        triples = self.session.exec(_select).all()

        # Handle Brand New Edges
        if not triples:
            if not direct_count and not indirect_count:
                return []
            if subject_id is None or object_id is None:
                return []

            assert (indirect_count or 0) >= (direct_count or 0)
            assert (indirect_count or 0) > 0

            edge = EdgeV4(
                store_id=self.store_id,
                subject_id=subject_id,
                object_id=object_id,
                direct_edge_count=direct_count or 0,
                indirect_edge_count=indirect_count or 0
            )
            self.session.add(edge)
            deltas.append(PermissionDelta(self.store_id, subject_id, object_id, "ADDED"))
            return deltas

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
                deltas.append(PermissionDelta(self.store_id, triple.subject_id, triple.object_id, "REMOVED"))
                continue

            triple.direct_edge_count = new_direct
            triple.indirect_edge_count = new_indirect

            assert triple.indirect_edge_count >= triple.direct_edge_count
            assert triple.indirect_edge_count > 0

            self.session.add(triple)

            if old_indirect == 0 and new_indirect > 0:
                deltas.append(PermissionDelta(self.store_id, triple.subject_id, triple.object_id, "ADDED"))

        return deltas

    def _add_direct_edge_unsafe(self, subject_id: int, object_id: int, count: int) -> list[PermissionDelta]:
        assert count in {-1, 1}
        deltas = []

        # Remove direct edge first to preserve invariant on subtraction
        if subject_id != object_id and count < 0:
            deltas.extend(self._add_db_edges_unsafe(subject_id, object_id, count, count))

        # Node removal shortcut: unsets direct edge counts globally
        if subject_id == object_id:
            assert count == -1
            deltas.extend(self._add_db_edges_unsafe(subject_id, None, None, 0))
            deltas.extend(self._add_db_edges_unsafe(None, object_id, None, 0))

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
                deltas.extend(self._add_db_edges_unsafe(from_node_id, to_node_id, 0, from_count * to_count * count))

        for to_node_id, path_count in reachable_after_object.items():
            deltas.extend(self._add_db_edges_unsafe(subject_id, to_node_id, 0, path_count * count))

        for from_node_id, path_count in reachable_before_subject.items():
            deltas.extend(self._add_db_edges_unsafe(from_node_id, object_id, 0, path_count * count))

        # Add the direct edge last to preserve invariants on addition
        if subject_id != object_id and count > 0:
            deltas.extend(self._add_db_edges_unsafe(subject_id, object_id, count, count))

        # Handle logical Node deletion
        if subject_id == object_id:
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

        return deltas

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
            if implicit is not None and found.implicit != implicit:
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

    def add_edge_by_id(self, subject_id: int, object_id: int) -> list[PermissionDelta]:
        """Add a direct edge between two already-resolved node ids.

        Performs the same reverse-reachability cycle pre-check as add_edge, then
        the ref-counted +1 direct-edge update. The façade uses this so it never
        re-resolves names it already resolved.
        """
        assert subject_id != object_id

        triple = self.session.exec(
            select(EdgeV4)
            .where(EdgeV4.store_id == self.store_id)
            .where(EdgeV4.subject_id == object_id)
            .where(EdgeV4.object_id == subject_id)
        ).first()

        if triple is not None and triple.indirect_edge_count > 0:
            raise ValueError(
                f'{subject_id=} is reachable from {object_id=}, adding this edge would create a cycle')

        return self._add_direct_edge_unsafe(subject_id, object_id, 1)

    def remove_edge_by_id(self, subject_id: int, object_id: int) -> list[PermissionDelta]:
        """Remove a direct edge between two already-resolved node ids (ref-counted -1)."""
        assert subject_id != object_id

        triple = self.session.exec(
            select(Edge)
            .where(Edge.store_id == self.store_id)
            .where(Edge.subject_id == subject_id)
            .where(Edge.object_id == object_id)
        ).first()

        if triple is None or triple.direct_edge_count == 0:
            raise ValueError(
                f'{subject_id=} has no direct edge to {object_id=}, cannot remove nonexistent edge')

        return self._add_direct_edge_unsafe(subject_id, object_id, -1)

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
                 object_type: str, object_name: str) -> list[PermissionDelta]:
        _subject = self.node(subject_predicate, subject_type, subject_name, create_if_missing=True)
        _object = self.node(relation, object_type, object_name, create_if_missing=True)
        return self.add_edge_by_id(_subject.id, _object.id)

    def remove_edge(self, subject_predicate: str | EllipsisType, subject_type: str, subject_name: str, relation: str,
                    object_type: str, object_name: str) -> list[PermissionDelta]:
        try:
            _subject = self.node(subject_predicate, subject_type, subject_name, create_if_missing=False)
            _object = self.node(relation, object_type, object_name, create_if_missing=False)
        except KeyError as e:
            raise ValueError('Non-existent edge cannot be removed') from e

        return self.remove_edge_by_id(_subject.id, _object.id)

    def remove_node(self, predicate: str | EllipsisType, entity_type: str, entity_name: str) -> list[PermissionDelta]:
        _node = self.node(predicate, entity_type, entity_name, create_if_missing=False)
        return self._add_direct_edge_unsafe(_node.id, _node.id, -1)

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
