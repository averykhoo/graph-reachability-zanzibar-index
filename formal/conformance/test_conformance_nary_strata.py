"""Language-feature coverage: n-ARY operators, >= 3 STRATA (ZT-P4-4), PLAN-LEAF
kinds, and the two 2026-07-28 zero-coverage shapes (wildcard usersets `[T:*#p]`
and the `derived-tupleset-ttu` leaf; see section (d) for their scope arguments).
Since `TK106` (2026-09-26) the second shape is REFUSED by both parsers, so for it this
module pins the refusal and the leaf-kind exclusion, not answers (sections (c), (d)).

Two holes were measured across the whole conformance harness on 2026-07-26:

  * **every union and intersection was BINARY.** `encode.py::_fold_binary` — the
    documented modeling bridge from the n-ary `Union`/`Intersection` that BOTH
    parsers build to Lean's strictly binary `Expr.union`/`Expr.inter` — therefore
    never ran at the arity it exists for. Its loop body executed exactly once per
    node, so the left-association it commits to was never on trial, even though
    both parsers accept `a or b or c`.
  * **max 2 strata anywhere.** Python's `DeltaProcessor` cascade over >= 3 strata
    was reached by nothing in this harness (only `tests/test_bulk_build.py`'s
    `demorgan1` reaches it repo-wide).

`corpus.py` closes both with `nary_union` / `nary_intersection` and
`three_strata_chain`. This module
is the anti-vacuity proof that those corpora REALLY exercise the features — the
`tests/test_bulk_build.py::_assert_r4bf_features` idiom: a corpus added for a
feature must be pinned to actually reach it, or it silently degrades into not
testing the thing.

--------------------------------------------------------------------------- #
SCOPE — where each corpus is gated, and WHY. (ZT-P3-3 is the cautionary tale.)
--------------------------------------------------------------------------- #
**`nary_union` + `nary_intersection` -> `SCHEMAS` + `GRAPH_FRAGMENT` (full Lean
gating).** Arity
widens a def's FAN-IN; `W4Fragment.twoStrata` bounds dependency DEPTH. The two
are independent, and the corpus is in-fragment on every other field as well
(per-field argument in the n-ary block in `corpus.py`; measured 0 and 1 strata).
So the Lean graph/state/remove gates carry both apples-to-apples.

They are TWO small corpora rather than one for a measured runtime wall in the
LEAN MODEL, not for scope: the model's round-2 job enumeration hits a cliff in the
number of DISTINCT SUBJECTS (measured 2026-07-26 at the 120 s per-spawn timeout:
2 subj 0.1 s, 3 subj 0.3 s, 4 subj 5.5 s, 5 subj 115 s on a 5-relation
1-stratum schema; a derived-reads-derived 3-arm union timed out at FOUR TUPLES).
Splitting keeps each corpus at 0.1-0.6 s AND buys more arm-witness coverage than
one 8-tuple corpus could. Numbers are in `corpus.py`.

**RE-MEASURED 2026-07-27 — the arity ceiling had stopped at 3, and the derived
residue was still open.** Over all 69 schemas the harness read that day (28
curated + 40 generated + `three_strata_chain`; as of 2026-07-29 the curated set
is **33** and the total **73**) the operator-arity histogram was
`{2: 120 nodes, 3: 2 nodes}`: the only >= 3-arity nodes in existence were
`nary_union`'s and `nary_intersection`'s, and BOTH are untainted. So
`_fold_binary`'s loop had still never run more than twice, and the residue this
docstring used to record — "a DERIVED n-ary union is not gated Lean-side
anywhere" — was live. `nary_union_derived4` closes both: a FOUR-arm union whose
last arm is boolean, so the union itself is derived, at two strata and therefore
IN `GRAPH_FRAGMENT` (measured: zcli spec 0.1 s, graph-state 0.5 s, Python graph
index 0.5 s — it stays under the subject cliff because only one relation is
boolean-side). `test_harness_wide_arity_ceiling` floors the ceiling at 4 and
pins that the high-arity node is really derived.

**`three_strata_chain` -> `MULTI_STRATUM_SCHEMAS`, spec-side ONLY, and the
python-to-python differential below. NEVER `GRAPH_FRAGMENT`.**
`W4Fragment.twoStrata` is literally "at most TWO derived strata", recorded as
attack-confirmed load-bearing ("a 3-stratum schema fires the round-2 reject"),
and the Lean operational model's cascade is `runCascade2` — a FIXED two rounds,
so a third stratum has no round to settle in. The spec `sem` is a pure function
of the final store with no cascade and no round bound, so `sem` comparisons ARE
scope-clean at any stratum count (that is `test_conformance_spec.py`'s leg).
Putting the corpus in `GRAPH_FRAGMENT` would compare the Lean OPERATIONAL model
outside the theorem that covers it — the exact mistake ZT-P3-3 caught with
`direct_arm_exclusion` — and it would NOT fail loudly, because zcli gates only on
runtime write admission (rc 2) and drained-ness (rc 3), never on `W4Fragment`.

So Python's >= 3-stratum cascade is exercised here against the ORACLE and the SET
ENGINE only. That is a real gate on the real `DeltaProcessor` (it is the same
three-backend differential `test_conformance_direct_arm.py` runs), and it makes
NO claim about any Lean model. No zcli process is spawned by this module.

**Re-verified in the Lean sources 2026-07-27 (ZT-P4-4 follow-up), because the
disposition above is load-bearing and was second-hand.** Both halves hold:
`GraphIndex/CascadeStrata.lean::runCascade2` is literally two nested
`reconcileJobsLR` applications plus one quiescence check — the round count is
structural, not a parameter, so no third stratum has a round to settle in; and
`FullScope.lean::W4Fragment`'s `twoStrata` field is a hypothesis of the final
`FullScope.lean::graph_correct` (threaded through
`CascadeStrata.lean::runCascade2_no_abort` as `hLU2`), whose own comment records
the attack that confirmed it load-bearing (`a := b or y, b := c or x, c := x but
not y` makes `hLU2` FALSE and the round-2 reject FIRE). Widening is therefore not
a matter of relaxing a hypothesis: it needs a `runCascadeN`/fuel-indexed
scheduler and a re-proof of the whole W3d-2 chain that is stated over exactly two
rounds. **Consequently: what is ungated at >= 3 strata is the LEAN OPERATIONAL
MODEL, not the Python cascade.** The Python cascade IS driven and checked at 3
strata, here, against the oracle and the set engine, under both `SetOps` — and
also at spec level against Lean `sem` (`test_conformance_spec.py`, which is
round-bound-free), including on 12 of the 40 generated schemas that reach 3
strata (measured 2026-07-27). Full write-up:
`formal/history/nary-strata-coverage-2026-07-27.md`.
"""

from __future__ import annotations

import pytest

from setengine import SetEngine
from setengine.setops import ALL_SETOPS
from sqlmodel import Session, SQLModel, create_engine

from tests.oracle import Oracle, OIntersection, OUnion, parse_schema_ast

from zanzibar_utils_v1 import (
    Intersection, Union, parse_openfga_schema,
    parse_schema_ast as prod_parse_schema_ast)

from formal.conformance.backends import graphindex_answers
from formal.conformance.corpus import (
    GRAPH_FRAGMENT, MULTI_STRATUM_SCHEMAS, SCHEMAS)
from formal.conformance.encode import schema_to_json
from formal.conformance.grid import (
    assert_grid_nonvacuous, queries_for, fmt_mismatches as _fmt)

_NARY_UNION = "nary_union"
_NARY_INTER = "nary_intersection"
_NARY_D4 = "nary_union_derived4"
_TRI = "three_strata_chain"

