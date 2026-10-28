"""
WildcardIndex: the wildcard-aware facade over ReachabilityIndex.

It materialises the interior wildcard hops as real ref-counted edges (bridges) at
write time, so that check() stays O(1): at most four point lookups on the unique
edge index, independent of data size or nesting depth. Only the two hops touching
the literal query endpoints stay virtual, covered by fixed probes.

This layer does NOT commit; sessions/transactions remain the caller's job (mirrors
ReachabilityIndex). All errors raise; on cycle rejection the caller's rollback
restores consistency.
"""
# Provenance (moved out of the docstring, TK123 item 14): spec §6/§7; §3.1.

from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import EllipsisType

from sqlalchemy import tuple_
from sqlmodel import select

from .cascade_mark import note_write as _note_cascade_owed
from .core import ReachabilityIndex, _ThreadFlag
from .invariants import InvariantViolation
from .models import Edge, Node, ResidueRef, Residue
from zanzibar.schema.tuplestr import shape_filter
from zanzibar.schema import (AdmissionRejected, SchemaInfo,
                               norm_pred as _norm_pred,
                               validate_node_identifiers,
                               validate_write_identifiers)


@dataclass
class LookupResult:
    """What ``lookup`` / ``lookup_reverse`` return (also via ``Store``).

    * ``node_ids``: ids of ``zanzibar.graphindex.Node`` rows in this store.
      ``Store.result_keys(result)`` turns them into ``(type, name, predicate)`` keys,
      ``predicate`` being the relation or ``"..."`` for a bare subject. Intermediate usersets
      (``group:eng#member``) are included. From ``lookup_reverse``, a userset in the result
      means the userset ITSELF is an allowed subject; it is not a claim about each member
      (under ``but not banned`` a banned member stays refused), so ask ``check`` about a
      member instead of expanding the userset.
    * ``markers``: wildcard grants as ``(type, predicate, variant)``. Variant ``"any"`` is
      subject-side: from ``lookup_reverse``, ``("user", "...", "any")`` means every user (a
      ``[user:*]`` tuple). Variant ``"all"`` is object-side and appears only with
      ``object_wildcard_shapes`` (an extension): from ``lookup``, ``("doc", "reader",
      "all")`` means reader of every doc (a ``doc:*`` tuple). An ``"all"`` marker from
      ``lookup_reverse``, or an ``"any"`` marker from ``lookup``, is a by-product of how
      wildcards are stored and carries no claim on its own.
    * ``excluded_node_ids``: node ids a marker would cover but that are refused (``but not``).
      The caller subtracts them: "every user except these". ``Store.excluded_keys(result)``
      gives their keys.
    * ``implicit_keys`` / ``implicit_excluded_keys``: the same two parts for answers that
      have NO node, as ``(type, name, predicate)`` keys. OpenFGA's implicit userset
      self-relation makes ``doc:1#viewer`` a viewer of ``doc:1`` on an empty store, and the
      index never creates a node to say so. ``Store.result_keys`` / ``excluded_keys`` fold
      them in, so read a result through those.

    A subject that a marker already covers may also appear in ``node_ids``; the set
    engine's ``SetLookupResult`` leaves it out. Compare results by what they cover (the
    keys, plus every subject of a marker's shape, minus the excluded keys), not as raw sets.
    """
    node_ids: set[int] = field(default_factory=set)               # concrete results
    markers: set[tuple[str, str, str]] = field(default_factory=set)  # (type, predicate, variant) symbolic "all/any"
    # "everyone of a starred shape EXCEPT these" (boolean spec §6): concrete node ids
    # excluded from a derived relation's star coverage, from the residue's neg.
    # Additive and empty everywhere except derived lookup_reverse.
    excluded_node_ids: set[int] = field(default_factory=set)
    # TK144 (TK138 D3a): answers / exclusions with no node, as (type, name, predicate).
    implicit_keys: set[tuple[str, str, str]] = field(default_factory=set)
    implicit_excluded_keys: set[tuple[str, str, str]] = field(default_factory=set)


