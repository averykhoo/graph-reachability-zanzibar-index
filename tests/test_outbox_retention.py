"""ZT-P1-8 (retention): ``delta_outbox_v1`` was append-only -- there was no ``DELETE``
anywhere in ``index_v4/outbox.py``, so the table grew for the life of a store.

``prune_outbox`` is the retention helper. These tests pin the three things that make
it safe rather than merely small:

  (a) it deletes DRAINED rows (id <= a watermark every consumer has passed);
  (b) it never touches UNDRAINED rows, and refuses a nonsensical watermark;
  (c) it keeps the HEAD row as an id anchor -- on SQLite ``delta_outbox_v1.id`` is
      the rowid, and an emptied table restarts at 1, which would hand a consumer
      holding cursor 500 a stream of rows it can never see again. This is the one
      way a "retention" helper could lose a delta permanently;
  (d) the cascade behaves identically afterwards (a pruned store and an unpruned
      control reach byte-identical state under the same op sequence).

Nothing calls it from a write path, by design: what is drained is the caller's
knowledge, not the library's.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from index_v4 import ReachabilityIndex, Store
from index_v4.invariants import snapshot_rows
from index_v4.models import DeltaOutboxV1
from index_v4.outbox import outbox_rows, outbox_watermark, prune_outbox
from index_v4.processor import DeltaProcessor
from zanzibar_utils_v1 import Entity, RelationalTriple, parse_openfga_schema
from tests.wildcard_helpers import make_wildcard_index


@pytest.fixture
def env():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Store(id='s'))
    session.add(Store(id='other'))
    session.commit()
    yield session, ReachabilityIndex(session, store_id='s')
    session.close()


def _ids(session, store_id='s'):
    return [r.id for r in session.exec(
        select(DeltaOutboxV1).where(DeltaOutboxV1.store_id == store_id)
        .order_by(DeltaOutboxV1.id)).all()]


def test_prune_deletes_drained_rows_and_keeps_the_head_anchor(env):
    """(a) + (c). Six flips, all drained; pruning removes five and keeps the head, so
    the watermark is UNCHANGED and the next emitted id is strictly greater."""
    session, idx = env
    for i in range(6):
        idx.add_edge(..., 'user', f'u{i}', 'viewer', 'doc', 'd1')
    session.commit()

    before = _ids(session)
    assert len(before) == 6, 'fixture emitted nothing -- the rest would be vacuous'
    head = outbox_watermark(session, 's')
    assert head == before[-1]

    deleted = prune_outbox(session, 's', head)
    session.commit()

    assert deleted == 5, f'expected 5 drained rows deleted, got {deleted}'
    assert _ids(session) == [head], 'the head row must survive as the id anchor'
    # (c) the anchor is what keeps ids monotone: without it SQLite reuses rowid 1.
    assert outbox_watermark(session, 's') == head
    idx.add_edge(..., 'user', 'later', 'viewer', 'doc', 'd1')
    session.commit()
    assert _ids(session)[-1] > head, 'a pruned outbox must not reissue a spent id'


def test_head_anchor_is_what_prevents_permanent_delta_loss(env):
    """(c), demonstrated rather than argued.

    First half: empty the store's outbox BY HAND (not through ``prune_outbox``) and
    watch SQLite reissue a spent rowid -- a consumer holding the old cursor never sees
    the next delta, and no other record of that reachability flip exists. Second half:
    the same sequence through ``prune_outbox``, which retains the head row, so the new
    delta lands above the cursor and is drained normally.
    """
    from sqlalchemy import delete

    session, idx = env
    for i in range(4):
        idx.add_edge(..., 'user', f'u{i}', 'viewer', 'doc', 'd1')
    session.commit()
    cursor = outbox_watermark(session, 's')          # what a drained consumer holds
    assert cursor == 4

    # -- the hazard, by hand ------------------------------------------------- #
    session.execute(delete(DeltaOutboxV1).where(DeltaOutboxV1.store_id == 's'))
    session.commit()
    idx.add_edge(..., 'user', 'after-wipe', 'viewer', 'doc', 'd1')
    session.commit()
    reissued = _ids(session)
    assert len(reissued) == 1 and reissued[0] <= cursor, \
        f'expected a reissued rowid at or below {cursor}, got {reissued}'
    assert outbox_rows(session, 's', cursor) == [], \
        'the hazard did not reproduce -- the rest of this test would prove nothing'

    # -- the same shape through prune_outbox --------------------------------- #
    for i in range(3):
        idx.add_edge(..., 'user', f'v{i}', 'viewer', 'doc', 'd2')
    session.commit()
    cursor = outbox_watermark(session, 's')
    prune_outbox(session, 's', cursor)
    session.commit()
    idx.add_edge(..., 'user', 'after-prune', 'viewer', 'doc', 'd2')
    session.commit()
    fresh = outbox_rows(session, 's', cursor)
    assert len(fresh) == 1, 'the post-prune delta must be visible to the held cursor'
    assert fresh[0].id > cursor
    assert fresh[0].object_name == 'd2' and fresh[0].subject_name == 'after-prune'


def test_prune_never_touches_undrained_rows(env):
    """(b). Rows above the supplied watermark are the ones no consumer has seen; they
    must survive verbatim, and the surviving stream must still drain correctly."""
    session, idx = env
    for i in range(3):
        idx.add_edge(..., 'user', f'a{i}', 'viewer', 'doc', 'd1')
    session.commit()
    drained_wm = outbox_watermark(session, 's')
    for i in range(3):
        idx.add_edge(..., 'user', f'b{i}', 'viewer', 'doc', 'd2')
    session.commit()

    undrained = [r.id for r in outbox_rows(session, 's', drained_wm)]
    assert len(undrained) == 3, 'no undrained rows -- test would prove nothing'

    deleted = prune_outbox(session, 's', drained_wm)
    session.commit()

    assert deleted == 3, f'expected the 3 drained rows, got {deleted}'
    assert [r.id for r in outbox_rows(session, 's', drained_wm)] == undrained
    assert _ids(session) == undrained


def test_prune_refuses_nonsense_and_is_a_no_op_when_nothing_is_drained(env):
    session, idx = env
    idx.add_edge(..., 'user', 'a', 'viewer', 'doc', 'd1')
    session.commit()
    before = _ids(session)
    assert len(before) == 1

    with pytest.raises(ValueError):
        prune_outbox(session, 's', -1)
    assert prune_outbox(session, 's', 0) == 0, 'watermark 0 means nothing is drained'
    # A single row IS the head, so even a fully-drained watermark keeps it.
    assert prune_outbox(session, 's', before[0]) == 0
    assert prune_outbox(session, 'no-such-store', 10 ** 9) == 0
    assert _ids(session) == before


def test_prune_is_scoped_to_one_store(env):
    """The outbox is shared by every store on the bind; pruning one must not touch
    another's stream (the ``store_id`` predicate is load-bearing, not decorative)."""
    session, idx = env
    other = ReachabilityIndex(session, store_id='other')
    for i in range(4):
        idx.add_edge(..., 'user', f'u{i}', 'viewer', 'doc', 'd1')
        other.add_edge(..., 'user', f'u{i}', 'viewer', 'doc', 'd1')
    session.commit()
    other_before = _ids(session, 'other')
    assert len(other_before) == 4 and len(_ids(session, 's')) == 4

    deleted = prune_outbox(session, 's', outbox_watermark(session, 's'))
    session.commit()
    assert deleted == 3
    assert _ids(session, 'other') == other_before