# The documented feature bounds, ASSERTED so they cannot silently drift (the
# `test_conformance_enum._SHAPES` idiom). Per corpus:
#   name -> (expected {relation: arity}, expected stratum count)
_NARY_BOUNDS: dict[str, tuple[dict[str, int], int]] = {
    _NARY_UNION: ({"any_of": 3}, 0),      # untainted: no boolean plans at all
    _NARY_INTER: ({"all_of": 3}, 1),
    _NARY_D4: ({"any_of4": 4}, 2),        # DERIVED 4-arm union (2026-07-27)
}
_TRI_EXPECTED_STRATA = 3

# ZT-P4-4 follow-up (2026-07-27): the harness-wide arity ceiling, asserted so it
# cannot silently regress. Measured that day over all 69 schemas the harness
# then read (28 curated corpora + 40 generated + `three_strata_chain`; the
# harness reads **73** as of 2026-07-29 — 33 curated + 40 generated): before
# `nary_union_derived4` the histogram was {arity 2: 120 nodes, arity 3: 2 nodes},
# i.e. `encode._fold_binary`'s loop had never run more than twice anywhere.
_MIN_MAX_ARITY = 4


def _json_nest_depth(node, tags=("union", "inter")) -> int:
    """Depth of the left-nested binary spine `encode.py::_fold_binary` produced.
    A binary source node folds to depth 1; an n-ary node folds to depth n-1."""
    if not isinstance(node, dict):
        return 0
    for tag in tags:
        if tag in node:
            a, _b = node[tag]
            return 1 + _json_nest_depth(a, tags)
    return 0


def _defs_json(schema_text):
    return {tuple(k): v for k, v in schema_to_json(schema_text)["defs"]}


# --------------------------------------------------------------------------- #
# (a) n-ARY union / intersection
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("name", sorted(_NARY_BOUNDS))
def test_nary_corpus_encoding(name):
    """The n-ary corpora really reach >= 3 arity, in BOTH parsers, and really
    drive `encode._fold_binary` into a NESTED binary spine."""
    schema_text, _tuples, _ow = SCHEMAS[name]
    expected_arities, expected_strata = _NARY_BOUNDS[name]

    # 1. The ORACLE's parser (the one `encode.py` feeds to Lean) sees n-ary nodes.
    oast = parse_schema_ast(schema_text)
    arities = {rel: len(node.children)
               for (_ty, rel), node in oast.items()
               if isinstance(node, (OUnion, OIntersection))}
    assert arities == expected_arities, (
        f"[{name}] oracle-parsed operator arities are {arities}, expected "
        f"{expected_arities} — the n-ary coverage this corpus exists for has "
        f"drifted")
    assert max(arities.values()) >= 3, (
        f"[{name}] no >= 3-arm operator in the oracle AST: {arities}")

    # 2. The PRODUCTION parser (zanzibar_utils_v1) agrees on the arities — the
    #    two independent parsers must both really be reading `a or b or c`.
    prod = parse_openfga_schema(schema_text)
    prod_ast = prod_parse_schema_ast(schema_text)
    prod_arities = {rel: len(node.children)
                    for (_ty, rel), node in prod_ast.items()
                    if isinstance(node, (Union, Intersection))}
    assert prod_arities == expected_arities, (
        f"[{name}] production-parsed arities {prod_arities} != oracle-parsed "
        f"{expected_arities} — the two parsers disagree on n-ary shape")

    # 3. `_fold_binary` actually FOLDED: a 3-arm node becomes a depth-2 left
    #    spine. Before these corpora every fold produced depth 1 (an identity in
    #    practice), so the left-association was never observable.
    defs = _defs_json(schema_text)
    depths = {rel: _json_nest_depth(defs[("doc", rel)]) for rel in expected_arities}
    assert depths == {rel: n - 1 for rel, n in expected_arities.items()}, (
        f"[{name}] encoded binary-spine depths {depths} do not match the arities "
        f"{expected_arities} — `encode._fold_binary` did not fold")
    assert max(depths.values()) >= 2, (
        f"[{name}] the encoded spine is at most depth 1 — `_fold_binary`'s loop "
        f"body ran once, i.e. the n-ary bridge is still untested at its arity")

    # 4. It compiles to <= 2 strata, which is WHY it may sit in GRAPH_FRAGMENT.
    n_strata = 0 if prod.compiled is None else len(prod.compiled.strata)
    assert n_strata == expected_strata, (
        f"[{name}] compiles to {n_strata} strata, expected {expected_strata}; "
        f"> 2 would put it OUTSIDE W4Fragment.twoStrata and it must then leave "
        f"GRAPH_FRAGMENT")
    assert n_strata <= 2, f"[{name}] {n_strata} strata is outside twoStrata"
    assert name in GRAPH_FRAGMENT, (
        f"[{name}] is in-fragment and should be gated graph-side")


def test_harness_wide_arity_ceiling():
    """SOMEWHERE in the corpora an operator reaches arity >= 4, so
    `encode._fold_binary` runs its loop body three times and the left spine it
    builds is observed at depth 3.

    ZT-P4-4 closed the "every operator is BINARY" hole with two 3-arm corpora;
    re-measuring 2026-07-27 showed the ceiling had stopped at 3 (histogram over
    all 69 schemas the harness reads: 120 binary nodes, 2 ternary, 0 higher).
    `nary_union_derived4` raises it to 4 AND makes the high-arity node DERIVED —
    the residue this module's docstring names ("a DERIVED n-ary union is not
    gated Lean-side anywhere")."""
    def _arities(ast):
        out = []

        def walk(e):
            if isinstance(e, (Union, Intersection)):
                out.append(len(e.children))
                for c in e.children:
                    walk(c)
            else:
                for field in ("base", "subtract"):
                    if hasattr(e, field):
                        walk(getattr(e, field))
        for e in ast.values():
            walk(e)
        return out

    per_corpus = {name: _arities(prod_parse_schema_ast(SCHEMAS[name][0]))
                  for name in SCHEMAS}
    all_arities = [a for v in per_corpus.values() for a in v]
    assert all_arities, (
        "ANTI-VACUITY: no union/intersection node found in ANY corpus — the "
        "ceiling assertion below would be about an empty list")
    ceiling = max(all_arities)
    assert ceiling >= _MIN_MAX_ARITY, (
        f"harness-wide maximum operator arity is {ceiling}, floor "
        f"{_MIN_MAX_ARITY}: `encode._fold_binary`'s loop no longer runs past "
        f"two iterations anywhere. Per-corpus arities: "
        f"{ {k: v for k, v in per_corpus.items() if v} }")

    # and the >= 4-arity node must really be a DERIVED relation's root
    prod = parse_openfga_schema(SCHEMAS[_NARY_D4][0])
    assert prod.compiled is not None and any(
        ("doc", "any_of4") in stratum for stratum in prod.compiled.strata), (
        f"[{_NARY_D4}] `any_of4` is no longer a DERIVED relation — the 4-arm "
        f"fold is back to an untainted shape and the derived-n-ary residue "
        f"reopens: strata={None if prod.compiled is None else prod.compiled.strata}")


def test_nary_union_derived4_arms_load_bearing():
    """All FOUR arms of `any_of4` are load-bearing, and the fourth (the DERIVED
    `safe = x but not blocked`) really evaluates its exclusion inside the fold:
    `ux` holds `x` yet is `blocked`, so it must NOT be a member."""
    schema_text, tuples, _ow = SCHEMAS[_NARY_D4]
    orc = Oracle(schema_text, list(tuples))

    def chk(user, rel):
        return orc.check("...", "user", user, rel, "doc", "d1")

    for witness, own_arm, others in (("ua", "a", ("b", "c", "safe")),
                                     ("ub", "b", ("a", "c", "safe")),
                                     ("uc", "c", ("a", "b", "safe")),
                                     ("us", "safe", ("a", "b", "c"))):
        assert chk(witness, own_arm), (
            f"[{_NARY_D4}] witness `{witness}` lost its own arm `{own_arm}`")
        assert not any(chk(witness, o) for o in others), (
            f"[{_NARY_D4}] witness `{witness}` is no longer isolated to arm "
            f"`{own_arm}` — the arm is not independently load-bearing")
        assert chk(witness, "any_of4"), (
            f"[{_NARY_D4}] arm `{own_arm}` of the 4-arm union does not carry "
            f"its own witness into the union")

    assert chk("ux", "x") and chk("ux", "blocked"), \
        f"[{_NARY_D4}] the `ux` exclusion witness no longer holds x AND blocked"
    assert not chk("ux", "safe") and not chk("ux", "any_of4"), (
        f"[{_NARY_D4}] `ux` is a member of the 4-arm union despite being blocked "
        f"— the DERIVED arm's exclusion is not being evaluated inside the fold, "
        f"which is the whole point of a derived n-ary arm")


