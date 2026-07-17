"""Shared schema corpus for conformance tests (SEMANTICS.md §10 / plan C1).

Each entry: name -> (schema_text, tuples, object_wildcard_shapes). Tuples use the
oracle's `t(...)` constructor. Kept small so the full query grid stays fast, but
chosen to exercise every AST node and the star x boolean corners.
"""

from __future__ import annotations

from tests.oracle import t as mk_tuple


def _deep_grid(n_rel: int = 8, n_obj: int = 8):
    """A schema/tuples pair that traverses the object x relation grid so the
    evaluation depth is ~n_rel*n_obj — far exceeding an additive fuel bound.
    Regression for the multiplicative-fuelBound fix (Store.lean). check(alice, r1,
    node{n_obj}) is True (reaches the r1@node1 grant through the grid)."""
    lines = ["type user", "type node", "  define parent: [node]",
             "  define r1: [user] or r2"]
    for i in range(2, n_rel):
        lines.append(f"  define r{i}: r{i + 1}")
    lines.append(f"  define r{n_rel}: r1 from parent")
    schema = "\n".join(lines)
    tuples = [mk_tuple("...", "node", f"node{i}", "parent", "node", f"node{i + 1}")
              for i in range(1, n_obj)]
    tuples.append(mk_tuple("...", "user", "alice", "r1", "node", "node1"))
    return schema, tuples, ()


