"""TK166 (2026-10-23): a freshness token issued by ANOTHER store is refused on every
tokened read, with a message that leads with the cause.

Before TK166 a token is just a ``TupleLog`` id, ids count up across every store, and
the freshness tests only compare ids, so a foreign token at or below this store's
cursor was ACCEPTED SILENTLY on check / lookup / lookup_reverse / expand (repro
``docs/tk151-repros-2026-10-20/B4.py``); one above the cursor was refused with
refresh/catch_up-and-retry advice that cannot help (``B5.py``). Now every tokened read
runs ``src/zanzibar/store/source.py::refuse_foreign_token`` (one primary-key lookup of
the token's owning store) before any freshness test, and raises ``ForeignToken``, a
``StaleRead`` subclass. Plan: ``docs/tk166-foreign-token-2026-10-23.md``.

SABOTAGE (2026-10-23, ``.scratch/wf-0p1/tk166-impl/sabotage.py``: the body of
``refuse_foreign_token``'s ``if owner is None or owner == store_id:`` replaced with
``if True:``, anchor count asserted == 1, this module run, file restored and
sha256-checked). Literal result, error lines counted by ``uniq -c``::

    rc= 1
    33 failed, 4 passed in 28.03s
    10 E  Failed: DID NOT RAISE ForeignToken            (below the cursor: B4's silent accept)
    10 E  Failed: DID NOT RAISE StaleRead               (message test, below the cursor)
     2 E  Failed: DID NOT RAISE StaleRead
     1 E  Failed: DID NOT RAISE ForeignToken            (the async-backlog case)
     4 E  zanzibar.store.source.StaleRead: token 4 is not visible in this session snapshot
          (evaluator at 3); call refresh() to start a fre...   (above the cursor: B5's advice)
     2 E  zanzibar.store._store.LookupNotFresh: lookup(at_least=4) cannot be served: ...
     2 E  zanzibar.store._store.LookupNotFresh: lookup_reverse(at_least=4) cannot be served: ...
     2 E  zanzibar.store.source.StaleRead: token 4 is not visible in this session snapshot
          (evaluator at 3); rollback to start a fresh...       (TupleSource.check)

The 4 that stay green are the controls (own tokens x2, a token naming no row, the export).
"""

from __future__ import annotations

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import zanzibar
from zanzibar.store import ForeignToken, LookupNotFresh, StaleRead, Store

SCHEMA = '''model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
'''

ADVICE = ('retry', 'refresh', 'catch_up', 'check(', 'not visible')


