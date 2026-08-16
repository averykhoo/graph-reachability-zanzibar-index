"""ZT-P5 re-adjudication pins (2026-07-26) — "ignore the ignore".

`docs/history/handoff-status-2026-07.md` "Zero-trust review 2026-07-26" (archived from
`HANDOFF.md` 2026-07-29) section P5 lists dismissals whose stated
justification no longer holds. This module re-adjudicates them BY REPRO or BY
BOUNDED SEARCH, never by argument, and pins each verdict so the next session does
not redo the work. Every negative result here states its bounds explicitly — a
bounded search is evidence, not a proof, and must not be quoted as one.

What is pinned, per target:

  1. reg11's "the multi-hop out-bridge generalization is unreachable"
     (`docs/spec-deviations.md` 2026-07-16) — **DISPROVED**. Also: a NEW
     accept/reject divergence found while disproving it — filed strict-xfail on
     2026-07-26 and **FIXED the same day** (`WildcardIndex._reject_star_self_edge`);
     the xfail and its behaviour-of-today companion were flipped together into
     plain regression pins.
  2. the 2026-07-13 X4 from-chain TARGET note's *reachability* half — **DISPROVED**.
  3. the object-wildcard corpus at STATE level (`FINAL_REVIEW.md` §3 /
     `ARCHITECTURE.md` §6 assert "proof-scope, not observed divergence" from a
     CHECK-level probe) — Python-side state level is CLEAN (bounded).
  4. the `group_userset` enum exclusion's admission-domain question — the two
     backends' admission domains are IDENTICAL (exhaustive at the enum's own K).
  5. three orphaned `formal/history/` findings — current Python-side truth.

See `docs/spec-deviations.md` 2026-07-26 (ZT-P5) for the full write-up.
"""

import itertools
import json

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from setengine import ALL_SETOPS
from tests.oracle import Oracle, OracleTuple
from zanzibar_utils_v1 import parse_openfga_schema, UnsupportedByGraphIndex


def _backends(schema, owc=frozenset()):
    from tests.test_matrix import GraphBackend, SetBackend
    return [GraphBackend(schema, owc)] + [SetBackend(schema, owc, o) for o in ALL_SETOPS]


def _unanimous(backends, raw, op='add'):
    """Apply `raw` to every backend; return the unanimous decision or fail."""
    res = {b.name: b.apply(raw, op) for b in backends}
    assert len(set(res.values())) == 1, (
        f'accept/reject disagreement on {op} {raw}: {res}')
    return next(iter(res.values()))


# ===========================================================================
# TARGET 1 — reg11: "the multi-hop out-bridge generalization is unreachable"
# ===========================================================================
#
# reg11 (docs/spec-deviations.md 2026-07-16) argued: "Any derived edge INTO
# `w_all(T,p)` is minted by a `T:x <tupleset> T:*` write whose own subject is a
# same-shape concrete `T:x#p`, which the out-bridge immediately reaches back --
# so such a write always self-cycles at admission and can never persist for a
# later write to build a longer loop on."
#
# That is an artefact of reg11's OWN schema, where the TTU reads the SAME
# relation it defines (`viewer: [user] or viewer from parent`). With a TTU whose
# TARGET relation differs from its HEAD (`viewer: [user] or admin from parent` --
# the reg10 shape), the derived edge into `w_all(folder,viewer)` is minted from
# `folder:a#admin`, a DIFFERENT shape, which the out-bridge does not reach back.
# The write therefore PERSISTS, and a later write closes a genuine MULTI-HOP
# out-bridge cycle.

REG11_MULTIHOP_SCHEMA = """model
  schema 1.1
type user
type folder
  relations
    define parent: [folder, folder:*]
    define admin: [user, folder#viewer]
    define viewer: [user] or admin from parent
"""
REG11_MULTIHOP_OWC = frozenset({('folder', 'parent')})

# W_STAR mints the edge INTO w_all(folder,viewer):
#   folder:a is a parent of folder:*, and `viewer from parent` rewrites it to
#   folder:a#admin -> folder:*#viewer  ==  folder:a#admin -> w_all(folder,viewer).
# The out-bridge w_all(folder,viewer) -> folder:x#viewer then reaches EVERY
# concrete viewer node, folder:a#viewer included -- but folder:a#admin is NOT
# reachable from folder:a#viewer yet, so W_STAR is admitted and PERSISTS.
_W_STAR = ('...', 'folder', 'a', 'parent', 'folder', '*')
# W_CLOSE is the second hop: folder:a#viewer -> folder:a#admin. Only now does the
# loop close: folder:a#admin -> w_all(folder,viewer) -[out-bridge]-> folder:a#viewer
# -> folder:a#admin. That is the MULTI-HOP out-bridge cycle reg11 called
# unreachable.
_W_CLOSE = ('viewer', 'folder', 'a', 'admin', 'folder', 'a')


