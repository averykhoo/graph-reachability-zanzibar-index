"""TK140: one write path per store id (0.0.4 install trial BROKEN-2 / BROKEN-3).

Plan, census, decision and residuals: ``docs/tk140-one-write-path-per-store-2026-10-13.md``.

* BROKEN-2 (p12): a SECOND ``SetEngine`` opened on a store id that a ``Store``
  owns accepted an unlogged ``remove_tuple``. The grant then stayed ALLOWed by
  ``Store.check`` with ``lag 0`` and ``Store.remove_tuple`` refused it
  as non-existent (fail-OPEN, unrecoverable through the API). Fix: a ``SetEngine`` on a
  store id with a ``SchemaRecord`` is LOG-GOVERNED (``SetEngine._probe_log_governance``),
  so its direct writes raise ``UnloggedWriteRefused``; reads keep working.
* BROKEN-3 (p09): ``Store`` silently adopted a store id a standalone
  ``SetEngine`` had already written: the index was born empty (``check`` False, the set
  engine True) and removing the tuple raised ``InvariantViolation``. Fix:
  ``store/_store.py::_reject_unlogged_adoption`` refuses the first open with
  ``UnloggedTuplesPresent``, naming ``save_schema`` + ``build_index``.

SABOTAGE (2026-10-13d, literal observed output). Runner:
``.scratch/s1013d/tk140/sabotage.py`` -- each edit is an anchored replace (anchor count
asserted), the module re-run, the file restored byte-for-byte and its sha256 re-checked;
``git diff --stat src/`` was unchanged afterwards. The runner itself is scratch; this list
is the record.

- S1, the construction probe removed (``self._probe_log_governance()`` before
  ``self.rebuild()`` in ``SetEngine.__init__``)::

      FAILED tests/test_tk140_one_write_path.py::test_p12_second_engine_on_an_owned_store_is_log_governed
      FAILED tests/test_tk140_one_write_path.py::test_a_standalone_engine_probes_once_per_transaction
      2 failed, 10 passed
      E   assert False is True  (where False = <...SetEngine ...>.log_governed)

- S2, the write-time probe removed from BOTH ``add_tuple`` and ``remove_tuple``::

      FAILED tests/test_tk140_one_write_path.py::test_claim_after_open_refuses_the_next_transactions_write
      FAILED tests/test_tk140_one_write_path.py::test_a_standalone_engine_probes_once_per_transaction
      2 failed, 10 passed
      E   zanzibar.schema.errors.AdmissionRejected: non-existent tuple cannot be removed

- S3, the ``has_table`` guard removed from ``store_has_schema_record``::

      FAILED tests/test_tk140_one_write_path.py::test_setengine_only_database_without_the_schema_table
      1 failed, 11 passed
      E   sqlite3.OperationalError: no such table: zanzibar_schema_record

  and on PostgreSQL (``ZANZIBAR_TEST_DSN``, the same edit), where the failed SELECT would
  also abort the caller's transaction::

      E   psycopg2.errors.UndefinedTable: relation "zanzibar_schema_record" does not exist
      1 failed, 11 passed

- S4, the ``_reject_unlogged_adoption(session, store_id)`` call in
  ``Store.__init__`` replaced by ``pass``::

      FAILED tests/test_tk140_one_write_path.py::test_p09_adoption_of_unlogged_tuples_is_refused
      1 failed, 11 passed
      E   Failed: DID NOT RAISE UnloggedTuplesPresent

- S5, the accounting test weakened to "any tuple refuses" (``if n_tuples == n_add -
  n_remove:`` -> ``if False:``)::

      FAILED tests/test_tk140_one_write_path.py::test_a_fully_logged_store_is_adopted_on_first_open
      1 failed, 11 passed
      E   zanzibar.connectedstore.store.UnloggedTuplesPresent: store 'app' already has 1
          RelationTuple row(s) but its tuple log accounts for 1 (ADD 2 - REMOVE 1): ...

- S6, the ``session.rollback()`` before the raise removed::

      FAILED tests/test_tk140_one_write_path.py::test_p09_adoption_of_unlogged_tuples_is_refused
      1 failed, 11 passed
      E   assert not True  (where True = <...Session ...>.in_transaction())

- S7, the per-transaction memo disabled (``if txn is not None and txn is
  self._governance_probed_txn:`` -> ``if False:``)::

      FAILED tests/test_tk140_one_write_path.py::test_a_standalone_engine_probes_once_per_transaction
      1 failed, 11 passed
      E   AssertionError: assert ['solo', 'sol...solo', 'solo'] == ['solo']

- S8, ``SCHEMA_RECORD_TABLE`` misspelled (``'zanzibar_schema_records'``)::

      FAILED tests/test_tk140_one_write_path.py::test_the_probe_names_the_real_schema_table
      FAILED tests/test_tk140_one_write_path.py::test_p12_second_engine_on_an_owned_store_is_log_governed
      FAILED tests/test_tk140_one_write_path.py::test_claim_after_open_refuses_the_next_transactions_write
      3 failed, 9 passed

- S9 / S10 (``tests/test_refused_shape_comments.py``, which now scans store.py too): the
  ``# REFUSED SHAPE`` header of ``_reject_unlogged_adoption`` (S9) or of
  ``_reject_unlogged_write`` (S10) renamed to ``# REFUSED``::

      FAILED ...::test_every_in_scope_refusal_has_a_refused_shape_comment[src/zanzibar/connectedstore/store.py]
      FAILED ...::test_refused_shape_blocks_meet_the_floor[src/zanzibar/connectedstore/store.py]
      2 failed, 29 passed            (S10: the same two, [src/zanzibar/setengine/engine.py])
"""

