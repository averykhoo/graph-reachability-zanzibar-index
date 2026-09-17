"""TK69 + TK70 -- admission parity on the I14 crossing middle: both backends refuse the
write that FORMS a by-construction cycle, neither refuses anything else, and no latent
cycle is ever admitted for a later write to detonate on.

Property guarded
----------------
On a CROSSABLE shape ``(T, p)`` (bridged in AND out) the graph index mints the crossing
middle ``(T, x, p)`` -- with both bridges -- for every live ENTITY ``x`` of type ``T``
(``index_v4/wildcard.py::WildcardIndex._ensure_entity_middles``, invariant I14), because
``zanzibar_utils_v1.py::SchemaInfo.crossable_shapes`` fixes the wildcard-materialization
spec's existential as ENTITY-wise. Those bridges are SCHEMATIC, not data: every present
**and future** entity of type ``T`` gets them. So

  **L.** a path ``w_any(T,p) --> w_all(T,p)`` is a cycle by construction, whatever its
  length, and no write may create one.

``WildcardIndex::_reject_star_self_edge`` has stated L at length 1 since 2026-07-26.
``WildcardIndex::_reject_latent_star_cycle`` states it at length n (`TK70`, 2026-09-17),
and ``SetEngine._flow_reaches`` states the same rule from the other side by stepping
``w_all -> w_any`` for free on a crossable shape, so ``::_would_cycle`` refuses the same
write. ``docs/specs/set-engine-spec.md`` sec 1 item 5 already decided that direction
("Reject them here too, with equivalent errors, so the 4-way matrix compares identical
stores. ... A parity test asserts both backends accept/reject the same op sequences");
this module is that parity test for the crossing.

The two families this module was built from
-------------------------------------------
  F1  order A,B,C,D -- an entity of type ``folder`` already exists, so the graph saw the
      cycle and refused D while the set engine's flow graph could not see the crossing
      (its nodes exist per incident EDGE, ``SetEngine::_shape_node_ref``) and accepted it.
      CLOSED 2026-09-16 by the crossing hop in ``_flow_reaches``.
  F2  order B,C,D,A -- the DETONATION. No ``folder`` entity exists yet, so the graph
      accepted D with the cycle merely LATENT, and then permanently refused A =
      ``user:u1 editor folder:f1``: a write naming no wildcard, no userset and not the
      crossable relation. Through ``ConnectedStore`` that write is admission-validated by
      the set engine, lands in the permanent log, and wedges ``catch_up`` forever.
      CLOSED 2026-09-17 (`TK70`) graph-side, by refusing the latent write itself.

(!) F2's fix is NOT "teach the set engine to detonate too". That would make both backends
lock themselves out of a grant the ORACLE allows -- an admission divergence traded for an
oracle divergence, which is the outcome ``_reject_star_self_edge`` exists to avoid. The
refusal had to MOVE onto the cycle-forming write, not spread.

Evidence, literal (``formal/probes/tk70_latent_cycle_sweep_2026-09-17.py``, all 720
orderings of six writes on this schema, against the graph index and both ``SetOps``)::

    PRE-FIX  rc=1
      SWEEP: 720 orderings, 4320 write decisions, 80 divergence(s),
             824 unanimous refusal(s), 156 latent-cycle state(s)
        divergence on A in 40 ordering(s); divergence on E in 40 ordering(s)
      OVERREJECT: 120 orderings, 600 write decisions, 0 / 0 / 0
    POST-FIX rc=0
      SWEEP: 720 orderings, 4320 write decisions, 0 divergence(s),
             840 unanimous refusal(s), 0 latent-cycle state(s)
        unanimous refusals: B(300) C(120) D(300) F(120) -- A and E never
      OVERREJECT: 120 orderings, 600 write decisions, 0 / 0 / 0

Read the OVERREJECT arm: the cycle-free corpus is fully accepted before AND after, so the
16 extra refusals are the cycle moving earlier, not the gate widening. Read the refusal
census: the ordinary grants A and E are refused in ZERO orderings post-fix, and the
refusal now lands on whichever of B/C/D completes the path -- order-dependent, exactly as
any cycle rejection is, but never on a write outside the cycle.

Sabotage, literal, 2026-09-16 (the F1 fix, the crossing hop in ``_flow_reaches``)::

    S1  remove the crossing hop entirely    -> 1 failed, 3 passed
    S2  keep the hop, drop the entity gate  -> 2 failed, 2 passed

(!) S2 IS NO LONGER A SABOTAGE -- it is the shipped behaviour. The entity gate was
correct only while the graph detonated; `TK70` removed that premise and the gate with it.
The 2026-09-17 sweep table below is this module's own evidence, and it is what the reader
should use; S1/S2 are kept because they are the historical reason the hop exists at all.

Mutation sweep, literal, 2026-09-17 (baseline ``32 passed``; one weakening at a time, whole
module re-run, restored from memory in a ``finally``). Test names abbreviated to their
suffix; every row is the sweep's own attribution, not a prediction::

    M0  CONTROL: flip test_family1's own expectation to accept      RED  1 failed
          ::test_family1_cycle_closing_write_refused_by_every_backend
    M1  delete the _reject_latent_star_cycle call                   RED  8 failed
          ::test_family2_detonation_closed ::test_no_latent_star_cycle_is_ever_admitted
          ::test_ordinary_grant_accepted_in_every_ordering
    M2  subject side narrowed to identity (length 1 on the left)    RED  6 failed
          ::test_family2_detonation_closed ::test_no_latent_star_cycle_is_ever_admitted
          ::test_ordinary_grant_accepted_in_every_ordering
    M3  object side narrowed to identity (length 1 on the right)    RED  6 failed
          ::test_family2_detonation_closed ::test_no_latent_star_cycle_is_ever_admitted
          ::test_ordinary_grant_accepted_in_every_ordering
    M4  restore the entity gate on the set engine's crossing hop    RED  2 failed
          ::test_family2_detonation_closed
          ::test_ordinary_grant_accepted_in_every_ordering
    M5  drop the `obj reaches w_all` half of the rule               RED  8 failed
          ::test_ctrl_cycle_free_corpus_fully_accepted
          ::test_family1_cycle_closing_write_refused_by_every_backend
          ::test_family2_detonation_closed
          ::test_ordinary_grant_accepted_in_every_ordering
    M6  widen the shape set from crossable to bridged_in_shapes     INERT

Three readings, and none of them is "all green, ship it":

* **M0 named its own pin**, so the attribution is working and the other six rows can be
  read at all. A sweep whose control does not fire is void, however clean it looks
  (docs/sabotage-procedure.md, "A sweep needs an M0").
* **M4 is the parity half, and only it.** Restoring the entity gate leaves the GRAPH
  refusing D correctly -- so ``::test_no_latent_star_cycle_is_ever_admitted`` stays green
  -- while the set engine goes back to accepting it. Only the arms that compare backends
  fire. That is the shape of a divergence, and it is why this module asserts unanimity
  separately from the store invariant rather than folding them together.
* **M5 is the only mutation that reddens the over-reject control**, and it is the whole
  reason that arm exists: a rule that refuses everything downstream of ``w_any`` still
  refuses D (so the F1/F2 arms alone cannot tell it from the correct rule) while also
  refusing writes of the legal reg11 class. ⚠ It reddens the F1 arm too, which is
  *itself* an over-reject -- F1's earlier writes are asserted accepted.
* **M6 is INERT for a stated reason, not for lack of coverage.** On this schema
  ``bridged_in_shapes == bridged_out_shapes == crossable_shapes == {('folder','viewer')}``
  (dumped first-hand 2026-09-17), so substituting one for another cannot move anything
  the module can observe. The edit did not fail to be caught; it did not happen. The
  bridged-in/bridged-out minimality it was aimed at is guarded by
  ``_reject_star_self_edge``'s own clause and by the wider matrix. Recorded rather than
  dropped so nobody reads its green as coverage.
"""
import itertools
from collections import deque

