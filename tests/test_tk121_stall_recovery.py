"""TK121: an async index stalled behind a path-count poison row can be RECOVERED.

What TK111 left, by design: ``PathCountExceeded`` is a storage-width bound, never
suspended, and ``TupleSource`` admission cannot see the closure, so on the async schedule
the refused row is already in the log. ``catch_up`` then stalls in front of it for good,
and every later row waits behind it -- including a REMOVE of the very tuple that caused
it. Reads stay correct (the TK111 stall marker), but the index is unavailable.

The recovery is ``connectedstore.rebuild_index``: remove the offending tuple at the
SOURCE, then rebuild the index in place from the snapshot. In place because a
``ConnectedStore`` always reads the index under its own store id. Decision and procedure:
``docs/tk121-stall-recovery-2026-10-04.md``.

What these tests pin:
  * the premise -- after the source REMOVE, ``catch_up`` alone is STILL stalled;
  * the recovery on the real TK111 K=31 diamond, both constructors: no stall, lag 0,
    graph == set engine == oracle over the grid, lookups served again, and the store
    keeps working afterwards on the async schedule;
  * a rebuild that cannot succeed changes NOTHING: same graph rows, same stall marker,
    reads still fall back;
  * the rebuilt state equals a FRESH build of the same snapshot exactly, on a boolean
    schema with residues -- junk planted in every cleared table first, so a table the
    rebuild forgets to clear shows up as a difference;
  * the outbox is preserved (ids stay monotone) and the cursor row is reused;
  * a replica reader sees the recovery after ``refresh()``.
"""

from collections import Counter

import pytest
from sqlalchemy import func
from sqlmodel import Session, SQLModel, create_engine, select

import index_v4.core as core
from connectedstore import (ConnectedStore, IndexStalled, TupleSource, build_index,
                            rebuild_index, save_schema)
from connectedstore.models import IndexCursorV1
from index_v4.models import DeltaOutboxV1, EdgeV4, NodeV4, ResidueRefV1, ResidueV1
from setengine.models import TupleV1
from tests import oracle as O
from tests.test_bulk_build import (_BOOLEAN, _boolean_tuples, _edges_proj, _id_to_key,
                                   _nodes_proj, _residues_proj)
from tests.test_tk111_path_count_bound import _grid
from tests.test_tk111_stall_aware_freshness import DIAMOND, MALLORY, _diamond_writes
from zanzibar_utils_v1 import PathCountExceeded

# The K=31 diamond's one refused write (tests/test_tk111_path_count_bound.py pins it).
POISON = ('member', 'group', 'B30', 'member', 'group', 'L31')
DEEP = ('...', 'user', 'u', 'member', 'group', 'L31')


def _engine(url='sqlite:///:memory:'):
    engine = create_engine(url)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session():
    with Session(_engine()) as s:
        yield s


def _counts(session, store_id='st'):
    return tuple(session.exec(select(func.count()).select_from(m)
                              .where(m.store_id == store_id)).one()
                 for m in (NodeV4, EdgeV4, ResidueV1, ResidueRefV1, DeltaOutboxV1))


def _live(session, store_id='st'):
    rows = session.exec(select(TupleV1).where(TupleV1.store_id == store_id)).all()
    return sorted(O.t(r.subject_predicate, r.subject_type, r.subject_name, r.relation,
                      r.object_type, r.object_name) for r in rows)


def _stall_on_poison(cs, k=31):
    """Log the K-diamond plus mallory's revocation behind it, async; catch_up stalls."""
    for op, t in _diamond_writes(k) + [('-', MALLORY)]:
        cs.add_tuple(*t) if op == '+' else cs.remove_tuple(*t)
    with pytest.raises(PathCountExceeded):
        cs.catch_up(batch=1)
    assert cs.index_stalled and cs.lag() == 2


def _assert_index_agrees(cs, schema, grid):
    """graph index == set engine == oracle, the graph read DIRECTLY (not via the
    fallback), over ``grid``."""
    orc = O.Oracle(schema, _live(cs.session))
    for q in grid:
        want = orc.check(*q)
        assert cs.widx.check(*q) == want, q
        assert cs.source.check(*q) == want, q
        assert cs.check(*q) == want, q


