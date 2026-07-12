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
      stars and id not in neg; ghosts by shape-in-stars) == O, for every candidate
      subject that is interned, a bare entity, or '*'. Star shapes are exact both
      ways ('*' subjects: shape in stars == O).
  S2  expand component sweeps: every ``pos`` id is O-true; every ``neg`` id is
      star-covered (its own shape in ``stars``) AND O-false.
  S3  lookup_reverse is the documented neg-dropping render of expand
      (node_ids == pos, markers == stars; engine.py lookup_reverse) => one-sided:
      every node id O-true (soundness); every O-true candidate subject is in
      node_ids or marker-covered (completeness); marker-covered-but-O-false is
      LEGAL (that is exactly the dropped neg).
  S4  forward lookup (check-backed): every node id and every marker is O-true
      (markers against the intensional '*'-object query); exact two-sided over
      candidates whose (o_type, o_name, rel) key is interned; for uninterned
      candidates coverage still implies O-truth.

Known genuine divergences, pinned as strict xfails below (NOT worked around --
each is a wrong/undefined read answer today; see the tests for full repros):
  X1  Set forward ``lookup`` drops objects reachable ONLY via TTU whose
      (type, name, relation) key was never interned (engine.py:753 candidate
      universe = interned keys; spec set-engine §6.4 prescribes reverse
      propagation incl. TTU). The graph returns them.
  X2  Graph ``lookup_reverse`` on a derived relation with o_name='*' raises
      ValueError (wildcard.py _get_concrete -> core.node reserved-name guard)
      where ``check`` answers False (P7 #3) and the set engine returns empty.
      The gate's grid therefore skips derived '*'-object reverse lookups.
  X3  Set ``expand`` / ``lookup_reverse`` cannot represent an O-true from-chain
      userset subject that was never interned (no id exists; check answers it
      True via the from-chain rule, the graph returns its node). The gate's
      completeness therefore skips uninterned userset-shaped subjects
      (bare entities are unaffected: a tuple-less entity is only star-covered).
  X4  CHECK-level divergence (found by this gate, wider than lookups): on a
      DERIVED TTU, userset-shaped subjects whose truth flows through a stored
      tupleset parent answer False on the graph where the oracle and BOTH set
      engines answer True. Two flavors, both pinned:
        (a) the from-chain userset itself (oracle ttu_leaf / engine.py ttu_leaf
            from-chain rule): after ``doc:d1 parent doc:d2``,
            check('viewer','doc','d1','inherited','doc','d2') = graph False /
            others True -- while the graph's own UNTAINTED TTU path answers the
            analogous wildcards.fga query True via the rewrite edge;
        (b) userset membership lifted through the parent's target: after
            ``group:g1#member editor doc:d2`` + ``doc:d2 parent doc:d1``,
            check('member','group','g1','inherited','doc','d1') = graph False /
            others True -- even though the graph itself answers
            check('member','group','g1','viewer','doc','d2') True. The residue
            ``upos`` of the dependent never receives cross-object userset
            memberships (reconcile settles usersets from the object's own
            stored tuples only).
      The existing matrix/property grids never query userset subjects on
      derived TTU families, which is why this survived P7. The walks skip
      exactly the (subject, object) pairs where a stored tupleset tuple gives
      the subject a TTU explanation on a derived family
      (``_make_derived_ttu_userset_gap``); everything else stays strict.

A tamper suite proves the gate can fail: corrupted results (leaked id, dropped
id, cleared exclusions, dropped neg) must each trip the checkers.
"""

import random

import pytest

from setengine import ALL_SETOPS, SetEngine
from setengine.memberset import MemberSet
from zanzibar_utils_v1 import (Direct, Computed, TTU, Union, Intersection, Exclusion,
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


def _make_derived_ttu_userset_gap(ast, derived, present):
    """Predicate for the X4 known divergence: a userset-shaped subject on a derived
    family whose truth has a TTU explanation via a STORED tupleset parent of
    exactly this object -- either the from-chain userset itself (X4a) or a
    membership in the parent's target relation (X4b, decided by the oracle)."""
    ttu_cache: dict[tuple[str, str], list] = {}

    def closure_ttus(ot, rel):
        key = (ot, rel)
        if key not in ttu_cache:
            out, seen = [], set()

            def walk(t, r):
                if (t, r) in seen:
                    return
                seen.add((t, r))
                expr = ast.get((t, r))
                if expr is None:
                    return
                for node in _iter_exprs(expr):
                    if isinstance(node, TTU):
                        out.append(node)
                    elif isinstance(node, Computed):
                        walk(t, node.relation)

            walk(ot, rel)
            ttu_cache[key] = out
        return ttu_cache[key]

    def gap(oc, sp, st, sn, rel, ot, on):
        if sp == '...' or sn == '*' or (ot, rel) not in derived:
            return False
        for ttu in closure_ttus(ot, rel):
            for (_p, tst, tsn, trel, tot, ton) in present:
                if (trel, tot, ton) != (ttu.tupleset_rel, ot, on) or tsn == '*':
                    continue
                if sp == ttu.target_rel and (st, sn) == (tst, tsn):
                    return True                     # X4a: the from-chain userset itself
                if oc(sp, st, sn, ttu.target_rel, tst, tsn):
                    return True                     # X4b: membership via parent's target
        return False

    return gap


def _check_graph_forward(widx, ast, oc, subject, objects, res, known_gap=None):
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
        if got != expected and known_gap is not None \
                and known_gap(oc, sp, st, sn, rel, ot, on):
            continue                                            # X4 (pinned strict-xfail)
        assert got == expected, (
            f'graph.lookup{subject} vs oracle on {rel} {ot}:{on}: '
            f'graph={got} oracle={expected}')


def _check_graph_reverse(widx, oc, subjects, obj, res, known_gap=None):
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
        if got != expected and known_gap is not None \
                and known_gap(oc, sp, st, sn, rel, ot, on):
            continue                                            # X4 (pinned strict-xfail)
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
            got = (st, sp) in m.stars
            if sp != '...':
                # uninterned userset subject: representational gap X3 -- one-sided
                assert not got or expected, (
                    f'set.expand{obj} [{se.ops.name}] covers uninterned userset '
                    f'({sp},{st},{sn}) that is oracle-false')
                continue
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
        if uid is None and sp != '...':
            continue                                            # X3: no id can represent it
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
        if nid is not None:
            # exact over the engine's own candidate universe (interned keys);
            # full completeness for uninterned keys is the strict-xfail gap X1
            assert covered == expected, (
                f'set.lookup{subject} [{se.ops.name}] vs oracle on {rel} {ot}:{on}: '
                f'set={covered} oracle={expected}')
        else:
            assert not covered or expected, (
                f'set.lookup{subject} [{se.ops.name}] covers uninterned {rel} '
                f'{ot}:{on} that is oracle-false')


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
        self.known_gap = _make_derived_ttu_userset_gap(self.ast, self.derived, self.present)

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
                                     self.graph.widx.lookup(*subject), self.known_gap)
            for obj in self.objects:
                if obj[2] == '*' and (obj[1], obj[0]) in self.derived:
                    continue        # X2: derived '*'-object reverse raises today
                _check_graph_reverse(self.graph.widx, oc, self.subjects, obj,
                                     self.graph.widx.lookup_reverse(*obj), self.known_gap)
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
# Genuine divergences found by this gate (strict xfails; do NOT delete or relax
# these to make a refactor pass -- fix the underlying surface, then flip them)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason=(
    'GENUINE GAP (X1): set-engine forward lookup enumerates candidates from the '
    'interned keys only (setengine/engine.py lookup, "every interned object node is '
    'a candidate"), so an object reachable ONLY via TTU -- whose (type,name,relation) '
    'key no tuple ever interned -- is silently dropped even though check() and the '
    'graph both answer True. Spec set-engine §6.4 prescribes reverse propagation '
    'through TTU for candidate generation.'))
