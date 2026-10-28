"""TK163: a post-commit ``InvariantViolation`` reaches a ``Store`` caller as itself, the
write it reports on is committed, and the Store stays usable.

Under paranoia ``full`` / ``fixpoint`` the guard re-checks the store AFTER every root
commit (``zanzibar.graphindex.invariants.ParanoiaGuard.after_commit``). Before the fix
that re-check raised from inside SQLAlchemy's ``after_commit`` hook, which leaves the
session stuck in the COMMITTED state; ``Store._write``'s ``session.rollback()`` then
raised ``InvalidRequestError`` over the violation, and every later call on the Store
raised it too. Observed first-hand 2026-10-28 (``docs/tk151-repros-2026-10-20/B1.py``)::

    caller type: sqlalchemy.exc.InvalidRequestError
    caller msg : This session is in 'committed' state; no further SQL can be emitted within this transaction.
    __context__: InvariantViolation | store='s' [post-commit] SABOTAGE post-commit
    check b RAISED InvalidRequestError: This session is in 'committed' state; ...
    fresh Store sees b: True | a: True

The fix: a session the Store opted in (``defer_post_commit_violations``) gets the
violation PARKED on ``session.info``; ``Store`` re-raises it from
``raise_post_commit_violation`` once ``commit()`` has returned. ``residue`` runs no
post-commit re-check at all, so it never had this shape (pinned below). A raw session
that did NOT opt in keeps the old raise-from-commit behaviour (pinned below, so the
deferral can never silently swallow a violation). Plan doc:
``docs/tk163-post-commit-violation-2026-10-28.md``.

Instrument: ``invariants.check_invariants`` is wrapped to raise ONLY on a session other
than the Store's own -- the post-commit pass runs in a fresh Session on the same bind,
the pre-commit pass on the Store's session.

SABOTAGE (2026-10-28, first-hand, each mutation edited into
``src/zanzibar/graphindex/invariants.py`` and reverted; restored run ``6 passed``):

(1) Deferral removed (``if not sess.info.get(_DEFER_POST_COMMIT_KEY):`` -> ``if True:``,
i.e. the pre-fix raise from the hook): ``4 failed, 2 passed`` -- both rows of
``test_sync_write_...`` and ``test_async_catch_up_...``, each with::

    E   zanzibar.graphindex.invariants.InvariantViolation: SABOTAGE post-commit
    E   zanzibar.graphindex.invariants.InvariantViolation: store='s' [post-commit] SABOTAGE post-commit
    E   sqlalchemy.exc.InvalidRequestError: This session is in 'committed' state; no further SQL can be emitted within this transaction.

(2) Deferral made unconditional (``-> if False:``): ``1 failed, 5 passed`` --
``test_a_raw_session_that_did_not_opt_in_still_raises_from_commit`` with
``Failed: DID NOT RAISE InvariantViolation``.

(3) The parked violation swallowed (``raise_post_commit_violation``'s ``pending = ...
and None``): ``4 failed, 2 passed`` -- the same four rows as (1), each
``Failed: DID NOT RAISE InvariantViolation``.

(4) ``build.py``'s two new ``raise_post_commit_violation(session)`` calls replaced by
``pass`` (2026-10-28, first-hand): ``1 failed, 6 passed`` --
``test_rebuild_index_on_a_store_session_raises_its_own_violation`` with
``Failed: DID NOT RAISE InvariantViolation``.
"""
from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from zanzibar import InvariantViolation, Store
from zanzibar.graphindex import invariants
from zanzibar.store.models import TupleLog

SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
"""


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f'sqlite:///{tmp_path / "tk163.db"}')
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


def _sabotage_post_commit(monkeypatch, own_session, calls=None):
    real = invariants.check_invariants

    def fake(sess, store_id, *a, **k):
        if sess is not own_session:
            if calls is not None:
                calls.append(store_id)
            raise InvariantViolation('SABOTAGE post-commit')
        return real(sess, store_id, *a, **k)

    monkeypatch.setattr(invariants, 'check_invariants', fake)
    return real


def _logged(engine, store_id):
    with Session(engine) as s:
        return [(r.subject_name, r.op) for r in
                s.exec(select(TupleLog).where(TupleLog.store_id == store_id)).all()]


@pytest.mark.parametrize('paranoia', ['full', 'fixpoint'])
def test_sync_write_raises_invariantviolation_after_commit(engine, monkeypatch, paranoia):
    st = Store(Session(engine), 's', schema=SCHEMA, paranoia=paranoia)
    st.add_tuple('user:a', 'viewer', 'doc:1')
    real = _sabotage_post_commit(monkeypatch, st.session)

    with pytest.raises(InvariantViolation) as ei:
        st.add_tuple('user:b', 'viewer', 'doc:1')
    msg = str(ei.value)
    assert "store='s' [post-commit] SABOTAGE post-commit" in msg, msg
    assert 'IS committed' in msg, msg
    assert type(ei.value) is InvariantViolation

    monkeypatch.setattr(invariants, 'check_invariants', real)
    # the write is committed: log and index, seen by an independent Store
    assert [n for n, _ in _logged(engine, 's')] == ['a', 'b']
    fresh = Store(Session(engine), 's')
    assert fresh.check('user:b', 'viewer', 'doc:1') is True
    # and the original Store is still usable: read, write, refresh
    assert st.session.in_transaction() is False
    assert st.check('user:b', 'viewer', 'doc:1') is True
    st.add_tuple('user:c', 'viewer', 'doc:1')
    st.refresh()
    assert st.check('user:c', 'viewer', 'doc:1') is True
    assert st.lag() == 0


@pytest.mark.parametrize('paranoia', ['full', 'fixpoint'])
def test_async_catch_up_raises_invariantviolation_and_stays_usable(
        engine, monkeypatch, paranoia):
    st = Store(Session(engine), 's', schema=SCHEMA, paranoia=paranoia, sync=False)
    st.add_tuple('user:a', 'viewer', 'doc:1')
    real = _sabotage_post_commit(monkeypatch, st.session)

    with pytest.raises(InvariantViolation) as ei:
        st.catch_up()
    assert 'IS committed' in str(ei.value)

    monkeypatch.setattr(invariants, 'check_invariants', real)
    # the batch landed (cursor at the head); the catch_up failure recorded a stall,
    # as any catch_up failure does, and the next poll at the head clears it
    assert st.lag() == 0
    assert st.index_stalled, 'a catch_up failure must record a stall'
    assert 'IS committed' in st.stall_error
    st.catch_up()
    assert not st.index_stalled
    assert st.check('user:a', 'viewer', 'doc:1') is True


def test_residue_runs_no_post_commit_recheck(engine, monkeypatch):
    """``residue`` never had the TK163 shape: its guard returns from after_commit
    before any check, so the instrument is never called on the fresh session."""
    st = Store(Session(engine), 's', schema=SCHEMA, paranoia='residue')
    calls: list[str] = []
    _sabotage_post_commit(monkeypatch, st.session, calls)
    st.add_tuple('user:a', 'viewer', 'doc:1')
    assert calls == []
    assert st.check('user:a', 'viewer', 'doc:1') is True


def test_a_raw_session_that_did_not_opt_in_still_raises_from_commit(engine, monkeypatch):
    """Instrument control: the deferral is opt-in per session. A raw session with a
    guard and no ``defer_post_commit_violations`` keeps raising from ``commit()`` --
    an unconditional deferral would swallow the violation for every non-Store caller."""
    Store(Session(engine), 's', schema=SCHEMA, paranoia='off')
    raw = Session(engine)
    invariants.install_paranoia(raw, 's', level='full')
    calls: list[str] = []
    _sabotage_post_commit(monkeypatch, raw, calls)
    raw.exec(select(TupleLog)).all()
    with pytest.raises(InvariantViolation, match=r'\[post-commit\] SABOTAGE'):
        raw.commit()
    assert calls == ['s']


def test_rebuild_index_on_a_store_session_raises_its_own_violation(engine, monkeypatch):
    """``rebuild_index`` on a Store's opted-in session (the recovery the stall message
    names) must raise the violation parked by ITS commit there, not leave it for the
    next Store call to raise as if it were that call's (review finding, 2026-10-28)."""
    from zanzibar.store import rebuild_index
    st = Store(Session(engine), 's', schema=SCHEMA, paranoia='full')
    st.add_tuple('user:a', 'viewer', 'doc:1')
    real = _sabotage_post_commit(monkeypatch, st.session)
    with pytest.raises(InvariantViolation, match=r'SABOTAGE post-commit'):
        rebuild_index(st.session, 's')
    monkeypatch.setattr(invariants, 'check_invariants', real)
    st.add_tuple('user:b', 'viewer', 'doc:1')   # nothing left parked for this call
    assert st.check('user:b', 'viewer', 'doc:1') is True
