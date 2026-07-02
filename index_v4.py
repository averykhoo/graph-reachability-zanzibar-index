import time
from typing import Generator, NamedTuple
from types import EllipsisType

from sqlalchemy.orm import RelationshipProperty
from sqlmodel import Field, Relationship, SQLModel, Session, UniqueConstraint, select, create_engine

# Using the MultiSet from v1 as per the original design
from index_v1 import MultiSet


class PermissionDelta(NamedTuple):
    """Represents a discrete change in a computed permission."""
    store_id: str
    subject_id: int
    object_id: int
    action: str  # "ADDED" or "REMOVED"


class StoreV4(SQLModel, table=True):
    """
    Represents a discrete graph index environment (e.g., a specific Tenant or App).
    Allows attaching arbitrary metadata to the graph boundary.
    """
    __tablename__ = "store_v4"
    __table_args__ = {'extend_existing': True}

    id: str = Field(primary_key=True)
    description: str = Field(default="")
    created_at: float = Field(default_factory=time.time)


class NodeV4(SQLModel, table=True):
    __tablename__ = "node_v4"
    __table_args__ = (
        UniqueConstraint('store_id', 'predicate', 'type', 'name', name='node_v4_unique_constraint'),
        {'extend_existing': True},
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: str = Field(foreign_key="store_v4.id", index=True)
    predicate: str = Field(index=True)
    type: str = Field(index=True)
    name: str = Field(index=True)
    implicit: bool = Field(default=True)
    reference_count: int = Field(default=0)

    store: StoreV4 = Relationship()

    @property
    def predicate_or_ellipsis(self) -> str | EllipsisType:
        return Ellipsis if self.predicate == '...' else self.predicate


class EdgeV4(SQLModel, table=True):
    __tablename__ = "edge_v4"
    __table_args__ = (
        UniqueConstraint('store_id', 'subject_id', 'object_id', name='edge_v4_unique_constraint'),
        {'extend_existing': True},
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: str = Field(foreign_key="store_v4.id", index=True)
    subject_id: int = Field(foreign_key="node_v4.id", index=True)
    object_id: int = Field(foreign_key="node_v4.id", index=True)
    direct_edge_count: int = Field(default=0)
    indirect_edge_count: int = Field(default=0)

    store: StoreV4 = Relationship()
    subject: NodeV4 = Relationship(sa_relationship=RelationshipProperty(foreign_keys='[EdgeV4.subject_id]'))
    object: NodeV4 = Relationship(sa_relationship=RelationshipProperty(foreign_keys='[EdgeV4.object_id]'))

Node = NodeV4
Edge = EdgeV4
Store = StoreV4


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
             implicit: bool | None = None) -> NodeV4:
        if predicate is Ellipsis:
            predicate = '...'

        found = self.session.exec(
            select(NodeV4)
            .where(NodeV4.store_id == self.store_id)
            .where(NodeV4.predicate == predicate)
            .where(NodeV4.type == entity_type)
            .where(NodeV4.name == entity_name)
        ).first()

        if found is not None:
            if implicit is not None and found.implicit != implicit:
                found.implicit = False
                self.session.add(found)
            return found

        if not create_if_missing:
            raise KeyError(f'Node missing: {predicate=}, {entity_type=}, {entity_name=}')

        _node = NodeV4(store_id=self.store_id, predicate=predicate, type=entity_type, name=entity_name, implicit=implicit)
        self.session.add(_node)
        self.session.flush()  # flush to get auto-increment id immediately without committing transaction
        return _node

    def add_edge(self, subject_predicate: str | EllipsisType, subject_type: str, subject_name: str, relation: str,
                 object_type: str, object_name: str) -> list[PermissionDelta]:
        _subject = self.node(subject_predicate, subject_type, subject_name, create_if_missing=True)
        _object = self.node(relation, object_type, object_name, create_if_missing=True)

        assert _subject.id != _object.id

        triple = self.session.exec(
            select(EdgeV4)
            .where(EdgeV4.store_id == self.store_id)
            .where(EdgeV4.subject_id == _object.id)
            .where(EdgeV4.object_id == _subject.id)
        ).first()

        if triple is not None and triple.indirect_edge_count > 0:
            raise ValueError(f'{_subject=} is reachable from {_object=}, adding this edge would create a cycle')

        return self._add_direct_edge_unsafe(_subject.id, _object.id, 1)

    def remove_edge(self, subject_predicate: str | EllipsisType, subject_type: str, subject_name: str, relation: str,
                    object_type: str, object_name: str) -> list[PermissionDelta]:
        try:
            _subject = self.node(subject_predicate, subject_type, subject_name, create_if_missing=False)
            _object = self.node(relation, object_type, object_name, create_if_missing=False)
        except KeyError as e:
            raise ValueError('Non-existent edge cannot be removed') from e

        assert _subject.id != _object.id

        triple = self.session.exec(
            select(Edge)
            .where(Edge.store_id == self.store_id)
            .where(Edge.subject_id == _subject.id)
            .where(Edge.object_id == _object.id)
        ).first()

        if triple is None or triple.direct_edge_count == 0:
            raise ValueError(f'{_subject=} has no direct edge to {_object=}, cannot remove nonexistent edge')

        return self._add_direct_edge_unsafe(_subject.id, _object.id, -1)

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

        assert _subject.id != _object.id

        triple = self.session.exec(
            select(Edge)
            .where(Edge.store_id == self.store_id)
            .where(Edge.subject_id == _subject.id)
            .where(Edge.object_id == _object.id)
        ).first()

        return triple is not None and triple.indirect_edge_count > 0

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


if __name__ == '__main__':
    # Usage Example End-to-End Test
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Create a new graph boundary (Store)
        store = Store(id="tenant_a", description="GitHub Repository Index")
        session.add(store)
        session.commit()

    with Session(engine) as session:
        # Initialize index targeting that store
        index = ReachabilityIndex(session, store_id="tenant_a")

        # Create relations (Collect Deltas)
        deltas = []
        deltas.extend(index.add_edge(..., 'user', 'alice', 'member', 'group', 'g1'))
        deltas.extend(index.add_edge('member', 'group', 'g1', 'reader', 'document', 'abc.txt'))

        # Commit transaction
        session.commit()

        print("--- PERMISSION DELTAS GENERATED ---")
        for d in deltas:
            print(d)

        print("\n--- REACHABILITY CHECKS ---")
        print("Alice can read abc.txt?", index.check_reachable(..., 'user', 'alice', 'reader', 'document', 'abc.txt'))
        print("Bob can read abc.txt?", index.check_reachable(..., 'user', 'bob', 'reader', 'document', 'abc.txt'))