"""The COUNTS pin — make `FINAL_REVIEW.md`'s headline numbers machine-true.

WHY THIS EXISTS. `ZT-P3-5` (zero-trust review, 2026-07-26) found that *every*
number in *every* claim document was stale and that **nothing gate-enforced any
of them**. It was fixed by hand. It went stale again and was fixed by hand on
2026-07-28 (`7fce0f1`, "refresh stale counts"). It was stale AGAIN on
2026-07-29 — including, both times, `FINAL_REVIEW.md`'s own header block
simultaneously stating two different values for the same quantity, which is the
precise failure it diagnoses in its own text.

Three hand-fixes of the same defect is the repo's signal to stop writing
comments and build a refusal (`docs/sabotage-procedure.md`, "prefer a mechanical
refusal to a doc warning"). So the counts `FINAL_REVIEW.md` publishes are now
GENERATED into a delimited block and CHECKED by `verify.sh`. A count cannot
drift from reality without the gate going red, and the house rule "nothing may
claim more than FINAL_REVIEW" finally binds to something true.

WHAT THIS DOES **NOT** DO, stated plainly so nobody reads it as more than it is:
it pins the numbers inside ONE block in ONE file. Prose counts elsewhere in the
tree are still hand-maintained and can still rot; what changes is that there is
now an authoritative, machine-checked place to check them against. Extending the
block is cheap — add a row to `measure()` — and that is the intended way to bring
another number under the pin.

Usage::

    python -m formal.conformance.doc_counts --check      # gate (verify.sh step 4e)
    python -m formal.conformance.doc_counts --generate   # rewrite the block
    python -m formal.conformance.doc_counts --print      # just show the measurement
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
TARGET = REPO / "formal" / "FINAL_REVIEW.md"

BEGIN = "<!-- BEGIN GENERATED COUNTS (formal/conformance/doc_counts.py) -->"
END = "<!-- END GENERATED COUNTS -->"

#: Conformance files that are gate TOOLING (unit tests of the harness itself),
#: not Lean-vs-Python differentials. Derived counts below split on this set, so a
#: new tooling file must be added here or it inflates the "differential" figure.
TOOLING_FILES = {"test_sorry_scan.py", "test_runner_retry.py"}


def _collect(path: str) -> int:
    """Number of tests pytest collects under `path` (no execution)."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", path, "-q", "--collect-only"],
        cwd=REPO, capture_output=True, text=True)
    m = re.search(r"(\d+) tests? collected", out.stdout)
    if not m:
        raise SystemExit(
            f"doc_counts: could not parse a collection count for {path}.\n"
            f"--- stdout ---\n{out.stdout[-2000:]}\n--- stderr ---\n"
            f"{out.stderr[-2000:]}")
    return int(m.group(1))


def _collect_per_file(directory: pathlib.Path) -> dict[str, int]:
    counts = {}
    for f in sorted(directory.glob("test_*.py")):
        counts[f.name] = _collect(str(f.relative_to(REPO)).replace("\\", "/"))
    return counts


def _verify_sh_floor(name: str) -> int:
    text = (REPO / "formal" / "verify.sh").read_text(encoding="utf-8")
    m = re.search(rf"^{re.escape(name)}=(\d+)", text, re.M)
    if not m:
        raise SystemExit(f"doc_counts: floor {name} not found in formal/verify.sh")
    return int(m.group(1))


