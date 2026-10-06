"""TK111 S5: a write whose closure path count overflows storage is a CLEAN refusal.

``Edge.indirect_edge_count`` counts derivation paths, so a K-layer diamond chain makes
it ``2**K``. Before this fix the overflowing write died at FLUSH with a raw driver error
that no caller could classify: ``DataError: integer out of range`` on PostgreSQL at K=31,
``OverflowError: Python int too large to convert to SQLite INTEGER`` on SQLite at K=63
(both PROBED 2026-09-27d, ``docs/p10-scope-audit-2026-09-27.md`` sec 5 H4).

Now ``ReachabilityIndex._add_indirect_edges_batch_unsafe`` refuses, before its first
mutation, any addition that would push a closure row past ``core.MAX_PATH_COUNT`` (the
int4 ceiling, enforced on both dialects). The error is ``PathCountExceeded``, an
``IndexResourceLimit``, which is an ``AdmissionRejected``. Observed first-hand on
2026-10-03b, sync, SQLite (``docs/tk111-stall-aware-freshness-2026-10-02.md`` sec 7):
    K=30: 122 of 122 writes admitted
    K=31: 124 of 125 admitted; refused ('member','group','B30','member','group','L31')
          PathCountExceeded: path count bound exceeded: this edge would give closure
          row (3 -> 96) 2147483648 distinct ...

What is NOT fixed here, and why: on the async schedule the row is already in the log
when the index refuses it, so the index stalls behind it permanently (reads are correct,
via the TK111 stall marker; see ``tests/test_tk111_stall_aware_freshness.py``).
"""

import pytest
from sqlalchemy import func
from sqlmodel import Session, SQLModel, create_engine, select

import zanzibar.graphindex.core as core
from zanzibar.connectedstore import ConnectedStore
from zanzibar.graphindex import Edge, InvariantViolation, ReachabilityIndex
from zanzibar.graphindex.models import DeltaOutbox, Node, Store
from tests import oracle as O
from tests.test_tk111_stall_aware_freshness import DIAMOND, _diamond_writes
from zanzibar.schema import (AdmissionRejected, IndexResourceLimit,
                               PathCountExceeded)


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _apply(cs, writes):
    """Apply every write; return the ones refused as (tuple, exception)."""
    refused = []
    for op, t in writes:
        try:
            cs.add_tuple(*t) if op == '+' else cs.remove_tuple(*t)
        except Exception as e:  # noqa: BLE001 -- classified by the asserts below
            refused.append((t, e))
    return refused


def _grid(k):
    return [('...', 'user', 'u', 'member', 'group', f'L{i}') for i in range(k + 1)] + \
           [('...', 'user', 'u', 'member', 'group', f'{m}{i}')
            for i in range(k) for m in ('A', 'B')]


def _assert_three_way(cs, writes, refused, k):
    gone = {t for t, _ in refused}
    live = sorted(O.t(*t) for op, t in writes if op == '+' and t not in gone)
    orc = O.Oracle(DIAMOND, live)
    for q in _grid(k):
        want = orc.check(*q)
        assert cs.widx.check(*q) == want, q
        assert cs.source.check(*q) == want, q
        assert cs.check(*q) == want, q


def test_sync_overflow_is_a_clean_refusal_at_the_int4_ceiling(session):
    """K=31 is the first width that overflows int4; it must refuse exactly ONE write,
    with a classifiable type, and leave a consistent, writable store."""
    writes = _diamond_writes(31)
    cs = ConnectedStore(session, 'st', schema=DIAMOND, sync=True)
    refused = _apply(cs, writes)

    assert [t for t, _ in refused] == [('member', 'group', 'B30', 'member', 'group', 'L31')]
    exc = refused[0][1]
    assert isinstance(exc, PathCountExceeded)
    assert isinstance(exc, IndexResourceLimit) and isinstance(exc, AdmissionRejected)
    assert not isinstance(exc, InvariantViolation)
    assert 'path count bound exceeded' in str(exc) and '2147483648' in str(exc)
    # atomic: the refused write is in neither the log nor the set engine nor the index
    assert cs.watermark() == len(writes) - 1
    _assert_three_way(cs, writes, refused, 31)
    # and the store is still writable
    cs.add_tuple('...', 'user', 'z', 'member', 'group', 'L0')
    assert cs.check('...', 'user', 'z', 'member', 'group', 'L31') is True


def test_ceiling_control_k30_admits_everything(session):
    """The CEILING control: one layer less (2**30) is under the bound, so nothing is
    refused. Without it the K=31 test cannot tell a bound at 2**31 from one far lower."""
    writes = _diamond_writes(30)
    cs = ConnectedStore(session, 'st', schema=DIAMOND, sync=True)
    assert _apply(cs, writes) == []
    _assert_three_way(cs, writes, [], 30)


