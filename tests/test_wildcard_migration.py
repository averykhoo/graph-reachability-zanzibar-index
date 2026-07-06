"""
Schema-migration test for WildcardIndex.backfill() (spec §7.2).

Simulates a timeline: a store is populated with many concrete userset nodes while the
schema declares NO wildcard, then the schema is migrated to declare a subject-wildcard
shape. backfill() must back-propagate the bridges onto every pre-existing concrete node,
restoring the structural invariants -- without failing.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from index_v4 import ReachabilityIndex, Store, WildcardIndex
from zanzibar_utils_v1 import SchemaInfo
from tests.wildcard_helpers import assert_wildcard_invariants


@pytest.mark.parametrize('n', [500])
def test_backfill_migrates_existing_concretes(n):
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Store(id='m'))
    session.commit()
    idx = ReachabilityIndex(session, 'm')

    # --- v1: schema declares NO wildcard; build n concrete group#member nodes ---
    w1 = WildcardIndex(idx, SchemaInfo())
    w1.backfill()                                  # no-op on empty store
    for i in range(n):
        w1.add_tuple('...', 'user', f'u{i}', 'member', 'group', f'g{i}')
    session.commit()
    assert_wildcard_invariants(w1)                 # no bridges expected, and none exist

    # --- migrate: schema now declares group:*#member -> bridged-in shape (group, member) ---
    info_v2 = SchemaInfo(subject_wildcard_shapes=frozenset({('group', 'member')}))
    w2 = WildcardIndex(idx, info_v2)

    # Before backfill the pre-existing concretes lack their concrete->w_any bridges, so the
    # bridge-completeness invariant must fail -- proving backfill has real work to do.
    with pytest.raises(AssertionError):
        assert_wildcard_invariants(w2)

    # --- backfill: back-propagate bridges onto all n existing nodes ---
    w2.backfill()
    session.commit()
    assert_wildcard_invariants(w2)                 # every concrete now has its bridge

    # spot-check the actual bridge edges for a sample of the migrated nodes
    w_any = idx.node('member', 'group', '*', create_if_missing=False, implicit=True, wildcard='any')
    for i in (0, n // 2, n - 1):
        gi = idx.node('member', 'group', f'g{i}', create_if_missing=False)
        assert idx.direct_edge_exists_by_id(gi.id, w_any.id), f'g{i}#member missing bridge to w_any'

    # backfill is idempotent: calling it again changes nothing and stays valid
    w2.backfill()
    session.commit()
    assert_wildcard_invariants(w2)
    session.close()
