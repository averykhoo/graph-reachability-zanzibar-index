"""
Persistence for the set engine (spec §1.2).

``TupleV1`` is the missing *source of truth* the repo lacked: a raw-tuple table. The
graph index stores *derived* edges (post-`RuleSet.apply`), so it cannot serve as ground
truth for a rewrite-free engine; JSON dumps of bitmaps are opaque and duplicate state.
The set engine rebuilds its in-memory state from these rows on open (replay), the oracle
reads the same rows, and the validation harness gets one canonical op log.

Bitmap snapshot persistence (`BitMap.serialize()` blobs) is a documented non-goal
(spec §3/§10); state is in-memory, rebuilt on open.
"""

import time

from sqlmodel import Field, SQLModel, UniqueConstraint


class TupleV1(SQLModel, table=True):
    """A single raw relation tuple. ``subject_predicate`` is ``'...'`` for a bare entity.

    Deliberately independent of the graph index's ``store_v4`` table (no FK): the set
    engine is a standalone backend that happens to share a database in the test harness.
    """
    __tablename__ = "tuple_v1"
    __table_args__ = (
        UniqueConstraint('store_id', 'subject_predicate', 'subject_type', 'subject_name',
                         'relation', 'object_type', 'object_name', name='tuple_v1_unique'),
        {'extend_existing': True},
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: str = Field(index=True)
    subject_predicate: str = Field(index=True)
    subject_type: str = Field(index=True)
    subject_name: str = Field(index=True)
    relation: str = Field(index=True)
    object_type: str = Field(index=True)
    object_name: str = Field(index=True)
    created_at: float = Field(default_factory=time.time)
