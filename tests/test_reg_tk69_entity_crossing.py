"""TK69 -- admission parity on the I14 crossing middle: the set engine refuses the
cycle-closing write the graph index refuses, and still accepts what the graph accepts.

Property guarded
----------------
On a CROSSABLE shape ``(T, p)`` (bridged in AND out) the graph index mints the crossing
middle ``(T, x, p)`` -- with both bridges -- for every live ENTITY ``x`` of type ``T``
(``index_v4/wildcard.py::WildcardIndex._ensure_entity_middles``, invariant I14), because
``zanzibar_utils_v1.py::SchemaInfo.crossable_shapes`` fixes the wildcard-materialization
spec's existential as ENTITY-wise. The set engine's flow graph holds a node only once an
edge is incident on it (``setengine/engine.py::SetEngine._shape_node_ref``: "Added on the
first incident edge"), so before the TK69 fix it could not see a crossing through an
entity that no edge of that shape touches -- and it ACCEPTED a cycle-closing write that
the graph REFUSED.

``docs/specs/set-engine-spec.md`` sec 1 item 5 already decided this direction ("Reject
them here too, with equivalent errors, so the 4-way matrix compares identical stores. ...
A parity test asserts both backends accept/reject the same op sequences"), with the
mechanic prescribed in sec 6.2. This module is that parity test for the crossing.

THE THREE CASES ARE NOT INTERCHANGEABLE, and the third is the important one:

  F1    the audited case -- every backend must REFUSE the cycle-closing write.
  F2    the detonation -- a SECOND divergence family, still OPEN; see below.
  CTRL  the OVER-REJECT CONTROL -- with no entity of type ``T`` in the store the graph
        mints no middle and ACCEPTS the same write, so every backend must accept it.
        This is what goes red if the virtual crossing hop is ever made unconditional
        instead of gated on entity existence. A fix that buys parity by over-rejecting
        passes F1 and fails here, which is the only reason F1's green means anything.

Evidence, literal, 2026-09-16 (``formal/probes/tk69_admission_parity_2026-09-16.py``,
the tracked pre/post instrument)::

    PRE-FIX  (rc=1)
      F1    DIVERGES add ('viewer','doc','d1','member','group','g') -> graph=False set:py=True set:roaring=True
      F2    DIVERGES add ('...','user','u1','editor','folder','f1') -> graph=False set:py=True set:roaring=True
      CTRL  ok       (all three writes accepted by every backend)

    POST-FIX (rc=1, F2 only)
      F1    ok       add ('viewer','doc','d1','member','group','g') -> graph=False set:py=False set:roaring=False
      F2    DIVERGES add ('...','user','u1','editor','folder','f1') -> graph=False set:py=True set:roaring=True
      CTRL  ok       (unchanged -- no over-reject)

Sabotage, literal, 2026-09-16 (the fix is the crossing hop in
``SetEngine._flow_reaches``'s w_all branch)::

    S1  remove the crossing hop entirely    -> 1 failed, 3 passed
          FAILED ::test_family1_cycle_closing_write_refused_by_every_backend
    S2  keep the hop, drop the entity gate  -> 2 failed, 2 passed
          FAILED ::test_ctrl_no_entity_means_no_refusal[ops0-no folder entity ever exists]
          FAILED ::test_family2_detonation_is_still_open

S2 is the control on S1: a hop that reddened F1 only because it reddened everything would
pass S1 and fail S2. Read S2's second red -- it is not noise. An ungated hop makes the SET
ENGINE refuse the ordinary grant too, so the F2 pin below fires on its third assertion,
which exists exactly to catch the detonation being propagated instead of removed. The
narrower CTRL arm (``[B, C]``, no closing write) stays green under S2, which is why S2's
reds are attributable to the gate rather than to a broken traversal.

Both sabotages were run and their attribution read before this module was believed.

(!) F2 IS A KNOWN OPEN DIVERGENCE AND IS PINNED POSITIVELY BELOW, NOT XFAILED.
``test_family2_detonation_is_still_open`` asserts TODAY's divergent behaviour on purpose,
so that closing F2 turns it RED and forces a deliberate flip. It is NOT a statement that
the behaviour is correct -- it is the opposite, and the task row it cites carries the fix
direction. An xfail here would be a failure that passes, which is what this repo budgets
against (``formal/verify.sh``'s ``MAX_TESTS_XFAILED``).
"""
import pytest

from setengine.setops import ALL_SETOPS
from tests.test_matrix import GraphBackend, SetBackend

SCHEMA = """
type user
type group
  relations
    define member: [user, doc#viewer]
type folder
  relations
    define editor: [user]
    define parent: [folder, folder:*]
    define viewer: [user, group#member] or viewer from parent
type doc
  relations
    define parent: [folder, folder:*]
    define viewer: [user, group#member] or viewer from parent
"""

