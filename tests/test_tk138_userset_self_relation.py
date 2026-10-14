"""TK138 landing 1 -- a userset is NOT related to itself here; in OpenFGA it is.

Property guarded (a POSITIVE DIVERGENCE PIN, not an xfail)
----------------------------------------------------------
OpenFGA treats a userset subject ``o#r`` as a member of ``(o, r)`` unconditionally, at
every resolve node and outside the rewrite: ``Members(o, r) = {o#r} ∪ Eval(rewrite(r))``.
So it propagates through computed usersets, TTU and boolean arms, across objects, and
it can flip a ``but not`` from ALLOW to DENY (the ``vx`` row). This library does not
apply that rule, except at a TTU target reached through a stored parent (the
2026-07-13 X4a from-chain disjunct), where it agrees by accident of representation.
Map, probes and decision: ``docs/tk138-userset-self-relation-2026-10-14.md``; ledger
entry: ``docs/spec-deviations.md`` ``## 2026-10-14 — TK138``.

Every row below carries TWO literal answers:

* ``openfga`` -- transcribed by hand from the live OpenFGA v1.22.0 server transcripts
  in the plan doc (section 1.1 model A, section 1.2 model B, challenge C1 model C,
  challenge C3 model D). It is NEVER derived from ``tests/oracle.py``, so the oracle
  cannot drift together with it.
* ``repo`` -- today's answer, asserted UNANIMOUS on every corner: ``check`` through
  ``tests/parity.py::ParityEngine`` (graph index, set engine under both ``SetOps``,
  and the oracle), lookups computed on the graph and both set engines and required
  to agree after translation to ``(type, name, predicate)`` keys.

On top of the row-by-row pin, each model asserts the EXACT set of row ids where
repo != OpenFGA (``EXPECTED_DIVERGENT``). The moment any corner moves -- landing 2
(the semantic change), or an accidental change -- this file goes red and must be
edited deliberately, together with the deviations entry. Rows that must NOT move
are in the same tables: the TTU from-chain rows (True on both sides), concrete-user
rows, ``user:*`` and the userset-star subject (``REPO_ONLY``, no OpenFGA probe), and
the self-tuple write refusal (both refuse it; this repo as a cycle, OpenFGA as
"implicit" -- challenge C6).

Model provenance
----------------
* Model A' is the plan doc's model A MINUS ``viewer_bn``, ``vi``, ``banned2`` and
  ``viewer_bn3`` (this repo refuses ``viewer_bn3``/``banned2`` as recursion through
  negation and ``vi`` as a cyclic derived dependency on the graph; ``viewer_bn`` and
  ``vi`` cannot be kept in their probed form). Dropping them, rather than editing
  them as the scout's repo probe did, keeps every remaining definition byte-identical
  to the probed one, so OpenFGA's answers for the remaining relations transfer
  unchanged: none of the remaining relations reaches a dropped one, and the dropped
  write ``doc:1#viewer_bn3 banned2 doc:1`` is read only by ``banned2`` (REASONED).
  Rows on the dropped relations are omitted, not transferred.
* Models B, C and D are the probed models exactly.
* ``ListObjects`` rows project ``lookup(subject)`` onto ``(type, relation)``;
  ``ListUsers`` rows project ``lookup_reverse(relation, object)`` onto the filter
  (``T#r`` = userset keys of type ``T`` and relation ``r``; ``T`` = bare subjects).

Repo answers were measured first-hand 2026-10-14 (``build-TK138-L1``) and agree with
the plan doc's section 2 and C1 transcripts.

Sabotage (2026-10-14, docs/sabotage-procedure.md, the plan doc's section 7.1 oracle
instrument). In ``tests/oracle.py::Oracle.check.sat`` ONLY, the line
``result = sat_expr(expr, o_type, o_name, rel)`` was replaced (anchor asserted to occur
exactly once) by OpenFGA's disjunct
``result = ((subject[2] != '...' and subject[1] != '*' and subject == (o_type, o_name,
rel)) or sat_expr(expr, o_type, o_name, rel))``; no backend touched. Result
``4 failed, 3 passed in 0.65s`` (models A, B, C and the ``vx`` test red), literal::

    AssertionError: check disagreement on ('viewer', 'doc', '1', 'viewer', 'doc', '1'): {'graph': False, 'set:py': False, 'set:roaring': False, 'oracle': True}
    AssertionError: check disagreement on ('plain', 'doc', '1', 'plain', 'doc', '1'): {'graph': False, 'set:py': False, 'set:roaring': False, 'oracle': True}
    AssertionError: check parity broken after add ('member', 'group', '1', 'viewer', 'doc', '1'): q=('admin', 'group', '1', 'nb', 'doc', '1') graph=False oracle=True
    AssertionError: check disagreement on ('plain', 'doc', '1', 'plain', 'doc', '1'): {'graph': False, 'set:py': False, 'set:roaring': False, 'oracle': True}

Model D and the write-refusal test stay green under it, as they should: the instrument
does not move the C3 row, and refused writes are not grid-checked. Restored from a byte
copy; ``grep -c SABOTAGE tests/oracle.py`` 0 and ``git status`` clean for it.

Instrument control (same day): with ``_lookup_keys`` blinded to return ``set()``, models
A, B and C go red on their non-empty lookup rows, e.g.
``model B: repo answers moved (row: pinned, measured): {'B17': ({'doc:1'}, set()),
'B18': ({'doc:1#banned'}, set())}`` -- so the lookup projection is not vacuous.
"""