def measure() -> dict:
    from formal.conformance.corpus import (
        SCHEMAS, GRAPH_FRAGMENT, TTU_USERSET_SCHEMAS,
        SELF_REFERENTIAL_SCHEMAS, MULTI_STRATUM_SCHEMAS)

    conf_dir = REPO / "formal" / "conformance"
    per_file = _collect_per_file(conf_dir)
    conf_total = _collect("formal/conformance/")
    tests_total = _collect("tests/")

    # Anti-vacuity: the per-file sum MUST equal the directory collection, or the
    # table below is describing a different test set than the gate runs.
    if sum(per_file.values()) != conf_total:
        raise SystemExit(
            f"doc_counts: per-file sum {sum(per_file.values())} != directory "
            f"collection {conf_total}. The generated table would misdescribe the "
            f"gate; refusing to emit it.")

    audit_lean = (REPO / "formal" / "lean" / "ZanzibarProofs" / "Audit.lean"
                  ).read_text(encoding="utf-8")
    audits = len(re.findall(r"^#print axioms ", audit_lean, re.M))

    pinned = len([ln for ln in (REPO / "formal" / "audited_theorems.txt")
                  .read_text(encoding="utf-8").splitlines()
                  if ln.strip() and not ln.startswith("#")])
    def_lines = [ln for ln in (REPO / "formal" / "headline_definitions.txt")
                 .read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.startswith("#")]
    defs_rows = len(def_lines)
    defs_decls = sum(1 for ln in def_lines if ln.startswith("def:"))

    from formal.conformance import anchor_check
    anchors = anchor_check.extract_anchors(
        (REPO / "formal" / "CORRESPONDENCE.md").read_text(encoding="utf-8"))
    n_lean = sum(1 for (_ln, f, _sym) in anchors if f.endswith(".lean"))
    n_py = len(anchors) - n_lean

    tooling = {k: v for k, v in per_file.items() if k in TOOLING_FILES}
    differential = {k: v for k, v in per_file.items() if k not in TOOLING_FILES}

    # The state gate's own blindness, measured rather than asserted (~4-5 s: 23
    # corpora driven through the real graph index). Added 2026-08-05 because this
    # was the ONE number in the tree that quantifies what the differential gate
    # does NOT compare, and it had rotted through two corpus additions while
    # being quoted in three places. See `extractor.projection_ledger`.
    from formal.conformance.extractor import graph_fragment_ledger
    proj = graph_fragment_ledger()

    return {
        "proj": proj,
        "conf_total": conf_total,
        "tests_total": tests_total,
        "repo_total": conf_total + tests_total,
        "per_file": per_file,
        "differential_files": len(differential),
        "differential_tests": sum(differential.values()),
        "tooling_files": len(tooling),
        "tooling_tests": sum(tooling.values()),
        "audits": audits,
        "pinned_audits": pinned,
        "definition_rows": defs_rows,
        "definition_decls": defs_decls,
        "anchors": len(anchors),
        "anchors_py": n_py,
        "anchors_lean": n_lean,
        "schemas": len(SCHEMAS),
        "graph_fragment": len(GRAPH_FRAGMENT),
        "ttu_userset": len(TTU_USERSET_SCHEMAS),
        "self_referential": len(SELF_REFERENTIAL_SCHEMAS),
        "multi_stratum": len(MULTI_STRATUM_SCHEMAS),
        "spec_scope": (len(SCHEMAS) + len(TTU_USERSET_SCHEMAS)
                       + len(SELF_REFERENTIAL_SCHEMAS) + len(MULTI_STRATUM_SCHEMAS)),
        "min_conf_all": _verify_sh_floor("MIN_CONF_ALL"),
        "min_conf_heavy": _verify_sh_floor("MIN_CONF_HEAVY"),
        "min_conf_rest": _verify_sh_floor("MIN_CONF_REST"),
        "min_tests_all": _verify_sh_floor("MIN_TESTS_ALL"),
        "expected_min_audits": _verify_sh_floor("EXPECTED_MIN_AUDITS"),
    }


