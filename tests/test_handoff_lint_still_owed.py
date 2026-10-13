"""`handoff_lint.py::check_still_owed_fresh` (`TK97`, 2026-10-13): a `## Still owed` bullet
is a baton for the NEXT session, not backlog.

The rule: every bullet carries a session key, and its OLDEST key is no older than the
previous root-ledger entry (`STILL_OWED_SESSIONS` = the current entry and the one before).
Re-stamping does not reset age. A missing section is red; a bare `- Nothing` is allowed.
Decision and reasoning: the check's docstring and the TK97 row.

Every red asserted below was watched go red before it was believed. SABOTAGE RECORD,
2026-10-13, each a one-line patch of `scripts/handoff_lint.py`, run against this module,
then restored (literal pytest lines):

  * S1 -- no-key bullets skipped (`if not stamps: continue` before the fail)::

        FAILED tests/test_handoff_lint_still_owed.py::test_a_bullet_with_no_key_is_red
        FAILED tests/test_handoff_lint_still_owed.py::test_prose_and_fences_in_the_section_are_not_bullets

  * S2 -- age read from the NEWEST key (`oldest = max(stamps)`), i.e. re-stamping resets::

        FAILED tests/test_handoff_lint_still_owed.py::test_restamping_does_not_reset_age
        FAILED tests/test_handoff_lint_still_owed.py::test_a_wrapped_bullet_is_read_whole

  * S3 -- the bound widened by one session (`keys[:STILL_OWED_SESSIONS + 1]`)::

        FAILED tests/test_handoff_lint_still_owed.py::test_a_bullet_two_entries_old_is_red

  * S4 -- missing section treated as clean (`return` instead of `fail` + `return`)::

        FAILED tests/test_handoff_lint_still_owed.py::test_a_missing_section_is_red

  * S5 -- continuation lines dropped (the `elif cur is not None ...` arm removed): the key
    on the second line of a wrapped bullet is lost, so a fresh bullet reads as keyless::

        FAILED tests/test_handoff_lint_still_owed.py::test_a_wrapped_bullet_is_read_whole

  * S6 -- check removed from `CHECKS`::

        FAILED tests/test_handoff_lint_still_owed.py::test_the_check_is_appended - In...
        FAILED tests/test_handoff_lint_b_prime.py::test_the_two_checks_are_in_the_list_and_nothing_was_inserted

The sweep ran on a COPY in a temp dir (other sessions share this tree), with a clean
baseline first (`96 passed` across this module, test_handoff_lint_warn_budget.py and
test_handoff_lint_b_prime.py); every anchor was asserted to occur exactly once.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from scripts import handoff_lint  # noqa: E402

LEDGER_KEYS = ("2026-10-13", "2026-10-12c", "2026-10-12b", "2026-10-12")

NOTE = """# HANDOFF

## Banner

> 2026-10-13 -- head.

## Still owed

{body}

A session that runs short lists its skipped Rhythm steps here.

## Next session

