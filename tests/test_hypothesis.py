"""
P8: the hypothesis campaign (boolean spec §9).

Property layer (stateless):
  * metamorphic schema pairs over identical tuple sequences -- A∖B ≡ A∖(A∧B),
    (A∪B)∖C ≡ (A∖C)∪(B∖C), the De Morgan pair -- asserted as full-grid equality
    between the paired stores on every backend (via two ParityEngines, which each
    already assert 4-way agreement internally);
  * add-then-remove restores the exact row multiset (ids ignored), residues included;
  * permutation invariance for commuting op sets;
  * replay: raw writes with no cascade, then ONE cascade over the outbox from zero,
    equals the live per-op-cascaded store;
  * parser round-trip on GENERATED schemas (parse ∘ unparse ∘ parse ≡ parse);
  * generated cyclic boolean schemas are refused at compile;
  * boundary: self-referential wildcard tuples (rejected shape and the accepted
    object-star self-containment) -- accept/reject parity + I12.

Stateful layer: a RuleBasedStateMachine drawing weighted add/remove/check ops against
a ParityEngine over a GENERATED stratifiable schema; every accepted op already runs
unanimity + I12 + full-grid oracle parity + paranoia + the graph's I9 audit inside
the engine.

Profiles: 'ci' (fast, default) / 'deep' (HYPOTHESIS_PROFILE=deep for local/nightly).
"""

import os
from typing import NamedTuple

import pytest
from hypothesis import HealthCheck, Phase, assume, example, given, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from index_v4.invariants import snapshot_rows
from index_v4.outbox import outbox_watermark
from index_v4.processor import DeltaProcessor
from zanzibar_utils_v1 import (Computed, CyclicDerivedDependency, Direct,
                               DoublyBridgedShapeError, Exclusion,
                               Intersection, Restriction, TTU, Union,
                               UnsupportedByGraphIndex,
                               parse_openfga_schema, parse_schema_ast,
                               unparse_schema_ast, wildcard_userset_restriction_shapes)
from setengine import ALL_SETOPS, SetEngine
from tests.parity import ParityEngine, _fresh_session
from tests.test_processor import build

settings.register_profile('ci', max_examples=12, stateful_step_count=8,
                          deadline=None, suppress_health_check=[HealthCheck.too_slow],
                          phases=(Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink))
settings.register_profile('deep', max_examples=120, stateful_step_count=25,
                          deadline=None, suppress_health_check=[HealthCheck.too_slow])
settings.load_profile(os.environ.get('HYPOTHESIS_PROFILE', 'ci'))

USERS = ['u1', 'u2']
DOCS = ['d1', 'd2']
FOLDERS = ['f1']

# The pool generator's subject-name table (design doc `docs/design/generator-coverage/`
# §3 hunk 1). ``_op_pool`` used ``USERS if r.type == 'user' else DOCS``, which is correct
# only while every non-user restriction is ``doc``-typed. The moment the TTU tupleset can
# restrict a SECOND entity type that fallback emits ``folder:d1``.
#
# ⚠ The design doc calls that "a restriction-INVALID tuple" which the set engine rejects.
# It is NOT -- measured 2026-08-10: entity NAMES are free-form, so ``folder:d1`` is a
# perfectly legal tuple about a folder entity named ``d1``, and an admission-rate guard
# (which is what the design prescribes) stays GREEN over it. The real damage is quieter
# and therefore worse: the check grid queries ``folder:f1``, so every such write is
# admitted, driven, and INERT -- a "compiled but never driven" corpus. A table keyed by
# the restriction's own ``r.type`` keeps the pool and the grid on ONE universe by
# construction, and ``test_op_pool_is_schema_valid_and_co_varies_with_the_grid`` is the
# mechanical guard: it asserts the universe, not merely the admission.
TYPE_NAMES = {'user': USERS, 'doc': DOCS, 'folder': FOLDERS}


# ---------------------------------------------------------------------------
# Generated schemas: relations on `doc` built in topo order (stratifiable by
# construction), referencing only earlier relations; rendered via the unparser.
# ---------------------------------------------------------------------------

_BASE_DIRECTS = [
    (Restriction('user', '...', False),),
    (Restriction('user', '...', False), Restriction('user', '...', True)),
    (Restriction('user', '...', True),),
]

# --- the TTU tupleset grammar (item (c), HANDOFF plan 1b) ------------------- #
# Until 2026-08-10 ``schema_asts`` PINNED the tupleset to
# ``{('doc','parent'): Direct((Restriction('doc','...',False),))}``, so every TTU in every
# generated schema read a plain single-type non-boolean ``parent: [doc]``. The whole
# "TTU over a structured tupleset" space was therefore unreachable BY CONSTRUCTION --
# not by seed luck, and not fixable by raising ``max_examples`` (measured:
# `docs/design/generator-coverage/README.md` §0 -- 13 of the 15 never-reached coverage
# features are that one hardcoded relation). Both 2026-08-10 divergences (RC1/RC2) came
# through it.
#
# The bodies below are Direct-leaf-only on purpose: ``compile_ruleset`` REFUSES a tupleset
# carrying computed/rewritten arms ("Zanzibar tupleset semantics read stored tuples only")
# and refuses userset restrictions on a tupleset outright, so drawing those would just
# measure the rejection path. Booleans, multi-type and subject-wildcard leaves are all
# admissible and are all drawn.
_R_DOC = Restriction('doc', '...', False)
_R_FOLDER = Restriction('folder', '...', False)
_R_DOC_STAR = Restriction('doc', '...', True)

# ⚠ THE NEG-ONLY TRAP, recorded because a reviewer cannot see it by eye. A subtrahend
# whose type ALSO occurs in the base -- e.g. ``Exclusion(Direct([doc, folder]),
# Direct([doc]))`` -- *looks* like a neg-only arm, compiles, reads correctly in review,
# and yields ``parent`` ≡ ∅: the same raw tuple routes to both arms and cancels. That is a
# "compiled but never driven" cell (`docs/sabotage-procedure.md`, the 2026-07-28 row), and
# the design's first witness builder shipped exactly it and found ZERO divergences. Every
# ``negonly-*`` body below has base types DISJOINT from subtrahend types, which is
# asserted mechanically -- and independently of the production ``_member_types`` walk,
# which is itself the seat of RC1 -- by
# ``test_negonly_tupleset_bodies_really_have_a_type_only_in_the_negative_arm``.
_TUPLESET_BODIES = {
    # untainted (plain `parent`): the pre-2026-08-10 behaviour, kept as a stratum so the
    # new grammar cannot regress what the old one reached.
    'plain': Direct((_R_DOC,)),
    'multitype': Direct((_R_DOC, _R_FOLDER)),
    'wildcard': Direct((_R_DOC, _R_DOC_STAR)),
    'multitype-wildcard': Direct((_R_DOC, _R_FOLDER, _R_DOC_STAR)),
    # tainted (`parent` becomes a DERIVED predicate with storage leaves)
    'union': Union((Direct((_R_DOC,)), Direct((_R_FOLDER,)))),
    'intersection': Intersection((Direct((_R_DOC, _R_FOLDER)), Direct((_R_DOC,)))),
    # RC1's shape: `doc` occurs ONLY in the subtrahend, so `_member_types`' `walk(e.base)`
    # drops it from the compiled `parent_types` and the TTU stops walking a stored
    # `doc:dX parent doc:dY` tuple.
    'negonly-multitype': Exclusion(Direct((_R_FOLDER,)), Direct((_R_DOC,))),
    # RC2's shape: a STORED `doc:*` parent on a DERIVED tupleset relation.
    'negonly-star': Exclusion(Direct((_R_DOC_STAR,)), Direct((_R_FOLDER,))),
}
_TUPLESET_KINDS = sorted(_TUPLESET_BODIES)


# --- the choice seam ------------------------------------------------------- #
# Both schema generators are written against this four-method interface instead of
# against `draw` directly, and there are two implementations of it.
#
# WHY: the 4-way-rate and coverage floors below have to measure the DISTRIBUTION a
# generator produces, which needs hundreds of independent draws. Doing that with
# `@given(st.lists(strategy, min_size=N))` does NOT work and fails in the project's
# characteristic direction -- at a small `max_examples` hypothesis emits its minimal
# buffer, every element of the list comes back IDENTICAL, and the sweep then reports a
# perfectly stable rate computed from one configuration. (Observed while writing this:
# 80 "draws" that were 80 copies of one schema.) Driving the same generator body with a
# seeded `random.Random` gives real variety and is reproducible.
#
# The seam is what keeps the instrument honest: the sweeps drive the SAME function the
# fuzzer does, not a private re-implementation that could drift into measuring a clone.

class _Choices:
    """Interface only -- see ``_HypothesisChoices`` / ``_RandomChoices``."""

    def one(self, seq):          # pick one element
        raise NotImplementedError

    def intrange(self, lo, hi):  # inclusive
        raise NotImplementedError

    def perm(self, seq):         # a permutation
        raise NotImplementedError

    def subset(self, seq):       # a frozenset subset
        raise NotImplementedError


class _HypothesisChoices(_Choices):
    def __init__(self, draw):
        self._draw = draw

    def one(self, seq):
        return self._draw(st.sampled_from(list(seq)))

    def intrange(self, lo, hi):
        return self._draw(st.integers(min_value=lo, max_value=hi))

    def perm(self, seq):
        return list(self._draw(st.permutations(list(seq))))

    def subset(self, seq):
        seq = list(seq)
        if not seq:
            return frozenset()
        return frozenset(self._draw(st.sets(st.sampled_from(seq), max_size=len(seq))))


class _RandomChoices(_Choices):
    """The deterministic driver for the rate/coverage sweeps. Seeded, so a failure is
    reproducible; NOT used by any property test."""

    def __init__(self, rng):
        self._rng = rng

    def one(self, seq):
        return self._rng.choice(list(seq))

    def intrange(self, lo, hi):
        return self._rng.randint(lo, hi)

    def perm(self, seq):
        seq = list(seq)
        self._rng.shuffle(seq)
        return seq

    def subset(self, seq):
        seq = list(seq)
        return frozenset(x for x in seq if self._rng.random() < 0.5)


def _restriction_types(expr) -> frozenset[str]:
    """Every entity type named by a bare (``'...'``-predicate) restriction anywhere in
    ``expr`` -- BOTH arms of an Exclusion. Deliberately local and total: the production
    ``_member_types`` takes only ``walk(e.base)`` for an Exclusion, which is RC1 itself,
    so reusing it here would make the instrument share its subject's defect."""
    if isinstance(expr, Direct):
        return frozenset(r.type for r in expr.restrictions if r.predicate == '...')
    if isinstance(expr, (Union, Intersection)):
        return frozenset().union(*(_restriction_types(c) for c in expr.children)) \
            if expr.children else frozenset()
    if isinstance(expr, Exclusion):
        return _restriction_types(expr.base) | _restriction_types(expr.subtract)
    return frozenset()


@st.composite
def schema_asts(draw, allow_usersets: bool = True, tupleset_kind: str | None = None):
    """Relations on ``doc`` in topo order (stratifiable), each referencing only earlier
    relations.

    ``tupleset_kind`` (item (c), 2026-08-10) selects the body of ``parent`` -- the tupleset
    of EVERY generated TTU -- from ``_TUPLESET_BODIES`` instead of the pre-2026-08-10
    hardcoded ``[doc]``. Left as ``None`` it is DRAWN, so the campaign fuzzes multi-type,
    subject-wildcard, boolean and neg-only-arm tuplesets. The parameter exists so a caller
    can pin one cell deterministically (see the pins below); it must never be used to
    narrow the campaign back to ``'plain'``.

    ``allow_usersets`` (G2) offers a CONCRETE userset leaf ``[doc#r_k]``. It is ON by
    default: when ``r_k`` is tainted the userset makes a schema carry userset-shaped
    subjects (``doc:X#r_k``) over a derived relation, exercising the edge-free-userset
    (``ResidueV1.upos``) + ``_find_leaf_node`` reconcile paths and the full X4/D2/upos
    userset-subject-through-derived family. Until 2026-07-17 this leaf was OPT-IN (default
    OFF) because it tripped three then-open graph behaviours the deep hunt surfaced; ALL
    THREE are now FIXED (the ``processor._leaf_concretes`` upos lift for the derived-computed
    and derived-userset branches, plus the state-functional implicit-flag canonicalization --
    promote-on-record / demote-on-release) and pinned, so the leaf is fully fuzzed again
    (deviations 2026-07-17, "fuzzer blind-spot hardening" + the fix sub-entry):
      * the answer-benign implicit-flag CANONICAL DRIFT (a derived object node doubling as a
        self-referential userset subject) -- pinned by
        ``test_pderived_userset_self_ref_cascade_replay_drift``;
      * the graph from-chain-through-boolean-TTU-arm completeness gap -- pinned by
        ``test_lookup_oracle.py::test_graph_from_chain_userset_through_boolean_ttu_arm``;
      * the graph userset-subject-through-derived completeness gap (wildcard variant) --
        pinned by ``test_lookup_oracle.py::test_graph_userset_subject_through_derived_wildcard_gap``
        (and its granted-userset sibling ``::test_graph_userset_member_through_granted_userset_over_derived``).
    The PDerivedUserset reconcile WRITE path (upos / ``_find_leaf_node``) is additionally
    covered deterministically by ``test_pderived_userset_add_remove_deterministic_pin``.
    ``allow_usersets`` remains a knob (default ON) so a future novel divergence can re-exclude
    the narrowest class if ever needed."""
    return _schema_ast(_HypothesisChoices(draw), allow_usersets, tupleset_kind)


