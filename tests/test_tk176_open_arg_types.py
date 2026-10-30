"""TK176 (2026-10-30): the 0.1.1 install trial's F19 (BROKEN) and F10 / F5 (DOC GAP).

Source: ``docs/pypi-trial-0.1.1-2026-10-30.md``, F19 and F10 re-run first-hand against
``src/`` before the fix.

* **F19** ``Store(sync=...)`` picked the mode by truthiness: ``sync=None`` / ``0`` silently
  gave ASYNC mode (where an untokened check may serve a revoked grant until ``catch_up``),
  ``sync="false"`` gave sync. Only ``True`` / ``False`` are accepted now, on ``Store`` and
  ``Store.adopt``, before any statement runs.
* **F10** ``ops="pysets"`` failed later as ``'str' object has no attribute 'new'``;
  ``Store``, ``Store.adopt`` and ``SetEngine`` now refuse a non-``SetOps`` up front.
* **F5** a docs page that opens a SQLite file deletes it first, so a second run in the
  same folder prints what the page says (five pages did not).

SABOTAGE (2026-10-30, session; one asserted-unique anchor per mutation, this module only,
``-p no:cacheprovider``, file restored and checked). Literal tails, every one RED:

- S1 ``_check_open_args`` sync check disabled: ``rc=1 | 6 failed, 6 passed``
- S2 ``require_setops`` check disabled: ``rc=1 | 3 failed, 9 passed``
- S3 ``stall-recovery.md`` unlink line removed: ``rc=1 | 1 failed, 11 passed``
"""
import re
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar import Store
from zanzibar.setengine import PySets, SetEngine

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "type user\ntype doc\n  relations\n    define viewer: [user]\n"
BAD_SYNC = [None, 0, 1, "false", "async"]


@pytest.fixture
def engine():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        Store(session, "s", schema=SCHEMA)
        session.commit()
    return eng


@pytest.mark.parametrize("sync", BAD_SYNC, ids=repr)
def test_store_refuses_a_non_bool_sync(engine, sync):
    with Session(engine) as session:
        with pytest.raises(TypeError, match=r"sync must be True \(sync mode\) or False "
                                            r"\(async mode\), not " + re.escape(repr(sync))):
            Store(session, "s", sync=sync)


@pytest.mark.parametrize("sync", [True, False])
def test_store_accepts_a_bool_sync(engine, sync):
    with Session(engine) as session:
        store = Store(session, "s", sync=sync)
        store.add_tuple("user:a", "viewer", "doc:1")
        assert store.lag() == (0 if sync else 1)


def test_adopt_refuses_a_non_bool_sync(engine):
    with Session(engine) as session:
        with pytest.raises(TypeError, match="sync must be True"):
            Store.adopt(session, "fresh", schema=SCHEMA, sync=None)


@pytest.mark.parametrize("ops", ["pysets", None, object()], ids=["str", "None", "object"])
def test_ops_must_be_a_setops_everywhere(engine, ops):
    msg = r"ops must be a SetOps \(PySets or RoaringSets, from zanzibar\.setengine\)"
    with Session(engine) as session:
        with pytest.raises(TypeError, match=msg):
            Store(session, "s", ops=ops)
        with pytest.raises(TypeError, match=msg):
            Store.adopt(session, "fresh", schema=SCHEMA, ops=ops)
        with pytest.raises(TypeError, match=msg):
            SetEngine(session, "s", ops=ops)
    with Session(engine) as session:
        assert SetEngine(session, "s", ops=PySets).check("...", "user", "a", "viewer", "doc", "1") is False


def test_every_docs_page_deletes_its_sqlite_file_before_opening_it():
    """A page that opens ``sqlite:///X.db`` mentions ``"X.db"`` and ``unlink(missing_ok=True)``
    before that line (``errors.md`` unlinks both of its files in one loop)."""
    opened = 0
    missing = []
    for page in sorted((ROOT / "userdocs").rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        for m in re.finditer(r'create_engine\("sqlite:///([A-Za-z0-9_.-]+\.db)"\)', text):
            opened += 1
            before = text[:m.start()]
            if f'"{m.group(1)}"' not in before or "unlink(missing_ok=True)" not in before:
                missing.append(f"{page.relative_to(ROOT).as_posix()}: {m.group(1)}")
    assert opened >= 10, f"only {opened} sqlite:/// opens found: the pattern drifted"
    assert not missing, f"pages open a SQLite file without deleting it first: {missing}"
