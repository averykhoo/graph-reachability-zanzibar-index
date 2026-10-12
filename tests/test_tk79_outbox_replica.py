"""TK79: a ``drain_deltas`` replica must see the late reconcile-time-GC outbox rows.

``DeltaProcessor._run_cascade``'s quiescence block justifies NOT suppressing the outbox
rows that a reconcile-time GC emits after the round's frontier snapshot (the TK73 shape):
"they are honest, balanced retractions (an external ``drain_deltas`` replica must see
them)". That sentence is why TK73 asks a semantic question instead of dropping the rows.
Until this module, nothing asserted it in either direction: nothing showed that a
replica needs the rows, and nothing showed that a replica fed them ends up right.
Measurements and reasoning: ``docs/tk79-outbox-replica-2026-10-12.md``.

THE REPLICA. ``core.py::ReachabilityIndex._emit`` fires ADDED when an ``Edge`` row is
created and REMOVED when one is deleted, so the drained stream is an exact changelog of
the ``(subject_id, object_id)`` pair set. ``drain_deltas`` renders node IDS only, so the
replica here is an id-keyed set. It applies the stream strictly: an ADDED for a present
pair, or a REMOVED for an absent one, is an unbalanced stream and fails.

THE FOUR TESTS.
  * ``test_drained_replica_matches_primary_closure``: on the TK73 witness, for every
    star target, the replica equals the primary's ``Edge`` pair set after every commit.
    Vacuity guards require that a GC window really emitted rows and a settle pass ran.
  * ``test_strip_arm_rows_reach_the_replica``: the same property at the strip arm of
    ``_sync_entity_middles`` called from ``_gc_public_node`` (TK75, I14 fixture).
  * ``test_subject_gc_strip_arm_rows_reach_the_replica``: the same property at the
    THIRD site, the strip arm called at the end of ``_gc_subject_node``. On the TK73 and
    I14 fixtures that call never emits (the 2026-10-12c review measured it), so this test
    brings its own fixture, ``SUBJECT_GC_SCHEMA``, in which a recorded residue subject has
    a crossable type. On that fixture no settle pass runs (``proc._settle is None``,
    measured 2026-10-12c), so the test pins what a replica gets from the site, not that
    the rows arrive after a frontier snapshot.
  * ``test_late_gc_rows_are_load_bearing``: the permanent sabotage, the "must" half. A
    replica that skips the rows emitted inside a reconcile-time GC keeps the GC'd node's
    pairs. Once SQLite reuses that node id for ``user:u9``, the stale pair reads as the
    type-legal claim "user:u9 viewer folder:x", which the primary's ``check`` and the
    independent oracle both deny (and a control query of the same shape, for u8, both
    affirm). Reading the id as user:u9 resolves it against the primary's ``Node`` table,
    because ``drain_deltas`` carries ids only. That step is REASONED, not observed in a
    real consumer.

THE ORACLE LEG. The replica is a changelog of ``Edge`` pairs; residue rows are not in the
stream, so a replica can never answer derived membership alone. "Replica == oracle"
therefore holds TRANSITIVELY: replica == primary pair set (here) and primary == oracle
(``tests/test_cascade_quiesce_gc.py::test_the_witness_generalises_on_its_star_target`` for
the TK73 family, and a grid check after every write inside
``test_subject_gc_strip_arm_rows_reach_the_replica`` for its own fixture).

SABOTAGE RECORD (literal output, 2026-10-12c). The narrowest plausible weakening is the
fix TK73 rejected: suppress the late rows. In
``src/zanzibar/graphindex/processor.py::DeltaProcessor._gc_subject_node``, the outbox
watermark was captured before ``self.widx._maybe_remove_bridges(n)`` and every outbox row
above it was deleted after the call (S1). Command:
``pytest tests/test_tk79_outbox_replica.py -q -rf -p no:randomly``:

    S1  5 failed, 3 passed
        test_drained_replica_matches_primary_closure[x]  (and [z], [w], [q]):
          AssertionError: after remove ('...', 'folder', 'x', 'parent', 'folder', 'y'):
          replica-only [(9, 3), (9, 4), (9, 5)], primary-only []
        test_late_gc_rows_are_load_bearing:
          AssertionError: no settle pass ran -- not the TK73 shape
    S2  (the same suppression around ``self.widx._sync_entity_middles(*entity)`` at BOTH
        call sites, ``_gc_subject_node`` and ``_gc_public_node``)
        2 failed, 6 passed: the two strip-arm tests
    S2pub  (``_gc_public_node`` site only; this run adds test_i14_crossing_middles and
        test_cascade_quiesce_gc)
        1 failed, 24 passed
        test_strip_arm_rows_reach_the_replica:
          AssertionError: after remove ('...', 'user', 'u1', 'editor', 'folder', 'f1')
          assert {(3, 4), (5, 3), (5, 4)} == set()
    S2sub  (``_gc_subject_node`` site only; same three files)
        1 failed, 24 passed
        test_subject_gc_strip_arm_rows_reach_the_replica:
          AssertionError: after remove
          assert {(3, 4), (5, 3), (5, 4)} == set()
        Before this test existed, the review measured S2sub at 7 passed, and a probe
        asserting that the site emits NO row ran 24 passed. With the test it fails:
        AssertionError: SUBJECT-STRIP-EMITTED.

(!) Read the attribution. Each of the three sites is guarded by a DIFFERENT test, and no
test covers two of them. Under S1, the load-bearing test reddens on its settle-pass guard
rather than on a stale pair. The suppression also removes the TK73 leftover, so the
stranded pairs are what the replica tests see.

Instrument controls, applied to this file:
    S3  ``_Replica`` silently ignores REMOVED   -> 8 failed
    S4  ``_deficient_pairs`` skips nothing      -> 3 failed
          test_strip_arm_rows_reach_the_replica: AssertionError: the GC-window rows here
          are redundant for a replica -- the strip arm is not load-bearing on this fixture
          test_subject_gc_strip_arm_rows_reach_the_replica: AssertionError: the
          subject-GC strip-arm rows are redundant for a replica on this fixture
          test_late_gc_rows_are_load_bearing: AssertionError: dropping the late rows
          should strand exactly the GC'd node's pairs; stale=[]
    S5  ``oracle_true_seen`` given no tuples    -> 1 failed
          AssertionError: grid never answers True -- vacuous

Every mutation was restored from a temp copy, and ``cmp`` against the copy matched for
both ``processor.py`` and this file after each run.
"""
from __future__ import annotations