from __future__ import annotations

import pytest

from zanzibar.graphindex import Node

from tests.parity import ParityEngine

T, F = True, False
ERR = 'ERR'           # OpenFGA answered 400 validation_error; this repo reads leniently

# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #

MODEL_A = """
model
  schema 1.1
type user
type folder
  relations
    define viewer: [user, folder#viewer]
    define plain: [user]
type doc
  relations
    define viewer: [user, doc#viewer]
    define banned: [user]
    define editor: [user]
    define plain: [user]
    define parent: [folder]
    define can_view: viewer
    define fview: viewer from parent
    define fplain: plain from parent
    define vu: [user] or editor
    define nb: viewer but not banned
"""

MODEL_B = """
model
  schema 1.1
type user
type doc
  relations
    define banned: [user]
    define editor: [user]
    define plain: [user]
    define viewer: [user, doc#viewer]
    define vx: [user, doc#banned] but not banned
    define vy: [user, doc#editor] and editor
    define nb: viewer but not banned
    define chain: [user, doc#viewer]
    define cv: plain
"""

MODEL_C = """
model
  schema 1.1
type user
type group
  relations
    define admin: [user]
    define member: [user] or admin
type doc
  relations
    define viewer: [user, group#member]
    define banned: [user, group#admin]
    define nb: viewer but not banned
"""

# Challenge C3: a TTU target declared on only one of the tupleset's types (ASK-1 allows it).
MODEL_D = """
model
  schema 1.1
type user
type team
type folder
  relations
    define viewer: [user]
type doc
  relations
    define parent: [folder, team]
    define x: viewer from parent
"""

# --------------------------------------------------------------------------- #
# Row encoding.  Subjects and objects are 'type:name' / 'type:name#relation'.
#   ('CHECK',   subject, relation, object)
#   ('LISTOBJ', subject, 'type#relation')                -> set of 'type:name'
#   ('LISTUSR', object, relation, filter)                -> set of subjects
#   ('WRITE',   subject, relation, object)               -> 'ok' | 'refused'
# A row is (row_id, phase, query, openfga, repo); phase 'empty' runs before the
# model's writes, 'write' is a write, 'after' runs after all writes.
# --------------------------------------------------------------------------- #