@pytest.mark.parametrize('bound, refused_last', [(8, False), (7, True)])
def test_bound_is_inclusive_and_exact(session, monkeypatch, bound, refused_last):
    """K=3 makes the deepest closure row exactly 8 paths: a bound of 8 admits it and 7
    refuses the last diamond row. Pins ``new > MAX_PATH_COUNT``, not ``>=``."""
    monkeypatch.setattr(core, 'MAX_PATH_COUNT', bound)
    writes = _diamond_writes(3)
    cs = ConnectedStore(session, 'st', schema=DIAMOND, sync=True)
    refused = _apply(cs, writes)
    if refused_last:
        assert [t for t, _ in refused] == [writes[-1][1]]
        assert isinstance(refused[0][1], PathCountExceeded)
        assert ' 8 distinct derivation paths' in str(refused[0][1])
    else:
        assert refused == []
    _assert_three_way(cs, writes, refused, 3)


def _raw_store():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Store(id='s'))
    session.commit()
    return session, ReachabilityIndex(session, store_id='s')


def _counts(session):
    return tuple(session.exec(select(func.count()).select_from(m)).one()
                 for m in (Edge, Node, DeltaOutbox))


def test_direct_edge_row_alone_is_checked(monkeypatch):
    """An edge with no ancestors and no descendants has NO closure deltas; its only
    growing row is its own (a -> b), already at 1 via a -> m -> b. That row is checked
    through ``direct_pair``, which rides the region read; without it this is admitted."""
    session, idx = _raw_store()
    idx.add_edge('p', 't', 'a', 'p', 't', 'm')
    idx.add_edge('p', 't', 'm', 'p', 't', 'b')
    session.commit()
    monkeypatch.setattr(core, 'MAX_PATH_COUNT', 1)
    before = _counts(session)
    with pytest.raises(PathCountExceeded) as ei:
        idx.add_edge('p', 't', 'a', 'p', 't', 'b')
    assert ' 2 distinct derivation paths' in str(ei.value)
    # refused BEFORE the first mutation: nothing written, not even outbox rows
    assert _counts(session) == before
    session.close()


def test_refusal_leaves_no_partial_state_and_removals_are_never_refused(monkeypatch):
    """A refusal mid-region writes nothing. A removal only shrinks counts, so it is
    never refused, even with the bound below what the store already holds."""
    session, idx = _raw_store()
    # x -> {m0, m1} -> s and o -> {n0, n1} -> y: adding s -> o gives the closure row
    # x -> y 2 x 2 = 4 paths, and every OTHER row in the region at most 2. With the
    # bound at 3 the refusal fires on one pair after others have passed the check.
    for mid in ('m0', 'm1'):
        idx.add_edge('p', 't', 'x', 'p', 't', mid)
        idx.add_edge('p', 't', mid, 'p', 't', 's')
    for mid in ('n0', 'n1'):
        idx.add_edge('p', 't', 'o', 'p', 't', mid)
        idx.add_edge('p', 't', mid, 'p', 't', 'y')
    session.commit()
    monkeypatch.setattr(core, 'MAX_PATH_COUNT', 3)
    before = _counts(session)
    with pytest.raises(PathCountExceeded) as ei:
        idx.add_edge('p', 't', 's', 'p', 't', 'o')
    assert ' 4 distinct derivation paths' in str(ei.value)
    assert _counts(session) == before
    session.rollback()

    monkeypatch.setattr(core, 'MAX_PATH_COUNT', 0)
    idx.remove_edge('p', 't', 'm0', 'p', 't', 's')
    session.commit()
    assert _counts(session)[0] < before[0]
    session.close()


@pytest.mark.parametrize('bulk', [True, False])
@pytest.mark.parametrize('bound, refused', [(8, False), (7, True)])
def test_both_build_index_constructors_apply_the_same_bound(monkeypatch, bulk, bound,
                                                             refused):
    """``build_index`` has two constructors over one snapshot. The incremental one
    (``bulk=False``) refuses through the edge-add path; the bulk one
    (``src/zanzibar/graphindex/bulk_build.py``) builds the closure in memory and must refuse the same
    snapshot with the same type, not fail in the driver at INSERT. K=3 is exactly 8."""
    from zanzibar.connectedstore import TupleSource, build_index, save_schema
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        save_schema(session, 'b', DIAMOND)
        src = TupleSource(session, 'b')
        writes = _diamond_writes(3)
        for _op, t in writes:
            src.add(*t)
        session.commit()
        monkeypatch.setattr(core, 'MAX_PATH_COUNT', bound)
        if refused:
            with pytest.raises(PathCountExceeded):
                build_index(session, 'b', bulk=bulk)
        else:
            _cursor, widx, _rs = build_index(session, 'b', bulk=bulk)
            assert widx.check('...', 'user', 'u', 'member', 'group', 'L3') is True
