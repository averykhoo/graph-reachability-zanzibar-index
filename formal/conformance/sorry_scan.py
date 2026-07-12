"""Token-level `sorry`/`admit` scanner for the Lean sources (verify.sh step 2).

Extracted VERBATIM from the inline `<<'PYEOF'` heredoc that used to live in
`formal/verify.sh` so the tricky comment/string/char-literal handling can be unit
tested (`test_sorry_scan.py`). The scanning logic is byte-for-byte the same as the
heredoc it replaces.

Contract (matches the old heredoc + verify.sh's use of it):
  * argv[1] is the Lean source root (a directory scanned recursively for `*.lean`);
  * every `sorry` / `admit` TOKEN OUTSIDE comments (`--` line, nested `/- -/`
    block, `/-- -/` docstring) and string literals is counted -- an inline
    `:= sorry` counts, a prose mention in a comment or a `"sorry"` string does not;
  * the count is printed to stdout; each offending file is printed to stderr;
  * the process exits nonzero when the count is > 0 (a found sorry), 0 otherwise.
"""

import re
import sys
import pathlib


def scan(root: pathlib.Path) -> int:
    """Return the number of live `sorry`/`admit` tokens under `root`, printing each
    offending file to stderr as it is found (verbatim from the old heredoc)."""
    count = 0
    for p in sorted(root.rglob("*.lean")):
        src = p.read_text(encoding="utf-8")
        n, i, depth, out = len(src), 0, 0, []
        while i < n:
            if depth > 0:                      # inside (possibly nested) block comment
                if src.startswith("/-", i):
                    depth += 1; i += 2
                elif src.startswith("-/", i):
                    depth -= 1; i += 2
                    if depth == 0:
                        out.append(" ")        # token barrier where the comment was
                else:
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
                i += 1
                while i < n:
                    if src[i] == "\\": i += 2; continue
                    if src[i] == '"': i += 1; break
                    i += 1
                out.append(" ")
                continue
            out.append(src[i]); i += 1
        for m in re.finditer(r"\b(?:sorry|admit)\b", "".join(out)):
            count += 1
            print(f"  {m.group(0)} token: {p.relative_to(root)}", file=sys.stderr)
    return count


def main(argv: list[str]) -> int:
    root = pathlib.Path(argv[1])
    count = scan(root)
    print(count)
    return 0 if count == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