def render(m: dict) -> str:
    rows = "\n".join(
        f"| `{name}` | {n} | {'tooling' if name in TOOLING_FILES else 'differential'} |"
        for name, n in sorted(m["per_file"].items(), key=lambda kv: (-kv[1], kv[0])))
    return f"""{BEGIN}
<!-- Do not hand-edit. Regenerate:
     python -m formal.conformance.doc_counts --generate
     `verify.sh lean` step 4e fails if this block disagrees with the tree. -->

**Counts — MEASURED, not asserted.** Every number in this block is generated from
the tree and re-checked by `formal/verify.sh` (step 4e). If one is wrong, the gate
is red, not the document. Numbers elsewhere in this file, and in every other doc,
are hand-maintained prose — check them against this block, and prefer moving a
number INTO it over restating it.

| quantity | value |
|---|---|
| `formal/conformance/` collected | **{m['conf_total']}** |
| `tests/` collected | **{m['tests_total']}** |
| whole-repo suite | **{m['repo_total']}** |
| differential conformance tests | **{m['differential_tests']}** across **{m['differential_files']}** files |
| gate-tooling conformance tests | **{m['tooling_tests']}** across **{m['tooling_files']}** files |
| audited theorems (`#print axioms` in `Audit.lean`) | **{m['audits']}** |
| audit identity pin (`audited_theorems.txt`) | **{m['pinned_audits']}** |
| headline definition pin | **{m['definition_rows']}** rows (**{m['definition_decls']}** declarations + ambient) |
| `CORRESPONDENCE.md` anchors | **{m['anchors']}** (**{m['anchors_py']}** Python + **{m['anchors_lean']}** Lean) |
| `corpus.SCHEMAS` | **{m['schemas']}** |
| `corpus.GRAPH_FRAGMENT` (graph-side gates) | **{m['graph_fragment']}** |
| spec-scope corpora (four dicts) | **{m['spec_scope']}** = {m['schemas']} + {m['ttu_userset']} `TTU_USERSET` + {m['self_referential']} `SELF_REFERENTIAL` + {m['multi_stratum']} `MULTI_STRATUM` |
| gate floors (`verify.sh`) | `MIN_CONF_ALL`={m['min_conf_all']} (={m['min_conf_heavy']}+{m['min_conf_rest']}), `MIN_TESTS_ALL`={m['min_tests_all']}, `EXPECTED_MIN_AUDITS`={m['expected_min_audits']} |

**State-gate projection ledger — what the differential gate does NOT compare.**
Driven fresh over all **{m['proj']['corpora']}** `GRAPH_FRAGMENT` corpora through the real graph
index (`extractor.projection_ledger`). Read this as the honest width of the
state-level claim: of the raw `EdgeV4` rows Python writes, only the `compared`
row is checked against Lean. **Do not restate these numbers elsewhere** — three
prose copies rotted through two corpus additions before this became generated.

| edge projection | rows |
|---|---|
| raw `EdgeV4` rows | **{m['proj']['raw']}** |
| dropped by P1 (closure-only) | **{m['proj']['P1']}** |
| dropped by P2 (bridge) | **{m['proj']['P2']}** |
| dropped by P6 (leaf-family copy) | **{m['proj']['P6']}** |
| **compared against Lean** | **{m['proj']['compared']}** |
| raw `NodeV4` rows (all dropped by P5) | **{m['proj']['nodes']}** |
| residue rows kept | **{m['proj']['residues']}** |

Per conformance file:

| file | tests | kind |
|---|---|---|
{rows}

{END}"""


def _extract(text: str) -> str | None:
    i, j = text.find(BEGIN), text.find(END)
    if i == -1 or j == -1:
        return None
    return text[i:j + len(END)]


# --------------------------------------------------------------------------- #
# The prose refusal (added 2026-08-09)
# --------------------------------------------------------------------------- #
# The generated block above fixed `ZT-P3-5` for the numbers INSIDE it. It did
# nothing for the hand-written copies scattered through prose, and on 2026-08-08
# the `rewriteClosure` dedup leg grew `GRAPH_FRAGMENT` 23 -> 25 and left NINE
# stale "23 corpora" claims across five files -- including, in `HANDOFF.md`,
# leg 7's own success criterion. That is the fourth recurrence of the same rot.
#
# The repo's standing rule (HANDOFF.md working-rhythm 3b) is "do not restate
# gate counts in prose". This turns that rule from a request into a refusal.
#
# THE CONTRACT, and it is deliberately permissive about history:
#   * A corpus count that equals a LIVE registry size is fine (it is true).
#   * A corpus count that does NOT is fine ONLY if the line is explicitly marked
#     as a past measurement -- a date plus a pastness word. Dated provenance is
#     valuable and must stay writable; what rots is an undated number that reads
#     as current coverage.
#   * Anything else fails, and the message says which of the two fixes to apply.
# Deleting the number is always available and is the durable fix.

#: Pastness markers. A bare date is NOT enough -- "Measured 2026-07-29 over all
#: 23 corpora" reads as a current claim with a provenance note attached, which is
#: exactly the shape that rotted. The line must also say it is in the past.
_PAST_WORDS = ("then", "was", "were", "had", "historical", "stale", "previously",
               "used to", "at the time", "since moved", "no longer", "superseded")
