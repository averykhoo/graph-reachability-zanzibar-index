#!/usr/bin/env python3
"""Claim-rot gate for `formal/CORRESPONDENCE.md` (`P13`; verify.sh steps 4d2 / 4d3).

WHY THIS EXISTS.  Step 4d (`anchor_check.py`) resolves every `file::symbol` anchor in
the model<->code map and NOTHING ELSE.  A 2026-08-16 audit of the rows one session had
touched found four defects, three of them invisible to every gate in the project: a
retracted "82/82 derived keys agree" still live in a row; two rows describing a model
that had since changed; an unanchored def; and a divergence missing from §7.  All four
were hand-fixed, and hand-fixing does not generalise.  The design is
`formal/history/claim-rot-gate-design-2026-08-16.md`; the build record, with the
sabotage evidence, is `docs/p13-claim-rot-gate-2026-09-27.md`.

TWO CHECKS, BOTH RUN BY `--check`:

(B) THE ANCHOR CONTENT PIN (step 4d2) -- `check_content_pin`.  Every unique anchor in
    `CORRESPONDENCE.md` has the hash of its symbol's BODY recorded in the golden
    `formal/correspondence_anchor_pin.txt`.  When a body changes, the pin moves, the gate
    is red, and the failure names the CORRESPONDENCE.md lines that cite the symbol.
    Regenerating (`--generate`) is the deliberate step, and it is the moment to re-read
    those rows.  What "body" means, per kind (`anchor_body`):
      * Lean `def`/`abbrev`/`structure`/`class`/`inductive`/`instance`/`opaque`: the
        full declaration text, comments stripped and whitespace collapsed (the same
        `statement_pin.strip_comments` / `::normalize` the definition pin uses).  NOT
        the signature: `persistedLeaves` changed twice on 2026-08-16 with a
        byte-identical signature, which is the case that motivated the design.
      * Lean `theorem`/`lemma`: the STATEMENT only (`statement_pin.extract`, up to the
        top-level `:=`).  The proof is not pinned, for the reason `statement_pin.py`
        gives: refactoring a proof is normal work, changing what is claimed is not.
      * Lean structure field / inductive constructor (`Delta.leaf`): the whole parent
        declaration.
      * Python function / method: `ast.unparse` of the definition with its docstring
        removed -- so comment, docstring and formatting edits do not fire, and any
        change to the code does.
      * Python class: its SHELL only -- decorators, bases, keywords and class-level
        statements (fields, constants), docstring removed, method and nested-class
        bodies excluded.  A method is pinned only if a row anchors the method itself.
        Pinning whole class bodies would fire on every edit to `WildcardIndex` or
        `SetEngine`, and a gate that fires on everything gets regenerated without
        being read, which is the failure this exists to prevent.
      * Python module/class assignment: `ast.unparse` of every statement binding it.
    A name that resolves to several declarations (a Lean suffix matching two decls in
    one file, a Python property and its setter) hashes all of them, in order.

(C) THE PROSE-NUMBER LINT (step 4d3) -- `check_prose_numbers`.  Every `N/M` or
    `N of M` (with N <= M) in `CORRESPONDENCE.md` must, within its own SENTENCE,
    either CITE a test or the generated counts block (`CITE_RE`; the sentence after it
    also counts, since "X is 132/299. It is pinned by `tests/...`" is the common
    shape), or be MARKED as a past measurement: a date AND a pastness word, the same
    contract as step 4e's corpus-count prose scan (`doc_counts.py::_DATE_RE`,
    `::_PAST_WORDS`).  The window is the sentence, not the row or 4e's three lines,
    because the row that carries the leaf-allocation claim already contains
    "2026-08-16 ... was measured WRONG": a row-scoped exemption would have let the
    re-inserted "82/82" through (measured; see the build record).

WHAT NEITHER CHECK DOES -- read this before trusting either for more than it claims:
  * NEITHER VERIFIES THAT A ROW IS TRUE.  They convert SILENTLY STALE into LOUDLY
    MUST-LOOK.  (B) tells you a symbol a row describes has changed; whether the row is
    still right is a human reading.  A `--generate` run without that reading defeats
    it, and nothing here can tell the difference.
  * (B) sees only ANCHORED symbols.  An unanchored def a row relies on (the
    `unionSpineLeaves` case) is invisible to it; so is a change to a callee the anchored
    body calls, a Lean `variable`/`open`/`instance` elsewhere in the file, and a Python
    module-level import or decorator definition.  The Python body is `ast.unparse`
    under the gate's interpreter: a Python upgrade that changes `unparse` output moves
    every Python hash at once (that is loud, not silent -- regenerate and say why).
  * (C) cannot tell whether a cited test asserts the number it sits next to, whether a
    past-marked number was ever true, or anything about numbers not shaped `N/M` /
    `N of M`.  A ratio with N > M (`194/41`, a split) is not treated as a claim, and
    ordinal enumerations (`Phase 0/2`, `tile 1/5`) are skipped by `ORDINAL_RE`.
  * One of the four motivating defects is not mechanizable at all: knowing that a newly
    discovered Python fact belongs in §7's drift log is irreducibly human.

Usage:
    python formal/conformance/claim_rot.py --check      # both checks (the gate)
    python formal/conformance/claim_rot.py --generate   # rewrite the (B) golden
    python formal/conformance/claim_rot.py --coverage   # (A) census, report only
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from formal.conformance import anchor_check, statement_pin  # noqa: E402
from formal.conformance import doc_counts  # noqa: E402

DOC = REPO_ROOT / "formal" / "CORRESPONDENCE.md"
PIN = REPO_ROOT / "formal" / "correspondence_anchor_pin.txt"

# Non-vacuity floor on the golden.  Measured 2026-09-27: 474 unique anchors
# (248 Python + 226 Lean).  A truncated golden already fails (every live anchor
# missing from it is reported), so this is the belt to that brace: it catches a
# golden AND map gutted together, which anchor_check's own floors bound loosely.
# Asserted with >=; lowering it must be a deliberate, reviewed edit.
MIN_PINNED_ANCHORS = 470

HASH_LEN = 16


# --------------------------------------------------------------------------- #
# (B) body extraction
# --------------------------------------------------------------------------- #
def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        return body[1:]
    return body


def _py_body(node: ast.stmt) -> tuple[str, str]:
    """(kind, normalized text) for one binding statement."""
    # A SHALLOW copy with a replaced `body` list: `ast.unparse` never mutates, so the
    # original tree (shared through the parse cache) is left intact, and a deepcopy
    # of a whole class -- methods included -- was 10 s of a cold run.
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        n = copy.copy(node)
        n.body = _strip_docstring(node.body) or [ast.Pass()]
        return "py:function", ast.unparse(n)
    if isinstance(node, ast.ClassDef):
        n = copy.copy(node)
        n.body = [s for s in _strip_docstring(node.body)
                  if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef,
                                        ast.ClassDef))] or [ast.Pass()]
        return "py:class-shell", ast.unparse(n)
    return "py:assign", ast.unparse(node)


# Lean: every declaration keyword anchor_check resolves (LEAN_DECL_RE), scanned over
# COMMENT-STRIPPED text so a comment edit cannot move a hash.
LEAN_DECL_RE = anchor_check.LEAN_DECL_RE
_KW_RE = re.compile(
    r"\b(def|theorem|lemma|abbrev|structure|inductive|instance|opaque|class)\s+"
)


def lean_decls(path: Path) -> dict[str, tuple[str, str]]:
    """Full Lean name -> (kind, normalized body) for every declaration in `path`."""
    text = statement_pin.strip_comments(path.read_text(encoding="utf-8"))
    lines = text.splitlines()
    stmts = statement_pin.extract(path)
    out: dict[str, tuple[str, str]] = {}
    ns: list[str | None] = []
    for idx, line in enumerate(lines):
        m = statement_pin.NS_RE.match(line)
        if m:
            ns.append(m.group("name"))
            continue
        if statement_pin.SECTION_RE.match(line):
            ns.append(None)
            continue
        if statement_pin.END_RE.match(line):
            if ns:
                ns.pop()
            continue
        m = LEAN_DECL_RE.match(line)
        if not m:
            continue
        kw = _KW_RE.search(line[: m.end("name")]).group(1)
        prefix = ".".join(x for x in ns if x)
        full = f"{prefix}.{m.group('name')}" if prefix else m.group("name")
        if kw in ("theorem", "lemma") and full in stmts:
            out[full] = (f"lean:{kw}-statement", stmts[full])
            continue
        buf = [line]
        for chunk in lines[idx + 1:]:
            if statement_pin.DEF_STOP_RE.match(chunk):
                break
            buf.append(chunk)
        out[full] = (f"lean:{kw}", statement_pin.normalize(" ".join(buf)))
    return out


def _lean_match(decls: dict[str, tuple[str, str]], sym: str) -> list[str]:
    """Declarations `sym` names by dotted suffix -- anchor_check's own rule."""
    return sorted(n for n in decls if n == sym or n.endswith("." + sym))