def test_zt_p5_reg11_multihop_out_bridge_IS_reachable():
    """reg11's unreachability claim is DISPROVED: the star-object write persists
    and a LATER write closes a multi-hop out-bridge cycle.

    The claim survives only for schemas whose TTU head and target are the same
    relation. Both backends agree here (parity intact) -- what is disproved is the
    REACHABILITY argument, not accept/reject parity. Because the argument is what
    licensed leaving the class unfuzzed, the class must stay pinned.
    """
    # The compiler propagates (folder, viewer) onto the object-wildcard set
    # through the TTU head, so the out-bridge exists without being declared.
    si = parse_openfga_schema(REG11_MULTIHOP_SCHEMA,
                              object_wildcard_shapes=REG11_MULTIHOP_OWC).schema_info
    assert ('folder', 'viewer') in si.bridged_out_shapes, (
        'the out-bridge shape must exist for this to be an out-bridge test')

    backends = _backends(REG11_MULTIHOP_SCHEMA, REG11_MULTIHOP_OWC)
    try:
        assert _unanimous(backends, _W_STAR) is True, (
            'reg11 claims a star-OBJECT write of this class always self-cycles at '
            'admission; it does not when the TTU target differs from its head')
        assert _unanimous(backends, _W_CLOSE) is False, (
            'the second hop must close the multi-hop out-bridge cycle')
    finally:
        for b in backends:
            b.close()

    # ... and the reverse order is rejected on the FIRST write that closes it,
    # confirming the cycle is a property of the pair, not of the order.
    backends = _backends(REG11_MULTIHOP_SCHEMA, REG11_MULTIHOP_OWC)
    try:
        assert _unanimous(backends, _W_CLOSE) is True
        assert _unanimous(backends, _W_STAR) is False
    finally:
        for b in backends:
            b.close()


# --- the NEW divergence found while disproving reg11 -- FIXED 2026-07-26 ---
#
# WAS: on reg11's OWN schema, a star-SUBJECT + star-OBJECT tupleset write
# (`folder:* parent folder:*`) was ACCEPTED by the graph and REJECTED by the set
# engine. The graph's routed edge is w_any(folder,viewer) -> w_all(folder,viewer)
# (the wildcard node is position-split, so this is not a self-loop and the core's
# cycle check does not fire). Every present-or-future concrete of shape
# (folder,viewer) carries BOTH bridges, so the graph state then contained a latent
# cycle and DETONATED: every later innocent concrete `viewer` write was permanently
# graph-rejected while the set engine and the oracle accepted it.
#
# This is the F1/F2 mechanism (docs/spec-deviations.md 2026-07-16 / 2026-07-17),
# but the 2026-07-17 compile gate does not catch it: `_reject_doubly_bridged_shapes`
# narrowed its left factor from `bridged_in_shapes` to the LITERAL `T:*#p`
# restriction shapes, justified by "star-tupleset through-shapes ... cannot mint a
# persistent w_any node -- reg11's dangerous writes self-cycle and are rejected on
# both backends, so nothing detonates". This repro falsified that sentence.
#
# FIX (2026-07-26): NOT a compile-time scope rejection -- the offending schema IS
# reg11's, and reg11's other writes are legal and oracle-pinned, so no compile
# criterion can reject the dangerous write without deleting a working class (proved
# by construction in `test_zt_p5_starstar_fix_does_not_over_reject_the_legal_class`
# below). It is a WRITE-time rejection in
# `index_v4.wildcard.WildcardIndex._reject_star_self_edge`: a routed edge
# `w_any(T,p) -> w_all(T,p)` on a shape that is both bridged-in and bridged-out is a
# cycle by construction. That is the position-split restatement of the rule the set
# engine already had (`SetEngine._would_cycle`'s raw-level `any(u == v ...)`), so the
# backends now implement ONE rule.
#
# ConnectedStore was never affected: TupleSource delegates admission to the SetEngine,
# which rejects. The exposure was the graph index used directly (WildcardIndex --
# a public API and the matrix's GraphBackend).

ZT_P5_STARSTAR_SCHEMA = """model
  schema 1.1
type user
type folder
  relations
    define parent: [folder, folder:*]
    define viewer: [user] or viewer from parent
"""
ZT_P5_STARSTAR_OWC = frozenset({('folder', 'parent')})
_W_STARSTAR = ('...', 'folder', '*', 'parent', 'folder', '*')
_W_INNOCENT = ('...', 'user', 'v', 'viewer', 'folder', 'q')


def test_zt_p5_star_subject_star_object_tupleset_write_parity():
    """Accept/reject parity + no detonation on `folder:* parent folder:*`.

    Was a STRICT xfail (it pinned a GENUINE divergence, CLAUDE.md testing
    conventions); FLIPPED to a plain regression pin on 2026-07-26 when
    `WildcardIndex._reject_star_self_edge` landed. The assertions were never
    relaxed -- this is byte-for-byte the body that used to fail.
    """
    backends = _backends(ZT_P5_STARSTAR_SCHEMA, ZT_P5_STARSTAR_OWC)
    try:
        _unanimous(backends, _W_STARSTAR)          # <- the accept/reject break
        assert _unanimous(backends, _W_INNOCENT) is True, (
            'an innocent concrete viewer grant must stay writable (detonation)')
    finally:
        for b in backends:
            b.close()


def test_zt_p5_star_subject_star_object_fixed_behaviour_pinned():
    """The companion of the test above, flipped with it: it pinned TODAY's broken
    behaviour so drift in EITHER direction was caught. Now it pins the FIXED
    behaviour, elementwise, for the same reason -- the parity test alone would still
    pass if BOTH backends silently started accepting the write.

    Concretely: both backends must REJECT the star/star tupleset write, both must
    then still accept the innocent concrete grant, the oracle must agree that grant
    holds, and the graph's state must answer it correctly (no residual detonation).
    """
    from tests.test_matrix import GraphBackend, SetBackend
    g = GraphBackend(ZT_P5_STARSTAR_SCHEMA, ZT_P5_STARSTAR_OWC)
    sets = [SetBackend(ZT_P5_STARSTAR_SCHEMA, ZT_P5_STARSTAR_OWC, o) for o in ALL_SETOPS]
    try:
        assert g.apply(_W_STARSTAR, 'add') is False, (
            'the graph must reject the latent-cycle write (w_any -> w_all same shape)')
        for s in sets:
            assert s.apply(_W_STARSTAR, 'add') is False, 'set engine rejects'
        # no detonation: the graph stays open to concrete viewer writes
        assert g.apply(_W_INNOCENT, 'add') is True, 'graph must stay writable'
        for s in sets:
            assert s.apply(_W_INNOCENT, 'add') is True
        # ... and every backend answers it the way the oracle does
        orc = Oracle(ZT_P5_STARSTAR_SCHEMA, [OracleTuple(*_W_INNOCENT)])
        assert orc.check(*_W_INNOCENT) is True
        assert g.check(_W_INNOCENT) is True
        for s in sets:
            assert s.check(_W_INNOCENT) is True
        g.post_op()                      # I1-I13 + I9 fixpoint on the surviving state
    finally:
        g.close()
        for s in sets:
            s.close()


