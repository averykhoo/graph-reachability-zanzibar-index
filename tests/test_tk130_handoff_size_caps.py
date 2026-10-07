"""`TK130` (2026-10-07d): the one-hop note's caps can no longer be evaded by line LENGTH.

On 2026-10-07 `HANDOFF.md` was inside both of its line caps -- 56 of 60 lines
(`scripts/handoff_lint.py::MAX_LINES`), and a banner of exactly 14 lines
(`scripts/task.py::BANNER_MAX_LINES`) -- while single banner lines ran to ~3.7k characters
and the file had grown from 3285 B at the 2026-09-06 cutover commit to 18803 B. Each session
had appended a dated layer to an old line instead of rewriting it, which is the layering
`docs/README.md` section 6 bans. Two caps close it, each where its line-count twin lives:

  * `scripts/handoff_lint.py::MAX_BYTES` -- the whole file, in UTF-8 bytes of the LF text, in
    `check_ceilings` (`verify.sh` lean step 4f).
  * `scripts/task.py::BANNER_MAX_WIDTH` -- each banner line as `board` prints it, in
    `check_banner`, lint check 12 (`verify.sh` lean step 4g).

Every red below was watched go red before it was believed (`docs/sabotage-procedure.md`).
MUTATION SWEEP, 2026-10-07d: eleven mutants of the two checks plus three controls, each in a
temp copy of `scripts/` (the shipped files untouched; probe `.scratch/hk-2026-10-07d/
tk130_sweep.py`, gitignored, so the table is kept HERE). Every mutant reddened the test
named for it in advance. `M0`/`M0b` are the attribution controls: raising either cap past
the real 2026-10-07 evasion is red. `M0c` is the documented blind spot: the boundary tests
derive from the live constant, so LOWERING a cap a little is invisible here, by design --
the value is held by its in-file provenance comment, and a raise past the evasion is not.
Literal output (`run | failed tests`)::

    NONE: 9 passed in 0.42s | -
    M0 control: MAX_BYTES 5000 -> 20000 [expect: test_a_note_inside_its_line_cap_but_over_its_byte_cap_is_red]: 3 failed, 6 passed in 0.38s | test_a_note_inside_its_line_cap_but_over_its_byte_cap_is_red, test_the_byte_cap_binds_before_a_full_banner_of_full_width_lines, test_the_byte_cap_is_exact_at_its_boundary_and_blind_to_crlf
    M0b control: BANNER_MAX_WIDTH 600 -> 4000 [expect: test_the_real_evading_line_is_red]: 1 failed, 8 passed in 0.40s | test_the_real_evading_line_is_red
    M0c control (constant-following, expected NO red): MAX_BYTES 5000 -> 4999 [expect: none -- tests derive from the constant]: 9 passed in 0.38s | -
    M1 byte loop iterates nothing [expect: evasion, boundary, missing]: 3 failed, 6 passed in 0.39s | test_a_byte_cap_on_a_missing_file_is_itself_red, test_a_note_inside_its_line_cap_but_over_its_byte_cap_is_red, test_the_byte_cap_is_exact_at_its_boundary_and_blind_to_crlf
    M2 measure raw on-disk bytes (CRLF counted) [expect: boundary (crlf leg)]: 1 failed, 8 passed in 0.40s | test_the_byte_cap_is_exact_at_its_boundary_and_blind_to_crlf
    M3 byte cap off-by-one (>=) [expect: boundary]: 1 failed, 8 passed in 0.39s | test_the_byte_cap_is_exact_at_its_boundary_and_blind_to_crlf
    M4 byte cap only fires past the line cap [expect: evasion, boundary]: 2 failed, 7 passed in 0.39s | test_a_note_inside_its_line_cap_but_over_its_byte_cap_is_red, test_the_byte_cap_is_exact_at_its_boundary_and_blind_to_crlf
    M5 check_ceilings dropped from CHECKS [expect: rides_the_gated_check]: 1 failed, 8 passed in 0.38s | test_the_byte_cap_covers_the_root_note_and_rides_the_gated_check
    M6 width check never fires [expect: overwide]: 2 failed, 7 passed in 0.43s | test_an_overwide_banner_line_is_red_even_at_the_line_cap, test_the_real_evading_line_is_red
    M7 width off-by-one (>=) [expect: exactly_at_the_width_cap]: 1 failed, 8 passed in 0.40s | test_a_banner_line_exactly_at_the_width_cap_is_legal
    M8 width checks the first line only [expect: overwide]: 2 failed, 7 passed in 0.39s | test_an_overwide_banner_line_is_red_even_at_the_line_cap, test_the_real_evading_line_is_red
    M9 width only below the line cap [expect: overwide (at the line cap)]: 1 failed, 8 passed in 0.43s | test_an_overwide_banner_line_is_red_even_at_the_line_cap
    M10 width counted on the raw blockquote line (+2) [expect: exactly_at_the_width_cap]: 1 failed, 8 passed in 0.41s | test_a_banner_line_exactly_at_the_width_cap_is_legal
    M11 check_banner dropped from LINT_CHECKS [expect: rides_lint_check_12]: 1 failed, 8 passed in 0.43s | test_the_width_cap_rides_lint_check_12
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        "tk130_" + name, str(REPO_ROOT / "scripts" / (name + ".py")))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HL = _load("handoff_lint")
TM = _load("task")

def _ceilings(root: Path) -> list[str]:
    out: list[str] = []
    old = HL.REPO
    HL.REPO = str(root)
    try:
        HL.check_ceilings(out.append)
    finally:
        HL.REPO = old
    return out


def _seed_ceiling_root(root: Path, handoff: bytes) -> None:
    """A temp root holding every file `check_ceilings` reads: a missing one is its own red."""
    (root / "formal").mkdir(parents=True, exist_ok=True)
    (root / "formal" / "HANDOFF.md").write_bytes(b"# formal\n")
    # byte-capped too since TK131, and a slack RATCHET since fix-hk (2026-10-07d): a stub far
    # under its cap would be its own red (MAX_BYTES_SLACK), so it is written AT the cap.
    claude = b"# CLAUDE\n"
    (root / "CLAUDE.md").write_bytes(claude + b"x" * (HL.MAX_BYTES["CLAUDE.md"] - len(claude)))
    (root / "HANDOFF.md").write_bytes(handoff)


def _layered_note() -> str:
    """The 2026-10-07 shape: few lines, each a stack of dated layers ~1.3k chars wide."""
    layer = "2026-09-22c -- an old layer that should have been rewritten, not kept. " * 18
    banner = "\n".join("> " + layer for _ in range(TM.BANNER_MAX_LINES))
    return ("# HANDOFF -- the one-hop note\n\n## Banner\n\n" + banner +
            "\n\n## Still owed\n\n- Nothing.\n\n## Next session\n\n- board\n")


# --- the whole-file byte cap (handoff_lint.py::MAX_BYTES) --------------------------------

def test_a_note_inside_its_line_cap_but_over_its_byte_cap_is_red(tmp_path):
    """The evasion itself: under MAX_LINES, over MAX_BYTES. The line ceiling stays SILENT on
    this file -- that silence is the hole -- and the byte ceiling is the one red."""
    text = _layered_note()
    assert len(text.split("\n")) < HL.MAX_LINES["HANDOFF.md"]
    assert len(text.encode("utf-8")) > HL.MAX_BYTES["HANDOFF.md"]
    _seed_ceiling_root(tmp_path, text.encode("utf-8"))
    fails = _ceilings(tmp_path)
    assert len(fails) == 1, fails
    assert fails[0].startswith("HANDOFF.md is %d bytes, ceiling %d"
                               % (len(text.encode("utf-8")), HL.MAX_BYTES["HANDOFF.md"])), fails
    assert "lines, ceiling" not in fails[0], fails


def test_the_byte_cap_is_exact_at_its_boundary_and_blind_to_crlf(tmp_path):
    """At the cap is legal, one byte over is red, and a CRLF checkout of an at-cap file is
    legal: Windows working trees are CRLF (`core.autocrlf`) and CI is LF, and the two must
    measure the same file the same way."""
    cap = HL.MAX_BYTES["HANDOFF.md"]
    head = "# HANDOFF\n\n## Banner\n\n> 2026-10-07d -- x\n\n"
    body_lines = (cap - len(head)) // 150
    at_cap = head + ("y" * 149 + "\n") * body_lines
    at_cap += "z" * (cap - len(at_cap.encode("utf-8")))
    assert len(at_cap.encode("utf-8")) == cap
    assert len(at_cap.split("\n")) <= HL.MAX_LINES["HANDOFF.md"]

    _seed_ceiling_root(tmp_path, at_cap.encode("utf-8"))
    assert _ceilings(tmp_path) == []

    _seed_ceiling_root(tmp_path, (at_cap + "z").encode("utf-8"))
    fails = _ceilings(tmp_path)
    assert len(fails) == 1 and ("is %d bytes, ceiling %d" % (cap + 1, cap)) in fails[0], fails

    crlf = at_cap.replace("\n", "\r\n").encode("utf-8")
    assert len(crlf) > cap
    _seed_ceiling_root(tmp_path, crlf)
    assert _ceilings(tmp_path) == [], "a CRLF checkout must measure as its LF text"


def test_a_byte_cap_on_a_missing_file_is_itself_red(tmp_path):
    """A ceiling on a file that does not exist guards nothing, so both ceilings say so:
    one MISSING from the line loop and one from the byte loop."""
    (tmp_path / "formal").mkdir()
    (tmp_path / "formal" / "HANDOFF.md").write_bytes(b"# formal\n")
    (tmp_path / "CLAUDE.md").write_bytes(b"# CLAUDE\n")
    fails = _ceilings(tmp_path)
    assert sum(f.startswith("MISSING: HANDOFF.md") for f in fails) == 2, fails


def test_the_byte_cap_covers_the_root_note_and_rides_the_gated_check():
    """`check_ceilings` is `CHECKS[0]`, and `verify.sh` lean step 4f runs the script whose
    `main` walks CHECKS; a cap held in a dict nobody iterates would pass by reading nothing."""
    assert "HANDOFF.md" in HL.MAX_BYTES
    assert HL.CHECKS[0] is HL.check_ceilings
    verify = (REPO_ROOT / "formal" / "verify.sh").read_text(encoding="utf-8")
    assert '"$REPO_ROOT/scripts/handoff_lint.py"' in verify
    assert '"$REPO_ROOT/scripts/task.py" lint' in verify


# --- the per-line banner width cap (task.py::BANNER_MAX_WIDTH, lint check 12) -------------

def _banner_fails(tmp_path: Path, banner_lines: list[str]) -> list[str]:
    tasks = tmp_path / "tasks"
    tasks.mkdir(exist_ok=True)
    note = ("# HANDOFF\n\n## Banner\n\n" + "\n".join("> " + ln for ln in banner_lines) +
            "\n\n## Still owed\n\n- Nothing.\n")
    (tmp_path / "HANDOFF.md").write_bytes(note.encode("utf-8"))
    out: list[str] = []
    TM.check_banner(types.SimpleNamespace(dir=str(tasks)), out.append, {})
    return out


def test_an_overwide_banner_line_is_red_even_at_the_line_cap(tmp_path):
    """The evasion at banner scale: exactly BANNER_MAX_LINES lines, so the line cap is
    silent, and ONE line -- not the first -- one character too wide."""
    w = TM.BANNER_MAX_WIDTH
    lines = ["2026-10-07d -- headline"] + ["ok line %d" % n
                                          for n in range(TM.BANNER_MAX_LINES - 1)]
    lines[5] = "x" * (w + 1)
    fails = _banner_fails(tmp_path, lines)
    assert len(fails) == 1, fails
    assert ("1 banner line(s) wider than %d characters" % w) in fails[0], fails
    assert ("banner line 6 is %d" % (w + 1)) in fails[0], fails


def test_the_real_evading_line_is_red(tmp_path):
    """The widest banner line on 2026-10-07 was 3762 characters as written (sabotage
    lessons from seven sessions appended to one line). It must be red under the live cap; a cap raised
    past it would make this whole module a description of a check that no longer exists."""
    lines = ["2026-10-07d -- headline", "layered " * 470 + "xx"]
    assert len(lines[1]) == 3762
    fails = _banner_fails(tmp_path, lines)
    assert len(fails) == 1 and "banner line 2 is 3762" in fails[0], fails


def test_the_byte_cap_binds_before_a_full_banner_of_full_width_lines():
    """The two caps are designed as a pair (`task.py::BANNER_MAX_WIDTH`'s comment): a banner
    of BANNER_MAX_LINES lines at full width would overflow MAX_BYTES on its own, so the
    file cap binds first and the width cap only stops one line from swallowing it."""
    assert TM.BANNER_MAX_LINES * TM.BANNER_MAX_WIDTH > HL.MAX_BYTES["HANDOFF.md"]


def test_a_banner_line_exactly_at_the_width_cap_is_legal(tmp_path):
    """Measured as `board` prints it: the `> ` blockquote marker is not counted, so a line
    of exactly BANNER_MAX_WIDTH characters after the marker passes. Pinned so the test
    above cannot be satisfied by a check that refuses every banner."""
    lines = ["2026-10-07d -- headline", "y" * TM.BANNER_MAX_WIDTH]
    assert _banner_fails(tmp_path, lines) == []


def test_the_width_cap_rides_lint_check_12():
    """Check 12 is LINT_CHECKS[11] (checks are cited by number), and lint is `verify.sh`
    lean step 4g (asserted above)."""
    assert TM.LINT_CHECKS[11] is TM.check_banner
    assert TM.BANNER_MAX_WIDTH > 0
