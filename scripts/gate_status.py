#!/usr/bin/env python3
"""Read back the `verify.sh` run ledger: what ran, when, and on which tree.

`formal/verify.sh` appends one row per phase run to `.gate-runs/ledger.tsv` and
dumps that phase's full output beside it (both gitignored -- see below). This
script is the reader. It exists because the question every session opens with --
"were the nine tile phases run, and do they apply to the code in front of me?" --
had no answer in the repo at all: the gate printed to stdout and exited, and the
only surviving artifacts were pytest cache mtimes, which cannot name a phase,
cannot report a verdict, and (cache/lastfailed is CUMULATIVE, retaining entries
for tests that did not re-run) cannot even be dated honestly.

    python scripts/gate_status.py                 # the report
    python scripts/gate_status.py --require-green # exit 1 unless this tree is covered
    python scripts/gate_status.py --tree-id       # the tree id alone (verify.sh calls this)

WHY verify.sh CALLS THIS FOR THE TREE ID. The recorder and the reader must agree
on what "the same tree" means, byte for byte. Two implementations of that rule
would drift, and the failure would be silent in the worst direction: a status
tool reporting freshness that never existed. So there is one implementation --
`tree_id` below -- and the shell shells out to it.

WHAT THE TREE ID IS (since 2026-08-17, board row `GS-1`): a CONTENT ADDRESS,
`t2<scope>:<12 hex>`, over the contents of the tracked and untracked-non-ignored
files IN THAT PHASE'S INPUT SCOPE (`git ls-files --cached --others
--exclude-standard`, filtered). It says nothing about HEAD, and that is the
point -- the id is invariant under `git add` and `git commit`, so ten phases
earned just before a commit still read green just after it.

PER-PHASE SCOPES (added the same day, board row `GS-2`). One id over every file
was correct but expensive in one specific way: editing a MARKDOWN paragraph
invalidated nine green pytest tiles, which happened twice in a single session
(~50 min of gate time re-earning verdicts that could not have changed). A rule
whose cost is that visible is one sessions begin overriding from memory, which is
the habit this ledger exists to retire. So:

  * `t2a:` -- ALL inputs. `lean` uses it and must: step 4d resolves
    CORRESPONDENCE.md anchors, 4e scans prose globs (docs/*.md, formal/*.md,
    HANDOFF.md, CLAUDE.md), 4f lints both boards and the session ledger. A
    docs-only edit really can turn `lean` red.
  * `t2c:` -- CODE inputs: `all` minus `*.md` and `benchmarks/`. The pytest tiles
    use it.

  ⚠ AN EXCLUSION IS A FAIL-OPEN: an excluded input can no longer invalidate a
  cached green. The two exclusions were verified, not assumed -- no collected test
  reads markdown (only `doc_counts.py` does, from step 4e), no `.md` file exists
  under `tests/` or `formal/conformance/` at all, and nothing there imports
  `benchmarks`. Fixtures (*.fga), goldens (*.txt) and corpora (*.json) stay IN
  scope by construction, since only two extensions are named. See `_in_scope`.
  The scope tag is mixed into the digest AND the prefix, so a code-scoped id
  cannot match an all-scoped row even by coincidence, and the `t1` -> `t2` bump
  makes every pre-existing row structurally incapable of matching.

  ⚠ THE SCHEME IT REPLACED FAILED THREE WAYS -- ONCE SAFELY, TWICE NOT, and that
  asymmetry is why this is written down at length. Until 2026-08-17 the id was
  `<short HEAD>+clean`, else `<short HEAD>+<sha1 of (git status --porcelain,
  git diff HEAD)>`:
    * committing changed the id though the content did not, so a full green gate
      went stale one second after `git commit`. This was the filed defect, and it
      is the only one of the three that errs SAFELY (it under-reports freshness).
    * `--porcelain` NAMES untracked files but never reads them, so editing an
      untracked file left the id -- and its green rows -- unchanged. Worse, an
      untracked directory collapses to a single `?? dir/` line, so adding files
      inside one moved nothing at all. Fail-OPEN.
    * a failed `git status` was coalesced to an empty string, so a tree whose
      dirt was untracked-only (in which case `git diff HEAD` is empty anyway)
      reported the CLEAN id and matched a clean tree's green rows. One failed
      command was enough. Fail-OPEN.
  All three, plus the (phase, tree) keying below, are pinned by
  `tests/test_gate_status.py` with the observed pre-fix output in its docstrings.

WHAT IT STILL DOES NOT COVER: anything gitignored (notably `formal/lean/.lake/**`
-- a matching tree id does NOT mean the same Lean build), and the environment
(interpreter, `ZANZIBAR_TEST_DSN`, installed deps). Treat a green row as "this
phase passed against this source", never as a full provenance record.

IT FAILS LOUDLY, NEVER PLAUSIBLY. Any git or IO failure raises `TreeIdError`
instead of returning an id. `--tree-id` then exits nonzero, `verify.sh` records
that row's tree as `unknown`, and `report` refuses to match an `unknown` row
against anything -- so the run simply does not count, which is the safe
direction. A tool whose whole job is answering "is the gate green" must not be
able to invent a matching id: that is this repo's house failure mode
(`docs/sabotage-procedure.md`) turned on the instrument instead of the subject.

AND WHY `.gate-runs/` MUST STAY GITIGNORED. The id hashes every tracked AND
untracked-non-ignored file, so an un-ignored ledger would be inside its own
hash: writing a row would change the tree id that the next row records, and
every row would be born stale. (The pre-2026-08-17 scheme reached the same
conclusion by a different route -- `git status --porcelain` listed the directory.
The requirement is unchanged; only its mechanism is, and it now bites for a
merely-untracked ledger as well as a tracked one.) `report` warns loudly if it
sees `.gate-runs/` in `git status` output.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR_NAME = ".gate-runs"
LEDGER_NAME = "ledger.tsv"

# The recommended sequence from docs/gate-runbook.md §"Push gate". Shown in the
# report as the default expectation -- but coverage is NOT judged against this
# list, because K is a free parameter (a throttled box runs conf-tile:1/8 .. 8/8
# and that is just as complete). See `coverage`.
RECOMMENDED = ["lean"] + [f"conf-tile:{i}/5" for i in range(1, 6)] + [
    f"tests-tile:{i}/4" for i in range(1, 5)
]

TILE_RE = re.compile(r"^(conf|tests)-tile:(\d+)/(\d+)$")
COLUMNS = ("started", "dur_s", "phase", "status", "tree", "facts", "log")

TREE_ID_ALGO = "t2"

# --- Per-phase input SCOPES (2026-08-17, board row `GS-2`) ------------------------
# Until now one id covered every tracked file, so editing a MARKDOWN paragraph
# invalidated nine green pytest tiles. That is safe but wasteful, and the waste is
# not academic: it happened twice in one session (~50 min of gate time), and a rule
# whose cost is that visible is a rule sessions start overriding from memory -- the
# exact habit the ledger exists to retire.
#
# So a phase's id now covers only the inputs that phase can actually read:
#
#   all   -- every tracked/untracked-non-ignored file (the pre-existing behaviour).
#            `lean` MUST use this: step 4d resolves CORRESPONDENCE.md anchors, 4e
#            scans prose globs including docs/*.md, formal/*.md, HANDOFF.md and
#            CLAUDE.md, and 4f lints both board files and the session ledger. A
#            docs-only edit genuinely can turn `lean` red, and the gate-runbook
#            already warns about exactly that.
#   code  -- `all` minus *.md and benchmarks/. Used by the pytest tiles.
#
# ⚠ THE EXCLUSION IS A FAIL-OPEN SURFACE, so it was verified rather than assumed
# (2026-08-17). Excluding an input a tile really reads would cache a stale green --
# this repo's house failure mode. What was checked:
#   * NO collected test reads markdown. Every `.md` in tests/ and
#     formal/conformance/test_*.py is a docstring mention. The only real reader is
#     formal/conformance/doc_counts.py, which runs from `verify.sh` step 4e (an
#     `all`-scope phase), and no collected test imports it.
#   * NO `.md` file exists under tests/ or formal/conformance/ at all, so no
#     golden, fixture or corpus can be markdown. Goldens are .txt; conformance
#     carries one .json.
#   * NOTHING under tests/ or formal/conformance/ imports `benchmarks`; the
#     dependency runs the other way (benchmarks imports tests.wildcard_helpers).
# Re-verify all three before widening this list. Fixtures (*.fga), goldens (*.txt),
# snapshots and every .py stay IN scope by construction -- only two extensions are
# named, and the default for an unrecognised phase is `all`.
SCOPE_ALL = "all"
SCOPE_CODE = "code"

# Tag baked into the id string, so a code-scoped id is structurally incapable of
# matching an all-scoped one (`t2a:...` vs `t2c:...`). Same versioning discipline as
# the t1 -> t2 bump: make a stale match impossible rather than unlikely.
SCOPE_TAGS = {SCOPE_ALL: "a", SCOPE_CODE: "c"}

_TILE_PHASE_RE = re.compile(r"^(conf|tests)-tile:\d+/\d+$")


def phase_scope(phase: str) -> str:
    """Which input scope a phase's verdict is keyed to.

    Defaults to `all` for ANYTHING unrecognised. That direction is deliberate: an
    unknown phase over-invalidates (safe, wasteful) rather than under-invalidates
    (fast, wrong). A new phase must opt IN to a narrow scope, in this file, with
    the verification above redone for it.
    """
    return SCOPE_CODE if _TILE_PHASE_RE.match(phase or "") else SCOPE_ALL


def _in_scope(rel: bytes, scope: str) -> bool:
    if scope == SCOPE_ALL:
        return True
    p = rel.replace(b"\\", b"/")
    return not (p.endswith(b".md") or p.startswith(b"benchmarks/"))

# A tree column carrying one of these identifies nothing: `verify.sh` writes
# `unknown` when `--tree-id` fails, and `nogit` is a pre-2026-08-17 leftover.
# They must never match -- otherwise two runs that both FAILED to identify
# themselves would be treated as having agreed.
OPAQUE_TREES = frozenset({"", "unknown", "nogit"})

# What `report` prints when it cannot identify the tree at all. Deliberately not
# a plausible id and deliberately not `unknown`: it must not collide with any
# value `verify.sh` can write into the ledger.
UNRESOLVED = "<unresolved>"

# Ids written by the pre-2026-08-17 HEAD-based scheme (`abc1234+clean`,
# `abc1234+1eabb8af`). Structurally distinct from `t1:...`, so they cannot match
# by accident -- the report names them out loud instead of leaving a session to
# wonder why every row went stale at once.
LEGACY_TREE_RE = re.compile(r"^[0-9a-f]{4,}\+")


class TreeIdError(RuntimeError):
    """The working tree could not be identified. Never fall back to a guess."""


# --------------------------------------------------------------------------- #
# tree identity
# --------------------------------------------------------------------------- #
def _git_bytes(repo: Path, *args: str) -> bytes:
    """Run git and return stdout as bytes, or raise. It never returns a guess.

    Bytes, not text: `ls-files -z` emits raw path bytes, and decoding them
    through the platform's default codec is a way to silently mangle a filename
    -- i.e. to change what the id covers without saying so.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise TreeIdError(f"`git {' '.join(args)}` could not run: {exc}") from exc
    if out.returncode != 0:
        tail = out.stderr.decode("utf-8", "replace").strip().splitlines()
        raise TreeIdError(
            f"`git {' '.join(args)}` exited {out.returncode}"
            + (f": {tail[-1]}" if tail else "")
        )
    return out.stdout


