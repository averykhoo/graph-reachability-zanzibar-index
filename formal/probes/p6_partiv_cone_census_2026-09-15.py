#!/usr/bin/env python
"""P6 PART (iv) -- REVERSE CONE CENSUS (2026-09-15).

`docs/p6-part-iv-plan-2026-09-14.md` section "Corrections appended 2026-09-15 (eighth)",
section "Still not established at this line", second bullet:

    "**Cost of 4'/5' is unmeasured.** `LeafRules.lean:340-345` records `writeRules`' reverse
     cone as 40 modules against `writeBridgedOne`'s 24 (AGENT quote, not re-measured this
     session).  Re-measure before planning 6' -- the census' own numbers came in low twice."

This is that re-measurement, mechanical and re-runnable, so the figure stops being an
unverified agent quote.  Run from the repo root:

    C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe \
        formal/probes/p6_partiv_cone_census_2026-09-15.py

WHY A SCRIPT AND NOT A GREP.  "Reverse cone" is ambiguous, and that ambiguity is exactly
what sent the recorded "40 vs 24" into the tree unqualified.  There are at least four
distinct things it can mean, and they differ by a lot:

  (U1) TRANSITIVE REVERSE IMPORT CLOSURE of the DEFINING MODULE -- every module that
       transitively imports the file the symbol is defined in.  This is an upper bound on
       "what could possibly see it", and it is almost entirely inert: importing a module is
       not using a symbol.
  (U2) MODULES CONTAINING A TEXTUAL REFERENCE to the symbol, word-boundary matched so that
       `writeRules` does not swallow `writeLoggedRules` / `writeRulesRaw` /
       `removeLoggedRules`.  Substring contamination is the single easiest way to inflate
       one of these counts silently.
  (U3) Of those, the ones referencing it OUTSIDE comments and docstrings -- i.e. real code
       and proof sites rather than prose ABOUT the symbol.
  (U4) DECLARATIONS (theorem/lemma/def) whose own text mentions the symbol -- the closest
       mechanical proxy for "sites that would need repair".

A number is reported for each, per symbol, with the unit named.  Do not quote one without
its unit.

INSTRUMENT LIMITS, stated rather than discovered later:
  * Lean comment syntax is handled approximately: `--` to end of line, and `/- ... -/`
    blocks including `/-- ... -/` docstrings, tracked with a nesting counter.  String
    literals containing comment markers would fool it; none are expected in this tree, and
    (U2) is reported alongside (U3) so a divergence between them is visible.
  * (U4) attributes a reference to the nearest PRECEDING declaration header, which is wrong
    for a reference sitting between declarations (e.g. in a section docstring).  It is a
    proxy, not a proof; treat it as a lower bound on repair sites.
  * This measures the CURRENT tree only.  It says nothing about whether a site would still
    typecheck after a swap -- only the kernel can answer that.
"""

import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # formal/
LEAN_ROOT = os.path.join(ROOT, "lean", "ZanzibarProofs")
PKG = "ZanzibarProofs"

DECL_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+|partial\s+)*"
    r"(theorem|lemma|def|abbrev|instance|structure|inductive|class)\s+([^\s:({\[]+)"
)


def strip_comments(text):
    """Return (code_only, full) where code_only blanks Lean comments.

    Keeps line structure so line numbers stay usable.
    """
    out = []
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if depth == 0 and ch == "-" and nxt == "-":
            # line comment: blank to end of line
            j = text.find("\n", i)
            if j == -1:
                j = n
            out.append(" " * (j - i))
            i = j
            continue
        if ch == "/" and nxt == "-":
            depth += 1
            out.append("  ")
            i += 2
            continue
        if ch == "-" and nxt == "/" and depth > 0:
            depth -= 1
            out.append("  ")
            i += 2
            continue
        if depth > 0:
            out.append("\n" if ch == "\n" else " ")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def module_name(path):
    rel = os.path.relpath(path, os.path.dirname(LEAN_ROOT))
    rel = rel[:-5] if rel.endswith(".lean") else rel
    return rel.replace(os.sep, ".")


def load():
    mods = {}
    for dirpath, _dirs, files in os.walk(LEAN_ROOT):
        for f in files:
            if not f.endswith(".lean"):
                continue
            p = os.path.join(dirpath, f)
            with open(p, "r", encoding="utf-8") as fh:
                text = fh.read()
            mods[module_name(p)] = {"path": p, "text": text, "code": strip_comments(text)}
    return mods


IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)", re.M)


def import_graph(mods):
    fwd = {m: set() for m in mods}
    for m, d in mods.items():
        for target in IMPORT_RE.findall(d["code"]):
            if target in mods:
                fwd[m].add(target)
    rev = defaultdict(set)
    for m, deps in fwd.items():
        for dep in deps:
            rev[dep].add(m)
    return fwd, rev


def transitive_importers(rev, start):
    """Every module that transitively imports `start` (excluding `start`)."""
    seen = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        for m in rev.get(cur, ()):
            if m not in seen:
                seen.add(m)
                stack.append(m)
    return seen


def word_re(sym):
    """Word-boundary match for a Lean identifier.

    A reference must not be preceded or followed by an identifier CHARACTER -- that is what
    keeps `writeRules` from matching inside `writeRulesRaw` (trailing `R`).  Substring
    contamination in the other direction is not a risk for these names: `writeLoggedRules`
    and `removeLoggedRules` do not contain `writeRules` at all.

    (!) A preceding `.` MUST be allowed.  These are all `GraphState` methods and are almost
    always written qualified -- `sigma.writeRules S t`, `GraphState.ensureInBridges`.  The
    first draft of this script excluded a preceding `.` and therefore reported ZERO code
    references for `writeRules`, `writeBridgedOne`, `writeRulesRaw` and `ensureInBridges`,
    which reads exactly like "this symbol is only talked about, never used" -- a broken
    harness wearing the costume of a finding.  `check_instrument` below now refuses that
    outcome mechanically.
    """
    return re.compile(r"(?<![A-Za-z0-9_'])" + re.escape(sym) + r"(?![A-Za-z0-9_'])")


def decls_mentioning(text, rx):
    """Declaration names whose body (up to the next declaration) matches rx."""
    lines = text.split("\n")
    cur = None
    hits = set()
    for ln in lines:
        m = DECL_RE.match(ln)
        if m:
            cur = m.group(2)
        if rx.search(ln) and cur:
            hits.add(cur)
    return hits


SYMBOLS = [
    ("writeRules", "GraphIndex.RulesWrite", "the BRIDGE-FREE fold (ReachedByRulesAdmitted's step)"),
    ("writeBridgedOne", "GraphIndex.UsStarWrite", "the bridging write (part (ii))"),
    ("writeRulesRaw", "GraphIndex.LeafRules", "the BRIDGED fold proposed by step 4'"),
    ("ensureInBridges", "GraphIndex.UsStarWrite", "the bridge materialiser"),
    ("ReachedByRulesAdmitted", "GraphIndex.RulesComplete", "the admission predicate needing a twin"),
    ("ShadowOver", "GraphIndex.CascadeStable", "the shadow relation step 5' edits"),
    ("UntaintedShadow", "GraphIndex.CascadeStable", "ShadowOver's three-disjunct instance"),
    ("shadow_graphRec_agree", "GraphIndex.CascadeStable", "the transport lemma"),
]


def check_instrument(mods):
    """M0-style CONTROL: refuse to report if the matcher cannot see the obvious.

    This repo's standing rule (`docs/sabotage-procedure.md`, and the `P6` step-0 lesson of
    2026-09-13) is that a sweep without a control cannot tell a clean module from a broken
    harness.  The concrete failure this guards was real and happened on this script's first
    run: every `GraphState` method reported ZERO code references.

    Two mechanical demands, both of which the first draft failed:
      (i)  every symbol must have at least one CODE reference in its OWN defining module --
           a definition is a reference;
      (ii) the disambiguation must actually discriminate: `writeRules` must NOT match inside
           `writeRulesRaw`, checked on a literal string rather than asserted in a comment.
    """
    problems = []
    for sym, defmod, _note in SYMBOLS:
        key = defmod if defmod in mods else PKG + "." + defmod
        if key not in mods:
            problems.append("(i) defining module missing for %s: %s" % (sym, defmod))
            continue
        if not word_re(sym).search(mods[key]["code"]):
            problems.append(
                "(i) %s has NO code reference in its own defining module %s -- the matcher "
                "is broken, not the tree" % (sym, defmod))
    probe = "  sigma.writeRules S t ; acc.writeRulesRaw S u ; GraphState.writeLoggedRules"
    hits = word_re("writeRules").findall(probe)
    if len(hits) != 1:
        problems.append(
            "(ii) discrimination check failed: `writeRules` matched %d times in the control "
            "string (expected exactly 1 -- the qualified call, not writeRulesRaw and not "
            "writeLoggedRules)" % len(hits))
    return problems


