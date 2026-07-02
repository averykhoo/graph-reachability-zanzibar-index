import pytest
from sqlmodel import Session, create_engine, SQLModel
from index_v4.models import StoreV4, NodeV4, PermissionDelta
from types import EllipsisType

def test_permission_delta_fields():
    delta = PermissionDelta(store_id="s1", subject_id=1, object_id=2, action="ADDED")
    assert delta.store_id == "s1"
    assert delta.subject_id == 1
    assert delta.object_id == 2
    assert delta.action == "ADDED"

def test_store_model():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        store = StoreV4(id="tenant_1", description="test tenant")
        session.add(store)
        session.commit()
        session.refresh(store)
        
        assert store.id == "tenant_1"
        assert store.description == "test tenant"
        assert store.created_at > 0

def test_node_model_ellipsis():
    node = NodeV4(store_id="s1", predicate="...", type="user", name="alice")
    assert node.predicate_or_ellipsis is Ellipsis
    
    node2 = NodeV4(store_id="s1", predicate="viewer", type="user", name="bob")
    assert node2.predicate_or_ellipsis == "viewer"
