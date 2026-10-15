"""TK123 items 7, 8, 23, 26 -- the call surface a first-time user types.

Properties guarded
------------------
* **Item 7, keyword names.** ``subject_type`` / ``subject_name`` / ``object_type`` /
  ``object_name`` (and the kept ``subject_predicate`` / ``relation``) are the parameter
  names of ``add_tuple`` / ``remove_tuple`` / ``check`` / ``lookup`` / ``lookup_reverse`` on
  ``SetEngine`` and ``WildcardIndex``, and they BIND as keywords on ``Store``,
  ``TupleSource``, ``SetEngine`` and ``WildcardIndex`` (pinned by literal signatures and by
  keyword calls agreeing with positional ones).
* **Item 8.** The set engine's result type is ``SetLookupResult``, a dataclass (keyword
  constructor, ``==``); ``zanzibar.setengine`` no longer exports ``LookupResult``.
* **Item 23, the OpenFGA string form.** ``Store`` / ``TupleSource`` accept
  ``("user:alice", "viewer", "doc:d1")``, ``"group:eng#member"`` and ``"user:*"`` beside
  the six-part form, chosen by keyword or by arity; both forms give identical answers over a
  grid, and malformed strings are refused with the expected form in the message
  (``zanzibar.schema.tuplestr``).
* **Item 26.** ``Store(schema=...)`` accepts an OpenFGA JSON model (``dict``, JSON string,
  or wrapped as ``{"authorization_model": ...}``), persists it as DSL, and reopens with the
  same JSON without ``SchemaMismatch``; any other type (a ``RuleSet``) is a ``TypeError``
  naming ``str`` / ``dict``.

SABOTAGE (2026-10-15, agent ``items-7-8-23-26``; this docstring is the tracked record). One
asserted-unique anchor per mutation (gitignored ``.scratch/tk123/sab7823.py``), this module
only (34 tests), ``-p no:cacheprovider``, file restored byte-for-byte and sha256-checked.
Literal tails, every one RED:

- S1 ``tuplestr.parse_user`` drops the ``'#' in predicate`` check (splits on the first
  '#' only, so ``group:eng#member#x`` is admitted): ``rc=1 | 2 failed, 32 passed``
  (``test_malformed_strings_are_refused[user-group:eng#member#x]``,
  ``test_wrong_arity_and_keywords_name_both_forms``).
- S2 ``store/_store.py::_schema_text`` returns a JSON *string* unconverted:
  ``rc=1 | 2 failed, 32 passed`` (``..._persists_dsl[str]``, ``[wrapped-str]``).
- S3 ``SetEngine.lookup`` keeps the old ``s_type`` parameter name:
  ``rc=1 | 2 failed, 32 passed`` (``test_backend_parameter_names_are_the_documented_ones
  [SetEngine]``, ``test_documented_keyword_names_bind_on_every_entry``).
- S4 ``SetLookupResult`` loses ``@dataclass``: ``rc=1 | 3 failed, 31 passed``.
- S5 ``parse_user`` maps a bare ``type:name`` to predicate ``'member'`` instead of
  ``'...'``: ``rc=1 | 8 failed, 26 passed`` (the string/six grid among them).
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

import zanzibar
import zanzibar.setengine
from zanzibar import MalformedTupleString, SchemaError, ZanzibarError
from zanzibar.graphindex import WildcardIndex
from zanzibar.schema import parse_openfga_schema, parse_schema_ast
from zanzibar.schema.tuplestr import parse_object, parse_user
from zanzibar.setengine import SetEngine, SetLookupResult
from zanzibar.store import SchemaRecord, Store, TupleSource

SCHEMA = """model
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

FGA = Path(__file__).parent / 'fga_schemas'


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f'sqlite:///{(tmp_path / "tk123_forms.db").as_posix()}')
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


# --------------------------------------------------------------------------- item 7

_LONG = ('subject_predicate', 'subject_type', 'subject_name',
         'relation', 'object_type', 'object_name')


@pytest.mark.parametrize('cls', [SetEngine, WildcardIndex])
def test_backend_parameter_names_are_the_documented_ones(cls):
    def names(meth):
        return tuple(inspect.signature(getattr(cls, meth)).parameters)[1:]
    assert names('add_tuple') == _LONG
    assert names('remove_tuple') == _LONG
    assert names('check') == _LONG
    assert names('lookup') == _LONG[:3]
    assert names('lookup_reverse') == _LONG[3:]


def _populated(session, store_id='app'):
    store = Store(session, store_id, schema=SCHEMA)
    store.add_tuple('...', 'user', 'alice', 'member', 'group', 'eng')
    store.add_tuple('member', 'group', 'eng', 'viewer', 'doc', 'd1')
    store.add_tuple('...', 'user', '*', 'viewer', 'doc', 'd2')
    store.add_tuple('...', 'user', 'mallory', 'banned', 'doc', 'd2')
    return store


