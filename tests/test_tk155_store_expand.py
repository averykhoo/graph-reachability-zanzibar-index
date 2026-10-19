"""TK155: ``Store.expand`` -- Zanzibar Expand on the composed store, returning keys.

Properties guarded (docs/tk155-store-expand-2026-10-19.md):

* **E1 exactness vs the independent oracle.** After every accepted write of a seeded walk
  (adds, then a drain to empty), for every candidate object and every candidate subject
  (``tests/test_lookup_oracle.py::_subject_candidates``: schema-derived shapes x {<=2 pool
  names, a ghost name, ``*``}), ``ExpandResult.covers(key)`` equals ``Oracle.check``; a
  ``*`` subject is covered iff its ``(type, predicate)`` shape is in ``markers``. Run under
  BOTH ``SetOps``.
* **E2 component sweeps.** Every ``keys`` entry is oracle-true; every ``excluded_keys``
  entry is marker-covered, oracle-false and not in ``keys``.
* **E3 cross-backend tie.** For the same candidates, ``Store.expand`` coverage equals the
  graph index's ``Store.lookup_reverse`` coverage (``result_keys``, or an ``"any"`` marker
  minus ``excluded_keys``) whenever the schema joins the graph.
* **E4 the pos-vs-star reading.** A member covered by a wildcard grant is NOT repeated in
  ``keys``; ``covers`` still answers True (the A26 addition: ``MemberSet.pos`` omits
  star-covered subjects).
* **E5 freshness.** ``expand`` reads another instance's write untokened; ``at_least`` past
  this snapshot raises ``StaleRead``; a bad token is refused like everywhere else.
* **E6 call forms.** ``expand("viewer", "doc:d1")`` == ``expand("viewer", "doc", "d1")`` ==
  the keyword form.

The checker is proven able to fail by a permanent instrument control
(``test_checker_catches_a_dropped_exclusion``).

Sabotage (2026-10-19, agent TK155/implement; ``docs/sabotage-procedure.md``). Each mutation
applied alone to ``src/zanzibar/store/_store.py::Store.expand`` by an asserted-unique
anchor, the file restored byte-for-byte (sha256-checked) after each; runner
``.scratch/tk155-157/TK155/probes/sabotage.py`` (gitignored, so this docstring is the
record). This module only, ``-p no:cacheprovider``; every one RED:

- S1 ``excluded = frozenset()`` (drop ``neg`` / ``ineg``): ``4 failed, 9 passed``;
  ``Store.expand divergence (seed=4 ops=py): expand('viewer', 'doc', 'd1') vs oracle on
  subject (...,user,u1): expand=True oracle=False`` (also red: both ``boolean[4-*]``,
  ``test_expand_reads_markers_minus_exclusions``, the control's green half).
- S2 ``keys`` from ``pos`` only (drop the ``ipos`` key channel): ``8 failed, 5 passed``;
  ``expand('blocked', 'doc', 'd1') vs oracle on subject (blocked,doc,d1): expand=False
  oracle=True``.
- S3 no ``catch_up_evaluator()``: ``1 failed, 12 passed``;
  ``assert ('user', 'alice', '...') in ExpandResult(keys=frozenset({('doc', 'd1',
  'viewer')}), ...)`` in ``test_expand_sees_another_instance_and_enforces_at_least``.
- S4 the ``StaleRead`` raise removed: ``1 failed, 12 passed``; ``DID NOT RAISE StaleRead``.
- S5 ``markers=frozenset()``: ``8 failed, 5 passed``; ``expand('public', 'doc', 'd2') vs
  oracle on subject (...,user,u1): expand=False oracle=True``.
- E3 alone (instrument control for the cross-backend tie: ``_check_expand`` patched to a
  no-op, S1 applied by monkeypatch, boolean seed 4): RED ``Store.expand divergence
  (seed=4 ops=py): expand('viewer', 'doc', 'd1') vs graph lookup_reverse on ('user', 'u1',
  '...'): expand=True``.
- S6 (review 2026-10-19, fixer TK155) markers keep only bare shapes
  (``frozenset(s for s in m.stars if s[1] == '...')``, the reviewer's in-process plugin
  ``.scratch/tk155-157/TK155/review-probes/mutplug.py`` M8): GREEN before
  ``test_expand_userset_star_marker`` existed (``13 passed``, the walks never draw a
  ``[group:*#member]`` grant); now ``1 failed, 13 passed``; ``AssertionError: assert
  frozenset() == {('group', 'member')}``.

NOT covered: the ``m.ineg`` term of ``excluded_keys`` (an implicit, never-interned
star-covered key that the self-relation correction refuses). Dropping it stays green
(review mutation M1, re-run 2026-10-19: ``14 passed``); neither the reviewer's reach probe
(0 of 2624 calls) nor a hand construction reached a non-empty ``ineg``.
"""
from __future__ import annotations

