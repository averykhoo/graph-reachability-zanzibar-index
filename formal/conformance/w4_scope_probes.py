"""The `W4Fragment` scope-pin probes as RE-RUNNABLE fixtures (`DW-1` step 3, 2026-09-23).

`test_w4fragment_scope_pin.py` classifies each `W4Fragment` field LOUD / SILENT / MIXED on
the strength of a 2026-08-31 probe: one violating schema or write per field, fed to the
real backends. Its docstring quotes the probe's OUTPUT, but the probe's INPUTS survived
only as labels (`computedOrDirect/ttu-in-derived`, ...) and a few DSL fragments in the
`note` cells. The script was in `.scratch/` and is gone. This module re-creates one input
per label, keyed by that label, so the claims can be re-run.

**These are reconstructions, not the originals.** Where a note quotes the DSL, the fixture
uses it verbatim. Otherwise the shape was built from the label and the quoted output.
Where the original probe violated more than one field, the fixture was narrowed so that
it violates ONLY its own field (`twoStrata/three-strata`, `term.NoStoreSubjectR/...`), in
the style of `FragmentDecide.lean`'s per-field controls. Each fixture's docstring-comment
says which.

Each entry is `label -> (schema_text, tuples, object_wildcard_shapes, expected_failures)`.
`expected_failures` was derived BY HAND from the Lean definitions in
`FullScope.lean::W4Fragment` (REASONED, 2026-09-23), before either decider was run on the
fixture. `test_conformance_fragment.py` holds Lean's `zcli mode="fragment"` AND the
production `zanzibar_utils_v1.py::w4_fragment_report` to it. That makes three derivations
that share no code. **The hand derivation was wrong twice on the first run**, and both
errors were the hand's, not a decider's: Lean and Python agreed with each other on all 17
fixtures of that run. (An 18th, `computedOnlyOperands/derived-operand-second`, was added by
the mutation sweep.) The two entries carry a dated CORRECTION comment.

`PYTHON_OUTCOME` records what the 2026-08-31 probe observed the backends do with each input
(ADMITTED / RAISED). `test_conformance_fragment.py` re-checks it for the schema-side probes.
"""
from __future__ import annotations

from tests.oracle import t as mk_tuple

