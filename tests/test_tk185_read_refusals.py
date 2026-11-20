"""TK185 step 4 (C5 + C7): a READ naming an undeclared type, relation or subject relation
is refused with ``UndeclaredTypeOrRelation``, identically on every backend and path.

The owner decided on 2026-11-01 that such a read is an ERROR (it used to answer ``False``
or empty); the design is decision DEC-16. One validator
(``src/zanzibar/schema/readcheck.py``) runs on the set engine's ``DeclaredRelations``:

* at the top of ``Store.check`` / ``lookup`` / ``lookup_reverse`` / ``expand``, BEFORE
  token validation, freshness and dispatch, so the graph path, the set-engine fallback
  (stalled or tokened-lagging index) and ``IndexStalled`` / ``LookupNotFresh`` all come
  after the refusal;
* at the top level of ``SetEngine.check`` / ``lookup`` / ``lookup_reverse`` / ``expand`` /
  ``filter_result`` (and through ``SetEngine.check``, ``TupleSource.check``).

What these tests pin, for every surface: the same class, the same message, the same
attributes; the refusal happens before dispatch (a spy on the set-engine rung must never
fire); and the legal reads still answer -- an unknown NAME (``doc:999``), ``user:*``,
``folder:*``, ``'...'`` and ``None`` as the bare predicate, a boolean-derived relation.
``WildcardIndex`` stays lenient (DEC-16 item 5), pinned at the end.

Sabotage (2026-11-20, agent D; each restored with the Edit tool and re-run green):

  S1 ``readcheck.py::refuse_undeclared_subject`` returns at once (no subject check):
     rc=1 ``14 failed, 40 passed`` -- exactly the subject / result-key pins of check and
     lookup (``E   Failed: DID NOT RAISE UndeclaredTypeOrRelation``); object and filter
     pins stayed green.
  S2 Store's validator calls neutralised (``refuse_undeclared_* = lambda *a, **k: None``
     in ``store/_store.py``; SetEngine's calls kept): rc=1 ``38 failed, 16 passed``
     (``DID NOT RAISE`` on the graph path; ``AssertionError: dispatched to the set-engine
     rung before the refusal`` on expand). With the two single-surface pins below and the
     ``TupleSource.check`` spy: ``-k "fallback_paths or stalled_index_refuses"`` rc=1
     ``7 failed`` -- 6x ``dispatched to the set-engine rung before the refusal`` and
     ``IndexStalled: lookup() cannot be served: the index for store 'stalled' is STALLED``.
     (Before the ``TupleSource.check`` spy the tokened-lagging leg stayed green: the
     evaluator is already at the token, so the fallback skips ``catch_up_evaluator`` and
     SetEngine's own refusal fired -- same answer, order unproven; hence the spy.)
  S3a ``SetEngine.filter_result`` skips its validator: rc=1 ``9 failed, 52 passed`` --
     every lookup / lookup_reverse filter pin (``DID NOT RAISE``).
  S3b ``SetEngine.check`` loses both validator calls: rc=1 ``17 failed, 44 passed`` --
     every check refusal on the SetEngine / TupleSource surfaces and both fallback paths.
  S4 the C5 hint dropped (``if False and ...``): rc=1 ``2 failed, 59 passed`` -- the two
     C5 pins (``-  the schema. A result key is (type, name, predicate); lookup takes
     ...``); ``scripts/installed_smoke.py --allow-checkout`` rc=1 ``FAIL  TK185: the
     result-key refusal names the corrected call``, ``106 checks passed, 1 failed``.
  Restored: ``61 passed``; claim_rot ``549/549 bodies match``.
"""
from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

import zanzibar
import zanzibar.store._store as store_mod
from zanzibar.setengine import SetEngine
from zanzibar.store import IndexStalled, Store

U = zanzibar.UndeclaredTypeOrRelation

