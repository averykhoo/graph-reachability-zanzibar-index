"""P13 identity gate: the bulk closure builder produces state BYTE-IDENTICAL to the
incremental per-tuple load (``docs/architecture/p13-bulk-build-design.md``).

For each corpus schema (spanning union / computed chains / TTU / subject-wildcard /
object-wildcard bridged in AND out / userset restrictions / boolean and-but-not), a
deterministic tuple set is written through a ``TupleSource``, then the graph index is
built TWICE from that one snapshot: once with ``build_index(..., bulk=False)`` (the
incremental reference loop) and once with ``bulk=True`` (the new builder). The four
canonical projections -- nodes / edges / residues / outbox, keyed by NATURAL keys and
never raw ids -- must be exactly equal, with a precise diff printed on any divergence.

The comparison's strictness IS the deliverable: a divergence must fail loudly with the
differing keys, never be papered over. On top of equality, the I1-I13 invariant checker
runs green on the bulk-built store, and a read-parity spot grid is compared against the
independent oracle on the wildcard and boolean schemas.
"""

import json
from collections import Counter
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from connectedstore import TupleSource, build_index, save_schema
from index_v4.invariants import check_invariants, snapshot_rows
from index_v4.models import DeltaOutboxV1, EdgeV4, NodeV4, ResidueV1
from setengine.models import TupleV1
from tests.oracle import Oracle, OracleTuple
from tests.test_wildcard_property import OBJECT_WC, _query_grid
from tests.test_matrix import _boolean_grid, _demorgan_pool


_FGA_DIR = Path(__file__).parent / 'fga_schemas'


def _load_fga(name: str) -> str:
    with open(_FGA_DIR / name, 'r') as f:
        return f.read()


# --------------------------------------------------------------------------- #
# Deterministic, acyclic, schema-valid tuple generators (shapes mirror the
# proven-valid reference pools in tests/, over enlarged universes so fan-in and
# path diamonds -- hence indirect counts > 1 -- are exercised).
# --------------------------------------------------------------------------- #

def _wildcards_tuples(nusers=4, ngroups=4, nfolders=4, ndocs=4) -> list[tuple]:
    users = [f'u{i}' for i in range(1, nusers + 1)]
    groups = [f'g{i}' for i in range(1, ngroups + 1)]
    folders = [f'f{i}' for i in range(1, nfolders + 1)]
    docs = [f'd{i}' for i in range(1, ndocs + 1)]
    out: list[tuple] = []
    # membership [user]: every user in every group (fan-in) ...
    for u in users:
        for g in groups:
            out.append(('...', 'user', u, 'member', 'group', g))
    # ... plus nested groups gi->gj (i<j: acyclic) -> membership diamonds (indirect>1)
    for i in range(ngroups):
        for j in range(i + 1, ngroups):
            out.append(('member', 'group', groups[i], 'member', 'group', groups[j]))
    # viewer: [user, user:*, group#member, group:*#member] or viewer from parent
    viewer_objs = ([('folder', f) for f in folders] + [('document', d) for d in docs]
                   + [('folder', '*'), ('document', '*')])   # object wildcards (bridged out)
    for (ot, on) in viewer_objs:
        for u in users:
            out.append(('...', 'user', u, 'viewer', ot, on))
        out.append(('...', 'user', '*', 'viewer', ot, on))          # subject wildcard user:*
        for g in groups:
            out.append(('member', 'group', g, 'viewer', ot, on))
        out.append(('member', 'group', '*', 'viewer', ot, on))      # group:*#member (bridged in)
    # parent: folder->folder (i<j) + folder->doc (TTU inheritance chain)
    for i in range(nfolders):
        for j in range(i + 1, nfolders):
            out.append(('...', 'folder', folders[i], 'parent', 'folder', folders[j]))
    for f in folders:
        for d in docs:
            out.append(('...', 'folder', f, 'parent', 'document', d))
    return list(dict.fromkeys(out))


