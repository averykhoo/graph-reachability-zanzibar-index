"""
P4: the delta processor, driven directly on the graph backend (boolean spec §5, §10).

Named scenarios from §10 that exercise the processor without the P5 read path --
assertions go through the processor's own derived_check (the §6 edge+residue
semantics) and raw residue/edge state. Every scenario ends with the I9 fixpoint audit:
a second reconcile of every live key must change nothing.
"""

import pytest
from sqlmodel import select

from zanzibar.graphindex import Edge
from zanzibar.graphindex.models import Residue
from zanzibar.graphindex.outbox import outbox_watermark
from zanzibar.graphindex.processor import DeltaProcessor
from zanzibar.graphindex.invariants import snapshot_rows
from zanzibar.schema import Entity, RelationalTriple, parse_openfga_schema
from tests.wildcard_helpers import make_wildcard_index


def build(schema, object_wc=frozenset()):
    rs = parse_openfga_schema(schema, object_wildcard_shapes=object_wc, enable_boolean=True)
    session, widx = make_wildcard_index(rs.schema_info)
    proc = DeltaProcessor(widx, rs.compiled)

    def write(op, raw):
        """One synchronous v1 logical write: route the raw tuple, run the cascade,
        commit -- all one transaction."""
        wm = outbox_watermark(session, 'test')
        sp = Ellipsis if raw[0] == '...' else raw[0]
        triple = RelationalTriple(Entity(raw[1], raw[2]), raw[3], Entity(raw[4], raw[5]), sp)
        fn = widx.add_tuple if op == 'add' else widx.remove_tuple
        for d in rs.apply(triple):
            fn('...' if d.subject_predicate is Ellipsis else d.subject_predicate,
               d.subject.type, d.subject.name, d.relation, d.object.type, d.object.name)
        proc.run_cascade(wm)
        session.commit()

    return session, widx, proc, write


def _residues(session):
    return {r.relation: (r.stars, r.neg, r.version)
            for r in session.exec(select(Residue)).all()}


# ---------------------------------------------------------------------------
# §10: test_symbolic_flip_reconciles_concretes -- BOTH polarities
# ---------------------------------------------------------------------------

_SYMBOLIC = '''
    type user
    type doc
      relations
        define editor: [user]
        define blocked: [user, user:*]
        define public: [user, user:*]
        define viewer: editor but not blocked
        define restricted: editor and public
'''


def test_symbolic_flip_reconciles_concretes_exclusion():
    """§5.4's own example: bob holds a concrete editor tuple and a derived viewer
    edge; adding [user:*] to blocked produces NO concrete delta for bob, yet must
    revoke his edge (the symbolic full-object rule)."""
    session, widx, proc, write = build(_SYMBOLIC)
    write('add', ('...', 'user', 'bob', 'editor', 'doc', 'd1'))
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'bob')) is True

    write('add', ('...', 'user', '*', 'blocked', 'doc', 'd1'))     # symbolic, no bob delta
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'bob')) is False
    # and the edge itself is gone, not just masked
    assert not [e for e in session.exec(select(Edge)).all() if e.derived]

    # removal flips him back
    write('remove', ('...', 'user', '*', 'blocked', 'doc', 'd1'))
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'bob')) is True

    proc.audit_fixpoint()
    session.close()


def test_symbolic_flip_reconciles_concretes_intersection():
    """Mirrored for intersections: bob's membership appears when the symbolic side
    arrives and disappears when it leaves -- again with no concrete delta for bob."""
    session, widx, proc, write = build(_SYMBOLIC)
    write('add', ('...', 'user', 'bob', 'editor', 'doc', 'd1'))
    assert proc.derived_check('doc', 'restricted', 'd1', ('...', 'user', 'bob')) is False

    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
    assert proc.derived_check('doc', 'restricted', 'd1', ('...', 'user', 'bob')) is True

    write('remove', ('...', 'user', '*', 'public', 'doc', 'd1'))
    assert proc.derived_check('doc', 'restricted', 'd1', ('...', 'user', 'bob')) is False

    proc.audit_fixpoint()
    session.close()


