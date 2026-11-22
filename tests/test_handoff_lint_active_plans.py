"""`handoff_lint.py::check_active_plans_closed_rows` (`TK-275`, 2026-11-22): an ACTIVE-PLAN doc
whose file name names task rows that are ALL closed is red, so "freeze at landing"
(docs/README.md sec 2) stops being held by hand.

Rule, scope and the design calls (file-name key, aliases resolved, the engine's reading of a
declaration, why not the engine's own G-D4): the comment above `handoff_lint.PLAN_DOC_DIRS`
and docs/tk275-plan-freeze-check-2026-11-22.md.

Every red asserted below was watched go red before it was believed. SABOTAGE RECORD,
2026-11-23, each a one-line patch of a COPY of scripts/handoff_lint.py in a temp dir (other
sessions share this tree), run against this module, then discarded; every anchor asserted to
occur exactly once; clean baseline first (``33 passed``). S11-S17 were added after review
found those reader branches unpinned. Literal pytest lines:

  * S1 -- red when ANY named row is closed (all -> any)::

        FAILED tests/test_handoff_lint_active_plans.py::test_a_two_row_plan_stays_open_while_either_row_is_open

  * S2 -- the task.py alias form dropped (only TK-91 tried, never TK91)::

        FAILED tests/test_handoff_lint_active_plans.py::test_a_plan_whose_row_is_closed_is_red
        FAILED tests/test_handoff_lint_active_plans.py::test_the_alias_resolves - Ass...
        FAILED tests/test_handoff_lint_active_plans.py::test_a_two_row_plan_is_red_once_both_rows_close
        FAILED tests/test_handoff_lint_active_plans.py::test_a_token_that_names_no_row_is_ignored

  * S3 -- the soft-line-break guard dropped (if not opens -> if False)::

        FAILED tests/test_handoff_lint_active_plans.py::test_frozen_at_a_soft_line_break_does_not_freeze_it

  * S4 -- the bold-only reader (_DECLARATION over the window) instead of the engine's::

        FAILED tests/test_handoff_lint_active_plans.py::test_the_engines_unbolded_frozen_line_freezes_it
        FAILED tests/test_handoff_lint_active_plans.py::test_a_blockquoted_unbolded_active_plan_counts
        FAILED tests/test_handoff_lint_active_plans.py::test_an_archived_line_freezes_it
        FAILED tests/test_handoff_lint_active_plans.py::test_frontmatter_is_skipped_and_its_next_line_opens_a_block
        FAILED tests/test_handoff_lint_active_plans.py::test_every_emphasis_form_is_read[*]
        FAILED tests/test_handoff_lint_active_plans.py::test_every_emphasis_form_is_read[_]
        FAILED tests/test_handoff_lint_active_plans.py::test_every_emphasis_form_is_read[__]

  * S5 -- fenced code read as prose (if fence: continue -> if False)::

        FAILED tests/test_handoff_lint_active_plans.py::test_a_declaration_in_fenced_code_declares_nothing

  * S6 -- the floor removed::

        FAILED tests/test_handoff_lint_active_plans.py::test_the_floor_catches_a_blind_parser

  * S7 -- tasks/closed/ read by frontmatter state only::

        FAILED tests/test_handoff_lint_active_plans.py::test_a_pre_engine_closed_dir_counts_as_closed

  * S8 -- the check removed from CHECKS::

        FAILED tests/test_handoff_lint_active_plans.py::test_the_check_is_appended - ...

  * S9 -- the window ignored (enumerate(lines[:window]) -> enumerate(lines))::

        FAILED tests/test_handoff_lint_active_plans.py::test_a_declaration_past_the_window_declares_nothing

  * S11 -- the ARCHIVED branch dropped::

        FAILED tests/test_handoff_lint_active_plans.py::test_an_archived_line_freezes_it

  * S12 -- the line after a heading no longer opens a block::

        FAILED tests/test_handoff_lint_active_plans.py::test_the_line_after_a_heading_opens_a_block

  * S13 -- the frontmatter skip dropped::

        FAILED tests/test_handoff_lint_active_plans.py::test_frontmatter_is_skipped_and_its_next_line_opens_a_block

  * S14 -- the line after the frontmatter no longer opens a block::

        FAILED tests/test_handoff_lint_active_plans.py::test_frontmatter_is_skipped_and_its_next_line_opens_a_block

  * S15 -- the (?![A-Za-z0-9-]) lookahead dropped::

        FAILED tests/test_handoff_lint_active_plans.py::test_a_longer_word_is_not_the_declaration

  * S16 -- the emphasis forms cut to bold only::

        FAILED tests/test_handoff_lint_active_plans.py::test_frontmatter_is_skipped_and_its_next_line_opens_a_block
        FAILED tests/test_handoff_lint_active_plans.py::test_every_emphasis_form_is_read[*]
        FAILED tests/test_handoff_lint_active_plans.py::test_every_emphasis_form_is_read[_]
        FAILED tests/test_handoff_lint_active_plans.py::test_every_emphasis_form_is_read[__]

  * S17 -- formal dropped from PLAN_DOC_DIRS::

        FAILED tests/test_handoff_lint_active_plans.py::test_the_plan_dirs_are_the_reviewed_set

  * S10 -- PLAN_DOC_DIRS cut to docs/ only::

        FAILED tests/test_handoff_lint_active_plans.py::test_the_plan_dirs_are_the_reviewed_set
        FAILED tests/test_handoff_lint_active_plans.py::test_history_and_formal_dirs_are_scanned

The SUBJECT was sabotaged too: ``docs/tk70-detonation-2026-09-17.md`` read as it was before its
freeze (``_read`` patched to the pre-freeze bytes) gives exactly one failure, ``docs/tk70-
detonation-2026-09-17.md: declares ACTIVE-PLAN, but every row its file name names (TK70) is
closed, ...``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from scripts import handoff_lint  # noqa: E402

PLAN = """# `{title}` -- a plan