# --------------------------------------------------------------------------- #
# (c) PLAN-LEAF KIND coverage (2026-07-27, the Item-4(b) `PDerivedUserset` board
#     finding). Same idiom as the arity ceiling: a compiler branch that no corpus
#     reaches is a differential that never runs.
# --------------------------------------------------------------------------- #

# Measured 2026-07-27 by walking `RuleSet.compiled.plans[..].leaves` over all 69
# schemas the harness then read (28 curated + 40 generated + three_strata_chain;
# **73** as of 2026-07-29 — 33 curated + 40 generated, NOT re-walked here):
#   closure 211 · derived-computed 42 · derived-ttu 50 · derived-userset 0
#   · derived-tupleset-ttu 0
# `derived-userset` (`zanzibar_utils_v1.py::PDerivedUserset`) was compiled by NO
# corpus, in exactly the plan-leaf area where the X4 adjudication found five real
# divergences. `corpus.py::TTU_USERSET_SCHEMAS['derived_userset']` closes it.
#
# **2026-07-28 (board item C): `derived-tupleset-ttu` closed too, so the list is
# now EVERY kind `_plan_leaves` can emit.** It was recorded-not-asserted for a
# day because it needed its own scope argument AND because reachability had to be
# established first: the leaf is emitted whenever a TTU's tupleset relation is
# tainted, but TTU parents are the STORED tupleset tuples, so a derived tupleset
# with no Direct restriction yields a constantly-EMPTY TTU (that is why
# `demorgans_law_1.fga`, the one in-tree schema compiling this leaf, has all three
# of its dependent relations ∅ by construction and never served as a
# differential). `corpus.py::TTU_USERSET_SCHEMAS['derived_tupleset_ttu']` gives
# the tupleset a storage leaf, so the kind is DRIVEN, not merely compiled.
#
# The tuple is checked against the compiler below (`test_required_leaf_kinds_are_
# exactly_the_compilers_kinds`) so a NEW plan-leaf kind cannot be added to
# `zanzibar_utils_v1` and silently stay uncovered.
#
# ⚠ 2026-09-26 (`TK106`, user decision: refuse boolean tuplesets, as OpenFGA does):
# `derived-tupleset-ttu` became UNREACHABLE from every checked parse, and its carrier moved
# to `corpus.py::REFUSED_TUPLESET_SCHEMAS`. Until 2026-10-05 the kind stayed here with an
# asserted exclusion from the floor.
#
# ⚠ 2026-10-05 (`TK107`): the kind is GONE from the compiler. `_validate_ttu_tuplesets`
# refuses any non-direct tupleset, tainted ones included, before plan construction, and
# `PDerivedTuplesetTTU` plus the processor/bulk branches were deleted. So the tuple below
# is again exactly what `_plan_leaves` can emit, with no exception list. The carrier's
# refusal by the graph compiler is pinned in section (d).
_REQUIRED_LEAF_KINDS = ("closure", "derived-computed", "derived-ttu",
                        "derived-userset")

#: The fixed fragment both parsers' refusal messages contain
#: (`zanzibar_utils_v1.py::_validate_tuplesets_direct`,
#: `tests/oracle.py::_validate_tuplesets_direct`).
_TUPLESET_REFUSAL = "tupleset must be direct"


def _checked_refusals(schema_text: str, ow=()) -> dict[str, str]:
    """What each CHECKED schema entry point says about `schema_text`: the refusal message,
    or `"ACCEPTED"`. A ValueError without the TK106 fragment is re-raised, so an unrelated
    refusal cannot pass for this one."""
    out: dict[str, str] = {}
    for name, parse in (
            ("zanzibar_utils_v1.parse_schema_ast", prod_parse_schema_ast),
            ("tests.oracle.parse_schema_ast", parse_schema_ast),
            ("zanzibar_utils_v1.parse_openfga_schema",
             lambda s: parse_openfga_schema(s, frozenset(ow)))):
        try:
            parse(schema_text)
        except ValueError as e:
            if _TUPLESET_REFUSAL not in str(e):
                raise
            out[name] = str(e)
        else:
            out[name] = "ACCEPTED"
    return out


def test_every_plan_leaf_kind_is_reached_by_some_corpus():
    """Every compiled plan-leaf KIND in `_REQUIRED_LEAF_KINDS` is produced by at
    least one corpus the harness actually runs. A `compile_ruleset` branch that
    no corpus reaches is a branch no differential ever exercises.

    `TK106` (2026-09-26) to `TK107` (2026-10-05) this carried an asserted exception for
    `derived-tupleset-ttu`, unreachable from a checked parse. `TK107` deleted the kind from
    the compiler, so the exception went with it; the refusal it guarded is pinned by
    `test_derived_tupleset_ttu_carrier_is_refused_by_every_parser_and_the_graph_compiler`.
    """
    from formal.conformance.corpus import (
        MULTI_STRATUM_SCHEMAS, SELF_REFERENTIAL_SCHEMAS, TTU_USERSET_SCHEMAS)

    where: dict[str, set[str]] = {}
    n_leaves = 0
    for dname, d in (("SCHEMAS", SCHEMAS),
                     ("MULTI_STRATUM_SCHEMAS", MULTI_STRATUM_SCHEMAS),
                     ("TTU_USERSET_SCHEMAS", TTU_USERSET_SCHEMAS),
                     ("SELF_REFERENTIAL_SCHEMAS", SELF_REFERENTIAL_SCHEMAS)):
        for name, (schema_text, _tuples, ow) in d.items():
            compiled = parse_openfga_schema(schema_text, frozenset(ow)).compiled
            if compiled is None:
                continue
            for plan in compiled.plans.values():
                for leaf in plan.leaves:
                    n_leaves += 1
                    where.setdefault(leaf.kind, set()).add(f"{dname}:{name}")

    assert n_leaves > 0, (
        "ANTI-VACUITY: no compiled plan leaves found in ANY corpus — the "
        "coverage assertion below would be about an empty histogram")
    missing = [k for k in _REQUIRED_LEAF_KINDS if not where.get(k)]
    assert not missing, (
        f"plan-leaf kind(s) {missing} are produced by NO corpus — the "
        f"corresponding `compile_ruleset` branch is unexercised by every "
        f"conformance differential. Observed histogram: "
        f"{ {k: len(v) for k, v in sorted(where.items())} }")