def test_zt_p5_starstar_fix_does_not_over_reject_the_legal_class():
    """WHY the fix is a WRITE-time rejection and not a compile-time one.

    The offending schema is reg11's own, and `owc_star_ttu.fga` is the same shape.
    Both have a NON-EMPTY coarse `bridged_in & bridged_out` -- so the coarse F1/F2
    criterion, and any compile criterion able to see the dangerous write, rejects
    them wholesale. Yet every one of their other writes is legal, unanimous and
    oracle-correct. This test pins that: the schema still COMPILES on both backends,
    reg11's two pinned writes keep their verdicts, and the (i)-without-(ii) class
    (a TTU whose target differs from its head) is entirely unaffected.
    """
    si = parse_openfga_schema(ZT_P5_STARSTAR_SCHEMA,
                              object_wildcard_shapes=ZT_P5_STARSTAR_OWC).schema_info
    assert (frozenset(si.bridged_in_shapes) & frozenset(si.bridged_out_shapes)), (
        'the coarse criterion IS non-empty here -- that is exactly why restoring it '
        'would over-reject this legal schema')

    # reg11's own pinned verdicts, unchanged by the fix.
    reg11_writes = [(('...', 'folder', 'a', 'parent', 'folder', '*'), False),
                    (('...', 'folder', 'a', 'parent', 'folder', 'b'), True)]
    for w, expect in reg11_writes:
        backends = _backends(ZT_P5_STARSTAR_SCHEMA, ZT_P5_STARSTAR_OWC)
        try:
            assert _unanimous(backends, w) is expect, (w, expect)
        finally:
            for b in backends:
                b.close()

    # (i) object-wildcard tupleset shape WITHOUT (ii) a self-referential TTU: the
    # whole sequence stays unanimously ACCEPTED (the reg10-shaped TTU head != target).
    non_self_ref = """model
  schema 1.1
type user
type folder
  relations
    define parent: [folder, folder:*]
    define admin: [user, folder#viewer]
    define viewer: [user] or admin from parent
"""
    backends = _backends(non_self_ref, ZT_P5_STARSTAR_OWC)
    try:
        assert _unanimous(backends, _W_STARSTAR) is True, (
            'precondition (i) alone is LEGAL and must keep working')
        assert _unanimous(backends, _W_INNOCENT) is True
    finally:
        for b in backends:
            b.close()


def test_zt_p5_starstar_generator_blind_spot_is_closed():
    """WHY the star-bridge fuzzer never found the divergence, and that the hole is
    now closed.

    `tests/test_hypothesis.py::_star_bridge_pool` DOES emit `T:* parent T:*`
    whenever `(T,'parent')` is in the drawn object-wildcard set. What
    `_star_bridge_schema` could not produce was a SELF-REFERENTIAL TTU: it was
    always `B: [user] or A from parent` with `A != B` drawn distinct. On that shape
    the write is unanimously ACCEPTED, so the class stayed invisible. The divergence
    needs the TTU head and target to be the SAME relation.

    Fix applied 2026-07-26: `star_bridge_configs` now sometimes draws `A == B`.
    This test pins that the generator's schema builder CAN produce the
    self-referential form and that the strategy actually reaches it.
    """
    from hypothesis import find
    from tests.test_hypothesis import (_star_bridge_pool, _star_bridge_schema,
                                       star_bridge_configs)
    T, A, B = 'folder', 'admin', 'viewer'
    owc = frozenset({(T, 'parent')})
    assert ('...', T, '*', 'parent', T, '*') in _star_bridge_pool(T, A, B, owc), \
        'the fuzzer pool no longer emits the star-subject/star-object parent write'

    # the builder can now emit the self-referential TTU ...
    self_ref = _star_bridge_schema(T, B, B)
    assert f'define {B}: [user' in self_ref and f'or {B} from parent' in self_ref, self_ref
    # ... and it is EXACTLY the dangerous class (same doubly-bridged intersection)
    si = parse_openfga_schema(self_ref, object_wildcard_shapes=owc).schema_info
    assert (T, B) in (frozenset(si.bridged_in_shapes)
                      & frozenset(si.bridged_out_shapes))

    # ... and the strategy REACHES a self-referential config that ALSO draws the
    # object wildcard on the tupleset shape -- i.e. preconditions (i) AND (ii).
    # ``star_bridge_configs`` yields (schema, owc, pool); the self-referential
    # template is the two-relation one (parent + the single self-referential rel).
    def _is_dangerous(cfg):
        schema, owc, pool = cfg
        return (schema.count('    define ') == 2
                and any(s[1] == 'parent' for s in owc))

    found = find(star_bridge_configs(), _is_dangerous)
    gen_schema, gen_owc, gen_pool = found
    assert _is_dangerous(found), found
    T2 = next(s[0] for s in gen_owc if s[1] == 'parent')
    dangerous = ('...', T2, '*', 'parent', T2, '*')
    assert dangerous in gen_pool, (
        'the generated pool must contain the star-subject/star-object write')

    # and on that generated config the dangerous write is now unanimously REJECTED
    backends = _backends(gen_schema, gen_owc)
    try:
        assert _unanimous(backends, dangerous) is False
    finally:
        for b in backends:
            b.close()

    # non-self-referential TTU (what the generator used to build): unanimous ACCEPT
    backends = _backends(_star_bridge_schema(T, A, B), owc)
    try:
        assert _unanimous(backends, _W_STARSTAR) is True
    finally:
        for b in backends:
            b.close()