_DATE_RE = re.compile(r"20\d\d-\d\d-\d\d")

#: `N corpora` / `all N ... corpora`. Only counts phrased about CORPORA -- other
#: doc numbers are out of scope here and belong in the generated block.
#: `(?<![-\d])` is load-bearing, and it is not speculative: the instrument's own
#: first run produced two false positives without it -- "the two 2026-07-28
#: corpora" matched as `28 corpora` (date digits) and `3 corpora x 3 comparisons`
#: matched as a coverage claim when it is arithmetic. Controlling the instrument
#: is as required as controlling the subject (docs/sabotage-procedure.md).
_COUNT_RE = re.compile(
    r"(?<![-\d])(\d+)[- ](?:in-fragment |current |curated |spec-side )?corpora\b",
    re.I)

# ---- SABOTAGE RECORD (docs/sabotage-procedure.md), both RUN 2026-08-09 --------
# Property guarded: "a hand-written corpus count in prose is either LIVE or
# explicitly marked as a past measurement."
#
#   (1) the actual rot class -- append a fresh unmarked live claim:
#         + "The state gate drives all 23 corpora end to end."
#       observed: FAIL: 1 hand-written corpus count(s) ... (ZT-P3-5)
#                 formal/ARCHITECTURE.md:725: '23 corpora' | The state gate
#                 drives all 23 corpora end to end.
#
#   (2) ★ the discriminating one -- the well-meaning copy-edit that deletes the
#       pastness word from a correctly-dated line ("the 23 corpora THEN in the
#       fragment" -> "the 23 corpora in the fragment"):
#         observed: FAIL ... test_conformance_state.py:121: '23 corpora' |
#                   (2026-07-29): across the 23 corpora in the fragment, ...
#       Note the line STILL CARRIES ITS DATE and still fails. That is the whole
#       point of requiring a date AND a pastness word: "measured <date> over all
#       23 corpora" reads as a current claim with provenance attached, and that
#       is the exact shape that rotted four times.
#
# WHAT THIS DOES NOT CATCH, stated rather than left to be discovered:
#   * A stale count that COINCIDES with some live registry size passes. The live
#     set is currently {1, 2, 6, 25, 26, 35}, so e.g. a stale "6 corpora" is
#     invisible. Accepting that keeps the check free of false positives on the
#     several legitimate non-fragment corpus counts in the tree (`test_bulk_build`
#     has its own 6). Narrow it only if a real miss appears.
#   * Counts of anything other than CORPORA. Edge/node/row/test counts belong in
#     the generated block above; this only polices the word "corpora".

#: Files whose corpus counts this refuses to let rot. `history/` is append-only
#: provenance and `FINAL_REVIEW.md` is generated, so both are exempt by design.
_PROSE_GLOBS = ("formal/*.md", "formal/conformance/*.py", "docs/*.md",
                "docs/architecture/*.md", "HANDOFF.md", "CLAUDE.md")


def _live_corpus_counts() -> set[int]:
    """Every count a corpus claim could legitimately be stating, read from the
    registries themselves rather than hand-listed (sabotage-procedure ranking 2)."""
    from formal.conformance.corpus import (
        SCHEMAS, GRAPH_FRAGMENT, MULTI_STRATUM_SCHEMAS, TTU_USERSET_SCHEMAS,
        SELF_REFERENTIAL_SCHEMAS)
    spec_scope = (len(SCHEMAS) + len(TTU_USERSET_SCHEMAS)
                  + len(SELF_REFERENTIAL_SCHEMAS) + len(MULTI_STRATUM_SCHEMAS))
    return {len(SCHEMAS), len(GRAPH_FRAGMENT), len(MULTI_STRATUM_SCHEMAS),
            len(TTU_USERSET_SCHEMAS), len(SELF_REFERENTIAL_SCHEMAS), spec_scope}


def _ascii(t: str) -> str:
    """Console-safe: verify.sh runs under a cp1252 console on this box, and a
    check that CRASHES while reporting is worse than one that stays silent."""
    return t.encode("ascii", "replace").decode("ascii")


