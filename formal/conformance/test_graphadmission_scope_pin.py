"""**The `GraphAdmission` SCOPE pin -- the other half of the headline premise, classified.**

Every headline theorem takes `(hA : GraphAdmission S T) (hF : W4Fragment S T)`.
`test_w4fragment_scope_pin.py` classifies the `W4Fragment` half. This module does the same
for `structure GraphAdmission` (`formal/lean/ZanzibarProofs/FullScope.lean::GraphAdmission`),
whose docstring calls it *"hypotheses the Python compiler/write admission guarantee for
EVERY accepted schema and store"*. Until 2026-09-24 that sentence was the only evidence. The
`DW-1` plan repeated it as "largely mirrored by Python compile and write refusals" and marked
it UNVERIFIED (`docs/dw1-decidable-w4fragment-2026-09-23.md` sec 1). Board row `TK104`.

The design is `test_w4fragment_scope_pin.py`'s, reused, including its field parser:
`GRAPHADMISSION_SCOPE` is HAND-MAINTAINED (a new Lean field cannot arrive with a blank cell)
and the live field list is PARSED from the Lean source, so the two sides have independent
derivations. The classification vocabulary is the same (LOUD / SILENT / MIXED: *if I hand
the real Python a schema/store outside this field, do I find out?*).

What this module adds over the `W4Fragment` pin, because the classification is only as good
as its evidence:

* **Every row is TIED to re-runnable probes** (`graphadmission_scope_probes.py`), and the
  tie is mechanical: a LOUD row's probes must all RAISE, a SILENT row's must all be
  ADMITTED, and a MIXED row needs one of each. Re-classifying a row without new evidence is
  a red test, and so is a Python refusal that quietly goes away.
* **A MIXED row names the `W4Fragment` field that shadows its SILENT half** (`shadowed_by`),
  and that claim is checked on the probes through `zanzibar_utils_v1.py::w4_fragment_report`,
  which is differential-pinned to Lean's decider. So "SILENT here, but the joint premise
  still excludes it" is a measurement, not a comment.

---------------------------------------------------------------------------
THE FINDING (2026-09-24)
---------------------------------------------------------------------------
LOUD 10, MIXED 2, SILENT 2. The docstring's claim is MOSTLY true, and where it is false the
gap is narrow and named:

* The two MIXED rows (`ttuDirect`, `storeValid`) are silent only on inputs that ALSO fail a
  `W4Fragment` field (`computedOrDirect`, `directArmsBare`), which the report surfaces. The
  joint premise therefore never silently covers them.
* The two SILENT rows are the whole of the unreported surface of the premise:
  - `matchDecl` -- a DANGLING reference (a computed ref, or a TTU tupleset, naming an
    undeclared relation). Python checks only the '.' lock on referenced names
    (`zanzibar_utils_v1.py::_validate_ast_references`), never declared-ness.
  - `ranked` -- an UNTAINTED computed CYCLE (`a: [user] or b`, `b: [user] or a`).
    `Spec/Stratify.lean`'s header says Python allows it on purpose: *"untainted relations
    may be positively recursive; the closure handles them"*. TTU recursion (nested
    folders) is NOT excluded: a tupleset def is direct-only (`ttuDirect`), so it emits no
    rule and a TTU edge cannot close a cycle (REASONED; pinned on one control probe).
* A REASONED Python mirror of those two fields finds ZERO violations across all 36 curated
  corpora (MEASURED 2026-09-24), so no `_THEOREM_BACKED` prose argument is refuted by them.

"LOUD" is established by one probe per field (sub-case), plus a REASONED reading of the
refusing code (cited in `evidence`). It says Python refuses THAT input, not that its refusal
provably covers every violation. Only a decider can say that.

Probe output, literal (`graphadmission_scope_probes.py` inputs, 2026-09-24):

    wf/dotted-relation-name: RAISED ValueError: relation 'a.b': '.' is reserved for compiled leaf predicates and cannot appear in a declared relation name
    nodup/duplicate-define: RAISED ValueError: duplicate relation definition: doc#viewer
    strat/derived-cycle: RAISED CyclicDerivedDependency: derived relations form a dependency cycle (...): [('doc', 'a'), ('doc', 'b')]
    ttuDirect/untainted-tupleset-computed: RAISED UnsupportedByGraphIndex: relation doc#view: tupleset 'parent' has computed/rewritten arms; ...
    ttuDirect/derived-tupleset: ADMITTED (strata=2)
    matchDecl/undeclared-computed-ref: ADMITTED (strata=0)
    matchDecl/undeclared-tupleset-untainted-target: ADMITTED (strata=0)
    ranked/computed-two-cycle: ADMITTED (strata=0)
    ranked/computed-self-loop: ADMITTED (strata=0)
    ranked/in-scope-control(ttu-recursion): ADMITTED (strata=0)
    objWild/object-wildcard-on-derived: RAISED UnsupportedByGraphIndex: object-wildcard shape (doc, view) targets a derived (boolean-tainted) relation; ...
    usWild.a/wildcard-userset-over-derived: RAISED UnsupportedByGraphIndex: relation doc#viewer: wildcard userset restriction [group:*#member] over the derived relation group#member ...
    usWild.b/star-tupleset-through-derived: RAISED UnsupportedByGraphIndex: relation doc#view: star tupleset [folder:*] on 'parent' derives the wildcard userset shape (folder, viewer) over the derived relation folder#viewer, ...
    ttuNotLeaf/dotted-ttu-target: RAISED ValueError: doc#view: 'viewer.0' is inside the reserved leaf namespace ('.' in referenced relation names)
    directRestrNotLeaf/dotted-restriction-predicate: RAISED ValueError: doc#viewer: 'member.0' is inside the reserved leaf namespace (...)
    computedRefsNotLeaf/dotted-computed-ref: RAISED ValueError: doc#view: 'viewer.0' is inside the reserved leaf namespace (...)
    noLeafSubjects/dotted-ttu-target-in-derived-arm: RAISED ValueError: doc#view: 'viewer.0' is inside the reserved leaf namespace (...)
    keysNonempty/empty-relation-name: RAISED ValueError: type 'doc': a declared relation name may not be empty ('define : [user]')
    storeValid.untainted/userset-subject-on-bare-arm: CS+SE RAISED AdmissionRejected: tuple doc:d1#viewer@group:g1#member matches no declared type restriction for doc#viewer
    storeValid.untainted/write-on-computed-only-relation: CS+SE RAISED AdmissionRejected: ... matches no declared type restriction for doc#view
    storeValid.untainted/write-on-undeclared-relation: CS+SE RAISED AdmissionRejected: ... matches no declared type restriction for doc#editor
    storeValid.derived/userset-subject-on-derived-direct-arm: CS+SE ADMITTED (check=True)
    storeValid.derived/bare-subject-beside-a-userset-restriction: CS+SE ADMITTED (check=True)
    storeValid/in-scope-control(bare-on-derived): CS+SE ADMITTED (check=True)
    corpus sweep, silent-field mirror: 36 curated corpora, 0 failing

(`CS` = `ConnectedStore.add_tuple`, `SE` = standalone `SetEngine.add_tuple`. The two
`ttuDirect` labels were later renamed `ttuDirect.untainted/...` and `ttuDirect.derived/...`.)

SABOTAGE (`docs/sabotage-procedure.md`) -- recorded in
`docs/tk104-graphadmission-scope-2026-09-24.md` sec 4, literal output quoted there.
"""
from __future__ import annotations