def test_required_leaf_kinds_are_exactly_the_compilers_kinds():
    """`_REQUIRED_LEAF_KINDS` names EVERY kind `zanzibar_utils_v1._plan_leaves`
    can emit — so adding a new plan-leaf kind to the compiler cannot leave the
    coverage floor quietly one kind short.

    A hand-maintained "required" list is itself a check that can fail by passing:
    the list was correct on the day it was written and would stay green forever
    while the compiler grew a branch nobody covered. The kinds are read out of the
    compiler's own source (the `LeafSpec(..., '<kind>', ...)` literals in
    `_plan_leaves`, which is the single function that mints them), so the two
    cannot drift."""
    import inspect
    import re

    import zanzibar_utils_v1

    src = inspect.getsource(zanzibar_utils_v1._plan_leaves)
    emitted = set(re.findall(r"LeafSpec\([^,]+,\s*'([a-z][a-z-]*)'", src))
    assert emitted, (
        "ANTI-VACUITY: no `LeafSpec(..., '<kind>')` literal found in "
        "`zanzibar_utils_v1._plan_leaves` — the regex has rotted and this "
        "comparison would be against an empty set")
    assert emitted == set(_REQUIRED_LEAF_KINDS), (
        f"the plan-leaf coverage floor and the compiler disagree about which "
        f"leaf kinds exist.\n"
        f"  emitted by `_plan_leaves` but NOT in the floor: "
        f"{sorted(emitted - set(_REQUIRED_LEAF_KINDS))}\n"
        f"  in the floor but NOT emitted by `_plan_leaves`: "
        f"{sorted(set(_REQUIRED_LEAF_KINDS) - emitted)}\n"
        f"A new kind must get a corpus (and its own scope argument), not a "
        f"silent omission; a removed kind must leave the floor.")


# --------------------------------------------------------------------------- #
# (d) WILDCARD USERSETS `[T:*#p]` and the `derived-tupleset-ttu` leaf
#     (2026-07-28, board item C — the last two ZERO-coverage holes).
#
# SCOPE — where these two corpora are gated, and WHY (the ZT-P3-3 discipline;
# the full per-field argument is in situ on each `corpus.py` entry):
#
# **Both -> `TTU_USERSET_SCHEMAS`, i.e. spec-side (`test_conformance_spec.py`:
# Lean `sem` x oracle x set engine) PLUS the python-only three-backend leg below.
# NEITHER may enter `SCHEMAS` or `GRAPH_FRAGMENT`.**
#   * `wildcard_userset` is outside `FullScope.lean::W4Fragment.wsBare`
#     (`∀ sh ∈ declaredWildcardShapes S, sh.2 = BARE` since 2026-09-14h -- it read
#     `wildcardShapes` before that name was corrected to cover both passes of
#     `derive_schema_info`; this schema's shape set contains
#     the non-bare `(group, member)`). `wsBare`'s own doc comment already records
#     the asymmetry — Python admits wildcard usersets over UNTAINTED relations and
#     rejects them only over derived ones — so this is a declared Lean gap.
#   * `derived_tupleset_ttu` is outside `W4Fragment.computedOnly` (a `ttu` node is
#     never `ComputedOnly`) AND outside the ADMISSION bundle
#     `GraphAdmission.ttuDirect` (`TtuTuplesetsDirect`: a declared tupleset def
#     must be directs-only; `parent` is an `excl`). `w4_within_scope`'s third
#     clause is literally "a TTU tupleset relation is never derived".
# zcli gates on runtime write admission (rc 2) and drained-ness (rc 3), NEVER on
# `GraphAdmission`/`W4Fragment`, so either corpus placed in `GRAPH_FRAGMENT`
# would run GREEN while comparing two models no theorem relates.
#
# The python-only leg IS in scope and is the point: `sem` is a pure function of
# the store (no fragment hypotheses), the set engine is covered unconditionally by
# T1, and the real graph index ADMITS both shapes and answers them correctly
# (measured 2026-07-28). Driving it against the oracle is a genuine gate on real
# `WildcardIndex` + `DeltaProcessor` behaviour that makes NO Lean claim — the same
# footing as `test_multi_stratum_three_way` above.
#
# REACHABILITY (established empirically FIRST, because the finding as filed reads
# wider than the reachable surface):
#   * wildcard usersets over a DERIVED relation are a deliberate scope rejection
#     (`UnsupportedByGraphIndex`, `_build_plan_tree`'s `Direct` arm) — verified;
#     the reachable surface is the UNTAINTED one, and it is fully live.
#   * `derived-tupleset-ttu` IS reachable, but only non-vacuously when the derived
#     tupleset carries a Direct restriction (TTU parents are STORED tuples), which
#     is why the one pre-existing schema compiling this leaf could not test it.
#
# ⚠ 2026-09-26 (`TK106`): the `derived_tupleset_ttu` half of this section is SUPERSEDED.
# The user decided boolean tuplesets are refused, as OpenFGA refuses them, so the shape
# is rejected at parse time by both parsers (`zanzibar_utils_v1.py::
# _validate_tuplesets_direct`, `tests/oracle.py::_validate_tuplesets_direct`) and the
# corpus moved to `corpus.py::REFUSED_TUPLESET_SCHEMAS`. The "graph index ADMITS both
# shapes" sentence above is now true of `wildcard_userset` only. What this section pins
# for the refused shape is the refusal itself: all three backends refuse it
# (`test_refused_tupleset_three_way_refusal`), and since `TK107` (2026-10-05), which
# deleted the leaf kind, the graph compiler refuses it even on the unchecked parse
# (`test_derived_tupleset_ttu_carrier_is_refused_by_every_parser_and_the_graph_compiler`).
# --------------------------------------------------------------------------- #

_WILDCARD_USERSET = "wildcard_userset"
_DERIVED_TS_TTU = "derived_tupleset_ttu"

# Harness-wide floor, same idiom as `_MIN_MAX_ARITY`: at least this many DISTINCT
# non-bare wildcard shapes `(T, p)` must exist across the corpora. Measured
# 2026-07-26/27 at ZERO across every curated corpus and every generated schema —
# the whole `[T:*#p]` half of `derive_schema_info`'s `subject_wildcard_shapes` /
# `bridged_in_shapes` machinery was uncompared. `wildcard_userset` makes it 1.
_MIN_WILDCARD_USERSET_SHAPES = 1


def _all_corpora():
    """Every (label, schema, tuples, object_wildcards) the harness gates on."""
    from formal.conformance.corpus import (
        MULTI_STRATUM_SCHEMAS, SELF_REFERENTIAL_SCHEMAS, TTU_USERSET_SCHEMAS)
    out = []
    for dname, d in (("SCHEMAS", SCHEMAS),
                     ("MULTI_STRATUM_SCHEMAS", MULTI_STRATUM_SCHEMAS),
                     ("TTU_USERSET_SCHEMAS", TTU_USERSET_SCHEMAS),
                     ("SELF_REFERENTIAL_SCHEMAS", SELF_REFERENTIAL_SCHEMAS)):
        for name, (schema_text, tuples, ow) in d.items():
            out.append((f"{dname}:{name}", schema_text, tuples, ow))
    return out


def test_harness_wide_wildcard_userset_floor():
    """SOMEWHERE in the corpora a NON-BARE wildcard shape `(T, p)` is declared, so
    the `[T:*#p]` compile/eval path is differentially compared at all.

    `SchemaInfo.subject_wildcard_shapes` mixes bare `[T:*]` shapes (predicate
    `'...'`, covered by many corpora) with userset shapes; only the latter reach
    `bridged_in_shapes` and the set engine's star-userset arm. The floor counts
    the userset ones specifically, because the bare ones would otherwise keep this
    assertion green while the feature stayed at zero — which is exactly the state
    the harness was in until 2026-07-28."""
    from zanzibar_utils_v1 import wildcard_userset_restriction_shapes

    shapes: dict[str, set] = {}
    for label, schema_text, _tuples, _ow in _all_corpora():
        ast = prod_parse_schema_ast(schema_text)
        for sh in wildcard_userset_restriction_shapes(ast):
            shapes.setdefault(label, set()).add(sh)
    distinct = {sh for v in shapes.values() for sh in v}
    assert len(distinct) >= _MIN_WILDCARD_USERSET_SHAPES, (
        f"harness-wide DISTINCT wildcard-userset shapes = {len(distinct)}, floor "
        f"{_MIN_WILDCARD_USERSET_SHAPES}: no corpus declares a `[T:*#p]` "
        f"restriction, so the wildcard-userset compile/eval path is compared by "
        f"NOTHING (the pre-2026-07-28 state). Per-corpus: { {k: sorted(v) for k, v in shapes.items()} }")


