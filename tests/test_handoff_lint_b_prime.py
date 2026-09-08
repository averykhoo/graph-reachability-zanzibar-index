"""The two `handoff_lint.py` checks Phase B-prime needed before the board can become a
one-hop stub (docs/tree-sole-authority-spec-2026-08-29.md, B-prime prerequisites 2 and 7,
decided 2026-09-06c).

  * `check_priority_capacities` falls back to the TASK TREE when the board has no row
    table. Its only branch for "no rows" used to be a violation, so the cutover commit
    would have had to delete the check -- and a capacity nobody checks is no capacity.
    Pre-cutover it still reads the board; the fallback is not a second opinion.
  * `check_session_receipt` (new): the newest root-ledger entry must carry both trial
    receipts -- the literal `task lint:` line and the `read: <vocab>` line. The C1 tally
    (docs/tasktool-trial-protocol.md section 6, 2026-09-06) found four shapes for the
    lint line and two entries with neither line. All four shapes are pinned GREEN here;
    a check that rejected three of the four would have been commented out.

Every red asserted below was watched go red before it was believed; the observed lines
are in the docstrings. Both checks run against a temp root via the same
`monkeypatch.setattr(handoff_lint, "REPO", ...)` pattern as tests/test_handoff_lint_row_ids.py.

INSTRUMENT CONTROLS, run 2026-09-06c against patched copies (not kept as permanent
tests: each is a one-line patch of a helper, and the guarding test below already
carries the control corpus):

  * `_newest_entry_lines` replaced by "the whole ledger" -- the receipt check then finds
    the OLDER entry's lines and reports nothing. Observed from
    `test_receipt_is_red_when_either_line_is_missing_from_the_newest_entry`::

        AssertionError: []

  * `if not tree:` -> `if tree is None:` in `check_priority_capacities` -- an empty
    harvest falls through to the budget arithmetic. Still red, but for the WRONG reason
    (`found 0 NOW open task files (-), must be exactly 1`), which is why
    `test_capacities_do_not_coast_on_an_empty_tree` asserts on the message text and not
    only on the count.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from scripts import handoff_lint  # noqa: E402

TABLE_BOARD = """# HANDOFF -- the board

| id | item | pri | size | deps | moved |
|---|---|---|---|---|---|
| `P3` | leg 7 4c-ii | **NOW** | L | - | 2026-08-21b |
| `P6` | ttuStarFree (ii) | **NEXT** | M | - | 2026-08-20b |
"""

STUB_BOARD = """# HANDOFF -- one hop

Start with `python scripts/task.py board`. There is no row table here any more.
"""

TASK_FILE = """---
id: {tid}
title: {tid} title
brief:
pri: {pri}
size: M
deps: []
related: []
parent:
labels: []
source: hand
source_hash:
created: 2026-08-21
moved: 2026-08-21
updated: 2026-08-21
closed:
---

Summary.

