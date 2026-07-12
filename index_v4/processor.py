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
        sp, st, sn = s
        stored = self.proc.stored_userset_subjects(self.object_type, self.obj_name, leaf, t, p)
        # "this exact userset is granted" (Zanzibar/oracle direct_leaf semantics --
        # blind-audit): the stored userset row itself is a member, regardless of its
        # own membership set
        if (st, sp) == (t, p) and sn in stored:
            return True
        for x_name in stored:
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
        sp, st, sn = s
        for (pt, pn) in self.proc.tupleset_parents(self.object_type, self.obj_name, ts, parent_types):
            # from-chain identity rule (oracle ttu_leaf; lookup-gate X4a): a stored
            # tupleset parent p makes the userset p#target itself a member,
            # regardless of the target relation's own content -- the exact analogue
            # of the untainted path's materialized rewrite edge
            if (sp, st, sn) == (target, pt, pn):
                return True
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
        sp, st, sn = s
        for (pt, pn) in self.proc.derived_stored_parents(self.object_type, self.obj_name,
                                                         ts, parent_types):
            if (sp, st, sn) == (target, pt, pn):
                return True         # from-chain identity rule (oracle ttu_leaf; X4a)
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
        # spec -> plan-tree node, by identity (blind-audit P2: two same-target TTU
        # leaves carry EQUAL specs, so the pairing must be positional/identity,
        # never by name). Built once; specs stay alive on their Plan's tuples.
        self._leaf_node_by_spec = {
            id(spec): node
            for plan in compiled.plans.values()
            for spec, node in zip(plan.leaves, plan.leaf_nodes)
        }
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
                       ) -> tuple[frozenset, set[int], set[int]]:
        return self.widx._residue_state(rel, object_type, obj_name)

    def residue_stars(self, object_type: str, rel: str, obj_name: str) -> frozenset:
        return self._residue_state(object_type, rel, obj_name)[0]

    def derived_check(self, object_type: str, rel: str, obj_name: str, s: SubjectKey) -> bool:
        """The §6 derived membership check: edge probe + residue (point reads).

        Delegates to the façade's ``_check_derived`` -- the read path and the
        processor's reconcile MUST share one implementation, or a semantics fix in
        one (e.g. the blind-audit P4 upos rule) silently diverges the other."""
        sp, st, sn = s
        return self.widx._check_derived(sp, st, sn, rel, object_type, obj_name)

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

    def _keys_referencing(self, node_id: int) -> list[Key]:
        """Reconcile keys of every residue whose ``neg``/``upos`` records this subject
        node id. Cross-object memberships (TTU from-chain usersets and lifted userset
        memberships, lookup-gate X4) are NOT justified by an edge on the recording
        object, so the recorder must be findable from the id alone -- both for GC
        anchoring and for pruning when the node dies."""
        out: list[Key] = []
        rows = self.session.exec(
            select(ResidueV1).where(ResidueV1.store_id == self.store_id)).all()
        for row in rows:
            if node_id in json.loads(row.neg) or node_id in json.loads(row.upos):
                obj = self.session.get(NodeV4, row.object_node_id)
                if obj is not None:
                    out.append((obj.type, obj.predicate, obj.name))
        return out

    def _residue_references(self, node_id: int) -> bool:
        return bool(self._keys_referencing(node_id))

    def _from_chain_keys(self, object_type: str, obj_name: str, plan) -> list[SubjectKey]:
        """The from-chain userset subjects of every TTU leaf (any polarity): one key
        ``(target_rel, parent_type, parent_name)`` per stored tupleset parent (oracle
        ttu_leaf identity rule; lookup-gate X4a). Key-level -- the subjects need not
        have nodes."""
        keys: dict[SubjectKey, None] = {}
        for spec, node in zip(plan.leaves, plan.leaf_nodes):
            if spec.kind == 'derived-ttu':
                parents = self.tupleset_parents(object_type, obj_name,
                                                node.tupleset_rel, node.parent_types)
            elif spec.kind == 'derived-tupleset-ttu':
                parents = self.derived_stored_parents(object_type, obj_name,
                                                      node.tupleset_rel, node.parent_types)
            else:
                continue
            for (pt, pn) in parents:
                keys[(node.target_rel, pt, pn)] = None
        return list(keys)

    def _ttu_target_upos_nodes(self, parents: list[tuple[str, str]], target: str
                               ) -> list[NodeV4]:
        """Live userset-shaped members recorded in a tainted TTU target's residues
        (``upos``): usersets hold no edges (P4), so the dependent's enumeration must
        read them from the parents' residues, not the closure (lookup-gate X4b)."""
        out: list[NodeV4] = []
        for (pt, pn) in parents:
            if (pt, target) not in self.compiled.tainted:
                continue
            for nid in self._residue_state(pt, target, pn)[2]:
                n = self.session.get(NodeV4, nid)
                if n is not None:
                    out.append(n)
        return out

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
        """Cheap path: reconcile one subject's membership representation.

        Canonical representation (deterministic across op orders, and the space rule
        'star-only members: zero edges'):
          * star-covered subjects hold NO edge -- they are answered by the residue:
            in ``neg`` iff expr-false;
          * uncovered BARE-ENTITY subjects hold an edge iff expr-true;
          * USERSET subjects never hold edges (a userset edge leaks through the
            closure to every member, defeating pointwise exclusion -- blind-audit
            P4): uncovered ones are in ``upos`` iff expr-true.
        Returns True iff anything changed."""
        plan = self.compiled.plans[(object_type, rel)]
        ctx = _EvalContext(self, object_type, obj_name)
        should = bool(plan.check_fn(ctx, s))

        sp, st, sn = s
        changed = False

        stars, neg, upos = self._residue_state(object_type, rel, obj_name)
        covered = _shape(sp, st) in stars
        s_node = self._node(sp, st, sn)

        if sp != '...':
            # userset subject: upos, never edges
            if s_node is not None:
                want_upos = should and not covered
                want_neg = covered and not should
                if want_upos != (s_node.id in upos) or want_neg != (s_node.id in neg):
                    (upos.add if want_upos else upos.discard)(s_node.id)
                    (neg.add if want_neg else neg.discard)(s_node.id)
                    self._store_residue(object_type, rel, obj_name, stars, neg, upos)
                    changed = True
                    if not want_upos and not want_neg:
                        self._gc_subject_node(s_node.id)
            if changed:
                self._gc_public_node(object_type, rel, obj_name)
            return changed

        want_edge = should and not covered
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
                self._store_residue(object_type, rel, obj_name, stars, neg, upos)
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

        # (2a) from-chain userset subjects of TTU leaves (oracle ttu_leaf identity
        #      rule; lookup-gate X4a). Evaluated by KEY -- a from-chain userset may
        #      have no node. A node is interned ONLY when the outcome must be
        #      recorded (upos: true+uncovered / neg: false+covered); the two
        #      residue-free outcomes are already answered exactly by the read path
        #      (covered+true -> stars, uncovered+false -> miss).
        for s in self._from_chain_keys(object_type, obj_name, plan):
            sp, st, sn = s
            n = self._node(sp, st, sn)
            if n is None:
                covered = _shape(sp, st) in stars
                should = bool(plan.check_fn(ctx, s))
                if should == covered:
                    continue
                n = self.idx.node(sp, st, sn, create_if_missing=True)
                # I3: a fresh concrete of a bridged shape must get its bridges
                self.widx._ensure_bridges(n)
            candidates[n.id] = n

        neg: set[int] = set()
        for nid, n in candidates.items():
            if _shape(n.predicate, n.type) not in stars:
                continue
            if not plan.check_fn(ctx, (n.predicate, n.type, n.name)):
                neg.add(nid)

        # (2b) audit set: current derived incoming concretes ∪ concretes of every
        #      positive leaf ∪ step-2 candidates ∪ current upos members.
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
        old_stars, old_neg, old_upos = self._residue_state(object_type, rel, obj_name)
        for nid in old_upos:
            n = self.session.get(NodeV4, nid)
            if n is not None:
                audit[n.id] = n

        # (2c) upos: userset-shaped audit members, recomputed wholesale (blind-audit
        #      P4 -- userset memberships are edge-free; wholesale recompute prunes
        #      stale ids the same way neg's does).
        upos: set[int] = set()
        for nid, n in audit.items():
            if n.predicate == '...' or n.wildcard != '':
                continue
            if _shape(n.predicate, n.type) in stars:
                continue                        # covered: answered by stars/neg
            if plan.check_fn(ctx, (n.predicate, n.type, n.name)):
                upos.add(nid)

        # (3) upsert/delete the residue iff changed.
        residue_changed = (stars != old_stars) or (neg != old_neg) or (upos != old_upos)
        if residue_changed:
            self._store_residue(object_type, rel, obj_name, stars, neg, upos)

        # (4) edge audit over BARE-ENTITY subjects (userset subjects were settled in
        #     2c and must never hold edges -- P4).
        edges_changed = False
        for n in audit.values():
            if n.predicate != '...':
                continue
            edges_changed |= self.reconcile_subject(
                object_type, rel, obj_name, (n.predicate, n.type, n.name))

        # (5) subject-node GC: ids dropped from neg/upos may have been interned
        #     solely to anchor a cross-object recording (from-chain usersets, X4a);
        #     once nothing references them they must go, or add-then-remove stops
        #     being a row-multiset round trip.
        if residue_changed:
            for nid in (old_neg | old_upos) - (neg | upos):
                self._gc_subject_node(nid)

        if residue_changed or edges_changed:
            self._gc_public_node(object_type, rel, obj_name)
        return residue_changed or edges_changed

    def _gc_subject_node(self, node_id: int) -> None:
        """Delete a recorded-subject node that anchors nothing anymore: edge-free,
        residue-less, and referenced by no residue's neg/upos. Mirrors
        ``_gc_public_node``'s policy for processor-created state (lookup-gate X4a:
        from-chain userset nodes are interned by ``reconcile`` and must be collected
        when their recording is dropped)."""
        n = self.session.get(NodeV4, node_id)
        if n is None or n.store_id != self.store_id or n.wildcard != '':
            return
        if self._residue_row(n.id) is not None or self._residue_references(n.id):
            return
        # strip pure-bridge scaffolding first (implicit GC then collects the node)
        self.widx._maybe_remove_bridges(n)
        n = self.session.get(NodeV4, node_id)
        if n is not None and n.reference_count == 0:
            self.session.delete(n)

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
            tree_node = self._find_leaf_node(spec)
            for x in self.stored_userset_subjects(object_type, obj_name, spec.predicate,
                                                  tree_node.subject_type,
                                                  tree_node.subject_predicate):
                out |= self._residue_state(tree_node.subject_type,
                                           tree_node.subject_predicate, x)[1]
            return out
        if spec.kind == 'derived-ttu':
            node = self._find_leaf_node(spec)
            out = set()
            for (pt, pn) in self.tupleset_parents(object_type, obj_name,
                                                  node.tupleset_rel, node.parent_types):
                if (pt, node.target_rel) in self.compiled.tainted:
                    out |= self._residue_state(pt, node.target_rel, pn)[1]
            return out
        if spec.kind == 'derived-tupleset-ttu':
            node = self._find_leaf_node(spec)
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
            node = self._find_leaf_node(spec)
            out: dict[int, NodeV4] = {}
            parents = self.tupleset_parents(object_type, obj_name,
                                            node.tupleset_rel, node.parent_types)
            for (pt, pn) in parents:
                p_node = self._node(node.target_rel, pt, pn)
                if p_node is not None:
                    for n in self._incoming_concretes(p_node.id):
                        out[n.id] = n
            # userset members of tainted targets are edge-free (P4): lift them from
            # the parents' residue upos, or the dependent never sees them (X4b)
            for n in self._ttu_target_upos_nodes(parents, node.target_rel):
                out[n.id] = n
            return list(out.values())
        if spec.kind == 'derived-tupleset-ttu':
            node = self._find_leaf_node(spec)
            out = {}
            parents = self.derived_stored_parents(object_type, obj_name,
                                                  node.tupleset_rel, node.parent_types)
            for (pt, pn) in parents:
                p_node = self._node(node.target_rel, pt, pn)
                if p_node is not None:
                    for n in self._incoming_concretes(p_node.id):
                        out[n.id] = n
            for n in self._ttu_target_upos_nodes(parents, node.target_rel):
                out[n.id] = n           # X4b, derived-tupleset variant
            return list(out.values())
        raise TypeError(f'unknown leaf kind {spec.kind!r}')

    def _find_leaf_node(self, spec):
        """The plan-tree node for a leaf spec, via the compile-time index-aligned
        pairing (blind-audit P2: reconstructing this by name resolved two
        same-target TTU leaves to the same node, silently dropping one tupleset's
        parents -- and audit_fixpoint shared the blindness). Identity match: specs
        handed to us always come from a plan's own ``leaves`` tuple."""
        node = self._leaf_node_by_spec.get(id(spec))
        if node is None:
            raise AssertionError(f'plan node not found for leaf {spec}')
        return node

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
        if self._residue_references(node.id):
            # the node doubles as a recorded SUBJECT in another object's residue
            # (from-chain userset, X4a): deleting it would dangle that id -- the
            # recording reconcile collects it once the reference is dropped
            return
        self.session.delete(node)

    def _store_residue(self, object_type: str, rel: str, obj_name: str,
                       stars: frozenset, neg: set[int], upos: set[int]) -> None:
        """Upsert/delete the residue row; bump version; record the bump for dependent
        invalidation. Empty residues are deleted, never stored (spec §4)."""
        # The processor may intern the public object node on the write path (spec §4);
        # non-implicit so residue-only objects (star coverage, zero edges) survive GC.
        node = self.idx.node(rel, object_type, obj_name, create_if_missing=True, implicit=False)
        row = self._residue_row(node.id)
        empty = not stars and not neg and not upos
        if row is None:
            if empty:
                return
            self.session.add(ResidueV1(
                store_id=self.store_id, object_node_id=node.id, relation=rel,
                stars=json.dumps(sorted([list(s) for s in stars])),
                neg=json.dumps(sorted(neg)), upos=json.dumps(sorted(upos)), version=1))
        elif empty:
            self.session.delete(row)
        else:
            row.stars = json.dumps(sorted([list(s) for s in stars]))
            row.neg = json.dumps(sorted(neg))
            row.upos = json.dumps(sorted(upos))
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
            if self.session.get(NodeV4, r.subject_node_id) is None:
                # the subject node was GC'd in this transaction: cross-object
                # recordings of its id (from-chain/lifted userset memberships, X4)
                # are not edge-justified on the recording object, so no other delta
                # reaches them -- reconcile every residue still holding the id
                for ref_key in self._keys_referencing(r.subject_node_id):
                    full(ref_key)
            fam = self.compiled.namespace.get((o_type, o_pred))
            if isinstance(fam, LeafFamily):
                assert not (o_name == '*'), \
                    'wildcard-object delta mapped to a derived key (decision-15 shape leaked)'
                key = (o_type, fam.owner_relation, o_name)
                if s_name == '*':
                    full(key)              # symbolic delta: §5.4 full-object rule
                elif fam.kind == 'userset-storage' and s_pred != '...':
                    # a stored userset tuple arrived/left: the dependent's stars
                    # (userset_stars) and neg candidates change, and star-covered
                    # members of the userset hold no edges to invalidate them --
                    # the cheap path left order-dependent stale state (blind-audit
                    # P3: symbolic in effect, so full-object like §5.4)
                    full(key)
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
                    # a (tainted) TTU target changed: dependents are the objects
                    # holding a STORED tupleset tuple from this entity (blind-audit
                    # P1: this called a method deleted in the stored-tuple-semantics
                    # rework -- any derived tupleset with a tainted target crashed)
                    for on in self._stored_parent_objects_of_entity(
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
                node = self._find_leaf_node(spec)
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
                node = self._find_leaf_node(spec)
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
