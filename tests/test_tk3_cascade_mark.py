"""TK3 (2026-10-22): the always-on cascade-owed mark.

On a schema with ``and`` / ``but not`` relations, a ``WildcardIndex`` write that is
committed without ``DeltaProcessor.run_cascade`` (or ``DeltaProcessor.backfill``) in the
same transaction leaves the derived relations stale: the graph index then disagrees with
the set engine, silently. ``src/zanzibar/graphindex/cascade_mark.py`` refuses that commit
with ``CascadeNotRun``. Plan, census and design: docs/tk3-cascade-ran-mark-2026-10-22.md.

Positive pins (W*) write, skip the cascade, commit, and expect the refusal. Negative pins
(N*) are the controls: nothing that cascades, rolls back, or never wrote may be refused.

Sabotage evidence (2026-10-22, each applied alone to the named file and restored, bytes
checked by SHA-256; full outputs in docs/tk3-cascade-ran-mark-2026-10-22.md, correction
"BUILD stage"). Literal tails over this file (S1: + tests/test_matrix.py):
  M0 control, break test_top_level_export  -> 1 failed, 1 passed (that test only)
  S1 drop the clear in run_cascade          -> 27 failed, 21 passed; every boolean matrix
     case red with "CascadeNotRun: commit refused: store 'g' (first unpaired write:
     add_tuple) ..."
  S2 before_commit returns at once          -> 14 failed, 17 passed (W1-W6, N4b, N4e, ...)
  S3 no mark in _remove_tuple_trusted       -> 1 failed, 30 passed (W2)
  S4 drop the root after_transaction_end clear -> 1 failed, 30 passed (N3b)
  S5 mark keyed by id(widx)                 -> 18 failed, 13 passed (N7b among them)
  S6 clear at the START of run_cascade      -> 1 failed, 30 passed (N12)
  S7 hook ignores in_nested_transaction()   -> 3 failed, 28 passed (N4b, N4c, N4d)
  S8 drop the processor_writes skip         -> 1 failed, 30 passed (N11; the first N11
     was vacuous, 31 passed, and was rebuilt to repair a really stale key)
  S9 a waiver planted in tests/_tk3_s9_probe.py -> test_waiver_sites_are_the_census red
     ("Extra items in the left set: 'tests/_tk3_s9_probe.py'")
"""
from __future__ import annotations

import re
import threading
from pathlib import Path
from types import EllipsisType

import pytest
from sqlmodel import Session, SQLModel, create_engine

import zanzibar
from zanzibar.graphindex import (CascadeNotRun, DeltaProcessor, IndexStore,
                                 ReachabilityIndex, WildcardIndex)
from zanzibar.graphindex import cascade_mark
from zanzibar.graphindex.cascade_mark import _cascade_check_waived, owed_stores
from zanzibar.graphindex.invariants import install_paranoia
from zanzibar.graphindex.outbox import outbox_watermark
from zanzibar.schema import (AdmissionRejected, Entity, RelationalTriple,
                             parse_openfga_schema)
from tests.wildcard_helpers import make_wildcard_index

ROOT = Path(__file__).resolve().parents[1]

BOOLEAN = '''
model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define owner: [user]
    define banned: [user]
    define viewer: [user, group#member] but not banned
'''

UNION = '''
model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
    define editor: [user]
'''


def _norm(pred: str | EllipsisType) -> str:
    return '...' if pred is Ellipsis else pred