import random

import pytest
from sqlmodel import Session, SQLModel, create_engine

import zanzibar
from zanzibar.schema import parse_openfga_schema, parse_schema_ast
from zanzibar.schema.errors import (CyclicDerivedDependency, UnsupportedByGraphIndex,
                                    ZanzibarError)
from zanzibar.setengine import ALL_SETOPS
from zanzibar.store import ExpandResult, StaleRead, Store
from tests.oracle import Oracle, OracleTuple
from tests.test_lookup_oracle import (_names_by_type, _object_candidates,
                                      _subject_candidates)
from tests.test_matrix import _boolean_pool
from tests.test_wildcard_property import OBJECT_WC, _candidate_raw_tuples


@pytest.fixture
def mem_engine():
    eng = create_engine('sqlite://')
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


# --------------------------------------------------------------------------- checkers

def _check_expand(oc, subjects, obj, res: ExpandResult) -> None:
    """E1 + E2 for one object. ``oc(sp, st, sn, rel, ot, on)`` is the oracle."""
    rel, ot, on = obj
    for (t, n, p) in res.keys:
        assert oc(p, t, n, rel, ot, on), f'expand{obj}: key {t}:{n}#{p} is oracle-false'
    for (t, n, p) in res.excluded_keys:
        assert (t, p) in res.markers, f'expand{obj}: excluded {t}:{n}#{p} outside markers'
        assert (t, n, p) not in res.keys, f'expand{obj}: excluded {t}:{n}#{p} also in keys'
        assert not oc(p, t, n, rel, ot, on), (
            f'expand{obj}: excluded {t}:{n}#{p} is oracle-TRUE')
    for (sp, st, sn) in subjects:
        expected = oc(sp, st, sn, rel, ot, on)
        got = ((st, sp) in res.markers) if sn == '*' else ((st, sn, sp) in res)
        assert got == expected, (
            f'expand{obj} vs oracle on subject ({sp},{st},{sn}): expand={got} '
            f'oracle={expected}')


def _graph_covers(store: Store, res, key) -> bool:
    t, n, p = key
    if n == '*':
        return (t, p, 'any') in res.markers
    return (key in store.result_keys(res)
            or ((t, p, 'any') in res.markers and key not in store.excluded_keys(res)))


def _check_cross_backend(store, subjects, obj, res: ExpandResult) -> None:
    """E3: the graph index's lookup_reverse covers exactly what expand covers."""
    g = store.lookup_reverse(*obj)
    for (sp, st, sn) in subjects:
        key = (st, sn, sp)
        e = ((st, sp) in res.markers) if sn == '*' else (key in res)
        assert _graph_covers(store, g, key) == e, (
            f'expand{obj} vs graph lookup_reverse on {key}: expand={e}')