**ACTIVE-PLAN, opened 2026-01-01.** Corrections append dated at the top. Freeze it
when the row closes.

Body.
"""


def _task(root: Path, tid: str, closed: bool, aliases=(), sub: str = "") -> None:
    d = root / "tasks" / sub if sub else root / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    al = "[%s]" % ", ".join(aliases)
    state = "closed" if closed else "open"
    (d / ("%s-x.md" % tid)).write_text(
        "---\ntype: Task\nid: %s\naliases: %s\nstate: %s\n---\n\nbody\n" % (tid, al, state),
        encoding="utf-8")


def _doc(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.setattr(handoff_lint, "REPO", str(tmp_path))
    monkeypatch.setattr(handoff_lint, "MIN_PLAN_DOCS_KEYED", 1)
    return tmp_path


def _run() -> list[str]:
    out: list[str] = []
    handoff_lint.check_active_plans_closed_rows(out.append)
    return out


# NO TEST HERE READS THE LIVE docs/ TREE, on purpose. scripts/gate_status.py::_in_scope leaves
# docs/*.md out of the code scope the pytest tiles are keyed on (only CODE_SCOPE_MD_KEEP stays
# in), so a live-tree test here would stay cached green after a doc edit turned it red: a
# fail-open. The live property is held where markdown IS in scope: verify.sh's lean phase runs
# scripts/handoff_lint.py, whose CHECKS include this check (pinned by test_the_check_is_appended)
# and whose MIN_PLAN_DOCS_KEYED floor fails it if the parser goes blind on the real tree.


def test_a_plan_whose_row_is_closed_is_red(tree):
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    _doc(tree, "docs/tk1-plan-2026-01-01.md", PLAN.format(title="TK1"))
    out = _run()
    assert len(out) == 1 and "docs/tk1-plan-2026-01-01.md" in out[0] and "TK1" in out[0], out
    assert "context-engine doc freeze docs/tk1-plan-2026-01-01.md" in out[0], out


def test_a_plan_whose_row_is_open_is_green(tree):
    _task(tree, "TK-1", closed=False, aliases=["TK1"])
    _doc(tree, "docs/tk1-plan-2026-01-01.md", PLAN.format(title="TK1"))
    assert _run() == []


def test_the_engine_id_form_resolves_without_an_alias(tree):
    _task(tree, "TK-8", closed=True)
    _doc(tree, "docs/tk-8-plan-2026-01-01.md", PLAN.format(title="TK-8"))
    _doc(tree, "docs/tk8-plan-2026-01-01.md", PLAN.format(title="TK-8"))
    out = _run()
    assert len(out) == 2, out


def test_the_alias_resolves(tree):
    """The pre-engine docs name the task.py id (`TK106`), which is only an alias now."""
    _task(tree, "TK-501", closed=True, aliases=["TK106"])
    _doc(tree, "docs/tk106-plan-2026-01-01.md", PLAN.format(title="TK106"))
    out = _run()
    assert len(out) == 1 and "(TK106)" in out[0], out


def test_a_two_row_plan_stays_open_while_either_row_is_open(tree):
    _task(tree, "TK-91", closed=True, aliases=["TK91"])
    _task(tree, "TK-80", closed=False, aliases=["TK80"])
    _doc(tree, "docs/tk91-tk80-plan-2026-01-01.md", PLAN.format(title="TK91 + TK80"))
    assert _run() == []


def test_a_two_row_plan_is_red_once_both_rows_close(tree):
    _task(tree, "TK-91", closed=True, aliases=["TK91"])
    _task(tree, "TK-80", closed=True, aliases=["TK80"])
    _doc(tree, "docs/tk91-tk80-plan-2026-01-01.md", PLAN.format(title="TK91 + TK80"))
    out = _run()
    assert len(out) == 1 and "(TK91, TK80)" in out[0], out


def test_a_token_that_names_no_row_is_ignored(tree):
    """`p22-i14-...`: I14 is an invariant, not a row; P22 alone decides."""
    _task(tree, "TK-22", closed=True, aliases=["P22"])
    _doc(tree, "docs/p22-i14-plan-2026-01-01.md", PLAN.format(title="P22"))
    out = _run()
    assert len(out) == 1 and "(P22)" in out[0], out


def test_a_name_that_resolves_to_no_row_is_out_of_scope(tree):
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    _doc(tree, "docs/tk1-plan-2026-01-01.md", "# t\n\n**FROZEN 2026-01-02.** x\n")
    _doc(tree, "docs/goal-census-2026-01-01.md", PLAN.format(title="no id"))
    _doc(tree, "docs/tk9-plan-2026-01-01.md", PLAN.format(title="no such row"))
    assert _run() == []


def test_the_engines_unbolded_frozen_line_freezes_it(tree):
    """`context-engine doc freeze` writes an UNBOLDED FROZEN line above the old one."""
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    text = PLAN.format(title="TK1").replace(
        "**ACTIVE-PLAN", "FROZEN 2026-11-22 (session 2026-11-22a): TK1 closed; below, the plan\n"
        "as it stood\n\n**ACTIVE-PLAN")
    _doc(tree, "docs/tk1-plan-2026-01-01.md", text)
    assert _run() == []


def test_a_blockquoted_unbolded_active_plan_counts(tree):
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    _doc(tree, "docs/tk1-plan-2026-01-01.md", "# t\n\n> ACTIVE-PLAN (sec 3): the record.\n")
    assert len(_run()) == 1


def test_frozen_at_a_soft_line_break_does_not_freeze_it(tree):
    """A paragraph ABOVE the declaration that wraps "FROZEN" onto the start of a line is the
    word in passing (the engine's reading): the plan is still ACTIVE-PLAN. It must sit above
    the declaration, since the topmost one wins and a wrap below it could never matter."""
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    _doc(tree, "docs/tk1-plan-2026-01-01.md",
         "# t\n\nScout for `TK1`, whose earlier plan was\nFROZEN by mistake; see below.\n\n"
         "**ACTIVE-PLAN, opened 2026-01-01.** x\n")
    assert len(_run()) == 1


def test_a_declaration_in_fenced_code_declares_nothing(tree):
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    # The blank line inside the fence matters: without it the FROZEN line would be skipped as
    # a soft line break, and this test would pass with the fence handling deleted.
    _doc(tree, "docs/tk1-plan-2026-01-01.md", "# t\n\n```\n\nFROZEN 2026-01-02\n```\n\n"
         "**ACTIVE-PLAN.** x\n")
    assert len(_run()) == 1


def test_a_declaration_past_the_window_declares_nothing(tree):
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    pad = "".join("line %d\n\n" % i for i in range(handoff_lint.LIVENESS_WINDOW))
    _doc(tree, "docs/tk1-plan-2026-01-01.md", "# t\n\n" + pad + "**ACTIVE-PLAN.** x\n")
    assert _run() == []


def test_an_archived_line_freezes_it(tree):
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    _doc(tree, "docs/tk1-plan-2026-01-01.md", "ARCHIVED 2026-02-02 from docs/\n\n**ACTIVE-PLAN.** x\n")
    assert _run() == []


def test_the_line_after_a_heading_opens_a_block(tree):
    """No blank line between the title and the declaration: still a declaration."""
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    _doc(tree, "docs/tk1-plan-2026-01-01.md", "# t\n**ACTIVE-PLAN.** x\n")
    assert len(_run()) == 1


def test_frontmatter_is_skipped_and_its_next_line_opens_a_block(tree):
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    _doc(tree, "docs/tk1-plan-2026-01-01.md", "---\nnote: FROZEN\n---\n**ACTIVE-PLAN.** x\n")
    _doc(tree, "docs/tk1-other-2026-01-01.md", "---\nkey: a\n\nFROZEN: x\n---\n\n_ACTIVE-PLAN_ x\n")
    assert len(_run()) == 2


def test_a_longer_word_is_not_the_declaration(tree):
    """`FROZEN-ISH` is not `FROZEN` (the engine's `(?![A-Za-z0-9-])`)."""
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    _doc(tree, "docs/tk1-plan-2026-01-01.md", "# t\n\nFROZEN-ISH notes\n\n**ACTIVE-PLAN.** x\n")
    assert len(_run()) == 1


@pytest.mark.parametrize("lead", ["*", "_", "__"])
def test_every_emphasis_form_is_read(tree, lead):
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    _doc(tree, "docs/tk1-plan-2026-01-01.md", "# t\n\n%sACTIVE-PLAN%s x\n" % (lead, lead))
    assert len(_run()) == 1


@pytest.mark.parametrize("d", handoff_lint.PLAN_DOC_DIRS)
def test_every_plan_dir_is_scanned(tree, d):
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    _doc(tree, "%s/tk1-plan-2026-01-01.md" % d, PLAN.format(title="TK1"))
    assert len(_run()) == 1


def test_the_plan_dirs_are_the_reviewed_set():
    """Pins the tuple itself: the parametrized test above would shrink with it."""
    assert handoff_lint.PLAN_DOC_DIRS == (
        'docs', 'docs/architecture', 'docs/specs', 'docs/evidence', 'docs/history',
        'formal', 'formal/history')


def test_history_and_formal_dirs_are_scanned(tree):
    _task(tree, "TK-1", closed=True, aliases=["TK1"])
    _doc(tree, "formal/history/tk1-plan-2026-01-01.md", PLAN.format(title="TK1"))
    _doc(tree, "docs/architecture/tk1-design.md", PLAN.format(title="TK1"))
    assert len(_run()) == 2


def test_a_pre_engine_closed_dir_counts_as_closed(tree):
    _task(tree, "TK-1", closed=False, aliases=["TK1"], sub="closed")
    _doc(tree, "docs/tk1-plan-2026-01-01.md", PLAN.format(title="TK1"))
    assert len(_run()) == 1


def test_the_floor_catches_a_blind_parser(tree, monkeypatch):
    monkeypatch.setattr(handoff_lint, "MIN_PLAN_DOCS_KEYED", 2)
    _task(tree, "TK-1", closed=False, aliases=["TK1"])
    _doc(tree, "docs/tk1-plan-2026-01-01.md", PLAN.format(title="TK1"))
    out = _run()
    assert len(out) == 1 and "MIN_PLAN_DOCS_KEYED" in out[0], out


def test_no_task_tree_is_a_no_op(tree):
    _doc(tree, "docs/tk1-plan-2026-01-01.md", PLAN.format(title="TK1"))
    assert _run() == []


def test_the_check_is_appended():
    """Appended, never inserted (see test_handoff_lint_b_prime's positional pin)."""
    names = [c.__name__ for c in handoff_lint.CHECKS]
    assert names[-1] == "check_active_plans_closed_rows", names
