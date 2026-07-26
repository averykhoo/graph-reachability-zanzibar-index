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
    "direct_arm_exclusion": (
        # Direct-arm boolean shape (moved INTO SCHEMAS/GRAPH_FRAGMENT 2026-07-20e,
        # the #1 leg-5d widening): `approver = [user] but not banned` — the
        # exclusion's BASE is a **Direct storage arm ON the derived relation**
        # (AST `excl (direct[user]) (computed banned)`), not a separately-named
        # computed relation like `boolean_exclusion`'s `editor`. Lean coverage is
        # the C-chain T2b `graph_correct_w3d2_d` (CascadeStrataResettle.lean,
        # audited; witness `W4WitnessDirect` = exactly this corpus in compiled
        # form). NOTE the shape is still outside `W4Fragment`/the E-chain final
        # theorems (`computedOnly`) — the add-only graph/state gates carry it on
        # the C-chain theorem's scope; the REMOVE-stream Lean gate cannot (see
        # test_conformance_remove_graph._REMOVE_EXCLUDED: the model's remove
        # guard is plain StoreValidRules, which provably rejects any store
        # holding a Direct-arm-under-exclusion tuple — `hNoUD`, 2026-07-20d/e).
        # Store exercises the full truth table:
        #   alice — approver only            -> True  (Direct arm, not excluded)
        #   bob   — approver AND banned      -> False (excluded by the subtrahend)
        #   carol — banned only              -> False (never granted approver)
        #   (ghost / dave — nothing          -> False, via the grid's ghost subject)
        """
        type user
        type doc
          define banned: [user]
          define approver: [user] but not banned
        """,
        [mk_tuple("...", "user", "alice", "approver", "doc", "d1"),
         mk_tuple("...", "user", "bob", "approver", "doc", "d1"),
         mk_tuple("...", "user", "bob", "banned", "doc", "d1"),
         mk_tuple("...", "user", "carol", "banned", "doc", "d1")],
        (),
    ),
    # ---------------------------------------------------------------------
    # n-ARY (>= 3 arm) OPERATORS — ZT-P4-4, added 2026-07-26.
    #
    # BEFORE these two corpora every `or`/`and` in the entire conformance harness
    # was BINARY, so `encode.py::_fold_binary` — the documented modeling bridge
    # from the n-ary `Union`/`Intersection` BOTH parsers build to Lean's strictly
    # binary `Expr.union`/`Expr.inter` — never once produced a NESTED tree: its
    # loop body ran exactly once per node and the fold was an identity in
    # practice. At arity 3 it runs twice, so the left-association it commits to is
    # genuinely on trial:
    #     any_of -> union (union (computed a) (computed b)) (computed c)
    #     all_of -> inter (inter (computed a) (computed b)) (computed c)
    # `_fold_binary` runs inside `schema_to_json`, i.e. for EVERY zcli mode (spec
    # as well as graph), so the bridge is exercised on every leg these corpora
    # reach — not only the graph ones.
    #
    # SCOPE — both are inside GraphAdmission + W4Fragment, hence in GRAPH_FRAGMENT
    # (unlike `direct_arm_exclusion`; see that entry and
    # test_conformance_graph.py's classification guard). Field by field
    # (FullScope.lean):
    #   * computedOnly — `all_of` is the only DERIVED def in either schema
    #     (`any_of` is a plain union of untainted relations, hence untainted) and
    #     its leaves are all COMPUTED. `ComputedOnly` recurses through
    #     union/inter/excl, so the left-folded nest is `ComputedOnly` exactly when
    #     its leaves are. No `direct`/`ttu` leaf under a derived def anywhere.
    #   * twoStrata — measured 0 strata (`nary_union`, untainted) and 1 stratum
    #     (`nary_intersection`). n-ary arity does NOT raise the stratum count:
    #     arity widens a def's FAN-IN, depth deepens the dependency CHAIN, and
    #     only depth feeds `twoStrata`. That is exactly why n-ary can be gated
    #     graph-side while >= 3 strata (MULTI_STRATUM_SCHEMAS below) cannot.
    #   * wsBare / bareStar / ttuStarFree — no wildcard restriction, no stored
    #     star subject, no TTU: all three hold vacuously.
    #   * term — no TTU (NoTtuTarget vacuous) and no stored tuple uses a derived
    #     relation as its subject predicate (NoStoreSubjectR).
    #   * storeValid — every stored tuple lands on a/b/c, each a plain `[user]`
    #     Direct def, so `exprDirects` is non-empty and matches. (This is the
    #     field `direct_arm_exclusion` provably FAILS.)
    #
    # WHY TWO SMALL CORPORA INSTEAD OF ONE (a measured runtime wall in the LEAN
    # MODEL, recorded rather than papered over). The first version was a single
    # corpus carrying `any_of`, `all_of` and a DERIVED 3-arm union
    # `gated: all_of or a or b`. All of it is scope-clean and every Python backend
    # handles it, but the Lean OPERATIONAL model does not finish on it. Measured
    # 2026-07-26, zcli `graph`/`graph-state`, per-spawn timeout 120 s:
    #     6 relations, 2 strata (with `gated`):  3 tuples 0.2 s -> 4 tuples TIMEOUT
    #     5 relations, 1 stratum (no `gated`), by DISTINCT SUBJECT count:
    #         2 subj 0.1 s · 3 subj 0.3 s · 4 subj 5.5 s · 5 subj 115 s
    #     4 relations, derived inter only:  3 subj 0.6 s · 4 subj TIMEOUT
    # A cliff, not a slope, driven by the round-2 job enumeration over distinct
    # subjects. Two corpora at 3-4 subjects each stay at ~0.1-0.6 s and together
    # carry MORE arm-witness coverage than the single 8-tuple version could.
    # Consequences recorded honestly: the DERIVED n-ary union arm is not gated
    # anywhere Lean-side. `_fold_binary` is a pure AST->JSON transform that does
    # not care whether a relation is derived, so the arity hole is closed; what is
    # NOT covered is the Lean operational model on a derived-reads-derived n-ary
    # union, and that is a model-runtime limit, not a scope decision.
    # ---------------------------------------------------------------------
    "nary_union": (
        # UNTAINTED 3-arm union. Store: ua/ub/uc are each in EXACTLY ONE arm, so
        # all three arms are load-bearing (drop any arm and that member flips);
        # `alice` is in all three so the union is not just a disjoint relabeling.
        #   alice — a,b,c  -> any_of T
        #   ua    — a      -> any_of T   (arm 1 bites)
        #   ub    — b      -> any_of T   (arm 2 bites)
        #   uc    — c      -> any_of T   (arm 3 bites — the arm that only exists
        #                                 at arity >= 3)
        """
        type user
        type doc
          define a: [user]
          define b: [user]
          define c: [user]
          define any_of: a or b or c
        """,
        [mk_tuple("...", "user", "alice", "a", "doc", "d1"),
         mk_tuple("...", "user", "alice", "b", "doc", "d1"),
         mk_tuple("...", "user", "alice", "c", "doc", "d1"),
         mk_tuple("...", "user", "ua", "a", "doc", "d1"),
         mk_tuple("...", "user", "ub", "b", "doc", "d1"),
         mk_tuple("...", "user", "uc", "c", "doc", "d1")],
        (),
    ),
    "nary_intersection": (
        # DERIVED 3-arm intersection (1 stratum). Store held to THREE distinct
        # subjects — the measured Lean-model cliff is at four (see the block
        # above). Witnesses:
        #   alice — a,b,c  -> all_of T   (non-empty: not vacuously false)
        #   bob   — a,b    -> all_of F   (fails ONLY arm 3 — the arm that only
        #                                 exists at arity >= 3; at `a and b` bob
        #                                 would be a member, so the fold's extra
        #                                 arm demonstrably bites)
        #   carol — b,c    -> all_of F   (fails ONLY arm 1)
        # Arm 2 sits at the fold's depth-1 position, which every pre-existing
        # binary intersection corpus (`boolean_intersection`, `nested_boolean`)
        # already covers; adding its witness would cost a 4th subject and the
        # corpus would stop running under the zcli timeout.
        """
        type user
        type doc
          define a: [user]
          define b: [user]
          define c: [user]
          define all_of: a and b and c
        """,
        [mk_tuple("...", "user", "alice", "a", "doc", "d1"),
         mk_tuple("...", "user", "alice", "b", "doc", "d1"),
         mk_tuple("...", "user", "alice", "c", "doc", "d1"),
         mk_tuple("...", "user", "bob", "a", "doc", "d1"),
         mk_tuple("...", "user", "bob", "b", "doc", "d1"),
         mk_tuple("...", "user", "carol", "b", "doc", "d1"),
         mk_tuple("...", "user", "carol", "c", "doc", "d1")],
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
#   * nary_union / nary_intersection (added 2026-07-26) are in-fragment on every
#     W4Fragment field — the per-field argument is in the n-ary block in SCHEMAS.
#     n-ary arity widens fan-in, not dependency depth, so `twoStrata` is
#     untouched (measured: 0 and 1 strata).
#   * direct_arm_exclusion (added 2026-07-20e) rides the C-CHAIN Direct-arm T2b
#     `graph_correct_w3d2_d` instead of the E-chain `graph_correct` (its Direct
#     storage arm is outside `W4Fragment.computedOnly`); the witness
#     `W4WitnessDirect` pins the corpus-to-theorem tie. Its add-only zcli runs
#     were attack-probed first (full truth table `check = sem`, drained); the
#     remove-stream Lean gate excludes it (see its entry above).
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
    "direct_arm_exclusion",
    "nary_union",
    "nary_intersection",
)

