"""ZT-P1-8 regression pins: the two fail-open-direction gaps around the source of
truth, plus the atomicity of the (watermark, rebuild) pair.

Three findings, three sections:

  (a) **ZT-P1-8a -- the unlogged write.** ``SetEngine.add_tuple`` mutates ``TupleV1``
      (the source of truth) and appends NOTHING to ``TupleLogV1``, and the engine used
      to hang off ``TupleSource.engine`` as a plain public attribute. So
      ``store.source.engine.add_tuple(...)`` diverged the source from the index
      permanently and INVISIBLY -- ``lag()`` counts unapplied LOG rows, and there is no
      log row to count. ``test_the_hazard_is_real`` reproduces the divergence through
      the (still-reachable, sanctioned-writer-only) internal body, so the guard below
      is pinned against a demonstrated failure rather than an argued one.

  (b) **ZT-P1-8b -- the freshness demand the lookup surfaces could not express.**
      ``check`` takes ``at_least``; ``lookup``/``lookup_reverse`` took nothing and read
      the possibly-stale index, so a revoked principal stayed ENUMERABLE with no API to
      demand otherwise -- and list-objects/list-users is exactly what a revocation UI
      reads. They now take the token and ENFORCE it (``LookupNotFresh``); see that
      class for why enforcing is the honest option and a set-engine fallback is not.

  (c) **the constructor race.** ``TupleSource.__init__`` / ``refresh_evaluator`` read
      the watermark and rebuild the evaluator in two statements, which is atomic only
      under a pinned read snapshot. The real interleaving needs a real MVCC server and
      lives in ``tests/test_postgres_ha.py``
      ``::test_open_instance_races_a_concurrent_commit``; the pins here drive
      ``_consistent_rebuild``'s two arms directly, so the mechanism is covered by the
      DEFAULT (SQLite) gate too rather than only by the optional PostgreSQL leg.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, func, select

import connectedstore.source as source_mod
from connectedstore import ConnectedStore, LookupNotFresh, TupleLogV1, TupleSource
from connectedstore.source import SNAPSHOT_ATTEMPTS
from index_v4.models import NodeV4
from setengine import SetEngine, TupleV1, UnloggedWriteRefused

SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define editor: [user, group#member]
    define viewer: [user, group#member] or editor
'''


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _count(session, model, store_id) -> int:
    return session.exec(select(func.count()).select_from(model)
                        .where(model.store_id == store_id)).one()


def _keys(session, store_id, result) -> set[tuple[str, str, str]]:
    """Graph ``LookupResult.node_ids`` rendered as ``(type, name, predicate)`` keys --
    the readable form for an assertion (and, not incidentally, the portable form the
    two backends would have to agree on before a lookup fallback could exist)."""
    if not result.node_ids:
        return set()
    rows = session.exec(select(NodeV4).where(NodeV4.store_id == store_id)
                        .where(NodeV4.id.in_(result.node_ids))).all()  # type: ignore[union-attr]
    return {(r.type, r.name, r.predicate) for r in rows}


# =========================================================================== #
# (a) ZT-P1-8a -- a direct set-engine write on a logged store
# =========================================================================== #

def test_the_hazard_is_real(session):
    """WHY the guard exists, demonstrated rather than asserted: a ``TupleV1`` mutation
    with no log row diverges source from index and NOTHING reports it.

    Drives ``_add_tuple_direct`` -- the body behind the guard, which stays reachable
    because ``TupleSource`` legitimately uses it (it appends the log row itself). Here
    it is called with no append, i.e. it plays the exact role the public method used to
    play for any caller holding ``source.engine``."""
    cs = ConnectedStore(session, 'cs', schema=SCHEMA)
    token = cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    session.commit()
    assert token > 0 and cs.check('...', 'user', 'u1', 'viewer', 'doc', 'd1') is True

    logged_before = _count(session, TupleLogV1, 'cs')
    cs.source.engine._add_tuple_direct('...', 'user', 'u2', 'editor', 'doc', 'd1')
    session.commit()

    # The source of truth grew; the log did not; the index never heard about it.
    assert _count(session, TupleV1, 'cs') == 2
    assert _count(session, TupleLogV1, 'cs') == logged_before == 1
    assert cs.check('...', 'user', 'u2', 'viewer', 'doc', 'd1') is False   # WRONG
    assert cs.source.check('...', 'user', 'u2', 'viewer', 'doc', 'd1') is True
    # ...and the divergence is invisible to every freshness signal there is.
    assert cs.lag() == 0
    assert cs.source.evaluator_lag() == 0
    assert cs.cursor.applied_log_id == cs.watermark()


def test_direct_add_on_a_logged_store_is_refused(session):
    cs = ConnectedStore(session, 'cs', schema=SCHEMA)
    cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    session.commit()

    with pytest.raises(UnloggedWriteRefused) as exc:
        cs.source.engine.add_tuple('...', 'user', 'u2', 'editor', 'doc', 'd1')
    # the message has to route the caller somewhere, not just say no
    assert 'TupleSource.add' in str(exc.value)

    # Refused BEFORE any mutation, in memory and on disk alike.
    session.commit()
    assert _count(session, TupleV1, 'cs') == 1
    assert _count(session, TupleLogV1, 'cs') == 1
    assert cs.check('...', 'user', 'u2', 'viewer', 'doc', 'd1') is False
    assert cs.source.check('...', 'user', 'u2', 'viewer', 'doc', 'd1') is False


def test_direct_remove_on_a_logged_store_is_refused(session):
    """The fail-OPEN half: an unlogged remove would leave the grant materialized in the
    index, which keeps answering ALLOW for good."""
    cs = ConnectedStore(session, 'cs', schema=SCHEMA)
    cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    session.commit()

    with pytest.raises(UnloggedWriteRefused):
        cs.source.engine.remove_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    session.commit()
    assert _count(session, TupleV1, 'cs') == 1
    assert cs.check('...', 'user', 'u1', 'viewer', 'doc', 'd1') is True
    assert cs.source.check('...', 'user', 'u1', 'viewer', 'doc', 'd1') is True

    # ...and the sanctioned path still removes it, both halves together.
    cs.remove_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    session.commit()
    assert _count(session, TupleV1, 'cs') == 0
    assert _count(session, TupleLogV1, 'cs') == 2                 # ADD + REMOVE
    assert cs.check('...', 'user', 'u1', 'viewer', 'doc', 'd1') is False


def test_the_engine_attribute_is_read_only(session):
    """Reads through ``source.engine`` are legitimate and must keep working; swapping
    the engine out from under the watermark bookkeeping must not."""
    cs = ConnectedStore(session, 'cs', schema=SCHEMA)
    cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    session.commit()
    assert cs.source.engine.check('...', 'user', 'u1', 'viewer', 'doc', 'd1') is True
    assert cs.source.engine.log_governed is True
    with pytest.raises(AttributeError):
        cs.source.engine = object()                               # type: ignore[misc]


def test_a_standalone_set_engine_is_untouched(session):
    """The engine is ALSO a first-class standalone backend over a store with no log at
    all (the validation matrix's SetBackend, formal/conformance's SetDriver, the
    benchmarks). The guard must be invisible there -- it keys on a flag only
    ``TupleSource`` sets."""
    se = SetEngine(session, 'solo', SCHEMA)
    assert se.log_governed is False
    writes = 0
    for name in ('a', 'b', 'c'):
        assert se.add_tuple('...', 'user', name, 'editor', 'doc', 'd1') is True
        writes += 1
    session.commit()
    assert writes == 3 and _count(session, TupleV1, 'solo') == 3
    assert _count(session, TupleLogV1, 'solo') == 0                # no log: by design
    assert se.check('...', 'user', 'b', 'viewer', 'doc', 'd1') is True
    se.remove_tuple('...', 'user', 'b', 'editor', 'doc', 'd1')
    session.commit()
    assert _count(session, TupleV1, 'solo') == 2
    assert se.check('...', 'user', 'b', 'viewer', 'doc', 'd1') is False


# =========================================================================== #
# (b) ZT-P1-8b -- at_least on the lookup surfaces
# =========================================================================== #

def _async_store(session):
    """Async schedule: writes land in the source of truth only, so the index lags by
    exactly as many log rows as were written -- the lag a token exists to detect."""
    return ConnectedStore(session, 'cs', schema=SCHEMA, sync=False)


def test_lookup_without_a_token_is_unchanged(session):
    """No token = no demand (``_fresh_enough(None)``): the untokened call still serves
    the bounded-stale index, exactly as before this change."""
    cs = _async_store(session)
    token = cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    session.commit()
    assert cs.lag() == 1 and cs.cursor.applied_log_id < token
    assert _keys(session, 'cs', cs.lookup('...', 'user', 'u1')) == set()
    assert _keys(session, 'cs', cs.lookup_reverse('viewer', 'doc', 'd1')) == set()


def test_lookup_refuses_a_token_the_index_cannot_honour(session):
    cs = _async_store(session)
    token = cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    session.commit()
    assert cs.lag() == 1

    refused = 0
    for call in (lambda: cs.lookup('...', 'user', 'u1', at_least=token),
                 lambda: cs.lookup_reverse('viewer', 'doc', 'd1', at_least=token)):
        with pytest.raises(LookupNotFresh) as exc:
            call()
        assert str(token) in str(exc.value) and 'catch_up()' in str(exc.value)
        refused += 1
    assert refused == 2

    # ...and the demand becomes satisfiable exactly when the apply step runs.
    assert cs.catch_up() == 1
    served = 0
    fwd = cs.lookup('...', 'user', 'u1', at_least=token)
    assert ('doc', 'd1', 'viewer') in _keys(session, 'cs', fwd)
    served += 1
    rev = cs.lookup_reverse('viewer', 'doc', 'd1', at_least=token)
    assert ('user', 'u1', '...') in _keys(session, 'cs', rev)
    served += 1
    assert served == 2


def test_revoked_principal_cannot_be_enumerated_under_a_token(session):
    """The headline shape of the finding, in the direction that matters. The grant is
    revoked in the source of truth; the lagging index still lists the principal. A
    revocation UI asking for its own write back must not be handed the stale list."""
    cs = _async_store(session)
    grant = cs.add_tuple('...', 'user', 'victim', 'editor', 'doc', 'd1')
    session.commit()
    assert cs.catch_up() == 1
    assert ('user', 'victim', '...') in _keys(
        session, 'cs', cs.lookup_reverse('viewer', 'doc', 'd1', at_least=grant))

    revoked = cs.remove_tuple('...', 'user', 'victim', 'editor', 'doc', 'd1')
    session.commit()
    assert revoked > grant and cs.lag() == 1

    # Untokened: still listed. That is the documented bounded-stale read, and it is
    # ALSO why the token had to exist -- there was no way to ask for anything better.
    assert ('user', 'victim', '...') in _keys(
        session, 'cs', cs.lookup_reverse('viewer', 'doc', 'd1'))
    with pytest.raises(LookupNotFresh):
        cs.lookup_reverse('viewer', 'doc', 'd1', at_least=revoked)
    with pytest.raises(LookupNotFresh):
        cs.lookup('...', 'user', 'victim', at_least=revoked)

    assert cs.catch_up() == 1
    assert ('user', 'victim', '...') not in _keys(
        session, 'cs', cs.lookup_reverse('viewer', 'doc', 'd1', at_least=revoked))
    assert _keys(session, 'cs', cs.lookup('...', 'user', 'victim',
                                          at_least=revoked)) == set()


def test_a_satisfied_token_is_served_from_the_index(session):
    """Sync schedule: the cursor rides the head, so a tokened lookup is the ordinary
    index read plus one integer comparison. Pins that the guard costs nothing and
    changes no answer when the demand IS met."""
    cs = ConnectedStore(session, 'cs', schema=SCHEMA)
    token = cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    session.commit()
    assert cs.cursor.applied_log_id == token
    compared = 0
    for tok in (None, token, 1):
        assert (_keys(session, 'cs', cs.lookup('...', 'user', 'u1', at_least=tok))
                == {('doc', 'd1', 'editor'), ('doc', 'd1', 'viewer')})
        compared += 1
    assert compared == 3


def test_a_stale_in_memory_cursor_is_refreshed_before_refusing(tmp_path):
    """Rung 2 of the ladder is not dead code: the in-memory cursor row is routinely
    just behind another session's committed catch-up, and re-reading it satisfies the
    token without anyone paying for a fallback or a refusal."""
    url = f'sqlite:///{tmp_path / "zt.db"}'
    engine = create_engine(url)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as sw, Session(engine) as sr:
        writer = ConnectedStore(sw, 'cs', schema=SCHEMA, sync=False)
        reader = ConnectedStore(sr, 'cs', sync=False)       # cursor loaded at 0
        assert reader.cursor.applied_log_id == 0

        token = writer.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
        sw.commit()
        assert writer.catch_up() == 1                       # the worker, elsewhere
        assert reader.cursor.applied_log_id == 0            # ...unseen by the reader

        sr.rollback()                                       # fresh read snapshot
        res = reader.lookup('...', 'user', 'u1', at_least=token)   # must NOT raise
        assert reader.cursor.applied_log_id == token        # rung 2 did the work
        assert ('doc', 'd1', 'viewer') in _keys(sr, 'cs', res)


# =========================================================================== #
# (c) _consistent_rebuild -- both arms, driven directly
# =========================================================================== #

def _watermark_script(monkeypatch, values):
    """Replace ``source.log_watermark`` with a scripted sequence and count the calls.

    The real race needs a second connection committing between two statements of one
    READ COMMITTED transaction, which SQLite cannot produce (see the module docstring).
    Scripting the two reads is the same thing from ``_consistent_rebuild``'s point of
    view -- it sees exactly the value sequence a real interleaving would hand it -- and
    it makes both arms deterministic."""
    calls: list[int] = []
    it = iter(values)

    def fake(session, store_id):
        v = next(it)
        calls.append(v)
        return v

    monkeypatch.setattr(source_mod, 'log_watermark', fake)
    return calls


def test_consistent_rebuild_retries_until_the_pair_agrees(session, monkeypatch):
    cs = ConnectedStore(session, 'cs', schema=SCHEMA)
    cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    session.commit()
    src = cs.source
    assert src.snapshot_attempts == 1                       # uncontended open

    rebuilds = []
    real_rebuild = src.engine.rebuild
    monkeypatch.setattr(src.engine, 'rebuild',
                        lambda: (rebuilds.append(1), real_rebuild())[1])
    # attempt 1: read 5, rebuild, read 6 -> a commit landed across the rebuild, so the
    # pair is NOT self-consistent and the watermark 5 would under-claim it.
    # attempt 2: 6 / 6 -> consistent.
    calls = _watermark_script(monkeypatch, [5, 6, 6, 6])

    src.refresh_evaluator()

    assert src.snapshot_attempts == 2
    assert len(rebuilds) == 2                               # it really re-replayed
    assert calls == [5, 6, 6, 6]                            # 2 reads per attempt
    assert src.evaluator_watermark == 6                     # the CONSISTENT one


def test_consistent_rebuild_falls_back_to_the_shared_lock(session, monkeypatch):
    """Under a sustained write stream the optimistic loop can lose every time; it must
    terminate by locking, not by spinning or by returning an inconsistent pair."""
    cs = ConnectedStore(session, 'cs', schema=SCHEMA)
    cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    session.commit()
    src = cs.source

    locked = []
    real_lock = src._lock_source_shared
    monkeypatch.setattr(src, '_lock_source_shared',
                        lambda: (locked.append(1), real_lock())[1])
    # never two equal reads in a row, until the locked pair at the end
    script = [10 + i for i in range(2 * SNAPSHOT_ATTEMPTS)] + [99]
    calls = _watermark_script(monkeypatch, script)

    src.refresh_evaluator()

    assert locked == [1], 'the loop never fell back -- it would spin under write load'
    assert src.snapshot_attempts == SNAPSHOT_ATTEMPTS + 1
    assert len(calls) == len(script), 'the post-lock pair reads the watermark ONCE'
    assert src.evaluator_watermark == 99