def _boolean_tuples(nusers=5, ngroups=4, ndocs=5) -> list[tuple]:
    users = [f'u{i}' for i in range(1, nusers + 1)]
    groups = [f'g{i}' for i in range(1, ngroups + 1)]
    docs = [f'd{i}' for i in range(1, ndocs + 1)]
    out: list[tuple] = []
    for u in users:
        for g in groups:
            out.append(('...', 'user', u, 'member', 'group', g))
    for i in range(ngroups):
        for j in range(i + 1, ngroups):
            out.append(('member', 'group', groups[i], 'member', 'group', groups[j]))
    for d in docs:
        out.append(('...', 'user', '*', 'public', 'doc', d))        # subject wildcard user:*
        for u in users:
            out.append(('...', 'user', u, 'blocked', 'doc', d))     # but-not exclusion input
            out.append(('...', 'user', u, 'editor', 'doc', d))
        for g in groups:
            out.append(('member', 'group', g, 'editor', 'doc', d))  # userset restriction
    for i in range(ndocs):
        for j in range(i + 1, ndocs):
            out.append(('...', 'doc', docs[i], 'parent', 'doc', docs[j]))   # TTU (inherited)
    return list(dict.fromkeys(out))


_WILDCARDS = _load_fga('wildcards.fga')
_BOOLEAN = _load_fga('boolean_wildcards.fga')
_DEMORGAN = _load_fga('demorgans_reverse.fga')

# Fan-in corpus: two directly-writable operands unioned into one computed relation,
# so two DISTINCT raw tuples (editor + owner on the same subject/object) derive the
# SAME routed pair -- the multigraph direct_edge_count > 1 case the add_tuple
# docstring warns about, which the other corpora never reach (their routing never
# collides). The group#member arm additionally threads the m=2 edge into a longer
# path, so the DP's multiplicity WEIGHTING (not just presence) is pinned:
# P(user -> viewer:doc via g#member) multiplies through the m=2 edge.
_FANIN = """
model
  schema 1.1

type user

type group
  relations
    define member: [user]

type document
  relations
    define editor: [user, group#member]
    define owner: [user, group#member]
    define viewer: editor or owner
"""


def _fanin_tuples(nusers=3, ngroups=2, ndocs=3) -> list[tuple]:
    users = [f'u{i}' for i in range(1, nusers + 1)]
    groups = [f'g{i}' for i in range(1, ngroups + 1)]
    docs = [f'd{i}' for i in range(1, ndocs + 1)]
    out: list[tuple] = []
    for u in users:
        for g in groups:
            out.append(('...', 'user', u, 'member', 'group', g))
    for d in docs:
        # direct editor+owner fan-in for the first two users only: the LAST user
        # reaches documents solely through group membership, so their (user ->
        # viewer:doc) pair is PURE-indirect with a count multiplied through the
        # m=2 (group#member -> viewer:doc) edge below.
        for u in users[:2]:
            out.append(('...', 'user', u, 'editor', 'document', d))
            out.append(('...', 'user', u, 'owner', 'document', d))    # fan-in with editor
        for g in groups:
            out.append(('member', 'group', g, 'editor', 'document', d))
            out.append(('member', 'group', g, 'owner', 'document', d))  # m=2 mid-path
    return list(dict.fromkeys(out))


def _fanin_grid() -> list[tuple]:
    subjects = ([('...', 'user', f'u{i}') for i in range(1, 5)]
                + [('member', 'group', f'g{i}') for i in range(1, 4)])
    return [(sp, st, sn, rel, 'document', f'd{i}')
            for (sp, st, sn) in subjects
            for rel in ('editor', 'owner', 'viewer')
            for i in range(1, 5)]


