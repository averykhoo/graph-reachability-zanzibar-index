"""TK112: the closure fan-out cap is a SYNC-ADMISSION bound (decided 2026-10-03b).

Under ``but not`` a revocation is often an ADD: banning a group, or adding a user to a
group that is already banned. And a REMOVE can restore a grant through the delta
processor (the un-ban). The cap therefore cannot promise "revocations are never refused"
without switching itself off for most of a boolean schema. The decision
(``docs/tk111-stall-aware-freshness-2026-10-02.md`` sec 7, a ``fable`` consult adopted by
the session) is:

  * SYNC: every edge ADD is capped, whatever it means for access. The refusal is LOUD
    (``ClosureFanoutExceeded``) and ATOMIC: the write is in neither the log, nor the set
    engine, nor the index, so the backends agree and the caller knows it did not land.
  * ASYNC ``catch_up`` and the non-bulk ``build_index``: never capped. Those rows are
    already committed, so a refusal could only stall the index, never refuse the write.
    An over-cap row is applied with a warning.

The three witnesses are the P10 scout's, PROBED at cap 20 (sec 6 of the doc above):
  A2 ban:   ``+ group:big#member banned doc:d``      anc=30 desc=0   (refused, sync)
  K  join:  ``+ user:victim member group:big``       anc=0  desc=60  (refused, sync)
  D3 unban: ``- user:u0 banned doc:d`` -> processor adds ``u0 -> doc:d#viewer``
            with 30 folder readers below it          (refused, sync; fails CLOSED)
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from connectedstore import ConnectedStore, TupleSource, build_index, save_schema
from index_v4.core import MAX_CLOSURE_FANOUT_ENV
from tests import oracle as O
from zanzibar_utils_v1 import ClosureFanoutExceeded

SCHEMA = '''
type user
type group
  relations
    define member: [user]
type doc
  relations
    define grant: [user, group#member]
    define banned: [user, group#member]
    define viewer: grant but not banned
type folder
  relations
    define reader: [doc#viewer]
'''

CAP = 20
N = 30


def _ban_case():
    setup = [('+', ('...', 'user', f'u{i}', 'member', 'group', 'big')) for i in range(N)]
    setup.append(('+', ('...', 'user', 'u0', 'grant', 'doc', 'd')))
    op = ('+', ('member', 'group', 'big', 'banned', 'doc', 'd'))
    probe = ('...', 'user', 'u0', 'viewer', 'doc', 'd')
    return setup, op, probe


def _join_case():
    setup = [('+', ('...', 'user', f'u{i}', 'member', 'group', 'big')) for i in range(N)]
    setup += [('+', ('member', 'group', 'big', 'banned', 'doc', f'd{j}')) for j in range(N)]
    setup.append(('+', ('...', 'user', 'victim', 'grant', 'doc', 'd0')))
    op = ('+', ('...', 'user', 'victim', 'member', 'group', 'big'))
    probe = ('...', 'user', 'victim', 'viewer', 'doc', 'd0')
    return setup, op, probe


def _unban_case():
    setup = [('+', ('viewer', 'doc', 'd', 'reader', 'folder', f'f{j}')) for j in range(N)]
    setup += [('+', ('...', 'user', 'u0', 'grant', 'doc', 'd')),
              ('+', ('...', 'user', 'u0', 'banned', 'doc', 'd'))]
    op = ('-', ('...', 'user', 'u0', 'banned', 'doc', 'd'))
    probe = ('...', 'user', 'u0', 'reader', 'folder', 'f0')
    return setup, op, probe


CASES = {'ban': _ban_case, 'join-banned-group': _join_case, 'unban': _unban_case}


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _do(cs, op, t):
    return cs.add_tuple(*t) if op == '+' else cs.remove_tuple(*t)


def _oracle(writes):
    live = set()
    for op, t in writes:
        (live.add if op == '+' else live.discard)(O.t(*t))
    return O.Oracle(SCHEMA, sorted(live))


@pytest.mark.parametrize('case', sorted(CASES))
def test_sync_over_cap_write_is_refused_loudly_and_atomically(session, case):
    setup, (op, t), probe = CASES[case]()
    cs = ConnectedStore(session, 's', schema=SCHEMA, sync=True)
    cs.widx.idx.max_closure_fanout = 0          # build the region freely
    for o, w in setup:
        _do(cs, o, w)
    cs.widx.idx.max_closure_fanout = CAP
    head = cs.watermark()
    before = _oracle(setup).check(*probe)
    after = _oracle(setup + [(op, t)]).check(*probe)
    assert before != after, 'the witness must CHANGE access, or it pins nothing'

    with pytest.raises(ClosureFanoutExceeded):
        _do(cs, op, t)

    # atomic: not in the log, and neither backend reflects it
    assert cs.watermark() == head
    assert cs.widx.check(*probe) is before
    assert cs.source.check(*probe) is before
    assert cs.check(*probe) is before
    # the store is still writable
    _do(cs, '+', ('...', 'user', 'fresh', 'grant', 'doc', 'other'))
    assert cs.check('...', 'user', 'fresh', 'viewer', 'doc', 'other') is True


@pytest.mark.parametrize('case', sorted(CASES))
def test_async_apply_is_never_capped(session, case, caplog):
    setup, (op, t), probe = CASES[case]()
    cs = ConnectedStore(session, 's', schema=SCHEMA, sync=False)
    cs.widx.idx.max_closure_fanout = CAP        # tight from the start, never relaxed
    for o, w in setup + [(op, t)]:
        _do(cs, o, w)
    want = _oracle(setup + [(op, t)]).check(*probe)

    with caplog.at_level('WARNING', logger='index_v4.core'):
        cs.catch_up()
    assert cs.lag() == 0 and not cs.index_stalled
    assert any('materialised anyway' in r.getMessage() for r in caplog.records)
    # answered by the INDEX (not stalled, so no set-engine fallback), and right
    assert cs.widx.check(*probe) is want
    assert cs.source.check(*probe) is want
    assert cs.check(*probe) is want
    # the window closed with catch_up: a direct over-cap write on this index refuses
    assert not cs.widx.idx._fanout_cap_suspended.on


def test_non_bulk_build_index_is_never_capped(session, monkeypatch):
    """The bulk constructor was never capped; the incremental reference constructor
    must admit the same snapshot, or the two disagree on what a store can hold."""
    setup, (op, t), probe = _ban_case()
    save_schema(session, 'b', SCHEMA)
    src = TupleSource(session, 'b')
    for o, w in setup + [(op, t)]:
        (src.add if o == '+' else src.remove)(*w)
    session.commit()
    monkeypatch.setenv(MAX_CLOSURE_FANOUT_ENV, str(CAP))

    _cursor, widx, _rs = build_index(session, 'b', bulk=False)

    assert widx.idx.max_closure_fanout == CAP
    assert widx.check(*probe) is _oracle(setup + [(op, t)]).check(*probe) is False


def test_suspend_window_is_reentrant_and_thread_scoped(session):
    import threading
    cs = ConnectedStore(session, 's', schema=SCHEMA, sync=True)
    idx = cs.widx.idx
    seen = []
    with idx.fanout_cap_suspended():
        with idx.fanout_cap_suspended():
            assert idx._fanout_cap_suspended.on
        assert idx._fanout_cap_suspended.on, 'the inner exit must restore, not clear'
        th = threading.Thread(target=lambda: seen.append(idx._fanout_cap_suspended.on))
        th.start()
        th.join()
    assert seen == [False], 'another thread must see a CLOSED window'
    assert not idx._fanout_cap_suspended.on
