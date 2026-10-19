"""TK157: ``Store.adopt`` -- the adoption recipe (``save_schema`` + ``build_index`` + open
``Store``) as one call, returning ``(store, BuildReport)``.

Plan and decisions D1-D7: ``docs/tk157-adopt-helper-2026-10-19.md``. The hand recipe it
replaces is pinned by ``tests/test_tk140_one_write_path.py::test_p09_the_instead_recipe_adopts_the_store``.

What is pinned here beyond "it works":

* D2 atomicity -- a build that fails after the schema was saved leaves NO ``SchemaRecord``
  (the hand recipe commits between the steps; adopt does not).
* D3 refuse-before-build -- an outdated SQLite file (``TablesOutdated``) and a refused
  isolation level (``UnsafeIsolationLevel``) leave no cursor and no schema committed.
  Without D3 the SAME exception type still surfaces (from the ``Store`` open at the end), so
  the type alone would pass by PASSING; the pins read the committed state instead.

Sabotage, observed 2026-10-19 (each restored green; literal output in the test docstrings):
S1 a ``session.commit()`` after ``save_schema`` in ``Store.adopt`` (D2); S2 the
``refuse_reusable_node_ids(session)`` call deleted from ``Store.adopt`` (D3); S3 the
``assert_read_isolation(session)`` call deleted from ``Store.adopt`` (D3). After the review
fix (same day): S4 the early ``paranoia`` / ``ops`` checks deleted (4 failed, 15 passed);
S5 ``object_wildcard_shapes`` dropped from the ``save_schema`` call (1 failed, 18 passed).
The S1-S3 counts below were taken at 14 tests, before the review fix added five.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select

import zanzibar
import zanzibar.store._store as store_mod
import zanzibar.store.build as build_mod
from zanzibar.setengine import SetEngine
from zanzibar.setengine.setops import PySets
from zanzibar.store import (BuildReport, IndexCursor, IndexExists, SchemaRecord, Store,
                            StoreNotFound, SchemaMismatch, TablesNotCreated, TablesOutdated,
                            TupleSource, UnloggedTuplesPresent, UnsafeIsolationLevel,
                            load_schema, save_schema)

from tests.dbengine import shared_engine

SCHEMA = "model\n  schema 1.1\ntype user\ntype doc\n  relations\n    define viewer: [user]\n"
OTHER = ("model\n  schema 1.1\ntype user\ntype doc\n  relations\n"
         "    define viewer: [user]\n    define editor: [user]\n")
ALICE = ('...', 'user', 'alice', 'viewer', 'doc', 'd')
BOB = ('...', 'user', 'bob', 'viewer', 'doc', 'd')


def _unlogged_store(tmp_path, store_id='app', name='tk157.db'):
    """A store id written by a standalone SetEngine: the shape ``Store`` refuses to open."""
    eng = shared_engine(tmp_path, name)
    with Session(eng) as s:
        SetEngine(s, store_id, SCHEMA).add_tuple(*ALICE)
        s.commit()
    return eng


def _committed(eng, store_id='app'):
    """``(SchemaRecord present, IndexCursor present)`` as a FRESH session sees them."""
    with Session(eng) as s:
        return (s.get(SchemaRecord, store_id) is not None,
                s.exec(select(IndexCursor)
                       .where(IndexCursor.index_store_id == store_id)).first() is not None)


def test_adopt_opens_an_unlogged_store_and_returns_the_build_report(tmp_path):
    eng = _unlogged_store(tmp_path)
    with Session(eng) as s:
        with pytest.raises(UnloggedTuplesPresent) as exc:   # the shape adopt exists for
            Store(s, 'app', schema=SCHEMA)
        assert "Store.adopt(session, 'app', schema=schema)" in str(exc.value)
    with Session(eng) as s:
        store, report = Store.adopt(s, 'app', schema=SCHEMA)
        assert isinstance(store, Store) and isinstance(report, BuildReport)
        assert report.constructor == 'bulk'
        assert report.cursor.index_store_id == 'app' and report.cursor.applied_log_id == 0
        assert store.check(*ALICE) is True and store.source.check(*ALICE) is True
        store.remove_tuple(*ALICE)
        assert store.check(*ALICE) is False and store.source.check(*ALICE) is False
        store.add_tuple(*BOB)
        assert store.check(*BOB) is True and store.lag() == 0
    with Session(eng) as s:                                 # reopened like any store
        assert Store(s, 'app').check(*BOB) is True


def test_adopt_passes_bulk_and_store_options_through(tmp_path):
    eng = _unlogged_store(tmp_path)
    with Session(eng) as s:
        store, report = Store.adopt(s, 'app', schema=SCHEMA, bulk=False, sync=False,
                                    paranoia='full', ops=PySets)
        assert report.constructor == 'incremental'
        assert store.sync is False and store.paranoia == 'full'
        assert store.source.engine.ops is PySets       # the default is RoaringSets
        assert store.check(*ALICE) is True


def test_adopt_with_the_schema_already_persisted(tmp_path):
    """schema=None reads the persisted schema; passing the identical one is a no-op."""
    eng = _unlogged_store(tmp_path)
    with Session(eng) as s:
        save_schema(s, 'app', SCHEMA)
        s.commit()
        store, _ = Store.adopt(s, 'app')
        assert store.check(*ALICE) is True
    eng2 = _unlogged_store(tmp_path, name='tk157b.db')
    with Session(eng2) as s:
        save_schema(s, 'app', SCHEMA)
        s.commit()
        store, _ = Store.adopt(s, 'app', schema=SCHEMA)
        assert store.check(*ALICE) is True


def test_adopt_without_any_schema_is_store_not_found(tmp_path):
    eng = _unlogged_store(tmp_path)
    with Session(eng) as s:
        with pytest.raises(StoreNotFound):
            Store.adopt(s, 'app')
        assert not s.in_transaction()
    assert _committed(eng) == (False, False)


def test_adopt_with_a_different_schema_is_schema_mismatch(tmp_path):
    eng = _unlogged_store(tmp_path)
    with Session(eng) as s:
        save_schema(s, 'app', SCHEMA)
        s.commit()
        with pytest.raises(SchemaMismatch):
            Store.adopt(s, 'app', schema=OTHER)
        assert not s.in_transaction()      # only adopt's own rollback releases this one
    assert _committed(eng) == (True, False)


def test_adopt_an_already_indexed_store_is_index_exists(tmp_path):
    eng = _unlogged_store(tmp_path)
    with Session(eng) as s:
        Store.adopt(s, 'app', schema=SCHEMA)
    with Session(eng) as s:
        with pytest.raises(IndexExists, match=r"open it with Store\(session, 'app'\)") as exc:
            Store.adopt(s, 'app', schema=SCHEMA)
        assert 'rebuild_index' not in str(exc.value)    # build_index's advice, not adopt's
        assert exc.value.index_store_id == 'app'
        assert not s.in_transaction()
        assert Store(s, 'app').check(*ALICE) is True    # the advice works


def test_adopt_a_fully_logged_store(tmp_path):
    """Adopting a store the log already accounts for works too (build from the snapshot)."""
    eng = shared_engine(tmp_path, 'tk157.db')
    with Session(eng) as s:
        save_schema(s, 'app', SCHEMA)
        s.commit()
        src = TupleSource(s, 'app')
        src.add(*ALICE)
        src.add(*BOB)
        src.remove(*BOB)
        s.commit()
    with Session(eng) as s:
        store, report = Store.adopt(s, 'app')
        assert report.cursor.applied_log_id == 3 and store.lag() == 0
        assert store.check(*ALICE) is True and store.check(*BOB) is False


def test_adopt_an_empty_store_id(tmp_path):
    eng = shared_engine(tmp_path, 'tk157.db')
    with Session(eng) as s:
        store, report = Store.adopt(s, 'fresh', schema=SCHEMA)
        assert report.cursor.applied_log_id == 0
        store.add_tuple(*ALICE)
        assert store.check(*ALICE) is True


def test_adopt_refuses_a_dirty_session(tmp_path):
    eng = _unlogged_store(tmp_path)
    with Session(eng) as s:
        s.add(SchemaRecord(store_id='pending', schema_text=SCHEMA,
                           object_wildcard_shapes='[]'))
        with pytest.raises(ValueError, match='Store.adopt owns the transaction'):
            Store.adopt(s, 'app', schema=SCHEMA)


def test_a_failed_build_leaves_no_schema_behind(tmp_path, monkeypatch):
    """D2: the schema and the index commit together.

    Sabotage S1 (2026-10-19, ``session.commit()`` added after ``save_schema`` in
    ``Store.adopt``), pytest printed ``E       assert (True, False) == (False, False)``
    (1 failed, 13 passed)."""
    eng = _unlogged_store(tmp_path)

    def concurrent(*a, **k):
        raise RuntimeError('concurrent writes (simulated)')
    monkeypatch.setattr(build_mod, '_require_quiescent', concurrent)
    with Session(eng) as s:
        with pytest.raises(RuntimeError, match='simulated'):
            Store.adopt(s, 'app', schema=SCHEMA)
        assert not s.in_transaction()
    assert _committed(eng) == (False, False)


def _downgrade_node_table(engine) -> None:
    """The 0.0.x ``zanzibar_node`` DDL (no AUTOINCREMENT); twin of the TK154 test's helper."""
    with engine.begin() as c:
        ddl = c.execute(text("select sql from sqlite_master where type='table' "
                             "and name='zanzibar_node'")).scalar()
        indexes = [row[0] for row in c.execute(text(
            "select sql from sqlite_master where type='index' and tbl_name='zanzibar_node' "
            "and sql is not null"))]
        assert 'AUTOINCREMENT' in ddl.upper()
        c.execute(text('DROP TABLE zanzibar_node'))
        c.execute(text(ddl.replace(' AUTOINCREMENT', '').replace(' autoincrement', '')))
        for sql in indexes:
            c.execute(text(sql))