import re

import pytest
from sqlmodel import Session, SQLModel, create_engine

from formal.conformance.graphadmission_scope_probes import (
    SCHEMA_PROBES,
    SHADOWED,
    STORE_PROBES,
    silent_admission_failures,
)
from formal.conformance.test_w4fragment_scope_pin import (
    FULLSCOPE_LEAN,
    _parse_structure_fields,
)

STRUCTURE_NAME = "GraphAdmission"

#: Exact number of fields `structure GraphAdmission` carries. MEASURED 2026-09-24 by
#: `_parse_structure_fields` on `FullScope.lean`, and independently by reading the
#: structure: `wf` ... `keysNonempty`, fourteen bindings, two of them (`noLeafSubjects`,
#: `keysNonempty`) preceded by doc comments inside the structure body.
GRAPHADMISSION_FIELD_COUNT = 14

#: ANTI-VACUITY floor on the parse, `>=` so an addition is adjudicated by the equality
#: assertion, never blocked by the floor.
MIN_FIELDS_PARSED = 14

#: The `W4Fragment` field names a `shadowed_by` cell may cite.
_W4_FIELDS = frozenset({
    "computedOrDirect", "directArmsBare", "directArmsConcrete", "computedOnlyOperands",
    "noUnionDirects", "twoStrata", "wsBare", "bareStar", "ttuStarFree", "term",
})

