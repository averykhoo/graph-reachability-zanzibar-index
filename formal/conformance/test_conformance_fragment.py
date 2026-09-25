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
    corpus's own schema and store. Half of the prose argument becomes a machine check.
    Since `TK104` (2026-09-25) the other half is checked too: (A') in the `GraphAdmission`
    section at the end of this module asserts the WHOLE premise.
(B) **The Lean verdict, field by field, on every curated corpus** equals
    `_EXPECTED_FAILURES`. That table was derived INDEPENDENTLY, by the straw-man Python mirror
    `formal/probes/dw1_python_mirror_2026-09-23.py` run over the production AST
    (`docs/dw1-decidable-w4fragment-2026-09-23.md` §2), before the Lean decider existed. The
    two derivations share no code. Lean's `zcli` reads `encode.py`'s oracle-side encoding; the
    mirror reads `zanzibar_utils_v1.parse_schema_ast`.
(C) **Lean's `taintedKeys` equals Python's `compute_taint`** on every curated corpus. This is
    the `isDerived ≡ compute_taint` correspondence, which `CORRESPONDENCE.md` asserted in
    prose and which no test compared until now.

Since `DW-1` step 3 (2026-09-23e) the module also pins the OPERATOR-FACING report:

(D) **The production `zanzibar_utils_v1.py::w4_fragment_report` equals Lean's decider**,
    per field and on the tainted set, over every curated corpus plus every scope probe.
    The report is a hand-written mirror. This differential is the only thing that stops
    it from saying "covered" where the proof does not.
(E) **The re-created scope-pin probes** (`w4_scope_probes.py::SCOPE_PROBES`) fail exactly
    the fields derived by hand from the Lean definitions, by Lean and by the report.
(F) **The scope pin's ADMITTED / RAISED evidence still holds** for each schema-side probe
    (`PYTHON_OUTCOME`), so a change to a refusal surfaces here and not in a stale docstring.

`test_production_field_list_is_the_lean_structure` ties the report's field list and order
to the fields parsed from `FullScope.lean`. The tuple-carrier surface the differential
cannot see is pinned in `tests/test_w4_fragment_report.py`.

Three corpora are IN `W4Fragment` by Lean's verdict although `corpus.py` prose placed them
outside or left them open: `TTU_USERSET:ttu_fromchain`, `TTU_USERSET:ttu_fromchain_group`
and `SELF_REF:self_flag`. That is the `W4Fragment` half only. None of them is moved into
`GRAPH_FRAGMENT` here, because that also needs the `GraphAdmission` half argued.

Since `TK104` (2026-09-25), `zcli` also decides `GraphAdmission`
(`AdmissionDecide.lean::graphAdmissionB`, EXACT by `graphAdmissionB_iff`), and sections
(G)-(J) at the end of this module hold the corpora, the sizing probes and the REASONED
silent-field mirror to it. Their record is `docs/tk104-graphadmission-scope-2026-09-24.md`.

SABOTAGE (2026-09-23d for (A)-(C), 2026-09-23e for (D)-(F), `docs/sabotage-procedure.md`):
recorded in `docs/dw1-decidable-w4fragment-2026-09-23.md`, literal output quoted there. The
(D)-(F) record is a 19-mutation sweep of the report with an attribution control.
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


# --------------------------------------------------------------------------- #
# (D)-(G): the PRODUCTION report, `DW-1` step 3 (2026-09-23)
# --------------------------------------------------------------------------- #
# `zanzibar_utils_v1.py::w4_fragment_report` is the operator-facing twin of the Lean
# decider. It is a hand-written mirror, so it is held to Lean field for field. On a red,
# fix the PYTHON. The two sides read different parsers (`encode.py` uses the oracle's;
# the report uses the production `parse_schema_ast`), so attribute a red to parser vs
# mirror first.

from formal.conformance.w4_scope_probes import PYTHON_OUTCOME, SCOPE_PROBES  # noqa: E402

#: Anti-vacuity floor on the probe fixtures: 18 on 2026-09-23 (12 schema-side labels from
#: the scope pin's probe, 5 store-side, and 1 added by the mutation sweep). A `>=`, so
#: adding a probe is free.
MIN_SCOPE_PROBES = 18

#: Every input the differential sweeps: all curated corpora plus the scope probes.
DIFFERENTIAL_INPUTS: dict[str, tuple] = {
    **{k: spec for k, spec in ALL_CORPORA.items()},
    **{f"PROBE:{k}": (s, t, ow) for k, (s, t, ow, _exp) in SCOPE_PROBES.items()},
}


def _lean_report(schema_text, tuples, obj_wild) -> dict:
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")
    return runner.run_fragment(build_request(schema_text, tuples, [], obj_wild, mode="fragment"))


def test_production_field_list_is_the_lean_structure():
    """The production report's field list, this module's `W4_FIELDS`, and the fields
    parsed from `FullScope.lean`'s source are one list in one order. A field added to
    the Lean structure must reach the operator report as well as the scope pin."""
    from formal.conformance.test_w4fragment_scope_pin import _live_fields
    from zanzibar_utils_v1 import W4_FRAGMENT_FIELDS

    live = tuple(_live_fields())
    assert len(live) >= 10, f"parsed only {live} from FullScope.lean"
    assert W4_FRAGMENT_FIELDS == live == W4_FIELDS, (
        f"W4Fragment field lists diverge: production {W4_FRAGMENT_FIELDS}, Lean source "
        f"{live}, this module {W4_FIELDS}. A new or reordered field must be decided in "
        f"FragmentDecide.lean, emitted by zcli, and mirrored in w4_fragment_report.")


def test_scope_probes_are_not_vacuous():
    """Every field is the ONLY failure of at least one probe, and at least one probe is
    fully inside, so each field's mirror is exercised in isolation."""
    assert len(SCOPE_PROBES) >= MIN_SCOPE_PROBES, (
        f"only {len(SCOPE_PROBES)} scope probes; floor {MIN_SCOPE_PROBES}")
    isolated = {exp[0] for (_s, _t, _ow, exp) in SCOPE_PROBES.values() if len(exp) == 1}
    missing = [f for f in W4_FIELDS if f not in isolated]
    assert not missing, f"no probe fails ONLY these fields: {missing}"
    assert any(exp == () for (_s, _t, _ow, exp) in SCOPE_PROBES.values())
    assert set(PYTHON_OUTCOME) <= set(SCOPE_PROBES), "PYTHON_OUTCOME names a non-probe"


@pytest.mark.parametrize("key", sorted(DIFFERENTIAL_INPUTS))
def test_production_report_equals_lean(key):
    """(D) The production report == Lean's decider, per field, plus the tainted set."""
    from zanzibar_utils_v1 import w4_fragment_report

    schema_text, tuples, obj_wild = DIFFERENTIAL_INPUTS[key]
    lean = _lean_report(schema_text, tuples, obj_wild)
    py = w4_fragment_report(schema_text, tuples)
    assert dict(py.fields) == lean["fields"], (
        f"[{key}] production w4_fragment_report disagrees with Lean's w4FragmentB on "
        f"{sorted(f for f in W4_FIELDS if dict(py.fields)[f] != lean['fields'][f])}: "
        f"Python fails {list(py.failures)}, Lean fails {lean['failures']}. Fix the "
        f"Python mirror (zanzibar_utils_v1.py, W4Fragment section); Lean is proved exact.")
    assert list(py.failures) == lean["failures"]
    assert py.in_fragment == lean["inFragment"]
    assert py.tainted == {tuple(k) for k in lean["tainted"]}, f"[{key}] tainted sets differ"


@pytest.mark.parametrize("label", sorted(SCOPE_PROBES))
def test_scope_probe_verdict_matches_the_hand_derivation(label):
    """(E) Each re-created scope probe fails exactly the fields derived by hand from the
    Lean definitions (`w4_scope_probes.py`), by Lean AND by the production report."""
    from zanzibar_utils_v1 import w4_fragment_report

    schema_text, tuples, obj_wild, expected = SCOPE_PROBES[label]
    lean = _lean_report(schema_text, tuples, obj_wild)
    assert lean["failures"] == list(expected), (
        f"[{label}] Lean fails {lean['failures']}, hand derivation {list(expected)}")
    assert w4_fragment_report(schema_text, tuples).failures == expected


@pytest.mark.parametrize("label", sorted(PYTHON_OUTCOME))
def test_scope_probe_python_outcome_still_holds(label):
    """(F) The scope pin's LOUD/SILENT evidence, re-run: each schema-side probe is still
    ADMITTED or RAISED by the production compile exactly as the 2026-08-31 probe saw it.
    A change here means `W4FRAGMENT_SCOPE`'s classification needs re-adjudicating."""
    from zanzibar_utils_v1 import UnsupportedByGraphIndex, parse_openfga_schema

    schema_text, _tuples, obj_wild, _exp = SCOPE_PROBES[label]
    try:
        parse_openfga_schema(schema_text, object_wildcard_shapes=frozenset(obj_wild))
        got = "ADMITTED"
    except UnsupportedByGraphIndex:
        got = "RAISED"
    assert got == PYTHON_OUTCOME[label], (
        f"[{label}] the production compile now {got}; the scope pin recorded "
        f"{PYTHON_OUTCOME[label]}. Re-adjudicate test_w4fragment_scope_pin.py's row.")


# --------------------------------------------------------------------------- #
# (G)-(J): the `GraphAdmission` half, `TK104` (2026-09-25)
# --------------------------------------------------------------------------- #
# `AdmissionDecide.lean::graphAdmissionFieldsB`, EXACT by `graphAdmissionB_iff`, reaches
# Python as the `"admission"` key of the same zcli report. These tests hold the curated
# corpora, the `TK104` sizing probes and the REASONED silent-field mirror to it.

from formal.conformance.graphadmission_scope_probes import (  # noqa: E402
    SCHEMA_PROBES as GA_SCHEMA_PROBES,
    SHADOWED as GA_SHADOWED,
    STORE_PROBES as GA_STORE_PROBES,
    silent_admission_failures,
)

#: The fourteen `GraphAdmission` field names, in declaration order
#: (`FullScope.lean::GraphAdmission`).
GA_FIELDS = (
    "wf", "nodup", "strat", "ttuDirect", "matchDecl", "ranked", "objWild", "usWild",
    "storeValid", "ttuNotLeaf", "directRestrNotLeaf", "computedRefsNotLeaf",
    "noLeafSubjects", "keysNonempty",
)

#: The `GraphAdmission` fields each curated corpus fails. Every corpus not listed is
#: expected to be ADMITTED. PREDICTED 2026-09-25 from the `TK104` sizing
#: (`docs/tk104-graphadmission-scope-2026-09-24.md` sec 0) BEFORE zcli could be asked:
#: the LOUD fields cannot fail on a corpus Python compiles and writes, the silent fields
#: were swept by the mirror at 0, so only MIXED silent halves can appear, and only these
#: three corpora carry one. `derived_tupleset_ttu`'s `inherited` reads a derived
#: tupleset (the `ttuDirect` silent half). The two `derived_userset` corpora write a
#: userset subject onto a derived `Direct` arm (the `storeValid` silent half).
_EXPECTED_ADMISSION_FAILURES: dict[str, tuple[str, ...]] = {
    "SCHEMAS:derived_userset_subject": ("storeValid",),
    "TTU_USERSET:derived_userset": ("storeValid",),
    "TTU_USERSET:derived_tupleset_ttu": ("ttuDirect",),
}

#: The `W4Fragment` field that also takes a MIXED field's silent half out of the premise
#: (`graphadmission_scope_probes.py::SHADOWED`, per field rather than per probe).
_SHADOW_FIELD = {"ttuDirect": "computedOrDirect", "storeValid": "directArmsBare"}


def _field_of(label: str) -> str:
    """`<field>/<case>` or `<field>.<half>/<case>` -> `<field>`."""
    return label.split("/", 1)[0].split(".", 1)[0]


def test_admission_expectation_table_is_well_formed():
    stale = sorted(set(_EXPECTED_ADMISSION_FAILURES) - set(ALL_CORPORA))
    assert not stale, f"_EXPECTED_ADMISSION_FAILURES names corpora that do not exist: {stale}"
    bad = sorted({f for fs in _EXPECTED_ADMISSION_FAILURES.values() for f in fs}
                 - set(GA_FIELDS))
    assert not bad, f"_EXPECTED_ADMISSION_FAILURES names non-fields: {bad}"


def test_admission_field_list_is_the_lean_structure():
    """`GA_FIELDS` is the field list parsed from `FullScope.lean`, in order."""
    from formal.conformance.test_graphadmission_scope_pin import _live_fields

    live = tuple(_live_fields())
    assert live == GA_FIELDS, f"GraphAdmission fields: Lean source {live}, this module {GA_FIELDS}"


@pytest.mark.parametrize("key", sorted(ALL_CORPORA))
def test_lean_admission_verdict_matches_the_prediction(key):
    """(G) Lean's per-field `GraphAdmission` verdict on every curated corpus equals the
    prediction made from the sizing, field for field."""
    rep = _fragment_report(key)
    adm = rep["admission"]
    # a set, not a list: Lean's `Json.mkObj` sorts keys, so JSON cannot carry the order.
    # The order is `graphAdmissionFieldsB`'s, and `failures` below is compared as a list.
    assert set(adm["fields"]) == set(GA_FIELDS), (
        f"[{key}] zcli reported admission fields {sorted(adm['fields'])}, not the "
        f"fourteen GraphAdmission fields")
    expected = list(_EXPECTED_ADMISSION_FAILURES.get(key, ()))
    assert adm["failures"] == expected, (
        f"[{key}] Lean's GraphAdmission verdict fails {adm['failures']}, the sizing "
        f"predicted {expected}. If a LOUD field fails, a corpus Python accepts is "
        f"outside a field the sizing classified as a Python refusal: re-adjudicate "
        f"test_graphadmission_scope_pin.py before touching this table.")


@pytest.mark.parametrize("key", sorted(ALL_CORPORA))
def test_no_corpus_is_in_w4fragment_but_outside_admission(key):
    """(H) The shadowing claim, machine-checked on the corpora: a corpus that fails a
    `GraphAdmission` field also fails that field's `W4Fragment` shadow, so the joint
    premise never covers it silently through the other bundle."""
    rep = _fragment_report(key)
    for f in rep["admission"]["failures"]:
        assert f in _SHADOW_FIELD, (
            f"[{key}] fails GraphAdmission.{f}, which has no W4Fragment shadow")
        assert not rep["fields"][_SHADOW_FIELD[f]], (
            f"[{key}] fails GraphAdmission.{f} but passes W4Fragment."
            f"{_SHADOW_FIELD[f]}, its claimed shadow")


def test_theorem_backed_corpora_meet_the_whole_premise():
    """(A') Every `_THEOREM_BACKED` corpus meets BOTH bundles by Lean's deciders, so the
    classification no longer rests on prose for either half."""
    outside = {}
    for name in sorted(GRAPH_FRAGMENT):
        if name in _DIFFERENTIAL_ONLY:
            continue
        rep = _fragment_report(f"SCHEMAS:{name}")
        if not rep["inPremise"]:
            outside[name] = (rep["failures"], rep["admission"]["failures"])
    assert not outside, (
        f"`_THEOREM_BACKED` corpora outside the headline premise by Lean's deciders "
        f"(W4Fragment failures, GraphAdmission failures): {outside}. Move them to "
        f"`_DIFFERENTIAL_ONLY` with this output as the citation. Do NOT edit a decider.")


def _ga_probe_request(label: str) -> str:
    if label in GA_SCHEMA_PROBES:
        schema_text, obj_wild, _ = GA_SCHEMA_PROBES[label]
        return build_request(schema_text, [], [], obj_wild, mode="fragment")
    schema_text, tup, _ = GA_STORE_PROBES[label]
    return build_request(schema_text, [tup], [], (), mode="fragment")


#: Probes the ORACLE-side parser (`tests/oracle.py`, which `encode.py` reads) refuses, so
#: no request can be built and zcli is never asked. Pinned as a set so a parser change
#: surfaces here rather than as a silently shrunk sweep. MEASURED 2026-09-25: the first
#: raises `malformed userset restriction 'group#member.0'` (`tests/oracle.py::
#: _parse_restrictions`), the second the oracle's own empty-name lock (`TK55`). Both
#: fields keep a Lean control in `AdmissionDecide.lean` (`refutes_directRestrNotLeaf`,
#: `refutes_keysNonempty`).
_ORACLE_REFUSES: frozenset[str] = frozenset({
    "directRestrNotLeaf/dotted-restriction-predicate",
    "keysNonempty/empty-relation-name",
})

#: Probes the oracle-side parser ACCEPTS but cannot represent, so the request zcli gets is
#: not the probe. MEASURED 2026-09-25: `tests/oracle.py::parse_schema_ast` keeps the LAST
#: of two `define viewer` lines without complaint, where the production parser raises
#: `duplicate relation definition`. The encoded schema therefore has one key and Lean
#: rightly admits it. Pinned so that fixing the oracle (task row `TK105`) flips this loudly.
#: The Lean side of `nodup` is `AdmissionDecide.lean::refutes_nodup`.
_ORACLE_COLLAPSES: frozenset[str] = frozenset({"nodup/duplicate-define"})


@pytest.mark.parametrize("label", sorted({**GA_SCHEMA_PROBES, **GA_STORE_PROBES}))
def test_lean_admission_fails_each_probes_named_field(label):
    """(I) The sizing's REASONED claim that each probe VIOLATES the field its label names
    is now checked by Lean: a non-control probe fails its field, and a control does not.
    This is independent of what Python did with the probe, which the scope pin checks."""
    try:
        req = _ga_probe_request(label)
    except Exception as exc:  # noqa: BLE001 -- the refusal set is pinned, not tolerated
        assert label in _ORACLE_REFUSES, (
            f"[{label}] the oracle-side parser refuses this probe ({exc!r}); add it to "
            f"_ORACLE_REFUSES only after confirming the refusal is the parser's own")
        return
    assert label not in _ORACLE_REFUSES, f"[{label}] is in _ORACLE_REFUSES but now encodes"
    try:
        runner.zcli_path()
    except runner.ZcliUnavailable:
        pytest.skip("zcli not built (run `lake build zcli` in formal/lean)")
    rep = runner.run_fragment(req)
    field = _field_of(label)
    assert field in GA_FIELDS, f"[{label}] names no GraphAdmission field"
    failing = rep["admission"]["failures"]
    if label in _ORACLE_COLLAPSES:
        assert field not in failing, (
            f"[{label}] the oracle parser no longer collapses this probe (Lean now fails "
            f"{field}). Move it out of _ORACLE_COLLAPSES and close TK105's finding.")
        return
    if "control" in label:
        assert field not in failing, f"[{label}] is an in-scope control but Lean fails {failing}"
    else:
        assert field in failing, (
            f"[{label}] was built to violate GraphAdmission.{field}, but Lean's decider "
            f"says it holds (failures {failing}). The probe does not test its row.")
    if label in GA_SHADOWED:
        assert GA_SHADOWED[label] in rep["failures"], (
            f"[{label}] is SHADOWED by W4Fragment.{GA_SHADOWED[label]}, but Lean says that "
            f"field holds (W4Fragment failures {rep['failures']})")


def _mirror_inputs() -> dict[str, tuple]:
    """Every curated corpus plus every schema probe the production parser accepts."""
    from zanzibar_utils_v1 import parse_schema_ast

    out = {k: (s, t, ow) for k, (s, t, ow) in ALL_CORPORA.items()}
    for label, (s, ow, _) in GA_SCHEMA_PROBES.items():
        try:
            parse_schema_ast(s)
        except ValueError:
            continue
        out[f"GA_PROBE:{label}"] = (s, [], ow)
    return out


#: Floor on `_mirror_inputs()`: 36 corpora + 11 parseable schema probes, 2026-09-25.
MIN_MIRROR_INPUTS = 47


def test_mirror_sweep_is_not_vacuous():
    assert len(_mirror_inputs()) >= MIN_MIRROR_INPUTS


@pytest.mark.parametrize("key", sorted(_mirror_inputs()))
def test_silent_field_mirror_equals_lean(key):
    """(J) `graphadmission_scope_probes.py::silent_admission_failures`, the REASONED hand
    mirror of `matchDecl` and `ranked`, equals Lean's verdict on those two fields. Until
    this test it was pinned only by known answers. On a red, fix the mirror."""
    schema_text, tuples, obj_wild = _mirror_inputs()[key]
    rep = _lean_report(schema_text, tuples, obj_wild)
    lean = tuple(f for f in ("matchDecl", "ranked") if not rep["admission"]["fields"][f])
    assert silent_admission_failures(schema_text) == lean, (
        f"[{key}] mirror says {silent_admission_failures(schema_text)}, Lean says {lean}")
