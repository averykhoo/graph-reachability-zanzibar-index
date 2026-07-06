"""
Tests for v4-specific features that don't exist in v3:
- PermissionDelta return values from add_edge / remove_edge
- Multi-store isolation
- lookup_reachable / lookup_reverse
- remove_node
"""
import pytest
from sqlmodel import SQLModel, Session, create_engine


def _import_v4():
    """Lazy import to avoid SQLAlchemy table name collision with v3 at module-collection time."""
    import index_v4
    return index_v4


@pytest.fixture
def v4_env():
    """Provides a fresh in-memory v4 environment with a single store."""
    v4 = _import_v4()
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)

    session = Session(engine)
    store = v4.Store(id="test_store", description="unit test store")
    session.add(store)
    session.commit()

    idx = v4.ReachabilityIndex(session, store_id="test_store")
    yield engine, session, idx
    session.close()


# ---------------------------------------------------------------------------
# PermissionDelta tests -- deltas are outbox rows now (boolean spec §4); each op's
# flips are drained from the cursor watermark taken just before it.
# ---------------------------------------------------------------------------

def _drained(session, store_id, op):
    from index_v4.outbox import drain_deltas, outbox_watermark
    wm = outbox_watermark(session, store_id)
    op()
    session.commit()
    return drain_deltas(session, store_id, wm)


