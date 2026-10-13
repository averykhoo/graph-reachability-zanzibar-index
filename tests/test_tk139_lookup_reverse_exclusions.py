"""TK139 -- ``SetEngine.lookup_reverse`` carries ``but not`` exclusions, as the graph does.

Property guarded
----------------
Under a subject wildcard (``[user:*]``) on a ``but not`` relation, ``lookup_reverse`` on
the standalone ``SetEngine`` and on ``ConnectedStore`` (the graph index) render the SAME
answer once ids are translated to portable ``(type, name, predicate)`` keys: the same
concrete subjects, the same marker shapes, and the same ``excluded_node_ids``. A
list-users caller that follows the PyPI README ("subtract ``excluded_node_ids`` from the
marker") then lists exactly the oracle's allowed set on BOTH backends.

Found by the 0.0.4 fresh-user install trial (``docs/pypi-trial-0.0.4-2026-10-13.md``
BROKEN-1, probe p05): the set engine returned ``markers={('user', '...')}`` with
``excluded_node_ids=set()`` -- "every user" -- while its own ``check(mallory)`` was False
and ``ConnectedStore`` excluded mallory. ``expand`` carried the exclusion in ``neg``;
``lookup_reverse`` copied only ``pos`` and ``stars``. Map and census:
``docs/tk139-lookup-reverse-exclusions-2026-10-13.md``. The generated-schema twin of this
pin is S3 in ``tests/test_lookup_oracle.py`` (now two-sided).

Sabotage (2026-10-13, docs/sabotage-procedure.md): with the fix line
``result.excluded_node_ids = set(m.neg)`` in
``src/zanzibar/setengine/engine.py::SetEngine.lookup_reverse`` replaced by ``pass``, all
four tests here went RED (``7 failed, 44 passed`` together with
``tests/test_lookup_oracle.py``), literal output::

    AssertionError: SetEngine[py] excluded set() != graph {('user', 'mallory', '...')}
    AssertionError: SetEngine[roaring] excluded set() != graph {('user', 'mallory', '...')}
    AssertionError: SetEngine[py] excluded set() != graph {('user', 'mallory', '...'), ('user', 'eve', '...')}
    AssertionError: SetEngine[roaring] excluded set() != graph {('user', 'mallory', '...'), ('user', 'eve', '...')}

Restored from a byte copy; ``grep -c SABOTAGE`` 0 and ``git diff`` shows only the fix.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar.connectedstore import ConnectedStore
from zanzibar.graphindex import Node
from zanzibar.setengine import ALL_SETOPS, SetEngine

from tests.oracle import Oracle, OracleTuple

# The p05 probe's schema and writes, verbatim.
P05_SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define viewer: [user:*] but not banned
"""
P05_TUPLES = [('...', 'user', '*', 'viewer', 'doc', 'd'),
              ('...', 'user', 'mallory', 'banned', 'doc', 'd')]