def anchor_body(f: str, sym: str, cache: dict) -> tuple[str, str] | None:
    """(kind, normalized body) of anchor `f::sym`, or None if it cannot be pinned."""
    p = anchor_check.resolve_path(f)
    if p is None:
        return None
    if p not in cache:
        cache[p] = lean_decls(p) if f.endswith(".lean") else anchor_check.python_nodes(p)
    idx = cache[p]
    if f.endswith(".py"):
        nodes = idx.get(sym)
        if not nodes:
            return None
        parts = [_py_body(n) for n in nodes]
        return "+".join(sorted({k for k, _ in parts})), "\n".join(t for _, t in parts)
    names = _lean_match(idx, sym)
    member = False
    if not names and "." in sym:
        # A structure field or inductive constructor (`Delta.leaf`): pin the parent.
        names = _lean_match(idx, sym.rsplit(".", 1)[0])
        member = True
    if not names:
        return None
    kinds = sorted({idx[n][0] for n in names})
    kind = "+".join(kinds) + (":member" if member else "")
    return kind, "\n".join(f"{n}\t{idx[n][1]}" for n in names)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:HASH_LEN]


def live_anchor_rows(
    doc_text: str, cache: dict | None = None
) -> tuple[dict[str, str], dict[str, list[int]], list[str]]:
    """(key -> "kind\\thash", key -> citing line numbers, unpinnable keys).

    `key` is `file::symbol` exactly as anchor_check extracts it.  An anchor 4d
    resolves but this cannot pin is reported, never dropped: a silent drop is a
    coverage leak of exactly the kind this module exists to close.
    """
    cache = {} if cache is None else cache
    rows: dict[str, str] = {}
    cites: dict[str, list[int]] = {}
    bad: list[str] = []
    for line_no, f, sym in anchor_check.extract_anchors(doc_text):
        key = f"{f}::{sym}"
        cites.setdefault(key, []).append(line_no)
        if key in rows or key in bad:
            continue
        got = anchor_body(f, sym, cache)
        if got is None:
            bad.append(key)
            continue
        kind, body = got
        rows[key] = f"{kind}\t{_digest(body)}"
    return rows, cites, bad