from __future__ import annotations

import pytest
from sqlalchemy import event
from sqlmodel import Session, select

import zanzibar.setengine.engine as engine_mod
import zanzibar.store._store as store_mod
from zanzibar.store import (Store, SchemaRecord, TupleLog, TupleSource,
                                     UnloggedTuplesPresent, build_index, save_schema)
from zanzibar.setengine import RelationTuple, SetEngine, UnloggedWriteRefused

from tests.dbengine import shared_engine

SCHEMA = "model\n  schema 1.1\ntype user\ntype doc\n  relations\n    define viewer: [user]\n"
ALICE = ('...', 'user', 'alice', 'viewer', 'doc', 'd')
BOB = ('...', 'user', 'bob', 'viewer', 'doc', 'd')


def _file_engine(tmp_path, name='tk140.db'):
    """``tests/dbengine.py::shared_engine``: a file-backed SQLite database by default, a
    wiped PostgreSQL database at READ COMMITTED under ``ZANZIBAR_TEST_DSN`` -- so the
    governance probe and the refused open's rollback also run against a real server."""
    return shared_engine(tmp_path, name)


def _count(session, model, store_id):
    return len(session.exec(select(model).where(model.store_id == store_id)).all())


def test_the_probe_names_the_real_schema_table():
    """The probe names the table by string (layering); a rename must go red HERE."""
    assert engine_mod.SCHEMA_RECORD_TABLE == SchemaRecord.__tablename__
    assert 'store_id' in SchemaRecord.__table__.c
    assert list(SchemaRecord.__table__.primary_key.columns.keys()) == ['store_id']


def test_p12_second_engine_on_an_owned_store_is_log_governed(tmp_path):
    """BROKEN-2 positive pin (p12). Before TK140 the literal output was
    ``SetEngine.log_governed: False`` / ``Store check alice: True lag 0`` /
    ``cs.remove_tuple: AdmissionRejected non-existent tuple cannot be removed``."""
    eng = _file_engine(tmp_path)
    with Session(eng) as s:
        Store(s, 'app', schema=SCHEMA).add_tuple(*ALICE)
    with Session(eng) as s:
        se = SetEngine(s, 'app', SCHEMA)
        assert se.log_governed is True                    # latched at construction
        assert se.check(*ALICE) is True                   # reads stay legal
        with pytest.raises(UnloggedWriteRefused) as exc:
            se.remove_tuple(*ALICE)
        msg = str(exc.value)
        assert 'Store.remove_tuple' in msg and 'TK140' not in msg   # TK123 item 14
        with pytest.raises(UnloggedWriteRefused):
            se.add_tuple(*BOB)
        s.commit()
        assert _count(s, RelationTuple, 'app') == 1       # nothing written, on disk
    with Session(eng) as s:
        cs = Store(s, 'app')
        assert cs.check(*ALICE) is True and cs.lag() == 0
        cs.remove_tuple(*ALICE)                           # the store can still revoke
        assert cs.check(*ALICE) is False
        assert SetEngine(s, 'app', SCHEMA).check(*ALICE) is False