class G:
    """One boolean (or union) graph index on its own in-memory session."""

    def __init__(self, schema: str = BOOLEAN, store_id: str = 'g', *, session=None,
                 paranoia='full'):
        self.rs = parse_openfga_schema(schema)
        if session is None:
            self.session, self.widx = make_wildcard_index(self.rs.schema_info, store_id,
                                                          paranoia=paranoia)
        else:
            self.session = session
            session.add(IndexStore(id=store_id))
            session.commit()
            install_paranoia(session, store_id, self.rs.schema_info, level=paranoia)
            self.widx = WildcardIndex(ReachabilityIndex(session, store_id=store_id),
                                      self.rs.schema_info)
        self.store_id = store_id
        self.proc = (DeltaProcessor(self.widx, self.rs.compiled)
                     if self.rs.compiled is not None and self.rs.compiled.plans else None)

    def wm(self) -> int:
        return outbox_watermark(self.session, self.store_id)

    def write(self, user: str, relation: str, obj: str, op: str = 'add') -> None:
        """Route one raw tuple through RuleSet.apply onto the index; NO cascade."""
        s_type, rest = user.split(':')
        s_name, _, s_pred = rest.partition('#')
        o_type, o_name = obj.split(':')
        sp = s_pred if s_pred else Ellipsis
        triple = RelationalTriple(Entity(s_type, s_name), relation, Entity(o_type, o_name), sp)
        fn = self.widx.add_tuple if op == 'add' else self.widx.remove_tuple
        for d in self.rs.apply(triple):
            fn(_norm(d.subject_predicate), d.subject.type, d.subject.name,
               d.relation, d.object.type, d.object.name)

    def committed_write(self, user: str, relation: str, obj: str, op: str = 'add') -> None:
        wm = self.wm()
        self.write(user, relation, obj, op)
        if self.proc is not None:
            self.proc.run_cascade(wm)
        self.session.commit()

    def check(self, user: str, relation: str, obj: str) -> bool:
        s_type, s_name = user.split(':')
        o_type, o_name = obj.split(':')
        return self.widx.check('...', s_type, s_name, relation, o_type, o_name)


@pytest.fixture
def g():
    graph = G()
    yield graph
    graph.session.rollback()
    graph.session.close()


# --------------------------------------------------------------------------- positive pins

def test_w1_add_without_cascade_is_refused_at_commit(g):
    """W1, and the instrument control: the refusal is CascadeNotRun, raised BEFORE the
    paranoia guard (full tier installed) could report the stale state some other way."""
    g.write('user:alice', 'viewer', 'doc:d1')
    assert owed_stores(g.session) == ['g']
    with pytest.raises(CascadeNotRun) as ei:
        g.session.commit()
    assert ei.value.store_ids == ('g',)
    assert isinstance(ei.value, zanzibar.ZanzibarError)
    assert isinstance(ei.value, RuntimeError)


def test_w2_remove_without_cascade_is_refused(g):
    g.committed_write('user:alice', 'viewer', 'doc:d1')
    assert g.check('user:alice', 'viewer', 'doc:d1')
    g.write('user:alice', 'viewer', 'doc:d1', op='remove')
    with pytest.raises(CascadeNotRun):
        g.session.commit()


def test_w2b_a_banned_write_without_cascade_is_refused(g):
    """The write that matters most: the revocation-shaped leaf. Committed uncascaded, the
    graph would keep granting what the set engine now denies."""
    g.committed_write('user:alice', 'viewer', 'doc:d1')
    g.write('user:alice', 'banned', 'doc:d1')
    with pytest.raises(CascadeNotRun):
        g.session.commit()
    assert g.check('user:alice', 'viewer', 'doc:d1')    # the stale ALLOW it refused to commit


def test_w3_remove_node_without_cascade_is_refused(g):
    g.committed_write('user:alice', 'owner', 'doc:x')
    g.widx.remove_node('owner', 'doc', 'x')
    with pytest.raises(CascadeNotRun) as ei:
        g.session.commit()
    assert 'remove_node' in str(ei.value)


def test_w4_wildcard_backfill_without_cascade_is_refused(g):
    g.widx.backfill()
    with pytest.raises(CascadeNotRun) as ei:
        g.session.commit()
    assert 'WildcardIndex.backfill' in str(ei.value)


