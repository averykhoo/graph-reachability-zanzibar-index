from types import EllipsisType

from sqlmodel import Field
from sqlmodel import SQLModel
from sqlmodel import Session
from sqlmodel import create_engine
from sqlmodel import select

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


engine = create_engine('sqlite:///database.db')  # , echo=True)

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

        # delete the entire node, ignoring state of Node.implicit flag
        if subject_id == object_id:
            _node = session.exec(select(Node)
                                 .where(Node.id == subject_id)
                                 ).first()
            assert _node is not None
            session.delete(_node)

        # add reference counts
        else:
            for node_id in (subject_id, object_id):
                _node = session.exec(select(Node)
                                     .where(Node.id == node_id)
                                     ).first()
                assert _node is not None
                assert _node.reference_count + multiplier >= 0
                if _node.reference_count + multiplier == 0 and _node.implicit:
                    session.delete(_node)
                else:
                    _node.reference_count += multiplier
                    session.add(_node)

        # commit transaction
        session.commit()


def node(predicate: str | EllipsisType,
         entity_type: str,
         entity_name: str,
         *,
         implicit: bool | None = None,
         create_if_missing: bool = True,
         ):
    if predicate is Ellipsis:
        predicate = '...'
    with Session(engine) as session:
        found = session.exec(select(Node)
                             .where(Node.predicate == predicate)
                             .where(Node.type == entity_type)
                             .where(Node.name == entity_name)
                             ).first()
        if found is not None:
            if implicit is not None and found.implicit != implicit:
                found.implicit = False
                session.add(found)
                session.commit()
                session.refresh(found)
            return found
        if not create_if_missing:
            raise KeyError(f'Node missing: {predicate=}, {entity_type=}, {entity_name=}')
        _node = Node(predicate=predicate, type=entity_type, name=entity_name, implicit=implicit)
        session.add(_node)
        session.commit()
        session.refresh(_node)
        return _node


def add_edge(subject_predicate: str | EllipsisType,
             subject_type: str,
             subject_name: str,
             relation: str,
             object_type: str,
             object_name: str,
             ):
    _subject = node(subject_predicate, subject_type, subject_name)
    _object = node(relation, object_type, object_name)

    # sanity check
    assert _subject.id != _object.id

    with Session(engine) as session:
        triple = session.exec(select(Edge)
                              .where(Edge.subject_id == _object.id)
                              .where(Edge.object_id == _subject.id)
                              ).first()
        # ensure acyclic invariant holds
        if triple is not None and triple.indirect_edge_count > 0:
            raise ValueError(f'{_subject=} is reachable from {_object=}, '
                             f'adding this edge would create a cycle')

    _add_direct_edge_unsafe(_subject.id, _object.id, 1)


def remove_edge(subject_predicate: str | EllipsisType,
                subject_type: str,
                subject_name: str,
                relation: str,
                object_type: str,
                object_name: str,
                ):
    try:
        _subject = node(subject_predicate, subject_type, subject_name, create_if_missing=False)
        _object = node(relation, object_type, object_name, create_if_missing=False)
    except KeyError as e:
        raise ValueError('Non-existent edge cannot be removed') from e

    # sanity check
    assert _subject.id != _object.id

    with Session(engine) as session:
        triple = session.exec(select(Edge)
                              .where(Edge.subject_id == _subject.id)
                              .where(Edge.object_id == _object.id)
                              ).first()
        # ensure acyclic invariant holds
        if triple is None or triple.direct_edge_count == 0:
            raise ValueError(f'{_subject=} has no direct edge to {_object=}, '
                             f'cannot remove nonexistent edge')

    _add_direct_edge_unsafe(_subject.id, _object.id, -1)


def remove_node(predicate: str | EllipsisType,
                entity_type: str,
                entity_name: str,
                ):
    _node = node(predicate, entity_type, entity_name, create_if_missing=False)  # raises KeyError if missing
    _add_direct_edge_unsafe(_node.id, _node.id, -1)


def check_reachable(subject_predicate: str | EllipsisType,
                    subject_type: str,
                    subject_name: str,
                    relation: str,
                    object_type: str,
                    object_name: str,
                    ):
    # TODO: does not yet handle subject:* relations
    try:
        _subject = node(subject_predicate, subject_type, subject_name, create_if_missing=False)
        _object = node(relation, object_type, object_name, create_if_missing=False)
    except KeyError:
        return False

    # sanity check
    assert _subject.id != _object.id

    with Session(engine) as session:
        triple = session.exec(select(Edge)
                              .where(Edge.subject_id == _subject.id)
                              .where(Edge.object_id == _object.id)
                              ).first()
        # ensure acyclic invariant holds
        return triple is not None and triple.indirect_edge_count > 0


def lookup_reachable(subject_id: int):
    # TODO: need some sort of sql table join to select object type
    # TODO: return nodes or something more useful instead of node ids
    with Session(engine) as session:
        triples = session.exec(select(Edge)
                               .where(Edge.subject_id == subject_id)
                               ).all()

        object_ids = set()
        for triple in triples:
            if triple.indirect_edge_count > 0:
                assert triple.object_id != subject_id  # invariant
                object_ids.add(triple.object_id)

        return object_ids


def lookup_reverse(object_id: int):
    # TODO: need some sort of sql table join to select subject type
    # TODO: return nodes or something more useful instead of node ids
    with Session(engine) as session:
        triples = session.exec(select(Edge)
                               .where(Edge.object_id == object_id)
                               ).all()

        subject_ids = set()
        for triple in triples:
            if triple.indirect_edge_count > 0:
                assert triple.subject_id != object_id  # invariant
                subject_ids.add(triple.subject_id)

        return subject_ids


if __name__ == '__main__':
    add_edge('writer', 'document', 'abc.xyz', 'reader', 'document', 'abc.xyz')
    add_edge(..., 'user', 'alice', 'reader', 'document', 'abc.xyz')
    add_edge(..., 'user', 'alice', 'member', 'group', 'g1')
    add_edge(..., 'user', 'bob', 'member', 'group', 'g1')
    add_edge(..., 'user', 'bob', 'member', 'group', 'g2')
    add_edge('member', 'group', 'g1', 'writer', 'document', 'abc.xyz')
    add_edge('member', 'group', 'g2', 'reader', 'document', 'abc.xyz')
    add_edge('member', 'group', 'g2', 'writer', 'document', 'qwerty.pdf')

    print(f"{check_reachable(..., 'user', 'alice', 'reader', 'document', 'abc.xyz')=}")
    print(f"{check_reachable(..., 'user', 'alice', 'writer', 'document', 'abc.xyz')=}")
    print(f"{check_reachable(..., 'user', 'alice', 'writer', 'document', 'qwerty.pdf')=}")
    print(f"{lookup_reachable(node(..., 'user', 'alice', create_if_missing=False).id)=}")

    print(f"{check_reachable(..., 'user', 'bob', 'reader', 'document', 'abc.xyz')=}")
    print(f"{check_reachable(..., 'user', 'bob', 'writer', 'document', 'abc.xyz')=}")
    print(f"{check_reachable(..., 'user', 'bob', 'writer', 'document', 'qwerty.pdf')=}")
    print(f"{lookup_reachable(node(..., 'user', 'bob', create_if_missing=False).id)=}")

    print(f"{lookup_reverse(node('reader', 'document', 'abc.xyz', create_if_missing=False).id)=}")
