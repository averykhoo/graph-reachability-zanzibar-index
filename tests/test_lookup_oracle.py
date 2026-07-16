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

import random

import pytest

from setengine import ALL_SETOPS, SetEngine
from setengine.memberset import MemberSet
from zanzibar_utils_v1 import (Direct, TTU, Union, Intersection, Exclusion,
                               parse_openfga_schema, parse_schema_ast)
from tests.oracle import Oracle, OracleTuple
from tests.parity import _GraphSide, _SetSide, GHOST_NAME
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