def test_w5_a_write_refused_after_the_mark_still_owes(g):
    """Fail-closed: a refusal raised once the write is past its pure pre-checks (here the
    core's cycle refusal) does not pay the debt; roll back or cascade."""
    g.committed_write('group:a#member', 'member', 'group:b')
    with pytest.raises(AdmissionRejected):
        g.write('group:b#member', 'member', 'group:a')
    with pytest.raises(CascadeNotRun):
        g.session.commit()


def test_w6_the_message_names_the_store_and_both_remedies(g):
    g.write('user:alice', 'viewer', 'doc:d1')
    with pytest.raises(CascadeNotRun) as ei:
        g.session.commit()
    msg = str(ei.value)
    assert "'g'" in msg
    assert 'run_cascade' in msg and 'outbox_watermark' in msg
    assert 'roll it back' in msg and 'zanzibar.Store' in msg


def test_top_level_export():
    assert zanzibar.CascadeNotRun is CascadeNotRun is cascade_mark.CascadeNotRun


# --------------------------------------------------------------------------- negative pins

def test_n1_write_then_cascade_commits(g):
    g.committed_write('user:alice', 'viewer', 'doc:d1')
    g.committed_write('user:alice', 'banned', 'doc:d1')
    assert not g.check('user:alice', 'viewer', 'doc:d1')
    assert owed_stores(g.session) == []


def test_n2_write_then_processor_backfill_commits(g):
    g.write('user:alice', 'viewer', 'doc:d1')
    g.proc.backfill()
    g.session.commit()
    assert g.check('user:alice', 'viewer', 'doc:d1')


def test_n3_rollback_clears_the_mark(g):
    g.write('user:alice', 'viewer', 'doc:d1')
    g.session.rollback()
    assert owed_stores(g.session) == []
    g.session.commit()                                  # an unrelated, empty commit
    g.committed_write('user:bob', 'viewer', 'doc:d1')   # and a real one


def test_n3b_close_clears_the_mark(g):
    g.write('user:alice', 'viewer', 'doc:d1')
    g.session.close()
    assert owed_stores(g.session) == []


def test_n4a_rolled_back_savepoint_owes_nothing(g):
    sp = g.session.begin_nested()
    g.write('user:alice', 'viewer', 'doc:d1')
    sp.rollback()
    assert owed_stores(g.session) == []
    g.session.commit()


def test_n4b_released_savepoint_still_owes(g):
    sp = g.session.begin_nested()
    g.write('user:alice', 'viewer', 'doc:d1')
    sp.commit()
    with pytest.raises(CascadeNotRun):
        g.session.commit()


def test_n4c_releasing_a_savepoint_is_not_refused_and_a_later_cascade_pays(g):
    """``before_commit`` also fires on a savepoint RELEASE; the cascade may legally come
    later in the root transaction, so the release must not be refused."""
    wm = g.wm()
    sp = g.session.begin_nested()
    g.write('user:alice', 'viewer', 'doc:d1')
    sp.commit()                                         # must not raise
    g.proc.run_cascade(wm)
    g.session.commit()
    assert g.check('user:alice', 'viewer', 'doc:d1')


def test_n4d_outer_savepoint_rollback_discards_an_inner_released_write():
    # paranoia='off' on purpose: with the 'full' paranoia guard installed, releasing the
    # inner savepoint on SQLite loses the outer one ("no such savepoint: sa_savepoint_1"
    # on the outer rollback). PROBED 2026-10-22 to be independent of the cascade mark
    # (the same failure with note_write patched to a no-op); recorded on the TK3 row.
    g = G(paranoia='off')
    try:
        outer = g.session.begin_nested()
        inner = g.session.begin_nested()
        g.write('user:alice', 'viewer', 'doc:d1')
        inner.commit()
        assert owed_stores(g.session) == ['g']
        outer.rollback()
        assert owed_stores(g.session) == []
        g.session.commit()
    finally:
        g.session.close()


