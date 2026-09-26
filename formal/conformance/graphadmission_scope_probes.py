"""The `GraphAdmission` scope probes as RE-RUNNABLE fixtures (`TK104` sizing, 2026-09-24).

`FullScope.lean::GraphAdmission` is the other half of every headline theorem's premise,
`(hA : GraphAdmission S T) (hF : W4Fragment S T)`. Its docstring calls it *"hypotheses the
Python compiler/write admission guarantee for EVERY accepted schema and store"*, and the
`DW-1` plan repeated that it is "largely mirrored by Python compile and write refusals",
marked UNVERIFIED. These fixtures are the verification: one violating input per field (or
per sub-case), each paired with what the real Python surface did with it on 2026-09-24.
`test_graphadmission_scope_pin.py` re-runs every one of them.

Provenance, per entry:
  * that the input VIOLATES the field named by its label was REASONED from the Lean
    definition on 2026-09-24. Since 2026-09-25 it is CHECKED by Lean's decider
    (`AdmissionDecide.lean::graphAdmissionB`) in
    `test_conformance_fragment.py::test_lean_admission_fails_each_probes_named_field`;
  * the outcome (`ADMITTED` / the raised class) is MEASURED, and re-measured by the pin.

A label is `<field>/<case>` or `<field>.<half>/<case>`. A label containing `control` is an
IN-scope input that must be admitted, so that a surface which refused everything could not
make every LOUD row look confirmed.
"""
from __future__ import annotations

from tests.oracle import t as mk_tuple

