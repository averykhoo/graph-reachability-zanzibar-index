"""TK154: a lookup result held across a write must never translate to ANOTHER entity's key.

Properties guarded
------------------
* **Set engine (D1).** Every ``SetLookupResult`` from ``lookup`` / ``lookup_reverse`` carries
  ``id_stamp = (interner serial, frees)``. ``SetEngine.result_keys`` / ``excluded_keys``
  raise ``StaleLookupIds`` (a ``ZanzibarError`` and a ``KeyError``) once any interner id has
  been freed since the lookup (a remove, or a catch-up applying another instance's remove),
  after ``rebuild()``, or for a result from another engine instance. A write that only
  acquires FRESH ids does not invalidate a held result (the precision choice: frees, not
  writes). A hand-built (unstamped) result with an id naming no entity raises the same
  named error instead of a raw ``KeyError``.
* **Graph (D3).** ``zanzibar_node`` is created with ``AUTOINCREMENT`` on SQLite, so a
  removed node's id is never handed out again: a stale ``LookupResult`` id can only go
  MISSING, and ``Store.result_keys`` / ``excluded_keys`` raise ``StaleLookupIds`` for it. A
  ``Store`` refuses to open a 0.0.x SQLite file whose ``zanzibar_node`` lacks
  ``AUTOINCREMENT`` (``TablesOutdated``, a ``ZanzibarError`` and a ``RuntimeError``).

Two PERMANENT instrument controls (t9, t10) remove the guard by monkeypatch and assert the
WRONG key comes back, so the fixtures are proven to really recycle an id: if they ever stop
recycling, the controls go red rather than the guards silently passing.

Before the fix (PROBE, ``.scratch/tk150-154/p154_setengine.log`` / ``p154_graph.log`` /
``p154_cross.log``, 2026-10-16): A3 ``excluded_keys`` -> ``{('doc', 'd', 'banned')}`` (was
``user:m``); B2 after ``rebuild()`` -> ``{('user', 'b', '...')}`` (was
``{('doc', 'd3', 'viewer')}``); X2 another instance -> ``{('user', 'u2', '...')}``; G3 graph
after remove + add -> ``{('user', 'b', '...')}`` (was ``user:a``).

Sabotage evidence (docs/sabotage-procedure.md) is recorded per test below and in
``docs/tk154-stale-lookup-ids-2026-10-16.md``.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

import zanzibar
import zanzibar.store._store as store_mod
from zanzibar.schema.errors import ZanzibarError
from zanzibar.setengine import SetEngine, SetLookupResult
from zanzibar.setengine.engine import StaleLookupIds
from zanzibar.store import Store, TablesOutdated

P = ('type user\ntype doc\n  relations\n    define banned: [user]\n'
     '    define viewer: [user, user:*] but not banned\n    define reader: [user]\n')
S = 'model\n  schema 1.1\n' + P


@pytest.fixture
def mem_engine():
    eng = create_engine('sqlite://')
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


def _set_engine_recycle_sequence(se: SetEngine):
    """PROBE A: ``user:m`` is banned under a ``user:*`` grant, the result holds m's id in
    ``excluded_node_ids``; unbanning m frees the id, banning eve does not reuse it for eve
    but for ``doc:d#banned`` (the free list is LIFO)."""
    se.add_tuple('...', 'user', '*', 'viewer', 'doc', 'd')
    se.add_tuple('...', 'user', 'm', 'banned', 'doc', 'd')
    r = se.lookup_reverse('viewer', 'doc', 'd')
    assert se.excluded_keys(r) == {('user', 'm', '...')}
    return r


def test_set_engine_recycled_id_is_refused_not_translated(mem_engine):
    """A2/A3. Sabotage observed 2026-10-16 (plugin
    ``formal/probes/tk154_sabotage_plugin_2026_10_16.py``): S1 (both raises in
    ``_check_id_stamp`` removed) and S2 (``frees`` not bumped in ``Interner.release``) each
    go red here at A3 with ``Failed: DID NOT RAISE StaleLookupIds`` (A2 still raises via
    the missing-id path); the value it then returns, ``{('doc', 'd', 'banned')}``, is
    pinned by the t9 control."""
    with Session(mem_engine) as s:
        se = SetEngine(s, 'st', P)
        r = _set_engine_recycle_sequence(se)
        se.remove_tuple('...', 'user', 'm', 'banned', 'doc', 'd')
        with pytest.raises(StaleLookupIds, match='node_ids') as ei:
            se.excluded_keys(r)                                          # A2
        exc = ei.value
        assert isinstance(exc, KeyError) and isinstance(exc, ZanzibarError)
        assert exc.field == 'excluded_node_ids'
        se.add_tuple('...', 'user', 'eve', 'banned', 'doc', 'd')
        with pytest.raises(StaleLookupIds, match='run the lookup again'):
            se.excluded_keys(r)                                          # A3
        with pytest.raises(StaleLookupIds):
            se.result_keys(r)
        fresh = se.lookup_reverse('viewer', 'doc', 'd')
        assert se.excluded_keys(fresh) == {('user', 'eve', '...')}


