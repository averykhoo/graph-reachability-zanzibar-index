"""
Invariant checker + paranoia mode for the graph index (boolean spec §8.1/§8.2).

Numbered invariants from the boolean spec §8.2. This module carries the *state*
invariants that can be asserted from a session snapshot:

  I1  count algebra: per persisted edge row, ``indirect >= direct`` and ``indirect > 0``
      (the core's exact asserted form, core.py); no zero-reachability rows survive.
  I2  acyclicity: the direct-edge graph is a DAG.
  I3  bridge hygiene: every bridge edge is justified by a declared bridged shape and a
      live concrete node; every concrete of a bridged shape has its bridges; no bridges
      for undeclared shapes (materialization completeness + GC completeness).
  I14 crossing-middle completeness: on every crossable shape (bridged in AND out) the
      concrete middle of the w_all -> concrete -> w_any crossing exists -- with both
      bridges -- for every live ENTITY of the shape's type, not merely for entities
      that happen to intern a node of that shape (2026-08-09).
  (I4-I10 arrive with the derived-predicate state in later phases.)

I11 (read purity) and I12 (rejection cleanliness) are *differential* invariants -- they
compare two snapshots -- so they live with the harness (``snapshot_rows`` here provides
the id-independent snapshot; the ParityEngine does the comparison).

Paranoia mode (boolean spec §8.1): ``install_paranoia(session, ...)`` wires the checker
to run pre-commit *inside* the transaction (a violation raises ``InvariantViolation``
and aborts the commit) and post-commit in a *fresh* session on the same bind (catching
commit-boundary/session-state bugs). Default ON while prerelease; pass
``paranoia=False`` at the wiring site for benchmarks.

**Tiers (ZT-P1-3, 2026-07-26).** Paranoia now has three levels, because the full
checker is an O(store) per-commit cost (measured 4.8x-10x on the write path,
`benchmarks/results/BASELINE_2026-07-13.md`) and was therefore never wired into
production at all -- leaving every runtime corruption detector dark:

  ``'off'``      no listeners (the historical production behaviour).
  ``'residue'``  the CHEAP, security-relevant tier: residue hygiene only (the I6
                 family, minus its two edge-overlap clauses), scoped to the store's
                 ``ResidueV1`` rows and the node ids those rows reference --
                 O(residue rows + referenced ids), no full node or edge scan, no
                 BFS. This is the tier that owns the dangling
                 ``upos``/``neg`` id class, i.e. the ZT-P0-1 authorization
                 escalation (pin: ``tests/test_reg14_residue_gc_elision.py``).
                 Pre-commit only, so a violation ABORTS the writing transaction.
  ``'full'``     everything: ``check_invariants`` (I1/I2/I3/I13/I14 + I4-I7 + I10) plus
                 the delta-scoped BFS verifier, pre-commit AND post-commit in a
                 fresh session. O(store) per commit, plus O(pairs x edges) for the
                 verifier (`docs/perf-next-round.md`). Prerelease/test tier.

``resolve_paranoia_level`` is the shared precedence rule for wiring sites: an
explicit argument beats the ``ZANZIBAR_PARANOIA`` environment variable, which beats
the caller's default. ``ConnectedStore`` defaults to ``'off'`` because ``'residue'``
measured at +4.3%/+5.7% of the sync write path (162/478 per-write commits,
interleaved A/B, min-of-3) -- cheap next to ``'full'``'s +124%/+303%, but too much
to impose silently; see ``ConnectedStore.DEFAULT_PARANOIA``. ``'residue'`` is
nonetheless the RECOMMENDED production setting: it is the only runtime detector for
the ZT-P0-1 escalation class.
"""

from __future__ import annotations

import os
from collections import Counter
from typing import NamedTuple, TYPE_CHECKING

import json

from sqlalchemy import event
from sqlmodel import Session, select

from .models import DeltaOutboxV1, EdgeV4, NodeV4, ResidueRefV1, ResidueV1
from .outbox import outbox_rows, outbox_watermark

if TYPE_CHECKING:
    from zanzibar_utils_v1 import SchemaInfo


class InvariantViolation(AssertionError):
    """A store-state invariant does not hold. Distinct from ValueError (op rejection):
    a rejection is a *correct* refusal; a violation is corruption."""


# Allowed (subject.wildcard, object.wildcard) combinations for a DIRECT edge
# (wildcard spec §1.4):
#   ('', '')       ordinary edge
#   ('', 'any')    bridge concrete -> w_any        (same shape required)
#   ('all', '')    bridge w_all -> concrete        (same shape required)
#   ('any', '')    grant w_any -> concrete         (wildcard-subject tuple)
#   ('', 'all')    grant concrete -> w_all         (wildcard-object tuple)
#   ('any', 'all') grant w_any -> w_all            (both-wildcard tuple)
_ALLOWED_DIRECT = {('', ''), ('', 'any'), ('all', ''), ('any', ''), ('', 'all'), ('any', 'all')}


