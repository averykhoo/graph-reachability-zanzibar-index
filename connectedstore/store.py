"""ConnectedStore: source-of-truth tuples + materialized graph index, composed
(connected-store spec §1/§4).

NOTE (spec §1): the synchronous coupling here is a **temporary schedule, not
temporary machinery**. ``write`` runs the exact same ``advance_index`` apply step
the async worker loops -- inlined into the write transaction, cursor pinned at the
log head. The async cutover (spec §5-S6) changes when the apply step runs, never
what it does; whether the two halves stay unified behind one façade long-term is an
open question this class deliberately does not answer.

Reads are served by the graph index (O(1) probes). ``at_least`` freshness tokens
(spec §2.5) are honored structurally: if the index cursor lags the token -- possible
only under the async schedule -- the read falls back to the set engine, which is
fresh by construction.

Transaction semantics: ``write`` commits on success and rolls back on rejection
(one logical write = one transaction across BOTH halves; I12 holds across both).
"""

from __future__ import annotations

from sqlmodel import Session

from index_v4.processor import DeltaProcessor
from setengine.setops import SetOps, DEFAULT_SETOPS

from .apply import advance_index, ensure_cursor
from .schema_io import ensure_schema, open_graph_index
from .source import TupleSource


class ConnectedStore:
    """One permission store, end to end: validated writes into the tuple log +
    synchronously-maintained graph index; index-served reads with freshness
    fallback."""

    def __init__(self, session: Session, store_id: str, *,
                 schema: str | None = None,
                 object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset(),
                 ops: SetOps = DEFAULT_SETOPS,
                 sync: bool = True):
        """Open (or bootstrap, when ``schema`` is given) a connected store.

        A passed schema is persisted write-once via ``ensure_schema``; passing one
        that disagrees with the store's persisted schema is a loud error.

        ``sync=True`` (default) inlines the apply step into every write (cursor at
        the log head). ``sync=False`` is the async schedule: writes land in the
        source of truth only; the index advances when ``catch_up`` runs (the worker
        loop), and token-carrying reads fall back to the set engine while it lags.
        """
        self.session = session
        self.store_id = store_id
        self.sync = sync
        if schema is not None:
            ensure_schema(session, store_id, schema, object_wildcard_shapes)
            session.flush()
        self.source = TupleSource(session, store_id, ops=ops)
        self.widx, self.ruleset = open_graph_index(session, store_id)
        compiled = self.ruleset.compiled
        self.proc = (DeltaProcessor(self.widx, compiled)
                     if compiled is not None and compiled.plans else None)
        self.cursor = ensure_cursor(session, store_id, store_id)

    # ------------------------------------------------------------------ #
    # Writes: one transaction across both halves (sync schedule)
    # ------------------------------------------------------------------ #

    def add_tuple(self, subject_predicate, s_type: str, s_name: str,
                  relation: str, o_type: str, o_name: str) -> int:
        return self._write('add', subject_predicate, s_type, s_name,
                           relation, o_type, o_name)

    def remove_tuple(self, subject_predicate, s_type: str, s_name: str,
                     relation: str, o_type: str, o_name: str) -> int:
        return self._write('remove', subject_predicate, s_type, s_name,
                           relation, o_type, o_name)

    def _write(self, op: str, *raw) -> int:
        try:
            fn = self.source.add if op == 'add' else self.source.remove
            token = fn(*raw)
            if self.sync:
                # the async apply step, inlined (sync schedule): cursor rides the head
                advance_index(self.session, self.cursor, self.widx, self.ruleset, self.proc)
            self.session.commit()
            return token
        except Exception:
            self.session.rollback()
            # the set engine's in-memory state is a cache over TupleV1 and may have
            # been mutated before the failure: rebuild it from the rolled-back truth
            self.source.engine.rebuild()
            raise

    # ------------------------------------------------------------------ #
    # The worker loop (async schedule): same apply step, batched
    # ------------------------------------------------------------------ #

    def catch_up(self, batch: int | None = None) -> int:
        """Advance the index over the log until it reaches the head; one transaction
        per batch (exactly-once: applied rows + cursor commit together, so a failed
        batch moves nothing and a retry re-reads the same rows). Returns the number
        of log rows applied. This IS the async worker's body -- a daemon would just
        call it on a schedule."""
        total = 0
        while True:
            try:
                applied = advance_index(self.session, self.cursor, self.widx,
                                        self.ruleset, self.proc, batch=batch)
                if applied:
                    self.session.commit()
            except Exception:
                self.session.rollback()
                raise
            if not applied:
                return total
            total += applied

    def lag(self) -> int:
        """Log rows the index has not yet applied (0 = fully caught up). Counted,
        not id-subtracted: log ids are globally monotonic across stores."""
        from .source import log_rows
        return len(log_rows(self.session, self.store_id, self.cursor.applied_log_id))

    # ------------------------------------------------------------------ #
    # Reads: index-served, freshness-gated (spec §2.5)
    # ------------------------------------------------------------------ #

    def _fresh_enough(self, at_least: int | None) -> bool:
        return at_least is None or self.cursor.applied_log_id >= at_least

    def check(self, subject_predicate, s_type: str, s_name: str,
              relation: str, o_type: str, o_name: str, *,
              at_least: int | None = None) -> bool:
        if self._fresh_enough(at_least):
            return self.widx.check(subject_predicate, s_type, s_name,
                                   relation, o_type, o_name)
        # index lags the token (async schedule): the set engine is fresh by construction
        return self.source.check(subject_predicate, s_type, s_name,
                                 relation, o_type, o_name)

    def lookup(self, subject_predicate, s_type: str, s_name: str):
        return self.widx.lookup(subject_predicate, s_type, s_name)

    def lookup_reverse(self, relation: str, o_type: str, o_name: str):
        return self.widx.lookup_reverse(relation, o_type, o_name)

    def watermark(self) -> int:
        return self.source.watermark()
