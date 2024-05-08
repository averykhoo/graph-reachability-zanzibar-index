from types import EllipsisType

from sqlmodel import SQLModel, Field, create_engine, Session, select

from index_v1 import MultiSet


class Node(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    predicate: str = Field(index=True)
    type: str = Field(index=True)
    name: str = Field(index=True)
    implicit: bool = Field(default=True)  # if implicit, should be auto-deleted once all referencing tuples are deleted
    reference_count: int = Field(default=0)

    @property
    def predicate_or_ellipsis(self) -> str | EllipsisType:
        return Ellipsis if self.predicate == '...' else self.predicate


class Edge(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    subject_id: int = Field(foreign_key="node.id", index=True)
    object_id: int = Field(foreign_key="node.id", index=True)
    direct_edge_count: int = Field(default=0)  # how many tuples were inserted
    indirect_edge_count: int = Field(default=0)


engine = create_engine('sqlite:///database.db', echo=True)

SQLModel.metadata.create_all(engine)


def _add_db_edges_unsafe(session: Session,
                         subject_id: int | None,
                         object_id: int | None,
                         direct_edge_count: int | None,
                         indirect_edge_count: int | None,
                         ):
    """

    :param subject_id:
    :param object_id:
    :param direct_edge_count: if `None`, sets edge count to 0
    :param indirect_edge_count: if `None`, sets edge count to 0
    :return:
    """
    assert subject_id is not None or object_id is not None
    assert subject_id != object_id
    assert direct_edge_count != 0 or indirect_edge_count != 0
    if indirect_edge_count is None:
        assert direct_edge_count is None
    if direct_edge_count:
        # only used in this way for now
        assert indirect_edge_count == direct_edge_count

    _select = select(Edge)
    if subject_id is not None:
        _select = _select.where(Edge.subject_id == subject_id)
    if object_id is not None:
        _select = _select.where(Edge.object_id == object_id)

    triples = session.exec(_select).all()
    if not triples:
        if not direct_edge_count and not indirect_edge_count:  # both are zero or None
            return
        if subject_id is None:
            return
        if object_id is None:
            return
        assert (indirect_edge_count or 0) >= (direct_edge_count or 0)
        assert (indirect_edge_count or 0) > 0
        session.add(Edge(subject_id=subject_id,
                         object_id=object_id,
                         direct_edge_count=direct_edge_count or 0,
                         indirect_edge_count=indirect_edge_count or 0,
                         ))
        return

    for triple in triples:
        if direct_edge_count is None or triple.direct_edge_count + direct_edge_count == 0:
            if indirect_edge_count is None or triple.indirect_edge_count + indirect_edge_count == 0:
                session.delete(triple)
                continue
        if direct_edge_count is None:
            triple.direct_edge_count = 0
        else:
            triple.direct_edge_count += direct_edge_count
            assert triple.direct_edge_count >= 0
        if indirect_edge_count is None:
            triple.indirect_edge_count = 0
        else:
            triple.indirect_edge_count += indirect_edge_count
            assert triple.direct_edge_count >= 0
        assert triple.indirect_edge_count >= triple.direct_edge_count
        assert triple.indirect_edge_count > 0  # if this is zero, this tuple should be deleted
        session.add(triple)


def _add_direct_edge_unsafe(subject_id: int,
                            object_id: int,
                            multiplier: int,
                            ):
    # if multiplier is zero, there's probably a bug somewhere
    # at least for now, we only ever add or remove a single edge at a time
    assert multiplier in {-1, 1}

    # do this all in a single transaction
    with Session(engine) as session:

        # we need to remove direct edge first to preserve the invariant
        if subject_id != object_id and multiplier < 0:
            _add_db_edges_unsafe(session, subject_id, object_id, multiplier, multiplier)

        # alternatively, remove the entire node from direct edges
        if subject_id == object_id:
            assert multiplier == -1
            _add_db_edges_unsafe(session, subject_id, None, None, 0)
            _add_db_edges_unsafe(session, None, object_id, None, 0)

        # get the reachable nodes
        reachable_before_subject = MultiSet()
        reachable_after_object = MultiSet()

        triples_from = session.exec(select(Edge)
                                    .where(Edge.object_id == subject_id)
                                    ).all()
        for triple in triples_from:
            reachable_before_subject[triple.subject_id] = triple.indirect_edge_count
        triples_to = session.exec(select(Edge)
                                  .where(Edge.subject_id == object_id)
                                  ).all()
        for triple in triples_to:
            reachable_after_object[triple.object_id] = triple.indirect_edge_count

    # ensure we're not creating a cycle
    assert reachable_before_subject[object_id] == 0, reachable_before_subject
    assert reachable_after_object[subject_id] == 0, reachable_after_object

    # add the indirect edges:
    for from_node_id, from_count in reachable_before_subject.items():
        for to_node_id, to_count in reachable_after_object.items():
            _add_db_edges_unsafe(session, from_node_id, to_node_id, 0, from_count * to_count * multiplier)

    # add the object's reachable nodes to subject
    for to_node_id, count in reachable_after_object.items():
        _add_db_edges_unsafe(session, subject_id, to_node_id, 0, count * multiplier)

    # make object reachable from all the nodes that can reach subject
    for from_node_id, count in reachable_before_subject.items():
        _add_db_edges_unsafe(session, from_node_id, object_id, 0, count * multiplier)

    # add the direct edge last to preserve the invariant
    if subject_id != object_id and multiplier > 0:
        _add_db_edges_unsafe(session, subject_id, object_id, multiplier, multiplier)


def add_edge(subject_id, object_id):
    # sanity check
    assert subject_id != object_id

    with Session(engine) as session:
        triple = session.exec(select(Edge)
                              .where(Edge.subject_id == object_id)
                              .where(Edge.object_id == subject_id)
                              ).first()
        # ensure acyclic invariant holds
        if triple is not None and triple.indirect_edge_count > 0:
            raise ValueError(f'{subject_id=} is reachable from {object_id=}, '
                             f'adding this edge would create a cycle')

    _add_direct_edge_unsafe(subject_id, object_id, 1)


def remove_edge(subject_id, object_id):
    # sanity check
    assert subject_id != object_id

    with Session(engine) as session:
        triple = session.exec(select(Edge)
                              .where(Edge.subject_id == subject_id)
                              .where(Edge.object_id == object_id)
                              ).first()
        # ensure acyclic invariant holds
        if triple is None or triple.direct_edge_count == 0:
            raise ValueError(f'{subject_id=} has no direct edge to {object_id=}, '
                             f'cannot remove nonexistent edge')

    _add_direct_edge_unsafe(subject_id, object_id, -1)


def remove_node(node_id: int):
    # NOTE: this removes a node, not an entity
    # removing an entity may require removing multiple nodes
    _add_direct_edge_unsafe(node_id, node_id, -1)

# def check_reachable(node_from: Node, node_to: Node):
#     # probably slightly faster than using the forward index
#     return node_from in inverted_index_paths.get(node_to, set())
#
#
# def lookup_reachable(node_from: Node):
#     return list(index_paths_counts.get(node_from, MultiSet()).keys())
#
#
# def lookup_reverse(node_to: Node):
#     return list(inverted_index_paths.get(node_to))
#
#
# if __name__ == '__main__':
#     idx = random_test(['ab', 'bc', 'bd', 'ac', 'cd'])
#     print(idx.index_paths_counts)
#     print(idx.inverted_index_paths)
#     print(idx.direct_edge_counts)
#     idx.remove_node(Node('d'))
#     print(idx.index_paths_counts)
#     print(idx.inverted_index_paths)
#     print(idx.direct_edge_counts)