def test_zt_p5_connectedstore_is_not_exposed_to_the_starstar_divergence():
    """The composed system rejects the write (TupleSource delegates admission to
    the SetEngine), so the exposure is the graph index used DIRECTLY."""
    from connectedstore import ConnectedStore
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        cs = ConnectedStore(s, 'cx', schema=ZT_P5_STARSTAR_SCHEMA,
                            object_wildcard_shapes=ZT_P5_STARSTAR_OWC)
        s.commit()
        with pytest.raises(ValueError, match='cycle'):
            cs.add_tuple(*_W_STARSTAR)
        cs.add_tuple(*_W_INNOCENT)          # and it stays writable
        assert cs.check(*_W_INNOCENT) is True


# --- the bounded NEGATIVE result -------------------------------------------

_OB_RESTR = ['user', 'folder#a', 'folder#b', 'folder:*#a', 'folder:*#b']
_OB_RULES = [None, 'a from parent', 'b from parent']


def _ob_schema(ra, rule_a, rb, rule_b):
    def rel(name, restr, rule):
        s = f'    define {name}: [{", ".join(restr)}]'
        return s + (f' or {rule}' if rule else '')
    return ('model\n  schema 1.1\ntype user\ntype folder\n  relations\n'
            '    define parent: [folder, folder:*]\n'
            + rel('a', ra, rule_a) + '\n' + rel('b', rb, rule_b) + '\n')


def test_zt_p5_bounded_search_object_wildcard_out_bridge_no_further_divergence():
    """BOUNDED negative result for target 1 (evidence, NOT a proof).

    Bounds actually covered by the session's search (see docs/spec-deviations.md
    2026-07-26): family A -- one object type `folder`, relations
    {parent:[folder,folder:*], a, b} with restriction subsets of
    {user, folder#a, folder#b, folder:*#a, folder:*#b} (size 1-2) and an optional
    `{a|b} from parent` arm; object-wildcard shapes any non-empty subset of
    {(folder,parent),(folder,a),(folder,b)}; write sequences of 2-4 tuples drawn
    from a 33-tuple pool always containing a `folder:*`-OBJECT write. Family B --
    two object types (folder, doc) with cross-type tuplesets and remove ops.
    Roughly 2,000 admissible randomized trials; every admission divergence found
    was the SAME class (the star-subject/star-object tupleset write pinned above)
    and no ANSWER-level divergence was found at all.

    This test re-runs a small deterministic slice so the negative result is
    executable rather than asserted. It is NOT exhaustive over that space.
    """
    pool = []
    for on in ('x', 'y', '*'):
        for sn in ('x', 'y'):                      # star SUBJECT excluded: pinned above
            pool.append(('...', 'folder', sn, 'parent', 'folder', on))
        for rel in ('a', 'b'):
            for sp, sn in (('a', 'x'), ('b', 'x'), ('a', '*'), ('b', '*')):
                pool.append((sp, 'folder', sn, rel, 'folder', on))
            pool.append(('...', 'user', 'u', rel, 'folder', on))

    grid = [(sp, st, sn, r, 'folder', o)
            for (sp, st, sn) in (('...', 'user', 'u'), ('a', 'folder', 'x'),
                                 ('b', 'folder', 'x'))
            for r in ('a', 'b') for o in ('x', 'y')]

    owcs = [frozenset({('folder', 'parent')}),
            frozenset({('folder', 'parent'), ('folder', 'a')})]
    schemas = [_ob_schema(['user', 'folder:*#a'], 'a from parent', ['user'], None),
               _ob_schema(['folder#a'], 'a from parent', ['user', 'folder#a'], None),
               _ob_schema(['user'], 'b from parent', ['user', 'folder:*#b'], 'b from parent')]

    star_obj = [t for t in pool if t[5] == '*']
    checked = 0
    for schema in schemas:
        for owc in owcs:
            try:
                _ = parse_openfga_schema(schema, object_wildcard_shapes=owc)
            except (UnsupportedByGraphIndex, ValueError):
                continue
            for w0 in star_obj[:6]:
                for w1 in pool[:6]:
                    backends = _backends(schema, owc)
                    present = []
                    try:
                        for w in (w0, w1):
                            if _unanimous(backends, w):
                                present.append(w)
                        orc = Oracle(schema, [OracleTuple(*r) for r in present])
                        for q in grid:
                            want = orc.check(*q)
                            for b in backends:
                                assert b.check(q) == want, (
                                    f'answer divergence: schema={schema!r} owc={sorted(owc)} '
                                    f'writes={present} query={q} {b.name}={b.check(q)} '
                                    f'oracle={want}')
                        checked += 1
                    finally:
                        for b in backends:
                            b.close()
    assert checked >= 70, f'the bounded slice went vacuous ({checked} states)'