# --------------------------------------------------------------------------- #
# Paranoia levels (ZT-P1-3)
# --------------------------------------------------------------------------- #

PARANOIA_OFF = 'off'
PARANOIA_RESIDUE = 'residue'
PARANOIA_FULL = 'full'
PARANOIA_LEVELS = (PARANOIA_OFF, PARANOIA_RESIDUE, PARANOIA_FULL)
_LEVEL_RANK = {name: i for i, name in enumerate(PARANOIA_LEVELS)}

#: The environment variable an operator sets to turn the layer on (or off) without
#: a code change. Accepts a level name, or a boolean-ish word (``1``/``true``/``on``
#: => ``'full'``, ``0``/``false``/``off`` => ``'off'``).
PARANOIA_ENV_VAR = 'ZANZIBAR_PARANOIA'

_BOOLISH = {'1': PARANOIA_FULL, 'true': PARANOIA_FULL, 'yes': PARANOIA_FULL,
            'on': PARANOIA_FULL,
            '0': PARANOIA_OFF, 'false': PARANOIA_OFF, 'no': PARANOIA_OFF}


def normalize_paranoia_level(value: 'bool | str | None') -> str:
    """Coerce a user-supplied paranoia setting to one of ``PARANOIA_LEVELS``.

    ``True``/``False`` map to ``'full'``/``'off'`` so the historical boolean flag
    keeps working. Anything unrecognized is a loud ``ValueError`` -- a typo'd
    security switch must never silently mean "off"."""
    if value is True:
        return PARANOIA_FULL
    if value is False:
        return PARANOIA_OFF
    if isinstance(value, str):
        v = value.strip().lower()
        if v in _LEVEL_RANK:
            return v
        if v in _BOOLISH:
            return _BOOLISH[v]
    raise ValueError(
        f'bad paranoia level {value!r}; expected one of {PARANOIA_LEVELS} '
        f'(or a bool / {sorted(_BOOLISH)})')


def resolve_paranoia_level(explicit: 'bool | str | None' = None, *,
                           default: str = PARANOIA_OFF,
                           env: 'dict[str, str] | None' = None) -> str:
    """Precedence: explicit argument > ``ZANZIBAR_PARANOIA`` > ``default``.

    An explicit constructor argument always wins, so a caller that has made a
    deliberate choice cannot be overridden by the deployment environment. An empty
    env var is treated as unset."""
    if explicit is not None:
        return normalize_paranoia_level(explicit)
    environ = os.environ if env is None else env
    raw = environ.get(PARANOIA_ENV_VAR)
    if raw is not None and raw.strip() != '':
        return normalize_paranoia_level(raw)
    return normalize_paranoia_level(default)


def _load(session: Session, store_id: str) -> tuple[list[NodeV4], list[EdgeV4]]:
    nodes = list(session.exec(select(NodeV4).where(NodeV4.store_id == store_id)).all())
    edges = list(session.exec(select(EdgeV4).where(EdgeV4.store_id == store_id)).all())
    return nodes, edges


def _fail(msg: str) -> None:
    raise InvariantViolation(msg)


