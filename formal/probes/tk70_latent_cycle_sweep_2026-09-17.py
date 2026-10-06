"""TK70: the DETONATION -- an ordering sweep over the reg11 / ``owc_star_ttu`` class.

  Run:  PYTHONPATH=. <env-python> formal/probes/tk70_latent_cycle_sweep_2026-09-17.py

`TK70` is family F2 of `TK69` (`formal/probes/tk69_admission_parity_2026-09-16.py`): on a
CROSSABLE shape ``(T, p)`` the graph index ACCEPTS the write that closes a userset cycle
while no entity of type ``T`` exists yet -- the cycle is latent, not closed -- and then
REFUSES the next write that mints such an entity, even when that write names no wildcard,
no userset and not the crossable relation. That is the "detonation" named in
``src/zanzibar/graphindex/wildcard.py::WildcardIndex._reject_star_self_edge``'s own docstring.

THIS PROBE IS THE OVER-REJECT CONTROL, and it is deliberately wider than the four-write
case the `TK69` probe pins. The fix direction is graph-side -- refuse the latent write
EARLY -- and an early refusal is exactly the kind of change that buys parity by refusing
too much, on a schema class (reg11 / ``owc_star_ttu``) that is LEGAL and oracle-pinned and
whose every other write must keep working.

THE ACCEPTANCE PROPERTY IS A STORE INVARIANT, NOT A PER-WRITE PREDICATE, and the first
draft of this probe got that wrong in a way worth recording. It tried to say "an INNOCENT
write (no star endpoint, bare ``'...'`` subject predicate, non-crossable object relation)
must never be refused" -- and the pre-fix run reported 144 orderings refusing
``F = folder:f1 parent doc:d1`` UNANIMOUSLY, which reads like a second detonation family.
It is not. `F` is innocent only in its RAW form: the TTU rewrite routes it to
``folder:f1#viewer -> doc:d1#viewer``, whose subject IS a concrete of the crossable shape,
so with `D` already present `F` genuinely closes the loop and both backends correctly
refuse it. A syntactic innocence test cannot see a routed edge. What actually distinguishes
the defect is WHEN the refusal happens:

  LATENT   after every ACCEPTED write, in every ordering, the graph store must contain no
           path ``w_any(T,p) --> w_all(T,p)`` for any crossable shape ``(T, p)``. Such a
           path is a cycle BY CONSTRUCTION -- ``_ensure_entity_middles`` gives every
           present *and future* entity of type ``T`` the middle ``(T,x,p)`` with both
           bridges, so ``w_all -> (T,x,p) -> w_any`` closes it the moment any entity of
           type ``T`` exists. Admitting the path is precisely deferring the refusal onto
           whichever write happens to mint that entity. This invariant is the fix's
           acceptance signal, and it is measured with an INDEPENDENT instrument: a BFS
           over stored DIRECT edge rows (``::latent_paths``), not the materialized
           closure the fix itself queries.

  PARITY   every backend must make the same accept/reject call on every step of every
           ordering. Family F2 breaks this today.

The three arms:

  SWEEP       all 720 orderings of six writes on the class: PARITY + LATENT, plus a
              by-write census of the unanimous refusals (informational -- which write a
              given ordering refuses is legitimately order-dependent, exactly as any
              cycle rejection is; WHERE the refusal lands is what LATENT pins).
  OVERREJECT  all 120 orderings of the SAME six writes minus the cycle-closing `D`. Every
              write must be ACCEPTED by every backend in every ordering. This is the arm
              that goes red if the early refusal is stated too broadly -- e.g. on the
              SCHEMA, or on any write that merely touches the crossable shape.
  NARROW      the two-write prefix ``[B, C]`` and its reverse: always all-accepted. The
              narrow arm of the `TK69` CTRL case, kept so a fix that reddens everything
              cannot be mistaken for a fix that reddens the cycle only.

WHAT A GREEN MEANS, AND WHAT IT DOES NOT. Green says the two backends agree on all 4320 +
600 + 4 write decisions, no latent by-construction cycle is ever admitted, and no write of
the cycle-free corpus is refused. It does NOT say the accepted stores EVALUATE the same --
that is the validation matrix's job (`tests/test_matrix.py`). This probe touches no
evaluation path: ``SetEngine._flow_reaches`` is reached only from ``::_would_cycle``
(admission), verified by grep 2026-09-17.

(!) PRE-FIX THIS PROBE EXITS NONZERO. rc=0 is the acceptance signal for `TK70`.

-- TRANSCRIPTS (literal, 2026-09-17) ----------------------------------------------------

PRE-FIX, rc=1::

    == SWEEP -- all orderings of A,B,C,D,E,F ==
      SWEEP: 720 orderings, 4320 write decisions, 80 divergence(s), 824 unanimous refusal(s), 156 latent-cycle state(s)
        PARITY BROKEN:
          divergence on A = ('...', 'user', 'u1', 'editor', 'folder', 'f1')  in 40 ordering(s)
          divergence on E = ('...', 'user', 'u2', 'viewer', 'folder', 'f1')  in 40 ordering(s)
        LATENT CYCLE ADMITTED (w_any --> w_all present after an accepted write):
          latent state after on A(40) B(12) C(16) D(12) E(40) F(36) ordering(s)
        unanimous refusals, by write: B(288) C(104) D(288) F(144)
    == OVERREJECT -- the same class with the cycle-closing D removed ==
      OVERREJECT: 120 orderings, 600 write decisions, 0 divergence(s), 0 unanimous refusal(s), 0 latent-cycle state(s)
    == NARROW -- [B, C] both ways, always all-accepted ==
      NARROW: 2 orderings, 4 write decisions, 0 divergence(s), 0 unanimous refusal(s), 0 latent-cycle state(s)

    TK70 SWEEP FAILED:
        SWEEP parity: 80 divergent write decision(s)
        SWEEP latent: 156 store state(s) hold a by-construction cycle

POST-FIX, rc=0::

    == SWEEP -- all orderings of A,B,C,D,E,F ==
      SWEEP: 720 orderings, 4320 write decisions, 0 divergence(s), 840 unanimous refusal(s), 0 latent-cycle state(s)
        unanimous refusals, by write (informational -- order-dependent):
          refusal on B in 300 ordering(s); C in 120; D in 300; F in 120
    == OVERREJECT -- the same class with the cycle-closing D removed ==
      OVERREJECT: 120 orderings, 600 write decisions, 0 divergence(s), 0 unanimous refusal(s), 0 latent-cycle state(s)
    == NARROW -- [B, C] both ways, always all-accepted ==
      NARROW: 2 orderings, 4 write decisions, 0 divergence(s), 0 unanimous refusal(s), 0 latent-cycle state(s)

    TK70 SWEEP CLEAN: parity holds on every write decision, no latent by-construction
    cycle is ever admitted, and the cycle-free corpus is fully accepted.

⚠ READ THE REFUSAL CENSUS, NOT THE REFUSAL COUNT. 824 -> 840 looks like the gate widening
and is the opposite: pre-fix, A and E were refused by the GRAPH in 40 orderings each while
both set backends accepted them (those 80 are counted as divergences, not refusals), and
post-fix they are refused in ZERO. What grew is B/C/D -- the three writes that form the
path -- because the refusal now lands on whichever of them arrives last instead of being
deferred. `F` fell (144 -> 120) for the same reason: in some orderings `D` is now refused
first, so `F` no longer closes anything. And OVERREJECT is 0 before AND after, which is
the arm that says none of this movement reached a write outside the cycle.
"""
import itertools
import sys
from collections import deque

