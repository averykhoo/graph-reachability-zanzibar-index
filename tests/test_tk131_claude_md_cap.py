"""`TK131` (2026-10-07d): `CLAUDE.md` has a byte ceiling, so accretion goes red within days.

`CLAUDE.md` is auto-loaded into every session, so every byte costs every session. On
2026-10-07 it was uncapped at 45483 B / 558 lines on disk (44925 B as LF text) and growing
about 4 KB a week (`docs/context-audit-2026-10-07.md` item 4), mostly as case histories and
"this bullet said X until <date>" provenance inside rules. It was pruned to 31017 B LF on
2026-10-07d and capped at `scripts/handoff_lint.py::MAX_BYTES['CLAUDE.md']`, checked by
`check_ceilings` (`CHECKS[0]`, `verify.sh` lean step 4f). The per-row half of the model
(audio-workspace `claudeMdShape.test.ts`) is not ported, because `CLAUDE.md` has no table;
the reason is in the constant's comment.

Every red below was watched go red before it was believed (`docs/sabotage-procedure.md`).
The real pre-prune file, fed to the shipped `check_ceilings` on 2026-10-07d, is red::

    CLAUDE.md is 44925 bytes, ceiling 32500 (MAX_BYTES; LF line endings). It is auto-loaded
    into every session, so every byte costs every session. Do not raise the ceiling ...

MUTATION SWEEP, 2026-10-07d: six mutants of the check plus three controls, each in a temp
mirror root (the shipped files untouched; probe `.scratch/hk-2026-10-07d/tk131_sweep.py`,
gitignored, so the table is kept HERE). Every mutant reddened the test named for it in
advance. `M0`/`M0b` are the attribution controls: raising the cap to the pre-prune size, or
by enough slack to absorb one re-added case history, is red. `M0c` is the documented blind
spot: the boundary tests derive from the live constant, so a small LOWERING is invisible,
by design. `M1` reds as a collection error (`CAP` is read at import), which the gate's
pytest exit-code assertion counts as red. Literal output (`run | failed tests`)::

    NONE: 6 passed in 0.57s | -
    M0 control: cap 32500 -> 45000: 2 failed, 4 passed in 0.58s | test_re_adding_the_pruned_case_history_to_the_live_file_is_red, test_the_pre_prune_size_is_red
    M0b control: cap 32500 -> 33000: 1 failed, 5 passed in 0.53s | test_re_adding_the_pruned_case_history_to_the_live_file_is_red
    M0c control (expected NO red): cap 32500 -> 32400: 6 passed in 0.57s | -
    M1 CLAUDE.md dropped from MAX_BYTES: 1 error in 0.34s | -
    M2 check_ceilings dropped from CHECKS: 1 failed, 5 passed in 0.75s | test_the_cap_rides_the_gated_check
    M3 raw on-disk bytes (CRLF counted): 1 failed, 5 passed in 0.81s | test_the_cap_is_exact_at_its_boundary_and_blind_to_crlf
    M4 byte cap off-by-one (>=): 1 failed, 5 passed in 0.70s | test_the_cap_is_exact_at_its_boundary_and_blind_to_crlf
    M5 CLAUDE.md red carries the HANDOFF remedy: 1 failed, 5 passed in 0.83s | test_the_red_names_the_claude_md_remedy_not_the_banner_one
    M6 byte loop skips a missing file: 1 failed, 5 passed in 0.84s | test_a_missing_claude_md_is_itself_red

ADDENDUM 2026-10-07d (fix-hk review). The table above is as-of-then: the test it calls
`test_re_adding_the_pruned_case_history_to_the_live_file_is_red` read the LIVE `CLAUDE.md`,
which the pytest tiles' `t2c` tree id does not cover, so it was replaced by
`handoff_lint.py::MAX_BYTES_SLACK` (checked in `lean`) plus the two temp-root tests below,
and `formal/HANDOFF.md`'s caps were ratcheted to the TK131 prune. Second sweep, this module
plus `test_tk130_handoff_size_caps.py` against a temp copy of `scripts/` (probe
`.scratch/hk-2026-10-07d/fixhk_sweep2.py`), literal output::

    NONE: rc=0 | 18 passed in 1.98s | -
    S1 slack branch never fires: rc=1 | 1 failed, 17 passed in 1.95s | test_a_prune_left_unratcheted_is_red_and_names_the_new_cap
    S2 slack off-by-one (>=): rc=1 | 1 failed, 17 passed in 1.86s | test_re_adding_the_pruned_case_history_at_maximal_legal_headroom_is_red
    S3 bold-caps under-budget branch dropped: rc=1 | 1 failed, 17 passed in 1.96s | test_the_bold_caps_budget_is_a_ratchet_in_both_directions
    S4 formal dropped from MAX_BYTES: rc=1 | 2 failed, 16 passed in 1.85s | test_the_red_names_the_claude_md_remedy_not_the_banner_one, test_formal_handoff_has_a_byte_cap_with_its_own_remedy
    S5 slack 1900 -> 2000 (>= one case history): rc=1 | 1 failed, 17 passed in 1.90s | test_re_adding_the_pruned_case_history_at_maximal_legal_headroom_is_red
    S6 remedy lookup hardwired to CLAUDE.md: rc=1 | 1 failed, 17 passed in 1.58s | test_formal_handoff_has_a_byte_cap_with_its_own_remedy

S6's first draft mutated one fragment of the formal remedy string and SURVIVED, because the
"formal/history/" the test asserts sits in a later fragment; the mutant, not the test, was
too weak, so it was replaced by the lookup mutant above. Still a blind spot, by the same
design as M0c: the VALUES `MAX_LINES['formal/HANDOFF.md']` = 265 and
`MAX_BYTES['formal/HANDOFF.md']` = 21600 are held only by their provenance comments (a slack
ratchet like CLAUDE.md's was not added for them).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        "tk131_" + name, str(REPO_ROOT / "scripts" / (name + ".py")))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HL = _load("handoff_lint")
CAP = HL.MAX_BYTES["CLAUDE.md"]

# The narrowest PLAUSIBLE regrowth: the exact case history the 2026-10-07d prune removed from
# footgun 1 (three dated variants of the exit-code lie, 1970 B as LF text). A session
# re-adding one such paragraph is precisely the accretion the cap exists to stop.
REGROWN_CASE_HISTORY = """\
    ⚠ **2026-09-16b generalises it past pipes: it is ANY trailing command in the chain,
    and `rc=$?` does not save you if something runs after it.** A backgrounded
    `pytest > "$L" 2>&1; rc=$?; echo "rc=$rc"; grep -E ... "$L"` was reported by the harness
    as **"exit code 0"** while the log ended `1 failed, 29 passed` — the task's status was
    GREP's (it matched nothing it considered an error), not pytest's. The captured `rc` was
    correct and never looked at. So: **put the verdict where you will READ it, not only
    where you compute it** — `echo` the branch (`[ $rc -eq 0 ] || echo RED`) rather than
    trusting any exit status reported by a wrapper, and read the log's last line every time.
    This is the fourth distinct mechanism for the same lie.
    The 2026-09-08b variant runs the OTHER way — `EXIT=0` under a log ending `25 failed`
    — because looping phases in one command lets the harness kill the shell while its
    `pytest` child survives, and the orphan then writes the next phase's log. **One phase
    per command**; on any exit-code/log disagreement, check for a stray interpreter and
    re-run alone to a fresh log before believing either.
    ⚠ **The 2026-09-10 variant needs neither a pipe nor an orphan: two runs and one
    filename.** `EXIT=0` under a log ending `60 failed`, with no stray interpreter and no
    loop — two overlapping runs both redirecting into the FIXED `/tmp/p.log` this file
    used to prescribe, so the caller got the passing run's honest `rc` beside the failing
    run's tail. **A fixed log path is a shared resource; use `mktemp`.** `verify.sh` now
    takes an exclusive run lock (`scripts/gate_lock.py`) and a second concurrent run
    refuses nonzero in under a second, so this cannot recur silently — but the same
    reasoning applies to any command you run twice. Note what this one cost: it was filed
    as a hole in `verify.sh`'s exit-code guard, and the guard was fine.