_VALID_CLASSIFICATIONS = frozenset({"LOUD", "SILENT", "MIXED"})


# --------------------------------------------------------------------------- #
# The hand-maintained scope pin. NOTHING REGENERATES THIS.
# --------------------------------------------------------------------------- #
# Same columns as `W4FRAGMENT_SCOPE` (demands / classification / evidence / note), plus:
#   shadowed_by -- REQUIRED for MIXED: the `W4Fragment` field that every SILENT-half input
#                  also fails, so the joint premise never silently covers it. Checked on
#                  the probes via `w4_fragment_report`.
GRAPHADMISSION_SCOPE: dict[str, dict[str, str]] = {
    "wf": {
        "demands": "No declared relation name contains '.', the reserved leaf namespace.",
        "classification": "LOUD",
        "evidence": "zanzibar_utils_v1.py::parse_schema_ast",
        "note": "The '.' lock beside the empty-name lock; every declared name passes it.",
    },
    "nodup": {
        "demands": "At most one definition per (object type, relation) key.",
        "classification": "LOUD",
        "evidence": "zanzibar_utils_v1.py::parse_schema_ast",
        "note": "'duplicate relation definition'; duplicate TYPE blocks raise too.",
    },
    "strat": {
        "demands": (
            "The dependency graph among DERIVED relations is acyclic, so Kahn layering "
            "succeeds (`Spec/Stratify.lean::Stratifiable`)."
        ),
        "classification": "LOUD",
        "evidence": "zanzibar_utils_v1.py::_stratify",
        "note": "Raises `CyclicDerivedDependency`, a `ValueError` subclass.",
    },
    "ttuDirect": {
        "demands": (
            "Every TTU's tupleset relation, when declared on the same object type, is "
            "defined by direct restrictions only -- derived tuplesets included."
        ),
        "classification": "MIXED",
        "shadowed_by": "computedOrDirect",
        "evidence": "zanzibar_utils_v1.py::_validate_ttu_tuplesets",
        "note": (
            "LOUD sub-case: an UNTAINTED tupleset with a computed/TTU arm raises "
            "`UnsupportedByGraphIndex`. SILENT sub-case: a DERIVED tupleset is exempted by "
            "design (`ts_key not in tainted`), which FullScope.lean's own field comment "
            "concedes ('stronger than the mechanism it cites'). Its container is then a "
            "derived def with a `.ttu` leaf, so `W4Fragment.computedOrDirect` fails too."
        ),
    },
    "matchDecl": {
        "demands": (
            "Every rewrite rule of an untainted definition matches a DECLARED, untainted "
            "(object type, relation): no computed reference or TTU tupleset names an "
            "undeclared relation."
        ),
        "classification": "SILENT",
        "evidence": "zanzibar_utils_v1.py::_validate_ast_references",
        "note": (
            "Referenced names are checked for the '.' lock only, never for declared-ness, "
            "so `define viewer: [user] or editor` with no `editor` compiles. The derived "
            "half is vacuous: referencing a derived relation taints the referrer, and "
            "`schemaRewrites` skips tainted defs (REASONED)."
        ),
    },
    "ranked": {
        "demands": (
            "The untainted rewrite graph (match relation -> output relation) admits a "
            "strictly increasing rank bounded by the key count, i.e. it is acyclic: no "
            "untainted computed cycle such as `a: [user] or b`, `b: [user] or a`."
        ),
        "classification": "SILENT",
        "evidence": "formal/lean/ZanzibarProofs/Spec/Stratify.lean",
        "note": (
            "Python admits positively recursive untainted relations on purpose ('the "
            "closure handles them', that file's header), and nothing in "
            "`zanzibar_utils_v1.py::compile_ruleset` refuses them. TTU recursion is NOT "
            "excluded: a tupleset def emits no rule, so a TTU edge closes no cycle."
        ),
    },
    "objWild": {
        "demands": "No declared object-wildcard shape targets a derived relation.",
        "classification": "LOUD",
        "evidence": "zanzibar_utils_v1.py::_reject_object_wildcard_scope",
        "note": "The first loop of that function.",
    },
    "usWild": {
        "demands": (
            "No derived key is a subject-wildcard userset shape: neither a literal "
            "`[T:*#p]` restriction over a derived `T#p`, nor a star-tupleset TTU "
            "through-shape landing on a derived target."
        ),
        "classification": "LOUD",
        "evidence": "zanzibar_utils_v1.py::_reject_object_wildcard_scope",
        "note": (
            "Disjunct (a) raises in `zanzibar_utils_v1.py::_build_plan_tree`, disjunct (b) "
            "in `_reject_object_wildcard_scope`; one probe each. `TK68` added this field "
            "precisely because the Lean predicate was weaker than the compiler."
        ),
    },
    "storeValid": {
        "demands": (
            "Every stored tuple matches a declared direct restriction of its relation; on "
            "a derived relation, additionally with a BARE subject and an all-bare "
            "restriction list (`StoreValidRulesD`)."
        ),
        "classification": "MIXED",
        "shadowed_by": "directArmsBare",
        "evidence": "zanzibar_utils_v1.py::RuleSet.apply",
        "note": (
            "LOUD sub-case: an untainted relation's write must match a strict Filter, else "
            "`AdmissionRejected`. Two gates in series refuse it: `RuleSet.apply` fires first "
            "on BOTH backends (the set engine calls it from `_derived_pairs`), and "
            "`setengine/engine.py::SetEngine._validate` re-checks the same Filters. Disabling "
            "either one alone changes no probe outcome (sweep M5/M5b, INERT by design); "
            "disabling both does. SILENT sub-case: on a "
            "derived Direct arm that carries a userset restriction, Python admits both the "
            "userset subject and a bare one beside it. That arm is not bare, so "
            "`W4Fragment.directArmsBare` fails too."
        ),
    },
    "ttuNotLeaf": {
        "demands": "Every untainted TTU target is the bare sentinel or dot-free.",
        "classification": "LOUD",
        "evidence": "zanzibar_utils_v1.py::_validate_ast_references",
        "note": "The '.' lock on referenced names (`check_name`), TTU branch.",
    },
    "directRestrNotLeaf": {
        "demands": "Every direct restriction's predicate is the bare sentinel or dot-free.",
        "classification": "LOUD",
        "evidence": "zanzibar_utils_v1.py::_validate_ast_references",
        "note": "The '.' lock on referenced names (`check_name`), Direct branch.",
    },
    "computedRefsNotLeaf": {
        "demands": "Every computed reference is the bare sentinel or dot-free.",
        "classification": "LOUD",
        "evidence": "zanzibar_utils_v1.py::_validate_ast_references",
        "note": "The '.' lock on referenced names (`check_name`), Computed branch.",
    },
    "noLeafSubjects": {
        "demands": (
            "No rule of the full leaf-routed rule set (`schemaRewritesL`) has a dotted "
            "TTU target, derived arms included."
        ),
        "classification": "LOUD",
        "evidence": "zanzibar_utils_v1.py::_validate_ast_references",
        "note": "The same walk visits every arm of every definition, derived ones too.",
    },
    "keysNonempty": {
        "demands": "No declared relation name is empty.",
        "classification": "LOUD",
        "evidence": "zanzibar_utils_v1.py::parse_schema_ast",
        "note": "The `TK55` empty-name lock (2026-09-06).",
    },
}


