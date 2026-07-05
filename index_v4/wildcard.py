"""
WildcardIndex: the wildcard-aware façade over ReachabilityIndex (spec §6/§7).

It materialises the interior wildcard hops as real ref-counted edges (bridges) at
write time, so that check() stays O(1): at most four point lookups on the unique
edge index, independent of data size or nesting depth. Only the two hops touching
the literal query endpoints stay virtual, covered by fixed probes (§3.1).

This layer does NOT commit; sessions/transactions remain the caller's job (mirrors
ReachabilityIndex). All errors raise; on cycle rejection the caller's rollback
restores consistency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import EllipsisType

from sqlmodel import select

from .core import ReachabilityIndex
from .models import NodeV4, PermissionDelta
from zanzibar_utils_v1 import SchemaInfo


@dataclass
class LookupResult:
    node_ids: set[int] = field(default_factory=set)               # concrete results
    markers: set[tuple[str, str, str]] = field(default_factory=set)  # (type, predicate, variant) symbolic "all/any"


def _norm_pred(predicate: str | EllipsisType) -> str:
    return '...' if predicate is Ellipsis else predicate


class WildcardIndex:
    def __init__(self, idx: ReachabilityIndex, schema_info: SchemaInfo):
        self.idx = idx
        self.schema_info = schema_info
        # Per-store cache of wildcard-node ids (spec §3.1: the set is tiny and changes
        # rarely). Read-only lookups (check/lookup) hit it; every write clears it, so it
        # can never go stale across an add/remove that creates or GCs a w node.
        self._w_id_cache: dict[tuple[str, str, str], int | None] = {}

    # ------------------------------------------------------------------ #
    # Node resolution (position rule §1.2 + validity §3.5)
    # ------------------------------------------------------------------ #

    def _resolve(self, predicate: str | EllipsisType, entity_type: str, name: str,
                 position: str, *, create: bool) -> NodeV4:
        """Apply the position rule and validate, returning (or creating) the node.

        subject '*' -> w_any(type, predicate); object '*' -> w_all(type, relation).
        """
        pred = _norm_pred(predicate)

        if name == '*':
            if position == 'subject':
                shape = (entity_type, pred)
                if shape not in self.schema_info.subject_wildcard_shapes:
                    raise ValueError(
                        f"subject wildcard {entity_type}:* (predicate {pred!r}) is not a declared "
                        f"subject-wildcard shape {shape}")
                variant = 'any'
            else:
                shape = (entity_type, pred)  # pred is the relation in object position
                if shape not in self.schema_info.object_wildcard_shapes:
                    raise ValueError(
                        f"object wildcard {entity_type}:* (relation {pred!r}) is not a declared "
                        f"object-wildcard shape {shape}")
                variant = 'all'
            return self.idx.node(pred, entity_type, '*', create_if_missing=create,
                                 implicit=True, wildcard=variant)

        # concrete node; node() rejects a bare name=='*' (reserved, §3.5.3)
        return self.idx.node(pred, entity_type, name, create_if_missing=create)

    def _w_node(self, entity_type: str, predicate: str, variant: str, *, create: bool) -> NodeV4 | None:
        """Fetch (or create) the w_any/w_all node for a shape, or None if absent."""
        try:
            return self.idx.node(predicate, entity_type, '*', create_if_missing=create,
                                 implicit=True, wildcard=variant)
        except KeyError:
            return None

    def _w_id(self, entity_type: str, predicate: str, variant: str) -> int | None:
        """Cached id of a w_any/w_all node (read path), or None if it doesn't exist."""
        key = (entity_type, predicate, variant)
        if key not in self._w_id_cache:
            node = self._w_node(entity_type, predicate, variant, create=False)
            self._w_id_cache[key] = node.id if node is not None else None
        return self._w_id_cache[key]

    def _invalidate_w_cache(self) -> None:
        self._w_id_cache.clear()

    def _bridge_degree(self, shape: tuple[str, str]) -> int:
        return ((1 if shape in self.schema_info.bridged_in_shapes else 0)
                + (1 if shape in self.schema_info.bridged_out_shapes else 0))

    # ------------------------------------------------------------------ #
    # Bridge lifecycle (§7)
    # ------------------------------------------------------------------ #

    def _ensure_bridges(self, node: NodeV4) -> None:
        """Lazily create the configured bridges for a concrete node (idempotent)."""
        if node.wildcard != '':          # only concretes are bridged
            return
        shape = (node.type, node.predicate)
        if shape in self.schema_info.bridged_in_shapes:
            w_any = self.idx.node(node.predicate, node.type, '*', create_if_missing=True,
                                  implicit=True, wildcard='any')
            if not self.idx.direct_edge_exists_by_id(node.id, w_any.id):
                self.idx.add_edge_by_id(node.id, w_any.id)          # concrete -> w_any (bridge)
        if shape in self.schema_info.bridged_out_shapes:
            w_all = self.idx.node(node.predicate, node.type, '*', create_if_missing=True,
                                  implicit=True, wildcard='all')
            if not self.idx.direct_edge_exists_by_id(w_all.id, node.id):
                self.idx.add_edge_by_id(w_all.id, node.id)          # w_all -> concrete (bridge)

    def _maybe_remove_bridges(self, node: NodeV4) -> None:
        """If a concrete node's only remaining edges are its bridges, strip them so the
        core's implicit GC deletes it (§7.3)."""
        if node.wildcard != '':
            return
        shape = (node.type, node.predicate)
        degree = self._bridge_degree(shape)
        if degree == 0:
            return
        fresh = self._node_by_id(node.id)
        if fresh is None:
            return                                                  # already collected
        if not (fresh.implicit and fresh.reference_count == degree):
            return
        if shape in self.schema_info.bridged_in_shapes:
            w_any = self._w_node(node.type, node.predicate, 'any', create=False)
            if w_any is not None and self.idx.direct_edge_exists_by_id(fresh.id, w_any.id):
                self.idx.remove_edge_by_id(fresh.id, w_any.id)
        # re-fetch: the first removal may already have collected the node
        fresh = self._node_by_id(node.id)
        if fresh is None:
            return
        if shape in self.schema_info.bridged_out_shapes:
            w_all = self._w_node(node.type, node.predicate, 'all', create=False)
            if w_all is not None and self.idx.direct_edge_exists_by_id(w_all.id, fresh.id):
                self.idx.remove_edge_by_id(w_all.id, fresh.id)

    def _node_by_id(self, node_id: int) -> NodeV4 | None:
        return self.idx.session.exec(
            select(NodeV4)
            .where(NodeV4.store_id == self.idx.store_id)
            .where(NodeV4.id == node_id)
        ).first()

    def _concrete_nodes_of_shape(self, entity_type: str, predicate: str) -> list[NodeV4]:
        return list(self.idx.session.exec(
            select(NodeV4)
            .where(NodeV4.store_id == self.idx.store_id)
            .where(NodeV4.type == entity_type)
            .where(NodeV4.predicate == predicate)
            .where(NodeV4.wildcard == '')
        ).all())

    def backfill(self) -> None:
        """Ensure every existing concrete of a bridged shape has its bridges (§7.2).

        Idempotent; safe to call always. Does not create a w node for a shape that has
        no concrete instances (avoids orphan wildcard nodes)."""
        self._invalidate_w_cache()
        for shape in self.schema_info.bridged_in_shapes:
            entity_type, predicate = shape
            concretes = self._concrete_nodes_of_shape(entity_type, predicate)
            if not concretes:
                continue
            w_any = self.idx.node(predicate, entity_type, '*', create_if_missing=True,
                                  implicit=True, wildcard='any')
            for c in concretes:
                if not self.idx.direct_edge_exists_by_id(c.id, w_any.id):
                    self.idx.add_edge_by_id(c.id, w_any.id)
        for shape in self.schema_info.bridged_out_shapes:
            entity_type, predicate = shape
            concretes = self._concrete_nodes_of_shape(entity_type, predicate)
            if not concretes:
                continue
            w_all = self.idx.node(predicate, entity_type, '*', create_if_missing=True,
                                  implicit=True, wildcard='all')
            for c in concretes:
                if not self.idx.direct_edge_exists_by_id(w_all.id, c.id):
                    self.idx.add_edge_by_id(w_all.id, c.id)

    # ------------------------------------------------------------------ #
    # Writes (§6)
    # ------------------------------------------------------------------ #

    def add_tuple(self, subject_predicate: str | EllipsisType, s_type: str, s_name: str,
                  relation: str, o_type: str, o_name: str) -> list[PermissionDelta]:
        self._invalidate_w_cache()
        subject = self._resolve(subject_predicate, s_type, s_name, 'subject', create=True)
        obj = self._resolve(relation, o_type, o_name, 'object', create=True)

        # Bridge-before-grant: cycle errors then attach to the grant (the offending write).
        self._ensure_bridges(subject)
        self._ensure_bridges(obj)

        try:
            return self.idx.add_edge_by_id(subject.id, obj.id)
        except ValueError as e:
            if 'cycle' in str(e) and (subject.wildcard != '' or obj.wildcard != ''):
                raise ValueError(
                    "wildcard tuple rejected: a wildcard tuple whose object participates in the "
                    "wildcard's own shape forms a cycle and is unsupported by construction "
                    f"({s_type}:{s_name}#{_norm_pred(subject_predicate)} {relation} {o_type}:{o_name})"
                ) from e
            raise

    def remove_tuple(self, subject_predicate: str | EllipsisType, s_type: str, s_name: str,
                     relation: str, o_type: str, o_name: str) -> list[PermissionDelta]:
        self._invalidate_w_cache()
        subject = self._resolve(subject_predicate, s_type, s_name, 'subject', create=False)
        obj = self._resolve(relation, o_type, o_name, 'object', create=False)

        deltas = self.idx.remove_edge_by_id(subject.id, obj.id)

        # GC bridges for concrete endpoints whose only remaining edges are their bridges.
        self._maybe_remove_bridges(subject)
        self._maybe_remove_bridges(obj)
        return deltas

    # ------------------------------------------------------------------ #
    # Reads (§3.1)
    # ------------------------------------------------------------------ #

    def check(self, subject_predicate: str | EllipsisType, s_type: str, s_name: str,
              relation: str, o_type: str, o_name: str) -> bool:
        s_pred = _norm_pred(subject_predicate)
        subj_is_star = (s_name == '*')
        obj_is_star = (o_name == '*')

        subject_shape_declared = (s_type, s_pred) in self.schema_info.subject_wildcard_shapes
        object_shape_declared = (o_type, relation) in self.schema_info.object_wildcard_shapes

        # Resolve up to 4 node ids (w-ids cached), then up to 4 point-lookup edge reads.
        # A literal '*' query endpoint maps to its own variant node in probe 1.
        if subj_is_star:
            subj_id = self._w_id(s_type, s_pred, 'any')
        else:
            subj = self._get_concrete(s_pred, s_type, s_name)
            subj_id = subj.id if subj is not None else None
        if obj_is_star:
            obj_id = self._w_id(o_type, relation, 'all')
        else:
            obj = self._get_concrete(relation, o_type, o_name)
            obj_id = obj.id if obj is not None else None

        def reach(a_id: int | None, b_id: int | None) -> bool:
            return a_id is not None and b_id is not None and self.idx.check_reachable_by_id(a_id, b_id)

        # Probe 1: (subject) -> (object)
        if reach(subj_id, obj_id):
            return True

        # Probe 2: w_any(s_type, s_pred) -> (object)
        if not subj_is_star and subject_shape_declared:
            if reach(self._w_id(s_type, s_pred, 'any'), obj_id):
                return True

        # Probe 3: (subject) -> w_all(o_type, relation)
        if not obj_is_star and object_shape_declared:
            if reach(subj_id, self._w_id(o_type, relation, 'all')):
                return True

        # Probe 4: w_any(...) -> w_all(...)
        if (not subj_is_star and subject_shape_declared
                and not obj_is_star and object_shape_declared):
            if reach(self._w_id(s_type, s_pred, 'any'), self._w_id(o_type, relation, 'all')):
                return True

        return False

    def _get_concrete(self, predicate: str, entity_type: str, name: str) -> NodeV4 | None:
        try:
            return self.idx.node(predicate, entity_type, name, create_if_missing=False)
        except KeyError:
            return None

    def lookup(self, subject_predicate: str | EllipsisType, s_type: str, s_name: str) -> LookupResult:
        """Everything the subject can reach. Concrete targets go in node_ids; any wildcard
        node reached becomes a symbolic marker (spec §6) -- never enumerated to concretes."""
        s_pred = _norm_pred(subject_predicate)
        result = LookupResult()

        if s_name == '*':
            self._collect_reachable(self._w_node(s_type, s_pred, 'any', create=False), result)
        else:
            self._collect_reachable(self._get_concrete(s_pred, s_type, s_name), result)
            if (s_type, s_pred) in self.schema_info.subject_wildcard_shapes:
                self._collect_reachable(self._w_node(s_type, s_pred, 'any', create=False), result)
        return result

    def lookup_reverse(self, relation: str, o_type: str, o_name: str) -> LookupResult:
        """Everything that can reach the object. Symmetric with lookup: w_all/w_any nodes
        in the reverse set become symbolic markers (e.g. 'every T#P')."""
        result = LookupResult()

        if o_name == '*':
            self._collect_reverse(self._w_node(o_type, relation, 'all', create=False), result)
        else:
            self._collect_reverse(self._get_concrete(relation, o_type, o_name), result)
            if (o_type, relation) in self.schema_info.object_wildcard_shapes:
                self._collect_reverse(self._w_node(o_type, relation, 'all', create=False), result)
        return result

    def _collect_reachable(self, node: NodeV4 | None, result: LookupResult) -> None:
        if node is None:
            return
        for nid in self.idx.lookup_reachable(node.id):
            self._classify_into(nid, result)

    def _collect_reverse(self, node: NodeV4 | None, result: LookupResult) -> None:
        if node is None:
            return
        for nid in self.idx.lookup_reverse(node.id):
            self._classify_into(nid, result)

    def _classify_into(self, node_id: int, result: LookupResult) -> None:
        n = self._node_by_id(node_id)
        if n is None:
            return
        if n.wildcard == '':
            result.node_ids.add(node_id)
        else:
            result.markers.add((n.type, n.predicate, n.wildcard))
