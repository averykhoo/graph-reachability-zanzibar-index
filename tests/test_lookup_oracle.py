"""
Brute-force oracle-lookup parity gate.

The check surface is pinned 3/4-way by the matrix and property suites, but the
*lookup* read surfaces (``lookup`` / ``lookup_reverse`` / ``expand``) had NO
independent reference: the oracle is check-only and the ParityEngine serves lookups
from a single "richest live backend" with no unanimity (deviations log #3, P1 #2).
A lookup that leaks or drops an object is a wrong authorization answer nothing
would catch. This module closes that gap by composing the oracle's pointwise
``check`` into a brute-force lookup reference over the candidate universe:

    oracle_lookup(subject, rel, T)   = {n | oracle.check(subject, rel, T:n)}
    oracle_reverse(rel, T:n)         = {u | oracle.check(u,       rel, T:n)}

and asserting BOTH backends' lookup surfaces against it after every accepted op of
seeded randomized walks (adds AND removals, drained to the empty store -- removal
is where these surfaces were least tested).

Exact properties asserted (O = the independent oracle; the candidate grid is
schema-derived: subjects from Direct-restriction + TTU from-chain shapes x
{names, ghost, '*'}, objects from declared (type, relation) x {names, ghost, '*'}):

Graph index (``WildcardIndex``) -- exact (two-sided) surfaces:
  G1  lookup exactness: for every candidate object, [object's public node in
      ``node_ids``  or  (o_type, rel, 'all') in ``markers``] == O; a '*' object is
      covered by the 'all' marker alone (intensional).
  G2  lookup soundness sweep: every returned node id whose (type, predicate) is a
      declared relation is O-true for the subject. Internal '.'-leaf-family storage
      nodes appear in forward results by design (callers filter by shape, cf.
      test_reads.viewer_objects) and are skipped.
  G3  lookup_reverse exactness: for every candidate subject, [subject node in
      ``node_ids``  or  ((s_type, s_pred, 'any') in markers and subject node not in
      ``excluded_node_ids``)] == O; a '*' subject is covered by the 'any' marker
      alone. Variant-'all' markers in reverse results (and 'any' in forward) are
      bridge-topology artifacts with no pointwise claim -- ignored.
  G4  lookup_reverse sweeps: every node id maps to an O-true subject; every
      ``excluded_node_ids`` entry is marker-covered AND O-false (the neg
      semantics); no '.'-leaf node ever leaks into reverse results.

Set engine (both ``SetOps``) -- exact where the representation is, one-sided where
it drops information:
  S1  expand pointwise exactness: MemberSet coverage (pos wins; else shape in
      stars and id not in neg; uninterned subjects by shape-in-stars) == O, for
      EVERY candidate subject (userset-shaped included since the X3 fix: an
      oracle-true userset subject is always interned or star-covered). Star
      shapes are exact both ways ('*' subjects: shape in stars == O).
  S2  expand component sweeps: every ``pos`` id is O-true; every ``neg`` id is
      star-covered (its own shape in ``stars``) AND O-false.
  S3  lookup_reverse is the documented neg-dropping render of expand
      (node_ids == pos, markers == stars; engine.py lookup_reverse) => one-sided:
      every node id O-true (soundness); every O-true candidate subject is in
      node_ids or marker-covered (completeness); marker-covered-but-O-false is
      LEGAL (that is exactly the dropped neg).
  S4  forward lookup (check-backed): every node id and every marker is O-true
      (markers against the intensional '*'-object query); exact two-sided over
      ALL candidates -- tuple-anchored object keys are write-time interned
      (§6.4 reverse-dependency interning, the X1 fix), and star-object truth is
      carried exactly by the intensional markers.

Genuine-divergence inventory (each was a wrong/undefined read answer when
found; FIXED entries are pinned as plain regression tests below, open ones as
strict xfails -- NOT worked around; see the tests for full repros):
  X1  FIXED (2026-07-13; plain regression test below). Set forward ``lookup``
      dropped objects reachable ONLY via TTU whose (type, name, relation) key
      was never interned. Fixed per spec set-engine §6.4: writes intern each
      tuple's reverse-dependent object keys (Computed chains + TTU tuplesets),
      and lookup renders intensional markers per declared relation, so S4 is
      now exact two-sided over the whole candidate grid.
  X2  FIXED (2026-07-13; plain regression test below). Graph ``lookup_reverse``
      on a derived relation with o_name='*' raised ValueError (wildcard.py
      _get_concrete -> core.node reserved-name guard) where ``check`` answers
      False (P7 #3) and the set engine returns empty. Fixed: the derived branch
      now short-circuits o_name='*' to the empty result (decision 15: no
      object-star state can exist), so the gate's grid asserts derived
      '*'-object reverse lookups like every other object.
  X3  FIXED (2026-07-13; plain regression test below). Set ``expand`` /
      ``lookup_reverse`` could not represent an O-true from-chain userset
      subject that was never interned (no id existed). Fixed by write-time
      interning of the from-chain userset key (subject, target_rel) on every
      stored tupleset tuple; the gate's S1/S3 completeness no longer skips
      userset-shaped subjects -- uninterned subjects are asserted exactly via
      star coverage.
  X4  FIXED (2026-07-13; plain regression tests below). CHECK-level divergence
      (found by this gate, wider than lookups): on a DERIVED TTU, userset-shaped
      subjects whose truth flows through a stored tupleset parent answered False
      on the graph where the oracle and BOTH set engines answer True. Two
      flavors: (a) the from-chain userset itself (oracle ttu_leaf identity
      rule) -- after ``doc:d1 parent doc:d2``,
      check('viewer','doc','d1','inherited','doc','d2') was graph-False; and
      (b) userset membership lifted through the parent's target -- after
      ``group:g1#member editor doc:d2`` + ``doc:d2 parent doc:d1``,
      check('member','group','g1','inherited','doc','d1') was graph-False.
      Fixed in the delta processor (the boolean spec is silent on both shapes;
      the oracle is the pin): ttu_check/tupleset_ttu_check implement the
      from-chain identity rule, and reconcile enumerates from-chain userset
      keys (interning a node only when the outcome must be recorded) plus the
      tainted targets' residue ``upos`` members, so the dependent's residue is
      complete for userset subjects and the ``check``/lookup surfaces answer
      them exactly. The walks no longer skip any (subject, object) pair --
      everything is strict.

A tamper suite proves the gate can fail: corrupted results (leaked id, dropped
id, cleared exclusions, dropped neg) must each trip the checkers.
"""

import os
import random

import pytest
from hypothesis import HealthCheck, assume, given, settings, strategies as st

# Deep-aware cap for the (expensive, brute-force-referenced) generated-schema gate: a real
# hunt under HYPOTHESIS_PROFILE=deep, a cheap safety net otherwise.
_GATE_MAX_EXAMPLES = 30 if os.environ.get('HYPOTHESIS_PROFILE') == 'deep' else 6

from setengine import ALL_SETOPS, SetEngine
from setengine.memberset import MemberSet
from zanzibar_utils_v1 import (Direct, TTU, Union, Intersection, Exclusion,
                               parse_openfga_schema, parse_schema_ast,
                               derive_schema_info, unparse_schema_ast,
                               UnsupportedByGraphIndex,
                               DoublyBridgedShapeError,
                               wildcard_userset_restriction_shapes)
from tests.oracle import Oracle, OracleTuple
from tests.parity import _GraphSide, _SetSide, GHOST_NAME
from tests.test_hypothesis import schema_asts, _op_pool
from tests.test_matrix import _boolean_pool, _demorgan_pool
from tests.test_wildcard_property import OBJECT_WC, _candidate_raw_tuples


# ---------------------------------------------------------------------------
# Candidate grid, derived from the schema AST + the pool's names
# ---------------------------------------------------------------------------

def _iter_exprs(expr):
    yield expr
    if isinstance(expr, (Union, Intersection)):
        for c in expr.children:
            yield from _iter_exprs(c)
    elif isinstance(expr, Exclusion):
        yield from _iter_exprs(expr.base)
        yield from _iter_exprs(expr.subtract)


def _names_by_type(pool):
    names = {}
    for (_sp, st, sn, _rel, ot, on) in pool:
        if sn != '*':
            names.setdefault(st, set()).add(sn)
        if on != '*':
            names.setdefault(ot, set()).add(on)
    return names


def _subject_candidates(ast, names):
    """(pred, type, name) subjects: Direct-restriction shapes + TTU from-chain
    userset shapes, each over {<=2 pool names, ghost, '*'}."""
    shapes = set()
    for (o_type, _rel), expr in ast.items():
        for node in _iter_exprs(expr):
            if isinstance(node, Direct):
                for r in node.restrictions:
                    shapes.add((r.type, r.predicate))
            elif isinstance(node, TTU):
                tupleset = ast.get((o_type, node.tupleset_rel))
                if tupleset is None:
                    continue
                for leaf in _iter_exprs(tupleset):
                    if isinstance(leaf, Direct):
                        for r in leaf.restrictions:
                            shapes.add((r.type, node.target_rel))
    subjects = []
    for (t, p) in sorted(shapes):
        for n in sorted(names.get(t, set()))[:2] + [GHOST_NAME, '*']:
            subjects.append((p, t, n))
    return subjects


def _object_candidates(ast, names):
    """(relation, type, name) objects: every declared relation over
    {<=2 pool names, ghost, '*'}."""
    objects = []
    for (t, rel) in sorted(ast):
        for n in sorted(names.get(t, set()))[:2] + [GHOST_NAME, '*']:
            objects.append((rel, t, n))
    return objects


# ---------------------------------------------------------------------------
# Graph-side checkers (take the result so the tamper tests can corrupt it)
# ---------------------------------------------------------------------------

def _gnode_id(widx, pred, entity_type, name):
    try:
        return widx.idx.node(pred, entity_type, name, create_if_missing=False).id
    except KeyError:
        return None


def _is_leaf_pred(pred: str) -> bool:
    """Internal leaf-family storage predicate (``rel.idx``). NOT the bare-entity
    sentinel ``'...'``, which also contains dots."""
    return pred != '...' and '.' in pred


def _check_graph_forward(widx, ast, oc, subject, objects, res):
    sp, st, sn = subject
    for nid in res.node_ids:                                    # G2 soundness sweep
        node = widx._node_by_id(nid)
        assert node is not None, f'graph.lookup{subject}: dead node id {nid}'
        if _is_leaf_pred(node.predicate) or (node.type, node.predicate) not in ast:
            continue                     # internal leaf-family storage node (documented)
        assert oc(sp, st, sn, node.predicate, node.type, node.name), (
            f'graph.lookup{subject} leaked {node.type}:{node.name}#{node.predicate} '
            f'(oracle says no access)')
    for (rel, ot, on) in objects:                               # G1 exactness
        expected = oc(sp, st, sn, rel, ot, on)
        marker = (ot, rel, 'all') in res.markers
        if on == '*':
            got = marker
        else:
            nid = _gnode_id(widx, rel, ot, on)
            got = (nid is not None and nid in res.node_ids) or marker
        assert got == expected, (
            f'graph.lookup{subject} vs oracle on {rel} {ot}:{on}: '
            f'graph={got} oracle={expected}')