def test_an_outdated_sqlite_file_is_refused_before_anything_is_built(tmp_path):
    """D3, SQLite only (the TK154 refusal is a no-op on other dialects).

    Sabotage S2 (2026-10-19, ``refuse_reusable_node_ids(session)`` deleted from
    ``Store.adopt``): ``TablesOutdated`` still raised -- by the ``Store`` open at the end --
    and the pin went red on state:
    ``E       assert (True, True) == (False, False)`` (1 failed, 13 passed)."""
    eng = create_engine(f'sqlite:///{tmp_path / "tk157-old.db"}')
    SQLModel.metadata.create_all(eng)
    _downgrade_node_table(eng)
    with Session(eng) as s:
        SetEngine(s, 'app', SCHEMA).add_tuple(*ALICE)
        s.commit()
    with Session(eng) as s:
        with pytest.raises(TablesOutdated):
            Store.adopt(s, 'app', schema=SCHEMA)
        assert not s.in_transaction()
    assert _committed(eng) == (False, False)
    eng.dispose()


def test_a_refused_isolation_level_is_refused_before_anything_is_built(tmp_path, monkeypatch):
    """D3. On SQLite ``assert_read_isolation`` is a no-op, so the refusal a SERIALIZABLE
    PostgreSQL bind gets (``tests/test_postgres_ha.py::test_serializable_bind_is_refused``)
    is stood in for by patching the name ``Store.adopt`` and ``Store.__init__`` both call.

    Sabotage S3 (2026-10-19, ``assert_read_isolation(session)`` deleted from
    ``Store.adopt``): the ``Store`` open still raised ``UnsafeIsolationLevel`` and the pin
    went red on state:
    ``E       assert (True, True) == (False, False)`` (1 failed, 13 passed)."""
    eng = _unlogged_store(tmp_path)

    def refuse(session):
        raise UnsafeIsolationLevel('SERIALIZABLE (simulated)')
    monkeypatch.setattr(store_mod, 'assert_read_isolation', refuse)
    with Session(eng) as s:
        with pytest.raises(UnsafeIsolationLevel):
            Store.adopt(s, 'app', schema=SCHEMA)
    assert _committed(eng) == (False, False)