def test_wildcard_userset_corpus_features():
    """`wildcard_userset` really declares a NON-BARE wildcard shape, really
    stores a `group:*#member` subject, and every witness in its store is
    load-bearing — including the ghost-group userset (probe-2 parity) and the
    exclusion applied to star-derived membership."""
    from formal.conformance.corpus import TTU_USERSET_SCHEMAS
    from zanzibar_utils_v1 import (
        derive_schema_info, wildcard_userset_restriction_shapes)

    schema_text, tuples, _ow = TTU_USERSET_SCHEMAS[_WILDCARD_USERSET]

    ast = prod_parse_schema_ast(schema_text)
    assert wildcard_userset_restriction_shapes(ast) == frozenset({("group", "member")}), (
        f"[{_WILDCARD_USERSET}] no longer carries the literal `group:*#member` "
        f"restriction: {sorted(wildcard_userset_restriction_shapes(ast))}")
    info = derive_schema_info(ast)
    assert ("group", "member") in info.bridged_in_shapes, (
        f"[{_WILDCARD_USERSET}] the wildcard-userset shape no longer reaches "
        f"`bridged_in_shapes` — the concrete->w_any bridge machinery this corpus "
        f"exists to exercise is not engaged: {sorted(info.bridged_in_shapes)}")
    assert any(t.subject_name == "*" and t.subject_predicate == "member"
               for t in tuples), (
        f"[{_WILDCARD_USERSET}] the store no longer holds a `group:*#member` "
        f"subject — the shape would be declared but never written")

    # SCOPE: outside W4Fragment.wsBare, so it must stay out of the Lean graph gates.
    assert _WILDCARD_USERSET not in SCHEMAS, (
        f"[{_WILDCARD_USERSET}] leaked into SCHEMAS — a non-bare wildcard shape "
        f"makes `FullScope.lean::W4Fragment.wsBare` FALSE, and zcli would NOT "
        f"refuse it (it gates on admission rc 2 / drainedness rc 3, never on the "
        f"fragment)")
    assert _WILDCARD_USERSET not in GRAPH_FRAGMENT, \
        f"[{_WILDCARD_USERSET}] leaked into GRAPH_FRAGMENT"

    orc = Oracle(schema_text, list(tuples))

    def chk(sp, st, sn, rel):
        return orc.check(sp, st, sn, rel, "doc", "d1")

    # alice: viewer ONLY via the star userset (no concrete `viewer` grant).
    assert chk("...", "user", "alice", "viewer") and \
        chk("...", "user", "alice", "can_view"), \
        f"[{_WILDCARD_USERSET}] the star userset grants nothing — vacuous corpus"
    # dave: in no group => strict forall=>exists means the star does NOT cover him.
    assert not chk("...", "user", "dave", "viewer"), (
        f"[{_WILDCARD_USERSET}] a user who is a member of NO group is a viewer — "
        f"the `[group:*#member]` star has collapsed into 'everyone', so it would "
        f"pass every differential without testing membership at all")
    # bob: covered by the star AND banned => the exclusion bites star-derived
    # membership, not just stored grants.
    assert chk("...", "user", "bob", "viewer") and \
        not chk("...", "user", "bob", "can_view"), (
        f"[{_WILDCARD_USERSET}] the `banned` exclusion no longer applies to a "
        f"subject whose `viewer` membership comes from the wildcard userset")
    # carol: the non-star arm of the same Direct still works.
    assert chk("...", "user", "carol", "viewer") and \
        chk("...", "user", "carol", "can_view"), \
        f"[{_WILDCARD_USERSET}] the concrete `[user]` arm stopped granting"
    # ghost group's userset: covered by the star (probe-2 ghost-subject parity).
    assert chk("member", "group", "ghost_group", "viewer"), (
        f"[{_WILDCARD_USERSET}] a never-stored group's `#member` userset is not "
        f"covered by the `group:*#member` grant — the ghost-subject probe this "
        f"shape is defined by is not being exercised")


def test_derived_tupleset_ttu_carrier_is_refused_by_every_parser_and_the_graph_compiler():
    """`TK106` (2026-09-26) made a boolean tupleset a parse refusal; `TK107` (2026-10-05)
    deleted the compiler path it used to take (`PDerivedTuplesetTTU`, leaf kind
    `derived-tupleset-ttu`, and the processor/bulk branches that read it).

    Until `TK107` this test was `..._is_refused_and_still_mints_the_leaf` and pinned that
    the UNCHECKED compile still built the dead leaf. What it pins now: the carrier
    (`corpus.py::REFUSED_TUPLESET_SCHEMAS['derived_tupleset_ttu']`) is refused by every
    checked entry point with the TK106 message, it is kept out of every conformance
    family, and the GRAPH COMPILER refuses it too when handed the unchecked AST
    (`zanzibar_utils_v1.py::_validate_ttu_tuplesets`, `UnsupportedByGraphIndex`). That last
    refusal is what makes the deleted code unreachable from any input rather than only
    from a checked parse: without it, an unchecked AST would compile a tainted tupleset as
    an ordinary `PDerivedTTU` over a tupleset whose stored tuples sit on leaf families
    that `tupleset_parents` does not read.

    Measured 2026-09-26 (`.scratch/tk106/conf_probe1.py`), the checked half::

        prod parse_schema_ast: ValueError: doc#inherited: 'viewer' from 'parent': a tupleset must be direct (...)
        oracle parse_schema_ast: ValueError: doc#inherited: tupleset must be direct, but doc#parent is not
        parse_openfga_schema: ValueError: doc#inherited: 'viewer' from 'parent': a tupleset must be direct (...)
    """
    from formal.conformance.corpus import (
        REFUSED_TUPLESET_SCHEMAS, SELF_REFERENTIAL_SCHEMAS, TTU_USERSET_SCHEMAS)
    from zanzibar_utils_v1 import (
        UnsupportedByGraphIndex, _parse_schema_ast_unchecked, compile_ruleset,
        compute_taint, derive_schema_info)

    schema_text, _tuples, ow = REFUSED_TUPLESET_SCHEMAS[_DERIVED_TS_TTU]

    verdicts = _checked_refusals(schema_text, ow)
    assert len(verdicts) == 3, verdicts
    accepted = sorted(n for n, v in verdicts.items() if v == "ACCEPTED")
    assert not accepted, (
        f"[{_DERIVED_TS_TTU}] a boolean tupleset is ACCEPTED by {accepted}. TK106 "
        f"(2026-09-26) made it a parse-time refusal on both parsers; if that was relaxed "
        f"on purpose, the corpus goes back to TTU_USERSET_SCHEMAS with answers "
        f"re-adjudicated, not with the pre-TK106 ones restored")

    # SCOPE: a refused schema must sit in no family any differential reads.
    for fam_name, fam in (("SCHEMAS", SCHEMAS), ("GRAPH_FRAGMENT", GRAPH_FRAGMENT),
                          ("MULTI_STRATUM_SCHEMAS", MULTI_STRATUM_SCHEMAS),
                          ("TTU_USERSET_SCHEMAS", TTU_USERSET_SCHEMAS),
                          ("SELF_REFERENTIAL_SCHEMAS", SELF_REFERENTIAL_SCHEMAS)):
        assert _DERIVED_TS_TTU not in fam, (
            f"[{_DERIVED_TS_TTU}] is refused by both parsers but sits in {fam_name}")

    # The carrier is still a TAINTED tupleset (else the refusal below proves nothing
    # about the tainted case, which is the one TK107 deleted the code for).
    ast = _parse_schema_ast_unchecked(schema_text)
    assert ("doc", "parent") in compute_taint(ast), (
        f"[{_DERIVED_TS_TTU}] the tupleset `doc#parent` is not tainted, so this carrier "
        f"no longer exercises the tainted-tupleset refusal")

    # The graph compiler refuses it on the unchecked AST, BEFORE plan construction.
    with pytest.raises(UnsupportedByGraphIndex, match="has computed/rewritten arms"):
        compile_ruleset(ast, derive_schema_info(ast, frozenset(ow)))


