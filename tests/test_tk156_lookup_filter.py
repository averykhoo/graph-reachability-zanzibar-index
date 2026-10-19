"""TK156: an optional object-type / relation filter on ``lookup`` / ``lookup_reverse``.

Properties guarded (docs/tk156-lookup-filter-2026-10-19.md):

* **F1 exactness vs the independent oracle, on BOTH backends.** At every state of the
  seeded oracle-gate walks of ``tests/test_lookup_oracle.py`` (adds, then a drain to
  empty), for every candidate subject and every filter (each declared ``(type, relation)``
  shape, each type alone, each relation alone, an undeclared name), the FILTERED forward
  result passes that module's own G1/G2 (graph) and S4 (set, both ``SetOps``) checkers over
  the candidate objects the filter keeps; likewise the filtered reverse result passes
  G3/G4 and the oracle half of S3 over the candidate subjects the filter keeps. Since both
  backends must equal the oracle, they equal each other: the equivalence goal.
* **F2 nothing outside the filter.** Every node id, marker, excluded id and implicit key
  of a filtered result has the filter's shape, and no candidate outside the filter is
  covered by it.
* **F3 the Store surface.** ``Store.lookup(..., object_type=, relation=)`` and
  ``Store.lookup_reverse(..., subject_type=, subject_predicate=)`` filter in every call
  form, keep a marker's exclusions with it, answer an undeclared name with an empty result
  (as ``check`` answers False), refuse a non-``str`` filter with ``TypeError``, and leave
  the unfiltered call unchanged.

The checkers are proven able to fail by a permanent instrument control
(``test_checker_catches_an_unfiltered_result``).

Cost control: each state asks ``_PER_STATE`` filters round-robin plus the filters of the
whole result's marker shapes, and ``_run_filter_gate`` asserts every filter was asked at
least once. Asking every filter at every state took 10m47s for the two gates (2026-10-19);
this form, 112s for the module.

Sabotage (2026-10-19, agent TK156/implement; ``docs/sabotage-procedure.md``). Each mutation
applied alone, by an asserted-unique anchor, the file restored byte-for-byte after each
(only if it still held the mutant); S5/S6 as in-process ``-p`` plugins so ``_store.py`` was
never edited. Runner ``.scratch/tk155-157/TK156/probes/sabotage.py`` (gitignored, so this
docstring is the record). This module only, ``-x -p no:cacheprovider``; every one RED:

- S1 graph ``filter_result`` keeps every marker (``markers=set(res.markers)``): ``1
  failed``; ``graph.lookup_reverse('viewer', 'document', 'd2') filter=('folder', '...'):
  marker ('document', 'viewer', 'all') is outside filter ('folder', '...')``.
- S2 graph ``filter_result`` drops exclusions (``excluded_node_ids=set()``): ``1 failed, 1
  passed`` (the wildcards gate stays green; the boolean seed-4 gate catches it):
  ``filtered lookup/oracle divergence (seed=4): graph.lookup_reverse('viewer', 'doc',
  'd1') vs oracle on subject (...,user,u1): graph=True oracle=False``.
- S3 set ``filter_result`` matches the NAME instead of the predicate (``key_of[i][1]``):
  ``1 failed``; ``set.lookup('member', 'group', 'g1') [py] vs oracle on member group:g1:
  set=False oracle=True``.
- S4 set ``filter_result`` keeps every implicit key: ``1 failed``; ``set.lookup('parent',
  'document', 'd1') [py] filter=('folder', 'parent'): implicit_keys ('document', 'd1',
  'parent') outside filter ('folder', 'parent')``.
- S5 ``Store.lookup`` ignores its filter: ``1 failed, 4 passed``; ``assert {('doc',
  'd1'...g', 'member')} == {('doc', 'd1'...4', 'viewer')}``.
- S6 ``Store.lookup_reverse`` passes its filters swapped: ``1 failed, 5 passed``;
  ``assert set() == {('user', '...', 'any')}``.
- S7 ``schema/tuplestr.py::shape_filter`` ignores the predicate (``and True)``): ``1
  failed``; ``graph.lookup('viewer', 'folder', 'f1') filter=('folder', 'parent'):
  implicit_keys ('folder', 'f1', 'viewer') outside filter ('folder', 'parent')``.

Review fixes (2026-10-19, agent TK156/fix): in-process ``-p`` plugin mutants, no tracked
file edited (``.scratch/tk155-157/TK156/fix-probes/fix_mut_plugin.py``), run with ``-k
"implicit_exclusions or stale or undeclared_is_empty"``; unmutated ``3 passed``, every
mutant RED (``1 failed, 2 passed``):

- M3 graph ``filter_result`` drops ``implicit_excluded_keys``: ``('WildcardIndex',
  ('group', 'member'))`` / ``assert set() == {('group', 'g8', 'member')}``.
- M4 set ``filter_result`` keeps every implicit exclusion unfiltered: ``('SetEngine',
  ('group', 'member'))``.
- M5 set ``filter_result`` without the stamp / dead-id check: ``DID NOT RAISE
  StaleLookupIds``.
- M11 graph ``filter_result`` silently skipping dead node ids: ``DID NOT RAISE
  StaleLookupIds``.
- M12 ``Store`` skipping its keyword-named validation (the backend message leaks):
  ``- filter_result(): the predicate filter must be a str or None, not int``.
"""
from __future__ import annotations