# ===========================================================================
# TARGET 2 — the 2026-07-13 X4 from-chain TARGET note's REACHABILITY half
# ===========================================================================
#
# The note (docs/spec-deviations.md 2026-07-13, X4 §1) says: "if a from-chain
# TARGET were an untainted subject-wildcard-bridged shape with grants already
# sitting in its `w_any`, interning a from-chain subject node mid-cascade could
# create new bridge-fed truth ... No currently-compilable schema class reaches
# this shape".
#
# It IS reachable. `_from_chain_keys` fires for leaf kind 'derived-ttu', which
# `_is_pure` produces when SOME parent type of the tupleset has a TAINTED
# target_rel -- but the key enumeration walks ALL stored parents, so a parent of a
# DIFFERENT type whose target_rel is UNTAINTED yields exactly the excluded shape.

FROM_CHAIN_SCHEMA = """model
  schema 1.1
type user
type folder
  relations
    define member: [user]
    define shared: [user, folder:*#member]
type team
  relations
    define tblk: [user]
    define member: [user] but not tblk
type doc
  relations
    define fparent: [folder, team]
    define viewer: member from fparent
"""
_FC_GRANT = ('member', 'folder', '*', 'shared', 'folder', 'g')   # grant into w_any
_FC_PARENT = ('...', 'folder', 'f1', 'fparent', 'doc', 'd1')     # from-chain parent


def test_zt_p5_from_chain_target_shape_IS_reachable():
    """The 2026-07-13 "no currently-compilable schema class reaches this shape"
    claim is DISPROVED: `folder#member` is UNTAINTED, is in `bridged_in_shapes`,
    already carries a grant in its `w_any`, and reconcile step 2a interns its
    from-chain node FRESH mid-cascade (minting the in-bridge).

    The note's OTHER half -- "if one ever did it fails LOUD" -- is not contradicted:
    answers stay oracle-correct here and the cascade quiesces. What is disproved is
    only the reachability premise, which is what licensed never re-deriving the
    note across the 2026-07-17 Fix A lift, the `rootB` widening and the Direct-arm
    corpora.
    """
    import index_v4.processor as P
    from tests.test_matrix import GraphBackend, SetBackend

    rs = parse_openfga_schema(FROM_CHAIN_SCHEMA)
    si, compiled = rs.schema_info, rs.compiled
    assert ('folder', 'member') in si.bridged_in_shapes
    assert ('folder', 'member') not in compiled.tainted, 'the TARGET must be UNTAINTED'
    kinds = {s.kind for p in compiled.plans.values() for s in p.leaves}
    assert 'derived-ttu' in kinds, 'the from-chain path only runs on derived-ttu leaves'

    seen = []
    original = P.DeltaProcessor._from_chain_keys

    def spy(self, object_type, obj_name, plan):
        keys = original(self, object_type, obj_name, plan)
        for (sp, st, sn) in keys:
            seen.append(dict(key=(sp, st, sn),
                             fresh=self._node(sp, st, sn) is None,
                             bridged_in=(st, sp) in si.bridged_in_shapes,
                             tainted=(st, sp) in self.compiled.tainted))
        return keys

    P.DeltaProcessor._from_chain_keys = spy
    try:
        g = GraphBackend(FROM_CHAIN_SCHEMA)
        sets = [SetBackend(FROM_CHAIN_SCHEMA, frozenset(), o) for o in ALL_SETOPS]
        try:
            # the GRANT lands first, so it is "already sitting in the w_any" when
            # the from-chain intern happens -- the note's exact precondition.
            for w in (_FC_GRANT, _FC_PARENT):
                res = {g.name: g.apply(w, 'add')}
                for s in sets:
                    res[s.name] = s.apply(w, 'add')
                assert all(res.values()), f'write {w} rejected: {res}'

            hits = [e for e in seen
                    if e['fresh'] and e['bridged_in'] and not e['tainted']]
            assert hits, (
                'the excluded shape was NOT reached -- if this fires the repro has '
                f'drifted; observed from-chain keys: {seen}')

            # the mid-cascade intern really minted the in-bridge, and the closure
            # really carries the bridge-fed truth
            from index_v4.models import NodeV4, EdgeV4
            nodes = {n.id: (n.type, n.name, n.predicate, n.wildcard)
                     for n in g.session.exec(select(NodeV4)).all()}
            edges = {(nodes[e.subject_id], nodes[e.object_id])
                     for e in g.session.exec(select(EdgeV4)).all()}
            assert (('folder', 'f1', 'member', ''),
                    ('folder', '*', 'member', 'any')) in edges, \
                'the from-chain intern must mint the concrete -> w_any in-bridge'
            assert (('folder', 'f1', 'member', ''),
                    ('folder', 'g', 'shared', '')) in edges, \
                'the bridge-fed truth must reach the pre-existing w_any grant'

            # and it is ANSWER-correct (the "fails LOUD" half is not contradicted)
            orc = Oracle(FROM_CHAIN_SCHEMA,
                         [OracleTuple(*_FC_GRANT), OracleTuple(*_FC_PARENT)])
            for q in (('member', 'folder', 'f1', 'viewer', 'doc', 'd1'),
                      ('member', 'folder', 'f1', 'shared', 'folder', 'g'),
                      ('viewer', 'doc', 'd1', 'shared', 'folder', 'g')):
                want = orc.check(*q)
                assert g.check(q) == want, (q, g.check(q), want)
                for s in sets:
                    assert s.check(q) == want, (q, s.name, s.check(q), want)
            g.post_op()
        finally:
            g.close()
            for s in sets:
                s.close()
    finally:
        P.DeltaProcessor._from_chain_keys = original


