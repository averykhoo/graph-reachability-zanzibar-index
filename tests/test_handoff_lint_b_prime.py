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


# --- check_session_receipt: the conditional `asked:` receipt (TK96, 2026-09-27) ----------
#
# An `ASK-<n>` row at NEXT is a question the session must raise with the user in chat; the
# newest ledger entry then carries `asked: <every NEXT ask>`. Decisions and the full
# sabotage/mutation record: docs/tk96-ask-channel-2026-09-27.md. The mutation sweep's
# literal observations are transcribed on `test_asked_receipt_is_red_until_every_next_ask_
# is_named` below.

BOTH = "task lint: clean (13 checks, 227 task file(s) parsed)\nread: board only"


def _write_closed(root: Path, tid: str, pri: str) -> None:
    d = root / "tasks" / "closed"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{tid}-x.md").write_text(TASK_FILE.format(tid=tid, pri=pri), encoding="utf-8")


def test_asked_receipt_is_red_until_every_next_ask_is_named(tmp_path, monkeypatch):
    """THE property that makes the nag fail-red (TK96 Traps: steps 1-2 alone are a doc
    warning). Two asks at NEXT; the receipt must name BOTH. The OLDER entry names both in
    every case, so a check that read the whole ledger instead of the newest entry passes
    here -- the same control `test_receipt_is_red_when_either_line_is_missing_from_the_
    newest_entry` carries for the other two receipts.

    Sabotage, observed 2026-09-27d before this was believed (the new block in
    `check_session_receipt` deleted -- i.e. steps 1-2 landed and step 3 did not)::

        AssertionError: []

    and end to end, `scripts/handoff_lint.py` (what `verify.sh lean` step 4f runs) on a
    copy of the live tree with `ASK-2` flipped to NEXT and no `asked:` line -- rc=1,
    `handoff_lint: 1 violation(s)`, the one failure being (headline elided)::

        FAIL: docs/history/session-log.md: the newest entry (## 2026-09-27c ...) -- it
        has no `asked:` line, but ASK-2 sit(s) at NEXT. A NEXT ask is a question only
        the user can answer, ...

    while the same copy with the new block disabled printed `handoff_lint: clean (12
    checks)`, rc=0 -- steps 1-2 alone failing by passing, as the row's Traps predicted.
    Full transcript: docs/tk96-ask-channel-2026-09-27.md section 4.
    """
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    _write_tasks(tmp_path, {"TK1": "NOW", "ASK-3": "NEXT", "ASK-5": "NEXT",
                            "ASK-4": "LATER"})
    older = BOTH + "\nasked: ASK-3, ASK-5"

    _write_ledger(tmp_path, BOTH, older_body=older)
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "it has no `asked:` line" in out[0], out
    assert "ASK-3, ASK-5 sit(s) at NEXT" in out[0], out
    assert "2026-09-06c newest" in out[0], out

    # An honest `none` is the one report this receipt exists to refuse.
    _write_ledger(tmp_path, BOTH + "\nasked: none", older_body=older)
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "it says `asked: none`" in out[0], out

    # Naming one of two is not the receipt. Ids are compared exactly.
    _write_ledger(tmp_path, BOTH + "\nasked: ASK-3", older_body=older)
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "does not name ASK-5, but ASK-5 sit(s)" in out[0], out

    _write_ledger(tmp_path, BOTH + "\nasked: ASK-5, ASK-35", older_body=older)
    out = _run(handoff_lint.check_session_receipt)
    assert any("does not name ASK-3," in o for o in out), out

    # `none` then an id reads as `none`: the id after it is not a receipt.
    _write_ledger(tmp_path, BOTH + "\nasked: none, ASK-3, ASK-5", older_body=older)
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "it says `asked: none`" in out[0], out

    # THE GRAMMAR (decided 2026-09-28): the receipt is the ONE comma list directly after
    # `asked: `. Commentary after it is ignored, so an id mentioned there -- or in prose on
    # another line of the entry -- names nothing. A sentence ABOUT an unasked question is
    # not the receipt that it was asked. Mutants V7 (ids harvested from the whole line)
    # and V8 (from every line of the entry once any `asked:` exists) were GREEN before
    # these three cases existed; observed KILLED 2026-09-28, docs/tk96-ask-channel-
    # 2026-09-27.md, the 2026-09-28 correction.
    for body in ("asked: ASK-3 (ASK-5 deferred)", "asked: ASK-3 (ASK-5 later)",
                 "asked: ASK-3\nASK-5 is still open"):
        _write_ledger(tmp_path, BOTH + "\n" + body, older_body=older)
        out = _run(handoff_lint.check_session_receipt)
        assert len(out) == 1 and "does not name ASK-5, but ASK-5 sit(s)" in out[0], (
            body, out)

    # GREEN: both named, on one line or across two, in any order -- and two receipts on
    # ONE line are unioned too (mutant V5, first match per line only, was GREEN).
    for body in ("asked: ASK-3, ASK-5", "asked: ASK-5,ASK-3",
                 "asked: ASK-3\nasked: ASK-5", "asked: ASK-3, ASK-4, ASK-5",
                 "asked: ASK-3; asked: ASK-5"):
        _write_ledger(tmp_path, BOTH + "\n" + body, older_body=older)
        assert _run(handoff_lint.check_session_receipt) == [], body


