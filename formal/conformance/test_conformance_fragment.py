"""**`DW-1` — `W4Fragment` is DECIDED by Lean, and the corpora are held to the verdict.**

Until 2026-09-23d nothing in this repo could say whether a given `(schema, store)` is inside
`W4Fragment`, the hypothesis bundle that scopes every headline theorem.
`test_conformance_graph.py::_THEOREM_BACKED` asserted it for 25 corpora, and all but one of
those assertions were prose arguments in `corpus.py`. That test's own failure message said
*"zcli will NOT tell you"*. Now it does:
`formal/lean/ZanzibarProofs/GraphIndex/FragmentDecide.lean::w4FragmentB`, proved EXACT in
both directions by `w4FragmentB_iff`, is reached through `zcli mode="fragment"`
(`Cli.lean::fragmentJson`, `runner.py::run_fragment`).

What this module pins:

(A) **Every `_THEOREM_BACKED` corpus is inside `W4Fragment`**, by Lean's decider at the
    corpus's own schema and store. Half of the prose argument becomes a machine check. The
    other half, `GraphAdmission`, has no decider (`RewriteRanked` is an existential over rank
    functions) and stays prose.
(B) **The Lean verdict, field by field, on every curated corpus** equals
    `_EXPECTED_FAILURES`. That table was derived INDEPENDENTLY, by the straw-man Python mirror
    `formal/probes/dw1_python_mirror_2026-09-23.py` run over the production AST
    (`docs/dw1-decidable-w4fragment-2026-09-23.md` §2), before the Lean decider existed. The
    two derivations share no code. Lean's `zcli` reads `encode.py`'s oracle-side encoding; the
    mirror reads `zanzibar_utils_v1.parse_schema_ast`.
(C) **Lean's `taintedKeys` equals Python's `compute_taint`** on every curated corpus. This is
    the `isDerived ≡ compute_taint` correspondence, which `CORRESPONDENCE.md` asserted in
    prose and which no test compared until now.

Three corpora are IN `W4Fragment` by Lean's verdict although `corpus.py` prose placed them
outside or left them open: `TTU_USERSET:ttu_fromchain`, `TTU_USERSET:ttu_fromchain_group`
and `SELF_REF:self_flag`. That is the `W4Fragment` half only. None of them is moved into
`GRAPH_FRAGMENT` here, because that also needs the `GraphAdmission` half argued.

SABOTAGE (2026-09-23d, `docs/sabotage-procedure.md`): recorded at the bottom of
`docs/dw1-decidable-w4fragment-2026-09-23.md`, literal output quoted there.
"""
from __future__ import annotations

import pytest

from formal.conformance import runner
from formal.conformance.corpus import (
    GRAPH_FRAGMENT,
    MULTI_STRATUM_SCHEMAS,
    SCHEMAS,
    SELF_REFERENTIAL_SCHEMAS,
    TTU_USERSET_SCHEMAS,
)
from formal.conformance.encode import build_request
from formal.conformance.test_conformance_graph import _DIFFERENTIAL_ONLY, _THEOREM_BACKED

#: Every curated corpus family, keyed `LABEL:name` (names are only unique per family).
_FAMILIES = (
    ("SCHEMAS", SCHEMAS),
    ("MULTI_STRATUM", MULTI_STRATUM_SCHEMAS),
    ("TTU_USERSET", TTU_USERSET_SCHEMAS),
    ("SELF_REF", SELF_REFERENTIAL_SCHEMAS),
)
ALL_CORPORA: dict[str, tuple] = {
    f"{label}:{name}": spec for label, fam in _FAMILIES for name, spec in fam.items()
}

#: Anti-vacuity floor on the corpus sweep. Measured 2026-09-23 with the probe named in
#: the module docstring (`agree=33 disagree=3`, i.e. 36 corpora). A `>=`, so adding a
#: corpus is free; it catches a family import that silently went empty.
MIN_CORPORA = 36

#: The ten `W4Fragment` field names, in declaration order (`FullScope.lean::W4Fragment`).
W4_FIELDS = (
    "computedOrDirect", "directArmsBare", "directArmsConcrete", "computedOnlyOperands",
    "noUnionDirects", "twoStrata", "wsBare", "bareStar", "ttuStarFree", "term",
)

