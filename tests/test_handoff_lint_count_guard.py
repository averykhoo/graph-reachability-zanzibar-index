"""`check_restated_counts` -- the extractor, the five escapes, and the walk floor.

`scripts/handoff_lint.py::check_restated_counts` refuses a restated corpus count in a
live doc's prose: `N checks`, `N open tasks`, `N tests`. It is the graduated form of the
`count_guard.py` that was designed for the gitignored `.scratch/tasktool/` corpus, never
shipped, and deleted with that directory on 2026-09-07 (task `TK58`, batch 4 of the nine
findings the archive carried).

WHY THIS MODULE PINS THE MECHANISM AND NOT THE CORPUS. There is deliberately no test here
that runs the check against the real tree and asserts it is clean, and the reason is a
gate hole rather than taste: the pytest tiles key off the `t2c` tree id, which EXCLUDES
`*.md` outside `tasks/`. A live-corpus assertion would go green on one tree, stay
"green on this tree" after someone edited `docs/gate-runbook.md`, and quietly stop being
true. Corpus coverage belongs to `verify.sh` step 4f (`lean`), which keys off `t2a` and
therefore re-runs on any `*.md` edit. This module owns the parts that a synthetic corpus
can settle for good.

EVERY ESCAPE HERE EARNED ITS PLACE BY MEASUREMENT, not by argument. Each was disabled in
turn against the live corpus (2026-09-08), counting the violations it was suppressing::

    baseline                 75 file(s) scanned, 0 violation(s)
    banner exemption OFF     79 file(s) scanned, 8 violation(s)   (+8)
    task `## Log` OFF        75 file(s) scanned, 1 violation(s)   (+1)
    dated-line OFF           75 file(s) scanned, 4 violation(s)   (+4)
    quoted-span OFF          75 file(s) scanned, 0 violation(s)   (+0)
    fence OFF                75 file(s) scanned, 0 violation(s)   (+0)

⚠ **The last two suppress nothing in today's corpus**, which is precisely the state the
archived design was caught in (its FROZEN exemption once matched *nothing at all* because
it tested for a literal substring no real banner used). They are kept because both are
one paste away from mattering -- a fenced `handoff_lint: clean (12 checks)` transcript, a
correction quoting the figure it repeals -- and the way to keep an unexercised exemption
honest is to make it a test rather than a belief. That is what
`test_a_fenced_transcript_is_evidence_not_a_claim` and
`test_a_quoted_figure_is_a_citation_not_a_claim` are for. Re-run the measurement above if
you touch them; an escape that suppresses nothing AND has no test is decoration.

SABOTAGE RECORD (docs/sabotage-procedure.md), 2026-09-08. The narrowest PLAUSIBLE
weakening, not a catastrophe: one true-today sentence appended to `HANDOFF.md`'s banner,
which is exactly how every figure this check exists for was born. Literal observed
output::

    handoff_lint: 2 violation(s)   [before the corpus sweep: HANDOFF.md + the task file]

      FAIL: HANDOFF.md:30 restates a checks count in prose ('12 checks'). A quoted count
      is not merely stale, it is UNENFORCED -- docs/README.md section 1, and ZT-P3-5 is
      this repo's most-recurring doc defect. DELETE the number and point at its home ...

      FAIL: tasks/TK58-...md:54 restates a open tasks/rows count in prose ('65 open
      tasks'). ...

Both restored, and the clean tree reports `handoff_lint: clean (12 checks)` in the same
session. Control on the SAME sabotage line: re-prefixed with `Measured 2026-09-08:` the
check goes silent again, so it is judging the escape and not the line's shape.

THE RETROSPECTIVE CONTROL is stronger than either, and it is why this check was believed
before any test existed. Two figures in `docs/gate-runbook.md` were found wrong BY HAND on
2026-09-08 -- a "Three checks now run inside the `lean` phase" that seven do, and a
`handoff_lint.py` check count stale since the eleventh check landed. Run against the
parent commit `966f6aa`, these patterns report both, plus four the same reader walked
past::

     81 tests   Three tests    | ... Three tests in the shared HA
    197 tests   6 tests        | ... `test_conformance_enum.py` - 6 tests,
    201 tests   6 tests        | ... interleaves those 6 tests across the **five** tiles
    285 checks  Three checks   | Three checks now run inside the `lean` phase ...
    365 checks  Ten checks     | ... `handoff_lint.py`. Ten checks over the two board files
    566 tests   eight        t | ... Pinned by the eight `GS-2` tests in

Real, independently-confirmed rot from before the check was written. The six live claims
the 2026-09-08 census left after the escapes were all fixed in the landing commit, so the
check arrives green rather than red -- red on arrival is how a check gets deleted.

THE INSTRUMENT WAS SWEPT TOO, and it had a hole. Ten one-line weakenings of
`check_restated_counts` were applied in turn, each the plausible edit rather than a
catastrophe, and this module was run against every one (2026-09-08, restoring the file
from memory in a `finally`). Nine were caught by exactly the test that claims to guard
them::

    fence off                  1 failed  test_a_fenced_transcript_is_evidence_not_a_claim
    quoted-span off            1 failed  test_a_quoted_figure_is_a_citation_not_a_claim
    dated-line off             1 failed  test_a_dated_line_is_a_stamped_observation
    banner exemption off       1 failed  test_a_provenance_banner_exempts_the_whole_file
    task `## Log` off          1 failed  test_a_task_files_log_is_append_only_...
    scope: tasks/README.md in  1 failed  test_tasks_non_task_md_is_out_of_scope
    floor removed              1 failed  test_the_floor_fires_when_the_walk_goes_blind
    lookbehind removed         1 failed  test_a_number_that_starts_mid_token_is_not_a_count
    one/two admitted           1 failed  test_one_and_two_are_deliberately_below_the_floor
    intervening word admitted  17 passed  -- NOTHING CAUGHT IT

⚠ The tenth is the finding. Widening the `checks` pattern to `(?:\\w+\\s+)?checks?` -- the
single most likely "improvement" anyone would make -- broke the check and every test here
still passed, because `test_an_intervening_prose_word_makes_it_a_subset_not_a_census`
exercised `TESTS_PAT` only. The hole was in the INSTRUMENT, not in the subject, and no
amount of staring at the check would have shown it. That test now asserts on all three
patterns and the sweep is 10/10. **A test module that guards N patterns must assert on
all N**; run the sweep, do not reason about it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# `scripts/` has no __init__.py and pytest.ini sets no pythonpath -- same explicit
# insert, and same reason, as tests/test_handoff_lint_row_ids.py.
sys.path.insert(0, str(REPO_ROOT))
from scripts import handoff_lint  # noqa: E402

CHECKS_PAT = handoff_lint._COUNT_PATTERNS[0][1]
CORPUS_PAT = handoff_lint._COUNT_PATTERNS[1][1]
TESTS_PAT = handoff_lint._COUNT_PATTERNS[2][1]

FROZEN_BANNER = (
    "# An archived record\n\n"
    "**FROZEN 2026-09-01 -- provenance, not a living document.** Status lines below\n"
    "are as-of-then.\n"
)
APPEND_ONLY_BANNER = (
    "# Spec deviations log\n\n"
    "**LIVING -- append-only.** Every entry is true *as of its date key* and is never\n"
    "rewritten.\n"
)
ACTIVE_PLAN_BANNER = (
    "# A scope doc\n\n"
    "**ACTIVE-PLAN 2026-09-08.** Body is provenance; corrections appended dated.\n"
)

# A task file as `scripts/task.py` writes one: frontmatter, summary, Traps, Read first,
# then the append-only `## Log` last. The section ORDER is the thing under test -- the
# check reads until `## Log` and stops, so a fixture that put the Log first would pass
# for the wrong reason.
TASK_FILE = (
    "---\nid: %(id)s\ntitle: %(id)s\npri: LATER\nsize: S\ndeps: []\n---\n"
    "\n%(body)s\n"
    "\n## Traps\n\n- %(traps)s\n"
    "\n## Log\n\n### 2026-09-08\n\n%(log)s\n"
)


@pytest.fixture()
def run_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run `check_restated_counts` over a synthetic root; return its failures.

    `files` maps a repo-relative path to its full text. `HANDOFF.md` and `CLAUDE.md` are
    written as empty stubs unless overridden, because they are DECLARED scope and their
    absence is its own (separately tested) failure.

    `MIN_COUNT_SCANNED` is neutralised here and exercised by
    `test_the_floor_fires_when_the_walk_goes_blind` alone: leaving it live would make
    every behavioural test in this module fail for the floor's reason instead of its own,
    which is how a test file stops telling you what broke.
    """

    def _run(files: dict, floor: int = 0) -> list:
        root = tmp_path / "repo"
        root.mkdir(exist_ok=True)
        stubs = {"CLAUDE.md": "# CLAUDE\n", "HANDOFF.md": "# HANDOFF\n"}
        stubs.update(files)
        for rel, text in stubs.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        monkeypatch.setattr(handoff_lint, "REPO", str(root))
        monkeypatch.setattr(handoff_lint, "MIN_COUNT_SCANNED", floor)
        failures: list = []
        handoff_lint.check_restated_counts(failures.append)
        return failures

    return _run


