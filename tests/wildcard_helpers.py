"""
Test helpers for the wildcard façade: an invariant checker (spec §8.3) and a
row-multiset snapshot for the GC parity test (§7.3 / §8.2).
"""

from collections import Counter

from sqlmodel import Session, create_engine, SQLModel, select

from index_v4 import ReachabilityIndex, Store, WildcardIndex, NodeV4, EdgeV4
from zanzibar_utils_v1 import SchemaInfo


def make_wildcard_index(schema_info: SchemaInfo, store_id: str = 'test') -> tuple[Session, WildcardIndex]:
    """Fresh in-memory store + WildcardIndex."""
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Store(id=store_id))
    session.commit()
    idx = ReachabilityIndex(session, store_id=store_id)
    return session, WildcardIndex(idx, schema_info)


# ---------------------------------------------------------------------------
# Invariant checker (§8.3)
# ---------------------------------------------------------------------------

# Allowed (subject.wildcard, object.wildcard) combinations for a DIRECT edge (§1.4).
#   ('', '')      ordinary edge
#   ('', 'any')   bridge concrete -> w_any        (same shape required)
#   ('all', '')   bridge w_all -> concrete        (same shape required)
#   ('any', '')   grant w_any -> concrete         (wildcard-subject tuple)
#   ('', 'all')   grant concrete -> w_all         (wildcard-object tuple)
#   ('any', 'all') grant w_any -> w_all           (both-wildcard tuple)
_ALLOWED_DIRECT = {('', ''), ('', 'any'), ('all', ''), ('any', ''), ('', 'all'), ('any', 'all')}


def assert_wildcard_invariants(widx: WildcardIndex) -> None:
    idx = widx.idx
    info = widx.schema_info
    session, store_id = idx.session, idx.store_id

    nodes = list(session.exec(select(NodeV4).where(NodeV4.store_id == store_id)).all())
    by_id = {n.id: n for n in nodes}
    edges = list(session.exec(select(EdgeV4).where(EdgeV4.store_id == store_id)).all())

    # (1) node encoding: (name=='*') iff wildcard!='' ; wildcard is one of the enum values
    for n in nodes:
        assert n.wildcard in ('', 'any', 'all'), f'bad wildcard value {n.wildcard!r} on {n}'
        assert (n.name == '*') == (n.wildcard != ''), f'name/wildcard mismatch on {n}'

    # (2) core invariants + direct-edge classification
    direct_edges = []
    for e in edges:
        assert e.indirect_edge_count >= e.direct_edge_count, f'indirect < direct on edge {e}'
        assert e.indirect_edge_count > 0, f'stale zero-indirect edge {e}'
        assert e.direct_edge_count >= 0
        if e.direct_edge_count > 0:
            direct_edges.append(e)

    for e in direct_edges:
        s, o = by_id[e.subject_id], by_id[e.object_id]
        combo = (s.wildcard, o.wildcard)
        assert combo in _ALLOWED_DIRECT, f'forbidden direct edge variant {combo}: {s} -> {o}'
        # bridge into w_any: same-shape concrete subject
        if o.wildcard == 'any':
            assert s.wildcard == '' and (s.type, s.predicate) == (o.type, o.predicate), \
                f'w_any in-edge not a same-shape concrete bridge: {s} -> {o}'
        # bridge out of w_all: same-shape concrete object
        if s.wildcard == 'all':
            assert o.wildcard == '' and (o.type, o.predicate) == (s.type, s.predicate), \
                f'w_all out-edge not a same-shape concrete bridge: {s} -> {o}'

    # (3) bridge completeness: every concrete of a bridged shape has exactly its
    #     configured bridges; no concrete outside a bridged shape has any bridge.
    #     Built from in-memory maps (no per-node DB round-trips).
    node_by_variant = {(n.type, n.predicate, n.wildcard): n for n in nodes}
    direct_edge_set = {(e.subject_id, e.object_id) for e in direct_edges}

    for n in nodes:
        if n.wildcard != '':
            continue
        shape = (n.type, n.predicate)
        w_any = node_by_variant.get((n.type, n.predicate, 'any'))
        w_all = node_by_variant.get((n.type, n.predicate, 'all'))
        has_in = w_any is not None and (n.id, w_any.id) in direct_edge_set
        has_out = w_all is not None and (w_all.id, n.id) in direct_edge_set
        if shape in info.bridged_in_shapes:
            assert has_in, f'concrete {n} of bridged-in shape missing its concrete->w_any bridge'
        else:
            assert not has_in, f'concrete {n} of non-bridged-in shape has a concrete->w_any bridge'
        if shape in info.bridged_out_shapes:
            assert has_out, f'concrete {n} of bridged-out shape missing its w_all->concrete bridge'
        else:
            assert not has_out, f'concrete {n} of non-bridged-out shape has a w_all->concrete bridge'


# ---------------------------------------------------------------------------
# Row-multiset snapshot for GC parity (§8.2 test_bridge_gc_restores_clean_state)
# ---------------------------------------------------------------------------

def snapshot(widx: WildcardIndex) -> tuple[Counter, Counter]:
    """Return (node_rows, edge_rows) as id-independent multisets, so two stores that
    reach the same logical state compare equal."""
    session, store_id = widx.idx.session, widx.idx.store_id
    nodes = list(session.exec(select(NodeV4).where(NodeV4.store_id == store_id)).all())
    by_id = {n.id: (n.predicate, n.type, n.name, n.wildcard) for n in nodes}

    node_rows = Counter(
        (n.predicate, n.type, n.name, n.wildcard, n.implicit, n.reference_count) for n in nodes
    )
    edges = list(session.exec(select(EdgeV4).where(EdgeV4.store_id == store_id)).all())
    edge_rows = Counter(
        (by_id[e.subject_id], by_id[e.object_id], e.direct_edge_count, e.indirect_edge_count)
        for e in edges
    )
    return node_rows, edge_rows