def test_claim_after_open_refuses_the_next_transactions_write(tmp_path):
    """The reverse order: a standalone engine opened on a FRESH id, the id then claimed by
    a Store. The construction probe saw nothing; the write probe (once per
    transaction) must refuse."""
    eng = _file_engine(tmp_path)
    sa = Session(eng)
    try:
        se = SetEngine(sa, 'app', SCHEMA)
        assert se.log_governed is False
        sa.commit()                                       # end the probing transaction
        with Session(eng) as sb:
            Store(sb, 'app', schema=SCHEMA).add_tuple(*ALICE)
        with pytest.raises(UnloggedWriteRefused):
            se.remove_tuple(*ALICE)
        with pytest.raises(UnloggedWriteRefused):
            se.add_tuple(*BOB)
        assert se.log_governed is True
        sa.rollback()
    finally:
        sa.close()
    with Session(eng) as s:
        assert _count(s, RelationTuple, 'app') == 1
        assert Store(s, 'app').check(*ALICE) is True


def test_p09_adoption_of_unlogged_tuples_is_refused(tmp_path):
    """BROKEN-3 positive pin (p09). Before TK140 the literal output was ``check carol:
    False`` / ``remove carol: InvariantViolation log row 1 (REMOVE) was rejected by the
    index ...``. Now the open is refused, writes nothing, and releases the session."""
    eng = _file_engine(tmp_path)
    with Session(eng) as s:
        SetEngine(s, 'app', SCHEMA).add_tuple(*ALICE)
        s.commit()
    with Session(eng) as s:
        with pytest.raises(UnloggedTuplesPresent) as exc:
            Store(s, 'app', schema=SCHEMA)
        msg = str(exc.value)
        assert 'build_index' in msg and 'save_schema' in msg and 'TK140' not in msg  # TK123 i14
        assert not s.in_transaction()                     # no SQLite write lock held
        assert s.get(SchemaRecord, 'app') is None         # nothing landed
    with Session(eng) as other:                           # another writer is not blocked
        SetEngine(other, 'other', SCHEMA).add_tuple(*BOB)
        other.commit()
    with Session(eng) as s:
        with pytest.raises(UnloggedTuplesPresent):
            Store(s, 'app', schema=SCHEMA, paranoia='full')


def test_p09_the_instead_recipe_adopts_the_store(tmp_path):
    """The refusal's INSTEAD, executed: save_schema, commit, build_index, then open."""
    eng = _file_engine(tmp_path)
    with Session(eng) as s:
        SetEngine(s, 'app', SCHEMA).add_tuple(*ALICE)
        s.commit()
    with Session(eng) as s:
        save_schema(s, 'app', SCHEMA)
        s.commit()
        build_index(s, 'app')
        cs = Store(s, 'app')
        assert cs.check(*ALICE) is True
        assert cs.source.check(*ALICE) is True
        cs.remove_tuple(*ALICE)
        assert cs.check(*ALICE) is False and cs.source.check(*ALICE) is False
        cs.add_tuple(*BOB)
        assert cs.check(*BOB) is True and cs.lag() == 0


def test_a_fully_logged_store_is_adopted_on_first_open(tmp_path):
    """A store written only through TupleSource (log accounts for every row) and opened by
    a Store for the first time later is NOT refused: the log replays it."""
    eng = _file_engine(tmp_path)
    with Session(eng) as s:
        save_schema(s, 'app', SCHEMA)
        s.commit()
        src = TupleSource(s, 'app')
        src.add(*ALICE)
        src.add(*BOB)
        src.remove(*BOB)
        s.commit()
    with Session(eng) as s:
        cs = Store(s, 'app')
        assert cs.lag() == 3                              # born at 0; the log is the path
        assert cs.catch_up() == 3
        assert cs.check(*ALICE) is True and cs.check(*BOB) is False
        assert cs.source.check(*ALICE) is True