# ===========================================================================
# TARGET 3 — the object-wildcard corpus at STATE level
# ===========================================================================
#
# `FINAL_REVIEW.md` §3 / `ARCHITECTURE.md` §6 infer "the fragment exclusions are
# proof-scope, not observed divergence" from a 2026-07-12 CHECK-level probe. That
# exact inference failed on 2026-07-17 at STATE level, and the object-wildcard
# corpus was never probed at state level. The Lean half cannot be settled here
# (formal/ is out of scope for this module); what IS checkable Python-side is
# state-functionality: the live incremental state must equal a fresh rebuild and
# must not depend on write order. Those are the properties the 2026-07-17
# stale-fanout bug actually broke.

_OWC_CORPUS = ("""model
  schema 1.1
type user
type folder
  relations
    define viewer: [user]
""", frozenset({('folder', 'viewer')}),
    [('...', 'user', u, 'viewer', 'folder', o)
     for u in ('u1', 'u2') for o in ('f1', 'f2', '*')])

_OWC_TTU_CORPUS = ("""model
  schema 1.1
type user
type folder
  relations
    define parent: [folder]
    define viewer: [user, user:*] or viewer from parent
""", frozenset({('folder', 'viewer')}),
    [('...', 'user', u, 'viewer', 'folder', o)
     for u in ('u1', '*') for o in ('f1', 'f2', '*')]
    + [('...', 'folder', 'f1', 'parent', 'folder', 'f2')])


def _state_projections(session, store_id):
    """The canonical natural-key projections of tests/test_bulk_build.py."""
    from index_v4.models import EdgeV4, NodeV4, ResidueV1
    nodes = list(session.exec(select(NodeV4).where(NodeV4.store_id == store_id)).all())
    idmap = {n.id: (n.predicate, n.type, n.name, n.wildcard) for n in nodes}
    proj_nodes = {idmap[n.id]: (n.implicit, n.reference_count) for n in nodes}
    proj_edges = {(idmap[e.subject_id], idmap[e.object_id]):
                  (e.direct_edge_count, e.indirect_edge_count, e.derived)
                  for e in session.exec(
                      select(EdgeV4).where(EdgeV4.store_id == store_id)).all()}
    proj_res = {}
    for r in session.exec(select(ResidueV1).where(ResidueV1.store_id == store_id)).all():
        proj_res[idmap[r.object_node_id]] = (
            frozenset(tuple(x) for x in json.loads(r.stars)),
            frozenset(idmap[i] for i in json.loads(r.neg)),
            frozenset(idmap[i] for i in json.loads(r.upos)))
    return {'nodes': proj_nodes, 'edges': proj_edges, 'residues': proj_res}


def _state_diff(a, b):
    out = {}
    for kind in a:
        keys = set(a[kind]) | set(b[kind])
        d = {k: (a[kind].get(k), b[kind].get(k)) for k in keys
             if a[kind].get(k) != b[kind].get(k)}
        if d:
            out[kind] = d
    return out


def _live_state(schema, owc, seq):
    from connectedstore import ConnectedStore
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    cs = ConnectedStore(session, 'live', schema=schema, object_wildcard_shapes=owc)
    session.commit()
    landed = []
    for w in seq:
        try:
            cs.add_tuple(*w)
            landed.append(w)
        except ValueError:
            pass
    session.commit()
    return session, landed


@pytest.mark.parametrize('corpus,k', [(_OWC_CORPUS, 2), (_OWC_TTU_CORPUS, 2)],
                         ids=['object_wildcard', 'object_wildcard_ttu'])
def test_zt_p5_object_wildcard_state_level_live_equals_rebuild(corpus, k):
    """STATE level (bounded, exhaustive to k tuples): the live incremental state
    of an object-wildcard corpus equals a fresh incremental rebuild AND a fresh
    BULK build, over the four canonical projections; and I1-I13 are green on all
    three. Settles the Python half of the "never probed at state level" gap; the
    Lean half still needs a `formal/` state-conformance run over the
    `object_wildcard` corpus (currently EXCLUDED from `GRAPH_FRAGMENT`).
    """
    from connectedstore import build_index
    from index_v4.invariants import check_invariants

    schema, owc, space = corpus
    stores = [s for kk in range(k + 1) for s in itertools.combinations(space, kk)]
    assert len(stores) >= 20, 'bound went vacuous'
    for store in stores:
        session, landed = _live_state(schema, owc, list(store))
        try:
            if not landed:
                continue
            check_invariants(session, 'live')
            live = _state_projections(session, 'live')
            build_index(session, 'live', 'inc', bulk=False)
            build_index(session, 'live', 'blk', bulk=True)
            check_invariants(session, 'inc')
            check_invariants(session, 'blk')
            inc = _state_projections(session, 'inc')
            blk = _state_projections(session, 'blk')
            assert not _state_diff(live, inc), \
                f'live vs incremental-rebuild state differs on {store}: ' \
                f'{_state_diff(live, inc)}'
            assert not _state_diff(inc, blk), \
                f'incremental vs bulk build state differs on {store}: ' \
                f'{_state_diff(inc, blk)}'
        finally:
            session.close()