def check_invariants(session: Session, store_id: str,
                     schema_info: 'SchemaInfo | None' = None,
                     residue_versions: dict[int, int] | None = None) -> None:
    """Assert I1-I7 + I10 + I13 + I14 (+ node encoding) over the store's
    committed-or-pending rows.

    Read that list against the BODY below, not against prose elsewhere: three
    documents gave three different accounts of which invariants run per commit and
    none of them matched this function (zero-trust review 2026-07-26, P5). This
    headline was one of them -- it stopped at I6 + I10, silently dropping I7 and the
    I13 refcount/degree clause, which is the one that makes the corruption defeating
    bridge and derived-node GC visible at all. An UNDERstated checker docstring is not
    cosmetic: it is what an operator reads to decide what paranoia mode buys them.

    Unconditional: node encoding, I1 (count algebra), I2 (acyclicity of the direct-edge
    graph), I3's direct-edge variant + same-shape bridge rules, I13 (reference_count ==
    direct-edge degree), and I10 (outbox row sanity).

    ``schema_info`` gates the schema-dependent invariants: the rest of I3 (bridge
    completeness/exclusivity), I14 crossing-middle completeness, I4 namespace
    classification, I5 derived-flag exclusivity, I6 residue placement; without it
    only the schema-independent ones run. ``residue_versions`` (a mutable dict the caller keeps across checks) enables
    I7 version monotonicity.

    Not here, by design: I9 is the processor's fixpoint audit (``audit_fixpoint``) and
    I11/I12 are cross-store snapshot comparisons the test harness makes.
    """
    nodes, edges = _load(session, store_id)
    by_id = {n.id: n for n in nodes}

    # Node encoding: (name=='*') iff wildcard!='' ; wildcard is one of the enum values.
    for n in nodes:
        if n.wildcard not in ('', 'any', 'all'):
            _fail(f'bad wildcard value {n.wildcard!r} on {n}')
        if (n.name == '*') != (n.wildcard != ''):
            _fail(f'name/wildcard mismatch on {n}')

    # I1: count algebra.
    direct_edges = []
    for e in edges:
        if e.indirect_edge_count < e.direct_edge_count:
            _fail(f'I1: indirect < direct on edge {e}')
        if e.indirect_edge_count <= 0:
            _fail(f'I1: stale zero-indirect edge {e}')
        if e.direct_edge_count < 0:
            _fail(f'I1: negative direct count on edge {e}')
        if e.subject_id not in by_id or e.object_id not in by_id:
            _fail(f'I1: edge references a missing node: {e}')
        if e.direct_edge_count > 0:
            direct_edges.append(e)

    # I2: acyclicity of the direct-edge graph (iterative 3-colour DFS).
    adj: dict[int, list[int]] = {}
    for e in direct_edges:
        adj.setdefault(e.subject_id, []).append(e.object_id)
    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[int, int] = {}
    for root in adj:
        if colour.get(root, WHITE) != WHITE:
            continue
        stack: list[tuple[int, int]] = [(root, 0)]
        colour[root] = GREY
        while stack:
            node, i = stack[-1]
            succs = adj.get(node, [])
            if i < len(succs):
                stack[-1] = (node, i + 1)
                nxt = succs[i]
                c = colour.get(nxt, WHITE)
                if c == GREY:
                    _fail(f'I2: direct-edge cycle through node ids {nxt} <- {node}')
                if c == WHITE:
                    colour[nxt] = GREY
                    stack.append((nxt, 0))
            else:
                colour[node] = BLACK
                stack.pop()

    # Direct-edge variant classification + same-shape bridge rules.
    direct_edge_set = set()
    for e in direct_edges:
        s, o = by_id[e.subject_id], by_id[e.object_id]
        direct_edge_set.add((e.subject_id, e.object_id))
        combo = (s.wildcard, o.wildcard)
        if combo not in _ALLOWED_DIRECT:
            _fail(f'forbidden direct edge variant {combo}: {s} -> {o}')
        # bridge into w_any: same-shape concrete subject
        if o.wildcard == 'any':
            if not (s.wildcard == '' and (s.type, s.predicate) == (o.type, o.predicate)):
                _fail(f'I3: w_any in-edge not a same-shape concrete bridge: {s} -> {o}')
        # bridge out of w_all: same-shape concrete object
        if s.wildcard == 'all':
            if not (o.wildcard == '' and (o.type, o.predicate) == (s.type, s.predicate)):
                _fail(f'I3: w_all out-edge not a same-shape concrete bridge: {s} -> {o}')

    # I3: bridge completeness/exclusivity (needs the declared shapes).
    if schema_info is not None:
        node_by_variant = {(n.type, n.predicate, n.wildcard): n for n in nodes}
        for n in nodes:
            if n.wildcard != '':
                continue
            shape = (n.type, n.predicate)
            w_any = node_by_variant.get((n.type, n.predicate, 'any'))
            w_all = node_by_variant.get((n.type, n.predicate, 'all'))
            has_in = w_any is not None and (n.id, w_any.id) in direct_edge_set
            has_out = w_all is not None and (w_all.id, n.id) in direct_edge_set
            if shape in schema_info.bridged_in_shapes:
                if not has_in:
                    _fail(f'I3: concrete {n} of bridged-in shape missing its concrete->w_any bridge')
            elif has_in:
                _fail(f'I3: concrete {n} of non-bridged-in shape has a concrete->w_any bridge')
            if shape in schema_info.bridged_out_shapes:
                if not has_out:
                    _fail(f'I3: concrete {n} of bridged-out shape missing its w_all->concrete bridge')
            elif has_out:
                _fail(f'I3: concrete {n} of non-bridged-out shape has a w_all->concrete bridge')

    # I14 (2026-08-09): crossing-middle completeness. On a CROSSABLE shape (T, p)
    # (bridged in AND out -- SchemaInfo.crossable_shapes) the wildcard nodes compose
    # through any concrete: w_all(T,p) -> (T,x,p) -> w_any(T,p). The spec's
    # existential ("'granted on all S' implies 'reaches some S' only if at least one
    # concrete instance of S exists", wildcard spec §3.4) is ENTITY-wise --
    # tests/oracle.py::instances witnesses it with any tuple-mentioned entity of
    # type T -- so the middle must track ENTITY existence, not node existence
    # (docs/spec-deviations.md 2026-08-09):
    #
    #   for every crossable shape (T, p) and every entity name x such that the store
    #   holds at least one node (T, x, *) that is not itself a bridge-only middle,
    #   the store holds the node (T, x, p) with BOTH of its bridges.
    #
    # I3 above says a concrete of a bridged shape must HAVE its bridges; I14 says the
    # middle must EXIST while the entity does. A "bridge-only middle" is implicit, of
    # a crossable shape, and carries nothing but its two bridges (under I3, degree 2
    # == exactly the bridges); such nodes witness nothing, or the middles would keep
    # each other alive forever. Maintained by WildcardIndex._ensure_entity_middles /
    # _sync_entity_middles; sabotage-verified (tests/test_i14_crossing_middles.py).
    if schema_info is not None:
        crossable = schema_info.crossable_shapes
        if crossable:
            concrete_by_key = {(n.type, n.name, n.predicate): n
                               for n in nodes if n.wildcard == ''}
            wildcard_by_variant = {(n.type, n.predicate, n.wildcard): n
                                   for n in nodes if n.wildcard != ''}

            def _is_bridge_middle(n: NodeV4) -> bool:
                return (n.implicit and (n.type, n.predicate) in crossable
                        and n.reference_count == 2)

            witnessed = {(n.type, n.name) for n in concrete_by_key.values()
                         if not _is_bridge_middle(n)}
            for (t, x) in sorted(witnessed):
                for (ct, p) in sorted(crossable):
                    if ct != t:
                        continue
                    mid = concrete_by_key.get((t, x, p))
                    if mid is None:
                        _fail(f'I14: entity {t}:{x} exists but its crossing middle '
                              f'{t}:{x}#{p} for crossable shape {(t, p)} is missing')
                    w_any = wildcard_by_variant.get((t, p, 'any'))
                    w_all = wildcard_by_variant.get((t, p, 'all'))
                    if w_any is None or (mid.id, w_any.id) not in direct_edge_set:
                        _fail(f'I14: crossing middle {mid} is missing its '
                              f'concrete->w_any bridge')
                    if w_all is None or (w_all.id, mid.id) not in direct_edge_set:
                        _fail(f'I14: crossing middle {mid} is missing its '
                              f'w_all->concrete bridge')

    # I13 (blind-audit C5): reference_count is exactly the node's direct-edge degree
    # (each direct edge increments both endpoints on add and decrements on remove).
    # This is what makes remove_node-style refcount corruption -- which silently
    # defeats bridge GC and derived-node GC -- visible to paranoia instead of latent.
    # Runs AFTER the bridge checks: a missing/extra bridge edge also skews degree,
    # and I3 is the more specific diagnosis for that corruption.
    degree: dict[int, int] = {}
    for e in edges:
        if e.direct_edge_count > 0:
            degree[e.subject_id] = degree.get(e.subject_id, 0) + e.direct_edge_count
            degree[e.object_id] = degree.get(e.object_id, 0) + e.direct_edge_count
    for n in nodes:
        if n.reference_count != degree.get(n.id, 0):
            _fail(f'I13: reference_count {n.reference_count} != direct-edge degree '
                  f'{degree.get(n.id, 0)} on {n}')

    if schema_info is not None:
        _check_derived_invariants(session, store_id, schema_info, nodes, edges, by_id,
                                  residue_versions)

    _check_outbox_sanity(session, store_id)


