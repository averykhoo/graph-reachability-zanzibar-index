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

WHAT THE TREE ID DOES AND DOES NOT COVER. It is
`<short HEAD>+clean` for a clean tree, else `<short HEAD>+<sha1(porcelain,diff)>`.
So it sees tracked-file edits, staged or not, and the NAMES of untracked files.
It does NOT see: the CONTENTS of untracked files, anything gitignored (notably
`formal/lean/.lake/**` -- a matching tree id does not mean the same Lean build),
or the environment (interpreter, `ZANZIBAR_TEST_DSN`, installed deps). Treat a
green row as "this phase passed against this source", never as a full provenance
record.

AND WHY `.gate-runs/` MUST STAY GITIGNORED: the id is derived from
`git status --porcelain`, so a tracked ledger would change the tree id on every
run and every row would be born stale. `report` warns loudly if it sees that.
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


# --------------------------------------------------------------------------- #
# tree identity
# --------------------------------------------------------------------------- #
def _git(repo: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def tree_id(repo: Path = REPO_ROOT) -> str:
    """Identify the working tree well enough to say 'the run tested this code'."""
    head = _git(repo, "rev-parse", "--short", "HEAD")
    if head is None:
        return "nogit"
    porcelain = _git(repo, "status", "--porcelain") or ""
    diff = _git(repo, "diff", "HEAD") or ""
    head = head.strip() or "nohead"
    if not porcelain.strip() and not diff.strip():
        return head + "+clean"
    digest = hashlib.sha1((porcelain + "\0" + diff).encode("utf-8", "replace"))
    return head + "+" + digest.hexdigest()[:8]


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
    here = tree_id()
    d = runs_dir()
    rows = read_ledger(d / LEDGER_NAME)

    print(f"tree:   {here}")
    print(f"ledger: {d / LEDGER_NAME}  ({len(rows)} row(s))")

    porcelain = _git(REPO_ROOT, "status", "--porcelain") or ""
    if any(RUNS_DIR_NAME in ln for ln in porcelain.splitlines()):
        print(f"\n⚠ WARNING: {RUNS_DIR_NAME}/ shows up in `git status` -- it is NOT ignored here.")
        print("  The tree id is derived from that output, so every run changes it and")
        print("  every row is born stale. Add it to .gitignore before trusting anything below.")

    if not rows:
        print("\nNo runs recorded yet. Run a phase: bash formal/verify.sh lean")
        return 1 if require_green else 0

    last: dict[str, dict] = {}
    for r in rows:
        last[r["phase"]] = r          # rows are appended in order; last wins
    green_here = {p for p, r in last.items() if r["status"] == "PASSED" and r["tree"] == here}

    phases = RECOMMENDED + sorted(p for p in last if p not in RECOMMENDED)
    width = max(len(p) for p in phases)
    print()
    print(f"{'phase'.ljust(width)}  {'last run':19}  {'age':9}  {'took':>6}  "
          f"{'status':12}  this tree  counts")
    for phase in phases:
        r = last.get(phase)
        if r is None:
            print(f"{phase.ljust(width)}  {'-':19}  {'-':9}  {'-':>6}  {'never run':12}  -")
            continue
        when = _parse_when(r["started"])
        stamp = when.strftime("%Y-%m-%d %H:%M:%S") if when else r["started"][:19]
        same = "yes" if r["tree"] == here else "NO"
        took = f"{r['dur_s']}s" if r["dur_s"].isdigit() else "?"
        print(f"{phase.ljust(width)}  {stamp:19}  {_age(when):9}  {took:>6}  "
              f"{r['status']:12}  {same:9}  {r['facts']}")

    stale = [p for p, r in last.items() if r["status"] == "PASSED" and r["tree"] != here]
    if stale:
        print(f"\n{len(stale)} phase(s) are green on a DIFFERENT tree "
              f"(e.g. {last[stale[0]]['tree']}) -- those verdicts do not apply here.")

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
    ap.add_argument("--require-green", action="store_true",
                    help="exit 1 unless every phase is PASSED on the current tree")
    args = ap.parse_args(argv)
    if args.tree_id:
        print(tree_id())
        return 0
    return report(args.require_green)


if __name__ == "__main__":
    sys.exit(main())