class _Walk:
    """One Store per SetOps over an in-memory SQLite, walked in lockstep, the oracle as
    referee after every accepted write."""

    def __init__(self, engine, schema, object_wc, pool, ops):
        self.session = Session(engine)
        self.store = Store(self.session, 'tk155', schema=schema,
                           object_wildcard_shapes=object_wc, ops=ops)
        self.schema = schema
        self.graph_joined = True
        try:
            parse_openfga_schema(schema, object_wildcard_shapes=object_wc)
        except (UnsupportedByGraphIndex, CyclicDerivedDependency):
            self.graph_joined = False
        ast = parse_schema_ast(schema)
        names = _names_by_type(pool)
        self.subjects = _subject_candidates(ast, names)
        self.objects = _object_candidates(ast, names)
        self.present: set[tuple] = set()
        self.accepted = 0
        self.excluded_seen = 0      # reach counter: states with a non-empty excluded_keys
        self.star_omitted_seen = 0  # reach counter: E4, a member a marker covers, not in keys

    def apply(self, op, raw):
        try:
            (self.store.add_tuple if op == 'add' else self.store.remove_tuple)(*raw)
        except ZanzibarError:
            self.session.rollback()
            return False
        (self.present.add if op == 'add' else self.present.discard)(raw)
        self.accepted += 1
        return True

    def assert_state(self, context):
        oracle = Oracle(self.schema, [OracleTuple(*r) for r in self.present])
        memo = {}

        def oc(*q):
            if q not in memo:
                memo[q] = oracle.check(*q)
            return memo[q]

        for obj in self.objects:
            res = self.store.expand(*obj)
            if res.excluded_keys:
                self.excluded_seen += 1
            for (sp, st, sn) in self.subjects:
                if (sn != '*' and (st, sp) in res.markers and (st, sn, sp) not in res.keys
                        and oc(sp, st, sn, *obj)):
                    self.star_omitted_seen += 1
                    break
            try:
                _check_expand(oc, self.subjects, obj, res)
                if self.graph_joined:
                    _check_cross_backend(self.store, self.subjects, obj, res)
            except AssertionError as e:
                pytest.fail(f'Store.expand divergence ({context}): {e}\npresent: '
                            f'{sorted(self.present)}')

    def close(self):
        self.session.close()


def _run_walk(engine, schema, object_wc, pool, ops, seed, steps):
    w = _Walk(engine, schema, object_wc, pool, ops)
    rng = random.Random(seed)
    for _ in range(steps):
        cands = [r for r in pool if r not in w.present]
        if not w.present or (cands and rng.random() < 0.75):
            op, raw = 'add', rng.choice(cands)
        else:
            op, raw = 'remove', rng.choice(sorted(w.present))
        if w.apply(op, raw):
            w.assert_state(f'seed={seed} ops={ops.name}')
    while w.present:
        w.apply('remove', rng.choice(sorted(w.present)))
        w.assert_state(f'seed={seed} ops={ops.name} drain')
    w.close()
    return w


# --------------------------------------------------------------------------- E1-E4 gates

@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
@pytest.mark.parametrize('seed', [0, 4])
def test_store_expand_oracle_gate_boolean(mem_engine, load_fga_schema, ops, seed):
    """``boolean_wildcards.fga`` (exclusion, intersection, TTU over a derived relation)
    with the matrix's boolean pool. Seed 4 is the TK142 exclusion seed of the lookup
    gate: its walk must reach a non-empty ``excluded_keys`` (tripwire below)."""
    w = _run_walk(mem_engine, load_fga_schema('boolean_wildcards.fga'), frozenset(),
                  _boolean_pool(), ops, seed, steps=8)
    assert w.accepted >= 8 and w.graph_joined, (w.accepted, w.graph_joined)  # E3 ran
    if seed == 4:
        assert w.excluded_seen > 0, (
            'tripwire: the walk never reached a state with excluded_keys, so a dropped '
            'exclusion would stay green here; re-pick a seed that reaches one')
        assert w.star_omitted_seen > 0, w.star_omitted_seen   # E4 reached (16, 2026-10-19)


@pytest.mark.parametrize('ops', ALL_SETOPS, ids=lambda o: o.name)
@pytest.mark.parametrize('seed', [0, 1])
def test_store_expand_oracle_gate_wildcards(mem_engine, load_fga_schema, ops, seed):
    """``wildcards.fga``: subject stars, userset stars, object wildcards, TTU from-chains,
    recursive group membership. Must reach E4 (a marker-covered member not in ``keys``)."""
    w = _run_walk(mem_engine, load_fga_schema('wildcards.fga'), OBJECT_WC,
                  _candidate_raw_tuples(), ops, seed, steps=8)
    assert w.accepted >= 8 and w.graph_joined, (w.accepted, w.graph_joined)  # E3 ran
    # measured 2026-10-19: seed 0 -> 5 states, seed 1 -> 15 (PySets)
    assert w.star_omitted_seen > 0, 'tripwire: E4 never reached; re-pick a seed'