def _schema_ast(ch, allow_usersets: bool = True, tupleset_kind: str | None = None):
    """The generator BODY, written against the ``_Choices`` interface (see there for why).
    ``schema_asts`` is the hypothesis-driven wrapper; the coverage/rate sweeps below drive
    this same function with a seeded RNG."""
    n = ch.intrange(2, 5)
    names = [f'r{i}' for i in range(n)]
    if tupleset_kind is None:
        tupleset_kind = ch.one(_TUPLESET_KINDS)
    ast = {('doc', 'parent'): _TUPLESET_BODIES[tupleset_kind]}

    def expr(i: int, depth: int):
        leaves = [Direct(ch.one(_BASE_DIRECTS))]
        if i > 0:
            ref = ch.one(names[:i])
            leaves.append(Computed(ref))
            leaves.append(TTU(ref, 'parent'))
            # G2 (deviations 2026-07-17): a CONCRETE userset restriction over an
            # EARLIER (possibly tainted) relation -- `[doc#r_k]`. When r_k is derived
            # this compiles to a PDerivedUserset and drives the edge-free-userset
            # (`ResidueV1.upos`) + `_find_leaf_node` reconcile paths, which twice had
            # CRITICAL bugs found by review not fuzzing (deviations 2026-07-08 D2;
            # 2026-07-08 review-2 #1). Offered at modest probability so the existing
            # example distribution is not washed out.
            if allow_usersets and ch.intrange(0, 2) == 0:
                uref = ch.one(names[:i])
                leaves.append(Direct((Restriction('doc', uref, False),)))
        if depth >= 2:
            return ch.one(leaves)
        kind = ch.one(['leaf', 'leaf', 'union', 'intersection', 'exclusion'])
        if kind == 'leaf':
            return ch.one(leaves)
        a, b = expr(i, depth + 1), expr(i, depth + 1)
        if kind == 'union':
            return Union((a, b))
        if kind == 'intersection':
            return Intersection((a, b))
        return Exclusion(a, b)

    for i, name in enumerate(names):
        ast[('doc', name)] = expr(i, 0)
    if 'folder' in _restriction_types(ast[('doc', 'parent')]):
        # A `folder`-typed tupleset parent is only DRIVEN if `folder` declares the
        # relation a TTU reads off it: `r0 from parent` over `folder:f1 parent doc:d1`
        # resolves to (folder, r0). Without this the folder arm compiles and is never
        # driven -- the "compiled but never driven" cell the sabotage procedure names.
        # r0 is the one name every draw has (n >= 2) and the only one a TTU can target
        # from position 1, so it is the cell-bearing choice.
        ast[('folder', names[0])] = Direct((Restriction('user', '...', False),))
    return ast


def _directs(x):
    """Every ``Direct`` leaf of an expression -- BOTH arms of an Exclusion (a subtrahend
    restriction is a writable, admissible shape and a genuine STORED tupleset parent)."""
    if isinstance(x, Direct):
        yield x
    elif isinstance(x, (Union, Intersection)):
        for c in x.children:
            yield from _directs(c)
    elif isinstance(x, Exclusion):
        yield from _directs(x.base)
        yield from _directs(x.subtract)


def _op_pool(ast):
    """Schema-valid raw tuples over the tiny universe (Direct restrictions only).

    The walk is already AST-generic; what was hardcoded was the NAME TABLE (see
    ``TYPE_NAMES``). Validity is preserved by the same argument the pre-2026-08-10 code
    relied on: every emitted candidate is derived from a declared restriction of the very
    relation it is written to, so it matches by construction -- now for any restriction
    type, not just ``user``/``doc``."""
    out = []
    for (otype, rel), e in ast.items():
        for d in _directs(e):
            for r in d.restrictions:
                names = ['*'] if r.wildcard else TYPE_NAMES[r.type]
                for sn in names:
                    for on in TYPE_NAMES[otype]:
                        out.append((r.predicate, r.type, sn, rel, otype, on))
    return sorted(set(out))


def _grid(ast):
    """The check grid, DERIVED from the AST's own Direct restrictions (design §3 hunk 3).

    It used to hardcode ``('...', 'user', ...)`` subjects and ``DOCS`` objects, which is
    blind to any object type or subject shape the schema declares beyond those -- so a
    multi-type tupleset would be compiled and never queried. Values may be ``None`` (the
    deterministic pins below pass a key-only dict); such entries contribute no subject
    shapes and fall back to the legacy user subjects."""
    subject_shapes = {('user', '...')}
    for e in ast.values():
        if e is None:
            continue
        for d in _directs(e):
            for r in d.restrictions:
                subject_shapes.add((r.type, r.predicate))
    subjects = [(pred, s_type, sn)
                for (s_type, pred) in sorted(subject_shapes)
                for sn in TYPE_NAMES.get(s_type, []) + ['ghost', '*']]
    otypes = sorted({ot for (ot, _rel) in ast})
    objects = {ot: TYPE_NAMES.get(ot, []) + ['ghost' + ot[0].upper()] for ot in otypes}
    return [(sp, st_, sn, rel, ot, on)
            for (ot, rel) in sorted(ast)
            for (sp, st_, sn) in subjects
            for on in objects[ot]]


# ---------------------------------------------------------------------------
# Item (c) assurance: the tupleset grammar is admissible, driven, and NOT vacuous
# (HANDOFF plan 1b; docs/design/generator-coverage/README.md §3, §4 sabotages 2/6/8)
# ---------------------------------------------------------------------------

def _ts_probe_schema(kind: str, negated: bool = False) -> str:
    """A minimal deterministic schema carrying tupleset body ``kind`` plus a TTU over it
    -- the same shape the campaign draws, assembled without hypothesis so the assertions
    below are exhaustive over ``_TUPLESET_BODIES`` rather than sampled."""
    # ``negated`` selects the TTU's POLARITY, and the two must be probed SEPARATELY.
    # Both shapes are ones `_schema_ast`'s `expr` builds (`TTU(ref, 'parent')` as a leaf,
    # and the same leaf as an Exclusion subtrahend). Probing only one mis-classifies
    # severity by a sign -- a dropped TTU parent is a false NEGATIVE under a positive TTU
    # and a false POSITIVE, i.e. an authorization FAIL-OPEN, under a negated one -- and
    # putting both in ONE schema does not fix that: the positive relation's mismatch is
    # reported first and MASKS the negated one, which is a compiled-but-never-observed
    # cell wearing the disguise of a covered one.
    ttu = TTU('r0', 'parent')
    ast = {('doc', 'parent'): _TUPLESET_BODIES[kind],
           ('doc', 'r0'): Direct((Restriction('user', '...', False),)),
           ('doc', 'r1'): (Exclusion(Direct((Restriction('user', '...', False),)), ttu)
                           if negated else ttu)}
    if 'folder' in _restriction_types(_TUPLESET_BODIES[kind]):
        ast[('folder', 'r0')] = Direct((Restriction('user', '...', False),))
    return unparse_schema_ast(ast)


def test_negonly_tupleset_bodies_really_have_a_type_only_in_the_negative_arm():
    """★ THE ANTI-VACUITY GUARD FOR THE NEG-ONLY CELL.

    Property: for every ``negonly-*`` tupleset body the campaign can draw, some entity
    type occurs in the SUBTRAHEND and in no base arm. That is what makes it the RC1 shape;
    a body whose subtrahend type also occurs in the base compiles, reads correctly in
    review, and yields ``parent`` ≡ ∅ -- a compiled-but-never-driven cell, and the
    documented first-draft failure of the 2026-08-10 design (its sweep found ZERO
    divergences until the construction was corrected).

    The check is derived from ``_TUPLESET_BODIES`` itself, so a new body cannot be added
    without being covered, and it walks the AST with the LOCAL ``_restriction_types``
    rather than the production ``_member_types`` -- which takes ``walk(e.base)`` only and
    is RC1 itself. An instrument that shares its subject's defect measures nothing.

    Sabotage (observed 2026-08-10): changing `negonly-multitype` to the plausible-looking
    ``Exclusion(Direct((_R_DOC, _R_FOLDER)), Direct((_R_DOC,)))`` -- which still *is* an
    exclusion with a subtrahend, still compiles, still drives an Exclusion plan node --
    fires this test:
        AssertionError: tupleset body 'negonly-multitype' has NO type that occurs only in
        the negative arm (base={'doc', 'folder'} neg={'doc'}); it compiles and drives
        `parent` = empty
    """
    negonly = [k for k in _TUPLESET_KINDS if k.startswith('negonly')]
    assert negonly, 'the neg-only tupleset cell disappeared from _TUPLESET_BODIES'
    for kind in negonly:
        body = _TUPLESET_BODIES[kind]
        assert isinstance(body, Exclusion), f'{kind} is not an Exclusion'
        base = _restriction_types(body.base)
        neg = _restriction_types(body.subtract)
        assert neg - base, (
            f"tupleset body {kind!r} has NO type that occurs only in the negative arm "
            f"(base={set(base)} neg={set(neg)}); it compiles and drives `parent` = empty")
        # ...and the neg-only type must be WRITABLE as a stored parent, or the cell is
        # still never driven. The pool is the thing that drives it.
        pool = _op_pool({('doc', 'parent'): body})
        for t in sorted(neg - base):
            assert any(raw[1] == t and raw[3] == 'parent' for raw in pool), (
                f'{kind}: no candidate write carries the neg-only type {t!r} onto '
                f'`parent`, so the stored-parent path is never exercised')


def test_op_pool_is_schema_valid_and_co_varies_with_the_grid():
    """★ THE POOL/SCHEMA CO-VARIANCE GUARD (design §4 sabotage 8), and the reason item (c)
    is safe. Two properties, because the first one alone is NOT enough:

    (1) ADMISSION -- every candidate ``_op_pool`` emits is accepted by the set engine,
        which validates restrictions strictly (the graph admits a restriction-invalid
        tuple as a silent no-op). Measured 2026-08-10: 3550/3550 = 100.0 % over the
        deterministic sweep, and zero refusals over every tupleset kind here.

    (2) UNIVERSE -- every entity a candidate writes to is an entity the CHECK GRID
        queries. A pool and a grid that disagree on the universe produce a corpus that is
        admitted, driven, and answers ``False`` everywhere: compiled and never driven.

    ⚠ (2) exists because sabotage 8 as filed in
    `docs/design/generator-coverage/README.md` DOES NOT WORK, and the design's stated
    reason for the typed table is wrong. Reverting ``_op_pool`` to
    ``names = ['*'] if r.wildcard else (USERS if r.type == 'user' else DOCS)`` emits
    ``folder:d1``, and the design predicted the set engine would refuse it as
    "restriction-INVALID". It does not: entity NAMES are free-form, so ``folder:d1`` is a
    perfectly legal tuple -- about a folder entity named ``d1`` that no query ever
    mentions. Measured 2026-08-10 with the untyped fallback restored:
        1 passed        <- the admission-only version of this test, GREEN over the defect
    The damage is silent inertness, not rejection, which is strictly harder to notice --
    so the guard has to be the universe check, and it is:
        AssertionError: tupleset kind 'intersection': 4/14 candidates write to entities
        the check grid never queries, so they are admitted and inert:
        [('...', 'folder', 'd1', 'parent', 'doc', 'd1'),
         ('...', 'folder', 'd1', 'parent', 'doc', 'd2'),
         ('...', 'folder', 'd2', 'parent', 'doc', 'd1'),
         ('...', 'folder', 'd2', 'parent', 'doc', 'd2')]
    """
    for kind in _TUPLESET_KINDS:
        schema = _ts_probe_schema(kind)
        ast = parse_schema_ast(schema)
        pool = _op_pool(ast)
        assert pool, f'{kind}: empty candidate pool'
        assert any(raw[3] == 'parent' for raw in pool), f'{kind}: no `parent` candidates'

        se = SetEngine(_fresh_session(), 's', schema)
        refused = []
        for raw in pool:
            try:
                se.add_tuple(*raw)
            except ValueError:
                refused.append(raw)
        assert not refused, (
            f'tupleset kind {kind!r}: the set engine REFUSED {len(refused)}/{len(pool)} '
            f'candidates the pool claims are schema-valid: {refused[:4]}')

        grid = _grid(ast)
        known = {(q[1], q[2]) for q in grid} | {(q[4], q[5]) for q in grid}
        inert = [raw for raw in pool
                 if (raw[1], raw[2]) not in known and raw[2] != '*'
                 or (raw[4], raw[5]) not in known]
        assert not inert, (
            f'tupleset kind {kind!r}: {len(inert)}/{len(pool)} candidates write to '
            f'entities the check grid never queries, so they are admitted and inert: '
            f'{inert[:4]}')


def test_every_tupleset_kind_is_reachable_and_the_grid_queries_it():
    """Non-vacuity for the whole tupleset axis: every body in ``_TUPLESET_BODIES`` is a
    value ``schema_asts`` can draw, round-trips through the unparser, and lands in a check
    grid that actually queries ``parent`` and every object type it introduces.

    The kind list is DERIVED from the table (``_TUPLESET_KINDS = sorted(...)``), so adding
    a body without wiring it into the draw is a red test rather than a silent gap."""
    assert len(_TUPLESET_KINDS) >= 8, _TUPLESET_KINDS
    for kind in _TUPLESET_KINDS:
        schema = _ts_probe_schema(kind)
        ast = parse_schema_ast(schema)
        assert ast[('doc', 'parent')] == _TUPLESET_BODIES[kind], kind
        grid = _grid(ast)
        assert any(q[3] == 'parent' for q in grid), f'{kind}: grid never queries `parent`'
        assert any(q[3] == 'r1' for q in grid), f'{kind}: grid never queries the TTU'
        for t in _restriction_types(_TUPLESET_BODIES[kind]):
            assert any(q[1] == t for q in grid), (
                f'{kind}: grid has no {t}-typed subject, so the tupleset arm that '
                f'declares it is compiled and never driven')