ROWS_A = [
    # plan doc 1.1, "== empty store ==" (openfga_probe.out)
    ('A01', 'empty', ('CHECK', 'doc:1#viewer', 'viewer', 'doc:1'), T, F),
    ('A02', 'empty', ('CHECK', 'doc:1#viewer', 'viewer', 'doc:2'), F, F),
    ('A03', 'empty', ('CHECK', 'doc:1#editor', 'viewer', 'doc:1'), F, F),
    ('A04', 'empty', ('CHECK', 'doc:1#plain', 'plain', 'doc:1'), T, F),
    ('A05', 'empty', ('CHECK', 'doc:1#banned', 'banned', 'doc:1'), T, F),
    ('A06', 'empty', ('CHECK', 'doc:1#can_view', 'can_view', 'doc:1'), T, F),
    ('A07', 'empty', ('CHECK', 'doc:1#viewer', 'can_view', 'doc:1'), T, F),
    ('A08', 'empty', ('CHECK', 'doc:1#fview', 'fview', 'doc:1'), T, F),
    ('A09', 'empty', ('CHECK', 'doc:1#vu', 'vu', 'doc:1'), T, F),
    ('A10', 'empty', ('CHECK', 'doc:1#nb', 'nb', 'doc:1'), T, F),
    ('A11', 'empty', ('CHECK', 'doc:1#viewer', 'nb', 'doc:1'), T, F),
    ('A12', 'empty', ('CHECK', 'folder:1#viewer', 'viewer', 'folder:1'), T, F),
    ('A13', 'empty', ('CHECK', 'folder:1#viewer', 'fview', 'doc:1'), F, F),
    ('A14', 'empty', ('CHECK', 'doc:1#nosuchrel', 'nosuchrel', 'doc:1'), ERR, F),
    ('A15', 'empty', ('LISTOBJ', 'doc:1#viewer', 'doc#viewer'), {'doc:1'}, set()),
    ('A16', 'empty', ('LISTOBJ', 'doc:1#viewer', 'doc#can_view'), {'doc:1'}, set()),
    ('A17', 'empty', ('LISTUSR', 'doc:1', 'viewer', 'doc#viewer'), {'doc:1#viewer'}, set()),
    ('A18', 'empty', ('LISTUSR', 'doc:1', 'can_view', 'doc#viewer'), {'doc:1#viewer'}, set()),
    ('A19', 'empty', ('LISTUSR', 'doc:1', 'viewer', 'user'), set(), set()),
    # "== writes ==" (the banned2 write is on a dropped relation; see the docstring)
    ('A20', 'write', ('WRITE', 'doc:1#viewer', 'viewer', 'doc:1'), 'refused', 'refused'),
    ('A21', 'write', ('WRITE', 'doc:1#viewer', 'viewer', 'doc:2'), 'ok', 'ok'),
    ('A22', 'write', ('WRITE', 'user:alice', 'viewer', 'doc:1'), 'ok', 'ok'),
    ('A23', 'write', ('WRITE', 'user:bob', 'banned', 'doc:1'), 'ok', 'ok'),
    ('A24', 'write', ('WRITE', 'user:bob', 'viewer', 'doc:1'), 'ok', 'ok'),
    ('A25', 'write', ('WRITE', 'folder:1', 'parent', 'doc:1'), 'ok', 'ok'),
    ('A26', 'write', ('WRITE', 'user:carol', 'viewer', 'folder:1'), 'ok', 'ok'),
    # "== after writes =="
    ('A27', 'after', ('CHECK', 'doc:1#viewer', 'viewer', 'doc:1'), T, F),
    ('A28', 'after', ('CHECK', 'doc:1#viewer', 'viewer', 'doc:2'), T, T),
    ('A29', 'after', ('CHECK', 'folder:1#viewer', 'fview', 'doc:1'), T, T),   # TTU from-chain
    ('A30', 'after', ('CHECK', 'folder:1#plain', 'fplain', 'doc:1'), T, T),   # TTU from-chain
    ('A31', 'after', ('CHECK', 'folder:2#viewer', 'fview', 'doc:1'), F, F),
    ('A32', 'after', ('CHECK', 'user:alice', 'viewer', 'doc:2'), T, T),
    ('A33', 'after', ('CHECK', 'user:bob', 'nb', 'doc:1'), F, F),
    ('A34', 'after', ('LISTOBJ', 'doc:1#viewer', 'doc#viewer'), {'doc:1', 'doc:2'}, {'doc:2'}),
    ('A35', 'after', ('LISTOBJ', 'doc:1#viewer', 'doc#can_view'), {'doc:1', 'doc:2'}, {'doc:2'}),
    ('A36', 'after', ('LISTOBJ', 'folder:1#viewer', 'doc#fview'), {'doc:1'}, {'doc:1'}),
    ('A37', 'after', ('LISTOBJ', 'folder:1#viewer', 'folder#viewer'), {'folder:1'}, set()),
    ('A38', 'after', ('LISTUSR', 'doc:1', 'viewer', 'doc#viewer'), {'doc:1#viewer'}, set()),
    ('A39', 'after', ('LISTUSR', 'doc:2', 'viewer', 'doc#viewer'),
     {'doc:2#viewer', 'doc:1#viewer'}, {'doc:1#viewer'}),
    ('A40', 'after', ('LISTUSR', 'doc:1', 'fview', 'folder#viewer'),
     {'folder:1#viewer'}, {'folder:1#viewer'}),
    ('A41', 'after', ('LISTUSR', 'doc:2', 'viewer', 'user'),
     {'user:alice', 'user:bob'}, {'user:alice', 'user:bob'}),
]