def _check_graph_reverse(widx, oc, subjects, obj, res):
    rel, ot, on = obj
    markers_any = {(t, p) for (t, p, v) in res.markers if v == 'any'}
    for nid in res.node_ids:                                    # G4 soundness sweep
        node = widx._node_by_id(nid)
        assert node is not None, f'graph.lookup_reverse{obj}: dead node id {nid}'
        assert not _is_leaf_pred(node.predicate), (
            f'graph.lookup_reverse{obj}: internal leaf node '
            f'{node.type}:{node.name}#{node.predicate} leaked into a reverse result')
        assert oc(node.predicate, node.type, node.name, rel, ot, on), (
            f'graph.lookup_reverse{obj} leaked subject '
            f'{node.type}:{node.name}#{node.predicate} (oracle says no access)')
    for nid in res.excluded_node_ids:                           # G4 neg sweep
        node = widx._node_by_id(nid)
        assert node is not None, f'graph.lookup_reverse{obj}: dead excluded id {nid}'
        assert (node.type, node.predicate) in markers_any, (
            f'graph.lookup_reverse{obj}: excluded {node.type}:{node.name} is not '
            f'covered by any marker (neg outside starred shapes)')
        assert not oc(node.predicate, node.type, node.name, rel, ot, on), (
            f'graph.lookup_reverse{obj}: excluded subject {node.type}:{node.name}'
            f'#{node.predicate} is oracle-TRUE (wrong exclusion)')
    for (sp, st, sn) in subjects:                               # G3 exactness
        expected = oc(sp, st, sn, rel, ot, on)
        if sn == '*':
            got = (st, sp) in markers_any
        else:
            nid = _gnode_id(widx, sp, st, sn)
            got = (nid is not None and nid in res.node_ids) or (
                (st, sp) in markers_any
                and not (nid is not None and nid in res.excluded_node_ids))
        assert got == expected, (
            f'graph.lookup_reverse{obj} vs oracle on subject ({sp},{st},{sn}): '
            f'graph={got} oracle={expected}')


# ---------------------------------------------------------------------------
# Set-side checkers
# ---------------------------------------------------------------------------

def _check_set_expand(se, oc, subjects, obj, m):
    rel, ot, on = obj
    for uid in m.pos:                                           # S2 pos sweep
        t, n, p = se.interner.key(uid)
        assert oc(p, t, n, rel, ot, on), (
            f'set.expand{obj} [{se.ops.name}]: pos member {t}:{n}#{p} is oracle-false')
    for uid in m.neg:                                           # S2 neg sweep
        t, n, p = se.interner.key(uid)
        assert (t, p) in m.stars, (
            f'set.expand{obj} [{se.ops.name}]: neg member {t}:{n}#{p} outside stars')
        assert not oc(p, t, n, rel, ot, on), (
            f'set.expand{obj} [{se.ops.name}]: neg member {t}:{n}#{p} is oracle-TRUE')
    for (sp, st, sn) in subjects:                               # S1 exactness
        expected = oc(sp, st, sn, rel, ot, on)
        if sn == '*':
            got = (st, sp) in m.stars
            assert got == expected, (
                f'set.expand{obj} [{se.ops.name}] star shape ({st},{sp}): '
                f'stars={got} oracle={expected}')
            continue
        uid = se.interner.get(st, sn, sp)
        if uid is None:
            # uninterned subject (entity or userset): only star coverage can hold it.
            # Exact since the X3 fix: every oracle-true userset subject is interned
            # (stored tuples intern it; from-chain usersets are write-time interned)
            # or star-covered, so shape-in-stars is the whole answer.
            got = (st, sp) in m.stars
        elif sp == '...':
            got = m.contains_entity(uid, st)
        else:
            got = m.contains_userset(uid, (st, sp))
        assert got == expected, (
            f'set.expand{obj} [{se.ops.name}] vs oracle on subject ({sp},{st},{sn}): '
            f'set={got} oracle={expected}')


def _check_set_reverse(se, oc, subjects, obj, m, res):
    rel, ot, on = obj
    # S3: the documented render of expand (neg dropped)
    assert res.node_ids == set(m.pos), (
        f'set.lookup_reverse{obj} [{se.ops.name}]: node_ids != expand.pos')
    assert res.markers == set(m.stars), (
        f'set.lookup_reverse{obj} [{se.ops.name}]: markers != expand.stars')
    for nid in res.node_ids:                                    # soundness
        t, n, p = se.interner.key(nid)
        assert oc(p, t, n, rel, ot, on), (
            f'set.lookup_reverse{obj} [{se.ops.name}] leaked {t}:{n}#{p}')
    for (sp, st, sn) in subjects:                               # one-sided completeness
        if sn == '*':
            continue                                            # star: pinned via stars in S1
        uid = se.interner.get(st, sn, sp)
        if oc(sp, st, sn, rel, ot, on):
            covered = (uid is not None and uid in res.node_ids) or (st, sp) in res.markers
            assert covered, (
                f'set.lookup_reverse{obj} [{se.ops.name}] dropped oracle-true subject '
                f'({sp},{st},{sn}): not in node_ids and not marker-covered')


def _check_set_forward(se, oc, subject, objects, res):
    sp, st, sn = subject
    for nid in res.node_ids:                                    # S4 soundness
        t, n, p = se.interner.key(nid)
        assert oc(sp, st, sn, p, t, n), (
            f'set.lookup{subject} [{se.ops.name}] leaked {t}:{n}#{p}')
    for (t, p) in res.markers:                                  # S4 marker soundness
        assert oc(sp, st, sn, p, t, '*'), (
            f'set.lookup{subject} [{se.ops.name}]: marker ({t},{p}) is oracle-false '
            f'for the intensional star-object query')
    for (rel, ot, on) in objects:
        expected = oc(sp, st, sn, rel, ot, on)
        if on == '*':
            got = (ot, rel) in res.markers
            assert got == expected, (
                f'set.lookup{subject} [{se.ops.name}] star object ({ot},{rel}): '
                f'marker={got} oracle={expected}')
            continue
        nid = se.interner.get(ot, on, rel)
        covered = (nid is not None and nid in res.node_ids) or (ot, rel) in res.markers
        # Exact over ALL candidates since the X1 fix: every tuple-anchored object
        # key is write-time interned (TTU/Computed reverse deps included), and the
        # only remaining truth source for an uninterned key is star-object
        # coverage, which the intensional markers carry exactly.
        assert covered == expected, (
            f'set.lookup{subject} [{se.ops.name}] vs oracle on {rel} {ot}:{on}: '
            f'set={covered} oracle={expected}')


# ---------------------------------------------------------------------------
# The gate: seeded walk (adds + removals, drained to empty), asserting all
# surfaces on all backends against the oracle after every accepted op
# ---------------------------------------------------------------------------

class _Gate:
    """Graph + both set engines in lockstep, with the full lookup-surface-vs-oracle
    assertion battery runnable at any state."""

    def __init__(self, schema, object_wc, pool):
        self.schema = schema
        ruleset = parse_openfga_schema(schema, object_wildcard_shapes=object_wc)
        self.graph = _GraphSide(ruleset, paranoia=True)
        self.sets = [_SetSide(schema, object_wc, ops) for ops in ALL_SETOPS]
        self.ast = parse_schema_ast(schema)
        names = _names_by_type(pool)
        self.subjects = _subject_candidates(self.ast, names)
        self.objects = _object_candidates(self.ast, names)
        self.derived = self.graph.widx.schema_info.derived_families
        self.present: set[tuple] = set()
        self.history: list[tuple] = []

    def apply(self, op, raw):
        ok = self.graph.apply(raw, op)
        for side in self.sets:
            ok_s = side.apply(raw, op)
            assert ok_s == ok, (
                f'accept/reject divergence on {op} {raw}: graph={ok} {side.name}={ok_s}')
        if ok:
            (self.present.add if op == 'add' else self.present.discard)(raw)
            self.history.append((op, raw))
        return ok

    def assert_surfaces(self, context=''):
        oracle = Oracle(self.schema, [OracleTuple(*r) for r in self.present])
        memo = {}

        def oc(*q):
            if q not in memo:
                memo[q] = oracle.check(*q)
            return memo[q]

        try:
            for subject in self.subjects:
                _check_graph_forward(self.graph.widx, self.ast, oc, subject, self.objects,
                                     self.graph.widx.lookup(*subject))
            for obj in self.objects:
                _check_graph_reverse(self.graph.widx, oc, self.subjects, obj,
                                     self.graph.widx.lookup_reverse(*obj))
            for side in self.sets:
                se = side.se
                for subject in self.subjects:
                    _check_set_forward(se, oc, subject, self.objects, se.lookup(*subject))
                for obj in self.objects:
                    m = se.expand(*obj)
                    _check_set_expand(se, oc, self.subjects, obj, m)
                    _check_set_reverse(se, oc, self.subjects, obj, m, se.lookup_reverse(*obj))
        except AssertionError as e:
            pytest.fail(f'lookup/oracle divergence ({context}): {e}\nhistory:\n'
                        + '\n'.join(f'  {op} {raw}' for op, raw in self.history))

    def close(self):
        self.graph.close()
        for side in self.sets:
            side.close()


def _run_gate(schema, object_wc, pool, seed, walk_steps):
    gate = _Gate(schema, object_wc, pool)
    rng = random.Random(seed)
    present = gate.present

    def apply_all(op, raw):
        return gate.apply(op, raw)

    def assert_state():
        gate.assert_surfaces(context=f'seed={seed}')

    for _ in range(walk_steps):
        cands = [r for r in pool if r not in present]
        if not present or (cands and rng.random() < 0.75):
            op, raw = 'add', rng.choice(cands)
        else:
            op, raw = 'remove', rng.choice(sorted(present))
        if apply_all(op, raw):
            assert_state()

    # drain to empty: removals are where the lookup surfaces were least tested
    while present:
        apply_all('remove', rng.choice(sorted(present)))
        assert_state()

    gate.close()


@pytest.mark.parametrize('seed', [0, 1])
def test_lookup_oracle_gate_wildcards(load_fga_schema, seed):
    """Pure-union wildcard schema: subject stars, userset stars, object wildcards,
    TTU from-chains, recursive group membership."""
    _run_gate(load_fga_schema('wildcards.fga'), OBJECT_WC,
              _candidate_raw_tuples(), seed, walk_steps=8)


@pytest.mark.parametrize('seed', [0, 1])
def test_lookup_oracle_gate_boolean(load_fga_schema, seed):
    """Boolean fixture: exclusion (viewer), intersection (restricted), TTU over a
    derived relation (inherited) -- residues, markers and excluded_node_ids live."""
    _run_gate(load_fga_schema('boolean_wildcards.fga'), frozenset(),
              _boolean_pool(), seed, walk_steps=8)


