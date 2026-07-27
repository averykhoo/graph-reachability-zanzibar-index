"""Language-feature coverage: n-ARY operators and >= 3 STRATA (ZT-P4-4).

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
residue was still open.** Over all 69 schemas the harness reads (28 curated + 40
generated + `three_strata_chain`) the operator-arity histogram was
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
# reads (28 curated corpora + 40 generated + `three_strata_chain`): before
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
# schemas the harness reads (28 curated + 40 generated + three_strata_chain):
#   closure 211 · derived-computed 42 · derived-ttu 50 · derived-userset 0
# `derived-userset` (`zanzibar_utils_v1.py::PDerivedUserset`) was compiled by NO
# corpus, in exactly the plan-leaf area where the X4 adjudication found five real
# divergences. `corpus.py::TTU_USERSET_SCHEMAS['derived_userset']` closes it.
_REQUIRED_LEAF_KINDS = ("closure", "derived-computed", "derived-ttu",
                        "derived-userset")

# STILL ZERO after 2026-07-27, recorded rather than asserted: `derived-tupleset-ttu`
# (`::PDerivedTuplesetTTU` — `target from tupleset` where the TUPLESET relation is
# itself derived). Not added here because it needs its own scope argument; it is
# the remaining plan-leaf hole and is listed on the board.


def test_every_plan_leaf_kind_is_reached_by_some_corpus():
    """Every compiled plan-leaf KIND in `_REQUIRED_LEAF_KINDS` is produced by at
    least one corpus the harness actually runs. A `compile_ruleset` branch that
    no corpus reaches is a branch no differential ever exercises."""
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
