#!/usr/bin/env python3
"""Mechanical anchor check for `formal/CORRESPONDENCE.md` (CORRESPONDENCE.md §9).

WHY THIS EXISTS.  `CORRESPONDENCE.md` is the auditable model<->code map.  Its
previous revision cited Python by LINE NUMBER; by 2026-07-26 the zero-trust
review measured 4 of ~45 citations accurate and ~35 pointing at unrelated code
(§5 was 100% wrong).  The rebuild re-keyed every row onto `file::symbol`
anchors and hand-verified them ONCE.  Nothing checked them afterwards, and the
drift rate that destroyed the line numbers (~3,000 lines / two weeks) is
unchanged -- so the map was accurate on the day it was written and undefended
every day after.  This script is the defence: it asserts every anchor still
RESOLVES.

WHAT IT DOES NOT DO (say this out loud, or the next reader over-trusts it, which
is how the previous revision rotted): it keeps the map NAVIGABLE, not TRUE.  It
cannot tell you that a row's correspondence CLAIM is wrong -- §2's `check` row is
the standing proof that a resolvable anchor can head a false twin claim.

Resolution is by PARSE, never by import: Python via `ast`, Lean via a
declaration scanner with namespace tracking (no Lean toolchain needed, ~1 s).

Usage:
    python formal/conformance/anchor_check.py            # check, exit 1 on failure
    python formal/conformance/anchor_check.py --list     # dump resolved anchors

Gated by `formal/verify.sh` (the `lean` phase, step 4c).
"""

from __future__ import annotations

import argparse
import ast
import difflib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "formal" / "CORRESPONDENCE.md"
LEAN_ROOT = REPO_ROOT / "formal" / "lean" / "ZanzibarProofs"

# Non-vacuity floors (CORRESPONDENCE.md §9.1 step 4).  ZT-P2-1/ZT-P2-2 showed the
# failure mode where a gate derives its expectation from the artifact it audits:
# without these, deleting every row from CORRESPONDENCE.md would leave this script
# checking zero anchors and reporting success.  Measured 2026-07-27: 349 anchors --
# 243 Python + 106 Lean, 0 unresolved.  Asserted with >=, so ADDING rows is always free; LOWERING one
# must be a deliberate, reviewed edit here.
MIN_PY_ANCHORS = 250
MIN_LEAN_ANCHORS = 100

# `path.py::Symbol` / `Dir/File.lean::Decl`, and the bare continuation `::Symbol`
# which inherits the most recently named file in the SAME table cell or prose
# paragraph (the tables above use it heavily for readability).
FULL_RE = re.compile(
    r"`(?P<file>[A-Za-z0-9_./+-]+\.(?:py|lean))::(?P<sym>[A-Za-z_][A-Za-z0-9_.']*)`"
)
BARE_RE = re.compile(r"`::(?P<sym>[A-Za-z_][A-Za-z0-9_.']*)`")
ANY_RE = re.compile(
    r"`(?:(?P<file>[A-Za-z0-9_./+-]+\.(?:py|lean)))?::(?P<sym>[A-Za-z_][A-Za-z0-9_.']*)`"
)
# A plain backticked file mention (`index_v4/processor.py`) with no `::` also
# supplies the inherited file for the bare anchors that follow it in the same
# scope -- §8's prose bullets name the file in their bold header and then use the
# bare form throughout the body.
PLAIN_FILE_RE = re.compile(r"`(?P<file2>[A-Za-z0-9_./+-]+\.(?:py|lean))`")
# A new inheritance scope starts at a blank line, a table row (per cell) or a new
# list item / heading -- so a file named in one bullet cannot leak into the next.
NEW_SCOPE_RE = re.compile(r"^\s*(?:[*+-]\s|#{1,6}\s|>)")


# --------------------------------------------------------------------------- #
# Anchor extraction
# --------------------------------------------------------------------------- #
def _scopes(text: str):
    """Yield (line_no, scope_text) units within which a bare `::Sym` inherits a file.

    A markdown table row is split into its CELLS (a bare anchor in the "models"
    column must not silently inherit the Lean column's file); everything else is
    grouped into blank-line-delimited paragraphs.
    """
    para: list[str] = []
    para_start = 1
    for i, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("|"):
            if para:
                yield para_start, "\n".join(para)
                para = []
            for cell in line.split("|"):
                yield i, cell
            continue
        if not line.strip() or NEW_SCOPE_RE.match(line):
            if para:
                yield para_start, "\n".join(para)
                para = []
            if not line.strip():
                continue
        if not para:
            para_start = i
        para.append(line)
    if para:
        yield para_start, "\n".join(para)