SCHEMAS: dict[str, tuple[str, list, tuple]] = {
    "deep_grid": _deep_grid(),
    "union_computed": (
        """
        type user
        type doc
          define editor: [user]
          define viewer: [user] or editor
        """,
        [mk_tuple("...", "user", "alice", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "viewer", "doc", "d1")],
        (),
    ),
    "group_userset": (
        """
        type user
        type group
          define member: [user, group#member]
        type doc
          define viewer: [group#member]
        """,
        [mk_tuple("...", "user", "alice", "member", "group", "g1"),
         mk_tuple("member", "group", "g1", "member", "group", "g2"),
         mk_tuple("member", "group", "g2", "viewer", "doc", "d1")],
        (),
    ),
    "ttu": (
        """
        type user
        type folder
          define viewer: [user]
        type doc
          define parent: [folder]
          define viewer: viewer from parent
        """,
        [mk_tuple("...", "user", "alice", "viewer", "folder", "f1"),
         mk_tuple("...", "folder", "f1", "parent", "doc", "d1")],
        (),
    ),
    "wildcard_public": (
        """
        type user
        type doc
          define viewer: [user, user:*]
        """,
        [mk_tuple("...", "user", "*", "viewer", "doc", "d1")],
        (),
    ),
    "wildcard_group_member": (
        """
        type user
        type group
          define member: [user, user:*]
        type doc
          define viewer: [group#member]
        """,
        [mk_tuple("...", "user", "*", "member", "group", "g1"),
         mk_tuple("member", "group", "g1", "viewer", "doc", "d1")],
        (),
    ),
    "object_wildcard": (
        """
        type user
        type folder
          define viewer: [user]
        """,
        [mk_tuple("...", "user", "alice", "viewer", "folder", "*")],
        (("folder", "viewer"),),
    ),
    "boolean_exclusion": (
        """
        type user
        type doc
          define editor: [user]
          define banned: [user]
          define viewer: editor but not banned
        """,
        [mk_tuple("...", "user", "alice", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "banned", "doc", "d1")],
        (),
    ),
    "boolean_intersection": (
        """
        type user
        type doc
          define editor: [user]
          define required: [user]
          define viewer: editor and required
        """,
        [mk_tuple("...", "user", "alice", "editor", "doc", "d1"),
         mk_tuple("...", "user", "alice", "required", "doc", "d1"),
         mk_tuple("...", "user", "bob", "editor", "doc", "d1")],
        (),
    ),
    "boolean_star_exclusion": (
        """
        type user
        type doc
          define base: [user:*]
          define blocked: [user]
          define viewer: base but not blocked
        """,
        [mk_tuple("...", "user", "*", "base", "doc", "d1"),
         mk_tuple("...", "user", "mallory", "blocked", "doc", "d1")],
        (),
    ),
    "two_stratum_cascade": (
        """
        type user
        type doc
          define editor: [user]
          define banned: [user]
          define viewer: editor but not banned
          define muted: [user]
          define approver: viewer but not muted
        """,
        [mk_tuple("...", "user", "alice", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "muted", "doc", "d1"),
         mk_tuple("...", "user", "carol", "editor", "doc", "d1"),
         mk_tuple("...", "user", "carol", "banned", "doc", "d1")],
        (),
    ),
    "taint_union_over_boolean": (
        # §3.1 taint: a plain union OVER a boolean relation must still serve
        # star-covered members. viewer is boolean (star base minus blocked);
        # approver unions viewer with admin.
        """
        type user
        type doc
          define base: [user:*]
          define blocked: [user]
          define viewer: base but not blocked
          define admin: [user]
          define approver: viewer or admin
        """,
        [mk_tuple("...", "user", "*", "base", "doc", "d1"),
         mk_tuple("...", "user", "mallory", "blocked", "doc", "d1"),
         mk_tuple("...", "user", "root", "admin", "doc", "d1")],
        (),
    ),
    "nested_boolean": (
        """
        type user
        type doc
          define editor: [user]
          define required: [user]
          define banned: [user]
          define viewer: (editor and required) but not banned
        """,
        [mk_tuple("...", "user", "alice", "editor", "doc", "d1"),
         mk_tuple("...", "user", "alice", "required", "doc", "d1"),
         mk_tuple("...", "user", "bob", "editor", "doc", "d1"),
         mk_tuple("...", "user", "bob", "required", "doc", "d1"),
         mk_tuple("...", "user", "bob", "banned", "doc", "d1")],
        (),
    ),
    "double_exclusion": (
        # a but not (b but not c): parenthesized nested exclusion as the subtrahend.
        """
        type user
        type doc
          define a: [user]
          define b: [user]
          define c: [user]
          define viewer: a but not (b but not c)
        """,
        [mk_tuple("...", "user", "alice", "a", "doc", "d1"),
         mk_tuple("...", "user", "bob", "a", "doc", "d1"),
         mk_tuple("...", "user", "bob", "b", "doc", "d1"),
         mk_tuple("...", "user", "carol", "a", "doc", "d1"),
         mk_tuple("...", "user", "carol", "b", "doc", "d1"),
         mk_tuple("...", "user", "carol", "c", "doc", "d1")],
        (),
    ),
    "demorgans": (
        # (A but not B) vs (not (not A or B)) style — exercise nested exclusion.
        """
        type user
        type doc
          define a: [user]
          define b: [user]
          define lhs: a but not b
          define rhs: a but not (a and b)
        """,
        [mk_tuple("...", "user", "alice", "a", "doc", "d1"),
         mk_tuple("...", "user", "bob", "a", "doc", "d1"),
         mk_tuple("...", "user", "bob", "b", "doc", "d1"),
         mk_tuple("...", "user", "carol", "b", "doc", "d1")],
        (),
    ),
    "cross_stratum_resettle": (
        # Phase 6 attack probe (the 12h stale-edge shape, operationalized): alice
        # is granted `e` (settling v=TRUE and the stratum-2 a=TRUE, materializing
        # a's derived edge), THEN banned at stratum 1 — the later cascade must
        # RETRACT the stale stratum-2 derived edge (the diffing pass,
        # processor.py:359-367). Write ORDER is load-bearing: settle-then-retract.
        """
        type user
        type doc
          define e: [user]
          define b: [user]
          define v: e but not b
          define m: [user]
          define a: v but not m
        """,
        [mk_tuple("...", "user", "alice", "e", "doc", "d1"),
         mk_tuple("...", "user", "dave", "e", "doc", "d1"),
         mk_tuple("...", "user", "dave", "m", "doc", "d1"),
         mk_tuple("...", "user", "alice", "b", "doc", "d1")],
        (),
    ),
    "star_two_strata_churn": (
        # Phase 6 attack probe #2: a bare star grant feeding TWO strata, the
        # exclusions arriving AFTER the star settles (add-only churn: the
        # stratum-2 residue must re-settle under later stratum-1 negatives),
        # plus a second object's star grant interleaved.
        """
        type user
        type doc
          define e: [user:*]
          define b: [user]
          define v: e but not b
          define m: [user]
          define a: v but not m
        """,
        [mk_tuple("...", "user", "*", "e", "doc", "d1"),
         mk_tuple("...", "user", "mallory", "m", "doc", "d1"),
         mk_tuple("...", "user", "mallory", "b", "doc", "d1"),
         mk_tuple("...", "user", "*", "e", "doc", "d2"),
         mk_tuple("...", "user", "zoe", "b", "doc", "d2")],
        (),
    ),
    "taint_union_userset_arm": (
        # Regression pin for the 2026-07-17 taint-filter fix (the stale userset-
        # sourced fanout edge). `approver = viewer or admin` unions a boolean
        # `viewer` with `admin`, and `admin` accepts a USERSET subject
        # (group#member). Before the taint filter on schemaRewrites, the Lean model
        # leaked a stale fanout edge group:eng#member -> approver (the union arm
        # firing on the userset-subject stored tuple) into the DRAINED state — a
        # real Lean-model-vs-Python state divergence. The taint filter routes the
        # derived `approver` off the fanout (as compile_ruleset does); the state
        # gate now pins that stale edge's absence.
        """
        type user
        type group
          define member: [user]
        type doc
          define base: [user:*]
          define blocked: [user]
          define viewer: base but not blocked
          define admin: [user, group#member]
          define approver: viewer or admin
        """,
        [mk_tuple("...", "user", "*", "base", "doc", "d1"),
         mk_tuple("...", "user", "mallory", "blocked", "doc", "d1"),
         mk_tuple("member", "group", "eng", "admin", "doc", "d1"),
         mk_tuple("...", "user", "alice", "member", "group", "eng")],
        (),
    ),
    "taint_computed_root_over_boolean": (
        # Computed roots taint too (compile_ruleset): `approver = viewer` is a bare
        # computed reference to a boolean relation, so `approver` is derived. In
        # scope since the 2026-07-17 fragment widening (ComputedOnly derived def,
        # union/computed roots no longer rejected by W4Fragment).
        """
        type user
        type doc
          define base: [user:*]
          define blocked: [user]
          define viewer: base but not blocked
          define approver: viewer
        """,
        [mk_tuple("...", "user", "*", "base", "doc", "d1"),
         mk_tuple("...", "user", "mallory", "blocked", "doc", "d1")],
        (),
    ),
}

