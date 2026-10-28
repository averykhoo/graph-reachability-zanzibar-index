"""
Invariant checker + paranoia mode for the graph index.

Numbered invariants of the graph index. This module carries the *state*
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
      that happen to intern a node of that shape.
  I4-I7 cover derived-predicate state (namespace classification, derived-flag
      exclusivity, residue placement, residue-version monotonicity); I10 is outbox
      row sanity and I13 node reference-count degree. ``check_invariants`` lists
      exactly what it runs.

I11 (read purity) and I12 (rejection cleanliness) are *differential* invariants -- they
compare two snapshots -- so they are not checked here; ``snapshot_rows`` provides the
id-independent snapshot such a comparison needs.

Paranoia mode: ``install_paranoia(session, ...)`` wires the checker
to run pre-commit *inside* the transaction (a violation raises ``InvariantViolation``
and aborts the commit) and post-commit in a *fresh* session on the same bind (catching
commit-boundary/session-state bugs). ``Store`` defaults to ``'off'``;
``install_paranoia`` called directly defaults to ``'full'``.

**Tiers.** Paranoia has four
levels, because the full
checker is an O(store) per-commit cost (measured 4.8x-10x on the write path),
too expensive for production, while a cheaper tier can still run there:

  ``'off'``      no listeners (the ``Store`` default).
  ``'residue'``  the CHEAP, security-relevant tier: residue hygiene only (the I6
                 family, minus its two edge-overlap clauses), scoped to the store's
                 ``Residue`` rows and the node ids those rows reference --
                 O(residue rows + referenced ids), no full node or edge scan, no
                 BFS. This is the tier that owns the dangling
                 ``upos``/``neg`` id class, i.e. a known authorization
                 escalation.
                 PLUS I14 crossing-middle completeness, DELTA-SCOPED to the entities
                 the transaction touched (``check_i14_delta``): a missing crossing
                 middle is a fail-OPEN under a negated consumer.
                 Vacuous on a schema with no crossable shape (every plain OpenFGA
                 schema). An untouched entity's I14 state, and an I13 refcount
                 corruption, stay full-tier only.
                 Pre-commit only, so a violation ABORTS the writing transaction.
  ``'full'``     everything above: ``check_invariants`` plus the delta-scoped BFS verifier, pre-commit AND post-commit
                 in a fresh session. O(store) per commit, plus O(pairs x edges) for
                 the verifier. Prerelease/test tier.
  ``'fixpoint'`` everything ``'full'`` runs, PLUS a per-cascade I9 check: after each cascade
                 drains, re-reconcile every key the cascade SCHEDULED and require each
                 to be a fixpoint. It is the only detector for an execution-side
                 missed reconcile -- the settle pass is structurally blind to one
                 within the cascade that skipped it, and no I1-I12 clause fires on the
                 resulting closure-edge-only staleness.
                 O(cascade work), roughly DOUBLING cascade cost -- far past
                 ``'residue'``'s ~+5%, so it is a diagnosis tier, never a production
                 one. Nothing selects it implicitly: it is above ``'full'`` on the
                 ladder, no default is it, and no boolean-ish word maps to it.
                 Scope bound: EXECUTION-side misses only. A key that was never
                 SCHEDULED is outside this tier by construction; ``audit_fixpoint``
                 (O(live derived keys), unbounded by write size) remains the only
                 detector for that class.

``resolve_paranoia_level`` is the shared precedence rule for wiring sites: an
explicit argument beats the ``ZANZIBAR_PARANOIA`` environment variable, which beats
the caller's default. ``Store`` defaults to ``'off'`` because ``'residue'``
measured at +4.3%/+5.7% of the sync write path (162/478 per-write commits,
interleaved A/B, min-of-3) -- cheap next to ``'full'``'s +124%/+303%, but too much
to impose silently; see ``Store.DEFAULT_PARANOIA``. ``'residue'`` is
nonetheless the RECOMMENDED production setting: it is the only runtime detector for
that escalation class.
"""
# Provenance (moved out of the docstring, TK123 item 14): numbering from boolean spec sec 8.2;
# tiers from ZT-P1-3 (2026-07-26), the fourth by TK82 (2026-09-19); the 4.8x-10x figure is
# benchmarks/results/BASELINE_2026-07-13.md; the escalation class is ZT-P0-1; check_i14_delta
# is TK118.
# Provenance (moved out of the docstring, TK123 item 14): boolean spec §8.1/§8.2; boolean spec
# §8.1; pin: ``tests/test_reg14_residue_gc_elision.py``; ``tests/test_p12_severity_sign.py``;
# ``tests/test_tk118_residue_i14.py``; I1/I2/I3/I13/I14 + I4-I7 + I10; `docs/perf-next-
# round.md`; TK74, docs/tk74-staleness-net-2026-09-18.md sec 9.2 / sec 10.3.