"""

# The real pre-prune size, LF text, measured 2026-10-07 (45483 B on disk minus 558 CRs).
PRE_PRUNE_LF_BYTES = 44925


def _ceilings(root: Path) -> list[str]:
    out: list[str] = []
    old = HL.REPO
    HL.REPO = str(root)
    try:
        HL.check_ceilings(out.append)
    finally:
        HL.REPO = old
    return out


def _seed(root: Path, claude: bytes | None) -> None:
    """A temp root holding every file `check_ceilings` reads, the other two well inside."""
    (root / "formal").mkdir(parents=True, exist_ok=True)
    (root / "formal" / "HANDOFF.md").write_bytes(b"# formal\n")
    (root / "HANDOFF.md").write_bytes(b"# HANDOFF\n")
    if claude is not None:
        (root / "CLAUDE.md").write_bytes(claude)
    elif (root / "CLAUDE.md").exists():
        (root / "CLAUDE.md").unlink()


def _sized(n: int) -> str:
    """LF text of exactly ``n`` UTF-8 bytes, shaped like markdown bullets."""
    head = "# CLAUDE.md\n\n## Rules\n"
    line = "- " + "r" * 97 + "\n"
    text = head + line * ((n - len(head)) // len(line))
    return text + "x" * (n - len(text.encode("utf-8")))


def test_re_adding_the_pruned_case_history_at_maximal_legal_headroom_is_red(tmp_path):
    """A `CLAUDE.md` with the MOST headroom the slack ratchet allows, plus the one case history
    the prune removed, is over the cap -- so no legal state lets that paragraph back in green.

    ⚠ CORRECTION 2026-10-07d (fix-hk): this test used to read the LIVE `CLAUDE.md` and assert
    the headroom there. That was a gate hole: the pytest tiles key off `t2c`, which excludes
    `CLAUDE.md` (`scripts/gate_status.py::CODE_SCOPE_MD_KEEP`), so a CLAUDE.md-only prune
    could turn it red while `gate_status.py` still reported the tiles COVERED. The live half
    is now `handoff_lint.py::MAX_BYTES_SLACK`, checked by `check_ceilings` in `lean` (keyed
    off `t2a`); this test pins the mechanism on a temp root, from the constants alone."""
    slack = HL.MAX_BYTES_SLACK["CLAUDE.md"]
    regrowth = len(REGROWN_CASE_HISTORY.encode("utf-8"))
    loosest = _sized(CAP - slack)
    _seed(tmp_path, loosest.encode("utf-8"))
    assert _ceilings(tmp_path) == [], "exactly at the slack is legal"
    _seed(tmp_path, (loosest + REGROWN_CASE_HISTORY).encode("utf-8"))
    fails = _ceilings(tmp_path)
    assert len(fails) == 1 and fails[0].startswith(
        "CLAUDE.md is %d bytes, ceiling %d" % (CAP - slack + regrowth, CAP)), fails


def test_a_prune_left_unratcheted_is_red_and_names_the_new_cap(tmp_path):
    """One byte more headroom than the slack is red in `lean`, naming the value to lower
    the cap to. This is the live headroom pin, moved out of the pytest tiles (see above).
    Literal observed output on the live tree with the cap raised to the pre-fix M0b value
    33000 (2026-10-07d, in memory)::

        CLAUDE.md is 31017 bytes against a ceiling of 33000: 1983 B of headroom, more than
        its slack 1900 (MAX_BYTES_SLACK). ... lower MAX_BYTES['CLAUDE.md'] to 32917 or less
    """
    slack = HL.MAX_BYTES_SLACK["CLAUDE.md"]
    _seed(tmp_path, _sized(CAP - slack - 1).encode("utf-8"))
    fails = _ceilings(tmp_path)
    assert len(fails) == 1, fails
    assert "%d B of headroom, more than its slack %d" % (slack + 1, slack) in fails[0], fails
    assert "lower MAX_BYTES['CLAUDE.md'] to %d" % (CAP - 1) in fails[0], fails


def test_the_pre_prune_size_is_red(tmp_path):
    """Attribution control: the file as it stood on 2026-10-07, uncapped, is over the cap."""
    _seed(tmp_path, _sized(PRE_PRUNE_LF_BYTES).encode("utf-8"))
    fails = _ceilings(tmp_path)
    assert len(fails) == 1 and fails[0].startswith(
        "CLAUDE.md is %d bytes, ceiling %d" % (PRE_PRUNE_LF_BYTES, CAP)), fails


def test_the_cap_is_exact_at_its_boundary_and_blind_to_crlf(tmp_path):
    """At the cap is legal, one byte over is red, and a CRLF checkout (Windows,
    `core.autocrlf`) of an at-cap file measures as its LF text, the same as Linux CI."""
    at_cap = _sized(CAP)
    assert len(at_cap.encode("utf-8")) == CAP
    _seed(tmp_path, at_cap.encode("utf-8"))
    assert _ceilings(tmp_path) == []

    _seed(tmp_path, (at_cap + "x").encode("utf-8"))
    fails = _ceilings(tmp_path)
    assert len(fails) == 1 and ("CLAUDE.md is %d bytes, ceiling %d" % (CAP + 1, CAP)) in fails[0]

    crlf = at_cap.replace("\n", "\r\n").encode("utf-8")
    assert len(crlf) > CAP
    _seed(tmp_path, crlf)
    assert _ceilings(tmp_path) == [], "a CRLF checkout must measure as its LF text"


def test_the_red_names_the_claude_md_remedy_not_the_banner_one(tmp_path):
    """The two capped files are fixed differently; a CLAUDE.md red that told the reader to
    delete stale banner layers would send them to the wrong file."""
    _seed(tmp_path, _sized(CAP + 1).encode("utf-8"))
    (fail,) = _ceilings(tmp_path)
    assert "every byte costs every session" in fail, fail
    assert "banner" not in fail, fail
    assert set(HL.BYTE_CAP_REMEDY) == set(HL.MAX_BYTES), "every byte cap needs its remedy text"


def test_a_missing_claude_md_is_itself_red(tmp_path):
    """A ceiling on a file that does not exist guards nothing."""
    _seed(tmp_path, None)
    assert _ceilings(tmp_path) == ["MISSING: CLAUDE.md (a ceiling on a file that does not "
                                   "exist guards nothing)"]


def test_the_cap_rides_the_gated_check():
    """`check_ceilings` is `CHECKS[0]`, and `verify.sh` lean step 4f runs the script whose
    `main` walks CHECKS; a cap held in a dict nobody iterates would pass by reading nothing."""
    assert "CLAUDE.md" in HL.MAX_BYTES
    assert HL.CHECKS[0] is HL.check_ceilings
    verify = (REPO_ROOT / "formal" / "verify.sh").read_text(encoding="utf-8")
    assert '"$REPO_ROOT/scripts/handoff_lint.py"' in verify


# --- formal/HANDOFF.md, the other half of TK131 (fix-hk, 2026-10-07d) ---------------------
# TK131 pruned formal/HANDOFF.md 520 -> 241 lines / 19636 B LF and left its caps where they
# were: MAX_LINES 520, MAX_BOLDCAPS 6 (1 offender left), no byte cap. Fixed by landed + 10%
# (265 lines, 21600 B) and an exact bold-caps budget of 1, and the bold-caps ratchet is now
# red in BOTH directions. Live sabotage, in memory against the real tree (2026-10-07d):
#   MAX_LINES formal 241 -> clean; 240 -> "formal/HANDOFF.md is 241 lines, ceiling 240."
#   MAX_BYTES formal 19636 -> clean; 19635 -> "formal/HANDOFF.md is 19636 bytes, ceiling 19635"
#   MAX_BOLDCAPS formal 1 -> 0: "1 line(s) with bold ALL-CAPS ..., budget 0 (lines [52])"
#   MAX_BOLDCAPS formal 6 (the pre-fix value): "only 1 line(s) with bold ALL-CAPS outside a
#     trap paragraph, but the budget is 6. ... lower MAX_BOLDCAPS['formal/HANDOFF.md'] to 1"
FORMAL = "formal/HANDOFF.md"


def _bold_caps(root: Path) -> list[str]:
    out: list[str] = []
    old = HL.REPO
    HL.REPO = str(root)
    try:
        HL.check_bold_caps(out.append)
    finally:
        HL.REPO = old
    return out


def test_formal_handoff_has_a_byte_cap_with_its_own_remedy(tmp_path):
    """The line-length evasion TK130 closed for HANDOFF.md, at formal/HANDOFF.md: a file
    inside its line cap but over its byte cap is red, naming the formal remedy."""
    cap = HL.MAX_BYTES[FORMAL]
    _seed(tmp_path, _sized(CAP).encode("utf-8"))
    width = cap // (HL.MAX_LINES[FORMAL] // 2) + 1          # half the lines, too wide
    text = ("w" * (width - 1) + "\n") * (HL.MAX_LINES[FORMAL] // 2)
    assert len(text.split("\n")) <= HL.MAX_LINES[FORMAL] and len(text.encode()) > cap
    (tmp_path / FORMAL).write_bytes(text.encode("utf-8"))
    fails = _ceilings(tmp_path)
    assert len(fails) == 1 and fails[0].startswith("%s is %d bytes, ceiling %d"
                                                   % (FORMAL, len(text.encode()), cap)), fails
    assert "formal/history/" in fails[0], fails
    (tmp_path / FORMAL).write_bytes(text.encode("utf-8")[:cap])
    assert _ceilings(tmp_path) == [], "exactly at the cap is legal"


def test_the_bold_caps_budget_is_a_ratchet_in_both_directions(tmp_path):
    """Over budget is red (unchanged); UNDER budget is now red too, naming the value to
    lower it to -- the slip TK131 made. Exactly at budget is the only green."""
    budget = HL.MAX_BOLDCAPS[FORMAL]
    (tmp_path / "formal").mkdir()
    (tmp_path / "HANDOFF.md").write_bytes(b"# HANDOFF\n")
    shout = "**THIS IS SHOUTING** outside any trap paragraph.\n\n"
    for n, expect in ((budget, None), (budget + 1, "budget %d" % budget),
                      (budget - 1, "lower MAX_BOLDCAPS['%s'] to %d" % (FORMAL, budget - 1))):
        (tmp_path / FORMAL).write_text("# formal\n\n" + shout * max(n, 0), encoding="utf-8")
        fails = _bold_caps(tmp_path)
        if expect is None:
            assert fails == [], (n, fails)
        else:
            assert len(fails) == 1 and expect in fails[0], (n, fails)