# --------------------------------------------------------------------------- #
# the sabotage, and the three patterns
# --------------------------------------------------------------------------- #
def test_a_restated_check_count_in_the_banner_is_caught(run_check):
    """THE sabotage: one true-today sentence appended to `HANDOFF.md`.

    It is true when written, unenforced forever after, and indistinguishable from the
    lines that actually rotted. The message must NAME the file, the line and the token --
    a verdict without them leaves the reader diffing the corpus.
    """
    failures = run_check({
        "HANDOFF.md": "# HANDOFF\n\nThe lint now runs 12 checks over the two boards.\n",
    })
    assert len(failures) == 1, failures
    assert "HANDOFF.md:3" in failures[0]
    assert "'12 checks'" in failures[0]


def test_each_pattern_extracts_the_expected_token(run_check):
    """Token-level instrument control, one line per pattern.

    A verdict cannot distinguish "the regex read the number and judged it fine" from "the
    regex never saw it" -- the hole that made `check_ledger_row_ids` pass for eight days
    (`TK46`; see tests/test_handoff_lint_row_ids.py). So assert on what was EXTRACTED.
    """
    line = "It runs 12 checks over 65 open tasks, and 879 tests guard them."
    assert CHECKS_PAT.findall(line) == ["12 checks"]
    assert CORPUS_PAT.findall(line) == ["65 open tasks"]
    assert TESTS_PAT.findall(line) == ["879 tests"]
    # ... and all three fire from one line, so a fix cannot silence a sibling.
    failures = run_check({"docs/live.md": "# live\n\n%s\n" % line})
    assert len(failures) == 3, failures