# ---------------------------------------------------------------------------
# >= 3 STRATA corpora — SPEC-SIDE ONLY (spec `sem` × oracle × set engine), plus a
# PYTHON-ONLY graph differential (test_conformance_nary_strata.py). NEVER
# GRAPH_FRAGMENT.
#
# Added 2026-07-26 for ZT-P4-4: measured across every corpus in this file, the
# maximum stratum count anywhere was TWO, so Python's >= 3-stratum cascade path —
# `DeltaProcessor.run_cascade`'s per-stratum loop past round 2 — was reached by
# nothing in the formal harness at all (tests/ reaches it only via
# `tests/test_bulk_build.py`'s `demorgan1`).
#
# WHY NOT GRAPH_FRAGMENT (the scope discipline — this is the mistake ZT-P3-3
# caught, and repeating it would be worse the second time):
#   * `W4Fragment.twoStrata` (FullScope.lean) is literally "at most TWO derived
#     strata dependency-wise", and its docstring records the restriction as
#     ATTACK-CONFIRMED load-bearing: "a 3-stratum schema fires the round-2
#     reject, CascadeStrata.lean".
#   * the Lean operational model's cascade is `runCascade2` — a FIXED two rounds.
#     A 3-stratum schema's third stratum has no round to settle in, so the model
#     would answer from a state Python has already advanced past.
#   * zcli's graph mode does NOT gate on `GraphAdmission`/`W4Fragment` (it exits
#     nonzero only on run failure (rc 2) and non-drained-ness (rc 3)), so an
#     out-of-fragment corpus placed in `GRAPH_FRAGMENT` does NOT fail loudly — it
#     silently compares two models that no theorem relates. That is exactly how
#     `direct_arm_exclusion` came to be described as theorem-backed when it is
#     not.
# So the Lean-side comparison here is `sem` ONLY (the spec is a pure function of
# the final store — no cascade, no rounds, no stratum bound), and the graph index
# is compared against the ORACLE and the SET ENGINE only, python-to-python.
# ---------------------------------------------------------------------------