#: label -> (schema_text, object_wildcard_shapes, expected) where expected is
#: "ADMITTED" or the name of the exception class `parse_openfga_schema` raises.
SCHEMA_PROBES: dict[str, tuple[str, tuple, str]] = {
    "wf/dotted-relation-name": ("""
        type user
        type doc
          define a.b: [user]
        """, (), "ValueError"),
    "nodup/duplicate-define": ("""
        type user
        type doc
          define viewer: [user]
          define viewer: [user]
        """, (), "ValueError"),
    # A derived cycle through a TTU TARGET. Until ASK-1 (2026-09-26) this was the
    # same-type `a: b but not x`, `b: a but not x`; the parser now refuses that as a
    # reference cycle before `_stratify` runs, so only a TTU target still reaches it.
    "strat/derived-cycle": ("""
        type user
        type doc
          define x: [user]
          define parent: [doc]
          define a: ([user] but not x) or a from parent
        """, (), "CyclicDerivedDependency"),
    # Both `ttuDirect` probes are refused at PARSE time since TK106 (2026-09-26, user
    # decision: refuse boolean tuplesets, as OpenFGA does) by
    # `zanzibar_utils_v1.py::_validate_tuplesets_direct`, message "tupleset must be direct".
    #
    # Was the LOUD half: an UNTAINTED tupleset with a computed arm. It raised
    # `UnsupportedByGraphIndex` from the graph compiler (`_validate_ttu_tuplesets`) until
    # TK106; the parse-time check now fires first, so it raises `ValueError`.
    "ttuDirect.untainted/tupleset-with-computed-arm": ("""
        type user
        type folder
          define viewer: [user]
        type doc
          define owner: [folder]
          define parent: owner
          define view: viewer from parent
        """, (), "ValueError"),
    # Was the SILENT half, ADMITTED until TK106: `_validate_ttu_tuplesets` exempts DERIVED
    # tuplesets by design, and `TtuTuplesetsDirect` has no such guard. The container
    # doc#view is tainted through its tupleset reference, so it is a derived def with a
    # `.ttu` leaf, and it was listed in SHADOWED (by `computedOrDirect`) until TK106.
    "ttuDirect.derived/derived-tupleset": ("""
        type user
        type folder
          define viewer: [user]
        type doc
          define blockedp: [folder]
          define parent: [folder] but not blockedp
          define view: viewer from parent
        """, (), "ValueError"),
    # A computed reference to an undeclared relation. ADMITTED until ASK-1 (2026-09-26),
    # when the user decided schemas must be self-consistent; now
    # `zanzibar_utils_v1.py::_validate_ast_consistency` refuses it at parse time.
    "matchDecl/undeclared-computed-ref": ("""
        type user
        type doc
          define viewer: [user] or editor
        """, (), "ValueError"),
    # An undeclared tupleset whose TARGET is untainted. (With a derived target the same
    # shape raised even before ASK-1 -- `w4_scope_probes.py`'s
    # `term.NoTtuTarget/undeclared-tupleset`.)
    "matchDecl/undeclared-tupleset-untainted-target": ("""
        type user
        type folder
          define viewer: [user]
        type doc
          define view: viewer from parent
        """, (), "ValueError"),
    # An untainted computed cycle. `RewriteRanked` needs a strictly increasing rank along
    # every untainted rule. ADMITTED until ASK-1 (2026-09-26); OpenFGA refuses it too
    # (`ErrCycle`), and now so does `_validate_ast_consistency`.
    "ranked/computed-two-cycle": ("""
        type user
        type doc
          define a: [user] or b
          define b: [user] or a
        """, (), "ValueError"),
    "ranked/computed-self-loop": ("""
        type user
        type doc
          define viewer: [user] or viewer
        """, (), "ValueError"),
    # IN scope: TTU recursion (nested folders) puts the edge (folder,parent) -> (folder,
    # viewer), which is not a cycle. The shape a reader most fears is NOT excluded.
    "ranked/in-scope-control(ttu-recursion)": ("""
        type user
        type folder
          define parent: [folder]
          define viewer: [user] or viewer from parent
        """, (), "ADMITTED"),
    "objWild/object-wildcard-on-derived": ("""
        type user
        type doc
          define banned: [user]
          define view: [user] but not banned
        """, (("doc", "view"),), "UnsupportedByGraphIndex"),
    "usWild.a/wildcard-userset-over-derived": ("""
        type user
        type group
          define banned: [user]
          define member: [user] but not banned
        type doc
          define viewer: [group:*#member]
        """, (), "UnsupportedByGraphIndex"),
    "usWild.b/star-tupleset-through-derived": ("""
        type user
        type folder
          define banned: [user]
          define viewer: [user] but not banned
        type doc
          define parent: [folder, folder:*]
          define view: viewer from parent
        """, (), "UnsupportedByGraphIndex"),
    "ttuNotLeaf/dotted-ttu-target": ("""
        type user
        type folder
          define viewer: [user]
        type doc
          define parent: [folder]
          define view: viewer.0 from parent
        """, (), "ValueError"),
    "directRestrNotLeaf/dotted-restriction-predicate": ("""
        type user
        type group
          define member: [user]
        type doc
          define viewer: [group#member.0]
        """, (), "ValueError"),
    "computedRefsNotLeaf/dotted-computed-ref": ("""
        type user
        type doc
          define viewer: [user]
          define view: viewer.0
        """, (), "ValueError"),
    # Over the LEAF-routed rules (`schemaRewritesL`): the TTU sits in a derived arm.
    "noLeafSubjects/dotted-ttu-target-in-derived-arm": ("""
        type user
        type folder
          define viewer: [user]
        type doc
          define banned: [user]
          define parent: [folder]
          define view: (viewer.0 from parent) but not banned
        """, (), "ValueError"),
    "keysNonempty/empty-relation-name": ("""
        type user
        type doc
          define : [user]
        """, (), "ValueError"),
}