def test_a_number_that_starts_mid_token_is_not_a_count():
    """The lookbehind, which the 2026-09-08 census demanded (AMENDMENT 2).

    Without it `R6-6` yields a "6" and `1.00 row/edge` yields an "00" -- both observed --
    so the check would have opened with false reds on identifiers and on measured rates.
    A check that reddens on correct writing is a check someone deletes.
    """
    assert CHECKS_PAT.findall("R6-6 checks the cascade") == []
    assert CHECKS_PAT.findall("1.00 checks per edge") == []
    assert TESTS_PAT.findall("the 2026-08-17 tests") == []
    # ... and the positive control on the same shapes: a bare number still parses.
    assert CHECKS_PAT.findall("6 checks") == ["6 checks"]


def test_one_and_two_are_deliberately_below_the_floor():
    """`one`/`two` are absent from the word list ON PURPOSE.

    At those magnitudes the prose is a narrative pair ("two checks", "one test") far more
    often than a census, and the census forms this guards are bigger than two. Pinned so
    the omission reads as a decision rather than an oversight -- and so that widening the
    list is a deliberate edit with this test's docstring in front of it.
    """
    assert CHECKS_PAT.findall("the two checks disagree") == []
    assert TESTS_PAT.findall("one test pins it") == []
    assert CHECKS_PAT.findall("three checks now run") == ["three checks"]
    assert TESTS_PAT.findall("Twenty tests cover it") == ["Twenty tests"]


def test_an_intervening_prose_word_makes_it_a_subset_not_a_census():
    """`N <word> tests` describes a SUBSET; `N tests` is the census this refuses.

    ALL THREE patterns are asserted here, and that is not padding. A mutation sweep on
    2026-09-08 widened the `checks` pattern alone to `%s\\s+(?:\\w+\\s+)?checks?` -- the
    single most likely "improvement" anyone would make to it -- and every test in this
    module still passed, because this test only exercised `TESTS_PAT`. Nine of ten
    mutations were caught by the test that claimed to guard them; that one was the hole,
    and it was in the instrument, not the check.

    Both false positives are real: "six isinstance tests" (counting branches in an AST
    walker) and "44 KB `sync` test suite" were the 2026-09-08 census's noise. But a
    QUOTED qualifier must stay transparent, because "the eight `GS-2` tests in
    tests/test_gate_status.py" is a genuine restated count -- and it is, because the
    quote is blanked to spaces before the pattern runs, preserving the `\\s+`.

    THE CORPUS PATTERN'S IMMEDIACY WAS TESTED, not assumed. "the 65 still open tasks" is
    a census the immediate form misses, so the widened variant was run against the live
    corpus: it found ZERO new real claims and exactly one false red -- `docs/tasktool-
    spec.md:420`, "at most three `NEXT` among OPEN tasks", a capacity RULE with a blanked
    code span between the number and the noun. Uniform immediacy is therefore a measured
    trade, not a symmetry argument.
    """
    assert CHECKS_PAT.findall("six isinstance checks per pass") == []
    assert TESTS_PAT.findall("six isinstance tests per check") == []
    assert TESTS_PAT.findall("a 44 KB test suite") == []
    assert CORPUS_PAT.findall("three NEXT among open tasks") == []
    # ... and the bare census form of each still parses, so the rule is immediacy and not
    # a pattern that has quietly stopped matching.
    assert CHECKS_PAT.findall("12 checks") == ["12 checks"]
    assert CORPUS_PAT.findall("65 open tasks") == ["65 open tasks"]
    blanked = handoff_lint._COUNT_QUOTED.sub(
        lambda m: " " * len(m.group(0)), "Pinned by the eight `GS-2` tests in ...")
    assert TESTS_PAT.findall(blanked) == ["eight        tests"]


