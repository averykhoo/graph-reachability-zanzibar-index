"""TK175 (2026-10-30): a node collected and re-created in ONE cascade no longer trips the
``zanzibar_node`` UNIQUE key.

Found by the gate (``tests/test_hypothesis.py::test_add_then_remove_restores_row_multiset``,
a rare draw; seeds 1-6 do not hit it). Schema below, base tuple ``user:u2 r0 doc:d1``, then
the self-parent ``doc:d1 parent doc:d1``: the reconcile of ``doc:d1#r1`` loses u2 (``r0 from
parent`` is now true), so ``DeltaProcessor._gc_public_node`` deletes the ``r1 doc d1`` node;
the reconcile of ``r2 = r1 from parent`` then re-interns that same identity through
``ReachabilityIndex.node``, and SQLAlchemy flushes the INSERT before the pending DELETE.
On 0.1.0 a sync ``add_tuple`` raised a raw ``IntegrityError`` (rolled back: the valid tuple
could never be written) and on async every ``catch_up()`` re-raised (the index stalled). No
wrong answer was served either way.

SABOTAGE (2026-10-30, session): with the ``if self.session.deleted: self.session.flush()``
guard removed from ``core.py::ReachabilityIndex.node`` -> ``rc=1 | 3 failed`` (all three
tests, each with the UNIQUE ``IntegrityError``). The first draft's async leg PASSED under that
sabotage (``2 failed, 1 passed``): it queued both writes and caught up once, and one batch
holding both never creates the node it would collect; hence the intermediate ``catch_up()``.
"""
import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar import Store
from tests.test_processor import build

SCHEMA = """model
  schema 1.1
type user
type folder
  relations
    define r0: [user]
type doc
  relations
    define parent: [doc, folder]
    define r0: [user] and [user]
    define r1: r0 but not (r0 from parent)
    define r2: r1 from parent
"""
BASE = ('...', 'user', 'u2', 'r0', 'doc', 'd1')
SELF_PARENT = ('...', 'doc', 'd1', 'parent', 'doc', 'd1')


def test_processor_add_then_remove_self_parent_restores_rows():
    from zanzibar.graphindex.invariants import snapshot_rows
    session, widx, proc, write = build(SCHEMA)
    write('add', BASE)
    before = snapshot_rows(session, 'test')
    write('add', SELF_PARENT)
    write('remove', SELF_PARENT)
    assert snapshot_rows(session, 'test') == before


@pytest.mark.parametrize('sync', [True, False], ids=['sync', 'async'])
def test_store_writes_the_self_parent(sync):
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        store = Store(session, 's', schema=SCHEMA, sync=sync)
        store.add_tuple('user:u2', 'r0', 'doc:d1')
        if not sync:
            # apply the base first: one batch holding both tuples never creates doc:d1#r1,
            # so it never collects and re-creates it (that leg passed with the guard removed)
            store.catch_up()
        store.add_tuple('doc:d1', 'parent', 'doc:d1')
        if not sync:
            store.catch_up()
            assert not store.index_stalled, store.stall_error
        assert store.check('user:u2', 'r1', 'doc:d1') is False
        assert store.check('user:u2', 'r2', 'doc:d1') is False
        store.remove_tuple('doc:d1', 'parent', 'doc:d1')
        if not sync:
            store.catch_up()
        assert store.check('user:u2', 'r1', 'doc:d1') is True