def test_lookup_oracle_gate_demorgans_reverse(load_fga_schema):
    """Nested exclusions + TTU-over-derived chains (demorgans_reverse.fga)."""
    schema = load_fga_schema('demorgans_reverse.fga')
    _run_gate(schema, frozenset(), _demorgan_pool(schema), seed=0, walk_steps=6)


# ---------------------------------------------------------------------------
# G4 (deviations 2026-07-17): the lookup-surface battery over GENERATED schemas
# (schema_asts, with the G2 concrete-userset leaf) instead of only the 5 handwritten
# fixtures with fixed seeds. A drawn op sequence is applied through the gate's graph +
# both set backends, and the full two-sided surface battery runs after every accepted op.
# Low example count: the brute-force oracle reference is expensive, so this is a safety
# net, not a load test. Object wildcards are not used (schema_asts never emits them), so
# the graph always joins (stratifiable-by-construction => compiles).
#
# Fuzzes the FULL generated schema space (usersets ON, TTU-in-boolean-arm ON). Until
# 2026-07-17 this gate excluded userset leaves + TTU boolean arms (`allow_usersets=False`,
# `ttu_in_boolean=False`) to dodge a graph completeness gap in the X4/D2/upos family:
# userset-subject membership was not fully propagated through a derived relation (graph=False
# where set + oracle=True), needing a userset subject, a derived relation referencing the
# relation that holds the userset, and -- in one variant -- a wildcard star arm or a TTU
# boolean arm. That gap is now FIXED (the ``processor._leaf_concretes`` upos lift, both the
# derived-computed and derived-userset branches) and pinned by strict regression tests
# ``test_graph_from_chain_userset_through_boolean_ttu_arm``,
# ``test_graph_userset_subject_through_derived_wildcard_gap``, and
# ``test_graph_userset_member_through_granted_userset_over_derived`` below, so the exclusion
# is retired. The gate now fuzzes booleans, Computed, whole-definition + boolean-arm TTU, AND
# userset leaves over generated derived schemas on the lookup surfaces (deviations 2026-07-17).
# ---------------------------------------------------------------------------

@settings(max_examples=_GATE_MAX_EXAMPLES, deadline=None,
          suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
@given(ast=schema_asts(), data=st.data())
def test_lookup_oracle_gate_generated_schemas(ast, data):
    pool = _op_pool(ast)
    assume(pool)
    schema = unparse_schema_ast(ast)
    ops = data.draw(st.lists(st.sampled_from(pool), min_size=1, max_size=4, unique=True))
    gate = _Gate(schema, frozenset(), pool)
    try:
        gate.assert_surfaces(context='generated: initial')
        for raw in ops:
            if gate.apply('add', raw):
                gate.assert_surfaces(context=f'generated: after add {raw}')
        for raw in list(gate.present):
            if gate.apply('remove', raw):
                gate.assert_surfaces(context=f'generated: after remove {raw}')
    finally:
        gate.close()


# ---------------------------------------------------------------------------
# N17 corpus: object-wildcard shapes + a STAR-able tupleset ([folder, folder:*]
# parent) + TTU from-chains + a boolean relation, all live at once. This is the
# constellation the N17 wildcard-bridge walk exists for -- the owc shape feeds a
# TTU whose tupleset parent can itself be a star (`folder:*`), the exact triple
# combo the reverse walk cannot reach without the star-parent cross. Kept
# graph-acceptable: the boolean `restricted` uses a separate `editor` arm, so the
# object-wildcard shape closure never lands on a derived family (owc-on-derived
# is a decision-15 graph refusal), letting `_Gate` run the graph backend too.
# ---------------------------------------------------------------------------

OWC_STAR_TTU_SHAPES = frozenset({('folder', 'viewer'), ('doc', 'viewer')})


def _owc_star_ttu_pool() -> list[tuple]:
    """Schema-valid raw tuples for ``owc_star_ttu.fga`` over a small universe,
    combining object wildcards (viewer of ``folder:*``/``doc:*``), a star-able
    tupleset (``folder:*`` as a ``parent`` subject), group usersets, TTU chains and
    the boolean ``restricted``."""
    USERS = ['u1', 'u2']
    FOLDERS = ['f1', 'f2']
    DOCS = ['d1']
    viewer_objs = [('folder', f) for f in FOLDERS] + [('doc', d) for d in DOCS]
    viewer_objs_wc = viewer_objs + [('folder', '*'), ('doc', '*')]
    out = []
    # group membership
    for u in USERS:
        out.append(('...', 'user', u, 'member', 'group', 'g1'))
    # editor + blocked (the boolean's arms; blocked also mentions instances)
    for (ot, on) in viewer_objs:
        for u in USERS:
            out.append(('...', 'user', u, 'editor', ot, on))
        out.append(('member', 'group', 'g1', 'editor', ot, on))
        out.append(('...', 'user', 'u1', 'blocked', ot, on))
    # viewer grants incl. subject-star + object-wildcard objects + group usersets
    for (ot, on) in viewer_objs_wc:
        for u in USERS:
            out.append(('...', 'user', u, 'viewer', ot, on))
        out.append(('...', 'user', '*', 'viewer', ot, on))
        out.append(('member', 'group', 'g1', 'viewer', ot, on))
    # parent hierarchy incl. the STAR tupleset parent (folder:* is a parent)
    out.append(('...', 'folder', 'f1', 'parent', 'folder', 'f2'))
    for d in DOCS:
        out.append(('...', 'folder', 'f1', 'parent', 'doc', d))
        out.append(('...', 'folder', '*', 'parent', 'doc', d))       # star parent
    out.append(('...', 'folder', '*', 'parent', 'folder', 'f2'))     # star parent
    return out


@pytest.mark.parametrize('seed', [0, 1])
def test_lookup_oracle_gate_owc_star_ttu(load_fga_schema, seed):
    """N17 corpus (owc shapes + star tupleset + TTU + boolean), 4-backend two-sided
    vs the oracle after every op -- the fixed-fixture net for the bridge walk."""
    _run_gate(load_fga_schema('owc_star_ttu.fga'), OWC_STAR_TTU_SHAPES,
              _owc_star_ttu_pool(), seed, walk_steps=6)


# ---------------------------------------------------------------------------
# Dense scripted states: the seeded walks may miss specific residue/bridge
# constellations, so these pin them deterministically (attack-first finding:
# an injected neg-drop in the graph's forward residue scan survived the walks
# because no seed had combined a star grant with an exclusion on one object)
# ---------------------------------------------------------------------------

def _run_scripted(schema, object_wc, script):
    gate = _Gate(schema, object_wc, [raw for _op, raw in script])
    for i, (op, raw) in enumerate(script):
        assert gate.apply(op, raw), f'script step {i}: {op} {raw} rejected'
        gate.assert_surfaces(context=f'script step {i}')
    gate.close()


def test_lookup_oracle_dense_boolean(load_fga_schema):
    """Star coverage + exclusion + upos + derived TTU live simultaneously, then
    removed one by one: neg-subtraction and residue-shrink paths always run."""
    _run_scripted(load_fga_schema('boolean_wildcards.fga'), frozenset(), [
        ('add', ('...', 'user', '*', 'public', 'doc', 'd1')),
        ('add', ('...', 'user', '*', 'public', 'doc', 'd2')),
        ('add', ('...', 'user', 'u1', 'blocked', 'doc', 'd1')),   # neg on starred d1
        ('add', ('...', 'user', 'u2', 'editor', 'doc', 'd1')),
        ('add', ('member', 'group', 'g1', 'editor', 'doc', 'd2')),  # upos candidate
        ('add', ('...', 'user', 'u1', 'member', 'group', 'g1')),
        ('add', ('...', 'doc', 'd2', 'parent', 'doc', 'd1')),     # derived TTU feed
        ('remove', ('...', 'user', '*', 'public', 'doc', 'd2')),  # star retires
        ('remove', ('...', 'user', 'u1', 'blocked', 'doc', 'd1')),  # neg retires
        ('remove', ('...', 'user', 'u2', 'editor', 'doc', 'd1')),
        ('remove', ('...', 'doc', 'd2', 'parent', 'doc', 'd1')),
    ])


def test_lookup_oracle_dense_wildcards(load_fga_schema):
    """Subject stars, userset stars, object wildcards and a TTU chain live at
    once, then removed: bridge/w-node GC paths always run."""
    _run_scripted(load_fga_schema('wildcards.fga'), OBJECT_WC, [
        ('add', ('...', 'user', 'u1', 'viewer', 'folder', 'f1')),
        ('add', ('...', 'user', '*', 'viewer', 'folder', 'f1')),  # star + concrete
        ('add', ('member', 'group', '*', 'viewer', 'document', 'd2')),
        ('add', ('...', 'user', 'u2', 'member', 'group', 'g1')),
        ('add', ('...', 'folder', 'f1', 'parent', 'document', 'd1')),  # TTU chain
        ('add', ('...', 'user', 'u1', 'viewer', 'document', '*')),     # object wildcard
        ('add', ('member', 'group', 'g1', 'viewer', 'folder', 'f2')),
        ('remove', ('...', 'user', '*', 'viewer', 'folder', 'f1')),
        ('remove', ('...', 'user', 'u1', 'viewer', 'document', '*')),
        ('remove', ('...', 'folder', 'f1', 'parent', 'document', 'd1')),
        ('remove', ('member', 'group', '*', 'viewer', 'document', 'd2')),
    ])


# ---------------------------------------------------------------------------
# Tamper suite: prove the gate can fail (permanent attack-first evidence)
# ---------------------------------------------------------------------------

def _boolean_reverse_fixture():
    """viewer d1 = star-covered minus alice; bob holds a concrete editor edge."""
    from tests.test_processor import build
    session, widx, proc, write = build('''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define editor: [user]
            define viewer: (public but not blocked) or editor
    ''')
    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
    write('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd1'))
    write('add', ('...', 'user', 'bob', 'editor', 'doc', 'd1'))
    present = [('...', 'user', '*', 'public', 'doc', 'd1'),
               ('...', 'user', 'alice', 'blocked', 'doc', 'd1'),
               ('...', 'user', 'bob', 'editor', 'doc', 'd1')]
    oracle = Oracle('''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define editor: [user]
            define viewer: (public but not blocked) or editor
    ''', [OracleTuple(*r) for r in present])
    subjects = [('...', 'user', 'alice'), ('...', 'user', 'bob'),
                ('...', 'user', GHOST_NAME), ('...', 'user', '*')]
    return session, widx, oracle.check, subjects


