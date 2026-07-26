"""Token-level soundness-hole scanner for the Lean sources (verify.sh step 2).

Originally extracted from the inline `<<'PYEOF'` heredoc that used to live in
`formal/verify.sh` so the tricky comment/string/char-literal handling can be unit
tested (`test_sorry_scan.py`).

WHAT IT LOOKS FOR (all of these are ways a "0 sorries" tree can still be unsound):
  * `sorry` / `admit`  — the classic proof holes;
  * `sorryAx`          — the CONSTANT a `sorry` elaborates to. The pre-2026-07-26
    regex was `\\b(?:sorry|admit)\\b`, and `\\bsorry\\b` CANNOT match `sorryAx`
    (`A` is a word character), so the scanner was blind to the exact name the
    axiom audit exists to exclude (zero-trust review `ZT-P2-3`);
  * `native_decide`    — closes a goal by running compiled code, pulling the
    `Lean.ofReduceBool` axiom: a real soundness risk, not a proof;
  * custom `axiom` DECLARATIONS — `axiom cheat : ∀ p, p` typechecks, produces no
    `sorry`, and is invisible to every other check unless the declaration happens
    to sit inside an audited dependency cone. Note the tree legitimately contains
    the WORD "axiom" in prose and in `#print axioms <thm>` COMMANDS, so the match
    is anchored at a declaration position (line start, modulo declaration
    modifiers) — `#print axioms` starts with `#` and never matches.

WHAT IT DOES NOT LOOK FOR: `opaque`. The tree carries exactly one deliberate
`opaque` (`Core/Ident.lean` `ValidIdent`, a Phase-1 placeholder) and the axiom
audit already reports an opaque constant in any dependency cone that routes
through one, so flagging it here would be a permanent false positive.

Contract (matches the old heredoc + verify.sh's use of it):
  * argv holds one or more Lean source roots (a directory is scanned recursively
    for `*.lean`; a file is scanned directly), plus the optional flags below;
  * dot-directories are NEVER scanned — `formal/lean/.lake/` holds the vendored
    toolchain + mathlib/aesop/batteries (~9.3k `.lean` files) which is not project
    code. This is what lets verify.sh point the scan at `formal/lean` (covering the
    library ROOT `ZanzibarProofs.lean`, previously unscanned — `ZT-P2-4`) instead of
    at the `ZanzibarProofs/` subdirectory;
  * every violating TOKEN OUTSIDE comments (`--` line, nested `/- -/` block,
    `/-- -/` docstring) and string literals is counted -- an inline `:= sorry`
    counts, a prose mention in a comment or a `"sorry"` string does not;
  * an UNTERMINATED string literal is itself a violation: it means the tokenizer
    desynced and the rest of that file was invisible to the scan. It used to be
    swallowed silently (`ZT-P2-3`); now it is reported loudly and counted;
  * `--min-files N` makes the scanner exit nonzero if fewer than N project `.lean`
    files were scanned in total — a coverage floor, so a scan that silently
    stopped finding files (bad root, moved tree) cannot report a clean 0;
  * the total violation count is printed to stdout (verify.sh parses this and
    requires the shape to be numeric); every finding and the coverage summary go
    to stderr;
  * the process exits nonzero on any violation, on a coverage shortfall, or on a
    bad root; 0 otherwise.
"""

from __future__ import annotations

import re
import sys
import pathlib
from typing import NamedTuple

# `formal/lean/.lake/**` (vendored mathlib et al.) must never be scanned; skipping
# every dot-directory covers it and anything else hidden.
_DOT = "."

# Proof holes + soundness-relevant tactics. `sorryAx` is listed BEFORE `sorry` so
# the alternation reports the longer name; `\b` on both sides keeps identifiers
# like `sorryish` / `presorry` from tripping (pinned in test_sorry_scan.py).
HOLE_RE = re.compile(r"\b(?:sorryAx|sorry|admit|native_decide)\b")

# A custom `axiom` DECLARATION, anchored at a declaration position: start of line,
# optionally preceded by declaration modifiers / an attribute block, and followed
# by whitespace (so `axiom_free_foo` is not a match). `#print axioms X` begins with
# `#` and can never match. Applied to the comment/string-stripped text, so prose
# mentions of the word are already gone.
AXIOM_DECL_RE = re.compile(
    r"^[ \t]*(?:(?:@\[[^\]\n]*\]|private|protected|scoped|local|noncomputable)[ \t]+)*"
    r"axiom[ \t\r\n]",
    re.MULTILINE,
)


class Finding(NamedTuple):
    """One violation: its kind, the offending text, and the 1-based line."""
    kind: str      # 'token' | 'axiom' | 'unterminated-string'
    text: str
    line: int