# ---------------------------------------------------------------------------
# Phase 6 — graph-state conformance corpora (Lean graph model vs Python graph
# index). The Lean write model is add-only and W4Fragment-scoped; these are the
# corpora INSIDE the proved fragment (apples-to-apples with `graph_correct`):
#   * untainted schemas subsume via `w4Fragment_of_untainted` (needs only
#     wsBare/bareStar/ttuStarFree — all stars here are bare-subject grants);
#   * boolean schemas need ComputedOnly derived defs (boolean tree over computed
#     leaves) and <= two strata. The derived ROOT operator is UNRESTRICTED — an
#     inter/excl/union/computed root all qualify (the rootB gap CLOSED 2026-07-17,
#     `W4Fragment.rootB`/`RootBoolean` deleted; taint routing on `schemaRewrites`
#     now mirrors compile_ruleset).
# Excluded, with the honest reason (ROADMAP "W4 — honest gaps"):
#   * object_wildcard — the stored tuple has object name '*'; `BareStarStore`
#     requires stored objects concrete (gap: bareStar / W1b object-star tuples
#     are outside the operational chain's store scope).
# Attack-first finding (2026-07-12k, scratch probe, deleted after recording):
# the object_wildcard corpus — and the (now in-fragment) union-rooted corpus —
# showed 0 lean-graph/py-graph mismatches. The remaining exclusion is PROOF-scope-
# driven (what graph_correct covers), not an observed behavioral divergence; do
# not read it as a known model/Python disagreement.
# ---------------------------------------------------------------------------

GRAPH_FRAGMENT: tuple[str, ...] = (
    "deep_grid",
    "union_computed",
    "group_userset",
    "ttu",
    "wildcard_public",
    "wildcard_group_member",
    "boolean_exclusion",
    "boolean_intersection",
    "boolean_star_exclusion",
    "two_stratum_cascade",
    "taint_union_over_boolean",
    "taint_union_userset_arm",
    "taint_computed_root_over_boolean",
    "nested_boolean",
    "double_exclusion",
    "demorgans",
    "cross_stratum_resettle",
    "star_two_strata_churn",
)

# ---------------------------------------------------------------------------
# TTU userset-subject corpora — SPEC-SIDE ONLY (spec `sem` × oracle × set engine).
#
# These pin the Lean spec `sem` on the exact shapes the 2026-07-13 X4 fix
# adjudicated to the ORACLE: userset-shaped subjects whose truth flows through a
# TTU's stored tupleset parents (the from-chain identity rule, and the
# cross-object membership lift). The boolean spec is SILENT on those shapes
# (docs/spec-deviations.md 2026-07-13; formal/FINAL_REVIEW.md §3), so the fix
# followed the oracle — and `sem` is the formal trust root that oracle stands in
# for. These corpora check the choice is anchored: probed 2026-07-13, sem ==
# oracle == set engine on every grid query (the from-chain userset answers True
# on all three, matching the oracle the graph was fixed toward).
#
# DELIBERATELY separate from SCHEMAS (and thus from GRAPH_FRAGMENT): the shapes
# are OUTSIDE `W4Fragment` (`computedOnly` bans `ttu` leaves in derived defs;
# `PDerivedTTU` plan leaves are a documented proof gap — FINAL_REVIEW §3 item 3),
# so the graph conformance / state / remove gates must NOT carry them. Only
# test_conformance_spec's comparisons consume them — those are full-scope (T1
# places no fragment restriction on the set engine; `sem`/oracle are the
# reference for every stratifiable schema).
# ---------------------------------------------------------------------------