class TestPermissionDeltas:
    def test_add_edge_emits_added_delta(self, v4_env):
        engine, session, idx = v4_env
        deltas = _drained(session, "test_store",
                          lambda: idx.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1'))

        assert len(deltas) >= 1
        assert any(d.action == "ADDED" for d in deltas)

    def test_remove_edge_emits_removed_delta(self, v4_env):
        engine, session, idx = v4_env
        idx.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
        session.commit()

        deltas = _drained(session, "test_store",
                          lambda: idx.remove_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1'))

        assert len(deltas) >= 1
        assert any(d.action == "REMOVED" for d in deltas)

    def test_transitive_deltas(self, v4_env):
        """Adding B->C when A->B exists should produce a delta for A reaching C."""
        engine, session, idx = v4_env
        idx.add_edge(..., 'user', 'alice', 'member', 'group', 'g1')
        session.commit()

        deltas = _drained(session, "test_store",
                          lambda: idx.add_edge('member', 'group', 'g1', 'viewer', 'document', 'doc1'))

        # Should include the new transitive path: alice -> doc1
        added = [d for d in deltas if d.action == "ADDED"]
        assert len(added) >= 1

    def test_delta_store_id_matches(self, v4_env):
        engine, session, idx = v4_env
        deltas = _drained(session, "test_store",
                          lambda: idx.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1'))

        assert deltas
        for delta in deltas:
            assert delta.store_id == "test_store"

    def test_no_false_removed_delta_on_multi_edge(self, v4_env):
        """Removing one of two duplicate edges should NOT produce a REMOVED delta."""
        engine, session, idx = v4_env
        idx.add_edge(..., 'node', 'A', '...', 'node', 'B')
        session.commit()
        idx.add_edge(..., 'node', 'A', '...', 'node', 'B')
        session.commit()

        deltas = _drained(session, "test_store",
                          lambda: idx.remove_edge(..., 'node', 'A', '...', 'node', 'B'))

        # Edge still exists, so no REMOVED delta expected
        removed = [d for d in deltas if d.action == "REMOVED"]
        assert len(removed) == 0
        assert idx.check_reachable(..., 'node', 'A', '...', 'node', 'B') is True


# ---------------------------------------------------------------------------
# Multi-store isolation tests
# ---------------------------------------------------------------------------

class TestMultiStoreIsolation:
    @pytest.fixture
    def two_stores(self):
        """Provides two independent stores in the same database."""
        v4 = _import_v4()
        engine = create_engine('sqlite:///:memory:')
        SQLModel.metadata.create_all(engine)

        session = Session(engine)
        session.add(v4.Store(id="store_a", description="Store A"))
        session.add(v4.Store(id="store_b", description="Store B"))
        session.commit()

        idx_a = v4.ReachabilityIndex(session, store_id="store_a")
        idx_b = v4.ReachabilityIndex(session, store_id="store_b")
        yield session, idx_a, idx_b
        session.close()

    def test_edges_are_isolated(self, two_stores):
        session, idx_a, idx_b = two_stores

        idx_a.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
        session.commit()

        assert idx_a.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is True
        assert idx_b.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is False

    def test_same_entities_different_stores(self, two_stores):
        session, idx_a, idx_b = two_stores

        idx_a.add_edge(..., 'user', 'alice', 'writer', 'document', 'doc1')
        session.commit()
        idx_b.add_edge(..., 'user', 'alice', 'reader', 'document', 'doc1')
        session.commit()

        # store_a: alice is writer, not reader
        assert idx_a.check_reachable(..., 'user', 'alice', 'writer', 'document', 'doc1') is True
        assert idx_a.check_reachable(..., 'user', 'alice', 'reader', 'document', 'doc1') is False

        # store_b: alice is reader, not writer
        assert idx_b.check_reachable(..., 'user', 'alice', 'reader', 'document', 'doc1') is True
        assert idx_b.check_reachable(..., 'user', 'alice', 'writer', 'document', 'doc1') is False

    def test_remove_in_one_store_doesnt_affect_other(self, two_stores):
        session, idx_a, idx_b = two_stores

        idx_a.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
        session.commit()
        idx_b.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
        session.commit()

        idx_a.remove_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
        session.commit()

        assert idx_a.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is False
        assert idx_b.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is True

    def test_transitive_isolation(self, two_stores):
        """Transitive edges in store A don't leak to store B."""
        session, idx_a, idx_b = two_stores

        idx_a.add_edge(..., 'user', 'alice', 'member', 'group', 'g1')
        session.commit()
        idx_a.add_edge('member', 'group', 'g1', 'viewer', 'document', 'doc1')
        session.commit()

        assert idx_a.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is True
        assert idx_b.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is False


# ---------------------------------------------------------------------------
# lookup_reachable / lookup_reverse tests
# ---------------------------------------------------------------------------

class TestLookupMethods:
    def test_lookup_reachable_basic(self, v4_env):
        engine, session, idx = v4_env
        idx.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
        idx.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc2')
        session.commit()

        subject = idx.node(..., 'user', 'alice', create_if_missing=False)
        reachable = idx.lookup_reachable(subject.id)

        obj1 = idx.node('viewer', 'document', 'doc1', create_if_missing=False)
        obj2 = idx.node('viewer', 'document', 'doc2', create_if_missing=False)

        assert obj1.id in reachable
        assert obj2.id in reachable

    def test_lookup_reachable_transitive(self, v4_env):
        engine, session, idx = v4_env
        idx.add_edge(..., 'user', 'alice', 'member', 'group', 'g1')
        idx.add_edge('member', 'group', 'g1', 'viewer', 'document', 'doc1')
        session.commit()

        subject = idx.node(..., 'user', 'alice', create_if_missing=False)
        reachable = idx.lookup_reachable(subject.id)

        doc_node = idx.node('viewer', 'document', 'doc1', create_if_missing=False)
        assert doc_node.id in reachable

    def test_lookup_reverse_basic(self, v4_env):
        engine, session, idx = v4_env
        idx.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
        idx.add_edge(..., 'user', 'bob', 'viewer', 'document', 'doc1')
        session.commit()

        obj = idx.node('viewer', 'document', 'doc1', create_if_missing=False)
        subjects = idx.lookup_reverse(obj.id)

        alice_node = idx.node(..., 'user', 'alice', create_if_missing=False)
        bob_node = idx.node(..., 'user', 'bob', create_if_missing=False)

        assert alice_node.id in subjects
        assert bob_node.id in subjects

    def test_lookup_reachable_empty(self, v4_env):
        engine, session, idx = v4_env
        # Create a node with no outgoing edges
        n = idx.node(..., 'user', 'lonely', create_if_missing=True, implicit=False)
        session.commit()

        reachable = idx.lookup_reachable(n.id)
        assert len(reachable) == 0

    def test_lookup_reverse_empty(self, v4_env):
        engine, session, idx = v4_env
        n = idx.node('viewer', 'document', 'orphan', create_if_missing=True, implicit=False)
        session.commit()

        subjects = idx.lookup_reverse(n.id)
        assert len(subjects) == 0


# ---------------------------------------------------------------------------
# remove_node tests
# ---------------------------------------------------------------------------

class TestRemoveNode:
    def test_remove_node_clears_edges(self, v4_env):
        engine, session, idx = v4_env
        idx.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
        session.commit()

        assert idx.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is True

        # Remove the alice user node
        idx.remove_node(..., 'user', 'alice')
        session.commit()

        assert idx.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is False

    def test_remove_node_deltas(self, v4_env):
        engine, session, idx = v4_env
        idx.add_edge(..., 'user', 'alice', 'viewer', 'document', 'doc1')
        session.commit()

        deltas = _drained(session, "test_store",
                          lambda: idx.remove_node(..., 'user', 'alice'))

        removed = [d for d in deltas if d.action == "REMOVED"]
        assert len(removed) >= 1

    def test_remove_middle_node_breaks_transitivity(self, v4_env):
        engine, session, idx = v4_env
        idx.add_edge(..., 'user', 'alice', 'member', 'group', 'g1')
        idx.add_edge('member', 'group', 'g1', 'viewer', 'document', 'doc1')
        session.commit()

        assert idx.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is True

        # Remove the group node
        idx.remove_node('member', 'group', 'g1')
        session.commit()

        assert idx.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is False


# ---------------------------------------------------------------------------
# Node management tests
# ---------------------------------------------------------------------------

class TestNodeManagement:
    def test_node_create_if_missing(self, v4_env):
        engine, session, idx = v4_env
        n = idx.node(..., 'user', 'alice', create_if_missing=True)
        session.commit()

        assert n is not None
        assert n.type == 'user'
        assert n.name == 'alice'
        assert n.id is not None

    def test_node_not_found_raises(self, v4_env):
        engine, session, idx = v4_env
        with pytest.raises(KeyError, match='Node missing'):
            idx.node(..., 'user', 'ghost', create_if_missing=False)

    def test_node_idempotent_lookup(self, v4_env):
        engine, session, idx = v4_env
        n1 = idx.node(..., 'user', 'alice', create_if_missing=True)
        session.commit()
        n2 = idx.node(..., 'user', 'alice', create_if_missing=True)

        assert n1.id == n2.id

    def test_node_predicate_ellipsis_stored_as_dots(self, v4_env):
        engine, session, idx = v4_env
        n = idx.node(..., 'user', 'alice', create_if_missing=True)
        session.commit()

        assert n.predicate == '...'
        assert n.predicate_or_ellipsis is Ellipsis


# ---------------------------------------------------------------------------
# Store metadata tests
# ---------------------------------------------------------------------------

class TestStoreMetadata:
    def test_store_creation(self):
        v4 = _import_v4()
        engine = create_engine('sqlite:///:memory:')
        SQLModel.metadata.create_all(engine)
        session = Session(engine)

        store = v4.Store(id="my_store", description="A test store")
        session.add(store)
        session.commit()
        session.refresh(store)

        assert store.id == "my_store"
        assert store.description == "A test store"
        assert store.created_at > 0
        session.close()

    def test_store_default_description(self):
        v4 = _import_v4()
        engine = create_engine('sqlite:///:memory:')
        SQLModel.metadata.create_all(engine)
        session = Session(engine)

        store = v4.Store(id="bare_store")
        session.add(store)
        session.commit()
        session.refresh(store)

        assert store.description == ""
        session.close()


# ---------------------------------------------------------------------------
# Edge-case and error-handling tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_cycle_prevention(self, v4_env):
        engine, session, idx = v4_env
        idx.add_edge(..., 'node', 'A', '...', 'node', 'B')
        idx.add_edge(..., 'node', 'B', '...', 'node', 'C')
        session.commit()

        with pytest.raises((ValueError, AssertionError)):
            idx.add_edge(..., 'node', 'C', '...', 'node', 'A')

    def test_self_loop_prevention(self, v4_env):
        """Adding an edge from a node to itself should fail."""
        engine, session, idx = v4_env
        with pytest.raises((ValueError, AssertionError)):
            idx.add_edge(..., 'node', 'A', '...', 'node', 'A')

    def test_remove_nonexistent_edge_raises(self, v4_env):
        engine, session, idx = v4_env
        with pytest.raises((ValueError, KeyError)):
            idx.remove_edge(..., 'user', 'nobody', 'viewer', 'document', 'nothing')

    def test_remove_edge_twice_raises(self, v4_env):
        engine, session, idx = v4_env
        idx.add_edge(..., 'node', 'A', '...', 'node', 'B')
        session.commit()

        idx.remove_edge(..., 'node', 'A', '...', 'node', 'B')
        session.commit()

        with pytest.raises((ValueError, KeyError)):
            idx.remove_edge(..., 'node', 'A', '...', 'node', 'B')

    def test_duplicate_edge_multi_graph(self, v4_env):
        """Adding the same edge twice requires removing it twice."""
        engine, session, idx = v4_env
        idx.add_edge(..., 'node', 'A', '...', 'node', 'B')
        idx.add_edge(..., 'node', 'A', '...', 'node', 'B')
        session.commit()

        assert idx.check_reachable(..., 'node', 'A', '...', 'node', 'B') is True

        idx.remove_edge(..., 'node', 'A', '...', 'node', 'B')
        session.commit()
        assert idx.check_reachable(..., 'node', 'A', '...', 'node', 'B') is True

        idx.remove_edge(..., 'node', 'A', '...', 'node', 'B')
        session.commit()
        assert idx.check_reachable(..., 'node', 'A', '...', 'node', 'B') is False

    def test_check_reachable_missing_nodes_returns_false(self, v4_env):
        engine, session, idx = v4_env
        assert idx.check_reachable(..., 'user', 'ghost', 'viewer', 'document', 'phantom') is False

    def test_long_chain(self, v4_env):
        engine, session, idx = v4_env
        nodes = [f"N{i}" for i in range(10)]
        for i in range(len(nodes) - 1):
            idx.add_edge(..., 'node', nodes[i], '...', 'node', nodes[i + 1])
        session.commit()

        assert idx.check_reachable(..., 'node', nodes[0], '...', 'node', nodes[-1]) is True
        assert idx.check_reachable(..., 'node', nodes[-1], '...', 'node', nodes[0]) is False

        # Break chain in the middle
        idx.remove_edge(..., 'node', nodes[4], '...', 'node', nodes[5])
        session.commit()

        assert idx.check_reachable(..., 'node', nodes[0], '...', 'node', nodes[-1]) is False
        assert idx.check_reachable(..., 'node', nodes[0], '...', 'node', nodes[4]) is True
        assert idx.check_reachable(..., 'node', nodes[5], '...', 'node', nodes[-1]) is True

    def test_diamond_graph(self, v4_env):
        """A -> B, A -> C, B -> D, C -> D: removing one path keeps the other."""
        engine, session, idx = v4_env
        idx.add_edge(..., 'node', 'A', '...', 'node', 'B')
        idx.add_edge(..., 'node', 'A', '...', 'node', 'C')
        idx.add_edge(..., 'node', 'B', '...', 'node', 'D')
        idx.add_edge(..., 'node', 'C', '...', 'node', 'D')
        session.commit()

        assert idx.check_reachable(..., 'node', 'A', '...', 'node', 'D') is True

        idx.remove_edge(..., 'node', 'B', '...', 'node', 'D')
        session.commit()
        # A -> C -> D still exists
        assert idx.check_reachable(..., 'node', 'A', '...', 'node', 'D') is True

        idx.remove_edge(..., 'node', 'C', '...', 'node', 'D')
        session.commit()
        assert idx.check_reachable(..., 'node', 'A', '...', 'node', 'D') is False

    def test_fan_out(self, v4_env):
        """One source with many targets."""
        engine, session, idx = v4_env
        for i in range(5):
            idx.add_edge(..., 'user', 'admin', 'viewer', 'document', f'doc{i}')
        session.commit()

        for i in range(5):
            assert idx.check_reachable(..., 'user', 'admin', 'viewer', 'document', f'doc{i}') is True

        # Cross-check: unrelated docs
        assert idx.check_reachable(..., 'user', 'admin', 'viewer', 'document', 'doc99') is False

    def test_fan_in(self, v4_env):
        """Many subjects reaching the same object."""
        engine, session, idx = v4_env
        for i in range(5):
            idx.add_edge(..., 'user', f'user{i}', 'viewer', 'document', 'shared')
        session.commit()

        for i in range(5):
            assert idx.check_reachable(..., 'user', f'user{i}', 'viewer', 'document', 'shared') is True

        obj = idx.node('viewer', 'document', 'shared', create_if_missing=False)
        subjects = idx.lookup_reverse(obj.id)
        assert len(subjects) == 5