import sys

import pytest
from sqlmodel import select

from zanzibar.graphindex.models import Edge, Node
from zanzibar.graphindex.outbox import drain_deltas, outbox_rows, outbox_watermark
from zanzibar.graphindex.processor import DeltaProcessor
from zanzibar.schema import parse_openfga_schema
from tests.oracle import Oracle, OracleTuple
from tests.test_cascade_quiesce_gc import (SCHEMA, STAR_TARGET_NO_GC, STAR_TARGETS,
                                           _witness)
from tests.test_matrix import GraphBackend
from tests.wildcard_helpers import make_wildcard_index
import tests.test_i14_crossing_middles as i14


class _Replica:
    """An external ``drain_deltas`` consumer: an id-keyed pair set with a cursor."""

    def __init__(self):
        self.pairs: set[tuple[int, int]] = set()
        self.cursor = 0

    def catch_up(self, session, store_id):
        for d in drain_deltas(session, store_id, self.cursor):
            pair = (d.subject_id, d.object_id)
            if d.action == 'ADDED':
                assert pair not in self.pairs, f'unbalanced stream: ADDED for present {pair}'
                self.pairs.add(pair)
            else:
                assert d.action == 'REMOVED', d
                assert pair in self.pairs, f'unbalanced stream: REMOVED for absent {pair}'
                self.pairs.remove(pair)
        self.cursor = outbox_watermark(session, store_id)


def _primary_pairs(session, store_id) -> set[tuple[int, int]]:
    return {(e.subject_id, e.object_id) for e in session.exec(
        select(Edge).where(Edge.store_id == store_id)).all()}


def _instrument_gc(proc, session, store_id) -> list[tuple[object, int, int]]:
    """Record ``(arg, lo, hi)`` for every reconcile-time GC call: the rows it emitted
    are the outbox ids in ``(lo, hi]``. Both GC entry points are wrapped."""
    windows: list[tuple[object, int, int]] = []
    for name in ('_gc_subject_node', '_gc_public_node'):
        orig = getattr(proc, name)

        def wrapped(*a, _orig=orig, **k):
            session.flush()
            lo = outbox_watermark(session, store_id)
            out = _orig(*a, **k)
            session.flush()
            windows.append((a[0] if len(a) == 1 else a, lo,
                            outbox_watermark(session, store_id)))
            return out
        setattr(proc, name, wrapped)
    return windows