def test_n4e_a_write_outside_the_rolled_back_savepoint_still_owes(g):
    g.write('user:alice', 'viewer', 'doc:d1')
    sp = g.session.begin_nested()
    g.write('user:bob', 'viewer', 'doc:d1')
    sp.rollback()
    with pytest.raises(CascadeNotRun):
        g.session.commit()


def test_n5_pure_union_schema_never_owes():
    graph = G(UNION)
    try:
        assert graph.proc is None
        graph.write('user:alice', 'viewer', 'doc:d1')
        graph.widx.backfill()
        graph.session.commit()
        assert cascade_mark._INSTALLED_KEY not in graph.session.info
    finally:
        graph.session.close()


def test_n6_a_write_refused_before_mutating_owes_nothing(g):
    with pytest.raises(ValueError, match='derived'):
        g.widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')   # I5 refusal
    with pytest.raises(AdmissionRejected):
        g.widx.remove_tuple('...', 'user', 'zed', 'owner', 'doc', 'nowhere')
    with pytest.raises(AdmissionRejected):
        g.widx.remove_node('owner', 'doc', 'nowhere')
    assert owed_stores(g.session) == []
    g.session.commit()


def test_n7_two_stores_on_one_session_are_tracked_apart():
    a = G(store_id='a')
    b = G(store_id='b', session=a.session)
    try:
        wm_b = b.wm()
        a.write('user:alice', 'viewer', 'doc:d1')
        b.write('user:alice', 'viewer', 'doc:d1')
        b.proc.run_cascade(wm_b)          # pays b's debt only
        with pytest.raises(CascadeNotRun) as ei:
            a.session.commit()
        assert ei.value.store_ids == ('a',)
    finally:
        a.session.rollback()
        a.session.close()


def test_n7b_a_second_facade_on_the_same_store_pays_the_debt(g):
    """The mark belongs to the (session, store), not to a facade: writing through one
    WildcardIndex and cascading through a processor built on another is correct."""
    other = WildcardIndex(ReachabilityIndex(g.session, store_id='g'), g.rs.schema_info)
    other_proc = DeltaProcessor(other, g.rs.compiled)
    wm = g.wm()
    g.write('user:alice', 'viewer', 'doc:d1')
    other_proc.run_cascade(wm)
    g.session.commit()
    assert g.check('user:alice', 'viewer', 'doc:d1')


def test_n8_one_session_per_thread_marks_apart(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "t.db"}')
    SQLModel.metadata.create_all(engine)
    rs = parse_openfga_schema(BOOLEAN)
    with Session(engine) as s0:
        s0.add(IndexStore(id='g'))
        s0.commit()
    errors: list[BaseException] = []
    a_owes = threading.Event()
    b_done = threading.Event()

    def thread_b():
        try:
            with Session(engine) as sb:
                widx = WildcardIndex(ReachabilityIndex(sb, store_id='g'), rs.schema_info)
                proc = DeltaProcessor(widx, rs.compiled)
                wm = outbox_watermark(sb, 'g')
                widx.add_tuple('...', 'user', 'bob', 'banned', 'doc', 'd9')
                proc.run_cascade(wm)
                sb.commit()
                a_owes.wait(10)
                assert owed_stores(sb) == []
                sb.commit()                    # thread A's debt is not thread B's
        except BaseException as e:              # noqa: BLE001 -- re-raised below
            errors.append(e)
        finally:
            b_done.set()

    t = threading.Thread(target=thread_b)
    t.start()
    with Session(engine) as sa:
        widx = WildcardIndex(ReachabilityIndex(sa, store_id='g'), rs.schema_info)
        # wait until B has committed its write, so A's write lock cannot block B
        import time
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with Session(engine) as probe:
                if outbox_watermark(probe, 'g') > 0:
                    break
            time.sleep(0.01)
        triple = RelationalTriple(Entity('user', 'alice'), 'viewer', Entity('doc', 'd1'), Ellipsis)
        for d in rs.apply(triple):
            widx.add_tuple(_norm(d.subject_predicate), d.subject.type, d.subject.name,
                           d.relation, d.object.type, d.object.name)
        a_owes.set()
        b_done.wait(10)
        with pytest.raises(CascadeNotRun):
            sa.commit()
        sa.rollback()
    t.join(10)
    assert not errors, errors