def test_set_lookup_forward_ttu_completeness_gap(load_fga_schema):
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


@pytest.mark.xfail(strict=True, reason=(
    'GENUINE GAP (X2): WildcardIndex.lookup_reverse on a derived relation with '
    "o_name='*' raises ValueError (_get_concrete -> core.node reserved-name guard) "
    "instead of returning the empty result that check() (False, deviations P7 #3) "
    'and the set engine (empty LookupResult) give for the same query.'))
def test_graph_reverse_star_object_on_derived_is_empty(load_fga_schema):
    from tests.test_processor import build
    session, widx, proc, write = build(load_fga_schema('boolean_wildcards.fga'))
    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
    res = widx.lookup_reverse('viewer', 'doc', '*')             # raises today
    assert res.node_ids == set() and res.markers == set() \
        and res.excluded_node_ids == set()
    session.close()


@pytest.mark.xfail(strict=True, reason=(
    'GENUINE GAP (X3): the set engine cannot represent an oracle-true from-chain '
    'userset subject that was never interned -- lookup_reverse/expand return ids, '
    'and no id exists for (folder,f1,viewer) when only the parent tuple is stored. '
    'check() answers the same subject True via the from-chain rule '
    '(engine.py ttu_leaf) and the graph lookup_reverse returns its node.'))