import dataclasses
import random

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar.graphindex import LookupResult
from zanzibar.setengine import SetLookupResult, StaleLookupIds
from zanzibar.store import Store
from tests.oracle import Oracle, OracleTuple
from tests.test_lookup_oracle import (_Gate, _check_graph_forward, _check_graph_reverse,
                                      _check_set_forward, _gnode_id)
from tests.test_matrix import _boolean_pool
from tests.test_wildcard_property import OBJECT_WC, _candidate_raw_tuples


# --------------------------------------------------------------------------- filters

_UNDECLARED = 'tk156_undeclared'


def _filters(shapes):
    """Every filter worth asking over ``(type, predicate)`` shapes: each shape, each type
    alone, each predicate alone, and an undeclared name in each slot."""
    out = set()
    for (t, r) in shapes:
        out |= {(t, r), (t, None), (None, r)}
    out |= {(_UNDECLARED, None), (None, _UNDECLARED)}
    return sorted(out, key=repr)


#: filters taken round-robin per state, on top of the always-asked marker-shape filters
#: (cost: the whole battery runs once per filter; the unfiltered battery is
#: tests/test_lookup_oracle.py's job)
_PER_STATE = 2


def _pick(filters, k, marker_shapes):
    """The filters one state asks: ``_PER_STATE`` round-robin from ``filters`` (so a walk
    of N states visits ``N * _PER_STATE`` of them), plus, for every marker shape of the
    whole result, the shape filter and the type filter -- the ones that must keep a
    marker WITH its exclusions."""
    n = len(filters)
    out = {filters[(k * _PER_STATE + j) % n] for j in range(min(_PER_STATE, n))}
    for (t, p) in marker_shapes:
        out |= {(t, p), (t, None)}
    return sorted(out, key=repr)


def _match(flt, t, p):
    ft, fp = flt
    return (ft is None or t == ft) and (fp is None or p == fp)


# --------------------------------------------------------------------------- checkers

def _graph_within(widx, flt, res, where):
    """F2 for a graph result: every entry has the filter's shape."""
    for field in ('node_ids', 'excluded_node_ids'):
        for nid in getattr(res, field):
            n = widx._node_by_id(nid)
            assert n is not None and _match(flt, n.type, n.predicate), (
                f'{where}: {field} entry {nid} '
                f'({None if n is None else (n.type, n.name, n.predicate)}) is outside '
                f'filter {flt}')
    for (t, p, _v) in res.markers:
        assert _match(flt, t, p), f'{where}: marker {(t, p, _v)} is outside filter {flt}'
    for field in ('implicit_keys', 'implicit_excluded_keys'):
        for (t, n, p) in getattr(res, field):
            assert _match(flt, t, p), f'{where}: {field} {(t, n, p)} outside filter {flt}'


