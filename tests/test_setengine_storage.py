"""
P3 tests (spec §5, §6.1-6.2): set-engine storage, writes, validation, and replay.

  * replay-equivalence: state rebuilt from the TupleV1 table equals the live state;
  * accept/reject parity vs the graph backend over randomized op sequences (including
    the cycles the graph rejects -- group-membership and from-chain);
  * type-restriction validity ([user] rejects user:*, undeclared object wildcards, etc.).
"""

import random

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from zanzibar_utils_v1 import parse_openfga_schema, Entity, RelationalTriple
from setengine import SetEngine, TupleV1, ALL_SETOPS
from setengine.setops import PySets
from tests.wildcard_helpers import make_wildcard_index

# Reuse the property harness's universe + candidate pool (spec §7.1: extend, don't rewrite).
from tests.test_wildcard_property import _candidate_raw_tuples, OBJECT_WC


def _fresh_session() -> Session:
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)      # creates tuple_v1 + graph tables
    return Session(engine)


def _make_engine(session, schema, ops):
    return SetEngine(session, 'st', schema, object_wildcard_shapes=OBJECT_WC, ops=ops)


def _membership_edges(se) -> frozenset:
    """Canonical, id-independent membership relation (subject_key, object_key, side)."""
    out = set()
    for object_id, ns in se.node_sets.items():
        okey = se.interner.key(object_id)
        for sid in ns.entities:
            out.add((se.interner.key(sid), okey, 'entity'))
        for sid in ns.usersets:
            out.add((se.interner.key(sid), okey, 'userset'))
    return frozenset(out)


# ---------------------------------------------------------------------------
# Replay equivalence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_replay_equivalence(load_fga_schema, ops):
    schema = load_fga_schema('wildcards.fga')
    session = _fresh_session()
    se = _make_engine(session, schema, ops)

    rng = random.Random(7)
    pool = _candidate_raw_tuples()
    present = set()
    for _ in range(40):
        raw = rng.choice(pool)
        try:
            if raw in present:
                se.remove_tuple(*raw)
                present.discard(raw)
            else:
                se.add_tuple(*raw)
                present.add(raw)
            session.commit()
        except ValueError:
            session.rollback()

    live = _membership_edges(se)
    # discard all in-memory state, rebuild purely from the TupleV1 rows
    se.rebuild()
    assert _membership_edges(se) == live

    # the table holds exactly the present tuples
    rows = session.exec(select(TupleV1).where(TupleV1.store_id == 'st')).all()
    stored = {(r.subject_predicate, r.subject_type, r.subject_name, r.relation,
               r.object_type, r.object_name) for r in rows}
    assert stored == present
    session.close()


# ---------------------------------------------------------------------------
# Accept/reject parity vs the graph backend
# ---------------------------------------------------------------------------

def _graph_accepts(sess, widx, ruleset, raw) -> bool:
    """Apply a raw op to the graph façade; True if accepted, False if it raised (cycle)."""
    sp = Ellipsis if raw[0] == '...' else raw[0]
    triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
    derived = list(ruleset.apply(triple))
    try:
        for d in derived:
            widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                           d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
        sess.commit()
        return True
    except ValueError:
        sess.rollback()
        return False


def _set_accepts(sess, se, raw) -> bool:
    try:
        se.add_tuple(*raw)
        sess.commit()
        return True
    except ValueError:
        sess.rollback()
        return False


@pytest.mark.parametrize('seed', [0, 1, 2, 3])
def test_accept_reject_parity_vs_graph(load_fga_schema, seed):
    schema = load_fga_schema('wildcards.fga')
    ruleset = parse_openfga_schema(schema, object_wildcard_shapes=OBJECT_WC)

    gsess, widx = make_wildcard_index(ruleset.schema_info, store_id='g')
    ssess = _fresh_session()
    se = _make_engine(ssess, schema, PySets)

    pool = _candidate_raw_tuples()
    rng = random.Random(seed)
    present = set()

    for _ in range(60):
        # bias toward adds (cycles only arise once tuples accumulate)
        raw = rng.choice([r for r in pool if r not in present] or list(present))
        is_add = raw not in present
        if is_add:
            g = _graph_accepts(gsess, widx, ruleset, raw)
            s = _set_accepts(ssess, se, raw)
            assert g == s, f'accept/reject disagreement on add {raw}: graph={g} set={s}'
            if g:
                present.add(raw)
        else:
            # removes always succeed for a present tuple in both backends
            sp = Ellipsis if raw[0] == '...' else raw[0]
            triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
            for d in ruleset.apply(triple):
                widx.remove_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                                  d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
            gsess.commit()
            se.remove_tuple(*raw)
            ssess.commit()
            present.discard(raw)

    gsess.close()
    ssess.close()


# ---------------------------------------------------------------------------
# Type-restriction validity
# ---------------------------------------------------------------------------

VALIDITY_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member]
type document
  relations
    define viewer: [user, user:*]
    define can_share: viewer
'''


@pytest.fixture
def validity_engine():
    session = _fresh_session()
    se = SetEngine(session, 'v', VALIDITY_SCHEMA, ops=PySets)
    yield se
    session.close()


def test_rejects_undeclared_subject_wildcard(validity_engine):
    # group.member = [user, group#member] -- no user:* allowed.
    with pytest.raises(ValueError):
        validity_engine.add_tuple('...', 'user', '*', 'member', 'group', 'g1')


def test_accepts_declared_subject_wildcard(validity_engine):
    validity_engine.add_tuple('...', 'user', '*', 'viewer', 'document', 'd1')  # [user:*] declared


def test_rejects_wrong_subject_type(validity_engine):
    # document.viewer allows user / user:* only, not a group userset.
    with pytest.raises(ValueError):
        validity_engine.add_tuple('member', 'group', 'g1', 'viewer', 'document', 'd1')


def test_rejects_direct_tuple_on_computed_only_relation(validity_engine):
    # can_share is `viewer` (computed) -- it has no direct restriction, so no raw tuple.
    with pytest.raises(ValueError):
        validity_engine.add_tuple('...', 'user', 'alice', 'can_share', 'document', 'd1')


def test_rejects_undeclared_object_wildcard(validity_engine):
    # object wildcards must be declared; none are for this schema.
    with pytest.raises(ValueError):
        validity_engine.add_tuple('...', 'user', 'alice', 'viewer', 'document', '*')


def test_remove_nonexistent_raises(validity_engine):
    with pytest.raises(ValueError):
        validity_engine.remove_tuple('...', 'user', 'alice', 'viewer', 'document', 'd1')
