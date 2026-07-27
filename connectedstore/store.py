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
only under the async schedule -- ``check`` falls back to the set engine, which is
fresh by construction. The ENUMERATION surfaces (``lookup``/``lookup_reverse``) take
the same token but cannot fall back, because the two backends' lookup results are not
the same shape; an unsatisfiable demand raises ``LookupNotFresh`` rather than quietly
serving the stale list (zero-trust review ZT-P1-8b -- see that class).

Transaction semantics: ``write`` commits on success and rolls back on rejection
(one logical write = one transaction across BOTH halves; I12 holds across both).
"""

from __future__ import annotations

from sqlmodel import Session, select

from index_v4.core import probe_store_write_lock
from index_v4.invariants import (PARANOIA_ENV_VAR, PARANOIA_OFF,
                                 install_paranoia, resolve_paranoia_level)
from index_v4.processor import DeltaProcessor
from setengine.setops import SetOps, DEFAULT_SETOPS
from zanzibar_utils_v1 import AdmissionRejected

from .apply import advance_index, ensure_cursor
from .schema_io import ensure_schema, open_graph_index
# StaleRead lives with the evaluator that raises it first (TupleSource.check);
# re-exported here for backward compatibility.
from .source import StaleRead, TupleSource, assert_read_isolation


class LookupNotFresh(StaleRead):
    """A ``lookup`` / ``lookup_reverse`` carrying an ``at_least`` token could not be
    served, because the index lags the token and the lookup surface has NO fallback
    (zero-trust review ZT-P1-8b).

    ``check`` can fall back to the set engine when the index lags: it returns a bool,
    so which backend answered is invisible. The lookup surfaces cannot, because the two
    backends do not return the same thing:

    * ``node_ids`` are graph ``NodeV4`` row ids on one side and instance-local,
      RECYCLED interner ids on the other (``SetEngine.result_keys`` is the portable
      form; the graph has no twin) -- so a fallback would silently change the id
      DOMAIN of a result depending on how far behind the worker happened to be;
    * markers are ``(type, predicate, variant)`` on the graph and ``(type, predicate)``
      on the set engine, and ``excluded_node_ids`` ("everyone of this shape except
      these", the derived-relation ``neg`` channel) exists only on the graph side --
      it cannot be reconstructed from a set-engine result at all.

    Unifying that contract is a real, breaking API change with its own oracle-gate
    arc (``docs/architecture/decision-log.md``, round 3). Until it lands, the honest
    behaviour under an explicit freshness demand is to REFUSE: silently serving the
    stale enumeration is how a revoked principal stays listed in a revocation UI, and
    silently swapping id domains is a different bug in a nicer costume.

    RECOVERABLE: run the apply step (``ConnectedStore.catch_up()`` -- an instance may
    run it; it IS the async worker's body) or wait for the worker, then retry. For a
    single yes/no decision, ``check(..., at_least=...)`` has the fallback and needs no
    catch-up."""


class ConnectedStore:
    """One permission store, end to end: validated writes into the tuple log +
    synchronously-maintained graph index; index-served reads with freshness
    fallback."""

    #: Paranoia level when neither the constructor argument nor ``ZANZIBAR_PARANOIA``
    #: says otherwise.
    #:
    #: **OFF, and that is a measured decision, not an oversight.** Interleaved A/B
    #: (alternating arms, min-of-3, boolean fixture, per-write commits through this
    #: class's sync path, 2026-07-26):
    #:
    #:   162 writes:  off 3.896s | residue 4.063s (**+4.3%**) | full  8.743s (+124%)
    #:   478 writes:  off 14.641s | residue 15.480s (**+5.7%**) | full 58.928s (+303%)
    #:
    #: The cheap tier is genuinely cheap *relative to* the full checker (~50x less
    #: overhead), but it is still ~5% of the write path and it GROWS with the store
    #: (its scan is O(residue rows), i.e. O(objects carrying derived state)). A
    #: silent 5%-and-rising write regression is not something to switch on under
    #: everybody without their consent -- so the default preserves today's behaviour
    #: exactly and the switch is one argument (or one env var) away.
    #:
    #: **Operators: turn it on.** ``ZANZIBAR_PARANOIA=residue`` buys the runtime
    #: detector for the ZT-P0-1 authorization-escalation class (a residue vouching
    #: for a recycled node rowid) for that ~5%. It is the recommended production
    #: setting for anything security-sensitive; only the number, not the value, kept
    #: it out of the default.
    DEFAULT_PARANOIA = PARANOIA_OFF

    def __init__(self, session: Session, store_id: str, *,
                 schema: str | None = None,
                 object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset(),
                 ops: SetOps = DEFAULT_SETOPS,
                 sync: bool = True,
                 paranoia: bool | str | None = None):
        """Open (or bootstrap, when ``schema`` is given) a connected store.

        A passed schema is persisted write-once via ``ensure_schema``; passing one
        that disagrees with the store's persisted schema is a loud error.

        ``sync=True`` (default) inlines the apply step into every write (cursor at
        the log head). ``sync=False`` is the async schedule: writes land in the
        source of truth only; the index advances when ``catch_up`` runs (the worker
        loop), and token-carrying ``check``s fall back to the set engine while it
        lags (token-carrying LOOKUPs raise ``LookupNotFresh`` instead -- see there).

        ``paranoia`` wires the runtime invariant layer (``index_v4.invariants``,
        boolean spec §8.1) into this store's commits. Before this parameter existed
        the layer had two callers, both tests, so every runtime corruption detector
        was dark in production (zero-trust review ZT-P1-3). Levels:

        * ``'off'`` / ``False`` -- no checking. **The default** -- see
          ``DEFAULT_PARANOIA`` for the measurement behind that choice.
        * ``'residue'`` -- **the recommended production setting.** The I6
          residue-hygiene family, checked pre-commit over the store's residue rows
          and the node ids they name: the runtime detector for the
          dangling-``upos``/``neg`` corruption class (the ZT-P0-1 authorization
          escalation -- a residue vouching for a recycled rowid). O(residue rows),
          no full node/edge scan, no BFS. Measured +4.3%/+5.7% on the sync write
          path at 162/478 per-write commits; reads are untouched.
        * ``'full'`` / ``True`` -- everything: I1-I7/I10/I13 plus the delta-scoped
          BFS verifier, pre- and post-commit. O(store) per commit -- measured
          +124%/+303% on the same two workloads (and 4.8-10x in
          ``benchmarks/results/BASELINE_2026-07-13.md``). A prerelease/test tier;
          do not run it under production write load.

        **Fail-closed:** a violation raises ``InvariantViolation`` inside
        ``before_commit``, so the write's commit never happens and ``_write``'s
        handler rolls back both halves and rebuilds the evaluator. The message
        carries the store id, the commit phase, and the violated clause.

        Precedence: this argument (when not ``None``) > the ``ZANZIBAR_PARANOIA``
        environment variable (``off``/``residue``/``full``, or ``0``/``1``) >
        ``ConnectedStore.DEFAULT_PARANOIA``. So an operator can turn the layer up or
        off in a deployment without a code change, and a caller that has made an
        explicit choice is never overridden by the environment.
        """
        self.session = session
        self.store_id = store_id
        self.sync = sync
        self.paranoia = resolve_paranoia_level(paranoia, default=self.DEFAULT_PARANOIA)
        # ZT-P1-5: refuse a bind whose read snapshot can hide a committed log row --
        # anything but READ COMMITTED on a real MVCC server -- before anything else
        # touches the database, because every freshness guarantee in this class rests on
        # the catch-up reaching the real head. Not theoretical on the supported server: a
        # SERIALIZABLE bind was shown to certify a revoked grant as ALLOWED
        # (tests/test_postgres_ha.py::test_serializable_bind_is_refused). Dialect-aware:
        # a no-op on SQLite, where there is no server-side level to pin.
        assert_read_isolation(session)
        # ZT-P1-4: on a SQLite bind, take the real per-store write lock once, right
        # here, and verify it actually HELD -- an autocommit-configured connection
        # releases it instantly, which silently un-atomizes every write's check-then-act
        # admission (two writers both pass, against a state their combined result
        # invalidates). Fail at open, with the configuration fix in the message, rather
        # than corrupting state under concurrency later. FIRST statement of the
        # transaction on purpose (see ``probe_store_write_lock``); released by this
        # constructor's own bootstrap commit below.
        probe_store_write_lock(session, store_id)
        boot_ruleset = None
        if schema is not None:
            # On first bootstrap ensure_schema compiles the schema; reuse that
            # RuleSet below instead of re-parsing the identical text.
            _, boot_ruleset = ensure_schema(session, store_id, schema, object_wildcard_shapes)
            session.flush()
        # Graph side first: its compiled RuleSet is handed to the set engine so the
        # shared schema is parsed + compiled once, not once per backend.
        self.widx, self.ruleset = open_graph_index(session, store_id, ruleset=boot_ruleset)
        self.source = TupleSource(session, store_id, ops=ops, ruleset=self.ruleset)
        compiled = self.ruleset.compiled
        self.proc = (DeltaProcessor(self.widx, compiled)
                     if compiled is not None and compiled.plans else None)
        self.cursor = ensure_cursor(session, store_id, store_id)
        # Blind-audit X3: the bootstrap rows (schema/store/cursor) used to ride the
        # session transaction un-committed -- so the FIRST rejected write (an
        # ordinary ValueError!) or one documented refresh() poll rolled them back
        # and bricked the instance; a read-only open also held the write lock for
        # its lifetime. The class owns commits everywhere else; it owns this one too.
        self.session.commit()
        # ZT-P1-3: the invariant layer is wired here (AFTER the bootstrap commit, so
        # the checker only ever sees a fully-open store). ``install_paranoia`` is
        # idempotent per (session, store), so a test that installs `full` on top of
        # this upgrades the same guard instead of stacking a second set of listeners.
        self.paranoia_guard = install_paranoia(
            session, store_id, self.widx.schema_info, level=self.paranoia)

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
        # P12b — pending-row drain contract. ``source._append`` stashes each flushed
        # log row in ``source._pending_rows``; we hand those rows to ``advance_index``
        # as a read hint on the sync fast path, then this buffer MUST be empty before
        # ``_write`` returns so no row survives into a later transaction. Every exit
        # path is covered:
        #   * admission rejection (fn raises): nothing was flushed on the reject path
        #     (``add`` returns early on a duplicate WITHOUT appending; ``remove``
        #     raises before its append), but the store may carry a stale row from a
        #     prior aborted write, so we drain-and-discard.
        #   * sync success: ``pop_pending_rows`` drains it into the hint below.
        #   * async success (``sync=False``): drained-and-discarded (the async worker
        #     re-reads from the log; no hint).
        #   * apply/commit failure: drained-and-discarded before re-raising.
        fn = self.source.add if op == 'add' else self.source.remove
        try:
            token = fn(*raw)
        except AdmissionRejected:
            # ordinary admission rejection: the set engine validates before mutating
            # its in-memory state (SetEngine.add_tuple/remove_tuple contract), so
            # the rollback alone restores truth -- no O(N) evaluator rebuild on the
            # hot rejection path.
            #
            # NARROWED from `except ValueError` (ZT-P4-7): the "no rebuild needed"
            # shortcut is licensed by that pre-mutation contract, which holds for a
            # REFUSAL and for nothing else. An unclassified `ValueError` escaping the
            # write is by construction an internal-contract failure, i.e. a bug that
            # may well have fired mid-mutation -- it now falls through to the
            # `except Exception` arm below, which rebuilds the evaluator before
            # re-raising. Strictly safer, and the exception still propagates
            # unchanged either way.
            self.source.pop_pending_rows()  # discard: nothing must span the rollback
            self.session.rollback()
            raise
        except Exception:
            self.source.pop_pending_rows()  # discard: nothing must span the rollback
            self.session.rollback()
            self.source.refresh_evaluator()
            raise
        try:
            if self.sync:
                # the async apply step, inlined (sync schedule): cursor rides the head.
                # Hand the just-flushed log rows through so the apply step skips
                # re-SELECTing them (P12b); the guard in advance_index only trusts the
                # hint when it equals what log_rows would return.
                hint = self.source.pop_pending_rows()
                advance_index(self.session, self.cursor, self.widx, self.ruleset,
                              self.proc, rows_hint=hint or None)
            else:
                # async schedule: the worker re-reads from the log; drop the hint so
                # it can never leak into a later transaction.
                self.source.pop_pending_rows()
            self.session.commit()
            return token
        except Exception:
            self.source.pop_pending_rows()  # discard: nothing must span the rollback
            self.session.rollback()
            # past admission the evaluator HAS the write in memory: it is a cache
            # over TupleV1, so rebuild it from the rolled-back truth (also resets
            # the evaluator watermark past the discarded token)
            self.source.refresh_evaluator()
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
                else:
                    # Blind-audit X2: the zero-row path still opened a transaction
                    # (store lock + cursor refresh + log read). Leaving it open
                    # pins the worker's read snapshot forever (blind daemon) and,
                    # on PostgreSQL, holds the FOR UPDATE store lock indefinitely.
                    self.session.rollback()
            except Exception:
                self.session.rollback()
                raise
            if not applied:
                return total
            total += applied

    def refresh(self) -> None:
        """Replica-reader poll: drop the current read snapshot and every read-path
        cache, so the next queries see the latest committed state coherently
        (fresh transaction + rebuilt evaluator; the graph read path is uncached
        by design -- blind-audit W2)."""
        self.session.rollback()
        self.source.refresh_evaluator()

    def lag(self) -> int:
        """Log rows the index has not yet applied (0 = fully caught up). A COUNT
        query -- never materializes rows (ids are globally monotonic across stores,
        so counting, not id-subtraction, is also what makes the number meaningful)."""
        from sqlalchemy import func
        from .models import TupleLogV1
        return self.session.exec(
            select(func.count())
            .select_from(TupleLogV1)
            .where(TupleLogV1.store_id == self.store_id)
            .where(TupleLogV1.id > self.cursor.applied_log_id)
        ).one()

    # ------------------------------------------------------------------ #
    # Reads: index-served, freshness-gated (spec §2.5)
    # ------------------------------------------------------------------ #

    def _fresh_enough(self, at_least: int | None) -> bool:
        # ``at_least is None`` -> True is the DESIGN, not a fail-open default (called
        # out because it reads like one): no token means the caller made no freshness
        # demand, and an untokened read is documented as bounded-stale (spec §2.5 --
        # the index cursor may lag under the async schedule). A caller that needs
        # read-your-writes passes the token the write returned; there is nothing to
        # fall back to when it did not, and defaulting to "stale is unacceptable"
        # would make every ordinary read pay for a demand nobody made.
        return at_least is None or self.cursor.applied_log_id >= at_least

    def _require_index_freshness(self, at_least: int | None, surface: str) -> None:
        """Enforce an ``at_least`` demand on an index-only read surface (ZT-P1-8b).

        Same first two rungs as ``check``'s ladder -- test the in-memory cursor, then
        re-read the cursor row once, because it is routinely just behind another
        session's committed catch-up and that alone satisfies most tokened reads
        without paying for anything. Where ``check`` then falls back to the set engine,
        this raises: see ``LookupNotFresh`` for why there is no third rung here."""
        if self._fresh_enough(at_least):
            return
        self.session.refresh(self.cursor)
        if self._fresh_enough(at_least):
            return
        raise LookupNotFresh(
            f'{surface}(at_least={at_least}) cannot be served: the index for store '
            f'{self.store_id!r} has applied through {self.cursor.applied_log_id} '
            f'(lag {self.lag()}). Unlike check(), the lookup surfaces have no '
            f'set-engine fallback -- the two backends return different id domains and '
            f'different marker/exclusion shapes, so serving one in place of the other '
            f'would change the meaning of the result (zero-trust review ZT-P1-8b). '
            f'Run catch_up() (or wait for the async worker) and retry; for a single '
            f'decision use check(..., at_least={at_least}), which does fall back.')

    def check(self, subject_predicate, s_type: str, s_name: str,
              relation: str, o_type: str, o_name: str, *,
              at_least: int | None = None) -> bool:
        if self._fresh_enough(at_least):
            return self.widx.check(subject_predicate, s_type, s_name,
                                   relation, o_type, o_name)
        # the in-memory cursor may simply be behind another session's catch-up:
        # re-read it once before paying for a fallback
        self.session.refresh(self.cursor)
        if self._fresh_enough(at_least):
            return self.widx.check(subject_predicate, s_type, s_name,
                                   relation, o_type, o_name)

        # Index lags the token: fall back to the set engine -- but its state is an
        # in-memory cache, only as fresh as its own watermark. Catch up on demand if
        # it predates the token (the honest cost of a tokened read against a lagging
        # index: tailing the log delta, O(delta) not O(store)). If the token is
        # STILL not visible, this session's read snapshot predates the write --
        # refuse loudly rather than serve a stale answer under an explicit
        # freshness demand.
        if self.source.evaluator_watermark < at_least:
            self.source.catch_up_evaluator()
            if self.source.evaluator_watermark < at_least:
                raise StaleRead(
                    f'token {at_least} is not visible in this session snapshot '
                    f'(evaluator at {self.source.evaluator_watermark}); call '
                    f'refresh() to start a fresh read transaction and retry')
        return self.source.check(subject_predicate, s_type, s_name,
                                 relation, o_type, o_name)

    def lookup(self, subject_predicate, s_type: str, s_name: str, *,
               at_least: int | None = None):
        """List-objects: everything the subject can reach, served by the index.

        ``at_least`` demands the index reflect the log through that token. It is
        ENFORCED, not fulfilled by fallback: satisfied demands are served normally,
        unsatisfiable ones raise ``LookupNotFresh`` (see there -- and note this is the
        revocation surface, where quietly returning the pre-revocation enumeration is
        the failure that matters). Omitting the token keeps the previous behaviour
        exactly: an untokened, bounded-stale index read."""
        self._require_index_freshness(at_least, 'lookup')
        return self.widx.lookup(subject_predicate, s_type, s_name)

    def lookup_reverse(self, relation: str, o_type: str, o_name: str, *,
                       at_least: int | None = None):
        """List-users: everything that can reach the object. ``at_least`` behaves
        exactly as in ``lookup`` -- enforced, never silently downgraded."""
        self._require_index_freshness(at_least, 'lookup_reverse')
        return self.widx.lookup_reverse(relation, o_type, o_name)

    def watermark(self) -> int:
        return self.source.watermark()