from sqlmodel import select

from zanzibar.graphindex.models import Edge, Node
from zanzibar.setengine.setops import ALL_SETOPS
from tests.test_matrix import GraphBackend, SetBackend

SCHEMA = '''
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
'''

OBJ_WC = frozenset({('folder', 'viewer')})

WRITES = {
    'A': ('...', 'user', 'u1', 'editor', 'folder', 'f1'),    # ordinary grant; mints folder:f1
    'B': ('member', 'group', 'g', 'viewer', 'folder', '*'),  # object-wildcard userset grant
    'C': ('...', 'folder', '*', 'parent', 'doc', 'd1'),      # bare-star tupleset parent
    'D': ('viewer', 'doc', 'd1', 'member', 'group', 'g'),    # closes the userset cycle
    'E': ('...', 'user', 'u2', 'viewer', 'folder', 'f1'),    # ordinary grant ON the crossable relation
    'F': ('...', 'folder', 'f1', 'parent', 'doc', 'd1'),     # concrete tupleset parent
}


def latent_paths(graph) -> list[tuple[str, str]]:
    """Crossable shapes whose ``w_any --> w_all`` path is present in the STORE.

    INDEPENDENT INSTRUMENT, deliberately: a breadth-first walk over the stored DIRECT
    edge rows, not ``ReachabilityIndex.check_reachable_by_id``. The fix under test
    queries the materialized closure, so sharing that query would make the probe agree
    with the fix by construction rather than by measurement.
    """
    widx = graph.widx
    idx = widx.idx
    crossable = sorted(widx.schema_info.crossable_shapes)
    if not crossable:
        return []
    nodes = {n.id: n for n in idx.session.exec(
        select(Node).where(Node.store_id == idx.store_id)).all()}
    adj: dict[int, list[int]] = {}
    for s, o in idx.session.exec(
            select(Edge.subject_id, Edge.object_id)
            .where(Edge.store_id == idx.store_id)
            .where(Edge.direct_edge_count > 0)).all():   # type: ignore[arg-type]
        adj.setdefault(s, []).append(o)
    by_shape = {}
    for n in nodes.values():
        if n.wildcard in ('any', 'all') and n.name == '*':
            by_shape[(n.type, n.predicate, n.wildcard)] = n.id
    hits = []
    for (t, p) in crossable:
        src = by_shape.get((t, p, 'any'))
        dst = by_shape.get((t, p, 'all'))
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


