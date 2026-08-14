import time
from typing import NamedTuple
from types import EllipsisType

from sqlalchemy import Index
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
    # The per-column indexes were dropped (N5 audit 2026-07-14): every NodeV4 query
    # filters a `(store_id, predicate, type[, name][, wildcard])` leftmost prefix or by
    # id, all served by `node_v4_unique_constraint`. `store_id` is kept for the FK.
    predicate: str
    type: str
    name: str
    # '' for concrete nodes, 'any' or 'all' for split wildcard nodes (spec §1.2/§1.3).
    # Empty string (NOT NULL) is deliberate: SQLite treats NULLs as distinct in a
    # unique constraint, which would silently permit duplicate concrete nodes.
    wildcard: str = Field(default='')
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
        # Object-keyed scans (`core.py:320,617`, `processor.py:260`) filter
        # `(store_id, object_id)` without `subject_id`, so the unique constraint's
        # prefix cannot serve them; this composite does (N5 audit 2026-07-14).
        Index('ix_edge_v4_store_object', 'store_id', 'object_id'),
        {'extend_existing': True},
    )

    id: int | None = Field(default=None, primary_key=True)
    # `store_id` and `subject_id` single-column indexes dropped (N5 audit 2026-07-14):
    # every subject-keyed scan filters `store_id` too, served by the
    # `(store_id, subject_id, ...)` unique-constraint prefix; object-keyed scans use
    # the composite above -- a real per-insert win on both supported backends
    # (SQLite, PostgreSQL), neither of which conjures an index back for an FK column.
    store_id: str = Field(foreign_key="store_v4.id")
    subject_id: int = Field(foreign_key="node_v4.id")
    object_id: int = Field(foreign_key="node_v4.id")
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
    already encodes the relation; ``relation`` is denormalized (unindexed) purely for
    debuggability/inspection -- no query filters on it (residue scans go by
    ``store_id`` or ``object_node_id``). ``stars``/``neg`` are JSON (list of [type, predicate]
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
    relation: str  # unindexed: denormalized for inspection only (N5 audit 2026-07-14)
    stars: str = Field(default='[]')     # JSON: [[type, predicate], ...]
    neg: str = Field(default='[]')       # JSON: [subject_node_id, ...]
    # userset-shaped subjects whose membership is TRUE (blind-audit P4): a derived
    # EDGE from a userset node would leak through the closure to every member,
    # defeating each member's own pointwise exclusion -- so userset memberships are
    # recorded here, edge-free, and answered like pos-with-no-transitivity.
    upos: str = Field(default='[]')      # JSON: [userset_node_id, ...]
    version: int = Field(default=0)      # bumped on every changing reconcile (I7)


class ResidueRefV1(SQLModel, table=True):
    """Reverse index: recorded subject node id -> the residues recording it.

    One row per ``(residue object, subject id)`` pair in ``ResidueV1.neg | upos``.
    Exists so the node-release paths can ask "does ANY residue reference this node?"
    with an indexed seek instead of decoding every residue row in the store: the scan
    it replaces was measured at ~15 us/residue row and went quadratic under churn
    (docs/spec-deviations.md 2026-07-29b). It is the index ``ZT-P0-1``'s own note
    named -- "a subject-id -> residue index maintained in ``_store_residue``, never a
    leaf-kind whitelist" -- see the N3-WITHDRAWN block at the head of ``processor.py``.

    DERIVED, not authoritative. ``ResidueV1.neg``/``upos`` remain the source of truth
    and ``invariants.py`` I6 keeps decoding that JSON directly; a new I6 clause asserts
    the two AGREE in both directions. That split is deliberate: an invariant that read
    this table instead of the JSON would be a mirror of the thing it checks, which is
    the failure mode ``docs/sabotage-procedure.md`` calls "the mirror instrument".

    No foreign keys, deliberately. ``subject_node_id`` may legitimately be observed
    dangling mid-transaction, and a dangling id is precisely the ZT-P0-1 corruption
    class I6 exists to DETECT -- an FK would let the database silently prevent (on
    PostgreSQL) or silently ignore (on SQLite, where FK enforcement is off by default)
    the very state the checker must be able to see.
    """
    __tablename__ = "residue_ref_v1"
    __table_args__ = (
        # Serves the subject-keyed lookup (`store_id AND subject_node_id`) as a
        # leftmost prefix, which is the whole point of the table; no separate
        # single-column index is added, per the N5 audit 2026-07-14 house rule.
        UniqueConstraint('store_id', 'subject_node_id', 'object_node_id',
                         name='residue_ref_v1_unique'),
        # Object-keyed maintenance (`_sync_residue_refs` rewrites one residue's rows)
        # filters `(store_id, object_node_id)`, which the unique constraint's prefix
        # cannot serve -- same shape as `ix_edge_v4_store_object` above.
        Index('ix_residue_ref_v1_store_object', 'store_id', 'object_node_id'),
        {'extend_existing': True},
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: str
    subject_node_id: int
    object_node_id: int


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
    __table_args__ = (
        # Composite replaces the single `store_id` index (N5 audit 2026-07-14): serves
        # both the keyset drain (`store_id AND id > ? ORDER BY id`) and the watermark
        # (`store_id ... ORDER BY id DESC LIMIT 1`) as index-only seeks.
        Index('ix_delta_outbox_v1_store_id_id', 'store_id', 'id'),
        {'extend_existing': True},
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: str
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
