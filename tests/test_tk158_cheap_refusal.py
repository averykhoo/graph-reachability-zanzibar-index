"""TK158: a ``ClosureFanoutExceeded`` refusal is cheap -- and still atomic.

Before TK158 a refused grant through a 1M-member group cost 78.89 s and 3,827 MB on
SQLite (2026-10-22; ``docs/tk158-cheap-fanout-refusal-2026-10-22.md`` sec 1d), for two
reasons this module pins away:

  * D1 -- ``ReachabilityIndex._add_direct_edge_unsafe_impl`` loaded the whole closure
    region (A = ancestors of the subject, D = descendants of the object) as ORM ``Edge``
    rows BEFORE counting it. It now takes two indexed ``count(*)`` queries
    (``_closure_region_counts``) and refuses before loading anything. The counts must be
    EXACTLY the old loaded lengths (tests 4a/4b), and an admitted write asserts that at
    runtime.
  * D2 -- ``Store._write``'s error arm rebuilt the whole set engine
    (``refresh_evaluator``, O(store)) to drop the one tuple admission had put in memory.
    An ``IndexResourceLimit`` now undoes exactly that tuple
    (``TupleSource.undo_last_admission``, through ``SetEngine.apply_logged``) and
    restores the watermark; the rebuild stays the fallback if the undo fails.

What must NOT change: the refusal is atomic across the log, the set engine and the index
(CLAUDE.md, the fan-out knob). Test 1 compares the live evaluator against a FRESH engine
rebuilt from the database -- membership, interner refcounts, population masks, the
flow graph -- and the index/log/outbox rows against a snapshot, for the three TK112
witnesses (``unban`` is a REMOVE, so it exercises the inverse ADD) plus a plain union
schema whose flow graph is non-trivial.

Every test runs on file-backed SQLite and, with ``ZANZIBAR_TEST_DSN`` set, on PostgreSQL
(``tests/dbengine.py::shared_engine``).

Sabotage (``docs/sabotage-procedure.md``), 2026-10-22: each mutant applied to the
implemented code (anchor asserted to match exactly once, file restored byte-for-byte and
its sha256 re-checked after), the named tests run on the mutated tree; literal output:

  M1 ``undo_last_admission``: the inverse ``apply_logged`` + watermark restore replaced
     by ``return`` -> test 1 RED, ``4 failed``, e.g. (ban) ``AssertionError: evaluator
     diverged from a fresh rebuild in: ['flow adjacency', 'flow edge counts', 'interner
     refcounts', 'member_of', 'membership', 'node_sets keys', 'shape masks']``.
  M2 undo restores the tuple but NOT the watermark -> ``5 failed``: test 1 on all four
     cases (``AssertionError: evaluator_watermark 32 != log head 31`` on ban; 62/61,
     33/32, 37/36 on the others) and test 6 (``assert 37 == 36``).
  M3 undo applies the SAME op instead of the inverse -> ``8 failed``: test 1
     (``AssertionError: the undo fell back to a rebuild 1 time(s)`` -- apply_logged's
     presence guard raised ``RuntimeError: log ADD of an already-present tuple ...`` and
     the fallback rebuilt, so test 1 COUNTS rebuilds or this mutant passes) and test 2
     (``_RebuildCalled: rebuild on the refusal path``).
  M4 ``except IndexResourceLimit`` in ``Store._write`` made unreachable (back to the
     rebuild) -> test 2 RED, ``4 failed``: ``_RebuildCalled: rebuild on the refusal
     path``.
  M5 D1's count-first block disabled (``if False:``; back to load-then-count) -> test 3
     RED, ``1 failed``: ``AssertionError: the refused write loaded 1000 Edge rows
     (expected 0)``.
  M6 the A count drops its ``store_id`` filter -> test 4b RED, ``1 failed``:
     ``AssertionError: (2, 1) != (1, 1) for (2, 1)``.
  M7 the A count filters ``subject_id`` instead of ``object_id`` -> test 4a RED,
     ``1 failed``: ``AssertionError: (5, 4) != (0, 4) for pair (1, 2)``.
  M8 the over-cap cycle point lookup disabled -> test 7 RED, ``1 failed``:
     ``ClosureFanoutExceeded: closure fan-out cap exceeded: this write would add 23
     permission-closure rows (11 ancestors x 1 descendants + fringes), over the limit
     of 1`` escaped where the cycle ``InvariantViolation`` was expected.

FIX-stage sabotage, 2026-10-22 (same procedure, runner
``.scratch/tk158-tk3/tk158fix_sabotage.py``), for tests 8-10 and the MultiSet
``_old_lengths``:

  F1 the count==load mismatch guard disabled (``if False and ...``) -> test 8 RED,
     ``1 failed``: ``Failed: DID NOT RAISE InvariantViolation``.
  F2 the count block taken on the suspended path again (HEAD-of-build guard) -> test 9
     RED, ``1 failed``: ``AssertionError: _closure_region_counts ran on the suspended
     path``.
  F3 ``except IndexResourceLimit`` in ``Store._write`` made unreachable -> test 10 RED,
     ``2 failed``: ``AssertionError: the undo fell back to a rebuild 1 time(s)``.
  F4 ``_old_lengths`` back to a set of row keys -> test 8 RED, ``1 failed``:
     ``assert (2, 0) == (1, 0)``.

Instrument control: each test was run green on the unmutated tree first, and each
mutant's anchor was asserted to match exactly once before applying it.
"""

