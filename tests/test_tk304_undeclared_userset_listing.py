"""TK-304: ``lookup_reverse`` / ``expand`` never list a subject ``check`` refuses.

A TTU ``viewer from parent`` with ``parent: [folder, team]`` reaches the userset
``team:t1#viewer`` although ``team`` declares no ``viewer``. Since TK-185 (DEC-16)
``check('viewer', 'team', 't1', 'viewer', 'doc', '4')`` is refused with
``UndeclaredTypeOrRelation``, yet before TK-304 every listing surface returned that key, so a
caller could not feed a listing back into ``check`` (TK-185 residual D03, RISK-1). Such a
userset has no members (no write can name it), so dropping it removes no user.

Decision D1 (docs/tk304-prune-undeclared-usersets-2026-11-23.md, PROVISIONAL): the listing
rule is the refusal's twin and lives where the refusal lives. One predicate,
``src/zanzibar/schema/readcheck.py::lists_subject_shape``, prunes keys, markers and
exclusions at ``SetEngine.expand``'s top-level call (so ``SetEngine.lookup_reverse`` and
``Store.expand``) and in ``Store.lookup_reverse`` after the graph index answers. The
lenient ``WildcardIndex`` (DEC-16 item 5) still lists the key: pinned here as the
instrument control, so these pins cannot pass on a scenario that never reaches it.

Pinned here, on Store sync, Store async (caught up) and SetEngine, under both a concrete
``team`` parent (a key) and a ``team:*`` star parent (a marker): the undeclared userset is
absent; the declared members are present; and every listed key round-trips through
``check`` without a refusal.

Sabotage, observed 2026-11-23 (docs/sabotage-procedure.md; each restored by copying the
saved file back, then re-run green). Run: this module plus ``tests/test_lookup_oracle.py``
``-k`` the TK-185/TK-304 undeclared tests.

  S1 ``SetEngine.expand``'s top-level prune removed (``return m``): rc=1 ``4 failed, 5
     passed`` -- ``AssertionError: ('sync.expand', [('doc', '4', 'viewer'), ('folder', 'f1',
     'viewer'), ('team', 't1', 'viewer'), ('user', 'u', '...')])``, the round trip's
     ``UndeclaredTypeOrRelation: check() names an undeclared subject relation team#viewer``,
     the star marker ``('sync.expand', {('team', 'viewer')})``, and the lookup-oracle gate's
     ``set.expand('r2', 'doc', 'd1') [py]: pos member folder:f1#r1 is oracle-false``.
  S2 ``Store.lookup_reverse``'s prune removed (first form: its ``_filter_shapes`` line
     deleted; re-run after the review merged it with the TK156 filter, as ``listed =
     lambda t, p: True``, same result): rc=1 ``3 failed, 6 passed``
     -- ``('sync.lookup_reverse', [... ('team', 't1', 'viewer') ...])``, the round trip, and
     ``('sync.lookup_reverse', {('team', 'viewer')})``.
  S3 ``lists_subject_shape`` returns True always: rc=1 ``5 failed, 4 passed`` -- the S2
     failures plus ``test_lists_subject_shape`` (``assert not True``) and both set-side ones.
  S4 (instrument) ``tests/test_lookup_oracle.py::_listed`` returns the plain oracle: rc=1
     ``1 failed, 8 passed`` -- ``set.expand('r2', 'doc', 'd1') [py] vs oracle on subject
     (r1,folder,f1): set=False oracle=True``: the gate's set-side reference must carry the
     listing rule, or the pruned product reads as a divergence.
  Also: the executed example in ``userdocs/explanation/semantics-vs-openfga.md`` with its
  old expected output put back: ``tests/test_userdocs_examples.py -k semantics`` rc=1.
"""
from __future__ import annotations

import warnings

import pytest
from sqlmodel import Session, SQLModel, create_engine

import zanzibar
from zanzibar.setengine import SetEngine
from zanzibar.store import Store

SCHEMA = '''model
  schema 1.1
type user
type team
  relations
    define member: [user]
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder, team]
    define viewer: [user] or viewer from parent
'''
STAR_SCHEMA = SCHEMA.replace('define parent: [folder, team]',
                             'define parent: [folder, team, team:*]')

TUPLES = [('...', 'folder', 'f1', 'parent', 'doc', '4'),
          ('...', 'team', 't1', 'parent', 'doc', '4'),
          ('...', 'user', 'u', 'viewer', 'folder', 'f1')]
STAR_TUPLES = [('...', 'team', '*', 'parent', 'doc', '4'),
               ('...', 'user', 'u', 'viewer', 'doc', '4')]

UNDECLARED = ('team', 't1', 'viewer')
OBJ = ('viewer', 'doc', '4')


