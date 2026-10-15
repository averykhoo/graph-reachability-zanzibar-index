"""TK123 item 22 (2026-10-15): the PyPI page's interim sections cannot drift from the code.

`tests/test_tk122_release_metadata.py` executes the page's one python block (the
quickstart). The sections item 22 added (freshness tokens and async mode, stall recovery,
wildcards, exceptions, sessions, memory and storage) use plain fences, so nothing executes
them. This module pins what they claim:

* every `from zanzibar... import ...` line on the page imports;
* every `store.<attr>` / `worker.<attr>` the page names exists on `Store`;
* the exception table: each name imports from the top level, is a `ZanzibarError`, and
  has the builtin base the table states;
* the async-mode, per-instance-sync, wildcard and outbox claims, run against a real store;
* a refused remove names the tuple (A22).

Sabotage evidence (2026-10-15, each applied alone to a temp copy of the page or by an
in-process patch, then reverted; `.scratch/tk123/i22/sab_page.out`):

    S1 page names `store.catch_upp()`                  -> red: names Store attributes that do not exist: ['catch_upp']
    S2 table says `StoreNotFound` base `ValueError`    -> red: AssertionError ('StoreNotFound', 'ValueError')
    S3 page imports `from zanzibar import Stor`        -> red: imports Stor from zanzibar; it does not exist
    S4 Store.check: untokened read falls back too      -> red: AssertionError at the stale-DENY line
    S5 remove message without the tuple                -> red: Regex pattern did not match.
"""
import builtins
import re
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

import zanzibar
from zanzibar import (AdmissionRejected, LookupNotFresh, Store, ZanzibarError)
from zanzibar.graphindex import outbox_watermark, prune_outbox

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "PYPI_README.md"

SCHEMA = """
model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define viewer: [user, user:*] but not banned
"""

_IMPORT = re.compile(r"^\s*from (zanzibar[\w.]*) import ([\w, ()]+)$", re.M)
_ATTR = re.compile(r"(?<![\w.])(?:store|worker)\.(\w+)")   # not zanzibar.store.<fn>
_ROW = re.compile(r"^\| `(\w+)` \| `(\w+)` \|", re.M)


def _page() -> str:
    return README.read_text(encoding="utf-8")


def imports_on(page: str) -> list[tuple[str, str]]:
    out = []
    for mod, names in _IMPORT.findall(page):
        out += [(mod, n.strip()) for n in names.strip("()").split(",") if n.strip()]
    return out


def test_every_import_on_the_page_resolves():
    found = imports_on(_page())
    assert len(found) >= 5, found          # quickstart + async + outbox lines
    for mod, name in found:
        m = __import__(mod, fromlist=[name])
        assert hasattr(m, name), f"PYPI_README imports {name} from {mod}; it does not exist"


def test_every_store_attribute_the_page_names_exists():
    names = set(_ATTR.findall(_page()))
    assert {"catch_up", "lag", "refresh", "watermark", "index_stalled", "stall_error",
            "result_keys", "excluded_keys", "remove_tuple"} <= names, names
    missing = sorted(n for n in names if not hasattr(Store, n))
    assert not missing, f"PYPI_README names Store attributes that do not exist: {missing}"


def exception_table(page: str) -> list[tuple[str, str]]:
    start = page.index("## Exceptions")
    return _ROW.findall(page[start:page.index("\n## ", start + 1)])


def test_the_exception_table_matches_the_classes():
    rows = exception_table(_page())
    assert len(rows) >= 15, rows
    for name, base in rows:
        cls = getattr(zanzibar, name)       # top-level import, as the section says
        assert issubclass(cls, ZanzibarError), name
        assert issubclass(cls, getattr(builtins, base)), (name, base)
    assert not issubclass(zanzibar.InvariantViolation, ZanzibarError)


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'page.db'}")
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