def run_ordering(keys):
    """Apply WRITES[k] for k in keys to all backends.

    Returns [(key, graph_ok, {backend: ok}, latent_shapes_after)].
    """
    graph = GraphBackend(SCHEMA, OBJ_WC)
    sets = [SetBackend(SCHEMA, OBJ_WC, o) for o in ALL_SETOPS]
    out = []
    try:
        for k in keys:
            raw = WRITES[k]
            g = graph.apply(raw, 'add')
            ss = {b.name: b.apply(raw, 'add') for b in sets}
            out.append((k, g, ss, latent_paths(graph)))
    finally:
        graph.close()
    return out


def sweep(keys_pool, label):
    """Run every ordering of ``keys_pool``; return (divergences, refusals, latents)."""
    divergences = []   # (ordering, step_index, key, graph, sets)
    refusals = []      # (ordering, step_index, key) -- refused UNANIMOUSLY
    latents = []       # (ordering, step_index, key, shapes)
    steps = 0
    orderings = list(itertools.permutations(sorted(keys_pool)))
    for perm in orderings:
        for i, (k, g, ss, lat) in enumerate(run_ordering(perm)):
            steps += 1
            if any(s != g for s in ss.values()):
                divergences.append((''.join(perm), i, k, g, dict(ss)))
            elif g is False:
                refusals.append((''.join(perm), i, k))
            if lat:
                latents.append((''.join(perm), i, k, lat))
    print(f'  {label}: {len(orderings)} orderings, {steps} write decisions, '
          f'{len(divergences)} divergence(s), {len(refusals)} unanimous refusal(s), '
          f'{len(latents)} latent-cycle state(s)')
    return divergences, refusals, latents


def summarise(rows, what, limit=6):
    by_key = {}
    for row in rows:
        by_key.setdefault(row[2], []).append(row[0])
    for k in sorted(by_key):
        orders = by_key[k]
        print(f'      {what} on {k} = {WRITES[k]}  in {len(orders)} ordering(s): '
              + ', '.join(orders[:limit]) + (' ...' if len(orders) > limit else ''))


def main() -> int:
    probe = GraphBackend(SCHEMA, OBJ_WC)
    print(f'crossable shape(s): {sorted(probe.widx.schema_info.crossable_shapes)}')
    probe.close()
    print()

    bad = []

    print('== SWEEP -- all orderings of A,B,C,D,E,F ==')
    div, ref, lat = sweep('ABCDEF', 'SWEEP')
    if div:
        print('    PARITY BROKEN:')
        summarise(div, 'divergence')
        bad.append(f'SWEEP parity: {len(div)} divergent write decision(s)')
    if lat:
        print('    LATENT CYCLE ADMITTED (w_any --> w_all present after an accepted write):')
        summarise(lat, 'latent state after')
        bad.append(f'SWEEP latent: {len(lat)} store state(s) hold a by-construction cycle')
    if ref:
        print('    unanimous refusals, by write (informational -- order-dependent):')
        summarise(ref, 'refusal')
    print()

    print('== OVERREJECT -- the same class with the cycle-closing D removed ==')
    div2, ref2, lat2 = sweep('ABCEF', 'OVERREJECT')
    if div2:
        print('    PARITY BROKEN:')
        summarise(div2, 'divergence')
        bad.append(f'OVERREJECT parity: {len(div2)} divergent write decision(s)')
    if ref2:
        print('    OVER-REJECT (a write of the legal class was refused):')
        summarise(ref2, 'refusal')
        bad.append(f'OVERREJECT: {len(ref2)} refused write(s) on a cycle-free corpus')
    if lat2:
        print('    LATENT CYCLE ADMITTED on the cycle-free corpus:')
        summarise(lat2, 'latent state after')
        bad.append(f'OVERREJECT latent: {len(lat2)} state(s)')
    print()

    print('== NARROW -- [B, C] both ways, always all-accepted ==')
    div3, ref3, lat3 = sweep('BC', 'NARROW')
    if div3 or ref3 or lat3:
        print('    NARROW arm is not clean')
        bad.append('NARROW: the two-write prefix is no longer unanimously accepted')
    print()

    if bad:
        print('TK70 SWEEP FAILED:')
        for b in bad:
            print(f'    {b}')
        return 1
    print('TK70 SWEEP CLEAN: parity holds on every write decision, no latent '
          'by-construction cycle is ever admitted, and the cycle-free corpus is '
          'fully accepted.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
