"""The gate's own status tool, pinned against the four ways it used to lie.

`scripts/gate_status.py` answers the question every session opens with -- "were
the ten phases run, and do they apply to the code in front of me?" -- and until
2026-08-17 it was the only assurance artifact in this repo with no tests at all.
Four defects shipped in it as a direct result, in a file whose own docstring
argues carefully about fail direction. That is the house failure mode
(`docs/sabotage-procedure.md`) applied to the instrument instead of the subject,
so the instrument now has a suite.

PROPERTY GUARDED, in one sentence: *a ledger row's tree id names the CONTENT the
phase actually ran against -- it survives a commit that changes nothing, it moves
when any covered file's content moves, it is never invented when the tree cannot
be read -- and a green verdict earned on a tree is not erased by a later run of
the same phase somewhere else.*

SABOTAGE RECORD (observed 2026-08-17 against the pre-fix
`scripts/gate_status.py`, on the real repo at HEAD `0cddd4a`). Each of the four
is a permanent test below -- durability rank 1, "make the sabotage a permanent
test" -- rather than a docstring warning:

  1. GS-1, the filed defect: committing changed the id although the content did
     not. Direction: fail-SAFE (it under-reports freshness).
         ledger row earned pre-commit  b53bfc9+1eabb8af
         `--tree-id` one commit later  0cddd4a+clean
     -> ten green phases read stale one second after `git commit`.
     Pinned by `test_tree_id_survives_a_commit_that_changes_no_content`.

  2. Untracked file CONTENTS were never read -- `git status --porcelain` names
     them. Direction: fail-OPEN.
         baseline                                 0cddd4a+clean
         untracked tests/zz_probe.py created      0cddd4a+0e72b085
         that file's contents rewritten           0cddd4a+0e72b085   <-- unchanged
     Pinned by `test_tree_id_moves_when_an_untracked_files_contents_change`.

  3. The same hole, wider: an untracked DIRECTORY collapses to a single
     `?? dir/` line, so whole subtrees were invisible. Direction: fail-OPEN.
         zz_probe_dir/one.py (new untracked dir)  0cddd4a+36649ed0
         zz_probe_dir/two.py added inside it      0cddd4a+36649ed0   <-- unchanged
     Pinned by `test_tree_id_moves_when_a_file_appears_inside_an_untracked_dir`.

  4. A failed `git status` was coalesced to `""`; untracked-only dirt leaves
     `git diff HEAD` empty too, so ONE failed command sufficed to report the
     CLEAN id. Direction: fail-OPEN.
         dirty (untracked only), git healthy      0cddd4a+1a7b0c67
         dirty (untracked only), `git status` down  0cddd4a+clean    <-- fabricated
     Pinned by `test_tree_id_refuses_to_guess_when_git_cannot_be_read` and
     `test_tree_id_cli_exits_nonzero_and_prints_no_id_on_failure`.

  5. And the reader's own: `report` kept the last row per PHASE, so re-running
     one phase on another tree discarded the green row earned on yours.
     Direction: fail-safe, but it is why the board carried a green gate as
     "will read stale". Observed against the real `.gate-runs/ledger.tsv`:
         PASSED rows recorded for b53bfc9+1eabb8af   ->  10 phases (all ten)
         gate_status.py concluded                    ->  lean: missing, COVERED: False
         keyed by (phase, tree) instead              ->  lean: PASSED,  COVERED: True
     Pinned by `test_a_green_verdict_is_not_erased_by_a_later_run_elsewhere`,
     with `test_a_phase_rerun_red_on_the_same_tree_is_not_green` as the negative
     control -- the keying must not buy freshness by forgetting failures.

CONTROLS. `test_tree_id_moves_when_a_tracked_file_is_edited` is the positive
control: the pre-fix scheme got this case RIGHT, so a "fix" that broke it would
be a regression the four sabotages above could not see.
`test_tree_id_ignores_gitignored_files` asserts the SCOPE the tool claims rather
than merely that it ran -- the `.gate-runs/` ledger lives in that blind spot on
purpose, and if it ever stopped doing so every row would be born stale.

SUITE-LEVEL SABOTAGE, the one that certifies the suite rather than the fix: the
pre-2026-08-17 `tree_id` and per-phase `green_phases` were reinstalled verbatim
into `scripts/gate_status.py` and this file was run against them. Observed:

    10 failed, 6 passed in 3.57s

and the six survivors are exactly the controls above plus the unchanged
`coverage` behaviour -- the red is ATTRIBUTABLE, not blanket, which is what
distinguishes "these tests pin the four defects" from "this file is broken".
Two of the failures, verbatim:

    assert {'conf-tile:1/1'} == {'conf-tile:1/1', 'lean'}
      Extra items in the right set: 'lean'        <- the (phase, tree) keying
    AssertionError: unknown
      assert {'lean'} == set()
      Extra items in the left set: 'lean'         <- `unknown` matched itself
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# `scripts/` has no __init__.py and pytest.ini sets no pythonpath, so there is no
# established idiom in this repo for importing a scripts module from a test. The
# gate happens to run pytest as `cd $REPO_ROOT && python -m pytest`, which puts
# the root on sys.path -- but a bare `pytest tests/` does not, and a test that
# only collects under the gate is exactly the kind of coverage that leaks. Hence
# the explicit insert.
sys.path.insert(0, str(REPO_ROOT))
from scripts import gate_status  # noqa: E402


# --------------------------------------------------------------------------- #
# temp-repo helpers
# --------------------------------------------------------------------------- #
def _git(repo: Path, *args: str) -> None:
    """Run git in `repo`, failing the test loudly on nonzero.

    `commit.gpgsign=false` is set per-invocation so a developer's global signing
    config cannot make these fixtures block on a passphrase prompt. That is test
    hermeticity, not a project-level signing bypass.
    """
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false",
         "-c", "user.email=gate@test", "-c", "user.name=gate test", *args],
        capture_output=True, text=True, timeout=120,
    )
    assert done.returncode == 0, (
        f"git {' '.join(args)} failed ({done.returncode}):\n{done.stdout}\n{done.stderr}"
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A real git repo with one committed file, clean at HEAD."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "kept.txt").write_text("original\n", encoding="utf-8")
    _git(root, "add", "kept.txt")
    _git(root, "commit", "-q", "-m", "initial")
    return root


def _id(repo: Path) -> str:
    return gate_status.tree_id(repo)


# --------------------------------------------------------------------------- #
# 1. GS-1 -- the id must not depend on HEAD
# --------------------------------------------------------------------------- #
def test_tree_id_survives_a_commit_that_changes_no_content(repo: Path) -> None:
    """Staging and committing identical content must not move the id (GS-1).

    Pre-fix the id was `<short HEAD>+<sha1 of porcelain+diff>` for a dirty tree
    and `<short HEAD>+clean` for a clean one, so BOTH halves changed at the
    commit: ten phases earned at `b53bfc9+1eabb8af` read stale at `0cddd4a+clean`
    one second later, with not one byte of tracked content different.
    """
    (repo / "kept.txt").write_text("edited\n", encoding="utf-8")
    (repo / "fresh.txt").write_text("new file\n", encoding="utf-8")
    dirty = _id(repo)

    _git(repo, "add", "-A")
    assert _id(repo) == dirty, "staging changed the id although content did not"

    _git(repo, "commit", "-q", "-m", "same content, now committed")
    assert _id(repo) == dirty, "committing changed the id although content did not"


def test_two_repos_with_identical_content_but_different_history_agree(
    tmp_path: Path,
) -> None:
    """The id is a content address, so unrelated history must not separate them.

    The complement of the test above: it is not enough that the id survives ONE
    commit, it must not encode history at all -- otherwise `git commit --amend`,
    a rebase, or a re-clone would each resurrect GS-1 in a new costume.
    """
    ids = []
    for name, messages in (("a", ["one"]), ("b", ["one", "two", "three"])):
        root = tmp_path / name
        root.mkdir()
        _git(root, "init", "-q")
        (root / "kept.txt").write_text("original\n", encoding="utf-8")
        _git(root, "add", "kept.txt")
        for msg in messages:                      # different number of commits
            _git(root, "commit", "-q", "--allow-empty", "-m", msg)
        ids.append(_id(root))
    assert ids[0] == ids[1], "identical content got different ids from history alone"


# --------------------------------------------------------------------------- #
# 2 + 3. the untracked blind spots -- both were fail-OPEN
# --------------------------------------------------------------------------- #
def test_tree_id_moves_when_an_untracked_files_contents_change(repo: Path) -> None:
    """Editing an untracked file must move the id.

    Pre-fix it did not: `git status --porcelain` NAMES untracked files but never
    reads them, so `0cddd4a+0e72b085` was returned both before and after
    rewriting the probe file's contents. A session that wrote a new test file,
    ran the ten phases green, then edited it before `git add` kept a full green
    verdict for code the gate had never seen.
    """
    (repo / "untracked.py").write_text("print(1)\n", encoding="utf-8")
    before = _id(repo)

    (repo / "untracked.py").write_text("print(2)  # changed\n", encoding="utf-8")
    assert _id(repo) != before, "untracked file contents are still invisible to the id"


def test_tree_id_moves_when_a_file_appears_inside_an_untracked_dir(repo: Path) -> None:
    """A new file inside an already-untracked directory must move the id.

    The wider form of the same hole: porcelain collapses an untracked directory
    to one `?? dir/` line, so `zz_probe_dir/two.py` left the id at
    `0cddd4a+36649ed0`, exactly where `zz_probe_dir/one.py` had put it. Whole
    subtrees could appear with no effect on the recorded tree.
    """
    (repo / "probe_dir").mkdir()
    (repo / "probe_dir" / "one.py").write_text("a\n", encoding="utf-8")
    before = _id(repo)

    (repo / "probe_dir" / "two.py").write_text("b\n", encoding="utf-8")
    assert _id(repo) != before, "an untracked subtree is still summarised by its name"


# --------------------------------------------------------------------------- #
# 4. it must never invent an id
# --------------------------------------------------------------------------- #
def test_tree_id_refuses_to_guess_when_git_cannot_be_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A git failure must raise, never return a plausible id.

    Pre-fix, `_git` coalesced any failure to `""`; with untracked-only dirt
    `git diff HEAD` is empty anyway, so a single failed `git status` produced
    `0cddd4a+clean` -- byte-identical to the id a genuinely clean tree carries,
    and therefore a match against a clean tree's green rows. One failed command
    was the whole exploit.
    """
    not_a_repo = tmp_path / "bare"
    not_a_repo.mkdir()
    (not_a_repo / "kept.txt").write_text("content\n", encoding="utf-8")
    # Stop git discovering an enclosing repo if the temp root ever sits inside
    # one -- otherwise this test would quietly assert nothing.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))

    with pytest.raises(gate_status.TreeIdError):
        gate_status.tree_id(not_a_repo)