MULTI_STRATUM_SCHEMAS: dict[str, tuple[str, list, tuple]] = {
    # A 4-relation exclusion CHAIN: each derived relation subtracts from the
    # previous one, so the dependency depth (not the fan-in) forces the stratum
    # count. Measured: `len(compile_ruleset(...).compiled.strata) == 3`
    # (stratum 1 `s1`, stratum 2 `s2`, stratum 3 `s3`) — pinned by
    # `test_conformance_nary_strata.py::test_three_strata_corpus_features`.
    #
    # Store makes every stratum load-bearing (each removes exactly one principal,
    # and each principal is removed by exactly one stratum):
    #     e  = {alice, bob, carol, dave}
    #     s1 = e  \ b1({bob})   = {alice, carol, dave}
    #     s2 = s1 \ b2({carol}) = {alice, dave}
    #     s3 = s2 \ b3({dave})  = {alice}
    # so `check(bob, s1)`, `check(carol, s2)` and `check(dave, s3)` are each False
    # for a DIFFERENT stratum's reason — collapse the cascade to two rounds and
    # `dave in s3` flips.
    "three_strata_chain": (
        """
        type user
        type doc
          define e: [user]
          define b1: [user]
          define b2: [user]
          define b3: [user]
          define s1: e but not b1
          define s2: s1 but not b2
          define s3: s2 but not b3
        """,
        [mk_tuple("...", "user", "alice", "e", "doc", "d1"),
         mk_tuple("...", "user", "bob", "e", "doc", "d1"),
         mk_tuple("...", "user", "carol", "e", "doc", "d1"),
         mk_tuple("...", "user", "dave", "e", "doc", "d1"),
         mk_tuple("...", "user", "bob", "b1", "doc", "d1"),
         mk_tuple("...", "user", "carol", "b2", "doc", "d1"),
         mk_tuple("...", "user", "dave", "b3", "doc", "d1")],
        (),
    ),
}

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

# ---------------------------------------------------------------------------
# Direct-arm boolean corpora — the names of the SCHEMAS entries whose derived
# defs carry a **Direct arm under an exclusion** (`approver := (direct[user])
# but not banned`, AST `excl (direct[user]) (computed banned)`). The entries
# LIVE in SCHEMAS/GRAPH_FRAGMENT since 2026-07-20e (the #1 leg-5d widening —
# Lean coverage via the C-chain `graph_correct_w3d2_d` + `W4WitnessDirect`,
# see the `direct_arm_exclusion` entry's comment); this name list survives so
# the dedicated python-only 3-backend differential
# (`test_conformance_direct_arm.py`: oracle == set engine == real graph index
# under BOTH SetOps + the exhaustive small-store attack) keeps its focused
# parametrization.
# ---------------------------------------------------------------------------

DIRECT_ARM_NAMES: tuple[str, ...] = ("direct_arm_exclusion",)


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
