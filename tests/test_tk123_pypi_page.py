"""TK123 item 22 (2026-10-15): the PyPI page cannot drift from the code.

`tests/test_tk122_release_metadata.py` executes the page's one python block (the
quickstart). Item 22 added interim sections (async mode, outbox pruning, an exception
table) with plain fences. TK151 phase 6 (2026-10-23) deleted them, as the user decided on
2026-10-14: the page is now the pitch, status, install, the executed quickstart, the
documentation links and the license, and points to the docs site for async mode, outbox
pruning and exceptions. This module pins:

* every `from zanzibar... import ...` line on the page imports;
* every `store.<attr>` / `worker.<attr>` the page names exists on `Store`;
* the deleted sections stay deleted and the page links the three docs pages that replace
  them;
* the exception hierarchy on the docs site (`userdocs/reference/exceptions.md`, which
  replaced the page's table): every node is a real class with the parent and builtin base
  the tree shows, and every exception class `zanzibar` exports is in the tree;
* the async-mode, per-instance-sync, wildcard and outbox behaviour, run against a real store;
* a refused remove names the tuple (A22).

Sabotage evidence (2026-10-15, each applied alone to a temp copy of the page or by an
in-process patch, then reverted; `.scratch/tk123/i22/sab_page.out`):

    S1 page names `store.catch_upp()`                  -> red: names Store attributes that do not exist: ['catch_upp']
    S2 table says `StoreNotFound` base `ValueError`    -> red: AssertionError ('StoreNotFound', 'ValueError')
    S3 page imports `from zanzibar import Stor`        -> red: imports Stor from zanzibar; it does not exist
    S4 Store.check: untokened read falls back too      -> red: AssertionError at the stale-DENY line
    S5 remove message without the tuple                -> red: Regex pattern did not match.

S1-S3 targeted the deleted sections; the 2026-10-23 sabotage of their retargeted forms is
in each test's docstring.
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
EXCEPTIONS_PAGE = ROOT / "userdocs" / "reference" / "exceptions.md"
ASYNC_PAGE = ROOT / "userdocs" / "how-to" / "async-tokens.md"
SITE = "https://averykhoo.github.io/graph-reachability-zanzibar-index/"

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
# A line of the box-drawing tree: either a root (a bare builtin name at column 0) or a
# node: indent of "\u2502   " / "    " units, then "\u251c\u2500\u2500 " or
# "\u2514\u2500\u2500 ", the class name, and an optional [Builtin].
_NODE = re.compile(
    "^(?:([\u2502 ]*)([\u251c\u2514])\u2500\u2500 )?(\\w+)[ \\t]*(?:\\[(\\w+)\\])?", re.M)


def _page() -> str:
    return README.read_text(encoding="utf-8")


def imports_on(page: str) -> list[tuple[str, str]]:
    out = []
    for mod, names in _IMPORT.findall(page):
        out += [(mod, n.strip()) for n in names.strip("()").split(",") if n.strip()]
    return out


def test_every_import_on_the_page_resolves():
    """Floor history: `>= 5` (2026-10-15: quickstart + async + outbox import lines) became
    `>= 1` on 2026-10-23, when TK151 phase 6 deleted the async and outbox sections. The
    page's only `zanzibar` import is now the quickstart's `from zanzibar import Store`.

    Sabotage (2026-10-23, each alone on a temp copy of the page; the probe for every
    2026-10-23 sabotage in this module is `.scratch/wf-0p1/docs-pypi-readme-shrink/sab.py`):

        quickstart `import Store` -> `import Stor`  -> red: PYPI_README imports Stor from
                                                      zanzibar; it does not exist
        quickstart import line deleted              -> red: AssertionError: []
    """
    found = imports_on(_page())
    assert len(found) >= 1, found          # the quickstart's import line
    for mod, name in found:
        m = __import__(mod, fromlist=[name])
        assert hasattr(m, name), f"PYPI_README imports {name} from {mod}; it does not exist"


def test_every_store_attribute_the_page_names_exists():
    """Retargeted 2026-10-23 (TK151 phase 6). The required set was {catch_up, lag, refresh,
    watermark, index_stalled, stall_error, result_keys, excluded_keys, remove_tuple}, all
    named by the deleted "Async mode in brief" section; it is now the quickstart's
    {add_tuple, check}. The existence check over every name found is unchanged.

    Sabotage (2026-10-23, on a temp copy of the page via the same probe):

        one quickstart `store.check(` -> `store.chek(` -> red: PYPI_README names Store
                                                         attributes that do not exist: ['chek']
    """
    names = set(_ATTR.findall(_page()))
    assert {"add_tuple", "check"} <= names, names
    missing = sorted(n for n in names if not hasattr(Store, n))
    assert not missing, f"PYPI_README names Store attributes that do not exist: {missing}"


def test_the_folded_sections_stay_on_the_docs_site():
    """TK151 phase 6 (2026-10-23): the interim sections are deleted, not restated, and the
    page points to the docs pages that replace them.

    Sabotage (2026-10-23, each alone on a temp copy of the page via the same probe):

        re-add a `## Exceptions` section  -> red: the interim section '## Exceptions' is back
        rename the prune-outbox link      -> red: missing how-to/prune-outbox.html
    """
    page = _page()
    for heading in ("## Async mode in brief", "## Exceptions", "## Memory and storage"):
        assert f"\n{heading}\n" not in page, f"the interim section {heading!r} is back"
    assert "The rest of this page is a summary" not in page
    for target in ("how-to/async-tokens.html", "how-to/prune-outbox.html",
                   "reference/exceptions.html"):
        assert f"({SITE}{target})" in page, f"missing {target}"


def exception_tree(page: str) -> list[tuple[int, str, str | None]]:
    start = page.index("## Hierarchy")
    begin = page.index("```text\n", start)
    block = page[begin:page.index("\n```", begin + 1)]
    return [(len(indent) // 4 if branch else -1, name, base or None)
            for indent, branch, name, base in _NODE.findall(block)]


def _cls(name: str) -> type:
    return getattr(zanzibar, name, None) or getattr(builtins, name)


def _builtin_bases(cls: type) -> set[str]:
    """The builtin exception classes in `cls`'s MRO, less the ones every exception has."""
    return {b.__name__ for b in cls.__mro__
            if b.__module__ == "builtins" and b not in (object, BaseException, Exception)}