# --------------------------------------------------------------------------- #
# (d) the cascade is unaffected by retention
# --------------------------------------------------------------------------- #

_SCHEMA = '''
    type user
    type doc
      relations
        define blocked: [user]
        define editor: [user]
        define viewer: editor but not blocked
'''

_OPS = [
    ('add', ('...', 'user', 'alice', 'editor', 'doc', 'd1')),
    ('add', ('...', 'user', 'bob', 'editor', 'doc', 'd1')),
    ('add', ('...', 'user', 'bob', 'blocked', 'doc', 'd1')),
    ('add', ('...', 'user', 'alice', 'editor', 'doc', 'd2')),
    ('remove', ('...', 'user', 'bob', 'blocked', 'doc', 'd1')),
    ('remove', ('...', 'user', 'alice', 'editor', 'doc', 'd1')),
]


def _run(prune: bool):
    rs = parse_openfga_schema(_SCHEMA, enable_boolean=True)
    session, widx = make_wildcard_index(rs.schema_info)
    proc = DeltaProcessor(widx, rs.compiled)
    applied = 0
    for op, raw in _OPS:
        wm = outbox_watermark(session, 'test')
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]),
                                  Ellipsis if raw[0] == '...' else raw[0])
        fn = widx.add_tuple if op == 'add' else widx.remove_tuple
        for d in rs.apply(triple):
            fn('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
               d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
        proc.run_cascade(wm)
        session.commit()
        applied += 1
        if prune:
            # Prune to the watermark this write's cascade just fully consumed: a
            # cascade never reads below its own start watermark, so everything at or
            # below it is drained by the contract prune_outbox documents.
            prune_outbox(session, 'test', outbox_watermark(session, 'test'))
            session.commit()
    assert applied == len(_OPS)
    answers = {(u, d): proc.derived_check('doc', 'viewer', d, ('...', 'user', u))
               for u in ('alice', 'bob') for d in ('d1', 'd2')}
    state = snapshot_rows(session, 'test')
    rows = len(_ids(session, 'test'))
    session.close()
    return answers, state, rows


def test_cascade_state_is_identical_with_and_without_pruning():
    pruned_answers, pruned_state, pruned_rows = _run(prune=True)
    control_answers, control_state, control_rows = _run(prune=False)

    assert len(control_answers) == 4 and any(control_answers.values()), \
        'control produced no positive answers -- comparison would be vacuous'
    assert pruned_answers == control_answers
    assert pruned_state == control_state
    # ...and retention actually did something: the control keeps every row ever
    # emitted, the pruned store keeps only its anchors.
    assert pruned_rows < control_rows