import pytest
from sqlmodel import select

from index_v4.models import EdgeV4, NodeV4
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
E = ('...', 'user', 'u2', 'viewer', 'folder', 'f1')      # ordinary grant ON the crossable relation


def _latent_star_cycle(graph) -> list[tuple[str, str]]:
    """Crossable shapes whose ``w_any --> w_all`` path is present in the STORE.

    INDEPENDENT INSTRUMENT, deliberately: a breadth-first walk over the stored DIRECT
    edge rows, NOT ``ReachabilityIndex.check_reachable_by_id``. The fix under test queries
    the materialized closure, so sharing that query would make this agree with the fix by
    construction instead of by measurement. Mirrors
    ``formal/probes/tk70_latent_cycle_sweep_2026-09-17.py::latent_paths``.
    """
    idx = graph.widx.idx
    crossable = sorted(graph.widx.schema_info.crossable_shapes)
    if not crossable:
        return []
    adj: dict[int, list[int]] = {}
    for s, o in idx.session.exec(
            select(EdgeV4.subject_id, EdgeV4.object_id)
            .where(EdgeV4.store_id == idx.store_id)
            .where(EdgeV4.direct_edge_count > 0)).all():   # type: ignore[arg-type]
        adj.setdefault(s, []).append(o)
    w_nodes = {(n.type, n.predicate, n.wildcard): n.id for n in idx.session.exec(
        select(NodeV4).where(NodeV4.store_id == idx.store_id)
        .where(NodeV4.name == '*')).all() if n.wildcard in ('any', 'all')}
    hits = []
    for (t, p) in crossable:
        src, dst = w_nodes.get((t, p, 'any')), w_nodes.get((t, p, 'all'))
        if src is None or dst is None:
            continue
        seen, q = {src}, deque([src])
        while q:
            cur = q.popleft()
            if cur == dst:
                hits.append((t, p))
                break
            for nxt in adj.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
    return hits