def test_n9_after_a_refusal_cascade_and_commit_recover(g):
    wm = g.wm()
    g.write('user:alice', 'viewer', 'doc:d1')
    with pytest.raises(CascadeNotRun):
        g.session.commit()
    g.proc.run_cascade(wm)
    g.session.commit()
    assert g.check('user:alice', 'viewer', 'doc:d1')
    g.proc.audit_fixpoint()
    g.session.commit()


def test_n10_the_composed_path_commits():
    from zanzibar import Store
    from zanzibar.store import build_index
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        store = Store(session, 'sync', schema=BOOLEAN)
        store.add_tuple('user:alice', 'viewer', 'doc:d1')
        store.add_tuple('user:alice', 'banned', 'doc:d1')
        assert not store.check('user:alice', 'viewer', 'doc:d1')
        store.remove_tuple('user:alice', 'banned', 'doc:d1')
        assert store.check('user:alice', 'viewer', 'doc:d1')

        lazy = Store(session, 'async', schema=BOOLEAN, sync=False)
        lazy.add_tuple('user:bob', 'viewer', 'doc:d2')
        lazy.add_tuple('user:bob', 'banned', 'doc:d2')
        lazy.catch_up()
        assert owed_stores(session) == []

        for bulk, target in ((False, 'inc'), (True, 'blk')):
            build_index(session, 'sync', index_store_id=target, bulk=bulk)
        assert owed_stores(session) == []


def test_n11_the_processors_own_writes_owe_nothing(g):
    """A processor write OUTSIDE run_cascade / backfill (a reconcile that repairs a stale
    key) must not arm the mark. The stale key is built under a waiver, so the reconcile
    really writes: the control is that it changes the answer."""
    g.committed_write('user:alice', 'viewer', 'doc:d1')
    with _cascade_check_waived(g.widx, reason='TK3 N11: a stale key for reconcile to repair'):
        g.write('user:alice', 'viewer', 'doc:d1', op='remove')
    g.session.commit()
    assert g.check('user:alice', 'viewer', 'doc:d1'), 'the fixture is not stale'
    assert g.proc.reconcile('doc', 'viewer', 'd1') is not False
    assert not g.check('user:alice', 'viewer', 'doc:d1'), 'reconcile wrote nothing'
    assert owed_stores(g.session) == []
    g.session.commit()
    g.proc.audit_fixpoint()
    g.session.commit()


def test_n12_a_cascade_that_raises_leaves_the_mark(g, monkeypatch):
    wm = g.wm()
    g.write('user:alice', 'viewer', 'doc:d1')

    def boom(_wm):
        raise RuntimeError('planted cascade failure')
    monkeypatch.setattr(g.proc, '_run_cascade', boom)
    with pytest.raises(RuntimeError, match='planted'):
        g.proc.run_cascade(wm)
    with pytest.raises(CascadeNotRun):
        g.session.commit()


def test_n12b_a_fixpoint_tier_that_raises_leaves_the_mark(g, monkeypatch):
    """The clear sits AFTER ``_check_cascade_fixpoint``: a cascade whose fixpoint tier
    raised has not paid. (FIX stage 2026-10-22: moving the clear between _run_cascade
    and the fixpoint tier kept the whole file green -- reviewer sabotage R2.)"""
    wm = g.wm()
    g.write('user:alice', 'viewer', 'doc:d1')

    def boom():
        raise RuntimeError('planted fixpoint-tier failure')
    monkeypatch.setattr(g.proc, '_check_cascade_fixpoint', boom)
    with pytest.raises(RuntimeError, match='planted'):
        g.proc.run_cascade(wm)
    with pytest.raises(CascadeNotRun):
        g.session.commit()