SCHEMA = '''model
  schema 1.1
type user
type group
  relations
    define member: [user, user:*, group#member]
type folder
  relations
    define viewer: [user, group#member]
type doc
  relations
    define parent: [folder]
    define banned: [user]
    define viewer: [user, user:*, group#member] or viewer from parent
    define readable: viewer but not banned
'''

TUPLES = [
    ('...', 'user', 'alice', 'viewer', 'doc', '1'),
    ('...', 'user', 'alice', 'banned', 'doc', '1'),
    ('...', 'user', '*', 'viewer', 'doc', 'pub'),
    ('...', 'user', 'bob', 'member', 'group', 'eng'),
    ('member', 'group', 'eng', 'viewer', 'doc', '2'),
    ('...', 'user', 'carol', 'viewer', 'folder', 'f'),
    ('...', 'folder', 'f', 'parent', 'doc', '3'),
]

CHECK_FIX = "check('...', 'user', 'alice', 'viewer', 'doc', '1')"
LOOKUP_FIX = "lookup('...', 'user', 'alice')"
RESULT_KEY = ('user', 'alice', '...')        # a result key: (type, name, predicate)


# --------------------------------------------------------------------------- the world

class World:
    """Every read surface over the same schema and tuples."""

    def __init__(self, tmp_path):
        self.engine = create_engine(f'sqlite:///{tmp_path / "w.db"}')
        SQLModel.metadata.create_all(self.engine)
        self.sessions = []
        self.sync = self._store('sync', sync=True)
        self.asyn = self._store('asyn', sync=False)
        assert self.asyn.catch_up() == len(TUPLES)
        self.stalled = self._store('stalled', sync=False)
        self.stalled.catch_up()
        self._stall(self.stalled)
        self.lagging = self._store('lagging', sync=False)
        self.lagging.catch_up()
        # one more write, never applied to the index: a tokened read must fall back
        self.token = self.lagging.add_tuple('...', 'user', 'dave', 'viewer', 'doc', '4')
        assert self.lagging.lag() == 1
        s = self._session()
        self.se = SetEngine(s, 'standalone', SCHEMA)
        for t in TUPLES:
            self.se.add_tuple(*t)
        s.commit()

    def _session(self):
        s = Session(self.engine)
        self.sessions.append(s)
        return s

    def _store(self, store_id, *, sync):
        st = Store(self._session(), store_id, schema=SCHEMA, sync=sync)
        for t in TUPLES:
            st.add_tuple(*t)
        return st

    @staticmethod
    def _stall(st):
        """A lag-0 stall (``tests/test_tk165_idle_stall_clears.py``): one failed idle
        ``catch_up`` records the stall marker."""
        real = store_mod.advance_index

        def boom(*a, **kw):
            raise ConnectionError('simulated failure on an idle poll')
        store_mod.advance_index = boom
        try:
            with pytest.raises(ConnectionError):
                st.catch_up()
        finally:
            store_mod.advance_index = real
        assert st.index_stalled and st.lag() == 0
        with pytest.raises(IndexStalled):
            st.lookup('user:alice')

    def close(self):
        for s in self.sessions:
            s.rollback()
            s.close()
        self.engine.dispose()


@pytest.fixture(scope='module')
def world(tmp_path_factory):
    w = World(tmp_path_factory.mktemp('tk185-read-refusals'))
    yield w
    w.close()


def _no_dispatch(*a, **kw):
    raise AssertionError('dispatched to the set-engine rung before the refusal')


@pytest.fixture
def spied(world, monkeypatch):
    """Every Store's set-engine rung (``TupleSource.catch_up_evaluator``, the first thing
    the stalled fallback and ``expand`` do, and ``TupleSource.check`` on the stalled and
    tokened-lagging stores) fails the test if reached."""
    for st in (world.sync, world.asyn, world.stalled, world.lagging):
        monkeypatch.setattr(st.source, 'catch_up_evaluator', _no_dispatch)
    # the fallback's set-engine read itself: on the tokened-lagging path the evaluator is
    # already at the token (writes catch it up), so catch_up_evaluator is skipped there
    for st in (world.stalled, world.lagging):
        monkeypatch.setattr(st.source, 'check', _no_dispatch)
    return world