def _strip(src: str) -> tuple[str, int | None]:
    """Blank out comments and string literals, preserving line structure.

    Returns `(stripped_text, unterminated_string_line)` where the second element is
    the 1-based line a string literal opened on if it was never closed (else None).

    Newlines inside comments and multi-line strings are PRESERVED so that
    `AXIOM_DECL_RE`'s line anchoring stays faithful to the original file: a block
    comment that ends mid-line must not glue the next line onto the previous one.
    """
    n, i, depth, out = len(src), 0, 0, []
    unterminated: int | None = None
    while i < n:
        if depth > 0:                      # inside (possibly nested) block comment
            if src.startswith("/-", i):
                depth += 1; i += 2
            elif src.startswith("-/", i):
                depth -= 1; i += 2
                if depth == 0:
                    out.append(" ")        # token barrier where the comment was
            else:
                if src[i] == "\n":
                    out.append("\n")       # keep line structure
                i += 1
            continue
        if src.startswith("/-", i):        # block comment / docstring opens
            depth = 1; i += 2; continue
        if src.startswith("--", i):        # line comment
            j = src.find("\n", i)
            i = n if j < 0 else j          # keep the newline as the barrier
            continue
        if src.startswith("'\"'", i):      # the char literal '"' — not a string
            out.append(" "); i += 3; continue
        if src[i] == '"':                  # string literal: data, not a proof hole
            open_line = src.count("\n", 0, i) + 1
            i += 1
            closed = False
            while i < n:
                if src[i] == "\\":
                    i += 2; continue
                if src[i] == '"':
                    i += 1; closed = True; break
                if src[i] == "\n":
                    out.append("\n")       # multi-line string: keep line structure
                i += 1
            if not closed and unterminated is None:
                # ZT-P2-3: this used to swallow the rest of the file in silence.
                unterminated = open_line
            out.append(" ")
            continue
        out.append(src[i]); i += 1
    return "".join(out), unterminated


def scan_text(src: str) -> list[Finding]:
    """Return every finding in one Lean source text."""
    stripped, unterminated = _strip(src)
    findings: list[Finding] = []
    if unterminated is not None:
        findings.append(Finding("unterminated-string", '"', unterminated))
    for m in HOLE_RE.finditer(stripped):
        findings.append(
            Finding("token", m.group(0), stripped.count("\n", 0, m.start()) + 1))
    for m in AXIOM_DECL_RE.finditer(stripped):
        findings.append(
            Finding("axiom", m.group(0).strip(), stripped.count("\n", 0, m.start()) + 1))
    return findings


def lean_files(root: pathlib.Path) -> tuple[list[pathlib.Path], int]:
    """Project `*.lean` files under `root`, plus the count skipped as vendored.

    A file root is returned as-is. Any path with a dot-directory component below
    `root` (`.lake/**` above all) is skipped and counted, never scanned.
    """
    if root.is_file():
        return [root], 0
    kept: list[pathlib.Path] = []
    skipped = 0
    for p in sorted(root.rglob("*.lean")):
        rel = p.relative_to(root)
        if any(part.startswith(_DOT) for part in rel.parts[:-1]):
            skipped += 1
            continue
        kept.append(p)
    return kept, skipped


def scan(root: pathlib.Path, *, report: bool = True) -> int:
    """Return the number of violations under `root`, printing each to stderr.

    Backwards-compatible with the original `scan(root) -> int` (verify.sh only ever
    used the count + the exit status); the count now spans every detection above,
    not just `sorry`/`admit`.
    """
    count = 0
    for p in lean_files(root)[0]:
        try:
            src = p.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:               # pragma: no cover - defensive
            count += 1
            if report:
                print(f"  UNREADABLE (not utf-8): {p} ({exc})", file=sys.stderr)
            continue
        for f in scan_text(src):
            count += 1
            if report:
                where = f"{_rel(p, root)}:{f.line}"
                if f.kind == "unterminated-string":
                    print(f"  !! UNTERMINATED STRING LITERAL at {where} -- the rest of"
                          f" this file was NOT scanned; fix the source", file=sys.stderr)
                elif f.kind == "axiom":
                    print(f"  custom axiom declaration: {where}: {f.text}",
                          file=sys.stderr)
                else:
                    print(f"  {f.text} token: {where}", file=sys.stderr)
    return count


def _rel(p: pathlib.Path, root: pathlib.Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:                                  # pragma: no cover - defensive
        return str(p)


def main(argv: list[str]) -> int:
    roots: list[pathlib.Path] = []
    min_files: int | None = None
    args = argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--min-files":
            min_files = int(args[i + 1]); i += 2
        elif a.startswith("--min-files="):
            min_files = int(a.split("=", 1)[1]); i += 1
        else:
            roots.append(pathlib.Path(a)); i += 1
    if not roots:
        print("usage: sorry_scan.py [--min-files N] ROOT [ROOT...]", file=sys.stderr)
        print(0)
        return 2

    count = 0
    scanned = 0
    skipped = 0
    for root in roots:
        if not root.exists():
            print(f"  FAIL: scan root does not exist: {root}", file=sys.stderr)
            print(0)
            return 2
        files, sk = lean_files(root)
        scanned += len(files)
        skipped += sk
        count += scan(root)

    print(f"  scanned {scanned} project .lean file(s) under "
          f"{', '.join(str(r) for r in roots)}"
          f"; skipped {skipped} vendored file(s) in dot-directories (.lake/**)",
          file=sys.stderr)

    short = min_files is not None and scanned < min_files
    if short:
        print(f"  !! COVERAGE FLOOR: only {scanned} project .lean file(s) scanned,"
              f" expected >= {min_files}. A clean 0 from a scan that stopped finding"
              f" files is not evidence. Check the scan root, or lower the floor"
              f" deliberately if the tree really shrank.", file=sys.stderr)
    print(count)
    return 0 if (count == 0 and not short) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
