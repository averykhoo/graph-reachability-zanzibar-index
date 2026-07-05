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

    store: StoreV4 = Relationship()
    subject: NodeV4 = Relationship(sa_relationship=RelationshipProperty(foreign_keys='[EdgeV4.subject_id]'))
    object: NodeV4 = Relationship(sa_relationship=RelationshipProperty(foreign_keys='[EdgeV4.object_id]'))

Node = NodeV4
Edge = EdgeV4
Store = StoreV4