def _check_derived_invariants(session: Session, store_id: str, schema_info,
                              nodes, edges, by_id, residue_versions) -> None:
    """I4 namespace classification, I5 derived-flag exclusivity, I6 residue placement,
    I7 residue-version monotonicity (boolean spec §8.2)."""
    leaf_families = schema_info.leaf_families
    derived_families = schema_info.derived_families

    # I4: every '.'-predicate node family must be a declared leaf family; leaf and
    # derived families never appear as w_all shapes (decision 15 rejected those).
    for n in nodes:
        key = (n.type, n.predicate)
        if '.' in n.predicate and n.predicate != '...' and key not in leaf_families:
            _fail(f'I4: node {n} uses a leaf-style predicate outside the compiled namespace')
        if n.wildcard == 'all' and (key in leaf_families or key in derived_families):
            _fail(f'I4: w_all node on a leaf/derived family: {n}')

    # I5: derived=True iff a direct edge into a derived-public family; nowhere else.
    for e in edges:
        o = by_id.get(e.object_id)
        if o is None:
            continue
        on_derived = (o.type, o.predicate) in derived_families and o.wildcard == ''
        if e.direct_edge_count > 0 and on_derived:
            if not e.derived:
                _fail(f'I5: direct edge into derived family lacks the derived flag: {e}')
        elif e.derived:
            _fail(f'I5: derived flag on a non-derived-direct edge row: {e}')

    # I6 / I7: residue placement + version monotonicity.
    rows = session.exec(
        select(ResidueV1).where(ResidueV1.store_id == store_id)).all()
    derived_edge_subjects: dict[int, set[int]] = {}
    for e in edges:
        if e.direct_edge_count > 0 and e.derived:
            derived_edge_subjects.setdefault(e.object_id, set()).add(e.subject_id)

    _check_residue_rows(rows, by_id.get,
                        derived_families=derived_families,
                        subject_shapes=schema_info.subject_wildcard_shapes,
                        derived_edge_subjects=derived_edge_subjects,
                        residue_refs=_load_residue_refs(session, store_id),
                        residue_versions=residue_versions)


