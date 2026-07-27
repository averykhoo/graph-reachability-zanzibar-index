"""reg17 (zero-trust ZT-P1-6a): a per-write closure fan-out cap on the graph index.

There were no resource bounds anywhere in this library -- no fuel counter, no fan-out
cap, no tuple quota. One direct-edge addition expands
|ancestors(subject)| x |descendants(object)| closure rows (the review measured 240 raw
tuples in a hub topology producing 14,640 rows in 5.1 s), and it does so INSIDE
``advance_index`` while holding the source lock AND the graph store lock, so a single
write stalls every other writer on the store for its whole duration.

``ReachabilityIndex.max_closure_fanout`` bounds that. What these tests pin:

  * the cap counts the region EXACTLY (|A|x|D| + |A| + |D|) -- boundary tested, so a
    future refactor of the expansion loops cannot drift the accounting;
  * a rejection is an ``AdmissionRejected`` that leaves NO partial state, and rollback
    restores the store byte-for-byte;
  * REMOVALS are never capped (a cap on shrinking would make an over-large region
    permanently unshrinkable -- a worse DoS than the one being bounded);
  * configuration: constructor argument > env var > module default, malformed input
    fails loud, ``0`` disables;
  * the DEFAULT cannot refuse anything this repo writes -- pinned against the measured
    suite maximum, so lowering the constant under it fails here rather than in the
    conformance differential.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, func, select

from index_v4 import ReachabilityIndex, Store
from index_v4.core import (DEFAULT_MAX_CLOSURE_FANOUT, MAX_CLOSURE_FANOUT_ENV,
                           resolve_max_closure_fanout)
from index_v4.invariants import check_invariants, snapshot_rows
from index_v4.models import DeltaOutboxV1, EdgeV4, NodeV4
from zanzibar_utils_v1 import AdmissionRejected

# Largest single-write closure expansion the existing suite produces, measured
# 2026-07-27 by instrumenting the expansion path and running both suites to
# completion: 44 rows over `tests/` (727 tests) and 124 over `formal/conformance/`
# (391 tests). The default must sit far above the larger of the two or it would start
# refusing writes that are legal today -- including inside the Lean differential,
# where a spurious rejection is silently absorbed as "the graph rejected it"
# (ZT-P4-7) and would shrink both corners of the comparison rather than fail.
MEASURED_SUITE_MAX_FANOUT = 124


def _store(cap=None):
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Store(id='s'))
    session.commit()
    return session, ReachabilityIndex(session, store_id='s', max_closure_fanout=cap)


def _hub(idx, n_anc: int, n_desc: int):
    """``n_anc`` ancestors above node ``s``, ``n_desc`` descendants below node ``o``.

    Adding ``s -> o`` then expands exactly n_anc*n_desc + n_anc + n_desc closure rows.
    Every hop uses one predicate/type so the object node of one edge IS the subject
    node of the next.
    """
    for i in range(n_anc):
        idx.add_edge('p', 't', f'x{i}', 'p', 't', 's')
    for j in range(n_desc):
        idx.add_edge('p', 't', 'o', 'p', 't', f'y{j}')


def _counts(session):
    return (session.exec(select(func.count()).select_from(EdgeV4)).one(),
            session.exec(select(func.count()).select_from(NodeV4)).one(),
            session.exec(select(func.count()).select_from(DeltaOutboxV1)).one())


# --------------------------------------------------------------------------- #
# the cap fires, and its arithmetic is exact
# --------------------------------------------------------------------------- #

def test_cap_boundary_is_the_exact_region_size():
    """4 ancestors x 4 descendants + fringes == 24 rows: a cap of 24 admits it, 23
    refuses it. Pins the counting formula, not just 'something big is refused'."""
    for cap, admitted in ((24, True), (23, False)):
        session, idx = _store(cap=cap)
        _hub(idx, 4, 4)
        session.commit()
        before = _counts(session)
        if admitted:
            idx.add_edge('p', 't', 's', 'p', 't', 'o')
            session.commit()
            # +24 closure rows, +1 direct edge row for s->o
            assert _counts(session)[0] == before[0] + 25
        else:
            with pytest.raises(AdmissionRejected) as exc:
                idx.add_edge('p', 't', 's', 'p', 't', 'o')
            assert '24 closure rows' in str(exc.value)
            assert 'limit of 23' in str(exc.value)
            assert MAX_CLOSURE_FANOUT_ENV in str(exc.value)
        session.close()


def test_rejection_leaves_no_partial_state():
    """A refusal must be a no-op on the store, not a half-expanded closure. Checked
    twice: nothing was written before the raise, and rollback restores the exact
    row-multiset snapshot (this layer never commits -- rollback is the contract)."""
    session, idx = _store(cap=10)
    _hub(idx, 4, 4)
    session.commit()
    snap_before = snapshot_rows(session, 's')
    counts_before = _counts(session)

    with pytest.raises(AdmissionRejected):
        idx.add_edge('p', 't', 's', 'p', 't', 'o')

    # nothing written at all -- not even the outbox rows the expansion would emit
    assert _counts(session) == counts_before
    session.rollback()
    assert _counts(session) == counts_before
    assert snapshot_rows(session, 's') == snap_before
    check_invariants(session, 's')

    # and the store is still WRITABLE afterwards: a small write goes through, so the
    # rejection did not wedge the session or leave the store lock in a bad state.
    idx.add_edge('p', 't', 'lone', 'p', 't', 'other')
    session.commit()
    assert _counts(session)[0] == counts_before[0] + 1
    session.close()


def test_removals_are_never_capped():
    """The bound is on GROWTH. Build an over-cap region with the cap disabled, then
    remove through an index whose cap is 1: the remove must succeed. A cap that
    refused removes would make the region permanently unshrinkable."""
    session, idx = _store(cap=0)                       # disabled: build freely
    _hub(idx, 4, 4)
    idx.add_edge('p', 't', 's', 'p', 't', 'o')
    session.commit()
    edges_before = _counts(session)[0]

    tight = ReachabilityIndex(session, store_id='s', max_closure_fanout=1)
    with pytest.raises(AdmissionRejected):             # control: adds ARE refused
        tight.add_edge('p', 't', 'x0', 'p', 't', 'o')
    session.rollback()

    tight.remove_edge('p', 't', 's', 'p', 't', 'o')    # the removal is not
    session.commit()
    assert _counts(session)[0] == edges_before - 25, 'the 24 closure rows + direct edge must retire'
    check_invariants(session, 's')
    session.close()


def test_node_removal_is_never_capped():
    """``remove_node`` runs the same expansion path with count == -1 (the node-removal
    shortcut). It must stay reachable however tight the cap is, or a store could be
    written into a state it can never be cleaned out of."""
    session, idx = _store(cap=0)
    _hub(idx, 4, 4)
    idx.add_edge('p', 't', 's', 'p', 't', 'o')
    session.commit()

    tight = ReachabilityIndex(session, store_id='s', max_closure_fanout=1)
    tight.remove_node('p', 't', 's')
    session.commit()
    assert session.exec(select(func.count()).select_from(NodeV4)
                        .where(NodeV4.name == 's')).one() == 0
    check_invariants(session, 's')
    session.close()


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #

def test_resolution_order_and_disable(monkeypatch):
    monkeypatch.delenv(MAX_CLOSURE_FANOUT_ENV, raising=False)
    assert resolve_max_closure_fanout(None) == DEFAULT_MAX_CLOSURE_FANOUT
    assert resolve_max_closure_fanout(7) == 7
    assert resolve_max_closure_fanout(0) == 0, '0 must mean disabled, not default'

    monkeypatch.setenv(MAX_CLOSURE_FANOUT_ENV, '5')
    assert resolve_max_closure_fanout(None) == 5
    assert resolve_max_closure_fanout(9) == 9, 'the constructor argument must win'
    session, idx = _store()                            # picks the env up at construction
    assert idx.max_closure_fanout == 5
    session.close()

    monkeypatch.setenv(MAX_CLOSURE_FANOUT_ENV, '')
    assert resolve_max_closure_fanout(None) == DEFAULT_MAX_CLOSURE_FANOUT


def test_malformed_configuration_fails_loud(monkeypatch):
    """A typo'd env var must NOT silently restore unbounded behaviour."""
    monkeypatch.setenv(MAX_CLOSURE_FANOUT_ENV, 'lots')
    with pytest.raises(ValueError):
        resolve_max_closure_fanout(None)
    monkeypatch.delenv(MAX_CLOSURE_FANOUT_ENV, raising=False)
    with pytest.raises(ValueError):
        resolve_max_closure_fanout(-1)


