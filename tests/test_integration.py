import pytest
from sqlmodel import SQLModel

from index_v3 import engine, add_edge, remove_edge, check_reachable
from zanzibar_utils_v1 import (
    Entity,
    RelationalTriple,
    parse_openfga_schema,
    RuleSet
)


@pytest.fixture(autouse=True)
def setup_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


def ingest_triple(ruleset: RuleSet, triple: RelationalTriple):
    for derived in ruleset.apply(triple):
        subject_predicate = derived.subject_predicate
        if subject_predicate is Ellipsis:
            subject_predicate = '...'
            
        add_edge(
            subject_predicate=subject_predicate,
            subject_type=derived.subject.type,
            subject_name=derived.subject.name,
            relation=derived.relation,
            object_type=derived.object.type,
            object_name=derived.object.name
        )


def remove_ingested_triple(ruleset: RuleSet, triple: RelationalTriple):
    for derived in ruleset.apply(triple):
        subject_predicate = derived.subject_predicate
        if subject_predicate is Ellipsis:
            subject_predicate = '...'
            
        remove_edge(
            subject_predicate=subject_predicate,
            subject_type=derived.subject.type,
            subject_name=derived.subject.name,
            relation=derived.relation,
            object_type=derived.object.type,
            object_name=derived.object.name
        )


def test_integration_zanzibar_v3():
    schema = '''
    model
      schema 1.1

    type user

    type group
      relations
        define member: [user]

    type document
      relations
        define owner: [user]
        define writer: [user, group#member] or owner
        define viewer: [user, group#member] or writer
    '''
    ruleset = parse_openfga_schema(schema)

    # 1. Add alice as member of group g1
    # 2. Add group g1 as viewer of document doc1
    # 3. Check if alice can view doc1
    
    t1 = RelationalTriple(Entity('user', 'alice'), 'member', Entity('group', 'g1'), Ellipsis)
    ingest_triple(ruleset, t1)
    
    t2 = RelationalTriple(Entity('group', 'g1'), 'viewer', Entity('document', 'doc1'), 'member')
    ingest_triple(ruleset, t2)
    
    # Alice should be able to view doc1
    assert check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is True
    
    # Alice shouldn't be able to write
    assert check_reachable(..., 'user', 'alice', 'writer', 'document', 'doc1') is False
    
    # 4. Add bob as owner of doc1
    t3 = RelationalTriple(Entity('user', 'bob'), 'owner', Entity('document', 'doc1'), Ellipsis)
    ingest_triple(ruleset, t3)
    
    # Bob should be owner, writer, and viewer
    assert check_reachable(..., 'user', 'bob', 'owner', 'document', 'doc1') is True
    assert check_reachable(..., 'user', 'bob', 'writer', 'document', 'doc1') is True
    assert check_reachable(..., 'user', 'bob', 'viewer', 'document', 'doc1') is True

    # 5. Remove g1 as viewer of doc1
    remove_ingested_triple(ruleset, t2)
    
    # Alice should no longer view doc1
    assert check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is False


def test_integration_hierarchy():
    schema = '''
    model
      schema 1.1

    type user

    type folder
      relations
        define parent_folder: [folder]
        define owner: [user] or owner from parent_folder
        define viewer: [user] or owner or viewer from parent_folder

    type document
      relations
        define parent_folder: [folder]
        define owner: [user] or owner from parent_folder
        define viewer: [user] or owner or viewer from parent_folder
    '''
    ruleset = parse_openfga_schema(schema)
    
    # hierarchy: root -> src -> main.py
    t_f_parent = RelationalTriple(Entity('folder', 'root'), 'parent_folder', Entity('folder', 'src'), Ellipsis)
    ingest_triple(ruleset, t_f_parent)
    
    t_d_parent = RelationalTriple(Entity('folder', 'src'), 'parent_folder', Entity('document', 'main.py'), Ellipsis)
    ingest_triple(ruleset, t_d_parent)

    # charlie is owner of root folder
    t_owner = RelationalTriple(Entity('user', 'charlie'), 'owner', Entity('folder', 'root'), Ellipsis)
    ingest_triple(ruleset, t_owner)

    # Check reachability: charlie should be owner of main.py
    assert check_reachable(..., 'user', 'charlie', 'owner', 'document', 'main.py') is True
    # charlie should be viewer of main.py
    assert check_reachable(..., 'user', 'charlie', 'viewer', 'document', 'main.py') is True

    # Check that another user doesn't have access
    assert check_reachable(..., 'user', 'eve', 'viewer', 'document', 'main.py') is False
