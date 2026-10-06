import pytest
from sqlmodel import Session, create_engine, SQLModel
from zanzibar.graphindex.models import Store
from zanzibar.graphindex.core import ReachabilityIndex

@pytest.fixture
def empty_env():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    
    session = Session(engine)
    store = Store(id="test_store")
    session.add(store)
    session.commit()
    
    idx = ReachabilityIndex(session, store_id="test_store")
    yield engine, session, idx
    session.close()

def test_core_add_edge_cycle_detection(empty_env):
    engine, session, idx = empty_env
    idx.add_edge(..., "node", "A", "...", "node", "B")
    idx.add_edge(..., "node", "B", "...", "node", "C")
    session.commit()
    
    with pytest.raises((ValueError, AssertionError)):
        idx.add_edge(..., "node", "C", "...", "node", "A")

def test_core_lookup_methods(empty_env):
    engine, session, idx = empty_env
    idx.add_edge("...", "user", "alice", "viewer", "document", "doc1")
    session.commit()
    
    # lookup object given subject
    subj = idx.node("...", "user", "alice", create_if_missing=False)
    reachable = idx.lookup_reachable(subj.id)
    
    obj = idx.node("viewer", "document", "doc1", create_if_missing=False)
    assert obj.id in reachable
    
    # lookup reverse
    reverse = idx.lookup_reverse(obj.id)
    assert subj.id in reverse