- `python scripts/task.py board`.
"""


def _run(check) -> list[str]:
    out: list[str] = []
    check(out.append)
    return out


def _write(root: Path, body: str | None, keys=LEDGER_KEYS) -> None:
    if body is None:
        text = "# HANDOFF\n\n## Banner\n\n> 2026-10-13 -- head.\n\n## Next session\n\n- x\n"
    else:
        text = NOTE.format(body=body)
    (root / "HANDOFF.md").write_text(text, encoding="utf-8")
    ledger = root / "docs" / "history"
    ledger.mkdir(parents=True, exist_ok=True)
    entries = "".join("## %s -- entry\n\nbody\n\n" % k for k in keys)
    (ledger / "session-log.md").write_text("# session log\n\n" + entries, encoding="utf-8")


def _check(tmp_path, monkeypatch, body, keys=LEDGER_KEYS) -> list[str]:
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    _write(tmp_path, body, keys)
    return _run(handoff_lint.check_still_owed_fresh)


def test_fresh_bullets_are_green(tmp_path, monkeypatch):
    """Stamped with the current entry, or the one before it: both are batons."""
    body = "- (2026-10-13) run the lean phase.\n- (2026-10-12c) close TK1."
    assert _check(tmp_path, monkeypatch, body) == []


def test_empty_and_nothing_sections_are_green(tmp_path, monkeypatch):
    assert _check(tmp_path, monkeypatch, "Nothing.") == []
    assert _check(tmp_path, monkeypatch, "- Nothing") == []
    assert _check(tmp_path, monkeypatch, "") == []


def test_a_bullet_with_no_key_is_red(tmp_path, monkeypatch):
    """The no-key case is the one 3 of the 5 bullets censused on 2026-09-22 were in.

    Observed 2026-10-13::

        HANDOFF.md:9: a `## Still owed` bullet carries no session key ('the docs still
        name deleted symbols.'). Stamp it with the key of the session that wrote it ...
    """
    out = _check(tmp_path, monkeypatch, "- the docs still name deleted symbols.")
    assert len(out) == 1 and "carries no session key" in out[0], out
    assert out[0].startswith("HANDOFF.md:9:"), out


def test_a_bullet_two_entries_old_is_red(tmp_path, monkeypatch):
    """Stamped with the entry BEFORE the previous one: it survived a handoff.

    Observed 2026-10-13::

        HANDOFF.md:9: a `## Still owed` bullet is stamped 2026-10-12b, older than
        2026-10-12c (the previous ledger entry): it has survived a handoff, ...
    """
    out = _check(tmp_path, monkeypatch, "- (2026-10-12b) close TK1.")
    assert len(out) == 1 and "stamped 2026-10-12b, older than 2026-10-12c" in out[0], out
    # The boundary: one entry newer is green (controls an off-by-one in either direction).
    assert _check(tmp_path, monkeypatch, "- (2026-10-12c) close TK1.") == []


def test_restamping_does_not_reset_age(tmp_path, monkeypatch):
    """The live 2026-10-13 shape: an old stamp plus a fresh re-stamp is still old."""
    body = "- (2026-10-05, re-stamped 2026-10-13: now actionable) fix the docs."
    out = _check(tmp_path, monkeypatch, body)
    assert len(out) == 1 and "stamped 2026-10-05" in out[0], out


def test_a_wrapped_bullet_is_read_whole(tmp_path, monkeypatch):
    """A key on the bullet's continuation line counts (and so does an old one there)."""
    assert _check(tmp_path, monkeypatch, "- fix the docs, written by\n  2026-10-13.") == []
    out = _check(tmp_path, monkeypatch, "- (2026-10-13) fix the docs\n  from 2026-09-07b.")
    assert len(out) == 1 and "stamped 2026-09-07b" in out[0], out


def test_prose_and_fences_in_the_section_are_not_bullets(tmp_path, monkeypatch):
    """The footer paragraph is not a bullet; a fenced example is not a bullet and its
    `## ` line does not end the section early (a bullet AFTER it is still checked)."""
    body = "```\n- an example bullet\n## not a heading\n```\n\n- no key here"
    out = _check(tmp_path, monkeypatch, body)
    assert len(out) == 1 and "'no key here'" in out[0], out


def test_a_missing_section_is_red(tmp_path, monkeypatch):
    """Deleting the section must not be the way to pass."""
    out = _check(tmp_path, monkeypatch, None)
    assert len(out) == 1 and "no `## Still owed` section" in out[0], out


def test_a_single_entry_ledger_ages_against_that_entry(tmp_path, monkeypatch):
    assert _check(tmp_path, monkeypatch, "- (2026-10-13) x", keys=("2026-10-13",)) == []
    out = _check(tmp_path, monkeypatch, "- (2026-10-12) x", keys=("2026-10-13",))
    assert len(out) == 1 and "older than 2026-10-13" in out[0], out


def test_bullets_with_no_ledger_to_age_against_are_red(tmp_path, monkeypatch):
    out = _check(tmp_path, monkeypatch, "- (2026-10-13) x", keys=())
    assert len(out) == 1 and "no `## <session-key> ` entry to age them" in out[0], out


def test_the_check_is_appended(tmp_path, monkeypatch):
    """Appended, never inserted (see test_handoff_lint_b_prime's positional pin)."""
    names = [c.__name__ for c in handoff_lint.CHECKS]
    assert names[12] == "check_still_owed_fresh", names