class WildcardIndex:
    """The graph index's schema-aware layer over ``ReachabilityIndex``: writes, ``check``,
    ``lookup`` and ``lookup_reverse`` with wildcard (``user:*``) subjects and objects and
    with ``and`` / ``but not`` relations (which the delta processor maintains).

    Most programs use ``zanzibar.store.Store``, which owns one of these and keeps it in
    step with the tuple log; build one directly only to drive the graph index alone.
    """

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
        # TK144 (TK138 landing 2): OpenFGA's implicit userset self-relation. A concrete
        # userset subject T:o#p is a member of its own declared node (T, o, p), outside
        # the rewrite. Nothing is materialized for it (the self tuple is refused as a
        # cycle and never stored): the untainted read uses the compile-time seed table
        # (``SchemaInfo.self_seeds``: the relations and leaf predicates the self tuple
        # would fan out to through Computed rewrites), and the derived read evaluates the
        # plan at read time (C5). ``reflexive=False`` -- the delta processor's reconcile,
        # the invariants and the I9 audit -- keeps the residue and the canonical state
        # exactly as before. A hand-built SchemaInfo has no seed table and reads
        # non-reflexively throughout.
        # Map: docs/tk138-userset-self-relation-2026-10-14.md (corrections 2026-10-17).
        seeds: dict[tuple[str, str], set[str]] = {}
        for (t, p, r1) in schema_info.self_seeds:
            seeds.setdefault((t, p), set()).add(r1)
        self._seed_index: dict[tuple[str, str], frozenset[str]] = {
            k: frozenset(v) for k, v in seeds.items()}
        # The inverse: (type, seed) -> the declared relations p whose self tuple reaches
        # the seed. A node (T, o, seed) that reaches a target makes every T:o#p a member.
        subs: dict[tuple[str, str], set[str]] = {}
        for (t, p, r1) in schema_info.self_seeds:
            subs.setdefault((t, r1), set()).add(p)
        self._sub_index: dict[tuple[str, str], frozenset[str]] = {
            k: frozenset(v) for k, v in subs.items()}
        self._reflexive_reads = bool(seeds)
        # The processor the derived read evaluates plans through (C5): the first
        # ``DeltaProcessor`` built over this facade registers itself; otherwise one is
        # built on first need from ``SchemaInfo.compiled``.
        self._self_read_proc = None

    @property
    def processor_writes(self) -> bool:
        """Is the CALLING thread inside the delta processor's write window?

        Only the delta processor writes the edges of a derived (boolean) relation. A
        write to one from a thread outside this window is refused, and no edge is
        marked as a derived grant, so a mis-threaded caller fails loudly instead of
        quietly writing authorization state."""
        # Provenance (moved out of the docstring, TK123 item 14): I5. Read by
        # _assert_derived_exclusivity and _derived_write_ctx; both fail CLOSED.
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
                 position: str, *, create: bool) -> Node:
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

    def _w_node(self, entity_type: str, predicate: str, variant: str, *, create: bool) -> Node | None:
        """Fetch (or create) the w_any/w_all node for a shape, or None if absent.

        ⚠ **W-node resolution is deliberately UNcached across calls (blind-audit W2),
        and that rule binds every path that resolves one, not just this function.**
        Every caching scheme tried here went stale across sessions: cached misses
        pinned probes off after another session created the w node, and cached
        positive ids turned into false POSITIVES under SQLite rowid reuse (a GC'd w
        node's id claimed by an unrelated node) plus permanent false negatives after
        w-node re-creation. Resolution is one point lookup on the unique node index --
        the same cost class as the probe it feeds. The per-batch N15 `_node_cache`
        underneath `idx.node` is NOT an exception: it never survives a commit.

        This paragraph lived on a `_w_id` wrapper until 2026-08-24d, when R6-6 made
        `_check_internal` resolve the w ids in its own batch and left that wrapper
        with no callers. It moved here rather than being deleted with it -- the rule
        outlived the function, which is the usual way one of these gets lost."""
        try:
            return self.idx.node(predicate, entity_type, '*', create_if_missing=create,
                                 implicit=True, wildcard=variant)
        except KeyError:
            return None

    def _bridge_degree(self, shape: tuple[str, str]) -> int:
        return ((1 if shape in self.schema_info.bridged_in_shapes else 0)
                + (1 if shape in self.schema_info.bridged_out_shapes else 0))

    def _reject_star_self_edge(self, subject: Node, obj: Node) -> None:
        """Reject a routed edge ``w_any(T,p) -> w_all(T,p)`` on the SAME shape
        (ZT-P5-NEW, 2026-07-26).

        WHY IT IS A CYCLE. The position rule (§1.2/§1.3) splits one wildcard shape into
        two ``node`` rows -- ``w_any`` (subject position) and ``w_all`` (object
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
        # Provenance: ZT-P5, docs/spec-deviations.md 2026-07-26.
        raise AdmissionRejected(
            f"wildcard tuple rejected: the routed edge w_any{shape} -> w_all{shape} is a "
            f"cycle by construction -- the shape {shape} is both subject-wildcard bridged "
            f"(concrete -> w_any) and object-wildcard bridged (w_all -> concrete), so every "
            f"present-or-future concrete of that shape closes the loop "
            f"w_any -> w_all -> concrete -> w_any (the set engine rejects the same write as a "
            f"userset-topology cycle)")

    def _reject_latent_star_cycle(self, subject: Node, obj: Node) -> None:
        """Reject a routed edge that would create a PATH ``w_any(T,p) --> w_all(T,p)`` on
        a crossable shape (TK70, 2026-09-17) -- the length-n form of the rule
        ``_reject_star_self_edge`` states at length 1.

        THE ARGUMENT IS THE ONE ABOVE, WORD FOR WORD. The bridges of a crossable shape are
        SCHEMATIC, not data: ``_ensure_entity_middles`` gives every present **and future**
        entity ``x`` of type ``T`` the crossing middle ``(T,x,p)`` with both bridges (I14),
        so ``w_all -> (T,x,p) -> w_any`` exists the moment ANY entity of type ``T`` does.
        A path ``w_any --> w_all`` is therefore a cycle by construction whatever its
        length, and admitting one does not avoid the cycle -- it defers it onto whichever
        later write happens to mint an entity of type ``T``.

        THE DETONATION THIS CLOSES (`TK70`, family F2 of `TK69`). Without this check the
        deferral is real and measured. Three grant edges --
        ``w_any(folder,viewer) -> doc:d1#viewer``, ``doc:d1#viewer -> group:g#member``,
        ``group:g#member -> w_all(folder,viewer)`` -- are each admitted alone, and the
        next ordinary grant naming ANY folder (``user:u1 editor folder:f1``: no wildcard,
        no userset, not the crossable relation) is then permanently refused, because
        minting ``folder:f1``'s middle emits the out-bridge that closes the loop. Through
        ``Store`` that write is admission-validated by the set engine, lands in
        the permanent log, and wedges ``catch_up`` on every subsequent call. The measured
        map is docs/tk70-detonation-2026-09-17.md; the instrument is
        formal/probes/tk70_latent_cycle_sweep_2026-09-17.py.

        WHY THE GRANT EDGE ALONE IS ENOUGH TO CHECK, even though this runs BEFORE
        ``_ensure_bridges``. The only other edges a write adds are bridges, and neither
        direction can create a ``w_any --> w_all`` path unless one already exists: a new
        IN-bridge ``c -> w_any`` can only extend a path that already passes through
        ``w_any``, and a new OUT-bridge ``w_all -> c`` leaves ``w_all``, so any
        ``w_any --> w_all`` path through it must already have reached ``w_all``. Both
        presuppose the invariant broken, which the check itself prevents inductively. So
        the check belongs here, before any mutation, exactly like the one above.

        PARITY PARTNER. ``SetEngine._flow_reaches`` states the same rule from the other
        side: it steps ``w_all -> w_any`` for free on a crossable shape, so ANY path
        ``w_any --> w_all`` closes a loop there and ``_would_cycle`` refuses the write.
        One rule, two representations -- keep them in step.

        MINIMALITY. Only CROSSABLE shapes (bridged in AND out) are considered: with one
        bridge missing there is no schematic return path and the edge is harmless. A w
        node that does not exist yet ends the shape's test immediately -- no path can run
        through a row that is not there -- so this cannot refuse a write on a shape the
        store has never touched. The over-reject control for the legal reg11 /
        ``owc_star_ttu`` class is the probe's OVERREJECT arm (all 120 orderings of the
        same corpus minus its cycle-closing write: 0 refusals, before and after)."""
        crossable = self.schema_info.crossable_shapes
        if not crossable:
            return
        for (t, p) in sorted(crossable):
            w_any = self._w_node(t, p, 'any', create=False)
            if w_any is None:
                continue
            w_all = self._w_node(t, p, 'all', create=False)
            if w_all is None:
                continue
            if not (subject.id == w_any.id
                    or self.idx.check_reachable_by_id(w_any.id, subject.id)):
                continue
            if not (obj.id == w_all.id
                    or self.idx.check_reachable_by_id(obj.id, w_all.id)):
                continue
            # AdmissionRejected: a cycle refusal, same class and same rule as the
            # length-1 case above and as the set engine's userset-topology refusal.
            # Provenance: invariant I14; TK70 (the detonation),
            # docs/tk70-detonation-2026-09-17.md.
            raise AdmissionRejected(
                f"wildcard tuple rejected: this edge would complete a path "
                f"w_any{(t, p)} --> w_all{(t, p)}, which is a cycle by construction -- "
                f"the shape {(t, p)} is crossable (bridged in AND out), so the crossing "
                f"middle node of every present-or-future entity of type {t!r} closes "
                f"the loop w_any --> w_all -> middle -> w_any. Admitting it would defer "
                f"the refusal onto the next write that mints such an entity (the set engine "
                f"rejects the same write as a userset-topology cycle)")

    # ------------------------------------------------------------------ #
    # Bridge lifecycle (§7)
    # ------------------------------------------------------------------ #

    def _ensure_bridges(self, node: Node) -> None:
        """Lazily create the configured bridges for a concrete node, plus its
        entity's crossing middles (idempotent).

        The middle half maintains the I14 property (``src/zanzibar/graphindex/invariants.py``):

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

    def _ensure_own_bridges(self, node: Node) -> None:
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

    def _is_bridge_middle(self, node: Node) -> bool:
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

    def _entity_nodes(self, entity_type: str, name: str) -> list[Node]:
        return list(self.idx.session.exec(
            select(Node)
            .where(Node.store_id == self.idx.store_id)
            .where(Node.type == entity_type)
            .where(Node.name == name)
            .where(Node.wildcard == '')
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

    def _maybe_remove_bridges(self, node: Node) -> None:
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

    def _node_by_id(self, node_id: int) -> Node | None:
        return self.idx.session.exec(
            select(Node)
            .where(Node.store_id == self.idx.store_id)
            .where(Node.id == node_id)
        ).first()

    def _concrete_nodes_of_shape(self, entity_type: str, predicate: str) -> list[Node]:
        return list(self.idx.session.exec(
            select(Node)
            .where(Node.store_id == self.idx.store_id)
            .where(Node.type == entity_type)
            .where(Node.predicate == predicate)
            .where(Node.wildcard == '')
        ).all())

    def _neighbour_entities(self, node_id: int) -> set[tuple[str, str]]:
        """(type, name) of every CONCRETE direct neighbour of a node (I14: the
        entities a ``remove_node`` can orphan). Empty when no shape is crossable, so
        plain schemas pay nothing."""
        if not self.schema_info.crossable_shapes:
            return set()
        pairs = self.idx.session.exec(
            select(Edge.subject_id, Edge.object_id)
            .where(Edge.store_id == self.idx.store_id)
            .where((Edge.subject_id == node_id) | (Edge.object_id == node_id))
            .where(Edge.direct_edge_count > 0)  # type: ignore[arg-type]
        ).all()
        other_ids = {s if o == node_id else o for (s, o) in pairs} - {node_id}
        nodes = self.idx._load_nodes(other_ids)
        return {(n.type, n.name) for n in nodes.values() if n.wildcard == ''}

    def backfill(self) -> None:
        """Ensure every existing concrete of a bridged shape has its bridges, and
        every existing entity of a crossable shape's type has its crossing middles.

        Idempotent; safe to call always. Does not create a w node for a NON-crossable
        shape that has no concrete instances (avoids orphan wildcard nodes); a
        CROSSABLE shape's w nodes arrive with its middles, i.e. exactly when an
        entity of the shape's type exists."""
        # Provenance (moved out of the docstring, TK123 item 14): §7.2 + I14.
        # Serialize against live writers: the existence probes below are
        # check-then-act on ref-counted bridge edges (blind-audit C2).
        self.idx._lock_store()
        # TK3: a backfill writes bridges and middles, which emit outbox rows the
        # derived relations must see. Before the first write, fail-closed.
        _note_cascade_owed(self, 'WildcardIndex.backfill')
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
                select(Node)
                .where(Node.store_id == self.idx.store_id)
                .where(Node.type == entity_type)
                .where(Node.wildcard == '')
            ).all() if not self._is_bridge_middle(n)}
            for x in sorted(names):
                self._ensure_entity_middles(entity_type, x)

    # ------------------------------------------------------------------ #
    # Writes (§6)
    # ------------------------------------------------------------------ #

    def _derived_write_ctx(self, relation: str, o_type: str) -> bool:
        """True iff this write is the processor writing into a derived-public family
        (flags the direct edge row Edge.derived; boolean spec §4/I5)."""
        return self.processor_writes and (o_type, relation) in self.schema_info.derived_families

    def add_tuple(self, subject_predicate: str | EllipsisType, subject_type: str, subject_name: str,
                  relation: str, object_type: str, object_name: str) -> None:
        """Add one (possibly rewrite-derived) triple as a ref-counted direct edge.

        WARNING: MULTIGRAPH SEMANTICS, deliberately: adding the same triple twice counts to
        2 and takes two removes to retire. That is load-bearing for rewrite fan-in
        (two different raw tuples may derive the same edge and must retire
        independently) -- it is NOT the raw-tuple API. Zanzibar raw tuples are a SET;
        set-semantics idempotence lives one layer up, at the tuple boundary
        (``zanzibar.store.TupleSource`` / ``Store``). Do not feed raw user
        writes here directly unless you deduplicate them yourself."""
        s_type, s_name, o_type, o_name = subject_type, subject_name, object_type, object_name  # TK123 item 7
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
        ``src/zanzibar/store/apply.py``; do not widen that."""
        self._assert_derived_exclusivity(relation, o_type)
        # Lock BEFORE resolution, exactly like core.add_edge (blind-audit C2): a
        # concurrent remove_node in the resolve-then-mutate gap would hand us stale
        # ids, and the bridge existence probes below are check-then-act -- two
        # unserialized writers would double-count a ref-counted bridge edge.
        self.idx._lock_store()
        # TK3: after the pure pre-checks, before the first mutation (_resolve interns
        # nodes): from here on a boolean-schema transaction owes a cascade.
        _note_cascade_owed(self, 'add_tuple',
                           derived_write=self._derived_write_ctx(relation, o_type))
        subject = self._resolve(subject_predicate, s_type, s_name, 'subject', create=True)
        obj = self._resolve(relation, o_type, o_name, 'object', create=True)

        # ZT-P5 (2026-07-26): the position-split w_any/w_all encoding hides a same-shape
        # star self-edge from the core's cycle check. Reject it here, BEFORE any bridge
        # or grant edge is written, so the offending write never mutates closure state.
        self._reject_star_self_edge(subject, obj)
        # TK70 (2026-09-17): the same rule at length n. A multi-hop path
        # w_any(T,p) --> w_all(T,p) on a crossable shape is a cycle by construction too,
        # and admitting one defers the refusal onto the next write that mints an entity
        # of type T (the "detonation"). Also before any mutation, and for the same reason.
        self._reject_latent_star_cycle(subject, obj)

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

    def remove_tuple(self, subject_predicate: str | EllipsisType, subject_type: str, subject_name: str,
                     relation: str, object_type: str, object_name: str) -> None:
        """Remove one (possibly rewrite-derived) triple: decrement its direct-edge count.

        WARNING: MULTIGRAPH SEMANTICS, the mirror of ``add_tuple``: a triple added twice
        takes two removes to retire, and the edge (with the closure it supports) goes
        only when its count reaches 0. This is NOT the raw-tuple API; set semantics
        live one layer up, at the tuple boundary (``zanzibar.store.TupleSource`` /
        ``Store``). Removing a triple whose endpoints were never written raises
        ``AdmissionRejected``."""
        s_type, s_name, o_type, o_name = subject_type, subject_name, object_type, object_name  # TK123 item 7
        validate_write_identifiers(subject_predicate, s_type, s_name, relation, o_type, o_name)
        self._remove_tuple_trusted(subject_predicate, s_type, s_name, relation, o_type, o_name)

    def _remove_tuple_trusted(self, subject_predicate: str | EllipsisType, s_type: str,
                              s_name: str, relation: str, o_type: str, o_name: str) -> None:
        """``remove_tuple`` minus ``validate_write_identifiers`` (perf N9). Same TRUST
        CONTRACT as ``_add_tuple_trusted``: identifiers must originate from an
        admission-validated raw tuple routed through ``RuleSet.apply``; the skipped
        check provably always passes here, so accept/reject behaviour is unchanged.
        Sole sanctioned caller: ``_apply_row`` in ``src/zanzibar/store/apply.py``."""
        self._assert_derived_exclusivity(relation, o_type)
        self.idx._lock_store()   # lock before resolution (blind-audit C2)
        try:
            subject = self._resolve(subject_predicate, s_type, s_name, 'subject', create=False)
            obj = self._resolve(relation, o_type, o_name, 'object', create=False)
        except KeyError as e:
            # Same rejection family as core.remove_edge and the set engine (validity
            # parity): a remove of a never-seen endpoint is an admission rejection.
            raise AdmissionRejected('Non-existent edge cannot be removed') from e

        _note_cascade_owed(self, 'remove_tuple',   # TK3: before the first mutation
                           derived_write=self._derived_write_ctx(relation, o_type))
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
        bridges FIRST (explicit nodes keep bridges for as long
        as they exist; ``remove_node`` must strip them before the core removal).

        The ordering is not cosmetic: the core's node-removal shortcut retires edge
        ROWS by count math but does not decrement the neighbours' reference counts
        -- stripping bridges through ``remove_edge_by_id`` first keeps the w-node
        refcounts honest, so an orphaned w node can be implicit-GC'd instead of
        lingering with a stale count."""
        # Provenance (moved out of the docstring, TK123 item 14): spec sec remove_tuple.
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

        # TK80 (2026-09-20): a node RECORDED BY a residue (or one that OWNS a residue
        # row) cannot be removed through this API. `remove_node` runs no cascade, so
        # nothing prunes the recording, and the COMMITTED state is then a residue
        # vouching for a node id that no longer exists -- the ZT-P0-1 escalation class
        # (under SQLite rowid reuse the dead id can later repoint at another
        # principal). Observed pre-fix on committed state at the production paranoia
        # default (`off`):
        #     I6: residue neg holds a dead node id 8 on node id=3 doc:x#viewer
        #
        # AdmissionRejected, exactly like the `T:*` refusal above: a user-facing
        # refusal on a public admin API, NOT proven corruption (which is what an
        # `InvariantViolation` asserts). Conditional, not blanket: an UNREFERENCED
        # node is still removable and commits clean (control C3).
        #
        # ⚠ The placement is load-bearing: this must run BEFORE `_strip_bridges`
        # below, which can implicit-GC the node itself and take the early `return`.
        # A check after the strip can be reached too late. Nothing has been written
        # yet either (the store lock plus two reads), so the transaction is clean on
        # rollback -- I12 rejection cleanliness.
        if self._residue_records_node(node.id):
            raise AdmissionRejected(
                "node is recorded by a derived relation's residue and cannot be "
                "removed directly (remove the tuples that record it -- the cascade "
                "prunes the recording -- then remove the node)")

        # REFUSED SHAPE (TK113, 2026-10-03b): a node whose (type, predicate) a write-time
        # rewrite straddles -- a Computed/TTU source or target, a TTU tupleset subject or
        # TTU-produced subject, a boolean routing relation or leaf -- on ANY schema.
        # WHY: `RuleSet.apply` stored a COPY of each such tuple on another node, and this
        # method deletes one node's edges and runs no rewrite, so the copies outlive (or
        # are outlived by) their originals. PROBED: on `viewer: editor`, removing
        # `doc:x#editor` left alice/bob/carol viewers (oracle: not), and removing a target
        # made later legitimate removes refuse ("Non-existent edge"). The invariants were
        # blind to both. docs/tk113-remove-node-fence-2026-10-03.md.
        # INSTEAD: remove the node's incident TUPLES through the write path
        # (`RuleSet.apply` + `remove_tuple`, then `run_cascade` on a boolean schema).
        # Placed AFTER the TK80 guard, so a residue-recorded node keeps its own message,
        # and BEFORE `_strip_bridges` (no write has happened yet; I12 cleanliness).
        if (entity_type, pred) in self.schema_info.unremovable_node_shapes:
            raise AdmissionRejected(
                f'{entity_type}:{name}#{pred} cannot be removed directly: the schema '
                f'rewrites tuples on {entity_type}#{pred} into copies on other nodes, which '
                f'remove_node cannot reach (remove its tuples through the write path '
                f'instead -- RuleSet.apply + remove_tuple, then run_cascade)')

        # TK3: every refusal above changed nothing; from here the removal retires edges
        # (and emits outbox rows), so a boolean-schema transaction owes a cascade. Armed
        # on purpose for every admitted remove_node: the fences above prove some shapes
        # stale, not the rest exact (decision: docs/tk3-cascade-ran-mark-2026-10-22.md
        # sec 4.2).
        _note_cascade_owed(self, 'remove_node',
                           derived_write=self._derived_write_ctx(pred, entity_type))
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

    def check(self, subject_predicate: str | EllipsisType, subject_type: str, subject_name: str,
              relation: str, object_type: str, object_name: str) -> bool:
        """Is the subject related to the object by ``relation``?

        A compiled leaf name (``<relation>.<n>``) is an internal storage name, not a
        readable relation: querying one always answers False, like any undeclared
        name (reads deny rather than raise). Answering it would expose, e.g., the
        ``editor`` operand of ``viewer: editor but not banned`` without the
        ``but not`` applied."""
        # Provenance (moved out of the docstring, TK169): the BL-2 leaf-name fence; spec
        # deviations 2026-08-21b. Matches the set engine and the oracle on undeclared
        # names; writes are fenced by RuleSet.apply / SetEngine.add_tuple. Internal
        # readers that probe leaf names (_EvalContext.leaf_check / leaf_stars) enter via
        # _check_internal below the fence.
        s_type, s_name, o_type, o_name = subject_type, subject_name, object_type, object_name  # TK123 item 7
        if (o_type, relation) in self.schema_info.leaf_families:
            return False
        return self._check_internal(subject_predicate, s_type, s_name,
                                    relation, o_type, o_name)

    def _check_internal(self, subject_predicate: str | EllipsisType, s_type: str, s_name: str,
                        relation: str, o_type: str, o_name: str,
                        reflexive: bool = True) -> bool:
        """The probe below the leaf-name fence. ``reflexive`` (default) applies the
        implicit userset self-relation (TK144); the delta processor's reconcile, the
        invariants and the I9 audit pass ``False``, so the state they maintain and
        verify is the pre-TK144 canonical form."""
        s_pred = _norm_pred(subject_predicate)
        reflexive = reflexive and self._reflexive_reads

        # Derived (boolean) relations: edge probe + residue, no wildcard probes --
        # derived relations are never wildcard shapes; symbolic state lives in the
        # residue (boolean spec §6).
        if (o_type, relation) in self.schema_info.derived_families:
            return self._check_derived(s_pred, s_type, s_name, relation, o_type, o_name,
                                       reflexive=reflexive)

        subj_is_star = (s_name == '*')
        obj_is_star = (o_name == '*')

        # TK144 seeds (the untainted half of the self-relation). For a CONCRETE userset
        # subject T:o#p, the self tuple would put T:o#p into every (T, o, r1), r1 in
        # SupG(T, p) (``SchemaInfo.self_seeds``), and from there along every closure edge
        # out of those nodes. So: the query node is a seed key of the subject's own object
        # (the self hit), or one of the ordinary probes succeeds from a DECLARED seed node.
        # A seed SHAPE's ``w_any`` probe counts only when the entity T:o is witnessed:
        # the oracle reaches (T, o, r1) through a ``[T:*#r1]`` grant only by expanding the
        # grant over tuple-mentioned instances (``tests/oracle.py`` ``instances``), and
        # ``_entity_has_witness`` is that population's graph twin (I14). The subject's own
        # shape keeps its unconditional probe 2 below.
        seed_keys: list[tuple[str, str, str, str]] = []
        w_seed_keys: list[tuple[str, str, str, str]] = []
        if reflexive and s_pred != '...' and not subj_is_star:
            seeds = self._seed_index.get((s_type, s_pred))
            if seeds:
                if (o_type, o_name) == (s_type, s_name) and relation in seeds:
                    return True                                  # the self hit
                for r1 in sorted(seeds):
                    if r1 == s_pred or (s_type, r1) in self.schema_info.leaf_families:
                        continue                                 # own node / never a subject
                    seed_keys.append((r1, s_type, s_name, ''))
                    if (s_type, r1) in self.schema_info.subject_wildcard_shapes:
                        w_seed_keys.append((r1, s_type, '*', 'any'))
                if w_seed_keys and not self._entity_has_witness(s_type, s_name):
                    w_seed_keys = []

        subject_shape_declared = (s_type, s_pred) in self.schema_info.subject_wildcard_shapes
        object_shape_declared = (o_type, relation) in self.schema_info.object_wildcard_shapes

        # Resolve up to 4 node ids in ONE statement (perf R6-6): the identities are
        # independent, so they go to ``ReachabilityIndex.resolve_node_ids`` together
        # instead of paying a point SELECT each -- 4.00 node statements per check
        # became 1.00, in front of an edge probe that was already batched. A literal
        # '*' query endpoint maps to its own variant node in probe 1; a missing node
        # is simply absent from ``ids`` and drops its keys (ghosts thus retain their
        # star-probe coverage). The w-variant identities are resolved HERE, as two more
        # keys in the same batch, rather than through ``_w_node`` -- same node, same
        # per-batch cache, one fewer round trip. **W2's no-caching rule is untouched**
        # and still binds this path: ``resolve_node_ids`` holds nothing across calls,
        # reading only the N15 batch cache that ``node`` already consulted underneath
        # ``_w_node`` (see that method's docstring, which is where W2 now lives).
        subj_key = ((s_pred, s_type, '*', 'any') if subj_is_star
                    else (s_pred, s_type, s_name, ''))
        obj_key = ((relation, o_type, '*', 'all') if obj_is_star
                   else (relation, o_type, o_name, ''))
        w_any_key = ((s_pred, s_type, '*', 'any')
                     if not subj_is_star and subject_shape_declared else None)
        w_all_key = ((relation, o_type, '*', 'all')
                     if not obj_is_star and object_shape_declared else None)

        ids = self.idx.resolve_node_ids(
            [k for k in (subj_key, obj_key, w_any_key, w_all_key) if k is not None]
            + seed_keys + w_seed_keys)

        subj_id = ids.get(subj_key)
        obj_id = ids.get(obj_key)

        keys: list[tuple[int, int]] = []

        def key(a_id: int | None, b_id: int | None) -> None:
            if a_id is not None and b_id is not None:
                keys.append((a_id, b_id))

        key(subj_id, obj_id)                                             # probe 1
        w_any_id = None if w_any_key is None else ids.get(w_any_key)
        w_all_id = None if w_all_key is None else ids.get(w_all_key)
        key(w_any_id, obj_id)                                            # probe 2
        key(subj_id, w_all_id)                                           # probe 3
        key(w_any_id, w_all_id)                                          # probe 4
        for sk in seed_keys + w_seed_keys:                               # TK144 seeds
            seed_id = ids.get(sk)
            key(seed_id, obj_id)
            key(seed_id, w_all_id)

        if not keys:
            return False

        # ONE SQL round trip for all probes (boolean spec §1.14 / §6): the candidate
        # keys go into a single row-value IN with LIMIT 1.
        row = self.idx.session.exec(
            select(Edge.id)
            .where(Edge.store_id == self.idx.store_id)
            .where(tuple_(Edge.subject_id, Edge.object_id).in_(keys))
            .where(Edge.indirect_edge_count > 0)  # type: ignore[arg-type]
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
            select(Residue)
            .where(Residue.store_id == self.idx.store_id)
            .where(Residue.object_node_id == node.id)
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

    def _residue_records_node(self, node_id: int) -> bool:
        """Does any residue in this store depend on ``node_id``? (TK80 admission guard)

        True when the node OWNS a residue row (``Residue.object_node_id``) or is
        RECORDED by one (``neg | upos``, served by the ``ResidueRef`` reverse index
        under the same liveness filter the processor applies). Read-only; never interns.

        ⚠ The second clause is a deliberate MIRROR of
        ``DeltaProcessor._keys_referencing`` / ``._residue_references``
        (``src/zanzibar/graphindex/processor.py``): the indexed seek on
        ``(store_id, subject_node_id)`` plus the "the recording object node must still
        exist" filter. It is duplicated rather than imported because
        ``core -> processor -> wildcard -> core`` is a real import cycle. If
        ``_keys_referencing`` ever changes its liveness rule this must follow, which is
        why the agreement is pinned over every node of the fixture by
        ``tests/test_reg_tk80_remove_node_residue.py::test_the_guard_agrees_with_the_processor_on_every_node``.
        That pin is only as wide as its fixture, and a 2026-09-20 sweep showed the two
        clauses it cannot reach -- the LIVENESS filter (no dangling ref row exists
        there) and the ``store_id`` scoping (one store) -- so each is pinned
        separately, at the state where it is the only thing that answers, by
        ``::test_a_dangling_residue_ref_does_not_count_as_a_recording`` and
        ``::test_the_guard_is_scoped_to_its_own_store`` in the same module.

        The first clause is NOT subsumed by the second: it guards a different I6 clause
        (``residue row N references a missing node M``) and a different victim -- the
        derived-public object the residue hangs off, which is reachable through
        ``remove_node`` whenever ``processor_writes`` is on
        (``_assert_derived_exclusivity`` returns early then).
        """
        s = self.idx.session
        sid = self.idx.store_id
        if s.exec(
            select(Residue)
            .where(Residue.store_id == sid)
            .where(Residue.object_node_id == node_id)
        ).first() is not None:
            return True
        for r in s.exec(
            select(ResidueRef)
            .where(ResidueRef.store_id == sid)
            .where(ResidueRef.subject_node_id == node_id)
        ).all():
            if s.get(Node, r.object_node_id) is not None:
                return True
        return False

    def _check_derived(self, s_pred: str, s_type: str, s_name: str,
                       relation: str, o_type: str, o_name: str,
                       reflexive: bool = True) -> bool:
        if o_name == '*':
            # object wildcards on derived relations are rejected at compile (decision
            # 15): no object-star state can exist, so the intensional query is False
            return False
        if s_name == '*':
            # intensional: is the whole shape covered? (1 residue read)
            stars, _, _ = self._residue_state(relation, o_type, o_name)
            return (s_type, s_pred) in stars

        if reflexive and self._reflexive_reads and s_pred != '...':
            # TK144, challenge C5: a concrete USERSET subject on a derived relation is
            # answered at READ time -- the self hit, or the relation's plan evaluated with
            # a reflexive context (seed-aware leaf probes, reflexive derived operands).
            # The residue records the non-reflexive answer the processor maintains
            # (``reflexive=False``) and is not consulted here: the self-relation reaches
            # subjects no reconcile enumerates (challenge C1: ``group:3#admin`` has no node
            # anywhere), and it flips answers the residue holds (the ``vx`` row).
            if (s_type, s_name, s_pred) == (o_type, o_name, relation):
                return True
            return self._derived_read_eval(s_pred, s_type, s_name, relation, o_type, o_name)

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

    def _read_processor(self):
        """The ``DeltaProcessor`` the derived read evaluates plans through (TK144, C5).

        Read-only use: plan evaluation reads the closure, the residues and the stored
        tuples, and never writes. The first processor built over this facade registers
        itself here (``DeltaProcessor.__init__``); otherwise one is built from
        ``SchemaInfo.compiled``. The import is function-local only because ``processor``
        imports this module at module level; the package ``__init__`` has always loaded
        both, so this is a lookup, not an import-time dependency."""
        proc = self._self_read_proc
        if proc is None:
            compiled = self.schema_info.compiled
            if compiled is None:
                raise InvariantViolation(
                    'a derived relation was queried with a userset subject, but this graph '
                    'index has no compiled boolean plans to evaluate it with (its SchemaInfo '
                    'carries derived families without SchemaInfo.compiled)')
            from .processor import DeltaProcessor
            proc = DeltaProcessor(self, compiled)       # registers itself on this facade
        return proc

    def _derived_read_eval(self, s_pred: str, s_type: str, s_name: str,
                           relation: str, o_type: str, o_name: str) -> bool:
        """Evaluate a derived relation's plan for one userset subject at read time, with
        a REFLEXIVE ``_EvalContext`` (TK144, C5). The same plan the reconcile runs; only
        the context's reads differ (they apply the self-relation)."""
        proc = self._read_processor()
        from .processor import _EvalContext
        plan = proc.compiled.plans[(o_type, relation)]
        ctx = _EvalContext(proc, o_type, o_name, reflexive=True)
        return bool(plan.check_fn(ctx, (s_pred, s_type, s_name)))

    def _check_fenced(self, subject_predicate: str | EllipsisType, s_type: str, s_name: str,
                      relation: str, o_type: str, o_name: str, *, reflexive: bool) -> bool:
        """``check`` with the reflexive flag exposed: the leaf-name fence, then
        ``_check_internal``. The delta processor's ``member_check`` / ``member_stars``
        read DECLARED relations through here, non-reflexively during a reconcile."""
        if (o_type, relation) in self.schema_info.leaf_families:
            return False
        return self._check_internal(subject_predicate, s_type, s_name,
                                    relation, o_type, o_name, reflexive=reflexive)

    def _get_concrete(self, predicate: str, entity_type: str, name: str) -> Node | None:
        try:
            return self.idx.node(predicate, entity_type, name, create_if_missing=False)
        except KeyError:
            return None

    def filter_result(self, res: LookupResult, entity_type: str | None = None,
                      predicate: str | None = None) -> LookupResult:
        """A copy of a ``lookup`` / ``lookup_reverse`` result keeping only the entries of
        one type and/or predicate: every node id, marker, excluded id and implicit
        key whose ``(type, predicate)`` matches every filter given. From ``lookup`` the
        entries are objects (``predicate`` is the relation); from ``lookup_reverse`` they
        are subjects (``predicate`` is ``"..."`` for a bare subject such as a user, or the
        relation of a userset). Both ``None`` returns ``res`` itself. An exclusion always
        has its marker's shape, so the filtered result still reads as "keys, plus every
        subject of a marker's shape, minus the excluded keys". Read it before the next
        write: an id whose node is gone raises ``StaleLookupIds``."""
        # Provenance: TK156 (docs/tk156-lookup-filter-2026-10-19.md D1/D2). A post-filter
        # on purpose: ``lookup`` / ``lookup_reverse`` are content-pinned anchors, and
        # filtering a computed result changes no modelled algorithm.
        matches = shape_filter('filter_result', entity_type, predicate)
        if matches is None:
            return res
        nodes = self.idx._load_nodes(res.node_ids | res.excluded_node_ids)
        for field_name, ids in (('node_ids', res.node_ids),
                                ('excluded_node_ids', res.excluded_node_ids)):
            missing = sorted(i for i in ids if i not in nodes)
            if missing:
                from zanzibar.setengine.engine import StaleLookupIds
                raise StaleLookupIds(
                    field_name, missing,
                    f'they name no node in store {self.idx.store_id!r}: the lookup result '
                    f'predates a write that removed them, or it came from another store')

        def keep(ids):
            return {i for i in ids if matches(nodes[i].type, nodes[i].predicate)}
        return LookupResult(
            node_ids=keep(res.node_ids),
            markers={m for m in res.markers if matches(m[0], m[1])},
            excluded_node_ids=keep(res.excluded_node_ids),
            implicit_keys={k for k in res.implicit_keys if matches(k[0], k[2])},
            implicit_excluded_keys={k for k in res.implicit_excluded_keys
                                    if matches(k[0], k[2])})

    def lookup(self, subject_predicate: str | EllipsisType, subject_type: str, subject_name: str) -> LookupResult:
        """Everything the subject can reach. Concrete targets go in node_ids; any wildcard
        node reached becomes a symbolic marker -- never enumerated to concretes.

        Derived relations contribute twice: materialised derived
        edges arrive through the ordinary reachable set, and star-covered memberships
        come from a residue scan (shape in stars and subject not in neg)."""
        # Provenance (moved out of the docstring, TK123 item 14): spec §6; boolean spec §6.
        s_type, s_name = subject_type, subject_name  # TK123 item 7
        s_pred = _norm_pred(subject_predicate)
        result = LookupResult()

        # BL-2 symmetric guard -- a CONTRACT, not a repair: no live leak exists
        # on this side (a leaf node is never a closure SUBJECT today; the
        # 2026-08-21 probe found 0 subject-position divergences in 4,833
        # comparisons). It pins the fence's symmetry so a future write path
        # cannot open a subject-side enumeration unnoticed.
        if (s_type, s_pred) in self.schema_info.leaf_families:
            return result

        if s_name == '*':
            self._collect_reachable(self._w_node(s_type, s_pred, 'any', create=False), result)
        else:
            self._collect_reachable(self._get_concrete(s_pred, s_type, s_name), result)
            if (s_type, s_pred) in self.schema_info.subject_wildcard_shapes:
                self._collect_reachable(self._w_node(s_type, s_pred, 'any', create=False), result)

        if (self._reflexive_reads and s_pred != '...' and s_name != '*'
                and (s_type, s_pred) in self._seed_index):
            self._self_lookup(s_pred, s_type, s_name, result)
            return result
        if self.schema_info.derived_families:
            self._collect_residue_memberships(s_pred, s_type, s_name, result)
        return result

    def _self_lookup(self, s_pred: str, s_type: str, s_name: str, result: LookupResult) -> None:
        """``lookup`` for a concrete userset subject T:o#p of a declared relation, with
        OpenFGA's implicit userset self-relation (TK144). Untainted answers: the closure
        out of every declared SEED node (and of a witnessed seed shape's ``w_any``), the
        twin of the read's seed probes. Derived answers: every derived key of an entity
        the index holds a node for, decided by ``check`` -- the read path answers a
        userset subject on a derived relation by evaluating the plan, so the residue's
        stored userset memberships are not the answer (a key whose entity has no node
        evaluates the same as without the self-relation, i.e. False). The subject's own
        object is decided relation by relation. Keys with no node go to
        ``implicit_keys``."""
        seeds = self._seed_index[(s_type, s_pred)]
        witnessed = None
        for r1 in sorted(seeds):
            if r1 == s_pred or (s_type, r1) in self.schema_info.leaf_families:
                continue
            self._collect_reachable(self._get_concrete(r1, s_type, s_name), result)
            if (s_type, r1) in self.schema_info.subject_wildcard_shapes:
                if witnessed is None:
                    witnessed = self._entity_has_witness(s_type, s_name)
                if witnessed:
                    self._collect_reachable(
                        self._w_node(s_type, r1, 'any', create=False), result)
        keys: set[tuple[str, str, str]] = set()
        for (t, rel) in sorted(self._declared_keys()):
            if t == s_type and self.check(s_pred, s_type, s_name, rel, s_type, s_name):
                keys.add((s_type, s_name, rel))
        derived = self.schema_info.derived_families
        for (t, rel) in sorted(derived):
            for name in self._entity_names(t):
                if (t, name) == (s_type, s_name):
                    continue                                 # decided just above
                if self.check(s_pred, s_type, s_name, rel, t, name):
                    keys.add((t, name, rel))
        self._add_keys(result, keys)

    def _declared_keys(self) -> frozenset[tuple[str, str]]:
        """Every declared ``(type, relation)`` (the seed table names each one)."""
        return frozenset(self._seed_index)

    def _entity_names(self, entity_type: str) -> list[str]:
        """Names of the concrete entities of a type the index holds a node for."""
        rows = self.idx.session.exec(
            select(Node.name).where(Node.store_id == self.idx.store_id)   # type: ignore[arg-type]
            .where(Node.type == entity_type).where(Node.wildcard == '')
        ).all()
        return sorted({n for n in rows if n != '*'})

    def _witnessed_names(self, entity_type: str) -> list[str]:
        """Names whose entity is witnessed (``_entity_has_witness``: a node that is not a
        bridge-only middle) -- the graph twin of the oracle's ``instances``."""
        return [n for n in self._entity_names(entity_type)
                if self._entity_has_witness(entity_type, n)]

    def _add_keys(self, result: LookupResult, keys) -> None:
        """Add ``(type, name, predicate)`` answers: by node id when the node exists,
        else to ``implicit_keys``. Read-only."""
        want = [(p, t, n, '') for (t, n, p) in keys]
        ids = self.idx.resolve_node_ids(want)
        for k in want:
            nid = ids.get(k)
            if nid is not None:
                result.node_ids.add(nid)
            else:
                result.implicit_keys.add((k[1], k[2], k[0]))

    def _collect_residue_memberships(self, s_pred: str, s_type: str, s_name: str,
                                     result: LookupResult) -> None:
        shape = (s_type, s_pred)
        s_node = None if s_name == '*' else self._get_concrete(s_pred, s_type, s_name)
        concrete = s_node is not None
        rows = self.idx.session.exec(
            select(Residue).where(Residue.store_id == self.idx.store_id)
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

    def lookup_reverse(self, relation: str, object_type: str, object_name: str) -> LookupResult:
        """Everything that can reach the object. Symmetric with lookup: w_all/w_any nodes
        in the reverse set become symbolic markers (e.g. 'every T#P').

        On a derived relation: concretes are the derived edges'
        subjects; the residue's stars render as the existing symbolic markers (variant
        'any': subject-side coverage) and its neg fills ``excluded_node_ids`` so
        "everyone of shape S except these" is representable without enumeration."""
        # Provenance (moved out of the docstring, TK123 item 14): boolean spec §6.
        o_type, o_name = object_type, object_name  # TK123 item 7
        result = LookupResult()

        # BL-2 fence, mirroring check's False (and the X2 empty-not-raise
        # precedent just below): a leaf family is storage-internal, and
        # enumerating one hands out a whole operand set -- the negative leaf
        # of `viewer: editor but not banned` enumerates everyone banned.
        if (o_type, relation) in self.schema_info.leaf_families:
            return result

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
            if self._reflexive_reads:
                self._self_reverse_derived(relation, o_type, o_name, result)
            return result

        if o_name == '*':
            self._collect_reverse(self._w_node(o_type, relation, 'all', create=False), result)
        else:
            self._collect_reverse(self._get_concrete(relation, o_type, o_name), result)
            if (o_type, relation) in self.schema_info.object_wildcard_shapes:
                self._collect_reverse(self._w_node(o_type, relation, 'all', create=False), result)
        if self._reflexive_reads:
            self._add_keys(result, self._self_reverse_extra(
                relation, o_type, o_name, result.node_ids, result.markers))
        return result

    def _self_reverse_extra(self, relation: str, o_type: str, o_name: str,
                            rev_ids, markers) -> set[tuple[str, str, str]]:
        """The userset members OpenFGA's self-relation adds to an UNTAINTED
        ``(o_type, o_name, relation)`` (a leaf family included, for internal use), given
        its ordinary reverse result (TK144). Exact, no ``check`` needed: the twin of the
        read's seed probes. ``T:o#p`` is a member iff some seed ``r1`` of ``(T, p)`` has
        ``(T, o, r1)`` equal to the target or reaching it -- so every plain userset node
        ``(T, o, r1)`` of the reverse result, and the target itself, contributes
        ``T:o#p`` for every ``p`` it is a seed of; a userset ``w_any(T, r1)`` marker
        contributes it for every WITNESSED entity ``T:o`` (seed shapes ``r1 != p`` only:
        the marker already covers its own shape)."""
        out: set[tuple[str, str, str]] = set()
        targets: list[tuple[str, str, str]] = []
        if o_name != '*':
            targets.append((o_type, o_name, relation))
        for n in self.idx._load_nodes(rev_ids).values():
            if n.wildcard == '' and n.predicate != '...':
                targets.append((n.type, n.name, n.predicate))
        for (t, n, r1) in targets:
            for p in self._sub_index.get((t, r1), ()):
                out.add((t, n, p))
        for (t, r1, variant) in sorted(markers):
            if variant != 'any' or r1 == '...':
                continue
            subs = sorted(p for p in self._sub_index.get((t, r1), ()) if p != r1)
            if not subs:
                continue
            for n in self._witnessed_names(t):
                out.update((t, n, p) for p in subs)
        return out

    def _untainted_reverse_userset_keys(self, relation: str, o_type: str,
                                        o_name: str) -> set[tuple[str, str, str]]:
        """Every userset member (as a key) of an untainted ``(o_type, o_name, relation)``,
        leaf families included, under the self-relation (TK144): the ordinary reverse
        closure plus ``_self_reverse_extra``. A candidate source for the derived case."""
        tmp = LookupResult()
        self._collect_reverse(self._get_concrete(relation, o_type, o_name), tmp)
        if (o_type, relation) in self.schema_info.object_wildcard_shapes:
            self._collect_reverse(self._w_node(o_type, relation, 'all', create=False), tmp)
        out = {(n.type, n.name, n.predicate)
               for n in self.idx._load_nodes(tmp.node_ids).values()
               if n.wildcard == '' and n.predicate != '...'}
        out |= self._self_reverse_extra(relation, o_type, o_name, tmp.node_ids, tmp.markers)
        return out

    def _derived_reverse_candidates(self, relation: str, o_type: str,
                                    o_name: str) -> set[tuple[str, str, str]]:
        """A SUPERSET of the userset subjects whose membership in the derived
        ``(o_type, o_name, relation)`` the self-relation can change (TK144): the target
        itself, plus -- per plan leaf, both polarities -- every userset member of the
        operand under the self-relation (untainted operands exactly, derived ones
        recursively; strata bound the recursion). A userset whose own node no operand
        reaches answers exactly as without the self-relation, i.e. as the residue says."""
        proc = self._read_processor()
        plan = proc.compiled.plans[(o_type, relation)]
        tainted = proc.compiled.tainted
        out: set[tuple[str, str, str]] = {(o_type, o_name, relation)}
        for spec, node in zip(plan.leaves, plan.leaf_nodes):
            if spec.kind == 'closure':
                out |= self._untainted_reverse_userset_keys(spec.predicate, o_type, o_name)
            elif spec.kind == 'derived-computed':
                out |= self._derived_reverse_candidates(spec.predicate, o_type, o_name)
            elif spec.kind == 'derived-userset':
                t, p = node.subject_type, node.subject_predicate
                for xn in proc.stored_userset_subjects(o_type, o_name, spec.predicate, t, p):
                    out.add((t, xn, p))
                    out |= self._derived_reverse_candidates(p, t, xn)
            elif spec.kind == 'derived-ttu':
                target = node.target_rel
                for (pt, pn) in proc.tupleset_parents(o_type, o_name, node.tupleset_rel,
                                                      node.parent_types):
                    out.add((pt, pn, target))
                    if (pt, target) in tainted:
                        out |= self._derived_reverse_candidates(target, pt, pn)
                    elif (pt, target) in self._seed_index:
                        out |= self._untainted_reverse_userset_keys(target, pt, pn)
        return out

    def _self_reverse_derived(self, relation: str, o_type: str, o_name: str,
                              result: LookupResult) -> None:
        """Correct a derived ``lookup_reverse`` for the self-relation (TK144): every
        candidate userset subject is decided by ``check`` (which evaluates the plan) and
        moved between ``node_ids`` / ``implicit_keys`` (member) and the marker exclusions
        ``excluded_node_ids`` / ``implicit_excluded_keys`` (covered but refused)."""
        cands = self._derived_reverse_candidates(relation, o_type, o_name)
        for n in self.idx._load_nodes(result.node_ids | result.excluded_node_ids).values():
            if n.wildcard == '' and n.predicate != '...':
                cands.add((n.type, n.name, n.predicate))
        markers_any = {(t, p) for (t, p, v) in result.markers if v == 'any'}
        want = sorted(cands)
        ids = self.idx.resolve_node_ids([(p, t, n, '') for (t, n, p) in want])
        for (t, n, p) in want:
            if n == '*' or p == '...':
                continue
            member = self.check(p, t, n, relation, o_type, o_name)
            covered = (t, p) in markers_any
            nid = ids.get((p, t, n, ''))
            if nid is not None:
                if member:
                    result.excluded_node_ids.discard(nid)
                    if not covered:
                        result.node_ids.add(nid)
                else:
                    result.node_ids.discard(nid)
                    if covered:
                        result.excluded_node_ids.add(nid)
            else:
                key = (t, n, p)
                if member:
                    result.implicit_excluded_keys.discard(key)
                    if not covered:
                        result.implicit_keys.add(key)
                else:
                    result.implicit_keys.discard(key)
                    if covered:
                        result.implicit_excluded_keys.add(key)

    def _collect_reachable(self, node: Node | None, result: LookupResult) -> None:
        if node is None:
            return
        self._classify_ids(self.idx.lookup_reachable(node.id), result)

    def _collect_reverse(self, node: Node | None, result: LookupResult) -> None:
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
        leaf_families = self.schema_info.leaf_families
        for nid in node_ids:
            n = node_map.get(nid)
            if n is None:
                n = self._node_by_id(nid)
            if n is None:
                continue
            # BL-2: leaf-family nodes are storage-internal and never surface.
            # Forward lookup is the live case (the routed write puts a real
            # subject -> leaf edge in the closure, so the reachable set carried
            # the positive operand's node id -- disclosed in list-objects form
            # even for a subject the boolean guard rejects). This helper also
            # serves lookup_reverse, where the filter is a no-op today: a leaf
            # node is an edge SINK (routed writes point INTO it; the processor
            # writes derived edges subject -> derived node directly), so it
            # cannot appear in a reverse set -- kept unconditional as the same
            # contract the lookup() subject-side guard pins.
            if (n.type, n.predicate) in leaf_families:
                continue
            if n.wildcard == '':
                result.node_ids.add(nid)
            else:
                result.markers.add((n.type, n.predicate, n.wildcard))
