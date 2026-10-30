"""Store: source-of-truth tuples + materialized graph index, composed
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

import json
from dataclasses import dataclass
from typing import overload

from sqlalchemy import func
from sqlalchemy.exc import DBAPIError
from sqlmodel import Session, select

from zanzibar.graphindex.core import probe_store_write_lock
from zanzibar.graphindex.invariants import (PARANOIA_ENV_VAR, PARANOIA_OFF,
                                 defer_post_commit_violations, install_paranoia,
                                 InvariantViolation, raise_post_commit_violation,
                                 resolve_paranoia_level)
from zanzibar.graphindex.processor import DeltaProcessor
from zanzibar.graphindex.wildcard import LookupResult
from zanzibar.setengine.engine import StaleLookupIds
from zanzibar.setengine.setops import SetOps, DEFAULT_SETOPS, require_setops
from zanzibar.schema import AdmissionRejected, IndexResourceLimit, validate_store_id
from zanzibar.schema.errors import ClosureFanoutExceeded
from zanzibar.schema.errors import SchemaError, ZanzibarError, reject_ellipsis_predicate
from zanzibar.schema.json_frontend import _reject_duplicate_json_keys, openfga_json_to_dsl
from zanzibar.schema.tuplestr import lookup_args, lookup_reverse_args, shape_filter, tuple_args

from zanzibar.setengine.models import RelationTuple

from .apply import advance_index, ensure_cursor
from .build import BuildReport, IndexExists, build_index
from .models import IndexCursor, TupleLog
from .schema_io import (TablesNotCreated, TablesOutdated, ensure_schema, missing_tables,
                        open_graph_index, refuse_reusable_node_ids, save_schema)
# StaleRead lives with the evaluator that raises it first (TupleSource.check);
# re-exported here for backward compatibility.
from .source import (StaleRead, TupleSource, _require_clean_session, assert_read_isolation,
                     log_rows, refuse_foreign_token, token_diagnosis, validate_token)


def _name_blocking_backlog_row(exc: BaseException, own_row_id: int | None,
                               store_id: str) -> None:
    """TK167: a sync write that failed on a backlog row OTHER than its own says so.

    The sync apply step replays the whole pending backlog inside the caller's write
    transaction, so one unappliable row that a ``sync=False`` writer logged (a path-count
    overflow, or a fan-out-capped row no ``catch_up`` has yet applied) refuses EVERY sync
    write on the store id, removals of that very tuple included. The bare limit message
    names the backlog row's closure row, not the caller's tuple, which reads as "your
    write was too big". Rewrite the message in place (same instance, same type, so an
    ``except PathCountExceeded`` keeps matching) to name the blocking row and the
    recovery (``catch_up()`` for a fan-out-capped row, a ``sync=False`` removal plus
    ``rebuild_index`` for a path-count overflow). A failure on the caller's OWN row is
    left exactly as it was.

    ``own_row_id`` is the id of the log row THIS call appended, or ``None`` when it
    appended none (a duplicate ``add``, which returns the log head as its token). It is
    deliberately not the returned token: on a duplicate add with the blocking row at the
    log head the token EQUALS the blocking row's id, and comparing against it brought the
    bare message back (TK167 repair round 1)."""
    row = getattr(exc, 'failing_log_row', None)
    if row is None or (own_row_id is not None and row[0] == own_row_id):
        return
    row_id, rendered = row
    original = str(exc)
    if isinstance(exc, ClosureFanoutExceeded):
        # catch_up() runs with the fan-out cap suspended, so it applies this row (with a
        # warning) and the writers are unblocked; nothing has to be removed.
        until, recovery = ('until it is applied', 'run Store.catch_up() (any instance; it '
                           'applies a logged over-cap row with a warning), then retry')
    else:
        until, recovery = ('until that row is gone', 'remove that tuple through a '
                           'Store(..., sync=False) instance, then run '
                           'zanzibar.store.rebuild_index')
    this_write = (f'this write (log row {own_row_id})' if own_row_id is not None else
                  'this write (a duplicate add, which appends no log row)')
    exc.args = (
        f'{this_write} was rolled back because the index backlog of '
        f'store {store_id!r} holds an earlier log row it cannot apply: row {row_id} '
        f'({rendered}). Every sync=True write on this store id, removals included, is '
        f'refused {until}. Recovery: {recovery}. '
        f'The index refused row {row_id} with: {original}',)


class LookupNotFresh(StaleRead):
    """A ``lookup`` / ``lookup_reverse`` carrying an ``at_least`` token could not be
    served, because the index lags the token and the lookup surface has NO fallback.

    ``check`` can fall back to the set engine when the index lags: it returns a bool,
    so which backend answered is invisible. The lookup surfaces cannot, because the two
    backends do not return the same thing:

    * ``node_ids`` are graph ``Node`` row ids on one side and instance-local,
      RECYCLED interner ids on the other (``SetEngine.result_keys`` and
      ``Store.result_keys`` are each side's portable form, in different id
      domains) -- so a fallback would silently change the id DOMAIN of a result
      depending on how far behind the worker happened to be;
    * markers are ``(type, predicate, variant)`` on the graph and ``(type, predicate)``
      on the set engine, and ``excluded_node_ids`` ("everyone of this shape except
      these", the ``neg`` channel) is filled on both sides but, like
      ``node_ids``, in each backend's own id domain.

    So under an explicit freshness demand the lookup REFUSES: silently serving the
    stale enumeration is how a revoked principal stays listed in a revocation UI, and
    silently swapping id domains is a different bug in a nicer costume.

    RECOVERABLE: run the apply step (``Store.catch_up()``, which any instance may
    run; an async deployment schedules it), then retry. For a
    single yes/no decision, ``check(..., at_least=...)`` has the fallback and needs no
    catch-up."""
    # Provenance (moved out of the docstring, TK123 item 14): zero-trust review ZT-P1-8b; the
    # neg channel since TK139.
    # Provenance (moved out of the docstring, TK123 item 14): ``docs/architecture/decision-
    # log.md``, round 3.


class IndexStalled(LookupNotFresh):
    """An UNTOKENED ``lookup`` / ``lookup_reverse`` was refused because the apply step
    has recorded a stall: the last ``catch_up`` failed to advance past the cursor, so
    the index's staleness is no longer bounded.

    An untokened read is documented as bounded-stale: the index trails the log by
    whatever the async worker has not applied YET. A row the index cannot apply at all
    (a path-count overflow, a fan-out-capped row) breaks that bound: every later row,
    revocations included, waits behind it forever, and serving the index would keep a
    revoked principal listed indefinitely. ``check`` falls back to the set engine in
    this state; the lookup surfaces have no fallback (see ``LookupNotFresh``), so they
    refuse.

    RECOVERABLE once the stall clears: any successful ``catch_up`` batch ends it. A
    stall recorded on a transient failure (a lock timeout, a lost connection) clears on
    the next good batch, including a ``catch_up()`` that applies nothing because the
    index is already at the log head. A poison row needs operator action, and
    ``Store.stall_error`` says which row failed and why. The
    fan-out cap is suspended in ``catch_up``, so the poison row left is a path-count
    overflow (``PathCountExceeded``). It never clears by itself, not even when a later
    REMOVE undoes it, because that REMOVE waits behind it. Remove the tuple at the
    source, then call ``zanzibar.store.rebuild_index(session, store_id)``."""
    # Provenance (moved out of the docstring, TK123 item 14): TK112.
    # Provenance (moved out of the docstring, TK123 item 14): TK111/TK112; TK121,
    # ``docs/tk121-stall-recovery-2026-10-04.md``.


class UnloggedTuplesPresent(ZanzibarError, RuntimeError):
    """``Store`` refused to adopt a store id whose ``RelationTuple`` rows the
    ``TupleLog`` does not account for.

    A ``Store`` open that CREATES the index's cursor starts the graph index
    empty and advances it from the log alone. Tuples written without a log row -- by a
    standalone ``SetEngine`` on the same id, before any ``Store`` claimed it --
    would be invisible to the index (``check`` False while the set engine says True), and
    removing one would raise ``InvariantViolation`` ("corruption"). The bootstrap for a
    store that already has tuples is ``Store.adopt`` (or its steps by hand,
    ``save_schema`` + ``build_index``), which materialises the index from the
    ``RelationTuple`` snapshot instead of from the log."""
    # Provenance (moved out of the docstring, TK123 item 14): TK140; 0.0.4 trial BROKEN-3,
    # p09; docs/tk140-one-write-path-per-store-2026-10-13.md.


def _check_open_args(ops: object, sync: object) -> None:
    """``ops`` and ``sync`` of ``Store`` / ``Store.adopt``, before any statement (TK176, the
    0.1.1 install trial F10 / F19)."""
    require_setops(ops)
    # Only a real bool: ``sync=None`` / ``0`` silently chose async mode (an untokened check
    # may then serve a revoked grant until catch_up), and ``sync="false"`` chose sync.
    if not isinstance(sync, bool):
        raise TypeError(f'sync must be True (sync mode) or False (async mode), not {sync!r}')


def _schema_text(schema) -> str | None:
    """The DSL text to persist for ``Store(schema=...)`` (TK123 item 26).

    A ``str`` that does not start with ``{`` is DSL and passes through unchanged. An
    OpenFGA JSON model -- a ``dict``, or a ``str`` starting with ``{`` -- is converted to
    DSL with ``openfga_json_to_dsl`` BEFORE it is saved or compared, so reopening a store
    with the same JSON compares DSL with DSL. The ``{"authorization_model": {...}}``
    envelope an OpenFGA server's ReadAuthorizationModel response wraps a model in is
    unwrapped. Anything else (a compiled ``RuleSet`` included) is a ``TypeError``."""
    if schema is None:
        return None
    if isinstance(schema, str):
        if not schema.lstrip().startswith('{'):
            return schema
        try:
            model = json.loads(schema, object_pairs_hook=_reject_duplicate_json_keys)
        except json.JSONDecodeError as exc:
            raise SchemaError(f'schema starts with {{ but is not valid OpenFGA JSON: '
                              f'{exc}') from None
    elif isinstance(schema, dict):
        model = schema
    else:
        raise TypeError(
            f'schema must be the DSL text (a str) or an OpenFGA JSON model (a str or a '
            f'dict), not {type(schema).__name__}'
            + ('; pass the schema text the RuleSet was compiled from'
               if type(schema).__name__ == 'RuleSet' else ''))
    if (isinstance(model, dict) and 'type_definitions' not in model
            and isinstance(model.get('authorization_model'), dict)):
        model = model['authorization_model']
    return openfga_json_to_dsl(model)


def _adoption_counts(session: Session, store_id: str) -> tuple[int, int, int]:
    """``(RelationTuple rows, TupleLog ADD rows, TupleLog REMOVE rows)`` for the store,
    read in ONE statement (three scalar subqueries).

    One statement because one statement is one snapshot. PostgreSQL READ COMMITTED (the
    only admitted level) re-snapshots per STATEMENT, and nothing serialises this read
    against writers there (``probe_store_write_lock`` is SQLite-only). With three
    separate COUNTs, a logged ``TupleSource`` write committing between them -- its
    ``RelationTuple`` row and its log row land in ONE transaction -- was seen by one count
    and not the other: a fully-logged store refused to open with a spurious
    ``UnloggedTuplesPresent`` (RUN on PG, TK140 review 2026-10-13d), and by the same
    arithmetic an unlogged store could be waved through. Inside one statement every
    committed writer is seen whole or not at all, so the comparison is exact."""
    def count(model, *where):
        return (select(func.count()).select_from(model).where(*where)
                .scalar_subquery())
    row = session.exec(select(
        count(RelationTuple, RelationTuple.store_id == store_id),
        count(TupleLog, TupleLog.store_id == store_id, TupleLog.op == 'ADD'),
        count(TupleLog, TupleLog.store_id == store_id, TupleLog.op == 'REMOVE'),
    )).one()
    return int(row[0]), int(row[1]), int(row[2])


def _reject_unlogged_adoption(session: Session, store_id: str) -> None:
    """Refuse a FIRST open (no ``IndexCursor`` yet) over tuples the log cannot replay.

    Runs only when the open would create the cursor, so a store that has an index pays
    nothing after its first open. "Accounted for" = the ``RelationTuple`` row count equals
    the log's net effect (``ADD`` rows minus ``REMOVE`` rows): admission-validated logging
    (``TupleSource.add/remove``) keeps those equal on every fully-logged store, and the
    trial's adopted store (rows, empty log) differs. The three counts are ONE statement
    (``_adoption_counts``), so a concurrent logged write cannot split them. Rolls back
    before raising, so a refused open leaves no ``SchemaRecord`` behind and does not hold
    the SQLite write lock."""
    has_cursor = session.exec(
        select(IndexCursor.index_store_id)
        .where(IndexCursor.index_store_id == store_id).limit(1)).first()
    if has_cursor is not None:
        return
    n_tuples, n_add, n_remove = _adoption_counts(session, store_id)
    if n_tuples == 0:
        return
    if n_tuples == n_add - n_remove:
        return
    session.rollback()
    # REFUSED SHAPE (TK140): a Store born over RelationTuple rows that no
    # TupleLog row accounts for (written by a standalone SetEngine on the same id).
    # WHY: the index is born empty and advanced from the log only, so those tuples are
    # invisible to it: check says False while the set engine says True, and removing one
    # raises InvariantViolation (0.0.4 trial BROKEN-3, p09).
    # INSTEAD: save_schema(session, id, schema) if the store has none, commit, then
    # build_index(session, id) -- it materialises the index from the RelationTuple
    # snapshot -- and open Store(session, id) without schema=.
    # Provenance: TK140 (one write path).
    raise UnloggedTuplesPresent(
        f'store {store_id!r} already has {n_tuples} RelationTuple row(s) but its tuple '
        f'log accounts for {n_add - n_remove} (ADD {n_add} - REMOVE {n_remove}): they were '
        f'written without the log (by a standalone SetEngine on this store id), and a '
        f'Store index born here would never see them -- check would answer '
        f'False while the set engine answers True, and removing one would be reported '
        f'as corruption. To adopt an existing tuple store: '
        f'Store.adopt(session, {store_id!r}, schema=schema) (leave schema= out if '
        f'it already has one) does it in one call; by hand, '
        f'zanzibar.store.save_schema(session, {store_id!r}, schema) if it has '
        f'no schema yet, session.commit(), then '
        f'zanzibar.store.build_index(session, {store_id!r}) (it builds the index '
        f'from the stored tuples), then Store(session, {store_id!r}). Nothing '
        f'was written by this refused open.')


Key = tuple[str, str, str]


@dataclass(frozen=True)
class ExpandResult:
    """What ``Store.expand`` returns: every subject that has the relation on the object,
    as portable ``(type, name, predicate)`` keys (``predicate`` is the relation, or
    ``"..."`` for a bare subject such as ``("user", "alice", "...")``).

    Three parts, read together:

    * ``keys`` -- members listed one by one;
    * ``markers`` -- ``(type, predicate)`` shapes granted through a wildcard: EVERY subject
      of that shape is a member, including ones no tuple mentions;
    * ``excluded_keys`` -- subjects a marker covers that are NOT members (a ``but not``
      or an ``and`` under a wildcard grant). Always subtract them from a marker.

    A subject a marker covers is usually NOT repeated in ``keys``, so ``keys`` alone is
    not the member list. Use ``key in result`` (``covers``) for one subject. Under
    ``define viewer: [user:*] but not banned`` with a ``user:*`` grant and ``user:mallory``
    banned, ``keys`` is empty, ``markers`` is ``{("user", "...")}`` and ``excluded_keys``
    is ``{("user", "mallory", "...")}``.

    A userset key such as ``("group", "eng", "member")`` means the userset itself is a
    member; its own members are already included (listed in ``keys`` or covered by a
    marker), so never expand it again yourself, which would re-admit a member a
    ``but not`` refuses.

    ``markers`` are ``(type, predicate)`` PAIRS, e.g. ``("user", "...")`` or
    ``("group", "member")`` for a ``[group:*#member]`` grant. ``LookupResult.markers``
    (from ``lookup_reverse``) are ``(type, predicate, "any")`` TRIPLES for the same
    grant, so compare across the two by the first two fields."""
    keys: frozenset = frozenset()
    markers: frozenset = frozenset()
    excluded_keys: frozenset = frozenset()

    def covers(self, key: Key) -> bool:
        """Is the ``(type, name, predicate)`` subject a member? Listed in ``keys``, or
        covered by a marker of its ``(type, predicate)`` shape and not excluded."""
        t, _n, p = key
        return key in self.keys or ((t, p) in self.markers and key not in self.excluded_keys)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, tuple) and len(key) == 3 and self.covers(key)  # type: ignore[arg-type]


class Store:
    """One permission store, end to end: validated writes into the tuple log, a graph
    index maintained from that log, and index-served reads.

    Every write commits and returns a freshness token (an ``int``, the write's log id).
    With ``sync=True`` (the default) the write also updates the index, so this
    instance's reads see it at once. With ``sync=False`` the index advances only when
    ``catch_up()`` runs, which the caller schedules (no worker ships). Until then an
    UNTOKENED ``check`` / ``lookup`` reads the index as it is and can be stale in both
    directions, a revoked grant still reading as allowed included. Only a ``check``
    given ``at_least=token`` falls back to the set engine when the index is behind the
    token; a tokened lookup raises ``LookupNotFresh`` instead. ``sync`` is per instance
    and is not stored.

    ``watermark()`` and ``lag()`` are methods, not properties, because each runs a
    query (``lag()`` a COUNT).

    Give the store a ``Session`` of its own: it commits on open and on every write, and
    rolls back on a refused write and in ``refresh()``."""

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
                 schema: str | dict | None = None,
                 object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset(),
                 ops: SetOps = DEFAULT_SETOPS,
                 sync: bool = True,
                 paranoia: bool | int | str | None = None):
        """Open (or bootstrap, when ``schema`` is given) a connected store.

        ``schema`` is the OpenFGA DSL text, or an OpenFGA JSON model as a ``dict`` or a
        JSON string (also wrapped as ``{"authorization_model": {...}}``, the shape an
        OpenFGA server returns). JSON is converted to DSL before it is saved, so the
        persisted schema is always DSL. A compiled ``RuleSet`` is not accepted.

        A passed schema is persisted write-once via ``ensure_schema``; passing one
        that disagrees with the store's persisted schema is a loud error. "Disagrees"
        means a different PARSED schema: reopening with the same schema re-indented,
        with CRLF line endings, comments or reordered type blocks is accepted.

        ``sync=True`` (default) inlines the apply step into every write (cursor at
        the log head). ``sync=False`` is the async schedule: writes land in the
        source of truth only; the index advances when ``catch_up`` runs (the worker
        loop), and token-carrying ``check``s fall back to the set engine while it
        lags (token-carrying LOOKUPs raise ``LookupNotFresh`` instead -- see there).

        ``paranoia`` wires the runtime invariant layer (``zanzibar.graphindex.invariants``)
        into this store's commits. Levels:

        * ``'off'`` / ``False`` -- no checking. **The default** -- see
          ``DEFAULT_PARANOIA`` for the measurement behind that choice.
        * ``'residue'`` -- **the recommended production setting.** The
          residue-hygiene invariants, checked pre-commit over the store's residue rows
          and the node ids they name: the runtime detector for the
          dangling-``upos``/``neg`` corruption class (an authorization
          escalation -- a residue vouching for a recycled rowid). O(residue rows),
          no full node/edge scan, no BFS. Measured +4.3%/+5.7% on the sync write
          path at 162/478 per-write commits; reads are untouched.
        * ``'full'`` / ``True`` -- every state invariant in that module plus the delta-scoped
          BFS verifier, pre- and post-commit. O(store) per commit -- measured
          +124%/+303% on the same two workloads (and 4.8-10x on
          an earlier write benchmark). A prerelease/test tier;
          do not run it under production write load.
        * ``'fixpoint'`` -- everything ``'full'`` runs, plus a per-cascade check that
          every derived key a boolean cascade scheduled ended at a fixpoint. Roughly
          doubles cascade cost: a diagnosis tier, never a production one. Only an
          explicit ``'fixpoint'`` selects it.

        The ints ``1`` / ``0`` are accepted as ``'full'`` / ``'off'``, like the booleans;
        any other value raises ``ValueError``.

        **Fail-closed:** a violation raises ``InvariantViolation`` before the write
        commits, so nothing is stored: the write is rolled back in the log and the
        index, and the set engine is rebuilt to match. The message carries the store
        id, the commit phase, and the violated clause.

        Under ``'full'`` / ``'fixpoint'`` the same checks run again AFTER the commit.
        A violation found there cannot undo anything: the write IS stored in the log
        and the index. It is raised as ``InvariantViolation`` (phase ``post-commit``,
        message saying the transaction is committed) once ``commit()`` has returned,
        and this Store stays usable; under ``'full'`` the next write's pre-commit
        pass re-checks the whole store, so a state that is still broken refuses it.

        Precedence: this argument (when not ``None``) > the ``ZANZIBAR_PARANOIA``
        environment variable (``off``/``residue``/``full``/``fixpoint``, or ``0``/``1``) >
        ``Store.DEFAULT_PARANOIA``. So an operator can turn the layer up or
        off in a deployment without a code change, and a caller that has made an
        explicit choice is never overridden by the environment.
        """
        # Provenance (moved out of the docstring, TK123 item 14): boolean spec sec 8.1;
        # residue = the I6 family, ZT-P0-1; full = I1-I7/I10/I13; 4.8-10x is
        # benchmarks/results/BASELINE_2026-07-13.md.
        # Provenance (moved out of the docstring, TK123 item 14): `TK136`; zero-trust review
        # ZT-P1-3.
        # TK127 follow-up (2026-10-08): a non-str / blank store id is refused before any
        # statement (``None`` used to reach the NOT NULL column as a raw IntegrityError).
        validate_store_id(store_id)
        # TK123 item 26: JSON -> DSL (and the type check) before any statement runs.
        schema = _schema_text(schema)
        # TK123 item 10: this class owns its transactions (it commits on success and
        # rolls back on failure), so a caller's pending ORM rows would ride along.
        _require_clean_session(session, 'Store')
        _check_open_args(ops, sync)
        self.session = session
        self.store_id = store_id
        self.sync = sync
        self.paranoia = resolve_paranoia_level(paranoia, default=self.DEFAULT_PARANOIA)
        # TK123 item 12: every failure past this point rolls back BEFORE it propagates, so
        # a refused open (StoreNotFound above all) never leaves the SQLite write lock
        # taken by ``probe_store_write_lock`` held on the caller's session.
        try:
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
            # TK154: a 0.0.x SQLite file's zanzibar_node reuses deleted ids; refuse it.
            # Inside this transaction on purpose: the bootstrap commit (or the rollback
            # below) ends the read, whereas a read AFTER the commit left the session holding
            # a stale WAL snapshot, so the next write raised "database is locked"
            # (tests/test_zt_p1_hardening.py::test_no_false_gap_when_log_ids_interleave_across_stores,
            # PROBE 2026-10-16). A missing table is left to the TablesNotCreated path.
            refuse_reusable_node_ids(session)
            # TK140 (0.0.4 trial BROKEN-3): refuse to be BORN over tuples the log cannot
            # replay, before anything (the SchemaRecord included) is written.
            _reject_unlogged_adoption(session, store_id)
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
            defer_post_commit_violations(session)  # TK163: see Store._commit
            self._commit()
        except Exception as exc:
            session.rollback()
            if isinstance(exc, DBAPIError):
                # TK123 item 18: a skipped create_all surfaces as the driver's own
                # message ("no such table" on SQLite, "relation ... does not exist" on
                # PostgreSQL); ask the inspector instead of matching either text.
                missing = missing_tables(session)
                session.rollback()
                if missing:
                    raise TablesNotCreated(missing) from exc
            raise
        # ZT-P1-3: the invariant layer is wired here (AFTER the bootstrap commit, so
        # the checker only ever sees a fully-open store). ``install_paranoia`` is
        # idempotent per (session, store), so a test that installs `full` on top of
        # this upgrades the same guard instead of stacking a second set of listeners.
        self.paranoia_guard = install_paranoia(
            session, store_id, self.widx.schema_info, level=self.paranoia)

    @classmethod
    def adopt(cls, session: Session, store_id: str, *,
              schema: str | dict | None = None,
              object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset(),
              bulk: bool = True,
              ops: SetOps = DEFAULT_SETOPS,
              sync: bool = True,
              paranoia: bool | int | str | None = None,
              ) -> tuple['Store', BuildReport]:
        """Adopt an existing tuple store in one call; returns ``(store, report)``.

        A store id whose ``RelationTuple`` rows were written without the tuple log (by a
        standalone ``SetEngine``) cannot simply be opened as a ``Store``: the open raises
        ``UnloggedTuplesPresent``. This runs the adoption recipe instead: save the
        schema (when ``schema`` is given), build the graph index from the stored tuples
        with ``build_index``, then open the ``Store``. ``report`` is the ``BuildReport``
        ``build_index`` returned; ``store`` is the open ``Store``. ``save_schema`` and
        ``build_index`` stay public for callers that want the steps one by one.

        ``schema`` takes what ``Store(schema=...)`` takes (DSL text, or an OpenFGA JSON
        model). Leave it out when the store already has a persisted schema; a store with
        neither raises ``StoreNotFound``. A schema that differs from the persisted one
        raises ``SchemaMismatch``. ``object_wildcard_shapes`` is saved with ``schema``
        and is used only together with it: with ``schema=None`` the persisted shapes
        apply and this argument is ignored, as in ``Store(session, id)``. ``bulk`` is
        ``build_index``'s; ``ops``, ``sync`` and ``paranoia`` are the ``Store``
        constructor's.

        The schema and the index commit TOGETHER. Each refusal below commits nothing:
        a bad ``paranoia`` (``ValueError``) or ``ops`` (``TypeError``), an id that
        already has an index (``IndexExists``; open it with ``Store(session, id)``),
        writes to the store while the index is built (a ``RuntimeError``; retry when it is
        quiescent), an isolation level other than READ COMMITTED
        (``UnsafeIsolationLevel``), an outdated SQLite database (``TablesOutdated``),
        missing tables (``TablesNotCreated``), and a stored object-wildcard tuple
        (``doc:*``) whose shape is not declared in ``object_wildcard_shapes``
        (``ValueError`` with ``bulk=True``, ``AdmissionRejected`` with ``bulk=False``).
        The argument, table and isolation checks run before anything is built. The
        session must be clean (no pending ORM changes)."""
        # Provenance: TK157 (TK123 review item A25b); decisions D1-D7 in
        # docs/tk157-adopt-helper-2026-10-19.md.
        validate_store_id(store_id)
        schema = _schema_text(schema)
        _require_clean_session(session, 'Store.adopt')
        # TK157 review fix: the Store-open arguments are checked here, before anything is
        # built. Store.__init__ checks them too, but only after build_index has committed,
        # which left a half-adopted id whose retry raised IndexExists.
        resolve_paranoia_level(paranoia, default=cls.DEFAULT_PARANOIA)
        _check_open_args(ops, sync)
        try:
            # D3: refuse before building. build_index checks neither, so without these an
            # index would be committed and only the Store open below would refuse.
            assert_read_isolation(session)
            refuse_reusable_node_ids(session)
            if schema is not None:
                # D2: flushed, not committed. build_index's clean-session guard ignores a
                # flushed row, so its one commit lands schema + index together and its
                # rollback undoes both.
                save_schema(session, store_id, schema, object_wildcard_shapes)
            report = build_index(session, store_id, bulk=bulk)
        except Exception as exc:
            session.rollback()
            if isinstance(exc, IndexExists):
                # build_index's own advice (build_index / rebuild_index) is wrong for an
                # adopt caller; same type, adopt's advice.
                raise IndexExists(exc.index_store_id, exc.detail,
                                  hint=f'it is already adopted; open it with '
                                       f'Store(session, {store_id!r})') from exc
            if isinstance(exc, DBAPIError):
                missing = missing_tables(session)
                session.rollback()
                if missing:
                    raise TablesNotCreated(missing) from exc
            raise
        store = cls(session, store_id, ops=ops, sync=sync, paranoia=paranoia)
        return store, report

    # ------------------------------------------------------------------ #
    # Writes: one transaction across both halves (sync schedule)
    # ------------------------------------------------------------------ #

    @overload
    def add_tuple(self, user: str, relation: str, object: str) -> int: ...
    @overload
    def add_tuple(self, subject_predicate: str, subject_type: str, subject_name: str,
                  relation: str, object_type: str, object_name: str) -> int: ...

    def add_tuple(self, *args, **kwargs) -> int:
        """Add one tuple and commit; returns its freshness token (a log id).

        Two call forms, positional or by keyword:

        * the OpenFGA form ``add_tuple(user, relation, object)``:
          ``add_tuple("user:alice", "viewer", "doc:d1")``, a userset as
          ``"group:eng#member"``, every user as ``"user:*"``;
        * six parts ``add_tuple(subject_predicate, subject_type, subject_name, relation,
          object_type, object_name)``, where ``subject_predicate`` is ``"..."`` for a
          bare subject: ``add_tuple("...", "user", "alice", "viewer", "doc", "d1")``.

        Adding a tuple that is already stored is a no-op that returns the current
        watermark. A refused write raises ``AdmissionRejected`` (or a subclass) and
        changes nothing."""
        return self._write('add', *tuple_args('add_tuple', args, kwargs))

    @overload
    def remove_tuple(self, user: str, relation: str, object: str) -> int: ...
    @overload
    def remove_tuple(self, subject_predicate: str, subject_type: str, subject_name: str,
                     relation: str, object_type: str, object_name: str) -> int: ...

    def remove_tuple(self, *args, **kwargs) -> int:
        """Remove one stored tuple and commit; returns its freshness token (a log id).
        Takes the same two call forms as ``add_tuple``. Removing a tuple that is not
        stored raises ``AdmissionRejected`` and changes nothing."""
        return self._write('remove', *tuple_args('remove_tuple', args, kwargs))

    def _write(self, op: str, *raw) -> int:
        _require_clean_session(self.session, f'Store.{op}_tuple')  # TK123 item 10
        reject_ellipsis_predicate(raw[0], f'{op}_tuple', write=True)  # TK123 item 9
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
        # TK167: the id of the log row THIS call appended (None on a duplicate add, which
        # appends nothing and returns the log head). Not ``token``: see
        # ``_name_blocking_backlog_row``.
        own_row_id: int | None = None
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
                own_row_id = hint[0].id if hint else None
                advance_index(self.session, self.cursor, self.widx, self.ruleset,
                              self.proc, rows_hint=hint or None)
            else:
                # async schedule: the worker re-reads from the log; drop the hint so
                # it can never leak into a later transaction.
                self.source.pop_pending_rows()
            self.session.commit()
        except IndexResourceLimit as exc:
            # TK158: the index refused the write on size (ClosureFanoutExceeded /
            # PathCountExceeded, re-raised unchanged by ``apply._apply_row``). That is
            # an expected refusal, not a bug signal, and the evaluator holds exactly
            # one admitted tuple the rollback does not reach: undo THAT, O(1) in the
            # store, instead of the O(store) rebuild below. The rebuild stays the
            # fallback if the undo itself fails. Atomicity is unchanged: the log row
            # and every index change go with the rollback, the set engine with the
            # undo (tests/test_tk158_cheap_refusal.py).
            undrained = self.source.pop_pending_rows()  # discard: nothing spans the rollback
            if undrained:  # raised before the sync arm drained it
                own_row_id = undrained[0].id
            self.session.rollback()
            try:
                self.source.undo_last_admission()
            except Exception:
                self.source.refresh_evaluator()
            _name_blocking_backlog_row(exc, own_row_id, self.store_id)  # TK167
            raise
        except Exception:
            self.source.pop_pending_rows()  # discard: nothing must span the rollback
            self.session.rollback()
            # past admission the evaluator HAS the write in memory: it is a cache
            # over RelationTuple, so rebuild it from the rolled-back truth (also resets
            # the evaluator watermark past the discarded token)
            self.source.refresh_evaluator()
            raise
        # TK163: OUTSIDE the try on purpose -- the write is committed, so neither the
        # rollback nor the evaluator rebuild above applies to a post-commit violation.
        raise_post_commit_violation(self.session)
        return token

    def _commit(self) -> None:
        """``session.commit()``, then re-raise a post-commit ``InvariantViolation``
        the paranoia guard parked during it (TK163). Raising from inside SQLAlchemy's
        ``after_commit`` hook left the session stuck in the COMMITTED state: the
        caller saw ``InvalidRequestError`` and this Store refused every later call.
        Raised here, the session is clean and the Store stays usable."""
        self.session.commit()
        raise_post_commit_violation(self.session)

    # ------------------------------------------------------------------ #
    # The worker loop (async schedule): same apply step, batched
    # ------------------------------------------------------------------ #

    def catch_up(self, batch: int | None = None) -> int:
        """Advance the index over the log until it reaches the head; one transaction
        per batch (exactly-once: applied rows + cursor commit together, so a failed
        batch moves nothing and a retry re-reads the same rows). Returns the number
        of log rows applied. This IS the async worker's body -- a daemon would just
        call it on a schedule.

        The closure fan-out cap is SUSPENDED here: every row is
        already committed truth, so the cap could only stall the index behind it, never
        refuse the write. An over-cap row is applied with a warning instead. The cap
        stays in force on the sync path, where its refusal reaches the writer.

        ``batch`` is ``None`` (no cap) or an ``int >= 1``; anything else raises
        ``ValueError`` / ``TypeError`` before the log is read."""
        # TK165 repair round 1: batch=0 made log_rows(limit=0) return [] with a poison
        # row still pending, which looked like "at the head" and cleared the stall.
        if batch is not None:
            if type(batch) is bool or not isinstance(batch, int):
                raise TypeError(f'batch must be None or an int >= 1, got {batch!r}')
            if batch < 1:
                raise ValueError(f'batch must be None or an int >= 1, got {batch}')
        # Provenance (moved out of the docstring, TK123 item 14): docs/tk111-stall-aware-
        # freshness-2026-10-02.md sec 7.
        # Provenance (moved out of the docstring, TK123 item 14): TK112, 2026-10-03b.
        with self.widx.idx.fanout_cap_suspended():
            return self._catch_up(batch)

    def _catch_up(self, batch: int | None) -> int:
        total = 0
        while True:
            try:
                applied = advance_index(self.session, self.cursor, self.widx,
                                        self.ruleset, self.proc, batch=batch)
                if applied:
                    self._commit()
                elif (self.cursor.stalled_after is not None
                      and self.cursor.stalled_after == self.cursor.applied_log_id
                      and not log_rows(self.session, self.cursor.source_store_id,
                                       self.cursor.applied_log_id, limit=1)):
                    # TK165: a stall recorded at lag 0 (a transient failure on an idle
                    # poll -- the store lock is taken before the log is read). The
                    # zero-row batch just ran under that same lock, on a cursor
                    # refreshed under it, and found nothing past ``applied_log_id``:
                    # the index is at the log head, so the staleness bound is back.
                    # "Zero rows applied" alone does NOT prove that (batch=0 once
                    # read nothing with a poison row pending), so the head is probed
                    # here, independent of ``batch``: no TupleLog id past
                    # ``applied_log_id``, same lock and snapshot. A poison-row stall
                    # is never cleared here: its failing row is past the cursor, so
                    # the probe finds it. Commit (not roll back) so every reader of
                    # the cursor row sees the stall end.
                    self.cursor.stalled_after = None
                    self.cursor.stall_error = None
                    self.session.add(self.cursor)
                    self._commit()
                else:
                    # Blind-audit X2: the zero-row path still opened a transaction
                    # (store lock + cursor refresh + log read). Leaving it open
                    # pins the worker's read snapshot forever (blind daemon) and,
                    # on PostgreSQL, holds the FOR UPDATE store lock indefinitely.
                    self.session.rollback()
            except Exception as e:
                self.session.rollback()
                self._record_stall(e)
                raise
            if not applied:
                return total
            total += applied

    def _record_stall(self, exc: BaseException) -> None:
        """Persist "the apply step could not advance past ``applied_log_id``" on the
        cursor row, in its own transaction, so EVERY reader of this index -- not just
        this instance -- stops treating it as merely behind (TK111/TK112).

        Recorded on ANY failure, transient ones included, on purpose: a false stall
        costs a set-engine fallback until the next successful batch clears it, while a
        missed stall is the unbounded stale ALLOW. A classifier that tried to tell
        poison rows from transient errors would re-open the fail-open the first time
        it guessed wrong. If recording itself fails, the original exception still
        propagates (the caller's ``raise``); the failure to record is attached to it
        as a note rather than replacing it."""
        try:
            self.session.refresh(self.cursor)
            self.cursor.stalled_after = self.cursor.applied_log_id
            # TK123 item 13: name the row the apply step could not get past, so the
            # operator knows which tuple to remove at the source.
            failing = getattr(exc, 'failing_log_row', None)
            where = f'applied through {self.cursor.applied_log_id}'
            if failing is not None:
                where += f'; failing row {failing[0]} ({failing[1]})'
            self.cursor.stall_error = f'{where}: {type(exc).__name__}: {exc}'[:2000]
            self.session.add(self.cursor)
            self.session.commit()
        except Exception as rec:
            self.session.rollback()
            exc.add_note(f'Store: recording the index stall ALSO failed '
                         f'({type(rec).__name__}: {rec}); untokened reads may still '
                         f'be served from the stalled index until it is recorded')
            return
        try:  # TK163: the stall IS recorded; a late violation rides on the original
            raise_post_commit_violation(self.session)
        except InvariantViolation as late:
            exc.add_note(f'Store: the stall was recorded, but the post-commit '
                         f're-check of that commit failed: {late}')

    @property
    def index_stalled(self) -> bool:
        """True while the last recorded apply failure is still at the cursor, i.e. the
        index is not merely behind but has failed to advance. As fresh
        as this session's view of the cursor row -- a replica reader sees a stall
        recorded by another instance after its next ``refresh()``, the same window it
        already accepts for every other write."""
        # Provenance (moved out of the docstring, TK123 item 14): TK111/TK112.
        c = self.cursor
        return c.stalled_after is not None and c.stalled_after == c.applied_log_id

    @property
    def stall_error(self) -> str | None:
        """The recorded failure behind a live stall, for operators; None otherwise."""
        return self.cursor.stall_error if self.index_stalled else None

    def refresh(self) -> None:
        """Replica-reader poll: drop the current read snapshot and every read-path
        cache, so the next queries see the latest committed state coherently
        (fresh transaction + rebuilt set engine; the graph read path is uncached
        by design). Refused on a session with pending ORM changes,
        which the rollback would silently discard."""
        # Provenance (moved out of the docstring, TK123 item 14): blind-audit W2.
        _require_clean_session(self.session, 'Store.refresh')  # TK123 item 10
        self.session.rollback()
        self.source.refresh_evaluator()

    def lag(self) -> int:
        """Log rows the index has not yet applied (0 = fully caught up). A COUNT
        query -- never materializes rows (ids are globally monotonic across stores,
        so counting, not id-subtraction, is also what makes the number meaningful).
        Counted against the cursor row as committed, so another instance's
        ``catch_up()`` shows up without a ``refresh()``."""
        # TK172: never the ORM-cached self.cursor.applied_log_id, which nothing
        # re-reads -- a long-lived monitoring instance reported a stale backlog forever.
        applied = (select(IndexCursor.applied_log_id)
                   .where(IndexCursor.id == self.cursor.id)
                   .scalar_subquery())
        return self.session.exec(
            select(func.count())
            .select_from(TupleLog)
            .where(TupleLog.store_id == self.store_id)
            .where(TupleLog.id > applied)
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
        #
        # TK111/TK112: the BOUND is what makes that sound, and a stalled apply step
        # removes it -- every later row, revocations included, waits behind the one the
        # index cannot apply, forever. So an untokened read is fresh enough only while
        # the index is not stalled. A TOKENED read is unaffected: a token at or below
        # the cursor is genuinely reflected, stalled or not.
        if at_least is None:
            return not self.index_stalled
        return self.cursor.applied_log_id >= at_least

    def _require_index_freshness(self, at_least: int | None, surface: str) -> None:
        """Enforce an ``at_least`` demand on an index-only read surface (ZT-P1-8b).

        Same first two rungs as ``check``'s ladder -- test the in-memory cursor, then
        re-read the cursor row once, because it is routinely just behind another
        session's committed catch-up and that alone satisfies most tokened reads
        without paying for anything. Where ``check`` then falls back to the set engine,
        this raises: see ``LookupNotFresh`` for why there is no third rung here."""
        validate_token(at_least)                                            # TK123 item 11
        refuse_foreign_token(self.session, self.store_id, at_least)          # TK166
        if self._fresh_enough(at_least):
            return
        self.session.refresh(self.cursor)
        if self._fresh_enough(at_least):
            return
        if at_least is None:
            # Provenance: TK111 (stall-aware freshness).
            raise IndexStalled(
                f'{surface}() cannot be served: the index for store {self.store_id!r} '
                f'is STALLED at log id {self.cursor.applied_log_id} (lag {self.lag()}): '
                f'the last catch_up() failed to advance past it -- '
                f'{self.cursor.stall_error} -- so its staleness is unbounded and a '
                f'revoked principal could stay listed indefinitely. check() '
                f'still answers, from the set engine. Clear the stall (a successful '
                f'catch_up(); for a poison row, remove the tuple at the source and '
                f'then call zanzibar.store.rebuild_index(session, {self.store_id!r})) '
                f'and retry.')
        # Provenance: zero-trust review ZT-P1-8b.
        raise LookupNotFresh(
            f'{surface}(at_least={at_least}) cannot be served: the index for store '
            f'{self.store_id!r} has applied through {self.cursor.applied_log_id} '
            f'(lag {self.lag()}). Unlike check(), the lookup surfaces have no '
            f'set-engine fallback -- the two backends return different id domains and '
            f'different marker/exclusion shapes, so serving one in place of the other '
            f'would change the meaning of the result. '
            f'Run catch_up() and retry; for a single '
            f'decision use check(..., at_least={at_least}), which does fall back.'
            + token_diagnosis(self.session, self.store_id, at_least))

    @overload
    def check(self, user: str, relation: str, object: str, *,
              at_least: int | None = None) -> bool: ...
    @overload
    def check(self, subject_predicate: str, subject_type: str, subject_name: str,
              relation: str, object_type: str, object_name: str, *,
              at_least: int | None = None) -> bool: ...

    def check(self, *args, at_least: int | None = None, **kwargs) -> bool:
        """Is the user related to the object? Same two call forms as ``add_tuple``:
        ``check("user:alice", "viewer", "doc:d1")`` or
        ``check("...", "user", "alice", "viewer", "doc", "d1")``.

        ``at_least`` (a token from a write) demands an answer that reflects the log
        through that write; a lagging index then falls back to the set engine. A token
        another store's write returned raises ``ForeignToken`` on every tokened read
        (``check``, ``lookup``, ``lookup_reverse``, ``expand``)."""
        (subject_predicate, s_type, s_name,
         relation, o_type, o_name) = tuple_args('check', args, kwargs)
        reject_ellipsis_predicate(subject_predicate, 'check', write=False)  # TK123 item 9
        validate_token(at_least)                                            # TK123 item 11
        refuse_foreign_token(self.session, self.store_id, at_least)          # TK166
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
        if at_least is None:
            # Untokened read on a STALLED index (TK111/TK112): there is no token to
            # satisfy, so serve the set engine as fresh as this snapshot allows. The
            # stall is what made the index answer unbounded-stale; this one is not.
            self.source.catch_up_evaluator()
            return self.source.check(subject_predicate, s_type, s_name,
                                     relation, o_type, o_name)
        if self.source.evaluator_watermark < at_least:
            self.source.catch_up_evaluator()
            self._require_evaluator_at(at_least)
        return self.source.check(subject_predicate, s_type, s_name,
                                 relation, o_type, o_name)

    @overload
    def lookup(self, user: str, *, at_least: int | None = None,
               object_type: str | None = None,
               relation: str | None = None) -> LookupResult: ...
    @overload
    def lookup(self, subject_predicate: str, subject_type: str, subject_name: str, *,
               at_least: int | None = None, object_type: str | None = None,
               relation: str | None = None) -> LookupResult: ...

    def lookup(self, *args, at_least: int | None = None, object_type: str | None = None,
               relation: str | None = None, **kwargs) -> LookupResult:
        """List-objects: everything the subject can reach, served by the index.

        The subject is ``lookup("user:alice")`` (or ``"group:eng#member"``) or
        ``lookup("...", "user", "alice")``.

        ``object_type`` / ``relation`` keep only the objects of that type and/or relation
        ("the documents alice can view": ``lookup("user:alice", object_type="doc",
        relation="viewer")``), markers and exclusions included. A name the schema does not
        declare matches nothing, as in ``check``.

        ``at_least`` demands the index reflect the log through that token. It is
        ENFORCED, not fulfilled by fallback: satisfied demands are served normally,
        unsatisfiable ones raise ``LookupNotFresh`` (see there -- and note this is the
        revocation surface, where quietly returning the pre-revocation enumeration is
        the failure that matters). Omitting the token keeps the previous behaviour
        exactly: an untokened, bounded-stale index read."""
        subject_predicate, s_type, s_name = lookup_args('lookup', args, kwargs)
        reject_ellipsis_predicate(subject_predicate, 'lookup', write=False)  # TK123 item 9
        shape_filter('lookup', object_type, relation, ('object_type', 'relation'))  # TK156
        self._require_index_freshness(at_least, 'lookup')
        res = self.widx.lookup(subject_predicate, s_type, s_name)
        return self.widx.filter_result(res, object_type, relation)   # TK156

    @overload
    def lookup_reverse(self, relation: str, object: str, *,
                       at_least: int | None = None, subject_type: str | None = None,
                       subject_predicate: str | None = None) -> LookupResult: ...
    @overload
    def lookup_reverse(self, relation: str, object_type: str, object_name: str, *,
                       at_least: int | None = None, subject_type: str | None = None,
                       subject_predicate: str | None = None) -> LookupResult: ...

    def lookup_reverse(self, *args, at_least: int | None = None,
                       subject_type: str | None = None,
                       subject_predicate: str | None = None, **kwargs) -> LookupResult:
        """List-users: everything that can reach the object's relation, as
        ``lookup_reverse("viewer", "doc:d1")`` or ``lookup_reverse("viewer", "doc",
        "d1")``. ``at_least`` behaves exactly as in ``lookup`` -- enforced, never
        silently downgraded.

        ``subject_type`` / ``subject_predicate`` keep only the subjects of that type
        and/or predicate, markers and exclusions included: ``subject_type="user",
        subject_predicate="..."`` keeps the users (``"..."`` is a bare subject), and
        ``subject_predicate="member"`` keeps ``member`` usersets. A name the schema does
        not declare matches nothing, as in ``check``.

        To list the USERS allowed, take the keys of type ``user`` (a granted group's
        members are already listed one by one, refused ones left out) plus each ``user``
        marker minus ``excluded_keys``. A userset key such as ``group:eng#member`` means
        the userset itself is allowed; never expand it to its members, which would
        re-admit a member a ``but not`` refuses."""
        relation, o_type, o_name = lookup_reverse_args('lookup_reverse', args, kwargs)
        shape_filter('lookup_reverse', subject_type, subject_predicate,       # TK156
                     ('subject_type', 'subject_predicate'))
        self._require_index_freshness(at_least, 'lookup_reverse')
        res = self.widx.lookup_reverse(relation, o_type, o_name)
        return self.widx.filter_result(res, subject_type, subject_predicate)   # TK156

    @overload
    def expand(self, relation: str, object: str, *,
               at_least: int | None = None) -> ExpandResult: ...
    @overload
    def expand(self, relation: str, object_type: str, object_name: str, *,
               at_least: int | None = None) -> ExpandResult: ...

    def expand(self, *args, at_least: int | None = None, **kwargs) -> ExpandResult:
        """Zanzibar Expand: every subject that has the relation on the object, as
        ``expand("viewer", "doc:d1")`` or ``expand("viewer", "doc", "d1")``. Returns an
        ``ExpandResult`` of ``(type, name, predicate)`` keys, wildcard markers and the
        keys those markers exclude (see there for how to read the three together).

        Served by the set engine, never the index, so a stalled index does not affect
        it. The engine first reads every write this session can see (including other
        instances'), so an untokened call is as fresh as this session's snapshot.
        ``at_least`` (a token from a write) demands the answer reflect the log through
        that write; if this session's snapshot does not contain it yet, ``StaleRead`` is
        raised -- call ``refresh()`` and retry."""
        relation, o_type, o_name = lookup_reverse_args('expand', args, kwargs)
        validate_token(at_least)
        refuse_foreign_token(self.session, self.store_id, at_least)          # TK166
        # TK155 (docs/tk155-store-expand-2026-10-19.md D2): the set-engine rung of
        # ``check``'s freshness ladder, taken unconditionally because Expand has no index
        # form. Catching up untokened too is O(delta), one empty log query when idle.
        self.source.catch_up_evaluator()
        if at_least is not None:
            self._require_evaluator_at(at_least)
        engine = self.source.engine
        # Delegation only: SetEngine.expand's body is a CORRESPONDENCE.md anchor (TK155 D3).
        m = engine.expand(relation, o_type, o_name)
        key = engine.interner.key
        keys = frozenset(key(i) for i in m.pos) | frozenset(m.ipos)
        # ``pos`` wins over ``neg`` (memberset.MemberSet); they are disjoint by
        # construction, and the subtraction keeps the reading exact if that ever changes.
        excluded = (frozenset(key(i) for i in m.neg) | frozenset(m.ineg)) - keys
        return ExpandResult(keys=keys, markers=frozenset(m.stars), excluded_keys=excluded)

    def _require_evaluator_at(self, at_least: int) -> None:
        # The one StaleRead for a set-engine read (``check``'s fallback rung and
        # ``expand``), called after ``catch_up_evaluator`` so the snapshot is all it
        # can be: if the token is still not visible, refuse rather than serve stale.
        if self.source.evaluator_watermark < at_least:
            raise StaleRead(
                f'token {at_least} is not visible in this session snapshot '
                f'(set engine at log id {self.source.evaluator_watermark}); call '
                f'refresh() to start a fresh read transaction and retry.'
                + token_diagnosis(self.session, self.store_id, at_least))

    def result_keys(self, res: LookupResult) -> set[tuple[str, str, str]]:
        """Translate ``res.node_ids`` (from this store's ``lookup`` / ``lookup_reverse``)
        to ``(type, name, predicate)`` keys, ``predicate`` being the relation or ``"..."``
        for a bare subject: ``{("doc", "d1", "viewer"), ("group", "eng", "member")}``.

        The key FORMAT is the one ``SetEngine.result_keys`` uses, but the key SET may
        differ: a subject that a marker already covers may be listed here too (the set
        engine leaves it out), so compare two results by what they cover -- the keys,
        plus every subject of a marker's shape, minus the excluded keys -- never by
        equality of key sets. This is the CONCRETE part of the result only:
        ``res.markers`` (wildcard grants) and ``excluded_keys(res)`` (the subjects a
        marker covers but which are refused) complete it, and a marker read without its
        exclusions over-grants.

        Read a result before the next write: ids are database row ids, which are never
        reused; an id whose node a later write removed raises ``StaleLookupIds`` (a
        ``KeyError``)."""
        return self._node_keys(res.node_ids, 'node_ids') | set(res.implicit_keys)

    def excluded_keys(self, res: LookupResult) -> set[tuple[str, str, str]]:
        """Translate ``res.excluded_node_ids`` to ``(type, name, predicate)`` keys: the
        portable form of "every subject of a marker's shape EXCEPT these". The companion
        of ``result_keys``; a caller expanding ``res.markers`` must subtract these."""
        return (self._node_keys(res.excluded_node_ids, 'excluded_node_ids')
                | set(res.implicit_excluded_keys))

    def _node_keys(self, ids, field: str) -> set[tuple[str, str, str]]:
        # One chunked IN per 900 ids (SQLite's bind-parameter limit), via the index's
        # own batch loader, scoped to this store.
        nodes = self.widx.idx._load_nodes(ids)
        missing = sorted(i for i in ids if i not in nodes)
        if missing:
            raise StaleLookupIds(
                field, missing,
                f'they name no node in store {self.store_id!r}: the lookup result '
                f'predates a write that removed them, or it came from another store')
        return {(n.type, n.name, n.predicate) for n in nodes.values()}

    def watermark(self) -> int:
        """The newest freshness token in this store's tuple log (0 for an empty log): the
        token of the latest write by any instance, as far as this session can see. Pass
        it as ``at_least`` to read through everything written so far."""
        return self.source.watermark()