def _field_of(label: str) -> str:
    return re.split(r"[./]", label, maxsplit=1)[0]


def _is_control(label: str) -> bool:
    return "control" in label


def _live_fields() -> list[str]:
    return _parse_structure_fields(FULLSCOPE_LEAN.read_text(encoding="utf-8"), STRUCTURE_NAME)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _schema_outcome(label: str) -> str:
    from zanzibar_utils_v1 import parse_openfga_schema
    schema, obj_wild, _exp = SCHEMA_PROBES[label]
    try:
        parse_openfga_schema(schema, object_wildcard_shapes=frozenset(obj_wild))
    except Exception as e:  # noqa: BLE001 -- the class name IS the measurement
        return type(e).__name__
    return "ADMITTED"


def _store_outcomes(label: str) -> tuple[str, str]:
    from connectedstore import ConnectedStore
    from setengine.engine import SetEngine
    schema, tup, _exp = STORE_PROBES[label]
    out = []
    for make in (lambda s: ConnectedStore(s, "cs", schema=schema),
                 lambda s: SetEngine(s, "se", schema)):
        backend = make(_session())
        try:
            backend.add_tuple(*tup)
        except Exception as e:  # noqa: BLE001
            out.append(type(e).__name__)
        else:
            out.append("ADMITTED")
    return out[0], out[1]