def test_every_tupleset_kind_is_driven_against_the_oracle():
    """★★ EXPECTED RED until the RC1/RC2 TTU-tupleset fix lands (HANDOFF plan item 1).
    This is the positive control the whole of item (c) exists to produce, and it is a
    POSITIVE PIN, not an xfail (`CLAUDE.md`; `verify.sh` carries MAX_TESTS_XFAILED=0).

    Property: for every tupleset body the generator can draw, driving the generator's OWN
    candidate pool through a ParityEngine agrees with the oracle on the generator's OWN
    check grid. Each configuration is driven with a two-tuple subset -- one stored
    ``parent`` write and one grant on the TTU's target -- because a fail-closed divergence
    is an under-grant and ANY extra granting tuple in the store masks it (this repo's own
    IIA property, commit 310fbcb; the design's full-pool variant found zero divergences
    over the same configurations).

    ★ The instrument carries its own control, which is what makes the red ATTRIBUTABLE.
    Measured 2026-08-10 at this commit, over all 8 bodies x both TTU polarities -- 12 of
    the 16 cells are GREEN, including every body the campaign could reach before this
    change, and exactly the 4 new ones are red:

        negonly-multitype / positive TTU:
            (('...','doc','d1','parent','doc','d1'), ('...','user','u1','r0','doc','d1'))
            q=('...','user','u1','r1','doc','d1') graph=False oracle=True
        negonly-multitype / negated TTU:
            (('...','doc','d1','parent','doc','d1'), ('...','user','u1','r1','doc','d1'),
             ('...','user','u1','r0','doc','d1'))
            q=('...','user','u1','r1','doc','d1') graph=True  oracle=False
        negonly-star / positive TTU:
            (('...','doc','*','parent','doc','d1'), ('...','user','u1','r0','doc','d1'))
            q=('...','user','u1','r1','doc','d1') graph=False oracle=True
        negonly-star / negated TTU:
            (('...','doc','*','parent','doc','d1'), ('...','user','u1','r1','doc','d1'),
             ('...','user','u1','r0','doc','d1'))
            q=('...','user','u1','r1','doc','d1') graph=True  oracle=False

    ``plain`` -- the PRE-2026-08-10 hardcoded body -- is green, which is the whole
    argument: the blind spot was the GRAMMAR, not the sampling budget. The four red cells
    are RC1 (a type only in the tupleset's negative arm) and RC2 (a stored ``doc:*``
    parent on a derived tupleset), each in both severity directions; both are pinned
    independently by ``tests/test_ttu_tupleset_parent_types.py``. Note the negated rows:
    ``graph=True oracle=False`` is an authorization FAIL-OPEN, and the design this work
    follows recorded that its prototype sweep could NOT reproduce that direction
    (`docs/design/generator-coverage/README.md` §6.7) -- driving both polarities as
    SEPARATE schemas is what surfaces it. When the fix lands this test goes green with no
    edit; if it needs an edit to go green, the fix is wrong."""
    grant = ('...', 'user', 'u1', 'r0', 'doc', 'd1')       # makes d1 an r0-member
    base = ('...', 'user', 'u1', 'r1', 'doc', 'd1')        # the negated TTU's base arm
    diverged, driven, checked = {}, 0, 0
    for kind in _TUPLESET_KINDS:
        for negated in (False, True):
            schema = _ts_probe_schema(kind, negated)
            ast = parse_schema_ast(schema)
            try:
                parse_openfga_schema(schema)
            except UnsupportedByGraphIndex as e:   # decision-15 scope: nothing to compare
                _assert_recorded_scope_rejection(str(e), f'{kind} probe schema')
                continue
            ttu_grid = [q for q in _grid(ast) if q[3] == 'r1']
            assert ttu_grid, f'{kind}: the grid never queries the TTU relation'
            # One stored-parent candidate per DISTINCT subject shape: driving `folder:f1`
            # and `doc:d1` matters (different types); `doc:d1` vs `doc:d2` does not.
            seen_shapes, parents = set(), []
            for raw in _op_pool(ast):
                if raw[3] == 'parent' and raw[4] == 'doc' and raw[5] == 'd1':
                    if (raw[0], raw[1], raw[2] == '*') not in seen_shapes:
                        seen_shapes.add((raw[0], raw[1], raw[2] == '*'))
                        parents.append(raw)
            assert parents, f'{kind}: no stored-parent candidate to drive'
            # Small subsets, deliberately: a fail-CLOSED divergence is an under-grant, so
            # any extra granting tuple supplies an alternative path and masks it.
            for p in parents:
                subset = (p, base, grant) if negated else (p, grant)
                pe = ParityEngine(schema, paranoia=False, grid_cap=150)
                try:
                    for raw in subset:
                        pe.add_tuple(*raw)
                    driven += 1
                    for q in ttu_grid:
                        pe.check(*q)
                        checked += 1
                except AssertionError as e:
                    key = (kind, 'negated TTU' if negated else 'positive TTU')
                    diverged.setdefault(key, (subset, str(e).split('\n')[0]))
                finally:
                    pe.close()
    # non-vacuity: a sweep that compared nothing reports success.
    assert driven >= 2 * len(_TUPLESET_KINDS), driven
    assert checked > 0, 'the sweep compared nothing'
    assert not diverged, (
        'the generated tupleset grammar DRIVES a backend divergence on '
        f'{sorted(diverged)}:\n' + '\n'.join(
            f'  {k[0]} / {k[1]}: {v[0]}\n     {v[1]}'
            for k, v in sorted(diverged.items())))


_SWEEP_SEEDS = (7, 19, 31)          # the sweeps below are deterministic, not sampled
_SWEEP_N = 60


def _sweep_schema_asts(n=_SWEEP_N, seeds=_SWEEP_SEEDS):
    """``n`` asts per seed from ONE rng per seed (a fresh ``Random(s)`` per draw would
    make every ast in a seed identical -- a sweep that measures one configuration and
    reports a stable rate is the house failure mode wearing an instrument's clothes)."""
    import random
    for s in seeds:
        rng = random.Random(s)
        for _ in range(n):
            yield _schema_ast(_RandomChoices(rng))


def test_schema_asts_draws_the_whole_tupleset_grammar():
    """The DRAW, not just the table: the sweep must realise EVERY body in
    ``_TUPLESET_BODIES``, including a boolean one and a genuine neg-only one. A future
    edit that pins the tupleset back to a single body -- the literal state of the tree
    before 2026-08-10 -- fires here.

    The expected set is DERIVED from ``_TUPLESET_BODIES`` (rank 2 on the durability
    ranking: read the expectation from the source of truth, never hand-maintain it), so
    adding a body without wiring it into the draw is red rather than silently uncovered.

    Sabotage (observed 2026-08-10): restoring
    ``ast = {('doc','parent'): Direct((Restriction('doc','...',False),))}`` in
    ``_schema_ast`` -- the literal pre-2026-08-10 line:
        AssertionError: 180 draws realised only 1 of the 8 tupleset bodies; missing
        ['intersection', 'multitype', 'multitype-wildcard', 'negonly-multitype',
        'negonly-star', 'union', 'wildcard'] -- the TTU tupleset is hardcoded again
    """
    seen = {}
    for ast in _sweep_schema_asts():
        body = ast[('doc', 'parent')]
        for k, v in _TUPLESET_BODIES.items():
            if v == body:
                seen[k] = seen.get(k, 0) + 1
    missing = sorted(set(_TUPLESET_KINDS) - set(seen))
    assert not missing, (
        f'{_SWEEP_N * len(_SWEEP_SEEDS)} draws realised only {len(seen)} of the '
        f'{len(_TUPLESET_KINDS)} tupleset bodies; missing {missing} -- the TTU tupleset '
        f'is hardcoded again')
    assert any(isinstance(_TUPLESET_BODIES[k], (Union, Intersection, Exclusion))
               for k in seen), 'no BOOLEAN tupleset body was drawn'
    assert any(isinstance(_TUPLESET_BODIES[k], Exclusion)
               and (_restriction_types(_TUPLESET_BODIES[k].subtract)
                    - _restriction_types(_TUPLESET_BODIES[k].base))
               for k in seen), 'no NEG-ONLY tupleset body was drawn'


# The floor's provenance: measured 2026-08-10 at this commit -- 172/200 = 86 % of drawn
# schemas compile for the graph index (and 158/180 = 88 % over the deterministic sweep
# below); the rest are the decision-15 "star tupleset over a derived TTU target" family.
# The floor is set well below the measurement so ordinary drift is not flaky, but a
# change that pushes most draws out of the graph fragment (which would make the 4-way
# campaign quietly 3-way, and the graph-only properties quietly filtered) is red.
_SCHEMA_ASTS_FOUR_WAY_FLOOR = 0.60


def test_schema_asts_four_way_rate():
    """★ The generated-schema campaign must stay MOSTLY FOUR-WAY.

    Property: a large majority of ``schema_asts`` draws compile for the graph index, so
    the ParityMachine compares four backends rather than three, and the graph-only
    properties (add/remove restoration, permutation invariance, replay-from-zero) are
    driven rather than filtered by ``_build_in_fragment``'s ``assume(False)``.

    This is the durability-rank-3 instrument the sabotage procedure prescribes: a floor
    with a stated provenance. It is self-contained (it re-draws and re-compiles here)
    precisely so it cannot land in a different ``verify.sh tests-tile`` from the machine
    it is about and then pass over counters that nothing incremented.

    Sabotage (observed 2026-08-10): making every tupleset draw the star-bearing
    ``'negonly-star'`` body -- the plausible "focus the generator on the new shape" edit:
        AssertionError: only 82/180 = 46% of generated schemas compile for the graph
        index (floor 60%); the campaign has drifted into fuzzing 3-way. Reasons:
        ["relation doc#r1: star tupleset [doc:*] on 'parent' derives the wildcard userset
        shape (doc, r0) over the derived relation doc#r0, ...", ...]
    """
    joined, dropped, reasons = 0, 0, []
    for ast in _sweep_schema_asts():
        schema = unparse_schema_ast(ast)
        try:
            parse_openfga_schema(schema)
            joined += 1
        except UnsupportedByGraphIndex as e:
            dropped += 1
            reasons.append(str(e))
            _assert_recorded_scope_rejection(str(e), f'generated schema\n{schema}')
    total = joined + dropped
    assert total == _SWEEP_N * len(_SWEEP_SEEDS)
    rate = joined / total
    assert rate >= _SCHEMA_ASTS_FOUR_WAY_FLOOR, (
        f'only {joined}/{total} = {rate:.0%} of generated schemas compile for the graph '
        f'index (floor {_SCHEMA_ASTS_FOUR_WAY_FLOOR:.0%}); the campaign has drifted into '
        f'fuzzing 3-way. Reasons: {sorted(set(reasons))[:3]}')


# ---------------------------------------------------------------------------
# Parser round-trip on generated schemas
# ---------------------------------------------------------------------------

@given(ast=schema_asts())
def test_parser_round_trip_generated(ast):
    # usersets ON by default now -- fuzzes the unparser/parser round-trip of concrete
    # userset restrictions (G2) alongside everything else.
    assert parse_schema_ast(unparse_schema_ast(ast)) == ast


# ---------------------------------------------------------------------------
# Metamorphic schema pairs (§9): identical tuple sequences, equal grids
# ---------------------------------------------------------------------------

_PAIR_BASE = '''
type user
type doc
  relations
    define a: [user, user:*]
    define b: [user]
    define c: [user]
'''

METAMORPHIC_PAIRS = [
    # A ∖ B  ≡  A ∖ (A ∧ B)
    (_PAIR_BASE + '    define lhs: a but not b\n',
     _PAIR_BASE + '    define lhs: a but not (a and b)\n'),
    # (A ∪ B) ∖ C  ≡  (A ∖ C) ∪ (B ∖ C)
    (_PAIR_BASE + '    define lhs: (a or b) but not c\n',
     _PAIR_BASE + '    define lhs: (a but not c) or (b but not c)\n'),
    # De Morgan over a declared-star base: A ∖ (B ∪ C)  ≡  (A ∖ B) ∧ (A ∖ C)
    (_PAIR_BASE + '    define lhs: a but not (b or c)\n',
     _PAIR_BASE + '    define lhs: (a but not b) and (a but not c)\n'),
]

_PAIR_POOL = sorted(set(
    (('...', 'user', sn, rel, 'doc', on))
    for rel in ('a', 'b', 'c')
    for sn in USERS + ['*']
    for on in DOCS
) - {('...', 'user', '*', 'b', 'doc', 'd1'), ('...', 'user', '*', 'b', 'doc', 'd2'),
     ('...', 'user', '*', 'c', 'doc', 'd1'), ('...', 'user', '*', 'c', 'doc', 'd2')})