@pytest.fixture
def engine():
    # In-memory, one shared connection: the stores share one Session (as B5.py does),
    # so no cross-connection locking is involved and setup stays cheap.
    eng = create_engine('sqlite://', poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


def _surfaces(store: Store):
    """Every tokened read a Store exposes, as ``name -> call(token)``."""
    return {
        'check': lambda t: store.check('user:bob', 'viewer', 'doc:d1', at_least=t),
        'lookup': lambda t: store.lookup('user:bob', at_least=t),
        'lookup_reverse': lambda t: store.lookup_reverse('viewer', 'doc:d1', at_least=t),
        'expand': lambda t: store.expand('viewer', 'doc:d1', at_least=t),
        'source.check': lambda t: store.source.check('user:bob', 'viewer', 'doc:d1',
                                                     at_least=t),
    }


SURFACES = ['check', 'lookup', 'lookup_reverse', 'expand', 'source.check']


@pytest.fixture
def stores(engine, request):
    """``(a, b, below, above)``: a foreign token from store-a at or below store-b's
    index cursor and evaluator watermark, and one above both. ``request.param`` is
    store-b's ``sync``."""
    sync = request.param
    with Session(engine) as s:
        a = Store(s, 'store-a', schema=SCHEMA)
        b = Store(s, 'store-b', schema=SCHEMA, sync=sync)
        below = a.add_tuple('user:carol', 'viewer', 'doc:d9')
        b.add_tuple('user:bob', 'viewer', 'doc:d1')
        b.add_tuple('user:dave', 'viewer', 'doc:d2')
        if not sync:
            b.catch_up()
        b.source.catch_up_evaluator()
        above = a.add_tuple('user:erin', 'viewer', 'doc:d9')
        assert below <= b.cursor.applied_log_id < above
        assert below <= b.source.evaluator_watermark < above
        yield a, b, below, above


@pytest.mark.parametrize('stores', [True, False], ids=['sync', 'async'], indirect=True)
@pytest.mark.parametrize('surface', SURFACES)
@pytest.mark.parametrize('where', ['below_cursor', 'above_cursor'])
def test_a_foreign_token_is_refused_on_every_tokened_read(stores, surface, where):
    _, b, below, above = stores
    token = below if where == 'below_cursor' else above
    with pytest.raises(ForeignToken) as info:
        _surfaces(b)[surface](token)
    err = info.value
    assert (err.token, err.issued_by, err.store_id) == (token, 'store-a', 'store-b')


@pytest.mark.parametrize('stores', [True, False], ids=['sync', 'async'], indirect=True)
@pytest.mark.parametrize('surface', SURFACES)
def test_the_message_leads_with_the_cause_and_gives_no_retry_advice(stores, surface):
    _, b, below, above = stores
    for token in (below, above):
        with pytest.raises(StaleRead) as info:
            _surfaces(b)[surface](token)
        msg = str(info.value)
        assert msg.startswith(f"Token {token} was returned by a write to store "
                              f"'store-a', not 'store-b'"), msg
        assert 'tokens are per-store' in msg
        for word in ADVICE:
            assert word not in msg, (word, msg)


@pytest.mark.parametrize('stores', [True, False], ids=['sync', 'async'], indirect=True)
def test_foreign_token_is_a_staleread_but_not_a_lookupnotfresh(stores):
    _, b, below, _ = stores
    with pytest.raises(StaleRead) as info:          # an existing `except StaleRead` catches it
        b.lookup('user:bob', at_least=below)
    assert type(info.value) is ForeignToken
    assert not isinstance(info.value, LookupNotFresh)
    assert issubclass(ForeignToken, zanzibar.ZanzibarError)


@pytest.mark.parametrize('stores', [True, False], ids=['sync', 'async'], indirect=True)
def test_own_tokens_still_serve(stores):
    """Control: the ownership lookup refuses only a FOREIGN row."""
    _, b, _, _ = stores
    own = b.add_tuple('user:bob', 'viewer', 'doc:d3')
    if not b.sync:
        b.catch_up()
    assert b.check('user:bob', 'viewer', 'doc:d3', at_least=own) is True
    assert ('doc', 'd3', 'viewer') in b.result_keys(b.lookup('user:bob', at_least=own))
    assert ('user', 'bob', '...') in b.result_keys(
        b.lookup_reverse('viewer', 'doc:d3', at_least=own))
    assert ('user', 'bob', '...') in b.expand('viewer', 'doc:d3', at_least=own).keys
    assert b.source.check('user:bob', 'viewer', 'doc:d3', at_least=own) is True
    assert b.check('user:bob', 'viewer', 'doc:d1', at_least=0) is True   # names no row


@pytest.mark.parametrize('stores', [True], ids=['sync'], indirect=True)
def test_a_token_naming_no_row_keeps_its_old_refusal(stores):
    """A token past the log head names no row, so it is not ForeignToken: the
    freshness path's StaleRead / LookupNotFresh and their diagnosis stay as they were."""
    _, b, _, above = stores
    future = above + 10
    with pytest.raises(StaleRead, match='past the newest log id') as info:
        b.check('user:bob', 'viewer', 'doc:d1', at_least=future)
    assert not isinstance(info.value, ForeignToken)
    with pytest.raises(LookupNotFresh, match='past the newest log id') as info:
        b.lookup('user:bob', at_least=future)
    assert not isinstance(info.value, ForeignToken)


def test_async_backlog_cannot_be_certified_by_a_foreign_token(engine):
    """B4 case 4: an async store with a backlog. A foreign token below the cursor used
    to return the stale False as if read-your-writes had been honoured."""
    with Session(engine) as s:
        a = Store(s, 'store-a', schema=SCHEMA)
        foreign = a.add_tuple('user:carol', 'viewer', 'doc:d9')
        c = Store(s, 'store-c', schema=SCHEMA, sync=False)
        c.add_tuple('user:frank', 'viewer', 'doc:d3')
        c.catch_up()
        own = c.add_tuple('user:gina', 'viewer', 'doc:d3')     # not applied (async)
        assert foreign <= c.cursor.applied_log_id < own
        assert c.check('user:gina', 'viewer', 'doc:d3') is False   # untokened: bounded-stale
        with pytest.raises(ForeignToken):
            c.check('user:gina', 'viewer', 'doc:d3', at_least=foreign)
        assert c.check('user:gina', 'viewer', 'doc:d3', at_least=own) is True


@pytest.mark.parametrize('stores', [True], ids=['sync'], indirect=True)
def test_the_refusal_path_diagnosis_also_raises_foreign_token(stores):
    """TK166 review (2026-10-23): ``token_diagnosis`` runs on the refusal path AFTER
    ``refuse_foreign_token``; under PostgreSQL READ COMMITTED a foreign row can become
    visible in between. Its foreign branch must raise ``ForeignToken`` (cause first),
    not append the cause to a retry message. This pins that branch directly, since on
    SQLite the earlier check shadows it on every read surface (which also left the TK123
    S11 sabotage of the old string branch unable to go red)."""
    from zanzibar.store.source import token_diagnosis
    _, b, below, above = stores
    for token in (below, above):
        with pytest.raises(ForeignToken, match=f"^Token {token} was returned by a write "
                                               f"to store 'store-a', not 'store-b'"):
            token_diagnosis(b.session, 'store-b', token)
    assert token_diagnosis(b.session, 'store-b', above + 10).startswith(' Token ')
    assert token_diagnosis(b.session, 'store-b', 0) == ''


def test_foreign_token_is_exported_like_staleread():
    assert zanzibar.ForeignToken is ForeignToken
    assert 'ForeignToken' in zanzibar.__all__
    # TK164 (2026-10-23): exceptions are exported from ``zanzibar`` only.
    assert 'ForeignToken' not in zanzibar.store.__all__
    assert zanzibar.store.ForeignToken is ForeignToken
    assert ForeignToken.__module__ == StaleRead.__module__
