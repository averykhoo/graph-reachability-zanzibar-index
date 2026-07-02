import pytest
from sqlmodel import SQLModel

from index_v1 import DirectedAcyclicMultiGraphReachabilityIndex
from index_v2 import DirectedAcyclicMultiGraphReachabilityIndexV2, Node as NodeV2
from index_v3 import engine, add_edge, remove_edge, check_reachable


class IndexPolyfill:
    def add_edge(self, from_node: str, to_node: str):
        raise NotImplementedError

    def remove_edge(self, from_node: str, to_node: str):
        raise NotImplementedError

    def check_reachable(self, from_node: str, to_node: str) -> bool:
        raise NotImplementedError


class IndexV1Polyfill(IndexPolyfill):
    def __init__(self):
        self.idx = DirectedAcyclicMultiGraphReachabilityIndex()

    def add_edge(self, from_node: str, to_node: str):
        self.idx.add_edge(from_node, to_node)

    def remove_edge(self, from_node: str, to_node: str):
        self.idx.remove_edge(from_node, to_node)

    def check_reachable(self, from_node: str, to_node: str) -> bool:
        return to_node in self.idx.index_paths.get(from_node, set())


class IndexV2Polyfill(IndexPolyfill):
    def __init__(self):
        self.idx = DirectedAcyclicMultiGraphReachabilityIndexV2()

    def add_edge(self, from_node: str, to_node: str):
        self.idx.add_edge(NodeV2(name=from_node), NodeV2(name=to_node))

    def remove_edge(self, from_node: str, to_node: str):
        self.idx.remove_edge(NodeV2(name=from_node), NodeV2(name=to_node))

    def check_reachable(self, from_node: str, to_node: str) -> bool:
        return self.idx.check_reachable(NodeV2(name=from_node), NodeV2(name=to_node))


class IndexV3Polyfill(IndexPolyfill):
    def __init__(self):
        # Clear database and recreate tables
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)

    def add_edge(self, from_node: str, to_node: str):
        add_edge(..., 'node', from_node, '...', 'node', to_node)

    def remove_edge(self, from_node: str, to_node: str):
        remove_edge(..., 'node', from_node, '...', 'node', to_node)

    def check_reachable(self, from_node: str, to_node: str) -> bool:
        return check_reachable(..., 'node', from_node, '...', 'node', to_node)


class IndexV4Polyfill(IndexPolyfill):
    def __init__(self):
        from index_v4 import ReachabilityIndex, Store
        from sqlmodel import Session, create_engine
        
        self.engine = create_engine('sqlite:///:memory:')
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        store = Store(id="test_store")
        self.session.add(store)
        self.session.commit()
        
        self.idx = ReachabilityIndex(self.session, store_id="test_store")

    def add_edge(self, from_node: str, to_node: str):
        self.idx.add_edge(..., 'node', from_node, '...', 'node', to_node)
        self.session.commit()

    def remove_edge(self, from_node: str, to_node: str):
        self.idx.remove_edge(..., 'node', from_node, '...', 'node', to_node)
        self.session.commit()

    def check_reachable(self, from_node: str, to_node: str) -> bool:
        return self.idx.check_reachable(..., 'node', from_node, '...', 'node', to_node)

    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()


@pytest.fixture(params=[IndexV1Polyfill, IndexV2Polyfill, IndexV3Polyfill, IndexV4Polyfill])
def index(request):
    """Provides a fresh index instance for each test across all versions."""
    return request.param()


def test_basic_add_and_reachable(index: IndexPolyfill):
    index.add_edge("A", "B")
    assert index.check_reachable("A", "B") is True
    assert index.check_reachable("B", "A") is False
    assert index.check_reachable("A", "C") is False


def test_indirect_reachability(index: IndexPolyfill):
    index.add_edge("A", "B")
    index.add_edge("B", "C")
    assert index.check_reachable("A", "B") is True
    assert index.check_reachable("B", "C") is True
    assert index.check_reachable("A", "C") is True
    assert index.check_reachable("C", "A") is False


def test_remove_edge(index: IndexPolyfill):
    index.add_edge("A", "B")
    index.add_edge("B", "C")
    assert index.check_reachable("A", "C") is True
    
    index.remove_edge("B", "C")
    assert index.check_reachable("A", "C") is False
    assert index.check_reachable("A", "B") is True
    assert index.check_reachable("B", "C") is False


def test_multiple_paths(index: IndexPolyfill):
    index.add_edge("A", "B")
    index.add_edge("B", "D")
    index.add_edge("A", "C")
    index.add_edge("C", "D")
    
    assert index.check_reachable("A", "D") is True
    index.remove_edge("B", "D")
    # A -> C -> D still exists
    assert index.check_reachable("A", "D") is True
    index.remove_edge("C", "D")
    assert index.check_reachable("A", "D") is False


def test_cycle_prevention(index: IndexPolyfill):
    index.add_edge("A", "B")
    index.add_edge("B", "C")
    with pytest.raises(ValueError, match="create a cycle|reachable"):
        index.add_edge("C", "A")


def test_multi_graph_behavior(index: IndexPolyfill):
    # Adding the same edge twice requires removing it twice
    index.add_edge("A", "B")
    index.add_edge("A", "B")
    assert index.check_reachable("A", "B") is True
    
    index.remove_edge("A", "B")
    assert index.check_reachable("A", "B") is True
    
    index.remove_edge("A", "B")
    assert index.check_reachable("A", "B") is False
    
    # Removing a non-existent edge should raise ValueError
    with pytest.raises(ValueError, match="(?i)no direct edge|cannot remove|Non-existent edge cannot be removed"):
        index.remove_edge("A", "B")

def test_long_chain(index: IndexPolyfill):
    nodes = [f"N{i}" for i in range(10)]
    for i in range(len(nodes) - 1):
        index.add_edge(nodes[i], nodes[i+1])
        
    assert index.check_reachable(nodes[0], nodes[-1]) is True
    assert index.check_reachable(nodes[-1], nodes[0]) is False
    
    # Break chain in the middle
    index.remove_edge(nodes[4], nodes[5])
    assert index.check_reachable(nodes[0], nodes[-1]) is False
    assert index.check_reachable(nodes[0], nodes[4]) is True
    assert index.check_reachable(nodes[5], nodes[-1]) is True
