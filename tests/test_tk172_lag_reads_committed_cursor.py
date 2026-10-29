"""TK172 (2026-10-30): ``Store.lag()`` counts against the COMMITTED cursor row.

Found by the 0.1.0 fresh-user install trial (finding F18,
``docs/pypi-trial-0.1.0-2026-10-30.md``): ``lag()`` compared against the ORM-cached
``self.cursor.applied_log_id``, which nothing re-reads. Once ANOTHER instance ran
``catch_up()``, a long-lived instance (the monitoring one the docs tell you to keep)
kept reporting the old backlog on every call, while its own ``check()`` already
served the applied index. It only over-reported, never under-reported.
"""
from sqlmodel import Session, SQLModel, create_engine

from zanzibar.store import Store

_SCHEMA = "type user\ntype doc\n  relations\n    define viewer: [user]\n"


def test_lag_sees_another_instances_catch_up(tmp_path):
    """Sabotage (2026-10-30): with ``lag()`` back on ``self.cursor.applied_log_id``
    -> ``assert 1 == 0`` on the ``watcher.lag()`` line (red)."""
    engine = create_engine(f"sqlite:///{tmp_path / 'lag.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as w_session, Session(engine) as c_session:
        watcher = Store(w_session, "app", schema=_SCHEMA, sync=False)
        watcher.add_tuple("user:a", "viewer", "doc:1")
        assert watcher.lag() == 1

        assert Store(c_session, "app", sync=False).catch_up() == 1

        assert watcher.lag() == 0                       # no refresh() needed
        assert watcher.check("user:a", "viewer", "doc:1") is True