PIN_HEADER = """\
# formal/correspondence_anchor_pin.txt -- the CONTENT pin for CORRESPONDENCE.md's
# anchors (P13 mechanism (B); verify.sh step 4d2).
#
# Step 4d proves every `file::symbol` in formal/CORRESPONDENCE.md still RESOLVES.
# This file records a hash of each anchored symbol's BODY, so a symbol whose meaning
# changed under an unchanged name turns the gate red and names the rows that cite
# it.  It does NOT say the rows are true -- only that nobody has looked since.
#
# Rows:  <file>::<symbol> TAB <kind> TAB <sha256 prefix of the normalized body>
# What "body" means per kind, and what this still cannot see, is in
# formal/conformance/claim_rot.py's module docstring.
#
# REGENERATE DELIBERATELY, after RE-READING the CORRESPONDENCE.md rows the failure
# names (a regeneration without that reading is the one thing this cannot detect):
#
#     python formal/conformance/claim_rot.py --generate
#
"""


def read_pin(path: Path = PIN) -> dict[str, str]:
    rows: dict[str, str] = {}
    if not path.is_file():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        key, _, val = raw.partition("\t")
        rows[key.strip()] = val.strip()
    return rows


def check_content_pin(
    doc_text: str, pinned: dict[str, str], cache: dict | None = None
) -> list[str]:
    """(B).  Return one complaint per discrepancy; empty == clean."""
    live, cites, unpinnable = live_anchor_rows(doc_text, cache)
    out: list[str] = []
    for key in unpinnable:
        out.append(f"{key}: resolves for step 4d but has no pinnable body here -- the "
                   f"two instruments disagree about what it names (cited at "
                   f"CORRESPONDENCE.md:{','.join(map(str, cites[key]))})")
    if len(pinned) < MIN_PINNED_ANCHORS:
        out.append(f"the golden lists only {len(pinned)} anchor(s); floor is "
                   f"{MIN_PINNED_ANCHORS} -- a gutted golden compares nothing")
    for key in sorted(set(live) - set(pinned)):
        out.append(f"{key}: anchored in CORRESPONDENCE.md (line(s) "
                   f"{','.join(map(str, cites[key]))}) but NOT pinned")
    for key in sorted(set(pinned) - set(live) - set(unpinnable)):
        out.append(f"{key}: pinned but no longer anchored in CORRESPONDENCE.md "
                   f"(a row was removed or re-pointed)")
    for key in sorted(set(live) & set(pinned)):
        if live[key] != pinned[key]:
            out.append(f"{key}: BODY CHANGED ({pinned[key]} -> {live[key]}); re-read "
                       f"CORRESPONDENCE.md line(s) {','.join(map(str, cites[key]))}")
    return out