def test_tamper_graph_reverse_is_caught():
    session, widx, oc, subjects = _boolean_reverse_fixture()
    obj = ('viewer', 'doc', 'd1')
    res = widx.lookup_reverse(*obj)
    _check_graph_reverse(widx, oc, subjects, obj, res)          # honest result passes

    alice = widx.idx.node('...', 'user', 'alice', create_if_missing=False)

    leak = widx.lookup_reverse(*obj)                            # leaked subject
    leak.node_ids.add(alice.id)
    with pytest.raises(AssertionError):
        _check_graph_reverse(widx, oc, subjects, obj, leak)

    negdrop = widx.lookup_reverse(*obj)                         # skipped neg subtraction
    negdrop.excluded_node_ids.clear()
    with pytest.raises(AssertionError):
        _check_graph_reverse(widx, oc, subjects, obj, negdrop)

    obj_e = ('editor', 'doc', 'd1')                             # dropped concrete subject
    drop = widx.lookup_reverse(*obj_e)
    bob = widx.idx.node('...', 'user', 'bob', create_if_missing=False)
    drop.node_ids.discard(bob.id)
    with pytest.raises(AssertionError):
        _check_graph_reverse(widx, oc, subjects, obj_e, drop)
    session.close()


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
def test_tamper_set_expand_is_caught(ops):
    from sqlmodel import Session, SQLModel, create_engine
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    schema = '''
        type user
        type doc
          relations
            define public: [user, user:*]
            define blocked: [user]
            define viewer: public but not blocked
    '''
    se = SetEngine(session, 'w', schema, ops=ops)
    se.add_tuple('...', 'user', '*', 'public', 'doc', 'd1')
    se.add_tuple('...', 'user', 'alice', 'blocked', 'doc', 'd1')
    se.add_tuple('...', 'user', 'bob', 'public', 'doc', 'd2')   # interns bob
    session.commit()
    oracle = Oracle(schema, [
        OracleTuple('...', 'user', '*', 'public', 'doc', 'd1'),
        OracleTuple('...', 'user', 'alice', 'blocked', 'doc', 'd1'),
        OracleTuple('...', 'user', 'bob', 'public', 'doc', 'd2')])
    subjects = [('...', 'user', 'alice'), ('...', 'user', 'bob'),
                ('...', 'user', GHOST_NAME), ('...', 'user', '*')]
    obj = ('viewer', 'doc', 'd1')

    m = se.expand(*obj)
    _check_set_expand(se, oracle.check, subjects, obj, m)       # honest result passes

    tampered = MemberSet(m.pos, m.stars, se.ops.freeze())       # drop the neg set
    with pytest.raises(AssertionError):
        _check_set_expand(se, oracle.check, subjects, obj, tampered)
    session.close()


# ---------------------------------------------------------------------------
# Genuine divergences found by this gate. Open ones are strict xfails (do NOT
# delete or relax them to make a refactor pass -- fix the underlying surface,
# then flip them); fixed ones stay as plain regression pins of the exact repro.
# ---------------------------------------------------------------------------

def test_set_lookup_forward_ttu_completeness_gap(load_fga_schema):
    """Regression pin for the FIXED gap X1: forward lookup used to enumerate
    candidates from the interned keys only, silently dropping objects reachable
    ONLY via TTU (whose (type,name,relation) key no tuple ever interned) even
    though check() and the graph both answer True. Fixed per spec set-engine
    §6.4 (reverse propagation), realized as write-time reverse-dependency
    interning in ``_apply_add``: the tupleset tuple now interns the dependent
    object key, so the semi-join enumerates and returns it."""
    from sqlmodel import Session, SQLModel, create_engine
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    se = SetEngine(session, 'w', load_fga_schema('wildcards.fga'))
    se.add_tuple('...', 'user', 'u1', 'viewer', 'folder', 'f1')
    se.add_tuple('...', 'folder', 'f1', 'parent', 'document', 'd1')
    session.commit()

    assert se.check('...', 'user', 'u1', 'viewer', 'document', 'd1') is True
    res = se.lookup('...', 'user', 'u1')
    reached = {se.interner.key(i) for i in res.node_ids}
    assert ('document', 'd1', 'viewer') in reached or ('document', 'viewer') in res.markers, \
        'forward lookup dropped a TTU-reachable object that check() grants'


def test_graph_reverse_star_object_on_derived_is_empty(load_fga_schema):
    """Regression pin for the FIXED gap X2: WildcardIndex.lookup_reverse on a
    derived relation with o_name='*' raised ValueError (_get_concrete ->
    core.node reserved-name guard) instead of the empty result that check()
    (False, deviations P7 #3) and the set engine (empty LookupResult) give for
    the same query. Fixed: the derived branch short-circuits o_name='*' to the
    empty result (decision 15: no object-star state can exist)."""
    from tests.test_processor import build
    session, widx, proc, write = build(load_fga_schema('boolean_wildcards.fga'))
    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
    res = widx.lookup_reverse('viewer', 'doc', '*')
    assert res.node_ids == set() and res.markers == set() \
        and res.excluded_node_ids == set()
    session.close()


def test_set_reverse_uninterned_from_chain_userset(load_fga_schema):
    """Regression pin for the FIXED gap X3: expand/lookup_reverse could not
    represent an oracle-true from-chain userset subject because no interned id
    existed for (folder,f1,viewer) when only the parent tuple was stored --
    while check() answered it True via the from-chain rule (engine.py ttu_leaf)
    and the graph lookup_reverse returned its node. Fixed by write-time
    interning of the from-chain userset key (``_apply_add``'s §6.4
    chain-target interning): ``ttu_expand``'s existing singleton path now
    always finds the id, so ``pos`` carries the subject."""
    from sqlmodel import Session, SQLModel, create_engine
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    se = SetEngine(session, 'w', load_fga_schema('wildcards.fga'))
    se.add_tuple('...', 'folder', 'f1', 'parent', 'document', 'd1')
    session.commit()

    assert se.check('viewer', 'folder', 'f1', 'viewer', 'document', 'd1') is True
    res = se.lookup_reverse('viewer', 'document', 'd1')
    reached = {se.interner.key(i) for i in res.node_ids}
    assert ('folder', 'f1', 'viewer') in reached, \
        'lookup_reverse dropped the oracle-true from-chain userset subject'


def test_graph_check_from_chain_userset_on_derived_ttu(load_fga_schema):
    """Regression pin for the FIXED divergence X4a (check-level): on a derived
    TTU, the graph answered the from-chain userset subject itself False where
    the oracle and BOTH set engines answer True (the Zanzibar from-chain rule:
    a stored tupleset parent p makes p#target_rel reach the object; oracle
    ttu_leaf, setengine ttu_leaf) -- while the graph's own UNTAINTED TTU path
    answers the analogous query True via the rewrite edge. Fixed: the delta
    processor's ttu_check/tupleset_ttu_check implement the identity rule, and
    reconcile records node-less from-chain usersets in the residue (interning
    the subject node) so the read surfaces answer them exactly. The removal
    leg pins the round trip: the recording and its anchoring node retire with
    the parent tuple."""
    from tests.test_processor import build
    session, widx, proc, write = build(load_fga_schema('boolean_wildcards.fga'))
    write('add', ('...', 'doc', 'd1', 'parent', 'doc', 'd2'))
    assert widx.check('viewer', 'doc', 'd1', 'inherited', 'doc', 'd2') is True
    # the from-chain subject also appears on the lookup surfaces (G3 exactness)
    subj = widx.idx.node('viewer', 'doc', 'd1', create_if_missing=False)
    assert subj.id in widx.lookup_reverse('inherited', 'doc', 'd2').node_ids
    # and retires with the parent tuple (row-multiset round trip)
    write('remove', ('...', 'doc', 'd1', 'parent', 'doc', 'd2'))
    assert widx.check('viewer', 'doc', 'd1', 'inherited', 'doc', 'd2') is False
    session.close()


def test_graph_check_from_chain_userset_demorgans_reverse(load_fga_schema):
    """The demorgans_reverse.fga reproduction of X4a: a from-chain userset over
    a chain of nested exclusions. After ``role:r1 assigned user:b``,
    check('access','role','r1','access','user','b') was graph-False /
    oracle-True / set-True."""
    from tests.test_processor import build
    session, widx, proc, write = build(load_fga_schema('demorgans_reverse.fga'))
    write('add', ('...', 'role', 'r1', 'assigned', 'user', 'b'))
    assert widx.check('access', 'role', 'r1', 'access', 'user', 'b') is True
    session.close()


def test_graph_check_userset_membership_through_derived_ttu(load_fga_schema):
    """Regression pin for the FIXED divergence X4b (check-level): a userset
    membership was not lifted through a derived TTU. With group:g1#member
    granted editor on doc:d2 and doc:d2 a parent of doc:d1, the graph answered
    check('member','group','g1','viewer','doc','d2') True but the 'inherited'
    query on doc:d1 False; the oracle and both set engines answer True. Fixed:
    the dependent's reconcile now lifts the tainted target's residue ``upos``
    members (edge-free userset memberships, P4) into its own audit set, so its
    ``upos`` receives cross-object userset memberships."""
    from tests.test_processor import build
    session, widx, proc, write = build(load_fga_schema('boolean_wildcards.fga'))
    write('add', ('member', 'group', 'g1', 'editor', 'doc', 'd2'))
    write('add', ('...', 'doc', 'd2', 'parent', 'doc', 'd1'))
    assert widx.check('member', 'group', 'g1', 'viewer', 'doc', 'd2') is True
    # membership flows through the stored parent (oracle + both set engines)
    assert widx.check('member', 'group', 'g1', 'inherited', 'doc', 'd1') is True
    # and retires with the parent tuple
    write('remove', ('...', 'doc', 'd2', 'parent', 'doc', 'd1'))
    assert widx.check('member', 'group', 'g1', 'inherited', 'doc', 'd1') is False
    session.close()


def test_graph_from_chain_userset_through_boolean_ttu_arm():
    """Regression pin for the FIXED from-chain-through-computed-alias divergence
    (X4 family; found by the G4 generated-schema gate, filed 2026-07-17, fixed same
    day). After ``doc:d1 parent doc:d1``, ``doc:d1#r0`` is a member of ``r2`` where
    ``r1: (r0 from parent) and (r0 from parent)`` and ``r2: r1``: the from-chain identity
    rule (a stored tupleset parent ``p`` makes ``p#r0`` a member of ``r0 from parent``)
    grants it, so set engines + oracle answer True.

    The graph already applied that identity for a BARE derived-TTU relation (X4a) and for
    the boolean ``r1`` queried DIRECTLY, but ``check('r0','doc','d1','r2','doc','d1')``
    answered graph=False on exactly this combination: a Computed alias (``r2: r1``) reading
    a boolean relation whose arm is a direct TTU. Root cause: the ``derived-computed``
    branch of ``processor._leaf_concretes`` pulled only edge-justified incoming concretes
    of the aliased relation and never lifted its edge-free userset memberships (residue
    ``upos``, P4), so the from-chain userset the boolean arm computes on the fly never
    reached the alias's audit set. Fixed by the ``_leaf_concretes`` upos lift (the
    ``derived-computed`` branch now merges ``_ttu_target_upos_nodes`` for the aliased
    relation, symmetric to the X4b TTU lift). The direct-TTU arm and the outer Computed
    alias are both load-bearing (either alone is graph-correct)."""
    schema = ('type user\n'
              'type doc\n'
              '  relations\n'
              '    define parent: [doc]\n'
              '    define r0: [user]\n'
              '    define r1: (r0 from parent) and (r0 from parent)\n'
              '    define r2: r1\n')
    rs = parse_openfga_schema(schema)
    graph = _GraphSide(rs, paranoia=True)
    sets = [_SetSide(schema, frozenset(), ops) for ops in ALL_SETOPS]
    write = ('...', 'doc', 'd1', 'parent', 'doc', 'd1')
    query = ('r0', 'doc', 'd1', 'r2', 'doc', 'd1')
    try:
        assert graph.apply(write, 'add') is True
        for s in sets:
            assert s.apply(write, 'add') is True
        oracle = Oracle(schema, [OracleTuple(*write)])
        # The from-chain userset subject IS granted by set engines and the oracle:
        assert oracle.check(*query) is True
        for s in sets:
            assert s.se.check(*query) is True
        # Fixed by the _leaf_concretes upos lift (derived-computed branch):
        assert graph.widx.check(*query) is True
    finally:
        graph.close()
        for s in sets:
            s.close()


