"""P13 -- the bulk closure builder for ``build_index`` (design: docs/p13-bulk-build-design.md).

Constructs the graph index's final pre-backfill state DIRECTLY -- one in-memory pass
over the tuple snapshot plus bulk writes -- instead of replaying every routed triple
through the incremental ``WildcardIndex.add_tuple`` machinery (which pays an
O(ancestors x descendants) closure-region update per triple).

**Correctness bar (design):** the state this builds is byte-IDENTICAL to what the
incremental add-only load produces, modulo auto-assigned row ids. It is pinned by the
differential identity gate in ``tests/test_bulk_build.py``; no new proof obligation
arises, since the incremental path (which stays the default online apply step) carries
the entire verification story and this is merely an alternative constructor of the same
modeled state (T4's closed-form path counts, computed directly).

Phases (design "Bulk algorithm"):
  R  route each ``TupleV1`` through ``RuleSet.apply``; apply the position rule of
     ``WildcardIndex._resolve`` to each derived triple to get natural-key endpoints;
     accumulate the direct-multigraph multiplicity ``m(s, o)`` (rewrite fan-in adds the
     same pair more than once -- deliberate multigraph semantics).
  B  bridge edges from the declared bridged shapes (concrete->w_any / w_all->concrete),
     multiplicity 1, existence-checked (mirrors ``_ensure_bridges``).
  C  topological sort of the direct graph; a cycle is a corruption signal.
  P  sparse integer DP in reverse topo order: ``P(a, b) = m(a, b) + sum_v m(a, v)*P(v, b)``
     -- the total weighted path count (== incremental ``indirect_edge_count``).
  W  bulk-INSERT nodes (implicit, reference_count = sum of incident direct multiplicities),
     edges (direct=m, indirect=P, derived=False), and one outbox ADDED row per final pair.

Everything a plain load leaves implicit/False is left implicit/False here; derived state
and residues are produced afterwards by the unchanged ``DeltaProcessor.backfill()``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from sqlalchemy import insert
from sqlmodel import Session, select

from setengine.models import TupleV1
from zanzibar_utils_v1 import Entity, RelationalTriple, RuleSet, norm_pred

from .invariants import InvariantViolation
from .models import DeltaOutboxV1, EdgeV4, NodeV4

if TYPE_CHECKING:
    from zanzibar_utils_v1 import SchemaInfo

# A node's natural key: (predicate, type, name, wildcard). Mirrors the identity
# ``ReachabilityIndex.node`` dedupes on, so it is id-independent by construction.
NodeKey = tuple[str, str, str, str]


def _subject_key(subject_predicate, s_type: str, s_name: str,
                 schema_info: 'SchemaInfo') -> NodeKey:
    """Position rule for a subject endpoint (``WildcardIndex._resolve`` subject branch).

    subject ``'*'`` -> ``w_any(type, predicate)`` and the shape must be a declared
    subject-wildcard shape; otherwise a concrete node. Predicate normalized via
    ``norm_pred`` (Ellipsis/None -> ``'...'``)."""
    pred = norm_pred(subject_predicate)
    if s_name == '*':
        shape = (s_type, pred)
        if shape not in schema_info.subject_wildcard_shapes:
            raise ValueError(
                f"subject wildcard {s_type}:* (predicate {pred!r}) is not a declared "
                f"subject-wildcard shape {shape}")
        return (pred, s_type, '*', 'any')
    return (pred, s_type, s_name, '')


def _object_key(relation: str, o_type: str, o_name: str,
                schema_info: 'SchemaInfo') -> NodeKey:
    """Position rule for an object endpoint (``WildcardIndex._resolve`` object branch).

    object ``'*'`` -> ``w_all(type, relation)`` and the shape must be a declared
    object-wildcard shape; otherwise a concrete node. The object node's *predicate* is
    the relation."""
    pred = norm_pred(relation)
    if o_name == '*':
        shape = (o_type, pred)
        if shape not in schema_info.object_wildcard_shapes:
            raise ValueError(
                f"object wildcard {o_type}:* (relation {pred!r}) is not a declared "
                f"object-wildcard shape {shape}")
        return (pred, o_type, '*', 'all')
    return (pred, o_type, o_name, '')


def _topo_order(nodes: set[NodeKey],
                succ: dict[NodeKey, list[tuple[NodeKey, int]]]) -> list[NodeKey]:
    """Kahn topological sort of the direct graph. A leftover (a cycle) is a corruption
    signal -- the tuple log is admission-validated acyclic, mirroring ``_apply_row``'s
    stance and the core's cycle assertions."""
    indeg: dict[NodeKey, int] = {n: 0 for n in nodes}
    for a in succ:
        for (b, _mult) in succ[a]:
            indeg[b] += 1
    # Deterministic order (sorted) so the build is reproducible run to run.
    queue = sorted(n for n in nodes if indeg[n] == 0)
    order: list[NodeKey] = []
    while queue:
        a = queue.pop()
        order.append(a)
        newly: list[NodeKey] = []
        for (b, _mult) in succ.get(a, ()):
            indeg[b] -= 1
            if indeg[b] == 0:
                newly.append(b)
        if newly:
            # keep the frontier sorted for a stable order
            queue.extend(newly)
            queue.sort()
    if len(order) != len(nodes):
        raise InvariantViolation(
            'bulk_build: the routed direct graph is cyclic -- the tuple log is '
            'admission-validated acyclic, so this is corruption')
    return order


