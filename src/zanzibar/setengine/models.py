"""
Persistence for the set engine.

``RelationTuple`` is the *source of truth*: a raw-tuple table. The graph index stores
*derived* edges (post-`RuleSet.apply`), so it cannot serve as ground truth for a
rewrite-free engine; JSON dumps of bitmaps are opaque and duplicate state. The set engine
rebuilds its in-memory state from these rows on open (replay).

Bitmap snapshot persistence (`BitMap.serialize()` blobs) is a documented non-goal;
state is in-memory, rebuilt on open.
"""
# Provenance (moved out of the docstring, TK123 item 14): spec §1.2; spec §3/§10.

import time

from sqlmodel import Field, SQLModel, UniqueConstraint


class RelationTuple(SQLModel, table=True):
    """One stored relation tuple, a row of table ``zanzibar_relation_tuple``.

    ``subject_type:subject_name#subject_predicate`` is related by ``relation`` to
    ``object_type:object_name``, within ``store_id``. ``subject_predicate`` is ``'...'``
    for a bare entity.
    """
    __tablename__ = "zanzibar_relation_tuple"
    __table_args__ = (
        UniqueConstraint('store_id', 'subject_predicate', 'subject_type', 'subject_name',
                         'relation', 'object_type', 'object_name', name='zanzibar_relation_tuple_unique'),
    )

    id: int | None = Field(default=None, primary_key=True)
    store_id: str = Field(index=True)
    # The per-column indexes were dropped (N5 audit 2026-07-14): the only filtered
    # query (`SetEngine._row`) conjoins all seven tuple columns and is served by
    # `zanzibar_relation_tuple_unique`'s prefix; `rebuild()` filters `store_id` only (index kept).
    subject_predicate: str
    subject_type: str
    subject_name: str
    relation: str
    object_type: str
    object_name: str
    created_at: float = Field(default_factory=time.time)
