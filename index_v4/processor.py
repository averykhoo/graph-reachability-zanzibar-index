"""
DeltaProcessor: stratified IVM for derived (boolean) relations (boolean spec §5).

The processor consumes the closure's own outbox stream and maintains, per derived
relation, (a) materialised derived edges for concretely-supported members and (b) a
per-object ``ResidueV1`` symbolic record ``(stars, neg)``. Deltas are invalidation
signals, never state transfers: every reconcile recomputes membership from committed
base state and reconciles idempotently.

Synchronous v1: ``run_cascade`` is called inside the writing transaction, after the
raw write's leaf edges + closure maintenance, before commit. ``_lock_store`` already
serializes the whole cascade; no new locking.

Evaluation context: no recursion anywhere -- closure-leaves are wildcard-aware point
probes, derived leaves read persisted edge+residue state of strictly earlier strata.
A processor write that the core rejects as a cycle is a HARD failure
(``InvariantViolation``), never an op rejection: stratification makes derived cycles
impossible, so a hit means a corrupted store (boolean spec §7).
"""

from __future__ import annotations

import json
from collections import defaultdict

from sqlmodel import select

from zanzibar_utils_v1 import (CompiledBooleans, DerivedFamily, LeafFamily)

from .invariants import InvariantViolation
from .models import EdgeV4, NodeV4, ResidueV1
from .outbox import outbox_rows
from .wildcard import WildcardIndex

SubjectKey = tuple[str, str, str]      # (predicate, type, name); predicate '...' for bare
Key = tuple[str, str, str]             # (object_type, relation, object_name)


def _shape(pred: str, s_type: str) -> tuple[str, str]:
    return (s_type, pred)


class _EvalContext:
    """Plan-evaluation context bound to one (store, object). Implements the leaf
    callbacks the compiled ``check_fn`` / ``stars_fn`` closures dispatch to."""

    def __init__(self, proc: 'DeltaProcessor', object_type: str, obj_name: str):
        self.proc = proc
        self.object_type = object_type
        self.obj_name = obj_name

    # -- closure leaves (wildcard-aware; star-under-boolean composes per §7) --

    def leaf_check(self, leaf_pred: str, s: SubjectKey) -> bool:
        sp, st, sn = s
        return self.proc.widx.check(sp, st, sn, leaf_pred, self.object_type, self.obj_name)

    def leaf_stars(self, leaf_pred: str) -> frozenset:
        widx = self.proc.widx
        return frozenset(
            (t, p) for (t, p) in self.proc.subject_shapes
            if widx.check(p, t, '*', leaf_pred, self.object_type, self.obj_name))

    # -- derived-computed leaves (same object) --

    def derived_check(self, rel: str, s: SubjectKey) -> bool:
        return self.proc.derived_check(self.object_type, rel, self.obj_name, s)

    def derived_stars(self, rel: str) -> frozenset:
        return self.proc.residue_stars(self.object_type, rel, self.obj_name)

    # -- derived-userset leaves: ∃ stored userset x on the storage leaf: s ∈ P(x) --

    def userset_check(self, leaf: str, t: str, p: str, s: SubjectKey) -> bool:
        for x_name in self.proc.stored_userset_subjects(self.object_type, self.obj_name, leaf, t, p):
            if self.proc.derived_check(t, p, x_name, s):
                return True
        return False

    def userset_stars(self, leaf: str, t: str, p: str) -> frozenset:
        out: frozenset = frozenset()
        for x_name in self.proc.stored_userset_subjects(self.object_type, self.obj_name, leaf, t, p):
            out |= self.proc.residue_stars(t, p, x_name)
        return out

    # -- derived-target TTU (untainted tupleset): ∃ tupleset-parent: derived target --

    def ttu_check(self, target: str, ts: str, parent_types: tuple, s: SubjectKey) -> bool:
        for (pt, pn) in self.proc.tupleset_parents(self.object_type, self.obj_name, ts, parent_types):
            if self.proc.member_check(pt, target, pn, s):
                return True
        return False

    def ttu_stars(self, target: str, ts: str, parent_types: tuple) -> frozenset:
        out: frozenset = frozenset()
        for (pt, pn) in self.proc.tupleset_parents(self.object_type, self.obj_name, ts, parent_types):
            out |= self.proc.member_stars(pt, target, pn)
        return out

    # -- derived-tupleset TTU: parents are the STORED tupleset tuples (the pinned
    #    Zanzibar semantics -- the oracle's ttu_leaf reads raw tuples, never computed
    #    membership), which for a derived tupleset live on its leaf families --

    def tupleset_ttu_check(self, target: str, ts: str, parent_types: tuple, s: SubjectKey) -> bool:
        for (pt, pn) in self.proc.derived_stored_parents(self.object_type, self.obj_name,
                                                         ts, parent_types):
            if self.proc.member_check(pt, target, pn, s):
                return True
        return False

    def tupleset_ttu_stars(self, target: str, ts: str, parent_types: tuple) -> frozenset:
        out: frozenset = frozenset()
        for (pt, pn) in self.proc.derived_stored_parents(self.object_type, self.obj_name,
                                                         ts, parent_types):
            out |= self.proc.member_stars(pt, target, pn)
        return out