# ------------------------------------------------- FIX stage 2026-10-22: the two holes

def _stale_ban_setup(paranoia='full'):
    """viewer granted and committed; then a ban written, NOT yet cascaded. A commit of
    this state without a surviving cascade is a stale ALLOW (graph True, truth False)."""
    graph = G(paranoia=paranoia)
    graph.committed_write('user:alice', 'viewer', 'doc:d1')
    wm = graph.wm()
    graph.write('user:alice', 'banned', 'doc:d1')
    return graph, wm


@pytest.mark.parametrize('paranoia', ['off', 'full'])
def test_w7_a_cascade_in_a_rolled_back_savepoint_does_not_pay(paranoia):
    """Hole 1 (reviewer probes P1 / p_holes.py::p1): the cascade's writes die with the
    savepoint, so its payment must too. Pre-fix: 'owed after sp rollback: []' and the
    commit went through with viewer=True although alice is banned."""
    graph, wm = _stale_ban_setup(paranoia)
    try:
        sp = graph.session.begin_nested()
        graph.proc.run_cascade(wm)
        assert not graph.check('user:alice', 'viewer', 'doc:d1')   # the cascade ran
        sp.rollback()
        assert graph.check('user:alice', 'viewer', 'doc:d1'), 'fixture not stale'
        assert owed_stores(graph.session) == ['g']
        with pytest.raises(CascadeNotRun):
            graph.session.commit()
        graph.proc.run_cascade(wm)                       # the remedy, at the root
        graph.session.commit()
        assert not graph.check('user:alice', 'viewer', 'doc:d1')
    finally:
        graph.session.close()


def test_w7b_sibling_savepoints_write_released_cascade_rolled_back():
    """Reviewer probe P4 (rev_tk3_p1.py): write in savepoint A (released), cascade in
    savepoint B (rolled back), commit -> must refuse."""
    graph = G(paranoia='off')
    try:
        graph.committed_write('user:alice', 'viewer', 'doc:d1')
        wm = graph.wm()
        a = graph.session.begin_nested()
        graph.write('user:alice', 'banned', 'doc:d1')
        a.commit()
        b = graph.session.begin_nested()
        graph.proc.run_cascade(wm)
        b.rollback()
        with pytest.raises(CascadeNotRun):
            graph.session.commit()
    finally:
        graph.session.close()


def test_w7c_an_ancestor_savepoint_rollback_re_arms_an_inner_payment():
    """Write at the root; cascade in an INNER savepoint that is released into an outer
    one; the OUTER rolls back -> the payment is undone with it."""
    graph, wm = _stale_ban_setup('off')
    try:
        outer = graph.session.begin_nested()
        inner = graph.session.begin_nested()
        graph.proc.run_cascade(wm)
        inner.commit()
        assert owed_stores(graph.session) == []
        outer.rollback()
        assert owed_stores(graph.session) == ['g']
        with pytest.raises(CascadeNotRun):
            graph.session.commit()
    finally:
        graph.session.close()


def test_n13_a_cascade_in_a_released_savepoint_pays():
    """Control for W7: a released savepoint's cascade survives, so the commit goes
    through and the answer is the cascaded one. paranoia='off' on purpose: under the
    'full' guard on in-memory SQLite, releasing a savepoint fires
    ParanoiaGuard.after_commit, whose fresh Session shares the SingletonThreadPool
    connection and LOSES the cascade's writes (viewer True after the release; with
    after_commit patched to a no-op, False). PROBED 2026-10-22
    (.scratch/tk158-tk3/fix-probes/n13_cause.py), independent of the mark, and the
    likely cause of N4d's 'no such savepoint'; filed for its own row."""
    graph, wm = _stale_ban_setup('off')
    try:
        sp = graph.session.begin_nested()
        graph.proc.run_cascade(wm)
        sp.commit()
        assert owed_stores(graph.session) == []
        graph.session.commit()
        assert not graph.check('user:alice', 'viewer', 'doc:d1')
    finally:
        graph.session.close()


