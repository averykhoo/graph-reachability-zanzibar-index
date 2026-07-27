#!/usr/bin/env python3
"""Statement pin for the headline theorems (ZT-P2-5).

THE ATTACK THIS EXISTS TO STOP.  Before this, `formal/verify.sh`'s axiom audit
was a COUNT and nothing more.  Two erosions kept the gate fully green:

  (i)  delete `#print axioms graph_correct` from `Audit.lean` and add
       `#print axioms Nat.add_comm` -- the count is unchanged, so the gate could
       not tell that the headline theorem stopped being audited.  (Closed by the
       IDENTITY pin, `formal/audited_theorems.txt`, enforced in verify.sh.)

  (ii) restate `theorem graph_correct : True := trivial`.  It BUILDS.  The
       soundness scan (`sorry_scan.py`) scans TOKENS, not statements, so it finds
       nothing.  The audit dutifully prints a clean report.  Every count matches.
       The gate says PASSED and the development proves nothing.

This script closes (ii): it extracts each headline theorem's STATEMENT (binders +
`:` + conclusion, everything up to the top-level `:=` that starts the proof)
straight from the Lean source, normalizes whitespace and comments away, and
compares it byte-for-byte against a checked-in golden.  The PROOF is deliberately
NOT pinned -- refactoring a proof is normal work; changing what is claimed is not.

Scope honesty (state it, or the next reader over-trusts this): the pin is over the
statement's SURFACE SYNTAX.  It catches restatement, weakening, dropped
conclusions and dropped/added hypotheses.  It does NOT catch a statement that is
hollowed out from underneath -- redefining `W4Fragment` to `True` leaves the text
`(hF : W4Fragment S T)` intact.  Nothing short of elaborating and unfolding the
whole development catches that, and `#check`-based pins do not either.  The
independent defences against that shape are the non-vacuity witnesses
(`W4Witness*`, themselves pinned here) and the conformance suite.

Usage:
    python formal/conformance/statement_pin.py            # check against the golden
    python formal/conformance/statement_pin.py --generate # rewrite the golden

Gated by `formal/verify.sh` (the `lean` phase, step 4b).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEAN_ROOT = REPO_ROOT / "formal" / "lean"
PIN = REPO_ROOT / "formal" / "headline_statements.txt"

# The headline theorems, by fully-qualified Lean name.  This list IS the claim
# `formal/FINAL_REVIEW.md` §2 makes in English -- T0a/T0b, T1, T2a, T2b, T3/T6,
# T4, T5, the Phase-6 driver honesty theorems, and the non-vacuity witnesses whose
# whole job is to say the hypothesis bundles are inhabited (a witness restated to
# `True` would be the quietest possible way to make the theorems vacuous again).
# Adding a name here is free; removing one must be a deliberate, reviewed edit.
HEADLINE = [
    # T0a / T0b -- the spec is well-defined
    "Zanzibar.sem_fuel_stable",
    "Zanzibar.stratify_none_iff_cycle",
    "Zanzibar.stratify_topological",
    # T1 -- the set engine computes sem
    "Zanzibar.setEngine_correct",
    # T4 -- closure path-count maintenance
    "Zanzibar.pathCount_addEdge",
    "Zanzibar.pathCount_removeEdge",
    # T5 -- the cascade converges / never aborts at <= 2 strata
    "Zanzibar.runCascade2_no_abort",
    "Zanzibar.cascade2_drains",
    # T2a / T2b / T3 / T6 -- the final graph theorems
    "Zanzibar.graph_correct",
    "Zanzibar.graph_reached_inv",
    "Zanzibar.backend_equivalence",
    "Zanzibar.exclusion_effective",
    "Zanzibar.no_ghost_grant",
    # Phase 6 -- the CLI's graph mode IS the chain
    "Zanzibar.graphRun_reached",
    "Zanzibar.graphRun_check_eq_sem",
    # Non-vacuity: the hypothesis bundles are inhabited by real compiled schemas
    "Zanzibar.W4Witness.accepts",
    "Zanzibar.W4Witness.fragment",
    "Zanzibar.W4Witness.within_scope",
    "Zanzibar.W4WitnessUnion.accepts",
    "Zanzibar.W4WitnessUnion.fragment",
    "Zanzibar.W4WitnessUnion.within_scope",
    "Zanzibar.W4WitnessDirect.accepts",
    "Zanzibar.W4WitnessDirect.fragment",
    "Zanzibar.W4WitnessDirect.within_scope",
    "Zanzibar.W4WitnessDirect.correct_applies",
    "Zanzibar.W4WitnessDirect.outside_old_admission",
]

DECL_RE = re.compile(
    r"^(?:@\[[^\]]*\]\s*)?"
    r"(?:private\s+|protected\s+|noncomputable\s+|nonrec\s+|scoped\s+)*"
    r"(?P<kw>theorem|lemma)\s+(?P<name>[A-Za-z_][A-Za-z0-9_.'!?]*)"
)
NS_RE = re.compile(r"^\s*namespace\s+(?P<name>[A-Za-z_][A-Za-z0-9_.']*)")
# `section` also consumes an `end`, so it must be pushed onto the same stack or a
# sectioned file silently pops a namespace and every later name is mis-qualified.
SECTION_RE = re.compile(r"^\s*section\b")
END_RE = re.compile(r"^\s*end\b")
# A line that begins a new top-level command -- the bound on the statement scan.
STOP_RE = re.compile(
    r"^(?:theorem|lemma|def|abbrev|structure|inductive|instance|opaque|class|"
    r"namespace|end|section|open|import|@\[|/--|/-!|attribute|macro|notation|"
    r"variable|universe|set_option|noncomputable|private|protected|example)\b"
)
OPEN = "([{⟨⦃"
CLOSE = ")]}⟩⦄"


def strip_comments(text: str) -> str:
    """Remove `--` line comments and (nested) `/- -/` blocks."""
    out: list[str] = []
    i, n, depth = 0, len(text), 0
    while i < n:
        if text.startswith("/-", i):
            depth += 1
            i += 2
            continue
        if text.startswith("-/", i) and depth:
            depth -= 1
            i += 2
            continue
        if depth:
            if text[i] == "\n":
                out.append("\n")
            i += 1
            continue
        if text.startswith("--", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def normalize(stmt: str) -> str:
    return " ".join(stmt.split())


def lean_files() -> list[Path]:
    return sorted(
        p
        for p in LEAN_ROOT.rglob("*.lean")
        if not any(part.startswith(".") for part in p.relative_to(LEAN_ROOT).parts)
    )


def extract(path: Path) -> dict[str, str]:
    """Map fully-qualified theorem name -> normalized statement text."""
    text = strip_comments(path.read_text(encoding="utf-8"))
    lines = text.splitlines()
    ns: list[str | None] = []
    found: dict[str, str] = {}
    for idx, line in enumerate(lines):
        m = NS_RE.match(line)
        if m:
            ns.append(m.group("name"))
            continue
        if SECTION_RE.match(line):
            ns.append(None)
            continue
        if END_RE.match(line):
            if ns:
                ns.pop()
            continue
        m = DECL_RE.match(line)
        if not m:
            continue
        prefix = ".".join(x for x in ns if x)
        full = f"{prefix}.{m.group('name')}" if prefix else m.group("name")
        # Scan forward for the top-level `:=` that starts the proof.
        buf: list[str] = [line[m.end("name") :]]
        depth = 0
        end = None
        for k, chunk in enumerate([buf[0]] + lines[idx + 1 :]):
            if k and STOP_RE.match(chunk):
                break
            j = 0
            while j < len(chunk):
                c = chunk[j]
                if c in OPEN:
                    depth += 1
                elif c in CLOSE:
                    depth -= 1
                elif depth == 0 and chunk.startswith(":=", j):
                    end = (k, j)
                    break
                elif (
                    depth == 0
                    and chunk.startswith("where", j)
                    and (j == 0 or not (chunk[j - 1].isalnum() or chunk[j - 1] == "_"))
                    and not chunk[j + 5 : j + 6].isalnum()
                ):
                    # `theorem accepts : GraphAdmission Sx Tx where` -- a structure
                    # instance proof; the statement ends at `where`.
                    end = (k, j)
                    break
                j += 1
            if end is not None:
                if k:
                    buf.append(chunk[: end[1]])
                else:
                    buf = [chunk[: end[1]]]
                break
            if k:
                buf.append(chunk)
        if end is None:
            continue  # not a `... := proof` theorem; leave it unpinned
        found[full] = normalize(" ".join(buf))
    return found


def collect() -> tuple[dict[str, str], dict[str, str]]:
    """Return (name -> statement, name -> file) over the whole Lean tree."""
    stmts: dict[str, str] = {}
    where: dict[str, str] = {}
    dupes: list[str] = []
    for p in lean_files():
        for name, stmt in extract(p).items():
            if name in stmts and name in HEADLINE:
                dupes.append(name)
            stmts[name] = stmt
            where[name] = str(p.relative_to(REPO_ROOT)).replace("\\", "/")
    if dupes:
        print(
            "FAIL: headline theorem name declared in more than one Lean file "
            f"(the pin would be ambiguous): {sorted(set(dupes))}",
            file=sys.stderr,
        )
        sys.exit(1)
    return stmts, where


def read_pin() -> dict[str, str]:
    pinned: dict[str, str] = {}
    if not PIN.is_file():
        return pinned
    for raw in PIN.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        name, _, stmt = raw.partition("\t")
        pinned[name.strip()] = stmt.strip()
    return pinned


HEADER = """\
# formal/headline_statements.txt -- the STATEMENT pin for the headline theorems.
#
# One `<fully-qualified name>\\t<normalized statement>` line per theorem, extracted
# from the Lean sources by formal/conformance/statement_pin.py and enforced by
# formal/verify.sh (the `lean` phase).  The statement is everything between the
# theorem's name and the top-level `:=`, with comments stripped and whitespace
# collapsed.  The PROOF is not pinned -- only what is claimed.
#
# WHY: before this file the gate could not distinguish `theorem graph_correct ... :
# GraphModel.check s q = sem S T q` from `theorem graph_correct : True := trivial`.
# The latter builds, carries no `sorry` token, and audits clean (ZT-P2-5).
#
# REGENERATE DELIBERATELY (a diff here is a change to what the development
# CLAIMS -- it belongs in a commit message and in formal/history/):
#
#     ZANZIBAR_PY=/path/to/python
#     "$ZANZIBAR_PY" formal/conformance/statement_pin.py --generate
#
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true", help="rewrite the golden file")
    args = ap.parse_args()

    stmts, where = collect()

    missing = [n for n in HEADLINE if n not in stmts]
    if missing:
        print(
            "FAIL: headline theorem(s) NOT FOUND in the Lean sources: "
            + ", ".join(missing),
            file=sys.stderr,
        )
        print(
            "      A headline theorem was deleted or renamed. That is a change to the\n"
            "      claim, not a refactor -- update HEADLINE in statement_pin.py and\n"
            "      regenerate the pin deliberately.",
            file=sys.stderr,
        )
        return 1

    if args.generate:
        body = "".join(f"{n}\t{stmts[n]}\n" for n in HEADLINE)
        PIN.write_text(HEADER + body, encoding="utf-8")
        print(f"  wrote {PIN} ({len(HEADLINE)} headline statements)")
        return 0

    pinned = read_pin()
    if not pinned:
        print(f"FAIL: statement pin {PIN} is missing or empty", file=sys.stderr)
        return 1
    # Non-vacuity: the pin must cover every headline name.  An emptied or truncated
    # pin file must FAIL, not silently check nothing (the ZT-P2-1 shape).
    unpinned = [n for n in HEADLINE if n not in pinned]
    if unpinned:
        print(
            "FAIL: the statement pin does not cover: " + ", ".join(unpinned),
            file=sys.stderr,
        )
        return 1

    bad = 0
    for name in HEADLINE:
        if stmts[name] != pinned[name]:
            bad += 1
            print(
                f"FAIL: the STATEMENT of {name} changed ({where[name]}):",
                file=sys.stderr,
            )
            print(f"    pinned: {pinned[name]}", file=sys.stderr)
            print(f"    source: {stmts[name]}", file=sys.stderr)
    if bad:
        print(
            f"      {bad} headline theorem statement(s) differ from "
            "formal/headline_statements.txt.\n"
            "      A theorem now CLAIMS something different from what the pin records.\n"
            "      If that is intended, regenerate the pin deliberately\n"
            "      (statement_pin.py --generate) and say why in formal/history/.",
            file=sys.stderr,
        )
        return 1
    print(f"  headline statement pin: {len(HEADLINE)}/{len(HEADLINE)} statements match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