def _all_probe_labels() -> list[str]:
    return sorted(SCHEMA_PROBES) + sorted(STORE_PROBES)


def _expected(label: str) -> str:
    return (SCHEMA_PROBES.get(label) or STORE_PROBES[label])[2]


# --------------------------------------------------------------------------- #
# The field-set pin (the `W4Fragment` pin's contract, same parser)
# --------------------------------------------------------------------------- #
def test_graphadmission_fields_match_the_hand_classified_scope_pin():
    """The live `structure GraphAdmission` field set is exactly the classified one."""
    parsed = _live_fields()
    assert len(parsed) >= MIN_FIELDS_PARSED, (
        f"the GraphAdmission field parser recovered only {len(parsed)} field(s) ({parsed}); "
        f"the measured floor is {MIN_FIELDS_PARSED}. INSTRUMENT failure, not a scope change.")
    assert len(parsed) == len(set(parsed)), f"duplicate fields parsed: {parsed}"
    live, pinned = set(parsed), set(GRAPHADMISSION_SCOPE)
    added, removed = sorted(live - pinned), sorted(pinned - live)
    assert not added, (
        f"UNCLASSIFIED: {added} is declared by structure {STRUCTURE_NAME} but has no "
        f"GRAPHADMISSION_SCOPE row. Every headline theorem takes this bundle, so a new "
        f"field makes all of them STRICTLY WEAKER. Probe it (graphadmission_scope_probes.py), "
        f"classify it LOUD / SILENT / MIXED, and only then add the row. Board row TK104.")
    assert not removed, (
        f"STALE: {removed} has a GRAPHADMISSION_SCOPE row but is no longer a field of "
        f"structure {STRUCTURE_NAME} -- the headline theorems got STRONGER. Drop the row, "
        f"its probes and GRAPHADMISSION_FIELD_COUNT together, and say so in the commit.")
    assert len(GRAPHADMISSION_SCOPE) >= MIN_FIELDS_PARSED   # LAST: see the W4 pin, sabotage 2


def test_graphadmission_field_count_is_the_pinned_constant():
    parsed = _live_fields()
    assert len(parsed) >= MIN_FIELDS_PARSED, f"instrument failure: parsed {parsed}"
    assert len(parsed) == GRAPHADMISSION_FIELD_COUNT, (
        f"structure {STRUCTURE_NAME} now declares {len(parsed)} fields, not "
        f"GRAPHADMISSION_FIELD_COUNT={GRAPHADMISSION_FIELD_COUNT}: {parsed}")
    assert len(GRAPHADMISSION_SCOPE) == GRAPHADMISSION_FIELD_COUNT


