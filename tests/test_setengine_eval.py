"""
P4 tests (spec §6.3-6.5): expand/lookup correctness and open-replay equivalence.

  * expand ≡ check: for every entity/star grid subject, MemberSet membership agrees
    with pointwise check (which is already validated against the oracle);
  * open-replay equivalence: check answers over a grid are identical after discarding
    the engine and rebuilding from the TupleV1 table (§6.5);
  * lookup / lookup_reverse hand-computed scenarios.
"""

import random

import pytest
from sqlmodel import Session, SQLModel, create_engine

from tests.test_wildcard_property import _candidate_raw_tuples, _query_grid, OBJECT_WC
from setengine import SetEngine, ALL_SETOPS
from setengine.setops import PySets


def _fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _memberset_contains(se, m, s_pred, s_type, s_name) -> bool:
    if s_name == '*':
        return m.contains_star((s_type, s_pred))
    sid = se.interner.get(s_type, s_name, s_pred)
    # ghost (never interned): use an unused non-negative id (roaring ids are uint32)
    uid = sid if sid is not None else max(se.interner.key_of, default=0) + 1000
    if s_pred == '...':
        return m.contains_entity(uid, s_type)
    return m.contains_userset(uid, (s_type, s_pred))


# ---------------------------------------------------------------------------
# expand ≡ check (entity + star subjects; userset subjects aren't MemberSet-representable)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
@pytest.mark.parametrize('seed', [0, 1, 2])
def test_expand_agrees_with_check(load_fga_schema, ops, seed):
    schema = load_fga_schema('wildcards.fga')
    session = _fresh_session()
    se = SetEngine(session, 'st', schema, object_wildcard_shapes=OBJECT_WC, ops=ops)

    pool = _candidate_raw_tuples()
    grid = _query_grid()
    rng = random.Random(seed)
    present = set()
    for _ in range(14):
        raw = rng.choice(pool)
        try:
            if raw in present:
                se.remove_tuple(*raw); present.discard(raw)
            else:
                se.add_tuple(*raw); present.add(raw)
            session.commit()
        except ValueError:
            session.rollback()

    # group grid queries by (relation, o_type, o_name); expand once, compare all subjects
    from collections import defaultdict
    by_obj = defaultdict(list)
    for (sp, st, sn, rel, ot, on) in grid:
        by_obj[(rel, ot, on)].append((sp, st, sn))
    for (rel, ot, on), subjects in by_obj.items():
        m = se.expand(rel, ot, on)
        for (sp, st, sn) in subjects:
            if sp != '...' and sn != '*':
                continue                     # userset subjects: not MemberSet-representable
            got = _memberset_contains(se, m, sp, st, sn)
            exp = se.check(sp, st, sn, rel, ot, on)
            assert got == exp, f'expand≠check for {(sp,st,sn)} on {(rel,ot,on)}: {got} vs {exp}'
    session.close()


# ---------------------------------------------------------------------------
# Open-replay equivalence (§6.5)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('seed', [0, 1, 2])
def test_open_replay_equivalence_answers(load_fga_schema, seed):
    schema = load_fga_schema('wildcards.fga')
    session = _fresh_session()
    se = SetEngine(session, 'st', schema, object_wildcard_shapes=OBJECT_WC, ops=PySets)

    pool = _candidate_raw_tuples()
    grid = _query_grid()
    rng = random.Random(seed)
    present = set()
    for _ in range(16):
        raw = rng.choice(pool)
        try:
            if raw in present:
                se.remove_tuple(*raw); present.discard(raw)
            else:
                se.add_tuple(*raw); present.add(raw)
            session.commit()
        except ValueError:
            session.rollback()

    before = {q: se.check(*q) for q in grid}
    se.rebuild()                              # discard state, replay from TupleV1
    after = {q: se.check(*q) for q in grid}
    assert before == after
    session.close()


# ---------------------------------------------------------------------------
# lookup / lookup_reverse scenarios
# ---------------------------------------------------------------------------

def test_lookup_reverse_markers_and_concretes(load_fga_schema):
    schema = load_fga_schema('wildcards.fga')
    session = _fresh_session()
    se = SetEngine(session, 'st', schema, object_wildcard_shapes=OBJECT_WC, ops=PySets)
    for t in [('...', 'user', 'alice', 'member', 'group', 'g1'),
              ('member', 'group', 'g1', 'viewer', 'document', 'd1'),
              ('...', 'user', '*', 'viewer', 'document', 'd1')]:
        se.add_tuple(*t)
    session.commit()

    lr = se.lookup_reverse('viewer', 'document', 'd1')
    keys = {se.interner.key(i) for i in lr.node_ids}
    # user:* grant -> a marker, not enumerated concretes
    assert ('user', '...') in lr.markers
    # the granted group userset is a concrete reacher
    assert ('group', 'g1', 'member') in keys
    session.close()


def test_lookup_forward(load_fga_schema):
    schema = load_fga_schema('wildcards.fga')
    session = _fresh_session()
    se = SetEngine(session, 'st', schema, object_wildcard_shapes=OBJECT_WC, ops=PySets)
    for t in [('...', 'user', 'alice', 'member', 'group', 'g1'),
              ('member', 'group', 'g1', 'viewer', 'document', 'd1')]:
        se.add_tuple(*t)
    session.commit()

    lk = se.lookup('...', 'user', 'alice')
    keys = {se.interner.key(i) for i in lk.node_ids}
    assert ('group', 'g1', 'member') in keys       # alice is a member of g1
    assert ('document', 'd1', 'viewer') in keys    # ...and thereby a viewer of d1
    session.close()
