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

import json
from dataclasses import dataclass, field
from types import EllipsisType

from sqlalchemy import tuple_
from sqlmodel import select

from .core import ReachabilityIndex
from .models import EdgeV4, NodeV4, ResidueV1
from zanzibar_utils_v1 import SchemaInfo, validate_write_identifiers


@dataclass
class LookupResult:
    node_ids: set[int] = field(default_factory=set)               # concrete results
    markers: set[tuple[str, str, str]] = field(default_factory=set)  # (type, predicate, variant) symbolic "all/any"
    # "everyone of a starred shape EXCEPT these" (boolean spec §6): concrete node ids
    # excluded from a derived relation's star coverage, from the residue's neg.
    # Additive and empty everywhere except derived lookup_reverse.
    excluded_node_ids: set[int] = field(default_factory=set)


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
        # Derived-family write exclusivity (boolean spec §3.3/I5): only the delta
        # processor may write incoming direct edges on a derived-public family. The
        # processor sets this flag around its own writes.
        self.processor_writes = False

    def _assert_derived_exclusivity(self, relation: str, o_type: str) -> None:
        if self.processor_writes:
            return
        if (o_type, relation) in self.schema_info.derived_families:
            raise ValueError(
                f"relation {relation!r} on {o_type} is a derived (boolean) relation; "
                f"its edges are processor-maintained -- tuples must be routed through "
                f"RuleSet.apply, which rewrites them onto the leaf families")

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
        """Cached id of a w_any/w_all node (read path), or None if it doesn't exist.

        Misses are NOT cached: another session may create the w node at any time (the
        replica-reader pattern), and a cached None would pin its probes off forever.
        A cached positive id stays safe -- a GC'd w node had no wildcard state left,
        so probing its dead id is correctly False."""
        key = (entity_type, predicate, variant)
        cached = self._w_id_cache.get(key)
        if cached is None:
            node = self._w_node(entity_type, predicate, variant, create=False)
            if node is None:
                return None
            self._w_id_cache[key] = cached = node.id
        return cached

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

    def _derived_write_ctx(self, relation: str, o_type: str) -> bool:
        """True iff this write is the processor writing into a derived-public family
        (flags the direct edge row EdgeV4.derived; boolean spec §4/I5)."""
        return self.processor_writes and (o_type, relation) in self.schema_info.derived_families

    def add_tuple(self, subject_predicate: str | EllipsisType, s_type: str, s_name: str,
                  relation: str, o_type: str, o_name: str) -> None:
        """Add one (possibly rewrite-derived) triple as a ref-counted direct edge.

        ⚠ MULTIGRAPH SEMANTICS, deliberately: adding the same triple twice counts to
        2 and takes two removes to retire. That is load-bearing for rewrite fan-in
        (two different raw tuples may derive the same edge and must retire
        independently) -- it is NOT the raw-tuple API. Zanzibar raw tuples are a SET;
        set-semantics idempotence lives one layer up, at the tuple boundary
        (connectedstore.TupleSource / the harness adapters). Do not feed raw user
        writes here directly unless you deduplicate them yourself."""
        validate_write_identifiers(subject_predicate, s_type, s_name, relation, o_type, o_name)
        self._assert_derived_exclusivity(relation, o_type)
        self._invalidate_w_cache()
        subject = self._resolve(subject_predicate, s_type, s_name, 'subject', create=True)
        obj = self._resolve(relation, o_type, o_name, 'object', create=True)

        # Bridge-before-grant: cycle errors then attach to the grant (the offending write).
        self._ensure_bridges(subject)
        self._ensure_bridges(obj)

        self.idx._writing_derived = self._derived_write_ctx(relation, o_type)
        try:
            self.idx.add_edge_by_id(subject.id, obj.id)
        except ValueError as e:
            if 'cycle' in str(e) and (subject.wildcard != '' or obj.wildcard != ''):
                raise ValueError(
                    "wildcard tuple rejected: a wildcard tuple whose object participates in the "
                    "wildcard's own shape forms a cycle and is unsupported by construction "
                    f"({s_type}:{s_name}#{_norm_pred(subject_predicate)} {relation} {o_type}:{o_name})"
                ) from e
            raise
        finally:
            self.idx._writing_derived = False

    def remove_tuple(self, subject_predicate: str | EllipsisType, s_type: str, s_name: str,
                     relation: str, o_type: str, o_name: str) -> None:
        validate_write_identifiers(subject_predicate, s_type, s_name, relation, o_type, o_name)
        self._assert_derived_exclusivity(relation, o_type)
        self._invalidate_w_cache()
        try:
            subject = self._resolve(subject_predicate, s_type, s_name, 'subject', create=False)
            obj = self._resolve(relation, o_type, o_name, 'object', create=False)
        except KeyError as e:
            # Same rejection family as core.remove_edge and the set engine (validity
            # parity): a remove of a never-seen endpoint is a ValueError rejection.
            raise ValueError('Non-existent edge cannot be removed') from e

        self.idx.remove_edge_by_id(subject.id, obj.id)

        # GC bridges for concrete endpoints whose only remaining edges are their bridges.
        self._maybe_remove_bridges(subject)
        self._maybe_remove_bridges(obj)

    # ------------------------------------------------------------------ #
    # Reads (§3.1)
    # ------------------------------------------------------------------ #

    def check(self, subject_predicate: str | EllipsisType, s_type: str, s_name: str,
              relation: str, o_type: str, o_name: str) -> bool:
        s_pred = _norm_pred(subject_predicate)

        # Derived (boolean) relations: edge probe + residue, no wildcard probes --
        # derived relations are never wildcard shapes; symbolic state lives in the
        # residue (boolean spec §6).
        if (o_type, relation) in self.schema_info.derived_families:
            return self._check_derived(s_pred, s_type, s_name, relation, o_type, o_name)

        subj_is_star = (s_name == '*')
        obj_is_star = (o_name == '*')

        subject_shape_declared = (s_type, s_pred) in self.schema_info.subject_wildcard_shapes
        object_shape_declared = (o_type, relation) in self.schema_info.object_wildcard_shapes

        # Resolve up to 4 node ids (w-ids cached). A literal '*' query endpoint maps
        # to its own variant node in probe 1; a missing node simply drops its keys
        # (ghosts thus retain their star-probe coverage).
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

        keys: list[tuple[int, int]] = []

        def key(a_id: int | None, b_id: int | None) -> None:
            if a_id is not None and b_id is not None:
                keys.append((a_id, b_id))

        key(subj_id, obj_id)                                             # probe 1
        w_any_id = (self._w_id(s_type, s_pred, 'any')
                    if not subj_is_star and subject_shape_declared else None)
        w_all_id = (self._w_id(o_type, relation, 'all')
                    if not obj_is_star and object_shape_declared else None)
        key(w_any_id, obj_id)                                            # probe 2
        key(subj_id, w_all_id)                                           # probe 3
        key(w_any_id, w_all_id)                                          # probe 4

        if not keys:
            return False

        # ONE SQL round trip for all probes (boolean spec §1.14 / §6): the candidate
        # keys go into a single row-value IN with LIMIT 1.
        row = self.idx.session.exec(
            select(EdgeV4.id)
            .where(EdgeV4.store_id == self.idx.store_id)
            .where(tuple_(EdgeV4.subject_id, EdgeV4.object_id).in_(keys))
            .where(EdgeV4.indirect_edge_count > 0)  # type: ignore[arg-type]
            .limit(1)
        ).first()
        return row is not None

    # ------------------------------------------------------------------ #
    # Derived reads (boolean spec §6)
    # ------------------------------------------------------------------ #

    def _residue_state(self, relation: str, o_type: str, o_name: str
                       ) -> tuple[frozenset, set[int]]:
        """(stars, neg) of the derived relation's residue; empty if no row/node.
        Read-only: never interns."""
        node = self._get_concrete(relation, o_type, o_name)
        if node is None:
            return frozenset(), set()
        row = self.idx.session.exec(
            select(ResidueV1)
            .where(ResidueV1.store_id == self.idx.store_id)
            .where(ResidueV1.object_node_id == node.id)
        ).first()
        if row is None:
            return frozenset(), set()
        return frozenset(tuple(s) for s in json.loads(row.stars)), set(json.loads(row.neg))

    def _check_derived(self, s_pred: str, s_type: str, s_name: str,
                       relation: str, o_type: str, o_name: str) -> bool:
        if o_name == '*':
            # object wildcards on derived relations are rejected at compile (decision
            # 15): no object-star state can exist, so the intensional query is False
            return False
        if s_name == '*':
            # intensional: is the whole shape covered? (1 residue read)
            stars, _ = self._residue_state(relation, o_type, o_name)
            return (s_type, s_pred) in stars

        # probe 1 only: the derived edge (public family)
        subj = self._get_concrete(s_pred, s_type, s_name)
        obj = self._get_concrete(relation, o_type, o_name)
        if subj is not None and obj is not None \
                and self.idx.check_reachable_by_id(subj.id, obj.id):
            return True

        # residue: star coverage minus neg; a ghost subject has no node and thus
        # cannot be in neg -- the stars answer alone.
        stars, neg = self._residue_state(relation, o_type, o_name)
        if (s_type, s_pred) not in stars:
            return False
        return subj is None or subj.id not in neg

    def _get_concrete(self, predicate: str, entity_type: str, name: str) -> NodeV4 | None:
        try:
            return self.idx.node(predicate, entity_type, name, create_if_missing=False)
        except KeyError:
            return None

    def lookup(self, subject_predicate: str | EllipsisType, s_type: str, s_name: str) -> LookupResult:
        """Everything the subject can reach. Concrete targets go in node_ids; any wildcard
        node reached becomes a symbolic marker (spec §6) -- never enumerated to concretes.

        Derived relations contribute twice (boolean spec §6): materialised derived
        edges arrive through the ordinary reachable set, and star-covered memberships
        come from a residue scan (shape ∈ stars ∧ subject ∉ neg)."""
        s_pred = _norm_pred(subject_predicate)
        result = LookupResult()

        if s_name == '*':
            self._collect_reachable(self._w_node(s_type, s_pred, 'any', create=False), result)
        else:
            self._collect_reachable(self._get_concrete(s_pred, s_type, s_name), result)
            if (s_type, s_pred) in self.schema_info.subject_wildcard_shapes:
                self._collect_reachable(self._w_node(s_type, s_pred, 'any', create=False), result)

        if self.schema_info.derived_families:
            self._collect_residue_memberships(s_pred, s_type, s_name, result)
        return result

    def _collect_residue_memberships(self, s_pred: str, s_type: str, s_name: str,
                                     result: LookupResult) -> None:
        shape = (s_type, s_pred)
        s_node = None if s_name == '*' else self._get_concrete(s_pred, s_type, s_name)
        rows = self.idx.session.exec(
            select(ResidueV1).where(ResidueV1.store_id == self.idx.store_id)
        ).all()
        for row in rows:
            stars = frozenset(tuple(s) for s in json.loads(row.stars))
            if shape not in stars:
                continue
            if s_name != '*' and s_node is not None and s_node.id in set(json.loads(row.neg)):
                continue
            result.node_ids.add(row.object_node_id)

    def lookup_reverse(self, relation: str, o_type: str, o_name: str) -> LookupResult:
        """Everything that can reach the object. Symmetric with lookup: w_all/w_any nodes
        in the reverse set become symbolic markers (e.g. 'every T#P').

        On a derived relation (boolean spec §6): concretes are the derived edges'
        subjects; the residue's stars render as the existing symbolic markers (variant
        'any': subject-side coverage) and its neg fills ``excluded_node_ids`` so
        "everyone of shape σ except these" is representable without enumeration."""
        result = LookupResult()

        if (o_type, relation) in self.schema_info.derived_families:
            self._collect_reverse(self._get_concrete(relation, o_type, o_name), result)
            stars, neg = self._residue_state(relation, o_type, o_name)
            for (t, p) in stars:
                result.markers.add((t, p, 'any'))
            result.excluded_node_ids |= neg
            return result

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