from __future__ import annotations

import os
from collections import Counter
from typing import NamedTuple, TYPE_CHECKING

import json

from sqlalchemy import event, tuple_
from sqlmodel import Session, select

from .models import DeltaOutbox, Edge, Node, ResidueRef, Residue
from .outbox import outbox_rows, outbox_watermark

if TYPE_CHECKING:
    from zanzibar.schema import SchemaInfo


class InvariantViolation(AssertionError):
    """A store-state invariant does not hold. Distinct from ValueError (op rejection):
    a rejection is a *correct* refusal; a violation is corruption.

    Deliberately NOT a ``zanzibar.ZanzibarError``: ``except ZanzibarError`` is the handler
    for refusals and limits, and it must never swallow a report that the stored index is
    corrupt. Catch this class explicitly (it is an ``AssertionError``) if you catch it at all.
    """


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
PARANOIA_FIXPOINT = 'fixpoint'
#: Ordered WEAKEST to STRONGEST. The order is load-bearing twice over: ``_LEVEL_RANK``
#: is built from it, and ``ParanoiaGuard.raise_to`` keeps the higher rank when a store
#: is wired twice. ``'fixpoint'`` is appended ABOVE ``'full'`` deliberately -- placed
#: below it, ``full`` would IMPLY the cascade tier and every caller that passes
#: ``paranoia=True`` would start paying a doubled cascade, which is exactly the
#: "opt-in, default OFF" property TK82 is specified around
#: (docs/tk82-cascade-fixpoint-tier-2026-09-19.md sec 1).
PARANOIA_LEVELS = (PARANOIA_OFF, PARANOIA_RESIDUE, PARANOIA_FULL, PARANOIA_FIXPOINT)
_LEVEL_RANK = {name: i for i, name in enumerate(PARANOIA_LEVELS)}


def paranoia_at_least(level: str, floor: str) -> bool:
    """``level`` is at least as strong as ``floor`` on the ladder.

    Use this instead of ``level == PARANOIA_FULL``: an equality test silently EXCLUDES
    every tier added above the one compared, so appending ``'fixpoint'`` would have made
    the strongest tier weaker than ``'full'`` (it would have fallen into the residue
    branch and lost post-commit re-checking)."""
    # Provenance (moved out of the docstring, TK123 item 14): pinned by
    # tests/test_cascade_fixpoint_tier.py::test_fixpoint_tier_is_at_least_full.
    return _LEVEL_RANK[level] >= _LEVEL_RANK[floor]


def paranoia_level(session: Session, store_id: str) -> str:
    """The level installed for ``store_id`` on ``session``, or ``'off'`` if none is.

    The registry IS the authority: ``install_paranoia`` registers nothing for ``'off'``,
    so absence means off. This is how code that runs *inside* a write (the delta
    processor's cascade tier) reads the operator's setting without growing a second,
    separately-configurable knob that could disagree with the guard."""
    guard = session.info.get('paranoia_guards', {}).get(store_id)
    return guard.level if guard is not None else PARANOIA_OFF

#: The environment variable an operator sets to turn the layer on (or off) without
#: a code change. Accepts a level name, or a boolean-ish word (``1``/``true``/``on``
#: => ``'full'``, ``0``/``false``/``off`` => ``'off'``).
PARANOIA_ENV_VAR = 'ZANZIBAR_PARANOIA'

_BOOLISH = {'1': PARANOIA_FULL, 'true': PARANOIA_FULL, 'yes': PARANOIA_FULL,
            'on': PARANOIA_FULL,
            '0': PARANOIA_OFF, 'false': PARANOIA_OFF, 'no': PARANOIA_OFF}