@pytest.mark.parametrize('bulk', [True, False])
def test_k31_poison_row_recovers_by_source_remove_then_rebuild(session, bulk):
    cs = ConnectedStore(session, 'st', schema=DIAMOND, sync=False)
    _stall_on_poison(cs)
    # The operator's starting point: the stall names the refused closure row.
    assert 'PathCountExceeded' in cs.stall_error and '2147483648' in cs.stall_error
    cursor_row_id = cs.cursor.id

    # Step 1, and the PREMISE: the corrective remove lands in the log behind the
    # poison row, so catch-up alone never reaches it.
    cs.remove_tuple(*POISON)
    with pytest.raises(PathCountExceeded):
        cs.catch_up(batch=1)
    assert cs.index_stalled and cs.lag() == 3

    # Step 2: rebuild in place.
    report = rebuild_index(session, 'st', bulk=bulk)
    assert report.constructor == ('bulk' if bulk else 'incremental')
    assert report[0] is cs.cursor and cs.cursor.id == cursor_row_id   # row reused
    assert cs.cursor.applied_log_id == cs.watermark()
    assert not cs.index_stalled and cs.stall_error is None
    assert cs.cursor.stalled_after is None
    assert cs.lag() == 0
    assert cs.catch_up() == 0            # nothing left behind the cursor

    # Served by the INDEX again, and right: mallory's revocation and the 2**30-path
    # grant the index now holds.
    _assert_index_agrees(cs, DIAMOND, _grid(31) + [MALLORY])
    assert cs.widx.check(*MALLORY) is False
    assert cs.widx.check(*DEEP) is True
    assert cs.lookup('...', 'user', 'mallory') is not None   # no IndexStalled
    cs.lookup_reverse('viewer', 'doc', 'secret')

    # And the store keeps working on the async schedule afterwards.
    grant = ('...', 'user', 'w', 'viewer', 'doc', 'secret')
    token = cs.add_tuple(*grant)
    assert cs.check(*grant, at_least=token) is True          # set-engine fallback
    assert cs.catch_up() == 1
    assert cs.widx.check(*grant) is True and cs.check(*grant) is True


@pytest.mark.parametrize('bulk', [True, False])
def test_rebuild_that_cannot_succeed_changes_nothing(session, bulk):
    """Skipping the source remove: the snapshot itself overflows, so the rebuild is
    refused with the bound's own type -- and it must leave the old index, its stall
    marker and the read behaviour EXACTLY as they were. That is what makes the entry
    point safe to try."""
    cs = ConnectedStore(session, 'st', schema=DIAMOND, sync=False)
    _stall_on_poison(cs)
    before = _counts(session)
    edges_before = _edges_proj(session, 'st')
    marker = (cs.cursor.applied_log_id, cs.cursor.stalled_after, cs.cursor.stall_error)

    with pytest.raises(PathCountExceeded):
        rebuild_index(session, 'st', bulk=bulk)

    assert _counts(session) == before
    assert _edges_proj(session, 'st') == edges_before
    session.refresh(cs.cursor)
    assert (cs.cursor.applied_log_id, cs.cursor.stalled_after,
            cs.cursor.stall_error) == marker
    assert cs.index_stalled
    # still correct, still by fallback: the stale index would say True here
    assert cs.widx.check(*MALLORY) is True
    assert cs.check(*MALLORY) is False
    # and the refusal names the recovery, not the pre-TK112 'raise the fan-out cap'
    with pytest.raises(IndexStalled, match='remove the tuple at the source and then '
                                           r'rebuild_index\(\)'):
        cs.lookup('...', 'user', 'mallory')


def test_rebuild_refuses_concurrent_writes_and_changes_nothing(session, monkeypatch):
    """The watermark re-check is shared with build_index: a write that lands during
    the rebuild is refused, and the refusal is atomic like every other one."""
    import connectedstore.build as build_mod
    cs = ConnectedStore(session, 'st', schema=DIAMOND, sync=False)
    _stall_on_poison(cs)
    cs.remove_tuple(*POISON)
    before = _counts(session)

    real = build_mod.log_watermark
    calls = []

    def moving(sess, sid):              # the second read sees one more committed row
        calls.append(sid)
        return real(sess, sid) + (len(calls) > 1)

    monkeypatch.setattr(build_mod, 'log_watermark', moving)
    with pytest.raises(RuntimeError, match='concurrent writes .* during rebuild_index'):
        rebuild_index(session, 'st')
    assert len(calls) == 2
    assert _counts(session) == before
    session.refresh(cs.cursor)
    assert cs.index_stalled


def _refs_proj(session, store_id):
    idmap, _ = _id_to_key(session, store_id)
    rows = session.exec(select(ResidueRefV1).where(ResidueRefV1.store_id == store_id)).all()
    return Counter((idmap[r.subject_node_id], idmap[r.object_node_id]) for r in rows)


def _state(session, store_id):
    return (_nodes_proj(session, store_id), _edges_proj(session, store_id),
            _residues_proj(session, store_id), _refs_proj(session, store_id))


