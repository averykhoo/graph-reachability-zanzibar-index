"""TK185 (2026-11-20): the user docs stop saying reads are lenient, and `None` as a subject
predicate is documented in ONE place.

Since 0.1.3 a read on a ``Store`` or ``SetEngine`` that names an undeclared type or relation
raises ``UndeclaredTypeOrRelation`` (DEC-16). Before it, five pages said the opposite
("Writes are strict, reads are lenient", "a check naming an undeclared relation answers
False"). A sentence like that coming back is claim rot nothing else in the gate notices,
because a page can say it without running it. So:

* ``RETIRED_RX`` is scanned line by line over every ``userdocs/**/*.md`` (``_build``
  excluded), ``README.md`` and ``PYPI_README.md``; every hit fails, named as ``file:line``.
* ``None`` as the subject predicate means three things (bare on a read, refused on a write,
  "no filter" for ``lookup_reverse(subject_predicate=None)``). Its one home is the
  tuple-strings reference, section ``NONE_HEADING``, which must name all three calls; every
  other user page that talks about a ``None`` subject predicate must link there instead of
  restating it.

The behaviour itself is pinned by the executed examples in that section
(``tests/test_userdocs_examples.py``); this module pins only the wording and the link.

Sabotage evidence (2026-11-20), each applied alone to the real file, restored byte for
byte (probes ``.scratch/tk185/E_sabotage.py`` / ``E_sabotage2.py``):

    S1 semantics-vs-openfga.md's new heading put back to "## Writes are strict, reads are
       lenient":
         E  Left contains one more item: 'userdocs/explanation/semantics-vs-openfga.md:292'
         FAILED ...::test_no_page_says_reads_are_lenient -> 1 failed, 4 passed
    S2 the None section's ``lookup_reverse(..., subject_predicate=None)`` example loses the
       keyword:
         E  AssertionError: the None-predicate section does not mention 'subject_predicate=None'
         -> 1 failed, 4 passed
    S3 upgrade-0.1.md's link to the None section replaced by plain words:
         E  AssertionError: ['changelog.md']   (assert 1 >= 2)
         FAILED ...::test_other_pages_link_to_the_none_home -> 1 failed, 4 passed
    S4 instrument: ``RETIRED_RX`` never matches:
         E  assert [] == ['p.md:2', 'p.md:3', 'p.md:4']
         FAILED ...::test_retired_claim_scan_fires -> 1 failed, 4 passed
    S5 instrument: ``NONE_PRED_RX`` never matches:
         E  assert [] == ['bad.md']
         FAILED ...::test_none_link_check_fires -> 1 failed, 4 passed
    A first S4 that removed only the regex's first alternative stayed GREEN (5 passed): the
    synthetic page's lines are caught by the other alternatives too, so S4 neuters the whole
    pattern.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USERDOCS = ROOT / "userdocs"
TUPLE_STRINGS = USERDOCS / "reference" / "tuple-strings.md"
NONE_HEADING = "### `None` as the subject predicate"
NONE_ANCHOR = "tuple-strings.md#none-as-the-subject-predicate"

RETIRED_RX = re.compile(
    r"reads?\s+(?:are|is|stays?)\s+lenient"
    r"|writes are strict, reads"
    r"|undeclared (?:type or )?relation (?:answers|returns|matches)"
    r"|answers `?False`? for an undeclared"
    r"|is not refused this way",
    re.IGNORECASE)

# A line that talks about None as a subject predicate (or as "a bare subject").
NONE_PRED_RX = re.compile(r"`None`[^\n]{0,60}(?:subject predicate|bare subject)", re.IGNORECASE)


def _user_pages(root: Path = USERDOCS) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if "_build" not in p.relative_to(root).parts)


def find_retired_claims(paths: list[Path], base: Path = ROOT) -> list[str]:
    hits = []
    for page in paths:
        for n, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
            if RETIRED_RX.search(line):
                hits.append(f"{page.relative_to(base).as_posix()}:{n}")
    return hits


def none_section(text: str) -> str:
    """The body of the ``NONE_HEADING`` section, up to the next heading of any level."""
    start = text.index(NONE_HEADING) + len(NONE_HEADING)
    nxt = re.search(r"^#{1,6} ", text[start:], re.MULTILINE)
    return text[start:start + nxt.start()] if nxt else text[start:]


def pages_restating_none(paths: list[Path], home: Path = TUPLE_STRINGS) -> list[str]:
    """Pages other than ``home`` that talk about a None subject predicate without linking
    to its one home."""
    bad = []
    for page in paths:
        if page == home:
            continue
        text = page.read_text(encoding="utf-8")
        if NONE_PRED_RX.search(text) and NONE_ANCHOR not in text:
            bad.append(page.name)
    return bad


def test_no_page_says_reads_are_lenient():
    pages = _user_pages() + [ROOT / "README.md", ROOT / "PYPI_README.md"]
    assert len(pages) > 30, pages  # the scan really reads the site
    assert find_retired_claims(pages) == []


def test_retired_claim_scan_fires(tmp_path):
    page = tmp_path / "p.md"
    page.write_text("ok line\n## Writes are strict, reads are lenient\n"
                    "a check naming an undeclared relation answers `False`.\n"
                    "A read is not refused this way.\n", encoding="utf-8")
    assert find_retired_claims([page], base=tmp_path) == ["p.md:2", "p.md:3", "p.md:4"]


def test_none_predicate_has_one_home_naming_all_three_calls():
    section = none_section(TUPLE_STRINGS.read_text(encoding="utf-8"))
    for must in ("check", "add_tuple", "lookup_reverse", "subject_predicate=None",
                 "AdmissionRejected", "no filter", '"..."'):
        assert must in section, f"the None-predicate section does not mention {must!r}"


def test_other_pages_link_to_the_none_home():
    pages = _user_pages()
    linking = [p.name for p in pages if NONE_ANCHOR in p.read_text(encoding="utf-8")]
    assert len(linking) >= 2, linking  # changelog.md and upgrade-0.1.md at least
    assert pages_restating_none(pages) == []


def test_none_link_check_fires(tmp_path):
    home = tmp_path / "tuple-strings.md"
    home.write_text(f"{NONE_HEADING}\nbody\n", encoding="utf-8")
    good = tmp_path / "good.md"
    good.write_text(f"`None` means the bare subject; see [x]({NONE_ANCHOR}).\n", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text("On a read, `None` as the subject predicate means bare.\n", encoding="utf-8")
    assert pages_restating_none([home, good, bad], home=home) == ["bad.md"]