# ---------------------------------------------------------------------------
# §10: star-minus-concrete residues vs ghost and '*' subjects
# ---------------------------------------------------------------------------

def test_star_minus_concrete_residue_ghost_and_star():
    session, widx, proc, write = build('''
        type user
        type doc
          relations
            define public: [user:*]
            define blocked: [user]
            define viewer: public but not blocked
    ''')
    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
    write('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd1'))

    # ghosts ride the star; alice is negated; the '*' query is intensional
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'ghost')) is True
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'alice')) is False
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', '*')) is True

    # the residue is exactly (stars={user bare}, neg={alice})
    row = session.exec(select(Residue)).one()
    assert row.relation == 'viewer'
    assert row.stars == '[["user", "..."]]'
    alice = widx.idx.node('...', 'user', 'alice', create_if_missing=False)
    assert row.neg == f'[{alice.id}]'

    # concrete-only exclusions never defeat star queries (§7)
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', '*')) is True

    proc.audit_fixpoint()
    session.close()


# ---------------------------------------------------------------------------
# §10: [user] but not [user:*] ⇒ empty relation, empty residue
# ---------------------------------------------------------------------------

def test_user_but_not_user_star_is_empty():
    session, widx, proc, write = build('''
        type user
        type doc
          relations
            define viewer: [user] but not [user:*]
    ''')
    write('add', ('...', 'user', 'alice', 'viewer', 'doc', 'd1'))
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'alice')) is True

    write('add', ('...', 'user', '*', 'viewer', 'doc', 'd1'))
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'alice')) is False
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'ghost')) is False
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', '*')) is False
    assert session.exec(select(Residue)).all() == []          # empty residue
    assert not [e for e in session.exec(select(Edge)).all() if e.derived]

    proc.audit_fixpoint()
    session.close()


def test_intersection_with_empty_branch():
    session, widx, proc, write = build(_SYMBOLIC)
    write('add', ('...', 'user', 'alice', 'editor', 'doc', 'd1'))
    # public branch empty: intersection yields nothing
    assert proc.derived_check('doc', 'restricted', 'd1', ('...', 'user', 'alice')) is False
    assert proc.derived_check('doc', 'restricted', 'd1', ('...', 'user', '*')) is False
    proc.audit_fixpoint()
    session.close()


# ---------------------------------------------------------------------------
# §10: a leaf flip cascading two strata
# ---------------------------------------------------------------------------

_TWO_STRATA = '''
    type user
    type doc
      relations
        define public: [user:*]
        define blocked: [user]
        define editor: [user]
        define admin: [user]
        define muted: [user]
        define viewer: (public but not blocked) or editor
        define approver: viewer or admin
        define auditor: approver but not muted
'''


def test_leaf_flip_cascades_two_strata():
    session, widx, proc, write = build(_TWO_STRATA)
    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))

    # ghost rides stars up the whole chain
    for rel in ('viewer', 'approver', 'auditor'):
        assert proc.derived_check('doc', rel, 'd1', ('...', 'user', 'ghost')) is True, rel

    # blocking alice cascades: viewer(stratum0) -> approver(1) -> auditor(2)
    write('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd1'))
    for rel in ('viewer', 'approver', 'auditor'):
        assert proc.derived_check('doc', rel, 'd1', ('...', 'user', 'alice')) is False, rel
        assert proc.derived_check('doc', rel, 'd1', ('...', 'user', 'ghost')) is True, rel

    # unblocking flows back up
    write('remove', ('...', 'user', 'alice', 'blocked', 'doc', 'd1'))
    for rel in ('viewer', 'approver', 'auditor'):
        assert proc.derived_check('doc', rel, 'd1', ('...', 'user', 'alice')) is True, rel

    # muting stops the top stratum only
    write('add', ('...', 'user', 'alice', 'muted', 'doc', 'd1'))
    assert proc.derived_check('doc', 'approver', 'd1', ('...', 'user', 'alice')) is True
    assert proc.derived_check('doc', 'auditor', 'd1', ('...', 'user', 'alice')) is False

    proc.audit_fixpoint()
    session.close()


