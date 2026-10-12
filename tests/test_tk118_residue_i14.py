"""TK118 -- the cheap paranoia tier (``residue``) carries a DELTA-SCOPED I14.

## Why

``tests/test_p12_severity_sign.py::test_which_paranoia_level_catches_the_simulated_revert``
measured (2026-09-27) that a regression of the 2026-08-09 crossing-middle fix serves a
fail-OPEN answer at ``residue`` -- the tier ``CLAUDE.md`` recommends in production -- because
I14 lived only in the whole-store ``check_invariants``. The decision and its reasoning:
``docs/tk118-residue-i14-2026-10-12.md``.

## What the tier now does

``ParanoiaGuard.note_flush`` (an ``after_flush`` listener) records the ``(type, name)``
entities whose concrete ``Node`` rows a transaction created, modified or deleted, plus any
crossable type whose WILDCARD node was created or deleted; pre-commit,
``invariants.py::check_i14_delta`` runs the full checker's own clause (``_check_i14``, shared)
over exactly those entities. Nothing is recorded or queried on a schema with no crossable
shape, i.e. on every plain OpenFGA schema.

## What each test pins

* the add-side regression (no middle interned) and the remove-side regression (a middle
  stripped while its entity is still witnessed) both ABORT the write at ``residue``;
* the honest lifecycle (add, remove, wildcard-node GC) commits clean at ``residue``;
* the tier is delta-scoped, NOT whole-store: corruption of an entity the transaction did not
  touch commits happily at ``residue`` and is caught by the same clause when that entity is
  named -- the boundary is the scope, never the clause;
* a plain schema records nothing;
* the listener records each ``Session`` bucket (new / dirty / deleted) on its own, and a
  wildcard node widens the scan to its whole type only when created or deleted -- a deleted
  ``w_any`` under a live middle aborts.

## Mutation sweep (literal, 2026-10-12b; ``.scratch/tk118/mut.py``, anchors asserted once,
file restored and hash-checked) over this module + P12 + I14 + paranoia-wiring::

    M0 control: no change                                          68 passed
    M1 check_i14_delta checks nothing                              5 failed
    M2 residue tier never calls check_i14_delta                    4 failed
    M3 note_flush ignores session.new                              1 failed  (bucket[new])
    M4 note_flush ignores session.deleted                          2 failed
    M5 commit does not empty the delta                             3 failed
    M6 delta check sees no bridge edges                            6 failed
    M7 wildcard create/delete never widens to the whole type       1 failed
    M8 type branch scans nothing                                   3 failed
    ALL RESTORED (hash-checked)

Before the bucket and wildcard tests existed, M3, M4 and M7 survived: on the real write path
the buckets overlap, so the end-to-end tests alone could not tell them apart.
"""

from pathlib import Path

import pytest
from sqlalchemy import or_
from sqlmodel import Session, delete, select

from zanzibar.graphindex.invariants import (InvariantViolation, check_i14_delta,
                                            check_invariants)
from zanzibar.graphindex.models import Edge, Node
from zanzibar.graphindex.outbox import outbox_watermark
from zanzibar.graphindex.processor import DeltaProcessor
from zanzibar.graphindex.wildcard import WildcardIndex
from tests.wildcard_helpers import make_wildcard_index, snapshot
from zanzibar.schema import Entity, RelationalTriple, parse_openfga_schema

_SHAPES = frozenset({('folder', 'viewer'), ('doc', 'viewer')})
_SCHEMA = (Path(__file__).parent / 'fga_schemas' / 'owc_star_ttu.fga').read_text()

_WITNESS = ('...', 'user', 'u1', 'editor', 'folder', 'f1')    # folder:f1, not a viewer node
_WITNESS2 = ('...', 'user', 'u1', 'blocked', 'folder', 'f1')  # a second witness of folder:f1
_OTHER = ('...', 'user', 'u2', 'editor', 'folder', 'f2')      # an unrelated entity


def _make(paranoia):
    rs = parse_openfga_schema(_SCHEMA, _SHAPES, enable_boolean=True)
    session, widx = make_wildcard_index(rs.schema_info, paranoia=paranoia)
    return rs, session, widx, DeltaProcessor(widx, rs.compiled)