def test_graph_userset_subject_through_derived_wildcard_gap():
    """Regression pin for the FIXED userset-subject-through-derived divergence (X4/D2/upos
    family; found by the G4 generated-schema gate + the deep ParityMachine hunt, filed
    2026-07-17, fixed same day). Repro: ``r0`` a wildcard/exclusion relation,
    ``r1: r0 or ([user] or [doc#r0])`` (so a userset subject ``doc:d1#r0`` can be STORED on
    r1 via the ``[doc#r0]`` arm), and ``r3: r1 but not [doc#r1] or [doc#r1]``. After the
    shown writes, ``check('r0','doc','d1','r3','doc','d2')`` answered graph=False where both
    set engines + oracle answer True -- the graph did not lift the userset-subject
    membership of ``r1`` into the dependent ``r3``.

    Root cause: the ``derived-userset`` branch of ``processor._leaf_concretes`` pulled only
    edge-justified incoming concretes on the storage leaf; the members of ``P(X)`` for a
    stored userset ``X`` (here the members of ``r1(doc:d1)`` reached through the ``[doc#r1]``
    arm) are edge-free userset memberships (residue ``upos``, P4) and were never lifted. The
    complex ``r0`` is load-bearing (with ``r0: [user]`` the graph was already correct),
    isolating the userset-subject × wildcard × derived interaction. Fixed by the
    ``_leaf_concretes`` upos lift (the ``derived-userset`` branch now merges
    ``_ttu_target_upos_nodes`` for each stored userset's residue, symmetric to the X4b TTU
    lift). The write ORDER is preserved from the reduced hunter finding."""
    schema = ('type user\n'
              'type doc\n'
              '  relations\n'
              '    define r0: [user:*] or [user:*] but not ([user:*] but not [user, user:*])\n'
              '    define r1: r0 or ([user] or [doc#r0])\n'
              '    define r3: r1 but not [doc#r1] or [doc#r1]\n')
    writes = [('...', 'user', 'u1', 'r0', 'doc', 'd2'),
              ('...', 'user', 'u1', 'r1', 'doc', 'd1'),
              ('r0', 'doc', 'd1', 'r1', 'doc', 'd2')]     # doc:d1#r0 stored on r1
    query = ('r0', 'doc', 'd1', 'r3', 'doc', 'd2')        # is doc:d1#r0 a member of r3@d2?
    rs = parse_openfga_schema(schema)
    graph = _GraphSide(rs, paranoia=True)
    sets = [_SetSide(schema, frozenset(), ops) for ops in ALL_SETOPS]
    try:
        for w in writes:
            assert graph.apply(w, 'add') is True
            for s in sets:
                assert s.apply(w, 'add') is True
        oracle = Oracle(schema, [OracleTuple(*w) for w in writes])
        assert oracle.check(*query) is True
        for s in sets:
            assert s.se.check(*query) is True
        # Fixed by the _leaf_concretes upos lift (derived-userset branch):
        assert graph.widx.check(*query) is True
    finally:
        graph.close()
        for s in sets:
            s.close()


def test_graph_userset_member_through_granted_userset_over_derived():
    """Regression pin for the FIXED userset-member-through-granted-userset-over-derived
    divergence (X4/upos family; found while root-causing the two pins above, filed +
    fixed 2026-07-17). A chain of granted usersets over derived relations:
    ``r0: [user] and [user]``, ``r1: [user] or [doc#r0]``, ``r3: [user] or [doc#r1]``. With
    ``doc:d1#r0`` stored on r1@dx and ``doc:dx#r1`` stored on r3@dy, ``doc:d1#r0`` is a
    member of ``r3@dy`` (it is a member of the granted userset ``doc:dx#r1``, whose
    membership is the edge-free userset set of the derived ``r1``), so oracle + both set
    engines answer True.

    The graph answered False in BOTH write orders: the ``derived-userset`` branch of
    ``processor._leaf_concretes`` never lifted ``P(X)`` for the stored userset ``X`` (edge-
    free residue ``upos``, P4). Fixed by the same ``_leaf_concretes`` upos lift that closed
    the two pins above; pinned in both write orders (fresh backends per order) because the
    gap was state-dependent."""
    schema = ('type user\n'
              'type doc\n'
              '  relations\n'
              '    define r0: [user] and [user]\n'
              '    define r1: [user] or [doc#r0]\n'
              '    define r3: [user] or [doc#r1]\n')
    writes = [('r0', 'doc', 'd1', 'r1', 'doc', 'dx'),    # doc:d1#r0 stored on r1@dx
              ('r1', 'doc', 'dx', 'r3', 'doc', 'dy')]     # doc:dx#r1 stored on r3@dy
    query = ('r0', 'doc', 'd1', 'r3', 'doc', 'dy')        # member of a granted userset over derived r1
    for order in ([0, 1], [1, 0]):
        rs = parse_openfga_schema(schema)
        graph = _GraphSide(rs, paranoia=True)
        sets = [_SetSide(schema, frozenset(), ops) for ops in ALL_SETOPS]
        try:
            for i in order:
                assert graph.apply(writes[i], 'add') is True
                for s in sets:
                    assert s.apply(writes[i], 'add') is True
            oracle = Oracle(schema, [OracleTuple(*w) for w in writes])
            assert oracle.check(*query) is True
            for s in sets:
                assert s.se.check(*query) is True
            # Fixed by the _leaf_concretes upos lift (derived-userset branch):
            assert graph.widx.check(*query) is True
        finally:
            graph.close()
            for s in sets:
                s.close()


# ---------------------------------------------------------------------------
# N17 handwritten regressions: the star-parent / object-wildcard-bridge walk
# scenarios, pinned as SetEngine-vs-oracle forward-lookup exactness (the same
# two-sided S4 checker the gate uses). Several use object wildcards feeding a
# boolean arm -- a decision-15 graph refusal -- so they are set-engine-only (the
# oracle is the independent reference). Constructed after the fixed X-scenarios
# above; do NOT relax these (they pin genuine walk completeness).
# ---------------------------------------------------------------------------

def _assert_set_forward_vs_oracle(schema, object_wc, tuples, *, subjects=None):
    """Build a ``SetEngine`` on ``tuples`` under BOTH ``SetOps`` and assert its
    forward ``lookup`` surface exactly two-sided against the oracle over the
    schema-derived candidate grid (reusing the gate's ``_check_set_forward``)."""
    from sqlmodel import Session, SQLModel, create_engine
    ast = parse_schema_ast(schema)
    names = _names_by_type(tuples)
    subj_grid = subjects if subjects is not None else _subject_candidates(ast, names)
    objects = _object_candidates(ast, names)
    oracle = Oracle(schema, [OracleTuple(*t) for t in tuples])
    memo: dict = {}

    def oc(*q):
        if q not in memo:
            memo[q] = oracle.check(*q)
        return memo[q]

    for ops in ALL_SETOPS:
        engine = create_engine('sqlite:///:memory:')
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            se = SetEngine(session, 'w', schema, object_wildcard_shapes=object_wc, ops=ops)
            for t in tuples:
                se.add_tuple(*t)
            session.commit()
            for subj in subj_grid:
                _check_set_forward(se, oc, subj, objects, se.lookup(*subj))


def _forward_keys(schema, object_wc, tuples, subject, ops=None):
    """(node_id key set, markers, interner-getter) for one forward lookup -- lets a
    regression pin that a concrete surfaces via ``node_ids`` (not just a marker)."""
    from sqlmodel import Session, SQLModel, create_engine
    ops = ops or ALL_SETOPS[0]
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    se = SetEngine(session, 'w', schema, object_wildcard_shapes=object_wc, ops=ops)
    for t in tuples:
        se.add_tuple(*t)
    session.commit()
    res = se.lookup(*subject)
    keys = {se.interner.key(i) for i in res.node_ids}
    interned = se.interner.get
    return keys, res.markers, interned


_STAR_PARENT_SCHEMA = '''
type user
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder, folder:*]
    define viewer: [user] or viewer from parent
'''


def test_reg1_star_bare_parent_from_chain():
    """(1) Commit-1 H3 star-bare fold: a star parent ``folder:* parent doc:d1``
    makes every folder a parent of doc:d1, so a subject that is a viewer of one
    concrete folder inherits viewer on doc:d1. The walk dropped it because
    ``_reverse_neighbors`` folded only the CONCRETE bare parent, not the star bare.
    owc-free schema (the walk ran here even pre-N17)."""
    tuples = [('...', 'folder', '*', 'parent', 'doc', 'd1'),
              ('...', 'user', 'alice', 'viewer', 'folder', 'f1')]
    _assert_set_forward_vs_oracle(_STAR_PARENT_SCHEMA, frozenset(), tuples)
    keys, markers, _ = _forward_keys(_STAR_PARENT_SCHEMA, frozenset(), tuples,
                                     ('...', 'user', 'alice'))
    assert ('doc', 'd1', 'viewer') in keys and ('doc', 'viewer') not in markers


_OWC_TTU_SCHEMA = '''
type user
type folder
  relations
    define parent: [folder, folder:*]
    define viewer: [user, user:*] or viewer from parent
type doc
  relations
    define parent: [folder, folder:*]
    define viewer: [user, user:*] or viewer from parent
'''
_OWC_TTU_SHAPES = frozenset({('folder', 'viewer'), ('doc', 'viewer')})


def test_reg2_owc_ttu_downstream_two_hops():
    """(2) The original owc x TTU bug shape, now WALKED: an object-wildcard grant
    ``alice viewer folder:*`` makes alice a viewer of every concrete folder, and a
    stored ``folder:f1 parent doc:d1`` inherits that onto doc:d1#viewer (2 hops:
    folder:* star node -> bridged folder:f1#viewer -> doc:d1#viewer)."""
    tuples = [('...', 'user', 'alice', 'viewer', 'folder', '*'),      # owc grant
              ('...', 'folder', 'f1', 'parent', 'doc', 'd1')]
    _assert_set_forward_vs_oracle(_OWC_TTU_SCHEMA, _OWC_TTU_SHAPES, tuples)
    keys, _, _ = _forward_keys(_OWC_TTU_SCHEMA, _OWC_TTU_SHAPES, tuples,
                               ('...', 'user', 'alice'))
    assert ('doc', 'd1', 'viewer') in keys