import pytest
from sqlalchemy import event
from sqlmodel import Session, func, select

from tests import oracle as O
from tests.dbengine import shared_engine
from zanzibar.graphindex import ReachabilityIndex, IndexStore
from zanzibar.graphindex.invariants import InvariantViolation
from zanzibar.graphindex.models import DeltaOutbox, Edge, Node
from zanzibar.graphindex.multiset import MultiSet
import zanzibar.graphindex.core as core
from zanzibar.schema import ClosureFanoutExceeded, PathCountExceeded
from zanzibar.setengine.engine import SetEngine
from zanzibar.store import Store, TupleSource
from zanzibar.store.models import TupleLog
from zanzibar.store.schema_io import open_set_engine

# --------------------------------------------------------------------------- #
# Witnesses: the three TK112 ones (tests/test_tk112_cap_policy.py) + a union grant
# --------------------------------------------------------------------------- #

BOOL_SCHEMA = '''
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

UNION_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define owner: [user]
    define viewer: [user, group#member] or owner
type folder
  relations
    define reader: [doc#viewer]
'''

CAP = 20
N = 30


def _ban_case():
    setup = [('+', ('...', 'user', f'u{i}', 'member', 'group', 'big')) for i in range(N)]
    setup.append(('+', ('...', 'user', 'u0', 'grant', 'doc', 'd')))
    return BOOL_SCHEMA, setup, ('+', ('member', 'group', 'big', 'banned', 'doc', 'd'))


def _join_case():
    setup = [('+', ('...', 'user', f'u{i}', 'member', 'group', 'big')) for i in range(N)]
    setup += [('+', ('member', 'group', 'big', 'banned', 'doc', f'd{j}')) for j in range(N)]
    setup.append(('+', ('...', 'user', 'victim', 'grant', 'doc', 'd0')))
    return BOOL_SCHEMA, setup, ('+', ('...', 'user', 'victim', 'member', 'group', 'big'))


def _unban_case():
    setup = [('+', ('viewer', 'doc', 'd', 'reader', 'folder', f'f{j}')) for j in range(N)]
    setup += [('+', ('...', 'user', 'u0', 'grant', 'doc', 'd')),
              ('+', ('...', 'user', 'u0', 'banned', 'doc', 'd'))]
    return BOOL_SCHEMA, setup, ('-', ('...', 'user', 'u0', 'banned', 'doc', 'd'))


def _union_case():
    # A plain (non-boolean) userset grant: the set engine's flow graph is non-empty
    # here, so the undo must also leave it equal to a fresh build. The nested group
    # and the owner arm give the interner's reverse-dependency refcounts work to do.
    setup = [('+', ('...', 'user', f'u{i}', 'member', 'group', 'big')) for i in range(N)]
    setup.append(('+', ('member', 'group', 'sub', 'member', 'group', 'big')))
    setup.append(('+', ('...', 'user', 'w', 'member', 'group', 'sub')))
    setup.append(('+', ('...', 'user', 'o', 'owner', 'doc', 'd')))
    setup += [('+', ('viewer', 'doc', 'd', 'reader', 'folder', f'f{j}')) for j in range(3)]
    return UNION_SCHEMA, setup, ('+', ('member', 'group', 'big', 'viewer', 'doc', 'd'))