OBJ_WC = frozenset({('folder', 'viewer')})

A = ('...', 'user', 'u1', 'editor', 'folder', 'f1')      # ordinary grant; mints folder:f1
B = ('member', 'group', 'g', 'viewer', 'folder', '*')    # object-wildcard userset grant
C = ('...', 'folder', '*', 'parent', 'doc', 'd1')        # bare-star tupleset parent
D = ('viewer', 'doc', 'd1', 'member', 'group', 'g')      # closes the userset cycle


def _apply_all(ops):
    """Apply ``ops`` to all three backends; return [(op, graph_ok, {name: ok})]."""
    graph = GraphBackend(SCHEMA, OBJ_WC)
    sets = [SetBackend(SCHEMA, OBJ_WC, o) for o in ALL_SETOPS]
    out = []
    for raw in ops:
        g = graph.apply(raw, 'add')
        out.append((raw, g, {b.name: b.apply(raw, 'add') for b in sets}))
    return out


def _assert_unanimous(rows):
    for raw, g, ss in rows:
        assert all(s == g for s in ss.values()), (
            f'admission parity broken on {raw}: graph={g} '
            + ' '.join(f'{n}={s}' for n, s in ss.items()))
    return rows


def test_family1_cycle_closing_write_refused_by_every_backend():
    """F1: the audited TK69 case -- every backend refuses the write that closes the
    userset cycle, and every earlier write is accepted by every backend."""
    rows = _assert_unanimous(_apply_all([A, B, C, D]))
    *earlier, (raw, g, ss) = rows
    assert raw == D
    assert g is False and set(ss.values()) == {False}, (
        f'the cycle-closing write must be refused by all three backends; got '
        f'graph={g} {ss}')
    for e_raw, e_g, e_ss in earlier:
        assert e_g is True and set(e_ss.values()) == {True}, (
            f'{e_raw} must still be ACCEPTED -- refusing it is an over-reject')


@pytest.mark.parametrize('ops,label', [
    ([B, C, D], 'no folder entity ever exists'),
    ([B, C], 'no folder entity and no closing write'),
])
def test_ctrl_no_entity_means_no_refusal(ops, label):
    """CTRL, the OVER-REJECT CONTROL. With no entity of type ``folder`` in the store the
    graph mints no crossing middle and accepts every one of these writes, so the set
    engine must too. Red here means the virtual crossing hop lost its entity gate and is
    buying F1's parity by refusing writes the graph allows."""
    for raw, g, ss in _assert_unanimous(_apply_all(ops)):
        assert g is True and set(ss.values()) == {True}, (
            f'[{label}] {raw} must be accepted by every backend; got graph={g} {ss}')


def test_family2_detonation_is_still_open():
    """F2 -- a SECOND divergence family, OPEN, pinned at today's behaviour ON PURPOSE.

    Same four writes, order B,C,D,A. With no ``folder`` entity yet the graph ACCEPTS the
    cycle-closing write D, then REFUSES the ordinary grant A (``user:u1 editor
    folder:f1``) -- a write naming no wildcard, no userset and not the crossable relation
    -- because minting that entity's I14 middle emits the bridge edge that closes the
    now-latent cycle.

    That is the failure ``WildcardIndex._reject_star_self_edge`` was written to prevent;
    its docstring calls it "the detonation: the graph locks itself out of a grant the set
    engine and the oracle both allow", and it refuses the offending write EARLY for the
    same-shape ``w_any -> w_all`` routed edge it does cover. F2 is a hole in that early
    rejection, so its fix belongs on the GRAPH side -- refuse D -- and NOT by teaching the
    set engine to detonate too, which would make both backends lock themselves out of a
    grant the oracle allows.

    When F2 is closed this test goes RED. That is intended: flip it to assert unanimity
    then, and delete this docstring's "open" framing."""
    rows = _apply_all([B, C, D, A])
    *earlier, (raw, g, ss) = rows
    assert raw == A
    for e_raw, e_g, e_ss in earlier:
        assert e_g is True and set(e_ss.values()) == {True}, (
            f'{e_raw} must be accepted by every backend')
    assert g is False, (
        'the graph is expected to REFUSE the ordinary grant here (the detonation); if it '
        'now accepts it, F2 was fixed graph-side -- flip this test to assert unanimity')
    assert set(ss.values()) == {True}, (
        'the set engine is expected to ACCEPT the ordinary grant (it has no entity-arrival '
        'rule); if it now refuses it, the detonation was propagated into the set engine '
        'instead of removed -- that is the outcome _reject_star_self_edge exists to avoid')
