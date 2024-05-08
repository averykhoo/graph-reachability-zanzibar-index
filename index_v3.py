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


class Edge(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    subject_id: int = Field(foreign_key="node.id", index=True)
    object_id: int = Field(foreign_key="node.id", index=True)
    direct_edge_count: int = Field(default=0)  # how many tuples were inserted
    indirect_edge_count: int = Field(default=0)
    ignored_count: int = Field(default=0)


engine = create_engine('sqlite:///database.db', echo=True)

SQLModel.metadata.create_all(engine)


def _add_db_edges_unsafe(subject_predicate: str | EllipsisType | None,
                         subject_id: int | None,
                         relation: str | None,
                         object_id: int | None,
                         direct_edge_count: int | None,
                         indirect_edge_count: int | None,
                         ):
    assert indirect_edge_count != 0
    assert subject_predicate != relation or subject_id != object_id

    with Session(engine) as session:
        _select = select(RelationalTriple)
        if subject_predicate is not None:
            _select = _select.where(RelationalTriple.subject_predicate == subject_predicate)
        if subject_id is not None:
            _select = _select.where(RelationalTriple.subject_id == subject_id)
        if relation is not None:
            _select = _select.where(RelationalTriple.relation == relation)
        if object_id is not None:
            _select = _select.where(RelationalTriple.object_id == object_id)

        triples = session.exec(_select).all()
        if not triples:
            if not direct_edge_count and not indirect_edge_count:  # both are zero or None
                return
            if subject_predicate is None or subject_id is None:
                return
            if relation is None or object_id is None:
                return
            session.add(RelationalTriple(subject_predicate=subject_predicate,
                                         subject_id=subject_id,
                                         relation=relation,
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
            session.add(triple)


def _add_edge_unsafe(subject_predicate: str | EllipsisType | None,
                     subject_id: int | None,
                     relation: str | None,
                     object_id: int | None,
                     multiplier: int | None,
                     ):
    # if multiplier is zero, there's probably a bug somewhere
    assert multiplier in {-1, 1}

    # we need to remove direct edge first to preserve the invariant
    if (subject_predicate != relation or subject_id != object_id) and multiplier < 0:
        _add_db_edges_unsafe(subject_predicate, subject_id, relation, object_id, multiplier, multiplier)
    else:
        raise NotImplementedError  # disable this for now because i need to remove the whole entity, not just a node

    # alternatively, remove the entire node from direct edges
    if subject_predicate == relation and subject_id == object_id:
        assert multiplier == -1
        _add_db_edges_unsafe(None, subject_id, None, None, None, 0)
        _add_db_edges_unsafe(None, None, None, object_id, None, 0)

    # get the reachable nodes
    reachable_from_node_from = MultiSet()
    reachable_from_node_to = MultiSet()
    with Session(engine) as session:
        triples_from = session.exec(select(RelationalTriple)
                                    .where(RelationalTriple.relation == subject_predicate)
                                    .where(RelationalTriple.object_id == subject_id)
                                    ).all()
        for triple in triples_from:
            reachable_from_node_from[triple.subject_predicate, triple.subject_id] = triple.indirect_edge_count
        triples_to = session.exec(select(RelationalTriple)
                                  .where(RelationalTriple.subject_predicate == relation)
                                  .where(RelationalTriple.subject_id == object_id)
                                  ).all()
        for triple in triples_to:
            reachable_from_node_to[triple.relation, triple.object_id] = triple.indirect_edge_count

    # ensure we're not creating a cycle
    assert reachable_from_node_from[relation, object_id] == 0, reachable_from_node_from
    assert reachable_from_node_to[subject_predicate, subject_id] == 0, reachable_from_node_to

    # add the indirect edges:
    for (_subject_predicate, _subject_id), from_count in reachable_from_node_from.items():
        for (_relation, _object_id), to_count in reachable_from_node_to.items():
            _add_edge_unsafe(_subject_predicate, _subject_id, _relation, _object_id, from_count * to_count * multiplier)

    # add the node_to's reachable nodes to node_from
    for (_subject_id, _relation), count in reachable_from_node_to.items():
        _add_edge_unsafe(subject_predicate, subject_id, _subject_id, _relation, count * multiplier)

    # make node_to reachable from all the nodes that can reach node_from
    for (_subject_predicate, _subject_id), count in reachable_from_node_from.items():
        _add_edge_unsafe(_subject_predicate, _subject_id, relation, object_id, count * multiplier)

    # add the direct edge last to preserve the invariant
    if (subject_predicate != relation or subject_id != object_id) and multiplier > 0:
        _add_db_edges_unsafe(subject_predicate, subject_id, relation, object_id, multiplier, multiplier)


def add_edge(subject_predicate, subject_id, relation, object_id):
    # sanity check
    assert subject_predicate != relation or subject_id != object_id

    with Session(engine) as session:
        triple = session.exec(select(RelationalTriple)
                              .where(RelationalTriple.subject_predicate == relation)
                              .where(RelationalTriple.subject_id == object_id)
                              .where(RelationalTriple.relation == subject_predicate)
                              .where(RelationalTriple.object_id == subject_id)
                              ).first()
        # ensure acyclic invariant holds
        if triple is not None and triple.indirect_edge_count > 0:
            raise ValueError(f'{subject_predicate=} {subject_id=} is reachable from {relation=} {object_id=}, '
                             f'adding this edge would create a cycle')

    _add_edge_unsafe(subject_predicate, subject_id, relation, object_id, 1)


def remove_edge(subject_predicate, subject_id, relation, object_id):
    # sanity check
    assert subject_predicate != relation or subject_id != object_id

    with Session(engine) as session:
        triple = session.exec(select(RelationalTriple)
                              .where(RelationalTriple.subject_predicate == subject_predicate)
                              .where(RelationalTriple.subject_id == subject_id)
                              .where(RelationalTriple.relation == relation)
                              .where(RelationalTriple.object_id == object_id)
                              ).first()
        # ensure acyclic invariant holds
        if triple is None or triple.direct_edge_count == 0:
            raise ValueError(f'{subject_predicate=} {subject_id=} has no direct edge to {relation=} {object_id=}, '
                             f'cannot remove nonexistent edge')

    _add_edge_unsafe(subject_predicate, subject_id, relation, object_id, -1)

# def remove_node(node: Node):
#     _add_edge_unsafe(node, node, -1)
#
#
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