def test_set_reverse_uninterned_from_chain_userset(load_fga_schema):
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


@pytest.mark.xfail(strict=True, reason=(
    'GENUINE DIVERGENCE (X4, check-level): on a derived TTU, the graph answers the '
    'from-chain userset subject itself False where the oracle and BOTH set engines '
    'answer True (the Zanzibar from-chain rule: a stored tupleset parent p makes '
    'p#target_rel reach the object; oracle ttu_leaf, setengine ttu_leaf), and where '
    "the graph's own UNTAINTED TTU path answers the analogous query True via the "
    'rewrite edge (cf. wildcards.fga: viewer-from-parent from-chain is graph-True). '
    'The residue upos never records the from-chain userset. The matrix/property '
    'grids never query from-chain userset subjects on derived families, so this '
    'survived the P7 acceptance. Also reproduces on demorgans_reverse.fga: after '
    "role:r1 assigned user:b, check('access','role','r1','access','user','b') is "
    'graph-False / oracle-True / set-True.'))
def test_graph_check_from_chain_userset_on_derived_ttu(load_fga_schema):
    from tests.test_processor import build
    session, widx, proc, write = build(load_fga_schema('boolean_wildcards.fga'))
    write('add', ('...', 'doc', 'd1', 'parent', 'doc', 'd2'))
    # oracle + set engines say True (from-chain rule); the graph says False today
    assert widx.check('viewer', 'doc', 'd1', 'inherited', 'doc', 'd2') is True
    session.close()


@pytest.mark.xfail(strict=True, reason=(
    'GENUINE DIVERGENCE (X4b, check-level): a userset membership is not lifted '
    'through a derived TTU. With group:g1#member granted editor on doc:d2 and '
    "doc:d2 a parent of doc:d1, the graph answers check('member','group','g1',"
    "'viewer','doc','d2') True but check('member','group','g1','inherited','doc',"
    "'d1') False; the oracle and both set engines answer True. The dependent's "
    'residue upos never receives cross-object userset memberships (reconcile '
    "settles usersets from the object's own stored tuples only)."))
def test_graph_check_userset_membership_through_derived_ttu(load_fga_schema):
    from tests.test_processor import build
    session, widx, proc, write = build(load_fga_schema('boolean_wildcards.fga'))
    write('add', ('member', 'group', 'g1', 'editor', 'doc', 'd2'))
    write('add', ('...', 'doc', 'd2', 'parent', 'doc', 'd1'))
    assert widx.check('member', 'group', 'g1', 'viewer', 'doc', 'd2') is True
    # oracle + set engines say True (membership flows through the parent); graph: False
    assert widx.check('member', 'group', 'g1', 'inherited', 'doc', 'd1') is True
    session.close()
