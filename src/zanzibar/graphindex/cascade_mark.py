"""The cascade-owed mark: refuse to commit a boolean-schema graph write whose derived
relations were never brought up to date.

On a schema with ``and`` / ``but not`` relations, a ``WildcardIndex`` write changes only
the leaf relations; the derived relations follow only when ``DeltaProcessor.run_cascade``
(or ``DeltaProcessor.backfill``) runs in the same transaction. Committing without it would
leave the graph index disagreeing with the set engine, silently. This module turns that
convention into a mechanical refusal at the commit boundary.

How it works. A write on a boolean schema notes, in ``session.info``, that the store owes
a cascade in the current (innermost) transaction. ``run_cascade`` and ``backfill`` clear
the store's debt when they return normally. A ``before_commit`` listener refuses the root
commit with ``CascadeNotRun`` while any store still owes one. A rollback discards the debt
of the transaction it undoes (a savepoint rollback only that savepoint's), and RE-ARMS any
debt that a cascade run inside the rolled-back savepoint had paid, since that cascade's
writes are undone with it. The end of the root transaction (commit, rollback or close)
discards everything. The cost is a few dict and list operations per write and one dict
test per commit; no SQL, ever.

Who is exempt. Only the processor's own output: a write made with the
``processor_writes`` window open AND aimed at a derived-public family
(``WildcardIndex._derived_write_ctx``). A leaf write made with the window open owes a
cascade like any other. The processor-flagged derived write itself is exempt whoever
flips the flag -- a hand-flipped derived write bypasses derived-relation exclusivity, which the mark does not police
(``_assert_derived_exclusivity`` is the fence for that). The other opt-out is the test
waiver ``_cascade_check_waived``, census-pinned.

What it does NOT prove (the bound). It shows that a cascade was CALLED after the last
unpaired write in the transaction, not that it was called correctly: a cascade run with a
watermark that is too high (so it skips rows) clears the mark, as does a cascade run
through any processor on the same session and store id. It never reads the outbox. It
cannot see writes made through a bare ``ReachabilityIndex`` (which is schema-blind), a
``Session`` shared across threads (against the one-Session-per-thread rule, the threads
then share one mark), or a commit issued on the raw ``Connection`` rather than the
``Session``.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

from sqlalchemy import event
from sqlmodel import Session

from zanzibar.schema.errors import ZanzibarError

if TYPE_CHECKING:  # pragma: no cover
    from .wildcard import WildcardIndex

# Provenance: TK3 (decided 2026-10-13 A1, built 2026-10-22); the design, the census and
# the SQLAlchemy event facts it rests on are in docs/tk3-cascade-ran-mark-2026-10-22.md.

#: ``session.info`` key: ``{store_id: [[transaction, op], ...]}`` -- the transactions
#: (innermost at write time) in which a write on that store still owes a cascade.
OWED_KEY = 'zanzibar_cascade_owed'
#: ``session.info`` key: ``{store_id: [[pay_txn, entry], ...]}`` -- debt entries paid by
#: a cascade that ran inside savepoint ``pay_txn``; re-armed if ``pay_txn`` rolls back.
PAID_KEY = 'zanzibar_cascade_paid'
#: ``session.info`` key: ``{store_id: depth}`` -- open ``_cascade_check_waived`` blocks.
WAIVED_KEY = 'zanzibar_cascade_waived'
#: ``session.info`` key: set once the listeners are on this session.
_INSTALLED_KEY = 'zanzibar_cascade_guard'


class CascadeNotRun(ZanzibarError, RuntimeError):
    """A commit was refused because a graph-index write on a schema with ``and`` /
    ``but not`` relations ran no ``DeltaProcessor.run_cascade`` in the same transaction.

    Committing would leave the derived relations stale, so the graph index would disagree
    with the set engine. The transaction is still open when this is raised: roll it back,
    or call ``run_cascade(wm)`` (with ``wm`` the ``outbox_watermark`` read before the
    first write) and commit again. ``zanzibar.Store`` does both for you."""

    def __init__(self, message: str, *, store_ids: tuple[str, ...] = ()):
        super().__init__(message)
        self.store_ids = store_ids


def _innermost(session: Session):
    return session.get_nested_transaction() or session.get_transaction()


def _ensure_guard(session: Session) -> None:
    """Install the three listeners on ``session``, once."""
    info = session.info
    if info.get(_INSTALLED_KEY):
        return
    info[_INSTALLED_KEY] = True
    # insert=True: run BEFORE the paranoia guard's before_commit, so a caller who forgot
    # the cascade is told that, not handed an invariant report of the stale state.
    event.listen(session, 'before_commit', _before_commit, insert=True)
    event.listen(session, 'after_soft_rollback', _after_soft_rollback)
    event.listen(session, 'after_transaction_end', _after_transaction_end)


def note_write(widx: 'WildcardIndex', op: str, *, derived_write: bool = False) -> None:
    """Record that ``widx``'s store owes a cascade in the current transaction.

    A no-op unless the schema compiled boolean plans, for a ``derived_write`` (the
    processor window is open AND the target is a derived-public family -- the
    processor's own output), and inside a waiver. An open ``processor_writes`` window
    alone exempts nothing: a LEAF write made with the flag on still owes. Call it
    AFTER a write's pure pre-checks and BEFORE its first index mutation, so a write
    refused before it changed anything owes nothing, and one refused part-way still
    owes a cascade or a rollback."""
    compiled = widx.schema_info.compiled
    if compiled is None or not compiled.plans or derived_write:
        return
    session = widx.idx.session
    store_id = widx.idx.store_id
    info = session.info
    waived = info.get(WAIVED_KEY)
    if waived and waived.get(store_id):
        return
    _ensure_guard(session)
    owed = info.setdefault(OWED_KEY, {})
    txn = _innermost(session)
    entries = owed.setdefault(store_id, [])
    for entry in entries:
        if entry[0] is txn:
            return
    entries.append([txn, op])


def clear(session: Session, store_id: str) -> None:
    """The store's cascade debt is paid (called when ``run_cascade`` / ``backfill``
    return normally); every nesting level is cleared.

    A payment made inside a SAVEPOINT is provisional: the cascade's writes die with
    that savepoint, so each cleared entry is kept in ``PAID_KEY`` against the
    transaction the cascade ran in, and is re-armed when that transaction (or an
    ancestor savepoint) rolls back.
    A payment at the root needs no record: only the root's own end can undo it, and
    that discards everything."""
    info = session.info
    owed = info.get(OWED_KEY)
    if not owed:
        return
    entries = owed.pop(store_id, None)
    if not entries:
        return
    pay_txn = _innermost(session)
    if pay_txn is not None and pay_txn.parent is not None:
        paid = info.setdefault(PAID_KEY, {}).setdefault(store_id, [])
        paid.extend([pay_txn, e] for e in entries)


def owed_stores(session: Session) -> list[str]:
    """The store ids that still owe a cascade on ``session`` (for tests and messages)."""
    owed = session.info.get(OWED_KEY) or {}
    return sorted(s for s, entries in owed.items() if entries)


def _descends_from(txn, ancestor) -> bool:
    while txn is not None:
        if txn is ancestor:
            return True
        txn = txn.parent
    return False


def _after_soft_rollback(session: Session, previous_transaction) -> None:
    # A savepoint rollback: discard the debt of writes made inside it (or inside a
    # savepoint nested in it). Ended transactions keep their .parent chain (PROBED,
    # plan doc sec 3). A root rollback was already cleared by _after_transaction_end.
    info = session.info
    # First re-arm the payments this rollback undoes: a cascade that ran inside the
    # rolled-back savepoint paid a debt its writes no longer settle. A debt whose write
    # ALSO lies inside it is re-armed here and dropped just below with the rest of that
    # savepoint's debt.
    paid = info.get(PAID_KEY)
    if paid:
        for store_id in list(paid):
            kept_paid = []
            for pay_txn, entry in paid[store_id]:
                if not _descends_from(pay_txn, previous_transaction):
                    kept_paid.append([pay_txn, entry])
                else:
                    entries = info.setdefault(OWED_KEY, {}).setdefault(store_id, [])
                    if not any(e[0] is entry[0] for e in entries):
                        entries.append(entry)
            if kept_paid:
                paid[store_id] = kept_paid
            else:
                del paid[store_id]
    owed = info.get(OWED_KEY)
    if not owed:
        return
    for store_id in list(owed):
        kept = [e for e in owed[store_id] if not _descends_from(e[0], previous_transaction)]
        if kept:
            owed[store_id] = kept
        else:
            del owed[store_id]


def _after_transaction_end(session: Session, transaction) -> None:
    if transaction.parent is None:          # the root: commit, rollback or close
        session.info.pop(OWED_KEY, None)
        session.info.pop(PAID_KEY, None)


def _before_commit(session: Session) -> None:
    # before_commit also fires when a SAVEPOINT is released (PROBED, plan doc sec 2.3);
    # the cascade may legally come later in the root transaction, so only a root commit
    # is checked.
    if session.in_nested_transaction():
        return
    owed = session.info.get(OWED_KEY)
    if not owed:
        return
    pending = {s: entries for s, entries in owed.items() if entries}
    if not pending:
        return
    stores = tuple(sorted(pending))
    detail = ', '.join(f'{s!r} (first unpaired write: {pending[s][0][1]})' for s in stores)
    raise CascadeNotRun(
        f'commit refused: store {detail} wrote to the graph index on a schema with boolean '
        f'(and / but not) relations, but no DeltaProcessor.run_cascade ran in this '
        f'transaction after that write, so committing it would leave the derived '
        f'relations stale and the graph index would disagree with the set engine. The '
        f'transaction is still open. Either roll it back, or call proc.run_cascade(wm) '
        f'in this transaction (wm = outbox_watermark(session, store_id), read BEFORE the '
        f'first write) and commit again; or write through zanzibar.Store, which does both.',
        store_ids=stores)


@contextmanager
def _cascade_check_waived(widx: 'WildcardIndex', *, reason: str) -> Iterator[None]:
    """Test machinery, not an API: writes made through ``widx`` (its session and store)
    INSIDE the block owe no cascade, so the test may commit deliberately stale derived
    state. ``reason`` is required. The waiver covers the writes, not the commit: a write
    after the block owes a cascade as usual. Every file that uses it is pinned by
    ``tests/test_tk3_cascade_mark.py::test_waiver_sites_are_the_census``."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('_cascade_check_waived needs a non-empty reason')
    info = widx.idx.session.info
    store_id = widx.idx.store_id
    waived = info.setdefault(WAIVED_KEY, {})
    waived[store_id] = waived.get(store_id, 0) + 1
    try:
        yield
    finally:
        waived[store_id] -= 1
        if not waived[store_id]:
            del waived[store_id]
