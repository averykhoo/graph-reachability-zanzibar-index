"""I14 (crossing-middle completeness) -- the permanent sabotage tests.

## The property (index_v4/invariants.py, next to I3)

For every CROSSABLE shape ``(T, p)`` (``SchemaInfo.crossable_shapes`` -- bridged in
AND out) and every entity name ``x`` such that the store holds at least one node
``(T, x, *)`` that is not itself a bridge-only middle, the store holds the node
``(T, x, p)`` with BOTH of its bridges.

I3 says a concrete of a bridged shape must HAVE its bridges; I14 says the middle must
EXIST while the entity does. It is what makes the 2026-08-09 fix (the graph
under-reporting the OWC x star-parent x TTU cross, ``docs/spec-deviations.md``
2026-08-09) self-policing: paranoia mode runs ``check_invariants`` inside every
commit, so a write path that stops maintaining the middles aborts the very first
innocent write instead of silently under-reporting again.

## Sabotage evidence (docs/sabotage-procedure.md -- literal observed output)

The sabotage is the narrowest plausible weakening: ``_ensure_entity_middles`` made a
no-op (exactly what a refactor that "simplifies the bridge code" would do), not a
deleted feature. The degraded store still has every OLD bridge -- I3 stays green --
and only I14 fires. Observed on this tree, 2026-08-09:

* checker sabotage (``test_i14_fires_when_middle_ensure_is_a_noop``)::

      index_v4.invariants.InvariantViolation: I14: entity folder:f1 exists but its
      crossing middle folder:f1#viewer for crossable shape ('folder', 'viewer') is
      missing

* paranoia self-policing (``test_paranoia_aborts_first_write_without_middles``)::

      index_v4.invariants.InvariantViolation: store='test' [pre-commit] I14: entity
      folder:f1 exists but its crossing middle folder:f1#viewer for crossable shape
      ('folder', 'viewer') is missing

* behaviour sabotage (reverting the middle-creation by hand -- a bare ``return`` at
  the top of ``_ensure_entity_middles`` -- and re-running the pinned files +
  this one): ``7 failed, 3 passed in 25.24s``. Notably the two 2026-08-09 pins
  (``tests/test_owc_star_parent_cross.py``, ``tests/test_irrelevant_alternatives
  .py``) no longer fail with the original quiet ``graph=False`` under-report: with
  I14 in the tree they abort at the FIRST write's commit --
  ``InvariantViolation: store='pg' [pre-commit] I14: entity folder:f1 exists but
  its crossing middle folder:f1#viewer for crossable shape ('folder', 'viewer') is
  missing`` -- i.e. the regression is now caught earlier and louder than the bug it
  reintroduces. (The 3 passes were the positive control, whose witness IS a
  ``(folder, viewer)`` node, and the two monkeypatch tests here, whose expectation
  the revert makes true.)

The honest-state test and the GC round-trip test are the controls in the other
direction: the checker must NOT fire on a store the fix maintains, and the middles
must retire with their entity (or add-then-remove stops being a row-multiset round
trip).
"""

from pathlib import Path

import pytest

from index_v4.invariants import InvariantViolation, check_invariants
from index_v4.outbox import outbox_watermark
from index_v4.processor import DeltaProcessor
from index_v4.wildcard import WildcardIndex
from tests.wildcard_helpers import make_wildcard_index, snapshot
from zanzibar_utils_v1 import Entity, RelationalTriple, parse_openfga_schema

_SHAPES = frozenset({('folder', 'viewer'), ('doc', 'viewer')})
_SCHEMA = (Path(__file__).parent / 'fga_schemas' / 'owc_star_ttu.fga').read_text()

# The filed divergence, minimised (docs/spec-deviations.md 2026-08-09): the witness
# mentions folder:f1 through a NON-viewer relation, so pre-fix no node of shape
# (folder, viewer) was ever interned and the graph answered the query False.
_WITNESS = ('...', 'user', 'u1', 'editor', 'folder', 'f1')
_OWC_GRANT = ('...', 'user', 'u1', 'viewer', 'folder', '*')
_STAR_PARENT = ('...', 'folder', '*', 'parent', 'doc', 'd1')
_QUERY = ('...', 'user', 'u1', 'viewer', 'doc', 'd1')


def _make(paranoia: bool):
    rs = parse_openfga_schema(_SCHEMA, _SHAPES, enable_boolean=True)
    session, widx = make_wildcard_index(rs.schema_info, paranoia=paranoia)
    proc = DeltaProcessor(widx, rs.compiled)
    return rs, session, widx, proc


