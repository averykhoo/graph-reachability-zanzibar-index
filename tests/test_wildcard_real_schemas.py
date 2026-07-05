"""
Correctness tests against the repo's real-world wildcard schemas (gdrive.fga,
master_store.fga). These use *bare* subject wildcards (`user:*`, `service-account:*`),
i.e. the common OpenFGA case: zero bridges, propagation entirely through computed
usersets and from-chains -- a different path than the bridged shapes the property test
stresses.

Each query is triangulated three ways: WildcardIndex.check == reference oracle ==
hand-computed expectation.
"""

from types import EllipsisType

from zanzibar_utils_v1 import Entity, RelationalTriple, parse_openfga_schema
from tests.oracle import Oracle, OracleTuple
from tests.wildcard_helpers import make_wildcard_index, assert_wildcard_invariants


def _norm(pred: str | EllipsisType) -> str:
    return '...' if pred is Ellipsis else pred


def _build(schema: str, raw_tuples, object_wildcard_shapes=frozenset()):
    ruleset = parse_openfga_schema(schema, object_wildcard_shapes=object_wildcard_shapes)
    session, widx = make_wildcard_index(ruleset.schema_info)
    for raw in raw_tuples:
        s_pred = Ellipsis if raw[0] == '...' else raw[0]
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), s_pred)
        for d in ruleset.apply(triple):
            widx.add_tuple(_norm(d.subject_predicate), d.subject.type, d.subject.name,
                           d.relation, d.object.type, d.object.name)
    session.commit()
    assert_wildcard_invariants(widx)
    oracle = Oracle(schema, [OracleTuple(*r) for r in raw_tuples])
    return session, widx, oracle


def _agree(widx, oracle, query, expected):
    got = widx.check(*query)
    exp = oracle.check(*query)
    assert got == exp, f'index/oracle disagree on {query}: index={got} oracle={exp}'
    assert got is expected, f'wrong result for {query}: got {got}, expected {expected}'


# ===========================================================================
# gdrive.fga: user:* viewer propagating through computed usersets + from-chains
# ===========================================================================

def test_gdrive_public_folder_propagates_to_child_doc(load_fga_schema):
    schema = load_fga_schema('gdrive.fga')
    raws = [
        ('...', 'user', '*', 'viewer', 'folder', 'root'),   # everyone views the root folder
        ('...', 'folder', 'root', 'parent', 'doc', 'd1'),   # root is the parent of doc d1
    ]
    session, widx, oracle = _build(schema, raws)

    # can_read on d1 = "viewer or owner or viewer from parent"; ghost views root -> reads d1
    _agree(widx, oracle, ('...', 'user', 'ghost', 'can_read', 'doc', 'd1'), True)
    # a concrete never-seen user behaves the same
    _agree(widx, oracle, ('...', 'user', 'alice', 'can_read', 'doc', 'd1'), True)
    # ghost is a direct viewer of the public folder
    _agree(widx, oracle, ('...', 'user', 'ghost', 'viewer', 'folder', 'root'), True)
    # but doc.viewer has NO "from parent" clause -> ghost is not a direct viewer of d1
    _agree(widx, oracle, ('...', 'user', 'ghost', 'viewer', 'doc', 'd1'), False)
    # can_write is owner-based (no user:* owner) -> ghost cannot write
    _agree(widx, oracle, ('...', 'user', 'ghost', 'can_write', 'doc', 'd1'), False)
    # unrelated doc is uncovered
    _agree(widx, oracle, ('...', 'user', 'ghost', 'can_read', 'doc', 'other'), False)
    session.close()


def test_gdrive_intensional_vs_extensional(load_fga_schema):
    schema = load_fga_schema('gdrive.fga')
    # two users granted individually, NO wildcard: intensional user:* query is False.
    raws = [
        ('...', 'user', 'alice', 'viewer', 'doc', 'd1'),
        ('...', 'user', 'bob', 'viewer', 'doc', 'd1'),
    ]
    session, widx, oracle = _build(schema, raws)
    _agree(widx, oracle, ('...', 'user', 'alice', 'viewer', 'doc', 'd1'), True)
    _agree(widx, oracle, ('...', 'user', '*', 'viewer', 'doc', 'd1'), False)   # intensional
    _agree(widx, oracle, ('...', 'user', 'ghost', 'viewer', 'doc', 'd1'), False)  # no wildcard grant
    session.close()


# ===========================================================================
# master_store.fga: wildcard group membership + computed-userset role chain + subgroup
# ===========================================================================

def test_master_store_wildcard_group_role_chain(load_fga_schema):
    schema = load_fga_schema('master_store.fga')
    raws = [
        ('...', 'user', '*', 'member', 'group', 'g1'),                 # every user is a member of g1
        ('member', 'group', 'g1', 'reader', 'store', 's1'),           # g1's members read s1
        ('...', 'service-account', '*', 'member', 'group', 'g2'),     # every service-account is in g2
        ('member', 'group', 'g2', 'checker', 'store', 's2'),          # g2's members check s2
        ('...', 'user', 'realuser', 'member', 'group', 'sub1'),       # realuser is a member of sub1
        ('...', 'group', 'sub1', 'subgroup', 'group', 'g1'),          # sub1 is a subgroup of g1
    ]
    session, widx, oracle = _build(schema, raws)

    # ghost user is a member of g1 (user:*) -> reads s1, and reader => checker
    _agree(widx, oracle, ('...', 'user', 'ghost', 'reader', 'store', 's1'), True)
    _agree(widx, oracle, ('...', 'user', 'ghost', 'checker', 'store', 's1'), True)
    # ...but reader does NOT imply writer
    _agree(widx, oracle, ('...', 'user', 'ghost', 'writer', 'store', 's1'), False)

    # service-account wildcard membership -> ghost service-account checks s2
    _agree(widx, oracle, ('...', 'service-account', 'ghost', 'checker', 'store', 's2'), True)
    # a user is NOT in g2 (that's the service-account wildcard), so no checker on s2
    _agree(widx, oracle, ('...', 'user', 'ghost', 'checker', 'store', 's2'), False)

    # subgroup from-chain: realuser -> sub1#member -> g1#member -> reader s1
    _agree(widx, oracle, ('...', 'user', 'realuser', 'reader', 'store', 's1'), True)

    # NO group:*#member wildcard is declared here, so a ghost group's #member userset
    # is not covered by any marker.
    _agree(widx, oracle, ('member', 'group', 'ghostgrp', 'reader', 'store', 's1'), False)
    session.close()