def test_async_mode_claims(engine):
    with Session(engine) as s:
        st = Store(s, "a", schema=SCHEMA, sync=False)
        t = st.add_tuple("user:alice", "viewer", "doc:d1")
        assert isinstance(t, int) and t == st.watermark()
        assert st.lag() == 1
        assert st.check("user:alice", "viewer", "doc:d1") is False          # stale DENY
        assert st.check("user:alice", "viewer", "doc:d1", at_least=t) is True
        with pytest.raises(LookupNotFresh):
            st.lookup("user:alice", at_least=t)
        assert st.catch_up() == 1 and st.lag() == 0
        t2 = st.remove_tuple("user:alice", "viewer", "doc:d1")
        assert st.check("user:alice", "viewer", "doc:d1") is True           # stale ALLOW
        assert st.check("user:alice", "viewer", "doc:d1", at_least=t2) is False
        st.catch_up()
        assert st.check("user:alice", "viewer", "doc:d1") is False


def test_sync_is_per_instance_and_a_reopen_does_not_apply_the_backlog(engine):
    with Session(engine) as s, Session(engine) as s2:
        Store(s, "a", schema=SCHEMA, sync=False).add_tuple("user:carol", "viewer", "doc:d1")
        reader = Store(s2, "a")
        assert reader.sync is True
        assert reader.lag() == 1
        assert reader.check("user:carol", "viewer", "doc:d1") is False
        reader.catch_up()
        assert reader.check("user:carol", "viewer", "doc:d1") is True


def test_wildcard_section_and_outbox_pruning(engine):
    with Session(engine) as s:
        st = Store(s, "a", schema=SCHEMA)
        st.add_tuple("user:*", "viewer", "doc:d2")
        st.add_tuple("user:mallory", "banned", "doc:d2")
        assert st.check("user:bob", "viewer", "doc:d2") is True
        assert st.check("user:mallory", "viewer", "doc:d2") is False
        res = st.lookup_reverse("viewer", "doc:d2")
        assert ("user", "...", "any") in res.markers
        assert ("user", "mallory", "...") in st.excluded_keys(res)
        with pytest.raises(AdmissionRejected):
            st.add_tuple("user:*", "banned", "doc:d2")       # [user] has no user:*
        # Memory and storage: the outbox prune as the page writes it.
        assert prune_outbox(s, "a", outbox_watermark(s, "a")) >= 1
        s.commit()
        assert st.check("user:mallory", "viewer", "doc:d2") is False
        st.add_tuple("user:dave", "banned", "doc:d2")
        assert st.check("user:dave", "viewer", "doc:d2") is False


def test_a_refused_remove_names_the_tuple(engine):
    with Session(engine) as s:
        st = Store(s, "a", schema=SCHEMA)
        with pytest.raises(AdmissionRejected,
                           match=r"non-existent tuple cannot be removed: "
                                 r"user:alice viewer doc:d1 is not stored"):
            st.remove_tuple("user:alice", "viewer", "doc:d1")


def test_a_duplicate_add_returns_the_current_watermark_not_its_own_row(engine):
    """The page calls the token a "freshness token" and says a duplicate add returns the
    current `store.watermark()`, which may be another write's token. Review of item 22
    (2026-10-15) caught the earlier wording, "the id of the write's row in the store's tuple
    log", which is false for a duplicate: `.scratch/tk123/rev22/dup.py` printed
    `bob 1 carol 2 dup bob 2 watermark 2` (carol's token, not bob's row).

    Sabotage evidence (2026-10-15, each applied alone, then reverted byte-for-byte):

        S6 page restores "the id of the write's row"            -> red: AssertionError at the wording assert
        S7 TupleSource.add duplicate branch returns 0          -> red: assert (0 == 2)
    """
    page = _page()
    assert "the id of the write's row" not in page
    assert "Adding a tuple that is\nalready present changes nothing and returns the current" in page
    with Session(engine) as s:
        st = Store(s, "a", schema=SCHEMA)
        t1 = st.add_tuple("user:bob", "viewer", "doc:d1")
        t2 = st.add_tuple("user:carol", "viewer", "doc:d1")
        t3 = st.add_tuple("user:bob", "viewer", "doc:d1")             # duplicate
        assert t3 == st.watermark() == t2 and t3 != t1
        assert st.check("user:bob", "viewer", "doc:d1", at_least=t3) is True
