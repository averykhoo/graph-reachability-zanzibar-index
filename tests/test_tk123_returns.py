"""TK123 items 19 and 20: lookup results read as keys, and what bootstrap returns.

Properties guarded
------------------
* **Item 19 (A21, A41).** ``Store.result_keys`` / ``Store.excluded_keys`` turn a graph
  ``LookupResult`` into ``(type, name, predicate)`` keys, the same key vocabulary as
  ``SetEngine.result_keys`` / ``excluded_keys``. The gate below is an EQUIVALENCE gate on
  what a result COVERS: for every candidate on the lookup-oracle grid, "listed in the keys,
  or covered by a marker and not in the excluded keys" equals the independent oracle, on
  the ``Store`` (graph index) AND on its set engine, after every op of a seeded walk. Every
  key is oracle-true and every excluded key oracle-false.

  Why coverage and not raw key equality (first-hand probe 2026-10-15,
  ``.scratch/tk123/i19_probe.py``): forward keys were identical on all three schemas, but
  on ``wildcards.fga`` the graph's ``lookup_reverse('viewer', 'document', 'd1')`` listed
  ``('user', 'u2', '...')``, a subject a ``user:*`` marker already covers, which the set
  engine's ``expand.pos`` leaves out. Both read the same; the documented reading
  (``LookupResult`` docstring, PYPI_README) is "keys + marker coverage - excluded keys".

* **Item 20 (A23-A25).** ``build_index`` returns a ``BuildReport`` with named fields that
  still unpacks as a 3-tuple and keeps ``.constructor``; building over an existing index
  raises ``IndexExists`` (a ``ValueError`` and a ``ZanzibarError``); ``save_schema`` of the
  schema a store already has is a no-op (the mismatch half is pinned in
  ``tests/test_connectedstore_schema.py::test_schema_is_write_once``). The userset reading
  of ``lookup_reverse`` that the docs now state is pinned as behaviour.

Sabotage, observed 2026-10-15 (docs/sabotage-procedure.md). Applied as a pytest plugin that
monkeypatches the method (``-p <plugin>``, so the shared source tree is never edited):

* ``Store.excluded_keys`` returning ``set()``: ``5 failed, 5 passed`` -- the boolean and
  demorgans gates (the wildcards schema has no ``but not``), literal first red::

    AssertionError: graph lookup_reverse('viewer', 'doc', 'd1') vs oracle on ('user', 'u1',
    '...'): covered=True oracle=False

* ``Store.result_keys`` translating ``excluded_node_ids`` instead of ``node_ids``:
  ``7 failed, 3 passed`` -- all three gates, literal first red::

    AssertionError: graph lookup('...', 'user', 'u1') vs oracle on ('doc', 'd1', 'blocked'):
    covered=False oracle=True
"""

import random
import warnings

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar import ZanzibarError
from zanzibar.graphindex import LookupResult
from zanzibar.schema import parse_schema_ast
from zanzibar.store import (BuildReport, IndexExists, SchemaMismatch, Store, build_index,
                            save_schema)
from tests.oracle import Oracle, OracleTuple
from tests.test_lookup_oracle import _names_by_type, _object_candidates, _subject_candidates
from tests.test_matrix import _boolean_pool, _demorgan_pool
from tests.test_wildcard_property import OBJECT_WC, _candidate_raw_tuples


@pytest.fixture
def session():
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


# --------------------------------------------------------------------------- item 19 gate

