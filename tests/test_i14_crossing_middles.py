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
from index_v4.outbox import outbox_rows, outbox_watermark
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


def test_the_strip_arm_emits_from_inside_a_reconcile_time_gc():
    """TK75 item 1: `_sync_entity_middles`' strip arm is a SECOND late-emission site,
    and this is its first witness.

    `TK73` fixed the cascade's terminal quiescence check after
    `_maybe_remove_bridges` was found emitting outbox rows from inside a reconcile-time
    GC, i.e. after the round's frontier snapshot. Its doc named
    `_sync_entity_middles` as a second such site and had no witness; `TK75` then
    recorded (agent-measured) that the site fires on THIS module's
    `test_middles_retire_with_their_entity` and that only instrumentation was missing.
    Re-derived first-hand 2026-09-19b and pinned here: the removal's cascade takes the
    no-witness branch, calls `_strip_bridges` on the `('folder','viewer')` middle, and
    that call emits **3** outbox rows while nested `cascade=1, reconcile=1, gc=1`.

    (!) THE HONEST OTHER HALF, and it is why this test does not assert a leftover: on
    this fixture the late rows map back to NO derived key, so `leftover` stays empty,
    no settle pass runs, and `_settle is None`. The site is a late EMITTER here; it is
    not (here) a late LEFTOVER producer, so it does not reproduce `TK73`'s shape. Do
    not read this test as "the second site reproduces TK73" -- it does not, and the
    fixture that would is `TK77`'s deliverable, not this module's.

    (!) The re-add arm of the same function is a separate question and is NOT pinned
    here. Measured 2026-09-19b across every module `TK77` names as coverage of the
    crossable surface (this one, `test_owc_star_parent_cross.py`,
    `test_bulk_build.py`): 7 `_sync_entity_middles` calls in total, **1** of them
    inside a reconcile-time GC, and that one takes the STRIP arm. The in-GC re-add arm
    is not reached by any of them, so a "forced-strip" control test here would be
    pinning a fixture invented for the probe rather than the shipped surface. Recorded
    as a negative on `TK75`; the fixture question belongs to `TK77`.

    SWEEP (literal output, 2026-09-19b, `.scratch/tk75/sweep_i14.py`). 5 mutations,
    5 RED, 0 INERT, P0 attributing, and every row reddens THIS pin::

        BASELINE  rc=0  5 passed in 0.47s
        P0   RED  new-pin=1  total-failed=1   the pin's own shape claim flipped
        P1   RED  new-pin=1  total-failed=2   no-witness branch stops stripping
        P2   RED  new-pin=1  total-failed=2   `_strip_bridges` emits nothing
        P3   RED  new-pin=1  total-failed=1   the pin's own depth counter un-armed
        P4   RED  new-pin=1  total-failed=1   a leftover key forced to survive the drain
        RESTORED  rc=0  5 passed in 0.46s

    (!) P4's FIRST form died of a `KeyError`, not of the property -- it injected
    `('folder','viewer','f1')`, which is not a derived key on this schema, so the
    cascade blew up in plan lookup before reaching the assertion. It reddened, and it
    proved nothing. That is `GL-1`'s instrument failure verbatim. The real derived
    keys here are `('doc','restricted')` and `('folder','restricted')`; with
    `('folder','restricted','f1')` the mutation dies on the `_settle is None` clause
    itself, which is what makes that clause live rather than decorative.
    """
    rs, session, widx, proc = _make(paranoia=True)
    _write(rs, session, widx, proc, _WITNESS)

    depth = {'cascade': 0, 'reconcile': 0, 'gc': 0}
    calls = []

    def _counted(key, fn):
        def inner(*a, **k):
            depth[key] += 1
            try:
                return fn(*a, **k)
            finally:
                depth[key] -= 1
        return inner

    o_strip = widx._strip_bridges

    def strip(node_id, shape):
        wm = outbox_watermark(session, widx.idx.store_id)
        out = o_strip(node_id, shape)
        session.flush()
        calls.append((shape, len(outbox_rows(session, widx.idx.store_id, wm)),
                      dict(depth)))
        return out

    widx._strip_bridges = strip
    proc.run_cascade = _counted('cascade', proc.run_cascade)
    proc.reconcile = _counted('reconcile', proc.reconcile)
    proc.reconcile_subject = _counted('reconcile', proc.reconcile_subject)
    proc._gc_subject_node = _counted('gc', proc._gc_subject_node)
    proc._gc_public_node = _counted('gc', proc._gc_public_node)

    _write(rs, session, widx, proc, _WITNESS, action='remove')

    assert calls, (
        'the strip arm never ran -- INSTRUMENT BROKEN or the fixture stopped reaching '
        'the site, and either way this test asserts nothing'
    )
    assert len(calls) == 1, f'expected one strip call, got {calls}'
    shape, emitted, nesting = calls[0]
    assert shape == ('folder', 'viewer'), f'stripped the wrong shape: {shape}'
    assert emitted > 0, (
        'the strip arm emitted NOTHING, so it is not a late-emission site and TK73 '
        "doc sec 7's second-site claim is wrong"
    )
    assert nesting['cascade'] >= 1 and nesting['reconcile'] >= 1 and nesting['gc'] >= 1, (
        f'the strip ran at nesting {nesting} -- "late emission" means from inside a '
        f'reconcile-time GC inside the cascade, and outside that it is an ordinary write'
    )

    # The honest other half: the rows map to no derived key here, so the cascade drains
    # without a settle pass. If this ever starts producing one, TK73's shape has arrived
    # at the second site and TK75/TK77 want to know.
    assert proc._settle is None, (
        f'a settle pass ran at the second emission site ({proc._settle}) -- this '
        f'fixture now reproduces TK73 shape here; that is a finding, not a failure'
    )
    assert widx._get_concrete('viewer', 'folder', 'f1') is None
    session.close()