def _write(rs, session, widx, proc, raw, *, action: str = 'add') -> None:
    """One raw tuple through the rewrite fan-out + same-transaction cascade + commit
    (the ``GraphBackend.apply`` convention -- a graph write on a boolean schema must
    cascade in the same transaction)."""
    sp, st, sn, rel, ot, on = raw
    wm = outbox_watermark(session, widx.idx.store_id)
    triple = RelationalTriple(Entity(st, sn), rel, Entity(ot, on),
                              Ellipsis if sp == '...' else sp)
    op = widx.add_tuple if action == 'add' else widx.remove_tuple
    for d in rs.apply(triple):
        op('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
           d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
    proc.run_cascade(wm)
    session.commit()


def test_honest_state_passes_and_graph_answers_true():
    """Negative control (sabotage-procedure: control the instrument BOTH ways).

    The fixed write path maintains the middles, so paranoia's per-commit I14 runs
    green on every write of the filed divergence store, the standalone checker
    passes, and the graph now agrees with the oracle on the query three backends
    already answered True (the crossing middle ``folder:f1#viewer`` exists purely
    because the ENTITY ``folder:f1`` does)."""
    rs, session, widx, proc = _make(paranoia=True)
    for raw in (_WITNESS, _OWC_GRANT, _STAR_PARENT):
        _write(rs, session, widx, proc, raw)
    check_invariants(session, widx.idx.store_id, rs.schema_info)
    # the middle exists for the ENTITY, though nothing ever wrote a viewer tuple on f1
    assert widx._get_concrete('viewer', 'folder', 'f1') is not None
    assert widx.check(*_QUERY) is True
    session.close()


def test_i14_fires_when_middle_ensure_is_a_noop(monkeypatch):
    """★ The checker sabotage: ``_ensure_entity_middles`` as a no-op (the narrowest
    plausible weakening -- every OLD bridge still materializes, so I3 stays green and
    a naive "bridges are all there" reading stays green too). I14 must be the clause
    that fires, and it must name the missing middle. Literal observed output in the
    module docstring."""
    monkeypatch.setattr(WildcardIndex, '_ensure_entity_middles',
                        lambda self, entity_type, name: None)
    rs, session, widx, proc = _make(paranoia=False)
    for raw in (_WITNESS, _OWC_GRANT, _STAR_PARENT):
        _write(rs, session, widx, proc, raw)
    with pytest.raises(InvariantViolation) as exc:
        check_invariants(session, widx.idx.store_id, rs.schema_info)
    assert 'I14' in str(exc.value)
    assert 'folder:f1#viewer' in str(exc.value)
    session.close()


def test_paranoia_aborts_first_write_without_middles(monkeypatch):
    """★ The self-policing leg: with paranoia ON (the test-suite default), a write
    path that stops maintaining the middles cannot even land the first innocent
    write -- the commit aborts on I14 rather than the store silently regressing to
    the 2026-08-09 under-report. Literal observed output in the module docstring."""
    monkeypatch.setattr(WildcardIndex, '_ensure_entity_middles',
                        lambda self, entity_type, name: None)
    rs, session, widx, proc = _make(paranoia=True)
    with pytest.raises(InvariantViolation) as exc:
        _write(rs, session, widx, proc, _WITNESS)
    assert 'I14' in str(exc.value)
    session.rollback()
    session.close()


def test_middles_retire_with_their_entity():
    """The GC direction of I14's lifecycle: the middle tracks ENTITY existence, so
    removing the entity's last real tuple must collect the middle (and the w nodes it
    alone kept alive) -- add-then-remove stays an exact row-multiset round trip.
    Guards ``_sync_entity_middles`` / the ``_maybe_remove_bridges`` middle-preserving
    branch from the opposite side: keeping middles forever would also satisfy the
    completeness invariant, and this is what refuses that."""
    rs, session, widx, proc = _make(paranoia=True)
    clean = snapshot(widx)
    _write(rs, session, widx, proc, _WITNESS)
    assert widx._get_concrete('viewer', 'folder', 'f1') is not None, \
        'the middle must exist while the entity does'
    _write(rs, session, widx, proc, _WITNESS, action='remove')
    assert widx._get_concrete('viewer', 'folder', 'f1') is None, \
        'the middle must go when the entity does'
    assert snapshot(widx) == clean, 'add-then-remove must restore the row multiset'
    session.close()