class DeltaProcessor:
    """Maintains derived-relation state from the outbox stream (boolean spec §5)."""

    def __init__(self, widx: WildcardIndex, compiled: CompiledBooleans):
        self.widx = widx
        self.idx = widx.idx
        self.session = widx.idx.session
        self.store_id = widx.idx.store_id
        self.compiled = compiled
        self.subject_shapes = sorted(widx.schema_info.subject_wildcard_shapes)
        # residue bumps of the current round, consumed by the cascade as extra
        # invalidations for the next round (spec §5.2: version bumps enqueue the same
        # dependent keys; they emit no outbox rows).
        self._bumped: list[tuple[str, str, str]] = []

    # ------------------------------------------------------------------ #
    # Node / state accessors (read-only; never intern on reads)
    # ------------------------------------------------------------------ #

    def _node(self, predicate: str, e_type: str, name: str) -> NodeV4 | None:
        return self.session.exec(
            select(NodeV4).where(NodeV4.store_id == self.store_id)
            .where(NodeV4.predicate == predicate).where(NodeV4.type == e_type)
            .where(NodeV4.name == name).where(NodeV4.wildcard == '')
        ).first()

    def _residue_row(self, object_node_id: int) -> ResidueV1 | None:
        return self.session.exec(
            select(ResidueV1).where(ResidueV1.store_id == self.store_id)
            .where(ResidueV1.object_node_id == object_node_id)
        ).first()

    def _residue_state(self, object_type: str, rel: str, obj_name: str
                       ) -> tuple[frozenset, set[int]]:
        node = self._node(rel, object_type, obj_name)
        if node is None:
            return frozenset(), set()
        row = self._residue_row(node.id)
        if row is None:
            return frozenset(), set()
        stars = frozenset(tuple(s) for s in json.loads(row.stars))
        neg = set(json.loads(row.neg))
        return stars, neg

    def residue_stars(self, object_type: str, rel: str, obj_name: str) -> frozenset:
        return self._residue_state(object_type, rel, obj_name)[0]

    def derived_check(self, object_type: str, rel: str, obj_name: str, s: SubjectKey) -> bool:
        """The §6 derived membership check: edge probe + residue (≤2 point reads)."""
        sp, st, sn = s
        obj_node = self._node(rel, object_type, obj_name)
        if obj_node is None:
            return False
        if sn == '*':
            stars, _ = self._residue_state(object_type, rel, obj_name)
            return _shape(sp, st) in stars
        s_node = self._node(sp, st, sn)
        if s_node is not None and self.idx.check_reachable_by_id(s_node.id, obj_node.id):
            return True
        stars, neg = self._residue_state(object_type, rel, obj_name)
        if _shape(sp, st) not in stars:
            return False
        return s_node is None or s_node.id not in neg

    def member_check(self, object_type: str, rel: str, obj_name: str, s: SubjectKey) -> bool:
        """Membership in (object_type, rel) -- derived (edge+residue) when tainted,
        plain wildcard-aware closure check otherwise."""
        if (object_type, rel) in self.compiled.tainted:
            return self.derived_check(object_type, rel, obj_name, s)
        sp, st, sn = s
        return self.widx.check(sp, st, sn, rel, object_type, obj_name)

    def member_stars(self, object_type: str, rel: str, obj_name: str) -> frozenset:
        if (object_type, rel) in self.compiled.tainted:
            return self.residue_stars(object_type, rel, obj_name)
        return frozenset(
            (t, p) for (t, p) in self.subject_shapes
            if self.widx.check(p, t, '*', rel, object_type, obj_name))

    # ------------------------------------------------------------------ #
    # Enumerations (all data-bounded: stored edges / nodes / residues only)
    # ------------------------------------------------------------------ #

    def _incoming_concretes(self, obj_node_id: int) -> list[NodeV4]:
        """Concrete subject nodes reaching obj (markers excluded)."""
        ids = self.idx.lookup_reverse(obj_node_id)
        if not ids:
            return []
        nodes = self.session.exec(
            select(NodeV4).where(NodeV4.store_id == self.store_id)
            .where(NodeV4.id.in_(ids))  # type: ignore[attr-defined]
        ).all()
        return [n for n in nodes if n.wildcard == '']

    def _direct_incoming(self, obj_node_id: int) -> list[EdgeV4]:
        return list(self.session.exec(
            select(EdgeV4).where(EdgeV4.store_id == self.store_id)
            .where(EdgeV4.object_id == obj_node_id)
            .where(EdgeV4.direct_edge_count > 0)  # type: ignore[arg-type]
        ).all())

    def stored_userset_subjects(self, object_type: str, obj_name: str, leaf: str,
                                t: str, p: str) -> list[str]:
        """Names x of userset subjects (t, x, p) holding a stored tuple on the storage
        leaf (obj, leaf)."""
        leaf_node = self._node(leaf, object_type, obj_name)
        if leaf_node is None:
            return []
        out = []
        for e in self._direct_incoming(leaf_node.id):
            n = self.session.get(NodeV4, e.subject_id)
            if n is not None and n.wildcard == '' and (n.type, n.predicate) == (t, p):
                out.append(n.name)
        return out

    def tupleset_parents(self, object_type: str, obj_name: str, ts: str,
                         parent_types: tuple) -> list[tuple[str, str]]:
        """Entity parents p with a stored tupleset tuple (p, ts, obj): DIRECT incoming
        entity subjects on the (obj, ts) node. Stored tuples only -- the pinned TTU
        semantics (oracle ttu_leaf); computed members of the tupleset never count."""
        ts_node = self._node(ts, object_type, obj_name)
        if ts_node is None:
            return []
        out = []
        for e in self._direct_incoming(ts_node.id):
            n = self.session.get(NodeV4, e.subject_id)
            if (n is not None and n.wildcard == '' and n.predicate == '...'
                    and n.type in parent_types):
                out.append((n.type, n.name))
        return out

    def _ts_leaf_predicates(self, object_type: str, ts: str) -> list[str]:
        """The STORAGE-leaf predicates of a derived tupleset relation: only
        RewriteFilter-fed leaves hold raw stored tuples (rule-routed leaves carry
        computed state, which never counts as a TTU parent)."""
        plan = self.compiled.plans[(object_type, ts)]
        return [spec.predicate for spec in plan.leaves if spec.storage]

    def derived_stored_parents(self, object_type: str, obj_name: str, ts: str,
                               parent_types: tuple) -> list[tuple[str, str]]:
        """Stored tupleset tuples of a DERIVED tupleset relation: raw admitted writes
        live on its leaf families (rewrite routing), so parents are the direct
        incoming entity subjects across those leaf nodes."""
        seen: dict[tuple[str, str], None] = {}
        for leaf in self._ts_leaf_predicates(object_type, ts):
            for (pt, pn) in self.tupleset_parents(object_type, obj_name, leaf, parent_types):
                seen[(pt, pn)] = None
        return list(seen)

    def _stored_parent_objects_of_entity(self, e_type: str, e_name: str,
                                         object_type: str, ts: str) -> set[str]:
        """Objects obj with a stored tuple (entity, ts, obj) where ts is a derived
        tupleset: the entity's direct outgoing edges into ts's leaf families."""
        ent = self._node('...', e_type, e_name)
        if ent is None:
            return set()
        leaf_preds = set(self._ts_leaf_predicates(object_type, ts))
        out: set[str] = set()
        edges = self.session.exec(
            select(EdgeV4).where(EdgeV4.store_id == self.store_id)
            .where(EdgeV4.subject_id == ent.id)
            .where(EdgeV4.direct_edge_count > 0)  # type: ignore[arg-type]
        ).all()
        for e in edges:
            o = self.session.get(NodeV4, e.object_id)
            if o is not None and o.type == object_type and o.predicate in leaf_preds:
                out.add(o.name)
        return out

    # ------------------------------------------------------------------ #
    # Derived writes (through the ordinary façade path, processor-flagged)
    # ------------------------------------------------------------------ #

    def _write_derived(self, s: SubjectKey, object_type: str, rel: str, obj_name: str,
                       add: bool) -> None:
        sp, st, sn = s
        if add:
            # Pin the derived-public node non-implicit: it anchors the residue row and
            # must survive its last edge's removal (implicit GC would orphan the
            # residue; see spec-deviations P4).
            self.idx.node(rel, object_type, obj_name, create_if_missing=True, implicit=False)
        self.widx.processor_writes = True
        try:
            if add:
                self.widx.add_tuple(sp, st, sn, rel, object_type, obj_name)
            else:
                self.widx.remove_tuple(sp, st, sn, rel, object_type, obj_name)
        except ValueError as e:
            if 'cycle' in str(e):
                # Stratification makes derived cycles impossible; hitting the core's
                # cycle rejection here means a corrupted store -- hard failure, never
                # an op rejection (boolean spec §7).
                raise InvariantViolation(
                    f'derived write would close a cycle -- corrupted store or broken '
                    f'stratification: {s} -> ({object_type}, {rel}, {obj_name})') from e
            raise
        finally:
            self.widx.processor_writes = False

    # ------------------------------------------------------------------ #
    # Reconciliation (§5.3 / §5.4) -- idempotent by construction
    # ------------------------------------------------------------------ #

    def reconcile_subject(self, object_type: str, rel: str, obj_name: str,
                          s: SubjectKey) -> bool:
        """Cheap path: reconcile one subject's derived edge + residue-neg membership.

        Canonical representation (deterministic across op orders, and the space rule
        'star-only members: zero edges'):
          * star-covered subjects hold NO edge -- they are answered by the residue:
            in ``neg`` iff expr-false;
          * uncovered subjects hold an edge iff expr-true, and are never in ``neg``.
        Returns True iff anything changed."""
        plan = self.compiled.plans[(object_type, rel)]
        ctx = _EvalContext(self, object_type, obj_name)
        should = bool(plan.check_fn(ctx, s))

        sp, st, sn = s
        changed = False

        stars, neg = self._residue_state(object_type, rel, obj_name)
        covered = _shape(sp, st) in stars
        want_edge = should and not covered

        s_node = self._node(sp, st, sn)
        obj_node = self._node(rel, object_type, obj_name)
        has_edge = (s_node is not None and obj_node is not None
                    and self.idx.direct_edge_exists_by_id(s_node.id, obj_node.id))

        if want_edge and not has_edge:
            self._write_derived(s, object_type, rel, obj_name, add=True)
            changed = True
        elif not want_edge and has_edge:
            self._write_derived(s, object_type, rel, obj_name, add=False)
            changed = True

        # neg maintenance for this subject: star-covered ∧ expr-false ⇔ in neg.
        if s_node is not None:
            want_neg = covered and not should
            if want_neg != (s_node.id in neg):
                (neg.add if want_neg else neg.discard)(s_node.id)
                self._store_residue(object_type, rel, obj_name, stars, neg)
                changed = True
        if changed:
            self._gc_public_node(object_type, rel, obj_name)
        return changed

    def reconcile(self, object_type: str, rel: str, obj_name: str) -> bool:
        """Full-object reconcile (§5.3): star fold, neg recompute, residue upsert,
        edge audit. Returns True iff anything changed (I9: fixpoint ⇒ False)."""
        plan = self.compiled.plans[(object_type, rel)]
        ctx = _EvalContext(self, object_type, obj_name)

        # (1) stars: the pinned star×boolean fold, compiled into stars_fn.
        stars = plan.stars_fn(ctx)

        # (2) neg candidates: concrete members of every negative-polarity leaf ∪ neg
        #     sets of every referenced derived leaf (any kind -- exclusions propagate
        #     up through residues); then neg = star-covered ∧ expr-false.
        candidates: dict[int, NodeV4] = {}
        for spec in plan.leaves:
            if spec.positive:
                continue
            for n in self._leaf_concretes(object_type, obj_name, spec):
                candidates[n.id] = n
        for spec in plan.leaves:
            for nid in self._derived_leaf_neg_ids(object_type, obj_name, spec):
                n = self.session.get(NodeV4, nid)
                if n is not None:
                    candidates[n.id] = n

        neg: set[int] = set()
        neg_nodes: dict[int, NodeV4] = {}
        for nid, n in candidates.items():
            if _shape(n.predicate, n.type) not in stars:
                continue
            if not plan.check_fn(ctx, (n.predicate, n.type, n.name)):
                neg.add(nid)
                neg_nodes[nid] = n

        # (3) upsert/delete the residue iff changed.
        old_stars, old_neg = self._residue_state(object_type, rel, obj_name)
        residue_changed = (stars != old_stars) or (neg != old_neg)
        if residue_changed:
            self._store_residue(object_type, rel, obj_name, stars, neg)

        # (4) edge audit: current derived incoming concretes ∪ concretes of every
        #     positive leaf ∪ step-2 candidates.
        audit: dict[int, NodeV4] = dict(candidates)
        obj_node = self._node(rel, object_type, obj_name)
        if obj_node is not None:
            for n in self._incoming_concretes(obj_node.id):
                audit[n.id] = n
        for spec in plan.leaves:
            if not spec.positive:
                continue
            for n in self._leaf_concretes(object_type, obj_name, spec):
                audit[n.id] = n

        edges_changed = False
        for n in audit.values():
            edges_changed |= self.reconcile_subject(
                object_type, rel, obj_name, (n.predicate, n.type, n.name))

        if residue_changed or edges_changed:
            self._gc_public_node(object_type, rel, obj_name)
        return residue_changed or edges_changed

    def _derived_leaf_neg_ids(self, object_type: str, obj_name: str, spec) -> set[int]:
        """The neg sets of one referenced derived leaf (§5.3 step 2): exclusions
        recorded in lower-strata residues must surface as candidates here, or a
        star-covered-but-excluded subject would silently ride this relation's stars."""
        if spec.kind == 'closure':
            return set()
        if spec.kind == 'derived-computed':
            return self._residue_state(object_type, spec.predicate, obj_name)[1]
        if spec.kind == 'derived-userset':
            # stored usersets x of (t, p): pull residue(x, p).neg
            out: set[int] = set()
            tree_node = self._find_leaf_node(spec, object_type)
            for x in self.stored_userset_subjects(object_type, obj_name, spec.predicate,
                                                  tree_node.subject_type,
                                                  tree_node.subject_predicate):
                out |= self._residue_state(tree_node.subject_type,
                                           tree_node.subject_predicate, x)[1]
            return out
        if spec.kind == 'derived-ttu':
            node = self._find_leaf_node(spec, object_type)
            out = set()
            for (pt, pn) in self.tupleset_parents(object_type, obj_name,
                                                  node.tupleset_rel, node.parent_types):
                if (pt, node.target_rel) in self.compiled.tainted:
                    out |= self._residue_state(pt, node.target_rel, pn)[1]
            return out
        if spec.kind == 'derived-tupleset-ttu':
            node = self._find_leaf_node(spec, object_type)
            out = set()
            for (pt, pn) in self.derived_stored_parents(object_type, obj_name,
                                                        node.tupleset_rel, node.parent_types):
                if (pt, node.target_rel) in self.compiled.tainted:
                    out |= self._residue_state(pt, node.target_rel, pn)[1]
            return out
        raise TypeError(f'unknown leaf kind {spec.kind!r}')

    def _leaf_concretes(self, object_type: str, obj_name: str, spec) -> list[NodeV4]:
        """Concrete members, on this object, of one plan leaf (any kind)."""
        if spec.kind in ('closure', 'derived-userset'):
            # storage families: reverse concretes on the leaf node (closure includes
            # members flowing through userset nodes and, for derived-userset leaves,
            # through processor-written derived edges)
            leaf_node = self._node(spec.predicate, object_type, obj_name)
            return [] if leaf_node is None else self._incoming_concretes(leaf_node.id)
        if spec.kind == 'derived-computed':
            d_node = self._node(spec.predicate, object_type, obj_name)
            return [] if d_node is None else self._incoming_concretes(d_node.id)
        if spec.kind == 'derived-ttu':
            node = self._find_leaf_node(spec, object_type)
            out: dict[int, NodeV4] = {}
            for (pt, pn) in self.tupleset_parents(object_type, obj_name,
                                                  node.tupleset_rel, node.parent_types):
                p_node = self._node(node.target_rel, pt, pn)
                if p_node is not None:
                    for n in self._incoming_concretes(p_node.id):
                        out[n.id] = n
            return list(out.values())
        if spec.kind == 'derived-tupleset-ttu':
            node = self._find_leaf_node(spec, object_type)
            out = {}
            for (pt, pn) in self.derived_stored_parents(object_type, obj_name,
                                                        node.tupleset_rel, node.parent_types):
                p_node = self._node(node.target_rel, pt, pn)
                if p_node is not None:
                    for n in self._incoming_concretes(p_node.id):
                        out[n.id] = n
            return list(out.values())
        raise TypeError(f'unknown leaf kind {spec.kind!r}')

    def _find_leaf_node(self, spec, object_type: str):
        """Recover the plan-tree node for a derived leaf spec (kind + predicate
        match). Userset leaves match on their storage predicate; TTU leaves on their
        target relation."""
        from zanzibar_utils_v1 import PDerivedTTU, PDerivedTuplesetTTU, PDerivedUserset

        if spec.kind == 'derived-userset':
            want, match_attr = PDerivedUserset, 'predicate'
        elif spec.kind == 'derived-ttu':
            want, match_attr = PDerivedTTU, 'target_rel'
        else:
            want, match_attr = PDerivedTuplesetTTU, 'target_rel'
        found = []

        def walk(n):
            if isinstance(n, want) and getattr(n, match_attr) == spec.predicate:
                found.append(n)
            for c in getattr(n, 'children', ()):
                walk(c)
            for attr in ('base', 'subtract'):
                if hasattr(n, attr):
                    walk(getattr(n, attr))

        for plan in self.compiled.plans.values():
            if plan.key[0] == object_type and any(s is spec for s in plan.leaves):
                walk(plan.tree)
                break
        assert found, f'plan node not found for leaf {spec}'
        return found[0]

    def _gc_public_node(self, object_type: str, rel: str, obj_name: str) -> None:
        """Processor-managed lifecycle for the pinned derived-public node: it is
        created non-implicit (it anchors the residue row and must survive its last
        edge's removal), so the processor deletes it itself once NOTHING remains --
        no residue row and no edges (reference_count counts direct edges, and a node
        with zero direct edges can hold no closure rows either). Keeps add-then-remove
        an exact row-multiset round trip."""
        node = self._node(rel, object_type, obj_name)
        if node is None or node.reference_count != 0:
            return
        if self._residue_row(node.id) is not None:
            return
        self.session.delete(node)

    def _store_residue(self, object_type: str, rel: str, obj_name: str,
                       stars: frozenset, neg: set[int]) -> None:
        """Upsert/delete the residue row; bump version; record the bump for dependent
        invalidation. Empty residues are deleted, never stored (spec §4)."""
        # The processor may intern the public object node on the write path (spec §4);
        # non-implicit so residue-only objects (star coverage, zero edges) survive GC.
        node = self.idx.node(rel, object_type, obj_name, create_if_missing=True, implicit=False)
        row = self._residue_row(node.id)
        empty = not stars and not neg
        if row is None:
            if empty:
                return
            self.session.add(ResidueV1(
                store_id=self.store_id, object_node_id=node.id, relation=rel,
                stars=json.dumps(sorted([list(s) for s in stars])),
                neg=json.dumps(sorted(neg)), version=1))
        elif empty:
            self.session.delete(row)
        else:
            row.stars = json.dumps(sorted([list(s) for s in stars]))
            row.neg = json.dumps(sorted(neg))
            row.version += 1
            self.session.add(row)
        self._bumped.append((object_type, rel, obj_name))

    # ------------------------------------------------------------------ #
    # Delta → key mapping (§5.2) + cascade loop (§5.1)
    # ------------------------------------------------------------------ #

    def _map_deltas_to_keys(self, rows) -> dict[Key, set[SubjectKey] | None]:
        """Coalesced invalidation map: key -> None (full-object reconcile) or the set
        of concrete subjects for the cheap path."""
        keys: dict[Key, set[SubjectKey] | None] = {}

        def full(key: Key) -> None:
            keys[key] = None

        def subject(key: Key, s: SubjectKey) -> None:
            if keys.get(key, set()) is not None:
                keys.setdefault(key, set()).add(s)

        for r in rows:
            # endpoints come from the row's denormalized columns: the node rows may
            # already be GC'd within this transaction, and the mapping must survive that
            o_type, o_name, o_pred = r.object_type, r.object_name, r.object_predicate
            s_name, s_pred, s_type = r.subject_name, r.subject_predicate, r.subject_type
            fam = self.compiled.namespace.get((o_type, o_pred))
            if isinstance(fam, LeafFamily):
                assert not (o_name == '*'), \
                    'wildcard-object delta mapped to a derived key (decision-15 shape leaked)'
                key = (o_type, fam.owner_relation, o_name)
                if s_name == '*':
                    full(key)              # symbolic delta: §5.4 full-object rule
                elif self._node(s_pred, s_type, s_name) is None:
                    # subject node GC'd within this transaction: its id may linger in
                    # the residue's neg; a full reconcile recomputes neg from live
                    # candidates and prunes it (id-reuse hazard otherwise)
                    full(key)
                else:
                    subject(key, (s_pred, s_type, s_name))
                # a stored tuple of a derived TUPLESET changed: the parent set of its
                # tupleset-ttu dependents changed on this object (stored-tuple TTU
                # semantics -- membership changes alone don't move parents)
                for edge in self.compiled.dependents.get((o_type, fam.owner_relation), []):
                    if edge.via == 'tupleset-ttu':
                        full((edge.dependent[0], edge.dependent[1], o_name))
            elif isinstance(fam, DerivedFamily):
                self._fan_out((o_type, o_pred), o_name, keys, full)
            # a tupleset tuple appeared/vanished: the dependent on the SAME object
            for edge in self.compiled.tupleset_feeders.get((o_type, o_pred), []):
                full((edge.dependent[0], edge.dependent[1], o_name))
            for edge in self.compiled.target_feeders.get((o_type, o_pred), []):
                # delta on an (untainted) TTU target relation
                dep_t, dep_r = edge.dependent
                if edge.via == 'tupleset-ttu':
                    # dependents = objects holding a STORED tupleset tuple from this
                    # entity (on the derived tupleset's leaf families)
                    for obj_name in self._stored_parent_objects_of_entity(
                            o_type, o_name, dep_t, edge.tupleset_rel):
                        full((dep_t, dep_r, obj_name))
                else:   # 'ttu' (mixed-type untainted target of a PDerivedTTU)
                    # dependents = objects holding a tupleset tuple from this entity
                    ent = self._node('...', o_type, o_name)
                    if ent is None:
                        continue
                    for oid in self.idx.lookup_reachable(ent.id):
                        o2 = self.session.get(NodeV4, oid)
                        if o2 is not None and (o2.type, o2.predicate) == (dep_t, edge.tupleset_rel):
                            full((dep_t, dep_r, o2.name))
        return keys

    def _fan_out(self, source: tuple[str, str], obj_name: str,
                 keys: dict, full) -> None:
        """Dependent invalidations for a change of derived (source) @ obj (§5.2)."""
        for edge in self.compiled.dependents.get(source, []):
            dep_t, dep_r = edge.dependent
            if edge.via == 'computed':
                full((dep_t, dep_r, obj_name))
            elif edge.via == 'ttu':
                # dependents = objects holding a tupleset tuple FROM this object
                ent = self._node('...', source[0], obj_name)
                if ent is None:
                    continue
                for oid in self.idx.lookup_reachable(ent.id):
                    o = self.session.get(NodeV4, oid)
                    if o is not None and (o.type, o.predicate) == (dep_t, edge.tupleset_rel):
                        full((dep_t, dep_r, o.name))
            elif edge.via == 'userset':
                # dependents = objects granted-to by this userset node's stored tuples
                us_node = self._node(source[1], source[0], obj_name)
                if us_node is None:
                    continue
                for oid in self.idx.lookup_reachable(us_node.id):
                    o = self.session.get(NodeV4, oid)
                    if o is not None and (o.type, o.predicate) == (dep_t, edge.leaf):
                        full((dep_t, dep_r, o.name))
            elif edge.via == 'tupleset-ttu':
                if source[1] == edge.tupleset_rel:
                    # the derived tupleset itself changed: same object reconciles
                    full((dep_t, dep_r, obj_name))
                else:
                    # a (tainted) target changed: every object whose tupleset holds it
                    for on in self._derived_memberships_of_entity(
                            source[0], obj_name, dep_t, edge.tupleset_rel):
                        full((dep_t, dep_r, on))
            else:
                raise AssertionError(f'unknown dependency via {edge.via!r}')

    def run_cascade(self, txn_start_watermark: int) -> None:
        """The in-transaction cascade (§5.1): per stratum round, map the frontier's
        deltas (plus pending residue bumps) to keys, reconcile each, advance."""
        self.session.flush()
        frontier_start = txn_start_watermark
        rounds = len(self.compiled.strata)

        for _ in range(rounds):
            rows = outbox_rows(self.session, self.store_id, frontier_start)
            frontier_start = max((r.id for r in rows), default=frontier_start)

            keys = self._map_deltas_to_keys(rows)
            bumped, self._bumped = self._bumped, []
            for (b_type, b_rel, b_name) in bumped:
                self._fan_out((b_type, b_rel), b_name,
                              keys, lambda k: keys.__setitem__(k, None))

            if not keys:
                break

            # settle lower strata first inside the round (idempotent either way;
            # ordering just avoids provably-stale recomputes)
            def stratum_of(key: Key) -> int:
                return self.compiled.plans[(key[0], key[1])].stratum

            for key in sorted(keys, key=lambda k: (stratum_of(k), k)):
                object_type, rel, obj_name = key
                subjects = keys[key]
                if subjects is None:
                    self.reconcile(object_type, rel, obj_name)
                else:
                    for s in sorted(subjects):
                        self.reconcile_subject(object_type, rel, obj_name, s)
            self.session.flush()

        # quiescence (§5.1): stratification guarantees the cascade drains
        rows = outbox_rows(self.session, self.store_id, frontier_start)
        leftover = self._map_deltas_to_keys(rows)
        for (b_type, b_rel, b_name) in self._bumped:
            self._fan_out((b_type, b_rel), b_name,
                          leftover, lambda k: leftover.__setitem__(k, None))
        self._bumped = []
        if leftover:
            raise InvariantViolation(
                f'cascade failed to quiesce after {rounds} strata rounds; '
                f'leftover keys: {sorted(leftover)}')

    # ------------------------------------------------------------------ #
    # Backfill / bootstrap (§5.5)
    # ------------------------------------------------------------------ #

    def _live_keys_of(self, object_type: str, rel: str) -> set[str]:
        """Object names with any state under (object_type, rel): positive-leaf family
        nodes (subtrahends never generate candidates, only filter), the public node
        family, plus -- for derived leaves with no storage family of their own --
        the objects discoverable through what they read: tupleset-tuple families for
        TTU leaves, the referenced relation's own live keys for computed references.
        (Live maintenance reaches those objects via dependents-invalidation; backfill
        must reach them by enumeration.)"""
        names: set[str] = set()
        plan = self.compiled.plans[(object_type, rel)]
        preds = [rel] + [spec.predicate for spec in plan.leaves
                         if spec.positive and spec.kind in ('closure', 'derived-userset')]
        for pred in preds:
            rows = self.session.exec(
                select(NodeV4).where(NodeV4.store_id == self.store_id)
                .where(NodeV4.type == object_type).where(NodeV4.predicate == pred)
                .where(NodeV4.wildcard == '')
            ).all()
            names.update(n.name for n in rows)

        for spec in plan.leaves:
            if not spec.positive or spec.kind in ('closure', 'derived-userset'):
                continue
            if spec.kind == 'derived-computed':
                # same-object reference: any object live under the referenced relation
                names |= self._live_keys_of(object_type, spec.predicate)
            elif spec.kind == 'derived-ttu':
                # objects holding tupleset tuples: the (T, *, tupleset_rel) family
                node = self._find_leaf_node(spec, object_type)
                rows = self.session.exec(
                    select(NodeV4).where(NodeV4.store_id == self.store_id)
                    .where(NodeV4.type == object_type)
                    .where(NodeV4.predicate == node.tupleset_rel)
                    .where(NodeV4.wildcard == '')
                ).all()
                names.update(n.name for n in rows)
            elif spec.kind == 'derived-tupleset-ttu':
                # stored tuples of a derived tupleset live on ITS leaf families,
                # which its own live keys enumerate (strictly lower stratum)
                node = self._find_leaf_node(spec, object_type)
                names |= self._live_keys_of(object_type, node.tupleset_rel)
        return names

    def backfill(self, chunk_size: int = 200) -> None:
        """Bootstrap/repair derived state from existing leaf data (§5.5): per stratum
        in topo order, reconcile every object with any positive-leaf state. Chunked,
        idempotent, mirroring the wildcard ``backfill()`` precedent; doubles as the
        recovery path when I9 finds an inconsistent key."""
        for stratum in self.compiled.strata:
            for (object_type, rel) in stratum:
                names = sorted(self._live_keys_of(object_type, rel))
                for i in range(0, len(names), chunk_size):
                    for obj_name in names[i:i + chunk_size]:
                        self.reconcile(object_type, rel, obj_name)
                    self.session.flush()
        self._bumped = []

    # ------------------------------------------------------------------ #
    # I9 fixpoint audit (§8.2)
    # ------------------------------------------------------------------ #

    def audit_fixpoint(self) -> None:
        """I9: reconcile of every live derived key produces zero changes. On a hit,
        ``backfill()`` is the recovery path (§5.5)."""
        for stratum in self.compiled.strata:
            for (object_type, rel) in stratum:
                for obj_name in sorted(self._live_keys_of(object_type, rel)):
                    if self.reconcile(object_type, rel, obj_name):
                        raise InvariantViolation(
                            f'I9: reconcile of ({object_type}, {rel}, {obj_name}) was '
                            f'not a fixpoint -- derived state was stale')
        self._bumped = []