#: label -> (schema_text, tuple, expected) where expected is "ADMITTED" or the name of the
#: exception class raised. Each is written through BOTH `ConnectedStore.add_tuple`
#: (TupleSource admission + synchronous graph apply) and a standalone `SetEngine.add_tuple`.
STORE_PROBES: dict[str, tuple[str, object, str]] = {
    "storeValid.untainted/userset-subject-on-bare-arm": ("""
        type user
        type group
          define member: [user]
        type doc
          define viewer: [user]
        """, mk_tuple("member", "group", "g1", "viewer", "doc", "d1"), "AdmissionRejected"),
    "storeValid.untainted/write-on-computed-only-relation": ("""
        type user
        type doc
          define viewer: [user]
          define view: viewer
        """, mk_tuple("...", "user", "alice", "view", "doc", "d1"), "AdmissionRejected"),
    "storeValid.untainted/write-on-undeclared-relation": ("""
        type user
        type doc
          define viewer: [user]
        """, mk_tuple("...", "user", "alice", "editor", "doc", "d1"), "AdmissionRejected"),
    # The SILENT half. `StoreValidRulesD`'s derived disjunct demands a BARE subject AND an
    # all-bare restriction list; this write has a userset subject.
    "storeValid.derived/userset-subject-on-derived-direct-arm": ("""
        type user
        type group
          define member: [user]
        type doc
          define banned: [user]
          define view: [user, group#member] but not banned
        """, mk_tuple("member", "group", "g1", "view", "doc", "d1"), "ADMITTED"),
    # Subtler: the SUBJECT is bare, but the restriction list it matches is not all-bare,
    # so the same clause still fails.
    "storeValid.derived/bare-subject-beside-a-userset-restriction": ("""
        type user
        type group
          define member: [user]
        type doc
          define banned: [user]
          define view: [user, group#member] but not banned
        """, mk_tuple("...", "user", "alice", "view", "doc", "d1"), "ADMITTED"),
    "storeValid/in-scope-control(bare-on-derived)": ("""
        type user
        type doc
          define banned: [user]
          define view: [user] but not banned
        """, mk_tuple("...", "user", "alice", "view", "doc", "d1"), "ADMITTED"),
}

#: A MIXED field's SILENT half, and the `W4Fragment` field that nonetheless takes the input
#: out of the joint premise. The claim is that the headline theorem never silently covers
#: these inputs, because the other bundle fails too, and `zanzibar_utils_v1.py::
#: w4_fragment_report` (differential-pinned to Lean's decider) reports that field.
#: REASONED as a general statement:
#:   storeValid.derived -- a tuple matching a NON-bare restriction on a derived Direct arm
#:                         means that arm is not bare, and `directArmsBare` fails.
#: MEASURED on the probes by the pin.
#: `ttuDirect.derived/derived-tupleset -> computedOrDirect` was REMOVED on 2026-09-26
#: (TK106): `ttuDirect` is LOUD now, the probe is refused at parse time, so there is no
#: SILENT half left to shadow. (The reasoning still holds of the unchecked schema: a
#: derived tupleset taints its container, whose `.ttu` leaf `computedOrDirect` bans.)
SHADOWED: dict[str, str] = {
    "storeValid.derived/userset-subject-on-derived-direct-arm": "directArmsBare",
    "storeValid.derived/bare-subject-beside-a-userset-restriction": "directArmsBare",
}


# --------------------------------------------------------------------------- #
# The two formerly SILENT fields, LOUD since ASK-1 (2026-09-26): the parsers refuse every
# violation, and this report still describes one on the unchecked parse. Since TK104's
# decider landed (2026-09-25) this delegates to the
# PRODUCTION report, which `test_conformance_fragment.py` section (J) differential-pins
# to Lean's `AdmissionDecide.lean::graphAdmissionB`. It was a REASONED hand mirror with
# known-answer controls only, from the 2026-09-24 sizing until then.
# --------------------------------------------------------------------------- #
def silent_admission_failures(schema_text: str) -> tuple[str, ...]:
    """Which of `matchDecl` / `ranked` a schema fails (`zanzibar_utils_v1.py::
    graph_admission_report`).

    `matchDecl` -- every untainted rule's match key is declared and untainted
                  (`RestrictBase.lean::RewriteMatchDeclared`).
    `ranked`    -- the untainted rule graph, match -> out, is acyclic
                  (`RulesSaturate.lean::RewriteRanked`).
    """
    from zanzibar_utils_v1 import graph_admission_report
    return graph_admission_report(schema_text).failures