def _tree_files(repo: Path) -> list[bytes]:
    """Every path the id covers: tracked plus untracked, minus gitignored."""
    raw = _git_bytes(repo, "ls-files", "-z", "--cached", "--others",
                     "--exclude-standard")
    # Sorted and de-duplicated, so the digest is a function of the SET of paths
    # rather than of git's output order -- and so a path listed once per stage
    # during an unmerged state still counts once.
    return sorted({p for p in raw.split(b"\0") if p})


def _file_fingerprint(repo: Path, rel: bytes) -> bytes:
    path = repo / os.fsdecode(rel)
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        # In the index, absent from the worktree. A deletion is a content change
        # like any other, so it gets its own marker rather than being skipped --
        # skipping it would make `rm tests/test_matrix.py` invisible to the id.
        return b"absent"
    except OSError as exc:
        # Unreadable is NOT "empty" and NOT "skip": either would let the id agree
        # with a tree it never read. Refuse, and let the caller record `unknown`.
        raise TreeIdError(f"cannot read {os.fsdecode(rel)}: {exc}") from exc
    return b"f%d:%s" % (len(data), hashlib.sha256(data).hexdigest().encode())


def tree_id(repo: Path = REPO_ROOT, scope: str = SCOPE_ALL) -> str:
    """Identify the working tree by CONTENT, so a verdict survives a commit.

    Deliberately independent of HEAD: two checkouts whose files are identical are
    the same tree for gate purposes, whether that content is committed, staged or
    neither. See the module docstring for what this does not cover, and for the
    three failures of the HEAD-based scheme it replaced.

    ``scope`` selects WHICH files the id covers (see SCOPE_* above). The scope tag
    is mixed into both the digest and the printed prefix, so ids from different
    scopes can never collide or be mistaken for one another.
    """
    if scope not in SCOPE_TAGS:
        raise TreeIdError(f"unknown tree-id scope {scope!r}")
    h = hashlib.sha256()
    h.update(b"zanzibar-gate-tree-id/" + TREE_ID_ALGO.encode()
             + b"/" + scope.encode() + b"\0")
    covered = 0
    for rel in _tree_files(repo):
        if not _in_scope(rel, scope):
            continue
        covered += 1
        h.update(rel)
        h.update(b"\0")
        h.update(_file_fingerprint(repo, rel))
        h.update(b"\0")
    if not covered:
        # An id over nothing would match every other empty-scope id -- i.e. it
        # would certify anything. Refuse, exactly as an unreadable file does.
        raise TreeIdError(
            f"scope {scope!r} covered 0 files; an id over nothing certifies nothing")
    return f"{TREE_ID_ALGO}{SCOPE_TAGS[scope]}:{h.hexdigest()[:12]}"


