"""Persistence for the connected store.

``SchemaRecord`` -- the store's schema SOURCE, write-once (schemas are
static everywhere; compiled artifacts are cache, recompiled on open, never stored).

``TupleLog`` -- the permanent, append-only tuple event log: the audit
log, the replay source, and the token domain. Written in the same transaction as the
``RelationTuple`` mutation; never cleared (compaction is a documented hook). ``RelationTuple``
stays the current-state snapshot; this is the history.

``IndexCursor`` -- "this graph index reflects that tuple store through log row N".
Applied rows and the cursor advance commit in one transaction: that
transactionality IS the exactly-once guarantee. It also carries the
apply step's STALL marker (``stalled_after``), which the read path consults so an
index that cannot advance is never served as if it were merely behind.
"""
# Provenance (moved out of the docstring, TK123 item 14): connected-store spec sec 2.1/2.2.
# Provenance (moved out of the docstring, TK123 item 14): connected-store spec §3.
# Provenance (moved out of the docstring, TK123 item 14): spec §2.3; spec §4; spec §2.6;
# TK111.

import contextlib
import time

from sqlalchemy import Index
from sqlalchemy import inspect as _sa_inspect
from sqlmodel import Field, SQLModel, UniqueConstraint


def _row_repr(row, fields: tuple[str, ...], short: frozenset[str] = frozenset()) -> str:
    """A repr naming ``fields`` that never prints an empty ``Model()``.

    SQLModel's own repr reads the instance ``__dict__``, which a ``commit()`` EXPIRES, so a
    committed row printed as ``SchemaRecord()`` (0.0.5 install trial, F6). Reading an
    expired attribute on a row still in its session reloads it (one SELECT, as any
    attribute access would), under ``no_autoflush``: printing a row never flushes the
    session's pending writes, so a ``print`` or a log line cannot fail or commit-order the
    caller's transaction. A value that cannot be read (detached, or a session that must
    roll back first) prints as ``?`` instead of raising from ``repr``. A field in
    ``short`` prints as its length."""
    # TK153 F6, 2026-10-17. no_autoflush: TK153 review fix, same day -- without it the
    # reload flushed pending rows, and a conflicting one left the session needing rollback.
    state = _sa_inspect(row)
    session = state.session
    guard = session.no_autoflush if session is not None else contextlib.nullcontext()
    parts = []
    unloaded = state.unloaded
    with guard:
        for name in fields:
            if name in unloaded and session is None:
                parts.append(f'{name}=?')
                continue
            try:
                value = getattr(row, name)
            except Exception:     # noqa: BLE001 -- a repr must not raise
                parts.append(f'{name}=?')
                continue
            if name in short and isinstance(value, str):
                parts.append(f'{name}=<{len(value)} chars>')
            else:
                parts.append(f'{name}={value!r}')
    return f"{type(row).__name__}({', '.join(parts)})"


class SchemaRecord(SQLModel, table=True):
    """A store's schema, in table ``zanzibar_schema_record``: one row per store id,
    written once (``save_schema``, or the first ``Store(..., schema=...)``) and never
    changed. ``schema_text`` is the DSL as given (OpenFGA JSON is stored converted to
    DSL); ``object_wildcard_shapes`` is a JSON list of ``[type, relation]`` pairs.
    """
    __tablename__ = "zanzibar_schema_record"

    store_id: str = Field(primary_key=True)
    schema_text: str
    object_wildcard_shapes: str = Field(default='[]')   # JSON: [[type, relation], ...]
    created_at: float = Field(default_factory=time.time)

    def __repr__(self) -> str:
        return _row_repr(self, ('store_id', 'schema_text', 'object_wildcard_shapes'),
                         short=frozenset({'schema_text'}))


class TupleLog(SQLModel, table=True):
    """The append-only log of accepted writes, in table ``zanzibar_tuple_log``: the
    source of truth both backends are built from.

    One row per accepted ``add_tuple`` (``op="ADD"``) or ``remove_tuple``
    (``op="REMOVE"``). A row's ``id`` is the freshness token the write returned and the
    position an index cursor counts in. Rows are never updated or deleted.
    """
    __tablename__ = "zanzibar_tuple_log"
    __table_args__ = (
        # Composite replaces the single `store_id` index (N5 audit 2026-07-14):
        # `log_rows` (`store_id AND id > ? ORDER BY id`, per sync write) and
        # `log_watermark` (`store_id ... ORDER BY id DESC`) are keyset/max-id shapes;
        # the log is append-only forever, so this is asymptotic protection as it grows.
        Index('ix_zanzibar_tuple_log_store_id_id', 'store_id', 'id'),
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


class IndexCursor(SQLModel, table=True):
    """How far a graph index has applied its source store's tuple log, in table
    ``zanzibar_index_cursor``: one row per index store id.

    ``applied_log_id`` is the last ``TupleLog`` id the index reflects. ``stalled_after``
    and ``stall_error`` are set when the index cannot apply the next row (see
    ``Store.index_stalled``), and cleared once a row applies again (after ``rebuild_index``,
    say).
    """
    __tablename__ = "zanzibar_index_cursor"
    __table_args__ = (
        UniqueConstraint('index_store_id', name='zanzibar_index_cursor_unique'),
    )

    id: int | None = Field(default=None, primary_key=True)
    # `index_store_id` index dropped (N5 audit 2026-07-14): `zanzibar_index_cursor_unique`
    # already indexes it (it's the sole constraint column).
    index_store_id: str
    source_store_id: str = Field(index=True)
    applied_log_id: int = Field(default=0)
    # TK111/TK112 stall marker: the ``applied_log_id`` the apply step last FAILED to
    # advance past. A stall is live only while it equals ``applied_log_id`` -- any
    # successful advance invalidates it even if nothing clears it. Persisted (not held
    # in memory) because the reader that must stop trusting the index is usually a
    # different instance from the worker that hit the failure. See
    # ``Store.index_stalled``.
    stalled_after: int | None = Field(default=None)
    stall_error: str | None = Field(default=None)

    def __repr__(self) -> str:
        return _row_repr(self, ('index_store_id', 'source_store_id', 'applied_log_id',
                                'stalled_after'))