def _set_within(se, flt, res, where):
    """F2 for a set-engine result."""
    for field in ('node_ids', 'excluded_node_ids'):
        for nid in getattr(res, field):
            t, _n, p = se.interner.key(nid)
            assert _match(flt, t, p), (
                f'{where}: {field} entry {se.interner.key(nid)} outside filter {flt}')
    for (t, p) in res.markers:
        assert _match(flt, t, p), f'{where}: marker {(t, p)} outside filter {flt}'
    for field in ('implicit_keys', 'implicit_excluded_keys'):
        for (t, n, p) in getattr(res, field):
            assert _match(flt, t, p), f'{where}: {field} {(t, n, p)} outside filter {flt}'


def _graph_fwd_covers(widx, res, obj):
    rel, ot, on = obj
    marker = (ot, rel, 'all') in res.markers
    if on == '*':
        return marker
    nid = _gnode_id(widx, rel, ot, on)
    return (nid is not None and nid in res.node_ids) or (ot, on, rel) in res.implicit_keys \
        or marker


def _set_fwd_covers(se, res, obj):
    rel, ot, on = obj
    if on == '*':
        return (ot, rel) in res.markers
    nid = se.interner.get(ot, on, rel)
    return ((nid is not None and nid in res.node_ids) or (ot, on, rel) in res.implicit_keys
            or ((ot, rel) in res.markers and nid not in res.excluded_node_ids
                and (ot, on, rel) not in res.implicit_excluded_keys))


def _graph_rev_covers(widx, res, subj):
    sp, st, sn = subj
    any_ = (st, sp, 'any') in res.markers
    if sn == '*':
        return any_
    nid = _gnode_id(widx, sp, st, sn)
    return ((nid is not None and nid in res.node_ids) or (st, sn, sp) in res.implicit_keys
            or (any_ and not (nid is not None and nid in res.excluded_node_ids)
                and (st, sn, sp) not in res.implicit_excluded_keys))


def _set_rev_covers(se, res, subj):
    sp, st, sn = subj
    if sn == '*':
        return (st, sp) in res.markers
    uid = se.interner.get(st, sn, sp)
    return ((uid is not None and uid in res.node_ids) or (st, sn, sp) in res.implicit_keys
            or ((st, sp) in res.markers
                and not (uid is not None and uid in res.excluded_node_ids)
                and (st, sn, sp) not in res.implicit_excluded_keys))


def _check_set_reverse_filtered(se, oc, subjects, obj, res, where):
    """The oracle half of S3 (soundness sweeps + two-sided exactness) for a filtered
    ``SetEngine.lookup_reverse``; S3's structural ``== expand`` half does not apply to a
    filtered result."""
    rel, ot, on = obj
    for nid in res.node_ids:
        t, n, p = se.interner.key(nid)
        assert oc(p, t, n, rel, ot, on), f'{where} leaked {t}:{n}#{p}'
    for nid in res.excluded_node_ids:
        t, n, p = se.interner.key(nid)
        assert n != '*' and (t, p) in res.markers and not oc(p, t, n, rel, ot, on), (
            f'{where} excluded {t}:{n}#{p}: star, marker-uncovered or oracle-true')
    for (t, n, p) in res.implicit_keys:
        assert oc(p, t, n, rel, ot, on), f'{where} leaked implicit {t}:{n}#{p}'
    for (t, n, p) in res.implicit_excluded_keys:
        assert (t, p) in res.markers and not oc(p, t, n, rel, ot, on), (
            f'{where} implicit exclusion {t}:{n}#{p} marker-uncovered or oracle-true')
    for subj in subjects:
        got = _set_rev_covers(se, res, subj)
        expected = oc(*subj, rel, ot, on)
        assert got == expected, f'{where} vs oracle on subject {subj}: set={got} oracle={expected}'


