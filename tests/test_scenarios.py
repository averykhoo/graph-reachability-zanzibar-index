"""
Run the handwritten declarative scenarios (spec §7.2) against the set engine (both
SetOps) AND the oracle. The hand-computed expectation, the oracle, and the set engine
must all agree -- three independent sources pinned together.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from tests.oracle import Oracle, OracleTuple
from tests.scenarios import SCENARIOS
from setengine import SetEngine, ALL_SETOPS


def _ids(scn):
    return scn['name']


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
@pytest.mark.parametrize('scn', SCENARIOS, ids=_ids)
def test_scenario(scn, ops):
    schema = scn['schema']
    object_wc = frozenset(scn.get('object_wildcard_shapes', frozenset()))

    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    se = SetEngine(session, 'scn', schema, object_wildcard_shapes=object_wc, ops=ops)
    for op in scn['ops']:
        se.add_tuple(*op)
    session.commit()

    oracle = Oracle(schema, [OracleTuple(*op) for op in scn['ops']])

    for *query, expected in scn['expect']:
        q = tuple(query)
        got_set = se.check(*q)
        got_oracle = oracle.check(*q)
        assert got_set is expected, f'{scn["name"]} [{ops.name}] set engine {q}: {got_set} != {expected}'
        assert got_oracle is expected, f'{scn["name"]} oracle {q}: {got_oracle} != {expected}'
    session.close()