ROWS_B = [
    # plan doc 1.2 (openfga_probe2.out)
    ('B01', 'empty', ('CHECK', 'doc:1#plain', 'plain', 'doc:1'), T, F),
    ('B02', 'empty', ('LISTOBJ', 'doc:1#plain', 'doc#plain'), {'doc:1'}, set()),
    ('B03', 'empty', ('LISTUSR', 'doc:1', 'plain', 'doc#plain'), {'doc:1#plain'}, set()),
    ('B04', 'empty', ('CHECK', 'doc:1#plain', 'cv', 'doc:1'), T, F),
    ('B05', 'empty', ('LISTOBJ', 'doc:1#plain', 'doc#cv'), {'doc:1'}, set()),
    ('B06', 'empty', ('LISTUSR', 'doc:1', 'cv', 'doc#plain'), {'doc:1#plain'}, set()),
    ('B07', 'empty', ('CHECK', 'doc:1#viewer', 'nb', 'doc:1'), T, F),
    ('B08', 'empty', ('LISTOBJ', 'doc:1#viewer', 'doc#nb'), {'doc:1'}, set()),
    ('B09', 'empty', ('LISTUSR', 'doc:1', 'nb', 'doc#viewer'), {'doc:1#viewer'}, set()),
    ('B10', 'write', ('WRITE', 'doc:1#banned', 'vx', 'doc:1'), 'ok', 'ok'),
    ('B11', 'write', ('WRITE', 'doc:1#editor', 'vy', 'doc:1'), 'ok', 'ok'),
    ('B12', 'write', ('WRITE', 'doc:1#viewer', 'chain', 'doc:2'), 'ok', 'ok'),
    ('B13', 'write', ('WRITE', 'doc:2#chain', 'viewer', 'doc:3'), 'refused', 'refused'),
    # the vx row: ALLOWED here, DENIED by OpenFGA (self in the subtrahend)
    ('B14', 'after', ('CHECK', 'doc:1#banned', 'vx', 'doc:1'), F, T),
    ('B15', 'after', ('CHECK', 'doc:1#banned', 'vx', 'doc:2'), F, F),
    ('B16', 'after', ('CHECK', 'doc:1#editor', 'vy', 'doc:1'), T, F),
    ('B17', 'after', ('LISTOBJ', 'doc:1#banned', 'doc#vx'), set(), {'doc:1'}),
    ('B18', 'after', ('LISTUSR', 'doc:1', 'vx', 'doc#banned'), set(), {'doc:1#banned'}),
    ('B19', 'after', ('LISTOBJ', 'doc:1#editor', 'doc#vy'), {'doc:1'}, set()),
    ('B20', 'after', ('LISTUSR', 'doc:1', 'vy', 'doc#editor'), {'doc:1#editor'}, set()),
    ('B21', 'after', ('CHECK', 'doc:1#viewer', 'chain', 'doc:2'), T, T),
    ('B22', 'after', ('CHECK', 'doc:2#chain', 'chain', 'doc:2'), T, F),
]

