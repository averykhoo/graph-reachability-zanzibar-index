import pytest
from sqlmodel import SQLModel

from index_v3 import engine as v3_engine
from index_v3 import add_edge as v3_add_edge
from index_v3 import remove_edge as v3_remove_edge
from index_v3 import check_reachable as v3_check_reachable
from zanzibar_utils_v1 import (
    Entity,
    RelationalTriple,
    parse_openfga_schema,
    RuleSet
)


# ---------------------------------------------------------------------------
# Backend abstraction
# ---------------------------------------------------------------------------

class Backend:
    """Unified interface for add_edge / remove_edge / check_reachable."""

    def add_edge(self, subject_predicate, subject_type, subject_name,
                 relation, object_type, object_name):
        raise NotImplementedError

    def remove_edge(self, subject_predicate, subject_type, subject_name,
                    relation, object_type, object_name):
        raise NotImplementedError

    def check_reachable(self, subject_predicate, subject_type, subject_name,
                        relation, object_type, object_name) -> bool:
        raise NotImplementedError

    def teardown(self):
        pass


class V3Backend(Backend):
    def __init__(self):
        SQLModel.metadata.drop_all(v3_engine)
        SQLModel.metadata.create_all(v3_engine)

    def add_edge(self, subject_predicate, subject_type, subject_name,
                 relation, object_type, object_name):
        v3_add_edge(subject_predicate, subject_type, subject_name,
                    relation, object_type, object_name)

    def remove_edge(self, subject_predicate, subject_type, subject_name,
                    relation, object_type, object_name):
        v3_remove_edge(subject_predicate, subject_type, subject_name,
                       relation, object_type, object_name)

    def check_reachable(self, subject_predicate, subject_type, subject_name,
                        relation, object_type, object_name) -> bool:
        return v3_check_reachable(subject_predicate, subject_type, subject_name,
                                  relation, object_type, object_name)


class V4Backend(Backend):
    def __init__(self):
        from index_v4 import ReachabilityIndex, Store
        from sqlmodel import Session, create_engine

        self._engine = create_engine('sqlite:///:memory:')
        SQLModel.metadata.create_all(self._engine)
        self._session = Session(self._engine)

        store = Store(id="integration_test")
        self._session.add(store)
        self._session.commit()

        self.idx = ReachabilityIndex(self._session, store_id="integration_test")

    def add_edge(self, subject_predicate, subject_type, subject_name,
                 relation, object_type, object_name):
        self.idx.add_edge(subject_predicate, subject_type, subject_name,
                          relation, object_type, object_name)
        self._session.commit()

    def remove_edge(self, subject_predicate, subject_type, subject_name,
                    relation, object_type, object_name):
        self.idx.remove_edge(subject_predicate, subject_type, subject_name,
                             relation, object_type, object_name)
        self._session.commit()

    def check_reachable(self, subject_predicate, subject_type, subject_name,
                        relation, object_type, object_name) -> bool:
        return self.idx.check_reachable(subject_predicate, subject_type, subject_name,
                                        relation, object_type, object_name)

    def teardown(self):
        self._session.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(params=["v3", "v4"])
def backend(request) -> Backend:
    """Provides a fresh backend for each test, parameterized over v3 and v4."""
    if request.param == "v3":
        be = V3Backend()
    else:
        be = V4Backend()
    yield be
    be.teardown()


def ingest_triple(backend: Backend, ruleset: RuleSet, triple: RelationalTriple):
    for derived in ruleset.apply(triple):
        subject_predicate = derived.subject_predicate
        if subject_predicate is Ellipsis:
            subject_predicate = '...'

        backend.add_edge(
            subject_predicate=subject_predicate,
            subject_type=derived.subject.type,
            subject_name=derived.subject.name,
            relation=derived.relation,
            object_type=derived.object.type,
            object_name=derived.object.name
        )


def remove_ingested_triple(backend: Backend, ruleset: RuleSet, triple: RelationalTriple):
    for derived in ruleset.apply(triple):
        subject_predicate = derived.subject_predicate
        if subject_predicate is Ellipsis:
            subject_predicate = '...'

        backend.remove_edge(
            subject_predicate=subject_predicate,
            subject_type=derived.subject.type,
            subject_name=derived.subject.name,
            relation=derived.relation,
            object_type=derived.object.type,
            object_name=derived.object.name
        )