#: The fields each OUT-of-fragment corpus fails, in declaration order. Every corpus not
#: listed is expected to be IN (no failures). Derived by the Python mirror probe
#: (2026-09-23), not by reading zcli's output. The probe's `term.NoStoreSubjectR` column
#: maps to Lean's single `term` field.
_EXPECTED_FAILURES: dict[str, tuple[str, ...]] = {
    "SCHEMAS:derived_userset_subject": ("directArmsBare", "noUnionDirects", "term"),
    "SCHEMAS:object_wildcard": ("bareStar",),
    "MULTI_STRATUM:three_strata_chain": ("twoStrata",),
    "TTU_USERSET:derived_ttu_fromchain": ("computedOrDirect",),
    "TTU_USERSET:derived_tupleset_ttu": ("computedOrDirect",),
    "TTU_USERSET:derived_userset": ("directArmsBare", "noUnionDirects", "term"),
    "TTU_USERSET:wildcard_userset": ("wsBare", "bareStar"),
    "SELF_REF:self_ttu_parent": ("computedOrDirect", "directArmsConcrete", "noUnionDirects"),
}


def _fragment_report(key: str) -> dict:
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")
    schema_text, tuples, obj_wild = ALL_CORPORA[key]
    return runner.run_fragment(build_request(schema_text, tuples, [], obj_wild, mode="fragment"))


def test_corpus_sweep_is_not_vacuous():
    """The sweep covers every curated family, both verdicts occur, and the expectation
    table names only real corpora and real fields."""
    assert len(ALL_CORPORA) >= MIN_CORPORA, (
        f"only {len(ALL_CORPORA)} curated corpora found; floor {MIN_CORPORA}. A corpus "
        f"family import went empty, and a sweep over nothing reports green.")
    stale = sorted(set(_EXPECTED_FAILURES) - set(ALL_CORPORA))
    assert not stale, f"_EXPECTED_FAILURES names corpora that no longer exist: {stale}"
    bad = sorted({f for fs in _EXPECTED_FAILURES.values() for f in fs} - set(W4_FIELDS))
    assert not bad, f"_EXPECTED_FAILURES names non-fields: {bad}"
    n_in = len(ALL_CORPORA) - len(_EXPECTED_FAILURES)
    assert n_in > 0 and _EXPECTED_FAILURES, "need both IN and OUT corpora to discriminate"


@pytest.mark.parametrize("name", sorted(GRAPH_FRAGMENT))
def test_theorem_backed_corpora_are_inside_w4fragment(name):
    """(A) A corpus in `_THEOREM_BACKED` must satisfy `W4Fragment` by Lean's own decider.
    A `_DIFFERENTIAL_ONLY` corpus is exempt: running out-of-scope inputs is that category's
    purpose, and `zcli mode="graph"` deliberately does not refuse them."""
    rep = _fragment_report(f"SCHEMAS:{name}")
    if name in _DIFFERENTIAL_ONLY:
        return
    assert name in _THEOREM_BACKED, f"{name} is in GRAPH_FRAGMENT but unclassified"
    assert rep["inFragment"], (
        f"[{name}] is classified `_THEOREM_BACKED` (test_conformance_graph.py) but Lean's "
        f"decider `FragmentDecide.lean::w4FragmentB` says it is OUTSIDE W4Fragment, "
        f"failing {rep['failures']}. The prose argument in corpus.py is wrong. Move the "
        f"corpus to `_DIFFERENTIAL_ONLY` with this output as its machine-checked citation, "
        f"or fix the corpus. Do NOT edit the decider to agree.")


@pytest.mark.parametrize("key", sorted(ALL_CORPORA))
def test_lean_verdict_matches_the_independent_mirror(key):
    """(B) Lean's per-field verdict equals the independently derived expectation."""
    rep = _fragment_report(key)
    assert set(rep["fields"]) == set(W4_FIELDS), (
        f"[{key}] zcli reported fields {sorted(rep['fields'])}, not the ten W4Fragment "
        f"fields -- the structure or fragmentJson changed; see "
        f"test_w4fragment_scope_pin.py")
    expected = list(_EXPECTED_FAILURES.get(key, ()))
    assert rep["failures"] == expected, (
        f"[{key}] Lean's W4Fragment verdict fails {rep['failures']}, the independent "
        f"Python mirror derivation expected {expected}. One of the two derivations is "
        f"wrong; attribute it (encode.py vs the production parser vs the decider) before "
        f"changing either.")


@pytest.mark.parametrize("key", sorted(ALL_CORPORA))
def test_lean_taint_equals_python_compute_taint(key):
    """(C) `isDerived` (Lean `taintedKeys`) == `zanzibar_utils_v1.compute_taint`."""
    from zanzibar_utils_v1 import compute_taint, parse_schema_ast

    rep = _fragment_report(key)
    lean = {tuple(k) for k in rep["tainted"]}
    assert len(lean) == len(rep["tainted"]), f"[{key}] Lean taintedKeys has duplicates"
    python = set(compute_taint(parse_schema_ast(ALL_CORPORA[key][0])))
    assert lean == python, (
        f"[{key}] derived-relation sets differ: Lean-only {sorted(lean - python)}, "
        f"Python-only {sorted(python - lean)}")