def _apply_all(ops, *, watch_latent=False):
    """Apply ``ops`` to all three backends; return [(op, graph_ok, {name: ok}, latent)]."""
    graph = GraphBackend(SCHEMA, OBJ_WC)
    sets = [SetBackend(SCHEMA, OBJ_WC, o) for o in ALL_SETOPS]
    out = []
    try:
        for raw in ops:
            g = graph.apply(raw, 'add')
            ss = {b.name: b.apply(raw, 'add') for b in sets}
            out.append((raw, g, ss, _latent_star_cycle(graph) if watch_latent else []))
    finally:
        graph.close()
    return out


def _assert_unanimous(rows):
    for raw, g, ss, _lat in rows:
        assert all(s == g for s in ss.values()), (
            f'admission parity broken on {raw}: graph={g} '
            + ' '.join(f'{n}={s}' for n, s in ss.items()))
    return rows


def test_family1_cycle_closing_write_refused_by_every_backend():
    """F1: the audited TK69 case -- every backend refuses the write that closes the
    userset cycle, and every earlier write is accepted by every backend."""
    rows = _assert_unanimous(_apply_all([A, B, C, D]))
    *earlier, (raw, g, ss, _lat) = rows
    assert raw == D
    assert g is False and set(ss.values()) == {False}, (
        f'the cycle-closing write must be refused by all three backends; got '
        f'graph={g} {ss}')
    for e_raw, e_g, e_ss, _e_lat in earlier:
        assert e_g is True and set(e_ss.values()) == {True}, (
            f'{e_raw} must still be ACCEPTED -- refusing it is an over-reject')


def test_family2_detonation_closed():
    """F2, CLOSED (`TK70`, 2026-09-17). Same four writes, order B,C,D,A.

    D now completes the path ``w_any(folder,viewer) --> w_all(folder,viewer)`` -- a cycle
    by construction, because the I14 middle of every present-or-future ``folder`` entity
    joins ``w_all`` back to ``w_any`` -- so every backend refuses D, with no ``folder``
    entity in the store and none needed. The ordinary grant A that follows is then
    ACCEPTED by every backend.

    This test asserted the OPPOSITE until 2026-09-17: it pinned the divergence positively
    (never an xfail) so that closing F2 would turn it red and force a deliberate flip.
    This is that flip. What must not happen is the third assertion below failing in the
    other direction -- the set engine refusing A -- which would mean the detonation was
    propagated into the set engine rather than removed."""
    rows = _assert_unanimous(_apply_all([B, C, D, A]))
    by_raw = {raw: (g, ss) for raw, g, ss, _lat in rows}

    g_d, ss_d = by_raw[D]
    assert g_d is False and set(ss_d.values()) == {False}, (
        f'D forms the latent by-construction cycle and must be refused by every backend '
        f'even with no folder entity present; got graph={g_d} {ss_d}')

    g_a, ss_a = by_raw[A]
    assert g_a is True, (
        'the ordinary grant user:u1 editor folder:f1 must be ACCEPTED by the graph -- a '
        'refusal here is the TK70 detonation, the graph locking itself out of a write '
        'that names no wildcard, no userset and not the crossable relation')
    assert set(ss_a.values()) == {True}, (
        'the ordinary grant must be accepted by the set engine too; a refusal here means '
        'the detonation was PROPAGATED into the set engine instead of removed, which is '
        'the outcome _reject_star_self_edge exists to avoid')

    for raw in (B, C):
        g, ss = by_raw[raw]
        assert g is True and set(ss.values()) == {True}, (
            f'{raw} precedes the cycle and must still be accepted by every backend')