ASKED_SHAPES = (
    "asked: ASK-3",
    "`asked: ASK-3`",
    "**asked: ASK-3.**",
    "asked: ASK-3 (raised at session start; the user said: later)",
    "  - asked: ASK-3",
    "asked: `ASK-3`",        # a backticked id: only the NORMALISED line reads as a receipt
)

ASKED_NEAR_MISSES = (
    "asked ASK-3",           # no colon
    "asked: ask-3",          # the id is case-exact, as in the tree
    "asked: ASK-3b",         # not the id ASK-3
    "asked: ASK-3-x",
    "unasked: ASK-3",        # a different word
    "asked: nonetheless ASK-3",
    "asked: ASK 3",
)


@pytest.mark.parametrize("line", ASKED_SHAPES)
def test_asked_receipt_accepts_the_shapes_the_other_receipts_accept(tmp_path, monkeypatch,
                                                                    line):
    """Same normalisation as the lint and read receipts (backticks and `**` dropped,
    searched not anchored), so the ledger's existing writing habits carry over."""
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    _write_tasks(tmp_path, {"TK1": "NOW", "ASK-3": "NEXT"})
    _write_ledger(tmp_path, "prose\n%s\n%s\nmore prose" % (BOTH, line))
    assert _run(handoff_lint.check_session_receipt) == []


@pytest.mark.parametrize("line", ASKED_NEAR_MISSES)
def test_asked_receipt_refuses_near_misses(tmp_path, monkeypatch, line):
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    _write_tasks(tmp_path, {"TK1": "NOW", "ASK-3": "NEXT"})
    _write_ledger(tmp_path, "%s\n%s" % (BOTH, line))
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "ASK-3 sit(s) at NEXT" in out[0], (line, out)


def test_asked_receipt_is_optional_without_a_next_ask(tmp_path, monkeypatch):
    """No open ask at NEXT, no requirement -- not for a LATER ask, not for a CLOSED file
    whose frontmatter still says NEXT (closed/ is not a standing nag), and not for an id
    that merely resembles the series. `asked: none` is accepted here."""
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    _write_tasks(tmp_path, {"TK1": "NOW", "ASK-3": "LATER", "ASKX-4": "NEXT",
                            "TASK-5": "NEXT", "ASK-8b": "NEXT", "ASK-11": "HOLD",
                            "ASK-12": "SOMEDAY"})
    _write_closed(tmp_path, "ASK-7", "NEXT")
    for body in (BOTH, BOTH + "\nasked: none", BOTH + "\nasked: ASK-7"):
        _write_ledger(tmp_path, body)
        assert _run(handoff_lint.check_session_receipt) == [], body

    # Optional is not unchecked: a line that IS written must still name real ids.
    _write_ledger(tmp_path, BOTH + "\nasked: ASK-9")
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "names ASK-9 on its `asked:` line" in out[0], out

    # The instrument control for the loop above: the SAME tree with ASK-3 promoted is red,
    # so the green was the harvester reading NEXT correctly, not reading nothing.
    _write_tasks(tmp_path, {"TK1": "NOW", "ASK-3": "NEXT"})
    _write_closed(tmp_path, "ASK-7", "NEXT")
    _write_ledger(tmp_path, BOTH)
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "ASK-3 sit(s) at NEXT" in out[0], out