class _FilterGate(_Gate):
    """The lookup-oracle gate, asserting FILTERED results instead of whole ones (the
    unfiltered battery already runs in ``tests/test_lookup_oracle.py``)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fwd_filters = _filters(self.ast)
        self.rev_filters = _filters({(st, sp) for (sp, st, _sn) in self.subjects})
        self.k = 0                  # state counter, drives the round-robin
        self.asked_fwd: set = set()
        self.asked_rev: set = set()
        # reach counters (non-vacuity): filtered results that kept a marker / an exclusion
        self.graph_fwd_marker = self.set_fwd_marker = 0
        self.graph_rev_excl = self.set_rev_excl = 0
        self.nonempty = 0

    def assert_surfaces(self, context=''):
        oracle = Oracle(self.schema, [OracleTuple(*r) for r in self.present])
        memo = {}

        def oc(*q):
            if q not in memo:
                memo[q] = oracle.check(*q)
            return memo[q]

        self.k += 1
        try:
            if self.graph:
                w = self.graph.widx
                for subject in self.subjects:
                    whole = w.lookup(*subject)
                    for flt in _pick(self.fwd_filters, self.k,
                                     {(t, p) for (t, p, _v) in whole.markers}):
                        res = w.filter_result(whole, *flt)
                        self.asked_fwd.add(flt)
                        where = f'graph.lookup{subject} filter={flt}'
                        self.nonempty += bool(res.node_ids or res.implicit_keys)
                        self.graph_fwd_marker += bool(res.markers)
                        _graph_within(w, flt, res, where)
                        keep = [o for o in self.objects if _match(flt, o[1], o[0])]
                        _check_graph_forward(w, self.ast, oc, subject, keep, res)
                        for o in self.objects:
                            if o not in keep:
                                assert not _graph_fwd_covers(w, res, o), (
                                    f'{where}: covers {o}, outside the filter')
                for obj in self.objects:
                    whole = w.lookup_reverse(*obj)
                    for flt in _pick(self.rev_filters, self.k,
                                     {(t, p) for (t, p, _v) in whole.markers}):
                        res = w.filter_result(whole, *flt)
                        self.asked_rev.add(flt)
                        where = f'graph.lookup_reverse{obj} filter={flt}'
                        self.graph_rev_excl += bool(res.excluded_node_ids)
                        _graph_within(w, flt, res, where)
                        keep = [s for s in self.subjects if _match(flt, s[1], s[0])]
                        _check_graph_reverse(w, oc, keep, obj, res)
                        for s in self.subjects:
                            if s not in keep:
                                assert not _graph_rev_covers(w, res, s), (
                                    f'{where}: covers {s}, outside the filter')
            for side in self.sets:
                se = side.se
                for subject in self.subjects:
                    whole = se.lookup(*subject)
                    for flt in _pick(self.fwd_filters, self.k, whole.markers):
                        res = se.filter_result(whole, *flt)
                        where = f'set.lookup{subject} [{se.ops.name}] filter={flt}'
                        self.set_fwd_marker += bool(res.markers)
                        _set_within(se, flt, res, where)
                        keep = [o for o in self.objects if _match(flt, o[1], o[0])]
                        _check_set_forward(se, oc, subject, keep, res)
                        for o in self.objects:
                            if o not in keep:
                                assert not _set_fwd_covers(se, res, o), (
                                    f'{where}: covers {o}, outside the filter')
                for obj in self.objects:
                    whole = se.lookup_reverse(*obj)
                    for flt in _pick(self.rev_filters, self.k, whole.markers):
                        res = se.filter_result(whole, *flt)
                        where = f'set.lookup_reverse{obj} [{se.ops.name}] filter={flt}'
                        self.set_rev_excl += bool(res.excluded_node_ids)
                        _set_within(se, flt, res, where)
                        keep = [s for s in self.subjects if _match(flt, s[1], s[0])]
                        _check_set_reverse_filtered(se, oc, keep, obj, res, where)
                        for s in self.subjects:
                            if s not in keep:
                                assert not _set_rev_covers(se, res, s), (
                                    f'{where}: covers {s}, outside the filter')
        except AssertionError as e:
            pytest.fail(f'filtered lookup/oracle divergence ({context}): {e}\nhistory:\n'
                        + '\n'.join(f'  {op} {raw}' for op, raw in self.history))


def _run_filter_gate(schema, object_wc, pool, seed, walk_steps):
    gate = _FilterGate(schema, object_wc, pool)
    rng = random.Random(seed)
    present = gate.present
    for _ in range(walk_steps):
        cands = [r for r in pool if r not in present]
        if not present or (cands and rng.random() < 0.75):
            op, raw = 'add', rng.choice(cands)
        else:
            op, raw = 'remove', rng.choice(sorted(present))
        if gate.apply(op, raw):
            gate.assert_surfaces(context=f'seed={seed}')
    while present:
        gate.apply('remove', rng.choice(sorted(present)))
        gate.assert_surfaces(context=f'seed={seed}')
    gate.close()
    # every filter of both lists was asked at least once (the round-robin's reach)
    assert gate.asked_fwd >= set(gate.fwd_filters) and gate.asked_rev >= set(gate.rev_filters), (
        f'round-robin reach: forward {len(gate.asked_fwd)}/{len(gate.fwd_filters)}, '
        f'reverse {len(gate.asked_rev)}/{len(gate.rev_filters)}; raise _PER_STATE or the walk')
    return gate


# --------------------------------------------------------------------------- F1 / F2

def test_filtered_lookups_match_oracle_wildcards(load_fga_schema):
    """F1/F2 on the pure-union wildcard schema (subject stars, userset stars, object
    wildcards, TTU from-chains): object-side ``"all"`` markers must survive a filter of
    their shape and vanish under any other."""
    gate = _run_filter_gate(load_fga_schema('wildcards.fga'), OBJECT_WC,
                            _candidate_raw_tuples(), seed=0, walk_steps=8)
    assert gate.nonempty > 0 and gate.graph_fwd_marker > 0 and gate.set_fwd_marker > 0, (
        'reach: the walk never produced a non-empty filtered result or a filtered marker')


def test_filtered_lookups_match_oracle_boolean(load_fga_schema):
    """F1/F2 on the boolean fixture at the TK142 exclusion seed (4): a filtered
    ``lookup_reverse`` must keep a marker's exclusions with it on both backends."""
    gate = _run_filter_gate(load_fga_schema('boolean_wildcards.fga'), frozenset(),
                            _boolean_pool(), seed=4, walk_steps=8)
    assert gate.graph_rev_excl > 0 and gate.set_rev_excl > 0, (
        f'reach: no filtered reverse result kept an exclusion (graph={gate.graph_rev_excl}, '
        f'set={gate.set_rev_excl}); re-pick the seed as test_lookup_oracle_gate_boolean says')