# ---------------------------------------------------------------------------
# Integration tests (run against both v3 and v4)
# ---------------------------------------------------------------------------

def test_integration_zanzibar(backend: Backend):
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
    t1 = RelationalTriple(Entity('user', 'alice'), 'member', Entity('group', 'g1'), Ellipsis)
    ingest_triple(backend, ruleset, t1)

    # 2. Add group g1 as viewer of document doc1
    t2 = RelationalTriple(Entity('group', 'g1'), 'viewer', Entity('document', 'doc1'), 'member')
    ingest_triple(backend, ruleset, t2)

    # Alice should be able to view doc1
    assert backend.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is True

    # Alice shouldn't be able to write
    assert backend.check_reachable(..., 'user', 'alice', 'writer', 'document', 'doc1') is False

    # 3. Add bob as owner of doc1
    t3 = RelationalTriple(Entity('user', 'bob'), 'owner', Entity('document', 'doc1'), Ellipsis)
    ingest_triple(backend, ruleset, t3)

    # Bob should be owner, writer, and viewer
    assert backend.check_reachable(..., 'user', 'bob', 'owner', 'document', 'doc1') is True
    assert backend.check_reachable(..., 'user', 'bob', 'writer', 'document', 'doc1') is True
    assert backend.check_reachable(..., 'user', 'bob', 'viewer', 'document', 'doc1') is True

    # 4. Remove g1 as viewer of doc1
    remove_ingested_triple(backend, ruleset, t2)

    # Alice should no longer view doc1
    assert backend.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is False


def test_integration_hierarchy(backend: Backend):
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
    ingest_triple(backend, ruleset, t_f_parent)

    t_d_parent = RelationalTriple(Entity('folder', 'src'), 'parent_folder', Entity('document', 'main.py'), Ellipsis)
    ingest_triple(backend, ruleset, t_d_parent)

    # charlie is owner of root folder
    t_owner = RelationalTriple(Entity('user', 'charlie'), 'owner', Entity('folder', 'root'), Ellipsis)
    ingest_triple(backend, ruleset, t_owner)

    # charlie should be owner and viewer of main.py
    assert backend.check_reachable(..., 'user', 'charlie', 'owner', 'document', 'main.py') is True
    assert backend.check_reachable(..., 'user', 'charlie', 'viewer', 'document', 'main.py') is True

    # another user doesn't have access
    assert backend.check_reachable(..., 'user', 'eve', 'viewer', 'document', 'main.py') is False


def test_integration_confluence(backend: Backend, load_fga_schema):
    schema = load_fga_schema('confluence.fga')
    ruleset = parse_openfga_schema(schema)

    t1 = RelationalTriple(Entity('user', 'u1'), 'member', Entity('group', 'g1'), Ellipsis)
    ingest_triple(backend, ruleset, t1)

    t2 = RelationalTriple(Entity('group', 'g1'), 'member', Entity('organization', 'org1'), 'member')
    ingest_triple(backend, ruleset, t2)

    t3 = RelationalTriple(Entity('organization', 'org1'), 'organization', Entity('space', 's1'), Ellipsis)
    ingest_triple(backend, ruleset, t3)

    t4 = RelationalTriple(Entity('space', 's1'), 'space', Entity('page', 'p1'), Ellipsis)
    ingest_triple(backend, ruleset, t4)

    assert backend.check_reachable(..., 'user', 'u1', 'can_view_pages', 'space', 's1') is True
    assert backend.check_reachable(..., 'user', 'u1', 'can_view', 'page', 'p1') is True


@pytest.mark.xfail(reason="'but not' might not be fully supported by parser yet")
def test_integration_demorgans(backend: Backend, load_fga_schema):
    schema = load_fga_schema('demorgans_reverse.fga')
    ruleset = parse_openfga_schema(schema)

    t1 = RelationalTriple(Entity('user', 'alice'), 'assigned', Entity('role', 'r1'), Ellipsis)
    ingest_triple(backend, ruleset, t1)


