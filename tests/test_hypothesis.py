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
from zanzibar_utils_v1 import (Computed, Direct, Exclusion, Intersection, Restriction,
                               TTU, Union, parse_openfga_schema, parse_schema_ast,
                               unparse_schema_ast)
from tests.parity import ParityEngine
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
def schema_asts(draw):
    n = draw(st.integers(min_value=2, max_value=5))
    names = [f'r{i}' for i in range(n)]
    ast = {('doc', 'parent'): Direct((Restriction('doc', '...', False),))}

    def expr(i: int, depth: int):
        leaves = [Direct(draw(st.sampled_from(_BASE_DIRECTS)))]
        if i > 0:
            ref = draw(st.sampled_from(names[:i]))
            leaves.append(Computed(ref))
            leaves.append(TTU(ref, 'parent'))
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
# Stateful: weighted ops against a ParityEngine over a generated schema (§9)
# ---------------------------------------------------------------------------

class ParityMachine(RuleBasedStateMachine):
    """Every accepted op already runs 4-way unanimity, I12, full-grid oracle parity,
    per-commit paranoia (I1-I7, I10, §8.3), and the graph's I9 audit -- the rules
    just drive the walk."""

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
    the matching valid-tuple pool. Every config keeps the graph 4-way (asserted in the
    machine's setup), so a graph/set admission divergence is actually compared."""
    T = draw(st.sampled_from(_SB_TYPES))
    A = draw(st.sampled_from(_SB_RELS))
    B = draw(st.sampled_from([r for r in _SB_RELS if r != A]))
    # Object-wildcard shapes are drawn only over ``parent`` (out-bridge feeder, reg11) and
    # ``B`` (the TTU target -- its w_all node gets the out-bridge). Deliberately NOT over
    # ``A``: an object wildcard on the relation that ALSO carries the ``T:*#A``
    # wildcard-userset restriction opens an orthogonal axis (the star node plays BOTH the
    # object-wildcard and the subject-userset role) with its own pre-existing graph
    # divergences, unrelated to the bridge-cycle class under test -- see the 2026-07-16
    # star-bridge-fuzzer entry in docs/spec-deviations.md (F1/F2) and the HANDOFF backlog.
    owc = frozenset(draw(st.sets(
        st.sampled_from([(T, 'parent'), (T, B)]), max_size=2)))
    return _star_bridge_schema(T, A, B), owc, _star_bridge_pool(T, A, B, owc)


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
    """Weighted add/remove/check ops over a GENERATED star-bridge schema, driven through
    a ParityEngine (4-way: graph + both set engines + oracle). Every accepted op runs
    unanimity + I12 + full-grid oracle parity + paranoia inside the engine; the point
    here is the ADMISSION sequence -- order-dependent bridge cycles (reg10 is W1-then-W2)
    only surface when writes interleave, which the stock ParityMachine can't build."""

    @initialize(cfg=star_bridge_configs())
    def setup(self, cfg):
        schema, owc, pool = cfg
        self.pool = pool
        self.pe = ParityEngine(schema, object_wildcard_shapes=owc, grid_cap=150)
        # 4-way is the invariant that makes this catch graph/set divergences; if a future
        # change drops the graph on this shape, fail loudly rather than fuzz 3-way blind.
        assert self.pe.graph is not None, 'star-bridge schema unexpectedly dropped the graph'
        self.live: list = []

    @rule(data=st.data())
    def add(self, data):
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

    def teardown(self):
        if hasattr(self, 'pe'):
            self.pe.close()


TestStarBridgeParityMachine = StarBridgeParityMachine.TestCase
