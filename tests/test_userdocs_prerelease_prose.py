"""TK151 (2026-10-23): pre-release prose on the user docs cannot survive the 0.1.0 cut.

While the source tree is ahead of the last release, several user pages say so: "0.1.0
(unreleased)", "not yet released", "a source build still reports 0.0.5", "the library is
at version 0.0.x". Every one of those sentences becomes false the moment
``zanzibar.__version__`` leaves 0.0.x, and nothing else in the gate notices.

The guard: when ``zanzibar.__version__`` is NOT a ``0.0.N`` version, every
``userdocs/**/*.md`` (the ``_build`` output excluded) is scanned line by line for
``PRERELEASE_RX`` and every hit fails the test, named as ``file:line``. While the version
is 0.0.x the prose is true and the guard finds nothing by construction.

``reference/changelog.md`` is covered ON PURPOSE: its "## 0.1.0 (unreleased)" heading is
exactly the kind of line that must change in the release commit (to a date), so the
guard reports it at the cut like any other page.

The guard is exercised two ways so that it cannot pass by being blind:

* ``test_guard_fires_on_synthetic_tree`` plants one line per regex alternative in a temp
  tree, plus one line in a ``_build`` dir that must be ignored, and asserts the exact hits.
  This stays meaningful after the cut.
* ``test_guard_fires_on_current_tree``: while the real version is 0.0.x, run the guard
  with ``__version__`` monkeypatched to "0.1.0" over the REAL tree and assert it reports at
  least the pages known to carry pre-release prose today; with "0.0.5" it reports nothing.
  After the cut that half is covered by ``test_no_prerelease_prose_after_release`` itself.
  **Replaced at the cut (2026-10-26)** by ``test_guard_armed_on_current_tree``: see the
  correction below.

Current hits (first-hand, 2026-10-23, version patched to "0.1.0"; see S3 below): explanation/limits.md,
how-to/errors.md, how-to/upgrade-0.1.md, reference/changelog.md, reference/environments.md,
reference/tables.md. All six are in ``KNOWN_CURRENT``; ``how-to/errors.md`` was added on
2026-10-23 once that page's restructure in the same review round had landed (its hit is
the ``TablesOutdated`` 0.0.5 note, now at line 182).
(``index.md``'s pre-release note had already been removed when this was written, and
``reference/api/index.md``'s ``"0.0.5"`` is an example value that the regex does not and
should not match.)

Correction 2026-10-26 (the 0.1.0 cut, session 2026-10-26e). ``__version__`` is now "0.1.0",
so the guard is armed on the real tree. At the cut it reported (literal, version bumped,
prose not yet rewritten): ['explanation/limits.md:287', 'how-to/errors.md:182',
'how-to/upgrade-0.1.md:15', 'reference/environments.md:23', 'reference/tables.md:119']
(``reference/changelog.md`` had already been re-dated). Each line was rewritten per
``docs/tk151-site-review-2026-10-26.md`` M1. ``KNOWN_CURRENT`` and the monkeypatched
real-tree half were removed (nothing pre-release is left to know); the replacement
``test_guard_armed_on_current_tree`` pins that the shipped version arms the guard.
TRAP: the next "[Unreleased]" CHANGELOG section must not be mirrored into
``userdocs/reference/changelog.md`` under that word (title it "Next release"), or narrow
``PRERELEASE_RX`` deliberately. Sabotage at the cut: see "Sabotage 2026-10-26" at the end.

Sabotage evidence (2026-10-23, literal pytest output), each applied alone and reverted:

    S1 PRERELEASE_RX's "unreleased" alternative changed to "unreleasedX":
         E       AssertionError: assert ['a.md:3', 'a... 'sub/b.md:1'] == ['a.md:1', 'a... 'sub/b.md:1']
         E       AssertionError: missing pre-release hits: ['reference/changelog.md', 'reference/environments.md']
         FAILED tests/test_userdocs_prerelease_prose.py::test_guard_fires_on_synthetic_tree
         FAILED tests/test_userdocs_prerelease_prose.py::test_guard_fires_on_current_tree
    S2 ``_is_prerelease`` body replaced by ``return True`` (the guard never arms):
         E       AssertionError: assert [] == ['a.md:1', 'a... 'sub/b.md:1']
         E       AssertionError: missing pre-release hits: ['explanation/limits.md', 'how-to/upgrade-0.1.md',
                 'reference/changelog.md', 'reference/environments.md', 'reference/tables.md']
         FAILED tests/test_userdocs_prerelease_prose.py::test_guard_fires_on_synthetic_tree
         FAILED tests/test_userdocs_prerelease_prose.py::test_guard_fires_on_current_tree
    S3 the real ``__version__`` in src/zanzibar/__init__.py set to "0.1.0" (the cut, with
       the prose left in place):
         E           Failed: pre-release prose survives at version 0.1.0; rewrite or delete these
                     lines: ['explanation/limits.md:269', 'how-to/errors.md:190',
                     'how-to/upgrade-0.1.md:15', 'reference/changelog.md:8',
                     'reference/environments.md:23', 'reference/tables.md:93']
         FAILED tests/test_userdocs_prerelease_prose.py::test_no_prerelease_prose_after_release
         FAILED tests/test_userdocs_prerelease_prose.py::test_guard_fires_on_current_tree
    Restored (files byte-compared against their pre-sabotage copies): 3 passed.

Sabotage 2026-10-26 (at the cut, version "0.1.0"; literal pytest output, each applied alone
and restored byte-for-byte by the runner):

    A ``_is_prerelease`` body replaced by ``return True`` (guard disarmed at 0.1.0):
         E       AssertionError: assert [] == ['a.md:1', 'a... 'sub/b.md:1']
         E       AssertionError: the guard is disarmed at the shipped version 0.1.0
         FAILED tests/test_userdocs_prerelease_prose.py::test_guard_fires_on_synthetic_tree
         FAILED tests/test_userdocs_prerelease_prose.py::test_guard_armed_on_current_tree
         2 failed, 1 passed
    B ``reference/changelog.md``'s "## 0.1.0 (2026-10-26)" put back to "## 0.1.0 (unreleased)":
         E           Failed: pre-release prose survives at version 0.1.0; rewrite or delete
                     these lines: ['reference/changelog.md:8']
         FAILED tests/test_userdocs_prerelease_prose.py::test_no_prerelease_prose_after_release
         FAILED tests/test_userdocs_prerelease_prose.py::test_guard_armed_on_current_tree
         2 failed, 1 passed
    C PRERELEASE_RX's "unreleased" alternative changed to "unreleasedX":
         E       AssertionError: assert ['a.md:3', 'a... 'sub/b.md:1'] == ['a.md:1', 'a... 'sub/b.md:1']
         FAILED tests/test_userdocs_prerelease_prose.py::test_guard_fires_on_synthetic_tree
         1 failed, 2 passed
    Restored: 3 passed.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import zanzibar

ROOT = Path(__file__).resolve().parents[1]
USERDOCS = ROOT / "userdocs"

PRERELEASE_RX = re.compile(
    r"unreleased|not yet released|reports[^\n]*0\.0\.5|is at version 0\.0", re.IGNORECASE)

def _is_prerelease(version: str) -> bool:
    return re.fullmatch(r"0\.0\.\d+", version) is not None


def find_prerelease_prose(root: Path = USERDOCS) -> list[str]:
    """``file:line`` for each pre-release sentence, or [] while the version is 0.0.x."""
    if _is_prerelease(zanzibar.__version__):
        return []
    hits = []
    for page in sorted(root.rglob("*.md")):
        rel = page.relative_to(root)
        if "_build" in rel.parts:
            continue
        for n, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
            if PRERELEASE_RX.search(line):
                hits.append(f"{rel.as_posix()}:{n}")
    return hits


def test_no_prerelease_prose_after_release():
    hits = find_prerelease_prose()
    if hits:
        pytest.fail(f"pre-release prose survives at version {zanzibar.__version__}; "
                    f"rewrite or delete these lines: {hits}")


def test_guard_fires_on_synthetic_tree(tmp_path, monkeypatch):
    (tmp_path / "sub").mkdir()
    (tmp_path / "_build").mkdir()
    (tmp_path / "a.md").write_text(
        "## 1.0.0 (Unreleased)\n"
        "released on 2026-01-01\n"
        "This is new in 1.0, which is not yet released.\n"
        "A source build still reports `__version__ == \"0.0.5\"`.\n",
        encoding="utf-8")
    (tmp_path / "sub" / "b.md").write_text("The library is at version 0.0.x.\n",
                                           encoding="utf-8")
    (tmp_path / "_build" / "c.md").write_text("unreleased\n", encoding="utf-8")
    monkeypatch.setattr(zanzibar, "__version__", "0.1.0")
    assert find_prerelease_prose(tmp_path) == ["a.md:1", "a.md:3", "a.md:4", "sub/b.md:1"]
    monkeypatch.setattr(zanzibar, "__version__", "0.0.5")
    assert find_prerelease_prose(tmp_path) == []


def test_guard_armed_on_current_tree():
    """Since the 0.1.0 cut (2026-10-26) the real version must ARM the guard.

    Before the cut this half monkeypatched the version to "0.1.0" and asserted the guard
    found the pages in ``KNOWN_CURRENT``; at the cut those lines were rewritten, so the
    real-tree check is ``test_no_prerelease_prose_after_release`` itself. What this test
    still pins is that the guard is not silently disarmed at the shipped version (a
    ``_is_prerelease`` that matches 0.1.x would make that test pass on any prose), and
    that the scan really reads the real tree (it finds the pages).
    """
    assert not _is_prerelease(zanzibar.__version__), (
        f"the guard is disarmed at the shipped version {zanzibar.__version__}")
    assert _is_prerelease("0.0.5") and not _is_prerelease("0.1.0")
    pages = [p for p in USERDOCS.rglob("*.md") if "_build" not in p.relative_to(USERDOCS).parts]
    assert len(pages) >= 20, f"the scan sees only {len(pages)} userdocs pages"
    assert find_prerelease_prose() == []