def test_asked_receipt_refuses_an_id_the_tree_does_not_know(tmp_path, monkeypatch):
    """A typo guard: `ASK-9` named beside the real `ASK-3` would otherwise pass. A CLOSED
    ask is known (ask, get the answer, close -- all in one session), so it is accepted."""
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    _write_tasks(tmp_path, {"TK1": "NOW", "ASK-3": "NEXT"})
    _write_closed(tmp_path, "ASK-7", "LATER")

    _write_ledger(tmp_path, BOTH + "\nasked: ASK-3, ASK-7")
    assert _run(handoff_lint.check_session_receipt) == []

    _write_ledger(tmp_path, BOTH + "\nasked: ASK-3, ASK-9")
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "names ASK-9 on its `asked:` line" in out[0], out


def test_asked_receipt_counts_an_ask_at_now_as_at_next(tmp_path, monkeypatch):
    """Decided 2026-09-28 (TK96 fixer): "at NEXT" means at NEXT OR ABOVE. The nag exists so
    the user is asked; an ask promoted to NOW is at least as pressing as one at NEXT, and
    a promotion must never be the way to silence it (`handoff_lint.py::_ASK_NAG_PRIS`).
    Mutant V4r (the harvest back to NEXT only) observed KILLED 2026-09-28."""
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    _write_tasks(tmp_path, {"TK1": "NEXT", "ASK-3": "NOW", "ASK-4": "LATER"})
    _write_ledger(tmp_path, BOTH)
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "it has no `asked:` line" in out[0], out
    assert "ASK-3 sit(s) at NEXT or NOW" in out[0], out

    _write_ledger(tmp_path, BOTH + "\nasked: none")
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "it says `asked: none`" in out[0], out

    _write_ledger(tmp_path, BOTH + "\nasked: ASK-3")
    assert _run(handoff_lint.check_session_receipt) == []


def test_asked_receipt_refuses_none_beside_names(tmp_path, monkeypatch):
    """Decided 2026-09-28 (TK96 fixer; the verifier's V6 -- "none beats names" was GREEN,
    i.e. unpinned either way): an entry that says `asked: none` on one line and names ids
    on another contradicts itself, and is RED whether or not an ask is at NEXT. The
    control: `asked: none, ASK-3` is ONE receipt that reads as `none` (the grammar pinned
    in `test_asked_receipt_is_red_until_every_next_ask_is_named`), so with no ask at NEXT
    it is green -- the contradiction check fires on two receipts, not on one."""
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    _write_tasks(tmp_path, {"TK1": "NOW", "ASK-3": "NEXT", "ASK-5": "NEXT"})
    _write_ledger(tmp_path, BOTH + "\nasked: none\nasked: ASK-3, ASK-5")
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1, out
    assert "says `asked: none` AND names ASK-3, ASK-5" in out[0], out

    _write_tasks(tmp_path, {"TK1": "NOW", "ASK-3": "LATER"})
    _write_ledger(tmp_path, BOTH + "\nasked: ASK-3\nasked: none")
    out = _run(handoff_lint.check_session_receipt)
    assert len(out) == 1 and "says `asked: none` AND names ASK-3" in out[0], out

    _write_ledger(tmp_path, BOTH + "\nasked: none, ASK-3")
    assert _run(handoff_lint.check_session_receipt) == []