CASES = {'ban': _ban_case, 'join-banned-group': _join_case, 'unban': _unban_case,
         'union-grant': _union_case}

SUBJECTS = [f'u{i}' for i in range(3)] + ['victim', 'w', 'o', 'fresh', 'nobody']
OBJECTS = {'group': ['big', 'sub'], 'doc': ['d', 'd0', 'd1'],
           'folder': ['f0', 'f1']}
RELATIONS = {'group': ['member'], 'doc': ['grant', 'banned', 'viewer', 'owner'],
             'folder': ['reader']}


def _grid(schema):
    for o_type, names in OBJECTS.items():
        for rel in RELATIONS[o_type]:
            if f'define {rel}:' not in schema.split(f'type {o_type}')[1].split('type ')[0]:
                continue
            for on in names:
                for sn in SUBJECTS:
                    yield ('...', 'user', sn, rel, o_type, on)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _do(cs, op, t):
    return cs.add_tuple(*t) if op == '+' else cs.remove_tuple(*t)


def _fingerprint(se: SetEngine) -> dict:
    """Canonical, id-independent snapshot of a set engine's whole in-memory state.

    Ids are recycled handles (an undo frees ids a fresh rebuild never allocated), so
    everything is keyed by the ``(type, name, predicate)`` surrogate."""
    se._ensure_flow_graph()
    k = se.interner.key
    members = set()
    for oid, ns in se.node_sets.items():
        for sid in ns.entities:
            members.add((k(sid), k(oid), 'entity'))
        for sid in ns.usersets:
            members.add((k(sid), k(oid), 'userset'))
    return {
        'membership': frozenset(members),
        'node_sets keys': frozenset(k(o) for o in se.node_sets),
        'member_of': frozenset((k(s), k(o)) for s, os in se.member_of.items() for o in os),
        'interner refcounts': {key: se.interner.refcount[i]
                               for key, i in se.interner.id_of.items()},
        'type masks': {t: frozenset(k(i) for i in m)
                       for t, m in se.interner.ids_of_type.items() if len(m)},
        'shape masks': {s: frozenset(k(i) for i in m)
                        for s, m in se.interner.ids_of_shape.items() if len(m)},
        'flow edge counts': dict(se._edge_count),
        'flow adjacency': {u: frozenset(v) for u, v in se._flow_adj.items() if v},
        'flow node refs': dict(se._flow_node_refs),
        'flow shape nodes': {s: frozenset(v) for s, v in se._shape_nodes.items() if v},
    }


def _assert_equals_fresh_rebuild(cs: Store, label: str = 'evaluator'):
    live = _fingerprint(cs.source.engine)
    fresh = _fingerprint(open_set_engine(cs.session, 's'))
    diff = sorted(name for name in live if live[name] != fresh[name])
    assert not diff, f'{label} diverged from a fresh rebuild in: {diff}'


def _db_rows(session):
    edges = frozenset(session.exec(select(Edge.subject_id, Edge.object_id,
                                          Edge.direct_edge_count,
                                          Edge.indirect_edge_count,
                                          Edge.derived)
                                   .where(Edge.store_id == 's')).all())
    outbox = session.exec(select(func.count()).select_from(DeltaOutbox)).one()
    log = frozenset(session.exec(select(TupleLog.id, TupleLog.op, TupleLog.subject_name,
                                        TupleLog.relation, TupleLog.object_name)).all())
    nodes = session.exec(select(func.count()).select_from(Node)).one()
    return edges, outbox, log, nodes


def _built_store(tmp_path, case, name='tk158.db'):
    schema, setup, op = CASES[case]()
    engine = shared_engine(tmp_path, name)
    session = Session(engine)
    cs = Store(session, 's', schema=schema, sync=True)
    cs.widx.idx.max_closure_fanout = 0          # build the region freely
    for o, w in setup:
        _do(cs, o, w)
    cs.widx.idx.max_closure_fanout = CAP
    return engine, session, cs, schema, setup, op


class _Counter:
    def __init__(self):
        self.n = 0


