"""
Set engine storage model + writes (spec §5, §6.1-6.2).

Stores ONLY raw set memberships; builds no closure. In-memory state is rebuilt from the
``TupleV1`` table on open (replay). The evaluator (check/expand/lookups, §6.3-6.5) is
added on top of this storage layer.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import chain
from types import EllipsisType

from sqlmodel import Session, select

from zanzibar_utils_v1 import (
    CyclicDerivedDependency,
    Entity,
    RelationalTriple,
    norm_pred as _norm_pred,
    parse_schema_ast,
    derive_schema_info,
    schema_filters,
    compile_ruleset,
    validate_write_identifiers,
    UnsupportedByGraphIndex,
    Direct,
    Computed,
    TTU,
    Union,
    Intersection,
    Exclusion,
)
from .setops import SetOps, DEFAULT_SETOPS
from .models import TupleV1
from . import memberset as ms
from .memberset import MemberSet

NodeKey = tuple[str, str, str]      # (type, name, predicate) flow-graph node


class LookupResult:
    """Concrete result ids + symbolic wildcard markers (mirrors index_v4 LookupResult)."""

    def __init__(self):
        self.node_ids: set[int] = set()               # concrete result ids
        self.markers: set[tuple[str, str]] = set()    # (type, predicate) star shapes

    def __repr__(self):
        return f'LookupResult(node_ids={self.node_ids}, markers={self.markers})'


def _denorm_pred(pred: str) -> str | EllipsisType:
    return Ellipsis if pred == '...' else pred


def _candidate_reverse_deps(ast) -> tuple[dict, dict]:
    """Static reverse-dependency tables for write-time candidate interning (the
    engine's adaptation of spec §6.4's reverse propagation; see ``lookup``).

    Returns ``(object_deps, chain_targets)``:

    - ``object_deps[(T, r)]`` -> relations ``R`` on ``T`` (``R != r``) whose truth on
      an object can be anchored by that object's stored tuples of relation ``r``
      alone: ``R`` reaches ``r`` through Computed chains, or holds a TTU whose
      tupleset relation is ``r`` (TTU parents are STORED tupleset tuples, so any
      TTU-derived membership implies such a tuple on the object itself).
    - ``chain_targets[(T, ts)]`` -> target relations of TTUs over tupleset ``ts`` on
      ``T``: a stored tupleset tuple makes its (bare) subject ``p`` reach the object
      as the from-chain userset ``p#target_rel`` (the Zanzibar from-chain rule).

    Every expression position is walked, subtrahends included: over-approximate
    candidates cost one check-verification each, while a missed one is a silently
    dropped lookup result (the X1 gap this closes).
    """
    object_deps: dict[tuple[str, str], set[str]] = {}
    chain_targets: dict[tuple[str, str], set[str]] = {}
    for (t, root), expr in ast.items():
        seen: set[str] = {root}
        stack = [expr]
        while stack:
            node = stack.pop()
            if isinstance(node, (Union, Intersection)):
                stack.extend(node.children)
            elif isinstance(node, Exclusion):
                stack.append(node.base)
                stack.append(node.subtract)
            elif isinstance(node, Computed):
                if node.relation != root:
                    object_deps.setdefault((t, node.relation), set()).add(root)
                if node.relation not in seen:
                    seen.add(node.relation)
                    ref = ast.get((t, node.relation))
                    if ref is not None:
                        stack.append(ref)
            elif isinstance(node, TTU):
                if node.tupleset_rel != root:
                    object_deps.setdefault((t, node.tupleset_rel), set()).add(root)
                chain_targets.setdefault((t, node.tupleset_rel), set()).add(node.target_rel)
    return ({k: tuple(sorted(v)) for k, v in object_deps.items()},
            {k: tuple(sorted(v)) for k, v in chain_targets.items()})


def _ttu_reverse_map(ast) -> dict:
    """``(object_type, tupleset_rel, target_rel)`` -> relations ``R`` on that object
    type whose expression contains a TTU ``R: target_rel from tupleset_rel``.

    Drives the ``lookup`` reverse walk's TTU from-chain hop (the dual of
    ``ttu_expand``): a subject that is a member of ``parent#target_rel`` reaches
    ``object#R`` whenever ``parent`` is a stored tupleset tuple of ``object`` (the
    Zanzibar from-chain rule). Computed is treated as opaque -- a TTU reached
    through a Computed chain surfaces via the target relation's own entry plus the
    ``object_deps`` Computed hop, so this map holds only the DIRECT TTU nodes of
    each relation's expression."""
    m: dict[tuple[str, str, str], set[str]] = {}
    for (t, root), expr in ast.items():
        stack = [expr]
        while stack:
            node = stack.pop()
            if isinstance(node, (Union, Intersection)):
                stack.extend(node.children)
            elif isinstance(node, Exclusion):
                stack.append(node.base)
                stack.append(node.subtract)
            elif isinstance(node, TTU):
                m.setdefault((t, node.tupleset_rel, node.target_rel), set()).add(root)
    return {k: tuple(sorted(v)) for k, v in m.items()}


class Interner:
    """Per-store, reference-counted interning of ``(type, name, predicate)`` to int32 ids.

    Two decoupled identities: the ``(type, name, predicate)`` key is the immutable
    *surrogate* (the stable identity, and what ``TupleV1`` persists), while the int32 id is
    a *reusable internal handle* for the bitmap algebra. Each id carries a reference count
    (how many stored tuples mention it, in either position -- plus one reference per tuple
    that anchors it as a reverse-dependency candidate key, ``_apply_add``'s §6.4
    interning). When the last referencing
    tuple is removed the count reaches zero, the surrogate->id mapping is dropped, the id
    is scrubbed from the population masks, and the id is returned to a free list for reuse.
    This bounds memory by the *live* entity count rather than the lifetime count -- so churn
    of temporary entities cannot leak -- and keeps ids within the uint32 domain roaring
    needs. (Supersedes the append-only design in spec §5/§10; ``rebuild`` remains the way
    to reconstruct minimal state from the table.)

    Star nodes intern like anything else -- ``(T, '*', pred)`` -- and need no any/all
    split: a star id's role is unambiguous from which side of storage it sits on (a
    star *subject* is a sentinel inside some node's entities/usersets; a star *object*
    is a NodeSets key). ``ids_of_type`` / ``ids_of_shape`` are the population masks the
    MemberSet algebra needs; freeing an id scrubs it from them.
    """

    def __init__(self, ops: SetOps):
        self.ops = ops
        self.id_of: dict[tuple[str, str, str], int] = {}      # surrogate key -> in-use internal id
        self.key_of: dict[int, tuple[str, str, str]] = {}     # internal id -> surrogate key
        self.refcount: dict[int, int] = {}                    # internal id -> # referencing tuples
        self.ids_of_type: dict[str, object] = defaultdict(ops.new)          # concrete entities (pred '...')
        self.ids_of_shape: dict[tuple[str, str], object] = defaultdict(ops.new)  # concrete usersets
        self._free: list[int] = []                            # recyclable internal ids
        self._next: int = 0                                   # next fresh internal id

    def acquire(self, entity_type: str, name: str, pred: str) -> int:
        """Intern (creating the mapping and allocating/reusing an internal id if needed)
        and add one reference. Called once per subject/object occurrence in a tuple."""
        key = (entity_type, name, pred)
        i = self.id_of.get(key)
        if i is None:
            if self._free:
                i = self._free.pop()
            else:
                i = self._next
                self._next += 1
            self.id_of[key] = i
            self.key_of[i] = key
            self.refcount[i] = 0
            if name != '*':                   # star ids are sentinels, not population members
                if pred == '...':
                    self.ids_of_type[entity_type].add(i)
                else:
                    self.ids_of_shape[(entity_type, pred)].add(i)
        self.refcount[i] += 1
        return i

    def release(self, entity_type: str, name: str, pred: str) -> int | None:
        """Drop one reference; when it reaches zero, remove the mapping, scrub the masks,
        and recycle the id. Returns the freed id (else None) so the caller can scrub any
        residual per-id state before the id is reused."""
        key = (entity_type, name, pred)
        i = self.id_of.get(key)
        if i is None:
            return None                       # unknown surrogate: nothing to release
        self.refcount[i] -= 1
        if self.refcount[i] > 0:
            return None
        del self.id_of[key]
        del self.key_of[i]
        del self.refcount[i]
        if name != '*':
            mask = (self.ids_of_type.get(entity_type) if pred == '...'
                    else self.ids_of_shape.get((entity_type, pred)))
            if mask is not None:
                mask.discard(i)
        self._free.append(i)
        return i

    def get(self, entity_type: str, name: str, pred: str) -> int | None:
        return self.id_of.get((entity_type, name, pred))

    def key(self, uid: int) -> tuple[str, str, str]:
        return self.key_of[uid]