SCOPE_PROBES: dict[str, tuple[str, list, tuple, tuple[str, ...]]] = {
    # A TTU leaf inside a derived (boolean) definition.
    "computedOrDirect/ttu-in-derived": (
        """
        type user
        type folder
          define viewer: [user]
        type doc
          define parent: [folder]
          define banned: [user]
          define view: (viewer from parent) but not banned
        """,
        [], (), ("computedOrDirect",),
    ),
    # A userset restriction on a derived definition's direct arm.
    "directArmsBare/userset-direct-arm": (
        """
        type user
        type group
          define member: [user]
        type doc
          define banned: [user]
          define view: [user, group#member] but not banned
        """,
        [], (), ("directArmsBare",),
    ),
    # Verbatim from the scope pin's note: `define approver: [user, user:*] but not banned`.
    "directArmsConcrete/star-direct-arm": (
        """
        type user
        type doc
          define banned: [user]
          define approver: [user, user:*] but not banned
        """,
        [], (), ("directArmsConcrete",),
    ),
    # Verbatim from the note: `editor: [user] but not banned` read by
    # `view: editor but not banned`.
    "computedOnlyOperands/direct-one-stratum-down": (
        """
        type user
        type doc
          define banned: [user]
          define editor: [user] but not banned
          define view: editor but not banned
        """,
        [], (), ("computedOnlyOperands",),
    ),
    # ADDED by the step-3 mutation sweep (M16, 2026-09-23): every other probe's derived
    # operand is its definition's FIRST computed ref, so a mirror that read only the first
    # ref was INERT. Here the non-computed-only derived operand `blocked` is second.
    "computedOnlyOperands/derived-operand-second": (
        """
        type user
        type doc
          define banned: [user]
          define editor: [user]
          define blocked: [user] but not banned
          define view: editor but not blocked
        """,
        [], (), ("computedOnlyOperands",),
    ),
    # Verbatim from the note: `view: [user] or (editor but not banned)`.
    "noUnionDirects/union-reachable-direct": (
        """
        type user
        type doc
          define editor: [user]
          define banned: [user]
          define view: [user] or (editor but not banned)
        """,
        [], (), ("noUnionDirects",),
    ),
    # NARROWED: the bottom stratum `b` is computed-only (`y but not x`), so that only
    # `twoStrata` fails; `b: [user] but not x` would also fail `computedOnlyOperands`.
    "twoStrata/three-strata": (
        """
        type user
        type doc
          define x: [user]
          define y: [user]
          define b: y but not x
          define c: b but not x
          define d: c but not x
        """,
        [], (), ("twoStrata",),
    ),
    "wsBare/wildcard-userset-over-UNTAINTED": (
        """
        type user
        type group
          define member: [user]
        type doc
          define viewer: [group:*#member]
        """,
        [], (), ("wsBare",),
    ),
    # The LOUD sub-case: Python's compile raises `UnsupportedByGraphIndex`. The report and
    # the Lean decider still classify it; parsing succeeds.
    # CORRECTION (2026-09-23, first run): the hand derivation said `("wsBare",)` and was
    # WRONG. A userset restriction over a derived relation taints its HOLDER
    # (`compute_taint`'s `_mentions` and Lean's `taintedKeys` agree), so doc#viewer is
    # derived, and its non-bare, wildcard, union-reachable direct arm fails three more
    # fields. Lean and the production report agreed with each other on the first run.
    "wsBare/wildcard-userset-over-DERIVED": (
        """
        type user
        type group
          define banned: [user]
          define member: [user] but not banned
        type doc
          define viewer: [group:*#member]
        """,
        [], (), ("directArmsBare", "directArmsConcrete", "noUnionDirects", "wsBare"),
    ),
    # Taint propagates from org#member through the TTU onto doc#view, so the schema
    # compiles; what takes it out of the fragment is `computedOrDirect` on the now-derived
    # doc#view, and `term` HOLDS -- exactly the scope pin's correction.
    "term.NoTtuTarget/untainted-ttu-onto-derived": (
        """
        type user
        type org
          define banned: [user]
          define member: [user] but not banned
        type doc
          define parent: [org]
          define view: member from parent
        """,
        [], (), ("computedOrDirect",),
    ),
    # A LOUD corner: the tupleset `parent` is not declared on doc, so no member type
    # carries taint onto doc#view, it stays UNTAINTED, and its TTU rule targets the
    # derived NAME `member`. Python's compile raises.
    "term.NoTtuTarget/undeclared-tupleset": (
        """
        type user
        type org
          define banned: [user]
          define member: [user] but not banned
        type doc
          define view: member from parent
        """,
        [], (), ("term",),
    ),
    # The other LOUD corner (`zanzibar_utils_v1.py::_validate_ttu_tuplesets`' comment:
    # "a member type whose own `target_rel` is untainted while another type's is
    # tainted"). doc#view's tupleset admits only team, whose `member` is plain, so doc#view
    # stays UNTAINTED; its TTU target NAME `member` is derived on org. Both Python's refusal
    # and `NoTtuTarget` compare names type-agnostically.
    # CORRECTION (2026-09-23, first run): the first reconstruction had `parent: [org,
    # team]`. Taint then propagates through org, the schema COMPILES, and it fails
    # `computedOrDirect`, which is not the RAISED corner the probe observed.
    "term.NoTtuTarget/mixed-member-types": (
        """
        type user
        type org
          define banned: [user]
          define member: [user] but not banned
        type team
          define member: [user]
        type doc
          define parent: [team]
          define view: member from parent
        """,
        [], (), ("term",),
    ),
    "ttuStarFree/star-tupleset-schema": (
        """
        type user
        type folder
          define viewer: [user]
        type doc
          define parent: [folder, folder:*]
          define viewer: viewer from parent
        """,
        [], (), (),
    ),
    # ---- store-side probes: one violating write each ----
    "bareStar/userset-star-subject": (
        """
        type user
        type group
          define member: [user]
        type doc
          define viewer: [group:*#member]
        """,
        [mk_tuple("member", "group", "*", "viewer", "doc", "d1")],
        (), ("wsBare", "bareStar"),
    ),
    "bareStar/object-wildcard-DECLARED": (
        """
        type user
        type doc
          define viewer: [user]
        """,
        [mk_tuple("...", "user", "alice", "viewer", "doc", "*")],
        (("doc", "viewer"),), ("bareStar",),
    ),
    "ttuStarFree/star-subject-on-tupleset": (
        """
        type user
        type folder
          define viewer: [user]
        type doc
          define parent: [folder, folder:*]
          define viewer: viewer from parent
        """,
        [mk_tuple("...", "folder", "*", "parent", "doc", "d1")],
        (), ("ttuStarFree",),
    ),
    # NARROWED: the userset subject `group:g1#view` is over an UNTAINTED relation that
    # shares its NAME with the derived doc#view. `NoStoreSubjectR` is keyed on the name
    # alone, so only `term` fails; a subject over doc#view itself would also need a
    # `[doc#view]` restriction, which taints its holder and fails two more fields.
    "term.NoStoreSubjectR/derived-userset-subject": (
        """
        type user
        type group
          define view: [user]
        type doc
          define banned: [user]
          define editor: [user]
          define view: editor but not banned
          define reader: [group#view]
        """,
        [mk_tuple("view", "group", "g1", "reader", "doc", "d1")],
        (), ("term",),
    ),
    "wsBare/bare-star-subject(in-scope control)": (
        """
        type user
        type doc
          define viewer: [user, user:*]
        """,
        [mk_tuple("...", "user", "*", "viewer", "doc", "d1")],
        (), (),
    ),
}

#: What the 2026-08-31 probe observed Python's COMPILE do with each schema-side label
#: (`test_w4fragment_scope_pin.py` docstring, literal). Store-side labels are omitted.
PYTHON_OUTCOME: dict[str, str] = {
    "computedOrDirect/ttu-in-derived": "ADMITTED",
    "directArmsBare/userset-direct-arm": "ADMITTED",
    "directArmsConcrete/star-direct-arm": "ADMITTED",
    "computedOnlyOperands/direct-one-stratum-down": "ADMITTED",
    "computedOnlyOperands/derived-operand-second": "ADMITTED",
    "noUnionDirects/union-reachable-direct": "ADMITTED",
    "twoStrata/three-strata": "ADMITTED",
    "wsBare/wildcard-userset-over-UNTAINTED": "ADMITTED",
    "wsBare/wildcard-userset-over-DERIVED": "RAISED",
    "term.NoTtuTarget/untainted-ttu-onto-derived": "ADMITTED",
    "ttuStarFree/star-tupleset-schema": "ADMITTED",
    "term.NoTtuTarget/undeclared-tupleset": "RAISED",
    "term.NoTtuTarget/mixed-member-types": "RAISED",
}
