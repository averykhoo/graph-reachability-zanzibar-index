"""The `GraphAdmission` scope probes as RE-RUNNABLE fixtures (`TK104` sizing, 2026-09-24).

`FullScope.lean::GraphAdmission` is the other half of every headline theorem's premise,
`(hA : GraphAdmission S T) (hF : W4Fragment S T)`. Its docstring calls it *"hypotheses the
Python compiler/write admission guarantee for EVERY accepted schema and store"*, and the
`DW-1` plan repeated that it is "largely mirrored by Python compile and write refusals",
marked UNVERIFIED. These fixtures are the verification: one violating input per field (or
per sub-case), each paired with what the real Python surface did with it on 2026-09-24.
`test_graphadmission_scope_pin.py` re-runs every one of them.

Provenance, per entry:
  * that the input VIOLATES the field named by its label is REASONED from the Lean
    definition (there is no `GraphAdmission` decider; building one is what `TK104` owns);
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
    "strat/derived-cycle": ("""
        type user
        type doc
          define x: [user]
          define a: b but not x
          define b: a but not x
        """, (), "CyclicDerivedDependency"),
    # The LOUD half: an UNTAINTED tupleset with a computed arm.
    "ttuDirect.untainted/tupleset-with-computed-arm": ("""
        type user
        type folder
          define viewer: [user]
        type doc
          define owner: [folder]
          define parent: owner
          define view: viewer from parent
        """, (), "UnsupportedByGraphIndex"),
    # The SILENT half: `_validate_ttu_tuplesets` exempts DERIVED tuplesets by design, and
    # `TtuTuplesetsDirect` has no such guard. The container doc#view is tainted through
    # its tupleset reference, so it is a derived def with a `.ttu` leaf: see SHADOWED.
    "ttuDirect.derived/derived-tupleset": ("""
        type user
        type folder
          define viewer: [user]
        type doc
          define blockedp: [folder]
          define parent: [folder] but not blockedp
          define view: viewer from parent
        """, (), "ADMITTED"),
    # A computed reference to an undeclared relation. Nothing in Python checks that a
    # referenced relation is DECLARED (`_validate_ast_references` checks the '.' lock only).
    "matchDecl/undeclared-computed-ref": ("""
        type user
        type doc
          define viewer: [user] or editor
        """, (), "ADMITTED"),
    # An undeclared tupleset whose TARGET is untainted. (With a derived target the same
    # shape RAISES -- `w4_scope_probes.py`'s `term.NoTtuTarget/undeclared-tupleset`.)
    "matchDecl/undeclared-tupleset-untainted-target": ("""
        type user
        type folder
          define viewer: [user]
        type doc
          define view: viewer from parent
        """, (), "ADMITTED"),
    # An untainted computed cycle. `Spec/Stratify.lean`'s header says it outright:
    # "untainted relations may be positively recursive; the closure handles them".
    # `RewriteRanked` needs a strictly increasing rank along every untainted rule.
    "ranked/computed-two-cycle": ("""
        type user
        type doc
          define a: [user] or b
          define b: [user] or a
        """, (), "ADMITTED"),
    "ranked/computed-self-loop": ("""
        type user
        type doc
          define viewer: [user] or viewer
        """, (), "ADMITTED"),
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
#:   ttuDirect.derived  -- a derived tupleset taints its container (`exprRefs`'s `.ttu`
#:                         case lists `(t, ts)`), so the container is a derived def with a
#:                         `.ttu` leaf, and `computedOrDirect` bans those.
#:   storeValid.derived -- a tuple matching a NON-bare restriction on a derived Direct arm
#:                         means that arm is not bare, and `directArmsBare` fails.
#: MEASURED on the probes by the pin.
SHADOWED: dict[str, str] = {
    "ttuDirect.derived/derived-tupleset": "computedOrDirect",
    "storeValid.derived/userset-subject-on-derived-direct-arm": "directArmsBare",
    "storeValid.derived/bare-subject-beside-a-userset-restriction": "directArmsBare",
}


# --------------------------------------------------------------------------- #
# A REASONED mirror of the two SILENT fields. NOT a decider: nothing pins it to Lean.
# --------------------------------------------------------------------------- #
def _untainted_rules(ast, tainted):
    """Mirror of `RulesWrite.lean::schemaRewrites`: the `exprArms` of every UNTAINTED def,
    walking into unions only. Yields `(object_type, match_rel, out_rel)`."""
    from zanzibar_utils_v1 import TTU, Computed, Union

    def arms(e):
        if isinstance(e, Computed):
            yield e.relation
        elif isinstance(e, TTU):
            yield e.tupleset_rel
        elif isinstance(e, Union):
            for c in e.children:
                yield from arms(c)

    for (ot, rel), e in ast.items():
        if (ot, rel) not in tainted:
            for m in arms(e):
                yield ot, m, rel


def silent_admission_failures(schema_text: str) -> tuple[str, ...]:
    """Which of `matchDecl` / `ranked` a schema fails, by a hand mirror of the Lean.

    `matchDecl` -- every untainted rule's match key is declared and untainted
                  (`RestrictBase.lean::RewriteMatchDeclared`).
    `ranked`    -- the untainted rule graph, match -> out, is acyclic. `RewriteRanked`
                  also bounds the rank by `S.keys.length`; under `matchDecl` every rule
                  endpoint is a declared key, so an acyclic graph always fits (REASONED).
    """
    from zanzibar_utils_v1 import compute_taint, parse_schema_ast
    ast = parse_schema_ast(schema_text)
    tainted = compute_taint(ast)
    rules = list(_untainted_rules(ast, tainted))
    fails = []
    if any((ot, m) not in ast or (ot, m) in tainted for ot, m, _ in rules):
        fails.append("matchDecl")
    succ: dict = {}
    for ot, m, out in rules:
        succ.setdefault((ot, m), set()).add((ot, out))
    state: dict = {}

    def on_cycle(n) -> bool:
        state[n] = 1
        for nx in succ.get(n, ()):
            if state.get(nx) == 1 or (nx not in state and on_cycle(nx)):
                return True
        state[n] = 2
        return False

    if any(n not in state and on_cycle(n) for n in list(succ)):
        fails.append("ranked")
    return tuple(fails)