# R4-BF gate extension (design docs/architecture/r4bf-bulk-backfill-design.md §5). The boolean/
# demorgan corpora already drive the in-memory backfill; these reach the state-shaping
# features the four originals do not:
#
#  (a) DERIVED-USERSET LEAF + STICKY PROMOTION + DERIVED NODE WITH OUTGOING EDGES:
#      ``member`` is derived on ``group`` (``[user] but not banned``); a raw tuple whose
#      subject is the userset ``group:g#member`` creates the public node
#      ``(member, group, g)`` IMPLICIT during load (a userset subject), and the processor
#      sticky-promotes it explicit when it reconciles ``(group, member, g)``. That public
#      node has an OUTGOING edge (the userset tuple onto viewer's leaf), so derived edges
#      into it extend the closure THROUGH it. ``viewer = [group#member] but not blocked``
#      makes viewer's storage leaf a ``derived-userset`` kind (member derived).
_DERIVED_MEMBER = """
model
  schema 1.1

type user

type group
  relations
    define banned: [user]
    define member: [user] but not banned

type doc
  relations
    define blocked: [user]
    define viewer: [group#member] but not blocked
"""


def _derived_member_tuples(nusers=4, ngroups=3, ndocs=3) -> list[tuple]:
    users = [f'u{i}' for i in range(1, nusers + 1)]
    groups = [f'g{i}' for i in range(1, ngroups + 1)]
    docs = [f'd{i}' for i in range(1, ndocs + 1)]
    out: list[tuple] = []
    for u in users:
        for g in groups:
            out.append(('...', 'user', u, 'member', 'group', g))   # routes to member.0
    for i, u in enumerate(users):
        for j, g in enumerate(groups):
            if (i + j) % 3 == 0:
                out.append(('...', 'user', u, 'banned', 'group', g))   # but-not input
    for g in groups:
        for d in docs:
            # userset subject OVER a derived relation: creates the (member, group, g)
            # public node during load; derived edges into it extend the closure to viewer.
            out.append(('member', 'group', g, 'viewer', 'doc', d))
    for i, u in enumerate(users):
        for j, d in enumerate(docs):
            if (i + j) % 2 == 0:
                out.append(('...', 'user', u, 'blocked', 'doc', d))
    return list(dict.fromkeys(out))


def _derived_member_grid() -> list[tuple]:
    subjects = ([('...', 'user', f'u{i}') for i in range(1, 6)]
                + [('member', 'group', f'g{i}') for i in range(1, 4)])
    return [(sp, st, sn, rel, ot, on)
            for (sp, st, sn) in subjects
            for (rel, ot) in (('member', 'group'), ('viewer', 'doc'))
            for on in ([f'g{i}' for i in range(1, 4)] if ot == 'group'
                       else [f'd{i}' for i in range(1, 4)])]


#  (c) DERIVED-TUPLESET-TTU (derived tupleset) + (d) >= 3 BOOLEAN STRATA + X4b/from-chain:
#      demorgans_law_1 chains three ``derived-tupleset-ttu`` leaves (each TTU's tupleset is
#      itself derived) across five strata; its from-chain nodes are recorded edge-free
#      (no bridged shape) -> the rc=0 explicit-node case (e).
_DEMORGAN1 = _load_fga('demorgans_law_1.fga')


def _demorgan1_tuples(nusers=3, nroles=2, nconds=2, nattrs=3, ndocs=2) -> list[tuple]:
    users = [f'u{i}' for i in range(1, nusers + 1)]
    roles = [f'r{i}' for i in range(1, nroles + 1)]
    conds = [f'c{i}' for i in range(1, nconds + 1)]
    attrs = [f'a{i}' for i in range(1, nattrs + 1)]
    docs = [f'd{i}' for i in range(1, ndocs + 1)]
    out: list[tuple] = []
    for u in users:
        for r in roles:
            out.append(('...', 'user', u, 'granted', 'role', r))
    for r in roles:
        for c in conds:
            out.append(('...', 'role', r, 'assigned', 'cond', c))
    for c in conds:
        for a in attrs:
            out.append(('...', 'cond', c, 'required_by', 'attr', a))
    for j, d in enumerate(docs):
        out.append(('...', 'attr', '*', '_all_attrs', 'doc', d))   # attr:* subject wildcard
        out.append(('...', 'cond', '*', '_all_conds', 'doc', d))   # cond:* subject wildcard
        for i, a in enumerate(attrs):
            if (i + j) % 2 == 0:                                    # label a varying subset
                out.append(('...', 'attr', a, 'labels', 'doc', d))
    return list(dict.fromkeys(out))