ROWS_C = [
    # challenge C1 (openfga_probe3.out); the server was asked only after the writes
    ('C01', 'write', ('WRITE', 'group:1#member', 'viewer', 'doc:1'), 'ok', 'ok'),
    ('C02', 'write', ('WRITE', 'group:1#member', 'viewer', 'doc:2'), 'ok', 'ok'),
    ('C03', 'write', ('WRITE', 'group:1#admin', 'banned', 'doc:2'), 'ok', 'ok'),
    ('C04', 'write', ('WRITE', 'user:alice', 'admin', 'group:1'), 'ok', 'ok'),
    ('C05', 'write', ('WRITE', 'group:3#member', 'viewer', 'doc:1'), 'ok', 'ok'),
    ('C06', 'after', ('CHECK', 'group:1#admin', 'viewer', 'doc:1'), T, F),
    ('C07', 'after', ('CHECK', 'group:1#admin', 'nb', 'doc:1'), T, F),
    ('C08', 'after', ('CHECK', 'group:3#admin', 'viewer', 'doc:1'), T, F),
    ('C09', 'after', ('CHECK', 'group:3#admin', 'nb', 'doc:1'), T, F),
    ('C10', 'after', ('CHECK', 'group:1#member', 'nb', 'doc:1'), T, T),
    ('C11', 'after', ('CHECK', 'group:1#admin', 'nb', 'doc:2'), F, F),
    ('C12', 'after', ('CHECK', 'group:1#member', 'nb', 'doc:2'), T, T),
    ('C13', 'after', ('CHECK', 'user:alice', 'nb', 'doc:2'), F, F),
    ('C14', 'after', ('CHECK', 'user:alice', 'nb', 'doc:1'), T, T),
    ('C15', 'after', ('LISTOBJ', 'group:1#admin', 'doc#viewer'), {'doc:1', 'doc:2'}, set()),
    ('C16', 'after', ('LISTOBJ', 'group:1#admin', 'doc#nb'), {'doc:1'}, set()),
    ('C17', 'after', ('LISTOBJ', 'group:3#admin', 'doc#nb'), {'doc:1'}, set()),
    ('C18', 'after', ('LISTUSR', 'doc:1', 'nb', 'group#admin'),
     {'group:1#admin', 'group:3#admin'}, set()),
    ('C19', 'after', ('LISTUSR', 'doc:2', 'nb', 'group#member'),
     {'group:1#member'}, {'group:1#member'}),
]

ROWS_D = [
    # challenge C3 (openfga_probe5.out: "relation 'team#viewer' not found"). This repo
    # answers True through the ttu_leaf from-chain disjunct, which TK138 keeps (D4).
    ('D01', 'write', ('WRITE', 'team:1', 'parent', 'doc:1'), 'ok', 'ok'),
    ('D02', 'write', ('WRITE', 'folder:1', 'parent', 'doc:1'), 'ok', 'ok'),
    ('D03', 'after', ('CHECK', 'team:1#viewer', 'x', 'doc:1'), ERR, T),
]

# Pins with NO OpenFGA probe behind them: they must not move under landing 2 either
# (the rule adds only the subject o#r itself -- never its members, never a star subject).
REPO_ONLY = {
    'A': [('after', ('CHECK', 'user:*', 'viewer', 'doc:1'), F),
          ('after', ('CHECK', 'user:*', 'nb', 'doc:1'), F),
          ('after', ('CHECK', 'doc:*#viewer', 'viewer', 'doc:1'), F),   # D1: userset star
          ('after', ('CHECK', 'doc:*#viewer', 'viewer', 'doc:2'), F),
          ('after', ('CHECK', 'user:carol', 'fview', 'doc:1'), T),
          ('after', ('CHECK', 'user:alice', 'can_view', 'doc:1'), T),
          ('after', ('CHECK', 'user:bob', 'can_view', 'doc:2'), T)],
    'B': [('after', ('CHECK', 'user:*', 'vx', 'doc:1'), F),
          ('after', ('CHECK', 'doc:*#banned', 'vx', 'doc:1'), F)],
    'C': [('after', ('CHECK', 'user:*', 'nb', 'doc:1'), F),
          ('after', ('CHECK', 'group:*#admin', 'nb', 'doc:1'), F)],
    'D': [('after', ('CHECK', 'folder:1#viewer', 'x', 'doc:1'), T)],   # C3's control row
}