TTU_USERSET_SCHEMAS: dict[str, tuple[str, list, tuple]] = {
    # (a) X4 shape (a): from-chain userset through an UNTAINTED TTU. doc:d1#viewer
    # is a member of `inherited` on doc:d2 — d2's parent is d1, and d1#viewer
    # trivially has viewer on d1 (the from-chain identity rule the graph's
    # untainted TTU path materializes as a rewrite edge).
    "ttu_fromchain": (
        """
        type user
        type doc
          define viewer: [user]
          define parent: [doc]
          define inherited: viewer from parent
        """,
        [mk_tuple("...", "user", "alice", "viewer", "doc", "d1"),
         mk_tuple("...", "doc", "d1", "parent", "doc", "d2")],
        (),
    ),
    # (b) X4 shape (b): cross-object userset LIFT through a TTU. group:g1#member
    # is an editor of doc:d2 via a userset grant, and doc:d2 is the parent of
    # doc:d1, so group:g1#member is a member of `inherited` on doc:d1 — a
    # membership that flows across objects (the graph residue-`upos` lift).
    "ttu_fromchain_group": (
        """
        type user
        type group
          define member: [user]
        type doc
          define editor: [user, group#member]
          define parent: [doc]
          define inherited: editor from parent
        """,
        [mk_tuple("...", "user", "alice", "member", "group", "g1"),
         mk_tuple("member", "group", "g1", "editor", "doc", "d2"),
         mk_tuple("...", "doc", "d2", "parent", "doc", "d1")],
        (),
    ),
    # (c) from-chain userset through a TTU over a DERIVED (boolean) target
    # relation: folder:f1#viewer (viewer = editor but not banned) is a member of
    # `inherited` on doc:d1 (d1's parent is f1). The genuinely derived-TTU case
    # central to X4 (cf. demorgans_reverse.fga), minimized.
    "derived_ttu_fromchain": (
        """
        type user
        type folder
          define editor: [user]
          define banned: [user]
          define viewer: editor but not banned
        type doc
          define parent: [folder]
          define inherited: viewer from parent
        """,
        [mk_tuple("...", "user", "alice", "editor", "folder", "f1"),
         mk_tuple("...", "folder", "f1", "parent", "doc", "d1")],
        (),
    ),
}

# ---------------------------------------------------------------------------
# Self-referential-tuple corpora — SPEC-SIDE ONLY (spec `sem` × oracle × set engine).
#
# Anchors `sem` on self-referential tuples (subject entity == object entity), which
# OpenFGA supports (the `IsSelfDefining` concept / self-defining attribute-marker
# idiom). This is the trust-root confirmation for the 2026-07-13 self-referential
# fix (index_v4 node-GC/implicit canonicalization; docs/spec-deviations.md): the fix
# followed the oracle, and `sem` agrees. Probed 2026-07-13: sem == oracle == set
# engine on every grid query, including the self-referential rows.
#
# Separate from SCHEMAS (and GRAPH_FRAGMENT): both shapes are outside `W4Fragment`
# (`self_flag` has Direct arms under a boolean — genuine storage leaves, not
# `computedOnly`; `self_ttu_parent` is a TTU over a derived relation), so the
# graph-side gates must not carry them. Only test_conformance_spec's full-scope
# comparisons consume them (T1 places no fragment restriction on the set engine).
# ---------------------------------------------------------------------------

SELF_REFERENTIAL_SCHEMAS: dict[str, tuple[str, list, tuple]] = {
    # OpenFGA self-defining / attribute-marker idiom: a self-referential tuple as a
    # boolean flag, gating a derived (exclusion) relation. `resource:r1 activated
    # resource:r1` sets the flag; `usable = activated but not deprecated` reads it.
    "self_flag": (
        """
        type user
        type resource
          define activated: [resource]
          define deprecated: [resource]
          define usable: activated but not deprecated
        """,
        [mk_tuple("...", "resource", "r1", "activated", "resource", "r1"),
         mk_tuple("...", "resource", "r2", "activated", "resource", "r2"),
         mk_tuple("...", "resource", "r2", "deprecated", "resource", "r2")],
        (),
    ),
    # The fixed-bug shape: a self-referential TTU parent (doc:d1 parent doc:d1)
    # feeding a derived relation read back on the SAME object. The from-chain
    # userset doc:d1#r0 is a member of r4@d1 by the identity rule (self-parent).
    "self_ttu_parent": (
        """
        type user
        type doc
          define parent: [doc]
          define r0: [user] and [user]
          define r4: r0 from parent or [user, user:*]
        """,
        [mk_tuple("...", "doc", "d1", "parent", "doc", "d1"),
         mk_tuple("...", "user", "u1", "r0", "doc", "d1")],
        (),
    ),
}