@pytest.mark.parametrize("field", sorted(GRAPHADMISSION_SCOPE))
def test_every_scope_row_is_well_formed(field):
    row = GRAPHADMISSION_SCOPE[field]
    keys = {"demands", "classification", "evidence", "note", "shadowed_by"}
    assert set(row) <= keys, f"{field}: unexpected key(s) {sorted(set(row) - keys)}"
    assert len(row.get("demands", "").strip()) >= 30, f"{field}: `demands` is not a sentence"
    cls = row.get("classification", "")
    assert cls in _VALID_CLASSIFICATIONS, f"{field}: bad classification {cls!r}"
    ev = row.get("evidence", "")
    assert ev.strip() and ("::" in ev or "/" in ev), f"{field}: evidence {ev!r} is not greppable"
    assert not re.search(r":\d+", ev), f"{field}: evidence {ev!r} cites a bare line number"
    if cls == "MIXED":
        assert "LOUD" in row.get("note", "") and "SILENT" in row.get("note", ""), (
            f"{field} is MIXED; its note must name the LOUD and the SILENT sub-case")
        assert row.get("shadowed_by") in _W4_FIELDS, (
            f"{field} is MIXED but `shadowed_by` ({row.get('shadowed_by')!r}) does not name a "
            f"W4Fragment field. A MIXED row must say what keeps its SILENT half out of the "
            f"joint premise, or that it does not -- in which case it is a headline gap.")
    else:
        assert "shadowed_by" not in row, f"{field}: only a MIXED row carries `shadowed_by`"


def test_the_classification_ratio_is_the_finding():
    """LOUD 10 / MIXED 2 / SILENT 2 (2026-09-24). A row that changes class has to come
    here and say so; see the module docstring for what each number means."""
    counts = {c: 0 for c in _VALID_CLASSIFICATIONS}
    for row in GRAPHADMISSION_SCOPE.values():
        counts[row["classification"]] += 1
    assert counts == {"LOUD": 10, "MIXED": 2, "SILENT": 2}, (
        f"GraphAdmission classification moved: {counts}. The SILENT rows are the unreported "
        f"part of every headline theorem's premise; a change here changes that sentence.")


# --------------------------------------------------------------------------- #
# The classification <-> evidence tie
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("field", sorted(GRAPHADMISSION_SCOPE))
def test_classification_agrees_with_its_probes(field):
    """A LOUD row's violating probes all RAISE, a SILENT row's are all ADMITTED, and a MIXED
    row has at least one of each. This is what stops a row being re-classified without new
    evidence, and it is the check that goes red if a refusal is quietly dropped."""
    labels = [lb for lb in _all_probe_labels() if _field_of(lb) == field and not _is_control(lb)]
    assert labels, f"{field}: no violating probe in graphadmission_scope_probes.py"
    admitted = [lb for lb in labels if _expected(lb) == "ADMITTED"]
    raised = [lb for lb in labels if _expected(lb) != "ADMITTED"]
    cls = GRAPHADMISSION_SCOPE[field]["classification"]
    if cls == "LOUD":
        assert not admitted, f"{field} is LOUD but these probes are ADMITTED: {admitted}"
    elif cls == "SILENT":
        assert not raised, f"{field} is SILENT but these probes RAISE: {raised}"
    else:
        assert admitted and raised, (
            f"{field} is MIXED but its probes are not split: admitted={admitted} "
            f"raised={raised}")


def test_every_control_probe_is_admitted():
    """The controls are in scope; a surface that refused everything must not be able to
    make every LOUD row look confirmed."""
    controls = [lb for lb in _all_probe_labels() if _is_control(lb)]
    assert len(controls) >= 2
    assert all(_expected(lb) == "ADMITTED" for lb in controls), controls