@pytest.mark.parametrize('pair', range(len(METAMORPHIC_PAIRS)))
@given(ops=st.lists(st.sampled_from(_PAIR_POOL), min_size=1, max_size=8, unique=True))
def test_metamorphic_pairs(pair, ops):
    left_schema, right_schema = METAMORPHIC_PAIRS[pair]
    left, right = ParityEngine(left_schema), ParityEngine(right_schema)
    try:
        for raw in ops:
            a, b = left.add_tuple(*raw), right.add_tuple(*raw)
            assert a == b, f'accept/reject differs between pair stores on {raw}'
        for sn in USERS + ['ghost', '*']:
            for on in DOCS + ['ghostD']:
                q = ('...', 'user', sn, 'lhs', 'doc', on)
                assert left.check(*q) == right.check(*q), q
    finally:
        left.close()
        right.close()


# ---------------------------------------------------------------------------
# Add-then-remove restores the exact row multiset; permutation invariance;
# replay-from-zero (all on generated schemas, graph backend w/ processor)
# ---------------------------------------------------------------------------

def _residues_by_name(session, widx):
    import json
    from sqlmodel import select
    from index_v4.models import ResidueV1
    out = {}
    for r in session.exec(select(ResidueV1)).all():
        node = widx._node_by_id(r.object_node_id)
        neg = frozenset((n.predicate, n.type, n.name)
                        for n in (widx._node_by_id(i) for i in json.loads(r.neg))
                        if n is not None)
        out[(node.type, node.name, r.relation)] = (r.stars, neg)
    return out


def _state(session, widx):
    return snapshot_rows(session, widx.idx.store_id), _residues_by_name(session, widx)


def _build_in_fragment(schema):
    """``tests.test_processor.build`` for a GENERATED schema, refusing to swallow anything
    but a recorded decision-15 / tupleset-scope rejection.

    These three properties are graph-only (they compare the graph against ITSELF), so
    there is no 3-way fallback: an out-of-fragment draw has to be filtered. Filtering is
    the exact move that hides coverage, so the rejection is first asserted to be a
    recorded family (never a bare compile bug), and
    ``test_schema_asts_four_way_rate`` floors how often the filter may fire."""
    try:
        return build(schema)
    except UnsupportedByGraphIndex as e:
        _assert_recorded_scope_rejection(str(e), f'generated schema\n{schema}')
        assume(False)


@given(ast=schema_asts(), data=st.data())
def test_add_then_remove_restores_row_multiset(ast, data):
    pool = _op_pool(ast)
    assume(pool)
    schema = unparse_schema_ast(ast)
    session, widx, proc, write = _build_in_fragment(schema)
    base = data.draw(st.lists(st.sampled_from(pool), max_size=5, unique=True))
    applied = []
    for raw in base:
        try:
            write('add', raw)
            applied.append(raw)
        except ValueError:
            session.rollback()
    extra = data.draw(st.sampled_from(pool))
    assume(extra not in applied)

    before = _state(session, widx)
    try:
        write('add', extra)
    except ValueError:
        session.rollback()
        assume(False)                      # rejected op: nothing to round-trip
    write('remove', extra)
    assert _state(session, widx) == before
    proc.audit_fixpoint()
    session.close()


@given(ast=schema_asts(), data=st.data())
def test_permutation_invariance(ast, data):
    pool = _op_pool(ast)
    assume(pool)
    ops = data.draw(st.lists(st.sampled_from(pool), min_size=2, max_size=6, unique=True))
    perm = data.draw(st.permutations(ops))
    schema = unparse_schema_ast(ast)

    states = []
    for sequence in (ops, perm):
        session, widx, proc, write = _build_in_fragment(schema)
        rejected = set()
        for raw in sequence:
            try:
                write('add', raw)
            except ValueError:
                session.rollback()
                rejected.add(raw)
        states.append((_state(session, widx), frozenset(rejected)))
        proc.audit_fixpoint()
        session.close()
    # commuting op sets: if both orders accepted the same subset, states must match
    assume(states[0][1] == states[1][1])
    assert states[0][0] == states[1][0]


# Draws include the G2 concrete-userset leaf (usersets ON by default): a derived object node
# can double as a self-referential userset SUBJECT node. That once caused an ANSWER-BENIGN
# single-node implicit-flag drift between the live cascade and the bulk replay-from-zero;
# FIXED 2026-07-17 by the state-functional implicit-flag canonicalization (promote-on-record /
# demote-on-release), so the two builds now converge EXACTLY. Pinned deterministically by
# ``test_pderived_userset_self_ref_cascade_replay_drift`` below.
@given(ast=schema_asts(), data=st.data())
def test_cascade_replay_from_zero(ast, data):
    """Raw leaf writes with NO cascade, then one cascade over the whole outbox,
    equals the live store that cascaded after every op (§9 replay)."""
    pool = _op_pool(ast)
    assume(pool)
    ops = data.draw(st.lists(st.sampled_from(pool), min_size=1, max_size=6, unique=True))
    schema = unparse_schema_ast(ast)

    live_session, live_widx, live_proc, live_write = _build_in_fragment(schema)
    accepted = []
    for raw in ops:
        try:
            live_write('add', raw)
            accepted.append(raw)
        except ValueError:
            live_session.rollback()

    from zanzibar_utils_v1 import Entity, RelationalTriple
    rs = parse_openfga_schema(schema)
    from tests.wildcard_helpers import make_wildcard_index
    bulk_session, bulk_widx = make_wildcard_index(rs.schema_info, store_id='test')
    for raw in accepted:
        sp = Ellipsis if raw[0] == '...' else raw[0]
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        for d in rs.apply(triple):
            bulk_widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                                d.subject.type, d.subject.name,
                                d.relation, d.object.type, d.object.name)
    bulk_proc = DeltaProcessor(bulk_widx, rs.compiled)
    bulk_proc.run_cascade(0)
    bulk_session.commit()
    bulk_proc.audit_fixpoint()

    assert _state(live_session, live_widx) == _state(bulk_session, bulk_widx)
    live_session.close()
    bulk_session.close()


# REGRESSION PIN (2026-07-17): the promote-on-record fix (processor _reconcile step 2d +
# bulk_backfill mirror) makes the implicit flag state-functional, so live cascade and bulk
# replay now converge exactly. Was a strict xfail (deviations 2026-07-17 sub-entry); flipped
# when the fix landed.
def test_pderived_userset_self_ref_cascade_replay_drift():
    """MINIMAL repro of the drift that ``test_cascade_replay_from_zero`` excludes usersets
    to dodge. Schema: a derived ``r0`` (intersection), ``r1`` with a CONCRETE userset over
    r0 (``[doc#r0]``), and a TTU ``r4: r0 from parent``. Writes: a self-referential parent
    ``doc:d1 parent doc:d1`` and the userset tuple ``doc:d1#r0 r1 doc:d1``.

    Node ``(r0, doc, d1)`` is BOTH r0's derived-public node AND the userset subject
    ``doc:d1#r0``. Before the fix, the live cascade's transient r0 edge promoted it to
    ``implicit=False`` ("explicit is sticky", core.py) while bulk replay-from-zero interned
    it fresh at the default ``implicit=True`` -- an answer-benign one-flag canonical drift.
    The promote-on-record fix (both paths now pin every userset-shaped RECORDED subject
    explicit) makes the flag state-functional, so the two builds converge EXACTLY. This
    pins that convergence (state equality below) plus the standing answer-benignity."""
    from zanzibar_utils_v1 import Entity, RelationalTriple
    from tests.wildcard_helpers import make_wildcard_index
    from tests.oracle import Oracle, OracleTuple
    schema = ('type user\n'
              'type doc\n'
              '  relations\n'
              '    define parent: [doc]\n'
              '    define r0: [user] and [user]\n'
              '    define r1: [user] or [doc#r0]\n'
              '    define r4: r0 from parent\n')
    writes = [('...', 'doc', 'd1', 'parent', 'doc', 'd1'),
              ('r0', 'doc', 'd1', 'r1', 'doc', 'd1')]

    live_session, live_widx, live_proc, live_write = build(schema)
    for raw in writes:
        try:
            live_write('add', raw)
        except ValueError:
            live_session.rollback()

    rs = parse_openfga_schema(schema)
    bulk_session, bulk_widx = make_wildcard_index(rs.schema_info, store_id='test')
    for raw in writes:
        sp = Ellipsis if raw[0] == '...' else raw[0]
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        for d in rs.apply(triple):
            bulk_widx.add_tuple('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
                                d.subject.type, d.subject.name,
                                d.relation, d.object.type, d.object.name)
    bulk_proc = DeltaProcessor(bulk_widx, rs.compiled)
    bulk_proc.run_cascade(0)
    bulk_session.commit()
    bulk_proc.audit_fixpoint()

    # ANSWER-BENIGNITY (these hold): every check agrees with the oracle on BOTH builds.
    oracle = Oracle(schema, [OracleTuple(*r) for r in writes])
    grid = _grid({k: None for k in (('doc', 'parent'), ('doc', 'r0'),
                                    ('doc', 'r1'), ('doc', 'r4'))})
    for q in grid:
        assert live_widx.check(*q) == oracle.check(*q)
        assert bulk_widx.check(*q) == oracle.check(*q)

    # Canonical STATE now converges exactly (the fix: promote-on-record).
    try:
        assert _state(live_session, live_widx) == _state(bulk_session, bulk_widx)
    finally:
        live_session.close()
        bulk_session.close()


# ---------------------------------------------------------------------------
# Cyclic boolean schemas are refused at compile (§9)
# ---------------------------------------------------------------------------

_CYCLIC_SCHEMAS = [
    '''
type user
type doc
  relations
    define parent: [doc]
    define blocked: [user]
    define viewer: ([user] or viewer from parent) but not blocked
''',
    '''
type user
type doc
  relations
    define b: [user]
    define x: y but not b
    define y: x or [user]
''',
]


@pytest.mark.parametrize('schema', _CYCLIC_SCHEMAS)
def test_cyclic_boolean_schema_refused(schema):
    with pytest.raises(ValueError, match='cycle'):
        parse_openfga_schema(schema)


# ---------------------------------------------------------------------------
# Boundary generators (§9): self-referential wildcard tuples, both orientations
# ---------------------------------------------------------------------------

_WC_SCHEMA = '''
type user
type group
  relations
    define member: [user, group#member, group:*#member]
'''


def test_self_referential_wildcard_rejected_with_parity_and_i12():
    """`group:*#member member group:g` closes the w_any bridge loop: both live
    engines must reject identically and leave their rows untouched (I12)."""
    pe = ParityEngine(_WC_SCHEMA)
    pe.add_tuple('...', 'user', 'u1', 'member', 'group', 'g1')
    accepted = pe.add_tuple('member', 'group', '*', 'member', 'group', 'g1')
    assert accepted is False, 'the self-referential wildcard tuple must be rejected'
    assert pe.check('...', 'user', 'u1', 'member', 'group', 'g1') is True
    pe.close()


def test_object_star_self_containment_accepted():
    """`folder:X contains folder:*` (X contains itself) is representable and true,
    with no cycle -- subject-role and object-role are different nodes (§7)."""
    schema = '''
type folder
  relations
    define contains: [folder]
'''
    pe = ParityEngine(schema, object_wildcard_shapes=frozenset({('folder', 'contains')}))
    assert pe.add_tuple('...', 'folder', 'x', 'contains', 'folder', '*') is True
    assert pe.check('...', 'folder', 'x', 'contains', 'folder', 'x') is True
    pe.close()


# ---------------------------------------------------------------------------
# Item 4 (deviations 2026-07-17): targeted deterministic pins, independent of the
# generators, for two paths the blind-spot audit flagged.
# ---------------------------------------------------------------------------

def test_owc_propagates_through_computed_hop():
    """Item 4a: an object-wildcard shape declared on ``w`` propagates through the Computed
    rewrite ``v: w`` onto ``(doc, v)`` -- the type-agnostic wildcard-relation branch of
    ``_expand_object_wildcard_shapes`` the audit flagged. Verified empirically and pinned:
    expansion adds ``(doc, v)`` to ``object_wildcard_shapes``, and an object-star write on
    the SOURCE shape ``w`` (whose rewrite lands a star-object tuple on ``v``) is accepted
    UNANIMOUSLY across backends, with the wildcard grant flowing through ``v: w`` (check
    True on all). It does NOT land in the doubly-bridged intersection -- ``v`` is Computed,
    so there is no writable ``doc:*#v`` restriction -- so it compiles rather than rejecting
    (contrast the reg12 doubly-bridged rejections)."""
    schema = ('type user\n'
              'type doc\n'
              '  relations\n'
              '    define w: [user, doc]\n'
              '    define v: w\n')
    owc = frozenset({('doc', 'w')})
    rs = parse_openfga_schema(schema, object_wildcard_shapes=owc)
    assert ('doc', 'v') in rs.schema_info.object_wildcard_shapes, \
        'expansion must propagate the OWC shape through the Computed hop onto (doc, v)'
    pe = ParityEngine(schema, object_wildcard_shapes=owc, grid_cap=150)
    try:
        # object-star on the source shape w (accept/reject unanimity asserted internally)
        assert pe.add_tuple('...', 'doc', 'y', 'w', 'doc', '*') is True
        # the wildcard grant flows through v: w onto an arbitrary object (check unanimity)
        assert pe.check('...', 'doc', 'y', 'v', 'doc', 'q') is True
        assert pe.check('...', 'doc', 'y', 'w', 'doc', 'q') is True
        for side in pe.set_sides:
            assert side.se._ghost_hop_fired is False
    finally:
        pe.close()


