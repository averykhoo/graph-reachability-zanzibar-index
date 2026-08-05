#!/usr/bin/env python3
"""Statement + definition pin for the headline theorems (ZT-P2-5, ZT-P5-LEG0).

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

THE SECOND ATTACK, AND THE SECOND PIN (added 2026-07-27).  The paragraph above
used to end by CONCEDING the next attack:

    "It does NOT catch a statement that is hollowed out from underneath --
     redefining `W4Fragment` to `True` leaves the text `(hF : W4Fragment S T)`
     intact."

That concession was the hole.  `graph_correct`'s scope is carried entirely by
`(hA : GraphAdmission S T) (hF : W4Fragment S T)`, recorded BY NAME.  Both are
`structure`s.  Delete `W4Fragment.twoStrata` -- one line -- and `graph_correct`
claims something strictly weaker over a strictly larger class of schemas while
its pinned statement line stays BYTE-IDENTICAL.  The audit-identity pin (4a) does
not fire either: no declaration name changed.  The same hole existed for every
other named definition in the 26 statements, `sem` and `GraphModel.check`
included -- and `check := sem` is the exact model the project's own honesty norm
(`formal/HANDOFF.md` house rule 1) names as forbidden.

So this script now runs TWO pins:

  * the STATEMENT pin (`formal/headline_statements.txt`) -- what the 26 headline
    theorems claim, verbatim; and
  * the DEFINITION pin (`formal/headline_definitions.txt`) -- the full text of
    every project declaration those statements DEPEND ON, transitively, together
    with the ambient `variable` / `open` context of the files that host them.

RECURSION DEPTH, AND WHY.  The definition pin recurses to the TRANSITIVE CLOSURE
of names declared inside `formal/lean/ZanzibarProofs/**`, with no depth cap.  The
justification is measurement, not taste:

  * The closure TERMINATES INSIDE THE PROJECT.  Resolution only ever succeeds for
    a name this development declares; `List.foldl`, `Nat.le`, `Finset`, every
    Mathlib and core lemma resolves to nothing and stops the walk.  Measured
    2026-07-27: 58 declarations at depth 1, then 36 / 17 / 5 / 7 / 3 / 3 / 2 / 1,
    converging at depth 9 to 132 declarations and ~28 KB -- about a third of the
    365 declarations in the tree, not "half the tree" and not unbounded.
  * The deep levels DO NOT CHURN.  Replaying the pin against three earlier
    revisions of the most active fortnight this tree has had (34 commits touching
    `formal/lean/`): from `dc505fd` (2026-07-13) the full closure would have
    fired 12 times, from `de93853` (2026-07-18) 5 times, from `b91d488`
    (2026-07-20) 0 times -- and in ALL THREE cases levels 3..9 contributed ZERO
    additional firings over levels 1-2.  The unbounded pin therefore costs the
    same maintenance as a depth-2 pin and covers 38 more definitions.
  * Every firing that WOULD have happened was a real change of modelled meaning:
    `W4Fragment` (the `RootBoolean` widening), `Delta` (the `leaf` provenance
    tag), `affectedKeys` (the 2026-07-20c own-key model fix), `StoreValidRulesD`.
    Those are exactly the edits `CLAUDE.md` says must not drift unrecorded.

WHERE IT STOPS, AND WHAT IS CONSEQUENTLY STILL INVISIBLE.  Say it plainly; this
is one level deeper, not a proof of anything:

  1. THE PROJECT BOUNDARY.  The walk stops at names this repo does not declare.
     A change in the pinned Mathlib/Lean toolchain that alters what `List.erase`,
     `Finset.sum` or `Decidable` MEAN is invisible here.  (`lakefile`/`lean-
     toolchain` pinning is what covers that, not this file.)
  2. SURFACE SYNTAX, STILL.  Two textually different declarations can be
     definitionally equal, and two textually identical ones can mean different
     things under a different `open`/instance environment.  The ambient section
     pins `variable` and `open` lines for the hosting files, which closes the
     `variable {V} [Fintype V]` shape of that attack -- it does NOT close a
     changed `instance` elsewhere in the tree, an `attribute` change, or a
     `macro`/`notation` redefinition (there are none in the tree today; if
     someone adds one, this pin will not see it).
  3. STRUCTURE FIELDS ARE COMPARED AS TEXT PLUS A NAME LIST.  A field whose TYPE
     is hollowed out is caught only because the hollowed type is itself a pinned
     declaration -- i.e. by rule (0) above, not by anything special about fields.
  4. NOTHING HERE ELABORATES ANYTHING.  A definition that is vacuous on its own
     terms -- satisfiable by nothing, or trivially satisfiable by everything --
     passes this pin with its text intact.  That remains the job of the
     non-vacuity witnesses (`W4Witness*`, pinned as statements above) and of the
     conformance suite, which compares ANSWERS rather than syntax.

The PROOFS are deliberately not pinned, in either pin: refactoring a proof is
normal work; changing what is claimed, or what the claim's words mean, is not.

Usage:
    python formal/conformance/statement_pin.py            # check both goldens
    python formal/conformance/statement_pin.py --generate # rewrite both goldens

Gated by `formal/verify.sh` (the `lean` phase, steps 4b and 4c).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEAN_ROOT = REPO_ROOT / "formal" / "lean"
PIN = REPO_ROOT / "formal" / "headline_statements.txt"
DEF_PIN = REPO_ROOT / "formal" / "headline_definitions.txt"

# Floor on the DEFINITION pin, so gutting the golden cannot make it vacuously
# green (the ZT-P2-1 shape, one level down -- exactly the failure the audit
# identity pin's MIN_PINNED_AUDITS exists to stop).  Measured 2026-07-27: 132
# declarations + 7 ambient entries = 139 rows.  Asserted with >=, so a leg that
# ADDS a definition to the closure never trips it; a leg that REMOVES one must
# lower this deliberately and say why.  `formal/verify.sh` asserts the same floor
# against the file independently (belt and suspenders, as for the audit pin).
MIN_PINNED_DEFS = 139

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
    # ...and the op-driver (removes) sibling.  Added 2026-08-05 (leg 5): it takes the
    # same two bundles and was axiom-printed but NOT statement-pinned, so restating it
    # to `True` was invisible here.  Nothing to do with leg 5's content; a gap the leg
    # tripped over while inventorying the bundle consumers.
    "Zanzibar.graphRunOps_check_eq_sem",
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
    # The E-chain widening's per-leg instruments.  Legs 3/4 landed these (they are
    # what catches a `_d` packaging whose hypotheses are jointly unsatisfiable) but
    # never pinned their statements -- same "quietest possible way" hole the comment
    # above describes.  Added 2026-08-05 with leg 5.
    "Zanzibar.W4WitnessDirect.coverage_applies",
    "Zanzibar.W4WitnessDirect.toC_applies",
    "Zanzibar.W4WitnessDirect.w3d2E_correct_applies",
    # Leg 5 -- the HEADLINE bundles inhabited at `can_view: [user] but not blocked`.
    # `final_applies` is the unsuffixed `graph_correct` at that store; it is the ONLY
    # declaration in the tree that distinguishes the real widening from a half-done
    # one that compiles, audits clean and regenerates both goldens (see its docstring
    # for the observed sabotage output).  `outside_narrow_t2a` is the machine-checked
    # counterexample keeping the T2a asymmetry declared rather than silent.
    "Zanzibar.W4WitnessDirect.admission",
    "Zanzibar.W4WitnessDirect.w4fragment",
    "Zanzibar.W4WitnessDirect.final_applies",
    "Zanzibar.W4WitnessDirect.outside_narrow_t2a",
    # Leg 6 -- the same two bundles at `Td4`, the `direct_arm_exclusion` corpus store
    # VERBATIM rather than the one-tuple minimal store.  `final_applies4` is what
    # licenses `test_conformance_graph._THEOREM_BACKED` to carry that corpus: the
    # bundles are store-indexed, so a witness at a subset store would not establish
    # what that classification asserts.  Restating any of these to `True` would
    # silently un-earn the reclassification.
    "Zanzibar.W4WitnessDirect.outside_old_admission4",
    "Zanzibar.W4WitnessDirect.admission4",
    "Zanzibar.W4WitnessDirect.w4fragment4",
    "Zanzibar.W4WitnessDirect.final_applies4",
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


# --------------------------------------------------------------------------- #
# The DEFINITION pin.  Everything below closes the hole the docstring describes:
# a headline statement's words are only worth what the definitions behind them
# mean, and those could be changed without changing a single pinned character.
# --------------------------------------------------------------------------- #

# A declaration whose MEANING is what the headline statements are made of.
# `theorem`/`lemma` are deliberately absent: a proved fact cannot weaken a
# statement that mentions it (it has no computational or propositional content
# the statement reads).  `instance` IS included -- an instance body can change
# what a `[Fintype V]`-style binder resolves to.
DEF_KW = "structure|class|inductive|def|abbrev|instance"
DEF_RE = re.compile(
    r"^(?:@\[[^\]]*\]\s*)?"
    r"(?:private\s+|protected\s+|noncomputable\s+|nonrec\s+|scoped\s+|partial\s+|unsafe\s+)*"
    rf"(?P<kw>{DEF_KW})\s+(?P<name>[A-Za-z_][A-Za-z0-9_.'!?]*)"
)
# Same bound as STOP_RE, MINUS `deriving`: a `deriving DecidableEq, Repr` line
# belongs to the declaration above it and is part of what that type means.
DEF_STOP_RE = re.compile(
    r"^(?:theorem|lemma|def|abbrev|structure|inductive|instance|opaque|class|"
    r"namespace|end|section|open|import|@\[|/--|/-!|attribute|macro|notation|"
    r"variable|universe|set_option|noncomputable|private|protected|example)\b"
)
# The ambient context of a file: binders injected into every declaration after
# them (`variable`) and the namespaces a bare name is resolved against (`open`).
# Neither appears in a declaration's own text, and both change what it means.
AMBIENT_RE = re.compile(r"^(?:variable|open)\b")
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.'!?]*")
FIELD_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_'!?]*)\b")
CTOR_RE = re.compile(r"\|\s*([A-Za-z_][A-Za-z0-9_'!?]*)")


def _members(kind: str, lines: list[str]) -> list[str]:
    """Field names of a structure/class, or constructor names of an inductive.

    Pulled out separately from the text so a failure can NAME the field that was
    added or removed -- `W4Fragment.twoStrata` deleted must read as
    "REMOVED field(s): twoStrata", not as an unreadable one-line text diff.
    """
    if kind == "inductive":
        # `| plain | wAny | wAll` is legal on ONE line, so scan each line for all
        # of them rather than matching only at the start.
        return [m.group(1) for ln in lines for m in CTOR_RE.finditer(ln)]
    if kind not in ("structure", "class"):
        return []
    # Fields start after the top-level `where`; continuation lines of a field's
    # type are indented DEEPER than the field, so "at the first field's indent"
    # identifies exactly the field starts.
    body: list[str] = []
    seen_where = False
    for ln in lines:
        if not seen_where:
            if re.search(r"\bwhere\b", ln):
                seen_where = True
                tail = ln.split("where", 1)[1]
                if tail.strip():
                    body.append("  " + tail.strip())
            continue
        body.append(ln)
    if not body:
        return []
    # A trailing `deriving ...` sits at column 0, so it must be excluded BEFORE
    # taking the minimum -- otherwise the base indent is 0, no real field matches
    # it, and the field list comes back empty (silently defeating the whole point).
    cand = [
        (len(m.group(1)), m.group(2))
        for ln in body
        if ln.strip() and (m := FIELD_RE.match(ln)) and m.group(2) != "deriving"
    ]
    cand = [(i, n) for i, n in cand if i > 0]
    if not cand:
        return []
    base = min(i for i, _ in cand)
    return [n for i, n in cand if i == base]


def index_definitions() -> tuple[dict[str, tuple[str, str, list[str]]], dict[str, str]]:
    """(name -> (kind, normalized text, members), relpath -> ambient text)."""
    defs: dict[str, tuple[str, str, list[str]]] = {}
    ambient: dict[str, str] = {}
    for p in lean_files():
        rel = str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        text = strip_comments(p.read_text(encoding="utf-8"))
        lines = text.splitlines()
        amb = [normalize(ln) for ln in lines if AMBIENT_RE.match(ln)]
        if amb:
            ambient[rel] = " ; ".join(amb)
        ns: list[str | None] = []
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
            m = DEF_RE.match(line)
            if not m:
                continue
            buf = [line]
            for chunk in lines[idx + 1:]:
                if DEF_STOP_RE.match(chunk):
                    break
                buf.append(chunk)
            prefix = ".".join(x for x in ns if x)
            full = f"{prefix}.{m.group('name')}" if prefix else m.group("name")
            defs[full] = (m.group("kw"), normalize(" ".join(buf)),
                          _members(m.group("kw"), buf))
    return defs, ambient


def _resolve(tok: str, defs: dict[str, tuple[str, str, list[str]]]) -> str | None:
    """Best-effort name resolution for a token appearing in Lean source text.

    Everything in the development lives in `namespace Zanzibar`, so a bare `Inv`
    means `Zanzibar.Inv`; a projection like `Variant.plain` names the type
    `Zanzibar.Variant`.  Resolution FAILING is what stops the walk at the project
    boundary (docstring rule 1) -- `List.foldl` matches nothing and is dropped.
    Over-resolution (a binder that happens to share a declaration's name) only
    ever pins something extra, which is harmless; UNDER-resolution is the risk,
    and is why the walk is unbounded rather than truncated.
    """
    for cand in (f"Zanzibar.{tok}", tok, f"Zanzibar.{tok.split('.')[0]}"):
        if cand in defs:
            return cand
    return None


def definition_closure(
    stmts: dict[str, str], defs: dict[str, tuple[str, str, list[str]]]
) -> tuple[dict[str, int], list[int]]:
    """Transitive closure of project declarations reachable from the statements.

    Returns (name -> depth at which it was first reached, per-level sizes).
    """
    seen: dict[str, int] = {}
    frontier = {
        r for n in HEADLINE for t in IDENT_RE.findall(stmts[n])
        if (r := _resolve(t, defs))
    }
    sizes: list[int] = []
    depth = 1
    while frontier:
        sizes.append(len(frontier))
        for r in frontier:
            seen[r] = depth
        nxt = set()
        for k in frontier:
            for t in IDENT_RE.findall(defs[k][1]):
                r = _resolve(t, defs)
                if r and r not in seen:
                    nxt.add(r)
        frontier = nxt
        depth += 1
    return seen, sizes


def build_definition_pin() -> dict[str, str]:
    """The rows the definition golden must contain, in stable order.

    Two kinds of row:
      `def:<name>`     -> the declaration's full normalized text, prefixed by its
                          member (field / constructor) list when it has one.
      `ambient:<path>` -> the `variable` / `open` lines of a file that hosts at
                          least one pinned declaration or headline theorem.
    """
    stmts, where = collect()
    missing = [n for n in HEADLINE if n not in stmts]
    if missing:
        raise SystemExit("FAIL: headline theorem(s) not found: " + ", ".join(missing))
    defs, ambient = index_definitions()
    seen, _ = definition_closure(stmts, defs)
    rows: dict[str, str] = {}
    hosts = {where[n] for n in HEADLINE}
    for name in sorted(seen):
        kind, text, members = defs[name]
        rows[f"def:{name}"] = (
            f"[{kind}] fields=({' '.join(members)}) {text}" if members
            else f"[{kind}] {text}"
        )
    # Locate the hosting file of each pinned declaration, for the ambient rows.
    for p in lean_files():
        rel = str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        if rel in ambient and (rel in hosts or _hosts_pinned(p, seen)):
            rows[f"ambient:{rel}"] = ambient[rel]
    return rows


def _hosts_pinned(path: Path, seen: dict[str, int]) -> bool:
    text = strip_comments(path.read_text(encoding="utf-8"))
    ns: list[str | None] = []
    for line in text.splitlines():
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
        m = DEF_RE.match(line)
        if not m:
            continue
        prefix = ".".join(x for x in ns if x)
        full = f"{prefix}.{m.group('name')}" if prefix else m.group("name")
        if full in seen:
            return True
    return False


def read_rows(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    if not path.is_file():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        key, _, val = raw.partition("\t")
        rows[key.strip()] = val.strip()
    return rows


FIELDS_RE = re.compile(r"fields=\(([^)]*)\)")


def _field_delta(pinned: str, live: str) -> str:
    """A human-readable field/constructor delta, so a failure NAMES the field."""
    mp, ml = FIELDS_RE.search(pinned), FIELDS_RE.search(live)
    if not mp or not ml:
        return ""
    was, now = mp.group(1).split(), ml.group(1).split()
    gone = [f for f in was if f not in now]
    new = [f for f in now if f not in was]
    bits = []
    if gone:
        bits.append("REMOVED field(s)/constructor(s): " + ", ".join(gone))
    if new:
        bits.append("ADDED field(s)/constructor(s): " + ", ".join(new))
    return "; ".join(bits)


DEF_HEADER = """\
# formal/headline_definitions.txt -- the DEFINITION pin: what the headline
# theorems' WORDS MEAN.
#
# The statement pin (formal/headline_statements.txt) records `(hF : W4Fragment S T)`
# BY NAME.  Delete the `twoStrata` field from `structure W4Fragment` and
# `graph_correct` claims something strictly weaker over a strictly larger class of
# schemas -- while its pinned statement line stays byte-identical and no
# declaration name changes, so neither the statement pin nor the audit identity
# pin fires.  This file closes that: it pins the full text of every project
# declaration the 26 headline statements depend on, TRANSITIVELY, plus the ambient
# `variable` / `open` context of the files that host them.
#
# Rows:
#   def:<name>       [<kind>] fields=(<field/ctor names>) <normalized declaration text>
#   ambient:<path>   the file's `variable` / `open` lines, in order
#
# The closure is unbounded WITHIN THE PROJECT and stops at the project boundary
# (Mathlib/core names resolve to nothing).  Measured 2026-07-27: it converges at
# depth 9 to 132 declarations.  Depth, churn measurements and -- importantly --
# what this pin still CANNOT see are documented in
# formal/conformance/statement_pin.py's module docstring.  Read that before
# trusting this file for more than it claims.
#
# REGENERATE DELIBERATELY (a diff here is a change to what the development's
# claims MEAN -- it belongs in a commit message and in formal/history/):
#
#     ZANZIBAR_PY=/path/to/python
#     "$ZANZIBAR_PY" formal/conformance/statement_pin.py --generate
#
"""


def check_definitions() -> int:
    live = build_definition_pin()
    pinned = read_rows(DEF_PIN)
    if not pinned:
        print(f"FAIL: definition pin {DEF_PIN} is missing or empty", file=sys.stderr)
        return 1
    if len(pinned) < MIN_PINNED_DEFS:
        print(
            f"FAIL: {DEF_PIN} lists only {len(pinned)} row(s); floor is "
            f"{MIN_PINNED_DEFS}.\n"
            "      The pin itself was gutted -- checking a truncated golden passes\n"
            "      vacuously, which is the very failure mode this closes.",
            file=sys.stderr,
        )
        return 1

    gone = sorted(set(pinned) - set(live))
    added = sorted(set(live) - set(pinned))
    bad = 0
    if gone:
        bad += len(gone)
        print(
            "FAIL: pinned definition(s) NO LONGER reachable from the headline\n"
            "      statements (deleted, renamed, or the statement stopped\n"
            "      mentioning them -- all three change what is claimed):",
            file=sys.stderr,
        )
        for k in gone[:30]:
            print(f"        {k}", file=sys.stderr)
    if added:
        bad += len(added)
        print(
            "FAIL: definition(s) now reachable from the headline statements but\n"
            "      NOT in the pin (the meaning of a claim grew a new dependency):",
            file=sys.stderr,
        )
        for k in added[:30]:
            print(f"        {k}", file=sys.stderr)
    for key in sorted(set(live) & set(pinned)):
        if live[key] != pinned[key]:
            bad += 1
            print(f"FAIL: the DEFINITION of {key} changed:", file=sys.stderr)
            delta = _field_delta(pinned[key], live[key])
            if delta:
                print(f"    >>> {delta}", file=sys.stderr)
            print(f"    pinned: {pinned[key]}", file=sys.stderr)
            print(f"    source: {live[key]}", file=sys.stderr)
    if bad:
        print(
            f"      {bad} definition-pin discrepancy(ies) against "
            "formal/headline_definitions.txt.\n"
            "      A headline theorem's STATEMENT may be byte-identical and still\n"
            "      claim something different, because a definition it names now\n"
            "      MEANS something different. If that is intended, regenerate the\n"
            "      pin deliberately (statement_pin.py --generate), say why in\n"
            "      formal/history/, and re-check the FINAL_REVIEW.md claim wording.",
            file=sys.stderr,
        )
        return 1
    print(
        f"  headline definition pin: {len(live)}/{len(pinned)} definitions match "
        f"(floor {MIN_PINNED_DEFS})"
    )
    return 0


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
        rows = build_definition_pin()
        dbody = "".join(f"{k}\t{rows[k]}\n" for k in sorted(rows))
        DEF_PIN.write_text(DEF_HEADER + dbody, encoding="utf-8")
        print(f"  wrote {DEF_PIN} ({len(rows)} definitions/ambient contexts)")
        if len(rows) < MIN_PINNED_DEFS:
            print(
                f"WARNING: only {len(rows)} rows, below the MIN_PINNED_DEFS floor of "
                f"{MIN_PINNED_DEFS} -- lower the floor deliberately or the gate will "
                "reject this golden.",
                file=sys.stderr,
            )
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
    # The second pin: the statements' words are only worth what their definitions
    # mean.  Run it even when the statements matched -- especially then, because a
    # weakening from underneath is precisely the change that leaves them matching.
    return check_definitions()


if __name__ == "__main__":
    sys.exit(main())