# --------------------------------------------------------------------------- #
# (C) prose-number lint
# --------------------------------------------------------------------------- #
#: `82/82`, `744/744`, `132/299`; not a path (`a/1/2`), a tile (`tile:1/5`), a
#: version, a date fragment or a decimal.
SLASH_RE = re.compile(r"(?<![\w/.:-])(\d+)/(\d+)(?![\w/]|\.\d)")
#: `5 of 21`, `**11 of 13**`, `18 out of 171`.
OF_RE = re.compile(r"(?<![\w.])(\d+) (?:out )?of (\d+)(?![\w.]|\.\d)")
#: Ordinal enumerations are positions, not validation claims.
ORDINAL_RE = re.compile(
    r"(?:phase|step|leg|tile|part|round|stage|rows?|lines?)\s*\**\s*$", re.I)
#: A citation: a test file or test anchor that EXISTS (`_cites` resolves the file;
#: step 4d additionally resolves the `::symbol` of the anchored form), or the
#: generated counts block (step 4e proves its numbers).
CITE_RE = re.compile(r"`(?P<f>[^`\s]*\btest_[A-Za-z0-9_]*\.py)(?:::[^`]+)?`")
GEN_RE = re.compile(r"generated (?:counts )?block|doc_counts")


def _cites(sentence: str) -> bool:
    """A cited test file that does not exist is not a citation -- otherwise
    "`tests/test_anything.py`" would exempt any number, and 4d never looks at a
    bare file mention."""
    return bool(GEN_RE.search(sentence)) or any(
        anchor_check.resolve_path(m.group("f")) is not None
        for m in CITE_RE.finditer(sentence))