def test_set_engine_rebuild_invalidates_held_results(mem_engine):
    """B: ``rebuild()`` with no write remaps ids (before the fix: ``{('user', 'b', '...')}``
    for a result that read ``{('doc', 'd3', 'viewer')}``)."""
    with Session(mem_engine) as s:
        se = SetEngine(s, 'st', P)
        se.add_tuple('...', 'user', 'a', 'viewer', 'doc', 'd1')
        se.add_tuple('...', 'user', 'b', 'viewer', 'doc', 'd2')
        se.remove_tuple('...', 'user', 'a', 'viewer', 'doc', 'd1')
        se.add_tuple('...', 'user', 'c', 'viewer', 'doc', 'd3')
        s.flush()
        r = se.lookup('...', 'user', 'c')
        before = se.result_keys(r)
        assert before == {('doc', 'd3', 'viewer')}
        se.rebuild()
        with pytest.raises(StaleLookupIds, match='rebuilt'):
            se.result_keys(r)
        assert se.result_keys(se.lookup('...', 'user', 'c')) == before


def test_set_engine_result_from_another_instance_is_refused(mem_engine):
    """X: before the fix ``b.result_keys(ra)`` was ``{('user', 'u2', '...')}``."""
    with Session(mem_engine) as s:
        a = SetEngine(s, 'st', P)
        a.add_tuple('...', 'user', 'u1', 'viewer', 'doc', 'd1')
        a.add_tuple('...', 'user', 'u2', 'viewer', 'doc', 'd2')
        a.remove_tuple('...', 'user', 'u1', 'viewer', 'doc', 'd1')
        a.add_tuple('...', 'user', 'u3', 'viewer', 'doc', 'd3')
        s.flush()
        b = SetEngine(s, 'st', P)
        ra = a.lookup('...', 'user', 'u3')
        with pytest.raises(StaleLookupIds, match='another SetEngine instance'):
            b.result_keys(ra)
        assert a.result_keys(ra) == {('doc', 'd3', 'viewer')}


def test_a_fresh_id_add_does_not_invalidate(mem_engine):
    """The precision choice: only a FREE can re-point an id, so an add that acquires fresh
    ids leaves a held result translatable."""
    with Session(mem_engine) as s:
        se = SetEngine(s, 'st', P)
        se.add_tuple('...', 'user', 'a', 'reader', 'doc', 'd1')
        se.add_tuple('...', 'user', 'a', 'viewer', 'doc', 'd2')
        r = se.lookup('...', 'user', 'a')
        keys = se.result_keys(r)
        assert keys == {('doc', 'd1', 'reader'), ('doc', 'd2', 'viewer')}
        assert not se.interner._free
        se.add_tuple('...', 'user', 'newbie', 'reader', 'doc', 'brand_new')
        assert not se.interner._free
        assert se.result_keys(r) == keys


def test_store_set_engine_result_after_another_instances_remove(tmp_path):
    """Y: instance 1 holds a set-engine result; instance 2 unbans m; instance 1's next write
    catches its evaluator up, which frees m's id, so the held result is refused."""
    eng = create_engine(f'sqlite:///{tmp_path / "tk154.db"}')
    SQLModel.metadata.create_all(eng)
    try:
        with Session(eng) as s1:
            st1 = Store(s1, 'm', schema=S)
            st1.add_tuple('user:*', 'viewer', 'doc:x')
            st1.add_tuple('user:m', 'banned', 'doc:x')
            se1 = st1.source.engine
            r = se1.lookup_reverse('viewer', 'doc', 'x')
            assert se1.excluded_keys(r) == {('user', 'm', '...')}
            s1.commit()
            with Session(eng) as s2:
                st2 = Store(s2, 'm')
                st2.remove_tuple('user:m', 'banned', 'doc:x')
            s1.rollback()
            st1.add_tuple('user:zed', 'reader', 'doc:q')
            with pytest.raises(StaleLookupIds, match='run the lookup again'):
                se1.excluded_keys(r)
            assert se1.excluded_keys(se1.lookup_reverse('viewer', 'doc', 'x')) == set()
    finally:
        eng.dispose()


