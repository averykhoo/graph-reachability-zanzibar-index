"""reg18 (board BL-2, deviations 2026-08-21b): a minted LEAF PREDICATE name must be
DENIED on every read surface -- False / empty, never a grant, never a raise.

The compiler mints one leaf family per operand of a boolean relation (`<rel>.<idx>`;
boolean spec §3.3), and ``RuleSet.apply`` routes every PUBLIC write onto those leaf
families at WRITE time -- so `user:alice editor doc:d1` alone materializes a real
`(doc, viewer.0, d1)` node under `viewer: editor but not banned`. Writes naming a leaf
are fenced (``AdmissionRejected``, pinned by test_admission_rejected.py), but the READ
path routed derived queries by ``derived_families`` membership only: a leaf family is
not a derived family, so a leaf-name query fell through to the ordinary edge probe and
FOUND the routed write's node. Literal failure output observed on this tree,
2026-08-21, before the fix (the repro pin):

    AssertionError: BL-2 leak: check(user:alice, 'viewer.0', doc:d1) is True on the
    graph index -- the caller just read an operand of 'viewer: editor but not
    banned' with the boolean guard unapplied (set engines and oracle answer False)

and, worse, the enumeration form handed out the whole negative-operand set
(observed via lookup_reverse on the same tree, alice editor + bob/carol banned):

    viewer.0 -> [('user', 'alice', '...')] markers= set() excluded= set()
    viewer.1 -> [('user', 'bob', '...'), ('user', 'carol', '...')] markers= set() excluded= set()

Adjudicated semantics (user call, 2026-08-21 -- do not relitigate): DENY, do NOT
raise. It matches the set engine, the oracle, and the junk-name case (`foo.bar`), and
keeps reads lenient per the documented contract ("an out-of-charset name just never
matches"). The lenient-read controls below pin the not-raise half so a future fix
cannot swap the deny for an exception.

House rules honoured here:
  * every leaf name is DERIVED from ``compiled.leaf_families`` -- never hand-written
    (the pattern of test_admission_rejected.test_raw_write_to_a_leaf_predicate_...);
  * each denial pin carries an ANTI-VACUITY control: the materialized leaf node is
    asserted to EXIST in the store first, so a passing pin means "denied despite
    materialization", not "False on an empty store";
  * positive pins, no xfails (CLAUDE.md: a divergence gets a positive pin).

The lookup-surface pins (reverse-at-a-leaf-name is empty; forward lookup surfaces no
leaf-family node ids) live HERE rather than in test_lookup_oracle.py's X-series: the
X-series inventories divergences found BY that gate, and BL-2 was invisible to it --
its grids contain only declared relations, and its G2 forward sweep carried a
tolerated skip for leaf-pred nodes. That skip is now tightened into a positive
assertion over there (mirroring the G4 reverse assertion); this module keeps the
deterministic minimal repro.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from connectedstore import ConnectedStore
from setengine import ALL_SETOPS
from tests.oracle import Oracle, OracleTuple
from tests.parity import GHOST_NAME, _GraphSide, _SetSide
from tests.test_processor import build
from zanzibar_utils_v1 import parse_openfga_schema

SCHEMA = """
type user
type doc
  relations
    define editor: [user]
    define banned: [user]
    define viewer: editor but not banned
