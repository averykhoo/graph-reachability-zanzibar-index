"""R4-BF -- the in-memory boolean backfill for the bulk builder (design:
docs/r4bf-bulk-backfill-design.md).

P13 (``bulk_build``) constructs the pre-backfill closure directly; on a boolean
schema the total build was then dominated by the per-object SQL-backed
``DeltaProcessor.backfill()``. This module computes the SAME final derived state
(derived edges, residues, from-chain nodes, and their closure/refcount effects)
IN MEMORY, mutating the bulk builder's direct multigraph so ``bulk_build``'s Phase
W writes the union of load and derived state in one pass.

**Correctness bar (design):** the state produced here + Phase W is byte-IDENTICAL
to ``build_index(..., bulk=False)`` + ``DeltaProcessor.backfill()`` -- pinned by the
differential identity gate (``tests/test_bulk_build.py``). Everything below MIRRORS
``DeltaProcessor`` on a FRESH (empty derived state, add-only) build:

  * evaluation reuses the COMPILED plan closures ``plan.check_fn`` / ``plan.stars_fn``
    (design 2.2): ``_BulkEvalContext`` implements the SAME 10 callbacks as
    ``processor._EvalContext`` against the in-memory graph, so the boolean-expression
    logic is shared, not reimplemented. Only state ACCESS is mirrored.
  * ``_reconcile`` mirrors ``DeltaProcessor._reconcile`` (boolean spec §5.3) step for
    step, on empty per-key state: stars fold, neg candidates, from-chain interning
    (bridges immediately, within-stratum visibility), neg, upos, residue, edge audit.
  * iteration mirrors ``backfill()``: ``compiled.strata`` in order, relations in
    stratum list order, ``_live_keys_of`` over the in-memory family index, names sorted.

Reachability (the ``check`` / ``check_reachable_by_id`` probes read
``indirect_edge_count > 0``) is maintained INCREMENTALLY on every edge add with
immediate visibility (design §1 visibility subtleties); exact path counts are NOT
maintained here -- ``bulk_build`` recomputes them once over the FINAL multigraph.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from .invariants import InvariantViolation

if TYPE_CHECKING:
    from zanzibar_utils_v1 import CompiledBooleans, SchemaInfo

# A node's natural key: (predicate, type, name, wildcard) -- the same identity
# ``bulk_build`` and ``ReachabilityIndex.node`` dedupe on.
NodeKey = tuple[str, str, str, str]
# (predicate, type, name) -- a subject/leaf key as the plan closures see it.
SubjectKey = tuple[str, str, str]


class _Residue:
    """In-memory residue for one derived key: shapes ``stars`` plus node-KEY sets
    ``neg`` / ``upos`` (translated to flushed ids at Phase W write time), and the
    ``version`` bumped on every changing store (mirrors ``ResidueV1``)."""

    __slots__ = ('stars', 'neg', 'upos', 'version')

    def __init__(self, stars: frozenset, neg: set, upos: set, version: int):
        self.stars = stars
        self.neg = neg
        self.upos = upos
        self.version = version


class _BulkEvalContext:
    """Plan-evaluation context bound to one (object_type, obj_name). Implements the
    exact callback protocol of ``processor._EvalContext``; the compiled ``check_fn`` /
    ``stars_fn`` closures dispatch to these, so the boolean logic is shared."""

    __slots__ = ('bf', 'object_type', 'obj_name')

    def __init__(self, bf: '_BulkBackfill', object_type: str, obj_name: str):
        self.bf = bf
        self.object_type = object_type
        self.obj_name = obj_name

    # -- closure leaves (wildcard-aware; the 4-probe untainted check) --
    def leaf_check(self, leaf_pred: str, s: SubjectKey) -> bool:
        return self.bf._untainted_check(s, leaf_pred, self.object_type, self.obj_name)

    def leaf_stars(self, leaf_pred: str) -> frozenset:
        return frozenset(
            (t, p) for (t, p) in self.bf.subject_shapes
            if self.bf._untainted_check((p, t, '*'), leaf_pred,
                                        self.object_type, self.obj_name))

    # -- derived-computed leaves (same object) --
    def derived_check(self, rel: str, s: SubjectKey) -> bool:
        return self.bf._derived_check(self.object_type, rel, self.obj_name, s)

    def derived_stars(self, rel: str) -> frozenset:
        return self.bf._residue_stars(self.object_type, rel, self.obj_name)

    # -- derived-userset leaves: ∃ stored userset x on the storage leaf: s ∈ P(x) --
    def userset_check(self, leaf: str, t: str, p: str, s: SubjectKey) -> bool:
        sp, st, sn = s
        stored = self.bf._stored_userset_subjects(self.object_type, self.obj_name,
                                                  leaf, t, p)
        if (st, sp) == (t, p) and sn in stored:
            return True                      # blind-audit direct_leaf: the userset itself
        for x_name in stored:
            if self.bf._derived_check(t, p, x_name, s):
                return True
        return False

    def userset_stars(self, leaf: str, t: str, p: str) -> frozenset:
        out: frozenset = frozenset()
        for x_name in self.bf._stored_userset_subjects(self.object_type, self.obj_name,
                                                       leaf, t, p):
            out |= self.bf._residue_stars(t, p, x_name)
        return out

    # -- derived-target TTU (untainted tupleset) --
    def ttu_check(self, target: str, ts: str, parent_types: tuple, s: SubjectKey) -> bool:
        sp, st, sn = s
        for (pt, pn) in self.bf._tupleset_parents(self.object_type, self.obj_name,
                                                  ts, parent_types):
            if (sp, st, sn) == (target, pt, pn):
                return True                  # from-chain identity rule (X4a)
            if self.bf._member_check(pt, target, pn, s):
                return True
        return False

    def ttu_stars(self, target: str, ts: str, parent_types: tuple) -> frozenset:
        out: frozenset = frozenset()
        for (pt, pn) in self.bf._tupleset_parents(self.object_type, self.obj_name,
                                                  ts, parent_types):
            out |= self.bf._member_stars(pt, target, pn)
        return out

    # -- derived-tupleset TTU: parents are the STORED tupleset tuples (leaf families) --
    def tupleset_ttu_check(self, target: str, ts: str, parent_types: tuple,
                           s: SubjectKey) -> bool:
        sp, st, sn = s
        for (pt, pn) in self.bf._derived_stored_parents(self.object_type, self.obj_name,
                                                        ts, parent_types):
            if (sp, st, sn) == (target, pt, pn):
                return True                  # from-chain identity rule (X4a)
            if self.bf._member_check(pt, target, pn, s):
                return True
        return False

    def tupleset_ttu_stars(self, target: str, ts: str, parent_types: tuple) -> frozenset:
        out: frozenset = frozenset()
        for (pt, pn) in self.bf._derived_stored_parents(self.object_type, self.obj_name,
                                                        ts, parent_types):
            out |= self.bf._member_stars(pt, target, pn)
        return out


class _BulkBackfill:
    """Computes the fresh-build derived state of ``compiled`` over the bulk builder's
    in-memory direct multigraph ``m`` (design 2.2). Mutates ``m`` (derived edges +
    mid-backfill bridges, multiplicity 1) and ``nodes`` (interned public / from-chain /
    w nodes), and records ``derived_pairs`` / ``explicit`` / ``residues`` for Phase W.
    """

    def __init__(self, m: dict[tuple[NodeKey, NodeKey], int], nodes: set[NodeKey],
                 schema_info: 'SchemaInfo', compiled: 'CompiledBooleans'):
        self.m = m
        self.nodes = nodes
        self.schema_info = schema_info
        self.compiled = compiled
        self.subject_shapes = sorted(schema_info.subject_wildcard_shapes)

        # spec -> plan-tree node, by IDENTITY (blind-audit P2: same-target TTU leaves
        # carry equal specs, so the pairing is positional, never by name).
        self._leaf_node_by_spec = {
            id(spec): node
            for plan in compiled.plans.values()
            for spec, node in zip(plan.leaves, plan.leaf_nodes)
        }

        # Outputs consumed by Phase W.
        self.derived_pairs: set[tuple[NodeKey, NodeKey]] = set()
        self.explicit: set[NodeKey] = set()
        self.residues: dict[tuple[str, str, str], _Residue] = {}

        # -- direct-graph adjacency + reachability, seeded from load + bridge edges --
        self.out_adj: dict[NodeKey, set[NodeKey]] = defaultdict(set)
        self.in_adj: dict[NodeKey, set[NodeKey]] = defaultdict(set)
        for (a, b) in m:
            self.out_adj[a].add(b)
            self.in_adj[b].add(a)
        # concrete-family index (type, pred) -> {name} for the _live_keys_of mirror.
        self.family_names: dict[tuple[str, str], set[str]] = defaultdict(set)
        for (pred, typ, name, wild) in nodes:
            if wild == '':
                self.family_names[(typ, pred)].add(name)
        # full transitive reachability over the seed graph (one topo + DP); maintained
        # incrementally thereafter. reach_out[n] / reach_in[n] EXCLUDE n itself, so
        # ``b in reach_out[a]`` == the incremental ``check_reachable`` (indirect > 0).
        self.reach_out: dict[NodeKey, set[NodeKey]] = {n: set() for n in nodes}
        self.reach_in: dict[NodeKey, set[NodeKey]] = {n: set() for n in nodes}
        self._seed_reachability()

    # ------------------------------------------------------------------ #
    # Reachability (boolean, incremental, immediate visibility)
    # ------------------------------------------------------------------ #

    def _seed_reachability(self) -> None:
        order = self._topo(self.nodes, self.out_adj)
        for a in reversed(order):
            ra = self.reach_out[a]
            for b in self.out_adj[a]:
                ra.add(b)
                ra |= self.reach_out[b]
        for a in self.nodes:
            for b in self.reach_out[a]:
                self.reach_in[b].add(a)

    @staticmethod
    def _topo(nodes: set[NodeKey], out_adj: dict[NodeKey, set[NodeKey]]) -> list[NodeKey]:
        indeg: dict[NodeKey, int] = {n: 0 for n in nodes}
        for a in out_adj:
            for b in out_adj[a]:
                indeg[b] += 1
        queue = sorted(n for n in nodes if indeg[n] == 0)
        order: list[NodeKey] = []
        while queue:
            a = queue.pop()
            order.append(a)
            newly = []
            for b in out_adj.get(a, ()):
                indeg[b] -= 1
                if indeg[b] == 0:
                    newly.append(b)
            if newly:
                queue.extend(newly)
                queue.sort()
        if len(order) != len(nodes):
            raise InvariantViolation(
                'bulk backfill: the in-memory derived graph is cyclic -- '
                'stratification makes derived cycles impossible, so this is corruption')
        return order

    def _add_edge_existence(self, a: NodeKey, b: NodeKey) -> None:
        """Register a NEW direct edge a->b for reachability (idempotent on parallel
        edges). New reachable pairs = ancestors(a)∪{a} x descendants(b)∪{b}, applied
        immediately so later same-stratum probes see them (design §1 visibility)."""
        if b in self.out_adj[a]:
            return                           # parallel edge: reachability unchanged
        if a == b or a in self.reach_out.get(b, ()):
            raise InvariantViolation(
                'derived/bridge edge would close a cycle -- corrupted store or broken '
                f'stratification: {a} -> {b}')
        self.out_adj[a].add(b)
        self.in_adj[b].add(a)
        anc = self.reach_in.get(a, set()) | {a}
        desc = self.reach_out[b] | {b}
        for x in anc:
            rx = self.reach_out[x]
            for y in desc:
                if y not in rx:
                    rx.add(y)
                    self.reach_in[y].add(x)

    def _reachable(self, a: NodeKey | None, b: NodeKey | None) -> bool:
        return a is not None and b is not None and b in self.reach_out.get(a, ())

    # ------------------------------------------------------------------ #
    # Node / edge mutation
    # ------------------------------------------------------------------ #

    def _intern(self, key: NodeKey, *, implicit: bool) -> None:
        """Intern (or sticky-promote) a node. ``implicit=False`` pins it explicit,
        promoting a pre-existing implicit node (core.node's sticky rule)."""
        if key not in self.nodes:
            self.nodes.add(key)
            self.reach_out[key] = set()
            self.reach_in[key] = set()
            self.out_adj[key]          # touch defaultdicts so the sets exist
            self.in_adj[key]
            pred, typ, name, wild = key
            if wild == '':
                self.family_names[(typ, pred)].add(name)
        if implicit is False:
            self.explicit.add(key)

    def _add_bridge_edge(self, a: NodeKey, b: NodeKey) -> None:
        """A bridge edge, multiplicity 1, existence-checked (mirrors add_edge_by_id
        under _writing_derived=False -> not a derived grant)."""
        if self.m.get((a, b), 0) == 0:
            self.m[(a, b)] = 1
            self._add_edge_existence(a, b)

    def _add_derived_edge(self, skey: NodeKey, public_key: NodeKey) -> None:
        """A processor-written direct edge subject->public, multiplicity exactly 1
        (existence-checked). Flags the pair derived (core _add_db_edges_unsafe:
        derived iff _writing_derived and direct>0)."""
        pair = (skey, public_key)
        self.m[pair] = self.m.get(pair, 0) + 1
        self.derived_pairs.add(pair)
        self._add_edge_existence(skey, public_key)

    def _ensure_bridges(self, key: NodeKey) -> None:
        """Mirror WildcardIndex._ensure_bridges: a concrete of a bridged shape gets
        concrete->w_any and/or w_all->concrete (w nodes created implicit)."""
        pred, typ, name, wild = key
        if wild != '':
            return
        shape = (typ, pred)
        if shape in self.schema_info.bridged_in_shapes:
            w_any = (pred, typ, '*', 'any')
            self._intern(w_any, implicit=True)
            self._add_bridge_edge(key, w_any)
        if shape in self.schema_info.bridged_out_shapes:
            w_all = (pred, typ, '*', 'all')
            self._intern(w_all, implicit=True)
            self._add_bridge_edge(w_all, key)

    # ------------------------------------------------------------------ #
    # State access (mirrors WildcardIndex / DeltaProcessor read paths)
    # ------------------------------------------------------------------ #

    def _concrete_key(self, pred: str, typ: str, name: str) -> NodeKey | None:
        key = (pred, typ, name, '')
        return key if key in self.nodes else None

    def _w_key(self, typ: str, pred: str, variant: str) -> NodeKey | None:
        key = (pred, typ, '*', variant)
        return key if key in self.nodes else None

    def _untainted_check(self, s: SubjectKey, relation: str, o_type: str,
                         o_name: str) -> bool:
        """Mirror WildcardIndex.check's UNTAINTED path (the 4-probe wildcard check):
        probes (subj,obj), (w_any,obj), (subj,w_all), (w_any,w_all) with the exact
        declared-shape conditions; a missing node drops its probe."""
        sp, st, sn = s
        subj_is_star = (sn == '*')
        obj_is_star = (o_name == '*')
        subject_shape_declared = (st, sp) in self.schema_info.subject_wildcard_shapes
        object_shape_declared = (o_type, relation) in self.schema_info.object_wildcard_shapes

        if subj_is_star:
            subj_key = self._w_key(st, sp, 'any')
        else:
            subj_key = self._concrete_key(sp, st, sn)
        if obj_is_star:
            obj_key = self._w_key(o_type, relation, 'all')
        else:
            obj_key = self._concrete_key(relation, o_type, o_name)

        w_any = (self._w_key(st, sp, 'any')
                 if (not subj_is_star and subject_shape_declared) else None)
        w_all = (self._w_key(o_type, relation, 'all')
                 if (not obj_is_star and object_shape_declared) else None)

        return (self._reachable(subj_key, obj_key)      # probe 1
                or self._reachable(w_any, obj_key)       # probe 2
                or self._reachable(subj_key, w_all)      # probe 3
                or self._reachable(w_any, w_all))        # probe 4

    def _residue_state(self, o_type: str, rel: str, o_name: str
                       ) -> tuple[frozenset, set[NodeKey], set[NodeKey]]:
        e = self.residues.get((o_type, rel, o_name))
        if e is None:
            return frozenset(), set(), set()
        return e.stars, set(e.neg), set(e.upos)

    def _residue_stars(self, o_type: str, rel: str, o_name: str) -> frozenset:
        e = self.residues.get((o_type, rel, o_name))
        return frozenset() if e is None else e.stars

    def _derived_check(self, o_type: str, rel: str, o_name: str, s: SubjectKey) -> bool:
        """Mirror WildcardIndex._check_derived: star subject -> intensional stars;
        userset subject -> upos then stars-minus-neg (edge-free, P4); bare entity ->
        derived-edge reach probe then stars-minus-neg; ghosts answered by stars."""
        sp, st, sn = s
        # o_name is never '*' in backfill (live keys are concrete objects).
        if sn == '*':
            return (st, sp) in self._residue_stars(o_type, rel, o_name)
        subj_key = self._concrete_key(sp, st, sn)
        if sp != '...':
            stars, neg, upos = self._residue_state(o_type, rel, o_name)
            if subj_key is not None and subj_key in upos:
                return True
            if (st, sp) not in stars:
                return False
            return subj_key is None or subj_key not in neg
        # bare entity: probe the derived edge (public family), then residue.
        public_key = self._concrete_key(rel, o_type, o_name)
        if self._reachable(subj_key, public_key):
            return True
        stars, neg, _ = self._residue_state(o_type, rel, o_name)
        if (st, sp) not in stars:
            return False
        return subj_key is None or subj_key not in neg

    def _member_check(self, o_type: str, rel: str, o_name: str, s: SubjectKey) -> bool:
        if (o_type, rel) in self.compiled.tainted:
            return self._derived_check(o_type, rel, o_name, s)
        return self._untainted_check(s, rel, o_type, o_name)

    def _member_stars(self, o_type: str, rel: str, o_name: str) -> frozenset:
        if (o_type, rel) in self.compiled.tainted:
            return self._residue_stars(o_type, rel, o_name)
        return frozenset(
            (t, p) for (t, p) in self.subject_shapes
            if self._untainted_check((p, t, '*'), rel, o_type, o_name))

    # ------------------------------------------------------------------ #
    # Enumerations (all data-bounded over the in-memory graph)
    # ------------------------------------------------------------------ #

    def _incoming_concretes(self, key: NodeKey) -> list[NodeKey]:
        """Concrete reverse-reachable subjects (markers excluded) -- mirrors
        DeltaProcessor._incoming_concretes over lookup_reverse."""
        return [a for a in self.reach_in.get(key, ()) if a[3] == '']

    def _stored_userset_subjects(self, o_type: str, o_name: str, leaf: str,
                                 t: str, p: str) -> list[str]:
        leaf_key = self._concrete_key(leaf, o_type, o_name)
        if leaf_key is None:
            return []
        out = []
        for (sp2, st2, sn2, w2) in sorted(self.in_adj.get(leaf_key, ())):
            if w2 == '' and (st2, sp2) == (t, p):
                out.append(sn2)
        return out

    def _tupleset_parents(self, o_type: str, o_name: str, ts: str,
                          parent_types: tuple) -> list[tuple[str, str]]:
        """Stored tupleset parents: DIRECT incoming bare-entity subjects on (obj, ts)
        (stored-tuple TTU semantics -- computed members never count)."""
        ts_key = self._concrete_key(ts, o_type, o_name)
        if ts_key is None:
            return []
        out = []
        for (sp2, st2, sn2, w2) in sorted(self.in_adj.get(ts_key, ())):
            if w2 == '' and sp2 == '...' and st2 in parent_types:
                out.append((st2, sn2))
        return out

    def _ts_leaf_predicates(self, o_type: str, ts: str) -> list[str]:
        plan = self.compiled.plans[(o_type, ts)]
        return [spec.predicate for spec in plan.leaves if spec.storage]

    def _derived_stored_parents(self, o_type: str, o_name: str, ts: str,
                                parent_types: tuple) -> list[tuple[str, str]]:
        seen: dict[tuple[str, str], None] = {}
        for leaf in self._ts_leaf_predicates(o_type, ts):
            for pp in self._tupleset_parents(o_type, o_name, leaf, parent_types):
                seen[pp] = None
        return list(seen)

    def _ttu_target_upos_nodes(self, parents: list[tuple[str, str]],
                               target: str) -> list[NodeKey]:
        """Userset-shaped members of tainted TTU targets are edge-free (P4): lift them
        from the parents' residue upos, or the dependent never sees them (X4b)."""
        out: list[NodeKey] = []
        for (pt, pn) in parents:
            if (pt, target) not in self.compiled.tainted:
                continue
            out.extend(self._residue_state(pt, target, pn)[2])
        return out

    def _find_leaf_node(self, spec):
        node = self._leaf_node_by_spec.get(id(spec))
        if node is None:
            raise AssertionError(f'plan node not found for leaf {spec}')
        return node

    def _leaf_concretes(self, o_type: str, o_name: str, spec) -> list[NodeKey]:
        if spec.kind in ('closure', 'derived-userset'):
            leaf_key = self._concrete_key(spec.predicate, o_type, o_name)
            return [] if leaf_key is None else self._incoming_concretes(leaf_key)
        if spec.kind == 'derived-computed':
            d_key = self._concrete_key(spec.predicate, o_type, o_name)
            return [] if d_key is None else self._incoming_concretes(d_key)
        if spec.kind in ('derived-ttu', 'derived-tupleset-ttu'):
            node = self._find_leaf_node(spec)
            if spec.kind == 'derived-ttu':
                parents = self._tupleset_parents(o_type, o_name, node.tupleset_rel,
                                                 node.parent_types)
            else:
                parents = self._derived_stored_parents(o_type, o_name, node.tupleset_rel,
                                                       node.parent_types)
            out: dict[NodeKey, None] = {}
            for (pt, pn) in parents:
                p_key = self._concrete_key(node.target_rel, pt, pn)
                if p_key is not None:
                    for n in self._incoming_concretes(p_key):
                        out[n] = None
            for n in self._ttu_target_upos_nodes(parents, node.target_rel):
                out[n] = None
            return list(out)
        raise TypeError(f'unknown leaf kind {spec.kind!r}')

    def _derived_leaf_neg_ids(self, o_type: str, o_name: str, spec) -> set[NodeKey]:
        if spec.kind == 'closure':
            return set()
        if spec.kind == 'derived-computed':
            return self._residue_state(o_type, spec.predicate, o_name)[1]
        if spec.kind == 'derived-userset':
            node = self._find_leaf_node(spec)
            out: set[NodeKey] = set()
            for x in self._stored_userset_subjects(o_type, o_name, spec.predicate,
                                                   node.subject_type, node.subject_predicate):
                out |= self._residue_state(node.subject_type, node.subject_predicate, x)[1]
            return out
        if spec.kind == 'derived-ttu':
            node = self._find_leaf_node(spec)
            out = set()
            for (pt, pn) in self._tupleset_parents(o_type, o_name, node.tupleset_rel,
                                                   node.parent_types):
                if (pt, node.target_rel) in self.compiled.tainted:
                    out |= self._residue_state(pt, node.target_rel, pn)[1]
            return out
        if spec.kind == 'derived-tupleset-ttu':
            node = self._find_leaf_node(spec)
            out = set()
            for (pt, pn) in self._derived_stored_parents(o_type, o_name, node.tupleset_rel,
                                                         node.parent_types):
                if (pt, node.target_rel) in self.compiled.tainted:
                    out |= self._residue_state(pt, node.target_rel, pn)[1]
            return out
        raise TypeError(f'unknown leaf kind {spec.kind!r}')

    def _from_chain_keys(self, o_type: str, o_name: str, plan) -> list[SubjectKey]:
        """From-chain userset subjects of every TTU leaf (any polarity): one key
        (target_rel, parent_type, parent_name) per stored tupleset parent (X4a)."""
        keys: dict[SubjectKey, None] = {}
        for spec, node in zip(plan.leaves, plan.leaf_nodes):
            if spec.kind == 'derived-ttu':
                parents = self._tupleset_parents(o_type, o_name, node.tupleset_rel,
                                                 node.parent_types)
            elif spec.kind == 'derived-tupleset-ttu':
                parents = self._derived_stored_parents(o_type, o_name, node.tupleset_rel,
                                                       node.parent_types)
            else:
                continue
            for (pt, pn) in parents:
                keys[(node.target_rel, pt, pn)] = None
        return list(keys)

    # ------------------------------------------------------------------ #
    # Residue write + reconcile (mirrors DeltaProcessor, fresh-build)
    # ------------------------------------------------------------------ #

    def _store_residue(self, o_type: str, rel: str, o_name: str, stars: frozenset,
                       neg: set[NodeKey], upos: set[NodeKey]) -> None:
        """Upsert/delete the residue and bump version. The public object node is
        interned/sticky-promoted implicit=False (it anchors the residue). Empty
        residues are never stored (spec §4)."""
        self._intern((rel, o_type, o_name, ''), implicit=False)
        key = (o_type, rel, o_name)
        empty = not stars and not neg and not upos
        existing = self.residues.get(key)
        if existing is None:
            if empty:
                return
            self.residues[key] = _Residue(stars, set(neg), set(upos), 1)
        elif empty:
            del self.residues[key]
        else:
            existing.stars = stars
            existing.neg = set(neg)
            existing.upos = set(upos)
            existing.version += 1

    def _write_derived_add(self, s: SubjectKey, o_type: str, rel: str,
                           o_name: str) -> None:
        """Mirror DeltaProcessor._write_derived (add): promote the public node
        implicit=False, ensure both endpoints' bridges, add the derived direct edge."""
        sp, st, sn = s
        public_key = (rel, o_type, o_name, '')
        self._intern(public_key, implicit=False)
        skey = (sp, st, sn, '')
        # add_tuple's _resolve creates a missing subject implicit (defensive; audit
        # members always pre-exist on a fresh build).
        self._intern(skey, implicit=True)
        self._ensure_bridges(skey)
        self._ensure_bridges(public_key)
        self._add_derived_edge(skey, public_key)

    def _reconcile_subject_edge(self, o_type: str, rel: str, o_name: str,
                                s: SubjectKey, plan, ctx: _BulkEvalContext) -> None:
        """The bare-entity arm of DeltaProcessor._reconcile_subject (step 4): edge iff
        expr-true ∧ uncovered; then neg maintenance (star-covered ∧ expr-false), which
        can bump the residue version -- so it is replicated faithfully."""
        should = bool(plan.check_fn(ctx, s))
        sp, st, sn = s                       # sp == '...'
        stars, neg, upos = self._residue_state(o_type, rel, o_name)
        covered = (st, sp) in stars
        skey = self._concrete_key(sp, st, sn)
        public_key = self._concrete_key(rel, o_type, o_name)

        want_edge = should and not covered
        has_edge = (skey is not None and public_key is not None
                    and (skey, public_key) in self.derived_pairs)
        if want_edge and not has_edge:
            self._write_derived_add(s, o_type, rel, o_name)
        # (the remove arm is unreachable on a fresh add-only build)

        if skey is not None:
            want_neg = covered and not should
            if want_neg != (skey in neg):
                (neg.add if want_neg else neg.discard)(skey)
                self._store_residue(o_type, rel, o_name, stars, neg, upos)

    def _reconcile(self, o_type: str, rel: str, o_name: str) -> None:
        """Full-object reconcile from empty per-key state (boolean spec §5.3)."""
        plan = self.compiled.plans[(o_type, rel)]
        ctx = _BulkEvalContext(self, o_type, o_name)

        # (1) stars: the pinned star×boolean fold.
        stars = plan.stars_fn(ctx)

        # (2) neg candidates: concrete members of negative leaves ∪ neg sets of every
        #     referenced derived leaf (exclusions propagate up through residues).
        candidates: dict[NodeKey, None] = {}
        for spec in plan.leaves:
            if spec.positive:
                continue
            for n in self._leaf_concretes(o_type, o_name, spec):
                candidates[n] = None
        for spec in plan.leaves:
            for nkey in self._derived_leaf_neg_ids(o_type, o_name, spec):
                if nkey in self.nodes:       # mirror the _nodes_by_ids "if n is not None"
                    candidates[nkey] = None

        # (2a) from-chain userset subjects (X4a): interned ONLY when should != covered,
        #      implicit=False, bridges ensured immediately (within-stratum visibility).
        for s in self._from_chain_keys(o_type, o_name, plan):
            sp, st, sn = s
            skey = self._concrete_key(sp, st, sn)
            if skey is None:
                covered = (st, sp) in stars
                should = bool(plan.check_fn(ctx, s))
                if should == covered:
                    continue                 # residue-free outcomes are answered by reads
                skey = (sp, st, sn, '')
                self._intern(skey, implicit=False)
                self._ensure_bridges(skey)
            candidates[skey] = None

        # neg = star-covered ∧ expr-false over the candidates.
        neg: set[NodeKey] = set()
        for nkey in candidates:
            pred, typ, name, wild = nkey
            if (typ, pred) not in stars:
                continue
            if not plan.check_fn(ctx, (pred, typ, name)):
                neg.add(nkey)

        # (2b) audit = candidates ∪ derived incoming concretes ∪ positive-leaf concretes
        #      ∪ old upos (empty on fresh build).
        audit: dict[NodeKey, None] = dict(candidates)
        obj_key = self._concrete_key(rel, o_type, o_name)
        if obj_key is not None:
            for n in self._incoming_concretes(obj_key):
                audit[n] = None
        for spec in plan.leaves:
            if not spec.positive:
                continue
            for n in self._leaf_concretes(o_type, o_name, spec):
                audit[n] = None
        old_stars, old_neg, old_upos = self._residue_state(o_type, rel, o_name)
        for nkey in old_upos:
            audit[nkey] = None

        # (2c) upos: userset-shaped audit members, uncovered ∧ expr-true (edge-free P4).
        upos: set[NodeKey] = set()
        for nkey in audit:
            pred, typ, name, wild = nkey
            if pred == '...' or wild != '':
                continue
            if (typ, pred) in stars:
                continue
            if plan.check_fn(ctx, (pred, typ, name)):
                upos.add(nkey)

        # (3) residue upsert iff changed (fresh build: iff non-empty), version=1.
        if (stars != old_stars) or (neg != old_neg) or (upos != old_upos):
            self._store_residue(o_type, rel, o_name, stars, neg, upos)

        # (4) edge audit over BARE-ENTITY audit members (usersets never hold edges).
        for nkey in list(audit):
            pred, typ, name, wild = nkey
            if pred != '...':
                continue
            self._reconcile_subject_edge(o_type, rel, o_name, (pred, typ, name),
                                         plan, ctx)

    # ------------------------------------------------------------------ #
    # Backfill iteration (mirrors DeltaProcessor.backfill / _live_keys_of)
    # ------------------------------------------------------------------ #

    def _live_keys_of(self, o_type: str, rel: str) -> set[str]:
        names: set[str] = set()
        plan = self.compiled.plans[(o_type, rel)]
        preds = [rel] + [spec.predicate for spec in plan.leaves
                         if spec.positive and spec.kind in ('closure', 'derived-userset')]
        for pred in preds:
            names |= set(self.family_names.get((o_type, pred), ()))
        for spec in plan.leaves:
            if not spec.positive or spec.kind in ('closure', 'derived-userset'):
                continue
            if spec.kind == 'derived-computed':
                names |= self._live_keys_of(o_type, spec.predicate)
            elif spec.kind == 'derived-ttu':
                node = self._find_leaf_node(spec)
                names |= set(self.family_names.get((o_type, node.tupleset_rel), ()))
            elif spec.kind == 'derived-tupleset-ttu':
                node = self._find_leaf_node(spec)
                names |= self._live_keys_of(o_type, node.tupleset_rel)
        return names

    def run(self) -> None:
        """Reconcile every live key, stratum by stratum, in backfill's exact order."""
        for stratum in self.compiled.strata:
            for (o_type, rel) in stratum:
                for o_name in sorted(self._live_keys_of(o_type, rel)):
                    self._reconcile(o_type, rel, o_name)