def _load_residue_refs(session: Session, store_id: str) -> dict[int, set[int]]:
    """The ``ResidueRefV1`` reverse index as ``object_node_id -> {subject_node_id}``.

    A COLUMN select, not an entity select: this runs inside every commit under the
    cheap ``residue`` tier, where ORM instance bookkeeping is the bulk of the cost.
    """
    out: dict[int, set[int]] = {}
    for object_node_id, subject_node_id in session.exec(
            select(ResidueRefV1.object_node_id, ResidueRefV1.subject_node_id)
            .where(ResidueRefV1.store_id == store_id)).all():
        out.setdefault(object_node_id, set()).add(subject_node_id)
    return out


def _check_residue_rows(rows, node_of, *,
                        derived_families=None, subject_shapes=None,
                        derived_edge_subjects: 'dict[int, set[int]] | None' = None,
                        residue_refs: 'dict[int, set[int]] | None' = None,
                        residue_versions: 'dict | None' = None) -> None:
    """I6 residue placement (+ I7 monotonicity when ``residue_versions`` is given).

    Shared by the full checker and by the cheap ``residue`` paranoia tier, so the two
    can never drift. ``node_of`` resolves a node id to its ``NodeV4`` (or None -- a
    dangling reference, which is the ZT-P0-1 corruption class).
    ``derived_edge_subjects`` is the per-object set of subjects holding a derived
    direct edge; ``None`` means "not computed" and SKIPS the two edge-overlap clauses
    (they need a full edge scan, which is exactly what the cheap tier refuses to pay).
    ``derived_families``/``subject_shapes`` of ``None`` skip the schema-dependent
    clauses.

    ``residue_refs`` is the ``ResidueRefV1`` reverse index as
    ``object_node_id -> {subject_node_id}``; ``None`` skips the agreement clause.
    That clause is what keeps the index from becoming an unchecked second source of
    truth: this function decodes ``neg``/``upos`` STRAIGHT FROM THE JSON and never
    consults ``processor.py``, so comparing the two here is an independent check
    rather than the index agreeing with itself (docs/sabotage-procedure.md, "the
    mirror instrument"). A stale index is not a cosmetic drift -- it is read by the
    node-release guards, so a missing row re-opens the ZT-P0-1 escalation class.
    """
    seen_ref_objects: set[int] = set()
    for r in rows:
        node = node_of(r.object_node_id)
        if node is None:
            _fail(f'I6: residue row {r.id} references a missing node {r.object_node_id}')
        if derived_families is not None and (node.type, node.predicate) not in derived_families:
            _fail(f'I6: residue on a non-derived relation: {node}')
        if r.relation != node.predicate:
            _fail(f'I6: residue.relation {r.relation!r} disagrees with its node {node}')
        stars = frozenset(tuple(s) for s in json.loads(r.stars))
        neg = set(json.loads(r.neg))
        upos = set(json.loads(r.upos))
        if not stars and not neg and not upos:
            _fail(f'I6: empty residue row persisted for {node}')
        if subject_shapes is not None and not stars <= subject_shapes:
            _fail(f'I6: residue stars {stars} outside declared subject shapes on {node}')
        edge_holders = (set() if derived_edge_subjects is None
                        else derived_edge_subjects.get(r.object_node_id, set()))
        for nid in neg:
            s = node_of(nid)
            if s is None:
                _fail(f'I6: residue neg holds a dead node id {nid} on {node}')
            if s.wildcard != '':
                _fail(f'I6: residue neg holds a wildcard node {s} on {node}')
            if (s.type, s.predicate) not in stars:
                _fail(f'I6: neg subject {s} not star-covered by {stars} on {node}')
            # state-functional canonical form (2026-07-17): a USERSET-shaped recorded
            # subject survives on its residue reference alone, so it must be EXPLICIT
            # (an implicit one would be dropped by core's implicit-GC at rc-0, dangling
            # the reference). Bare-entity neg ids stay implicit-eligible (excluded).
            if s.predicate != '...' and s.implicit:
                _fail(f'I6: userset neg subject {s} is implicit on {node} '
                      f'(recorded subjects must be explicit -- state-functional form)')
        if neg & edge_holders:
            _fail(f'I6: neg overlaps derived-edge holders on {node} '
                  f'(an edge means expr-true; neg means expr-false)')
        # upos (blind-audit P4): edge-free TRUE memberships of userset-shaped
        # subjects. Must hold live, concrete, userset-predicate nodes; disjoint from
        # neg (true vs false); never star-covered (covered ⇒ answered by stars/neg);
        # and never edge-holders (upos exists precisely so usersets get no edges).
        if upos & neg:
            _fail(f'I6: upos overlaps neg on {node}')
        if upos & edge_holders:
            _fail(f'I6: upos overlaps derived-edge holders on {node} '
                  f'(userset memberships must be edge-free)')
        for nid in upos:
            s = node_of(nid)
            if s is None:
                _fail(f'I6: residue upos holds a dead node id {nid} on {node}')
            if s.wildcard != '' or s.predicate == '...':
                _fail(f'I6: residue upos holds a non-userset node {s} on {node}')
            if (s.type, s.predicate) in stars:
                _fail(f'I6: upos subject {s} is star-covered by {stars} on {node} '
                      f'(covered subjects are answered by stars/neg, not upos)')
            # state-functional canonical form (2026-07-17): every upos subject is
            # userset-shaped and survives on its residue reference alone -> EXPLICIT.
            if s.implicit:
                _fail(f'I6: upos subject {s} is implicit on {node} '
                      f'(recorded subjects must be explicit -- state-functional form)')
        # I6: the ResidueRefV1 reverse index agrees with this row, exactly and in both
        # directions. Under-coverage is the dangerous side (a node-release guard then
        # believes nothing references the node and deletes/demotes it -- ZT-P0-1), but
        # over-coverage is checked too: a stale row pins a node alive forever and
        # silently drifts the state-functional canonical form.
        if residue_refs is not None:
            seen_ref_objects.add(r.object_node_id)
            indexed = residue_refs.get(r.object_node_id, set())
            if indexed != (neg | upos):
                _fail(f'I6: residue_ref index disagrees with neg|upos on {node}: '
                      f'indexed={sorted(indexed)} recorded={sorted(neg | upos)}')

    # I6: no reverse-index row survives its residue. `_store_residue` deletes an
    # emptied residue row, so its index rows must go with it; an orphan here means the
    # index outlived the only thing that justifies it.
    if residue_refs is not None:
        for object_node_id in sorted(set(residue_refs) - seen_ref_objects):
            _fail(f'I6: residue_ref rows for object {object_node_id} '
                  f'(subjects {sorted(residue_refs[object_node_id])}) '
                  f'have no residue row')

    # I7: version monotonicity per residue ROW (empty rows are deleted, so a
    # recreated residue legitimately restarts its lineage at version 1 -- lineage is
    # keyed by (row id, object) and pruned when the row disappears). A row observed
    # at version 1 is ALWAYS treated as a fresh lineage: SQLite may reuse a just-
    # deleted max rowid for a same-object recreate within one transaction, and
    # without this allowance that legitimate recreate would FALSELY trip I7 (the
    # residual blind spot is an in-place regression to exactly 1, accepted).
    if residue_versions is not None:
        seen = set()
        for r in rows:
            k = (r.id, r.object_node_id)
            seen.add(k)
            last = residue_versions.get(k)
            if last is not None and r.version < last and r.version != 1:
                _fail(f'I7: residue version regressed on row {r.id} '
                      f'(object {r.object_node_id}): {last} -> {r.version}')
            residue_versions[k] = r.version
        for k in list(residue_versions):
            if k not in seen:
                del residue_versions[k]


