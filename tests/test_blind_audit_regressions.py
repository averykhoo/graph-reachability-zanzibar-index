"""
Blind-audit regression pins (docs/spec-deviations.md, blind-audit entry).

One test (or small group) per confirmed finding, each carrying the auditor's
original repro where one existed. Grouped:

  * memo poisoning under the recursion guard (oracle + set engine + expand);
  * '*'-subject flow-through semantics (D1), 3-way agreed;
  * userset-subject exclusion poisoning -> edge-free upos residues (P4/D2);
  * core hygiene: remove_node neighbour refcounts (C1/I13), dead-id TOCTOU
    surface (C2), self-edge rejection (C3);
  * parser hardening, production AND the oracle's independent mirror (S-1/O4);
  * tupleset restriction scope (D3) + derived TTU-target object wildcards (D4);
  * connected-store transaction hygiene (X2 idle rollback, X3 ctor commit);
  * ParityEngine constructibility on cyclic boolean schemas (X7).
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from index_v4 import ReachabilityIndex, NodeV4
from index_v4.models import StoreV4
from index_v4.invariants import check_invariants
from setengine import SetEngine, ALL_SETOPS
from zanzibar_utils_v1 import (Entity, RelationalTriple, UnsupportedByGraphIndex,
                               parse_openfga_schema, parse_schema_ast)
from tests.oracle import Oracle, OracleTuple
from tests.oracle import _tokenize as oracle_tokenize
from tests.oracle import _parse_restrictions as oracle_parse_restrictions
from tests.parity import ParityEngine
from tests.wildcard_helpers import make_wildcard_index


def _fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


# --------------------------------------------------------------------------- #
# Memo poisoning under the recursion guard (oracle + set engine)
# --------------------------------------------------------------------------- #

_CYCLIC_ORACLE_SCHEMA = '''
type user
type doc
  relations
    define a: x or [user]
    define x: a
    define r: a and x
    define r2: a but not x
'''


def test_oracle_memo_not_poisoned_by_revisit_guard():
    """Auditor repro: `x` consults in-stack `a` (guard -> provisional False); the
    old code memoized that provisional result, so `r = a and x` answered False
    while `a` and `x` each answered True -- internally inconsistent."""
    o = Oracle(_CYCLIC_ORACLE_SCHEMA,
               [OracleTuple('...', 'user', 'alice', 'a', 'doc', 'd1')])
    q = lambda rel: o.check('...', 'user', 'alice', rel, 'doc', 'd1')
    assert q('a') is True
    assert q('x') is True
    assert q('r') is True            # a and x: both True above
    assert q('r2') is False          # a but not x


_CYCLIC_SET_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define reader: [group#member]
    define editor: [group#member]
    define can_view: reader and editor
    define x2: [user] and y2
    define y2: [user] and x2
'''

_CYCLIC_SET_TUPLES = [
    ('member', 'group', 'A', 'member', 'group', 'B'),
    ('...', 'user', 'alice', 'member', 'group', 'C'),
    ('member', 'group', 'C', 'member', 'group', 'A'),
    ('member', 'group', 'B', 'member', 'group', 'A'),
    ('member', 'group', 'A', 'reader', 'doc', 'd'),
    ('member', 'group', 'B', 'editor', 'doc', 'd'),
]


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_setengine_memo_not_poisoned_by_revisit_guard(ops):
    """Auditor repro: a group-membership cycle (A->B->A, alice in C->A) made a
    frame's provisional in-cycle result stick in the memo; `can_view = reader and
    editor` then disagreed with its own conjuncts."""
    session = _fresh_session()
    se = SetEngine(session, 't', _CYCLIC_SET_SCHEMA, ops=ops)
    for raw in _CYCLIC_SET_TUPLES:
        se.add_tuple(*raw)
    session.commit()

    r = se.check('...', 'user', 'alice', 'reader', 'doc', 'd')
    e = se.check('...', 'user', 'alice', 'editor', 'doc', 'd')
    cv = se.check('...', 'user', 'alice', 'can_view', 'doc', 'd')
    assert r is True and e is True
    assert cv == (r and e), 'can_view disagrees with its own conjuncts'

    # the expand path shares the memo scheme -- same guard, same pin
    res = se.lookup_reverse('can_view', 'doc', 'd')
    assert res.node_ids, 'expand lost the membership check confirmed'
    session.close()


def test_parity_engine_constructible_on_cyclic_boolean_schema():
    """X7: cyclic derived dependencies raise ValueError (not
    UnsupportedByGraphIndex) at graph compile; ParityEngine must degrade to
    3-way instead of failing to construct -- this was exactly the schema class
    where the memo bug lived, so the matrix was blind to it."""
    pe = ParityEngine(_CYCLIC_SET_SCHEMA, grid_cap=200)
    assert pe.graph is None          # graph refused (cycle), set engines + oracle live
    for raw in _CYCLIC_SET_TUPLES:
        assert pe.add_tuple(*raw) is True    # grid parity asserted per op inside
    assert pe.check('...', 'user', 'alice', 'can_view', 'doc', 'd') is True
    pe.close()


# --------------------------------------------------------------------------- #
# D1: '*'-subject queries are flow-through (resolve through granted usersets)
# --------------------------------------------------------------------------- #

_STAR_FLOW_SCHEMA = '''
type user
type group
  relations
    define member: [user, user:*]
type doc
  relations
    define viewer: [user, group#member]
'''


def test_star_subject_flows_through_granted_usersets_3way():
    """D1 (semantic decision): `check(user:* viewer doc:d)` where user:* is a
    member of a granted userset answers True on ALL backends -- the OpenFGA
    literal-subject reading. The live bug: graph said True, oracle/set said
    False (per-branch-only), a standing 3-way divergence."""
    tuples = [
        ('member', 'group', 'g', 'viewer', 'doc', 'd'),
        ('...', 'user', '*', 'member', 'group', 'g'),
    ]
    star_q = ('...', 'user', '*', 'viewer', 'doc', 'd')
    ghost_q = ('...', 'user', 'ghost', 'viewer', 'doc', 'd')

    answers = {}
    oracle = Oracle(_STAR_FLOW_SCHEMA, [OracleTuple(*t) for t in tuples])
    answers['oracle'] = (oracle.check(*star_q), oracle.check(*ghost_q))

    for ops in ALL_SETOPS:
        session = _fresh_session()
        se = SetEngine(session, 't', _STAR_FLOW_SCHEMA, ops=ops)
        for t in tuples:
            se.add_tuple(*t)
        session.commit()
        answers[f'set:{ops.name}'] = (se.check(*star_q), se.check(*ghost_q))
        session.close()

    rs = parse_openfga_schema(_STAR_FLOW_SCHEMA)
    session, widx = make_wildcard_index(rs.schema_info)
    for (sp, st, sn, r, ot, on) in tuples:
        trip = RelationalTriple(Entity(st, sn), r, Entity(ot, on),
                                Ellipsis if sp == '...' else sp)
        for d in rs.apply(trip):
            widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                           d.subject.type, d.subject.name,
                           d.relation, d.object.type, d.object.name)
    session.commit()
    answers['graph'] = (widx.check(*star_q), widx.check(*ghost_q))
    session.close()

    assert all(v == (True, True) for v in answers.values()), answers


# --------------------------------------------------------------------------- #
# P4/D2: userset subjects on derived relations are edge-free (upos)
# --------------------------------------------------------------------------- #

_USERSET_EXCLUSION_SCHEMA = '''
type user
type group
  relations
    define member: [user]
type doc
  relations
    define a: [user, group#member]
    define b: [user]
    define perm: a but not b
'''


def test_userset_edge_does_not_poison_member_exclusions():
    """Auditor repro: with `group:g#member` granted `a` and bob both a member of
    g AND in `b`, a derived EDGE from the userset node would leak `perm` to bob
    through the closure, past his own exclusion. ParityEngine runs the real
    write path (RuleSet.apply + cascade) and pins every backend to the oracle."""
    pe = ParityEngine(_USERSET_EXCLUSION_SCHEMA, grid_cap=300)
    assert pe.graph is not None      # boolean schema, 4-way
    pe.add_tuple('...', 'user', 'bob', 'member', 'group', 'g')
    pe.add_tuple('member', 'group', 'g', 'a', 'doc', 'x')
    pe.add_tuple('...', 'user', 'bob', 'b', 'doc', 'x')

    assert pe.check('...', 'user', 'bob', 'perm', 'doc', 'x') is False
    # the exact-userset-granted reading: the userset subject itself holds perm
    # (a=True via its own grant, b=False -- a userset can't be in b)
    assert pe.check('member', 'group', 'g', 'perm', 'doc', 'x') is True
    pe.close()


# --------------------------------------------------------------------------- #
# C1/C2/C3: core hygiene
# --------------------------------------------------------------------------- #

def _core_index():
    session = _fresh_session()
    session.add(StoreV4(id='t'))
    session.commit()
    return session, ReachabilityIndex(session, 't')


def test_remove_node_decrements_neighbour_refcounts():
    """C1: the node-removal shortcut retires incident direct edges by count math;
    before the fix the neighbours' reference_counts stayed inflated forever
    (defeating implicit GC). I13 (refcount == direct-edge degree) now audits it."""
    session, idx = _core_index()
    idx.add_edge('...', 'user', 'alice', 'viewer', 'doc', 'd1')
    session.commit()

    idx.remove_node('...', 'user', 'alice')
    session.commit()
    # the implicit neighbour's refcount honestly hit zero -> implicit GC
    assert session.exec(select(NodeV4)).all() == []
    check_invariants(session, 't')   # includes I13
    session.close()


def test_add_edge_by_id_rejects_dead_ids():
    """C2: id-based writes re-verify both endpoints inside the store lock; a stale
    id (concurrent removal) raises ValueError instead of writing a dangling edge."""
    session, idx = _core_index()
    idx.add_edge('...', 'user', 'a', 'viewer', 'doc', 'd')
    session.commit()
    with pytest.raises(ValueError, match='no longer exists'):
        idx.add_edge_by_id(99991, 99992)
    session.close()


def test_self_edge_rejected_as_cycle():
    """C3: subject == object is a 1-cycle; the acyclicity bijection's precondition
    makes it a ValueError, not a silent self-loop write."""
    session, idx = _core_index()
    idx.add_edge('...', 'user', 'a', 'viewer', 'doc', 'd')
    with pytest.raises(ValueError, match='cycle'):
        idx.add_edge('...', 'user', 'a', '...', 'user', 'a')
    session.close()


# --------------------------------------------------------------------------- #
# S-1/O4: parser hardening -- production and the oracle's independent mirror
# --------------------------------------------------------------------------- #

def test_production_parser_rejects_stray_bracket_without_hanging():
    with pytest.raises(ValueError):
        parse_schema_ast('type user\ntype doc\n  relations\n'
                         '    define v: [user]]\n')


def test_production_parser_rejects_double_hash():
    with pytest.raises(ValueError):
        parse_schema_ast('type user\ntype group\n  relations\n'
                         '    define member: [user]\ntype doc\n  relations\n'
                         '    define v: [group#member#x]\n')


def test_oracle_tokenizer_rejects_stray_bracket_without_hanging():
    """O4: the oracle's own tokenizer had the same zero-progress loop on a stray
    ']' -- the word branch scanned zero characters forever."""
    with pytest.raises(ValueError, match='unmatched'):
        oracle_tokenize('[user]]')


def test_oracle_restrictions_reject_double_hash():
    with pytest.raises(ValueError, match='malformed'):
        oracle_parse_restrictions('[group#member#x]')
    with pytest.raises(ValueError, match='malformed'):
        oracle_parse_restrictions('[group#]')


# --------------------------------------------------------------------------- #
# D3/D4: tupleset restriction scope
# --------------------------------------------------------------------------- #

def test_userset_restriction_in_tupleset_rejected():
    """D3: a userset restriction on a tupleset relation bypassed taint analysis
    (drop-the-predicate parent semantics no spec defines). OpenFGA model rule:
    tupleset relations must be directly assignable."""
    schema = '''
type user
type group
  relations
    define member: [user]
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder, group#member]
    define viewer: [user] or viewer from parent
'''
    with pytest.raises(UnsupportedByGraphIndex, match='userset'):
        parse_openfga_schema(schema)


def test_wildcard_tupleset_still_supported_with_derived_shape():
    """D3 scope check: star tuplesets are this repo's deliberate object-wildcard
    extension and stay accepted; the TTU rewrite's through-shape
    (parent_type, target_rel) is derived so the rewritten write resolves."""
    schema = '''
type user
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder, folder:*]
    define viewer: [user] or viewer from parent
'''
    rs = parse_openfga_schema(schema)
    assert ('folder', 'viewer') in rs.schema_info.subject_wildcard_shapes


def test_object_wildcard_on_derived_ttu_target_rejected():
    """D4 (decision-15 family): derived evaluation probes the closure directly
    and cannot see w_all state -- an object-wildcard grant on the TTU target of
    a tainted plan would be silently invisible, so compile rejects the shape."""
    schema = '''
type user
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder]
    define banned: [user]
    define viewer: viewer from parent but not banned
'''
    with pytest.raises(UnsupportedByGraphIndex, match='TTU target'):
        parse_openfga_schema(schema,
                             object_wildcard_shapes=frozenset({('folder', 'viewer')}))


# --------------------------------------------------------------------------- #
# X2/X3: connected-store transaction hygiene
# --------------------------------------------------------------------------- #

_CS_SCHEMA = '''
type user
type doc
  relations
    define viewer: [user]
'''


def test_connected_store_ctor_commits_bootstrap():
    """X3: the constructor persists schema source + store rows and COMMITS them;
    before the fix a reader opening a second session saw nothing until the first
    data write happened to commit."""
    from connectedstore import ConnectedStore
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s1:
        ConnectedStore(s1, 'cs', schema=_CS_SCHEMA)
        # a SECOND session sees the bootstrap without any tuple write
        with Session(engine) as s2:
            reopened = ConnectedStore(s2, 'cs')      # self-describing reopen
            assert reopened.check('...', 'user', 'u', 'viewer', 'doc', 'd') is False


def test_catch_up_idle_leaves_no_open_transaction():
    """X2: the zero-row catch_up path still opened a transaction (store lock +
    cursor refresh + log read) and left it open -- pinning the worker's read
    snapshot forever and, on PostgreSQL, holding the FOR UPDATE store lock."""
    from connectedstore import ConnectedStore
    session = _fresh_session()
    cs = ConnectedStore(session, 'cs', schema=_CS_SCHEMA)
    cs.add_tuple('...', 'user', 'u', 'viewer', 'doc', 'd')
    assert cs.catch_up() == 0                        # sync mode: already at head
    assert not session.in_transaction(), \
        'idle catch_up left a transaction open (pinned snapshot / held lock)'
    session.close()