def test_tree_id_refuses_to_guess_when_git_cannot_be_executed(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other failure branch: git present but unrunnable, e.g. a broken PATH."""
    def _boom(*args, **kwargs):
        raise OSError("simulated: git could not be spawned")

    monkeypatch.setattr(gate_status.subprocess, "run", _boom)
    with pytest.raises(gate_status.TreeIdError):
        gate_status.tree_id(repo)


def test_tree_id_cli_exits_nonzero_and_prints_no_id_on_failure(tmp_path: Path) -> None:
    """`--tree-id` must fail visibly, because verify.sh consumes its stdout.

    The recorder does `out=$(... --tree-id) || ...` and writes `out` into the
    ledger's tree column. If a failure ever printed a fallback id on stdout, that
    id would be recorded as fact. So: nonzero, and nothing id-shaped on stdout.
    """
    # The script derives its repo root from __file__, so it is copied into the
    # temp tree to make that root a NON-repo. Running the real one from a foreign
    # cwd would still identify this repo -- correctly -- and assert nothing.
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    copy = scripts_dir / "gate_status.py"
    copy.write_bytes((REPO_ROOT / "scripts" / "gate_status.py").read_bytes())

    env = dict(os.environ)
    env["GIT_CEILING_DIRECTORIES"] = str(tmp_path)
    done = subprocess.run(
        [PY, str(copy), "--tree-id"],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=120, env=env,
    )

    assert done.returncode != 0, (
        f"--tree-id exited 0 on a non-repo and printed {done.stdout.strip()!r}"
    )
    assert not done.stdout.strip(), "a failing --tree-id printed something to stdout"
    assert "cannot identify" in done.stderr, done.stderr


# --------------------------------------------------------------------------- #
# controls: the cases the OLD scheme got right, and the scope it claims
# --------------------------------------------------------------------------- #
def test_tree_id_moves_when_a_tracked_file_is_edited(repo: Path) -> None:
    """Positive control. The pre-fix scheme handled this correctly.

    Without it, a "fix" that returned a constant would satisfy every sabotage
    above -- an id that never changes is trivially invariant under commit.
    """
    before = _id(repo)
    (repo / "kept.txt").write_text("edited\n", encoding="utf-8")
    assert _id(repo) != before


def test_tree_id_moves_when_a_tracked_file_is_deleted(repo: Path) -> None:
    """Deletion is a content change; the `absent` marker is what records it.

    Skipping unreadable index entries instead would make `rm tests/test_matrix.py`
    invisible to the gate -- a deletion that removes coverage is precisely the
    edit this repo's `-ge` floors exist to catch.
    """
    before = _id(repo)
    (repo / "kept.txt").unlink()
    assert _id(repo) != before


def test_tree_id_ignores_gitignored_files(repo: Path) -> None:
    """The claimed blind spot, asserted rather than assumed.

    `.gate-runs/` lives here on purpose: the ledger is written DURING a run, so
    if it were inside the hash each row would change the id the next row records
    and every row would be born stale. This test is what keeps that property from
    silently regressing -- and it is also the honest statement of the limitation,
    since `formal/lean/.lake/**` is ignored too and a matching id therefore does
    not mean the same Lean build.
    """
    (repo / ".gitignore").write_text(".gate-runs/\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-q", "-m", "ignore the ledger")
    before = _id(repo)

    (repo / ".gate-runs").mkdir()
    (repo / ".gate-runs" / "ledger.tsv").write_text("a row\n", encoding="utf-8")
    assert _id(repo) == before, "the run ledger is inside its own tree id"

    (repo / ".gate-runs" / "ledger.tsv").write_text("a row\nanother\n", encoding="utf-8")
    assert _id(repo) == before, "appending to the ledger moved the tree id"


def test_tree_id_is_shaped_as_the_ledger_and_docs_describe(repo: Path) -> None:
    """`t1:<12 hex>` -- versioned, so a legacy row can never match a new id."""
    got = _id(repo)
    algo, _, digest = got.partition(":")
    assert algo == gate_status.TREE_ID_ALGO
    assert len(digest) == 12 and all(c in "0123456789abcdef" for c in digest)
    assert not gate_status.LEGACY_TREE_RE.match(got)


# --------------------------------------------------------------------------- #
# 5. the reader: verdicts are keyed by (phase, tree)
# --------------------------------------------------------------------------- #
def _row(phase: str, status: str, tree: str) -> dict:
    return {"started": "2026-08-17T10:00:00+0800", "dur_s": "10", "phase": phase,
            "status": status, "tree": tree, "facts": "rc=0", "log": f"{phase}.log"}


def test_a_green_verdict_is_not_erased_by_a_later_run_elsewhere() -> None:
    """Re-running a phase on another tree must not discard your tree's verdict.

    Observed pre-fix on the real ledger: ten PASSED rows existed for
    `b53bfc9+1eabb8af`, `lean` had since been re-run twice on other trees, and
    the report said `lean: missing` / `VERDICT: NOT covered` for a tree the
    ledger recorded as fully green.
    """
    rows = [
        _row("lean", "PASSED", "t1:aaaaaaaaaaaa"),
        _row("conf-tile:1/1", "PASSED", "t1:aaaaaaaaaaaa"),
        _row("lean", "PASSED", "t1:bbbbbbbbbbbb"),   # later, different tree
    ]
    green = gate_status.green_phases(rows, "t1:aaaaaaaaaaaa")
    assert green == {"lean", "conf-tile:1/1"}


def test_a_phase_rerun_red_on_the_same_tree_is_not_green() -> None:
    """Negative control: the keying must not buy freshness by forgetting reds.

    The whole risk of keying by (phase, tree) is that it could remember a PASSED
    row forever. It must not: on a given tree the LAST row still wins.
    """
    rows = [
        _row("lean", "PASSED", "t1:aaaaaaaaaaaa"),
        _row("lean", "FAILED", "t1:aaaaaaaaaaaa"),
    ]
    assert gate_status.green_phases(rows, "t1:aaaaaaaaaaaa") == set()


def test_rows_that_identify_no_tree_never_match() -> None:
    """`unknown` is not a tree. Two runs that both failed to identify themselves
    must not be treated as having agreed with each other.

    `verify.sh` writes `unknown` when `--tree-id` fails, so these rows exist in
    real ledgers; `nogit` is the pre-fix sentinel and may persist in old ones.
    """
    for opaque in ("unknown", "nogit", ""):
        rows = [_row("lean", "PASSED", opaque)]
        assert gate_status.green_phases(rows, opaque) == set(), opaque


def test_legacy_head_based_ids_cannot_match_a_content_address(repo: Path) -> None:
    """Old rows are history, not coverage -- and must not collide with a new id.

    Versioning the id (`t1:`) is what makes this structural instead of a lucky
    accident: every pre-2026-08-17 row is `<hex>+<something>`, which cannot be
    equal to any `t1:<hex>`.
    """
    rows = [_row("lean", "PASSED", "b53bfc9+1eabb8af"),
            _row("conf-tile:1/1", "PASSED", "0cddd4a+clean")]
    assert gate_status.green_phases(rows, _id(repo)) == set()
    for r in rows:
        assert gate_status.LEGACY_TREE_RE.match(r["tree"])


def test_coverage_still_refuses_tiles_at_mixed_K() -> None:
    """Unchanged behaviour, pinned because the keying change rewrote its caller.

    `conf-tile:1/5` + `conf-tile:2/8` provably leaves holes, so a mix must be
    refused rather than summed -- and now that verdicts can be assembled from
    rows written at different times, the chance of a mixed-K set reaching
    `coverage` is strictly higher than it was.
    """
    ok, _ = gate_status.coverage({"lean", "conf-tile:1/5", "conf-tile:2/8",
                                  "tests-tile:1/1"})
    assert not ok

    ok, notes = gate_status.coverage({"lean", "conf-tile:1/1", "tests-tile:1/1"})
    assert ok, notes