def head_description(repo: Path = REPO_ROOT) -> str:
    """A human label for the report header ONLY -- never used to match a row.

    Kept strictly out of `tree_id`: the moment HEAD influences identity, `GS-1`
    is back.
    """
    try:
        head = _git_bytes(repo, "rev-parse", "--short", "HEAD").decode().strip()
    except TreeIdError:
        return "no git"
    try:
        dirty = bool(_git_bytes(repo, "status", "--porcelain").strip())
    except TreeIdError:
        return f"HEAD {head}, dirty-or-not unknown"
    return f"HEAD {head}, {'dirty' if dirty else 'clean'}"


def runs_dir() -> Path:
    return Path(os.environ.get("ZANZIBAR_GATE_RUNS_DIR", REPO_ROOT / RUNS_DIR_NAME))


# --------------------------------------------------------------------------- #
# ledger
# --------------------------------------------------------------------------- #
def read_ledger(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != len(COLUMNS):
            continue          # a torn append; skip rather than guess
        rows.append(dict(zip(COLUMNS, parts)))
    return rows


def green_phases(rows: list[dict], here: str) -> set[str]:
    """The phases whose LAST run **on `here`** passed.

    Keyed by (phase, tree), never by phase alone. Keying by phase alone loses a
    verdict that is sitting in the ledger: re-running one phase on a different
    tree -- a doc edit, a stash, a scratch file -- overwrote the entry and the
    green row earned on THIS tree stopped counting. Observed 2026-08-17 on the
    real ledger: ten PASSED rows existed for `b53bfc9+1eabb8af`, `lean` had since
    been re-run twice elsewhere, and the report said `lean: missing` / `VERDICT:
    NOT covered`. That direction is safe but it is still wrong, and a status tool
    that cries stale is a status tool that gets overridden from memory -- which
    is the habit the ledger exists to retire.

    Per (phase, tree) still keeps the property that matters: a phase that PASSED
    and was then re-run RED on this same tree has a FAILED last row for the pair,
    so it is not green.
    """
    ids = here if isinstance(here, dict) else {SCOPE_ALL: here, SCOPE_CODE: here}
    last_by_pair: dict[tuple[str, str], dict] = {}
    for r in rows:                       # appended in order; last wins per pair
        last_by_pair[(r["phase"], r["tree"])] = r
    return {
        phase for (phase, tree), r in last_by_pair.items()
        if tree not in OPAQUE_TREES and r["status"] == "PASSED"
        and tree == ids.get(phase_scope(phase))
    }


def _parse_when(started: str) -> datetime | None:
    try:
        return datetime.strptime(started, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


def _age(when: datetime | None) -> str:
    if when is None:
        return "?"
    secs = (datetime.now(timezone.utc) - when).total_seconds()
    if secs < 0:
        return "future?"
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{int(secs // size)}{unit} ago"
    return f"{int(secs)}s ago"


def coverage(green: set[str]) -> tuple[bool, list[str]]:
    """Is the gate covered on this tree by the set of PASSED phase names?

    A phase list covers a suite when SOME single K has all K of its tiles green.
    Deliberately not "the recommended ten": K is free and the tiles partition by
    collection index, so 1/8..8/8 is exactly as complete as 1/5..5/5. Equally
    deliberately, tiles at MIXED K do not compose -- conf-tile:1/5 plus
    conf-tile:2/8 provably leaves holes -- so a mix is refused, not summed.
    """
    notes, ok = [], True
    if "lean" in green:
        notes.append("lean: PASSED")
    else:
        notes.append("lean: missing")
        ok = False
    seen: dict[str, dict[int, set[int]]] = {"conf": {}, "tests": {}}
    for phase in green:
        m = TILE_RE.match(phase)
        if m:
            suite, i, k = m.group(1), int(m.group(2)), int(m.group(3))
            seen[suite].setdefault(k, set()).add(i)
    for suite, label in (("conf", "formal/conformance"), ("tests", "tests/")):
        complete = [k for k, got in seen[suite].items() if got >= set(range(1, k + 1))]
        if complete:
            notes.append(f"{label}: covered by K={min(complete)}")
        elif seen[suite]:
            partial = ", ".join(
                f"K={k}: {len(got)}/{k}" for k, got in sorted(seen[suite].items())
            )
            notes.append(f"{label}: INCOMPLETE ({partial})")
            ok = False
        else:
            notes.append(f"{label}: no green tile")
            ok = False
    return ok, notes


def report(require_green: bool) -> int:
    ids: dict[str, str] = {}
    here_err = None
    for scope in SCOPE_TAGS:
        try:
            ids[scope] = tree_id(scope=scope)
        except TreeIdError as exc:
            ids[scope], here_err = UNRESOLVED, str(exc)
    here = ids[SCOPE_ALL]
    d = runs_dir()
    rows = read_ledger(d / LEDGER_NAME)

    print(f"tree:   {ids[SCOPE_ALL]}   ({head_description()})")
    print(f"        {ids[SCOPE_CODE]}   (code scope: excludes *.md and benchmarks/; "
          f"used by the pytest tiles)")
    print(f"ledger: {d / LEDGER_NAME}  ({len(rows)} row(s))")

    if here_err is not None:
        print(f"\n⚠ CANNOT IDENTIFY THIS TREE: {here_err}")
        print("  No row can match, so nothing below counts as green here. This is")
        print("  deliberate -- inventing an id would be the one failure this tool")
        print("  must not have. Fix git/the filesystem and re-run.")

    try:
        porcelain = _git_bytes(REPO_ROOT, "status", "--porcelain").decode("utf-8", "replace")
    except TreeIdError:
        porcelain = ""
    if any(RUNS_DIR_NAME in ln for ln in porcelain.splitlines()):
        print(f"\n⚠ WARNING: {RUNS_DIR_NAME}/ shows up in `git status` -- it is NOT ignored here.")
        print("  The tree id hashes every tracked and untracked-non-ignored file, so the")
        print("  ledger would be inside its own hash: each row would change the id that")
        print("  the next row records, and every row would be born stale. Add it to")
        print("  .gitignore before trusting anything below.")

    if not rows:
        print("\nNo runs recorded yet. Run a phase: bash formal/verify.sh lean")
        return 1 if require_green else 0

    last_by_phase: dict[str, dict] = {}
    last_by_pair: dict[tuple[str, str], dict] = {}
    for r in rows:
        last_by_phase[r["phase"]] = r
        last_by_pair[(r["phase"], r["tree"])] = r
    green_here = green_phases(rows, ids)

    phases = RECOMMENDED + sorted(p for p in last_by_phase if p not in RECOMMENDED)
    width = max(len(p) for p in phases)
    print()
    print(f"{'phase'.ljust(width)}  {'last run':19}  {'age':9}  {'took':>6}  "
          f"{'status':12}  this tree  counts")
    for phase in phases:
        # Prefer this tree's own last row over the phase's last row anywhere:
        # with (phase, tree) keying the verdict can come from an earlier run, and
        # a table that showed a newer run on another tree would contradict the
        # VERDICT line below it.
        mine = ids.get(phase_scope(phase), here)
        r = last_by_pair.get((phase, mine)) or last_by_phase.get(phase)
        if r is None:
            print(f"{phase.ljust(width)}  {'-':19}  {'-':9}  {'-':>6}  {'never run':12}  -")
            continue
        when = _parse_when(r["started"])
        stamp = when.strftime("%Y-%m-%d %H:%M:%S") if when else r["started"][:19]
        same = "yes" if r["tree"] == mine else "NO"
        took = f"{r['dur_s']}s" if r["dur_s"].isdigit() else "?"
        print(f"{phase.ljust(width)}  {stamp:19}  {_age(when):9}  {took:>6}  "
              f"{r['status']:12}  {same:9}  {r['facts']}")

    stale = sorted(p for p, r in last_by_phase.items()
                   if r["status"] == "PASSED"
                   and r["tree"] != ids.get(phase_scope(p), here)
                   and p not in green_here)
    if stale:
        print(f"\n{len(stale)} phase(s) are green only on a DIFFERENT tree "
              f"(e.g. {last_by_phase[stale[0]]['tree']}) -- those verdicts do not apply here.")

    legacy = sorted({r["tree"] for r in rows if LEGACY_TREE_RE.match(r["tree"])})
    if legacy:
        print(f"\n{len(legacy)} tree id(s) here use the pre-2026-08-17 HEAD-based scheme "
              f"(e.g. {legacy[0]}).")
        print("  They can never match a content-addressed `t2a:`/`t2c:` id, so those rows")
        print("  are")
        print("  history, not coverage. Re-run the phases to earn green on this tree.")

    logged = {r["log"] for r in rows}
    orphans = sorted(p.name for p in d.glob("*.log") if p.name not in logged)
    if orphans:
        print(f"\nincomplete run(s) -- output log, no ledger row (killed mid-phase, or "
              f"still running):")
        for name in orphans[-10:]:
            print(f"  {name}")

    ok, notes = coverage(green_here)
    print("\non the current tree: " + "; ".join(notes))
    print("VERDICT: the ten-phase gate is " + ("COVERED" if ok else "NOT covered")
          + " on this tree." + ("" if ok else "  (a covered tree still needs a fuzz"
                                              " sweep for an algorithm change)"))
    return 0 if ok or not require_green else 1




def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tree-id", action="store_true",
                    help="print the working-tree id and exit (used by verify.sh)")
    ap.add_argument("--phase", default=None,
                    help="with --tree-id: print the id for THIS phase's input scope "
                         "(unrecognised phases get the widest scope, never a narrow one)")
    ap.add_argument("--require-green", action="store_true",
                    help="exit 1 unless every phase is PASSED on the current tree")
    args = ap.parse_args(argv)
    if args.tree_id:
        try:
            print(tree_id(scope=phase_scope(args.phase) if args.phase else SCOPE_ALL))
        except TreeIdError as exc:
            # Nonzero and silent on stdout: verify.sh records `unknown`, which
            # matches nothing. Never print a fallback id here.
            print(f"gate_status: cannot identify the working tree: {exc}", file=sys.stderr)
            return 1
        return 0
    return report(args.require_green)


if __name__ == "__main__":
    sys.exit(main())