class _NodeFacts(NamedTuple):
    """The node columns the residue clauses read, without the ORM instance."""
    id: int
    type: str
    name: str
    predicate: str
    wildcard: str
    implicit: bool

    def __str__(self) -> str:                            # for violation messages
        w = f' wildcard={self.wildcard!r}' if self.wildcard else ''
        return (f'node id={self.id} {self.type}:{self.name}#{self.predicate}'
                f'{w} implicit={self.implicit}')


class _ResidueFacts(NamedTuple):
    """Ditto for ``ResidueV1``. ``version`` is absent: I7 is a full-tier clause."""
    id: int
    object_node_id: int
    relation: str
    stars: str
    neg: str
    upos: str


def check_residue_hygiene(session: Session, store_id: str,
                          schema_info: 'SchemaInfo | None' = None) -> None:
    """The CHEAP paranoia tier (ZT-P1-3): the I6 residue-hygiene family alone.

    Every clause of I6 except the two that need a full edge scan
    (``neg``/``upos`` overlapping derived-edge holders) -- in particular the
    **dead node id** clauses, which are the runtime detector for the ZT-P0-1
    residue-GC escalation (a residue vouching for a recycled rowid).

    Cost: one indexed ``ResidueV1`` scan for the store, plus one batched
    ``NodeV4 WHERE id IN (...)`` fetch of exactly the ids those rows name --
    O(residue rows + referenced ids). No node scan, no edge scan, no BFS, so it
    does NOT grow with store size the way ``check_invariants`` does.

    I7 (version monotonicity) is deliberately excluded: it needs a baseline carried
    across commits, it is not security-relevant, and the cheap tier runs pre-commit
    only (where a rolled-back bump would poison that baseline).
    """
    # COLUMN selects, not entity selects, on both queries: this runs inside every
    # commit, and materializing ORM instances (identity-map bookkeeping, instance
    # state) measured as the bulk of the tier's cost. The lightweight records below
    # duck-type the attributes the shared clause code reads.
    rows = [_ResidueFacts(*t) for t in session.exec(
        select(ResidueV1.id, ResidueV1.object_node_id, ResidueV1.relation,
               ResidueV1.stars, ResidueV1.neg, ResidueV1.upos)
        .where(ResidueV1.store_id == store_id)).all()]
    refs = _load_residue_refs(session, store_id)
    if not rows:
        # The orphan clause is still owed here, and this is exactly where it matters:
        # "residue rows all gone, index rows left behind" is the state a broken delete
        # produces, and returning early on `not rows` would make the tier blind to the
        # one case it is most likely to be the only witness for.
        _check_residue_rows((), {}.get, residue_refs=refs)
        return

    wanted: set[int] = set()
    for r in rows:
        wanted.add(r.object_node_id)
        wanted.update(json.loads(r.neg))
        wanted.update(json.loads(r.upos))

    by_id: dict[int, _NodeFacts] = {}
    ids = sorted(wanted)
    # Chunked: SQLite's default bound-parameter limit is 999.
    for i in range(0, len(ids), 400):
        chunk = ids[i:i + 400]
        for t in session.exec(
                select(NodeV4.id, NodeV4.type, NodeV4.name, NodeV4.predicate,
                       NodeV4.wildcard, NodeV4.implicit)
                .where(NodeV4.store_id == store_id)
                .where(NodeV4.id.in_(chunk))).all():
            by_id[t[0]] = _NodeFacts(*t)

    _check_residue_rows(
        rows, by_id.get,
        derived_families=None if schema_info is None else schema_info.derived_families,
        subject_shapes=(None if schema_info is None
                        else schema_info.subject_wildcard_shapes),
        derived_edge_subjects=None,       # skipped: needs a full edge scan
        residue_refs=refs,                # cheap (one indexed select) and ZT-P0-1-relevant
        residue_versions=None)