PAST_WORDS = tuple(doc_counts._PAST_WORDS) + ("retracted", "refuted")
PAST_RE = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in PAST_WORDS) + r")\b",
                     re.I)
DATE_RE = doc_counts._DATE_RE
#: A sentence ends at `.`/`;`/`!`/`?` followed by whitespace, or at a table-cell bar.
SENT_END_RE = re.compile(r"(?<=[.;!?])\s+|\|")


def _blocks(text: str):
    """Yield (first line number, [lines]) for each markdown block.

    A table row is its own block (a row cannot borrow its neighbour's citation);
    otherwise a block is a paragraph or list item, ended by a blank line, a heading,
    a new list item or a table row.
    """
    buf: list[str] = []
    start = 1
    for i, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        is_row = s.startswith("|")
        new_item = bool(re.match(r"^\s*(?:[*+-]|\d+\.)\s|^\s*#{1,6}\s", line))
        if not s or is_row or new_item:
            if buf:
                yield start, buf
                buf = []
            if is_row:
                yield i, [line]
                continue
            if not s:
                continue
        if not buf:
            start = i
        buf.append(line)
    if buf:
        yield start, buf


def _sentences(block: str) -> list[tuple[int, int]]:
    spans, pos = [], 0
    for m in SENT_END_RE.finditer(block):
        spans.append((pos, m.start()))
        pos = m.end()
    spans.append((pos, len(block)))
    return spans


def ratio_claims(text: str):
    """Yield (line_no, ratio, sentence, next_sentence) for every N/M, N of M claim."""
    for start, lines in _blocks(text):
        block = "\n".join(lines)
        spans = _sentences(block)
        for rx in (SLASH_RE, OF_RE):
            for m in rx.finditer(block):
                n, d = int(m.group(1)), int(m.group(2))
                if d == 0 or n > d:
                    continue
                if ORDINAL_RE.search(block[max(0, m.start() - 12):m.start()]):
                    continue
                k = next(i for i, (a, b) in enumerate(spans) if a <= m.start() <= b)
                a, b = spans[k]
                nxt = block[slice(*spans[k + 1])] if k + 1 < len(spans) else ""
                line_no = start + block.count("\n", 0, m.start())
                yield line_no, m.group(0), block[a:b], nxt


def check_prose_numbers(text: str) -> list[str]:
    """(C).  Return one complaint per uncited, unmarked ratio claim; empty == clean."""
    bad: list[str] = []
    for line_no, ratio, sent, nxt in ratio_claims(text):
        if _cites(sent) or _cites(nxt):
            continue
        if DATE_RE.search(sent) and PAST_RE.search(sent):
            continue
        excerpt = doc_counts._ascii(" ".join(sent.split())[:110])
        bad.append(f"CORRESPONDENCE.md:{line_no}: '{ratio}' | {excerpt}")
    return bad


# --------------------------------------------------------------------------- #
# (A) census -- report only; see the build record for why it is not a gate
# --------------------------------------------------------------------------- #
def coverage(doc_text: str) -> dict[str, int]:
    """Non-witness Lean declarations under ZanzibarProofs/, and how many are anchored.

    The witness exclusion is STRUCTURAL -- any enclosing namespace component ending
    in `Witness` -- never a list (the design's trap: a list has failed twice here).
    """
    by_file: dict[Path, set[str]] = {}
    for _, f, sym in anchor_check.extract_anchors(doc_text):
        if f.endswith(".lean"):
            p = anchor_check.resolve_path(f)
            if p is not None:
                by_file.setdefault(p, set()).add(sym)
    tot = anch = defs = defs_anch = files = files_zero = 0
    for p in statement_pin.lean_files():
        if "ZanzibarProofs" not in p.parts:
            continue
        syms = by_file.get(p, set())
        hit_any = seen = False
        for n, (kind, _) in lean_decls(p).items():
            if any(c.endswith("Witness") for c in n.split(".")[:-1]):
                continue
            hit = any(n == s or n.endswith("." + s) for s in syms)
            seen = True
            tot += 1
            anch += hit
            hit_any |= hit
            if "theorem" not in kind and "lemma" not in kind:
                defs += 1
                defs_anch += hit
        files += seen
        files_zero += seen and not hit_any
    return {"decls": tot, "anchored": anch, "defs": defs, "defs_anchored": defs_anch,
            "files": files, "files_zero": files_zero}


# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--generate", action="store_true")
    g.add_argument("--coverage", action="store_true")
    args = ap.parse_args(argv)
    doc_text = DOC.read_text(encoding="utf-8")

    if args.coverage:
        c = coverage(doc_text)
        print(f"  (A) census: {c['decls']} non-witness Lean declarations, "
              f"{c['anchored']} anchored; non-theorem {c['defs']}, anchored "
              f"{c['defs_anchored']}; {c['files_zero']} of {c['files']} files have none")
        return 0

    if args.generate:
        live, _, unpinnable = live_anchor_rows(doc_text)
        if unpinnable:
            print("FAIL: cannot pin: " + ", ".join(unpinnable), file=sys.stderr)
            return 1
        old = read_pin()
        changed = sorted(k for k in live if k in old and old[k] != live[k])
        added = sorted(set(live) - set(old))
        gone = sorted(set(old) - set(live))
        PIN.write_text(PIN_HEADER + "".join(f"{k}\t{live[k]}\n" for k in sorted(live)),
                       encoding="utf-8", newline="\n")
        print(f"  wrote {PIN.name}: {len(live)} anchors "
              f"({len(changed)} changed, {len(added)} added, {len(gone)} removed)")
        for label, keys in (("changed", changed), ("added", added), ("removed", gone)):
            for k in keys:
                print(f"    {label}: {k}")
        if len(live) < MIN_PINNED_ANCHORS:
            print(f"WARNING: {len(live)} rows is below MIN_PINNED_ANCHORS="
                  f"{MIN_PINNED_ANCHORS}; the gate will reject this golden.",
                  file=sys.stderr)
        return 0

    rc = 0
    pinned = read_pin()
    pin_bad = check_content_pin(doc_text, pinned)
    if pin_bad:
        print(f"FAIL: {len(pin_bad)} CORRESPONDENCE.md anchor CONTENT-pin "
              f"discrepancy(ies) against {PIN.name}:")
        for s in pin_bad:
            print(f"      {s}")
        print("      A symbol a row DESCRIBES changed under an unchanged name. Re-read\n"
              "      the cited rows; fix any that are now false (or log the drift in\n"
              "      CORRESPONDENCE.md section 7); THEN regenerate deliberately:\n"
              "        python formal/conformance/claim_rot.py --generate")
        rc = 1
    else:
        print(f"  CORRESPONDENCE.md anchor content pin: {len(pinned)}/{len(pinned)} "
              f"bodies match (floor {MIN_PINNED_ANCHORS})")
    prose_bad = check_prose_numbers(doc_text)
    if prose_bad:
        print(f"FAIL: {len(prose_bad)} N/M or 'N of M' claim(s) in CORRESPONDENCE.md "
              f"that neither cite a test / the generated counts block nor are marked "
              f"as past measurements:")
        for s in prose_bad:
            print(f"      {s}")
        print("      Fix EITHER way, in the SAME sentence: (a) cite the test that pins\n"
              "      it (`tests/x.py::test_y`) or point at FINAL_REVIEW.md's generated\n"
              "      counts block; (b) if it is a past measurement, say so -- a date AND\n"
              "      a pastness word ('82/82, retracted 2026-08-16b'). Deleting the\n"
              "      number is always available and is the durable fix.")
        rc = 1
    else:
        n = sum(1 for _ in ratio_claims(doc_text))
        print(f"  CORRESPONDENCE.md prose numbers: {n} N/M claim(s), 0 uncited "
              f"and unmarked")
    return rc


if __name__ == "__main__":
    sys.exit(main())
