import pytest
from sqlmodel import SQLModel

from legacy.index_v3 import engine as v3_engine
from legacy.index_v3 import add_edge as v3_add_edge
from legacy.index_v3 import remove_edge as v3_remove_edge
from legacy.index_v3 import check_reachable as v3_check_reachable
from zanzibar_utils_v1 import (
    Entity,
    RelationalTriple,
    parse_openfga_schema,
    RuleSet,
    UnsupportedByGraphIndex,
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


class V4WildcardBackend(Backend):
    """Wildcard-aware backend over WildcardIndex (v4 only). add_edge/remove_edge map to
    add_tuple/remove_tuple; check_reachable runs the O(1) probe set."""

    def __init__(self, schema_info):
        from index_v4 import ReachabilityIndex, Store, WildcardIndex
        from sqlmodel import Session, create_engine

        self._engine = create_engine('sqlite:///:memory:')
        SQLModel.metadata.create_all(self._engine)
        self._session = Session(self._engine)
        store = Store(id="wildcard_test")
        self._session.add(store)
        self._session.commit()

        idx = ReachabilityIndex(self._session, store_id="wildcard_test")
        self.widx = WildcardIndex(idx, schema_info)
        self.widx.backfill()          # harmless on an empty store; spec §7.2 calls it in every fixture

    def add_edge(self, subject_predicate, subject_type, subject_name,
                 relation, object_type, object_name):
        self.widx.add_tuple(subject_predicate, subject_type, subject_name,
                            relation, object_type, object_name)
        self._session.commit()

    def remove_edge(self, subject_predicate, subject_type, subject_name,
                    relation, object_type, object_name):
        self.widx.remove_tuple(subject_predicate, subject_type, subject_name,
                               relation, object_type, object_name)
        self._session.commit()

    def check_reachable(self, subject_predicate, subject_type, subject_name,
                        relation, object_type, object_name) -> bool:
        return self.widx.check(subject_predicate, subject_type, subject_name,
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


def test_integration_demorgans_compiles_for_graph(load_fga_schema):
    # The P7 flip (boolean spec §10): `but not` schemas compile into derived
    # predicates instead of being refused; the historical guard stays reachable.
    schema = load_fga_schema('demorgans_reverse.fga')
    ruleset = parse_openfga_schema(schema)
    assert ruleset.compiled is not None and ruleset.compiled.plans
    with pytest.raises(UnsupportedByGraphIndex):
        parse_openfga_schema(schema, enable_boolean=False)


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

    # alice is a member of engineering group
    t1 = RelationalTriple(Entity('user', 'alice'), 'member', Entity('group', 'engineering'), Ellipsis)
    ingest_triple(backend, ruleset, t1)

    # engineering group member is a viewer on shared-docs folder
    t2 = RelationalTriple(Entity('group', 'engineering'), 'viewer', Entity('folder', 'shared-docs'), 'member')
    ingest_triple(backend, ruleset, t2)

    # alice should be a viewer of shared-docs
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


# ---------------------------------------------------------------------------
# Wildcard integration tests (v4 WildcardIndex only; v3 has no wildcard support)
# ---------------------------------------------------------------------------

def test_integration_wildcard_public_doc():
    schema = '''
    model
      schema 1.1

    type user

    type document
      relations
        define viewer: [user, user:*]
    '''
    ruleset = parse_openfga_schema(schema)
    backend = V4WildcardBackend(ruleset.schema_info)

    # public grant: any user can view doc1
    ingest_triple(backend, ruleset, RelationalTriple(Entity('user', '*'), 'viewer', Entity('document', 'doc1'), Ellipsis))

    # a never-seen user is a viewer; an unrelated doc is not covered
    assert backend.check_reachable(..., 'user', 'ghost', 'viewer', 'document', 'doc1') is True
    assert backend.check_reachable(..., 'user', 'ghost', 'viewer', 'document', 'doc2') is False
    backend.teardown()


def test_integration_wildcard_two_hop_hierarchy():
    schema = '''
    model
      schema 1.1

    type user

    type folder
      relations
        define parent_folder: [folder, folder:*]
        define viewer: [user:*, user, folder:*#viewer] or viewer from parent_folder

    type document
      relations
        define parent_folder: [folder, folder:*]
        define viewer: [user:*, user, folder:*#viewer] or viewer from parent_folder
    '''
    # Only SUBJECT wildcards are exercised (user:* viewer, folder:* parent_folder), never
    # a folder:* OBJECT on viewer, so no object-wildcard shape is needed. Declaring
    # {('folder','viewer')} would make this schema doubly-bridged (folder:*#viewer userset
    # + object-wildcard on the same shape) -- now compile-rejected as F1/F2
    # (docs/spec-deviations.md 2026-07-17).
    ruleset = parse_openfga_schema(schema)
    backend = V4WildcardBackend(ruleset.schema_info)

    # user:* views folder xyz; folder:* is the parent of doc1 -> everyone views doc1
    ingest_triple(backend, ruleset, RelationalTriple(Entity('user', '*'), 'viewer', Entity('folder', 'xyz'), Ellipsis))
    ingest_triple(backend, ruleset, RelationalTriple(Entity('folder', '*'), 'parent_folder', Entity('document', 'doc1'), Ellipsis))

    assert backend.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'doc1') is True
    assert backend.check_reachable(..., 'user', 'ghost', 'viewer', 'document', 'doc1') is True
    backend.teardown()


def test_integration_wildcard_object_all_folders():
    schema = '''
    model
      schema 1.1

    type user

    type folder
      relations
        define parent: [folder]
        define viewer: [user] or viewer from parent

    type document
      relations
        define parent: [folder]
        define viewer: [user] or viewer from parent
    '''
    ruleset = parse_openfga_schema(schema,
                                   object_wildcard_shapes={('folder', 'viewer'), ('document', 'viewer')})
    backend = V4WildcardBackend(ruleset.schema_info)

    # alice views ALL folders (object wildcard); f1 is parent of d -> alice views d
    ingest_triple(backend, ruleset, RelationalTriple(Entity('user', 'alice'), 'viewer', Entity('folder', '*'), Ellipsis))
    ingest_triple(backend, ruleset, RelationalTriple(Entity('folder', 'f1'), 'parent', Entity('document', 'd'), Ellipsis))

    assert backend.check_reachable(..., 'user', 'alice', 'viewer', 'document', 'd') is True
    assert backend.check_reachable(..., 'user', 'alice', 'viewer', 'folder', 'ghost_folder') is True   # probe 3
    assert backend.check_reachable(..., 'user', 'bob', 'viewer', 'document', 'd') is False
    backend.teardown()