def _check_outbox_sanity(session: Session, store_id: str) -> None:
    """I10: outbox rows well-formed (the watermark bookkeeping lives with paranoia)."""
    rows = session.exec(
        select(DeltaOutboxV1).where(DeltaOutboxV1.store_id == store_id)).all()
    for r in rows:
        if r.action not in ('ADDED', 'REMOVED'):
            _fail(f'I10: malformed outbox action {r.action!r} (row {r.id})')
        if not r.object_type or not r.object_predicate or not r.subject_type:
            _fail(f'I10: outbox row {r.id} missing denormalized endpoints')


def snapshot_rows(session: Session, store_id: str) -> tuple[Counter, Counter]:
    """Id-independent (node_rows, edge_rows) multisets, for I11/I12 comparisons: two
    stores that reach the same logical state compare equal regardless of row ids."""
    nodes, edges = _load(session, store_id)
    by_id = {n.id: (n.predicate, n.type, n.name, n.wildcard) for n in nodes}
    node_rows = Counter(
        (n.predicate, n.type, n.name, n.wildcard, n.implicit, n.reference_count) for n in nodes
    )
    edge_rows = Counter(
        (by_id[e.subject_id], by_id[e.object_id], e.direct_edge_count, e.indirect_edge_count)
        for e in edges
    )
    return node_rows, edge_rows


def verify_outbox_deltas(session: Session, store_id: str, after_id: int = 0) -> None:
    """Delta-scoped verification (boolean spec §8.3): the outbox names exactly the
    pairs whose reachability allegedly flipped. For each pair's *final* action in the
    range, recompute reachability by BFS over direct edges and compare with both the
    closure row and the claimed flip. O(affected × local neighbourhood) -- the full
    closure recompute stays a test-suite job, never a per-write cost."""
    rows = outbox_rows(session, store_id, after_id)
    if not rows:
        return

    final: dict[tuple[int, int], str] = {}
    for r in rows:
        final[(r.subject_node_id, r.object_node_id)] = r.action

    edges = session.exec(select(EdgeV4).where(EdgeV4.store_id == store_id)).all()
    adj: dict[int, list[int]] = {}
    closure: dict[tuple[int, int], int] = {}
    for e in edges:
        if e.direct_edge_count > 0:
            adj.setdefault(e.subject_id, []).append(e.object_id)
        closure[(e.subject_id, e.object_id)] = e.indirect_edge_count

    def bfs_reaches(src: int, dst: int) -> bool:
        seen = {src}
        frontier = [src]
        while frontier:
            nxt = []
            for n in frontier:
                for m in adj.get(n, ()):
                    if m == dst:
                        return True
                    if m not in seen:
                        seen.add(m)
                        nxt.append(m)
            frontier = nxt
        return False

    for (s, o), action in final.items():
        reachable = bfs_reaches(s, o)
        row_positive = closure.get((s, o), 0) > 0
        if reachable != row_positive:
            _fail(f'delta-scoped: closure row disagrees with direct-edge BFS for '
                  f'({s} -> {o}): bfs={reachable} row={row_positive}')
        expected = (action == 'ADDED')
        if reachable != expected:
            _fail(f'delta-scoped: outbox claims {action} for ({s} -> {o}) but BFS '
                  f'reachability is {reachable}')