def test_hand_built_result_with_a_missing_id_raises_the_named_error(mem_engine):
    with Session(mem_engine) as s:
        se = SetEngine(s, 'st', P)
        se.add_tuple('...', 'user', 'a', 'reader', 'doc', 'd1')
        with pytest.raises(StaleLookupIds, match='node_ids') as ei:
            se.result_keys(SetLookupResult(node_ids={10_000}))
        assert ei.value.ids == [10_000]
        with pytest.raises(StaleLookupIds, match='excluded_node_ids'):
            se.excluded_keys(SetLookupResult(excluded_node_ids={10_000}))


def _node_ddl(conn) -> str:
    return conn.execute(text(
        "select sql from sqlite_master where type='table' and name='zanzibar_node'")).scalar()


def _graph_reuse_sequence(store: Store):
    """PROBE G1-G3: a result naming user:a; remove it (its nodes are collected); add user:b
    on another doc. Returns the held result."""
    store.add_tuple('user:a', 'reader', 'doc:d')
    r = store.lookup_reverse('reader', 'doc:d')
    # TK144: the target's own userset doc:d#reader is a member of itself (OpenFGA's
    # implicit self-relation); its node goes with user:a's when the tuple is removed.
    assert store.result_keys(r) == {('user', 'a', '...'), ('doc', 'd', 'reader')}
    store.remove_tuple('user:a', 'reader', 'doc:d')
    store.add_tuple('user:b', 'reader', 'doc:e')
    return r


def test_graph_node_ids_are_never_reused_on_sqlite(mem_engine):
    """G3/G6. Sabotage S3 observed 2026-10-16 (``sqlite_autoincrement`` dropped from
    ``Node``): ``AssertionError: assert 'AUTOINCREMENT' in 'CREATE TABLE ZANZIBAR_NODE
    (...'``. What the reused rowid then translates to, ``{('user', 'b', '...')}``, is
    pinned by the t10 control."""
    with mem_engine.connect() as c:
        assert 'AUTOINCREMENT' in _node_ddl(c).upper()
    with Session(mem_engine) as s:
        store = Store(s, 'g', schema=S)
        r = _graph_reuse_sequence(store)
        with pytest.raises(StaleLookupIds, match='run the lookup again') as ei:
            store.result_keys(r)
        assert ei.value.field == 'node_ids'
        assert store.result_keys(store.lookup_reverse('reader', 'doc:e')) == {
            ('user', 'b', '...'), ('doc', 'e', 'reader')}       # TK144: + the self userset
        # G4-G6: the excluded channel
        store.add_tuple('user:*', 'viewer', 'doc:x')
        store.add_tuple('user:m', 'banned', 'doc:x')
        r2 = store.lookup_reverse('viewer', 'doc:x')
        assert store.excluded_keys(r2) == {('user', 'm', '...')}
        store.remove_tuple('user:m', 'banned', 'doc:x')
        store.add_tuple('user:eve', 'banned', 'doc:x')
        with pytest.raises(StaleLookupIds, match='excluded_node_ids'):
            store.excluded_keys(r2)
        assert store.excluded_keys(store.lookup_reverse('viewer', 'doc:x')) == {('user', 'eve', '...')}


def _downgrade_node_table(engine) -> None:
    """Re-create ``zanzibar_node`` with the 0.0.x DDL (no ``AUTOINCREMENT``), keeping its
    indexes."""
    with engine.begin() as c:
        ddl = _node_ddl(c)
        indexes = [row[0] for row in c.execute(text(
            "select sql from sqlite_master where type='index' and tbl_name='zanzibar_node' "
            "and sql is not null"))]
        assert 'AUTOINCREMENT' in ddl.upper()
        c.execute(text('DROP TABLE zanzibar_node'))
        c.execute(text(ddl.replace(' AUTOINCREMENT', '').replace(' autoincrement', '')))
        for sql in indexes:
            c.execute(text(sql))
        assert 'AUTOINCREMENT' not in _node_ddl(c).upper()


