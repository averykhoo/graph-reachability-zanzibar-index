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


class IndexStore(SQLModel, table=True):
    """One row per graph index store id, in table ``zanzibar_store``.

    Represents a discrete graph index environment (e.g., a specific Tenant or App)
    and allows attaching arbitrary metadata to the graph boundary. Its ``id`` is the
    same store id that ``zanzibar.store.Store`` and ``SchemaRecord`` use. This is the
    index's bookkeeping row, not the user-facing ``zanzibar.store.Store`` class; the
    table name is kept from 0.0.x so existing databases still open.
    """
    __tablename__ = "zanzibar_store"

    id: str = Field(primary_key=True)
    description: str = Field(default="")
    created_at: float = Field(default_factory=time.time)


class Node(SQLModel, table=True):
    """One node of the graph index, in table ``zanzibar_node``: an entity, a userset or a
    relation on an object, written ``(type, name, predicate)``.

    ``predicate`` is the relation (``doc:d1#viewer`` is ``("doc", "d1", "viewer")``) or
    ``"..."`` for a bare entity (``user:alice`` is ``("user", "alice", "...")``).
    ``wildcard`` is ``""`` for a concrete node and ``"any"`` / ``"all"`` for the nodes that
    stand for a ``*`` name. The ``node_ids`` of a ``LookupResult`` are this table's ``id``
    values; ``Store.result_keys`` reads them for you. The library maintains the rows:
    read them, never write them.
    """
    __tablename__ = "zanzibar_node"
    __table_args__ = (
        UniqueConstraint('store_id', 'predicate', 'type', 'name', 'wildcard',
                         name='zanzibar_node_unique_constraint'),
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: str = Field(foreign_key="zanzibar_store.id", index=True)
    # The per-column indexes were dropped (N5 audit 2026-07-14): every Node query
    # filters a `(store_id, predicate, type[, name][, wildcard])` leftmost prefix or by
    # id, all served by `zanzibar_node_unique_constraint`. `store_id` is kept for the FK.
    predicate: str
    type: str
    name: str
    # '' for concrete nodes, 'any' or 'all' for split wildcard nodes (spec §1.2/§1.3).
    # Empty string (NOT NULL) is deliberate: SQLite treats NULLs as distinct in a
    # unique constraint, which would silently permit duplicate concrete nodes.
    wildcard: str = Field(default='')
    implicit: bool = Field(default=True)
    reference_count: int = Field(default=0)

    store: IndexStore = Relationship()

    @property
    def predicate_or_ellipsis(self) -> str | EllipsisType:
        return Ellipsis if self.predicate == '...' else self.predicate


class Edge(SQLModel, table=True):
    """One edge of the graph index's materialized transitive closure, in table
    ``zanzibar_edge``: ``subject_id`` reaches ``object_id`` (both ``Node`` ids).

    The counts record how many direct tuples and how many derivation paths support the
    edge, so a removal knows when the edge goes; ``derived`` marks an edge the
    ``and`` / ``but not`` processor wrote. Maintained by the library: read, never write.
    """
    __tablename__ = "zanzibar_edge"
    __table_args__ = (
        UniqueConstraint('store_id', 'subject_id', 'object_id', name='zanzibar_edge_unique_constraint'),
        # Object-keyed scans (`core.py:320,617`, `processor.py:260`) filter
        # `(store_id, object_id)` without `subject_id`, so the unique constraint's
        # prefix cannot serve them; this composite does (N5 audit 2026-07-14).
        Index('ix_zanzibar_edge_store_object', 'store_id', 'object_id'),
    )

    id: int | None = Field(default=None, primary_key=True)
    # `store_id` and `subject_id` single-column indexes dropped (N5 audit 2026-07-14):
    # every subject-keyed scan filters `store_id` too, served by the
    # `(store_id, subject_id, ...)` unique-constraint prefix; object-keyed scans use
    # the composite above -- a real per-insert win on both supported backends
    # (SQLite, PostgreSQL), neither of which conjures an index back for an FK column.
    store_id: str = Field(foreign_key="zanzibar_store.id")
    subject_id: int = Field(foreign_key="zanzibar_node.id")
    object_id: int = Field(foreign_key="zanzibar_node.id")
    direct_edge_count: int = Field(default=0)
    indirect_edge_count: int = Field(default=0)
    # True iff the direct edge was written by the delta processor into a derived-public
    # family (boolean spec §4/I5). Exclusivity makes this equivalent to "direct edge on
    # a derived-public family"; the flag makes the invariant checkable per row.
    derived: bool = Field(default=False)

    store: IndexStore = Relationship()
    subject: Node = Relationship(sa_relationship=RelationshipProperty(foreign_keys='[Edge.subject_id]'))
    object: Node = Relationship(sa_relationship=RelationshipProperty(foreign_keys='[Edge.object_id]'))


class Residue(SQLModel, table=True):
    """Persisted symbolic wildcard state per (object node, derived relation): the
    ``(stars, neg)`` record `check` consults alongside the edge probe.

    ``object_node_id`` is the derived relation's public object node, whose identity
    already encodes the relation; ``relation`` is denormalized (unindexed) purely for
    debuggability/inspection -- no query filters on it (residue scans go by
    ``store_id`` or ``object_node_id``). ``stars``/``neg`` are JSON (list of [type, predicate]
    shapes / list of concrete subject node ids) -- layout adaptable;
    cursor-free, one row per object. Empty residues are deleted, never stored.
    """
    # Provenance (moved out of the docstring, TK123 item 14): spec sec 4.
    # Provenance (moved out of the docstring, TK123 item 14): boolean spec §4.
    __tablename__ = "zanzibar_residue"
    __table_args__ = (
        UniqueConstraint('store_id', 'object_node_id', name='zanzibar_residue_unique'),
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: str = Field(index=True)
    object_node_id: int = Field(foreign_key="zanzibar_node.id", index=True)
    relation: str  # unindexed: denormalized for inspection only (N5 audit 2026-07-14)
    stars: str = Field(default='[]')     # JSON: [[type, predicate], ...]
    neg: str = Field(default='[]')       # JSON: [subject_node_id, ...]
    # userset-shaped subjects whose membership is TRUE (blind-audit P4): a derived
    # EDGE from a userset node would leak through the closure to every member,
    # defeating each member's own pointwise exclusion -- so userset memberships are
    # recorded here, edge-free, and answered like pos-with-no-transitivity.
    upos: str = Field(default='[]')      # JSON: [userset_node_id, ...]
    version: int = Field(default=0)      # bumped on every changing reconcile (I7)


class ResidueRef(SQLModel, table=True):
    """Reverse index: recorded subject node id -> the residues recording it.

    One row per ``(residue object, subject id)`` pair in ``Residue.neg | upos``.
    Exists so the node-release paths can ask "does ANY residue reference this node?"
    with an indexed seek instead of decoding every residue row in the store: the scan
    it replaces was measured at ~15 us/residue row and went quadratic under churn.
    It is the index a security review called for: "a subject-id -> residue index
    maintained in ``_store_residue``, never a leaf-kind whitelist".

    DERIVED, not authoritative. ``Residue.neg``/``upos`` remain the source of truth
    and the residue-hygiene invariants keep decoding that JSON directly; a clause there asserts
    the two AGREE in both directions. That split is deliberate: an invariant that read
    this table instead of the JSON would be a mirror of the thing it checks, which is
    a known failure mode ("the mirror instrument").

    No foreign keys, deliberately. ``subject_node_id`` may legitimately be observed
    dangling mid-transaction, and a dangling id is precisely the corruption
    class the residue-hygiene invariants exist to DETECT -- an FK would let the database silently prevent (on
    PostgreSQL) or silently ignore (on SQLite, where FK enforcement is off by default)
    the very state the checker must be able to see.
    """
    # Provenance (moved out of the docstring, TK123 item 14): ZT-P0-1's own note; the
    # N3-WITHDRAWN block at the head of processor.py; I6 is the residue-hygiene invariant
    # family; the mirror instrument is docs/sabotage-procedure.md; ZT-P0-1 corruption class.
    # Provenance (moved out of the docstring, TK123 item 14): docs/spec-deviations.md
    # 2026-07-29b.
    __tablename__ = "zanzibar_residue_ref"
    __table_args__ = (
        # Serves the subject-keyed lookup (`store_id AND subject_node_id`) as a
        # leftmost prefix, which is the whole point of the table; no separate
        # single-column index is added, per the N5 audit 2026-07-14 house rule.
        UniqueConstraint('store_id', 'subject_node_id', 'object_node_id',
                         name='zanzibar_residue_ref_unique'),
        # Object-keyed maintenance (`_sync_residue_refs` rewrites one residue's rows)
        # filters `(store_id, object_node_id)`, which the unique constraint's prefix
        # cannot serve -- same shape as `ix_zanzibar_edge_store_object` above.
        Index('ix_zanzibar_residue_ref_store_object', 'store_id', 'object_node_id'),
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: str
    subject_node_id: int
    object_node_id: int


class DeltaOutbox(SQLModel, table=True):
    """The delta stream: every reachability flip inserts a row
    inside the writing transaction. The autoincrement id is the cursor; the cascade
    reads by keyset pagination from its starting watermark. Replayable, memory-flat,
    and the seam for a future async worker.

    Endpoints are denormalized (type/name/predicate captured at emission): implicit-
    node GC can delete an endpoint's node row inside the same transaction, and the
    processor must still be able to map the flip to its derived key.
    """
    # Provenance (moved out of the docstring, TK123 item 14): see docs/spec-deviations.md P4.
    # Provenance (moved out of the docstring, TK123 item 14): boolean spec §4/§5.1; spec §13.
    __tablename__ = "zanzibar_delta_outbox"
    __table_args__ = (
        # Composite replaces the single `store_id` index (N5 audit 2026-07-14): serves
        # both the keyset drain (`store_id AND id > ? ORDER BY id`) and the watermark
        # (`store_id ... ORDER BY id DESC LIMIT 1`) as index-only seeks.
        Index('ix_zanzibar_delta_outbox_store_id_id', 'store_id', 'id'),
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