def _walk(schema, object_wc, pool, seed, steps, stats):
    engine = create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session, warnings.catch_warnings():
        warnings.simplefilter('ignore')
        store = Store(session, 'k', schema=schema, object_wildcard_shapes=object_wc,
                      paranoia='off')
        se = store.source.engine
        ast = parse_schema_ast(schema)
        names = _names_by_type(pool)
        subjects = [s for s in _subject_candidates(ast, names) if s[2] != '*']
        objects = [o for o in _object_candidates(ast, names) if o[2] != '*']
        rng = random.Random(seed)
        present: set[tuple] = set()

        def battery():
            oracle = Oracle(schema, [OracleTuple(*r) for r in present])
            for subj in subjects:
                for side, res, keys, excl, marker in (
                        ('graph', store.lookup(*subj), store.result_keys,
                         store.excluded_keys, lambda t, r: (t, r, 'all')),
                        ('set', se.lookup(*subj), se.result_keys, se.excluded_keys,
                         lambda t, r: (t, r))):
                    _assert_covers(f'{side} lookup{subj}', res, keys(res), excl(res),
                                   [((t, n, r), (*subj, r, t, n)) for (r, t, n) in objects],
                                   lambda k: marker(k[0], k[2]), oracle, ast, stats,
                                   sweep=lambda k: (*subj, k[2], k[0], k[1]))
            for obj in objects:
                rel, o_type, o_name = obj
                for side, res, keys, excl, marker in (
                        ('graph', store.lookup_reverse(*obj), store.result_keys,
                         store.excluded_keys, lambda t, p: (t, p, 'any')),
                        ('set', se.lookup_reverse(*obj), se.result_keys, se.excluded_keys,
                         lambda t, p: (t, p))):
                    _assert_covers(f'{side} lookup_reverse{obj}', res, keys(res), excl(res),
                                   [((t, n, p), (p, t, n, rel, o_type, o_name))
                                    for (p, t, n) in subjects],
                                   lambda k: marker(k[0], k[2]), oracle, None, stats,
                                   sweep=lambda k: (k[2], k[0], k[1], rel, o_type, o_name))

        for _ in range(steps):
            cands = [r for r in pool if r not in present]
            if not present or (cands and rng.random() < 0.75):
                op, raw = 'add', rng.choice(cands)
            else:
                op, raw = 'remove', rng.choice(sorted(present))
            try:
                (store.add_tuple if op == 'add' else store.remove_tuple)(*raw)
            except ZanzibarError:
                continue
            (present.add if op == 'add' else present.discard)(raw)
            battery()
        while present:
            raw = rng.choice(sorted(present))
            store.remove_tuple(*raw)
            present.discard(raw)
            battery()


def _assert_covers(where, res, keys, excluded, grid, marker_of, oracle, ast, stats, sweep):
    for k in keys:                          # every listed key is oracle-true
        if k[1] == '*' or (ast is not None and (k[0], k[2]) not in ast):
            continue
        stats['keys'] += 1
        assert oracle.check(*sweep(k)), f'{where}: key {k} listed, oracle says False'
    for k in excluded:                      # every excluded key is oracle-false
        stats['excluded'] += 1
        assert not oracle.check(*sweep(k)), f'{where}: key {k} excluded, oracle says True'
    for key, q in grid:                     # coverage == oracle, pointwise
        covered = key in keys or (marker_of(key) in res.markers and key not in excluded)
        want = oracle.check(*q)
        assert covered == want, f'{where} vs oracle on {key}: covered={covered} oracle={want}'


_CASES = {
    'wildcards': ('wildcards.fga', OBJECT_WC, lambda s: _candidate_raw_tuples(), 0, 8),
    'boolean': ('boolean_wildcards.fga', frozenset(), lambda s: _boolean_pool(), 4, 8),
    'demorgans': ('demorgans_reverse.fga', frozenset(), _demorgan_pool, 0, 12),
}


@pytest.mark.parametrize('case', sorted(_CASES))
def test_result_keys_cover_what_the_oracle_allows(load_fga_schema, case):
    fname, object_wc, pool, seed, steps = _CASES[case]
    schema = load_fga_schema(fname)
    stats = {'keys': 0, 'excluded': 0}
    _walk(schema, object_wc, pool(schema), seed, steps, stats)
    assert stats['keys'] > 0, f'{case}: no key was ever asserted (vacuous gate)'
    if case != 'wildcards':
        # non-vacuity of the exclusion half: these walks reach a `but not` under `user:*`
        assert stats['excluded'] > 0, f'{case}: the walk never reached an exclusion'


_BOOL = """model
  schema 1.1
type user
type group
  relations
    define member: [user, group#member]
type doc
  relations
    define banned: [user]
    define viewer: [user, user:*, group#member] but not banned
"""


