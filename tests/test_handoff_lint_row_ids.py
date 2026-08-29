"""`check_ledger_row_ids`' extractor, pinned against the hole that made it pass.

`scripts/handoff_lint.py::check_ledger_row_ids` exists to catch a ledger `rows:`
line citing a board id that resolves to nothing -- a typo or an invention. Board
row `TK46` found that it could not: `_ROW_ID` was

    \\b([A-Z]{1,3}-?\\d+|ZT-[A-Z0-9-]+)\\b

and on `R6-99` the first alternative matched `R6` and stopped at the word
boundary before the hyphen. `R6` **is** a real id, so the comparison found it and
reported clean. Every `R6-N` sub-item sat in that blind spot -- nineteen ids at
the time, roughly a fifth of the live id space.

WHY THE ORIGINAL SABOTAGE MISSED IT, which is the transferable part. The check
shipped 2026-08-16 with a sabotage on its docstring record::

    rows: ids     FAIL: docs/history/session-log.md:2 cites board id 'P99', which
                        is on neither the board nor its retired-ids line.

`P99` proves the COMPARISON works. It cannot prove the regex READ the id being
compared, because `P99` is a shape the regex handles. **The instrument was not
controlled, only the subject** (`docs/sabotage-procedure.md`, "control your
instrument as well as your subject"), and the id shape that was actually blind
was never tried. That is why `test_extractor_reads_the_whole_sub_item_id` below
asserts on the extracted TOKENS and not only on the verdict.

SABOTAGE RECORD (observed 2026-08-24c against the REAL corpus -- `HANDOFF.md` and
`docs/history/session-log.md` copied to a temp root, with `session-log.md:123`'s
`rows:` line citing an invented `R6-99` in place of `HS-5`). Both regexes run
against the identical sabotaged corpus::

    inherited -> 0 violation(s); tokens ['R6', 'R6', 'P3', 'P6']
    ported    -> 1 violation(s); tokens ['R6-99', 'R6', 'P3', 'P6']
        FAIL: docs/history/session-log.md:123 cites board id 'R6-99', which
        appears nowhere in HANDOFF.md -- not as a row, not on the retired-ids
        line, not in an item block.

The token lists are the evidence that matters: the inherited regex never had
`R6-99` in hand, so its silence was not a judgement.

CONTROLS on the same corpus, one probe per citation, ported regex::

    R6-99   -> 1 violation(s)      invented sub-item      (the closed hole)
    P99     -> 1 violation(s)      invented top-level     (2026-08-16 behaviour)
    R6-10   -> 0 violation(s)      real, prose-only       (see below)
    R6-19   -> 0 violation(s)      real, prose-only
    HS-5    -> 0 violation(s)      real board row         (not firing on shape)

`R6-10` IS THE REASON THIS IS NOT A ONE-LINE FIX. `TK46` recorded the fix as
"porting one line". Porting only the regex was run against the live tree and
observed::

    FAIL: docs/history/session-log.md:388 cites board id 'R6-10', which is on
    neither the board nor its retired-ids line.

`R6-10` is a real, landed sub-item. The board names it in the `### R6` item block
and deliberately gives it no table row, because sub-items are not ranked -- and a
ledger legitimately cites it. So `known` now harvests ids from the whole board,
with the non-vacuity floor kept on the TABLE harvest specifically
(`test_the_floor_fires_when_the_row_parser_breaks`): put the floor on the
whole-file harvest and a broken row parser would coast on prose.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# `scripts/` has no __init__.py and pytest.ini sets no pythonpath -- same explicit
# insert, and same reason, as tests/test_gate_status.py.
sys.path.insert(0, str(REPO_ROOT))
from scripts import handoff_lint  # noqa: E402

# The pre-TK46 extractor, kept verbatim so the hole can be re-demonstrated rather
# than merely described. `test_the_inherited_extractor_had_the_hole` is what makes
# this suite evidence that the fix fixed something.
INHERITED_ROW_ID = re.compile(r'\b([A-Z]{1,3}-?\d+|ZT-[A-Z0-9-]+)\b')

BOARD = """# HANDOFF -- the board