@pytest.fixture
def rebuilds(monkeypatch):
    """Count every ``SetEngine.rebuild`` (the O(store) replay)."""
    c = _Counter()
    real = SetEngine.rebuild

    def counting(self):
        c.n += 1
        return real(self)
    monkeypatch.setattr(SetEngine, 'rebuild', counting)
    return c


# --------------------------------------------------------------------------- #
# 1. After a refusal the evaluator equals a fresh rebuild; log/index unchanged
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('case', sorted(CASES))
def test_refusal_leaves_evaluator_equal_to_a_fresh_rebuild(tmp_path, case, rebuilds):
    engine, session, cs, schema, setup, (op, t) = _built_store(tmp_path, case)
    try:
        cs.source.engine._ensure_flow_graph()   # warm, as on a store that has written
        head = cs.watermark()
        rows_before = _db_rows(session)
        oracle = O.Oracle(schema, sorted(
            {O.t(*w) for o, w in setup if o == '+'} - {O.t(*w) for o, w in setup if o == '-'}))
        rebuilds.n = 0

        with pytest.raises(ClosureFanoutExceeded):
            _do(cs, op, t)

        assert rebuilds.n == 0, f'the undo fell back to a rebuild {rebuilds.n} time(s)'
        _assert_equals_fresh_rebuild(cs)
        assert cs.source.evaluator_watermark == cs.watermark() == head, (
            f'evaluator_watermark {cs.source.evaluator_watermark} != log head {head}')
        assert _db_rows(session) == rows_before    # log, Edge rows, outbox, nodes
        for q in _grid(schema):
            want = oracle.check(*q)
            assert cs.source.check(*q) is want, q
            assert cs.widx.check(*q) is want, q
        # the store is still writable, and still agrees after it
        _do(cs, '+', ('...', 'user', 'fresh', 'member', 'group', 'other'))
        assert cs.check('...', 'user', 'fresh', 'member', 'group', 'other') is True
        _assert_equals_fresh_rebuild(cs, 'evaluator after a later write')
    finally:
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# 2. The refusal never rebuilds the evaluator
# --------------------------------------------------------------------------- #

class _RebuildCalled(Exception):
    pass


@pytest.mark.parametrize('case', sorted(CASES))
def test_refusal_does_not_rebuild(tmp_path, case, monkeypatch):
    engine, session, cs, schema, setup, (op, t) = _built_store(tmp_path, case)
    try:
        def boom(*a, **k):
            raise _RebuildCalled('rebuild on the refusal path')
        monkeypatch.setattr(SetEngine, 'rebuild', boom)
        monkeypatch.setattr(TupleSource, 'refresh_evaluator', boom)
        with pytest.raises(ClosureFanoutExceeded):
            _do(cs, op, t)
    finally:
        monkeypatch.undo()
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# 3. The refusal does not load the closure region
# --------------------------------------------------------------------------- #

def test_refusal_loads_no_region_rows(tmp_path):
    engine = shared_engine(tmp_path, 'noload.db')
    session = Session(engine)
    try:
        cs = Store(session, 's', schema=UNION_SCHEMA, sync=True)
        cs.widx.idx.max_closure_fanout = 0
        for i in range(1000):
            cs.add_tuple('...', 'user', f'u{i}', 'member', 'group', 'big')
        cs.widx.idx.max_closure_fanout = 10
        loaded = _Counter()

        def on_load(target, *_):
            loaded.n += 1
        event.listen(Edge, 'load', on_load)
        event.listen(Edge, 'refresh', on_load)
        try:
            with pytest.raises(ClosureFanoutExceeded):
                cs.add_tuple('member', 'group', 'big', 'viewer', 'doc', 'd')
        finally:
            event.remove(Edge, 'load', on_load)
            event.remove(Edge, 'refresh', on_load)
        # Observed 2026-10-22: 0 -- the reverse-edge pre-check in `_add_edge_locked`
        # and the over-cap cycle point lookup both find no row.
        assert loaded.n == 0, f'the refused write loaded {loaded.n} Edge rows (expected 0)'
    finally:
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# 4. The counts equal what the old code loaded
# --------------------------------------------------------------------------- #