_OWC_LIFT_SCHEMA = '''
type user
type folder
  relations
    define viewer: [user, user:*]
type doc
  relations
    define editor: [folder#viewer]
'''


def test_reg3_owc_nonwildcard_userset_lift():
    """(3) owc x NON-wildcard userset lift: a stored ``folder:f1#viewer editor
    doc:d1`` lifts folder:f1#viewer's members onto doc:d1#editor, and alice's ONLY
    route into folder:f1#viewer is the object wildcard ``alice viewer folder:*``.
    The bridge enqueues the interned folder:f1#viewer (ids_of_shape), then H1
    fan-in reaches doc:d1#editor."""
    tuples = [('...', 'user', 'alice', 'viewer', 'folder', '*'),          # owc grant
              ('viewer', 'folder', 'f1', 'editor', 'doc', 'd1')]          # userset lift
    _assert_set_forward_vs_oracle(_OWC_LIFT_SCHEMA, frozenset({('folder', 'viewer')}), tuples)
    keys, _, _ = _forward_keys(_OWC_LIFT_SCHEMA, frozenset({('folder', 'viewer')}),
                               tuples, ('...', 'user', 'alice'))
    assert ('doc', 'd1', 'editor') in keys


_OWC_BOOL_SCHEMA = '''
type user
type folder
  relations
    define parent: [folder, folder:*]
    define blocked: [user]
    define public: [user]
    define viewer: [user, user:*] or viewer from parent
    define both: viewer and public
type doc
  relations
    define parent: [folder, folder:*]
    define blocked: [user]
    define viewer: [user, user:*] or viewer from parent
    define guarded: viewer but not blocked
'''
_OWC_BOOL_SHAPES = frozenset({('folder', 'viewer'), ('doc', 'viewer')})


def test_reg4a_owc_boolean_intersection_arm():
    """(4a) owc feeding an intersection ``both = viewer and public``: the star grant
    lands on viewer's shape, ``public`` is stored at ONE concrete (folder:f1). That
    concrete must surface via node_ids, and NO ``both`` marker exists (the marker is
    false: public is not granted at the star object folder:*). Set-engine-only (owc
    closes onto the derived ``both`` -- a graph refusal)."""
    tuples = [('...', 'user', 'alice', 'viewer', 'folder', '*'),   # owc grant on viewer
              ('...', 'user', 'alice', 'public', 'folder', 'f1')]  # public at one concrete
    _assert_set_forward_vs_oracle(_OWC_BOOL_SCHEMA, _OWC_BOOL_SHAPES, tuples)
    keys, markers, _ = _forward_keys(_OWC_BOOL_SCHEMA, _OWC_BOOL_SHAPES, tuples,
                                     ('...', 'user', 'alice'))
    assert ('folder', 'f1', 'both') in keys and ('folder', 'both') not in markers


def test_reg4b_owc_boolean_exclusion_arm():
    """(4b) owc feeding an exclusion ``guarded = viewer but not blocked`` on doc,
    reached via the star parent (so viewer -- hence guarded -- is FALSE at the star
    object doc:*, keeping the guarded marker false per S4). alice is a viewer of
    every doc via ``folder:* parent`` + owc-on-folder; blocking doc:d1 must keep
    doc:d1#guarded OUT while doc:d2#guarded surfaces. Set-engine-only."""
    tuples = [('...', 'user', 'alice', 'viewer', 'folder', '*'),   # owc on folder viewer
              ('...', 'folder', '*', 'parent', 'doc', 'd1'),       # star parents
              ('...', 'folder', '*', 'parent', 'doc', 'd2'),
              ('...', 'user', 'x', 'blocked', 'folder', 'f1'),     # mentions folder:f1 instance
              ('...', 'user', 'alice', 'blocked', 'doc', 'd1')]    # ban d1
    _assert_set_forward_vs_oracle(_OWC_BOOL_SCHEMA, _OWC_BOOL_SHAPES, tuples)
    keys, markers, _ = _forward_keys(_OWC_BOOL_SCHEMA, _OWC_BOOL_SHAPES, tuples,
                                     ('...', 'user', 'alice'))
    assert ('doc', 'd2', 'guarded') in keys                         # unbanned surfaces
    assert ('doc', 'd1', 'guarded') not in keys                     # banned excluded
    assert ('doc', 'guarded') not in markers                        # marker stays false


def test_reg5_triple_combo_star_parent_cross_no_concrete():
    """(5) Triple combo owc x star-parent x TTU with NO concrete (folder,X,viewer)
    interned -- exercises the bridge's star-parent cross (step 2). folder:f1 is
    mentioned only via a ``blocked`` tuple, so folder:f1#viewer is never interned;
    the ONLY route to doc:d1#viewer is the star-parent cross over member_of of the
    star bare folder:* crossed with the doc TTU."""
    tuples = [('...', 'user', 'alice', 'viewer', 'folder', '*'),   # owc grant
              ('...', 'folder', '*', 'parent', 'doc', 'd1'),       # star bare parent
              ('...', 'user', 'x', 'blocked', 'folder', 'f1')]     # mention f1 (no viewer intern)
    _assert_set_forward_vs_oracle(_OWC_BOOL_SCHEMA, _OWC_BOOL_SHAPES, tuples)
    keys, _, interned = _forward_keys(_OWC_BOOL_SCHEMA, _OWC_BOOL_SHAPES, tuples,
                                      ('...', 'user', 'alice'))
    assert interned('folder', 'f1', 'viewer') is None              # step-2, not step-1
    assert ('doc', 'd1', 'viewer') in keys


_OWC_CHAIN_SCHEMA = '''
type user
type folder
  relations
    define viewer: [user, user:*]
type doc
  relations
    define viewer: [user, user:*, folder#viewer]
'''
_OWC_CHAIN_SHAPES = frozenset({('folder', 'viewer'), ('doc', 'viewer')})


def test_reg6_shape_chaining():
    """(6) Shape chaining: the shape-1 injection (owc ``alice viewer folder:*``)
    makes alice a member of the stored userset ``folder:f1#viewer``, which is granted
    viewer on the doc wildcard object (shape-2's star). Reaching doc:*#viewer must
    fire the DOC bridge, surfacing the mentioned concrete doc:d1#viewer."""
    tuples = [('...', 'user', 'alice', 'viewer', 'folder', '*'),        # shape-1 owc
              ('viewer', 'folder', 'f1', 'viewer', 'doc', '*'),         # userset -> doc:* (shape-2)
              ('...', 'user', 'z', 'viewer', 'doc', 'd1')]              # mention doc:d1
    _assert_set_forward_vs_oracle(_OWC_CHAIN_SCHEMA, _OWC_CHAIN_SHAPES, tuples)
    keys, _, _ = _forward_keys(_OWC_CHAIN_SCHEMA, _OWC_CHAIN_SHAPES, tuples,
                               ('...', 'user', 'alice'))
    assert ('doc', 'd1', 'viewer') in keys


_OWC_GHOST_SCHEMA = '''
type user
type folder
  relations
    define viewer: [user, user:*]
'''


def test_reg7_ghost_subject_via_subject_star():
    """(7) A ghost (uninterned) subject covered only by a ``[user:*]`` subject-wildcard
    grant, on an owc schema: ``user:* viewer folder:f1`` makes every user (including a
    ghost) a viewer of folder:f1. The seed resolves the ghost's star sibling
    (user:* bare) via ``_reverse_neighbors_key`` H1 star coverage."""
    tuples = [('...', 'user', '*', 'viewer', 'folder', 'f1')]
    _assert_set_forward_vs_oracle(_OWC_GHOST_SCHEMA, frozenset({('folder', 'viewer')}), tuples)
    keys, markers, _ = _forward_keys(_OWC_GHOST_SCHEMA, frozenset({('folder', 'viewer')}),
                                     tuples, ('...', 'user', 'zz-ghost-user'))
    assert ('folder', 'f1', 'viewer') in keys


def test_reg8_bridge_tuple_add_remove_roundtrip():
    """(8) add -> assert -> remove -> assert: the walk is stateless, so removing the
    bridge tuples (which releases the interner refs and scrubs ids_of_shape /
    member_of) must leave the walk surfacing nothing. Pins interner-release /
    ids_of_shape maintenance on the star-parent cross state (regression 5)."""
    from sqlmodel import Session, SQLModel, create_engine
    add_tuples = [('...', 'user', 'alice', 'viewer', 'folder', '*'),
                  ('...', 'folder', '*', 'parent', 'doc', 'd1'),
                  ('...', 'user', 'x', 'blocked', 'folder', 'f1')]
    for ops in ALL_SETOPS:
        engine = create_engine('sqlite:///:memory:')
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            se = SetEngine(session, 'w', _OWC_BOOL_SCHEMA,
                           object_wildcard_shapes=_OWC_BOOL_SHAPES, ops=ops)
            for t in add_tuples:
                se.add_tuple(*t)
            session.commit()
            res = se.lookup('...', 'user', 'alice')
            assert ('doc', 'd1', 'viewer') in {se.interner.key(i) for i in res.node_ids}
            for t in add_tuples:
                se.remove_tuple(*t)
            session.commit()
            res2 = se.lookup('...', 'user', 'alice')
            assert res2.node_ids == set() and res2.markers == set()
            # interner fully drained (no leaked bridge/dep candidate ids)
            assert se.interner.get('doc', 'd1', 'viewer') is None
            assert se.interner.get('folder', '*', '...') is None


def test_reg9_same_type_star_parent_accept_reject_parity(load_fga_schema):
    """(9) Accept/reject parity on star tupleset parents (found by the seed-7 fuzz
    sweep on the owc_star_ttu corpus). A SAME-TYPE star parent (`folder:* parent
    folder:f2`) routes via the TTU rewrite's through-shape to `folder:*#viewer
    viewer folder:f2` -- a wildcard tuple whose object participates in the
    wildcard's own shape, which the graph rejects by construction (in-bridge +
    grant = two-cycle). The set engine's raw-level same-shape check could not see
    it (the raw subject is bare), so it ACCEPTED -- an accept/reject divergence.
    Pins: both backends reject same-type, both accept cross-type."""
    from tests.test_matrix import GraphBackend, SetBackend
    schema = load_fga_schema('owc_star_ttu.fga')
    same_type = ('...', 'folder', '*', 'parent', 'folder', 'f2')
    cross_type = ('...', 'folder', '*', 'parent', 'doc', 'd1')
    backends = [GraphBackend(schema, OWC_STAR_TTU_SHAPES)] + [
        SetBackend(schema, OWC_STAR_TTU_SHAPES, ops) for ops in ALL_SETOPS]
    try:
        for b in backends:
            assert b.apply(same_type, 'add') is False, (
                f'{b.name} accepted the same-type star parent (routed same-shape '
                f'wildcard self-reference; graph rejects it by construction)')
            assert b.apply(cross_type, 'add') is True, (
                f'{b.name} rejected the acyclic cross-type star parent')
    finally:
        for b in backends:
            b.close()