def _late_ids(windows) -> set[int]:
    return {i for (_, lo, hi) in windows for i in range(lo + 1, hi + 1)}


def _deficient_pairs(session, store_id, skip: set[int]) -> set[tuple[int, int]]:
    """The stream replayed WITHOUT the rows in ``skip`` (lenient: a skipped ADDED makes
    later REMOVEDs unbalanced, so this replica cannot be strict)."""
    pairs: set[tuple[int, int]] = set()
    for r in outbox_rows(session, store_id, 0):
        if r.id in skip:
            continue
        pair = (r.subject_node_id, r.object_node_id)
        (pairs.add if r.action == 'ADDED' else pairs.discard)(pair)
    return pairs


@pytest.mark.parametrize('star_target', STAR_TARGETS + (STAR_TARGET_NO_GC,))
def test_drained_replica_matches_primary_closure(star_target):
    """The "a replica fed them is RIGHT" half, on the TK73 witness family."""
    g = GraphBackend(SCHEMA, frozenset())
    try:
        windows = _instrument_gc(g.proc, g.session, 'g')
        replica = _Replica()
        for raw, op in _witness(star_target):
            assert g.apply(raw, op), f'{op} {raw} was REJECTED'
            replica.catch_up(g.session, 'g')
            assert replica.pairs == _primary_pairs(g.session, 'g'), (
                f'after {op} {raw}: replica-only '
                f'{sorted(replica.pairs - _primary_pairs(g.session, "g"))}, primary-only '
                f'{sorted(_primary_pairs(g.session, "g") - replica.pairs)}')
        late = _late_ids(windows)
        if star_target == STAR_TARGET_NO_GC:
            assert g.proc._settle is None and not late, (
                'the no-GC control started GC-ing -- see '
                'test_cascade_quiesce_gc::test_the_star_target_that_shares_the_removed_object')
        else:
            # Vacuity guards: the stream really carried reconcile-time-GC rows, and the
            # remove really took the TK73 settle path (the rows were LATE).
            assert late, 'no reconcile-time GC emitted a row -- this asserts nothing'
            assert g.proc._settle is not None, 'no settle pass ran -- not the TK73 shape'
    finally:
        g.close()


def test_strip_arm_rows_reach_the_replica():
    """The same property at TK75's second late-emission site (the
    ``_sync_entity_middles`` strip arm, inside a reconcile-time GC)."""
    rs, session, widx, proc = i14._make(paranoia=True)
    sid = widx.idx.store_id
    try:
        windows = _instrument_gc(proc, session, sid)
        replica = _Replica()
        ops = [(i14._WITNESS, 'add'), (i14._WITNESS, 'remove'), (i14._OWC_GRANT, 'add'),
               (i14._STAR_PARENT, 'add'), (i14._WITNESS, 'add'),
               (i14._WITNESS, 'remove'), (i14._STAR_PARENT, 'remove')]
        for raw, action in ops:
            i14._write(rs, session, widx, proc, raw, action=action)
            replica.catch_up(session, sid)
            assert replica.pairs == _primary_pairs(session, sid), f'after {action} {raw}'
        late = _late_ids(windows)
        assert late, 'no reconcile-time GC emitted a row -- this asserts nothing'
        assert _deficient_pairs(session, sid, late) != _primary_pairs(session, sid), (
            'the GC-window rows here are redundant for a replica -- the strip arm is '
            'not load-bearing on this fixture')
    finally:
        session.close()


#: The TK79 fix-1 fixture for the THIRD late-emission site, the strip arm at the end of
#: ``DeltaProcessor._gc_subject_node``. On the TK73 and I14 fixtures that call never emits
#: (measured by the 2026-10-12c review: a probe asserting it emits nothing ran green over
#: 24 tests), because there every recorded residue subject is a user or a group userset,
#: whose type has no crossable shape. Here a FOLDER userset (``folder:f1#member``) is the
#: recorded subject: reconcile records it in ``restricted``'s upos and promotes it
#: explicit, so it outlives the raw remove, and it is the entity folder:f1's only real
#: node. When the cascade un-records it, ``_gc_subject_node`` deletes it, the entity loses
#: its last real node, and ``_sync_entity_middles`` strips the middle folder:f1#viewer.
SUBJECT_GC_SCHEMA = (
    'type user\n'
    'type folder\n'
    '  relations\n'
    '    define parent: [folder, folder:*]\n'
    '    define member: [user]\n'
    '    define viewer: [user, user:*] or viewer from parent\n'
    'type doc\n'
    '  relations\n'
    '    define parent: [folder, folder:*]\n'
    '    define blocked: [user, folder#member]\n'
    '    define editor: [user, folder#member]\n'
    '    define viewer: [user, user:*] or viewer from parent\n'
    '    define restricted: editor but not blocked\n')