def test_pderived_userset_add_remove_deterministic_pin():
    """Item 4b: a handwritten boolean schema with a CONCRETE userset ``[doc#p]`` where
    ``p`` is TAINTED (``p: editor but not blocked``). Adding then removing the userset
    tuple ``doc:d1#p q doc:d2`` restores the EXACT row multiset (residues included), the
    grid answers match the oracle while it is present (userset subject and lifted-member
    queries included), and ``audit_fixpoint`` (I9) holds. Drives the PDerivedUserset
    ``upos`` / ``_find_leaf_node`` reconcile path deterministically -- the path with two
    historical CRITICAL bugs found by review not fuzzing (deviations 2026-07-08 D2;
    2026-07-08 review-2 #1)."""
    from tests.oracle import Oracle, OracleTuple
    schema = ('type user\n'
              'type doc\n'
              '  relations\n'
              '    define blocked: [user]\n'
              '    define editor: [user]\n'
              '    define p: editor but not blocked\n'
              '    define q: [user, doc#p]\n')
    session, widx, proc, write = build(schema)
    write('add', ('...', 'user', 'u1', 'editor', 'doc', 'd1'))    # d1 is a p-member via editor
    before = _state(session, widx)

    write('add', ('p', 'doc', 'd1', 'q', 'doc', 'd2'))            # userset: doc:d1#p is q of d2
    present = [('...', 'user', 'u1', 'editor', 'doc', 'd1'),
               ('p', 'doc', 'd1', 'q', 'doc', 'd2')]
    oracle = Oracle(schema, [OracleTuple(*r) for r in present])
    ast_keys = {('doc', r): None for r in ('blocked', 'editor', 'p', 'q')}
    grid = _grid(ast_keys) + [
        ('p', 'doc', 'd1', 'q', 'doc', 'd2'),                     # userset subject IS a q-member
        ('...', 'user', 'u1', 'q', 'doc', 'd2'),                  # lifted member of the userset
    ]
    for query in grid:
        assert widx.check(*query) == oracle.check(*query), query
    proc.audit_fixpoint()                                          # I9 while present

    write('remove', ('p', 'doc', 'd1', 'q', 'doc', 'd2'))
    assert _state(session, widx) == before, 'add/remove of the userset tuple must restore state'
    proc.audit_fixpoint()                                          # I9 after
    session.close()


def test_graph_remove_node_invariants_and_answers():
    """Item 5 (G5, deviations 2026-07-17): ``WildcardIndex.remove_node`` on a live node --
    the surface with the CRITICAL neighbour-refcount bug (I13, deviations 2026-07-08). The
    set engine has NO node-level removal, so remove_node cannot fan out through ParityEngine
    (no cross-backend equivalent); it is pinned here on the graph surface that exists.
    Removing a pure-subject node (``user:u2``) must (a) keep all wildcard invariants I1-I13
    incl. the refcount==direct-degree check, and (b) leave the check grid equal to an oracle
    rebuilt over exactly the raw tuples NOT incident to the removed node (remove_node ==
    dropping every incident tuple, for a subject-only node)."""
    from tests.parity import _GraphSide
    from tests.wildcard_helpers import assert_wildcard_invariants
    from tests.oracle import Oracle, OracleTuple
    schema = ('type user\n'
              'type group\n'
              '  relations\n'
              '    define member: [user, group#member, group:*#member]\n')
    rs = parse_openfga_schema(schema)
    gs = _GraphSide(rs, paranoia=True)
    tuples = [('...', 'user', 'u1', 'member', 'group', 'g1'),
              ('...', 'user', 'u2', 'member', 'group', 'g1'),
              ('member', 'group', 'g1', 'member', 'group', 'g2')]
    try:
        for t in tuples:
            assert gs.apply(t, 'add') is True
        gs.widx.remove_node('...', 'user', 'u2')
        gs.session.commit()
        assert_wildcard_invariants(gs.widx)                       # I1..I13 (incl. refcount)
        remaining = [t for t in tuples
                     if not (t[0] == '...' and t[1] == 'user' and t[2] == 'u2')]
        oracle = Oracle(schema, [OracleTuple(*r) for r in remaining])
        for u in ('u1', 'u2'):
            for g in ('g1', 'g2'):
                q = ('...', 'user', u, 'member', 'group', g)
                assert gs.widx.check(*q) == oracle.check(*q), q
    finally:
        gs.close()


# ---------------------------------------------------------------------------
# Stateful: weighted ops against a ParityEngine over a generated schema (§9)
# ---------------------------------------------------------------------------

class ParityMachine(RuleBasedStateMachine):
    """Every accepted op already runs 4-way unanimity, I12, full-grid oracle parity,
    per-commit paranoia (I1-I7, I10, §8.3), and the graph's I9 audit -- the rules
    just drive the walk.

    Draws include the G2 concrete-userset leaf (usersets ON by default; deviations
    2026-07-17). ParityEngine's grid derives subjects from Direct restrictions, so the
    `[doc#r_k]` leaf makes it CHECK userset-shaped subjects (`doc:X#r_k`) against every
    derived relation -- the X4/D2/upos userset-subject-through-derived family. Those graph
    ★ 2026-08-10: the tupleset of every generated TTU is now DRAWN (item (c)), not pinned
    to ``parent: [doc]``. That change alone makes this machine find a live divergence it
    could not previously express at ANY budget -- observed at ``--hypothesis-seed=53``,
    ``ci`` profile, on a ONE-write walk:

        AssertionError: check parity broken after add ('...','doc','d1','parent','doc','d1'):
            q=('r0','doc','d1','r1','doc','d1') graph=False oracle=True
        state.setup(ast={('doc','parent'): Exclusion(Direct([folder]), Direct([doc])),
                         ('doc','r0'): Direct([user]),
                         ('doc','r1'): Union((TTU('r0','parent'), Direct([doc#r0]))),
                         ('folder','r0'): Direct([user])})

    That schema is RC1's shape ASSEMBLED BY THE GENERATOR, not transcribed from the bug
    report. Seeds 7/19/31/71 do not reach it and 53/97 do, so the stateful machine alone
    is a sample; ``test_every_tupleset_kind_is_driven_against_the_oracle`` is the
    deterministic version of the same claim.

    completeness gaps are now FIXED (the `processor._leaf_concretes` upos lift) and pinned:
    ``test_lookup_oracle.py::test_graph_from_chain_userset_through_boolean_ttu_arm``,
    ``::test_graph_userset_subject_through_derived_wildcard_gap``, and
    ``::test_graph_userset_member_through_granted_userset_over_derived``. The PDerivedUserset
    reconcile WRITE path is additionally covered deterministically by
    ``test_pderived_userset_add_remove_deterministic_pin``."""

    @initialize(ast=schema_asts())
    def setup(self, ast):
        self.ast = ast
        self.pool = _op_pool(ast)
        self.grid = _grid(ast)
        self.pe = ParityEngine(unparse_schema_ast(ast), grid_cap=150)
        # A drawn tupleset (item (c)) can cross a star restriction with a derived TTU
        # target, which is a decision-15 scope rejection -- ParityEngine then sets
        # graph=None and this machine would fuzz 3-way SILENTLY. Measured 2026-08-10:
        # 28/200 draws (14 %). The drop is allowed, but only as a recorded scope family,
        # and `test_schema_asts_four_way_rate` floors how often it may happen.
        if self.pe.graph is None:
            _assert_recorded_scope_rejection(
                self.pe.graph_drop_reason,
                f'generated schema\n{unparse_schema_ast(ast)}')
        self.live: list = []

    @rule(data=st.data())
    def add(self, data):
        if not self.pool:
            return
        raw = data.draw(st.sampled_from(self.pool))
        if self.pe.add_tuple(*raw):
            self.live.append(raw)

    @rule(data=st.data())
    def remove(self, data):
        if not self.live:
            return
        raw = data.draw(st.sampled_from(sorted(set(self.live))))
        if self.pe.remove_tuple(*raw):
            self.live.remove(raw)

    @rule(data=st.data())
    def check(self, data):
        if self.grid:
            self.pe.check(*data.draw(st.sampled_from(self.grid)))

    def teardown(self):
        if hasattr(self, 'pe'):
            self.pe.close()


TestParityMachine = ParityMachine.TestCase


# ---------------------------------------------------------------------------
# Star-bridge shape class (regressions reg9/reg10/reg11; deviations 2026-07-16).
#
# The multi-hop star-bridge accept/reject divergence (set engine accepted a
# bridge-mediated cycle the graph rejects) hid from the fuzzer because the stock
# ``schema_asts`` generator CANNOT build the shape: it emits only user-typed Direct
# leaves over a single ``doc`` type -- no same-type star tupleset parent and no
# wildcard-userset-over-shape. This dedicated generator emits the whole class --
#     define parent: [T, T:*]                 # star tupleset parent (in/out bridge feeder)
#     define A: [user, T:*#A, T#B]            # self-referential wildcard userset over A
#     define B: [user] or A from parent       # a TTU routing back into the shape
# -- and fuzzes the write-time cycle-admission surface where the bug lived, driven
# through a ParityEngine whose per-op accept/reject-parity assertion (parity.py) is
# exactly what fires on a bridge divergence. Verified during authoring: blinding the
# set engine's bridge awareness (``_flow_reaches`` -> no bridges) makes both the
# deterministic pin and this machine reproduce the reg10 disagreement.
#
# The candidate pool is schema-VALID by construction (subjects match a declared type
# restriction) -- like every other corpus here. This is deliberate: the graph backend
# admits a restriction-invalid tuple as a silent no-op (empty rewrite fan-out) while the
# set engine strictly rejects it, a long-standing by-design admission asymmetry the
# corpora avoid; feeding invalid tuples would trip accept/reject parity on that unrelated
# axis rather than on the bridge shape under test.
# ---------------------------------------------------------------------------

_SB_TYPES = ['folder', 'doc']
_SB_RELS = ['admin', 'viewer', 'editor', 'owner']
_SB_OBJS = ['x', 'y']
_SB_USERS = ['u1']


def _star_bridge_schema(T: str, A: str, B: str) -> str:
    """The star-bridge template. ``A == B`` selects the SELF-REFERENTIAL TTU variant.

    ZT-P5-NEW (2026-07-26) -- the generator blind spot this closes. The two-relation
    form below can never express a TTU whose head and TARGET are the same relation
    (``B: … or A from parent`` with ``A != B``), which is precondition (ii) of the
    2026-07-26 accept/reject divergence + detonation; the other precondition (an
    object wildcard on the star-restricted tupleset shape) the generator already drew.
    Their CONJUNCTION was generated by nothing in ``tests/`` or ``formal/conformance/``,
    which is why a live bug survived every fuzz sweep.

    The self-referential arm deliberately DROPS the literal ``T:*#A`` wildcard-userset
    restriction. Keeping it would make ``(T, A)`` doubly bridged the moment
    ``(T,'parent')`` is object-wildcarded, so ``compile_ruleset`` would reject the
    schema (``DoublyBridgedShapeError``) and the machine would skip every
    self-referential config -- i.e. the blind spot would stay open under a new name.
    Without it the shape is exactly reg11 / ``owc_star_ttu``: legal, compilable, and
    the one that carries the write-level latent cycle."""
    if A == B:
        return (f'type user\n'
                f'type {T}\n'
                f'  relations\n'
                f'    define parent: [{T}, {T}:*]\n'
                f'    define {A}: [user, {T}#{A}] or {A} from parent\n')
    return (f'type user\n'
            f'type {T}\n'
            f'  relations\n'
            f'    define parent: [{T}, {T}:*]\n'
            f'    define {A}: [user, {T}:*#{A}, {T}#{B}]\n'
            f'    define {B}: [user] or {A} from parent\n')


def _star_bridge_pool(T, A, B, owc):
    """Schema-VALID raw tuples for the star-bridge schema (subject matches a declared
    restriction). Covers the reg9/reg10/reg11 admission instances:
      * ``T:* parent T:x``         -- subject-star parent (reg9/reg10 in-bridge feeder)
      * ``T:x parent T:*``         -- object-star parent (reg11 out-bridge feeder), valid
                                      only when (T,'parent') is an object-wildcard shape
      * ``T:x#B  A  T:y``          -- the userset grant that closes the reg10 cycle
      * ``T:*#A  A  T:y``          -- the self-referential wildcard userset (reg9 family)
    plus direct user grants and, per declared object-wildcard shape, the T:* object
    variants (extra out-bridge coverage)."""
    out = set()

    def objects_for(rel):
        objs = [(T, o) for o in _SB_OBJS]
        if (T, rel) in owc:
            objs.append((T, '*'))
        return objs

    for (ot, on) in objects_for('parent'):          # parent: [T, T:*]
        for x in _SB_OBJS:
            out.add(('...', T, x, 'parent', ot, on))
        out.add(('...', T, '*', 'parent', ot, on))
    for (ot, on) in objects_for(A):                  # A: [user, T:*#A, T#B]
        for u in _SB_USERS:
            out.add(('...', 'user', u, A, ot, on))
        if A != B:
            # the literal T:*#A restriction exists only in the A != B template
            # (_star_bridge_schema); emitting it for the self-referential variant
            # would put a restriction-INVALID tuple in a pool that is schema-valid
            # by construction (see the docstring's admission-asymmetry note).
            out.add((A, T, '*', A, ot, on))          # T:*#A  (self-ref wildcard userset)
        for x in _SB_OBJS:
            out.add((B, T, x, A, ot, on))            # T:x#B  (routes via the TTU)
    for (ot, on) in objects_for(B):                  # B: [user] (the "A from parent" arm is a rule)
        for u in _SB_USERS:
            out.add(('...', 'user', u, B, ot, on))
    return sorted(out)