@pytest.mark.parametrize('ops,label', [
    ([B, C], 'the two-write prefix, no cycle-forming write'),
    ([A, B, C], 'plus an ordinary grant on a non-crossable relation'),
    ([A, B, C, E], 'plus an ordinary grant ON the crossable relation'),
    ([E, C, B, A], 'the same corpus, reversed'),
    ([B, A, E, C], 'the same corpus, wildcard writes interleaved'),
])
def test_ctrl_cycle_free_corpus_fully_accepted(ops, label):
    """THE OVER-REJECT CONTROL, and the arm that makes every green above mean something.

    reg11 / ``owc_star_ttu`` is a LEGAL, oracle-pinned schema class
    (docs/spec-deviations.md 2026-07-26) whose every non-cycle-forming write must keep
    working. None of these corpora contains D, so none of them completes a
    ``w_any --> w_all`` path, and every write must be ACCEPTED by every backend whatever
    the order -- including E, an ordinary grant on the crossable relation itself.

    Red here means the early refusal is stated too broadly: it is refusing writes on the
    strength of touching the crossable shape rather than of completing the path. This is
    the ONLY arm the 2026-09-17 mutation sweep's M5 (drop the ``obj reaches w_all`` half
    of the rule) reddens that the F1/F2 arms do not -- M5 still refuses D, so without this
    arm a rule that refuses everything downstream of ``w_any`` looks exactly like the
    correct one."""
    for raw, g, ss, _lat in _assert_unanimous(_apply_all(ops)):
        assert g is True and set(ss.values()) == {True}, (
            f'[{label}] {raw} must be accepted by every backend; got graph={g} {ss}')


@pytest.mark.parametrize('ops', [
    list(perm) for perm in itertools.permutations([A, B, C, D])
], ids=lambda ops: ''.join('ABCD'[[A, B, C, D].index(o)] for o in ops))
def test_no_latent_star_cycle_is_ever_admitted(ops):
    """INVARIANT L, over every ordering of the four writes: after each ACCEPTED write the
    store holds no path ``w_any(T,p) --> w_all(T,p)`` for any crossable shape.

    This is the property, stated where it belongs -- on the store rather than on any one
    write. Which write a given ordering refuses is legitimately order-dependent (the last
    arrival of the three that form the path), so a per-write expectation either encodes
    one ordering or says nothing. What must hold in all 24 is that the cycle is never
    merely LATENT: a latent cycle is a refusal deferred onto whichever innocent write
    later mints an entity of the crossable type, which is exactly what `TK70` was.

    Measured with an independent instrument (``_latent_star_cycle`` walks stored direct
    edge rows; the fix queries the materialized closure)."""
    for raw, _g, _ss, latent in _apply_all(ops, watch_latent=True):
        assert latent == [], (
            f'a by-construction cycle was admitted as LATENT after {raw}: shape(s) '
            f'{latent} now have a w_any --> w_all path, so the next write that mints an '
            f'entity of that type will be refused instead (TK70, the detonation)')


def test_ordinary_grant_accepted_in_every_ordering():
    """The user-visible form of invariant L: an ordinary grant is never the victim.

    ``A = user:u1 editor folder:f1`` names no wildcard, no userset and not the crossable
    relation. Across all 24 orderings of the four writes it must be accepted by every
    backend, every time -- including the orderings where the cycle-forming writes all
    precede it. Pre-fix the graph refused it in 40 of the sweep's 720 orderings while
    both set backends accepted it."""
    refused = []
    for ops in itertools.permutations([A, B, C, D]):
        for raw, g, ss, _lat in _assert_unanimous(_apply_all(list(ops))):
            if raw == A and not (g and set(ss.values()) == {True}):
                refused.append((''.join('ABCD'[[A, B, C, D].index(o)] for o in ops),
                                g, dict(ss)))
    assert refused == [], (
        f'the ordinary grant was refused in {len(refused)} ordering(s): {refused[:4]}')
