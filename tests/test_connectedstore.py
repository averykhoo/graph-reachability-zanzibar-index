"""
S3 (connected-store spec §5-S3): the ConnectedStore, sync schedule.

  * randomized walks on the boolean fixture: after every accepted write, the store's
    index-served checks ≡ the oracle ≡ its own set engine over the full grid, with
    graph invariants + I9 fixpoint audited per op;
  * one logical write is one transaction across BOTH halves: a failure after the
    source half landed rolls back tuple, log, index, and cursor together, and the
    in-memory evaluator self-heals;
  * the cursor rides the log head in sync mode; duplicate adds stay idempotent.
"""

import random

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from connectedstore import ConnectedStore, TupleLogV1, log_rows
from index_v4.invariants import install_paranoia, snapshot_rows
from setengine import TupleV1
from tests.oracle import Oracle, OracleTuple
from tests.test_matrix import _boolean_pool, _boolean_grid
from tests.wildcard_helpers import assert_wildcard_invariants


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _open(session, load_fga_schema, fixture='boolean_wildcards.fga', store='cs'):
    cs = ConnectedStore(session, store, schema=load_fga_schema(fixture))
    install_paranoia(session, store, cs.widx.schema_info)
    return cs


def _full_state(session, store_id, widx):
    """Row multisets across BOTH halves (ids ignored), for cross-half atomicity."""
    tuples = frozenset(
        (r.subject_predicate, r.subject_type, r.subject_name,
         r.relation, r.object_type, r.object_name)
        for r in session.exec(select(TupleV1).where(TupleV1.store_id == store_id)).all())
    log = tuple((r.op, r.subject_name, r.relation, r.object_name)
                for r in session.exec(select(TupleLogV1)
                                      .where(TupleLogV1.store_id == store_id)
                                      .order_by(TupleLogV1.id)).all())
    return tuples, log, snapshot_rows(session, store_id)


@pytest.mark.parametrize('seed', [0, 1])
def test_connected_store_parity_walk(session, load_fga_schema, seed):
    schema = load_fga_schema('boolean_wildcards.fga')
    cs = _open(session, load_fga_schema)

    pool = _boolean_pool()
    grid = _boolean_grid()
    rng = random.Random(seed)
    present, history = set(), []

    for _ in range(14):
        if not present or rng.random() < 0.6:
            cands = [r for r in pool if r not in present]
            op, raw = ('add', rng.choice(cands)) if cands else ('remove', rng.choice(sorted(present)))
        else:
            op, raw = 'remove', rng.choice(sorted(present))

        try:
            (cs.add_tuple if op == 'add' else cs.remove_tuple)(*raw)
        except ValueError:
            continue                                   # rejected: nothing landed anywhere
        (present.add if op == 'add' else present.discard)(raw)
        history.append((op, raw))

        # sync schedule: the cursor rides the head
        assert cs.cursor.applied_log_id == cs.watermark()

        assert_wildcard_invariants(cs.widx)
        if cs.proc is not None:
            cs.proc.audit_fixpoint()

        oracle = Oracle(schema, [OracleTuple(*r) for r in present])
        for q in grid:
            expected = oracle.check(*q)
            got_index = cs.check(*q)
            got_source = cs.source.check(*q)
            if not (got_index == got_source == expected):
                pytest.fail(f'seed={seed} q={q} index={got_index} source={got_source} '
                            f'oracle={expected}\n'
                            + '\n'.join(f'  {o} {r}' for o, r in history))


