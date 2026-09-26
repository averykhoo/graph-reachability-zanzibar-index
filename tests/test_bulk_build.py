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


#  (e) the rc=0 explicit-node case, on demorgans_law_1's star-minus-concrete `non_labels`.
#      Until 2026-09-26 this corpus also carried (c) DERIVED-TUPLESET-TTU and (d) >= 3
#      BOOLEAN STRATA: the fixture chained three `from`s whose tuplesets were themselves
#      derived, across five strata. TK106 (user decision) made a non-direct tupleset a
#      parse refusal; the fixture was trimmed to its legal core and (c)/(d) left with it
#      (the `derived-tupleset-ttu` leaf is unreachable from a checked parse).
_DEMORGAN1 = _load_fga('demorgans_law_1.fga')


def _demorgan1_tuples(nattrs=3, ndocs=2) -> list[tuple]:
    attrs = [f'a{i}' for i in range(1, nattrs + 1)]
    docs = [f'd{i}' for i in range(1, ndocs + 1)]
    out: list[tuple] = []
    for j, d in enumerate(docs):
        out.append(('...', 'attr', '*', '_all_attrs', 'doc', d))   # attr:* subject wildcard
        for i, a in enumerate(attrs):
            if (i + j) % 2 == 0:                                    # label a varying subset
                out.append(('...', 'attr', a, 'labels', 'doc', d))
    return list(dict.fromkeys(out))


#  (f) STAR TUPLESET PARENT UNDER A DERIVED TTU -- the RC2 corpus, added 2026-08-11 with
#      the fix. `parent` carries a stored `doc:*` subject, so the TTUs over it must walk a
#      STAR parent: the shape (doc, viewer) unconditionally, plus the ∃-expansion over
#      instances of `doc`.
#
#      MOVED 2026-09-26 (TK106): until then `parent` was DERIVED (`[doc, doc:*] and gate`),
#      a boolean tupleset, now a parse refusal. The fix site
#      (`bulk_backfill.py::_stored_tupleset_subjects` / `_tupleset_parents`) is shared with
#      the `derived-ttu` path, so the corpus now reaches it with an UNTAINTED
#      `parent: [folder, doc, doc:*]` whose `folder#viewer` is derived. Sabotage S1 was
#      re-run on the new corpus, 2026-09-26: dropping star parents from
#      `bulk_backfill`'s `_stored_tupleset_subjects` ALONE, and separately from
#      `DeltaProcessor._stored_tupleset_subjects` alone, each gave (literal)
#      `AssertionError: [rc2_star_tupleset] snapshot_rows differ`, `1 failed`.
#
#      ⚠ WHY IT HAD TO BE ADDED. This gate was MEASURED BLIND to exactly this direction
#      before the corpus existed. One-sided sabotage S1 (restore `w2 == ''` in
#      `bulk_backfill._stored_tupleset_subjects` and drop the star arms, i.e. fix only
#      `processor.py`) left the suite 6 passed GREEN, while control S2 (`return []`)
#      reddened it 2/6 -- so the gate REACHED the function and the gap was the corpus:
#      nothing had a `T:*` subject holding a stored tupleset tuple on a derived tupleset
#      relation. `docs/spec-deviations.md` 2026-08-10 carries the measurement.
#
#      Both TTU directions are present deliberately: `inherited` (positive) fails CLOSED
#      on the bug and `access` (negated) fails OPEN, and probing only the positive one
#      mis-classifies the severity by one sign -- the general rule RC1/RC2 established.
_RC2_STAR_TUPLESET = """
model
  schema 1.1

type user

type folder
  relations
    define banned: [user]
    define viewer: [user] but not banned

type doc
  relations
    define parent: [folder, doc, doc:*]
    define viewer: [user]
    define inherited: viewer from parent
    define access: [user] but not viewer from parent
"""