def _world(tmp_path, schema, tuples):
    engine = create_engine(f'sqlite:///{tmp_path / "w.db"}')
    SQLModel.metadata.create_all(engine)
    sessions = []

    def session():
        s = Session(engine)
        sessions.append(s)
        return s
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', zanzibar.UnprovenExtensionWarning)  # team:* parent
        sync = Store(session(), 'sync', schema=schema, sync=True)
        asyn = Store(session(), 'asyn', schema=schema, sync=False)
        se = SetEngine(session(), 'se', schema)
    for t in tuples:
        sync.add_tuple(*t)
        asyn.add_tuple(*t)
        se.add_tuple(*t)
    assert asyn.catch_up() == len(tuples)
    return sync, asyn, se, sessions


@pytest.fixture
def world(tmp_path):
    sync, asyn, se, sessions = _world(tmp_path, SCHEMA, TUPLES)
    yield sync, asyn, se
    for s in sessions:
        s.close()


@pytest.fixture
def star_world(tmp_path):
    sync, asyn, se, sessions = _world(tmp_path, STAR_SCHEMA, STAR_TUPLES)
    yield sync, asyn, se
    for s in sessions:
        s.close()


def _listings(sync, asyn, se):
    """Every listing surface of ``OBJ`` as (name, keys, markers-as-(type, predicate))."""
    out = []
    for name, st in (('sync', sync), ('async', asyn)):
        r = st.lookup_reverse(*OBJ)
        out.append((f'{name}.lookup_reverse', st.result_keys(r) | st.excluded_keys(r),
                    {m[:2] for m in r.markers}))
        e = st.expand(*OBJ)
        out.append((f'{name}.expand', set(e.keys) | set(e.excluded_keys),
                    {m[:2] for m in e.markers}))
    r = se.lookup_reverse(*OBJ)
    out.append(('se.lookup_reverse', se.result_keys(r) | se.excluded_keys(r),
                {m[:2] for m in r.markers}))
    m = se.expand(*OBJ)
    out.append(('se.expand', {se.interner.key(i) for i in (*m.pos, *m.neg)}
                | set(m.ipos) | set(m.ineg), set(m.stars)))
    return out


def test_check_refuses_the_undeclared_userset(world):
    sync, asyn, se = world
    for surface in (sync, asyn, se):
        with pytest.raises(zanzibar.UndeclaredTypeOrRelation):
            surface.check('viewer', 'team', 't1', *OBJ)


def test_lenient_graph_index_still_lists_it(world):
    """Instrument control: the scenario reaches the key the pins below must not see."""
    sync, asyn, _ = world
    for st in (sync, asyn):
        raw = st.widx.lookup_reverse(*OBJ)
        assert UNDECLARED in st.result_keys(raw)


def test_no_surface_lists_the_undeclared_userset(world):
    listings = _listings(*world)
    assert len(listings) == 6
    for name, keys, markers in listings:
        assert UNDECLARED not in keys, (name, sorted(keys))
        assert {('folder', 'f1', 'viewer'), ('user', 'u', '...'),
                ('doc', '4', 'viewer')} <= keys, (name, sorted(keys))   # anti-vacuity
        assert not markers, (name, markers)


def test_every_listed_key_round_trips_through_check(world):
    sync, asyn, se = world
    for _name, keys, _ in _listings(sync, asyn, se):
        for (t, n, p) in keys:
            for surface in (sync, se):
                surface.check(p, t, n, *OBJ)        # must not raise


def test_star_tupleset_marker_is_not_listed(star_world):
    sync, asyn, se = star_world
    for st in (sync, asyn):                          # instrument control
        assert ('team', 'viewer', 'any') in st.widx.lookup_reverse(*OBJ).markers
    for name, keys, markers in _listings(sync, asyn, se):
        assert ('team', 'viewer') not in markers, (name, markers)
        assert ('user', 'u', '...') in keys, (name, sorted(keys))        # anti-vacuity


def test_a_declared_userset_is_still_listed(world):
    """The prune is by shape, not by 'userset': ``folder:f1#viewer`` is declared."""
    for name, keys, _ in _listings(*world):
        assert ('folder', 'f1', 'viewer') in keys, name


def test_lists_subject_shape(world):
    from zanzibar.schema.readcheck import lists_subject_shape
    d = world[2]._declared
    assert lists_subject_shape(d, 'user', '...')
    assert lists_subject_shape(d, 'team', '...')
    assert lists_subject_shape(d, 'team', 'member')
    assert lists_subject_shape(d, 'folder', 'viewer')
    assert not lists_subject_shape(d, 'team', 'viewer')
    assert not lists_subject_shape(d, 'nosuchtype', '...')