def bulk_build(session: Session, source_store_id: str, index_store_id: str,
               ruleset: RuleSet, schema_info: 'SchemaInfo') -> None:
    """Build the graph index's pre-backfill state for ``index_store_id`` directly from
    the ``TupleV1`` snapshot of ``source_store_id``. Writes nodes/edges/outbox into the
    caller's (uncommitted) transaction; the caller runs ``backfill()`` and commits.

    Identical in effect to routing every snapshot tuple through
    ``WildcardIndex.add_tuple`` (the ``build_index(..., bulk=False)`` reference path),
    modulo row ids."""
    store_id = index_store_id

    # -- Phase R: route -> direct-multigraph multiplicities m(skey, okey). --------
    m: dict[tuple[NodeKey, NodeKey], int] = defaultdict(int)
    rows = session.exec(
        select(TupleV1).where(TupleV1.store_id == source_store_id)
        .order_by(TupleV1.id)  # type: ignore[arg-type]
    ).all()
    for r in rows:
        sp = Ellipsis if r.subject_predicate == '...' else r.subject_predicate
        triple = RelationalTriple(Entity(r.subject_type, r.subject_name), r.relation,
                                  Entity(r.object_type, r.object_name), sp)
        for d in ruleset.apply(triple):
            skey = _subject_key(d.subject_predicate, d.subject.type, d.subject.name,
                                schema_info)
            okey = _object_key(d.relation, d.object.type, d.object.name, schema_info)
            if skey == okey:
                # subject node IS object node: the trivial cycle. The core rejects this
                # (ValueError -> InvariantViolation on the admission-validated log path).
                raise InvariantViolation(
                    f'bulk_build: self-referential edge {skey} would create a cycle')
            m[(skey, okey)] += 1

    # -- Phase B: bridges (concrete->w_any, w_all->concrete), multiplicity 1. ------
    # Every concrete node that appears as a routed endpoint is bridged for its shape,
    # exactly as ``_ensure_bridges`` bridges the subject and object of every triple.
    # Bridge pairs provably never collide with routed pairs (a routed object is never
    # w_any; a routed subject is never w_all), so "add once" == the incremental
    # existence-checked ``add_edge_by_id``.
    concretes: set[NodeKey] = set()
    for (skey, okey) in m:
        if skey[3] == '':
            concretes.add(skey)
        if okey[3] == '':
            concretes.add(okey)
    for key in concretes:
        pred, typ, name, _wild = key
        shape = (typ, pred)
        if shape in schema_info.bridged_in_shapes:
            bridge = (key, (pred, typ, '*', 'any'))
            if bridge not in m:
                m[bridge] = 1
        if shape in schema_info.bridged_out_shapes:
            bridge = ((pred, typ, '*', 'all'), key)
            if bridge not in m:
                m[bridge] = 1

    # -- Node set + reference counts (sum of incident direct multiplicities). ------
    nodes: set[NodeKey] = set()
    ref_count: dict[NodeKey, int] = defaultdict(int)
    succ: dict[NodeKey, list[tuple[NodeKey, int]]] = defaultdict(list)
    for (a, b), mult in m.items():
        nodes.add(a)
        nodes.add(b)
        ref_count[a] += mult
        ref_count[b] += mult
        succ[a].append((b, mult))

    if not nodes:
        return   # empty snapshot: nothing to build (backfill will also find nothing)

    # -- Phase C: topological sort (cycle => InvariantViolation). ------------------
    order = _topo_order(nodes, succ)

    # -- Phase P: sparse integer path counts in reverse topo order. ----------------
    # P(a, b) = m(a, b) + sum_v m(a, v)*P(v, b). Processing sinks first means every
    # successor's vector is complete before its predecessor consumes it.
    pvec: dict[NodeKey, dict[NodeKey, int]] = {}
    for a in reversed(order):
        pa: dict[NodeKey, int] = defaultdict(int)
        for (v, mult) in succ.get(a, ()):
            pa[v] += mult                       # the direct edge a->v (length-1 path)
            for b, cnt in pvec[v].items():
                pa[b] += mult * cnt
        pvec[a] = pa

    # -- Phase W: bulk writes. -----------------------------------------------------
    # (1) nodes: implicit=True, reference_count computed above; ORM add + one flush so
    #     the auto-increment ids are available for the edge/outbox foreign keys.
    node_objs: dict[NodeKey, NodeV4] = {}
    for key in sorted(nodes):
        pred, typ, name, wild = key
        node_objs[key] = NodeV4(
            store_id=store_id, predicate=pred, type=typ, name=name, wildcard=wild,
            implicit=True, reference_count=ref_count[key])
    session.add_all(node_objs.values())
    session.flush()
    node_id = {key: n.id for key, n in node_objs.items()}

    # Final edge pairs, sorted by (subject_key, object_key) so edge and outbox writes
    # share one deterministic order (the outbox order is provably inert -- design
    # section 5 -- and the identity gate compares content as a multiset).
    edge_pairs = sorted(
        (a, b) for a in order for b in pvec[a] if pvec[a][b] > 0)

    # (2) edges: one executemany INSERT. direct=m (0 for pure-indirect pairs), indirect=P.
    edge_rows = [
        {
            'store_id': store_id,
            'subject_id': node_id[a],
            'object_id': node_id[b],
            'direct_edge_count': m.get((a, b), 0),
            'indirect_edge_count': pvec[a][b],
            'derived': False,
        }
        for (a, b) in edge_pairs
    ]
    if edge_rows:
        session.execute(insert(EdgeV4), edge_rows)

    # (3) outbox: one ADDED row per final pair, endpoint identities denormalized from
    #     the node keys (== what ``_emit`` captures from the live node rows). An add-only
    #     load flips each closure pair 0->positive exactly once, so exactly one ADDED per
    #     pair and no REMOVED (design section 5).
    outbox_rows = [
        {
            'store_id': store_id,
            'subject_node_id': node_id[a],
            'object_node_id': node_id[b],
            'action': 'ADDED',
            'subject_type': a[1],
            'subject_name': a[2],
            'subject_predicate': a[0],
            'object_type': b[1],
            'object_name': b[2],
            'object_predicate': b[0],
        }
        for (a, b) in edge_pairs
    ]
    if outbox_rows:
        session.execute(insert(DeltaOutboxV1), outbox_rows)