# --------------------------------------------------------------------------- #
# the five escapes -- each asserted in BOTH directions
# --------------------------------------------------------------------------- #
def test_a_fenced_transcript_is_evidence_not_a_claim(run_check):
    """A fenced block is a run's output, not the document's assertion.

    Suppresses nothing in the 2026-09-08 corpus (see the module docstring), so this test
    IS its justification: the first doc to paste a `clean (12 checks)` transcript would
    otherwise go red for quoting the tool correctly.
    """
    fenced = "# live\n\nOutput::\n\n```\nhandoff_lint: clean (12 checks)\n```\n"
    assert run_check({"docs/live.md": fenced}) == []
    # Same text, fence removed: the pattern is there and the fence is what silenced it.
    assert len(run_check({"docs/live.md": fenced.replace("```\n", "")})) == 1


def test_a_quoted_figure_is_a_citation_not_a_claim(run_check):
    """A backticked or double-quoted number is text being QUOTED, not asserted.

    The shape is a correction repealing a figure -- CLAUDE.md's "★ No figures here"
    bullet quotes the wrong count it retired, and must stay writable. Also suppresses
    nothing today, so this test is the whole of its evidence.
    """
    quoted = '# live\n\nIt used to read "12 checks", which is why the rule exists.\n'
    assert run_check({"docs/live.md": quoted}) == []
    assert run_check({"docs/live.md": "# live\n\nIt used to read `12 checks` here.\n"}) == []
    assert len(run_check({"docs/live.md": "# live\n\nIt used to read 12 checks here.\n"})) == 1


def test_a_dated_line_is_a_stamped_observation(run_check):
    """A `YYYY-MM-DD[letter]` key on the line makes the number as-of-then.

    This is the repo's own convention for a measured figure, and the failure message
    offers it as one of the two remedies. Suppresses four live lines today.
    """
    assert run_check({"docs/live.md": "# live\n\nMeasured 2026-09-08: 12 checks run.\n"}) == []
    assert len(run_check({"docs/live.md": "# live\n\nMeasured today: 12 checks run.\n"})) == 1


def test_a_provenance_banner_exempts_the_whole_file(run_check):
    """FROZEN / ACTIVE-PLAN / LIVING-append-only bodies are provenance by declaration.

    ⚠ AMENDMENT 1 of the census: the OBVIOUS design -- skip any line carrying a date --
    is useless for `docs/spec-deviations.md`, which is 3511 lines of dated entries whose
    date sits on the `## <date>` HEADING and never on the body line. That one file is the
    largest block of legitimate hits in the repo. So the exemption keys on the FILE's
    liveness banner (docs/README.md sections 2-3), which is the machine-readable fact.
    """
    body = "\n\nIt ran 12 checks over 65 open tasks.\n"
    for banner in (FROZEN_BANNER, APPEND_ONLY_BANNER, ACTIVE_PLAN_BANNER):
        assert run_check({"docs/live.md": banner + body}) == [], banner.split("\n")[2]
    # The control: the same body under a LIVING banner with no append-only clause is
    # scanned. Without it this test could be passing because the BODY never matched.
    living = "# A living doc\n\n**LIVING.** Maintained; every statement is true today.\n"
    assert len(run_check({"docs/live.md": living + body})) == 2


def test_a_banner_below_the_window_does_not_exempt(run_check):
    """The banner must be above the fold, like `check_frozen_banners` requires.

    A declaration buried at line 40 warns nobody, and honouring it would let any file
    opt out by mentioning FROZEN somewhere in its body.
    """
    buried = "# doc\n" + ("\nfiller\n" * handoff_lint.LIVENESS_WINDOW) + FROZEN_BANNER
    assert len(run_check({"docs/live.md": buried + "\n12 checks run.\n"})) == 1


