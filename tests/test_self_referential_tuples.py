"""Self-referential tuples (subject entity == object entity) are SUPPORTED.

OpenFGA explicitly allows self-referential relationship tuples — it even has an
`IsSelfDefining` concept (e.g. `document:1#viewer@document:1#viewer`) — and the
documented idiom is the **self-defining / attribute-marker relation**: an object
points to *itself* on a relation to represent a boolean attribute ("activated",
"public", "archived", ...). We match that: a self-referential tuple is accepted
and evaluated correctly, on every backend, and (post-fix) add/remove of one is an
exact state round trip.

Refs: OpenFGA `tuple.IsSelfDefining`
(https://pkg.go.dev/github.com/openfga/openfga/pkg/tuple); Update Tuples /
Concepts docs (https://openfga.dev/docs/concepts).

This file pins two things:
  1. the self-defining "activated" flag pattern works across oracle + set engine
     + graph, and toggling the flag toggles a derived relation;
  2. the regression for the 2026-07-13 canonicalization bug (docs/spec-deviations.md):
     a self-referential TTU parent (`doc:d1 parent doc:d1`), where the object's own
     derived node doubles as a from-chain userset subject, used to leave a
     refcount-0 node with a stale `implicit` flag after add/remove. From-chain
     subject nodes are now interned NON-implicit (processor.py reconcile step 2a),
     so add/remove restores the exact materialized state.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from setengine import SetEngine, ALL_SETOPS
from tests.oracle import Oracle, OracleTuple
from tests.test_matrix import GraphBackend
from tests.test_hypothesis import build, _state


# --------------------------------------------------------------------------- #
# 1. The OpenFGA self-defining / attribute-marker pattern: a self-referential
#    tuple as a boolean flag, gating a derived (exclusion) relation.
# --------------------------------------------------------------------------- #

FLAG_SCHEMA = """model
  schema 1.1

type resource
  relations
    define activated: [resource]
    define deprecated: [resource]
    define usable: activated but not deprecated
"""


def _fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_self_defining_flag_gates_derived_relation(ops):
    """`resource:r1 activated resource:r1` is a self-referential attribute flag;
    `usable = activated but not deprecated` reads it. Oracle, set engine, and graph
    agree as the flag toggles."""
    q_usable = ('...', 'resource', 'r1', 'usable', 'resource', 'r1')
    q_active = ('...', 'resource', 'r1', 'activated', 'resource', 'r1')
    activated = ('...', 'resource', 'r1', 'activated', 'resource', 'r1')
    deprecated = ('...', 'resource', 'r1', 'deprecated', 'resource', 'r1')

    def check_all(tuples, expect_active, expect_usable):
        orc = Oracle(FLAG_SCHEMA, [OracleTuple(*t) for t in tuples])
        session = _fresh_session()
        se = SetEngine(session, 'se', FLAG_SCHEMA, ops=ops)
        graph = GraphBackend(FLAG_SCHEMA)
        for t in tuples:
            se.add_tuple(*t)
            assert graph.apply(t, 'add'), f'graph rejected {t}'
        session.commit()
        graph.post_op()
        for label, q, exp in (('activated', q_active, expect_active),
                              ('usable', q_usable, expect_usable)):
            o, s, g = orc.check(*q), se.check(*q), graph.check(q)
            assert o == s == g == exp, f'{label}: oracle={o} set={s} graph={g} expected={exp}'
        graph.close()
        session.close()

    check_all([], expect_active=False, expect_usable=False)              # no flag
    check_all([activated], expect_active=True, expect_usable=True)       # flag set
    check_all([activated, deprecated], expect_active=True, expect_usable=False)  # + deprecated


# --------------------------------------------------------------------------- #
# 2. Regression: a self-referential TTU parent round-trips on add/remove.
#    (The 2026-07-13 canonicalization bug — hypothesis-found.)
# --------------------------------------------------------------------------- #

TTU_SELF_PARENT_SCHEMA = """model
  schema 1.1

type user

type doc
  relations
    define parent: [doc]
    define r0: [user] and [user]
    define r4: r0 from parent or [user, user:*]
"""


def test_self_referential_ttu_parent_add_remove_restores():
    """With `doc:d1 parent doc:d1` present, adding then removing `u1 r0 d1` must
    restore the EXACT materialized state (rows + residues), keep `check` correct,
    and leave a valid fixpoint. Before the fix, the object's derived node
    `(r0,doc,d1)` — which doubles as the from-chain userset subject `doc:d1#r0` in
    `r4@d1`'s residue — was left refcount-0 with a stale `implicit=False` flag."""
    self_parent = ('...', 'doc', 'd1', 'parent', 'doc', 'd1')
    grant = ('...', 'user', 'u1', 'r0', 'doc', 'd1')

    session, widx, proc, write = build(TTU_SELF_PARENT_SCHEMA)
    write('add', self_parent)

    before = _state(session, widx)
    write('add', grant)
    write('remove', grant)
    after = _state(session, widx)

    # exact state restoration (the property that was violated)
    assert after == before, 'add/remove of the grant did not restore the state'
    # valid fixpoint
    proc.audit_fixpoint()
    # answers correct (u1 was removed; r0/r4 deny; the from-chain userset holds)
    assert widx.check('...', 'user', 'u1', 'r0', 'doc', 'd1') is False
    assert widx.check('...', 'user', 'u1', 'r4', 'doc', 'd1') is False
    assert widx.check('r0', 'doc', 'd1', 'r4', 'doc', 'd1') is True   # from-chain identity
    session.close()

    # driven state equals a fresh add-only build (canonical form)
    s2, w2, _p2, wr2 = build(TTU_SELF_PARENT_SCHEMA)
    wr2('add', self_parent)
    assert after == _state(s2, w2), 'post-remove state diverges from a fresh build'
    s2.close()