def test_result_keys_and_excluded_keys_read_a_but_not_wildcard(session):
    store = Store(session, 'r', schema=_BOOL)
    store.add_tuple('user:alice', 'member', 'group:eng')
    store.add_tuple('group:eng#member', 'viewer', 'doc:d1')
    assert store.result_keys(store.lookup('user:alice')) == {
        ('group', 'eng', 'member'), ('doc', 'd1', 'viewer')}
    store.add_tuple('user:*', 'viewer', 'doc:d2')
    store.add_tuple('user:mallory', 'banned', 'doc:d2')
    res = store.lookup_reverse('viewer', 'doc:d2')
    assert ('user', '...', 'any') in res.markers
    assert store.excluded_keys(res) == {('user', 'mallory', '...')}
    se = store.source.engine
    sres = se.lookup_reverse('viewer', 'doc', 'd2')
    assert se.excluded_keys(sres) == store.excluded_keys(res)


def test_result_keys_refuses_an_id_with_no_node(session):
    store = Store(session, 'r', schema=_BOOL)
    store.add_tuple('user:alice', 'viewer', 'doc:d1')
    # chunked IN: more ids than SQLite's 999 bound parameters, none of them real
    with pytest.raises(KeyError, match='run the lookup again'):
        store.result_keys(LookupResult(node_ids=set(range(10_000, 12_000))))
    with pytest.raises(KeyError, match='excluded_node_ids'):
        store.excluded_keys(LookupResult(excluded_node_ids={10_000}))


def test_a_userset_in_lookup_reverse_is_not_a_claim_about_each_member(session):
    """A24: the documented reading. ``group:eng#member`` is listed (the userset itself is
    allowed), while its banned member ``dave`` is refused by ``check``."""
    store = Store(session, 'u', schema=_BOOL)
    store.add_tuple('user:dave', 'member', 'group:eng')
    store.add_tuple('group:eng#member', 'viewer', 'doc:d1')
    store.add_tuple('user:dave', 'banned', 'doc:d1')
    res = store.lookup_reverse('viewer', 'doc:d1')
    assert ('group', 'eng', 'member') in store.result_keys(res)
    assert store.excluded_keys(res) == set()
    assert store.check('user:dave', 'viewer', 'doc:d1') is False


def test_lookup_annotations_name_the_graph_result():
    import inspect
    for name in ('lookup', 'lookup_reverse'):
        assert inspect.signature(getattr(Store, name)).return_annotation in (
            'LookupResult', LookupResult)
    for name in ('result_keys', 'excluded_keys'):
        assert inspect.signature(getattr(Store, name)).return_annotation == \
            'set[tuple[str, str, str]]'


# --------------------------------------------------------------------------- item 20

_PLAIN = """model
  schema 1.1
type user
type doc
  relations
    define viewer: [user]
"""


def test_build_report_has_named_fields_and_unpacks(session):
    save_schema(session, 's', _PLAIN)
    session.commit()
    report = build_index(session, 's')
    assert isinstance(report, BuildReport) and isinstance(report, tuple)
    assert report._fields == ('cursor', 'widx', 'ruleset')
    cursor, widx, ruleset = report
    assert (report.cursor, report.widx, report.ruleset) == (cursor, widx, ruleset)
    assert report.constructor == 'bulk'
    again = report._replace(ruleset=ruleset)
    assert isinstance(again, BuildReport) and again.constructor == 'bulk'
    assert repr(report) == "BuildReport(index_store_id='s', applied_log_id=0, " \
                           "constructor='bulk')"
    with pytest.raises(ValueError, match='unknown build_index constructor'):
        BuildReport(cursor, widx, ruleset, 'other')


def test_build_index_over_an_existing_index_raises_index_exists(session):
    save_schema(session, 's', _PLAIN)
    session.commit()
    build_index(session, 's')
    with pytest.raises(IndexExists, match='rebuild_index') as exc:
        build_index(session, 's')
    assert isinstance(exc.value, ValueError) and isinstance(exc.value, ZanzibarError)
    assert exc.value.index_store_id == 's'


def test_save_schema_of_the_same_schema_is_a_no_op(session):
    row, _ = save_schema(session, 's', _PLAIN)
    session.commit()
    # same schema, different text (whitespace and comments do not matter, as on reopen)
    again, ruleset = save_schema(session, 's', _PLAIN.replace('type doc', 'type doc  '))
    assert again is row and again.schema_text == _PLAIN and ruleset is not None
    with pytest.raises(SchemaMismatch, match='static'):
        save_schema(session, 's', _PLAIN.replace('[user]', '[user, user:*]'))
    with pytest.raises(SchemaMismatch, match='object_wildcard_shapes'):
        save_schema(session, 's', _PLAIN, frozenset({('doc', 'viewer')}))