def test_removing_last_positive_leaf_revokes_downstream():
    session, widx, proc, write = build(_TWO_STRATA)
    write('add', ('...', 'user', 'alice', 'admin', 'doc', 'd1'))
    assert proc.derived_check('doc', 'approver', 'd1', ('...', 'user', 'alice')) is True
    assert proc.derived_check('doc', 'auditor', 'd1', ('...', 'user', 'alice')) is True

    write('remove', ('...', 'user', 'alice', 'admin', 'doc', 'd1'))
    assert proc.derived_check('doc', 'approver', 'd1', ('...', 'user', 'alice')) is False
    assert proc.derived_check('doc', 'auditor', 'd1', ('...', 'user', 'alice')) is False
    assert not [e for e in session.exec(select(Edge)).all() if e.derived]

    proc.audit_fixpoint()
    session.close()


# ---------------------------------------------------------------------------
# §10: interleaved add/remove order-independence
# ---------------------------------------------------------------------------

def test_interleaved_order_independence():
    """A sequence and its shuffle reach the identical end state (row multiset, ids
    ignored, residues included)."""
    ops_a = [
        ('add', ('...', 'user', '*', 'public', 'doc', 'd1')),
        ('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd1')),
        ('add', ('...', 'user', 'bob', 'editor', 'doc', 'd1')),
        ('add', ('...', 'user', 'alice', 'editor', 'doc', 'd1')),
        ('remove', ('...', 'user', 'bob', 'editor', 'doc', 'd1')),
        ('add', ('...', 'user', 'bob', 'muted', 'doc', 'd1')),
    ]
    # a permutation of the same surviving multiset
    ops_b = [
        ('add', ('...', 'user', 'bob', 'muted', 'doc', 'd1')),
        ('add', ('...', 'user', 'alice', 'editor', 'doc', 'd1')),
        ('add', ('...', 'user', 'bob', 'editor', 'doc', 'd1')),
        ('add', ('...', 'user', 'alice', 'blocked', 'doc', 'd1')),
        ('remove', ('...', 'user', 'bob', 'editor', 'doc', 'd1')),
        ('add', ('...', 'user', '*', 'public', 'doc', 'd1')),
    ]

    states = []
    for ops in (ops_a, ops_b):
        session, widx, proc, write = build(_TWO_STRATA)
        for op, raw in ops:
            write(op, raw)
        proc.audit_fixpoint()
        nodes, edges = snapshot_rows(session, 'test')
        # neg ids are order-dependent surrogates; compare by node identity
        residues = {(r.relation, r.stars, frozenset(_neg_names(session, widx, r)))
                    for r in session.exec(select(Residue)).all()}
        states.append((nodes, edges, residues))
        session.close()

    assert states[0] == states[1]


def _neg_names(session, widx, row):
    import json
    from zanzibar.graphindex import Node
    out = []
    for nid in json.loads(row.neg):
        n = session.get(Node, nid)
        assert n is not None, f'residue neg holds a dead node id {nid} (I6)'
        out.append((n.predicate, n.type, n.name))
    return out


# ---------------------------------------------------------------------------
# demorgans_law_1's star-minus-concrete residue
# ---------------------------------------------------------------------------

def test_demorgans_law_1_star_minus_concrete_residue(load_fga_schema):
    """`non_labels = _all_attrs but not labels`: the residue algebra over a star minus a
    concrete member.

    Until 2026-09-26 this was `test_derived_tupleset_ttu_chain`, which also drove the
    fixture's `from` chain (`unmatchable_conds: required_by from non_labels` and two more)
    and pinned it CONSTANTLY EMPTY: no tuple can be stored on a tupleset with no Direct
    restriction, so `from` found no parent even when `non_labels` had computed members.
    That silent emptiness is what TK106 (user decision) refuses: a non-direct tupleset is
    now a parse refusal, the chain was trimmed from the fixture, and the refusal is pinned
    in `tests/test_tupleset_must_be_direct.py`."""
    session, widx, proc, write = build(load_fga_schema('demorgans_law_1.fga'))

    write('add', ('...', 'attr', '*', '_all_attrs', 'doc', 'd'))
    write('add', ('...', 'attr', 'a1', 'labels', 'doc', 'd'))

    # non_labels(d): all attrs but a1 (star-minus-concrete residue)
    assert proc.derived_check('doc', 'non_labels', 'd', ('...', 'attr', 'a2')) is True
    assert proc.derived_check('doc', 'non_labels', 'd', ('...', 'attr', 'a1')) is False
    assert proc.derived_check('doc', 'non_labels', 'd', ('...', 'attr', 'ghost')) is True

    proc.audit_fixpoint()
    session.close()