def test_disabled_cap_admits_an_arbitrarily_wide_region():
    session, idx = _store(cap=0)
    _hub(idx, 5, 5)
    idx.add_edge('p', 't', 's', 'p', 't', 'o')         # 5*5 + 5 + 5 == 35 rows
    session.commit()
    assert idx.max_closure_fanout == 0
    assert _counts(session)[0] == 5 + 5 + 35 + 1
    session.close()


# --------------------------------------------------------------------------- #
# the default is a blast-radius bound, not a policy: it must refuse nothing
# --------------------------------------------------------------------------- #

def test_default_has_headroom_over_the_measured_suite_maximum():
    """Lowering the default under what the suite actually writes must fail HERE --
    loudly, next to the measurement -- rather than as a mysterious rejection inside a
    differential harness that classifies every ValueError as 'rejected'."""
    assert MEASURED_SUITE_MAX_FANOUT == 124
    assert DEFAULT_MAX_CLOSURE_FANOUT >= 100 * MEASURED_SUITE_MAX_FANOUT, (
        f'default {DEFAULT_MAX_CLOSURE_FANOUT} leaves under 100x headroom over the '
        f'measured suite maximum {MEASURED_SUITE_MAX_FANOUT}')


def test_default_admits_a_region_far_larger_than_any_test_writes():
    """Positive control for the pin above: a 20x20 hub (440 closure rows, ~3.5x the
    measured suite maximum) goes through untouched on a default-configured index."""
    session, idx = _store()
    assert idx.max_closure_fanout == DEFAULT_MAX_CLOSURE_FANOUT
    _hub(idx, 20, 20)
    session.commit()
    edges_before = _counts(session)[0]
    idx.add_edge('p', 't', 's', 'p', 't', 'o')
    session.commit()
    assert _counts(session)[0] == edges_before + 441, '20*20 + 20 + 20 closure rows + the direct edge'
    session.close()