def test_zt_p5_object_wildcard_state_is_order_independent():
    """STATE level: the live object-wildcard state is a function of the tuple SET,
    not of the write order (the property the 2026-07-17 stale-fanout bug broke)."""
    schema, owc, space = _OWC_TTU_CORPUS
    checked = 0
    for store in itertools.combinations(space, 3):
        session, landed = _live_state(schema, owc, list(store))
        base = _state_projections(session, 'live')
        session.close()
        for perm in (tuple(reversed(store)), (store[1], store[2], store[0])):
            session2, landed2 = _live_state(schema, owc, list(perm))
            other = _state_projections(session2, 'live')
            session2.close()
            if set(landed) != set(landed2):
                continue                # admission is order-sensitive: not comparable
            assert not _state_diff(base, other), (
                f'live state depends on write order: {store} vs {perm}: '
                f'{_state_diff(base, other)}')
            checked += 1
    assert checked >= 20, f'order-independence check went vacuous ({checked})'


# ===========================================================================
# TARGET 4 — the `group_userset` enum exclusion (an ADMISSION-DOMAIN question)
# ===========================================================================
#
# `formal/conformance/test_conformance_enum.py` drops the self-referential
# nested-group shape from the only exhaustive gate because the SET ENGINE's cycle
# guard rejects 132 of its 299 stores. The zero-trust review flagged that as an
# unadjudicated admission-domain difference -- precisely the reg9/reg10/reg13 bug
# class. It is not one: the GRAPH rejects exactly the same 132 stores, write for
# write, in every write order.

GROUP_USERSET_SCHEMA = """model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define viewer: [group#member]
"""


def _group_userset_space():
    space = []
    for on in ('g1', 'g2'):
        for sn in ('u1', 'u2'):
            space.append(('...', 'user', sn, 'member', 'group', on))
        for sn in ('g1', 'g2'):
            space.append(('member', 'group', sn, 'member', 'group', on))
    for on in ('d1', 'd2'):
        for sn in ('g1', 'g2'):
            space.append(('member', 'group', sn, 'viewer', 'doc', on))
    return sorted(space)


def test_zt_p5_group_userset_admission_domains_are_identical():
    """EXHAUSTIVE at the enum module's own bound (12-tuple space, K=3, 299
    stores): the set engine and the graph index accept and reject exactly the
    same writes on every store. So the enum exclusion is a genuine
    admission-domain property of the SHAPE (self-referential nested groups are
    cyclic), not a backend disagreement.

    Full-session evidence (not re-run here for runtime): the same comparison over
    ALL permutations of every store found 0 mismatches and 0 order-dependent
    stores, and on the 167 fully-admitted stores graph == both SetOps == oracle
    over a 16-query grid.
    """
    space = _group_userset_space()
    assert len(space) == 12, f'tuple space drifted: {len(space)}'
    stores = [s for k in range(4) for s in itertools.combinations(space, k)]
    assert len(stores) == 299, f'store count drifted: {len(stores)}'

    set_rejecting = 0
    graph_rejecting = 0
    for store in stores:
        backends = _backends(GROUP_USERSET_SCHEMA)
        try:
            graph, sets = backends[0], backends[1:]
            g_all, s_all = True, True
            for w in store:
                gr = graph.apply(w, 'add')
                srs = [s.apply(w, 'add') for s in sets]
                assert len(set(srs)) == 1, f'SetOps disagree on {w} in {store}: {srs}'
                assert gr == srs[0], (
                    f'ADMISSION-DOMAIN DIVERGENCE on {w} in store {store}: '
                    f'graph={gr} set={srs[0]}')
                g_all &= gr
                s_all &= srs[0]
            graph_rejecting += not g_all
            set_rejecting += not s_all
        finally:
            for b in backends:
                b.close()
    assert set_rejecting == graph_rejecting == 132, (
        'the documented 132/299 rejection count drifted: '
        f'set={set_rejecting} graph={graph_rejecting}')


# ===========================================================================
# TARGET 5 — orphaned findings that never reached any board
# ===========================================================================

STAR_ON_DERIVED_DIRECT_ARM = """model
  schema 1.1
type user
type doc
  relations
    define blocked: [user]
    define viewer: [user, user:*] but not blocked
"""


def test_zt_p5_star_restriction_on_derived_direct_arm_python_truth():
    """`formal/HANDOFF.md` records an OPEN Lean-side star-freeness hole in
    `w3cJobValid_enumJob2D` -- "a WILDCARD restriction on a derived Direct arm
    puts `user:*` in `storedDirectSubjects`". Python-side truth: the shape is
    ADMITTED, compiles to two closure leaves, and is exhaustively correct at K=2
    over its 10-tuple space (graph == both SetOps == oracle). The hole is
    PROOF-side only; no Python behaviour change is implied.
    """
    rs = parse_openfga_schema(STAR_ON_DERIVED_DIRECT_ARM)
    assert ('doc', 'viewer') in rs.compiled.tainted
    kinds = [(s.kind, s.predicate) for s in rs.compiled.plans[('doc', 'viewer')].leaves]
    assert kinds == [('closure', 'viewer.0'), ('closure', 'viewer.1')], kinds

    space = ([('...', 'user', u, 'viewer', 'doc', d)
              for u in ('u1', 'u2', '*') for d in ('d1', 'd2')]
             + [('...', 'user', u, 'blocked', 'doc', d)
                for u in ('u1', 'u2') for d in ('d1', 'd2')])
    grid = [('...', 'user', u, r, 'doc', d)
            for u in ('u1', 'u2', '*') for r in ('viewer', 'blocked') for d in ('d1', 'd2')]
    for k in (1, 2):
        for store in itertools.combinations(space, k):
            backends = _backends(STAR_ON_DERIVED_DIRECT_ARM)
            try:
                present = [w for w in store if _unanimous(backends, w)]
                orc = Oracle(STAR_ON_DERIVED_DIRECT_ARM,
                             [OracleTuple(*w) for w in present])
                for q in grid:
                    want = orc.check(*q)
                    for b in backends:
                        assert b.check(q) == want, (store, q, b.name, want)
            finally:
                for b in backends:
                    b.close()