def test_missing_tables_are_tables_not_created(tmp_path):
    eng = create_engine(f'sqlite:///{tmp_path / "tk157-empty.db"}')
    with Session(eng) as s:
        with pytest.raises(TablesNotCreated):
            Store.adopt(s, 'app', schema=SCHEMA)
        assert not s.in_transaction()
    eng.dispose()


def test_adopt_is_public_on_the_top_level_store_with_an_ascii_docstring():
    doc = zanzibar.Store.adopt.__doc__
    assert callable(getattr(zanzibar.Store, 'adopt', None)) and doc
    assert doc.isascii()                                 # TK153: help() stays ASCII
    assert 'TK1' not in doc and 'D2' not in doc          # no internal ids in user help


@pytest.mark.parametrize('kwargs, exc_type, match', [
    ({'paranoia': 'bogus'}, ValueError, 'bad paranoia level'),
    ({'paranoia': -7}, ValueError, 'bad paranoia level'),
    ({'ops': object()}, TypeError, 'ops must be a SetOps'),
])
def test_a_bad_store_argument_is_refused_before_anything_is_built(tmp_path, kwargs,
                                                                  exc_type, match):
    """The Store-open arguments are checked before the build. ``Store.__init__`` refuses
    them too, but only after ``build_index`` has committed -- so the type alone would pass
    by PASSING; the pin reads the committed state.

    Sabotage S4 (2026-10-19, the early ``resolve_paranoia_level`` / ``isinstance(ops,
    SetOps)`` checks deleted from ``Store.adopt``): the paranoia cases and the env case
    went red on state, ``E       assert (True, True) == (False, False)``, and the ops case
    raised ``AttributeError: 'object' object has no attribute 'new'`` from the late
    ``Store`` open (4 failed, 15 passed)."""
    eng = _unlogged_store(tmp_path)
    with Session(eng) as s:
        with pytest.raises(exc_type, match=match):
            Store.adopt(s, 'app', schema=SCHEMA, **kwargs)
        assert not s.in_transaction()
    assert _committed(eng) == (False, False)
    with Session(eng) as s:                              # and a corrected retry adopts
        store, _ = Store.adopt(s, 'app', schema=SCHEMA)
        assert store.check(*ALICE) is True