def test_checker_catches_an_unfiltered_result(load_fga_schema):
    """Instrument control: the F2 checkers go red when ``filter_result`` hands back the
    WHOLE result (the "filter ignored" mutation), on both backends."""
    gate = _FilterGate(load_fga_schema('boolean_wildcards.fga'), frozenset(),
                       _boolean_pool())
    try:
        for raw in [('...', 'user', '*', 'public', 'doc', 'd1'),
                    ('...', 'user', 'u2', 'blocked', 'doc', 'd1'),
                    ('...', 'user', 'u1', 'editor', 'doc', 'd1')]:
            assert gate.apply('add', raw)
        flt = ('doc', 'editor')
        g = gate.graph.widx
        whole = g.lookup('...', 'user', 'u1')
        assert g.filter_result(whole, *flt) != whole
        with pytest.raises(AssertionError, match='outside filter'):
            _graph_within(g, flt, whole, 'control')
        se = gate.sets[0].se
        whole_s = se.lookup('...', 'user', 'u1')
        with pytest.raises(AssertionError, match='outside filter'):
            _set_within(se, flt, whole_s, 'control')
        # reverse: a user-only filter must drop nothing here and keep the exclusion
        rev = g.lookup_reverse('viewer', 'doc', 'd1')
        kept = g.filter_result(rev, 'user', '...')
        assert kept.excluded_node_ids == rev.excluded_node_ids != set()
        assert g.filter_result(rev, 'group', None).excluded_node_ids == set()
    finally:
        gate.close()


def test_no_filter_returns_the_result_itself(load_fga_schema):
    gate = _FilterGate(load_fga_schema('boolean_wildcards.fga'), frozenset(),
                       _boolean_pool())
    try:
        res = gate.graph.widx.lookup('...', 'user', 'u1')
        assert gate.graph.widx.filter_result(res) is res
        sres = gate.sets[0].se.lookup('...', 'user', 'u1')
        assert gate.sets[0].se.filter_result(sres) is sres
        assert isinstance(gate.graph.widx.filter_result(res, 'doc'), LookupResult)
        out = gate.sets[0].se.filter_result(sres, 'doc')
        assert isinstance(out, SetLookupResult) and out.id_stamp == sres.id_stamp
        for bad in (1, ('doc',), b'doc'):
            with pytest.raises(TypeError, match='filter must be a str or None'):
                gate.graph.widx.filter_result(res, bad)
            with pytest.raises(TypeError, match='filter must be a str or None'):
                gate.sets[0].se.filter_result(sres, None, bad)
    finally:
        gate.close()


