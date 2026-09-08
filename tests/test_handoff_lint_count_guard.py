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