"""


def _leaf_families():
    """The compiler-minted (object_type, leaf_predicate) pairs -- THE derivation
    seam. Never hand-write a leaf name like 'viewer.0': the numbering is a compiler
    artifact and hand-written names would silently pin nothing if it changed."""
    fams = sorted(parse_openfga_schema(SCHEMA).compiled.leaf_families)
    assert fams, 'the boolean schema minted no leaf families -- every pin here vacuous'
    return fams


def _node_exists(widx, pred, o_type, o_name):
    try:
        widx.idx.node(pred, o_type, o_name, create_if_missing=False)
        return True
    except KeyError:
        return False


# --------------------------------------------------------------------------- #
# 1. THE REPRO PIN: denied DESPITE the materialized leaf node
# --------------------------------------------------------------------------- #

def test_check_at_a_leaf_name_is_denied_despite_the_materialized_node():
    """The write fan-out is the point: writing `editor` ALONE (the leak never needed
    `viewer` to be true) materializes the positive leaf node, and the leaf-name query
    must STILL answer False while the public name answers True.

    Anti-vacuity control: the leaf node's EXISTENCE is asserted before the denial.
    Without it this pin would also pass on an empty store, i.e. it would stop
    distinguishing "denied despite materialization" from "nothing there to leak".

    SABOTAGE EVIDENCE (2026-08-21, legs S1/S3; each restore verified byte-identical
    via git hash-object):
      * S1 -- the fence's set swapped to `derived_families` (one-token, still
        compiles, branch still runs). Module: `3 failed, 3 passed in 0.63s` -- this
        pin red at the PUBLIC-name control (the swapped fence denies public derived
        reads too: `AssertionError: assert False is True` at the viewer check), the
        leak itself reopening in the grid pin below:
            AssertionError: graph grants leaf-name query
            ('...', 'user', 'alice', 'viewer.0', 'doc', 'd1')
        test_matrix.py `7 failed, 5 passed` (`boolean check disagreement seed=0
        q=('...', 'user', 'u1', 'viewer.1', 'doc', 'd1'): {'graph': True,
        'connected': True, 'oracle': False, 'set:py': False, 'set:roaring': False}`),
        and ParityEngine grid parity red at tests/parity.py::_assert_grid_parity
        (`q=('...', 'user', 'alice', 'both.0', 'folder', 'child') graph=True
        oracle=False`) -- while the scope meta-pin
        (test_parity_grid_covers_every_leaf_family_even_under_a_tiny_cap) stayed
        GREEN (`1 passed`), so the red points at the FIX, not the instrument.
      * S3 -- the routed write replaced with a bare
        `widx.add_tuple('...', 'user', 'alice', 'editor', 'doc', 'd1')` (no
        fan-out; probed 2026-08-21: ROUTING materializes the leaf node, the cascade
        does not). The anti-vacuity control went red ALONE (`1 failed, 5 passed in
        0.61s`):
            AssertionError: anti-vacuity control failed: RuleSet.apply routes a
            public editor write onto a leaf family at WRITE time, so a materialized
            leaf node for doc:d1 must exist -- without it every False below is
            vacuous
        proving the pin tests deny-DESPITE-materialization, not an empty store."""
    session, widx, proc, write = build(SCHEMA)
    try:
        write('add', ('...', 'user', 'alice', 'editor', 'doc', 'd1'))

        leaves = _leaf_families()
        # the facade handle (the fix's routing input) agrees with the compiler
        assert sorted(widx.schema_info.leaf_families) == leaves

        materialized = [(t, leaf) for (t, leaf) in leaves
                        if _node_exists(widx, leaf, t, 'd1')]
        assert materialized, (
            'anti-vacuity control failed: RuleSet.apply routes a public editor write '
            'onto a leaf family at WRITE time, so a materialized leaf node for doc:d1 '
            'must exist -- without it every False below is vacuous')

        # control: the PUBLIC relation still grants (alice is editor, not banned)
        assert widx.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True

        for (o_type, leaf) in leaves:
            assert widx.check('...', 'user', 'alice', leaf, o_type, 'd1') is False, (
                f"BL-2 leak: check(user:alice, {leaf!r}, doc:d1) is True on the graph "
                f"index -- the caller just read an operand of 'viewer: editor but not "
                f"banned' with the boolean guard unapplied (set engines and oracle "
                f"answer False)")
    finally:
        session.close()


# --------------------------------------------------------------------------- #
# 2. FULL LEAF-FAMILY PARITY: graph == both set engines == oracle == False
# --------------------------------------------------------------------------- #

def test_leaf_family_grid_is_unanimously_false_across_all_backends():
    """Every (o_type, leaf) x subject-grid x object-grid cell: all four backends
    answer False. The grid includes a subject in the positive operand (alice), two in
    the negative operand (bob, carol), one in BOTH (erin), a ghost, and the star
    sentinel; objects include a live one and a ghost. Blast-radius measurement
    (2026-08-21, 1,728 target-position comparisons over 9 tainted fixtures): every
    divergence had signature oracle=False graph=True sets=[False,False], residual
    under DENY = 0 -- so this parity pin reddens nothing but the leak itself."""
    rs = parse_openfga_schema(SCHEMA)
    graph = _GraphSide(rs, paranoia=True)
    sets = [_SetSide(SCHEMA, frozenset(), ops) for ops in ALL_SETOPS]
    writes = [('...', 'user', 'alice', 'editor', 'doc', 'd1'),
              ('...', 'user', 'bob', 'banned', 'doc', 'd1'),
              ('...', 'user', 'carol', 'banned', 'doc', 'd1'),
              ('...', 'user', 'erin', 'editor', 'doc', 'd1'),
              ('...', 'user', 'erin', 'banned', 'doc', 'd1')]
    try:
        for raw in writes:
            assert graph.apply(raw, 'add') is True
            for side in sets:
                assert side.apply(raw, 'add') is True
        oracle = Oracle(SCHEMA, [OracleTuple(*raw) for raw in writes])

        subjects = [('...', 'user', n)
                    for n in ('alice', 'bob', 'carol', 'erin', GHOST_NAME, '*')]
        objects = ['d1', GHOST_NAME]

        # anti-vacuity: the routed writes materialized every leaf family for d1
        for (o_type, leaf) in rs.compiled.leaf_families:
            assert _node_exists(graph.widx, leaf, o_type, 'd1'), (
                f'anti-vacuity: no ({o_type}, {leaf}, d1) node -- the grid below '
                f'would be probing an empty store')

        for (o_type, leaf) in sorted(rs.compiled.leaf_families):
            for o_name in objects:
                for (sp, s_type, s_name) in subjects:
                    q = (sp, s_type, s_name, leaf, o_type, o_name)
                    assert oracle.check(*q) is False, (
                        f'oracle unexpectedly grants leaf-name query {q} -- the '
                        f'expectation derivation itself is broken')
                    answers = [('graph', graph.widx.check(*q))]
                    answers += [(side.name, side.se.check(*q)) for side in sets]
                    for backend, got in answers:
                        assert got is False, (
                            f'{backend} grants leaf-name query {q} '
                            f'(oracle and every other backend: False)')
    finally:
        graph.close()
        for side in sets:
            side.close()


# --------------------------------------------------------------------------- #
# 3. LENIENT-READ CONTROLS: DENY means False, never a raise
# --------------------------------------------------------------------------- #

def test_junk_and_ghost_dotted_names_are_false_everywhere_and_raise_nothing():
    """The adjudication is DENY-not-raise. These controls make the not-raise half
    load-bearing: a fix that pattern-matched dots and RAISED (the tempting blanket
    guard) fails here. Two shapes:

      * 'foo.bar'      -- a dotted name over a relation stem the schema never had;
      * '<rel>.99'     -- a GHOST leaf: the real derived relation's stem with an
                          index the compiler never minted (asserted below), so it
                          exercises the near-miss path a naive prefix guard would
                          route into the derived machinery.

    Both must answer False on the graph, both set engines, the oracle AND the
    composed ConnectedStore, with nothing raised (a raise fails the test naturally).
    NOTE these controls pass on the UNFIXED tree too -- they are the boundary of the
    fix, pinned so the deny cannot overshoot into an exception or a KeyError."""
    leaves = _leaf_families()
    rs = parse_openfga_schema(SCHEMA)
    derived = sorted(rs.compiled.derived_families)
    assert derived, 'no derived family -- the ghost-leaf derivation below is vacuous'
    o_type, rel = derived[0]
    ghost_leaf = f'{rel}.99'
    assert (o_type, ghost_leaf) not in rs.compiled.leaf_families, (
        'the ghost leaf collided with a real minted leaf; pick a higher index')

    session, widx, proc, write = build(SCHEMA)
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    cs_session = Session(engine)
    cs = ConnectedStore(cs_session, 'cs', schema=SCHEMA)
    sets = [_SetSide(SCHEMA, frozenset(), ops) for ops in ALL_SETOPS]
    try:
        write('add', ('...', 'user', 'alice', 'editor', 'doc', 'd1'))
        cs.add_tuple('...', 'user', 'alice', 'editor', 'doc', 'd1')
        for side in sets:
            assert side.apply(('...', 'user', 'alice', 'editor', 'doc', 'd1'), 'add')
        oracle = Oracle(SCHEMA, [OracleTuple('...', 'user', 'alice',
                                             'editor', 'doc', 'd1')])
        for name in ('foo.bar', ghost_leaf):
            q = ('...', 'user', 'alice', name, o_type, 'd1')
            assert widx.check(*q) is False
            assert cs.check(*q) is False
            assert oracle.check(*q) is False
            for side in sets:
                assert side.se.check(*q) is False, f'{side.name} grants {q}'
            # the enumeration surfaces are equally lenient: empty, no raise
            res = widx.lookup_reverse(name, o_type, 'd1')
            assert (res.node_ids, res.markers, res.excluded_node_ids) \
                == (set(), set(), set())
        assert leaves, 'control: the real leaves still exist beside the ghosts'
    finally:
        session.close()
        cs_session.close()
        for side in sets:
            side.close()


# --------------------------------------------------------------------------- #
# 4. THE COMPOSED SURFACE: ConnectedStore.check
# --------------------------------------------------------------------------- #

def test_connectedstore_check_at_a_leaf_name_is_false():
    """The composed system serves reads from the same facade, so the leak reached
    ConnectedStore.check verbatim. Same anti-vacuity discipline: the routed write's
    leaf node must exist in the composed store before the denial means anything."""
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    cs = ConnectedStore(session, 'cs', schema=SCHEMA)
    try:
        cs.add_tuple('...', 'user', 'alice', 'editor', 'doc', 'd1')

        leaves = _leaf_families()
        assert sorted(cs.widx.schema_info.leaf_families) == leaves
        assert any(_node_exists(cs.widx, leaf, t, 'd1') for (t, leaf) in leaves), (
            'anti-vacuity: the composed write path materialized no leaf node')

        assert cs.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True
        for (o_type, leaf) in leaves:
            assert cs.check('...', 'user', 'alice', leaf, o_type, 'd1') is False, (
                f'BL-2 through the composed surface: ConnectedStore.check grants '
                f'the leaf name {leaf!r}')
    finally:
        session.close()


# --------------------------------------------------------------------------- #
# 5. ENUMERATION FORM: lookup_reverse at a leaf name is EMPTY
# --------------------------------------------------------------------------- #

def test_lookup_reverse_at_a_leaf_name_returns_empty():
    """The worst form of the leak: lookup_reverse at the NEGATIVE leaf enumerated
    the entire banned set. Literal output observed on the unfixed tree (2026-08-21,
    alice editor + bob/carol banned on doc:d1, resolved node ids rendered):

        viewer.0 -> [('user', 'alice', '...')] markers= set() excluded= set()
        viewer.1 -> [('user', 'bob', '...'), ('user', 'carol', '...')] markers= set() excluded= set()

    Pinned empty across all three result components, for EVERY minted leaf, with a
    public-name control proving enumeration itself still works."""
    session, widx, proc, write = build(SCHEMA)
    try:
        write('add', ('...', 'user', 'alice', 'editor', 'doc', 'd1'))
        write('add', ('...', 'user', 'bob', 'banned', 'doc', 'd1'))
        write('add', ('...', 'user', 'carol', 'banned', 'doc', 'd1'))

        leaves = _leaf_families()
        for (o_type, leaf) in leaves:                    # anti-vacuity: nodes exist
            assert _node_exists(widx, leaf, o_type, 'd1'), (
                f'anti-vacuity: ({o_type}, {leaf}, d1) never materialized; an empty '
                f'reverse result below would prove nothing')

        # control: the PUBLIC surface still enumerates (alice is a viewer)
        alice = widx.idx.node('...', 'user', 'alice', create_if_missing=False)
        assert alice.id in widx.lookup_reverse('viewer', 'doc', 'd1').node_ids

        for (o_type, leaf) in leaves:
            res = widx.lookup_reverse(leaf, o_type, 'd1')
            leaked = sorted(
                (n.type, n.name, n.predicate)
                for n in (widx._node_by_id(nid) for nid in res.node_ids)
                if n is not None)
            assert (res.node_ids, res.markers, res.excluded_node_ids) \
                == (set(), set(), set()), (
                    f'BL-2 enumeration leak: lookup_reverse({leaf!r}, {o_type!r}, '
                    f"'d1') returned {leaked} + markers={res.markers} "
                    f'excluded={res.excluded_node_ids} -- a leaf-family operand set '
                    f'is storage-internal and must never be enumerable')
    finally:
        session.close()


# --------------------------------------------------------------------------- #
# 6. ENUMERATION FORM: forward lookup surfaces no leaf-family node ids
# --------------------------------------------------------------------------- #

def test_forward_lookup_does_not_surface_leaf_family_node_ids():
    """`lookup('...','user','alice')` walks the reachable set, and the routed write
    put a real edge alice -> (doc, <leaf>, d1) there, so the forward result carried
    the leaf-family node id -- the positive operand disclosed in list-objects form
    (and the subject need NOT hold the derived relation: a banned editor still
    reaches the positive leaf node). test_lookup_oracle's G2 sweep tolerated these
    as 'internal leaf-family storage node (documented)', which is exactly how BL-2
    stayed invisible; that skip is now a positive assertion there, and this is the
    deterministic minimal repro. Membership tested against the DERIVED leaf_families
    set, not a name pattern."""
    session, widx, proc, write = build(SCHEMA)
    try:
        write('add', ('...', 'user', 'alice', 'editor', 'doc', 'd1'))
        write('add', ('...', 'user', 'alice', 'banned', 'doc', 'd1'))  # not a viewer!

        leaves = set(_leaf_families())
        assert any(_node_exists(widx, leaf, t, 'd1') for (t, leaf) in leaves)

        res = widx.lookup('...', 'user', 'alice')
        surfaced = [widx._node_by_id(nid) for nid in res.node_ids]
        leaked = sorted((n.type, n.name, n.predicate) for n in surfaced
                        if n is not None and (n.type, n.predicate) in leaves)
        assert leaked == [], (
            f'BL-2 forward-enumeration leak: lookup(user:alice) surfaced internal '
            f'leaf-family node(s) {leaked} -- alice is banned, holds no viewer '
            f'grant, and just listed the positive operand of the exclusion')

        # control: the public editor grant is still enumerated
        editor_node = widx.idx.node('editor', 'doc', 'd1', create_if_missing=False)
        assert editor_node.id in res.node_ids
    finally:
        session.close()