| id | item | pri | size | deps | moved |
|---|---|---|---|---|---|
| `P3` | leg 7 4c-ii | **NOW** | L | - | 2026-08-21b |
| `P6` | ttuStarFree (ii) | **NEXT** | M | - | 2026-08-20b |
| `R6` | perf round 6 | **NEXT** | L | - | 2026-08-24 |
| `P4` | leg 7 4b | LATER | M | `P3` | 2026-08-16 |
| `HS-5` | liveness banners | LATER | S | - | 2026-08-24 |

Closed ids stay retired: `P1`, `P2`, `BL-2`.

### `R6` -- perf round 6

`R6-10` landed 2026-08-20b (2.54x). Remaining order: `R6-6` then `R6-19`.
"""


def _write_corpus(root: Path, rows_line: str) -> None:
    """A minimal board plus a ledger whose single `rows:` line is `rows_line`."""
    (root / "HANDOFF.md").write_text(BOARD, encoding="utf-8")
    ledger = root / "docs" / "history"
    ledger.mkdir(parents=True)
    (ledger / "session-log.md").write_text(
        "# session log\n\n## 2026-08-24 headline\n\n%s\n" % rows_line, encoding="utf-8"
    )


# A task file as `scripts/task.py` writes one: YAML-ish frontmatter between `---`
# fences, `id:` on its own line. `_tree_ids` reads the first 20 lines only.
TASK_FILE = "---\nid: %s\ntitle: %s\npri: LATER\nsize: S\ndeps: []\n---\n\nbody\n"

# The tree that MATCHES `BOARD`, keyed filename -> frontmatter id. It must cover
# every id `check_ledger_row_ids` puts in `row_ids`, which is the table's first
# column PLUS the "Closed ids stay retired" line -- so `P1`/`P2`/`BL-2` are here
# too, carried by `RETIRED` the way the live tree carries them.
TREE = {
    "P3-leg-7-4c-ii.md": "P3",
    "P6-ttustarfree-ii.md": "P6",
    "R6-perf-round-6.md": "R6",
    "P4-leg-7-4b.md": "P4",
    "HS-5-liveness-banners.md": "HS-5",
}
RETIRED = "# Ids that are spent. NEVER reused.\n#\n\nP1\nP2\nBL-2\n"


def _write_tasks(root: Path, files: dict, retired: str | None = RETIRED) -> None:
    """Write a `tasks/` tree under `root`. `files` maps a path RELATIVE TO
    `tasks/` (so `closed/X.md` works) to the id that file's frontmatter declares.
    The two are deliberately independent -- disagreeing with each other is the
    point of `test_tree_ids_reads_the_frontmatter_not_the_filename`.
    """
    tasks = root / "tasks"
    tasks.mkdir(exist_ok=True)
    for rel, task_id in files.items():
        path = tasks / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(TASK_FILE % (task_id, rel), encoding="utf-8")
    if retired is not None:
        (tasks / "retired-ids.txt").write_text(retired, encoding="utf-8")


@pytest.fixture()
def run_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run `check_ledger_row_ids` over a synthetic corpus; return its failures.

    `tree=None` writes no `tasks/` directory at all, which is the pre-trial state
    and the one `_tree_ids` answers `None` for -- not the same thing as an empty
    tree, and the check treats them differently.
    """

    def _run(rows_line: str, board: str | None = None,
             tree: dict | None = None, retired: str | None = RETIRED) -> list:
        root = tmp_path / "repo"
        root.mkdir()
        _write_corpus(root, rows_line)
        if board is not None:
            (root / "HANDOFF.md").write_text(board, encoding="utf-8")
        if tree is not None:
            _write_tasks(root, tree, retired)
        monkeypatch.setattr(handoff_lint, "REPO", str(root))
        failures: list = []
        handoff_lint.check_ledger_row_ids(failures.append)
        return failures

    return _run