def _refusal(call):
    with pytest.raises(U) as ei:
        call()
    e = ei.value
    assert isinstance(e, ValueError) and isinstance(e, zanzibar.ZanzibarError)
    return (type(e), str(e), e.method, e.role, e.type_name, e.relation)


# --------------------------------------------------------------------------- check

CHECK_REFUSALS = {
    'object-type': ('...', 'user', 'alice', 'viewer', 'dco', '1'),
    'object-relation': ('...', 'user', 'alice', 'vewer', 'doc', '1'),
    'relationless-object': ('...', 'user', 'alice', 'viewer', 'user', 'bob'),
    'object-leaf': ('...', 'user', 'alice', 'readable.0', 'doc', '1'),
    'subject-type': ('...', 'usr', 'alice', 'viewer', 'doc', '1'),
    'subject-predicate': ('nosuch', 'group', 'eng', 'viewer', 'doc', '1'),
    'subject-leaf': ('readable.0', 'doc', '1', 'viewer', 'doc', '2'),
    'subject-relationless': ('member', 'user', 'alice', 'viewer', 'doc', '1'),
    'subject-wildcard-predicate': ('nosuch', 'group', '*', 'viewer', 'doc', '1'),
    'result-key': (*RESULT_KEY, 'viewer', 'doc', '1'),
}


def _check_surfaces(w, args):
    return {
        'Store sync (graph)': lambda: w.sync.check(*args),
        'Store async (graph)': lambda: w.asyn.check(*args),
        'Store stalled (set-engine fallback)': lambda: w.stalled.check(*args),
        'Store tokened lagging (set-engine fallback)':
            lambda: w.lagging.check(*args, at_least=w.token),
        'TupleSource.check': lambda: w.sync.source.check(*args),
        'SetEngine.check': lambda: w.se.check(*args),
    }


@pytest.mark.parametrize('case', sorted(CHECK_REFUSALS))
def test_check_refuses_identically_on_every_surface(spied, case):
    args = CHECK_REFUSALS[case]
    got = {name: _refusal(call) for name, call in _check_surfaces(spied, args).items()}
    first = got['SetEngine.check']
    assert all(g == first for g in got.values()), got
    assert first[2] == 'check'
    assert first[3] == ('subject' if case.startswith(('subject', 'result')) else 'object')


def test_check_messages_name_the_mistake(world):
    msg = {c: _refusal(lambda a=a: world.sync.check(*a))[1] for c, a in CHECK_REFUSALS.items()}
    assert msg['object-relation'] == (
        "check() names an undeclared relation doc#vewer: type 'doc' declares no relation "
        "'vewer'; did you mean 'viewer'?")
    assert msg['object-type'] == (
        "check() names an undeclared relation dco#viewer: type 'dco' is not declared in "
        "the schema; did you mean 'doc'?")
    assert msg['relationless-object'] == (
        "check() names an undeclared relation user#viewer: type 'user' declares no "
        "relations")
    assert msg['subject-type'] == (
        "check() names an undeclared subject type 'usr': type 'usr' is not declared in "
        "the schema; did you mean 'user'?")
    assert msg['subject-predicate'] == (
        "check() names an undeclared subject relation group#nosuch: type 'group' declares "
        "no relation 'nosuch'; it declares member")
    assert msg['subject-leaf'].startswith(
        "check() names an undeclared subject relation doc#readable.0: type 'doc' declares "
        "no relation 'readable.0'")