def _rc2_star_tupleset_tuples(nusers=3, ndocs=4) -> list[tuple]:
    users = [f'u{i}' for i in range(1, nusers + 1)]
    docs = [f'd{i}' for i in range(1, ndocs + 1)]
    out: list[tuple] = []
    # the star tupleset parent
    out.append(('...', 'doc', '*', 'parent', 'doc', 'd1'))
    # a CONCRETE parent on another object, so the corpus drives both shapes and a
    # star-only regression cannot hide behind the concrete path
    out.append(('...', 'doc', 'd3', 'parent', 'doc', 'd2'))
    # a FOLDER parent, whose derived `viewer` is what makes the TTUs derived at all
    out.append(('...', 'folder', 'f1', 'parent', 'doc', 'd4'))
    out.append(('...', 'user', 'u1', 'viewer', 'folder', 'f1'))
    out.append(('...', 'user', 'u2', 'viewer', 'folder', 'f1'))
    out.append(('...', 'user', 'u2', 'banned', 'folder', 'f1'))
    for i, u in enumerate(users):
        for j, d in enumerate(docs):
            if (i + j) % 2 == 0:
                out.append(('...', 'user', u, 'viewer', 'doc', d))
            if (i + j) % 3 == 0:
                out.append(('...', 'user', u, 'access', 'doc', d))
    return list(dict.fromkeys(out))


def _rc2_star_tupleset_grid() -> list[tuple]:
    subjects = ([('...', 'user', f'u{i}') for i in range(1, 4)]
                + [('viewer', 'doc', f'd{i}') for i in range(1, 5)])
    return [(sp, st, sn, rel, 'doc', on)
            for (sp, st, sn) in subjects
            for rel in ('inherited', 'access', 'parent', 'viewer')
            for on in [f'd{i}' for i in range(1, 5)]]


#  (g) OBJECT-WILDCARD GRANT CARRIED BY A STAR TUPLESET INTO A TTU -- the `owc_star_ttu`
#      corpus, added 2026-09-16 to close `P22`. It exists for ONE reason: it is the first
#      corpus in this module whose `schema_info.crossable_shapes` is NON-EMPTY, i.e. the
#      first that reaches the I14 crossable-middle loop in `index_v4/bulk_build.py`.
#
#      ⚠ WHY IT HAD TO BE ADDED -- A GREEN SABOTAGE THAT STAYED GREEN FOR TEN DAYS.
#      `P22` (filed 2026-09-06b by the `P17` sweep) deleted that loop OUTRIGHT and every
#      `build_index` caller stayed GREEN: this module, `formal/conformance/
#      test_conformance_bulk_state.py` over all 25 `GRAPH_FRAGMENT` corpora, and the
#      validation matrix. The cause was corpus coverage, not a weak assertion -- every
#      other `_CORPORA` entry has `crossable_shapes = frozenset()`, because
#      `zanzibar_utils_v1.py::_reject_doubly_bridged_shapes` intersects only LITERAL
#      `T:*#p` shapes, while a star-tupleset THROUGH-shape makes the set non-empty on a
#      schema the compiler admits.
#
#      THE SHAPE, and why each of the three tuples is load-bearing: an object-wildcard
#      grant (`u1 viewer folder:*`) creates `w_all(folder,viewer)`; a bare-star tupleset
#      parent (`folder:* parent doc:d1`) carries it into `doc.viewer`'s `or viewer from
#      parent`; and the WITNESS (`u1 editor folder:f1`) mentions `folder:f1` WITHOUT ever
#      putting a `viewer` triple on it, so the middle `w_all(folder,viewer) ->
#      folder:f1#viewer -> w_any(folder,viewer)` exists only if the I14 loop creates it.
#      Drop any one of the three and the loop is not reached.
#
#      MEASURED (literal, 2026-09-16, `formal/probes/
#      bulk_i14_crossable_middle_2026-09-16.py`, rc=0): on the shipped tree
#      `inc=True bulk=True oracle=True` for all three probes; with the loop's only guard
#      neutered (`SchemaInfo.crossable_shapes -> frozenset()`),
#
#          SABOTAGE-RED: q=(..., 'u1', 'viewer', 'doc', 'd1') bulk_no_i14=False oracle=True
#
#      i.e. a MISSING GRANT, while the two controls -- the object-wildcard leg
#      (`folder:f1#viewer`) and the plain direct edge (`folder:f1#editor`) -- stayed
#      green. One mechanism moved, not the whole build, which is what makes it evidence
#      about this clause rather than a broken instrument
#      (`docs/sabotage-procedure.md` §"Sweep the TEST MODULE with mutations").
_OWC_STAR_TTU = """
model
  schema 1.1

type user

type group
  relations
    define member: [user, group#member]

type folder
  relations
    define parent: [folder, folder:*]
    define blocked: [user]
    define editor: [user, group#member]
    define viewer: [user, user:*, group#member] or viewer from parent
    define restricted: editor but not blocked

type doc
  relations
    define parent: [folder, folder:*]
    define blocked: [user]
    define editor: [user, group#member]
    define viewer: [user, user:*, group#member] or viewer from parent
    define restricted: editor but not blocked
"""

