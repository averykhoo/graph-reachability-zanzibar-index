"""Persistence for the connected store (connected-store spec §3).

``SchemaV4`` -- the store's schema SOURCE, write-once (spec §2.1/§2.2: schemas are
static everywhere; compiled artifacts are cache, recompiled on open, never stored).

``TupleLogV1`` -- the permanent, append-only tuple event log (spec §2.3): the audit
log, the replay source, and the token domain. Written in the same transaction as the
``TupleV1`` mutation; never cleared (compaction is a documented hook). ``TupleV1``
stays the current-state snapshot; this is the history.

``IndexCursorV1`` -- "this graph index reflects that tuple store through log row N"
(spec §4). Applied rows and the cursor advance commit in one transaction: that
transactionality IS the exactly-once guarantee (spec §2.6).
"""

import time

from sqlalchemy import Index
from sqlmodel import Field, SQLModel, UniqueConstraint


class SchemaV4(SQLModel, table=True):
    __tablename__ = "schema_v4"
    __table_args__ = {'extend_existing': True}

    store_id: str = Field(primary_key=True)
    schema_text: str
    object_wildcard_shapes: str = Field(default='[]')   # JSON: [[type, relation], ...]
    created_at: float = Field(default_factory=time.time)


class TupleLogV1(SQLModel, table=True):
    __tablename__ = "tuple_log_v1"
    __table_args__ = (
        # Composite replaces the single `store_id` index (N5 audit 2026-07-14):
        # `log_rows` (`store_id AND id > ? ORDER BY id`, per sync write) and
        # `log_watermark` (`store_id ... ORDER BY id DESC`) are keyset/max-id shapes;
        # the log is append-only forever, so this is asymptotic protection as it grows.
        Index('ix_tuple_log_v1_store_id_id', 'store_id', 'id'),
        {'extend_existing': True},
    )

    id: int | None = Field(default=None, primary_key=True)   # the token / cursor domain
    store_id: str
    op: str                                                  # 'ADD' | 'REMOVE'
    subject_predicate: str
    subject_type: str
    subject_name: str
    relation: str
    object_type: str
    object_name: str
    created_at: float = Field(default_factory=time.time)


class IndexCursorV1(SQLModel, table=True):
    __tablename__ = "index_cursor_v1"
    __table_args__ = (
        UniqueConstraint('index_store_id', name='index_cursor_v1_unique'),
        {'extend_existing': True},
    )

    id: int | None = Field(default=None, primary_key=True)
    # `index_store_id` index dropped (N5 audit 2026-07-14): `index_cursor_v1_unique`
    # already indexes it (it's the sole constraint column).
    index_store_id: str
    source_store_id: str = Field(index=True)
    applied_log_id: int = Field(default=0)