def normalize_paranoia_level(value: 'bool | int | str | None') -> str:
    """Coerce a user-supplied paranoia setting to one of ``PARANOIA_LEVELS``.

    ``True``/``False`` and the ints ``1``/``0`` map to ``'full'``/``'off'``, the same
    as the strings ``'1'``/``'0'`` the environment variable accepts. Anything
    unrecognized (``2`` included) is a loud ``ValueError`` -- a typo'd security switch
    must never silently mean "off"."""
    if value is True:
        return PARANOIA_FULL
    if value is False:
        return PARANOIA_OFF
    if type(value) is int and value in (0, 1):
        return PARANOIA_FULL if value else PARANOIA_OFF
    if isinstance(value, str):
        v = value.strip().lower()
        if v in _LEVEL_RANK:
            return v
        if v in _BOOLISH:
            return _BOOLISH[v]
    raise ValueError(
        f'bad paranoia level {value!r}; expected one of {PARANOIA_LEVELS} '
        f'(or a bool, the int 0 / 1, or one of {sorted(_BOOLISH)})')


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


def _load(session: Session, store_id: str) -> tuple[list[Node], list[Edge]]:
    nodes = list(session.exec(select(Node).where(Node.store_id == store_id)).all())
    edges = list(session.exec(select(Edge).where(Edge.store_id == store_id)).all())
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
    none of them matched this function. This
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
    # Provenance (moved out of the docstring, TK123 item 14): zero-trust review 2026-07-26,
    # P5.
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
    # The clause itself is _check_i14, shared with the cheap tier's delta-scoped
    # check_i14_delta (TK118), so the two tiers cannot drift.
    if schema_info is not None and schema_info.crossable_shapes:
        _check_i14(schema_info.crossable_shapes,
                   [n for n in nodes if n.wildcard == ''],
                   [n for n in nodes if n.wildcard != ''],
                   direct_edge_set)

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


def _check_i14(crossable, concrete_nodes, wildcard_nodes, direct_edge_set) -> None:
    """The I14 clause (see ``check_invariants``), over the entities the given concrete
    nodes witness. ``concrete_nodes`` must hold EVERY concrete node of each entity it
    mentions (a partial entity could look unwitnessed, or lack a middle it has);
    ``wildcard_nodes`` the wildcard nodes of the crossable shapes' types; and
    ``direct_edge_set`` at least the direct ``(subject_id, object_id)`` pairs among
    those nodes. Shared by the full checker and the cheap tier's ``check_i14_delta``."""
    concrete_by_key = {(n.type, n.name, n.predicate): n for n in concrete_nodes}
    wildcard_by_variant = {(n.type, n.predicate, n.wildcard): n for n in wildcard_nodes}

    def _is_bridge_middle(n) -> bool:
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


class _I14NodeFacts(NamedTuple):
    """The node columns the I14 clause reads, without the ORM instance."""
    id: int
    type: str
    name: str
    predicate: str
    wildcard: str
    implicit: bool
    reference_count: int

    def __str__(self) -> str:                            # for violation messages
        return f'{self.type}:{self.name}#{self.predicate}'


_I14_COLS = (Node.id, Node.type, Node.name, Node.predicate, Node.wildcard,
             Node.implicit, Node.reference_count)


