"""Regression pin for the released-userset-subject bridge leak
(filed docs/spec-deviations.md ## 2026-08-20b, FIXED ## 2026-08-21).

Found by the hypothesis campaign
(``test_hypothesis.py::test_add_then_remove_restores_row_multiset``); the cached
counterexample lives in the gitignored ``.hypothesis/`` DB, so this file is the
durable, seed-independent pin. The tests are POSITIVE pins of the required
behaviour (row-multiset restoration; an empty store answers empty), per
CLAUDE.md's "a divergence gets a positive pin, never an xfail". They were filed
RED and went green with the fix below -- an xfail is itself a failure that
passes, and a ``skip`` would both hide the evidence while iterating AND still
turn the gate red (``verify.sh`` asserts zero skipped), so it buys nothing.

THE FIX (2026-08-21), and what these tests now guard.
``processor.py::DeltaProcessor._gc_subject_node`` now DEMOTES the released node
before asking ``_maybe_remove_bridges`` to strip it. The strip guard is
``implicit and reference_count == degree``; a released userset subject is still
EXPLICIT from the add-cascade's step-2d promotion, so the strip-first order was
a guaranteed no-op on exactly the path that needed it, and nothing re-checked
after the demote landed. Relaxing the guard would have been the WRONG fix -- it
is what implements ``remove_node``'s "explicit nodes keep bridges for as long as
they exist" policy.

⚠ SABOTAGE RECORD (2026-08-21), per docs/sabotage-procedure.md. The weakening
these pins must catch is not a dramatic one -- it is a future reader tidying the
two calls back into their old order. That exact edit (order swapped, every other
part of the fix intact) was applied and both pins went red::

    FAILED tests/test_userset_bridge_release_leak.py::test_released_userset_subject_add_remove_restores_rows
    FAILED tests/test_userset_bridge_release_leak.py::test_released_userset_subject_lookup_is_empty_after_drain
    2 failed in 0.37s

and restoring the order gave ``2 passed in 0.30s``. So the ORDER is what these
tests pin, which is the property that was actually broken.

THE BUG AS FILED. On a schema where a TTU's tupleset is DERIVED (boolean-tainted) and
carries an object-star arm, the TTU target shape (here ``(doc, r0)``) becomes
subject-bridged (``SchemaInfo.bridged_in_shapes``), so a raw write whose subject
is the userset ``doc:d1#r0`` bridges that subject node to ``w_any(doc, r0)`` at
``WildcardIndex._add_tuple_trusted`` -> ``_ensure_bridges``. The add-cascade then
records the subject in the object's residue ``upos`` and PROMOTES it explicit
(processor step 2d). On removal the teardown WAS asymmetric with that setup:

  * ``wildcard.py::_remove_tuple_trusted`` calls ``_maybe_remove_bridges`` right
    after the leaf-edge removal, but the node is still EXPLICIT (recorded in
    upos, cascade not yet run), and the strip guard requires
    ``implicit and reference_count == bridge degree`` -> no-op. This call is
    STILL a no-op on this path and is not what was fixed; it is listed because
    it is the reason the release path is the only place the strip can land;
  * the remove-cascade then drops the recording and runs
    ``processor.py::DeltaProcessor._gc_subject_node``, which CALLED
    ``_maybe_remove_bridges`` BEFORE ``_demote_released_node`` flipped the node
    back to implicit -> no-op again, and nothing re-checked after the demote.
    That second call is the one now ordered after the demote.

Literal observed leak (snapshot_rows delta after add-then-remove from empty, at
the filing tree; node rows are (predicate, type, name, wildcard, implicit,
reference_count)):

    nodes leaked : [(('r0', 'doc', '*', 'any', True, 1), 1),
                    (('r0', 'doc', 'd1', '', True, 1), 1)]
    edges leaked : [((('r0', 'doc', 'd1', ''), ('r0', 'doc', '*', 'any'), 1, 1), 1)]

Severity (probed 2026-08-20, full grid on both backends + tests/oracle.py):
STATE-ONLY. 255-query check grid: 0 disagreements; the full lookup-surface
oracle battery passes on the leaked store. The only observable trace is a
spurious variant-'any' marker in graph forward lookup (pinned below) -- a facet
``test_lookup_oracle.py`` documents as carrying no pointwise claim. Not an
authorization fail-open; it violates row-multiset restoration and leaks
unbounded node/edge state under add/remove churn.

Load-bearing (measured by dropping each feature in turn): the DERIVED tupleset
(Exclusion and Intersection both leak; a plain star tupleset is clean), the
object-star arm in the tupleset (no star -> clean), the TTU over it (dropped ->
clean), and the userset-shaped subject write. NOT load-bearing: the wildcard on
the target relation, the self-referential subject, and the extra
Computed/folder relations of the original counterexample.
"""

from index_v4.invariants import snapshot_rows
from tests.test_processor import build

# The minimized repro: one type, three relations. ``parent`` is derived (any
# taint works; Exclusion here) with an object-star arm, ``r1`` hosts a TTU over
# it plus the direct userset arm that admits the tuple.
MINIMAL_SCHEMA = '''
    type doc
      relations
        define parent: [doc:*] but not [doc]
        define r0: [user]
        define r1: r0 from parent or [doc#r0]
'''

# A userset-shaped subject on r1 (self-reference NOT required; d1 -> d2 leaks too).
TUPLE = ('r0', 'doc', 'd1', 'r1', 'doc', 'd1')


def test_released_userset_subject_add_remove_restores_rows():
    """Add-then-remove of a single userset-subject tuple from an EMPTY store must
    restore the empty row multiset. As filed it leaked the subject node, its
    ``w_any`` bridge edge, and the ``w_any`` node (docstring above, ledger
    2026-08-20b); green since the demote-before-strip fix (ledger 2026-08-21)."""
    session, widx, proc, write = build(MINIMAL_SCHEMA)
    store_id = widx.idx.store_id
    before = snapshot_rows(session, store_id)
    write('add', TUPLE)
    write('remove', TUPLE)
    after = snapshot_rows(session, store_id)
    proc.audit_fixpoint()
    session.close()
    assert after == before, (
        'add-then-remove did not restore the row multiset:\n'
        f'  leaked nodes: {sorted((after[0] - before[0]).items())}\n'
        f'  leaked edges: {sorted((after[1] - before[1]).items())}\n'
        f'  lost nodes:   {sorted((before[0] - after[0]).items())}\n'
        f'  lost edges:   {sorted((before[1] - after[1]).items())}'
    )


def test_released_userset_subject_lookup_is_empty_after_drain():
    """The leak's one observable read-surface trace: after draining the store,
    graph ``lookup`` for the released userset subject must be EMPTY. As filed,
    the leaked ``doc:d1#r0 -> w_any(doc, r0)`` bridge rendered as a spurious
    ``('doc', 'r0', 'any')`` marker (probe 2026-08-20: A(add+remove) returned
    ``[('doc', 'r0', 'any')]`` where B(fresh) returned ``[]``). Forward 'any'
    markers carry no pointwise claim (test_lookup_oracle.py G3 note) -- this
    pins the state leak at the surface where it shows, not an over-grant."""
    session, widx, proc, write = build(MINIMAL_SCHEMA)
    write('add', TUPLE)
    write('remove', TUPLE)
    res = widx.lookup('r0', 'doc', 'd1')
    session.close()
    assert set(res.node_ids) == set() and set(res.markers) == set(), (
        f'drained store still answers for the released subject: '
        f'node_ids={sorted(res.node_ids)} markers={sorted(res.markers)}'
    )