def extract_anchors(text: str) -> list[tuple[int, str, str]]:
    """Return [(line_no, file, symbol)] for every anchor in the document."""
    combined = re.compile(
        r"`(?:" + ANY_RE.pattern[1:-1] + r"|" + PLAIN_FILE_RE.pattern[1:-1] + r")`"
    )
    out: list[tuple[int, str, str]] = []
    for line_no, scope in _scopes(text):
        current: str | None = None
        for m in combined.finditer(scope):
            here = line_no + scope.count("\n", 0, m.start())
            plain = m.group("file2") if "file2" in m.groupdict() else None
            if plain is not None:
                # Only a file that actually exists may supply inheritance -- an
                # illustrative mention of a moved module must not silently become
                # the resolution context for the anchors after it.
                if resolve_path(plain) is not None:
                    current = plain
                continue
            f = m.group("file")
            if f:
                current = f
            if current is None:
                # A bare anchor with no file in scope: the row is unusable to an
                # auditor, which is exactly the defect this check exists to find.
                out.append((here, "<no file in scope>", m.group("sym")))
                continue
            out.append((here, current, m.group("sym")))
    return out


# --------------------------------------------------------------------------- #
# Python resolution (ast; no import, no side effects)
# --------------------------------------------------------------------------- #
def python_symbols(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()

    def targets(node: ast.stmt) -> list[str]:
        if isinstance(node, ast.AnnAssign):
            return [node.target.id] if isinstance(node.target, ast.Name) else []
        if isinstance(node, ast.Assign):
            return [t.id for t in node.targets if isinstance(t, ast.Name)]
        return []

    def walk(body: list[ast.stmt], prefix: str, in_class: bool, top: bool) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qual = f"{prefix}{node.name}"
                names.add(qual)
                walk(
                    node.body,
                    qual + ".",
                    isinstance(node, ast.ClassDef),
                    top=False,
                )
            elif in_class or top:
                # Class-body fields (dataclass / SQLModel columns are anchored by
                # several rows) and module-level constants.  Deliberately NOT
                # function locals -- those would leak and weaken the check.
                for t in targets(node):
                    names.add(f"{prefix}{t}")
    walk(tree.body, "", in_class=False, top=True)
    return names


# --------------------------------------------------------------------------- #
# Lean resolution (declaration scanner + namespace tracking)
# --------------------------------------------------------------------------- #
LEAN_DECL_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?"
    r"(?:private\s+|protected\s+|noncomputable\s+|partial\s+|unsafe\s+|nonrec\s+|scoped\s+)*"
    r"(?:def|theorem|lemma|abbrev|structure|inductive|instance|opaque|class)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_.'!?]*)"
)
LEAN_NS_RE = re.compile(r"^\s*namespace\s+(?P<name>[A-Za-z_][A-Za-z0-9_.']*)")
LEAN_SECTION_RE = re.compile(r"^\s*section\b")
LEAN_END_RE = re.compile(r"^\s*end\b")
LEAN_FIELD_RE = re.compile(r"^\s+(?P<name>[A-Za-z_][A-Za-z0-9_']*)\s*:\s*\S")
LEAN_CTOR_RE = re.compile(r"^\s*\|\s*(?P<name>[A-Za-z_][A-Za-z0-9_']*)")


def _add_suffixes(names: set[str], full: str) -> None:
    """Record every dotted SUFFIX of a Lean declaration's full name.

    Most graph-side definitions are written `def GraphState.foo` inside
    `namespace Zanzibar`, while others are `def foo` inside `namespace Zanzibar
    namespace GraphState` -- both are legitimately anchored `GraphState.foo`.
    Accepting any suffix makes the two spellings indistinguishable to the check,
    which is what the anchor convention (§0) already assumes.
    """
    parts = full.split(".")
    for i in range(len(parts)):
        names.add(".".join(parts[i:]))