def _old_lengths(idx, s, o):
    """The pre-TK158 accounting, verbatim: load A and D as rows into ``MultiSet``s keyed
    by node id with value ``indirect_edge_count`` (as ``_add_direct_edge_unsafe_impl``
    does), take len(). A MultiSet DROPS a zero-valued key, so this differs from
    ``count(*)`` exactly on a zero-count (I1-violating) row -- test 8 pins that case;
    a set of row keys would equal ``count(*)`` by the unique constraint and could not
    see it (TK158 FIX, 2026-10-22)."""
    a, d = MultiSet(), MultiSet()
    for e in idx.session.exec(select(Edge).where(Edge.store_id == idx.store_id)
                              .where(Edge.object_id == s)).all():
        a[e.subject_id] = e.indirect_edge_count
    for e in idx.session.exec(select(Edge).where(Edge.store_id == idx.store_id)
                              .where(Edge.subject_id == o)).all():
        d[e.object_id] = e.indirect_edge_count
    return len(a), len(d)


def _bare_index(tmp_path, name):
    engine = shared_engine(tmp_path, name)
    session = Session(engine)
    for sid in ('s', 'other'):
        session.add(IndexStore(id=sid))
    session.commit()
    return engine, session, ReachabilityIndex(session, store_id='s', max_closure_fanout=0)


def test_region_counts_equal_old_loaded_lengths_over_shapes(tmp_path):
    engine, session, idx = _bare_index(tmp_path, 'counts.db')
    try:
        # userset, object, product, a diamond (path counts > 1) and a chain
        for i in range(4):
            idx.add_edge('...', 'user', f'u{i}', 'member', 'group', 'g')
        idx.add_edge('member', 'group', 'g', 'viewer', 'doc', 'd')
        for j in range(3):
            idx.add_edge('viewer', 'doc', 'd', 'reader', 'folder', f'f{j}')
        idx.add_edge('...', 'user', 'x', 'member', 'group', 'h1')
        idx.add_edge('...', 'user', 'x', 'member', 'group', 'h2')
        idx.add_edge('member', 'group', 'h1', 'member', 'group', 'top')
        idx.add_edge('member', 'group', 'h2', 'member', 'group', 'top')
        idx.add_edge('member', 'group', 'top', 'viewer', 'doc', 'e')
        session.flush()
        ids = sorted(n.id for n in session.exec(select(Node).where(Node.store_id == 's')))
        assert len(ids) == 14           # 4 u + g + d + 3 f + x + h1 + h2 + top + e
        checked = 0
        for s in ids:
            for o in ids:
                if s == o:
                    continue
                got = idx._closure_region_counts(s, o)
                want = _old_lengths(idx, s, o)
                assert got == want, f'{got} != {want} for pair {(s, o)}'
                checked += 1
        assert checked == len(ids) * (len(ids) - 1)
        # and the runtime assertion is live on every admitted capped write
        idx.max_closure_fanout = 10_000
        idx.add_edge('member', 'group', 'top', 'viewer', 'doc', 'd')
        session.commit()
    finally:
        session.close()
        engine.dispose()


def test_region_counts_are_scoped_to_the_store(tmp_path):
    engine, session, idx = _bare_index(tmp_path, 'scoped.db')
    try:
        idx.add_edge('...', 'user', 'a', 'member', 'group', 'g')
        session.flush()
        g = session.exec(select(Node).where(Node.name == 'g')).one().id
        a = session.exec(select(Node).where(Node.name == 'a')).one().id
        # a foreign store's row that happens to name the same node ids
        session.add(Edge(store_id='other', subject_id=a, object_id=g,
                         direct_edge_count=1, indirect_edge_count=1))
        session.flush()
        for s, o in ((g, a), (a, g)):
            got = idx._closure_region_counts(s, o)
            want = _old_lengths(idx, s, o)
            assert got == want, f'{got} != {want} for {(s, o)}'
    finally:
        session.rollback()
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# 5. Fallback: an undo that fails rebuilds, and the evaluator is still truthful
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('case', ['ban', 'unban', 'union-grant'])
def test_failed_undo_falls_back_to_rebuild(tmp_path, case, rebuilds):
    engine, session, cs, schema, setup, (op, t) = _built_store(tmp_path, case)
    try:
        def broken_apply_logged(*a, **k):
            raise RuntimeError('sabotaged undo')
        cs.source.engine.apply_logged = broken_apply_logged
        rebuilds.n = 0
        with pytest.raises(ClosureFanoutExceeded):
            _do(cs, op, t)
        del cs.source.engine.apply_logged
        assert rebuilds.n >= 1, 'the fallback rebuild did not run'
        assert cs.source.evaluator_watermark == cs.watermark()
        _assert_equals_fresh_rebuild(cs)
    finally:
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# 6. The restored watermark is truthful under a second instance
# --------------------------------------------------------------------------- #