def main():
    mods = load()
    fwd, rev = import_graph(mods)

    problems = check_instrument(mods)
    if problems:
        print("INSTRUMENT CONTROL FAILED -- no numbers reported.")
        print("(A census whose matcher cannot see its own definitions would report a clean")
        print(" tree and mean nothing.  Fix the matcher before reading anything below.)")
        print("")
        for p in problems:
            print("  ! " + p)
        return 1
    print("instrument control: PASSED (every symbol resolves in its defining module;")
    print("                    `writeRules` discriminates against writeRulesRaw/writeLoggedRules)")
    print("")
    print("P6 PART (iv) REVERSE CONE CENSUS -- 2026-09-15")
    print("tree: %d modules under %s" % (len(mods), PKG))
    print("")
    print("UNITS (see module docstring):")
    print("  U1 = transitive reverse IMPORT closure of the defining module (upper bound, mostly inert)")
    print("  U2 = modules with a word-boundary TEXTUAL reference (incl. comments)")
    print("  U3 = modules referencing it in CODE (comments stripped)")
    print("  U4 = DECLARATIONS whose text mentions it (proxy for repair sites; lower bound)")
    print("")
    hdr = "%-26s %-30s %5s %5s %5s %5s" % ("symbol", "defining module", "U1", "U2", "U3", "U4")
    print(hdr)
    print("-" * len(hdr))

    detail = {}
    for sym, defmod, _note in SYMBOLS:
        rx = word_re(sym)
        defmod = defmod if defmod in mods else PKG + "." + defmod
        if defmod not in mods:
            print("%-26s %-30s  MODULE NOT FOUND" % (sym, defmod))
            continue
        u1 = transitive_importers(rev, defmod)
        u2 = {m for m, d in mods.items() if rx.search(d["text"])}
        u3 = {m for m, d in mods.items() if rx.search(d["code"])}
        u4 = 0
        u4mods = {}
        for m, d in mods.items():
            hits = decls_mentioning(d["code"], rx)
            if hits:
                u4 += len(hits)
                u4mods[m] = sorted(hits)
        print("%-26s %-30s %5d %5d %5d %5d" % (sym, defmod.split(".")[-1], len(u1), len(u2), len(u3), u4))
        detail[sym] = {"u1": u1, "u2": u2, "u3": u3, "u4mods": u4mods}

    print("")
    print("=" * 78)
    print("THE RECORDED CLAIM UNDER TEST")
    print("=" * 78)
    print("LeafRules.lean (docstring of GraphState.writeRulesRaw) records, AGENT-sourced and")
    print("marked not re-measured: \"writeRules' reverse cone is 40 modules against")
    print("writeBridgedOne's 24\".  Measured today, by each candidate unit:")
    print("")
    for sym in ("writeRules", "writeBridgedOne"):
        d = detail[sym]
        print("  %-18s U1=%-4d U2=%-4d U3=%-4d  (U4 decls=%d across %d modules)"
              % (sym, len(d["u1"]), len(d["u2"]), len(d["u3"]),
                 sum(len(v) for v in d["u4mods"].values()), len(d["u4mods"])))
    print("")
    print("=" * 78)
    print("CODE-REFERENCE SITES, module by module (U3) -- the actual work surface")
    print("=" * 78)
    for sym, _defmod, note in SYMBOLS:
        if sym not in detail:
            continue
        d = detail[sym]
        print("")
        print("%s  -- %s" % (sym, note))
        if not d["u3"]:
            print("    (no code references)")
        for m in sorted(d["u3"]):
            decls = d["u4mods"].get(m, [])
            shown = ", ".join(decls[:6]) + (" ... (+%d)" % (len(decls) - 6) if len(decls) > 6 else "")
            print("    %-42s %s" % (m.replace(PKG + ".", ""), shown if decls else "(no decl attributed)"))
        comment_only = sorted(d["u2"] - d["u3"])
        if comment_only:
            print("    COMMENT/DOCSTRING ONLY (no code reference):")
            for m in comment_only:
                print("      %s" % m.replace(PKG + ".", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
