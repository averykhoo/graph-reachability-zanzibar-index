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
    print(f"  FINAL_REVIEW.md counts: {m['conf_total']} conf / {m['tests_total']} "
          f"tests / {m['audits']} audits / {m['anchors']} anchors — all match the tree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
