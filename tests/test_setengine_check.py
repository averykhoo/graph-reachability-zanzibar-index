"""
P4 evaluator correctness: SetEngine.check vs the reference oracle over the full query
grid after randomized op sequences (spec §6.3), under both SetOps implementations.

This is the set-engine analogue of test_wildcard_property (which checks the graph index
against the oracle); it reuses the same universe, candidate pool, and grid.
"""

import random

import pytest
from sqlmodel import Session, SQLModel, create_engine

from tests.oracle import Oracle, OracleTuple
from tests.test_wildcard_property import _candidate_raw_tuples, _query_grid, OBJECT_WC
from setengine import SetEngine, ALL_SETOPS


def _fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
@pytest.mark.parametrize('seed', [0, 1, 2, 3, 4])
def test_setengine_check_vs_oracle(load_fga_schema, ops, seed):
    schema = load_fga_schema('wildcards.fga')
    session = _fresh_session()
    se = SetEngine(session, 'st', schema, object_wildcard_shapes=OBJECT_WC, ops=ops)

    pool = _candidate_raw_tuples()
    grid = _query_grid()
    rng = random.Random(seed)
    present: set = set()
    history: list = []

    for _ in range(14):
        if not present or rng.random() < 0.6:
            candidates = [r for r in pool if r not in present]
            op, raw = ('add', rng.choice(candidates)) if candidates else ('remove', rng.choice(sorted(present)))
        else:
            op, raw = 'remove', rng.choice(sorted(present))

        try:
            (se.add_tuple if op == 'add' else se.remove_tuple)(*raw)
            session.commit()
        except ValueError:
            session.rollback()
            continue

        (present.add if op == 'add' else present.discard)(raw)
        history.append((op, raw))

        oracle = Oracle(schema, [OracleTuple(*r) for r in present])
        for q in grid:
            got = se.check(*q)
            exp = oracle.check(*q)
            if got != exp:
                pytest.fail(
                    f'check mismatch seed={seed} ops={ops.name}\n'
                    f'history:\n' + '\n'.join(f'  {o} {r}' for o, r in history) +
                    f'\nquery: {q}\nset={got} oracle={exp}')
    session.close()
