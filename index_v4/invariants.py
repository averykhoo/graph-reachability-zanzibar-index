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
  (I4-I10 arrive with the derived-predicate state in later phases.)

I11 (read purity) and I12 (rejection cleanliness) are *differential* invariants -- they
compare two snapshots -- so they live with the harness (``snapshot_rows`` here provides
the id-independent snapshot; the ParityEngine does the comparison).

Paranoia mode (boolean spec §8.1): ``install_paranoia(session, ...)`` wires the checker
to run pre-commit *inside* the transaction (a violation raises ``InvariantViolation``
and aborts the commit) and post-commit in a *fresh* session on the same bind (catching
commit-boundary/session-state bugs). Default ON while prerelease; pass
``paranoia=False`` at the wiring site for benchmarks.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import json

from sqlalchemy import event
from sqlmodel import Session, select

from .models import DeltaOutboxV1, EdgeV4, NodeV4, ResidueV1
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


def _load(session: Session, store_id: str) -> tuple[list[NodeV4], list[EdgeV4]]:
    nodes = list(session.exec(select(NodeV4).where(NodeV4.store_id == store_id)).all())
    edges = list(session.exec(select(EdgeV4).where(EdgeV4.store_id == store_id)).all())
    return nodes, edges


def _fail(msg: str) -> None:
    raise InvariantViolation(msg)


def check_invariants(session: Session, store_id: str,
                     schema_info: 'SchemaInfo | None' = None,
                     residue_versions: dict[int, int] | None = None) -> None:
    """Assert I1-I6 + I10 (+ node encoding) over the store's committed-or-pending rows.

    ``schema_info`` gates the schema-dependent invariants (I3 bridge hygiene, I4
    namespace classification, I5 derived-flag exclusivity, I6 residue placement);
    without it only the schema-independent ones run. ``residue_versions`` (a mutable
    dict the caller keeps across checks) enables I7 version monotonicity.
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
    subject_shapes = schema_info.subject_wildcard_shapes
    rows = session.exec(
        select(ResidueV1).where(ResidueV1.store_id == store_id)).all()
    derived_edge_subjects: dict[int, set[int]] = {}
    for e in edges:
        if e.direct_edge_count > 0 and e.derived:
            derived_edge_subjects.setdefault(e.object_id, set()).add(e.subject_id)

    for r in rows:
        node = by_id.get(r.object_node_id)
        if node is None:
            _fail(f'I6: residue row {r.id} references a missing node {r.object_node_id}')
        if (node.type, node.predicate) not in derived_families:
            _fail(f'I6: residue on a non-derived relation: {node}')
        if r.relation != node.predicate:
            _fail(f'I6: residue.relation {r.relation!r} disagrees with its node {node}')
        stars = frozenset(tuple(s) for s in json.loads(r.stars))
        neg = set(json.loads(r.neg))
        if not stars and not neg:
            _fail(f'I6: empty residue row persisted for {node}')
        if not stars <= subject_shapes:
            _fail(f'I6: residue stars {stars} outside declared subject shapes on {node}')
        for nid in neg:
            s = by_id.get(nid)
            if s is None:
                _fail(f'I6: residue neg holds a dead node id {nid} on {node}')
            if s.wildcard != '':
                _fail(f'I6: residue neg holds a wildcard node {s} on {node}')
            if (s.type, s.predicate) not in stars:
                _fail(f'I6: neg subject {s} not star-covered by {stars} on {node}')
        if neg & derived_edge_subjects.get(r.object_node_id, set()):
            _fail(f'I6: neg overlaps derived-edge holders on {node} '
                  f'(an edge means expr-true; neg means expr-false)')

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


def install_paranoia(session: Session, store_id: str,
                     schema_info: 'SchemaInfo | None' = None) -> None:
    """Wire paranoia mode onto a session (boolean spec §8.1).

    - pre-commit (inside the transaction): flush pending state, run the invariant
      checker AND the delta-scoped verifier over this transaction's outbox range; a
      violation raises, aborting the commit, so the caller's rollback restores the
      last consistent state.
    - post-commit (fresh session, same bind): re-run the checker against what was
      actually committed, catching commit-boundary and session-state bugs.
    """
    # Watermark of the last COMMITTED outbox id: rows above it in before_commit are
    # exactly this transaction's flips. Only ever set from committed state, so a
    # rollback (which discards its own rows) can never leave it stale.
    state = {'wm': outbox_watermark(session, store_id)}
    # I7: last-seen residue versions, monotone across the run. Only advanced by the
    # post-commit pass so rolled-back bumps don't poison the baseline.
    committed_versions: dict[int, int] = {}

    @event.listens_for(session, 'before_commit')
    def _pre_commit_check(sess: Session) -> None:
        sess.flush()   # before_commit fires before the commit's flush; check real state
        check_invariants(sess, store_id, schema_info,
                         residue_versions=dict(committed_versions))
        verify_outbox_deltas(sess, store_id, state['wm'])

    @event.listens_for(session, 'after_commit')
    def _post_commit_check(sess: Session) -> None:
        with Session(sess.get_bind()) as fresh:
            check_invariants(fresh, store_id, schema_info,
                             residue_versions=committed_versions)
            state['wm'] = outbox_watermark(fresh, store_id)