def test_a_task_files_log_is_append_only_and_its_body_is_not(run_check):
    """A task `## Log` entry is a dated journal; everything above it is present tense.

    Both halves matter and this is the only test that can tell them apart. Exempting the
    whole file would drop `tasks/` from the scan (70 of 72 open task files had no hit at
    all in the census, so the scan would look fine while covering nothing); exempting
    nothing would fire on every session's own notes and force a date stamp onto every
    line of an append-only journal.
    """
    task = TASK_FILE % {
        "id": "TK99",
        "body": "The tree carries 65 open tasks today.",
        "traps": "It runs 12 checks.",
        "log": "The census found 65 open tasks and 12 checks.",
    }
    failures = run_check({"tasks/TK99-a-task.md": task})
    assert len(failures) == 2, failures
    assert any("65 open tasks" in f for f in failures)
    assert any("12 checks" in f for f in failures)
    # ... and both of the Log's counts are silent, which is the other half.
    assert all(":19" not in f for f in failures)


def test_tasks_non_task_md_is_out_of_scope(run_check):
    """`README.md` and the `BANNER.md` tombstone are not tasks.

    Same skip, and the same duplicated-tuple caveat, as `_tree_ids`: `TASKS_NON_TASK_MD`
    is copied from `scripts/task.py::NON_TASK_MD` rather than imported so one bug cannot
    corrupt both sides.
    """
    prose = "# not a task\n\nIt runs 12 checks.\n"
    assert run_check({"tasks/README.md": prose}) == []
    assert len(run_check({"tasks/NOT-README.md": prose})) == 1


def test_history_and_subdirectories_are_out_of_scope(run_check):
    """`docs/` is TOP LEVEL only, and that is a measured scope, not laziness.

    `docs/history/` is provenance by its path (CLAUDE.md: status lines there are FROZEN
    as-of-then). `docs/specs/` and `docs/architecture/` were never censused, and a scope
    widened without a census arrives red on lines nobody has read -- which is how the
    archived `count_guard` was going to die. Widening it is a deliberate act with a
    census in front of it.
    """
    prose = "# doc\n\nIt runs 12 checks.\n"
    assert run_check({"docs/history/old.md": prose}) == []
    assert run_check({"docs/specs/a-spec.md": prose}) == []
    assert len(run_check({"docs/top-level.md": prose})) == 1


# --------------------------------------------------------------------------- #
# the instrument controls
# --------------------------------------------------------------------------- #
def test_the_floor_fires_when_the_walk_goes_blind(run_check):
    """`MIN_COUNT_SCANNED` guards BOTH ways this check can pass by reading nothing.

    A glob that stops matching, and an exemption predicate that widens until it swallows
    the corpus, produce the identical symptom: a green run over almost no files. One
    number catches both because it counts files walked AND not exempt. The archived
    design's own `MIN_DOCS_SCANNED` caught its walker mid-session seeing 21 records
    instead of 22 -- *"a guard that scans nothing passes forever. Fix the walk, not the
    floor."*
    """
    failures = run_check({"docs/live.md": "# doc\n\nnothing to see\n"},
                         floor=handoff_lint.MIN_COUNT_SCANNED)
    assert len(failures) == 1, failures
    assert "scanned only 3 file(s)" in failures[0]
    assert "Fix the walk, not" in failures[0]


def test_a_banner_on_every_file_trips_the_same_floor(run_check):
    """The exemption-went-broad direction, which is the one silence hides.

    A blind GLOB is visible the moment anyone looks at the file list; an exemption that
    quietly matches everything looks exactly like a clean corpus. Same floor, and this is
    the case that justifies counting scanned rather than walked.
    """
    files = {"docs/d%d.md" % i: FROZEN_BANNER + "\n12 checks run.\n" for i in range(50)}
    files["CLAUDE.md"] = FROZEN_BANNER
    files["HANDOFF.md"] = FROZEN_BANNER
    failures = run_check(files, floor=handoff_lint.MIN_COUNT_SCANNED)
    assert len(failures) == 1, failures
    assert "scanned only 0 file(s)" in failures[0]