def test_restored_watermark_tails_another_instances_commit(tmp_path):
    schema, setup, (op, t) = _union_case()
    engine = shared_engine(tmp_path, 'two.db')
    sa, sb = Session(engine), Session(engine)
    try:
        a = Store(sa, 's', schema=schema, sync=True)
        a.widx.idx.max_closure_fanout = 0
        for o, w in setup:
            _do(a, o, w)
        a.widx.idx.max_closure_fanout = CAP
        head = a.watermark()

        with pytest.raises(ClosureFanoutExceeded):
            _do(a, op, t)
        assert a.source.evaluator_watermark == head
        sa.rollback()

        b = Store(sb, 's', sync=True)
        tok = b.add_tuple('...', 'user', 'late', 'member', 'group', 'sub')
        assert tok > head

        sa.rollback()                      # fresh snapshot for A
        a.source.catch_up_evaluator()      # no RuntimeError, no WatermarkGap
        assert a.source.evaluator_watermark == tok
        assert a.source.check('...', 'user', 'late', 'member', 'group', 'big') is True
        _assert_equals_fresh_rebuild(a, "A's evaluator")
        # and A can write on top
        a.add_tuple('...', 'user', 'later', 'member', 'group', 'sub')
        _assert_equals_fresh_rebuild(a, "A's evaluator after its own write")
    finally:
        sa.close()
        sb.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# 7. Error precedence: a cycle is still reported before the cap
# --------------------------------------------------------------------------- #

def test_over_cap_cycle_is_reported_as_a_cycle(tmp_path):
    """``_add_edge_locked`` pre-checks the reverse edge, so the in-impl cycle guard is
    reached only by callers that skip it (the wildcard bridge writer). Drive the impl
    directly: an over-cap addition that would close a cycle must raise the cycle
    ``InvariantViolation``, as the old load-then-check code did, not the cap refusal."""
    engine, session, idx = _bare_index(tmp_path, 'cycle.db')
    try:
        for i in range(10):
            idx.add_edge('...', 'user', f'u{i}', 'member', 'group', 'g')
        idx.add_edge('member', 'group', 'g', 'member', 'group', 'h')
        session.flush()
        g = session.exec(select(Node).where(Node.name == 'g')).one().id
        h = session.exec(select(Node).where(Node.name == 'h')).one().id
        idx.max_closure_fanout = 1
        with pytest.raises(InvariantViolation, match='Cycle detected'):
            idx._add_direct_edge_unsafe(h, g, 1)   # h -> g closes g -> h -> g
    finally:
        session.rollback()
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# 8. The runtime count==load guard fires on a zero-count (I1-violating) row
# --------------------------------------------------------------------------- #

def test_count_load_mismatch_guard_fires_on_a_zero_count_row(tmp_path):
    """``count(*)`` counts a zero-count ``Edge`` row the loaded ``MultiSet`` drops, so
    on an (already corrupt, I1-violating) store the two disagree. An ADMITTED capped add
    must then refuse with the mismatch ``InvariantViolation`` instead of expanding on a
    region its admission arithmetic did not see. Also the instrument control for
    ``_old_lengths``: it must SEE the difference (a set of row keys would not)."""
    engine, session, idx = _bare_index(tmp_path, 'zero.db')
    try:
        idx.add_edge('...', 'user', 'a', 'member', 'group', 'g')
        idx.add_edge('...', 'user', 'b', 'member', 'group', 'other')
        session.flush()
        g = session.exec(select(Node).where(Node.name == 'g')).one().id
        b = session.exec(select(Node).where(Node.name == 'b')).one().id
        session.add(Edge(store_id='s', subject_id=b, object_id=g,
                         direct_edge_count=0, indirect_edge_count=0))
        session.flush()
        assert idx._closure_region_counts(g, -1) == (2, 0)
        assert _old_lengths(idx, g, -1) == (1, 0)
        idx.max_closure_fanout = 10_000
        with pytest.raises(InvariantViolation, match='closure region count mismatch'):
            idx.add_edge('member', 'group', 'g', 'viewer', 'doc', 'd')
    finally:
        session.rollback()
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# 9. With the cap suspended (replay) the count queries are not taken
# --------------------------------------------------------------------------- #