@pytest.mark.parametrize("ops", ALL_SETOPS, ids=lambda o: o.name)
def test_refused_tupleset_three_way_refusal(ops):
    """`TK106` (2026-09-26): the three backends that used to be compared on
    `derived_tupleset_ttu` now AGREE BY REFUSING it. The independent oracle (`Oracle()`),
    the real `SetEngine` under this SetOps, and the graph-index compile
    (`parse_openfga_schema`, which `backends.graphindex_answers` starts from) each raise
    `ValueError` containing the TK106 fragment. A backend that started accepting it again
    would be a divergence between backends, which this makes a red test rather than a
    shrunk parametrization. Replaces the `derived_tupleset_ttu` rows of
    `test_zero_coverage_shapes_three_way`, one per SetOps, like them."""
    from formal.conformance.corpus import REFUSED_TUPLESET_SCHEMAS

    schema_text, tuples, obj_wild = REFUSED_TUPLESET_SCHEMAS[_DERIVED_TS_TTU]
    ow = frozenset(obj_wild)

    def refused(make) -> str:
        try:
            make()
        except ValueError as e:
            assert _TUPLESET_REFUSAL in str(e), f"refused for another reason: {e}"
            return "REFUSED"
        return "ACCEPTED"

    def set_engine():
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)
        session = Session(engine)
        try:
            SetEngine(session, "s1", schema_text, ops=ops, object_wildcard_shapes=ow)
        finally:
            session.close()

    got = {
        "oracle": refused(lambda: Oracle(schema_text, list(tuples))),
        "setengine": refused(set_engine),
        "graph": refused(lambda: parse_openfga_schema(schema_text, ow)),
    }
    assert got == {"oracle": "REFUSED", "setengine": "REFUSED", "graph": "REFUSED"}, (
        f"[{_DERIVED_TS_TTU}/{ops.name}] backends disagree on a refused shape: {got}")


@pytest.mark.parametrize("ops", ALL_SETOPS, ids=lambda o: o.name)
@pytest.mark.parametrize("name", [_WILDCARD_USERSET])
def test_zero_coverage_shapes_three_way(name, ops):
    """PYTHON-ONLY three-backend differential on the two 2026-07-28 corpora:
    independent oracle == real `SetEngine` == real graph index (`WildcardIndex` +
    `DeltaProcessor` cascade), over the full shared grid, under BOTH SetOps.

    No Lean artifact is involved and none may be: both shapes are outside
    `W4Fragment` (see the block comment above), so their Lean side is `sem` only
    and lives in `test_conformance_spec.py`. This leg exists because the graph
    index genuinely ADMITS both shapes — a scope rejection would make it
    impossible, and a rejection is exactly what the wildcard-userset finding
    looked like until it was measured.

    Since `TK106` (2026-09-26) only `wildcard_userset` runs here. `derived_tupleset_ttu`
    is refused by every backend, and `test_refused_tupleset_three_way_refusal` pins
    that the three agree on the refusal."""
    from formal.conformance.corpus import TTU_USERSET_SCHEMAS

    schema_text, tuples, obj_wild = TTU_USERSET_SCHEMAS[name]
    queries = queries_for(schema_text, tuples)
    assert_grid_nonvacuous(f"{name}/{ops.name}", queries)

    orc = Oracle(schema_text, list(tuples))
    oracle = [orc.check(*q) for q in queries]
    assert any(oracle), (
        f"[{name}/{ops.name}] ANTI-VACUITY: the oracle answers False on EVERY "
        f"query — three backends agreeing on 'no' everywhere compares nothing "
        f"about the feature under test")

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    try:
        eng = SetEngine(session, "s1", schema_text, ops=ops,
                        object_wildcard_shapes=frozenset(obj_wild))
        for tup in tuples:
            eng.add_tuple(tup.subject_predicate, tup.subject_type,
                          tup.subject_name, tup.relation, tup.object_type,
                          tup.object_name)
        se = [bool(eng.check(*q)) for q in queries]
    finally:
        session.close()

    graph = graphindex_answers(schema_text, tuples, queries, obj_wild)

    assert len(oracle) == len(se) == len(graph) == len(queries), (
        f"[{name}/{ops.name}] answer-vector length mismatch")

    mism = [(queries[i], oracle[i], se[i]) for i in range(len(queries))
            if oracle[i] != se[i]]
    assert not mism, (
        f"[{name}/{ops.name}] oracle/set-engine disagreement:\n"
        f"{_fmt(mism, 'oracle', 'setengine')}")

    mism = [(queries[i], oracle[i], graph[i]) for i in range(len(queries))
            if oracle[i] != graph[i]]
    assert not mism, (
        f"[{name}/{ops.name}] oracle/graph-index disagreement on a shape that "
        f"had ZERO coverage until 2026-07-28 — this is a GENUINE FINDING:\n"
        f"{_fmt(mism, 'oracle', 'graph')}")


def test_nary_union_arms_load_bearing():
    """Every arm of the 3-arm UNION changes an answer. An n-ary node whose extra
    arms never matter would pass every differential while testing a binary op."""
    schema_text, tuples, _ow = SCHEMAS[_NARY_UNION]
    orc = Oracle(schema_text, list(tuples))

    def chk(user, rel):
        return orc.check("...", "user", user, rel, "doc", "d1")

    for arm, witness, others in (("1", "ua", ("b", "c")),
                                 ("2", "ub", ("a", "c")),
                                 ("3", "uc", ("a", "b"))):
        assert chk(witness, "any_of") and not any(chk(witness, o) for o in others), (
            f"[{_NARY_UNION}] arm {arm} of the 3-arm union is not load-bearing: "
            f"`{witness}` must be a member of `any_of` via arm {arm} ALONE")
    assert chk("alice", "any_of"), (
        f"[{_NARY_UNION}] the union is empty on its all-arms member — it would "
        f"pass vacuously")


def test_nary_intersection_arms_load_bearing():
    """The 3-arm INTERSECTION is non-empty, and arms 1 and 3 each independently
    exclude a subject. Arm 3 is the arm that ONLY exists at arity >= 3: at
    `a and b` the `bob` witness would be a member, so its exclusion is direct
    evidence the fold's extra arm bites.

    Arm 2 sits at the fold's depth-1 position, already covered by every binary
    intersection corpus; witnessing it would need a 4th distinct subject, which
    measurably puts this shape past the zcli per-spawn timeout (see the n-ary
    block in corpus.py for the numbers)."""
    schema_text, tuples, _ow = SCHEMAS[_NARY_INTER]
    orc = Oracle(schema_text, list(tuples))

    def chk(user, rel):
        return orc.check("...", "user", user, rel, "doc", "d1")

    assert chk("alice", "all_of"), (
        f"[{_NARY_INTER}] the 3-arm intersection is empty — it would pass "
        f"vacuously")
    # arm 3: bob satisfies a and b but not c
    assert chk("bob", "a") and chk("bob", "b") and not chk("bob", "c"), \
        f"[{_NARY_INTER}] the `bob` witness no longer isolates arm 3"
    assert not chk("bob", "all_of"), (
        f"[{_NARY_INTER}] arm 3 of the 3-arm intersection is not load-bearing: a "
        f"subject failing ONLY the third arm is still a member, so the fold's "
        f"extra arm is untested")
    # arm 1: carol satisfies b and c but not a
    assert chk("carol", "b") and chk("carol", "c") and not chk("carol", "a"), \
        f"[{_NARY_INTER}] the `carol` witness no longer isolates arm 1"
    assert not chk("carol", "all_of"), (
        f"[{_NARY_INTER}] arm 1 of the 3-arm intersection is not load-bearing")