@pytest.fixture()
def tree_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Harvest `_tree_ids` directly off a synthetic tree; no board is involved."""

    def _run(files: dict, retired: str | None = None, make_tree: bool = True):
        root = tmp_path / "treeroot"
        root.mkdir()
        if make_tree:
            _write_tasks(root, files, retired)
        monkeypatch.setattr(handoff_lint, "REPO", str(root))
        return handoff_lint._tree_ids()

    return _run


# --------------------------------------------------------------------------- #
# the sabotage, and the hole it re-demonstrates
# --------------------------------------------------------------------------- #
def test_an_invented_sub_item_id_is_caught(run_check):
    """`R6-99` resolves to nothing and must be reported.

    THE sabotage. Its parent `R6` is a real row, which is precisely why the
    inherited extractor let it through.
    """
    failures = run_check("rows: `R6-99` (count corrected).")
    assert len(failures) == 1, failures
    assert "R6-99" in failures[0]


def test_the_inherited_extractor_had_the_hole(monkeypatch):
    """The pre-fix regex truncates `R6-99` to the real parent id `R6`.

    Pinned so the fix cannot be silently reverted into "it always worked". This
    asserts on the EXTRACTOR, because the verdict alone cannot distinguish "the
    regex read the id and judged it fine" from "the regex never saw it".
    """
    assert INHERITED_ROW_ID.findall("rows: R6-99 corrected") == ["R6"]
    assert handoff_lint._ROW_ID.findall("rows: R6-99 corrected") == ["R6-99"]


def test_extractor_reads_the_whole_sub_item_id():
    """Token-level instrument control over a realistic mixed `rows:` line.

    `P99`-style sabotage cannot reach this: it exercises the comparison, not the
    read. Every id shape the board actually uses appears here.
    """
    line = "rows: R6-99 , R6-19 , AW-1 , P3 , B2 , R6 ."
    assert handoff_lint._ROW_ID.findall(line) == [
        "R6-99", "R6-19", "AW-1", "P3", "B2", "R6",
    ]


def test_compound_zt_ids_survive_the_widening():
    """Widening a regex can go the other way -- the `ZT-*` compounds still parse.

    `TK46`'s third trap. The zero-trust series is the only multi-segment id shape
    in the corpus, and a widened alternation that swallowed or split it would
    trade one hole for another.
    """
    assert handoff_lint._ROW_ID.findall("ZT-P5-NEW") == ["ZT-P5-NEW"]
    assert handoff_lint._ROW_ID.findall("ZT-P1 and ZT-P4-1") == ["ZT-P1", "ZT-P4-1"]


# --------------------------------------------------------------------------- #
# controls -- the fix must not buy detection with false reds
# --------------------------------------------------------------------------- #
def test_a_real_sub_item_named_only_in_prose_is_accepted(run_check):
    """`R6-10` has no table row on purpose, and a ledger legitimately cites it.

    The false red observed when only the regex was ported. This is the control
    that keeps the extractor fix from being paid for in noise.
    """
    assert run_check("rows: `R6-10` (landed), `R6-19` (next).") == []


def test_a_real_board_row_is_accepted(run_check):
    """Positive control: the check is judging the id, not the line's shape."""
    assert run_check("rows: `HS-5` (retitled), `P3` / `P6` (a related edge).") == []


def test_an_invented_top_level_id_is_still_caught(run_check):
    """The 2026-08-16 behaviour survives the widening -- `P99` still fails."""
    failures = run_check("rows: `P99` (new).")
    assert len(failures) == 1, failures
    assert "P99" in failures[0]


def test_a_line_that_is_not_a_rows_line_is_ignored(run_check):
    """Scope control: only `rows:` lines are read, so prose ids cannot false-red."""
    assert run_check("This entry mentions R6-99 and P99 in prose, not on a rows line.") == []


# --------------------------------------------------------------------------- #
# the non-vacuity floor
# --------------------------------------------------------------------------- #
def test_the_floor_fires_when_the_row_parser_breaks(run_check):
    """A board whose TABLE cannot be parsed fails, even though its prose is full
    of ids.

    `known` reads the whole board now, so the floor had to stay on the table
    harvest -- otherwise the day `_table_rows` breaks, this check would compare
    against a prose-scraped set, find everything, and report clean. That is the
    exact failure mode the floor was added for.
    """
    prose_only = (
        "# HANDOFF -- the board\n\n"
        "P3 is NOW. P6 and R6 are NEXT. P4, HS-5, R6-10, R6-19 exist too.\n"
    )
    failures = run_check("rows: `P3`.", board=prose_only)
    assert len(failures) == 1, failures
    assert "the id parser is broken" in failures[0]