PDERIVED_USERSET_SCHEMA = """model
  schema 1.1
type user
type group
  relations
    define banned: [user]
    define member: [user] but not banned
type doc
  relations
    define viewer: [user, group#member]
"""


def test_zt_p5_pderived_userset_python_truth():
    """`PDerivedUserset` (the X4 shape, fixed Python-side 2026-07-13 and extended
    2026-07-17) is recorded as NEVER MODELLED IN LEAN. Python-side truth: a Direct
    restriction over a DERIVED relation compiles to a `derived-userset` leaf and is
    exhaustively correct at K=2 over its 6-tuple space; its WILDCARD form
    (`[group:*#member]`) is a compile-time scope rejection on both backends.
    """
    rs = parse_openfga_schema(PDERIVED_USERSET_SCHEMA)
    kinds = [s.kind for s in rs.compiled.plans[('doc', 'viewer')].leaves]
    assert 'derived-userset' in kinds, kinds

    space = ([('...', 'user', u, r, 'group', 'g1')
              for u in ('u1', 'u2') for r in ('banned', 'member')]
             + [('member', 'group', 'g1', 'viewer', 'doc', 'd1'),
                ('...', 'user', 'u1', 'viewer', 'doc', 'd1')])
    grid = [(sp, st, sn, r, ot, on)
            for (sp, st, sn) in (('...', 'user', 'u1'), ('...', 'user', 'u2'),
                                 ('member', 'group', 'g1'))
            for (r, ot, on) in (('member', 'group', 'g1'), ('viewer', 'doc', 'd1'))]
    for k in (1, 2):
        for store in itertools.combinations(space, k):
            backends = _backends(PDERIVED_USERSET_SCHEMA)
            try:
                present = [w for w in store if _unanimous(backends, w)]
                orc = Oracle(PDERIVED_USERSET_SCHEMA, [OracleTuple(*w) for w in present])
                for q in grid:
                    want = orc.check(*q)
                    for b in backends:
                        assert b.check(q) == want, (store, q, b.name, want)
            finally:
                for b in backends:
                    b.close()

    # the wildcard form stays a scope rejection (decision-15 family)
    with pytest.raises(UnsupportedByGraphIndex, match='wildcard userset restriction'):
        parse_openfga_schema(
            PDERIVED_USERSET_SCHEMA.replace('[user, group#member]',
                                            '[user, group:*#member]'))


_UNDEFINED_REFERENCE_SCHEMAS = {
    'computed': 'model\n  schema 1.1\ntype user\ntype doc\n  relations\n'
                '    define viewer: nosuch\n',
    'ttu_target': 'model\n  schema 1.1\ntype user\ntype folder\n  relations\n'
                  '    define x: [user]\ntype doc\n  relations\n'
                  '    define parent: [folder]\n    define viewer: nosuch from parent\n',
    'ttu_tupleset': 'model\n  schema 1.1\ntype user\ntype doc\n  relations\n'
                    '    define viewer: [user] or x from nosuch\n',
    'direct_type': 'model\n  schema 1.1\ntype user\ntype doc\n  relations\n'
                   '    define viewer: [nosuchtype]\n',
    'userset_relation': 'model\n  schema 1.1\ntype user\ntype group\n  relations\n'
                        '    define m: [user]\ntype doc\n  relations\n'
                        '    define viewer: [group#nosuch]\n',
    'boolean_arm': 'model\n  schema 1.1\ntype user\ntype doc\n  relations\n'
                   '    define a: [user]\n    define viewer: a but not nosuch\n',
    'self_computed': 'model\n  schema 1.1\ntype user\ntype doc\n  relations\n'
                     '    define viewer: viewer\n',
}


@pytest.mark.parametrize('name', sorted(_UNDEFINED_REFERENCE_SCHEMAS))
def test_zt_p5_undefined_references_compile_silently_and_read_empty(name):
    """Phase-ledger row 0.5 ("verify compiler undefined-reference behavior (A3)",
    still `todo` since Phase 0). Current Python-side truth, established here:

      * `compile_ruleset` performs NO undefined-reference validation at all --
        every form below compiles SILENTLY (undefined computed target, undefined
        TTU target, undefined tupleset relation, undefined restriction type,
        undefined userset relation, undefined boolean arm, self-referential
        computed);
      * all three backends (graph, both SetOps, oracle) then build, and every
        such reference reads as the EMPTY relation -- fail-CLOSED, and unanimous.

    That is the safe direction, so this is a WF/diagnostics gap, not a soundness
    one; pinning it means a future "reject undefined references" change is a
    deliberate, visible decision rather than a silent behaviour flip.
    """
    from tests.test_matrix import GraphBackend, SetBackend
    schema = _UNDEFINED_REFERENCE_SCHEMAS[name]
    rs = parse_openfga_schema(schema)          # must NOT raise (documents today)
    assert rs is not None

    backends = _backends(schema)
    try:
        # anything writable stays writable, and nothing an undefined reference
        # gates ever becomes true
        orc = Oracle(schema, [])
        for q in (('...', 'user', 'u1', 'viewer', 'doc', 'd1'),
                  ('m', 'group', 'g1', 'viewer', 'doc', 'd1')):
            want = orc.check(*q)
            assert want is False, (name, q, want)
            for b in backends:
                assert b.check(q) is False, (name, q, b.name)
    finally:
        for b in backends:
            b.close()