# --------------------------------------------------------------------------- #
# (b) >= 3 STRATA
# --------------------------------------------------------------------------- #

def test_three_strata_corpus_features():
    """`three_strata_chain` really compiles to >= 3 strata, each one is
    load-bearing, and it is NOT gated against any Lean operational model."""
    schema_text, tuples, _ow = MULTI_STRATUM_SCHEMAS[_TRI]
    prod = parse_openfga_schema(schema_text)

    assert prod.compiled is not None, f"[{_TRI}] did not compile boolean plans"
    n_strata = len(prod.compiled.strata)
    assert n_strata == _TRI_EXPECTED_STRATA and n_strata >= 3, (
        f"[{_TRI}] compiles to {n_strata} strata, expected "
        f"{_TRI_EXPECTED_STRATA} (and at least 3) — the >= 3-stratum cascade "
        f"path this corpus exists for is no longer reached: {prod.compiled.strata}")
    assert all(len(s) >= 1 for s in prod.compiled.strata), (
        f"[{_TRI}] an empty stratum: {prod.compiled.strata}")

    # SCOPE (the ZT-P3-3 forcing function): >= 3 strata is OUTSIDE
    # W4Fragment.twoStrata and outside the fixed two-round `runCascade2`, so the
    # corpus must never reach a Lean OPERATIONAL comparison.
    assert _TRI not in SCHEMAS, (
        f"[{_TRI}] leaked into SCHEMAS — that would enrol it in the graph, "
        f"state and Lean-remove gates, comparing the operational model outside "
        f"W4Fragment.twoStrata (and zcli would NOT refuse: it gates on runtime "
        f"write admission and drained-ness, never on the fragment)")
    assert _TRI not in GRAPH_FRAGMENT, f"[{_TRI}] leaked into GRAPH_FRAGMENT"

    # Every stratum is load-bearing: each removes exactly one principal, so
    # collapsing the cascade by one round flips a distinct answer.
    orc = Oracle(schema_text, list(tuples))

    def chk(user, rel):
        return orc.check("...", "user", user, rel, "doc", "d1")

    assert chk("alice", "s1") and chk("alice", "s2") and chk("alice", "s3"), \
        f"[{_TRI}] the chain is empty at the top — every stratum would be vacuous"
    assert chk("bob", "e") and not chk("bob", "s1"), \
        f"[{_TRI}] stratum 1 (s1 = e but not b1) is not load-bearing"
    assert chk("carol", "s1") and not chk("carol", "s2"), \
        f"[{_TRI}] stratum 2 (s2 = s1 but not b2) is not load-bearing"
    assert chk("dave", "s2") and not chk("dave", "s3"), (
        f"[{_TRI}] stratum 3 (s3 = s2 but not b3) is not load-bearing — this is "
        f"the answer a two-round cascade would get WRONG, so it is the whole "
        f"point of the corpus")


@pytest.mark.parametrize("ops", ALL_SETOPS, ids=lambda o: o.name)
@pytest.mark.parametrize("name", sorted(MULTI_STRATUM_SCHEMAS))
def test_multi_stratum_three_way(name, ops):
    """PYTHON-ONLY three-backend differential on the >= 3-stratum corpora:
    independent oracle == real `SetEngine` == real graph index (`WildcardIndex` +
    `DeltaProcessor` cascade), over the full shared grid, under BOTH SetOps.

    No Lean artifact is involved: `W4Fragment.twoStrata` and the fixed two-round
    `runCascade2` put >= 3 strata outside the operational model's scope, so the
    Lean side of these corpora is `sem` ONLY and lives in
    `test_conformance_spec.py`. This leg exists so Python's >= 3-stratum cascade
    is actually driven and checked against the oracle."""
    schema_text, tuples, obj_wild = MULTI_STRATUM_SCHEMAS[name]
    queries = queries_for(schema_text, tuples)
    assert_grid_nonvacuous(f"{name}/{ops.name}", queries)

    orc = Oracle(schema_text, list(tuples))
    oracle = [orc.check(*q) for q in queries]

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    try:
        eng = SetEngine(session, "s1", schema_text, ops=ops,
                        object_wildcard_shapes=frozenset(obj_wild))
        for tup in tuples:
            eng.add_tuple(tup.subject_predicate, tup.subject_type,
                          tup.subject_name, tup.relation, tup.object_type,
                          tup.object_name)
        se = [bool(eng.check(*q)) for q in queries]
    finally:
        session.close()

    graph = graphindex_answers(schema_text, tuples, queries, obj_wild)

    assert len(oracle) == len(se) == len(graph) == len(queries), (
        f"[{name}/{ops.name}] answer-vector length mismatch")

    mism = [(queries[i], oracle[i], se[i]) for i in range(len(queries))
            if oracle[i] != se[i]]
    assert not mism, (
        f"[{name}/{ops.name}] oracle/set-engine disagreement on a >= 3-stratum "
        f"schema:\n{_fmt(mism, 'oracle', 'setengine')}")

    mism = [(queries[i], oracle[i], graph[i]) for i in range(len(queries))
            if oracle[i] != graph[i]]
    assert not mism, (
        f"[{name}/{ops.name}] oracle/graph-index disagreement on a >= 3-stratum "
        f"schema — the multi-stratum cascade is a GENUINE FINDING here:\n"
        f"{_fmt(mism, 'oracle', 'graph')}")


# --------------------------------------------------------------------------- #
# (e) TK94 -- the SCHEMAS-side coverage floor for a DERIVED relation used as the
#     predicate of a STORED USERSET SUBJECT.
#
# Censused 2026-09-21 while closing `TK92`: of the then-26 `SCHEMAS` entries,
# ZERO paired the two, so every `SCHEMAS`-parametrized arm -- and in particular
# the three GRAPH legs of `test_conformance_remove.py` -- had never run on the
# class. `TK92` had to hand-build a fixture in `tests/` to refute `TK91`'s
# unreachability hypothesis at all.
#
# (!) THE FLOOR IS OVER `SCHEMAS` SPECIFICALLY, NOT OVER THE HARNESS-WIDE CORPORA,
# and that is the whole point. `TTU_USERSET_SCHEMAS::derived_userset` (2026-07-27)
# is the same SHAPE but is spec-side only (`test_conformance_spec.py`), so a floor
# written over `_all_corpora()` would stay GREEN with the `SCHEMAS` entry deleted --
# an assurance step that fails by passing, this project's house failure mode.
# Sabotage S1 below is exactly that check.
# --------------------------------------------------------------------------- #

_DERIVED_USERSET_SUBJECT = "derived_userset_subject"


def _stored_userset_subjects_over_derived(schema_text, tuples):
    """`[(subject_type, subject_name, subject_predicate)]` for every stored tuple whose
    subject predicate names a DERIVED (boolean-tainted) relation of the schema.

    Derivedness is read from the COMPILED ruleset (`RuleSet.compiled.plans` keys), not
    from the schema text, so a relation that stops being derived -- e.g. its `but not`
    arm is dropped -- takes this floor red rather than quietly satisfying it.
    """
    compiled = parse_openfga_schema(schema_text).compiled
    if compiled is None:
        return []
    derived = set(compiled.plans)
    return [(t.subject_type, t.subject_name, t.subject_predicate)
            for t in tuples
            if t.subject_predicate not in ("...", "*")
            and (t.subject_type, t.subject_predicate) in derived]