_OWC_STAR_TTU_WC = frozenset({('folder', 'viewer'), ('doc', 'viewer')})


def _owc_star_ttu_tuples() -> list[tuple]:
    # ⚠ All three are load-bearing (see the comment block above); do not "simplify".
    out: list[tuple] = [
        ('...', 'user', 'u1', 'editor', 'folder', 'f1'),   # witness: names f1, NOT via viewer
        ('...', 'user', 'u1', 'viewer', 'folder', '*'),    # object-wildcard grant -> w_all
        ('...', 'folder', '*', 'parent', 'doc', 'd1'),     # bare star tupleset parent
    ]
    # ⚠ NOTHING MAY BE ADDED HERE THAT GIVES ANY `folder` A CONCRETE `viewer`
    #   GRANT OR A CONCRETE `parent` EDGE -- either one MASKS this corpus, and a
    #   masked corpus is the exact failure `P22` was filed for. This is MEASURED, not
    #   reasoned (2026-09-16, `.scratch` diag re-run in the probe's part (B) form;
    #   the four candidates were the "extra coverage" this corpus shipped with for
    #   one session before the sabotage caught it):
    #
    #       minimal 3 tuples               -> sabotage RED   (1 oracle mismatch)
    #       + ('folder','f2','parent','doc','d2')  -> sabotage GREEN  (MASKS)
    #       + ('user','u2','viewer','folder','f2') -> sabotage GREEN  (MASKS)
    #       + ('user','u2','blocked','folder','f2')-> sabotage RED    (safe)
    #       + ('user','u2','editor','folder','f2') -> sabotage RED    (safe)
    #
    #   Both maskers work the same way: they give the generic bridged-in/out loop a
    #   CONCRETE `viewer(folder, _)` node to bridge, which completes the w_all ->
    #   middle -> w_any crossing without the I14 loop, so every grid answer stays
    #   right while the loop's own product is gone. The two safe tuples touch only
    #   `editor`/`blocked`, so they add the `restricted: editor but not blocked`
    #   boolean arm without ever interning a concrete `viewer` middle.
    out += [
        ('...', 'user', 'u2', 'blocked', 'folder', 'f2'),
        ('...', 'user', 'u2', 'editor', 'folder', 'f2'),
    ]
    return list(dict.fromkeys(out))


def _owc_star_ttu_grid() -> list[tuple]:
    subjects = [('...', 'user', 'u1'), ('...', 'user', 'u2')]
    out = [(sp, st, sn, rel, ot, on)
           for (sp, st, sn) in subjects
           for (rel, ot, on) in (('viewer', 'doc', 'd1'), ('viewer', 'doc', 'd2'),
                                 ('viewer', 'folder', 'f1'), ('viewer', 'folder', 'f2'),
                                 ('editor', 'folder', 'f1'), ('editor', 'folder', 'f2'),
                                 ('restricted', 'folder', 'f2'))]
    return out