# A wider twin: a concrete grant beside the wildcard, a user banned only on ANOTHER doc
# (interned and star-covered, so must NOT be excluded on doc:d), and two bans on doc:d.
MIXED_SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define viewer: [user, user:*] but not banned
"""
MIXED_TUPLES = [('...', 'user', '*', 'viewer', 'doc', 'd'),
                ('...', 'user', 'bob', 'viewer', 'doc', 'd'),
                ('...', 'user', 'mallory', 'banned', 'doc', 'd'),
                ('...', 'user', 'eve', 'banned', 'doc', 'd'),
                ('...', 'user', 'carol', 'banned', 'doc', 'd2'),
                ('...', 'user', 'carol', 'viewer', 'doc', 'd2')]

# Candidate users a list-users UI might ask about: written ones plus a ghost nobody wrote.
CANDIDATES = ['mallory', 'eve', 'bob', 'carol', 'never_written_ghost']


def _session():
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _set_render(se, res):
    """(node keys, marker shapes, excluded keys) in the portable key space, through the
    PUBLIC translators a service-boundary caller uses (``result_keys`` /
    ``excluded_keys``), so the pins below also pin those helpers."""
    return (se.result_keys(res), set(res.markers), se.excluded_keys(res))


def _graph_render(session, res):
    def key(nid):
        n = session.get(Node, nid)
        assert n is not None, f'dead graph node id {nid}'
        return (n.type, n.name, n.predicate)
    return ({key(i) for i in res.node_ids},
            {(t, p) for (t, p, v) in res.markers if v == 'any'},
            {key(i) for i in res.excluded_node_ids})


def _listed(render, name):
    """What a README-following list-users UI concludes for user ``name``."""
    nodes, markers, excluded = render
    k = ('user', name, '...')
    return k in nodes or (('user', '...') in markers and k not in excluded)


def _assert_agree(schema, tuples, ops):
    oracle = Oracle(schema, [OracleTuple(*t) for t in tuples])
    allowed = {u for u in CANDIDATES
               if oracle.check('...', 'user', u, 'viewer', 'doc', 'd')}

    s = _session()
    try:
        se = SetEngine(s, 'set-side', schema, ops=ops)
        for t in tuples:
            se.add_tuple(*t)
        cs = ConnectedStore(s, 'graph-side', schema=schema)
        for t in tuples:
            cs.add_tuple(*t)

        for u in CANDIDATES:                                    # check agrees first
            want = u in allowed
            assert se.check('...', 'user', u, 'viewer', 'doc', 'd') is want, u
            assert cs.check('...', 'user', u, 'viewer', 'doc', 'd') is want, u

        set_r = _set_render(se, se.lookup_reverse('viewer', 'doc', 'd'))
        graph_r = _graph_render(s, cs.lookup_reverse('viewer', 'doc', 'd'))
        name = f'SetEngine[{ops.name}]'
        assert set_r[0] == graph_r[0], f'{name} node keys {set_r[0]} != graph {graph_r[0]}'
        assert set_r[1] == graph_r[1], f'{name} markers {set_r[1]} != graph {graph_r[1]}'
        assert set_r[2] == graph_r[2], f'{name} excluded {set_r[2]} != graph {graph_r[2]}'

        for label, render in ((name, set_r), ('ConnectedStore', graph_r)):
            listed = {u for u in CANDIDATES if _listed(render, u)}
            assert listed == allowed, (
                f'{label}: a list-users UI subtracting excluded_node_ids lists '
                f'{sorted(listed)}, the oracle allows {sorted(allowed)}')
        return set_r, allowed
    finally:
        s.close()


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_p05_repro_both_backends_agree(ops):
    """The install-trial repro, verbatim: mallory is excluded on both backends."""
    (nodes, markers, excluded), allowed = _assert_agree(P05_SCHEMA, P05_TUPLES, ops)
    assert nodes == set()
    assert markers == {('user', '...')}
    assert excluded == {('user', 'mallory', '...')}       # the field TK139 filled
    assert 'mallory' not in allowed and 'never_written_ghost' in allowed  # anti-vacuity


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_mixed_grants_both_backends_agree(ops):
    """Concrete grant + wildcard + bans on this doc and on another: exclusions are
    exactly the users banned on doc:d (carol, banned elsewhere, is not excluded)."""
    (nodes, markers, excluded), allowed = _assert_agree(MIXED_SCHEMA, MIXED_TUPLES, ops)
    # bob's concrete grant is star-covered, so BOTH backends carry him by the marker,
    # not as a concrete id (observed 2026-10-13: node keys set() on each side).
    assert nodes == set()
    assert markers == {('user', '...')}
    assert excluded == {('user', 'mallory', '...'), ('user', 'eve', '...')}
    assert allowed == {'bob', 'carol', 'never_written_ghost'}


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_excluded_keys_is_the_portable_exclusion_channel(ops):
    """``SetEngine.excluded_keys`` is the portable twin of ``excluded_node_ids``: equal to
    the interner translation of the raw ids, and the key a caller subtracts. A caller who
    ships only ``result_keys`` + ``markers`` across a service boundary re-creates the
    TK139 "every user" over-grant (review finding, 2026-10-13d); before this helper the
    ``result_keys`` docstring called its output alone "the portable form".

    Sabotage (2026-10-13d, docs/sabotage-procedure.md): ``excluded_keys`` body replaced by
    ``return set()``; this module went ``6 failed in 0.92s`` (the p05 and mixed pins too,
    via ``_set_render``), literal output::

        AssertionError: SetEngine[py] excluded set() != graph {('user', 'mallory', '...')}
        AssertionError: assert set() == {('user', 'mallory', '...')}

    Restored from a byte copy; ``grep -c SABOTAGE`` 0."""
    s = _session()
    try:
        se = SetEngine(s, 'keys', P05_SCHEMA, ops=ops)
        for t in P05_TUPLES:
            se.add_tuple(*t)
        res = se.lookup_reverse('viewer', 'doc', 'd')
        assert se.result_keys(res) == set()                       # anti-vacuity: the
        assert res.markers == {('user', '...')}                   # marker carries it all
        assert se.excluded_keys(res) == {('user', 'mallory', '...')}
        assert se.excluded_keys(res) == {se.interner.key(i) for i in res.excluded_node_ids}
        assert se.check('...', 'user', 'mallory', 'viewer', 'doc', 'd') is False
    finally:
        s.close()