REG10_SCHEMA = """model
  schema 1.1
type user
type folder
  relations
    define parent: [folder, folder:*]
    define admin: [user, folder:*#admin, folder#viewer]
    define viewer: [user] or admin from parent
"""


def test_reg10_multihop_star_bridge_cycle_accept_reject_parity():
    """(10) MULTI-HOP generalization of reg9: a cycle that closes only through a
    materialized subject-wildcard IN-bridge. W1 (`folder:* parent folder:c`) mints the
    derived edge `w_any(folder,admin) -> folder:c#viewer` (via the TTU rewrite); W2
    (`folder:c#viewer admin folder:y`) adds `folder:c#viewer -> folder:y#admin`. The
    shape (folder, admin) is a subject-wildcard USERSET shape, so the concrete
    `folder:y#admin` carries an IN-bridge to `w_any(folder,admin)`, closing
    `folder:c#viewer -> folder:y#admin ->[in-bridge] w_any(folder,admin) ->
    folder:c#viewer`. The graph REJECTS W2 as a cycle; the set engine's flow graph is
    now bridge-aware (mirrors index_v4/wildcard.py `_ensure_bridges`) so it rejects it
    too. Pins accept/reject parity (no ParityEngine): both backends reject W2 after W1,
    and an acyclic control (W1 present, a DIFFERENT viewer subject that never returns to
    the loop) is accepted by both."""
    from tests.test_matrix import GraphBackend, SetBackend
    W1 = ('...', 'folder', '*', 'parent', 'folder', 'c')       # folder:*  parent  folder:c
    W2 = ('viewer', 'folder', 'c', 'admin', 'folder', 'y')     # folder:c#viewer admin folder:y (cycle)
    # Acyclic control: same W1, but the admin grant is FROM a different viewer subject
    # (folder:d#viewer). Its IN-bridge still reaches w_any(folder,admin) -> folder:c#viewer,
    # but folder:c#viewer never returns to folder:d#viewer, so no loop closes.
    CTRL = ('viewer', 'folder', 'd', 'admin', 'folder', 'y')   # folder:d#viewer admin folder:y (acyclic)

    for W2_case, expect, label in ((W2, False, 'cycle'), (CTRL, True, 'acyclic control')):
        backends = [GraphBackend(REG10_SCHEMA)] + [
            SetBackend(REG10_SCHEMA, frozenset(), ops) for ops in ALL_SETOPS]
        try:
            for b in backends:
                assert b.apply(W1, 'add') is True, (
                    f'{b.name} rejected the star parent W1 ({label} case)')
                assert b.apply(W2_case, 'add') is expect, (
                    f'{b.name} disagreed on the {label} admin grant '
                    f'(expected {"accept" if expect else "reject"})')
        finally:
            for b in backends:
                b.close()


# The object-wildcard / OUT-bridge analog of reg10. Where reg10 closes a cycle through
# a subject-wildcard IN-bridge (concrete -> w_any), this closes one through an
# object-wildcard OUT-bridge (w_all -> concrete). Object wildcards have no DSL syntax, so
# the shape is enabled via ``object_wildcard_shapes``: ``(folder, parent)`` lets a tuple's
# OBJECT be ``folder:*`` and ``(folder, viewer)`` gives ``w_all(folder, viewer)`` its
# out-bridges to concrete viewer nodes.
REG11_OWC_SHAPES = frozenset({('folder', 'viewer'), ('folder', 'parent')})
REG11_SCHEMA = """model
  schema 1.1
type user
type folder
  relations
    define parent: [folder, folder:*]
    define viewer: [user] or viewer from parent
"""


def test_reg11_out_bridge_object_wildcard_self_cycle_accept_reject_parity():
    """(11) The OUT-bridge mirror of reg10 (object-wildcard analog). Writing
    ``folder:a parent folder:*`` routes via the ``viewer from parent`` TTU to the derived
    edge ``folder:a#viewer -> folder:*#viewer``; the star object ``folder:*#viewer`` is an
    OBJECT-wildcard shape, so it carries a materialized OUT-bridge
    ``w_all(folder,viewer) -> folder:a#viewer``, closing the two-cycle
    ``folder:a#viewer -> w_all(folder,viewer) ->[out-bridge] folder:a#viewer``. The graph
    REJECTS it; the set engine's flow graph is now OUT-bridge-aware (``_flow_reaches``
    steps ``w_all(T,p) -> concrete`` for ``bridged_out_shapes``) so it rejects it too --
    without that branch the set engine ACCEPTS while the graph rejects (verified: blinding
    ``bridged_out_shapes`` to empty flips this write to accepted). Pins accept/reject
    parity on the out-bridge branch (reg10 exercises only the in-bridge branch), plus an
    acyclic control (a concrete parent ``folder:a parent folder:b`` -- no star object, no
    bridge) accepted by both.

    Note: only this SINGLE-hop out-bridge self-cycle is realizable; the multi-hop
    generalization of reg10 is unreachable in this direction. Any derived edge INTO
    ``w_all(T,p)`` is minted by a ``T:x <tupleset> T:*`` write whose own subject is a
    same-shape concrete ``T:x#p``, which the out-bridge immediately reaches back -- so such
    a write always self-cycles at admission and can never persist for a later write to
    build a longer loop on (verified: writing ``folder:b parent folder:a`` first, then
    ``folder:a parent folder:*`` is still rejected on the second write, by both backends)."""
    from tests.test_matrix import GraphBackend, SetBackend
    W_OUT = ('...', 'folder', 'a', 'parent', 'folder', '*')   # object star -> out-bridge self-cycle
    CTRL = ('...', 'folder', 'a', 'parent', 'folder', 'b')    # concrete parent -> acyclic

    for W_case, expect, label in ((W_OUT, False, 'out-bridge cycle'),
                                  (CTRL, True, 'acyclic control')):
        backends = [GraphBackend(REG11_SCHEMA, REG11_OWC_SHAPES)] + [
            SetBackend(REG11_SCHEMA, REG11_OWC_SHAPES, ops) for ops in ALL_SETOPS]
        try:
            for b in backends:
                assert b.apply(W_case, 'add') is expect, (
                    f'{b.name} disagreed on the {label} parent write '
                    f'(expected {"accept" if expect else "reject"})')
        finally:
            for b in backends:
                b.close()


# ===========================================================================
# reg12 -- doubly-bridged shape rejection (F1/F2 CLOSED, 2026-07-17)
# ===========================================================================
#
# The star-bridge fuzzer surfaced two latent divergences (docs/spec-deviations.md
# 2026-07-16 "two new latent OWC divergences" + the 2026-07-17 CLOSED entry). Both
# need a shape (T,p) that is SIMULTANEOUSLY a wildcard-userset shape (a `T:*#p`
# restriction -> bridged_in_shapes) and an object-wildcard shape (bridged_out_shapes)
# -- the "doubly-bridged" precondition. When such a shape exists, wildcard writes
# materialize a `w_any(T,p) -> w_all(T,p)` path; every present-or-future concrete node
# of that shape carries both bridges (concrete->w_any in, w_all->concrete out), so the
# path is a latent CYCLE:
#   * F1: graph `check` returns False where set + oracle say True (completeness gap);
#   * F2: graph accepts a wildcard self-reference the set engine rejects;
#   * DETONATION (both): after the wildcard write is accepted, the graph's _ensure_bridges
#     closes the cycle, so every later INNOCENT concrete write of that shape is
#     permanently graph-REJECTED (set + oracle accept) -- a 3rd divergence and the
#     reason the state must be unconstructible, not merely papered over at read time.
# Fix: reject at COMPILE (DoublyBridgedShapeError, the third decision-15 scope
# rejection; OpenFGA supports neither wildcard usersets nor object-wildcard tuple
# objects). BOTH backends must reject identically -- the graph via parse_openfga_schema,
# the set engine by re-raising the subclass (the other scope rejections it swallows into
# an oracle-only mode; this one it must refuse). See docs/spec-deviations.md 2026-07-17.

def _assert_doubly_bridged_rejected(schema, owc, expect_shape):
    """Both backends must raise DoublyBridgedShapeError at CONSTRUCTION."""
    from tests.test_matrix import _fresh_session
    # DoublyBridgedShapeError is a subclass of UnsupportedByGraphIndex, so external
    # graph-optional catchers still degrade -- but it is its OWN type so the set engine
    # can re-raise it (both backends reject identically).
    assert issubclass(DoublyBridgedShapeError, UnsupportedByGraphIndex)
    with pytest.raises(DoublyBridgedShapeError, match=expect_shape):
        parse_openfga_schema(schema, object_wildcard_shapes=owc)
    with pytest.raises(DoublyBridgedShapeError, match=expect_shape):
        SetEngine(_fresh_session(), 'w', schema, object_wildcard_shapes=owc)


# --- F1: the graph-incomplete + detonation repro ---
F1_SCHEMA = """model
  schema 1.1
type user
type folder
  relations
    define parent: [folder, folder:*]
    define viewer: [user, folder:*#viewer, folder#admin]
    define admin: [user] or viewer from parent
"""
F1_OWC = frozenset({('folder', 'parent'), ('folder', 'viewer')})


def test_reg12_f1_doubly_bridged_rejected_both_backends():
    """F1: `(folder, viewer)` is declared both a wildcard-userset shape (folder:*#viewer)
    and an object-wildcard shape (F1_OWC). The compiler also propagates (folder, admin)
    into object_wildcard_shapes (TTU head), but (folder, viewer) is already doubly-bridged
    at declaration. Both backends reject at construction."""
    _assert_doubly_bridged_rejected(F1_SCHEMA, F1_OWC, r'folder, viewer')


# --- F2: the graph-over-permissive + detonation repro ---
F2_SCHEMA = """model
  schema 1.1
type user
type folder
  relations
    define viewer: [user]
    define admin: [user, folder:*#admin, folder#viewer]
"""
F2_OWC = frozenset({('folder', 'admin')})


def test_reg12_f2_doubly_bridged_rejected_both_backends():
    """F2: `(folder, admin)` is both a wildcard-userset shape (folder:*#admin) and a
    declared object-wildcard shape. Both backends reject at construction."""
    _assert_doubly_bridged_rejected(F2_SCHEMA, F2_OWC, r'folder, admin')


# --- Propagation-derived: the user never declares the intersecting shape ---
# `viewer` carries the folder:*#viewer wildcard userset (so (folder,viewer) is a
# wildcard-userset shape); the user declares object-wildcard ONLY on (folder,parent).
# `_expand_object_wildcard_shapes` closes the OWC set over the `viewer from parent` TTU
# head, ADDING (folder,viewer) to object_wildcard_shapes -- which makes it doubly-bridged
# even though the user never asked for an object wildcard on viewer.
P_SCHEMA = """model
  schema 1.1
type user
type folder
  relations
    define parent: [folder, folder:*]
    define viewer: [user, folder:*#viewer] or viewer from parent
"""
P_OWC = frozenset({('folder', 'parent')})


