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
    "nary_union_derived4": (
        # ZT-P4-4 follow-up (2026-07-27). Re-measuring the arity histogram over
        # all 69 schemas the harness then read (28 curated + 40 generated + this
        # file's dicts; **73** as of 2026-07-29 — 33 curated + 40 generated)
        # found the MAXIMUM operator arity anywhere was 3, reached
        # by exactly TWO nodes — `nary_union` and `nary_intersection` — and both
        # of them are UNTAINTED. So `encode.py::_fold_binary`'s loop had still
        # never run more than twice, and the residue the n-ary block below names
        # in as many words ("a DERIVED n-ary union is not gated Lean-side
        # anywhere") was still open.
        #
        # This corpus closes both at once: `any_of4` is a FOUR-arm union (the
        # first >= 4-arity operator in the harness — `_fold_binary` folds it to a
        # depth-3 left spine) whose last arm is the boolean `safe`, so `any_of4`
        # is itself DERIVED (measured strata: [[('doc','safe')],
        # [('doc','any_of4')]] — two, hence in-fragment).
        #
        # IN-FRAGMENT per field: `safe`/`any_of4` are ComputedOnly; twoStrata
        # holds (2); no wildcard restriction at all (wsBare, bareStar vacuous);
        # no TTU (ttuStarFree). MEASURED runtime 2026-07-27 against the round-2
        # subject cliff documented in the n-ary block: zcli spec 0.1 s,
        # graph-state 0.5 s, Python graph index 0.5 s — it stays cheap because
        # only ONE relation (`safe`) is boolean-side, so the model's round-2 job
        # enumeration sees two subjects, not five.
        #
        # Every arm is load-bearing (pinned in test_conformance_nary_strata.py):
        #   ua -> arm 1 only, ub -> arm 2 only, uc -> arm 3 only,
        #   us -> arm 4 (`safe`) only; ux holds `x` but is `blocked`, so it fails
        #   arm 4 and is NOT a member — the witness that the derived arm really
        #   evaluates its exclusion inside the fold.
        """
        type user
        type doc
          define a: [user]
          define b: [user]
          define c: [user]
          define x: [user]
          define blocked: [user]
          define safe: x but not blocked
          define any_of4: a or b or c or safe
        """,
        [mk_tuple("...", "user", "ua", "a", "doc", "d1"),
         mk_tuple("...", "user", "ub", "b", "doc", "d1"),
         mk_tuple("...", "user", "uc", "c", "doc", "d1"),
         mk_tuple("...", "user", "us", "x", "doc", "d1"),
         mk_tuple("...", "user", "ux", "x", "doc", "d1"),
         mk_tuple("...", "user", "ux", "blocked", "doc", "d1")],
        (),
    ),
    "residue_rich": (
        # ZT-P4-5(d) — the RESIDUE half of the state gate was near-vacuous.
        # Measured 2026-07-27 over the (then) 21 in-fragment corpora: only 5
        # produced ANY residue row (11 rows total, so 16 corpora compared two
        # EMPTY residue dicts), and EVERY one of those 11 rows had
        # |stars| == 1 and |neg| == 1 — i.e. `extractor.diff_states`' set
        # comparison on `stars`/`neg` had never been asked to distinguish two
        # elements from one. A singleton-vs-singleton compare cannot catch an
        # ordering, dedup or partial-recompute bug in the residue path.
        #
        # This corpus is the first with a MULTI-SHAPE `stars` and a MULTI-SUBJECT
        # `neg`, plus a `upos` member, on TWO derived keys at once:
        #   residue(doc:d1, viewer)   stars {(user,...),(svc,...)}  neg {mallory,eve}  upos {}
        #   residue(doc:d1, approver) stars {(user,...),(svc,...)}  neg {mallory,eve}  upos {group:eng#member}
        # (measured; pinned non-vacuously by test_conformance_state.py::
        # test_residue_rich_corpus_is_really_rich, so it cannot silently degrade).
        #
        # IN-FRAGMENT per field: derived defs `viewer`/`approver` are ComputedOnly
        # (no Direct arm on a derived def); two strata (viewer -> approver); all
        # star grants are BARE-predicate (`user:*`, `svc:*` — BareStarStore +
        # decision-15 hWSbare); no TTU at all (TtuStarFree); every stored subject
        # is concrete-or-star-bare-or-userset, all admitted. zcli `graph-state`
        # measured at 0.1 s (the model's round-2 subject cliff documented in the
        # n-ary block below bites at ~5 DISTINCT SUBJECTS on wide schemas; this
        # corpus has 5 and stays flat because only two of them are boolean-side).
        """
        type user
        type svc
        type group
          define member: [user]
        type doc
          define base: [user:*, svc:*]
          define blocked: [user]
          define admin: [user, group#member]
          define viewer: base but not blocked
          define approver: viewer or admin
        """,
        [mk_tuple("...", "user", "*", "base", "doc", "d1"),
         mk_tuple("...", "svc", "*", "base", "doc", "d1"),
         mk_tuple("...", "user", "mallory", "blocked", "doc", "d1"),
         mk_tuple("...", "user", "eve", "blocked", "doc", "d1"),
         mk_tuple("...", "user", "alice", "member", "group", "eng"),
         mk_tuple("member", "group", "eng", "admin", "doc", "d1")],
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
        # Direct-arm boolean shape (moved INTO SCHEMAS/GRAPH_FRAGMENT 2026-07-20e):
        # `approver = [user] but not banned` — the exclusion's BASE is a **Direct
        # storage arm ON the derived relation** (AST `excl (direct[user]) (computed
        # banned)`), not a separately-named computed relation like
        # `boolean_exclusion`'s `editor`. This is the canonical Zanzibar boolean
        # shape, and the whole E-chain Direct-arm widening arc exists for it.
        #
        # THEOREM-BACKED since 2026-08-05 (E-chain legs 5+6), and by a machine-checked
        # witness rather than a prose fragment argument. `FullScope.lean`'s
        # `W4WitnessDirect` is exactly this corpus in compiled form — `Sd` is the schema,
        # `Td4` is all four tuples below — and it carries `admission4 : GraphAdmission Sd
        # Td4`, `w4fragment4 : W4Fragment Sd Td4`, and `final_applies4`, the HEADLINE
        # `graph_correct` at that pair. All audited and statement-pinned.
        #
        # It was genuinely outside before, not mislabelled: `outside_old_admission4`
        # machine-checks `¬ StoreValidRules Sd Td4`, and `StoreValidRules` WAS
        # `GraphAdmission.storeValid`, so the headline theorems were VACUOUS here. Leg 5
        # rebased the bundles (`storeValid → StoreValidRulesD`; `computedOnly` → five
        # derived-def clauses). Both `outside_old_admission*` theorems are KEPT as the
        # proof that this was a widening and not a relabeling.
        #
        # TWO carve-outs remain, and neither is a divergence:
        #   * T2a `graph_reached_inv` takes a third bundle `W4NarrowT2a` that this store
        #     provably fails (`outside_narrow_t2a`). Probe D.3 machine-checked
        #     `Inv.negEdgeFree` FALSE on the `_d` fragment — a P6 leaf-family MODELLING
        #     limit; Python routes the write onto the leaf family, so the edge and the
        #     `neg` row live on different nodes (0 mismatches on the real backends).
        #   * the REMOVE-stream Lean gate still excludes it (see
        #     test_conformance_remove_graph._REMOVE_EXCLUDED): `removeGateB` decides
        #     plain `storeValidRulesB`. That is now the SOLE reason for the exclusion —
        #     the admission reason it used to carry is gone.
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
    # SCOPE — both are inside GraphAdmission + W4Fragment, hence in GRAPH_FRAGMENT.
    # (Until 2026-08-05 this line read "unlike `direct_arm_exclusion`"; E-chain leg 6
    # brought that corpus in too, so every GRAPH_FRAGMENT member is now inside. See
    # test_conformance_graph.py's classification guard.) Field by field
    # (FullScope.lean; the field was named `computedOnly` until leg 5 widened it to
    # `computedOrDirect` — the argument below is unchanged and holds a fortiori,
    # since `ComputedOrDirect` admits strictly more than `ComputedOnly`):
    #   * computedOrDirect — `all_of` is the only DERIVED def in either schema
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
    #     Direct def, so `exprDirects` is non-empty and matches. (This is the field
    #     `direct_arm_exclusion` provably failed under the pre-leg-5 `StoreValidRules`
    #     — `outside_old_admission4`. It satisfies the widened `StoreValidRulesD`
    #     through the DERIVED disjunct instead; these corpora take the untainted one,
    #     which is the old clause verbatim.)
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
    # ---------------------------------------------------------------------
    # RECONVERGENT corpora (added 2026-08-08) — the two shapes on which the
    # model's `rewriteClosure` used to over-count edge multiplicity relative to
    # Python's `RuleSet.apply` (`CORRESPONDENCE.md` §7.2 item 6, filed
    # 2026-07-28 as "no corpus exercises it today", adjudicated MODEL-side
    # 2026-08-08). "Reconvergent" = a schema whose rewrite DAG has two distinct
    # paths from one stored tuple to the same derived key, so a single write
    # materializes the same edge twice.
    #
    # They were added BEFORE the model fix, deliberately and in their own
    # commit, so the divergence went red under its own name rather than
    # arriving mixed into the fix's diff. The literal observed red is in the
    # commit message and `history/PROOF_STATUS.md` 2026-08-08b.
    #
    # ★ The control for the fix lives in `nary_union`, not here: its
    # `alice -> any_of` multiplicity of 3 comes from THREE stored tuples, one
    # occurrence in each one's rewrite closure. A dedup applied per-closure
    # must leave it at 3; a dedup applied to the assembled edge list would
    # collapse it to 1 and `nary_union` goes red. That is the difference
    # between mirroring Python's worklist dedup and mirroring nothing.
    # ---------------------------------------------------------------------
    "reconvergent_diamond": (
        # UNTAINTED diamond — `a` is reachable from a single `d` grant along two
        # distinct rewrite paths (via `b` and via `c`). Taint set is EMPTY, so
        # every edge here is compared on the untainted arm, where P3 compares
        # multiplicity EXACTLY. In-fragment via `w4Fragment_of_untainted`
        # (no wildcard restriction, no star tuple, no TTU).
        #
        # Two grants rather than one so the corpus also carries the rc>=2
        # survival shape the remove gate cares about: removing `alice@d` must
        # retract alice's four edges and leave bob's standing.
        """
        type user
        type doc
          define d: [user]
          define b: d
          define c: d
          define a: b or c
        """,
        [mk_tuple("...", "user", "alice", "d", "doc", "d1"),
         mk_tuple("...", "user", "bob", "d", "doc", "d1")],
        (),
    ),
    "reconvergent_derived": (
        # The same diamond with a BOOLEAN root on top — `viewer: e but not
        # banned` over the reconvergent `e`. Two divergence sites at once:
        #   * `alice -> d1#e`      untainted arm, compared EXACTLY (the red)
        #   * `alice -> d1#viewer` derived arm, exempted by P3 and pinned
        #                          instead by the derived-arm ledger golden
        # The second one is the reason this corpus exists rather than the
        # diamond alone: leg 7 forks `writeDirect` onto the leaf family, and
        # that contribution then lands on `viewer.0` — a leaf node, untainted
        # arm, compared exactly (scope doc §10.3).
        #
        # In-fragment, field by field against `FullScope.lean`:
        #   computedOnly — `viewer`'s def is `.excl (.computed e) (.computed
        #     banned)`; no Direct arm inside a derived def, so `storeValid`
        #     holds too. `e`/`b`/`c`/`d`/`banned` are all UNTAINTED (taint
        #     flows to relations that DEPEND on a boolean, not to the ones a
        #     boolean reads).
        #   twoStrata — one derived relation, one stratum.
        #   wsBare / bareStar / ttuStarFree / NoTtuTarget — vacuous (no
        #     wildcard restriction anywhere, no star tuple, no TTU).
        #   NoStoreSubjectR — every stored subject predicate is `...`.
        # `bob` is granted and then banned, so the exclusion arm is
        # load-bearing rather than decorative: drop `banned` from the store and
        # bob flips to a member.
        """
        type user
        type doc
          define d: [user]
          define banned: [user]
          define b: d
          define c: d
          define e: b or c
          define viewer: e but not banned
        """,
        [mk_tuple("...", "user", "alice", "d", "doc", "d1"),
         mk_tuple("...", "user", "bob", "d", "doc", "d1"),
         mk_tuple("...", "user", "bob", "banned", "doc", "d1")],
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
#   * direct_arm_exclusion (added 2026-07-20e) rode the C-CHAIN Direct-arm T2b
#     `graph_correct_w3d2_d` until 2026-08-05; since E-chain legs 5+6 it rides the
#     HEADLINE `graph_correct` like every other entry, witnessed at its own four-tuple
#     store by `W4WitnessDirect.final_applies4`. Its add-only zcli runs were
#     attack-probed first (full truth table `check = sem`, drained). The remove-stream
#     Lean gate still excludes it, now on remove-guard grounds only (see its entry).
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
    "nary_union_derived4",
    "residue_rich",
    #   * reconvergent_diamond / reconvergent_derived (added 2026-08-08) — the
    #     per-field arguments are in their SCHEMAS entries. Both are here on
    #     purpose: the divergence they exercise is a GRAPH-STATE one (edge
    #     multiplicity), so a spec-side-only placement would compare nothing.
    "reconvergent_diamond",
    "reconvergent_derived",
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
#     `direct_arm_exclusion` came to be described as theorem-backed in 2026-07-20e
#     when it was not (corrected 2026-07-26, ZT-P3-3). It IS theorem-backed as of
#     2026-08-05 — but by `W4WitnessDirect.final_applies4`, not by having been put
#     in the list. The hazard this bullet describes is unchanged.
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
# are OUTSIDE `W4Fragment` (`computedOrDirect` — `computedOnly` before leg 5 — still
# maps `.ttu` to `False`, so `ttu` leaves in derived defs remain banned;
# `PDerivedTTU` plan leaves are a documented proof gap — FINAL_REVIEW §3 item 3),
# so the graph conformance / state / remove gates must NOT carry them. Only
# test_conformance_spec's comparisons consume them — those are full-scope (T1
# places no fragment restriction on the set engine; `sem`/oracle are the
# reference for every stratifiable schema).
#
# The dict has since grown two more OUT-OF-W4Fragment families that are equally
# spec-clean and equally graph-ungated Lean-side (`derived_userset` 2026-07-27,
# and `wildcard_userset` + `derived_tupleset_ttu` 2026-07-28). Each entry carries
# its OWN per-field scope argument in situ — read the entry, not this header. The
# two 2026-07-28 additions additionally carry a PYTHON-ONLY three-backend
# differential (oracle == set engine == real graph index, both SetOps) in
# `test_conformance_nary_strata.py`, because the graph index ADMITS both shapes
# and answers them correctly; that leg makes no Lean claim whatsoever, which is
# exactly why it is allowed where `GRAPH_FRAGMENT` is not.
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
    # (d) **`PDerivedUserset`** — a userset restriction `[group#member]` whose
    # PREDICATE is derived (`member: base but not kicked`). Added 2026-07-27
    # (Item-4(b) board finding). Measured that day over all 69 schemas the
    # conformance harness then read (28 curated + 40 generated +
    # three_strata_chain; **73** as of 2026-07-29 — 33 curated + 40 generated),
    # by walking every `RuleSet.compiled.plans` leaf: the leaf-kind histogram was
    #   closure 211 · derived-computed 42 · derived-ttu 50 · derived-userset 0
    # — i.e. `zanzibar_utils_v1.py::PDerivedUserset` (and
    # `::PDerivedTuplesetTTU`) were compiled by NO corpus at all, in exactly the
    # plan-leaf area where the X4 adjudication found five real divergences and
    # where `tests/test_lookup_oracle.py` still carries regression pins. This
    # corpus closes the `derived-userset` half.
    #
    # SCOPE: spec-side only (Lean `sem` x oracle x set engine, via
    # `test_conformance_spec.py`) — never `GRAPH_FRAGMENT`.
    # `FullScope.lean::W4Fragment`'s derived-def clause (`computedOrDirect` since
    # leg 5, `computedOnly` before it — both map `.ttu` to `False`) explicitly excludes
    # `PDerivedTTU`/`PDerivedUserset` plan leaves ("out of scope (W3a decision)",
    # `FullScope.lean` W4Fragment doc), and `term`/`NoStoreSubjectR` forbids the
    # stored `group:g1#member` tuple this corpus needs, so a Lean OPERATIONAL
    # comparison would sit outside every theorem that covers it (the ZT-P3-3
    # mistake). `sem` is a pure function of the store with no fragment
    # hypotheses, so the spec leg is scope-clean.
    #
    # Verified 2026-07-27 before landing: the compile really produces a
    # `derived-userset` leaf (`Plan(('doc','viewer'), tree=PDerivedUserset(...),
    # leaves=(LeafSpec('viewer.0','derived-userset',...),))`, 2 strata), and
    # oracle == set engine == real graph index over the full 126-query grid —
    # alice (member) True, bob (kicked out of `member`) False.
    "derived_userset": (
        """
        type user
        type group
          define base: [user]
          define kicked: [user]
          define member: base but not kicked
        type doc
          define viewer: [group#member]
        """,
        [mk_tuple("...", "user", "alice", "base", "group", "g1"),
         mk_tuple("...", "user", "bob", "base", "group", "g1"),
         mk_tuple("...", "user", "bob", "kicked", "group", "g1"),
         mk_tuple("member", "group", "g1", "viewer", "doc", "d1")],
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
    # (e) **WILDCARD USERSET `[T:*#p]`** — "any instance of T's `p`". Added
    # 2026-07-28 (board item C). Measured 2026-07-26 (ZT-P4-4) and re-measured
    # 2026-07-27: wildcard usersets were at ZERO coverage across the whole
    # conformance harness — no curated corpus and no generated schema emitted a
    # single `T:*#p` restriction, so the entire non-bare half of
    # `derive_schema_info`'s `subject_wildcard_shapes` / `bridged_in_shapes`
    # machinery (and the set engine's star-userset `MemberSet` arm) was never
    # differentially compared against `sem`.
    #
    # REACHABILITY, established empirically before writing this (the finding as
    # filed reads wider than the reachable surface): a wildcard userset over a
    # DERIVED relation is a deliberate scope rejection —
    # `zanzibar_utils_v1.py::_build_plan_tree`'s `Direct` arm raises
    # `UnsupportedByGraphIndex` ("needs symbolic composition through residues"),
    # so `[group:*#member]` with `member: base but not kicked` cannot be compiled
    # at all and cannot be a corpus here (the plan-leaf coverage floor calls
    # `parse_openfga_schema` on every entry of this dict and would raise). Over an
    # UNTAINTED relation, however, the shape compiles and runs on BOTH backends:
    # measured 2026-07-28, oracle == set engine == real graph index == Lean `sem`
    # over the full 210-query grid (14 True). That untainted surface IS the
    # reachable one, and it is what this corpus covers.
    #
    # SCOPE: spec-side (Lean `sem` × oracle × set engine, `test_conformance_spec`)
    # + a PYTHON-ONLY three-backend differential
    # (`test_conformance_nary_strata.py::test_wildcard_userset_three_way`).
    # NEVER `GRAPH_FRAGMENT`: `FullScope.lean::W4Fragment.wsBare` is literally
    # `∀ sh ∈ wildcardShapes S, sh.2 = BARE`, and this schema's shape set contains
    # `(group, member)` — non-bare by construction — so `wsBare` is FALSE here and
    # every theorem routed through `graph_correct` says nothing about this corpus.
    # `wsBare`'s own doc comment records the asymmetry deliberately ("Python
    # rejects wildcard USERSETS only over derived relations; over untainted ones
    # they are admitted"), i.e. this is a KNOWN Lean-side gap, not a discovery.
    # zcli would NOT refuse it (it gates on runtime admission rc 2 and drainedness
    # rc 3, never on the fragment), so placing it in `GRAPH_FRAGMENT` would
    # silently compare two models no theorem relates — the ZT-P3-3 mistake.
    #
    # Load-bearing store (pinned by `test_wildcard_userset_corpus_features`):
    #   alice  — member of g1 only        -> viewer via the STAR userset, can_view
    #   bob    — member of g2, banned     -> viewer via the star, NOT can_view
    #                                        (the exclusion bites on star-derived
    #                                         membership, not just on stored ones)
    #   carol  — concrete `viewer` grant  -> the non-star arm of the same Direct,
    #                                        so the star is not the only path
    #   dave   — in no group              -> NOT viewer (strict ∀⇒∃: the star
    #                                        needs SOME group he is a member of)
    #   group:ghost#member                -> viewer (a never-stored group's
    #                                        userset is covered by the star —
    #                                        spec §probe-2 ghost-subject parity)
    "wildcard_userset": (
        """
        type user
        type group
          define member: [user]
        type doc
          define viewer: [user, group:*#member]
          define banned: [user]
          define can_view: viewer but not banned
        """,
        [mk_tuple("...", "user", "alice", "member", "group", "g1"),
         mk_tuple("...", "user", "bob", "member", "group", "g2"),
         mk_tuple("member", "group", "*", "viewer", "doc", "d1"),
         mk_tuple("...", "user", "carol", "viewer", "doc", "d1"),
         mk_tuple("...", "user", "bob", "banned", "doc", "d1")],
        (),
    ),
    # (f) **`PDerivedTuplesetTTU`** — `target from tupleset` where the TUPLESET
    # relation is itself DERIVED. Added 2026-07-28 (board item C); this was the
    # last plan-leaf kind produced by NO corpus (histogram 2026-07-27 over all 69
    # schemas the harness reads: closure 211 · derived-computed 42 ·
    # derived-ttu 50 · derived-userset 0 · derived-tupleset-ttu 0), and it was
    # deliberately left OUT of the coverage floor rather than faked.
    #
    # REACHABILITY: it is reachable, and non-vacuously so — but ONLY when the
    # derived tupleset relation carries a Direct restriction. `compile_ruleset`
    # emits the leaf whenever `(object_type, ttu.tupleset_rel)` is tainted
    # (`_build_plan_tree`'s `TTU` arm), yet the pinned Zanzibar semantics are that
    # **TTU parents are the STORED tupleset tuples, never computed membership**
    # (docs/spec-deviations.md 2026-07-07 P5 #1), so a derived tupleset with no
    # Direct restrictions holds no stored tuples and its dependent TTU is
    # constantly EMPTY — which is exactly why `demorgans_law_1.fga`, the only
    # in-tree schema that compiled this leaf, has `unmatchable_conds` /
    # `matched_roles` / `matched_users` all ∅ by construction and could not have
    # served as a differential. `parent: [folder] but not detached` gives the
    # tupleset a storage leaf (`parent.0`), so the leaf is DRIVEN, not just
    # compiled.
    #
    # SCOPE: spec-side + the python-only three-backend differential; NEVER
    # `GRAPH_FRAGMENT`, and here the Lean exclusion is doubled:
    #   * `W4Fragment.computedOrDirect` (`computedOnly` before leg 5) — a derived
    #     def's expr must be `ComputedOrDirect`, which is `False` on a `ttu` node
    #     outright, and `inherited` IS a `ttu`. Leg 5 widened this field to admit
    #     `Direct` arms; it did NOT admit `ttu` ones, which is a separate later leg;
    #   * `GraphAdmission.ttuDirect` (`TtuTuplesetsDirect`) — a declared TTU
    #     tupleset def must be directs-only, and `parent` is an `excl`. So this
    #     shape fails the ADMISSION bundle too, not merely the fragment carries;
    #     `w4_within_scope`'s third clause is precisely "a TTU tupleset relation
    #     is never derived".
    # Measured 2026-07-28: oracle == set engine == real graph index == Lean `sem`
    # over the full 200-query grid (8 True), zcli 0.08 s.
    #
    # Load-bearing store (pinned by `test_derived_tupleset_ttu_corpus_features`):
    #   parent(f1, d1)      True   — plain stored parent
    #   parent(f2, d1)      False  — the DERIVED tupleset's exclusion bites HERE
    #   inherited(alice,d1) True   — alice views f1, f1 is a parent
    #   inherited(bob, d1)  True   — ★ bob views f2, and f2 is STILL a stored
    #                                `parent` tuple even though `parent(f2,d1)` is
    #                                False. This asymmetry IS the semantics the
    #                                leaf kind exists to implement, and it is what
    #                                distinguishes `derived-tupleset-ttu` from
    #                                `derived-ttu`; a corpus where the two agreed
    #                                would compile the leaf without testing it.
    #   inherited(carol,d1) False  — anti-vacuity: not everyone inherits
    "derived_tupleset_ttu": (
        """
        type user
        type folder
          define viewer: [user]
        type doc
          define detached: [folder]
          define parent: [folder] but not detached
          define inherited: viewer from parent
        """,
        [mk_tuple("...", "user", "alice", "viewer", "folder", "f1"),
         mk_tuple("...", "folder", "f1", "parent", "doc", "d1"),
         mk_tuple("...", "user", "bob", "viewer", "folder", "f2"),
         mk_tuple("...", "folder", "f2", "parent", "doc", "d1"),
         mk_tuple("...", "folder", "f2", "detached", "doc", "d1")],
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
# Separate from SCHEMAS (and GRAPH_FRAGMENT). `self_ttu_parent` is a TTU over a
# derived relation, which `W4Fragment.computedOrDirect` still maps to `False` — out,
# unchanged.
#
# ⚠ `self_flag`'s stated reason has EXPIRED and is deliberately not being replaced by
# a guess. It read "Direct arms under a boolean — genuine storage leaves, not
# `computedOnly`", and that is exactly the shape E-chain leg 5 brought INTO scope
# (`direct_arm_exclusion` is now theorem-backed on it). Whether `self_flag` is in
# `W4Fragment` now is an OPEN question this leg did not answer: it would need the
# ten fields checked at its own schema and store — in particular `term`'s
# `NoStoreSubjectR` and `bareStar` against its self-referential tuples — and, per the
# ZT-P3-3 lesson two blocks below, a corpus goes into GRAPH_FRAGMENT on a written
# per-field argument, never on a plausible-sounding one. Until someone does that
# work it stays spec-side-only, which is the conservative direction. Only
# test_conformance_spec's full-scope comparisons consume these (T1 places no fragment
# restriction on the set engine).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Direct-arm boolean corpora — the names of the SCHEMAS entries whose derived
# defs carry a **Direct arm under an exclusion** (`approver := (direct[user])
# but not banned`, AST `excl (direct[user]) (computed banned)`). The entries
# LIVE in SCHEMAS/GRAPH_FRAGMENT since 2026-07-20e (Lean coverage was the C-chain
# `graph_correct_w3d2_d` + `W4WitnessDirect`; since 2026-08-05 it is the HEADLINE
# `graph_correct` via `W4WitnessDirect.final_applies4` — see the
# `direct_arm_exclusion` entry's comment); this name list survives so
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