def test_a_read_and_a_write_with_the_same_mistake_say_the_same_thing(world):
    with pytest.raises(zanzibar.AdmissionRejected) as ei:
        world.sync.add_tuple('user:alice', 'vewer', 'doc:1')
    read = _refusal(lambda: world.sync.check('user:alice', 'vewer', 'doc:1'))[1]
    tail = 'names an undeclared relation doc#vewer'
    assert str(ei.value).split(tail)[1] == read.split(tail)[1]


def test_the_short_form_is_refused_with_the_six_part_message(world):
    assert (_refusal(lambda: world.sync.check('user:alice', 'vewer', 'doc:1'))
            == _refusal(lambda: world.sync.check('...', 'user', 'alice', 'vewer', 'doc', '1')))


def test_c5_a_result_key_passed_as_the_subject_names_the_corrected_call(spied):
    """The C5 repro (0.1.2 install trial): ``check(*key, ...)`` with a result key
    ``(type, name, predicate)`` used to answer ``False``."""
    args = (*RESULT_KEY, 'viewer', 'doc', '1')
    for name, call in _check_surfaces(spied, args).items():
        msg = _refusal(call)[1]
        assert msg.endswith(
            ". A result key is (type, name, predicate); check takes (subject_predicate, "
            "subject_type, subject_name, relation, object_type, object_name): write "
            + CHECK_FIX), (name, msg)
    # the corrected call answers
    assert spied.se.check('...', 'user', 'alice', 'viewer', 'doc', '1') is True
    assert spied.sync.check('...', 'user', 'alice', 'viewer', 'doc', '1') is True


@pytest.mark.parametrize('surface', ['Store stalled (set-engine fallback)',
                                     'Store tokened lagging (set-engine fallback)'])
@pytest.mark.parametrize('case', ['object-relation', 'subject-type', 'subject-predicate'])
def test_the_fallback_paths_refuse_before_dispatch(spied, surface, case):
    """``Store.check``'s set-engine fallback (a stalled index, or a token the index lags)
    refuses before it reaches the set engine: the spy on ``catch_up_evaluator`` (the
    fallback's first step) must not fire, and the refusal is the set engine's own."""
    args = CHECK_REFUSALS[case]
    got = _refusal(_check_surfaces(spied, args)[surface])
    assert got == _refusal(lambda: spied.se.check(*args))


def test_a_stalled_index_refuses_the_call_before_raising_index_stalled(spied):
    """DEC-16 item 4: a refusal of the CALL comes before the state of the index."""
    st = spied.stalled
    for call in (lambda: st.lookup('...', 'usr', 'alice'),
                 lambda: st.lookup('user:alice', object_type='dco'),
                 lambda: st.lookup_reverse('vewer', 'doc', '1'),
                 lambda: st.lookup_reverse('viewer', 'doc:1', subject_type='usr')):
        _refusal(call)
    with pytest.raises(IndexStalled):                # control: the index IS stalled
        st.lookup('user:alice')
    with pytest.raises(IndexStalled):
        st.lookup_reverse('viewer', 'doc', '1')


CHECK_LEGAL = {
    'declared': (('...', 'user', 'alice', 'viewer', 'doc', '1'), True),
    'none-is-bare': ((None, 'user', 'alice', 'viewer', 'doc', '1'), True),
    'unknown-object-name': (('...', 'user', 'alice', 'viewer', 'doc', '999'), False),
    'unknown-subject-name': (('...', 'user', 'zed', 'viewer', 'doc', '1'), False),
    'unknown-name-by-wildcard': (('...', 'user', 'zed', 'viewer', 'doc', 'pub'), True),
    'subject-wildcard': (('...', 'user', '*', 'viewer', 'doc', 'pub'), True),
    'object-wildcard-name': (('...', 'user', 'alice', 'viewer', 'folder', '*'), False),
    'userset-subject': (('member', 'group', 'eng', 'viewer', 'doc', '2'), True),
    'ttu': (('...', 'user', 'carol', 'viewer', 'doc', '3'), True),
    'boolean-derived-allowed': (('...', 'user', 'bob', 'readable', 'doc', '2'), True),
    'boolean-derived-refused': (('...', 'user', 'alice', 'readable', 'doc', '1'), False),
}


