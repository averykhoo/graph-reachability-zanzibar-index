"""`handoff_lint.py::check_warn_budget` (`TK86`, hardened 2026-10-13): the trap-badge
budget in `HANDOFF.md` counts BOTH spellings of the badge and exempts only code.

THE DEFECT. Until 2026-10-13 the count was `sum(ln.count(WARN))` -- the U+26A0 glyph only.
`task.py board` folds that glyph to `(!)` (`task.py::ASCII_FOLD`), so the two spellings
are one badge at the read surface, yet a trap typed `(!)` cost nothing (observed
2026-09-19d: the same banner line was RED at 11 with the glyph and green with `(!)`). And
the counter had no escape, so NAMING the badge in backticks spent budget, which pushed
authors to the ASCII spelling. Nothing tested the check at all.

DECISION (2026-10-13, recorded on the TK86 row): HARDEN rather than retire. The budget
still bounds something the byte/line caps do not -- the SHARE of the note that shouts --
and on the live note (re-measured 2026-10-13: 0 glyphs, 0 `(!)`) widening the count reds
nothing, so the row's worry that widening would turn the banner red is stale. The escape
is code only (backtick spans + fences, mirroring `check_restated_counts`); double quotes
are not an escape.

SABOTAGE RECORD, 2026-10-13, both directions plus the boundary, each a one-line patch of
`scripts/handoff_lint.py` run against this module and restored (literal pytest lines):

  * W1 -- count only the glyph (`WARN_SPELLINGS = (WARN,)`), the pre-TK86 behaviour::

        FAILED tests/test_handoff_lint_warn_budget.py::test_the_badge_spellings_match_what_board_folds_it_to
        FAILED tests/test_handoff_lint_warn_budget.py::test_ascii_spelled_overflow_is_red
        FAILED tests/test_handoff_lint_warn_budget.py::test_mixed_spellings_add_up - ...

  * W2 -- no code-span escape (`bare = ln`)::

        FAILED tests/test_handoff_lint_warn_budget.py::test_a_badge_quoted_in_backticks_is_free

  * W3 -- no fence escape (the `in_fence` skip removed)::

        FAILED tests/test_handoff_lint_warn_budget.py::test_a_fenced_badge_is_free - ...

  * W4 -- off by one (`n >= WARN_BUDGET`)::

        FAILED tests/test_handoff_lint_warn_budget.py::test_exactly_the_budget_is_green
        FAILED tests/test_handoff_lint_warn_budget.py::test_a_badge_quoted_in_backticks_is_free
        FAILED tests/test_handoff_lint_warn_budget.py::test_a_fenced_badge_is_free - ...

Run on a temp-dir COPY after a clean baseline; anchors asserted to occur exactly once.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from scripts import handoff_lint  # noqa: E402

GLYPH = "⚠"
B = handoff_lint.WARN_BUDGET


def _red(tmp_path, monkeypatch, body: str) -> list[str]:
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    (tmp_path / "HANDOFF.md").write_text("# HANDOFF\n\n" + body + "\n", encoding="utf-8")
    out: list[str] = []
    handoff_lint.check_warn_budget(out.append)
    return out


def _traps(n: int, badge: str) -> str:
    return "\n".join("- %s **trap %d** do not do X." % (badge, i) for i in range(n))


def test_the_badge_spellings_match_what_board_folds_it_to():
    """The second spelling is not a guess: it is what `task.py board` prints."""
    spec = importlib.util.spec_from_file_location(
        "tk86_task", str(REPO_ROOT / "scripts" / "task.py"))
    task = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(task)
    assert task.ASCII_FOLD[GLYPH] in handoff_lint.WARN_SPELLINGS
    assert GLYPH in handoff_lint.WARN_SPELLINGS


def test_exactly_the_budget_is_green(tmp_path, monkeypatch):
    assert _red(tmp_path, monkeypatch, _traps(B, GLYPH)) == []
    assert _red(tmp_path, monkeypatch, _traps(B, "(!)")) == []


def test_glyph_overflow_is_red(tmp_path, monkeypatch):
    out = _red(tmp_path, monkeypatch, _traps(B + 1, GLYPH))
    assert len(out) == 1 and "%d trap badges" % (B + 1) in out[0], out


def test_ascii_spelled_overflow_is_red(tmp_path, monkeypatch):
    """The evasion the row is about.

    Observed 2026-10-13::

        HANDOFF.md: 11 trap badges (U+26A0 or `(!)`, outside code), budget 10. Overflow is
        a DEFINED move, ...
    """
    out = _red(tmp_path, monkeypatch, _traps(B + 1, "(!)"))
    assert len(out) == 1 and "%d trap badges" % (B + 1) in out[0], out


def test_mixed_spellings_add_up(tmp_path, monkeypatch):
    body = _traps(B // 2 + 1, GLYPH) + "\n" + _traps(B - B // 2, "(!)")
    out = _red(tmp_path, monkeypatch, body)
    assert len(out) == 1 and "%d trap badges" % (B + 1) in out[0], out


def test_a_badge_quoted_in_backticks_is_free(tmp_path, monkeypatch):
    """The control direction: at budget, a line that merely NAMES the badge in a code
    span -- the 2026-09-19d pointer that went RED -- stays green, in either spelling."""
    body = _traps(B, GLYPH) + "\nThe trap badge is `%s` (folded to `(!)` by board)." % GLYPH
    assert _red(tmp_path, monkeypatch, body) == []


def test_a_fenced_badge_is_free(tmp_path, monkeypatch):
    body = _traps(B, GLYPH) + "\n\n```\n%s an example trap line\n(!) another\n```\n" % GLYPH
    assert _red(tmp_path, monkeypatch, body) == []


def test_double_quotes_are_not_an_escape(tmp_path, monkeypatch):
    """Unlike `check_restated_counts`, a double-quoted badge still reads as a badge."""
    body = _traps(B, GLYPH) + '\n- "%s" **trap** quoted.' % GLYPH
    assert len(_red(tmp_path, monkeypatch, body)) == 1
