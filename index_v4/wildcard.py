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

from .core import ReachabilityIndex, _ThreadFlag
from .models import EdgeV4, NodeV4, ResidueV1
from zanzibar_utils_v1 import (AdmissionRejected, SchemaInfo,
                               norm_pred as _norm_pred,
                               validate_node_identifiers,
                               validate_write_identifiers)


@dataclass
class LookupResult:
    node_ids: set[int] = field(default_factory=set)               # concrete results
    markers: set[tuple[str, str, str]] = field(default_factory=set)  # (type, predicate, variant) symbolic "all/any"
    # "everyone of a starred shape EXCEPT these" (boolean spec §6): concrete node ids
    # excluded from a derived relation's star coverage, from the residue's neg.
    # Additive and empty everywhere except derived lookup_reverse.
    excluded_node_ids: set[int] = field(default_factory=set)


class WildcardIndex:
    def __init__(self, idx: ReachabilityIndex, schema_info: SchemaInfo):
        self.idx = idx
        self.schema_info = schema_info
        # Mirror-side belt (F1/F2, 2026-07-17): a doubly-bridged shape -- a LITERAL
        # wildcard-userset restriction (T:*#p) that is also an object-wildcard shape --
        # admits wildcard writes whose materialized bridges form a latent w_any->w_all
        # cycle (set/graph divergence + innocent-write lockout). ``compile_ruleset``
        # rejects such SCHEMAS up front (``DoublyBridgedShapeError``), so no
        # WildcardIndex is ever built with one. We deliberately DON'T assert here: the
        # PRECISE check needs the AST to tell a literal T:*#p restriction from a
        # star-tupleset through-shape, and the AST is not available here.
        #
        # ⚠ 2026-07-26 (ZT-P5-NEW): the compile gate is NOT sufficient on its own, and
        # the old justification for that ("a through-shape is never a writable userset,
        # so it cannot mint a persistent w_any node") is FALSE. A star-tupleset
        # through-shape reaches the SAME latent cycle through the TTU REWRITE when the
        # TTU is self-referential -- but that is a property of the WRITE, not of the
        # schema: the schema it needs is exactly the legal reg11 / ``owc_star_ttu``
        # class, whose other writes are oracle-correct on both backends, so a compile
        # rejection would over-reject. The residual write-level case is caught by
        # ``_reject_star_self_edge`` below (parity mirror of ``SetEngine._would_cycle``'s
        # raw-level ``u == v`` rule). See docs/spec-deviations.md 2026-07-17 + 2026-07-26.
        # Derived-family write exclusivity (boolean spec §3.3/I5): only the delta
        # processor may write incoming direct edges on a derived-public family. The
        # processor sets this flag around its own writes.
        #
        # THREAD-SCOPED (zero-trust review ZT-P1-8e). This flag is the ENTIRE I5
        # bypass window, and as a plain instance attribute the window belonged to the
        # OBJECT, not to the thread that opened it: two threads sharing one
        # WildcardIndex meant the processor's cascade on thread A silently authorised
        # a USER write on thread B to land directly on a derived-public family. The
        # repo documents "one Session per thread" but nothing enforces it, and this is
        # the one flag whose violation costs authorization state (a derived grant
        # nobody derived, committed and invisible) rather than a DB error. Per-thread
        # storage makes the window belong to its opener; every other thread reads the
        # closed default and gets the ordinary loud I5 refusal below.
        self._processor_writes_flag = _ThreadFlag()
        # Per-reconcile residue read cache (perf P3). None outside a reconcile: the
        # read path then behaves exactly as before (no memoization). The delta
        # processor installs a fresh dict for the duration of one full-object /
        # subject reconcile, and invalidates the key it writes via ``_store_residue``,
        # so a cached read can never return pre-write state to a post-write consumer
        # (the only residue written in a reconcile is that of the object being
        # reconciled, which is never read through this cache -- stratification forbids
        # a plan from referencing its own relation, and the object's own residue is
        # read only through the direct ``_residue_state`` calls, which the write
        # invalidates). Values are immutable snapshots; every read hands back fresh
        # mutable neg/upos sets, preserving the callers that mutate them in place.
        self._residue_cache: dict[tuple[str, str, str],
                                  tuple[frozenset, tuple[int, ...], tuple[int, ...]]] | None = None

    @property
    def processor_writes(self) -> bool:
        """Is the CALLING thread inside the delta processor's write window? (I5)

        Read by ``_assert_derived_exclusivity`` (may this write touch a derived-public
        family at all) and ``_derived_write_ctx`` (is the resulting direct edge row a
        derived grant). Both fail CLOSED for a thread that never opened the window --
        the write is refused, and no row is stamped ``derived`` -- so a mis-threaded
        caller is told, loudly, instead of quietly writing authorization state."""
        return self._processor_writes_flag.on

    @processor_writes.setter
    def processor_writes(self, value: bool) -> None:
        self._processor_writes_flag.on = bool(value)

    def _assert_derived_exclusivity(self, relation: str, o_type: str) -> None:
        if self.processor_writes:
            return
        if (o_type, relation) in self.schema_info.derived_families:
            # DELIBERATELY NOT AdmissionRejected (I5 exclusivity, boolean spec §3.3):
            # a hit means the CALLER bypassed `RuleSet.apply`'s leaf routing -- a wiring
            # bug in the write path, not an inadmissible tuple. Every harness routes, so
            # a classifier must let this one propagate and fail loudly.
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
                    # AdmissionRejected: the write names a `*` shape the schema never
                    # declared -- a correct refusal of the tuple.
                    raise AdmissionRejected(
                        f"subject wildcard {entity_type}:* (predicate {pred!r}) is not a declared "
                        f"subject-wildcard shape {shape}")
                variant = 'any'
            else:
                shape = (entity_type, pred)  # pred is the relation in object position
                if shape not in self.schema_info.object_wildcard_shapes:
                    # AdmissionRejected: ditto, object position (the set engine refuses
                    # the identical write in `_validate` step 1).
                    raise AdmissionRejected(
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
        """Id of a w_any/w_all node (read path), or None if it doesn't exist.

        Deliberately UNcached (blind-audit W2): every caching scheme tried here went
        stale across sessions -- cached misses pinned probes off after another
        session created the w node, and cached positive ids turned into false
        POSITIVES under SQLite rowid reuse (a GC'd w node's id claimed by an
        unrelated node) and permanent false negatives after w-node re-creation.
        Resolution is one point lookup on the unique node index -- the same cost
        class as the probe it feeds."""
        node = self._w_node(entity_type, predicate, variant, create=False)
        return node.id if node is not None else None

    def _bridge_degree(self, shape: tuple[str, str]) -> int:
        return ((1 if shape in self.schema_info.bridged_in_shapes else 0)
                + (1 if shape in self.schema_info.bridged_out_shapes else 0))

    def _reject_star_self_edge(self, subject: NodeV4, obj: NodeV4) -> None:
        """Reject a routed edge ``w_any(T,p) -> w_all(T,p)`` on the SAME shape
        (ZT-P5-NEW, 2026-07-26).

        WHY IT IS A CYCLE. The position rule (§1.2/§1.3) splits one wildcard shape into
        two ``node_v4`` rows -- ``w_any`` (subject position) and ``w_all`` (object
        position) -- so such an edge is not a self-loop *in the edge table* and the
        core's cycle check cannot see it. It is nevertheless a cycle by CONSTRUCTION,
        because the bridges of that shape are SCHEMATIC, not data: every present **and
        future** concrete ``T:x#p`` gets ``T:x#p -> w_any(T,p)`` (in-bridge) and
        ``w_all(T,p) -> T:x#p`` (out-bridge) from ``_ensure_bridges``. So
        ``w_any(T,p) -> w_all(T,p) ->[out] T:x#p ->[in] w_any(T,p)`` closes the moment
        ANY concrete of the shape exists. Admitting the edge while the shape happens to
        have no concretes yet therefore does not avoid the cycle -- it defers it onto
        the next innocent write, which is then permanently rejected (the "detonation":
        the graph locks itself out of a grant the set engine and the oracle both allow).

        WHY HERE AND NOT AT COMPILE TIME. This is a property of the WRITE, not of the
        schema. The only schema class that can express such a write through a TTU
        rewrite is a self-referential TTU (``viewer: ... or viewer from parent``) over a
        star-restricted tupleset whose shape carries an object wildcard -- i.e. exactly
        reg11 / ``owc_star_ttu``, a LEGAL and oracle-pinned class whose every other
        write must keep working. Rejecting the schema would over-reject it (verified by
        construction, docs/spec-deviations.md 2026-07-26). The set engine agrees: it
        BUILDS this schema and rejects only the offending write, via the raw-level
        ``any(u == v for u, v in pairs)`` rule in ``_would_cycle`` -- the very same rule,
        stated on the UNSPLIT node key. This method is that rule restated for the
        position-split encoding, so the two backends implement one rule, not two rules
        that happen to agree.

        MINIMALITY. Both bridge memberships are required explicitly: without the
        in-bridge (a bare ``'...'`` predicate is never in ``bridged_in_shapes``) or
        without the out-bridge there is no schematic return path and the edge is
        harmless. Only a same-shape ``any -> all`` pair is rejected; a cross-shape
        ``w_any(A) -> w_all(B)`` needs stored data to close its loop and is left to the
        core's ordinary cycle check, which both backends already run (the reg11
        MULTI-HOP class -- pinned accepted/rejected in lockstep by
        tests/test_zt_p5_readjudication.py)."""
        if subject.wildcard != 'any' or obj.wildcard != 'all':
            return
        shape = (subject.type, subject.predicate)
        if shape != (obj.type, obj.predicate):
            return
        if (shape not in self.schema_info.bridged_in_shapes
                or shape not in self.schema_info.bridged_out_shapes):
            return
        # AdmissionRejected: a cycle refusal (the ZT-P5 star self-edge). Same rule the
        # set engine states on the unsplit node key, so both backends reject the same
        # write with the same class.
        raise AdmissionRejected(
            f"wildcard tuple rejected: the routed edge w_any{shape} -> w_all{shape} is a "
            f"cycle by construction -- the shape {shape} is both subject-wildcard bridged "
            f"(concrete -> w_any) and object-wildcard bridged (w_all -> concrete), so every "
            f"present-or-future concrete of that shape closes the loop "
            f"w_any -> w_all -> concrete -> w_any (ZT-P5, docs/spec-deviations.md "
            f"2026-07-26; the set engine rejects the same write as a userset-topology cycle)")

    # ------------------------------------------------------------------ #
    # Bridge lifecycle (§7)
    # ------------------------------------------------------------------ #

    def _ensure_bridges(self, node: NodeV4) -> None:
        """Lazily create the configured bridges for a concrete node, plus its
        entity's crossing middles (idempotent).

        The middle half maintains the I14 property (``index_v4/invariants.py``):

          for every crossable shape ``(T, p)`` (``SchemaInfo.crossable_shapes`` --
          bridged in AND out) and every entity name ``x`` such that the store holds
          at least one node ``(T, x, *)`` that is not itself a bridge-only middle,
          the store holds the node ``(T, x, p)`` with BOTH of its bridges.

        so the ``w_all(T,p) -> concrete -> w_any(T,p)`` crossing tracks ENTITY
        existence -- the spec's reading of §3.4's existential
        (``tests/oracle.py::instances`` witnesses it with any tuple-mentioned entity
        of type ``T``; docs/spec-deviations.md 2026-08-09). The remove-side dual is
        ``_sync_entity_middles``."""
        if node.wildcard != '':          # only concretes are bridged
            return
        self._ensure_own_bridges(node)
        self._ensure_entity_middles(node.type, node.name)

    def _ensure_own_bridges(self, node: NodeV4) -> None:
        """The per-node half of ``_ensure_bridges``: this node's own bridge edges."""
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

    def _ensure_entity_middles(self, entity_type: str, name: str) -> None:
        """Intern the crossing middle ``(T, x, p)`` -- with both bridges -- for every
        crossable shape ``(T, p)`` of this entity's type (I14; idempotent).

        Middles are created IMPLICIT so they are exactly bridge-only state
        (``_is_bridge_middle``), collected by ``_sync_entity_middles`` when the
        entity's last real node goes. Never called for a wildcard endpoint: every
        caller guards on ``wildcard == ''``, and the ``name == '*'`` return below is
        the defensive restatement (a middle for ``'*'`` would be a concrete node
        named ``'*'``, which the encoding reserves)."""
        if name == '*':
            return
        crossable = self.schema_info.crossable_shapes
        if not crossable:
            return
        for (t, p) in sorted(crossable):
            if t != entity_type:
                continue
            mid = self.idx.node(p, entity_type, name, create_if_missing=True)
            self._ensure_own_bridges(mid)

    def _is_bridge_middle(self, node: NodeV4) -> bool:
        """Is this node currently BRIDGE-ONLY crossing-middle state? Implicit, of a
        crossable shape, and carrying nothing but its own two bridges (I3 guarantees
        a live concrete of a crossable shape has both bridges, so
        ``reference_count == bridge degree`` means exactly "bridges only"). Such a
        node witnesses nothing for I14: it exists BECAUSE the entity does, so letting
        it witness the entity would make the middles self-sustaining garbage."""
        if node.wildcard != '' or not node.implicit:
            return False
        shape = (node.type, node.predicate)
        return (shape in self.schema_info.crossable_shapes
                and node.reference_count == self._bridge_degree(shape))

    def _entity_nodes(self, entity_type: str, name: str) -> list[NodeV4]:
        return list(self.idx.session.exec(
            select(NodeV4)
            .where(NodeV4.store_id == self.idx.store_id)
            .where(NodeV4.type == entity_type)
            .where(NodeV4.name == name)
            .where(NodeV4.wildcard == '')
        ).all())

    def _entity_has_witness(self, entity_type: str, name: str) -> bool:
        """Does the entity ``(T, x)`` still EXIST for I14 -- i.e. does the store hold
        at least one ``(T, x, *)`` node that is not itself a bridge-only middle?"""
        return any(not self._is_bridge_middle(n)
                   for n in self._entity_nodes(entity_type, name))

    def _sync_entity_middles(self, entity_type: str, name: str) -> None:
        """Re-normalize one entity's crossing middles after a removal (I14): while a
        witness remains the middles must (still) exist -- re-ensured here, which makes
        the property self-healing -- and when the entity's last real node is gone
        every remaining bridge-only middle is stripped, so implicit GC collects it
        (and any w node it alone kept alive)."""
        if name == '*':
            return
        if not any(t == entity_type for (t, _p) in self.schema_info.crossable_shapes):
            return
        if self._entity_has_witness(entity_type, name):
            self._ensure_entity_middles(entity_type, name)
            return
        for n in self._entity_nodes(entity_type, name):
            if self._is_bridge_middle(n):
                self._strip_bridges(n.id, (n.type, n.predicate))

    def _strip_bridges(self, node_id: int, shape: tuple[str, str]) -> None:
        """Remove a concrete node's bridge edges (in, then out), tolerating the
        implicit GC that the first strip may trigger."""
        entity_type, predicate = shape
        if shape in self.schema_info.bridged_in_shapes:
            w_any = self._w_node(entity_type, predicate, 'any', create=False)
            if w_any is not None and self.idx.direct_edge_exists_by_id(node_id, w_any.id):
                self.idx.remove_edge_by_id(node_id, w_any.id)
        # re-fetch: the first removal may already have collected the node
        if self._node_by_id(node_id) is None:
            return
        if shape in self.schema_info.bridged_out_shapes:
            w_all = self._w_node(entity_type, predicate, 'all', create=False)
            if w_all is not None and self.idx.direct_edge_exists_by_id(w_all.id, node_id):
                self.idx.remove_edge_by_id(w_all.id, node_id)

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
        if (shape in self.schema_info.crossable_shapes
                and self._entity_has_witness(fresh.type, fresh.name)):
            # The node has become exactly the entity's crossing middle (bridge-only,
            # implicit, crossable shape). I14 requires the middle to EXIST while the
            # entity does, so it is deliberately NOT collected here; it goes when
            # ``_sync_entity_middles`` sees the entity's last real node go.
            # (``_entity_has_witness`` ignores bridge-only middles, ``fresh``
            # included, so a witness here means some OTHER real node of the entity.)
            return
        self._strip_bridges(fresh.id, shape)

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

    def _neighbour_entities(self, node_id: int) -> set[tuple[str, str]]:
        """(type, name) of every CONCRETE direct neighbour of a node (I14: the
        entities a ``remove_node`` can orphan). Empty when no shape is crossable, so
        plain schemas pay nothing."""
        if not self.schema_info.crossable_shapes:
            return set()
        pairs = self.idx.session.exec(
            select(EdgeV4.subject_id, EdgeV4.object_id)
            .where(EdgeV4.store_id == self.idx.store_id)
            .where((EdgeV4.subject_id == node_id) | (EdgeV4.object_id == node_id))
            .where(EdgeV4.direct_edge_count > 0)  # type: ignore[arg-type]
        ).all()
        other_ids = {s if o == node_id else o for (s, o) in pairs} - {node_id}
        nodes = self.idx._load_nodes(other_ids)
        return {(n.type, n.name) for n in nodes.values() if n.wildcard == ''}

    def backfill(self) -> None:
        """Ensure every existing concrete of a bridged shape has its bridges, and
        every existing entity of a crossable shape's type has its crossing middles
        (§7.2 + I14).

        Idempotent; safe to call always. Does not create a w node for a NON-crossable
        shape that has no concrete instances (avoids orphan wildcard nodes); a
        CROSSABLE shape's w nodes arrive with its middles, i.e. exactly when an
        entity of the shape's type exists."""
        # Serialize against live writers: the existence probes below are
        # check-then-act on ref-counted bridge edges (blind-audit C2).
        self.idx._lock_store()
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
        # I14: the crossing middles track ENTITY existence -- after the bridge loops
        # above (so ``reference_count == bridge degree`` again means "bridges only"
        # and ``_is_bridge_middle`` classifies correctly on a half-migrated store),
        # intern the middle for every entity of a crossable shape's type that has at
        # least one real (non-bridge-only-middle) node.
        crossable_types = {t for (t, _p) in self.schema_info.crossable_shapes}
        for entity_type in sorted(crossable_types):
            names = {n.name for n in self.idx.session.exec(
                select(NodeV4)
                .where(NodeV4.store_id == self.idx.store_id)
                .where(NodeV4.type == entity_type)
                .where(NodeV4.wildcard == '')
            ).all() if not self._is_bridge_middle(n)}
            for x in sorted(names):
                self._ensure_entity_middles(entity_type, x)

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
        self._add_tuple_trusted(subject_predicate, s_type, s_name, relation, o_type, o_name)

    def _add_tuple_trusted(self, subject_predicate: str | EllipsisType, s_type: str,
                           s_name: str, relation: str, o_type: str, o_name: str) -> None:
        """``add_tuple`` minus the ``validate_write_identifiers`` charset check (perf N9).

        TRUST CONTRACT: the caller MUST guarantee every identifier already came from
        an admission-validated raw tuple routed through ``RuleSet.apply`` -- the raw
        tuple was charset-checked at admission (``SetEngine.add_tuple`` /
        ``TupleSource``), and rewrite fan-out only ever rewrites the *relation* field
        to a compiler-generated leaf predicate ``<relation>.<index>``, which is
        charset-valid by construction (``.`` is in the identifier charset). Skipping
        the re-validation therefore changes NO accept/reject behaviour: on this path
        the check provably always passes, so it is pure redundant work. The public
        ``add_tuple`` above (used directly by tests/harness) keeps validating. The
        ONLY sanctioned caller of this trusted entry point is ``_apply_row`` in
        ``connectedstore/apply.py``; do not widen that."""
        self._assert_derived_exclusivity(relation, o_type)
        # Lock BEFORE resolution, exactly like core.add_edge (blind-audit C2): a
        # concurrent remove_node in the resolve-then-mutate gap would hand us stale
        # ids, and the bridge existence probes below are check-then-act -- two
        # unserialized writers would double-count a ref-counted bridge edge.
        self.idx._lock_store()
        subject = self._resolve(subject_predicate, s_type, s_name, 'subject', create=True)
        obj = self._resolve(relation, o_type, o_name, 'object', create=True)

        # ZT-P5 (2026-07-26): the position-split w_any/w_all encoding hides a same-shape
        # star self-edge from the core's cycle check. Reject it here, BEFORE any bridge
        # or grant edge is written, so the offending write never mutates closure state.
        self._reject_star_self_edge(subject, obj)

        # Bridge-before-grant: cycle errors then attach to the grant (the offending write).
        self._ensure_bridges(subject)
        self._ensure_bridges(obj)

        self.idx._writing_derived = self._derived_write_ctx(relation, o_type)
        try:
            self.idx.add_edge_by_id(subject.id, obj.id)
        except AdmissionRejected as e:
            # Narrowed from `except ValueError` (ZT-P4-7): the only thing this handler
            # ever meant to re-dress is the core's CYCLE REFUSAL, which is now typed.
            # Behaviour is identical -- the other ValueErrors `add_edge_by_id` can raise
            # (`node id ... no longer exists`) never contained 'cycle', so they fell
            # through the bare `raise` below and propagated unchanged; now they simply
            # never enter the handler. The re-dressed error keeps the rejection type.
            if 'cycle' in str(e) and (subject.wildcard != '' or obj.wildcard != ''):
                raise AdmissionRejected(
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
        self._remove_tuple_trusted(subject_predicate, s_type, s_name, relation, o_type, o_name)

    def _remove_tuple_trusted(self, subject_predicate: str | EllipsisType, s_type: str,
                              s_name: str, relation: str, o_type: str, o_name: str) -> None:
        """``remove_tuple`` minus ``validate_write_identifiers`` (perf N9). Same TRUST
        CONTRACT as ``_add_tuple_trusted``: identifiers must originate from an
        admission-validated raw tuple routed through ``RuleSet.apply``; the skipped
        check provably always passes here, so accept/reject behaviour is unchanged.
        Sole sanctioned caller: ``_apply_row`` in ``connectedstore/apply.py``."""
        self._assert_derived_exclusivity(relation, o_type)
        self.idx._lock_store()   # lock before resolution (blind-audit C2)
        try:
            subject = self._resolve(subject_predicate, s_type, s_name, 'subject', create=False)
            obj = self._resolve(relation, o_type, o_name, 'object', create=False)
        except KeyError as e:
            # Same rejection family as core.remove_edge and the set engine (validity
            # parity): a remove of a never-seen endpoint is an admission rejection.
            raise AdmissionRejected('Non-existent edge cannot be removed') from e

        self.idx.remove_edge_by_id(subject.id, obj.id)

        # GC bridges for concrete endpoints whose only remaining edges are their bridges.
        self._maybe_remove_bridges(subject)
        self._maybe_remove_bridges(obj)
        # I14: this removal may have retired an endpoint entity's last real node --
        # collect its crossing middles (or re-ensure them while a witness remains).
        self._sync_entity_middles(s_type, s_name)
        self._sync_entity_middles(o_type, o_name)

    def remove_node(self, predicate: str | EllipsisType, entity_type: str,
                    name: str) -> None:
        """Remove a node and all its edges, stripping its materialized wildcard
        bridges FIRST (spec §remove_tuple: explicit nodes keep bridges for as long
        as they exist; ``remove_node`` must strip them before the core removal).

        The ordering is not cosmetic: the core's node-removal shortcut retires edge
        ROWS by count math but does not decrement the neighbours' reference counts
        -- stripping bridges through ``remove_edge_by_id`` first keeps the w-node
        refcounts honest, so an orphaned w node can be implicit-GC'd instead of
        lingering with a stale count."""
        validate_node_identifiers(predicate, entity_type, name)
        if name == '*':
            # AdmissionRejected: a user-facing refusal on the public remove_node API
            # (the message names the supported alternative), not a broken store.
            raise AdmissionRejected(
                'wildcard nodes are bridge/GC-managed and cannot be removed directly '
                '(remove the grants and bridged concretes that keep them alive)')
        pred = _norm_pred(predicate)
        # derived-public nodes are processor-owned state (I5), same as their edges
        self._assert_derived_exclusivity(pred, entity_type)
        self.idx._lock_store()   # lock before resolution (blind-audit C2)
        try:
            node = self.idx.node(pred, entity_type, name, create_if_missing=False)
        except KeyError as e:
            # AdmissionRejected: removing a node the store never saw is a refusal.
            raise AdmissionRejected('Non-existent node cannot be removed') from e

        neighbour_entities: set[tuple[str, str]] = set()
        if node.wildcard == '':
            node_id = node.id
            # I14: capture the CONCRETE neighbour entities BEFORE the core removal
            # retires their edges -- removing this node may leave a neighbour entity
            # witness-less (its node implicit-GC'd by the neighbour-debit machinery,
            # or reduced to bridge-only middle state), orphaning its crossing middles.
            neighbour_entities = self._neighbour_entities(node_id)
            self._strip_bridges(node_id, (node.type, node.predicate))
            # stripping a bridge may already have implicit-GC'd the node
            if self._node_by_id(node_id) is None:
                self._sync_entity_middles(entity_type, name)
                return

        self.idx.remove_node(pred, entity_type, name)
        # I14: the removed node may have been its entity's last real node, and the
        # removal may have orphaned a neighbour entity too.
        self._sync_entity_middles(entity_type, name)
        for (t, x) in sorted(neighbour_entities):
            self._sync_entity_middles(t, x)

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
                       ) -> tuple[frozenset, set[int], set[int]]:
        """(stars, neg, upos) of the derived relation's residue; empty if no
        row/node. Read-only: never interns.

        When a per-reconcile cache is installed (perf P3) the node SELECT, residue
        SELECT and JSON decode are memoized by ``(o_type, relation, o_name)``. The
        cache holds only immutable snapshots; every call reconstructs fresh mutable
        ``neg``/``upos`` sets, so callers that mutate the returned sets in place
        (``reconcile_subject``) can never corrupt a cached entry."""
        cache = self._residue_cache
        if cache is not None:
            hit = cache.get((o_type, relation, o_name))
            if hit is not None:
                stars, neg_ids, upos_ids = hit
                return stars, set(neg_ids), set(upos_ids)

        node = self._get_concrete(relation, o_type, o_name)
        row = None if node is None else self.idx.session.exec(
            select(ResidueV1)
            .where(ResidueV1.store_id == self.idx.store_id)
            .where(ResidueV1.object_node_id == node.id)
        ).first()
        if row is None:
            stars, neg_ids, upos_ids = frozenset(), (), ()
        else:
            stars = frozenset(tuple(s) for s in json.loads(row.stars))
            neg_ids = tuple(json.loads(row.neg))
            upos_ids = tuple(json.loads(row.upos))

        if cache is not None:
            cache[(o_type, relation, o_name)] = (stars, neg_ids, upos_ids)
        return stars, set(neg_ids), set(upos_ids)

    def _check_derived(self, s_pred: str, s_type: str, s_name: str,
                       relation: str, o_type: str, o_name: str) -> bool:
        if o_name == '*':
            # object wildcards on derived relations are rejected at compile (decision
            # 15): no object-star state can exist, so the intensional query is False
            return False
        if s_name == '*':
            # intensional: is the whole shape covered? (1 residue read)
            stars, _, _ = self._residue_state(relation, o_type, o_name)
            return (s_type, s_pred) in stars

        subj = self._get_concrete(s_pred, s_type, s_name)

        if s_pred != '...':
            # userset subject: edge-free membership (blind-audit P4 -- userset
            # edges would leak through the closure past members' own exclusions)
            stars, neg, upos = self._residue_state(relation, o_type, o_name)
            if subj is not None and subj.id in upos:
                return True
            if (s_type, s_pred) not in stars:
                return False
            return subj is None or subj.id not in neg

        # probe 1 only: the derived edge (public family)
        obj = self._get_concrete(relation, o_type, o_name)
        if subj is not None and obj is not None \
                and self.idx.check_reachable_by_id(subj.id, obj.id):
            return True

        # residue: star coverage minus neg; a ghost subject has no node and thus
        # cannot be in neg -- the stars answer alone.
        stars, neg, _ = self._residue_state(relation, o_type, o_name)
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
        concrete = s_node is not None
        rows = self.idx.session.exec(
            select(ResidueV1).where(ResidueV1.store_id == self.idx.store_id)
        ).all()
        want = list(shape)
        for row in rows:
            # stars first (small, and the common filter) so the per-row upos/neg
            # JSON decodes only run on the branch that needs them. Point membership
            # reads the decoded list directly -- no set/frozenset materialization for
            # a single ``in`` probe, and ``upos`` decodes only when its branch is hit.
            covered = want in json.loads(row.stars)
            if covered:
                if concrete and s_node.id in json.loads(row.neg) \
                        and s_node.id not in json.loads(row.upos):
                    continue
                result.node_ids.add(row.object_node_id)
            elif concrete and s_node.id in json.loads(row.upos):
                result.node_ids.add(row.object_node_id)     # edge-free userset membership

    def lookup_reverse(self, relation: str, o_type: str, o_name: str) -> LookupResult:
        """Everything that can reach the object. Symmetric with lookup: w_all/w_any nodes
        in the reverse set become symbolic markers (e.g. 'every T#P').

        On a derived relation (boolean spec §6): concretes are the derived edges'
        subjects; the residue's stars render as the existing symbolic markers (variant
        'any': subject-side coverage) and its neg fills ``excluded_node_ids`` so
        "everyone of shape σ except these" is representable without enumeration."""
        result = LookupResult()

        if (o_type, relation) in self.schema_info.derived_families:
            if o_name == '*':
                # object wildcards on derived relations are compile-rejected
                # (decision 15): no object-star state can exist, so mirror the
                # check path's False (P7 #3) with the empty result instead of the
                # reserved-name ValueError (lookup gate X2)
                return result
            self._collect_reverse(self._get_concrete(relation, o_type, o_name), result)
            stars, neg, upos = self._residue_state(relation, o_type, o_name)
            for (t, p) in stars:
                result.markers.add((t, p, 'any'))
            result.excluded_node_ids |= neg
            result.node_ids |= upos            # edge-free userset memberships (P4)
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
        self._classify_ids(self.idx.lookup_reachable(node.id), result)

    def _collect_reverse(self, node: NodeV4 | None, result: LookupResult) -> None:
        if node is None:
            return
        self._classify_ids(self.idx.lookup_reverse(node.id), result)

    def _classify_ids(self, node_ids, result: LookupResult) -> None:
        """Classify a whole reachable/reverse id set concrete-vs-wildcard (perf N6).

        Batch-load the entire id set in one chunked ``IN`` (``idx._load_nodes``,
        SQLite-bind-safe) instead of a per-id ``_node_by_id`` round trip -- K+1
        point SELECTs for K results collapse to ``ceil(K/900)`` batched SELECTs.
        The classification is byte-identical to the old per-id path: the identity
        map makes a batched row the same instance ``_node_by_id`` would return, and
        a map miss (defensive parity, P7's pattern) falls back to ``_node_by_id``."""
        node_map = self.idx._load_nodes(node_ids)
        for nid in node_ids:
            n = node_map.get(nid)
            if n is None:
                n = self._node_by_id(nid)
            if n is None:
                continue
            if n.wildcard == '':
                result.node_ids.add(nid)
            else:
                result.markers.add((n.type, n.predicate, n.wildcard))
