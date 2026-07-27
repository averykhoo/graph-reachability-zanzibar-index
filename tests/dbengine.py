"""Which database engine a concurrency/HA test should run against.

Every test in this repo has always run on SQLite -- in-memory, or (for the
concurrency modules) file-backed WAL. That is a problem specific to THIS corner of
the suite, because the mechanisms these modules exist to test are no-ops or
unreachable on SQLite:

  * ``take_row_write_lock`` / ``_lock_store`` / ``_lock_source`` -- the ``FOR UPDATE``
    arm has literally never executed (pysqlite renders it to nothing; the SQLite arm
    is a different mechanism entirely, a no-op UPDATE taking the RESERVED lock);
  * ``assert_read_isolation`` -- returns immediately on SQLite by design, so it was
    only ever exercised against a hand-written fake session reporting a dialect
    string;
  * ``log_gap`` / ``WatermarkGap`` -- the hazard they guard is real MVCC
    (a lower log id committing after a higher one), which SQLite's single-writer
    model cannot produce.

So: set ``ZANZIBAR_TEST_DSN`` and the same test modules re-run against a real
server. Unset, they behave EXACTLY as before -- ``_sqlite_file_engine`` below is a
byte-for-byte copy of the ``_file_engine`` that lived in
``tests/test_connectedstore_multi_instance.py``, so the default gate is unaffected.

Fail-loud contract: ``ZANZIBAR_PG_REQUIRED=1`` turns "no DSN / unreachable DSN" into
a hard ERROR. A Postgres leg that silently degrades to SQLite (or to a pile of
skips) and then reports green is exactly the failure mode this file exists to
eliminate -- a green tick that proves nothing is worse than a red one.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import event
from sqlmodel import SQLModel, create_engine

# Import for the side effect of registering every table on SQLModel.metadata --
# ``create_all`` below must create all nine, whoever imports this helper first.
import connectedstore.models  # noqa: F401
import index_v4.models        # noqa: F401
import setengine.models       # noqa: F401

#: Point this at a real server (e.g.
#: ``postgresql+psycopg2://postgres@127.0.0.1:55432/zanzibar_test``) to re-run the
#: concurrency/HA modules there.
DSN_ENV_VAR = 'ZANZIBAR_TEST_DSN'
#: Set to ``1`` to make a missing/unreachable DSN a hard error instead of a
#: SQLite fallback or a skip.
REQUIRED_ENV_VAR = 'ZANZIBAR_PG_REQUIRED'

#: Mandatory for a server bind: ``connectedstore.assert_read_isolation`` REFUSES to
#: open a store whose snapshot can hide a committed log row, and psycopg2's default
#: is whatever the server default is. READ COMMITTED is also the level the whole
#: log-tailing design is written against (per-statement snapshots, so a catch-up
#: inside a long transaction really does reach the head).
SERVER_ISOLATION = 'READ COMMITTED'

#: Engines handed out by ``shared_engine`` that still hold pooled connections to the
#: shared database. They are disposed before the next test's DROP SCHEMA, because an
#: idle-in-transaction connection left behind by a thread would make that DDL block
#: (and then, thanks to the statement timeout below, fail loudly -- which is right,
#: but it would fail the WRONG test).
_LIVE_SERVER_ENGINES: list = []

#: DDL guard. A clean-slate that cannot complete means some earlier test leaked a
#: transaction; fail in seconds with that diagnosis rather than hanging the run.
_DDL_TIMEOUT_MS = 30_000


def rdbms_dsn() -> str | None:
    """The configured server DSN, or ``None`` for the default SQLite legs."""
    dsn = os.environ.get(DSN_ENV_VAR)
    return dsn or None


def rdbms_required() -> bool:
    return os.environ.get(REQUIRED_ENV_VAR, '') not in ('', '0', 'false', 'False')


def _require_dsn() -> str:
    """The DSN, or a hard failure when the run demanded one.

    Deliberately ``pytest.fail``, not ``pytest.skip``, under
    ``ZANZIBAR_PG_REQUIRED=1``: the whole point of that flag is that the operator
    asked for the server leg and a skip would report success for work never done."""
    dsn = rdbms_dsn()
    if dsn is None and rdbms_required():
        pytest.fail(
            f'{REQUIRED_ENV_VAR}=1 but {DSN_ENV_VAR} is unset: this run demanded the '
            f'real-server leg and would otherwise have silently reported green on '
            f'SQLite. Set {DSN_ENV_VAR} (e.g. '
            f'postgresql+psycopg2://postgres@127.0.0.1:55432/zanzibar_test) or unset '
            f'{REQUIRED_ENV_VAR}.')
    return dsn


def requires_rdbms() -> str:
    """For tests that are MEANINGLESS on SQLite (real row locks, real MVCC): return
    the DSN, else skip -- or hard-fail under ``ZANZIBAR_PG_REQUIRED=1``."""
    dsn = _require_dsn()
    if dsn is None:
        pytest.skip(f'needs a real RDBMS; set {DSN_ENV_VAR} (or {REQUIRED_ENV_VAR}=1 '
                    f'to make its absence an error)')
    return dsn


# --------------------------------------------------------------------------- #
# SQLite: unchanged from tests/test_connectedstore_multi_instance.py
# --------------------------------------------------------------------------- #

def _sqlite_file_engine(path):
    engine = create_engine(f'sqlite:///{path}',
                           connect_args={'check_same_thread': False, 'timeout': 60})

    @event.listens_for(engine, 'connect')
    def _busy_timeout(dbapi, _rec):
        cur = dbapi.cursor()
        cur.execute('PRAGMA busy_timeout=60000')
        # WAL: snapshot-isolated readers that never block the writer -- the honest
        # local simulation of a replica reading a store the primary writes.
        cur.execute('PRAGMA journal_mode=WAL')
        cur.close()
        # real transaction semantics (SQLAlchemy pysqlite workaround): let SQLAlchemy
        # emit BEGIN itself so a snapshot doesn't tear between statements.
        dbapi.isolation_level = None

    @event.listens_for(engine, 'begin')
    def _begin(conn):
        conn.exec_driver_sql('BEGIN')

    SQLModel.metadata.create_all(engine)
    return engine


# --------------------------------------------------------------------------- #
# Server: one database, one clean slate per test
# --------------------------------------------------------------------------- #

def server_engine(dsn: str | None = None, *, isolation_level: str = SERVER_ISOLATION,
                  clean: bool = False, **kwargs):
    """A server engine at an explicit isolation level. ``clean=True`` wipes the
    database first (see ``_clean_slate``).

    Exposed separately from ``shared_engine`` because the isolation-level tests need
    to open engines at levels the rest of the suite must never use."""
    dsn = dsn or requires_rdbms()
    engine = create_engine(dsn, isolation_level=isolation_level, **kwargs)
    if clean:
        _clean_slate(engine)
    _LIVE_SERVER_ENGINES.append(engine)
    return engine


def _clean_slate(engine) -> None:
    """``DROP SCHEMA public CASCADE`` + ``CREATE SCHEMA public`` + ``create_all``.

    WHY this and not ``drop_all``/``create_all`` or a per-test schema:

    * **Sequences must be reset, not just emptied.** Several tests reason about log
      id ORDER and contiguity (``advance_index``'s cursor, ``log_gap``, the
      ``at_least`` token domain), and PostgreSQL sequences are NOT rolled back by an
      aborted transaction -- a rejected write BURNS an id. ``drop_all``/``TRUNCATE``
      without ``RESTART IDENTITY`` would carry a stale, gap-riddled sequence into the
      next test and make "log ids are contiguous" assertions depend on test order.
      Dropping the schema drops the identity sequences with it, so every test starts
      at id 1 exactly as a fresh SQLite file does.
    * **Unambiguous.** One statement removes every table, sequence, index and
      constraint, including anything a future migration adds that ``drop_all`` would
      not know about.
    * **Fast enough.** Nine small tables: the whole wipe+recreate is a few tens of
      milliseconds, well under the per-test cost of the concurrency work itself.

    A per-test schema via ``search_path`` was the alternative; rejected because the
    production code never sets a search_path, so the tests would be exercising a
    configuration nothing else in the system uses."""
    for old in _LIVE_SERVER_ENGINES:
        # Pooled connections from an earlier test hold no locks once their sessions
        # closed, but a thread that leaked an open transaction would block the DDL.
        # Dispose first so a hang is impossible for that reason.
        old.dispose()
    _LIVE_SERVER_ENGINES.clear()
    with engine.begin() as conn:
        conn.exec_driver_sql(f"SET statement_timeout = {_DDL_TIMEOUT_MS}")
        conn.exec_driver_sql('DROP SCHEMA public CASCADE')
        conn.exec_driver_sql('CREATE SCHEMA public')
    SQLModel.metadata.create_all(engine)


def shared_engine(tmp_path, name: str, *, sqlite_factory=None):
    """THE entry point: the engine this test should use.

    * ``ZANZIBAR_TEST_DSN`` set -> a server engine at READ COMMITTED on a wiped
      database (``name`` is ignored -- one database, one clean slate per test).
    * unset -> a file-backed SQLite engine at ``tmp_path / name``: the WAL recipe
      above by default, or ``sqlite_factory(path)`` for a module whose historical
      engine differs (``tests/test_concurrency.py`` deliberately uses the
      rollback-journal default, and "unchanged on SQLite" means unchanged there
      too).

    Call this ONCE per test: a second call wipes the database the first one is
    using. (No test in the suite needs two independent databases; stores are already
    namespaced by ``store_id``.)"""
    dsn = _require_dsn()
    if dsn is None:
        return (sqlite_factory or _sqlite_file_engine)(tmp_path / name)
    return server_engine(dsn, clean=True)