@pytest.mark.parametrize('case', sorted(CHECK_LEGAL))
def test_legal_checks_still_answer_on_every_surface(world, case):
    args, want = CHECK_LEGAL[case]
    got = {name: call() for name, call in _check_surfaces(world, args).items()}
    assert got == dict.fromkeys(got, want), got


# --------------------------------------------------------------------------- lookup

LOOKUP_SUBJECT_REFUSALS = {
    'subject-type': ('...', 'usr', 'alice'),
    'subject-predicate': ('nosuch', 'group', 'eng'),
    'subject-leaf': ('readable.0', 'doc', '1'),
    'subject-relationless': ('member', 'user', 'alice'),
    'result-key': RESULT_KEY,
}


def _lookup_surfaces(w, args):
    return {
        'Store sync': lambda: w.sync.lookup(*args),
        'Store async': lambda: w.asyn.lookup(*args),
        'Store stalled (not IndexStalled)': lambda: w.stalled.lookup(*args),
        'Store tokened lagging (not LookupNotFresh)':
            lambda: w.lagging.lookup(*args, at_least=w.token),
        'SetEngine.lookup': lambda: w.se.lookup(*args),
    }


@pytest.mark.parametrize('case', sorted(LOOKUP_SUBJECT_REFUSALS))
def test_lookup_refuses_an_undeclared_subject_identically(spied, case):
    args = LOOKUP_SUBJECT_REFUSALS[case]
    got = {n: _refusal(c) for n, c in _lookup_surfaces(spied, args).items()}
    first = got['SetEngine.lookup']
    assert all(g == first for g in got.values()), got
    assert first[2:4] == ('lookup', 'subject')


def test_c5_lookup_of_a_result_key_names_the_corrected_call(world):
    msg = _refusal(lambda: world.sync.lookup(*RESULT_KEY))[1]
    assert msg == (
        "lookup() names an undeclared subject type 'alice': type 'alice' is not declared "
        "in the schema. A result key is (type, name, predicate); lookup takes "
        f"(subject_predicate, subject_type, subject_name): write {LOOKUP_FIX}")


# Store.lookup's filters and SetEngine.filter_result's are different keywords on different
# methods, so the messages differ in their lead; class, attributes and reason must agree.
LOOKUP_FILTER_REFUSALS = {
    'type': ({'object_type': 'dco'}, {'entity_type': 'dco'}),
    'relation-on-type': ({'object_type': 'doc', 'relation': 'vewer'},
                         {'entity_type': 'doc', 'predicate': 'vewer'}),
    'relation-anywhere': ({'relation': 'vewer'}, {'predicate': 'vewer'}),
    'relationless-type': ({'object_type': 'user', 'relation': 'viewer'},
                          {'entity_type': 'user', 'predicate': 'viewer'}),
}


def _reason(msg):
    return msg.split('names an undeclared', 1)[1]


@pytest.mark.parametrize('case', sorted(LOOKUP_FILTER_REFUSALS))
def test_lookup_filters_refuse_identically(spied, case):
    store_kw, se_kw = LOOKUP_FILTER_REFUSALS[case]
    se = spied.se
    want = _refusal(lambda: se.filter_result(se.lookup('...', 'user', 'alice'), **se_kw))
    assert want[2:4] == ('filter_result', 'filter')
    for st in (spied.sync, spied.asyn, spied.stalled):
        got = _refusal(lambda st=st: st.lookup('user:alice', **store_kw))
        assert got[0] is want[0] and got[2:4] == ('lookup', 'filter'), got
        assert got[4:] == want[4:] and _reason(got[1]) == _reason(want[1]), (got, want)
    got = _refusal(lambda: spied.lagging.lookup('user:alice', at_least=spied.token,
                                                **store_kw))
    assert got[4:] == want[4:] and _reason(got[1]) == _reason(want[1])