def test_the_exception_hierarchy_on_the_docs_site_matches_the_classes():
    """Replaces the PyPI page's exception-table check (2026-10-15, `len(rows) >= 15`; that
    table had 21 rows and lacked CascadeNotRun, UnsupportedByGraphIndex and
    DoublyBridgedShapeError). The table was deleted on 2026-10-23 (TK151 phase 6); its home
    is the docs site's hierarchy tree, which this now reads (floor `>= 25` nodes; the tree
    had 33 lines, 2 roots + 31 nodes, on 2026-10-23 before ForeignToken was added). Stronger
    than the old check: every node's PARENT is checked (roots included: the two root lines
    must be Exception and UserWarning), the builtins in each class's MRO must EQUAL its
    parent's plus the bracketed one (the page's "a class inherits every base of its
    parents"), and every exception class `zanzibar` exports must be in the tree.

    Sabotage (2026-10-23, on temp copies via the same probe, against this check's first
    form, a base-only test whose messages the review form below replaced):

        the tree as it stood (UnsupportedByGraphIndex shown with no builtin base, ForeignToken
        absent) -> red: ('UnsupportedByGraphIndex', 'is shown without a builtin base but has',
        ['ValueError']). Against that tree corrected to match src/ (control: green):
        StoreNotFound shown as [ValueError]       -> red: ('StoreNotFound', 'ValueError')
        ForeignToken removed                      -> red: exported but not in the tree: ['ForeignToken']
        StoreNotFound also listed under           -> red: ('StoreNotFound', 'is not a subclass of',
          AdmissionRejected                                 'AdmissionRejected')

    Review re-sabotage of the MRO-equality and root form (2026-10-23, probe
    `.scratch/wf-0p1/docs-review-pypi-readme-shrink/sab_tree.py`, output `sab_tree.out`):

        page as it stands  -> red: ('UnsupportedByGraphIndex', 'has builtin bases',
                              ['ValueError'], 'the tree shows', [])
        corrected tree     -> green (control)
        ShapeNoLongerAccepted shown [KeyError]  -> red: ('ShapeNoLongerAccepted', 'has builtin
                              bases', ['ValueError'], 'the tree shows', ['KeyError',
                              'LookupError', 'ValueError'])
        "UserWarning" root line deleted (UnprovenExtensionWarning then hangs off Exception,
                              which the parent check alone accepts) -> red at the roots assert
        InvariantViolation shown [ValueError]   -> red: ('InvariantViolation', 'has builtin
                              bases', ['AssertionError'], 'the tree shows', ['AssertionError',
                              'ValueError'])
    """
    tree = exception_tree(EXCEPTIONS_PAGE.read_text(encoding="utf-8"))
    assert len(tree) >= 25, tree
    assert [n for d, n, _ in tree if d < 0] == ["Exception", "UserWarning"], tree
    stack: list[str] = []            # stack[d + 1] is the node at depth d; stack[0] the root
    shown = set()
    for depth, name, base in tree:
        if depth < 0:                # a root line: a builtin, with no tree prefix
            assert getattr(builtins, name, None) is not None, (name, "is not a builtin")
            stack = [name]
            continue
        del stack[depth + 1:]
        parent = stack[depth]
        stack.append(name)
        cls = _cls(name)
        shown.add(name)
        assert issubclass(cls, _cls(parent)), (name, "is not a subclass of", parent)
        # "A class inherits every base of its parents": the builtins in the class's MRO are
        # exactly its parent's plus the bracketed one (plus itself, for a builtin node).
        want = _builtin_bases(_cls(parent))
        if base:
            want |= _builtin_bases(getattr(builtins, base))
        if getattr(builtins, name, None) is cls:
            want |= _builtin_bases(cls)
        got = _builtin_bases(cls)
        assert got == want, (name, "has builtin bases", sorted(got), "the tree shows", sorted(want))
    exported = {n for n in zanzibar.__all__ if isinstance(getattr(zanzibar, n), type)
                and issubclass(getattr(zanzibar, n), BaseException)}
    assert not exported - shown, f"exported but not in the tree: {sorted(exported - shown)}"
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

    Retargeted 2026-10-23 (TK151 phase 6): the PyPI page's async section, which carried
    the sentence, was deleted; the claim now lives on the docs site's async-tokens how-to,
    so the positive wording check reads that page. The negative check still covers both.
    Sabotage (2026-10-23, each alone on a temp copy of the how-to via the same probe):

        how-to loses the sentence                 -> red: AssertionError at the wording assert
        how-to says "the id of the write's row"   -> red: AssertionError at the negative assert
    """
    for page in (_page(), ASYNC_PAGE.read_text(encoding="utf-8")):
        assert "the id of the write's row" not in page
    assert ("Adding a tuple that is already stored writes nothing and returns the current "
            "watermark." in ASYNC_PAGE.read_text(encoding="utf-8"))
    with Session(engine) as s:
        st = Store(s, "a", schema=SCHEMA)
        t1 = st.add_tuple("user:bob", "viewer", "doc:d1")
        t2 = st.add_tuple("user:carol", "viewer", "doc:d1")
        t3 = st.add_tuple("user:bob", "viewer", "doc:d1")             # duplicate
        assert t3 == st.watermark() == t2 and t3 != t1
        assert st.check("user:bob", "viewer", "doc:d1", at_least=t3) is True