def test_a_missing_declared_file_is_reported(run_check, tmp_path):
    """The declared half of "a declared list AND a walk".

    A glob cannot notice that it stopped seeing something; the declared list can. Deleting
    `HANDOFF.md` must be loud rather than a quietly smaller scan.
    """
    root = tmp_path / "repo"
    root.mkdir(exist_ok=True)
    run_check({})                      # writes the stubs
    (root / "HANDOFF.md").unlink()
    failures: list = []   # the floor stays neutralised by the fixture's monkeypatch
    handoff_lint.check_restated_counts(failures.append)
    assert len(failures) == 1, failures
    assert failures[0].startswith("MISSING: HANDOFF.md")


def test_the_check_is_registered_in_the_gated_tuple():
    """It rides `CHECKS`, therefore `verify.sh` step 4f, therefore `lean`.

    A standalone script nobody's gate runs is the dead check the archived design warned
    about -- and the check being WRITTEN is not the same fact as the check being RUN.
    """
    assert handoff_lint.check_restated_counts in handoff_lint.CHECKS


# --------------------------------------------------------------------------- #
# tier caps (TK128, 2026-10-07d) -- a VALUE check riding the same walk
# --------------------------------------------------------------------------- #
# MUTATION SWEEP, 2026-10-07d: nine plausible one-line weakenings of the cap check, each
# exec'd IN MEMORY as `scripts.handoff_lint` (the shipped file was never edited), with this
# module run against every one. 9/9 caught, by the test named (unmutated: 22 passed):
#
#   cap check after dated escape  1 failed  ..._caught_even_on_a_dated_line
#   tier name blanked too         3 failed  ..._dated_line, ..._agrees_..., ..._extracts_...
#   comparison form dropped       2 failed  ..._agrees_..., ..._extracts_...
#   hardcoded NEXT 5              1 failed  ..._reads_the_live_constant_not_a_literal
#   no intervening words          3 failed  ..._agrees_..., ..._extracts_..., ..._live_constant_...
#   tier case-insensitive         1 failed  ..._not_a_tier_cap_stay_silent
#   quote escape off for caps     1 failed  ..._extracts_... (the quoted-phrase assertion)
#   spelled numbers dropped       1 failed  ..._extracts_...
#   NOW cap off (1 -> 2)          3 failed  ..._agrees_..., ..._extracts_..., ..._live_constant_...
#
# The quote-escape row was a hole on the first pass (the `cap of `3`` assertion cannot
# tell: a backtick already breaks the pattern), closed by asserting a fully quoted phrase.
# The line the check exists for, cut from `HANDOFF.md`'s banner as it stood on 2026-10-07
# (baseline copy of the 2026-10-07d housekeeping run). It carries a `2026-09-22` key, which
# is the whole point: the dated escape silences a census, and it silenced this cap too
# until TK128 moved the cap check in front of it.
STALE_BANNER_LINE = (
    "> **`ASK-*` is a NEW id series, decided with the user 2026-09-22**: `LATER` by "
    "default; **`NEXT` means the session must raise it with the user in chat that "
    "session**, and `NEXT`'s cap of 3 bounds the standing nags at three."
)


def test_a_stale_tier_cap_in_the_banner_is_caught_even_on_a_dated_line(run_check):
    """THE sabotage for TK128: the real stale banner line, planted back.

    Literal observed output (2026-10-07d, this test's run against the shipped check)::

        HANDOFF.md:3 restates the NEXT cap as 3 ("NEXT`'s cap of 3"), but the live cap
        is 5. A cap is a rule, not a stamped measurement, so a date on the line does
        not excuse it. DELETE the number and point at its home (`tasks/config.json`
        `budgets` (mirrored by `handoff_lint.py::NEXT_MAX`)); ...

    Before TK128 the same input produced NO failure -- no pattern spoke of caps, and the
    line's `2026-09-22` would have tripped the dated escape anyway. Both halves of that
    are pinned: the failure exists, and it survives the date.
    """
    failures = run_check({"HANDOFF.md": "# HANDOFF\n\n%s\n" % STALE_BANNER_LINE})
    assert len(failures) == 1, failures
    assert "HANDOFF.md:3" in failures[0]
    assert "NEXT cap as 3" in failures[0]
    assert "live cap is %d" % handoff_lint.NEXT_MAX in failures[0]


def test_a_tier_cap_that_agrees_with_the_live_value_passes(run_check):
    """A VALUE check, not a refusal: the right number is silent, the wrong one is not.

    Each correct phrasing is paired with the same phrasing off by one, so a pattern that
    has quietly stopped matching cannot pass this as "agrees".
    """
    live = handoff_lint.NEXT_MAX
    for tmpl in ("`NEXT`'s cap of %d bounds the nags.",
                 "`NEXT` is capped at %d now.",
                 "the NEXT tier has a cap of %d",
                 "it refuses to break `NOW`=1 / `NEXT`<=%d at write time"):
        assert run_check({"docs/live.md": "# live\n\n%s\n" % (tmpl % live)}) == [], tmpl
        bad = run_check({"docs/live.md": "# live\n\n%s\n" % (tmpl % (live + 1))})
        assert len(bad) == 1 and "NEXT cap as %d" % (live + 1) in bad[0], (tmpl, bad)
    assert run_check({"docs/live.md": "# live\n\nNOW is capped at 1.\n"}) == []
    assert len(run_check({"docs/live.md": "# live\n\nNOW is capped at 2.\n"})) == 1