@pytest.mark.parametrize('bulk', [True, False])
def test_rebuilt_state_equals_a_fresh_build_on_a_boolean_schema(bulk):
    """The rebuild must leave EXACTLY what a fresh ``build_index`` of the same snapshot
    builds (natural keys, never raw ids) -- on a boolean schema, so residues and their
    refs exist. Junk is planted in all four cleared tables first; a table the rebuild
    fails to clear then shows up as a difference (or as an id no node owns)."""
    tuples = _boolean_tuples(nusers=3, ngroups=3, ndocs=3)
    with Session(_engine()) as s:
        cs = ConnectedStore(s, 'st', schema=_BOOLEAN, sync=True)
        for t in tuples:
            cs.add_tuple(*t)
        for t in tuples[::4]:                  # churn: the live index is not a fresh build
            cs.remove_tuple(*t)
        assert _counts(s)[2] > 0 and _counts(s)[3] > 0, 'corpus must carry residues + refs'

        # plant junk in every table the rebuild clears
        a = NodeV4(store_id='st', predicate='junk', type='group', name='ja')
        b = NodeV4(store_id='st', predicate='junk', type='group', name='jb')
        s.add_all([a, b])
        s.flush()
        s.add(EdgeV4(store_id='st', subject_id=a.id, object_id=b.id,
                     direct_edge_count=1, indirect_edge_count=1))
        s.add(ResidueV1(store_id='st', object_node_id=b.id, relation='junk',
                        neg=f'[{a.id}]'))
        s.add(ResidueRefV1(store_id='st', subject_node_id=a.id, object_node_id=b.id))
        s.commit()
        outbox_before = s.exec(select(DeltaOutboxV1.id).where(
            DeltaOutboxV1.store_id == 'st').order_by(DeltaOutboxV1.id)).all()
        live_state = _state(s, 'st')

        rebuild_index(s, 'st', bulk=bulk)
        rebuilt = _state(s, 'st')
        live = _live(s)
        # the outbox is kept, and the rebuild's own rows land ABOVE it (ids monotone)
        outbox_after = s.exec(select(DeltaOutboxV1.id).where(
            DeltaOutboxV1.store_id == 'st').order_by(DeltaOutboxV1.id)).all()
        assert outbox_after[:len(outbox_before)] == outbox_before
        assert len(outbox_after) > len(outbox_before)
        assert min(outbox_after[len(outbox_before):]) > max(outbox_before)
        _assert_index_agrees(cs, _BOOLEAN, [
            ('...', 'user', u, rel, 'doc', d)
            for u in ('u1', 'u2', 'u3', 'zz') for d in ('d1', 'd2', 'd3')
            for rel in ('viewer', 'editor', 'public', 'blocked')])

    with Session(_engine()) as f:
        save_schema(f, 'st', _BOOLEAN)
        src = TupleSource(f, 'st')
        for t in live:
            src.add(t.subject_predicate, t.subject_type, t.subject_name, t.relation,
                    t.object_type, t.object_name)
        f.commit()
        build_index(f, 'st', bulk=bulk)
        fresh = _state(f, 'st')

    assert rebuilt == fresh
    assert live_state != fresh          # the rebuild had something to replace


def test_rebuild_requires_an_existing_index_and_a_clean_session(session):
    save_schema(session, 'src', DIAMOND)
    TupleSource(session, 'src').add(*MALLORY)
    session.commit()
    with pytest.raises(ValueError, match='does not exist .*use build_index'):
        rebuild_index(session, 'src')
    build_index(session, 'src')
    with pytest.raises(ValueError, match='rebuild_index replaces an existing index'):
        build_index(session, 'src')
    with pytest.raises(ValueError, match='materializes source'):
        rebuild_index(session, 'other', 'src')
    session.add(TupleV1(store_id='x', subject_predicate='...', subject_type='user',
                        subject_name='a', relation='viewer', object_type='doc',
                        object_name='b'))
    with pytest.raises(ValueError, match='rebuild_index owns the transaction'):
        rebuild_index(session, 'src')
    session.rollback()
    # a separate-id index rebuilds against its own source
    build_index(session, 'src', 'idx')
    report = rebuild_index(session, 'src', 'idx')
    assert report[1].check(*MALLORY) is True
    assert session.exec(select(func.count()).select_from(IndexCursorV1)).one() == 2


def test_replica_reader_sees_the_recovery_after_refresh(tmp_path, monkeypatch):
    """The cursor row is REUSED, so an instance that never ran the rebuild sees it on
    its next ``refresh()`` and serves the index again. K=3 under a bound of 7 is the
    same shape as the K=31 diamond (the last write is the refused one) at file-DB cost."""
    monkeypatch.setattr(core, 'MAX_PATH_COUNT', 7)
    poison = _diamond_writes(3)[-1][1]
    engine = _engine(f'sqlite:///{tmp_path / "st.db"}')
    with Session(engine) as ws, Session(engine) as rs:
        worker = ConnectedStore(ws, 'st', schema=DIAMOND, sync=False)
        for op, t in _diamond_writes(3) + [('-', MALLORY)]:
            worker.add_tuple(*t) if op == '+' else worker.remove_tuple(*t)
        with pytest.raises(PathCountExceeded):
            worker.catch_up()
        reader = ConnectedStore(rs, 'st', schema=DIAMOND, sync=False)
        assert reader.index_stalled
        with pytest.raises(IndexStalled):
            reader.lookup('...', 'user', 'mallory')

        worker.remove_tuple(*poison)
        rebuild_index(ws, 'st')

        assert reader.index_stalled                   # its snapshot predates the rebuild
        reader.refresh()
        assert not reader.index_stalled and reader.lag() == 0
        assert reader.widx.check(*MALLORY) is False
        assert reader.widx.check('...', 'user', 'u', 'member', 'group', 'L3') is True
        reader.lookup('...', 'user', 'mallory')