def check_i14_delta(session: Session, store_id: str, schema_info: 'SchemaInfo',
                    entities: 'set[tuple[str, str]]', types: 'set[str]') -> None:
    """The cheap tier's I14: the full checker's clause, scoped to the
    entities a transaction touched instead of the whole store.

    ``entities`` are ``(type, name)`` pairs with a concrete ``Node`` row created,
    modified or deleted in the transaction; ``types`` are crossable types whose
    WILDCARD node was created or deleted, so every entity of that type is re-checked.
    Both are collected by ``ParanoiaGuard``'s ``after_flush`` listener. Cost:
    O(touched entities' nodes + their bridge edges), plus O(entities of T) only on the
    rare wildcard-node create/delete -- never O(store). Vacuous (no query at all) when
    the schema has no crossable shape, i.e. on every plain OpenFGA schema.

    Blind spot, by design: a bridge ``Edge`` row changed WITHOUT its endpoints'
    ``reference_count`` moving touches no node; that is I13 corruption, which only the
    full tier sees.
    """
    # Provenance (moved out of the docstring, TK123 item 14): TK118;
    # ``tests/test_paranoia_wiring.py::test_tier_boundary_is_what_it_says_it_is``.
    crossable = schema_info.crossable_shapes
    if not crossable:
        return
    crossable_types = {t for (t, _p) in crossable}
    types = types & crossable_types
    entities = {(t, x) for (t, x) in entities if t in crossable_types and t not in types}
    if not entities and not types:
        return

    concrete: list[_I14NodeFacts] = []
    for t in sorted(types):
        concrete += [_I14NodeFacts(*r) for r in session.exec(
            select(*_I14_COLS).where(Node.store_id == store_id)
            .where(Node.type == t).where(Node.wildcard == '')).all()]
    keys = sorted(entities)
    # Chunked: SQLite's default bound-parameter limit is 999.
    for i in range(0, len(keys), 400):
        chunk = keys[i:i + 400]
        concrete += [_I14NodeFacts(*r) for r in session.exec(
            select(*_I14_COLS).where(Node.store_id == store_id)
            .where(Node.wildcard == '')
            .where(tuple_(Node.type, Node.name).in_(chunk))).all()]
    if not concrete:
        return
    wildcards = [_I14NodeFacts(*r) for r in session.exec(
        select(*_I14_COLS).where(Node.store_id == store_id)
        .where(Node.wildcard != '')
        .where(Node.type.in_(sorted(crossable_types)))).all()]

    # Only the bridge pairs the clause asks about: (middle -> w_any), (w_all -> middle).
    wildcard_ids = [n.id for n in wildcards]
    mid_ids = sorted({n.id for n in concrete if (n.type, n.predicate) in crossable})
    direct_edge_set: set[tuple[int, int]] = set()
    if wildcard_ids:
        for i in range(0, len(mid_ids), 400):
            chunk = mid_ids[i:i + 400]
            for s, o in session.exec(
                    select(Edge.subject_id, Edge.object_id)
                    .where(Edge.store_id == store_id)
                    .where(Edge.direct_edge_count > 0)
                    .where(((Edge.subject_id.in_(chunk))
                            & (Edge.object_id.in_(wildcard_ids)))
                           | ((Edge.object_id.in_(chunk))
                              & (Edge.subject_id.in_(wildcard_ids))))).all():
                direct_edge_set.add((s, o))
    _check_i14(crossable, concrete, wildcards, direct_edge_set)


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
        select(Residue).where(Residue.store_id == store_id)).all()
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
    """The ``ResidueRef`` reverse index as ``object_node_id -> {subject_node_id}``.

    A COLUMN select, not an entity select: this runs inside every commit under the
    cheap ``residue`` tier, where ORM instance bookkeeping is the bulk of the cost.
    """
    out: dict[int, set[int]] = {}
    for object_node_id, subject_node_id in session.exec(
            select(ResidueRef.object_node_id, ResidueRef.subject_node_id)
            .where(ResidueRef.store_id == store_id)).all():
        out.setdefault(object_node_id, set()).add(subject_node_id)
    return out