def test_setengine_only_database_without_the_schema_table(tmp_path):
    """A database with NO ``zanzibar_schema_record`` table (a process that never imported
    the connected store, so ``create_all`` never made it): the probe must not touch the
    missing table. On PostgreSQL a SELECT from it would abort the caller's transaction."""
    eng = _file_engine(tmp_path)
    with eng.begin() as conn:
        conn.exec_driver_sql(f'DROP TABLE {SchemaRecord.__tablename__}')
    with Session(eng) as s:
        se = SetEngine(s, 'solo', SCHEMA)
        assert se.log_governed is False
        assert se.add_tuple(*ALICE) is True
        s.commit()
        assert se.check(*ALICE) is True
        se.remove_tuple(*ALICE)
        s.commit()
        assert se.check(*ALICE) is False


def test_a_standalone_engine_probes_once_per_transaction(monkeypatch, tmp_path):
    """Cost and memo pin: a standalone engine probes at construction and then at most once
    per transaction before a write; an engine a TupleSource owns never probes on write."""
    calls = []
    real = engine_mod.store_has_schema_record
    monkeypatch.setattr(engine_mod, 'store_has_schema_record',
                        lambda s, sid: calls.append(sid) or real(s, sid))
    eng = _file_engine(tmp_path)
    with Session(eng) as s:
        se = SetEngine(s, 'solo', SCHEMA)
        assert calls == ['solo']                          # construction
        for name in ('a', 'b', 'c'):
            se.add_tuple('...', 'user', name, 'viewer', 'doc', 'd')
        assert calls == ['solo']                          # same transaction: memoised
        s.commit()
        se.add_tuple('...', 'user', 'e', 'viewer', 'doc', 'd')
        se.remove_tuple('...', 'user', 'a', 'viewer', 'doc', 'd')
        assert calls == ['solo', 'solo']                  # new transaction: one probe
        s.commit()

        cs = Store(s, 'owned', schema=SCHEMA)
        n = len(calls)
        for name in ('a', 'b', 'c'):
            cs.add_tuple('...', 'user', name, 'viewer', 'doc', 'd')
        assert len(calls) == n                            # governed: never probes on write


def test_the_store_owners_own_engine_is_still_governed(tmp_path):
    """ZT-P1-8a unchanged: the engine a Store owns refuses direct writes."""
    eng = _file_engine(tmp_path)
    with Session(eng) as s:
        cs = Store(s, 'app', schema=SCHEMA)
        assert cs.source.engine.log_governed is True
        with pytest.raises(UnloggedWriteRefused):
            cs.source.engine.add_tuple(*ALICE)
        cs.add_tuple(*ALICE)
        assert _count(s, TupleLog, 'app') == 1


def test_a_reopened_store_is_never_reaudited(monkeypatch, tmp_path):
    """The adoption check runs only on the open that CREATES the cursor; a store that has
    an index is not re-counted on every open (and a later open is not refused). The cost
    claim is pinned by counting ``_adoption_counts`` calls, not inferred from the opens
    succeeding (on a legitimately reopened store the counts agree anyway).

    Sabotage (2026-10-13d, TK140 review finding): the ``has_cursor`` short-circuit in
    ``_reject_unlogged_adoption`` disabled (``if has_cursor is not None:`` -> ``if
    False:``); literal output::

        FAILED tests/test_tk140_one_write_path.py::test_p09_the_instead_recipe_adopts_the_store
        FAILED tests/test_tk140_one_write_path.py::test_a_reopened_store_is_never_reaudited
        2 failed, 11 passed in 1.10s
        E   AssertionError: assert ['app', 'app', 'app'] == ['app']

    (before this pin the same edit went ``1 failed, 11 passed``, with only the p09 recipe
    test catching it incidentally)."""
    calls = []
    real = store_mod._adoption_counts
    monkeypatch.setattr(store_mod, '_adoption_counts',
                        lambda s, sid: calls.append(sid) or real(s, sid))
    eng = _file_engine(tmp_path)
    with Session(eng) as s:
        Store(s, 'app', schema=SCHEMA).add_tuple(*ALICE)
    assert calls == ['app']                               # the cursor-creating open counts
    with Session(eng) as s:
        assert Store(s, 'app', schema=SCHEMA).check(*ALICE) is True
        assert Store(s, 'app').check(*ALICE) is True
    assert calls == ['app']                               # reopens never re-count