def test_documented_keyword_names_bind_on_every_entry(engine):
    six = dict(zip(_LONG, ('...', 'user', 'alice', 'viewer', 'doc', 'd1')))
    with Session(engine) as session:
        store = _populated(session)
        for target in (store, store.source, store.source.engine, store.widx):
            assert target.check(**six) is True, type(target).__name__
            assert target.check(**{**six, 'object_name': 'd9'}) is False
        for target in (store, store.source.engine, store.widx):
            subj = {k: six[k] for k in _LONG[:3]}
            obj = {k: six[k] for k in _LONG[3:]}
            assert target.lookup(**subj) == target.lookup(*subj.values())
            assert target.lookup_reverse(**obj) == target.lookup_reverse(*obj.values())
        # writes by keyword, on the Store and on a TupleSource
        bob = {**six, 'subject_name': 'bob'}
        store.add_tuple(**bob)
        assert store.check(**bob) is True
        store.remove_tuple(**bob)
        assert store.check(**bob) is False


# --------------------------------------------------------------------------- item 8

def test_set_lookup_result_is_a_dataclass_with_equality():
    a = SetLookupResult(node_ids={1, 2}, markers={('user', '...')}, excluded_node_ids={3})
    assert a == SetLookupResult(node_ids={2, 1}, markers={('user', '...')},
                                excluded_node_ids={3})
    assert a != SetLookupResult(node_ids={1, 2})
    assert SetLookupResult() == SetLookupResult(node_ids=set(), markers=set(),
                                                excluded_node_ids=set())
    assert SetLookupResult().node_ids is not SetLookupResult().node_ids  # no shared default
    assert 'SetLookupResult' in zanzibar.setengine.__all__
    assert not hasattr(zanzibar.setengine, 'LookupResult')


def test_set_engine_lookups_return_set_lookup_result(engine):
    with Session(engine) as session:
        se = _populated(session).source.engine
        res = se.lookup('...', 'user', 'alice')
        assert isinstance(res, SetLookupResult)
        assert isinstance(se.lookup_reverse('viewer', 'doc', 'd2'), SetLookupResult)


# --------------------------------------------------------------------------- item 23

@pytest.mark.parametrize('text, parts', [
    ('user:alice', ('...', 'user', 'alice')),
    ('group:eng#member', ('member', 'group', 'eng')),
    ('user:*', ('...', 'user', '*')),
    ('group:*#member', ('member', 'group', '*')),
])
def test_user_strings_split(text, parts):
    assert parse_user(text) == parts


@pytest.mark.parametrize('kind, text', [
    ('user', 'group:eng#member#x'), ('user', 'user'), ('user', ':alice'),
    ('user', 'user:'), ('user', 'user:a:b'), ('user', 'user:alice#'),
    ('user', 'user:alice#...'), ('user', ''), ('user', '#member'),
    ('object', 'doc:d1#viewer'), ('object', 'doc'), ('object', 'doc:'),
    ('object', ':d1'), ('object', 'doc:a:b'),
])
def test_malformed_strings_are_refused(kind, text):
    parse = parse_user if kind == 'user' else parse_object
    with pytest.raises(MalformedTupleString) as exc:
        parse(text)
    assert "'type:name'" in str(exc.value)
    assert isinstance(exc.value, ValueError) and isinstance(exc.value, ZanzibarError)


@pytest.mark.parametrize('bad', [None, 3, ('user', 'alice')])
def test_non_string_parts_are_a_type_error(bad):
    with pytest.raises(TypeError, match='must be a str'):
        parse_user(bad)
    with pytest.raises(TypeError, match='must be a str'):
        parse_object(bad)


_SUBJECTS = [('...', 'user', 'alice'), ('...', 'user', 'bob'), ('...', 'user', 'mallory'),
             ('member', 'group', 'eng'), ('...', 'user', '*')]
_OBJECTS = [('doc', 'd1'), ('doc', 'd2'), ('group', 'eng')]
_RELATIONS = ['viewer', 'banned', 'member']


def _user_str(pred, typ, name):
    return f'{typ}:{name}' if pred == '...' else f'{typ}:{name}#{pred}'