def test_filter_keeps_implicit_exclusions_by_shape(load_fga_schema):
    """F2 for the key channel (``implicit_keys`` / ``implicit_excluded_keys``), both
    backends: an implicit exclusion survives a filter of its marker's shape and is dropped
    by any other. No seeded walk of the two oracle gates produces a non-empty
    ``implicit_excluded_keys`` (probed 2026-10-19 over seeds 0-5 of both fixtures, and three
    crafted TK144 schemas whose refused usersets all had a node / an interned id), so the
    channel is driven here through a real result with the key channel set by hand:
    ``filter_result`` reads only the shapes of those keys."""
    gate = _FilterGate(load_fga_schema('boolean_wildcards.fga'), frozenset(),
                       _boolean_pool())
    try:
        assert gate.apply('add', ('...', 'user', '*', 'public', 'doc', 'd1'))
        ikeys = {('group', 'g7', 'member'), ('user', 'u7', '...')}
        iexcl = {('group', 'g8', 'member'), ('user', 'u8', '...')}
        g = gate.graph.widx
        gres = dataclasses.replace(
            g.lookup_reverse('viewer', 'doc', 'd1'),
            markers={('user', '...', 'any'), ('group', 'member', 'any')},
            implicit_keys=set(ikeys), implicit_excluded_keys=set(iexcl))
        se = gate.sets[0].se
        sres = dataclasses.replace(
            se.lookup_reverse('viewer', 'doc', 'd1'),
            markers={('user', '...'), ('group', 'member')},
            implicit_keys=set(ikeys), implicit_excluded_keys=set(iexcl))
        for backend, res in ((g, gres), (se, sres)):
            for flt, want in ((('group', 'member'), 'group'), (('group', None), 'group'),
                              ((None, 'member'), 'group'), (('user', '...'), 'user'),
                              (('user', None), 'user'), ((None, '...'), 'user')):
                out = backend.filter_result(res, *flt)
                assert out.implicit_excluded_keys == {k for k in iexcl if k[0] == want}, (
                    type(backend).__name__, flt)
                assert out.implicit_keys == {k for k in ikeys if k[0] == want}, (
                    type(backend).__name__, flt)
            out = backend.filter_result(res, 'doc')
            assert out.implicit_keys == out.implicit_excluded_keys == set()
    finally:
        gate.close()


# --------------------------------------------------------------------------- F3 Store

_SCHEMA = """model
  schema 1.1
type user
type group
  relations
    define member: [user]
type folder
  relations
    define viewer: [user, group#member]
type doc
  relations
    define banned: [user]
    define editor: [user]
    define viewer: [user, user:*, group#member] but not banned
"""


@pytest.fixture
def store():
    eng = create_engine('sqlite://')
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        st = Store(s, 'tk156', schema=_SCHEMA)
        for t in [('user:alice', 'viewer', 'doc:d1'), ('user:alice', 'editor', 'doc:d2'),
                  ('user:alice', 'viewer', 'folder:f1'), ('user:alice', 'member', 'group:g'),
                  ('group:g#member', 'viewer', 'doc:d3'), ('user:*', 'viewer', 'doc:d4'),
                  ('user:mallory', 'banned', 'doc:d4')]:
            st.add_tuple(*t)
        yield st
    eng.dispose()