class ParanoiaGuard:
    """The installed paranoia state for one (session, store) pair.

    The commit listeners read their level off this object, so a *re-install* (say a
    test that wants ``'full'`` on a store its ``ConnectedStore`` already opened at
    ``'residue'``) UPGRADES in place instead of stacking a second pair of listeners
    and double-checking every commit.
    """

    def __init__(self, session: Session, store_id: str,
                 schema_info: 'SchemaInfo | None', level: str):
        self.store_id = store_id
        self.schema_info = schema_info
        self.level = level
        # Watermark of the last COMMITTED outbox id: rows above it in before_commit
        # are exactly this transaction's flips. Only ever set from committed state,
        # so a rollback (which discards its own rows) can never leave it stale.
        self.wm = outbox_watermark(session, store_id)
        # I7: last-seen residue versions, monotone across the run. Only advanced by
        # the post-commit pass so rolled-back bumps don't poison the baseline.
        self.committed_versions: dict[int, int] = {}

    def raise_to(self, level: str, schema_info: 'SchemaInfo | None') -> 'ParanoiaGuard':
        if _LEVEL_RANK[level] > _LEVEL_RANK[self.level]:
            self.level = level
        if schema_info is not None and self.schema_info is None:
            self.schema_info = schema_info
        return self

    # -- the listeners ---------------------------------------------------- #

    def before_commit(self, sess: Session) -> None:
        if self.level == PARANOIA_OFF:
            return
        sess.flush()   # before_commit fires before the commit's flush; check real state
        with _violations_tagged(self.store_id, 'pre-commit'):
            if self.level == PARANOIA_FULL:
                check_invariants(sess, self.store_id, self.schema_info,
                                 residue_versions=dict(self.committed_versions))
                verify_outbox_deltas(sess, self.store_id, self.wm)
            else:                                   # PARANOIA_RESIDUE
                check_residue_hygiene(sess, self.store_id, self.schema_info)

    def after_commit(self, sess: Session) -> None:
        # Post-commit re-checking is a FULL-tier facility only: it cannot abort
        # anything (the commit already landed), so the cheap tier -- whose whole job
        # is to fail closed on the write path -- does not pay for it.
        if self.level != PARANOIA_FULL:
            return
        with Session(sess.get_bind()) as fresh:
            with _violations_tagged(self.store_id, 'post-commit'):
                check_invariants(fresh, self.store_id, self.schema_info,
                                 residue_versions=self.committed_versions)
            self.wm = outbox_watermark(fresh, self.store_id)


class _violations_tagged:
    """Re-raise an ``InvariantViolation`` with the store id and commit phase attached,
    so an operator reading a production traceback learns WHICH store and WHICH clause
    without re-deriving it. The original clause text (``I6: ...``) is preserved
    verbatim inside the new message."""

    def __init__(self, store_id: str, phase: str):
        self.store_id, self.phase = store_id, phase

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None and issubclass(exc_type, InvariantViolation):
            raise InvariantViolation(
                f'store={self.store_id!r} [{self.phase}] {exc}') from exc
        return False


def install_paranoia(session: Session, store_id: str,
                     schema_info: 'SchemaInfo | None' = None, *,
                     level: 'bool | str' = PARANOIA_FULL) -> 'ParanoiaGuard | None':
    """Wire paranoia mode onto a session (boolean spec §8.1). Returns the guard (or
    ``None`` for ``level='off'``).

    ``level='full'`` (the default, and what every existing caller gets):

    - pre-commit (inside the transaction): flush pending state, run the invariant
      checker AND the delta-scoped verifier over this transaction's outbox range; a
      violation raises, aborting the commit, so the caller's rollback restores the
      last consistent state.
    - post-commit (fresh session, same bind): re-run the checker against what was
      actually committed, catching commit-boundary and session-state bugs.

    ``level='residue'`` is the cheap production tier: ``check_residue_hygiene``
    pre-commit only (see this module's docstring for the tier table).

    Installing twice for the same (session, store) never stacks listeners -- the
    second call raises the existing guard's level if the new one is stronger and
    returns it.
    """
    level = normalize_paranoia_level(level)
    registry: dict[str, ParanoiaGuard] = session.info.setdefault('paranoia_guards', {})
    existing = registry.get(store_id)
    if existing is not None:
        return existing.raise_to(level, schema_info)
    if level == PARANOIA_OFF:
        return None

    guard = ParanoiaGuard(session, store_id, schema_info, level)
    registry[store_id] = guard

    @event.listens_for(session, 'before_commit')
    def _pre_commit_check(sess: Session) -> None:
        guard.before_commit(sess)

    @event.listens_for(session, 'after_commit')
    def _post_commit_check(sess: Session) -> None:
        guard.after_commit(sess)

    return guard