# (name, schema_text, object_wildcard_shapes, tuples, read-parity grid or None)
_CORPORA = [
    ('wildcards', _WILDCARDS, OBJECT_WC, _wildcards_tuples(), _query_grid()),
    ('boolean', _BOOLEAN, frozenset(), _boolean_tuples(), _boolean_grid()),
    ('demorgan', _DEMORGAN, frozenset(), _demorgan_pool(_DEMORGAN), None),
    ('fanin', _FANIN, frozenset(), _fanin_tuples(), _fanin_grid()),
    ('derived_member', _DERIVED_MEMBER, frozenset(), _derived_member_tuples(),
     _derived_member_grid()),
    ('demorgan1', _DEMORGAN1, frozenset(), _demorgan1_tuples(), None),
]


# --------------------------------------------------------------------------- #
# Canonical projections (natural keys, never raw ids).
# --------------------------------------------------------------------------- #

def _id_to_key(session: Session, store_id: str) -> tuple[dict, list]:
    nodes = list(session.exec(select(NodeV4).where(NodeV4.store_id == store_id)).all())
    return {n.id: (n.predicate, n.type, n.name, n.wildcard) for n in nodes}, nodes


def _nodes_proj(session: Session, store_id: str) -> dict:
    _, nodes = _id_to_key(session, store_id)
    return {(n.predicate, n.type, n.name, n.wildcard): (n.implicit, n.reference_count)
            for n in nodes}


def _edges_proj(session: Session, store_id: str) -> dict:
    idmap, _ = _id_to_key(session, store_id)
    edges = session.exec(select(EdgeV4).where(EdgeV4.store_id == store_id)).all()
    return {(idmap[e.subject_id], idmap[e.object_id]):
            (e.direct_edge_count, e.indirect_edge_count, e.derived) for e in edges}


def _residues_proj(session: Session, store_id: str) -> dict:
    idmap, _ = _id_to_key(session, store_id)
    out: dict = {}
    for r in session.exec(select(ResidueV1).where(ResidueV1.store_id == store_id)).all():
        stars = frozenset(tuple(s) for s in json.loads(r.stars))
        neg = frozenset(idmap[i] for i in json.loads(r.neg))
        upos = frozenset(idmap[i] for i in json.loads(r.upos))
        out[idmap[r.object_node_id]] = (stars, neg, upos, r.version)
    return out


def _outbox_proj(session: Session, store_id: str) -> Counter:
    rows = session.exec(select(DeltaOutboxV1).where(DeltaOutboxV1.store_id == store_id)).all()
    return Counter(
        ((r.subject_type, r.subject_name, r.subject_predicate),
         (r.object_type, r.object_name, r.object_predicate), r.action)
        for r in rows)


def _assert_projection_equal(inc, bulk, kind: str, corpus: str) -> None:
    if inc == bulk:
        return
    keys = set(inc) | set(bulk)
    diff = {k: (inc.get(k), bulk.get(k)) for k in keys if inc.get(k) != bulk.get(k)}
    shown = sorted(diff.items(), key=lambda kv: repr(kv[0]))[:40]
    lines = '\n'.join(f'  {k!r}:  inc={a!r}  bulk={b!r}' for k, (a, b) in shown)
    pytest.fail(f'[{corpus}] {kind} projections differ ({len(diff)} differing key(s), '
                f'showing up to 40):\n{lines}')