def test_integration_github(backend: Backend, load_fga_schema):
    schema = load_fga_schema('github.fga')
    ruleset = parse_openfga_schema(schema)

    t1 = RelationalTriple(Entity('user', 'u1'), 'repo_admin', Entity('organization', 'org1'), Ellipsis)
    ingest_triple(backend, ruleset, t1)

    t2 = RelationalTriple(Entity('organization', 'org1'), 'owner', Entity('repo', 'r1'), Ellipsis)
    ingest_triple(backend, ruleset, t2)

    assert backend.check_reachable(..., 'user', 'u1', 'admin', 'repo', 'r1') is True
    assert backend.check_reachable(..., 'user', 'u1', 'maintainer', 'repo', 'r1') is True
    assert backend.check_reachable(..., 'user', 'u1', 'writer', 'repo', 'r1') is True
    assert backend.check_reachable(..., 'user', 'u1', 'triager', 'repo', 'r1') is True
    assert backend.check_reachable(..., 'user', 'u1', 'reader', 'repo', 'r1') is True


def test_integration_gdrive(backend: Backend, load_fga_schema):
    """Integration test with Google Drive schema: domain membership + folder hierarchy."""
    schema = load_fga_schema('gdrive.fga')
    ruleset = parse_openfga_schema(schema)

    # alice is a member of engineering domain
    t1 = RelationalTriple(Entity('user', 'alice'), 'member', Entity('domain', 'engineering'), Ellipsis)
    ingest_triple(backend, ruleset, t1)

    # engineering domain member is a writer on shared-docs folder
    t2 = RelationalTriple(Entity('domain', 'engineering'), 'writer', Entity('folder', 'shared-docs'), 'member')
    ingest_triple(backend, ruleset, t2)

    # alice should be writer and viewer of shared-docs
    assert backend.check_reachable(..., 'user', 'alice', 'writer', 'folder', 'shared-docs') is True
    assert backend.check_reachable(..., 'user', 'alice', 'viewer', 'folder', 'shared-docs') is True

    # alice should NOT be owner
    assert backend.check_reachable(..., 'user', 'alice', 'owner', 'folder', 'shared-docs') is False


def test_integration_multiple_group_memberships(backend: Backend):
    """Test a user in multiple groups with different permissions on the same document."""
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

    # alice is in group editors and group readers
    t1 = RelationalTriple(Entity('user', 'alice'), 'member', Entity('group', 'editors'), Ellipsis)
    ingest_triple(backend, ruleset, t1)

    t2 = RelationalTriple(Entity('user', 'alice'), 'member', Entity('group', 'readers'), Ellipsis)
    ingest_triple(backend, ruleset, t2)

    # editors can write doc1, readers can view doc1
    t3 = RelationalTriple(Entity('group', 'editors'), 'writer', Entity('document', 'doc1'), 'member')
    ingest_triple(backend, ruleset, t3)

    t4 = RelationalTriple(Entity('group', 'readers'), 'viewer', Entity('document', 'doc1'), 'member')
    ingest_triple(backend, ruleset, t4)

    # alice should have both write and view
    assert backend.check_reachable(..., 'user', 'alice', 'writer', 'document', 'doc1') is True
    assert backend.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is True

    # Remove editors -> writer on doc1
    remove_ingested_triple(backend, ruleset, t3)

    # alice should still have view (through readers group) but NOT write
    assert backend.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is True
    assert backend.check_reachable(..., 'user', 'alice', 'writer', 'document', 'doc1') is False


def test_integration_revoke_group_membership(backend: Backend):
    """Removing a user from a group revokes all permissions granted through that group."""
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

    t1 = RelationalTriple(Entity('user', 'alice'), 'member', Entity('group', 'g1'), Ellipsis)
    ingest_triple(backend, ruleset, t1)

    t2 = RelationalTriple(Entity('group', 'g1'), 'writer', Entity('document', 'doc1'), 'member')
    ingest_triple(backend, ruleset, t2)

    assert backend.check_reachable(..., 'user', 'alice', 'writer', 'document', 'doc1') is True
    assert backend.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is True

    # Remove alice from g1
    remove_ingested_triple(backend, ruleset, t1)

    # All access revoked
    assert backend.check_reachable(..., 'user', 'alice', 'writer', 'document', 'doc1') is False
    assert backend.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is False