def check_corpus_count_prose() -> list[str]:
    """Return one complaint per unmarked, non-live corpus count. Empty == clean."""
    live = _live_corpus_counts()
    bad: list[str] = []
    for glob in _PROSE_GLOBS:
        for path in sorted(REPO.glob(glob)):
            # Exempt: `history/` is append-only provenance, `FINAL_REVIEW.md` is
            # generated, and THIS file necessarily quotes stale numbers while
            # explaining what it refuses. (The first run flagged its own error
            # message — a check that fails on its own documentation.)
            if ("history" in path.parts or path.name == TARGET.name
                    or path.samefile(pathlib.Path(__file__))):
                continue
            rel = path.relative_to(REPO).as_posix()
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for i, line in enumerate(lines, 1):
                for m in _COUNT_RE.finditer(line):
                    n = int(m.group(1))
                    if n in live:
                        continue
                    # Look at the two previous lines too: prose wraps, and the
                    # date or the pastness word routinely lands a line or two
                    # above the number. Measured on the first run — a genuinely
                    # well-marked paragraph in `test_conformance_nary_strata.py`
                    # was flagged because its date sat two lines up.
                    ctx = " ".join(lines[max(0, i - 3):i])
                    low = ctx.lower()
                    if _DATE_RE.search(ctx) and any(w in low for w in _PAST_WORDS):
                        continue
                    bad.append(f"{rel}:{i}: '{m.group(0)}' | {_ascii(line.strip()[:90])}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--generate", action="store_true")
    g.add_argument("--print", dest="show", action="store_true")
    args = ap.parse_args()

    m = measure()
    block = render(m)

    if args.show:
        print(block)
        return 0

    text = TARGET.read_text(encoding="utf-8")
    current = _extract(text)

    if args.generate:
        if current is None:
            raise SystemExit(
                f"doc_counts: no generated-counts block found in {TARGET.name}. "
                f"Insert the marker pair first:\n  {BEGIN}\n  {END}")
        TARGET.write_text(text.replace(current, block), encoding="utf-8")
        print(f"doc_counts: regenerated the counts block in {TARGET.name}")
        return 0

    # --check
    if current is None:
        print(f"FAIL: {TARGET.name} has no generated-counts block. It is the "
              f"governing claim document; its headline counts must be machine-"
              f"checked. Run --generate after inserting the markers.")
        return 1
    if current != block:
        print(f"FAIL: {TARGET.name}'s generated counts DISAGREE with the tree.")
        print("      The document is stale (or someone hand-edited the block).")
        print("      Regenerate deliberately:")
        print("        python -m formal.conformance.doc_counts --generate")
        cur = current.splitlines()
        new = block.splitlines()
        for k in range(max(len(cur), len(new))):
            a = cur[k] if k < len(cur) else "<absent>"
            b = new[k] if k < len(new) else "<absent>"
            if a != b:
                print(f"      doc:  {a}")
                print(f"      tree: {b}")
        return 1
    stale = check_corpus_count_prose()
    if stale:
        print(f"FAIL: {len(stale)} hand-written corpus count(s) in prose that are "
              f"neither live nor marked as past measurements (ZT-P3-5).")
        print(f"      Live registry sizes are {sorted(_live_corpus_counts())}.")
        print("      Fix EITHER way — both are accepted, the first is durable:")
        print("        (a) delete the number: 'every `GRAPH_FRAGMENT` corpus', and")
        print("            point at FINAL_REVIEW.md's generated block for figures;")
        print("        (b) if it is a PAST measurement, say so on the line - a date")
        print("            AND a pastness word ('measured 2026-07-29, over the 23")
        print("            corpora THEN in the fragment'). A bare date is not enough:")
        print("            'measured <date> over all 23 corpora' still reads as a")
        print("            current coverage claim, which is the shape that rots.")
        for s in stale:
            print(f"      {s}")
        return 1
    print(f"  FINAL_REVIEW.md counts: {m['conf_total']} conf / {m['tests_total']} "
          f"tests / {m['audits']} audits / {m['anchors']} anchors — all match the tree")
    print(f"  corpus-count prose: 0 stale claim(s) across {len(_PROSE_GLOBS)} "
          f"path globs (live sizes {sorted(_live_corpus_counts())})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
