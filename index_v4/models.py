import time
from typing import NamedTuple
from types import EllipsisType

from sqlalchemy.orm import RelationshipProperty
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


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
        UniqueConstraint('store_id', 'predicate', 'type', 'name', 'wildcard',
                         name='node_v4_unique_constraint'),
        {'extend_existing': True},
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: str = Field(foreign_key="store_v4.id", index=True)
    predicate: str = Field(index=True)
    type: str = Field(index=True)
    name: str = Field(index=True)
    # '' for concrete nodes, 'any' or 'all' for split wildcard nodes (spec §1.2/§1.3).
    # Empty string (NOT NULL) is deliberate: SQLite treats NULLs as distinct in a
    # unique constraint, which would silently permit duplicate concrete nodes.
    wildcard: str = Field(default='', index=True)
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
    # True iff the direct edge was written by the delta processor into a derived-public
    # family (boolean spec §4/I5). Exclusivity makes this equivalent to "direct edge on
    # a derived-public family"; the flag makes the invariant checkable per row.
    derived: bool = Field(default=False)

    store: StoreV4 = Relationship()
    subject: NodeV4 = Relationship(sa_relationship=RelationshipProperty(foreign_keys='[EdgeV4.subject_id]'))
    object: NodeV4 = Relationship(sa_relationship=RelationshipProperty(foreign_keys='[EdgeV4.object_id]'))


class ResidueV1(SQLModel, table=True):
    """Persisted symbolic wildcard state per (object node, derived relation): the
    ``(stars, neg)`` record `check` consults alongside the edge probe (boolean spec §4).

    ``object_node_id`` is the derived relation's public object node, whose identity
    already encodes the relation; ``relation`` is denormalized for ``lookup()``'s
    by-relation residue scan. ``stars``/``neg`` are JSON (list of [type, predicate]
    shapes / list of concrete subject node ids) -- layout adaptable per spec §4;
    cursor-free, one row per object. Empty residues are deleted, never stored.
    """
    __tablename__ = "residue_v1"
    __table_args__ = (
        UniqueConstraint('store_id', 'object_node_id', name='residue_v1_unique'),
        {'extend_existing': True},
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: str = Field(index=True)
    object_node_id: int = Field(foreign_key="node_v4.id", index=True)
    relation: str = Field(index=True)
    stars: str = Field(default='[]')     # JSON: [[type, predicate], ...]
    neg: str = Field(default='[]')       # JSON: [subject_node_id, ...]
    version: int = Field(default=0)      # bumped on every changing reconcile (I7)


class DeltaOutboxV1(SQLModel, table=True):
    """The delta stream (boolean spec §4/§5.1): every reachability flip inserts a row
    inside the writing transaction. The autoincrement id is the cursor; the cascade
    reads by keyset pagination from its starting watermark. Replayable, memory-flat,
    and the seam for a future async worker (spec §13).

    Endpoints are denormalized (type/name/predicate captured at emission): implicit-
    node GC can delete an endpoint's node row inside the same transaction, and the
    processor must still be able to map the flip to its derived key (see
    docs/spec-deviations.md P4).
    """
    __tablename__ = "delta_outbox_v1"
    __table_args__ = {'extend_existing': True}

    id: int | None = Field(default=None, primary_key=True)
    store_id: str = Field(index=True)
    subject_node_id: int
    object_node_id: int
    action: str                          # 'ADDED' | 'REMOVED'
    subject_type: str = Field(default='')
    subject_name: str = Field(default='')
    subject_predicate: str = Field(default='')
    object_type: str = Field(default='')
    object_name: str = Field(default='')
    object_predicate: str = Field(default='')


Node = NodeV4
Edge = EdgeV4
Store = StoreV4