@dataclass
class NodeSets:
    """Direct subjects granted a relation on one object node (the tuple's object side).

    The split is a performance invariant, not cosmetics (spec §5): evaluator recursion
    iterates only ``usersets`` (small, topology-shaped), while ``entities`` bitmaps
    (potentially huge populations) are only ever combined by C-level bulk ops.
    """
    entities: object      # subject ids with predicate '...' (concrete entities + bare-star sentinels)
    usersets: object      # subject ids with predicate != '...' (concrete usersets + userset-star sentinels)


class SetEngine:
    """Raw-tuple, bitmap-backed reachability engine (storage + writes; §5, §6.1-6.2)."""

    def __init__(self, session: Session, store_id: str, schema: str, *,
                 object_wildcard_shapes: frozenset[tuple[str, str]] = frozenset(),
                 ops: SetOps = DEFAULT_SETOPS,
                 ruleset=None):
        self.session = session
        self.store_id = store_id
        self.ops = ops
        self.ast = parse_schema_ast(schema)
        # P9: the per-Direct-node restriction key set is fully determined by the
        # (frozen, lifetime-stable) AST node -- cache it once instead of rebuilding
        # the comprehension on every direct_leaf / direct_expand call. Keyed by
        # id(direct); safe because self.ast pins every node for the engine's life
        # (rebuild() only resets tuple state, never reparses the AST).
        self._restr_cache: dict[int, frozenset[tuple[str, str, bool]]] = {}
        # Reverse-dependency tables for write-time candidate interning (§6.4) and
        # the read-time lookup reverse walk (TTU from-chain hop).
        self._object_deps, self._chain_targets = _candidate_reverse_deps(self.ast)
        self._ttu_map = _ttu_reverse_map(self.ast)
        self.schema_info = derive_schema_info(self.ast, object_wildcard_shapes)
        self.filters = schema_filters(self.ast)
        # Reproduce the graph backend's raw-write edge graph (same RuleSet) and reject
        # exactly the cycles it rejects -- including from-chain cycles. Since the P7
        # matrix flip this covers boolean schemas too (their raw writes route onto
        # leaf families). Schemas the graph still refuses (decision-15 scope, cyclic
        # derived dependencies) have no graph partner: data-cycle rejection is off and
        # the oracle remains the only cross-check. A caller that already compiled the
        # same schema (ConnectedStore opens both backends) passes its RuleSet in.
        if ruleset is not None:
            self._ruleset = ruleset
        else:
            try:
                self._ruleset = compile_ruleset(self.ast, self.schema_info)
            except (UnsupportedByGraphIndex, CyclicDerivedDependency):
                # Only the graph's documented refusals leave us ruleset-less; any
                # other ValueError from compile is a regression that must surface
                # (review 3).
                self._ruleset = None
        if self._ruleset is not None and self._ruleset.schema_info is not None:
            # Adopt the compiled SchemaInfo: its object-wildcard shapes are CLOSED
            # over the rewrite rules (_expand_object_wildcard_shapes), which is what
            # the graph façade validates against -- validating the declared set here
            # rejected star-object writes on rewrite-target shapes that the graph
            # accepted (accept/reject divergence on exactly the shapes the expansion
            # exists for).
            self.schema_info = self._ruleset.schema_info
        # N17: per-type object-wildcard bridge-seeding reach, precomputed once from
        # the finalized schema_info + the reverse-dependency tables. Maps each type
        # T that declares an object-wildcard shape to the relations r' a star
        # injection on T can reach ({r0} plus its Computed/TTU-tupleset reverse
        # closure), which `lookup`'s walk loop uses to seed the wildcard-covered
        # concrete siblings the reverse walk cannot reach on its own (see `lookup`).
        self._owc_bridge_reach: dict[str, tuple[str, ...]] = {}
        _reach_acc: dict[str, set[str]] = {}
        for (T, r0) in self.schema_info.object_wildcard_shapes:
            acc = _reach_acc.setdefault(T, set())
            acc.add(r0)
            acc.update(self._object_deps.get((T, r0), ()))
        self._owc_bridge_reach = {t: tuple(sorted(rs)) for t, rs in _reach_acc.items()}
        self.rebuild()

    # ------------------------------------------------------------------ #
    # State (rebuilt on open)
    # ------------------------------------------------------------------ #

    def _reset_state(self) -> None:
        self.interner = Interner(self.ops)
        self.node_sets: dict[int, NodeSets] = {}       # object id -> NodeSets
        self.member_of: dict[int, object] = {}         # subject id -> object ids it appears in
        # Write-time cycle-detection index over the graph backend's DERIVED edges
        # (union schemas only). NOT read state -- reads never consult it.
        # N10: built LAZILY (``_ensure_flow_graph``) on the first flow-graph touch,
        # never during replay -- ``rebuild()`` skips the whole ``_derived_pairs``
        # fan-out (60% of true rebuild wall on union/TTU schemas), so a read-only
        # reopen (the ``refresh_evaluator`` rollback / tokened-read-fallback path)
        # pays nothing for state only writes consult. ``_flow_built`` gates both the
        # incremental maintenance in ``_apply_add`` / ``_apply_remove`` and the
        # one-shot build.
        self._flow_adj: dict[NodeKey, set[NodeKey]] = {}
        self._edge_count: dict[tuple[NodeKey, NodeKey], int] = {}
        self._flow_built: bool = False

    def rebuild(self) -> None:
        """Replay the TupleV1 table into fresh in-memory state (spec §3, §6.5)."""
        self._reset_state()
        rows = self.session.exec(
            select(TupleV1).where(TupleV1.store_id == self.store_id).order_by(TupleV1.id)
        ).all()
        for row in rows:
            self._apply_add(row.subject_predicate, row.subject_type, row.subject_name,
                            row.relation, row.object_type, row.object_name)

    # ------------------------------------------------------------------ #
    # Population masks (for the MemberSet algebra)
    # ------------------------------------------------------------------ #

    def _restrictions_of(self, direct) -> frozenset[tuple[str, str, bool]]:
        """P9: cached (type, predicate, wildcard) key set for a ``Direct`` node.

        Identical content to ``{(r.type, r.predicate, r.wildcard) for r in
        direct.restrictions}``; computed once per node and reused across the
        check and expand leaves (the node is lifetime-stable, see __init__).
        """
        key = id(direct)
        restr = self._restr_cache.get(key)
        if restr is None:
            restr = frozenset(
                (r.type, r.predicate, r.wildcard) for r in direct.restrictions
            )
            self._restr_cache[key] = restr
        return restr

    def population(self, shape: tuple[str, str]):
        """Concrete member ids of a shape: ids_of_type[T] for bare, ids_of_shape[(T,P)]."""
        entity_type, pred = shape
        if pred == '...':
            return self.interner.ids_of_type.get(entity_type, self.ops.new())
        return self.interner.ids_of_shape.get(shape, self.ops.new())

    # ------------------------------------------------------------------ #
    # Writes (§6.1) -- no rewrite expansion, no derived state
    # ------------------------------------------------------------------ #

    def add_tuple(self, subject_predicate, s_type: str, s_name: str,
                  relation: str, o_type: str, o_name: str) -> bool:
        """Add one raw tuple; True if added, False for the idempotent duplicate
        no-op. Raises ``ValueError`` only from validation, BEFORE any in-memory
        mutation (ConnectedStore's rejection path relies on this to skip the
        evaluator rebuild). This backend computes no deltas (§6.1)."""
        s_pred = _norm_pred(subject_predicate)
        validate_write_identifiers(s_pred, s_type, s_name, relation, o_type, o_name)
        if self._tuple_present(s_pred, s_type, s_name, relation, o_type, o_name):
            return False                               # idempotent: septuple already present (in-memory, no SELECT)
        # one rewrite fan-out per accepted add: validation and application share it
        pairs = self._derived_pairs(s_pred, s_type, s_name, relation, o_type, o_name)
        self._validate(s_pred, s_type, s_name, relation, o_type, o_name, pairs)
        self.session.add(TupleV1(
            store_id=self.store_id, subject_predicate=s_pred, subject_type=s_type,
            subject_name=s_name, relation=relation, object_type=o_type, object_name=o_name))
        self._apply_add(s_pred, s_type, s_name, relation, o_type, o_name, pairs=pairs)
        return True

    def remove_tuple(self, subject_predicate, s_type: str, s_name: str,
                     relation: str, o_type: str, o_name: str) -> None:
        """Remove one raw tuple. Raises ``ValueError`` only from validation /
        the missing-tuple rejection, BEFORE any in-memory mutation (same contract
        as ``add_tuple``)."""
        s_pred = _norm_pred(subject_predicate)
        validate_write_identifiers(s_pred, s_type, s_name, relation, o_type, o_name)
        # Cheap in-memory existence test first; only fetch the ORM row (needed for
        # session.delete) when the tuple is actually present -- an absent tuple is
        # rejected without a DB round-trip.
        if not self._tuple_present(s_pred, s_type, s_name, relation, o_type, o_name):
            raise ValueError('non-existent tuple cannot be removed')
        row = self._row(s_pred, s_type, s_name, relation, o_type, o_name)
        self.session.delete(row)
        # Flush the delete now. The old per-add ``_row`` SELECT (dropped in P0)
        # implicitly autoflushed pending ops on every add, so a delete never sat
        # pending when a later same-key add queued its insert. Without that, a
        # re-add of a just-removed septuple leaves INSERT+DELETE pending on the
        # same unique key in one uncommitted batch, and SQLAlchemy's unit-of-work
        # orders the INSERT before the DELETE -> UNIQUE violation on flush.
        # Flushing here restores the delete-before-reinsert ordering.
        self.session.flush()
        self._apply_remove(s_pred, s_type, s_name, relation, o_type, o_name)

    def _tuple_present(self, s_pred, s_type, s_name, relation, o_type, o_name) -> bool:
        """Authoritative in-memory existence test for one raw septuple, replacing the
        per-write ``_row`` SELECT (P0). The tuple is present iff both endpoints are
        interned AND the subject id sits in the object node's membership set --
        ``entities`` for a bare '...' subject, ``usersets`` otherwise. ``node_sets``
        membership is populated ONLY by real ``_apply_add``s (never by the reverse-
        dependency candidate interning in ``_apply_add``), so this is exact, not an
        over-approximation."""
        subject_id = self.interner.get(s_type, s_name, s_pred)
        object_id = self.interner.get(o_type, o_name, relation)
        if subject_id is None or object_id is None:
            return False
        ns = self.node_sets.get(object_id)
        if ns is None:
            return False
        return subject_id in (ns.entities if s_pred == '...' else ns.usersets)

    def _row(self, s_pred, s_type, s_name, relation, o_type, o_name) -> TupleV1 | None:
        return self.session.exec(
            select(TupleV1)
            .where(TupleV1.store_id == self.store_id)
            .where(TupleV1.subject_predicate == s_pred)
            .where(TupleV1.subject_type == s_type)
            .where(TupleV1.subject_name == s_name)
            .where(TupleV1.relation == relation)
            .where(TupleV1.object_type == o_type)
            .where(TupleV1.object_name == o_name)
        ).first()

    def _apply_add(self, s_pred, s_type, s_name, relation, o_type, o_name, *,
                   pairs=None) -> None:
        subject_id = self.interner.acquire(s_type, s_name, s_pred)   # +1 ref (create mapping if new)
        object_id = self.interner.acquire(o_type, o_name, relation)
        ns = self.node_sets.get(object_id)
        if ns is None:
            ns = NodeSets(self.ops.new(), self.ops.new())
            self.node_sets[object_id] = ns
        # classification is purely by predicate: entities carry '...', usersets a relation
        (ns.entities if s_pred == '...' else ns.usersets).add(subject_id)
        mo = self.member_of.get(subject_id)
        if mo is None:
            mo = self.ops.new()
            self.member_of[subject_id] = mo
        mo.add(object_id)

        # Reverse-dependency candidate interning (spec §6.4 reverse propagation,
        # adapted): a stored tuple of relation r anchors -- on this very object --
        # every relation that reaches r in reverse through Computed chains or a
        # TTU tupleset, so intern those object keys now (the lookup semi-join can
        # then enumerate, and return real ids for, TTU-/Computed-only objects);
        # and intern the TTU from-chain userset (subject, target_rel) so expand /
        # lookup_reverse can represent it. Write-path only (reads stay
        # side-effect-free); rebuild() replays the same acquisitions, and
        # _apply_remove releases them symmetrically.
        for dep in self._object_deps.get((o_type, relation), ()):
            self.interner.acquire(o_type, o_name, dep)
        if s_pred == '...' and s_name != '*':
            for tgt in self._chain_targets.get((o_type, relation), ()):
                self.interner.acquire(s_type, s_name, tgt)

        # N10: flow-graph maintenance is deferred until the graph is built. During
        # replay (rebuild / constructor) ``_flow_built`` is False, so the whole
        # ``_derived_pairs`` fan-out is skipped -- the eventual lazy build reads the
        # final in-memory state. Once built, every accepted add maintains it
        # incrementally (``pairs`` is passed in by ``add_tuple``, already computed
        # for ``_validate``'s cycle check).
        if self._flow_built:
            if pairs is None:
                pairs = self._derived_pairs(s_pred, s_type, s_name, relation, o_type, o_name)
            for u, v in pairs:
                if u != v:
                    self._flow_add_edge(u, v)

    def _apply_remove(self, s_pred, s_type, s_name, relation, o_type, o_name) -> None:
        subject_id = self.interner.get(s_type, s_name, s_pred)
        object_id = self.interner.get(o_type, o_name, relation)
        if subject_id is None or object_id is None:
            return
        # Prune the membership entry, dropping now-empty node/member maps so nothing
        # accumulates for removed entities.
        ns = self.node_sets.get(object_id)
        if ns is not None:
            (ns.entities if s_pred == '...' else ns.usersets).discard(subject_id)
            if not ns.entities and not ns.usersets:
                self.node_sets.pop(object_id, None)
        mo = self.member_of.get(subject_id)
        if mo is not None:
            mo.discard(object_id)
            if len(mo) == 0:
                self.member_of.pop(subject_id, None)
        # N10: maintain the flow graph only once it is built; a remove arriving
        # first on a never-read (unbuilt) graph must not decrement it (the eventual
        # lazy build reads the post-remove state -- node_sets is pruned above).
        if self._flow_built:
            for u, v in self._derived_pairs(s_pred, s_type, s_name, relation, o_type, o_name):
                if u != v:
                    self._flow_remove_edge(u, v)
        # Release the reverse-dependency candidate references (mirrors _apply_add).
        for dep in self._object_deps.get((o_type, relation), ()):
            did = self.interner.get(o_type, o_name, dep)
            if self.interner.release(o_type, o_name, dep) is not None:
                self.node_sets.pop(did, None)
                self.member_of.pop(did, None)
        if s_pred == '...' and s_name != '*':
            for tgt in self._chain_targets.get((o_type, relation), ()):
                tid = self.interner.get(s_type, s_name, tgt)
                if self.interner.release(s_type, s_name, tgt) is not None:
                    self.node_sets.pop(tid, None)
                    self.member_of.pop(tid, None)
        # Release interner references; a freed (recycled) id must not carry residual state.
        if self.interner.release(s_type, s_name, s_pred) is not None:
            self.node_sets.pop(subject_id, None)
            self.member_of.pop(subject_id, None)
        if self.interner.release(o_type, o_name, relation) is not None:
            self.node_sets.pop(object_id, None)
            self.member_of.pop(object_id, None)

    # ------------------------------------------------------------------ #
    # Flow-graph index (write-time cycle detection; union schemas only)
    # ------------------------------------------------------------------ #

    def _derived_pairs(self, s_pred, s_type, s_name, relation, o_type, o_name) -> list[tuple[NodeKey, NodeKey]]:
        """ALL of the graph backend's derived (node_from, node_to) pairs for this raw
        tuple, u == v included (the trivial-cycle probe needs those; the flow graph
        skips them). Reuses the compiled RuleSet so the flow graph is byte-for-byte
        the graph index's edge set. Empty for schemas with no RuleSet."""
        if self._ruleset is None:
            return []
        triple = RelationalTriple(
            subject=Entity(s_type, s_name), relation=relation,
            object=Entity(o_type, o_name), subject_predicate=_denorm_pred(s_pred))
        return [((d.subject.type, d.subject.name, _norm_pred(d.subject_predicate)),
                 (d.object.type, d.object.name, d.relation))
                for d in self._ruleset.apply(triple)]

    def _ensure_flow_graph(self) -> None:
        """N10: build the write-time cycle-detection flow graph lazily, exactly once,
        on the first flow-graph touch (a ``_would_cycle`` / ``_flow_reaches`` read, or
        a ``_flow_add_edge`` / ``_flow_remove_edge`` mutation). ``rebuild()`` and the
        constructor's replay skip all ``_derived_pairs`` work, so a read-only reopen
        never pays for state reads never consult.

        Reconstructed from the engine's own in-memory raw-tuple state -- ``node_sets``
        holds EXACTLY the stored septuples (it is populated only by real ``_apply_add``s,
        never by the §6.4 reverse-dependency candidate interning; the same completeness
        ``_tuple_present`` relies on to answer without a SELECT), so no DB read is
        needed. Iterating it and re-running ``_derived_pairs`` over every membership
        reproduces the identical edge multiset the old per-row replay built (
        ``_flow_add_edge`` is count-based and order-independent). ``_flow_built`` is set
        BEFORE populating so the ``_flow_add_edge`` calls below re-enter as no-ops.
        Boolean / ruleset-less schemas build nothing (``_derived_pairs`` is empty)."""
        if self._flow_built:
            return
        self._flow_built = True
        if self._ruleset is None:
            return
        for object_id, ns in self.node_sets.items():
            o_type, o_name, relation = self.interner.key(object_id)
            for subject_id in chain(ns.entities, ns.usersets):
                s_type, s_name, s_pred = self.interner.key(subject_id)
                for u, v in self._derived_pairs(s_pred, s_type, s_name, relation,
                                                o_type, o_name):
                    if u != v:
                        self._flow_add_edge(u, v)

    def _flow_add_edge(self, u: NodeKey, v: NodeKey) -> None:
        self._ensure_flow_graph()
        c = self._edge_count.get((u, v), 0)
        self._edge_count[(u, v)] = c + 1
        if c == 0:
            self._flow_adj.setdefault(u, set()).add(v)

    def _flow_remove_edge(self, u: NodeKey, v: NodeKey) -> None:
        self._ensure_flow_graph()
        c = self._edge_count.get((u, v), 0)
        if c <= 1:
            self._edge_count.pop((u, v), None)
            succ = self._flow_adj.get(u)
            if succ is not None:
                succ.discard(v)
        else:
            self._edge_count[(u, v)] = c - 1

    def _flow_reaches(self, src: NodeKey, dst: NodeKey, extra: list[tuple[NodeKey, NodeKey]]) -> bool:
        """Is dst reachable from src in the flow graph plus `extra` (tentative) edges?"""
        self._ensure_flow_graph()
        seen: set[NodeKey] = set()
        stack = [src]
        while stack:
            node = stack.pop()
            if node == dst:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(self._flow_adj.get(node, ()))
            stack.extend(v for (a, v) in extra if a == node)
        return False

    # ------------------------------------------------------------------ #
    # Validation (§6.2) -- parity with the graph backend, side-effect free
    # ------------------------------------------------------------------ #

    def _validate(self, s_pred, s_type, s_name, relation, o_type, o_name,
                  pairs) -> None:
        # (1) object-wildcard gating: a T:* object is valid only for a declared shape.
        if o_name == '*' and (o_type, relation) not in self.schema_info.object_wildcard_shapes:
            raise ValueError(
                f"object wildcard {o_type}:* (relation {relation!r}) is not a declared "
                f"object-wildcard shape")

        # (2) type-restriction validity via the schema's strict Filters (same code as the
        #     graph backend). Subject-wildcard gating is encoded IN the Filters (a [T:*]
        #     restriction yields a subject_name='*' filter; [T] keeps rejecting T:*).
        triple = RelationalTriple(
            subject=Entity(s_type, s_name), relation=relation,
            object=Entity(o_type, o_name), subject_predicate=_denorm_pred(s_pred))
        if not any(f.apply(triple) for f in self.filters):
            raise ValueError(
                f"tuple {s_type}:{s_name}#{s_pred} {relation} {o_type}:{o_name} matches no "
                f"declared type restriction for {o_type}#{relation}")

        # (3) cycle rejection (§6.2): reject usersets whose membership would loop, matching
        #     the graph backend's cycle detection. Side-effect free -- uses existing ids only.
        if self._would_cycle(s_pred, s_type, s_name, relation, o_type, pairs):
            raise ValueError(
                f"tuple {s_type}:{s_name}#{s_pred} {relation} {o_type}:{o_name} would create a "
                f"cycle in the userset membership topology")

    def _would_cycle(self, s_pred, s_type, s_name, relation, o_type, pairs) -> bool:
        # Boolean schemas have no graph partner and the oracle evaluates cyclic schemas
        # rather than rejecting -- so we do not reject data cycles for them.
        if self._ruleset is None:
            return False

        # Same-shape wildcard self-reference (e.g. group:*#member member group:g): a cycle
        # by construction that the graph backend also rejects (§1.5).
        if s_name == '*' and s_pred != '...' and (s_type, s_pred) == (o_type, relation):
            return True

        # The same self-reference at the ROUTED level: a rewrite can MINT the star
        # userset from a bare star subject -- e.g. `folder:* parent folder:f2` routes
        # (via the TTU rewrite's through-shape) to `folder:*#viewer viewer folder:f2`,
        # whose object participates in the wildcard's own (subject-wildcard) shape.
        # The graph rejects that write by construction: bridge-before-grant gives the
        # object node an in-bridge to the star userset node, and the grant edge closes
        # the two-cycle (wildcard.py's reworded cycle error). The raw-level check
        # above cannot see it (the raw subject is bare), and the flow graph cannot
        # either (it carries only RuleSet-derived edges, never the materialized
        # bridges), so mirror it over every derived pair. The through-shape guard is
        # documentation-exactness: a routed star userset's shape is always declared
        # (`_expand_object_wildcard_shapes` / the D3 through-shape derivation), so it
        # never blocks a pair the graph would accept.
        for (ut, un, up), (vt, _vn, vr) in pairs:
            if (un == '*' and up != '...' and (ut, up) == (vt, vr)
                    and (ut, up) in self.schema_info.subject_wildcard_shapes):
                return True

        # A derived pair whose endpoints coincide is the trivial cycle (e.g.
        # doc:x#viewer viewer doc:x) -- blind-audit E3: the graph backend rejects
        # the same tuple.
        if any(u == v for u, v in pairs):
            return True

        # Would adding any DERIVED edge u->v close a loop? (v already reaches u.) This
        # reproduces the graph backend's reachability cycle check exactly, so both accept
        # and reject the same op sequences -- including from-chain cycles.
        edges = [(u, v) for u, v in pairs if u != v]
        for u, v in edges:
            if self._flow_reaches(v, u, edges):
                return True
        return False

    # ------------------------------------------------------------------ #
    # Object-node resolution shared by the evaluator
    # ------------------------------------------------------------------ #

    def _object_ids(self, o_type: str, o_name: str, rel: str) -> list[int]:
        """Interned ids for (o_type,o_name,rel) plus the star object (o_type,'*',rel) when
        declared and the query object is concrete (§6.3 object-side handling)."""
        ids: list[int] = []
        if o_name == '*':
            i = self.interner.get(o_type, '*', rel)          # intensional: star object only
            if i is not None:
                ids.append(i)
            return ids
        i = self.interner.get(o_type, o_name, rel)
        if i is not None:
            ids.append(i)
        if (o_type, rel) in self.schema_info.object_wildcard_shapes:
            si = self.interner.get(o_type, '*', rel)
            if si is not None:
                ids.append(si)
        return ids

    def _instances_of_type(self, t: str, memo: dict[str, set[str]]) -> set[str]:
        """Concrete instance names of a type (interner keys), for the strict ∀⇒∃
        expansion of star tuplesets. Rare path (star parents).

        N7: memoized per evaluation. This scans ALL interned keys (O(interner)); the
        interner never mutates during a read, so one scan per type serves an entire
        ``check`` / ``expand`` call. ``memo`` is a CALL-LOCAL dict, never persisted
        across writes (interner ids are only guaranteed stable within a single read).
        The returned set is shared read-only across calls in one evaluation -- callers
        only iterate it. The former ``query_names`` union arm is dropped: every call
        site passed ``frozenset()`` (query endpoints must never act as ∃-witnesses --
        strict ∀⇒∃), so the arm was always empty."""
        cached = memo.get(t)
        if cached is not None:
            return cached
        names = {n for (kt, n, _p) in self.interner.key_of.values() if kt == t and n != '*'}
        memo[t] = names
        return names

    # ------------------------------------------------------------------ #
    # check -- pointwise, short-circuiting (§6.3)
    # ------------------------------------------------------------------ #

    def check(self, subject_predicate, s_type: str, s_name: str,
              relation: str, o_type: str, o_name: str) -> bool:
        s_pred = _norm_pred(subject_predicate)
        subject = (s_type, s_name, s_pred)
        memo: dict[tuple[str, str, str], bool] = {}
        inst_memo: dict[str, set[str]] = {}             # N7: per-eval _instances_of_type cache
        stack: dict[tuple[str, str, str], int] = {}     # key -> stack depth
        # Lowlink memo guard (see tests/oracle.py sat, kept in lockstep): a frame
        # whose subtree consulted an in-progress key computed only a provisional
        # answer -- memoizing it would poison non-short-circuiting boolean consumers
        # and make answers depend on bitmap/interner iteration order.
        _INF = float('inf')
        low = [_INF]

        def sat(ot: str, on: str, rel: str) -> bool:
            key = (ot, on, rel)
            cached = memo.get(key)
            if cached is not None:
                return cached
            if key in stack:
                low[0] = min(low[0], stack[key])
                return False
            expr = self.ast.get((ot, rel))
            if expr is None:
                memo[key] = False
                return False
            depth = len(stack)
            stack[key] = depth
            outer_low, low[0] = low[0], _INF
            result = sat_expr(expr, ot, on, rel)
            my_low = low[0]
            del stack[key]
            if my_low >= depth:
                memo[key] = result
                low[0] = outer_low
            else:
                low[0] = min(outer_low, my_low)
            return result

        def sat_expr(expr, ot: str, on: str, rel: str) -> bool:
            if isinstance(expr, Union):
                return any(sat_expr(c, ot, on, rel) for c in expr.children)
            if isinstance(expr, Intersection):
                return all(sat_expr(c, ot, on, rel) for c in expr.children)
            if isinstance(expr, Exclusion):
                return sat_expr(expr.base, ot, on, rel) and not sat_expr(expr.subtract, ot, on, rel)
            if isinstance(expr, Direct):
                return direct_leaf(expr, ot, on, rel)
            if isinstance(expr, Computed):
                return sat(ot, on, expr.relation)
            if isinstance(expr, TTU):
                return ttu_leaf(expr.target_rel, expr.tupleset_rel, ot, on)
            raise TypeError(f'unknown AST node {expr!r}')

        def direct_leaf(direct, ot: str, on: str, rel: str) -> bool:
            restr = self._restrictions_of(direct)
            nodes = [self.node_sets[i] for i in self._object_ids(ot, on, rel) if i in self.node_sets]
            if not nodes:
                return False

            def in_entities(uid):
                return uid is not None and any(uid in ns.entities for ns in nodes)

            def in_usersets(uid):
                return uid is not None and any(uid in ns.usersets for ns in nodes)

            if s_name == '*':
                # intensional on this branch's own restrictions: the matching star
                # sentinel granted here...
                if s_pred == '...':
                    if (s_type, '...', True) in restr and in_entities(
                            self.interner.get(s_type, '*', '...')):
                        return True
                elif (s_type, s_pred, True) in restr and in_usersets(
                        self.interner.get(s_type, '*', s_pred)):
                    return True
                # ...or flow-through: '*' resolves through granted usersets like any
                # subject (blind-audit D1 -- the OpenFGA literal-subject reading; the
                # graph closure and this engine's own expand already behave this way,
                # and per-branch-only is structurally unimplementable in the graph)
                return member_via_usersets(nodes, restr)

            if s_pred == '...':
                # concrete bare entity
                if (s_type, '...', False) in restr and in_entities(
                        self.interner.get(s_type, s_name, '...')):
                    return True
                if (s_type, '...', True) in restr and in_entities(
                        self.interner.get(s_type, '*', '...')):
                    return True
                return member_via_usersets(nodes, restr)

            # userset query subject
            if (s_type, s_pred, False) in restr and in_usersets(
                    self.interner.get(s_type, s_name, s_pred)):
                return True
            if (s_type, s_pred, True) in restr and in_usersets(
                    self.interner.get(s_type, '*', s_pred)):
                return True
            return member_via_usersets(nodes, restr)

        def member_via_usersets(nodes, restr) -> bool:
            # iterate only usersets (small, topology-shaped -- the §5 performance invariant)
            for ns in nodes:
                for uid in ns.usersets:
                    t, n, p = self.interner.key(uid)
                    if n != '*':
                        if (t, p, False) in restr and sat(t, n, p):
                            return True
                    elif (t, p, True) in restr:
                        # ∀-shaped grant (T:*#P): ∃ an INSTANCE of T whose P contains
                        # the subject. Instances come from tuple-mentioned names only
                        # (blind-audit: never from ids_of_shape, which misses members
                        # via Computed/TTU; and never from query endpoints, which
                        # would let a ghost witness its own existence -- strict ∀⇒∃)
                        for inst in self._instances_of_type(t, inst_memo):
                            if sat(t, inst, p):
                                return True
            return False

        def ttu_leaf(target_rel: str, tupleset_rel: str, ot: str, on: str) -> bool:
            nodes = [self.node_sets[i] for i in self._object_ids(ot, on, tupleset_rel)
                     if i in self.node_sets]
            for ns in nodes:
                # tupleset subjects (parents) live in entities (bare) -- iterated per §6.3;
                # userset tuplesets are unusual but handled for completeness.
                # N8: reads never mutate node_sets, so iterate lazily (no list copies).
                for pid in chain(ns.entities, ns.usersets):
                    pt, pn, _pp = self.interner.key(pid)
                    if pn != '*':
                        if (s_type, s_name, s_pred) == (pt, pn, target_rel):
                            return True                       # the from-chain userset itself
                        if sat(pt, pn, target_rel):
                            return True
                    else:
                        if (s_type, s_pred) == (pt, target_rel):
                            return True                       # star/userset subject of that shape
                        # tuple-mentioned instances only: query endpoints must not
                        # act as ∃-witnesses (strict ∀⇒∃; blind-audit O3)
                        for inst in self._instances_of_type(pt, inst_memo):
                            if sat(pt, inst, target_rel):
                                return True
            return False

        return sat(o_type, o_name, relation)

    # ------------------------------------------------------------------ #
    # expand -- bulk, memoized MemberSets (§6.3)
    # ------------------------------------------------------------------ #

    def expand(self, relation: str, o_type: str, o_name: str,
               memo: dict | None = None) -> MemberSet:
        """The full member set of (o_type, o_name, relation) as a MemberSet (§6.3).

        Concrete entity/userset members land in ``pos``; subject wildcards become star
        shapes in ``stars`` (never enumerated). Never interns on read."""
        if memo is None:
            memo = {}
        inst_memo: dict[str, set[str]] = {}             # N7: per-eval _instances_of_type cache
        stack: dict[tuple[str, str, str], int] = {}     # key -> stack depth
        ops, pop = self.ops, self.population
        # Lowlink memo guard, same as check()/the oracle: a frame whose subtree
        # consulted an in-progress key holds a provisional (under-approximated)
        # MemberSet and must not be memoized.
        _INF = float('inf')
        low = [_INF]

        def do(ot: str, on: str, rel: str) -> MemberSet:
            key = (ot, on, rel)
            cached = memo.get(key)
            if cached is not None:
                return cached
            if key in stack:
                low[0] = min(low[0], stack[key])
                return ms.empty(ops)
            expr = self.ast.get((ot, rel))
            if expr is None:
                memo[key] = ms.empty(ops)
                return memo[key]
            depth = len(stack)
            stack[key] = depth
            outer_low, low[0] = low[0], _INF
            r = do_expr(expr, ot, on, rel)
            my_low = low[0]
            del stack[key]
            if my_low >= depth:
                memo[key] = r
                low[0] = outer_low
            else:
                low[0] = min(outer_low, my_low)
            return r

        def do_expr(expr, ot, on, rel) -> MemberSet:
            if isinstance(expr, Union):
                acc = ms.empty(ops)
                for c in expr.children:
                    acc = ms.union(acc, do_expr(c, ot, on, rel), ops, pop)
                return acc
            if isinstance(expr, Intersection):
                acc = None
                for c in expr.children:
                    m = do_expr(c, ot, on, rel)
                    acc = m if acc is None else ms.intersect(acc, m, ops, pop)
                return acc if acc is not None else ms.empty(ops)
            if isinstance(expr, Exclusion):
                return ms.subtract(do_expr(expr.base, ot, on, rel),
                                   do_expr(expr.subtract, ot, on, rel), ops, pop)
            if isinstance(expr, Direct):
                return direct_expand(expr, ot, on, rel)
            if isinstance(expr, Computed):
                return do(ot, on, expr.relation)
            if isinstance(expr, TTU):
                return ttu_expand(expr.target_rel, expr.tupleset_rel, ot, on)
            raise TypeError(f'unknown AST node {expr!r}')

        def direct_expand(direct, ot, on, rel) -> MemberSet:
            restr = self._restrictions_of(direct)
            nodes = [self.node_sets[i] for i in self._object_ids(ot, on, rel) if i in self.node_sets]
            pos = ops.new()
            stars: set[tuple[str, str]] = set()
            acc = ms.empty(ops)
            for ns in nodes:
                for (rtype, rpred, rwild) in restr:
                    if rpred != '...':
                        continue
                    if rwild:
                        sid = self.interner.get(rtype, '*', '...')
                        if sid is not None and sid in ns.entities:
                            stars.add((rtype, '...'))
                    else:
                        # intersect the (small) node entities against the persistent
                        # type-population mask directly; wrapping pop(...) in ops.new()
                        # copied the whole O(population) mask per expand (& returns a
                        # new set, so neither operand is mutated). N8: drop the copy of
                        # ns.entities too -- `&` reads it without mutating.
                        pos |= (ns.entities & pop((rtype, '...')))
                for uid in ns.usersets:
                    t, n, p = self.interner.key(uid)
                    if n != '*':
                        if (t, p, False) in restr:
                            pos.add(uid)                              # the userset node itself
                            acc = ms.union(acc, do(t, n, p), ops, pop)
                    elif (t, p, True) in restr:
                        stars.add((t, p))                             # covers all usersets of shape
                        # tuple-mentioned instances, not ids_of_shape: an instance
                        # whose P-membership exists only via Computed/TTU never
                        # interns (T, n, P) and would be missed (blind-audit E2)
                        for inst in self._instances_of_type(t, inst_memo):
                            acc = ms.union(acc, do(t, inst, p), ops, pop)
            local = MemberSet(ops.freeze(pos), frozenset(stars), ops.freeze())
            return ms.union(local, acc, ops, pop)

        def ttu_expand(target, tupleset, ot, on) -> MemberSet:
            nodes = [self.node_sets[i] for i in self._object_ids(ot, on, tupleset)
                     if i in self.node_sets]
            acc = ms.empty(ops)
            for ns in nodes:
                # N8: reads never mutate node_sets, so iterate lazily (no list copies).
                for pid in chain(ns.entities, ns.usersets):
                    pt, pn, _pp = self.interner.key(pid)
                    if pn != '*':
                        acc = ms.union(acc, do(pt, pn, target), ops, pop)
                        fid = self.interner.get(pt, pn, target)       # from-chain userset itself
                        if fid is not None:
                            acc = ms.union(acc, ms.singleton_entity(fid, ops), ops, pop)
                    else:
                        acc = ms.union(acc, ms.star((pt, target), ops), ops, pop)
                        # tuple-mentioned instances only (no endpoint witnesses; O3)
                        for inst in self._instances_of_type(pt, inst_memo):
                            acc = ms.union(acc, do(pt, inst, target), ops, pop)
            return acc

        return do(o_type, o_name, relation)

    # ------------------------------------------------------------------ #
    # Lookups (§6.4)
    # ------------------------------------------------------------------ #

    def lookup_reverse(self, relation: str, o_type: str, o_name: str) -> LookupResult:
        """Everything that can reach the object: expand rendered as a LookupResult (§6.4).

        Concretes come from the MemberSet's ``pos``; star shapes become symbolic markers
        (never enumerated to concretes)."""
        m = self.expand(relation, o_type, o_name)
        result = LookupResult()
        result.node_ids = set(m.pos)
        result.markers = set(m.stars)
        return result

    def _reverse_neighbors(self, oid: int) -> list[int]:
        """Candidate object nodes one reverse membership hop from a node the subject
        is (a candidate) member of -- the dual of ``expand``'s forward edges:

        - **H1 userset fan-in:** ``member_of[oid]`` -- objects that granted this
          userset node a relation (``group:g#member viewer doc:x`` etc.).
        - **H2 same-object Computed/TTU-tupleset dependents:** ``_object_deps`` --
          relations ``R`` on the SAME object anchored by this node's relation.
        - **H3 TTU from-chain:** the entity's stored tupleset memberships
          (``member_of`` of the bare / star-bare node) crossed with ``_ttu_map`` -- a
          stored parent tuple lets ``parent#target_rel`` reach ``object#R``.

        Returns interned ids only; an unreachable/uninterned candidate is dropped
        (it can carry no result). Bare-entity/star nodes contribute their H1 edges
        but generate no H2/H3 (their relation slot is not a declared relation)."""
        return self._reverse_neighbors_key(*self.interner.key(oid), oid=oid)

    def _reverse_neighbors_key(self, t: str, n: str, rel: str,
                               oid: int | None = None) -> list[int]:
        """``_reverse_neighbors`` addressed by SURROGATE KEY rather than interned id,
        so the walk can seed from an UNINTERNED subject shape (H2/H3 need only the
        bare siblings interned, not the ``(t, n, rel)`` node itself). ``oid`` is the
        node's id when known (drives H1 ``member_of``); pass ``None`` for a key with
        no live node -- H1 is then empty, but the H1-star-coverage and H2/H3 hops
        still fire off the (interned) siblings. See ``_reverse_neighbors``."""
        out: list[int] = []
        if oid is None:
            oid = self.interner.get(t, n, rel)
        if oid is not None:
            mo = self.member_of.get(oid)                   # H1 direct fan-in
            if mo is not None:
                out.extend(mo)
        if n != '*':                                       # H1 star coverage
            # the wildcard sibling (t, '*', rel) covers this node: a `[t:*]`
            # (bare) or `[t:*#rel]` (userset) grant made to the star sentinel is
            # inherited by every concrete member of the shape (check's star-restr
            # branch). Verified downstream by check() like any other candidate.
            star_id = self.interner.get(t, '*', rel)
            if star_id is not None:
                mos = self.member_of.get(star_id)
                if mos is not None:
                    out.extend(mos)
        if rel != '...':
            for R in self._object_deps.get((t, rel), ()):  # H2
                rid = self.interner.get(t, n, R)
                if rid is not None:
                    out.append(rid)
            # H3 (TTU from-chain over bare parent tuplesets): the concrete bare
            # sibling (t, n, '...') carries this entity's stored parent tuples, and
            # -- when (t, n) is a concrete instance -- so does the STAR bare sibling
            # (t, '*', '...'). A stored star parent tuple `Q:q ts t:*` makes EVERY
            # tuple-mentioned instance of t a parent of Q:q (check's strict forall=>
            # exists, ttu_leaf's star branch), so a subject confirmed on (t, n, rel)
            # must hop to (Q, q, R) for R in _ttu_map[(Q, ts, rel)] just as for a
            # concrete parent. This is the bare twin of the H1 star fold above (line
            # ~1009). For n == '*' the concrete bare_id already IS the star bare, so
            # do not double-process. Candidates are check-confirmed at visit, so this
            # is a pure completeness addition (over-approx safe).
            bare_ids = [self.interner.get(t, n, '...')]     # H3 concrete bare parent
            if n != '*':
                bare_ids.append(self.interner.get(t, '*', '...'))  # H3 star bare parent
            for bare_id in bare_ids:
                if bare_id is None:
                    continue
                mob = self.member_of.get(bare_id)
                if mob is None:
                    continue
                for pid in mob:
                    ot, on, ts = self.interner.key(pid)
                    for R in self._ttu_map.get((ot, ts, rel), ()):
                        rid = self.interner.get(ot, on, R)
                        if rid is not None:
                            out.append(rid)
        return out

    def lookup(self, subject_predicate, s_type: str, s_name: str) -> LookupResult:
        """Everything the subject can reach (§6.4), via an O(reachable) reverse walk.

        The dual of ``expand``: a reverse BFS over membership edges from the subject
        (seeded by its direct memberships, propagated by ``_reverse_neighbors``'s
        H1/H2/H3 hops -- the mirror of ``check``'s direct-userset / Computed / TTU
        recursion). Each surfaced candidate is confirmed by ``check`` (exact under
        booleans, so an over-approximate candidate that an ``and``/``but not`` excludes
        is dropped), and only confirmed nodes propagate -- so the walk touches the
        subject's reachable neighborhood, never the whole store. Replaces the former
        O(stored-tuples) candidate sweep (``_lookup_sweep``, kept as the differential
        test reference); the write-time reverse-dependency interning (``_apply_add``)
        still guarantees every reachable object key has an id for the walk to find.
        Markers are intensional and exact by construction: one star-object check per
        declared relation, so star coverage arriving through Computed/TTU hops
        surfaces without enumerating names.

        N17 -- **wildcard-bridge seeding.** An object-wildcard grant ``s #... rel T:*``
        makes ``s`` a member of every concrete ``(T, X, rel)``, but the reverse walk
        only ever reaches the ``(T, '*', rel)`` star node, never the wildcard-covered
        concrete siblings ``(T, X, rel)``. That is harmless while those concretes are
        *direct* results -- the intensional marker ``(T, rel)`` covers them exactly
        (S4) -- but the walk would then silently drop any DOWNSTREAM object whose
        membership is inherited THROUGH such a concrete node (a TTU from-chain, or a
        non-wildcard userset restriction), which no marker covers. ``check`` crosses
        from one object's membership to another's by exactly two mechanisms (see
        ``member_via_usersets`` / ``ttu_leaf``): (a) a NON-wildcard userset restriction
        ``[T#r]`` lifts ``T:X#r``'s members onto a grantee, and (b) a TTU from-chain
        ``R2: r from ts`` evaluates a stored tupleset parent ``T:X`` at ``r``. To keep
        the whole walk O(reachable) rather than falling back to the O(store) sweep for
        such schemas, when the walk DEQUEUES any star node ``(T, '*', p)`` (bare or
        userset; the trigger is per-TYPE and fires before the entity-node skip and
        regardless of the star node's own check outcome), it bridges T once: for each
        declared shape ``(T, r0)`` and each relation ``r'`` the injection reaches
        (``{r0} plus _object_deps[(T, r0)]`` -- ``_owc_bridge_reach[T]``), it enqueues
        (1) every interned concrete ``(T, X, r')`` (``ids_of_shape`` -- stored userset
        subjects, TTU chain-target-interned keys, dep-interned keys) so mechanisms (a)
        and the concrete-parent arm of (b) are seeded, and (2) the star-parent cross
        for the triple combo owc x star-parent x TTU where NO concrete ``(T, X, r')``
        is interned: for each object ``Q:q`` that stored ``T:*`` as a tupleset parent
        (``member_of`` of ``(T, '*', '...')``) and each ``R`` with ``R: r' from ts``,
        it enqueues ``(Q, q, R)``. Bridged nodes then propagate through the normal
        confirmed-only walk, so chained shapes compose.

        **Completeness (the bridge trigger + seeds cover every wildcard route):**
        1. Star-injection of the subject on shape ``(T, rel)`` requires the subject's
           membership among the star node ``(T, '*', rel)``'s direct members (the only
           truth source beyond stored-at-X tuples; ``_object_ids`` adds the star node
           only for shapes). Every such membership route enqueues a star node of T:
           (i) a direct grant / subject-star sentinel -> the seed's H1 (+ the line-1004
           H1 star fold); (ii) a stored userset ``u`` at the star node with ``sat(u)``
           true -> each intermediate hop is check-true and ``member_of``-connected, so
           ``u`` is visited & confirmed and ``member_of[u]`` contains the star node;
           (iii) a star userset sentinel ``(T2, '*', p)`` -> any confirmed instance
           ``(T2, inst, p)`` folds ``member_of[(T2, '*', p)]`` (the H1 star fold),
           which contains the star node; when the instance key is uninterned under
           boolean mixing, the stored non-star arm interns it via dep-interning and
           connects it (mixing requires stored arms). The trigger is per-TYPE (any
           dequeued ``(T, '*', *)``, bare included), strictly wider than per-shape.
        2. Given the trigger, every cross-object crossing out of a star-injected
           concrete is seeded: a userset lift needs a stored subject ``(T, X, r')``
           -> in ``ids_of_shape``; a TTU crossing from a concrete parent chain-interns
           ``(T, X, r')`` -> in ``ids_of_shape``; a TTU crossing from a STAR parent is
           seeded by the explicit star-parent cross (and ``(Q, q, R)`` is dep-interned
           by the parent-tuple write). Chained shapes compose because bridged nodes
           propagate through the normal confirmed-only walk, which can dequeue further
           star nodes.
        3. Soundness is unconditional: every candidate is confirmed by ``check`` before
           entering ``node_ids`` or propagating, and ``n == '*'`` nodes never enter
           ``node_ids`` (markers carry them)."""
        s_pred = _norm_pred(subject_predicate)
        result = LookupResult()
        for (t, rel) in self.ast:                          # declared (type, relation)
            if self.check(s_pred, s_type, s_name, rel, t, '*'):
                result.markers.add((t, rel))
        # Seed from the subject's memberships, addressed by SHAPE via
        # ``_reverse_neighbors_key`` so an UNINTERNED subject is seeded too (it
        # resolves its own id for H1 when live). A ghost/uninterned subject can still
        # reach concretes -- through a `[type:*]` grant (H1 star coverage), or, for a
        # userset subject `T:X#r` (concrete, ghost, OR the `*` shape itself), as a
        # from-chain identity member of every object with a stored `T`/`T:*` tupleset
        # parent whose TTU targets `r` (ttu_leaf's concrete + star identity branches;
        # H3, needing only the bare siblings interned, not the subject node). A
        # star-sibling-only / empty seed missed the from-chain star identity for
        # uninterned userset subjects on star-able tuplesets.
        queue: list[int] = self._reverse_neighbors_key(s_type, s_name, s_pred)
        if not queue:
            return result                   # reaches nothing concrete: no seed, so no
                                            # star node can be dequeued to bridge (only
                                            # markers, if any)
        visited: set[int] = set()
        bridged_types: set[str] = set()     # N17: object-wildcard types already bridged
        while queue:
            oid = queue.pop()
            if oid in visited:
                continue
            visited.add(oid)
            t, n, p = self.interner.key(oid)
            # N17 wildcard-bridge seeding: on dequeuing any star node of a type that
            # declares an object-wildcard shape, enqueue the wildcard-covered concrete
            # siblings the reverse walk cannot reach on its own (see docstring). Fires
            # before the entity-node skip and regardless of this node's check outcome
            # (a star node refuted at the intensional '*' object can still be
            # star-injected at concretes under boolean mixing).
            if n == '*' and t not in bridged_types:
                reach = self._owc_bridge_reach.get(t)
                if reach is not None:
                    bridged_types.add(t)
                    bs = self.interner.get(t, '*', '...')       # star bare tupleset node
                    star_parents = self.member_of.get(bs) if bs is not None else None
                    for r_prime in reach:
                        # (1) userset/TTU intermediates: every interned concrete
                        # (t, X, r') (.get -- never index the defaultdict).
                        for iid in self.interner.ids_of_shape.get((t, r_prime), ()):
                            if iid not in visited:
                                queue.append(iid)
                        # (2) star-parent cross: owc x star-parent x TTU where no
                        # concrete (t, X, r') is interned (unconditional -- must not
                        # depend on the '*'-object confirmation of any star sibling).
                        if star_parents is not None:
                            for pid in star_parents:
                                qt, qn, ts = self.interner.key(pid)
                                for R in self._ttu_map.get((qt, ts, r_prime), ()):
                                    rid = self.interner.get(qt, qn, R)
                                    if rid is not None and rid not in visited:
                                        queue.append(rid)
            if p == '...':
                continue                    # entity node: not a relation result
            if not self.check(s_pred, s_type, s_name, p, t, n):
                continue                    # over-approximate candidate refuted (boolean, etc.)
            if n != '*':
                result.node_ids.add(oid)    # concrete result; star objects carried by markers
            for nxt in self._reverse_neighbors(oid):        # propagate only from confirmed nodes
                if nxt not in visited:
                    queue.append(nxt)
        return result

    def _lookup_sweep(self, s_pred, s_type: str, s_name: str, result: LookupResult) -> None:
        """Exact O(stored-tuples) candidate sweep: every interned relation key is a
        candidate, confirmed by ``check`` (sound under booleans). The write-time
        reverse-dependency interning (``_apply_add``) guarantees TTU/Computed-only
        reachable object keys have ids, so this is complete; appends concrete ids to
        ``result.node_ids`` in place.

        No longer a runtime path: since N17 ``lookup`` walks on EVERY schema (the
        object-wildcard bridge is seeded inline). This is retained as the DIFFERENTIAL
        REFERENCE for that walk -- its trivially-complete sweep is the ground truth the
        property test ``test_owc_bridge_walk_vs_sweep`` asserts the walk's covered set
        (node_ids union marker-covered) equals over random add/remove states, the
        direct net for the N17 bridge-trigger completeness claim."""
        for (t, n, p) in list(self.interner.key_of.values()):
            if p == '...' or n == '*':
                continue                    # entity nodes are not relations; stars are markers
            if self.check(s_pred, s_type, s_name, p, t, n):
                oid = self.interner.get(t, n, p)
                if oid is not None:
                    result.node_ids.add(oid)


# The backend protocol (§6.5) is exactly SetEngine's surface: add_tuple / remove_tuple /
# check / lookup / lookup_reverse, constructed from (session, store_id, schema), plus
# rebuild() for open-replay.
SetEngineBackend = SetEngine