def _write(rs, session, widx, proc, raw, *, action='add', commit=True):
    """One raw tuple through the rewrite fan-out + same-transaction cascade (+ commit):
    the ``tests/test_i14_crossing_middles.py::_write`` convention."""
    sp, st, sn, rel, ot, on = raw
    wm = outbox_watermark(session, widx.idx.store_id)
    triple = RelationalTriple(Entity(st, sn), rel, Entity(ot, on),
                              Ellipsis if sp == '...' else sp)
    op = widx.add_tuple if action == 'add' else widx.remove_tuple
    for d in rs.apply(triple):
        op('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
           d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
    proc.run_cascade(wm)
    if commit:
        session.commit()


def test_residue_aborts_the_add_side_regression(monkeypatch):
    """★ ``_ensure_entity_middles`` as a no-op (the P12 simulation): the FIRST innocent
    write -- which creates the witness node, the ``new`` path -- aborts at ``residue``."""
    monkeypatch.setattr(WildcardIndex, '_ensure_entity_middles',
                        lambda self, entity_type, name: None)
    rs, session, widx, proc = _make('residue')
    with pytest.raises(InvariantViolation,
                       match=r"\[pre-commit\] I14: entity folder:f1 exists but its "
                             r"crossing middle folder:f1#viewer"):
        _write(rs, session, widx, proc, _WITNESS)
    session.rollback()
    session.close()


def test_residue_aborts_the_remove_side_regression(monkeypatch):
    """★ ``_sync_entity_middles`` stripping middles while a witness REMAINS (it skips the
    "still witnessed" branch): removing one of two witnesses deletes the middle node --
    the ``deleted`` path -- and must abort at ``residue``. The same sequence on the honest
    code is the control: it commits."""
    def strip_always(self, entity_type, name):
        if name == '*':
            return
        for n in self._entity_nodes(entity_type, name):
            if self._is_bridge_middle(n):
                self._strip_bridges(n.id, (n.type, n.predicate))

    rs, session, widx, proc = _make('residue')
    for raw in (_WITNESS, _WITNESS2):
        _write(rs, session, widx, proc, raw)
    _write(rs, session, widx, proc, _WITNESS, action='remove')       # control: honest
    assert widx._get_concrete('viewer', 'folder', 'f1') is not None
    session.close()

    rs, session, widx, proc = _make('residue')
    for raw in (_WITNESS, _WITNESS2):
        _write(rs, session, widx, proc, raw)
    # patched only now: the add path's cascade calls _sync_entity_middles too, and this
    # test is about the REMOVE side
    monkeypatch.setattr(WildcardIndex, '_sync_entity_middles', strip_always)
    with pytest.raises(InvariantViolation, match=r'I14: entity folder:f1 exists'):
        _write(rs, session, widx, proc, _WITNESS, action='remove')
    session.rollback()
    session.close()


def test_residue_honest_lifecycle_commits_clean():
    """CONTROL (no false positives): add two entities, remove both -- including the GC of
    the crossable shapes' wildcard nodes, which takes the whole-type branch -- all commit
    at ``residue``, and add-then-remove restores the row multiset."""
    rs, session, widx, proc = _make('residue')
    clean = snapshot(widx)
    for raw in (_WITNESS, _WITNESS2, _OTHER):
        _write(rs, session, widx, proc, raw)
    check_invariants(session, widx.idx.store_id, rs.schema_info)
    for raw in (_OTHER, _WITNESS2, _WITNESS):
        _write(rs, session, widx, proc, raw, action='remove')
    assert snapshot(widx) == clean
    session.close()


def test_the_tier_is_delta_scoped_not_whole_store():
    """Honesty pin for the tier table: corrupt ``folder:f1`` (drop its crossing middle) in
    a side session the guard does not watch, then write ``folder:f2`` at ``residue`` -- it
    commits, because f1 was not touched. The same clause catches f1 the moment f1 is in
    scope, so the miss is the SCOPE, not the clause. If someone widens the tier to a
    whole-store scan, this test must move -- and the cost must be re-measured."""
    rs, session, widx, proc = _make('residue')
    _write(rs, session, widx, proc, _WITNESS)
    store = widx.idx.store_id
    mid = widx._get_concrete('viewer', 'folder', 'f1')
    assert mid is not None
    mid_id = mid.id
    with Session(session.get_bind()) as side:                # no paranoia listeners
        side.exec(delete(Edge).where(or_(Edge.subject_id == mid_id,
                                         Edge.object_id == mid_id)))
        side.exec(delete(Node).where(Node.id == mid_id))
        side.commit()
    session.expire_all()

    _write(rs, session, widx, proc, _OTHER)                  # f2 only: commits happily
    with pytest.raises(InvariantViolation, match=r'I14: entity folder:f1 exists'):
        check_i14_delta(session, store, rs.schema_info, {('folder', 'f1')}, set())
    with pytest.raises(InvariantViolation, match=r'I14: entity folder:f1 exists'):
        check_i14_delta(session, store, rs.schema_info, set(), {'folder'})
    session.close()


def test_a_plain_schema_records_nothing():
    """The zero-cost claim: with no crossable shape the listener records nothing (and
    ``check_i14_delta`` returns before any query). The crossable schema is the control:
    the same kind of write, flushed but uncommitted, IS recorded."""
    plain = parse_openfga_schema(
        'model\n  schema 1.1\ntype user\ntype folder\n  relations\n'
        '    define editor: [user, user:*]\n')
    assert not plain.schema_info.crossable_shapes
    session, widx = make_wildcard_index(plain.schema_info, paranoia='residue')
    widx.add_tuple('...', 'user', 'u1', 'editor', 'folder', 'f1')
    session.flush()
    guard = session.info['paranoia_guards'][widx.idx.store_id]
    assert guard.i14_entities == set() and guard.i14_types == set()
    session.commit()
    session.close()

    rs, session, widx, proc = _make('residue')
    _write(rs, session, widx, proc, _WITNESS, commit=False)
    session.flush()
    guard = session.info['paranoia_guards'][widx.idx.store_id]
    assert ('folder', 'f1') in guard.i14_entities
    session.commit()
    assert guard.i14_entities == set(), 'a commit must empty the delta'
    session.close()


def _guard(session, widx):
    return session.info['paranoia_guards'][widx.idx.store_id]


@pytest.mark.parametrize('bucket', ['new', 'dirty', 'deleted'])
def test_the_listener_records_each_bucket_on_its_own(bucket):
    """The listener's contract, one ``Session`` bucket at a time. On the real write path the
    buckets overlap (a node is created, then its refcount moves in a later flush), so the
    end-to-end tests above stay green with ``new`` or ``deleted`` ignored (mutation sweep in
    ``docs/tk118-residue-i14-2026-10-12.md``); this is what gives each bucket its own witness."""
    rs, session, widx, proc = _make('residue')
    store = widx.idx.store_id
    n = Node(store_id=store, type='folder', name='f9', predicate='editor', wildcard='',
             implicit=True, reference_count=0)
    if bucket != 'new':
        with Session(session.get_bind()) as side:            # created out of sight
            side.add(n)
            side.commit()
            side.refresh(n)
            nid = n.id
        n = session.get(Node, nid)
    guard = _guard(session, widx)
    assert guard.i14_entities == set()
    if bucket == 'new':
        session.add(n)
    elif bucket == 'dirty':
        n.reference_count += 1
        session.add(n)
    else:
        session.delete(n)
    session.flush()
    assert guard.i14_entities == {('folder', 'f9')}
    assert guard.i14_types == set()
    session.rollback()
    session.close()


def test_a_wildcard_node_matters_only_when_created_or_deleted():
    """A crossable shape's wildcard node: its refcount moves on EVERY bridge add, so a
    ``dirty`` wildcard node must not widen the scan to the whole type, while deleting it
    must -- the middles of every entity of that type lose a bridge."""
    rs, session, widx, proc = _make('residue')
    _write(rs, session, widx, proc, _WITNESS)
    guard = _guard(session, widx)
    w_any = session.exec(select(Node).where(Node.store_id == widx.idx.store_id)
                         .where(Node.type == 'folder').where(Node.predicate == 'viewer')
                         .where(Node.wildcard == 'any')).one()
    w_any.reference_count += 1
    session.add(w_any)
    session.flush()
    assert guard.i14_types == set(), 'a dirty wildcard node must not widen the scan'
    session.rollback()


def test_residue_catches_a_wildcard_node_deleted_under_a_live_middle():
    """★ The whole-type branch's witness: drop ``w_any(folder, viewer)`` and its edges
    through the guarded session WITHOUT touching any concrete node (an over-eager GC of the
    shared wildcard node). The only touch is the wildcard node's deletion, and the write
    must abort on the live middle ``folder:f1#viewer`` losing its bridge."""
    rs, session, widx, proc = _make('residue')
    _write(rs, session, widx, proc, _WITNESS)
    store = widx.idx.store_id
    w_any = session.exec(select(Node).where(Node.store_id == store)
                         .where(Node.type == 'folder').where(Node.predicate == 'viewer')
                         .where(Node.wildcard == 'any')).one()
    for e in session.exec(select(Edge).where(Edge.store_id == store).where(
            or_(Edge.subject_id == w_any.id, Edge.object_id == w_any.id))).all():
        session.delete(e)
    session.delete(w_any)
    with pytest.raises(InvariantViolation,
                       match=r'I14: crossing middle folder:f1#viewer is missing its '
                             r'concrete->w_any bridge'):
        session.commit()
    session.rollback()
    session.close()