def test_lookup_filter_messages(world):
    def m(**kw):
        return _refusal(lambda: world.sync.lookup('user:alice', **kw))[1]
    assert m(object_type='dco') == (
        "lookup(): object_type='dco' names an undeclared type: type 'dco' is not declared "
        "in the schema; did you mean 'doc'?")
    assert m(relation='vewer') == (
        "lookup(): relation='vewer' names an undeclared relation: no type in the schema "
        "declares a relation 'vewer'; did you mean 'viewer'?")
    # '...' is the bare SUBJECT; an object filter has no bare entries to keep
    assert m(relation='...').startswith("lookup(): relation='...' names an undeclared relation")


def test_legal_lookups_still_answer(world):
    for st in (world.sync, world.asyn):
        keys = st.result_keys(st.lookup('user:alice', object_type='doc', relation='viewer'))
        assert ('doc', '1', 'viewer') in keys
        assert st.result_keys(st.lookup('user:nobody')) == {               # unknown name
            ('doc', 'pub', 'viewer'), ('doc', 'pub', 'readable')}       # via user:*
        assert st.lookup('user:*', relation='viewer') is not None          # wildcard name
        assert st.lookup(None, 'user', 'alice', object_type='doc') is not None
        assert ('doc', '1', 'readable') not in st.result_keys(st.lookup('user:alice'))
    se = world.se
    res = se.lookup('...', 'user', 'alice')
    assert ('doc', '1', 'viewer') in se.result_keys(se.filter_result(res, 'doc', 'viewer'))
    assert se.result_keys(se.lookup('...', 'user', 'nobody')) == {
        ('doc', 'pub', 'viewer'), ('doc', 'pub', 'readable')}
    # filter_result serves lookup_reverse results too, so '...' (the bare subject) is legal
    rev = se.lookup_reverse('viewer', 'doc', '1')
    assert ('user', 'alice', '...') in se.result_keys(se.filter_result(rev, 'user', '...'))


# --------------------------------------------------------------------------- lookup_reverse

OBJECT_REFUSALS = {
    'object-type': ('viewer', 'dco', '1'),
    'object-relation': ('vewer', 'doc', '1'),
    'relationless-object': ('viewer', 'user', 'bob'),
    'object-leaf': ('readable.0', 'doc', '1'),
}


@pytest.mark.parametrize('case', sorted(OBJECT_REFUSALS))
def test_lookup_reverse_refuses_an_undeclared_object_identically(spied, case):
    args = OBJECT_REFUSALS[case]
    w = spied
    got = {
        'Store sync': _refusal(lambda: w.sync.lookup_reverse(*args)),
        'Store async': _refusal(lambda: w.asyn.lookup_reverse(*args)),
        'Store stalled (not IndexStalled)': _refusal(lambda: w.stalled.lookup_reverse(*args)),
        'Store tokened lagging (not LookupNotFresh)':
            _refusal(lambda: w.lagging.lookup_reverse(*args, at_least=w.token)),
        'SetEngine.lookup_reverse': _refusal(lambda: w.se.lookup_reverse(*args)),
    }
    first = got['SetEngine.lookup_reverse']
    assert all(g == first for g in got.values()), got
    assert first[2:4] == ('lookup_reverse', 'object')


REVERSE_FILTER_REFUSALS = {
    'type': ({'subject_type': 'usr'}, {'entity_type': 'usr'}),
    'predicate-on-type': ({'subject_type': 'group', 'subject_predicate': 'nosuch'},
                          {'entity_type': 'group', 'predicate': 'nosuch'}),
    'predicate-anywhere': ({'subject_predicate': 'nosuch'}, {'predicate': 'nosuch'}),
    'predicate-on-relationless': ({'subject_type': 'user', 'subject_predicate': 'member'},
                                  {'entity_type': 'user', 'predicate': 'member'}),
    'leaf-predicate': ({'subject_predicate': 'readable.0'}, {'predicate': 'readable.0'}),
}


