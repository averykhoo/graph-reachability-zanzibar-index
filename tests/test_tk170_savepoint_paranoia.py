"""TK170: releasing a SAVEPOINT must not run the paranoia guard's post-commit hook.

SQLAlchemy fires ``after_commit`` for a nested transaction's commit (a savepoint
RELEASE) as well as for the root commit. Before the fix,
``zanzibar.graphindex.invariants.ParanoiaGuard.after_commit`` ran on a release, opened
a fresh ``Session`` on the same bind, and on in-memory SQLite (``SingletonThreadPool``)
that fresh session shared the caller's DBAPI connection: its ``close()`` rolled back the
WHOLE open transaction, savepoint writes included. Observed first-hand 2026-10-26
(``paranoia full``, a ban written, cascade run in a savepoint, savepoint released, root
commit; check ``user:alice viewer doc:d1``, truth False)::

    full inside sp after cascade False
    full after release True          <- stale ALLOW
    full after commit True
    full N4d raised OperationalError (sqlite3.OperationalError) no such savepoint: sa_savepoint_1

``off`` and ``residue`` answered False throughout. The fix returns early from
``after_commit`` while ``sess.in_nested_transaction()`` (the savepoint is still the
session's current transaction when SQLAlchemy dispatches the event). Plan doc:
``docs/tk170-savepoint-paranoia-2026-10-26.md``.

SABOTAGE (2026-10-26, first-hand). (1) The early return deleted: ``5 failed, 4 passed``::

    [full]    test_a_released_savepoint_keeps_its_cascade
              AssertionError: stale ALLOW after the release
    [full]    test_an_outer_rollback_after_an_inner_release_works
              sqlalchemy.exc.OperationalError: (sqlite3.OperationalError)
              no such savepoint: sa_savepoint_1
    [off], [full]  test_the_post_commit_hook_runs_on_the_root_commit_only
              AssertionError: a savepoint release ran the post-commit re-check
    [residue] test_the_post_commit_hook_runs_on_the_root_commit_only
              AssertionError: a release emptied the I14 sets

(2) The guard widened to ``if sess.in_transaction(): return`` (which also skips the
ROOT commit, so it would pass the first two tests): ``3 failed, 6 passed``, every row of
``test_the_post_commit_hook_runs_on_the_root_commit_only`` with
``AssertionError: the root commit did not empty the I14 sets``.
"""
from __future__ import annotations

import pytest

from zanzibar.graphindex import invariants
from zanzibar.graphindex.cascade_mark import owed_stores

from tests.test_tk3_cascade_mark import G, _stale_ban_setup

LEVELS = ['off', 'residue', 'full']


@pytest.mark.parametrize('paranoia', LEVELS)
def test_a_released_savepoint_keeps_its_cascade(paranoia):
    """Equivalence: the cascaded answer (False, as the set engine says) must survive
    the release AND the root commit, at every paranoia level."""
    graph, wm = _stale_ban_setup(paranoia)
    try:
        sp = graph.session.begin_nested()
        graph.proc.run_cascade(wm)
        assert not graph.check('user:alice', 'viewer', 'doc:d1'), 'cascade did not run'
        sp.commit()
        assert not graph.check('user:alice', 'viewer', 'doc:d1'), \
            'stale ALLOW after the release'
        assert owed_stores(graph.session) == []
        graph.session.commit()
        assert not graph.check('user:alice', 'viewer', 'doc:d1'), \
            'stale ALLOW after the root commit'
    finally:
        graph.session.close()


@pytest.mark.parametrize('paranoia', LEVELS)
def test_an_outer_rollback_after_an_inner_release_works(paranoia):
    """The release must not destroy the OUTER savepoint ("no such savepoint")."""
    graph = G(paranoia=paranoia)
    try:
        outer = graph.session.begin_nested()
        inner = graph.session.begin_nested()
        graph.write('user:alice', 'viewer', 'doc:d1')
        inner.commit()
        outer.rollback()
        assert owed_stores(graph.session) == []
        graph.session.commit()
        assert not graph.check('user:alice', 'viewer', 'doc:d1')
    finally:
        graph.session.close()


@pytest.mark.parametrize('paranoia', LEVELS)
def test_the_post_commit_hook_runs_on_the_root_commit_only(paranoia, monkeypatch):
    """Instrument control: the post-commit re-check must still run on the ROOT commit
    (a fix that silenced after_commit altogether would pass the two tests above), and a
    release must neither run it nor empty the I14 sets that only a commit may empty.

    The guard is installed at 'full' for the 'off' row too (an 'off' guard has no
    post-commit hook to observe), so the row pins the same contract on a guard that a
    re-install upgraded in place."""
    graph = G(paranoia=paranoia)
    guard = invariants.install_paranoia(graph.session, graph.store_id,
                                        graph.rs.schema_info, level='full')
    if paranoia == 'residue':
        guard.level = 'residue'   # observe the cheap tier's half (the I14 sets)
    phases: list[str] = []
    real = invariants.check_invariants

    def spy(sess, store_id, *a, **kw):
        if sess is not graph.session:
            phases.append('post-commit')
        return real(sess, store_id, *a, **kw)

    monkeypatch.setattr(invariants, 'check_invariants', spy)
    try:
        wm = graph.wm()
        sp = graph.session.begin_nested()
        graph.write('user:alice', 'viewer', 'doc:d1')
        graph.proc.run_cascade(wm)
        guard.i14_entities.add(('doc', 'sentinel'))
        sp.commit()
        assert phases == [], 'a savepoint release ran the post-commit re-check'
        assert ('doc', 'sentinel') in guard.i14_entities, 'a release emptied the I14 sets'
        graph.session.commit()
        assert guard.i14_entities == set(), 'the root commit did not empty the I14 sets'
        expected = [] if paranoia == 'residue' else ['post-commit']
        assert phases == expected
        assert graph.check('user:alice', 'viewer', 'doc:d1')
    finally:
        graph.session.close()