@pytest.mark.parametrize("label", sorted(SCHEMA_PROBES))
def test_schema_probe_outcome_still_holds(label):
    got = _schema_outcome(label)
    assert got == SCHEMA_PROBES[label][2], (
        f"[{label}] parse_openfga_schema now gives {got}, recorded {SCHEMA_PROBES[label][2]}. "
        f"A refusal appeared or went away: re-adjudicate the "
        f"`{_field_of(label)}` row of GRAPHADMISSION_SCOPE.")


@pytest.mark.parametrize("label", sorted(STORE_PROBES))
def test_store_probe_outcome_still_holds(label):
    cs, se = _store_outcomes(label)
    exp = STORE_PROBES[label][2]
    assert (cs, se) == (exp, exp), (
        f"[{label}] ConnectedStore gives {cs}, SetEngine gives {se}, recorded {exp} for "
        f"both. Re-adjudicate the `{_field_of(label)}` row of GRAPHADMISSION_SCOPE.")


@pytest.mark.parametrize("label", sorted(SHADOWED))
def test_mixed_silent_half_is_shadowed_by_w4fragment(label):
    """Each SILENT-half probe of a MIXED row fails the `W4Fragment` field its row names, by
    the production report (which is differential-pinned to Lean's decider)."""
    from zanzibar_utils_v1 import w4_fragment_report
    field = _field_of(label)
    assert GRAPHADMISSION_SCOPE[field]["classification"] == "MIXED"
    assert SHADOWED[label] == GRAPHADMISSION_SCOPE[field]["shadowed_by"]
    assert _expected(label) == "ADMITTED", f"{label} is not a SILENT-half probe"
    if label in SCHEMA_PROBES:
        report = w4_fragment_report(SCHEMA_PROBES[label][0])
    else:
        schema, tup, _exp = STORE_PROBES[label]
        report = w4_fragment_report(schema, [tup])
    assert SHADOWED[label] in report.failures, (
        f"[{label}] is admitted by Python AND passes W4Fragment.{SHADOWED[label]} "
        f"(failures={report.failures}): the joint premise does NOT exclude it, so "
        f"GraphAdmission.{field}'s SILENT half is a headline gap, not a shadowed one.")


def test_every_mixed_row_has_a_shadowed_probe():
    for field, row in GRAPHADMISSION_SCOPE.items():
        if row["classification"] == "MIXED":
            assert any(_field_of(lb) == field for lb in SHADOWED), (
                f"{field} is MIXED but no SHADOWED probe measures its `shadowed_by` claim")


# --------------------------------------------------------------------------- #
# The REASONED mirror of the two SILENT fields, and the corpus sweep it enables
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label", sorted(
    lb for lb in SCHEMA_PROBES if _field_of(lb) in ("matchDecl", "ranked")))
def test_silent_field_mirror_known_answers(label):
    """KNOWN-ANSWER control for the mirror: each SILENT-field probe fails exactly its own
    field, and the in-scope control fails nothing."""
    want = () if _is_control(label) else (_field_of(label),)
    assert silent_admission_failures(SCHEMA_PROBES[label][0]) == want


def test_theorem_backed_corpora_pass_the_silent_fields():
    """No `_THEOREM_BACKED` corpus has a dangling reference or an untainted computed cycle.
    These are the two premise fields that nothing else checks; the prose argument in
    `corpus.py` covers them only by assertion. REASONED mirror, not a decider."""
    from formal.conformance.test_conformance_fragment import ALL_CORPORA
    from formal.conformance.test_conformance_graph import _THEOREM_BACKED
    backed = {k: v for k, v in ALL_CORPORA.items()
              if k.startswith("SCHEMAS:") and k.split(":", 1)[1] in _THEOREM_BACKED}
    assert len(backed) >= 20, f"only {len(backed)} theorem-backed corpora found"
    bad = {k: f for k, (schema, _t, _ow) in sorted(backed.items())
           if (f := silent_admission_failures(schema))}
    assert not bad, (
        f"theorem-backed corpora outside GraphAdmission's SILENT fields: {bad}. The "
        f"headline theorems do not cover them; move them to _DIFFERENTIAL_ONLY or fix them.")