# --------------------------------------------------------------------------- #
# the task tree as a SECOND id source (added 2026-08-29)
#
# `tasks/` is the file-per-task tree the board is on trial against. When it is
# present its ids are unioned into `known`, it carries its own non-vacuity floor,
# and -- because CLAUDE.md's trial contract is that a board row and its task file
# move in the SAME session -- a board row with no task file is itself a failure.
# The tests below split into the CHECK's behaviour (1, 2, 3, 4, 8) and the
# HARVESTER's behaviour (5, 6, 7), because the check cannot distinguish "the
# harvester read this id and matched it" from "the harvester invented it".
# --------------------------------------------------------------------------- #
def test_a_board_row_with_no_task_file_fails(run_check):
    """The divergence direction that IS checked: board row -> task file.

    A row that exists in only one tree is the trial contract silently broken, and
    since the trial's whole result is the comparison between the two trees, an
    unnoticed divergence destroys the evidence rather than merely leaving a stale
    file. The message must NAME the id, otherwise the fix is a tree-wide diff.

    SABOTAGE: `i not in tree_ids` -> `i not in known` in `missing`. An innocent
    refactor -- `known` is the set every other comparison in this function uses --
    and it can never fire, because `known` is seeded from `row_ids` itself.
    Observed (2026-08-29)::

        E   AssertionError: []
        E   assert 0 == 1
        E    +  where 0 = len([])

    The empty list IS the evidence: the sabotaged check reported clean on a corpus
    whose board names an id the tree does not carry.
    """
    partial = {k: v for k, v in TREE.items() if v != "HS-5"}
    failures = run_check("rows: `P3`.", tree=partial)
    assert len(failures) == 1, failures
    assert "'HS-5'" in failures[0]
    assert "has no task file for" in failures[0]


def test_a_task_file_with_no_board_row_stays_clean(run_check):
    """The reverse direction is false BY DESIGN and must never fire.

    Hand-filed tasks that were never board rows are most of why the tree exists --
    51 of them at the trial's start. A check that reddens on correct use is a check
    that gets deleted, which is the same reasoning that scoped `HEADLINE_LEDGERS`
    and `MENTION_ROOTS` in this script.

    SABOTAGE: make the parity check bidirectional by appending

        missing += sorted(i for i in tree_ids if i not in row_ids)

    -- the "obvious" completion of a one-directional comparison. Observed
    (2026-08-29), with pytest's own truncation left in::

        E   assert ['HANDOFF.md ...ove the row.'] == []
        E     Left contains one more item: "HANDOFF.md names 'N42', 'TK99', which
        E     tasks has no task file for. The trial contract in CLAUDE.md is that a
        E     board row...s is lost evidence rather than an untidy file. ..."

    Two hand-filed tasks, two false reds. Scaled to the live tree that is 51.
    """
    extra = dict(TREE)
    extra["TK99-a-hand-filed-task.md"] = "TK99"
    extra["closed/N42-a-closed-hand-filed-task.md"] = "N42"
    assert run_check("rows: `P3`.", tree=extra) == []