SUBJECT_GC_SHAPES = frozenset({('folder', 'viewer'), ('doc', 'viewer')})
SUBJECT_GC_TUPLE = ('member', 'folder', 'f1', 'editor', 'doc', 'd1')


def _instrument_sync_from(widx, session, store_id, caller: str):
    """Record ``(entity, lo, hi)`` for every ``_sync_entity_middles`` call made directly
    by ``caller``: the rows it emitted are the outbox ids in ``(lo, hi]``."""
    windows: list[tuple[tuple[str, str], int, int]] = []
    orig = widx._sync_entity_middles

    def wrapped(entity_type, name):
        session.flush()
        lo = outbox_watermark(session, store_id)
        orig(entity_type, name)
        session.flush()
        if sys._getframe(1).f_code.co_name == caller:
            windows.append(((entity_type, name), lo, outbox_watermark(session, store_id)))
    widx._sync_entity_middles = wrapped
    return windows


def test_subject_gc_strip_arm_rows_reach_the_replica():
    """The same property at the strip arm inside ``_gc_subject_node`` (TK79 fix-1: the
    first version of this module pinned only the ``_gc_public_node`` one). Also carries
    the oracle leg locally: after every write the primary agrees with the independent
    oracle on a small grid, so replica == primary pair set is replica == oracle closure
    for this fixture (the replica holds Edge pairs only; residue rows are not in the
    stream, so a derived-membership answer always needs the primary's residue)."""
    rs = parse_openfga_schema(SUBJECT_GC_SCHEMA, SUBJECT_GC_SHAPES, enable_boolean=True)
    session, widx = make_wildcard_index(rs.schema_info, paranoia=True)
    proc = DeltaProcessor(widx, rs.compiled)
    sid = widx.idx.store_id
    try:
        windows = _instrument_sync_from(widx, session, sid, '_gc_subject_node')
        replica = _Replica()
        grid = [(sp, st, sn, rel, ot, on)
                for (sp, st, sn) in (('...', 'user', 'u1'), ('member', 'folder', 'f1'))
                for (rel, ot, on) in (('editor', 'doc', 'd1'), ('restricted', 'doc', 'd1'),
                                      ('viewer', 'doc', 'd1'), ('viewer', 'folder', 'f1'))]
        stored: list = []
        for action in ('add', 'remove'):
            i14._write(rs, session, widx, proc, SUBJECT_GC_TUPLE, action=action)
            (stored.append if action == 'add' else stored.remove)(
                OracleTuple(*SUBJECT_GC_TUPLE))
            replica.catch_up(session, sid)
            assert replica.pairs == _primary_pairs(session, sid), f'after {action}'
            oracle = Oracle(SUBJECT_GC_SCHEMA, stored)
            assert [widx.check(*q) for q in grid] == [oracle.check(*q) for q in grid], (
                f'primary disagrees with the oracle after {action}')
        assert oracle_true_seen(rs, grid), 'grid never answers True -- vacuous'
        emitting = [(e, lo, hi) for (e, lo, hi) in windows if hi > lo]
        assert [e for (e, _, _) in emitting] == [('folder', 'f1')], (
            f'the _gc_subject_node strip arm did not emit on this fixture: {windows}')
        late = {i for (_, lo, hi) in emitting for i in range(lo + 1, hi + 1)}
        rows = [r for r in outbox_rows(session, sid, 0) if r.id in late]
        assert {r.action for r in rows} == {'REMOVED'} and all(
            'f1' in (r.subject_name, r.object_name) or '*' in (r.subject_name,
                                                              r.object_name)
            for r in rows), rows
        assert _deficient_pairs(session, sid, late) != _primary_pairs(session, sid), (
            'the subject-GC strip-arm rows are redundant for a replica on this fixture')
    finally:
        session.close()