def test_write_is_atomic_across_both_halves(session, load_fga_schema):
    """A hard failure AFTER the source half landed must roll back tuple, log, index,
    and cursor together -- and the store must remain consistent and usable."""
    cs = _open(session, load_fga_schema)
    cs.add_tuple('...', 'user', '*', 'public', 'doc', 'd1')
    before = _full_state(session, 'cs', cs.widx)
    before_cursor = cs.cursor.applied_log_id

    def boom(wm):
        raise RuntimeError('injected index-half failure')

    original = cs.proc.run_cascade
    cs.proc.run_cascade = boom
    with pytest.raises(RuntimeError, match='injected'):
        cs.add_tuple('...', 'user', 'u1', 'blocked', 'doc', 'd1')
    cs.proc.run_cascade = original

    assert _full_state(session, 'cs', cs.widx) == before
    assert cs.cursor.applied_log_id == before_cursor
    # the in-memory evaluator self-healed from the rolled-back ground truth
    assert cs.source.check('...', 'user', 'u1', 'blocked', 'doc', 'd1') is False
    assert cs.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1') is True

    # and the store still works end to end
    cs.add_tuple('...', 'user', 'u1', 'blocked', 'doc', 'd1')
    assert cs.check('...', 'user', 'u1', 'viewer', 'doc', 'd1') is False


def test_rejected_write_lands_nowhere(session, load_fga_schema):
    cs = _open(session, load_fga_schema)
    cs.add_tuple('member', 'group', 'g1', 'member', 'group', 'g2')
    before = _full_state(session, 'cs', cs.widx)

    with pytest.raises(ValueError):                    # userset cycle (admission)
        cs.add_tuple('member', 'group', 'g2', 'member', 'group', 'g1')
    with pytest.raises(ValueError):                    # undeclared restriction
        cs.add_tuple('...', 'martian', 'zork', 'viewer', 'doc', 'd1')

    assert _full_state(session, 'cs', cs.widx) == before


def test_rejected_write_skips_evaluator_rebuild(session, load_fga_schema):
    """An ordinary admission rejection (ValueError) leaves the in-memory evaluator
    untouched (the set engine validates before mutating), so the O(N) rebuild is
    reserved for failures past admission -- a burst of invalid writes must not go
    quadratic (review 3)."""
    cs = _open(session, load_fga_schema)
    cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')

    calls = []
    original = cs.source.refresh_evaluator
    cs.source.refresh_evaluator = lambda: calls.append(1) or original()
    with pytest.raises(ValueError):
        cs.add_tuple('...', 'martian', 'zork', 'viewer', 'doc', 'd1')
    with pytest.raises(ValueError):
        cs.remove_tuple('...', 'user', 'ghost', 'editor', 'doc', 'd1')
    cs.source.refresh_evaluator = original
    assert calls == []

    # the evaluator is still coherent with the (unchanged) ground truth
    assert cs.source.check('...', 'user', 'u1', 'editor', 'doc', 'd1') is True
    assert cs.check('...', 'user', 'u1', 'editor', 'doc', 'd1') is True


def test_duplicate_add_through_store_is_idempotent(session, load_fga_schema):
    cs = _open(session, load_fga_schema)
    t1 = cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    t2 = cs.add_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    assert t2 == t1
    assert len(log_rows(session, 'cs')) == 1

    cs.remove_tuple('...', 'user', 'u1', 'editor', 'doc', 'd1')
    assert cs.check('...', 'user', 'u1', 'viewer', 'doc', 'd1') is False
    assert cs.check('...', 'user', 'u1', 'editor', 'doc', 'd1') is False


def test_fresh_token_reads_served_by_index(session, load_fga_schema):
    """Sync schedule: every returned token is immediately satisfied by the index."""
    cs = _open(session, load_fga_schema)
    token = cs.add_tuple('...', 'user', '*', 'public', 'doc', 'd1')
    assert cs.check('...', 'user', 'ghost', 'viewer', 'doc', 'd1', at_least=token) is True
    assert cs.cursor.applied_log_id >= token


def test_reopen_is_self_describing(session, load_fga_schema):
    """A second ConnectedStore on the same (session, store_id) needs no schema and
    sees the same state."""
    cs = _open(session, load_fga_schema)
    cs.add_tuple('...', 'user', 'u2', 'editor', 'doc', 'd1')

    reopened = ConnectedStore(session, 'cs')
    assert reopened.check('...', 'user', 'u2', 'viewer', 'doc', 'd1') is True
    assert reopened.cursor.applied_log_id == cs.cursor.applied_log_id