# --------------------------------------------------------------------------- #

@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _seed_source(session: Session, store_id: str, schema: str, object_wc, tuples) -> list:
    """Write the tuple set through a TupleSource (admission-validated; dedup + any
    cycle-rejections handled by the source), commit, and return the RAW tuples that
    actually landed (read back from TupleV1) so the oracle sees exactly the store."""
    save_schema(session, store_id, schema, object_wc)
    src = TupleSource(session, store_id)
    for raw in tuples:
        try:
            src.add(*raw)
        except ValueError:
            # a tuple the admission validator rejects (e.g. a cycle from an
            # unordered pool) simply does not land; the read-back below is truth.
            pass
    session.commit()
    rows = session.exec(
        select(TupleV1).where(TupleV1.store_id == store_id).order_by(TupleV1.id)
    ).all()
    return [OracleTuple(r.subject_predicate, r.subject_type, r.subject_name,
                        r.relation, r.object_type, r.object_name) for r in rows]


def _leaf_kinds(compiled) -> set:
    return {spec.kind for plan in compiled.plans.values() for spec in plan.leaves}


def _assert_r4bf_features(name: str, compiled, nodes: dict, edges: dict,
                          residues: dict) -> None:
    """Anti-vacuity for the R4-BF gate extension (design §5): each new corpus must
    actually REACH the state-shaping feature it was added for, so it can't silently
    degrade into not testing the thing. Same spirit as the fanin multiplicity checks."""
    if compiled is None:
        return
    edge_keys = {a for (a, b) in edges} | {b for (a, b) in edges}
    subject_keys = {a for (a, b) in edges}
    # nodes pinned explicit (implicit False) that hold no edge and rc 0: a residue /
    # from-chain anchor alone keeps them alive (design item e).
    edge_free_explicit = {k for k, (implicit, rc) in nodes.items()
                          if implicit is False and rc == 0 and k not in edge_keys}
    recorded_in_residue: set = set()
    have_upos = False
    for obj_key, (stars, neg, upos, version) in residues.items():
        recorded_in_residue |= set(neg) | set(upos)
        if upos:
            have_upos = True

    if name == 'derived_member':
        # (a) derived-userset leaf + sticky promotion of a pre-existing implicit public
        #     node that also has an OUTGOING edge (closure extends through it).
        assert 'derived-userset' in _leaf_kinds(compiled), \
            '[derived_member] expected a derived-userset leaf kind'
        promoted_out = [k for k, (implicit, rc) in nodes.items()
                        if k[0] == 'member' and k[1] == 'group' and k[3] == ''
                        and implicit is False and k in subject_keys]
        assert promoted_out, \
            '[derived_member] expected a sticky-promoted member(group) public node ' \
            'with an outgoing edge (derived node extending the closure)'
        assert any(d for (_a, _b), (_dir, _ind, d) in edges.items()), \
            '[derived_member] expected processor-written derived edges'

    if name == 'demorgan1':
        # (c) derived-tupleset-ttu leaf + (d) >= 3 boolean strata; and an edge-free
        #     explicit rc=0 node (e).
        assert 'derived-tupleset-ttu' in _leaf_kinds(compiled), \
            '[demorgan1] expected a derived-tupleset-ttu leaf kind'
        assert len(compiled.strata) >= 3, \
            f'[demorgan1] expected >= 3 boolean strata; got {len(compiled.strata)}'
        assert edge_free_explicit, \
            '[demorgan1] expected an edge-free explicit rc=0 node (residue-anchored)'

    if name == 'demorgan':
        # (b) X4b upos lift + (e) a from-chain node recorded in upos/neg that is itself
        #     edge-free, explicit, rc=0 (anchored by the residue reference alone).
        assert 'derived-ttu' in _leaf_kinds(compiled), \
            '[demorgan] expected a derived-ttu leaf kind (X4b target)'
        assert have_upos, '[demorgan] expected a residue with non-empty upos (X4b lift)'
        assert recorded_in_residue & edge_free_explicit, \
            '[demorgan] expected a from-chain node recorded in a residue that is ' \
            'edge-free/explicit/rc=0'