def test_derived_tupleset_with_stored_tuples_is_refused():
    """A derived tupleset WITH Direct restrictions (`linked: [folder] but not banned`).

    Until 2026-09-26 this was `test_derived_tupleset_ttu_with_stored_tuples`, and it
    pinned that banning f2 does NOT stop `owner from linked` walking the stored f2 link:
    `from` reads stored tuples, so the `but not banned` arm was silently ignored. That is
    exactly the behaviour TK106 (user decision, as OpenFGA does) refuses, so the schema is
    now a parse refusal. The behaviour-preserving rewrite (`linked_link: [folder]`, used
    by the `from`) is pinned in `tests/test_tupleset_must_be_direct.py`."""
    with pytest.raises(ValueError, match='tupleset must be direct'):
        build('''
            type user
            type folder
              relations
                define banned: [folder]
                define linked: [folder] but not banned
                define owner: [user]
                define reachable_owner: owner from linked
            type doc
        ''')


# ---------------------------------------------------------------------------
# Frozen hypothesis counterexample (P8 deep run): add-then-remove must restore
# the exact row multiset -- the pinned derived-public node used to leak.
# ---------------------------------------------------------------------------

def test_regression_public_node_gc_on_add_remove():
    """Shrunk by hypothesis: `r4 = (r0 from parent) or ([user] and [user])` with a
    self-parent tuple. The pure TTU subtree is a rule-routed leaf, so the parent
    write creates a userset-subject leaf edge, eval flips true, and the processor
    writes a derived edge -- pinning the public node non-implicit. Removing the
    tuple retired the edge but leaked the empty pinned node; the processor now GCs
    its public node once neither residue nor edges remain."""
    schema = '''
        type user
        type doc
          relations
            define parent: [doc]
            define r0: [user]
            define r4: (r0 from parent) or ([user] and [user])
    '''
    session, widx, proc, write = build(schema)
    before = snapshot_rows(session, 'test')

    write('add', ('...', 'doc', 'd1', 'parent', 'doc', 'd1'))
    assert proc.derived_check('doc', 'r4', 'd1', ('r0', 'doc', 'd1')) is True
    write('remove', ('...', 'doc', 'd1', 'parent', 'doc', 'd1'))

    assert snapshot_rows(session, 'test') == before
    proc.audit_fixpoint()
    session.close()


# ---------------------------------------------------------------------------
# Frozen external-review finding: tainted userset restrictions ([T#P] with P
# derived) -- the whole PDerivedUserset path, previously unexercised.
# ---------------------------------------------------------------------------

_TAINTED_USERSET = '''
    type user
    type group
      relations
        define gblocked: [user]
        define member: [user] but not gblocked
    type doc
      relations
        define banned: [group#member]
        define viewer: [user] but not banned
'''


def test_regression_tainted_userset_full_reconcile():
    """_find_leaf_node only knew TTU leaves: a FULL reconcile of any plan holding a
    derived-userset leaf (here banned = [group#member], member tainted) crashed with
    'plan node not found'. The cheap per-subject path masked it -- audit_fixpoint
    (or any symbolic/dependency invalidation) was the trigger."""
    session, widx, proc, write = build(_TAINTED_USERSET)
    write('add', ('...', 'user', 'alice', 'viewer', 'doc', 'd1'))
    write('add', ('...', 'user', 'alice', 'member', 'group', 'g1'))
    write('add', ('member', 'group', 'g1', 'banned', 'doc', 'd1'))

    proc.audit_fixpoint()                       # used to crash right here
    session.close()