# The literal divergence sets: every row id where repo != OpenFGA today.
EXPECTED_DIVERGENT = {
    'A': {'A01', 'A04', 'A05', 'A06', 'A07', 'A08', 'A09', 'A10', 'A11', 'A12', 'A14',
          'A15', 'A16', 'A17', 'A18', 'A27', 'A34', 'A35', 'A37', 'A38', 'A39'},
    'B': {'B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09',
          'B14', 'B16', 'B17', 'B18', 'B19', 'B20', 'B22'},
    'C': {'C06', 'C07', 'C08', 'C09', 'C15', 'C16', 'C17', 'C18'},
    'D': {'D03'},
}

MODELS = {
    'A': (MODEL_A, ROWS_A),
    'B': (MODEL_B, ROWS_B),
    'C': (MODEL_C, ROWS_C),
    'D': (MODEL_D, ROWS_D),
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _ent(text: str) -> tuple[str, str, str]:
    """'type:name[#pred]' -> (type, name, pred) with '...' for a bare subject."""
    ent, _, pred = text.partition('#')
    t, _, n = ent.partition(':')
    return t, n, pred or '...'


def _render(key: tuple[str, str, str]) -> str:
    t, n, p = key
    return f'{t}:{n}' if p == '...' else f'{t}:{n}#{p}'


def _raw(subject: str, relation: str, obj: str) -> tuple[str, ...]:
    st, sn, sp = _ent(subject)
    ot, on, _ = _ent(obj)
    return sp, st, sn, relation, ot, on


def _lookup_keys(pe: ParityEngine, kind: str, *args) -> set[tuple[str, str, str]]:
    """``lookup`` / ``lookup_reverse`` on the graph and BOTH set engines, translated to
    portable keys and required to agree (ParityEngine pins check parity only)."""
    assert pe.graph is not None, pe.graph_drop_reason
    answers = {}
    g = getattr(pe.graph.widx, kind)(*args)
    keys = set()
    for nid in g.node_ids:
        node = pe.graph.session.get(Node, nid)
        assert node is not None, f'dead graph node id {nid}'
        keys.add((node.type, node.name, node.predicate))
    answers['graph'] = (frozenset(keys), frozenset(g.markers), frozenset(g.excluded_node_ids))
    for side in pe.set_sides:
        r = getattr(side.se, kind)(*args)
        answers[side.name] = (frozenset(side.se.result_keys(r)), frozenset(r.markers),
                              frozenset(side.se.excluded_keys(r)))
    assert len(set(answers.values())) == 1, f'{kind}{args} disagrees across corners: {answers}'
    nodes, markers, excluded = answers['graph']
    # No row here involves a wildcard: a marker or an exclusion would need its own row.
    assert not markers and not excluded, f'{kind}{args}: unexpected {markers} / {excluded}'
    return set(nodes)


def _ask(pe: ParityEngine, query: tuple):
    kind = query[0]
    if kind == 'CHECK':
        _, subject, relation, obj = query
        return pe.check(*_raw(subject, relation, obj))           # unanimous incl. oracle
    if kind == 'WRITE':
        _, subject, relation, obj = query
        return 'ok' if pe.add_tuple(*_raw(subject, relation, obj)) else 'refused'
    if kind == 'LISTOBJ':
        _, subject, target = query
        st, sn, sp = _ent(subject)
        o_type, _, rel = target.partition('#')
        keys = _lookup_keys(pe, 'lookup', sp, st, sn)
        return {f'{t}:{n}' for (t, n, p) in keys if t == o_type and p == rel}
    if kind == 'LISTUSR':
        _, obj, relation, filt = query
        ot, on, _ = _ent(obj)
        f_type, _, f_rel = filt.partition('#')
        f_rel = f_rel or '...'
        keys = _lookup_keys(pe, 'lookup_reverse', relation, ot, on)
        return {_render(k) for k in keys if k[0] == f_type and k[2] == f_rel}
    raise AssertionError(f'unknown row kind {kind!r}')


def _run_model(model: str):
    """Run the model's rows in phase order; return {row_id: (openfga, repo, measured)}."""
    schema, rows = MODELS[model]
    pe = ParityEngine(schema)
    try:
        assert pe.graph is not None, f'model {model} lost the graph: {pe.graph_drop_reason}'
        measured = {}
        for phase in ('empty', 'write', 'after'):
            for row_id, row_phase, query, openfga, repo in rows:
                if row_phase == phase:
                    measured[row_id] = (openfga, repo, _ask(pe, query))
            for row_phase, query, want in REPO_ONLY.get(model, []):
                if row_phase == phase:
                    got = _ask(pe, query)
                    assert got == want, f'repo-only pin moved: {query} -> {got}, pinned {want}'
        return measured
    finally:
        pe.close()


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

def test_row_ids_are_unique_and_tables_are_literal():
    """Instrument control: unique ids, and every expected-divergent id names a real row
    whose two literal answers really differ (so the set below is not vacuous)."""
    for model, (_, rows) in MODELS.items():
        ids = [r[0] for r in rows]
        assert len(ids) == len(set(ids)), f'duplicate row id in model {model}'
        by_id = {r[0]: r for r in rows}
        assert EXPECTED_DIVERGENT[model] <= set(by_id), model
        literal_divergent = {i for i, (_, _, _, ofga, repo) in by_id.items() if ofga != repo}
        assert literal_divergent == EXPECTED_DIVERGENT[model], (
            f'model {model}: the literal tables and EXPECTED_DIVERGENT disagree: '
            f'{sorted(literal_divergent ^ EXPECTED_DIVERGENT[model])}')


@pytest.mark.parametrize('model', sorted(MODELS))
def test_openfga_transcript_vs_repo_today(model):
    """Every row's measured answer equals today's pinned repo answer (unanimous on every
    corner), and the measured divergence from OpenFGA is EXACTLY the literal set."""
    measured = _run_model(model)
    _, rows = MODELS[model]
    assert set(measured) == {r[0] for r in rows}
    moved = {i: (repo, got) for i, (_, repo, got) in measured.items() if got != repo}
    assert not moved, f'model {model}: repo answers moved (row: pinned, measured): {moved}'
    divergent = {i for i, (ofga, _, got) in measured.items() if got != ofga}
    assert divergent == EXPECTED_DIVERGENT[model], (
        f'model {model}: divergence from OpenFGA changed; now {sorted(divergent)}, '
        f'pinned {sorted(EXPECTED_DIVERGENT[model])}')


def test_vx_is_allowed_here_and_denied_by_openfga():
    """The security-relevant direction, named on its own so a reader cannot miss it: a
    stored ``doc:1#banned vx doc:1`` under ``vx: [user, doc#banned] but not banned`` is
    ALLOWED by this library and DENIED by OpenFGA v1.22.0 (``doc:1#banned`` is in the
    subtrahend ``banned`` on ``doc:1`` by the self rule)."""
    by_id = {r[0]: r for r in ROWS_B}
    assert by_id['B14'][2] == ('CHECK', 'doc:1#banned', 'vx', 'doc:1')
    assert (by_id['B14'][3], by_id['B14'][4]) == (False, True)
    measured = _run_model('B')
    assert measured['B14'] == (False, True, True)


def test_self_tuple_write_is_refused_on_every_backend():
    """Both sides refuse the EXACT self tuple ``doc:1#viewer viewer doc:1`` -- OpenFGA as
    "implicit" (400), this repo as a closure cycle (``AdmissionRejected``, unanimous via
    ParityEngine, I12 row multisets unchanged). Agreement in outcome only (C6)."""
    pe = ParityEngine(MODEL_A)
    try:
        assert pe.add_tuple(*_raw('doc:1#viewer', 'viewer', 'doc:1')) is False
        assert pe.add_tuple(*_raw('folder:1#viewer', 'viewer', 'folder:1')) is False
        assert pe.present == set()
    finally:
        pe.close()