def test_each_cap_phrasing_extracts_the_tier_and_number():
    """Token-level instrument control for BOTH cap patterns (the TK58 lesson: a module
    guarding N patterns must assert on all N). Spelled-out numbers count, a backticked
    tier name survives the quote-blanker, a backticked NUMBER does not."""
    caps = handoff_lint._restated_caps
    assert caps("NEXT has a cap of three") == [
        ("NEXT", 3, handoff_lint.NEXT_MAX, "NEXT has a cap of three")]
    assert caps("violate the NOW=1 / NEXT<=3 budget") == [
        ("NEXT", 3, handoff_lint.NEXT_MAX, "NEXT<=3")]
    assert [c[:2] for c in caps("`NEXT`'s cap of 3")] == [("NEXT", 3)]
    assert caps("`NEXT`'s cap of `3`") == []          # quoted figure: a citation
    assert caps("it used to read `NEXT is capped at 3`") == []   # quoted phrase, ditto


def test_cap_phrasings_that_are_not_a_tier_cap_stay_silent(run_check):
    """The false-positive side, each one a real or near-real line.

    Lower-case "next" is English, not the tier. "the 100,000 fan-out cap of rows" is the
    closure cap (CLAUDE.md). The bare noun form "NEXT cap 3" is NOT matched on purpose:
    the open TK128 row's frontmatter brief quotes the defect in exactly that form. And the
    fence / FROZEN escapes still apply to caps, as they do to censuses.
    """
    for line in ("the next cap of 3 is fine", "up to the 100,000 fan-out cap of rows",
                 "banner says NEXT cap 3 (it is 5)"):
        assert run_check({"docs/live.md": "# live\n\n%s\n" % line}) == [], line
    fenced = "# live\n\n```\nNEXT is capped at 3\n```\n"
    assert run_check({"docs/live.md": fenced}) == []
    assert run_check({"docs/live.md": FROZEN_BANNER + "\nNEXT is capped at 3.\n"}) == []


def test_the_cap_check_reads_the_live_constant_not_a_literal(run_check, monkeypatch):
    """If the cap moves, the check moves with it. Raising `NEXT_MAX` to 5 on 2026-10-04g
    is what made the banner stale; a check with a hardcoded 5 would go stale the same way
    at the next raise. `TIER_CAPS` must also agree with `NEXT_MAX` itself."""
    assert handoff_lint.TIER_CAPS == {"NOW": 1, "NEXT": handoff_lint.NEXT_MAX}
    monkeypatch.setitem(handoff_lint.TIER_CAPS, "NEXT", 3)
    assert run_check({"docs/live.md": "# live\n\nNEXT is capped at 3.\n"}) == []
    assert len(run_check({"docs/live.md": "# live\n\nNEXT is capped at 5.\n"})) == 1


