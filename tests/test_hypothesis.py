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

import pytest
from hypothesis import HealthCheck, Phase, assume, example, given, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from index_v4.invariants import snapshot_rows
from index_v4.outbox import outbox_watermark
from index_v4.processor import DeltaProcessor
from zanzibar_utils_v1 import (Computed, Direct, DoublyBridgedShapeError, Exclusion,
                               Intersection, Restriction, TTU, Union,
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


# ---------------------------------------------------------------------------
# Generated schemas: relations on `doc` built in topo order (stratifiable by
# construction), referencing only earlier relations; rendered via the unparser.
# ---------------------------------------------------------------------------

_BASE_DIRECTS = [
    (Restriction('user', '...', False),),
    (Restriction('user', '...', False), Restriction('user', '...', True)),
    (Restriction('user', '...', True),),
]


@st.composite
def schema_asts(draw, allow_usersets: bool = True):
    """Relations on ``doc`` in topo order (stratifiable), each referencing only earlier
    relations.

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
    n = draw(st.integers(min_value=2, max_value=5))
    names = [f'r{i}' for i in range(n)]
    ast = {('doc', 'parent'): Direct((Restriction('doc', '...', False),))}

    def expr(i: int, depth: int):
        leaves = [Direct(draw(st.sampled_from(_BASE_DIRECTS)))]
        if i > 0:
            ref = draw(st.sampled_from(names[:i]))
            leaves.append(Computed(ref))
            leaves.append(TTU(ref, 'parent'))
            # G2 (deviations 2026-07-17): a CONCRETE userset restriction over an
            # EARLIER (possibly tainted) relation -- `[doc#r_k]`. When r_k is derived
            # this compiles to a PDerivedUserset and drives the edge-free-userset
            # (`ResidueV1.upos`) + `_find_leaf_node` reconcile paths, which twice had
            # CRITICAL bugs found by review not fuzzing (deviations 2026-07-08 D2;
            # 2026-07-08 review-2 #1). Offered at modest probability so the existing
            # example distribution is not washed out.
            if allow_usersets and draw(st.integers(min_value=0, max_value=2)) == 0:
                uref = draw(st.sampled_from(names[:i]))
                leaves.append(Direct((Restriction('doc', uref, False),)))
        leaf = st.sampled_from(leaves)
        if depth >= 2:
            return draw(leaf)
        kind = draw(st.sampled_from(['leaf', 'leaf', 'union', 'intersection', 'exclusion']))
        if kind == 'leaf':
            return draw(leaf)
        a, b = expr(i, depth + 1), expr(i, depth + 1)
        if kind == 'union':
            return Union((a, b))
        if kind == 'intersection':
            return Intersection((a, b))
        return Exclusion(a, b)

    for i, name in enumerate(names):
        ast[('doc', name)] = expr(i, 0)
    return ast


def _op_pool(ast):
    """Schema-valid raw tuples over the tiny universe (Direct restrictions only)."""
    out = []
    for (otype, rel), e in ast.items():
        def directs(x):
            if isinstance(x, Direct):
                yield x
            elif isinstance(x, (Union, Intersection)):
                for c in x.children:
                    yield from directs(c)
            elif isinstance(x, Exclusion):
                yield from directs(x.base)
                yield from directs(x.subtract)
        for d in directs(e):
            for r in d.restrictions:
                names = ['*'] if r.wildcard else (USERS if r.type == 'user' else DOCS)
                for sn in names:
                    for on in DOCS:
                        out.append((r.predicate, r.type, sn, rel, otype, on))
    return sorted(set(out))


def _grid(ast):
    subjects = [('...', 'user', 'u1'), ('...', 'user', 'ghost'), ('...', 'user', '*')]
    return [(sp, st_, sn, rel, ot, on)
            for (ot, rel) in sorted(ast) if ot == 'doc'
            for (sp, st_, sn) in subjects
            for on in DOCS + ['ghostD']]


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


@given(ast=schema_asts(), data=st.data())
def test_add_then_remove_restores_row_multiset(ast, data):
    pool = _op_pool(ast)
    assume(pool)
    schema = unparse_schema_ast(ast)
    session, widx, proc, write = build(schema)
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
        session, widx, proc, write = build(schema)
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

    live_session, live_widx, live_proc, live_write = build(schema)
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
        out.add((A, T, '*', A, ot, on))              # T:*#A  (self-ref wildcard userset)
        for x in _SB_OBJS:
            out.add((B, T, x, A, ot, on))            # T:x#B  (routes via the TTU)
    for (ot, on) in objects_for(B):                  # B: [user] (the "A from parent" arm is a rule)
        for u in _SB_USERS:
            out.add(('...', 'user', u, B, ot, on))
    return sorted(out)


@st.composite
def star_bridge_configs(draw):
    """A star-bridge schema (T, distinct A/B) + a drawn object-wildcard-shape subset +
    the matching valid-tuple pool. Non-doubly-bridged configs keep the graph 4-way
    (asserted in the machine's setup), so a graph/set admission divergence is actually
    compared; doubly-bridged configs are asserted rejected on both backends and skipped."""
    T = draw(st.sampled_from(_SB_TYPES))
    A = draw(st.sampled_from(_SB_RELS))
    B = draw(st.sampled_from([r for r in _SB_RELS if r != A]))
    # Object-wildcard shapes are drawn over ``parent`` (out-bridge feeder, reg11), ``B``
    # (the TTU target -- its w_all node gets the out-bridge) AND ``A`` (deviations
    # 2026-07-17: this is the previously-excluded F1/F2 axis). ``A`` carries the literal
    # ``T:*#A`` wildcard-userset restriction, so an object wildcard on it makes ``(T, A)``
    # a DOUBLY-BRIDGED shape -- which the compiler now rejects with
    # ``DoublyBridgedShapeError`` on BOTH backends (the third decision-15 scope rejection).
    # The machine's setup asserts that consistent rejection and skips such a config; all
    # other configs proceed exactly as before. Widening the domain here fuzzes the F1/F2
    # boundary that the previous ``{parent, B}``-only domain left uncovered.
    owc = frozenset(draw(st.sets(
        st.sampled_from([(T, 'parent'), (T, A), (T, B)]), max_size=3)))
    return _star_bridge_schema(T, A, B), owc, _star_bridge_pool(T, A, B, owc)


# ---------------------------------------------------------------------------
# Shared helpers for the star-bridge machines (deviations 2026-07-17):
#   * doubly-bridged configs must reject identically on both backends;
#   * a check grid derived from the config's own valid-tuple pool (D4/G1);
#   * a ParityEngine builder that skips (after asserting rejection) doubly-bridged
#     configs and otherwise returns a live engine.
# ---------------------------------------------------------------------------

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


def _sb_grid(pool):
    """A check grid drawn from the config's OWN pool: subjects (+ ghost/'*') x relations
    x objects (+ ghost). ParityEngine.check asserts cross-backend equality per query."""
    subjects = sorted({(t[0], t[1], t[2]) for t in pool}
                      | {('...', 'user', 'ghost'), ('...', 'user', '*')})
    otypes = sorted({t[4] for t in pool})
    objects = sorted({(t[4], t[5]) for t in pool} | {(ot, 'ghostO') for ot in otypes})
    rels = sorted({t[3] for t in pool})
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


def _bool_star_bridge_schema(T, A, B, blk, b_op) -> str:
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


@st.composite
def bool_star_bridge_configs(draw):
    T = draw(st.sampled_from(_SB_TYPES))
    rels = draw(st.permutations(_SB_RELS))
    A, B, blk = rels[0], rels[1], rels[2]
    b_op = draw(st.sampled_from(_BOOL_B_OPS))
    # OWC domain: parent (out-bridge feeder), A (doubly-bridged -> rejection path), blk
    # (a plain subtrahend). B is offered only when it stays pure-union ('or'); when B is
    # boolean an object wildcard on it is the ORTHOGONAL owc-on-derived (decision-15)
    # axis, covered elsewhere -- excluded here to keep this generator on the bridge cross.
    owc_domain = [(T, 'parent'), (T, A), (T, blk)]
    if b_op == 'or':
        owc_domain.append((T, B))
    owc = frozenset(draw(st.sets(st.sampled_from(owc_domain), max_size=len(owc_domain))))
    schema = _bool_star_bridge_schema(T, A, B, blk, b_op)
    return schema, owc, _bool_star_bridge_pool(T, A, B, blk, owc)


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
    not the presence of rejections; the ghost hop must never fire."""
    T, A, B, blk = 'folder', 'admin', 'viewer', 'blocked'
    schema = _bool_star_bridge_schema(T, A, B, blk, 'but not')
    owc = frozenset({(T, 'parent')})
    pool = _bool_star_bridge_pool(T, A, B, blk, owc)
    pe = _parity_or_skip_doubly_bridged(schema, owc)
    assert pe is not None, 'the canonical boolean star-bridge config must compile'
    try:
        decisions = [pe.add_tuple(*t) for t in pool]     # ParityEngine asserts parity per op
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
        schema, owc, pool = cfg
        self.pool = pool
        self.pe = _parity_or_skip_doubly_bridged(schema, owc)
        if self.pe is None:
            return                              # doubly-bridged: rejected + skipped
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