def test_schemas_carries_a_derived_userset_subject():
    """At least one `SCHEMAS` corpus stores a userset subject whose predicate is a
    DERIVED relation, and at least one such subject object carries NO state of its own.

    Two claims, because the second is what `TK92` showed the first does not imply:

      (a) the class is present in `SCHEMAS` at all -- the census that was `0 of 26` on
          2026-09-21;
      (b) some such subject object appears as the OBJECT of no stored tuple, so it is
          interned during the bulk LOAD purely because it is a stored subject and has
          no positive-leaf state. That is the only shape under which the leading `rel`
          term of `index_v4/bulk_backfill.py::_BulkBackfill._live_keys_of` enumerates a
          name nothing else does (`TK92`, `tests/test_reg_tk92_bulk_rel_term.py`).

    Claim (b) is the load-bearing half. Without it the corpus RUNS the line and learns
    nothing from it, which is the state all 26 pre-existing corpora were in -- measured
    2026-09-22 over every `SCHEMAS` entry at the real gate driver
    (`formal/probes/tk94_new_arm_reach_2026-09-22.py`): eighteen corpora call
    `_live_keys_of` between 5 and 15 times across the five seeds and NONE of them ever
    gets a rel-exclusive name; nine never call it; `derived_userset_subject` is the
    only True.

    SCOPE (!): `SCHEMAS` is asserted, `GRAPH_FRAGMENT` is asserted AGAINST. The class is
    outside `FullScope.lean::W4Fragment` by a named field -- `term`'s `NoStoreSubjectR`
    half forbids a stored userset subject naming a derived relation, and Python ADMITS
    such a write (`test_w4fragment_scope_pin.py:83`, classified SILENT). zcli does not
    gate on the fragment, so `GRAPH_FRAGMENT` membership would silently compare two
    models no theorem relates -- the ZT-P3-3 mistake.

    SABOTAGE (2026-09-22, `docs/sabotage-procedure.md`), LITERAL observed output; each
    run is `pytest formal/conformance/test_conformance_nary_strata.py -q`, one byte-level
    edit per run, restored between runs (`.scratch/tk94/sabotage.py`):

      * CLEAN: `20 passed in 1.88s`, rc 0. RESTORED after the last run: `20 passed in
        2.45s`, rc 0 -- so every red below is attributable to its own edit.

      * S0 -- THE FIRST ATTEMPT WAS A GREEN THAT WAS CORRECT, and it is recorded because
        it is the easy mistake here. Renaming the dict key
        (`"derived_userset_subject"` -> `"_TK94_DISABLED_derived_userset_subject"`)
        returned `20 passed in 1.88s`, rc 0. That is not a hole: this floor tests the
        CLASS, not the name, so a rename is not a weakening at all. The mutation had to
        be re-cut as a real deletion. *Say what the edit was supposed to move, and check
        it moved* -- `docs/sabotage-procedure.md`, the P6 step-2 lesson.

      * S1 -- DELETE the `derived_userset_subject` entry from `SCHEMAS` (schema and
        tuples), the narrowest plausible weakening and the one this floor exists for. It
        is ALSO the control that the floor is not satisfied by the spec-side twin, which
        is left in place::

            E  AssertionError: NO `SCHEMAS` corpus stores a userset subject whose
               predicate is a derived relation -- the 0-of-26 census TK94 was filed for
               has returned. `TTU_USERSET_SCHEMAS::derived_userset` does NOT satisfy
               this: it is spec-side only, so the graph arms still never see the class.
            E  assert {}
            FAILED ...::test_schemas_carries_a_derived_userset_subject
            1 failed, 19 passed in 1.94s

      * S2 -- keep the entry, delete ONLY its `g2#member viewer d2` tuple (the
        rel-exclusive subject). Claim (a) survives; claim (b) is the one that must fire::

            E  AssertionError: [['derived_userset_subject']] every derived-userset
               subject object also carries state of its own (['g1']) -- the bulk
               mirror's leading `rel` term is REACHED but never exclusive, so this
               corpus does not discriminate it (TK92). Add a subject object with no
               tuples of its own.
            E  assert {}
            FAILED ...::test_schemas_carries_a_derived_userset_subject
            1 failed, 19 passed in 2.05s

        S2 is the sharp one. S1 alone would be satisfied by any corpus of the shape,
        including one that cannot tell the branch apart -- which is the state `TK92`
        found four whole modules in.

      * S3 -- the INSTRUMENT control: invert `_stored_userset_subjects_over_derived`'s
        filter to `in ("...", "*")`, so the helper reports BARE subjects as
        derived-userset ones. Without this arm, a green above could be the helper
        matching nothing rather than the corpus being right::

            E  AssertionError: NO `SCHEMAS` corpus stores a userset subject whose
               predicate is a derived relation ...
            E  assert {}
            FAILED ...::test_schemas_carries_a_derived_userset_subject
            1 failed, 19 passed in 2.21s

        (!) S3's message is IDENTICAL to S1's, because both end at an empty `found`.
        The two are distinguishable only by which edit was applied, not by the output --
        so read this list, not the failure text, when this test goes red.

    NOT SWEPT, and said rather than implied: this is one test appended to a module of
    twenty, and the mutation sweep above covers its own predicate and helper only, not
    the module. `docs/sabotage-procedure.md` asks for a module-wide sweep when a module
    is ADDED; this floor joins an existing one.
    """
    from formal.conformance.corpus import TTU_USERSET_SCHEMAS

    found: dict[str, list] = {}
    for name in sorted(SCHEMAS):
        schema_text, tuples, _ow = SCHEMAS[name]
        subs = _stored_userset_subjects_over_derived(schema_text, tuples)
        if subs:
            found[name] = subs

    assert found, (
        "NO `SCHEMAS` corpus stores a userset subject whose predicate is a derived "
        "relation -- the 0-of-26 census TK94 was filed for has returned. "
        "`TTU_USERSET_SCHEMAS::derived_userset` does NOT satisfy this: it is "
        "spec-side only, so the graph arms still never see the class.")

    # (b) somewhere among them, a subject object with no state of its own.
    stateless_anywhere = {}
    for name, subs in found.items():
        _schema_text, tuples, _ow = SCHEMAS[name]
        objects = {(t.object_type, t.object_name) for t in tuples}
        stateless = sorted(sn for (st, sn, _sp) in subs if (st, sn) not in objects)
        if stateless:
            stateless_anywhere[name] = stateless
    assert stateless_anywhere, (
        f"[{sorted(found)}] every derived-userset subject object also carries state of "
        f"its own ({sorted({sn for subs in found.values() for (_st, sn, _sp) in subs})}) "
        f"-- the bulk mirror's leading `rel` term is REACHED but never exclusive, so "
        f"this corpus does not discriminate it (TK92). Add a subject object with no "
        f"tuples of its own.")

    # SCOPE: in SCHEMAS, and deliberately NOT in GRAPH_FRAGMENT.
    for name in found:
        assert name not in GRAPH_FRAGMENT, (
            f"[{name}] stores a userset subject over a derived relation and has leaked "
            f"into GRAPH_FRAGMENT. `FullScope.lean::W4Fragment.term`'s `NoStoreSubjectR` "
            f"half is FALSE for such a store, and zcli would NOT refuse it (it gates on "
            f"admission rc 2 / drained-ness rc 3, never on the fragment), so the Lean "
            f"graph/state/bulk gates would compare two models no theorem relates -- the "
            f"ZT-P3-3 mistake. Keep it in SCHEMAS only; the python-to-python remove legs "
            f"are what it is there for.")

    # The spec-side twin still exists and is still NOT in SCHEMAS -- if it were, the
    # floor above would be satisfied by a corpus with no graph arms at all.
    assert "derived_userset" in TTU_USERSET_SCHEMAS, (
        "`TTU_USERSET_SCHEMAS::derived_userset` is gone -- the spec-side half of this "
        "class went with it")
    assert "derived_userset" not in SCHEMAS, (
        "`derived_userset` was moved into SCHEMAS. That is not automatically wrong, but "
        "it enrols an out-of-W4Fragment shape in every SCHEMAS-parametrized arm and its "
        "store was never built for them -- re-adjudicate, do not just delete this line.")