@st.composite
def star_bridge_configs(draw):
    """A star-bridge schema (T, A/B, possibly EQUAL) + a drawn object-wildcard-shape
    subset + the matching valid-tuple pool. Non-doubly-bridged configs keep the graph
    4-way (asserted in the machine's setup), so a graph/set admission divergence is
    actually compared; doubly-bridged configs are asserted rejected on both backends
    and skipped.

    ZT-P5-NEW (2026-07-26): ``B`` is drawn from the FULL relation set, so ~1 draw in 4
    yields ``A == B`` -- the SELF-REFERENTIAL TTU (``A: … or A from parent``) that the
    old ``B != A`` draw made unreachable. Crossed with the ``(T,'parent')`` object
    wildcard the domain below already offered, that is precisely the conjunction which
    hid a live accept/reject divergence + graph detonation from every previous sweep
    (see ``_star_bridge_schema`` and tests/test_zt_p5_readjudication.py)."""
    T = draw(st.sampled_from(_SB_TYPES))
    A = draw(st.sampled_from(_SB_RELS))
    B = draw(st.sampled_from(_SB_RELS))
    # Object-wildcard shapes are drawn over ``parent`` (out-bridge feeder, reg11), ``B``
    # (the TTU target -- its w_all node gets the out-bridge) AND ``A`` (deviations
    # 2026-07-17: this is the previously-excluded F1/F2 axis). ``A`` carries the literal
    # ``T:*#A`` wildcard-userset restriction, so an object wildcard on it makes ``(T, A)``
    # a DOUBLY-BRIDGED shape -- which the compiler now rejects with
    # ``DoublyBridgedShapeError`` on BOTH backends (the third decision-15 scope rejection).
    # The machine's setup asserts that consistent rejection and skips such a config; all
    # other configs proceed exactly as before. Widening the domain here fuzzes the F1/F2
    # boundary that the previous ``{parent, B}``-only domain left uncovered.
    owc_domain = sorted({(T, 'parent'), (T, A), (T, B)})   # A == B collapses to 2
    owc = frozenset(draw(st.sets(st.sampled_from(owc_domain),
                                 max_size=len(owc_domain))))
    return _star_bridge_schema(T, A, B), owc, _star_bridge_pool(T, A, B, owc)


# ---------------------------------------------------------------------------
# Shared helpers for the star-bridge machines (deviations 2026-07-17):
#   * doubly-bridged configs must reject identically on both backends;
#   * a check grid derived from the config's own valid-tuple pool (D4/G1);
#   * a ParityEngine builder that skips (after asserting rejection) doubly-bridged
#     configs and otherwise returns a live engine.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# The graph-drop CONTRACT (2026-08-10).
#
# `ParityEngine` degrades to 3-way (oracle + both set engines) whenever the graph index
# refuses a schema, and it does so SILENTLY -- which is how `BoolStarBridgeParityMachine`
# ran 269 of 400 boolean draws with no graph index at all and reported green. Every
# generator in this file now either promises 4-way and asserts it, or declares the draw
# out-of-fragment and asserts the drop is one of the recorded decision-15 / tupleset-scope
# families below. An UNRECOGNISED refusal is a regression, not a smaller matrix.
#
# The substrings are the compiler's own message families, kept short so a reworded
# message still matches while a NEW rejection class does not.
# ---------------------------------------------------------------------------

_SCOPE_REJECTION_FAMILIES = (
    'star tupleset',                    # star tupleset over a derived TTU target
    'wildcard userset restriction',     # [T:*#r] over a derived relation
    'object-wildcard shape',            # decision-15: OWC touching a derived relation
    'tupleset ',                        # tupleset scope (userset / rewritten arms)
    'cycle',                            # CyclicDerivedDependency
)


def _assert_recorded_scope_rejection(reason: str, context: str) -> None:
    """A graph drop is acceptable ONLY as one of the recorded scope families."""
    assert reason, f'{context}: graph dropped with no recorded reason'
    assert any(f in reason for f in _SCOPE_REJECTION_FAMILIES), (
        f'{context}: the graph index refused this schema with an UNRECOGNISED reason, so '
        f'the matrix silently shrank to 3-way instead of comparing anything: {reason}')


def _assert_doubly_bridged_rejected(schema, owc):
    """A doubly-bridged config must raise ``DoublyBridgedShapeError`` at CONSTRUCTION on
    BOTH backends -- the state is unconstructible everywhere (deviations 2026-07-17), so
    graph and set engine reject identically rather than one degrading."""
    with pytest.raises(DoublyBridgedShapeError):
        parse_openfga_schema(schema, object_wildcard_shapes=owc)
    with pytest.raises(DoublyBridgedShapeError):
        SetEngine(_fresh_session(), 'w', schema, object_wildcard_shapes=owc)


def _parity_or_skip_doubly_bridged(schema, owc, *, grid_cap=150):
    """Build a ParityEngine for a star-bridge config. If the config is doubly-bridged,
    ParityEngine construction re-raises ``DoublyBridgedShapeError`` (the set side refuses
    it -- parity.py); assert BOTH backends reject and return None so the machine skips."""
    try:
        return ParityEngine(schema, object_wildcard_shapes=owc, grid_cap=grid_cap)
    except DoublyBridgedShapeError:
        _assert_doubly_bridged_rejected(schema, owc)
        return None


def _sb_grid(pool, extra_rels=()):
    """A check grid drawn from the config's OWN pool: subjects (+ ghost/'*') x relations
    x objects (+ ghost). ParityEngine.check asserts cross-backend equality per query.

    ``extra_rels`` carries relations that appear in NO pool tuple because they have no
    Direct arm (the downstream boolean ``C``). Without it the pool-derived relation list
    silently omits exactly the relation the config exists to exercise."""
    subjects = sorted({(t[0], t[1], t[2]) for t in pool}
                      | {('...', 'user', 'ghost'), ('...', 'user', '*')})
    otypes = sorted({t[4] for t in pool})
    objects = sorted({(t[4], t[5]) for t in pool} | {(ot, 'ghostO') for ot in otypes})
    rels = sorted({t[3] for t in pool} | set(extra_rels))
    return [(sp, s_t, sn, rel, ot, on)
            for (sp, s_t, sn) in subjects for rel in rels for (ot, on) in objects]


def test_star_bridge_class_deterministic_pin():
    """Deterministic guard that the star-bridge class stays closed regardless of
    hypothesis sampling: apply the whole valid pool for the canonical reg10 config
    (folder/admin/viewer, all three object-wildcard shapes) through a ParityEngine.
    The pool contains the reg9/reg10/reg11 instances; ParityEngine asserts accept/reject
    + full-grid parity on every op, and the sequence includes real bridge REJECTIONS (so
    the bridge branch is exercised, not merely bypassed). Authoring check: blinding the
    set engine's bridge awareness makes this fire the reg10 accept/reject disagreement."""
    T, A, B = 'folder', 'admin', 'viewer'
    owc = frozenset({(T, 'parent'), (T, B)})   # in-bridge (parent star) + out-bridge (B's w_all)
    pool = _star_bridge_pool(T, A, B, owc)
    pe = ParityEngine(_star_bridge_schema(T, A, B), object_wildcard_shapes=owc, grid_cap=150)
    assert pe.graph is not None, 'star-bridge schema must stay 4-way (graph must join)'
    try:
        decisions = [pe.add_tuple(*t) for t in pool]
    finally:
        pe.close()
    assert any(decisions) and not all(decisions), (
        'expected the pool to exercise BOTH accepts and bridge-cycle rejections; '
        f'got {sum(decisions)}/{len(decisions)} accepted')


def test_star_bridge_self_referential_ttu_deterministic_pin():
    """ZT-P5-NEW (2026-07-26): the SELF-REFERENTIAL star-bridge config, pinned
    deterministically so the class is covered regardless of hypothesis sampling.

    ``A == B`` gives ``A: [user, T#A] or A from parent`` over a star-restricted
    ``parent`` whose shape is object-wildcarded -- the exact conjunction the old
    ``B != A`` draw made ungeneratable, and the one under which the graph used to
    ACCEPT ``T:* parent T:*`` (routing ``w_any(T,A) -> w_all(T,A)``) while the set
    engine rejected it, then permanently locked itself out of every later concrete
    ``A`` grant. ParityEngine asserts accept/reject unanimity + full-grid oracle
    parity + paranoia on EVERY op, so a regression fires here, not three sweeps later.
    """
    T, A = 'folder', 'admin'
    owc = frozenset({(T, 'parent')})
    schema = _star_bridge_schema(T, A, A)
    assert f'or {A} from parent' in schema and f'{T}:*#{A}' not in schema, schema
    pool = _star_bridge_pool(T, A, A, owc)
    star_star = ('...', T, '*', 'parent', T, '*')
    assert star_star in pool, 'the pool must still contain the dangerous write'
    pe = _parity_or_skip_doubly_bridged(schema, owc)
    assert pe is not None, (
        'the self-referential config must COMPILE -- if it starts raising '
        'DoublyBridgedShapeError the blind spot has reopened under a new name')
    try:
        assert pe.add_tuple(*star_star) is False, (
            'the same-shape w_any -> w_all write must be rejected unanimously')
        decisions = [pe.add_tuple(*t) for t in pool]
        for side in pe.set_sides:
            assert side.se._ghost_hop_fired is False
    finally:
        pe.close()
    assert any(decisions), f'pool exercised no accepted ops (0/{len(decisions)})'


class StarBridgeParityMachine(RuleBasedStateMachine):
    """Weighted add/remove/check/rebuild ops over a GENERATED star-bridge schema, driven
    through a ParityEngine (4-way: graph + both set engines + oracle). Every accepted op
    runs unanimity + I12 + full-grid oracle parity + paranoia inside the engine; the point
    here is the ADMISSION sequence -- order-dependent bridge cycles (reg10 is W1-then-W2)
    only surface when writes interleave, which the stock ParityMachine can't build.

    Doubly-bridged configs (OWC over ``(T, A)``, the F1/F2 axis) are asserted rejected on
    both backends at construction and then skipped (deviations 2026-07-17). The set-engine
    ghost-hop safeguard is asserted never-fired in teardown (it is unreachable for any
    constructible engine)."""

    @initialize(cfg=star_bridge_configs())
    def setup(self, cfg):
        schema, owc, pool = cfg
        self.pool = pool
        self.pe = _parity_or_skip_doubly_bridged(schema, owc)
        if self.pe is None:
            return                              # doubly-bridged: rejected + skipped
        # 4-way is the invariant that makes this catch graph/set divergences; a legal
        # star-bridge config is pure-union, so if the graph ever drops here, fail loudly
        # rather than fuzz 3-way blind.
        assert self.pe.graph is not None, 'legal star-bridge schema unexpectedly dropped the graph'
        self.grid = _sb_grid(pool)
        self.live: list = []

    @rule(data=st.data())
    def add(self, data):
        if self.pe is None:
            return
        raw = data.draw(st.sampled_from(self.pool))
        if self.pe.add_tuple(*raw):
            self.live.append(raw)

    @rule(data=st.data())
    def remove(self, data):
        if self.pe is None or not self.live:
            return
        raw = data.draw(st.sampled_from(sorted(set(self.live))))
        if self.pe.remove_tuple(*raw):
            self.live.remove(raw)

    @rule(data=st.data())
    def check(self, data):
        """D4 (deviations 2026-07-17): an explicit check rule. The machine relied on
        ParityEngine's post-write grid parity, which SAMPLES the grid (cap 150); a drawn
        check asserts cross-backend equality on a query of the harness's choosing."""
        if self.pe is None:
            return
        self.pe.check(*data.draw(st.sampled_from(self.grid)))

    @rule(data=st.data())
    def rebuild_sets(self, data):
        """G5 (deviations 2026-07-17): rebuild each set engine from its TupleV1 log
        (spec §6.5 replay) and assert the check grid is unchanged. Low frequency."""
        if self.pe is None or data.draw(st.integers(min_value=0, max_value=3)) != 0:
            return
        qs = data.draw(st.lists(st.sampled_from(self.grid), min_size=1, max_size=6,
                                unique=True))
        for side in self.pe.set_sides:
            before = [side.se.check(*q) for q in qs]
            side.se.rebuild()
            assert [side.se.check(*q) for q in qs] == before, \
                f'{side.name} check grid changed after rebuild'

    def teardown(self):
        pe = getattr(self, 'pe', None)
        if pe is not None:
            for side in pe.set_sides:
                assert side.se._ghost_hop_fired is False, \
                    'set-engine ghost hop fired on a constructible star-bridge schema'
            pe.close()


TestStarBridgeParityMachine = StarBridgeParityMachine.TestCase


# ---------------------------------------------------------------------------
# G1 (deviations 2026-07-17): booleans x star-bridge. The audit's headline blind
# spot -- ``schema_asts`` fuzzes booleans but only bare user subjects, while
# ``star_bridge_configs`` fuzzes wildcards/usersets/bridges but is provably pure-union.
# Their PRODUCT (where every historical bug lived) was covered only by handwritten pins.
# This generator crosses the star-bridge template with a boolean arm on ``B``:
#     define parent: [T, T:*]
#     define blk:    [user]
#     define A:      [user, T:*#A, T#B]                     # self-ref wildcard userset
#     define B:      ([user] or A from parent) but not blk # boolean over the bridge target
# plus a drawn OWC subset that MAY hit the doubly-bridged ``(T, A)`` intersection. A draw
# that compiles runs a ParityEngine (3-way when a boolean B drops the graph via owc-on-
# derived, else 4-way); a draw that rejects is asserted consistent per each backend's
# contract (DoublyBridgedShapeError on BOTH; other scope rejections: graph drops / set
# degrades -- exactly ParityEngine's own behavior, reused here rather than reinvented).
# ---------------------------------------------------------------------------