# (name, schema_text, object_wildcard_shapes, tuples, read-parity grid or None)
_CORPORA = [
    ('wildcards', _WILDCARDS, OBJECT_WC, _wildcards_tuples(), _query_grid()),
    ('boolean', _BOOLEAN, frozenset(), _boolean_tuples(), _boolean_grid()),
    ('demorgan', _DEMORGAN, frozenset(), _demorgan_pool(_DEMORGAN), None),
    ('fanin', _FANIN, frozenset(), _fanin_tuples(), _fanin_grid()),
    ('derived_member', _DERIVED_MEMBER, frozenset(), _derived_member_tuples(),
     _derived_member_grid()),
    ('demorgan1', _DEMORGAN1, frozenset(), _demorgan1_tuples(), None),
    ('rc2_star_tupleset', _RC2_STAR_TUPLESET, frozenset(),
     _rc2_star_tupleset_tuples(), _rc2_star_tupleset_grid()),
    ('owc_star_ttu', _OWC_STAR_TTU, _OWC_STAR_TTU_WC,
     _owc_star_ttu_tuples(), _owc_star_ttu_grid()),
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
        # an edge-free explicit rc=0 node (e). ((c) and (d) retired 2026-09-26, TK106.)
        assert edge_free_explicit, \
            '[demorgan1] expected an edge-free explicit rc=0 node (residue-anchored)'

    if name == 'rc2_star_tupleset':
        # (f) RC2. Three separate things must hold, because each is a way this corpus
        #     could silently stop testing what it was added for:
        #       1. the leaf kind is reached at all (the TTU target really is derived);
        #       2. a `doc:*` subject really holds an edge into `parent` -- a stored TTU
        #          parent rather than decoration (before TK106, 2026-09-26, into a
        #          STORAGE leaf of the then-derived `parent`);
        #       3. some residue carries the star SHAPE (doc, viewer), which is the half
        #          of the star rule the ∃-expansion over instances cannot express.
        #     Without 2 and 3 a regression could drop the star arm and still pass 1.
        assert 'derived-ttu' in _leaf_kinds(compiled), \
            '[rc2_star_tupleset] expected a derived-ttu leaf kind'
        assert ('doc', 'parent') not in compiled.plans, \
            '[rc2_star_tupleset] `parent` must stay an UNTAINTED (direct) tupleset'
        star_on_parent = [(a, b) for (a, b) in edges
                          if a[2] == '*' and a[3] == 'any' and a[1] == 'doc'
                          and b[1] == 'doc' and b[0] == 'parent']
        assert star_on_parent, (
            '[rc2_star_tupleset] no `doc:*` subject edge lands on `parent` -- the corpus '
            'is not driving the star tupleset parent it exists for')
        assert any(('doc', 'viewer') in {tuple(s) for s in stars}
                   for (stars, _neg, _upos, _v) in residues.values()), \
            '[rc2_star_tupleset] no residue carries the star shape (doc, viewer); the ' \
            'star-parent SHAPE rule is not being exercised'

    if name == 'owc_star_ttu':
        # (g) I14 CROSSABLE MIDDLE, bulk path. The grid alone is NOT enough here and that
        #     is the whole lesson of `P22`: an extra tuple that grants some folder a
        #     CONCRETE `viewer` lets the generic bridged-in/out loop build the crossing,
        #     so every answer stays right while the I14 loop's own product is gone (the
        #     measurement is in `_owc_star_ttu_tuples`). So pin the PRODUCT structurally.
        #
        #     `folder:f1` is named by an `editor` tuple ONLY -- it never holds a `viewer`
        #     triple -- so its `viewer` middle and the two bridges around it can be
        #     created by nothing but `bulk_build.py`'s crossable-shape loop (the
        #     `WildcardIndex._ensure_entity_middles` mirror). DERIVED, not guessed: the
        #     three keys below are the literal shipped state on this corpus, 2026-09-16.
        w_all = ('viewer', 'folder', '*', 'all')
        w_any = ('viewer', 'folder', '*', 'any')
        mid = ('viewer', 'folder', 'f1', '')
        assert mid in nodes, (
            '[owc_star_ttu] no `viewer(folder, f1)` middle node -- `f1` holds no viewer '
            'triple, so this node exists only if the I14 crossable-middle loop ran')
        assert (w_all, mid) in edges and (mid, w_any) in edges, (
            '[owc_star_ttu] the w_all -> viewer(folder, f1) -> w_any crossing is not '
            f'bridged (have {(w_all, mid) in edges}/{(mid, w_any) in edges}); the I14 '
            'crossable-middle loop did not run for this entity')
        # ⚠ ANTI-MASK CONTROL. If some later edit gives a folder a concrete `viewer`
        #   grant, the crossing above could be satisfied WITHOUT the loop and this clause
        #   would silently stop testing it. Refuse that corpus mechanically rather than
        #   warning about it in a comment.
        concrete_viewer_folders = {b[2] for (_a, b), (direct, _ind, _d) in edges.items()
                                   if b[0] == 'viewer' and b[1] == 'folder' and b[3] == ''
                                   and _a[0] == '...' and direct > 0}
        assert not concrete_viewer_folders, (
            '[owc_star_ttu] a concrete `viewer` grant on folder(s) '
            f'{sorted(concrete_viewer_folders)} MASKS the I14 loop (see '
            '`_owc_star_ttu_tuples`) -- this corpus must keep `viewer` reachable on a '
            'folder only through the object wildcard')

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