def test_the_adoption_counts_are_one_statement(monkeypatch, tmp_path):
    """The three adoption counts (``RelationTuple`` rows, ``TupleLog`` ADD and REMOVE
    rows) are read in ONE SQL statement, i.e. one snapshot. PostgreSQL READ COMMITTED
    re-snapshots per statement and nothing serialises this read against writers there,
    so separate COUNTs let a logged write committing between them be seen by one count and
    not the other. RUN on PG by the TK140 review (2026-10-13d, the three-COUNT code): a
    fully-logged store refused to open with ``UnloggedTuplesPresent store 'race-0b9f5d44'
    already has 1 RelationTuple row(s) but its tuple log accounts for 2 (ADD 2 - REMOVE
    0)``. A statement-level interleaving cannot be forced from a test, so the pin is
    structural: every SELECT on the tuple table issued by the first open is one that also
    reads the log.

    Sabotage (2026-10-13d): ``_adoption_counts`` rewritten back to three separate
    ``session.exec(select(func.count())...)`` statements; literal output::

        FAILED tests/test_tk140_one_write_path.py::test_the_adoption_counts_are_one_statement
        1 failed, 12 passed in 1.54s
        E   AssertionError: adoption counts split across 3 statements: ...
    """
    eng = _file_engine(tmp_path)
    with Session(eng) as s:
        save_schema(s, 'app', SCHEMA)
        s.commit()
        src = TupleSource(s, 'app')
        src.add(*ALICE)
        s.commit()
    rt, log = RelationTuple.__tablename__, TupleLog.__tablename__
    real = store_mod._adoption_counts
    seen = []

    def spy(session, store_id):
        stmts = []
        listener = lambda conn, cur, statement, *a: stmts.append(statement)
        event.listen(eng, 'before_cursor_execute', listener)
        try:
            return real(session, store_id)
        finally:
            event.remove(eng, 'before_cursor_execute', listener)
            seen.extend(stmts)

    monkeypatch.setattr(store_mod, '_adoption_counts', spy)
    with Session(eng) as s:
        cs = Store(s, 'app')                     # fully logged: adopted
        assert cs.catch_up() == 1 and cs.check(*ALICE) is True
    counting = [q for q in seen if 'count(' in q.lower()]
    assert counting, f'anti-vacuity: no COUNT statement observed in {seen}'
    assert len(counting) == 1 and rt in counting[0] and log in counting[0], (
        f'adoption counts split across {len(counting)} statements: {counting}')


def test_an_empty_store_id_bootstraps_as_before(tmp_path):
    eng = _file_engine(tmp_path)
    with Session(eng) as s:
        cs = Store(s, 'fresh', schema=SCHEMA)
        cs.add_tuple(*ALICE)
        assert cs.check(*ALICE) is True


def test_a_separate_id_built_index_does_not_govern_the_source_engine_twice(tmp_path):
    """``build_index`` into a separate index id copies the schema there; the SOURCE store's
    log-governed engine and its writes are unaffected."""
    eng = _file_engine(tmp_path)
    with Session(eng) as s:
        cs = Store(s, 'src', schema=SCHEMA)
        cs.add_tuple(*ALICE)
    with Session(eng) as s:
        build_index(s, 'src', index_store_id='src-idx')
    with Session(eng) as s:
        cs = Store(s, 'src')
        cs.add_tuple(*BOB)
        assert cs.check(*BOB) is True