def test_suspended_cap_takes_no_region_count(tmp_path, monkeypatch):
    """Inside ``fanout_cap_suspended`` the cap can only warn, from the loaded lengths,
    so ``_closure_region_counts`` must not run (it cost 9.4% of a 1700-row
    ``catch_up``). The over-cap add is admitted, as before."""
    engine, session, idx = _bare_index(tmp_path, 'susp.db')
    try:
        for i in range(5):
            idx.add_edge('...', 'user', f'u{i}', 'member', 'group', 'g')
        idx.max_closure_fanout = 1

        def boom(*a, **k):
            raise AssertionError('_closure_region_counts ran on the suspended path')
        monkeypatch.setattr(ReachabilityIndex, '_closure_region_counts', boom)
        with idx.fanout_cap_suspended():
            idx.add_edge('member', 'group', 'g', 'viewer', 'doc', 'd')
        monkeypatch.undo()
        assert idx.check_reachable('...', 'user', 'u3', 'viewer', 'doc', 'd')
        # and outside the suspension the count still decides the refusal
        with pytest.raises(ClosureFanoutExceeded):
            idx.add_edge('member', 'group', 'g', 'viewer', 'doc', 'e')
    finally:
        session.rollback()
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# 10. The undo also serves the OTHER IndexResourceLimit: PathCountExceeded
# --------------------------------------------------------------------------- #

PATH_CASES = {
    'union-diamond': (UNION_SCHEMA,
                      [('...', 'user', 'x', 'member', 'group', 'h1'),
                       ('...', 'user', 'x', 'member', 'group', 'h2'),
                       ('member', 'group', 'h1', 'member', 'group', 'top')],
                      ('member', 'group', 'h2', 'member', 'group', 'top')),
    'bool-diamond-grant': (BOOL_SCHEMA,
                           [('...', 'user', 'x', 'member', 'group', 'g'),
                            ('...', 'user', 'x', 'grant', 'doc', 'd')],
                           ('member', 'group', 'g', 'grant', 'doc', 'd')),
}


@pytest.mark.parametrize('case', sorted(PATH_CASES))
def test_path_count_refusal_is_undone_without_rebuild(tmp_path, case, rebuilds,
                                                      monkeypatch):
    """``PathCountExceeded`` (TK111) is raised from the batch writer, AFTER the loads,
    and reaches ``Store._write``'s ``IndexResourceLimit`` arm like the fan-out refusal.
    ``MAX_PATH_COUNT`` is lowered to 1 so a diamond (two paths) refuses."""
    schema, setup, t = PATH_CASES[case]
    engine = shared_engine(tmp_path, 'pc.db')
    session = Session(engine)
    try:
        cs = Store(session, 's', schema=schema, sync=True)
        for w in setup:
            cs.add_tuple(*w)
        cs.source.engine._ensure_flow_graph()
        head = cs.watermark()
        rows_before = _db_rows(session)
        rebuilds.n = 0
        real_max = core.MAX_PATH_COUNT
        monkeypatch.setattr(core, 'MAX_PATH_COUNT', 1)
        with pytest.raises(PathCountExceeded):
            cs.add_tuple(*t)
        monkeypatch.setattr(core, 'MAX_PATH_COUNT', real_max)
        assert rebuilds.n == 0, f'the undo fell back to a rebuild {rebuilds.n} time(s)'
        _assert_equals_fresh_rebuild(cs)
        assert cs.source.evaluator_watermark == cs.watermark() == head
        assert _db_rows(session) == rows_before
        cs.add_tuple('...', 'user', 'later', 'member', 'group', 'zz')
        _assert_equals_fresh_rebuild(cs, 'evaluator after a later write')
    finally:
        session.close()
        engine.dispose()
