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


@pytest.fixture()
def run_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run `check_ledger_row_ids` over a synthetic corpus; return its failures."""

    def _run(rows_line: str, board: str | None = None) -> list:
        root = tmp_path / "repo"
        root.mkdir()
        _write_corpus(root, rows_line)
        if board is not None:
            (root / "HANDOFF.md").write_text(board, encoding="utf-8")
        monkeypatch.setattr(handoff_lint, "REPO", str(root))
        failures: list = []
        handoff_lint.check_ledger_row_ids(failures.append)
        return failures

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
