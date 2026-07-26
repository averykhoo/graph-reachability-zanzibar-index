"""
reg14 -- the N3 ``_keys_referencing`` elision was UNSOUND on ``closure`` leaves:
a dangling residue ``upos`` id survived a GC, its rowid was recycled onto another
principal, and ``check`` then returned True where the oracle says False
(authorization escalation; zero-trust review 2026-07-26 `ZT-P0-1`).

Mechanism (traced, do not re-derive):
  ``_RESIDUE_LOCAL_LEAF_KINDS`` whitelisted ``'closure'`` on the premise that closure
  leaves "store raw tuples", so any id they record in a residue is edge-justified on
  the recording object. FALSE: ``_leaf_concretes(kind='closure')`` resolves its
  candidates via ``_incoming_concretes`` -> ``idx.lookup_reverse`` -> the FULL
  TRANSITIVE CLOSURE, so a userset node reachable only transitively
  (``group:g1#member -> group:g2#member -> doc:y#a.0``) gets recorded in
  ``residue(doc:y#a).upos`` while holding NO edge on ``doc:y``. When the whitelist
  made ``_cross_object_recordings_possible`` False, ``_keys_referencing`` short-
  circuited to ``[]``, ``_residue_references`` was unconditionally False, and
  ``_gc_subject_node``'s guard stopped protecting the node: the first affected key in
  the cascade round un-recorded and DELETED it; the second key found ``s_node is
  None`` and skipped its whole recording block, never pruning the stale id.

Why the gate missed it: it needs an all-whitelist schema + a TRANSITIVE userset chain
into a tainted relation's closure leaf on >= 2 objects + the chain edge removed in one
op so both objects flip in one cascade round. No corpus or generator built that
conjunction -- hence this pin. Ported from the session repro ``n3_FINAL.py``.

The pins below are deliberately layered so a regression cannot hide: the oracle's
answer (the behavioural spec), structural integrity (no dangling residue id), the
runtime detector (I6), and the observable authorization answer.
"""

import json

import pytest
from sqlmodel import select

from index_v4.invariants import check_invariants
from index_v4.models import NodeV4, ResidueV1
from index_v4.outbox import outbox_watermark
from index_v4.processor import DeltaProcessor
from tests.oracle import Oracle, t as ot
from tests.wildcard_helpers import make_wildcard_index
from zanzibar_utils_v1 import Entity, RelationalTriple, parse_openfga_schema

# All leaves of this schema are 'closure' -- the whitelist's own worst case, and the
# proof that the root cause is the 'closure' entry and not the 2026-07-17 Fix A lift
# (there is no derived-computed leaf here at all).
REG14_SCHEMA = """
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define banned: [user, group#member]
    define a: [user, group#member] but not banned
"""

# group:g2#member is granted `a` on TWO objects; group:g1#member reaches doc:*#a.0
# only TRANSITIVELY, through group:g2#member.
REG14_SETUP = [
    ('member', 'group', 'g2', 'a', 'doc', 'x'),
    ('member', 'group', 'g2', 'a', 'doc', 'y'),
    ('member', 'group', 'g1', 'member', 'group', 'g2'),
]
# Removing the chain edge flips BOTH doc:x and doc:y in ONE cascade round.
REG14_CHAIN = ('member', 'group', 'g1', 'member', 'group', 'g2')
# One further write interns a fresh node, which SQLite hands the freed rowid.
REG14_RECYCLE = ('member', 'group', 'g9', 'a', 'doc', 'x')
# g9 was granted `a` on doc:x ONLY -- never on doc:y.
REG14_QUERY = ('member', 'group', 'g9', 'a', 'doc', 'y')