# --------------------------------------------------------------------------- E4 example

S = ('model\n  schema 1.1\ntype user\ntype group\n  relations\n    define member: [user]\n'
     'type doc\n  relations\n    define banned: [user]\n'
     '    define viewer: [user, user:*, group#member] but not banned\n')


def test_expand_reads_markers_minus_exclusions(mem_engine):
    """The documented example: a wildcard grant, a ban, a granted group. ``user:bob`` is a
    member only through the group AND the marker, and is not listed in ``keys``."""
    with Session(mem_engine) as s:
        st = Store(s, 'x', schema=S)
        st.add_tuple('user:*', 'viewer', 'doc:d1')
        st.add_tuple('user:mallory', 'banned', 'doc:d1')
        st.add_tuple('group:eng#member', 'viewer', 'doc:d1')
        st.add_tuple('user:bob', 'member', 'group:eng')
        r = st.expand('viewer', 'doc:d1')
        assert r.markers == {('user', '...')}
        assert r.excluded_keys == {('user', 'mallory', '...')}
        assert ('group', 'eng', 'member') in r.keys
        assert ('user', 'bob', '...') not in r.keys          # covered by the marker only
        assert ('user', 'bob', '...') in r and r.covers(('user', 'bob', '...'))
        assert ('user', 'never-written', '...') in r          # a ghost: the marker covers it
        assert ('user', 'mallory', '...') not in r
        assert 'user:bob' not in r                             # only key tuples are members
        assert ('doc', 'd1', 'viewer') in r                    # OpenFGA's userset self-relation


def test_expand_userset_star_marker(mem_engine, load_fga_schema):
    """A ``[group:*#member]`` grant: the only marker is the USERSET-star shape
    ``("group", "member")`` (the seeded walks never draw one; review finding 2026-10-19).
    Every group userset is covered, a ghost and the ``*`` subject included; a user is a
    member only through a stored group membership. Oracle and graph agree on every probe.
    Also pins the documented marker-shape difference: ``lookup_reverse`` reports the same
    grant as the triple ``("group", "member", "any")``."""
    schema = load_fga_schema('wildcards.fga')
    raw = [('member', 'group', '*', 'viewer', 'folder', 'f1'),
           ('...', 'user', 'u1', 'member', 'group', 'g1'),
           ('member', 'group', 'g1', 'member', 'group', 'g2')]
    with Session(mem_engine) as s:
        st = Store(s, 'us', schema=schema, object_wildcard_shapes=OBJECT_WC)
        for (sp, stt, sn, rel, ot, on) in raw:
            st.add_tuple(f'{stt}:{sn}' + ('' if sp == '...' else f'#{sp}'), rel,
                         f'{ot}:{on}')
        obj = ('viewer', 'folder', 'f1')
        r = st.expand(*obj)
        assert r.markers == {('group', 'member')}
        assert r.excluded_keys == frozenset()
        assert ('group', 'zz', 'member') in r                 # a ghost userset: the marker
        assert ('user', 'u1', '...') in r and ('user', 'u2', '...') not in r
        assert ('group', 'member', 'any') in st.lookup_reverse(*obj).markers
        oracle = Oracle(schema, [OracleTuple(*t) for t in raw])
        subjects = [('...', 'user', 'u1'), ('...', 'user', 'u2'), ('member', 'group', 'g1'),
                    ('member', 'group', 'g2'), ('member', 'group', 'zz'),
                    ('member', 'group', '*')]
        _check_expand(oracle.check, subjects, obj, r)
        _check_cross_backend(st, subjects, obj, r)


# --------------------------------------------------------------------------- E5 freshness