def test_store_refuses_a_legacy_node_table(mem_engine):
    """Sabotage S4 observed 2026-10-16 (``refuse_reusable_node_ids`` returns at once):
    ``Failed: DID NOT RAISE TablesOutdated``."""
    _downgrade_node_table(mem_engine)
    with Session(mem_engine) as s:
        with pytest.raises(TablesOutdated, match='AUTOINCREMENT') as ei:
            Store(s, 'g', schema=S)
        assert 'new database file' in str(ei.value).lower()
        assert isinstance(ei.value, RuntimeError) and isinstance(ei.value, ZanzibarError)
        assert ei.value.table == 'zanzibar_node'
    assert zanzibar.TablesOutdated is TablesOutdated


def test_sabotage_control_set_engine_without_the_stamp_check_translates_wrong(
        mem_engine, monkeypatch):
    """PERMANENT instrument control: with the stamp check gone the fixture's recycled id
    translates to ``{('doc', 'd', 'banned')}`` -- the wrong key t1 guards against."""
    monkeypatch.setattr(SetEngine, '_check_id_stamp', lambda self, res, field: None)
    with Session(mem_engine) as s:
        se = SetEngine(s, 'st', P)
        r = _set_engine_recycle_sequence(se)
        se.remove_tuple('...', 'user', 'm', 'banned', 'doc', 'd')
        se.add_tuple('...', 'user', 'eve', 'banned', 'doc', 'd')
        assert se.excluded_keys(r) == {('doc', 'd', 'banned')}


def test_sabotage_control_graph_without_autoincrement_translates_wrong(
        mem_engine, monkeypatch):
    """PERMANENT instrument control: on a 0.0.x table with the refusal bypassed, the held
    result translates to ``{('user', 'b', '...'), ('doc', 'e', 'reader')}`` -- SQLite reused
    the removed nodes' rowids (TK144: the held result also named the target's own userset
    ``doc:d#reader``, whose recycled rowid now names ``doc:e#reader``). AUTOINCREMENT is what
    t7 relies on."""
    _downgrade_node_table(mem_engine)
    monkeypatch.setattr(store_mod, 'refuse_reusable_node_ids', lambda session: None)
    with Session(mem_engine) as s:
        store = Store(s, 'g', schema=S)
        r = _graph_reuse_sequence(store)
        assert store.result_keys(r) == {('user', 'b', '...'), ('doc', 'e', 'reader')}


def test_stale_lookup_ids_and_tables_outdated_are_exported():
    from zanzibar import StaleLookupIds as top_stale, TablesOutdated as top_outdated
    import zanzibar.setengine as se_pkg
    import zanzibar.store as store_pkg
    assert top_stale is StaleLookupIds and top_outdated is TablesOutdated
    assert {'StaleLookupIds', 'TablesOutdated'} <= set(zanzibar.__all__)
    assert 'StaleLookupIds' in se_pkg.__all__
    assert {'StaleLookupIds', 'TablesOutdated'} <= set(store_pkg.__all__)
    assert store_pkg.StaleLookupIds is StaleLookupIds


_XPROC_CHILD = '''
import pickle, sys
from sqlmodel import Session, SQLModel, create_engine
from zanzibar.setengine import SetEngine
P = 'type user\\ntype doc\\n  relations\\n    define reader: [user]\\n'
role, path = sys.argv[1], sys.argv[2]
eng = create_engine('sqlite://'); SQLModel.metadata.create_all(eng)
with Session(eng) as s:
    se = SetEngine(s, 'st', P)
    if role == 'A':
        se.add_tuple('...', 'user', 'alice', 'reader', 'doc', 'secret')
        r = se.lookup('...', 'user', 'alice')
        assert se.result_keys(r) == {('doc', 'secret', 'reader')}
        open(path, 'wb').write(pickle.dumps(r))
        print('A-OK frees', r.id_stamp[1])
    else:
        se.add_tuple('...', 'user', 'bob', 'reader', 'doc', 'public')
        r = pickle.loads(open(path, 'rb').read())
        print('B frees', se.interner.frees, 'held frees', r.id_stamp[1])
        try:
            print('TRANSLATED', sorted(se.result_keys(r)))
        except Exception as e:
            print('REFUSED', type(e).__name__, e)
'''