class _Harness:
    """Synchronous-v1 graph backend: route the raw tuple, run the cascade, commit --
    one transaction (the `GraphBackend.apply` discipline, I5)."""

    def __init__(self, schema, paranoia):
        self.rs = parse_openfga_schema(schema, enable_boolean=True)
        self.session, self.widx = make_wildcard_index(
            self.rs.schema_info, store_id='reg14', paranoia=paranoia)
        self.proc = DeltaProcessor(self.widx, self.rs.compiled)

    def apply(self, raw, op):
        wm = outbox_watermark(self.session, 'reg14')
        sp = Ellipsis if raw[0] == '...' else raw[0]
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        fn = self.widx.add_tuple if op == 'add' else self.widx.remove_tuple
        for d in self.rs.apply(triple):
            fn('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
               d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
        self.proc.run_cascade(wm)
        self.session.commit()

    def dangling_residue_ids(self):
        """Every (relation, object, field, id) where a residue records a node id with
        no matching ``NodeV4`` row. Must always be empty."""
        live = {n.id for n in self.session.exec(
            select(NodeV4).where(NodeV4.store_id == 'reg14')).all()}
        bad = []
        for r in self.session.exec(
                select(ResidueV1).where(ResidueV1.store_id == 'reg14')).all():
            for field in ('neg', 'upos'):
                for nid in json.loads(getattr(r, field)):
                    if nid not in live:
                        obj = self.session.get(NodeV4, r.object_node_id)
                        bad.append((
                            r.relation,
                            (obj.type, obj.name) if obj is not None else r.object_node_id,
                            field, nid))
        return bad


def test_reg14_closure_leaf_transitive_userset_is_gc_protected():
    """(14) The escalation pin. A transitively-reached userset recorded in a closure
    leaf's residue ``upos`` must survive GC while ANY residue still references it; the
    stale id must never outlive its node, and ``check`` must track the oracle across the
    rowid recycle."""
    # (0) Ground truth from the independent oracle (the behavioural spec -- never edit
    #     it to make this pass). Post-remove state = the two `a` grants + the recycle
    #     write; the chain edge is gone.
    oracle = Oracle(REG14_SCHEMA,
                    [ot(*REG14_SETUP[0]), ot(*REG14_SETUP[1]), ot(*REG14_RECYCLE)])
    assert oracle.check(*REG14_QUERY) is False, \
        'oracle sanity: group:g9#member holds `a` on doc:x only, never on doc:y'

    g = _Harness(REG14_SCHEMA, paranoia=False)
    try:
        for raw in REG14_SETUP:
            g.apply(raw, 'add')

        # (1) the trigger: one remove, both objects flip in the same cascade round.
        g.apply(REG14_CHAIN, 'remove')

        # (2) structural: no residue may reference a node that no longer exists.
        assert g.dangling_residue_ids() == [], \
            'a residue references a deleted node -- _gc_subject_node collected a node ' \
            'a live residue still records (the N3 elision blinded its guard)'

        # (3) the runtime detector: I6 owns exactly this corruption class.
        check_invariants(g.session, 'reg14', g.rs.schema_info)

        # (4) the observable escalation: SQLite recycles the freed rowid onto the next
        #     interned node, and the stale upos entry would then vouch for it.
        g.apply(REG14_RECYCLE, 'add')
        assert g.widx.check(*REG14_QUERY) is oracle.check(*REG14_QUERY), \
            'check disagrees with the oracle after the rowid recycle -- a stale residue ' \
            'upos id is vouching for an unrelated principal (authorization escalation)'
    finally:
        g.session.close()


def test_reg14_paranoia_mode_survives_the_same_sequence():
    """(14, control) The same sequence with paranoia ON: the in-commit invariant
    checker must not fire. Pre-fix this aborts the removing transaction instead of
    silently corrupting -- both outcomes are bugs, so pin the clean one."""
    g = _Harness(REG14_SCHEMA, paranoia=True)
    try:
        for raw in REG14_SETUP:
            g.apply(raw, 'add')
        g.apply(REG14_CHAIN, 'remove')
        g.apply(REG14_RECYCLE, 'add')
        g.proc.audit_fixpoint()
    finally:
        g.session.close()


def test_reg14_keys_referencing_finds_closure_leaf_recordings():
    """(14, mechanism) Pin the FIX ITSELF, not just its symptom.
    ``_keys_referencing`` is the GC guard's only informant: it MUST report every residue
    that records a node id, on every schema. Here the recording object (``doc:y``) is
    reached only transitively, so a leaf-kind elision that assumes closure recordings
    are edge-justified on the recording object answers ``[]`` -- and this fails BEFORE
    the escalation can silently re-open."""
    rs = parse_openfga_schema(REG14_SCHEMA, enable_boolean=True)
    kinds = {spec.kind for plan in rs.compiled.plans.values() for spec in plan.leaves}
    assert kinds == {'closure'}, f'schema drifted; reg14 needs closure-only leaves: {kinds}'

    g = _Harness(REG14_SCHEMA, paranoia=False)
    try:
        for raw in REG14_SETUP:
            g.apply(raw, 'add')
        # group:g1#member holds NO edge on doc:x / doc:y -- it reaches them only through
        # group:g2#member -- yet both residues record it (the transitive-closure
        # resolution in _leaf_concretes(kind='closure')).
        chain_node = g.widx.idx.cached_concrete_node('member', 'group', 'g1')
        assert chain_node is not None
        recorded_on = {
            (obj.type, r.relation, obj.name)
            for r in g.session.exec(
                select(ResidueV1).where(ResidueV1.store_id == 'reg14')).all()
            for obj in [g.session.get(NodeV4, r.object_node_id)]
            if chain_node.id in json.loads(r.upos) or chain_node.id in json.loads(r.neg)
        }
        assert recorded_on == {('doc', 'a', 'x'), ('doc', 'a', 'y')}, \
            f'reg14 premise drifted -- expected both objects to record it: {recorded_on}'
        assert set(g.proc._keys_referencing(chain_node.id)) == recorded_on, \
            'the GC guard is blind to residue recordings it must protect'
        # And a genuinely unreferenced id still answers [] (the scan is real, not stubbed).
        assert g.proc._keys_referencing(-1) == []
    finally:
        g.session.close()


def test_reg14_cheap_path_self_heals_a_missing_userset_node():
    """(14, second barrier / ZT-P0-2) The cheap path's ``s_node is None`` skip was the
    proximate leak: reconciling BY NAME cannot prune an id whose node is gone, so it
    silently no-opped and left the stale id behind. It now escalates to the full-object
    reconcile, which recomputes neg/upos wholesale from live candidates.

    Driven by deleting the node behind the residue's back -- the state the GC guard now
    prevents, but which ``ReachabilityIndex.remove_node`` (an admin API the processor
    does not own) can still create."""
    g = _Harness(REG14_SCHEMA, paranoia=False)
    try:
        for raw in REG14_SETUP:
            g.apply(raw, 'add')
        chain_node = g.widx.idx.cached_concrete_node('member', 'group', 'g1')
        assert chain_node is not None
        nid = chain_node.id
        assert ('doc', 'a', 'y') in set(g.proc._keys_referencing(nid))

        # Forcibly drop the node, leaving both residues holding a now-dead id.
        g.widx.idx._evict_node(chain_node)
        g.session.delete(chain_node)
        g.session.flush()
        assert g.dangling_residue_ids(), 'setup: the id must be dangling before the heal'

        # The cheap path for that very subject must now heal the key it is given.
        g.proc.reconcile_subject('doc', 'a', 'y', ('member', 'group', 'g1'))
        remaining = [b for b in g.dangling_residue_ids() if b[1] == ('doc', 'y')]
        assert remaining == [], f'the stale id survived the reconcile: {remaining}'
    finally:
        g.session.close()


if __name__ == '__main__':          # pragma: no cover
    pytest.main([__file__, '-q'])