def test_no_tasks_dir_is_none_and_the_check_stays_board_only(run_check, tree_ids):
    """No `tasks/` at all is a legitimate state -- the one this repo shipped in.

    `None` and an EMPTY SET are different answers: `None` means "no tree here",
    an empty set means "the tree is there and the harvester read nothing", which
    is the blind-parser failure the `< 5` floor exists for. Returning `set()` for
    the first case would collapse them, and the pre-trial repo would fail the
    floor forever -- a check nobody can satisfy is a check that gets commented out.

    SABOTAGE: `return None` -> `return set()` in `_tree_ids`. Observed
    (2026-08-29) -- `7 failed, 10 passed`, i.e. it took SIX of the pre-existing
    board-only tests down with it, every one of them now tripping the tree floor
    on a repo that has no tree::

        E   assert set() is None
    """
    assert tree_ids({}, make_tree=False) is None
    # ... and the check still does its board-only job. One corpus, both signs: the
    # two real ids must stay quiet and the invented one must still be caught, so a
    # blanket pass and a blanket fail are both excluded by the same call.
    failures = run_check("rows: `HS-5`, `P99`, `P3`.")
    assert len(failures) == 1, failures
    assert "P99" in failures[0]
    # No tree, so the message must not claim anything about task files.
    assert "no task file" not in failures[0]


def test_the_tree_floor_fires_when_the_harvester_goes_blind(run_check):
    """A tree that harvests fewer than 5 ids fails, mirroring the board floor.

    The blind-harvester control. Without it, the day `_tree_ids` stops parsing
    frontmatter this check compares every ledger citation against a near-empty
    set -- and the `known` union means the failure mode is SILENCE on the board
    side plus noise on the row side, i.e. exactly the "passes by comparing against
    nothing" shape `test_the_floor_fires_when_the_row_parser_breaks` guards.

    SABOTAGE: delete the `if len(tree_ids) < 5:` branch. Observed (2026-08-29)::

        E   assert 'the harvester is broken' in "HANDOFF.md names 'BL-2', 'HS-5',
        E   'P1', 'P2', 'P3', 'P4', 'P6', 'R6', which tasks has no task file for.
        E   The trial cont...s is lost evidence rather than an untidy file. ..."

    ⚠ THAT RED IS NOT THE ONE THE FLOOR'S OWN MESSAGE PREDICTS, and the difference
    is a real finding rather than a wording quibble -- the floor guards a DIFFERENT
    state from the one it names. Probed directly, floor deleted, three corpora::

        board+tree, blind harvester      -> LOUD (8 board rows reported missing)
        stub board, tree of 0, cites X1  -> LOUD (the citation resolves nowhere)
        stub board, tree of 2, cites AA-1-> SILENT, 0 failures

    The third line is the floor's actual justification and the only one that is
    silent: after a cutover `HANDOFF.md` is a stub with no table, so `row_ids` is
    empty, nothing can be missing, and the tree is the only comparand left -- a
    half-blind harvester that still happens to hold the cited id then passes by
    comparing against almost nothing, exactly as the message says. WHILE BOTH TREES
    EXIST the floor is buying a precise diagnosis and an early `return`, not
    detection, because the parity comparison would catch a blind harvester anyway.
    Do not "simplify" it away on the strength of that: the state it guards is the
    one this repo is trying to reach.
    """
    failures = run_check("rows: `P3`.",
                         tree={"A-one.md": "AA-1", "B-two.md": "BB-1"}, retired=None)
    assert len(failures) == 1, failures
    assert "the harvester is broken" in failures[0]
    assert "harvested only 2 ids" in failures[0]


def test_tree_ids_reads_the_frontmatter_not_the_filename(tree_ids):
    """The id is the address; the filename is cosmetic.

    `scripts/task.py` resolves by glob and then falls back to a full frontmatter
    scan for exactly this reason, so harvesting names off disk would disagree with
    the tool the first time anyone renamed a file -- and disagree in the direction
    that INVENTS ids, which is the direction this check cannot detect.

    SABOTAGE: harvest `name.split('-')[0]` from the filename instead of opening
    the file. It is the cheaper implementation and it looks right against the live
    tree, where the two agree. Observed (2026-08-29)::

        E   AssertionError: assert {'P3'} == {'TK99'}

    `5 failed, 12 passed` -- and note WHICH way it fails on the live naming
    convention: `HS-5-liveness-banners.md` harvests as `HS`, not `HS-5`, so the
    filename shortcut both misses real ids and mints ones that were never filed.
    """
    assert tree_ids({"P3-a-stale-filename.md": "TK99"}) == {"TK99"}