def test_set_engine_result_from_another_process_is_refused(tmp_path):
    """Review finding (2026-10-16, PROBE ``.scratch/tk150-154/rev154_xproc.log``): with a
    per-process counter as the interner serial, the first ``Interner`` in EVERY process got
    serial 1, so a ``SetLookupResult`` pickled in process A matched a fresh engine's stamp in
    process B (``frees`` both 0) and translated to B's entity:
    ``TRANSLATED [('doc', 'public', 'reader')]`` for a result that read
    ``{('doc', 'secret', 'reader')}``. Each child here is a FRESH interpreter, so both hold
    their process's first interner and both stamps have ``frees == 0`` -- the serial is the
    only thing that can tell the id maps apart. Sabotage observed 2026-10-16
    (``_new_interner_serial`` returning ``1``): red with
    ``assert 'REFUSED StaleLookupIds' in "B frees 0 held frees 0\\nTRANSLATED [('doc', 'public', 'reader')]\\n"``."""
    import subprocess
    import sys
    script = tmp_path / 'xproc_child.py'
    script.write_text(_XPROC_CHILD, encoding='utf-8')
    pkl = tmp_path / 'result.pkl'

    def run(role):
        cp = subprocess.run([sys.executable, str(script), role, str(pkl)],
                            capture_output=True, text=True, timeout=120)
        assert cp.returncode == 0, cp.stderr
        return cp.stdout

    assert 'A-OK frees 0' in run('A')
    out = run('B')
    assert 'B frees 0 held frees 0' in out          # instrument: frees cannot tell them apart
    assert 'REFUSED StaleLookupIds' in out, out
    assert 'another SetEngine instance' in out


def test_sabotage_control_constant_serial_translates_a_pickled_result_wrong(
        mem_engine, monkeypatch):
    """PERMANENT instrument control for the cross-process test: if two id maps share a
    serial (what a per-process counter did across processes), an unpickled result with
    matching ``frees`` translates to the OTHER engine's entity --
    ``{('doc', 'public', 'reader')}``. Proves the serial is the only guard on that path."""
    import pickle
    import zanzibar.setengine.engine as engine_mod
    monkeypatch.setattr(engine_mod, '_new_interner_serial', lambda: 1)
    q = 'type user\ntype doc\n  relations\n    define reader: [user]\n'
    with Session(mem_engine) as s:
        a = SetEngine(s, 'a', q)
        a.add_tuple('...', 'user', 'alice', 'reader', 'doc', 'secret')
        held = pickle.loads(pickle.dumps(a.lookup('...', 'user', 'alice')))
        b = SetEngine(s, 'b', q)
        b.add_tuple('...', 'user', 'bob', 'reader', 'doc', 'public')
        assert b.result_keys(held) == {('doc', 'public', 'reader')}


def test_the_new_errors_survive_pickle_and_copy():
    """Review finding (2026-10-16, PROBE ``.scratch/tk150-154/rev154_probe.log``): before
    ``__reduce__``, ``pickle.loads(pickle.dumps(StaleLookupIds(...)))`` and ``copy.copy``
    raised ``TypeError: StaleLookupIds.__init__() missing 2 required positional arguments:
    'ids' and 'reason'`` -- a raise inside a worker process could not cross back.
    ``TablesOutdated`` round-tripped with ``.table`` set to the whole message. Sabotage
    observed 2026-10-16 (each ``__reduce__`` renamed away): exactly those two failures --
    the ``TypeError`` above, and for ``TablesOutdated`` the ``back.table ==
    'zanzibar_node'`` assertion red with ``.table`` holding
    ``"table 'zanzibar_node' in this SQLite database has no AUTOINCREMENT ..."``."""
    import copy
    import pickle
    e = StaleLookupIds('excluded_node_ids', [3, 4], 'because')
    for back in (pickle.loads(pickle.dumps(e)), copy.copy(e)):
        assert type(back) is StaleLookupIds
        assert (back.field, back.ids, back.reason) == ('excluded_node_ids', [3, 4], 'because')
        assert str(back) == str(e)
    t = TablesOutdated('zanzibar_node')
    for back in (pickle.loads(pickle.dumps(t)), copy.copy(t)):
        assert type(back) is TablesOutdated
        assert back.table == 'zanzibar_node' and str(back) == str(t)
