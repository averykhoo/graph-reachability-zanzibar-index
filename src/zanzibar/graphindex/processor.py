"""
DeltaProcessor: stratified IVM for derived (boolean) relations (boolean spec §5).

The processor consumes the closure's own outbox stream and maintains, per derived
relation, (a) materialised derived edges for concretely-supported members and (b) a
per-object ``Residue`` symbolic record ``(stars, neg)``. Deltas are invalidation
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
from contextlib import contextmanager
from typing import NamedTuple

from sqlmodel import select

from zanzibar.schema import (CompiledBooleans, DerivedFamily, LeafFamily)

from .invariants import (InvariantViolation, PARANOIA_FIXPOINT,
                         paranoia_at_least, paranoia_level)
from .models import Edge, Node, ResidueRef, Residue
from .outbox import outbox_rows
from .wildcard import WildcardIndex

SubjectKey = tuple[str, str, str]      # (predicate, type, name); predicate '...' for bare
Key = tuple[str, str, str]             # (object_type, relation, object_name)


class SettlePass(NamedTuple):
    """What ``_run_cascade``'s terminal fixpoint assertion looked at and concluded.

    ``keys`` are the derived keys still reachable from undrained outbox rows after the
    budgeted rounds; ``changed`` is the subset whose reconcile was NOT a fixpoint, which
    is the genuine-staleness signal the cascade raises on. A cascade that drained
    cleanly records None, not an empty pass. See TK73 /
    docs/tk73-cascade-quiesce-gc-2026-09-17.md."""
    keys: tuple[Key, ...]
    changed: tuple[Key, ...]


class FixpointTier(NamedTuple):
    """What the opt-in ``'fixpoint'`` paranoia tier looked at and concluded (TK82).

    ``keys`` is the cascade's SCHEDULED-key union -- every key placed in
    ``_run_cascade``'s per-round ``keys`` map, plus the terminal ``leftover`` -- and
    ``changed`` is the subset whose re-reconcile was NOT a fixpoint, i.e. the keys the
    cascade left stale. A cascade that ran with the tier OFF records None, not an empty
    pass, so a test can tell "the tier ran and found nothing" from "the tier never ran".

    ⚠ Reading this is the ONLY way to observe the tier's verdict after the fact:
    ``reconcile`` is a REPAIRING mutator, so calling it again returns False both on
    state that was already a fixpoint and on state the tier just repaired.
    See docs/tk82-cascade-fixpoint-tier-2026-09-19.md."""
    keys: tuple[Key, ...]
    changed: tuple[Key, ...]

# N3 WITHDRAWN 2026-07-26 (zero-trust review ZT-P0-1) -- DO NOT RE-INTRODUCE.
#
# ``_keys_referencing`` used to be elided on schemas whose every leaf kind was in a
# ``_RESIDUE_LOCAL_LEAF_KINDS = {'closure', 'derived-computed'}`` whitelist. The
# elision was UNSOUND and produced an authorization escalation (regression pin:
# ``tests/test_reg14_residue_gc_elision.py``).
#
# The property the GC guard needs, stated precisely -- for every leaf kind L, every
# object O, and every subject id i that reconciling a plan containing L can write into
# ``residue(O).neg`` / ``residue(O).upos``:
#
#     (P)  i's node holds a DIRECT-EDGE-justified position on O -- i.e. O's own
#          ``reference_count`` accounting keeps i's node alive independently of the
#          recording, so deleting i on ``reference_count == 0`` cannot dangle it.
#
# Only under (P) may GC skip looking for recorders, because only under (P) does
# refcount alone dominate the residue reference. The withdrawn comment justified the
# whitelist with a DIFFERENT property -- "the recording is not cross-object" -- and
# treated the two as interchangeable. They are not, and (P) is the strictly stronger
# one:
#
#   * ``closure`` VIOLATES (P). ``_leaf_concretes(kind='closure')`` resolves its
#     candidates through ``_incoming_concretes`` -> ``idx.lookup_reverse`` -- the FULL
#     TRANSITIVE CLOSURE, not the raw stored tuples the old comment claimed. A userset
#     node reachable only transitively (``group:g1#member -> group:g2#member ->
#     doc:y#a.0``) is therefore recorded on ``doc:y`` while holding no edge on it, and
#     is deleted the moment its one real edge goes.
#   * ``derived-computed`` VIOLATES (P) too, since the 2026-07-17 Fix A lift added
#     ``_ttu_target_upos_nodes`` to its branch: it now records edge-FREE userset
#     memberships lifted out of another residue. (There ``reference_count`` happens to
#     still protect the node, but that is an accident of the current leaf set, not the
#     stated reason -- so it cannot carry a GC-safety argument.)
#
# Every remaining kind (``derived-ttu`` / ``derived-userset``; ``derived-tupleset-ttu``
# too, until TK107 deleted it) records from-chain (X4a) or lifted (X4b) usersets that are
# edge-free by construction. So NO leaf kind satisfies (P): the safe residual whitelist
# is EMPTY and the mechanism had nothing left to gate. ``_keys_referencing`` now always
# scans. It was never the saving it looked like anyway -- ``_any_residue_reference``
# already runs the identical full ``Residue`` scan, with the same per-row JSON decode,
# on every node-release path on every schema (see ``_demote_released_node``).
#
# The scan DID have to get cheaper, and it got the answer this note named: an INDEX
# from subject id to recording residue (``ResidueRef``, maintained in
# ``_store_residue`` via ``_sync_residue_refs``), never a leaf-kind whitelist. Both
# lookups below are now indexed seeks and neither consults a leaf kind, so the
# whitelist mechanism stays retired. The reasoning above is kept because it is what
# forbids re-introducing it: a correct whitelist would have to re-establish (P) for
# each kind, and (P) is a property of the *candidate-resolution* code, which is free
# to widen at any time (as ``closure`` and Fix A both did) without anyone noticing
# the whitelist went stale. An index has no such coupling -- it is keyed on the ids
# actually recorded, so widening candidate resolution maintains it automatically.


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

    # BL-2: these two are the ONLY internal readers that probe the facade with a
    # LEAF PREDICATE name and legitimately expect real grants -- every compiled
    # boolean plan reads its operands through them. They must therefore enter
    # BELOW the public entry's leaf-name fence (`WildcardIndex._check_internal`,
    # not `.check`): the fenced entry answers False for every leaf family, which
    # would zero ALL boolean evaluation. `member_check` / `member_stars` below
    # only ever receive DECLARED relations and stay on the public `check`.

    def leaf_check(self, leaf_pred: str, s: SubjectKey) -> bool:
        sp, st, sn = s
        return self.proc.widx._check_internal(sp, st, sn, leaf_pred, self.object_type, self.obj_name)

    def leaf_stars(self, leaf_pred: str) -> frozenset:
        widx = self.proc.widx
        return frozenset(
            (t, p) for (t, p) in self.proc.subject_shapes
            if widx._check_internal(p, t, '*', leaf_pred, self.object_type, self.obj_name))

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
        # ONE stored-tuple enumeration for BOTH halves (perf R6-10 step A). This used
        # to call ``tupleset_star_types`` and then ``tupleset_parents`` with identical
        # arguments; each bottoms out in its own full ``_stored_tupleset_subjects``
        # pass (an Edge SELECT + a Node IN SELECT), so the pair issued 4 SQL
        # statements where 2 suffice. The star expansion stays LAZY -- the star arm
        # below returns before ``_expand_tupleset_parents`` (and therefore before
        # ``_instances_of_type``) runs, exactly as the two-call form did.
        concretes, star_types = self.proc._stored_tupleset_subjects(
            self.object_type, self.obj_name, ts, parent_types)
        # STAR-parent shape rule (RC2; oracle ttu_leaf's `pn == '*'` arm, and
        # src/zanzibar/setengine/engine.py::ttu_leaf): a stored `T:*` tupleset tuple makes EVERY
        # userset of shape (T, target) a member, whatever its name -- the ∃-expansion
        # over instances cannot express that, and folding it in is what the
        # star-expansion inside `tupleset_parents` deliberately leaves to this arm.
        for pt in star_types:
            if (st, sp) == (pt, target):
                return True
        for (pt, pn) in self.proc._expand_tupleset_parents(concretes, star_types):
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
        # one enumeration for both halves -- see ttu_check (perf R6-10 step A)
        concretes, star_types = self.proc._stored_tupleset_subjects(
            self.object_type, self.obj_name, ts, parent_types)
        # the star-parent shape itself (RC2), mirroring `ms.star((pt, target))` at
        # src/zanzibar/setengine/engine.py::ttu_expand
        out: frozenset = frozenset((pt, target) for pt in star_types)
        for (pt, pn) in self.proc._expand_tupleset_parents(concretes, star_types):
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
        # Last cascade's settle pass, or None if it drained without one (TK73). This is
        # the ONLY way to observe that the fixpoint assertion actually ran and what it
        # concluded: ``reconcile`` is a REPAIRING mutator, so a test that calls it after
        # the fact cannot distinguish "was already a fixpoint" from "was stale and I
        # just fixed it" -- the second call returns False either way. Read by
        # ``tests/test_cascade_quiesce_gc.py``.
        self._settle: SettlePass | None = None
        # TK82's opt-in per-cascade I9 tier. ``_tier_union`` is tri-state exactly like
        # the caches below: None = the tier is OFF for this cascade and the scheduling
        # sites cost one ``is not None`` test; a set = the tier is armed and collecting.
        # ``_tier`` is last cascade's verdict (None if it never ran).
        self._tier_union: set[Key] | None = None
        self._tier: FixpointTier | None = None
        # Stored-tuple enumeration memo (perf R6-10). Tri-state, exactly like
        # ``ReachabilityIndex._node_cache`` (N15) and ``WildcardIndex._residue_cache``
        # (P3): None = NO scope installed, so every read goes to SQL; a dict = a scope
        # is open and the enumerations below are memoized within it. Installed by
        # ``_stored_cache_scope``, whose docstring carries the correctness argument.
        self._stored_cache: dict | None = None
        # Non-vacuity counters for the memo, read by
        # ``benchmarks/profile_r6_write.py::target_cascade``. They exist because a
        # post-fix "0 calls" is ambiguous between "the memo worked" and "the probe
        # stopped reaching the code" (instrument correction (ii),
        # benchmarks/results/R6_PROFILE_2026-08-17.md); hits/misses disambiguate.
        # Only touched while a scope is installed -- a dict increment beside a SQL
        # round trip, and zero cost on the uncached path.
        self._stored_cache_stats = {'hits': 0, 'misses': 0, 'scopes': 0, 'keys_max': 0}

    # ------------------------------------------------------------------ #
    # Node / state accessors (read-only; never intern on reads)
    # ------------------------------------------------------------------ #

    def _node(self, predicate: str, e_type: str, name: str) -> Node | None:
        # Route concrete resolution through the shared per-batch cache (perf N15):
        # identical single point SELECT when no batch cache is installed, but during a
        # cascade the same subject/object/leaf concretes are re-resolved dozens of times
        # (leaf_check probes, residue reads, reconcile) -- this collapses them.
        return self.idx.cached_concrete_node(predicate, e_type, name)

    def _residue_row(self, object_node_id: int) -> Residue | None:
        return self.session.exec(
            select(Residue).where(Residue.store_id == self.store_id)
            .where(Residue.object_node_id == object_node_id)
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

    def _incoming_concretes(self, obj_node_id: int) -> list[Node]:
        """Concrete subject nodes reaching obj (markers excluded)."""
        ids = self.idx.lookup_reverse(obj_node_id)
        if not ids:
            return []
        nodes = self.session.exec(
            select(Node).where(Node.store_id == self.store_id)
            .where(Node.id.in_(ids))  # type: ignore[attr-defined]
        ).all()
        return [n for n in nodes if n.wildcard == '']

    def _nodes_by_ids(self, ids) -> dict[int, Node]:
        """Batch-load nodes by id in one ``IN`` query, replacing per-id
        ``session.get`` N+1 loops. Already-loaded rows come from the identity map,
        so the returned instances are identical to what ``session.get`` would hand
        back per id -- this only collapses the round trips for the cold ids."""
        want = [i for i in dict.fromkeys(ids) if i is not None]
        if not want:
            return {}
        rows = self.session.exec(
            select(Node).where(Node.store_id == self.store_id)
            .where(Node.id.in_(want))  # type: ignore[attr-defined]
        ).all()
        return {n.id: n for n in rows}

    def _direct_incoming(self, obj_node_id: int) -> list[Edge]:
        return list(self.session.exec(
            select(Edge).where(Edge.store_id == self.store_id)
            .where(Edge.object_id == obj_node_id)
            .where(Edge.direct_edge_count > 0)  # type: ignore[arg-type]
        ).all())

    def stored_userset_subjects(self, object_type: str, obj_name: str, leaf: str,
                                t: str, p: str) -> list[str]:
        """Names x of userset subjects (t, x, p) holding a stored tuple on the storage
        leaf (obj, leaf).

        Memoized inside an open ``_stored_cache_scope`` (perf R6-10) -- see that
        method's docstring for why a cascade/reconcile-scoped memo is exact."""
        cache = self._stored_cache
        key = ('us', object_type, obj_name, leaf, t, p)
        if cache is not None:
            hit = cache.get(key)
            if hit is not None:
                self._stored_cache_stats['hits'] += 1
                return list(hit)        # fresh list: callers must never see each other's
            self._stored_cache_stats['misses'] += 1
        leaf_node = self._node(leaf, object_type, obj_name)
        if leaf_node is None:
            out: list[str] = []
        else:
            edges = self._direct_incoming(leaf_node.id)
            nodes = self._nodes_by_ids(e.subject_id for e in edges)
            out = []
            for e in edges:
                n = nodes.get(e.subject_id)
                if n is not None and n.wildcard == '' and (n.type, n.predicate) == (t, p):
                    out.append(n.name)
        if cache is not None:
            cache[key] = tuple(out)     # immutable snapshot
        return out

    def _instances_of_type(self, t: str) -> list[str]:
        """Concrete instance names of a type, for the strict ∀⇒∃ expansion of a STAR
        tupleset parent (RC2). The graph twin of ``SetEngine._instances_of_type``
        (src/zanzibar/setengine/engine.py) and of the oracle's ``instances`` (tests/oracle.py):
        TUPLE-MENTIONED names only.

        The graph interns a concrete node only on a write path -- reads resolve through
        ``cached_concrete_node`` and never create -- so the interned concrete nodes of a
        type ARE its tuple-mentioned names. That is what makes this the right source and
        a query endpoint an illegal one: a ghost would "exist" because somebody asked
        about it (blind-audit O3), which is the ∀⇒∃ strictness both other backends keep.

        Rare path: only reached when a stored ``T:*`` tupleset tuple exists."""
        rows = self.session.exec(
            select(Node.name).where(Node.store_id == self.store_id)   # type: ignore[arg-type]
            .where(Node.type == t).where(Node.wildcard == '')
        ).all()
        return sorted({n for n in rows if n != '*'})

    def _stored_tupleset_subjects(self, object_type: str, obj_name: str, ts: str,
                                  parent_types: tuple) -> tuple[list, list]:
        """The stored tupleset tuples on ``(obj, ts)``, split by subject shape:
        ``(concrete parents, star parent types)``.

        The split exists because the two carry DIFFERENT semantics (oracle ``ttu_leaf``,
        tests/oracle.py): a concrete parent ``p`` contributes ``p`` alone, while a star
        parent ``T:*`` contributes (a) the SHAPE ``(T, target_rel)`` unconditionally and
        (b) an ∃-expansion over every instance of ``T``. Collapsing them -- returning
        ``(T, '*')`` as if it were a parent name -- is the naive fix that crashes:
        ``('T','*')`` is not expressible as a concrete node (core.py:913 rejects
        ``name=='*'`` with an empty ``wildcard``), so ``_from_chain_keys`` detonates in
        ``_reconcile`` and the write is reported as an admission REJECTION.

        Memoized inside an open ``_stored_cache_scope`` (perf R6-10): this was 59.8% of
        incremental boolean write time, two uncached SELECTs (``_direct_incoming`` +
        ``_nodes_by_ids``) re-issued once per candidate per leaf for arguments that are
        constant across a cascade. The memo stops at THIS level deliberately -- the
        star expansion above it stays live; see ``_stored_cache_scope`` and
        ``_expand_tupleset_parents``."""
        cache = self._stored_cache
        key = ('ts', object_type, obj_name, ts, parent_types)
        if cache is not None:
            hit = cache.get(key)
            if hit is not None:
                self._stored_cache_stats['hits'] += 1
                # fresh mutable lists off an immutable snapshot: no caller can mutate
                # another caller's result (``_expand_tupleset_parents`` copies today,
                # but do not rely on that staying true)
                return list(hit[0]), list(hit[1])
            self._stored_cache_stats['misses'] += 1
        concretes: list[tuple[str, str]] = []
        star_types: list[str] = []
        ts_node = self._node(ts, object_type, obj_name)
        if ts_node is not None:
            edges = self._direct_incoming(ts_node.id)
            nodes = self._nodes_by_ids(e.subject_id for e in edges)
            for e in edges:
                n = nodes.get(e.subject_id)
                if n is None or n.predicate != '...' or n.type not in parent_types:
                    continue
                if n.wildcard == '':
                    concretes.append((n.type, n.name))
                elif n.wildcard == 'any':  # 'all' is object-position; never a subject
                    star_types.append(n.type)
        if cache is not None:
            cache[key] = (tuple(concretes), tuple(star_types))
        return concretes, star_types

    def tupleset_parents(self, object_type: str, obj_name: str, ts: str,
                         parent_types: tuple) -> list[tuple[str, str]]:
        """Entity parents p with a stored tupleset tuple (p, ts, obj): DIRECT incoming
        entity subjects on the (obj, ts) node. Stored tuples only -- the pinned TTU
        semantics (oracle ttu_leaf); computed members of the tupleset never count.

        A stored ``T:*`` parent is EXPANDED here into the concrete instances of ``T``
        (RC2), which is what makes every downstream consumer -- ``_from_chain_keys``,
        ``_leaf_concretes``, ``_derived_leaf_neg_ids`` -- correct without edits: each
        instance really is a parent. The half the expansion cannot express, "the shape
        ``(T, target_rel)`` is a member whatever its name", is carried separately by
        ``tupleset_star_types`` and consumed by the ``_EvalContext`` TTU methods."""
        return self._expand_tupleset_parents(
            *self._stored_tupleset_subjects(object_type, obj_name, ts, parent_types))

    def _expand_tupleset_parents(self, concretes: list, star_types: list
                                 ) -> list[tuple[str, str]]:
        """The RC2 star-expansion half of ``tupleset_parents``, split out so a caller
        that already holds a ``_stored_tupleset_subjects`` result can derive the parent
        list without re-issuing the two SELECTs (perf R6-10 step A).

        ⚠ Deliberately NOT memoized, and neither is ``_instances_of_type``: the
        expansion reads the GLOBAL Node table, which legitimately changes inside one
        reconcile (``_reconcile`` step 2a interns from-chain subjects with
        ``create_if_missing=True``; step 5 ``_gc_subject_node`` deletes). Freezing it
        is a live correctness bug on RC2 star-tupleset schemas -- and no benchmark
        workload stores a ``T:*`` tupleset parent, so no profile can catch that
        mistake.

        ⚠ The net is ``tests/test_stored_cache_scope.py::
        test_star_expansion_is_not_frozen_by_the_memo`` -- and ONLY that test. It is
        tempting to name ``tests/test_ttu_tupleset_parent_types.py`` here (an earlier
        draft did), but that was falsified by sabotage: memoizing this expansion leaves
        all 12 of its tests green, and all 12 of ``tests/test_matrix.py`` too. Those
        modules pin that a star parent IS expanded, never that the expansion stays
        LIVE across a mid-reconcile intern."""
        out = list(concretes)
        for pt in star_types:
            out.extend((pt, inst) for inst in self._instances_of_type(pt))
        return list(dict.fromkeys(out))

    def tupleset_star_types(self, object_type: str, obj_name: str, ts: str,
                            parent_types: tuple) -> list[str]:
        """Types T with a stored ``T:*`` tupleset tuple on ``(obj, ts)``."""
        return self._stored_tupleset_subjects(object_type, obj_name, ts, parent_types)[1]

    def _keys_referencing(self, node_id: int) -> list[Key]:
        """Reconcile keys of every residue whose ``neg``/``upos`` records this subject
        node id -- an UNCONDITIONAL scan, on every schema.

        A recorded id is in general NOT justified by a direct edge on the recording
        object (TTU from-chain usersets and lifted userset memberships are edge-free by
        construction, lookup-gate X4/X4a/X4b; and closure leaves resolve candidates
        through the transitive closure, so they record transitively-reached subjects
        too). The recorder must therefore be findable from the id alone -- both for GC
        anchoring and for pruning when the node dies. Never gate this on the schema's
        leaf kinds; see the N3-WITHDRAWN note at the top of this module for why no
        such gate is sound.

        Served by the ``ResidueRef`` reverse index (an indexed seek on
        ``(store_id, subject_node_id)``), not by decoding every residue in the store.
        The liveness filter is retained deliberately: a reference whose recording
        object node row is gone yields no key, exactly as the scan it replaced did,
        so ``_residue_references`` keeps its meaning."""
        out: list[Key] = []
        rows = self.session.exec(
            select(ResidueRef)
            .where(ResidueRef.store_id == self.store_id)
            .where(ResidueRef.subject_node_id == node_id)
            .order_by(ResidueRef.object_node_id)      # type: ignore[arg-type]
        ).all()
        for row in rows:
            obj = self.session.get(Node, row.object_node_id)
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
            if spec.kind != 'derived-ttu':
                continue
            parents = self.tupleset_parents(object_type, obj_name,
                                            node.tupleset_rel, node.parent_types)
            for (pt, pn) in parents:
                keys[(node.target_rel, pt, pn)] = None
        return list(keys)

    def _ttu_target_upos_nodes(self, parents: list[tuple[str, str]], target: str
                               ) -> list[Node]:
        """Live userset-shaped members recorded in a tainted TTU target's residues
        (``upos``): usersets hold no edges (P4), so the dependent's enumeration must
        read them from the parents' residues, not the closure (lookup-gate X4b)."""
        out: list[Node] = []
        for (pt, pn) in parents:
            if (pt, target) not in self.compiled.tainted:
                continue
            upos_ids = self._residue_state(pt, target, pn)[2]
            nodes = self._nodes_by_ids(upos_ids)
            for nid in upos_ids:
                n = nodes.get(nid)
                if n is not None:
                    out.append(n)
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

    @contextmanager
    def _residue_cache_scope(self):
        """Install a per-reconcile residue read cache on the façade for the duration
        of one (outermost) reconcile (perf P3). Reentrant: a full-object reconcile's
        nested ``reconcile_subject`` calls share the same cache; only the outermost
        entry tears it down. Correctness rests on ``_store_residue`` invalidating the
        key it writes, so a post-write read of the object's own residue never sees the
        pre-write snapshot (see ``WildcardIndex._residue_cache``)."""
        outer = self.widx._residue_cache is None
        if outer:
            self.widx._residue_cache = {}
        try:
            yield
        finally:
            if outer:
                self.widx._residue_cache = None

    @contextmanager
    def _stored_cache_scope(self):
        """Install the stored-tuple enumeration memo for the duration of one
        (outermost) cascade or reconcile (perf R6-10).

        Reentrant, structurally identical to ``_residue_cache_scope``: outer-flag
        install, only the outermost entry tears it down. It MUST be -- ``run_cascade``
        wraps ``reconcile`` / ``reconcile_subject``, ``reconcile_subject`` escalates
        into ``_reconcile`` (the ``s_node is None`` branch), and ``_reconcile`` step 4
        nests ``_reconcile_subject`` inside itself, so a non-reentrant scope would tear
        the cache down under its own caller.

        THE CONSTANCY PREMISE (this IS the correctness argument -- read it before
        widening what the memo covers or where it is installed):

        The two memoized reads -- ``_stored_tupleset_subjects`` and
        ``stored_userset_subjects`` -- enumerate DIRECT incoming edges on STORAGE-leaf
        families, i.e. raw admitted user writes. Those cannot change inside one
        cascade:

          * raw writes PRECEDE the cascade. ``src/zanzibar/connectedstore/apply.py::advance_index``
            runs its whole ``_apply_row`` loop before ``proc.run_cascade(wm)``, and
            ``tests/test_matrix.py::GraphBackend.apply`` does the same (synchronous v1).
          * the cascade's own writes go somewhere else. ``_write_derived`` writes only
            the PUBLIC derived family (``WildcardIndex.processor_writes``), which is
            invariant I5: incoming direct edges on a derived-public family are
            processor-written exclusively, and no storage leaf is one. Derived-public
            names are declared relation names; storage-leaf predicates are
            ``<relation>.<index>`` (``.`` is reserved), and an untainted tupleset
            relation is never a derived-public name either.
          * the bridge/GC machinery cannot move either answer. ``_ensure_own_bridges``
            (the ONLY bridge-edge writer, reached from ``_ensure_bridges`` /
            ``_ensure_entity_middles``) creates exactly two edge shapes:
            ``w_all(T, p) -> concrete`` and ``concrete -> w_any(T, p)``. Neither can be
            an incoming edge that either reader accepts: the ``w_all`` subject has a
            relation name for its ``predicate``, so ``_stored_tupleset_subjects``'s
            ``n.predicate != '...'`` skip drops it and ``stored_userset_subjects``'s
            ``n.wildcard == ''`` test drops it; and the ``concrete -> w_any`` edge's
            OBJECT is a wildcard node, never a ts/leaf node. The precise claim is
            therefore: **the bridge machinery never creates an edge whose subject is a
            ``w_any`` node or a bare (``'...'``) concrete** — the ``w_any``-subject case
            because ``_ensure_own_bridges`` only ever puts a ``w_any`` in OBJECT
            position, and the bare-concrete case because
            ``SchemaInfo.bridged_in_shapes`` excludes ``(T, '...')`` outright, so a bare
            concrete never receives an out-bridge at all.
            ⚠ Do NOT weaken this to "nothing ever creates an edge out of a ``w_any``
            node" (as an earlier draft of this docstring did). That is FALSE, and
            refuted by the very function this premise justifies: the ``elif
            n.wildcard == 'any'`` arm of ``_stored_tupleset_subjects`` exists precisely
            to read edges whose subject is a ``w_any`` node — a raw ``T:*`` tupleset
            write creates one (RC2). Those come from RAW writes, which precede the
            cascade, which is why the premise still holds.
            And a node holding stored tupleset/userset edges has
            ``reference_count > 0``, so ``_gc_subject_node`` (which deletes only at 0)
            cannot remove it mid-cascade.

        ⚠ NEGATIVE results are cached too, and that needs its own argument.
        ``_stored_tupleset_subjects`` returns ``([], [])`` when ``_node(ts, ...)`` is
        None, and that node CAN be interned mid-cascade:
        ``WildcardIndex._ensure_entity_middles`` (I14 crossing middles, reached from
        ``add_tuple`` -> ``_ensure_bridges``) interns ``(p, T, x)`` for every crossable
        shape. It is benign TODAY because a freshly interned middle carries nothing but
        its own two bridges, and both bridge subjects are excluded by the filters named
        above -- so the answer is still ``([], [])``. That argument is three hops deep
        and is exactly the kind that rots: if the middle machinery ever grows an edge
        whose subject is a bare (``'...'``) concrete or a ``w_any`` node, this memo
        starts serving a stale empty answer. The pin is
        ``tests/test_stored_cache_scope.py``.

        ⚠ DO NOT install this in ``src/zanzibar/connectedstore/apply.py::advance_index``. That is
        where the N15 node cache lives and its scope SPANS the raw-write apply loop --
        a stored-tuple memo there would outlive writes that change the very edges it
        caches, which is a silent wrong-answer authorization bug, not a crash.

        ⚠ DO NOT extend the memo to ``tupleset_parents`` / ``tupleset_star_types``
        (nor to the ``derived_stored_*`` pair they had until TK107): they fan a star
        parent through ``_instances_of_type``, which reads the global Node table, and
        that table legitimately changes mid-reconcile. See
        ``_expand_tupleset_parents``."""
        outer = self._stored_cache is None
        if outer:
            self._stored_cache = {}
            self._stored_cache_stats['scopes'] += 1
        try:
            yield
        finally:
            if outer:
                stats = self._stored_cache_stats
                stats['keys_max'] = max(stats['keys_max'], len(self._stored_cache))
                self._stored_cache = None

    def reconcile_subject(self, object_type: str, rel: str, obj_name: str,
                          s: SubjectKey) -> bool:
        with self._residue_cache_scope(), self._stored_cache_scope():
            return self._reconcile_subject(object_type, rel, obj_name, s)

    def _reconcile_subject(self, object_type: str, rel: str, obj_name: str,
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
            # userset subject: recorded in upos, never as an edge (P4).
            #
            # REACHABLE from the cascade -- corrected 2026-07-26 (zero-trust review
            # ZT-P0-2). The previous comment here claimed this branch was unreachable,
            # reasoning that _map_deltas_to_keys forces userset-subject deltas on
            # 'userset-storage' leaves to a full reconcile and that 'closure' leaves can
            # never see a userset-subject flip because "their stored subjects are bare".
            # That last step is FALSE: a closure leaf's stored subjects include stored
            # USERSETS ([T#P] restrictions), so a closure-leaf delta with
            # ``s_pred != '...'`` routes straight here via the ``subject(key, ...)``
            # branch. It is exactly the path the ZT-P0-1 escalation ran down: removing
            # ``group:g1#member -> group:g2#member`` produces closure-leaf deltas whose
            # subject is the userset ``group:g1#member`` on BOTH doc:x#a.0 and
            # doc:y#a.0, and both keys take this cheap path in one cascade round.
            #
            # ``s_node is None`` (below) was the proximate leak in that bug: with the
            # node already deleted by an earlier key of the same round, the recording
            # block was skipped wholesale and the earlier key's stale id was never
            # pruned. The primary fix is upstream -- _gc_subject_node's guard now really
            # scans (N3 withdrawn), so the node cannot be deleted while this residue
            # still records it. The escalation below is the SECOND barrier: reconciling
            # by name cannot prune an id whose node is gone, so hand the key to the
            # full-object path, which recomputes neg/upos wholesale from live candidates
            # and drops dead ids by construction. Same policy _map_deltas_to_keys
            # already applies when the subject node is missing at MAP time; this covers
            # the node disappearing mid-round, after the map was built.
            if s_node is None:
                return self._reconcile(object_type, rel, obj_name)
            want_upos = should and not covered
            want_neg = covered and not should
            if want_upos != (s_node.id in upos) or want_neg != (s_node.id in neg):
                (upos.add if want_upos else upos.discard)(s_node.id)
                (neg.add if want_neg else neg.discard)(s_node.id)
                self._store_residue(object_type, rel, obj_name, stars, neg, upos)
                changed = True
                if want_upos or want_neg:
                    # promote-on-record (state-functional form; mirrors _reconcile
                    # step 2d): a recorded userset subject must be explicit, or
                    # core's implicit-GC drops it at rc-0 and dangles the residue
                    # reference. The cheap path records here too, so it must promote.
                    if s_node.wildcard == '' and s_node.implicit:
                        self.idx.node(s_node.predicate, s_node.type, s_node.name,
                                      create_if_missing=False, implicit=False)
                else:
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
        with self._residue_cache_scope(), self._stored_cache_scope():
            return self._reconcile(object_type, rel, obj_name)

    def _reconcile(self, object_type: str, rel: str, obj_name: str) -> bool:
        """Full-object reconcile (§5.3): star fold, neg recompute, residue upsert,
        edge audit. Returns True iff anything changed (I9: fixpoint ⇒ False)."""
        plan = self.compiled.plans[(object_type, rel)]
        ctx = _EvalContext(self, object_type, obj_name)

        # (1) stars: the pinned star×boolean fold, compiled into stars_fn.
        stars = plan.stars_fn(ctx)

        # (2) neg candidates: concrete members of every negative-polarity leaf ∪ neg
        #     sets of every referenced derived leaf (any kind -- exclusions propagate
        #     up through residues); then neg = star-covered ∧ expr-false.
        candidates: dict[int, Node] = {}
        for spec in plan.leaves:
            if spec.positive:
                continue
            for n in self._leaf_concretes(object_type, obj_name, spec):
                candidates[n.id] = n
        for spec in plan.leaves:
            neg_ids = self._derived_leaf_neg_ids(object_type, obj_name, spec)
            nodes = self._nodes_by_ids(neg_ids)
            for nid in neg_ids:
                n = nodes.get(nid)
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
                # A recorded from-chain subject must be NON-implicit: it survives on
                # its upos/neg residue reference alone and is collected only by
                # _gc_subject_node (step 5). Interned implicit, core's implicit-GC
                # would drop it the moment its own refcount hit 0 -- dangling the
                # residue reference and drifting the canonical form (a self-referential
                # TTU parent, where this node doubles as the target relation's own
                # node, exposed this: add-then-remove left it explicit while a fresh
                # build interned it implicit). See docs/spec-deviations.md 2026-07-13.
                # NOTE: this fresh-intern covers only from-chain subjects that have NO
                # node yet; a PRE-EXISTING recorded node (e.g. a raw-write endpoint,
                # interned implicit) is promoted uniformly by the state-functional
                # promote pass after step 2c below (2026-07-17 generalization).
                n = self.idx.node(sp, st, sn, create_if_missing=True, implicit=False)
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
        audit: dict[int, Node] = dict(candidates)
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
        upos_nodes = self._nodes_by_ids(old_upos)
        for nid in old_upos:
            n = upos_nodes.get(nid)
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

        # (2d) promote-on-record (state-functional canonical form): every USERSET-
        #      shaped node recorded in neg/upos must be EXPLICIT, uniformly -- whether
        #      reconcile freshly interned it (step 2a) or it pre-existed as a raw-write
        #      endpoint (default implicit, core.py). A recorded subject survives on its
        #      residue reference alone; interned implicit, core's implicit-GC would drop
        #      it at rc-0, dangling the reference and drifting the canonical form vs a
        #      fresh build (which path -- parent-tuple-first vs grant-first -- ran first
        #      otherwise decided the flag). Bare-entity ('...') ids are DELIBERATELY
        #      excluded: their canonical convergence rests on the implicit-GC + full-
        #      reconcile-prune dance (_map_deltas_to_keys, P4 #1), and promoting them
        #      would strand rc-0 bare nodes in neg where a fresh build has no node at
        #      all. Un-recording demotes back (_gc_subject_node / _gc_public_node). See
        #      docs/spec-deviations.md 2026-07-13 + 2026-07-17.
        for nid in (neg | upos):
            n = audit.get(nid) or candidates.get(nid)
            if n is not None and n.predicate != '...' and n.wildcard == '' and n.implicit:
                # the node provably exists (audit/candidates member) -> create_if_missing
                # =False surfaces a bug rather than masking it by creating.
                self.idx.node(n.predicate, n.type, n.name,
                              create_if_missing=False, implicit=False)   # sticky promote

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
            edges_changed |= self._reconcile_subject(
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
        n = self.session.get(Node, node_id)
        if n is None or n.store_id != self.store_id or n.wildcard != '':
            return
        if self._residue_row(n.id) is not None or self._residue_references(n.id):
            return
        entity = (n.type, n.name)
        # DEMOTE BEFORE STRIP (BL-1, docs/spec-deviations.md 2026-08-21). The node
        # survives here on an unrelated reference (e.g. a raw grant tuple, or -- the
        # leak -- its own in-bridge): its recording was just dropped, so demote it back
        # to implicit, because a fresh build interns it implicit and leaving it explicit
        # would drift the canonical form (Edit 2). This ORDER is load-bearing, not
        # incidental: ``_maybe_remove_bridges``' guard is ``implicit and
        # reference_count == degree``, and a released userset subject is still EXPLICIT
        # from the add-cascade's step-2d promotion, so stripping first was a GUARANTEED
        # no-op on exactly the path that needed it and nothing re-checked afterwards.
        # ⚠ The strip guard is NOT the thing to relax -- ``remove_node``'s "explicit
        # nodes keep bridges for as long as they exist" policy depends on it; what was
        # missing is this demote landing first, so the node is no longer explicit when
        # the strip asks. Both orders are otherwise identical: when the node is already
        # implicit the demote returns immediately, and when it stays explicit (a
        # canonical reason still holds) the strip no-ops exactly as it did before.
        if n.reference_count > 0:
            self._demote_released_node(n)
        # strip pure-bridge scaffolding (implicit GC then collects the node)
        self.widx._maybe_remove_bridges(n)
        n = self.session.get(Node, node_id)
        if n is not None and n.reference_count == 0:
            self.idx._evict_node(n)             # N15: evict before delete
            self.session.delete(n)
        # I14: whichever branch ran may have removed -- or demoted into bridge-only
        # crossing-middle state -- the entity's last real node; re-normalize its
        # crossing middles (collect them when no witness remains).
        self.widx._sync_entity_middles(*entity)

    def _has_incoming_direct_edge(self, node_id: int) -> bool:
        """Whether any DIRECT edge terminates on this node (limit-1 probe). On a
        derived-public family this means an active member -- I5 makes incoming direct
        edges there exclusively processor-written derived grants."""
        return self.session.exec(
            select(Edge).where(Edge.store_id == self.store_id)
            .where(Edge.object_id == node_id)
            .where(Edge.direct_edge_count > 0)  # type: ignore[arg-type]
        ).first() is not None

    def _any_residue_reference(self, node_id: int) -> bool:
        """Whether ANY residue's neg/upos references this node id -- an indexed
        existence probe against ``ResidueRef`` (it was a complete residue scan until
        the reverse index landed).

        Kept as a separate name from ``_residue_references`` because the two callers
        ask different QUESTIONS: ``_residue_references`` gates *deletion*, this one
        gates *demotion* (a recorded userset subject must stay EXPLICIT even when its
        own edge, not the residue, is what keeps it alive). They also differ in
        extension, and always have: this one ignores whether the RECORDING object's
        node row is still live, which is the conservative direction for a demotion
        guard. (The N3 leaf-kind elision that used to be the difference was withdrawn
        2026-07-26 as unsound -- see the module-head note.)"""
        return self.session.exec(
            select(ResidueRef)
            .where(ResidueRef.store_id == self.store_id)
            .where(ResidueRef.subject_node_id == node_id)
        ).first() is not None

    def _demote_released_node(self, n: Node) -> None:
        """Demote a surviving node back to ``implicit=True`` once its recording is
        dropped, unless a canonical explicit-reason still holds. This is a DELIBERATE,
        documented exception to core's "explicit is sticky" rule (core.py), owned by
        the processor at exactly the two lifecycle points where recordings are dropped
        (_gc_subject_node / _gc_public_node). Without it, a node recorded-then-un-
        recorded that survives on an unrelated reference stays stuck explicit while a
        fresh build interns it implicit (hysteresis drift).

        State-functional canonical form: a node is EXPLICIT iff it has its OWN residue
        row, OR is referenced by ANY residue's neg/upos (local or cross-object), OR is an
        active derived-public node with an incoming direct edge (matching _write_derived's
        / _store_residue's pinning -- a public node holding derived edges is explicit in a
        fresh build too). Self-contained (re-checks all three reasons via a COMPLETE
        residue scan), so either call site is a one-liner regardless of what it already
        established."""
        if n.implicit:
            return
        if self._residue_row(n.id) is not None:
            return
        if self._any_residue_reference(n.id):
            return
        if (n.type, n.predicate) in self.compiled.plans and self._has_incoming_direct_edge(n.id):
            return
        n.implicit = True
        self.session.add(n)

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
        raise TypeError(f'unknown leaf kind {spec.kind!r}')

    def _leaf_concretes(self, object_type: str, obj_name: str, spec) -> list[Node]:
        """Concrete members, on this object, of one plan leaf (any kind)."""
        if spec.kind == 'closure':
            # storage family: reverse concretes on the leaf node (closure includes
            # members flowing through userset nodes and processor-written derived edges)
            leaf_node = self._node(spec.predicate, object_type, obj_name)
            return [] if leaf_node is None else self._incoming_concretes(leaf_node.id)
        if spec.kind == 'derived-userset':
            # storage family: edge-justified incoming concretes on the leaf node, PLUS
            # -- for each stored userset X granted on this leaf ([T#P], P derived) --
            # the members of P(X). Those are userset-shaped memberships of a tainted
            # target: edge-free (P4), recorded only in X's residue upos, so lift them
            # here or the dependent never sees them (closes the
            # userset-subject-through-derived lookup-gate divergence, 2026-07-17;
            # analog of the X4b TTU lift below).
            leaf_node = self._node(spec.predicate, object_type, obj_name)
            out: dict[int, Node] = {}
            if leaf_node is not None:
                for n in self._incoming_concretes(leaf_node.id):
                    out[n.id] = n
            tree_node = self._find_leaf_node(spec)
            for x in self.stored_userset_subjects(object_type, obj_name, spec.predicate,
                                                  tree_node.subject_type,
                                                  tree_node.subject_predicate):
                for n in self._ttu_target_upos_nodes([(tree_node.subject_type, x)],
                                                     tree_node.subject_predicate):
                    out[n.id] = n
            return list(out.values())
        if spec.kind == 'derived-computed':
            # edge-justified incoming concretes of the aliased relation's public node,
            # PLUS its edge-free userset memberships: a Computed alias over a tainted
            # relation reads that relation's residue upos (P4), so lift it here or the
            # alias never sees userset-shaped members (closes the
            # from-chain-through-computed-alias lookup-gate divergence, 2026-07-17;
            # analog of the X4b TTU lift below).
            d_node = self._node(spec.predicate, object_type, obj_name)
            out = {}
            if d_node is not None:
                for n in self._incoming_concretes(d_node.id):
                    out[n.id] = n
            for n in self._ttu_target_upos_nodes([(object_type, obj_name)], spec.predicate):
                out[n.id] = n
            return list(out.values())
        if spec.kind == 'derived-ttu':
            node = self._find_leaf_node(spec)
            out: dict[int, Node] = {}
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
        if node is None:
            return
        # Deletable iff NOTHING remains: no edges (reference_count counts direct-edge
        # degree, and zero-degree nodes hold no closure rows), no own residue row, and
        # no residue references it as a subject (from-chain userset, X4a: deleting it
        # would dangle that id -- the recording reconcile collects it once the reference
        # is dropped).
        if (node.reference_count == 0
                and self._residue_row(node.id) is None
                and not self._residue_references(node.id)):
            entity = (node.type, node.name)
            self.idx._evict_node(node)          # N15: evict before delete
            self.session.delete(node)
            # I14: the public node may have been its entity's last real node --
            # collect the entity's crossing middles if no witness remains. (The
            # demote branch below cannot orphan the entity: the surviving public
            # node is itself a witness -- derived families are never crossable.)
            self.widx._sync_entity_middles(*entity)
            return
        # survives -> demote back to implicit unless a canonical explicit-reason still
        # holds (own residue row / residue reference / active derived-public with an
        # incoming direct edge). Edit 2: without this a public node that shed its last
        # member but survives on an unrelated reference stays stuck explicit vs a fresh
        # build's implicit intern.
        self._demote_released_node(node)

    def _store_residue(self, object_type: str, rel: str, obj_name: str,
                       stars: frozenset, neg: set[int], upos: set[int]) -> None:
        """Upsert/delete the residue row; bump version; record the bump for dependent
        invalidation. Empty residues are deleted, never stored (spec §4)."""
        # The processor may intern the public object node on the write path (spec §4);
        # non-implicit so residue-only objects (star coverage, zero edges) survive GC.
        node = self.idx.node(rel, object_type, obj_name, create_if_missing=True, implicit=False)
        # Invalidate the per-reconcile residue cache for the key being written (perf
        # P3): the object's own residue is read (via the direct ``_residue_state``
        # calls) both before and after this write within one reconcile, so a stale
        # cached snapshot must never survive the mutation.
        if self.widx._residue_cache is not None:
            self.widx._residue_cache.pop((object_type, rel, obj_name), None)
        row = self._residue_row(node.id)
        empty = not stars and not neg and not upos
        if row is None:
            if empty:
                return
            self.session.add(Residue(
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
        # Maintain the reverse index in the same statement block as the row it
        # indexes: this is the ONLY live-path writer of Residue, so it is the only
        # place the index can go stale. (The early return above is safe -- no row
        # existed and none was written, so there is nothing to index.)
        self._sync_residue_refs(node.id, set() if empty else (neg | upos))
        self._bumped.append((object_type, rel, obj_name))

    def _sync_residue_refs(self, object_node_id: int, subjects: set[int]) -> None:
        """Bring one residue's ``ResidueRef`` rows to exactly ``subjects``.

        Diffed against the rows that exist rather than delete-all-then-reinsert, so a
        reconcile that rewrites a residue without changing its recorded set costs no
        writes. Cost is O(rows for this object), never O(store).
        """
        existing = {
            r.subject_node_id: r
            for r in self.session.exec(
                select(ResidueRef)
                .where(ResidueRef.store_id == self.store_id)
                .where(ResidueRef.object_node_id == object_node_id)).all()
        }
        for sid, row in existing.items():
            if sid not in subjects:
                self.session.delete(row)
        for sid in sorted(subjects - set(existing)):
            self.session.add(ResidueRef(store_id=self.store_id,
                                          subject_node_id=sid,
                                          object_node_id=object_node_id))

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

        # P6: P2's closure expansion emits O(ancestors x descendants) outbox rows,
        # and the pre-coalescing loop redid the per-row work (a subject_node SELECT,
        # a residue scan for GC'd subjects, and the whole dependent/tupleset/target
        # fan-out) once PER ROW. Two facts let us collapse it: (1) the subject-GC
        # residue scan depends only on ``subject_node_id``; (2) all the dependent
        # fan-out (DerivedFamily ``_fan_out``, tupleset and target feeders; leaf
        # tupleset-ttu dependents too, until TK107) depends only on
        # ``(o_type, o_name, o_pred)`` -- never on the subject. Only the leaf's OWN-key full/subject decision is subject-shaped.
        # ``_map_deltas_to_keys`` mutates no node/residue state, so a per-call
        # ``session.get`` memo is exact; ``full``/``subject`` merge order-independently
        # and idempotently, so running each object's fan-out once is equivalent.
        node_by_id: dict[int, Node | None] = {}

        def get_by_id(nid: int) -> Node | None:
            if nid not in node_by_id:
                node_by_id[nid] = self.session.get(Node, nid)
            return node_by_id[nid]

        node_by_key: dict[SubjectKey, Node | None] = {}

        def get_by_key(pred: str, e_type: str, name: str) -> Node | None:
            k = (pred, e_type, name)
            if k not in node_by_key:
                node_by_key[k] = self._node(pred, e_type, name)
            return node_by_key[k]

        # (A) subject-GC residue scan, deduped by subject_node_id: the subject node
        # was GC'd in this transaction, so its recordings (from-chain / lifted userset
        # memberships, X4; transitively-reached closure-leaf concretes) are not
        # edge-justified anywhere and no other delta reaches them -- reconcile every
        # residue still holding the id, which prunes it wholesale.
        for nid in {r.subject_node_id for r in rows}:
            if get_by_id(nid) is None:
                for ref_key in self._keys_referencing(nid):
                    full(ref_key)

        processed_objects: set[tuple[str, str, str]] = set()
        for r in rows:
            # endpoints come from the row's denormalized columns: the node rows may
            # already be GC'd within this transaction, and the mapping must survive that
            o_type, o_name, o_pred = r.object_type, r.object_name, r.object_predicate
            s_name, s_pred, s_type = r.subject_name, r.subject_predicate, r.subject_type
            fam = self.compiled.namespace.get((o_type, o_pred))

            # -- subject-shaped: the leaf's own-key full/subject decision (per row) --
            if isinstance(fam, LeafFamily):
                # `raise`, not `assert`: survives `python -O` (ZT-P1-2, 2026-07-26).
                if o_name == '*':
                    raise InvariantViolation(
                        'wildcard-object delta mapped to a derived key '
                        '(decision-15 shape leaked)')
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
                elif get_by_key(s_pred, s_type, s_name) is None:
                    # subject node GC'd within this transaction: its id may linger in
                    # the residue's neg; a full reconcile recomputes neg from live
                    # candidates and prunes it (id-reuse hazard otherwise)
                    full(key)
                else:
                    subject(key, (s_pred, s_type, s_name))

            # -- object-shaped fan-out: identical for every row of this (type, name,
            #    predicate), so run it exactly once (idempotent full/subject merges) --
            obj_ident = (o_type, o_name, o_pred)
            if obj_ident in processed_objects:
                continue
            processed_objects.add(obj_ident)
            if isinstance(fam, DerivedFamily):
                self._fan_out((o_type, o_pred), o_name, keys, full)
            # a tupleset tuple appeared/vanished: the dependent on the SAME object
            for edge in self.compiled.tupleset_feeders.get((o_type, o_pred), []):
                full((edge.dependent[0], edge.dependent[1], o_name))
            for edge in self.compiled.target_feeders.get((o_type, o_pred), []):
                # delta on an (untainted) TTU target relation
                dep_t, dep_r = edge.dependent
                # 'ttu' only (a mixed-type untainted target of a PDerivedTTU): the
                # 'tupleset-ttu' kind went with TK107.
                # dependents = objects holding a tupleset tuple from this entity -- or a
                # STAR one of this entity's type, which hangs off w_any and so is
                # invisible from the entity alone (RC2). Omitting the star source is a
                # silent STALENESS bug, not a missing feature: a later delta on some
                # ``T:x`` would invalidate nothing, and the dependent would stay stale
                # until an unrelated write happened to reconcile it.
                srcs = [n for n in (self._node('...', o_type, o_name),
                                    self.widx._w_node(o_type, '...', 'any',
                                                      create=False))
                        if n is not None]
                for src in srcs:
                    for oid in self.idx.lookup_reachable(src.id):
                        o2 = self.session.get(Node, oid)
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
                    o = self.session.get(Node, oid)
                    if o is not None and (o.type, o.predicate) == (dep_t, edge.tupleset_rel):
                        full((dep_t, dep_r, o.name))
            elif edge.via == 'userset':
                # dependents = objects granted-to by this userset node's stored tuples
                us_node = self._node(source[1], source[0], obj_name)
                if us_node is None:
                    continue
                for oid in self.idx.lookup_reachable(us_node.id):
                    o = self.session.get(Node, oid)
                    if o is not None and (o.type, o.predicate) == (dep_t, edge.leaf):
                        full((dep_t, dep_r, o.name))
            else:
                raise AssertionError(f'unknown dependency via {edge.via!r}')

    def run_cascade(self, txn_start_watermark: int) -> None:
        """The in-transaction cascade (§5.1): per stratum round, map the frontier's
        deltas (plus pending residue bumps) to keys, reconcile each, advance.

        A TWO-CACHE wrapper around ``_run_cascade``; both scopes are reentrant and both
        close before the caller commits, so the paranoia checker reads true state.

        (1) The per-batch node-resolution cache (perf N15): the cascade re-resolves the
        same concrete subject/object/leaf nodes across every reconcile, leaf probe and
        residue read of a round, so one scope over the whole cascade collapses the
        ``node`` SELECTs (with negative caching for the many absent probes). Being
        reentrant, under ``advance_index`` (which installs its own outer scope) it is a
        no-op, and under a standalone ``run_cascade`` (test-matrix GraphBackend) it is
        the outermost -- exercised under paranoia either way. See
        ``ReachabilityIndex._node_cache_scope``.

        (2) The stored-tuple enumeration memo (perf R6-10), installed cascade-wide
        because the raw stored tuples it reads cannot change inside a cascade -- the
        full premise, and the two places it must NOT be installed or widened, are in
        ``_stored_cache_scope``'s own docstring. Unlike (1) this one is NOT installed
        by ``advance_index``, deliberately: that scope spans the raw-write apply loop.

        (3) TK82's opt-in ``'fixpoint'`` tier runs AFTER both scopes close, not inside
        them. That is the stronger question -- a memoized node resolution or stored-tuple
        enumeration cannot mask a divergence the check exists to see -- it is what
        docs/tk74-staleness-net-2026-09-18.md sec 10.3 actually measured (its instrument
        wrapped this public method), and one call site here covers all three of
        ``_run_cascade``'s normal exits, where a check placed inside would have to be
        repeated at each and silently skipped by the next one added. ⚠ Bound: under
        ``advance_index`` an OUTER node-cache scope spans the apply loop, so there the
        tier still runs inside *that* one; the tier closes its own scopes, not a
        caller's."""
        self._tier = None
        self._tier_union = set() if paranoia_at_least(
            paranoia_level(self.session, self.store_id), PARANOIA_FIXPOINT) else None
        with self.idx._node_cache_scope(), self._stored_cache_scope():
            self._run_cascade(txn_start_watermark)
        self._check_cascade_fixpoint()

    def _run_cascade(self, txn_start_watermark: int) -> None:
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
            self._tier_schedule(keys)

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

        # quiescence (§5.1): stratification guarantees the cascade drains the work it
        # SCHEDULES. It does not schedule reconcile-time node GC, and that is the gap
        # this pass closes (TK73, 2026-09-17).
        #
        # A reconcile's step (5) may collect a recorded-subject node
        # (``_gc_subject_node``; ``_reconcile_subject`` has its own call). That demotes
        # the node and hands it to ``WildcardIndex._maybe_remove_bridges``, whose strip
        # contracts ref-counted closure edges and EMITS outbox rows -- after this
        # round's frontier snapshot was taken, and on the last budgeted round there is
        # no further round to drain them. Those rows are honest, balanced retractions
        # (an external ``drain_deltas`` replica must see them), but they are membership-
        # NEUTRAL, so the derived key they map back to is already at its fixpoint.
        #
        # The old check tested a SYNTACTIC proxy -- "no outbox row above the final
        # frontier maps to a derived key" -- for the SEMANTIC property it wants: "no
        # derived key is stale". Late GC emission makes the two come apart. So ASK THE
        # SEMANTIC QUESTION directly: reconcile each leftover key once and require that
        # reconcile to be a FIXPOINT (the I9 property, §8.2). A key that was genuinely
        # stale reports ``changed`` and still raises; a key that is merely the shadow of
        # a neutral retraction reports False and the cascade is done.
        #
        # ⚠ The budget (``rounds``) is DELIBERATELY unchanged. ``rounds + 1`` also makes
        # this witness green -- and that is exactly why it was rejected: under a
        # sabotage that makes the leftover key GENUINELY stale, the extra round silently
        # REPAIRS it and reports success, while this pass raises. A fix that absorbs the
        # failure it is supposed to detect is an assurance step that fails by passing.
        # Evidence and the rejected alternatives: docs/tk73-cascade-quiesce-gc-2026-09-17.md.
        rows = outbox_rows(self.session, self.store_id, frontier_start)
        leftover = self._map_deltas_to_keys(rows)
        for (b_type, b_rel, b_name) in self._bumped:
            self._fan_out((b_type, b_rel), b_name,
                          leftover, lambda k: leftover.__setitem__(k, None))
        self._bumped = []
        self._settle = None
        self._tier_schedule(leftover)
        if not leftover:
            return

        settle_start = max((r.id for r in rows), default=frontier_start)
        keys = tuple(sorted(leftover))
        # Full-object reconcile even for subject-scoped leftovers: it recomputes
        # neg/upos wholesale, so it is the strictly stronger fixpoint question.
        changed = tuple(k for k in keys if self.reconcile(*k))
        self._settle = SettlePass(keys=keys, changed=changed)
        if changed:
            raise InvariantViolation(
                f'cascade failed to quiesce after {rounds} strata rounds; the settle '
                f'pass CHANGED derived state at {list(changed)} -- those keys were '
                f'genuinely stale (leftover keys: {list(keys)})')

        self.session.flush()
        tail = self._map_deltas_to_keys(
            outbox_rows(self.session, self.store_id, settle_start))
        for (b_type, b_rel, b_name) in self._bumped:
            self._fan_out((b_type, b_rel), b_name,
                          tail, lambda k: tail.__setitem__(k, None))
        self._bumped = []
        if tail:
            # Unobserved in practice: a fixpoint reconcile writes nothing, so it emits
            # nothing. Raise rather than loop -- an unbounded drain has no termination
            # argument here, because the extra pass runs a full reconcile that can
            # itself write and emit. A witness for this arm is a bug to understand.
            raise InvariantViolation(
                f'cascade failed to quiesce after {rounds} strata rounds; the settle '
                f'pass was a fixpoint at {list(keys)} but still emitted deltas mapping '
                f'to {sorted(tail)}')

    # ------------------------------------------------------------------ #
    # The opt-in per-cascade I9 tier (TK82, paranoia level 'fixpoint')
    # ------------------------------------------------------------------ #

    def _tier_schedule(self, keys) -> None:
        """Record keys the cascade has just SCHEDULED, for the fixpoint tier.

        ⚠ THE SIDE THIS READS FROM IS THE WHOLE DESIGN, and it is not observable by any
        clean-traffic measurement. On unmutated traffic the scheduled union and the
        dispatched (reconciled) set are BYTE-IDENTICAL -- ``union_minus_dispatched = 0``
        over 3,744 clean cascades (2026-09-18c) -- so the right and the wrong source cost
        the same, produce the same union and the same zero false-positive rate. Only
        fault injection separates them: the key of a SKIPPED reconcile is absent from the
        dispatched set *by construction*, because its reconcile is precisely what did not
        run, so a tier sourced from the execution side ships DEAD (measured: raises on
        0 of 43 genuinely-wrong arms, against 43 of 43 for this one).

        Called from the scheduling sites only -- after ``_map_deltas_to_keys`` plus the
        bumped fan-out in each round, and on the terminal ``leftover``. It is a named
        method rather than an inline ``update`` so the permanent sabotage
        (``tests/test_cascade_fixpoint_tier.py::test_sabotage_reconciled_union_ships_dead``)
        can re-source the union from the execution side by patching ONE symbol, which is
        the refactor this design chooses against. Do not inline it.
        """
        if self._tier_union is not None:
            self._tier_union.update(keys)

    def _check_cascade_fixpoint(self) -> None:
        """I9 over the cascade's scheduled-key union: every key the cascade scheduled
        must now re-reconcile to a fixpoint (boolean spec §8.2 I9; TK82).

        Runs only at paranoia ``'fixpoint'``; ``_tier_union is None`` otherwise, and this
        is a single test per cascade. Detects EXECUTION-side misses -- a scheduled
        reconcile that did not run, or ran wrong. A key never scheduled at all is out of
        scope by construction; ``audit_fixpoint`` is the detector for that class, at
        O(live derived keys) rather than O(cascade work).

        ⚠ Do NOT write "the tier is a subset of ``audit_fixpoint``". The per-cascade
        ratio of union size to ``audit_fixpoint`` scope EXCEEDS 1 (max 2.0 measured
        2026-09-18c): the union is scheduled from deltas, so it can hold keys whose
        object has just gone dead and left ``_live_keys_of``'s enumeration -- keys
        ``audit_fixpoint`` would never visit.

        Like the settle pass this repairs as it detects (``reconcile`` is a mutator) and
        then raises, so the caller's rollback is what restores the pre-write state.
        """
        union, self._tier_union = self._tier_union, None
        if union is None:
            return
        keys = tuple(sorted(union))
        # Full-object reconcile even for subject-scoped schedulings: it recomputes
        # neg/upos wholesale, so it is the strictly stronger fixpoint question (the
        # settle pass takes the same decision for the same reason).
        changed = tuple(k for k in keys if self.reconcile(*k))
        self._tier = FixpointTier(keys=keys, changed=changed)
        # A fixpoint reconcile writes nothing, so it bumps nothing; on the changed path
        # we raise and the transaction is dead either way. Clearing keeps a caller that
        # swallows the violation from carrying this cascade's bumps into the next one.
        self._bumped = []
        if changed:
            raise InvariantViolation(
                f'I9: the cascade left derived state STALE at {list(changed)} -- '
                f'the re-reconcile of its SCHEDULED keys was not a fixpoint '
                f'(scheduled union: {list(keys)})')

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
                select(Node).where(Node.store_id == self.store_id)
                .where(Node.type == object_type).where(Node.predicate == pred)
                .where(Node.wildcard == '')
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
                    select(Node).where(Node.store_id == self.store_id)
                    .where(Node.type == object_type)
                    .where(Node.predicate == node.tupleset_rel)
                    .where(Node.wildcard == '')
                ).all()
                names.update(n.name for n in rows)
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