def test_tree_ids_skips_top_level_banner_and_readme_only(tree_ids):
    """`BANNER.md`/`README.md` are skipped at the TOP LEVEL, not under `closed/`.

    Both halves matter. Not skipping them harvests prose files as tasks (spurious
    ids, which weaken the comparison silently); skipping them everywhere drops
    real closed tasks that happen to be named that way -- and `TASKS_NON_TASK_MD`
    is duplicated from `scripts/task.py::NON_TASK_MD` rather than imported, so the
    two lists CAN drift and the scope of the skip has to be pinned here.

    SABOTAGE: drop the `top and` guard -- `(top and name in TASKS_NON_TASK_MD)`
    -> `name in TASKS_NON_TASK_MD`. Observed (2026-08-29)::

        E   AssertionError: assert {'TK99'} == {'CB-1', 'CR-1', 'TK99'}
        E     Extra items in the right set:
        E     'CB-1'
        E     'CR-1'
    """
    harvested = tree_ids({
        "BANNER.md": "BAN-1",
        "README.md": "RDM-1",
        "T1-a-real-task.md": "TK99",
        "closed/BANNER.md": "CB-1",
        "closed/README.md": "CR-1",
    })
    assert harvested == {"TK99", "CB-1", "CR-1"}


def test_retired_ids_are_harvested_with_comments_and_blanks_skipped(tree_ids, run_check):
    """`tasks/retired-ids.txt` is the third id source, and it is a plain list.

    Ids are never reused, so a retired id is still a resolvable citation -- the
    board expresses this with its "Closed ids stay retired" line and the tree with
    this file. The file is heavily commented (its header explains why it is empty
    today), so a harvester that does not strip `#` lines poisons `known` with
    prose tokens, which can only ever make this check quieter.

    SABOTAGE: `if ln and not ln.startswith('#')` -> `if ln`. Observed
    (2026-08-29)::

        E   AssertionError: assert {'#', '# Ids ...RT-9', 'TK99'}
        E                       == {'RT-10', 'RT-9', 'TK99'}
        E     Extra items in the left set:
        E     '# Ids that are spent.'
        E     '#'
    """
    harvested = tree_ids(
        {"T1-a-real-task.md": "TK99"},
        retired="# Ids that are spent.\n#\n\nRT-9\n   \nRT-10\n",
    )
    assert harvested == {"TK99", "RT-9", "RT-10"}
    # ... and a ledger citing a retired id therefore resolves.
    assert run_check("rows: `RT-9` (retired).", tree=TREE,
                     retired=RETIRED + "RT-9\n") == []


def test_the_row_id_filter_keeps_table_furniture_out_of_the_comparison(run_check):
    """`_table_rows` yields the header and the `|---|---|` separator too.

    So the raw `row_ids` harvest carries `'id'` and `'---'`. Harmless while that
    set only fed the non-vacuity floor; the moment it fed a comparison against the
    tree it produced a permanent, unfixable red on a CLEAN corpus -- there is no
    task file you can write to satisfy it. Literally observed before the filter::

        FAIL: HANDOFF.md names '---', 'id', which tasks has no task file for.

    SABOTAGE (re-demonstrating it): drop the `_ROW_ID.match(i)` guard from the
    `missing` comprehension. Observed (2026-08-29), reproducing the recorded text
    verbatim down to the id list and its order::

        E   assert ['HANDOFF.md ...ove the row.'] == []
        E     Left contains one more item: "HANDOFF.md names '---', 'id', which
        E     tasks has no task file for. The trial contract in CLAUDE.md is that a
        E     board row a...s is lost evidence rather than an untidy file. ..."
    """
    # Instrument control first: the furniture really is in the raw harvest, so the
    # filter is guarding something rather than describing a case that never arises.
    first_cells = [cells[0] for cells, _ in handoff_lint._table_rows(BOARD.split("\n"))]
    assert "id" in first_cells and "---" in first_cells
    # ... and neither is id-SHAPED, which is what the filter tests.
    assert handoff_lint._ROW_ID.match("id") is None
    assert handoff_lint._ROW_ID.match("---") is None
    assert run_check("rows: `P3`.", tree=TREE) == []