def test_reg12_propagation_derived_doubly_bridged_rejected():
    """The intersection is created by compiler PROPAGATION, not by the user. Verify
    empirically that expansion puts (folder, viewer) into object_wildcard_shapes, and
    that both backends then reject."""
    # Unexpanded derive: the intersection does NOT yet exist (bridged_out is parent-only).
    ast = parse_schema_ast(P_SCHEMA)
    raw = derive_schema_info(ast, P_OWC)
    assert ('folder', 'viewer') in raw.bridged_in_shapes
    assert ('folder', 'viewer') not in raw.object_wildcard_shapes
    assert not (frozenset(raw.bridged_in_shapes) & frozenset(raw.bridged_out_shapes)), (
        'unexpanded schema_info must NOT be doubly-bridged -- the intersection is '
        'purely propagation-derived (proving the check must run post-expansion)')
    # Both backends reject after expansion propagates (folder, viewer) into the OWC set.
    _assert_doubly_bridged_rejected(P_SCHEMA, P_OWC, r'folder, viewer')


# --- Negative controls: rich-but-legal star-bridge schemas still compile ---
def test_reg12_negative_controls_reg10_reg11_not_doubly_bridged():
    """reg10 (subject-wildcard IN-bridge, no OWC) and reg11 (object-wildcard OUT-bridge,
    OWC declared) are legal star-bridge schemas: their doubly-bridged set is EMPTY, so
    they compile fine on both backends (their existing reg10/reg11 parity tests still
    pass). The doubly-bridged LEFT FACTOR is the set of LITERAL wildcard-userset
    restrictions (writable T:*#p), NOT the full bridged_in_shapes:

      * reg10's (folder, admin) IS a literal wildcard-userset (folder:*#admin) but has
        no object wildcard (OWC empty) -> intersection empty.
      * reg11 has NO literal wildcard-userset restriction at all -- its (folder, viewer)
        lands in bridged_in only as a STAR-TUPLESET THROUGH-SHAPE (from [folder:*] on the
        TTU tupleset `parent`), which is not a writable userset and cannot mint a
        persistent w_any node, so it does not detonate. Using the full bridged_in_shapes
        here would over-reject reg11 (verified: bridged_in ∩ bridged_out is NON-empty for
        reg11, but the narrow literal-restriction ∩ bridged_out is empty)."""
    # reg10: literal wildcard-userset (folder, admin), but no OWC -> empty intersection.
    rs10 = parse_openfga_schema(REG10_SCHEMA, object_wildcard_shapes=frozenset())
    si10 = rs10.schema_info
    lit10 = wildcard_userset_restriction_shapes(parse_schema_ast(REG10_SCHEMA))
    assert ('folder', 'admin') in lit10                            # literal T:*#admin
    assert not (lit10 & frozenset(si10.bridged_out_shapes))
    # reg11: NO literal wildcard-userset -> empty intersection despite the coarse overlap.
    rs11 = parse_openfga_schema(REG11_SCHEMA, object_wildcard_shapes=REG11_OWC_SHAPES)
    si11 = rs11.schema_info
    lit11 = wildcard_userset_restriction_shapes(parse_schema_ast(REG11_SCHEMA))
    assert lit11 == frozenset()                                    # no writable T:*#p
    assert not (lit11 & frozenset(si11.bridged_out_shapes))
    # The coarse bridged_in ∩ bridged_out IS non-empty for reg11 -- documenting why the
    # narrow left factor is required (the reg11 test must keep passing).
    assert ('folder', 'viewer') in (frozenset(si11.bridged_in_shapes)
                                    & frozenset(si11.bridged_out_shapes))


# --- The ghost-hop safeguard never fires on legal schemas ---
def test_reg12_ghost_hop_never_fires_on_legal_star_bridges():
    """The set-engine flow-graph ghost hop (w_all->w_any for doubly-bridged shapes) is a
    defense-in-depth safeguard: post-rejection its trigger set is always empty. Build
    SetEngines on the rich-but-legal reg10/reg11 star-bridge schemas, replay their write
    sequences (including the rejected cycle-forming writes, which is exactly when the flow
    reachability walk runs), and assert the ghost hop NEVER fired and doubly_bridged is
    empty."""
    from tests.test_matrix import _fresh_session
    # reg10: subject-wildcard IN-bridge class, no OWC.
    for ops in ALL_SETOPS:
        se = SetEngine(_fresh_session(), 'w', REG10_SCHEMA, ops=ops)
        assert se.doubly_bridged == frozenset()
        se.add_tuple('...', 'folder', '*', 'parent', 'folder', 'c')     # W1 accepted
        with pytest.raises(ValueError):
            se.add_tuple('viewer', 'folder', 'c', 'admin', 'folder', 'y')  # W2 cycle-rejected
        assert se._ghost_hop_fired is False
    # reg11: object-wildcard OUT-bridge class, OWC declared.
    for ops in ALL_SETOPS:
        se = SetEngine(_fresh_session(), 'w', REG11_SCHEMA,
                       object_wildcard_shapes=REG11_OWC_SHAPES, ops=ops)
        assert se.doubly_bridged == frozenset()
        with pytest.raises(ValueError):
            se.add_tuple('...', 'folder', 'a', 'parent', 'folder', '*')  # out-bridge cycle-rejected
        se.add_tuple('...', 'folder', 'a', 'parent', 'folder', 'b')      # acyclic control accepted
        assert se._ghost_hop_fired is False


# ===========================================================================
# reg13 -- no-restriction-match write: accept/reject parity (2026-07-17)
# ===========================================================================
#
# Scout-flagged accept/reject divergence: `group:*#member editor doc:d1` -- a
# WILDCARD-userset subject (group:*#member) against a CONCRETE [group#member]
# restriction -- was ACCEPTED by the graph backend and REJECTED by the set engine.
#
# Root cause (adjudicated): a general graph-admission wart, NOT specific to wildcard
# usersets. `RuleSet.apply` (the graph's raw-write routing) SILENTLY DROPPED any raw
# tuple matching no declared type restriction (the pure-union `else: return` branch),
# so the graph harnesses (GraphBackend/_GraphSide) reported True having written
# nothing -- a VACUOUS accept. The set engine's `_validate` step 2 RAISES ValueError
# on the same tuple. Same class as the derived-family branch of `RuleSet.apply`, which
# already RAISED. Answers were never affected (0 routed triples, 0 stored rows, every
# downstream check False on all backends) -- purely a unanimity break, for ANY
# no-restriction-match write (wrong subject type / predicate, wildcard userset under a
# concrete restriction, nonexistent relation, ...).
#
# Adjudication: the set engine's rejection is correct (OpenFGA rejects a tuple matching
# no type restriction; the answer -- no grant -- is what both backends already agreed
# on). The graph should reject too. Fix (zanzibar_utils_v1.py `RuleSet.apply`): the
# pure-union no-match branch RAISES ValueError for schema-derived rulesets (schema_info
# is not None), mirroring the set engine; hand-built rulesets keep silent-drop filter
# semantics. See docs/spec-deviations.md 2026-07-17.

REG13_TAINTED_SCHEMA = """model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define editor: [user, group#member]
    define viewer: (editor) or editor
"""  # `viewer` boolean-taints `editor`; editor's restriction stays concrete [group#member]

REG13_DECLARED_STAR_SCHEMA = """model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define editor: [user, group#member, group:*#member]
"""  # declares the wildcard userset [group:*#member] -> group:*#member is admissible

REG13_USERSTAR_SCHEMA = """model
  schema 1.1
type user
type doc
  relations
    define public: [user:*]
    define blocked: [user]
"""  # public declares [user:*]; blocked does not


def _reg13_unanimous(schema, raw, expect, owc=frozenset()):
    """Every backend (graph + both set ops) must agree accept/reject on `raw`."""
    from tests.test_matrix import GraphBackend, SetBackend
    backends = [GraphBackend(schema, owc)] + [
        SetBackend(schema, owc, ops) for ops in ALL_SETOPS]
    try:
        for b in backends:
            got = b.apply(raw, 'add')
            assert got is expect, (
                f'{b.name} {"accepted" if got else "rejected"} {raw} '
                f'(expected {"accept" if expect else "reject"})')
    finally:
        for b in backends:
            b.close()


def test_reg13_wildcard_userset_under_concrete_restriction_rejected_both():
    """Prong 1 (the reported divergence): group:*#member (wildcard userset) against a
    concrete [group#member] restriction on a boolean-tainted `editor` is REJECTED by
    BOTH backends. Pre-fix: graph accepted (silent drop) / set rejected."""
    _reg13_unanimous(REG13_TAINTED_SCHEMA,
                     ('member', 'group', '*', 'editor', 'doc', 'd1'), False)


def test_reg13_no_restriction_match_variants_rejected_both():
    """The divergence class is general -- ANY no-restriction-match raw write is rejected
    by both backends (not just the wildcard-userset instance): wrong subject type, wrong
    userset predicate, bare write to a userset-only shape, nonexistent relation."""
    for raw in (
        ('foo', 'doc', 'x', 'editor', 'doc', 'd1'),      # wrong subject type (userset)
        ('...', 'doc', 'x', 'editor', 'doc', 'd1'),      # wrong subject type (bare)
        ('admin', 'group', 'g', 'editor', 'doc', 'd1'),  # wrong userset predicate
        ('...', 'group', 'g', 'editor', 'doc', 'd1'),    # bare subject, no [group] restriction
        ('...', 'user', 'alice', 'bogus', 'doc', 'd1'),  # nonexistent relation
    ):
        _reg13_unanimous(REG13_TAINTED_SCHEMA, raw, False)


def test_reg13_valid_writes_still_accepted_both():
    """Guard: real writes matching a declared restriction stay ACCEPTED by both
    backends (the fix rejects only no-match tuples, not valid ones)."""
    for raw in (
        ('...', 'user', 'alice', 'editor', 'doc', 'd1'),   # [user]
        ('member', 'group', 'g', 'editor', 'doc', 'd1'),   # [group#member]
    ):
        _reg13_unanimous(REG13_TAINTED_SCHEMA, raw, True)


def test_reg13_declared_wildcard_userset_accepted_both():
    """Prong 2: when [group:*#member] IS declared, group:*#member is ADMISSIBLE and both
    backends ACCEPT it (the reg10/reg11 bridged-in shape family -- must stay unchanged)."""
    _reg13_unanimous(REG13_DECLARED_STAR_SCHEMA,
                     ('member', 'group', '*', 'editor', 'doc', 'd1'), True)


def test_reg13_plain_user_star_sentinel_behavior_unchanged():
    """Prong 3: plain user:* subject behavior is unchanged -- accepted where [user:*] is
    declared (`public`), rejected where it is not (`blocked`), on both backends."""
    _reg13_unanimous(REG13_USERSTAR_SCHEMA,
                     ('...', 'user', '*', 'public', 'doc', 'd1'), True)
    _reg13_unanimous(REG13_USERSTAR_SCHEMA,
                     ('...', 'user', '*', 'blocked', 'doc', 'd1'), False)