_BOOL_B_OPS = ['but not', 'and', 'or']     # 'or' keeps B pure-union (graph stays 4-way)

# --- WHERE THE BOOLEAN ARM SITS, and why it is now drawn ------------------- #
# ★★ MEASURED 2026-08-10, and it is worse than the 12 % the design doc recorded.
# Enumerating the ENTIRE old config space (2 types x 24 relation permutations x 3 ops x
# every OWC subset = 1536 configs, compile-only) gives:
#
#     UNSUP 768 / OK 384 / DOUBLY 384
#     ... and every one of the 768 UNSUP configs is `b_op in ('and', 'but not')`,
#         i.e. EVERY boolean config, for EVERY object-wildcard subset including the
#         empty one.
#
# and sampling the strategy the way hypothesis does (400 draws, seed 0) gives
#
#     ('boolean',    '3-way') 269      ('pure-union', '4-way') 51
#     ('pure-union', 'SKIP')   80      4-way draws that are BOOLEAN: 0
#
# So the machine whose docstring calls itself "booleans x star-bridge -- the audit's
# headline blind spot" had run the graph index on ZERO boolean draws, ever. Its 13 %
# 4-way draws are exactly the `or` ones, where there is no boolean at all. Because
# `ParityEngine` sets `graph = None` on a scope rejection, all 269 boolean draws fuzzed
# 3-way -- oracle + two set engines -- and reported green.
#
# The cause is structural, not a sampling accident. With the boolean ON THE BRIDGE TARGET
# (`B: (...) but not blk`), `B` is derived, `A`'s `[T#B]` restriction taints `A` too, and
# the star tupleset `[T:*]` on `parent` then derives a wildcard userset over a derived
# relation -- a decision-15 scope rejection that no OWC choice can avoid:
#     "relation T#B: star tupleset [T:*] on 'parent' derives the wildcard userset shape
#      (T, A) over the derived relation T#A, which needs symbolic composition through
#      residues"
# Adding `assert self.pe.graph is not None` (its sibling machine's guard) would therefore
# have turned 67 % of draws RED, which is why the honest fix is a GRAMMAR change and not
# an assertion: draw WHERE the boolean sits.
#
#   'target'     -- today's template. `B` itself is boolean. PROVABLY out of the graph
#                   fragment for every non-`or` op (768/768 above), so it is drawn only in
#                   the deliberate scope-boundary stratum, where the REJECTION is the
#                   asserted contract.
#   'downstream' -- `B` stays pure-union (the bridge, the star tupleset and the wildcard
#                   usersets all survive) and a FOURTH relation carries the boolean over
#                   it: `C: B <op> blk`. Measured in-fragment for every op at owc = {}
#                   (144/144 configs; see test_bool_star_bridge_in_fragment_stratum_is_
#                   exhaustively_four_way, which re-derives that exhaustively at run time).
#                   This is the boolean x star-bridge cross the machine claimed to fuzz.
#
# Honest limit, measured and NOT papered over: an object wildcard cannot coexist with a
# boolean here at all -- `_expand_object_wildcard_shapes` propagates any OWC on
# parent/A/B/blk onto the derived `C`'s leaf predicates, which decision-15 refuses. So an
# in-fragment boolean draw carries `owc = frozenset()` BY CONSTRUCTION. That is a real
# scope boundary of the backend, not a generator choice, and the boundary stratum is what
# keeps asserting it.
_BOOL_ARM_PLACEMENTS = ['target', 'downstream']


def _bool_star_bridge_schema(T, A, B, blk, b_op, C=None) -> str:
    """The boolean x star-bridge template. ``C`` selects the placement: ``None`` puts the
    boolean arm on the bridge TARGET ``B`` (the pre-2026-08-10 template, out of the graph
    fragment for every non-``or`` op); a relation name puts it DOWNSTREAM of a pure-union
    ``B``, which keeps the whole bridge shape and stays 4-way."""
    if C is not None:
        return (f'type user\n'
                f'type {T}\n'
                f'  relations\n'
                f'    define parent: [{T}, {T}:*]\n'
                f'    define {blk}: [user]\n'
                f'    define {A}: [user, {T}:*#{A}, {T}#{B}]\n'
                f'    define {B}: [user] or {A} from parent\n'
                f'    define {C}: {B} {b_op} {blk}\n')
    if b_op == 'or':
        bdef = f'[user] or {A} from parent'
    else:
        bdef = f'([user] or {A} from parent) {b_op} {blk}'
    return (f'type user\n'
            f'type {T}\n'
            f'  relations\n'
            f'    define parent: [{T}, {T}:*]\n'
            f'    define {blk}: [user]\n'
            f'    define {A}: [user, {T}:*#{A}, {T}#{B}]\n'
            f'    define {B}: {bdef}\n')


def _bool_star_bridge_pool(T, A, B, blk, owc):
    """The star-bridge pool (parent/A/B) plus ``blk`` user grants (incl. the object-star
    variant when ``(T, blk)`` is an object-wildcard shape)."""
    out = set(_star_bridge_pool(T, A, B, owc))
    blk_objs = [(T, o) for o in _SB_OBJS]
    if (T, blk) in owc:
        blk_objs.append((T, '*'))
    for u in _SB_USERS:
        for (ot, on) in blk_objs:
            out.add(('...', 'user', u, blk, ot, on))
    return sorted(out)


def _bool_star_bridge_config(T, A, B, blk, C, b_op, owc, *, in_fragment):
    """Assemble one config. Factored out of the strategy so the deterministic exhaustive
    enumerator below covers the SAME constructor the fuzzer uses -- an enumerator over a
    private copy of the template would be a check that verifies a clone of its subject."""
    schema = _bool_star_bridge_schema(T, A, B, blk, b_op, C)
    pool = _bool_star_bridge_pool(T, A, B, blk, owc)
    # `C` is fully derived (no Direct arm), so nothing can be WRITTEN to it -- and
    # `_sb_grid` derives its relation list from the pool, so without this it would be
    # compiled and never queried: the "compiled but never driven" cell by name.
    extra_rels = (C,) if C is not None else ()
    return _BSBConfig(schema, owc, pool, in_fragment, extra_rels)


def _bsb_in_fragment_config(T, A, B, blk, C, b_op, owc):
    """★ THE IN-FRAGMENT CONSTRUCTION -- the single definition of "this draw promises the
    graph index joins". The fuzzing strategy AND the exhaustive enumerator below both call
    THIS function; an enumerator with its own copy of the placement rule would verify a
    clone of the generator rather than the generator, which is precisely how a check ends
    up green over a subject that changed underneath it.

    ``or`` keeps the whole schema pure-union, so any OWC subset avoiding the doubly-bridged
    (T, A) shape is fine. A boolean op must go DOWNSTREAM of the bridge target and must
    carry no object wildcard at all (measured; see ``_BOOL_ARM_PLACEMENTS``)."""
    if b_op == 'or':
        return _bool_star_bridge_config(T, A, B, blk, None, b_op, owc, in_fragment=True)
    return _bool_star_bridge_config(T, A, B, blk, C, b_op, frozenset(), in_fragment=True)


class _BSBConfig(NamedTuple):
    schema: str
    owc: frozenset
    pool: list
    in_fragment: bool          # the draw PROMISES the graph index joins (4-way)
    extra_rels: tuple


@st.composite
def bool_star_bridge_configs(draw):
    """A boolean x star-bridge config, drawn in one of two declared strata.

    ★ ``in_fragment`` (3 draws in 4) -- the config is constructed so the graph index
    MUST join, and ``BoolStarBridgeParityMachine.setup`` asserts it does. Two thirds of
    those carry a real boolean arm (downstream of a pure-union bridge target), which is
    the cell that had never once been compared against the graph index. See the
    ``_BOOL_ARM_PLACEMENTS`` block above for the measurement that forced this.

    ``not in_fragment`` (1 draw in 4) -- today's unconstrained draw over the full OWC
    domain and the ``target`` placement, kept BECAUSE it is mostly out of fragment: it is
    what keeps the decision-15 / doubly-bridged REJECTION contract fuzzed. The machine
    asserts the rejection is one of the recorded scope families rather than letting an
    arbitrary compile failure quietly shrink the matrix.

    ``intrange(0, 3) == 3`` selects the boundary stratum, so hypothesis' shrink target
    (0) is an in-fragment 4-way draw -- a shrunk counterexample stays maximally compared.
    """
    return _bool_star_bridge_draw(_HypothesisChoices(draw))


def _bool_star_bridge_draw(ch) -> '_BSBConfig':
    """The draw BODY, against the ``_Choices`` seam so the rate floor below measures this
    generator rather than a copy of it."""
    T = ch.one(_SB_TYPES)
    rels = ch.perm(_SB_RELS)
    A, B, blk, C = rels[0], rels[1], rels[2], rels[3]
    b_op = ch.one(_BOOL_B_OPS)
    boundary = ch.intrange(0, 3) == 3

    if not boundary:
        # pure union: the graph joins for any OWC subset that avoids the doubly-bridged
        # (T, A) shape, so the wildcard axis stays fuzzed. (Ignored for boolean ops.)
        return _bsb_in_fragment_config(T, A, B, blk, C, b_op,
                                       ch.subset([(T, 'parent'), (T, blk), (T, B)]))

    # the scope-boundary stratum: the pre-2026-08-10 draw, verbatim.
    owc_domain = [(T, 'parent'), (T, A), (T, blk)]
    if b_op == 'or':
        owc_domain.append((T, B))
    return _bool_star_bridge_config(T, A, B, blk, None, b_op, ch.subset(owc_domain),
                                    in_fragment=False)


def test_bool_star_bridge_deterministic_pin():
    """Deterministic guard that the boolean x star-bridge cross stays closed regardless of
    hypothesis sampling: the canonical config (folder / admin=A / viewer=B / blocked, B an
    exclusion) with OWC over ``parent`` applied through a ParityEngine. The pool contains
    the star-bridge admission instances AND the boolean storage/routed leaves, so
    ParityEngine asserts accept/reject unanimity + full-grid parity + I9/paranoia on EVERY
    op (it raises on any divergence). Note: unlike the pure-union star-bridge pin, the
    bridge CYCLES here dissolve -- with B (viewer) boolean, admin's ``folder#viewer`` arm
    is a PDerivedUserset rather than a closure edge, so the reg9/reg10 closure cycles never
    materialize and the whole pool is accepted UNANIMOUSLY. The property is that agreement,
    not the presence of rejections; the ghost hop must never fire.

    ★ CORRECTED 2026-08-10. This pin has ALWAYS run 3-way: with the boolean on the bridge
    TARGET the graph index refuses the schema outright, `ParityEngine` sets `graph=None`,
    and "the boolean x star-bridge cross stays closed" was a claim about the oracle and
    two set engines only. The drop is now ASSERTED and named rather than silent, and
    ``test_bool_star_bridge_four_way_deterministic_pin`` below is its 4-way companion --
    the same cross with the boolean placed downstream, where the graph does join. Do not
    delete either: this one pins the SCOPE REJECTION, that one pins the COMPARISON."""
    T, A, B, blk = 'folder', 'admin', 'viewer', 'blocked'
    schema = _bool_star_bridge_schema(T, A, B, blk, 'but not')
    owc = frozenset({(T, 'parent')})
    pool = _bool_star_bridge_pool(T, A, B, blk, owc)
    pe = _parity_or_skip_doubly_bridged(schema, owc)
    assert pe is not None, 'the canonical boolean star-bridge config must compile'
    try:
        assert pe.graph is None, (
            'the boolean-on-the-bridge-target config now COMPILES for the graph index -- '
            'if the decision-15 scope hook was lifted this pin must become 4-way, and '
            "the generator's `target` placement must move into the in_fragment stratum")
        _assert_recorded_scope_rejection(pe.graph_drop_reason, 'boolean-on-target pin')
        decisions = [pe.add_tuple(*t) for t in pool]     # ParityEngine asserts parity per op
        for side in pe.set_sides:
            assert side.se._ghost_hop_fired is False
    finally:
        pe.close()
    assert any(decisions), f'pool exercised no accepted ops (0/{len(decisions)})'