def oracle_true_seen(rs, grid) -> bool:
    """Vacuity guard for the grid above: with the tuple stored, the oracle answers True
    somewhere on it (``member@folder:f1`` is an editor, and restricted, of doc:d1)."""
    oracle = Oracle(SUBJECT_GC_SCHEMA, [OracleTuple(*SUBJECT_GC_TUPLE)])
    return any(oracle.check(*q) for q in grid)


def test_late_gc_rows_are_load_bearing():
    """The "a replica MUST see them" half, as a permanent sabotage: drop exactly the rows
    emitted inside a reconcile-time GC and the replica goes wrong, first at the closure
    level and then, after SQLite recycles the GC'd node id, at the membership level."""
    g = GraphBackend(SCHEMA, frozenset())
    try:
        windows = _instrument_gc(g.proc, g.session, 'g')
        replica = _Replica()
        for raw, op in _witness('x'):
            assert g.apply(raw, op)
            replica.catch_up(g.session, 'g')

        assert g.proc._settle is not None, 'no settle pass ran -- not the TK73 shape'
        emitting = [(arg, lo, hi) for (arg, lo, hi) in windows if hi > lo]
        assert len(emitting) == 1, f'expected one emitting GC window, got {emitting}'
        gc_node, lo, hi = emitting[0]
        late_rows = outbox_rows(g.session, 'g', lo)[:hi - lo]
        # Measured 2026-10-12c: rows 13..15, the implicit userset node admin@folder:x.
        assert {(r.action, r.subject_predicate, r.subject_type, r.subject_name)
                for r in late_rows} == {('REMOVED', 'admin', 'folder', 'x')}, late_rows
        assert g.session.get(Node, gc_node) is None, 'the GC did not delete the node'

        primary = _primary_pairs(g.session, 'g')
        deficient = _deficient_pairs(g.session, 'g', _late_ids(windows))
        assert replica.pairs == primary
        stale = deficient - primary
        assert stale and all(s == gc_node for (s, _) in stale), (
            f'dropping the late rows should strand exactly the GC\'d node\'s pairs; '
            f'stale={sorted(stale)}')

        # Membership level: later writes reuse the id (SQLite rowid = max + 1; 7 and 8
        # go to user:u8 and admin@folder:q, so the next fresh node, user:u9, gets 9).
        # The stream (``drain_deltas``) carries node IDS only, so reading the replica's
        # stale pair as a claim about user:u9 resolves the id against the primary's
        # ``Node`` table -- which is what any id-keyed consumer has to do.
        writes = [('...', 'user', 'u8', 'admin', 'folder', 'q'),
                  ('...', 'user', 'u9', 'editor', 'folder', 'x')]
        for raw in writes:
            assert g.apply(raw, 'add')
            replica.catch_up(g.session, 'g')
        primary = _primary_pairs(g.session, 'g')
        assert replica.pairs == primary
        recycled = g.session.get(Node, gc_node)
        assert recycled is not None and (recycled.predicate, recycled.type,
                                         recycled.name) == ('...', 'user', 'u9'), (
            f'precondition: id {gc_node} was expected to be reused for user:u9, got '
            f'{recycled} -- SQLite id allocation changed; re-derive the witness')
        viewer_x = g.widx._get_concrete('viewer', 'folder', 'x')
        assert viewer_x is not None
        claim = (gc_node, viewer_x.id)
        deficient = _deficient_pairs(g.session, 'g', _late_ids(windows))
        assert claim in deficient, 'the deficient replica no longer carries the stale pair'
        assert claim not in replica.pairs and claim not in primary

        # The claim is TYPE-LEGAL (viewer admits [user]) and FALSE: u9 is only an editor
        # of folder:x and an admin of nothing. Control in the other direction: u8, an
        # admin of folder:q, IS a viewer of folder:x through the star parent, so the
        # query shape is one the oracle and the primary can answer True.
        surviving = [OracleTuple('...', 'folder', '*', 'parent', 'folder', 'x')] + [
            OracleTuple(*w) for w in writes]
        oracle = Oracle(SCHEMA, surviving)
        query = ('...', 'user', 'u9', 'viewer', 'folder', 'x')
        assert oracle.check(*query) is False and g.check(query) is False
        control = ('...', 'user', 'u8', 'viewer', 'folder', 'x')
        assert oracle.check(*control) is True and g.check(control) is True
    finally:
        g.close()