@pytest.mark.parametrize('corpus', _CORPORA, ids=lambda c: c[0])
def test_bulk_build_identical_to_incremental(session, corpus):
    name, schema, object_wc, tuples, grid = corpus
    src_store = f'{name}_src'
    inc_store = f'{name}_inc'
    bulk_store = f'{name}_bulk'

    present = _seed_source(session, src_store, schema, object_wc, tuples)
    assert present, f'[{name}] no tuples landed -- corpus is vacuous'

    # Build the SAME snapshot two ways into two separate index stores.
    _, _, _ = build_index(session, src_store, inc_store, bulk=False)
    _, widx_bulk, rs_bulk = build_index(session, src_store, bulk_store, bulk=True)

    # (0) Belt-and-suspenders: the existing id-independent snapshot must match too.
    assert snapshot_rows(session, inc_store) == snapshot_rows(session, bulk_store), \
        f'[{name}] snapshot_rows differ'

    # (1-4) The four canonical projections, precise diff on any divergence.
    _assert_projection_equal(_nodes_proj(session, inc_store),
                             _nodes_proj(session, bulk_store), 'nodes', name)
    _assert_projection_equal(_edges_proj(session, inc_store),
                             _edges_proj(session, bulk_store), 'edges', name)
    _assert_projection_equal(_residues_proj(session, inc_store),
                             _residues_proj(session, bulk_store), 'residues', name)
    _assert_projection_equal(_outbox_proj(session, inc_store),
                             _outbox_proj(session, bulk_store), 'outbox', name)

    # The DP is genuinely exercised: multi-path diamonds give indirect counts > 1.
    edges = _edges_proj(session, bulk_store)
    max_indirect = max((v[1] for v in edges.values()), default=0)
    if name in ('wildcards', 'boolean'):
        assert max_indirect >= 2, \
            f'[{name}] expected path diamonds (indirect>=2); got max {max_indirect}'
    if name == 'fanin':
        # The multigraph dimension must actually be reached: some routed pair with
        # direct multiplicity >= 2 (editor+owner fan-in onto the shared viewer copy),
        # and some PURE-indirect pair whose count >= 2 came through an m>=2 edge
        # (the DP's multiplicity weighting, not just presence).
        max_direct = max((v[0] for v in edges.values()), default=0)
        assert max_direct >= 2, \
            f'[fanin] expected direct fan-in multiplicity >= 2; got max {max_direct}'
        assert any(v[0] == 0 and v[1] >= 2 for v in edges.values()), \
            '[fanin] expected a pure-indirect pair with count >= 2 through an m>=2 edge'

    # R4-BF gate extension (design §5): the new corpora must actually reach the
    # state-shaping features they were added for (anti-vacuity).
    _assert_r4bf_features(name, rs_bulk.compiled, _nodes_proj(session, bulk_store),
                          edges, _residues_proj(session, bulk_store))

    # I1-I13 invariant checker runs green on the bulk-built store.
    check_invariants(session, bulk_store, rs_bulk.schema_info, residue_versions={})

    # Read-parity spot grid vs the independent oracle (wildcard + boolean schemas).
    if grid is not None:
        oracle = Oracle(schema, present)
        mismatches = [(q, widx_bulk.check(*q), oracle.check(*q))
                      for q in grid if widx_bulk.check(*q) != oracle.check(*q)]
        assert not mismatches, (
            f'[{name}] read-parity vs oracle failed on {len(mismatches)} probe(s): '
            + '; '.join(f'{q}: bulk={g} oracle={e}' for q, g, e in mismatches[:10]))