def _check_residue_rows(rows, node_of, *,
                        derived_families=None, subject_shapes=None,
                        derived_edge_subjects: 'dict[int, set[int]] | None' = None,
                        residue_refs: 'dict[int, set[int]] | None' = None,
                        residue_versions: 'dict | None' = None) -> None:
    """I6 residue placement (+ I7 monotonicity when ``residue_versions`` is given).

    Shared by the full checker and by the cheap ``residue`` paranoia tier, so the two
    can never drift. ``node_of`` resolves a node id to its ``Node`` (or None -- a
    dangling reference, which is the ZT-P0-1 corruption class).
    ``derived_edge_subjects`` is the per-object set of subjects holding a derived
    direct edge; ``None`` means "not computed" and SKIPS the two edge-overlap clauses
    (they need a full edge scan, which is exactly what the cheap tier refuses to pay).
    ``derived_families``/``subject_shapes`` of ``None`` skip the schema-dependent
    clauses.

    ``residue_refs`` is the ``ResidueRef`` reverse index as
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
        # I6: the ResidueRef reverse index agrees with this row, exactly and in both
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
    """Ditto for ``Residue``. ``version`` is absent: I7 is a full-tier clause."""
    id: int
    object_node_id: int
    relation: str
    stars: str
    neg: str
    upos: str


def check_residue_hygiene(session: Session, store_id: str,
                          schema_info: 'SchemaInfo | None' = None) -> None:
    """The CHEAP paranoia tier: the I6 residue-hygiene family alone.

    Every clause of I6 except the two that need a full edge scan
    (``neg``/``upos`` overlapping derived-edge holders) -- in particular the
    **dead node id** clauses, which are the runtime detector for the
    residue-GC authorization escalation (a residue vouching for a recycled rowid).

    Cost: one indexed ``Residue`` scan for the store, plus one batched
    ``Node WHERE id IN (...)`` fetch of exactly the ids those rows name --
    O(residue rows + referenced ids). No node scan, no edge scan, no BFS, so it
    does NOT grow with store size the way ``check_invariants`` does.

    I7 (version monotonicity) is deliberately excluded: it needs a baseline carried
    across commits, it is not security-relevant, and the cheap tier runs pre-commit
    only (where a rolled-back bump would poison that baseline).
    """
    # Provenance (moved out of the docstring, TK123 item 14): ZT-P0-1.
    # Provenance (moved out of the docstring, TK123 item 14): ZT-P1-3.
    # COLUMN selects, not entity selects, on both queries: this runs inside every
    # commit, and materializing ORM instances (identity-map bookkeeping, instance
    # state) measured as the bulk of the tier's cost. The lightweight records below
    # duck-type the attributes the shared clause code reads.
    rows = [_ResidueFacts(*t) for t in session.exec(
        select(Residue.id, Residue.object_node_id, Residue.relation,
               Residue.stars, Residue.neg, Residue.upos)
        .where(Residue.store_id == store_id)).all()]
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
                select(Node.id, Node.type, Node.name, Node.predicate,
                       Node.wildcard, Node.implicit)
                .where(Node.store_id == store_id)
                .where(Node.id.in_(chunk))).all():
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
        select(DeltaOutbox).where(DeltaOutbox.store_id == store_id)).all()
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
    """Delta-scoped verification: the outbox names exactly the
    pairs whose reachability allegedly flipped. For each pair's *final* action in the
    range, recompute reachability by BFS over direct edges and compare with both the
    closure row and the claimed flip. O(affected x local neighbourhood) -- the full
    closure recompute stays a test-suite job, never a per-write cost."""
    # Provenance (moved out of the docstring, TK123 item 14): boolean spec §8.3.
    rows = outbox_rows(session, store_id, after_id)
    if not rows:
        return

    final: dict[tuple[int, int], str] = {}
    for r in rows:
        final[(r.subject_node_id, r.object_node_id)] = r.action

    edges = session.exec(select(Edge).where(Edge.store_id == store_id)).all()
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
    test that wants ``'full'`` on a store its ``Store`` already opened at
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
        # TK118: what this transaction touched, for the cheap tier's delta-scoped I14.
        # Filled by note_flush, emptied only by a COMMIT: an entry surviving a rollback
        # merely re-checks an entity next time, while emptying on a savepoint rollback
        # could drop the outer transaction's entries.
        self.i14_entities: set[tuple[str, str]] = set()
        self.i14_types: set[str] = set()

    def _crossable_types(self) -> frozenset[str]:
        # Cached per schema_info: this runs on EVERY flush, and on a plain schema the
        # whole listener must cost one lookup (the schema is static per store).
        si = self.schema_info
        if si is None:
            return frozenset()
        cached = getattr(self, '_crossable_cache', None)
        if cached is None or cached[0] is not si:
            cached = (si, frozenset(t for (t, _p) in si.crossable_shapes))
            self._crossable_cache = cached
        return cached[1]

    def note_flush(self, sess: Session) -> None:
        """``after_flush``: record the I14-relevant nodes this flush wrote (the
        pre-flush ``new`` / ``dirty`` / ``deleted`` sets are still populated here).
        A concrete node touches its entity; a crossable type's WILDCARD node matters
        only when created or deleted -- its refcount moves on every bridge add, and
        treating that as a touch would re-scan the whole type on every write."""
        if self.level == PARANOIA_OFF:
            return
        types = self._crossable_types()
        if not types:
            return
        for bucket, structural in ((sess.new, True), (sess.deleted, True),
                                   (sess.dirty, False)):
            for obj in bucket:
                if (not isinstance(obj, Node) or obj.store_id != self.store_id
                        or obj.type not in types):
                    continue
                if obj.wildcard == '':
                    self.i14_entities.add((obj.type, obj.name))
                elif structural:
                    self.i14_types.add(obj.type)

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
            if paranoia_at_least(self.level, PARANOIA_FULL):
                check_invariants(sess, self.store_id, self.schema_info,
                                 residue_versions=dict(self.committed_versions))
                verify_outbox_deltas(sess, self.store_id, self.wm)
            else:                                   # PARANOIA_RESIDUE
                check_residue_hygiene(sess, self.store_id, self.schema_info)
                if self.schema_info is not None:
                    check_i14_delta(sess, self.store_id, self.schema_info,
                                    self.i14_entities, self.i14_types)

    def after_commit(self, sess: Session) -> None:
        # TK170: SQLAlchemy also fires after_commit when a SAVEPOINT is released
        # (SessionTransaction.commit dispatches it for ``nested`` transactions, while
        # the savepoint is still the session's current transaction). A release commits
        # nothing: the root transaction is still open. Re-checking then is worse than
        # useless -- on a SingletonThreadPool bind (in-memory SQLite) the fresh Session
        # below shares the caller's DBAPI connection, and its close() ROLLS BACK the
        # whole open transaction, savepoint writes included (a stale ALLOW, and "no
        # such savepoint" on an outer rollback). The I14 sets are emptied only by a
        # real commit, too (see __init__). So only the ROOT commit runs this hook.
        if sess.in_nested_transaction():
            return
        self.i14_entities.clear()
        self.i14_types.clear()
        # Post-commit re-checking is a FULL-tier facility only: it cannot abort
        # anything (the commit already landed), so the cheap tier -- whose whole job
        # is to fail closed on the write path -- does not pay for it.
        if not paranoia_at_least(self.level, PARANOIA_FULL):
            return
        with Session(sess.get_bind()) as fresh:
            try:
                with _violations_tagged(self.store_id, 'post-commit'):
                    check_invariants(fresh, self.store_id, self.schema_info,
                                     residue_versions=self.committed_versions)
            except InvariantViolation as exc:
                # TK163: raising from inside SQLAlchemy's after_commit hook leaves the
                # session stuck in the COMMITTED state, so the caller's rollback raised
                # InvalidRequestError over this violation and the session refused every
                # later call. A session that opted in (``defer_post_commit_violations``,
                # what ``Store`` does) gets the violation parked instead; the committer
                # re-raises it once ``commit()`` has returned on a clean session.
                if not sess.info.get(_DEFER_POST_COMMIT_KEY):
                    raise
                parked = InvariantViolation(
                    f'{exc} -- found AFTER the commit: the transaction IS committed '
                    f'(tuple log and index); nothing was rolled back')
                parked.__cause__ = exc
                sess.info.setdefault(_PENDING_POST_COMMIT_KEY, []).append(parked)
            # The rows are committed whether or not the re-check passed: advance the
            # delta verifier's baseline past them either way, or every later
            # pre-commit pass re-verifies (and re-fails on) this transaction's range.
            self.wm = outbox_watermark(fresh, self.store_id)


_DEFER_POST_COMMIT_KEY = 'zanzibar_defer_post_commit_violations'
_PENDING_POST_COMMIT_KEY = 'zanzibar_pending_post_commit_violations'


def defer_post_commit_violations(session: Session) -> None:
    """Opt ``session`` in to DEFERRED post-commit violations: a guard's
    post-commit re-check that fails parks its ``InvariantViolation`` on the session
    instead of raising from inside SQLAlchemy's ``after_commit`` hook (which leaves the
    session stuck in the COMMITTED state). The committer must then call
    ``raise_post_commit_violation`` right after every ``commit()``. Per session, so a
    guard installed later on the same session defers too."""
    session.info[_DEFER_POST_COMMIT_KEY] = True


def raise_post_commit_violation(session: Session) -> None:
    """Raise (and clear) the first post-commit ``InvariantViolation`` parked on
    ``session`` since the last call; a no-op when none is. Further parked ones are
    attached to it as notes."""
    pending = session.info.pop(_PENDING_POST_COMMIT_KEY, None)
    if pending:
        first = pending[0]
        for more in pending[1:]:
            first.add_note(f'also: {more}')
        raise first


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
    """Wire paranoia mode onto a session. Returns the guard (or
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
    # Provenance (moved out of the docstring, TK123 item 14): boolean spec §8.1.
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

    @event.listens_for(session, 'after_flush')
    def _note_flush(sess: Session, _flush_context) -> None:
        guard.note_flush(sess)

    return guard