def lean_symbols(path: Path) -> set[str]:
    names: set[str] = set()
    ns: list[str] = []
    last_decl: str | None = None
    in_block_comment = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw
        if in_block_comment:
            in_block_comment += line.count("/-") - line.count("-/")
            if in_block_comment < 0:
                in_block_comment = 0
            continue
        if "/-" in line and "-/" not in line:
            in_block_comment = 1
            line = line.split("/-")[0]
        m = LEAN_NS_RE.match(line)
        if m:
            ns.append(m.group("name"))
            last_decl = None
            continue
        if LEAN_SECTION_RE.match(line):
            # `section` consumes an `end` too; without this the stack underflows
            # and every later declaration is qualified with the wrong namespace.
            ns.append("")
            last_decl = None
            continue
        if LEAN_END_RE.match(line):
            if ns:
                ns.pop()
            last_decl = None
            continue
        m = LEAN_DECL_RE.match(line)
        if m:
            short = m.group("name")
            prefix = ".".join(x for x in ns if x)
            _add_suffixes(names, f"{prefix}.{short}" if prefix else short)
            last_decl = short
            continue
        # Structure fields / inductive constructors of the last declaration
        # (`Delta.leaf`, the `Inv` clause names, `GraphOp.write`).
        if last_decl:
            m = LEAN_FIELD_RE.match(line) or LEAN_CTOR_RE.match(line)
            if m:
                child = f"{last_decl}.{m.group('name')}"
                prefix = ".".join(x for x in ns if x)
                _add_suffixes(names, f"{prefix}.{child}" if prefix else child)
    return names


# --------------------------------------------------------------------------- #
def resolve_path(anchor_file: str) -> Path | None:
    """Map an anchor's file string to a repo path.

    Python anchors are repo-relative (`tests/oracle.py`, `index_v4/processor.py`).
    Lean anchors are relative to `formal/lean/ZanzibarProofs/` (`Core/Refs.lean`).
    """
    if anchor_file.endswith(".lean"):
        for base in (LEAN_ROOT, REPO_ROOT / "formal" / "lean", REPO_ROOT):
            p = base / anchor_file
            if p.is_file():
                return p
        return None
    p = REPO_ROOT / anchor_file
    return p if p.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print every resolved anchor")
    args = ap.parse_args()

    if not DOC.is_file():
        print(f"FAIL: {DOC} does not exist", file=sys.stderr)
        return 1

    anchors = extract_anchors(DOC.read_text(encoding="utf-8"))
    n_py = sum(1 for _, f, _ in anchors if f.endswith(".py"))
    n_lean = sum(1 for _, f, _ in anchors if f.endswith(".lean"))

    cache: dict[str, set[str] | None] = {}
    failures: list[str] = []
    for line_no, f, sym in anchors:
        if f not in cache:
            p = resolve_path(f)
            if p is None:
                cache[f] = None
            else:
                try:
                    cache[f] = (
                        lean_symbols(p) if f.endswith(".lean") else python_symbols(p)
                    )
                except SyntaxError as exc:  # pragma: no cover - a broken source file
                    print(f"FAIL: could not parse {p}: {exc}", file=sys.stderr)
                    return 1
        syms = cache[f]
        if syms is None:
            failures.append(
                f"  CORRESPONDENCE.md:{line_no}: file does not exist: {f}  (anchor ::{sym})"
            )
            continue
        if sym in syms:
            if args.list:
                print(f"  ok  {f}::{sym}")
            continue
        near = difflib.get_close_matches(sym, sorted(syms), n=3, cutoff=0.6)
        hint = f"   did you mean {', '.join(near)}?" if near else ""
        failures.append(f"  CORRESPONDENCE.md:{line_no}: {f}::{sym} does NOT resolve.{hint}")

    print(
        f"  CORRESPONDENCE.md anchors: {len(anchors)} parsed "
        f"({n_py} Python >= {MIN_PY_ANCHORS}, {n_lean} Lean >= {MIN_LEAN_ANCHORS}), "
        f"{len(anchors) - len(failures)} resolved"
    )

    rc = 0
    if failures:
        print(
            f"FAIL: {len(failures)} CORRESPONDENCE.md anchor(s) no longer resolve "
            f"-- the model<->code map has DRIFTED:",
            file=sys.stderr,
        )
        for f in failures:
            print(f, file=sys.stderr)
        print(
            "      Fix the row (or record the rename in the §5 ledger); do NOT delete\n"
            "      the anchor -- a deleted row lowers the floors below and fails too.",
            file=sys.stderr,
        )
        rc = 1
    if n_py < MIN_PY_ANCHORS:
        print(
            f"FAIL: only {n_py} Python anchors found; floor is {MIN_PY_ANCHORS}.\n"
            "      CORRESPONDENCE.md rows were DELETED -- the map covers less of the\n"
            "      code than it did. If intended, lower MIN_PY_ANCHORS deliberately.",
            file=sys.stderr,
        )
        rc = 1
    if n_lean < MIN_LEAN_ANCHORS:
        print(
            f"FAIL: only {n_lean} Lean anchors found; floor is {MIN_LEAN_ANCHORS}.\n"
            "      CORRESPONDENCE.md rows were DELETED -- see above.",
            file=sys.stderr,
        )
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