# --------------------------------------------------------------------------- #
# bound-first caps, wrapped caps, and the fence-toggle blind spot (fix-hk, 2026-10-07d)
# --------------------------------------------------------------------------- #
# The TK128 version above was reviewed and found blind to the form that had actually
# rotted: the rule sentence "at most three `NEXT` among OPEN tasks", bound FIRST. Three such
# lines were live in scanned docs when the check landed green, one of them wrapped across
# two lines, and three more sat in docs/tasktool-spec.md BEHIND a prose line starting with
# three backticks, which the walk took for a fence and which hid the rest of the file.
# Retrospective control (2026-10-07d): the shipped check, run on HEAD e8b340b's
# docs/tasktool-spec.md + docs/gate-runbook.md, now reports exactly the five sites a
# reviewer and an independent census found by hand --
#   gate-runbook.md:304 'at most three `NEXT'   gate-runbook.md:451 (wrapped, same token)
#   tasktool-spec.md:157 '<= 3 NEXT'   :343 'NEXT<=3'   :425 'at most three `NEXT'
# and before this change it reported none of them. Literal observed line for :425:
#   docs/tasktool-spec.md:425 restates the NEXT cap as 3 ('at most three `NEXT'), but the
#   live cap is 5. A cap is a rule, not a stamped measurement, ...
#
# MUTATION SWEEP, 2026-10-07d, each mutant exec'd in memory as `scripts.handoff_lint`, this
# module run against it (unmutated: 25 passed). 7/7 caught:
#
#   M1 bound-first pattern never matches     3 failed  bound_first, wrapped, prose_line
#   M2 no join (per-line only)               1 failed  wrapped  (AssertionError: [], 0 == 1)
#   M3 join re-reports non-crossing matches  6 failed  every single-line cap test (doubled)
#   M4 fence = any line starting with ```    1 failed  prose_line  (AssertionError: [])
#   M5 walk never passes the next line       1 failed  wrapped
#   M6 bound words narrowed to "at most"     1 failed  bound_first
#   M7 join takes next-line-only matches     6 failed  every single-line cap test (doubled)
#
# Not tested, on purpose: a fence / `## Log` guard on the join. No such line can COMPLETE
# a crossing match (neither starts with a number or a tier name), so a guard would be an
# untestable branch; the walk carries a comment saying so instead.
BOUND_FIRST_LINE = "5. exactly one `NOW` and at most three `NEXT` among OPEN tasks;"
WRAPPED_LINES = ("  exactly one `NOW` row and at\n"
                 "  most three `NEXT`, zero retired glyphs, the trap budget\n")
BACKTICK_PROSE = "  ``` or `~~~` fence is skipped, so a worked example of the banner shape\n"


def test_a_bound_first_cap_is_caught_and_a_correct_one_is_not(run_check):
    """The real check-5 line of docs/tasktool-spec.md, planted back; the same sentence at
    the live value is silent (a VALUE check, as above). Every bound word is exercised so
    one that quietly stops matching cannot pass."""
    bad = run_check({"docs/live.md": "# live\n\n%s\n" % BOUND_FIRST_LINE})
    assert len(bad) == 1 and "docs/live.md:3" in bad[0], bad
    assert "NEXT cap as 3" in bad[0] and "at most three `NEXT" in bad[0], bad
    live = handoff_lint.NEXT_MAX
    for bound in ("at most", "<=", "≤", "up to", "no more than", "maximum of", "max"):
        ok = "# live\n\nthere are %s %d `NEXT` rows.\n" % (bound, live)
        assert run_check({"docs/live.md": ok}) == [], bound
        stale = "# live\n\nthere are %s %d `NEXT` rows.\n" % (bound, live - 2)
        assert len(run_check({"docs/live.md": stale})) == 1, bound
    assert run_check({"docs/live.md": "# live\n\nat most two NOW rows\n"}) != []


def test_a_cap_wrapped_across_two_lines_is_caught_once(run_check):
    """docs/gate-runbook.md 4f as it stood: "at" ends one line, "most three `NEXT`" starts
    the next. Reported ONCE, on the line the claim starts on -- not zero times (a per-line
    walk), and not twice (a join that re-reports what one line already shows)."""
    bad = run_check({"docs/live.md": "# live\n\n" + WRAPPED_LINES})
    assert len(bad) == 1, bad
    assert "docs/live.md:3" in bad[0] and "at most three `NEXT" in bad[0], bad
    one_line = run_check({"docs/live.md": "# live\n\n%s\nnext line\n" % BOUND_FIRST_LINE})
    assert len(one_line) == 1, one_line
    # a claim wholly on the NEXT line is reported there, not on this one
    later = run_check({"docs/live.md": "# live\n\nintro\n%s\n" % BOUND_FIRST_LINE})
    assert len(later) == 1 and "docs/live.md:4" in later[0], later


def test_a_prose_line_starting_with_backticks_does_not_blind_the_walk(run_check):
    """docs/tasktool-spec.md's "``` or `~~~` fence is skipped" line, planted above a real
    fenced example and a stale cap. CommonMark: a backtick fence's info string may not
    contain a backtick, so that line is prose. Before fix-hk it toggled the fence state,
    the real fence after it was read as an OPENER, and every line after that -- here the
    stale cap -- was never scanned. A real fence still hides its body."""
    text = ("# live\n\n" + BACKTICK_PROSE + "\n```json\n{\"NEXT\": 3}\n```\n\n"
            + BOUND_FIRST_LINE + "\n")
    bad = run_check({"docs/live.md": text})
    assert len(bad) == 1 and "docs/live.md:9" in bad[0], bad
    assert handoff_lint._is_fence("```") and handoff_lint._is_fence("  ```json")
    assert not handoff_lint._is_fence(BACKTICK_PROSE)