def test_tainted_userset_end_to_end_vs_oracle():
    """The full chain: membership through a DERIVED userset feeds an exclusion two
    relations up, invalidations flow both ways, and every answer matches the oracle."""
    from tests.oracle import Oracle, OracleTuple

    session, widx, proc, write = build(_TAINTED_USERSET)
    present = []

    def w(op, raw):
        write(op, raw)
        if op == 'add':
            present.append(raw)
        else:
            present.remove(raw)

    w('add', ('...', 'user', 'alice', 'viewer', 'doc', 'd1'))
    w('add', ('...', 'user', 'bob', 'viewer', 'doc', 'd1'))
    w('add', ('...', 'user', 'alice', 'member', 'group', 'g1'))
    w('add', ('member', 'group', 'g1', 'banned', 'doc', 'd1'))

    grid = [('...', 'user', sn, rel, ot, on)
            for sn in ('alice', 'bob', 'ghost')
            for (rel, ot, on) in [('viewer', 'doc', 'd1'), ('banned', 'doc', 'd1'),
                                  ('member', 'group', 'g1')]]

    def compare(tag):
        oracle = Oracle(_TAINTED_USERSET, [OracleTuple(*r) for r in present])
        for q in grid:
            got = widx.check(*q)
            exp = oracle.check(*q)
            assert got == exp, f'{tag}: {q} graph={got} oracle={exp}'
        proc.audit_fixpoint()

    compare('after setup')                       # alice banned via g1; bob still viewer

    # gblock alice inside the group: she leaves member(g1), hence leaves banned,
    # hence RE-GAINS viewer -- a three-relation invalidation chain
    w('add', ('...', 'user', 'alice', 'gblocked', 'group', 'g1'))
    compare('after gblock')

    w('remove', ('...', 'user', 'alice', 'gblocked', 'group', 'g1'))
    compare('after ungblock')                    # banned again

    w('remove', ('member', 'group', 'g1', 'banned', 'doc', 'd1'))
    compare('after unban')                       # stored userset tuple retired
    session.close()


# ---------------------------------------------------------------------------
# boolean_wildcards.fga driven end-to-end at the processor level
# ---------------------------------------------------------------------------

def test_boolean_wildcards_fixture_processor(load_fga_schema):
    session, widx, proc, write = build(load_fga_schema('boolean_wildcards.fga'))

    write('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
    write('add', ('...', 'user', 'u1', 'blocked', 'doc', 'd1'))
    write('add', ('...', 'user', 'u2', 'editor', 'doc', 'd1'))
    write('add', ('...', 'user', 'u1', 'member', 'group', 'g1'))
    write('add', ('member', 'group', 'g1', 'editor', 'doc', 'd1'))
    write('add', ('...', 'doc', 'd1', 'parent', 'doc', 'd2'))

    # viewer = (public but not blocked) or editor
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'u2')) is True     # editor arm
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'u1')) is True     # blocked BUT editor via group
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'ghost')) is True  # star arm
    # restricted = editor and public
    assert proc.derived_check('doc', 'restricted', 'd1', ('...', 'user', 'u2')) is True
    assert proc.derived_check('doc', 'restricted', 'd1', ('...', 'user', 'ghost')) is False
    # inherited = viewer from parent: d2 inherits d1's viewers
    assert proc.derived_check('doc', 'inherited', 'd2', ('...', 'user', 'u2')) is True
    assert proc.derived_check('doc', 'inherited', 'd2', ('...', 'user', 'ghost')) is True
    assert proc.derived_check('doc', 'inherited', 'd1', ('...', 'user', 'u2')) is False

    # removing u1's group membership: still a viewer? u1 is blocked and loses editor
    write('remove', ('...', 'user', 'u1', 'member', 'group', 'g1'))
    assert proc.derived_check('doc', 'viewer', 'd1', ('...', 'user', 'u1')) is False

    proc.audit_fixpoint()
    session.close()