## Log
"""


def _run(check) -> list[str]:
    out: list[str] = []
    check(out.append)
    return out


def _write_tasks(root: Path, pris: dict[str, str]) -> None:
    """Replace the tree wholesale: each call is a fresh corpus, never an accretion."""
    d = root / "tasks"
    if d.is_dir():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    # A tombstone decoy: tasks/BANNER.md was retired at the 2026-09-06 cutover, but this
    # linter still excludes it by NAME (TASKS_NON_TASK_MD), and the decoy `pri: NOW` line
    # is what proves the exclusion. task.py's own lint check 12 is what refuses the file.
    (d / "BANNER.md").write_text("2026-08-21 banner\npri: NOW\n", encoding="utf-8")
    for tid, pri in pris.items():
        (d / f"{tid}-x.md").write_text(TASK_FILE.format(tid=tid, pri=pri), encoding="utf-8")


def _write_ledger(root: Path, newest_body: str, older_body: str = "") -> None:
    ledger = root / "docs" / "history"
    ledger.mkdir(parents=True, exist_ok=True)
    (ledger / "session-log.md").write_text(
        "# session log\n\n## 2026-09-06c newest\n\n%s\n\n## 2026-09-06b older\n\n%s\n"
        % (newest_body, older_body),
        encoding="utf-8",
    )


# --- check_priority_capacities: tree fallback -------------------------------------------

def test_capacities_read_the_board_while_it_has_a_table(tmp_path, monkeypatch):
    """Pre-cutover behaviour is unchanged: the board's rows are the ranking, and a tree
    that disagrees (two NOW files) is NOT consulted -- task.py lint check 5 owns that."""
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    (tmp_path / "HANDOFF.md").write_text(TABLE_BOARD, encoding="utf-8")
    _write_tasks(tmp_path, {"P3": "NOW", "P6": "NOW"})
    assert _run(handoff_lint.check_priority_capacities) == []


def test_capacities_fall_back_to_the_tree_when_the_table_is_gone(tmp_path, monkeypatch):
    """A stub board plus a well-budgeted tree is green; the same stub over a tree with
    two NOW files, or four NEXT files, is red and the message names the tree.

    Observed 2026-09-06c (two NOW files)::

        tasks/ (the board has no row table, so the tree is the ranking): found 2 NOW
        open task files (['P3-x.md', 'P6-x.md']), must be exactly 1. ...
    """
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    (tmp_path / "HANDOFF.md").write_text(STUB_BOARD, encoding="utf-8")
    _write_tasks(tmp_path, {"P3": "NOW", "P6": "NEXT", "R6": "NEXT", "P4": "LATER"})
    assert _run(handoff_lint.check_priority_capacities) == []

    _write_tasks(tmp_path, {"P3": "NOW", "P6": "NOW"})
    out = _run(handoff_lint.check_priority_capacities)
    assert len(out) == 1 and "found 2 NOW open task files" in out[0], out
    assert "tasks/ (the board has no row table" in out[0], out
    assert "P3-x.md" in out[0] and "P6-x.md" in out[0], out

    _write_tasks(tmp_path, {"P3": "NOW", "A": "NEXT", "B": "NEXT", "C": "NEXT",
                            "D": "NEXT"})
    out = _run(handoff_lint.check_priority_capacities)
    assert len(out) == 1 and "found 4 NEXT open task files" in out[0], out


def test_capacities_do_not_coast_on_an_empty_tree(tmp_path, monkeypatch):
    """None (no tree) and an empty harvest are both still violations: the fallback must
    not turn "the parser read nothing" into a satisfied budget. BANNER.md is excluded
    from the harvest by name, and it carries a decoy `pri: NOW` line to prove it."""
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    (tmp_path / "HANDOFF.md").write_text(STUB_BOARD, encoding="utf-8")
    out = _run(handoff_lint.check_priority_capacities)
    assert len(out) == 1 and "no task tree to fall back to" in out[0], out

    _write_tasks(tmp_path, {})
    out = _run(handoff_lint.check_priority_capacities)
    assert len(out) == 1 and "has no open task files" in out[0], out


def test_zero_now_message_is_true_of_zero(tmp_path, monkeypatch):
    """BUG FOUND 2026-08-21 (audit T3), fixed in `task.py` the same day and left unported
    here for 17 days; refiled 2026-09-07 as `TK64` and fixed 2026-09-07b.

    The `len(now) != 1` failure printed the `> 1` branch's explanation on a count of
    ZERO, beside a bare `-` where the id list goes. Observed 2026-09-07b by reverting
    only the message (not the check) and running this test::

        E  AssertionError: ['tasks/ (the board has no row table, so the tree is the
        E  ranking): found 0 NOW open task files (-), must be exactly 1. NOW is what an
        E  unassigned session picks up; two of them is no ranking at all.']

    Both halves are wrong for this corpus: the tree HAS a ranking problem, but it is
    that nothing is ranked, and the `-` reads as an id rather than as the absence of
    one. The zero case became reachable in this file only at the 2026-09-06 cutover,
    when the check gained its tree fallback -- before that a board with no NOW row
    tripped the "no board rows" branch instead.

    One check, one message, true on both sides of the `!=` -- the same resolution as
    `tests/test_tasktool.py::test_regression_zero_now_message_is_true_of_zero`, which
    pins the sibling. The two checkers disagreeing about one invariant is worse than
    either being wrong alone: whichever you meet first teaches you the rule.
    """
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    (tmp_path / "HANDOFF.md").write_text(STUB_BOARD, encoding="utf-8")

    # A tree that parses fine and simply ranks nothing -- not an empty harvest.
    _write_tasks(tmp_path, {"P3": "LATER", "P6": "LATER"})
    out = _run(handoff_lint.check_priority_capacities)
    assert len(out) == 1, out
    assert "found 0 NOW open task files" in out[0], out
    assert "(none)" in out[0] and "(-)" not in out[0], out
    assert "two of them" not in out[0], out
    assert "with none it has no answer" in out[0], out

    # The SAME sentence on the other side of the !=, where it must also be true.
    _write_tasks(tmp_path, {"P3": "NOW", "P6": "NOW"})
    out = _run(handoff_lint.check_priority_capacities)
    assert len(out) == 1, out
    assert "found 2 NOW open task files" in out[0], out
    assert "with more than one it has no ranking" in out[0], out


# --- check_session_receipt ----------------------------------------------------------------

LINT_SHAPES = (
    "task lint: clean (12 checks, 162 task file(s) parsed)",
    "`task lint: clean (12 checks, 162 task file(s) parsed)`",
    "lint: `task lint: clean (12 checks, 162 task file(s) parsed)`",
    "`python scripts/task.py lint` -> `task lint: clean (13 checks, 167 task file(s) "
    "parsed, 1 warning(s))`",
    "    task lint: clean (12 checks, 162 task file(s) parsed)",
    "task lint: 2 violation(s)",
)

# The post-cutover vocabulary (2026-09-06): `board + HANDOFF` / `HANDOFF only` were the
# trial's words for reading a row table that no longer exists. Older ledger entries keep
# them; only the newest entry is checked, so the shapes below are the ones it can carry.
READ_SHAPES = (
    "read: board + note",
    "`read: board only`",
    "**read: board + note.**",
    "read: board + note (the board query first, then `HANDOFF.md`, the one-hop note)",
)


@pytest.mark.parametrize("lint_line", LINT_SHAPES)
@pytest.mark.parametrize("read_line", READ_SHAPES)
def test_receipt_accepts_every_shape_the_ledger_actually_uses(tmp_path, monkeypatch,
                                                              lint_line, read_line):
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    _write_ledger(tmp_path, "prose\n%s\n%s\nmore prose" % (lint_line, read_line))
    assert _run(handoff_lint.check_session_receipt) == []


def test_receipt_is_red_when_either_line_is_missing_from_the_newest_entry(tmp_path,
                                                                           monkeypatch):
    """Both halves, each watched go red on its own. The OLDER entry carries both lines
    in every case, so a check that scanned the whole ledger instead of the newest entry
    would pass here -- that is the sabotage this test controls for.

    Observed 2026-09-06c (lint line missing)::

        docs/history/session-log.md: the newest entry (## 2026-09-06c newest) has no
        `task lint: clean (N checks, M task file(s) parsed)` / `task lint: N
        violation(s)` line. ...
    """
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    both = "task lint: clean (12 checks, 162 task file(s) parsed)\nread: board only"

    _write_ledger(tmp_path, "read: board + note\nno lint line here", older_body=both)
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "has no `task lint:" in out[0], out
    assert "2026-09-06c newest" in out[0], out

    _write_ledger(tmp_path, "task lint: clean (12 checks, 162 task file(s) parsed)",
                  older_body=both)
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "has no `read:" in out[0], out
    assert "board only | board + note" in out[0], out

    _write_ledger(tmp_path, "nothing at all", older_body=both)
    assert len(_run(handoff_lint.check_session_receipt)) == 2

    # A near-miss is not a receipt: a read line outside the vocabulary, a lint line
    # without the counts. Both are what a session writes when it is paraphrasing.
    _write_ledger(tmp_path, "task lint: clean\nread: everything", older_body=both)
    assert len(_run(handoff_lint.check_session_receipt)) == 2

    # The RETIRED vocabulary is a near-miss too: a post-cutover entry that says
    # `read: board + HANDOFF` is describing a file shape that no longer exists.
    _write_ledger(tmp_path, "task lint: clean (12 checks, 162 task file(s) parsed)\n"
                            "read: board + HANDOFF", older_body=both)
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "has no `read:" in out[0], out


def test_receipt_refuses_a_ledger_with_no_entries(tmp_path, monkeypatch):
    """Non-vacuity: a ledger the entry regex cannot find a heading in is a broken
    instrument, not a clean one."""
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    ledger = tmp_path / "docs" / "history"
    ledger.mkdir(parents=True)
    (ledger / "session-log.md").write_text("# session log\n\nno headings\n", encoding="utf-8")
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "no `## <session-key> ` entry" in out[0], out

    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path / "nowhere"))
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and out[0].startswith("MISSING:"), out


def test_the_two_checks_are_in_the_list_and_nothing_was_inserted():
    """Appended, never inserted: the task.py lint checks are cited by number, and this
    file keeps the same habit so a citation like "the eleventh check" stays true.

    ⚠ This asserted `names[-1] == "check_session_receipt"` until 2026-09-08b, and that
    pinned the wrong property. LAST-ness is not what keeps an ordinal citation true --
    POSITION is -- so the assertion made the next legitimate APPEND fail while still
    permitting an insertion anywhere after index 10. `check_restated_counts` (`TK58`) was
    the append that found it. Pinning the index instead keeps the real invariant and lets
    the tuple grow at the end, which is the only place it is allowed to grow.
    """
    names = [c.__name__ for c in handoff_lint.CHECKS]
    assert names[1] == "check_priority_capacities", names
    assert names[10] == "check_session_receipt", names
    assert names[11] == "check_restated_counts", names
    assert len(names) == 12, names