def test_expand_sees_another_instance_and_enforces_at_least(tmp_path):
    eng = create_engine(f'sqlite:///{tmp_path / "tk155.db"}')
    SQLModel.metadata.create_all(eng)
    try:
        with Session(eng) as s1:
            a = Store(s1, 'm', schema=S)
            with Session(eng) as s2:
                b = Store(s2, 'm')
                assert ('user', 'alice', '...') not in b.expand('viewer', 'doc:d1')
                s2.rollback()                                   # end b's read snapshot
                tok = a.add_tuple('user:alice', 'viewer', 'doc:d1')
                assert ('user', 'alice', '...') in b.expand('viewer', 'doc:d1')
                assert ('user', 'alice', '...') in b.expand('viewer', 'doc:d1', at_least=tok)
                with pytest.raises(StaleRead, match='not visible in this session snapshot'):
                    b.expand('viewer', 'doc:d1', at_least=tok + 50)
                with pytest.raises(TypeError, match='at_least must be None or an int'):
                    b.expand('viewer', 'doc:d1', at_least=True)
                with pytest.raises(ValueError, match='at_least must be >= 0'):
                    b.expand('viewer', 'doc:d1', at_least=-1)
    finally:
        eng.dispose()


def test_expand_is_served_while_the_index_lags(mem_engine):
    """``sync=False``: the index has not caught up, yet ``expand`` (set engine) answers
    with the write, tokened or not; ``lookup_reverse`` with the same token refuses."""
    with Session(mem_engine) as s:
        st = Store(s, 'a', schema=S, sync=False)
        tok = st.add_tuple('user:alice', 'viewer', 'doc:d1')
        assert st.lag() > 0
        assert ('user', 'alice', '...') in st.expand('viewer', 'doc:d1', at_least=tok)
        assert ('user', 'alice', '...') in st.expand('viewer', 'doc:d1')
        with pytest.raises(zanzibar.LookupNotFresh):
            st.lookup_reverse('viewer', 'doc:d1', at_least=tok)


# --------------------------------------------------------------------------- E6 call forms

def test_expand_call_forms_agree(mem_engine):
    with Session(mem_engine) as s:
        st = Store(s, 'c', schema=S)
        st.add_tuple('user:alice', 'viewer', 'doc:d1')
        short = st.expand('viewer', 'doc:d1')
        assert short == st.expand('viewer', 'doc', 'd1')
        assert short == st.expand(relation='viewer', object_type='doc', object_name='d1')
        assert ('user', 'alice', '...') in short.keys
        assert zanzibar.ExpandResult is ExpandResult


# --------------------------------------------------------------------------- instrument

def test_checker_catches_a_dropped_exclusion(mem_engine):
    """Permanent instrument control: the E1/E2 checker goes red on a result whose
    ``excluded_keys`` was dropped (the over-grant), and on a leaked key."""
    with Session(mem_engine) as s:
        st = Store(s, 'i', schema=S)
        st.add_tuple('user:*', 'viewer', 'doc:d1')
        st.add_tuple('user:mallory', 'banned', 'doc:d1')
        res = st.expand('viewer', 'doc:d1')
        present = [('...', 'user', '*', 'viewer', 'doc', 'd1'),
                   ('...', 'user', 'mallory', 'banned', 'doc', 'd1')]
        oracle = Oracle(S, [OracleTuple(*r) for r in present])
        subjects = [('...', 'user', 'mallory'), ('...', 'user', 'bob'), ('...', 'user', '*')]
        obj = ('viewer', 'doc', 'd1')
        _check_expand(oracle.check, subjects, obj, res)              # the real one is green
        dropped = ExpandResult(res.keys, res.markers, frozenset())
        with pytest.raises(AssertionError, match='user,mallory.*expand=True oracle=False'):
            _check_expand(oracle.check, subjects, obj, dropped)
        leaked = ExpandResult(res.keys | {('user', 'mallory', '...')}, res.markers,
                              frozenset())
        with pytest.raises(AssertionError, match='oracle-false'):
            _check_expand(oracle.check, subjects, obj, leaked)