def test_n13b_write_and_cascade_in_one_rolled_back_savepoint_owe_nothing(g):
    """Control for W7: when the write is undone with the cascade, nothing is re-armed."""
    wm = g.wm()
    sp = g.session.begin_nested()
    g.write('user:alice', 'viewer', 'doc:d1')
    g.proc.run_cascade(wm)
    sp.rollback()
    assert owed_stores(g.session) == []
    g.session.commit()
    assert not g.check('user:alice', 'viewer', 'doc:d1')


def test_w8_a_leaf_write_with_the_processor_flag_on_still_owes():
    """Hole 2 (reviewer probes P2 / rev_tk3_p9.py): an open processor_writes window
    exempts only the processor's DERIVED-family output, never a leaf write. Pre-fix:
    'COMMITTED without cascade; viewer = False (expected True)'."""
    graph, _wm = _stale_ban_setup('off')
    try:
        graph.session.rollback()
        graph.widx.processor_writes = True
        try:
            graph.write('user:alice', 'banned', 'doc:d1')     # routed onto a LEAF
        finally:
            graph.widx.processor_writes = False
        assert owed_stores(graph.session) == ['g']
        with pytest.raises(CascadeNotRun):
            graph.session.commit()
    finally:
        graph.session.close()


def test_n14_a_processor_flagged_derived_write_owes_nothing(g):
    """Control for W8: the processor's own output (flag on + derived-public family)
    stays exempt -- otherwise every reconcile outside run_cascade would owe."""
    g.widx.processor_writes = True
    try:
        g.widx.add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    finally:
        g.widx.processor_writes = False
    assert owed_stores(g.session) == []


# --------------------------------------------------------------------------- the waiver

def test_waiver_covers_the_writes_inside_it_only(g):
    with _cascade_check_waived(g.widx, reason='TK3 self-test: stale on purpose'):
        g.write('user:alice', 'viewer', 'doc:d1')
    assert owed_stores(g.session) == []
    g.session.commit()
    g.write('user:bob', 'viewer', 'doc:d1')            # after the block: owes as usual
    with pytest.raises(CascadeNotRun):
        g.session.commit()


@pytest.mark.parametrize('reason', ['', '   ', None])
def test_waiver_needs_a_reason(g, reason):
    with pytest.raises(ValueError, match='reason'):
        with _cascade_check_waived(g.widx, reason=reason):
            pass


# Every file allowed to commit deliberately uncascaded state. A new entry is a reviewed
# diff: prefer adding the missing run_cascade, then a rollback, and waive only where the
# test exists to observe stale state (plan doc sec 5).
_WAIVER_SITES = {
    'tests/test_reg_tk91_live_keys_repair.py',   # builds a grant that outlived its leaf
    'tests/test_tk3_cascade_mark.py',            # this file: the waiver's own pins
}


#: The module that DEFINES the waiver; it is the one src/ file allowed to name it.
_WAIVER_HOME = 'src/zanzibar/graphindex/cascade_mark.py'


def _waiver_sites() -> set[str]:
    """Every .py file under src/, tests/, formal/, benchmarks/ and scripts/ that NAMES
    the waiver at all (a call, an import, an alias binding), not only one that spells
    the call -- so ``from ... import _cascade_check_waived as w`` is counted too (FIX
    stage 2026-10-22: the first census scanned tests/ + formal/conformance/ for the
    literal call text only)."""
    found = set()
    for top in ('src', 'tests', 'formal', 'benchmarks', 'scripts'):
        for p in (ROOT / top).rglob('*.py'):
            if re.search(r'\b_cascade_check_waived\b', p.read_text(encoding='utf-8')):
                found.add(p.relative_to(ROOT).as_posix())
    found.discard(_WAIVER_HOME)
    return found


def test_waiver_sites_are_the_census():
    assert _waiver_sites() == _WAIVER_SITES
