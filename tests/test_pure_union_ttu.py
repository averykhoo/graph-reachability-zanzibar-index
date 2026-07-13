"""Pure-union TTU latent-gap fixture (P5 #3 — docs/spec-deviations.md).

Adjudicates the "pure-union latent gap": whether the graph index over-grants when a
TTU's tupleset relation gains members through a RULE-ROUTED / computed path rather than
raw stored tuples. Zanzibar/OpenFGA tupleset semantics (oracle-pinned) read STORED
tupleset tuples only — a computed member of the tupleset is NOT a TTU parent.

Shape under test (``linked`` is an *untainted* tupleset that also has a computed arm,
so ``f1`` becomes a member of ``linked`` on ``d1`` via ``backlink`` with no stored
``linked`` tuple)::

    type user
    type folder
      define viewer: [user]
    type doc
      define backlink: [folder]
      define linked:   [folder] or backlink     # untainted, rule-routed members
      define can_read: viewer from linked        # TTU over the rule-routed tupleset

Finding (2026-07-13): the divergence is UNREACHABLE on the graph. The graph rejects
this schema at compile time (``_validate_ttu_tuplesets`` → ``UnsupportedByGraphIndex``):
a rewrite rule only ever lands edges on the relation it DEFINES, so the only untainted
tuplesets that compile are directs-only, and those receive raw stored edges exclusively.
The set engine and oracle (both stored-only) accept the schema and agree it does NOT
grant ``can_read`` through the rule-routed path. Latent gap closed as benign — the guard
prevents the over-granting shape from ever materializing on the graph. See
docs/spec-deviations.md 2026-07-07 P5 #3 (resolution appended 2026-07-13).
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar_utils_v1 import parse_openfga_schema, UnsupportedByGraphIndex
from setengine import SetEngine, ALL_SETOPS
from tests.oracle import Oracle, OracleTuple
from tests.test_matrix import GraphBackend


# The rule-routed shape: `linked` is untainted yet has a computed arm (`or backlink`),
# so `f1` joins `linked` on `d1` via a stored `backlink` tuple, never a stored `linked`.
RULE_ROUTED_SCHEMA = """model
  schema 1.1

type user

type folder
  relations
    define viewer: [user]

type doc
  relations
    define backlink: [folder]
    define linked: [folder] or backlink
    define can_read: viewer from linked
"""

# The compilable sibling: `linked` is directs-only, so parents are raw stored tuples.
DIRECTS_ONLY_SCHEMA = """model
  schema 1.1

type user

type folder
  relations
    define viewer: [user]

type doc
  relations
    define linked: [folder]
    define can_read: viewer from linked
"""


def _fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


# ---------------------------------------------------------------------------
# 1. The graph closes the gap by REJECTING the rule-routed tupleset at compile
#    time — over-granting is unreachable because the schema never materializes.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('enable_boolean', [True, False])
def test_graph_rejects_rule_routed_untainted_tupleset(enable_boolean):
    with pytest.raises(UnsupportedByGraphIndex) as exc:
        parse_openfga_schema(RULE_ROUTED_SCHEMA, enable_boolean=enable_boolean)
    msg = str(exc.value)
    assert 'tupleset' in msg and 'linked' in msg


# ---------------------------------------------------------------------------
# 2. Stored-only TTU semantics: the set engine ACCEPTS the same schema (it reads
#    raw tuples) and, together with the oracle, refuses to grant through the
#    rule-routed path — no over-grant. A genuinely stored `linked` tuple DOES grant.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_stored_only_ttu_no_overgrant(ops):
    # f1 is a member of `linked` on d1 ONLY via the rule-routed `backlink` arm;
    # f2 is a member of `linked` on d1 via a genuinely STORED `linked` tuple.
    tuples = [
        ('...', 'user', 'u', 'viewer', 'folder', 'f1'),
        ('...', 'folder', 'f1', 'backlink', 'doc', 'd1'),   # rule-routed into `linked`
        ('...', 'user', 'u2', 'viewer', 'folder', 'f2'),
        ('...', 'folder', 'f2', 'linked', 'doc', 'd1'),     # stored `linked` parent
    ]

    oracle = Oracle(RULE_ROUTED_SCHEMA, [OracleTuple(*t) for t in tuples])

    session = _fresh_session()
    se = SetEngine(session, 'se', RULE_ROUTED_SCHEMA, ops=ops)
    for t in tuples:
        se.add_tuple(*t)
    session.commit()

    # rule-routed parent (f1 via backlink) must NOT grant can_read — stored-only.
    q_routed = ('...', 'user', 'u', 'can_read', 'doc', 'd1')
    assert oracle.check(*q_routed) is False
    assert se.check(*q_routed) is False

    # genuinely stored `linked` parent (f2) DOES grant — the TTU itself works.
    q_stored = ('...', 'user', 'u2', 'can_read', 'doc', 'd1')
    assert oracle.check(*q_stored) is True
    assert se.check(*q_stored) is True

    session.close()


# ---------------------------------------------------------------------------
# 3. On the compilable (directs-only) sibling, all three backends — graph, set
#    engine, oracle — agree: the only difference between grant and no-grant is a
#    STORED tupleset tuple, exactly the semantics the guard protects.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_directs_only_tupleset_all_backends_agree(ops):
    tuples = [
        ('...', 'user', 'u', 'viewer', 'folder', 'f1'),
        ('...', 'folder', 'f1', 'linked', 'doc', 'd1'),     # stored parent -> grant
        ('...', 'user', 'u3', 'viewer', 'folder', 'f3'),    # f3 never linked to d1 -> no grant
    ]

    oracle = Oracle(DIRECTS_ONLY_SCHEMA, [OracleTuple(*t) for t in tuples])

    session = _fresh_session()
    se = SetEngine(session, 'se', DIRECTS_ONLY_SCHEMA, ops=ops)
    graph = GraphBackend(DIRECTS_ONLY_SCHEMA)
    for t in tuples:
        se.add_tuple(*t)
        assert graph.apply(t, 'add'), f'graph rejected {t}'
    session.commit()
    graph.post_op()

    grid = [
        ('...', 'user', 'u', 'can_read', 'doc', 'd1'),      # via stored linked parent -> True
        ('...', 'user', 'u3', 'can_read', 'doc', 'd1'),     # no linked parent -> False
        ('...', 'folder', 'f1', 'linked', 'doc', 'd1'),     # stored tupleset membership -> True
        ('...', 'user', 'u', 'can_read', 'doc', 'd2'),      # unrelated object -> False
    ]
    for q in grid:
        o, s, g = oracle.check(*q), se.check(*q), graph.check(q)
        assert o == s == g, f'q={q} oracle={o} set={s} graph={g}'

    graph.close()
    session.close()