def test_a_bad_paranoia_environment_is_refused_before_anything_is_built(tmp_path,
                                                                        monkeypatch):
    eng = _unlogged_store(tmp_path)
    monkeypatch.setenv('ZANZIBAR_PARANOIA', 'bogus')
    with Session(eng) as s:
        with pytest.raises(ValueError, match='bad paranoia level'):
            Store.adopt(s, 'app', schema=SCHEMA)
    assert _committed(eng) == (False, False)


OWC_SCHEMA = ("model\n  schema 1.1\ntype user\ntype doc\n  relations\n"
              "    define viewer: [user]\n")
OWC_SHAPES = frozenset({('doc', 'viewer')})


def test_adopt_saves_the_object_wildcard_shapes(tmp_path):
    """``object_wildcard_shapes`` reaches ``save_schema``: dropping it would persist a
    schema without the shapes (a semantic change) while every other test stayed green.

    Sabotage S5 (2026-10-19, ``save_schema(session, store_id, schema)`` without the shapes
    in ``Store.adopt``): ``E               ValueError: object wildcard doc:* (relation
    'viewer') is not a declared object-wildcard shape ('doc', 'viewer')`` (1 failed,
    18 passed)."""
    eng = shared_engine(tmp_path, 'tk157-owc.db')
    star = ('...', 'user', 'alice', 'viewer', 'doc', '*')
    with Session(eng) as s:
        SetEngine(s, 'app', OWC_SCHEMA, object_wildcard_shapes=OWC_SHAPES).add_tuple(*star)
        s.commit()
    with Session(eng) as s:
        store, _ = Store.adopt(s, 'app', schema=OWC_SCHEMA,
                               object_wildcard_shapes=OWC_SHAPES)
        assert load_schema(s, 'app')[1] == OWC_SHAPES
        q = ('...', 'user', 'alice', 'viewer', 'doc', 'd1')
        assert store.check(*q) is True and store.source.check(*q) is True