def test_bool_star_bridge_four_way_deterministic_pin():
    """★ The boolean x star-bridge cross, ACTUALLY COMPARED AGAINST THE GRAPH INDEX.

    Property guarded: a schema that keeps every star-bridge feature (a star tupleset
    ``parent: [T, T:*]``, a self-referential wildcard userset ``T:*#A``, a TTU
    ``A from parent``) AND carries a boolean arm is evaluated by all four backends in
    lockstep -- accept/reject unanimity, I12, full-grid oracle parity, paranoia and the
    graph's I9 audit, on every op.

    Until 2026-08-10 NOTHING in this repo compared that cross against the graph: the
    boolean was always placed on the bridge target, which is a decision-15 scope rejection
    (768/768 configs, enumerated), so `BoolStarBridgeParityMachine` ran 0 boolean 4-way
    draws out of 400 and `test_bool_star_bridge_deterministic_pin` ran 3-way.

    Sabotage (observed): deleting the `assert pe.graph is not None` below and reverting
    the generator's `downstream` placement restores exactly the old silent 3-way state --
    which is why the assertion, not a docstring, is the artifact here."""
    T, A, B, blk, C = 'folder', 'admin', 'viewer', 'blocked', 'owner'
    schema = _bool_star_bridge_schema(T, A, B, blk, 'but not', C)
    assert f'define {C}: {B} but not {blk}' in schema, schema
    pool = _bool_star_bridge_pool(T, A, B, blk, frozenset())
    pe = _parity_or_skip_doubly_bridged(schema, frozenset())
    assert pe is not None, 'the downstream-boolean star-bridge config must compile'
    try:
        assert pe.graph is not None, (
            'the graph index dropped the downstream-boolean star-bridge config: '
            f'{pe.graph_drop_reason}\n{schema}')
        decisions = [pe.add_tuple(*t) for t in pool]     # ParityEngine asserts parity per op
        # non-vacuity: the derived relation C must actually be QUERIED, and by a grid that
        # knows about it (a pool-derived relation list omits C -- it has no Direct arm).
        grid = _sb_grid(pool, (C,))
        assert any(q[3] == C for q in grid), 'grid never queries the boolean relation'
        for q in grid:
            if q[3] == C:
                pe.check(*q)
        for side in pe.set_sides:
            assert side.se._ghost_hop_fired is False
    finally:
        pe.close()
    assert any(decisions), f'pool exercised no accepted ops (0/{len(decisions)})'


class BoolStarBridgeParityMachine(RuleBasedStateMachine):
    """Weighted add/remove/check/rebuild ops over a GENERATED boolean star-bridge schema,
    driven through a ParityEngine. Crosses the bridge-admission axis with boolean arms
    (and/but not on B): every accepted op runs unanimity + I12 + full-grid oracle parity +
    paranoia + (when the graph joins) I9. Doubly-bridged configs are asserted rejected on
    both backends and skipped; the ghost hop is asserted never-fired in teardown."""

    @initialize(cfg=bool_star_bridge_configs())
    def setup(self, cfg):
        self.pool = cfg.pool
        self.pe = _parity_or_skip_doubly_bridged(cfg.schema, cfg.owc)
        if self.pe is None:
            # doubly-bridged: rejected on BOTH backends (asserted) and skipped. Only the
            # boundary stratum may produce this -- an in-fragment draw that turns out
            # doubly bridged is a generator bug, not a smaller run.
            assert not cfg.in_fragment, (
                'an in_fragment draw was refused as doubly bridged; the 4-way promise '
                f'in bool_star_bridge_configs is broken:\n{cfg.schema}')
            return
        # ★ THE ASSERTION THIS MACHINE NEVER HAD. Measured 2026-08-10: 269/400 draws
        # raised UnsupportedByGraphIndex, ParityEngine set graph=None, and the machine
        # fuzzed 3-way -- oracle + two set engines, no graph index -- while reporting
        # green; only 51/400 were 4-way and NONE of those carried a boolean arm. Its
        # sibling StarBridgeParityMachine has asserted this since it was written.
        if cfg.in_fragment:
            assert self.pe.graph is not None, (
                'an in_fragment boolean star-bridge draw DROPPED the graph index, so this '
                'machine would have fuzzed 3-way and reported green: '
                f'{self.pe.graph_drop_reason}\n{cfg.schema}')
        elif self.pe.graph is None:
            _assert_recorded_scope_rejection(
                self.pe.graph_drop_reason, 'bool star-bridge boundary draw')
        self.grid = _sb_grid(cfg.pool, cfg.extra_rels)
        self.live: list = []

    @rule(data=st.data())
    def add(self, data):
        if self.pe is None:
            return
        raw = data.draw(st.sampled_from(self.pool))
        if self.pe.add_tuple(*raw):
            self.live.append(raw)

    @rule(data=st.data())
    def remove(self, data):
        if self.pe is None or not self.live:
            return
        raw = data.draw(st.sampled_from(sorted(set(self.live))))
        if self.pe.remove_tuple(*raw):
            self.live.remove(raw)

    @rule(data=st.data())
    def check(self, data):
        if self.pe is None:
            return
        self.pe.check(*data.draw(st.sampled_from(self.grid)))

    @rule(data=st.data())
    def rebuild_sets(self, data):
        if self.pe is None or data.draw(st.integers(min_value=0, max_value=3)) != 0:
            return
        qs = data.draw(st.lists(st.sampled_from(self.grid), min_size=1, max_size=6,
                                unique=True))
        for side in self.pe.set_sides:
            before = [side.se.check(*q) for q in qs]
            side.se.rebuild()
            assert [side.se.check(*q) for q in qs] == before, \
                f'{side.name} check grid changed after rebuild'

    def teardown(self):
        pe = getattr(self, 'pe', None)
        if pe is not None:
            for side in pe.set_sides:
                assert side.se._ghost_hop_fired is False, \
                    'set-engine ghost hop fired on a constructible boolean star-bridge schema'
            pe.close()


TestBoolStarBridgeParityMachine = BoolStarBridgeParityMachine.TestCase


# ---------------------------------------------------------------------------
# ★★ THE 4-WAY FLOOR for the boolean x star-bridge machine (2026-08-10).
#
# `BoolStarBridgeParityMachine` cannot be allowed to run mostly-3-way and report green
# again. Two instruments, deliberately of different kinds:
#
#   * an EXHAUSTIVE, deterministic statement about the in-fragment config space (rank 1 on
#     `docs/sabotage-procedure.md`'s durability ranking -- it is a complete claim about a
#     closed space, not a sample), which also carries the REJECTION WITNESS for the
#     placement that is out of fragment, so relaxing the scope check revokes the exemption
#     automatically instead of minting a silent blind spot;
#   * a RATE FLOOR over the actual strategy (rank 3 -- a floor with a stated provenance),
#     which is what catches a future edit to the stratum weights.
#
# Both are self-contained: they re-draw and re-compile inside the test body rather than
# reading module-level counters. `verify.sh` partitions `tests/` into tiles by collection
# index, so a counter incremented by the machine and asserted by a separate test can land
# in a DIFFERENT TILE and assert over zeros -- an assurance step that fails by passing, by
# construction.
# ---------------------------------------------------------------------------

def test_bool_star_bridge_in_fragment_stratum_is_exhaustively_four_way():
    """★ Exhaustive over the whole in-fragment config space: every configuration the
    ``in_fragment`` stratum of ``bool_star_bridge_configs`` can produce is accepted by the
    graph index, and two thirds of them carry a real boolean arm.

    Measured 2026-08-10 (this enumeration, run at authoring time):
        in-fragment configs enumerated: 144   graph joined: 144   boolean: 96

    It also carries the REJECTION WITNESS for the other placement: with the boolean on the
    bridge TARGET the compiler must refuse, for every OWC subset -- enumerated at 768/768
    when this was written. If that scope hook is ever lifted, `pytest.raises` fails here
    and the exemption is revoked rather than silently becoming a new blind spot.

    Sabotage (observed 2026-08-10): reverting `bool_star_bridge_configs` so the in-fragment
    stratum uses the `target` placement for boolean ops -- the one-line "simplification" a
    future contributor would make -- fires the first assertion:
        AssertionError: the in_fragment stratum promised 4-way and the graph index REFUSED
        24 of 144 configs. First: relation folder#viewer: star tupleset [folder:*] on
        'parent' derives the wildcard userset shape (folder, admin) over the derived
        relation folder#admin, ...
    """
    import itertools
    joined, refused, boolean = 0, [], 0
    for T in _SB_TYPES:
        for rels in itertools.permutations(_SB_RELS):
            A, B, blk, C = rels
            for b_op in _BOOL_B_OPS:
                boolean += (b_op != 'or')
                cfg = _bsb_in_fragment_config(       # the generator's OWN construction
                    T, A, B, blk, C, b_op,
                    frozenset({(T, 'parent'), (T, blk), (T, B)}))
                assert cfg.in_fragment
                try:
                    parse_openfga_schema(cfg.schema, object_wildcard_shapes=cfg.owc)
                    joined += 1
                except (UnsupportedByGraphIndex, ValueError) as e:
                    # NOTE UnsupportedByGraphIndex is NOT a ValueError (it derives from
                    # Exception); catching only ValueError here would let the sabotage
                    # escape as a raw traceback instead of the diagnostic below.
                    refused.append(f'{type(e).__name__}: {e}')
    total = joined + len(refused)
    assert total == 144, f'the in-fragment config space changed size: {total} != 144'
    assert not refused, (
        f'the in_fragment stratum promised 4-way and the graph index REFUSED '
        f'{len(refused)} of {total} configs. First: {refused[0]}')
    assert boolean == 96, boolean
    assert set(_BOOL_ARM_PLACEMENTS) == {'target', 'downstream'}, _BOOL_ARM_PLACEMENTS

    # the rejection witness for the `target` placement under a boolean op
    for T in _SB_TYPES:
        A, B, blk = _SB_RELS[0], _SB_RELS[1], _SB_RELS[2]
        for b_op in ('and', 'but not'):
            for owc in (frozenset(), frozenset({(T, 'parent')}), frozenset({(T, blk)})):
                with pytest.raises(UnsupportedByGraphIndex) as ei:
                    parse_openfga_schema(
                        _bool_star_bridge_schema(T, A, B, blk, b_op),
                        object_wildcard_shapes=owc)
                _assert_recorded_scope_rejection(str(ei.value), 'target-placement witness')


# Provenance for the floors below: measured 2026-08-10 by sampling
# `bool_star_bridge_configs` 400 times at hypothesis seed 0.
#   BEFORE this change: 4-way 51/400 (13 %), 3-way 269/400 (67 %), skipped 80/400 (20 %),
#                       and 4-way draws carrying a boolean arm: 0.
#   AFTER:              4-way ~77 %, of which ~2/3 carry a boolean arm.
# The floors are set below the measurement so ordinary sampling noise is not flaky, but
# well above the BEFORE state so the regression that motivated this work cannot return.
_BSB_FOUR_WAY_FLOOR = 0.55
_BSB_BOOLEAN_FOUR_WAY_FLOOR = 0.30


def test_bool_star_bridge_generator_four_way_rate():
    """★ The measured property: this generator must MOSTLY run the graph index, and must
    run it on draws that carry a boolean arm.

    Before 2026-08-10 the honest description of ``BoolStarBridgeParityMachine`` was: 13 %
    of draws 4-way, 67 % silently graph-less, and *zero* draws in which a boolean arm was
    ever compared against the graph index -- while the generator's own header called
    itself "the audit's headline blind spot" closer.

    Sabotage (observed 2026-08-10): deleting the `if not boundary:` branch of
    ``bool_star_bridge_configs`` -- i.e. restoring the pre-2026-08-10 draw, which is the
    narrowest plausible weakening because it looks like removing dead stratification --
    fires it:
        AssertionError: only 9/80 = 11% of draws run the graph index (floor 55%); this
        machine is fuzzing 3-way and reporting green
    """
    import random
    cfgs = []
    for s in _SWEEP_SEEDS:
        rng = random.Random(s)          # ONE rng per seed: a fresh Random(s) per draw
        for _ in range(_SWEEP_N):       # would make every config in the seed identical
            cfgs.append(_bool_star_bridge_draw(_RandomChoices(rng)))
    assert len({c.schema for c in cfgs}) > 10, (
        'the sweep produced almost no distinct configs, so every rate below is computed '
        'from one draw -- the instrument, not the subject, is broken')
    four_way, three_way, skipped, boolean_four_way = 0, 0, 0, 0
    for cfg in cfgs:
        boolean = ' but not ' in cfg.schema or ' and ' in cfg.schema
        try:
            parse_openfga_schema(cfg.schema, object_wildcard_shapes=cfg.owc)
            four_way += 1
            boolean_four_way += bool(boolean)
        except DoublyBridgedShapeError:
            skipped += 1
            assert not cfg.in_fragment, 'in_fragment draw was doubly bridged'
        except (UnsupportedByGraphIndex, CyclicDerivedDependency) as e:
            three_way += 1
            assert not cfg.in_fragment, (
                f'in_fragment draw DROPPED the graph: {e}\n{cfg.schema}')
            _assert_recorded_scope_rejection(str(e), 'boundary-stratum draw')
    total = len(cfgs)
    rate = four_way / total
    assert rate >= _BSB_FOUR_WAY_FLOOR, (
        f'only {four_way}/{total} = {rate:.0%} of draws run the graph index '
        f'(floor {_BSB_FOUR_WAY_FLOOR:.0%}); this machine is fuzzing 3-way and '
        f'reporting green')
    brate = boolean_four_way / total
    assert brate >= _BSB_BOOLEAN_FOUR_WAY_FLOOR, (
        f'only {boolean_four_way}/{total} = {brate:.0%} of draws compare a BOOLEAN arm '
        f'against the graph index (floor {_BSB_BOOLEAN_FOUR_WAY_FLOOR:.0%}); the '
        f'"booleans x star-bridge" cross this generator exists for is back to 0 %')
    # NEGATIVE CONTROL / non-vacuity: the scope-boundary stratum must still fire, or the
    # rejection contract above is asserted over nothing and the decision-15 boundary stops
    # being fuzzed at all. 1 draw in 4 is the boundary stratum; ~85 % of those reject.
    assert three_way + skipped >= 5, (
        f'the scope-boundary stratum produced only {three_way + skipped}/{total} '
        f'rejections; the decision-15 / doubly-bridged contract is no longer exercised')