def test_string_form_equals_six_form_over_a_grid(engine):
    """Store A is written in the six-part form, store B in the string form; every check
    agrees across the two stores AND across the two read forms, and lookups agree by key."""
    writes = [(('...', 'user', 'alice'), 'member', ('group', 'eng')),
              (('member', 'group', 'eng'), 'viewer', ('doc', 'd1')),
              (('...', 'user', '*'), 'viewer', ('doc', 'd2')),
              (('...', 'user', 'mallory'), 'banned', ('doc', 'd2')),
              (('...', 'user', 'bob'), 'viewer', ('doc', 'd1'))]
    with Session(engine) as session:
        a = Store(session, 'six', schema=SCHEMA)
        b = Store(session, 'str', schema=SCHEMA)
        for subj, rel, obj in writes:
            a.add_tuple(*subj, rel, *obj)
            b.add_tuple(_user_str(*subj), rel, f'{obj[0]}:{obj[1]}')
        a.remove_tuple('...', 'user', 'bob', 'viewer', 'doc', 'd1')
        b.remove_tuple(user='user:bob', relation='viewer', object='doc:d1')
        answers = 0
        for subj in _SUBJECTS:
            for rel in _RELATIONS:
                for obj in _OBJECTS:
                    six = a.check(*subj, rel, *obj)
                    assert b.check(*subj, rel, *obj) is six, (subj, rel, obj)
                    s = (_user_str(*subj), rel, f'{obj[0]}:{obj[1]}')
                    assert a.check(*s) is six and b.check(*s) is six, (subj, rel, obj)
                    assert b.check(user=s[0], relation=rel, object=s[2]) is six
                    assert b.source.check(*s) is b.source.check(*subj, rel, *obj)
                    answers += six
            assert a.lookup(_user_str(*subj)) == a.lookup(*subj)
            assert a.lookup(user=_user_str(*subj)) == a.lookup(*subj)
        assert answers > 0                       # the grid is not vacuously all-False
        for rel in _RELATIONS:
            for obj in _OBJECTS:
                o = f'{obj[0]}:{obj[1]}'
                assert a.lookup_reverse(rel, o) == a.lookup_reverse(rel, *obj)
                assert a.lookup_reverse(relation=rel, object=o) == a.lookup_reverse(rel, *obj)


def test_tuple_source_writes_in_the_string_form(engine):
    with Session(engine) as session:
        save = Store(session, 'ts', schema=SCHEMA)
        del save
        src = TupleSource(session, 'ts')
        src.add('user:alice', 'viewer', 'doc:d1')
        assert src.check('user:alice', 'viewer', 'doc:d1') is True
        assert src.check('...', 'user', 'alice', 'viewer', 'doc', 'd1') is True
        src.remove(user='user:alice', relation='viewer', object='doc:d1')
        assert src.check('user:alice', 'viewer', 'doc:d1') is False


def test_wrong_arity_and_keywords_name_both_forms(engine):
    with Session(engine) as session:
        store = _populated(session)
        with pytest.raises(TypeError, match=r'takes 3 arguments \(user, relation, object\) '
                                            r'or 6'):
            store.add_tuple('user:alice', 'viewer', 'doc', 'd1')
        with pytest.raises(TypeError, match='multiple values'):
            store.check('user:alice', 'viewer', 'doc:d1', user='user:bob')
        with pytest.raises(TypeError):
            store.check('user:alice', 'viewer', object_name='d1')
        with pytest.raises(TypeError, match='takes 1 arguments'):
            store.lookup('user', 'alice')
        with pytest.raises(MalformedTupleString):
            store.add_tuple('user:alice', 'viewer', 'doc:d1#viewer')
        with pytest.raises(MalformedTupleString):
            store.check('group:eng#member#x', 'viewer', 'doc:d1')


# --------------------------------------------------------------------------- item 26

def _json_model() -> dict:
    return json.loads((FGA / 'boolean_wildcards.json').read_text(encoding='utf-8'))


def _dsl_twin() -> str:
    return (FGA / 'boolean_wildcards.fga').read_text(encoding='utf-8')


@pytest.mark.parametrize('form', ['dict', 'str', 'wrapped-dict', 'wrapped-str'])
def test_store_accepts_openfga_json_and_persists_dsl(engine, form):
    model = _json_model()
    schema = {
        'dict': model,
        'str': json.dumps(model, indent=2),
        'wrapped-dict': {'authorization_model': {'id': '01HX', **model}},
        'wrapped-str': '  ' + json.dumps({'authorization_model': model}),
    }[form]
    with Session(engine) as session:
        store = Store(session, 'j', schema=schema)
        text = session.get(SchemaRecord, 'j').schema_text
        assert not text.lstrip().startswith('{')
        assert parse_schema_ast(text) == parse_schema_ast(_dsl_twin())
        store.add_tuple('user:alice', 'editor', 'doc:d1')
        assert store.check('user:alice', 'viewer', 'doc:d1') is True
        # reopen with the same JSON, with the DSL twin, and with no schema at all
        for again in (schema, _dsl_twin(), None):
            reopened = Store(session, 'j', schema=again)
            assert reopened.check('user:alice', 'viewer', 'doc:d1') is True


def test_store_refuses_a_ruleset_and_other_types(engine):
    with Session(engine) as session:
        with pytest.raises(TypeError, match=r'a str\) or an OpenFGA JSON model \(a str or a '
                                            r'dict\), not RuleSet'):
            Store(session, 'r', schema=parse_openfga_schema(SCHEMA))
        with pytest.raises(TypeError, match='not bytes'):
            Store(session, 'r', schema=SCHEMA.encode())
        with pytest.raises(SchemaError, match='not valid OpenFGA JSON'):
            Store(session, 'r', schema='{"schema_version": ')
        assert session.get(SchemaRecord, 'r') is None