def test_store_lookup_filters_objects(store):
    keys = store.result_keys(store.lookup('user:alice', object_type='doc',
                                          relation='viewer'))
    assert keys == {('doc', 'd1', 'viewer'), ('doc', 'd3', 'viewer'),
                    ('doc', 'd4', 'viewer')}
    whole = store.result_keys(store.lookup('user:alice'))
    assert ('folder', 'f1', 'viewer') in whole and ('doc', 'd2', 'editor') in whole
    by_type = store.result_keys(store.lookup('user:alice', object_type='doc'))
    assert by_type == {k for k in whole if k[0] == 'doc'}
    by_rel = store.result_keys(store.lookup('user:alice', relation='viewer'))
    assert by_rel == {k for k in whole if k[2] == 'viewer'}
    # every call form filters alike
    for res in (store.lookup('...', 'user', 'alice', object_type='doc', relation='viewer'),
                store.lookup(user='user:alice', object_type='doc', relation='viewer'),
                store.lookup(subject_predicate='...', subject_type='user',
                             subject_name='alice', object_type='doc', relation='viewer')):
        assert store.result_keys(res) == keys
    # the same answer as the set engine's own filter (the equivalence goal)
    se = store.source.engine
    assert se.result_keys(se.filter_result(se.lookup('...', 'user', 'alice'), 'doc',
                                           'viewer')) == keys


def test_store_lookup_reverse_filters_subjects_and_keeps_exclusions(store):
    res = store.lookup_reverse('viewer', 'doc:d4', subject_type='user',
                               subject_predicate='...')
    assert res.markers == {('user', '...', 'any')}
    assert store.excluded_keys(res) == {('user', 'mallory', '...')}
    assert store.lookup_reverse('viewer', 'doc', 'd4', subject_type='group') == LookupResult()
    d3 = store.lookup_reverse('viewer', 'doc:d3')
    assert ('group', 'g', 'member') in store.result_keys(d3)
    users = store.result_keys(store.lookup_reverse('viewer', 'doc:d3', subject_type='user'))
    assert users == {k for k in store.result_keys(d3) if k[0] == 'user'}
    assert ('user', 'alice', '...') in users
    usersets = store.result_keys(store.lookup_reverse(
        relation='viewer', object='doc:d3', subject_predicate='member'))
    assert usersets == {('group', 'g', 'member')}


def test_store_filter_undeclared_is_empty_and_bad_type_refused(store):
    assert store.check('user:alice', 'nope', 'doc:d1') is False   # the read precedent
    assert store.lookup('user:alice', object_type='nodoc') == LookupResult()
    assert store.lookup('user:alice', relation='nope') == LookupResult()
    assert store.lookup_reverse('viewer', 'doc:d1', subject_type='nouser') == LookupResult()
    with pytest.raises(TypeError, match=r'^lookup\(\): relation must be a str or None, not int$'):
        store.lookup('user:alice', relation=3)
    with pytest.raises(TypeError, match=r'^lookup\(\): object_type must be a str'):
        store.lookup('user:alice', object_type=b'doc')
    with pytest.raises(TypeError, match=r'^lookup_reverse\(\): subject_type must be a str or '
                                        r'None, not list$'):
        store.lookup_reverse('viewer', 'doc:d1', subject_type=['user'])
    # the Python Ellipsis gets the same pointer as the query-side refusal
    with pytest.raises(TypeError, match=r"^lookup_reverse\(\): subject_predicate must be a "
                                        r"str or None, not ellipsis; write the string '\.\.\.' "
                                        r"for a bare subject$"):
        store.lookup_reverse('viewer', 'doc:d1', subject_predicate=...)


def test_store_unfiltered_unchanged(store):
    assert store.lookup('user:alice') == store.widx.lookup('...', 'user', 'alice')
    assert store.lookup_reverse('viewer', 'doc:d4') == \
        store.widx.lookup_reverse('viewer', 'doc', 'd4')


def test_filter_result_refuses_a_stale_result(store):
    """Both backends: a result read before a write that freed one of its ids is refused
    (``StaleLookupIds``), never classified by whatever entity now holds the id."""
    store.add_tuple('user:bob', 'viewer', 'doc:d1')
    se = store.source.engine
    sres = se.lookup_reverse('viewer', 'doc', 'd1')
    gres = store.widx.lookup_reverse('viewer', 'doc', 'd1')
    store.remove_tuple('user:bob', 'viewer', 'doc:d1')
    with pytest.raises(StaleLookupIds, match='run the lookup again'):
        se.filter_result(sres, 'user')
    with pytest.raises(StaleLookupIds, match='run the lookup again'):
        store.widx.filter_result(gres, 'user')
    # a fresh read filters normally
    fresh = store.lookup_reverse('viewer', 'doc:d1', subject_type='user')
    assert store.result_keys(fresh) == {('user', 'alice', '...')}