@pytest.mark.parametrize('case', sorted(REVERSE_FILTER_REFUSALS))
def test_lookup_reverse_filters_refuse_identically(spied, case):
    store_kw, se_kw = REVERSE_FILTER_REFUSALS[case]
    se = spied.se
    want = _refusal(lambda: se.filter_result(se.lookup_reverse('viewer', 'doc', '1'),
                                             **se_kw))
    for st in (spied.sync, spied.asyn, spied.stalled):
        got = _refusal(lambda st=st: st.lookup_reverse('viewer', 'doc:1', **store_kw))
        assert got[2:4] == ('lookup_reverse', 'filter'), got
        assert got[4:] == want[4:] and _reason(got[1]) == _reason(want[1]), (got, want)


def test_legal_lookup_reverse_still_answers(world):
    for st in (world.sync, world.asyn):
        keys = st.result_keys(st.lookup_reverse('viewer', 'doc:1', subject_type='user',
                                                subject_predicate='...'))
        assert ('user', 'alice', '...') in keys
        # an unknown name: only the userset self-relation (doc:999#viewer is its own member)
        assert st.result_keys(st.lookup_reverse('viewer', 'doc:999')) == {('doc', '999', 'viewer')}
        assert st.lookup_reverse('viewer', 'folder:*').markers == set()
        res = st.lookup_reverse('viewer', 'doc:pub', subject_predicate=None)
        assert ('user', '...') in {m[:2] for m in res.markers}
        assert st.lookup_reverse('readable', 'doc:2', subject_predicate='member') is not None


# --------------------------------------------------------------------------- expand

@pytest.mark.parametrize('case', sorted(OBJECT_REFUSALS))
def test_expand_refuses_an_undeclared_object_identically(spied, case):
    args = OBJECT_REFUSALS[case]
    w = spied
    got = {
        'Store sync': _refusal(lambda: w.sync.expand(*args)),
        'Store stalled': _refusal(lambda: w.stalled.expand(*args)),
        'Store tokened lagging': _refusal(lambda: w.lagging.expand(*args, at_least=w.token)),
        'SetEngine.expand': _refusal(lambda: w.se.expand(*args)),
    }
    first = got['SetEngine.expand']
    assert all(g == first for g in got.values()), got
    assert first[2:4] == ('expand', 'object')


def test_legal_expand_still_answers(world):
    for st in (world.sync, world.stalled):
        assert ('user', 'alice', '...') in st.expand('viewer', 'doc:1').keys
        assert st.expand('viewer', 'doc:999').keys == {('doc', '999', 'viewer')}
        assert st.expand('viewer', 'folder', '*').keys == frozenset()       # a wildcard NAME
    assert world.se.expand('readable', 'doc', '2') is not None


# --------------------------------------------------------------------------- filter_result

def test_filter_result_legal_filters(world):
    se = world.se
    res = se.lookup_reverse('viewer', 'doc', '2')
    assert se.filter_result(res) is res
    assert se.filter_result(res, 'group', 'member') is not None
    assert se.filter_result(res, None, '...') is not None
    assert se.filter_result(res, None, 'member') is not None


# --------------------------------------------------------------------------- the graph

def test_wildcard_index_stays_lenient(world):
    """DEC-16 item 5: the graph index answers ``False`` / empty and never raises; Store,
    its only supported caller, refuses first."""
    widx = world.sync.widx
    assert widx.check('...', 'user', 'alice', 'vewer', 'doc', '1') is False
    assert widx.check('readable.0', 'doc', '1', 'viewer', 'doc', '2') is False
    assert not widx.lookup_reverse('vewer', 'doc', '1').node_ids
